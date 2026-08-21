"""Servidor MCP minimo (rama SDK 2.x, API lowlevel de mcp 2.0.0) — banco de pruebas de FileX.

Mismas herramientas que srv_1x.py. La API cambia por completo:
  - handlers por constructor (on_list_tools / on_call_tool), no decoradores
  - firma (ctx, params) -> Result
  - roots esta DEPRECADO (SEP-2577): ServerSession.list_roots emite MCPDeprecationWarning
  - mime_type (snake_case) en vez de mimeType
"""

import anyio
import base64
import json
import os
import sys
import time
import warnings
from urllib.parse import urlparse, unquote

import mcp.types as types
from mcp.server.lowlevel import Server
import mcp.server.stdio

T0 = time.time()
AVISOS: list[str] = []


def log(msg: str) -> None:
    print(f"[srv2 +{time.time()-T0:7.3f}s] {msg}", file=sys.stderr, flush=True)


def _captura_aviso(message, category, filename, lineno, file=None, line=None):
    AVISOS.append(f"{category.__name__}: {message}")
    log(f"WARNING {category.__name__}: {message}")


warnings.showwarning = _captura_aviso
warnings.simplefilter("always")

RAICES_SERVIDOR = [os.path.abspath(p) for p in
                   (os.environ.get("FILEX_RAICES", "").split(";") if os.environ.get("FILEX_RAICES") else [])]

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
B64_PURO = base64.b64encode(PNG_1X1).decode()
B64_PREFIJO = f"data:image/png;base64,{B64_PURO}"

EVENTOS: list[dict] = []

HERRAMIENTAS = [
    types.Tool(name="t_ping", description="trivial", input_schema={"type": "object", "properties": {}}),
    types.Tool(name="t_roots", description="pide roots/list", input_schema={"type": "object", "properties": {}}),
    types.Tool(name="t_roots_cap", description="capacidades del cliente", input_schema={"type": "object", "properties": {}}),
    types.Tool(name="t_roots_interseca", description="interseca", input_schema={"type": "object", "properties": {}}),
    types.Tool(name="t_slow", description="duerme N s con progreso",
               input_schema={"type": "object", "properties": {"seconds": {"type": "number"}}, "required": ["seconds"]}),
    types.Tool(name="t_img", description="ImageContent",
               input_schema={"type": "object", "properties": {"mode": {"type": "string"}}, "required": ["mode"]}),
    types.Tool(name="t_eventos", description="log", input_schema={"type": "object", "properties": {}}),
]


def uri_a_ruta(uri: str):
    p = urlparse(uri)
    if p.scheme != "file":
        return None
    ruta = unquote(p.path)
    if os.name == "nt" and len(ruta) > 2 and ruta[0] == "/" and ruta[2] == ":":
        ruta = ruta[1:]
    return os.path.abspath(ruta)


async def on_list_tools(ctx, params) -> types.ListToolsResult:
    return types.ListToolsResult(tools=HERRAMIENTAS)


async def _pedir_roots(ctx):
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            res = await ctx.session.list_roots()
            for x in w:
                AVISOS.append(f"{x.category.__name__}: {x.message}")
                log(f"WARNING(list_roots) {x.category.__name__}: {x.message}")
        return True, {"roots": [{"uri": str(r.uri), "name": r.name} for r in res.roots]}
    except Exception as e:  # noqa: BLE001
        err = getattr(e, "error", None)
        return False, {"excepcion": type(e).__module__ + "." + type(e).__name__,
                       "repr": repr(e), "str": str(e),
                       "code": getattr(err, "code", getattr(e, "code", None)),
                       "message": getattr(err, "message", None)}


def _txt(obj):
    return types.CallToolResult(content=[types.TextContent(text=json.dumps(obj, ensure_ascii=False, default=str))])


async def on_call_tool(ctx, params) -> types.CallToolResult:
    name, args = params.name, (params.arguments or {})

    if name == "t_ping":
        return types.CallToolResult(content=[types.TextContent(text="pong")])

    if name == "t_roots_cap":
        caps = None
        try:
            caps = ctx.session.client_params.capabilities.model_dump() if ctx.session.client_params else None
        except Exception as e:  # noqa: BLE001
            caps = f"<error: {e!r}>"
        chk = None
        try:
            chk = ctx.session.check_client_capability(
                types.ClientCapabilities(roots=types.RootsCapability(list_changed=False)))
        except Exception as e:  # noqa: BLE001
            chk = f"<error: {type(e).__name__}: {e}>"
        return _txt({"check_client_capability": chk, "capacidades_cliente": caps,
                     "protocolo": getattr(ctx, "protocol_version", None), "avisos": AVISOS})

    if name == "t_roots":
        ok, payload = await _pedir_roots(ctx)
        log(f"t_roots ok={ok} payload={payload}")
        return _txt({"ok": ok, **payload, "avisos": AVISOS})

    if name == "t_roots_interseca":
        ok, payload = await _pedir_roots(ctx)
        if not ok:
            return _txt({"modo": "fallback_lista_servidor", "servidor": RAICES_SERVIDOR,
                         "cliente": [], "efectiva": list(RAICES_SERVIDOR)})
        efectiva = []
        for r in payload["roots"]:
            c = uri_a_ruta(r["uri"])
            if not c:
                continue
            for s in RAICES_SERVIDOR:
                cn, sn = os.path.normcase(c), os.path.normcase(s)
                if cn == sn or cn.startswith(sn + os.sep):
                    efectiva.append(c)
                    break
                if sn.startswith(cn + os.sep):
                    efectiva.append(s)
                    break
        return _txt({"modo": "interseccion", "servidor": RAICES_SERVIDOR,
                     "cliente": payload["roots"], "efectiva": efectiva})

    if name == "t_slow":
        secs = float(args.get("seconds", 5))
        tok = getattr(ctx.meta, "progress_token", None) or getattr(ctx.meta, "progressToken", None) if ctx.meta else None
        log(f"t_slow secs={secs} progress_token={tok!r} meta={ctx.meta!r}")
        pasos = max(1, int(secs))
        fallos = []
        for i in range(pasos):
            await anyio.sleep(secs / pasos)
            # En 2.x la via correcta es session.report_progress(): no necesita token,
            # el propio dispatcher sabe contra que peticion emitir (no-op si el
            # llamante no pidio progreso). send_progress_notification() con el token
            # de ctx.meta NO sirve en la era moderna: alli meta no trae progressToken.
            try:
                await ctx.session.report_progress(
                    float(i + 1), float(pasos), f"paso {i+1}/{pasos}")
            except Exception as e:  # noqa: BLE001
                fallos.append(repr(e))
                log(f"report_progress fallo: {e!r}")
        return _txt({"dormido_s": secs, "progress_token": str(tok), "pasos": pasos, "fallos_progreso": fallos[:3]})

    if name == "t_img":
        modo = args["mode"]
        datos = {"puro": B64_PURO, "prefijo": B64_PREFIJO,
                 "basura": "esto no es base64 !!!! @@@@", "vacio": "", "nomime": B64_PURO}[modo]
        mime = "" if modo == "nomime" else "image/png"
        return types.CallToolResult(content=[types.ImageContent(data=datos, mime_type=mime)])

    if name == "t_eventos":
        return _txt({"eventos": EVENTOS, "avisos": AVISOS})

    return types.CallToolResult(content=[types.TextContent(text=f"desconocida: {name}")], is_error=True)


async def on_roots_list_changed(ctx, params) -> None:
    log("RECIBIDA notifications/roots/list_changed")
    EVENTOS.append({"t": round(time.time() - T0, 3), "evento": "roots/list_changed"})


async def main():
    kwargs = dict(on_list_tools=on_list_tools, on_call_tool=on_call_tool)
    if os.environ.get("FILEX_SIN_ROOTS_HANDLER") != "1":
        kwargs["on_roots_list_changed"] = on_roots_list_changed
    server = Server("filex-probe-2x", version="0.0.1", **kwargs)
    log(f"arrancando. raices={RAICES_SERVIDOR}. avisos_hasta_ahora={AVISOS}")
    async with mcp.server.stdio.stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options(), raise_exceptions=False)


if __name__ == "__main__":
    anyio.run(main)

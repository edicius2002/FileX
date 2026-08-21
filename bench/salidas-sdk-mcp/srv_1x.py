"""Servidor MCP minimo (rama SDK 1.x, API lowlevel) — banco de pruebas de FileX.

Herramientas:
  t_ping                  trivial
  t_roots                 pide roots/list al cliente y devuelve resultado o error literal
  t_roots_cap             solo consulta check_client_capability(), sin llamar
  t_roots_interseca       demuestra la INTERSECCION con la lista inmutable del servidor
  t_slow(seconds)         operacion larga, emite notifications/progress si hay progressToken
  t_img(mode)             ImageContent con base64 puro / prefijo data: / basura / vacio

stderr lleva un log con marca de tiempo: es la evidencia del comportamiento sin soporte de roots.
Uso: python srv_1x.py [--roots-al-arrancar] [--raices RUTA1;RUTA2]
"""

import anyio
import asyncio
import base64
import json
import os
import sys
import time
from urllib.parse import urlparse, unquote

import mcp.types as types
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

T0 = time.time()


def log(msg: str) -> None:
    print(f"[srv +{time.time()-T0:7.3f}s] {msg}", file=sys.stderr, flush=True)


# Lista blanca inmutable del servidor (lo que en la referencia TS son los argv)
RAICES_SERVIDOR = [os.path.abspath(p) for p in
                   (os.environ.get("FILEX_RAICES", "").split(";") if os.environ.get("FILEX_RAICES") else [])]

PEDIR_AL_ARRANCAR = "--roots-al-arrancar" in sys.argv

# PNG 1x1 rojo real, para el ImageContent
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
B64_PURO = base64.b64encode(PNG_1X1).decode()
B64_PREFIJO = f"data:image/png;base64,{B64_PURO}"   # lo que hace image-worker-mcp

server = Server("filex-probe-1x")

EVENTOS: list[dict] = []


def uri_a_ruta(uri: str) -> str | None:
    """file:///C:/x -> C:\\x   (el fileURLToPath de Node lleva barra de mas en Windows)."""
    p = urlparse(uri)
    if p.scheme != "file":
        return None
    ruta = unquote(p.path)
    if os.name == "nt" and len(ruta) > 2 and ruta[0] == "/" and ruta[2] == ":":
        ruta = ruta[1:]
    return os.path.abspath(ruta)


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(name="t_ping", description="trivial",
                   inputSchema={"type": "object", "properties": {}}),
        types.Tool(name="t_roots", description="pide roots/list al cliente",
                   inputSchema={"type": "object", "properties": {}}),
        types.Tool(name="t_roots_cap", description="check_client_capability(roots)",
                   inputSchema={"type": "object", "properties": {}}),
        types.Tool(name="t_roots_interseca", description="interseca roots del cliente con la lista del servidor",
                   inputSchema={"type": "object", "properties": {}}),
        types.Tool(name="t_slow", description="duerme N segundos emitiendo progreso",
                   inputSchema={"type": "object",
                                "properties": {"seconds": {"type": "number"},
                                               "progress": {"type": "boolean"}},
                                "required": ["seconds"]}),
        types.Tool(name="t_img", description="devuelve un ImageContent",
                   inputSchema={"type": "object",
                                "properties": {"mode": {"type": "string",
                                                        "enum": ["puro", "prefijo", "basura", "vacio", "nomime"]}},
                                "required": ["mode"]}),
        types.Tool(name="t_eventos", description="devuelve el log de eventos del servidor",
                   inputSchema={"type": "object", "properties": {}}),
    ]


async def _pedir_roots(ctx):
    """Devuelve (ok, payload). Captura el error literal si el cliente no soporta roots."""
    try:
        res = await ctx.session.list_roots()
        return True, {"roots": [{"uri": str(r.uri), "name": r.name} for r in res.roots]}
    except Exception as e:  # noqa: BLE001
        err = getattr(e, "error", None)
        return False, {"excepcion": type(e).__module__ + "." + type(e).__name__,
                       "repr": repr(e), "str": str(e),
                       "code": getattr(err, "code", None),
                       "message": getattr(err, "message", None)}


@server.call_tool()
async def call_tool(name: str, args: dict):
    ctx = server.request_context

    if name == "t_ping":
        return [types.TextContent(type="text", text="pong")]

    if name == "t_roots_cap":
        soporta = ctx.session.check_client_capability(
            types.ClientCapabilities(roots=types.RootsCapability(listChanged=False)))
        soporta_lc = ctx.session.check_client_capability(
            types.ClientCapabilities(roots=types.RootsCapability(listChanged=True)))
        caps = ctx.session.client_params.capabilities.model_dump() if ctx.session.client_params else None
        return [types.TextContent(type="text", text=json.dumps(
            {"roots": soporta, "roots.listChanged": soporta_lc, "capacidades_cliente": caps},
            ensure_ascii=False, default=str))]

    if name == "t_roots":
        ok, payload = await _pedir_roots(ctx)
        log(f"t_roots ok={ok} payload={payload}")
        return [types.TextContent(type="text", text=json.dumps(
            {"ok": ok, **payload}, ensure_ascii=False))]

    if name == "t_roots_interseca":
        ok, payload = await _pedir_roots(ctx)
        if not ok:
            # R13: sin roots del cliente se sigue con la lista inmutable del servidor
            efectiva = list(RAICES_SERVIDOR)
            modo = "fallback_lista_servidor"
        else:
            del_cliente = [uri_a_ruta(r["uri"]) for r in payload["roots"]]
            del_cliente = [p for p in del_cliente if p]
            # INTERSECCION por segmentos: se queda la raiz del cliente solo si esta
            # contenida en (o es igual a) alguna raiz del servidor. Nunca amplia.
            efectiva = []
            for c in del_cliente:
                for s in RAICES_SERVIDOR:
                    cn, sn = os.path.normcase(c), os.path.normcase(s)
                    if cn == sn or cn.startswith(sn + os.sep):
                        efectiva.append(c)     # el cliente ESTRECHA
                        break
                    if sn.startswith(cn + os.sep):
                        efectiva.append(s)     # el cliente pide mas ancho -> se queda el servidor
                        break
            modo = "interseccion"
        return [types.TextContent(type="text", text=json.dumps(
            {"modo": modo, "servidor": RAICES_SERVIDOR,
             "cliente": payload.get("roots", []), "efectiva": efectiva},
            ensure_ascii=False))]

    if name == "t_slow":
        secs = float(args.get("seconds", 5))
        con_prog = bool(args.get("progress", True))
        tok = ctx.request_context.meta.progressToken if getattr(ctx, "request_context", None) else None
        tok = ctx.meta.progressToken if (getattr(ctx, "meta", None) is not None) else tok
        log(f"t_slow secs={secs} progressToken={tok!r}")
        pasos = max(1, int(secs))
        for i in range(pasos):
            await anyio.sleep(secs / pasos)
            if con_prog and tok is not None:
                try:
                    await ctx.session.send_progress_notification(
                        progress_token=tok, progress=float(i + 1), total=float(pasos),
                        message=f"paso {i+1}/{pasos}")
                except Exception as e:  # noqa: BLE001
                    log(f"progreso fallo: {e!r}")
        return [types.TextContent(type="text", text=json.dumps(
            {"dormido_s": secs, "progressToken": str(tok), "pasos": pasos}))]

    if name == "t_img":
        modo = args["mode"]
        datos = {"puro": B64_PURO, "prefijo": B64_PREFIJO,
                 "basura": "esto no es base64 !!!! @@@@", "vacio": "",
                 "nomime": B64_PURO}[modo]
        mime = "" if modo == "nomime" else "image/png"
        return [types.ImageContent(type="image", data=datos, mimeType=mime)]

    if name == "t_eventos":
        return [types.TextContent(type="text", text=json.dumps(EVENTOS, ensure_ascii=False))]

    raise ValueError(f"herramienta desconocida: {name}")


# --- notificacion roots/list_changed -------------------------------------
# El SDK 1.x NO expone decorador para notifications/roots/list_changed en el
# lowlevel Server: hay que registrarlo a mano en el mapa de handlers.
async def on_roots_changed(req) -> None:
    log(f"RECIBIDA notifications/roots/list_changed: {req!r}")
    EVENTOS.append({"t": round(time.time() - T0, 3), "evento": "roots/list_changed"})


try:
    server.notification_handlers[types.RootsListChangedNotification] = on_roots_changed
    log("handler de roots/list_changed registrado a mano (no hay decorador)")
except Exception as e:  # noqa: BLE001
    log(f"NO se pudo registrar handler de roots/list_changed: {e!r}")


async def main():
    opts = InitializationOptions(
        server_name="filex-probe-1x",
        server_version="0.0.1",
        capabilities=server.get_capabilities(
            notification_options=NotificationOptions(), experimental_capabilities={}),
    )
    log(f"arrancando. raices_servidor={RAICES_SERVIDOR} pedir_al_arrancar={PEDIR_AL_ARRANCAR}")
    async with mcp.server.stdio.stdio_server() as (r, w):
        if PEDIR_AL_ARRANCAR:
            # Imitar el oninitialized de la referencia TS. En Python NO hay hook:
            # se lanza una tarea de fondo que espera a que la sesion este inicializada.
            async def tarea_arranque():
                for _ in range(100):
                    await anyio.sleep(0.05)
                    ses = getattr(server, "_session", None)
                    if ses is not None:
                        break
            # se hace dentro de run() via el propio server; aqui solo se anota
            log("PEDIR_AL_ARRANCAR: sin hook oninitialized en el SDK Python")
        await server.run(r, w, opts, raise_exceptions=False)


if __name__ == "__main__":
    anyio.run(main)

"""Cabo 1 — Servidor MCP minimo sobre `mcp 2.0.0` para enfrentarlo a CLIENTES REALES.

Objetivo: comprobar contra un cliente que no es Python
  - que version del protocolo se negocia,
  - que informa el cliente de si mismo (`clientInfo`) y que capacidades declara,
  - si las anotaciones (`readOnlyHint`, `destructiveHint`, `title`, `icons`, `meta`)
    llegan y se usan,
  - si sobrevive `ImageContent`, `structuredContent`, recursos y prompts.

Todo lo observable se escribe como JSONL en `cabo1_srv_log.jsonl` (una linea por evento),
porque el stdout es la tuberia JSON-RPC y el stderr lo captura el cliente.
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.mcpserver import MCPServer, Context  # noqa: E402
from mcp_types import ToolAnnotations  # noqa: E402

from cabo2_roots import RootsOpcionales, raices_efectivas  # noqa: E402

T0 = time.time()
LOG = Path(os.environ.get("CABO1_LOG",
                          str(Path(__file__).with_name("cabo1_srv_log.jsonl"))))


def log(evento: str, **datos):
    reg = {"t": round(time.time() - T0, 3),
           "ts": time.strftime("%H:%M:%S"),
           "pid": os.getpid(),
           "evento": evento, **datos}
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(reg, ensure_ascii=False, default=str) + "\n")
    print(f"[cabo1 +{time.time()-T0:7.3f}s] {evento} {datos}", file=sys.stderr, flush=True)


server = MCPServer("filex-cabo1", version="0.0.1")


def _radiografia(ctx: Context) -> dict:
    """Todo lo que el servidor puede saber del cliente, sin suponer nada de la API."""
    d = {"protocolo_negociado": getattr(ctx, "protocol_version", None)}
    caps = getattr(ctx, "client_capabilities", None)
    d["client_capabilities"] = caps.model_dump(exclude_none=True) if caps is not None else None
    ses = getattr(ctx, "session", None)
    for attr in ("client_params", "_client_params", "client_info"):
        v = getattr(ses, attr, None)
        if v is not None:
            d[attr] = v.model_dump(exclude_none=True) if hasattr(v, "model_dump") else str(v)
    rc = getattr(ctx, "request_context", None)
    if rc is not None:
        d["request_meta"] = str(getattr(rc, "meta", None))[:400]
    d["sdk_mcp"] = __import__("importlib.metadata", fromlist=["x"]).version("mcp")
    return d


@server.tool(
    title="Radiografia del cliente MCP",
    description="Devuelve la version del protocolo negociada y las capacidades del cliente. "
                "No toca el disco.",
    annotations=ToolAnnotations(title="Radiografia del cliente MCP",
                                readOnlyHint=True, destructiveHint=False,
                                idempotentHint=True, openWorldHint=False),
    meta={"filex/marca": "cabo1", "filex/version_regla": "R13"},
)
def filex_radiografia(ctx: Context) -> str:
    """Radiografia del cliente."""
    d = _radiografia(ctx)
    log("llamada:filex_radiografia", **d)
    return json.dumps(d, ensure_ascii=False, indent=2, default=str)


@server.tool(
    title="Herramienta DESTRUCTIVA de prueba",
    description="Marcada destructiveHint=true y openWorldHint=true. No hace nada real.",
    annotations=ToolAnnotations(title="Herramienta DESTRUCTIVA de prueba",
                                readOnlyHint=False, destructiveHint=True,
                                idempotentHint=False, openWorldHint=True),
)
def filex_destructiva(objetivo: str, ctx: Context) -> str:
    """Simula una operacion destructiva; no borra nada."""
    log("llamada:filex_destructiva", objetivo=objetivo, **_radiografia(ctx))
    return f"NO se ha borrado nada. objetivo={objetivo}"


@server.tool(
    title="Devuelve una imagen como ImageContent",
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False),
)
def filex_imagen(ctx: Context, ruta: str = ""):
    """Devuelve un PNG como ImageContent nativo del protocolo. Sin ruta, un PNG de 1x1."""
    import base64
    from mcp_types import ImageContent
    if ruta:
        datos = Path(ruta).read_bytes()
        b64 = base64.b64encode(datos).decode()
        mime = "image/png" if ruta.lower().endswith(".png") else "image/jpeg"
    else:
        b64 = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
               "+M9QzwAEYBxVSF44AAAAAElFTkSuQmCC")
        mime = "image/png"
    log("llamada:filex_imagen", ruta=ruta, bytes_b64=len(b64), **_radiografia(ctx))
    return ImageContent(type="image", data=b64, mimeType=mime)


@server.tool(
    title="Salida estructurada",
    annotations=ToolAnnotations(readOnlyHint=True),
    structured_output=True,
)
def filex_estructurada(ctx: Context) -> dict[str, str | int]:
    """Devuelve structuredContent con un outputSchema real."""
    log("llamada:filex_estructurada", **_radiografia(ctx))
    return {"formato": "png", "ancho": 1, "alto": 1, "ruta": "D:/tmp/x.png"}


# ---- Cabo 2: el patron condicional de roots, ejercitado tambien por el cliente real ----

RAICES_INMUTABLES = [os.path.abspath(p) for p in
                     (os.environ.get("FILEX_RAICES", "").split(";")
                      if os.environ.get("FILEX_RAICES") else [os.getcwd()])]


@server.tool(
    title="Roots efectivos (patron condicional R13)",
    annotations=ToolAnnotations(readOnlyHint=True),
)
def filex_roots_efectivos(roots: RootsOpcionales, ctx: Context) -> str:
    """Interseca los roots del cliente con la lista inmutable del servidor; degrada si no hay."""
    r = raices_efectivas(RAICES_INMUTABLES, roots)
    log("llamada:filex_roots_efectivos", resultado=r, **_radiografia(ctx))
    return json.dumps(r, ensure_ascii=False, indent=2, default=str)


@server.resource("filex://cabo1/nota")
def nota() -> str:
    """Un recurso de prueba."""
    log("lectura:recurso")
    return "recurso servido por filex-cabo1"


@server.prompt(title="Prompt de prueba de FileX")
def filex_prompt(tema: str) -> str:
    """Prompt de prueba."""
    log("lectura:prompt", tema=tema)
    return f"Habla de {tema}"


if __name__ == "__main__":
    log("arranque", argv=sys.argv, raices=RAICES_INMUTABLES,
        exe=sys.executable,
        cliente_env={k: v for k, v in os.environ.items()
                     if k.startswith(("CLAUDE", "MCP", "ANTHROPIC"))})
    server.run(transport="stdio")
    log("parada")

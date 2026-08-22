"""Cabo 2 — Servidor de contraste: dependencia DURA vs. patron CONDICIONAL vs. cuerpo."""

import json
import os
import sys
import time
from pathlib import Path
from typing import Annotated

sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.mcpserver import Context, ListRoots, MCPServer, Resolve  # noqa: E402
from mcp_types import ListRootsResult  # noqa: E402

from cabo2_roots import RootsOpcionales, raices_efectivas  # noqa: E402

T0 = time.time()


def log(m):
    print(f"[cabo2srv +{time.time()-T0:7.3f}s] {m}", file=sys.stderr, flush=True)


RAICES = [os.path.abspath(p) for p in
          (os.environ.get("FILEX_RAICES", "").split(";") if os.environ.get("FILEX_RAICES") else [])]

server = MCPServer("filex-cabo2", version="0.0.1")


def pedir_roots_duro() -> ListRoots:
    """Dependencia DURA: siempre devuelve el marcador -> siempre comprueba la capacidad."""
    log("resolver DURO -> marcador ListRoots()")
    return ListRoots()


@server.tool()
def t_dura(roots: Annotated[ListRootsResult, Resolve(pedir_roots_duro)], ctx: Context) -> str:
    """Lo que HOY recomienda el informe: aborta con -32021 si el cliente no declara roots."""
    return json.dumps(raices_efectivas(RAICES, roots), ensure_ascii=False, default=str)


@server.tool()
def t_condicional(roots: RootsOpcionales, ctx: Context) -> str:
    """El patron nuevo: el resolver mira `ctx.client_capabilities` y decide si pregunta."""
    caps = ctx.client_capabilities
    r = raices_efectivas(RAICES, roots)
    r["capacidad_roots_declarada"] = caps is not None and caps.roots is not None
    r["protocolo"] = ctx.protocol_version
    log(f"t_condicional -> {r['modo']}")
    return json.dumps(r, ensure_ascii=False, default=str)


@server.tool()
async def t_cuerpo(ctx: Context) -> str:
    """Control: pedir los roots desde el cuerpo con `session.list_roots()`."""
    caps = ctx.client_capabilities
    if caps is None or caps.roots is None:
        return json.dumps({"modo": "DEGRADADO (sin capacidad)", "efectiva": RAICES,
                           "protocolo": ctx.protocol_version}, ensure_ascii=False)
    try:
        res = await ctx.session.list_roots()
        return json.dumps(raices_efectivas(RAICES, res), ensure_ascii=False, default=str)
    except Exception as e:  # noqa: BLE001
        return json.dumps({"EXCEPCION": type(e).__module__ + "." + type(e).__name__,
                           "repr": repr(e)[:400], "degradado_a": RAICES,
                           "protocolo": ctx.protocol_version}, ensure_ascii=False)


@server.tool()
def t_ping_final() -> str:
    """Comprueba que la sesion sigue viva despues de los intentos anteriores."""
    return "pong"


if __name__ == "__main__":
    log(f"arranque, raices={RAICES}")
    server.run(transport="stdio")

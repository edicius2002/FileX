"""Servidor MCP 2.x con la API alta `MCPServer` + `Resolve(ListRoots)`.

Es el UNICO camino que consigue los roots del cliente en la era moderna
(protocolo 2026-07-28), donde `ServerSession.list_roots()` muere con
NoBackChannelError. El framework traduce solo:
  >= 2026-07-28  -> InputRequiredResult + reintento del cliente
  <= 2025-11-25  -> peticion servidor->cliente a mitad de llamada
"""

import json
import os
import sys
import time
from typing import Annotated
from urllib.parse import urlparse, unquote

from mcp.server.mcpserver import MCPServer, Context, Resolve, ListRoots
from mcp_types import ListRootsResult

T0 = time.time()


def log(m):
    print(f"[srv2r +{time.time()-T0:7.3f}s] {m}", file=sys.stderr, flush=True)


RAICES_SERVIDOR = [os.path.abspath(p) for p in
                   (os.environ.get("FILEX_RAICES", "").split(";") if os.environ.get("FILEX_RAICES") else [])]

server = MCPServer("filex-probe-2x-resolve", version="0.0.1")


def uri_a_ruta(uri: str):
    p = urlparse(uri)
    if p.scheme != "file":
        return None
    ruta = unquote(p.path)
    if os.name == "nt" and len(ruta) > 2 and ruta[0] == "/" and ruta[2] == ":":
        ruta = ruta[1:]
    return os.path.abspath(ruta)


def pedir_roots() -> ListRoots:
    """Resolver: devuelve el marcador; el framework inyecta el ListRootsResult."""
    log("resolver pedir_roots() -> marcador ListRoots")
    return ListRoots()


@server.tool()
def t_roots_resolve(roots: Annotated[ListRootsResult, Resolve(pedir_roots)], ctx: Context) -> str:
    log(f"t_roots_resolve recibio {len(roots.roots)} roots, protocolo={ctx.protocol_version}")
    return json.dumps({"protocolo": ctx.protocol_version,
                       "roots": [{"uri": str(r.uri), "name": r.name} for r in roots.roots]},
                      ensure_ascii=False)


@server.tool()
def t_interseca_resolve(roots: Annotated[ListRootsResult, Resolve(pedir_roots)], ctx: Context) -> str:
    efectiva = []
    for r in roots.roots:
        c = uri_a_ruta(str(r.uri))
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
    return json.dumps({"protocolo": ctx.protocol_version, "servidor": RAICES_SERVIDOR,
                       "cliente": [str(r.uri) for r in roots.roots], "efectiva": efectiva},
                      ensure_ascii=False)


@server.tool()
def t_ping() -> str:
    return "pong"


if __name__ == "__main__":
    log(f"arrancando MCPServer. raices={RAICES_SERVIDOR}")
    server.run(transport="stdio")

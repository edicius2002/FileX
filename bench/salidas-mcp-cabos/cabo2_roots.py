"""Cabo 2 — El patron CONDICIONAL de roots para `mcp>=2.0.0` (regla R13).

Problema medido en `bench/sdk-mcp-capacidades.md` §2.6: declarar
`Annotated[ListRootsResult, Resolve(pedir_roots)]` como dependencia dura **aborta la
llamada entera** con `-32021 MISSING_REQUIRED_CLIENT_CAPABILITY` cuando el cliente no
declara la capacidad `roots`. R13 exige lo contrario: sin roots del cliente se sigue
con la lista inmutable del servidor.

La solucion, leida en `mcp/server/mcpserver/resolve.py:568-575` y demostrada aqui:

    if _is_marker(result):            # ListRoots() / Elicit() / Sample()
        outcome = await _fulfil(...)  # <- aqui, y SOLO aqui, corre _require_capability
    else:
        outcome = _accepted(result)   # <- un valor plano se acepta sin comprobar nada

Es decir: **el resolver decide si pregunta**. Si devuelve el marcador `ListRoots()`
se dispara la comprobacion de capacidad (y el -32021); si devuelve un
`ListRootsResult` ya construido, el framework lo acepta tal cual y no comprueba nada.
El resolver puede recibir el `Context`, asi que puede mirar `ctx.client_capabilities`
antes de decidir.

Resultado: **cero abortos**, y el mismo codigo sirve para las tres eras del protocolo.
"""

from __future__ import annotations

import os
from typing import Annotated
from urllib.parse import unquote, urlparse

from mcp.server.mcpserver import Context, ListRoots, Resolve
from mcp_types import ListRootsResult

# --------------------------------------------------------------------------------------
# 1. El resolver condicional. ESTA es la pieza que faltaba.
# --------------------------------------------------------------------------------------


def roots_o_nada(ctx: Context) -> ListRoots | ListRootsResult:
    """Pide los roots SOLO si el cliente declaro la capacidad; si no, devuelve vacio.

    Devolver el marcador `ListRoots()` hace que el framework lo cumpla por el transporte
    negociado (InputRequiredResult en >=2026-07-28, peticion a mitad de llamada en
    <=2025-11-25). Devolver un `ListRootsResult` construido a mano lo esquiva entero.
    """
    caps = getattr(ctx, "client_capabilities", None)
    if caps is not None and getattr(caps, "roots", None) is not None:
        return ListRoots()
    return ListRootsResult(roots=[])


#: Tipo listo para usar en la firma de una herramienta.
RootsOpcionales = Annotated[ListRootsResult, Resolve(roots_o_nada)]


# --------------------------------------------------------------------------------------
# 2. La interseccion (R13 + R2 + R3). Portada de `srv_1x.py::t_roots_interseca`.
# --------------------------------------------------------------------------------------


def uri_a_ruta(uri: str) -> str | None:
    p = urlparse(uri)
    if p.scheme != "file":
        return None
    ruta = unquote(p.path)
    if os.name == "nt" and len(ruta) > 2 and ruta[0] == "/" and ruta[2] == ":":
        ruta = ruta[1:]
    return os.path.abspath(ruta)


def intersecar(raices_servidor: list[str], raices_cliente: list[str]) -> list[str]:
    """El cliente solo puede ESTRECHAR. Nunca ampliar, nunca sustituir.

    - raiz del cliente contenida en una del servidor -> se queda la del cliente
    - raiz del cliente mas ancha que una del servidor -> se queda la del servidor
    - raiz del cliente disjunta -> se descarta
    """
    efectiva: list[str] = []
    for c in raices_cliente:
        cn = os.path.normcase(os.path.abspath(c))
        for s in raices_servidor:
            sn = os.path.normcase(os.path.abspath(s))
            if cn == sn or cn.startswith(sn + os.sep):
                efectiva.append(os.path.abspath(c))
                break
            if sn.startswith(cn + os.sep):
                efectiva.append(os.path.abspath(s))
                break
    # dedup preservando orden
    vistas, salida = set(), []
    for r in efectiva:
        k = os.path.normcase(r)
        if k not in vistas:
            vistas.add(k)
            salida.append(r)
    return salida


def raices_efectivas(raices_inmutables: list[str], roots: ListRootsResult) -> dict:
    """Aplica R13 con degradacion: sin roots del cliente, la lista del servidor intacta."""
    uris = [str(r.uri) for r in (roots.roots or [])]
    rutas = [p for p in (uri_a_ruta(u) for u in uris) if p]
    if not rutas:
        return {"modo": "DEGRADADO (sin roots del cliente)",
                "servidor": raices_inmutables, "cliente": uris,
                "efectiva": list(raices_inmutables)}
    return {"modo": "INTERSECADO",
            "servidor": raices_inmutables, "cliente": uris,
            "efectiva": intersecar(raices_inmutables, rutas)}

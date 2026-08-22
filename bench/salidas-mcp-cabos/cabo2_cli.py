"""Cabo 2 — Demostracion del patron condicional de roots en los DOS casos.

Lanza `cabo2_srv.py` cuatro veces:
  (modo auto=2026-07-28 / legacy=2025-11-25) x (cliente CON roots / cliente SIN roots)

y en cada una llama a tres herramientas:
  - `t_dura`        : Resolve(ListRoots) como dependencia DURA  -> debe abortar (-32021) sin roots
  - `t_condicional` : el patron nuevo                            -> nunca aborta
  - `t_cuerpo`      : `ctx.session.list_roots()` desde el cuerpo -> control
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import anyio
import mcp.types as types
from mcp.client.client import Client
from mcp.client.stdio import StdioServerParameters, stdio_client


async def prueba(modo: str, con_roots: bool, raices_srv: str, raices_cli: list[str], carpeta: Path):
    t0 = time.time()
    veces = []

    async def list_roots_cb(ctx):
        veces.append(round(time.time() - t0, 3))
        return types.ListRootsResult(
            roots=[types.Root(uri=Path(r).absolute().as_uri(), name=os.path.basename(r))
                   for r in raices_cli])

    env = dict(os.environ)
    env["FILEX_RAICES"] = raices_srv
    params = StdioServerParameters(command=sys.executable,
                                   args=[str(Path(__file__).with_name("cabo2_srv.py"))], env=env)
    etiqueta = f"{modo}_{'conroots' if con_roots else 'sinroots'}"
    errlog = open(carpeta / f"cabo2_stderr_{etiqueta}.txt", "w", encoding="utf-8")
    out = {"modo": modo, "cliente_declara_roots": con_roots, "pasos": []}
    try:
        kw = {"list_roots_callback": list_roots_cb} if con_roots else {}
        async with Client(stdio_client(params, errlog=errlog), mode=modo, **kw) as c:
            out["protocolo_negociado"] = c.protocol_version
            for nombre in ("t_dura", "t_condicional", "t_cuerpo", "t_ping_final"):
                p = {"paso": nombre}
                t1 = time.time()
                try:
                    res = await c.call_tool(nombre, {})
                    p["ms"] = round((time.time() - t1) * 1000, 1)
                    p["isError"] = res.is_error
                    p["contenido"] = [x.model_dump(exclude_none=True) for x in (res.content or [])]
                except Exception as e:  # noqa: BLE001
                    p["ms"] = round((time.time() - t1) * 1000, 1)
                    p["EXCEPCION"] = type(e).__module__ + "." + type(e).__name__
                    p["repr"] = repr(e)[:700]
                out["pasos"].append(p)
            out["veces_que_el_cliente_respondio_roots"] = veces
    except Exception as e:  # noqa: BLE001
        out["EXCEPCION_SESION"] = repr(e)[:800]
    finally:
        errlog.close()
    return out


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raices-servidor", default="")
    ap.add_argument("--roots", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    carpeta = Path(a.out).parent
    raices_cli = [r for r in a.roots.split(";") if r]

    todo = {"sdk_mcp": __import__("importlib.metadata", fromlist=["x"]).version("mcp"),
            "raices_servidor": a.raices_servidor.split(";"),
            "roots_cliente": raices_cli, "resultados": []}
    for modo in ("auto", "legacy"):
        for con_roots in (True, False):
            todo["resultados"].append(
                await prueba(modo, con_roots, a.raices_servidor, raices_cli, carpeta))

    Path(a.out).write_text(json.dumps(todo, ensure_ascii=False, indent=2, default=str),
                           encoding="utf-8")
    print(json.dumps(todo, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    anyio.run(main)

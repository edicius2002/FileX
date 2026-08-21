"""Cliente 2.x contra srv_2x_resolve.py. Compara era moderna (auto) y era clasica (legacy)."""

import anyio
import argparse
import json
import os
import sys
import time
from pathlib import Path

import mcp.types as types
from mcp.client.client import Client
from mcp.client.stdio import StdioServerParameters, stdio_client


async def prueba(modo: str, raices_srv: str, raices_cli: list[str], stderr_path: str):
    t0 = time.time()
    pedidos = []

    async def list_roots_cb(ctx):
        pedidos.append({"t": round(time.time() - t0, 3), "n": len(raices_cli)})
        return types.ListRootsResult(
            roots=[types.Root(uri=Path(r).absolute().as_uri(), name=os.path.basename(r))
                   for r in raices_cli])

    env = dict(os.environ)
    env["FILEX_RAICES"] = raices_srv
    params = StdioServerParameters(command=sys.executable,
                                   args=[str(Path(__file__).with_name("srv_2x_resolve.py"))], env=env)
    errlog = open(stderr_path, "w", encoding="utf-8")
    out = {"modo": modo, "pasos": []}
    try:
        kw = {} if os.environ.get("FILEX_SIN_ROOTS_CLIENTE") == "1" else {
            "list_roots_callback": list_roots_cb}
        async with Client(stdio_client(params, errlog=errlog), mode=modo, **kw) as c:
            out["protocolo_negociado"] = c.protocol_version
            for nombre in ("t_ping", "t_roots_resolve", "t_interseca_resolve"):
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
                    p["repr"] = repr(e)[:600]
                out["pasos"].append(p)
            out["veces_que_el_cliente_respondio_roots"] = pedidos
    except Exception as e:  # noqa: BLE001
        out["EXCEPCION_SESION"] = repr(e)[:800]
    finally:
        errlog.close()
    return out


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raices-servidor", default="")
    ap.add_argument("--roots", default="")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    raices_cli = [r for r in a.roots.split(";") if r]

    todo = {"sdk_mcp": __import__("importlib.metadata", fromlist=["x"]).version("mcp"),
            "resultados": []}
    for modo in ("auto", "legacy"):
        todo["resultados"].append(
            await prueba(modo, a.raices_servidor, raices_cli,
                         str(Path(__file__).with_name(f"stderr_2x_resolve_{modo}.txt"))))

    txt = json.dumps(todo, ensure_ascii=False, indent=2, default=str)
    if a.out:
        Path(a.out).write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    anyio.run(main)

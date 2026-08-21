"""Cliente MCP minimo (rama SDK 2.x) contra srv_2x.py, por stdio."""

import anyio
import argparse
import json
import os
import sys
import time
import warnings
from pathlib import Path

import mcp.types as types
from mcp.client.client import Client
from mcp.client.stdio import StdioServerParameters, stdio_client

SDK_VER = __import__("importlib.metadata", fromlist=["x"]).version("mcp")
AVISOS = []
warnings.simplefilter("always")


def ruta_a_uri(p: str) -> str:
    return Path(p).absolute().as_uri()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", default=None)
    ap.add_argument("--roots-2", default=None)
    ap.add_argument("--raices-servidor", default="")
    ap.add_argument("--stderr", default=None)
    ap.add_argument("--slow", type=float, default=0)
    ap.add_argument("--slow-timeout", type=float, default=0)
    ap.add_argument("--modo", default="auto", help="auto | legacy | 2026-07-28")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    salida = {"sdk_mcp": SDK_VER, "protocolo_cliente": types.LATEST_PROTOCOL_VERSION,
              "modo": a.modo, "argv": sys.argv[1:], "pasos": []}

    raices = [r for r in (a.roots.split(";") if a.roots else []) if r]
    raices_2 = [r for r in (a.roots_2.split(";") if a.roots_2 else []) if r]
    estado = {"actuales": raices}
    veces_pedido = []
    t0 = time.time()

    async def list_roots_cb(ctx):
        veces_pedido.append({"t": round(time.time() - t0, 3), "devuelve": list(estado["actuales"])})
        return types.ListRootsResult(
            roots=[types.Root(uri=ruta_a_uri(r), name=os.path.basename(r) or r) for r in estado["actuales"]])

    env = dict(os.environ)
    env["FILEX_RAICES"] = a.raices_servidor
    params = StdioServerParameters(command=sys.executable,
                                   args=[str(Path(__file__).with_name("srv_2x.py"))], env=env)
    errlog = open(a.stderr, "w", encoding="utf-8") if a.stderr else sys.stderr

    kwargs = {}
    if a.roots is not None:
        kwargs["list_roots_callback"] = list_roots_cb

    with warnings.catch_warnings(record=True) as wlist:
        warnings.simplefilter("always")
        # En 2.x `Client` consume el propio Transport (un async CM), no la tupla de streams.
        transporte = stdio_client(params, errlog=errlog)
        if True:
            async with Client(transporte, mode=a.modo, **kwargs) as c:
                salida["init"] = {
                    "protocolo_negociado": c.protocol_version,
                    "servidor": c.server_info.model_dump() if c.server_info else None,
                    "capacidades_servidor": c.server_capabilities.model_dump(exclude_none=True),
                }
                salida["cliente_declara_roots"] = a.roots is not None
                tools = await c.list_tools()
                salida["tipo_list_tools"] = type(tools).__name__
                lst = getattr(tools, "tools", tools)
                if isinstance(lst, tuple):
                    lst = lst[0]
                salida["herramientas"] = [getattr(t, "name", str(t)) for t in lst]

                async def paso(nombre, coro, **kw):
                    p = {"paso": nombre}
                    t1 = time.time()
                    try:
                        res = await coro
                        p["ms"] = round((time.time() - t1) * 1000, 1)
                        p["isError"] = getattr(res, "is_error", None)
                        cont = getattr(res, "content", []) or []
                        p["contenido"] = [x.model_dump(exclude_none=True, by_alias=False) for x in cont]
                        for x in p["contenido"]:
                            if isinstance(x.get("data"), str) and len(x["data"]) > 120:
                                x["data_len"] = len(x["data"])
                                x["data"] = x["data"][:60] + "...[recortado]"
                    except Exception as e:  # noqa: BLE001
                        p["ms"] = round((time.time() - t1) * 1000, 1)
                        p["EXCEPCION"] = type(e).__module__ + "." + type(e).__name__
                        p["repr"] = repr(e)[:600]
                    salida["pasos"].append(p)
                    return p

                await paso("t_ping", c.call_tool("t_ping", {}))
                await paso("t_roots_cap", c.call_tool("t_roots_cap", {}))
                await paso("t_roots", c.call_tool("t_roots", {}))
                await paso("t_roots_interseca", c.call_tool("t_roots_interseca", {}))

                if raices_2:
                    estado["actuales"] = raices_2
                    try:
                        await c.send_roots_list_changed()
                        salida["list_changed_enviada"] = True
                    except Exception as e:  # noqa: BLE001
                        salida["list_changed_enviada"] = repr(e)
                    await anyio.sleep(0.4)
                    await paso("t_eventos_tras_list_changed", c.call_tool("t_eventos", {}))
                    await paso("t_roots_tras_cambio", c.call_tool("t_roots", {}))

                for modo in ("puro", "prefijo", "basura", "vacio", "nomime"):
                    await paso(f"t_img_{modo}", c.call_tool("t_img", {"mode": modo}))

                if a.slow:
                    await paso("t_slow", c.call_tool("t_slow", {"seconds": a.slow}))

                salida["roots_list_pedidos_por_el_servidor"] = veces_pedido
                salida["tasks_en_types"] = hasattr(types, "CreateTaskResult")
                salida["capacidad_tasks_servidor"] = getattr(c.server_capabilities, "tasks", "<sin campo>")
        AVISOS.extend(f"{x.category.__name__}: {x.message}" for x in wlist)

    salida["avisos_cliente"] = AVISOS
    if errlog is not sys.stderr:
        errlog.close()
    txt = json.dumps(salida, ensure_ascii=False, indent=2, default=str)
    if a.out:
        Path(a.out).write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    anyio.run(main)

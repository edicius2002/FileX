"""Matriz de interoperabilidad ENTRE PROCESOS: cliente en un venv, servidor en otro.

Es la pregunta que le importa a FileX: FileX entrega un SERVIDOR; el cliente
(Claude Desktop/Code, un IDE...) trae SU propia version del SDK. La restriccion
real no es "1.8 y 2.0 no conviven en un venv" (ya medido), sino que version del
protocolo se negocia y que capacidades sobreviven.

Se ejecuta con el python del CLIENTE y se le pasa el python del SERVIDOR.
"""

import anyio
import argparse
import json
import os
import sys
import time
from pathlib import Path

SDK = __import__("importlib.metadata", fromlist=["x"]).version("mcp")
RAMA = "2x" if SDK.startswith("2.") else "1x"


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-python", required=True)
    ap.add_argument("--server-script", required=True)
    ap.add_argument("--etiqueta", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    out = {"etiqueta": a.etiqueta, "sdk_cliente": SDK, "rama_cliente": RAMA,
           "server_script": a.server_script}
    env = dict(os.environ)
    env["FILEX_RAICES"] = str(Path(__file__).with_name("raiz_srv"))
    errlog = open(Path(__file__).with_name(f"stderr_interop_{a.etiqueta}.txt"), "w", encoding="utf-8")

    try:
        if RAMA == "1x":
            import mcp.types as types
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            async def cb(ctx):
                return types.ListRootsResult(roots=[])

            params = StdioServerParameters(command=a.server_python, args=[a.server_script], env=env)
            async with stdio_client(params, errlog=errlog) as (r, w):
                async with ClientSession(r, w, list_roots_callback=cb) as s:
                    init = await s.initialize()
                    out["protocolo_negociado"] = init.protocolVersion
                    out["servidor"] = init.serverInfo.model_dump()
                    out["capacidades_servidor"] = init.capabilities.model_dump(exclude_none=True)
                    t = await s.list_tools()
                    out["n_herramientas"] = len(t.tools)
                    r1 = await s.call_tool("t_ping", {})
                    out["t_ping"] = r1.content[0].text
        else:
            import mcp.types as types
            from mcp.client.client import Client
            from mcp.client.stdio import StdioServerParameters, stdio_client

            async def cb(ctx):
                return types.ListRootsResult(roots=[])

            params = StdioServerParameters(command=a.server_python, args=[a.server_script], env=env)
            async with Client(stdio_client(params, errlog=errlog), mode="auto",
                              list_roots_callback=cb) as c:
                out["protocolo_negociado"] = c.protocol_version
                out["servidor"] = c.server_info.model_dump() if c.server_info else None
                out["capacidades_servidor"] = c.server_capabilities.model_dump(exclude_none=True)
                t = await c.list_tools()
                out["n_herramientas"] = len(getattr(t, "tools", t))
                r1 = await c.call_tool("t_ping", {})
                out["t_ping"] = r1.content[0].text
    except Exception as e:  # noqa: BLE001
        out["EXCEPCION"] = type(e).__module__ + "." + type(e).__name__
        out["repr"] = repr(e)[:900]
    finally:
        errlog.close()

    print(json.dumps(out, ensure_ascii=False, default=str))
    if a.out:
        Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    anyio.run(main)

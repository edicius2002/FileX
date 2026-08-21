"""Cliente MCP minimo (rama SDK 1.x) contra srv_1x.py, por stdio.

Modos de roots:
  --roots RUTA1;RUTA2   declara la capacidad roots y responde roots/list con esas rutas
  (sin --roots)         NO pasa list_roots_callback

Escribe un JSON con todo lo observado a stdout; el stderr del servidor va a --stderr FICH.
"""

import anyio
import argparse
import json
import os
import sys
import time
import traceback
from datetime import timedelta
from pathlib import Path

import mcp.types as types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SDK_VER = __import__("importlib.metadata", fromlist=["x"]).version("mcp")


def ruta_a_uri(p: str) -> str:
    return Path(p).absolute().as_uri()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", default=None)
    ap.add_argument("--roots-2", default=None, help="segunda lista, para probar list_changed")
    ap.add_argument("--raices-servidor", default="")
    ap.add_argument("--stderr", default=None)
    ap.add_argument("--slow", type=float, default=0)
    ap.add_argument("--slow-timeout", type=float, default=0, help="timeout de la llamada larga, s")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    salida = {"sdk_mcp": SDK_VER, "protocolo_cliente": types.LATEST_PROTOCOL_VERSION,
              "argv": sys.argv[1:], "pasos": []}

    raices = [r for r in (a.roots.split(";") if a.roots else []) if r]
    raices_2 = [r for r in (a.roots_2.split(";") if a.roots_2 else []) if r]
    estado = {"actuales": raices}
    veces_pedido = []

    async def list_roots_cb(ctx):
        veces_pedido.append({"t": round(time.time() - t0, 3), "devuelve": list(estado["actuales"])})
        return types.ListRootsResult(
            roots=[types.Root(uri=ruta_a_uri(r), name=os.path.basename(r) or r)
                   for r in estado["actuales"]])

    progresos = []

    async def progress_cb(progress: float, total: float | None, message: str | None = None):
        progresos.append({"t": round(time.time() - t0, 3), "progress": progress,
                          "total": total, "message": message})

    env = dict(os.environ)
    env["FILEX_RAICES"] = a.raices_servidor
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(Path(__file__).with_name("srv_1x.py"))],
        env=env,
    )

    t0 = time.time()
    errlog = open(a.stderr, "w", encoding="utf-8") if a.stderr else sys.stderr

    kwargs = {}
    if a.roots is not None:
        kwargs["list_roots_callback"] = list_roots_cb

    async with stdio_client(params, errlog=errlog) as (r, w):
        async with ClientSession(r, w, **kwargs) as s:
            init = await s.initialize()
            salida["init"] = {
                "protocolo_negociado": init.protocolVersion,
                "servidor": init.serverInfo.model_dump(),
                "capacidades_servidor": init.capabilities.model_dump(exclude_none=True),
            }
            # que capacidades DECLARO el cliente
            salida["cliente_declara_roots"] = a.roots is not None

            tools = await s.list_tools()
            salida["herramientas"] = [t.name for t in tools.tools]

            async def paso(nombre, coro):
                p = {"paso": nombre}
                t1 = time.time()
                try:
                    res = await coro
                    p["ms"] = round((time.time() - t1) * 1000, 1)
                    p["isError"] = getattr(res, "isError", None)
                    p["contenido"] = [c.model_dump(exclude_none=True) for c in getattr(res, "content", [])]
                    # recortar base64 largo
                    for c in p["contenido"]:
                        for k in ("data",):
                            if k in c and isinstance(c[k], str) and len(c[k]) > 120:
                                c[k + "_len"] = len(c[k])
                                c[k] = c[k][:60] + "...[recortado]"
                except Exception as e:  # noqa: BLE001
                    p["ms"] = round((time.time() - t1) * 1000, 1)
                    p["EXCEPCION"] = type(e).__module__ + "." + type(e).__name__
                    p["repr"] = repr(e)[:600]
                salida["pasos"].append(p)
                return p

            await paso("t_ping", s.call_tool("t_ping", {}))
            await paso("t_roots_cap", s.call_tool("t_roots_cap", {}))
            await paso("t_roots", s.call_tool("t_roots", {}))
            await paso("t_roots_interseca", s.call_tool("t_roots_interseca", {}))

            # cambio de roots + notificacion list_changed
            if raices_2:
                estado["actuales"] = raices_2
                try:
                    await s.send_roots_list_changed()
                    salida["list_changed_enviada"] = True
                except Exception as e:  # noqa: BLE001
                    salida["list_changed_enviada"] = repr(e)
                await anyio.sleep(0.4)
                await paso("t_eventos_tras_list_changed", s.call_tool("t_eventos", {}))
                await paso("t_roots_tras_cambio", s.call_tool("t_roots", {}))

            # ImageContent
            for modo in ("puro", "prefijo", "basura", "vacio", "nomime"):
                await paso(f"t_img_{modo}", s.call_tool("t_img", {"mode": modo}))

            # operacion larga
            if a.slow:
                kw = {}
                to = timedelta(seconds=a.slow_timeout) if a.slow_timeout else None
                try:
                    p = await paso("t_slow_con_progreso", s.call_tool(
                        "t_slow", {"seconds": a.slow, "progress": True},
                        read_timeout_seconds=to, progress_callback=progress_cb))
                except TypeError as e:
                    # 1.8.1 no tiene progress_callback
                    salida["progress_callback_soportado"] = False
                    salida["progress_callback_error"] = repr(e)
                    await paso("t_slow_sin_progreso", s.call_tool(
                        "t_slow", {"seconds": a.slow, "progress": True},
                        read_timeout_seconds=to))
                else:
                    salida["progress_callback_soportado"] = True

                # el mismo trabajo con timeout MENOR que la duracion: reproduce el fallo de 9.4
                salida["progresos_fase1"] = list(progresos)
                progresos.clear()
                corto = max(1.0, a.slow / 3)
                salida["timeout_corto_s"] = corto
                await paso("t_slow_timeout_corto", s.call_tool(
                    "t_slow", {"seconds": a.slow, "progress": True},
                    read_timeout_seconds=timedelta(seconds=corto),
                    **({"progress_callback": progress_cb} if salida.get("progress_callback_soportado") else {})))
                salida["progresos_fase2_tras_timeout"] = list(progresos)
                # la sesion, ¿sobrevive al timeout?
                await paso("t_ping_tras_timeout", s.call_tool("t_ping", {}))
                # ¿sigue el servidor trabajando en el t_slow abandonado?
                await anyio.sleep(a.slow)
                await paso("t_ping_tras_esperar_a_que_acabe", s.call_tool("t_ping", {}))

            salida["progresos_recibidos"] = progresos
            salida["roots_list_pedidos_por_el_servidor"] = veces_pedido

            # capacidades tasks?
            salida["tasks_en_types"] = hasattr(types, "CreateTaskResult")
            salida["capacidad_tasks_servidor"] = getattr(init.capabilities, "tasks", "<sin campo>")

    if errlog is not sys.stderr:
        errlog.close()

    txt = json.dumps(salida, ensure_ascii=False, indent=2, default=str)
    if a.out:
        Path(a.out).write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    anyio.run(main)

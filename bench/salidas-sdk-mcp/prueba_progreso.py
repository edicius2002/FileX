"""Mide si `notifications/progress` mantiene VIVA una llamada larga. Rama 2.x.

Dos fases contra srv_2x.py:
  A) t_slow(D) con timeout > D           -> ¿llegan progresos? ¿acaba bien?
  B) t_slow(D) con timeout << D          -> ¿el progreso empuja el plazo, o vence igual?
Y la pregunta que decide el hito 4: tras el timeout, ¿que ve el cliente del trabajo hecho?
"""

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


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dur", type=float, default=30)
    ap.add_argument("--timeout-largo", type=float, default=45)
    ap.add_argument("--timeout-corto", type=float, default=10)
    ap.add_argument("--modo", default="auto")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    t0 = time.time()
    progresos = []

    async def progress_cb(progress, total, message=None):
        progresos.append({"t": round(time.time() - t0, 3), "progress": progress,
                          "total": total, "message": message})

    env = dict(os.environ)
    params = StdioServerParameters(command=sys.executable,
                                   args=[str(Path(__file__).with_name("srv_2x.py"))], env=env)
    errlog = open(Path(__file__).with_name(f"stderr_progreso_{a.modo}.txt"), "w", encoding="utf-8")
    out = {"sdk_mcp": __import__("importlib.metadata", fromlist=["x"]).version("mcp"),
           "modo": a.modo, "dur": a.dur, "fases": []}

    async with Client(stdio_client(params, errlog=errlog), mode=a.modo) as c:
        out["protocolo_negociado"] = c.protocol_version

        async def fase(nombre, timeout):
            progresos.clear()
            f = {"fase": nombre, "timeout_s": timeout}
            t1 = time.time()
            try:
                res = await c.call_tool("t_slow", {"seconds": a.dur},
                                        read_timeout_seconds=timeout,
                                        progress_callback=progress_cb)
                f["ms"] = round((time.time() - t1) * 1000, 1)
                f["resultado"] = [x.model_dump(exclude_none=True) for x in (res.content or [])]
            except Exception as e:  # noqa: BLE001
                f["ms"] = round((time.time() - t1) * 1000, 1)
                f["EXCEPCION"] = type(e).__module__ + "." + type(e).__name__
                f["repr"] = repr(e)[:400]
            f["n_progresos"] = len(progresos)
            f["primeros"] = progresos[:2]
            f["ultimos"] = progresos[-2:]
            out["fases"].append(f)

        await fase("A_timeout_largo", a.timeout_largo)
        await fase("B_timeout_corto", a.timeout_corto)

        # ¿sobrevive la sesion? ¿se puede recuperar el resultado abandonado?
        p = {"fase": "C_ping_tras_timeout"}
        t1 = time.time()
        try:
            r = await c.call_tool("t_ping", {}, read_timeout_seconds=10)
            p["ok"] = True
            p["ms"] = round((time.time() - t1) * 1000, 1)
        except Exception as e:  # noqa: BLE001
            p["ok"] = False
            p["repr"] = repr(e)[:300]
        out["fases"].append(p)
        out["hay_api_para_recuperar_el_resultado_abandonado"] = any(
            "task" in n.lower() or "resume" in n.lower() for n in dir(c))
        out["metodos_client_con_task_o_resume"] = [n for n in dir(c)
                                                   if "task" in n.lower() or "resume" in n.lower()]

    errlog.close()
    txt = json.dumps(out, ensure_ascii=False, indent=2, default=str)
    if a.out:
        Path(a.out).write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    anyio.run(main)

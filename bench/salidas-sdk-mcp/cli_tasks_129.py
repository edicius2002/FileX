"""Cliente que ejerce Tasks (SEP-1686) contra srv_tasks_129.py. Solo mcp 1.2x."""

import anyio
import argparse
import json
import os
import sys
import time
import warnings
from datetime import timedelta
from pathlib import Path

import mcp.types as types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

AVISOS = []


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dur", type=float, default=30)
    ap.add_argument("--timeout", type=float, default=10, help="timeout CORTO, menor que --dur")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    out = {"sdk_mcp": __import__("importlib.metadata", fromlist=["x"]).version("mcp"),
           "dur": a.dur, "timeout_cliente_s": a.timeout, "pasos": []}
    t0 = time.time()
    params = StdioServerParameters(command=sys.executable,
                                   args=[str(Path(__file__).with_name("srv_tasks_129.py"))],
                                   env=dict(os.environ))
    errlog = open(Path(__file__).with_name("stderr_tasks_129.txt"), "w", encoding="utf-8")

    with warnings.catch_warnings(record=True) as wl:
        warnings.simplefilter("always")
        async with stdio_client(params, errlog=errlog) as (r, w):
            async with ClientSession(r, w) as s:
                init = await s.initialize()
                out["protocolo_negociado"] = init.protocolVersion
                out["capacidad_tasks_servidor"] = (
                    init.capabilities.tasks.model_dump(exclude_none=True)
                    if getattr(init.capabilities, "tasks", None) else None)
                tools = await s.list_tools()
                out["herramientas"] = [
                    {"name": t.name, "execution": (t.execution.model_dump(exclude_none=True)
                                                   if getattr(t, "execution", None) else None)}
                    for t in tools.tools]

                # 1) llamada normal con timeout CORTO: falla, se pierde el resultado
                p = {"paso": "bloqueante_timeout_corto"}
                t1 = time.time()
                try:
                    await s.call_tool("convertir_largo", {"seconds": a.dur},
                                      read_timeout_seconds=timedelta(seconds=a.timeout))
                    p["ok"] = True
                except Exception as e:  # noqa: BLE001
                    p["EXCEPCION"] = type(e).__name__
                    p["repr"] = repr(e)[:300]
                p["ms"] = round((time.time() - t1) * 1000, 1)
                out["pasos"].append(p)

                # 2) la MISMA herramienta como TAREA, con el MISMO timeout corto
                p = {"paso": "como_tarea_mismo_timeout_corto"}
                t1 = time.time()
                cr = await s.experimental.call_tool_as_task(
                    "convertir_largo", {"seconds": a.dur}, ttl=int((a.dur + 60) * 1000))
                p["ms_hasta_el_asa"] = round((time.time() - t1) * 1000, 1)
                task_id = cr.task.taskId
                p["taskId"] = task_id
                p["status_inicial"] = cr.task.status
                p["pollInterval"] = cr.task.pollInterval
                out["pasos"].append(p)

                # 3) sondeo
                estados = []
                t2 = time.time()
                while time.time() - t2 < a.dur + 30:
                    st = await s.experimental.get_task(task_id)
                    estados.append({"t": round(time.time() - t0, 2), "status": st.status,
                                    "msg": st.statusMessage})
                    if st.status in ("completed", "failed", "cancelled"):
                        break
                    await anyio.sleep(2)
                out["estados_sondeados"] = estados[:4] + (["..."] if len(estados) > 6 else []) + estados[-2:]
                out["n_sondeos"] = len(estados)

                # 4) recoger el resultado
                p = {"paso": "tasks_result"}
                try:
                    final = await s.experimental.get_task_result(task_id, types.CallToolResult)
                    p["isError"] = final.isError
                    p["contenido"] = [c.model_dump(exclude_none=True) for c in final.content]
                except Exception as e:  # noqa: BLE001
                    p["EXCEPCION"] = repr(e)[:300]
                out["pasos"].append(p)

                # 5) cancelacion de una tarea nueva
                cr2 = await s.experimental.call_tool_as_task(
                    "convertir_largo", {"seconds": a.dur}, ttl=int((a.dur + 60) * 1000))
                await anyio.sleep(1)
                p = {"paso": "tasks_cancel", "taskId": cr2.task.taskId}
                try:
                    can = await s.experimental.cancel_task(cr2.task.taskId)
                    p["status_tras_cancelar"] = can.status
                except Exception as e:  # noqa: BLE001
                    p["EXCEPCION"] = repr(e)[:300]
                out["pasos"].append(p)

                # 6) listado
                try:
                    lst = await s.experimental.list_tasks()
                    out["tasks_list"] = [{"taskId": t.taskId, "status": t.status} for t in lst.tasks]
                except Exception as e:  # noqa: BLE001
                    out["tasks_list"] = repr(e)[:300]

    AVISOS.extend(f"{x.category.__name__}: {x.message}" for x in wl)
    out["avisos"] = sorted(set(AVISOS))
    errlog.close()
    txt = json.dumps(out, ensure_ascii=False, indent=2, default=str)
    if a.out:
        Path(a.out).write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    anyio.run(main)

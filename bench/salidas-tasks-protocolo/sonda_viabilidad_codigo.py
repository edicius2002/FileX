"""¿Se pueden servir `tasks/*` A MANO sobre `mcp 2.0.0`?

`mcp 2.0.0` no trae el mecanismo (ver `sonda_tasks.json` S2). La pregunta que
decide el coste en CODIGO es si el `Server` de bajo nivel deja registrar metodos
arbitrarios, o si haria falta bifurcar el SDK. Se sondea EJECUTANDO.

    .venv-mcp-filex\\Scripts\\python.exe bench/salidas-tasks-protocolo/sonda_viabilidad_codigo.py
"""

import inspect
import json
import os

R = {}

import mcp.types as t                                             # noqa: E402
from mcp.server.lowlevel import Server                            # noqa: E402

srv = Server("sonda-viabilidad")

# ------------------------------------------- V1. ¿existe un registro abierto?
v1 = {}
for m in ("add_request_handler", "add_notification_handler", "get_request_handler"):
    f = getattr(srv, m, None)
    v1[m] = str(inspect.signature(f)) if f else "AUSENTE"
v1["manejadores_de_serie"] = sorted(str(k) for k in srv._request_handlers)
R["V1_registro"] = v1

# ------------------------------- V2. ¿acepta un metodo del SEP que no conoce?
v2 = {}


async def manejador_falso(ctx, params):
    return t.GetTaskResult(taskId="x", status="working")


# La firma real es (method, params_type, handler): el registro es ABIERTO y
# pide el tipo de parametros, que en 2025-11-25 existe para los cuatro metodos.
PARAMS = {
    "tasks/get": getattr(t, "GetTaskRequestParams", None),
    "tasks/result": getattr(t, "GetTaskPayloadRequestParams", None),
    "tasks/list": getattr(t, "PaginatedRequestParams", None),
    "tasks/cancel": getattr(t, "CancelTaskRequestParams", None),
}
for metodo, ptipo in PARAMS.items():
    if ptipo is None:
        v2[metodo] = "SIN TIPO DE PARAMS en mcp.types"
        continue
    try:
        srv.add_request_handler(metodo, ptipo, manejador_falso)
        v2[metodo] = "REGISTRADO con %s" % ptipo.__name__
    except Exception as e:
        v2[metodo] = "%s: %s" % (type(e).__name__, e)
v2["manejadores_tras_registrar"] = sorted(str(k) for k in srv._request_handlers)
R["V2_registro_de_tasks"] = v2

# --------------------- V3. ¿anuncia el servidor la capacidad `tasks` al init?
v3 = {}
try:
    opts = srv.create_initialization_options()
    caps = opts.capabilities
    d = caps.model_dump(exclude_none=True, by_alias=True)
    v3["capacidades_emitidas"] = d
    v3["tasks_en_capacidades"] = "tasks" in d
    v3["protocolo_de_las_opciones"] = getattr(opts, "protocol_version", "n/a")
except Exception as e:
    v3["error"] = "%s: %s" % (type(e).__name__, e)
R["V3_capacidades"] = v3

# ------------- V4. ¿validan los tipos 2025-11-25 lo que habria que devolver?
v4 = {}
try:
    tk = t.Task(taskId="t-1", status="working", createdAt="2026-09-04T00:00:00Z",
                ttl=60000, pollInterval=1000)
    v4["Task"] = tk.model_dump(exclude_none=True, by_alias=True)
except Exception as e:
    v4["Task"] = "%s: %s" % (type(e).__name__, e)
try:
    v4["campos_Task"] = sorted(t.Task.model_fields)
    v4["campos_CreateTaskResult"] = sorted(t.CreateTaskResult.model_fields)
    v4["TaskStatus"] = str(t.TaskStatus)
except Exception as e:
    v4["campos"] = str(e)
R["V4_tipos"] = v4

# ------- V5. ¿que le pasa a `tasks` si el servidor habla la era 2026-07-28?
v5 = {}
try:
    import mcp_types._v2026_07_28 as v26
    v5["ServerCapabilities_2026_tiene_tasks"] = "tasks" in v26.ServerCapabilities.model_fields
    v5["campo_nuevo_extensions"] = "extensions" in v26.ServerCapabilities.model_fields
    # ¿se puede construir una capacidad de tareas en esa era?
    try:
        v26.ServerCapabilities(tasks={"list": {}})
        v5["construir_con_tasks"] = "ACEPTADO (campo ignorado o extra)"
    except Exception as e:
        v5["construir_con_tasks"] = "%s: %s" % (type(e).__name__, str(e)[:200])
except Exception as e:
    v5["error"] = str(e)
R["V5_era_2026"] = v5

sal = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "sonda_viabilidad_codigo.json")
with open(sal, "w", encoding="utf-8") as f:
    json.dump(R, f, indent=2, ensure_ascii=False, default=str)
print(json.dumps(R, indent=2, ensure_ascii=False, default=str))
print("\n-> %s" % sal)

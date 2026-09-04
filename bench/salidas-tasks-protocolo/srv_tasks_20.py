"""Servidor `mcp 2.0.0` que sirve `tasks/*` A MANO, sin el mecanismo retirado.

Es la prueba de que «registrable» y «servido» no son lo mismo: se sondea
ejecutando. NO es codigo de producto y no vive en `filex/`.

Lo lanza `cli_tasks_20.py` por stdio.
"""

import anyio
import mcp.types as t
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

TAREAS = {}


async def on_list_tools(ctx, params):
    return t.ListToolsResult(tools=[t.Tool(
        name="convertir_lento",
        description="Sonda: simula una conversion larga.",
        inputSchema={"type": "object", "properties": {}},
    )])


async def on_call_tool(ctx, params):
    return t.CallToolResult(content=[t.TextContent(type="text", text="hecho")])


async def tasks_get(ctx, params):
    tid = getattr(params, "task_id", None) or getattr(params, "taskId", "?")
    tarea = TAREAS.setdefault(tid, t.Task(
        taskId=tid, status="working",
        createdAt="2026-09-04T00:00:00Z",
        lastUpdatedAt="2026-09-04T00:00:00Z",
        ttl=60000, pollInterval=1000))
    return t.GetTaskResult(**tarea.model_dump(by_alias=True, exclude_none=True))


async def tasks_cancel(ctx, params):
    tid = getattr(params, "task_id", None) or getattr(params, "taskId", "?")
    return t.CancelTaskResult(
        taskId=tid, status="cancelled",
        createdAt="2026-09-04T00:00:00Z",
        lastUpdatedAt="2026-09-04T00:00:01Z",
        ttl=60000, pollInterval=1000)


async def tasks_list(ctx, params):
    return t.ListTasksResult(tasks=list(TAREAS.values()))


def construir():
    srv = Server("sonda-tasks-20", version="0.0.1",
                 on_list_tools=on_list_tools, on_call_tool=on_call_tool)
    srv.add_request_handler("tasks/get", t.GetTaskRequestParams, tasks_get)
    srv.add_request_handler("tasks/cancel", t.CancelTaskRequestParams, tasks_cancel)
    srv.add_request_handler("tasks/list", t.PaginatedRequestParams, tasks_list)
    return srv


async def _correr():
    srv = construir()
    async with stdio_server() as (lectura, escritura):
        await srv.run(lectura, escritura, srv.create_initialization_options())


if __name__ == "__main__":
    anyio.run(_correr)

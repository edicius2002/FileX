"""Servidor MCP con Tasks (SEP-1686) EXPERIMENTAL, solo mcp 1.2x.

Demuestra el patron que la regla 9.4 de FileX pide: la llamada devuelve un asa
(taskId) INMEDIATAMENTE y el trabajo sigue en segundo plano. El cliente sondea.

En mcp 2.0.0 este modulo no existe: `mcp.server.experimental` fue eliminado.
"""

import anyio
import sys
import time

import mcp.types as types
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.experimental.task_context import ServerTaskContext
import mcp.server.stdio

T0 = time.time()


def log(m):
    print(f"[tsk +{time.time()-T0:7.3f}s] {m}", file=sys.stderr, flush=True)


server = Server("filex-tasks-129")
soporte = server.experimental.enable_tasks()   # store + queue en memoria


@server.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="convertir_largo",
            description="simula una conversion de N segundos",
            inputSchema={"type": "object", "properties": {"seconds": {"type": "number"}},
                         "required": ["seconds"]},
            # declara que la herramienta ADMITE ejecucion como tarea
            execution=types.ToolExecution(taskSupport="optional")
            if hasattr(types, "ToolExecution") else None,
        ),
    ]


@server.call_tool()
async def call_tool(name: str, args: dict):
    ctx = server.request_context
    secs = float(args.get("seconds", 10))

    # ¿pidio el cliente ejecucion como tarea? (params.task presente)
    meta_tarea = getattr(ctx, "experimental", None)
    pide_tarea = False
    try:
        pide_tarea = ctx.experimental.task_metadata is not None
    except Exception:  # noqa: BLE001
        pass
    log(f"call_tool {name} secs={secs} pide_tarea={pide_tarea}")

    if not pide_tarea:
        await anyio.sleep(secs)
        return [types.TextContent(type="text", text=f"bloqueante, {secs}s")]

    async def trabajo(task: ServerTaskContext) -> types.CallToolResult:
        log("trabajo de fondo arrancado")
        pasos = max(1, int(secs))
        for i in range(pasos):
            await anyio.sleep(secs / pasos)
            await task.update_status(f"paso {i+1}/{pasos}")
        log("trabajo de fondo terminado")
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"convertido en {secs}s")])

    res = await ctx.experimental.run_task(trabajo)
    log(f"run_task devolvio inmediatamente: taskId={res.task.taskId}")
    return res


async def main():
    opts = InitializationOptions(
        server_name="filex-tasks-129", server_version="0.0.1",
        capabilities=server.get_capabilities(NotificationOptions(), {}),
    )
    log("arrancando")
    async with mcp.server.stdio.stdio_server() as (r, w):
        await server.run(r, w, opts, raise_exceptions=False)


if __name__ == "__main__":
    anyio.run(main)

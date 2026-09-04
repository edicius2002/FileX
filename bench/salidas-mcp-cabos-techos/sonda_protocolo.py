"""Ítem 2 de C36 — qué pasa con `roots` en el protocolo 2026-07-28.

Sonda EJECUTABLE contra el SDK instalado. No lee especificación: ejecuta.
Lo que sólo se lea queda PENDIENTE en el informe, nunca aquí.

    .venv-mcp-filex/Scripts/python.exe bench/salidas-mcp-cabos-techos/sonda_protocolo.py
"""
from __future__ import annotations

import json
import os
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "protocolo.json")


def main() -> int:
    r: dict = {"interprete": sys.version, "plataforma": sys.platform}

    import importlib.metadata as md
    r["mcp_version"] = md.version("mcp")
    try:
        r["mcp_types_version"] = md.version("mcp-types")
    except Exception as e:                                    # pragma: no cover
        r["mcp_types_version"] = f"ERROR: {e!r}"

    from mcp_types.version import (KNOWN_PROTOCOL_VERSIONS,
                                   LATEST_PROTOCOL_VERSION,
                                   SUPPORTED_PROTOCOL_VERSIONS)
    r["versiones_conocidas"] = list(KNOWN_PROTOCOL_VERSIONS)
    r["version_ultima"] = LATEST_PROTOCOL_VERSION
    r["versiones_soportadas"] = list(SUPPORTED_PROTOCOL_VERSIONS)

    # --- 1. ¿`session.list_roots` está deprecado, y con qué texto? ----------
    from mcp.server.session import ServerSession
    f = ServerSession.list_roots
    r["list_roots_deprecado"] = bool(getattr(f, "__deprecated__", None))
    r["list_roots_texto"] = getattr(f, "__deprecated__", None)

    # --- 2. ¿El servidor de FileX, TAL COMO SE CONSTRUYE HOY, avisa? --------
    # Ésta es la celda que importa: no mide el SDK, mide a FileX.
    from filex import mcp as M
    from filex.nucleo import FileX
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        srv, _svc, _rz = M.construir(FileX(), None)
        avisos = [{"categoria": type(x.message).__name__, "texto": str(x.message)}
                  for x in w]
    r["avisos_al_construir_filex"] = avisos
    r["n_avisos_al_construir_filex"] = len(avisos)

    # --- 3. Control negativo: construir SIN el manejador de roots ----------
    # Si esto también avisa, el aviso no es del manejador y la atribución
    # de arriba sería falsa (trampa 111: la sonda lleva dentro su refutación).
    import mcp.types as t
    from mcp.server.lowlevel import Server
    with warnings.catch_warnings(record=True) as w2:
        warnings.simplefilter("always")

        async def _lt(ctx, params):
            return t.ListToolsResult(tools=[])

        Server("control", version="0", on_list_tools=_lt)
        r["avisos_control_sin_roots"] = [str(x.message) for x in w2]
    r["n_avisos_control_sin_roots"] = len(r["avisos_control_sin_roots"])

    # --- 4. ¿Qué capacidades declara el servidor de FileX? -----------------
    try:
        op = srv.create_initialization_options()
        caps = op.capabilities
        r["capacidades_servidor"] = json.loads(caps.model_dump_json(
            exclude_none=True)) if hasattr(caps, "model_dump_json") else str(caps)
    except Exception as e:
        r["capacidades_servidor"] = f"ERROR: {e!r}"

    # --- 5. ¿Sigue existiendo `ListRoots` como marcador de resolver? -------
    try:
        from mcp.server.mcpserver import ListRoots, Resolve
        r["ListRoots_existe"] = True
        r["ListRoots_doc"] = (ListRoots.__doc__ or "").strip()
        r["Resolve_doc"] = (Resolve.__doc__ or "").strip()
        r["ListRoots_deprecado"] = bool(getattr(ListRoots, "__deprecated__", None))
    except Exception as e:
        r["ListRoots_existe"] = False
        r["ListRoots_error"] = repr(e)

    # --- 6. El transporte por versión, tal como lo documenta el SDK --------
    import mcp.server.mcpserver.resolve as _res
    r["resolve_docstring"] = (_res.__doc__ or "").strip()

    # --- 7. ¿`roots` sigue siendo una capacidad declarable del CLIENTE? ----
    try:
        from mcp_types import ClientCapabilities
        r["campos_ClientCapabilities"] = sorted(
            ClientCapabilities.model_fields.keys())
    except Exception as e:
        r["campos_ClientCapabilities"] = f"ERROR: {e!r}"

    # --- 8. Tasks (SEP-1686): `PLAN-ORQUESTADOR.md` §5.3 lo da por ELIMINADO
    # de la especificación, y sobre eso se justificó construir el `job_id` a
    # mano. Se comprueba contra el SDK, no contra el recuerdo.
    try:
        from mcp_types import ServerCapabilities
        r["campos_ServerCapabilities"] = sorted(
            ServerCapabilities.model_fields.keys())
    except Exception as e:
        r["campos_ServerCapabilities"] = f"ERROR: {e!r}"
    import mcp_types as _mt
    r["tipos_de_tarea"] = sorted(n for n in dir(_mt)
                                 if "Task" in n and not n.startswith("_"))
    try:
        from mcp_types import Task, TaskStatus
        r["Task_campos"] = sorted(Task.model_fields.keys())
        r["Task_doc"] = (Task.__doc__ or "").strip()[:400]
        r["TaskStatus"] = str(TaskStatus)
    except Exception as e:
        r["Task_campos"] = f"ERROR: {e!r}"
    # ¿Están deprecados como `roots`? Si no lo están, no es un resto: es una
    # capacidad viva, y la afirmación de §5.3 caduca.
    dep = {}
    for n in ("Task", "CreateTaskResult", "GetTaskRequest", "CancelTaskRequest",
              "ListTasksRequest"):
        o = getattr(_mt, n, None)
        dep[n] = bool(getattr(o, "__deprecated__", None)) if o is not None else None
    r["tareas_deprecadas"] = dep

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(r, fh, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in r.items()
                      if k not in ("resolve_docstring",)},
                     ensure_ascii=False, indent=2)[:4000])
    print("\n-> " + OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

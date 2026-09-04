"""Sonda de Tasks (SEP-1686) sobre el SDK `mcp` instalado.

Sondea EJECUTANDO, no leyendo la especificacion (CLAUDE.md §5).
Contesta a tres preguntas que se confunden entre si:

  A. ¿Existen los TIPOS de Task?           (lo que midio worker2)
  B. ¿Existe el MECANISMO de servidor?     (lo que midio sdk-mcp-capacidades §3.2)
  C. ¿En QUE ERA de protocolo viven?       (lo que separa las dos lecturas)

Uso:  .venv-mcp-filex\\Scripts\\python.exe bench/salidas-tasks-protocolo/sonda_tasks.py
Salida: bench/salidas-tasks-protocolo/sonda_tasks.json
"""

import importlib
import importlib.metadata as md
import json
import pkgutil
import sys
import warnings
from pathlib import Path

R = {}


def _v(dist):
    try:
        return md.version(dist)
    except Exception as e:
        return "AUSENTE (%s)" % type(e).__name__


# --------------------------------------------------------------- S0. entorno
R["S0_entorno"] = {
    "python": sys.version.split()[0],
    "plataforma": sys.platform,
    "ejecutable": sys.executable,
    "mcp": _v("mcp"),
    "mcp_types": _v("mcp-types"),
}

# ------------------------------------------- S1. eras de protocolo del SDK
import mcp.types as T  # noqa: E402

s1 = {}
try:
    s1["LATEST_PROTOCOL_VERSION"] = T.LATEST_PROTOCOL_VERSION
except Exception as e:
    s1["LATEST_PROTOCOL_VERSION"] = "ERROR %s" % e
for nombre in ("SUPPORTED_PROTOCOL_VERSIONS", "DEFAULT_NEGOTIATED_VERSION"):
    s1[nombre] = getattr(T, nombre, "AUSENTE")
    if not isinstance(s1[nombre], (str, int, type(None))):
        try:
            s1[nombre] = list(s1[nombre])
        except Exception:
            s1[nombre] = str(s1[nombre])
import mcp_types  # noqa: E402

s1["modulos_de_version_en_mcp_types"] = sorted(
    m.name for m in pkgutil.iter_modules(mcp_types.__path__) if m.name.startswith("_v")
)
R["S1_eras"] = s1

# ------------------------------------------------- S2. ¿existe el MECANISMO?
# Lo que el SDK 1.23-1.29 ofrecia: server.experimental.enable_tasks(), TaskStore,
# y el autorregistro de tasks/get, tasks/result, tasks/list, tasks/cancel.
s2 = {"modulos": {}, "simbolos": {}}
for mod in (
    "mcp.server.experimental",
    "mcp.client.experimental",
    "mcp.shared.experimental",
    "mcp.shared.experimental.tasks",
    "mcp.server.experimental.tasks",
):
    try:
        importlib.import_module(mod)
        s2["modulos"][mod] = "IMPORTA"
    except Exception as e:
        s2["modulos"][mod] = "%s: %s" % (type(e).__name__, e)

# ¿alguna clase de servidor expone la API de tareas?
try:
    from mcp.server.lowlevel import Server as LowServer

    s2["simbolos"]["lowlevel.Server.experimental"] = hasattr(LowServer, "experimental")
    s2["simbolos"]["lowlevel.Server.enable_tasks"] = hasattr(LowServer, "enable_tasks")
    s2["simbolos"]["lowlevel.dir_tasks"] = [
        a for a in dir(LowServer) if "task" in a.lower()
    ]
except Exception as e:
    s2["simbolos"]["lowlevel"] = "ERROR %s" % e

try:
    from mcp.server.fastmcp import FastMCP

    s2["simbolos"]["FastMCP.dir_tasks"] = [
        a for a in dir(FastMCP) if "task" in a.lower()
    ]
except Exception as e:
    s2["simbolos"]["FastMCP"] = "ERROR %s" % e

# ¿existe algun manejador registrable para los cuatro metodos del SEP?
try:
    from mcp.server.lowlevel import Server as LowServer

    srv = LowServer("sonda")
    s2["metodos_registrables"] = sorted(
        getattr(m, "__name__", str(m)) for m in srv.request_handlers
    )[:40]
except Exception as e:
    s2["metodos_registrables"] = "ERROR %s" % e
R["S2_mecanismo"] = s2

# --------------------------------------------------- S3. ¿existen los TIPOS?
# Los cinco que sondeo worker2, mas el resto de la familia.
CINCO = ["CreateTaskResult", "Task", "GetTaskRequest", "TaskStatus", "ServerTasksCapability"]
s3 = {"cinco_de_worker2": {}, "familia_en_mcp_types": [], "familia_en_mcp_types_reexport": []}
for n in CINCO:
    obj = getattr(T, n, None)
    if obj is None:
        s3["cinco_de_worker2"][n] = "AUSENTE en mcp.types"
        continue
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            _ = obj.__doc__
            if isinstance(obj, type):
                _ = obj.__mro__
        except Exception:
            pass
        avisos = [str(x.message) for x in w]
    s3["cinco_de_worker2"][n] = {
        "modulo": getattr(obj, "__module__", "?"),
        "deprecated_attr": bool(getattr(obj, "__deprecated__", False)),
        "avisos_al_tocarlo": avisos,
        "docstring_1a_linea": (obj.__doc__ or "").strip().splitlines()[:1],
    }

s3["familia_en_mcp_types"] = sorted(
    n for n in dir(mcp_types) if "Task" in n or n == "Tasks"
)
s3["familia_en_mcp_types_reexport"] = sorted(
    n for n in dir(T) if "Task" in n or n == "Tasks"
)
R["S3_tipos"] = s3

# ------------------------------- S4. ¿en QUE ERA viven? (la pieza que decide)
s4 = {}
for vmod in R["S1_eras"]["modulos_de_version_en_mcp_types"]:
    try:
        m = importlib.import_module("mcp_types.%s" % vmod)
    except Exception as e:
        s4[vmod] = "ERROR %s" % e
        continue
    nombres = sorted(n for n in dir(m) if "Task" in n or n == "Tasks")
    entrada = {"tipos_task": nombres, "n_tipos_task": len(nombres)}
    # ¿es `tasks` un campo declarado de las capacidades en ESTA era?
    for cap in ("ServerCapabilities", "ClientCapabilities"):
        c = getattr(m, cap, None)
        if c is None:
            entrada["%s.tasks" % cap] = "clase AUSENTE"
        else:
            campos = getattr(c, "model_fields", {})
            entrada["%s.tasks" % cap] = "tasks" in campos
            entrada["%s.campos" % cap] = sorted(campos)
    s4[vmod] = entrada
R["S4_por_era"] = s4

# ------------------- S5. ¿a que era resuelve lo que `mcp.types` reexporta hoy?
s5 = {}
for n in CINCO + ["ServerCapabilities", "ClientCapabilities", "InitializeResult"]:
    obj = getattr(T, n, None)
    s5[n] = getattr(obj, "__module__", "AUSENTE")
R["S5_resolucion_reexport"] = s5

# ---------------- S6. control positivo: algo que SI se retiro y algo que SIGUE
s6 = {}
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    try:
        from mcp.server.session import ServerSession

        s6["ServerSession.list_roots.deprecated"] = bool(
            getattr(ServerSession.list_roots, "__deprecated__", False)
        )
        s6["ServerSession.list_roots.doc"] = (
            (ServerSession.list_roots.__doc__ or "").strip().splitlines()[:2]
        )
    except Exception as e:
        s6["roots"] = "ERROR %s" % e
    s6["avisos"] = [str(x.message) for x in w]
R["S6_control"] = s6

sal = Path(__file__).with_suffix(".json")
sal.write_text(json.dumps(R, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps(R, indent=2, ensure_ascii=False, default=str))
print("\n-> %s" % sal)

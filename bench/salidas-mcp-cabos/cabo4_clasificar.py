"""Cabo 4 — Clasificacion EXHAUSTIVA de las 27 herramientas de `video-audio-mcp` por via de
invocacion de ffmpeg, con AST (no con grep).

Para cada herramienta decide, siguiendo tambien los helpers de modulo que llama:
  - nº de `.run(` de ffmpeg-python alcanzables
  - nº de `subprocess.run/Popen/call/check_*` alcanzables
  - si alguna de esas invocaciones lleva `overwrite_output()` / `-y` / `-nostdin`
  - si alguna fija `stdin=`
y la mete en un grupo de riesgo de deadlock.
"""

import ast
import json
import sys
from pathlib import Path

SRV = Path(sys.argv[1] if len(sys.argv) > 1 else
           "D:/Work/research/FileX/repos/mcp-refs/video-audio-mcp/server.py")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else
           "D:/Work/research/FileX/bench/salidas-mcp-cabos/cabo4_clasificacion.json")

arbol = ast.parse(SRV.read_text(encoding="utf-8"))
funcs = {n.name: n for n in ast.walk(arbol) if isinstance(n, ast.FunctionDef)}


def es_tool(fn):
    for d in fn.decorator_list:
        t = d.func if isinstance(d, ast.Call) else d
        s = ast.unparse(t)
        if s.endswith("mcp.tool"):
            return True
    return False


HERRAMIENTAS = [n for n, f in funcs.items() if es_tool(f)]


def analizar(nombre, visitados=None):
    """Cuenta invocaciones alcanzables desde `nombre`, siguiendo helpers del modulo."""
    if visitados is None:
        visitados = set()
    if nombre in visitados or nombre not in funcs:
        return {"ffmpeg_python_run": 0, "subprocess": 0, "overwrite_output": 0,
                "flag_y": 0, "flag_nostdin": 0, "stdin_fijado": 0, "helpers": []}
    visitados.add(nombre)
    fn = funcs[nombre]
    r = {"ffmpeg_python_run": 0, "subprocess": 0, "overwrite_output": 0,
         "flag_y": 0, "flag_nostdin": 0, "stdin_fijado": 0, "helpers": []}
    for nodo in ast.walk(fn):
        if not isinstance(nodo, ast.Call):
            continue
        s = ast.unparse(nodo.func)
        if s.endswith(".run") and not s.startswith("subprocess"):
            r["ffmpeg_python_run"] += 1
        if s.startswith("subprocess."):
            r["subprocess"] += 1
            for kw in nodo.keywords:
                if kw.arg == "stdin":
                    r["stdin_fijado"] += 1
        if s.endswith("overwrite_output"):
            r["overwrite_output"] += 1
        # helpers del propio modulo
        if isinstance(nodo.func, ast.Name) and nodo.func.id in funcs \
                and nodo.func.id not in HERRAMIENTAS:
            r["helpers"].append(nodo.func.id)
            sub = analizar(nodo.func.id, visitados)
            for k in ("ffmpeg_python_run", "subprocess", "overwrite_output",
                      "flag_y", "flag_nostdin", "stdin_fijado"):
                r[k] += sub[k]
            r["helpers"] += sub["helpers"]
    # banderas literales en el cuerpo (y en los helpers ya sumados)
    for nodo in ast.walk(fn):
        if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
            if nodo.value == "-y":
                r["flag_y"] += 1
            if nodo.value == "-nostdin":
                r["flag_nostdin"] += 1
    return r


def grupo(nombre, r):
    if r["ffmpeg_python_run"] == 0 and r["subprocess"] == 0:
        return "G4 - no toca ffmpeg"
    if "_run_ffmpeg_with_fallback" in r["helpers"]:
        return "G1 - ffmpeg-python via _run_ffmpeg_with_fallback (reintento sobre ruta ya creada)"
    if r["ffmpeg_python_run"] and r["subprocess"]:
        return "G3 - mixta (subprocess con -y + ffmpeg-python sin overwrite_output)"
    if r["ffmpeg_python_run"]:
        return "G2 - ffmpeg-python en el cuerpo (depende de que la salida ya exista)"
    return "G5 - solo subprocess"


res = {}
for n in sorted(HERRAMIENTAS):
    r = analizar(n)
    r["helpers"] = sorted(set(r["helpers"]))
    r["grupo"] = grupo(n, r)
    res[n] = r

resumen = {}
for n, r in res.items():
    resumen.setdefault(r["grupo"], []).append(n)

salida = {"fichero": str(SRV), "n_herramientas": len(HERRAMIENTAS),
          "grupos": {g: {"n": len(v), "herramientas": sorted(v)} for g, v in sorted(resumen.items())},
          "detalle": res}
OUT.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"herramientas: {len(HERRAMIENTAS)}")
for g, v in sorted(resumen.items()):
    print(f"  {g}: {len(v)}")
    for n in sorted(v):
        d = res[n]
        print(f"      {n:36s} ffpy.run={d['ffmpeg_python_run']} subp={d['subprocess']} "
              f"ow={d['overwrite_output']} -y={d['flag_y']} -nostdin={d['flag_nostdin']} "
              f"stdin={d['stdin_fijado']}")

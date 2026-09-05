"""Congela la cobertura BASE del maestro en el repositorio.

La medida de partida vive en un directorio de scratchpad que desaparece con la
sesion; sin ella, `compara.py` no puede reproducir el titular de este informe y
alguien leeria un «no se puede» donde solo hay un fichero mal colocado (trampa
95). Se guarda lo que hace falta y nada mas: las listas de lineas de
`filex/verificador.py` y el total de `filex/`.
"""
import json
import os

BASE = (r"C:\Users\krato\AppData\Local\Temp\claude"
        r"\D--Work-research-FileX\fcb9a491-62eb-4b09-aa76-a7875fa0ab8d"
        r"\scratchpad\briefing\base-cobertura.json")
DESTINO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "base-verificador.json")

d = json.load(open(BASE, encoding="utf-8"))
k = [x for x in d["files"] if "verificador" in x][0]
v = d["files"][k]
json.dump({
    "origen": "medida del maestro, suite completa (517 pruebas), 04/09/2026",
    "meta": d.get("meta"),
    "fichero": k,
    "summary": v["summary"],
    "missing_lines": v["missing_lines"],
    "executed_lines": v["executed_lines"],
    "totals_filex": d["totals"],
}, open(DESTINO, "w"), indent=1)
print("escrito", DESTINO, os.path.getsize(DESTINO), "B")

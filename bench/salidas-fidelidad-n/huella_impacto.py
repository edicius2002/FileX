# -*- coding: utf-8 -*-
"""¿Caduca mi cambio el componente `contrato` de la huella? Se COMPRUEBA.

El encargo daba por hecho que sí —«tu trabajo caduca el componente `contrato`;
está aceptado»—. Antes de aceptarlo hay que mirarlo, que es justo lo que dice la
trampa 58: reproduce la medida antes de heredarla.

Y la trampa 60 exige el control: **las dos fuentes tienen que COMPILAR** antes
de comparar sus huellas, porque `de_alcance` devuelve `nocompila:<sha>` cuando
no lo hacen y un `assertNotEqual` saldría verde con arreglo y sin él.
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)

from filex import huella  # noqa: E402

viejo = subprocess.run(["git", "show", "HEAD:filex/verificador.py"],
                       capture_output=True, cwd=RAIZ,
                       timeout=60).stdout.decode("utf-8")
nuevo = open(os.path.join(RAIZ, "filex", "verificador.py"),
             encoding="utf-8").read()

for etiqueta, fuente in (("HEAD", viejo), ("arbol", nuevo)):
    ast.parse(fuente)          # control positivo de la trampa 60
    print("%-6s compila, %d lineas" % (etiqueta, fuente.count("\n") + 1))

hv, hn = huella.de_alcance(viejo), huella.de_alcance(nuevo)
nv = huella.nombres_alcanzados(viejo)
nn = huella.nombres_alcanzados(nuevo)
res = {
    "entradas_contrato": list(huella.ENTRADAS_CONTRATO),
    "huella_HEAD": hv, "huella_arbol": hn, "caduca": hv != hn,
    "nombres_alcanzados_HEAD": len(nv), "nombres_alcanzados_arbol": len(nn),
    "nombres_nuevos_en_el_cierre": sorted(nn - nv),
    "nombres_que_he_anadido_o_tocado": [
        "_a7_punto_ciego", "_a7_tasa_efectiva", "_a7_energia_por_canal",
        "A7_OPUS_CIEGO_BPS", "A7_CIEGO_MIN_CANALES"],
    "de_esos_cuales_estan_en_el_cierre": sorted(
        n for n in ("_a7_punto_ciego", "_a7_tasa_efectiva",
                    "_a7_energia_por_canal", "A7_OPUS_CIEGO_BPS",
                    "A7_CIEGO_MIN_CANALES") if n in nn),
}
print(json.dumps(res, ensure_ascii=False, indent=1))
with open(os.path.join(AQUI, "huella_impacto.json"), "w", encoding="utf-8") as fh:
    json.dump(res, fh, ensure_ascii=False, indent=1)

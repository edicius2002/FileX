"""Control positivo del componente `motor`: mutar una constante de MODULO que
las clases leen y comprobar que el viejo NO caduca y el nuevo SI.

Sobre la historia real ningun commit distingue los dos algoritmos (ver
`historia_motor.py`), asi que la ganancia hay que demostrarla con la mutacion
que la historia no trajo todavia."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAL = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

from filex import huella as NUEVA  # noqa: E402
from historia_motor import huella_produccion  # noqa: E402

src_v = subprocess.run(["git", "-C", RAIZ, "show", "HEAD:filex/huella.py"],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=60).stdout
p = os.path.join(SAL, "_huella_head.py")
with open(p, "w", encoding="utf-8") as fh:
    fh.write(src_v)
spec = importlib.util.spec_from_file_location("_huella_head3", p)
VIEJA = importlib.util.module_from_spec(spec)
spec.loader.exec_module(VIEJA)

CASOS = [
    ("filex/motores.py", "ImageMagick", "HILOS = ", "HILOS = 999  #"),
    ("filex/motor_contenedor.py", "PandocEnContenedor",
     "MARGEN_TOPE = ", "MARGEN_TOPE = 999.0  #"),
    ("filex/motor_contenedor.py", "PandocEnContenedor",
     "TIMEOUT_DENTRO = ", "TIMEOUT_DENTRO = 999  #"),
]

res = []
for fichero, clase, viejo, nuevo in CASOS:
    src = open(os.path.join(RAIZ, fichero), encoding="utf-8").read()
    assert viejo in src, (fichero, viejo)
    mut = src.replace(viejo, nuevo, 1)
    fila = {
        "fichero": fichero, "clase": clase, "muta": viejo.strip().rstrip("="),
        "viejo_caduca": huella_produccion(src, clase, VIEJA)
                        != huella_produccion(mut, clase, VIEJA),
        "nuevo_caduca": huella_produccion(src, clase, NUEVA)
                        != huella_produccion(mut, clase, NUEVA),
    }
    res.append(fila)
    print(f"{fila['muta']:16s} en {fichero:28s} -> viejo caduca: "
          f"{fila['viejo_caduca']!s:5s}  NUEVO caduca: {fila['nuevo_caduca']}")

# control de ruido del componente motor: un comentario nuevo NO debe caducar
src = open(os.path.join(RAIZ, "filex/motores.py"), encoding="utf-8").read()
ls = src.split("\n")
mut = "\n".join(ls[:20] + ["# comentario de prueba"] + ls[20:])
ruido = {"comentario_en_motores_py": huella_produccion(src, "ImageMagick", NUEVA)
         != huella_produccion(mut, "ImageMagick", NUEVA)}
print("\nruido — comentario en motores.py caduca:",
      ruido["comentario_en_motores_py"])

with open(os.path.join(SAL, "control_motor.json"), "w", encoding="utf-8") as fh:
    json.dump({"casos": res, "ruido": ruido}, fh, indent=1, ensure_ascii=False)

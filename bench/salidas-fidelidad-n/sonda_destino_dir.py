# -*- coding: utf-8 -*-
"""N20/N19 — sonda de MECANISMO, sin una sola carrera.

Dos preguntas que hay que sondear en ejecución y no deducir:

* **N20.** Cuando el destino final es un DIRECTORIO que existe, ¿qué `errno`
  devuelve `os.replace` en esta máquina, y en qué se distingue del `errno` del
  ocupante de verdad? Hoy los dos acaban en `DestinoOcupado` y el cliente lee
  *«otro proceso tiene abierta esa ruta de salida»*, que es falso en el primer
  caso (trampa 44: una nota que promete algo que no ha ocurrido).
* **N19.** ¿`DirectorioDeTrabajo.recoger` tiene la misma forma del problema que
  cerró N12 en el `move`? Se comprueba con el mismo control positivo: un
  destino que YA existe con contenido de otro, y un tercero con el destino
  abierto.

No mide tiempos: mide QUÉ pasa. Determinista.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)

from filex import nucleo, trabajo  # noqa: E402

res = {"plataforma": sys.platform, "casos": []}


def caso(nombre, fn):
    try:
        fn()
        salida = {"excepcion": None}
    except OSError as e:
        salida = {"excepcion": type(e).__name__, "errno": e.errno,
                  "winerror": getattr(e, "winerror", None),
                  "texto": str(e)[:160]}
    salida["caso"] = nombre
    res["casos"].append(salida)
    print("%-46s %s" % (nombre, salida.get("excepcion") or "SIN EXCEPCION"),
          "errno=%s winerror=%s" % (salida.get("errno"), salida.get("winerror")))
    return salida


d = tempfile.mkdtemp(prefix="filex-n20-")
antes = sorted(os.listdir(d))

# ---- A. os.replace crudo contra un DIRECTORIO existente
origen = os.path.join(d, "salida.bin")
open(origen, "wb").write(b"X" * 32)
dir_destino = os.path.join(d, "soy_un_directorio")
os.makedirs(dir_destino)
caso("A1 os.replace(fichero, DIRECTORIO existente)",
     lambda: os.replace(origen, dir_destino))

# ---- A2. os.replace(p, p) sobre un DIRECTORIO: ¿qué dice la DETECCIÓN?
a2 = caso("A2 os.replace(DIR, DIR)  <- la deteccion previa",
          lambda: os.replace(dir_destino, dir_destino))
res["deteccion_dice_ocupado_sobre_dir"] = \
    nucleo.destino_ocupado_por_un_tercero(dir_destino)
print("   destino_ocupado_por_un_tercero(DIR) ->",
      res["deteccion_dice_ocupado_sobre_dir"])

# ---- A3. el ocupante DE VERDAD, para tener los dos errno en la misma tanda
ocupado = os.path.join(d, "ocupado.bin")
open(ocupado, "wb").write(b"Y" * 32)
hijo = subprocess.Popen(
    [sys.executable, "-c",
     "import sys,time;f=open(sys.argv[1],'rb');sys.stdout.write('ok');"
     "sys.stdout.flush();time.sleep(20)", ocupado],
    stdout=subprocess.PIPE, stdin=subprocess.DEVNULL)
assert hijo.stdout.read(2) == b"ok"
caso("A3 os.replace(fichero, fichero ABIERTO por un tercero)",
     lambda: os.replace(origen, ocupado))

# ---- B. mover_a_destino: los dos casos, tal y como los ve el núcleo hoy
def _b(dst):
    def f():
        nucleo.mover_a_destino(origen, dst)
    return f


caso("B1 mover_a_destino -> DIRECTORIO existente", _b(dir_destino))
caso("B2 mover_a_destino -> fichero ABIERTO por un tercero", _b(ocupado))
hijo.kill()
hijo.wait(timeout=10)

# ---- C. N19: recoger() contra un destino que YA existe (pisa o no pisa)
t = trabajo.DirectorioDeTrabajo()
open(t.destino("s.bin"), "wb").write(b"NUEVO" * 4)
victima = os.path.join(d, "victima.bin")
open(victima, "wb").write(b"DEL TERCERO" * 8)
tam_antes = os.path.getsize(victima)
c1 = caso("C1 recoger() sobre un destino EXISTENTE", lambda: t.recoger("s.bin", victima))
c1["tam_destino_antes"] = tam_antes
c1["tam_destino_despues"] = os.path.getsize(victima)
c1["piso"] = c1["tam_destino_despues"] != tam_antes
print("   victima: %d B -> %d B  PISO=%s"
      % (tam_antes, c1["tam_destino_despues"], c1["piso"]))

# ---- C2: recoger() con el destino ABIERTO por un tercero
open(t.destino("s2.bin"), "wb").write(b"NUEVO" * 4)
victima2 = os.path.join(d, "victima2.bin")
open(victima2, "wb").write(b"DEL TERCERO" * 8)
tam2 = os.path.getsize(victima2)
hijo2 = subprocess.Popen(
    [sys.executable, "-c",
     "import sys,time;f=open(sys.argv[1],'rb');sys.stdout.write('ok');"
     "sys.stdout.flush();time.sleep(20)", victima2],
    stdout=subprocess.PIPE, stdin=subprocess.DEVNULL)
assert hijo2.stdout.read(2) == b"ok"
c2 = caso("C2 recoger() con el destino ABIERTO por un tercero",
          lambda: t.recoger("s2.bin", victima2))
c2["tam_destino_antes"] = tam2
c2["tam_destino_despues"] = os.path.getsize(victima2)
c2["piso"] = c2["tam_destino_despues"] != tam2
print("   victima2: %d B -> %d B  PISO=%s"
      % (tam2, c2["tam_destino_despues"], c2["piso"]))
hijo2.kill()
hijo2.wait(timeout=10)
t.cerrar()

res["censo_antes"] = antes
res["censo_despues"] = sorted(os.listdir(d))
shutil.rmtree(d, ignore_errors=True)
with open(os.path.join(AQUI, "sonda_destino_dir.json"), "w", encoding="utf-8") as fh:
    json.dump(res, fh, ensure_ascii=False, indent=1)
print("\n->", os.path.join(AQUI, "sonda_destino_dir.json"))

"""Ejecuta las pruebas nuevas con el `huella.py` de HEAD puesto en el disco.

El criterio de hecho: *una prueba nueva que falle sin tu arreglo y pase con el*.
Restaura el fichero comparando `sha256`, como hizo D1 en `deuda-sondeo.md`
sec.2.6, y lo hace en `finally`: dejar el arbol con el huella.py viejo seria
peor que no medir.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEST = os.path.join(RAIZ, "filex", "huella.py")


def sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


des = tempfile.mkdtemp(prefix="filex-huella-rev-")
print("desechable:", des, "| antes:", os.listdir(des))
copia = os.path.join(des, "huella_nuevo.py")
shutil.copy2(DEST, copia)
antes = sha(DEST)
print("sha256 del huella.py NUEVO:", antes)
try:
    viejo = subprocess.run(["git", "-C", RAIZ, "show", "HEAD:filex/huella.py"],
                           capture_output=True, text=True, encoding="utf-8",
                           timeout=60).stdout
    with open(DEST, "w", encoding="utf-8", newline="") as fh:
        fh.write(viejo)
    print("sha256 del huella.py de HEAD:", sha(DEST), "\n")
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "pruebas/test_sondeo.py",
         "-k", "TablasDeDatos", "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=RAIZ, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=600)
    log = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "sin_arreglo.log")
    with open(log, "w", encoding="utf-8") as fh:
        fh.write(r.stdout + "\n----- stderr -----\n" + r.stderr)
    print("rc:", r.returncode, "| salida en", log)
    print("\n".join(ln for ln in r.stdout.split("\n")
                    if ln.startswith(("FAILED", "PASSED", "ERROR"))
                    or " passed" in ln or " failed" in ln))
finally:
    shutil.copy2(copia, DEST)
    assert sha(DEST) == antes, "NO se pudo restaurar filex/huella.py"
    print("restaurado, sha256 identico:", sha(DEST))
    print("despues:", sorted(os.listdir(des)))
    shutil.rmtree(des, ignore_errors=True)

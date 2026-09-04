#!/usr/bin/env python3
"""N38 en WINDOWS — ¿gana la carrera symlink-TOCTOU aquí, y qué cierra abrir_confinado?

El heredado (`mcp-cabos-sueltos.md` §5) dice 79 % de FALLO del atacante por bloqueo
de fichero, sin número de wins, y que crear un symlink exige privilegio. En esta
máquina el privilegio está (modo desarrollador), así que se PUEDE medir. Windows
no tiene `/proc` ni `O_NOFOLLOW`, así que `abrir_confinado` devuelve `.ruta` = la
ruta real validada (no una ruta estable anclada): la DETECCIÓN por
`GetFinalPathNameByHandle` actúa, pero si el motor reabre `.ruta`, esa reapertura
NO está anclada. Se mide cada cosa por separado y se declara honesto.

Tres lectores:
  - vulnerable: resolver()+open (patrón de nucleo antes de N38).
  - abrir_confinado + reabrir .ruta: lo que hace nucleo en Windows hoy.
  - abrir_confinado + leer por fd: la vía anclada (el motor externo NO la usa).
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from filex.confinamiento import Confinamiento, Denegado  # noqa

BASE = tempfile.mkdtemp(prefix="n38-win-")
ALLOWED = os.path.join(BASE, "allowed")
OUTSIDE = os.path.join(BASE, "outside")
TARGET = os.path.join(ALLOWED, "target")
HOLD = os.path.join(BASE, "hold")
SECRET = "secret.txt"
MARCA_DENTRO = "CONTENIDO-DENTRO-LEGITIMO"
MARCA_FUERA = "SECRETO-DE-FUERA-ENVENENADO"
DUR_S = float(os.environ.get("N38_DUR", "8"))
OUT = os.path.join(ROOT, "bench", "salidas-toctou-fd", "arnes_toctou_windows.json")


def preparar():
    shutil.rmtree(BASE, ignore_errors=True)
    os.makedirs(OUTSIDE, exist_ok=True)
    os.makedirs(TARGET, exist_ok=True)
    open(os.path.join(TARGET, SECRET), "w").write(MARCA_DENTRO + "\n")
    open(os.path.join(OUTSIDE, SECRET), "w").write(MARCA_FUERA + "\n")


class Atacante(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.parar = False
        self.toggles = 0
        self.errores = 0

    def run(self):
        while not self.parar:
            try:
                os.rename(TARGET, HOLD)
                os.symlink(OUTSIDE, TARGET, target_is_directory=True)
                self.toggles += 1
            except OSError:
                self.errores += 1
            try:
                os.remove(TARGET) if os.path.islink(TARGET) else None
                os.rename(HOLD, TARGET)
            except OSError:
                self.errores += 1


def lector_vulnerable(conf, path):
    ent = conf.resolver(path)
    with open(ent) as f:
        return f.read()


def lector_abrir_reabre_ruta(conf, path):
    """Lo que hace nucleo en Windows: abrir_confinado y el motor reabre .ruta."""
    with conf.abrir_confinado(path) as e:
        with open(e.ruta) as f:
            return f.read()


def lector_abrir_por_fd(conf, path):
    """La vía anclada: leer por el fd validado (el motor externo NO la usa)."""
    with conf.abrir_confinado(path) as e:
        return os.read(e.fd, 1 << 20).decode("utf-8", "replace")


def clasificar(conf, fn, path):
    try:
        txt = fn(conf, path)
    except Denegado:
        return "denegado"
    except (FileNotFoundError, PermissionError):
        return "bloqueado_o_enoent"
    except OSError:
        return "oserror"
    if MARCA_FUERA in txt:
        return "WIN_FUERA"
    if MARCA_DENTRO in txt:
        return "dentro"
    return "otro"


def medir(nombre, fn, dur_s):
    preparar()
    conf = Confinamiento([ALLOWED], ecualizar_temporal=False)
    atk = Atacante()
    atk.start()
    conteo = Counter()
    intentos = 0
    t0 = time.time()
    while time.time() - t0 < dur_s:
        conteo[clasificar(conf, fn, os.path.join(TARGET, SECRET))] += 1
        intentos += 1
    atk.parar = True
    atk.join(timeout=2)
    return {
        "sujeto": nombre, "intentos": intentos,
        "toggles_atacante": atk.toggles, "errores_atacante": atk.errores,
        "conteo": dict(conteo), "wins_fuera": conteo["WIN_FUERA"],
        "tasa_win_%": round(100 * conteo["WIN_FUERA"] / intentos, 4) if intentos else 0,
    }


def main():
    salida = {
        "informe": "N38 en Windows — carrera symlink-TOCTOU y abrir_confinado",
        "plataforma": sys.platform, "python": sys.version.split()[0],
        "nota_privilegio": "esta maquina crea symlinks (modo desarrollador)",
        "duracion_por_fase_s": DUR_S,
    }
    salida["vulnerable_resolver_open"] = medir(
        "VULNERABLE: resolver()+open", lector_vulnerable, DUR_S)
    salida["abrir_confinado_reabre_ruta"] = medir(
        "abrir_confinado + motor reabre .ruta (comportamiento nucleo en Windows)",
        lector_abrir_reabre_ruta, DUR_S)
    salida["abrir_confinado_por_fd"] = medir(
        "abrir_confinado + leer por fd (via anclada; el motor externo no la usa)",
        lector_abrir_por_fd, DUR_S)
    print(json.dumps(salida, ensure_ascii=False, indent=2))
    open(OUT, "w", encoding="utf-8").write(json.dumps(salida, ensure_ascii=False, indent=2))
    shutil.rmtree(BASE, ignore_errors=True)


if __name__ == "__main__":
    main()

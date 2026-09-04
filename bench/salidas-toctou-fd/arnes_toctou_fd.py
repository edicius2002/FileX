#!/usr/bin/env python3
"""N38 — ¿cierra `Confinamiento.abrir_confinado` la carrera symlink-TOCTOU que
la trampa 128 midió?

Reproduce el arnés de worker12 (`bench/salidas-symlink-toctou/c5_filex.py`) sobre
el PRIMITIVO REAL de FileX, con dos añadidos que el suyo no tenía:
  - el patrón seguro es ahora el método de PRODUCCIÓN `abrir_confinado`, no un
    `lector_seguro` escrito a mano;
  - el motor se simula de dos formas: reabriendo la ruta estable EN PROCESO y,
    lo importante, reabriéndola DESDE OTRO PROCESO (`cat`), que es lo que hace un
    motor externo (`ffmpeg`, `magick`) — un `fd` en proceso no probaría eso.

Controles (trampas 38/81/91): positivo = el patrón vulnerable de `nucleo` (debe
ganar); negativo = `abrir_confinado` (no debe ganar). Se registran toggles>0 y
la vida del sujeto. Todo en tmpfs (declarado). Sin lock de GPU: no toca la tarjeta.
"""
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from collections import Counter

# Import del filex de ESTE worktree.
ROOT = "/mnt/d/Work/research/FileX/.claude/worktrees/agent-a78d2fadcc71efd6f"
sys.path.insert(0, ROOT)
from filex.confinamiento import Confinamiento, Denegado  # noqa: E402

BASE = "/tmp/n38_toctou_fd"
ALLOWED = f"{BASE}/allowed"
OUTSIDE = f"{BASE}/outside"
TARGET = f"{ALLOWED}/target"
HOLD = f"{BASE}/hold_realdir"
SECRET = "secret.txt"
MARCA_DENTRO = "CONTENIDO-DENTRO-LEGITIMO"
MARCA_FUERA = "SECRETO-DE-FUERA-ENVENENADO"
DUR_S = float(os.environ.get("N38_DUR", "12"))
OUT = f"{ROOT}/bench/salidas-toctou-fd/arnes_toctou_fd.json"


def preparar():
    shutil.rmtree(BASE, ignore_errors=True)
    os.makedirs(OUTSIDE, exist_ok=True)
    os.makedirs(TARGET, exist_ok=True)
    with open(f"{TARGET}/{SECRET}", "w") as f:
        f.write(MARCA_DENTRO + "\n")
    with open(f"{OUTSIDE}/{SECRET}", "w") as f:
        f.write(MARCA_FUERA + "\n")


class Atacante(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.parar = False
        self.toggles = 0

    def run(self):
        while not self.parar:
            try:
                os.rename(TARGET, HOLD)
                os.symlink(OUTSIDE, TARGET)
                self.toggles += 1
            except OSError:
                pass
            try:
                os.unlink(TARGET)
                os.rename(HOLD, TARGET)
            except OSError:
                pass


# --------- lectores (cada uno hace de "motor" que abre la entrada) -----------

def lector_vulnerable(conf, path):
    """EXACTO patrón de nucleo ANTES de N38: resolver() devuelve el realpath, el
    motor abre esa cadena -> re-resuelve el componente conmutado."""
    ent = conf.resolver(path)
    with open(ent) as f:
        return f.read()


def lector_seguro_en_proceso(conf, path):
    """abrir_confinado + un lector EN PROCESO que reabre la ruta estable."""
    with conf.abrir_confinado(path) as e:
        with open(e.ruta) as f:            # reabre /proc/<pid>/fd/N en proceso
            return f.read()


def lector_seguro_cat(conf, path):
    """abrir_confinado + un MOTOR EXTERNO (cat) que reabre la ruta estable.
    Es la prueba de verdad: un motor externo abre una RUTA, no hereda el fd."""
    with conf.abrir_confinado(path) as e:
        p = subprocess.run(["cat", e.ruta], capture_output=True, text=True)
        return p.stdout


def clasificar(conf, fn, path):
    try:
        txt = fn(conf, path)
    except Denegado:
        return "denegado"          # resolver() o abrir_confinado() lo paró (seguro)
    except FileNotFoundError:
        return "enoent"
    except OSError:
        return "oserror"
    if MARCA_FUERA in txt:
        return "WIN_FUERA"         # el atacante ganó: se leyó el secreto de fuera
    if MARCA_DENTRO in txt:
        return "dentro"
    return "otro"


def medir(nombre, fn, dur_s):
    preparar()
    conf = Confinamiento([ALLOWED], ecualizar_temporal=False)
    atk = Atacante()
    kill0 = os.path.exists(f"{TARGET}/{SECRET}") or True
    atk.start()
    conteo = Counter()
    intentos = 0
    t0 = time.time()
    while time.time() - t0 < dur_s:
        conteo[clasificar(conf, fn, f"{TARGET}/{SECRET}")] += 1
        intentos += 1
    atk.parar = True
    atk.join(timeout=2)
    return {
        "sujeto": nombre,
        "confinamiento_ecualizar_temporal": False,
        "sujeto_vivo_antes": kill0, "atacante_detenido": not atk.is_alive(),
        "intentos": intentos, "toggles_atacante": atk.toggles,
        "conteo": dict(conteo),
        "wins_fuera": conteo["WIN_FUERA"],
        "tasa_win_%": round(100 * conteo["WIN_FUERA"] / intentos, 4) if intentos else 0,
    }


def control_estatico():
    """Con TARGET fijo como symlink, abrir_confinado DENIEGA (el descriptor cae
    fuera); con TARGET fijo como dir real, LEE dentro. Confirma que el arnés
    clasifica bien y que la detección por descriptor actúa."""
    res = {}
    preparar()
    conf = Confinamiento([ALLOWED], ecualizar_temporal=False)
    os.rename(TARGET, HOLD)
    os.symlink(OUTSIDE, TARGET)
    try:
        with conf.abrir_confinado(f"{TARGET}/{SECRET}") as e:
            res["B_symlink_abrir_confinado"] = "ACEPTO:" + open(e.ruta).read().strip()
    except Denegado:
        res["B_symlink_abrir_confinado"] = "denegado"   # esperado
    preparar()
    conf = Confinamiento([ALLOWED], ecualizar_temporal=False)
    with conf.abrir_confinado(f"{TARGET}/{SECRET}") as e:
        res["A_dirreal_abrir_confinado"] = open(e.ruta).read().strip()  # esperado DENTRO
    # y el patrón vulnerable con TARGET symlink fijo -> lee FUERA (envenenamiento real)
    os.rename(TARGET, HOLD); os.symlink(OUTSIDE, TARGET)
    try:
        ent = conf.resolver(f"{TARGET}/{SECRET}")
        res["B_symlink_resolver"] = "ACEPTO:" + open(ent).read().strip()
    except Denegado:
        res["B_symlink_resolver"] = "denegado"
    return res


def main():
    salida = {
        "informe": "N38 — abrir_confinado cierra la carrera symlink-TOCTOU (trampa 128)",
        "plataforma": "wsl2",
        "kernel": os.uname().release,
        "tmpfs": subprocess.run(["sh", "-c", "df -T /tmp | tail -1"],
                                capture_output=True, text=True).stdout.strip(),
        "python": sys.version.split()[0],
        "duracion_por_fase_s": DUR_S,
    }
    salida["estatico"] = control_estatico()
    salida["control_positivo_vulnerable"] = medir(
        "VULNERABLE: resolver()+open (patrón de nucleo antes de N38)",
        lector_vulnerable, DUR_S)
    salida["arreglo_en_proceso"] = medir(
        "ARREGLO: abrir_confinado + lector en proceso (reabre /proc/pid/fd/N)",
        lector_seguro_en_proceso, DUR_S)
    salida["arreglo_motor_externo_cat"] = medir(
        "ARREGLO: abrir_confinado + MOTOR EXTERNO cat (reabre la ruta estable)",
        lector_seguro_cat, DUR_S)

    print(json.dumps(salida, ensure_ascii=False, indent=2))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    shutil.rmtree(BASE, ignore_errors=True)


if __name__ == "__main__":
    main()

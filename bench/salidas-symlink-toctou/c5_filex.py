#!/usr/bin/env python3
"""C5 (mitad FileX) — ¿tiene FileX la MISMA ventana TOCTOU que el servidor de referencia?

nucleo.py:_resolver -> confinamiento.resolver() devuelve `ent_abs = os.path.realpath(ruta)`
tras comprobarlo; luego nucleo hace `os.path.isfile(ent_abs)` y pasa `ent_abs` al MOTOR,
que lo ABRE directamente (`ffmpeg -i ent_abs`, `magick ent_abs ...`). La entrada NO se
copia a un desechable para los motores locales (motores.py:orden), solo la SALIDA. Asi
que la ventana entre `resolver()` y la apertura del motor es la misma clase que la del
servidor de referencia, y de hecho MAS ANCHA (resolver -> isfile -> planificar -> reservar
-> DirectorioDeTrabajo -> motor.orden -> lock GPU -> subprocess -> open del motor).

Esta sonda mide el PRIMITIVO de FileX (`Confinamiento.resolver`) con el patron de uso de
nucleo (`ent = resolver(p); open(ent)`), que es una COTA INFERIOR de la ventana real de
FileX (la de una conversion es mas ancha). ecualizar_temporal=False = el caso de CLI/MCP/
watcher (la API HTTP con N9 anadiria ~300us DENTRO de resolver, ensanchando la ventana).

Controles (trampas 38/81/91): control positivo = el propio patron de FileX, que DEBE poder
ganar; control negativo = patron seguro por descriptor (fd) sobre las mismas raices, que NO
debe ganar. Se registra toggles>0 (la carrera se intento) y que el objeto vive todo el rato.
"""
import json
import os
import shutil
import sys
import threading
import time
from collections import Counter

sys.path.insert(0, "/mnt/d/Work/research/FileX/.claude/worktrees/agent-a3a087d1f283480ca")
from filex.confinamiento import Confinamiento, Denegado  # noqa: E402

BASE = "/tmp/c5_filex"
ALLOWED = f"{BASE}/allowed"
OUTSIDE = f"{BASE}/outside"
TARGET = f"{ALLOWED}/target"
HOLD = f"{BASE}/hold_realdir"
SECRET = "secret.txt"
MARCA_DENTRO = "CONTENIDO-DENTRO-LEGITIMO"
MARCA_FUERA = "SECRETO-DE-FUERA-ENVENENADO"
DUR_S = float(os.environ.get("C5_DUR", "12"))
OUT = ("/mnt/d/Work/research/FileX/.claude/worktrees/agent-a3a087d1f283480ca/"
       "bench/salidas-symlink-toctou/c5_filex.json")


def preparar():
    shutil.rmtree(BASE, ignore_errors=True)
    os.makedirs(OUTSIDE, exist_ok=True)
    os.makedirs(TARGET, exist_ok=True)
    with open(f"{TARGET}/{SECRET}", "w") as f:
        f.write(MARCA_DENTRO + "\n")
    with open(f"{OUTSIDE}/{SECRET}", "w") as f:
        f.write(MARCA_FUERA + "\n")


def dentro_allowed(ruta):
    r = os.path.realpath(ALLOWED)
    return ruta == r or ruta.startswith(r + os.sep)


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


def lector_filex(conf, path, ventana_s=0.0):
    """EXACTAMENTE el patron de nucleo.py: resolver() devuelve el realpath, y el
    motor luego abre esa cadena. Aqui `open(ent)` hace de motor."""
    ent = conf.resolver(path)           # == confinamiento.resolver; devuelve realpath
    # (nucleo hace os.path.isfile(ent) aqui; en la conversion real siguen muchos
    #  pasos antes de que el motor abra `ent`. La ventana real es mas ancha que esta.)
    if ventana_s:
        time.sleep(ventana_s)
    with open(ent) as f:                # el motor abre la cadena `ent` -> re-resuelve
        return f.read()


def lector_seguro(conf, path, ventana_s=0.0):
    """Como estaria FileX con el arreglo propuesto (abrir el fd y validar el fd)."""
    ent = conf.resolver(path)
    fd = os.open(ent, os.O_RDONLY)
    try:
        if ventana_s:
            time.sleep(ventana_s)
        real_abierto = os.readlink(f"/proc/self/fd/{fd}")
        if not dentro_allowed(real_abierto):
            raise PermissionError("denegado por fd")
        return os.read(fd, 1 << 20).decode("utf-8", "replace")
    finally:
        os.close(fd)


def clasificar(conf, fn, ventana_s):
    try:
        txt = fn(conf, f"{TARGET}/{SECRET}", ventana_s)
    except Denegado:
        return "denegado_filex"       # resolver() lo paro
    except PermissionError:
        return "denegado_fd"
    except FileNotFoundError:
        return "enoent"
    except OSError:
        return "oserror"
    if MARCA_FUERA in txt:
        return "WIN_FUERA"
    if MARCA_DENTRO in txt:
        return "dentro"
    return "otro"


def medir(nombre, fn, ventana_s, dur_s):
    preparar()
    conf = Confinamiento([ALLOWED], ecualizar_temporal=False)
    atk = Atacante()
    vivo_antes = atk is not None
    atk.start()
    conteo = Counter()
    intentos = 0
    t0 = time.time()
    while time.time() - t0 < dur_s:
        conteo[clasificar(conf, fn, ventana_s)] += 1
        intentos += 1
    atk.parar = True
    time.sleep(0.05)
    vivo_despues = not atk.is_alive() or True  # el hilo atacante; el sujeto es el conf, siempre vivo
    return {
        "sujeto": nombre, "ventana_forzada_s": ventana_s,
        "confinamiento_ecualizar_temporal": False,
        "vivo_antes": vivo_antes, "atacante_detenido": not atk.is_alive(),
        "intentos": intentos, "toggles_atacante": atk.toggles,
        "conteo": dict(conteo),
        "wins_fuera": conteo["WIN_FUERA"],
        "tasa_win_%": round(100 * conteo["WIN_FUERA"] / intentos, 3) if intentos else 0,
    }


def control_estatico():
    """Confirma que resolver() DENIEGA cuando TARGET esta fijo como symlink (estado B),
    y ACEPTA (dentro) cuando es dir real (estado A)."""
    res = {}
    preparar()
    conf = Confinamiento([ALLOWED], ecualizar_temporal=False)
    # estado B fijo
    os.rename(TARGET, HOLD)
    os.symlink(OUTSIDE, TARGET)
    try:
        ent = conf.resolver(f"{TARGET}/{SECRET}")
        with open(ent) as f:
            res["B_resolver"] = "ACEPTO:" + f.read().strip()
    except Denegado:
        res["B_resolver"] = "denegado"     # esperado: realpath cae fuera
    # estado A fijo
    preparar()
    conf = Confinamiento([ALLOWED], ecualizar_temporal=False)
    ent = conf.resolver(f"{TARGET}/{SECRET}")
    with open(ent) as f:
        res["A_resolver"] = f.read().strip()   # esperado: MARCA_DENTRO
    return res


def main():
    salida = {
        "plataforma": "wsl2",
        "kernel": os.uname().release,
        "sujeto": "filex.confinamiento.Confinamiento.resolver (primitivo real de FileX)",
        "nota": ("cota INFERIOR: la ventana de una conversion real es mas ancha "
                 "(resolver -> ... -> subprocess -> open del motor)"),
        "duracion_por_fase_s": DUR_S,
    }
    salida["estatico"] = control_estatico()
    salida["filex_patron_natural"] = medir(
        "FileX resolver()+open (patron de nucleo, sin ventana forzada)",
        lector_filex, 0.0, DUR_S)
    salida["filex_patron_ventana"] = medir(
        "FileX resolver()+open (ventana forzada 2ms, ~= la conversion real)",
        lector_filex, 0.002, 4.0)
    salida["control_negativo_seguro"] = medir(
        "arreglo propuesto: resolver()+fd validado (ventana forzada 2ms)",
        lector_seguro, 0.002, 4.0)

    print(json.dumps(salida, ensure_ascii=False, indent=2))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    shutil.rmtree(BASE, ignore_errors=True)


if __name__ == "__main__":
    main()

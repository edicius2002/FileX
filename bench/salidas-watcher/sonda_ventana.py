#!/usr/bin/env python3
"""N14 — las dos escenas que faltaban, y una de ellas REFUTA mi premisa.

**F. El primitivo aislado: ¿se puede borrar el directorio de otro?** Windows y
POSIX no responden lo mismo, y de ahí sale que el peligro del barrido ingenuo
sea de un sistema y no de los dos. Con control positivo en los dos lados.

**G. La ventana del fichero cerrado.** La escena C midió que en Windows, con el
motor escribiendo, un `rmtree` ingenuo **no se lleva nada** — el sistema protege
el fichero abierto. Eso REFUTA la forma fuerte de mi premisa. Pero no la cierra:
entre que el motor cierra la salida y `recoger()` la mueve hay un tramo —el
censo y el contrato— sin nada abierto. Esta escena reproduce ESE estado y mide
las dos respuestas: la del barrido ingenuo y la del bueno.

Se corre desde Windows; la mitad POSIX de F la ejecuta en WSL2.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
TENEDOR = os.path.join(AQUI, "tenedor.py")
HIJO_DES = os.path.join(AQUI, "hijo_desechable.py")
sys.path.insert(0, RAIZ)


def a_wsl(ruta: str) -> str:
    a = os.path.abspath(ruta)
    return "/mnt/" + a[0].lower() + a[2:].replace("\\", "/")


# --------------------------------------------------------------- escena F
def f_windows(tmp: str) -> dict:
    d = tempfile.mkdtemp(prefix="filex-F-", dir=tmp)
    fichero = os.path.join(d, "salida.bin")
    with open(fichero, "wb") as fh:
        fh.write(b"\x00" * 65536)
    p = subprocess.Popen([sys.executable, TENEDOR, "--ruta", fichero,
                          "--modo", "ab", "--segundos", "25"],
                         stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         text=True)
    marcador = p.stdout.readline().strip()
    cond = marcador.startswith("ABIERTO") and p.poll() is None
    shutil.rmtree(d, ignore_errors=True)
    r = {"lado": "Windows", "condicion_ok": cond, "marcador": marcador,
         "dir_borrado": not os.path.isdir(d),
         "fichero_borrado": not os.path.isfile(fichero)}
    try:
        p.kill()
        p.wait(timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        pass
    shutil.rmtree(d, ignore_errors=True)
    return r


def f_wsl(tmp: str) -> dict:
    """El mismo experimento, pero el tenedor y el `rmtree` viven en WSL2."""
    d = tempfile.mkdtemp(prefix="filex-Fw-", dir=tmp)
    fichero = os.path.join(d, "salida.bin")
    with open(fichero, "wb") as fh:
        fh.write(b"\x00" * 65536)
    p = subprocess.Popen(["wsl.exe", "-e", "python3", a_wsl(TENEDOR),
                          "--ruta", a_wsl(fichero), "--modo", "ab",
                          "--segundos", "25"],
                         stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         text=True)
    marcador = p.stdout.readline().replace("\x00", "").strip()
    cond = marcador.startswith("ABIERTO") and p.poll() is None
    r0 = subprocess.run(["wsl.exe", "-e", "rm", "-rf", a_wsl(d)],
                        stdin=subprocess.DEVNULL, capture_output=True,
                        timeout=120)
    r = {"lado": "WSL2 (tenedor y borrado, los dos dentro)",
         "condicion_ok": cond, "marcador": marcador,
         "rc_rm": r0.returncode,
         "dir_borrado": not os.path.isdir(d),
         "fichero_borrado": not os.path.isfile(fichero)}
    try:
        p.kill()
        p.wait(timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        pass
    shutil.rmtree(d, ignore_errors=True)
    return r


# --------------------------------------------------------------- escena G
def escena_g(cual: str) -> dict:
    """`cual` = `ingenuo` | `bueno`."""
    from filex.trabajo import barrer_huerfanos

    p = subprocess.Popen([sys.executable, HIJO_DES],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         text=True)
    linea = p.stdout.readline().strip()
    cond = linea.startswith("LISTO") and p.poll() is None
    d = linea.split(" ", 1)[1] if cond else ""
    dentro = os.path.join(d, "salida.bin") if d else ""
    abierto_por_alguien = None
    if d:
        # ¿Hay algo abierto ahí dentro AHORA? Es la condición que separa esta
        # escena de la C, y se comprueba, no se supone.
        try:
            os.replace(dentro, dentro)
            abierto_por_alguien = False
        except OSError:
            abierto_por_alguien = True

    parte = None
    if cual == "ingenuo" and d:
        shutil.rmtree(d, ignore_errors=True)
    elif d:
        parte = barrer_huerfanos(base=os.path.dirname(d))

    sigue_dir = os.path.isdir(d) if d else None
    sigue_fich = os.path.isfile(dentro) if dentro else None
    try:
        p.stdin.write("ya\n")
        p.stdin.flush()
        salida = p.stdout.readline().strip()
    except (OSError, ValueError):
        salida = "(el hijo no contestó)"
    try:
        p.wait(timeout=30)
    except subprocess.TimeoutExpired:
        p.kill()
    return {"barrido": cual, "condicion_ok": bool(cond and d),
            "condicion": "el hijo vivo tenía su desechable con el fichero YA "
                         "CERRADO",
            "nada_abierto_dentro": abierto_por_alguien is False,
            "desechable": d, "sigue_el_directorio": sigue_dir,
            "sigue_el_fichero": sigue_fich,
            "lo_que_vio_el_hijo": salida, "parte": parte}


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tmp", required=True)
    p.add_argument("--salida", required=True)
    p.add_argument("--log", required=True)
    a = p.parse_args(argv)

    os.makedirs(a.tmp, exist_ok=True)
    res = {"F": [f_windows(a.tmp), f_wsl(a.tmp)],
           "G": [escena_g("ingenuo"), escena_g("bueno")]}
    with open(a.log, "w", encoding="utf-8") as log:
        log.write(json.dumps(res, ensure_ascii=False, indent=1))
    with open(a.salida, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    for x in res["F"]:
        print(f"F {x['lado']:42s} cond={x['condicion_ok']} "
              f"dir_borrado={x['dir_borrado']} fichero_borrado={x['fichero_borrado']}")
    for x in res["G"]:
        print(f"G barrido={x['barrido']:8s} cond={x['condicion_ok']} "
              f"nada_abierto={x['nada_abierto_dentro']} "
              f"sigue_dir={x['sigue_el_directorio']} "
              f"sigue_fich={x['sigue_el_fichero']} hijo={x['lo_que_vio_el_hijo']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

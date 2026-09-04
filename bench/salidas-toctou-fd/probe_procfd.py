#!/usr/bin/env python3
"""Sonda: ¿un /proc/<pid>/fd/N reabierto por OTRO proceso (cat) alcanza el inodo
fijado, o re-traversa la ruta envenenada? Esto es lo que decide si podemos
entregar una ruta estable a un motor externo que reabre por ruta.

MEDIR, no deducir (regla del proyecto)."""
import os
import subprocess
import sys

BASE = "/tmp/probe_procfd"
ALLOWED = f"{BASE}/allowed"
OUTSIDE = f"{BASE}/outside"
TARGET = f"{ALLOWED}/target"
HOLD = f"{BASE}/hold"
SECRET = "secret.txt"
DENTRO = "CONTENIDO-DENTRO"
FUERA = "SECRETO-FUERA"


def preparar():
    subprocess.run(["rm", "-rf", BASE], check=False)
    os.makedirs(OUTSIDE)
    os.makedirs(TARGET)
    open(f"{TARGET}/{SECRET}", "w").write(DENTRO + "\n")
    open(f"{OUTSIDE}/{SECRET}", "w").write(FUERA + "\n")


def envenenar():
    """Convierte TARGET (dir real) en symlink a OUTSIDE."""
    os.rename(TARGET, HOLD)
    os.symlink(OUTSIDE, TARGET)


def main():
    res = {}
    mipid = os.getpid()

    # 1) Abro el fichero DENTRO (dir real), obtengo fd, construyo la ruta estable.
    preparar()
    fd = os.open(f"{TARGET}/{SECRET}", os.O_RDONLY)
    real_abierto = os.readlink(f"/proc/self/fd/{fd}")
    ruta_estable_self = f"/proc/self/fd/{fd}"
    ruta_estable_pid = f"/proc/{mipid}/fd/{fd}"

    # 2) AHORA envenveno la ruta: TARGET pasa a symlink->OUTSIDE.
    envenenar()

    # 2a) Lectura directa por la ruta original (lo que hace un motor ingenuo):
    #     debe leer FUERA (confirma que el envenenamiento es real).
    txt_ruta = open(f"{TARGET}/{SECRET}").read().strip()
    res["lectura_ruta_original_tras_envenenar"] = txt_ruta

    # 2b) Reabrir /proc/self/fd/N en ESTE proceso (mismo tabla de fd):
    txt_self = open(ruta_estable_self).read().strip()
    res["reabrir_proc_self_mismo_proceso"] = txt_self

    # 2c) Reabrir /proc/<pid>/fd/N desde OTRO proceso (cat), como un motor externo:
    p = subprocess.run(["cat", ruta_estable_pid], capture_output=True, text=True)
    res["reabrir_proc_pid_otro_proceso_cat"] = p.stdout.strip()
    res["cat_rc"] = p.returncode
    res["cat_stderr"] = p.stderr.strip()

    # 2d) ¿Y si el hijo hereda el fd y usa /proc/self/fd/N? (pass_fds)
    os.set_inheritable(fd, True)
    p2 = subprocess.run(["cat", f"/proc/self/fd/{fd}"], capture_output=True,
                        text=True, pass_fds=[fd])
    res["reabrir_proc_self_hijo_heredado"] = p2.stdout.strip()
    res["cat2_rc"] = p2.returncode

    os.close(fd)
    res["real_abierto_al_validar"] = real_abierto
    res["esperado"] = f"{DENTRO} en 2b/2c/2d (inodo fijado); {FUERA} en 2a"
    res["veredicto_2c_estable_cross_proceso"] = (
        "OK: motor externo alcanza el inodo fijado"
        if res["reabrir_proc_pid_otro_proceso_cat"] == DENTRO
        else "FALLA: re-traversa la ruta envenenada")

    import json
    print(json.dumps(res, ensure_ascii=False, indent=2))
    subprocess.run(["rm", "-rf", BASE], check=False)


if __name__ == "__main__":
    main()

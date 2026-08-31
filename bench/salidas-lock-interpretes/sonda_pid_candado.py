"""¿De QUIÉN es el PID que queda en el candado de un trabajo?

`test_el_dueno_se_puede_saber_sin_preguntar_por_ningun_PID` compara el PID del
candado con `self.proc.pid` y falla siempre. Hay tres candidatos y el test sólo
mira uno; esta sonda los imprime los tres a la vez en vez de deducirlo.

Uso:  .venv-mcp-filex/Scripts/python.exe bench/salidas-lock-interpretes/sonda_pid_candado.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

HIJO = os.path.join(RAIZ, "pruebas", "hijo_de_trabajo.py")
VIDEO = os.path.join(RAIZ, "corpus", "video", "tipico.mp4")


def lee_evento(proc, nombre, tope=60):
    """Lee líneas de eventos del hijo hasta encontrar `nombre`."""
    import time
    t0 = time.time()
    while time.time() - t0 < tope:
        linea = proc.stdout.readline()
        if not linea:
            break
        try:
            ev = json.loads(linea)
        except Exception:
            continue
        if ev.get("evento") == nombre:
            return ev
    raise SystemExit(f"no llego el evento {nombre!r}")


def main() -> int:
    from filex import cerrojo
    from filex import servicio as S

    d = tempfile.mkdtemp(prefix="sonda-pid-")
    trabajos = os.path.join(d, "trabajos")
    os.makedirs(trabajos, exist_ok=True)

    argv = [sys.executable, HIJO, "--trabajos", trabajos,
            "--entrada", VIDEO, "--salida", os.path.join(d, "s.webm")]
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            text=True, encoding="utf-8", errors="replace",
                            cwd=RAIZ)
    try:
        arrancado = lee_evento(proc, "arrancado")
        lee_evento(proc, "en_vuelo")

        jid = arrancado["job_id"]
        duenio = cerrojo.dueno(S.clave_de(jid))
        pid_candado = int(duenio.split("\t")[0]) if duenio else None

        print("PID de ESTE proceso (el de pytest) :", os.getpid())
        print("PID de Popen  (self.proc.pid)      :", proc.pid)
        print("PID que el HIJO dice ser           :", arrancado.get("pid"))
        print("PID escrito en el CANDADO          :", pid_candado)
        print()
        print("candado == Popen ?", pid_candado == proc.pid)
        print("candado == hijo  ?", pid_candado == arrancado.get("pid"))
        print("candado == pytest?", pid_candado == os.getpid())
        print()
        print("carga completa del candado:", repr(duenio))
        return 0
    finally:
        try:
            proc.kill(); proc.wait(timeout=20); proc.stdout.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())

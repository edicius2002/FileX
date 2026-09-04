"""Arnés de repetición para N36: `test_cancelar_alcanza_al_motor_de_otro_proceso`.

Corre una selección de pytest `n` veces y **guarda la salida ÍNTEGRA de cada
pasada** en `logs/`. No canaliza a `tail`: la trampa 103 se pagó por descartar
justo la salida del caso que falla.

Testigos que acompañan a cada pasada, porque el sujeto de N36 es la carga:

* **nivel** — lo que tarda en lanzarse un proceso (`python -c pass`). Detecta el
  nivel de carga de la máquina (§3 de `CLAUDE.md`).
* **deriva** — un bucle monohilo. Detecta la deriva DENTRO de la pasada.
* **residuos** — `ffmpeg.exe` vivos antes y después (trampas 112 y 47).

Uso::

    python bench/salidas-cancelacion-inestable/tanda.py \
        --etiqueta modulo --n 10 --sel pruebas/test_cancelacion_procesos.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
LOGS = os.path.join(AQUI, "logs")

#: Tope del propio testigo. Un testigo que puede tumbar la medición no es un
#: testigo (§3 de `CLAUDE.md`).
TOPE_TESTIGO = 20.0

#: Bucle de CPU para `--carga`. Sin fin: se mata al cerrar la pasada.
_CARGA = "x=0\nwhile True:\n    x=(x*x+1)%1000003\n"


def nivel_ms() -> float:
    """Lo que cuesta lanzar un proceso. Mediana de 3, con tope."""
    v = []
    for _ in range(3):
        t0 = time.perf_counter()
        try:
            subprocess.run([sys.executable, "-c", "pass"],
                           stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,
                           timeout=TOPE_TESTIGO)
        except subprocess.TimeoutExpired:
            return TOPE_TESTIGO * 1000
        v.append((time.perf_counter() - t0) * 1000)
    return round(sorted(v)[1], 1)


def deriva_ms() -> float:
    """Un bucle monohilo de trabajo fijo. Ciego a la contención multinúcleo."""
    t0 = time.perf_counter()
    x = 0
    for i in range(400_000):
        x += i * i
    return round((time.perf_counter() - t0) * 1000, 1)


def ffmpeg_vivos() -> int:
    if sys.platform != "win32":
        return -1
    try:
        p = subprocess.run(["tasklist", "/FI", "IMAGENAME eq ffmpeg.exe", "/NH"],
                           stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, errors="replace", timeout=TOPE_TESTIGO)
    except subprocess.TimeoutExpired:
        return -1
    return len(re.findall(r"^ffmpeg\.exe", p.stdout, re.M))


_RES = re.compile(
    r"^(?:=+\s*)?(?:(\d+) failed[,\s]*)?(?:(\d+) passed)?"
    r"(?:[,\s]*(\d+) skipped)?(?:[,\s]*(\d+) error)?", re.M)


def resumen(salida: str) -> dict:
    """Lee la última línea de resumen de pytest."""
    fallos = re.findall(r"(\d+) failed", salida)
    pasan = re.findall(r"(\d+) passed", salida)
    saltan = re.findall(r"(\d+) skipped", salida)
    errores = re.findall(r"(\d+) error", salida)
    return {
        "failed": int(fallos[-1]) if fallos else 0,
        "passed": int(pasan[-1]) if pasan else 0,
        "skipped": int(saltan[-1]) if saltan else 0,
        "errors": int(errores[-1]) if errores else 0,
    }


def cuales_fallan(salida: str) -> list[str]:
    return sorted(set(re.findall(r"^FAILED (\S+)", salida, re.M)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--etiqueta", required=True)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--sel", required=True,
                    help="lo que se le pasa a pytest como selección")
    ap.add_argument("--env", action="append", default=[],
                    help="VAR=VALOR extra para el proceso de pytest")
    ap.add_argument("--carga", type=int, default=0,
                    help="procesos de CPU levantados DURANTE cada pasada. Es "
                         "una variable independiente declarada, no ruido "
                         "heredado: los fallos del módulo se dan en las "
                         "pasadas lentas y esto pregunta si la lentitud basta")
    args = ap.parse_args()

    os.makedirs(LOGS, exist_ok=True)
    entorno = dict(os.environ)
    entorno["PYTHONIOENCODING"] = "utf-8"
    for par in args.env:
        k, _, v = par.partition("=")
        entorno[k] = v

    filas = []
    for i in range(1, args.n + 1):
        cargas = [subprocess.Popen(
            [sys.executable, "-c", _CARGA], stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(args.carga)]
        antes_ff = ffmpeg_vivos()
        niv0, der0 = nivel_ms(), deriva_ms()
        t0 = time.perf_counter()
        p = subprocess.run(
            [sys.executable, "-m", "pytest", args.sel, "-v", "--durations=0",
             "-p", "no:cacheprovider"],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            encoding="utf-8", errors="replace", cwd=RAIZ, env=entorno)
        seg = round(time.perf_counter() - t0, 2)
        for c in cargas:
            try:
                c.kill()
                c.wait(timeout=20)
            except Exception:
                pass
        niv1, der1 = nivel_ms(), deriva_ms()
        despues_ff = ffmpeg_vivos()

        salida = p.stdout + "\n" + p.stderr
        log = os.path.join(LOGS, f"{args.etiqueta}-{i:02d}.log")
        with open(log, "w", encoding="utf-8") as fh:
            fh.write(salida)

        r = resumen(salida)
        fila = {
            "etiqueta": args.etiqueta, "i": i, "rc": p.returncode,
            "segundos": seg, "log": os.path.basename(log),
            "fallan": cuales_fallan(salida), **r,
            "nivel_ms_antes": niv0, "nivel_ms_despues": niv1,
            "deriva_ms_antes": der0, "deriva_ms_despues": der1,
            "ffmpeg_antes": antes_ff, "ffmpeg_despues": despues_ff,
            "carga": args.carga,
        }
        filas.append(fila)
        print(json.dumps(fila, ensure_ascii=False), flush=True)

    destino = os.path.join(AQUI, f"tanda-{args.etiqueta}.json")
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(filas, fh, ensure_ascii=False, indent=1)
    print(f"-> {destino}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

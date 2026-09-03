#!/usr/bin/env python3
"""Qué módulos de la suite puede ejecutar un runner Windows HOSPEDADO por
GitHub (`windows-latest`), MEDIDO.

    python3 ci/sonda_windows_hosted.py [--tope 90] [--json ruta.json]

**Es un fichero aparte de `ci/sonda_windows.py`, no el mismo con una bandera
distinta**, por el mismo motivo que separó a éste de `ci/sonda_linux.py`
(trampa 104): la lista que produce **no es intercambiable** con la de un
runner autoalojado. `ci/sonda_windows.py` mide una máquina con GPU real y
Docker con contenedores reales (`.github/workflows/windows-gpu.yml`, que hoy
NO EXISTE como runner registrado, ver `bench/runner-autoalojado.md`); ésta
mide `windows-latest`, que GitHub hospeda y destruye después de cada
ejecución, **sin GPU ni Docker con contenedores reales, pero con NTFS de
verdad**. Ninguna de las dos listas se puede deducir de la otra, ni de la de
Linux (`ci/linux-apto.json`) ni de la de la máquina de escritorio del
proyecto (WSL2 sobre DrvFs): **se mide donde se va a usar, siempre**.

**Sólo se puede correr DENTRO de un runner `windows-latest` real.** No hay
forma honesta de simularlo desde otra máquina Windows -- ejecutarlo aquí, en
la máquina del proyecto, mediría WSL2/DrvFs con otro intérprete y sería
exactamente el error de la trampa 104. La única corrida que cuenta es la que
sale de `.github/workflows/windows-tests.yml` con `workflow_dispatch` (entrada
`medir: true`) sobre `windows-latest`.

Mecánica idéntica a `ci/sonda_linux.py`: tope **por módulo**, no alrededor de
la suite entera (trampas 52 y 25) -- un tope global no dice cuál colgó.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PRUEBAS = RAIZ / "pruebas"

_RESUMEN = re.compile(r"^Ran (\d+) tests? in ([\d.]+)s", re.M)
_SALTOS = re.compile(r"skipped=(\d+)")
_FALLOS = re.compile(r"(?:failures|errors)=(\d+)")


def mide(modulo: str, tope: int) -> dict:
    t0 = time.monotonic()
    try:
        r = subprocess.run(
            [sys.executable, "-m", "unittest", "-v", "pruebas.%s" % modulo],
            cwd=RAIZ, capture_output=True, text=True, errors="replace",
            timeout=tope, stdin=subprocess.DEVNULL,
        )
        salida, rc, colgo = r.stdout + r.stderr, r.returncode, False
    except subprocess.TimeoutExpired as e:
        salida = (e.stdout or b"").decode("utf-8", "replace") + \
                 (e.stderr or b"").decode("utf-8", "replace")
        rc, colgo = None, True

    segundos = time.monotonic() - t0
    m = _RESUMEN.search(salida)
    corridas = int(m.group(1)) if m else 0
    saltos = sum(int(x) for x in _SALTOS.findall(salida))
    fallos = sum(int(x) for x in _FALLOS.findall(salida))

    if colgo:
        # El ultimo test que EMPEZO es el que colgo: `-v` lo imprime al entrar.
        vistos = re.findall(r"^(\w+) \(([\w.]+)\)", salida, re.M)
        veredicto, culpable = "CUELGA", (vistos[-1][0] if vistos else "?")
    elif rc == 0:
        veredicto, culpable = "APTO", ""
    else:
        veredicto, culpable = "FALLA", ""

    return {"modulo": modulo, "veredicto": veredicto, "rc": rc,
            "corridas": corridas, "saltos": saltos, "fallos": fallos,
            "segundos": round(segundos, 1), "cuelga_en": culpable}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tope", type=int, default=90,
                    help="segundos por módulo (defecto 90, como Linux)")
    ap.add_argument("--json", type=pathlib.Path,
                    default=RAIZ / "ci" / "windows-hosted-apto.json")
    args = ap.parse_args()

    modulos = sorted(p.stem for p in PRUEBAS.glob("test_*.py"))
    print("%-26s %-7s %6s %6s %6s %7s  %s" % (
        "modulo", "verdicto", "corr", "salt", "fall", "seg", "cuelga en"))
    print("-" * 82)

    filas = []
    for m in modulos:
        f = mide(m, args.tope)
        filas.append(f)
        print("%-26s %-7s %6d %6d %6d %7.1f  %s" % (
            f["modulo"], f["veredicto"], f["corridas"], f["saltos"],
            f["fallos"], f["segundos"], f["cuelga_en"]))

    aptos = [f["modulo"] for f in filas if f["veredicto"] == "APTO"]
    no_aptos_cuelga = {f["modulo"]: (f["cuelga_en"] or "?")
                        for f in filas if f["veredicto"] == "CUELGA"}
    no_aptos_falla = {f["modulo"]: "%d fallos" % f["fallos"]
                       for f in filas if f["veredicto"] == "FALLA"}

    print("-" * 82)
    print("APTOS %d de %d · %d pruebas · %d saltadas · %.1f s en total" % (
        len(aptos), len(filas),
        sum(f["corridas"] for f in filas if f["veredicto"] == "APTO"),
        sum(f["saltos"] for f in filas if f["veredicto"] == "APTO"),
        sum(f["segundos"] for f in filas if f["veredicto"] == "APTO")))
    if no_aptos_cuelga:
        print("CUELGA: %s" % ", ".join(
            "%s (%s)" % kv for kv in no_aptos_cuelga.items()))
    if no_aptos_falla:
        print("FALLA: %s" % ", ".join(
            "%s (%s)" % kv for kv in no_aptos_falla.items()))

    salida = {
        "_": ("Medido con %s el %s en windows-latest (runner hospedado por "
              "GitHub). Se regenera lanzando `.github/workflows/"
              "windows-tests.yml` con workflow_dispatch (entrada medir: "
              "true) -- correrlo en otra máquina Windows mide otro entorno "
              "y no vale (trampa 104). APTO = rc 0 dentro del tope; no "
              "significa que la prueba MIDA algo en Windows, sólo que no "
              "rompe ni cuelga." % (sys.version.split()[0], time.strftime("%Y-%m-%d"))),
        "interprete": sys.version.split()[0],
        "plataforma": sys.platform,
        "medido_en": "PENDIENTE -- rellenar con el número de `run` real de "
                     "GitHub Actions tras el `workflow_dispatch`",
        "tope_por_modulo_s": args.tope,
        "aptos": aptos,
        "no_aptos": {
            "cuelga": no_aptos_cuelga,
            "falla": no_aptos_falla,
        },
        "detalle": filas,
    }

    args.json.write_text(json.dumps(salida, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    try:
        donde = args.json.relative_to(RAIZ)
    except ValueError:
        donde = args.json
    print("\nescrito %s" % donde)
    return 0


if __name__ == "__main__":
    sys.exit(main())

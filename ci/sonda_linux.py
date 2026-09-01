#!/usr/bin/env python3
"""Qué módulos de la suite puede ejecutar un runner de Linux, MEDIDO.

    python3 ci/sonda_linux.py [--tope 120]

**No se deduce cuál corre y cuál no: se ejecuta cada uno por separado, con tope,
y se registra el `rc`.** Es la regla del proyecto —sondear en ejecución, no
deducir— aplicada al propio arnés, y hacía falta: lanzar la suite entera con el
`python3` de Linux **se queda dormida** (`hrtimer_nanosleep`, sin hijos y sin
sockets) y agota un tope de 900 s sin decir en qué módulo. Un flujo de CI que
hiciera eso quemaría seis horas de runner y devolvería un rojo que no nombra
nada.

El tope va **por módulo**, no alrededor de la suite: un tope que sólo mata al
final no dice cuál colgó. Trampas 52 y 25.

La salida es la lista que `.github/workflows/suite.yml` debe declarar. Vuelve a
ejecutarla cuando añadas un módulo de pruebas.
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
    ap.add_argument("--tope", type=int, default=120,
                    help="segundos por módulo (defecto 120)")
    ap.add_argument("--json", type=pathlib.Path, default=RAIZ / "ci" / "linux-apto.json")
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
    print("-" * 82)
    print("APTOS %d de %d · %d pruebas · %d saltadas · %.1f s en total" % (
        len(aptos), len(filas),
        sum(f["corridas"] for f in filas if f["veredicto"] == "APTO"),
        sum(f["saltos"] for f in filas if f["veredicto"] == "APTO"),
        sum(f["segundos"] for f in filas if f["veredicto"] == "APTO")))
    for estado in ("CUELGA", "FALLA"):
        malos = [f for f in filas if f["veredicto"] == estado]
        if malos:
            print("%s: %s" % (estado, ", ".join(
                "%s%s" % (f["modulo"], (" (%s)" % f["cuelga_en"]) if f["cuelga_en"] else "")
                for f in malos)))

    args.json.write_text(json.dumps(
        {"_": ("Medido con %s el %s. Se regenera con `python3 ci/sonda_linux.py`. "
               "APTO = rc 0 dentro del tope; no significa que la prueba MIDA algo "
               "en Linux, sólo que no rompe ni cuelga." % (
                   sys.version.split()[0], time.strftime("%Y-%m-%d"))),
         "interprete": sys.version.split()[0],
         "plataforma": sys.platform,
         "tope_por_modulo_s": args.tope,
         "aptos": aptos,
         "detalle": filas}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\nescrito %s" % args.json.relative_to(RAIZ))
    return 0


if __name__ == "__main__":
    sys.exit(main())

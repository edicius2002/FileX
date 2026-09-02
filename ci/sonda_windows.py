#!/usr/bin/env python3
"""Qué módulos de la suite puede ejecutar un runner de WINDOWS, MEDIDO.

    python3 ci/sonda_windows.py [--tope 120] [--json ruta.json]

**Espejo exacto de `ci/sonda_linux.py`, con las mismas reglas** (sondear en
ejecución, no deducir; tope POR MÓDULO, no alrededor de la suite entera —
trampas 52 y 25) — pero es un fichero aparte, no un `if sys.platform` dentro
del mismo, porque **la lista que produce NO es intercambiable con la de
Linux**: la trampa 104 midió que de 11 módulos aptos en un entorno y 7 en
otro, sólo 5 coinciden, y que no hay contención entre las dos listas — cada
una se mide, se congela y se declara donde se midió.

**Esto NO congela `ci/windows-apto.json` por sí solo.** El primer congelado
legítimo de esa lista es el que corre en el runner autoalojado de verdad
(`.github/workflows/windows.yml`, trabajo `medir`), porque ejecutar esta
sonda en OTRA máquina Windows (la de desarrollo, `D:\\...\\.venv-mcp-filex`)
es exactamente el error que abrió C42/trampa 104: una lista de aptitud
medida en el sitio equivocado. `bench/runner-autoalojado.md` publica el
resultado LOCAL bajo su propio nombre, `windows-local.json`, declarando
expresamente que **no es el runner** — ver ese informe antes de creerte
cualquier número de aquí.
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
    ap.add_argument("--json", type=pathlib.Path, default=None,
                    help="defecto: NO escribe ci/windows-apto.json -- "
                         "ese fichero sólo lo congela el runner de verdad")
    ap.add_argument("--excluir", action="append", default=[],
                    help="módulo a NO ejecutar (repetible). Para cuando hay "
                         "que dejar la GPU/el lock reales tranquilos: un "
                         "módulo excluido no se cuenta ni de APTO ni de "
                         "FALLA, se declara aparte.")
    args = ap.parse_args()

    modulos = sorted(p.stem for p in PRUEBAS.glob("test_*.py"))
    excluidos = [m for m in modulos if m in args.excluir]
    modulos = [m for m in modulos if m not in args.excluir]
    if excluidos:
        print("EXCLUIDOS a propósito (no se ejecutan): %s\n" % ", ".join(excluidos))
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

    salida = {"_": ("Medido con %s el %s. Se regenera con `python ci/sonda_windows.py`. "
                     "APTO = rc 0 dentro del tope; no significa que la prueba MIDA algo "
                     "en Windows, sólo que no rompe ni cuelga." % (
                         sys.version.split()[0], time.strftime("%Y-%m-%d"))),
              "interprete": sys.version.split()[0],
              "ejecutable": sys.executable,
              "plataforma": sys.platform,
              "tope_por_modulo_s": args.tope,
              "excluidos": excluidos,
              "aptos": aptos,
              "detalle": filas}

    if args.json is not None:
        args.json.write_text(json.dumps(salida, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")
        try:
            donde = args.json.relative_to(RAIZ)
        except ValueError:
            donde = args.json
        print("\nescrito %s" % donde)
    else:
        print("\n(sin --json: no se escribió ningún fichero -- "
              "pásalo explícitamente si quieres guardar el resultado)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

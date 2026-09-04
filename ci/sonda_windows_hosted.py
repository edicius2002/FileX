#!/usr/bin/env python3
"""Qué módulos de la suite puede ejecutar un runner Windows HOSPEDADO por
GitHub (`windows-latest`), MEDIDO — **con la traza de cada fallo, no sólo su
recuento**.

    python3 ci/sonda_windows_hosted.py [--tope 90] [--json ruta.json]
                                       [--logs directorio]

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

─────────────────────────────────────────────────────────────────────────────
POR QUÉ CAPTURA LA TRAZA (ronda 13, C-trazas)
─────────────────────────────────────────────────────────────────────────────
La primera versión guardaba **el recuento** de fallos por módulo, y con eso se
congeló `ci/windows-hosted-apto.json` el 03/09: cinco módulos con «N de M
fallos -- PENDIENTE de traza, motivo no verificado». **Un recuento no separa
causas** -- es la trampa 25 en el nivel del arnés: «9 de 24 fallos» tiene la
misma pinta viniendo de un motor ausente, de un puntero de LFS, de una
diferencia de sistema de ficheros o de un fallo real del producto, **y los
cuatro remedios son distintos**. El precedente es `C42` en Linux: diez módulos
que parecían diez causas eran **dos mecanismos repetidos**, y sólo se vio
leyendo la traza.

Así que esta versión:

* parsea los bloques `FAIL:` / `ERROR:` de `unittest -v` y guarda, por cada
  uno, **el nombre del test y su traceback completo** en el JSON;
* vuelca **la salida íntegra** de cada módulo a `--logs/<modulo>.log`, incluida
  la de los que fallan y la de los que cuelgan. La trampa 103 se pagó por
  canalizar a `tail` justo la salida del caso que fallaba: **un arnés que
  descarta la salida del caso que falla ha medido y no ha aprendido**;
* imprime un resumen de las trazas por pantalla, para que el log del paso de
  Actions ya sirva aunque nadie descargue el artefacto.
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

# Un bloque de fallo de unittest: 70 '=' , cabecera 'FAIL: ...' o 'ERROR: ...',
# 70 '-', el traceback, y hasta la siguiente linea de 70 '=' o '-'.
_BLOQUE = re.compile(
    r"^={70}\n(FAIL|ERROR):[ ]+(.*?)\n-{70}\n(.*?)(?=^={70}\n|^-{70}\n)",
    re.M | re.S)

# Tope por traza: una traza larguisima no puede tapar a las demas en el log.
TOPE_TRAZA = 6000


def _trazas(salida: str) -> list[dict]:
    """Los bloques FAIL/ERROR de una salida de `unittest -v`, con traceback."""
    fuera = []
    for tipo, prueba, traza in _BLOQUE.findall(salida):
        traza = traza.rstrip()
        recortada = len(traza) > TOPE_TRAZA
        if recortada:
            # Recorta por el PRINCIPIO: la ultima linea es la excepcion, que es
            # justo lo que identifica la causa.
            traza = "[... %d caracteres recortados ...]\n%s" % (
                len(traza) - TOPE_TRAZA, traza[-TOPE_TRAZA:])
        fuera.append({"tipo": tipo, "prueba": prueba.strip(),
                      "traza": traza, "recortada": recortada})
    return fuera


def mide(modulo: str, tope: int, logs: pathlib.Path | None) -> dict:
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

    # La salida ENTERA a disco, tambien --y sobre todo-- la de los que fallan
    # y la de los que cuelgan (trampa 103).
    ruta_log = ""
    if logs is not None:
        logs.mkdir(parents=True, exist_ok=True)
        f = logs / ("%s.log" % modulo)
        f.write_text(salida, encoding="utf-8", errors="replace")
        try:
            ruta_log = str(f.relative_to(RAIZ))
        except ValueError:
            ruta_log = str(f)

    return {"modulo": modulo, "veredicto": veredicto, "rc": rc,
            "corridas": corridas, "saltos": saltos, "fallos": fallos,
            "segundos": round(segundos, 1), "cuelga_en": culpable,
            "trazas": _trazas(salida), "log": ruta_log,
            "bytes_de_salida": len(salida)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tope", type=int, default=90,
                    help="segundos por módulo (defecto 90, como Linux)")
    ap.add_argument("--json", type=pathlib.Path,
                    default=RAIZ / "ci" / "windows-hosted-apto.json")
    ap.add_argument("--logs", type=pathlib.Path,
                    default=RAIZ / "ci-windows-hosted-logs",
                    help="directorio donde volcar la salida ÍNTEGRA de cada "
                         "módulo (vacío para no volcar nada)")
    args = ap.parse_args()

    logs = args.logs if str(args.logs) else None
    modulos = sorted(p.stem for p in PRUEBAS.glob("test_*.py"))
    print("%-26s %-7s %6s %6s %6s %7s  %s" % (
        "modulo", "verdicto", "corr", "salt", "fall", "seg", "cuelga en"))
    print("-" * 82)

    filas = []
    for m in modulos:
        f = mide(m, args.tope, logs)
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

    # Las TRAZAS por pantalla: el log del paso de Actions tiene que servir sin
    # descargar el artefacto.
    for f in filas:
        if f["veredicto"] == "APTO" or not f["trazas"]:
            continue
        print("\n" + "=" * 82)
        print("TRAZAS de %s -- %d bloque(s), salida íntegra en %s"
              % (f["modulo"], len(f["trazas"]), f["log"] or "(sin volcar)"))
        print("=" * 82)
        for t in f["trazas"]:
            print("\n--- %s: %s" % (t["tipo"], t["prueba"]))
            print(t["traza"])

    salida = {
        "_": ("Medido con %s el %s en windows-latest (runner hospedado por "
              "GitHub). Se regenera lanzando `.github/workflows/"
              "windows-tests.yml` con workflow_dispatch (entrada medir: "
              "true) -- correrlo en otra máquina Windows mide otro entorno "
              "y no vale (trampa 104). APTO = rc 0 dentro del tope; no "
              "significa que la prueba MIDA algo en Windows, sólo que no "
              "rompe ni cuelga. Cada fila de `detalle` trae `trazas` con el "
              "nombre y el traceback de cada FAIL/ERROR, y `log` con la ruta "
              "de la salida íntegra: un recuento no separa causas (trampa 25 "
              "en el nivel del arnés)." % (sys.version.split()[0], time.strftime("%Y-%m-%d"))),
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

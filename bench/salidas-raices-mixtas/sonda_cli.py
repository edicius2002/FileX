"""N35 — la TERCERA superficie, de extremo a extremo: la CLI real.

El informe mide el nucleo (`FileX._resolver`) y MCP (`Raices.asegurar`). El
nucleo es la via de CLI, watcher y API, asi que en teoria las tres quedan
cubiertas — pero eso es una deduccion, y la regla del proyecto es sondear en
ejecucion. Esta sonda lanza `python -m filex` **como proceso**, con
`--raiz` repetida, y mira el codigo de salida y el mensaje.

Lo que tiene que verse:

  * con `--raiz <unidad> --raiz <legitima>`, la CLI **arranca** y convierte
    dentro de la legitima  (antes: no arrancaba, `ValueError` por el conjunto)
  * con esa misma invocacion, sigue **denegando** lo de fuera
  * con `--raiz <unidad>` sola, **no arranca**  (N7 no reabierta)

Salida: bench/salidas-raices-mixtas/cli.json
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))


def correr(args, cwd) -> dict:
    p = subprocess.run([sys.executable, "-m", "filex"] + args,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=cwd, timeout=180,
                       stdin=subprocess.DEVNULL)
    return {"argv": args, "rc": p.returncode,
            "stdout": (p.stdout or "").strip()[-400:],
            "stderr": (p.stderr or "").strip()[-400:]}


def main() -> int:
    base = tempfile.mkdtemp(prefix="filex-n35-cli-")
    legit = os.path.join(base, "legit")
    hermano = os.path.join(base, "hermano")
    os.makedirs(legit, exist_ok=True)
    os.makedirs(hermano, exist_ok=True)

    origen = os.path.join(RAIZ, "corpus", "imagen", "tipico.png")
    if not os.path.exists(origen) or os.path.getsize(origen) < 1000:
        print("ABORTA: el corpus es un puntero de LFS o falta (trampa 34/107)")
        return 2
    dentro = os.path.join(legit, "entrada.png")
    fuera = os.path.join(hermano, "entrada.png")
    shutil.copy2(origen, dentro)
    shutil.copy2(origen, fuera)

    unidad = os.path.splitdrive(os.path.abspath(legit))[0] + os.sep
    casos = {
        # el caso de N35: mixta. Antes ni siquiera arrancaba.
        "MIXTA_convierte_dentro_de_su_raiz": [
            "--raiz", unidad, "--raiz", legit,
            "convertir", dentro, os.path.join(legit, "salida.webp")],
        # y con la MISMA invocacion, lo de fuera se sigue denegando
        "MIXTA_deniega_lo_de_fuera": [
            "--raiz", unidad, "--raiz", legit,
            "convertir", fuera, os.path.join(legit, "salida2.webp")],
        # N7: sin ninguna raiz util, no se arranca
        "SOLO_UNIDAD_no_arranca": [
            "--raiz", unidad,
            "convertir", dentro, os.path.join(legit, "salida3.webp")],
        # control: solo la legitima, tiene que comportarse igual que la mixta
        "CONTROL_solo_legitima": [
            "--raiz", legit,
            "convertir", dentro, os.path.join(legit, "salida4.webp")],
    }

    res = {"plataforma": sys.platform, "base": base, "unidad": unidad,
           "celdas": {}}
    for nombre, args in casos.items():
        c = correr(args, cwd=RAIZ)
        # El veredicto se lee del disco, no del mensaje: lo que importa es si
        # el fichero de salida existe (trampa 25: un rc no basta).
        destino = args[-1]
        c["salida_existe"] = os.path.exists(destino)
        c["salida_bytes"] = os.path.getsize(destino) if c["salida_existe"] else 0
        res["celdas"][nombre] = c

    destino_json = os.path.join(AQUI, "cli.json")
    with open(destino_json, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)

    print("%-38s %4s %8s %10s" % ("caso", "rc", "salida?", "bytes"))
    for nombre, c in res["celdas"].items():
        print("%-38s %4s %8s %10s" % (
            nombre, c["rc"], c["salida_existe"], c["salida_bytes"]))
    print()
    for nombre, c in res["celdas"].items():
        m = (c["stderr"] or c["stdout"]).replace("\n", " ")[:110]
        print("  %-38s %s" % (nombre, m))
    print("\n-> %s" % destino_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

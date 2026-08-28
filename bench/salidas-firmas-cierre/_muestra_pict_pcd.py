"""C37 - Censo de cabecera de PICT y PCD con TRES semillas distintas.

Escribe cada destino desde tres entradas de contenido y geometria distintos
(§3 de CLAUDE.md, el sesgo de SEMILLA: si no varias la entrada, mides tu
entrada y no el formato). Vuelca los primeros 4 KB de cada salida y calcula
el prefijo comun byte a byte de las tres, que es lo unico que puede ser un
marcador.

Uso:  python bench/salidas-firmas-cierre/_muestra_pict_pcd.py <dir_desechable>
"""
import hashlib
import json
import os
import subprocess
import sys

TIMEOUT = 120
NLEER = 4096

DESTINOS = ["pict", "pct", "pcd", "pcds", "palm", "map", "hrz", "otb", "wbmp"]


def semillas(tmp):
    """Tres entradas distintas: contenido, geometria y paleta distintos."""
    fuera = []
    recetas = [
        ("s1", ["-size", "192x128", "gradient:red-blue"]),
        ("s2", ["-size", "96x64", "plasma:fractal"]),
        ("s3", ["-size", "64x64", "xc:white", "-fill", "black",
                "-draw", "rectangle 8,8 40,40"]),
    ]
    for nombre, receta in recetas:
        d = os.path.join(tmp, "sem_" + nombre)
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, nombre + ".png")
        orden = ["magick"] + receta + ["-seed", "7", p]
        r = subprocess.run(orden, stdin=subprocess.DEVNULL,
                           capture_output=True, timeout=TIMEOUT)
        if r.returncode != 0 or not os.path.exists(p):
            raise SystemExit("no pude construir la semilla %s: %s"
                             % (nombre, r.stderr[:300]))
        fuera.append((nombre, p))
    return fuera


def prefijo_comun(cabs):
    """Bytes iguales en TODAS las muestras, posicion a posicion.

    Devuelve una lista de tramos (desplazamiento, bytes) de longitud >= 2.
    No exige que el tramo empiece en 0: el marcador de PICT esta en el 522 y
    el de PCD en el 0x800.
    """
    n = min(len(c) for c in cabs)
    iguales = [all(c[i] == cabs[0][i] for c in cabs) for i in range(n)]
    tramos, i = [], 0
    while i < n:
        if iguales[i]:
            j = i
            while j < n and iguales[j]:
                j += 1
            if j - i >= 2:
                tramos.append((i, cabs[0][i:j]))
            i = j
        else:
            i += 1
    return tramos


def main():
    tmp = sys.argv[1]
    sems = semillas(tmp)
    salida = {"destinos": {}, "semillas": [s[0] for s in sems]}
    for dest in DESTINOS:
        filas, cabs = [], []
        for nombre, origen in sems:
            d = os.path.join(tmp, "out_" + dest)
            os.makedirs(d, exist_ok=True)
            p = os.path.join(d, nombre + "." + dest)
            orden = ["magick", origen, p]
            try:
                r = subprocess.run(orden, stdin=subprocess.DEVNULL,
                                   capture_output=True, timeout=TIMEOUT)
                rc = r.returncode
                err = r.stderr.decode("utf-8", "replace")[:200]
            except subprocess.TimeoutExpired:
                rc, err = "timeout", ""
            fila = {"semilla": nombre, "rc": rc, "stderr": err}
            if os.path.exists(p) and os.path.getsize(p) > 0:
                with open(p, "rb") as fh:
                    cab = fh.read(NLEER)
                cabs.append(cab)
                fila["bytes"] = os.path.getsize(p)
                fila["sha256"] = hashlib.sha256(cab).hexdigest()[:16]
                fila["cab_hex_0_64"] = cab[:64].hex()
                fila["cab_hex_508_540"] = cab[508:540].hex()
                fila["cab_hex_2040_2080"] = cab[2040:2080].hex()
            filas.append(fila)
        entrada = {"muestras": filas, "n_ok": len(cabs)}
        if len(cabs) >= 2:
            tramos = prefijo_comun(cabs)
            entrada["tramos_comunes"] = [
                {"desp": d, "n": len(b), "hex": b.hex(),
                 "ascii": b.decode("latin-1").replace("\x00", ".")}
                for d, b in tramos]
        salida["destinos"][dest] = entrada
    print(json.dumps(salida, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

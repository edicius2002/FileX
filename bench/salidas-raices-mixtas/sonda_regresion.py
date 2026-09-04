"""N35 — la sonda de NO REGRESION: mide la clase REAL, no un candidato.

`sonda_candidatos.py` y `sonda_superficies.py` miden SUBCLASES que
reimplementan `_preparar`, asi que su resultado no cambia al arreglar
`filex/confinamiento.py` — y eso es correcto para comparar politicas, pero
inutil para comprobar que el arreglo hace lo que dice. Esta sonda usa
`Confinamiento` TAL CUAL, para poder correrse en dos commits y comparar.

    # antes
    git stash push filex/confinamiento.py
    python sonda_regresion.py --salida regresion_antes.json
    git stash pop
    # despues
    python sonda_regresion.py --salida regresion_despues.json

Lo que hay que ver en la comparacion, y que es TODO el encargo:

  * las filas MIXTAS pasan de `sin_acceso` a leer su raiz legitima  (N35 cerrado)
  * la fila `2_solo_raiz_de_unidad` NO se mueve                     (N7 no reabierto)
  * ninguna fila gana un acceso que no tuviera                      (no hay fuga)

Salida: bench/salidas-raices-mixtas/regresion_{antes,despues}.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)

from filex.confinamiento import Confinamiento, Denegado  # noqa: E402


def medir(lectura, escritura, objetivos, destino_escr) -> dict:
    """La clase REAL, sin sustituir nada."""
    celda = {"lectura_declarada": list(lectura),
             "escritura_declarada": None if escritura is None else list(escritura)}
    try:
        c = Confinamiento(lectura, escritura)
    except ValueError as e:
        celda["constructor"] = "ValueError"
        celda["mensaje"] = str(e)
        celda["lee"] = {k: False for k in objetivos}
        celda["escribe"] = False
        return celda
    celda["constructor"] = "ok"
    celda["lectura_efectiva"] = list(c.lectura)
    celda["escritura_efectiva"] = list(c.escritura)
    lee = {}
    for nombre, ruta in objetivos.items():
        if not os.path.exists(ruta):
            lee[nombre] = None
            continue
        try:
            c.resolver(ruta)
            lee[nombre] = True
        except Denegado:
            lee[nombre] = False
    celda["lee"] = lee
    try:
        c.resolver(destino_escr, escritura=True)
        celda["escribe"] = True
    except Denegado:
        celda["escribe"] = False
    return celda


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="regresion_despues.json")
    # La base tiene que ser LA MISMA en las dos corridas o las rutas no son
    # comparables: se pasa por parametro y se declara en el JSON.
    ap.add_argument("--base", default=None)
    args = ap.parse_args()

    base = args.base or tempfile.mkdtemp(prefix="filex-n35-reg-")
    legit = os.path.join(base, "legit")
    escr = os.path.join(base, "escr")
    hermano = os.path.join(base, "hermano")
    for d in (legit, escr, hermano):
        os.makedirs(d, exist_ok=True)
    o1 = os.path.join(legit, "dentro.txt")
    o2 = os.path.join(hermano, "fuera.txt")
    for p, t in ((o1, "dentro\n"), (o2, "fuera\n")):
        if not os.path.exists(p):
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(t)

    objetivos = {
        "O1_dentro_de_la_raiz_legitima": o1,
        "O2_hermano_no_declarado": o2,
        "O3_otra_unidad": os.path.join(RAIZ, "corpus", "imagen", "tipico.png"),
        "O4_bajo_la_unidad_fuera_de_legit": r"C:\Windows\win.ini",
    }

    filas = {
        "1_solo_legitima_CONTROL": ([legit], None),
        "2_solo_raiz_de_unidad_N7": (["C:\\"], None),
        "3_MIXTA_mala_primero_N35": (["C:\\", legit], None),
        "4_MIXTA_buena_primero_N35": ([legit, "C:\\"], None),
        "5_dos_malas": (["C:\\", "D:\\"], None),
        "6_dos_buenas": ([legit, escr], None),
        "7_MIXTA_con_UNC": ([r"\\servidor\recurso", legit], None),
        "8_vacia": ([], None),
        "9_escritura_SOLO_raiz_de_unidad": ([legit], ["C:\\"]),
        "10_escritura_MIXTA": ([legit], ["C:\\", escr]),
        "11_escritura_declarada_VACIA": ([legit], []),
    }

    res = {"plataforma": sys.platform, "python": sys.version.split()[0],
           "base": base, "objetivos": objetivos,
           "destino_escritura": escr, "celdas": {}}
    for nombre, (lec, esc) in filas.items():
        res["celdas"][nombre] = medir(lec, esc, objetivos, escr)

    destino = os.path.join(AQUI, args.salida)
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)

    print("base: %s\n" % base)
    print("%-34s %-12s %-6s %s" % ("fila", "constructor", "escr", "lee O1..O4"))
    for nombre in filas:
        c = res["celdas"][nombre]
        if c["constructor"] != "ok":
            print("%-34s %-12s %-6s %s" % (nombre, "ValueError", "-", "-"))
        else:
            s = "".join("L" if c["lee"][k] else "." for k in objetivos)
            print("%-34s %-12s %-6s %s" % (nombre, "ok", c["escribe"], s))
    print("\n-> %s" % destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""K1 / hito 5 — genera las tablas de aristas DESDE `sonda.json`, por submotor.

No se escriben a mano. El criterio es mecánico y por eso se puede auditar:

* **`REAL`** = `rc == 0`, la salida existe **y** el centinela `FILEXSENTINELA7743`
  sobrevive. El umbral de caracteres no es 0: `txtwrite` emite 1-3 caracteres de
  basura en un PDF sin texto (trampa 4 de `CLAUDE.md`), así que «conserva texto»
  es >= 10 — pero exigir además el centinela es más fuerte y sale gratis.
* **`NOMINAL`** = se ejecutó y NO salió bien. Es la mitad del valor del fichero.
* Lo que no está en `sonda.json` no aparece en ninguna tabla.

**No se deduplica por par de formatos.** Si dos submotores hacen `docx→pdf`, las
dos aristas entran y **elige el grafo**, que es justamente para lo que está. El
coste de cada arista es **su tiempo medido**, en segundos.

    python bench/salidas-hito5/_tabla.py
"""
from __future__ import annotations

import json
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
MIN_CAR = 10

#: Destinos donde la sonda de texto es CIEGA y por tanto no puede exigir el
#: centinela. No es una excepción de conveniencia, es una limitación medida:
#: MOBI y AZW3 comprimen el texto (PalmDoc/LZ77) y `FILEXSENTINELA7743` no
#: aparece literal en el binario aunque el libro esté entero; PNG es un raster.
#: Aquí el veredicto se queda en `rc == 0` y bytes, **y se dice**.
CIEGOS = {"mobi", "azw3", "png", "jpg", "webp"}

#: Sustituye el `n=1` de la sonda por la mediana de `n=9` donde la haya.
MEDIANAS = os.path.join(AQUI, "medianas.json")


def coste(ms: float) -> float:
    """**Un salto vale 1,0; el tiempo medido solo desempata.** 1 s = +0,01.

    La primera versión de esta función devolvía **los segundos medidos**, que
    parecía lo más honesto —una cifra medida en vez de una constante— y **da una
    elección peor. MEDIDO** (`bench/hito5-documental.md` §6): con el coste en
    segundos el grafo resuelve `docx→pdf` como **`docx→html→pdf`** (Pandoc 1,0 s
    + LibreOffice 2,2 s = 3,2) en vez de `docx→pdf` con LibreOffice (6,5 s).
    Es **la mitad de tiempo y una conversión peor**: pasar un DOCX por HTML tira
    la maquetación, y el grafo no lo sabe porque **nadie le ha dado un precio al
    salto de más**.

    Con `1,0 + ms/100 000` el número de saltos vuelve a mandar —que es la
    convención de los motores nativos, todos entre 1,0 y 1,2— y el tiempo
    decide **entre motores que hacen la misma arista**, que es justo donde el
    tiempo es la variable correcta: LibreOffice (1,065), Pandoc (1,072) y
    Calibre (1,102) para `docx→pdf`.
    """
    return round(1.0 + ms / 100000.0, 3)


def main() -> int:
    with open(os.path.join(AQUI, "sonda.json"), encoding="utf-8") as f:
        res = json.load(f)
    med9 = {}
    if os.path.isfile(MEDIANAS):
        with open(MEDIANAS, encoding="utf-8") as f:
            med9 = {k: v["mediana"] for k, v in json.load(f)["muestras"].items()
                    if k != "_vacio"}

    reales, muertas, dudosas = {}, {}, []
    for r in res:
        o, d, motor = r["origen"], r["destino"], r["motor"]
        rast = r.get("rasteriza_esperado", False)
        ok = r.get("rc") == 0 and r.get("bytes", 0) > 0
        if ok and not rast and d not in CIEGOS:
            if r.get("caracteres", 0) < MIN_CAR or not r.get("centinela"):
                ok = False
                dudosas.append((r["id"], motor, o, d, r.get("caracteres"),
                                r.get("centinela")))
        ms = med9.get(r["id"], r.get("ms", 0.0))
        if ok:
            reales.setdefault(motor, {})[(o, d)] = (r["id"], coste(ms), rast)
        else:
            muertas.setdefault(motor, {})[(o, d)] = (r["id"],)

    for motor in sorted(set(reales) | set(muertas)):
        print(f"# ---------------- {motor} "
              f"({len(reales.get(motor, {}))} reales, "
              f"{len(muertas.get(motor, {}))} nominales)")
        for nombre, tabla in (("_MEDIDAS", reales.get(motor, {})),
                              ("_MUERTAS", muertas.get(motor, {}))):
            print(f"    {nombre} = {{")
            for (o, d), v in sorted(tabla.items()):
                print(f'        ("{o}", "{d}"): {v!r},')
            print("    }")
        print()

    if dudosas:
        print("# rc=0 pero sin centinela o sin texto (no entran como REAL):")
        for x in dudosas:
            print("#  ", x)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

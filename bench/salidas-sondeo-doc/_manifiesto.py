# -*- coding: utf-8 -*-
"""S3 — `MANIFIESTO.md` de las salidas binarias, que después se borran.

`CLAUDE.md` §6: no se versionan salidas regenerables. Queda el nombre, el
`sha256`, el tamaño y **la orden exacta que las reproduce**.

**Se construye desde los `.json` MEDIDOS, no recorriendo el disco**, y no es un
detalle de estilo: recorrer el disco hace que el manifiesto dependa de qué
directorios sigan sin borrar en el momento de generarlo — la primera versión de
este fichero perdió cuatro filas por eso. El `sha256` de cada salida ya está
dentro del JSON que lo midió, que es donde tiene sentido que esté.

    python bench/salidas-sondeo-doc/_manifiesto.py
"""
from __future__ import annotations

import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAL = os.path.join(RAIZ, "bench", "salidas-sondeo-doc")


def carga(nombre):
    p = os.path.join(SAL, nombre)
    if not os.path.isfile(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def fila(nombre, bytes_, sha256, orden):
    s = f"`{(sha256 or '')[:32]}…`" if sha256 else "—"
    return f"| `{nombre}` | {bytes_ or 0} | {s} | {orden} |"


def main() -> int:
    for f in (sys.stdout, sys.stderr):
        try:
            f.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    L = ["# MANIFIESTO — `bench/salidas-sondeo-doc/` (agente S3)", "",
         "**Las salidas binarias están BORRADAS** (`CLAUDE.md` §6). Aquí queda de",
         "cada una el tamaño, el `sha256` y la orden que la reproduce.", "",
         "Lo que SÍ se versiona de este directorio: los arneses (`_*.py`), los",
         "`.json` de resultados, los `.log` y **las tres semillas escritas a mano**",
         "(`entradas/entrada.csv`, `.svg`, `.tex`), que son fuente y no salida.", "",
         "> **AVISO: los `sha256` de las salidas de CALIBRE no reproducen — MEDIDO**",
         "> (`bench/sondeo-documental.md` §5). Con n=3, `mobi→epub` dio **tres",
         "> tamaños distintos** (18 333 / 24 270 / 30 876 B) y `epub→pdf` dio el",
         "> mismo tamaño con **tres `sha256` distintos**. El motivo está al miembro:",
         "> de los 11 ficheros del EPUB, **8 son idénticos byte a byte —incluido el",
         "> texto—** y cambian `content.opf`, `toc.ncx` (UUID) y `cover_image.jpg`,",
         "> que es una **portada generada**. Las salidas de **pandoc sí son byte a",
         "> byte reproducibles** (`md→html`: un solo `sha` en 3 ejecuciones).",
         "> **Para una salida de Calibre, lo que hay que comparar es el `sha256` del",
         "> miembro que lleva el texto, no el del fichero.**", "",
         "**Reproducir, en este orden** (Docker levantado, imagen `filex-c13`):", "",
         "```",
         "python bench/salidas-sondeo-doc/_sonda23.py       # 23 aristas, ~190 s",
         "python bench/salidas-sondeo-doc/_sonda_p5.py      # pendiente 5, ~150 s",
         "python bench/salidas-sondeo-doc/_d2.py            # defectos del verificador + ida y vuelta",
         "python bench/salidas-sondeo-doc/_repro.py         # reproducibilidad, n=3",
         "python bench/salidas-sondeo-doc/_tabla_sondeo.py  # escribe filex/sondeo/doc_*.json",
         "python bench/salidas-sondeo-doc/_manifiesto.py",
         "```", "",
         "`_sonda23.py` fabrica las semillas que le falten (`entrada.mobi` y",
         "`entrada.azw3`, desde `epub→mobi`/`epub→azw3`, C03/C04 de K1);",
         "`_sonda_p5.py` fabrica `entrada.xlsx` (Q01) y `entrada.pptx` (Q02). Las",
         "siete semillas de texto se REUSAN de `bench/salidas-hito5/entradas/` sin",
         "copiarlas.", "",
         "| fichero | bytes | sha256 | reproduce |", "|---|---:|---|---|"]

    d = carga("sonda23.json")
    if d:
        for c in d.get("casos", []):
            if not c.get("bytes"):
                continue
            L.append(fila(f"out/{c['id']}_{c['motor'][4:]}_{c['origen']}2{c['destino']}"
                          f".{c['destino']}", c.get("bytes"), c.get("sha256"),
                          f"`_sonda23.py --solo {c['id']}`"))
    p5 = carga("sonda-p5.json")
    if p5:
        for c in p5:
            if not c.get("bytes"):
                continue
            L.append(fila(f"out-p5/{c['id']}_{c['origen']}2{c['destino']}.{c['destino']}",
                          c.get("bytes"), c.get("sha256"), f"`_sonda_p5.py --solo {c['id']}`"))
    dd = carga("d2.json")
    if dd:
        for c in dd.get("B_aristas_REAL_hacia_texto", []):
            if not c.get("bytes"):
                continue
            L.append(fila(f"out-d2/R_{c['motor'][4:]}_{c['origen']}2{c['destino']}"
                          f".{c['destino']}", c.get("bytes"), c.get("sha256"), "`_d2.py`"))
    rp = carga("repro.json")
    if rp:
        for r in rp:
            for f_ in r.get("filas", []):
                if not f_.get("bytes"):
                    continue
                o, dd_ = r["arista"].split(">")
                L.append(fila(f"out-repro/{r['motor'][4:]}_{o}2{dd_}_{f_['i']}.{dd_}",
                              f_.get("bytes"), f_.get("sha256"),
                              "`_repro.py` (**no reproducible**)"))

    L += ["", "## Las órdenes exactas", "",
          "* `sonda-p5.json` lleva el **`argv` literal** de cada caso, con el",
          "  `docker run`, los dos `--mount` y el tope de dentro.",
          "* `sonda23.json` **no lleva `argv` a propósito**: esas 23 conversiones",
          "  las hace `FileX.convertir()`, y la orden la construye",
          "  `filex.motor_contenedor._argv_docker`. Reproducirlas es llamar al",
          "  núcleo, no copiar una línea.",
          "* `d2.json` §A no invoca ningún motor: son tres ficheros escritos a mano",
          "  pasados por `filex.contrato.verificar()`.", ""]

    ruta = os.path.join(SAL, "MANIFIESTO.md")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(ruta, len(L), "líneas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

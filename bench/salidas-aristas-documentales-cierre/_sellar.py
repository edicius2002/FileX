# -*- coding: utf-8 -*-
"""worker7 — construye `filex/sondeo/doc_libreoffice.json` y `doc_pandoc.json`
NUEVOS a partir de `resondeo55.json` (RESONDEO real, no resellado por
algoritmo). Solo lleva entradas para pares `_DECLARADAS` — igual que el
convenio ya establecido por worker2 en ronda 7: las `_MEDIDAS` no necesitan
superposición porque ya nacen `REAL` en `_aristas()`.

Las dos aristas excluidas a propósito (`pptx>png`, `svg>png` — ver
`motor_contenedor.LibreOfficeEnContenedor._DECLARADAS`, comentario) se
CONSERVAN del JSON viejo sin re-medir: siguen sin tener tupla en
`_DECLARADAS`, así que `sondeo.aplicar()` las ignora, pero es evidencia real
que no hay motivo para tirar.

    python bench/salidas-aristas-documentales-cierre/_sellar.py
"""
from __future__ import annotations

import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import huella  # noqa: E402
from filex.motor_contenedor import LibreOfficeEnContenedor, PandocEnContenedor  # noqa: E402

SAL = os.path.dirname(os.path.abspath(__file__))
DIR_SONDEO = os.path.join(RAIZ, "filex", "sondeo")
INFORME = "bench/aristas-documentales-cierre.md"
FECHA = "2026-09-03"

#: (motor, o, d) que este resondeo cubrió y que corresponden a `_DECLARADAS`
#: (no a `_MEDIDAS`, que no necesitan JSON). Los 14 de LibreOffice y los 16 de
#: Pandoc.
DECLARADAS_LO = [("rtf", "odt"), ("rtf", "docx"), ("html", "odt"),
                 ("txt", "odt"), ("odt", "html"), ("docx", "rtf"),
                 ("csv", "xlsx"), ("xlsx", "pdf"), ("xlsx", "csv"),
                 ("xlsx", "html"), ("csv", "pdf"), ("pptx", "pdf"),
                 ("pptx", "odp"), ("svg", "pdf")]
DECLARADAS_PANDOC = [("html", "epub"), ("html", "odt"), ("html", "rtf"),
                     ("docx", "odt"), ("epub", "docx"), ("epub", "txt"),
                     ("rtf", "md"), ("rtf", "html"), ("md", "rtf"),
                     ("md", "pptx"), ("md", "tex"), ("docx", "tex"),
                     ("tex", "docx"), ("tex", "html"), ("tex", "pdf"),
                     ("pptx", "md")]


def cargar_casos() -> dict:
    with open(os.path.join(SAL, "resondeo55.json"), encoding="utf-8") as f:
        d = json.load(f)
    return {(x["motor"], x["origen"], x["destino"]): x for x in d["casos"]}


def entrada_aristas(motor: str, pares: list, casos: dict) -> dict:
    out = {}
    for o, d in pares:
        x = casos.get((motor, o, d))
        if x is None:
            raise SystemExit(f"falta el caso resondeado {motor}:{o}>{d}")
        if x.get("rc") != 0 or x.get("contrato") == "fallo":
            raise SystemExit(f"{motor}:{o}>{d} no salio bien: rc={x.get('rc')} "
                             f"contrato={x.get('contrato')}")
        motivo = (f"{x.get('bytes')} B, {x.get('caracteres')} caracteres, "
                 f"contrato {x.get('contrato')}")
        out[f"{o}>{d}"] = {"estado": "real", "ms": x.get("ms"),
                           "motivo": motivo, "caso": x["id"]}
    return out


def legado(motor_json: dict, claves: tuple) -> dict:
    """Las entradas que YA estaban en el JSON viejo y no se re-miden esta
    ronda (`pptx>png`, `svg>png`): se conservan tal cual."""
    out = {}
    for k in claves:
        if k in motor_json.get("aristas", {}):
            out[k] = motor_json["aristas"][k]
    return out


def main() -> None:
    casos = cargar_casos()

    with open(os.path.join(DIR_SONDEO, "doc_libreoffice.json"), encoding="utf-8") as f:
        viejo_lo = json.load(f)
    with open(os.path.join(DIR_SONDEO, "doc_pandoc.json"), encoding="utf-8") as f:
        viejo_pandoc = json.load(f)

    aristas_lo = entrada_aristas("doc_libreoffice", DECLARADAS_LO, casos)
    aristas_lo.update(legado(viejo_lo, ("pptx>png", "svg>png")))

    aristas_pandoc = entrada_aristas("doc_pandoc", DECLARADAS_PANDOC, casos)

    huella.olvidar()
    h_lo = huella.de_motor(LibreOfficeEnContenedor)
    huella.olvidar()
    h_pandoc = huella.de_motor(PandocEnContenedor)
    interprete = huella.interprete_actual()

    build_lo = viejo_lo["build"]
    build_pandoc = viejo_pandoc["build"]

    nota_lo = (
        "RESONDEADO (no resellado por algoritmo) el 2026-09-03 por worker7, "
        "carril aristas-documentales-doc: `bench/aristas-documentales-cierre.md` "
        "anadio 8 tuplas a `_DECLARADAS` (csv>xlsx, xlsx>pdf, xlsx>csv, "
        "xlsx>html, csv>pdf, pptx>pdf, pptx>odp, svg>pdf) para cerrar el "
        "hueco de `fx.destinos('csv') -> []`. Eso cambio el AST de la clase "
        "y CADUCO la huella `motor` (de ffe3c41451f77538 a 48e14e7a35210f60); "
        "`invocacion` y `contrato` no se tocaron y no cambiaron. Las 24 "
        "aristas REAL de este motor (10 `_MEDIDAS` + 14 `_DECLARADAS`) se "
        "REMIDIERON de verdad con `FileX.convertir()` real (contrato de cinco "
        "puntos, censo del punto 5 incluido) via "
        "`bench/salidas-aristas-documentales-cierre/_resondeo55.py`, no se "
        "copio el JSON viejo con la huella cambiada. `pptx>png` y `svg>png` "
        "siguen SIN tupla en `_DECLARADAS` a proposito (rasterizan y "
        "`_aristas()` no puede marcarlas `rasteriza=True` sin un tercer campo "
        "en la tupla - ver el comentario en motor_contenedor.py): sus dos "
        "entradas se conservan del sellado de worker2 (ronda 7, 2026-09-02) "
        "sin re-medir, porque siguen siendo evidencia real aunque el codigo "
        "de hoy no las use."
    )
    nota_pandoc = (
        "RESONDEADO (no resellado por algoritmo) el 2026-09-03 por worker7, "
        "carril aristas-documentales-doc: `bench/aristas-documentales-cierre.md` "
        "anadio 7 tuplas a `_DECLARADAS` (md>pptx, md>tex, docx>tex, tex>docx, "
        "tex>html, tex>pdf, pptx>md), ninguna rasteriza. Eso cambio el AST de "
        "la clase y CADUCO la huella `motor` (de f750a96c5bcb196a a "
        "08817e0e76ef187f); `invocacion` y `contrato` no se tocaron y no "
        "cambiaron. Las 31 aristas REAL de este motor (15 `_MEDIDAS` + 16 "
        "`_DECLARADAS`) se REMIDIERON de verdad con `FileX.convertir()` real "
        "(contrato de cinco puntos, censo del punto 5 incluido) via "
        "`bench/salidas-aristas-documentales-cierre/_resondeo55.py`, no se "
        "copio el JSON viejo con la huella cambiada."
    )

    nuevo_lo = {
        "motor": "doc_libreoffice", "build": build_lo, "fecha": FECHA,
        "informe": INFORME, "huella": h_lo, "interprete": interprete,
        "nota_huella": nota_lo, "aristas": dict(sorted(aristas_lo.items())),
    }
    nuevo_pandoc = {
        "motor": "doc_pandoc", "build": build_pandoc, "fecha": FECHA,
        "informe": INFORME, "huella": h_pandoc, "interprete": interprete,
        "nota_huella": nota_pandoc, "aristas": dict(sorted(aristas_pandoc.items())),
    }

    with open(os.path.join(DIR_SONDEO, "doc_libreoffice.json"), "w", encoding="utf-8") as f:
        json.dump(nuevo_lo, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(os.path.join(DIR_SONDEO, "doc_pandoc.json"), "w", encoding="utf-8") as f:
        json.dump(nuevo_pandoc, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("doc_libreoffice.json:", len(aristas_lo), "aristas, huella motor",
          h_lo["motor"])
    print("doc_pandoc.json:", len(aristas_pandoc), "aristas, huella motor",
          h_pandoc["motor"])


if __name__ == "__main__":
    main()

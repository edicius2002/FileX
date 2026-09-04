# -*- coding: utf-8 -*-
"""worker14 — reconstruye los TRES `filex/sondeo/doc_*.json` a partir de
`resondeo40.json`. **RESONDEO real, no resellado por algoritmo.**

La distinción está escrita en la trampa 61 y no es retórica: resellar es
legítimo cuando se demuestra que el CÓDIGO medido no cambió, e indulgencia
cuando sí. Aquí el código cambió a propósito —`_DECLARADAS` pasa de `tuple` a
`dict` y `_aristas()` lee el valor—, así que las 40 entradas se remidieron una
por una contra Docker con `FileX.convertir()` real.

Solo lleva entradas de pares `_DECLARADAS`: las `_MEDIDAS` nacen `REAL` en
`_aristas()` sin pasar por `sondeo.aplicar()`, así que ninguna huella las
gobierna (convenio establecido por worker2 en la ronda 7 y seguido por worker7
en la 12).

    python bench/salidas-rasteriza-declaradas/_sellar.py
"""
from __future__ import annotations

import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import huella  # noqa: E402
from filex.motor_contenedor import (CalibreEnContenedor,  # noqa: E402
                                    LibreOfficeEnContenedor, PandocEnContenedor)

SAL = os.path.dirname(os.path.abspath(__file__))
DIR_SONDEO = os.path.join(RAIZ, "filex", "sondeo")
INFORME = "bench/rasteriza-declaradas.md"
FECHA = "2026-09-03"

#: Las huellas `motor` que había ANTES de este cambio, para poder escribir la
#: transición en la nota en vez de decir «cambió» sin número.
HUELLA_ANTES = {"doc_libreoffice": "48e14e7a35210f60",
                "doc_pandoc": "08817e0e76ef187f",
                "doc_calibre": "5ccb326907e06e1e"}

CLASES = {"doc_libreoffice": LibreOfficeEnContenedor,
          "doc_pandoc": PandocEnContenedor,
          "doc_calibre": CalibreEnContenedor}

NOTA_COMUN = (
    "RESONDEADO (no resellado por algoritmo) el 2026-09-03 por worker14, "
    "carril rasteriza-declaradas: `bench/rasteriza-declaradas.md` convierte "
    "`_DECLARADAS` de `tuple` de pares en `dict` `{{(o,d): rasteriza}}` y hace "
    "que `_EnContenedor._aristas()` lea el valor. Hasta hoy toda arista nacida "
    "de `_DECLARADAS` salia con `rasteriza=False` mintiera o no, y "
    "`sondeo.aplicar()` conserva `rasteriza` de la arista que ya existe, asi "
    "que el valor falso sobrevivia al sondeo. Eso cambia el AST de la clase y "
    "de su base `_EnContenedor`, y CADUCA la huella `motor` ({antes} -> "
    "{ahora}); `invocacion` y `contrato` no se tocaron y no cambiaron "
    "(comprobado antes de editar: los cinco ficheros del disco coincidian con "
    "el arbol). Las {n} aristas que este fichero aplica se REMIDIERON de "
    "verdad con `FileX.convertir()` real -contrato de cinco puntos y censo del "
    "punto 5 incluidos- via "
    "`bench/salidas-rasteriza-declaradas/_resondeo40.py`; {n} de {n} "
    "reprodujeron su veredicto anterior. "
)

NOTA_EXTRA = {
    "doc_libreoffice": (
        "ADEMAS entran al grafo `pptx>png` y `svg>png`, que llevaban desde el "
        "2026-09-02 medidas `real` en este mismo fichero y FUERA del grafo "
        "porque `_DECLARADAS` no sabia declararlas `rasteriza=True` "
        "(comentario de worker7 en `motor_contenedor.py`). Las dos se "
        "remidieron y las dos siguen rasterizando: 0 caracteres recuperados y "
        "sin centinela."),
    "doc_pandoc": (
        "AUDITORIA: el comentario anterior afirmaba que ninguna rasteriza "
        "*porque pandoc no produce imagenes desde estos pares*, que es el "
        "hecho por la causa (trampa 58). Medido de verdad, el criterio es si "
        "el TEXTO sobrevive: las 16 devuelven el centinela, asi que la "
        "conclusion aguanta y ahora es una medida."),
    "doc_calibre": (
        "AUDITORIA: es la primera vez que las 8 se remiden. 7 conservan el "
        "centinela; `mobi>azw3` va con sonda de texto CIEGA (AZW3 comprime el "
        "texto), y su no-rasterizacion se apoya en la ida y vuelta a epub ya "
        "medida en `bench/salidas-sondeo-doc/d2.json` seccion C. AVISO "
        "MEDIDO: `epub>epub` NO es determinista -4 corridas dan 19596/18555/"
        "141175/17712 B y 4 sha256 distintos, con 564 caracteres y centinela "
        "en las 4-; la varianza esta en `cover_image.jpg` (portada que Calibre "
        "GENERA), `content.opf` y `toc.ncx`, y las otras 8 entradas del zip "
        "son identicas al CRC. El `ms` y los bytes de este fichero son de UNA "
        "corrida; el veredicto es lo estable."),
}

#: (o, d) de `_DECLARADAS` que este resondeo cubre, por motor. Se sacan de la
#: clase, no de una copia a mano: una lista tecleada aqui se desincroniza en
#: silencio, que es la trampa 66 (una sonda que mira otra cosa).
def declaradas(motor: str) -> list:
    return sorted(CLASES[motor]._DECLARADAS)


def cargar_casos() -> dict:
    with open(os.path.join(SAL, "resondeo40.json"), encoding="utf-8") as f:
        d = json.load(f)
    return {(x["motor"], x["origen"], x["destino"]): x for x in d["casos"]}


def entrada_aristas(motor: str, casos: dict) -> dict:
    out = {}
    for o, d in declaradas(motor):
        x = casos.get((motor, o, d))
        if x is None:
            raise SystemExit(f"falta el caso resondeado {motor}:{o}>{d}")
        if x.get("rc") != 0 or x.get("contrato") == "fallo":
            raise SystemExit(f"{motor}:{o}>{d} no salio bien: rc={x.get('rc')} "
                             f"contrato={x.get('contrato')}")
        motivo = (f"{x.get('bytes')} B, {x.get('caracteres')} caracteres, "
                  f"contrato {x.get('contrato')}")
        if x.get("rasteriza_medido") == "si":
            motivo += ("; RASTERIZA: sin centinela y 0 caracteres, es el precio "
                       "del destino, no un fallo")
        elif x.get("rasteriza_medido") == "ciego":
            motivo += ("; sonda de texto CIEGA (comprime el texto), no "
                       "rasteriza por la ida y vuelta a epub de "
                       "bench/salidas-sondeo-doc/d2.json seccion C")
        out[f"{o}>{d}"] = {"estado": "real", "ms": x.get("ms"),
                           "motivo": motivo, "caso": x["id"]}
    return out


def main() -> None:
    casos = cargar_casos()
    for motor, cls in CLASES.items():
        ruta = os.path.join(DIR_SONDEO, f"{motor}.json")
        with open(ruta, encoding="utf-8") as f:
            viejo = json.load(f)
        aristas = entrada_aristas(motor, casos)
        huella.olvidar()
        h = huella.de_motor(cls)
        nota = NOTA_COMUN.format(antes=HUELLA_ANTES[motor], ahora=h["motor"],
                                 n=len(aristas)) + NOTA_EXTRA[motor]
        nuevo = {"motor": motor, "build": viejo["build"], "fecha": FECHA,
                 "informe": INFORME, "huella": h,
                 "interprete": huella.interprete_actual(),
                 "nota_huella": nota,
                 "aristas": dict(sorted(aristas.items()))}
        # `newline="\n"` EXPLICITO: el `.gitattributes` de este repositorio fija
        # LF en el repositorio Y EN EL ARBOL DE TRABAJO, y el `open()` de
        # Windows traduce a CRLF por defecto. Sin esto los tres JSON salen
        # ENTEROS como modificados y el diff real se entierra — el mismo
        # sintoma que el `.gitattributes` documenta con numero: 3.002 de 3.006
        # rojos que eran puro CR.
        with open(ruta, "w", encoding="utf-8", newline="\n") as f:
            json.dump(nuevo, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"{motor}.json: {len(aristas)} aristas, huella motor "
              f"{HUELLA_ANTES[motor]} -> {h['motor']}")


if __name__ == "__main__":
    main()

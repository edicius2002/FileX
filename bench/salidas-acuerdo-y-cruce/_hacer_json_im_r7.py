"""Convierte el barrido de `sonda_im.py` en `filex/sondeo/imagemagick.json`.

Regla de decision, la del encargo:

* `real`    -> se ejecuto y la salida paso el contrato **con al menos una
               semilla**. Que falle con OTRA semilla no borra la arista: lo
               documenta el `motivo`.
* `nominal` -> rc != 0 o contrato `fallo` **con todas las semillas**.

El `ms` es la MEDIANA DE 3 de la semilla A (1920x1080). Las siete aristas
`*->ico` no admiten 1920 px, asi que su `ms` viene de una semilla de 256x144 con
el mismo contenido: **no son comparables con las demas** y se marca.

Uso: python bench/salidas-sondeo-im/hacer_json.py <barrido.json> <ico256.json> <destino>
"""

from __future__ import annotations

import collections
import json
import sys

INFORME = "bench/sondeo-imagemagick.md"

#: Salvedades MEDIDAS que un lector del JSON a secas no puede deducir.
MOTIVOS = {
    "png>ico": "real solo hasta 256 px de lado",
    "jpg>ico": "real solo hasta 256 px de lado",
    "webp>ico": "real solo hasta 256 px de lado",
    "avif>ico": "real solo hasta 256 px de lado",
    "gif>ico": "real solo hasta 256 px de lado",
    "bmp>ico": "real solo hasta 256 px de lado",
    "tif>ico": "real solo hasta 256 px de lado",
    "bmp>pdf": ("real en pixeles (RMSE 0,0032) y con la PAGINA MAL: -density "
                "hereda PixelsPerCentimeter del BMP y da 362,8x204,1 pt donde "
                "el resto da 921,6x518,4"),
    "gif>png": ("real y exacto (RMSE 0,000000); con un GIF de 2 colores el PNG "
                "sale a 2 bits de indice y el contrato lo declara fallo por I4"),
}
_AVISO_ICO = ("; 257-512 px devuelve rc=0 y escribe ancho&0xFF en el "
              "ICONDIRENTRY (Pillow lee 320x180 como 64x180); >=513 px, rc=1")


def main() -> int:
    barrido, ico256, destino = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(barrido, encoding="utf-8") as fh:
        d = json.load(fh)
    with open(ico256, encoding="utf-8") as fh:
        ico = json.load(fh)

    por = collections.defaultdict(dict)
    for r in d["filas"]:
        por[(r["origen"], r["destino"])][r["semilla"]] = r

    aristas = {}
    for (o, dd), v in sorted(por.items()):
        clave = f"{o}>{dd}"
        a, b = v.get("A"), v.get("B")
        buenas = [x for x in (a, b) if x and x.get("ok")]
        motivo = MOTIVOS.get(clave, "")
        if dd == "ico" and o != "svg" and clave in MOTIVOS:
            motivo += _AVISO_ICO

        if not buenas:
            peor = a or b
            aristas[clave] = {"estado": "nominal",
                              "motivo": motivo or peor.get("motivo", "")}
            continue

        if dd == "ico" and o in ico:
            ms, semilla = ico[o]["ms"], "D-256px"
            veredicto = ico[o]["veredicto"]
        else:
            fuente = a if (a and a.get("ok") and a.get("ms")) else buenas[0]
            ms, semilla = fuente.get("ms"), fuente["semilla"]
            veredicto = fuente.get("veredicto")

        ent = {"estado": "real", "ms": ms, "semilla": semilla,
               "veredicto": veredicto}
        if len(buenas) == 1 and len(v) > 1:
            fallida = [s for s, x in v.items() if not x.get("ok")]
            if not motivo:
                motivo = f"falla con la semilla {','.join(fallida)}"
        if motivo:
            ent["motivo"] = motivo
        aristas[clave] = ent

    doc = {
        "motor": "imagemagick",
        "build": d["build"],
        "fecha": d["fecha"],
        "informe": INFORME,
        "aristas": aristas,
    }
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    n_r = sum(1 for x in aristas.values() if x["estado"] == "real")
    print(f"{destino}: {len(aristas)} aristas, {n_r} real, {len(aristas)-n_r} nominal")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""G4 / B19 — genera `MANIFIESTO.md` y BORRA los PNG regenerables.

`CLAUDE.md` §6: no se versionan salidas binarias regenerables. Se deja el nombre, el
`sha256`, el tamaño y la orden EXACTA que las reproduce.

Aviso que va en el manifiesto y que conviene no perder: `magick` escribe en el PNG
trozos `tEXt` con `date:create`, `date:modify` y `date:timestamp`, asi que **el
`sha256` del PNG no es reproducible entre tandas aunque los pixeles si lo sean**.
Lo reproducible —y lo que importa aqui— es el `md5` de los IDAT, que tambien se anota.

uso: python manifiesto_pm.py [--borrar]
"""
import hashlib
import json
import os
import sys

BASE = r"D:\Work\research\FileX\bench\salidas-phys-multi"
IMG = os.path.join(BASE, "img")
IMGC = os.path.join(BASE, "img_color")
JSN = os.path.join(BASE, "json")

ORDEN_BASE = (
    "magick -density <ppp> corpus/pdf/<doc>.pdf[0] -colorspace Gray "
    "-alpha remove -background white -flatten <doc>__k<kkkk>__sin.png"
)

if __name__ == "__main__":
    borrar = "--borrar" in sys.argv
    geo = json.load(open(os.path.join(JSN, "geometria_pm.json"), encoding="utf-8"))
    filas = []
    total = 0
    fuentes = [(IMG, "")] + ([(IMGC, "img_color/")] if os.path.isdir(IMGC) else [])
    for carpeta, pref in fuentes:
     for nom in sorted(os.listdir(carpeta)):
        if not nom.endswith(".png"):
            continue
        ruta = os.path.join(carpeta, nom)
        nom = pref + nom
        b = open(ruta, "rb").read()
        clave = os.path.basename(nom)[:-4]
        g = geo.get(clave, {})
        filas.append({
            "fichero": nom, "bytes": len(b),
            "sha256": hashlib.sha256(b).hexdigest(),
            "md5_idat": g.get("md5_idat"), "phys": g.get("phys"),
            "px": g.get("px"), "ppp_render": g.get("ppp_render"),
            "ppp_declarados": g.get("ppp_declarados"),
            "doc": g.get("doc"), "factor": g.get("factor"),
        })
        total += len(b)
    with open(os.path.join(BASE, "MANIFIESTO.md"), "w", encoding="utf-8") as f:
        f.write("# MANIFIESTO — `bench/salidas-phys-multi/`\n\n")
        f.write("Salidas binarias de G4 / B19. **Borradas del repositorio**: son "
                "regenerables con dos órdenes.\n\n")
        f.write(f"- ficheros: **{len(filas)}**\n- bytes: **{total:,}** "
                f"({total / 1e6:.1f} MB)\n\n")
        f.write("## Cómo se reproducen\n\n")
        f.write("**Paso 1 — rasterizar y generar las variantes de cabecera** (una "
                "sola orden; rasteriza UNA vez por documento y factor y genera las "
                "variantes por cirugía de bytes sobre el `pHYs`, sin tocar los "
                "IDAT):\n\n```\n")
        f.write("cd bench/salidas-phys-multi\n")
        f.write("../../.venv-ai/Scripts/python.exe preparar_pm.py \\\n"
                "    escaneado_d3:1.0 escaneado_d4:1.0 escaneado_d4c:1.0 \\\n"
                "    escaneado_d4e:1.0 escaneado_d4f:1.0\n")
        f.write("../../.venv-ai/Scripts/python.exe preparar_pm.py escaneado_d4:1.25\n")
        f.write("```\n\n")
        f.write("La orden de rasterizado que ejecuta por dentro es la del corpus:\n\n"
                f"```\n{ORDEN_BASE}\n```\n\n")
        f.write("**Paso 1-bis — los dos rásteres EN COLOR de la tanda E** "
                "(`img_color/`), que existen para separar el orden de canales del "
                "modo paleta:\n\n```\n"
                "magick img/escaneado_d4__k1000__sin.png -colorspace sRGB \\\n"
                "    -channel R -evaluate multiply 0.55 +channel \\\n"
                "    -channel B -evaluate multiply 0.85 +channel \\\n"
                "    img_color/escaneado_d4__k1000__color.png\n"
                "    # ^ magick lo escribe en PALETA (mode P), a proposito del hallazgo\n"
                "magick img/escaneado_d4__k1000__sin.png -colorspace sRGB \\\n"
                "    -channel R -evaluate multiply 0.55 +channel \\\n"
                "    -channel B -evaluate multiply 0.85 +channel \\\n"
                "    PNG24:img_color/escaneado_d4__k1000__color24.png\n"
                "    # ^ el mismo, forzado a truecolor\n"
                "```\n\n")
        f.write("**Paso 2 — las tandas**:\n\n```\n"
                "bash run_a_tess.sh      # control Tesseract, CPU, sin lock de GPU\n"
                "bash run_b_gpu.sh       # los tres motores GPU, con lock\n"
                "bash run_c_color.sh     # tanda E: la via sobre raster en color\n"
                "# y las tres sondas:\n"
                "#   sonda_pixeles_pm.py, sonda_lectura_pm.py, sonda_canales_pm.py\n"
                "```\n\n")
        f.write("> **El `sha256` de un PNG de `magick` NO es reproducible entre "
                "tandas**: escribe trozos `tEXt` con `date:create`, `date:modify` y "
                "`date:timestamp`. Lo que sí es reproducible es el **`md5` de los "
                "IDAT**, que es lo que garantiza que las variantes de cabecera "
                "comparten píxeles. Se dan los dos.\n\n")
        f.write("## Ficheros\n\n")
        f.write("| fichero | bytes | px | ppp render | ppp declarados | `pHYs` | "
                "`md5` IDAT | `sha256` |\n")
        f.write("|---|---:|---|---:|---|---|---|---|\n")
        for r in filas:
            ph = r["phys"]
            phs = "-" if ph is None else f"u={ph['unidad']} x={ph['x_ppu']}"
            px = f"{r['px'][0]}×{r['px'][1]}" if r["px"] else "1294×1716"
            f.write(f"| `{r['fichero']}` | {r['bytes']:,} | "
                    f"{px} | {r['ppp_render'] or 200} | "
                    f"{r['ppp_declarados']} | {phs} | `{(r['md5_idat'] or '')[:12]}` "
                    f"| `{r['sha256'][:16]}` |\n")
        f.write("\n## Lo que SÍ queda versionado\n\n")
        f.write("Los scripts, los `.json` de celda (`json/`), la salida literal de "
                "OCR de cada celda (`texto/`) y los logs (`logs/`). Son texto y son "
                "la trazabilidad del informe.\n")
    print(f"MANIFIESTO.md: {len(filas)} ficheros, {total / 1e6:.1f} MB")
    if borrar:
        n = 0
        for r in filas:
            os.remove(os.path.join(BASE, r["fichero"].replace("img_color/", "img_color\\")) if r["fichero"].startswith("img_color/") else os.path.join(IMG, r["fichero"]))
            n += 1
        print(f"borrados {n} PNG de {IMG}")
    else:
        print("(no se borra nada; usa --borrar)")

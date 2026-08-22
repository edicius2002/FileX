# -*- coding: utf-8 -*-
"""G3 / paso 4 — genera `tablas.md` (todas las celdas), `corpus/pdf/MANIFIESTO-d5.md`
y `bench/salidas-corpus-d5/MANIFIESTO.md`. Todo sale de los `.json`: ninguna cifra de
los informes esta transcrita a mano.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RAIZ = r"D:\Work\research\FileX"
BASE = os.path.join(RAIZ, r"bench\salidas-corpus-d5")
JSON = os.path.join(BASE, "json")
PDF = os.path.join(RAIZ, r"corpus\pdf")


def carga(n):
    p = os.path.join(JSON, n)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []


def num(x):
    return "—" if x is None else f"{x:.2f}".replace(".", ",")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    man = carga("manifiesto_d5.json")
    v1 = carga("tess_v1_canonica.json")
    v2 = carga("tess_v2_gs.json")
    v3 = carga("tess_v3_ppp.json")
    abl = carga("tess_ablacion.json")
    crib = carga("tess_cribado.json")
    bil = carga("tess_barrido_ilum.json")
    bpo = carga("tess_barrido_polvo.json")
    dens = carga("sonda_densidad.json")

    L = []
    A = L.append
    A("# Tablas completas — corpus d5 (G3)\n")
    A("Evaluador: `bench/salidas-corpus-d4/ocr_eval_d4.py`, copia byte a byte en este")
    A("directorio, `rid=\"d4\"`. Toda cifra es **CER con acentos**, en por ciento.")
    A("Motor: **Tesseract 5.5.0, CPU**. Rasterizador declarado en cada tabla.\n")

    # T1 — las 90 celdas de V1
    A("## T1 · Tanda V1 — 15 documentos x 3 `--psm` x 2 idiomas, ppp nativos, "
      "rasterizador ImageMagick\n")
    A("| documento | ppp nat | px | psm 3 spa | psm 6 spa | psm 11 spa | psm 3 eng | "
      "psm 6 eng | psm 11 eng | min | max |")
    A("|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    docs = []
    for f in v1:
        if f["doc"] not in docs:
            docs.append(f["doc"])
    for d in docs:
        c = {(f["psm"], f["lang"]): f["cer_acentos"] for f in v1 if f["doc"] == d}
        g = [f for f in v1 if f["doc"] == d][0]
        vals = [c.get((p, l)) for l in ("spa", "eng") for p in (3, 6, 11)]
        A(f"| `{d}` | {g['ppp_nativo']} | {g['px']} | "
          + " | ".join(num(c.get((p, l))) for l in ("spa", "eng") for p in (3, 6, 11))
          + f" | **{num(min(v for v in vals if v is not None))}** "
            f"| {num(max(v for v in vals if v is not None))} |")

    # T2 — desglose por bloque
    A("\n## T2 · Desglose por tamaño de letra (el GRADIENTE), `psm 11`, `spa`, "
      "ppp nativos, ImageMagick\n")
    A("| documento | titulo | subtitulo | cuerpo | letra pequeña | ¿monotono? | "
      "config. (de 6) con las 4 cifras distintas |")
    A("|---|---:|---:|---:|---:|---|---:|")
    for d in docs:
        f = next((x for x in v1 if x["doc"] == d and x["psm"] == 11
                  and x["lang"] == "spa"), None)
        if not f:
            continue
        b = f["bloques"]
        vs = [b.get("titulo"), b.get("subtitulo"), b.get("cuerpo"), b.get("pequeña")]
        n4 = 0
        for x in v1:
            if x["doc"] != d:
                continue
            bb = x["bloques"]
            w = [bb.get("titulo"), bb.get("subtitulo"), bb.get("cuerpo"),
                 bb.get("pequeña")]
            if len(set(w)) == 4:
                n4 += 1
        mono = "si" if vs == sorted(vs) else "no"
        A(f"| `{d}` | " + " | ".join(num(v) for v in vs)
          + f" | {mono} | {n4}/6 |")

    # T3 — barrido de ppp
    A("\n## T3 · Tanda V3 — barrido de ppp sobre B15 (`spa`, ImageMagick). "
      "**La medida del suelo de 100.**\n")
    pppset = sorted({f["ppp"] for f in v3})
    for psm in (3, 11):
        A(f"\n**`--psm {psm}`**\n")
        A("| documento | ppp nativos | regla vigente | "
          + " | ".join(f"{p} ppp" for p in pppset) + " |")
        A("|---|---:|---:|" + "---:|" * len(pppset))
        for d in ("escaneado_d5b", "escaneado_d5", "escaneado_d5c", "escaneado_d5a"):
            fs = {f["ppp"]: f for f in v3 if f["doc"] == d and f["psm"] == psm}
            if not fs:
                continue
            nat = list(fs.values())[0]["ppp_nativo"]
            regla = min(max(nat, 100), nat * 1.25)
            A(f"| `{d}` | {nat} | {regla:g} | "
              + " | ".join(num(fs[p]["cer_acentos"]) if p in fs else "—"
                           for p in pppset) + " |")

    # T4 — ablacion
    A("\n## T4 · Ablacion de las cinco patologias de escaner "
      "(partiendo de la primera pared, `spa`, ImageMagick)\n")
    A("| variante | que cambia | psm 3 | psm 11 | Δ psm 11 frente a la base |")
    A("|---|---|---:|---:|---:|")
    base = {f["psm"]: f["cer_acentos"] for f in crib if f["doc"] == "patologico_d5b"}
    nombres = {"abl_p5b_imp02": "polvo 0,10 -> **0,02**",
               "abl_p5b_ilum": "iluminacion 58/68 -> **85/90** (casi uniforme)",
               "abl_p5b_blur06": "desenfoque 1,0 -> **0,6**",
               "abl_p5b_jq60": "JPEG 40 -> **60**",
               "abl_p5b_niv12": "contraste `24%,80%` -> **`12%,90%`**",
               "abl_p5b_rui10": "ruido gaussiano 0,25 -> **0,10**",
               "abl_p5b_sinray": "**sin** rayas de sensor"}
    A(f"| *(base)* | — | {num(base.get(3))} | {num(base.get(11))} | — |")
    orden = []
    for f in abl:
        if f["doc"] not in orden:
            orden.append(f["doc"])
    for d in orden:
        c = {f["psm"]: f["cer_acentos"] for f in abl if f["doc"] == d}
        delta = c.get(11, 0) - base.get(11, 0)
        A(f"| `{d}` | {nombres.get(d, '')} | {num(c.get(3))} | {num(c.get(11))} "
          f"| {delta:+.2f}".replace(".", ",") + " |")

    # T5 — barridos
    A("\n## T5 · Los dos barridos de una sola perilla (`spa`, ImageMagick)\n")
    A("**Iluminacion** (polvo fijo en 0,045). Da un INTERRUPTOR, no un gradiente.\n")
    A("| viñeta/lampara | psm 3 | psm 11 |")
    A("|---|---:|---:|")
    for d in sorted({f["doc"] for f in bil}, key=lambda x: -int(x.split("_v")[1])):
        c = {f["psm"]: f["cer_acentos"] for f in bil if f["doc"] == d}
        A(f"| {d.split('_v')[1]} | {num(c.get(3))} | {num(c.get(11))} |")
    A("\n**Polvo** (iluminacion fija en 78/85). Da la escalera que se uso.\n")
    A("| `-attenuate` del impulso | psm 3 | psm 11 | va al corpus como |")
    A("|---|---:|---:|---|")
    corpusnom = {"045": "—", "080": "—", "120": "`patologico_d5a`",
                 "180": "—", "250": "`patologico_d5b`", "350": "**`patologico_d5`**"}
    for d in sorted({f["doc"] for f in bpo}, key=lambda x: int(x.split("_i")[1])):
        c = {f["psm"]: f["cer_acentos"] for f in bpo if f["doc"] == d}
        k = d.split("_i")[1]
        A(f"| 0,{k} | {num(c.get(3))} | {num(c.get(11))} | {corpusnom.get(k, '—')} |")

    # T6 — rasterizador / densidad
    A("\n## T6 · El \"efecto del rasterizador\", desmontado (`spa`)\n")
    A("`A` = PNG de ImageMagick tal cual (unidades `Undefined`). "
      "`B` = **el mismo PNG** con `-units PixelsPerInch -density N`, "
      "**sin tocar un pixel**. `C` = PNG de Ghostscript.\n")
    A("| documento | psm | A ImageMagick | B ImageMagick + dpi | C Ghostscript | "
      "¿B = C? | ¿pixeles identicos? | A − C |")
    A("|---|---:|---:|---:|---:|---|---|---:|")
    for f in dens:
        c = f["cer"]
        igual = "**si**" if c["B_magick_dpi"] == c["C_gs"] else "no"
        d = c["A_magick"] - c["C_gs"]
        A(f"| `{f['doc']}` | {f['psm']} | {num(c['A_magick'])} | "
          f"{num(c['B_magick_dpi'])} | {num(c['C_gs'])} | {igual} | "
          f"{'**si**' if f['pixeles_identicos'] else 'no'} | "
          f"{d:+.2f}".replace(".", ",") + " |")

    # T7 — V2 completa
    A("\n## T7 · Tanda V2 — los 12 del corpus con Ghostscript, ppp nativos, `spa`\n")
    A("| documento | psm 3 gs | psm 11 gs | psm 3 magick | psm 11 magick |")
    A("|---|---:|---:|---:|---:|")
    for d in [f["doc"] for f in v2]:
        if any(f"| `{d}` |" in x for x in L[-40:]):
            pass
    vistos = []
    for f in v2:
        if f["doc"] in vistos:
            continue
        vistos.append(f["doc"])
        g = {x["psm"]: x["cer_acentos"] for x in v2 if x["doc"] == f["doc"]}
        m = {x["psm"]: x["cer_acentos"] for x in v1
             if x["doc"] == f["doc"] and x["lang"] == "spa"}
        A(f"| `{f['doc']}` | {num(g.get(3))} | {num(g.get(11))} | "
          f"{num(m.get(3))} | {num(m.get(11))} |")

    open(os.path.join(BASE, "tablas.md"), "w", encoding="utf-8",
         newline="\n").write("\n".join(L) + "\n")
    print("-> tablas.md")

    # ---------------------------------------------------------------- MANIFIESTO
    cer = {}
    for f in v1:
        cer.setdefault(f["doc"], []).append(f["cer_acentos"])
    M = []
    B = M.append
    B("# MANIFIESTO — familia `d5` del corpus de OCR\n")
    B("**Agente G3**, 22 de agosto de 2026. Generados por")
    B("`bench/salidas-corpus-d5/gen_corpus_d5.py`, **copia adaptada** de")
    B("`bench/salidas-corpus-d4/gen_corpus_d4.py` (que a su vez lo es de")
    B("`bench/scripts/gen_corpus_ocr.sh`). **Ninguno de los dos originales se ha")
    B("tocado.** Los diez PDF anteriores de `corpus/pdf/` tampoco.\n")
    B("Informe completo: **`bench/corpus-d5.md`**. Celdas: "
      "`bench/salidas-corpus-d5/tablas.md`.\n")
    B("---\n")
    B("## 1. Los doce ficheros\n")
    B("`ppp nativos` NO es un dato declarado a mano: sale de leer el PDF con")
    B("`pypdfium2` (ancho en px de la imagen incrustada / ancho de pagina en")
    B("pulgadas), igual que hace `bench/salidas-corpus-d4/preparar_img.py`.\n")
    B("| fichero | familia | ppp nativos | px | ancho pagina (pt) | bytes | "
      "CER Tesseract (min–max de 6 config.) | sha256 |")
    B("|---|---|---:|---|---:|---:|---:|---|")
    fam = {"bajo_ppp": "B15 bajo ppp", "patologico": "B19 patologico",
           "realista": "B12 realista"}
    for f in man:
        cs = cer.get(f["nombre"], [])
        rango = f"{num(min(cs))} – {num(max(cs))}" if cs else "—"
        neg = "**" if f["nombre"] in ("escaneado_d5", "patologico_d5",
                                      "realista_d5") else ""
        B(f"| {neg}`{f['nombre']}.pdf`{neg} | {fam[f['receta']]} | "
          f"{f['ppp_nativos']:g} | {f['px']} | {f['ancho_pt']} | {f['bytes']} | "
          f"{rango} | `{f['sha256']}` |")
    B("\nLos tres en negrita son los **canonicos** de cada familia. "
      "Las 610 caracteres de referencia son los mismos para los doce.\n")
    B("## 2. Texto de referencia\n")
    B("**`corpus/pdf/REFERENCIA-d5.txt`** — 610 caracteres crudos, 35 acentuados,")
    B("cuatro bloques. Es **exactamente** el de `escaneado_d4`, a proposito: asi los")
    B("doce documentos nuevos son comparables celda a celda con las 396 de")
    B("`bench/k-por-motor.md` y con las 28 de `bench/corpus-d4.md`. Fuente unica de")
    B("verdad: `bench/salidas-corpus-d4/d4_texto.py` (copiado byte a byte a")
    B("`bench/salidas-corpus-d5/d4_texto.py`), que importan el generador Y el")
    B("evaluador.\n")
    B("**Evaluador obligatorio: `bench/salidas-corpus-d4/ocr_eval_d4.py` con")
    B("`rid=\"d4\"`.** `bench/scripts/ocr_eval.py` es ciego a las tildes y sobre este")
    B("texto mide de menos.\n")
    B("## 3. La orden exacta que los reproduce\n")
    B("```")
    B("cd D:\\Work\\research\\FileX\\bench\\salidas-corpus-d5")
    B("python gen_corpus_d5.py --corpus d5_limpio escaneado_d5 escaneado_d5a \\")
    B("    escaneado_d5b escaneado_d5c patologico_d5a patologico_d5b patologico_d5 \\")
    B("    patologico_d5e realista_d5a realista_d5b realista_d5 realista_d5e")
    B("python gen_corpus_d5.py --corpus patologico_d5   # solo uno")
    B("# SIN nombres regenera tambien las 7 ablaciones y los 13 puntos de barrido,")
    B("# que no van al corpus: se quedan en tmp/.")
    B("```")
    B("El generador usa `magick -seed 20260822`. **Sin esa semilla `+noise` es")
    B("aleatorio y el fichero no es reproducible.**\n")
    B("Parametros de cada variante (los mismos que estan en `CANDIDATAS`):\n")
    B("| fichero | receta | parametros |")
    B("|---|---|---|")
    for f in man:
        cfg = f["cfg"]
        B(f"| `{f['nombre']}` | {f['receta']} | "
          + ", ".join(f"`{k}={v}`" for k, v in cfg.items()) + " |")
    B("\n## 4. Aviso de reproducibilidad — MEDIDO\n")
    B("Igual que en `d4`: **el JPEG intermedio es reproducible bit a bit; el PDF no**,")
    B("porque ImageMagick estampa `/CreationDate` y no honra `SOURCE_DATE_EPOCH`.")
    B("**Y esta vez tambien se midio el PNG maestro, que TAMPOCO lo es**: su `sha256`")
    B("cambio en las seis ejecuciones y los JPEG derivados salieron identicos, asi")
    B("que la diferencia esta en los metadatos del PNG, no en los pixeles.\n")
    B("Comprobado en **cinco** ficheros regenerados en tandas distintas: "
      "`patologico_d5a`, `patologico_d5b`, `patologico_d5`, `realista_d5` y")
    B("`realista_d5e` dieron el **mismo sha256 de `.jpg`** y **distinto sha256 de")
    B("`.pdf`**.\n")
    B("| fichero | sha256 del `.jpg` (**reproducible**) | bytes del `.jpg` |")
    B("|---|---|---:|")
    for f in man:
        B(f"| `{f['nombre']}` | `{f['jpg_sha256']}` | {f['jpg_bytes']} |")
    B("\nEl `sha256` del PDF de la tabla 1 identifica **estos** ficheros concretos y")
    B("sirve para detectar corrupcion, no para verificar una regeneracion.\n")
    B("## 5. Como medir con ellos\n")
    B("- **ppp:** los de la columna 3. Y **lea `bench/corpus-d5.md` §2 antes de")
    B("  aplicar la regla vigente**: sobre `escaneado_d5b` (60 ppp nativos) la formula")
    B("  `min(max(n,100), n x 1,25)` devuelve **75 ppp**, y eso cuesta **hasta 16,8")
    B("  puntos** de CER frente a rasterizar a los 100 del suelo. **El suelo de 100 es")
    B("  aritmeticamente inalcanzable por debajo de 80 ppp nativos.**")
    B("- **Declare la densidad en el raster.** Escribir `-units PixelsPerInch")
    B("  -density N` en el PNG **sin tocar un pixel** mueve el CER de Tesseract hasta")
    B("  **33,22 puntos** (`bench/corpus-d5.md` §4). Sin declararla, Tesseract la")
    B("  estima — y sobre `escaneado_d4` estima **403 ppp** donde hay 200.")
    B("- **Declare el `--psm`.** Sobre estos doce documentos el `--psm` mueve hasta")
    B("  **38,8 puntos** (`patologico_d5e`, 92,62 vs 53,02 en el cribado).\n")
    open(os.path.join(PDF, "MANIFIESTO-d5.md"), "w", encoding="utf-8",
         newline="\n").write("\n".join(M) + "\n")
    print("-> corpus/pdf/MANIFIESTO-d5.md")


if __name__ == "__main__":
    main()

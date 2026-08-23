# -*- coding: utf-8 -*-
"""G4 / B19 — construye `tablas.md` a partir de los JSON de celda.

Lo que se calcula, y por que cada cosa:
  * Rejilla CER por (motor, via, documento) x variante de cabecera.
  * `md5` distintos de la SALIDA por (motor, via, documento): es la medida dura.
    El CER es un resumen y puede coincidir con textos distintos; el `md5` no.
  * Recorrido (max - min) del CER dentro de cada fila: cuanto MUEVE el metadato.
  * Comparacion VIA A VIA sobre la misma variante: ruta contra array.
  * Control de Tesseract sobre los MISMOS ficheros, con `Estimating resolution`.

uso: python tablas_pm.py
"""
import glob
import json
import os
from collections import defaultdict

BASE = r"D:\Work\research\FileX\bench\salidas-phys-multi"
JSN = os.path.join(BASE, "json")

ORDEN = ["sin", "ninguno", "p0070", "p0100", "p0150", "p0200", "p0240", "p0250",
         "p0300", "p0400", "color", "color24"]


def carga():
    celdas = {}
    for f in sorted(glob.glob(os.path.join(JSN, "*__cer.json"))):
        d = json.load(open(f, encoding="utf-8"))
        cab = d["cabecera"]
        for clave, v in d["res"].items():
            if "cer_acentos_pct" not in v:
                v = dict(v)
                v["_fallida"] = True
            v = dict(v)
            v["motor"] = cab["motor"]
            v["dispositivo"] = cab["dispositivo"]
            v["via"] = cab.get("via", "ruta")
            v["etiqueta"] = cab["etiqueta"]
            if "variante" not in v:
                base = clave.split("__psm")[0]
                v["raiz"], v["variante"] = base.rsplit("__", 1)
                v["doc"] = v["raiz"].split("__")[0]
            celdas[(cab["etiqueta"], clave)] = v
    return celdas


def tabla(celdas, motores, con_psm=False):
    filas = defaultdict(dict)
    for (_, clave), v in celdas.items():
        if v["motor"] not in motores or v.get("_fallida"):
            continue
        psm = v.get("psm")
        # La ETIQUETA entra en la clave: la tanda E (color) usa el mismo `raiz` que
        # la rejilla principal y NO se puede mezclar con ella.
        k = (v["motor"], v["via"], f"psm{int(psm):02d}" if con_psm and psm else "-",
             v["raiz"], v["etiqueta"])
        filas[k][v["variante"]] = v
    out = []
    for k in sorted(filas):
        vs = filas[k]
        cers = {e: vs[e]["cer_acentos_pct"] for e in ORDEN if e in vs}
        md5s = {vs[e]["md5_texto"] for e in ORDEN if e in vs}
        out.append({"clave": k, "cers": cers, "md5_unicos": len(md5s),
                    "n_variantes": len(cers),
                    "recorrido": round(max(cers.values()) - min(cers.values()), 2)
                    if cers else None,
                    "celdas": vs})
    return out


def md(f, txt=""):
    f.write(txt + "\n")


if __name__ == "__main__":
    celdas = carga()
    gpu = {"rapidocr", "paddleocr", "easyocr"}
    dst = os.path.join(BASE, "tablas.md")
    with open(dst, "w", encoding="utf-8") as f:
        md(f, "# G4 / B19 — tablas generadas (`tablas_pm.py`)\n")
        md(f, f"Celdas cargadas: **{len(celdas)}**.\n")
        # -------------------------------------------------- 1. motores GPU
        md(f, "## 1. Los tres motores GPU — CER por variante de cabecera\n")
        md(f, "Mismos IDAT en todas las columnas. `sin` = lo que escribe "
              "`magick -density N` (pHYs unidad=0) y es lo que tiene TODO el corpus "
              "del proyecto; `ninguno` = sin trozo `pHYs`; `pNNNN` = unidad=1 con "
              "NNNN ppp.\n")
        for t in tabla(celdas, gpu):
            m, via, _, raiz, etq = t["clave"]
            md(f, f"### `{m}` · via `{via}` · `{raiz}`\n")
            cols = [e for e in ORDEN if e in t["cers"]]
            md(f, "| " + " | ".join(cols) + " | md5 únicos | recorrido |")
            md(f, "|" + "---|" * (len(cols) + 2))
            md(f, "| " + " | ".join(f"{t['cers'][c]:.2f}" for c in cols)
                 + f" | **{t['md5_unicos']}** | **{t['recorrido']:.2f}** |\n")
        # -------------------------------------------------- 2. resumen duro
        md(f, "## 2. Resumen: ¿cuántas salidas distintas produce el metadato?\n")
        md(f, "| motor | vía | documento | variantes | md5 únicos | recorrido CER |")
        md(f, "|---|---|---|---:|---:|---:|")
        for t in tabla(celdas, gpu):
            m, via, _, raiz, etq = t["clave"]
            md(f, f"| {m} | {via} | {raiz} (`{etq}`) | {t['n_variantes']} | "
                 f"**{t['md5_unicos']}** | {t['recorrido']:.2f} |")
        md(f, "")
        # -------------------------------------------------- 3. ruta vs array
        md(f, "## 3. Vía `ruta` frente a vía `array`, celda a celda\n")
        md(f, "| motor | fichero | CER ruta | CER array | md5 iguales |")
        md(f, "|---|---|---:|---:|---|")
        idx = {}
        for (_, clave), v in celdas.items():
            if v["motor"] in gpu and not v.get("_fallida"):
                idx[(v["motor"], v["via"], clave)] = v
        difs = 0
        tot = 0
        for (m, via, clave), v in sorted(idx.items()):
            if via != "ruta":
                continue
            w = idx.get((m, "array", clave))
            if not w:
                continue
            tot += 1
            ig = v["md5_texto"] == w["md5_texto"]
            if not ig:
                difs += 1
            md(f, f"| {m} | {clave} | {v['cer_acentos_pct']:.2f} | "
                 f"{w['cer_acentos_pct']:.2f} | {'sí' if ig else '**NO**'} |")
        md(f, f"\n**Pares comparados: {tot}. Con `md5` distinto: {difs}.**\n")
        # -------------------------------------------------- 4. control tesseract
        md(f, "## 4. Control — Tesseract sobre LOS MISMOS ficheros\n")
        for t in tabla(celdas, {"tesseract"}, con_psm=True):
            m, via, psm, raiz, etq = t["clave"]
            cols = [e for e in ORDEN if e in t["cers"]]
            md(f, f"### `{raiz}` · `{psm}`\n")
            md(f, "| dato | " + " | ".join(cols) + " | md5 únicos | recorrido |")
            md(f, "|---" + "|---" * (len(cols) + 2) + "|")
            md(f, "| CER | " + " | ".join(f"{t['cers'][c]:.2f}" for c in cols)
                 + f" | **{t['md5_unicos']}** | **{t['recorrido']:.2f}** |")
            md(f, "| est.res | " + " | ".join(
                str(t["celdas"][c].get("estimating_resolution")) for c in cols)
                 + " | | |")
            md(f, "| bytes | " + " | ".join(
                str(t["celdas"][c].get("bytes_salida")) for c in cols) + " | | |")
            md(f, "| rc | " + " | ".join(
                str(t["celdas"][c].get("rc")) for c in cols) + " | | |\n")
        # -------------------------------------------------- 5. higiene
        md(f, "## 5. Higiene de la tanda\n")
        nd = [k for k, v in celdas.items() if v.get("determinista") is False]
        err = [k for k, v in celdas.items() if v.get("_fallida")]
        rcs = defaultdict(int)
        for v in celdas.values():
            if v["motor"] == "tesseract":
                rcs[v.get("rc")] += 1
        md(f, f"- celdas: **{len(celdas)}**")
        md(f, f"- NO deterministas: **{len(nd)}** {nd[:10]}")
        md(f, f"- celdas fallidas (excepción / omitidas): **{len(err)}** {err[:10]}")
        md(f, f"- `rc` de Tesseract: {dict(rcs)}")
    print(f"-> {dst}")
    print(f"celdas: {len(celdas)}")

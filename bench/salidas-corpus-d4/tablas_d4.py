# -*- coding: utf-8 -*-
"""G1 / genera bench/salidas-corpus-d4/tablas.md a partir de los .json de medidas.
No mide nada: solo ordena lo medido.
"""
import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.abspath(__file__))
JSN = os.path.join(BASE, "json")
SAL = []


def w(s=""):
    SAL.append(s)


def cargar():
    d = {}
    for f in sorted(glob.glob(os.path.join(JSN, "*__cer.json"))):
        try:
            d[os.path.basename(f)[:-len("__cer.json")]] = json.load(
                open(f, encoding="utf-8"))
        except Exception as ex:
            print("no se pudo leer", f, ex)
    return d


D = cargar()
DOCS_D4 = ["d4_limpio", "escaneado_d4a", "escaneado_d4b", "escaneado_d4c",
           "escaneado_d4", "escaneado_d4e", "escaneado_d4f"]


def celda(j, doc, campo="cer_acentos_pct"):
    for k, v in j.get("res", {}).items():
        base = k.split("__", 1)[-1]
        if base == doc:
            return v.get(campo)
    return None


def fmt(x, suf=" %"):
    return "—" if x is None else f"{x:.2f}{suf}"


# ------------------------------------------------------------------ T1
w("# Tablas de `bench/corpus-d4.md`")
w()
w("Generado por `tablas_d4.py` a partir de los `.json` de `json/`. "
  "Todo son medianas de n=9 salvo el cribado, que es n=1.")
w()
w("## T1 · Cribado de candidatas (n=1) — CER con acentos")
w()
mot = [("paddleocr_cuda_criba", "PaddleOCR v6 medium"),
       ("rapidocr_cuda_criba", "RapidOCR v5 mobile"),
       ("easyocr_cuda_criba", "EasyOCR"),
       ("docling_torch_cuda_criba", "Docling+RapidOCR torch (v6 small)")]
docs_criba = ["d4_limpio", "escaneado_d4a", "escaneado_d4b", "escaneado_d4c",
              "escaneado_d4d", "escaneado_d4e", "escaneado_d4f",
              "abl_d4d_blur12", "abl_d4d_jq45", "abl_d4d_niv20",
              "abl_d4d_rui35", "abl_d4d_ang0"]
w("| documento | " + " | ".join(n for _k, n in mot) + " |")
w("|---|" + "---:|" * len(mot))
for doc in docs_criba:
    fila = [fmt(celda(D[k], doc)) if k in D else "—" for k, _n in mot]
    w(f"| `{doc}` | " + " | ".join(fila) + " |")
w()

# ------------------------------------------------------------------ T2
w("## T2 · Validación de la familia d4 (n=9) — CER con acentos / CER ascii")
w()
mot2 = [("paddleocr_cuda_t", "PaddleOCR v6 medium"),
        ("rapidocr_cuda_t", "RapidOCR v5 mobile"),
        ("easyocr_cuda_t", "EasyOCR"),
        ("docling_torch_cuda_t", "Docling+RapidOCR torch")]
w("| documento | " + " | ".join(n for _k, n in mot2) + " |")
w("|---|" + "---:|" * len(mot2))
for doc in DOCS_D4:
    fila = []
    for k, _n in mot2:
        if k not in D:
            fila.append("—")
            continue
        a = celda(D[k], doc)
        b = celda(D[k], doc, "cer_ascii_pct")
        fila.append("—" if a is None else f"{a:.2f} / {b:.2f}")
    w(f"| `{doc}` | " + " | ".join(fila) + " |")
w()

# ------------------------------------------------------------------ T3 ceguera
w("## T3 · Cuánto esconde la métrica sin acentos")
w()
w("`dist_acentos − dist_ascii` = caracteres de error que `ocr_eval.py` **no ve**. "
  "`acentos_salida/acentos_ref` = cuántos caracteres acentuados sobreviven.")
w()
w("| motor | documento | dist. con acentos | dist. ascii | ocultos | acentos recuperados |")
w("|---|---|---:|---:|---:|---:|")
for k, n in mot2:
    if k not in D:
        continue
    for clave, v in D[k].get("res", {}).items():
        doc = clave.split("__", 1)[-1]
        if doc not in DOCS_D4 or "dist_acentos" not in v:
            continue
        oc = v["dist_acentos"] - v["dist_ascii"]
        w(f"| {n} | `{doc}` | {v['dist_acentos']} | {v['dist_ascii']} | "
          f"**{oc}** | {v['acentos_salida']}/{v['acentos_ref']} |")
w()

# ------------------------------------------------------------------ T4 fase 3
w("## T4 · Fase 3 — la asimetría, cruzando tamaño / idioma / tubería")
w()
docs3 = ["escaneado_d3", "escaneado_d4c", "escaneado_d4"]
w("| configuración | d3 (100 ppp) | d4c (200 ppp) | d4 (200 ppp) |")
w("|---|---:|---:|---:|")
orden = [k for k in D if "_f3" in k]


def etiqueta(k):
    return k.replace("__cer", "")


for k in sorted(orden):
    fila = [fmt(celda(D[k], d)) for d in docs3]
    w(f"| `{etiqueta(k)}` | " + " | ".join(fila) + " |")
w()

# ------------------------------------------------------------------ T5 fase 4
w("## T5 · Fase 4 — CPU contra GPU")
w()
docs4 = ["patologico_escaneado", "escaneado_d1", "escaneado_d2", "escaneado_d3",
         "escaneado_d4"]
w("| motor · dispositivo | imagen | CER acentos | ms mediana | etiqueta |")
w("|---|---|---:|---:|---|")
for k in sorted(D):
    if "_f4" not in k:
        continue
    cab = D[k].get("cabecera", {})
    for clave, v in D[k].get("res", {}).items():
        if "cer_acentos_pct" not in v:
            continue
        w(f"| `{k}` | `{clave}` | {v['cer_acentos_pct']:.2f} % | "
          f"{v['ms_mediana']:.1f} | {cab.get('flag', '?')} |")
w()

# ------------------------------------------------------------------ T6 VRAM
w("## T6 · VRAM y carga en frío (pasada con muestreador)")
w()
w("| motor | base MiB | tras carga MiB | pico MiB | coste propio MiB | carga frío s |")
w("|---|---:|---:|---:|---:|---:|")
for k in sorted(D):
    if not k.endswith("_vram"):
        continue
    c, f = D[k].get("cabecera", {}), D[k].get("fin", {})
    w(f"| `{k}` | {c.get('vram_base_MiB')} | {c.get('vram_tras_carga_MiB')} | "
      f"{f.get('vram_pico_MiB')} | {f.get('coste_propio_MiB')} | "
      f"{c.get('carga_frio_s')} |")
w()

open(os.path.join(BASE, "tablas.md"), "w", encoding="utf-8").write("\n".join(SAL))
print("escrito tablas.md:", len(SAL), "lineas")

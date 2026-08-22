# -*- coding: utf-8 -*-
"""P1 / genera todas las tablas del informe a partir de los .json de json/.
Salida: tablas.md. Nada se escribe a mano en el informe que no salga de aqui.

uso: python tablas_pn.py
"""
import glob
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
JSN = os.path.join(BASE, "json")
sys.stdout.reconfigure(encoding="utf-8")

GEO = {}
fg = os.path.join(JSN, "geometria_pn.json")
if os.path.exists(fg):
    GEO = json.load(open(fg, encoding="utf-8"))


def carga(patron):
    out = {}
    for f in sorted(glob.glob(os.path.join(JSN, patron))):
        try:
            out[os.path.basename(f)[:-9]] = json.load(open(f, encoding="utf-8"))
        except Exception as ex:
            out[os.path.basename(f)] = {"error": str(ex)}
    return out


def ppp_de(clave):
    m = re.match(r"ppp0*(\d+)__", clave)
    return int(m.group(1)) if m else None


def doc_de(clave):
    m = re.match(r"ppp\d+__(.+)$", clave)
    return m.group(1) if m else clave


L = []


def w(s=""):
    L.append(s)


todos = carga("*__cer.json")

# ------------------------------------------------------------------ T1 barrido d4
w("# P1 — tablas generadas (`tablas_pn.py`)\n")
w("Toda cifra de CER sale de `ocr_eval_d4.py` (copia exacta de "
  "`bench/salidas-corpus-d4/ocr_eval_d4.py`) via el envoltorio `ocr_eval_pn.py`.\n")
w("## T1 — barrido de ppp sobre `escaneado_d4` (200 ppp nativos)\n")
w("Formato: **CER con acentos / CER ascii** · `cajas` = renglones devueltos (12 en la "
  "pagina) · `peq` = CER del bloque de 7 pt.\n")

etqs = [k for k in todos if "_A_" in k]
filas = {}
for e in etqs:
    for clave, v in todos[e].get("res", {}).items():
        if "error" in v or doc_de(clave) != "escaneado_d4":
            continue
        filas.setdefault(ppp_de(clave), {})[e] = v
if filas:
    cols = sorted(etqs)
    w("| ppp | px ancho | factor | " + " | ".join(c.split("_A_")[-1] for c in cols) + " |")
    w("|---:|---:|---:|" + "---:|" * len(cols))
    for p in sorted(filas):
        g = GEO.get(f"ppp{p:04d}__escaneado_d4", {})
        px = (g.get("png_px") or ["?"])[0]
        fac = g.get("factor_sobre_nativo", "?")
        cel = []
        for c in cols:
            v = filas[p].get(c)
            cel.append("—" if not v else
                       f"{v['cer_acentos_pct']:.2f} / {v['cer_ascii_pct']:.2f} "
                       f"(c={v.get('cajas')}, peq={v['bloques'].get('pequeña')})")
        w(f"| {p} | {px} | {fac} | " + " | ".join(cel) + " |")
    w()
    w("### T1b — tiempos (mediana n=9, ms) y testigos de ruido\n")
    w("| ppp | " + " | ".join(c.split("_A_")[-1] for c in cols) + " |")
    w("|---:|" + "---:|" * len(cols))
    for p in sorted(filas):
        cel = [("—" if not filas[p].get(c) else f"{filas[p][c]['ms_mediana']:.0f}")
               for c in cols]
        w(f"| {p} | " + " | ".join(cel) + " |")
    w()
    w("| tanda | monohilo ini→fin (ms) | deriva | proceso ini→fin (ms) | nivel vs reposo |")
    w("|---|---|---:|---|---:|")
    for c in cols:
        f = todos[c].get("fin", {})
        w(f"| {c} | {f.get('testigo_monohilo_ini_ms')}→{f.get('testigo_monohilo_fin_ms')} "
          f"| {f.get('deriva_monohilo')} | {f.get('testigo_proceso_ini_ms')}→"
          f"{f.get('testigo_proceso_fin_ms')} | **{f.get('nivel_proceso_vs_reposo')}** |")
    w()

# ------------------------------------------------------------------ T2 otros docs
w("## T2 — barrido sobre los otros documentos (tanda B)\n")
etqs = [k for k in todos if "_B_" in k]
por_doc = {}
for e in etqs:
    for clave, v in todos[e].get("res", {}).items():
        if "error" in v:
            continue
        por_doc.setdefault(doc_de(clave), {}).setdefault(ppp_de(clave), {})[e] = v
for doc in sorted(por_doc):
    g0 = next(iter(GEO.get(f"ppp{p:04d}__{doc}", {}) for p in por_doc[doc]), {})
    nat = g0.get("ppp_calculado")
    w(f"### `{doc}` — {nat} ppp nativos\n")
    cols = sorted(etqs)
    w("| ppp | factor sobre nativo | px ancho | " +
      " | ".join(c.split("_B_")[-1] for c in cols) + " |")
    w("|---:|---:|---:|" + "---:|" * len(cols))
    for p in sorted(por_doc[doc]):
        g = GEO.get(f"ppp{p:04d}__{doc}", {})
        cel = []
        for c in cols:
            v = por_doc[doc][p].get(c)
            cel.append("—" if not v else
                       f"{v['cer_acentos_pct']:.2f} (c={v.get('cajas')})")
        w(f"| {p} | {g.get('factor_sobre_nativo')} | {(g.get('png_px') or ['?'])[0]} | "
          + " | ".join(cel) + " |")
    w()

# ------------------------------------------------------------------ T3 pagina
w("## T3 — mismos pixeles, distinto tamaño de pagina (tanda C)\n")
w("Los tres PDF llevan **el mismo JPEG** extraido de `escaneado_d4.pdf`; solo cambia "
  "la densidad declarada, y con ella el tamaño de la pagina y los «ppp nativos». "
  "Si el techo se escribiera en ppp, las tres filas romperian al mismo ppp; si se "
  "escribe en pixeles, romperian a la misma anchura.\n")
etqs = [k for k in todos if "_C_" in k]
filas = {}
for e in etqs:
    for clave, v in todos[e].get("res", {}).items():
        if "error" in v:
            continue
        g = GEO.get(clave, {})
        filas.setdefault((doc_de(clave), ppp_de(clave)), {})[e] = (v, g)
if filas:
    cols = sorted(etqs)
    w("| documento | ppp nativos | ppp usado | factor | px ancho | " +
      " | ".join(c.split("_C_")[-1] for c in cols) + " |")
    w("|---|---:|---:|---:|---:|" + "---:|" * len(cols))
    for (doc, p) in sorted(filas, key=lambda k: (GEO.get(f"ppp{k[1]:04d}__{k[0]}", {})
                                                 .get("png_px", [0])[0], k[0])):
        g = GEO.get(f"ppp{p:04d}__{doc}", {})
        cel = []
        for c in cols:
            t = filas[(doc, p)].get(c)
            cel.append("—" if not t else
                       f"{t[0]['cer_acentos_pct']:.2f} (c={t[0].get('cajas')})")
        w(f"| `{doc}` | {g.get('ppp_calculado')} | {p} | {g.get('factor_sobre_nativo')} "
          f"| **{(g.get('png_px') or ['?'])[0]}** | " + " | ".join(cel) + " |")
    w()

# ------------------------------------------------------------------ T4 B10
w("## T4 — B10: la correccion de normalizacion sobre 15 documentos (tanda D2, n=9)\n")
etqs = [k for k in todos if "_D_" in k]
docs = set()
for e in etqs:
    docs |= set(todos[e].get("res", {}))
if docs:
    cols = sorted(etqs)
    w("| documento | " + " | ".join(c.split("_D_")[-1] for c in cols) + " |")
    w("|---|" + "---:|" * len(cols))
    for d in sorted(docs):
        cel = []
        for c in cols:
            v = todos[c].get("res", {}).get(d)
            if not v:
                cel.append("—")
            elif "error" in v:
                cel.append("ERROR")
            else:
                cel.append(f"{v['cer_acentos_pct']:.2f} / {v['cer_ascii_pct']:.2f} "
                           f"(c={v.get('cajas')})")
        w(f"| `{d}` | " + " | ".join(cel) + " |")
    w()
    # delta R6 por pareja
    for par in (("_D_ro6sm_def", "_D_ro6sm_R6"), ("_D_ro5mob_def", "_D_ro5mob_R6")):
        a = next((c for c in cols if c.endswith(par[0])), None)
        b = next((c for c in cols if c.endswith(par[1])), None)
        if not a or not b:
            continue
        w(f"### Delta de la correccion — `{par[0]}` → `{par[1]}`\n")
        w("| documento | defecto | con R6 | **delta (puntos)** | veredicto |")
        w("|---|---:|---:|---:|---|")
        for d in sorted(docs):
            va = todos[a]["res"].get(d)
            vb = todos[b]["res"].get(d)
            if not va or not vb or "error" in va or "error" in vb:
                continue
            dl = vb["cer_acentos_pct"] - va["cer_acentos_pct"]
            ver = ("**PEOR**" if dl > 0.005 else "mejor" if dl < -0.005 else "igual")
            w(f"| `{d}` | {va['cer_acentos_pct']:.2f} | {vb['cer_acentos_pct']:.2f} "
              f"| {dl:+.2f} | {ver} |")
        w()

# ------------------------------------------------------------------ T5 cribado
fs = os.path.join(JSN, "survey_cuda.json")
if os.path.exists(fs):
    s = json.load(open(fs, encoding="utf-8"))
    w("## T5 — B10: cribado de 7 detectores x 4 variantes (tanda D1, n=1, CER acentos)\n")
    docs = []
    for v in s.values():
        if "docs" in v:
            docs = sorted(v["docs"])
            break
    w("| detector · variante | " + " | ".join(d.replace("ppp0", "").replace("__", " ")
                                              for d in docs) + " |")
    w("|---|" + "---:|" * len(docs))
    for k in s:
        v = s[k]
        if "docs" not in v:
            w(f"| `{k}` | " + " | ".join(["ERROR"] * len(docs)) + " |")
            continue
        cel = []
        for d in docs:
            c = v["docs"].get(d, {})
            cel.append("ERR" if "error" in c else f"{c['cer_acentos_pct']:.2f}")
        w(f"| `{k}` | " + " | ".join(cel) + " |")
    w()

# ------------------------------------------------------------------ T6 docling
w("## T6 — docling (tandas E1 y D3)\n")
for e in sorted(k for k in todos if k.startswith("docling")):
    r = todos[e].get("res", {})
    if not r:
        continue
    w(f"### `{e}`\n")
    w("| clave | ppp param | px al motor | CER acentos | CER ascii | ms mediana |")
    w("|---|---:|---|---:|---:|---:|")
    for k in sorted(r):
        v = r[k]
        if "error" in v:
            w(f"| `{k}` | — | — | ERROR: {v['error'][:80]} | | |")
            continue
        w(f"| `{k}` | {v.get('ppp_efectivo_param')} | {v.get('px_reales_al_motor')} "
          f"| {v['cer_acentos_pct']:.2f} | {v['cer_ascii_pct']:.2f} "
          f"| {v['ms_mediana']:.0f} |")
    w()

# ------------------------------------------------------------------ T7 VRAM
w("## T7 — VRAM y errores (tanda E, pasada con muestreador)\n")
w("| tanda | motor | pico MiB | base MiB | coste propio MiB | errores |")
w("|---|---|---:|---:|---:|---|")
for e in sorted(k for k in todos if "_E_vram" in k):
    f = todos[e].get("fin", {})
    errs = [k for k, v in todos[e].get("res", {}).items() if "error" in v]
    w(f"| {e} | {todos[e]['cabecera'].get('motor', 'docling')} | {f.get('vram_pico_MiB')} "
      f"| {f.get('vram_base_MiB')} | {f.get('coste_propio_MiB')} "
      f"| {', '.join(errs) if errs else '—'} |")
w()

open(os.path.join(BASE, "tablas.md"), "w", encoding="utf-8").write("\n".join(L))
print("\n".join(L))

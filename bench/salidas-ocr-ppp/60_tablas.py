# -*- coding: utf-8 -*-
"""G1 / paso 6 — genera en markdown todas las tablas del informe a partir de los JSON.

No recalcula nada: solo lee `json/*.json` y los formatea. Si una celda no existe,
lo dice; no inventa.

uso: python 60_tablas.py > tablas.md
"""
import json
import os

J = r"D:\Work\research\FileX\bench\salidas-ocr-ppp\json"
DOCS = ["patologico_escaneado", "escaneado_d1", "escaneado_d2", "escaneado_d3"]
CORTO = {"patologico_escaneado": "patológico (d0)", "escaneado_d1": "d1",
         "escaneado_d2": "d2", "escaneado_d3": "d3"}
NAT = {"patologico_escaneado": 200, "escaneado_d1": 150,
       "escaneado_d2": 100, "escaneado_d3": 100}
PPP = [75, 100, 125, 150, 175, 200, 250, 300]

# marcas publicadas en bench/gpu-fase2.md §5 (columna CUDA), para el diff de artefacto
VIEJAS = {
    "RapidOCR":  {"patologico_escaneado": 0.0, "escaneado_d1": 0.0,
                  "escaneado_d2": 1.3, "escaneado_d3": 65.8},
    "PaddleOCR": {"patologico_escaneado": 0.0, "escaneado_d1": 0.0,
                  "escaneado_d2": 0.0, "escaneado_d3": 75.9},
    "EasyOCR":   {"patologico_escaneado": 0.0, "escaneado_d1": 0.0,
                  "escaneado_d2": 43.0, "escaneado_d3": 59.5},
}


def carga(nombre):
    p = os.path.join(J, nombre)
    if not os.path.exists(p):
        return None
    return json.load(open(p, encoding="utf-8"))


MOTORES = [
    ("RapidOCR", "rapidocr_cuda__cer.json", "ppp{p}__{d}", "ext{g}__{d}"),
    ("PaddleOCR", "paddleocr_cuda__cer.json", "ppp{p}__{d}", "ext{g}__{d}"),
    ("EasyOCR", "easyocr_cuda__cer.json", "ppp{p}__{d}", "ext{g}__{d}"),
    ("Docling+RapidOCR torch", "docling_torch_cuda__cer.json", "ppp{p}__{d}", None),
]
DAT = {n: carga(f) for n, f, _, _ in MOTORES}
DIMG = carga("doclingimg_torch_cuda__cer.json")
DDEF = carga("docling_torch_cuda_defecto__cer.json")
LIMPIO = {n: carga(f.replace("__cer", "_t__cer")) for n, f, _, _ in MOTORES}


def cel(dat, clave, campo="cer_pct", suf="%"):
    if not dat:
        return "—"
    v = dat["res"].get(clave)
    if v is None:
        return "—"
    if "error" in v:
        return "ERROR"
    x = v.get(campo)
    return "—" if x is None else (f"{x:.1f}{suf}" if isinstance(x, float) else f"{x}{suf}")


def via_nativa(nom, d):
    return cel(DAT[nom], f"ppp{NAT[d]}__{d}")


def via_ext(nom, d):
    if nom == "Docling+RapidOCR torch":
        return cel(DIMG, f"extg__{d}")
    return cel(DAT[nom], f"extg__{d}")


def via_200(nom, d):
    return cel(DAT[nom], f"ppp200__{d}")


print("<!-- generado por 60_tablas.py; no editar a mano -->\n")

# ------------------------------------------------------------------ T1 canonica
print("### T1 — Tabla canónica: CER % por vía de entrada\n")
print("| Motor | Documento | ppp nativos | imagen extraída | 200 ppp (control) |")
print("|---|---|---:|---:|---:|")
for nom, *_ in MOTORES:
    for d in DOCS:
        print(f"| {nom} | {CORTO[d]} ({NAT[d]} ppp) | **{via_nativa(nom, d)}** | "
              f"{via_ext(nom, d)} | {via_200(nom, d)} |")

print("\n### T1b — distancia de edición (mismos datos, en caracteres sobre 79)\n")
print("| Motor | Documento | ppp nativos | imagen extraída | 200 ppp |")
print("|---|---|---:|---:|---:|")
for nom, *_ in MOTORES:
    for d in DOCS:
        a = cel(DAT[nom], f"ppp{NAT[d]}__{d}", "dist_global", "")
        b = ("—" if nom.startswith("Docling") and not DIMG
             else (cel(DIMG, f"extg__{d}", "dist_global", "")
                   if nom.startswith("Docling")
                   else cel(DAT[nom], f"extg__{d}", "dist_global", "")))
        c = cel(DAT[nom], f"ppp200__{d}", "dist_global", "")
        print(f"| {nom} | {CORTO[d]} | {a} | {b} | {c} |")

# ------------------------------------------------------------------ T2 artefacto
print("\n### T2 — Cuánto de la cifra vieja era artefacto\n")
print("| Motor | Doc | publicado (200 ppp) | reproducido aquí | a ppp nativos | "
      "artefacto (pp) |")
print("|---|---|---:|---:|---:|---:|")
for nom in ("RapidOCR", "PaddleOCR", "EasyOCR"):
    for d in DOCS:
        vieja = VIEJAS[nom][d]
        rep = DAT[nom]["res"].get(f"ppp200__{d}", {}).get("cer_pct") if DAT[nom] else None
        nat = DAT[nom]["res"].get(f"ppp{NAT[d]}__{d}", {}).get("cer_pct") if DAT[nom] else None
        art = "—" if rep is None or nat is None else f"{rep - nat:+.1f}"
        ok = "✔" if rep is not None and abs(rep - vieja) < 0.05 else "≠"
        print(f"| {nom} | {CORTO[d]} | {vieja:.1f}% | {rep}% {ok} | {nat}% | {art} |")

# ------------------------------------------------------------------ T3 curva
print("\n### T3 — Curva de ppp: CER % (celda de ppp nativos en **negrita**)\n")
for d in DOCS:
    print(f"\n**{CORTO[d]}** — nativo {NAT[d]} ppp\n")
    print("| ppp | " + " | ".join(n for n, *_ in MOTORES) + " |")
    print("|---:|" + "---:|" * len(MOTORES))
    for p in PPP:
        fila = [f"**{p}**" if p == NAT[d] else str(p)]
        for nom, *_ in MOTORES:
            v = cel(DAT[nom], f"ppp{p}__{d}")
            fila.append(f"**{v}**" if p == NAT[d] else v)
        print("| " + " | ".join(fila) + " |")
    fila = ["extraída"]
    for nom, *_ in MOTORES:
        fila.append(via_ext(nom, d))
    print("| " + " | ".join(fila) + " |")
    if DDEF:
        v = cel(DDEF, f"pppdefecto__{d}")
        print(f"| docling por defecto (216 ppp) | — | — | — | {v} |")

# ------------------------------------------------------------------ T4 coste
print("\n### T4 — Coste: mediana de tiempo (ms, n=9) por vía\n")
print("| Motor | Doc | ppp nativos | imagen extraída | 200 ppp | 300 ppp |")
print("|---|---|---:|---:|---:|---:|")
for nom, *_ in MOTORES:
    for d in DOCS:
        a = cel(DAT[nom], f"ppp{NAT[d]}__{d}", "ms_mediana", "")
        b = (cel(DIMG, f"extg__{d}", "ms_mediana", "") if nom.startswith("Docling")
             else cel(DAT[nom], f"extg__{d}", "ms_mediana", ""))
        c = cel(DAT[nom], f"ppp200__{d}", "ms_mediana", "")
        e = cel(DAT[nom], f"ppp300__{d}", "ms_mediana", "")
        print(f"| {nom} | {CORTO[d]} | {a} | {b} | {c} | {e} |")

print("\n### T4b — VRAM: pico total de la tarjeta y coste propio, sobre TODO el barrido\n")
print("| Motor | carga en frío | VRAM base | pico | coste propio | pico util. |")
print("|---|---:|---:|---:|---:|---:|")
for nom, f, _, _ in MOTORES:
    dat = DAT[nom]
    if not dat:
        print(f"| {nom} | — | — | — | — | — |")
        continue
    c, fi = dat["cabecera"], dat["fin"]
    print(f"| {nom} | {c.get('carga_frio_s', '—')} s | {fi['vram_base_MiB']} MiB | "
          f"**{fi['vram_pico_MiB']} MiB** | +{fi['coste_propio_MiB']} MiB | "
          f"{fi.get('pico_util_pct', '—')} % |")

# ------------------------------------------------------------------ tiempos limpios
if any(LIMPIO.values()):
    print("\n### T4c — Tiempos sin el muestreador de VRAM (los buenos), ms mediana n=9\n")
    print("| Motor | Doc | ppp nativos | imagen extraída | 200 ppp | ahorro nativo vs 200 |")
    print("|---|---|---:|---:|---:|---:|")
    for nom, *_ in MOTORES:
        dat = LIMPIO.get(nom)
        if not dat:
            continue
        for d in DOCS:
            a = dat["res"].get(f"ppp{NAT[d]}__{d}", {}).get("ms_mediana")
            b = dat["res"].get(f"extg__{d}", {}).get("ms_mediana")
            c = dat["res"].get(f"ppp200__{d}", {}).get("ms_mediana")
            r = f"{c/a:.2f}x" if a and c else "—"
            print(f"| {nom} | {CORTO[d]} | {a} | {b} | {c} | {r} |")

# ------------------------------------------------------------------ sonda docling
if DAT["Docling+RapidOCR torch"]:
    print("\n### T5 — Sonda: píxeles que llegan de verdad al motor dentro de docling\n")
    print("| configuración | escala | ppp nominal | px al motor |")
    print("|---|---:|---:|---|")
    r = DAT["Docling+RapidOCR torch"]["res"]
    for p in PPP:
        v = r.get(f"ppp{p}__escaneado_d3")
        if v and "px_reales_al_motor" in v:
            print(f"| d3 @ {p} ppp | {v['escala']} | {v['ppp_efectivo_param']} | "
                  f"{v['px_reales_al_motor']} |")
    if DDEF:
        v = DDEF["res"].get("pppdefecto__escaneado_d3")
        if v:
            print(f"| d3 @ **por defecto** | {v['escala']} | {v['ppp_efectivo_param']} | "
                  f"{v['px_reales_al_motor']} |")
    if DIMG:
        v = DIMG["res"].get("extg__escaneado_d3")
        if v:
            print(f"| d3 imagen extraída | 1.0 | — | {v['px_reales_al_motor']} "
                  f"(png {v['px_png']}) |")

# ------------------------------------------------------------------ texto d3
print("\n### T6 — Qué texto sale de verdad en d3\n")
print("Referencia: `documento escaneado texto que solo existe como pixeles "
      "debe recuperarse con ocr` (79 caracteres normalizados)\n")
print("| Motor | vía | CER | texto recuperado (normalizado) |")
print("|---|---|---:|---|")
for nom, *_ in MOTORES:
    dat = DAT[nom]
    if not dat:
        continue
    for etiq, clave in [(f"{NAT['escaneado_d3']} ppp (nativo)",
                         f"ppp{NAT['escaneado_d3']}__escaneado_d3"),
                        ("200 ppp", "ppp200__escaneado_d3")]:
        v = dat["res"].get(clave, {})
        t = v.get("normalizada", "")
        print(f"| {nom} | {etiq} | {v.get('cer_pct', '—')}% | `{t[:110]}` |")
    if nom.startswith("Docling"):
        continue
    v = dat["res"].get("extg__escaneado_d3", {})
    print(f"| {nom} | extraída | {v.get('cer_pct', '—')}% | "
          f"`{v.get('normalizada', '')[:110]}` |")
if DIMG:
    v = DIMG["res"].get("extg__escaneado_d3", {})
    print(f"| Docling+RapidOCR torch | extraída | {v.get('cer_pct', '—')}% | "
          f"`{v.get('normalizada', '')[:110]}` |")

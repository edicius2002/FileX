# -*- coding: utf-8 -*-
"""M1 / B13 — tablas y analisis. Lee los .json de `json/` y escribe `tablas.md`.

La pregunta que tiene que contestar: **el `k` optimo, ¿es una propiedad DEL MOTOR o
del PAR (motor, documento)?** El analisis que la contesta no es la tabla de optimos
—que se puede leer torcida— sino el **arrepentimiento** (`regret`): cuantos puntos de
CER cuesta fijar UN solo `k` por motor frente a acertar el mejor `k` de cada documento.

  regret(motor, k)  = media_documentos[ CER(motor, doc, k) - min_f CER(motor, doc, f) ]

Si el mejor `k` fijo por motor tiene un arrepentimiento pequeño, la regla vigente se
sostiene. Si el arrepentimiento del mejor `k` fijo es grande, la regla esta refutada:
el `k` seria del par.
"""
import glob
import io
import json
import os
import statistics

BASE = os.path.dirname(os.path.abspath(__file__))
JSN = os.path.join(BASE, "json")

FACTORES = [0.5, 0.625, 0.75, 0.875, 1.0, 1.125, 1.25, 1.4, 1.5, 1.6, 1.8]
DOCS = ["escaneado_d3", "escaneado_d4c", "patologico_escaneado", "escaneado_d4"]
DOC_CORTO = {"escaneado_d3": "d3", "escaneado_d4c": "d4c",
             "patologico_escaneado": "patológico", "escaneado_d4": "d4"}

# prefijo de la etiqueta del fichero -> nombre legible de la configuracion.
# Es un PREFIJO y no un nombre exacto porque PaddleOCR necesito varios procesos
# (tanda D): su asignador no devuelve la VRAM y un folio grande envenena el lote.
CONFIGS = [
    ("paddleocr_cuda_", "PaddleOCR v6 medium"),
    ("rapidocr_cuda_A_ro6sm_R6", "RapidOCR v6 small + R6"),
    ("rapidocr_cuda_A_ro6sm_def", "RapidOCR v6 small (defecto)"),
    ("rapidocr_cuda_A_ro5mob_def", "RapidOCR v5 mobile (defecto)"),
    ("easyocr_cuda_", "EasyOCR (CRAFT + latin_g2)"),
    ("docling_torch_cuda_C_dl_def", "Docling+RapidOCR torch (defecto)"),
    ("docling_torch_cuda_C_dl_R6", "Docling+RapidOCR torch + R6"),
    ("tesseract_cpu_D_tess", "Tesseract 5.5.0 · --psm 3 (defecto)"),
    ("tesseract_cpu_I_tess11", "Tesseract 5.5.0 · --psm 11"),
]

# K_D4: el ARGMIN que P1 midio sobre UN solo documento, `escaneado_d4`
# (ppp-y-normalizacion.md §2.7). Tesseract viene de P2 sobre `escaneado_d2`, n=1.
K_VIGENTE = {
    "PaddleOCR v6 medium": 1.25,
    "RapidOCR v6 small + R6": 1.00,
    "RapidOCR v6 small (defecto)": 1.25,
    "RapidOCR v5 mobile (defecto)": 0.50,
    "EasyOCR (CRAFT + latin_g2)": 1.80,
    "Docling+RapidOCR torch (defecto)": 1.60,
    "Docling+RapidOCR torch + R6": 0.875,
    "Tesseract 5.5.0 · --psm 3 (defecto)": 1.50,
    "Tesseract 5.5.0 · --psm 11": 1.50,
}

# K_REGLA: lo que la regla de ppp-y-normalizacion.md §2.8 / CLAUDE.md trampa 8
# realmente CABLEA, que no siempre es el argmin de d4 (a EasyOCR y a Docling+R6 les
# pone 1,00 «porque el 0,88 y el 1,80 medidos estan dentro del ruido»).
K_REGLA = {
    "PaddleOCR v6 medium": 1.25,
    "RapidOCR v6 small + R6": 1.00,
    "RapidOCR v6 small (defecto)": None,
    "RapidOCR v5 mobile (defecto)": None,
    "EasyOCR (CRAFT + latin_g2)": 1.00,
    "Docling+RapidOCR torch (defecto)": None,
    "Docling+RapidOCR torch + R6": 1.00,
    "Tesseract 5.5.0 · --psm 3 (defecto)": 1.50,
    "Tesseract 5.5.0 · --psm 11": 1.50,
}


def clave(f, doc):
    return f"k{int(round(f * 1000)):04d}__{doc}"


def _res_fusionada(et):
    """Fusiona todos los .json cuya etiqueta empieza por `et`. Una celda valida
    (con CER) nunca es sustituida por una omitida o con error."""
    ficheros = sorted(glob.glob(os.path.join(JSN, f"{et}*__cer.json")))
    if not ficheros:
        return None, None, None
    res, fin, cab = {}, {}, {}
    for fj in ficheros:
        d = json.load(io.open(fj, encoding="utf-8"))
        cab = cab or d.get("cabecera", {})
        fin = d.get("fin", fin)
        for k, v in d["res"].items():
            if k in res and "cer_acentos_pct" in res[k]:
                continue
            res[k] = v
    return res, fin, cab


def cargar():
    datos = {}
    meta = {}
    for et, nombre in CONFIGS:
        res_f, fin_f, cab_f = _res_fusionada(et)
        if res_f is None:
            continue
        d = {"res": res_f, "fin": fin_f, "cabecera": cab_f}
        meta[nombre] = {"fin": d.get("fin", {}), "cab": d.get("cabecera", {})}
        tabla = {}
        for doc in DOCS:
            fila = {}
            for f in FACTORES:
                r = d["res"].get(clave(f, doc))
                if r is None:
                    fila[f] = None
                elif "cer_acentos_pct" in r:
                    fila[f] = (r["cer_acentos_pct"], r["cer_ascii_pct"],
                               r.get("cajas"), r.get("determinista"))
                else:
                    fila[f] = ("ERR", r.get("error") or r.get("omitido_vram"), None, None)
            tabla[doc] = fila
        datos[nombre] = tabla
    return datos, meta


def cer(v):
    if v is None or v[0] == "ERR":
        return None
    return v[0]


def optimo(fila):
    """Devuelve (mejor_cer, [factores empatados en el mejor])."""
    vals = [(f, cer(v)) for f, v in fila.items() if cer(v) is not None]
    if not vals:
        return None, []
    m = min(c for _f, c in vals)
    return m, [f for f, c in vals if c == m]


def main():
    datos, meta = cargar()
    geo = json.load(io.open(os.path.join(JSN, "geometria_km.json"), encoding="utf-8"))
    out = []
    W = out.append

    W("# M1 / B13 — tablas completas\n")
    W("Generado por `tablas_km.py`. **CER acentos / CER ascii · cajas.** "
      "Dispositivo fijado: GPU (`cuda`, `gpu:0`) salvo Tesseract, que es CPU.\n")

    # --- geometria ---
    W("\n## 0. Las 40 rasterizaciones\n")
    W("| documento | ppp nativos | factor | ppp usados | píxeles | Mpx |")
    W("|---|---:|---:|---:|---:|---:|")
    for doc in DOCS:
        for f in FACTORES:
            g = geo.get(clave(f, doc))
            if not g:
                continue
            W(f"| `{doc}` | {g.get('ppp_calculado')} | ×{f:.3f} | {g.get('ppp_usado')} "
              f"| {g['png_px'][0]}×{g['png_px'][1]} | {g.get('megapixeles')} |")

    # --- tablas por configuracion ---
    W("\n## 1. El barrido, configuración por configuración\n")
    for _et, nombre in CONFIGS:
        if nombre not in datos:
            continue
        W(f"\n### {nombre}\n")
        W("| factor | " + " | ".join(DOC_CORTO[d] for d in DOCS) + " |")
        W("|---:|" + "---:|" * len(DOCS))
        for f in FACTORES:
            cel = []
            for doc in DOCS:
                v = datos[nombre][doc][f]
                if v is None:
                    cel.append("—")
                elif v[0] == "ERR":
                    cel.append(f"**{v[1]}**")
                else:
                    cel.append(f"{v[0]:.2f} / {v[1]:.2f} · c{v[2]}")
            W(f"| ×{f:.3f} | " + " | ".join(cel) + " |")
        fin = meta[nombre]["fin"]
        W(f"\n*testigos: deriva {fin.get('deriva_monohilo')} · "
          f"nivel {fin.get('nivel_proceso_vs_reposo')} × reposo · "
          f"topado={fin.get('testigo_topado')}*\n")

    # --- optimos ---
    W("\n## 2. Dónde cae el óptimo de cada configuración en cada documento\n")
    W("Marcas: **‡** = el óptimo NO es informativo porque el motor no lee el "
      "documento (mejor CER ≥ 50 %: elegir el mínimo entre 74,68 y 75,95 es elegir "
      "ruido). **†** = curva plana o en el suelo (≥5 factores empatados en el "
      "mínimo): el documento no discrimina el `k`.\n")
    W("| configuración | " + " | ".join(DOC_CORTO[d] for d in DOCS) +
      " | **¿coincide?** |")
    W("|---|" + "---|" * (len(DOCS) + 1))
    for _et, nombre in CONFIGS:
        if nombre not in datos:
            continue
        cel, ks = [], []
        for doc in DOCS:
            m, fs = optimo(datos[nombre][doc])
            if m is None:
                cel.append("—")
                continue
            ks.append(set(fs))
            marca = ("‡" if m >= 50 else "") + ("†" if len(fs) >= 5 else "")
            cel.append("×" + "/×".join(f"{x:g}" for x in fs) + f" ({m:.2f}){marca}")
        comun = set.intersection(*ks) if ks else set()
        W(f"| {nombre} | " + " | ".join(cel) + " | " +
          ("**sí**: ×" + "/×".join(f"{x:g}" for x in sorted(comun)) if comun
           else "**NO**") + " |")

    # --- arrepentimiento ---
    W("\n## 3. Arrepentimiento: lo que cuesta fijar UN solo `k` por motor\n")
    W("`regret(k)` = media sobre los documentos de "
      "`CER(doc, k) − min_f CER(doc, f)`. Un `k` con arrepentimiento 0 sería "
      "óptimo en los cuatro documentos a la vez.\n")
    W("| configuración | mejor `k` fijo | regret medio | regret máx | "
      "`k*` de `d4` | regret | `k` de la regla | regret | regret de ×1,00 | "
      "regret del mejor `k` fijo **sin `patológico`** |")
    W("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    resumen = {}
    for _et, nombre in CONFIGS:
        if nombre not in datos:
            continue
        mejores = {}
        for doc in DOCS:
            m, _ = optimo(datos[nombre][doc])
            mejores[doc] = m
        reg = {}
        for f in FACTORES:
            ds = [cer(datos[nombre][doc][f]) for doc in DOCS
                  if cer(datos[nombre][doc][f]) is not None and mejores[doc] is not None]
            bs = [mejores[doc] for doc in DOCS
                  if cer(datos[nombre][doc][f]) is not None and mejores[doc] is not None]
            if not ds:
                continue
            difs = [a - b for a, b in zip(ds, bs)]
            reg[f] = (round(statistics.mean(difs), 2), round(max(difs), 2))
        if not reg:
            continue
        # el mismo calculo excluyendo `patologico`, que aporta 0,00 a todo y diluye
        d3docs = [x for x in DOCS if x != "patologico_escaneado"]
        reg3 = {}
        for f in FACTORES:
            difs = [cer(datos[nombre][doc][f]) - mejores[doc] for doc in d3docs
                    if cer(datos[nombre][doc][f]) is not None
                    and mejores[doc] is not None]
            if difs:
                reg3[f] = (round(statistics.mean(difs), 2), round(max(difs), 2))
        kmej3 = min(reg3, key=lambda f: reg3[f][0]) if reg3 else None
        kmej = min(reg, key=lambda f: reg[f][0])
        kvig = K_VIGENTE.get(nombre)
        rv = reg.get(kvig, (None, None))
        r1 = reg.get(1.0, (None, None))
        resumen[nombre] = {"reg": reg, "kmej": kmej, "kvig": kvig}
        kreg = K_REGLA.get(nombre)
        rr = reg.get(kreg, (None, None)) if kreg else (None, None)
        W(f"| {nombre} | ×{kmej:g} | {reg[kmej][0]:.2f} | {reg[kmej][1]:.2f} | "
          f"×{kvig:g} | " + (f"{rv[0]:.2f}" if rv[0] is not None else "—") + " | " +
          (f"×{kreg:g}" if kreg else "—") + " | " +
          (f"{rr[0]:.2f}" if rr[0] is not None else "—") + " | " +
          (f"{r1[0]:.2f}" if r1[0] is not None else "—") + " | " +
          (f"{reg3[kmej3][0]:.2f} (×{kmej3:g})" if reg3 else "—") + " |")

    W("\n### 3b. Arrepentimiento por factor, entero\n")
    for _et, nombre in CONFIGS:
        if nombre not in resumen:
            continue
        W(f"\n**{nombre}** — regret medio (máx) por factor:\n")
        W("| " + " | ".join(f"×{f:g}" for f in FACTORES) + " |")
        W("|" + "---:|" * len(FACTORES))
        W("| " + " | ".join(
            (f"{resumen[nombre]['reg'][f][0]:.2f} ({resumen[nombre]['reg'][f][1]:.2f})"
             if f in resumen[nombre]["reg"] else "—") for f in FACTORES) + " |")

    # --- 3c: el arrepentimiento, documento a documento ---
    W("\n### 3c. El arrepentimiento, documento a documento\n")
    W("Puntos de CER que se pierden en CADA documento por usar el `k` fijo en vez "
      "del óptimo de ese documento. `vig` = el `k` que hoy está en `CLAUDE.md`, "
      "salido de `d4`; `fijo` = el mejor `k` único sobre los cuatro documentos.\n")
    W("| configuración | `k` | " + " | ".join(DOC_CORTO[d] for d in DOCS) + " |")
    W("|---|---:|" + "---:|" * len(DOCS))
    for _et, nombre in CONFIGS:
        if nombre not in resumen:
            continue
        for etiq, kk in (("vig", resumen[nombre]["kvig"]),
                         ("fijo", resumen[nombre]["kmej"])):
            cel = []
            for doc in DOCS:
                c = cer(datos[nombre][doc].get(kk)) if kk in FACTORES else None
                m, _ = optimo(datos[nombre][doc])
                cel.append("—" if (c is None or m is None) else f"+{c - m:.2f}")
            W(f"| {nombre} | {etiq} ×{kk:g} | " + " | ".join(cel) + " |")

    # --- cuantizacion ---
    W("\n## 4. Cuantización de la métrica por documento\n")
    W("`CLAUDE.md` trampa 9: con pocos caracteres de referencia no puede haber "
      "gradiente. Cada carácter de error vale:\n")
    W("| documento | referencia | caracteres | 1 carácter = |")
    W("|---|---|---:|---:|")
    vistos = set()
    for _et, nombre in CONFIGS:
        if nombre not in datos:
            continue
        res_f, _f, _c = _res_fusionada(_et)
        d = {"res": res_f or {}}
        for doc in DOCS:
            if doc in vistos:
                continue
            r = d["res"].get(clave(1.0, doc))
            if r and "chars_ref_acentos" in r:
                n = r["chars_ref_acentos"]
                W(f"| `{doc}` | {r['referencia']} | {n} | {100.0 / n:.2f} puntos |")
                vistos.add(doc)
    # --- 5: dispersion del optimo ---
    W("\n## 5. ¿Se mueve más el óptimo entre documentos o entre motores?\n")
    W("Si el `k` fuera del **motor**, la dispersión de `k*` **dentro de un motor "
      "(entre documentos)** tendría que ser mucho menor que **dentro de un documento "
      "(entre motores)**. Se toma como `k*` el menor factor empatado en el mínimo, y "
      "se excluye `patológico`, que empata a 0,00 en casi todo el barrido y no "
      "discrimina.\n")
    docs_disc = [d for d in DOCS if d != "patologico_escaneado"]
    kest = {}
    for _et, nombre in CONFIGS:
        if nombre not in datos:
            continue
        for doc in docs_disc:
            m, fs = optimo(datos[nombre][doc])
            if fs:
                kest[(nombre, doc)] = min(fs)
    W("| eje | grupo | `k*` observados | rango (máx/mín) |")
    W("|---|---|---|---:|")
    import math
    r_mot, r_doc = [], []
    for _et, nombre in CONFIGS:
        ks = [kest[(nombre, d)] for d in docs_disc if (nombre, d) in kest]
        if len(ks) < 2:
            continue
        r_mot.append(max(ks) / min(ks))
        W(f"| **por motor** (entre documentos) | {nombre} | " +
          ", ".join(f"×{x:g}" for x in ks) + f" | ×{max(ks) / min(ks):.2f} |")
    for doc in docs_disc:
        ks = [kest[(n, doc)] for _e, n in CONFIGS if (n, doc) in kest]
        if len(ks) < 2:
            continue
        r_doc.append(max(ks) / min(ks))
        W(f"| **por documento** (entre motores) | `{doc}` | " +
          ", ".join(f"×{x:g}" for x in ks) + f" | ×{max(ks) / min(ks):.2f} |")
    if r_mot and r_doc:
        gm = lambda v: math.exp(statistics.mean(math.log(x) for x in v))  # noqa: E731
        W(f"\n**Media geométrica de los rangos: ×{gm(r_mot):.2f} fijando el motor "
          f"frente a ×{gm(r_doc):.2f} fijando el documento.** Fijar el motor reduce "
          "la dispersión del óptimo, pero **no la cierra**: sigue habiendo un factor "
          f"×{gm(r_mot):.2f} de indeterminación dentro de un mismo motor.\n")


    # --- 6: descomposicion de la varianza de log2(k*) ---
    W("\n## 6. Descomposición de la varianza de `log2(k*)`\n")
    W("La pregunta del encargo, en una cifra. Se toma `log2(k*)` de cada pareja "
      "(configuración, documento) —excluido `patológico`, que no discrimina— y se "
      "reparte su varianza entre el efecto del **motor** (medias por fila), el del "
      "**documento** (medias por columna) y el **residuo** (la interacción, que es "
      "justo lo que la regla vigente supone que no existe).\n")
    obs = {k: v for k, v in kest.items()}
    import math
    if len(obs) >= 6:
        y = {k: math.log2(v) for k, v in obs.items()}
        gran = statistics.mean(y.values())
        mots = sorted({m for m, _d in y})
        dcs = sorted({d for _m, d in y})
        mm = {m: statistics.mean([y[(m, d)] for d in dcs if (m, d) in y]) for m in mots}
        md = {d: statistics.mean([y[(m, d)] for m in mots if (m, d) in y]) for d in dcs}
        ss_t = sum((v - gran) ** 2 for v in y.values())
        ss_m = sum((mm[m] - gran) ** 2 for m, _d in y)
        ss_d = sum((md[d] - gran) ** 2 for _m, d in y)
        ss_r = ss_t - ss_m - ss_d
        W("| fuente | suma de cuadrados | % de la varianza |")
        W("|---|---:|---:|")
        for et, v in (("**motor**", ss_m), ("**documento**", ss_d),
                      ("**interacción (motor × documento)**", ss_r)):
            W(f"| {et} | {v:.3f} | {100 * v / ss_t:.1f} % |")
        W(f"| total | {ss_t:.3f} | 100 % |")
        W(f"\nn = {len(y)} parejas · {len(mots)} configuraciones × {len(dcs)} "
          "documentos.\n")
    io.open(os.path.join(BASE, "tablas.md"), "w", encoding="utf-8",
            newline="\n").write("\n".join(out) + "\n")
    print("\n".join(out[:0]))
    print(f"escrito {os.path.join(BASE, 'tablas.md')}  ({len(out)} lineas)")


if __name__ == "__main__":
    main()

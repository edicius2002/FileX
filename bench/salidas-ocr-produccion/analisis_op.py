# -*- coding: utf-8 -*-
"""G5 / B26 — las tres preguntas del criterio de reciclado, con numero.

  1. ¿crece la VRAM retenida con el NUMERO DE PAGINAS?      (fase repetido)
  2. ¿con los MEGAPIXELES ACUMULADOS?                        (fase repetido)
  3. ¿con los MEGAPIXELES DEL DOCUMENTO MAYOR?               (ascendente/directo)
  4. ¿y con el CAMINO recorrido hasta el?                    (ascendente vs directo)

Y el coste: arranque en frio (tanda C) frente al tiempo por pagina, para decir
cada cuantas paginas sale a cuenta reciclar.

uso: analisis_op.py <dir_salidas>
"""
import glob
import json
import os
import statistics
import sys

D = sys.argv[1]
J = os.path.join(D, "json")


def carga(patron):
    return {os.path.basename(f)[:-5]: json.load(open(f, encoding="utf-8"))
            for f in sorted(glob.glob(os.path.join(J, patron)))}


def recta(puntos):
    """Minimos cuadrados sobre (x, y). Devuelve (pendiente, ordenada, r2)."""
    n = len(puntos)
    mx = sum(p[0] for p in puntos) / n
    my = sum(p[1] for p in puntos) / n
    sxy = sum((p[0] - mx) * (p[1] - my) for p in puntos)
    sxx = sum((p[0] - mx) ** 2 for p in puntos)
    b = sxy / sxx if sxx else 0.0
    a = my - b * mx
    sst = sum((p[1] - my) ** 2 for p in puntos)
    sse = sum((p[1] - (a + b * p[0])) ** 2 for p in puntos)
    return b, a, (1 - sse / sst) if sst else 1.0


print("# 1-2. ¿Crece con las PAGINAS o con los Mpx ACUMULADOS?\n")
print("| motor | paginas | Mpx acum. final | delta 1a (MiB) | delta ultima | "
      "recorrido | pendiente MiB/pagina |")
print("|---|---:|---:|---:|---:|---:|---:|")
for etq, d in carga("D_*_repetido.json").items():
    c = d["celdas"]
    # La primera pagina incluye la reserva inicial del motor; el regimen
    # estacionario empieza en la segunda.
    est = c[1:]
    ds = [x["delta_sobre_base_MiB"] for x in est]
    b, _, _ = recta([(x["paginas_hasta_ahora"], x["delta_sobre_base_MiB"])
                     for x in est])
    print(f"| {d['meta']['motor']} | {len(c)} | {c[-1]['mpx_acumulados']} | "
          f"{c[0]['delta_sobre_base_MiB']} | {c[-1]['delta_sobre_base_MiB']} | "
          f"{max(ds) - min(ds)} | {b:+.2f} |")

print("\n# 3. ¿Crece con los Mpx del documento MAYOR?\n")
print("| motor | puntos (Mpx -> MiB) | MiB/Mpx | ordenada | r2 |")
print("|---|---|---:|---:|---:|")
modelo = {}
for etq, d in carga("D_*_ascendente.json").items():
    pts = [(c["mpx"], c["delta_sobre_base_MiB"]) for c in d["celdas"]
           if c["nota"] == "ascendente"]
    b, a, r2 = recta(pts)
    modelo[d["meta"]["motor"]] = (b, a)
    serie = " · ".join(f"{x:.2f}->{y}" for x, y in pts)
    print(f"| {d['meta']['motor']} | {serie} | {b:.0f} | {a:.0f} | {r2:.4f} |")

print("\n# 4. El CAMINO: mismo documento mayor (8,88 Mpx), dos rutas\n")
print("| motor | en escalera (MiB) | directo (MiB) | diferencia | ratio |")
print("|---|---:|---:|---:|---:|")
asc = carga("D_*_ascendente.json")
dir_ = carga("D_*_directo.json")
for etq, d in asc.items():
    m = d["meta"]["motor"]
    e = next((c for c in d["celdas"] if c["mpx"] > 8), None)
    o = dir_.get(f"D_{m}_directo")
    if not e or not o:
        continue
    od = max(c["delta_sobre_base_MiB"] for c in o["celdas"] if c["mpx"] > 8)
    print(f"| {m} | {e['delta_sobre_base_MiB']} | {od} | "
          f"{e['delta_sobre_base_MiB'] - od:+d} | "
          f"x{e['delta_sobre_base_MiB'] / od:.2f} |")


def frio_por_config():
    out = {}
    for ruta in sorted(glob.glob(os.path.join(D, "logs", "C_*.log"))):
        etq = os.path.basename(ruta)[2:-4]
        cargados, pasos = [], []
        for linea in open(ruta, encoding="utf-8", errors="replace"):
            linea = linea.strip()
            if not linea.startswith("{"):
                continue
            try:
                o = json.loads(linea)
            except Exception:
                continue
            (cargados if o.get("evento") == "cargado" else
             pasos if "paso" in o else []).append(o)
        if len(cargados) < 2:
            continue
        c, p = cargados[1:], pasos[1:]     # se descarta la 1a (trampa 7)
        out[etq] = {
            "n": len(c),
            "import_s": statistics.median(x["import_s"] for x in c),
            "constr_s": statistics.median(x["carga_modelo_s"] for x in c),
            "frio_s": statistics.median(x["arranque_frio_s"] for x in c),
            "pag1_ms": statistics.median(x["ms"] for x in p) if p else None,
        }
    return out


print("\n# 5. Coste del reciclado: arranque en frio, un proceso por repeticion\n")
frio = frio_por_config()
print("| configuracion | n | import s | construccion s | **frio s** | "
      "1a pagina ms |")
print("|---|---:|---:|---:|---:|---:|")
for etq, v in frio.items():
    print(f"| {etq} | {v['n']} | {v['import_s']:.3f} | {v['constr_s']:.3f} | "
          f"**{v['frio_s']:.3f}** | {v['pag1_ms']:.1f} |")

print("\n# 6. Amortizacion: cada cuantas paginas sale a cuenta reciclar\n")
# Tiempo por pagina en REGIMEN ESTACIONARIO (fase repetido, sin la primera).
est = {}
for etq, d in carga("D_*_repetido.json").items():
    est[d["meta"]["motor"]] = statistics.median(c["ms"] for c in d["celdas"][1:])
print("| motor | frio s (GPU) | ms/pagina estacionario | paginas para +10 % | "
      "+25 % | +50 % | +100 % |")
print("|---|---:|---:|---:|---:|---:|---:|")
MAPA = {"rapidocr": "C_ro6small_R6_cuda", "easyocr": "C_easyocr_cuda",
        "paddleocr": "C_paddleocr_cuda"}
for m, ms in est.items():
    k = MAPA.get(m)
    if not k or k not in frio:
        print(f"| {m} | (falta tanda C) | {ms:.1f} | | | | |")
        continue
    f = frio[k]["frio_s"] * 1000
    fila = " | ".join(f"{f / (x * ms):.1f}" for x in (0.10, 0.25, 0.50, 1.00))
    print(f"| {m} | {frio[k]['frio_s']:.2f} | {ms:.1f} | {fila} |")

print("\n# 7. Umbral operativo: cuantos Mpx caben en la VRAM libre que queda\n")
print("Con el modelo lineal de la seccion 3, `Mpx_max_seguro = "
      "(VRAM_libre - margen - ordenada) / (MiB/Mpx)`.\n")
print("| motor | MiB/Mpx | ordenada | Mpx con 6000 MiB libres | con 4000 | con 2000 |")
print("|---|---:|---:|---:|---:|---:|")
MARGEN = 500
for m, (b, a) in modelo.items():
    fila = " | ".join(f"{max(0, (L - MARGEN - a) / b):.2f}"
                      for L in (6000, 4000, 2000))
    print(f"| {m} | {b:.0f} | {a:.0f} | {fila} |")
print(f"\n(margen de seguridad {MARGEN} MiB; RapidOCR satura y su recta es una "
      "cota superior floja: por encima de ~4,4 Mpx no crece)")

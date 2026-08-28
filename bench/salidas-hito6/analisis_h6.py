# -*- coding: utf-8 -*-
"""S6 / hito 6 — la pregunta de la coresidencia, en una tabla.

    ¿`coresidente` == `solo_audio` + `solo_ocr` + `solo_nvenc`?

Medianas de las repeticiones, **descartando la primera de cada fase** (trampa 7:
Windows Defender infla el primer arranque). Todas las cifras son `delta` sobre la
base del propio proceso.

uso: analisis_h6.py [prefijo]   (por defecto `A`)
"""
import glob
import json
import os
import statistics
import sys

D = os.path.dirname(os.path.abspath(__file__))
PREFIJO = sys.argv[1] if len(sys.argv) > 1 else "A"

por_fase = {}
for p in sorted(glob.glob(os.path.join(D, "json", f"{PREFIJO}_*.json"))):
    j = json.load(open(p, encoding="utf-8"))
    f = j["fin"]
    por_fase.setdefault(f["fase"], []).append({
        "etiqueta": f["etiqueta"], "base": f["vram_base_MiB"],
        "pico": f["vram_pico_MiB"], "propio": f["coste_propio_MiB"],
        "s": f["total_s"], "ruido": f["ruido"], "salida": f["salida"],
        "hitos": {h["hito"]: h["pico_MiB"] - f["vram_base_MiB"] for h in j["hitos"]}})

print(f"== tanda {PREFIJO} ==  (la 1.ª corrida de cada fase se descarta, trampa 7)\n")
med = {}
print(f"{'fase':<14} {'n':>2} {'base med':>9} {'PROPIO med':>11} {'min':>6} "
      f"{'max':>6} {'recorrido':>10} {'sucias':>7}")
for fase, filas in sorted(por_fase.items()):
    utiles = filas[1:] if len(filas) > 1 else filas
    v = [x["propio"] for x in utiles]
    b = [x["base"] for x in utiles]
    sucias = sum(1 for x in utiles if x["ruido"]["etiqueta"] == "SUCIA")
    med[fase] = statistics.median(v)
    print(f"{fase:<14} {len(v):>2} {statistics.median(b):>9.0f} "
          f"{statistics.median(v):>11.0f} {min(v):>6} {max(v):>6} "
          f"{max(v)-min(v):>10} {sucias:>7}")

print()
partes = ("solo_audio", "solo_ocr", "solo_nvenc")
if all(k in med for k in partes):
    suma = sum(med[k] for k in partes)
    print(f"SUMA de las partes  : {suma:.0f} MiB "
          f"({' + '.join(f'{med[k]:.0f}' for k in partes)})")
    print("  ¿es aditiva la coresidencia? (ruido del instrumento: ±43 MiB)")
    for fase in ("coresidente", "coresidente_inv", "dos_procesos"):
        if fase not in med:
            continue
        real = med[fase]
        dif = real - suma
        print(f"    {fase:<16} {real:>6.0f} MiB · {dif:+6.0f} · ×{real/suma:.3f}"
              f" · ¿supera el ruido? {abs(dif) > 43}")
    if "coresidente_inv" in med and "dos_procesos" in med:
        a, b = med["coresidente_inv"], med["dos_procesos"]
        print(f"  precio de la arquitectura de DOS procesos: {b - a:+.0f} MiB "
              f"(×{b/a:.3f})")

print("\n-- desglose de hitos (delta sobre la base del proceso) --")
for fase, filas in sorted(por_fase.items()):
    utiles = filas[1:] if len(filas) > 1 else filas
    claves = []
    for x in utiles:
        for k in x["hitos"]:
            if k not in claves:
                claves.append(k)
    if not claves:
        continue
    trozos = []
    for k in claves:
        vals = [x["hitos"][k] for x in utiles if k in x["hitos"]]
        trozos.append(f"{k}={statistics.median(vals):.0f}")
    print(f"  {fase:<14} " + " · ".join(trozos))

print("\n-- tiempos (mediana, s) --")
for fase, filas in sorted(por_fase.items()):
    utiles = filas[1:] if len(filas) > 1 else filas
    print(f"  {fase:<14} {statistics.median([x['s'] for x in utiles]):.2f}")

print("\n-- trabajo hecho (mediana de la 1.ª corrida util) --")
for fase, filas in sorted(por_fase.items()):
    utiles = filas[1:] if len(filas) > 1 else filas
    if utiles:
        print(f"  {fase:<14} {utiles[0]['salida']}")

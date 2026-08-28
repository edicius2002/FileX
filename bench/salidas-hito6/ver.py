# -*- coding: utf-8 -*-
"""Vista rapida de las corridas de `coresidencia.py` que hay en `json/`."""
import glob
import json
import os
import sys

d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "json")
patron = sys.argv[1] if len(sys.argv) > 1 else "*"
for p in sorted(glob.glob(os.path.join(d, patron + ".json"))):
    j = json.load(open(p, encoding="utf-8"))
    f, m = j["fin"], j["meta"]
    print(f"--- {f['etiqueta']} ({f['fase']}) ---")
    print(f"  base {f['vram_base_MiB']} · pico {f['vram_pico_MiB']} · "
          f"PROPIO {f['coste_propio_MiB']} MiB · {f['muestras_vram']} muestras · "
          f"{f['total_s']} s")
    print(f"  salida: {f['salida']}")
    print(f"  ruido: {f['ruido']['etiqueta']} {f['ruido']['motivos']} "
          f"der×{f['ruido']['deriva_ratio']} niv×{f['ruido']['nivel_ratio']}")
    print("  hitos: " + " · ".join(f"{h['hito']}={h['pico_MiB']}" for h in j["hitos"]))
    if "providers" in m:
        print(f"  providers: {m['providers']}")

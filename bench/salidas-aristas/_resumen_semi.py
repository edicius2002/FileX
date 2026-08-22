# -*- coding: utf-8 -*-
"""E1 - resumen exacto del censo de semiaristas, para la tabla del informe."""
import json, os

S = r"D:\Work\research\FileX\bench\salidas-aristas"
s1 = json.load(open(os.path.join(S, "semi_salida.json"), encoding="utf-8"))
s2 = json.load(open(os.path.join(S, "semi_salida2.json"), encoding="utf-8"))
e1 = json.load(open(os.path.join(S, "semi_entrada.json"), encoding="utf-8"))
e2 = json.load(open(os.path.join(S, "semi_entrada2.json"), encoding="utf-8"))

for m in ("ffmpeg", "imagemagick"):
    ks = [k for k in s1 if k.startswith(m + "|")]
    viva = [k for k in ks if s1[k]["vivo"] or s2.get(k, {}).get("vivo")]
    mu = sorted(k.split("|")[1] for k in ks if k not in viva)
    rev = sorted(k.split("|")[1] for k in ks if not s1[k]["vivo"] and s2.get(k, {}).get("vivo"))
    pc = 100.0 * len(mu) / len(ks)
    print("SALIDA  %-12s declaradas=%d vivas=%d MUERTAS=%d (%.1f %%)" % (m, len(ks), len(viva), len(mu), pc))
    print("   muertas: " + ", ".join(mu))
    print("   revividas en 2a vuelta: " + ", ".join(rev))

for m in ("ffmpeg", "imagemagick"):
    ks = [k for k in e1 if k.startswith(m + "|")]
    nm = [k for k in ks if e1[k]["estado"] == "no_materializable"]
    fin = {k: (e2.get(k, {}).get("estado") or e1[k]["estado"]) for k in ks if k not in nm}
    viva = [k for k, v in fin.items() if v == "viva"]
    mu = sorted(k.split("|")[1] for k, v in fin.items() if v == "muerta")
    pc = 100.0 * len(mu) / len(fin)
    print("ENTRADA %-12s declaradas=%d no_materializables=%d vivas=%d MUERTAS=%d (%.1f %% del marco)"
          % (m, len(ks), len(nm), len(viva), len(mu), pc))
    print("   muertas: " + ", ".join(mu))

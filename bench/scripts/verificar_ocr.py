# -*- coding: utf-8 -*-
"""FASE 1-C: verificacion funcional del OCR contra el texto conocido del PDF."""
import os, re, sys, glob, json, unicodedata

ESPERADO = ["DOCUMENTO ESCANEADO",
            "Texto que solo existe como pixeles.",
            "Debe recuperarse con OCR."]

def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def lev(a, b):
    if a == b: return 0
    prev = list(range(len(b)+1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j]+1, cur[j-1]+1, prev[j-1]+(ca != cb)))
        prev = cur
    return prev[-1]

OUT = r"D:\Work\research\FileX\bench\salidas-fase1\ia"
filas = []
for ruta in sorted(glob.glob(os.path.join(OUT, "*"))):
    if not ruta.endswith((".txt", ".md")): continue
    base = os.path.basename(ruta)
    if "escaneado" not in base and "surya" not in base: continue
    texto = open(ruta, encoding="utf-8", errors="replace").read()
    n = norm(texto)
    det = []
    for e in ESPERADO:
        ne = norm(e)
        ok = ne in n
        # distancia minima sobre ventana deslizante si no hay coincidencia exacta
        best = 0 if ok else min(
            (lev(ne, n[i:i+len(ne)]) for i in range(max(1, len(n)-len(ne)+1))),
            default=len(ne))
        det.append({"esperado": e, "exacto": ok,
                    "dist_edicion": best,
                    "similitud_pct": round(100*(1 - best/max(1,len(ne))), 1)})
    aciertos = sum(1 for d in det if d["exacto"])
    filas.append({"archivo": base, "chars": len(texto),
                  "frases_exactas": f"{aciertos}/3", "detalle": det})

print(json.dumps(filas, ensure_ascii=False, indent=2))
json.dump(filas, open(os.path.join(OUT, "verificacion_ocr.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

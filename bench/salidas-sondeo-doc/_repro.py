# -*- coding: utf-8 -*-
"""S3 — ¿es reproducible byte a byte una conversión de estos tres motores?

Salió al recoger: `_d2.py` §C convirtió **el mismo `entrada.mobi` a EPUB en tres
ejecuciones** y dio 19 720, 20 982 y 131 318 B. Un factor de ×6,7 sobre la misma
entrada, el mismo motor y la misma imagen no es ruido de medición: o el motor no
es determinista, o el arnés está mirando otro fichero. Esto lo separa.

`CLAUDE.md` trampa 22 ya avisa de lo contrario para ImageMagick
(`SOURCE_DATE_EPOCH` no hace reproducible su PDF). Aquí se mide para Calibre y
Pandoc, que es lo que un `MANIFIESTO.md` con `sha256` necesita saber.

    python bench/salidas-sondeo-doc/_repro.py
"""
from __future__ import annotations

import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex.nucleo import FileX  # noqa: E402

from _sonda23 import (CENTINELA, SAL, busca_arista, convertir_forzando,  # noqa: E402
                      entrada_de, sha, texto_de)

N = 3
CASOS = (("doc_calibre", "mobi", "epub"),
         ("doc_calibre", "epub", "pdf"),
         ("doc_pandoc", "md", "html"))


def main() -> int:
    for f in (sys.stdout, sys.stderr):
        try:
            f.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    out = os.path.join(SAL, "out-repro")
    os.makedirs(out, exist_ok=True)
    fx = FileX()
    res = []
    for motor, o, d in CASOS:
        ar = busca_arista(fx, motor, o, d)
        if ar is None:
            res.append({"motor": motor, "arista": f"{o}>{d}", "motivo": "no está"})
            continue
        filas = []
        for i in range(N):
            salida = os.path.join(out, f"{motor[4:]}_{o}2{d}_{i}.{d}")
            espia = os.path.join(out, f"{motor[4:]}_{o}2{d}_{i}_desechable")
            conv = convertir_forzando(fx, ar, entrada_de(o), salida, espia=espia)
            ruta = salida if os.path.isfile(salida) else os.path.join(espia, f"salida.{d}")
            if not os.path.isfile(ruta):
                filas.append({"i": i, "bytes": 0, "sha256": "", "ok": conv.ok})
                continue
            txt = texto_de(ruta)
            filas.append({"i": i, "bytes": os.path.getsize(ruta),
                          "sha256": sha(ruta), "ok": conv.ok,
                          "caracteres": len(txt), "centinela": CENTINELA in txt})
        tam = {f["bytes"] for f in filas}
        hsh = {f["sha256"] for f in filas}
        r = {"motor": motor, "arista": f"{o}>{d}", "n": N, "filas": filas,
             "bytes_distintos": len(tam), "sha_distintos": len(hsh),
             "min_bytes": min(tam), "max_bytes": max(tam),
             "razon_max_min": round(max(tam) / max(1, min(tam)), 2)}
        res.append(r)
        print(f"{motor[4:]:<12} {o}->{d:<5} n={N}  bytes {sorted(tam)}  "
              f"sha distintos={len(hsh)}  x{r['razon_max_min']}", flush=True)
    with open(os.path.join(SAL, "repro.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

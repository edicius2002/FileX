# -*- coding: utf-8 -*-
"""K1 / hito 5 — la demostración que NO depende del mensaje del grafo.

El criterio amarillo del hito 1 pide un par de formatos donde compitan un camino
que conserva el texto y otro que lo rasteriza. Aquí se hacen **los dos, de
verdad, por el núcleo**, y se mide el texto que sobrevive a cada uno. Los bytes
no opinan.

    python bench/salidas-hito5/_camino.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _sonda import CENTINELA, ENT, sha, texto_de  # noqa: E402
from filex.nucleo import FileX  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    for f in (sys.stdout, sys.stderr):
        try:
            f.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    fx = FileX()
    tmp = tempfile.mkdtemp(prefix="filex-camino-")
    ent = os.path.join(ENT, "entrada.docx")
    out = {"entrada": ent, "sha256_entrada": sha(ent), "caminos": []}

    dec = fx.planificar("x.docx", "y.pdf")
    out["elegido_por_el_grafo"] = {
        "camino": dec.camino.formatos,
        "motor": [p.arista.motor for p in dec.camino.pasos],
        "submotor": [p.arista.parametrizacion for p in dec.camino.pasos],
        "coste": round(dec.camino.coste, 3),
        "rasteriza": dec.camino.rasteriza,
        "rechazados": [{"camino": c.formatos, "coste": round(c.coste, 3),
                        "motivo": m} for c, m in dec.rechazados],
    }

    # ---- camino A: el que elige el grafo -------------------------------
    a = os.path.join(tmp, "A_directo.pdf")
    cA = fx.convertir(ent, a, timeout=300)
    tA = texto_de(a) if cA.ok else ""
    out["caminos"].append({
        "nombre": "A · docx→pdf (LibreOffice)",
        "ok": cA.ok, "veredicto": cA.veredicto,
        "ms": round(sum(s.ms for s in cA.saltos), 1),
        "bytes": os.path.getsize(a) if os.path.isfile(a) else 0,
        "sha256": sha(a) if os.path.isfile(a) else "",
        "caracteres": len(tA), "centinela": CENTINELA in tA,
        "tabla_ax1": "AX-1" in tA,
        "contrato": [s.cobertura for s in cA.saltos],
    })

    # ---- camino B: el que el grafo RECHAZA, forzado salto a salto ------
    b1 = os.path.join(tmp, "B_medio.png")
    cB1 = fx.convertir(ent, b1, timeout=300)
    b = os.path.join(tmp, "B_rasterizado.pdf")
    cB2 = fx.convertir(b1, b, timeout=300) if cB1.ok else None
    tB = texto_de(b) if (cB2 and cB2.ok) else ""
    out["caminos"].append({
        "nombre": "B · docx→png→pdf (LibreOffice + ImageMagick)",
        "ok": bool(cB2 and cB2.ok),
        "veredicto": cB2.veredicto if cB2 else "",
        "ms": round(sum(s.ms for s in cB1.saltos) +
                    (sum(s.ms for s in cB2.saltos) if cB2 else 0), 1),
        "bytes": os.path.getsize(b) if os.path.isfile(b) else 0,
        "sha256": sha(b) if os.path.isfile(b) else "",
        "caracteres": len(tB), "centinela": CENTINELA in tB,
        "tabla_ax1": "AX-1" in tB,
        "texto_literal": tB[:120],
        "contrato": [s.cobertura for s in (cB2.saltos if cB2 else [])],
    })

    for c in out["caminos"]:
        print(f"{c['nombre']:<48} ok={c['ok']} {c['bytes']:>8} B "
              f"car={c['caracteres']:>5} cent={c['centinela']} "
              f"{c['ms']:>9.0f} ms  contrato={c['veredicto']}")
    print("\ngrafo elige:", out["elegido_por_el_grafo"]["camino"],
          "coste", out["elegido_por_el_grafo"]["coste"])

    with open(os.path.join(AQUI, "camino.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

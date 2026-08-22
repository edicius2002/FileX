# -*- coding: utf-8 -*-
"""P2 / C15-d - `imagen -> pdf` SIN densidad: no es un caso raro, es el defecto.

E1 sec.6: once de las doce degradaciones del estrato PDF son la MISMA regla,
`P7 - 1 px -> 1 pt: pagina absurda (1920 x 1080 pt = 677 x 381 mm)`. No entra en el
50,5 % (una degradacion no es una arista nominal), pero es la degradacion mas
sistematica que E1 encontro y el encargo la pone entre los sospechosos.

Se comparan TRES invocaciones sobre las mismas aristas:
  0  ConvertX          magick ENT -auto-orient SAL.pdf
  D  densidad fija     ... -units PixelsPerInch -density 150 ...
  A4 ajuste a pagina   ... -density <ppp que hace que quepa en A4> ...
y se mide el TAMANO DE PAGINA en mm que sale, que es lo que P7 juzga.

Escribe densidad_p2.json
"""
import os, sys, json, glob, re

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-invocacion")
TMP = os.path.join(SAL, "tmp_dens")
sys.path.insert(0, SAL)
from _p2_lib import corre, limpia, juzga, sonda_y_veredicto

A4_MM = (210.0, 297.0)
GS = r"C:\Program Files\gs\gs10.07.0\bin\gswin64c.exe"


def pagina_mm(pdf):
    """Tamano de la primera pagina, leido con Ghostscript (bbox en puntos)."""
    import subprocess
    p = subprocess.run([GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-sDEVICE=bbox",
                        "-dFirstPage=1", "-dLastPage=1", pdf],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       errors="replace", timeout=120)
    m = re.search(r"%%HiResBoundingBox:\s*([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)",
                  (p.stdout or "") + (p.stderr or ""))
    if not m:
        return None
    x0, y0, x1, y1 = (float(x) for x in m.groups())
    return (round((x1 - x0) * 25.4 / 72, 1), round((y1 - y0) * 25.4 / 72, 1))


if __name__ == "__main__":
    limpia(TMP)
    inv = json.load(open(os.path.join(SAL, "inventario_e1.json"), encoding="utf-8"))
    idx = json.load(open(os.path.join(SAL, "pool_indice.json"), encoding="utf-8"))
    casos = [r for r in inv["degradados_pdf"] if r["b"] == "pdf"]
    print("aristas imagen->pdf DEGRADADAS por E1: %d\n" % len(casos), flush=True)
    res = []
    for i, r in enumerate(casos):
        a = r["a"]
        ent = (idx.get(a) or {}).get("ruta")
        if not ent:
            continue
        g = (idx.get(a) or {}).get("geometria")
        fila = {"a": a, "geometria": g}
        for etiqueta, extra in (("convertx", []),
                                ("densidad150", ["-units", "PixelsPerInch",
                                                 "-density", "150"]),
                                ("ajuste_a4", None)):
            if extra is None:
                if not g:
                    continue
                ppp = max(g[0] / (A4_MM[0] / 25.4), g[1] / (A4_MM[1] / 25.4))
                extra = ["-units", "PixelsPerInch", "-density", "%.2f" % ppp]
            for f in glob.glob(os.path.join(TMP, "*")):
                try:
                    os.remove(f)
                except OSError:
                    pass
            sal = os.path.join(TMP, "d%02d_%s.pdf" % (i, etiqueta))
            args = ["magick", ent, "-auto-orient"] + extra + ["pdf:" + sal]
            rc, err, ms = corre(args, 60, cwd=TMP)
            tam = os.path.getsize(sal) if os.path.exists(sal) else -1
            pag = pagina_mm(sal) if tam > 0 else None
            son, ver = ({}, {})
            if rc == 0 and tam > 0:
                son, ver = sonda_y_veredicto(sal, ent)
            nom, cat, mot, _ = juzga(rc, tam, os.path.getsize(ent), "pdf", son, ver)
            p7 = any("P7" in (h.get("regla") or "") for h in ver.get("hallazgos", []))
            fila[etiqueta] = {"rc": rc, "bytes": tam, "pagina_mm": pag,
                              "veredicto": cat, "P7": p7, "ms": round(ms, 1),
                              "motivo": mot[:150], "args": args}
        res.append(fila)
        print("  %-8s %-12s cx=%-16s d150=%-16s a4=%-16s  P7 %s/%s/%s" %
              (a, str(g),
               str(fila.get("convertx", {}).get("pagina_mm")),
               str(fila.get("densidad150", {}).get("pagina_mm")),
               str(fila.get("ajuste_a4", {}).get("pagina_mm")),
               fila.get("convertx", {}).get("P7"),
               fila.get("densidad150", {}).get("P7"),
               fila.get("ajuste_a4", {}).get("P7")), flush=True)
    json.dump(res, open(os.path.join(SAL, "densidad_p2.json"), "w", encoding="utf-8"),
              indent=0, ensure_ascii=False)
    from collections import Counter
    for et in ("convertx", "densidad150", "ajuste_a4"):
        c = Counter(f[et]["veredicto"] for f in res if et in f)
        p = sum(1 for f in res if f.get(et, {}).get("P7"))
        print("\n%-12s %s   con P7: %d de %d" % (et, dict(c), p, len(res)))

# -*- coding: utf-8 -*-
"""E1 / C8 - verificacion de las salidas producidas en el contenedor.

Tres comprobaciones por salida:
  1) firma real (verificador congelado, punto 1 del contrato);
  2) supervivencia del centinela FILEXSENTINELA7743 y de la tabla (para documentos);
  3) para SVG, comparacion de rasterizadores (Inkscape / resvg / magick-Windows).
"""
import os, sys, json, subprocess, re

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-aristas")
C8 = os.path.join(SAL, "c8")
OUT = os.path.join(C8, "out")
sys.path.insert(0, SAL)
import verificador_congelado as V

CENT = "FILEXSENTINELA7743"


def texto_de(p):
    """Texto plano recuperable sin motores externos: .txt directo, zip (ooxml/epub),
    o el .txt que ya dejo Ghostscript junto al PDF."""
    b = p.lower()
    try:
        if b.endswith((".txt", ".md", ".html", ".rtf", ".csv")):
            return open(p, encoding="utf-8", errors="replace").read()
        if os.path.exists(p + ".txt"):
            return open(p + ".txt", encoding="utf-8", errors="replace").read()
        if b.endswith((".docx", ".odt", ".epub", ".azw3", ".mobi")):
            import zipfile
            if zipfile.is_zipfile(p):
                z = zipfile.ZipFile(p)
                t = []
                for n in z.namelist():
                    if n.endswith((".xml", ".xhtml", ".html", ".htm")):
                        t.append(re.sub(r"<[^>]+>", " ", z.read(n).decode("utf-8", "replace")))
                return " ".join(t)
            d = open(p, "rb").read()
            return d.decode("utf-8", "replace")
    except Exception as e:
        return "<<error: %s>>" % e
    return ""


def main():
    filas = []
    for r, _, fs in os.walk(OUT):
        for f in sorted(fs):
            if f.endswith(".pdf.txt"):
                continue
            p = os.path.join(r, f)
            ext = f.rsplit(".", 1)[-1].lower()
            son = V.sondear(p, "proceso")
            t = texto_de(p)
            filas.append({
                "fichero": os.path.relpath(p, OUT).replace("\\", "/"),
                "ext": ext, "bytes": os.path.getsize(p),
                "firma": son.get("firma"), "categoria": son.get("categoria"),
                "ancho": son.get("ancho"), "alto": son.get("alto"),
                "centinela": CENT in t,
                "tabla_AX1": ("AX-1" in t) or ("AX1" in t),
                "chars": len(t.strip()),
            })
    for x in sorted(filas, key=lambda y: y["fichero"]):
        print("%-28s %-6s %9d  firma=%-9s cent=%-5s tabla=%-5s chars=%d"
              % (x["fichero"], x["ext"], x["bytes"], x["firma"], x["centinela"],
                 x["tabla_AX1"], x["chars"]))
    json.dump(filas, open(os.path.join(C8, "verificado.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)

    # --- SVG: tercer rasterizador, el magick de Windows, y comparacion
    svg = os.path.join(C8, "in", "e1.svg")
    win = os.path.join(C8, "out", "s_magick_win.png")
    p = subprocess.run(["magick", svg, win], stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, timeout=60)
    print("\nmagick(Windows) svg->png rc=%d bytes=%s" % (
        p.returncode, os.path.getsize(win) if os.path.exists(win) else -1))
    print("stderr:", (p.stderr or "")[-200:])
    pares = [("s_ink.png", "s_resvg.png"), ("s_ink.png", "s_magick_win.png"),
             ("s_resvg.png", "s_magick_win.png")]
    comp = []
    for a, b in pares:
        pa, pb = os.path.join(OUT, a), os.path.join(OUT, b)
        if not (os.path.exists(pa) and os.path.exists(pb)):
            continue
        sa, sb = V.sondear(pa, "proceso"), V.sondear(pb, "proceso")
        q = subprocess.run(["magick", "compare", "-metric", "RMSE", pa, pb, "null:"],
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
        comp.append({"a": a, "b": b, "geom_a": "%sx%s" % (sa.get("ancho"), sa.get("alto")),
                     "geom_b": "%sx%s" % (sb.get("ancho"), sb.get("alto")),
                     "rmse": (q.stderr or q.stdout).strip()[:60]})
        print("  %-18s vs %-18s  %sx%s vs %sx%s  RMSE=%s" % (
            a, b, sa.get("ancho"), sa.get("alto"), sb.get("ancho"), sb.get("alto"),
            comp[-1]["rmse"]))
    json.dump(comp, open(os.path.join(C8, "svg_comparacion.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()

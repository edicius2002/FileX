# -*- coding: utf-8 -*-
"""F1 / paso 0 - LEER (sin tocar) la muestra de E1 y medir el punto de partida.

bench/salidas-aristas/muestra.json es SOLO LECTURA. Aqui se recalcula, con los
mismos criterios de _muestra.py, cuantas aristas tuvieron el punto 1 del contrato
(N2, firma real frente a formato pedido) EVALUABLE, y se desglosa POR QUE no lo
fue en las demas. Esa descomposicion es lo que decide si el 88 % es deuda de
vocabulario o propiedad de los formatos.

Uso: python _analiza_muestra.py
"""
import os, json, sys
from collections import Counter, defaultdict

RAIZ = r"D:\Work\research\FileX"
MUE = os.path.join(RAIZ, r"bench\salidas-aristas\muestra.json")
SAL = os.path.join(RAIZ, r"bench\salidas-firmas")

# Copia LITERAL de la tabla CLASE de bench/salidas-aristas/_muestra.py (lineas 69-95).
CLASE = {}
for _f, _v in (
    ("png", "png png8 png00 png24 png32 png48 png64"),
    ("gif", "gif gif87"),
    ("jpeg", "jpg jpeg jpe jfif jpg2"),
    ("tiff", "tif tiff tiff64 ptif group4 g3 g4 fax"),
    ("bmp", "bmp bmp2 bmp3 dib"),
    ("pdf", "pdf"),
    ("webp", "webp"),
    ("wav", "wav w64"),
    ("avi", "avi"),
    ("matroska", "mkv webm mka mks"),
    ("isobmff", "mp4 m4v m4a m4b mov 3gp 3g2 f4v ismv isma mj2 avif heic heif"),
    ("flac", "flac"),
    ("mp3", "mp3 mp2 m1a m2a mpa"),
    ("ogg", "ogg oga ogv opus spx ogx"),
    ("zip", "zip epub docx xlsx pptx odt ods odp cbz jar"),
    ("gzip", "gz tgz"),
    ("texto", "txt csv json xml html htm md srt vtt ass ssa ttml lrc ffmeta y4m "
               "svg tex rtf ps eps sub scc jss js chk"),
):
    for _e in _v.split():
        CLASE[_e] = _f
INDEF = {"desconocido", "riff", None, ""}


def main():
    d = json.load(open(MUE, encoding="utf-8"))
    gen = [r for r in d["general"] if "nominal" in r]
    pdf = [r for r in d["pdf"] if "nominal" in r]
    for nombre, lote in (("GENERAL n=%d" % len(gen), gen), ("PDF n=%d" % len(pdf), pdf),
                         ("UNION n=%d" % (len(gen) + len(pdf)), gen + pdf)):
        ev = sum(1 for r in lote if r.get("n2_evaluable"))
        confich = [r for r in lote if r.get("rc") == 0 and (r.get("bytes") or 0) > 0]
        print("\n=== %s ===" % nombre)
        print("  n2_evaluable            : %d / %d = %.1f %%" % (ev, len(lote), 100 * ev / len(lote)))
        print("  con fichero (rc=0,>0 B) : %d" % len(confich))
        print("  n2_evaluable sobre esos : %.1f %%" % (100 * ev / max(1, len(confich))))
        # por que NO fue evaluable
        motivos = Counter()
        det = defaultdict(Counter)
        for r in lote:
            if r.get("n2_evaluable"):
                continue
            if r.get("rc") != 0 or (r.get("bytes") or 0) <= 0:
                motivos["A_sin_fichero(N1)"] += 1
                continue
            b = r["b"]
            f = (r.get("firma") or "").lower()
            sin_esp = CLASE.get(b) is None
            firma_indef = f in INDEF
            if sin_esp and firma_indef:
                motivos["D_ambas"] += 1
                det["D_ambas"][b] += 1
            elif sin_esp:
                motivos["B_destino_sin_expectativa"] += 1
                det["B_destino_sin_expectativa"][b] += 1
            elif firma_indef:
                motivos["C_firma_no_reconocida"] += 1
                det["C_firma_no_reconocida"][b] += 1
            else:
                motivos["Z_otro"] += 1
        print("  motivos de NO evaluable :")
        for k, v in sorted(motivos.items()):
            print("     %-28s %4d" % (k, v))
        if nombre.startswith("UNION"):
            for k in ("B_destino_sin_expectativa", "C_firma_no_reconocida", "D_ambas"):
                print("\n  --- destinos en %s (top 40) ---" % k)
                print("   ", dict(det[k].most_common(40)))

    todo = gen + pdf
    # inventario de destinos y firmas observadas
    dst = Counter(r["b"] for r in todo)
    frm = Counter((r.get("firma") or "-") for r in todo if r.get("rc") == 0 and (r.get("bytes") or 0) > 0)
    print("\n=== destinos distintos en la muestra: %d ===" % len(dst))
    print("=== firmas observadas (con fichero) ===")
    for k, v in frm.most_common():
        print("   %-14s %4d" % (k, v))
    orig = Counter(r["a"] for r in todo)
    print("\n=== origenes distintos: %d ===" % len(orig))
    json.dump({"destinos": dict(dst), "origenes": dict(orig)},
              open(os.path.join(SAL, "muestra_inventario.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()

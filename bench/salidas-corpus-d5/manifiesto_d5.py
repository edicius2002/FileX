# -*- coding: utf-8 -*-
"""G3 / paso 3 — escribe los dos MANIFIESTO y el fichero de referencia.

El texto de referencia se escribe DESDE `d4_texto.BLOQUES`, no a mano: es la misma
cadena que renderiza el generador y la misma que lee el evaluador. Un corpus cuyo
texto de referencia se copia a mano acaba divergiendo del documento.
"""
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from d4_texto import BLOQUES  # noqa: E402
from d5_texto import MAQUETAS  # noqa: E402
from gen_corpus_d5 import CANDIDATAS, SEMILLA  # noqa: E402

RAIZ = r"D:\Work\research\FileX"
BASE = os.path.join(RAIZ, r"bench\salidas-corpus-d5")
PDF = os.path.join(RAIZ, r"corpus\pdf")
TMP = os.path.join(BASE, "tmp")

FAMILIAS = [
    ("escaneado_d5", "B15 — pocos ppp nativos (60-90)"),
    ("patologico_d5", "B19 — patologico de verdad, sustituto de patologico_escaneado"),
    ("realista_d5", "B12 — degradacion realista (lomo, curvatura, transparencia)"),
]
ORDEN = ["escaneado_d5b", "escaneado_d5", "escaneado_d5c", "escaneado_d5a",
         "patologico_d5a", "patologico_d5b", "patologico_d5", "patologico_d5e",
         "realista_d5a", "realista_d5b", "realista_d5", "realista_d5e"]


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def ppp_nativos(ruta):
    import pypdfium2 as pdfium
    d = pdfium.PdfDocument(ruta)
    p = d[0]
    w_pt, _ = p.get_size()
    mejor = None
    for obj in p.get_objects(filter=(pdfium.raw.FPDF_PAGEOBJ_IMAGE,)):
        m = obj.get_metadata()
        if mejor is None or m.width * m.height > mejor[0] * mejor[1]:
            mejor = (m.width, m.height)
    d.close()
    return round(mejor[0] / (w_pt / 72.0), 1), f"{mejor[0]}x{mejor[1]}", round(w_pt, 2)


def referencia_txt():
    lineas = []
    for etq, v in BLOQUES.items():
        lineas.append(f"# [{etq}]")
        lineas.extend(v)
        lineas.append("")
    plano = " ".join(" ".join(v) for v in BLOQUES.values())
    lineas.append("# [cadena plana que usa el evaluador]")
    lineas.append(plano)
    return "\n".join(lineas) + "\n", plano


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cfgs = {c[0]: (c[1], c[3]) for c in CANDIDATAS}
    cand = {c["nombre"]: c
            for c in json.load(open(os.path.join(BASE, "json",
                                                 "candidatas_d5.json"),
                                    encoding="utf-8"))}

    txt, plano = referencia_txt()
    fref = os.path.join(PDF, "REFERENCIA-d5.txt")
    open(fref, "w", encoding="utf-8", newline="\n").write(txt)
    print(f"referencia -> {fref}  ({len(plano)} chars planos, "
          f"{sum(1 for c in plano if c in 'áéíóúüñÁÉÍÓÚÜÑ')} acentuados)")

    filas = []
    for nom in ORDEN:
        ruta = os.path.join(PDF, nom + ".pdf")
        ppp, px, w_pt = ppp_nativos(ruta)
        receta, cfg = cfgs[nom]
        filas.append({"nombre": nom, "receta": receta, "ppp_nativos": ppp,
                      "px": px, "ancho_pt": w_pt,
                      "bytes": os.path.getsize(ruta), "sha256": sha256(ruta),
                      "jpg_sha256": cand[nom]["jpg_sha256"],
                      "jpg_bytes": cand[nom]["jpg_bytes"],
                      "cfg": cfg})
    json.dump(filas, open(os.path.join(BASE, "json", "manifiesto_d5.json"), "w",
                          encoding="utf-8"), ensure_ascii=False, indent=2)
    for f in filas:
        print(f"{f['nombre']:16s} ppp={f['ppp_nativos']:5.1f} px={f['px']:10s} "
              f"pt={f['ancho_pt']:7.2f} bytes={f['bytes']:7d} "
              f"sha={f['sha256'][:16]} jpg={f['jpg_sha256'][:16]}")


if __name__ == "__main__":
    main()

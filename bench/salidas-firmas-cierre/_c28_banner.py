"""C28 / paso 3 - «BANNER DEL ESCRITOR» NO ES UNA SOLA COSA.

El pendiente propone atacar esta clase con **un segundo escritor por formato**.
Antes de comprar el remedio hay que mirar el dato (trampa 64: un pendiente que
propone un mecanismo lleva dentro un coste que nadie ha medido). Dos preguntas,
las dos con respuesta en ficheros que ya existen:

  1. ¿Cuantos de estos formatos tienen de verdad un SEGUNDO escritor entre los
     20 adaptadores de esta maquina y del contenedor? (si la respuesta es cero,
     el remedio no tiene ingredientes)
  2. ¿Es el prefijo un banner, o es un MARCADOR DEL FORMATO que ademas lleva la
     version del escritor dentro? No son lo mismo: `#FIG 3.2` y `GIMP Palette`
     son cabeceras que la especificacion EXIGE; `; Created by the Open Asset
     Import Library` es un comentario que otro escritor no pondria.

Uso:  python bench/salidas-firmas-cierre/_c28_banner.py
"""
import json
import os
import sys
from collections import defaultdict

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIRMAS_F1 = os.path.join(RAIZ, "bench", "salidas-firmas")
sys.path.insert(0, RAIZ)
from filex import verificador as V  # noqa: E402


def main():
    cat = json.load(open(os.path.join(FIRMAS_F1, "categorias.json"),
                         encoding="utf-8"))
    formatos = json.load(open(os.path.join(FIRMAS_F1, "formatos.json"),
                              encoding="utf-8"))
    censos = {}
    for nom in ("firmas_censo_local.json", "firmas_censo_contenedor.json"):
        censos[nom] = json.load(open(os.path.join(FIRMAS_F1, nom),
                                     encoding="utf-8"))

    # cuantos ADAPTADORES de ConvertX declaran cada formato como destino
    declaran = defaultdict(set)
    for ad, d in (formatos.get("por_adaptador") or {}).items():
        for f in d.get("to", []):
            declaran[f].add(ad)

    escriben = defaultdict(set)
    for d in censos.values():
        for motor, fs in d.items():
            if not isinstance(fs, dict):
                continue
            for f, e in fs.items():
                if isinstance(e, dict) and (e.get("muestras") or e.get("cab")):
                    escriben[f].add(motor)

    filas = []
    for fmt, e in sorted(cat.items()):
        if not isinstance(e, dict) or e.get("cat_nuevo") != "0_indeterminado":
            continue
        if (e.get("motivo") or "") != "el prefijo es el banner del escritor, no del formato":
            continue
        pre = e.get("prefijo") or ""
        txt = bytes.fromhex(pre).decode("latin-1") if pre else ""
        filas.append({
            "formato": fmt,
            "prefijo_len": e.get("prefijo_len"),
            "prefijo_txt": txt,
            "escritores_reales": sorted(escriben.get(fmt, ())),
            "adaptadores_que_lo_declaran": sorted(declaran.get(fmt, ())),
            "hay_segundo_escritor": len(escriben.get(fmt, ())) >= 2,
            "hay_segundo_adaptador": len(declaran.get(fmt, ())) >= 2,
            "firma_de_familia_que_daria": None,
        })
    # ¿que diria la sonda si mirase el prefijo como texto? (familia, no formato)
    for f in filas:
        t = f["prefijo_txt"].lstrip().lower()
        if t.startswith("<?xml"):
            f["firma_de_familia_que_daria"] = "xml"
        elif t.startswith("<!doctype html") or t.startswith("<html"):
            f["firma_de_familia_que_daria"] = "html"
        elif t and all(c in "\t\r\n" or 0x20 <= ord(c) < 0x7f for c in f["prefijo_txt"]):
            f["firma_de_familia_que_daria"] = "texto"

    res = {"n": len(filas),
           "con_segundo_escritor_real": [f["formato"] for f in filas
                                         if f["hay_segundo_escritor"]],
           "con_segundo_adaptador_declarado": [f["formato"] for f in filas
                                               if f["hay_segundo_adaptador"]],
           "filas": filas}
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

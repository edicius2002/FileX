# -*- coding: utf-8 -*-
"""C49 / worker9 - Clasificacion de los 445 y recuento del 54,78 %.

Dos mitades:
  (1) CONTROL: reproduce EXACTAMENTE la agregacion de _agrega.py sobre aristas.json.
      Si no da 138 501 / 22 235 / 40 252 / 75 874 / 140, no se sigue (trampa 58: hay
      que reproducir la medida ajena ANTES de tocarla).
  (2) RECUENTO: retira de la POBLACION las aristas cuyo origen no es un fichero
      (clases `no_aplica`) y vuelve a contar. No se retira nada mas.

Solo lectura. No ejecuta ningun motor.
Escribe clasificacion.json y recuento.json EN ESTE DIRECTORIO.
"""
import os, json, collections

AQUI = os.path.dirname(os.path.abspath(__file__))
SAL = os.path.abspath(os.path.join(AQUI, "..", "salidas-aristas"))

# ---------------------------------------------------------------- clases
# Cada token va con el CAMPO DE METADATOS que lo decide. La regla esta en el
# informe; aqui solo se aplica.
NO_APLICA = {
    # ffmpeg: aparece en `-devices` (lista APARTE de -demuxers) y no es demuxer.
    "ffmpeg|lavfi":  ("dispositivo", "-devices: 'D  lavfi  Libavfilter virtual input device'"),
    "ffmpeg|openal": ("dispositivo", "-devices: 'D  openal  OpenAL audio capture device'"),
}
# ImageMagick: modulo URL -> localizador, no formato.
for t in ("file", "ftp", "http", "https"):
    NO_APLICA["imagemagick|" + t] = ("protocolo", "-list format: Module=URL, 'Uniform Resource Locator'")
# ImageMagick: coders que SINTETIZAN la imagen (o la capturan); no decodifican fichero.
for t, mod in (("xc", "XC"), ("canvas", "XC"), ("gradient", "GRADIENT"),
               ("radial-gradient", "GRADIENT"), ("plasma", "PLASMA"), ("fractal", "PLASMA"),
               ("pattern", "PATTERN"), ("caption", "CAPTION"), ("label", "LABEL"),
               ("screenshot", "SCREENSHO")):
    NO_APLICA["imagemagick|" + t] = ("generador", "-list format: Module=%s, modo r--" % mod)

# ImageMagick: pseudo-formatos que SI consumen un fichero o una imagen. NO se mueven.
DUDOSOS_IM = {"tile", "stegano", "clip", "mask", "text", "msl", "pango"}


def clasifica():
    semi = json.load(open(os.path.join(SAL, "semi_entrada.json"), encoding="utf-8"))
    cruce = {f["clave"]: f for f in json.load(
        open(os.path.join(AQUI, "cruce.json"), encoding="utf-8"))["filas"]}
    censo = json.load(open(os.path.join(SAL, "censo.json"), encoding="utf-8"))
    desconocidos = {x.lower() for x in censo["ffmpeg"]["muertos_in"]}

    out = {}
    for k, v in semi.items():
        if v["estado"] != "no_materializable":
            continue
        motor, tok = k.split("|", 1)
        f = cruce[k]
        if k in NO_APLICA:
            cl, ev = NO_APLICA[k]
            out[k] = {"clase": "no_aplica_" + cl, "mueve": True, "evidencia": ev}
        elif motor == "imagemagick" and tok in DUDOSOS_IM:
            out[k] = {"clase": "im_pseudo_operador", "mueve": False,
                      "evidencia": "-list format: Module=%s, modo %s, '%s' -- consume un "
                                   "fichero o una imagen: NO se reclasifica"
                                   % (f["modulo"], f["modo"], f["desc"])}
        elif motor == "imagemagick":
            out[k] = {"clase": "im_formato_real_solo_lectura", "mueve": False,
                      "evidencia": "-list format: Module=%s, modo %s, '%s'"
                                   % (f["modulo"], f["modo"], f["desc"])}
        elif f["en_muxer"]:
            out[k] = {"clase": "ff_declarado_muxer", "mueve": False,
                      "evidencia": "aparece en `ffmpeg -muxers`: el binario declara que SI "
                                   "lo escribe -> el motivo del censo es falso"}
        elif f["en_demuxer"]:
            out[k] = {"clase": "ff_solo_demuxer", "mueve": False,
                      "evidencia": "en `-demuxers` y NO en `-muxers`: ffmpeg lo lee y no lo escribe"}
        elif tok in desconocidos:
            out[k] = {"clase": "ff_desconocido_por_el_binario", "mueve": False,
                      "evidencia": "en censo.json ffmpeg.muertos_in: ningun demuxer, extension "
                                   "ni dispositivo lo reconoce"}
        else:
            out[k] = {"clase": "ff_extension_de_demuxer", "mueve": False,
                      "evidencia": "no es nombre de demuxer/muxer pero NO esta en "
                                   "censo.muertos_in -> por complemento esta en las "
                                   "'Common extensions' de algun demuxer"}
    return out


# ---------------------------------------------------------------- agregacion
def agrega(retirar=frozenset()):
    """Copia literal de _agrega.py, con un conjunto de ORIGENES a retirar."""
    # aristas.json esta podado con su orden; aristas_A.json lo reconstruye sin
    # ejecutar motores (rehace_aristas.py) y reproduce las 138 501 exactas.
    ar = json.load(open(os.path.join(AQUI, "aristas_A.json"), encoding="utf-8"))
    s1 = json.load(open(os.path.join(SAL, "semi_salida.json"), encoding="utf-8"))
    s2 = json.load(open(os.path.join(SAL, "semi_salida2.json"), encoding="utf-8"))
    e1 = json.load(open(os.path.join(SAL, "semi_entrada.json"), encoding="utf-8"))
    e2 = json.load(open(os.path.join(SAL, "semi_entrada2.json"), encoding="utf-8"))
    out = {k: ("viva" if (v["vivo"] or s2.get(k, {}).get("vivo", False)) else "muerta")
           for k, v in s1.items()}
    ent = {}
    for k, v in e1.items():
        if v["estado"] == "no_materializable":
            ent[k] = "indet"
        else:
            fin = e2.get(k, {}).get("estado", v["estado"])
            ent[k] = "viva" if fin == "viva" else "muerta"

    cnt = collections.Counter()
    for reg in ar["A"]:
        ab, ms = reg.split("|")
        a, b = ab.split(">")
        motores = ms.split(",")
        # una arista sale de la POBLACION si TODOS sus motores la declaran desde un
        # origen que no es un fichero para ese motor.
        if motores and all(("%s|%s" % (m, a)) in retirar for m in motores):
            cnt["retirada"] += 1
            continue
        estados = []
        for m in motores:
            if m in ("ffmpeg", "imagemagick"):
                ei = ent.get("%s|%s" % (m, a), "indet")
                so = out.get("%s|%s" % (m, b), "indet")
                if ei == "muerta" or so == "muerta":
                    estados.append("muerta")
                elif ei == "viva" and so == "viva":
                    estados.append("viva")
                else:
                    estados.append("indet")
            else:
                estados.append("otro")
        if "viva" in estados:
            cnt["viva"] += 1
        elif "otro" in estados:
            cnt["otro_motor"] += 1
        elif "indet" in estados:
            cnt["indeterminada"] += 1
        else:
            cnt["muerta"] += 1
    return cnt


if __name__ == "__main__":
    cl = clasifica()
    print("clasificados: %d\n" % len(cl))
    porclase = collections.Counter(v["clase"] for v in cl.values())
    for c, n in porclase.most_common():
        ej = sorted(k.split("|", 1)[1] for k, v in cl.items() if v["clase"] == c)
        print("  %-32s %3d   ejemplos: %s" % (c, n, ", ".join(ej[:4])))
    mueve = {k for k, v in cl.items() if v["mueve"]}
    print("\n  MUEVEN a no_aplica: %d" % len(mueve))

    print("\n--- CONTROL: reproduccion de _agrega.py ---")
    base = agrega()
    tot = sum(base[k] for k in ("viva", "muerta", "indeterminada", "otro_motor"))
    print("  total %d  viva %d  muerta %d  indet %d  otro %d"
          % (tot, base["viva"], base["muerta"], base["indeterminada"], base["otro_motor"]))
    esperado = (138501, 40252, 22235, 75874, 140)
    real = (tot, base["viva"], base["muerta"], base["indeterminada"], base["otro_motor"])
    print("  esperado por aristas-nominales.md: %s" % (esperado,))
    print("  COINCIDE" if real == esperado else "  *** NO COINCIDE: %s ***" % (real,))

    print("\n--- RECUENTO con los origenes que no son ficheros retirados ---")
    nue = agrega(mueve)
    tot2 = sum(nue[k] for k in ("viva", "muerta", "indeterminada", "otro_motor"))
    print("  aristas retiradas de la poblacion: %d" % nue["retirada"])
    print("  poblacion nueva: %d  (antes %d)" % (tot2, tot))
    for k in ("viva", "muerta", "indeterminada", "otro_motor"):
        print("   %-16s %7d -> %7d   %5.2f %% -> %5.2f %%"
              % (k, base[k], nue[k], 100 * base[k] / tot, 100 * nue[k] / tot2))

    json.dump(cl, open(os.path.join(AQUI, "clasificacion.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False, sort_keys=True)
    json.dump({"base": dict(base), "total_base": tot,
               "nuevo": dict(nue), "total_nuevo": tot2,
               "retirados_tokens": sorted(mueve)},
              open(os.path.join(AQUI, "recuento.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)

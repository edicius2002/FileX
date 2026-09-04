# -*- coding: utf-8 -*-
"""C50 / worker10 - El numero corregido del estrato, con su derivacion.

Tres controles ANTES de mover nada (t.58: reproduce la medida ajena antes de tocarla):
  C1  la agregacion original de `_agrega.py`: 138 501 / 40 252 / 22 235 / 75 874 / 140
  C2  el recuento de worker9 (C49):           135 535 / 73 030 indeterminadas
Si cualquiera de los dos falla, no se sigue.

Luego se aplican DOS cambios, y solo dos:
  (a) RETIRAR de la poblacion los 9 dispositivos de Linux confirmados con
      `ffmpeg -devices` DENTRO del contenedor. Misma regla que worker9 uso para
      `lavfi` y `openal`: el origen no es un fichero, asi que la arista no existe.
  (b) MOVER de `indeterminada` a `viva`/`muerta` los 53 tokens materializados y
      leidos. El estado lo decide la columna NOMINAL de `lectura.json`, que es la
      invocacion que ConvertX ejecutaria; la columna del demuxer forzado se publica
      al lado pero no decide.

ESCRIBE unicamente en este directorio.
"""
import os, sys, json, collections

AQUI = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.abspath(os.path.join(AQUI, ".."))
SAL9 = os.path.join(BENCH, "salidas-aristas")
REC9 = os.path.join(BENCH, "salidas-aristas-reclasificacion")

DISPOSITIVOS = ["alsa", "fbdev", "iec61883", "jack", "kmsgrab", "oss", "pulse",
                "video4linux2", "x11grab"]


def agrega(retirar=frozenset(), reestado=None):
    """Copia de `recuento.py::agrega` de worker9 con UN anadido: `reestado`, que
    sobreescribe el estado de una semiarista de ENTRADA. Con los dos argumentos
    vacios tiene que dar las cifras originales; con `retirar` solo, las de worker9."""
    reestado = reestado or {}
    ar = json.load(open(os.path.join(AQUI, "aristas_A.json"), encoding="utf-8"))  # reconstruido por rehace_aristas_copia.py (t.95: podado con su orden)
    s1 = json.load(open(os.path.join(SAL9, "semi_salida.json"), encoding="utf-8"))
    s2 = json.load(open(os.path.join(SAL9, "semi_salida2.json"), encoding="utf-8"))
    e1 = json.load(open(os.path.join(SAL9, "semi_entrada.json"), encoding="utf-8"))
    e2 = json.load(open(os.path.join(SAL9, "semi_entrada2.json"), encoding="utf-8"))
    out = {k: ("viva" if (v["vivo"] or s2.get(k, {}).get("vivo", False)) else "muerta")
           for k, v in s1.items()}
    ent = {}
    for k, v in e1.items():
        if v["estado"] == "no_materializable":
            ent[k] = "indet"
        else:
            fin = e2.get(k, {}).get("estado", v["estado"])
            ent[k] = "viva" if fin == "viva" else "muerta"
    ent.update(reestado)

    cnt = collections.Counter()
    for reg in ar["A"]:
        ab, ms = reg.split("|")
        a, b = ab.split(">")
        motores = ms.split(",")
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


def tot(c):
    return sum(c[k] for k in ("viva", "muerta", "indeterminada", "otro_motor"))


def linea(nom, c):
    t = tot(c)
    print("  %-26s total %6d | viva %5d | muerta %5d | INDET %5d (%5.2f %%) | otro %d | ret %d"
          % (nom, t, c["viva"], c["muerta"], c["indeterminada"],
             100 * c["indeterminada"] / t, c["otro_motor"], c["retirada"]))


if __name__ == "__main__":
    print("--- CONTROL 1: la agregacion original ---")
    base = agrega()
    linea("original", base)
    esperado = (138501, 40252, 22235, 75874, 140)
    real = (tot(base), base["viva"], base["muerta"], base["indeterminada"], base["otro_motor"])
    assert real == esperado, "*** NO reproduce el original: %s ***" % (real,)
    print("  COINCIDE con aristas-nominales.md\n")

    print("--- CONTROL 2: el recuento de worker9 (C49) ---")
    cl = json.load(open(os.path.join(REC9, "clasificacion.json"), encoding="utf-8"))
    mueve9 = {k for k, v in cl.items() if v["mueve"]}
    w9 = agrega(mueve9)
    linea("worker9", w9)
    assert (tot(w9), w9["indeterminada"]) == (135535, 73030), \
        "*** NO reproduce a worker9: %s / %s ***" % (tot(w9), w9["indeterminada"])
    print("  COINCIDE con aristas-reclasificacion.md 5\n")

    # ---------------------------------------------------------- lo mio
    lect = json.load(open(os.path.join(AQUI, "lectura.json"), encoding="utf-8"))["res"]
    reestado = {"ffmpeg|%s" % t: v["estado_grafoA"] for t, v in lect.items()}
    disp = {"ffmpeg|%s" % t for t in DISPOSITIVOS}
    mueve50 = mueve9 | disp

    print("--- C50 paso (a): retirar los 9 dispositivos de Linux ---")
    a = agrega(mueve50)
    linea("worker9 + dispositivos", a)
    print("     dispositivos retirados: %d tokens, %d aristas mas fuera de la poblacion\n"
          % (len(disp), a["retirada"] - w9["retirada"]))

    print("--- C50 paso (b): + los 53 materializados y leidos ---")
    b = agrega(mueve50, reestado)
    linea("C50 completo", b)

    vv = sum(1 for v in lect.values() if v["estado_grafoA"] == "viva")
    print("\n  de los 53: %d vivas, %d muertas (columna nominal)" % (vv, len(lect) - vv))
    print("  el estrato indeterminado pasa de %5.2f %% (original) a %5.2f %% (worker9) a %5.2f %% (C50)"
          % (100 * base["indeterminada"] / tot(base),
             100 * w9["indeterminada"] / tot(w9),
             100 * b["indeterminada"] / tot(b)))
    print("  aristas sacadas del estrato por C50: %d (de las %d que worker9 dejo)"
          % (w9["indeterminada"] - b["indeterminada"], w9["indeterminada"]))

    # control de sensibilidad: si decidiera con el demuxer forzado
    reest_f = {"ffmpeg|%s" % t: ("viva" if v["demuxer_forzado"]["vivo"] else "muerta")
               for t, v in lect.items()}
    c = agrega(mueve50, reest_f)
    print("\n--- control de sensibilidad: si el grafo decidiera con el demuxer FORZADO ---")
    linea("C50 con demuxer forzado", c)
    print("     %d aristas mas vivas: la eleccion de columna vale ese tanto"
          % (c["viva"] - b["viva"]))

    json.dump({"original": dict(base), "worker9": dict(w9),
               "c50_solo_dispositivos": dict(a), "c50": dict(b),
               "c50_si_forzado": dict(c),
               "totales": {"original": tot(base), "worker9": tot(w9),
                           "c50_solo_dispositivos": tot(a), "c50": tot(b),
                           "c50_si_forzado": tot(c)},
               "dispositivos_retirados": sorted(disp),
               "reestado": reestado},
              open(os.path.join(AQUI, "recuento50.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False, sort_keys=True)
    print("\nescrito recuento50.json")

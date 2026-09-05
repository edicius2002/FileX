"""Revalida el arreglo 7 (V5 empareja por TIPO) contra el PATRON ORO.

El carril `cob/fidelidad` dejo el defecto sin arreglar por un motivo de
alcance: *no se puede revalidar contra el patron oro desde un worktree, porque
`bench/salidas-referencia/` solo trae `MANIFIESTO.md` y `referencia.json`*
(trampa 89). Pero `referencia.json` guarda la ruta ABSOLUTA de cada salida, y
la trampa dice como se cierra: **remapear por nombre base**. Eso es lo que hace
esto.

A/B por diferencia, dentro de la MISMA tanda y sobre las MISMAS lecturas de
`ffprobe` (una sola por fichero): se calculan las `perdidas` de V5 con el
emparejamiento VIEJO (por posicion absoluta) y con el NUEVO (por tipo y orden
dentro del tipo), y se publica en cuantas de las 39 parejas
(entrada, salida) del patron oro cambia el veredicto.

Uso:
  python bench/salidas-fix-verificador/revalidar_v5.py [<dir con las salidas>]
"""

import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import verificador as V  # noqa: E402

REF = os.path.join(RAIZ, "bench", "salidas-referencia", "referencia.json")
# V5 no se evalua hacia estos destinos (un solo fotograma o audio crudo).
SIN_V5 = ("wav", "bmp", "png", "jpg", "jpeg")


def _perdidas(te, ts, parejas):
    fuera = []
    for i, x in enumerate(te):
        if not (x["language"] or x["title"]):
            continue
        y = parejas[i]
        for campo in ("language", "title"):
            v = x[campo]
            w = (y or {}).get(campo)
            if v and v != "und" and w != v:
                fuera.append("pista %d %s: %r -> %r" % (i, campo, v, w))
    return fuera


def _viejo(te, ts):
    return [ts[i] if i < len(ts) else None for i in range(len(te))]


def main() -> int:
    ref = json.load(open(REF, encoding="utf-8"))
    # Remapeo por NOMBRE BASE (trampa 89): la ruta absoluta de `referencia.json`
    # apunta al arbol donde se genero, y las binarias no se versionan.
    # `ruta` apunta a `<...>/salidas-referencia/<categoria>/<fichero>`: la raiz
    # que hay que recorrer es DOS niveles arriba, no uno.
    base_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(
        os.path.dirname(ref["salidas"][0]["ruta"]))
    indice = {}
    for raiz, _, ficheros in os.walk(base_dir):
        for f in ficheros:
            indice.setdefault(f, os.path.join(raiz, f))

    filas, faltan = [], []
    for o in ref["ordenes"]:
        nombre = os.path.basename(o["salida"])
        ruta_sal = indice.get(nombre)
        ruta_ent = os.path.join(RAIZ, o["entrada"].replace("/", os.sep))
        if not ruta_sal or not os.path.exists(ruta_ent):
            faltan.append({"id": o["id"], "salida": nombre,
                           "hay_salida": bool(ruta_sal),
                           "hay_entrada": os.path.exists(ruta_ent)})
            continue
        dest = os.path.splitext(nombre)[1].lower().lstrip(".")
        if dest in SIN_V5:
            filas.append({"id": o["id"], "destino": dest,
                          "estado": "V5_no_aplica"})
            continue
        te, ee = V._ffprobe_etiquetas(ruta_ent)
        ts, es = V._ffprobe_etiquetas(ruta_sal)
        if te is None or ts is None:
            filas.append({"id": o["id"], "destino": dest,
                          "estado": "etiquetas_no_legibles",
                          "error": ee or es})
            continue
        con_etiqueta = [x for x in te if x["language"] or x["title"]]
        if not con_etiqueta:
            filas.append({"id": o["id"], "destino": dest,
                          "estado": "la_entrada_no_trae_etiquetas",
                          "n_pistas_ent": len(te), "n_pistas_sal": len(ts),
                          "tipos_ent": [x["tipo"] for x in te],
                          "tipos_sal": [x["tipo"] for x in ts]})
            continue
        pv = _perdidas(te, ts, _viejo(te, ts))
        pn = _perdidas(te, ts, V._emparejar_por_tipo(te, ts))
        filas.append({
            "id": o["id"], "destino": dest, "estado": "evaluada",
            "tipos_ent": [x["tipo"] for x in te],
            "tipos_sal": [x["tipo"] for x in ts],
            "veredicto_viejo": "aviso" if pv else "informativo",
            "veredicto_nuevo": "aviso" if pn else "informativo",
            "perdidas_viejo": pv, "perdidas_nuevo": pn,
            "cambia": bool(pv) != bool(pn),
        })

    evaluadas = [f for f in filas if f["estado"] == "evaluada"]
    resumen = {
        "n_ordenes": len(ref["ordenes"]),
        "n_filas": len(filas),
        "faltan": faltan,
        "n_evaluadas": len(evaluadas),
        "n_v5_no_aplica": sum(f["estado"] == "V5_no_aplica" for f in filas),
        "n_sin_etiquetas_en_la_entrada":
            sum(f["estado"] == "la_entrada_no_trae_etiquetas" for f in filas),
        "n_no_legibles":
            sum(f["estado"] == "etiquetas_no_legibles" for f in filas),
        "n_cambian": sum(f["cambia"] for f in evaluadas),
        "cambian": [f["id"] for f in evaluadas if f["cambia"]],
        # Un resultado nulo necesita saber POR QUE es nulo (trampa 56): que la
        # lista de tipos difiera no es reordenar, es que la salida tiene otras
        # pistas. Reordenar de verdad es MISMO multiconjunto y DISTINTO orden.
        "n_tipos_distintos": sum(f["tipos_ent"] != f["tipos_sal"]
                                 for f in evaluadas),
        "n_reordenadas_de_verdad": sum(
            f["tipos_ent"] != f["tipos_sal"]
            and sorted(f["tipos_ent"]) == sorted(f["tipos_sal"])
            for f in evaluadas),
        "filas": filas,
    }
    destino = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "revalidar_v5.json")
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(resumen, f, indent=2, ensure_ascii=False)
    for k in ("n_ordenes", "n_filas", "n_evaluadas", "n_v5_no_aplica",
              "n_sin_etiquetas_en_la_entrada", "n_no_legibles", "n_cambian",
              "cambian", "n_tipos_distintos", "n_reordenadas_de_verdad"):
        print("%-32s %s" % (k, resumen[k]))
    print("faltan: %d %s" % (len(faltan), [f["salida"] for f in faltan][:6]))
    print("escrito:", destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

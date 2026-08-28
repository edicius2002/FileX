# -*- coding: utf-8 -*-
"""C30 / paso 4 - ANTES contra DESPUES, celda a celda, sobre los mismos destinos.

Los cuatro falsos positivos de la primera tanda estan arreglados en
`filex/verificador.py`. Comprobar que ahora salen 0 es la mitad facil; la mitad
que importa es que la correccion **no haya apagado una deteccion buena**
(CLAUDE.md trampa 65: cuando una prueba que documenta un fallo antiguo se pone
verde sola, la pregunta no es «bien» sino «que la esta tapando»).

Por eso la comparacion es por CELDA y en las dos direcciones:
  - fallos que desaparecen  -> los cuatro arreglos, uno a uno;
  - fallos que se pierden   -> REGRESION, si el que desaparece era legitimo;
  - fallos NUEVOS y G6 que desaparecen -> REGRESION en cualquier caso.

Las dos tandas escriben ficheros DISTINTOS (los motores no son deterministas:
`/CreationDate`, trampa 22), asi que lo comparable es el veredicto por celda,
no el byte. Las semillas y los 288 destinos son los mismos.

Uso:  python bench/salidas-firmas-cierre/_c30_compara.py
"""
import json
import os
from collections import Counter

DEST = os.path.dirname(os.path.abspath(__file__))


def carga(nom):
    with open(os.path.join(DEST, nom), encoding="utf-8") as fh:
        return json.load(fh)


def indice(d):
    return {(f["motor"], f["destino"], f["semilla"]): f
            for f in d["filas"] if f.get("estado") == "escrito"}


def main():
    a, b = carga("c30_contenedor.json"), carga("c30_contenedor_v2.json")
    ia, ib = indice(a), indice(b)
    print("sha256 antes  :", a["resumen"]["sha256_verificador"])
    print("sha256 despues:", b["resumen"]["sha256_verificador"])
    print("celdas escritas: %d -> %d   destinos: %d -> %d"
          % (len(ia), len(ib), a["resumen"]["destinos_escritos"],
             b["resumen"]["destinos_escritos"]))

    comunes = sorted(set(ia) & set(ib))
    print("celdas comparables:", len(comunes),
          "| solo antes:", len(set(ia) - set(ib)),
          "| solo despues:", len(set(ib) - set(ia)))

    fallo_se_va, fallo_nuevo, g6_se_va, g6_nuevo, p1_cambia = [], [], [], [], []
    for k in comunes:
        x, y = ia[k], ib[k]
        if x["fallo"] and not y["fallo"]:
            fallo_se_va.append((k, x["firma_real"], y["firma_real"]))
        if y["fallo"] and not x["fallo"]:
            fallo_nuevo.append((k, x["firma_real"], y["firma_real"]))
        if x["g6"] and not y["g6"]:
            g6_se_va.append(k)
        if y["g6"] and not x["g6"]:
            g6_nuevo.append(k)
        if x["punto1_estado"] != y["punto1_estado"]:
            p1_cambia.append((k, x["punto1_estado"], y["punto1_estado"]))

    def porcaso(lista, n=3):
        c = Counter((k[0], k[1]) for k, *_ in lista) if lista and \
            isinstance(lista[0], tuple) and isinstance(lista[0][0], tuple) else \
            Counter((k[0], k[1]) for k in lista)
        return sorted(c.items())

    print("\n--- FALLOS QUE DESAPARECEN (los arreglos) ---")
    for par, n in porcaso(fallo_se_va):
        firmas = {(x, y) for k, x, y in fallo_se_va if (k[0], k[1]) == par}
        print("  %-16s %-12s %d celdas   firma antes->despues: %s"
              % (par[0], par[1], n, sorted(firmas)))
    print("\n--- FALLOS NUEVOS (serian regresion) ---")
    print("  ninguno" if not fallo_nuevo else porcaso(fallo_nuevo))
    print("\n--- G6 QUE DESAPARECEN (serian regresion) ---")
    print("  ninguno" if not g6_se_va else porcaso(g6_se_va))
    print("--- G6 NUEVOS ---")
    print("  ninguno" if not g6_nuevo else porcaso(g6_nuevo))
    print("  G6 total: %d -> %d celdas, %d -> %d destinos"
          % (a["resumen"]["n_g6"], b["resumen"]["n_g6"],
             a["resumen"]["n_g6_destinos"], b["resumen"]["n_g6_destinos"]))

    print("\n--- FALLOS QUE SIGUEN (tienen que seguir: son capturas legitimas) ---")
    siguen = Counter((k[0], k[1]) for k in comunes if ia[k]["fallo"] and ib[k]["fallo"])
    for par, n in sorted(siguen.items()):
        print("  %-16s %-12s %d celdas" % (par[0], par[1], n))

    print("\n--- COBERTURA POR DESTINO ---")
    ca, cb = a["resumen"]["cobertura_por_destino"], b["resumen"]["cobertura_por_destino"]
    for e in ("evaluado", "familia", "no_aplica", "sin_vocabulario"):
        print("  %-16s %3d -> %3d  (%+d)" % (e, ca.get(e, 0), cb.get(e, 0),
                                             cb.get(e, 0) - ca.get(e, 0)))
    print("  cambios de estado por celda:", len(p1_cambia),
          dict(Counter((x, y) for _, x, y in p1_cambia)))

    resto = sorted({"%s:%s" % (k[0], k[1]) for k in ib
                    if ib[k]["punto1_estado"] == "sin_vocabulario"})
    print("\n--- SIGUEN EN sin_vocabulario (%d destinos) ---" % len(resto))
    print("  " + " ".join(resto))


if __name__ == "__main__":
    main()

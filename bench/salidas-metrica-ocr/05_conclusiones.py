# -*- coding: utf-8 -*-
"""A7 / paso 5 — ¿cambia la CONCLUSION, no solo el numero?

Una conclusion de este repositorio casi siempre tiene la forma "sobre el mismo
documento, la configuracion A es mejor que la B" o "el optimo de este eje esta
en X". Eso NO depende del valor absoluto del CER: depende del ORDEN. Reescribir
una cifra es barato; retractar un hallazgo no.

Como se mecaniza
----------------
Los nombres de fichero de las tandas son `tok__tok__...__tok.txt` y cada `tok`
es un factor del experimento (motor, k, ppp, psm, pHYs, documento). Para cada
posicion de token que NO es el documento se forma una FAMILIA: todos los demas
tokens fijos, ese variando. Dentro de cada familia se compara el orden bajo la
metrica ciega y bajo cada acentuada.

Se separan tres cosas que no son lo mismo:
  * INVERSION ESTRICTA  A<B con la ciega y A>B con la acentuada. Esto SI
                        retracta un hallazgo.
  * EMPATE ROTO         A==B con la ciega y A!=B con la acentuada. Esto NO
                        retracta nada: es resolucion que antes no habia.
  * EMPATE CREADO       A!=B con la ciega y A==B con la acentuada.
Y aparte, si cambia el ARGMIN de la familia (la configuracion ganadora).

Umbral de empate: 1e-9 sobre el CER en porcentaje. Los tres evaluadores son
deterministas sobre texto ya escrito, asi que no hay ruido que absorber.
"""
import io
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
EPS = 1e-9


def familias(filas):
    """(clave_familia, eje) -> lista de celdas comparables."""
    fam = {}
    for f in filas:
        base = f["fichero"][:-4] if f["fichero"].endswith(".txt") else f["fichero"]
        toks = base.split("__")
        # posicion del token que contiene el documento
        ipos = [i for i, t in enumerate(toks) if f["doc"] in t.lower()]
        if not ipos:
            continue
        idoc = ipos[-1]
        for p in range(len(toks)):
            if p == idoc:
                continue
            patron = list(toks)
            patron[p] = "*"
            clave = (f["informe"], f["doc"], p, "__".join(patron))
            fam.setdefault(clave, []).append((toks[p], f))
    return fam


def compara(cel, campo_a, campo_b):
    """Devuelve (inversiones, empates_rotos, empates_creados, pares)."""
    inv = roto = creado = pares = 0
    n = len(cel)
    for i in range(n):
        for j in range(i + 1, n):
            a1 = cel[i][1][campo_a] - cel[j][1][campo_a]
            a2 = cel[i][1][campo_b] - cel[j][1][campo_b]
            pares += 1
            e1 = abs(a1) < EPS
            e2 = abs(a2) < EPS
            if e1 and not e2:
                roto += 1
            elif e2 and not e1:
                creado += 1
            elif not e1 and not e2 and (a1 > 0) != (a2 > 0):
                inv += 1
    return inv, roto, creado, pares


def argmin_cambia(cel, campo_a, campo_b):
    """True si el conjunto de ganadores (argmin, con empates) cambia."""
    m1 = min(c[1][campo_a] for c in cel)
    m2 = min(c[1][campo_b] for c in cel)
    g1 = {c[0] for c in cel if abs(c[1][campo_a] - m1) < EPS}
    g2 = {c[0] for c in cel if abs(c[1][campo_b] - m2) < EPS}
    return g1 != g2, sorted(g1), sorted(g2)


def main():
    r = json.load(io.open(os.path.join(AQUI, "recalculo.json"), encoding="utf-8"))
    filas = [f for f in r["filas"] if "cer_ciego" in f]
    fam = familias(filas)
    fam = {k: v for k, v in fam.items() if len(v) >= 2}
    print("familias comparables (>=2 celdas, un solo factor variando): %d" % len(fam))
    print("celdas implicadas: %d\n" % sum(len(v) for v in fam.values()))

    for etiqueta, campo in (("acentuada d4 (M2)", "cer_d4ac"),
                            ("acentuada tildes (M3)", "cer_tildes")):
        tot = {"inv": 0, "roto": 0, "creado": 0, "pares": 0,
               "fam_inv": 0, "fam_argmin": 0}
        por_inf = {}
        detalles = []
        for k, cel in fam.items():
            inv, roto, creado, pares = compara(cel, "cer_ciego", campo)
            cam, g1, g2 = argmin_cambia(cel, "cer_ciego", campo)
            tot["inv"] += inv
            tot["roto"] += roto
            tot["creado"] += creado
            tot["pares"] += pares
            if inv:
                tot["fam_inv"] += 1
            if cam:
                tot["fam_argmin"] += 1
            d = por_inf.setdefault(k[0], {"fam": 0, "inv": 0, "pares": 0,
                                          "argmin": 0, "roto": 0})
            d["fam"] += 1
            d["inv"] += inv
            d["pares"] += pares
            d["roto"] += roto
            if cam:
                d["argmin"] += 1
            if inv or cam:
                detalles.append({"informe": k[0], "doc": k[1], "eje_pos": k[2],
                                 "patron": k[3], "n": len(cel),
                                 "inversiones": inv, "argmin_cambia": cam,
                                 "ganador_ciega": g1, "ganador_acentuada": g2})
        print("### %s frente a la ciega" % etiqueta)
        print("  pares comparados          : %d" % tot["pares"])
        print("  INVERSIONES ESTRICTAS     : %d  (%.3f %%)" %
              (tot["inv"], 100.0 * tot["inv"] / max(1, tot["pares"])))
        print("  empates ROTOS (gana res.) : %d  (%.2f %%)" %
              (tot["roto"], 100.0 * tot["roto"] / max(1, tot["pares"])))
        print("  empates CREADOS           : %d" % tot["creado"])
        print("  familias con inversion    : %d de %d" % (tot["fam_inv"], len(fam)))
        print("  familias con OTRO ganador : %d de %d" % (tot["fam_argmin"], len(fam)))
        print("  %-26s %5s %7s %8s %8s" % ("por informe", "fams", "invers", "argmin", "pares"))
        for inf in sorted(por_inf):
            d = por_inf[inf]
            print("  %-26s %5d %7d %8d %8d" %
                  (inf, d["fam"], d["inv"], d["argmin"], d["pares"]))
        print()
        json.dump({"total": tot, "por_informe": por_inf, "detalles": detalles},
                  io.open(os.path.join(AQUI, "conclusiones_%s.json" %
                                       campo.replace("cer_", "")), "w",
                          encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.exit(main())

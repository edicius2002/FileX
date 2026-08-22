# -*- coding: utf-8 -*-
"""F1 / paso 5b - LA CIFRA DEL INFORME, y el riesgo que la acompana.

Lee remuestra.json y responde a las dos preguntas:
  (1) de que porcentaje a que porcentaje sube la fraccion de destinos reales con el
      punto 1 EVALUABLE;
  (2) cuantas aristas que E1 conto como REALES pasan ahora a DESTRUIDO por el punto
      1 — es decir, cuantos falsos positivos arriesga el vocabulario nuevo, y
      cuales de ellos son de verdad el motor escribiendo otro formato.

Uso: python _analiza_remuestra.py
Escribe resumen_remuestra.json
"""
import os, json, sys
from collections import Counter, defaultdict

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-firmas")


def bloque(d, etiqueta):
    con = [r for r in d if r.get("firma_nueva") is not None]
    n, m = len(d), len(con)
    if not n:
        return {}
    ev_e1 = sum(1 for r in d if r.get("e1_n2_evaluable"))
    ev_viejo = sum(1 for r in con if r.get("n2_evaluable_viejo"))
    est = Counter(r.get("punto1_nuevo") for r in con)
    ev_nuevo = est["evaluado"] + est["familia"]
    print("\n--- %s (n=%d, con fichero %d) ---" % (etiqueta, n, m))
    print("   E1 publicado            : %3d = %5.1f %%" % (ev_e1, 100 * ev_e1 / n))
    print("   viejo, reejecutado      : %3d = %5.1f %%" % (ev_viejo, 100 * ev_viejo / n))
    print("   NUEVO                   : %3d = %5.1f %%   (formato %d + familia %d)"
          % (ev_nuevo, 100 * ev_nuevo / n, est["evaluado"], est["familia"]))
    print("   NO APLICA               : %3d = %5.1f %%" % (est["no_aplica"], 100 * est["no_aplica"] / n))
    print("   deuda restante          : %3d = %5.1f %%" % (est["sin_vocabulario"],
                                                           100 * est["sin_vocabulario"] / n))
    print("   sin fichero (N1)        : %3d = %5.1f %%" % (n - m, 100 * (n - m) / n))
    return {"n": n, "con_fichero": m, "ev_e1": ev_e1, "ev_viejo": ev_viejo,
            "ev_nuevo": ev_nuevo, "estado": dict(est)}


def main():
    d = json.load(open(os.path.join(SAL, "remuestra.json"), encoding="utf-8"))["filas"]
    con = [r for r in d if r.get("firma_nueva") is not None]
    print("=== POR ESTRATO, COMO LO PUBLICO E1 ===")
    por = {}
    for etq in ("general", "pdf"):
        sub = [r for r in d if r.get("estrato") == etq]
        if sub:
            por[etq] = bloque(sub, "estrato " + etq)
    por["union"] = bloque(d, "union")
    print("filas reejecutadas      : %d" % len(d))
    print("con fichero (rc=0, >0 B): %d" % len(con))
    sin_sem = [r for r in d if r.get("estado") == "sin_semilla"]
    print("sin semilla de entrada  : %d" % len(sin_sem))

    n = len(d)
    ev_viejo = sum(1 for r in con if r.get("n2_evaluable_viejo"))
    ev_e1 = sum(1 for r in d if r.get("e1_n2_evaluable"))
    est = Counter(r.get("punto1_nuevo") for r in con)
    ev_nuevo = est["evaluado"] + est["familia"]
    print("\n=== PUNTO 1 SOBRE LA MISMA MUESTRA (denominador = las %d filas) ===" % n)
    print("  E1, tal y como lo publico       : %d  = %.1f %%" % (ev_e1, 100 * ev_e1 / n))
    print("  vocabulario VIEJO, reejecutado  : %d  = %.1f %%" % (ev_viejo, 100 * ev_viejo / n))
    print("  vocabulario NUEVO               : %d  = %.1f %%" % (ev_nuevo, 100 * ev_nuevo / n))
    print("     de ellos a nivel de FORMATO  : %d  = %.1f %%" % (est["evaluado"], 100 * est["evaluado"] / n))
    print("     de ellos a nivel de FAMILIA  : %d  = %.1f %%" % (est["familia"], 100 * est["familia"] / n))
    print("  NO APLICA (formato sin marcador): %d  = %.1f %%" % (est["no_aplica"], 100 * est["no_aplica"] / n))
    print("  sigue sin vocabulario (DEUDA)   : %d  = %.1f %%" % (est["sin_vocabulario"],
                                                                 100 * est["sin_vocabulario"] / n))
    print("  sin fichero que juzgar (N1)     : %d  = %.1f %%" % (n - len(con), 100 * (n - len(con)) / n))

    m = len(con)
    print("\n=== SOBRE LAS %d QUE SI PRODUJERON FICHERO ===" % m)
    print("  viejo  : %.1f %%   nuevo: %.1f %% (formato %.1f %% + familia %.1f %%)"
          % (100 * ev_viejo / m, 100 * ev_nuevo / m,
             100 * est["evaluado"] / m, 100 * est["familia"] / m))
    print("  no aplica: %.1f %%   deuda restante: %.1f %%"
          % (100 * est["no_aplica"] / m, 100 * est["sin_vocabulario"] / m))

    # --- EL REPARTO DEL 88 %: de lo que E1 no pudo evaluar, cuanto era deuda
    #     nuestra y cuanto es propiedad de los formatos.
    no_ev = [r for r in d if not r.get("e1_n2_evaluable")]
    rep = Counter()
    for r in no_ev:
        if r.get("firma_nueva") is None:
            rep["A_sin_fichero_que_juzgar"] += 1
        else:
            rep[{"evaluado": "B_era_deuda_nuestra_CERRADA",
                 "familia": "B_era_deuda_nuestra_CERRADA",
                 "no_aplica": "C_propiedad_del_formato",
                 "sin_vocabulario": "D_sigue_siendo_deuda"}[r["punto1_nuevo"]]] += 1
    print("\n=== EL REPARTO DEL 88 %% DE E1 (los %d destinos que no pudo evaluar) ===" % len(no_ev))
    for k, v in sorted(rep.items()):
        print("   %-34s %4d = %5.1f %%" % (k, v, 100 * v / len(no_ev)))
    conf = [r for r in no_ev if r.get("firma_nueva") is not None]
    if conf:
        rep2 = Counter(r["punto1_nuevo"] for r in conf)
        print("   -- solo sobre las %d que SI produjeron fichero:" % len(conf))
        for k, v in sorted(rep2.items()):
            print("      %-31s %4d = %5.1f %%" % (k, v, 100 * v / len(conf)))

    # --- el riesgo: aristas que E1 conto como REALES y que el punto 1 nuevo tumba
    nuevos_fallo = [r for r in con if r.get("punto1_fallo")]
    viejos_fallo = [r for r in con if r.get("n2_destruido_viejo")]
    sospechosos = [r for r in nuevos_fallo if r.get("e1_nominal") is False]
    print("\n=== EL RIESGO ===")
    print("  N2 disparaba con el vocabulario viejo : %d" % len(viejos_fallo))
    print("  el punto 1 nuevo dispara              : %d" % len(nuevos_fallo))
    print("  ...de ellas, E1 las conto como REALES : %d   <- hay que revisarlas una a una"
          % len(sospechosos))
    por_dest = Counter((r["b"], r["firma_nueva"]) for r in sospechosos)
    print("\n  (destino, firma real obtenida) -> n:")
    for (b, f), k in por_dest.most_common(60):
        print("     %-14s %-14s %d" % (b, f, k))

    # firmas que siguen sin reconocerse
    desc = Counter(r["b"] for r in con if r.get("firma_nueva") in ("desconocido", "riff"))
    print("\n  destinos cuya salida sigue sin firma reconocida (%d filas): %s"
          % (sum(desc.values()), dict(desc.most_common(40))))
    frm = Counter(r["firma_nueva"] for r in con)
    print("\n  firmas observadas ahora (%d distintas):" % len(frm))
    for k, v in frm.most_common():
        print("     %-14s %d" % (k, v))

    res = {"por_estrato": por, "reparto_88": dict(rep),
           "n": n, "con_fichero": m, "ev_e1": ev_e1, "ev_viejo": ev_viejo,
           "ev_nuevo": ev_nuevo, "estado": dict(est),
           "n2_viejo_fallo": len(viejos_fallo), "p1_nuevo_fallo": len(nuevos_fallo),
           "sospechosos": [{k: r.get(k) for k in
                            ("a", "b", "motor", "firma_vieja", "firma_nueva",
                             "aceptables", "e1_categoria", "e1_firma", "punto1_msg")}
                           for r in sospechosos],
           "firmas": dict(frm)}
    json.dump(res, open(os.path.join(SAL, "resumen_remuestra.json"), "w",
                        encoding="utf-8"), indent=1, ensure_ascii=False)
    print("\nescrito resumen_remuestra.json")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""P2 - desglose por estrato y recuento de invocaciones, para el informe."""
import os, json
from collections import Counter

SAL = os.path.dirname(os.path.abspath(__file__))
FP = {("ogg", "im24"), ("wtv", "im1"), ("tta", "h265.mp4"), ("266", "y")}
DIS = {("png", "ico")}


def j(n):
    return json.load(open(os.path.join(SAL, n), encoding="utf-8"))


if __name__ == "__main__":
    a, b = j("resid_p2.json"), j("resid_p2b.json")
    viv = ({(r["a"], r["b"]) for r in a if r.get("p2_estado") == "viva"} |
           {(r["a"], r["b"]) for r in b if r.get("p2b_estado") == "viva"}) - FP - DIS
    c, tot = Counter(), Counter()
    for r in a:
        tot[r.get("estrato")] += 1
        if (r["a"], r["b"]) in viv:
            c[r.get("estrato")] += 1
    print("ESTRATO                      nominales(E1)  recuperadas     %")
    for k in sorted(tot):
        print("  %-26s %6d %11d %8.1f" % (k, tot[k], c[k], 100 * c[k] / tot[k]))
    print("  %-26s %6d %11d %8.1f" % ("TOTAL", sum(tot.values()), sum(c.values()),
                                      100 * sum(c.values()) / sum(tot.values())))

    cz = Counter()
    for r in b:
        if r.get("p2b_estado") == "muerta":
            s = r.get("p2b_causa") or ""
            k = ("muxer sin pista compatible" if s.startswith("el muxer") else
                 "codificador ausente del build" if "ausente" in s else
                 "sin paquetes tras barrer parametros" if "no packets" in s else
                 "TIMEOUT" if "TIMEOUT" in s else "otra")
            cz[k] += 1
    print("\nCAUSA de las que no reviven:", dict(cz))

    n = 0
    for f in ("semi_in_p2.json", "semi_in_p2b.json", "semi_out_p2.json", "semi_out_p2b.json"):
        for v in j(f).values():
            n += len(v.get("intentos", [])) + 1
    n2 = len(a) * 2 + sum(r.get("p2b_n_variantes", 1) for r in b)
    n3 = len(j("c17.json")) + len(j("c17b.json"))
    n4 = sum(len(v.get("intentos", [])) + 1 for v in j("crudos_p2.json").values())
    print("\nINVOCACIONES: semiaristas %d, residuo %d, crudos %d, C17 %d  -> TOTAL %d"
          % (n, n2, n4, n3, n + n2 + n3 + n4))

    # salidas revividas: veredicto
    print("\nVEREDICTO de las revividas del residuo:")
    ver = Counter()
    for r in a:
        if (r["a"], r["b"]) in viv:
            ver[r["p2"]["veredicto"]] += 1
    for r in b:
        if (r["a"], r["b"]) in viv and r.get("p2b_estado") == "viva":
            ver[r["p2b"]["veredicto"]] += 1
    print(" ", dict(ver))

    # fuera del destino
    fu = 0
    for r in a:
        if r.get("p2", {}).get("fuera_del_destino"):
            fu += 1
    print("\naristas cuyo motor escribio FUERA del destino (5o punto):", fu)

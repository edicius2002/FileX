# -*- coding: utf-8 -*-
"""P2 - resumen consolidado para el informe. No mide nada: agrega los .json."""
import os, json, math
from collections import Counter

SAL = os.path.dirname(os.path.abspath(__file__))


def j(n):
    p = os.path.join(SAL, n)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(100 * max(0, c - h), 1), round(100 * min(1, c + h), 1))


if __name__ == "__main__":
    R = {}
    # --- semiaristas de entrada
    a, b, cr = j("semi_in_p2.json"), j("semi_in_p2b.json"), j("crudos_p2.json")
    ideal = j("crudos_ideal.json") or {}
    estado = {}
    for k, v in a.items():
        estado[k] = v.get("estado")
    for k, v in (b or {}).items():
        if v.get("estado") == "viva":
            estado[k] = "viva"
    for k, v in (cr or {}).items():
        if v.get("estado") == "viva":
            estado[k] = "viva"
    # el veredicto FINO de los crudos manda sobre el grueso
    for f, d in ideal.items():
        k = "imagemagick|" + f
        if d.get("veredicto") == "DESTRUIDO":
            estado[k] = "muerta"
    ent_vivas = [k for k, v in estado.items() if v == "viva"]
    R["semi_entrada"] = {"muertas_E1": len(a), "revividas": len(ent_vivas),
                         "lista": sorted(ent_vivas),
                         "ic95": wilson(len(ent_vivas), len(a))}
    # --- semiaristas de salida
    so = j("semi_out_p2.json")
    sob = j("semi_out_p2b.json")
    sal_v = sorted(k for k, v in (sob or {}).items() if v.get("estado") == "viva")
    causas = Counter(v.get("causa", "")[:40] for v in (sob or {}).values()
                     if v.get("estado") != "viva")
    R["semi_salida"] = {"muertas_E1": len(so), "revividas": len(sal_v),
                        "lista": sal_v, "causas_restantes": dict(causas),
                        "ic95": wilson(len(sal_v), len(so))}
    # --- crudos
    tabla = []
    for k, v in sorted((cr or {}).items()):
        f = k.split("|")[1]
        m = v.get("mejor") or {}
        tabla.append({"motor": k.split("|")[0], "formato": f,
                      "bytes_por_pixel": v.get("bytes_por_pixel"),
                      "bits_por_canal": v.get("bits_por_canal_medidos"),
                      "variante": m.get("variante"), "rmse_color": m.get("rmse"),
                      "rmse_vs_ideal": (ideal.get(f) or {}).get("rmse_vs_ideal"),
                      "veredicto": (ideal.get(f) or {}).get("veredicto") or v.get("veredicto"),
                      "estado": v.get("estado")})
    R["crudos"] = tabla
    # --- residuo
    R["residuo"] = (j("final_p2.json") or {}).get("residuo")
    R["final"] = j("final_p2.json")
    # --- C17
    c17 = (j("c17.json") or []) + (j("c17b.json") or [])
    por = {}
    for r in c17:
        if "nominal" not in r:
            continue
        m = r["motor"]
        clave = (m, r["a"], r["b"])
        # la 2a vuelta manda sobre la 1a
        por[clave] = r
    ev = list(por.values())
    res17 = {}
    for m in ("ghostscript", "gotenberg-chromium", "gotenberg-lo"):
        s = [r for r in ev if r["motor"] == m]
        k = sum(1 for r in s if r["nominal"])
        res17[m] = {"evaluadas": len(s), "nominales": k,
                    "tasa": round(100 * k / max(1, len(s)), 1),
                    "ic95": wilson(k, len(s)),
                    "cuales": [(r["a"], r["b"], r.get("err", "")[:80])
                               for r in s if r["nominal"]]}
    tot_ev = len(ev)
    tot_k = sum(1 for r in ev if r["nominal"])
    res17["TOTAL"] = {"evaluadas": tot_ev, "nominales": tot_k,
                      "tasa": round(100 * tot_k / max(1, tot_ev), 1),
                      "ic95": wilson(tot_k, tot_ev),
                      "poblacion_gs_gotenberg": 136,
                      "no_materializables": 136 - tot_ev}
    R["C17"] = res17
    # --- validacion
    val = j("validacion_p2.json") or []
    R["validacion"] = dict(Counter(v["veredicto"] for v in val))
    json.dump(R, open(os.path.join(SAL, "resumen_p2.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in R.items() if k != "crudos"},
                     ensure_ascii=False, indent=1)[:6000])
    print("\nCRUDOS")
    for t in R["crudos"]:
        print("  %-12s %-8s bpp=%-7s bits=%-6s %-14s rmse=%-9s ideal=%-9s %s" %
              (t["motor"], t["formato"], t["bytes_por_pixel"], t["bits_por_canal"],
               t["variante"], t["rmse_color"], t["rmse_vs_ideal"], t["veredicto"]))

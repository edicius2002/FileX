# -*- coding: utf-8 -*-
"""G2 / B17-B18-B14 — tablas y descomposicion de varianza a partir de los json.

No mide nada: solo lee `json/*__cer.json` y produce `tablas.md` + `json/resumen.json`.

La descomposicion de varianza usa el MISMO metodo que `bench/salidas-k-motor/tablas_km.py`
aplico al `k` (medias por fila, medias por columna, residuo), para que las dos cifras
sean comparables. Aqui se aplica DOS veces:
  * sobre `log2(k*)`, como hizo M1 (¿el optimo es del motor o del par?)
  * sobre el CER de la rejilla `--psm` x `k`, que es la pregunta nueva:
    ¿son SEPARABLES `--psm` y `k`, o interactuan?

uso: python tablas_psm.py
"""
import glob
import io
import json
import math
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
JSN = os.path.join(BASE, "json")

RE_CLAVE = re.compile(r"^(?P<var>[a-z0-9_]+)__k(?P<k>\d{4})__(?P<doc>[a-z0-9_]+)__psm(?P<psm>\d{2})$")


def cargar():
    filas = []
    for f in sorted(glob.glob(os.path.join(JSN, "*__cer.json"))):
        d = json.load(open(f, encoding="utf-8"))
        etq = d["cabecera"]["etiqueta"]
        dpi = d["cabecera"].get("user_defined_dpi")
        for clave, v in d["res"].items():
            if "error" in v:
                continue
            m = RE_CLAVE.match(clave)
            if not m:
                continue
            filas.append(dict(
                tanda=etq, dpi_declarado=dpi, variante=m["var"],
                k=int(m["k"]) / 1000.0, doc=m["doc"], psm=int(m["psm"]),
                cer=v["cer_acentos_pct"], cer_ascii=v["cer_ascii_pct"],
                bytes=v["bytes_salida"], ms=v["ms_mediana"], n=v["n"],
                det=v["determinista"], lineas=v["lineas_exactas"],
                lineas_tot=v["lineas_totales"], bloques=v.get("bloques", {}),
                clave=clave))
    return filas


def anova2(celdas, ejeA, ejeB, val):
    """Descomposicion de varianza a dos ejes por medias marginales (el metodo de M1).
    celdas: lista de dicts. Devuelve SS y % por fuente. Rejilla completa requerida."""
    A = sorted({c[ejeA] for c in celdas})
    B = sorted({c[ejeB] for c in celdas})
    tab = {(c[ejeA], c[ejeB]): val(c) for c in celdas}
    if len(tab) != len(A) * len(B):
        return {"error": f"rejilla incompleta: {len(tab)} de {len(A) * len(B)}"}
    gran = sum(tab.values()) / len(tab)
    mA = {a: sum(tab[(a, b)] for b in B) / len(B) for a in A}
    mB = {b: sum(tab[(a, b)] for a in A) / len(A) for b in B}
    ssA = len(B) * sum((mA[a] - gran) ** 2 for a in A)
    ssB = len(A) * sum((mB[b] - gran) ** 2 for b in B)
    ssI = sum((tab[(a, b)] - mA[a] - mB[b] + gran) ** 2 for a in A for b in B)
    tot = ssA + ssB + ssI
    p = (lambda x: round(100 * x / tot, 1) if tot else None)
    return {"n_A": len(A), "n_B": len(B), "ejeA": ejeA, "ejeB": ejeB,
            "ss_A": round(ssA, 4), "ss_B": round(ssB, 4), "ss_inter": round(ssI, 4),
            "ss_total": round(tot, 4),
            "pct_A": p(ssA), "pct_B": p(ssB), "pct_inter": p(ssI)}


def argmins(celdas, eje, val):
    """Todos los valores de `eje` que empatan en el minimo."""
    mejor = min(val(c) for c in celdas)
    return sorted({c[eje] for c in celdas if abs(val(c) - mejor) < 1e-9}), mejor


def regret(celdas, ejeFijo, ejeVar, val):
    """regret(v) = media sobre ejeFijo de [ val(v) - min_v' val(v') ]."""
    grupos = {}
    for c in celdas:
        grupos.setdefault(c[ejeFijo], []).append(c)
    vals = sorted({c[ejeVar] for c in celdas})
    out = {}
    for v in vals:
        acc, n = 0.0, 0
        for g, cs in grupos.items():
            mn = min(val(x) for x in cs)
            hit = [x for x in cs if x[ejeVar] == v]
            if not hit:
                continue
            acc += min(val(x) for x in hit) - mn
            n += 1
        out[v] = round(acc / n, 3) if n else None
    return out


def md_tabla(cab, filas):
    s = "| " + " | ".join(cab) + " |\n"
    s += "|" + "|".join("---" for _ in cab) + "|\n"
    for f in filas:
        s += "| " + " | ".join(str(x) for x in f) + " |\n"
    return s


if __name__ == "__main__":
    filas = cargar()
    res = {"celdas": len(filas),
           "deterministas": sum(1 for f in filas if f["det"]),
           "tandas": sorted({f["tanda"] for f in filas})}
    out = ["# Tablas de G2 — `--psm`, rasterizador y ppp de Tesseract",
           "",
           f"**{len(filas)} celdas**, {res['deterministas']} deterministas. "
           f"Evaluador `ocr_eval_d4.py` (acentuado). CER en la lectura **acentos**; "
           f"la lectura `ascii` va en `json/resumen.json`.", ""]

    # ---------------- §1 barrido de psm a k=1.00 -------------------------------
    A = [f for f in filas if f["tanda"] == "A_psm_barrido"]
    if A:
        docs = sorted({f["doc"] for f in A})
        psms = sorted({f["psm"] for f in A})
        out += ["## 1. Barrido de los 12 `--psm` a k=1,00 (raster `im`, sin resolucion declarada)", ""]
        tab = []
        for p in psms:
            fila = [f"psm {p}"]
            for d in docs:
                c = [x for x in A if x["doc"] == d and x["psm"] == p]
                fila.append(f"{c[0]['cer']:.2f} ({c[0]['bytes']} B)" if c else "—")
            tab.append(fila)
        out.append(md_tabla(["`--psm`"] + [d.replace("escaneado_", "") for d in docs], tab))
        mej = []
        for d in docs:
            cs = [x for x in A if x["doc"] == d]
            am, mn = argmins(cs, "psm", lambda c: c["cer"])
            # ‡ = el argmin NO es informativo: el motor no lee el documento con ningun
            # psm, asi que elegir el minimo entre 98,73 y 100,00 es elegir cual escupe
            # MENOS basura, no cual lee mejor. Es el criterio de k-por-motor.md §2.1.
            marca = " ‡" if mn >= 50 else ""
            mej.append([d.replace("escaneado_", ""),
                        ", ".join(f"psm {x}" for x in am) + marca, f"{mn:.2f}"])
            res.setdefault("mejor_psm_k1", {})[d] = {
                "psm": am, "cer": mn, "informativo": mn < 50}
        out += ["", "**Mejor `--psm` por documento** (k=1,00). "
                "**‡ = argmin NO informativo** (mejor CER ≥ 50 %: ningun `--psm` lee "
                "el documento, se estaria eligiendo cual escupe menos basura):", "",
                md_tabla(["documento", "argmin `--psm`", "mejor CER %"], mej), ""]
        an = anova2(A, "psm", "doc", lambda c: c["cer"])
        anc = anova2(A, "psm", "doc", lambda c: min(c["cer"], 100.0))
        res["anova_psm_doc_k1"] = an
        res["anova_psm_doc_k1_topado100"] = anc
        out += ["**Descomposicion de la varianza del CER en la rejilla `--psm` x "
                "documento**, en las dos lecturas: CER crudo (las alucinaciones de "
                ">100 % pesan al cuadrado) y CER topado a 100 (un documento no leido "
                "vale lo mismo se alucine o no):", "",
                "```", "crudo:   " + json.dumps(an, ensure_ascii=False),
                "topado:  " + json.dumps(anc, ensure_ascii=False), "```", ""]
        out += ["**Arrepentimiento por `--psm` fijo** (media sobre documentos de "
                "`CER(psm) - min_psm CER`):", "",
                md_tabla(["`--psm`", "regret medio"],
                         [[f"psm {k}", v] for k, v in
                          sorted(regret(A, "doc", "psm", lambda c: c["cer"]).items())]), ""]

    # ---------------- §2 interaccion psm x k -----------------------------------
    for tanda, titulo in (("B_inter_ppi", "raster `im_ppi` (resolucion DECLARADA)"),
                          ("C_inter_im", "raster `im` (resolucion NO declarada)")):
        B = [f for f in filas if f["tanda"] == tanda]
        if not B:
            continue
        docs = sorted({f["doc"] for f in B})
        out += [f"## 2.{tanda} Interaccion `--psm` x `k` — {titulo}", ""]
        for d in docs:
            cs = [x for x in B if x["doc"] == d]
            ks = sorted({x["k"] for x in cs})
            psms = sorted({x["psm"] for x in cs})
            tab = []
            for p in psms:
                fila = [f"psm {p}"]
                for kk in ks:
                    c = [x for x in cs if x["k"] == kk and x["psm"] == p]
                    fila.append(f"{c[0]['cer']:.2f}" if c else "—")
                am, mn = argmins([x for x in cs if x["psm"] == p], "k",
                                 lambda c: c["cer"])
                fila.append("/".join(f"×{x:.3f}".rstrip("0").rstrip(".") for x in am))
                tab.append(fila)
            out += [f"### {d}", "",
                    md_tabla(["`--psm`"] + [f"×{k:g}" for k in ks] + ["argmin k"], tab)]
            an = anova2(cs, "psm", "k", lambda c: c["cer"])
            res.setdefault(f"anova_{tanda}", {})[d] = an
            out += ["", "descomposicion de varianza del CER:", "",
                    "```", json.dumps(an, ensure_ascii=False), "```", ""]
            # ¿el argmin de k depende del psm?
            porpsm = {}
            for p in psms:
                am, mn = argmins([x for x in cs if x["psm"] == p], "k",
                                 lambda c: c["cer"])
                porpsm[p] = (am, round(mn, 2))
            porko = {}
            for kk in ks:
                am, mn = argmins([x for x in cs if x["k"] == kk], "psm",
                                 lambda c: c["cer"])
                porko[kk] = (am, round(mn, 2))
            res.setdefault(f"argmin_{tanda}", {})[d] = {
                "k_optimo_por_psm": {str(k): v for k, v in porpsm.items()},
                "psm_optimo_por_k": {str(k): v for k, v in porko.items()}}
            out += ["`k` optimo **por cada** `--psm`: " +
                    "; ".join(f"psm {p} → " + "/".join(f"×{x:g}" for x in v[0]) +
                              f" ({v[1]:.2f} %)" for p, v in porpsm.items()), "",
                    "`--psm` optimo **por cada** `k`: " +
                    "; ".join(f"×{k:g} → " + "/".join(f"psm {x}" for x in v[0]) +
                              f" ({v[1]:.2f} %)" for k, v in porko.items()), ""]

    # ---------------- §3 resolucion declarada ----------------------------------
    D = [f for f in filas if f["tanda"].startswith("D_dpi")]
    if D:
        out += ["## 3. La RESOLUCION DECLARADA, con los pixeles fijos", ""]
        docs = sorted({f["doc"] for f in D})
        psms = sorted({f["psm"] for f in D})
        dpis = sorted({(f["dpi_declarado"] or "0") for f in D}, key=lambda x: int(x))
        for d in docs:
            tab = []
            for p in psms:
                fila = [f"psm {p}"]
                for dp in dpis:
                    c = [x for x in D if x["doc"] == d and x["psm"] == p
                         and (x["dpi_declarado"] or "0") == dp]
                    fila.append(f"{c[0]['cer']:.2f}" if c else "—")
                tab.append(fila)
            out += [f"### {d} (pixeles fijos: raster `im` a k=1,00)", "",
                    md_tabla(["`--psm`"] + [("sin declarar" if x == "0" else f"{x} ppp")
                                            for x in dpis], tab), ""]
            cs = [x for x in D if x["doc"] == d]
            for _c in cs:
                _c["dpi_txt"] = _c["dpi_declarado"] or "0000"
            an = anova2(cs, "psm", "dpi_txt", lambda c: c["cer"])
            res.setdefault("anova_dpi", {})[d] = an
            out += ["```", json.dumps(an, ensure_ascii=False), "```", ""]

    # ---------------- §4 curva fina de ppp (B14) -------------------------------
    E = [f for f in filas if f["tanda"].startswith("E_curva")]
    if E:
        out += ["## 4. B14 — la curva de ppp de Tesseract, con `--psm` fijado", ""]
        docs = sorted({f["doc"] for f in E})
        psms = sorted({f["psm"] for f in E})
        for d in docs:
            cs = [x for x in E if x["doc"] == d]
            ks = sorted({x["k"] for x in cs})
            tab = []
            for p in psms:
                fila = [f"psm {p}"]
                for kk in ks:
                    c = [x for x in cs if x["k"] == kk and x["psm"] == p]
                    fila.append(f"{c[0]['cer']:.2f}" if c else "—")
                tab.append(fila)
            nat = {"escaneado_d2": 100, "escaneado_d3": 100, "escaneado_d4": 200,
                   "escaneado_d4c": 200, "escaneado_d4e": 200, "escaneado_d4f": 240}
            enc = [f"×{k:g} ({int(round(nat.get(d, 0) * k))} ppp)" for k in ks]
            out += [f"### {d}", "", md_tabla(["`--psm`"] + enc, tab), ""]
            for p in psms:
                am, mn = argmins([x for x in cs if x["psm"] == p], "k",
                                 lambda c: c["cer"])
                res.setdefault("curva_b14", {}).setdefault(d, {})[str(p)] = {
                    "argmin_k": am, "cer": round(mn, 2)}

    # ---------------- §5 regret global de k por psm ----------------------------
    todo_k = [f for f in filas if f["tanda"] in ("B_inter_ppi", "C_inter_im")]
    if todo_k:
        out += ["## 5. Arrepentimiento del `k` DENTRO de cada `--psm`", "",
                "Si `--psm` y `k` fueran separables, el `k` de minimo arrepentimiento "
                "seria el mismo para todos los `--psm`.", ""]
        for tanda in sorted({f["tanda"] for f in todo_k}):
            cs = [f for f in todo_k if f["tanda"] == tanda]
            psms = sorted({x["psm"] for x in cs})
            tab = []
            for p in psms:
                sub = [x for x in cs if x["psm"] == p]
                r = regret(sub, "doc", "k", lambda c: c["cer"])
                mejor = min(r, key=lambda kk: r[kk])
                tab.append([f"psm {p}", f"×{mejor:g}", r[mejor],
                            "; ".join(f"×{k:g}:{v}" for k, v in sorted(r.items()))])
            out += [f"**{tanda}**", "",
                    md_tabla(["`--psm`", "mejor `k` fijo", "su regret",
                              "regret de cada `k`"], tab), ""]
            res.setdefault("regret_k_por_psm", {})[tanda] = {
                str(t[0]): {"mejor_k": t[1], "regret": t[2]} for t in tab}

    # ---------------- §6 la eleccion CONJUNTA (psm, k) -------------------------
    for tanda in ("B_inter_ppi", "C_inter_im"):
        cs = [f for f in filas if f["tanda"] == tanda]
        if not cs:
            continue
        docs = sorted({x["doc"] for x in cs})
        psms = sorted({x["psm"] for x in cs})
        ks = sorted({x["k"] for x in cs})
        oraculo = {d: min(x["cer"] for x in cs if x["doc"] == d) for d in docs}
        # regret de cada par (psm, k)
        pares = {}
        for p in psms:
            for kk in ks:
                acc = 0.0
                for d in docs:
                    h = [x for x in cs if x["doc"] == d and x["psm"] == p
                         and x["k"] == kk]
                    if not h:
                        acc = None
                        break
                    acc += h[0]["cer"] - oraculo[d]
                if acc is not None:
                    pares[(p, kk)] = round(acc / len(docs), 3)
        mejor_par = min(pares, key=lambda t: pares[t])
        # procedimiento SEPARABLE: elegir psm a k=1,00 y luego optimizar k para el
        r1 = {}
        for p in psms:
            acc = 0.0
            for d in docs:
                h = [x for x in cs if x["doc"] == d and x["psm"] == p and x["k"] == 1.0]
                acc += h[0]["cer"] - oraculo[d] if h else 0.0
            r1[p] = acc / len(docs)
        psm_sep = min(r1, key=lambda p: r1[p])
        k_sep = min((kk for kk in ks), key=lambda kk: pares.get((psm_sep, kk), 1e9))
        res.setdefault("conjunto", {})[tanda] = {
            "oraculo_por_doc": oraculo,
            "mejor_par": {"psm": mejor_par[0], "k": mejor_par[1],
                          "regret": pares[mejor_par]},
            "separable": {"psm_elegido_a_k1": psm_sep, "k_optimo_para_ese_psm": k_sep,
                          "regret": pares.get((psm_sep, k_sep))},
            "regret_todos_los_pares": {f"psm{p}__k{kk:g}": v
                                       for (p, kk), v in sorted(pares.items())}}
        out += [f"## 6.{tanda} La eleccion CONJUNTA `(--psm, k)`", "",
                f"Oraculo por documento (mejor celda de las {len(psms) * len(ks)}): " +
                "; ".join(f"{d.replace('escaneado_', '')} {v:.2f} %"
                          for d, v in oraculo.items()), "",
                f"**Mejor par fijo: `--psm {mejor_par[0]}` con `k = ×{mejor_par[1]:g}`, "
                f"arrepentimiento medio {pares[mejor_par]:.3f} puntos.**", "",
                f"**Procedimiento separable** (elegir `--psm` a ×1,00 y luego su mejor "
                f"`k`): `--psm {psm_sep}` + `×{k_sep:g}`, arrepentimiento "
                f"**{pares.get((psm_sep, k_sep)):.3f}**.", "",
                "Las diez mejores parejas:", "",
                md_tabla(["`--psm`", "`k`", "regret medio"],
                         [[f"psm {p}", f"×{kk:g}", v] for (p, kk), v in
                          sorted(pares.items(), key=lambda t: t[1])[:10]]), ""]

    # ---------------- §7 cuanto mueve cada eje --------------------------------
    for tanda in ("B_inter_ppi", "C_inter_im"):
        cs = [f for f in filas if f["tanda"] == tanda]
        if not cs:
            continue
        out += [f"## 7.{tanda} Cuanto mueve cada eje, sobre los MISMOS pixeles", ""]
        tab = []
        for d in sorted({x["doc"] for x in cs}):
            sub = [x for x in cs if x["doc"] == d]
            ks = sorted({x["k"] for x in sub})
            psms = sorted({x["psm"] for x in sub})
            # recorrido del psm a k fijo, y del k a psm fijo
            rp = {kk: (max(x["cer"] for x in sub if x["k"] == kk) -
                       min(x["cer"] for x in sub if x["k"] == kk)) for kk in ks}
            rk = {p: (max(x["cer"] for x in sub if x["psm"] == p) -
                      min(x["cer"] for x in sub if x["psm"] == p)) for p in psms}
            tab.append([d.replace("escaneado_", ""),
                        f"{min(rp.values()):.2f} – {max(rp.values()):.2f}",
                        f"{sum(rp.values()) / len(rp):.2f}",
                        f"{min(rk.values()):.2f} – {max(rk.values()):.2f}",
                        f"{sum(rk.values()) / len(rk):.2f}"])
            res.setdefault("recorridos", {}).setdefault(tanda, {})[d] = {
                "psm_a_k_fijo": {str(k): round(v, 2) for k, v in rp.items()},
                "k_a_psm_fijo": {str(k): round(v, 2) for k, v in rk.items()}}
        out += [md_tabla(["documento", "recorrido del `--psm` a `k` fijo (min–max)",
                          "media", "recorrido del `k` a `--psm` fijo (min–max)",
                          "media"], tab), ""]

    io.open(os.path.join(BASE, "tablas.md"), "w", encoding="utf-8").write("\n".join(out))
    json.dump({"resumen": res, "filas": filas},
              io.open(os.path.join(JSN, "resumen.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"escrito tablas.md ({len(filas)} celdas) y json/resumen.json")

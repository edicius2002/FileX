#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Lo medible SIN modelo: ambiguedad lexica, solapamiento de esquemas y
herramientas indistinguibles por su descripcion.

Todas las metricas son deterministas y reproducibles: no hay LLM aqui.
Salida: bench/salidas-saturacion/estatico.json
"""
import json
import os
import re
import itertools
import difflib

BASE = os.path.dirname(os.path.abspath(__file__))

CATALOGOS = [
    ("A", "video-audio-mcp (27)", "catalogo_A_vam27.json"),
    ("C", "video-audio-mcp sin subsumidas (14)", "catalogo_C_vam14.json"),
    ("B", "ffmpeg-mcp-lite (8)", "catalogo_B_lite8.json"),
]

PARADAS = set("""a an the to of for and or in on with from into as is are be by at
un una el la los las de del a en con para y o que se su sus lo por es son
path to the file input output optional target source save saves saved returns
return args arg status message indicating success failure using use uses will
if not none default specified specify e g eg ej ruta fichero archivo""".split())

PROHIBIDAS = ("prd", "previous message", "see ", "above", "below", "brevity",
              "todo", "as described", "same as", "tbd")


def tokens_nombre(n):
    return [p for p in re.split(r"[_\W]+", n.lower()) if p]


def jaccard(a, b):
    a, b = set(a), set(b)
    if not a and not b:
        return 1.0
    return len(a & b) / float(len(a | b))


def sim_cadena(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def limpia_desc(d):
    """Deja solo la parte util: primera frase / resumen, sin la seccion Args."""
    d = (d or "").replace("\n", " ")
    d = re.split(r"\bArgs\b|\bReturns\b|\bParameters\b", d)[0]
    return re.sub(r"\s+", " ", d).strip()


def bolsa(texto):
    ws = [w for w in re.split(r"[^a-z0-9]+", texto.lower()) if w and w not in PARADAS]
    return set(ws)


def analiza(nombre_corto, etiqueta, fichero):
    tools = json.load(open(os.path.join(BASE, fichero), encoding="utf-8"))
    n = len(tools)
    res = {"catalogo": nombre_corto, "etiqueta": etiqueta, "n": n,
           "tokens_declaracion_suma": sum(t["tokens_declaracion"] for t in tools)}

    # --- 1. familias de prefijo -------------------------------------------
    familias = {}
    for t in tools:
        ps = tokens_nombre(t["name"])
        for k in (2, 3, 4):
            if len(ps) > k:
                familias.setdefault("_".join(ps[:k]), []).append(t["name"])
    res["familias_prefijo"] = {k: v for k, v in sorted(familias.items())
                               if len(v) >= 2}

    # --- 2. pares por similitud -------------------------------------------
    pares = []
    for x, y in itertools.combinations(tools, 2):
        jn = jaccard(tokens_nombre(x["name"]), tokens_nombre(y["name"]))
        sn = sim_cadena(x["name"], y["name"])
        dx, dy = limpia_desc(x["description"]), limpia_desc(y["description"])
        jd = jaccard(bolsa(dx), bolsa(dy))
        sd = sim_cadena(dx, dy)
        px = set((x["inputSchema"].get("properties") or {}).keys())
        py = set((y["inputSchema"].get("properties") or {}).keys())
        jp = jaccard(px, py)
        subsume = (px < py) or (py < px) or (px == py and px)
        pares.append({
            "a": x["name"], "b": y["name"],
            "jaccard_nombre": round(jn, 3), "sim_nombre": round(sn, 3),
            "jaccard_desc": round(jd, 3), "sim_desc": round(sd, 3),
            "jaccard_params": round(jp, 3),
            "params_anidados": bool(subsume),
        })

    def cuenta(pred):
        return sum(1 for p in pares if pred(p))

    res["n_pares"] = len(pares)
    res["pares_nombre_sim_ge_070"] = cuenta(lambda p: p["sim_nombre"] >= 0.70)
    res["pares_desc_sim_ge_070"] = cuenta(lambda p: p["sim_desc"] >= 0.70)
    res["pares_desc_sim_ge_085"] = cuenta(lambda p: p["sim_desc"] >= 0.85)
    res["pares_params_identicos"] = cuenta(lambda p: p["jaccard_params"] == 1.0)
    res["pares_params_anidados"] = cuenta(lambda p: p["params_anidados"])
    res["pares_confundibles"] = cuenta(
        lambda p: p["sim_nombre"] >= 0.70 and p["sim_desc"] >= 0.70)

    # --- 3. fraccion del catalogo con al menos un gemelo -------------------
    con_gemelo_desc = set()
    con_gemelo_total = set()
    for p in pares:
        if p["sim_desc"] >= 0.70:
            con_gemelo_desc.add(p["a"]); con_gemelo_desc.add(p["b"])
        if p["sim_nombre"] >= 0.70 and p["sim_desc"] >= 0.70:
            con_gemelo_total.add(p["a"]); con_gemelo_total.add(p["b"])
    res["frac_con_gemelo_por_descripcion"] = round(len(con_gemelo_desc) / float(n), 3)
    res["frac_confundible_nombre_y_desc"] = round(len(con_gemelo_total) / float(n), 3)
    res["herramientas_confundibles"] = sorted(con_gemelo_total)

    # --- 4. indistinguibles por el resumen solo ---------------------------
    resumen = {}
    for t in tools:
        r = limpia_desc(t["description"])
        resumen.setdefault(r.lower(), []).append(t["name"])
    res["resumenes_identicos"] = {k: v for k, v in resumen.items() if len(v) > 1}

    # --- 5. descripciones que remiten a lo invisible ----------------------
    malas = []
    for t in tools:
        d = (t["description"] or "").lower()
        hit = [w for w in PROHIBIDAS if w in d]
        if hit:
            malas.append({"tool": t["name"], "marcas": hit})
    res["descripciones_con_referencia_externa"] = malas

    # --- 6. esquemas: parametros sin descripcion --------------------------
    sin_desc = []
    tot_p = 0
    for t in tools:
        props = t["inputSchema"].get("properties") or {}
        for k, v in props.items():
            tot_p += 1
            if not (v or {}).get("description"):
                sin_desc.append("%s.%s" % (t["name"], k))
    res["n_parametros"] = tot_p
    res["n_parametros_sin_descripcion"] = len(sin_desc)
    res["frac_parametros_sin_descripcion"] = round(len(sin_desc) / float(tot_p), 3)

    # --- 7. esquemas opacos (object/array sin claves declaradas) ----------
    opacos = []
    for t in tools:
        props = t["inputSchema"].get("properties") or {}
        for k, v in props.items():
            v = v or {}
            it = v.get("items") or {}
            if v.get("type") == "array" and it.get("type") == "object" \
                    and not it.get("properties"):
                opacos.append("%s.%s" % (t["name"], k))
            elif v.get("type") == "object" and not v.get("properties"):
                opacos.append("%s.%s" % (t["name"], k))
    res["esquemas_opacos"] = opacos

    # --- 8. firma de forma del esquema -----------------------------------
    # Dos herramientas con la MISMA firma de forma son indistinguibles para
    # quien mire solo el esquema: mismo numero de argumentos, mismos tipos,
    # misma obligatoriedad. Solo los NOMBRES de los argumentos las separan.
    formas = {}
    for t in tools:
        props = t["inputSchema"].get("properties") or {}
        req = set(t["inputSchema"].get("required") or [])
        firma = tuple(sorted((str((v or {}).get("type")), k in req)
                             for k, v in props.items()))
        formas.setdefault(firma, []).append(t["name"])
    res["formas_esquema"] = {str(k): v for k, v in formas.items() if len(v) > 1}
    res["n_en_forma_compartida"] = sum(len(v) for v in formas.values() if len(v) > 1)
    res["frac_en_forma_compartida"] = round(res["n_en_forma_compartida"] / float(n), 3)

    # --- 9. indistinguibles salvo por el nombre de los argumentos ---------
    indist = set()
    forma_de = {}
    for firma, nombres in formas.items():
        for nm in nombres:
            forma_de[nm] = firma
    for p in pares:
        if forma_de[p["a"]] == forma_de[p["b"]] and p["sim_desc"] >= 0.70:
            indist.add(p["a"]); indist.add(p["b"])
    res["indistinguibles_salvo_nombres_de_argumento"] = sorted(indist)
    res["frac_indistinguibles"] = round(len(indist) / float(n), 3)

    res["_pares"] = sorted(pares, key=lambda p: -(p["sim_nombre"] + p["sim_desc"]))[:25]
    return res


def main():
    out = [analiza(*c) for c in CATALOGOS]
    with open(os.path.join(BASE, "estatico.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

    cols = ["n", "tokens_declaracion_suma", "n_pares", "pares_nombre_sim_ge_070",
            "pares_desc_sim_ge_070", "pares_desc_sim_ge_085",
            "pares_params_identicos", "pares_confundibles",
            "frac_con_gemelo_por_descripcion", "frac_confundible_nombre_y_desc",
            "frac_parametros_sin_descripcion", "frac_en_forma_compartida",
            "frac_indistinguibles"]
    print("%-38s %s" % ("metrica", "  ".join("%9s" % r["catalogo"] for r in out)))
    for c in cols:
        print("%-38s %s" % (c, "  ".join("%9s" % r[c] for r in out)))
    for r in out:
        print("\n== %s ==" % r["etiqueta"])
        print(" familias de prefijo >=2:",
              {k: len(v) for k, v in r["familias_prefijo"].items() if len(v) >= 3})
        print(" confundibles:", r["herramientas_confundibles"])
        print(" desc con referencia externa:",
              [m["tool"] for m in r["descripciones_con_referencia_externa"]])
        print(" esquemas opacos:", r["esquemas_opacos"])
        print(" indistinguibles salvo nombres de argumento:", r["indistinguibles_salvo_nombres_de_argumento"])
        print(" formas compartidas:", {k: v for k, v in r["formas_esquema"].items()})
        print(" top 5 pares:")
        for p in r["_pares"][:5]:
            print("   %-34s %-34s nom=%.2f desc=%.2f par=%.2f"
                  % (p["a"], p["b"], p["sim_nombre"], p["sim_desc"],
                     p["jaccard_params"]))


if __name__ == "__main__":
    main()

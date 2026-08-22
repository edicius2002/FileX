# -*- coding: utf-8 -*-
"""P2 - LA CIFRA: que porcentaje del 50,5 % de E1 es invocacion y no capacidad.

Contabilidad, sin ninguna medida nueva. Se parte de la de E1 (reproducida exactamente
por _p2_agrega.py: 40.252 / 22.235 / 75.874 / 140) y se aplica el resultado de P2:

  a) las semiaristas que P2-INV revive dejan de matar aristas; esas aristas pasan al
     marco y alli les toca el residuo, no la certeza de estar muertas;
  b) el residuo del marco baja de 23,1 % a 23,1 % x (1 - tasa_recuperacion_residuo).

La recuperacion se reparte en las tres categorias del encargo, y las aristas de
categoria 2 se contabilizan APARTE: son aristas, pero NO son aristas automaticas.

Escribe final_p2.json
"""
import os, sys, json, math
from collections import Counter, defaultdict

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-invocacion")
E1D = os.path.join(RAIZ, r"bench\salidas-aristas")

# --- falsos positivos detectados por validacion_p2.json / _p2_valida2: la salida
# no es del formato pedido aunque rc=0. NO cuentan como recuperacion.
FALSOS_POSITIVOS = {("ogg", "im24"), ("wtv", "im1"), ("tta", "h265.mp4"), ("266", "y")}
# discrepancia con E1: aqui la linea base de ConvertX NO falla, luego no hay nada
# que recuperar. Se excluye del numerador y se deja en el denominador.
DISCREPANTES = {("png", "ico")}


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def estado_semi_p2():
    """Estado FINAL de cada semiarista tras P2-INV, y su categoria."""
    ent, out = {}, {}
    cat_e, cat_s = {}, {}
    # 1) el estado de E1
    e1 = json.load(open(os.path.join(E1D, "semi_entrada.json"), encoding="utf-8"))
    e2 = json.load(open(os.path.join(E1D, "semi_entrada2.json"), encoding="utf-8"))
    s1 = json.load(open(os.path.join(E1D, "semi_salida.json"), encoding="utf-8"))
    s2 = json.load(open(os.path.join(E1D, "semi_salida2.json"), encoding="utf-8"))
    for k, v in e1.items():
        if v["estado"] == "no_materializable":
            ent[k] = "indet"
        else:
            ent[k] = "viva" if e2.get(k, {}).get("estado", v["estado"]) == "viva" else "muerta"
    for k, v in s1.items():
        out[k] = "viva" if (v["vivo"] or s2.get(k, {}).get("vivo", False)) else "muerta"
    # 2) las revivas de P2
    for fich, dicc, cat in (("semi_in_p2.json", ent, cat_e),
                            ("semi_in_p2b.json", ent, cat_e),
                            ("crudos_p2.json", ent, cat_e),
                            ("semi_out_p2b.json", out, cat_s)):
        p = os.path.join(SAL, fich)
        if not os.path.exists(p):
            continue
        for k, v in json.load(open(p, encoding="utf-8")).items():
            if v.get("estado") == "viva" and dicc.get(k) == "muerta":
                dicc[k] = "viva_p2"
                cat[k] = v.get("categoria_p2", 2)
    # el veredicto FINO de crudos_ideal.json manda: comparado contra su referencia
    # ideal degradada, `ftxt` sigue entregando basura (RMSE 0,65). No revive.
    pi = os.path.join(SAL, "crudos_ideal.json")
    if os.path.exists(pi):
        for f, d in json.load(open(pi, encoding="utf-8")).items():
            if d.get("veredicto") == "DESTRUIDO":
                k = "imagemagick|" + f
                if ent.get(k) == "viva_p2":
                    ent[k] = "muerta"
                    cat_e.pop(k, None)
    return ent, out, cat_e, cat_s


if __name__ == "__main__":
    ar = json.load(open(os.path.join(SAL, "aristas.json"), encoding="utf-8"))
    ent, out, cat_e, cat_s = estado_semi_p2()

    def clasifica(estado_ent, estado_out):
        vivo = {"viva", "viva_p2"}
        if estado_ent in vivo and estado_out in vivo:
            return "viva"
        if estado_ent == "muerta" or estado_out == "muerta":
            return "muerta"
        return "indet"

    c_e1, c_p2 = Counter(), Counter()
    recuperadas, cat_recup = [], Counter()
    for reg in ar["A"]:
        ab, ms = reg.split("|")
        a, b = ab.split(">")
        motores = ms.split(",")
        est1, est2 = [], []
        cats = []
        for m in motores:
            if m in ("ffmpeg", "imagemagick"):
                ke, ks = "%s|%s" % (m, a), "%s|%s" % (m, b)
                e0 = "viva" if ent.get(ke, "indet") == "viva" else ent.get(ke, "indet")
                s0 = "viva" if out.get(ks, "indet") == "viva" else out.get(ks, "indet")
                # estado con E1: viva_p2 cuenta como muerta
                est1.append(clasifica("muerta" if e0 == "viva_p2" else e0,
                                      "muerta" if s0 == "viva_p2" else s0))
                est2.append(clasifica(e0, s0))
                if e0 == "viva_p2" or s0 == "viva_p2":
                    cats.append(max([cat_e.get(ke, 1) if e0 == "viva_p2" else 1,
                                     cat_s.get(ks, 1) if s0 == "viva_p2" else 1]))
            else:
                est1.append("otro")
                est2.append("otro")
        f = lambda es: ("viva" if "viva" in es else "otro_motor" if "otro" in es
                        else "indeterminada" if "indet" in es else "muerta")
        v1, v2 = f(est1), f(est2)
        c_e1[v1] += 1
        c_p2[v2] += 1
        if v1 == "muerta" and v2 == "viva":
            recuperadas.append((a, b, ms))
            cat_recup[max(cats) if cats else 2] += 1

    # ---- residuo
    resid = json.load(open(os.path.join(SAL, "resid_p2.json"), encoding="utf-8"))
    residb = json.load(open(os.path.join(SAL, "resid_p2b.json"), encoding="utf-8"))
    vivas1 = {(r["a"], r["b"]) for r in resid if r.get("p2_estado") == "viva"}
    cat1 = {(r["a"], r["b"]): r.get("p2_categoria", 1) for r in resid if r.get("p2_estado") == "viva"}
    vivas2 = {(r["a"], r["b"]) for r in residb if r.get("p2b_estado") == "viva"}
    n_resid = len({(r["a"], r["b"]) for r in resid})
    vivas = (vivas1 | vivas2) - FALSOS_POSITIVOS - DISCREPANTES
    k_resid = len(vivas)
    p_rec_resid = k_resid / n_resid
    ic_resid = wilson(k_resid, n_resid)
    cat_res = Counter()
    for t in vivas:
        cat_res[cat1.get(t, 1)] += 1

    # ---- la contabilidad de E1, reproducida
    N = sum(c_e1.values())
    marco_e1 = c_e1["viva"]
    muertas_e1 = c_e1["muerta"]
    p_nom_marco_e1 = 0.231          # E1 sec.5, muestra de 498
    nominales_e1 = muertas_e1 + p_nom_marco_e1 * marco_e1
    verdicto_e1 = marco_e1 + muertas_e1
    tasa_e1 = nominales_e1 / verdicto_e1

    # ---- con P2-INV
    marco_p2 = c_p2["viva"]
    muertas_p2 = c_p2["muerta"]
    rec = len(recuperadas)
    p_nom_marco_p2 = p_nom_marco_e1 * (1 - p_rec_resid)

    # DENOMINADOR FIJO: las mismas 62.487 aristas que E1 juzgo. Al revivir una
    # semiarista de entrada, 2.868 aristas pasan de "muerta" a INDETERMINADA (su otra
    # mitad nunca se pudo materializar). NO estan recuperadas: estan sin veredicto.
    # Contarlas como recuperadas inflaria la cifra; aqui siguen contando como
    # nominales, que es la lectura conservadora.
    sin_veredicto_nuevo = muertas_e1 - muertas_p2 - rec
    nominales_p2 = (muertas_e1 - rec) + p_nom_marco_p2 * (marco_e1 + rec)
    tasa_p2 = nominales_p2 / verdicto_e1

    recuperado_abs = nominales_e1 - nominales_p2
    frac = recuperado_abs / nominales_e1

    # reparto por categoria (aristas)
    ar_cat1 = cat_recup[1] * (1 - p_nom_marco_p2)
    ar_cat2 = cat_recup[2] * (1 - p_nom_marco_p2)
    # residuo recuperado: aristas del marco original
    resid_rec = p_nom_marco_e1 * marco_e1 * p_rec_resid
    resid_cat1 = resid_rec * (cat_res[1] / max(1, sum(cat_res.values())))
    resid_cat2 = resid_rec * (cat_res[2] / max(1, sum(cat_res.values())))
    # intervalo: el censo de semiaristas no tiene error muestral; el residuo si
    base_semi = ar_cat1 + ar_cat2
    rec_lo = base_semi + p_nom_marco_e1 * marco_e1 * ic_resid[0]
    rec_hi = base_semi + p_nom_marco_e1 * marco_e1 * ic_resid[1]
    # sensibilidad: si las 4.805 recuperadas conservan el residuo de E1 (23,1 %)
    rec_pesim = (cat_recup[1] + cat_recup[2]) * (1 - p_nom_marco_e1) + resid_rec

    out_json = {
        "poblacion": N,
        "E1": {"marco": marco_e1, "muertas_semiarista": muertas_e1,
               "indeterminadas": c_e1["indeterminada"], "otro_motor": c_e1["otro_motor"],
               "con_veredicto": verdicto_e1, "nominales": round(nominales_e1),
               "tasa": round(100 * tasa_e1, 2)},
        "P2": {"marco": marco_p2, "muertas_semiarista": muertas_p2,
               "recuperadas_por_semiarista": rec,
               "recuperadas_por_categoria": dict(cat_recup),
               "residuo_nominal": round(100 * p_nom_marco_p2, 2),
               "nominales": round(nominales_p2), "tasa": round(100 * tasa_p2, 2)},
        "residuo": {"n": n_resid, "recuperadas": k_resid,
                    "tasa": round(100 * p_rec_resid, 2),
                    "ic95": [round(100 * ic_resid[0], 2), round(100 * ic_resid[1], 2)],
                    "por_categoria": dict(cat_res)},
        "recuperacion": {"aristas": round(recuperado_abs),
                         "fraccion_del_50_5": round(100 * frac, 2),
                         "ic95_fraccion": [round(100 * rec_lo / nominales_e1, 2),
                                           round(100 * rec_hi / nominales_e1, 2)],
                         "sensibilidad_pesimista": round(100 * rec_pesim / nominales_e1, 2),
                         "cat1_aristas": round(ar_cat1 + resid_cat1),
                         "cat2_aristas": round(ar_cat2 + resid_cat2),
                         "cat1_fraccion": round(100 * (ar_cat1 + resid_cat1) / nominales_e1, 2),
                         "cat2_fraccion": round(100 * (ar_cat2 + resid_cat2) / nominales_e1, 2),
                         "sin_veredicto_nuevo": sin_veredicto_nuevo},
    }
    json.dump(out_json, open(os.path.join(SAL, "final_p2.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)

    print("POBLACION: %d aristas\n" % N)
    print("                                E1 (ConvertX)     P2-INV")
    print("  marco muestral            %12d   %10d" % (marco_e1, marco_p2))
    print("  muertas por semiarista    %12d   %10d" % (muertas_e1, muertas_p2))
    print("  indeterminadas            %12d   %10d" % (c_e1["indeterminada"], c_p2["indeterminada"]))
    print("  con veredicto             %12d   %10d" % (verdicto_e1, marco_p2 + muertas_p2))
    print("  residuo nominal del marco %11.1f %%  %9.1f %%" %
          (100 * p_nom_marco_e1, 100 * p_nom_marco_p2))
    print("  NOMINALES                 %12d   %10d" % (round(nominales_e1), round(nominales_p2)))
    print("  TASA NOMINAL              %11.1f %%  %9.1f %%" % (100 * tasa_e1, 100 * tasa_p2))
    print("\n  aristas recuperadas por semiarista: %d  %s" % (rec, dict(cat_recup)))
    print("  residuo: %d de %d recuperadas = %.1f %% [%.1f - %.1f]  %s" %
          (k_resid, n_resid, 100 * p_rec_resid, 100 * ic_resid[0], 100 * ic_resid[1],
           dict(cat_res)))
    print("  aristas que pasan de MUERTA a SIN VEREDICTO (no recuperadas): %d" %
          sin_veredicto_nuevo)
    print("\n>>> RECUPERADO: %d aristas = %.1f %% del 50,5 %%  [IC 95 %%: %.1f - %.1f]" %
          (round(recuperado_abs), 100 * frac,
           100 * rec_lo / nominales_e1, 100 * rec_hi / nominales_e1))
    print("    sensibilidad (residuo de las recuperadas = 23,1 %%): %.1f %%" %
          (100 * rec_pesim / nominales_e1))
    print("    categoria 1 (bandera):   %6d aristas = %.1f %% del 50,5 %%" %
          (round(ar_cat1 + resid_cat1), 100 * (ar_cat1 + resid_cat1) / nominales_e1))
    print("    categoria 2 (parametro): %6d aristas = %.1f %% del 50,5 %%" %
          (round(ar_cat2 + resid_cat2), 100 * (ar_cat2 + resid_cat2) / nominales_e1))
    print("    categoria 3 (irrecuperable): %.1f %% del 50,5 %%" %
          (100 * (1 - frac)))

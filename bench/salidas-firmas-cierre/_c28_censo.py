"""C28 / paso 1 - LOS 86 INDETERMINADOS, separados en sus dos clases.

`bench/firmas-contrato.md` §10.1 los deja PENDIENTES en una sola frase: *«79 que
ningun motor de esta maquina escribe y 7 mas donde la muestra describe al
escritor y no al formato»*. Antes de atacar nada hay que REPRODUCIR esa
separacion sobre el fichero que la produjo (trampa 58: el hecho no implica la
causa), porque el encargo se resuelve distinto en cada clase: la primera
necesita una MUESTRA que no existe y la segunda un SEGUNDO ESCRITOR, que si.

Uso:  python bench/salidas-firmas-cierre/_c28_censo.py
"""
import json
import os
import sys
from collections import Counter

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIRMAS_F1 = os.path.join(RAIZ, "bench", "salidas-firmas")
sys.path.insert(0, RAIZ)
from filex import verificador as V  # noqa: E402


def escritores(fmt, censos):
    """Motores que SI escribieron el formato, con cuantas muestras cada uno."""
    out = {}
    for d in censos.values():
        for motor, formatos in d.items():
            if not isinstance(formatos, dict):
                continue
            e = formatos.get(fmt)
            if not isinstance(e, dict):
                continue
            n = 0
            if isinstance(e.get("muestras"), list):
                n = sum(len(m.get("cab", [])) for m in e["muestras"])
            elif e.get("cab"):
                n = len(e["cab"])
            if n:
                out[motor] = out.get(motor, 0) + n
    return out


def main():
    cat = json.load(open(os.path.join(FIRMAS_F1, "categorias.json"),
                         encoding="utf-8"))
    censos = {}
    for nom in ("firmas_censo_local.json", "firmas_censo_contenedor.json"):
        p = os.path.join(FIRMAS_F1, nom)
        if os.path.exists(p):
            censos[nom] = json.load(open(p, encoding="utf-8"))

    reparto = Counter()
    indet = []
    for fmt, e in cat.items():
        c = e.get("cat_nuevo") if isinstance(e, dict) else None
        reparto[c] += 1
        if c == "0_indeterminado":
            indet.append((fmt, e))

    # Los indeterminados, partidos por si HAY o NO muestra en algun censo
    sin_muestra, con_muestra = [], []
    for fmt, e in indet:
        esc = escritores(fmt, censos)
        fila = {"formato": fmt, "escritores": esc,
                "motivo_f1": (e.get("motivo") if isinstance(e, dict) else None),
                "adaptadores": (e.get("adaptadores") if isinstance(e, dict) else None),
                "en_tabla": ("." + fmt) in V.EXT_A_FIRMAS,
                "en_sin_firma": ("." + fmt) in V.EXT_SIN_FIRMA}
        (con_muestra if esc else sin_muestra).append(fila)

    res = {"reparto_categorias": dict(reparto),
           "n_indeterminados": len(indet),
           "n_sin_muestra": len(sin_muestra),
           "n_con_muestra_de_un_solo_escritor": len(con_muestra),
           "clave_ejemplo": indet[0][1] if indet else None,
           "sin_muestra": sin_muestra,
           "con_muestra": con_muestra}
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

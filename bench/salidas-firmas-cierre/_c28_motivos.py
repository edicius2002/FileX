"""C28 / paso 2 - EL REPARTO REAL DE LOS 86, por el motivo que escribio el censo.

`firmas-contrato.md` §10.1 los reparte «79 + 7». Este script cuenta los motivos
que el propio `categorias.json` guarda, que es de donde salio la frase, y
publica el reparto exacto -- porque **de los dos remedios que propone el
encargo, cada motivo solo admite uno**: si no hay muestra, no hay firma que
aprender y hace falta el corpus FATE; si la muestra describe al ESCRITOR, hace
falta un SEGUNDO escritor, que si esta.

Uso:  python bench/salidas-firmas-cierre/_c28_motivos.py
"""
import json
import os
import sys
from collections import Counter, defaultdict

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIRMAS_F1 = os.path.join(RAIZ, "bench", "salidas-firmas")


def main():
    cat = json.load(open(os.path.join(FIRMAS_F1, "categorias.json"),
                         encoding="utf-8"))
    censos = {}
    for nom in ("firmas_censo_local.json", "firmas_censo_contenedor.json"):
        censos[nom] = json.load(open(os.path.join(FIRMAS_F1, nom),
                                     encoding="utf-8"))
    # estado declarado por el censo para cada formato, por motor
    estado = defaultdict(dict)
    for d in censos.values():
        for motor, formatos in d.items():
            if isinstance(formatos, dict):
                for f, e in formatos.items():
                    if isinstance(e, dict):
                        estado[f][motor] = e.get("estado") or (
                            "escrito" if e.get("muestras") or e.get("cab")
                            else "sin_estado")

    por_motivo = defaultdict(list)
    for fmt, e in cat.items():
        if not isinstance(e, dict) or e.get("cat_nuevo") != "0_indeterminado":
            continue
        por_motivo[(e.get("motivo") or "(sin motivo)")].append(fmt)

    res = {"n": sum(len(v) for v in por_motivo.values()),
           "motivos": {k: {"n": len(v), "formatos": sorted(v)}
                       for k, v in sorted(por_motivo.items(),
                                          key=lambda x: -len(x[1]))}}
    # y para cada motivo, cuantos motores lo intentaron y con que estado
    for k, v in res["motivos"].items():
        c = Counter()
        for f in v["formatos"]:
            for motor, st in estado.get(f, {}).items():
                c[st] += 1
            if f not in estado:
                c["nadie_lo_intento"] += 1
        v["estados_del_censo"] = dict(c)
        v["segundo_escritor_posible"] = sorted(
            f for f in v["formatos"]
            if len([m for m, st in estado.get(f, {}).items()
                    if st == "escrito"]) >= 2)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

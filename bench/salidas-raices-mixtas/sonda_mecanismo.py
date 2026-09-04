"""N35 — por que `C:\\` no abre nada: el mecanismo, sondeado y no deducido.

Yo esperaba que el candidato E («relajar R3 y aceptar la raiz de unidad»)
fuera la fuga: si `C:\\` se admite como raiz, pense, se lee la unidad entera.
`sonda_candidatos.py` devuelve lo contrario — con `C:\\` como unica raiz NO se
lee ni `C:\\Windows\\win.ini`—, asi que la hipotesis estaba mal y hay que
sondear el mecanismo antes de escribir una linea (CLAUDE.md §3: una explicacion
plausible no es un mecanismo).

Salida: bench/salidas-raices-mixtas/mecanismo.json
"""

from __future__ import annotations

import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)

from filex.confinamiento import Confinamiento, _norm  # noqa: E402


def main() -> int:
    raiz_unidad = _norm(os.path.abspath("C:\\"))
    raiz_normal = _norm(os.path.abspath(r"C:\Users"))
    candidato = _norm(os.path.abspath(r"C:\Windows\win.ini"))

    obs = {
        "_norm('C:\\\\')": raiz_unidad,
        "_norm('C:\\\\Users')": raiz_normal,
        "candidato": candidato,
        # El predicado exacto de `_dentro`, desmontado
        "raiz_unidad + os.sep": raiz_unidad + os.sep,
        "raiz_normal + os.sep": raiz_normal + os.sep,
        "candidato == raiz_unidad": candidato == raiz_unidad,
        "candidato.startswith(raiz_unidad + os.sep)":
            candidato.startswith(raiz_unidad + os.sep),
        "candidato.startswith(raiz_normal + os.sep)":
            candidato.startswith(raiz_normal + os.sep),
    }

    # Control positivo y negativo del propio `_dentro`, por la via publica.
    c = Confinamiento([r"C:\Users"])
    obs["_dentro(win.ini, [C:\\Users])"] = c._dentro(candidato, [raiz_normal])
    obs["_dentro(win.ini, [C:\\])"] = c._dentro(candidato, [raiz_unidad])
    # Y el control que prueba que `_dentro` NO esta roto en general:
    bajo_users = _norm(os.path.abspath(r"C:\Users\publico.txt"))
    obs["_dentro(C:\\Users\\publico.txt, [C:\\Users])"] = c._dentro(bajo_users, [raiz_normal])

    obs["conclusion"] = (
        "la raiz de unidad ya termina en el separador, asi que `r + os.sep` "
        "produce una barra DOBLE que ningun candidato normalizado casa: "
        "`_dentro` devuelve False para todo. R3 dice literalmente lo que pasa "
        "-«no confina nada»- y no confina nada en el sentido de que DENIEGA "
        "todo, no en el de que lo permita todo."
    )

    destino = os.path.join(AQUI, "mecanismo.json")
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(obs, fh, indent=2, ensure_ascii=False)
    for k, v in obs.items():
        print("%-46s %s" % (k, v))
    print("\n-> %s" % destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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

    # ---------------------------------------------------------------------
    # CORREGIDO tras la revision: `_dentro` tiene DOS ramas y la primera
    # version de esta sonda solo desmonto una. El `or` de
    # `c == r or c.startswith(r + os.sep)` hace que la raiz de unidad SI
    # conceda un candidato: ELLA MISMA. Publicar «deniega para todo» era
    # falso, y era justo la frase que sostenia la decision.
    obs["_dentro(C:\\, [C:\\])  <- la rama `c == r`"] = c._dentro("C:\\", [raiz_unidad])
    # Cuantos candidatos concede, exactamente: se prueba una muestra.
    muestra = ["C:\\", r"C:\Windows", r"C:\Windows\win.ini", r"C:\Users",
               r"C:\noexiste"]
    concedidos = [m for m in muestra if c._dentro(_norm(os.path.abspath(m)),
                                                  [raiz_unidad])]
    obs["candidatos_concedidos_por_la_raiz_de_unidad"] = concedidos
    obs["n_concedidos_de_la_muestra"] = "%d de %d" % (len(concedidos), len(muestra))

    obs["conclusion"] = (
        "La raiz de unidad ya termina en el separador, asi que `r + os.sep` "
        "produce una barra DOBLE que ningun descendiente casa. Pero `_dentro` "
        "es un OR de dos ramas y la primera, `c == r`, SI acepta un candidato: "
        "LA PROPIA RAIZ. Asi que `C:\\` no concede «nada» -eso era falso y se "
        "publico- sino EXACTAMENTE UN camino, el directorio raiz; ningun "
        "descendiente, ni siquiera C:\\Windows."
    )
    obs["por_que_podar_sigue_siendo_seguro"] = (
        "No depende de la inercia, que era el argumento malo. (1) MONOTONIA: "
        "`_dentro` es un OR sobre las raices y `_preparar` no reescribe las que "
        "sobreviven, asi que quitar un termino de un OR solo puede REDUCIR el "
        "conjunto aceptado. (2) Y mas fuerte todavia: con el codigo de antes un "
        "`Confinamiento` construido NUNCA pudo contener una raiz de unidad "
        "-`_preparar` lanzaba-, luego la poda no puede quitar un acceso que "
        "jamas llego a existir."
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

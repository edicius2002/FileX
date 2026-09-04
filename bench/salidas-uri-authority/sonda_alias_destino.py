"""N37 — el precio de C4, medido donde muerde: el cerrojo de destinos.

`filex/nucleo.py::_clave_destino` dice, en su propio docstring, que la clave
léxica no cierra el alias de ruta y enumera los que hay en Windows — «el nombre
corto 8.3, un `subst`, un enlace de directorio, **una UNC**»— y que la defensa
que sí los cierra es `_identidad_destino` (`st_dev`+`st_ino`). Esa defensa tiene
una condición escrita al lado: **sólo se puede consultar si el fichero EXISTE**,
«y por eso esta clave es *añadida* y no sustituye a la léxica: en el caso normal
el destino todavía no está».

El caso normal de un conversor es justo ése: **el destino todavía NO existe**.
Esta sonda mide si, en ese caso, las dos formas del mismo destino producen dos
dueños — que es la trampa 26 (dos peticiones a la misma ruta devolvían las dos
`ok`) reaparecida por un alias nuevo, y el coste concreto de admitir C4.

Control positivo incluido: el mismo par CON el fichero creado, donde la clave de
identidad sí debe igualarlos. Sin ese control, un «no coinciden» no distingue
«el alias no se cierra» de «la sonda no mira lo que cree».

Va en fichero por la TRAMPA 19 (el shell se come los backslashes).
"""

from __future__ import annotations

import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import nucleo as _nuc  # noqa: E402

DIR_LOCAL = os.path.join(RAIZ, "bench", "salidas-uri-authority")
DIR_UNC = "\\\\localhost\\D$" + DIR_LOCAL[2:] if DIR_LOCAL[1] == ":" else None
NOMBRE = "_alias_tmp.bin"


def main() -> int:
    if DIR_UNC is None:
        print(json.dumps({"error": "el árbol no está en una unidad con letra"}))
        return 1
    local = os.path.join(DIR_LOCAL, NOMBRE)
    unc = os.path.join(DIR_UNC, NOMBRE)

    out: dict = {
        "python": sys.version.split()[0],
        "ruta_local": local,
        "ruta_unc": unc,
        "el_unc_apunta_al_mismo_directorio": os.path.exists(DIR_UNC),
    }

    # --- Caso NORMAL de un conversor: el destino todavía no existe.
    if os.path.exists(local):
        os.remove(local)
    sin_fichero = {
        "clave_lexica_local": _nuc._clave_destino(local),
        "clave_lexica_unc": _nuc._clave_destino(unc),
        "identidad_local": _nuc._identidad_destino(local),
        "identidad_unc": _nuc._identidad_destino(unc),
        "claves_local": _nuc._claves_destino(local),
        "claves_unc": _nuc._claves_destino(unc),
    }
    sin_fichero["lexicas_coinciden"] = (
        sin_fichero["clave_lexica_local"] == sin_fichero["clave_lexica_unc"])
    sin_fichero["comparten_alguna_clave"] = bool(
        set(sin_fichero["claves_local"]) & set(sin_fichero["claves_unc"]))
    out["A_destino_que_NO_existe"] = sin_fichero

    # --- Control positivo: con el fichero creado, la identidad debe igualarlos.
    with open(local, "wb") as fh:
        fh.write(b"n37")
    try:
        con_fichero = {
            "clave_lexica_local": _nuc._clave_destino(local),
            "clave_lexica_unc": _nuc._clave_destino(unc),
            "identidad_local": _nuc._identidad_destino(local),
            "identidad_unc": _nuc._identidad_destino(unc),
        }
        con_fichero["lexicas_coinciden"] = (
            con_fichero["clave_lexica_local"] == con_fichero["clave_lexica_unc"])
        con_fichero["identidades_coinciden"] = (
            con_fichero["identidad_local"] is not None
            and con_fichero["identidad_local"] == con_fichero["identidad_unc"])
        out["B_control_positivo_destino_que_SI_existe"] = con_fichero
    finally:
        if os.path.exists(local):
            os.remove(local)

    a = out["A_destino_que_NO_existe"]
    out["VEREDICTO"] = (
        "DOS DUEÑOS en el caso normal" if not a["comparten_alguna_clave"]
        else "el alias queda cerrado también sin fichero")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

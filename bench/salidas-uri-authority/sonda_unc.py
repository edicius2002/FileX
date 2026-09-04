"""N37 — ¿es MEDIBLE una raíz UNC en esta máquina? Decide si C4 es escribible.

El candidato C4 («traducir la *authority* a UNC») no se puede elegir sobre una
traducción de cadenas: conceder confinamiento sobre `\\\\servidor\\recurso`
mete a FileX en un dominio —rutas UNC— donde NADA está medido (`realpath`, el
cerrojo de máquina de la trampa 33, los desechables de R18, `os.replace` entre
volúmenes). La trampa 80 lo dice al revés: antes de medir una propuesta, mira
si se puede sostener; si no, lo que estás midiendo es una decisión de
arquitectura.

Esta sonda sólo contesta a la pregunta previa: **¿hay aquí un recurso UNC sobre
el que medir?** Si la respuesta es no, C4 no se puede validar en esta máquina y
eso hay que decirlo, no deducirlo.

Va en fichero por la TRAMPA 19 (el shell se come los backslashes).
"""

import json
import os
import subprocess
import sys

CANDIDATOS = [
    "\\\\localhost\\D$",
    "\\\\localhost\\C$",
    "\\\\127.0.0.1\\D$",
    "\\\\localhost\\D$\\Work",
]


def main() -> int:
    filas = []
    for p in CANDIDATOS:
        f = {"ruta": p}
        try:
            f["exists"] = os.path.exists(p)
        except Exception as e:
            f["exists"] = "%s: %s" % (type(e).__name__, e)
        try:
            f["n_entradas"] = len(os.listdir(p))
        except Exception as e:
            f["n_entradas"] = "%s: %s" % (type(e).__name__, str(e)[:120])
        try:
            f["realpath"] = os.path.realpath(p)
        except Exception as e:
            f["realpath"] = "%s: %s" % (type(e).__name__, e)
        f["dirname_igual"] = os.path.dirname(os.path.normpath(p)) == os.path.normpath(p)
        filas.append(f)

    try:
        share = subprocess.run(["net", "share"], capture_output=True, text=True,
                               timeout=20, stdin=subprocess.DEVNULL)
        share_txt = share.stdout[:600]
    except Exception as e:
        share_txt = "%s: %s" % (type(e).__name__, e)

    hay = any(f.get("exists") is True for f in filas)
    print(json.dumps({
        "pregunta": "¿hay un recurso UNC accesible sobre el que medir C4?",
        "python": sys.version.split()[0],
        "hay_unc_accesible": hay,
        "filas": filas,
        "net_share": share_txt,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

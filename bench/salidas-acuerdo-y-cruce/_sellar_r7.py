# -*- coding: utf-8 -*-
"""Sella `filex/sondeo/<motor>.json` con los datos de UN RESONDEO real (no un
resellado por algoritmo -- trampa 44 de CLAUDE.md, y el encargo de la ronda 7
lo pide explicito): toma el JSON crudo que produjo la resonda de esta ronda
(motor/build/fecha/informe/aristas) y le anade `huella` (calculada AHORA,
sobre el codigo de esta rama) e `interprete` (la granularidad nueva de
`huella.interprete_actual()`, mayor.menor).

Uso: python _sellar_r7.py <motor> <crudo.json> <informe_md>
"""
from __future__ import annotations

import json
import sys
import time

RAIZ = "C:/Users/krato/orca/workspaces/FileX/filex-cpu"
sys.path.insert(0, RAIZ)

from filex import huella  # noqa: E402


def main() -> None:
    motor, crudo_p, informe = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(crudo_p, encoding="utf-8") as fh:
        crudo = json.load(fh)

    h = huella.de_motor_por_nombre(motor)
    interprete = huella.interprete_actual()
    destino = {
        "motor": crudo["motor"],
        "build": crudo["build"],
        "fecha": time.strftime("%Y-%m-%d"),
        "informe": informe,
        "huella": h,
        "interprete": interprete,
        "nota_huella": ("RESONDEADO (no resellado por algoritmo) el %s por "
                        "worker2, ronda 7: `C31` (ronda 6) cambio el "
                        "componente `contrato` -- FIRMAS (TGA/CUR) y `_datos` "
                        "(RAM) -- y `bench/salidas-huella/resellar.py "
                        "--comprobar` confirmo que la huella guardada NO "
                        "coincidia con el algoritmo anterior sobre el arbol de "
                        "ahora: no era un cambio de algoritmo, hacia falta "
                        "resondear. Las 62/70/8/16/16 aristas se remidieron de "
                        "verdad (FileX.convertir() real, contrato de cinco "
                        "puntos incluido), no se copio el JSON viejo con un "
                        "campo cambiado." % time.strftime("%Y-%m-%d")),
        "aristas": crudo["aristas"],
    }
    ruta = "filex/sondeo/%s.json" % motor
    with open(ruta, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(destino, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("sellado", ruta, "interprete=", interprete)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""K1 / hito 5 — ¿el tope DENTRO del contenedor mata de verdad al motor?

El hallazgo que motiva esto (`bench/hito5-documental.md` §4.4): **matar el
`docker run` no mata el contenedor**. Tres `soffice` colgados sobrevivieron 37
minutos a `taskkill /F /T` sobre el cliente y al `--rm`.

Aquí se reproduce el cuelgue **con la invocación del producto**
(`filex.motor_contenedor`) y se comprueba lo único que importa: que **no queda
ningún contenedor vivo** cuando la llamada vuelve.

    python bench/salidas-hito5/_tope.py
"""
from __future__ import annotations

import json
import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import invocacion, motor_contenedor as mc  # noqa: E402
from filex.trabajo import DirectorioDeTrabajo  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
ENT = os.path.join(AQUI, "entradas")
TOPE = 20   # el de producción son 110 s; aquí 20 para no tardar 2 minutos


def vivos(imagen: str) -> list:
    r = invocacion.ejecutar(["docker", "ps", "--filter", f"ancestor={imagen}",
                             "--format", "{{.Names}}"], timeout=60)
    return [x for x in (r.salida_txt or "").split() if x]


def main() -> int:
    for f in (sys.stdout, sys.stderr):
        try:
            f.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    e = mc.entorno()
    if not e["ok"]:
        print("sin entorno de contenedor:", e["motivo"])
        return 1
    imagen = e["imagen"]

    lo = mc.LibreOfficeEnContenedor()
    lo.sondear()
    mc.TIMEOUT_DENTRO = TOPE

    antes = vivos(imagen)
    t = DirectorioDeTrabajo(prefijo="filex-tope-")
    try:
        # `docx→txt` está marcada `nominal`, así que `orden()` se niega —y hace
        # bien—. Se construye el mismo `docker run` por la misma función del
        # producto para poder medir el mecanismo.
        argv = lo._argv_docker(
            os.path.join(ENT, "entrada.docx"), t.ruta, "salida.docx",
            ["soffice", "--headless", "--norestore", "--convert-to", "txt:Text",
             "--outdir", "/trabajo", "/ent/salida.docx"])
        t0 = time.perf_counter()
        # El tope de fuera, MUY por encima del de dentro: si vuelve antes, ha
        # sido `timeout` quien ha matado al motor, no `invocacion`.
        r = invocacion.ejecutar(argv, timeout=TOPE * 6, cwd=t.ruta)
        ms = (time.perf_counter() - t0) * 1000
        censo = t.censo()
        sobra = t.sobrantes(["salida.txt"])
    finally:
        t.cerrar()

    # Se comprueba INMEDIATAMENTE: el fallo consistía en sobrevivir a la llamada.
    despues = vivos(imagen)
    nuevos = [x for x in despues if x not in antes]

    out = {
        "tope_dentro_s": TOPE, "tope_fuera_s": TOPE * 6,
        "rc": r.rc, "ms": round(ms, 1), "agotado_fuera": r.agotado,
        "sobrantes": sobra,
        "contenedores_nuevos_vivos": nuevos,
        # GNU `timeout` devuelve 124 cuando dispara. Un rc distinto de 124 y no
        # agotado significaría que el motor terminó solo.
        "lo_mato_el_tope_de_dentro": r.rc == 124 and not r.agotado,
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    with open(os.path.join(AQUI, "tope.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return 0 if (out["lo_mato_el_tope_de_dentro"] and not nuevos) else 2


if __name__ == "__main__":
    raise SystemExit(main())

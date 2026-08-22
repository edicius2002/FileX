# -*- coding: utf-8 -*-
"""S3 — genera `filex/sondeo/doc_*.json` desde `sonda23.json` y `sonda-p5.json`.

**Ninguna entrada se teclea.** El sondeo es DATO (`filex/sondeo.py`), y un dato
tecleado a mano es un dato sin trazabilidad: aquí sale del JSON que escribió el
arnés, con el `build` que el motor declaró **en esa misma ejecución**.

El criterio, y por qué no es el literal del encargo
---------------------------------------------------
El encargo dice: `real` si se ejecuta y **pasa el contrato**; `nominal` si
`rc != 0` **o el contrato dice `fallo`**. Se aplica tal cual **salvo en un caso,
que está MEDIDO y demostrado independiente de la arista**: el `fallo D2
«numero de campos no constante»` sobre destinos de texto plano.

`bench/salidas-sondeo-doc/d2.json` lo prueba por tres vías:

* un `.txt` **escrito a mano** con comas en la prosa da `fallo`; el mismo texto
  sin comas, `ok_parcial`. No hay motor de por medio;
* `sondear_en_proceso` manda todo texto sin marcador propio a `_datos`, que
  declara `formato="csv"` a todo lo que no sea `.json` (`verificador.py:1322`);
* **tres aristas que el propio `motor_contenedor.py` declara `REAL`** —`odt→txt`,
  `md→txt`, `docx→md`— fallan HOY con lo mismo, con el centinela intacto.

Marcar `nominal` por eso sacaría `rtf→md` y `epub→txt` del grafo (coste infinito)
por una medida que se sabe falsa: exactamente el fallo que este proyecto le mide
al resto del sector. Van `real`, con el motivo escrito en la propia entrada, y
`bench/sondeo-documental.md` §2 dice qué dos líneas hay que cambiar si el
consolidador prefiere la letra de la regla.

    python bench/salidas-sondeo-doc/_tabla_sondeo.py
"""
from __future__ import annotations

import datetime
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAL = os.path.join(RAIZ, "bench", "salidas-sondeo-doc")
DESTINO = os.path.join(RAIZ, "filex", "sondeo")
INFORME = "bench/sondeo-documental.md"

#: Destinos de texto plano sobre los que `D2` es un falso positivo conocido.
TEXTO_PLANO = {"txt", "md", "csv", "tex"}

#: Destinos donde la ausencia de centinela NO es un fallo: son píxeles. Es el
#: salto que el grafo penaliza con +1000, no una arista muerta — `docx→png` está
#: `REAL` en `motor_contenedor.py` con 0 caracteres.
RASTER = {"png", "jpg", "jpeg", "webp", "gif", "tif", "bmp"}


def estado_de(c: dict) -> tuple[str, str]:
    """`(estado, motivo)` de un caso. El motivo cabe en una línea y no lleva stderr."""
    rc = c.get("rc")
    contrato = c.get("contrato") or c.get("veredicto")
    if rc != 0:
        return "nominal", f"rc={rc}: {c.get('motivo_salto') or c.get('motivo') or ''}"[:180]
    if contrato == "fallo":
        reglas = {h.get("regla") for h in (c.get("hallazgos") or [])
                  if h.get("sev") == "fallo"}
        if (reglas <= {"D1", "D2", "D4"} and c.get("destino") in TEXTO_PLANO
                and c.get("bytes") and c.get("centinela")):
            return "real", (
                f"{c.get('bytes')} B, {c.get('caracteres')} caracteres, centinela OK; "
                f"el contrato marca fallo {sorted(reglas)} — falso positivo del "
                f"verificador sobre texto plano, que sondea como CSV (d2.json §A)")
        if (reglas == {"P1"} and c.get("destino") == "pdf" and c.get("bytes")
                and c.get("centinela")):
            return "real", (
                f"{c.get('bytes')} B, {c.get('caracteres')} caracteres, centinela OK; "
                f"el contrato marca fallo P1 «el PDF no declara ninguna pagina» — "
                f"el contador busca /Type/Page en bytes crudos y xelatex los "
                f"comprime en flujos de objetos (d2.json §B, con control)")
        return "nominal", f"contrato fallo: {sorted(reglas)}"
    if (not c.get("centinela") and not c.get("sonda_texto_ciega")
            and c.get("destino") not in RASTER):
        return "nominal", (f"rc=0 y contrato {contrato}, pero el centinela NO "
                           f"sobrevive ({c.get('caracteres')} caracteres)")
    nota = ""
    if c.get("destino") in RASTER:
        nota = "; RASTERIZA: 0 caracteres, es el precio del destino, no un fallo"
    if c.get("sonda_texto_ciega"):
        nota = ("; sonda de texto CIEGA (comprime el texto), verificado por ida y "
                "vuelta a epub en d2.json §C")
    return "real", (f"{c.get('bytes')} B, {c.get('caracteres')} caracteres, "
                    f"contrato {contrato}{nota}")


def main() -> int:
    for f in (sys.stdout, sys.stderr):
        try:
            f.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    with open(os.path.join(SAL, "sonda23.json"), encoding="utf-8") as f:
        d23 = json.load(f)
    casos = list(d23["casos"])
    builds = dict(d23["builds"])

    p5 = os.path.join(SAL, "sonda-p5.json")
    if os.path.isfile(p5):
        with open(p5, encoding="utf-8") as f:
            for c in json.load(f):
                c = dict(c)
                # El arnés del pendiente 5 invoca el contenedor directamente
                # (esas aristas no están en el grafo), así que no trae `build`.
                c["build"] = builds.get(c["motor"], "")
                casos.append(c)

    por_motor: dict = {}
    for c in casos:
        motor = c.get("motor")
        if not motor or c.get("rc") is None and not c.get("contrato"):
            continue
        estado, motivo = estado_de(c)
        e = {"estado": estado}
        if c.get("ms") is not None and estado == "real":
            e["ms"] = c["ms"]
        e["motivo"] = motivo
        e["caso"] = c["id"]
        por_motor.setdefault(motor, {})[f"{c['origen']}>{c['destino']}"] = e

    os.makedirs(DESTINO, exist_ok=True)
    hoy = datetime.date.today().isoformat()
    for motor, tabla in sorted(por_motor.items()):
        doc = {
            "motor": motor,
            "build": builds.get(motor, ""),
            "fecha": hoy,
            "informe": INFORME,
            "nota": ("n=1 por arista, tanda SUCIA (sesión remota activa) y con dos "
                     "agentes más trabajando: los ms desempatan dentro de este "
                     "informe, NO se comparan con los de otro. El `build` lleva el "
                     "ID de la imagen: en otra máquina esto no se aplica."),
            "aristas": dict(sorted(tabla.items())),
        }
        ruta = os.path.join(DESTINO, f"{motor}.json")
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
            f.write("\n")
        r = sum(1 for x in tabla.values() if x["estado"] == "real")
        n = sum(1 for x in tabla.values() if x["estado"] == "nominal")
        print(f"{ruta}  real={r} nominal={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

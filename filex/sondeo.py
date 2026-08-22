"""El resultado de sondear una arista es DATO, no código.

Una tabla de aristas escrita a mano en el módulo del motor tiene dos problemas,
y el segundo es el grave:

1. **Coordinación.** Dos personas —o dos agentes— que sondean familias distintas
   editan el mismo fichero. Es el mismo motivo por el que los motores se
   descubren en vez de listarse.
2. **Y el que importa: una tabla tecleada no lleva su `build`.** La arista
   mínima viable es `(origen, destino, motor, parametrización, build)` —MEDIDO
   por dos carriles: `svg→png` con `magick` es **real en Windows y nominal
   (rc=1) en el Debian del contenedor**, y 19 de las 33 semiaristas muertas de
   ffmpeg son **codificadores no compilados**—. Una tabla que no sabe en qué
   build se midió **miente en la siguiente máquina**, y miente en silencio.

Por eso el sondeo vive en `filex/sondeo/<motor>.json`, con el `build` dentro, y
**una medida hecha en otro build no se aplica: se degrada a `sin_sondear`.**
Perder una medida buena por prudencia es barato; heredar una falsa, no.

Formato::

    {
      "motor": "imagemagick",
      "build":  "imagemagick 7.1.2-21",
      "fecha":  "2026-08-22",
      "informe": "bench/sondeo-aristas.md",
      "aristas": {
        "png>webp": {"estado": "real",    "ms": 265.0},
        "gif>ico":  {"estado": "nominal", "motivo": "rc=1: no such image format"}
      }
    }

`estado` es `real` o `nominal`, y **nada más**: `sin_sondear` es la ausencia de
entrada, no un valor que se escriba.

**Dos consecuencias de que el sondeo sea DATO, y las dos están medidas:**

1. **La suite de pruebas lee estado del disco, así que no es reproducible
   mientras se sondea.** OBSERVADO (`bench/sondeo-documental.md`): una pasada de
   las 88 falló una justo cuando el grafo pasó de 142 a 190 aristas `real`
   porque otro agente escribió su fichero a mitad; las dos siguientes, con el
   fichero ya en su sitio, dieron 88 en verde. No es un fallo de nadie: es la
   naturaleza del mecanismo. **PENDIENTE:** o las pruebas fijan su propio
   sondeo, o se declara que la suite no vale mientras se sondea.

2. **El sondeo caduca al cambiar el CÓDIGO de FileX, no solo el `build` del
   motor — y hoy esto NO se comprueba.** MEDIDO el 22/08: 21 aristas que un
   agente midió `nominal` quedaron obsoletas en cuanto se arreglaron la sonda y
   la invocación; al resondearlas, **20 de 21 salieron `real`**. El `build` de
   arriba protege contra cambiar de máquina; **nada protege contra cambiar de
   código**. **PENDIENTE:** meter una huella del código que decide la arista
   —`motores.py` y `verificador.py`— junto al `build`.
"""

from __future__ import annotations

import json
import os

from .grafo import NOMINAL, REAL, SIN_SONDEAR, Arista

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sondeo")

#: El coste base cuando el sondeo trae un tiempo. El tiempo DESEMPATA, no
#: decide: K1 midió que con el coste puesto al tiempo el grafo resuelve
#: `docx→pdf` como `docx→html→pdf` —la mitad de tiempo y peor conversión—.
#: Dividir por 100.000 deja el milisegundo en la cuarta cifra.
DIVISOR_MS = 100_000.0


def cargar(motor: str) -> dict:
    """Lo sondeado para un motor. `{}` si no hay fichero o está roto.

    Un JSON ilegible **no tumba el registro**: se ignora y el motor se queda
    con lo que traía. Misma regla que un binario que falta.
    """
    ruta = os.path.join(_DIR, f"{motor}.json")
    if not os.path.isfile(ruta):
        return {}
    try:
        with open(ruta, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def aplicar(motor: str, build: str, aristas: list[Arista]) -> list[Arista]:
    """Superpone el sondeo sobre las aristas que declara el motor.

    **Si el `build` del fichero no es el de ahora, no se aplica nada.** No es
    pedantería: es la quinta dimensión de la arista, y sin ella una tabla
    heredada de otra máquina afirma capacidades que aquí no existen.
    """
    d = cargar(motor)
    if not d:
        return aristas
    if d.get("build") and d["build"] != build:
        return aristas
    tabla = d.get("aristas") or {}
    if not tabla:
        return aristas

    informe = d.get("informe", "")
    out = []
    for a in aristas:
        e = tabla.get(f"{a.origen}>{a.destino}")
        if not isinstance(e, dict):
            out.append(a)
            continue
        estado = e.get("estado")
        if estado not in (REAL, NOMINAL):
            out.append(a)
            continue
        ms = e.get("ms")
        coste = a.coste if ms is None else 1.0 + float(ms) / DIVISOR_MS
        motivo = e.get("motivo", "")
        out.append(Arista(
            origen=a.origen, destino=a.destino, motor=a.motor,
            parametrizacion=a.parametrizacion, build=a.build,
            estado=estado, coste=coste, rasteriza=a.rasteriza,
            evidencia=(f"{informe}: {motivo}" if motivo else informe) or a.evidencia,
        ))
    return out


def resumen() -> dict:
    """`{motor: (real, nominal)}` de lo que hay sondeado en disco. Para la CLI."""
    out = {}
    if not os.path.isdir(_DIR):
        return out
    for n in sorted(os.listdir(_DIR)):
        if not n.endswith(".json"):
            continue
        d = cargar(n[:-5])
        t = (d.get("aristas") or {}).values()
        out[n[:-5]] = (sum(1 for x in t if x.get("estado") == REAL),
                       sum(1 for x in t if x.get("estado") == NOMINAL))
    return out


__all__ = ["aplicar", "cargar", "resumen", "REAL", "NOMINAL", "SIN_SONDEAR"]

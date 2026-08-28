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
      "huella": {"motor": "…", "invocacion": "…", "contrato": "…"},
      "aristas": {
        "png>webp": {"estado": "real",    "ms": 265.0},
        "gif>ico":  {"estado": "nominal", "motivo": "rc=1: no such image format"}
      }
    }

`estado` es `real` o `nominal`, y **nada más**: `sin_sondear` es la ausencia de
entrada, no un valor que se escriba.

**Dos consecuencias de que el sondeo sea DATO. Las dos están SALDADAS, y una de
las dos resultó no existir** (`bench/deuda-sondeo.md`):

1. ~~**La suite de pruebas lee estado del disco, así que no es reproducible
   mientras se sondea.**~~ **REFUTADA EN MAGNITUD — MEDIDO, cuatro pasadas de
   129 pruebas.** Con `_DIR` apuntando a un directorio VACÍO el grafo cae de
   **210 aristas `real` a 57** —se mueven 153— y la suite da **exactamente
   `123 passed, 6 skipped`**, lo mismo que con el disco intacto. Quitando solo
   las 5 entradas `nominal`, lo mismo otra vez. **0 de 129 pruebas dependen del
   estado del sondeo en disco**, porque las que miran tablas usan `_forzado()`,
   que no pasa por aquí, y las de integración solo necesitan que EXISTA un
   camino. Lo que sí las mueve —34 fallos— es declarar `nominal` las 215
   aristas, y eso ningún sondeo real lo produce.

   Queda `congelar()`, que cuesta una lectura por motor y cierra la ventana que
   sí existe: **un fichero que APARECE a mitad de pasada declarando aristas
   muertas**. Es el mecanismo que se OBSERVÓ el 22/08, cuando el grafo pasó de
   142 a 190 y una prueba de 88 falló. **La suite sí vale mientras se sondea; el
   cerrojo está por si el margen se estrecha.**

2. **El sondeo caduca al cambiar el CÓDIGO de FileX, no solo el `build` del
   motor.** MEDIDO el 22/08: 21 aristas que un agente midió `nominal` quedaron
   obsoletas en cuanto se arreglaron la sonda y la invocación; al resondearlas,
   **20 de 21 salieron `real`**. El `build` protege contra cambiar de máquina;
   nada protegía contra cambiar de código. **CERRADO:** el fichero lleva ahora
   un campo `huella` con tres componentes —`motor`, `invocacion`, `contrato`—
   que se comparan igual que el `build`, y **lo que no coincide no se aplica: se
   degrada a `sin_sondear`**. Qué se hashea, con qué granularidad y **qué NO
   protege** está en `filex/huella.py`.

   **Un fichero SIN `huella` se aplica igual, y se declara en `diagnostico()`.**
   No es un descuido: degradar por prudencia los cinco ficheros del disco
   costaba **153 aristas medidas con este mismo código**, y perder trabajo bueno
   por no saber leerlo no es prudencia. La regla de legado es transitoria — los
   cinco están sellados.
"""

from __future__ import annotations

import copy
import json
import os

from . import huella as _huella
from .grafo import NOMINAL, REAL, SIN_SONDEAR, Arista

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sondeo")

#: Instantánea del disco, o `None` si no se ha congelado. Ver `congelar()`.
_CONGELADO: dict | None = None

#: Lo que la última pasada de `aplicar()` tuvo que decidir sin protección o
#: contra la protección. Se LEE, no se escribe: es el canal por el que se entera
#: un humano —y `pruebas/test_sondeo.py`— de que hay sondeo que ya no vale.
_DIAG: dict = {"sin_huella": [], "caducados": {}, "build_distinto": []}

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
    if _CONGELADO is not None:
        return copy.deepcopy(_CONGELADO.get(motor, {}))
    return _del_disco(motor)


def _del_disco(motor: str) -> dict:
    ruta = os.path.join(_DIR, f"{motor}.json")
    if not os.path.isfile(ruta):
        return {}
    try:
        with open(ruta, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def congelar() -> dict:
    """Fija una instantánea del disco para el resto del proceso.

    El sondeo es DATO en disco y **otro agente puede escribir su fichero a mitad
    de una pasada**: se OBSERVÓ el 22/08, con el grafo pasando de 142 a 190
    aristas `real` y una prueba de 88 cayendo por ello.

    **No hace falta para la suite de hoy —MEDIDO: 0 de 129 pruebas dependen del
    disco—**, y por eso esto es un cerrojo que se pide, no un comportamiento por
    defecto: congelar por sistema escondería un sondeo recién escrito a quien
    quiere justamente eso, que es el caso normal de la CLI.
    """
    global _CONGELADO
    _CONGELADO = {}
    if os.path.isdir(_DIR):
        for n in sorted(os.listdir(_DIR)):
            if n.endswith(".json"):
                _CONGELADO[n[:-5]] = _del_disco(n[:-5])
    return {k: len((v.get("aristas") or {})) for k, v in _CONGELADO.items()}


def descongelar() -> None:
    global _CONGELADO
    _CONGELADO = None


def diagnostico() -> dict:
    """Qué se aplicó sin protección, y qué se degradó por caducidad.

    ``sin_huella``      motores cuyo fichero es anterior a la huella: se aplican
                        por la regla de legado, **sin protección de código**.
    ``caducados``       `{motor: [componentes]}` que NO se aplicaron.
    ``build_distinto``  los que ya se degradaban antes, por la quinta dimensión.
    """
    return copy.deepcopy(_DIAG)


def aplicar(motor: str, build: str, aristas: list[Arista],
            huella_actual: dict | None = None) -> list[Arista]:
    """Superpone el sondeo sobre las aristas que declara el motor.

    Dos guardas, y las dos degradan a `sin_sondear` en vez de a `nominal`: una
    medida que ya no vale **no es prueba de que la arista esté muerta**.

    1. **Si el `build` del fichero no es el de ahora, no se aplica nada.** Es la
       quinta dimensión de la arista, y sin ella una tabla heredada de otra
       máquina afirma capacidades que aquí no existen.
    2. **Si la `huella` del código que decide la arista no es la de ahora,
       tampoco.** Es la sexta, y su ausencia costó 20 medidas falsas de 21.

    `huella_actual` se inyecta para poder PROBARLO sin editar `motores.py` a
    mitad de una prueba. En producción lo calcula el propio motor.
    """
    _DIAG["sin_huella"] = [m for m in _DIAG["sin_huella"] if m != motor]
    _DIAG["caducados"].pop(motor, None)
    _DIAG["build_distinto"] = [m for m in _DIAG["build_distinto"] if m != motor]

    d = cargar(motor)
    if not d:
        return aristas
    if d.get("build") and d["build"] != build:
        _DIAG["build_distinto"].append(motor)
        return aristas

    guardada = d.get("huella")
    if not isinstance(guardada, dict) or not guardada:
        # REGLA DE LEGADO. Se aplica —degradar costaba 153 aristas medidas con
        # este mismo código— y se DECLARA, que es lo que la convierte en una
        # decisión en vez de en el agujero que veníamos a tapar.
        _DIAG["sin_huella"].append(motor)
    else:
        if huella_actual is None:
            huella_actual = _huella.de_motor_por_nombre(motor)
        malos = _huella.diferencias(guardada, huella_actual)
        if malos:
            _DIAG["caducados"][motor] = malos
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

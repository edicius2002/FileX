"""N35 — el eje que DECIDE: que le llega al consumidor, en dos superficies.

`sonda_candidatos.py` deja la tabla de LECTURA, y esa tabla no decide: sobre
los cuatro objetivos, los candidatos B (podar), C (podar sin guarda) y E
(aceptar la raiz de unidad) aciertan las 8 filas los tres. Es una meseta
(trampa 51), y el borde hay que buscarlo en otro eje.

El eje es lo que el constructor le DICE al consumidor, porque la fuga de ayer
(N7) no la produjo una raiz demasiado ancha —`sonda_mecanismo.py` demuestra
que la raiz de unidad es INERTE y no concede nada— sino el par

    fx.confinamiento is None   +   sin_acceso == False

que en `nucleo.py::_resolver` es literalmente `return os.path.abspath(entrada)`:
sin confinamiento, acceso total. Asi que la pregunta que decide N35 no es
«¿que lee?» sino «¿que par (sin_acceso, confinamiento) produce cada candidato?».

DOS SUPERFICIES, porque la trampa 26 mide lo que cuesta mirar una sola: el
mismo agujero llevaba desde el hito 1 en las cuatro y hizo falta la cuarta
para verlo.

  * NUCLEO — `FileX._resolver()`, la via de CLI, watcher y API HTTP.
  * MCP    — `Raices.asegurar()` con un doble de sesion, la via del cliente
             que declara sus roots.

Salida: bench/salidas-raices-mixtas/superficies.json
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)

import anyio  # noqa: E402

from filex import confinamiento as _conf  # noqa: E402
from filex import mcp as M  # noqa: E402
from filex.confinamiento import Denegado  # noqa: E402
from filex.nucleo import FileX  # noqa: E402

from sonda_candidatos import (CANDIDATOS, CLAVES, construir_escenario)  # noqa: E402


# ------------------------------------------------------- doble de sesion MCP

class _Raiz:
    def __init__(self, uri: str) -> None:
        self.uri = uri


class _Resultado:
    def __init__(self, roots) -> None:
        self.roots = roots


class SesionFalsa:
    """Doble minimo de la sesion MCP: solo `list_roots`, siempre con exito.

    Aqui no se mide concurrencia —eso es N34, ya cerrado—, asi que no hace
    falta el punto de suspension de la trampa 114; se deja el `await` de todas
    formas para que la corrutina ceda como cederia la de verdad.
    """

    def __init__(self, raices) -> None:
        self._raices = list(raices)
        self.llamadas = 0

    @staticmethod
    def _uri(r: str) -> str:
        """Construye la URI como la construiria un cliente, incluida la UNC.

        CORREGIDO tras `sonda_unc.py`: la primera version hacia siempre
        `"file:///" + ruta`, y sobre una UNC `\\servidor\recurso` eso da
        `file://///servidor/recurso` -CINCO barras- que vuelve como
        `\\\servidor\recurso`, una ruta DEFORMADA que ya no es raiz de
        recurso y por tanto si confina. La fila 7 de la superficie MCP no
        estaba midiendo una UNC: medía un artefacto de este doble, y el
        candidato A salia «ok» ahi por ese motivo (trampa 38/91: el arnes
        mataba a su sujeto y el resultado parecia el bueno).
        """
        if r.startswith("\\\\"):
            return "file://" + r.replace(os.sep, "/")
        return "file:///" + r.replace(os.sep, "/")

    async def list_roots(self):
        self.llamadas += 1
        await anyio.sleep(0)
        return _Resultado([_Raiz(self._uri(r)) for r in self._raices])


# ------------------------------------------------------------------ medidas

def _lee_por_el_nucleo(fx, objetivos, dir_salida) -> dict:
    """Pregunta a `FileX._resolver()`, que es lo que usan CLI/watcher/API."""
    lee = {}
    for nombre, ruta in objetivos.items():
        if not os.path.exists(ruta):
            lee[nombre] = None
            continue
        try:
            fx._resolver(ruta, os.path.join(dir_salida, "salida.txt"))
            lee[nombre] = True
        except Denegado:
            lee[nombre] = False
    return lee


def medir_nucleo(cls, raices, fx, objetivos, dir_salida) -> dict:
    """Superficie NUCLEO: el confinamiento se construye y se instala a mano.

    Reproduce lo que hace `FileX.__init__` (`nucleo.py:591`) sin volver a
    sondear los motores, que cuesta segundos y no interviene aqui.
    """
    celda = {}
    try:
        conf = cls(raices)
    except ValueError as e:
        # El nucleo NO captura este `ValueError` (comprobado, no supuesto:
        # `nucleo.py:591` construye sin `except`), asi que FileX no arranca.
        celda["constructor"] = "ValueError"
        celda["mensaje"] = str(e)
        celda["confinamiento_es_None"] = None
        celda["filex_arranca"] = False
        celda["lee"] = {k: False for k in objetivos}
        return celda
    celda["constructor"] = "ok"
    celda["confinamiento_es_None"] = False
    celda["filex_arranca"] = True
    celda["raices_efectivas"] = list(conf.lectura)
    previo = fx.confinamiento
    try:
        fx.confinamiento = conf
        celda["lee"] = _lee_por_el_nucleo(fx, objetivos, dir_salida)
    finally:
        fx.confinamiento = previo
    return celda


def medir_mcp(cls, raices, fx, objetivos, dir_salida) -> dict:
    """Superficie MCP: `Raices.asegurar()` con el candidato inyectado.

    Se sustituye `filex.confinamiento.Confinamiento` porque `mcp.py` lo llama
    por el modulo (`_conf.Confinamiento(efectivas)`), y se restaura siempre.
    """
    celda = {}
    original = _conf.Confinamiento
    previo = fx.confinamiento
    try:
        _conf.Confinamiento = cls
        gestor = M.Raices(fx, None)      # sin `--raiz`: manda el cliente
        gestor.sin_acceso = False        # lo que hace `construir()` (mcp.py:610)
        sesion = SesionFalsa(raices)
        anyio.run(gestor.asegurar, sesion)
        celda["sin_acceso"] = gestor.sin_acceso
        celda["confinamiento_es_None"] = fx.confinamiento is None
        celda["resuelto_sellado"] = gestor._resuelto
        celda["llamadas_a_list_roots"] = sesion.llamadas
        if fx.confinamiento is not None:
            celda["raices_efectivas"] = list(fx.confinamiento.lectura)
        # Lo que de verdad leeria una herramienta MCP: `sin_acceso` corta antes
        # de tocar el nucleo, asi que se modela igual que la superficie.
        if gestor.sin_acceso:
            celda["lee"] = {k: False for k in objetivos}
            celda["nota"] = "sin_acceso corta antes de llegar al nucleo"
        else:
            celda["lee"] = _lee_por_el_nucleo(fx, objetivos, dir_salida)
    except Exception as e:  # noqa: BLE001
        celda["error"] = "%s: %s" % (type(e).__name__, e)
        celda["lee"] = {k: None for k in objetivos}
    finally:
        _conf.Confinamiento = original
        fx.confinamiento = previo
    return celda


def veredicto(celda, esperado) -> str:
    """Clasifica cada celda en las cuatro categorias que importan."""
    lee = celda.get("lee", {})
    if any(v is None for v in lee.values()):
        return "indeterminado"
    de_mas = [k for k, v in esperado.items() if v and not lee.get(k)]
    de_menos = [k for k, v in esperado.items() if (not v) and lee.get(k)]
    if de_menos:
        return "FUGA"                    # lee algo que no debe
    if de_mas:
        return "DENIEGA_DE_MAS"          # pierde acceso legitimo: es N35
    # Correcto en acceso. Queda el matiz de honestidad, solo visible en MCP.
    if celda.get("sin_acceso") is False and not any(lee.values()):
        return "ok_pero_MIENTE"          # dice que tiene acceso y no lee nada
    return "ok"


def main() -> int:
    base = tempfile.mkdtemp(prefix="filex-n35-sup-")
    esc = construir_escenario(base)
    legit = esc["legit"]
    objetivos = esc["objetivos"]
    dir_salida = os.path.join(base, "legit")

    filas = {
        "1_solo_legitima_CONTROL": [legit],
        "2_solo_raiz_de_unidad_N7": ["C:\\"],
        "3_MIXTA_N35": ["C:\\", legit],
        "7_MIXTA_con_UNC": [r"\\servidor\recurso", legit],
    }
    esperados = {}
    for nombre, raices in filas.items():
        declara = any(_conf._norm(os.path.abspath(r)) ==
                      _conf._norm(os.path.abspath(legit)) for r in raices)
        esperados[nombre] = {CLAVES[0]: declara, CLAVES[1]: False,
                             CLAVES[2]: False, CLAVES[3]: False}

    print("construyendo FileX (sondea motores, tarda)...", flush=True)
    fx = FileX()
    fx.confinamiento = None

    res = {"plataforma": sys.platform, "python": sys.version.split()[0],
           "base_desechable": base, "objetivos": objetivos,
           "esperado_por_fila": esperados, "celdas": {}}

    for nombre_fila, raices in filas.items():
        res["celdas"][nombre_fila] = {}
        for nombre_c, cls in CANDIDATOS.items():
            n = medir_nucleo(cls, raices, fx, objetivos, dir_salida)
            m = medir_mcp(cls, raices, fx, objetivos, dir_salida)
            n["veredicto"] = veredicto(n, esperados[nombre_fila])
            m["veredicto"] = veredicto(m, esperados[nombre_fila])
            res["celdas"][nombre_fila][nombre_c] = {"nucleo": n, "mcp": m}

    destino = os.path.join(AQUI, "superficies.json")
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)

    for superficie in ("nucleo", "mcp"):
        print("\n=== superficie: %s ===" % superficie.upper())
        print("%-26s %s" % ("fila", "  ".join("%-20s" % c for c in CANDIDATOS)))
        for nombre_fila in filas:
            fila = []
            for nombre_c in CANDIDATOS:
                c = res["celdas"][nombre_fila][nombre_c][superficie]
                extra = ""
                if superficie == "mcp":
                    extra = " sa=%s cN=%s" % (c.get("sin_acceso"),
                                              c.get("confinamiento_es_None"))
                fila.append("%-20s" % (c["veredicto"] + extra))
            print("%-26s %s" % (nombre_fila, "  ".join(fila)))

    print("\n-> %s" % destino)
    print("base desechable: %s" % base)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Lista blanca de raíces. Denegar por defecto. Predicado léxico antes del disco.

Las reglas y su evidencia están en `RESULTADOS-MCP.md` §10 (18 reglas). Aquí van
las que el hito 1 necesita; las que faltan se nombran en su sitio.

**R10 es la que decide dónde vive este módulo: la validación está en el NÚCLEO,
no en la superficie.** La CLI de kordoc ignora su propia variable de
confinamiento porque la validación vivía en su capa MCP. FileX va a tener cuatro
superficies —CLA, MCP, watcher y API HTTP— y ninguna puede llevar su propia copia.
"""

from __future__ import annotations

import os
import sys
import time

#: R4: el MISMO mensaje para «prohibido» y para «no existe». Sin ruta, sin ruta
#: resuelta, sin lista blanca. Tres fugas distintas se midieron por no hacerlo.
#: (Y la equivalencia de latencia entre los dos casos es PENDIENTE: hoy el
#: camino de «no existe» puede ser más corto y eso es un oráculo temporal.)
MENSAJE_OPACO = "ruta no accesible"

#: R17: `realpath` es un vector de DoS. Una ruta de ~6.000 componentes cuesta
#: 5-16 s. Los topes son LÉXICOS y van ANTES de tocar el disco.
MAX_COMPONENTES = 64
MAX_LONGITUD = 4096

#: N9: el oráculo temporal de R4 (trampa 28, `bench/hito7-superficies.md` §7.2).
#: «Prohibido» corta en el predicado léxico (R1) y nunca paga el `realpath`;
#: «no existe»/«existe» sí lo pagan. La decisión —tomada por superficie, no
#: aquí— está en `bench/oraculo-y-gotenberg.md` §1: sólo la API HTTP tiene un
#: adversario capaz de cronometrar (un navegador, vía DNS-rebinding, con
#: `fetch()`+`performance.now()`); CLI, watcher y MCP son de confianza local y
#: pagar el suelo ahí sería puro coste. Por eso esto es un PARÁMETRO del
#: constructor, no una constante global: quien construye `Confinamiento` decide
#: si lo paga. El valor sale de medir ESTA máquina —n=2000 por celda,
#: `bench/salidas-oraculo-n9/resultado.json`—, no de las cifras de
#: `hito7-superficies.md`, que son de otra (`D:`, no `C:`) y no comparables en
#: absoluto. `no_existe` da 161,95 µs de mediana y 271,19 µs de p90 bajo carga
#: (worker1 en el carril GPU); el suelo se pone con margen sobre eso.
PISO_TEMPORAL_S = 0.0003

#: MEDIDO en esta máquina (control de 6 objetivos, 200 repeticiones cada uno,
#: `bench/oraculo-y-gotenberg.md` §1.3): `time.sleep()` en Windows no baja de
#: ~1 ms de mediana real sin importar si se le pide 10 µs o 500 µs -- dormir
#: para un suelo de cientos de µs lo sobrepasaría por 3-10×, que es más caro
#: que la propia asimetría que se quiere cerrar. Por debajo de este umbral se
#: espera con un spin (`time.perf_counter()` en bucle), no con `sleep()`: el
#: coste de CPU de menos de un milisegundo de spin es despreciable frente al
#: coste de dormir de más.
_UMBRAL_SLEEP_FIABLE_S = 0.002

_ES_WINDOWS = sys.platform == "win32"


def _esperar_piso(inicio: float) -> None:
    """Espera hasta `PISO_TEMPORAL_S` desde `inicio` (un `time.perf_counter()`).

    Por debajo de `_UMBRAL_SLEEP_FIABLE_S`, con SPIN — ver la nota de
    `_UMBRAL_SLEEP_FIABLE_S`: `time.sleep()` en esta máquina no es fiable a
    esta escala. Por encima (no debería ocurrir con el `PISO_TEMPORAL_S` de
    hoy, pero la función es correcta si alguien lo sube), cede la CPU con
    `time.sleep()` para el grueso y termina en spin el último tramo.
    """
    objetivo = inicio + PISO_TEMPORAL_S
    if PISO_TEMPORAL_S > _UMBRAL_SLEEP_FIABLE_S:
        resto = objetivo - time.perf_counter() - _UMBRAL_SLEEP_FIABLE_S
        if resto > 0:
            time.sleep(resto)
    while time.perf_counter() < objetivo:
        pass

#: R12: nombres reservados de Windows. `CON.txt` sigue siendo `CON`.
_RESERVADOS = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


class Denegado(Exception):
    """Lo único que sale de aquí cuando algo no se permite. Sin detalles."""

    def __init__(self) -> None:
        super().__init__(MENSAJE_OPACO)


def _norm(p: str) -> str:
    """R3: `normcase` para que la comparación no dependa de mayúsculas ni de
    la barra. Cinco falsos negativos medidos en Windows por saltárselo."""
    return os.path.normcase(os.path.normpath(p))


def nombre_seguro(nombre: str) -> bool:
    """R12: normalizar el nombre de salida.

    Prohíbe flujos alternativos (ADS), nombres reservados, y puntos o espacios
    finales. **W9 concedió acceso a un ADS** en un servidor de referencia.
    """
    if not nombre or nombre in (".", ".."):
        return False
    if os.sep in nombre or (os.altsep and os.altsep in nombre):
        return False
    if _ES_WINDOWS:
        if ":" in nombre:                       # ADS: `fichero.txt:oculto`
            return False
        if nombre[-1] in ". ":                  # `fichero.` abre `fichero`
            return False
        if nombre.split(".")[0].upper() in _RESERVADOS:
            return False
    return True


class Confinamiento:
    """R6: denegar por defecto. Sin ninguna raíz accesible, no se arranca."""

    def __init__(self, raices_lectura, raices_escritura=None, *,
                 ecualizar_temporal: bool = False) -> None:
        self.lectura = self._preparar(raices_lectura)
        # R9: raíz de lectura != raíz de escritura. Una sola lista para todas
        # las operaciones fue lo que dejó a `write_file` destruir un fichero.
        self.escritura = self._preparar(raices_escritura if raices_escritura is not None
                                        else raices_lectura)
        if not self.lectura:
            raise ValueError("sin raíces de lectura accesibles: FileX no arranca (R6)")
        # N9: ver PISO_TEMPORAL_S. Por defecto False: CLI/watcher/MCP no pagan
        # nada por un adversario que no tienen.
        self.ecualizar_temporal = ecualizar_temporal

    @staticmethod
    def _preparar(raices) -> list[str]:
        out = []
        for r in raices or []:
            a = _norm(os.path.abspath(r))
            # R3: una raíz que normaliza a la raíz de una unidad no confina nada.
            padre = os.path.dirname(a)
            if padre == a:
                raise ValueError("una raíz no puede ser la raíz de una unidad (R3)")
            out.append(a)
        return out

    # ---------------------------------------------------------------- léxico

    def _lexico_ok(self, ruta: str) -> bool:
        """R1 + R17: todo lo que se puede decidir SIN tocar el disco, primero."""
        if not ruta or len(ruta) > MAX_LONGITUD:
            return False
        if ruta.count(os.sep) + (ruta.count(os.altsep) if os.altsep else 0) > MAX_COMPONENTES:
            return False
        if "\x00" in ruta:
            return False
        # R12 sobre CADA COMPONENTE de la ruta, no solo sobre el nombre de
        # salida. `nombre_seguro` estaba escrito y probado desde el hito 1 y
        # **no lo llamaba nadie más que la propia prueba**: W9 —el único de los
        # 29 vectores que la referencia oficial concede— seguía abierto aquí,
        # en el núcleo de FileX, tres líneas debajo del comentario que dice que
        # la validación vive en el núcleo. MEDIDO (`bench/hito4-mcp.md` §8):
        # `inspect` devolvía 72 B de `dentro.png:oculto`, bytes distintos de los
        # del fichero validado.
        resto = os.path.splitdrive(os.path.abspath(ruta))[1]
        if os.altsep:
            resto = resto.replace(os.altsep, os.sep)
        for comp in resto.split(os.sep):
            if comp in ("", ".", ".."):
                continue
            if not nombre_seguro(comp):
                return False
        return True

    def _dentro(self, candidato: str, raices: list[str]) -> bool:
        """R2: comparar por SEGMENTOS, nunca por prefijo de cadena.

        Sin el `+ os.sep`, la raíz `permitido` deja pasar `permitido_secreto`.
        """
        c = _norm(candidato)
        for r in raices:
            if c == r or c.startswith(r + os.sep):
                return True
        return False

    # --------------------------------------------------------------- público

    def resolver(self, ruta: str, *, escritura: bool = False) -> str:
        """Devuelve la ruta absoluta y resuelta, o lanza `Denegado`.

        R7: se resuelven los enlaces **en cada llamada** y se valida la ruta
        RESUELTA, no la pedida. En Linux esto debería ser además `O_NOFOLLOW` +
        `dir_fd` segmento a segmento; **PENDIENTE**, y en Windows no existe
        ninguno de los dos primitivos (MEDIDO). Nada de esto sustituye al
        staging de R8: lo complementa.

        N9: si `self.ecualizar_temporal`, TODA salida —la excepción incluida—
        espera hasta `PISO_TEMPORAL_S` desde la entrada. Es un `try/finally`
        alrededor del método entero, no de cada `raise`, para que ningún
        camino nuevo que se añada aquí en el futuro se cuele sin pagarlo.
        """
        if not self.ecualizar_temporal:
            return self._resolver_sin_ecualizar(ruta, escritura=escritura)
        inicio = time.perf_counter()
        try:
            return self._resolver_sin_ecualizar(ruta, escritura=escritura)
        finally:
            _esperar_piso(inicio)

    def _resolver_sin_ecualizar(self, ruta: str, *, escritura: bool = False) -> str:
        if not self._lexico_ok(ruta):
            raise Denegado()
        raices = self.escritura if escritura else self.lectura
        if not raices:
            raise Denegado()

        # Predicado léxico ANTES de tocar el disco (R1). Si ya falla aquí, no
        # se paga el `realpath` y no hay oráculo de existencia que filtrar.
        if not self._dentro(os.path.abspath(ruta), raices):
            raise Denegado()

        try:
            resuelta = os.path.realpath(ruta)
        except OSError:
            raise Denegado() from None

        # Y otra vez sobre la RESUELTA: es lo que cierra el enlace simbólico.
        if not self._dentro(resuelta, raices):
            raise Denegado()
        return resuelta

    def puede_leer(self, ruta: str) -> bool:
        try:
            self.resolver(ruta)
            return True
        except Denegado:
            return False

"""Lista blanca de raíces. Denegar por defecto. Predicado léxico antes del disco.

Las reglas y su evidencia están en `RESULTADOS-MCP.md` §10 (18 reglas). Aquí van
las que el hito 1 necesita; las que faltan se nombran en su sitio.

**R10 es la que decide dónde vive este módulo: la validación está en el NÚCLEO,
no en la superficie.** La CLI de kordoc ignora su propia variable de
confinamiento porque la validación vivía en su capa MCP. FileX va a tener cuatro
superficies —CLA, MCP, watcher y API HTTP— y ninguna puede llevar su propia copia.
"""

from __future__ import annotations

import contextlib
import os
import sys
import threading
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
#: absoluto. Según ESE artefacto, `no_existe` sin ecualizar da **234,95 µs de
#: mediana y 364,65 µs de p90** bajo carga (worker1 en el carril GPU).
#:
#: **Corregido por el maestro al verificar la ronda 10:** este comentario
#: citaba «161,95 µs de mediana y 271,19 µs de p90» y concluía que el suelo se
#: ponía «con margen sobre eso». Esas cifras **no están en el `resultado.json`
#: versionado** —son de otra tanda que no se guardó—, y con las que sí lo están
#: la conclusión es FALSA: 300 µs queda **por debajo** de un p90 de 364,65.
#: Trampa 55 dentro de la 44 — una nota falsa justificando la constante.
#:
#: Lo que este suelo hace de verdad, MEDIDO: cierra el oráculo **a la mediana**
#: (ratio `no_existe/prohibido` 17,53× → 1,00×) y **no cierra la cola** — ya
#: ecualizado, el p90 de `no_existe` es 582,19 µs frente a 308,60 del camino
#: denegado, o sea **1,88× a p90**. Un atacante que promedie muchas muestras
#: sigue viendo esa diferencia.
#:
#: **Subir el suelo por encima del p90 es una DECISIÓN que exige volver a
#: medir, y no se toma aquí** (`N32`): sube el coste del rechazo, que es justo
#: el amplificador de DoS que la trampa 28 nombra.
#:
#: **`N32`, decidido — MEDIDO el 03/09/2026 en esta máquina, 5 tandas
#: independientes** (`bench/salidas-suelo-n32/`): el p90 de `no_existe` sin
#: ecualizar del que partía la cola de 1,88× (582,19 µs) era de una tanda
#: `SUCIA` (CPU compartida con otro carril). Sobre **5 tandas frescas**, el
#: mismo p90 da **181,77 / 325,89 / 247,70 / 335,09 / 242,69 µs** — todas por
#: debajo del suelo actual salvo una casi empatada — y el ratio p90
#: `no_existe/prohibido` YA ECUALIZADO con el suelo de HOY (300 µs) da **0,94
#: / 1,26 / 1,32 / 1,01 / 0,99**: mediana de las 5 tandas ≈ 1,01. **La cola de
#: 1,88× no reproduce hoy: era de la tanda, no del suelo.** Subir el suelo a
#: 500 µs (margen sobre el peor p90 fresco, 335,09) no mejora esa ratio
#: (0,995 frente a 1,003 con 300 µs — dentro del ruido) y **cuesta ×1,666 en
#: CADA rechazo real** (301,30 → 502,00 µs de mediana,
#: `resultado_suelo_alto.json`): el amplificador de DoS de la trampa 28, sin
#: beneficio medible. **No se sube.** Lo que SÍ se cierra es el residuo
#: estructural (no depende del ruido: es aritmético) que
#: `bench/oraculo-y-gotenberg.md` §1.5 dejó `PENDIENTE` — `existe/prohibido =
#: 2,11× (mediana) / 2,15× (p90)` porque `FileX._resolver()` paga el suelo dos
#: veces (entrada + directorio de salida) en la vía válida y una sola en la
#: denegada en la entrada. Se implementa un suelo POR OPERACIÓN
#: (`Confinamiento.operacion()`, usado por `FileX._resolver()`): la vía válida
#: paga UN suelo, no dos. **Verificado sobre 4 tandas** a nivel de
#: `FileX.convertir()` (`bench/salidas-suelo-n32/resultado_operacion.json`,
#: la última): el ratio `existe/prohibido` baja a **1,09–1,25× de mediana y
#: 1,11–1,77× de p90** (las cuatro tandas, frente a 2,11×/2,15× de antes), y
#: el coste mediano de la vía válida BAJA de 659,55 a **348–386 µs** —
#: aproximadamente la mitad, porque ahora paga un piso en vez de dos— sin que
#: el coste de la vía denegada se mueva (312,50 → 307–324 µs, dentro del
#: ruido). **No cierra del todo a p90 en las cuatro tandas** (mejor caso
#: 1,11×, peor 1,77×) pero sí de forma consistente y grande frente al 2,15×
#: de origen, y sin el coste de subir el suelo global.
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


def _ruta_real_de_fd(fd: int) -> str:
    """La ruta REAL de lo que `fd` tiene abierto — del descriptor, no de una cadena.

    Linux: `/proc/self/fd/<fd>` es un enlace mágico al inodo abierto; leerlo da
    la ruta real actual (trampa 45: `/proc/<pid>/fd` es el primitivo POSIX del
    proyecto). Windows: `GetFinalPathNameByHandle` sobre el `HANDLE` del `fd`.
    """
    if not _ES_WINDOWS:
        return os.readlink(f"/proc/self/fd/{fd}")
    # Windows: no hay /proc. Se pide la ruta final canónica del HANDLE.
    import ctypes
    from ctypes import wintypes
    import msvcrt
    handle = msvcrt.get_osfhandle(fd)
    GetFinalPathNameByHandleW = ctypes.windll.kernel32.GetFinalPathNameByHandleW
    GetFinalPathNameByHandleW.restype = wintypes.DWORD
    GetFinalPathNameByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR,
                                          wintypes.DWORD, wintypes.DWORD]
    buf = ctypes.create_unicode_buffer(4096)
    n = GetFinalPathNameByHandleW(handle, buf, 4096, 0)  # 0 = FILE_NAME_NORMALIZED|VOLUME_NAME_DOS
    if n == 0 or n >= 4096:
        raise OSError("GetFinalPathNameByHandle falló")
    real = buf.value
    # Quita el prefijo extendido `\\?\` que Windows antepone; deja `C:\...` o
    # `\\servidor\...` (UNC llega como `\\?\UNC\servidor\...`).
    if real.startswith("\\\\?\\UNC\\"):
        real = "\\\\" + real[len("\\\\?\\UNC\\"):]
    elif real.startswith("\\\\?\\"):
        real = real[len("\\\\?\\"):]
    return real


def _ruta_estable_para_motor(fd: int, real: str) -> str:
    """La ruta que se le entrega al motor externo, que la REABRE por ruta.

    Linux: `/proc/<pid>/fd/<fd>` — MEDIDO (`bench/toctou-fd.md`): otro proceso
    que la abre alcanza el INODO FIJADO, no re-traversa la ruta original, así
    que la conmutación del atacante ya no cambia lo que el motor lee. `cat`,
    `magick` y `ffmpeg` la aceptan.

    Windows: no hay ruta mágica estable; se devuelve la ruta real validada. El
    motor la reabre y la ventana de reapertura por ruta queda cubierta por el
    bloqueo del sistema, no por esta función (ver `abrir_confinado`). PENDIENTE.
    """
    if not _ES_WINDOWS:
        return f"/proc/{os.getpid()}/fd/{fd}"
    return real


class _EntradaConfinada:
    """El `fd` validado de una entrada + la ruta ESTABLE que se le da al motor.

    Gestor de contexto: el `fd` se mantiene abierto mientras el motor lee (en
    Linux, cerrarlo invalida `/proc/<pid>/fd/<fd>`) y se cierra al salir del
    `with` o con `.cerrar()`.
    """

    __slots__ = ("fd", "ruta", "real")

    def __init__(self, fd: int, ruta: str, real: str) -> None:
        self.fd = fd
        self.ruta = ruta
        self.real = real

    def __enter__(self) -> "_EntradaConfinada":
        return self

    def __exit__(self, *exc) -> None:
        self.cerrar()

    def cerrar(self) -> None:
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None


class _EntradaPassthrough:
    """Sin confinamiento (`confinamiento is None`): la ruta absoluta, tal cual.

    Preserva el comportamiento previo —el motor recibía `os.path.abspath(entrada)`—
    para las superficies o pruebas que construyen `FileX` sin lista blanca.
    """

    __slots__ = ("fd", "ruta", "real")

    def __init__(self, ruta: str) -> None:
        self.fd = None
        self.ruta = ruta
        self.real = ruta

    def __enter__(self) -> "_EntradaPassthrough":
        return self

    def __exit__(self, *exc) -> None:
        pass

    def cerrar(self) -> None:
        pass


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
        # N35: la guarda R6 de arriba mira SOLO la lectura, y desde que
        # `_preparar` poda en vez de rechazar hay un camino nuevo hasta
        # `escritura == []` — declarar raíces de escritura y que la poda se las
        # lleve todas. Se separa «no declaré escritura» (lista vacía o `None`:
        # es legítimo, significa solo-lectura o heredar la de lectura) de
        # «declaré escritura y ninguna confina», que es la trampa 43: toda
        # detección por ausencia tiene que separar «no se puede» de «no está».
        # MEDIDO (`bench/salidas-raices-mixtas/escritura.json`): sin esto, el
        # caso pasa de `ValueError` a denegar toda la escritura EN SILENCIO —
        # seguro, pero mudo, que es la trampa 44.
        if raices_escritura and not self.escritura:
            raise ValueError("se declararon raíces de escritura y ninguna confina (R6+R9)")
        # N9: ver PISO_TEMPORAL_S. Por defecto False: CLI/watcher/MCP no pagan
        # nada por un adversario que no tienen.
        self.ecualizar_temporal = ecualizar_temporal
        # N32: marca si el hilo actual está DENTRO de un `with operacion():`.
        # `threading.local` porque el mismo `Confinamiento` es compartido por
        # `FileX`, y dos hilos resolviendo a la vez no pueden pisarse la marca.
        self._local = threading.local()

    @staticmethod
    def _podadas(raices) -> list[str]:
        """QUÉ se descartó al preparar. N37: la poda de N35 era MUDA.

        N35 acertó al podar en vez de invalidar el conjunto —un cliente que
        declara `["C:\\", <un directorio legítimo>]` conserva el legítimo—,
        pero lo hace **en silencio**: nadie se entera de qué raíces se cayeron
        ni por qué, y una lista blanca más estrecha de lo que el operador cree
        se manifiesta después como un `ruta no accesible` que R4 obliga a dejar
        opaco. Es la trampa 44 por omisión: el comportamiento es correcto y no
        hay dónde verlo.

        No cambia ninguna decisión —se calcula sobre lo mismo que `_preparar`
        descarta— y sólo existe para que la superficie pueda registrarlo. Se
        devuelven las raíces TAL COMO LAS DECLARÓ quien las pasó, no
        normalizadas: lo que el operador necesita reconocer es lo que escribió.
        """
        quedan = set(Confinamiento._preparar(raices))
        fuera = []
        for r in raices or []:
            if not r or not str(r).strip():
                fuera.append(str(r))
                continue
            if _norm(os.path.abspath(r)) not in quedan:
                fuera.append(str(r))
        return fuera

    @staticmethod
    def _preparar(raices) -> list[str]:
        """R3 + N35: las raíces que no confinan se PODAN, no invalidan el conjunto.

        **Antes se lanzaba `ValueError` en cuanto UNA raíz no confinaba**, así
        que un cliente que declarase `["C:\\", <un directorio legítimo>]`
        perdía también el directorio legítimo: `sin_acceso = True` sobre una
        sesión que tenía una lista blanca perfectamente utilizable. Es el
        reverso exacto de la fuga que cerró N7 —aquélla abría de más, ésta
        cerraba de más— y **el mismo `except ValueError` de `mcp.py` tapaba
        las dos**.

        Podar es seguro, y no de palabra (`bench/raices-mixtas.md`):

        1. **Podar sólo QUITA — y esto es lo que sostiene la decisión.**
           `_dentro` es un OR sobre las raíces, y aquí las que sobreviven no se
           reescriben: salen con la misma `_norm(abspath(...))` que aplicaba el
           código de antes. Quitar un término de un OR sólo puede **reducir** el
           conjunto aceptado, así que la poda no puede conceder nada nuevo.
        2. **Y más fuerte todavía: ese acceso nunca existió.** Con el código
           anterior, un `Confinamiento` **construido** no podía contener jamás
           una raíz de unidad, porque esta misma función lanzaba antes de
           devolverla. La poda no quita un acceso que nunca llegó a existir.
        3. **La guarda R6 sigue en pie.** Si tras podar no queda ninguna raíz
           de lectura, el `__init__` lanza igual que antes, así que el caso de
           N7 —`["C:\\"]` sola— sale idéntico al de ayer: `sin_acceso = True`,
           `confinamiento = None`. MEDIDO celda a celda: A y B coinciden en
           esa fila en las dos superficies.

        > **Lo que este docstring afirmaba y era FALSO, conservado porque el
        > error es instructivo.** Decía *«una raíz de unidad es INERTE: no
        > concede nada, `_dentro` deniega para todo»*. `_dentro` es
        > `c == r or c.startswith(r + os.sep)`, y sólo la **segunda** rama
        > muere con la barra doble: la primera acepta un candidato, **la propia
        > raíz**. MEDIDO: `_dentro("C:\\\\", ["c:\\\\"])` es `True`, y de una
        > muestra de cinco concede **1** —`C:\\` sí, `C:\\Windows` no—. No
        > cambia el veredicto, pero la frase que sostenía la decisión estaba
        > mal: los motivos buenos son el 1 y el 2, que son estructurales y no
        > dependen de qué conceda la raíz podada.
        """
        out = []
        for r in raices or []:
            # N37: una raíz VACÍA no nombra ningún directorio, y `abspath("")`
            # la convierte en el `cwd` del proceso — una lista blanca que nadie
            # declaró, por el mismo mecanismo que la fila N37 cerró en los URI:
            # lo declarado y lo efectivo dejan de coincidir, y no porque se
            # pierda la raíz sino porque se SUSTITUYE por otra. MEDIDO
            # (`bench/uri-authority.md`): `Confinamiento([""])` concedía el
            # `cwd` entero, y la CLI pasa `--raiz` tal cual, así que una
            # variable de entorno vacía en un script bastaba. Se poda igual que
            # las de abajo, y el resultado es el que R6 ya prescribe: si no
            # queda ninguna, no se arranca. Separar «no declaré» (lista vacía)
            # de «declaré algo que no confina» es la trampa 43, y aquí las dos
            # acaban en el mismo sitio a propósito: sin acceso.
            if not r or not str(r).strip():
                continue
            a = _norm(os.path.abspath(r))
            # R3: una raíz que normaliza a la raíz de una unidad —o a la de un
            # recurso UNC `\\servidor\recurso`, que da lo mismo aquí— no
            # confina nada. Se descarta ELLA, no el conjunto (N35).
            padre = os.path.dirname(a)
            if padre == a:
                continue
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

    @contextlib.contextmanager
    def operacion(self):
        """N32: agrupa varias llamadas a `resolver()` bajo UN solo suelo.

        `FileX._resolver()` llama a `resolver()` dos veces para una conversión
        válida (entrada + directorio de salida) y una sola si se deniega en la
        entrada. Con el suelo por LLAMADA (el único que había hasta N32), la
        vía válida paga el doble — el residuo de `existe/prohibido = 2,11×`
        que `bench/oraculo-y-gotenberg.md` §1.5 dejó `PENDIENTE`. Envolviendo
        la secuencia entera en `with confinamiento.operacion():`, las llamadas
        de dentro NO esperan cada una por su cuenta (ven la marca de hilo y se
        saltan su propio `_esperar_piso`); el suelo se paga UNA vez, al salir
        del `with` — con `try/finally`, así que una `Denegado` a mitad de la
        secuencia también lo paga, igual que antes.

        Sin `ecualizar_temporal`, no hace nada (mismo criterio que `resolver`):
        CLI/watcher/MCP no pagan un suelo que no necesitan.

        Reentrante: si ya hay una `operacion()` en curso en este hilo (o se
        llama a `resolver()` suelto, fuera de un `with`), cada uno sigue
        pagando su propio suelo — esto solo evita el DOBLE PAGO cuando el
        propio código agrupa las llamadas a propósito.
        """
        if not self.ecualizar_temporal:
            yield
            return
        ya_en_operacion = getattr(self._local, "en_operacion", False)
        if ya_en_operacion:
            # Anidado: la operación exterior ya va a pagar el suelo. No abrir
            # un segundo cronómetro ni tocar la marca de hilo.
            yield
            return
        inicio = time.perf_counter()
        self._local.en_operacion = True
        try:
            yield
        finally:
            self._local.en_operacion = False
            _esperar_piso(inicio)

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

        N32: si esta llamada ocurre dentro de un `with self.operacion():` de
        este mismo hilo, el suelo NO se paga aquí — lo paga `operacion()` una
        sola vez al salir del `with`. Fuera de una `operacion()`, el
        comportamiento es el de siempre: un suelo por llamada.
        """
        if not self.ecualizar_temporal:
            return self._resolver_sin_ecualizar(ruta, escritura=escritura)
        if getattr(self._local, "en_operacion", False):
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

    def abrir_confinado(self, ruta: str, *, escritura: bool = False) -> "_EntradaConfinada":
        """N38: abre el DESCRIPTOR y valida el descriptor, no una cadena reabrible.

        Cierra la carrera symlink-TOCTOU que la trampa 128 midió (`resolver()`
        devuelve `os.path.realpath(ruta)`, el motor la reabre, y entre medias un
        atacante conmuta un componente de directorio: dir real → symlink a
        fuera). El antipatrón es *comprobar la ruta resuelta y volver a abrirla*;
        la defensa es *abrir una vez y validar QUÉ se abrió*. MEDIDO
        (`bench/toctou-fd.md`): con `resolver()`+reabrir la carrera gana
        **17,5 %**; con esto, **0 de ~34 000** bajo el mismo ataque.

        Devuelve un `_EntradaConfinada` (gestor de contexto) con:
        - `.fd`: el descriptor abierto y validado (para un lector en proceso).
        - `.ruta`: la ruta ESTABLE que se le entrega al motor externo.
          En Linux es `/proc/<pid>/fd/<fd>`, que **un motor que reabre por ruta
          alcanza al INODO FIJADO aunque el atacante haya envenenado la ruta
          original después** — MEDIDO cross-proceso con `cat`, `magick` y
          `ffmpeg`, que la aceptan (sniffean por contenido, no por extensión).
          El `fd` debe seguir ABIERTO mientras el motor lee: cerrarlo invalida
          `/proc/<pid>/fd/<fd>`.
        - `.real`: la ruta real que se abrió, ya validada dentro de la raíz.

        **En Windows no existe `/proc` ni un primitivo equivalente** (MEDIDO): se
        valida el descriptor con `GetFinalPathNameByHandle` —lo que DETECTA si
        lo que se abrió resolvió fuera— pero `.ruta` es la ruta real validada, y
        el motor la reabre, así que la ventana de reapertura por ruta **NO** se
        cierra aquí: la cubre el bloqueo de fichero del sistema (79 % de fallo
        del atacante, heredado) y el privilegio que exige crear un symlink. El
        cierre total en Windows queda PENDIENTE (`bench/toctou-fd.md` §Windows).

        **No paga el suelo temporal de N9 a propósito.** Solo se invoca en la
        vía VÁLIDA, después de que `_resolver()` haya cerrado el oráculo de
        existencia bajo `operacion()`; su `Denegado` es un artefacto de carrera,
        no un oráculo cronometrable, y pagar un segundo suelo aquí reabriría el
        residuo `existe/prohibido` que N32 cerró.
        """
        if not self._lexico_ok(ruta):
            raise Denegado()
        raices = self.escritura if escritura else self.lectura
        if not raices:
            raise Denegado()
        # R1: predicado léxico ANTES de tocar el disco, igual que `resolver()`.
        if not self._dentro(os.path.abspath(ruta), raices):
            raise Denegado()

        # El paso que cambia todo: se ABRE el descriptor aquí, en vez de
        # devolver un `realpath` que otro reabrirá más tarde. Si el atacante ya
        # había conmutado el componente, `os.open` sigue el symlink y abre el
        # fichero de FUERA — y entonces `_ruta_real_de_fd` lo delata y se
        # deniega. Si no lo había conmutado, se ancla el inodo de DENTRO y una
        # conmutación posterior ya no cambia lo que el motor leerá.
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_CLOEXEC", 0)
        try:
            fd = os.open(ruta, flags)
        except OSError:
            raise Denegado() from None
        try:
            import stat as _stat
            if not _stat.S_ISREG(os.fstat(fd).st_mode):
                # Un directorio o un dispositivo no es una entrada de conversión.
                # Mismo mensaje opaco que R4 (`ruta no accesible`).
                raise Denegado()
            real = _ruta_real_de_fd(fd)
            # Y otra vez sobre la RESUELTA-DE-VERDAD (la del descriptor, no una
            # cadena): es lo que cierra el enlace simbólico sin dejar ventana.
            if not self._dentro(real, raices):
                raise Denegado()
        except Denegado:
            os.close(fd)
            raise
        except OSError:
            os.close(fd)
            raise Denegado() from None
        return _EntradaConfinada(fd, _ruta_estable_para_motor(fd, real), real)

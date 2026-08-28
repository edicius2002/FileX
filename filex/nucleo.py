"""La conversión. Y la verificación **dentro** de ella, no después.

Es la decisión de diseño más importante del hito 1, y está MEDIDA
(`bench/contrato-quinto-punto.md`):

    **El punto 5 es el único punto del contrato que NO se puede verificar a
    posteriori.** Sin censo, **49 de las 53 salidas del patrón oro bajan de `ok`
    a `ok_parcial`**. Hay que estar mirando cuando el motor escribe.

Por eso aquí no hay una función `convertir()` y otra `verificar()` que alguien
pueda llamar en el orden equivocado o saltarse: **el censo se toma dentro del
mismo `with` que lanza el motor**, y la salida no sale del directorio desechable
hasta que el contrato la ha juzgado.
"""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field

from . import contrato, formatos, invocacion, motores as _motores
from .confinamiento import Confinamiento, Denegado, nombre_seguro
from .grafo import Arista, Camino, Decision, Grafo
from .trabajo import DirectorioDeTrabajo


#: Las claves del pedido que deciden PÍXELES, y por tanto tienen que actuar en
#: el salto que los crea, no en el último — MEDIDO (`bench/sondeo-imagemagick.md`
#: §6.1): `--params '{"dpi":400}'` sobre `svg→pdf` daba una página de 3,0×1,5 cm
#: con los mismos 480×240 píxeles **y contrato 6/6 en los dos saltos**, porque el
#: `dpi` llegaba al `png→pdf` cuando el rasterizado ya había ocurrido.
#:
#: Lo que NO se propaga son las decisiones de CODIFICACIÓN —calidad, códec,
#: bitrate, sin_perdida—: esas pertenecen al fichero final, y aplicarlas a un
#: intermedio es recodificar dos veces.
CLAVES_DE_PIXEL = ("dpi", "ancho", "alto", "profundidad_bits", "fondo")


def _pedido_intermedio(pedido: dict) -> dict:
    return {k: v for k, v in (pedido or {}).items() if k in CLAVES_DE_PIXEL}


# --------------------------------------------------------------------------
# El destino en curso — un agujero que solo se ve con CONCURRENCIA
# --------------------------------------------------------------------------
#
# HITO 7, y es el hallazgo del hito — MEDIDO (`bench/hito7-superficies.md` §5.3).
# Tres peticiones simultáneas de la API HTTP con **tres entradas distintas**
# (PNG de 42 855 B, JPEG de 87 954 B y TIFF de 72 MB) y **la misma ruta de
# salida** devolvieron las tres `ok`, con contrato aprobado, declarando
# **13 516 / 14 402 / 647 580 bytes** — y en el disco quedó **un solo fichero de
# 647 580 B**. Dos de las tres respuestas describían un fichero que ya no
# existía.
#
# **El contrato no puede atraparlo y no es culpa suya:** juzga la salida dentro
# del directorio desechable, que es privado de cada conversión, y el
# atropello ocurre después, en el `shutil.move` al destino. El punto 5 mira el
# desechable; nadie miraba el destino.
#
# El arreglo va AQUÍ y no en la API, y eso es R10 funcionando: el fallo lo
# encontró la cuarta superficie y el remedio no vive en ella — la CLI, MCP y el
# watcher tenían exactamente el mismo agujero y se cierra en el mismo sitio para
# los cuatro.
#
# **Alcance declarado, sin adornos: era un cerrojo DE PROCESO.** Dos procesos
# `filex` distintos —una API y un watcher, por ejemplo— seguían pudiendo
# pisarse. **CERRADO el 23/08 (N1, `bench/cerrojo-de-maquina.md`)**: el fallo
# está reproducido entre procesos de verdad —3 procesos, 3 entradas distintas,
# un destino: **3 `ok` y 1 fichero**— y ahora la reserva tiene DOS mitades, que
# es la lección que dejó escrita `bench/lock-de-maquina.md` para el lock de GPU:
#
#   1. **EXCLUSIÓN**, para quien coopera: un candado de fichero por destino en
#      `%TEMP%/filex-destinos/`, tomado con `msvcrt.locking` (Windows) o
#      `fcntl.flock` (POSIX). Excluye a cualquier otro proceso `filex` del
#      mismo usuario, esté en el worktree que esté.
#   2. **DETECCIÓN**, para quien NO coopera: un `chrome.exe` descargando sobre
#      esa misma ruta no va a tomar nunca nuestro candado. Lo único que se
#      puede hacer con él es **verlo y negarse**, con el mismo primitivo de la
#      trampa 27 —`os.replace(p, p)`, el único cerrojo real en Windows—, justo
#      antes del `shutil.move` que sería el atropello.
#
# **Mover el fichero de sitio no habría bastado**, igual que no bastó para la
# GPU: un lock excluye a quien lo toma. La mitad que cierra el caso ajeno es la
# segunda.
#
# Lo que este cerrojo **NO** cubre está en `bench/cerrojo-de-maquina.md` §6, y
# lo más importante es que **`%TEMP%` es POR USUARIO**: dos usuarios de Windows
# distintos, o el `/tmp` de la VM de WSL2, tendrían candados distintos.
_DESTINOS_EN_CURSO: set[str] = set()
_CERROJO_DESTINOS = threading.Lock()

#: Descriptores del candado de fichero, por clave de destino. Solo se tocan con
#: `_CERROJO_DESTINOS` cogido.
_FDS_DESTINO: dict[str, int] = {}

_ES_WINDOWS = sys.platform == "win32"

#: El byte que se bloquea, MUY lejos del principio del fichero: así los
#: metadatos (quién lo tiene, desde cuándo, qué ruta) **siguen siendo legibles
#: desde otro proceso** mientras el candado está tomado. MEDIDO
#: (`bench/salidas-cerrojo/logs/sonda_primitivos.log`, paso 2).
_OFFSET_CERROJO = 1 << 30

#: Qué se declara cuando la infraestructura del candado no está disponible.
#: Degradar EN SILENCIO es el fallo de la trampa 13 (`onnxruntime` cayendo a
#: CPU sin un error): si el candado de máquina no se puede tomar, la conversión
#: sigue con el cerrojo de proceso **y lo dice en el aviso**.
_AVISO_SIN_CERROJO = ("cerrojo de máquina no disponible ({}): la exclusión es "
                      "solo de proceso")

_dir_cerrojos_cache: str | None = None
_aviso_cerrojo: str = ""


def _modo_cerrojo() -> str:
    """`maquina` (defecto) · `proceso` (el estado del hito 7) · `ninguno`.

    Existe para poder MEDIR el antes y el después **dentro de la misma tanda**
    —las cifras absolutas de tandas distintas no son comparables— y para que
    quien tenga un `%TEMP%` inservible pueda seguir. El valor por defecto es el
    seguro; los otros dos hay que pedirlos a mano.
    """
    return (os.environ.get("FILEX_CERROJO_DESTINO") or "maquina").strip().lower()


def _dir_cerrojos() -> str:
    global _dir_cerrojos_cache
    if _dir_cerrojos_cache is None:
        d = os.environ.get("FILEX_CERROJO_DIR") or os.path.join(
            tempfile.gettempdir(), "filex-destinos")
        os.makedirs(d, exist_ok=True)
        _dir_cerrojos_cache = d
    return _dir_cerrojos_cache


def _clave_destino(ruta: str) -> str:
    """La identidad del destino. **Y `abspath` NO basta — MEDIDO.**

    R3 (`normcase`) cierra el cambio de caja, que es lo que probaba el hito 7.
    No cierra el **alias de ruta**, y en Windows los hay de sobra: el nombre
    corto 8.3, un `subst`, un enlace de directorio, una UNC. Sobre esta máquina
    (`bench/cerrojo-de-maquina.md` §6.1), con `abspath` a secas:

        C:\\...\\Temp\\filex-aliaslargisimo-t0huurpm\\salida.webp   -> reserva OK
        C:\\...\\Temp\\FI09A7~1\\salida.webp                        -> reserva OK

    **Dos dueños del mismo fichero**, que es exactamente lo que este cerrojo
    viene a impedir. Se resuelve el DIRECTORIO —que existe y es estable— y se
    le vuelve a pegar el nombre. Resolver la ruta ENTERA sería más fuerte
    (cerraría también un destino que fuese un enlace a otro fichero) y es lo
    que **no** se hace, a propósito: el destino puede no existir al reservar y
    sí existir al soltar, y una clave que se mueve entre las dos llamadas deja
    el candado tomado para siempre. **PENDIENTE**, declarado en §6.2.
    """
    a = os.path.abspath(ruta)
    d, n = os.path.split(a)
    try:
        d = os.path.realpath(d)
    except OSError:
        pass
    return os.path.normcase(os.path.join(d, n))


def _fichero_cerrojo(clave: str) -> str:
    # El nombre es un resumen, no la ruta: una ruta de 200 caracteres no cabe
    # como nombre de fichero, y además el directorio de candados es común a
    # todos los destinos, así que no debe filtrar a qué ficheros ajenos está
    # accediendo otro usuario del mismo `%TEMP%`.
    h = hashlib.sha256(clave.encode("utf-8", "surrogatepass")).hexdigest()[:32]
    return os.path.join(_dir_cerrojos(), h + ".lock")


def _bloquear_fd(fd: int) -> None:
    """Candado de rango de bytes, no bloqueante. Lo suelta el SISTEMA.

    Esa es la razón de elegirlo frente a un `O_CREAT|O_EXCL`: MEDIDO
    (`sonda_primitivos.log`), matar al dueño con `taskkill /F` —que no ejecuta
    ningún `finally`— deja el candado **libre en 22,1 µs**, mientras que un
    `O_EXCL` deja un huérfano para siempre y obliga a un censo de PID que en
    esta máquina ya se sabe que no se puede hacer bien (trampa 31).
    """
    if _ES_WINDOWS:
        import msvcrt

        os.lseek(fd, _OFFSET_CERROJO, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _tomar_candado(clave: str) -> tuple[int | None, str]:
    """`(fd, aviso)`. `fd is None` = lo tiene otro proceso. `aviso` = degradado."""
    try:
        ruta_lock = _fichero_cerrojo(clave)
        fd = os.open(ruta_lock, os.O_RDWR | os.O_CREAT, 0o600)
    except OSError as e:
        return -1, _AVISO_SIN_CERROJO.format(e.__class__.__name__)
    try:
        _bloquear_fd(fd)
    except OSError:
        os.close(fd)
        return None, ""
    try:
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, f"{os.getpid()}\t{int(time.time())}\t{clave}\n".encode(
            "utf-8", "surrogatepass"))
    except OSError:
        pass  # los metadatos son para el humano; la exclusión ya está tomada
    return fd, ""


def _soltar_candado(fd: int, clave: str) -> None:
    if fd < 0:
        return
    try:
        if _ES_WINDOWS:
            import msvcrt

            os.lseek(fd, _OFFSET_CERROJO, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass
    try:
        os.close(fd)
    except OSError:
        pass
    if _ES_WINDOWS:
        # Barrer el fichero para que `%TEMP%/filex-destinos` no crezca sin
        # límite. **Solo en Windows, y no es pereza:** aquí un fichero abierto
        # por cualquiera no se puede borrar (MEDIDO, `sonda_primitivos.log`
        # paso 2), así que un borrado que TIENE ÉXITO demuestra que nadie lo
        # tenía. En POSIX el borrado siempre funciona y abriría la carrera
        # clásica de «borro el candado de otro», así que allí el fichero se
        # queda.
        try:
            os.remove(_fichero_cerrojo(clave))
        except OSError:
            pass


def _reservar_destino(ruta: str) -> bool:
    """Nadie más —ni en este proceso ni en otro— puede estar escribiendo aquí."""
    global _aviso_cerrojo
    clave = _clave_destino(ruta)
    with _CERROJO_DESTINOS:
        if clave in _DESTINOS_EN_CURSO:
            return False
        _DESTINOS_EN_CURSO.add(clave)
    if _modo_cerrojo() != "maquina":
        return True
    fd, aviso = _tomar_candado(clave)
    if fd is None:
        with _CERROJO_DESTINOS:
            _DESTINOS_EN_CURSO.discard(clave)
        return False
    _aviso_cerrojo = aviso
    with _CERROJO_DESTINOS:
        _FDS_DESTINO[clave] = fd
    return True


def _soltar_destino(ruta: str) -> None:
    clave = _clave_destino(ruta)
    with _CERROJO_DESTINOS:
        _DESTINOS_EN_CURSO.discard(clave)
        fd = _FDS_DESTINO.pop(clave, None)
    if fd is not None:
        _soltar_candado(fd, clave)


def destino_ocupado_por_un_tercero(ruta: str) -> bool:
    """La mitad de DETECCIÓN: ¿hay alguien más con ese fichero abierto AHORA?

    Es la trampa 27 usada al revés. `open(p,'rb')` funciona en los cuatro
    estados y no prueba nada; `os.replace(p, p)` falla con `WinError 32` en
    cuanto otro proceso tiene el fichero abierto, y **es el único cerrojo real
    en Windows**.

    Dos límites MEDIDOS que hay que declarar (`sonda_primitivos.log` §5, y
    `bench/cerrojo-de-maquina.md` §5):

    * **No distingue un LECTOR de un ESCRITOR.** Un visor con la salida abierta
      dispara el mismo `WinError 32` que un escritor. Es un falso positivo
      posible, y se prefiere a sobrescribir el fichero de alguien.
    * **En POSIX devuelve siempre `False`**: allí `os.replace(p, p)` es un
      no-op que siempre funciona. Es el mismo pendiente que `_estable_en_disco`
      del watcher (`hito7-superficies.md` §7.3).
    """
    if not _ES_WINDOWS or _modo_cerrojo() != "maquina":
        return False
    try:
        os.replace(ruta, ruta)
    except FileNotFoundError:
        return False  # no existe: nadie lo está escribiendo
    except OSError:
        return True
    return False


@dataclass
class Salto:
    arista: Arista
    rc: int | None = None
    ms: float = 0.0
    veredicto: str = ""
    hallazgos: list = field(default_factory=list)
    cobertura: dict = field(default_factory=dict)
    sobrantes: dict = field(default_factory=dict)
    motivo: str = ""
    #: Dónde quedó la salida de ESTE salto: dentro del desechable si es
    #: intermedia, en el destino real si es la última.
    ruta: str = ""
    #: `stderr` crudo. Para el log y para el humano. **Nunca para un modelo.**
    err: str = ""


@dataclass
class Conversion:
    entrada: str
    salida: str
    camino: Camino | None = None
    saltos: list[Salto] = field(default_factory=list)
    ok: bool = False
    motivo: str = ""
    aviso: str = ""
    rechazados: list = field(default_factory=list)

    @property
    def veredicto(self) -> str:
        if not self.ok:
            return "fallo"
        peor = "ok"
        for s in self.saltos:
            if s.veredicto == "fallo":
                return "fallo"
            if s.veredicto in ("aviso", "ok_parcial") and peor == "ok":
                peor = s.veredicto
        return peor


class FileX:
    """El núcleo. Las cuatro superficies (CLA, MCP, watcher, API) lo usan a él.

    R10: **la validación vive en el núcleo, no en la superficie.** La CLI de
    kordoc ignora su propia variable de confinamiento porque la validación
    estaba en la capa MCP. Aquí no puede pasar: no hay otro camino.
    """

    def __init__(self, raices_lectura=None, raices_escritura=None) -> None:
        self.motores = {m.nombre: m for m in _motores.sondear_todos()}
        self.grafo = Grafo()
        for m in self.motores.values():
            if m.disponible:
                for a in m.aristas:
                    self.grafo.añadir(a)
        self.confinamiento = None
        if raices_lectura:
            self.confinamiento = Confinamiento(raices_lectura, raices_escritura)

    # ------------------------------------------------------------ inventario

    @property
    def disponibles(self) -> list:
        return [m for m in self.motores.values() if m.disponible]

    @property
    def ausentes(self) -> list:
        return [m for m in self.motores.values() if not m.disponible]

    def destinos(self, ext: str) -> list[str]:
        """`list_targets`: la única respuesta honesta a «¿puedo hacer X?».

        MEDIDO y contraintuitivo (`bench/saturacion-herramientas.md` §3.5):
        cuando el catálogo no cubre lo que se pide, un modelo **no se abstiene**
        — llama a la más parecida y declara éxito con un dato falso, el 15-17 %
        de las veces. Por eso esto es un mecanismo de seguridad, no una comodidad.
        """
        o = formatos.normaliza(ext)
        vistos = {o}
        frente = [o]
        while frente:
            act = frente.pop()
            for a in self.grafo.desde(act):
                if a.destino not in vistos:
                    vistos.add(a.destino)
                    frente.append(a.destino)
        return sorted(vistos - {o})

    def planificar(self, entrada: str, salida: str) -> Decision:
        return self.grafo.camino(
            formatos.normaliza(os.path.splitext(entrada)[1]),
            formatos.normaliza(os.path.splitext(salida)[1]),
        )

    # ------------------------------------------------------------ conversión

    def _resolver(self, entrada: str, salida: str) -> tuple[str, str]:
        # R12 sobre el NOMBRE DE SALIDA, y va ANTES de mirar si hay lista
        # blanca: sin esto se escriben 94 B en el flujo alternativo de un
        # fichero ajeno con `veredicto: ok`, y el contenido visible de la
        # víctima queda intacto, así que nadie lo nota. Validar el DIRECTORIO
        # del destino no basta — el nombre del fichero no lo miraba nadie.
        if not nombre_seguro(os.path.basename(os.path.abspath(salida))):
            raise Denegado()
        if self.confinamiento is None:
            return os.path.abspath(entrada), os.path.abspath(salida)
        ent = self.confinamiento.resolver(entrada)
        # La salida aún no existe: se valida su DIRECTORIO, que sí.
        dsal = os.path.dirname(os.path.abspath(salida)) or "."
        self.confinamiento.resolver(dsal, escritura=True)
        return ent, os.path.abspath(salida)

    def convertir(self, entrada: str, salida: str, pedido: dict | None = None,
                  *, timeout: float = invocacion.TIMEOUT_POR_DEFECTO) -> Conversion:
        pedido = dict(pedido or {})
        conv = Conversion(entrada=entrada, salida=salida)

        try:
            ent_abs, sal_abs = self._resolver(entrada, salida)
        except Denegado as e:
            conv.motivo = str(e)
            return conv
        if not os.path.isfile(ent_abs):
            # R4: el MISMO mensaje que para «prohibido». Distinguirlos convierte
            # el conversor en un oráculo de existencia del disco ajeno.
            conv.motivo = "ruta no accesible"
            return conv

        dec = self.planificar(entrada, salida)
        conv.camino = dec.camino
        conv.rechazados = dec.rechazados
        conv.aviso = dec.aviso
        if not dec.hay:
            conv.motivo = dec.motivo
            return conv
        if dec.camino is not None and dec.camino.saltos == 0:
            conv.motivo = "origen y destino son el mismo formato"
            return conv

        # Nadie más puede estar escribiendo este destino. Se reserva DESPUÉS de
        # saber que hay camino —reservar para luego decir «no hay camino» sería
        # bloquear un destino por nada— y se suelta en el `finally`.
        if not _reservar_destino(sal_abs):
            # No es un mensaje opaco y no debe serlo: el cliente **pidió** esta
            # ruta, así que nombrarla no le dice nada que no supiera. Lo que sí
            # sería un fallo es devolver `ok` como se hacía hasta el hito 7.
            conv.motivo = "otra conversión está escribiendo ya esa ruta de salida"
            return conv
        if _aviso_cerrojo:
            conv.aviso = (conv.aviso + "; " + _aviso_cerrojo) if conv.aviso else _aviso_cerrojo

        # Mitad de DETECCIÓN, primera pasada: si el destino YA lo tiene abierto
        # alguien que no pasa por FileX, más vale saberlo antes de gastar 250 ms
        # en convertir para acabar negándose igual.
        if destino_ocupado_por_un_tercero(sal_abs):
            _soltar_destino(sal_abs)
            conv.motivo = "otro proceso tiene abierta esa ruta de salida"
            return conv

        actual = ent_abs
        temporales: list[DirectorioDeTrabajo] = []
        try:
            for i, paso in enumerate(dec.camino.pasos):
                ultimo = i == len(dec.camino.pasos) - 1
                s = self._un_salto(paso.arista, actual, sal_abs, pedido,
                                   ultimo=ultimo, timeout=timeout,
                                   temporales=temporales)
                conv.saltos.append(s)
                if s.veredicto == "fallo" or s.rc not in (0,):
                    conv.motivo = s.motivo or "el motor rechazó la conversión"
                    return conv
                actual = s.ruta
            conv.ok = True
            return conv
        finally:
            _soltar_destino(sal_abs)
            for t in temporales:
                t.cerrar()

    def _un_salto(self, arista: Arista, entrada: str, destino_final: str,
                  pedido: dict, *, ultimo: bool, timeout: float,
                  temporales: list) -> Salto:
        """Un salto = un directorio desechable + un motor + un censo + el contrato."""
        motor = self.motores[arista.motor]
        s = Salto(arista=arista)

        t = DirectorioDeTrabajo()
        temporales.append(t)
        nombre = f"salida.{arista.destino}"
        dentro = t.destino(nombre)

        try:
            # El motor recibe el tope de QUIEN LLAMA: el de aquí solo alcanza
            # al cliente, y hay motores cuyo trabajo real vive en otro proceso.
            argv = motor.orden(entrada, dentro,
                               pedido if ultimo else _pedido_intermedio(pedido),
                               timeout=timeout)
            # `orden()` puede devolver `(argv, decidido)`: lo que el motor eligio
            # por su cuenta y el contrato tiene que saber. Es aditivo — quien
            # devuelva solo `argv` sigue funcionando — y evita la unica
            # alternativa, que era duplicar la logica de decision en un segundo
            # metodo y verla divergir.
            declarado = {}
            if isinstance(argv, tuple):
                argv, declarado = argv
                declarado = dict(declarado or {})
        except Exception as e:
            s.motivo = f"no se pudo construir la orden: {e}"
            return s

        # El `cwd` del hijo va DENTRO del desechable. Validar la ruta de salida
        # NO basta: hay motores que escriben en el `cwd`.
        r = invocacion.ejecutar(argv, timeout=timeout, cwd=t.ruta)
        s.rc, s.ms, s.err = r.rc, r.ms, r.err
        if r.agotado:
            # ANTES de que el `finally` borre el desechable. Borrar el origen de
            # un bind mount vivo deja al contenedor atascado — MEDIDO.
            try:
                motor.parar()
            except Exception:
                pass
        if not r.ok:
            s.motivo = r.motivo
            s.ruta = dentro
            return s

        # --- el punto 5, tomado AQUÍ: después ya no existe -------------------
        censo = t.censo()
        s.sobrantes = t.sobrantes([nombre])

        # Lo que el MOTOR decide y nadie pidio tiene que llegar al contrato, o
        # el punto 4 —escrito para atrapar a `image-worker-mcp`— atrapa a FileX.
        # Tres agentes dieron con la misma forma el mismo dia: el motor y el
        # contrato no compartian el `pedido`.
        ped = dict(pedido, destino=arista.destino)
        _f = formatos.formato(arista.destino)
        if _f is not None and _f.categoria == "audio" and not ped.get("solo_audio"):
            # `orden()` pone `-vn` por la categoria del destino, y el contrato
            # exigia que un .wav extraido de un .mp4 conservara el video. MEDIDO
            # (`bench/sondeo-ffmpeg.md` 3): 13 aristas video->audio pasaban a
            # `V7 fallo` por no declararlo. Los DOS sitios hacen falta: el punto
            # 2 mira `solo_audio` o `params.solo_audio`, y el punto 4 solo mira
            # `params`.
            ped["solo_audio"] = True
            ped["params"] = dict(ped.get("params") or {}, solo_audio=True)
        ped["params"] = dict(ped.get("params") or {}, **declarado)
        ped.update(declarado)
        res = contrato.verificar(dentro, entrada, ped, censo)
        s.veredicto = res.get("veredicto", "?")
        s.hallazgos = res.get("hallazgos", [])
        s.cobertura = res.get("cobertura", {})
        if s.veredicto == "fallo":
            s.motivo = contrato.resumen(res)
            s.ruta = dentro
            return s

        if ultimo:
            # Mitad de DETECCIÓN, segunda pasada — **y es la que importa.**
            # Aquí es donde ocurría el atropello: `shutil.move` sobre un
            # destino existente cae a `copy2`, que sobrescribe en silencio. El
            # candado excluye a los otros `filex`; esto es lo único que se puede
            # hacer contra quien no lo toma, y es la ventana más estrecha
            # posible. Sigue siendo un INSTANTE, no una vigilancia
            # (`bench/lock-de-maquina.md` §5 punto 4).
            if destino_ocupado_por_un_tercero(destino_final):
                s.veredicto = "fallo"
                s.motivo = "otro proceso tiene abierta esa ruta de salida"
                s.ruta = dentro
                return s
            t.recoger(nombre, destino_final)
            s.ruta = destino_final
        else:
            s.ruta = dentro  # el desechable vive hasta el final
        return s

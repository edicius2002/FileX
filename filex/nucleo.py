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

import contextlib
import errno
import os
import shutil
import sys
import threading
import uuid
from dataclasses import dataclass, field

from . import cerrojo, contrato, formatos, gpu, invocacion, motores as _motores
from .confinamiento import Confinamiento, Denegado, nombre_seguro
from .grafo import Arista, Camino, Decision, Grafo
from .trabajo import DirectorioDeTrabajo, barrer_huerfanos


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
# **Y «de máquina» era todavía un título prestado. CERRADO el 27/08 (P,
# `bench/cerrojo-unico.md`)**, con las cuarenta líneas mudadas a
# `filex/cerrojo.py` —que es donde tienen que estar, porque el mismo primitivo
# lo piden otros dos consumidores— y con las dos mitades que faltaban:
#
#   * **La exclusión ahora cruza de usuario**, con un mutex con nombre en
#     `Global\`, que **sí se puede crear en esta máquina desde un token sin
#     elevar** —MEDIDO, y refuta el pendiente 1 de N-b—. Con descriptor de
#     seguridad **explícito**: por defecto el objeto es global en el nombre y de
#     usuario en el acceso.
#   * **La identidad del destino ya no es solo léxica.** `realpath` del
#     directorio cerró el nombre corto 8.3, pero un **enlace duro** al mismo
#     fichero seguía dando **DOS DUEÑOS** (MEDIDO, `sonda_enlaces.log`), y un
#     enlace duro no tiene «destino» que resolver: hace falta la identidad de
#     NTFS.
#
# Lo que este cerrojo **NO** cubre sigue en `bench/cerrojo-de-maquina.md` §6 y
# en `bench/cerrojo-unico.md` §6. Lo primero: **no cruza a la VM de WSL2**, y el
# motivo que se daba era falso — el fichero SÍ se ve desde `/mnt/c`; lo que no
# viaja es el candado (MEDIDO en las dos direcciones, con control positivo).
_DESTINOS_EN_CURSO: set[str] = set()
_CERROJO_DESTINOS = threading.Lock()

#: Los candados vivos, por clave PRINCIPAL (la léxica, que es la estable entre
#: reservar y soltar). Cada valor es `(claves, candados)`: se sueltan **las que
#: se tomaron**, no las que se vuelvan a calcular. Solo se tocan con
#: `_CERROJO_DESTINOS` cogido.
_RESERVAS: dict[str, tuple[list[str], list]] = {}

_ES_WINDOWS = sys.platform == "win32"

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
    return cerrojo.directorio()


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
    return cerrojo.fichero(clave)


def _identidad_destino(ruta: str) -> str | None:
    """La clave que un ENLACE no puede esquivar, o `None` si no hay fichero.

    Es el pendiente 4 de N-b, reproducido y cerrado — MEDIDO
    (`bench/salidas-cerrojo-unico/logs/sonda_enlaces.log`). Con la clave léxica
    a secas, sobre el MISMO fichero:

        enlace duro (mklink /H)       misma clave: False  -> DOS DUEÑOS
        enlace simbólico (mklink)     misma clave: False  -> DOS DUEÑOS
        unión de directorio (/J)      misma clave: True   -> ya lo cerró N-b

    **Y `realpath` de la ruta entera no habría bastado**, que es lo que la hacía
    parecer la respuesta obvia: un enlace **duro** no tiene destino que
    resolver — los dos nombres son igual de reales, y `realpath` devuelve cada
    uno tal cual. Lo único que los iguala es el identificador de fichero de
    NTFS, que `os.stat` ya trae: `st_dev` + `st_ino` coincidieron en los tres
    alias.

    **Solo se puede consultar si el fichero EXISTE**, y por eso esta clave es
    *añadida* y no sustituye a la léxica: en el caso normal el destino todavía
    no está. Cuesta 34,2 µs cuando existe y 21,9 cuando no.
    """
    # `FILEX_CERROJO_IDENTIDAD=0` la apaga, por el mismo motivo que
    # `FILEX_CERROJO_DESTINO`: medir el antes y el después en la misma tanda, y
    # que la prueba de b4 pueda fallar por el fallo que dice cubrir.
    if (os.environ.get("FILEX_CERROJO_IDENTIDAD") or "1").strip() == "0":
        return None
    try:
        st = os.stat(ruta)
    except OSError:
        return None
    if not st.st_ino:
        return None                # sistemas de ficheros sin identidad estable
    return f"id:{st.st_dev}:{st.st_ino}"


def _claves_destino(ruta: str) -> list[str]:
    """La léxica siempre; la de identidad **además**, si hay algo que mirar."""
    claves = [_clave_destino(ruta)]
    ident = _identidad_destino(ruta)
    if ident is not None:
        claves.append(ident)
    return claves


def _reservar_destino(ruta: str) -> bool:
    """Nadie más —ni en este proceso ni en otro— puede estar escribiendo aquí."""
    global _aviso_cerrojo
    claves = _claves_destino(ruta)
    principal = claves[0]
    # Entre hilos, primero: es un `set` en memoria y corta sin tocar el disco.
    with _CERROJO_DESTINOS:
        if any(c in _DESTINOS_EN_CURSO for c in claves):
            return False
        _DESTINOS_EN_CURSO.update(claves)
    if _modo_cerrojo() != "maquina":
        with _CERROJO_DESTINOS:
            _RESERVAS[principal] = (claves, [])
        return True

    tomados: list = []
    for clave in claves:
        c = cerrojo.Candado(clave, metadatos=principal)
        if not c.tomar():
            # **Se sueltan los que ya se tenían.** Tomar dos candados es tomar
            # dos candados: sin esta vuelta atrás, un rechazo por la segunda
            # clave dejaría la primera bloqueada hasta que muriese el proceso.
            for t in tomados:
                t.soltar()
            with _CERROJO_DESTINOS:
                _DESTINOS_EN_CURSO.difference_update(claves)
            return False
        if c.aviso:
            _aviso_cerrojo = c.aviso
        tomados.append(c)
    with _CERROJO_DESTINOS:
        _RESERVAS[principal] = (claves, tomados)
    return True


def _soltar_destino(ruta: str) -> None:
    # Se sueltan **las claves que se reservaron**, no las que salgan de volver a
    # mirar el disco: entre reservar y soltar el destino pasa de no existir a
    # existir, así que la clave de identidad **no está en la reserva y sí en el
    # recálculo**. Recalcular dejaría el candado tomado para siempre — que es
    # exactamente el riesgo por el que N-b no resolvió la ruta entera, y aquí
    # se evita guardando en vez de deduciendo.
    principal = _clave_destino(ruta)
    with _CERROJO_DESTINOS:
        claves, candados = _RESERVAS.pop(principal, ([principal], []))
        _DESTINOS_EN_CURSO.difference_update(claves)
    for c in candados:
        c.soltar()


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


# --------------------------------------------------------------------------
# N12 — la VENTANA entre la detección y el `move`, y por qué no se cierra con
# el handle que decía el pendiente
# --------------------------------------------------------------------------
#
# `bench/cerrojo-de-maquina.md` §6.3 dejó escrito: *«la detección es un
# INSTANTE, no una vigilancia. Entre el `os.replace(p,p)` y el `shutil.move`
# hay una ventana [...] quien llegue dentro de esa ventana pisa igual.
# Cerrarlo del todo exigiría abrir el destino con `FILE_SHARE_NONE`»*.
#
# **La ventana existe, y no es de microsegundos: son 681,4 µs de mediana**
# (n=15, testigos limpios; otra tanda dio 498,0 — el recorrido entre celdas es
# de 451,6 a 1 148,2 µs, `bench/ventana-antes-del-move.md` §2). Con un tercero de verdad en
# otro proceso, **12 de 12 celdas** acaban con FileX devolviendo `ok` sobre el
# fichero de otro; y **sin ningún gancho de sincronización, 7 de 12**. No hacía
# falta acertar nada fino: medio milisegundo es una eternidad.
#
# **Pero el remedio que proponía el pendiente es el caro y no es el bueno —
# MEDIDO** (ídem §3, `sonda_mecanismo.json`). `CreateFileW` con
# `dwShareMode=0` funciona (el tercero hizo **0 aberturas en 12 393 intentos**)
# **y me excluye también a MÍ**: con esa asa abierta, mi propio `os.replace`
# sobre el destino devuelve `WinError 5`. Es decir, quedarse el asa obliga a
# **escribir el contenido a través de ella**, que convierte un `rename` en una
# copia entera.
#
# **Lo que cierra la ventana es no tenerla: `os.replace` en vez de
# `shutil.move`.** Sobre el mismo estado —destino existente, abierto por un
# tercero— `shutil.move` **PISA** (4 014 B → 13 516 B, que son los números
# exactos del hito 7) porque su `os.rename` falla con `WinError 183` y él cae a
# `copy2`; `os.replace` **se niega con `WinError 5` y deja el fichero intacto**.
# La detección y la acción pasan a ser **la misma llamada del sistema**, así
# que no hay entre medias donde colarse.
#
# Cruzar volúmenes es el único caso en que sigue habiendo copia (el desechable
# vive en `%TEMP%`, que puede estar en otra unidad que el destino), y se
# distingue sin ambigüedad: `ERROR_NOT_SAME_DEVICE` llega como `errno.EXDEV`
# (18) y «ocupado» como `EACCES` (13) — MEDIDO. Ahí la copia va a un **temporal
# en el directorio de destino** y el paso final vuelve a ser un `os.replace`,
# que es el que decide.
#
# **Lo que NO cubre**, sin adornos:
#
#   * **El tercero que escribe y CIERRA dentro de la ventana.** `os.replace`
#     pisa un destino que existe y que nadie tiene abierto — tiene que hacerlo,
#     porque eso es exactamente sobrescribir un destino legítimo. Es
#     indistinguible desde aquí.
#   * **POSIX.** Allí `os.replace` sobrescribe aunque el fichero esté abierto,
#     igual que hoy. Lo que sí gana POSIX es la **atomicidad**: nunca queda un
#     destino a medio escribir. La detección sigue sin existir (§6.5 de N-b).
#   * **Después de escrito.** Lo que le pase a la salida un milisegundo más
#     tarde no es de aquí; es el punto 7 de la lista de N-b y sigue igual.
#   * **Un LECTOR sigue bastando para negarse.** El falso positivo de la trampa
#     33 no mejora ni empeora: es el mismo primitivo.
#   * **Si el destino es un DIRECTORIO existente**, `shutil.move` metía la
#     salida dentro y `os.replace` se niega. Es un cambio de comportamiento, y
#     negarse es lo correcto: nadie pidió esa ruta.
#     **N20: negarse era correcto y el MOTIVO era falso — MEDIDO**
#     (`bench/fidelidad-y-nucleo.md` §3). Ver `DestinoNoEsFichero`.


class DestinoOcupado(OSError):
    """El movimiento final se negó porque otro tiene el destino abierto.

    Es una excepción y no un booleano a propósito: el que la lanza es el
    `os.replace` que **ya ha decidido**, no una consulta previa que alguien
    pueda ignorar.
    """


class DestinoNoEsFichero(OSError):
    """El destino final existe y es un DIRECTORIO.

    **Por qué hace falta una excepción aparte, y por qué el `errno` no sirve
    para distinguirla — MEDIDO** (`bench/salidas-fidelidad-n/sonda_destino_dir.json`):
    en esta máquina `os.replace(fichero, DIRECTORIO)` y
    `os.replace(fichero, fichero_abierto_por_un_tercero)` dan **el mismo
    `PermissionError`, el mismo `errno=13` y el mismo `WinError 5`**. Los dos
    caían por tanto en `DestinoOcupado` y el cliente leía *«otro proceso tiene
    abierta esa ruta de salida»*, que **es falso** en el primero: no hay ningún
    otro proceso. Es la trampa 44 —un mensaje que promete algo que no ha
    ocurrido— sobre el camino que N12 acababa de arreglar.

    **La distinción se hace con `os.path.isdir` DESPUÉS del fallo, y eso no es
    un «comprobar y luego actuar» de los que prohíbe la trampa 63.** La acción
    ya está decidida y es la misma en los dos casos: negarse. Lo único que
    depende del `isdir` es **qué frase se escribe**, así que la peor
    consecuencia de una carrera aquí es un mensaje equivocado, nunca un
    atropello. Por eso se mira después y no antes.

    **Y no abre un canal de información que R1/R4 cierren.** La opacidad de
    R1/R4 protege rutas que el cliente **no** tiene permitidas: distingue
    «prohibido» de «no existe» para no ser un oráculo del sistema de ficheros.
    Aquí la ruta ya pasó el confinamiento —está dentro de una raíz de la lista
    blanca— y **la pidió el propio cliente**, que es el mismo argumento que ya
    justifica nombrar la ruta en «otra conversión está escribiendo ya esa ruta
    de salida». Lo que se revela es que **la ruta que él eligió** es un
    directorio, y eso ya lo sabía o lo puede saber sin FileX.
    """


def _move_seguro() -> bool:
    """`FILEX_MOVE_SEGURO=0` devuelve el `shutil.move` del hito 7.

    Mismo motivo que `FILEX_CERROJO_DESTINO` y `FILEX_CERROJO_MUTEX`: poder
    medir el antes y el después **dentro de la misma tanda**, y que una prueba
    pueda fallar por el fallo que dice cubrir. El defecto es el seguro.
    """
    return (os.environ.get("FILEX_MOVE_SEGURO") or "1").strip() != "0"


#: Los dos motivos, en un solo sitio: los leen `mover_a_destino`, `_un_salto` y
#: la comprobación temprana de `convertir`, y una prueba se pone roja si se
#: separan. La trampa 44 es exactamente esto: el texto es parte del contrato.
MOTIVO_OCUPADO = "otro proceso tiene abierta esa ruta de salida"
MOTIVO_NO_ES_FICHERO = "la ruta de salida es un directorio que ya existe"

def _espera_gpu() -> float:
    """Tope de espera del lock de GPU alrededor del CODIFICADO, en segundos.

    La misma variable de entorno y el mismo valor por defecto que usa
    `gpu.Lock.__enter__`, para que una tanda mixta no tenga dos políticas —
    pero se lee aquí, no allí, porque este camino no usa `__enter__`
    (ver `_lock_gpu`).
    """
    return float(os.environ.get("FILEX_GPU_ESPERA", "900"))


@contextlib.contextmanager
def _lock_gpu(etiqueta: str, argv):
    """N25 — el lock de GPU rodea al CODIFICADO, no solo al sondeo.

    `bench/hito2-nvenc.md` §6.5 dejó el hueco acotado: `Motor` tiene tres asas
    —`sondear()`, `orden()` y `parar()`— y **ninguna envuelve la ejecución**,
    así que desde `motores.py` no hay forma honesta de sostener el lock entre
    `orden()` y `ejecutar()`. Quien sí puede es este método, que llama a las
    dos. El predicado es `gpu.usa_gpu(argv)`, **léxico y sobre el argv ya
    construido**: es lo único que no depende de que cada punto de invocación se
    acuerde de declarar que va a la tarjeta.

    ⚠ **NO se usa `with gpu.Lock(...)`, y el motivo está MEDIDO** (N4,
    `bench/bitrate-y-lock.md` §3, tanda limpia). `Lock.__enter__` llama a
    `guardia()`, que lanza `nvidia-smi`: **46 859,8 µs**, frente a los
    **1 341,1 µs** del par tomar/soltar. El parche literal de H2 cuesta
    **47 482,6 µs por conversión**, **×35,4** los 1 403,6 µs que su propio
    informe le atribuye — y contradice a su
    §6.3, que dice que *«preguntar por la VRAM en cada conversión sería caro;
    por eso la guardia se aplica al tomar el lock, una vez por tanda, y no por
    fichero»*. Aquí la guardia se aplica **solo cuando el lock se toma de
    verdad**: si quien llama ya lo tenía —un lote, `gpu.poseido()`— la
    reentrada no vuelve a preguntar por la VRAM.
    """
    if not gpu.usa_gpu(argv):
        # 0,9 µs para todo lo que no toca la tarjeta (MEDIDO, n=201).
        yield None
        return
    ya = gpu.poseido()
    l = gpu.Lock(etiqueta)
    if not l.tomar(espera=_espera_gpu()):
        raise gpu.GpuOcupada(f"no se pudo tomar el lock de GPU en {l.ruta}")
    try:
        if not ya:
            l.aviso = gpu.guardia()
        yield l
    finally:
        l.soltar()


def _negativa(e: OSError, destino: str) -> OSError:
    """Traduce la negativa de `os.replace` al motivo VERDADERO.

    El `errno` no distingue los dos casos en esta máquina (los dos son
    `EACCES`/`WinError 5`, MEDIDO), así que la pregunta se le hace al sistema
    de ficheros. Se hace **después** del fallo y solo para elegir la frase: la
    decisión de negarse ya está tomada. Ver `DestinoNoEsFichero`.
    """
    if os.path.isdir(destino):
        return DestinoNoEsFichero(e.errno, str(e), destino)
    return DestinoOcupado(e.errno, str(e), destino)


def mover_a_destino(origen: str, destino: str) -> str:
    """Saca la salida del desechable al destino **sin ventana**.

    Devuelve la ruta final. Lanza `DestinoOcupado` si un tercero lo tiene
    abierto, `DestinoNoEsFichero` si el destino es un directorio (N20), y deja
    pasar `FileNotFoundError` tal cual: *«no está»* y *«no se puede»* son dos
    cosas distintas (trampa 43), y aquí «no está» es un fallo de programación
    nuestro, no un ocupante.
    """
    dir_destino = os.path.dirname(os.path.abspath(destino)) or "."
    os.makedirs(dir_destino, exist_ok=True)
    if not _move_seguro():
        shutil.move(origen, destino)
        return destino
    try:
        os.replace(origen, destino)
        return destino
    except FileNotFoundError:
        raise
    except OSError as e:
        if e.errno != errno.EXDEV:
            raise _negativa(e, destino) from e

    # Volúmenes distintos: hay copia, pero el paso que DECIDE sigue siendo un
    # `os.replace`. El temporal va en el directorio de destino —no en el
    # desechable— porque si no, el `replace` final volvería a cruzar volúmenes.
    parcial = os.path.join(dir_destino, f".filex-{uuid.uuid4().hex}.parcial")
    try:
        shutil.copy2(origen, parcial)
        os.replace(parcial, destino)
    except OSError as e:
        try:
            os.remove(parcial)
        except OSError:
            pass
        if isinstance(e, FileNotFoundError):
            raise
        raise _negativa(e, destino) from e
    try:
        os.remove(origen)
    except OSError:
        pass  # el desechable se borra entero de todas formas
    return destino


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
        # N14 — el barrido de desechables huérfanos, UNA vez por proceso y en el
        # arranque. Va aquí y no en cada superficie por lo mismo que el cerrojo
        # de destino: las cuatro tienen el agujero y se cierra en el sitio en el
        # que las cuatro pasan. Es seguro porque sabe si el dueño vive
        # (`filex/trabajo.py::barrer_huerfanos`); un barrido que no lo supiera
        # sería la trampa 26 sobre otro recurso.
        self.barrido = barrer_huerfanos(una_vez=True)
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
            conv.motivo = MOTIVO_OCUPADO
            return conv

        # N20 — y por el mismo motivo que la línea de arriba: si el destino ya
        # es un DIRECTORIO, la conversión va a acabar negándose igual, así que
        # más vale no gastar los ~250 ms del motor. **La detección de arriba no
        # lo ve**: `os.replace(DIR, DIR)` funciona y devuelve `False` (MEDIDO,
        # caso A2 de `sonda_destino_dir.json`), que es correcto —nadie tiene ese
        # directorio abierto— y por eso hace falta esta línea aparte.
        if os.path.isdir(sal_abs):
            _soltar_destino(sal_abs)
            conv.motivo = MOTIVO_NO_ES_FICHERO
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
        #
        # N25: y va DENTRO del lock de GPU cuando el argv toca la tarjeta. El
        # `GpuOcupada` se convierte en un `Salto` con motivo, no en una
        # excepción que suba: quien pidió una conversión merece un veredicto,
        # y la tarjeta ocupada es una respuesta, no un error del programa.
        try:
            with _lock_gpu(f"filex-{arista.motor}", argv):
                r = invocacion.ejecutar(argv, timeout=timeout, cwd=t.ruta)
        except gpu.GpuOcupada as e:
            s.motivo = str(e)
            s.ruta = dentro
            return s
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
            # hacer contra quien no lo toma.
            #
            # **Se queda, aunque `mover_a_destino` ya no la necesite.** No es
            # redundancia: cuando el desechable y el destino están en volúmenes
            # distintos el movimiento final incluye una COPIA, y verlo aquí la
            # ahorra entera. Lo que ha dejado de ser es la única defensa —antes
            # de N12 había 681,4 µs entre esta línea y el `move`, y por ahí se
            # colaron 12 de 12 terceros—.
            if destino_ocupado_por_un_tercero(destino_final):
                s.veredicto = "fallo"
                s.motivo = MOTIVO_OCUPADO
                s.ruta = dentro
                return s
            try:
                # N12: `mover_a_destino` en vez de `t.recoger`, que hace
                # `shutil.move` y **pisa en silencio**. La detección y la acción
                # son ahora la misma llamada del sistema.
                mover_a_destino(t.destino(nombre), destino_final)
            except DestinoNoEsFichero:
                # N20: el mismo `errno` que el de abajo y **otro** motivo. La
                # comprobación temprana de `convertir` cubre el caso normal;
                # esta cubre el directorio que aparece MIENTRAS se convierte.
                s.veredicto = "fallo"
                s.motivo = MOTIVO_NO_ES_FICHERO
                s.ruta = dentro
                return s
            except DestinoOcupado:
                s.veredicto = "fallo"
                s.motivo = MOTIVO_OCUPADO
                s.ruta = dentro
                return s
            s.ruta = destino_final
        else:
            s.ruta = dentro  # el desechable vive hasta el final
        return s

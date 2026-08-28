"""Exclusión mutua por NOMBRE, entre procesos y —en Windows— entre usuarios.

Sale de `filex/nucleo.py`, donde N-b lo escribió para los destinos de conversión
(`bench/cerrojo-de-maquina.md`), y su propio autor dejó dicho que la mudanza era
*«una mudanza, no un diseño»*: cuarenta líneas que no dependen de nada de
`filex`. **Este módulo no importa nada de `filex` a propósito**, porque uno de
sus tres consumidores son los arneses `.py` de `bench/`, que no son la
aplicación.

Los TRES consumidores para los que está pensada la API —solo el primero está
conectado hoy—:

1. **Destinos de conversión** (`filex/nucleo.py`, hoy). Exclusión sin espera:
   si otro está escribiendo esa ruta, se dice y se sale. `Candado(clave).tomar()`.
2. **Cancelación entre procesos** (ronda siguiente). Lo que necesita no es
   excluir, es **saber si el dueño sigue vivo sin preguntarle a nadie por su
   PID** —que es lo que la trampa 31 dice que en esta máquina no se puede hacer
   bien—: un trabajo retiene su candado mientras vive, y `esta_libre()` responde
   por él. Los metadatos (`dueno()`) dicen quién es sin adivinarlo.
3. **El lock de GPU en Python** (fila C38 de `bench/lock-de-maquina.md`: *«0 de
   15 arneses `.py` toman el lock»*). Lo que necesita y los otros dos no es
   **espera con tope**: `tomar(espera=900)`. Por eso `espera` es un parámetro y
   no un modo.

---

## Los dos primitivos, y por qué los DOS

**El candado de fichero** (`msvcrt.locking` / `fcntl.flock` sobre un byte en el
offset `1<<30`) es el que trajo N-b, y sus tres virtudes están medidas: **lo
suelta el sistema operativo** —un `taskkill /F` deja al siguiente entrar en
551,9 µs, frente al huérfano eterno de un `O_CREAT|O_EXCL`—, deja los
**metadatos legibles desde fuera** mientras está tomado, y funciona en POSIX.
Su límite es que vive en `%TEMP%`, que es **por usuario**.

**El mutex con nombre en `Global\\`** cierra ese límite, y que se pueda es un
hecho MEDIDO de esta máquina, no una deducción
(`bench/salidas-cerrojo-unico/logs/sonda_maquina.log`,
`sonda_namespace.log`): **se crea desde un token de integridad MEDIA, con
`BUILTIN\\Administradores` marcado «solo para denegar» y sin
`SeCreateGlobalPrivilege` en la lista de privilegios**, y el objeto vive de
verdad en `\\BaseNamedObjects` —se abre por ruta absoluta con `NtOpenMutant`,
y el control negativo con un nombre inventado da `0xC0000034`—. Esto **refuta**
el pendiente 1 de `cerrojo-de-maquina.md`, que lo daba por imposible sin elevar.

**Y hay una trampa dentro de la vía buena, que es la parte que de verdad
costaba:** el mutex `Global\\` con descriptor de seguridad **por defecto** es de
máquina en el NOMBRE y de usuario en el ACCESO. Su DACL medida es
`(A;;0x1f0001;;;<el usuario>)(A;;0x1f0001;;;BA)(A;;0x1f0001;;;SY)`: **«Everyone»
no está**. Otro usuario recibiría `ERROR_ACCESS_DENIED` y un código escrito con
prisa lo llamaría «no hay infraestructura» y **degradaría a cerrojo de usuario
justo en el único caso que el mutex venía a cubrir**. Por eso aquí el objeto se
crea con SDDL explícito (`D:(A;;0x1F0001;;;WD)`) y por eso
`ERROR_ACCESS_DENIED` se trata como **ocupado**, nunca como degradación.

Se toman los dos, y no es redundancia gratuita: el mutex añade el cruce de
usuarios y sesiones; el fichero conserva los metadatos, la limpieza automática
y **la compatibilidad con cualquier `filex` que todavía no tenga el mutex**, que
sin esto dejaría de verse con uno que sí. El mutex cuesta **7,0 µs**.

## Lo que NO cubre — MEDIDO, no supuesto

**No cruza a la VM de WSL2, y el motivo de siempre era falso.** Se decía que
*«el `/tmp` de Ubuntu es otro sistema de ficheros»*; pero **el `%TEMP%` de
Windows SÍ se ve desde WSL2** por `/mnt/c` (9p/drvfs). Lo que no viaja no es el
fichero: es el candado. MEDIDO en las dos direcciones y **con control positivo**
(`sonda_wsl.log`): Windows toma `msvcrt.locking` y WSL2 se lo lleva igual;
WSL2 toma `flock` y Windows se lo lleva igual; y **dos procesos de WSL2 sí se
excluyen entre ellos sobre ese mismo fichero de `/mnt/c`**, así que no es que
`flock` no funcione sobre 9p. El mutex tampoco cruza: WSL2 es una VM, no
comparte el namespace de objetos del kernel de Windows.
"""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import time

_ES_WINDOWS = sys.platform == "win32"

#: El byte que se bloquea, MUY lejos del principio: así los metadatos siguen
#: siendo legibles desde otro proceso mientras el candado está tomado — MEDIDO
#: por N-b (`bench/salidas-cerrojo/logs/sonda_primitivos.log`, paso 2). Un
#: candado que impidiera ver quién lo tiene sería un candado indepurable, y
#: media trampa 31 es justamente no poder preguntar por el dueño.
OFFSET = 1 << 30

#: `MUTEX_ALL_ACCESS` para «Everyone». Sin esto el mutex es de usuario en el
#: acceso aunque su nombre sea global — MEDIDO (`sonda_dacl.log`).
SDDL_TODOS = "D:(A;;0x1F0001;;;WD)"

_PREFIJO_GLOBAL = "Global\\filex-"

WAIT_OBJECT_0 = 0x00000000
WAIT_ABANDONED = 0x00000080
WAIT_TIMEOUT = 0x00000102
ERROR_ACCESS_DENIED = 5

#: Degradar EN SILENCIO es la trampa 13 (`onnxruntime` cayendo a CPU sin un
#: error). Si una de las dos mitades no está disponible, el candado sigue
#: funcionando con la otra **y lo dice**.
AVISO_SIN_MUTEX = ("exclusión entre usuarios no disponible ({}): el cerrojo es "
                   "de usuario, no de máquina")
AVISO_SIN_FICHERO = ("candado de fichero no disponible ({}): sin metadatos ni "
                     "exclusión en POSIX")

_dir_cache: str | None = None
_sa_cache = None
_k32 = None


# --------------------------------------------------------------------------
# Dónde viven los candados
# --------------------------------------------------------------------------
def directorio() -> str:
    """El directorio de ficheros de candado. `FILEX_CERROJO_DIR` lo cambia."""
    global _dir_cache
    if _dir_cache is None:
        d = os.environ.get("FILEX_CERROJO_DIR") or os.path.join(
            tempfile.gettempdir(), "filex-destinos")
        os.makedirs(d, exist_ok=True)
        _dir_cache = d
    return _dir_cache


def _resumen(nombre: str) -> str:
    # El nombre es un resumen y no la cosa nombrada por dos motivos: una ruta de
    # 200 caracteres no cabe como nombre de fichero, y el directorio de candados
    # es común, así que no debe filtrar a qué ficheros está accediendo otro.
    return hashlib.sha256(nombre.encode("utf-8", "surrogatepass")).hexdigest()[:32]


def fichero(nombre: str) -> str:
    """El fichero de candado que le toca a `nombre`."""
    return os.path.join(directorio(), _resumen(nombre) + ".lock")


# --------------------------------------------------------------------------
# Mitad 1 — el mutex de máquina (solo Windows)
# --------------------------------------------------------------------------
def _kernel32():
    """`(kernel32, SECURITY_ATTRIBUTES)` o `(None, motivo)` si no hay vía."""
    global _k32, _sa_cache
    if _k32 is not None:
        return _k32, _sa_cache
    if not _ES_WINDOWS:
        return None, "no es Windows"
    try:
        import ctypes
        import ctypes.wintypes as wt

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        adv = ctypes.WinDLL("advapi32", use_last_error=True)
        k32.CreateMutexW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.LPCWSTR]
        k32.CreateMutexW.restype = wt.HANDLE
        k32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
        k32.WaitForSingleObject.restype = wt.DWORD
        k32.ReleaseMutex.argtypes = [wt.HANDLE]
        k32.ReleaseMutex.restype = wt.BOOL
        k32.CloseHandle.argtypes = [wt.HANDLE]
        k32.CloseHandle.restype = wt.BOOL
        adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
            wt.LPCWSTR, wt.DWORD, ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(wt.ULONG)]
        adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wt.BOOL

        class SECURITY_ATTRIBUTES(ctypes.Structure):
            _fields_ = [("nLength", wt.DWORD),
                        ("lpSecurityDescriptor", ctypes.c_void_p),
                        ("bInheritHandle", wt.BOOL)]

        sd = ctypes.c_void_p()
        n = wt.ULONG()
        if not adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                SDDL_TODOS, 1, ctypes.byref(sd), ctypes.byref(n)):
            return None, "SDDL no convertible"
        sa = SECURITY_ATTRIBUTES()
        sa.nLength = ctypes.sizeof(sa)
        sa.lpSecurityDescriptor = sd
        sa.bInheritHandle = False
        _k32, _sa_cache = k32, (ctypes, sa)
        return _k32, _sa_cache
    except Exception as e:            # noqa: BLE001 — cualquier fallo es «no hay vía»
        return None, f"{e.__class__.__name__}"


def _mutex_activo() -> bool:
    """`FILEX_CERROJO_MUTEX=0` apaga la mitad de máquina.

    Existe por el mismo motivo que el `FILEX_CERROJO_DESTINO` de N-b: para poder
    medir el antes y el después **dentro de la misma tanda**, que es la única
    forma honesta de comparar en esta máquina, y para que una prueba pueda
    fallar por el fallo que dice cubrir. El defecto es el seguro.
    """
    return (os.environ.get("FILEX_CERROJO_MUTEX") or "1").strip() != "0"


def _tomar_mutex(nombre: str, ms: int):
    """`(handle, ocupado, aviso)`. `handle` verdadero = tomado."""
    if not _mutex_activo():
        return None, False, ""
    k32, extra = _kernel32()
    if k32 is None:
        return None, False, AVISO_SIN_MUTEX.format(extra)
    ctypes, sa = extra
    ctypes.set_last_error(0)
    h = k32.CreateMutexW(ctypes.byref(sa), False, _PREFIJO_GLOBAL + _resumen(nombre))
    err = ctypes.get_last_error()
    if not h:
        if err == ERROR_ACCESS_DENIED:
            # **Ocupado, no «no disponible».** Existe un objeto con ese nombre
            # al que no tenemos acceso: lo tiene otro usuario con un descriptor
            # restrictivo. Negarse cuesta un reintento; degradar aquí sería
            # abrir el agujero exactamente donde el mutex hace falta.
            return None, True, ""
        return None, False, AVISO_SIN_MUTEX.format(f"error {err}")
    r = k32.WaitForSingleObject(h, ms)
    if r in (WAIT_OBJECT_0, WAIT_ABANDONED):
        # WAIT_ABANDONED = el dueño murió sin soltarlo y el SISTEMA nos lo
        # entrega. Es la misma virtud que el candado de rango de bytes: no hay
        # que escribir recuperación de huérfanos. MEDIDO: 9,7 µs tras un
        # `taskkill /F` (`sonda_maquina.log`, paso 3).
        return h, False, ""
    k32.CloseHandle(h)
    return None, True, ""


def _soltar_mutex(h) -> None:
    k32, _ = _kernel32()
    if k32 is None or not h:
        return
    try:
        k32.ReleaseMutex(h)
        k32.CloseHandle(h)
    except Exception:                 # noqa: BLE001
        pass


# --------------------------------------------------------------------------
# Mitad 2 — el candado de fichero (metadatos, POSIX, compatibilidad)
# --------------------------------------------------------------------------
def _bloquear_fd(fd: int) -> None:
    if _ES_WINDOWS:
        import msvcrt

        os.lseek(fd, OFFSET, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _tomar_fichero(nombre: str, metadatos: str):
    """`(fd, ocupado, aviso)`. `fd is None and not ocupado` = degradado."""
    try:
        fd = os.open(fichero(nombre), os.O_RDWR | os.O_CREAT, 0o600)
    except OSError as e:
        return None, False, AVISO_SIN_FICHERO.format(e.__class__.__name__)
    try:
        _bloquear_fd(fd)
    except OSError:
        os.close(fd)
        return None, True, ""
    try:
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        carga = f"{os.getpid()}\t{int(time.time())}\t{metadatos or nombre}\n"
        os.write(fd, carga.encode("utf-8", "surrogatepass"))
    except OSError:
        pass  # los metadatos son para el humano; la exclusión ya está tomada
    return fd, False, ""


def _soltar_fichero(fd: int, nombre: str) -> None:
    try:
        if _ES_WINDOWS:
            import msvcrt

            os.lseek(fd, OFFSET, os.SEEK_SET)
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
        # Barrer el fichero. **Solo en Windows, y no es pereza:** aquí un
        # fichero que alguien tiene abierto no se puede borrar, así que un
        # borrado con ÉXITO demuestra que nadie lo tenía. En POSIX el borrado
        # siempre funciona y abriría la carrera de «borro el candado de otro».
        # Y encima paga: sin el `remove`, el `open` siguiente cae sobre un
        # fichero con contenido y el `ftruncate` se paga entero — el ciclo es
        # ×2,3 MÁS LENTO (MEDIDO por N-b, `desglose.json`).
        try:
            os.remove(fichero(nombre))
        except OSError:
            pass


# --------------------------------------------------------------------------
# La API
# --------------------------------------------------------------------------
class Candado:
    """Un nombre, tomado por un solo proceso de la máquina a la vez.

    Se usa como gestor de contexto o a mano:

        with Candado("gpu") as c:
            if not c.tomado:
                ...            # lo tiene otro: `c.dueno` dice quién

        c = Candado(ruta_de_salida, metadatos=ruta_de_salida)
        if c.tomar():
            try: ...
            finally: c.soltar()

    `aviso` queda no vacío cuando una de las dos mitades no estaba disponible.
    **Nunca se degrada en silencio**: quien lo tome tiene que poder contarlo.
    """

    __slots__ = ("nombre", "metadatos", "_h", "_fd", "aviso", "tomado")

    def __init__(self, nombre: str, *, metadatos: str = ""):
        self.nombre = nombre
        self.metadatos = metadatos
        self._h = None
        self._fd: int | None = None
        self.aviso = ""
        self.tomado = False

    # -- tomar / soltar ----------------------------------------------------
    def tomar(self, espera: float = 0.0) -> bool:
        """`True` si es nuestro. `espera` en segundos, **con tope siempre**.

        `espera=0` (el defecto) es lo que quieren los destinos: no bloquear.
        El lock de GPU es el consumidor de `espera>0`; el tope es explícito
        porque un lock que espera para siempre es el defecto 2 del lock viejo
        (900 s de espera inútil tras un `taskkill`).
        """
        if self.tomado:
            return True
        limite = time.monotonic() + max(0.0, espera)
        while True:
            if self._intentar():
                return True
            if time.monotonic() >= limite:
                return False
            time.sleep(0.05)

    def _intentar(self) -> bool:
        avisos = []
        # El mutex primero: cuesta 7 µs y corta antes que el fichero, que son
        # ~713.
        h, ocupado, aviso = _tomar_mutex(self.nombre, 0)
        if ocupado:
            return False
        if aviso:
            avisos.append(aviso)
        fd, ocupado, aviso = _tomar_fichero(self.nombre, self.metadatos)
        if ocupado:
            _soltar_mutex(h)
            return False
        if aviso:
            avisos.append(aviso)
        if h is None and fd is None:
            # Ninguna de las dos mitades: no hay exclusión que ofrecer, y
            # decirlo es mejor que fingirla.
            self.aviso = "; ".join(avisos)
            return False
        self._h, self._fd, self.aviso = h, fd, "; ".join(avisos)
        self.tomado = True
        return True

    def soltar(self) -> None:
        if self._fd is not None:
            _soltar_fichero(self._fd, self.nombre)
            self._fd = None
        if self._h is not None:
            _soltar_mutex(self._h)
            self._h = None
        self.tomado = False

    # -- contexto ----------------------------------------------------------
    def __enter__(self) -> "Candado":
        self.tomar()
        return self

    def __exit__(self, *_e) -> None:
        self.soltar()

    @property
    def dueno(self) -> str | None:
        """Quién lo tiene, sin adivinarlo. `None` si está libre."""
        return dueno(self.nombre)


def esta_libre(nombre: str) -> bool:
    """¿Puede tomarse ahora mismo? Lo toma y lo suelta: no hay otra forma
    honesta de saberlo, y preguntar por el PID del dueño es lo que la trampa 31
    declara imposible en esta máquina."""
    c = Candado(nombre)
    if c.tomar():
        c.soltar()
        return True
    return False


def dueno(nombre: str) -> str | None:
    """Los metadatos del que lo tiene: `"pid\\tepoch\\tqué"`. `None` si libre.

    Se comprueba primero que esté ocupado **de verdad**, porque un `taskkill`
    deja el fichero con su carga aunque el candado ya esté libre: el fichero
    puede mentir, el candado no.
    """
    if esta_libre(nombre):
        return None
    try:
        with open(fichero(nombre), "rb") as f:
            crudo = f.read(4096)
    except OSError:
        return None
    txt = crudo.split(b"\x00")[0].decode("utf-8", "replace").strip()
    return txt or None

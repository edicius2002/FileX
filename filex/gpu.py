"""La tarjeta: exclusión, guardia de VRAM y **sondeo de capacidades NVENC**.

Tres cosas que el paquete no tenía y que entran juntas porque no se sostienen
por separado (N7 + hito 2).

──────────────────────────────────────────────────────────────────────────────
1. EL LOCK NO ES EL DE `filex/cerrojo.py`, Y ESO NO ES UN DESCUIDO
──────────────────────────────────────────────────────────────────────────────
`cerrojo.py` excluye con un **candado de rango de bytes** (`msvcrt.locking`) más
un mutex con nombre. `bench/lib/harness.sh:173` excluye con **`set -o
noclobber`** —creación exclusiva de fichero— sobre `%TEMP%/filex-gpu.lock`.
**Los dos primitivos no se ven entre sí**: un `.py` con `cerrojo.Candado` y un
`.sh` con el arnés se creerían los dos dueños de la tarjeta a la vez. MEDIDO en
`bench/hito2-nvenc.md` §5 con un control positivo en las dos direcciones.

Como **51 ficheros de `bench/` usan el arnés** y `harness.sh` es código
compartido que no me toca, aquí se implementa **el protocolo del arnés**, no el
de `cerrojo.py`:

* mismo fichero: ``$GPU_LOCK`` o ``%TEMP%/filex-gpu.lock``;
* misma semántica: ``O_CREAT|O_EXCL`` (lo que hace `noclobber`);
* mismo contenido, TSV de seis campos::

      etiqueta \\t pid_msys \\t winpid \\t imagen \\t epoch \\t raiz

  El arnés lee el campo 3 (winpid) y el 4 (imagen) para saber si el dueño sigue
  vivo, y el campo 2 en `gpu_release` para no robarle el lock a otro. En Python
  sobre Windows `os.getpid()` **ya es** el PID de Windows, así que los campos 2
  y 3 llevan el mismo número: no hay dos PID que separar como en Git Bash.

**Contrapartida declarada, y es la que `cerrojo.py` evita:** `O_CREAT|O_EXCL`
**no lo suelta el sistema operativo**. Un `taskkill /F` deja el fichero
huérfano. Por eso se implementa también la recogida de huérfanos del arnés
—comprobar que el PID vive y que el nombre de imagen coincide, porque Windows
reutiliza los PID— y el robo bajo un `mkdir` atómico, igual que él.

──────────────────────────────────────────────────────────────────────────────
2. LA GUARDIA: VRAM LIBRE **TOTAL**, NUNCA POR PID (trampa 31)
──────────────────────────────────────────────────────────────────────────────
Un lock solo excluye a quien lo toma. La sesión ajena que dejó una tanda 12
minutos sin procesar una imagen no iba a tomarlo nunca. Lo único que la ve es
mirar la tarjeta — y **por PID no se puede**: en WDDM
``nvidia-smi --query-compute-apps=used_memory`` devuelve ``[N/A]``.

Los umbrales son los del arnés, para que las dos mitades del proyecto no
discrepen: aviso a 7 500 MiB libres, aborto a 6 000.

──────────────────────────────────────────────────────────────────────────────
3. EL SONDEO DE NVENC: DOS FALSOS NEGATIVOS PAGADOS
──────────────────────────────────────────────────────────────────────────────
`av1_nvenc` aparece en ``ffmpeg -encoders`` **y en ``-h encoder=av1_nvenc``,
con sus formatos de píxel, sus dispositivos y sus AVOptions**: al construir el
argv no hay nada que mirar. Falla al **abrir el codificador**, con
``Codec not supported`` / ``No capable devices found`` y **cero fotogramas**.

Y la sonda tiene dos formas de mentir, las dos MEDIDAS:

* **El lienzo pequeño.** NVENC tiene mínimos de geometría: ``hevc_nvenc`` exige
  **129×33** y ``h264_nvenc`` **145×49** (frontera exacta por bisección, y el
  píxel de menos en cualquiera de los dos ejes da ``rc=-22``). Una sonda de
  64×64 —el reflejo de «que sea barata»— declara **averiados los dos
  codificadores que sí funcionan**.
* **El destino.** Da igual ``-f null``, ``NUL`` o un fichero: el `rc` es el
  mismo. Lo que NO da igual es el tamaño.

Por eso el lienzo de la sonda es ``256x256``: holgado sobre los dos mínimos.

El resultado se **cachea por proceso** —«sondear una vez, cachear el resultado,
y degradar solo a CPU», `PLAN-ORQUESTADOR.md` §4.3—: la sonda cuesta ~250 ms y
pagarla en cada conversión sería más cara que la ventaja que busca.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
import json
import signal
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from filex.cerrojo import Candado

#: Lienzo de la sonda. **No lo bajes.** Con 128×128 `hevc_nvenc` dice que no
#: funciona y con 144×144 lo dice `h264_nvenc`: mínimos 129×33 y 145×49, MEDIDOS
#: por bisección en `bench/salidas-hito2/sonda_frontera.json`.
SONDA_LIENZO = "256x256"

#: Fotogramas de la sonda. El tope va DENTRO de la orden (trampa 52): un filtro
#: de `lavfi` no termina solo. Ocho es arbitrario y **da igual**: el barrido de
#: 1 a 25 fotogramas da el mismo `rc` en los tres codificadores. Lo que decide
#: es la geometría, no la duración.
SONDA_FRAMES = 8

#: Tope del cliente, ADEMÁS del de dentro. La sonda medida tarda ~250 ms.
SONDA_TIMEOUT = 30.0

#: `AVERROR_EXTERNAL`. Es el `rc` con el que NVENC dice «esta tarjeta no sabe
#: hacer esto», y **no es el mismo** que el `-22` (EINVAL) de una invocación
#: mal formada. Registrar el `rc` es lo único que separa las dos cosas
#: (trampa 25, trampa 72).
AVERROR_EXTERNAL = -542398533
EINVAL = -22

#: Umbrales de la guardia, en MiB libres. Los mismos que `bench/lib/harness.sh`.
LIBRE_AVISO_MIB = int(os.environ.get("GPU_LIBRE_AVISO_MIB", "7500"))
LIBRE_MIN_MIB = int(os.environ.get("GPU_LIBRE_MIN_MIB", "6000"))

#: `abortar` (por defecto) · `avisar` · `ignorar`. Mismo nombre y mismos valores
#: que el arnés, para que una tanda mixta no tenga dos políticas.
GUARD = os.environ.get("GPU_GUARD", "abortar")


def fichero_lock() -> str:
    """El MISMO fichero que `bench/lib/harness.sh`.

    `GPU_LOCK` gana, como allí. Si no está, `%TEMP%/filex-gpu.lock` —que es lo
    que `/tmp/filex-gpu.lock` resuelve en el Git Bash de esta máquina, MEDIDO.
    """
    v = os.environ.get("GPU_LOCK")
    if v:
        return v
    d = os.environ.get("GPU_LOCK_DIR") or tempfile.gettempdir()
    return os.path.join(d, "filex-gpu.lock")


# --------------------------------------------------------------------------
# La tarjeta: cuánta VRAM queda LIBRE (total, nunca por PID)
# --------------------------------------------------------------------------
def vram_libre_mib() -> int | None:
    """MiB libres, o `None` si `nvidia-smi` no responde.

    `None` no es cero: quien llama decide. Confundir «no hay tarjeta» con «la
    tarjeta está llena» convierte una máquina sin GPU en una máquina bloqueada.
    """
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free",
             "--format=csv,noheader,nounits"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    linea = (r.stdout.decode("utf-8", "replace").strip().splitlines() or [""])[0]
    try:
        return int(linea.strip())
    except ValueError:
        return None


def ocupacion_ajena() -> tuple[int, str]:
    """`(0 despejado | 1 estrecha | 2 ocupada, motivo legible)`.

    Los tres estados del arnés, con los mismos umbrales. **Sin censo por PID**:
    la trampa 31 lo declara imposible en esta máquina, y un censo que solo da
    sospechosos no puede decidir nada automáticamente.
    """
    libre = vram_libre_mib()
    if libre is None:
        return 1, "nvidia-smi no responde: no se puede comprobar la ocupación"
    if libre < LIBRE_MIN_MIB:
        return 2, f"OCUPADA por terceros: {libre} MiB libres < {LIBRE_MIN_MIB} de mínimo"
    if libre < LIBRE_AVISO_MIB:
        return 1, f"ESTRECHA: {libre} MiB libres < {LIBRE_AVISO_MIB} de aviso"
    return 0, f"despejada: {libre} MiB libres"


class GpuOcupada(RuntimeError):
    """La tarjeta la ocupa alguien que no coopera. No hay lock que lo arregle."""


def guardia() -> str:
    """Aplica `GPU_GUARD`. Devuelve el aviso (vacío si todo despejado).

    Lanza `GpuOcupada` con `GPU_GUARD=abortar`, que es el valor por defecto:
    *«el modo de fallo no es un número algo peor, sino una tanda entera sin
    resultado»*.
    """
    estado, motivo = ocupacion_ajena()
    if estado == 0:
        return ""
    if estado == 2 and GUARD == "abortar":
        raise GpuOcupada(motivo)
    return motivo


# --------------------------------------------------------------------------
# La exclusión: el protocolo de `harness.sh`, no el de `cerrojo.py`
# --------------------------------------------------------------------------
def _imagen() -> str:
    import sys
    return os.path.basename(sys.executable or "python.exe")


def _campos(ruta: str) -> list[str]:
    try:
        with open(ruta, "r", encoding="utf-8", errors="replace") as f:
            return (f.readline().rstrip("\r\n")).split("\t")
    except OSError:
        return []


def _vivo(winpid: str, imagen: str) -> bool:
    """¿Vive el dueño del lock? PID **y nombre de imagen**, como el arnés.

    N29 (`bench/ci-y-contrato.md` §1, trampa 90/93): la comprobación **es de
    plataforma**, y antes de este arreglo solo existía la mitad de Windows —
    fuera de Windows, `tasklist` no existe, `subprocess.run` lanzaba
    `FileNotFoundError`, y el `except` de aquí devolvía «vivo» por el lado
    seguro del error. Consecuencia MEDIDA (`GPU_LOCK=/tmp/aislado.lock`, sin
    contención de máquina): un huérfano **nunca** se recupera fuera de
    Windows, determinista. El fallo no era "no hay tarjeta" ni "no hay
    ffmpeg": es que `_vivo()` respondía siempre `True`.

    En Windows los PID se reutilizan: comprobar solo el número deja que un
    proceso cualquiera se haga pasar por el dueño y el lock no se recupere
    jamás. Si no se puede preguntar, se responde «vivo»: **no robar** es el
    lado seguro del error. Eso vale en las dos ramas.
    """
    if not winpid:
        return True                      # formato viejo, sin PID: no lo robo
    if sys.platform == "win32":
        return _vivo_win32(winpid, imagen)
    return _vivo_posix(winpid, imagen)


def _vivo_win32(winpid: str, imagen: str) -> bool:
    try:
        r = subprocess.run(["tasklist", "/FI", f"PID eq {winpid}", "/NH", "/FO", "CSV"],
                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return True
    linea = r.stdout.decode("utf-8", "replace").strip().splitlines()
    linea = linea[0] if linea else ""
    if winpid not in linea:
        return False
    return (not imagen) or (imagen in linea)


def _vivo_posix(winpid: str, imagen: str) -> bool:
    """La mitad que faltaba. NO es la del arnés de shell (`_gpu_dueno_vivo`
    en `bench/lib/harness.sh`, que sigue con `/proc/$$/winpid` + `tasklist`
    y su propio problema conocido, trampa 90) — es Python puro sobre
    `os.kill`, que en POSIX SÍ tiene semántica estándar: `ProcessLookupError`
    (ESRCH) es "no existe", `PermissionError` (EPERM) es "existe pero no es
    mío". MEDIDO en Linux real (WSL2 Ubuntu, Python 3.14.4, no deducido de la
    documentación — trampa 45): `os.kill(pid_vivo, 0)` no lanza,
    `os.kill(pid_inexistente, 0)` lanza `ProcessLookupError`. En Windows
    `os.kill(pid, 0)` con un PID inexistente lanza `OSError` genérico
    (`WinError 87`), no `ProcessLookupError` — por eso esta función solo se
    invoca fuera de `win32`, nunca como sustituto de `_vivo_win32`.
    """
    try:
        pid = int(winpid)
    except ValueError:
        return True                      # campo ilegible: no robar
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False                     # el PID no existe: muerto de verdad
    except PermissionError:
        return True                      # vive, y no es nuestro
    except OSError:
        return True                      # no se pudo preguntar: no robar
    if not imagen:
        return True
    # El PID existe, pero POSIX también reutiliza PID: comprobar la imagen,
    # igual que `_vivo_win32` con la columna de `tasklist`. `/proc` es
    # Linux (no lo hay en macOS/BSD); sin él no se puede verificar la
    # identidad y se responde por el lado seguro.
    try:
        with open(f"/proc/{pid}/comm", "r", encoding="utf-8", errors="replace") as f:
            comm = f.read().strip()
    except OSError:
        return True
    if comm and not (comm in imagen or imagen.startswith(comm)):
        return False
    return True


#: Cuántas veces lo tiene ESTE proceso. No es un lujo: sin esto, un lote que
#: toma el lock para toda la tanda y luego pide `capacidad()` se bloquea contra
#: sí mismo, agota el tope y **cachea «la tarjeta no sabe hacer esto»** — un
#: falso negativo permanente producido por la propia defensa. La reentrancia es
#: DENTRO del proceso; hacia fuera el fichero sigue siendo uno y exclusivo.
_PROFUNDIDAD = 0


def poseido() -> bool:
    """¿Tiene este proceso el lock ahora mismo?"""
    return _PROFUNDIDAD > 0


class Lock:
    """Exclusión de máquina para la tarjeta mediante ``Global\\filex-gpu``.

    Uso::

        with gpu.Lock("H2-lote", espera=120):
            ...

    `espera` es un tope, y es obligatorio que exista: *«un lock que espera sin
    tope es el defecto 2 del lock viejo»* (`bench/cerrojo-unico.md`).
    """

    def __init__(self, etiqueta: str = "filex", *, ruta: str | None = None):
        self.etiqueta = etiqueta
        self.ruta = ruta or fichero_lock()
        self.mio = False
        self.reentrada = False
        self.aviso = ""
        self._candado = Candado("gpu", metadatos=etiqueta)

    def _linea(self) -> str:
        pid = os.getpid()
        return "\t".join([self.etiqueta, str(pid), str(pid), _imagen(),
                          str(int(time.time())), os.getcwd()])

    def _intentar(self) -> bool:
        try:
            fd = os.open(self.ruta, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            return False
        except OSError:
            return False
        try:
            os.write(fd, (self._linea() + "\n").encode("utf-8"))
        finally:
            os.close(fd)
        self.mio = True
        return True

    def _recoger_huerfano(self) -> bool:
        """Roba el lock si su dueño ya no vive. Bajo `mkdir` atómico, para que
        dos que esperan no lo roben a la vez — igual que el arnés."""
        c = _campos(self.ruta)
        if len(c) < 4 or _vivo(c[2], c[3]):
            return False
        robo = self.ruta + ".robo"
        try:
            os.mkdir(robo)
        except OSError:
            return False
        try:
            os.unlink(self.ruta)
        except OSError:
            pass
        try:
            os.rmdir(robo)
        except OSError:
            pass
        return True

    def tomar(self, espera: float = 0.0, *, intervalo: float = 0.25) -> bool:
        global _PROFUNDIDAD
        if _PROFUNDIDAD > 0:
            # Ya lo tenemos: reentrada. No se toca el fichero.
            _PROFUNDIDAD += 1
            self.mio = True
            self.reentrada = True
            return True
        limite = time.monotonic() + max(0.0, espera)
        while True:
            # Compatibilidad deliberada: mientras haya arneses Python o shell
            # que sólo toman O_EXCL, el fichero SIGUE SIENDO exclusión, no
            # metadato. Tomar sólo el mutex crearía dos poblaciones que no se
            # ven: precisamente la media exclusión de C38/C39.
            if self._intentar():
                if self._candado.tomar(espera=0):
                    self.aviso = self._candado.aviso
                    _PROFUNDIDAD = 1
                    return True
                # El mutex está ocupado por alguien ya migrado: deshace sólo
                # nuestro O_EXCL antes de esperar, sin tocar el suyo.
                self.mio = False
                c = _campos(self.ruta)
                if c and c[1] == str(os.getpid()):
                    try:
                        os.unlink(self.ruta)
                    except OSError:
                        pass
            # Reintento inmediato tras recoger huérfano: con espera=0 la
            # recuperación no puede dejar el lock libre y devolver False.
            elif self._recoger_huerfano():
                continue
            if time.monotonic() >= limite:
                return False
            time.sleep(intervalo)

    def soltar(self) -> None:
        """Borra el lock **solo si es nuestro**. Si otro nos lo robó por
        huérfano, no se lo quitamos de debajo — el campo 2 lo dice."""
        global _PROFUNDIDAD
        if not self.mio:
            return
        self.mio = False
        _PROFUNDIDAD = max(0, _PROFUNDIDAD - 1)
        if self.reentrada or _PROFUNDIDAD > 0:
            return
        self._candado.soltar()
        c = _campos(self.ruta)
        if c and c[1] == str(os.getpid()):
            try:
                os.unlink(self.ruta)
            except OSError:
                pass

    def __enter__(self) -> "Lock":
        if not self.tomar(espera=float(os.environ.get("FILEX_GPU_ESPERA", "900"))):
            raise GpuOcupada(f"no se pudo tomar el lock de GPU en {self.ruta}")
        try:
            self.aviso = guardia()
        except Exception:
            self.soltar()
            raise
        return self

    def __exit__(self, *_e) -> None:
        self.soltar()


def dueno() -> str | None:
    """La etiqueta del dueño del lock, o `None` si está libre."""
    from filex.cerrojo import dueno as _dueno
    d = _dueno("gpu")
    return d.split("\t", 2)[2] if d and "\t" in d else d


def esta_libre() -> bool:
    from filex.cerrojo import esta_libre as _libre
    return _libre("gpu")


def _hold(etiqueta: str, espera: float) -> int:
    """CLI para shell: conserva el mutex hasta SIGTERM/taskkill.

    El JSON se escribe sólo tras tomar el candado; el shell usa ``pid`` para
    verificar y terminar el dueño Windows, no el PID de un lanzador MSYS.
    """
    lock = Lock(etiqueta)
    if not lock.tomar(espera=espera):
        print(json.dumps({"ok": False, "pid": os.getpid()}), flush=True)
        return 2
    print(json.dumps({"ok": True, "pid": os.getpid(), "aviso": lock.aviso}), flush=True)
    vivo = True
    def parar(_s, _f):
        nonlocal vivo
        vivo = False
    signal.signal(signal.SIGTERM, parar)
    signal.signal(signal.SIGINT, parar)
    while vivo:
        time.sleep(0.1)
    lock.soltar()
    return 0


if __name__ == "__main__":
    import argparse
    _p = argparse.ArgumentParser()
    _p.add_argument("modo", choices=("hold",))
    _p.add_argument("etiqueta")
    _p.add_argument("--espera", type=float, default=900.0)
    _a = _p.parse_args()
    raise SystemExit(_hold(_a.etiqueta, _a.espera))


# --------------------------------------------------------------------------
# El sondeo de capacidades — EN EJECUCIÓN, cacheado por proceso
# --------------------------------------------------------------------------
#: `codec -> (funciona, rc, motivo)`. Se rellena la primera vez que se pregunta.
_CACHE: dict[str, tuple[bool, int, str]] = {}


def _ffmpeg() -> str:
    return os.environ.get("FILEX_FFMPEG", "ffmpeg")


def _sondear(codec: str) -> tuple[bool, int, str]:
    argv = [_ffmpeg(), "-hide_banner", "-nostdin", "-y",
            "-f", "lavfi", "-i", f"testsrc=size={SONDA_LIENZO}:rate=25",
            # El tope DENTRO de la orden. `lavfi` no termina solo, y un tope que
            # solo mata al cliente deja un `ffmpeg` vivo 9 minutos (trampa 52).
            "-frames:v", str(SONDA_FRAMES),
            "-c:v", codec, "-f", "null", os.devnull]
    try:
        r = subprocess.run(argv, stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=SONDA_TIMEOUT)
    except subprocess.TimeoutExpired:
        return False, 0, "la sonda agotó su tope"
    except OSError as e:
        return False, 0, f"no se pudo lanzar el sondeo ({type(e).__name__})"
    rc = r.returncode
    if rc > 2 ** 31:
        rc -= 2 ** 32
    if rc == 0:
        return True, 0, ""
    txt = r.stdout.decode("utf-8", "replace")
    if "No capable devices found" in txt or "Codec not supported" in txt:
        motivo = "la tarjeta no tiene ese codificador"
    elif rc == AVERROR_EXTERNAL:
        motivo = "el codificador falló al abrirse (AVERROR_EXTERNAL)"
    elif rc == EINVAL:
        # Aquí es donde se cuela el falso negativo del lienzo pequeño. Con
        # `SONDA_LIENZO` por encima de los dos mínimos MEDIDOS no debería pasar,
        # y si pasa hay que decir que puede no ser culpa de la tarjeta.
        motivo = ("la invocación no cumple las restricciones del codificador "
                  "(rc=-22); revisa la geometría de la sonda antes que la tarjeta")
    else:
        motivo = f"el sondeo falló (rc={rc})"
    return False, rc, motivo


def capacidad(codec: str, *, lock: bool = True) -> tuple[bool, int, str]:
    """¿Funciona `codec` **en esta máquina**? Sondeado, no deducido.

    Devuelve `(funciona, rc, motivo)` y lo cachea por proceso. Con `lock=False`
    se salta la exclusión: solo para cuando quien llama ya tiene el lock — un
    lock reentrante que se toma dos veces no excluye nada.
    """
    if codec in _CACHE:
        return _CACHE[codec]
    if not lock or poseido():
        # `poseido()` no es una optimización: sin él, quien tomó el lock para su
        # tanda entera se bloquearía contra sí mismo y cachearía un «no» falso.
        _CACHE[codec] = _sondear(codec)
        return _CACHE[codec]
    l = Lock(f"filex-sonda-{codec}")
    if not l.tomar(espera=float(os.environ.get("FILEX_GPU_ESPERA_SONDA", "30"))):
        # No se cachea: no hemos medido nada, hemos medido que estaba ocupado.
        # Cachear esto haría que un proceso de vida larga se quedara con «no»
        # para siempre por una coincidencia de 30 segundos.
        return False, 0, "la tarjeta está ocupada: no se pudo sondear"
    try:
        _CACHE[codec] = _sondear(codec)
    finally:
        l.soltar()
    return _CACHE[codec]


def olvidar() -> None:
    """Vacía la caché de capacidades. Para las pruebas y para un resondeo."""
    _CACHE.clear()


def usa_gpu(argv) -> bool:
    """¿Esta orden de ffmpeg va a tocar la tarjeta?

    Léxico y sobre el argv ya construido: es lo único que no depende de que
    cada punto de invocación se acuerde de declararlo — *«una disciplina que hay
    que recordar en cada punto de invocación no es una defensa»*.
    """
    return any(isinstance(a, str) and ("nvenc" in a or "cuda" in a) for a in argv)

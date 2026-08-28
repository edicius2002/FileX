"""El punto ÚNICO de invocación de motores externos.

`PLAN-ORQUESTADOR.md` §5.1, MEDIDO:

    Todo subproceso corre con `stdin=DEVNULL`, con las banderas no interactivas
    (`-y`, `-nostdin`), con timeout del lado del servidor y matando el ÁRBOL de
    procesos, no solo el padre.

**El orden importa: `stdin=DEVNULL` primero, las banderas después.** Y por eso
este módulo es el único sitio del proyecto que puede llamar a `subprocess`:

    «Una disciplina que hay que recordar en cada punto de invocación no es una
    defensa; hay que cerrarla en la construcción del proceso, donde ninguna vía
    pueda saltársela.»

Aquí no hay puntos de invocación: hay uno.

Evidencia de por qué (`bench/mcp-cabos-sueltos.md` §4.3, `bench/mcp-cabos-2.md` §1):
`-y` es **necesario y no suficiente**. Con `-y` en las siete invocaciones y una
ruta de salida que no existía, `concatenate_videos` se colgó 2 de 3 veces. El
A/B decisivo, dos herramientas idénticas salvo en una línea:

    conv_heredado  (stdin hereda la tubería)  -> 2/5 colgadas
    conv_devnull   (stdin=subprocess.DEVNULL) -> 0/5 colgadas

Y el alcance quedó cerrado: **26 de 26** herramientas de `video-audio-mcp` que
tocan ffmpeg cuelgan la sesión entera cuando la salida ya existe.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field

#: Ninguna invocación puede quedarse sin tope. `CLAUDE.md` §3: «no dejes
#: procesos colgados: estos motores dejan huérfanos vivos 13 minutos».
TIMEOUT_POR_DEFECTO = 120.0

#: Tope del propio matar-el-árbol. Un `taskkill` que se cuelga convierte la
#: defensa en el problema.
TIMEOUT_MATAR = 10.0

#: Cuánto se insiste en encontrar el contenedor de una cancelación que llegó
#: antes de que el demonio lo creara. Ver `_matar_contenedor_de`. Tope, no
#: bucle de reintento: se abandona en cuanto el cliente muere o vence el plazo.
ESPERA_CONTENEDOR = 3.0

_ES_WINDOWS = sys.platform == "win32"


@dataclass
class Resultado:
    """Lo que devuelve una invocación. `stderr` NO se expone al modelo.

    `PLAN-ORQUESTADOR.md` §5: «Nunca devolver `stderr` crudo al modelo. El error
    de un motor puede dirigir la siguiente acción del agente.» Quien construya
    una respuesta para un modelo usa `motivo`, no `err`.
    """

    argv: list[str]
    rc: int | None
    ms: float
    agotado: bool = False
    err: str = ""          # crudo: para el log y el humano, nunca para el modelo
    salida_txt: str = ""   # stdout, cuando el motor lo usa como canal de datos
    arrancado: bool = True  # False si el binario no existe
    huerfanos: list[int] = field(default_factory=list)
    #: El motor no falló: lo mataron. **Un `rc` distinto de cero no distingue
    #: «el motor rechazó la conversión» de «alguien canceló», y son dos cosas
    #: muy distintas para quien lee el resultado. Misma familia que la trampa 25
    #: de `CLAUDE.md`: sin registrar por qué murió, dos causas se confunden.
    cancelado: bool = False

    @property
    def ok(self) -> bool:
        return self.arrancado and not self.agotado and self.rc == 0

    @property
    def motivo(self) -> str:
        """Clasificación opaca del fallo. Esto sí puede cruzar hasta un modelo."""
        if not self.arrancado:
            return "motor_no_disponible"
        if self.cancelado:
            return "cancelado"
        if self.agotado:
            return "tiempo_agotado"
        if self.rc == 0:
            return "ok"
        return "el_motor_rechazo_la_conversion"


# --------------------------------------------------------------------------
# C34 — el asa que faltaba: las invocaciones EN VUELO, por hilo
# --------------------------------------------------------------------------
#
# `filex/mcp.py` declaraba el agujero con precisión: *«esto detiene el trabajo
# ENTRE saltos, no mata el motor en vuelo […] para eso `invocacion.ejecutar`
# tendría que devolver un asa del `Popen`»*. **No hace falta devolverla: hace
# falta que se pueda ALCANZAR desde otro hilo**, que es lo que pide un
# `job cancelar` — quien cancela nunca es quien convierte.
#
# La clave es el HILO, y no es una comodidad: un trabajo de `servicio.py` corre
# entero en su propio hilo (`threading.Thread(target=corre, ...)`), así que
# «la invocación en vuelo de este trabajo» y «la invocación en vuelo de este
# hilo» son la misma cosa. Con eso, `nucleo.py` no cambia ni una línea: no hay
# que enhebrar un parámetro por `convertir` → `_un_salto` → `ejecutar`, ni
# inventar un identificador de trabajo que el núcleo no tiene por qué conocer.
#
# LO QUE **NO** CUBRE, dicho con todas las letras:
#
# * **Un hilo, una invocación.** Si algún día un salto lanzara dos motores en
#   paralelo desde el mismo hilo, aquí solo estaría el último.
# * **Es de PROCESO**, igual que el cerrojo de destinos de `nucleo.py`: cancelar
#   desde otro proceso `filex` no alcanza este registro. PENDIENTE.
# * **Los `ident` de hilo se RECICLAN.** Por eso `olvidar_hilo()` no es opcional:
#   quien lanza el hilo tiene que llamarla al terminar, o un `ident` reutilizado
#   heredaría una cancelación ajena. `servicio.py` lo hace en un `finally`.
_EN_VUELO: dict[int, tuple[subprocess.Popen, list[str]]] = {}
_CANCELADOS: set[int] = set()
_CERROJO_VUELO = threading.Lock()


def cancelar_hilo(ident: int | None = None) -> bool:
    """Mata el motor que `ident` tiene en vuelo. Devuelve si había alguno.

    Marca el hilo **además** de matar: entre dos saltos no hay ningún `Popen`
    que alcanzar, y sin la marca la cancelación se perdería justo en la ventana
    en la que el trabajo cambia de motor. La marca la lee `ejecutar()` antes de
    arrancar el siguiente, así que la cancelación es efectiva en los dos
    regímenes —con motor en vuelo y entre saltos— y no solo en uno.
    """
    if ident is None:
        ident = threading.get_ident()
    with _CERROJO_VUELO:
        _CANCELADOS.add(ident)
        par = _EN_VUELO.get(ident)
    if par is None:
        return False
    proc, argv = par
    # **El CONTENEDOR primero y el cliente después, y el orden es la mitad del
    # arreglo.** Matar el cliente NO mata el contenedor —MEDIDO, `CLAUDE.md` §3:
    # tres `soffice` sobrevivieron 37 minutos a un `taskkill /F /T`— y en cuanto
    # el cliente muere, el hilo del trabajo sale de `communicate`, vuelve al
    # núcleo y su `finally` **borra el directorio desechable**, que es el origen
    # del bind mount. Ése es exactamente el agravante medido: con el origen
    # borrado por debajo, `docker rm -f` responde «did not receive an exit
    # event». Al revés no hay carrera: cuando el contenedor está muerto, el
    # cliente sale solo y el desechable ya no le hace falta a nadie.
    #
    # En el camino del TIMEOUT esto ya estaba resuelto por otra vía —el
    # `timeout -k 5` de dentro dispara 10 s ANTES que el de fuera—; en el de la
    # CANCELACIÓN no había nada, y la distancia puede ser de minutos.
    # `espera_s`: ver `_matar_contenedor_de`. Cancelar puede llegar ANTES de que
    # el demonio haya creado el contenedor, y entonces la primera barrida no ve
    # nada. MEDIDO: 1 de 9 cancelaciones de un salto en contenedor dejaba un
    # huérfano por esa carrera. Se barre mientras el cliente siga vivo, que es
    # justo la ventana en la que el desechable todavía no se ha borrado.
    _matar_contenedor_de(argv, espera_s=ESPERA_CONTENEDOR, vivo=lambda: proc.poll() is None)
    _matar_arbol(proc)
    return True


def hilo_cancelado(ident: int | None = None) -> bool:
    with _CERROJO_VUELO:
        return (threading.get_ident() if ident is None else ident) in _CANCELADOS


def olvidar_hilo(ident: int | None = None) -> None:
    """Limpia el rastro de un hilo. **Obligatoria** al terminar el trabajo."""
    if ident is None:
        ident = threading.get_ident()
    with _CERROJO_VUELO:
        _CANCELADOS.discard(ident)
        _EN_VUELO.pop(ident, None)


def en_vuelo() -> int:
    """Cuántas invocaciones hay ahora mismo con un `Popen` vivo registrado."""
    with _CERROJO_VUELO:
        return len(_EN_VUELO)


def _fuentes_de_montaje(argv: list[str]) -> list[str]:
    """Las `source=` **de escritura** de los `--mount` de un `docker run`.

    Es lo ÚNICO que identifica al contenedor de esta conversión sin cambiar la
    orden: el directorio desechable de R18 es privado de cada salto. La
    alternativa limpia —`--cidfile`— vive en `filex/motor_contenedor.py`, y
    queda PENDIENTE (ver el informe).

    **Los montajes `readonly` NO cuentan, y esto no es un detalle.** Un motor en
    contenedor monta dos cosas: el desechable (escritura, único por conversión)
    y la ENTRADA en solo lectura, que es un fichero del corpus del usuario. Dos
    conversiones simultáneas del mismo fichero comparten la segunda, así que
    contarla convertiría la cancelación en un arma contra el trabajo del
    vecino — la misma familia que la trampa 26, con el destino compartido.
    """
    fuentes = []
    for i, a in enumerate(argv):
        if a != "--mount" or i + 1 >= len(argv):
            continue
        opciones = [t.strip() for t in argv[i + 1].split(",")]
        if "readonly" in opciones or "ro=true" in opciones or "ro" in opciones:
            continue
        for trozo in opciones:
            k, _, v = trozo.partition("=")
            if k.strip() in ("source", "src") and v:
                fuentes.append(os.path.normcase(os.path.normpath(v)))
    return fuentes


def _docker(sub: list[str]) -> str:
    """Un `docker` auxiliar, con tope. No pasa por `ejecutar()` a propósito:
    esto corre en el hilo de QUIEN CANCELA y no debe entrar en su registro."""
    try:
        p = subprocess.run(["docker"] + sub, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, errors="replace",
                           timeout=TIMEOUT_MATAR, check=False)
        return p.stdout or ""
    except Exception:
        return ""


def _matar_contenedor_de(argv: list[str], *, espera_s: float = 0.0,
                         vivo=None) -> list[str]:
    """Mata el contenedor que lanzó `argv`, si `argv` era un `docker run`.

    Se identifica por el **origen del bind mount de escritura**, que Docker
    devuelve literalmente en `.Mounts.Source` —MEDIDO en esta máquina: la ruta
    de Windows con barras normales vuelve tal cual, sin traducir a
    `/run/desktop/...`—. Devuelve los identificadores matados, para el log y
    para las pruebas.

    `espera_s` cubre la CARRERA DE ARRANQUE: entre que el cliente se lanza y
    que el demonio crea el contenedor pasan cientos de milisegundos, y en esa
    ventana `docker ps` **no lo ve**. Cancelar ahí mataba al cliente y dejaba
    nacer al huérfano — MEDIDO: 1 de 9. Se reintenta mientras `vivo()` diga que
    el cliente sigue en pie, porque es exactamente la ventana en la que el
    contenedor todavía puede aparecer y el desechable aún no se ha borrado.
    """
    if not argv:
        return []
    binario = os.path.splitext(os.path.basename(argv[0]))[0].lower()
    if binario != "docker" or "run" not in argv[1:3]:
        return []
    fuentes = set(_fuentes_de_montaje(argv))
    if not fuentes:
        return []
    limite = time.perf_counter() + max(espera_s, 0.0)
    while True:
        victimas = _victimas(fuentes)
        if victimas:
            _docker(["kill"] + victimas)
            return victimas
        if time.perf_counter() >= limite or (vivo is not None and not vivo()):
            return []
        time.sleep(0.15)


def _victimas(fuentes: set) -> list[str]:
    ids = [x for x in _docker(["ps", "-q"]).split() if x]
    if not ids:
        return []
    detalle = _docker(["inspect", "--format",
                       "{{.Id}}\t{{range .Mounts}}{{.Source}}\t{{end}}"] + ids)
    fuera = []
    for linea in detalle.splitlines():
        campos = [c for c in linea.strip().split("\t") if c]
        if not campos:
            continue
        montajes = {os.path.normcase(os.path.normpath(c)) for c in campos[1:]}
        if montajes & fuentes:
            fuera.append(campos[0])
    return fuera


def _matar_arbol(proc: subprocess.Popen) -> None:
    """Mata al hijo y a sus nietos.

    MEDIDO (`bench/mcp-cabos-sueltos.md` §4): un `ffmpeg.exe` **sobrevivió** a un
    `taskkill /F /T` sobre el servidor y hubo que matarlo por inventario. Matar
    el árbol es lo mínimo, no la garantía: quien necesite la garantía tiene que
    llevar inventario explícito (job object en Windows, grupo en POSIX).
    PENDIENTE: el inventario. Aquí queda el árbol, que es lo barato.
    """
    if proc.poll() is not None:
        return
    if _ES_WINDOWS:
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=TIMEOUT_MATAR,
                check=False,
            )
        except Exception:
            pass
    else:
        import signal

        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass
    try:
        proc.wait(timeout=TIMEOUT_MATAR)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def ejecutar(
    argv: list[str],
    *,
    timeout: float = TIMEOUT_POR_DEFECTO,
    cwd: str | None = None,
    entorno: dict[str, str] | None = None,
) -> Resultado:
    """Lanza un motor externo. Sin shell. Con `stdin` cerrado. Con tope.

    `argv` es una lista, siempre. No se acepta una cadena: morphos usa
    `bash -c` + `fmt.Sprintf` y tiene RCE (`analysis/00-licencias.md`).

    `cwd` debería ser SIEMPRE un directorio de trabajo desechable (R18): hay
    motores que escriben en el `cwd` del proceso y no en el destino.
    `ffmpeg -i x out.mpd` deja ahí 528 KB de segmentos DASH.
    """
    if isinstance(argv, str):  # defensa explícita, no un descuido de tipos
        raise TypeError("argv tiene que ser una lista; una cadena implicaría shell")
    if not argv:
        raise ValueError("argv vacío")

    if shutil.which(argv[0]) is None and not os.path.isfile(argv[0]):
        return Resultado(argv=list(argv), rc=None, ms=0.0, arrancado=False,
                         err=f"binario no encontrado: {argv[0]}")

    # C34: un hilo ya cancelado NO arranca el siguiente motor. Sin esto, cancelar
    # un camino de dos saltos mataría el primero y dejaría empezar el segundo.
    ident = threading.get_ident()
    with _CERROJO_VUELO:
        if ident in _CANCELADOS:
            return Resultado(argv=list(argv), rc=None, ms=0.0, cancelado=True,
                             err="cancelado antes de arrancar")

    creationflags = 0
    preexec = None
    if _ES_WINDOWS:
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        preexec = os.setsid  # grupo propio, para poder matar el árbol entero

    t0 = time.perf_counter()
    agotado = False
    salida = err = ""
    proc = subprocess.Popen(
        argv,
        # --- el orden de estas tres líneas ES la defensa ---
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        # ---------------------------------------------------
        cwd=cwd,
        env=entorno,
        shell=False,
        text=True,
        errors="replace",
        creationflags=creationflags,
        preexec_fn=preexec,
    )
    # El asa queda alcanzable ANTES del `communicate`, que es donde se pasa el
    # 99,9 % del tiempo. Y se comprueba la marca DENTRO del cerrojo: si la
    # cancelación llegó en la ventana entre el `Popen` y esta línea, no vio el
    # asa y hay que matar aquí — sin esto, esa ventana deja un motor inmortal.
    with _CERROJO_VUELO:
        tarde = ident in _CANCELADOS
        if not tarde:
            _EN_VUELO[ident] = (proc, list(argv))
    if tarde:
        _matar_contenedor_de(argv)      # el contenedor primero; ver cancelar_hilo
        _matar_arbol(proc)

    try:
        salida, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        agotado = True
        _matar_arbol(proc)
        try:
            salida, err = proc.communicate(timeout=TIMEOUT_MATAR)
        except Exception:
            pass
    finally:
        with _CERROJO_VUELO:
            _EN_VUELO.pop(ident, None)
            cancelado = ident in _CANCELADOS
    ms = (time.perf_counter() - t0) * 1000

    return Resultado(
        argv=list(argv),
        rc=proc.returncode,
        ms=ms,
        # Un motor cancelado no se agotó: si se marcaran las dos, `motivo`
        # diría «tiempo_agotado» de algo que nadie esperó.
        agotado=agotado and not cancelado,
        cancelado=cancelado,
        err=err or "",
        salida_txt=salida or "",
    )


def disponible(binario: str) -> str | None:
    """Ruta del binario, o None. Un motor cuyo binario falta se auto-excluye.

    Criterio de aceptación del hito 1: «un motor cuyo binario falta se
    auto-excluye y la CLI lo informa, en lugar de fallar».
    """
    return shutil.which(binario)

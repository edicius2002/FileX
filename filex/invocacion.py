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

import contextlib
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
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


# --------------------------------------------------------------------------
# a4 — el contenedor se DECLARA, no se adivina
# --------------------------------------------------------------------------
#
# N-a cerró C34 identificando el contenedor por el **origen de su bind mount de
# escritura** (`bench/cancelacion-y-servicio.md` §4.4). Funcionaba —contenedor
# muerto 9 de 9— y ella misma declaró el residuo: *«el identificador sigue
# siendo indirecto; se deduce del bind mount porque la orden no lo declara»*.
#
# Aquí la orden lo declara: `_argv_docker` pone un `--name` acuñado por
# `nombre_de_contenedor()`, y este módulo lo lee del propio `argv`. Lo que
# cambia no es el resultado, son cuatro propiedades:
#
# 1. **Cero lecturas del demonio para IDENTIFICAR.** La deducción necesitaba
#    `docker ps -q` + `docker inspect` de TODOS los contenedores de la máquina;
#    el nombre está en `argv[i+1]`.
# 2. **No depende de que `.Mounts.Source` devuelva la ruta de Windows literal.**
#    Eso está MEDIDO en esta máquina, pero es un detalle de implementación de un
#    tercero.
# 3. **La unicidad la impone el DEMONIO, no el generador** — MEDIDO
#    (`bench/salidas-contenedor/sonda_id.json`, S1): un segundo `docker run` con
#    el mismo `--name` sale con `rc=125` y *«Conflict. The container name … is
#    already in use»*. Una colisión sería un error visible, nunca un atropello
#    silencioso, que es la forma de la trampa 26.
# 4. **Alcanza al contenedor CREADO Y NO ARRANCADO**, que `docker ps` no lista y
#    la deducción por montajes no podía ver nunca. Es el huérfano que le costó a
#    N-a 1 de 9 en su primera tanda. Ver `_barrer_contenedor_de`.
#
# Y una propiedad de seguridad que no estaba antes: `_nombre_contenedor_de`
# **solo acepta un nombre con la forma que acuña FileX**. La cancelación no
# puede apuntar jamás a un contenedor que FileX no haya lanzado, aunque un
# `--name` llegara dentro de la orden del motor o de datos del usuario. Con la
# deducción por montajes esa garantía no existía: la daba el filtro de
# `readonly`, que es una convención, no un predicado sobre el identificador.

#: Prefijo de todo contenedor lanzado por FileX. Es lo que hace **censable** un
#: huérfano: `docker ps -a --filter name=filex-` los separa de los del usuario.
PREFIJO_CONTENEDOR = "filex-"

#: `filex-<pid en hex>-<uuid4>`. El PID no es decoración: `CLAUDE.md` §4.31 dice
#: que en esta máquina lo único atribuible de un proceso es su línea de órdenes;
#: aquí el propio nombre del contenedor dice qué proceso `filex` lo lanzó, que es
#: lo que hoy no se puede saber de un huérfano.
_RE_NOMBRE = re.compile(r"^filex-[0-9a-f]{1,8}-[0-9a-f]{32}$")


def nombre_de_contenedor() -> str:
    """Acuña un nombre de contenedor único. **El único sitio que lo hace.**

    El formato lo conoce este módulo y nadie más: quien acuña y quien valida
    son la misma pieza, así que no pueden divergir. `motor_contenedor.py` lo
    llama y lo pone en el `argv`; `_nombre_contenedor_de` lo lee de vuelta.
    """
    return f"{PREFIJO_CONTENEDOR}{os.getpid():x}-{uuid.uuid4().hex}"


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
    # el demonio haya arrancado el contenedor, y entonces el primer `docker
    # kill` falla. **Declarar el nombre NO cierra esa ventana** —el nombre no
    # existe hasta que el contenedor existe—, así que la espera de N-a sigue
    # haciendo falta entera. MEDIDO (`bench/contenedor-parar.md` §4, M7):
    # cancelando con el cliente ya corriendo y el contenedor todavía no,
    # **sin espera ni barrido quedan 9 huérfanos de 9**; con cualquiera de las
    # dos, 0 de 9. Se insiste mientras el cliente siga vivo, que es la ventana
    # en la que el desechable todavía no se ha borrado.
    muertos = _matar_contenedor_de(
        argv, espera_s=ESPERA_CONTENEDOR, vivo=lambda: proc.poll() is None)
    _matar_arbol(proc)
    # Y el barrido DESPUÉS de matar al cliente, que es el orden contrario al de
    # arriba y por un motivo distinto: el cliente puede haber CREADO el
    # contenedor sin llegar a arrancarlo, y en ese estado `docker ps` no lo
    # lista y `docker kill` no lo alcanza. Solo es posible porque el nombre lo
    # acuñó FileX: ver `_barrer_contenedor_de`.
    #
    # **Solo si el `kill` NO lo consiguió**, que es exactamente cuando el estado
    # raro puede existir: si el contenedor llegó a correr y se mató, `--rm` lo
    # limpia solo, y un `docker rm -f` de más costaría otra ida y vuelta al
    # demonio (~240 ms MEDIDOS) en el caso frecuente para no cambiar nada.
    if not muertos:
        _barrer_contenedor_de(argv)
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


@contextlib.contextmanager
def hilo_de():
    """El hilo de un trabajo, con su rastro BORRADO al salir. Pase lo que pase.

    N11. `bench/cancelacion-y-servicio.md` §4.3 dejó dicho el defecto con sus
    palabras:

        «Los `ident` de hilo se reciclan. `olvidar_hilo()` no es opcional:
        `servicio.py` la llama en un `finally` en los dos trabajos. Quien añada
        una tercera clase de trabajo tiene que hacer lo mismo, y **eso es una
        disciplina que hay que recordar**, que es justo lo que este repositorio
        evita en las invocaciones.»

    Es literalmente la frase de `CLAUDE.md` §5 sobre el `stdin=DEVNULL`: *«una
    disciplina que hay que recordar en cada punto de invocación no es una
    defensa»*. La respuesta que el proyecto ya dio una vez fue quitar el punto
    de invocación —hay uno— y la respuesta aquí es la misma: quitar el punto
    donde se olvida. `filex/servicio.py` no construye hilos de trabajo salvo en
    `Servicio._arrancar`, y `_arrancar` entra aquí; lo comprueba una prueba
    sobre el AST (`pruebas/test_cancelacion_procesos.py::ElAndamiajeEsUnMecanismo`).

    **NO se limpia al ENTRAR, y es deliberado.** Sería la simetría bonita y
    abriría una carrera real: entre `Thread.start()` y la primera línea del
    hilo, un `job(..., "cancelar")` puede marcar el `ident` recién nacido, y un
    borrado de cortesía a la entrada se tragaría esa cancelación. El reciclaje
    de `ident` solo puede ocurrir cuando el hilo anterior ya ha MUERTO, y para
    entonces su `finally` ya pasó por aquí: limpiar a la salida basta y no
    cuesta una ventana.

    Uso::

        with invocacion.hilo_de():
            ...          # todo el trabajo, con sus N saltos
    """
    try:
        yield threading.get_ident()
    finally:
        olvidar_hilo()


def _nombre_contenedor_de(argv: list[str]) -> str:
    """El `--name` que la ORDEN declara, si tiene la forma que acuña FileX.

    Sustituye a la deducción por el origen del bind mount de escritura que
    cerró C34 (`bench/cancelacion-y-servicio.md` §3). Aquella funcionaba pero
    era indirecta: contaba con que Docker devolviera la ruta de Windows literal
    en `.Mounts.Source`, y tenía que EXCLUIR los montajes `readonly` a mano
    porque la entrada es un fichero del usuario que dos conversiones del mismo
    fichero comparten — contarla habría matado el contenedor del vecino, que es
    la trampa 26 con otro recurso.

    **El filtro por `_RE_NOMBRE` es la mitad del arreglo, no una comprobación
    de higiene.** Sin él, un `--name` que llegara dentro de la orden del motor
    —o de datos del usuario— convertiría `cancelar_hilo` en un arma contra un
    contenedor ajeno. Con él, la cancelación **solo puede apuntar a un nombre
    que este módulo acuñó**, y esa garantía es sobre el identificador, no sobre
    una convención de montaje.
    """
    for i, a in enumerate(argv):
        candidato = ""
        if a == "--name" and i + 1 < len(argv):
            candidato = argv[i + 1]
        elif a.startswith("--name="):
            candidato = a[len("--name="):]
        if candidato and _RE_NOMBRE.match(candidato):
            return candidato
    return ""


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


def _docker_ok(sub: list[str]) -> bool:
    """Como `_docker`, pero lo que interesa es el `rc`, no la salida.

    Va aparte para no cambiarle la firma a `_docker`, del que cuelgan arneses
    ya publicados. Y hace falta un `rc`: `docker kill` sobre un contenedor que
    todavía no existe **falla**, y ése es justo el estado que hay que reintentar
    (la carrera de arranque). Sin mirar el `rc` no se distingue de haberlo
    matado — la trampa 25 en su versión de Docker.
    """
    try:
        p = subprocess.run(["docker"] + sub, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, errors="replace",
                           timeout=TIMEOUT_MATAR, check=False)
        return p.returncode == 0
    except Exception:
        return False


def matar_contenedor(nombre: str) -> bool:
    """`docker kill` de un contenedor **acuñado por FileX**. Devuelve si murió.

    Rechaza cualquier nombre que no tenga la forma de `nombre_de_contenedor()`:
    el punto de este cambio es que el identificador esté declarado y sea
    inconfundible, no que haya una vía genérica para matar contenedores.
    """
    if not nombre or not _RE_NOMBRE.match(nombre):
        return False
    return _docker_ok(["kill", nombre])


def barrer_contenedor(nombre: str) -> bool:
    """`docker rm -f` de un contenedor **acuñado por FileX**. Devuelve si lo había.

    Alcanza el estado que `matar_contenedor` no alcanza: **creado y no
    arrancado**. Ver `_barrer_contenedor_de` para por qué ese estado existe y
    por qué antes no había forma de nombrarlo.
    """
    if not nombre or not _RE_NOMBRE.match(nombre):
        return False
    return _docker_ok(["rm", "-f", nombre])


def _matar_contenedor_de(argv: list[str], *, espera_s: float = 0.0,
                         vivo=None) -> list[str]:
    """Mata el contenedor que lanzó `argv`, si `argv` era un `docker run`.

    Se identifica por el **`--name` que la propia orden declara**. Devuelve los
    nombres matados, para el log y para las pruebas.

    `espera_s` cubre la CARRERA DE ARRANQUE, que **no desaparece por declarar el
    nombre**: entre que el cliente se lanza y que el demonio arranca el
    contenedor pasan cientos de milisegundos —MEDIDO, mediana 686,1 ms
    (`sonda_id.json`, S4)—, y en esa ventana `docker kill` responde con error.
    Cancelar ahí mataba al cliente y dejaba nacer al huérfano: 1 de 9 en la
    primera tanda de N-a. Se reintenta mientras `vivo()` diga que el cliente
    sigue en pie, porque mientras el cliente vive el contenedor todavía puede
    aparecer. Tope, no bucle de reintento.

    Lo que el nombre SÍ añade es el cierre de la ventana que quedaba abierta:
    ver `_barrer_contenedor_de`.
    """
    if not argv:
        return []
    binario = os.path.splitext(os.path.basename(argv[0]))[0].lower()
    if binario != "docker" or "run" not in argv[1:3]:
        return []
    nombre = _nombre_contenedor_de(argv)
    if not nombre:
        return []
    limite = time.perf_counter() + max(espera_s, 0.0)
    while True:
        if matar_contenedor(nombre):
            return [nombre]
        if time.perf_counter() >= limite or (vivo is not None and not vivo()):
            return []
        time.sleep(0.15)


def _barrer_contenedor_de(argv: list[str]) -> list[str]:
    """`docker rm -f` del nombre declarado, DESPUÉS de matar al cliente.

    Cierra el único agujero que la deducción por montajes no podía cerrar. El
    cliente de `docker run` hace dos cosas: **crear** el contenedor y
    **arrancarlo**. Si el `taskkill` cae entre las dos, queda un contenedor
    creado y no arrancado: **`docker ps` no lo lista** —solo lista los que
    corren—, así que ni el barrido de montajes ni `docker kill` lo alcanzan, y
    con el desechable ya borrado por el `finally` del núcleo tampoco quedaba
    forma de nombrarlo. Es exactamente el huérfano medido de 1 de 9.

    `docker rm -f` sí alcanza a un contenedor creado, y aquí es seguro por una
    razón que antes no existía: **el nombre lo acuñó FileX y es único por
    invocación** —la unicidad la impone el demonio, MEDIDO (S1)—, así que este
    barrido no puede tocar el contenedor de otra conversión ni el del usuario.
    Con la deducción por montajes un barrido así habría sido impensable.

    Un solo intento y sin espera: si no hay nada, `docker rm` falla y ya está.
    """
    if not argv:
        return []
    binario = os.path.splitext(os.path.basename(argv[0]))[0].lower()
    if binario != "docker" or "run" not in argv[1:3]:
        return []
    nombre = _nombre_contenedor_de(argv)
    if not nombre:
        return []
    return [nombre] if barrer_contenedor(nombre) else []


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
        # El contenedor primero y el cliente después; ver `cancelar_hilo`. Y el
        # barrido solo si el `kill` no lo consiguió, por el mismo motivo.
        muertos = _matar_contenedor_de(argv)
        _matar_arbol(proc)
        if not muertos:
            _barrer_contenedor_de(argv)

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

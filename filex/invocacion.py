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
import time
from dataclasses import dataclass, field

#: Ninguna invocación puede quedarse sin tope. `CLAUDE.md` §3: «no dejes
#: procesos colgados: estos motores dejan huérfanos vivos 13 minutos».
TIMEOUT_POR_DEFECTO = 120.0

#: Tope del propio matar-el-árbol. Un `taskkill` que se cuelga convierte la
#: defensa en el problema.
TIMEOUT_MATAR = 10.0

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

    @property
    def ok(self) -> bool:
        return self.arrancado and not self.agotado and self.rc == 0

    @property
    def motivo(self) -> str:
        """Clasificación opaca del fallo. Esto sí puede cruzar hasta un modelo."""
        if not self.arrancado:
            return "motor_no_disponible"
        if self.agotado:
            return "tiempo_agotado"
        if self.rc == 0:
            return "ok"
        return "el_motor_rechazo_la_conversion"


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
    try:
        salida, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        agotado = True
        _matar_arbol(proc)
        try:
            salida, err = proc.communicate(timeout=TIMEOUT_MATAR)
        except Exception:
            pass
    ms = (time.perf_counter() - t0) * 1000

    return Resultado(
        argv=list(argv),
        rc=proc.returncode,
        ms=ms,
        agotado=agotado,
        err=err or "",
        salida_txt=salida or "",
    )


def disponible(binario: str) -> str | None:
    """Ruta del binario, o None. Un motor cuyo binario falta se auto-excluye.

    Criterio de aceptación del hito 1: «un motor cuyo binario falta se
    auto-excluye y la CLI lo informa, en lugar de fallar».
    """
    return shutil.which(binario)

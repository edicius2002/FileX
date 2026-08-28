"""El SERVICIO: los trabajos y la lógica de las cinco operaciones, sin protocolo.

Este módulo nació dentro de `filex/mcp.py` en el hito 4, y el hito 7 dejó
escrito por qué tenía que salir de ahí:

    «`Servicio` y `Trabajos` ya no son de MCP: los usan la API HTTP y el
    watcher. Lo dejo señalado, no hecho.»

**Y la prueba de que ya no eran de MCP era una importación al revés:**
`filex/api.py` hacía `from .mcp import Servicio, Trabajos` y `filex/watcher.py`
hacía `from .mcp import COMPLETADO, FALLIDO, Trabajos`. Dos superficies que no
hablan MCP importaban del módulo del protocolo — que es exactamente la forma que
R10 existe para evitar, solo que en el otro sentido: no es validación que se cae
a la superficie, es **núcleo que se quedó atrapado dentro de una**.

Reparto, después de la mudanza (N6):

``filex/nucleo.py``
    Convierte y verifica. No sabe qué es un trabajo.
``filex/servicio.py`` (este fichero)
    Convierte el núcleo en operaciones con **asa**: `convert` devuelve un
    `job_id` al empezar, `job` lo consulta y lo cancela. Cero protocolo.
``filex/mcp.py``, ``filex/api.py``, ``filex/cli.py``, ``filex/watcher.py``
    Transporte. Traducen a JSON-RPC, a HTTP, a `argv` o a un directorio
    vigilado, y **no reimplementan nada**.

**No hay reexportación desde `filex.mcp`, y es deliberado.** Un alias mantendría
viva la respuesta vieja a «¿dónde viven los trabajos?», que es justo la que N6
refuta, y no hay usuarios externos que proteger: esto es un repositorio de
investigación. `filex/mcp.py` sí importa de aquí lo que necesita para su propio
uso —no se puede construir un servidor sin el servicio— y `pruebas/test_hito7.py`
comprueba que **ninguna otra superficie** entra por esa puerta.

CANCELAR DE VERDAD (C34)
------------------------

Hasta el hito 7, `job(..., "cancelar")` era un `threading.Event` que se
consultaba **entre saltos**: el motor en vuelo seguía hasta terminar o hasta
agotar su tope. El propio código lo declaraba PENDIENTE y decía qué faltaba —un
asa del `Popen`—. Ya la hay: `filex.invocacion` lleva un registro de las
invocaciones en vuelo **por hilo**, y como el trabajo corre entero en su hilo,
cancelar es alcanzar ese registro y matar el árbol. Ver `bench/cancelacion-y-servicio.md`
para los números y para lo que NO cubre.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass, field

from . import cerrojo, confinamiento as _conf
from . import contrato, formatos, invocacion
from .nucleo import FileX

# **`subprocess` no se importa aquí, y no es un descuido: es la comprobación.**
# Todo motor externo se lanza por `filex.invocacion.ejecutar()`, que construye el
# proceso con `stdin=DEVNULL` ANTES de las banderas. Es la defensa que no se
# puede olvidar en un punto de invocación porque **no hay puntos de invocación:
# hay uno**. Y matar uno tampoco se hace aquí: se pide a `invocacion`, que es
# quien tiene el asa.

#: Tope duro de una conversión lanzada desde MCP. Ninguna invocación sin tope:
#: estos motores dejan huérfanos vivos 13 minutos.
TIMEOUT_MAXIMO = 900.0

#: El tope que se aplica cuando el modelo no dice nada — que es siempre, porque
#: `timeout_s` **no está en el catálogo**. Más alto que el de la CLI (120 s)
#: porque aquí la conversión no bloquea a nadie: el asa ya se entregó.
TIMEOUT_MCP = 300.0

#: Cuánto debe esperar el modelo entre sondeos de `job`. Es el «intervalo
#: sugerido por el servidor» del vocabulario de SEP-1686 (`PLAN-ORQUESTADOR.md`
#: §5.3), que fue eliminado de la especificación y hay que reconstruir a mano.
SONDEO_MS = 1000

#: Vocabulario de estado de SEP-1686. Se conserva aunque el mecanismo ya no
#: exista en el protocolo: es el que los clientes y los modelos reconocen.
TRABAJANDO, COMPLETADO, FALLIDO, CANCELADO = (
    "working", "completed", "failed", "cancelled")

#: Cada cuánto mira el vigilante si hay un mando de cancelación en el disco.
#: Es la mitad baja de la latencia de una cancelación entre procesos: la otra
#: mitad es lo que tarde el trabajo en cerrar su contrato.
INTERVALO_MANDO = 0.2

#: Cuánto espera `job(..., "cancelar")` a ver el efecto de un mando entregado a
#: OTRO proceso, antes de responder «entregado, todavía no atendido». Tope, no
#: bucle de reintento. La cancelación no es síncrona y no debe fingir que lo es:
#: esto no es una promesa, es hasta cuándo se mira.
ESPERA_MANDO = 3.0

#: Cuánto se insiste en tomar el candado del trabajo antes de arrancar su hilo.
#: Normalmente es instantáneo; la espera existe porque `cerrojo.esta_libre()`
#: —que es como OTRO proceso pregunta si el dueño vive— toma y suelta el
#: candado, y sin espera un sondeo ajeno que cayera en ese instante dejaría al
#: trabajo corriendo sin candado, es decir, con pinta de huérfano.
ESPERA_CANDADO = 0.5

#: Sufijo del fichero de mando. Un fichero por trabajo y por orden.
SUFIJO_MANDO = ".cancelar"

#: Prefijo de la clave de candado de un trabajo. No es una ruta: `cerrojo`
#: resume el nombre con `sha256`, así que el directorio de candados no filtra
#: qué trabajos hay en curso.
PREFIJO_TRABAJO = "filex-trabajo:"

#: Un `job_id` entra por la superficie —lo escribe el modelo o el usuario— y
#: aquí se usa para COMPONER NOMBRES DE FICHERO. `../` dentro de un `job_id`
#: sacaría el mando (y la lectura del trabajo) del directorio. Lista blanca,
#: denegar por defecto: es R1 aplicado a un identificador en vez de a una ruta.
_RE_JID = re.compile(r"^[0-9a-f]{6,64}$")
# ==========================================================================
# 1. Los trabajos — el asa que se entrega AL EMPEZAR
# ==========================================================================


@dataclass
class Trabajo:
    id: str
    tipo: str
    estado: str = TRABAJANDO
    creado: float = field(default_factory=time.time)
    fin: float | None = None
    resultado: dict | None = None
    cancelar: threading.Event = field(default_factory=threading.Event)
    hilo: threading.Thread | None = None

    @property
    def ms(self) -> float:
        return ((self.fin or time.time()) - self.creado) * 1000


class Trabajos:
    """Registro de trabajos, **persistido en disco**.

    `PLAN-ORQUESTADOR.md` §5.3: *el fallo de origen es que el trabajo sobrevivió
    a quien lo esperaba*. Si el `job_id` solo vive en el proceso del servidor
    MCP, una caída o una reconexión reproducen exactamente el fallo que se
    quería arreglar. Un JSON por trabajo sirve además a la CLI, al watcher y a
    la API: **los cuatro frentes ven el mismo trabajo**.
    """

    def __init__(self, directorio: str | None = None) -> None:
        self.dir = directorio or os.path.join(
            os.environ.get("TEMP") or "/tmp", "filex-trabajos")
        os.makedirs(self.dir, exist_ok=True)
        self._t: dict[str, Trabajo] = {}
        self._lock = threading.Lock()

    def _fichero(self, jid: str) -> str:
        return os.path.join(self.dir, f"{jid}.json")

    def nuevo(self, tipo: str) -> Trabajo:
        t = Trabajo(id=uuid.uuid4().hex[:12], tipo=tipo)
        with self._lock:
            self._t[t.id] = t
        self.volcar(t)
        return t

    def get(self, jid: str) -> Trabajo | None:
        with self._lock:
            t = self._t.get(jid)
        if t is not None:
            return t
        # No está en memoria: puede ser de otra sesión o de otra superficie.
        # **Y aquí el `job_id` deja de ser un identificador y pasa a ser parte
        # de una ruta**, así que se filtra antes de tocar el disco: es el
        # predicado léxico de R1 sobre un identificador. Sin esto, un `job_id`
        # con `../` convierte `job` en un lector de JSON ajenos — la misma forma
        # del oráculo de existencia que R4 evita, con otro nombre.
        if not _RE_JID.match(jid or ""):
            return None
        try:
            with open(self._fichero(jid), encoding="utf-8") as fh:
                d = json.load(fh)
        except OSError:
            return None
        return Trabajo(id=d["job_id"], tipo=d.get("tipo", "?"),
                       estado=d.get("estado", FALLIDO),
                       creado=d.get("creado", 0.0), fin=d.get("fin"),
                       resultado=d.get("resultado"))

    def volcar(self, t: Trabajo) -> None:
        tmp = self._fichero(t.id) + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({"job_id": t.id, "tipo": t.tipo, "estado": t.estado,
                           "creado": t.creado, "fin": t.fin,
                           "resultado": t.resultado},
                          fh, ensure_ascii=False)
            os.replace(tmp, self._fichero(t.id))
        except OSError:
            pass                                        # el disco no manda aquí

    def terminar(self, t: Trabajo, estado: str, resultado: dict) -> None:
        t.estado, t.resultado, t.fin = estado, resultado, time.time()
        self.volcar(t)


# ==========================================================================
# 1 bis. N10 — la cancelación deja de ser DE PROCESO
# ==========================================================================
#
# C34 cerró «cancelar de verdad» y declaró su propio alcance
# (`bench/cancelacion-y-servicio.md` §4.1):
#
#     «Es de PROCESO. El registro vive en la memoria de un `filex`. Cancelar un
#     trabajo leído del disco desde otro proceso no alcanza su `Popen`, y la
#     respuesta lo dice en vez de fingirlo: `motor_detenido: false`.»
#
# Es la MISMA FORMA que el cerrojo de destinos (trampa 26), y aquella se cerró
# en dos mitades que aquí vuelven a hacer falta las dos:
#
# **Mitad 1 — el MANDO.** Un fichero `<job_id>.cancelar` en el directorio de
# trabajos, que ya es el sitio donde las cuatro superficies se ven entre sí
# («los cuatro frentes ven el mismo trabajo»). Quien cancela lo escribe; el
# proceso dueño lo atiende con **un vigilante por proceso, no uno por trabajo**
# —un `scandir` cada `INTERVALO_MANDO`, no un hilo por conversión— y llama al
# `cancelar_hilo` de C34, que es el que ya sabe matar el árbol y el contenedor.
# El mando NO reimplementa la cancelación: la ALCANZA desde fuera del proceso.
#
# **Mitad 2 — la DETECCIÓN, que es la que faltaría si solo se hiciera lo obvio.**
# La lección de N-b y de P es que *un mecanismo que solo alcanza a quien coopera
# resuelve la mitad*: si el proceso dueño MURIÓ, no hay nadie que atienda el
# mando, y sin detección un trabajo `working` en el disco se queda `working`
# **para siempre** —MEDIDO, `bench/cancelacion-entre-procesos.md` §3—. Aquí la
# detección es un candado por trabajo, y usa exactamente el hueco para el que P
# construyó `filex/cerrojo.py`:
#
#     «Lo que necesita no es excluir, es saber si el dueño sigue vivo sin
#     preguntarle a nadie por su PID —que es lo que la trampa 31 dice que en
#     esta máquina no se puede hacer bien—: un trabajo retiene su candado
#     mientras vive, y `esta_libre()` responde por él.»
#
# El candado de rango de bytes **lo suelta el sistema operativo** cuando el
# proceso muere (MEDIDO por N-b: 551,9 µs tras un `taskkill /F`), así que
# «candado libre + disco dice `working`» es un huérfano, y lo es sin consultar
# un solo PID. `dueno()` da además el PID y el instante para el log, que es
# información para el humano y nunca la base de la decisión.
#
# **El trabajo no empieza a existir para el resto del mundo hasta que tiene su
# candado, y esa espera es la que hace que la detección no mienta.** Sin ella
# hay una ventana —trabajo ya escrito en el disco como `working`, candado
# todavía sin tomar— en la que otro proceso lo declararía huérfano siendo un
# trabajo recién nacido y perfectamente vivo. Es la misma familia que la ventana
# entre `Popen()` y el registro que C34 cerró dentro del cerrojo: **una
# detección con una ventana no es una detección, es un falso positivo con
# horario.** Ver `Servicio._arrancar` para por qué el candado se toma dentro del
# hilo y no fuera (afinidad de hilo del mutex, MEDIDO).

#: `FILEX_MANDO=0` apaga las dos mitades y devuelve el comportamiento exacto de
#: C34: cancelar desde otro proceso responde `motor_detenido: false`. Existe por
#: el mismo motivo que el `FILEX_CERROJO_MUTEX` de P —poder medir el antes y el
#: después DENTRO DE LA MISMA TANDA, que es la única comparación honesta en esta
#: máquina— y para que una prueba pueda fallar por el fallo que dice cubrir.
#: El defecto es el seguro.
def _mando_activo() -> bool:
    return (os.environ.get("FILEX_MANDO") or "1").strip() != "0"


def clave_de(jid: str) -> str:
    """La clave de candado de un trabajo. **El único sitio que la acuña.**"""
    return PREFIJO_TRABAJO + jid


def fichero_mando(directorio: str, jid: str) -> str:
    """El fichero de mando de un trabajo, o `""` si el `job_id` no es válido."""
    if not _RE_JID.match(jid or ""):
        return ""
    return os.path.join(directorio, jid + SUFIJO_MANDO)


def pedir_mando(directorio: str, jid: str) -> bool:
    """Deja la orden de cancelar en el disco. Devuelve si se pudo escribir.

    Es la única escritura de este canal, y es **de un solo sentido**: quien
    cancela no espera respuesta por aquí. La respuesta es el estado del trabajo,
    que ya se publica en el disco y que las cuatro superficies ya leen.
    """
    f = fichero_mando(directorio, jid)
    if not f:
        return False
    try:
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(f"{os.getpid()}\t{int(time.time())}\n")
        return True
    except OSError:
        return False


def _borrar_mando(directorio: str, jid: str) -> None:
    f = fichero_mando(directorio, jid)
    if not f:
        return
    try:
        os.remove(f)
    except OSError:
        pass


#: `(directorio de trabajos, job_id) -> (ident de hilo, Trabajo)`. Lo que este
#: proceso puede atender. Un mando de un trabajo que no está aquí no es nuestro.
_EN_CURSO: dict[tuple[str, str], tuple[int, Trabajo]] = {}
_CERROJO_MANDO = threading.Lock()
_VIGILANTE: threading.Thread | None = None


def _arrancar_vigilante() -> None:
    """Arranca el vigilante si no lo hay. **Se llama con `_CERROJO_MANDO` tomado.**"""
    global _VIGILANTE
    if _VIGILANTE is None:
        _VIGILANTE = threading.Thread(target=_vigilar, daemon=True,
                                      name="filex-mandos")
        _VIGILANTE.start()


def _vigilar() -> None:
    """Un `scandir` cada `INTERVALO_MANDO` mientras haya trabajos en curso.

    **Uno por proceso, no uno por trabajo**, y sin hilo cuando no hay nada que
    vigilar: el hilo nace con el primer trabajo y muere con el último. La
    decisión de morir se toma bajo el mismo cerrojo con el que se decide nacer,
    así que no hay ventana en la que un trabajo se registre contra un vigilante
    que ya estaba saliendo.
    """
    global _VIGILANTE
    while True:
        time.sleep(INTERVALO_MANDO)
        with _CERROJO_MANDO:
            items = list(_EN_CURSO.items())
            if not items:
                _VIGILANTE = None
                return
        pedidos: set[tuple[str, str]] = set()
        for d in {clave[0] for clave, _ in items}:
            try:
                with os.scandir(d) as it:
                    for e in it:
                        if e.name.endswith(SUFIJO_MANDO):
                            pedidos.add((d, e.name[:-len(SUFIJO_MANDO)]))
            except OSError:
                continue
        for clave, (ident, t) in items:
            if clave not in pedidos:
                continue
            # Las DOS cosas, igual que en `job(..., "cancelar")` dentro del
            # proceso: el `Event` cubre la ventana entre saltos, donde no hay
            # ningún `Popen` que matar, y `cancelar_hilo` mata el motor que esté
            # en vuelo ahora. Y el `Event` primero: si el hilo sale de
            # `communicate` entre las dos líneas, tiene que encontrarlo puesto o
            # el trabajo terminaría en `failed` en vez de en `cancelled`.
            t.cancelar.set()
            invocacion.cancelar_hilo(ident)


def _tomar_candado(t: Trabajo):
    """El candado que dice «este trabajo sigue vivo». `None` si no hay vía.

    No se hace `raise` si no se puede tomar: un trabajo tiene que poder correr
    aunque el directorio de candados no se deje escribir. Lo que NO se hace es
    callarlo — `convert` devuelve el aviso —, porque degradar en silencio es la
    trampa 13 y aquí la degradación es invisible desde fuera: un trabajo sin
    candado tiene la misma pinta que un huérfano.
    """
    if not _mando_activo():
        return None
    c = cerrojo.Candado(clave_de(t.id), metadatos=f"{t.tipo}\t{t.id}")
    return c if c.tomar(espera=ESPERA_CANDADO) else None


@contextlib.contextmanager
def en_curso(trabajos: Trabajos, t: Trabajo, candado):
    """Todo el andamiaje de un trabajo en vuelo, atado a su `with`.

    Tres cosas que antes estaban sueltas por el código y había que acordarse de
    hacer en cada clase de trabajo:

    1. `invocacion.hilo_de()` — el rastro del hilo, borrado pase lo que pase
       (N11: era un `finally` copiado en dos sitios).
    2. El registro del mando — lo que hace al trabajo alcanzable desde OTRO
       proceso (N10).
    3. El candado — lo que hace que otro proceso pueda saber que seguimos vivos,
       y su liberación, que es lo que le dice que ya no.
    """
    ident = threading.get_ident()
    clave = (trabajos.dir, t.id)
    with _CERROJO_MANDO:
        _EN_CURSO[clave] = (ident, t)
        _arrancar_vigilante()
    try:
        with invocacion.hilo_de():
            yield
    finally:
        with _CERROJO_MANDO:
            _EN_CURSO.pop(clave, None)
        if candado is not None:
            candado.soltar()
        # El mando se borra AL FINAL y siempre: si se quedara, el siguiente
        # trabajo con ese `job_id` nacería cancelado. No puede pasar con
        # `uuid4`, pero un fichero de mando que sobrevive a su trabajo es
        # basura con capacidad de hacer daño, y son 20 µs quitarla.
        _borrar_mando(trabajos.dir, t.id)


# ==========================================================================
# 2. Las respuestas — ruta y metadatos, dentro del presupuesto
# ==========================================================================


def _hallazgos_cortos(saltos, tope: int = 3) -> list[str]:
    """Los hallazgos del contrato, recortados. Nunca `stderr`.

    `RESULTADOS-MCP.md` §6: los tres servidores de referencia reenvían el
    `stderr` crudo de ffmpeg —**884-1.228 tokens, casi todo banner de
    compilación**— y el error nombra el comando que lo instala, que dirige la
    siguiente acción del agente. `invocacion.Resultado` ya separa `err` (log) de
    `motivo` (opaco); aquí solo cruza el segundo.
    """
    out = []
    for s in saltos:
        for h in (s.hallazgos or []):
            # Los `informativo` no cruzan: «el fichero declarado lleva el 100 %
            # de los bytes escritos» son 25 tokens para decir que todo fue bien.
            # El criterio operativo es tokens de respuesta, y esto no los paga.
            if h.get("severidad") == "informativo":
                continue
            if len(out) >= tope:
                return out
            out.append(f"{h.get('severidad', '?')}/{h.get('regla', '?')}: "
                       f"{str(h.get('mensaje', ''))[:110]}")
    return out


def _resumen_conversion(conv) -> dict:
    """`{ruta_salida, formato, bytes, ms, motor_usado, camino}` — el asa.

    MEDIDO: el asa cuesta **32-72 tokens con independencia del tamaño del
    fichero** (un MP4 de 15,5 MB devuelve 32, igual que un PNG de 316 B). Y no
    hay umbral por debajo del cual devolver el binario compense: el punto de
    rentabilidad está en **1-2 KB**, por debajo del tamaño de un icono.
    """
    d = {
        "ok": conv.ok,
        "veredicto": conv.veredicto,
        "camino": conv.camino.formatos if conv.camino else [],
        "motores": [s.arista.motor for s in conv.saltos],
        # `ms_motor`, no `ms`: el trabajo ya devuelve su tiempo de pared y dos
        # claves con el mismo nombre se pisan. Aquí van los motores; allí, el
        # reloj del trabajo. Que no coincidan es información, no ruido.
        "ms_motor": round(sum(s.ms for s in conv.saltos), 1),
    }
    if conv.ok:
        d["ruta_salida"] = os.path.abspath(conv.salida)
        try:
            d["bytes"] = os.path.getsize(conv.salida)
        except OSError:
            d["bytes"] = None
    else:
        d["motivo"] = conv.motivo
    if conv.aviso:
        d["aviso"] = conv.aviso
    hall = _hallazgos_cortos(conv.saltos)
    if hall:
        d["hallazgos"] = hall
    sobra = {n: b for s in conv.saltos for n, b in (s.sobrantes or {}).items()}
    if sobra:
        # El quinto punto en lenguaje de modelo: el motor escribió cosas que
        # nadie pidió. `ffmpeg -i x out.mpd` deja 528 KB de segmentos DASH.
        d["ficheros_no_declarados"] = sorted(sobra)[:5]
    return d


# ==========================================================================
# 3. El despachador — sin `async`, sin protocolo, para poder probarlo entero
# ==========================================================================


class Servicio:
    """Toda la lógica de las cinco herramientas, sin una línea de protocolo.

    Separarlo así no es estética: es lo que permite que `pruebas/test_hito4.py`
    ejercite las cinco herramientas **sin levantar un servidor**, y es también
    lo que hace evidente que aquí no hay validación propia — el único camino a
    disco pasa por `FileX`.
    """

    def __init__(self, fx: FileX, trabajos: Trabajos | None = None) -> None:
        self.fx = fx
        self.trabajos = trabajos or Trabajos()

    # ---------------------------------------------------------------- útiles

    @staticmethod
    def _denegado() -> dict:
        # R4: el MISMO mensaje que da el núcleo para «prohibido» y para «no
        # existe». Distinguirlos convierte el conversor en un oráculo de
        # existencia sobre el disco ajeno.
        return {"error": _conf.MENSAJE_OPACO}

    def _salida_de(self, entrada: str, directorio: str, destino: str) -> str:
        base = os.path.splitext(os.path.basename(entrada))[0]
        return os.path.join(directorio, f"{base}.{destino}")

    def _arrancar(self, t: Trabajo, cuerpo) -> str:
        """Lanza el hilo de un trabajo. **La única puerta, y por eso es un
        mecanismo y no una disciplina.**

        N11. Antes cada clase de trabajo construía su propio `threading.Thread`
        y tenía que acordarse de llamar a `invocacion.olvidar_hilo()` en un
        `finally`; C34 lo dejó escrito como pendiente: *«quien añada una tercera
        clase de trabajo tiene que hacer lo mismo, y eso es una disciplina que
        hay que recordar»*. Ahora el andamiaje entero —el rastro del hilo, el
        candado y el registro del mando— vive en `en_curso`, y una tercera clase
        de trabajo no puede olvidarse de él porque **no construye hilos**: llama
        aquí. `pruebas/test_cancelacion_procesos.py::ElAndamiajeEsUnMecanismo`
        lo comprueba sobre el AST de este fichero, no sobre su comportamiento.

        Devuelve el aviso de degradación, o `""`.

        **El candado se toma DENTRO del hilo del trabajo, y esta función espera
        a que esté tomado antes de volver.** Las dos mitades de esa frase son
        deliberadas y cada una arregla una cosa distinta:

        * *Dentro del hilo*, porque **un mutex de Windows tiene afinidad de
          hilo** y `cerrojo.Candado` toma uno — MEDIDO
          (`bench/salidas-cancelacion-procesos/sonda_afinidad.json`, celda C):
          `ReleaseMutex` desde un hilo que no es el dueño devuelve `False` con
          `ERROR_NOT_OWNER` (288). Soltar desde otro hilo *parece* funcionar
          —`esta_libre()` dice `True` después, celda B— pero funciona por el
          `CloseHandle` que viene detrás, no por el `ReleaseMutex` que falla.
          **Un mecanismo que se apoya en un efecto colateral no es un
          mecanismo**, y el día que `cerrojo` cachee asas dejaría de serlo sin
          avisar.
        * *Esperando a que esté tomado*, porque el trabajo ya figura `working`
          en el disco desde `Trabajos.nuevo()`, y un trabajo `working` sin
          candado es **un falso huérfano**: otro proceso lo declararía muerto
          estando recién nacido. La espera reduce esa ventana al tiempo de
          tomar el candado y le pone tope.
        """
        listo = threading.Event()
        caja: dict = {}

        def corre():
            # Tomar y soltar, los dos en ESTE hilo: ver el docstring.
            caja["candado"] = _tomar_candado(t)
            listo.set()
            with en_curso(self.trabajos, t, caja["candado"]):
                cuerpo()

        t.hilo = threading.Thread(target=corre, daemon=True, name=f"filex-{t.id}")
        t.hilo.start()
        # Tope siempre, también aquí: si el hilo no llegara a arrancar, quien
        # pidió la conversión no se queda colgado — se queda sin candado, que es
        # lo que dice el aviso.
        listo.wait(ESPERA_CANDADO + 1.0)
        if _mando_activo() and caja.get("candado") is None:
            return ("sin candado de trabajo: otro proceso no podrá saber si "
                    "este sigue vivo")
        return ""

    # ------------------------------------------------------------ herramientas

    def list_targets(self, formato_origen: str, formato_destino: str = "") -> dict:
        o = formatos.normaliza(formato_origen)
        if not formato_destino:
            d = self.fx.destinos(o)
            return {"origen": o, "destinos": d, "n": len(d),
                    "nota": "lista exhaustiva con los motores presentes; lo que "
                            "no está aquí no se puede hacer"}
        dst = formatos.normaliza(formato_destino)
        dec = self.fx.grafo.camino(o, dst)
        if not dec.hay:
            return {"origen": o, "destino": dst, "posible": False,
                    "motivo": dec.motivo}
        r = {
            "origen": o, "destino": dst, "posible": True,
            "camino": dec.camino.formatos,
            "motores": [p.arista.motor for p in dec.camino.pasos],
            "saltos": dec.camino.saltos,
            # `real` = se ejecutó y salió bien. **El 41,0 % de las aristas que
            # los catálogos del sector declaran no existen**: decir «sin_sondear»
            # cuando no se ha medido es la diferencia con ellos.
            "evidencia": sorted({p.arista.estado for p in dec.camino.pasos}),
        }
        if dec.aviso:
            r["aviso"] = dec.aviso
        rech = [m for _, m in dec.rechazados if "rasteriza" in m or "pierde" in m]
        if rech:
            r["descartado"] = rech[0]
        return r

    def inspect(self, ruta: str) -> dict:
        """R8 y R18 NO aplican aquí, y está MEDIDO por qué.

        `bench/mcp-cabos-2.md` §5.3: el `inspect` **en proceso** cuesta
        **0,04–0,06 ms**; el staging que R8 le impondría, de **1,7 ms (1 MB) a
        166 ms (256 MB)** — de 30× a más de 3.000× la operación **a cambio de
        cero seguridad**, porque una lectura de cabeceras en proceso nunca
        entrega la ruta a un lector ajeno. Y no escribe nada, así que no hay
        censo que hacer: exento también de R18.

        **La validación de la ruta NO se salta**: la hace el núcleo, igual que
        para convertir. Lo que se salta es la copia, no el permiso.
        """
        if self.fx.confinamiento is not None:
            try:
                ruta = self.fx.confinamiento.resolver(ruta)
            except _conf.Denegado:
                return self._denegado()
        else:
            ruta = os.path.abspath(ruta)
        if not os.path.isfile(ruta):
            return self._denegado()

        v = contrato.verificador()
        if v is None:
            return {"error": "verificador_no_disponible"}
        t0 = time.perf_counter()
        s = dict(v.sondear_en_proceso(ruta))
        s["inspect_ms"] = round((time.perf_counter() - t0) * 1000, 3)
        s.pop("motor", None)
        ext = formatos.normaliza(os.path.splitext(ruta)[1])
        if s.get("firma") and ext and not _coherente(s["firma"], ext):
            # R11: el tipo real se decide por CONTENIDO, no por extensión. En un
            # conversor la extensión ELIGE EL MOTOR, así que la discrepancia no
            # es cosmética.
            s["aviso"] = (f"la extensión dice '{ext}' y la firma dice "
                          f"'{s['firma']}': manda la firma")
        return s

    def convert(self, entrada: str, salida: str, formato_destino: str = "",
                parametros: dict | None = None, timeout_s: float | None = None) -> dict:
        if formato_destino:
            d = formatos.normaliza(formato_destino)
            if formatos.normaliza(os.path.splitext(salida)[1]) != d:
                salida = os.path.splitext(salida)[0] + "." + d
        tope = min(float(timeout_s or TIMEOUT_MCP), TIMEOUT_MAXIMO)

        # El plan se calcula AQUÍ, antes de devolver el asa: es puro, cuesta
        # microsegundos, y es lo que hace que el modelo sepa desde el primer
        # turno que el camino rasteriza — en vez de descubrirlo al recoger.
        dec = self.fx.planificar(entrada, salida)
        if not dec.hay or (dec.camino is not None and dec.camino.saltos == 0):
            # **Falla AQUÍ, no dentro del trabajo.** Que no haya camino se sabe
            # en microsegundos y sin tocar el disco: devolver un `job_id` para
            # que el modelo descubra dos turnos después que era imposible es
            # gastar dos turnos en decir «no». `PLAN-ORQUESTADOR.md` §4.4:
            # *`convert` falla explícitamente ante una combinación no soportada,
            # nombrando la alternativa. El silencio es el modo de fallo
            # peligroso, no el error.*
            return {"error": dec.motivo or "origen y destino son el mismo formato",
                    "sugerencia": "list_targets con formato_origen dice a qué "
                                  "formatos se llega de verdad desde ahí"}
        t = self.trabajos.nuevo("convert")
        r = {"job_id": t.id, "estado": TRABAJANDO, "sondeo_ms": SONDEO_MS,
             "camino": dec.camino.formatos,
             "motores": [p.arista.motor for p in dec.camino.pasos]}
        if dec.aviso:
            r["aviso"] = dec.aviso

        def corre():
            try:
                conv = self.fx.convertir(entrada, salida, parametros or {}, timeout=tope)
                if conv.ok:
                    estado = COMPLETADO
                elif t.cancelar.is_set():
                    # C34: una conversión cancelada NO es una conversión fallida.
                    # Confundirlas es la misma familia que la trampa 25: dos
                    # causas distintas con la misma pinta de fallo.
                    estado = CANCELADO
                else:
                    estado = FALLIDO
                self.trabajos.terminar(t, estado, _resumen_conversion(conv))
            except Exception as e:                      # nunca la traza al modelo
                self.trabajos.terminar(t, FALLIDO, {"ok": False, "motivo": type(e).__name__})

        # El `finally` con `invocacion.olvidar_hilo()` que había aquí —y su
        # gemelo en `batch`— ya no está: lo hace `en_curso`, dentro de
        # `_arrancar`. N11.
        aviso = self._arrancar(t, corre)
        if aviso:
            r["aviso_cerrojo"] = aviso
        return r

    def batch(self, entradas: list[str], directorio_salida: str,
              formato_destino: str, parametros: dict | None = None) -> dict:
        d = formatos.normaliza(formato_destino)
        t = self.trabajos.nuevo("batch")

        def corre():
            hechos, fallidos, rutas = 0, 0, []
            for e in entradas:
                if t.cancelar.is_set():
                    break
                try:
                    conv = self.fx.convertir(e, self._salida_de(e, directorio_salida, d),
                                             parametros or {}, timeout=TIMEOUT_MCP)
                except Exception:
                    fallidos += 1
                    continue
                if conv.ok:
                    hechos += 1
                    if len(rutas) < 5:
                        rutas.append(conv.salida)
                else:
                    # R5: la misma opacidad POR ELEMENTO. `read_multiple_files`
                    # devolvió 6 mensajes con la lista blanca repetida seis
                    # veces: 419 tokens para no decir nada.
                    fallidos += 1
            self.trabajos.terminar(
                t, CANCELADO if t.cancelar.is_set() else
                (COMPLETADO if fallidos == 0 else FALLIDO),
                {"n": len(entradas), "convertidos": hechos, "fallidos": fallidos,
                 "directorio_salida": directorio_salida, "primeras_rutas": rutas})

        r = {"job_id": t.id, "estado": TRABAJANDO, "n": len(entradas),
             "sondeo_ms": SONDEO_MS}
        aviso = self._arrancar(t, corre)
        if aviso:
            r["aviso_cerrojo"] = aviso
        return r

    # ------------------------------------------------- N10, entre procesos

    def _es_huerfano(self, t: Trabajo) -> bool:
        """¿El trabajo dice `working` y su proceso dueño ya no vive?

        **La detección, y su coste es una llamada.** `cerrojo.esta_libre` lo
        contesta tomando y soltando el candado, que es la única forma honesta:
        preguntar por el PID del dueño es justo lo que la trampa 31 declara
        imposible de automatizar en esta máquina. El candado de rango de bytes
        **lo suelta el sistema operativo** cuando el proceso muere, así que
        «libre» aquí significa «nadie vivo lo retiene», no «nadie lo tomó».
        """
        return cerrojo.esta_libre(clave_de(t.id))

    def _recoger_huerfano(self, t: Trabajo) -> dict:
        """Cierra un trabajo cuyo dueño murió. **Un `working` eterno es peor que
        un `failed`**: el primero hace esperar para siempre a las cuatro
        superficies y al modelo."""
        self.trabajos.terminar(t, FALLIDO, {
            "ok": False, "motivo": "proceso_dueno_muerto"})
        return {"job_id": t.id, "estado": FALLIDO, "motor_detenido": False,
                "huerfano": True,
                "nota": "el proceso dueño del trabajo ya no vive: el trabajo se "
                        "cierra como fallido en vez de quedarse working para "
                        "siempre"}

    def _cancelar_ajeno(self, t: Trabajo) -> dict:
        """Cancela un trabajo que corre en OTRO proceso vivo.

        Se deja el mando en el disco y se mira **con tope** si surte efecto. No
        se promete nada: lo que se devuelve es lo que se vio.
        """
        t0 = time.perf_counter()
        if not pedir_mando(self.trabajos.dir, t.id):
            return {"job_id": t.id, "estado": t.estado, "motor_detenido": False,
                    "nota": "no se pudo dejar la orden de cancelar en el disco"}
        estado = t.estado
        while time.perf_counter() - t0 < ESPERA_MANDO:
            time.sleep(0.02)
            otro = self.trabajos.get(t.id)
            if otro is not None and otro.estado != TRABAJANDO:
                estado = otro.estado
                break
        ms = round((time.perf_counter() - t0) * 1000, 1)
        atendido = estado != TRABAJANDO
        return {"job_id": t.id, "estado": estado, "motor_detenido": atendido,
                "via": "entre procesos", "ms": ms,
                "nota": "el proceso dueño atendió el mando y mató su motor"
                        if atendido else
                        "orden dejada en el disco; el proceso dueño vive y la "
                        "atenderá, pero no lo ha hecho todavía"}

    def job(self, job_id: str, accion: str = "estado") -> dict:
        t = self.trabajos.get(job_id)
        if t is None:
            return {"error": "job_id desconocido"}
        # **Ajeno = está en el disco y no tiene hilo aquí.** Se mira en las dos
        # acciones y no solo al cancelar: un `working` cuyo dueño murió engaña
        # igual a quien pregunta por el estado, y es donde más se pregunta.
        ajeno = (_mando_activo() and t.hilo is None and t.estado == TRABAJANDO)
        if ajeno and self._es_huerfano(t):
            return self._recoger_huerfano(t)
        if accion == "cancelar" and ajeno:
            return self._cancelar_ajeno(t)
        if accion == "cancelar":
            # C34, CERRADO. Antes esto solo ponía un `Event` que se consultaba
            # ENTRE saltos: el motor en vuelo seguía hasta terminar o hasta
            # agotar su tope —que por MCP son 300 s—. Ahora se hacen las DOS
            # cosas, y hacen falta las dos: el `Event` cubre la ventana entre
            # saltos, donde no hay ningún proceso que matar, y `cancelar_hilo`
            # mata el árbol del motor que esté en vuelo AHORA.
            #
            # **La cancelación no es síncrona y no debe fingir que lo es.**
            # Matado el motor, el hilo del trabajo todavía tiene que salir de
            # `communicate`, pasar por el contrato y borrar su desechable; el
            # estado cambia ahí, no aquí. Lo que sí es inmediato —y es lo que se
            # devuelve— es si había un motor que matar.
            t.cancelar.set()
            hilo = t.hilo
            matado = False
            if hilo is not None and hilo.is_alive():
                matado = invocacion.cancelar_hilo(hilo.ident)
            elif hilo is None and t.estado == TRABAJANDO:
                # Trabajo leído del disco y **sin canal de mando**: solo se
                # llega aquí con `FILEX_MANDO=0`, es decir, midiendo el antes.
                # Con el canal puesto, este caso lo atienden `_cancelar_ajeno` o
                # `_recoger_huerfano` unas líneas más arriba.
                #
                # Y la nota vieja decía una cosa que NO era verdad — MEDIDO
                # (`bench/cancelacion-entre-procesos.md` §3.1): *«la cancelación
                # queda anotada»*. No quedaba anotada en ninguna parte.
                # `Trabajos.get` construye un `Trabajo` NUEVO al leerlo del
                # disco y **no lo guarda en `self._t`**, así que el
                # `t.cancelar.set()` de la línea de arriba marca un objeto que
                # se tira al volver de esta función. Es la trampa 25 en su forma
                # de mensaje: una respuesta honesta sobre el motor («no se
                # toca») acompañada de una promesa falsa sobre el resto.
                return {"job_id": t.id, "estado": t.estado,
                        "motor_detenido": False,
                        "nota": "el trabajo no corre en este proceso y no hay "
                                "canal de mando: el motor no se toca"}
            if t.estado == TRABAJANDO:
                return {"job_id": t.id, "estado": TRABAJANDO,
                        "motor_detenido": matado,
                        "nota": "motor detenido; el trabajo cierra su "
                                "verificación y pasa a cancelled"
                                if matado else
                                "cancelación pedida entre saltos; no se "
                                "arrancará el siguiente motor"}
            return {"job_id": t.id, "estado": t.estado, "motor_detenido": matado}
        base = {"job_id": t.id, "estado": t.estado, "ms": round(t.ms, 1)}
        if t.estado == TRABAJANDO:
            base["sondeo_ms"] = SONDEO_MS
            return base
        if accion == "resultado" and t.resultado:
            base.update(t.resultado)
        return base

    # ----------------------------------------------------------- despachador

    #: Nombre → (método, obligatorios). Un `enum` mal puesto no debe llegar al
    #: núcleo como un `TypeError`.
    _RUTAS = {
        "convert": ("convert", ("entrada", "salida")),
        "inspect": ("inspect", ("ruta",)),
        "list_targets": ("list_targets", ("formato_origen",)),
        "batch": ("batch", ("entradas", "directorio_salida", "formato_destino")),
        "job": ("job", ("job_id",)),
    }

    def despachar(self, nombre: str, args: dict) -> dict:
        r = self._RUTAS.get(nombre)
        if r is None:
            return {"error": f"herramienta desconocida: {nombre}"}
        metodo, obliga = r
        faltan = [k for k in obliga if args.get(k) in (None, "", [])]
        if faltan:
            return {"error": f"faltan parámetros obligatorios: {', '.join(faltan)}"}
        permitidos = {"convert": ("entrada", "salida", "formato_destino",
                                  "parametros", "timeout_s"),
                      "inspect": ("ruta",),
                      "list_targets": ("formato_origen", "formato_destino"),
                      "batch": ("entradas", "directorio_salida", "formato_destino",
                                "parametros"),
                      "job": ("job_id", "accion")}[nombre]
        kw = {k: v for k, v in args.items() if k in permitidos and v is not None}
        try:
            return getattr(self, metodo)(**kw)
        except _conf.Denegado:
            return self._denegado()
        except Exception as e:
            # Ni la traza ni el mensaje de la excepción: solo su clase. El error
            # de un motor puede dirigir la siguiente acción del agente.
            return {"error": "la operación no se pudo completar",
                    "clase": type(e).__name__}


_FAMILIAS = {
    "jpeg": {"jpg", "jpeg"}, "tiff": {"tif", "tiff"}, "matroska": {"mkv", "webm"},
    "isobmff": {"mp4", "mov", "m4a", "avif"}, "mp4": {"mp4", "mov", "m4a"},
    "texto": {"txt", "csv", "tsv", "json", "md", "html", "svg"},
}


def _coherente(firma: str, ext: str) -> bool:
    if firma == ext:
        return True
    fam = _FAMILIAS.get(firma)
    return bool(fam and ext in fam)

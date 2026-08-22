"""Hito 4 — la capa MCP. La segunda de las cuatro superficies, sobre el MISMO núcleo.

**Este fichero no valida ni una ruta.** R10 (`RESULTADOS-MCP.md` §10): *la
validación vive en el núcleo, no en la superficie*. La CLI de `kordoc` lee
ficheros fuera de `KORDOC_ROOT` con `exit=0` precisamente porque `safePath` vivía
en su `mcp.ts`. Aquí el único predicado sobre rutas que se ejecuta es
`filex.confinamiento.Confinamiento.resolver`, llamado **desde el núcleo**.

Lo que este fichero sí hace, y son las cinco decisiones que el hito 4 tenía que
tomar, todas respaldadas por una medición:

1. **Cinco herramientas escritas a mano, no una por motor.** Del registro salen
   los `enum` de los parámetros. Generar una herramienta por motor es el
   mecanismo exacto que produce las **27 herramientas planas** de
   `video-audio-mcp`, de las que **13 son casos particulares de 2**
   (`RESULTADOS-MCP.md` §4). *(Por qué cinco y no cuatro: ver `catalogo()`.)*
2. **Cada parámetro lleva su `description`.** MEDIDO: **0 de 193** parámetros de
   los tres catálogos de referencia la lleva (ídem §4). FastMCP deriva el
   esquema de las anotaciones de tipo y deja la semántica en el docstring, que
   es lo que produce un `array of object` sin una sola clave declarada.
3. **Ni `resources` ni `prompts`.** MEDIDO (`bench/mcp-cabos-2.md` §3): el
   cliente los enumera y **el modelo responde «NINGUNO»**. Coste sin retorno.
   Tampoco viven advertencias en `annotations`: de lo que declara el servidor,
   al modelo **solo le cruzan `description` e `input_schema`**.
4. **Ruta y metadatos, nunca contenido** — y «contenido» incluye base64 dentro
   de un `TextContent`, que es como aparece de verdad en el ecosistema
   (`image-worker-mcp`, ×87,6 de coste). El criterio es **tokens de respuesta**.
5. **Nada bloquea el bucle de eventos.** MEDIDO: **26 de 26** herramientas de
   `video-audio-mcp` cuelgan la sesión MCP entera cuando la salida ya existe
   (`bench/mcp-cabos-2.md` §1). La conversión corre en un hilo trabajador y
   `convert` devuelve un `job_id` **al empezar** (`PLAN-ORQUESTADOR.md` §5.2).

Arranque:

    .venv-mcp-filex/Scripts/python.exe -m filex.mcp --raiz D:/Work/research/FileX

Requiere **`mcp>=2.0.0`** (§5.3) y **un venv propio**: `mcp~=1.8.0` y
`mcp>=2.0.0` no coexisten.
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field

from . import confinamiento as _conf
from . import contrato, formatos
from .nucleo import FileX

# **`subprocess` no se importa aquí, y no es un descuido: es la comprobación.**
# Todo motor externo se lanza por `filex.invocacion.ejecutar()`, que construye el
# proceso con `stdin=DEVNULL` ANTES de las banderas. Es la defensa que no se
# puede olvidar en un punto de invocación porque **no hay puntos de invocación:
# hay uno**. Con la tubería JSON-RPC heredada, 26 de 26 herramientas de
# `video-audio-mcp` cuelgan la sesión entera.

# --------------------------------------------------------------------------
# Presupuestos. Son criterios de aceptación del hito 4, no adornos.
# --------------------------------------------------------------------------

#: `PLAN-ORQUESTADOR.md` §7, hito 4. RE-ACOTADO el 22/08 (`bench/mcp-cabos-2.md`
#: §4): en una sesión real de Claude Code el **cuerpo** del catálogo llega
#: DIFERIDO —pesado y ligero dan 26.941 = 26.941 tokens de entrada— así que este
#: número ya no es el multiplicador ×2,0–2,6 por turno. **Sigue valiendo como
#: higiene**: los nombres sí se inyectan siempre, es comportamiento de UNA
#: versión (2.1.238) y con `--tools ""` vuelve el régimen ansioso.
#:
#: **Y MEDIDO en este hito: NO SE CUMPLE, y no por culpa de la quinta
#: herramienta.** El catálogo vigente son **1.503 tokens**; las cuatro del plan,
#: **1.350** — también fuera. Lo que lo rompe son las dos reglas de cobertura:
#: la `description` de cada parámetro cuesta **460 tokens (30,6 %)** y los `enum`
#: generados del registro **235 (15,6 %)**. Quitando las dos se baja a **728**,
#: que es exactamente el catálogo estilo FastMCP con el que se midió un
#: **15–17 % de fallos silenciosos**. El desglose, en
#: `bench/salidas-hito4/h4_tokens_catalogo.json`.
PRESUPUESTO_CATALOGO = 1200

#: Toda respuesta cabe aquí salvo `inspect` (`RESULTADOS-MCP.md` §9.3, regla 1).
PRESUPUESTO_RESPUESTA = 200

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


# ==========================================================================
# 1. El catálogo
# ==========================================================================


def _enum_origen(fx: FileX) -> list[str]:
    """Formatos que un motor DISPONIBLE sabe leer. Del registro, no de una lista."""
    return sorted({a.origen for a in fx.grafo.aristas})


def _enum_destino(fx: FileX) -> list[str]:
    """Formatos que un motor DISPONIBLE sabe escribir.

    **Esto es el mecanismo de seguridad, no una comodidad.** MEDIDO
    (`bench/saturacion-herramientas.md` §3.5): cuando el catálogo no cubre lo
    que se pide, el modelo **no se abstiene** — llama a la más parecida y
    declara éxito con un dato falso, el **15–17 %** de las veces. Un `enum`
    exhaustivo generado del registro hace que la combinación imposible sea
    inexpresable, y de propina ahorra el mensaje de error que enumeraría las
    alternativas (`ffmpeg-mcp-lite` lo resuelve así).
    """
    return sorted({a.destino for a in fx.grafo.aristas})


#: Los parámetros de conversión que los adaptadores de `motores.py` leen de
#: verdad. **Cada uno con su descripción**: es el punto 2 de la cabecera.
#: Se declaran los que cambian el RESULTADO, no todos los que el motor acepta:
#: `resize_image` de `image-worker-mcp` cuesta **875 tokens** —casi lo mismo que
#: las tres herramientas del grupo `conversion` de docling juntas— por declarar
#: 25. La superficie de parámetros es la que fija el precio, no el número de
#: herramientas.
_PARAMETROS = {
    "ancho": {"type": "integer", "minimum": 1,
              "description": "Anchura en píxeles. Omitido: no se redimensiona."},
    "alto": {"type": "integer", "minimum": 1,
             "description": "Altura en píxeles. Omitido: no se redimensiona."},
    "calidad": {"type": "integer", "minimum": 1, "maximum": 100,
                "description": "1-100, solo en formatos con pérdida (jpg, webp, avif)."},
    "crf": {"type": "integer", "minimum": 0, "maximum": 63,
            "description": "Calidad de vídeo; menor es mejor y más bytes. "
                           "Defecto 23 (x264), 33 (VP9)."},
    "copia": {"type": "boolean",
              "description": "Recontenerizar sin recodificar; solo si el códec "
                             "cabe en el envase de destino."},
    "dpi": {"type": "integer", "minimum": 1,
            "description": "Puntos por pulgada al rasterizar un PDF. Usa los "
                           "NATIVOS del documento: sobremuestrear degrada."},
}


def _esquema_parametros() -> dict:
    return {
        "type": "object",
        "description": "Ajustes opcionales. Lo que no se pida aquí se deja como "
                       "esté: no se aplica ninguna transformación no solicitada.",
        "properties": dict(_PARAMETROS),
        "additionalProperties": False,
    }


def catalogo(fx: FileX) -> list:
    """Las herramientas, con sus `enum` generados del registro.

    Devuelve `list[mcp.types.Tool]` si el SDK está instalado y, si no, una lista
    de `dict` con la misma forma — para poder **medir el catálogo en tokens sin
    arrancar el servidor**, que es el criterio de aceptación del hito.

    ---

    **Son CINCO herramientas, y las cuatro del plan no eran alcanzables.** Es el
    hallazgo de este hito y va aquí, donde se toma la decisión:

    `PLAN-ORQUESTADOR.md` §4.4 fija **cuatro** (`convert`, `inspect`,
    `list_targets`, `batch`) y §5.2 fija, con evidencia independiente, que **toda
    operación larga devuelve un `job_id` al empezar, sin bifurcar entre «rápida
    bloquea» y «lenta devuelve asa»** — un clip de 5 s superó los 900 s del
    timeout del cliente y la conversión ya estaba hecha en disco. §5.3 añade que
    Tasks (SEP-1686) **fue eliminado de la especificación**, así que el asa hay
    que construirla entera. **Con `convert` no bloqueante hace falta una
    herramienta que consulte el trabajo, y con cuatro no cabe.**

    Lo que se conserva es el presupuesto que está MEDIDO —≤1.200 tokens de
    catálogo— y no el número, porque el propio §4.4 dice que *«el presupuesto se
    fija en tokens de catálogo, no en número de herramientas»* (el coste por
    herramienta varía ×11) y porque las 540 ejecuciones de
    `bench/saturacion-herramientas.md` **refutaron** que un catálogo grande
    elija peor: 27 herramientas acertaron 100 %/98 % frente al 85 %/77 % de 8.
    La quinta se paga en tokens, y el precio está medido en `bench/hito4-mcp.md`.
    """
    orig = _enum_origen(fx)
    dest = _enum_destino(fx)
    par = _esquema_parametros()

    def h(nombre, desc, esquema, **anot):
        return {"name": nombre, "description": desc, "inputSchema": esquema,
                "annotations": anot or None}

    herr = [
        h(
            "convert",
            # La descripción declara LO QUE NO HACE. MEDIDO: ninguno de los tres
            # servidores de referencia describe sus límites, y el modo de fallo
            # peligroso es el silencio, no el error.
            "Convierte un fichero y VERIFICA la salida. Devuelve un job_id al "
            "empezar (no bloquea): recoge el resultado con job. Devuelve rutas y "
            "metadatos, nunca contenido. Si no hay camino entre los dos formatos "
            "falla diciendo por qué; no convierte a algo parecido. Si dudas de "
            "que la conversión exista, pregunta antes a list_targets.",
            {
                "type": "object",
                "properties": {
                    "entrada": {
                        "type": "string",
                        "description": "Ruta absoluta del fichero de origen, dentro "
                                       "de las raíces permitidas.",
                    },
                    "salida": {
                        "type": "string",
                        "description": "Ruta absoluta del destino. Su extensión "
                                       "decide el formato si no se pasa "
                                       "formato_destino.",
                    },
                    "formato_destino": {
                        "type": "string", "enum": dest,
                        "description": "Formato de salida. La lista es exhaustiva: "
                                       "la generan los motores presentes en esta "
                                       "máquina. Lo que no está aquí no se puede "
                                       "hacer, y nada parecido sirve.",
                    },
                    # `timeout_s` NO se declara, y es una decisión medida: costaba
                    # **55 tokens de catálogo** (3,5 %) por un valor que el
                    # servidor sabe mejor que el modelo y que, mal puesto, deja
                    # un motor colgado. El tope existe —siempre—, lo fija
                    # `TIMEOUT_MCP` y lo acota `TIMEOUT_MAXIMO`. La API de
                    # `Servicio.convert` sí lo acepta, para la CLI y las pruebas.
                    "parametros": par,
                },
                "required": ["entrada", "salida"],
                "additionalProperties": False,
            },
            destructiveHint=True, openWorldHint=False,
        ),
        h(
            "inspect",
            "Lee las cabeceras de un fichero: formato real por firma de bytes, "
            "geometría, pistas, duración, páginas. No escribe nada. La firma "
            "manda sobre la extensión: un .png que sea un JPEG se detecta aquí.",
            {
                "type": "object",
                "properties": {
                    "ruta": {
                        "type": "string",
                        "description": "Ruta absoluta del fichero a examinar, dentro "
                                       "de las raíces permitidas.",
                    },
                },
                "required": ["ruta"],
                "additionalProperties": False,
            },
            readOnlyHint=True, openWorldHint=False,
        ),
        h(
            "list_targets",
            "Qué conversiones existen DE VERDAD en esta máquina, con los motores "
            "instalados. Úsala antes de convert cuando no estés seguro. Con solo "
            "el origen enumera los destinos; con los dos devuelve el camino, los "
            "motores y lo que se perdería, o el motivo de que no haya camino.",
            {
                "type": "object",
                "properties": {
                    "formato_origen": {
                        "type": "string", "enum": orig,
                        "description": "Formato de partida, sin punto (png). Solo "
                                       "los que algún motor presente sabe leer.",
                    },
                    "formato_destino": {
                        "type": "string",
                        "description": "Formato de llegada, opcional y sin punto. "
                                       "Si se pasa, la respuesta es el camino "
                                       "concreto en vez de la lista de destinos.",
                    },
                },
                "required": ["formato_origen"],
                "additionalProperties": False,
            },
            readOnlyHint=True, openWorldHint=False,
        ),
        h(
            "batch",
            "Convierte varios ficheros al mismo formato en un único trabajo. "
            "Devuelve un job_id al empezar; el resultado agregado se recoge con "
            "job. Devuelve rutas y contadores, nunca contenido. Los ajustes finos "
            "de convert no se aplican aquí: usa convert si los necesitas.",
            {
                "type": "object",
                "properties": {
                    "entradas": {
                        "type": "array", "items": {"type": "string"}, "minItems": 1,
                        "description": "Rutas absolutas de origen. Cada una se "
                                       "valida por separado; una rechazada no "
                                       "aborta las demás.",
                    },
                    "directorio_salida": {
                        "type": "string",
                        "description": "Dónde se escriben las salidas, con el mismo "
                                       "nombre base y la extensión nueva. Debe "
                                       "estar en una raíz de escritura.",
                    },
                    "formato_destino": {
                        "type": "string", "enum": dest,
                        "description": "Formato común a todas las entradas. Lista "
                                       "exhaustiva de lo posible.",
                    },
                },
                "required": ["entradas", "directorio_salida", "formato_destino"],
                "additionalProperties": False,
            },
            destructiveHint=True, openWorldHint=False,
        ),
        h(
            "job",
            "Consulta o cancela un trabajo de convert o batch. Nunca bloquea: si "
            "sigue en curso lo dice y sugiere cuándo volver a preguntar.",
            {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Identificador devuelto por convert o batch.",
                    },
                    "accion": {
                        "type": "string",
                        "enum": ["estado", "resultado", "cancelar"],
                        "description": "estado: fase y tiempo. resultado: además el "
                                       "veredicto y las rutas escritas. cancelar: "
                                       "detiene el trabajo.",
                    },
                },
                "required": ["job_id"],
                "additionalProperties": False,
            },
            openWorldHint=False,
        ),
    ]

    try:
        import mcp.types as t
    except Exception:                                   # medir sin SDK
        return herr
    return [
        t.Tool(
            name=x["name"],
            description=x["description"],
            inputSchema=x["inputSchema"],
            # Se anotan porque es correcto según la especificación y otros
            # clientes pueden usarlo. **No se apoya nada en ello**: MEDIDO contra
            # Claude Code 2.1.238, las anotaciones NO cruzan hasta el modelo y
            # NO cambian el permiso. Una advertencia de seguridad no puede vivir
            # aquí: vive en la `description`, y la defensa, en el núcleo (R10).
            annotations=t.ToolAnnotations(**{
                {"readOnlyHint": "read_only_hint",
                 "destructiveHint": "destructive_hint",
                 "idempotentHint": "idempotent_hint",
                 "openWorldHint": "open_world_hint"}[k]: v
                for k, v in (x["annotations"] or {}).items()
            }) if x["annotations"] else None,
        )
        for x in herr
    ]


def catalogo_serializado(fx: FileX) -> str:
    """El catálogo tal como viaja por el cable, para contarlo con `tiktoken`.

    Mismo método que `bench/scripts/mcp_probe_bin.py:262`, para que la cifra sea
    comparable con las **7.964 / 2.322 / 79** tokens de `RESULTADOS-MCP.md` §4.
    """
    herr = catalogo(fx)
    if herr and not isinstance(herr[0], dict):
        herr = [h.model_dump(exclude_none=True, by_alias=True) for h in herr]
    else:
        herr = [{k: v for k, v in h.items() if v is not None} for h in herr]
    return json.dumps(herr, ensure_ascii=False)


# ==========================================================================
# 2. Los trabajos — el asa que se entrega AL EMPEZAR
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
# 3. Los roots del cliente — R13, cacheados por sesión
# ==========================================================================


class Raices:
    """Interseca los *roots* del cliente con la lista blanca del servidor.

    **R13: se INTERSECAN, no la reemplazan.** `servers/filesystem`
    (`index.ts:181`) sustituye la lista, que es justo lo que no hay que hacer.

    **Cacheada por sesión — capacidad MEDIDA** (`bench/mcp-cabos-2.md` §2):
    Claude Code 2.1.238 declara `roots.listChanged: true` en su `initialize`, es
    decir **se compromete a avisar** cuando su lista cambie. Así que se pregunta
    una vez y se invalida con `notifications/roots/list_changed`, en vez de
    llamar a `roots/list` en cada operación. **Observar una emisión real sigue
    PENDIENTE** (en headless no hay forma de cambiar los roots a media sesión);
    si el cliente nunca emitiera, la caché no se invalida hasta el fin de sesión,
    que es el comportamiento correcto por defecto.
    """

    def __init__(self, fx: FileX, raices_servidor: list[str] | None) -> None:
        self.fx = fx
        self.servidor = list(raices_servidor or [])
        self._resuelto = False
        self._lock = threading.Lock()

    def invalidar(self) -> None:
        with self._lock:
            self._resuelto = False

    @staticmethod
    def _interseca(servidor: list[str], cliente: list[str]) -> list[str]:
        """Intersección de dos conjuntos de DIRECTORIOS, no de cadenas.

        Para cada par, la intersección es el más profundo si uno contiene al
        otro, y vacía si no se solapan. Comparando por segmentos (R2): sin el
        separador, la raíz `permitido` dejaría pasar `permitido_secreto`.
        """
        if not servidor:
            return list(cliente)
        if not cliente:
            return list(servidor)
        out = []
        for s in servidor:
            ns = _conf._norm(os.path.abspath(s))
            for c in cliente:
                nc = _conf._norm(os.path.abspath(c))
                if nc == ns or nc.startswith(ns + os.sep):
                    out.append(c)
                elif ns.startswith(nc + os.sep):
                    out.append(s)
        return sorted(set(out))

    async def asegurar(self, sesion) -> None:
        """Pregunta los roots UNA vez por sesión y fija el confinamiento.

        Se llama **al principio del cuerpo de cada herramienta, antes de
        cualquier efecto**. `PLAN-ORQUESTADOR.md` §5.3: con `mcp 2.0.0` el
        `Resolve(ListRoots)` puede ejecutar el cuerpo **dos veces** por llamada.
        Hoy Claude Code negocia `2025-11-25` y usa la vía clásica —una sola
        ejecución— pero la regla de idempotencia hasta esta línea se respeta
        igual, porque el cliente se actualizará.
        """
        with self._lock:
            if self._resuelto:
                return
        cliente: list[str] = []
        try:
            r = await sesion.list_roots()
            for raiz in getattr(r, "roots", []) or []:
                p = _uri_a_ruta(str(getattr(raiz, "uri", "")))
                if p:
                    cliente.append(p)
        except Exception:
            # Un cliente sin `roots` no es un error: es el caso de `--raiz` sola.
            cliente = []
        efectivas = self._interseca(self.servidor, cliente)
        try:
            self.fx.confinamiento = _conf.Confinamiento(efectivas) if efectivas else None
        except ValueError:
            self.fx.confinamiento = None
        # R6: denegar por defecto. Sin ninguna raíz, no se opera. Es lo ÚNICO
        # que decide esta capa sobre el acceso, y no es un predicado sobre
        # rutas: es «no hay lista blanca». Todo predicado sigue en el núcleo.
        self.sin_acceso = not efectivas
        with self._lock:
            self._resuelto = True


def _uri_a_ruta(uri: str) -> str:
    """`file:///D:/x` → `D:\\x`. Un root que no sea `file://` se ignora."""
    if not uri.startswith("file://"):
        return ""
    from urllib.parse import unquote, urlparse

    p = urlparse(uri)
    ruta = unquote(p.path)
    if os.name == "nt" and len(ruta) > 2 and ruta[0] == "/" and ruta[2] == ":":
        ruta = ruta[1:]
    return os.path.normpath(ruta)


# ==========================================================================
# 4. Las respuestas — ruta y metadatos, dentro del presupuesto
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
# 5. El despachador — sin `async`, sin MCP, para poder probarlo entero
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
                self.trabajos.terminar(
                    t, COMPLETADO if conv.ok else FALLIDO, _resumen_conversion(conv))
            except Exception as e:                      # nunca la traza al modelo
                self.trabajos.terminar(t, FALLIDO, {"ok": False, "motivo": type(e).__name__})

        t.hilo = threading.Thread(target=corre, daemon=True, name=f"filex-{t.id}")
        t.hilo.start()
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

        t.hilo = threading.Thread(target=corre, daemon=True, name=f"filex-{t.id}")
        t.hilo.start()
        return {"job_id": t.id, "estado": TRABAJANDO, "n": len(entradas),
                "sondeo_ms": SONDEO_MS}

    def job(self, job_id: str, accion: str = "estado") -> dict:
        t = self.trabajos.get(job_id)
        if t is None:
            return {"error": "job_id desconocido"}
        if accion == "cancelar":
            # PENDIENTE, y se dice: esto detiene el trabajo ENTRE saltos, no
            # mata el motor en vuelo. `PLAN-ORQUESTADOR.md` §5.3 pide que
            # `job_cancel` mate el árbol de procesos, y para eso
            # `invocacion.ejecutar` tendría que devolver un asa del `Popen`
            # (ver «cambios que pido» en `bench/hito4-mcp.md`). El salto en
            # curso lo acota su timeout, que nunca falta.
            t.cancelar.set()
            if t.estado == TRABAJANDO:
                return {"job_id": t.id, "estado": TRABAJANDO,
                        "nota": "cancelación pedida; el salto en curso termina "
                                "o agota su timeout"}
            return {"job_id": t.id, "estado": t.estado}
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


# ==========================================================================
# 6. El servidor
# ==========================================================================


def _texto(d: dict):
    import mcp.types as t

    return t.TextContent(type="text", text=json.dumps(d, ensure_ascii=False))


def construir(fx: FileX, raices: list[str] | None, trabajos: Trabajos | None = None):
    """Devuelve `(server, servicio, raices)`, ya cableados."""
    import mcp.types as t
    from mcp.server.lowlevel import Server

    servicio = Servicio(fx, trabajos)
    gestor = Raices(fx, raices)
    gestor.sin_acceso = False
    herramientas = catalogo(fx)

    async def on_list_tools(ctx, params):
        return t.ListToolsResult(tools=herramientas)

    async def on_call_tool(ctx, params):
        # Los roots se resuelven ANTES de cualquier efecto: el cuerpo es
        # idempotente hasta esta línea (§5.3, doble ejecución de Resolve).
        try:
            await gestor.asegurar(ctx.session)
        except Exception:
            pass
        if getattr(gestor, "sin_acceso", False):
            # R6: sin lista blanca no se opera, y se dice con el mismo mensaje
            # opaco que todo lo demás.
            return t.CallToolResult(content=[_texto(Servicio._denegado())],
                                    is_error=True)
        d = servicio.despachar(params.name, dict(params.arguments or {}))
        return t.CallToolResult(content=[_texto(d)],
                                is_error=bool(d.get("error")))

    async def on_roots_list_changed(ctx, params):
        gestor.invalidar()

    srv = Server(
        "filex",
        version="0.1.0",
        # Las `instructions` sí cruzan como texto del servidor. No se gastan en
        # repetir el catálogo: solo en lo que ninguna herramienta puede decir.
        instructions="FileX convierte ficheros y VERIFICA la salida. Devuelve "
                     "rutas, nunca contenido. Si dudas de que una conversión "
                     "exista, pregunta a list_targets: su respuesta es la "
                     "verdad de esta máquina, no un catálogo teórico.",
        on_list_tools=on_list_tools,
        on_call_tool=on_call_tool,
        on_roots_list_changed=on_roots_list_changed,
    )
    # Ni `on_list_resources` ni `on_list_prompts`: sin manejador, el servidor no
    # declara la capacidad. MEDIDO: el cliente los enumera y el modelo responde
    # «NINGUNO». Coste sin retorno.
    return srv, servicio, gestor


async def _correr(raices: list[str] | None) -> None:
    from mcp.server.stdio import stdio_server

    fx = FileX()
    srv, _, _ = construir(fx, raices)
    async with stdio_server() as (lectura, escritura):
        await srv.run(lectura, escritura, srv.create_initialization_options())


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="filex-mcp",
        description="Servidor MCP de FileX (stdio). Requiere mcp>=2.0.0.")
    p.add_argument("--raiz", action="append", default=None,
                   help="raíz permitida del servidor. Repetible. Se INTERSECA "
                        "con los roots del cliente (R13), no se reemplaza. Sin "
                        "ninguna y sin roots del cliente, no se opera (R6).")
    p.add_argument("--catalogo", action="store_true",
                   help="imprime el catálogo serializado y sale, para medirlo")
    args = p.parse_args(argv)

    if args.catalogo:
        print(catalogo_serializado(FileX()))
        return 0

    import anyio

    anyio.run(_correr, args.raiz)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

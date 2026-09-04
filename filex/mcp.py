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

**Y una corrección de este fichero sobre sí mismo (N6):** los trabajos y la
lógica de las cinco herramientas ya no viven aquí. Están en `filex/servicio.py`,
porque las usan también la API HTTP y el watcher —que lo demostraban
importándolas de este módulo— y porque un catálogo y un servidor MCP no son
sitio para el registro de trabajos de las cuatro superficies. Aquí queda lo que
es de verdad del protocolo: el catálogo, los *roots* y el servidor.

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

from . import confinamiento as _conf
from .nucleo import FileX
# El servicio vive en `filex/servicio.py` desde N6: lo comparten las CUATRO
# superficies y quedarse dentro del módulo del protocolo era la forma inversa de
# R10 —núcleo atrapado en una superficie— con dos importaciones que lo
# demostraban (`api.py` y `watcher.py` importaban de aquí). Esto es una
# importación **para uso propio**, no una reexportación: no se puede construir
# un servidor sin su servicio. Quien no hable MCP importa de `.servicio`.
from .servicio import Servicio, Trabajos

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
# 2. Los roots del cliente — R13, cacheados por sesión
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
        #: El candado ASÍNCRONO de N34, que sí se sostiene a través del
        #: `await` de `roots/list`. Se crea perezosamente dentro del bucle de
        #: eventos —`construir()` se llama fuera de él— y eso es seguro porque
        #: entre el `if` y la asignación no hay punto de suspensión.
        self._alock = None

    #: Cuántas veces ha llegado `notifications/roots/list_changed` en esta
    #: sesión. **Es la instrumentación del ítem 3 de C36, y su valor esperado
    #: hoy es 0.** El pendiente lleva abierto desde el hito 4 —*«observar una
    #: emisión real sigue PENDIENTE»*— y **no se puede forzar**: en headless no
    #: hay forma de cambiar los roots a media sesión. Lo que sí se puede es
    #: dejar puesto el contador, para que el día que llegue una emisión haya
    #: dónde verlo en vez de tener que volver a instrumentar. Coste: un entero.
    emisiones: int = 0

    #: Si esta variable de entorno nombra un fichero, cada emisión se anota
    #: además ahí, con marca de tiempo — porque el contador vive y muere con el
    #: proceso del servidor, y una emisión real llegaría en una sesión de
    #: Claude Code que nadie está observando desde dentro.
    VAR_REGISTRO = "FILEX_MCP_REGISTRO_ROOTS"

    def invalidar(self) -> None:
        with self._lock:
            self._resuelto = False
            self.emisiones += 1
            n = self.emisiones
        destino = os.environ.get(self.VAR_REGISTRO)
        if not destino:
            return
        try:
            import time
            with open(destino, "a", encoding="utf-8") as fh:
                fh.write("%s\troots/list_changed\tn=%d\tpid=%d\n"
                         % (time.strftime("%Y-%m-%dT%H:%M:%S"), n, os.getpid()))
        except OSError:
            # Un registrador que tumba el servidor no es un registrador.
            pass

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

        **Y no se cachea una denegación nacida de un fallo — MEDIDO**
        (`bench/mcp-cabos-y-techos.md` §2, celda M3). Con `roots/list` fallando
        una vez, el `except` de abajo dejaba `cliente = []`, y con el servidor
        también sin raíces salía `sin_acceso = True` **con `_resuelto = True`
        detrás**: la sesión quedaba denegada **para siempre**, y el reintento
        del cliente no volvía a preguntar (0 llamadas nuevas, `sin_acceso`
        seguía en `True`). Es la **trampa 43** sobre otro recurso —*toda
        detección por excepción necesita separar «no se puede» de «no está»*—
        y aquí la separación no hace falta hacerla por la clase de la
        excepción, que no es clasificable: basta **no sellar el resultado
        cuando el resultado es «ninguna raíz» y hubo un fallo al preguntar**.
        El coste es una ida y vuelta más por llamada, y sólo en la sesión que
        ya estaba denegada de todos modos.

        **Y la petición va SERIALIZADA, no sólo la lectura de la caché —
        MEDIDO** (`bench/roots-concurrencia.md`, N34). El `threading.Lock` de
        arriba se suelta antes del `await`, así que N herramientas que entren a
        la vez con la caché fría hacían **N** `roots/list` (8 de 8 con N=8).
        Mientras un fallo se sellaba eso era sólo ruido; desde M3 **no**, y
        entonces **dos llamadas concurrentes pueden traer respuestas distintas
        y el ORDEN decide con qué queda la sesión**: en las dos órdenes medidas
        del mismo par, el estado final salió `sin_acceso=False` con
        confinamiento en una y `sin_acceso=True` sin él en la otra. Con el
        candado asíncrono sostenido a través del `await`, N=1..8 dan **1** ida
        y vuelta y el estado final **no depende del orden**. **No empeora el
        caso del cliente mudo**: con un `roots/list` que no vuelve, ni una sola
        herramienta responde ni con candado ni sin él (lo que cambia es que hay
        1 petición colgada en vez de N). Coste en caliente —el 99 % de las
        llamadas— **0,4 µs de mediana, el mismo que sin candado**.

        **Y ningún resultado nacido de un FALLO se sella, ni siquiera el que
        sale con raíces — MEDIDO** (ídem, celda N3). M3 dejó abierta una
        esquina que no necesita concurrencia para morder: con `--raiz` puesta,
        `_interseca(servidor, [])` devuelve la lista del **servidor entera**,
        así que un `roots/list` que falla no deja «ninguna raíz» sino
        **todas**, y con `efectivas` no vacía se sellaba `_resuelto = True`
        **para toda la sesión**, con un confinamiento MÁS ANCHO que la
        intersección que R13 exige. La condición correcta es `not fallo`.

        **Y un `Confinamiento` que no se puede construir es «sin acceso», no
        «sin confinamiento» — MEDIDO** (ídem, celda N7). `Confinamiento` lanza
        `ValueError` cuando ninguna raíz confina (R3: una raíz que normaliza a
        la raíz de una unidad no confina nada), y este `except` lo convertía en
        `confinamiento = None` **dejando `sin_acceso = False`**, porque
        `efectivas` no estaba vacía. Y `nucleo._resolver()` con
        `confinamiento is None` devuelve la ruta tal cual: con un cliente que
        declare `C:\\` como root, FileX leía un fichero de **otro directorio y
        de otra unidad**, con el control de raíz normal denegando los dos.
        `Confinamiento.__init__` ya lo dice —*«R6: denegar por defecto. Sin
        ninguna raíz accesible, no se arranca»*—: el núcleo deja subir el
        `ValueError` y era esta superficie la que se lo tragaba.

        **Y este mismo `except` tapaba TAMBIÉN el reverso — cerrado en N35**
        (`bench/raices-mixtas.md`). Hasta N35, `Confinamiento._preparar`
        lanzaba en cuanto **una** raíz no confinaba, así que un cliente que
        declarase `["C:\\", <un directorio legítimo>]` perdía también el
        legítimo: `sin_acceso = True` sobre una lista blanca utilizable. Las
        dos mitades salían por aquí con la misma excepción y el mismo `except`,
        y por eso la de arriba —que abría de más— tapó a ésta —que cerraba de
        más— durante toda una ronda. Ahora las raíces que no confinan **se
        podan** y el `ValueError` queda para lo que R6 siempre quiso decir:
        *no queda ninguna raíz*. Este `except` no cambia y **no debe cambiar**:
        sigue siendo el que traduce «no hay lista blanca» a `sin_acceso`.
        MEDIDO, misma sonda sobre el código de antes y el de después: 11 filas,
        7 sin cambio y 4 que recuperan acceso, con **cero** accesos indebidos
        ganados; la fila de N7 sale idéntica.
        """
        with self._lock:
            if self._resuelto:
                return
        import anyio

        if self._alock is None:
            # Atómico dentro del bucle: no hay `await` entre el `if` y la
            # asignación. Perezoso porque `construir()` corre fuera del bucle.
            self._alock = anyio.Lock()
        async with self._alock:
            with self._lock:
                # Segunda mirada: otro pudo resolverlo mientras se esperaba.
                if self._resuelto:
                    return
            cliente: list[str] = []
            fallo = False
            try:
                r = await sesion.list_roots()
                for raiz in getattr(r, "roots", []) or []:
                    p = _uri_a_ruta(str(getattr(raiz, "uri", "")))
                    if p:
                        cliente.append(p)
            except Exception:
                # Un cliente sin `roots` no es un error: es el caso de `--raiz`
                # sola. Pero tampoco es una respuesta: se anota, y decide abajo.
                cliente = []
                fallo = True
            efectivas = self._interseca(self.servidor, cliente)
            sin_confinar = False
            try:
                self.fx.confinamiento = (_conf.Confinamiento(efectivas)
                                         if efectivas else None)
            except ValueError:
                self.fx.confinamiento = None
                sin_confinar = True
            # R6: denegar por defecto. Sin ninguna raíz —o con raíces que no
            # confinan nada— no se opera. Es lo ÚNICO que decide esta capa
            # sobre el acceso, y no es un predicado sobre rutas: es «no hay
            # lista blanca». Todo predicado sigue en el núcleo.
            self.sin_acceso = (not efectivas) or sin_confinar
            with self._lock:
                # No se sella NINGÚN resultado nacido de un fallo: volver a
                # preguntar es lo único que puede cambiar la respuesta, y el
                # sellado de un fallo con raíces de servidor ensanchaba el
                # confinamiento para toda la sesión.
                self._resuelto = not fallo


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
# 3. El servidor
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

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

import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field

from . import confinamiento as _conf
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
            finally:
                # **Obligatorio**: los `ident` de hilo se reciclan, y un `ident`
                # reutilizado heredaría la cancelación del trabajo anterior.
                invocacion.olvidar_hilo()

        t.hilo = threading.Thread(target=corre, daemon=True, name=f"filex-{t.id}")
        t.hilo.start()
        return r

    def batch(self, entradas: list[str], directorio_salida: str,
              formato_destino: str, parametros: dict | None = None) -> dict:
        d = formatos.normaliza(formato_destino)
        t = self.trabajos.nuevo("batch")

        def corre():
            try:
                _corre_batch()
            finally:
                invocacion.olvidar_hilo()

        def _corre_batch():
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
                # Trabajo leído del disco: es de otra sesión o de otro proceso,
                # y su `Popen` no vive en este registro. Se dice, no se finge.
                return {"job_id": t.id, "estado": t.estado,
                        "motor_detenido": False,
                        "nota": "el trabajo no corre en este proceso: la "
                                "cancelación queda anotada, el motor no se toca"}
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

"""N34 — la caché de raíces en concurrencia: ¿serializar o aceptar la carrera?

`bench/mcp-cabos-y-techos.md` §2.4 (worker2) mide que **dos herramientas que
entran a la vez con la caché fría producen 2 `roots/list`, no 1**: el
`threading.Lock` de `Raices.asegurar()` se suelta **antes** del `await`. Lo dejó
medido y sin decidir, con el argumento de que *«el cálculo es idempotente y las
dos llamadas dan lo mismo»*.

Esta sonda pregunta lo que decide la fila: **¿pueden dar lo mismo SIEMPRE?**

Celdas, cada una con lo que la refutaría delante (trampa 111):

  N0  Control del arnés: doble sin ceder vs cediendo. **Si las dos celdas dan
      lo mismo, la de abajo no midió concurrencia** (trampa 114, de ayer).
  N1  Escalado: N herramientas a la vez con la caché fría -> ¿N `roots/list`?
  N2  DIVERGENCIA: dos llamadas concurrentes con respuestas DISTINTAS (una
      responde, la otra falla). ¿Decide el orden quién queda con acceso?
  N3  El sellado nacido de un fallo, SIN concurrencia: con `--raiz` puesta,
      un `roots/list` que falla sella la lista blanca ENTERA del servidor.
  N4  Los candidatos, tabulados (trampa 51: tabula qué atrapa y qué rompe).
  N5  Coste: la espera que la serialización impone al segundo llamador, y el
      coste del candado en caliente (trampa 88: cronometra la línea entera).

    .venv-mcp-filex/Scripts/python.exe bench/salidas-roots-concurrencia/sonda_carrera.py [salida.json]
"""
from __future__ import annotations

import json
import os
import shutil
import statistics
import sys
import tempfile
import time

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(os.path.dirname(_AQUI))
sys.path.insert(0, _RAIZ)

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(_AQUI, "carrera.json")
CORPUS = os.path.join(_RAIZ, "corpus", "imagen", "tipico.png")

#: Lo que un `roots/list` real tarda por el cable. No es un adorno: es el
#: tiempo que la serialización le hace esperar al segundo llamador, y se mide
#: aparte, con un par cliente/servidor de verdad (`sonda_par_real.py`).
RETARDO_ROUNDTRIP = 0.05


# --------------------------------------------------------------------------
# Los dobles
# --------------------------------------------------------------------------

class RaizFalsa:
    def __init__(self, uri):
        self.uri = uri


class ResultadoRaices:
    def __init__(self, roots):
        self.roots = roots


class FalloDeRoots(Exception):
    """Lo que hace un cliente que no responde a `roots/list`: un fallo
    TRANSITORIO. Desde el arreglo de M3, FileX ya no lo sella; por eso dos
    llamadas concurrentes pueden discrepar."""


class SesionFalsa:
    """Cuenta cada `roots/list` y permite responder DISTINTO a cada una.

    `ceder` no es un adorno: un `async def` sin un solo `await` dentro no
    devuelve el control al bucle, así que dos corrutinas «a la vez» corren en
    serie y el arnés mediría a su doble (trampa 114). `entradas_simultaneas`
    deja constancia de que el solape ocurrió de verdad.

    `guion` da, por índice de llamada, qué responder y cuánto tardar. Con él se
    construyen las DOS órdenes de terminación de un mismo par de llamadas, que
    es justo lo que decide si la carrera importa.
    """

    def __init__(self, raices, guion=None, ceder=True,
                 retardo=RETARDO_ROUNDTRIP):
        self._raices = list(raices)
        self.guion = list(guion or [])
        self.ceder = ceder
        self.retardo = retardo
        self.llamadas = 0
        self.dentro = 0
        self.entradas_simultaneas = 0
        self.orden_de_terminacion = []

    async def list_roots(self):
        self.llamadas += 1
        i = self.llamadas
        self.dentro += 1
        self.entradas_simultaneas = max(self.entradas_simultaneas, self.dentro)
        try:
            modo, raices, espera = ("ok", self._raices, self.retardo)
            if i <= len(self.guion):
                modo, raices, espera = self.guion[i - 1]
            if self.ceder:
                import anyio
                await anyio.sleep(espera)
            self.orden_de_terminacion.append(i)
            if modo == "fallo":
                raise FalloDeRoots("el cliente no respondió a roots/list")
            return ResultadoRaices(
                [RaizFalsa("file:///" + r.replace(os.sep, "/"))
                 for r in raices])
        finally:
            self.dentro -= 1


def _ctx(sesion):
    from mcp.server.lowlevel.server import ServerRequestContext
    return ServerRequestContext(session=sesion, lifespan_context=None,
                                protocol_version="2025-11-25",
                                method="tools/call")


def _manejador(srv):
    """El manejador REAL que el servidor despacharía para `tools/call`."""
    e = srv._request_handlers["tools/call"]
    return e.handler, e.params_type


def _leer(res):
    try:
        return json.loads(res.content[0].text)
    except Exception as e:                                   # pragma: no cover
        return {"_no_parseable": repr(e), "_repr": repr(res)[:400]}


def _confin(conf):
    """Las raíces de un `Confinamiento`, por su nombre REAL.

    La primera versión de esta sonda leía `conf.raices`, que no existe, así que
    devolvía `[]` para todo confinamiento vivo y `None` para el ausente: dos
    configuraciones que sé distintas daban el mismo valor, que es exactamente
    la trampa 66. Los campos son `lectura` y `escritura` (R9: no son el mismo).
    """
    if conf is None:
        return None
    return {"lectura": sorted(getattr(conf, "lectura", [])),
            "escritura": sorted(getattr(conf, "escritura", []))}


# --------------------------------------------------------------------------
# Los candidatos. Se escriben como SUBCLASES de la clase de producción y se
# inyectan antes de `construir()`, así que el camino que se ejercita sigue
# siendo `on_call_tool -> gestor.asegurar` (trampa 109). El ganador se
# implementa después en `filex/mcp.py` y se vuelve a medir con esta misma
# sonda: una variante en el arnés no es la prueba, es el boceto.
# --------------------------------------------------------------------------

def candidatos(M):
    import anyio

    class B_Serializado(M.Raices):
        """Candidato B: un candado ASÍNCRONO sostenido a través del `await`."""

        def _alock(self):
            a = getattr(self, "_alock_", None)
            if a is None:
                # Crearlo perezosamente es seguro: desde el `if` hasta la
                # asignación no hay punto de suspensión, así que dentro de un
                # bucle de eventos esto es atómico.
                a = self._alock_ = anyio.Lock()
            return a

        async def asegurar(self, sesion) -> None:
            with self._lock:
                if self._resuelto:
                    return
            async with self._alock():
                with self._lock:
                    if self._resuelto:
                        return          # otro lo resolvió mientras esperaba
                await M.Raices.asegurar(self, sesion)

    class C_PrimerSelladorGana(M.Raices):
        """Candidato C: N idas y vueltas, pero el sellado es atómico y sólo
        gana el PRIMERO que sella. Cero espera; el estado no puede divergir."""

        async def asegurar(self, sesion) -> None:
            with self._lock:
                if self._resuelto:
                    return
            cliente, fallo = [], False
            try:
                r = await sesion.list_roots()
                for raiz in getattr(r, "roots", []) or []:
                    p = M._uri_a_ruta(str(getattr(raiz, "uri", "")))
                    if p:
                        cliente.append(p)
            except Exception:
                cliente, fallo = [], True
            efectivas = self._interseca(self.servidor, cliente)
            with self._lock:
                if self._resuelto:
                    return              # ya hay veredicto: no se pisa
                try:
                    self.fx.confinamiento = (M._conf.Confinamiento(efectivas)
                                             if efectivas else None)
                except ValueError:
                    self.fx.confinamiento = None
                self.sin_acceso = not efectivas
                self._resuelto = not (fallo and not efectivas)

    class D_SerializadoSinSellarFallos(B_Serializado):
        """Candidato D: B, y además NINGÚN resultado nacido de un fallo se
        sella — ni siquiera el que sale con raíces (las del servidor)."""

        async def asegurar(self, sesion) -> None:
            with self._lock:
                if self._resuelto:
                    return
            async with self._alock():
                with self._lock:
                    if self._resuelto:
                        return
                cliente, fallo = [], False
                try:
                    r = await sesion.list_roots()
                    for raiz in getattr(r, "roots", []) or []:
                        p = M._uri_a_ruta(str(getattr(raiz, "uri", "")))
                        if p:
                            cliente.append(p)
                except Exception:
                    cliente, fallo = [], True
                efectivas = self._interseca(self.servidor, cliente)
                try:
                    self.fx.confinamiento = (M._conf.Confinamiento(efectivas)
                                             if efectivas else None)
                except ValueError:
                    self.fx.confinamiento = None
                self.sin_acceso = not efectivas
                with self._lock:
                    self._resuelto = not fallo

    return {"A_hoy": M.Raices, "B_serializado": B_Serializado,
            "C_primer_sellador": C_PrimerSelladorGana,
            "D_serializado_sin_sellar_fallos": D_SerializadoSinSellarFallos}


# --------------------------------------------------------------------------

def main() -> int:
    import anyio

    from filex import mcp as M
    from filex.nucleo import FileX
    from filex.servicio import Trabajos

    import importlib.metadata as md
    r: dict = {
        "interprete": sys.version.split()[0],
        "plataforma": sys.platform,
        "mcp_version": md.version("mcp"),
        # Trampa 62: pregúntale al instrumento su resolución antes de cronometrar.
        "resolucion_perf_counter_s":
            time.get_clock_info("perf_counter").resolution,
        "clase_de_produccion_hoy": M.Raices.__name__,
        "retardo_simulado_de_roots_list_s": RETARDO_ROUNDTRIP,
    }

    tmp = tempfile.mkdtemp(prefix="n34-")
    sub = os.path.join(tmp, "sub")
    os.makedirs(sub, exist_ok=True)
    ent = os.path.join(sub, "entrada.png")
    shutil.copy2(CORPUS, ent)
    # Trampa 34/107: se comprueba el TAMAÑO, no la existencia.
    r["entrada_bytes"] = os.path.getsize(ent)
    r["entrada_es_puntero_lfs"] = r["entrada_bytes"] < 1000

    CAND = candidatos(M)

    def nuevo_servidor(clase=None, raices_servidor=None):
        fx = FileX()
        anterior = M.Raices
        if clase is not None:
            M.Raices = clase
        try:
            srv, svc, gestor = M.construir(
                fx, raices_servidor, Trabajos(tempfile.mkdtemp(prefix="n34-t-")))
        finally:
            M.Raices = anterior
        return srv, svc, gestor

    async def llamar(srv, sesion, nombre, args):
        h, TipoParams = _manejador(srv)
        return await h(_ctx(sesion), TipoParams(name=nombre, arguments=args))

    # =====================================================================
    # N0 — el control del arnés (trampa 114)
    # =====================================================================
    async def n0(ceder):
        srv, _, ges = nuevo_servidor()
        ses = SesionFalsa([tmp], ceder=ceder)
        res = {}

        async def uno(k):
            res[k] = _leer(await llamar(srv, ses, "inspect", {"ruta": ent}))

        async with anyio.create_task_group() as tg:
            tg.start_soon(uno, "a")
            tg.start_soon(uno, "b")
        return {"doble_cede_el_bucle": ceder,
                "roots_list_llamadas": ses.llamadas,
                "entradas_simultaneas_en_roots_list": ses.entradas_simultaneas,
                "las_dos_respondieron": sorted(res) == ["a", "b"]}

    r["N0_sin_ceder_CONTROL_NEGATIVO"] = anyio.run(n0, False)
    r["N0_cediendo"] = anyio.run(n0, True)
    r["N0_el_arnes_mide_concurrencia"] = (
        r["N0_cediendo"]["entradas_simultaneas_en_roots_list"] > 1
        and r["N0_sin_ceder_CONTROL_NEGATIVO"]
            ["entradas_simultaneas_en_roots_list"] == 1
        and r["N0_cediendo"]["roots_list_llamadas"]
            != r["N0_sin_ceder_CONTROL_NEGATIVO"]["roots_list_llamadas"])

    # =====================================================================
    # N1 — escalado: ¿una ida y vuelta por herramienta concurrente?
    # =====================================================================
    async def n1(clase, n):
        srv, _, ges = nuevo_servidor(clase)
        ses = SesionFalsa([tmp], ceder=True)
        res = {}

        async def uno(k):
            t0 = time.perf_counter_ns()
            res[k] = (_leer(await llamar(srv, ses, "inspect", {"ruta": ent})),
                      (time.perf_counter_ns() - t0) / 1e6)

        t0 = time.perf_counter_ns()
        async with anyio.create_task_group() as tg:
            for i in range(n):
                tg.start_soon(uno, "t%d" % i)
        pared_ms = (time.perf_counter_ns() - t0) / 1e6
        esperas = sorted(v[1] for v in res.values())
        return {"n_herramientas": n, "roots_list_llamadas": ses.llamadas,
                "entradas_simultaneas": ses.entradas_simultaneas,
                "pared_ms": round(pared_ms, 2),
                "espera_min_ms": round(esperas[0], 2),
                "espera_max_ms": round(esperas[-1], 2),
                "ninguna_es_error": all(not v[0].get("error")
                                        for v in res.values())}

    r["N1_escalado"] = {nombre: [anyio.run(n1, cls, n) for n in (1, 2, 4, 8)]
                        for nombre, cls in CAND.items()}

    # =====================================================================
    # N2 — DIVERGENCIA: las dos concurrentes reciben respuestas DISTINTAS
    # =====================================================================
    # El guion fija cuál de las dos idas y vueltas termina antes, así que las
    # dos órdenes se miden a propósito en vez de dejarlas al azar.
    async def n2(clase, orden, raices_servidor=None):
        srv, _, ges = nuevo_servidor(clase, raices_servidor)
        if orden == "gana_el_fallo":
            guion = [("ok", [sub], 0.12), ("fallo", [], 0.02)]
        else:
            guion = [("fallo", [], 0.12), ("ok", [sub], 0.02)]
        ses = SesionFalsa([sub], guion=guion, ceder=True)
        res = {}

        async def uno(k):
            res[k] = _leer(await llamar(srv, ses, "inspect", {"ruta": ent}))

        async with anyio.create_task_group() as tg:
            tg.start_soon(uno, "a")
            tg.start_soon(uno, "b")
        conf = ges.fx.confinamiento
        return {
            "orden": orden,
            "roots_list_llamadas": ses.llamadas,
            "entradas_simultaneas": ses.entradas_simultaneas,
            "orden_de_terminacion": ses.orden_de_terminacion,
            "respuestas_con_error": sorted(bool(v.get("error"))
                                           for v in res.values()),
            "las_dos_coinciden": (len({bool(v.get("error"))
                                       for v in res.values()}) == 1),
            "final_sin_acceso": bool(getattr(ges, "sin_acceso", None)),
            "final_resuelto": bool(getattr(ges, "_resuelto", None)),
            "final_confinamiento": _confin(conf),
        }

    r["N2_divergencia"] = {}
    for nombre, cls in CAND.items():
        celdas = [anyio.run(n2, cls, o)
                  for o in ("gana_el_fallo", "gana_la_respuesta")]
        r["N2_divergencia"][nombre] = {
            "celdas": celdas,
            # Lo que decide la fila: ¿el estado final depende del orden?
            "el_orden_cambia_el_estado_final": (
                celdas[0]["final_sin_acceso"] != celdas[1]["final_sin_acceso"]
                or celdas[0]["final_confinamiento"]
                != celdas[1]["final_confinamiento"]
                or celdas[0]["final_resuelto"] != celdas[1]["final_resuelto"]),
            "alguna_celda_discrepa_entre_llamadores": any(
                not c["las_dos_coinciden"] for c in celdas),
        }

    # =====================================================================
    # N3 — el sellado nacido de un fallo, SIN concurrencia
    # =====================================================================
    # Con `--raiz` puesta, `_interseca(servidor, [])` devuelve la lista del
    # SERVIDOR entera, así que un `roots/list` que falla no deja «ninguna
    # raíz»: deja TODAS, `sin_acceso = False` y `_resuelto = True`. La esquina
    # que M3 dejó abierta no necesita concurrencia para morder.
    async def n3(clase):
        srv, _, ges = nuevo_servidor(clase, [tmp])   # el servidor confina a tmp
        # El cliente confinaría a `sub`, más estrecho. Pero el 1.er roots/list
        # falla; el 2.º responde bien.
        ses = SesionFalsa([sub], guion=[("fallo", [], 0.0),
                                        ("ok", [sub], 0.0)], ceder=True)
        r1 = _leer(await llamar(srv, ses, "inspect", {"ruta": ent}))
        conf1 = ges.fx.confinamiento
        est1 = {"roots_list_llamadas": ses.llamadas,
                "resuelto": bool(getattr(ges, "_resuelto", None)),
                "sin_acceso": bool(getattr(ges, "sin_acceso", None)),
                "confinamiento": _confin(conf1),
                "error": bool(r1.get("error"))}
        # Segunda llamada: ¿se vuelve a preguntar, o quedó sellado?
        _leer(await llamar(srv, ses, "inspect", {"ruta": ent}))
        conf2 = ges.fx.confinamiento
        est2 = {"roots_list_llamadas": ses.llamadas,
                "confinamiento": _confin(conf2)}
        return {"tras_el_fallo": est1, "tras_el_reintento": est2,
                "raiz_servidor": tmp, "raiz_cliente": sub,
                "sella_un_confinamiento_mas_ancho_que_la_interseccion":
                    est1["resuelto"]
                    and (est1["confinamiento"] or {}).get("lectura") == [
                        M._conf._norm(os.path.abspath(tmp))]}

    r["N3_sellado_por_fallo"] = {nombre: anyio.run(n3, cls)
                                 for nombre, cls in CAND.items()}

    # =====================================================================
    # N5 — coste (N4 es la tabla, y se arma a partir de N1/N2/N3/N5)
    # =====================================================================
    # (a) La caché CALIENTE: es el camino del 99 % de las llamadas, y es donde
    #     un candado de más se pagaría en cada herramienta.
    async def n5_caliente(clase, reps=200):
        srv, _, ges = nuevo_servidor(clase)
        ses = SesionFalsa([tmp], ceder=True, retardo=0.0)
        await ges.asegurar(ses)              # la calienta
        assert ges._resuelto, "la caché no quedó caliente"
        muestras = []
        for _ in range(reps):
            t0 = time.perf_counter_ns()
            await ges.asegurar(ses)
            muestras.append(time.perf_counter_ns() - t0)
        muestras.sort()
        return {"reps": reps,
                "mediana_us": round(statistics.median(muestras) / 1000.0, 3),
                "p10_us": round(muestras[reps // 10] / 1000.0, 3),
                "p90_us": round(muestras[(reps * 9) // 10] / 1000.0, 3),
                "roots_list_llamadas_extra": ses.llamadas - 1}

    r["N5_cache_caliente"] = {nombre: anyio.run(n5_caliente, cls)
                              for nombre, cls in CAND.items()}

    # (b) La espera que la serialización impone al SEGUNDO llamador, en frío.
    #     Se mide con el retardo declarado arriba; el número que importa en
    #     producción es ese retardo, no este arnés.
    r["N5_espera_del_segundo_en_frio"] = {
        nombre: {"n2_espera_max_ms": r["N1_escalado"][nombre][1]["espera_max_ms"],
                 "n8_espera_max_ms": r["N1_escalado"][nombre][3]["espera_max_ms"]}
        for nombre in CAND}

    # (c) El caso que un candado sostenido a través de un `await` puede romper:
    #     un `roots/list` que NO vuelve. Con tope, para no colgar la sonda.
    async def n5_cuelga(clase, tope=1.0):
        srv, _, ges = nuevo_servidor(clase)
        ses = SesionFalsa([tmp], ceder=True, retardo=30.0)
        acabadas = []

        async def uno(k):
            with anyio.move_on_after(tope):
                await llamar(srv, ses, "inspect", {"ruta": ent})
                acabadas.append(k)

        t0 = time.perf_counter_ns()
        async with anyio.create_task_group() as tg:
            tg.start_soon(uno, "a")
            tg.start_soon(uno, "b")
        return {"tope_s": tope, "acabadas": sorted(acabadas),
                "pared_ms": round((time.perf_counter_ns() - t0) / 1e6, 1),
                "roots_list_llamadas": ses.llamadas,
                # Con A/C las dos preguntan a la vez; con B/D la segunda ni
                # llega a preguntar. Ninguna de las dos responde: lo que se
                # mide es si serializar EMPEORA el caso del cliente mudo.
                "ninguna_responde": acabadas == []}

    r["N5_roots_list_que_no_vuelve"] = {nombre: anyio.run(n5_cuelga, cls)
                                        for nombre, cls in CAND.items()}

    # =====================================================================
    # N6 — ¿puede otra corrutina ver un estado A MEDIAS?
    # =====================================================================
    # `asegurar` escribe TRES cosas: `fx.confinamiento`, `sin_acceso` y
    # `_resuelto`. Si entre la primera y la segunda hubiera un punto de
    # suspensión, otra corrutina podría ver «puerta abierta y sin
    # confinamiento», que es el peor par posible. Se comprueba sobre el AST,
    # no leyendo el texto (trampa 42: una prueba de forma se hace sobre el AST).
    import ast
    import inspect as _ins

    def _sin_await_entre_las_dos_escrituras(fn):
        arbol = ast.parse(_ins.cleandoc(
            "if True:\n" + _ins.getsource(fn)).replace("if True:\n", "", 1))
        cuerpo = [n for n in ast.walk(arbol)
                  if isinstance(n, ast.AsyncFunctionDef)][0]
        i_conf = i_acc = None
        for n in ast.walk(cuerpo):
            if isinstance(n, ast.Attribute) and n.attr == "confinamiento":
                i_conf = n.lineno if i_conf is None else min(i_conf, n.lineno)
            if isinstance(n, ast.Attribute) and n.attr == "sin_acceso":
                i_acc = n.lineno if i_acc is None else min(i_acc, n.lineno)
        awaits = [n.lineno for n in ast.walk(cuerpo) if isinstance(n, ast.Await)]
        entre = [l for l in awaits if i_conf is not None and i_acc is not None
                 and i_conf < l < i_acc]
        return {"linea_confinamiento": i_conf, "linea_sin_acceso": i_acc,
                "awaits": awaits, "awaits_entre_las_dos": entre,
                "una_corrutina_no_puede_ver_el_par_a_medias": not entre}

    r["N6_par_atomico_para_corrutinas"] = _sin_await_entre_las_dos_escrituras(
        M.Raices.asegurar)

    # =====================================================================
    # N7 — el `except ValueError` de `asegurar`: puerta abierta SIN confinar
    # =====================================================================
    # `Confinamiento([...])` lanza `ValueError` cuando ninguna raíz confina —
    # R3: *«una raíz que normaliza a la raíz de una unidad no confina nada»*.
    # `asegurar` lo captura y pone `confinamiento = None`; pero `sin_acceso`
    # se calcula sobre `efectivas`, que NO está vacía. Y en el núcleo,
    # `_resolver()` con `confinamiento is None` devuelve la ruta tal cual.
    # La celda que lo refutaría está al lado: el mismo `inspect` con una raíz
    # normal tiene que salir DENEGADO.
    fuera = tempfile.mkdtemp(prefix="n34-fuera-")
    ajeno = os.path.join(fuera, "ajeno.png")
    shutil.copy2(CORPUS, ajeno)
    unidad = os.path.splitdrive(os.path.abspath(sub))[0] + os.sep

    async def n7(raiz_cliente, clase=None):
        srv, _, ges = nuevo_servidor(clase)
        ses = SesionFalsa([raiz_cliente], ceder=True, retardo=0.0)
        res_ajeno = _leer(await llamar(srv, ses, "inspect", {"ruta": ajeno}))
        res_corpus = _leer(await llamar(srv, ses, "inspect", {"ruta": CORPUS}))
        return {
            "raiz_declarada_por_el_cliente": raiz_cliente,
            "sin_acceso": bool(getattr(ges, "sin_acceso", None)),
            "confinamiento": _confin(ges.fx.confinamiento),
            "lee_un_fichero_de_OTRO_directorio": not res_ajeno.get("error"),
            "lee_un_fichero_de_OTRA_UNIDAD": not res_corpus.get("error"),
            "unidad_del_ajeno": os.path.splitdrive(ajeno)[0],
            "unidad_del_corpus": os.path.splitdrive(CORPUS)[0],
        }

    r["N7_raiz_de_unidad"] = {
        "CONTROL_raiz_normal": anyio.run(n7, sub),
        "raiz_de_unidad": anyio.run(n7, unidad),
    }
    r["N7_raiz_de_unidad"]["hay_fuga"] = (
        r["N7_raiz_de_unidad"]["raiz_de_unidad"]["lee_un_fichero_de_OTRO_directorio"]
        and not r["N7_raiz_de_unidad"]["CONTROL_raiz_normal"]
                ["lee_un_fichero_de_OTRO_directorio"])

    shutil.rmtree(fuera, ignore_errors=True)
    shutil.rmtree(tmp, ignore_errors=True)

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(r, fh, ensure_ascii=False, indent=2)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    print("\n-> " + OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

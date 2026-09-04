"""Ítem 6 de C36 — idempotencia real ante `Resolve(ListRoots)` doble.

`hito4-mcp.md` §13 lo deja así: *«El cuerpo está escrito idempotente hasta la
línea de roots, pero **no se ha ejercitado un cliente que lo dispare**: Claude
Code usa hoy la vía clásica»*.

Esta sonda ejercita el **camino de producción**, no una copia: recupera el
manejador que `filex.mcp.construir()` registró en `Server._request_handlers`
bajo `tools/call` y lo invoca. Es la trampa 109 —*una prueba que construye su
sujeto de forma distinta a producción puede pararse en una guarda anterior*—:
aquí el sujeto es el objeto que el servidor usaría.

Cinco celdas, cada una con lo que la refutaría delante (trampa 111):

  M0  ¿Puede FileX sufrir siquiera la doble ejecución? (estructural)
  M1  Doble ejecución completa: efectos observables contados
  M2  La caché: ¿cuántos `roots/list` por sesión?
  M3  El aborto estilo Resolve: ¿qué hace el `except Exception` de `asegurar`?
  M4  Dos herramientas a la vez sobre una caché fría

    .venv-mcp-filex/Scripts/python.exe bench/salidas-mcp-cabos-techos/sonda_idempotencia.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(os.path.dirname(_AQUI))
sys.path.insert(0, _RAIZ)

OUT = os.path.join(_AQUI, "idempotencia.json")
CORPUS = os.path.join(_RAIZ, "corpus", "imagen", "tipico.png")


# --------------------------------------------------------------------------
# Los dobles. Un doble que MIENTE sobre lo que cuenta es peor que ninguno:
# cada uno lleva su contador y se publica el contador, no una conclusión.
# --------------------------------------------------------------------------

class RaizFalsa:
    def __init__(self, uri):
        self.uri = uri


class ResultadoRaices:
    def __init__(self, roots):
        self.roots = roots


class AbortoResolve(Exception):
    """Lo que el transporte >= 2026-07-28 hace en vez de responder: parar el
    cuerpo y pedir al cliente que reintente con `input_responses`."""


class SesionFalsa:
    """Cuenta cada `roots/list`. Con `abortar_en` simula el aborto de Resolve.

    **`ceder` no es un adorno.** Un `async def` sin un solo `await` dentro NO
    devuelve el control al bucle de eventos, así que dos corrutinas «a la vez»
    se ejecutan en realidad **en serie** y M4 mediría el doble, no a FileX
    (trampa 38: *registra si la condición que dices reproducir se dio*). Con
    `ceder=True` hay punto de suspensión donde un `roots/list` real lo tendría,
    y `entradas_simultaneas` deja constancia de que el solape ocurrió.
    """

    def __init__(self, raices, abortar_en=(), ceder=False):
        self._raices = list(raices)
        self.llamadas = 0
        self.abortar_en = set(abortar_en)
        self.ceder = ceder
        self.dentro = 0
        self.entradas_simultaneas = 0

    async def list_roots(self):
        self.llamadas += 1
        self.dentro += 1
        self.entradas_simultaneas = max(self.entradas_simultaneas, self.dentro)
        try:
            if self.ceder:
                import anyio
                await anyio.sleep(0.05)
            if self.llamadas in self.abortar_en:
                raise AbortoResolve("input_required: el cliente debe reintentar")
            return ResultadoRaices(
                [RaizFalsa("file:///" + r.replace(os.sep, "/"))
                 for r in self._raices])
        finally:
            self.dentro -= 1


def _ctx(sesion):
    from mcp.server.lowlevel.server import ServerRequestContext
    return ServerRequestContext(session=sesion, lifespan_context=None,
                                protocol_version="2025-11-25",
                                method="tools/call")


def _manejador(srv):
    """El manejador REAL que el servidor despacharía para `tools/call`.

    `HandlerEntry` trae también el modelo con el que el runner VALIDA los
    parámetros, así que se usa ése en vez de un doble: un arnés que inventa el
    tipo de los parámetros mide su propio doble (trampa 109).
    """
    e = srv._request_handlers["tools/call"]
    return e.handler, e.params_type


def _leer(res):
    """El `CallToolResult` -> el `dict` que FileX metió en su `TextContent`."""
    try:
        return json.loads(res.content[0].text)
    except Exception as e:                                   # pragma: no cover
        return {"_no_parseable": repr(e), "_repr": repr(res)[:400]}


# --------------------------------------------------------------------------

def main() -> int:
    import anyio

    from filex import mcp as M
    from filex.nucleo import FileX
    from filex.servicio import Trabajos

    r: dict = {"interprete": sys.version.split()[0], "plataforma": sys.platform}
    import importlib.metadata as md
    r["mcp_version"] = md.version("mcp")

    # =====================================================================
    # M0 — ¿Puede FileX sufrir la doble ejecución? Estructural, no textual.
    # =====================================================================
    # `hito4-mcp.md` §13 atribuye el «no se ha ejercitado» al CLIENTE. Se
    # comprueba también el servidor: la maquinaria de `Resolve` vive en
    # `mcp.server.mcpserver`, y FileX construye con `mcp.server.lowlevel`.
    import mcp.server.lowlevel.server as _low
    import mcp.server.mcpserver.resolve as _res
    nombres_resolve = {"Resolve", "ListRoots", "Elicit", "Sample"}
    r["M0"] = {
        "modulo_que_usa_filex": M.construir.__module__ and "mcp.server.lowlevel",
        "lowlevel_exporta_maquinaria_resolve": sorted(
            n for n in nombres_resolve if hasattr(_low, n)),
        "mcpserver_resolve_exporta": sorted(
            n for n in nombres_resolve if hasattr(_res, n)),
    }
    r["M0"]["filex_puede_sufrir_doble_ejecucion"] = bool(
        r["M0"]["lowlevel_exporta_maquinaria_resolve"])

    # =====================================================================
    # Preparación común
    # =====================================================================
    tmp = tempfile.mkdtemp(prefix="c36-idem-")
    ent = os.path.join(tmp, "entrada.png")
    shutil.copy2(CORPUS, ent)
    r["entrada_bytes"] = os.path.getsize(ent)   # trampa 34/107: tamaño, no existencia
    r["entrada_es_puntero_lfs"] = r["entrada_bytes"] < 1000

    def nuevo_servidor():
        fx = FileX()
        srv, svc, gestor = M.construir(
            fx, None, Trabajos(tempfile.mkdtemp(prefix="c36-trab-")))
        return srv, svc, gestor

    async def llamar(srv, sesion, nombre, args):
        h, TipoParams = _manejador(srv)
        return await h(_ctx(sesion), TipoParams(name=nombre, arguments=args))

    # =====================================================================
    # M1 + M2 — doble ejecución COMPLETA del cuerpo, y la caché
    # =====================================================================
    async def m1():
        srv, svc, gestor = nuevo_servidor()
        ses = SesionFalsa([tmp])
        sal = os.path.join(tmp, "m1.jpg")
        args = {"entrada": ent, "salida": sal,
                "formato_destino": "jpg"}
        r1 = _leer(await llamar(srv, ses, "convert", args))
        r2 = _leer(await llamar(srv, ses, "convert", args))
        # `Trabajos` es el único registro de efectos que FileX publica.
        try:
            ids = sorted(svc.trabajos._t)          # dict interno
        except Exception:
            ids = []
        return {
            "roots_list_llamadas": ses.llamadas,
            "job_id_1": r1.get("job_id"), "job_id_2": r2.get("job_id"),
            "job_id_distintos": r1.get("job_id") != r2.get("job_id"),
            "n_trabajos_registrados": len(ids),
            "respuesta_1": r1, "respuesta_2": r2,
        }

    r["M1_M2"] = anyio.run(m1)

    # =====================================================================
    # M3 — el aborto estilo Resolve contra el `except Exception` de `asegurar`
    # =====================================================================
    # Si el `except Exception` se traga la señal, FileX no dice «vuelve a
    # preguntar»: dice «este cliente no tiene roots», que es un veredicto
    # distinto y con consecuencia de ACCESO. Es la trampa 43 sobre otro
    # recurso: separar «no se puede» de «no está».
    async def m3():
        srv, svc, gestor = nuevo_servidor()
        ses = SesionFalsa([tmp], abortar_en={1})   # el 1.er roots/list aborta
        res = _leer(await llamar(srv, ses, "inspect", {"ruta": ent}))
        estado_tras_aborto = {
            "roots_list_llamadas": ses.llamadas,
            "sin_acceso": bool(getattr(gestor, "sin_acceso", None)),
            "resuelto_marcado": bool(getattr(gestor, "_resuelto", None)),
            "confinamiento_es_none": gestor.fx.confinamiento is None,
            "respuesta": res,
        }
        # Y el reintento, que es lo que el cliente haría: ¿se recupera?
        res2 = _leer(await llamar(srv, ses, "inspect", {"ruta": ent}))
        estado_tras_aborto["reintento_roots_list_llamadas"] = ses.llamadas
        estado_tras_aborto["reintento_respuesta"] = res2
        estado_tras_aborto["reintento_sin_acceso"] = bool(
            getattr(gestor, "sin_acceso", None))
        return estado_tras_aborto

    r["M3"] = anyio.run(m3)

    # =====================================================================
    # M4 — dos herramientas a la vez sobre una caché fría
    # =====================================================================
    async def m4(ceder):
        srv, svc, gestor = nuevo_servidor()
        ses = SesionFalsa([tmp], ceder=ceder)
        res = {}

        async def uno(k):
            res[k] = _leer(await llamar(srv, ses, "inspect", {"ruta": ent}))

        async with anyio.create_task_group() as tg:
            tg.start_soon(uno, "a")
            tg.start_soon(uno, "b")
        return {"doble_cede_el_bucle": ceder,
                "roots_list_llamadas": ses.llamadas,
                # La celda que dice si la condición se dio de verdad.
                "entradas_simultaneas_en_roots_list": ses.entradas_simultaneas,
                "las_dos_respondieron": sorted(res) == ["a", "b"],
                "ninguna_es_error": all(not v.get("error")
                                        for v in res.values())}

    # Sin ceder es el CONTROL NEGATIVO del arnés: si las dos celdas dan lo
    # mismo, la de arriba no probaba concurrencia.
    r["M4_sin_ceder"] = anyio.run(m4, False)
    r["M4_cediendo"] = anyio.run(m4, True)

    shutil.rmtree(tmp, ignore_errors=True)

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(r, fh, ensure_ascii=False, indent=2)
    print(json.dumps(r, ensure_ascii=False, indent=2)[:5000])
    print("\n-> " + OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

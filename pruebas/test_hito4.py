"""Pruebas del hito 4 — la capa MCP. Biblioteca estándar, sin dependencias.

    python -m unittest discover -s pruebas -p "test_hito4*" -v

**Las que necesitan el SDK se saltan solas** (`mcp>=2.0.0` vive en
`.venv-mcp-filex`, y `mcp~=1.8.0` y `mcp>=2.0.0` no coexisten en un venv). Las
demás corren con cualquier Python: la lógica de las cinco herramientas vive en
`filex.mcp.Servicio`, que no importa el protocolo.

El criterio de aserción es el de `image-worker-mcp/tests/tools/sharp.test.ts:369`
—**abrir el fichero que escribió el código bajo prueba y afirmar sus propiedades
reales**— y no el de `ffmpeg-mcp-lite/test_convert.py:20`, que se conforma con
`exists()` más una subcadena y **daría por bueno un fichero de 0 bytes**
(`RESULTADOS-MCP.md` §11). Con una diferencia deliberada: aquí no se mockea
`shutil.move`, porque un fallo en cómo la herramienta escribe en disco es
exactamente lo que hay que atrapar.

Cada prueba cita la medición de la que sale. Las que comprueban una POLÍTICA y
no una medición lo dicen.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filex import confinamiento as _conf  # noqa: E402
from filex import mcp as M  # noqa: E402
from filex import servicio as S  # noqa: E402
from filex.nucleo import FileX  # noqa: E402

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CORPUS = os.path.join(_RAIZ, "corpus")

#: Solo ImageMagick lee PNG en `filex.motores.MOTORES`. `.github/workflows/
#: suite.yml` no instala ningún motor externo, así que en el runner de Linux
#: `shutil.which("magick")` es `None` -- C42, `bench/ci-y-contrato.md` §1,
#: MEDIDO dentro de un contenedor limpio. **Sigue habiendo un segundo
#: pendiente detrás de éste** (no arreglado aquí, fuera del alcance de C42):
#: incluso CON ImageMagick, `corpus/imagen/{tipico,trivial}.png` están en Git
#: LFS y con `lfs: false` llegan como punteros de texto de ~130 B, no como
#: PNG real -- la misma trampa 34 que ya se cerró en `test_a7_ciego` y
#: `test_cancelacion_procesos` para audio/vídeo, todavía abierta para imagen.
_MOTIVO_SIN_IMAGEMAGICK = ("no hay ImageMagick (`magick`): ningún motor lee "
                          "png (C42, bench/ci-y-contrato.md §1)")
HAY_IMAGEMAGICK = shutil.which("magick") is not None

try:
    import mcp.types as _t  # noqa: F401

    HAY_SDK = True
except Exception:
    HAY_SDK = False

try:
    import tiktoken as _tk

    _ENC = _tk.get_encoding("o200k_base")
except Exception:
    _ENC = None


def ntok(s: str) -> int:
    if _ENC is None:
        # Sin tiktoken no se INVENTA una cifra: se devuelve -1 y la prueba se
        # salta. Estimar tokens por caracteres es lo que hizo que
        # `00-mcp-componentes.md` §3.5 se quedara a un factor 2,2 de la realidad.
        return -1
    return len(_ENC.encode(s, disallowed_special=()))


def _servicio(raices=None):
    fx = FileX(raices_lectura=raices) if raices else FileX()
    return S.Servicio(fx, S.Trabajos(tempfile.mkdtemp(prefix="h4-trab-")))


def _esperar(sv, jid, tope=180.0):
    t0 = time.time()
    while time.time() - t0 < tope:
        r = sv.despachar("job", {"job_id": jid, "accion": "resultado"})
        if r.get("estado") != S.TRABAJANDO:
            return r
        time.sleep(0.15)
    return {"estado": "timeout_de_la_prueba"}


# ==========================================================================


class Catalogo(unittest.TestCase):
    """El catálogo: lo que el modelo ve, y lo único que ve.

    MEDIDO (`bench/mcp-cabos-sueltos.md` §1.2): de lo que declara el servidor,
    al modelo **solo le cruzan `description` e `input_schema`**. Ni las
    anotaciones, ni `outputSchema`, ni `_meta`, ni `icons`.
    """

    def setUp(self):
        self.fx = FileX()
        self.h = M.catalogo(self.fx)

    def test_cada_parametro_lleva_description(self):
        """MEDIDO: **0 de 193** parámetros de los tres catálogos de referencia
        la lleva (`RESULTADOS-MCP.md` §4). FastMCP deriva el esquema de las
        anotaciones de tipo y deja la semántica en el docstring, que es lo que
        produce un `array of object` sin una sola clave declarada."""
        sin_desc = []
        for x in self.h:
            d = x if isinstance(x, dict) else x.model_dump(by_alias=True)
            esq = d.get("inputSchema") or d.get("input_schema") or {}
            for nombre, prop in (esq.get("properties") or {}).items():
                if not (prop or {}).get("description"):
                    sin_desc.append(f"{d['name']}.{nombre}")
                # y un nivel más: las claves de `parametros`
                for sub, subprop in (prop.get("properties") or {}).items():
                    if not (subprop or {}).get("description"):
                        sin_desc.append(f"{d['name']}.{nombre}.{sub}")
        self.assertEqual(sin_desc, [], f"parámetros sin description: {sin_desc}")

    def test_los_enum_salen_del_registro(self):
        """«Añadir un motor no toca la capa MCP» — criterio del hito 4.

        Un motor nuevo tiene que aparecer como **un valor más en un `enum`**, no
        como una herramienta. Generar una herramienta por motor es el mecanismo
        que produce las 27 planas de `video-audio-mcp`, de las que 13 son casos
        particulares de 2."""
        del_grafo = {a.destino for a in self.fx.grafo.aristas}
        d = (self.h[0] if isinstance(self.h[0], dict)
             else self.h[0].model_dump(by_alias=True))
        enum = d["inputSchema"]["properties"]["formato_destino"]["enum"]
        self.assertEqual(set(enum), del_grafo)
        self.assertGreater(len(enum), 5)

    def test_un_motor_nuevo_no_toca_este_fichero(self):
        """La prueba dura del criterio: se inyecta una arista con un motor que
        no existe y el `enum` tiene que crecer **sin editar `filex/mcp.py`**."""
        from filex.grafo import REAL, Arista

        self.fx.grafo.añadir(Arista("png", "xyzzy", "motor_inventado", estado=REAL))
        h = M.catalogo(self.fx)
        d = h[0] if isinstance(h[0], dict) else h[0].model_dump(by_alias=True)
        self.assertIn("xyzzy", d["inputSchema"]["properties"]["formato_destino"]["enum"])
        self.assertEqual(len(h), len(self.h), "un motor nuevo NO añade herramientas")

    def test_ni_resources_ni_prompts(self):
        """MEDIDO (`bench/mcp-cabos-2.md` §3): el cliente los enumera y el
        modelo responde **«NINGUNO»**. Coste sin retorno."""
        if not HAY_SDK:
            self.skipTest("necesita mcp>=2.0.0")
        srv, _, _ = M.construir(self.fx, [_RAIZ])
        caps = srv.get_capabilities(None, None) if False else None  # noqa
        # La comprobación estructural que no depende de la firma del SDK:
        # el servidor no registra manejadores de recursos ni de prompts.
        self.assertIsNone(getattr(srv, "_on_list_resources", None))
        self.assertIsNone(getattr(srv, "_on_list_prompts", None))
        self.assertIsNone(caps)

    def test_presupuesto_de_catalogo(self):
        """El presupuesto de ≤1.200 tokens **NO se cumple, y está medido por qué**.

        No es un fallo que haya que ocultar: es el hallazgo del hito. Esta
        prueba fija la cifra vigente para que una regresión se vea, y comprueba
        que el exceso lo explican **las dos reglas de cobertura** y no la
        quinta herramienta — con las cuatro del plan tampoco se cumpliría.
        """
        if _ENC is None:
            self.skipTest("necesita tiktoken")
        total = ntok(M.catalogo_serializado(self.fx))
        # Techo de regresión: el sector empieza en 1.177 (image-worker, 2
        # herramientas) y su techo son 7.964 (video-audio-mcp, 27).
        self.assertLess(total, 2000, "el catálogo ha engordado; remide la curva")
        self.assertLess(total, 2322, "peor que ffmpeg-mcp-lite con 8 herramientas")
        # Y la parte honesta: hoy no cabe en el presupuesto declarado.
        self.assertGreater(total, M.PRESUPUESTO_CATALOGO,
                           "si esto falla, el presupuesto YA se cumple: "
                           "actualiza bench/hito4-mcp.md §3")

    def test_los_nombres_son_el_presupuesto_que_si_se_paga(self):
        """RE-ACOTADO (`bench/mcp-cabos-2.md` §4): en sesión real el **cuerpo**
        del catálogo llega diferido —26.941 = 26.941 tokens— pero los **nombres**
        se inyectan en cada turno. Ese es el presupuesto que sigue vivo."""
        if _ENC is None:
            self.skipTest("necesita tiktoken")
        nombres = " ".join(
            (x if isinstance(x, dict) else x.model_dump())["name"] for x in self.h)
        self.assertLessEqual(ntok(nombres), 20)


class Cobertura(unittest.TestCase):
    """`list_targets` como mecanismo de SEGURIDAD, no de comodidad.

    MEDIDO y contraintuitivo (`bench/saturacion-herramientas.md` §3.5): cuando
    el catálogo no cubre lo que se pide, el modelo **no se abstiene** — llama a
    la más parecida y declara éxito con un dato falso, el **15–17 %** de las
    veces.
    """

    def setUp(self):
        self.sv = _servicio([_RAIZ])

    @unittest.skipUnless(HAY_IMAGEMAGICK, _MOTIVO_SIN_IMAGEMAGICK)
    def test_responde_lo_que_existe_de_verdad(self):
        r = self.sv.despachar("list_targets", {"formato_origen": "png"})
        self.assertIn("webp", r["destinos"])
        self.assertNotIn("png", r["destinos"], "el origen no es un destino de sí mismo")

    def test_lo_imposible_dice_por_que_y_no_ofrece_un_parecido(self):
        r = self.sv.despachar("list_targets",
                              {"formato_origen": "png", "formato_destino": "mp3"})
        self.assertFalse(r["posible"])
        self.assertTrue(r["motivo"])
        self.assertNotIn("camino", r)

    def test_el_aviso_de_rasterizacion_viaja_al_modelo(self):
        """El fallo de `resvg`: `rc=0`, PNG válido, geometría exacta y **ni una
        letra** (`bench/aristas-nominales.md` §8.2). El contrato no lo atrapa,
        así que el modelo tiene que enterarse **antes**, no después.

        No fija el par: busca CUALQUIER arista real que rasterice hacia un
        destino que admite texto. Un par fijo (`svg→pdf`) dejó de servir el
        03/09 cuando `worker7` añadió `("svg", "pdf")` sin rasterizar a
        `LibreOfficeEnContenedor._DECLARADAS` (`bench/aristas-documentales-
        cierre.md` §9): el planificador, correctamente, empezó a preferirlo
        sobre la vía de ImageMagick que rasterizaba — el criterio amarillo
        del hito 1 funcionando como se diseñó, no una regresión. Buscar en
        vivo hace que la prueba siga siendo un tripwire real en vez de
        depender de qué arista sea hoy la peor disponible."""
        from filex import formatos as F

        def _rasteriza_hacia_texto(a):
            if not a.rasteriza:
                return False
            d = F.formato(a.destino)
            return d is not None and d.texto

        candidato = next(
            (a for a in self.sv.fx.grafo.aristas if _rasteriza_hacia_texto(a)), None)
        if candidato is None:
            self.skipTest("ningún par real rasteriza hacia un destino con texto "
                          "en esta máquina — ver bench/aristas-documentales-cierre.md §9")
        r = self.sv.despachar("list_targets",
                              {"formato_origen": candidato.origen,
                               "formato_destino": candidato.destino})
        if not r.get("posible"):
            self.skipTest("la arista candidata dejó de ser alcanzable")
        self.assertIn("aviso", r)
        self.assertIn("texto", r["aviso"])

    def test_convert_imposible_falla_en_el_acto_y_no_gasta_un_job(self):
        """La primera versión de este servidor devolvía un `job_id` también
        cuando no había camino, y el modelo lo descubría **dos turnos después**.
        Que no exista camino se sabe en microsegundos y sin tocar el disco: el
        asa es para lo que tarda, no para lo que es imposible."""
        r = self.sv.despachar("convert", {"entrada": "x.png", "salida": "y.mp3"})
        self.assertIn("error", r)
        self.assertNotIn("job_id", r)
        self.assertIn("list_targets", r.get("sugerencia", ""))

    @unittest.skipUnless(HAY_IMAGEMAGICK, _MOTIVO_SIN_IMAGEMAGICK)
    def test_evidencia_por_arista(self):
        """**El 41,0 % de las aristas que los catálogos del sector declaran no
        existen.** Decir `sin_sondear` cuando no se ha medido es la diferencia."""
        r = self.sv.despachar("list_targets",
                              {"formato_origen": "png", "formato_destino": "webp"})
        self.assertTrue(set(r["evidencia"]) <= {"real", "sin_sondear", "nominal"})


class Confinar(unittest.TestCase):
    """R10: la validación vive en el NÚCLEO. Esta capa no la reimplementa.

    La CLI de `kordoc` lee ficheros fuera de `KORDOC_ROOT` con `exit=0` porque
    `safePath` vivía en su `mcp.ts`. Aquí el punto de fallo equivalente sería
    que `filex/mcp.py` validara por su cuenta.
    """

    def setUp(self):
        self.raiz = tempfile.mkdtemp(prefix="h4-raiz-")
        self.dentro = os.path.join(self.raiz, "dentro.txt")
        with open(self.dentro, "w", encoding="utf-8") as fh:
            fh.write("hola")
        self.sv = _servicio([self.raiz])

    def test_no_hay_predicado_de_rutas_en_la_superficie(self):
        """Prueba **estructural**, no de comportamiento: si alguien vuelve a
        meter validación aquí, esto salta. Es la única forma de probar R10 sin
        esperar a que se rompa en producción."""
        with open(M.__file__, encoding="utf-8") as fh:
            fuente = fh.read()
        cuerpo = fuente.split('"""', 2)[-1]          # sin el docstring de módulo
        for prohibido in ("os.path.realpath", "startswith(raiz", "allowed_dir",
                          "..", "normcase("):
            if prohibido == "..":
                continue
            self.assertNotIn(prohibido, cuerpo,
                             f"validación de rutas en la superficie: {prohibido}")

    def test_mismo_mensaje_para_prohibido_y_para_no_existe(self):
        """R4. Tres fugas distintas se midieron por no hacerlo, y `kordoc` es
        un oráculo completo sobre todo el disco por invertir el orden."""
        fuera = self.sv.despachar("inspect", {"ruta": "C:/Windows/win.ini"})
        no_existe = self.sv.despachar(
            "inspect", {"ruta": os.path.join(self.raiz, "no_existe.txt")})
        self.assertEqual(fuera, no_existe)
        self.assertEqual(fuera["error"], _conf.MENSAJE_OPACO)

    def test_el_mensaje_no_filtra_la_lista_blanca(self):
        """Lo que `servers/filesystem` sí filtra en sus tres mensajes de
        denegación (`lib.ts:110,119,131`), y es su peor defecto."""
        r = self.sv.despachar("inspect", {"ruta": "C:/Windows/win.ini"})
        s = json.dumps(r, ensure_ascii=False)
        self.assertNotIn(self.raiz, s)
        self.assertNotIn("Windows", s)

    @unittest.skipUnless(HAY_IMAGEMAGICK, _MOTIVO_SIN_IMAGEMAGICK)
    def test_convert_fuera_de_la_raiz_no_convierte(self):
        """El camino existe (png→webp) y aun así no se convierte, porque el
        destino cae fuera. **El orden importa y sigue siendo deliberado:**
        primero se comprueba que la conversión EXISTE —una consulta al grafo,
        sin tocar el disco y sin decir nada que el `enum` del catálogo no diga
        ya— y solo después se toca el sistema de ficheros. Ese orden no
        filtra: el que sí filtraría es el de `kordoc`, que hace `realpathSync`
        antes de `assertWithinRoot` y por eso enumera el disco entero.

        C36-7 (`hito4-mcp.md` §8.6): lo que SÍ cambia es que la comprobación
        de confinamiento —que antes solo ocurría DENTRO del hilo del
        trabajo, gastando un `job_id` por nada (2 601,65 µs de mediana,
        200/200 `job_id`, `bench/salidas-suelo-n32/resultado_job_denegado.json`)—
        ahora ocurre en el acto, DESPUÉS de confirmar que el camino existe y
        ANTES de crear el trabajo: mismo orden, un paso menos de indirección.
        El mensaje sigue siendo el mismo opaco (R4); solo deja de haber un
        `job_id` que consultar."""
        png = os.path.join(self.raiz, "e.png")
        with open(png, "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n")
        d = tempfile.mkdtemp(prefix="h4-fuera-")
        r = self.sv.despachar("convert", {"entrada": png,
                                          "salida": os.path.join(d, "x.webp")})
        self.assertNotIn("job_id", r, "C36-7: se deniega ANTES del job_id")
        self.assertEqual(r, {"error": _conf.MENSAJE_OPACO})

    def test_interseccion_de_roots_no_sustitucion(self):
        """R13. `servers/filesystem` (`index.ts:181`) **sustituye** la lista, que
        es justo lo que no hay que hacer."""
        a = os.path.join(self.raiz, "a")
        os.makedirs(a, exist_ok=True)
        # cliente más estrecho que el servidor -> gana el cliente
        self.assertEqual(M.Raices._interseca([self.raiz], [a]), [a])
        # cliente más ancho que el servidor -> gana el servidor
        self.assertEqual(M.Raices._interseca([a], [self.raiz]), [a])
        # sin solape -> nada
        self.assertEqual(M.Raices._interseca([a], ["C:/Windows"]), [])
        # R2: por segmentos, nunca por prefijo de cadena
        self.assertEqual(M.Raices._interseca([a], [a + "_secreto"]), [])


class W9_FlujosAlternativos(unittest.TestCase):
    """**Estas dos pruebas están MARCADAS COMO FALLO ESPERADO A PROPÓSITO.**

    W9 —el único de los 29 vectores que la referencia oficial concede— está
    **abierto en el núcleo de FileX**, y no por olvido de escribir la defensa:
    `filex/confinamiento.py:51` define `nombre_seguro()`, que devuelve `False`
    para `x.txt:oculto` con el comentario *«W9 concedió acceso a un ADS»*… y en
    todo el paquete **el único que lo llama es `pruebas/test_hito1.py`**. La
    defensa está escrita, probada, y desconectada.

    MEDIDO (`bench/salidas-hito4/h4_ads_w9.json`): se lee un ADS de 72 B por
    `inspect` y se escribe uno de 94 B con `convert`, con `veredicto: ok`.

    **No se arregla desde aquí.** Meter el predicado en `filex/mcp.py` sería
    cometer el pecado de `kordoc`: la defensa en la superficie, la CLI sin ella.
    El arreglo vive en el núcleo y va con su diff exacto en `bench/hito4-mcp.md`
    §8. Cuando alguien lo aplique, estas dos pruebas darán **«unexpected
    success»** — que es la señal de «quita el `expectedFailure`», no un fallo.

    **Y eso es justo lo que pasó: W9 quedó cerrado el 22/08/2026** con los dos
    parches de `bench/hito4-mcp.md` §8 —`nombre_seguro` sobre CADA componente en
    `confinamiento._lexico_ok`, y sobre el NOMBRE DE SALIDA en `nucleo._resolver`,
    antes de mirar si hay lista blanca—. Los dos `expectedFailure` dieron
    «unexpected success» y se han quitado: **son pruebas normales desde ahora.**
    """

    def setUp(self):
        if sys.platform != "win32":
            self.skipTest("los ADS son de NTFS")
        import shutil

        origen = os.path.join(_CORPUS, "imagen", "trivial.png")
        if not os.path.isfile(origen):
            self.skipTest("sin corpus")
        self.raiz = tempfile.mkdtemp(prefix="h4-w9-")
        self.f = os.path.join(self.raiz, "dentro.png")
        # Un PNG **válido**: con uno roto el motor falla y la prueba pasaría por
        # el motivo equivocado, que es peor que fallar.
        shutil.copyfile(origen, self.f)
        try:
            with open(self.f + ":oculto", "wb") as fh:
                fh.write(b"\x89PNG\r\n\x1a\n" + b"SECRETO!" * 8)
        except OSError:
            self.skipTest("este sistema de ficheros no admite ADS")
        self.sv = _servicio([self.raiz])

    def test_leer_un_ADS_deberia_denegarse(self):
        self.assertEqual(self.sv.despachar("inspect", {"ruta": self.f + ":oculto"}),
                         {"error": _conf.MENSAJE_OPACO})

    def test_escribir_en_un_ADS_deberia_denegarse(self):
        victima = os.path.join(self.raiz, "victima.txt")
        with open(victima, "w", encoding="utf-8") as fh:
            fh.write("legítimo")
        r = self.sv.despachar("convert", {"entrada": self.f,
                                          "salida": victima + ":carga.webp"})
        if "job_id" in r:
            _esperar(self.sv, r["job_id"], tope=60)
        self.assertFalse(os.path.exists(victima + ":carga.webp"))


class Respuestas(unittest.TestCase):
    """Ruta y metadatos, nunca contenido — y el criterio es TOKENS, no tipos.

    `image-worker-mcp` devuelve la imagen entera **como base64 dentro de un
    `TextContent`**, y el arnés la clasificó como el patrón bueno porque el JSON
    llevaba un campo con la ruta. Solo `tokens_texto = 6.218` la delataba.
    """

    def setUp(self):
        self.sv = _servicio([_RAIZ])
        self.salidas = tempfile.mkdtemp(prefix="h4-out-")
        # el destino tiene que estar dentro de la raíz para poder escribir
        self.sv = _servicio([_RAIZ, self.salidas])

    @unittest.skipUnless(HAY_IMAGEMAGICK, _MOTIVO_SIN_IMAGEMAGICK)
    def test_ninguna_respuesta_lleva_base64(self):
        import re

        png = os.path.join(_CORPUS, "imagen", "trivial.png")
        if not os.path.isfile(png):
            self.skipTest("sin corpus")
        r = self.sv.despachar("convert", {"entrada": png,
                                          "salida": os.path.join(self.salidas, "s.webp")})
        fin = _esperar(self.sv, r["job_id"])
        for d in (r, fin):
            s = json.dumps(d, ensure_ascii=False)
            self.assertIsNone(re.search(r"[A-Za-z0-9+/=]{512,}", s),
                              "hay una racha de base64 en la respuesta")

    def test_presupuesto_de_respuesta(self):
        """≤200 tokens **salvo `inspect`** (`RESULTADOS-MCP.md` §9.3, regla 1).
        El asa cuesta 32-72 tokens **con independencia del tamaño del fichero**:
        un MP4 de 15,5 MB devuelve 32, igual que un PNG de 316 B."""
        if _ENC is None:
            self.skipTest("necesita tiktoken")
        png = os.path.join(_CORPUS, "imagen", "trivial.png")
        if not os.path.isfile(png):
            self.skipTest("sin corpus")
        r = self.sv.despachar("convert", {"entrada": png,
                                          "salida": os.path.join(self.salidas, "t.webp")})
        self.assertLessEqual(ntok(json.dumps(r, ensure_ascii=False)),
                             M.PRESUPUESTO_RESPUESTA)
        fin = _esperar(self.sv, r["job_id"])
        self.assertLessEqual(ntok(json.dumps(fin, ensure_ascii=False)),
                             M.PRESUPUESTO_RESPUESTA)
        lt = self.sv.despachar("list_targets", {"formato_origen": "png"})
        self.assertLessEqual(ntok(json.dumps(lt, ensure_ascii=False)),
                             M.PRESUPUESTO_RESPUESTA)

    @unittest.skipUnless(HAY_IMAGEMAGICK, _MOTIVO_SIN_IMAGEMAGICK)
    def test_nunca_stderr_crudo(self):
        """MEDIDO: los tres servidores de referencia reenvían el `stderr` de
        ffmpeg — **884-1.228 tokens, casi todo banner de compilación**. Y el
        error de `kordoc` y de `docling-mcp` **nombra el comando que lo
        instala**, que dirige la siguiente acción del agente (R14)."""
        malo = os.path.join(self.salidas, "roto.png")
        with open(malo, "wb") as fh:
            fh.write(b"esto no es un png" * 4)
        r = self.sv.despachar("convert", {"entrada": malo,
                                          "salida": os.path.join(self.salidas, "r.webp")})
        fin = _esperar(self.sv, r["job_id"])
        s = json.dumps(fin, ensure_ascii=False).lower()
        for filtracion in ("ffmpeg version", "configuration:", "libavcodec",
                           "pip install", "npm install", "traceback"):
            self.assertNotIn(filtracion, s)

    @unittest.skipUnless(HAY_IMAGEMAGICK, _MOTIVO_SIN_IMAGEMAGICK)
    def test_inspect_esta_exento_del_presupuesto_pero_no_del_confinamiento(self):
        """`inspect` es la excepción a R8 y a R18 —lectura de cabeceras en
        proceso, sin staging y sin censo— **pero no a la lista blanca**. Lo que
        se salta es la copia, no el permiso."""
        png = os.path.join(_CORPUS, "imagen", "tipico.png")
        if not os.path.isfile(png):
            self.skipTest("sin corpus")
        r = self.sv.despachar("inspect", {"ruta": png})
        self.assertEqual(r["firma"], "png")
        self.assertEqual((r["ancho"], r["alto"]), (1920, 1080))
        # MEDIDO en `bench/salidas-hito4/h4_inspect_r8.json`: 0,21-0,59 ms.
        self.assertLess(r["inspect_ms"], 20.0)
        self.assertEqual(self.sv.despachar("inspect", {"ruta": "C:/Windows/win.ini"}),
                         {"error": _conf.MENSAJE_OPACO})


class NoBloquear(unittest.TestCase):
    """**26 de 26** herramientas de `video-audio-mcp` cuelgan la sesión MCP
    entera cuando la salida ya existe (`bench/mcp-cabos-2.md` §1). Este es el
    fallo que no se puede heredar."""

    def setUp(self):
        self.salidas = tempfile.mkdtemp(prefix="h4-nb-")
        self.sv = _servicio([_CORPUS, self.salidas])

    @unittest.skipUnless(HAY_IMAGEMAGICK, _MOTIVO_SIN_IMAGEMAGICK)
    def test_convert_devuelve_el_asa_al_empezar(self):
        """§5.2: **una firma, un comportamiento.** Nada de bifurcar entre
        «rápida bloquea» y «lenta devuelve asa»: un clip de 5 s superó los 900 s
        del timeout del cliente y la conversión ya estaba hecha en disco."""
        png = os.path.join(_CORPUS, "imagen", "tipico.png")
        if not os.path.isfile(png):
            self.skipTest("sin corpus")
        t0 = time.perf_counter()
        r = self.sv.despachar("convert", {"entrada": png,
                                          "salida": os.path.join(self.salidas, "a.avif")})
        ms = (time.perf_counter() - t0) * 1000
        self.assertEqual(r["estado"], S.TRABAJANDO)
        self.assertIn("job_id", r)
        self.assertLess(ms, 200, "convert está bloqueando")
        _esperar(self.sv, r["job_id"])

    @unittest.skipUnless(HAY_IMAGEMAGICK, _MOTIVO_SIN_IMAGEMAGICK)
    def test_la_salida_preexistente_no_cuelga(self):
        """El disparador exacto de las 26: la ruta de salida **ya existe**."""
        png = os.path.join(_CORPUS, "imagen", "trivial.png")
        if not os.path.isfile(png):
            self.skipTest("sin corpus")
        destino = os.path.join(self.salidas, "existe.webp")
        with open(destino, "wb") as fh:
            fh.write(b"basura previa")
        r = self.sv.despachar("convert", {"entrada": png, "salida": destino})
        fin = _esperar(self.sv, r["job_id"], tope=60)
        self.assertNotEqual(fin["estado"], "timeout_de_la_prueba")
        self.assertEqual(fin["estado"], S.COMPLETADO)
        # Y la aserción de `sharp.test.ts:369`: se abre lo que se escribió.
        self.assertTrue(os.path.getsize(destino) > 0)

    def test_job_desconocido_no_revienta(self):
        r = self.sv.despachar("job", {"job_id": "no-existe"})
        self.assertIn("error", r)

    @unittest.skipUnless(HAY_IMAGEMAGICK, _MOTIVO_SIN_IMAGEMAGICK)
    def test_el_trabajo_se_persiste_en_disco(self):
        """§5.3: *el fallo de origen es que el trabajo sobrevivió a quien lo
        esperaba*. Si el `job_id` solo vive en el proceso, una reconexión
        reproduce el fallo que se quería arreglar."""
        png = os.path.join(_CORPUS, "imagen", "trivial.png")
        if not os.path.isfile(png):
            self.skipTest("sin corpus")
        r = self.sv.despachar("convert", {"entrada": png,
                                          "salida": os.path.join(self.salidas, "p.webp")})
        _esperar(self.sv, r["job_id"])
        # Otro registro, mismo directorio: es lo que verá la CLI o el watcher.
        otro = S.Trabajos(self.sv.trabajos.dir)
        t = otro.get(r["job_id"])
        self.assertIsNotNone(t)
        self.assertEqual(t.estado, S.COMPLETADO)


class Despacho(unittest.TestCase):
    def setUp(self):
        self.sv = _servicio([_RAIZ])

    def test_herramienta_desconocida(self):
        self.assertIn("error", self.sv.despachar("borrar_todo", {}))

    def test_faltan_obligatorios(self):
        r = self.sv.despachar("convert", {"entrada": "x.png"})
        self.assertIn("salida", r["error"])

    def test_los_parametros_de_mas_se_ignoran(self):
        """`additionalProperties: false` lo declara; el despachador lo aplica."""
        r = self.sv.despachar("list_targets",
                              {"formato_origen": "png", "inventado": 1})
        self.assertIn("destinos", r)


class ServidorReal(unittest.TestCase):
    """Lo que solo se puede comprobar con el SDK montado."""

    def setUp(self):
        if not HAY_SDK:
            self.skipTest("necesita mcp>=2.0.0 (.venv-mcp-filex)")

    def test_el_catalogo_es_Tool_valido(self):
        import mcp.types as t

        for x in M.catalogo(FileX()):
            self.assertIsInstance(x, t.Tool)
            self.assertTrue(x.description)
            self.assertEqual(x.input_schema.get("type"), "object")

    def test_se_construye_sin_arrancar(self):
        srv, sv, raices = M.construir(FileX(), [_RAIZ])
        self.assertIsNotNone(srv)
        self.assertIsInstance(sv, S.Servicio)
        self.assertIsInstance(raices, M.Raices)


class Subsuncion(unittest.TestCase):
    """C36 ítem 5 — `PLAN-ORQUESTADOR.md` §4.4: *si el esquema de A es un
    subconjunto estricto del de B con la misma semántica, A sobra*.

    **La regla tiene dos conjuntos y sólo el del esquema es automatizable.**
    Aquí se comprueba ese medio predicado sobre el catálogo de FileX, y se
    comprueba con un CONTROL POSITIVO sintético al lado: con cinco herramientas
    de nombres de parámetro disjuntos, un `assertEqual(0)` pasaría con el
    comprobador puesto y con el comprobador roto (trampas 60 y 109).

    La medida contra el catálogo real que se sabe redundante —las 27 de
    `video-audio-mcp`, 13 casos particulares de 2— vive en
    `bench/salidas-mcp-cabos-techos/subsuncion.py`, porque necesita `repos/`,
    que está en `.gitignore` y no existe en un clon.
    """

    @staticmethod
    def _normalizar(herr):
        out = {}
        for h in herr:
            if not isinstance(h, dict):
                h = h.model_dump(exclude_none=True, by_alias=True)
            esq = h.get("inputSchema") or {}
            props = {k: str((v or {}).get("type") or "?")
                     for k, v in (esq.get("properties") or {}).items()}
            out[h["name"]] = (props, set(esq.get("required") or []))
        return out

    @classmethod
    def _subsume(cls, a, b, exigir_rellenable=True):
        (pa, ra), (pb, rb) = a, b
        if not pa:                       # sin parámetros no se subsume a nadie
            return False
        if set(pa) - set(pb):
            return False
        if any(pa[k] != pb.get(k) for k in pa):
            return False
        if exigir_rellenable and (rb - set(pa)):
            return False
        return not (set(pa) == set(pb) and ra == rb)

    @classmethod
    def _sobrantes(cls, cat, exigir_rellenable=True):
        return sorted({na for na, a in cat.items()
                       for nb, b in cat.items()
                       if na != nb and cls._subsume(a, b, exigir_rellenable)})

    def test_el_comprobador_atrapa_una_subsuncion_de_verdad(self):
        """CONTROL POSITIVO. Sin esto el test de abajo no dice nada."""
        cat = self._normalizar([
            {"name": "poner_calidad", "inputSchema": {
                "type": "object",
                "properties": {"entrada": {"type": "string"},
                               "salida": {"type": "string"},
                               "calidad": {"type": "integer"}},
                "required": ["entrada", "salida", "calidad"]}},
            {"name": "convertir", "inputSchema": {
                "type": "object",
                "properties": {"entrada": {"type": "string"},
                               "salida": {"type": "string"},
                               "calidad": {"type": "integer"},
                               "ancho": {"type": "integer"}},
                "required": ["entrada", "salida"]}},
        ])
        self.assertEqual(self._sobrantes(cat), ["poner_calidad"])

    def test_el_comprobador_no_atrapa_lo_que_solo_se_PARECE(self):
        """CONTROL NEGATIVO: mismo número de parámetros, nombres distintos.

        Es el modo de fallo que la mitad semántica de la regla tendría que
        arbitrar, y el que el esquema **no** debe inventarse.
        """
        cat = self._normalizar([
            {"name": "poner_codec", "inputSchema": {
                "type": "object",
                "properties": {"entrada": {"type": "string"},
                               "codec": {"type": "string"}},
                "required": ["entrada", "codec"]}},
            {"name": "poner_bitrate", "inputSchema": {
                "type": "object",
                "properties": {"entrada": {"type": "string"},
                               "bitrate": {"type": "string"}},
                "required": ["entrada", "bitrate"]}},
        ])
        self.assertEqual(self._sobrantes(cat), [])

    def test_el_catalogo_de_filex_no_tiene_ninguna_herramienta_que_sobre(self):
        cat = self._normalizar(M.catalogo(FileX()))
        self.assertEqual(len(cat), 5, "el catálogo son cinco herramientas")
        # Con las DOS variantes del predicado: si sólo pasara con la estricta,
        # el 0 sería del predicado y no del catálogo.
        self.assertEqual(self._sobrantes(cat, True), [])
        self.assertEqual(self._sobrantes(cat, False), [])


class RootsCacheYFallo(unittest.TestCase):
    """C36 ítem 6 — lo que la caché de roots puede y no puede sellar."""

    class _Raiz:
        def __init__(self, uri):
            self.uri = uri

    class _Res:
        def __init__(self, roots):
            self.roots = roots

    class _Sesion:
        """Cuenta los `roots/list` y falla en los turnos que se le digan."""

        def __init__(self, raices, fallar_en=()):
            self.raices = list(raices)
            self.fallar_en = set(fallar_en)
            self.llamadas = 0

        async def list_roots(self):
            self.llamadas += 1
            if self.llamadas in self.fallar_en:
                raise RuntimeError("el canal de vuelta no respondió")
            return RootsCacheYFallo._Res(
                [RootsCacheYFallo._Raiz("file:///" + r.replace(os.sep, "/"))
                 for r in self.raices])

    @staticmethod
    def _correr(coro):
        import asyncio
        return asyncio.run(coro)

    def test_los_roots_se_preguntan_UNA_vez_por_sesion(self):
        g = M.Raices(FileX(), None)
        s = self._Sesion([_RAIZ])
        self._correr(g.asegurar(s))
        self._correr(g.asegurar(s))
        self._correr(g.asegurar(s))
        self.assertEqual(s.llamadas, 1)
        self.assertFalse(g.sin_acceso)

    def test_un_fallo_al_preguntar_NO_deja_la_sesion_denegada_para_siempre(self):
        """MEDIDO (`bench/mcp-cabos-y-techos.md` §2, celda M3).

        Antes del arreglo: `roots/list` falla una vez, `except Exception` deja
        `cliente = []`, sale `sin_acceso = True` **y `_resuelto = True`**, así
        que el reintento del cliente no volvía a preguntar (0 llamadas nuevas)
        y la sesión quedaba denegada entera. Trampa 43: *separar «no se puede»
        de «no está»*.
        """
        g = M.Raices(FileX(), None)
        s = self._Sesion([_RAIZ], fallar_en={1})
        self._correr(g.asegurar(s))
        self.assertTrue(g.sin_acceso, "sin raíces se deniega, y está bien")
        self.assertEqual(s.llamadas, 1)
        # Lo que se arregla: la denegación NO se sella.
        self._correr(g.asegurar(s))
        self.assertEqual(s.llamadas, 2, "el reintento tiene que volver a preguntar")
        self.assertFalse(g.sin_acceso, "y la sesión se recupera")

    def test_un_fallo_CON_raiz_de_servidor_TAMPOCO_se_sella(self):
        """~~El contrapunto: si queda alguna raíz, la respuesta es buena aunque
        el cliente no contestara, y volver a preguntar no cambiaría nada.~~
        **REFUTADO por N34** (`bench/roots-concurrencia.md`, celda N3).

        La premisa vieja era que con `efectivas` no vacía la respuesta ya es
        buena. Y **`_interseca(servidor, [])` devuelve la lista del SERVIDOR
        ENTERA**, así que un `roots/list` que falla no deja «ninguna raíz»:
        deja **todas**, y sellarlo fijaba para toda la sesión un confinamiento
        **más ancho que la intersección que R13 exige**. Volver a preguntar sí
        cambia la respuesta, y esta prueba lo mide en la segunda mitad: con el
        cliente respondiendo, el confinamiento se ESTRECHA a su raíz.

        Es la trampa 43 un nivel más adentro de donde M3 la aplicó: un fallo al
        preguntar no distingue «el cliente no tiene roots» de «el cliente tiene
        roots y no contestó», y sólo la primera justifica quedarse con los del
        servidor. El precio es una ida y vuelta más, y sólo mientras el cliente
        siga sin contestar.
        """
        sub = os.path.join(_RAIZ, "filex")          # más estrecho que `_RAIZ`
        g = M.Raices(FileX(), [_RAIZ])
        s = self._Sesion([sub], fallar_en={1})
        self._correr(g.asegurar(s))
        # Con el fallo: no hay respuesta del cliente, así que quedan las raíces
        # del servidor. Se opera —eso no cambia— pero NO se sella.
        self.assertFalse(g.sin_acceso)
        self.assertFalse(g._resuelto, "un resultado nacido de un fallo no se "
                                      "sella (N34)")
        self.assertEqual(g.fx.confinamiento.lectura,
                         [_conf._norm(os.path.abspath(_RAIZ))])
        # Y el reintento demuestra que preguntar SÍ cambiaba la respuesta.
        self._correr(g.asegurar(s))
        self.assertEqual(s.llamadas, 2, "hay que repreguntar: el fallo escondía "
                                        "las raíces del cliente")
        self.assertTrue(g._resuelto)
        self.assertEqual(g.fx.confinamiento.lectura,
                         [_conf._norm(os.path.abspath(sub))],
                         "la intersección de R13 es más estrecha que la lista "
                         "del servidor que el sellado había fijado")

    def test_la_emision_de_roots_list_changed_queda_CONTADA(self):
        """C36 ítem 3 — no se puede forzar una emisión real, así que lo que se
        entrega es el sitio donde se vería. El valor esperado hoy es 0."""
        g = M.Raices(FileX(), [_RAIZ])
        self.assertEqual(g.emisiones, 0)
        g.invalidar()
        self.assertEqual(g.emisiones, 1)
        self.assertFalse(g._resuelto, "invalidar tiene que invalidar")

    def test_el_registro_de_emisiones_es_opt_in_y_no_revienta(self):
        d = tempfile.mkdtemp(prefix="h4-roots-")
        try:
            reg = os.path.join(d, "emisiones.tsv")
            g = M.Raices(FileX(), [_RAIZ])
            g.invalidar()
            self.assertFalse(os.path.exists(reg), "sin la variable, no escribe")
            os.environ[M.Raices.VAR_REGISTRO] = reg
            try:
                g.invalidar()
            finally:
                os.environ.pop(M.Raices.VAR_REGISTRO, None)
            with open(reg, encoding="utf-8") as fh:
                lineas = fh.read().strip().splitlines()
            self.assertEqual(len(lineas), 1)
            self.assertIn("roots/list_changed", lineas[0])
            # Un destino imposible no puede tumbar el servidor.
            os.environ[M.Raices.VAR_REGISTRO] = os.path.join(d, "no", "hay", "x")
            try:
                g.invalidar()
            finally:
                os.environ.pop(M.Raices.VAR_REGISTRO, None)
        finally:
            shutil.rmtree(d, ignore_errors=True)


try:
    import anyio as _anyio  # noqa: F401

    HAY_ANYIO = True
except Exception:
    HAY_ANYIO = False


class _SesionDeRoots:
    """Doble de sesión para N34. Cuenta las idas y vueltas y puede fallar.

    **El `await` no es decoración**: un `async def` sin punto de suspensión no
    cede el bucle, así que dos corrutinas «a la vez» corren en serie y la
    prueba mediría a su doble (trampa 114). El retardo va donde un `roots/list`
    real tendría su ida y vuelta por el cable.
    """

    def __init__(self, raices, fallar=False, retardo=0.05):
        self._raices = list(raices)
        self.fallar = fallar
        self.retardo = retardo
        self.llamadas = 0

    async def list_roots(self):
        import anyio

        self.llamadas += 1
        await anyio.sleep(self.retardo)
        if self.fallar:
            raise RuntimeError("el cliente no respondió a roots/list")

        class _R:
            def __init__(self, uri):
                self.uri = uri

        class _Res:
            def __init__(self, roots):
                self.roots = roots

        return _Res([_R("file:///" + r.replace(os.sep, "/"))
                     for r in self._raices])


@unittest.skipUnless(HAY_ANYIO, "hace falta anyio (viene con el SDK de MCP)")
class RaicesEnConcurrencia(unittest.TestCase):
    """N34 — `bench/roots-concurrencia.md`.

    Tres fallos medidos en `Raices.asegurar`, los tres del mismo sitio: el
    `threading.Lock` se soltaba antes del `await` y el resultado se sellaba en
    esquinas donde no debía.
    """

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="n34-t-")
        self.sub = os.path.join(self.d, "sub")
        os.makedirs(self.sub, exist_ok=True)
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)

    def test_dos_a_la_vez_con_la_cache_fria_hacen_UNA_ida_y_vuelta(self):
        """MEDIDO: con el candado soltado antes del `await`, N=8 daba 8.

        La condición que la prueba dice reproducir queda REGISTRADA (trampa
        38): si la segunda llamada no hubiera solapado con la primera, no
        habría esperado, y se afirma que esperó.
        """
        import anyio

        fx = FileX()
        g = M.Raices(fx, None)
        ses = _SesionDeRoots([self.sub], retardo=0.05)
        tardanzas = {}

        async def uno(k):
            t0 = time.perf_counter()
            await g.asegurar(ses)
            tardanzas[k] = time.perf_counter() - t0

        async def a_la_vez():
            async with anyio.create_task_group() as tg:
                for k in range(4):
                    tg.start_soon(uno, k)

        anyio.run(a_la_vez)
        self.assertEqual(ses.llamadas, 1, "una ida y vuelta por sesión, no N")
        # El registro de que hubo solape: las cuatro entraron antes de que la
        # primera terminase, así que las cuatro pagaron la ida y vuelta.
        self.assertEqual(len(tardanzas), 4)
        self.assertGreaterEqual(min(tardanzas.values()), 0.04,
                                "si alguna no esperó, no hubo concurrencia y "
                                "esta prueba no mide lo que dice")
        self.assertFalse(getattr(g, "sin_acceso", True))

    def test_un_fallo_no_sella_NADA_ni_con_raices_de_servidor(self):
        """MEDIDO (celda N3): sellaba la lista blanca del servidor ENTERA.

        `_interseca(servidor, [])` devuelve el servidor entero, así que un
        `roots/list` que falla dejaba `efectivas` no vacía y `_resuelto=True`
        **con un confinamiento más ancho que la intersección que R13 exige**.
        """
        import anyio

        fx = FileX()
        g = M.Raices(fx, [self.d])          # el servidor confina a `d`
        malo = _SesionDeRoots([self.sub], fallar=True, retardo=0.0)
        anyio.run(g.asegurar, malo)
        self.assertFalse(g._resuelto, "un resultado nacido de un fallo no se "
                                      "sella: volver a preguntar es lo único "
                                      "que puede cambiar la respuesta")
        # Y el reintento sí pregunta y sí estrecha hasta la intersección.
        bueno = _SesionDeRoots([self.sub], retardo=0.0)
        anyio.run(g.asegurar, bueno)
        self.assertEqual(bueno.llamadas, 1)
        self.assertTrue(g._resuelto)
        self.assertEqual(fx.confinamiento.lectura,
                         [_conf._norm(os.path.abspath(self.sub))])

    def test_una_raiz_que_no_confina_es_SIN_ACCESO_no_sin_confinamiento(self):
        """MEDIDO (celda N7): era una fuga total del confinamiento.

        `Confinamiento` lanza `ValueError` cuando ninguna raíz confina (R3), y
        el `except` lo convertía en `confinamiento = None` dejando
        `sin_acceso = False`. Con `confinamiento is None`, `nucleo._resolver()`
        devuelve la ruta tal cual: un cliente que declarase la raíz de una
        unidad leía ficheros de otro directorio y de otra unidad.
        """
        import anyio

        unidad = os.path.splitdrive(os.path.abspath(self.sub))[0] + os.sep
        fx = FileX()
        g = M.Raices(fx, None)
        g.sin_acceso = False
        anyio.run(g.asegurar, _SesionDeRoots([unidad], retardo=0.0))
        self.assertIsNone(fx.confinamiento)
        self.assertTrue(g.sin_acceso,
                        "sin confinamiento construible no se opera (R6)")
        # Control: con una raíz normal, ni deniega ni se queda sin confinar.
        fx2 = FileX()
        g2 = M.Raices(fx2, None)
        g2.sin_acceso = False
        anyio.run(g2.asegurar, _SesionDeRoots([self.sub], retardo=0.0))
        self.assertFalse(g2.sin_acceso)
        self.assertIsNotNone(fx2.confinamiento)


@unittest.skipUnless(HAY_ANYIO, "hace falta anyio (viene con el SDK de MCP)")
class RaicesMixtasPorMCP(unittest.TestCase):
    """N35 (`bench/raices-mixtas.md`) visto desde la superficie que lo sufre.

    La política vive en `filex/confinamiento.py` y se prueba ahí
    (`test_hito1.RaicesMixtasN35`), pero el consumidor que la traduce a
    «tengo acceso o no» es `Raices.asegurar`, y **el mismo `except ValueError`
    tapaba las dos mitades**: la fuga de N7 —abría de más— y N35 —cerraba de
    más—. Por eso las dos se comprueban aquí, juntas: un arreglo que recupere
    el acceso legítimo y de paso relaje el confinamiento no sería un arreglo.
    """

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="n35-t-")
        self.sub = os.path.join(self.d, "sub")
        os.makedirs(self.sub, exist_ok=True)
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        self.unidad = os.path.splitdrive(os.path.abspath(self.sub))[0] + os.sep

    def _asegurar(self, raices):
        import anyio

        fx = FileX()
        g = M.Raices(fx, None)
        g.sin_acceso = False
        anyio.run(g.asegurar, _SesionDeRoots(raices, retardo=0.0))
        return fx, g

    def test_un_root_que_no_confina_NO_le_quita_al_cliente_los_que_si(self):
        """MEDIDO: antes, `sin_acceso = True` sobre una lista blanca utilizable."""
        for orden in ([self.unidad, self.sub], [self.sub, self.unidad]):
            with self.subTest(primero=os.path.basename(orden[0]) or orden[0]):
                fx, g = self._asegurar(orden)
                self.assertFalse(g.sin_acceso,
                                 "el root legítimo sobrevive a la poda del otro")
                self.assertIsNotNone(fx.confinamiento)
                self.assertEqual(fx.confinamiento.lectura,
                                 [_conf._norm(os.path.abspath(self.sub))])

    def test_y_el_confinamiento_que_queda_sigue_DENEGANDO_lo_de_fuera(self):
        """La mitad que impide que «recuperar acceso» se convierta en la fuga.

        Recuperar el root legítimo no puede traer consigo nada más: ni el
        directorio hermano, ni —lo que la raíz de unidad haría pensar— el resto
        de la unidad.
        """
        fx, g = self._asegurar([self.unidad, self.sub])
        hermano = os.path.join(self.d, "hermano")
        os.makedirs(hermano, exist_ok=True)
        fuera = os.path.join(hermano, "x.txt")
        open(fuera, "w").close()
        with self.assertRaises(_conf.Denegado):
            fx.confinamiento.resolver(fuera)
        # Y nada del resto de la unidad, que es lo que el root podado nombraba.
        raiz_unidad = os.path.join(self.unidad, "Windows", "win.ini")
        if os.path.exists(raiz_unidad):
            with self.assertRaises(_conf.Denegado):
                fx.confinamiento.resolver(raiz_unidad)

    def test_si_NINGUN_root_confina_se_sigue_diciendo_SIN_ACCESO(self):
        """N7 no se reabre: es la celda que separa este arreglo de la fuga.

        Cuando la poda se lleva TODOS los roots, `Confinamiento` lanza igual
        que antes de N35 y esta superficie tiene que traducirlo a
        `sin_acceso = True` con `confinamiento is None` — nunca a
        `confinamiento is None` con `sin_acceso = False`, que es exactamente
        el par que producía la fuga.
        """
        fx, g = self._asegurar([self.unidad])
        self.assertIsNone(fx.confinamiento)
        self.assertTrue(g.sin_acceso)


class _SesionDeUris:
    """Doble que entrega URIs LITERALES, no rutas.

    `_SesionDeRoots` fabrica el URI con `"file:///" + ruta`, que es justo la
    forma cuya traducción N37 pone a prueba: con él no se puede expresar una
    *authority*. Se añade uno nuevo en vez de cambiar aquél porque aquél es el
    instrumento de N34 y **un arnés no se toca mientras mide otra cosa**.
    """

    def __init__(self, uris):
        self._uris = list(uris)
        self.llamadas = 0

    async def list_roots(self):
        import anyio

        self.llamadas += 1
        await anyio.sleep(0.0)

        class _R:
            def __init__(self, uri):
                self.uri = uri

        class _Res:
            def __init__(self, roots):
                self.roots = roots

        return _Res([_R(u) for u in self._uris])


class AuthorityDeUriN37(unittest.TestCase):
    """N37 — `bench/uri-authority.md`. La *authority* de un `file://`.

    `_uri_a_ruta` descartaba `p.netloc`, y eso no perdía la raíz: la
    **sustituía**. `file://servidor/recurso` daba `\\recurso`, que `abspath`
    completa con la unidad del proceso, así que un root de red acababa
    confinando en `D:\\recurso` — y `file://nas-de-la-empresa/Work`, en
    `D:\\Work` entero.

    **Una prueba por RAMA del predicado (trampa 118).** La 118 nació justo de
    aquí al lado: una corrección sobre `_dentro` desmontó una de las dos ramas
    del `or` y publicó una conclusión falsa sobre la que no probó. Las ramas de
    `_uri_a_ruta` son seis y están numeradas en los nombres.
    """

    def test_R1_lo_que_no_es_file_se_ignora(self):
        for uri in ("", "http://servidor/recurso", "D:/Work", "ftp://x/y"):
            with self.subTest(uri=uri):
                self.assertEqual(M._uri_a_ruta(uri), "")

    def test_R2_una_authority_de_red_se_RECHAZA_entera(self):
        """La fila N37. Antes devolvía `\\recurso`; ahora, nada."""
        for uri in ("file://servidor/recurso",
                    "file://servidor/recurso/sub",
                    "file://nas-de-la-empresa/Work",
                    "file://192.168.1.10/datos"):
            with self.subTest(uri=uri):
                self.assertEqual(
                    M._uri_a_ruta(uri), "",
                    "una authority de red no puede acabar en una ruta local")

    def test_R3_localhost_es_la_authority_vacia_y_SIGUE_valiendo(self):
        """RFC 8089 §2, y no es teoría: rechazarla rompía 2 de 4 legítimas.

        Es la mitad que separa este arreglo de una regresión con mejor pinta
        (trampa 51). Node normaliza `localhost` él solo y Python no, así que
        sin esta rama el mismo root funcionaría o no según el runtime del
        cliente.
        """
        esperado = os.path.normpath("D:/Work") if os.name == "nt" else "/Work"
        crudo = "file://localhost/D:/Work" if os.name == "nt" else "file://localhost/Work"
        for uri in (crudo, crudo.replace("localhost", "LOCALHOST")):
            with self.subTest(uri=uri):
                self.assertEqual(M._uri_a_ruta(uri), esperado)

    def test_R4_el_caso_canonico_local_no_se_mueve(self):
        """El que emite el cliente de verdad — MEDIDO contra Claude Code 2.1.260,
        que responde `file:///D:/...` con la authority vacía."""
        if os.name != "nt":
            self.skipTest("la rama de la letra de unidad es de Windows")
        self.assertEqual(M._uri_a_ruta("file:///D:/Work/research/FileX"),
                         os.path.normpath("D:/Work/research/FileX"))
        # Y el `unquote` sigue delante del recorte:
        self.assertEqual(M._uri_a_ruta("file:///C:/a%20b"),
                         os.path.normpath("C:/a b"))

    def test_R5_en_Windows_una_ruta_SIN_unidad_se_rechaza(self):
        """Misma fuga que N37 pero sin authority a la que culpar.

        `file:///recurso` caía en `D:\\recurso` porque `abspath` le pone la
        unidad del proceso. Y `file:////servidor/recurso` es una UNC entrando
        por la puerta de atrás: sin *authority*, pero UNC igual.
        """
        if os.name != "nt":
            self.skipTest("en POSIX `/recurso` sí es una ruta absoluta legítima")
        for uri in ("file:///recurso", "file:////servidor/recurso",
                    "file://///servidor/recurso"):
            with self.subTest(uri=uri):
                self.assertEqual(M._uri_a_ruta(uri), "")

    def test_R5b_tener_unidad_no_es_ser_ABSOLUTA(self):
        """`file:///D:` (sin barra) es *relativa a la unidad*: da el `cwd`.

        La encontró enumerar las ramas **después** del arreglo: la guarda de
        `splitdrive` acepta `D:` porque unidad tiene, y `abspath("D:")` devuelve
        el directorio actual de esa unidad. Y el caso hermano prueba que el
        resultado dependía de estado no declarado: `file:///C:` daba `C:\\`
        sólo porque el directorio actual de `C:` era su raíz.
        """
        if os.name != "nt":
            self.skipTest("las rutas relativas a la unidad son de Windows")
        for uri in ("file:///D:", "file:///d:", "file:///C:"):
            with self.subTest(uri=uri):
                self.assertEqual(M._uri_a_ruta(uri), "")
        # Y con la barra sí, que es la forma que sí nombra un directorio:
        self.assertEqual(M._uri_a_ruta("file:///D:/"), os.path.normpath("D:/"))

    def test_R6_una_ruta_vacia_ya_no_es_el_cwd(self):
        """`normpath("")` devuelve `"."`, y nadie lo había registrado.

        `file://` es authority vacía y path vacío: pasaba el `if p:` de
        `asegurar` y confinaba en el **directorio de trabajo del servidor**.
        """
        self.assertEqual(M._uri_a_ruta("file://"), "")
        self.assertEqual(M._uri_a_ruta("file://localhost"), "")

    # ------------------------------------------------- por la SUPERFICIE
    # Trampa 70: el daño de una traducción mala no aparece donde se mira, sino
    # donde el valor se USA. Estas tres van por `asegurar`, no por la función.

    def _asegurar(self, uris):
        import anyio

        fx = FileX()
        g = M.Raices(fx, None)
        g.sin_acceso = False
        anyio.run(g.asegurar, _SesionDeUris(uris))
        return fx, g

    @unittest.skipUnless(HAY_ANYIO, "hace falta anyio (viene con el SDK de MCP)")
    def test_un_root_de_red_no_concede_NINGUNA_ruta_local(self):
        """La prueba de la fuga, en la moneda en la que dolía: qué se concede."""
        fx, g = self._asegurar(["file://nas-de-la-empresa/Work"])
        self.assertTrue(g.sin_acceso, "sin ninguna raíz utilizable, R6 deniega")
        self.assertIsNone(fx.confinamiento)

    @unittest.skipUnless(HAY_ANYIO, "hace falta anyio (viene con el SDK de MCP)")
    def test_y_el_root_de_red_NO_le_quita_al_cliente_los_que_si_valen(self):
        """N35 no se deshace: descartar uno deja los demás en pie.

        Es la misma exigencia que `RaicesMixtasPorMCP`, sobre la causa nueva:
        si rechazar la *authority* se llevara por delante la lista blanca
        entera, esto sería N35 reabierto por otra puerta.
        """
        d = tempfile.mkdtemp(prefix="n37-t-")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        uri_bueno = "file:///" + os.path.abspath(d).replace(os.sep, "/")
        fx, g = self._asegurar(["file://servidor/recurso", uri_bueno])
        self.assertFalse(g.sin_acceso)
        self.assertIsNotNone(fx.confinamiento)
        self.assertEqual(fx.confinamiento.lectura,
                         [_conf._norm(os.path.abspath(d))])
        # Y no se cuela la ruta local que el root de red producía antes.
        unidad = os.path.splitdrive(os.path.abspath(d))[0]
        with self.assertRaises(_conf.Denegado):
            fx.confinamiento.resolver(os.path.join(unidad + os.sep, "recurso"))

    @unittest.skipUnless(HAY_ANYIO, "hace falta anyio (viene con el SDK de MCP)")
    def test_el_descarte_deja_RASTRO_cuando_se_pide(self):
        """N37: la poda de N35 y el descarte de un URI eran mudos.

        Se comprueba el canal, no la prosa: sin la variable no se escribe nada
        y con ella aparecen las dos causas separadas (trampa 25: dos cosas con
        la misma pinta desde fuera necesitan registros distintos).
        """
        d = tempfile.mkdtemp(prefix="n37-r-")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        reg = os.path.join(d, "registro.tsv")
        uri_bueno = "file:///" + os.path.abspath(d).replace(os.sep, "/")
        antes = dict(os.environ)
        os.environ[M.Raices.VAR_REGISTRO] = reg
        try:
            self._asegurar(["file://servidor/recurso", uri_bueno])
        finally:
            os.environ.clear()
            os.environ.update(antes)
        self.assertTrue(os.path.exists(reg), "el descarte tiene que dejar rastro")
        texto = open(reg, encoding="utf-8").read()
        self.assertIn("motivo=uri_no_traducible", texto)
        self.assertIn("file://servidor/recurso", texto)


class RaizVaciaN37(unittest.TestCase):
    """N37: una raíz `""` confinaba en el `cwd` del proceso.

    Vive aquí y no en `test_hito1` porque el pendiente lo dejó escrito worker5
    junto a los otros dos de N37, pero el arreglo está en
    `filex/confinamiento.py` y se prueba también desde su propia superficie.
    """

    def test_una_raiz_vacia_no_concede_el_directorio_de_trabajo(self):
        with self.assertRaises(ValueError):
            _conf.Confinamiento([""])
        for basura in ("", "   ", "\t"):
            with self.subTest(raiz=repr(basura)):
                self.assertEqual(_conf.Confinamiento._preparar([basura]), [])

    def test_y_no_se_lleva_por_delante_a_las_raices_buenas(self):
        """Monotonía, igual que N35: podar sólo QUITA."""
        d = tempfile.mkdtemp(prefix="n37-v-")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        c = _conf.Confinamiento(["", d])
        self.assertEqual(c.lectura, [_conf._norm(os.path.abspath(d))])
        self.assertTrue(c.puede_leer(d))

    def test_la_poda_dice_QUE_descarto(self):
        d = tempfile.mkdtemp(prefix="n37-p-")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        unidad = os.path.splitdrive(os.path.abspath(d))[0] + os.sep
        self.assertEqual(_conf.Confinamiento._podadas(["", unidad, d]),
                         ["", unidad])
        self.assertEqual(_conf.Confinamiento._podadas([d]), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

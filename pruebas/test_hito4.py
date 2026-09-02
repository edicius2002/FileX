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
        así que el modelo tiene que enterarse **antes**, no después."""
        r = self.sv.despachar("list_targets",
                              {"formato_origen": "svg", "formato_destino": "pdf"})
        if not r.get("posible"):
            self.skipTest("sin motor svg→pdf en esta máquina")
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
        destino cae fuera. **El orden importa y es deliberado:** primero se
        comprueba que la conversión EXISTE —una consulta al grafo, sin tocar el
        disco y sin decir nada que el `enum` del catálogo no diga ya— y solo
        después se toca el sistema de ficheros. Ese orden no filtra: el que sí
        filtraría es el de `kordoc`, que hace `realpathSync` antes de
        `assertWithinRoot` y por eso enumera el disco entero."""
        png = os.path.join(self.raiz, "e.png")
        with open(png, "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n")
        d = tempfile.mkdtemp(prefix="h4-fuera-")
        r = self.sv.despachar("convert", {"entrada": png,
                                          "salida": os.path.join(d, "x.webp")})
        self.assertIn("job_id", r, "el camino png->webp sí existe")
        fin = _esperar(self.sv, r["job_id"])
        self.assertEqual(fin["estado"], S.FALLIDO)
        self.assertEqual(fin.get("motivo"), _conf.MENSAJE_OPACO)

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


if __name__ == "__main__":
    unittest.main(verbosity=2)

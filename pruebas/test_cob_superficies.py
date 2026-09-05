"""Cobertura de las CUATRO superficies de usuario: CLA, watcher, API y el
punto de entrada `python -m filex`.

    python -m unittest pruebas.test_cob_superficies -v

**Este fichero no añade producto: añade EJECUCIÓN.** El carril nace de una
medida del maestro (`bench/cobertura-superficies.md` §1): `filex/__main__.py`
al 0,0 %, `cli.py` al 35,2 %, `watcher.py` al 58,9 % y `api.py` al 65,3 %, con
279 líneas sin ejecutar entre los cuatro. Y nace con la trampa delante:

    **La cobertura es la única métrica de este proyecto que se puede subir sin
    medir nada.** Un `try: main([...]) except SystemExit: pass` sube el
    porcentaje de un `main()` entero y no afirma nada.

Por eso **cada prueba de este fichero tiene un control de discriminación
registrado**: se rompe UNA línea del módulo objetivo y se comprueba que la
prueba se pone ROJA (trampa 116 — un control que no discrimina no es un
control). La tabla vive en `bench/cobertura-superficies.md` §4 y la produce
`bench/salidas-cobertura-superficies/discriminacion.py`, que restaura el
código con `git checkout -- filex/<modulo>.py` (nunca `git stash push`:
trampa 119, sobre un fichero ya commiteado no hace nada y devuelve 0).

## Tres decisiones de método, y las tres tienen motivo escrito

1. **Cuando el objetivo es un FORMATEADOR, la entrada se construye a mano.**
   `cli._plan`, `cli._convertir` y `cli._inventario` imprimen lo que el núcleo
   les da. Con los seis motores de esta máquina **no existe ni un par
   (origen, destino) cuyo plan lleve `aviso`** —MEDIDO: 34×34 pares, 0 con
   aviso, `bench/salidas-cobertura-superficies/explorar3.py`—, no hay motor
   ausente que listar, y ninguna arista deja ficheros `sobrantes`. Esas ramas
   sólo se ejecutan alimentando las **dataclases reales** del núcleo
   (`nucleo.Conversion`, `nucleo.Salto`, `grafo.Arista`, `grafo.Camino`), que
   es lo que se hace aquí: nunca un duplicado del tipo, siempre el tipo.
   Y al lado de cada una hay una prueba de EXTREMO A EXTREMO con `magick` de
   verdad, para que la forma construida a mano no se separe de la real.
2. **`_tenedores_posix` es de POSIX y estamos en Windows.** No se marca
   `no_aplica`: se ejecuta contra un `/proc` **simulado** (`os.listdir` y
   `os.stat` desviados sólo para las rutas que empiezan por `/proc`), con
   ficheros y ENLACES DUROS de verdad, para que la coincidencia por
   `(st_dev, st_ino)` —que es todo el algoritmo— sea real y no un `assert` de
   adorno. Lo que sí queda declarado `no_aplica` está en el informe §5.
3. **Ningún tiempo absoluto** (§3 de `CLAUDE.md`). Todos los veredictos son
   deterministas.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import runpy
import shutil
import socket
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filex import api as _api          # noqa: E402
from filex import cli as _cli          # noqa: E402
from filex import confinamiento as _conf   # noqa: E402
from filex import grafo as _grafo      # noqa: E402
from filex import nucleo as _nucleo    # noqa: E402
from filex import watcher as _watch    # noqa: E402
from filex.confinamiento import Denegado   # noqa: E402
from filex.nucleo import FileX         # noqa: E402
from filex.servicio import Trabajos    # noqa: E402
from filex.watcher import Atendido, Huella, Memoria, Vigilante  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PNG = os.path.join(RAIZ, "corpus", "imagen", "tipico.png")

#: Igual que en `pruebas/test_hito7.py`: sin ImageMagick ningún motor lee png,
#: así que las pruebas de extremo a extremo no tienen sujeto (C42,
#: `bench/ci-y-contrato.md` §1). Las de formateo NO dependen de esto.
HAY_IMAGEMAGICK = shutil.which("magick") is not None
_SIN_IM = "no hay ImageMagick (`magick`): ningún motor lee png"

#: **El corpus puede ser un puntero de Git LFS** (trampa 34), y `os.path.exists`
#: devuelve `True` para los 130 B del puntero (trampa 107: un guarda que
#: comprueba la EXISTENCIA de un activo de LFS no comprueba nada). Se mira el
#: TAMAÑO, que para `tipico.png` es 42 855 B.
_TAM_PNG = 42855
HAY_CORPUS = os.path.isfile(PNG) and os.path.getsize(PNG) > 1024
_SIN_CORPUS = (f"`corpus/imagen/tipico.png` no está materializado "
               f"(se esperan {_TAM_PNG} B; con LFS sin descargar son 130): "
               f"`git lfs checkout` (trampas 34 y 107)")

ES_WINDOWS = os.name == "nt"

_FX = None
_LOCK_FX = threading.Lock()


def fx_de(raices):
    """Un `FileX` con lista blanca reaprovechando el sondeo de motores.

    Mismo motivo que en `pruebas/test_hito7.py`: el sondeo no depende de las
    raíces. Se copian los cuatro atributos que `FileX.__init__` fija.
    """
    global _FX
    with _LOCK_FX:
        if _FX is None:
            _FX = FileX()
    fx = FileX.__new__(FileX)
    fx.barrido = _FX.barrido
    fx.motores = _FX.motores
    fx.grafo = _FX.grafo
    fx.confinamiento = _conf.Confinamiento(raices) if raices else None
    return fx


def _arista(origen="png", destino="webp", motor="imagemagick", **kw):
    return _grafo.Arista(origen=origen, destino=destino, motor=motor, **kw)


def _camino(*pares):
    return _grafo.Camino(pasos=[_grafo.Paso(_arista(o, d)) for o, d in pares],
                         coste=float(len(pares)))


@contextlib.contextmanager
def _salidas():
    """Captura `stdout` y `stderr` a la vez y los devuelve como cadenas."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        yield out, err


class _FxDePapel:
    """Un `FileX` de mentira para las ramas que esta máquina no produce.

    Sólo tiene lo que la función bajo prueba usa. **No reimplementa ningún
    tipo del núcleo**: los objetos que devuelve son `nucleo.Conversion`,
    `nucleo.Salto` y `grafo.Decision` de verdad.
    """

    def __init__(self, *, decision=None, conversion=None, disponibles=(),
                 ausentes=(), aristas=(), destinos=()):
        self._decision = decision
        self._conversion = conversion
        self.disponibles = list(disponibles)
        self.ausentes = list(ausentes)
        self.grafo = type("G", (), {"aristas": list(aristas)})()
        self._destinos = list(destinos)
        self.confinamiento = None

    def planificar(self, entrada, salida):
        return self._decision

    def convertir(self, entrada, salida, pedido=None, timeout=None):
        if isinstance(self._conversion, Exception):
            raise self._conversion
        return self._conversion

    def destinos(self, ext):
        return self._destinos


class _MotorDePapel:
    def __init__(self, nombre, version="", aristas=(), motivo_ausencia="",
                 binario=""):
        self.nombre = nombre
        self.version = version
        self.aristas = list(aristas)
        self.motivo_ausencia = motivo_ausencia
        self.binario = binario


# ===========================================================================
#  filex/cli.py — el inventario, los destinos y el plan
# ===========================================================================


class CliInventario(unittest.TestCase):
    """`cli._inventario` y `cli._destinos`. Objetivo: 23-42 y 46-56."""

    def test_el_inventario_nombra_la_capacidad_que_falta_no_el_comando(self):
        """R14: el mensaje de un motor ausente nombra la CAPACIDAD, no el
        `pip install` que la trae — y cuando no hay motivo, nombra el binario.

        Se construye a mano porque en esta máquina **los seis motores están
        presentes**: `fx.ausentes` está vacío (MEDIDO,
        `bench/salidas-cobertura-superficies/explorar4.py`), así que el bucle
        de ausentes no se ejecutaría nunca con un `FileX` real.
        """
        aristas = [_arista(estado="real"), _arista("png", "gif", estado="nominal")]
        fx = _FxDePapel(
            disponibles=[_MotorDePapel("imagemagick", "7.1.2", aristas)],
            ausentes=[_MotorDePapel("docling", motivo_ausencia="falta el modelo"),
                      _MotorDePapel("vips", binario="vips")],
            aristas=aristas)
        with _salidas() as (out, _):
            rc = _cli._inventario(fx, None)
        texto = out.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("✓ imagemagick", texto)
        self.assertIn("2 aristas (1 medidas)", texto)
        self.assertIn("✗ docling", texto)
        self.assertIn("falta el modelo", texto)
        # Sin motivo declarado, el mensaje nombra el ejecutable que falta.
        self.assertIn("falta el ejecutable 'vips'", texto)
        self.assertIn("GRAFO: 2 aristas, 1 respaldadas", texto)

    def test_el_inventario_real_lista_los_motores_de_esta_maquina(self):
        """El mismo camino, con el `FileX` de verdad: la forma construida a
        mano de la prueba anterior no puede separarse de la real sin que ésta
        se entere."""
        fx = fx_de(None)
        with _salidas() as (out, _):
            rc = _cli._inventario(fx, None)
        texto = out.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("MOTORES", texto)
        self.assertIn(f"GRAFO: {len(fx.grafo.aristas)} aristas", texto)
        for m in fx.disponibles:
            self.assertIn(m.nombre, texto)

    def test_destinos_desconocido_es_error_de_uso(self):
        args = _cli.construir_parser().parse_args(["destinos", "xyzzy"])
        with _salidas() as (out, err):
            rc = _cli._destinos(fx_de(None), args)
        self.assertEqual(rc, 2)
        self.assertIn("formato desconocido", err.getvalue())
        self.assertEqual(out.getvalue(), "")

    def test_destinos_conocido_sin_salida_es_fallo_de_negocio(self):
        """`json` está en el vocabulario y **ningún motor de esta máquina llega
        a ningún sitio desde él** (MEDIDO: 6 formatos así). Es `1`, no `2`:
        la orden se entendió."""
        fx = fx_de(None)
        vacios = [e for e in ("json", "tsv", "aac", "mpd") if not fx.destinos(e)]
        self.assertTrue(vacios, "esta máquina ya llega a todos los formatos")
        args = _cli.construir_parser().parse_args(["destinos", vacios[0]])
        with _salidas() as (out, _):
            rc = _cli._destinos(fx, args)
        self.assertEqual(rc, 1)
        self.assertIn("no se llega a ningún destino", out.getvalue())

    def test_destinos_lista_los_alcanzables(self):
        fx = fx_de(None)
        args = _cli.construir_parser().parse_args(["destinos", "png"])
        with _salidas() as (out, _):
            rc = _cli._destinos(fx, args)
        texto = out.getvalue()
        self.assertEqual(rc, 0)
        esperados = fx.destinos("png")
        self.assertIn(f"({len(esperados)} destinos)", texto)
        for e in esperados:
            self.assertIn(e, texto)


class CliPlan(unittest.TestCase):
    """`cli._plan`. Objetivo: 60-78."""

    def test_sin_camino_lo_dice_y_devuelve_1(self):
        fx = fx_de(None)
        args = _cli.construir_parser().parse_args(["plan", "x.png", "y.xyzzy"])
        with _salidas() as (out, _):
            rc = _cli._plan(fx, args)
        self.assertEqual(rc, 1)
        self.assertIn("NO HAY CAMINO", out.getvalue())

    def test_con_camino_enseña_los_saltos_y_cuenta_los_descartes(self):
        """Los descartes que se ENSEÑAN son como mucho cuatro, y el resto se
        cuenta. png→webp tiene 8 descartados en esta máquina, ninguno
        «interesante», así que se ven 4 y se anuncia `+4`."""
        fx = fx_de(None)
        args = _cli.construir_parser().parse_args(["plan", "x.png", "y.webp"])
        dec = fx.planificar("x.png", "y.webp")
        self.assertTrue(dec.hay)
        with _salidas() as (out, _):
            rc = _cli._plan(fx, args)
        texto = out.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("CAMINO (1 salto(s)", texto)
        self.assertIn("png→webp", texto)
        self.assertEqual(texto.count("DESCARTADO"), min(4, len(dec.rechazados)))
        resto = len(dec.rechazados) - min(4, len(dec.rechazados))
        if resto > 0:
            self.assertIn(f"(+{resto} camino(s)", texto)

    def test_el_aviso_de_rasterizacion_se_imprime(self):
        """*El único camino disponible rasteriza y el destino admite texto.*

        Construido a mano: con los seis motores de esta máquina **no hay ni un
        par (origen, destino) cuyo plan lleve aviso** —0 de 1 122 pares,
        MEDIDO—, así que ésta es la única forma de ejecutar la rama.
        """
        dec = _grafo.Decision(camino=_camino(("svg", "pdf")),
                              rechazados=[(_camino(("svg", "png"), ("png", "pdf")),
                                           "rasteriza y pierde el texto")],
                              aviso="el ÚNICO camino disponible rasteriza")
        args = _cli.construir_parser().parse_args(["plan", "x.svg", "y.pdf"])
        with _salidas() as (out, _):
            rc = _cli._plan(_FxDePapel(decision=dec), args)
        texto = out.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("AVISO  el ÚNICO camino disponible rasteriza", texto)
        # Un descarte «interesante» (rasteriza/pierde) desplaza a los demás.
        self.assertIn("DESCARTADO  svg → png → pdf", texto)
        self.assertNotIn("camino(s) válido(s)", texto)


# ===========================================================================
#  filex/cli.py — la conversión
# ===========================================================================


class CliConvertirParams(unittest.TestCase):
    """`cli._convertir`, las dos negativas de `--params`. Objetivo: 84-97."""

    def _args(self, *extra):
        return _cli.construir_parser().parse_args(
            ["convertir", "a.png", "b.webp", *extra])

    def test_params_que_no_es_json_es_error_de_uso(self):
        args = self._args("--params", "{no soy json")
        with _salidas() as (out, err):
            rc = _cli._convertir(_FxDePapel(), args)
        self.assertEqual(rc, 2)
        self.assertIn("--params no es JSON válido", err.getvalue())
        self.assertEqual(out.getvalue(), "")

    def test_params_json_valido_pero_no_objeto_tambien_es_2(self):
        """`--params 42` y `--params '[1,2]'` llegaban como `int`/`list` hasta
        el núcleo y reventaban con un traceback. `--params null` es la
        excepción: `None` cae en `pedido or {}`."""
        for crudo, tipo in (("42", "int"), ("[1,2]", "list"), ('"x"', "str")):
            with self.subTest(crudo=crudo):
                args = self._args("--params", crudo)
                with _salidas() as (_, err):
                    rc = _cli._convertir(_FxDePapel(), args)
                self.assertEqual(rc, 2)
                self.assertIn(f"no {tipo}", err.getvalue())

    def test_params_null_no_se_rechaza(self):
        """La excepción que confirma la regla: `null` NO es un objeto y aun así
        pasa, porque `None` cae en `pedido or {}` del núcleo."""
        args = self._args("--params", "null")
        conv = _nucleo.Conversion(entrada="a.png", salida="b.webp", ok=False,
                                  motivo="sin_camino")
        with _salidas() as (out, err):
            rc = _cli._convertir(_FxDePapel(conversion=conv), args)
        self.assertEqual(rc, 1)                    # llegó al núcleo, no a la guarda
        self.assertNotIn("--params", err.getvalue())
        self.assertIn("NO CONVERTIDO", out.getvalue())


class CliConvertirImpresion(unittest.TestCase):
    """`cli._convertir`, lo que IMPRIME. Objetivo: 117-147 y `_fmt_ms` (19)."""

    def _args(self, *extra):
        return _cli.construir_parser().parse_args(
            ["convertir", "a.png", "b.webp", *extra])

    def test_fmt_ms_cambia_de_precision_por_debajo_del_milisegundo(self):
        self.assertEqual(_cli._fmt_ms(1234.6), "1235 ms")
        self.assertEqual(_cli._fmt_ms(1.0), "1 ms")
        self.assertEqual(_cli._fmt_ms(0.214), "0.21 ms")

    def test_un_fallo_enseña_el_camino_intentado_y_el_stderr_solo_con_verboso(self):
        """R: *nunca devolver `stderr` crudo al modelo*. En la CLI hay un
        humano, y aun así hace falta pedirlo con `-v`."""
        salto = _nucleo.Salto(arista=_arista(), rc=1, err="magick: no such file\n")
        conv = _nucleo.Conversion(entrada="a.png", salida="b.webp",
                                  camino=_camino(("png", "webp")), saltos=[salto],
                                  ok=False, motivo="el_motor_rechazo_la_conversion")
        with _salidas() as (out, _):
            rc = _cli._convertir(_FxDePapel(conversion=conv), self._args())
        texto = out.getvalue()
        self.assertEqual(rc, 1)
        self.assertIn("NO CONVERTIDO — el_motor_rechazo_la_conversion", texto)
        self.assertIn("camino intentado: png → webp", texto)
        self.assertNotIn("no such file", texto)          # sin -v no cruza

        with _salidas() as (out, _):
            _cli._convertir(_FxDePapel(conversion=conv), self._args("-v"))
        self.assertIn("no such file", out.getvalue())

    def test_un_fallo_sin_formatos_no_imprime_un_camino_vacio(self):
        """`conv.camino` puede existir con `formatos == []` (origen y destino
        en el mismo formato, saltos=0). Sin el segundo chequeo imprimía
        `camino intentado: ` con nada detrás."""
        conv = _nucleo.Conversion(entrada="a.png", salida="b.png",
                                  camino=_grafo.Camino(), ok=False,
                                  motivo="mismo_formato")
        with _salidas() as (out, _):
            rc = _cli._convertir(_FxDePapel(conversion=conv), self._args())
        self.assertEqual(rc, 1)
        self.assertNotIn("camino intentado", out.getvalue())

    def test_un_exito_enseña_contrato_hallazgos_aviso_y_el_punto_5(self):
        """La rama humana entera, con las tres cosas que esta máquina no
        produce por sí sola: `aviso`, un hallazgo y ficheros `sobrantes`.

        Los `sobrantes` son el punto 5 en lenguaje humano — `ffmpeg -i x
        out.mpd` deja los segmentos DASH en el `cwd` (trampa 21). **Ninguna
        arista de esta máquina llega a `mpd`** (MEDIDO: no está entre los
        destinos de `mp4`), así que la rama se alimenta a mano.
        """
        salto = _nucleo.Salto(
            arista=_arista(), rc=0, ms=214.7, veredicto="ok_parcial",
            hallazgos=[{"severidad": "informativo", "regla": "I5",
                        "mensaje": "reduccion de profundidad inevitable"}],
            cobertura={"1_firma": True, "2_flujos": True, "3_declarado": False,
                       "4_pedido": True, "5_escritura": True, "cobertura": "x"},
            sobrantes={"chunk-0.m4s": 12, "init.mp4": 34})
        conv = _nucleo.Conversion(
            entrada="a.png", salida="b.webp", camino=_camino(("png", "webp")),
            saltos=[salto], ok=True, aviso="el cerrojo de máquina degradó",
            rechazados=[(_camino(("png", "gif"), ("gif", "webp")),
                         "válido, pero más caro"),
                        (_camino(("png", "tif"), ("tif", "webp")),
                         "rasteriza y pierde")])
        with _salidas() as (out, _):
            rc = _cli._convertir(_FxDePapel(conversion=conv), self._args())
        texto = out.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("b.webp   [ok_parcial]", texto)
        self.assertIn("aviso: el cerrojo de máquina degradó", texto)
        # `cobertura` no cuenta: las claves del contrato empiezan por dígito.
        self.assertIn("contrato 4/5", texto)
        self.assertIn("215 ms", texto)
        self.assertIn("[informativo] I5:", texto)
        self.assertIn("punto 5: el motor escribió 2 fichero(s) no declarado(s)",
                      texto)
        self.assertIn("chunk-0.m4s, init.mp4", texto)
        # Sin `-v` sólo se enseña el descarte que ENSEÑA algo.
        self.assertIn("descartado png → tif → webp", texto)
        self.assertNotIn("descartado png → gif → webp", texto)

        with _salidas() as (out, _):
            _cli._convertir(_FxDePapel(conversion=conv), self._args("-v"))
        self.assertIn("descartado png → gif → webp", out.getvalue())


@unittest.skipUnless(HAY_CORPUS, _SIN_CORPUS)
@unittest.skipUnless(HAY_IMAGEMAGICK, _SIN_IM)
class CliExtremoAExtremo(unittest.TestCase):
    """La CLI entera con un motor de verdad. Objetivo: 243, 247-248, 252-256.

    R18: **directorio desechable por conversión**, y se lista antes y después
    (trampa 21: hay motores que escriben en el `cwd`, y una vez aparecieron 33
    ficheros no pedidos en la raíz del repositorio).
    """

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="filex-cob-cli-")
        self.entrada = os.path.join(self.dir, "tipico.png")
        shutil.copy2(PNG, self.entrada)
        self.cwd = os.getcwd()
        self.antes_cwd = set(os.listdir(self.cwd))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)
        nuevos = set(os.listdir(self.cwd)) - self.antes_cwd
        self.assertEqual(nuevos, set(),
                         f"el motor escribió fuera del destino, en el cwd: {nuevos}")

    def test_la_forma_corta_sin_subcomando_convierte_y_avisa_de_la_lista_blanca(self):
        """`filex a.png b.webp` — la forma corta del hito 1, que estuvo MUERTA
        hasta que se detectó ANTES de `parse_args`. Sin `--raiz` no hay lista
        blanca y se dice por `stderr`."""
        salida = os.path.join(self.dir, "corta.webp")
        with _salidas() as (out, err):
            rc = _cli.main([self.entrada, salida])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(salida))
        self.assertIn("aviso: sin --raiz no hay lista blanca", err.getvalue())
        self.assertIn("corta.webp", out.getvalue())
        self.assertIn("contrato ", out.getvalue())

    def test_sin_subcomando_y_sin_dos_posicionales_sale_la_ayuda_con_rc_0(self):
        with _salidas() as (out, _):
            rc = _cli.main([])
        self.assertEqual(rc, 0)
        self.assertIn("usage: filex", out.getvalue())

    def test_una_raiz_que_no_confina_impide_arrancar_con_rc_2(self):
        """R6: sin ninguna raíz de lectura accesible FileX no arranca, y la CLI
        lo traduce a `2` (error de USO), no a `1`."""
        with _salidas() as (out, err):
            rc = _cli.main(["--raiz", "", "convertir", self.entrada,
                            os.path.join(self.dir, "nunca.webp")])
        self.assertEqual(rc, 2)
        self.assertIn("no se puede arrancar", err.getvalue())
        self.assertEqual(out.getvalue(), "")

    def test_el_VALOR_de_una_bandera_ya_no_cuenta_como_posicional(self):
        """**Defecto MEDIDO y ARREGLADO** (`bench/fix-superficies.md` §2).
        Dos síntomas, una sola causa.

        La forma corta se detecta ANTES de `parse_args`, y el filtro de
        entonces —`[a for a in argv if not a.startswith("-")]`— quitaba las
        BANDERAS pero no sus VALORES. Consecuencias que ya no se dan:

        a. `filex --raiz D a.png b.webp` daba `resto` de 3 elementos, la forma
           corta no se activaba, argparse veía `a.png` donde espera un
           subcomando y abortaba con `SystemExit(2)`. **La forma corta y el
           confinamiento eran incompatibles**, que es justo la combinación que
           escribiría un usuario prudente.
        b. `filex --raiz D motores` daba `resto == ["D", "motores"]`, que sí
           mide 2, así que la forma corta se activaba **por error** y la orden
           se reescribía a `convertir --raiz D motores`.

        Y se comprueba además que la raíz **manda de verdad**: no basta con que
        la orden analice sintácticamente, tiene que confinar.
        """
        salida = os.path.join(self.dir, "corta-con-raiz.webp")
        with _salidas() as (out, _):
            rc = _cli.main(["--raiz", self.dir, self.entrada, salida])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(salida))
        # Con `--raiz` NO sale el aviso de «sin lista blanca»: es la prueba de
        # que la bandera llegó al parser principal y no al subparser.
        self.assertIn("corta-con-raiz.webp", out.getvalue())

        # (b) El subcomando del usuario sigue siendo suyo.
        with _salidas() as (out2, err2):
            rc2 = _cli.main(["--raiz", self.dir, "motores"])
        self.assertEqual(rc2, 0)
        self.assertIn("motores", out2.getvalue().lower())
        self.assertNotIn("convertir", err2.getvalue())

        # Y con el subcomando explícito la misma orden sigue funcionando.
        with _salidas():
            rc3 = _cli.main(["--raiz", self.dir, "convertir", self.entrada,
                             os.path.join(self.dir, "explicita.webp")])
        self.assertEqual(rc3, 0)

    def test_la_forma_corta_con_raiz_SIGUE_confinando(self):
        """La forma corta que ahora convive con `--raiz` no puede convertirse
        en una puerta trasera: con la raíz puesta, una entrada de fuera se
        deniega igual que con el subcomando explícito.

        Sin esta prueba, «`--raiz D a.png b.webp` ya funciona» sería
        compatible con haber colado `--raiz` dentro del subparser y perderla.
        """
        fuera = tempfile.mkdtemp(prefix="filex-cob-cli-fuera-")
        try:
            ajena = os.path.join(fuera, "ajena.png")
            shutil.copy2(PNG, ajena)
            with _salidas() as (out, err):
                rc = _cli.main(["--raiz", self.dir, ajena,
                                os.path.join(self.dir, "nunca.webp")])
            self.assertEqual(rc, 1)
            self.assertFalse(os.path.exists(os.path.join(self.dir, "nunca.webp")))
            self.assertNotIn(fuera, out.getvalue() + err.getvalue())
        finally:
            shutil.rmtree(fuera, ignore_errors=True)

    def test_una_bandera_del_subcomando_con_valor_tampoco_cuenta(self):
        """El mismo defecto por la otra puerta: `--params` lleva valor y vive
        en el subparser `convertir`. Antes, `filex a.png b.webp --params {...}`
        daba `resto` de 3 y la forma corta no se activaba."""
        salida = os.path.join(self.dir, "params.webp")
        with _salidas() as (out, _):
            rc = _cli.main([self.entrada, salida, "--params", '{"ancho": 40}'])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(salida))
        self.assertIn("params.webp", out.getvalue())

    def test_las_banderas_con_valor_salen_del_PARSER_y_no_de_una_lista_a_mano(self):
        """La fuente de verdad es `construir_parser()`, recorrido también por
        sus subparsers. Una lista escrita a mano se desincroniza en silencio el
        día que alguien añada una bandera — y el síntoma sería este mismo
        defecto, otra vez.

        Se comprueba en las dos direcciones (trampa 73): las que llevan valor
        están, y las que no llevan valor NO están.
        """
        con_valor = _cli._banderas_con_valor(_cli.construir_parser())
        for lleva in ("--raiz", "--params", "--timeout"):
            self.assertIn(lleva, con_valor)
        for no_lleva in ("--json", "-v", "--verboso", "--version", "-h", "--help"):
            self.assertNotIn(no_lleva, con_valor)


# ===========================================================================
#  Los puntos de entrada `python -m ...`
# ===========================================================================


class PuntosDeEntrada(unittest.TestCase):
    """`python -m filex` y los tres `if __name__ == "__main__"`.

    `filex/__main__.py` estaba al **0,0 %**: ninguna prueba invocaba el punto
    de entrada del paquete. Se ejecuta con `runpy.run_module(..., run_name=
    "__main__")`, que corre el MISMO fichero con el mismo nombre de módulo que
    `python -m` y **sin lanzar un proceso hijo** —matar o esperar por
    `Popen.pid` en Windows no alcanza a quien uno cree, porque el `python.exe`
    de un venv es un lanzador (trampa 93)—.

    Cada uno se invoca con los argumentos que **vuelven antes de construir un
    `FileX`**: el objetivo es la línea `raise SystemExit(main())`, no el
    motor.
    """

    @contextlib.contextmanager
    def _como_main(self, *argv):
        viejo = sys.argv
        sys.argv = list(argv)
        try:
            with _salidas() as (out, err):
                yield out, err
        finally:
            sys.argv = viejo

    def test_python_m_filex_sin_argumentos_imprime_la_ayuda_y_sale_con_0(self):
        with self._como_main("filex") as (out, _):
            with self.assertRaises(SystemExit) as ctx:
                runpy.run_module("filex", run_name="__main__")
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("usage: filex", out.getvalue())
        self.assertIn("convertir", out.getvalue())

    def test_importar_el_punto_de_entrada_NO_arranca_la_CLI(self):
        """La otra mitad del `if __name__ == "__main__"`, y la que de verdad
        importa: `import filex.__main__` tiene que ser inerte. Un punto de
        entrada que hiciera algo al importarse convertiría cualquier
        herramienta que recorra el paquete —un `pydoc`, un `pkgutil.walk`— en
        un lanzador de la CLI."""
        sys.modules.pop("filex.__main__", None)
        with self._como_main("no-deberia-mirarse") as (out, err):
            import filex.__main__ as entrada
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue(), "")
        self.assertIs(entrada.main, _cli.main)

    def test_python_m_filex_cli_es_el_mismo_punto_de_entrada(self):
        with self._como_main("filex.cli") as (out, _):
            with self.assertRaises(SystemExit) as ctx:
                runpy.run_module("filex.cli", run_name="__main__")
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("usage: filex", out.getvalue())

    def test_python_m_filex_api_se_niega_a_salir_de_loopback(self):
        with self._como_main("filex-api", "--host", "203.0.113.9") as (_, err):
            with self.assertRaises(SystemExit) as ctx:
                runpy.run_module("filex.api", run_name="__main__")
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("permitir-red", err.getvalue())

    def test_python_m_filex_watcher_rechaza_un_params_que_no_es_json(self):
        with self._como_main("filex-watch", "--vigilar", RAIZ, "--salida", RAIZ,
                             "--destino", "webp", "--params", "{roto") as (_, err):
            with self.assertRaises(SystemExit) as ctx:
                runpy.run_module("filex.watcher", run_name="__main__")
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("--params no es JSON válido", err.getvalue())


# ===========================================================================
#  filex/api.py — transporte puro
# ===========================================================================


class _ManejadorDeBanco(_api.Manejador):
    """El manejador SIN socket, para las ramas defensivas del transporte.

    `BaseHTTPRequestHandler.__init__` atiende la petición dentro del propio
    constructor, así que no se puede instanciar para inspeccionarlo. Aquí se
    sustituye el constructor y las tres llamadas de cabecera; **`_responder`,
    `_rechazo` y `_cuerpo` son los de producción**, que es lo que se prueba.
    """

    def __init__(self, cabeceras=None, rfile=None, wfile=None):
        self.headers = cabeceras or {}
        self.rfile = rfile
        self.wfile = wfile if wfile is not None else io.BytesIO()
        self.close_connection = False
        self.enviado = []

    def send_response(self, codigo, *a):
        self.enviado.append(("codigo", codigo))

    def send_header(self, clave, valor):
        self.enviado.append((clave, valor))

    def end_headers(self):
        self.enviado.append(("fin", ""))

    @property
    def codigo(self):
        return next(v for k, v in self.enviado if k == "codigo")


class _FicheroQueRevienta:
    def __init__(self, excepcion):
        self.excepcion = excepcion

    def write(self, datos):
        raise self.excepcion

    def read(self, n=-1):
        raise self.excepcion


class ApiTransporteDefensivo(unittest.TestCase):
    """Las ramas de `_responder`, `_rechazo` y `_cuerpo` que un cliente bien
    educado no produce. Objetivo: 121-130, 170-171, 184-185, 189-190, 247-249."""

    def test_es_ip_literal_separa_una_ip_de_un_nombre(self):
        """El *DNS rebinding* necesita un NOMBRE; con una IP literal no hay
        nada que rebindear. Es la única defensa que queda al escuchar en
        `0.0.0.0`."""
        for si in ("127.0.0.1", "192.168.1.107", "::1", "[::1]", "2001:db8::1",
                   " 10.0.0.1 "):
            self.assertTrue(_api._es_ip_literal(si), si)
        for no in ("malo.example", "localhost", "", "1.2.3", "[malo]", "999.1.1.1"):
            self.assertFalse(_api._es_ip_literal(no), no)

    def test_si_el_cliente_cuelga_la_respuesta_no_revienta_la_superficie(self):
        """Una superficie que revienta con una traza es una superficie que
        filtra. `BrokenPipe`/`ConnectionReset` al escribir se tragan."""
        for exc in (BrokenPipeError(), ConnectionResetError()):
            with self.subTest(exc=type(exc).__name__):
                m = _ManejadorDeBanco(wfile=_FicheroQueRevienta(exc))
                m._responder(200, {"ok": True})       # no debe propagar
                self.assertEqual(m.codigo, 200)
                self.assertIn(("X-Content-Type-Options", "nosniff"), m.enviado)
                self.assertIn(("Cache-Control", "no-store"), m.enviado)

    def test_la_respuesta_anuncia_close_cuando_va_a_cerrar(self):
        m = _ManejadorDeBanco()
        m.close_connection = True
        m._responder(421, {"error": "host no admitido"})
        self.assertIn(("Connection", "close"), m.enviado)

    def test_un_rechazo_con_content_length_ilegible_no_intenta_leer_nada(self):
        """`int('abc')` revienta; sin el `except` el rechazo se convertiría en
        una traza. Se trata como 0 y se cierra."""
        m = _ManejadorDeBanco({"Content-Length": "abc"},
                              rfile=_FicheroQueRevienta(AssertionError("no leer")))
        m._rechazo(400, "longitud no válida")
        self.assertEqual(m.codigo, 400)
        self.assertTrue(m.close_connection)

    def test_un_rechazo_descarta_el_cuerpo_y_aguanta_que_el_socket_muera(self):
        """Con `keep-alive`, rechazar sin consumir el cuerpo deja bytes en el
        socket y la petición siguiente se lee sobre la mitad de la anterior
        (MEDIDO como `WinError 10053`). Se descarta lo que quepa; si el socket
        ya murió, tampoco se propaga."""
        leidos = []

        class _Rfile:
            def read(self, n):
                leidos.append(n)
                return b"x" * n

        m = _ManejadorDeBanco({"Content-Length": "17"}, rfile=_Rfile())
        m._rechazo(415, "se requiere application/json")
        self.assertEqual(leidos, [17])

        m2 = _ManejadorDeBanco({"Content-Length": "17"},
                               rfile=_FicheroQueRevienta(OSError("socket muerto")))
        m2._rechazo(415, "se requiere application/json")
        self.assertEqual(m2.codigo, 415)

    def test_un_cuerpo_con_content_length_ilegible_es_400_y_no_None_silencioso(self):
        m = _ManejadorDeBanco({"Content-Length": "no-soy-un-numero"})
        self.assertIsNone(m._cuerpo())
        self.assertEqual(m.codigo, 400)


class ApiHostDeclarado(unittest.TestCase):
    """`_host_admitido`. Objetivo: 210-214 y 222.

    **Las dos defensas se anulaban entre sí** (`bench/hito7-superficies.md`
    §6.2): sin la segunda mitad, `--permitir-red` no servía de nada porque una
    petición legítima desde la LAN llega con `Host: 192.168.x.y`.

    No se abre ni un puerto fuera de loopback: lo que decide es el atributo
    `host_declarado` del servidor, que es exactamente lo que `main` le pone.
    """

    def _manejador(self, declarado, host):
        m = _ManejadorDeBanco({"Host": host})
        m.server = type("S", (), {"host_declarado": declarado})()
        return m

    def test_sin_direccion_declarada_solo_pasa_loopback(self):
        self.assertTrue(self._manejador("", "127.0.0.1:8756")._host_admitido("127.0.0.1:8756"))
        self.assertFalse(self._manejador("", "malo.example")._host_admitido("malo.example"))
        # Declarada pero de loopback: tampoco abre la puerta a nadie más.
        self.assertFalse(
            self._manejador("127.0.0.1", "malo.example")._host_admitido("malo.example"))

    def test_la_direccion_declarada_admite_a_su_cliente_legitimo(self):
        m = self._manejador("192.168.1.107", "192.168.1.107:8756")
        self.assertTrue(m._host_admitido("192.168.1.107:8756"))
        self.assertTrue(m._host_admitido("  192.168.1.107  "))
        self.assertFalse(m._host_admitido("192.168.1.108"))

    def test_en_0_0_0_0_se_admite_una_ip_literal_y_se_rechaza_todo_nombre(self):
        """`0.0.0.0` significa «todas»: no hay una sola dirección con la que
        comparar. Pero el *rebinding* necesita un nombre, así que la IP pasa y
        el nombre no. Sin esta línea, `--permitir-red` desactivaba el cerrojo
        entero y `Host: malo.example` respondía 200."""
        for declarado in ("0.0.0.0", "::"):
            with self.subTest(declarado=declarado):
                m = self._manejador(declarado, "")
                self.assertTrue(m._host_admitido("10.1.2.3"))
                self.assertTrue(m._host_admitido("[2001:db8::1]"))
                self.assertFalse(m._host_admitido("malo.example"))


@unittest.skipUnless(HAY_CORPUS, _SIN_CORPUS)
class ApiEncaminado(unittest.TestCase):
    """Las rutas de `do_GET` y `do_POST` que no tenían cliente. Objetivo:
    155, 256-261, 284-286, 290-293, 317-324.

    **Puerto 0**: lo asigna el sistema y se lee de `server_address`. Un puerto
    fijo chocaría con otro carril y el fallo parecería del producto.
    """

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="filex-cob-api-")
        shutil.copy2(PNG, os.path.join(cls.dir, "bueno.png"))
        cls.srv = _api.construir(fx_de([cls.dir]),
                                 trabajos=Trabajos(os.path.join(cls.dir, "_t")),
                                 host="127.0.0.1", puerto=0)
        cls.puerto = cls.srv.server_address[1]
        cls.hilo = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.hilo.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.hilo.join(timeout=10)
        shutil.rmtree(cls.dir, ignore_errors=True)

    def _http(self, metodo, ruta, crudo=None, cabeceras=None):
        url = f"http://127.0.0.1:{self.puerto}{ruta}"
        datos, cab = (crudo if crudo else (None, {}))
        cab = dict(cab)
        cab.update(cabeceras or {})
        req = urllib.request.Request(url, data=datos, headers=cab, method=metodo)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            cuerpo = e.read()
            try:
                return e.code, json.loads(cuerpo.decode())
            except ValueError:
                return e.code, {"_crudo": cuerpo[:120].decode("utf-8", "replace")}

    _JSON = {"Content-Type": "application/json"}

    def test_destinos_sin_formato_es_400_y_con_formato_responde_la_lista(self):
        cod, d = self._http("GET", "/destinos")
        self.assertEqual(cod, 400)
        self.assertIn("formato", d["error"])

        cod, d = self._http("GET", "/destinos?formato=png")
        self.assertEqual(cod, 200)
        self.assertIn("webp", json.dumps(d))

        # Con destino concreto: la misma respuesta que `list_targets`.
        cod, d = self._http("GET", "/destinos?formato=png&destino=webp")
        self.assertEqual(cod, 200)

    def test_inspeccionar_sin_ruta_es_400_y_una_ruta_ajena_es_404_opaco(self):
        cod, d = self._http("GET", "/inspeccionar")
        self.assertEqual(cod, 400)
        self.assertIn("ruta", d["error"])

        # R4: «prohibido» y «no existe» dicen lo mismo.
        cod, fuera = self._http("GET", "/inspeccionar?ruta=" +
                                urllib.parse.quote(os.path.join(RAIZ, "CLAUDE.md")))
        cod2, noexiste = self._http("GET", "/inspeccionar?ruta=" +
                                    urllib.parse.quote(os.path.join(self.dir, "no.png")))
        self.assertEqual((cod, cod2), (404, 404))
        self.assertEqual(fuera.get("error"), noexiste.get("error"))

        cod, d = self._http("GET", "/inspeccionar?ruta=" +
                            urllib.parse.quote(os.path.join(self.dir, "bueno.png")))
        self.assertEqual(cod, 200)
        self.assertNotIn("contenido", d)              # rutas y metadatos, nunca bytes

    def test_un_lote_sin_entradas_lo_rechaza_el_servicio_no_el_transporte(self):
        cod, d = self._http("POST", "/lote", crudo=(b"{}", self._JSON))
        self.assertEqual(cod, 400)
        self.assertIn("error", d)

    def test_cancelar_un_trabajo_que_no_existe_es_404(self):
        cod, d = self._http("POST", "/trabajos/no-existe/cancelar",
                            crudo=(b"{}", self._JSON))
        self.assertEqual(cod, 404)
        self.assertIn("error", d)

    def test_la_bitacora_calla_por_defecto_y_habla_con_verboso(self):
        """La línea de petición lleva rutas del disco del usuario: volcarla por
        defecto convierte la bitácora en el oráculo que R4 cierra en la
        respuesta."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self._http("GET", "/salud")
        self.assertEqual(err.getvalue(), "")

        self.srv.verboso = True
        try:
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self._http("GET", "/salud")
            self.assertIn("GET /salud", err.getvalue())
        finally:
            self.srv.verboso = False


class _ManejadorImpaciente(_api.Manejador):
    """El manejador de producción con un plazo de socket corto.

    Es la ÚNICA diferencia: `timeout` es un atributo de clase de
    `BaseHTTPRequestHandler`, así que todo lo que se ejecuta debajo —
    `do_POST`, `_cuerpo`, `_rechazo`, `_responder` — es el de `filex/api.py`.
    Existe porque, **con el defecto puesto**, cada celda de la prueba de abajo
    costaba el `TIMEOUT_SOCKET` entero: es el instrumento que hace medible el
    fallo sin pagar 30 s por celda. Se conserva después del arreglo porque es
    justo lo que convierte una regresión en un rojo barato en vez de en una
    suite que tarda un minuto y medio más.
    """

    timeout = 1.5


class _RfileEspia:
    """Registra los `read(n)` con `n > 0` y delega todo lo demás.

    Las cabeceras entran por `readline`, así que lo que este espía cuenta es
    **el cuerpo y sólo el cuerpo**. No sustituye a ninguna pieza de
    producción: la envuelve.
    """

    def __init__(self, crudo, registro):
        self._crudo = crudo
        self._registro = registro

    def read(self, n=-1):
        if n:
            self._registro.append(n)
        return self._crudo.read(n)

    def __getattr__(self, nombre):
        return getattr(self._crudo, nombre)


class _ManejadorQueCuenta(_ManejadorImpaciente):
    """Cuenta las lecturas de cuerpo **por petición**, no por conexión.

    Hace falta por petición porque la propiedad que hay que demostrar es de
    `keep-alive`: un manejador atiende varias peticiones seguidas, así que
    «el cuerpo ya se consumió» tiene que rearmarse en cada una o la petición
    siguiente rechazaría sin descartar el suyo — que es el `WinError 10053`
    que `_rechazo` viene a impedir.

    El espía se monta sobre el `rfile` **crudo** guardado la primera vez: sin
    eso, la segunda petición envolvería al espía de la primera y contaría dos
    veces cada lectura (un instrumento que se mide a sí mismo).
    """

    lecturas: list = []

    def handle_one_request(self):
        crudo = getattr(self, "_rfile_crudo", None)
        if crudo is None:
            crudo = self._rfile_crudo = self.rfile
        self._lecturas_peticion = []
        type(self).lecturas.append(self._lecturas_peticion)
        self.rfile = _RfileEspia(crudo, self._lecturas_peticion)
        super().handle_one_request()


@unittest.skipUnless(HAY_CORPUS, _SIN_CORPUS)
class ApiCuerpoLeidoUnaSolaVez(unittest.TestCase):
    """**Defecto MEDIDO y ARREGLADO** (`bench/fix-superficies.md` §1).
    Objetivo: 256-261 y 324.

    Antes: `_cuerpo` consumía el cuerpo y luego llamaba a `_rechazo`, que
    **lo volvía a leer**; el segundo `read(n)` se quedaba esperando bytes que
    no iban a llegar y sólo lo desatascaba el plazo del socket,
    `TIMEOUT_SOCKET = 30 s`. Aislado, contando las llamadas: **`[5, 5]`**.

    `_rechazo` descarta el cuerpo **a propósito** —con `keep-alive`, rechazar
    sin consumirlo deja bytes en el socket y la petición siguiente se lee
    sobre la mitad de la anterior, MEDIDO como `WinError 10053`—, así que el
    arreglo no es quitar esa lectura: es que `_cuerpo` marque el cuerpo como
    consumido. **Las dos propiedades se comprueban por separado aquí**: que se
    lee una sola vez (abajo) y que el descarte SIGUE ocurriendo cuando el
    rechazo llega antes de leer, incluso en la segunda petición de una misma
    conexión (`test_un_rechazo_ANTES_...` y `test_la_marca_...`).

    Alcance, MEDIDO: el fallo estaba en los **tres** caminos en que `do_POST`
    rechaza DESPUÉS de `_cuerpo` —cuerpo que no es JSON, cuerpo que no es un
    objeto, y `POST` a una ruta desconocida— y **no** en los que rechazan
    antes (`415`, `413`, `421`, `403`), que eran justo los que la suite ya
    tenía: las cuatro defensas probadas eran las cuatro que no lo disparan.
    """

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="filex-cob-api2-")
        cls.srv = _api.Servidor(("127.0.0.1", 0), _ManejadorQueCuenta,
                                _api.Servicio(fx_de([cls.dir]),
                                              Trabajos(os.path.join(cls.dir, "_t"))))
        cls.puerto = cls.srv.server_address[1]
        cls.hilo = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.hilo.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.hilo.join(timeout=10)
        shutil.rmtree(cls.dir, ignore_errors=True)

    def setUp(self):
        _ManejadorQueCuenta.lecturas = []

    def _post(self, ruta, crudo, tipo="application/json"):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.puerto}{ruta}", data=crudo,
            headers={"Content-Type": tipo}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode())

    def _lecturas_de_cuerpo(self):
        """Las lecturas de cuerpo de las peticiones que llegaron a tener una.

        Un `ThreadingHTTPServer` con `keep-alive` deja peticiones abiertas sin
        cuerpo (la que se queda esperando la siguiente línea); esas no cuentan.
        """
        return [l for l in _ManejadorQueCuenta.lecturas if l]

    def test_el_cuerpo_se_lee_UNA_sola_vez(self):
        """El mecanismo, sin socket y sin plazo: se cuenta cuántas veces se
        llama a `read`. **Una.** Con el defecto puesto era `[5, 5]`, y la
        segunda pedía los mismos bytes que la primera ya se había llevado."""
        pedidos = []

        class _Rfile:
            def __init__(self):
                self.queda = b"[1,2]"

            def read(self, n):
                pedidos.append(n)
                datos, self.queda = self.queda[:n], self.queda[n:]
                return datos

        m = _ManejadorDeBanco({"Content-Length": "5"}, rfile=_Rfile())
        self.assertIsNone(m._cuerpo())
        self.assertEqual(m.codigo, 400)
        self.assertEqual(pedidos, [5],
                         "el cuerpo tiene que leerse UNA vez, no dos")

    def test_los_tres_caminos_que_rechazan_despues_de_leer_leen_el_cuerpo_UNA_vez(self):
        """Los tres caminos que disparaban el defecto, sobre socket de verdad.

        La aserción es el **número de lecturas**, no el reloj: la espera de 30 s
        era la consecuencia de la segunda lectura, y contar lecturas es
        determinista mientras que un umbral de tiempo depende del estado de la
        máquina (trampa 101). El coste en reloj se mide aparte, en
        `bench/salidas-fix-superficies/reloj.py`.
        """
        for ruta, crudo, codigo, trozo in (
                ("/convertir", b"{roto", 400, "no es JSON válido"),
                ("/convertir", b"[1,2]", 400, "objeto JSON"),
                ("/no-existe", b"{}", 404, "no hay tal recurso")):
            with self.subTest(ruta=ruta, crudo=crudo):
                _ManejadorQueCuenta.lecturas = []
                cod, d = self._post(ruta, crudo)
                self.assertEqual(cod, codigo)
                self.assertIn(trozo, d["error"])
                self.assertEqual(self._lecturas_de_cuerpo(), [[len(crudo)]],
                                 "el cuerpo se leyó más de una vez")

    def test_un_rechazo_ANTES_de_leer_sigue_descartando_el_cuerpo(self):
        """La otra mitad del contrato, sobre socket de verdad: cuando el
        rechazo llega ANTES de `_cuerpo` (aquí un `415` por `Content-Type`),
        `_rechazo` **sí** tiene que consumir el cuerpo. Una lectura, y es la
        del descarte."""
        cod, d = self._post("/convertir", b"{}" * 8, tipo="text/plain")
        self.assertEqual(cod, 415)
        self.assertIn("application/json", d["error"])
        self.assertEqual(self._lecturas_de_cuerpo(), [[16]],
                         "el rechazo dejó de descartar el cuerpo")

    def test_la_marca_de_consumido_se_rearma_en_cada_peticion(self):
        """`keep-alive`: el manejador se reutiliza, así que la marca es de la
        PETICIÓN y no del manejador.

        Petición 1: un `POST` válido que consume su cuerpo y **no** cierra la
        conexión. Petición 2, por el mismo socket: un `415`, que rechaza antes
        de leer y por tanto tiene que descartar. Sin el rearme, la marca de la
        primera sobreviviría y la segunda dejaría 16 bytes en el socket.
        """
        s = socket.create_connection(("127.0.0.1", self.puerto), timeout=20)
        try:
            uno = json.dumps({"entrada": "no-existe.png",
                              "salida": "no-existe.webp"}).encode()
            s.sendall(b"POST /convertir HTTP/1.1\r\nHost: 127.0.0.1\r\n"
                      b"Content-Type: application/json\r\nContent-Length: "
                      + str(len(uno)).encode() + b"\r\n\r\n" + uno)
            cab = self._leer_respuesta(s)
            self.assertNotIn(b"Connection: close", cab,
                             "la 1.ª petición cerró: no hay 2.ª que medir")

            dos = b"{}" * 8
            s.sendall(b"POST /convertir HTTP/1.1\r\nHost: 127.0.0.1\r\n"
                      b"Content-Type: text/plain\r\nContent-Length: "
                      + str(len(dos)).encode() + b"\r\n\r\n" + dos)
            cab2 = self._leer_respuesta(s)
            self.assertIn(b" 415 ", cab2)
        finally:
            s.close()
        self.assertEqual(self._lecturas_de_cuerpo(), [[len(uno)], [len(dos)]],
                         "la 2.ª petición de la conexión no descartó su cuerpo")

    @staticmethod
    def _leer_respuesta(s) -> bytes:
        """Lee cabeceras y, si lo hay, el cuerpo declarado. Sin `http.client`
        para que la conexión la gobierne la prueba y no una biblioteca."""
        datos = b""
        while b"\r\n\r\n" not in datos:
            trozo = s.recv(4096)
            if not trozo:
                break
            datos += trozo
        cab, _, resto = datos.partition(b"\r\n\r\n")
        n = 0
        for linea in cab.split(b"\r\n"):
            if linea.lower().startswith(b"content-length:"):
                n = int(linea.split(b":")[1])
        while len(resto) < n:
            trozo = s.recv(4096)
            if not trozo:
                break
            resto += trozo
        return cab

    def test_un_cuerpo_vacio_no_lee_nada(self):
        """`n == 0` no lee nada, así que `_rechazo` tampoco: la frontera del
        defecto era «se leyó algo», no «se rechazó»."""
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.puerto}/no-existe", data=b"",
            headers={"Content-Type": "application/json", "Content-Length": "0"},
            method="POST")
        try:
            urllib.request.urlopen(req, timeout=10)
            self.fail("debería ser 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)
        self.assertEqual(self._lecturas_de_cuerpo(), [])


def _hay_loopback_ipv6() -> bool:
    """¿Se puede escuchar en `::1` en esta máquina? Se sondea, no se deduce."""
    try:
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    except OSError:                                # pragma: no cover
        return False
    try:
        s.bind(("::1", 0))
        return True
    except OSError:                                # pragma: no cover
        return False
    finally:
        s.close()


@unittest.skipUnless(_hay_loopback_ipv6(), "esta máquina no tiene loopback IPv6")
class ApiServidorIPv6(unittest.TestCase):
    """`Servidor.__init__`: `::1` necesita `AF_INET6`. Objetivo: 367.

    **El guarda se decide ANTES y por sondeo**, no capturando el `OSError` de
    `construir`: un `skipTest` dentro de la prueba la haría verde con el
    arreglo y sin él, que es la trampa 116 —un control que no discrimina no es
    un control—. Aquí, si se quita la línea que cambia la familia de socket, el
    `bind` falla y la prueba se pone ROJA en vez de saltarse.
    """

    def test_una_direccion_con_dos_puntos_cambia_la_familia_de_socket(self):
        srv = _api.construir(fx_de(None), host="::1", puerto=0)
        try:
            self.assertEqual(srv.address_family, socket.AF_INET6)
            self.assertEqual(srv.host_declarado, "::1")
        finally:
            srv.server_close()


class ApiArranque(unittest.TestCase):
    """`api.main`. Objetivo: 405-432.

    El bucle **no se mata desde fuera con un tope alrededor** (trampa 52: un
    `subprocess.run(timeout=…)` mata al cliente y deja el proceso vivo). Se
    corre `main` en un hilo, se le quita el servidor por el mismo sitio por el
    que lo construye y se le pide `shutdown()`: el tope está DENTRO.
    """

    def _main_en_un_hilo(self, argv):
        """Lanza `api.main(argv)` y devuelve (hilo, servidor, out, err)."""
        capturado = {}
        real = _api.construir

        def construir_espia(*a, **kw):
            srv = real(*a, **kw)
            capturado["srv"] = srv
            capturado["listo"].set()
            return srv

        capturado["listo"] = threading.Event()
        capturado["rc"] = None
        out, err = io.StringIO(), io.StringIO()

        def correr():
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                capturado["rc"] = _api.main(argv)

        with mock.patch.object(_api, "construir", construir_espia):
            hilo = threading.Thread(target=correr, daemon=True)
            hilo.start()
            self.assertTrue(capturado["listo"].wait(120),
                            "main no llegó a construir el servidor")
        return hilo, capturado, out, err

    def test_arranca_sirve_y_se_para_devolviendo_0(self):
        hilo, cap, out, err = self._main_en_un_hilo(
            ["--host", "127.0.0.1", "--puerto", "0"])
        srv = cap["srv"]
        puerto = srv.server_address[1]
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{puerto}/salud", timeout=30) as r:
                self.assertEqual(r.status, 200)
        finally:
            srv.shutdown()
            hilo.join(timeout=30)
        self.assertFalse(hilo.is_alive())
        self.assertEqual(cap["rc"], 0)
        self.assertIn("filex-api en http://127.0.0.1:0", err.getvalue())
        self.assertIn("aviso: sin --raiz no hay lista blanca", err.getvalue())

    def test_un_control_c_para_el_servidor_y_tambien_devuelve_0(self):
        """`KeyboardInterrupt` durante el `join` es la parada normal de un
        servidor de línea de órdenes. Se inyecta sustituyendo `threading` en el
        módulo por un `Thread` que arranca de verdad y cuyo `join` interrumpe:
        el `shutdown()` de después necesita un `serve_forever` VIVO o se
        quedaría esperando su propio evento para siempre."""
        arrancado = threading.Event()

        class _HiloQueInterrumpe:
            def __init__(self, target=None, daemon=None):
                self._h = threading.Thread(target=target, daemon=True)

            def start(self):
                self._h.start()
                arrancado.set()

            def join(self, *a, **kw):
                time.sleep(0.05)
                raise KeyboardInterrupt

        falso = type("T", (), {"Thread": _HiloQueInterrumpe})
        with mock.patch.object(_api, "threading", falso):
            hilo, cap, out, err = self._main_en_un_hilo(
                ["--host", "127.0.0.1", "--puerto", "0"])
            hilo.join(timeout=60)
        self.assertTrue(arrancado.is_set())
        self.assertFalse(hilo.is_alive())
        self.assertEqual(cap["rc"], 0)

    def test_una_raiz_que_no_confina_impide_arrancar_con_rc_2(self):
        with _salidas() as (_, err):
            rc = _api.main(["--raiz", "", "--puerto", "0"])
        self.assertEqual(rc, 2)
        self.assertIn("no se puede arrancar", err.getvalue())

    def test_con_permitir_red_avisa_por_stderr_antes_de_abrir_el_puerto(self):
        """*Cualquiera que llegue a este puerto puede convertir dentro de las
        raíces permitidas.* El aviso tiene que salir ANTES del `construir`, y
        eso se comprueba haciendo que `construir` reviente: si el aviso
        estuviera después, no se vería.

        Así no se abre ni un socket fuera de loopback, que en una máquina con
        seis agentes trabajando no es un detalle.
        """
        class _Adrede(Exception):
            pass

        def no_construyas(*a, **kw):
            raise _Adrede

        with mock.patch.object(_api, "construir", no_construyas):
            with _salidas() as (_, err), self.assertRaises(_Adrede):
                _api.main(["--host", "0.0.0.0", "--puerto", "0", "--permitir-red",
                           "--raiz", RAIZ])
        texto = err.getvalue()
        self.assertIn("AVISO: escuchando en 0.0.0.0", texto)
        self.assertNotIn("sin --raiz", texto)          # aquí sí se declaró raíz


# ===========================================================================
#  filex/watcher.py — las piezas
# ===========================================================================


class WatcherMemoria(unittest.TestCase):
    """`Memoria`. Objetivo: 165-166, 172, 183-184."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="filex-cob-mem-")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _huella(self, nombre="a.png"):
        return Huella(os.path.join(self.dir, nombre), 10, 20)

    def test_una_memoria_corrupta_arranca_vacia_en_vez_de_reventar(self):
        """Sin esto, un JSON a medias en disco impide arrancar el watcher — y
        el JSON a medias es exactamente lo que deja un `taskkill` (trampa 47)."""
        f = os.path.join(self.dir, "mem.json")
        for basura in ('{"atendidas": [', "no soy json", ""):
            with self.subTest(basura=basura):
                with open(f, "w", encoding="utf-8") as fh:
                    fh.write(basura)
                m = Memoria(f)
                self.assertEqual(len(m), 0)
                self.assertNotIn(self._huella(), m)

    def test_la_memoria_cuenta_lo_que_recuerda_y_persiste(self):
        f = os.path.join(self.dir, "mem2.json")
        m = Memoria(f)
        self.assertEqual(len(m), 0)
        m.marcar(self._huella())
        m.marcar(self._huella("b.png"))
        m.marcar(self._huella())                      # idempotente: es un conjunto
        self.assertEqual(len(m), 2)
        self.assertEqual(len(Memoria(f)), 2)

    def test_si_el_disco_no_deja_escribir_la_memoria_sigue_en_RAM(self):
        """*El disco no manda aquí*: perder la persistencia degrada a
        «reconvertir tras un reinicio», no a caerse."""
        f = os.path.join(self.dir, "no-existe-este-dir", "mem.json")
        m = Memoria(f)
        m.marcar(self._huella())
        self.assertEqual(len(m), 1)
        self.assertIn(self._huella(), m)
        self.assertFalse(os.path.exists(f))


class WatcherCoherencia(unittest.TestCase):
    """`_coherencia_declarada`. Objetivo: 346-349 y 362-363.

    N5, `bench/watcher-y-desechables.md` §2: lo que salva a un fichero
    truncado no es su suma de comprobación, es que su longitud esté DECLARADA.
    """

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="filex-cob-coh-")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _escribir(self, nombre, datos):
        r = os.path.join(self.dir, nombre)
        with open(r, "wb") as fh:
            fh.write(datos)
        return r

    def test_un_fichero_que_ya_no_esta_no_es_asunto_de_esta_defensa(self):
        r = os.path.join(self.dir, "fantasma.wav")
        self.assertEqual(_watch._coherencia_declarada(r), "sin_declaracion")

    def test_un_fichero_mas_corto_que_una_cabecera_esta_incompleto(self):
        """Menos de 12 bytes no da ni para mirar: no hay cabecera que leer."""
        for n in (0, 1, 11):
            with self.subTest(n=n):
                r = self._escribir(f"corto{n}.wav", b"R" * n)
                self.assertEqual(_watch._coherencia_declarada(r), "incompleto")
        # 12 bytes justos y coherentes: `4 + 8 == 12`, así que ya no es corto.
        r = self._escribir("justo.wav", b"RIFF" + (4).to_bytes(4, "little") + b"WAVE")
        self.assertEqual(_watch._coherencia_declarada(r), "completo")

    def test_un_png_que_desaparece_entre_la_cabecera_y_la_cola_no_revienta(self):
        """La cola de un PNG se lee en una SEGUNDA apertura, y entre las dos
        cabe que el fichero se vaya. Se responde `sin_declaracion`, que no es
        un aprobado — decirlo es mejor que fingir que sí o que no.

        Se inyecta poniendo un `open` en el espacio de nombres del módulo, que
        tapa al de `builtins` sólo mientras dura la prueba.
        """
        r = self._escribir("p.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 40 + b"IEND\xae\x42\x60\x82")
        self.assertEqual(_watch._coherencia_declarada(r), "completo")

        real = open
        llamadas = []

        def open_que_muere(*a, **kw):
            llamadas.append(a[0])
            if len(llamadas) > 1:
                raise OSError(2, "desapareció")
            return real(*a, **kw)

        _watch.open = open_que_muere
        try:
            self.assertEqual(_watch._coherencia_declarada(r), "sin_declaracion")
        finally:
            del _watch.open
        self.assertEqual(len(llamadas), 2)
        # Y sin la inyección vuelve a responder lo mismo que antes.
        self.assertEqual(_watch._coherencia_declarada(r), "completo")


class WatcherTenedoresPosix(unittest.TestCase):
    """`_tenedores_posix` y la mitad POSIX de `_estable_en_disco`.
    Objetivo: 231-265 y 291-296.

    **Esto es Windows**, así que `/proc` se SIMULA: `os.listdir` y `os.stat` se
    desvían **sólo** para las rutas que empiezan por `/proc` y delegan en el
    disco de verdad para todo lo demás. Los descriptores del proceso ficticio
    son ENLACES DUROS reales, así que la coincidencia por `(st_dev, st_ino)`
    —que es el algoritmo entero— no está simulada: se mide.

    Lo que sí queda fuera está declarado en el informe §5.
    """

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="filex-cob-proc-")
        self.objetivo = os.path.join(self.dir, "objetivo.bin")
        with open(self.objetivo, "wb") as fh:
            fh.write(b"x" * 32)
        self.otro = os.path.join(self.dir, "otro.bin")
        with open(self.otro, "wb") as fh:
            fh.write(b"y" * 32)
        self.fd_tenedor = os.path.join(self.dir, "fd-4242")
        self.fd_ajeno = os.path.join(self.dir, "fd-5150")
        os.makedirs(self.fd_tenedor)
        os.makedirs(self.fd_ajeno)
        try:
            os.link(self.objetivo, os.path.join(self.fd_tenedor, "3"))
            os.link(self.otro, os.path.join(self.fd_ajeno, "7"))
        except (OSError, NotImplementedError, AttributeError) as e:  # pragma: no cover
            self.skipTest(f"este sistema de ficheros no admite enlaces duros: {e}")
        self.mi_pid = os.getpid()
        self.miradas = []

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    @contextlib.contextmanager
    def _proc_simulado(self, entradas=None):
        real_listdir, real_stat = os.listdir, os.stat
        if entradas is None:
            entradas = ["1", "no-digito", str(self.mi_pid), "4242", "5150"]
        mapa_fd = {"4242": self.fd_tenedor, "5150": self.fd_ajeno}

        def listdir(p, *a, **kw):
            s = str(p).replace("\\", "/")
            if s == "/proc":
                return list(entradas)
            if s.startswith("/proc/"):
                pid = s.split("/")[2]
                self.miradas.append(pid)
                if pid == str(self.mi_pid):
                    raise AssertionError("no debe mirarse el propio pid")
                if pid not in mapa_fd:
                    raise PermissionError(13, "otro usuario")
                return real_listdir(mapa_fd[pid]) + ["fantasma"]
            return real_listdir(p, *a, **kw)

        def stat(p, *a, **kw):
            s = str(p).replace("\\", "/")
            if s.startswith("/proc/"):
                pid, hoja = s.split("/")[2], s.split("/")[-1]
                return real_stat(os.path.join(mapa_fd[pid], hoja))
            return real_stat(p, *a, **kw)

        with mock.patch.object(os, "listdir", listdir), \
                mock.patch.object(os, "stat", stat):
            yield

    def test_encuentra_al_que_tiene_el_inodo_y_solo_a_ese(self):
        with self._proc_simulado():
            tenedores = _watch._tenedores_posix(self.objetivo)
        self.assertEqual(tenedores, [4242])
        # Se miró al de al lado (y no coincidió) y NUNCA al propio proceso.
        self.assertIn("5150", self.miradas)
        self.assertNotIn(str(self.mi_pid), self.miradas)
        # `fantasma` no existe: un `fd` que muere entre el listado y el `stat`
        # se salta, no tumba el barrido.
        with self._proc_simulado():
            self.assertEqual(_watch._tenedores_posix(self.otro), [5150])

    def test_un_proceso_ajeno_ilegible_no_finge_una_respuesta(self):
        """*51 de 96 `/proc/<pid>/fd` son legibles*: un escritor de otro
        usuario es invisible, y la defensa POSIX es estrictamente más débil que
        la de Windows, no equivalente. Se salta el pid, no se aborta."""
        with self._proc_simulado(entradas=["1", "4242"]):
            self.assertEqual(_watch._tenedores_posix(self.objetivo), [4242])
        self.assertIn("1", self.miradas)

    def test_sin_proc_no_hay_defensa_que_dar_y_se_dice_None(self):
        """En Windows `os.listdir('/proc')` no encuentra nada: la respuesta es
        `None` («no se pudo saber»), no `[]` («no lo tiene nadie»). Las dos son
        distintas y la trampa 43 es exactamente ésa."""
        self.assertIsNone(_watch._tenedores_posix(self.objetivo))

    def test_un_fichero_que_no_esta_devuelve_None_no_una_lista_vacia(self):
        self.assertIsNone(_watch._tenedores_posix(os.path.join(self.dir, "no.bin")))

    def test_la_variable_de_apagado_devuelve_None_sin_mirar_el_disco(self):
        viejo = os.environ.get(_watch._VAR_PROC)
        os.environ[_watch._VAR_PROC] = "0"
        try:
            with self._proc_simulado():
                self.assertIsNone(_watch._tenedores_posix(self.objetivo))
            self.assertEqual(self.miradas, [])
        finally:
            if viejo is None:
                os.environ.pop(_watch._VAR_PROC, None)
            else:
                os.environ[_watch._VAR_PROC] = viejo

    def test_un_sistema_de_ficheros_sin_identidad_no_se_puede_sondear(self):
        """Sin `st_ino` no hay con qué comparar. Se devuelve `None`, que otra
        vez es «no se pudo», no «está libre».

        Se mide **con el `/proc` simulado delante**: sin él la respuesta sería
        `None` de todas formas —porque no hay `/proc`— y la prueba pasaría con
        el guarda y sin él (trampa 116). Con él, quitarlo devuelve `[4242]`.
        """
        real_stat = os.stat

        def stat_sin_inodo(p, *a, **kw):
            s = real_stat(p, *a, **kw)
            campos = list(s)
            campos[1] = 0                             # st_ino
            return os.stat_result(campos)

        with self._proc_simulado():
            self.assertEqual(_watch._tenedores_posix(self.objetivo), [4242])
            with mock.patch.object(os, "stat", stat_sin_inodo):
                self.assertIsNone(_watch._tenedores_posix(self.objetivo))

    def test_en_posix_el_cerrojo_pregunta_a_proc_y_no_a_os_replace(self):
        """`os.replace(p,p)` da `libre` en los cinco estados en POSIX —está
        MEDIDO—, así que ahí el primitivo es otro. Con un tenedor a la vista el
        fichero NO está estable; sin `/proc`, la respuesta cae a la
        estabilidad de `stat`, que es lo que había."""
        with mock.patch.object(os, "name", "posix"):
            with self._proc_simulado():
                self.assertFalse(_watch._estable_en_disco(self.objetivo))
            with self._proc_simulado(entradas=["1"]):
                self.assertTrue(_watch._estable_en_disco(self.objetivo))
            # Sin `/proc` en absoluto: `None` -> `True`, y no se inventa nada.
            self.assertTrue(_watch._estable_en_disco(self.objetivo))


@unittest.skipUnless(HAY_CORPUS, _SIN_CORPUS)
class WatcherSondeo(unittest.TestCase):
    """`comprobar_raices`, `_candidatos`, `maduros` y `correr`.
    Objetivo: 432-435, 454-460, 495-496, 615-626."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="filex-cob-son-")
        self.ent = os.path.join(self.dir, "entrada")
        self.sal = os.path.join(self.dir, "salida")
        os.makedirs(self.ent)
        os.makedirs(self.sal)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _vigilante(self, fx=None, **kw):
        return Vigilante(fx if fx is not None else fx_de([self.dir]),
                         [self.ent], self.sal, "webp", intervalo=0, **kw)

    def test_sin_confinamiento_no_hay_raices_que_comprobar(self):
        v = self._vigilante(fx=fx_de(None))
        self.assertIsNone(v.fx.confinamiento)
        v.comprobar_raices()                     # no lanza: no hay lista blanca

    def test_con_lista_blanca_se_valida_tambien_el_DIRECTORIO_DE_SALIDA(self):
        """No es una copia de la validación: es una llamada a la que hay. Y
        mira los dos lados — un watcher que sólo validara lo vigilado
        escribiría fuera de la lista blanca sin enterarse."""
        self._vigilante().comprobar_raices()     # vigilado y salida dentro: pasa

        v = Vigilante(fx_de([self.ent]), [self.ent], self.sal, "webp")
        with self.assertRaises(Denegado):
            v.comprobar_raices()                 # la SALIDA queda fuera

    def test_el_filtro_de_extension_pregunta_al_grafo_y_salta_lo_que_no_lleva_a_nada(self):
        v = self._vigilante()
        shutil.copy2(PNG, os.path.join(self.ent, "si.png"))
        for nombre in ("no.xyzzy", "sin-extension", "ya.webp"):
            with open(os.path.join(self.ent, nombre), "wb") as fh:
                fh.write(b"0" * 64)
        nombres = sorted(os.path.basename(h.ruta) for h in v._candidatos())
        self.assertEqual(nombres, ["si.png"])

    def test_sin_recursivo_no_se_baja_a_los_subdirectorios_y_con_el_si(self):
        """Un `os.walk` sin `--recursivo` se corta tras el primer nivel. Es la
        diferencia entre vigilar una bandeja de entrada y vigilar un árbol."""
        hondo = os.path.join(self.ent, "sub", "mas")
        os.makedirs(hondo)
        shutil.copy2(PNG, os.path.join(self.ent, "arriba.png"))
        shutil.copy2(PNG, os.path.join(hondo, "abajo.png"))

        llano = sorted(os.path.basename(h.ruta)
                       for h in self._vigilante()._candidatos())
        self.assertEqual(llano, ["arriba.png"])

        hondos = sorted(os.path.basename(h.ruta)
                        for h in self._vigilante(recursivo=True)._candidatos())
        self.assertEqual(hondos, ["abajo.png", "arriba.png"])

    def test_un_fichero_que_desaparece_entre_el_listado_y_el_stat_se_salta(self):
        """El `scandir` y el `stat` no son atómicos. Sin el `except OSError` el
        sondeo entero se cae por un fichero temporal que ya no está."""
        v = self._vigilante()
        shutil.copy2(PNG, os.path.join(self.ent, "vivo.png"))
        muerto = os.path.join(self.ent, "muerto.png")
        shutil.copy2(PNG, muerto)
        real_stat = os.stat

        def stat_que_pierde_uno(p, *a, **kw):
            if str(p) == muerto:
                raise FileNotFoundError(2, "desapareció entre medias")
            return real_stat(p, *a, **kw)

        with mock.patch.object(os, "stat", stat_que_pierde_uno):
            nombres = sorted(os.path.basename(h.ruta) for h in v._candidatos())
        self.assertEqual(nombres, ["vivo.png"])

    @unittest.skipUnless(ES_WINDOWS, "el cerrojo por `os.replace` es de Windows")
    def test_un_fichero_abierto_por_otro_se_aplaza_y_no_se_descarta(self):
        """Trampa 27: *«si puedo abrirlo, está completo» es FALSO*. Y trampa
        33: `os.replace(p,p)` no dice «alguien lo escribe», dice «alguien lo
        tiene ABIERTO» — con un LECTOR basta."""
        v = self._vigilante(estables=1)
        ruta = os.path.join(self.ent, "abierto.png")
        shutil.copy2(PNG, ruta)
        with open(ruta, "rb"):
            self.assertEqual(v.maduros(), [])
            self.assertEqual(v.contadores["aplazados_abiertos"], 1)
        # Cerrado el lector, el mismo fichero madura sin volver a empezar.
        maduros = v.maduros()
        self.assertEqual([os.path.basename(h.ruta) for h in maduros], ["abierto.png"])
        self.assertEqual(v.contadores["aplazados_abiertos"], 1)

    def test_el_bucle_para_por_ciclos_y_por_tiempo_y_no_de_otra_forma(self):
        """*«Hasta que lo maten» no es un tope*: los dos son explícitos."""
        v = self._vigilante(estables=99)          # nada madura: sólo se cuenta
        v.correr(ciclos=3)
        self.assertEqual(v.contadores["vistos"], 0)
        pasos = []
        v.paso = lambda: pasos.append(1) or []
        v.correr(ciclos=2)
        self.assertEqual(len(pasos), 2)
        pasos.clear()
        v.correr(hasta=0.001)
        self.assertGreaterEqual(len(pasos), 1)

        # `al_atender` es opcional: sin él el bucle sigue atendiendo y sólo
        # deja de informar. Un `correr` que exigiera la llamada de vuelta
        # obligaría a toda superficie a inventarse una.
        atendidos = [Atendido(entrada="a.png", salida="b.webp",
                              estado="convertido")]
        v.paso = lambda: atendidos
        v.correr(ciclos=1)                        # sin al_atender: no revienta


class WatcherAtender(unittest.TestCase):
    """`atender` y `_linea`. Objetivo: 568-580 y 633-639."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="filex-cob-at-")
        self.sal = os.path.join(self.dir, "salida")
        os.makedirs(self.sal)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_una_denegacion_del_nucleo_no_sale_por_la_superficie_como_traza(self):
        """*Una superficie que revienta con una traza es una superficie que
        filtra.* El watcher captura `Denegado` y devuelve el mismo mensaje
        opaco de R4 — y marca la entrada, para no reintentarla para siempre."""
        fx = _FxDePapel(conversion=Denegado())
        v = Vigilante(fx, [self.dir], self.sal, "webp",
                      trabajos=Trabajos(os.path.join(self.dir, "_t")))
        h = Huella(os.path.join(self.dir, "x.png"), 10, 20)
        r = v.atender(h)
        self.assertEqual(r.estado, "denegado")
        self.assertEqual(r.motivo, "ruta no accesible")
        self.assertEqual(v.contadores["fallidos"], 1)
        self.assertIn(h, v.memoria)
        # Y el trabajo queda cerrado como fallido, no colgado en `working`.
        t = v.trabajos.get(r.job_id)
        self.assertIsNotNone(t)

    def test_la_linea_humana_dice_el_punto_5_y_los_ficheros_no_declarados(self):
        r = Atendido(entrada="a.png", salida="b.webp", estado="convertido",
                     veredicto="ok", ms=214.6,
                     cobertura={"5_escritura": True})
        self.assertIn("punto5=sí", _watch._linea(r))
        self.assertIn("[convertido] b.webp  [ok]  215 ms", _watch._linea(r))

        r.cobertura = {"5_escritura": False}
        self.assertIn("punto5=NO", _watch._linea(r))

        r.sobrantes = {"init.mp4": 3, "chunk-0.m4s": 4}
        linea = _watch._linea(r)
        self.assertIn("no declarados: chunk-0.m4s, init.mp4", linea)

    def test_la_linea_de_lo_que_no_se_convirtio_nombra_la_ENTRADA(self):
        """En un fallo la salida no existe: nombrarla sería nombrar un fichero
        que no está."""
        for estado in ("fallido", "saltado", "denegado"):
            r = Atendido(entrada="a.png", salida="b.webp", estado=estado,
                         motivo="el destino ya existe")
            self.assertEqual(_watch._linea(r),
                             f"[{estado}] a.png — el destino ya existe")


@unittest.skipUnless(HAY_CORPUS, _SIN_CORPUS)
@unittest.skipUnless(HAY_IMAGEMAGICK, _SIN_IM)
class WatcherArranque(unittest.TestCase):
    """`watcher.main`. Objetivo: 647-734.

    El bucle tiene su tope DENTRO de la orden (`--ciclos`), que es lo que
    permite probarlo sin un proceso hijo al que luego habría que matar por un
    PID que en Windows no es el suyo (trampas 52 y 93).
    """

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="filex-cob-watch-")
        self.ent = os.path.join(self.dir, "entrada")
        self.sal = os.path.join(self.dir, "salida")
        os.makedirs(self.ent)
        self.cwd = os.getcwd()
        self.antes_cwd = set(os.listdir(self.cwd))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)
        nuevos = set(os.listdir(self.cwd)) - self.antes_cwd
        self.assertEqual(nuevos, set(),
                         f"el motor escribió fuera del destino, en el cwd: {nuevos}")

    def _base(self, *extra):
        return ["--vigilar", self.ent, "--salida", self.sal, "--destino", "webp",
                "--raiz", self.dir, "--ciclos", "1", "--estables", "1",
                "--intervalo", "0", *extra]

    def test_el_directorio_de_salida_lo_crea_MAIN_aunque_no_haya_nada_que_convertir(self):
        """**Refutación de mi propia primera prueba, y sale del control de
        discriminación.** La versión inicial comprobaba que el directorio
        existía DESPUÉS de convertir, y pasaba también con el `os.makedirs`
        borrado: **lo crea el núcleo al mover la salida**. Así que aquella
        aserción no medía la línea que decía medir (trampa 116).

        Lo que la línea sí garantiza —y sólo se ve con la carpeta vigilada
        VACÍA— es que un watcher arrancado antes de que llegue el primer
        fichero deja el destino listo en vez de esperar a tener suerte.
        """
        self.assertFalse(os.path.isdir(self.sal))
        with _salidas():
            rc = _watch.main(self._base())
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isdir(self.sal),
                        "main tiene que crear el destino aunque no convierta nada")

    def test_un_ciclo_convierte_y_lo_cuenta(self):
        shutil.copy2(PNG, os.path.join(self.ent, "tipico.png"))
        with _salidas() as (out, err):
            rc = _watch.main(self._base("--memoria",
                                        os.path.join(self.dir, "mem.json")))
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(os.path.join(self.sal, "tipico.webp")))
        self.assertIn("[convertido]", out.getvalue())
        self.assertIn("punto5=", out.getvalue())
        self.assertNotIn("sin --raiz", err.getvalue())
        # La memoria persiste: un segundo arranque no reconvierte.
        self.assertTrue(os.path.isfile(os.path.join(self.dir, "mem.json")))

    def test_con_json_cada_fichero_es_una_linea_de_json_con_su_asa(self):
        shutil.copy2(PNG, os.path.join(self.ent, "otro.png"))
        with _salidas() as (out, _):
            rc = _watch.main(self._base("--json", "--conservar-extension"))
        self.assertEqual(rc, 0)
        lineas = [l for l in out.getvalue().splitlines() if l.strip()]
        self.assertEqual(len(lineas), 1)
        d = json.loads(lineas[0])
        self.assertEqual(d["estado"], "convertido")
        self.assertTrue(d["job_id"])
        self.assertTrue(d["cobertura"]["5_escritura"])
        # `--conservar-extension`: feo, pero no colisiona.
        self.assertTrue(d["salida"].endswith("otro.png.webp"))

    def test_una_entrada_rota_se_informa_como_fallida_y_el_bucle_sigue(self):
        with open(os.path.join(self.ent, "roto.png"), "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 40 + b"IEND\xae\x42\x60\x82")
        with _salidas() as (out, _):
            rc = _watch.main(self._base("--sin-coherencia"))
        self.assertEqual(rc, 0)
        self.assertIn("[fallido]", out.getvalue())

    def test_vigilar_fuera_de_la_lista_blanca_es_rc_2_con_el_mensaje_opaco(self):
        """R4: el mismo mensaje que para «no existe». Un watcher que dijera
        «esa carpeta no existe» sería un mapa del disco ajeno."""
        otro = tempfile.mkdtemp(prefix="filex-cob-fuera-")
        try:
            with _salidas() as (_, err):
                rc = _watch.main(["--vigilar", otro, "--salida", self.sal,
                                  "--destino", "webp", "--raiz", self.dir,
                                  "--ciclos", "1"])
            self.assertEqual(rc, 2)
            self.assertNotIn(otro, err.getvalue())     # no dice qué carpeta era
            self.assertTrue(err.getvalue().strip())
        finally:
            shutil.rmtree(otro, ignore_errors=True)

    def test_sin_raiz_avisa_de_que_no_hay_lista_blanca(self):
        with _salidas() as (_, err):
            rc = _watch.main(["--vigilar", self.ent, "--salida", self.sal,
                              "--destino", "webp", "--ciclos", "1",
                              "--intervalo", "0"])
        self.assertEqual(rc, 0)
        self.assertIn("aviso: sin --raiz no hay lista blanca", err.getvalue())

    def test_una_raiz_que_no_confina_impide_arrancar_con_rc_2(self):
        with _salidas() as (_, err):
            rc = _watch.main(["--vigilar", self.ent, "--salida", self.sal,
                              "--destino", "webp", "--raiz", "", "--ciclos", "1"])
        self.assertEqual(rc, 2)
        self.assertIn("no se puede arrancar", err.getvalue())

    def test_un_control_c_en_el_bucle_sale_limpio_con_0(self):
        """El `KeyboardInterrupt` es la forma normal de parar un watcher. Se
        inyecta sustituyendo la CLASE que `main` instancia, no el `time.sleep`
        del proceso entero: un parche global de `sleep` alcanzaría a los demás
        hilos de la tanda."""
        class _VigilanteQueSeInterrumpe(_watch.Vigilante):
            def correr(self, **kw):
                raise KeyboardInterrupt

        with mock.patch.object(_watch, "Vigilante", _VigilanteQueSeInterrumpe):
            with _salidas():
                rc = _watch.main(self._base())
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
"""Cobertura del CUARTO PUNTO del contrato y del sondeo por SUBPROCESO.

Carril `cob/contrato`. Objetivo: `filex/verificador.py`, tres funciones que
entre las tres dejaban 187 lineas sin ejecutar en la suite completa:

    sondear_subproceso   80 de 93 sin ejecutar
    main                 55 sin ejecutar (el CLI del propio verificador)
    punto4_pedido        52 de 274 sin ejecutar

Lo que estas pruebas NO hacen, porque subir el porcentaje no es el objetivo:
no hay un solo `try: f(x) except: pass`. Cada prueba se calibro rompiendo UNA
linea de la funcion objetivo y comprobando que se pone ROJA; el control esta
tabulado en `bench/cobertura-contrato.md` §3, prueba por prueba.

Dos avisos que gobiernan el diseno de este fichero:

  * **Trampa 86** -- antes de escribir la prueba que juzga una magnitud, hay
    que comprobar que la sonda la PUBLICA. `test_censo_de_claves_reales` es
    esa comprobacion y corre primero: las sondas sinteticas de este fichero
    salen de un sondeo REAL del corpus, copiado y mutado, nunca inventado.
  * **Trampa 109** -- una prueba puede pararse en una guarda anterior y no
    llegar nunca a la asercion que la justifica. Por eso cada prueba de
    `punto4_pedido` afirma sobre el `esperado`/`obtenido` CONCRETO que solo
    esa rama produce, no sobre la regla a secas; y `CuartoPuntoEnProduccion`
    recorre dos ramas por `verificar()`, que es la puerta real.
"""

import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from filex import verificador as V  # noqa: E402


# ---------------------------------------------------------------------------
# Utilidades comunes
# ---------------------------------------------------------------------------

def corpus(rel):
    return os.path.join(RAIZ, "corpus", rel)


def hay_corpus(rel, minimo=1000):
    """Trampa 107: `os.path.exists` devuelve True para un PUNTERO de Git LFS.

    Un puntero son ~130 B de texto que empiezan por 'version https://...', asi
    que un guarda por existencia deja entrar el puntero y el motor revienta con
    una excepcion sin capturar. Se comprueba el TAMANO.
    """
    p = corpus(rel)
    return os.path.exists(p) and os.path.getsize(p) >= minimo


def hay_binario(nombre):
    return shutil.which(nombre) is not None


class Desechable(unittest.TestCase):
    """Directorio de trabajo desechable por prueba (regla R18, trampa 21).

    Los motores escriben fuera del destino, en el `cwd` del proceso: `magick`
    deja `_map.shtml`, `ffmpeg` deja segmentos DASH. Se lista antes y despues
    y se borra entero.
    """

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="cob-contrato-")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def ruta(self, nombre):
        return os.path.join(self.dir, nombre)

    def escribe(self, nombre, datos):
        p = self.ruta(nombre)
        with open(p, "wb") as fh:
            fh.write(datos)
        return p


class EspiaCorrer(object):
    """Envuelve `_correr` SIN sustituirlo: el binario se ejecuta de verdad y
    ademas queda registrado el `rc` de cada celda.

    Trampa 25: una salida de 0 bytes puede ser un proceso que NO ARRANCO, y es
    indistinguible de un silencio legitimo. El `rc` es lo unico que las separa
    -- y aqui separa tres cosas, no dos: `rc>0` es el binario diciendo que no,
    `rc=-1` es un OSError (no arranco) y `rc=-9` es el timeout de `_correr`.
    """

    def __init__(self):
        self.celdas = []
        self._orig = None

    def __enter__(self):
        self._orig = V._correr

        def envoltorio(orden, timeout=V.TIMEOUT):
            rc, out, err = self._orig(orden, timeout)
            self.celdas.append({"argv0": orden[0], "rc": rc,
                                "n_out": len(out), "n_err": len(err)})
            return rc, out, err

        V._correr = envoltorio
        return self

    def __exit__(self, *a):
        V._correr = self._orig
        return False

    @property
    def rcs(self):
        return [c["rc"] for c in self.celdas]


# ===========================================================================
# 0. La comprobacion que va ANTES de todas las demas (trampa 86)
# ===========================================================================

class CensoDeClaves(unittest.TestCase):
    """Las sondas sinteticas de este fichero copian la FORMA de un sondeo real.

    `bench/bitrate-y-lock.md` §2.1 midio que quitar el filtro `tipo == audio`
    de la regla de bitrate no habria producido ni una comparacion, porque el
    dato no existe. Esta prueba es la version generica de aquel aviso: fija por
    escrito que claves publica cada sonda, para que la prueba que las juzga no
    este juzgando un `None`.
    """

    @unittest.skipUnless(hay_corpus("video/tipico.mp4", 100000)
                         and hay_binario("ffprobe"),
                         "hace falta corpus/video (git lfs checkout) y ffprobe")
    def test_el_bitrate_de_pista_solo_lo_publica_el_subproceso(self):
        proc = V.sondear(corpus("video/tipico.mp4"), "proceso")
        sub = V.sondear(corpus("video/tipico.mp4"), "subproceso")

        def bitrate_de(sonda, tipo):
            for x in sonda.get("pistas", []):
                if x.get("tipo") == tipo:
                    return x.get("bitrate_bps")
            return "SIN PISTA"

        # Reproduce la trampa 86: NINGUNA de las dos sondas publica el bitrate
        # de la pista de VIDEO, asi que la regla V10 no puede compararlo y por
        # eso el codigo se apoya en el bitrate del CONTENEDOR.
        self.assertIsNone(bitrate_de(proc, "video"))
        self.assertIsNone(bitrate_de(sub, "video"))
        # Y la mitad que si es nueva: dentro de un contenedor, el bitrate de la
        # pista de AUDIO lo publica el SUBPROCESO y no la sonda en proceso.
        # De ahi que la rama de "bitrate pedido" de punto4_pedido fuera
        # inalcanzable con el motor por defecto.
        self.assertIsNone(bitrate_de(proc, "audio"))
        self.assertIsInstance(bitrate_de(sub, "audio"), int)

    @unittest.skipUnless(hay_corpus("datos/patologico_bom.csv", 50),
                         "hace falta corpus/datos")
    def test_las_claves_de_datos_que_juzga_el_punto_4_existen(self):
        s = V.sondear(corpus("datos/patologico_bom.csv"), "proceso")
        for clave in ("filas_datos", "csv_cabecera", "bom_utf8"):
            self.assertIn(clave, s, "punto4_pedido juzga %r y la sonda no lo "
                                    "publica" % clave)
        self.assertTrue(s["bom_utf8"])


# ===========================================================================
# 1. sondear_subproceso -- la via cara, la que casi nadie ejerce
# ===========================================================================

@unittest.skipUnless(hay_binario("ffprobe") and hay_binario("magick"),
                     "hacen falta ffprobe y magick en el PATH")
class SondeoPorSubproceso(Desechable):
    """`sondear_subproceso` delega en ffprobe / magick / gswin64c.

    El proyecto la evita a proposito -- «con subprocesos, en el 38 % de los
    casos verificar cuesta mas que convertir» (`CLAUDE.md` §5) -- y por eso
    tenia 80 de sus 93 lineas sin ejecutar. Aqui NO se mide su coste: esa
    comparacion ya esta hecha y no es de este carril.
    """

    def test_av_publica_pistas_y_un_solo_proceso(self):
        if not hay_corpus("video/tipico.mp4", 100000):
            self.skipTest("hace falta corpus/video (git lfs checkout)")
        with EspiaCorrer() as e:
            d = V.sondear_subproceso(corpus("video/tipico.mp4"))
        self.assertEqual(e.rcs, [0], "ffprobe no devolvio 0: %r" % e.celdas)
        self.assertEqual(d["categoria"], "av")
        self.assertEqual(d["n_procesos"], 1)
        self.assertEqual((d["n_video"], d["n_audio"], d["n_subtitulo"]),
                         (1, 1, 0))
        self.assertEqual(d["n_pistas"], len(d["pistas"]))
        vid = [x for x in d["pistas"] if x["tipo"] == "video"][0]
        aud = [x for x in d["pistas"] if x["tipo"] == "audio"][0]
        self.assertEqual((vid["ancho"], vid["alto"]), (1920, 1080))
        self.assertEqual(vid["fps"], "30/1")          # solo lo da ffprobe
        self.assertEqual(aud["sample_rate"], 44100)
        self.assertIsInstance(aud["bitrate_bps"], int)
        self.assertAlmostEqual(d["duracion_s"], 20.0, places=3)

    def test_av_cuenta_la_pista_de_subtitulos(self):
        """La rama `elif t == "subtitle"` no la ejerce ningun fichero del
        corpus: hay que fabricar el contenedor con una pista de texto."""
        if not (hay_corpus("video/trivial.mp4", 1000) and hay_binario("ffmpeg")):
            self.skipTest("hace falta corpus/video/trivial.mp4 y ffmpeg")
        srt = self.escribe("s.srt", b"1\r\n00:00:00,000 --> 00:00:01,000\r\n"
                                    b"hola\r\n\r\n")
        dest = self.ruta("consubs.mkv")
        antes = sorted(os.listdir(self.dir))
        # El tope va DENTRO de la orden (`-t 1`), no solo alrededor: la trampa
        # 52 midio un ffmpeg que sobrevivio 9 minutos al timeout del cliente.
        r = subprocess.run(
            ["ffmpeg", "-nostdin", "-y", "-t", "1", "-i",
             corpus("video/trivial.mp4"), "-i", srt,
             "-map", "0", "-map", "1", "-c:v", "copy", "-c:a", "copy",
             "-c:s", "srt", "-t", "1", dest],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=120)
        if r.returncode != 0 or not os.path.exists(dest):
            self.skipTest("ffmpeg rc=%s: %s"
                          % (r.returncode,
                             r.stderr.decode("utf-8", "replace")[-200:]))
        with EspiaCorrer() as e:
            d = V.sondear_subproceso(dest)
        self.assertEqual(e.rcs, [0], "ffprobe no devolvio 0: %r" % e.celdas)
        self.assertGreaterEqual(d["n_subtitulo"], 1)
        self.assertIn("subtitle", [x["tipo"] for x in d["pistas"]])
        # Trampa 21: el motor no escribio nada mas en el desechable.
        self.assertEqual(sorted(os.listdir(self.dir)),
                         sorted(antes + ["consubs.mkv"]))

    def test_una_pista_que_no_es_ni_video_ni_audio_ni_subtitulo_se_cuenta_igual(self):
        """`n_pistas` no es la suma de los tres contadores: un ADJUNTO de
        Matroska (`codec_type: attachment`) entra en `pistas` y en `n_pistas` y
        no incrementa ninguno de los tres. Es la salida por el `else` implicito
        de la cadena `if/elif`, y sin ella la cadena solo se ejerce por sus
        tres ramas que casan."""
        if not (hay_corpus("video/trivial.mp4", 1000) and hay_binario("ffmpeg")):
            self.skipTest("hace falta corpus/video/trivial.mp4 y ffmpeg")
        adj = self.escribe("leeme.txt", b"un adjunto cualquiera\n")
        dest = self.ruta("conadjunto.mkv")
        r = subprocess.run(
            ["ffmpeg", "-nostdin", "-y", "-t", "1", "-i",
             corpus("video/trivial.mp4"), "-map", "0", "-c", "copy",
             "-attach", adj, "-metadata:s:t", "mimetype=text/plain",
             "-t", "1", dest],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=120)
        if r.returncode != 0 or not os.path.exists(dest):
            self.skipTest("ffmpeg rc=%s: %s"
                          % (r.returncode,
                             r.stderr.decode("utf-8", "replace")[-200:]))
        with EspiaCorrer() as e:
            d = V.sondear_subproceso(dest)
        self.assertEqual(e.rcs, [0], "%r" % e.celdas)
        tipos = [x["tipo"] for x in d["pistas"]]
        if "attachment" not in tipos:
            self.skipTest("este ffmpeg no adjunto la pista: %r" % tipos)
        self.assertEqual(d["n_pistas"], len(d["pistas"]))
        self.assertGreater(d["n_pistas"],
                           d["n_video"] + d["n_audio"] + d["n_subtitulo"])

    def test_av_roto_devuelve_el_stderr_y_no_pistas(self):
        """rc=1 es el binario diciendo que no. Que quede REGISTRADO es lo que
        separa este caso de uno en que ffprobe no hubiera arrancado."""
        p = self.escribe("roto.mp3", b"ID3\x04\x00\x00\x00\x00\x00\x00"
                                     + b"\x00" * 200)
        with EspiaCorrer() as e:
            d = V.sondear_subproceso(p)
        self.assertEqual(e.rcs, [1], "se esperaba un fallo del binario, no un "
                                     "fallo de arranque: %r" % e.celdas)
        self.assertEqual(d["categoria"], "av")
        self.assertEqual(d["n_procesos"], 1)
        self.assertIn("error", d)
        self.assertNotIn("pistas", d)
        self.assertLessEqual(len(d["error"]), 300)

    def test_imagen_publica_geometria_y_alfa(self):
        if not hay_corpus("imagen/tipico.png", 40000):
            self.skipTest("hace falta corpus/imagen (git lfs checkout)")
        with EspiaCorrer() as e:
            d = V.sondear_subproceso(corpus("imagen/tipico.png"))
        self.assertEqual(e.rcs, [0], "magick no devolvio 0: %r" % e.celdas)
        self.assertEqual(d["categoria"], "imagen")
        self.assertEqual((d["ancho"], d["alto"]), (1920, 1080))
        self.assertEqual(d["formato"], "png")
        self.assertTrue(d["tiene_alfa"])
        self.assertEqual(d["espacio_color"], "sRGB")
        self.assertEqual(d["n_imagenes"], 1)
        self.assertIn("canales_txt", d)

    def test_imagen_rota_devuelve_error_de_identify(self):
        p = self.escribe("roto.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 200)
        with EspiaCorrer() as e:
            d = V.sondear_subproceso(p)
        self.assertEqual(e.rcs, [1], "%r" % e.celdas)
        self.assertEqual(d["categoria"], "imagen")
        self.assertEqual(d["n_procesos"], 1)
        self.assertIn("error", d)
        self.assertNotIn("ancho", d)

    def test_fichero_vacio_sale_antes_de_lanzar_un_solo_proceso(self):
        p = self.escribe("vacio.png", b"")
        with EspiaCorrer() as e:
            d = V.sondear_subproceso(p)
        self.assertEqual(e.celdas, [], "un fichero de 0 bytes no debe lanzar "
                                       "ningun proceso")
        self.assertEqual(d["categoria"], "vacio")
        self.assertEqual(d["bytes"], 0)
        self.assertEqual(d["n_procesos"], 0)
        self.assertEqual(d["error"], "fichero de 0 bytes")

    def test_datos_no_lanza_binario_externo(self):
        if not hay_corpus("datos/patologico_bom.csv", 50):
            self.skipTest("hace falta corpus/datos")
        with EspiaCorrer() as e:
            d = V.sondear_subproceso(corpus("datos/patologico_bom.csv"))
        self.assertEqual(e.celdas, [], "la rama de datos no tiene binario que "
                                       "aporte nada")
        self.assertEqual(d["categoria"], "datos")
        self.assertEqual(d["n_procesos"], 0)
        self.assertEqual(d["csv_cabecera"], ["id", "nombre", "notas"])
        self.assertTrue(d["bom_utf8"])

    @unittest.skipUnless(hay_binario("gswin64c"), "hace falta gswin64c")
    def test_pdf_publica_paginas_y_caja(self):
        if not hay_corpus("pdf/trivial.pdf", 1000):
            self.skipTest("hace falta corpus/pdf")
        with EspiaCorrer() as e:
            d = V.sondear_subproceso(corpus("pdf/trivial.pdf"))
        self.assertEqual(e.rcs, [0], "%r" % e.celdas)
        self.assertEqual(d["categoria"], "pdf")
        self.assertEqual(d["n_procesos"], 1)
        self.assertEqual(d["n_paginas"], 1)
        self.assertEqual((d["ancho_pt"], d["alto_pt"]), (400.0, 300.0))

    @unittest.skipUnless(hay_binario("gswin64c"), "hace falta gswin64c")
    def test_pdf_roto_no_inventa_un_numero_de_paginas(self):
        """Ghostscript escribe en stdout ANTES de rendirse, asi que `out` no
        esta vacio y aun asi `lin[0]` no es un entero. La rama que importa es
        el `except`, que declara `n_paginas=None` en vez de un numero."""
        p = self.escribe("roto.pdf", b"%PDF-1.4\n" + b"basura" * 30)
        with EspiaCorrer() as e:
            d = V.sondear_subproceso(p)
        self.assertEqual(e.rcs, [1], "%r" % e.celdas)
        self.assertGreater(e.celdas[0]["n_out"], 0,
                           "el interes de este caso es que gs SI escribe en "
                           "stdout y aun asi no hay numero de paginas")
        self.assertEqual(d["categoria"], "pdf")
        self.assertIsNone(d["n_paginas"])
        self.assertIn("error", d)


@unittest.skipUnless(hay_binario("magick"), "hace falta magick")
class SondeoSubprocesoUnidadDePpp(Desechable):
    """Las tres respuestas del ternario de `ppp`.

    El comentario del codigo lo avisa: «%x sin %U enganna. ImageMagick devuelve
    la resolucion en la unidad del fichero, y para un PNG es PIXELES POR
    CENTIMETRO». Las tres ramas se separan con tres FORMATOS, sin tocar bytes.
    """

    def convierte(self, ext):
        if not hay_corpus("imagen/trivial.png", 100):
            self.skipTest("hace falta corpus/imagen/trivial.png")
        dest = self.ruta("x." + ext)
        r = subprocess.run(["magick", corpus("imagen/trivial.png"), dest],
                           stdin=subprocess.DEVNULL, capture_output=True,
                           timeout=120)
        if r.returncode != 0 or not os.path.exists(dest):
            self.skipTest("magick rc=%s al escribir .%s" % (r.returncode, ext))
        return dest

    def test_pixels_per_centimeter_se_convierte_a_pulgadas(self):
        d = V.sondear_subproceso(self.convierte("bmp"))
        # 28,3465 px/cm x 2,54 = 72 ppp. Sin la conversion saldria 28.
        self.assertEqual(d["ppp"], 72)

    def test_pixels_per_inch_se_toma_tal_cual(self):
        d = V.sondear_subproceso(self.convierte("tif"))
        self.assertEqual(d["ppp"], 72)

    def test_unidad_indefinida_no_inventa_un_ppp(self):
        """La tercera respuesta es `None`, y es la que salva a la regla P4 de
        comparar contra un numero fabricado."""
        d = V.sondear_subproceso(self.convierte("gif"))
        self.assertIsNone(d["ppp"])
        self.assertEqual(d["formato"], "gif")

    def test_varias_imagenes_en_un_fichero_cuentan_n_imagenes(self):
        """`n_imagenes = len(lineas)`: `identify` emite una linea por
        fotograma."""
        if not hay_corpus("imagen/trivial.png", 100):
            self.skipTest("hace falta corpus/imagen/trivial.png")
        dest = self.ruta("dos.gif")
        r = subprocess.run(["magick", corpus("imagen/trivial.png"),
                            corpus("imagen/trivial.png"), dest],
                           stdin=subprocess.DEVNULL, capture_output=True,
                           timeout=120)
        if r.returncode != 0 or not os.path.exists(dest):
            self.skipTest("magick rc=%s" % r.returncode)
        self.assertEqual(V.sondear_subproceso(dest)["n_imagenes"], 2)


@unittest.skipUnless(hay_binario("magick"), "hace falta magick")
class SondeoConAlfa(unittest.TestCase):
    """`sondear(..., alfa=True)`: la unica via del sondeo que decodifica
    pixeles, y la que rellena `alfa_no_trivial`, del que depende la regla I2."""

    def test_alfa_no_trivial_se_calcula_en_proceso(self):
        if not hay_corpus("imagen/alpha.png", 1000):
            self.skipTest("hace falta corpus/imagen/alpha.png")
        d = V.sondear(corpus("imagen/alpha.png"), "proceso", alfa=True)
        self.assertIn("alfa", d)
        self.assertIn("alfa_ms", d)
        self.assertTrue(d["alfa"]["evaluable"])
        self.assertTrue(d["alfa_no_trivial"], "alpha.png es el fichero de alfa "
                                              "REAL del corpus (trampa 1)")
        self.assertLess(d["alfa_min"], 1.0)

    def test_alfa_trivial_de_tipico_png(self):
        """Trampa 1: `tipico.png` DECLARA canal alfa y es enteramente opaco."""
        if not hay_corpus("imagen/tipico.png", 40000):
            self.skipTest("hace falta corpus/imagen/tipico.png")
        d = V.sondear(corpus("imagen/tipico.png"), "proceso", alfa=True)
        self.assertTrue(d["tiene_alfa"])
        self.assertFalse(d["alfa_no_trivial"])

    def test_jpeg_es_opaco_POR_DEFINICION_del_formato(self):
        """No es que no se pueda calcular: es que el formato no admite alfa, y
        eso es un `evaluable=True` con `alfa_min=1.0`, no un hueco."""
        if not hay_corpus("imagen/tipico.jpg", 1000):
            self.skipTest("hace falta corpus/imagen/tipico.jpg")
        d = V.sondear(corpus("imagen/tipico.jpg"), "proceso", alfa=True)
        self.assertTrue(d["alfa"]["evaluable"])
        self.assertEqual(d["alfa"]["alfa_min"], 1.0)
        self.assertFalse(d["alfa_no_trivial"])

    def test_alfa_no_evaluable_deja_el_motivo_y_no_un_valor_inventado(self):
        """La rama que separa «comprobado y correcto» de «no lo se»: en AVIF el
        plano alfa es un flujo AV1 y haria falta un decodificador de video."""
        if not hay_corpus("imagen/alpha.png", 1000):
            self.skipTest("hace falta corpus/imagen/alpha.png")
        d = tempfile.mkdtemp(prefix="cob-contrato-avif-")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        dest = os.path.join(d, "x.avif")
        r = subprocess.run(["magick", corpus("imagen/alpha.png"), dest],
                           stdin=subprocess.DEVNULL, capture_output=True,
                           timeout=180)
        if r.returncode != 0 or not os.path.exists(dest):
            self.skipTest("este magick no escribe AVIF (rc=%s)" % r.returncode)
        s = V.sondear(dest, "proceso", alfa=True)
        if s.get("firma") != "avif":
            self.skipTest("magick entrego %r con extension .avif" % s.get("firma"))
        self.assertFalse(s["alfa"]["evaluable"])
        self.assertIn("AVIF/HEIF", s["alfa_no_evaluable"])
        self.assertNotIn("alfa_min", s)


# ===========================================================================
# 2. punto4_pedido -- las ramas que DETECTAN, que eran justo las que faltaban
# ===========================================================================

class BasePunto4(unittest.TestCase):
    """Las sondas salen de un sondeo REAL, se copian y se mutan.

    Mutar el dict de salida es lo que hace una conversion mala: entregar un
    fichero cuyas propiedades no son las pedidas. Lo que NO se hace es
    inventarse la forma del dict -- de ahi `CensoDeClaves`.
    """

    @classmethod
    def setUpClass(cls):
        cls.faltan = []
        cls.real = {}
        for clave, rel in (("png", "imagen/tipico.png"),
                           ("jpg", "imagen/tipico.jpg"),
                           ("mp4", "video/tipico.mp4"),
                           ("mp3", "audio/tipico.mp3"),
                           ("wav", "audio/trivial.wav"),
                           ("pdf", "pdf/trivial.pdf"),
                           ("csv", "datos/patologico_bom.csv"),
                           ("json", "datos/tipico.json")):
            if hay_corpus(rel, 40):
                cls.real[clave] = V.sondear(corpus(rel), "proceso")
            else:
                cls.faltan.append(rel)

    def sonda(self, clave, **cambios):
        if clave not in self.real:
            self.skipTest("hace falta el corpus %r (git lfs checkout)" % clave)
        d = copy.deepcopy(self.real[clave])
        d.update(cambios)
        return d

    def reglas(self, hallazgos):
        return [(h["regla"], h["severidad"]) for h in hallazgos]

    def unico(self, hallazgos, regla, severidad):
        """Exige que la rama buscada haya producido UN hallazgo y devuelve el
        hallazgo, para poder afirmar sobre `esperado`/`obtenido`.

        Trampa 109: comprobar solo `assertTrue(hallazgos)` no demuestra que se
        llego a la rama que se dice cubrir -- podria haberla producido otra.
        """
        cand = [h for h in hallazgos
                if h["regla"] == regla and h["severidad"] == severidad]
        self.assertEqual(len(cand), 1,
                         "se esperaba exactamente un hallazgo %s/%s; hubo %r"
                         % (regla, severidad, self.reglas(hallazgos)))
        self.assertEqual(cand[0]["punto"], 4)
        return cand[0]


class Punto4Guardas(BasePunto4):

    def test_sin_entrada_el_punto_4_se_declara_no_evaluable(self):
        h = V.punto4_pedido(self.sonda("png"), None, {"destino": "png",
                                                      "params": {}})
        self.assertEqual(len(h), 1)
        self.assertEqual((h[0]["punto"], h[0]["severidad"]),
                         (4, "informativo"))
        self.assertIn("no es evaluable", h[0]["mensaje"])

    def test_una_sonda_con_error_no_produce_ni_un_hallazgo(self):
        """No es lo mismo «comprobado y correcto» que «no lo se»: con una sonda
        rota, el punto 4 se calla en vez de juzgar sobre datos ausentes.

        La sonda rota lleva ADEMAS una geometria distinta, que sin la guarda
        producirIa un `I1/V7 fallo`. Sin eso la prueba seria VACUA -- pasaria
        con la guarda y sin ella --, y asi lo delato el control de
        discriminacion (M30 en `bench/salidas-cobertura-contrato/`): la primera
        version usaba dos sondas identicas y no habia hallazgo que suprimir.
        """
        pedido = {"destino": "png", "params": {}}
        sana = self.sonda("png")
        rota = self.sonda("png", ancho=800, alto=450,
                          error="identify: bad header")
        # control positivo: sin el campo `error`, esa misma sonda SI dispara
        testigo = self.sonda("png", ancho=800, alto=450)
        self.assertTrue([x for x in V.punto4_pedido(testigo, sana, pedido)
                         if x["severidad"] == "fallo"])
        self.assertEqual(V.punto4_pedido(rota, sana, pedido), [])
        # y en el otro sentido: la rota es la ENTRADA
        self.assertEqual(V.punto4_pedido(testigo, rota, pedido), [])


class Punto4Geometria(BasePunto4):
    """El fallo emblematico: image-worker-mcp entregaba 800x450 con barras
    negras donde le habian pedido conservar 1920x1080."""

    def test_redimensionado_no_solicitado(self):
        sal = self.sonda("png", ancho=800, alto=450)
        h = self.unico(V.punto4_pedido(sal, self.sonda("png"),
                                       {"destino": "png", "params": {}}),
                       "I1/V7", "fallo")
        self.assertEqual((h["esperado"], h["obtenido"]), ("1920x1080", "800x450"))
        self.assertIn("REDIMENSIONADO NO SOLICITADO", h["mensaje"])

    def test_un_redimensionado_PEDIDO_no_es_un_fallo(self):
        """Control negativo de la rama anterior: la MISMA salida deja de ser un
        fallo en cuanto el pedido la explica. Sin esta celda, la de arriba no
        demuestra que la regla mire el pedido."""
        sal = self.sonda("png", ancho=800, alto=450)
        h = V.punto4_pedido(sal, self.sonda("png"),
                            {"destino": "png",
                             "params": {"ancho": 800, "alto": 450}})
        self.assertEqual([x for x in h if x["severidad"] == "fallo"], [])

    def test_dimensiones_distintas_de_las_pedidas(self):
        sal = self.sonda("png", ancho=799, alto=450)
        h = self.unico(V.punto4_pedido(sal, self.sonda("png"),
                                       {"destino": "png",
                                        "params": {"ancho": 800, "alto": 450}}),
                       "I1", "fallo")
        self.assertEqual((h["esperado"], h["obtenido"]), ("800x450", "799x450"))

    def test_alto_distinto_del_pedido_con_ancho_correcto(self):
        """La segunda mitad del `or`: el ancho cuadra y el alto no. Trampa 118
        -- un `or` se desmonta ENTERO o no se ha desmontado."""
        sal = self.sonda("png", ancho=800, alto=451)
        h = self.unico(V.punto4_pedido(sal, self.sonda("png"),
                                       {"destino": "png",
                                        "params": {"ancho": 800, "alto": 450}}),
                       "I1", "fallo")
        self.assertEqual(h["obtenido"], "800x451")

    def test_la_relacion_de_aspecto_delata_las_barras_anadidas(self):
        """El lienzo cambia de forma sin que se haya pedido nada: es el indicio
        de que el motor ha metido barras."""
        sal = self.sonda("png", ancho=1920, alto=1440)
        hs = V.punto4_pedido(sal, self.sonda("png"),
                             {"destino": "png", "params": {}})
        h = self.unico(hs, "I1", "aviso")
        self.assertIn("relacion de aspecto", h["mensaje"])
        self.assertEqual(h["esperado"], round(1920 / 1080, 3))
        self.assertEqual(h["obtenido"], round(1920 / 1440, 3))

    def test_la_geometria_de_una_pista_de_video_tambien_cuenta(self):
        """`dims()` mira `ancho` y, si no lo hay, la primera pista de video.
        Sin esta celda la funcion `dims` solo se ejerce por su primera rama."""
        sal = copy.deepcopy(self.real.get("mp4") or {})
        if not sal:
            self.skipTest("hace falta corpus/video/tipico.mp4")
        for x in sal["pistas"]:
            if x["tipo"] == "video":
                x["ancho"], x["alto"] = 1280, 720
        h = self.unico(V.punto4_pedido(sal, self.sonda("mp4"),
                                       {"destino": "mp4", "params": {}}),
                       "I1/V7", "fallo")
        self.assertEqual((h["esperado"], h["obtenido"]),
                         ("1920x1080", "1280x720"))


class Punto4Densidad(BasePunto4):

    def test_ppp_distinto_del_pedido(self):
        sal = self.sonda("png", ppp=96)
        h = self.unico(V.punto4_pedido(sal, self.sonda("png"),
                                       {"destino": "png",
                                        "params": {"dpi": 150}}),
                       "P4", "fallo")
        self.assertEqual((h["esperado"], h["obtenido"]), (150, 96))

    def test_un_ppp_dentro_de_la_tolerancia_de_1_no_es_fallo(self):
        sal = self.sonda("png", ppp=151)
        hs = V.punto4_pedido(sal, self.sonda("png"),
                             {"destino": "png", "params": {"dpi": 150}})
        self.assertEqual([x for x in hs if x["regla"] == "P4"], [])

    def test_pdf_a_imagen_la_resolucion_debe_seguir_al_ppp_pedido(self):
        """400 pt a 150 ppp son 833 px. Si el motor entrega otra cosa, la
        conversion no respeto la densidad aunque el PNG sea impecable."""
        ent = self.sonda("pdf")
        sal = self.sonda("png", ancho=600, alto=450)
        h = self.unico(V.punto4_pedido(sal, ent,
                                       {"destino": "png",
                                        "params": {"dpi": 150}}),
                       "P4", "fallo")
        self.assertEqual(h["esperado"], round(400.0 * 150 / 72.0))
        self.assertEqual(h["obtenido"], 600)

    def test_pdf_a_imagen_con_la_resolucion_correcta_no_avisa(self):
        ent = self.sonda("pdf")
        esperado = round(400.0 * 150 / 72.0)
        sal = self.sonda("png", ancho=esperado, alto=625)
        hs = V.punto4_pedido(sal, ent,
                             {"destino": "png", "params": {"dpi": 150}})
        self.assertEqual([x for x in hs if x["regla"] == "P4"], [])


class Punto4Profundidad(BasePunto4):

    def test_degradacion_de_profundidad_no_pedida_ni_inevitable(self):
        """PNG admite 16 bits: bajar a 8 sin pedirlo no es perdida inevitable."""
        sal = self.sonda("png", profundidad_bits=8)
        h = self.unico(V.punto4_pedido(sal, self.sonda("png"),
                                       {"destino": "png", "params": {}}),
                       "I4", "fallo")
        self.assertEqual((h["esperado"], h["obtenido"]), (16, 8))

    def test_la_misma_bajada_hacia_jpeg_es_perdida_INEVITABLE(self):
        """Trampa 53 en miniatura: la severidad la decide el DESTINO, no el
        cambio. El mismo 16 -> 8 es `fallo` hacia PNG e `informativo` hacia
        JPEG, cuyo techo son 8 bits."""
        sal = self.sonda("jpg", profundidad_bits=8)
        h = self.unico(V.punto4_pedido(sal, self.sonda("png"),
                                       {"destino": "jpeg", "params": {}}),
                       "I5", "informativo")
        self.assertEqual((h["esperado"], h["obtenido"]), (16, 8))
        self.assertIn("techo 8 bits", h["mensaje"])

    def test_una_profundidad_pedida_explicitamente_no_produce_hallazgo(self):
        sal = self.sonda("png", profundidad_bits=8)
        hs = V.punto4_pedido(sal, self.sonda("png"),
                             {"destino": "png",
                              "params": {"profundidad_bits": 8}})
        self.assertEqual([x for x in hs if x["regla"] in ("I4", "I5")], [])

    def test_profundidad_INFLADA_en_audio_sin_perdida(self):
        """Al reves que en imagen: subir de 16 a 24 bits no anade informacion.
        Solo se avisa si el codec de destino es sin perdida -- la 'BitDepth'
        que Matroska escribe para un AAC es 32 y no significa nada."""
        ent = self.sonda("wav")
        sal = copy.deepcopy(self.real.get("wav") or {})
        if not sal:
            self.skipTest("hace falta corpus/audio/trivial.wav")
        for x in sal["pistas"]:
            x["profundidad_bits"] = 24
            x["codec"] = "flac"
        sal["profundidad_bits"] = 24
        h = self.unico(V.punto4_pedido(sal, ent,
                                       {"destino": "flac", "params": {}}),
                       "A6", "aviso")
        self.assertEqual((h["esperado"], h["obtenido"]), (16, 24))


class Punto4Alfa(BasePunto4):

    def test_se_pierde_un_alfa_NO_TRIVIAL_en_un_destino_que_lo_admite(self):
        ent = self.sonda("png", tiene_alfa=True, alfa_no_trivial=True)
        sal = self.sonda("png", tiene_alfa=False)
        h = self.unico(V.punto4_pedido(sal, ent,
                                       {"destino": "webp", "params": {}}),
                       "I2", "fallo")
        self.assertIn("NO TRIVIAL", h["mensaje"])

    def test_hacia_jpeg_la_misma_perdida_es_inevitable(self):
        ent = self.sonda("png", tiene_alfa=True, alfa_no_trivial=True)
        sal = self.sonda("jpg", tiene_alfa=False)
        h = self.unico(V.punto4_pedido(sal, ent,
                                       {"destino": "jpg", "params": {}}),
                       "I2", "informativo")
        self.assertIn("no admite alfa", h["mensaje"])

    def test_un_alfa_TRIVIAL_perdido_no_es_hallazgo(self):
        """Trampa 1: `tipico.png` declara alfa y es enteramente opaco. Sin esta
        celda, la regla I2 pareceria disparar por `tiene_alfa` a secas."""
        ent = self.sonda("png", tiene_alfa=True, alfa_no_trivial=False)
        sal = self.sonda("png", tiene_alfa=False)
        hs = V.punto4_pedido(sal, ent, {"destino": "webp", "params": {}})
        self.assertEqual([x for x in hs if x["regla"] == "I2"], [])

    def test_sin_min_alfa_calculado_la_regla_se_declara_NO_EVALUABLE(self):
        """La diferencia entre «comprobado y correcto» y «no lo se»."""
        ent = self.sonda("png", tiene_alfa=True,
                         alfa_no_evaluable="formato no cubierto")
        ent.pop("alfa_no_trivial", None)
        sal = self.sonda("png", tiene_alfa=False)
        h = self.unico(V.punto4_pedido(sal, ent,
                                       {"destino": "webp", "params": {}}),
                       "I2", "informativo")
        self.assertEqual(h["obtenido"], "formato no cubierto")
        self.assertIn("no es evaluable", h["mensaje"])


class Punto4Audio(BasePunto4):

    def test_la_duracion_cambia_mas_de_la_tolerancia(self):
        sal = self.sonda("wav", duracion_s=7.0)
        h = self.unico(V.punto4_pedido(sal, self.sonda("wav"),
                                       {"destino": "wav", "params": {}}),
                       "A1/V1", "fallo")
        self.assertEqual(h["obtenido"], 7.0)
        self.assertTrue(h["esperado"].startswith("8.0000"))

    def test_la_tolerancia_de_un_MP3_es_la_de_su_trama_no_10_ms(self):
        """Trampa: la trama de MP3 dura 26,1 ms, asi que exigirle +-10 ms es
        exigirle lo imposible. 20 ms de desvio NO deben ser fallo en mp3 y SI
        en wav, con la misma cifra."""
        des = 0.020
        mp3 = self.sonda("mp3", duracion_s=8.0 + des)
        hs = V.punto4_pedido(mp3, self.sonda("mp3"),
                             {"destino": "mp3", "params": {}})
        self.assertEqual([x for x in hs if x["regla"] == "A1/V1"], [],
                         "20 ms cabe en una trama de MP3")
        wav = self.sonda("wav", duracion_s=8.0 + des)
        self.unico(V.punto4_pedido(wav, self.sonda("wav"),
                                   {"destino": "wav", "params": {}}),
                   "A1/V1", "fallo")

    def test_solo_audio_compara_PISTA_contra_PISTA(self):
        """En `tipico.mp4` el contenedor dura 20,0000 s y su pista de audio
        20,0232: comparar contra el contenedor daba un falso fallo de 15,6 ms.

        El par se construye para que las DOS lecturas den respuestas OPUESTAS,
        que es la unica forma de demostrar que se tomo la rama y no otra: la
        pista de audio de la entrada dura 21 s y su contenedor 20; la salida
        dura 20,0232 en los dos sitios.

            con solo_audio -> 20,0232 contra 21,0000 = 977 ms  -> FALLO
            sin solo_audio -> 20,0232 contra 20,0000 =  23 ms  -> limpio
        """
        ent = copy.deepcopy(self.real.get("mp4") or {})
        sal = copy.deepcopy(self.real.get("wav") or {})
        if not sal or not ent:
            self.skipTest("hace falta corpus/video y corpus/audio")
        for x in ent["pistas"]:
            if x["tipo"] == "audio":
                x["duracion_s"] = 21.0
        sal["duracion_s"] = 20.0232
        for x in sal["pistas"]:
            x["duracion_s"] = 20.0232
        h = self.unico(
            V.punto4_pedido(sal, ent,
                            {"destino": "wav", "params": {"solo_audio": True}}),
            "A1/V1", "fallo")
        self.assertTrue(h["esperado"].startswith("21.0000"),
                        "el esperado tiene que ser la PISTA de la entrada, no "
                        "su contenedor: %r" % h["esperado"])
        hs2 = V.punto4_pedido(sal, ent, {"destino": "wav", "params": {}})
        self.assertEqual([x for x in hs2 if x["regla"] == "A1/V1"], [],
                         "sin solo_audio se compara contra el contenedor y los "
                         "23 ms caben en la trama de AAC de la entrada: %r"
                         % self.reglas(hs2))

    def test_solo_audio_sin_una_sola_pista_de_audio_con_duracion(self):
        """El bucle de `solo_audio` se agota sin `break`: cuando ninguna pista
        publica duracion, la comparacion cae de vuelta al contenedor en vez de
        quedarse sin dato. Es la rama de salida del `for`, y sin ella la regla
        parece que siempre encuentra una pista."""
        ent = copy.deepcopy(self.real.get("mp4") or {})
        sal = copy.deepcopy(self.real.get("wav") or {})
        if not ent or not sal:
            self.skipTest("hace falta corpus/video y corpus/audio")
        for s in (ent, sal):
            for x in s["pistas"]:
                x.pop("duracion_s", None)
        sal["duracion_s"] = 21.0                     # solo el contenedor habla
        h = self.unico(
            V.punto4_pedido(sal, ent,
                            {"destino": "wav", "params": {"solo_audio": True}}),
            "A1/V1", "fallo")
        self.assertEqual(h["obtenido"], 21.0)
        self.assertTrue(h["esperado"].startswith("20.0000"),
                        "sin pista con duracion se compara contra el "
                        "contenedor de la entrada: %r" % h["esperado"])

    def test_opus_fuerza_48_kHz_y_eso_es_informativo(self):
        """Trampa 3: Opus solo opera a 48 kHz. El cambio es real y no es un
        fallo del motor."""
        sal = copy.deepcopy(self.real.get("wav") or {})
        if not sal:
            self.skipTest("hace falta corpus/audio/trivial.wav")
        for x in sal["pistas"]:
            x["sample_rate"], x["codec"] = 48000, "libopus"
        h = self.unico(V.punto4_pedido(sal, self.sonda("wav"),
                                       {"destino": "opus", "params": {}}),
                       "A3", "informativo")
        self.assertEqual((h["esperado"], h["obtenido"]), (44100, 48000))

    def test_otro_codec_a_otra_frecuencia_SI_es_fallo(self):
        """El control de la celda anterior: la excepcion es de Opus, no del
        numero 48000 ni del hecho de que cambie."""
        sal = copy.deepcopy(self.real.get("wav") or {})
        if not sal:
            self.skipTest("hace falta corpus/audio/trivial.wav")
        for x in sal["pistas"]:
            x["sample_rate"], x["codec"] = 22050, "pcm_s16le"
        h = self.unico(V.punto4_pedido(sal, self.sonda("wav"),
                                       {"destino": "wav", "params": {}}),
                       "A3", "fallo")
        self.assertEqual((h["esperado"], h["obtenido"]), (44100, 22050))

    def test_numero_de_canales_alterado_sin_pedirlo(self):
        sal = copy.deepcopy(self.real.get("wav") or {})
        if not sal:
            self.skipTest("hace falta corpus/audio/trivial.wav")
        for x in sal["pistas"]:
            x["canales"] = 2
        h = self.unico(V.punto4_pedido(sal, self.sonda("wav"),
                                       {"destino": "wav", "params": {}}),
                       "A2", "fallo")
        self.assertEqual((h["esperado"], h["obtenido"]), (1, 2))

    def test_los_canales_pedidos_no_son_un_hallazgo(self):
        sal = copy.deepcopy(self.real.get("wav") or {})
        if not sal:
            self.skipTest("hace falta corpus/audio/trivial.wav")
        for x in sal["pistas"]:
            x["canales"] = 2
        hs = V.punto4_pedido(sal, self.sonda("wav"),
                             {"destino": "wav", "params": {"canales": 2}})
        self.assertEqual([x for x in hs if x["regla"] == "A2"], [])


class Punto4BitrateDeAudio(BasePunto4):
    """La rama que solo el SUBPROCESO puede alcanzar dentro de un contenedor.

    `CensoDeClaves` mide por que: `sondear_en_proceso` no publica el
    `bitrate_bps` de una pista de audio dentro de un MP4, y `ffprobe` si. Sobre
    un MP3 suelto lo publican las dos.
    """

    def pistas_con_bitrate(self, valor):
        sal = copy.deepcopy(self.real.get("mp3") or {})
        if not sal:
            self.skipTest("hace falta corpus/audio/tipico.mp3")
        for x in sal["pistas"]:
            if x["tipo"] == "audio":
                x["bitrate_bps"] = valor
        return sal

    def test_bitrate_muy_lejos_del_pedido_es_fallo(self):
        """ConvertX entregaba 64 kbps pidiendole 192: 67 % de desvio."""
        sal = self.pistas_con_bitrate(64000)
        h = self.unico(V.punto4_pedido(sal, self.sonda("mp3"),
                                       {"destino": "mp3",
                                        "params": {"bitrate_bps": 192000}}),
                       "-", "fallo")
        self.assertEqual((h["esperado"], h["obtenido"]), (192000, 64000))

    def test_bitrate_lejos_del_pedido_es_aviso(self):
        """El bitrate es una PETICION, no un contrato: el AAC nativo de ffmpeg
        entrega 129 kbps cuando se le piden 192 sobre material mono."""
        sal = self.pistas_con_bitrate(129000)
        h = self.unico(V.punto4_pedido(sal, self.sonda("mp3"),
                                       {"destino": "mp3",
                                        "params": {"bitrate_bps": 192000}}),
                       "-", "aviso")
        self.assertEqual(h["obtenido"], 129000)

    def test_un_desvio_menor_del_15_por_ciento_se_acepta(self):
        sal = self.pistas_con_bitrate(180000)
        hs = V.punto4_pedido(sal, self.sonda("mp3"),
                             {"destino": "mp3",
                              "params": {"bitrate_bps": 192000}})
        self.assertEqual([x for x in hs if x["regla"] == "-"], [])

    def test_sin_bitrate_en_ninguna_pista_la_regla_se_CALLA(self):
        """El bucle se agota sin `break`. Que no haya dato no puede convertirse
        en un hallazgo: es la diferencia entre «no cumple» y «no lo se», y es la
        rama que la sonda en proceso toma SIEMPRE dentro de un contenedor."""
        sal = copy.deepcopy(self.real.get("mp3") or {})
        if not sal:
            self.skipTest("hace falta corpus/audio/tipico.mp3")
        for x in sal["pistas"]:
            x.pop("bitrate_bps", None)
        hs = V.punto4_pedido(sal, self.sonda("mp3"),
                             {"destino": "mp3",
                              "params": {"bitrate_bps": 192000}})
        self.assertEqual([x for x in hs if x["regla"] == "-"], [])

    def test_una_pista_de_VIDEO_no_secuestra_la_regla_de_bitrate(self):
        """El bucle salta las pistas que no son de audio antes de romperse: si
        la primera pista es de video, la regla tiene que seguir buscando."""
        sal = copy.deepcopy(self.real.get("mp4") or {})
        if not sal:
            self.skipTest("hace falta corpus/video/tipico.mp4")
        for x in sal["pistas"]:
            if x["tipo"] == "audio":
                x["bitrate_bps"] = 64000
        self.assertEqual(sal["pistas"][0]["tipo"], "video")
        h = self.unico(V.punto4_pedido(sal, self.sonda("mp4"),
                                       {"destino": "mp4",
                                        "params": {"bitrate_bps": 192000}}),
                       "-", "fallo")
        self.assertEqual(h["obtenido"], 64000)

    @unittest.skipUnless(hay_binario("ffprobe"), "hace falta ffprobe")
    def test_con_sonda_REAL_por_subproceso_la_rama_se_alcanza(self):
        """Trampa 109: demostrar que la rama es alcanzable con la sonda de
        verdad y no solo con un dict mutado. `tipico.mp3` mide 64 kbps; se le
        piden 192 y la regla dispara con los numeros que trae el fichero."""
        if not hay_corpus("audio/tipico.mp3", 1000):
            self.skipTest("hace falta corpus/audio/tipico.mp3")
        sal = V.sondear(corpus("audio/tipico.mp3"), "subproceso")
        bit = [x.get("bitrate_bps") for x in sal["pistas"]
               if x["tipo"] == "audio"][0]
        self.assertIsInstance(bit, int, "sin este dato la rama no se evalua")
        h = self.unico(V.punto4_pedido(sal, sal,
                                       {"destino": "mp3",
                                        "params": {"bitrate_bps": 192000}}),
                       "-", "fallo")
        self.assertEqual(h["obtenido"], bit)


class Punto4Documentos(BasePunto4):

    def test_la_caja_de_pagina_no_corresponde_a_la_densidad_pedida(self):
        ent = self.sonda("png")                       # 1920 px de ancho
        sal = self.sonda("pdf", ancho_pt=400.0)       # a 150 ppp tocarian 921,6
        h = self.unico(V.punto4_pedido(sal, ent,
                                       {"destino": "pdf",
                                        "params": {"dpi": 150}}),
                       "P7", "fallo")
        self.assertEqual(h["esperado"], round(1920 * 72.0 / 150, 1))
        self.assertEqual(h["obtenido"], 400.0)

    def test_la_densidad_tambien_se_lee_de_params_densidad(self):
        """El codigo acepta `dpi` o `densidad`; sin esta celda solo se ejerce
        la primera mitad del `or`."""
        ent = self.sonda("png")
        sal = self.sonda("pdf", ancho_pt=400.0)
        h = self.unico(V.punto4_pedido(sal, ent,
                                       {"destino": "pdf",
                                        "params": {"densidad": 150}}),
                       "P7", "fallo")
        self.assertEqual(h["esperado"], round(1920 * 72.0 / 150, 1))

    def test_una_caja_de_pagina_CORRECTA_no_produce_hallazgo(self):
        """Control negativo de P7: la misma regla, con la caja que la densidad
        pedida ordena, se calla. Sin esta celda P7 solo se ejerce por su rama
        de fallo y no se demuestra que compare nada."""
        ent = self.sonda("png")                       # 1920 px
        sal = self.sonda("pdf", ancho_pt=round(1920 * 72.0 / 150, 1))
        hs = V.punto4_pedido(sal, ent,
                             {"destino": "pdf", "params": {"dpi": 150}})
        self.assertEqual([x for x in hs if x["regla"] == "P7"], [])

    def test_sin_numero_de_paginas_en_una_de_las_dos_la_regla_P1_se_calla(self):
        """Es la rama que salva a P1 de un PDF que Ghostscript no supo leer:
        `n_paginas=None` no es «cero paginas»."""
        sal = self.sonda("pdf", n_paginas=None)
        hs = V.punto4_pedido(sal, self.sonda("pdf"),
                             {"destino": "pdf", "params": {}})
        self.assertEqual([x for x in hs if x["regla"] == "P1"], [])

    def test_un_pixel_un_punto_es_una_pagina_absurda(self):
        """1920 px -> 1920 pt son 677 mm de ancho: casi un A0. Pasa los cuatro
        puntos del contrato y es basura."""
        ent = self.sonda("png")
        sal = self.sonda("pdf", ancho_pt=1920.0, alto_pt=1080.0)
        h = self.unico(V.punto4_pedido(sal, ent,
                                       {"destino": "pdf", "params": {}}),
                       "P7", "aviso")
        self.assertEqual(h["obtenido"], "1:1")
        self.assertIn("absurda", h["mensaje"])

    def test_cambia_el_numero_de_paginas(self):
        sal = self.sonda("pdf", n_paginas=3)
        h = self.unico(V.punto4_pedido(sal, self.sonda("pdf"),
                                       {"destino": "pdf", "params": {}}),
                       "P1", "fallo")
        self.assertEqual((h["esperado"], h["obtenido"]), (1, 3))

    def test_el_mismo_numero_de_paginas_no_produce_hallazgo(self):
        hs = V.punto4_pedido(self.sonda("pdf"), self.sonda("pdf"),
                             {"destino": "pdf", "params": {}})
        self.assertEqual([x for x in hs if x["regla"] == "P1"], [])


class Punto4Datos(BasePunto4):

    def test_cambia_el_numero_de_filas_logicas(self):
        sal = self.sonda("csv", filas_datos=1)
        h = self.unico(V.punto4_pedido(sal, self.sonda("csv"),
                                       {"destino": "csv", "params": {}}),
                       "D1", "fallo")
        self.assertEqual((h["esperado"], h["obtenido"]), (2, 1))

    def test_cero_filas_no_se_confunde_con_ausencia_de_dato(self):
        """`if fo is not None`: un CSV con 0 filas de datos es un dato, no un
        hueco. Con un `if fo and fe` la perdida TOTAL de filas seria invisible,
        que es justo el fallo que la regla busca."""
        sal = self.sonda("csv", filas_datos=0)
        h = self.unico(V.punto4_pedido(sal, self.sonda("csv"),
                                       {"destino": "csv", "params": {}}),
                       "D1", "fallo")
        self.assertEqual(h["obtenido"], 0)

    def test_cambia_la_cabecera(self):
        sal = self.sonda("csv", csv_cabecera=["id", "nombre"])
        h = self.unico(V.punto4_pedido(sal, self.sonda("csv"),
                                       {"destino": "csv", "params": {}}),
                       "D4", "fallo")
        self.assertEqual(h["esperado"], ["id", "nombre", "notas"])

    def test_una_cabecera_REORDENADA_no_es_una_cabecera_perdida(self):
        """La comparacion es `sorted(co) != sorted(ce)`.

        Se filtra por SEVERIDAD y no solo por regla: la etiqueta `D4` la
        comparten la cabecera perdida (fallo) y el BOM no pedido (aviso), y
        `patologico_bom.csv` dispara el segundo siempre.
        """
        sal = self.sonda("csv", csv_cabecera=["notas", "id", "nombre"])
        hs = V.punto4_pedido(sal, self.sonda("csv"),
                             {"destino": "csv", "params": {}})
        self.assertEqual([x for x in hs
                          if x["regla"] == "D4" and x["severidad"] == "fallo"],
                         [])

    def test_un_BOM_no_pedido_en_la_salida_es_un_aviso(self):
        ent = self.sonda("json")                       # sin BOM
        sal = self.sonda("csv")                        # patologico_bom.csv: BOM
        h = self.unico(V.punto4_pedido(sal, ent,
                                       {"destino": "csv", "params": {}}),
                       "D4", "aviso")
        self.assertIn("BOM UTF-8", h["mensaje"])

    def test_un_BOM_PEDIDO_no_es_un_aviso(self):
        ent = self.sonda("json")
        sal = self.sonda("csv")
        hs = V.punto4_pedido(sal, ent,
                             {"destino": "csv", "params": {"bom": True}})
        self.assertEqual([x for x in hs if x["severidad"] == "aviso"], [])


class CuartoPuntoEnProduccion(BasePunto4):
    """Trampa 109: las clases de arriba llaman a `punto4_pedido` directamente.

    Esta recorre la puerta que usa el producto -- `verificar()` -- y comprueba
    que el hallazgo llega hasta el veredicto y hasta la cobertura, que es lo
    que consumen la CLI, el MCP, el watcher y la API.
    """

    def test_el_redimensionado_llega_al_veredicto_por_verificar(self):
        if not ("png" in self.real):
            self.skipTest("hace falta corpus/imagen/tipico.png")
        sal = self.sonda("png", ancho=800, alto=450)
        r = V.verificar(corpus("imagen/tipico.png"),
                        {"destino": "png", "params": {}},
                        corpus("imagen/tipico.png"),
                        sonda_ent=self.sonda("png"), sonda_sal=sal)
        self.assertEqual(r["veredicto"], "fallo")
        self.assertIn(("I1/V7", "fallo"), self.reglas(r["hallazgos"]))
        self.assertIn("4_pedido", r["ms"])

    def test_sin_entrada_el_veredicto_baja_a_ok_parcial(self):
        if not ("png" in self.real):
            self.skipTest("hace falta corpus/imagen/tipico.png")
        r = V.verificar(corpus("imagen/tipico.png"),
                        {"destino": "png", "params": {}})
        self.assertEqual(r["veredicto"], "ok_parcial")
        self.assertFalse(r["cobertura"].get("4_pedido", True))


# ===========================================================================
# 3. main -- el CLI del propio verificador
# ===========================================================================

class BaseCli(Desechable):

    def corre(self, argv, rc_esperado=0):
        """Ejecuta `main(argv)` y devuelve su stdout.

        Se afirma sobre el CODIGO DE SALIDA ademas del texto: es lo que consume
        un script, y un `main` que imprime bien y devuelve mal es un fallo que
        una asercion sobre el texto no ve.
        """
        buf, err = io.StringIO(), io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            rc = V.main(argv)
        self.assertEqual(rc, rc_esperado,
                         "rc=%r con argv=%r; stdout=%r"
                         % (rc, argv, buf.getvalue()[:400]))
        return buf.getvalue()


class CliUtilidades(BaseCli):

    def test_censar_vuelca_el_censo_de_un_directorio(self):
        self.escribe("a.txt", b"hola")
        salida = self.corre(["--censar", self.dir])
        j = json.loads(salida)
        self.assertIn(self.dir, j)
        self.assertEqual(j[self.dir]["a.txt"], 4)

    def test_censar_admite_varios_directorios(self):
        otro = tempfile.mkdtemp(prefix="cob-contrato-2-")
        self.addCleanup(shutil.rmtree, otro, ignore_errors=True)
        self.escribe("a.txt", b"hola")
        j = json.loads(self.corre(["--censar", self.dir, otro]))
        self.assertEqual(sorted(j), sorted([self.dir, otro]))

    def test_sondear_vuelca_el_sondeo_sin_juzgarlo(self):
        if not hay_corpus("imagen/tipico.png", 40000):
            self.skipTest("hace falta corpus/imagen")
        j = json.loads(self.corre(["--sondear", corpus("imagen/tipico.png")]))
        self.assertEqual(j["categoria"], "imagen")
        self.assertEqual(j["motor"], "proceso")
        self.assertNotIn("veredicto", j, "--sondear no juzga")

    @unittest.skipUnless(hay_binario("magick"), "hace falta magick")
    def test_sondear_con_motor_subproceso(self):
        if not hay_corpus("imagen/tipico.png", 40000):
            self.skipTest("hace falta corpus/imagen")
        j = json.loads(self.corre(["--sondear", corpus("imagen/tipico.png"),
                                   "--motor", "subproceso"]))
        self.assertEqual(j["motor"], "subproceso")
        self.assertEqual(j["n_procesos"], 1)

    def test_sondear_con_alfa(self):
        if not hay_corpus("imagen/alpha.png", 1000):
            self.skipTest("hace falta corpus/imagen/alpha.png")
        j = json.loads(self.corre(["--sondear", corpus("imagen/alpha.png"),
                                   "--alfa"]))
        self.assertTrue(j["alfa_no_trivial"])

    def test_alfa_min_de_un_solo_fichero(self):
        """La ayuda del CLI dice que sin `--exacto` se corta en el primer pixel
        no opaco «y se marca exacto=false». MEDIDO: sobre `alpha.png` sale
        `exacto=true` aun sin la bandera, y esta bien -- el codigo hace
        `exacto or mn == 0`: si el minimo es 0 no puede haber nada menor, asi
        que el corte temprano no le quita exactitud. La ayuda describe el caso
        general, no este. Por eso la asercion es sobre el VALOR y no sobre la
        bandera."""
        if not hay_corpus("imagen/alpha.png", 1000):
            self.skipTest("hace falta corpus/imagen/alpha.png")
        j = json.loads(self.corre(["--alfa-min", corpus("imagen/alpha.png")]))
        self.assertTrue(j["evaluable"])
        self.assertEqual(j["alfa_min"], 0.0)
        self.assertTrue(j["alfa_no_trivial"])

    @unittest.skipUnless(hay_binario("magick"), "hace falta magick")
    def test_alfa_min_exacto_recorre_la_imagen_entera(self):
        """`--exacto` cambia el VALOR, no solo la etiqueta.

        Sobre `alpha.png` la bandera no discrimina -- su minimo es 0 y el
        codigo hace `exacto or mn == 0` --, asi que la primera version de esta
        prueba era VACUA y el control de discriminacion la delato (M32 en
        `bench/salidas-cobertura-contrato/`). Con un GRADIENTE de alfa, cortar
        en el primer pixel no opaco devuelve un minimo que NO es el minimo.
        """
        if not hay_corpus("imagen/trivial.png", 100):
            self.skipTest("hace falta corpus/imagen/trivial.png")
        grad = self.ruta("grad.png")
        r = subprocess.run(
            ["magick", "-size", "64x64", "xc:red", "-alpha", "set",
             "(", "-size", "64x64", "gradient:white-black", ")",
             "-compose", "CopyOpacity", "-composite", grad],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=180)
        if r.returncode != 0 or not os.path.exists(grad):
            self.skipTest("magick rc=%s" % r.returncode)
        rapido = json.loads(self.corre(["--alfa-min", grad]))
        lento = json.loads(self.corre(["--alfa-min", grad, "--exacto"]))
        self.assertFalse(rapido["exacto"])
        self.assertTrue(lento["exacto"])
        self.assertEqual(lento["alfa_min"], 0.0)
        self.assertGreater(rapido["alfa_min"], lento["alfa_min"],
                           "el corte temprano devuelve un minimo que no es el "
                           "minimo; por eso se marca exacto=false")
        self.assertGreater(lento["filas_leidas"], rapido["filas_leidas"])


class CliContrato(BaseCli):

    def test_sin_salida_ni_lote_el_parser_se_niega(self):
        buf, err = io.StringIO(), io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                V.main(["--motor", "proceso"])
        self.assertEqual(cm.exception.code, 2)
        self.assertIn("--salida", err.getvalue())

    def test_una_salida_correcta_devuelve_0_y_texto_legible(self):
        if not hay_corpus("imagen/tipico.png", 40000):
            self.skipTest("hace falta corpus/imagen")
        txt = self.corre(["--salida", corpus("imagen/tipico.png"),
                          "--entrada", corpus("imagen/tipico.png")])
        self.assertIn("CONTRATO (grupo A)", txt)
        self.assertIn("punto 1:", txt)
        self.assertIn("cobertura:", txt)
        self.assertIn("ms:", txt)

    def test_un_fallo_del_contrato_devuelve_1(self):
        """Un PNG con extension .webp: el punto 1 mira los bytes magicos, no la
        extension, y el CLI tiene que devolver 1 para que un script se entere."""
        if not hay_corpus("imagen/tipico.png", 40000):
            self.skipTest("hace falta corpus/imagen")
        mentira = self.ruta("mentira.webp")
        with open(corpus("imagen/tipico.png"), "rb") as f, \
                open(mentira, "wb") as g:
            g.write(f.read())
        txt = self.corre(["--salida", mentira,
                          "--entrada", corpus("imagen/tipico.png")],
                         rc_esperado=1)
        self.assertIn("FALLO", txt)
        self.assertIn("G3", txt)
        self.assertIn("la firma real no corresponde a la extension pedida", txt)

    @unittest.skipUnless(hay_binario("magick"), "hace falta magick")
    def test_el_destino_por_defecto_sale_de_la_extension_de_la_salida(self):
        """El efecto es observable: la MISMA bajada de 16 a 8 bits es `I4
        fallo` cuando el destino se deduce de la extension (.png, que admite 16)
        e `I5 informativo` cuando se declara `--destino jpeg`, cuyo techo son 8.
        """
        if not hay_corpus("imagen/tipico.png", 40000):
            self.skipTest("hace falta corpus/imagen")
        ocho = self.ruta("ocho.png")
        r = subprocess.run(["magick", corpus("imagen/tipico.png"),
                            "-depth", "8", ocho],
                           stdin=subprocess.DEVNULL, capture_output=True,
                           timeout=300)
        if r.returncode != 0 or not os.path.exists(ocho):
            self.skipTest("magick rc=%s" % r.returncode)
        base = ["--salida", ocho, "--entrada", corpus("imagen/tipico.png"),
                "--json"]
        sin = json.loads(self.corre(base, rc_esperado=1))
        con = json.loads(self.corre(base + ["--destino", "jpeg"]))
        self.assertIn(("I4", "fallo"),
                      [(h["regla"], h["severidad"]) for h in sin["hallazgos"]])
        self.assertIn(("I5", "informativo"),
                      [(h["regla"], h["severidad"]) for h in con["hallazgos"]])

    def test_params_json_llega_al_punto_4(self):
        """Sin `--params` no hay cuarto punto que valga: es lo que separa una
        conversion impecable de una degradacion silenciosa."""
        if not hay_corpus("imagen/tipico.png", 40000):
            self.skipTest("hace falta corpus/imagen")
        txt = self.corre(["--salida", corpus("imagen/tipico.png"),
                          "--entrada", corpus("imagen/tipico.png"),
                          "--params", '{"ancho": 800}'], rc_esperado=1)
        self.assertIn("dimensiones distintas de las pedidas", txt)
        self.assertIn("1920x1080", txt)

    def test_el_destino_PEDIDO_no_participa_en_el_punto_1(self):
        """OBSERVACION MEDIDA, no un fallo del contrato: `punto1_firma` compara
        la firma contra la EXTENSION DEL FICHERO DE SALIDA
        (`os.path.splitext(salida)`), nunca contra `pedido["destino"]`. Pedir
        `--destino webp` y entregar un `.png` que es un PNG no produce ni un
        hallazgo, y el veredicto sale `ok_parcial`.

        No hay riesgo en produccion -- FileX construye la ruta de salida CON la
        extension del destino, asi que las dos coinciden y el caso se convierte
        en el `mentira.webp` de la prueba de arriba, que si falla. Queda escrito
        porque desde el CLI las dos pueden diferir y nadie lo dice: el
        `--destino` solo mueve TOLERANCIAS (techos de profundidad, alfa, gif).
        """
        if not hay_corpus("imagen/tipico.png", 40000):
            self.skipTest("hace falta corpus/imagen")
        j = json.loads(self.corre(["--salida", corpus("imagen/tipico.png"),
                                   "--entrada", corpus("imagen/tipico.png"),
                                   "--destino", "webp", "--json"]))
        self.assertEqual(j["veredicto"], "ok_parcial")
        self.assertEqual([h for h in j["hallazgos"]
                          if h["severidad"] == "fallo"], [])
        self.assertEqual(j["punto1"], "evaluado")

    def test_json_vuelca_hallazgos_cobertura_y_tiempos(self):
        if not hay_corpus("imagen/tipico.png", 40000):
            self.skipTest("hace falta corpus/imagen")
        j = json.loads(self.corre(["--salida", corpus("imagen/tipico.png"),
                                   "--entrada", corpus("imagen/tipico.png"),
                                   "--json"]))
        for clave in ("veredicto", "hallazgos", "cobertura", "ms", "punto1"):
            self.assertIn(clave, j)

    def test_el_censo_habilita_el_punto_5(self):
        """El punto 5 es el unico del contrato que NO se puede verificar a
        posteriori: sin censo se declara NO CUBIERTO, no se da por bueno."""
        if not hay_corpus("imagen/tipico.png", 40000):
            self.skipTest("hace falta corpus/imagen")
        sal = corpus("imagen/tipico.png")
        d = os.path.dirname(sal)
        censo = self.ruta("censo.json")
        with open(censo, "w", encoding="utf-8") as fh:
            json.dump({"antes": {d: {}},
                       "despues": {d: {os.path.basename(sal):
                                       os.path.getsize(sal)}}}, fh)
        sin = json.loads(self.corre(["--salida", sal, "--json"]))
        con = json.loads(self.corre(["--salida", sal, "--censo", censo,
                                     "--json"]))
        self.assertFalse(sin["cobertura"].get("5_escritura", False))
        self.assertTrue(con["cobertura"].get("5_escritura", False))

    def test_lote_devuelve_una_lista_y_el_rc_del_peor(self):
        if not hay_corpus("imagen/tipico.png", 40000):
            self.skipTest("hace falta corpus/imagen")
        lote = self.ruta("lote.json")
        with open(lote, "w", encoding="utf-8") as fh:
            json.dump([{"salida": corpus("imagen/tipico.png"),
                        "entrada": corpus("imagen/tipico.png"),
                        "destino": "png", "params": {}},
                       {"salida": corpus("imagen/tipico.png"),
                        "entrada": corpus("imagen/tipico.png"),
                        "destino": "png", "params": {"ancho": 800}}], fh)
        j = json.loads(self.corre(["--lote", lote], rc_esperado=1))
        self.assertEqual(len(j), 2)
        # `ok_parcial` y no `ok`: sin censo, el punto 5 se declara NO CUBIERTO.
        # Que el primero no sea `fallo` es lo que hace que el rc=1 venga del
        # segundo y no del lote entero.
        self.assertEqual(j[0]["veredicto"], "ok_parcial")
        self.assertEqual(j[1]["veredicto"], "fallo")

    def test_un_lote_enteramente_sano_devuelve_0(self):
        if not hay_corpus("imagen/tipico.png", 40000):
            self.skipTest("hace falta corpus/imagen")
        lote = self.ruta("lote.json")
        with open(lote, "w", encoding="utf-8") as fh:
            json.dump([{"salida": corpus("imagen/tipico.png"),
                        "entrada": corpus("imagen/tipico.png"),
                        "destino": "png", "params": {}}], fh)
        j = json.loads(self.corre(["--lote", lote]))
        self.assertEqual(len(j), 1)


class CliFidelidad(BaseCli):
    """El grupo C se ejecuta aparte y con su PROPIO veredicto: un aviso de
    fidelidad no contamina el veredicto del contrato.

    Se usan ficheros de DATOS a proposito: las reglas de fidelidad de audio y
    video «cuestan lo que convertir» y este carril no es el sitio para gastar
    esa maquina. Lo que se ejercita aqui es el CABLEADO del CLI.
    """

    def setUp(self):
        Desechable.setUp(self)
        self.addCleanup(V.v2, True)   # el interruptor V2 es de MODULO

    def par(self):
        if not hay_corpus("datos/patologico_bom.csv", 50):
            self.skipTest("hace falta corpus/datos")
        return corpus("datos/patologico_bom.csv")

    def test_fidelidad_imprime_DOS_bloques_con_DOS_veredictos(self):
        p = self.par()
        txt = self.corre(["--salida", p, "--entrada", p, "--fidelidad",
                          "--sin-v2"])
        self.assertIn("CONTRATO (grupo A)", txt)
        self.assertIn("FIDELIDAD (grupo C)", txt)
        self.assertEqual(txt.count("cobertura:"), 2)

    def test_solo_fidelidad_omite_el_contrato(self):
        p = self.par()
        txt = self.corre(["--salida", p, "--entrada", p, "--solo-fidelidad",
                          "--sin-v2"])
        self.assertIn("FIDELIDAD (grupo C)", txt)
        self.assertNotIn("CONTRATO (grupo A)", txt)

    def test_fidelidad_en_json_va_bajo_su_propia_clave(self):
        p = self.par()
        j = json.loads(self.corre(["--salida", p, "--entrada", p,
                                   "--fidelidad", "--sin-v2", "--json"]))
        self.assertIn("fidelidad", j)
        self.assertIn("veredicto", j["fidelidad"])
        self.assertNotEqual(id(j["fidelidad"]), id(j))

    def test_lote_con_fidelidad(self):
        p = self.par()
        lote = self.ruta("lote.json")
        with open(lote, "w", encoding="utf-8") as fh:
            json.dump([{"salida": p, "entrada": p, "destino": "csv",
                        "params": {}}], fh)
        j = json.loads(self.corre(["--lote", lote, "--fidelidad", "--sin-v2"]))
        self.assertIn("fidelidad", j[0])

    def test_sin_v2_declara_la_regla_NO_CUBIERTA_en_vez_de_darla_por_buena(self):
        """`--sin-v2` apaga el recuento real de fotogramas, que DECODIFICA el
        video entero (el 36 % de la suite de fidelidad). Lo que importa es que
        apagarlo no produzca un verde: V2 aparece en la cobertura con valor
        `False`, no desaparece de ella."""
        if not hay_corpus("video/trivial.mp4", 1000):
            self.skipTest("hace falta corpus/video/trivial.mp4")
        p = corpus("video/trivial.mp4")
        try:
            j = json.loads(self.corre(["--salida", p, "--entrada", p,
                                       "--solo-fidelidad", "--sin-v2",
                                       "--json"]))
            cob = j.get("cobertura") or {}
            self.assertIn("V2", cob)
            self.assertFalse(cob["V2"])
            self.assertEqual(j["veredicto"], "ok_parcial")
        finally:
            V.v2(True)   # el interruptor es de MODULO: se deja como estaba


if __name__ == "__main__":
    unittest.main()

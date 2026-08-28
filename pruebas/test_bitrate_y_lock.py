"""N24 (bitrate de vídeo), N25 (el lock rodea al codificado) y N22 (`.pdb`).

Tres disciplinas que este encargo pagó y que están escritas aquí para que no se
pierdan:

* **Las pruebas de forma van sobre el AST, no sobre el texto** (trampa 42), y
  antes de comparar hay que comprobar que la fuente COMPILA (trampa 60): el
  camino de degradación de `huella.de_alcance` es también un camino de falso
  verde.
* **Ninguna prueba de aquí toca el lock de GPU de la máquina.** `GPU_LOCK`
  apunta a un fichero del `tempdir` de la prueba. Otro agente puede estar usando
  la tarjeta.
* **Un `.pdb` de Palm empieza por el NOMBRE del fichero**, así que una prueba
  que mire el principio del fichero mide el nombre que le puso el arnés.
"""
from __future__ import annotations

import ast
import base64
import inspect
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filex import gpu, huella, nucleo, verificador  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


CORPUS = os.path.join(RAIZ, "corpus", "video")


# ===========================================================================
# N24 — el bitrate de VÍDEO (regla V10)
# ===========================================================================
def _sonda_video(bitrate_contenedor, n_audio=0, dur=10.0):
    pistas = [{"tipo": "video", "codec": "hevc", "ancho": 640, "alto": 480}]
    for _ in range(n_audio):
        # `bitrate_bps` a None a propósito: es lo que la sonda en proceso
        # devuelve de verdad para una pista de audio dentro de un mp4 o un mkv.
        pistas.append({"tipo": "audio", "codec": "aac", "canales": 2,
                       "bitrate_bps": None})
    return {"categoria": "av", "duracion_s": dur, "n_pistas": len(pistas),
            "bitrate_bps": bitrate_contenedor, "pistas": pistas,
            "ancho": 640, "alto": 480}


def _v10(sonda, pedido_bps, n_audio=0):
    ped = {"destino": "mkv", "params": {"bitrate_video_bps": pedido_bps}}
    ent = _sonda_video(5_000_000, n_audio=n_audio)
    h = verificador.punto4_pedido(sonda, ent, ped)
    return [x for x in h if x.get("regla") == "V10"]


class ElBitrateDeVideoTieneRegla(unittest.TestCase):
    """El contrato daba `ok` a las 8 celdas de NVENC de H2 §4.3."""

    def test_la_sonda_NO_publica_el_bitrate_de_una_pista_de_video(self):
        """La causa real del hueco, y no es el filtro `tipo == "audio"`.

        Quitar el filtro no habría arreglado nada: la clave no existe. Es la
        trampa 58 — el hecho de H2 era cierto y la causa estaba un nivel abajo.
        """
        p = os.path.join(CORPUS, "tipico.mp4")
        if not os.path.exists(p) or os.path.getsize(p) < 1000:
            self.skipTest("corpus ausente o en punteros de LFS (trampa 34)")
        s = verificador.sondear(p)
        vid = [x for x in s["pistas"] if x["tipo"] == "video"]
        self.assertTrue(vid)
        for x in vid:
            self.assertIsNone(x.get("bitrate_bps"))
        self.assertIsNotNone(s.get("bitrate_bps"),
                             "el del CONTENEDOR sí existe, y es lo único que hay")

    def test_sin_bitrate_video_pedido_la_regla_calla(self):
        h = verificador.punto4_pedido(_sonda_video(9_000_000),
                                      _sonda_video(2_000_000),
                                      {"destino": "mkv", "params": {}})
        self.assertEqual([x for x in h if x.get("regla") == "V10"], [])

    def test_por_abajo_es_fallo_con_audio_y_sin_el(self):
        """El audio solo SUMA: el contenedor es cota superior del vídeo, así
        que el lado de abajo no puede dar un falso positivo por su culpa."""
        for n_aud in (0, 1, 2):
            with self.subTest(n_audio=n_aud):
                s = _sonda_video(200_000, n_audio=n_aud)
                hs = _v10(s, 2_000_000, n_audio=n_aud)
                self.assertEqual([x["severidad"] for x in hs], ["fallo"])

    def test_por_arriba_sin_audio_es_fallo(self):
        hs = _v10(_sonda_video(4_400_000), 2_000_000)
        self.assertEqual([x["severidad"] for x in hs], ["fallo"])

    def test_por_arriba_CON_audio_es_informativo_y_no_fallo(self):
        """MEDIDO: `2pistas.mkv -> .mp4` pidiendo 200 kbps de vídeo entrega
        390 800 bps de contenedor (**+95,4 %**) siendo una conversión buena,
        porque las dos pistas de audio son 128 kbps cada una."""
        hs = _v10(_sonda_video(390_800, n_audio=2), 200_000, n_audio=2)
        self.assertEqual([x["severidad"] for x in hs], ["informativo"])

    def test_el_desvio_normal_de_NVENC_no_es_un_fallo(self):
        """Las cuatro celdas de `hevc_nvenc` de `hito2-nvenc.md` §4.3, con sus
        cifras exactas. Ninguna puede salir `fallo`: +24,59 % es lo que NVENC
        hace a 1 Mbps, no una conversión rota."""
        for pedido, obtenido in ((1_000_000, 1_245_937), (2_000_000, 2_302_135),
                                 (4_000_000, 4_422_089), (8_000_000, 8_785_354)):
            with self.subTest(pedido=pedido):
                hs = _v10(_sonda_video(obtenido), pedido)
                self.assertEqual([x for x in hs if x["severidad"] == "fallo"], [])

    def test_el_umbral_deja_margen_sobre_el_peor_legitimo_medido(self):
        """+56,30 % (`libsvtav1`, fuente pequeña) y −54,83 % (`libvpx-vp9`
        pidiendo 8 Mbps a un 640x480). El umbral va por encima de los dos."""
        self.assertGreater(verificador.BITRATE_VIDEO_TOL, 0.5657)
        self.assertLess(verificador.BITRATE_VIDEO_TOL, 0.8233,
                        "y por debajo del |desvío| patológico más pequeño medido")


# ===========================================================================
# N25 — el lock de GPU alrededor del CODIFICADO
# ===========================================================================
class ElLockRodeaAlCodificado(unittest.TestCase):
    """`bench/hito2-nvenc.md` §6.5: el lock se tomaba alrededor del SONDEO."""

    ARGV_CPU = ["ffmpeg", "-i", "a.mp4", "-map", "0", "-c:v", "libx265", "b.mkv"]
    ARGV_GPU = ["ffmpeg", "-i", "a.mp4", "-map", "0", "-c:v", "hevc_nvenc", "b.mkv"]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.viejo = os.environ.get("GPU_LOCK")
        os.environ["GPU_LOCK"] = os.path.join(self.tmp.name, "prueba-gpu.lock")
        self.guardias = []
        self.guardia_real = gpu.guardia
        gpu.guardia = lambda: (self.guardias.append(1), "")[1]

    def tearDown(self):
        gpu.guardia = self.guardia_real
        if self.viejo is None:
            os.environ.pop("GPU_LOCK", None)
        else:
            os.environ["GPU_LOCK"] = self.viejo
        self.tmp.cleanup()

    def test_lo_que_no_toca_la_tarjeta_no_toca_el_lock(self):
        with nucleo._lock_gpu("prueba", self.ARGV_CPU) as l:
            self.assertIsNone(l)
            self.assertFalse(gpu.poseido())
            self.assertFalse(os.path.exists(gpu.fichero_lock()))
        self.assertEqual(self.guardias, [], "la guardia no debe correr sin GPU")

    def test_lo_que_toca_la_tarjeta_sostiene_el_lock_durante_la_ejecucion(self):
        self.assertTrue(gpu.usa_gpu(self.ARGV_GPU))
        with nucleo._lock_gpu("prueba", self.ARGV_GPU) as l:
            self.assertIsNotNone(l)
            self.assertTrue(gpu.poseido())
            self.assertTrue(os.path.exists(gpu.fichero_lock()))
        self.assertFalse(gpu.poseido())
        self.assertTrue(gpu.esta_libre())
        self.assertEqual(len(self.guardias), 1)

    def test_la_guardia_no_se_repite_en_la_reentrada(self):
        """*«Preguntar por la VRAM en cada conversión sería caro»* — §6.3 de H2.

        Su propio parche lo hacía: `with gpu.Lock(...)` llama a `guardia()`
        SIEMPRE, también cuando el lote ya tiene el lock. Aquí no.
        """
        fuera = gpu.Lock("lote")
        self.assertTrue(fuera.tomar(espera=5))
        try:
            with nucleo._lock_gpu("prueba", self.ARGV_GPU):
                self.assertTrue(gpu.poseido())
            self.assertEqual(self.guardias, [],
                             "la reentrada no debe volver a lanzar nvidia-smi")
            self.assertTrue(gpu.poseido(), "el lote sigue teniendo el lock")
        finally:
            fuera.soltar()
        self.assertTrue(gpu.esta_libre())

    def test_la_ejecucion_esta_DENTRO_del_with_en_el_arbol(self):
        """Forma, sobre el AST. Sin el parche, `ejecutar` es un `Expr` suelto.

        Se comprueba primero que la fuente COMPILA (trampa 60): una prueba de
        árbol que se traga un `SyntaxError` sale verde con arreglo y sin él.
        """
        fuente = inspect.getsource(nucleo)
        arbol = ast.parse(fuente)          # levanta SyntaxError si no compila
        salto = next(n for n in ast.walk(arbol)
                     if isinstance(n, ast.FunctionDef) and n.name == "_un_salto")
        dentro = False
        for w in [n for n in ast.walk(salto) if isinstance(n, ast.With)]:
            ctxs = [i.context_expr for i in w.items]
            if not any(isinstance(c, ast.Call) and getattr(c.func, "id", "") == "_lock_gpu"
                       for c in ctxs):
                continue
            for n in ast.walk(w):
                if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                        and n.func.attr == "ejecutar"):
                    dentro = True
        self.assertTrue(dentro,
                        "invocacion.ejecutar tiene que estar dentro de "
                        "`with _lock_gpu(...)` en `_un_salto`")

    def test_el_nucleo_no_esta_en_la_huella_de_ningun_motor(self):
        """Por qué N25 no caduca ni una arista: los tres componentes son
        `motor` (la clase), `invocacion` (el fichero) y `contrato` (el cierre de
        `verificar`). `nucleo.py` no es ninguno de los tres."""
        h = huella.de_motor_por_nombre("ffmpeg")
        self.assertEqual(sorted(h), ["contrato", "invocacion", "motor"])


# ===========================================================================
# N22 — `.pdb` es un CONTENEDOR de Palm, no dos formatos
# ===========================================================================
def _palmdb(nombre: bytes, tipo_creador: bytes) -> bytes:
    """Una cabecera PalmDB de 78 bytes, con el nombre y el `type`+`creator`.

    Los 32 primeros bytes son el NOMBRE, y es lo que el censo de prefijos
    comunes de F1 midió: ImageMagick y GraphicsMagick escriben ahí el nombre de
    SALIDA y Calibre el de ENTRADA. El marcador está 28 bytes más allá.
    """
    cab = bytearray(78)
    cab[0:len(nombre)] = nombre
    cab[60:68] = tipo_creador
    return bytes(cab)


class ElPdbEsUnContenedorDePalm(unittest.TestCase):

    #: MEDIDO en `filex-c13`, `bench/salidas-bitrate/muestras_pdb.py`.
    CASOS = [(b"vIMGView", "palm_imagen", "magick / gm convert x.png y.pdb"),
             (b"TEXtREAd", "mobi", "ebook-convert x.txt y.pdb"),
             (b"PNRdPPrs", "ereader", "ebook-convert x.txt y.pdb -f ereader"),
             (b"BOOKMOBI", "mobi", "el MOBI de siempre")]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _escribe(self, nombre, marca):
        p = os.path.join(self.tmp.name, nombre)
        with open(p, "wb") as fh:
            fh.write(_palmdb(nombre.encode("ascii"), marca))
        return p

    def test_el_byte_60_separa_la_imagen_del_libro(self):
        for marca, esperada, motor in self.CASOS:
            with self.subTest(motor=motor):
                p = self._escribe("muestra.pdb", marca)
                self.assertEqual(verificador.firma_real(p), esperada)

    def test_el_pdb_deja_de_ser_sin_vocabulario(self):
        p = self._escribe("muestra.pdb", b"vIMGView")
        self.assertEqual(verificador.punto1_estado(p), "evaluado")

    def test_el_nombre_del_fichero_NO_decide_la_firma(self):
        """El motivo por el que F1 lo dejó fuera era cierto y medía otra cosa.

        Dos ficheros con nombres distintos y el mismo `type`+`creator` dan la
        misma firma; dos con el mismo nombre y distinto `type`+`creator` dan
        firmas distintas.
        """
        a = os.path.join(self.tmp.name, "a.pdb")
        b = os.path.join(self.tmp.name, "b.pdb")
        with open(a, "wb") as fh:
            fh.write(_palmdb(b"un_nombre_larguisimo_aqui", b"vIMGView"))
        with open(b, "wb") as fh:
            fh.write(_palmdb(b"x", b"vIMGView"))
        self.assertEqual(verificador.firma_real(a), verificador.firma_real(b))
        with open(b, "wb") as fh:
            fh.write(_palmdb(b"un_nombre_larguisimo_aqui", b"TEXtREAd"))
        self.assertNotEqual(verificador.firma_real(a), verificador.firma_real(b))

    def test_la_imagen_de_palm_no_se_despacha_como_libro(self):
        """Trampa 70: la firma alimenta al DESPACHADOR, no solo al punto 1."""
        self.assertEqual(verificador.CAT_POR_FIRMA["palm_imagen"], "imagen")
        self.assertEqual(verificador.CAT_POR_FIRMA["ereader"], "documento")
        self.assertEqual(verificador.CAT_POR_FIRMA["mobi"], "documento")


if __name__ == "__main__":
    unittest.main()

"""Pruebas de los cuatro pendientes del contrato: C19, C21, C27 y C29.

    python -m unittest pruebas.test_contrato_v -v

Cada prueba cita la medición de la que sale (`bench/contrato-familia-resvg.md`).
Las que comprueban una POLÍTICA y no una medición lo dicen.

Las cuatro pruebas que necesitan `ffmpeg` se saltan si no está: el contrato del
proyecto es que un fallo se reporte como fallo, no que se disfrace de rojo de
entorno.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filex import verificador as V  # noqa: E402

HAY_FFMPEG = shutil.which("ffmpeg") is not None
TIMEOUT = 180


def _ff(args):
    p = subprocess.run(["ffmpeg", "-y", "-v", "error", "-nostdin"] + args,
                       capture_output=True, timeout=TIMEOUT,
                       stdin=subprocess.DEVNULL)
    return p.returncode, p.stderr.decode("utf-8", "replace")[-300:]


# ===========================================================================
# C19 — A7: el quinto miembro de la familia de `resvg`
# ===========================================================================

@unittest.skipUnless(HAY_FFMPEG, "hace falta ffmpeg para fabricar el caso")
class CanalSilenciado(unittest.TestCase):
    """`bench/contrato-familia-resvg.md` §2.

    Audio estéreo con un canal silenciado hacia un destino CON PÉRDIDA. Antes
    de A7 pasaba los cinco puntos del contrato y las quince reglas de fidelidad:
    el contrato ve 2 canales, 44 100 Hz y 8,000 s, y A4/A5 se retiran porque el
    destino tiene pérdida y no hay PCM que comparar.
    """

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="filex_pru_a7_")
        cls.ent = os.path.join(cls.dir, "entrada.wav")
        # dos tonos DISTINTOS, uno por canal: con dos canales iguales el caso
        # no existiría, porque perder uno no se notaría en la energía del otro.
        rc, err = _ff(["-f", "lavfi", "-i",
                       "sine=frequency=440:duration=2:sample_rate=44100",
                       "-f", "lavfi", "-i",
                       "sine=frequency=880:duration=2:sample_rate=44100",
                       "-filter_complex",
                       "[0:a][1:a]join=inputs=2:channel_layout=stereo[a]",
                       "-map", "[a]", "-c:a", "pcm_s16le", cls.ent])
        assert rc == 0, err
        cls.malo = os.path.join(cls.dir, "malo.mp3")
        rc, err = _ff(["-i", cls.ent, "-af", "pan=stereo|c0=c0|c1=0*c0",
                       "-c:a", "libmp3lame", "-b:a", "192k", cls.malo])
        assert rc == 0, err
        cls.bueno = os.path.join(cls.dir, "bueno.mp3")
        rc, err = _ff(["-i", cls.ent, "-c:a", "libmp3lame", "-b:a", "192k",
                       cls.bueno])
        assert rc == 0, err

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def _reglas(self, salida, severidad):
        r = V.verificar_fidelidad(salida, {"params": {}}, self.ent)
        return r, sorted({h["regla"] for h in r["hallazgos"]
                          if h["severidad"] == severidad})

    def test_el_canal_mudo_hacia_destino_con_perdida_es_FALLO(self):
        r, fallos = self._reglas(self.malo, "fallo")
        self.assertIn("A7", fallos,
                      "A7 tiene que atrapar el canal silenciado; hallazgos: %r"
                      % r["hallazgos"])
        self.assertEqual(r["veredicto"], "fallo")

    def test_los_cinco_puntos_del_CONTRATO_siguen_sin_verlo(self):
        """Y esto NO es un defecto que arreglar: es la formulación de
        `contrato-quinto-punto.md` §4.4 funcionando. La energía de un canal no
        está declarada en ninguna cabecera. El contrato no puede, y por eso la
        regla vive en fidelidad."""
        c = V.verificar(self.malo, {"params": {}}, self.ent,
                        censo={"antes": {}, "despues": {}})
        self.assertEqual([h for h in c["hallazgos"]
                          if h["severidad"] in ("fallo", "aviso")], [])
        self.assertEqual(c["veredicto"], "ok")

    def test_la_conversion_BUENA_no_dispara_A7(self):
        r, fallos = self._reglas(self.bueno, "fallo")
        self.assertEqual(fallos, [])
        self.assertIs(r["cobertura"].get("A7"), True,
                      "A7 tiene que declararse CUBIERTA en el caso bueno, no "
                      "aprobada en silencio")

    def test_A7_no_opina_cuando_el_pedido_cambia_los_canales(self):
        """`canales` en el pedido = el usuario pidió mover la energía. A7 se
        declara NO CUBIERTA, que no es lo mismo que aprobada."""
        r = V.verificar_fidelidad(self.malo, {"params": {"canales": 2}}, self.ent)
        self.assertIs(r["cobertura"].get("A7"), False)
        self.assertEqual([h for h in r["hallazgos"]
                          if h["regla"] == "A7" and h["severidad"] == "fallo"], [])


class UmbralesDeA7(unittest.TestCase):
    """Los dos umbrales salen de 136 celdas medidas, no de la intuición
    (`bench/contrato-familia-resvg.md` §2.3). Esta prueba fija los márgenes:
    si alguien los mueve, tiene que volver a medir."""

    def test_el_umbral_de_audible_deja_fuera_el_canal_que_un_codec_puede_tirar(self):
        # MEDIDO: `mp3 -q:a 9` convierte un canal de -91,57 dBFS en -inf, y es
        # legítimo. Con un umbral de audible por debajo de eso, ese caso sería
        # un falso positivo.
        self.assertGreater(V.A7_AUDIBLE_DBFS, -91.57)

    def test_el_umbral_de_silencio_deja_pasar_el_peor_canal_legitimo(self):
        # MEDIDO: el peor nivel de salida de un canal audible en 132 celdas
        # legítimas es -51,52 dBFS (desigual30dB/mp38k, canal 2).
        self.assertLess(V.A7_SILENCIO_DBFS, -51.52)

    def test_A7_esta_declarada_entre_las_reglas_de_fidelidad(self):
        self.assertIn("A7", V.REGLAS_FIDELIDAD)


# ===========================================================================
# C21 — el suelo duro de V8
# ===========================================================================

class SueloDeV8(unittest.TestCase):
    """`bench/contrato-familia-resvg.md` §3, 48 celdas + las 6 del patrón oro.

    Se prueba con el PSNR inyectado en vez de fabricar vídeo: la regla que se
    quiere probar es la decisión de severidad, no `ffmpeg -lavfi psnr`, que ya
    lo prueban las 53. Es más rápido y no depende del codificador.
    """

    def setUp(self):
        self.psnr = None
        self._orig = V._ffmpeg_psnr
        V._ffmpeg_psnr = lambda s, e: ({"y": self.psnr}, None)

    def tearDown(self):
        V._ffmpeg_psnr = self._orig

    def _v8(self, y):
        self.psnr = y
        h = []
        # se llama la regla suelta: fidelidad_video haria antes V5/V2/V6, que
        # necesitan ficheros de verdad.
        d, _ = V._ffmpeg_psnr("x", "y")
        yy = d["y"]
        if yy < V.PSNR_SUELO_VIDEO:
            return "fallo"
        if yy < V.PSNR_MIN_VIDEO:
            return "aviso"
        return "informativo"

    def test_el_video_enteramente_negro_es_FALLO(self):
        # MEDIDO: 5,347 / 5,359 / 5,386 dB sobre los tres videos del corpus.
        for y in (5.347707, 5.359269, 5.385942):
            self.assertEqual(self._v8(y), "fallo", "%.3f dB" % y)

    def test_blanco_ruido_y_negativo_tambien(self):
        # MEDIDO: blanco 5,13-5,17 · negativo 7,15-7,25 · ruido 8,85-8,88.
        for y in (5.127122, 7.147192, 8.876563):
            self.assertEqual(self._v8(y), "fallo", "%.3f dB" % y)

    def test_la_recodificacion_agresiva_LEGITIMA_sigue_siendo_aviso(self):
        # MEDIDO: el peor caso legitimo sin filtro declarado es
        # tipico.mp4 -> x264 -b:v 20k = 19,843 dB. El suelo tiene que dejarlo
        # en `aviso`, que es lo que era.
        self.assertEqual(self._v8(19.843044), "aviso")
        self.assertEqual(self._v8(10.104628), "aviso",
                         "h264 en gris con contraste 40 sobre un clip en color: "
                         "10,10 dB es el peor legitimo MEDIDO de las 27 celdas")

    def test_el_peor_del_patron_oro_ni_se_acerca(self):
        # MEDIDO: trivial_mp4-to.webm = 29,63 dB, el minimo de las 6 salidas
        # del patron oro con video.
        self.assertEqual(self._v8(29.625658), "aviso")

    def test_el_suelo_no_puede_subir_sin_volver_a_medir(self):
        """Subirlo a 12, 15 o 18 dB atrapa EXACTAMENTE las mismas 12 celdas
        patologicas y anade 3 falsos positivos. Comprar cero deteccion con tres
        falsos positivos no es un cambio."""
        self.assertLessEqual(V.PSNR_SUELO_VIDEO, 10.10,
                             "por encima de 10,10 dB entra h264_2colores, que "
                             "es una conversion legitima medida")
        self.assertGreater(V.PSNR_SUELO_VIDEO, 8.88,
                           "por debajo de 8,88 dB se escapa el video de RUIDO")


# ===========================================================================
# C27 — G6 se queda en `aviso`, y hay cuatro casos que lo impiden
# ===========================================================================

class G6SigueSiendoAviso(unittest.TestCase):
    """`bench/contrato-familia-resvg.md` §4. NO se puede subir a `fallo`:
    `vda -> icb`, `vda -> vst`, `vda -> tga` y `vda -> vid` son conversiones
    LEGITIMAS entre alias de TGA y G6 dispara en las cuatro (MEDIDO). Y de
    siete motores probados, solo ImageMagick produce el fallo que G6 atrapa.
    """

    def test_la_severidad_de_G6_es_aviso(self):
        """Se monta el caso emblematico de verdad —un PNG entregado con una
        extension que el vocabulario no conoce— en vez de leer el fuente."""
        d = tempfile.mkdtemp(prefix="filex_pru_g6_")
        try:
            ent = os.path.join(d, "entrada.png")
            sal = os.path.join(d, "salida.zzz")
            png = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
                   b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
                   b"\x90wS\xde\x00\x00\x00\x00IEND\xaeB`\x82")
            for p in (ent, sal):
                with open(p, "wb") as fh:
                    fh.write(png)
            son, son_e = V.sondear(sal), V.sondear(ent)
            h = V.punto1_firma(sal, son, {"destino": "zzz"}, son_e)
            g6 = [x for x in h if x["regla"] == "G6"]
            self.assertEqual(len(g6), 1, "G6 tiene que dispararse: %r" % h)
            self.assertEqual(g6[0]["severidad"], "aviso",
                             "G6 tiene que seguir siendo `aviso`: subirla a "
                             "`fallo` tiene 4 falsos positivos medidos")
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_los_dos_casos_que_el_inventario_temia_no_pueden_disparar_G6(self):
        """REFUTADO: `png -> apng` y `mkv -> mka` NO son un riesgo para G6,
        porque G6 exige que la extension de destino NO este en el vocabulario y
        las dos SI estan. El riesgo real esta en otro sitio."""
        for ext in (".apng", ".mka"):
            self.assertIn(ext, V.EXT_A_FIRMAS)

    def test_el_riesgo_real_esta_en_los_alias_sin_marcador(self):
        # Los cuatro alias de TGA de ImageMagick: destino FUERA de EXT_A_FIRMAS
        # y misma firma por construccion. Ahi es donde G6 se equivoca.
        for ext in (".tga", ".vda", ".vst", ".icb"):
            self.assertNotIn(ext, V.EXT_A_FIRMAS)
            self.assertIn(ext, V.EXT_SIN_FIRMA)


# ===========================================================================
# C29 — el nivel de `familia`
# ===========================================================================

class NivelDeFamilia(unittest.TestCase):
    """`bench/contrato-familia-resvg.md` §5.

    C29 preguntaba si `familia` debe bajar el veredicto a `ok_parcial`. La
    respuesta empezo por un defecto: `EXT_FAMILIA` se construia sin `.split()`
    y contenia los CARACTERES de la cadena, no las extensiones. El nivel de
    familia era codigo muerto y la pregunta no se podia ni formular.
    """

    def test_EXT_FAMILIA_contiene_extensiones_y_no_caracteres(self):
        cortas = sorted(e for e in V.EXT_FAMILIA if len(e) <= 2)
        self.assertEqual(cortas, [],
                         "entradas de un caracter en EXT_FAMILIA: el bucle "
                         "esta iterando la cadena en vez de sus palabras")
        for e in (".csv", ".json", ".xml", ".html", ".md", ".txt", ".yaml"):
            self.assertIn(e, V.EXT_FAMILIA)

    def test_punto1_estado_devuelve_familia_donde_toca(self):
        self.assertEqual(V.punto1_estado("x.csv"), "familia")
        self.assertEqual(V.punto1_estado("x.json"), "familia")
        self.assertEqual(V.punto1_estado("x.png"), "evaluado")
        self.assertEqual(V.punto1_estado("x.group4"), "no_aplica")
        self.assertEqual(V.punto1_estado("x.zzz"), "sin_vocabulario")

    def test_familia_SIGUE_contando_como_cobertura(self):
        """La decision, con su numero: llevar `familia` a `ok_parcial` mueve 3
        de las 53 (5,7 %), y las tres son `.csv`/`.json`, que son justo las que
        la sonda `_datos` SI parsea entera (reglas D1/D2/D4/D5). Degradarlas
        seria el fallo de markitdown-mcp al reves: mentir por pesimismo."""
        import re
        fuente = open(V.__file__, encoding="utf-8").read()
        m = re.search(r'"1_firma":\s*_p1 in \(([^)]*)\)', fuente)
        self.assertIsNotNone(m, "no se encuentra la clave 1_firma de cobertura")
        self.assertIn('"familia"', m.group(1))

    def test_G5_se_emite_de_verdad_sobre_un_csv(self):
        d = tempfile.mkdtemp(prefix="filex_pru_g5_")
        try:
            p = os.path.join(d, "salida.csv")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("id,nombre\n1,uno\n2,dos\n")
            son = V.sondear(p)
            h = V.punto1_firma(p, son, {"destino": "csv"})
            self.assertIn("G5", [x["regla"] for x in h],
                          "antes del arreglo de EXT_FAMILIA, G5 no se emitia "
                          "NUNCA: ni una vez en las 53 ni en las 54 del "
                          "conjunto ancho")
            self.assertEqual([x["severidad"] for x in h if x["regla"] == "G5"],
                             ["informativo"])
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

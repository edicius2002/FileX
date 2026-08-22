"""Pruebas del hito 1. Biblioteca estándar, sin dependencias.

    python -m unittest discover -s pruebas -v

Cada prueba cita la medición de la que sale. Las que comprueban una POLÍTICA y
no una medición lo dicen: no todo lo que hay que probar está medido, pero sí hay
que saber cuál es cuál.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filex import formatos, invocacion  # noqa: E402
from filex.confinamiento import Confinamiento, Denegado, nombre_seguro  # noqa: E402
from filex.grafo import REAL, SIN_SONDEAR, Arista, Grafo  # noqa: E402
from filex.nucleo import FileX  # noqa: E402
from filex.trabajo import DirectorioDeTrabajo  # noqa: E402


class ElegirBien(unittest.TestCase):
    """El criterio de aceptación que de verdad demuestra la tesis del hito 1.

    «Explica por qué RECHAZA un camino que rasteriza cuando el destino admite
    texto.» Con los tres motores nativos de esta máquina **el caso no se puede
    montar**, porque ninguno escribe un formato con texto desde otro formato con
    texto salvo `pdf→pdf`, que es el mismo formato. Eso no es una excusa: es lo
    que midió `bench/fidelidad-caminos.md` §1.4 («dos de los tres ejemplos
    estrella son inalcanzables aquí»). Así que el mecanismo se prueba con un
    grafo sintético, y queda dicho que la prueba de integración necesita el
    motor documental del hito 5.
    """

    def setUp(self):
        # docx →(pandoc)→ pdf   conserva el texto
        # docx →(magick)→ png →(magick)→ pdf   lo rasteriza: mismo destino, un
        # salto MÁS, pero un grafo que cuente saltos elegiría el segundo si el
        # primero costara más.
        self.g = Grafo([
            Arista("docx", "pdf", "pandoc", estado=REAL, coste=5.0),
            Arista("docx", "png", "magick", estado=REAL, coste=1.0, rasteriza=True),
            Arista("png", "pdf", "magick", estado=REAL, coste=1.0),
        ])

    def test_prefiere_el_camino_que_conserva_el_texto_aunque_sea_mas_caro(self):
        d = self.g.camino("docx", "pdf")
        self.assertTrue(d.hay)
        self.assertEqual(d.camino.formatos, ["docx", "pdf"])
        self.assertFalse(d.camino.rasteriza)

    def test_y_dice_por_que_descarto_el_otro(self):
        d = self.g.camino("docx", "pdf")
        motivos = [m for _, m in d.rechazados]
        self.assertTrue(any("rasteriza" in m for m in motivos), motivos)
        self.assertTrue(any("admite texto" in m for m in motivos), motivos)

    def test_si_el_destino_NO_admite_texto_rasterizar_deja_de_ser_caro(self):
        # La penalización no es una fobia a rasterizar: es que el DESTINO admita
        # texto. Hacia png, el camino corto gana.
        d = self.g.camino("docx", "png")
        self.assertEqual(d.camino.formatos, ["docx", "png"])

    def test_si_el_unico_camino_rasteriza_no_se_calla(self):
        g = Grafo([
            Arista("svg", "png", "magick", estado=REAL, rasteriza=True),
            Arista("png", "pdf", "magick", estado=REAL),
        ])
        d = g.camino("svg", "pdf")
        self.assertTrue(d.hay)
        self.assertIn("ÚNICO camino", d.aviso)

    def test_una_transcodificacion_NO_es_una_recodificacion(self):
        """Regresión: la penalización por pérdida iba en la arista y estaba mal.

        `mkv→mp3` es UNA codificación con pérdida. Penalizarla por «origen con
        pérdida y destino con pérdida» hacía que el grafo prefiriera
        `mkv→flac→mp3`: un salto más, un intermedio enorme y exactamente la
        misma codificación al final. Lo que se cuenta son los saltos que
        ESCRIBEN con pérdida, y se perdona el primero.
        """
        g = Grafo([
            Arista("mkv", "mp3", "ffmpeg", estado=REAL),
            Arista("mkv", "flac", "ffmpeg", estado=REAL),
            Arista("flac", "mp3", "ffmpeg", estado=REAL),
        ])
        d = g.camino("mkv", "mp3")
        self.assertEqual(d.camino.formatos, ["mkv", "mp3"])

    def test_pero_dos_codificaciones_con_perdida_SI_se_penalizan(self):
        g = Grafo([
            Arista("wav", "mp3", "ffmpeg", estado=REAL, coste=1.0),
            Arista("wav", "opus", "ffmpeg", estado=REAL, coste=1.0),
            Arista("opus", "mp3", "ffmpeg", estado=REAL, coste=0.1),
        ])
        d = g.camino("wav", "mp3")
        self.assertEqual(d.camino.formatos, ["wav", "mp3"])

    def test_una_arista_sondeada_y_muerta_no_se_usa(self):
        # El 41,0 % de las aristas declaradas no existen. Marcarla `nominal` la
        # saca del grafo; no la deja «por si acaso».
        g = Grafo([
            Arista("a", "b", "m1", estado="nominal"),
            Arista("a", "c", "m2", estado=REAL),
            Arista("c", "b", "m2", estado=REAL),
        ])
        d = g.camino("a", "b")
        self.assertEqual(d.camino.formatos, ["a", "c", "b"])


class CuandoNoHayCamino(unittest.TestCase):
    """«Cuando no hay camino, explica por qué» — criterio de aceptación."""

    def test_nadie_escribe_el_destino(self):
        g = Grafo([Arista("png", "webp", "magick", estado=REAL)])
        d = g.camino("png", "docx")
        self.assertFalse(d.hay)
        self.assertIn("escribe", d.motivo)
        self.assertIn("docx", d.motivo)

    def test_nadie_lee_el_origen(self):
        g = Grafo([Arista("png", "webp", "magick", estado=REAL)])
        d = g.camino("psd", "webp")
        self.assertFalse(d.hay)
        self.assertIn("lee", d.motivo)

    def test_se_escribe_pero_desde_un_formato_inalcanzable(self):
        g = Grafo([
            Arista("png", "webp", "magick", estado=REAL),
            Arista("docx", "pdf", "pandoc", estado=REAL),
        ])
        d = g.camino("png", "pdf")
        self.assertFalse(d.hay)
        self.assertIn("docx", d.motivo)


class Confinar(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="filex-test-")
        self.permitido = os.path.join(self.base, "permitido")
        self.vecino = os.path.join(self.base, "permitido_secreto")
        os.makedirs(self.permitido, exist_ok=True)
        os.makedirs(self.vecino, exist_ok=True)
        self.c = Confinamiento([self.permitido])

    def test_R2_el_vecino_con_el_mismo_prefijo_NO_entra(self):
        # Sin el `+ os.sep`, la raíz `permitido` deja pasar `permitido_secreto`.
        f = os.path.join(self.vecino, "x.txt")
        open(f, "w").close()
        with self.assertRaises(Denegado):
            self.c.resolver(f)

    def test_lo_que_esta_dentro_si_entra(self):
        f = os.path.join(self.permitido, "x.txt")
        open(f, "w").close()
        self.assertTrue(self.c.puede_leer(f))

    def test_R4_prohibido_y_no_existe_dan_EL_MISMO_mensaje(self):
        # Distinguirlos convierte el conversor en un oráculo de existencia del
        # disco ajeno. Tres fugas distintas se midieron por no hacerlo.
        try:
            self.c.resolver(os.path.join(self.vecino, "existe_no.txt"))
        except Denegado as e:
            m1 = str(e)
        try:
            self.c.resolver(os.path.join(self.permitido, "..", "fuera.txt"))
        except Denegado as e:
            m2 = str(e)
        self.assertEqual(m1, m2)
        self.assertNotIn(self.base, m1)  # y no filtra la ruta

    def test_R17_una_ruta_absurdamente_larga_se_rechaza_SIN_tocar_el_disco(self):
        # `realpath` es un vector de DoS: ~6.000 componentes cuestan 5-16 s.
        larga = os.path.join(self.permitido, *(["a"] * 500))
        with self.assertRaises(Denegado):
            self.c.resolver(larga)

    def test_R6_sin_raices_no_se_arranca(self):
        with self.assertRaises(ValueError):
            Confinamiento([])

    def test_R12_nombres_de_salida(self):
        self.assertTrue(nombre_seguro("salida.webp"))
        self.assertFalse(nombre_seguro(".."))
        self.assertFalse(nombre_seguro("a/b.png"))
        if sys.platform == "win32":
            self.assertFalse(nombre_seguro("x.txt:oculto"))  # ADS: W9 lo concedió
            self.assertFalse(nombre_seguro("CON.txt"))
            self.assertFalse(nombre_seguro("x.png."))


class Invocar(unittest.TestCase):
    def test_una_cadena_no_es_argv(self):
        # Aceptarla implicaría shell. morphos usa `bash -c` y tiene RCE.
        with self.assertRaises(TypeError):
            invocacion.ejecutar("echo hola")

    def test_un_binario_que_no_existe_no_revienta_se_informa(self):
        r = invocacion.ejecutar(["binario-que-no-existe-jamas"])
        self.assertFalse(r.ok)
        self.assertFalse(r.arrancado)
        self.assertEqual(r.motivo, "motor_no_disponible")

    def test_el_motivo_no_lleva_stderr(self):
        # «Nunca devolver stderr crudo al modelo»: el error de un motor puede
        # dirigir la siguiente acción del agente.
        r = invocacion.ejecutar([sys.executable, "-c",
                                 "import sys; sys.stderr.write('RUTA/SECRETA'); sys.exit(3)"])
        self.assertEqual(r.rc, 3)
        self.assertIn("RUTA/SECRETA", r.err)      # está, para el log
        self.assertNotIn("SECRETA", r.motivo)     # no está, para el modelo

    def test_hay_timeout_y_mata(self):
        r = invocacion.ejecutar([sys.executable, "-c", "import time; time.sleep(30)"],
                                timeout=1.5)
        self.assertTrue(r.agotado)
        self.assertFalse(r.ok)
        self.assertEqual(r.motivo, "tiempo_agotado")

    def test_stdin_esta_cerrado(self):
        # La defensa real. MEDIDO: con `-y` y ruta nueva, 2 de 5 se colgaron
        # heredando la tubería; con DEVNULL, 0 de 5.
        r = invocacion.ejecutar([sys.executable, "-c",
                                 "import sys; print(repr(sys.stdin.read()))"],
                                timeout=10)
        self.assertTrue(r.ok)
        self.assertIn("''", r.salida_txt)


class PuntoCinco(unittest.TestCase):
    """Lo que ningún competidor comprueba: ¿escribió el motor fuera de lo declarado?"""

    def test_el_censo_ve_lo_que_nadie_pidio(self):
        with DirectorioDeTrabajo() as t:
            open(t.destino("salida.webp"), "wb").write(b"x")
            open(t.destino("chunk-stream0-00001.m4s"), "wb").write(b"y" * 100)
            sobra = t.sobrantes(["salida.webp"])
        self.assertIn("chunk-stream0-00001.m4s", sobra)
        self.assertEqual(sobra["chunk-stream0-00001.m4s"], 100)

    def test_el_desechable_se_borra_entero(self):
        t = DirectorioDeTrabajo()
        ruta = t.ruta
        open(t.destino("basura.bin"), "wb").write(b"x")
        t.__exit__(None, None, None)
        self.assertFalse(os.path.exists(ruta))

    def test_el_censo_sobrevive_al_borrado(self):
        # El punto 5 no se puede verificar a posteriori: si el censo muriera con
        # el directorio, no habría punto 5.
        t = DirectorioDeTrabajo()
        open(t.destino("a.png"), "wb").write(b"x")
        c = t.censo()
        t.cerrar()
        clave = os.path.abspath(t.ruta)
        self.assertIn("a.png", c["despues"][clave])


class Formatos(unittest.TestCase):
    def test_los_que_admiten_texto_estan_marcados(self):
        for e in ("pdf", "docx", "svg", "html", "csv"):
            self.assertTrue(formatos.formato(e).texto, e)
        for e in ("png", "jpg", "mp4", "mp3"):
            self.assertFalse(formatos.formato(e).texto, e)

    def test_jpeg_no_tiene_alfa_ni_mas_de_8_bits(self):
        f = formatos.formato("jpg")
        self.assertFalse(f.alfa)
        self.assertEqual(f.prof_max, 8)

    def test_png_conserva_16_bits(self):
        # MEDIDO: RMSE 0 frente al TIFF. Si un conversor entrega 8 bits es un
        # FALLO del motor, no una limitación del formato.
        self.assertEqual(formatos.formato("png").prof_max, 16)

    def test_alias(self):
        self.assertEqual(formatos.normaliza(".JPEG"), "jpg")
        self.assertEqual(formatos.normaliza("TIFF"), "tif")


class Integracion(unittest.TestCase):
    """Contra los motores reales de esta máquina. Se salta lo que no haya."""

    @classmethod
    def setUpClass(cls):
        cls.fx = FileX()
        cls.raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_se_sondean_los_motores_en_ejecucion(self):
        # «Sondear capacidades en ejecución, no deducirlas.»
        for m in self.fx.disponibles:
            self.assertTrue(m.version, f"{m.nombre} sin versión sondeada")

    def test_un_motor_ausente_no_tumba_nada(self):
        self.assertIsInstance(self.fx.ausentes, list)
        self.assertGreater(len(self.fx.disponibles), 0)

    def test_conversion_real_con_contrato(self):
        ent = os.path.join(self.raiz, "corpus", "imagen", "tipico.png")
        if not os.path.isfile(ent):
            self.skipTest("falta el corpus")
        d = tempfile.mkdtemp(prefix="filex-test-")
        sal = os.path.join(d, "salida.webp")
        c = self.fx.convertir(ent, sal)
        self.assertTrue(c.ok, c.motivo)
        self.assertTrue(os.path.isfile(sal))
        self.assertIn(c.veredicto, ("ok", "ok_parcial"))
        # Y el punto 5 tiene que estar CUBIERTO, no dado por bueno.
        self.assertTrue(c.saltos[-1].cobertura.get("5_escritura"))

    def test_ruta_inexistente_da_el_mensaje_opaco(self):
        c = self.fx.convertir("no_existe_jamas.png", "x.webp")
        self.assertFalse(c.ok)
        self.assertEqual(c.motivo, "ruta no accesible")


if __name__ == "__main__":
    unittest.main(verbosity=2)

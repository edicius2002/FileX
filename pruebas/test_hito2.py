"""Hito 2 — NVENC con sondeo y degradación, y N7 (el lock de GPU en el paquete).

Las pruebas que tocan la tarjeta se **saltan solas** si no hay `ffmpeg` o si no
hay `nvidia-smi`: la suite tiene que correr en una máquina sin GPU igual que se
salta las de Docker.

Y una disciplina que este hito pagó: **las pruebas de comportamiento no bastan.**
`ReleaseMutex` desde otro hilo «funciona» por accidente (trampa 40) y un arnés
que espera a la condición equivocada sale verde (trampa 38). Aquí se comprueba
además el MECANISMO: qué `rc` devolvió el sondeo, si la condición se dio, y que
las dos fuentes comparadas compilan.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filex import formatos, gpu, motores  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(RAIZ, "corpus", "video")


def _hay(binario):
    try:
        subprocess.run([binario, "-version"] if binario != "nvidia-smi" else
                       [binario, "--version"], stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=30)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


HAY_FFMPEG = _hay("ffmpeg")
HAY_GPU = _hay("nvidia-smi")


def _ffmpeg():
    m = [c for c in motores.MOTORES if c.__name__ == "FFmpeg"][0]()
    m.sondear()
    return m


# ==========================================================================
class TablaDeCodecs(unittest.TestCase):
    """Lo que se puede comprobar sin tocar la tarjeta."""

    def test_toda_familia_tiene_una_salida_de_cpu(self):
        """**El criterio del hito es «degrada sin intervención», y eso exige que
        haya adónde degradar.** Una familia cuyos candidatos sean todos de NVENC
        no degradaría: lanzaría."""
        for fam, cands in motores.CODECS_VIDEO.items():
            with self.subTest(fam=fam):
                self.assertTrue(any("nvenc" not in c for c in cands),
                                f"'{fam}' no tiene salida de CPU: {cands}")

    def test_todo_candidato_tiene_control_de_tasa(self):
        """El fallo que casi se publica como hito cumplido: degradar el códec
        sin degradar sus banderas. `libsvtav1` no admite `-maxrate`."""
        for fam, cands in motores.CODECS_VIDEO.items():
            for c in cands:
                with self.subTest(codec=c):
                    self.assertIn(c, motores.FAMILIA_TASA)
                    self.assertIn(motores.FAMILIA_TASA[c], motores._TASA)

    def test_svtav1_no_lleva_maxrate(self):
        """MEDIDO: `Svt[error]: Max Bitrate only supported with CRF mode`,
        `rc=-22` y **0 bytes**. La regresión que esto vigila es real."""
        por_bitrate, _ = motores._TASA[motores.FAMILIA_TASA["libsvtav1"]]
        flags = por_bitrate(2000000)
        self.assertNotIn("-maxrate", flags)
        self.assertNotIn("-bufsize", flags)
        self.assertIn("-b:v", flags)

    def test_nvenc_si_lleva_maxrate(self):
        """El control de la anterior: si ninguna familia llevara `-maxrate`, la
        prueba de arriba pasaría sin decir nada."""
        por_bitrate, _ = motores._TASA[motores.FAMILIA_TASA["hevc_nvenc"]]
        self.assertIn("-maxrate", por_bitrate(2000000))

    def test_alias_de_codec(self):
        for entrada, esperado in (("h265", "hevc"), ("  H265 ", "hevc"),
                                  ("x265", "hevc"), ("hevc", "hevc"),
                                  ("av1", "av1"), ("AV1", "av1")):
            self.assertEqual(motores.codec_normaliza(entrada), esperado)

    def test_bitrate_a_bps(self):
        self.assertEqual(motores._a_bps("2000k"), 2000000)
        self.assertEqual(motores._a_bps("2M"), 2000000)
        self.assertEqual(motores._a_bps(2000000), 2000000)
        self.assertEqual(motores._a_bps("1.5M"), 1500000)

    def test_la_sonda_no_usa_un_lienzo_pequeno(self):
        """**La trampa medida de este hito.** `hevc_nvenc` exige 129x33 y
        `h264_nvenc` 145x49 (bisección, `sonda_frontera.json`): una sonda de
        64x64 declara averiados los dos codificadores que SÍ funcionan, con
        `rc=-22` indistinguible de una avería real."""
        w, h = (int(x) for x in gpu.SONDA_LIENZO.split("x"))
        self.assertGreaterEqual(w, 145, "el lienzo no llega al mínimo de h264_nvenc")
        self.assertGreaterEqual(h, 49, "el lienzo no llega al mínimo de h264_nvenc")

    def test_la_sonda_lleva_el_tope_dentro_de_la_orden(self):
        """Trampa 52: `lavfi` genera flujo infinito y el tope del cliente no
        basta — un `ffmpeg` huérfano sobrevivió 9 minutos."""
        self.assertGreaterEqual(gpu.SONDA_FRAMES, 1)


# ==========================================================================
@unittest.skipUnless(HAY_FFMPEG, "no hay ffmpeg")
class SondeoEnEjecucion(unittest.TestCase):

    def setUp(self):
        gpu.olvidar()

    def tearDown(self):
        gpu.olvidar()

    def test_av1_nvenc_esta_listado_y_no_funciona(self):
        """La premisa del hito, comprobada por los DOS lados: si algún día la
        tarjeta ganara codificador AV1, esta prueba lo diría en vez de que el
        código siguiera degradando sin motivo."""
        r = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"],
                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=60)
        self.assertIn("av1_nvenc", r.stdout.decode("utf-8", "replace"),
                      "av1_nvenc ya no aparece listado: la premisa cambió")
        if not HAY_GPU:
            self.skipTest("sin tarjeta no se puede sondear")
        ok, rc, motivo = gpu.capacidad("av1_nvenc")
        self.assertFalse(ok, f"av1_nvenc FUNCIONA ahora (rc={rc}): revisa el hito 2")
        # El `rc` es la respuesta, no una pista (trampa 72): se comprueba CUAL.
        self.assertEqual(rc, gpu.AVERROR_EXTERNAL,
                         f"falla, pero por otro motivo: rc={rc} ({motivo})")

    @unittest.skipUnless(HAY_GPU, "no hay tarjeta")
    def test_hevc_nvenc_si_funciona(self):
        ok, rc, motivo = gpu.capacidad("hevc_nvenc")
        self.assertTrue(ok, f"hevc_nvenc no abre: rc={rc} ({motivo})")

    @unittest.skipUnless(HAY_GPU, "no hay tarjeta")
    def test_un_lienzo_pequeno_da_falso_negativo(self):
        """El mecanismo de la trampa, reproducido. **No basta con que la sonda
        acierte: hay que demostrar que la variante ingenua falla**, o la
        constante `SONDA_LIENZO` es cosmética."""
        antes = gpu.SONDA_LIENZO
        try:
            gpu.SONDA_LIENZO = "64x64"
            gpu.olvidar()
            ok, rc, _ = gpu.capacidad("hevc_nvenc")
            self.assertFalse(ok, "con 64x64 hevc_nvenc ya no da falso negativo: "
                                 "la trampa dejó de existir y sobra la constante")
            self.assertEqual(rc, gpu.EINVAL)
        finally:
            gpu.SONDA_LIENZO = antes
            gpu.olvidar()

    @unittest.skipUnless(HAY_GPU, "no hay tarjeta")
    def test_la_capacidad_se_cachea(self):
        gpu.capacidad("hevc_nvenc")
        self.assertIn("hevc_nvenc", gpu._CACHE)
        gpu.olvidar()
        self.assertNotIn("hevc_nvenc", gpu._CACHE)


# ==========================================================================
@unittest.skipUnless(HAY_FFMPEG, "no hay ffmpeg")
class DegradacionSinIntervencion(unittest.TestCase):
    """El criterio del hito 2, punto por punto."""

    def setUp(self):
        gpu.olvidar()
        self.m = _ffmpeg()

    def tearDown(self):
        gpu.olvidar()

    def test_hevc_usa_nvenc_por_defecto(self):
        gpu._CACHE["hevc_nvenc"] = (True, 0, "")
        info = self.m.elegir_codec("hevc")
        self.assertEqual(info["codec_video_real"], "hevc_nvenc")
        self.assertTrue(info["nvenc"])
        self.assertEqual(info["degradado_de"], "")

    def test_av1_degrada_a_libsvtav1_y_lo_declara(self):
        gpu._CACHE["av1_nvenc"] = (False, gpu.AVERROR_EXTERNAL, "sin codificador")
        info = self.m.elegir_codec("av1")
        self.assertEqual(info["codec_video_real"], "libsvtav1")
        self.assertFalse(info["nvenc"])
        self.assertEqual(info["degradado_de"], "av1_nvenc")
        # El `rc` viaja con la degradación: sin él, «0 bytes» no distingue una
        # tarjeta incapaz de un proceso que no arrancó (trampa 25).
        self.assertEqual(info["degradado_rc"], gpu.AVERROR_EXTERNAL)

    def test_hevc_degrada_a_libx265_si_la_tarjeta_falla(self):
        gpu._CACHE["hevc_nvenc"] = (False, gpu.AVERROR_EXTERNAL, "sin codificador")
        info = self.m.elegir_codec("hevc")
        self.assertEqual(info["codec_video_real"], "libx265")

    def test_el_argv_degradado_no_lleva_banderas_del_codec_anterior(self):
        gpu._CACHE["av1_nvenc"] = (False, gpu.AVERROR_EXTERNAL, "sin codificador")
        argv, dec = self.m.orden("e.mp4", "s.mkv",
                                 {"codec_video": "av1", "bitrate_video": "2000k"})
        self.assertIn("libsvtav1", argv)
        self.assertNotIn("-maxrate", argv)
        self.assertNotIn("-rc", argv)
        self.assertEqual(dec["degradado_de"], "av1_nvenc")

    def test_map_0_explicito_sigue_estando(self):
        """Regla no negociable del proyecto: sin `-map 0` ffmpeg descarta la
        segunda pista de audio en silencio."""
        gpu._CACHE["hevc_nvenc"] = (True, 0, "")
        argv, _ = self.m.orden("e.mkv", "s.mkv", {"codec_video": "hevc"})
        self.assertIn("-map", argv)
        self.assertEqual(argv[argv.index("-map") + 1], "0")

    def test_el_bitrate_pedido_va_a_los_metadatos_de_salida(self):
        gpu._CACHE["hevc_nvenc"] = (True, 0, "")
        argv, _ = self.m.orden("e.mp4", "s.mkv",
                               {"codec_video": "hevc", "bitrate_video": "2000k"})
        i = argv.index("-metadata")
        self.assertIn("filex.bitrate_pedido_bps=2000000", argv[i + 1])
        self.assertIn("filex.codec=hevc_nvenc", argv[i + 1])

    def test_la_degradacion_va_a_los_metadatos_de_salida(self):
        gpu._CACHE["av1_nvenc"] = (False, gpu.AVERROR_EXTERNAL, "x")
        argv, _ = self.m.orden("e.mp4", "s.mkv", {"codec_video": "av1"})
        i = argv.index("-metadata")
        self.assertIn("filex.degradado_de=av1_nvenc", argv[i + 1])

    def test_el_bitrate_de_video_no_usa_la_clave_del_contrato(self):
        """`bitrate_bps` la lee la regla de bitrate del contrato, **que solo
        mira pistas de AUDIO**. Poner ahí los 2 Mbps de vídeo compararía el
        audio de 128 kbps contra 2 000 kbps: `fallo` sobre una salida buena."""
        gpu._CACHE["hevc_nvenc"] = (True, 0, "")
        _argv, dec = self.m.orden("e.mp4", "s.mkv",
                                  {"codec_video": "hevc", "bitrate_video": "2000k"})
        self.assertIn("bitrate_video_bps", dec)
        self.assertNotIn("bitrate_bps", dec)

    def test_el_bitrate_de_audio_se_publica_en_decidido(self):
        """N28: V10 necesita restar el audio que este mismo argv codifica."""
        gpu._CACHE["hevc_nvenc"] = (True, 0, "")
        _argv, dec = self.m.orden("e.mp4", "s.mkv",
                                  {"codec_video": "hevc", "bitrate_video": "2000k",
                                   "bitrate_audio": "96k"})
        self.assertEqual(dec.get("bitrate_audio_bps"), 96_000)

    def test_codec_desconocido_no_pasa_en_silencio(self):
        with self.assertRaises(ValueError):
            self.m.elegir_codec("no_existe_este_codec")

    def test_sin_codec_video_el_argv_no_cambia(self):
        """**La red de seguridad de las 210 aristas ya medidas.** El hito 2 no
        puede mover ni una: quien no pida `codec_video` recibe exactamente lo
        que recibía."""
        argv = self.m.orden("e.mp4", "s.mkv", {})
        self.assertIn("libx264", argv)
        self.assertNotIn("-metadata", argv)


# ==========================================================================
@unittest.skipUnless(HAY_FFMPEG, "no hay ffmpeg")
class ConversionDeVerdad(unittest.TestCase):
    """Punta a punta. Un argv correcto no es una conversión correcta: la propia
    degradación de este hito producía un argv impecable y 0 bytes."""

    def setUp(self):
        gpu.olvidar()
        self.tmp = tempfile.mkdtemp(prefix="test-hito2-")
        self.ent = os.path.join(CORPUS, "trivial.mp4")
        if not os.path.isfile(self.ent):
            self.skipTest("falta el corpus (¿punteros de LFS? `git lfs checkout`)")

    def tearDown(self):
        import shutil
        gpu.olvidar()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _convierte(self, pedido):
        from filex.nucleo import FileX
        fx = FileX(raices_lectura=[CORPUS, self.tmp],
                   raices_escritura=[self.tmp])
        sal = os.path.join(self.tmp, "s.mkv")
        return fx.convertir(self.ent, sal, pedido), sal

    def test_av1_produce_un_fichero_con_bytes(self):
        """La comprobación que faltaba: `rc=0` **no basta** — la primera versión
        de la degradación devolvía un fichero de 0 bytes."""
        c, sal = self._convierte({"codec_video": "av1", "bitrate_video": "1000k"})
        self.assertTrue(c.ok, c.motivo)
        self.assertGreater(os.path.getsize(sal), 0, "0 bytes con rc=0")

    @unittest.skipUnless(HAY_GPU, "no hay tarjeta")
    def test_hevc_produce_un_fichero_con_bytes(self):
        c, sal = self._convierte({"codec_video": "hevc", "bitrate_video": "1000k"})
        self.assertTrue(c.ok, c.motivo)
        self.assertGreater(os.path.getsize(sal), 0)

    def test_las_dos_pistas_de_audio_sobreviven(self):
        """`corpus/video/patologico_2pistas.mkv` existe para vigilar `-map 0`."""
        ent = os.path.join(CORPUS, "patologico_2pistas.mkv")
        if not os.path.isfile(ent):
            self.skipTest("falta el corpus")
        from filex.nucleo import FileX
        fx = FileX(raices_lectura=[CORPUS, self.tmp], raices_escritura=[self.tmp])
        sal = os.path.join(self.tmp, "dos.mp4")
        c = fx.convertir(ent, sal, {"codec_video": "hevc", "bitrate_video": "1000k"})
        self.assertTrue(c.ok, c.motivo)
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a",
                            "-show_entries", "stream=index", "-of", "csv=p=0", sal],
                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           timeout=120)
        pistas = [x for x in r.stdout.decode().split() if x.strip()]
        self.assertEqual(len(pistas), 2, f"se perdió una pista de audio: {pistas}")


# ==========================================================================
class LockDeGpu(unittest.TestCase):
    """N7 — el lock del paquete tiene que ser EL MISMO que el del arnés."""

    def setUp(self):
        gpu._PROFUNDIDAD = 0
        self.tmp = tempfile.mkdtemp(prefix="test-h2-lock-")
        self.ruta = os.path.join(self.tmp, "filex-gpu.lock")

    def tearDown(self):
        import shutil
        gpu._PROFUNDIDAD = 0
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_el_fichero_por_defecto_es_el_del_arnes(self):
        """`bench/lib/harness.sh` usa `$GPU_LOCK` o `/tmp/filex-gpu.lock`, que
        en este Git Bash **es `%TEMP%`**. Si los dos nombres no coinciden, los
        dos locks no se ven aunque el primitivo sea el mismo."""
        antes = os.environ.pop("GPU_LOCK", None)
        try:
            self.assertEqual(os.path.basename(gpu.fichero_lock()),
                             "filex-gpu.lock")
            self.assertEqual(os.path.dirname(gpu.fichero_lock()),
                             tempfile.gettempdir())
        finally:
            if antes is not None:
                os.environ["GPU_LOCK"] = antes

    def test_el_primitivo_es_creacion_exclusiva(self):
        """MEDIDO: un candado de rango de bytes **no** excluye a un
        `set -o noclobber`, y el arnés usa `noclobber`. La prueba mira el
        MECANISMO —que el fichero exista basta para bloquear— porque una prueba
        de comportamiento con los dos en Python pasaría con cualquiera de los
        dos primitivos (trampa 40)."""
        with open(self.ruta, "w", encoding="utf-8") as f:
            f.write("otro\t1\t1\tninguno\t0\t/tmp\n")
        gpu._PROFUNDIDAD = 0
        l = gpu.Lock("yo", ruta=self.ruta)
        self.assertFalse(l._intentar(),
                         "un fichero existente NO bloqueó: el primitivo no es "
                         "O_CREAT|O_EXCL y no excluiría al arnés")

    def test_el_formato_del_fichero_es_el_del_arnes(self):
        """Seis campos separados por tabulador. El arnés lee el 3 y el 4 para
        decidir si el dueño vive, y el 2 para no robarle el lock a otro: si
        cambia el orden, `harness.sh` roba locks vivos."""
        l = gpu.Lock("etiqueta-prueba", ruta=self.ruta)
        self.assertTrue(l.tomar())
        try:
            campos = open(self.ruta, encoding="utf-8").readline().rstrip("\n").split("\t")
            self.assertEqual(len(campos), 6, campos)
            self.assertEqual(campos[0], "etiqueta-prueba")
            self.assertEqual(campos[1], str(os.getpid()))
            self.assertEqual(campos[2], str(os.getpid()))
            self.assertTrue(campos[3])
            self.assertTrue(campos[4].isdigit())
        finally:
            l.soltar()

    def test_no_roba_un_lock_de_dueno_vivo(self):
        with open(self.ruta, "w", encoding="utf-8") as f:
            f.write(f"otro\t{os.getpid()}\t{os.getpid()}\t"
                    f"{os.path.basename(sys.executable)}\t0\t/tmp\n")
        gpu._PROFUNDIDAD = 0
        l = gpu.Lock("yo", ruta=self.ruta)
        self.assertFalse(l.tomar(espera=0.0))

    def test_recoge_un_huerfano_con_espera_cero(self):
        """**El reintento inmediato.** Sin él, recoger el huérfano y salir por
        el tope en la misma vuelta devolvía `False` habiendo dejado el lock
        libre, y la recogida no servía nunca con `espera=0`."""
        with open(self.ruta, "w", encoding="utf-8") as f:
            f.write("muerto\t999999\t999999\tningun_proceso.exe\t0\t/tmp\n")
        gpu._PROFUNDIDAD = 0
        l = gpu.Lock("yo", ruta=self.ruta)
        self.assertTrue(l.tomar(espera=0.0))
        l.soltar()

    def test_es_reentrante_dentro_del_proceso(self):
        """Un lote toma el lock para toda la tanda y luego pide `capacidad()`.
        Sin reentrancia se bloquearía contra sí mismo y **cachearía un «no»
        falso**: la defensa produciría el fallo que venía a evitar."""
        a = gpu.Lock("a", ruta=self.ruta)
        self.assertTrue(a.tomar())
        try:
            self.assertTrue(gpu.poseido())
            b = gpu.Lock("b", ruta=self.ruta)
            self.assertTrue(b.tomar(espera=0.0))
            b.soltar()
            self.assertTrue(os.path.exists(self.ruta),
                            "la reentrada borró el lock al soltarse")
        finally:
            a.soltar()
        self.assertFalse(os.path.exists(self.ruta))
        self.assertFalse(gpu.poseido())

    def test_usa_gpu_detecta_nvenc_en_el_argv(self):
        self.assertTrue(gpu.usa_gpu(["ffmpeg", "-c:v", "hevc_nvenc"]))
        self.assertTrue(gpu.usa_gpu(["ffmpeg", "-hwaccel", "cuda"]))
        self.assertFalse(gpu.usa_gpu(["ffmpeg", "-c:v", "libx265"]))

    @unittest.skipUnless(HAY_GPU, "no hay tarjeta")
    def test_la_guardia_decide_por_vram_libre_total(self):
        """Trampa 31: por PID no es observable en esta máquina."""
        self.assertIsNotNone(gpu.vram_libre_mib())
        estado, motivo = gpu.ocupacion_ajena()
        self.assertIn(estado, (0, 1, 2))
        self.assertTrue(motivo)

    def test_los_umbrales_son_los_del_arnes(self):
        self.assertEqual(gpu.LIBRE_MIN_MIB, 6000)
        self.assertEqual(gpu.LIBRE_AVISO_MIB, 7500)


# ==========================================================================
class ElFormatoHevcNoEsUnaExtension(unittest.TestCase):
    """El criterio dice «cuando el destino es HEVC» y HEVC **no es un destino**
    en este grafo: es un códec dentro de `mkv`, `mp4` o `mov`. Queda escrito
    como prueba para que nadie añada un `Formato("hevc", ...)` creyendo que
    cierra el hito."""

    def test_hevc_no_es_un_formato(self):
        self.assertIsNone(formatos.formato("hevc"))
        self.assertIsNone(formatos.formato("h265"))

    def test_se_pide_por_parametro_no_por_extension(self):
        self.assertIn("hevc", motores.CODECS_VIDEO)


if __name__ == "__main__":
    unittest.main()

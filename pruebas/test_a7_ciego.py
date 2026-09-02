"""N18 — A7 declara su punto ciego en vez de aprobar lo que no puede ver.

    python -m unittest pruebas.test_a7_ciego -v

De dónde sale, y por qué es un fichero nuevo. `bench/contrato-familia-resvg.md`
§2.5 midió que por debajo de 48 kb/s Opus **rellena** el canal mudo con una copia
del otro, así que A7 —que mira RMS por canal— no puede opinar; y aun así
devolvía `cobertura A7 = True`, es decir un aprobado que nadie había examinado.

**Y el nombre del punto ciego estaba mal, que es lo que decide dónde se declara
— MEDIDO** (`bench/fidelidad-y-nucleo.md` §2.4, 264 celdas). Sobre el MISMO
fallo y a la MISMA tasa de 32 kb/s, `libmp3lame` y `aac` atrapan **6 de 6** y
`libopus` **1 de 6**. No es «bitrate bajo»: es que Opus colapsa el estéreo a
mono. Por eso estas pruebas comprueban las dos direcciones — que se declara
donde toca **y que no se declara donde no toca**—: una regla que se declarase
ciega en todo sería tan inútil como una que no se declarase nunca.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from filex import verificador as V  # noqa: E402

CORPUS = os.path.join(RAIZ, "corpus", "audio")
JFK = os.path.join(CORPUS, "habla_jfk.flac")
LARGO = os.path.join(CORPUS, "habla_largo.flac")
TOPE = 300
DUR = 8.0


def _ff(argv):
    return subprocess.run(["ffmpeg", "-y", "-v", "error", "-nostdin"] + argv,
                          capture_output=True, timeout=TOPE,
                          stdin=subprocess.DEVNULL)


def _es_audio_real(ruta: str) -> bool:
    """`os.path.exists` es TRUE también para un puntero de Git LFS sin
    descargar (~130 B de texto) -- trampa 34, aquí sin proteger. Con
    `actions/checkout: lfs: false` el runner de Linux tiene el puntero, no el
    audio, y `setUpClass` revienta con un `ffmpeg` que no encuentra un flujo
    que decodificar: eso es el "0 pruebas corridas, 1 error de carga" de
    `ci/linux-apto.json` (C42, bench/ci-y-contrato.md §1), no un fallo del
    corpus en sí. Un FLAC real de este proyecto pesa >1 MB; el umbral de
    100 KB deja margen de sobra sin acercarse al tamaño de un puntero."""
    try:
        return os.path.getsize(ruta) > 100_000
    except OSError:
        return False


HAY_FFMPEG = shutil.which("ffmpeg") is not None


@unittest.skipUnless(
    HAY_FFMPEG and _es_audio_real(JFK) and _es_audio_real(LARGO),
    "hace falta ffmpeg y el corpus de audio REAL (no un puntero de Git LFS "
    "sin `git lfs checkout` -- trampa 34)")
class PuntoCiegoDeA7(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="filex-a7ciego-")
        # Estéreo de canales DESIGUALES: dos voces distintas. Con canales
        # iguales el colapso a mono no esconde nada y el caso no existe
        # (trampa 50: varía la entrada).
        cls.est = os.path.join(cls.dir, "est.wav")
        _ff(["-i", JFK, "-i", LARGO, "-filter_complex",
             "[0:a]pan=mono|c0=c0,atrim=0:%.1f[l];"
             "[1:a]pan=mono|c0=c0,atrim=60:%.1f,asetpts=PTS-STARTPTS[r];"
             "[l][r]join=inputs=2:channel_layout=stereo" % (DUR, 60 + DUR),
             "-t", str(DUR), "-ar", "48000", "-c:a", "pcm_s16le", cls.est])
        cls.mono = os.path.join(cls.dir, "mono.wav")
        _ff(["-i", JFK, "-t", str(DUR), "-ac", "1", "-ar", "48000",
             "-c:a", "pcm_s16le", cls.mono])
        # **La condición que digo reproducir tiene que darse** (trampa 38): la
        # primera versión de este montaje dejó la fuente estéreo VACÍA y las
        # celdas parecían decir «el cambio no toca nada».
        cls.hay_fuente = (os.path.exists(cls.est)
                          and os.path.getsize(cls.est) > 1_000_000)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def setUp(self):
        if not self.hay_fuente:
            self.skipTest("no se pudo fabricar la fuente estéreo")

    def _codificar(self, fuente, nombre, argv):
        dst = os.path.join(self.dir, nombre)
        r = _ff(["-i", fuente] + argv + [dst])
        self.assertEqual(r.returncode, 0, r.stderr[-300:])
        self.assertGreater(os.path.getsize(dst), 1000)
        return dst

    def _cobertura(self, fuente, salida):
        f = V.verificar_fidelidad(salida, {"params": {}}, fuente)
        return f["cobertura"].get("A7"), f["veredicto"], f["hallazgos"]

    def test_opus_estereo_a_tasa_baja_no_se_declara_aprobada(self):
        """**La prueba que se pone roja sin el arreglo**: antes decía
        `cobertura A7 = True` sobre un Opus estéreo de 8 kb/s, donde A7 atrapa
        0 de 6 del fallo que dice cubrir."""
        dst = self._codificar(self.est, "e8k.opus",
                              ["-c:a", "libopus", "-b:a", "8k"])
        cob, ver, hh = self._cobertura(self.est, dst)
        self.assertFalse(cob)
        self.assertEqual(ver, "ok_parcial")
        self.assertTrue([x for x in hh
                         if x["regla"] == "A7" and "punto ciego" in x["mensaje"]])

    def test_opus_estereo_a_96k_si_se_declara_aprobada(self):
        """Y el otro lado: a 96 kb/s Opus **sí** deja el canal mudo, A7 lo ve
        (3 de 3 en §2.5, 6 de 6 aquí) y tiene que seguir aprobando."""
        dst = self._codificar(self.est, "e96k.opus",
                              ["-c:a", "libopus", "-b:a", "96k"])
        cob, ver, _ = self._cobertura(self.est, dst)
        self.assertTrue(cob)
        self.assertEqual(ver, "ok")

    def test_mp3_y_aac_a_la_misma_tasa_baja_NO_son_ciegos(self):
        """Lo que refuta el nombre viejo: a 32 kb/s los otros dos atrapan
        6 de 6. Si la regla se declarase ciega aquí, estaría tirando cobertura
        buena."""
        for nombre, argv in (("e32k.mp3", ["-c:a", "libmp3lame", "-b:a", "32k"]),
                             ("e32k.m4a", ["-c:a", "aac", "-b:a", "32k"])):
            with self.subTest(nombre):
                dst = self._codificar(self.est, nombre, argv)
                cob, _, _ = self._cobertura(self.est, dst)
                self.assertTrue(cob, "%s no puede ser punto ciego" % nombre)

    def test_un_opus_MONO_no_es_punto_ciego(self):
        """Con un solo canal no hay de dónde copiar: el colapso a mono no
        esconde nada. **Es lo que deja intactas las dos salidas Opus del patrón
        oro**, que son mono."""
        dst = self._codificar(self.mono, "m8k.opus",
                              ["-c:a", "libopus", "-b:a", "8k"])
        cob, _, _ = self._cobertura(self.mono, dst)
        self.assertTrue(cob)

    def test_el_fallo_de_verdad_sigue_saliendo_fallo(self):
        """Declarar un punto ciego no puede apagar la regla: a 96 kb/s el canal
        derecho silenciado tiene que seguir dando `fallo`."""
        malo = os.path.join(self.dir, "malo.wav")
        _ff(["-i", self.est, "-af", "pan=stereo|c0=c0|c1=0*c0",
             "-c:a", "pcm_s16le", malo])
        dst = self._codificar(malo, "malo96k.opus",
                              ["-c:a", "libopus", "-b:a", "96k"])
        _, ver, hh = self._cobertura(self.est, dst)
        self.assertEqual(ver, "fallo")
        self.assertTrue([x for x in hh
                         if x["regla"] == "A7" and x["severidad"] == "fallo"])

    def test_la_tasa_se_deduce_cuando_la_sonda_no_la_da(self):
        """En un `.opus` la sonda devuelve `bitrate_bps = None` en la pista —
        MEDIDO—, así que una condición basada en ese campo no dispararía nunca
        justo en el formato al que apunta. Se deriva de bytes y duración."""
        dst = self._codificar(self.est, "e12k.opus",
                              ["-c:a", "libopus", "-b:a", "12k"])
        s = V.sondear(dst)
        pistas = [x for x in s.get("pistas", []) if x.get("tipo") == "audio"]
        self.assertIsNone(pistas[0].get("bitrate_bps"))
        tasa = V._a7_tasa_efectiva(dst, s)
        self.assertIsNotNone(tasa)
        self.assertLess(tasa, V.A7_OPUS_CIEGO_BPS)


if __name__ == "__main__":
    unittest.main(verbosity=2)

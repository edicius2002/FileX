"""N4, N5 y N14 — el watcher en POSIX, el fichero incompleto y el desechable huérfano.

    python -m unittest pruebas.test_watcher_n -v

**Por qué un fichero propio y no más clases en `test_hito7.py`.** El hito 7
probó el watcher con un escritor y un cerrojo de Windows; lo de aquí cruza a
otro sistema operativo (`wsl.exe`), mata procesos con `taskkill /F` y toca el
`%TEMP%`. Meterlo dentro de aquel fichero mezclaría dos regímenes de coste muy
distintos, y aquel fichero es de un hito cerrado.

Lo que mide cada clase está en `bench/watcher-y-desechables.md`:

* `CerrojoPosix`        — §1: `os.replace(p,p)` no sirve en POSIX y `/proc` sí.
* `CoherenciaDeclarada` — §2: la cabecera declara más bytes de los que hay.
* `PacienciaDelWatcher` — §2.5: la defensa APLAZA, no veta para siempre.
* `BarridoDeHuerfanos`  — §3: quién limpia el desechable de un `filex` muerto.

**Todas las pruebas que dicen reproducir una condición la COMPRUEBAN** (trampa
38): que el hijo siguiera vivo, que el desechable existiera, que el fichero
tuviera los bytes que se dijo. Una celda cuya condición no se dio se salta con
`skipTest`, nunca se cuenta como aprobada.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from filex import cerrojo, trabajo  # noqa: E402
from filex import watcher as w  # noqa: E402

CORPUS = os.path.join(RAIZ, "corpus")
PNG = os.path.join(CORPUS, "imagen", "tipico.png")
WAV = os.path.join(CORPUS, "audio", "trivial.wav")
CSV_BOM = os.path.join(CORPUS, "datos", "patologico_bom.csv")
SALIDAS = os.path.join(RAIZ, "bench", "salidas-watcher")
TENEDOR = os.path.join(SALIDAS, "tenedor.py")
HIJO_DES = os.path.join(SALIDAS, "hijo_desechable.py")
ES_WINDOWS = sys.platform == "win32"

#: Tope de todo lo que se lanza aquí. `CLAUDE.md` §3.
TOPE = 120


def _es_real(ruta: str) -> bool:
    """¿El fichero del corpus es el fichero, o el puntero de Git LFS?

    `os.path.exists()` devuelve `True` también para un puntero sin descargar
    —~130 B de texto que empiezan por `version https://git-lfs...`—, así que un
    guarda que comprueba EXISTENCIA no protege de nada (trampa 107; el daño,
    trampa 34). Se mira la CABECERA, que es exacta y no necesita umbral.
    """
    try:
        with open(ruta, "rb") as fh:
            return not fh.read(40).startswith(b"version https://git-lfs")
    except OSError:
        return False


#: MEDIDO en la ejecución 33826410849 de `windows-tests` sobre `windows-latest`:
#: los **4 fallos** de este módulo son este mecanismo y sólo éste. El job hace
#: `actions/checkout` con `lfs: false` —254 MB de corpus contra 1 GB de cuota
#: mensual—, así que `trivial.wav` llega como puntero de 130 B: cortarlo por la
#: mitad da los 65 B que aparecían en la traza, `_coherencia_declarada` responde
#: `sin_declaracion` en vez de `completo` y el `Vigilante` madura un fichero a
#: medias. **Dos pruebas más pasaban en VERDE por el mismo motivo**
#: (`test_riff_de_relleno_no_es_un_incompleto` y `test_un_wav_entero_no_se_aplaza`:
#: un puntero es `sin_declaracion` mires lo que mires), y un verde por el motivo
#: equivocado es peor que un rojo -- también van con guarda.
#:
#: `corpus/datos/patologico_bom.csv` **no** está en LFS (`git lfs ls-files`), así
#: que las pruebas que sólo usan el CSV no llevan guarda: el guarda se pone por
#: ACTIVO, no por clase.
PNG_REAL = _es_real(PNG)
WAV_REAL = _es_real(WAV)
_MOTIVO_LFS = ("hace falta el corpus REAL, no el puntero de Git LFS "
               "(`git lfs checkout`) -- trampas 34 y 107")


def _a_wsl(ruta: str) -> str:
    a = os.path.abspath(ruta)
    return "/mnt/" + a[0].lower() + a[2:].replace("\\", "/")


def _hay_wsl() -> bool:
    if not ES_WINDOWS:
        return False
    try:
        r = subprocess.run(["wsl.exe", "-e", "true"], stdin=subprocess.DEVNULL,
                           capture_output=True, timeout=60)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


class _Tenedor:
    """Un proceso aparte con un fichero abierto. Espera a su marcador."""

    def __init__(self, argv):
        self.p = subprocess.Popen(argv, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, text=True)
        self.marcador = (self.p.stdout.readline() or "").replace("\x00", "").strip()

    @property
    def ok(self) -> bool:
        return self.marcador.startswith("ABIERTO") and self.p.poll() is None

    def cerrar(self):
        try:
            self.p.kill()
            self.p.wait(timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            pass


# --------------------------------------------------------------------------
class CerrojoPosix(unittest.TestCase):
    """N4 — el equivalente POSIX que el hito 7 dio por inexistente sin mirar."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="prueba-n4-")
        self.sujeto = os.path.join(self.tmp, "sujeto.png")
        shutil.copyfile(PNG, self.sujeto)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @unittest.skipUnless(ES_WINDOWS, "el primitivo de Windows solo existe allí")
    def test_windows_ve_al_que_lo_tiene_abierto(self):
        """Control positivo del lado que ya estaba: sin esto, el 'no' de POSIX
        no significaría nada."""
        self.assertTrue(w._estable_en_disco(self.sujeto))
        t = _Tenedor([sys.executable, TENEDOR, "--ruta", self.sujeto,
                      "--modo", "ab", "--segundos", "20"])
        try:
            if not t.ok:
                self.skipTest("el tenedor no llegó a abrir el fichero")
            self.assertFalse(w._estable_en_disco(self.sujeto))
        finally:
            t.cerrar()

    def test_sin_proc_no_se_inventa_una_defensa(self):
        """Si no se puede mirar, se devuelve `True` y se sigue con la
        estabilidad de `stat`. Nunca se finge una defensa que no hay."""
        antes = os.environ.get(w._VAR_PROC)
        os.environ[w._VAR_PROC] = "0"
        try:
            self.assertIsNone(w._tenedores_posix(self.sujeto))
            self.assertTrue(w._estable_en_disco(self.sujeto))
        finally:
            if antes is None:
                os.environ.pop(w._VAR_PROC, None)
            else:
                os.environ[w._VAR_PROC] = antes

    @unittest.skipUnless(_hay_wsl(), "no hay wsl.exe: no se puede medir POSIX")
    def test_proc_ve_al_escritor_y_replace_no(self):
        """La prueba que **falla sin el arreglo**: en POSIX `os.replace(p,p)`
        aprueba mientras otro proceso escribe, y `/proc` no.

        Se corre entera dentro de WSL2, con un tenedor que también vive allí:
        el candado y la observación no cruzan de sistema (MEDIDO), así que un
        tenedor de Windows daría un falso negativo que parecería un fallo.
        """
        guion = os.path.join(SALIDAS, "prueba_posix.py")
        r = subprocess.run(
            ["wsl.exe", "-e", "python3", _a_wsl(guion),
             "--raiz", _a_wsl(RAIZ), "--tenedor", _a_wsl(TENEDOR),
             "--origen", _a_wsl(PNG)],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            timeout=TOPE)
        salida = (r.stdout or "").replace("\x00", "").strip()
        self.assertEqual(r.returncode, 0, salida + (r.stderr or "")[:400])
        datos = dict(x.split("=", 1) for x in salida.split() if "=" in x)
        if datos.get("condicion") != "True":
            self.skipTest(f"el tenedor de WSL2 no llegó a abrir: {salida}")
        # `os.replace(p,p)` aprueba con el escritor dentro: no sirve.
        self.assertEqual(datos["replace_con_escritor"], "libre")
        # `/proc` lo ve, y ve que se ha ido cuando se va.
        self.assertEqual(datos["proc_con_escritor"], "ocupado")
        self.assertEqual(datos["proc_sin_escritor"], "libre")
        # Y la función del watcher decide con eso.
        self.assertEqual(datos["estable_con_escritor"], "False")
        self.assertEqual(datos["estable_sin_escritor"], "True")


# --------------------------------------------------------------------------
class CoherenciaDeclarada(unittest.TestCase):
    """N5 — la cabecera declara una longitud; el `stat` dice otra."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="prueba-n5-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _cortar(self, origen: str, n: int, nombre: str) -> str:
        destino = os.path.join(self.tmp, nombre)
        with open(origen, "rb") as a, open(destino, "wb") as b:
            b.write(a.read(n))
        self.assertEqual(os.path.getsize(destino), n)   # la condición, medida
        return destino

    @unittest.skipUnless(WAV_REAL, _MOTIVO_LFS)
    def test_wav_truncado_se_ve(self):
        total = os.path.getsize(WAV)
        self.assertEqual(w._coherencia_declarada(WAV), "completo")
        for frac in (0.10, 0.50, 0.90):
            cortado = self._cortar(WAV, int(total * frac), f"c{frac}.wav")
            self.assertEqual(w._coherencia_declarada(cortado), "incompleto",
                             f"al {frac:.0%}")
        # Y el caso de un solo byte de menos, que es el más difícil.
        self.assertEqual(
            w._coherencia_declarada(self._cortar(WAV, total - 1, "casi.wav")),
            "incompleto")

    @unittest.skipUnless(PNG_REAL, _MOTIVO_LFS)
    def test_png_truncado_se_ve(self):
        total = os.path.getsize(PNG)
        self.assertEqual(w._coherencia_declarada(PNG), "completo")
        self.assertEqual(
            w._coherencia_declarada(self._cortar(PNG, total // 2, "m.png")),
            "incompleto")

    @unittest.skipUnless(WAV_REAL, _MOTIVO_LFS)
    def test_riff_de_relleno_no_es_un_incompleto(self):
        """El falso positivo MEDIDO: `ffmpeg` escribiendo a una tubería no puede
        volver atrás y estampa `0xFFFFFFFF`. Un WAV **entero** con esa cabecera
        no puede llamarse incompleto."""
        destino = os.path.join(self.tmp, "tuberia.wav")
        with open(WAV, "rb") as fh:
            crudo = bytearray(fh.read())
        crudo[4:8] = (0xFFFFFFFF).to_bytes(4, "little")
        with open(destino, "wb") as fh:
            fh.write(crudo)
        self.assertEqual(len(crudo), os.path.getsize(WAV))   # sigue entero
        self.assertEqual(w._coherencia_declarada(destino), "sin_declaracion")

    def test_csv_no_declara_nada_y_se_dice(self):
        """`sin_declaracion` NO es un aprobado: es el residuo declarado."""
        self.assertEqual(w._coherencia_declarada(CSV_BOM), "sin_declaracion")
        total = os.path.getsize(CSV_BOM)
        cortado = self._cortar(CSV_BOM, total // 2, "medio.csv")
        self.assertEqual(w._coherencia_declarada(cortado), "sin_declaracion")


# --------------------------------------------------------------------------
@unittest.skipUnless(WAV_REAL, _MOTIVO_LFS)
class PacienciaDelWatcher(unittest.TestCase):
    """N5 — la tercera defensa dentro del `Vigilante`, sin convertir nada."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="prueba-n5v-")
        self.ent = os.path.join(self.tmp, "ent")
        os.makedirs(self.ent)
        self.sujeto = os.path.join(self.ent, "medio.wav")
        with open(WAV, "rb") as a, open(self.sujeto, "wb") as b:
            b.write(a.read(os.path.getsize(WAV) // 2))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _vigilante(self, **kw):
        class _GrafoSi:
            def camino(self, *_a, **_k):
                class _D:
                    hay = True
                return _D()

        class _FxFalso:
            grafo = _GrafoSi()
            confinamiento = None

        return w.Vigilante(_FxFalso(), [self.ent],
                           os.path.join(self.tmp, "sal"), "mp3",
                           estables=1, cerrojo=False, **kw)

    def test_sin_coherencia_madura_un_wav_a_medias(self):
        """El ANTES. Si esta prueba pasara con la defensa puesta, la defensa no
        estaría haciendo nada."""
        v = self._vigilante(coherencia=False)
        self.assertEqual(len(v.maduros()), 1)

    def test_con_coherencia_lo_aplaza(self):
        v = self._vigilante(coherencia=True, paciencia=10)
        self.assertEqual(v.maduros(), [])
        self.assertEqual(v.contadores["aplazados_incompletos"], 1)
        self.assertEqual(v.contadores["rendidos"], 0)

    def test_la_paciencia_se_acaba_y_no_hay_veto_perpetuo(self):
        """Un fichero truncado de verdad no se mueve nunca más. Sin paciencia,
        el watcher lo re-sondearía para siempre y nadie lo atendería jamás."""
        v = self._vigilante(coherencia=True, paciencia=3)
        self.assertEqual(v.maduros(), [])
        self.assertEqual(v.maduros(), [])
        self.assertEqual(len(v.maduros()), 1)
        self.assertEqual(v.contadores["rendidos"], 1)

    def test_un_wav_entero_no_se_aplaza(self):
        entero = os.path.join(self.ent, "entero.wav")
        shutil.copyfile(WAV, entero)
        os.remove(self.sujeto)
        v = self._vigilante(coherencia=True)
        self.assertEqual(len(v.maduros()), 1)
        self.assertEqual(v.contadores["aplazados_incompletos"], 0)


# --------------------------------------------------------------------------
class BarridoDeHuerfanos(unittest.TestCase):
    """N14 — el desechable de R18 que un `taskkill /F` deja sin borrar."""

    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="prueba-n14-")

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def _falso_huerfano(self, bytes_=1024) -> str:
        """Un desechable como el que deja un proceso MUERTO, no uno que cerró.

        La diferencia costó un rojo: `soltar()` **borra el fichero de candado**
        en Windows, así que tomar y soltar simula a un dueño que terminó bien, y
        el barrido lo trataba —con razón— como «nunca tuvo candado». Un
        `taskkill /F` no ejecuta `soltar()`: el sistema libera el candado y
        **el fichero se queda con su carga dentro**. Eso es lo que se fabrica
        aquí, y es la escena que N-b midió de verdad.
        """
        d = tempfile.mkdtemp(prefix=trabajo.PREFIJO, dir=self.base)
        with open(os.path.join(d, "salida.bin"), "wb") as fh:
            fh.write(b"\x00" * bytes_)
        with open(cerrojo.fichero(trabajo._nombre_candado(d)), "wb") as fh:
            fh.write(f"99999\t0\t{d}\n".encode("utf-8"))
        return d

    def test_borra_al_muerto(self):
        d = self._falso_huerfano(2048)
        parte = trabajo.barrer_huerfanos(base=self.base)
        self.assertFalse(os.path.isdir(d))
        self.assertEqual(parte["borrados"], 1)
        self.assertEqual(parte["bytes"], 2048)

    def test_respeta_al_vivo_del_mismo_proceso(self):
        t = trabajo.DirectorioDeTrabajo(prefijo=trabajo.PREFIJO)
        # `mkdtemp` va al `%TEMP%` real, así que se barre SU directorio.
        try:
            with open(t.destino("salida.bin"), "wb") as fh:
                fh.write(b"x")
            parte = trabajo.barrer_huerfanos(base=os.path.dirname(t.ruta))
            self.assertTrue(os.path.isdir(t.ruta), parte)
            self.assertGreaterEqual(parte["vivos"], 1)
        finally:
            t.cerrar()

    @unittest.skipUnless(os.path.isfile(HIJO_DES), "falta el hijo de la sonda")
    def test_respeta_al_vivo_de_OTRO_proceso(self):
        """La que importa: un `set` en memoria no habría distinguido esto, y es
        el mismo error que el hito 7 cometió con el cerrojo de destino.

        Y reproduce la ventana real: el hijo tiene su fichero **ya cerrado**, de
        modo que el sistema operativo no lo protege y lo único que salva al
        directorio es el candado de vida.
        """
        p = subprocess.Popen([sys.executable, HIJO_DES],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             text=True)
        try:
            linea = (p.stdout.readline() or "").strip()
            if not linea.startswith("LISTO") or p.poll() is not None:
                self.skipTest(f"el hijo no llegó a crear su desechable: {linea!r}")
            d = linea.split(" ", 1)[1]
            dentro = os.path.join(d, "salida.bin")
            # La condición que separa esta prueba de la escena C: dentro NO hay
            # nada abierto, así que el sistema no va a protegerlo por su cuenta.
            if ES_WINDOWS:
                try:
                    os.replace(dentro, dentro)
                except OSError:
                    self.skipTest("algo tenía el fichero abierto: otra escena")
            parte = trabajo.barrer_huerfanos(base=os.path.dirname(d))
            self.assertTrue(os.path.isdir(d), parte)
            self.assertTrue(os.path.isfile(dentro), parte)
            p.stdin.write("ya\n")
            p.stdin.flush()
            self.assertEqual((p.stdout.readline() or "").strip(),
                             "RESULTADO True True")
        finally:
            try:
                p.kill()
                p.wait(timeout=30)
            except (OSError, subprocess.TimeoutExpired):
                pass

    def test_no_toca_el_directorio_de_candados(self):
        """El fallo que encontró la sonda EN MI PROPIO CÓDIGO: `filex-destinos`
        empieza por `filex-`, y el barrido se lo habría llevado entero con
        todos los candados de destino de la máquina dentro."""
        d = cerrojo.directorio()
        testigo = os.path.join(d, "testigo-n14.lock")
        with open(testigo, "wb") as fh:
            fh.write(b"x")
        try:
            trabajo.barrer_huerfanos(base=os.path.dirname(d))
            self.assertTrue(os.path.isdir(d))
            self.assertTrue(os.path.isfile(testigo))
        finally:
            try:
                os.remove(testigo)
            except OSError:
                pass

    def test_sin_candado_y_joven_no_se_toca(self):
        """Un `filex` anterior a esto, o uno cuyo candado se degradó. La edad es
        lo único que hay, y por eso es holgada."""
        d = tempfile.mkdtemp(prefix=trabajo.PREFIJO, dir=self.base)
        parte = trabajo.barrer_huerfanos(base=self.base)
        self.assertTrue(os.path.isdir(d))
        self.assertEqual(parte["sin_candado_jovenes"], 1)
        self.assertEqual(parte["borrados"], 0)
        # Y con la edad a cero, sí.
        parte = trabajo.barrer_huerfanos(base=self.base, edad_sin_candado=0.0)
        self.assertFalse(os.path.isdir(d))
        self.assertEqual(parte["borrados"], 1)

    def test_dos_barridos_seguidos_no_cambian_la_decision(self):
        """Regresión de un fallo propio: `esta_libre` CREA el fichero de
        candado, así que el segundo barrido veía «tenía candado y murió» donde
        el primero veía «nunca tuvo» — y se saltaba la edad."""
        d = tempfile.mkdtemp(prefix=trabajo.PREFIJO, dir=self.base)
        trabajo.barrer_huerfanos(base=self.base)
        parte = trabajo.barrer_huerfanos(base=self.base)
        self.assertTrue(os.path.isdir(d))
        self.assertEqual(parte["sin_candado_jovenes"], 1)
        self.assertEqual(parte["borrados"], 0)

    def test_la_variable_lo_apaga(self):
        """Control negativo: si con `FILEX_BARRER=0` también desapareciera, las
        otras pruebas no estarían midiendo el barrido."""
        d = self._falso_huerfano()
        antes = os.environ.get(trabajo._VAR_BARRER)
        os.environ[trabajo._VAR_BARRER] = "0"
        try:
            parte = trabajo.barrer_huerfanos(base=self.base)
            self.assertTrue(parte["saltado"])
            self.assertTrue(os.path.isdir(d))
        finally:
            if antes is None:
                os.environ.pop(trabajo._VAR_BARRER, None)
            else:
                os.environ[trabajo._VAR_BARRER] = antes

    def test_cerrar_suelta_el_candado_y_borra_su_fichero(self):
        t = trabajo.DirectorioDeTrabajo()
        nombre = trabajo._nombre_candado(t.ruta)
        self.assertFalse(cerrojo.esta_libre(nombre))
        t.cerrar()
        self.assertTrue(cerrojo.esta_libre(nombre))
        self.assertFalse(os.path.isdir(t.ruta))


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""N10 y N11 — cancelar entre PROCESOS, y el andamiaje del hilo como mecanismo.

Dos pendientes de `bench/cancelacion-y-servicio.md` §4:

* **§4.1 (N10)** *«Es de PROCESO. […] Cancelar un trabajo leído del disco desde
  otro proceso no alcanza su `Popen`.»* Se cierra con un canal de mando en el
  disco **y** con detección del dueño muerto, que es la mitad que un mecanismo
  cooperativo siempre se deja.
* **§4.3 (N11)** *«`olvidar_hilo()` […] es una disciplina que hay que
  recordar.»* Se cierra con `invocacion.hilo_de()` y con `Servicio._arrancar`
  como única puerta de construcción de hilos de trabajo.

**Las pruebas de N10 lanzan procesos de verdad.** Dos `Servicio` en el mismo
intérprete comparten el registro de `filex.invocacion` y darían verde sin que
exista canal ninguno: es la trampa 38 —*«un arnés que espera la carrera
equivocada sale verde»*— y por eso está `pruebas/hijo_de_trabajo.py`.

Todas las de N10 se ejercitan también con `FILEX_MANDO=0`, que es el **antes**
medible dentro de la misma tanda: sin el canal, la prueba falla por el fallo que
dice cubrir.
"""

from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from filex import invocacion                                    # noqa: E402
from filex import servicio as S                                 # noqa: E402

VIDEO = os.path.join(RAIZ, "corpus", "video", "tipico.mp4")
HIJO = os.path.join(RAIZ, "pruebas", "hijo_de_trabajo.py")


def _es_video_real(ruta: str) -> bool:
    """`os.path.exists` es TRUE también para un puntero de Git LFS sin
    descargar (~130 B de texto) -- trampa 34, aquí sin proteger. Con
    `actions/checkout: lfs: false` el runner de Linux tiene el puntero, no el
    vídeo, y ningún motor reconoce su firma: **"ningún motor disponible lee
    'mp4'" no es que falte ffmpeg** (MEDIDO: el mismo error aparece con
    ffmpeg instalado) -- es que la entrada no es un MP4. C42,
    `bench/ci-y-contrato.md` §1. Un MP4 real de este proyecto pesa >1 MB."""
    try:
        return os.path.getsize(ruta) > 100_000
    except OSError:
        return False


HAY_VIDEO_REAL = _es_video_real(VIDEO)
_MOTIVO_SIN_VIDEO = ("hace falta el corpus de vídeo REAL (no un puntero de "
                    "Git LFS sin `git lfs checkout` -- trampa 34)")

#: Cuánto se le da a un hijo para arrancar y poner un motor en vuelo.
TOPE_ARRANQUE = 90.0

#: Cuánto se espera a que una cancelación entre procesos surta efecto. El canal
#: mira cada `INTERVALO_MANDO` (0,2 s) y matar el árbol cuesta ~155 ms MEDIDOS,
#: así que esto es holgura, no la medida: la medida está en el arnés.
TOPE_CANCELACION = 30.0


def _lee_evento(proc, esperado: str, tope: float = TOPE_ARRANQUE) -> dict:
    """Lee líneas del hijo hasta encontrar el evento pedido. Con tope."""
    limite = time.perf_counter() + tope
    while time.perf_counter() < limite:
        linea = proc.stdout.readline()
        if not linea:
            break
        try:
            d = json.loads(linea)
        except ValueError:
            continue
        if d.get("evento") == esperado:
            return d
        if d.get("evento") == "error":
            raise AssertionError(f"el hijo falló: {d}")
    raise AssertionError(f"el hijo no dijo '{esperado}' en {tope} s")


class _ConHijo(unittest.TestCase):
    """Lanza un `filex` de verdad convirtiendo un vídeo, y lo limpia siempre."""

    no_mando = False

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="n10-")
        self.trabajos = os.path.join(self.d, "trabajos")
        os.makedirs(self.trabajos, exist_ok=True)
        argv = [sys.executable, HIJO, "--trabajos", self.trabajos,
                "--entrada", VIDEO, "--salida", os.path.join(self.d, "s.webm")]
        if self.no_mando:
            argv.append("--no-mando")
        self.proc = subprocess.Popen(
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
            errors="replace", cwd=RAIZ)
        # El hijo publica su PID REAL, y hace falta: en Windows el
        # `python.exe` de un venv es un LANZADOR, así que `self.proc.pid` es el
        # del shim y NO el del proceso que toma el candado (trampa 93).
        _arrancado = _lee_evento(self.proc, "arrancado")
        self.jid = _arrancado["job_id"]
        self.pid_hijo = _arrancado["pid"]
        self.assertTrue(_lee_evento(self.proc, "en_vuelo")["hay"],
                        "el motor del hijo no llegó a arrancar")
        # El servicio de ESTE proceso, que solo conoce al trabajo por el disco.
        self.sv = S.Servicio(_FxFalso(), S.Trabajos(self.trabajos))

    def tearDown(self):
        try:
            self.proc.kill()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=20)
        except Exception:
            pass
        try:
            self.proc.stdout.close()
        except Exception:
            pass
        shutil.rmtree(self.d, ignore_errors=True)


class _FxFalso:
    """`Servicio` necesita un `FileX` para convertir; aquí no se convierte nada.

    Se pasa un objeto vacío a propósito: si alguna de estas pruebas llegara a
    tocar el núcleo, fallaría con `AttributeError` en vez de convertir en
    silencio, que es la clase de error que se quiere ruidosa.
    """

    confinamiento = None


# ==========================================================================
# N10 — el mando: cancelar un trabajo que corre en OTRO proceso
# ==========================================================================


@unittest.skipUnless(HAY_VIDEO_REAL, _MOTIVO_SIN_VIDEO)
class CancelarEntreProcesos(_ConHijo):

    def test_cancelar_alcanza_al_motor_de_otro_proceso(self):
        """Lo que C34 declaró imposible: `motor_detenido` desde fuera.

        Sin el canal, `tipico.mp4 → webm` termina en ~21 s con `completed`
        (MEDIDO por N-a). Con él, el hijo pasa a `cancelled` sin llegar a
        convertir.
        """
        t0 = time.perf_counter()
        r = self.sv.job(self.jid, "cancelar")
        self.assertTrue(r["motor_detenido"], r)
        self.assertEqual(r["via"], "entre procesos")
        self.assertEqual(r["estado"], S.CANCELADO)

        fin = _lee_evento(self.proc, "fin", tope=TOPE_CANCELACION)
        self.assertEqual(fin["estado"], S.CANCELADO,
                         "cancelado no es fallido ni completado")
        ms = (time.perf_counter() - t0) * 1000
        self.assertLess(ms, TOPE_CANCELACION * 1000)
        # Y no queda salida: el desechable de R18 se borra en el `finally`.
        self.assertFalse(os.path.exists(os.path.join(self.d, "s.webm")))

    def test_el_mando_se_borra_al_terminar_el_trabajo(self):
        """Un fichero de mando que sobrevive a su trabajo es basura con
        capacidad de hacer daño: el siguiente trabajo nacería cancelado."""
        f = S.fichero_mando(self.trabajos, self.jid)
        self.sv.job(self.jid, "cancelar")
        _lee_evento(self.proc, "fin", tope=TOPE_CANCELACION)
        self.assertFalse(os.path.exists(f), "el mando se quedó en el disco")

    def test_el_candado_del_trabajo_se_suelta_al_terminar(self):
        """Mientras el trabajo vive su candado está tomado; al morir, libre.

        Es la mitad de DETECCIÓN vista desde el otro lado: si el candado no se
        soltara, un trabajo ya terminado seguiría pareciendo vivo para siempre.
        """
        clave = S.clave_de(self.jid)
        from filex import cerrojo
        self.assertFalse(cerrojo.esta_libre(clave),
                         "el trabajo corre y su candado debería estar tomado")
        self.sv.job(self.jid, "cancelar")
        _lee_evento(self.proc, "fin", tope=TOPE_CANCELACION)
        self.assertTrue(cerrojo.esta_libre(clave))

    def test_el_dueno_se_puede_saber_sin_preguntar_por_ningun_PID(self):
        """Trampa 31: la VRAM por PID no es observable, así que la respuesta a
        «¿quién lo tiene?» tiene que venir del propio candado. `dueno()` la da."""
        from filex import cerrojo
        d = cerrojo.dueno(S.clave_de(self.jid))
        self.assertIsNotNone(d)
        self.assertIn(self.jid, d)
        # Contra el PID que el hijo DICE ser, no contra `self.proc.pid`: ese es
        # el del lanzador y difiere siempre en Windows (trampa 93).
        self.assertEqual(int(d.split("\t")[0]), self.pid_hijo)


@unittest.skipUnless(HAY_VIDEO_REAL, _MOTIVO_SIN_VIDEO)
class SinCanalNoSeAlcanza(_ConHijo):
    """El ANTES, en la misma tanda. `FILEX_MANDO=0` en los DOS procesos."""

    no_mando = True

    def setUp(self):
        os.environ["FILEX_MANDO"] = "0"
        try:
            super().setUp()
        except Exception:
            os.environ.pop("FILEX_MANDO", None)
            raise

    def tearDown(self):
        os.environ.pop("FILEX_MANDO", None)
        super().tearDown()

    def test_sin_canal_la_cancelacion_no_llega_y_se_dice(self):
        r = self.sv.job(self.jid, "cancelar")
        self.assertFalse(r["motor_detenido"])
        self.assertNotIn("via", r)
        # Y lo que importa: el trabajo NO se entera. Se le da margen de sobra.
        time.sleep(2.0)
        est = self.sv.job(self.jid)
        self.assertEqual(est["estado"], S.TRABAJANDO,
                         "sin canal el trabajo no debería enterarse")


# ==========================================================================
# N10 — la DETECCIÓN: un `job_id` cuyo proceso dueño murió sin limpiar
# ==========================================================================


@unittest.skipUnless(HAY_VIDEO_REAL, _MOTIVO_SIN_VIDEO)
class DuenoMuerto(_ConHijo):

    def _matar_al_hijo(self) -> None:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.proc.pid)],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=30, check=False)
        else:
            self.proc.kill()
        self.proc.wait(timeout=30)

    def test_un_working_sin_dueno_vivo_se_detecta_y_se_cierra(self):
        """**La otra mitad.** Un mecanismo que solo alcanza a quien coopera
        resuelve la mitad del problema (trampa 33, y la lección de N-b y P).

        Sin detección, el trabajo se queda `working` en el disco para siempre:
        las cuatro superficies y el modelo esperan a algo que ya no existe.
        """
        self._matar_al_hijo()
        r = self.sv.job(self.jid)
        self.assertEqual(r["estado"], S.FALLIDO, r)
        self.assertTrue(r.get("huerfano"))
        self.assertIn("no vive", r["nota"])
        # Y queda escrito: quien pregunte después ve el mismo veredicto.
        otra = S.Servicio(_FxFalso(), S.Trabajos(self.trabajos))
        self.assertEqual(otra.job(self.jid, "resultado").get("motivo"),
                         "proceso_dueno_muerto")

    def test_sin_deteccion_el_trabajo_se_queda_working_para_siempre(self):
        """El mismo caso con `FILEX_MANDO=0`: es lo que había."""
        self._matar_al_hijo()
        os.environ["FILEX_MANDO"] = "0"
        try:
            r = self.sv.job(self.jid)
            self.assertEqual(r["estado"], S.TRABAJANDO,
                             "sin detección un huérfano parece vivo")
        finally:
            os.environ.pop("FILEX_MANDO", None)

    def test_un_trabajo_vivo_NO_se_declara_huerfano(self):
        """El falso positivo que la espera del candado existe para evitar."""
        r = self.sv.job(self.jid)
        self.assertEqual(r["estado"], S.TRABAJANDO)
        self.assertFalse(r.get("huerfano"))


# ==========================================================================
# N10 — el `job_id` entra por la superficie y compone nombres de fichero
# ==========================================================================


class UnJobIdEsUnaEntrada(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="n10-jid-")
        self.sv = S.Servicio(_FxFalso(), S.Trabajos(self.d))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_un_job_id_con_travesia_no_compone_ninguna_ruta(self):
        for malo in ("../fuera", "..\\fuera", "a/b", "C:\\x", "con espacios",
                     "MAYUSCULAS", ""):
            self.assertEqual(S.fichero_mando(self.d, malo), "",
                             f"{malo!r} llegó a componer una ruta")
            self.assertFalse(S.pedir_mando(self.d, malo))
            self.assertEqual(self.sv.job(malo), {"error": "job_id desconocido"})

    def test_un_job_id_bueno_si_compone(self):
        jid = "0123456789ab"
        self.assertTrue(S.fichero_mando(self.d, jid).endswith(
            jid + S.SUFIJO_MANDO))


# ==========================================================================
# N11 — el andamiaje del hilo deja de ser una disciplina
# ==========================================================================


def _fuente(nombre: str) -> str:
    with open(os.path.join(RAIZ, "filex", nombre), encoding="utf-8") as fh:
        return fh.read()


def _funcion_de(nodo, arbol):
    """La función (de cualquier nivel) que contiene a `nodo`, o `None`."""
    for f in ast.walk(arbol):
        if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for hijo in ast.walk(f):
                if hijo is nodo:
                    return f
    return None


class ElAndamiajeEsUnMecanismo(unittest.TestCase):
    """N11. Lo mismo que R10 hace con la validación, sobre el rastro del hilo.

    La prueba es sobre el AST y no sobre el comportamiento **a propósito**: lo
    que falla hoy no es que el código esté mal, es que una tercera clase de
    trabajo escrita mañana se olvide. Un comportamiento no se puede probar antes
    de escribirlo; una forma, sí.
    """

    def test_hilo_de_borra_el_rastro_aunque_el_cuerpo_reviente(self):
        caja = {}

        def hilo():
            try:
                with invocacion.hilo_de() as ident:
                    caja["ident"] = ident
                    invocacion.cancelar_hilo(ident)
                    raise RuntimeError("el cuerpo revienta")
            except RuntimeError:
                pass
            caja["cancelado_al_salir"] = invocacion.hilo_cancelado()

        h = threading.Thread(target=hilo)
        h.start()
        h.join(timeout=30)
        self.assertIn("ident", caja)
        self.assertFalse(caja["cancelado_al_salir"],
                         "el rastro sobrevivió a una excepción")

    def test_hilo_de_NO_limpia_al_entrar(self):
        """Sería la simetría bonita y se tragaría una cancelación real.

        Entre `Thread.start()` y la primera línea del hilo cabe un
        `job(..., 'cancelar')`; si `hilo_de` limpiara a la entrada, esa
        cancelación se perdería. Se prueba porque es una decisión, no un olvido.
        """
        caja = {}
        arranca = threading.Event()

        def hilo():
            arranca.wait(30)
            with invocacion.hilo_de():
                caja["visto"] = invocacion.hilo_cancelado()

        h = threading.Thread(target=hilo)
        h.start()
        while h.ident is None:
            time.sleep(0.001)
        invocacion.cancelar_hilo(h.ident)     # llega ANTES de entrar al `with`
        arranca.set()
        h.join(timeout=30)
        self.assertTrue(caja.get("visto"),
                        "hilo_de se tragó una cancelación anterior a su entrada")

    def test_los_hilos_de_trabajo_solo_se_construyen_en_una_puerta(self):
        """`threading.Thread(` en `servicio.py`, y dónde puede estar.

        Dos sitios y ni uno más: `Servicio._arrancar` (los trabajos) y
        `_arrancar_vigilante` (el hilo del canal de mando, que no es un
        trabajo). Cualquier tercero es una clase de trabajo que se ha saltado el
        andamiaje.
        """
        arbol = ast.parse(_fuente("servicio.py"))
        sitios = set()
        for n in ast.walk(arbol):
            if not isinstance(n, ast.Call):
                continue
            f = n.func
            nombre = (f.attr if isinstance(f, ast.Attribute) else
                      getattr(f, "id", ""))
            if nombre != "Thread":
                continue
            cont = _funcion_de(n, arbol)
            sitios.add(cont.name if cont is not None else "<módulo>")
        self.assertEqual(sitios, {"_arrancar", "_arrancar_vigilante"},
                         "un hilo construido fuera de la única puerta: si es "
                         "una clase de trabajo, tiene que pasar por "
                         "Servicio._arrancar")

    def test_una_clase_de_trabajo_nueva_no_puede_saltarse_arrancar(self):
        """Quien cree un trabajo tiene que lanzarlo por `_arrancar`.

        Es la prueba que N-a pedía: *«una prueba que falle si alguien añade una
        clase de trabajo sin él»*. Crear el trabajo es `self.trabajos.nuevo(`;
        lanzarlo es `self._arrancar(`. Lo uno sin lo otro es el olvido.
        """
        arbol = ast.parse(_fuente("servicio.py"))
        malas = []
        for f in ast.walk(arbol):
            if not isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            llamadas = {n.func.attr for n in ast.walk(f)
                        if isinstance(n, ast.Call)
                        and isinstance(n.func, ast.Attribute)}
            if "nuevo" in llamadas and "_arrancar" not in llamadas:
                malas.append(f.name)
        self.assertEqual(malas, [],
                         "estas funciones crean un trabajo y no lo lanzan por "
                         "Servicio._arrancar: su hilo no tendría ni candado, ni "
                         "canal de mando, ni limpieza de `ident`")

    def test_ya_no_queda_la_disciplina_suelta(self):
        """`olvidar_hilo` no se LLAMA a mano en `servicio.py`.

        Mientras siga llamándose a mano en algún sitio, sigue siendo una
        disciplina para el siguiente: el mecanismo es `en_curso`, y llega a
        `olvidar_hilo` por una sola vía, `invocacion.hilo_de`.

        Se mira el AST y no el texto: la primera versión de esta prueba buscaba
        la cadena y la encontró **dentro de un comentario que explicaba que ya
        no se llamaba**. Un buscador de texto no distingue una llamada de una
        mención — que es la trampa 25 en versión de arnés.
        """
        arbol = ast.parse(_fuente("servicio.py"))
        llamadas = {n.func.attr for n in ast.walk(arbol)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertNotIn("olvidar_hilo", llamadas)
        self.assertIn("hilo_de", llamadas)


if __name__ == "__main__":
    unittest.main()

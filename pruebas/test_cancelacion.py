"""C34 y N6: cancelar de verdad, y el servicio fuera del módulo del protocolo.

Cada prueba de este fichero **falla antes del arreglo y pasa después**:

* Las de C34 fallan porque `job(..., "cancelar")` era un `threading.Event` que
  solo se consultaba entre saltos: el motor en vuelo seguía hasta agotar su
  tope, que por MCP son 300 s.
* Las de N6 fallan porque `Servicio`, `Trabajo` y `Trabajos` vivían dentro de
  `filex/mcp.py` y dos superficies que no hablan MCP los importaban de ahí.

Los números están en `bench/cancelacion-y-servicio.md`.
"""

from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filex import invocacion  # noqa: E402
from filex import servicio as S  # noqa: E402
from filex.nucleo import FileX  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAQUETE = os.path.join(RAIZ, "filex")
VIDEO = os.path.join(RAIZ, "corpus", "video", "tipico.mp4")

#: Tope de paciencia de toda espera de este fichero. Ninguna prueba puede
#: colgarse: `CLAUDE.md` §3, «timeouts explícitos en todo».
PACIENCIA = 30.0

#: Cuánto se le concede a una cancelación para surtir efecto. Es holgadísimo
#: —lo MEDIDO es un orden de magnitud menos— y aun así el comportamiento
#: anterior no lo cumpliría ni de lejos: sin matar el motor, la conversión de
#: `tipico.mp4` a webm tarda ~26 s y la de un contenedor, hasta su tope.
TOPE_CANCELACION = 8.0


def _espera(cond, tope=PACIENCIA, paso=0.02) -> bool:
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < tope:
        if cond():
            return True
        time.sleep(paso)
    return False


def _ffmpeg_eterno() -> list[str]:
    """Un motor real que no termina solo, y que casi no consume CPU.

    `-re` lee a la velocidad del reloj: sin él, `testsrc2` satura un núcleo y la
    prueba mide la contención de la máquina en vez de la cancelación.
    """
    return ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-re",
            "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=30",
            "-t", "3600", "-f", "null", "-"]


# ==========================================================================
# 1. C34 — el asa alcanzable desde otro hilo
# ==========================================================================


@unittest.skipIf(shutil.which("ffmpeg") is None, "falta ffmpeg")
class MatarElMotorEnVuelo(unittest.TestCase):

    def test_cancelar_mata_el_motor_y_no_lo_llama_tiempo_agotado(self):
        """El corazón de C34: matar el árbol de un motor que está corriendo.

        Y la segunda mitad, que es de vocabulario: un motor cancelado **no se
        agotó ni rechazó la conversión**. Sin `motivo == "cancelado"`, quien lee
        el trabajo no puede distinguir «lo maté yo» de «el motor dijo que no» —
        misma familia que la trampa 25 de `CLAUDE.md`.
        """
        caja = {}
        arrancado = threading.Event()

        def corre():
            arrancado.set()
            caja["r"] = invocacion.ejecutar(_ffmpeg_eterno(), timeout=PACIENCIA)
            caja["ident"] = threading.get_ident()
            invocacion.olvidar_hilo()

        h = threading.Thread(target=corre, daemon=True)
        h.start()
        self.assertTrue(arrancado.wait(PACIENCIA))
        self.assertTrue(_espera(lambda: invocacion.en_vuelo() > 0),
                        "el `Popen` no llegó nunca al registro")

        t0 = time.perf_counter()
        self.assertTrue(invocacion.cancelar_hilo(h.ident),
                        "cancelar_hilo no encontró la invocación en vuelo")
        h.join(timeout=PACIENCIA)
        ms = (time.perf_counter() - t0) * 1000

        self.assertFalse(h.is_alive())
        r = caja["r"]
        self.assertTrue(r.cancelado)
        self.assertFalse(r.agotado, "cancelar no es agotarse")
        self.assertEqual(r.motivo, "cancelado")
        self.assertLess(ms, TOPE_CANCELACION * 1000,
                        f"la cancelación tardó {ms:.0f} ms")

    def test_un_hilo_cancelado_no_arranca_el_siguiente_motor(self):
        """La ventana ENTRE saltos, que no tiene ningún `Popen` que matar.

        Un camino de dos saltos cancelado en el primero no puede empezar el
        segundo. Con solo matar el proceso en vuelo, empezaría.
        """
        ident = threading.get_ident()
        try:
            invocacion.cancelar_hilo(ident)          # sin nada en vuelo
            r = invocacion.ejecutar(["ffmpeg", "-version"], timeout=PACIENCIA)
            self.assertTrue(r.cancelado)
            self.assertIsNone(r.rc, "no debería haberse lanzado ningún proceso")
            self.assertEqual(r.ms, 0.0)
        finally:
            invocacion.olvidar_hilo(ident)

    def test_olvidar_hilo_limpia_la_marca_porque_los_ident_se_reciclan(self):
        ident = threading.get_ident()
        invocacion.cancelar_hilo(ident)
        self.assertTrue(invocacion.hilo_cancelado(ident))
        invocacion.olvidar_hilo(ident)
        self.assertFalse(invocacion.hilo_cancelado(ident))
        r = invocacion.ejecutar(["ffmpeg", "-version"], timeout=PACIENCIA)
        self.assertTrue(r.ok, "tras olvidar, el hilo vuelve a poder invocar")

    def test_cancelar_un_hilo_no_toca_al_de_al_lado(self):
        """Dos trabajos a la vez: cancelar uno no puede matar al otro.

        El registro es por hilo justamente para esto. Un `taskkill` sobre «los
        hijos de este proceso» —la única alternativa sin asa— mataría los dos.
        """
        cajas = [{}, {}]
        listos = [threading.Event(), threading.Event()]

        def corre(i):
            listos[i].set()
            cajas[i]["r"] = invocacion.ejecutar(_ffmpeg_eterno(), timeout=12)
            invocacion.olvidar_hilo()

        hilos = [threading.Thread(target=corre, args=(i,), daemon=True)
                 for i in (0, 1)]
        for h in hilos:
            h.start()
        for e in listos:
            self.assertTrue(e.wait(PACIENCIA))
        self.assertTrue(_espera(lambda: invocacion.en_vuelo() >= 2))

        invocacion.cancelar_hilo(hilos[0].ident)
        hilos[0].join(timeout=PACIENCIA)
        self.assertFalse(hilos[0].is_alive())
        self.assertTrue(cajas[0]["r"].cancelado)
        # El otro sigue vivo: la prueba de que la cancelación es dirigida.
        self.assertTrue(hilos[1].is_alive())

        invocacion.cancelar_hilo(hilos[1].ident)
        hilos[1].join(timeout=PACIENCIA)
        self.assertTrue(cajas[1]["r"].cancelado)


@unittest.skipIf(not os.path.isfile(VIDEO) or shutil.which("ffmpeg") is None,
                 "falta el corpus de vídeo o ffmpeg")
class CancelarPorElServicio(unittest.TestCase):
    """Extremo a extremo por la misma puerta que usan MCP, la API y la CLI."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="c34-serv-")
        self.sv = S.Servicio(FileX(), S.Trabajos(tempfile.mkdtemp(prefix="c34-tr-")))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_job_cancelar_detiene_la_conversion_en_vuelo(self):
        """MEDIDO: `tipico.mp4 → webm` tarda ~26 s sin cancelar.

        Antes de C34 el trabajo seguía hasta el final —o hasta los 300 s del
        tope de MCP— por mucho que se pidiera `cancelar`. Ahora el trabajo pasa
        a `cancelled` en el tiempo que tarda el árbol en morir.
        """
        r = self.sv.convert(VIDEO, os.path.join(self.d, "s.webm"))
        self.assertEqual(r["estado"], S.TRABAJANDO)
        jid = r["job_id"]
        t = self.sv.trabajos.get(jid)

        # Se espera a que el motor esté REALMENTE en vuelo: cancelar antes
        # mediría la ventana entre saltos, que es otra prueba.
        self.assertTrue(_espera(lambda: invocacion.en_vuelo() > 0),
                        "el motor no llegó a arrancar")

        t0 = time.perf_counter()
        c = self.sv.job(jid, "cancelar")
        self.assertTrue(c["motor_detenido"], c)
        self.assertTrue(_espera(lambda: t.estado != S.TRABAJANDO,
                                tope=TOPE_CANCELACION),
                        "el trabajo siguió trabajando después de cancelarlo")
        ms = (time.perf_counter() - t0) * 1000

        self.assertEqual(t.estado, S.CANCELADO,
                         "cancelado no es fallido: son dos causas distintas")
        fin = self.sv.job(jid, "resultado")
        self.assertEqual(fin["estado"], S.CANCELADO)
        self.assertEqual(fin.get("motivo"), "cancelado")
        self.assertLess(ms, TOPE_CANCELACION * 1000)
        # Y no queda basura: el desechable de R18 se borra en el `finally` del
        # núcleo, así que la salida no existe.
        self.assertFalse(os.path.exists(os.path.join(self.d, "s.webm")))

    def test_cancelar_un_trabajo_de_otro_proceso_lo_dice_en_vez_de_fingir(self):
        """Un trabajo leído del disco no tiene hilo aquí. R4 en versión honesta:
        el registro es de PROCESO y la respuesta no puede aparentar otra cosa."""
        r = self.sv.convert(VIDEO, os.path.join(self.d, "s2.webm"))
        jid = r["job_id"]
        otro = S.Servicio(self.sv.fx, S.Trabajos(self.sv.trabajos.dir))
        c = otro.job(jid, "cancelar")
        self.assertFalse(c["motor_detenido"])
        self.assertIn("no corre en este proceso", c["nota"])
        self.sv.job(jid, "cancelar")                 # limpieza: que no siga


# ==========================================================================
# 2. C34 en CONTENEDOR — matar el cliente de docker no es matar nada
# ==========================================================================


def _hay_docker() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        p = subprocess.run(["docker", "version", "--format", "{{.Server.Version}}"],
                           stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=20, check=False)
        return p.returncode == 0
    except Exception:
        return False


IMAGEN = "ghcr.io/c4illin/convertx:latest"


class ContenedorPuro(unittest.TestCase):
    """Lo que se puede comprobar sin levantar un demonio."""

    def test_la_entrada_readonly_no_identifica_al_contenedor(self):
        """Solo cuenta el montaje de ESCRITURA: el desechable de R18.

        La entrada va montada `readonly` y es un fichero del usuario. Dos
        conversiones del mismo fichero a la vez lo comparten, así que contarlo
        haría que cancelar una matara el contenedor de la otra — la trampa 26
        otra vez, con otro recurso compartido.
        """
        argv = ["docker", "run", "--rm", "--mount",
                "type=bind,source=D:/tmp/a,target=/trabajo",
                "--mount", "type=bind,source=D:/tmp/b.png,target=/ent/x.png,readonly",
                "imagen"]
        f = invocacion._fuentes_de_montaje(argv)
        self.assertEqual(f, [os.path.normcase(os.path.normpath("D:/tmp/a"))])

    def test_un_motor_nativo_no_dispara_la_caza_de_contenedores(self):
        """Coste cero en el camino normal: si no es `docker run`, no hay censo."""
        self.assertEqual(invocacion._matar_contenedor_de(
            ["ffmpeg", "-i", "a.mp4", "b.webm"]), [])
        self.assertEqual(invocacion._matar_contenedor_de(
            ["docker", "ps", "-q"]), [])
        self.assertEqual(invocacion._matar_contenedor_de([]), [])


@unittest.skipUnless(_hay_docker(), "no hay demonio de docker")
class ContenedorReal(unittest.TestCase):

    def test_cancelar_mata_el_contenedor_y_no_solo_el_cliente(self):
        """MEDIDO en `CLAUDE.md` §3: matar el `docker run` NO mata el
        contenedor, y `--rm` tampoco — tres `soffice` sobrevivieron 37 minutos.

        Esta prueba mata el cliente igual que antes **y además** el contenedor,
        identificándolo por el origen de su bind mount.
        """
        d = tempfile.mkdtemp(prefix="c34-doc-")
        argv = ["docker", "run", "--rm", "--init", "--network", "none",
                "--mount", f"type=bind,source={d.replace(os.sep, '/')},target=/trabajo",
                "-w", "/trabajo", "--entrypoint", "sh", IMAGEN,
                "-c", "sleep 120"]
        caja = {}
        lanzado = threading.Event()

        def corre():
            lanzado.set()
            caja["r"] = invocacion.ejecutar(argv, timeout=PACIENCIA * 3)
            invocacion.olvidar_hilo()

        h = threading.Thread(target=corre, daemon=True)
        h.start()
        try:
            self.assertTrue(lanzado.wait(PACIENCIA))
            fuentes = set(invocacion._fuentes_de_montaje(argv))
            self.assertTrue(_espera(lambda: self._vivos(fuentes), tope=60),
                            "el contenedor no llegó a arrancar")
            self.assertTrue(invocacion.cancelar_hilo(h.ident))
            h.join(timeout=PACIENCIA)
            self.assertFalse(h.is_alive(), "el cliente de docker no murió")
            self.assertFalse(self._vivos(fuentes),
                             "el cliente murió y el CONTENEDOR siguió vivo")
        finally:
            invocacion.cancelar_hilo(h.ident)
            h.join(timeout=PACIENCIA)
            shutil.rmtree(d, ignore_errors=True)

    @staticmethod
    def _vivos(fuentes: set) -> bool:
        ids = [x for x in invocacion._docker(["ps", "-q"]).split() if x]
        if not ids:
            return False
        det = invocacion._docker(["inspect", "--format",
                                  "{{range .Mounts}}{{.Source}}\t{{end}}"] + ids)
        for linea in det.splitlines():
            m = {os.path.normcase(os.path.normpath(c))
                 for c in linea.strip().split("\t") if c}
            if m & fuentes:
                return True
        return False


# ==========================================================================
# 3. N6 — el servicio ya no es de MCP
# ==========================================================================


def _fuente(nombre: str) -> str:
    with open(os.path.join(PAQUETE, nombre), encoding="utf-8") as fh:
        return fh.read()


class ElServicioNoEsDeMcp(unittest.TestCase):

    def test_las_tres_clases_viven_en_servicio(self):
        for cls in (S.Trabajo, S.Trabajos, S.Servicio):
            self.assertEqual(cls.__module__, "filex.servicio", cls.__name__)

    def test_mcp_ya_no_define_ni_trabajos_ni_servicio(self):
        arbol = ast.parse(_fuente("mcp.py"))
        clases = {n.name for n in arbol.body if isinstance(n, ast.ClassDef)}
        self.assertEqual(clases & {"Trabajo", "Trabajos", "Servicio"}, set())
        # Ni el vocabulario de estado de SEP-1686, que es del trabajo y no del
        # protocolo: el watcher lo necesitaba y lo importaba del módulo MCP.
        asignados = {d.id for n in arbol.body if isinstance(n, ast.Assign)
                     for d in n.targets if isinstance(d, ast.Name)}
        self.assertNotIn("SONDEO_MS", asignados)

    def test_ninguna_superficie_entra_por_la_puerta_vieja(self):
        """La afirmación estructural de R10, del derecho.

        `pruebas/test_hito7.py` comprueba que la API **no reimplementa** el
        núcleo; esto comprueba que ninguna de las cuatro superficies —ni las
        pruebas— sigue tomándolo del módulo del protocolo. Sin esta prueba, una
        reexportación de cortesía dejaría el acoplamiento vivo y en silencio.
        """
        del_mcp = []
        for base, ficheros in ((PAQUETE, os.listdir(PAQUETE)),
                               (os.path.dirname(os.path.abspath(__file__)),
                                os.listdir(os.path.dirname(os.path.abspath(__file__))))):
            for f in sorted(ficheros):
                if not f.endswith(".py") or f == "mcp.py":
                    continue
                ruta = os.path.join(base, f)
                if not os.path.isfile(ruta):
                    continue
                with open(ruta, encoding="utf-8") as fh:
                    arbol = ast.parse(fh.read())
                for n in ast.walk(arbol):
                    if not isinstance(n, ast.ImportFrom) or not n.module:
                        continue
                    if n.module.split(".")[-1] != "mcp":
                        continue
                    tomados = {a.name for a in n.names}
                    if tomados & {"Servicio", "Trabajo", "Trabajos", "TRABAJANDO",
                                  "COMPLETADO", "FALLIDO", "CANCELADO"}:
                        del_mcp.append(f"{f}: {sorted(tomados)}")
        self.assertEqual(del_mcp, [])

    def test_servicio_no_importa_el_protocolo(self):
        """Al revés que antes: ahora el que no puede saber de MCP es el servicio.

        Si `filex/servicio.py` importara `mcp`, la mudanza no habría separado
        nada: habría cambiado el nombre del fichero.
        """
        arbol = ast.parse(_fuente("servicio.py"))
        nombres = set()
        for n in ast.walk(arbol):
            if isinstance(n, ast.Import):
                nombres |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom) and n.module:
                nombres.add(n.module.split(".")[-1])
        self.assertNotIn("mcp", nombres)
        # Y sigue sin haber un segundo punto de invocación (R de `invocacion`).
        self.assertNotIn("subprocess", nombres)


if __name__ == "__main__":
    unittest.main()

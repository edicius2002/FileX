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

    def test_sin_canal_de_mando_lo_dice_en_vez_de_fingir(self):
        """El alcance de C34, conservado como el ANTES medible.

        Esta prueba afirmaba el límite de C34 —*«cancelar un trabajo leído del
        disco no alcanza su `Popen`»*— y N10 lo cierra, así que ahora afirma la
        vía degradada: con `FILEX_MANDO=0` no hay canal entre procesos y la
        respuesta **sigue siendo honesta**. La otra mitad, la que prueba que con
        el canal SÍ se alcanza, está en
        `pruebas/test_cancelacion_procesos.py`, y entre procesos de verdad.
        """
        os.environ["FILEX_MANDO"] = "0"
        try:
            r = self.sv.convert(VIDEO, os.path.join(self.d, "s2.webm"))
            jid = r["job_id"]
            otro = S.Servicio(self.sv.fx, S.Trabajos(self.sv.trabajos.dir))
            c = otro.job(jid, "cancelar")
            self.assertFalse(c["motor_detenido"])
            self.assertIn("no corre en este proceso", c["nota"])
        finally:
            os.environ.pop("FILEX_MANDO", None)
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


def _hay_imagen_local(imagen: str) -> bool:
    """`docker image inspect` no descarga nada; `docker run` sobre una imagen
    ausente SÍ intenta descargarla, y eso es justo lo que hace que
    `ContenedorReal` CUELGUE en el runner de Linux (C42, `bench/ci-y-contrato.md`
    §1): el demonio SÍ está vivo ahí, pero la imagen pesa 5,7 GB y nunca está
    cacheada. `_hay_docker()` respondía la pregunta equivocada — «¿hay
    demonio?» en vez de «¿hay lo que esta clase necesita?» —, así que el
    `skipUnless` parecía honesto y no lo era."""
    if not _hay_docker():
        return False
    try:
        p = subprocess.run(["docker", "image", "inspect", imagen],
                           stdin=subprocess.DEVNULL, capture_output=True,
                           timeout=20, check=False)
        return p.returncode == 0
    except Exception:
        return False


class ContenedorPuro(unittest.TestCase):
    """Lo que se puede comprobar sin levantar un demonio.

    **a4 sustituyó la deducción por la declaración.** Hasta hoy el contenedor se
    identificaba por el origen de su bind mount de escritura, y estas pruebas
    afirmaban que el montaje `readonly` de la entrada NO contaba —porque dos
    conversiones del mismo fichero lo comparten y cancelar una habría matado el
    contenedor de la otra, la trampa 26 con otro recurso—. Con `--name` esa
    familia de fallos ya no existe: el identificador no se comparte nunca. Lo
    que se comprueba ahora es lo que la sustituye.
    """

    def test_la_orden_DECLARA_el_contenedor_en_vez_de_dejarlo_adivinar(self):
        from filex.motor_contenedor import LibreOfficeEnContenedor
        m = LibreOfficeEnContenedor()
        m.imagen = "imagen-de-prueba"
        argv = m._argv_docker("D:/tmp/e.docx", "D:/tmp/t", "e.docx", ["soffice"])
        self.assertIn("--name", argv)
        nombre = argv[argv.index("--name") + 1]
        self.assertTrue(nombre.startswith(invocacion.PREFIJO_CONTENEDOR), nombre)
        # Y se lee de vuelta desde el propio argv: cero lecturas del demonio.
        self.assertEqual(invocacion._nombre_contenedor_de(argv), nombre)

    def test_cada_invocacion_acuña_un_nombre_DISTINTO(self):
        """Un nombre constante mataría el contenedor del vecino, que es justo
        el fallo que la entrada `readonly` habría causado."""
        from filex.motor_contenedor import LibreOfficeEnContenedor
        m = LibreOfficeEnContenedor()
        m.imagen = "imagen-de-prueba"
        nombres = set()
        for _ in range(50):
            a = m._argv_docker("D:/tmp/e.docx", "D:/tmp/t", "e.docx", ["soffice"])
            nombres.add(a[a.index("--name") + 1])
        self.assertEqual(len(nombres), 50)

    def test_solo_se_acepta_un_nombre_ACUÑADO_POR_FILEX(self):
        """La cancelación no puede apuntar a un contenedor ajeno.

        Con la deducción por montajes esta garantía la daba una convención (el
        filtro de `readonly`); ahora es un predicado sobre el identificador. Un
        `--name` que llegara dentro de la orden del motor o de datos del usuario
        no lo cumple y no se toca.
        """
        for ajeno in ("filex-convertx", "postgres", "filex-snapotter",
                      "filex--", "filex-zz-" + "a" * 32, ""):
            argv = ["docker", "run", "--name", ajeno, "img"]
            self.assertEqual(invocacion._nombre_contenedor_de(argv), "", ajeno)
            self.assertEqual(invocacion._matar_contenedor_de(argv), [], ajeno)
            self.assertFalse(invocacion.matar_contenedor(ajeno), ajeno)
            self.assertFalse(invocacion.barrer_contenedor(ajeno), ajeno)

    def test_un_motor_nativo_no_dispara_la_caza_de_contenedores(self):
        """Coste cero en el camino normal: si no es `docker run`, no se mira."""
        for argv in (["ffmpeg", "-i", "a.mp4", "b.webm"],
                     ["docker", "ps", "-q"], []):
            self.assertEqual(invocacion._matar_contenedor_de(argv), [])
            self.assertEqual(invocacion._barrer_contenedor_de(argv), [])

    def test_el_gancho_parar_ya_NO_esta_muerto(self):
        """`Motor.parar()` era un `return None` que ninguna subclase
        sobrescribía (`bench/cancelacion-y-servicio.md` §4.4), justo en la única
        familia de motores que lo necesita."""
        from filex import motores
        from filex.motor_contenedor import (CalibreEnContenedor,
                                            LibreOfficeEnContenedor,
                                            PandocEnContenedor)
        for cls in (LibreOfficeEnContenedor, PandocEnContenedor,
                    CalibreEnContenedor):
            self.assertIsNot(cls.parar, motores.Motor.parar, cls.__name__)

    def test_parar_sin_contenedor_en_este_hilo_no_hace_nada(self):
        """Un `parar()` sin `orden()` previa no puede tocar a nadie: el
        peor caso de un valor por hilo tiene que ser inocuo, no ajeno."""
        import filex.motor_contenedor as mc
        from filex.motor_contenedor import LibreOfficeEnContenedor
        mc._HILO.contenedor = ""
        tocados = []
        guardado = invocacion.matar_contenedor
        invocacion.matar_contenedor = lambda n: tocados.append(n)
        try:
            LibreOfficeEnContenedor().parar()
        finally:
            invocacion.matar_contenedor = guardado
        self.assertEqual(tocados, [])


@unittest.skipUnless(_hay_imagen_local(IMAGEN),
                     "no hay demonio de docker, o la imagen %s no está cacheada "
                     "localmente (evita el cuelgue de C42: `docker run` sobre "
                     "una imagen ausente la descarga, 5,7 GB)" % IMAGEN)
class ContenedorReal(unittest.TestCase):

    @staticmethod
    def _argv(nombre: str, d: str, orden: str = "sleep 120") -> list[str]:
        return ["docker", "run", "--rm", "--init", "--network", "none",
                "--name", nombre,
                "--mount", f"type=bind,source={d.replace(os.sep, '/')},target=/trabajo",
                "-w", "/trabajo", "--entrypoint", "sh", IMAGEN, "-c", orden]

    @staticmethod
    def _existe(nombre: str) -> bool:
        """`-a`: un contenedor CREADO Y NO ARRANCADO no sale en `docker ps`.

        Ése es el estado que la deducción por montajes no podía ver nunca, y el
        que dejó 1 huérfano de 9 en la primera tanda de N-a.
        """
        salida = invocacion._docker(
            ["ps", "-a", "-q", "--filter", f"name=^{nombre}$"])
        return bool(salida.strip())

    @staticmethod
    def _vivo(nombre: str) -> bool:
        return bool(invocacion._docker(
            ["ps", "-q", "--filter", f"name=^{nombre}$"]).strip())

    def _lanza(self, argv):
        caja, lanzado = {}, threading.Event()

        def corre():
            lanzado.set()
            caja["r"] = invocacion.ejecutar(argv, timeout=PACIENCIA * 3)
            invocacion.olvidar_hilo()

        h = threading.Thread(target=corre, daemon=True)
        h.start()
        self.assertTrue(lanzado.wait(PACIENCIA))
        return h, caja

    def test_cancelar_mata_el_contenedor_y_no_solo_el_cliente(self):
        """MEDIDO en `CLAUDE.md` §3: matar el `docker run` NO mata el
        contenedor, y `--rm` tampoco — tres `soffice` sobrevivieron 37 minutos.

        Igual que antes del a4, pero identificando al contenedor por el
        **nombre que la orden declara** en vez de deducirlo del bind mount.
        """
        d = tempfile.mkdtemp(prefix="a4-doc-")
        nombre = invocacion.nombre_de_contenedor()
        argv = self._argv(nombre, d)
        h, _ = self._lanza(argv)
        try:
            self.assertTrue(_espera(lambda: self._vivo(nombre), tope=60),
                            "el contenedor no llegó a arrancar")
            self.assertTrue(invocacion.cancelar_hilo(h.ident))
            h.join(timeout=PACIENCIA)
            self.assertFalse(h.is_alive(), "el cliente de docker no murió")
            self.assertFalse(self._existe(nombre),
                             "el cliente murió y el CONTENEDOR siguió vivo")
        finally:
            invocacion.cancelar_hilo(h.ident)
            invocacion.barrer_contenedor(nombre)
            h.join(timeout=PACIENCIA)
            shutil.rmtree(d, ignore_errors=True)

    def test_cancelar_una_conversion_NO_toca_el_contenedor_de_la_de_al_lado(self):
        """Lo que N-a no pudo comprobar, y el fallo que la deducción rozaba.

        Con la entrada `readonly` contando como identificador, dos conversiones
        **del mismo fichero de entrada** habrían compartido el `.Mounts.Source`
        y cancelar una habría matado las dos. Aquí las dos comparten hasta el
        directorio de trabajo —el peor caso imaginable, que en producción no
        ocurre porque el desechable de R18 es privado— y aun así solo muere la
        cancelada: el identificador es del CONTENEDOR, no de un recurso.
        """
        d = tempfile.mkdtemp(prefix="a4-vecino-")
        n1, n2 = invocacion.nombre_de_contenedor(), invocacion.nombre_de_contenedor()
        h1, _ = self._lanza(self._argv(n1, d))
        h2, _ = self._lanza(self._argv(n2, d))
        try:
            self.assertTrue(_espera(lambda: self._vivo(n1) and self._vivo(n2),
                                    tope=90), "no arrancaron los dos")
            self.assertTrue(invocacion.cancelar_hilo(h1.ident))
            h1.join(timeout=PACIENCIA)
            self.assertFalse(self._existe(n1), "no murió el cancelado")
            self.assertTrue(self._vivo(n2),
                            "cancelar una conversión mató el contenedor de la otra")
        finally:
            for h, n in ((h1, n1), (h2, n2)):
                invocacion.cancelar_hilo(h.ident)
                invocacion.barrer_contenedor(n)
                h.join(timeout=PACIENCIA)
            shutil.rmtree(d, ignore_errors=True)

    def test_cancelar_EN_EL_ARRANQUE_no_deja_huerfano(self):
        """La carrera que costó 1 de 9 (`bench/cancelacion-y-servicio.md` §3).

        Se cancela **sin esperar** a que el contenedor exista: el cliente puede
        estar aún negociando con el demonio, o haber creado el contenedor sin
        arrancarlo — estado que `docker ps` no lista. Se comprueba con `ps -a`,
        que es lo único que lo ve.
        """
        d = tempfile.mkdtemp(prefix="a4-carrera-")
        nombre = invocacion.nombre_de_contenedor()
        h, _ = self._lanza(self._argv(nombre, d))
        try:
            invocacion.cancelar_hilo(h.ident)      # sin esperar a nada
            h.join(timeout=PACIENCIA)
            # Al demonio hay que darle margen: `--rm` borra de forma ASÍNCRONA
            # (diagnóstico de S3 en `bench/sondeo-documental.md`), y una prueba
            # que compite con el demonio no mide lo que dice medir.
            self.assertTrue(_espera(lambda: not self._existe(nombre), tope=30),
                            "quedó un contenedor huérfano del arranque")
        finally:
            invocacion.cancelar_hilo(h.ident)
            invocacion.barrer_contenedor(nombre)
            h.join(timeout=PACIENCIA)
            shutil.rmtree(d, ignore_errors=True)

    def test_parar_para_el_contenedor_cuando_el_tope_de_FUERA_dispara(self):
        """`_EnContenedor.parar()` de verdad, por la vía exacta del núcleo.

        `nucleo._un_salto` hace, en este orden: `ejecutar(...)`, y si
        `r.agotado`, `motor.parar()` **antes** de que el `finally` borre el
        desechable. Aquí se reproduce entero, y de paso se vuelve a medir el
        hallazgo que lo justifica: cuando dispara el tope de FUERA, el
        `_matar_arbol` mata al cliente y **el contenedor sigue vivo** — que es
        el estado que `Motor.parar()`, siendo un `return None`, no arreglaba.
        """
        import filex.motor_contenedor as mc
        from filex.motor_contenedor import LibreOfficeEnContenedor
        motor = LibreOfficeEnContenedor()
        motor.binario, motor.imagen = "docker", IMAGEN
        d = tempfile.mkdtemp(prefix="a4-parar-")
        caja, fin = {}, threading.Event()

        def corre():
            # `_argv_docker` es el único sitio que acuña el nombre, y lo deja
            # en el hilo. El tope de DENTRO es enorme (300 s) a propósito: el
            # que tiene que disparar aquí es el de fuera.
            argv = motor._argv_docker(os.path.join(d, "e.docx"), d, "e.docx",
                                      ["sh", "-c", "sleep 120"], 300)
            caja["nombre"] = mc._HILO.contenedor
            caja["r"] = invocacion.ejecutar(argv, timeout=12.0, cwd=d)
            caja["vivo_tras_agotarse"] = self._vivo(caja["nombre"])
            if caja["r"].agotado:
                motor.parar()              # <- exactamente lo que hace el núcleo
            invocacion.olvidar_hilo()
            fin.set()

        h = threading.Thread(target=corre, daemon=True)
        h.start()
        try:
            self.assertTrue(fin.wait(PACIENCIA * 3), "el salto no terminó")
            self.assertTrue(caja["r"].agotado, "no disparó el tope de fuera")
            self.assertTrue(caja["vivo_tras_agotarse"],
                            "matar el cliente ya mataba el contenedor: la "
                            "premisa de esta prueba dejó de valer")
            self.assertTrue(_espera(lambda: not self._existe(caja["nombre"]),
                                    tope=30),
                            "parar() no paró el contenedor")
        finally:
            invocacion.barrer_contenedor(caja.get("nombre", ""))
            h.join(timeout=PACIENCIA)
            shutil.rmtree(d, ignore_errors=True)


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

"""El cerrojo, ya extraído: que sea de MÁQUINA y que un enlace no lo esquive.

Todo lo que dice «entre procesos» se lanza con `subprocess`, que es **lo único
que distingue un hilo de un proceso** — la lección que N-b dejó escrita cuando
descubrió que `ApiConcurrencia` y `NucleoDestinoEnCurso` pasaban al 100 % con el
agujero abierto, porque lanzaban hilos.

Las dos pruebas que fallan sin el arreglo de esta ronda:

* `CerrojoDeMaquina::test_dos_directorios_de_candados_distintos_siguen_excluyendose`
  — es **la** prueba de b1. Dos procesos con `FILEX_CERROJO_DIR` distintos es la
  simulación honesta de dos usuarios de Windows, que es lo que hace que
  `%TEMP%` no sea de máquina. Con el cerrojo de N-b los dos ganan.
* `EnlaceComoDestino::test_un_enlace_duro_no_da_dos_duenos` — es b4, y entre
  procesos.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from filex import cerrojo, nucleo  # noqa: E402

ES_WINDOWS = sys.platform == "win32"

# Los hijos van como fuente por `-c`, no por fichero ni por la shell: `argv` es
# una lista, así que los backslashes de las rutas de Windows llegan enteros
# (trampa 19).
HIJO_CANDADO = (
    "import sys, os, json, time\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "os.environ['FILEX_CERROJO_DIR'] = sys.argv[2]\n"
    "from filex import cerrojo\n"
    "c = cerrojo.Candado(sys.argv[3], metadatos='hijo')\n"
    "ok = c.tomar()\n"
    "print(json.dumps({'ok': ok, 'pid': os.getpid(), 'aviso': c.aviso}), flush=True)\n"
    "time.sleep(float(sys.argv[4]))\n"
)

HIJO_DESTINO = (
    "import sys, os, json, time\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from filex import nucleo\n"
    "ok = nucleo._reservar_destino(sys.argv[2])\n"
    "print(json.dumps({'ok': ok, 'pid': os.getpid()}), flush=True)\n"
    "time.sleep(float(sys.argv[3]))\n"
)


def _lanzar(fuente: str, *args: str):
    """`(proceso, primera_linea_ya_leida)`. La cita es la línea, no un `sleep`:
    con un `sleep` se mediría el arranque del intérprete."""
    p = subprocess.Popen([sys.executable, "-c", fuente, *args],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         stdin=subprocess.DEVNULL, text=True)
    linea = p.stdout.readline()
    try:
        datos = json.loads(linea)
    except ValueError:
        p.kill()
        raise AssertionError(f"el hijo no dijo nada util: {linea!r} "
                             f"{p.stderr.read()[:400]!r}")
    return p, datos


def _matar(p) -> None:
    try:
        p.kill()
        p.wait(timeout=30)
    except Exception:
        pass


class CerrojoDeMaquina(unittest.TestCase):
    """b1: que «de máquina» deje de ser un título prestado."""

    def setUp(self):
        self.nombre = f"filex-prueba-{os.getpid()}-{self.id().rsplit('.', 1)[-1]}"
        self.dir1 = tempfile.mkdtemp(prefix="filex-cand1-")
        self.dir2 = tempfile.mkdtemp(prefix="filex-cand2-")

    @unittest.skipUnless(ES_WINDOWS, "el mutex con nombre es de Windows")
    def test_dos_directorios_de_candados_distintos_siguen_excluyendose(self):
        """**LA prueba de b1.** Dos `FILEX_CERROJO_DIR` distintos es lo que
        tendrían dos usuarios de Windows con su `%TEMP%` propio. Con solo el
        candado de fichero, los dos procesos ganan y no se ven."""
        p1, r1 = _lanzar(HIJO_CANDADO, RAIZ, self.dir1, self.nombre, "8")
        try:
            self.assertTrue(r1["ok"], "el primero tenia que tomarlo")
            p2, r2 = _lanzar(HIJO_CANDADO, RAIZ, self.dir2, self.nombre, "0")
            try:
                self.assertFalse(
                    r2["ok"],
                    "DOS DUEÑOS: el candado sigue siendo de usuario, no de "
                    "maquina — el segundo entro con otro directorio de candados")
            finally:
                _matar(p2)
        finally:
            _matar(p1)

    def test_el_mismo_directorio_tambien_excluye(self):
        """El caso que ya cerraba N-b, para que la mudanza no lo pierda."""
        p1, r1 = _lanzar(HIJO_CANDADO, RAIZ, self.dir1, self.nombre, "8")
        try:
            self.assertTrue(r1["ok"])
            p2, r2 = _lanzar(HIJO_CANDADO, RAIZ, self.dir1, self.nombre, "0")
            try:
                self.assertFalse(r2["ok"])
            finally:
                _matar(p2)
        finally:
            _matar(p1)

    def test_el_dueno_muerto_no_deja_huerfano(self):
        """`taskkill /F` no ejecuta ningún `finally`: lo tiene que soltar el
        sistema, o el siguiente espera para siempre (defecto 2 del lock viejo)."""
        p1, r1 = _lanzar(HIJO_CANDADO, RAIZ, self.dir1, self.nombre, "30")
        self.assertTrue(r1["ok"])
        if ES_WINDOWS:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(r1["pid"])],
                           capture_output=True, timeout=60)
        else:
            p1.kill()
        p1.wait(timeout=60)
        p2, r2 = _lanzar(HIJO_CANDADO, RAIZ, self.dir1, self.nombre, "0")
        try:
            self.assertTrue(r2["ok"],
                            "el candado quedo huerfano tras matar a su dueño")
        finally:
            _matar(p2)

    def test_los_metadatos_dicen_quien_lo_tiene_y_None_si_esta_libre(self):
        """Media trampa 31: por PID no se puede preguntar, así que el dueño
        tiene que dejarlo escrito. Y un fichero huérfano no debe mentir."""
        os.environ["FILEX_CERROJO_DIR"] = self.dir1
        cerrojo._dir_cache = None
        try:
            self.assertIsNone(cerrojo.dueno(self.nombre),
                              "libre tiene que responder None")
            c = cerrojo.Candado(self.nombre, metadatos="lo que sea")
            self.assertTrue(c.tomar())
            try:
                # Desde ESTE proceso el candado es nuestro, así que se consulta
                # el fichero desde fuera: es la propiedad que justifica el
                # offset de 1 GiB.
                with open(cerrojo.fichero(self.nombre), "rb") as f:
                    crudo = f.read(4096)
                texto = crudo.split(b"\x00")[0].decode("utf-8", "replace")
                self.assertIn(str(os.getpid()), texto)
                self.assertIn("lo que sea", texto)
            finally:
                c.soltar()
            self.assertIsNone(cerrojo.dueno(self.nombre))
        finally:
            os.environ.pop("FILEX_CERROJO_DIR", None)
            cerrojo._dir_cache = None

    def test_la_espera_tiene_tope_y_lo_respeta(self):
        """Lo que pide el tercer consumidor (el lock de GPU) y no piden los
        otros dos. Un lock que espera sin tope es el defecto 2 del lock viejo."""
        import time as _t

        p1, r1 = _lanzar(HIJO_CANDADO, RAIZ, self.dir1, self.nombre, "8")
        try:
            self.assertTrue(r1["ok"])
            os.environ["FILEX_CERROJO_DIR"] = self.dir1
            cerrojo._dir_cache = None
            try:
                c = cerrojo.Candado(self.nombre)
                t0 = _t.monotonic()
                ok = c.tomar(espera=0.5)
                dt = _t.monotonic() - t0
            finally:
                os.environ.pop("FILEX_CERROJO_DIR", None)
                cerrojo._dir_cache = None
            self.assertFalse(ok)
            self.assertGreaterEqual(dt, 0.4, "no espero lo que se le pidio")
            self.assertLess(dt, 5.0, "se paso del tope")
        finally:
            _matar(p1)


class EnlaceComoDestino(unittest.TestCase):
    """b4: *«un destino que sea un ENLACE sigue dando dos claves»*."""

    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="filex-enl-")
        self.real = os.path.join(self.base, "salida.webp")
        with open(self.real, "wb") as f:
            f.write(b"RIFF....WEBP" + b"\0" * 64)

    def tearDown(self):
        subprocess.run(["cmd", "/c", "rmdir", "/S", "/Q", self.base]
                       if ES_WINDOWS else ["rm", "-rf", self.base],
                       capture_output=True, timeout=60)

    def _enlace_duro(self) -> str | None:
        alias = os.path.join(self.base, "alias.webp")
        if ES_WINDOWS:
            r = subprocess.run(["cmd", "/c", "mklink", "/H", alias, self.real],
                               capture_output=True, text=True, timeout=60)
            if r.returncode:
                return None
        else:
            try:
                os.link(self.real, alias)
            except OSError:
                return None
        return alias

    def test_un_enlace_duro_no_da_dos_duenos(self):
        """El caso de b4, en el mismo proceso. Antes: `True` y `True`."""
        alias = self._enlace_duro()
        if alias is None:
            self.skipTest("esta maquina no deja crear enlaces duros")
        self.assertNotEqual(nucleo._clave_destino(self.real),
                            nucleo._clave_destino(alias),
                            "el caso pierde su gracia si las claves lexicas ya "
                            "coinciden")
        self.assertTrue(nucleo._reservar_destino(self.real))
        try:
            self.assertFalse(
                nucleo._reservar_destino(alias),
                "DOS DUEÑOS del mismo fichero por un enlace duro")
        finally:
            nucleo._soltar_destino(alias)
            nucleo._soltar_destino(self.real)

    def test_un_enlace_duro_no_da_dos_duenos_entre_procesos(self):
        alias = self._enlace_duro()
        if alias is None:
            self.skipTest("esta maquina no deja crear enlaces duros")
        p1, r1 = _lanzar(HIJO_DESTINO, RAIZ, self.real, "8")
        try:
            self.assertTrue(r1["ok"])
            p2, r2 = _lanzar(HIJO_DESTINO, RAIZ, alias, "0")
            try:
                self.assertFalse(r2["ok"], "DOS DUEÑOS entre procesos")
            finally:
                _matar(p2)
        finally:
            _matar(p1)

    def test_un_destino_que_nace_entre_reservar_y_soltar_se_suelta_igual(self):
        """La regresión que la clave de identidad podía introducir, y el motivo
        exacto por el que N-b no resolvió la ruta entera: si al soltar se
        RECALCULARA la clave, el destino recién creado traería una clave que no
        estaba en la reserva y el candado quedaría tomado para siempre."""
        nuevo = os.path.join(self.base, "aun-no-existe.webp")
        self.assertTrue(nucleo._reservar_destino(nuevo))
        with open(nuevo, "wb") as f:          # el motor escribe el destino
            f.write(b"x" * 32)
        nucleo._soltar_destino(nuevo)
        self.assertTrue(nucleo._reservar_destino(nuevo),
                        "el candado quedo tomado tras existir el destino")
        nucleo._soltar_destino(nuevo)


class ApiDelModulo(unittest.TestCase):
    """Que la mudanza sirva a los TRES consumidores, no solo al de hoy."""

    def test_el_modulo_no_depende_de_nada_de_filex(self):
        """El tercer consumidor son los arneses `.py` de `bench/`, que no son
        la aplicación: si `cerrojo` importara `filex`, la fila C38 seguiría
        cerrada por otro motivo."""
        with open(os.path.join(RAIZ, "filex", "cerrojo.py"), encoding="utf-8") as f:
            fuente = f.read()
        cuerpo = "\n".join(l for l in fuente.splitlines()
                           if l.startswith(("import ", "from ")))
        self.assertNotIn("from .", cuerpo)
        self.assertNotIn("from filex", cuerpo)
        self.assertNotIn("import filex", cuerpo)

    def test_esta_libre_y_el_gestor_de_contexto(self):
        nombre = f"filex-ctx-{os.getpid()}"
        self.assertTrue(cerrojo.esta_libre(nombre))
        with cerrojo.Candado(nombre) as c:
            self.assertTrue(c.tomado)
            self.assertFalse(cerrojo.esta_libre(nombre),
                             "esta_libre miente con el candado tomado")
        self.assertTrue(cerrojo.esta_libre(nombre))

    def test_tomarlo_dos_veces_desde_el_mismo_candado_no_se_bloquea(self):
        """Reentrada del propio objeto: `tomar()` sobre algo ya tomado no puede
        colgarse ni contar dos veces."""
        c = cerrojo.Candado(f"filex-re-{os.getpid()}")
        self.assertTrue(c.tomar())
        try:
            self.assertTrue(c.tomar())
        finally:
            c.soltar()
        self.assertFalse(c.tomado)


if __name__ == "__main__":
    unittest.main()

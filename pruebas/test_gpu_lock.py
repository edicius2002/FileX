"""C38: contrato mínimo del mutex de GPU para consumidores Python y shell."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import unittest
from unittest import mock

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from filex import gpu  # noqa: E402


HIJO = (
    "import json,sys,time; sys.path.insert(0,sys.argv[1]); "
    "from filex.gpu import Lock; x=Lock(sys.argv[2]); ok=x.tomar(espera=float(sys.argv[3])); "
    "print(json.dumps({'ok':ok,'pid':__import__('os').getpid()}),flush=True); time.sleep(float(sys.argv[4])); x.soltar()"
)


def lanzar(espera: str, retener: str):
    p = subprocess.Popen([sys.executable, "-c", HIJO, RAIZ, "prueba-c38", espera, retener],
                         stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True)
    return p, json.loads(p.stdout.readline())


def cerrar(p):
    for flujo in (p.stdout, p.stderr):
        if flujo is not None:
            flujo.close()


class GpuMutex(unittest.TestCase):
    # N29 (ronda 5, `bench/vivo-y-residuos.md`): este método estaba
    # `skipUnless(win32)` porque `_vivo()` solo sabía preguntar con
    # `tasklist` y fuera de Windows un huérfano nunca se recuperaba —MEDIDO,
    # trampa 90/93—. Arreglado en `filex.gpu._vivo_posix` (usa `os.kill`, que
    # sí tiene semántica estándar en POSIX). Control positivo Y negativo
    # ejecutados en Linux real (WSL2 Ubuntu, Python 3.14.4) en
    # `bench/vivo-y-residuos.md` §1: con el arreglo, el huérfano se recupera
    # en <5 ms; con la `_vivo()` vieja reimplantada a propósito, nunca se
    # recupera. El `skipUnless` ya no aplica: se retira.
    def test_python_excluye_y_muerto_se_libera(self):
        a, ra = lanzar("1", "30")
        self.assertTrue(ra["ok"])
        try:
            b, rb = lanzar("0", "0")
            self.assertFalse(rb["ok"])
            b.wait(timeout=20)
            cerrar(b)
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(ra["pid"])],
                               stdin=subprocess.DEVNULL, capture_output=True, timeout=20)
            else:
                a.kill()
            a.wait(timeout=20)
            c, rc = lanzar("1", "0")
            self.assertTrue(rc["ok"])
            c.wait(timeout=20)
            cerrar(c)
        finally:
            if a.poll() is None:
                a.kill()
                a.wait(timeout=20)
            cerrar(a)

    def test_api_contexto(self):
        with gpu.Lock("prueba-c38-contexto") as x:
            self.assertTrue(x.mio)
            self.assertTrue(gpu.poseido())
        self.assertFalse(gpu.poseido())


class VivoDespachaPorPlataforma(unittest.TestCase):
    """N29: `_vivo()` tiene que llamar a la rama que le toca, y solo a ésa.

    Control de MECANISMO (trampa 40): comprobar el resultado no basta —una
    `_vivo()` que siempre devuelve `True` también "pasaría" cualquier prueba
    que solo mire dueños vivos. Aquí se espía CUÁL rama se ejecuta.
    """

    def test_en_win32_llama_a_la_rama_de_tasklist(self):
        with mock.patch.object(gpu, "_vivo_win32", return_value=True) as vw, \
             mock.patch.object(gpu, "_vivo_posix", return_value=True) as vp, \
             mock.patch.object(gpu.sys, "platform", "win32"):
            gpu._vivo("123", "python.exe")
        vw.assert_called_once_with("123", "python.exe")
        vp.assert_not_called()

    def test_fuera_de_win32_llama_a_la_rama_de_os_kill(self):
        with mock.patch.object(gpu, "_vivo_win32", return_value=True) as vw, \
             mock.patch.object(gpu, "_vivo_posix", return_value=True) as vp, \
             mock.patch.object(gpu.sys, "platform", "linux"):
            gpu._vivo("123", "python3")
        vp.assert_called_once_with("123", "python3")
        vw.assert_not_called()

    def test_sin_winpid_no_roba_en_ninguna_rama(self):
        """Formato viejo (sin PID): ni siquiera se pregunta, en ninguna de
        las dos plataformas -- es el caso que ya cubría el código original."""
        for plataforma in ("win32", "linux"):
            with mock.patch.object(gpu, "_vivo_win32") as vw, \
                 mock.patch.object(gpu, "_vivo_posix") as vp, \
                 mock.patch.object(gpu.sys, "platform", plataforma):
                self.assertTrue(gpu._vivo("", "algo"))
            vw.assert_not_called()
            vp.assert_not_called()


class VivoPosixMecanismo(unittest.TestCase):
    """N29: `_vivo_posix` sondeada con `os.kill` y `/proc/<pid>/comm`
    controlados a mano, para separar las TRES respuestas de `os.kill` que
    POSIX distingue y que Windows no (`ProcessLookupError`, `PermissionError`,
    cualquier otro `OSError`) -- lo mismo que ya hace `_vivo_win32` con las
    columnas de `tasklist`.

    El control positivo Y negativo de EXTREMO A EXTREMO, sobre `filex.gpu.Lock`
    completo y en Linux real (no simulado), está en `bench/vivo-y-residuos.md`
    §1 (WSL2 Ubuntu, Python 3.14.4): con este mecanismo, un huérfano se
    recupera en <5 ms; con la `_vivo()` vieja (solo `tasklist`), nunca."""

    def test_pid_inexistente_no_esta_vivo(self):
        with mock.patch.object(gpu.os, "kill",
                                side_effect=ProcessLookupError(3, "No such process")):
            self.assertFalse(gpu._vivo_posix("12345", ""))

    def test_pid_de_otro_usuario_sin_permiso_se_asume_vivo(self):
        """EPERM significa que el proceso EXISTE (solo que no es nuestro):
        el lado seguro es no robarlo, igual que con cualquier otro error."""
        with mock.patch.object(gpu.os, "kill",
                                side_effect=PermissionError(1, "Operation not permitted")):
            self.assertTrue(gpu._vivo_posix("1", ""))

    def test_error_no_clasificado_no_roba(self):
        with mock.patch.object(gpu.os, "kill",
                                side_effect=OSError(5, "algo raro")):
            self.assertTrue(gpu._vivo_posix("123", ""))

    def test_pid_vivo_y_misma_imagen_por_prefijo_de_comm(self):
        with mock.patch.object(gpu.os, "kill", return_value=None), \
             mock.patch("builtins.open", mock.mock_open(read_data="python3\n")):
            self.assertTrue(gpu._vivo_posix("1", "python3.11"))

    def test_pid_vivo_pero_imagen_distinta_no_es_el_dueno(self):
        """PID reutilizado por otro binario -- el equivalente POSIX de que
        `tasklist` devuelva un nombre de imagen distinto."""
        with mock.patch.object(gpu.os, "kill", return_value=None), \
             mock.patch("builtins.open", mock.mock_open(read_data="otro_proceso\n")):
            self.assertFalse(gpu._vivo_posix("1", "python3.11"))

    def test_sin_proc_no_se_puede_verificar_identidad_no_roba(self):
        """Sin `/proc` (no Linux) no hay con qué comprobar el nombre: se
        responde por el lado seguro, igual que `tasklist` no disponible."""
        with mock.patch.object(gpu.os, "kill", return_value=None), \
             mock.patch("builtins.open", side_effect=FileNotFoundError()):
            self.assertTrue(gpu._vivo_posix("1", "python3.11"))

    def test_pid_vivo_sin_imagen_declarada_se_asume_vivo(self):
        with mock.patch.object(gpu.os, "kill", return_value=None):
            self.assertTrue(gpu._vivo_posix("1", ""))

    def test_winpid_no_numerico_no_roba(self):
        self.assertTrue(gpu._vivo_posix("no-es-un-numero", ""))

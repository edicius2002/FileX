"""C38: contrato mínimo del mutex de GPU para consumidores Python y shell."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import unittest

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

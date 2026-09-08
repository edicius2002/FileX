"""Prueba end-to-end del arnés CR-002; genera todos los binarios en TEMP."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


DIR = Path(__file__).resolve().parent


class DiagnosticoCR002(unittest.TestCase):
    def test_reproduce_rojos_controles_y_truncado(self):
        with tempfile.TemporaryDirectory(prefix="test-cr002-") as td:
            salida = Path(td) / "resultado.json"
            r = subprocess.run(
                [sys.executable, str(DIR / "diagnostico.py"), "--salida", str(salida)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=90,
                check=False,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            d = json.loads(salida.read_text(encoding="utf-8"))
            a = d["artefactos_transitorios"]
            self.assertEqual(a["fuente.mkv"]["verificador_proceso"]["n_pistas"], 3)
            self.assertEqual(a["fuente.mov"]["verificador_proceso"]["n_pistas"], 3)
            for origen in ("mkv", "mov"):
                v = a[f"desde-{origen}.m4a"]["verificacion"]
                self.assertEqual(v["proceso"]["veredicto"], "fallo")
                self.assertFalse(any(h["regla"] == "A1/V1" for h in v["subproceso"]["hallazgos"]))
            con = a["con-edit-list.m4a"]
            sin = a["sin-edit-list.m4a"]
            self.assertTrue(any(c["tipo"] == "elst" for c in con["isobmff_independiente"]["cajas_temporales"]))
            self.assertFalse(any(c["tipo"] == "elst" for c in sin["isobmff_independiente"]["cajas_temporales"]))
            self.assertNotEqual(
                con["ffprobe"]["format"]["duration"], sin["ffprobe"]["format"]["duration"]
            )
            self.assertNotEqual(a["truncada.m4a"]["ffprobe_rc"], 0)
            self.assertEqual(a["truncada.m4a"]["verificador"]["proceso"]["veredicto"], "fallo")


if __name__ == "__main__":
    unittest.main()

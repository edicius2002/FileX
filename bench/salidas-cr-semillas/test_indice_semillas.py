#!/usr/bin/env python3
"""Pruebas del indice portable de semillas de CR-010."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SALIDA = Path(__file__).resolve().parent
RAIZ = SALIDA.parents[1]
GENERADOR = SALIDA / "generar_indice.py"


def cargar_generador():
    spec = importlib.util.spec_from_file_location("generar_indice", GENERADOR)
    assert spec and spec.loader
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo


class IndiceSemillasTest(unittest.TestCase):
    def test_particiona_fuentes_y_conserva_ausencias(self) -> None:
        modulo = cargar_generador()
        indice = modulo.construir_indice(RAIZ)

        self.assertEqual(
            indice["denominadores"],
            {
                "corpus_versionado": 42,
                "entradas_documentales": 7,
                "pool_tokens_historicos": 111,
                "pool_roles_historicos": 10,
                "registros": 170,
            },
        )
        self.assertEqual(len(indice["semillas"]), 170)
        self.assertGreater(indice["disponibilidad"]["ausente"], 0)
        self.assertEqual(
            sum(indice["disponibilidad"].values()),
            indice["denominadores"]["registros"],
        )

    def test_cada_registro_es_portable_trazable_y_distingue_lfs(self) -> None:
        modulo = cargar_generador()
        indice = modulo.construir_indice(RAIZ)
        requeridos = {
            "id",
            "origen",
            "licencia",
            "sha256",
            "bytes",
            "formato_token",
            "uso_esperado",
            "argv_esperado",
            "ruta_relativa",
            "disponibilidad",
            "lfs",
        }
        for semilla in indice["semillas"]:
            self.assertTrue(requeridos <= semilla.keys())
            ruta = semilla["ruta_relativa"]
            self.assertFalse(ruta and (":" in ruta or ruta.startswith("/")))
            self.assertIn(semilla["licencia"]["estado"], {"conocida", "desconocida"})

        tipico = next(
            s for s in indice["semillas"]
            if s["id"] == "corpus:corpus/imagen/tipico.jpg"
        )
        self.assertEqual(tipico["disponibilidad"], "disponible")
        self.assertTrue(tipico["lfs"]["gestionado"])
        self.assertFalse(tipico["lfs"]["es_puntero"])
        self.assertEqual(len(tipico["sha256"]), 64)

        ausente = next(
            s for s in indice["semillas"]
            if s["id"] == "pool-rol:video_cif"
        )
        self.assertEqual(ausente["disponibilidad"], "ausente")
        self.assertIsNone(ausente["sha256"])

    def test_salida_es_determinista_y_comprobable(self) -> None:
        modulo = cargar_generador()
        uno = modulo.serializar(modulo.construir_indice(RAIZ))
        dos = modulo.serializar(modulo.construir_indice(RAIZ))
        self.assertEqual(uno, dos)
        json.loads(uno)

        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / "indice.json"
            subprocess.run(
                [sys.executable, "-B", "-X", "utf8", str(GENERADOR), "--salida", str(destino)],
                cwd=RAIZ,
                check=True,
            )
            comprobacion = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-X",
                    "utf8",
                    str(GENERADOR),
                    "--salida",
                    str(destino),
                    "--comprobar",
                ],
                cwd=RAIZ,
                text=True,
                capture_output=True,
            )
            self.assertEqual(comprobacion.returncode, 0, comprobacion.stderr)
            destino.write_text("{}\n", encoding="utf-8")
            obsoleto = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-X",
                    "utf8",
                    str(GENERADOR),
                    "--salida",
                    str(destino),
                    "--comprobar",
                ],
                cwd=RAIZ,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(obsoleto.returncode, 0)


if __name__ == "__main__":
    unittest.main()

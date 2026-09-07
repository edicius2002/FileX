#!/usr/bin/env python3
"""Pruebas de la particion y normalizacion de CR-007."""

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
GENERADOR = SALIDA / "generar_clasificacion.py"


def cargar_generador():
    spec = importlib.util.spec_from_file_location("generar_clasificacion", GENERADOR)
    assert spec and spec.loader
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo


class ClasificacionTest(unittest.TestCase):
    def test_particion_es_disjunta_y_exhaustiva_por_motor(self) -> None:
        modulo = cargar_generador()
        resultado = modulo.construir_clasificacion(RAIZ)
        clases = {
            "ficheros_materializables",
            "crudos_requieren_parametros",
            "protocolos",
            "metadatos",
            "directorios_paquetes",
            "alias",
            "retirados_no_aplicables",
        }

        self.assertEqual(resultado["denominadores"]["universo"], 719)
        self.assertEqual(resultado["denominadores"]["por_motor"], {"ffmpeg": 473, "imagemagick": 246})
        self.assertEqual(set(resultado["conjuntos"]), clases)
        miembros = [clave for clase in clases for clave in resultado["conjuntos"][clase]]
        self.assertEqual(len(miembros), 719)
        self.assertEqual(len(set(miembros)), 719)
        self.assertEqual(sum(resultado["denominadores"]["por_clase"].values()), 719)

    def test_separa_objetos_ambiguos_sin_equiparar_token_y_formato(self) -> None:
        modulo = cargar_generador()
        resultado = modulo.construir_clasificacion(RAIZ)
        filas = {fila["clave"]: fila for fila in resultado["filas"]}

        esperadas = {
            "ffmpeg|rgb": "crudos_requieren_parametros",
            "ffmpeg|rtsp": "protocolos",
            "ffmpeg|hls": "directorios_paquetes",
            "imagemagick|clip": "metadatos",
            "ffmpeg|alsa": "retirados_no_aplicables",
            "ffmpeg|webm": "alias",
            "imagemagick|png": "ficheros_materializables",
        }
        for clave, clase in esperadas.items():
            self.assertEqual(filas[clave]["clase_objeto"], clase)

        webm = filas["ffmpeg|webm"]
        self.assertEqual(webm["token_motor"], "webm")
        self.assertEqual(webm["identidad_motor"], "demuxer:matroska")
        self.assertEqual(webm["normalizado_motor"], "matroska")
        self.assertIn("extension", webm["roles_token"])

        png = filas["imagemagick|png"]
        self.assertEqual(png["identidad_motor"], "coder:png")
        self.assertNotEqual(png["identidad_motor"], png["token_motor"])

    def test_retirados_tienen_base_y_estado_experimental_es_independiente(self) -> None:
        modulo = cargar_generador()
        resultado = modulo.construir_clasificacion(RAIZ)
        filas = {fila["clave"]: fila for fila in resultado["filas"]}

        self.assertEqual(resultado["denominadores"]["por_clase"]["retirados_no_aplicables"], 25)
        self.assertEqual(filas["ffmpeg|alsa"]["base_clasificacion"], "C50: dispositivo confirmado")
        self.assertEqual(filas["imagemagick|http"]["base_clasificacion"], "C49: URL, no fichero")
        self.assertEqual(filas["ffmpeg|302"]["clase_objeto"], "ficheros_materializables")
        self.assertEqual(filas["ffmpeg|302"]["estado_historico"], "no_materializable")

    def test_salida_es_determinista_y_comprobable(self) -> None:
        modulo = cargar_generador()
        uno = modulo.serializar(modulo.construir_clasificacion(RAIZ))
        dos = modulo.serializar(modulo.construir_clasificacion(RAIZ))
        self.assertEqual(uno, dos)
        json.loads(uno)

        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / "clasificacion.json"
            subprocess.run(
                [sys.executable, "-B", "-X", "utf8", str(GENERADOR), "--salida", str(destino)],
                cwd=RAIZ,
                check=True,
            )
            self.assertEqual(
                subprocess.run(
                    [sys.executable, "-B", "-X", "utf8", str(GENERADOR), "--salida", str(destino), "--comprobar"],
                    cwd=RAIZ,
                ).returncode,
                0,
            )
            destino.write_text("{}\n", encoding="utf-8")
            self.assertNotEqual(
                subprocess.run(
                    [sys.executable, "-B", "-X", "utf8", str(GENERADOR), "--salida", str(destino), "--comprobar"],
                    cwd=RAIZ,
                ).returncode,
                0,
            )


if __name__ == "__main__":
    unittest.main()

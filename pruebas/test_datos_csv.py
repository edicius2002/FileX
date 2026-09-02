#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C31(a) — `_datos` deja de retener `csv_filas` y deja de MATERIALIZARLO.

`bench/firmas-contrato.md` §10 lo declaraba «lee el fichero entero en
memoria» (×1). `bench/hito3-mudanza.md` §6.1 midió que la cifra real es
**×21,3** (×7,0 en la rama degradada), y que el culpable no es el `read()`:
es `d["csv_filas"] = filas`, la lista de listas de `str` que se queda dentro
de la sonda. Ninguna regla del contrato lee `csv_filas` — solo los cuatro
agregados (`csv_n_filas`, `csv_n_campos_por_fila` en D2, `csv_cabecera`,
`filas_datos` en D1) —, así que `_datos` pasa a UN SOLO RECORRIDO de
`csv.reader` sin materializar la lista completa.

Dos familias de pruebas: **correctud** (los agregados no cambian de valor
frente al comportamiento viejo, reconstruido aquí a mano para no depender de
una copia congelada del código) y **RAM** (MEDIDO con `tracemalloc`, igual
que `bench/salidas-hito3/_datos_ram.py`, copiado a
`bench/salidas-pcd-y-memoria/_datos_ram_r6.py` para esta ronda).
"""
from __future__ import annotations

import csv
import io
import os
import sys
import tempfile
import tracemalloc
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from filex import verificador as V  # noqa: E402


def _viejo_agregados(texto: str) -> dict:
    """Reimplementación DELIBERADA del algoritmo anterior (materializando
    `filas`), para comparar contra el nuevo sin depender de git history ni de
    una copia congelada. Es el oráculo de esta prueba, no el código a probar."""
    filas = list(csv.reader(io.StringIO(texto, newline="")))
    filas = [f for f in filas if f]
    return {
        "csv_n_filas": len(filas),
        "csv_n_campos_por_fila": [len(f) for f in filas],
        "csv_cabecera": filas[0] if filas else [],
        "filas_datos": max(0, len(filas) - 1),
    }


class _ConCSV(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="c31a-datos-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.d, ignore_errors=True)

    def escribe(self, nombre, texto):
        p = os.path.join(self.d, nombre)
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(texto)
        return p


# --------------------------------------------------------------------------
# 1. Correctud: los agregados no cambian frente al algoritmo viejo
# --------------------------------------------------------------------------

class LosAgregadosNoCambian(_ConCSV):
    CASOS = {
        "normal": "a,b,c\n1,2,3\n4,5,6\n",
        "con_lineas_en_blanco": "a,b,c\n1,2,3\n\n\n4,5,6\n",
        "solo_cabecera": "a,b,c\n",
        "una_fila_sin_salto_final": "a,b,c\n1,2,3",
        "campos_desiguales": "a,b\n1,2,3\n4\n",
        "vacio": "",
    }

    def test_los_cuatro_agregados_coinciden_con_el_algoritmo_viejo(self):
        for nombre, texto in self.CASOS.items():
            with self.subTest(caso=nombre):
                p = self.escribe(nombre + ".csv", texto)
                nuevo = V._datos(p)
                viejo = _viejo_agregados(texto)
                for clave in ("csv_n_filas", "csv_n_campos_por_fila",
                             "csv_cabecera", "filas_datos"):
                    self.assertEqual(nuevo[clave], viejo[clave],
                                     f"{nombre}: {clave} difiere")

    def test_ya_no_se_retiene_csv_filas(self):
        # La afirmación central de C31(a): la clave que costaba la RAM ya no
        # se escribe. Si alguien la reintroduce, esta prueba lo dice.
        p = self.escribe("normal.csv", self.CASOS["normal"])
        self.assertNotIn("csv_filas", V._datos(p))

    def test_el_campo_demasiado_largo_sigue_degradando_igual(self):
        # La rama de `csv.Error` (el "TXT" de ImageMagick) no toca este
        # cambio: nunca llegó a materializar `filas`. Sigue devolviendo la
        # misma degradación que antes.
        texto = "a" * 200_000
        p = self.escribe("largo.csv", texto)
        d = V._datos(p)
        self.assertIn("error", d)
        self.assertEqual(d["csv_n_filas"], 0)
        self.assertEqual(d["csv_cabecera"], [])
        self.assertEqual(d["filas_datos"], 0)
        self.assertNotIn("csv_filas", d)

    def test_las_reglas_D1_D2_siguen_viendo_lo_que_necesitan(self):
        # Control de integración: D2 (`csv_n_campos_por_fila`) y D1
        # (`filas_datos`) leen la sonda, no `csv_filas`.
        p = self.escribe("desiguales.csv", self.CASOS["campos_desiguales"])
        sonda = V._datos(p)
        sonda["ruta"] = p
        h = V.punto3_propiedades(sonda, None, {})
        self.assertTrue(any(x["regla"] == "D2" for x in h), h)


# --------------------------------------------------------------------------
# 2. RAM — MEDIDO con tracemalloc, mismo método que
#    `bench/salidas-hito3/_datos_ram.py`
# --------------------------------------------------------------------------

class LaRAMBajaDeVeintiunoATresA(_ConCSV):
    """El listón histórico es ×21,3 (`bench/hito3-mudanza.md` §6.1). Aquí no
    se exige el número exacto —depende de la máquina y de Python—, solo que
    se haya quedado MUY por debajo: un umbral de ×10 deja margen de sobra
    sobre el ×6,2 medido en esta ronda (`bench/pcd-y-memoria.md`) y sigue
    siendo la mitad del listón viejo, así que una regresión hacia el
    comportamiento anterior lo dispara."""

    def test_el_pico_de_RAM_de_un_csv_grande_baja_del_umbral(self):
        fila = ",".join(str(i) for i in range(20)) + "\n"
        n = (2 << 20) // len(fila)   # ~2 MB
        texto = ",".join("c%d" % i for i in range(20)) + "\n" + fila * n
        p = self.escribe("grande.csv", texto)
        tam = os.path.getsize(p)

        tracemalloc.start()
        d = V._datos(p)
        _, pico = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        ratio = pico / tam
        self.assertGreater(d["csv_n_filas"], 0)
        self.assertLess(ratio, 10.0,
                        f"pico {pico} B sobre fichero de {tam} B: x{ratio:.2f} "
                        f"-- el listón viejo era x21,3, esto sugiere que "
                        f"`csv_filas` se ha vuelto a materializar")


if __name__ == "__main__":
    unittest.main(verbosity=2)

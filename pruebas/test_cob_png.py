"""Carril `cob/png`: pruebas del decodificador PNG a mano de `verificador.py`
y de los predictores VP8L, contra un ORACULO independiente.

Regla del carril (`bench/cobertura-png.md`): la cobertura es la unica metrica
del proyecto que se puede subir sin medir nada — un `try: f(x) except: pass`
sube el porcentaje y no afirma nada. Por eso aqui **ninguna** prueba se limita
a llamar: todas comparan contra `pruebas/fixtures_cob_png.py`, que reconstruye
la imagen entera con el algoritmo de libro y no importa una sola linea del
sujeto. El control de discriminacion de cada prueba (que linea se rompio y que
la prueba se puso roja) esta en `bench/salidas-cobertura-png/discriminacion.json`.
"""

from __future__ import annotations

import io
import os
import shutil
import struct
import subprocess
import tempfile
import unittest

from filex import verificador as V
from pruebas import fixtures_cob_png as F

TODOS_LOS_FILTROS = (0, 1, 2, 3, 4)


class BasePng(unittest.TestCase):
    """Escribe los fixtures en un desechable propio y los borra al terminar."""

    _n = 0   # contador COMPARTIDO: `escribe` lo lleva sobre `BasePng`

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="cob-png-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def escribe(self, datos, sufijo=".png"):
        BasePng._n += 1
        p = os.path.join(self.dir, "f%04d%s" % (BasePng._n, sufijo))
        with open(p, "wb") as fh:
            fh.write(datos)
        return p

    def afirma_contra_oraculo(self, datos, exacto=True):
        """alfa_min identico al del oraculo, y `primer_transparente` apuntando
        a un pixel que de verdad es transparente."""
        p = self.escribe(datos)
        ref = F.referencia(datos)
        got = V.alfa_minimo(p, "png", exacto=exacto)
        self.assertTrue(got["evaluable"], got.get("motivo"))
        self.assertAlmostEqual(got["alfa_min"], ref["alfa_min"], places=12,
                               msg="alfa_min: sujeto %r, oraculo %r"
                                   % (got["alfa_min"], ref["alfa_min"]))
        mapa, tope = F.mapa_alfa(datos)
        if ref["n_transparentes"]:
            self.assertIsNotNone(got["primer_transparente"],
                                 "hay %d pixeles transparentes y no se senala "
                                 "ninguno" % ref["n_transparentes"])
            x, y = got["primer_transparente"]
            self.assertLess(mapa[y][x], tope,
                            "primer_transparente=(%d,%d) apunta a un pixel "
                            "OPACO (alfa %d de %d)" % (x, y, mapa[y][x], tope))
        else:
            self.assertIsNone(got["primer_transparente"])
        if ref["n_transparentes"] == 1:
            self.assertEqual(tuple(got["primer_transparente"]),
                             ref["primer_transparente"])
        return got


# ---------------------------------------------------------------------------
# 1. El grueso: `_alfa_min_png` y `_alfa_min_png_adam7` contra el oraculo
# ---------------------------------------------------------------------------

class AlfaCanalReal(BasePng):
    """ct=4 (gris+alfa) y ct=6 (RGBA), 8 y 16 bits, entrelazado o no, con los
    cinco filtros de prediccion.

    16 bits se queda por debajo de 0xFF00 a proposito: el tramo de arriba lo
    cubre `DefectosVigentes.test_D1_...`, que es donde el sujeto y el oraculo
    discrepan.
    """

    def test_un_solo_pixel_transparente_en_todas_las_combinaciones(self):
        vistos = 0
        for ct in (4, 6):
            for bd, alfa in ((8, 17), (16, 4369), (16, 65279)):
                for ent in (0, 1):
                    for filtros in ((0,), (1,), (2,), (3,), (4,),
                                    TODOS_LOS_FILTROS):
                        hacer = (F.rgba_con_hueco if ct == 6
                                 else F.gris_alfa_con_hueco)
                        px = hacer(11, 7, 5, 3, alfa, bd=bd)
                        with self.subTest(ct=ct, bd=bd, ent=ent, filtros=filtros):
                            got = self.afirma_contra_oraculo(
                                F.png(px, ct, bd, entrelazado=ent,
                                      filtros=filtros))
                            self.assertEqual(tuple(got["primer_transparente"]),
                                             (5, 3))
                            vistos += 1
        self.assertEqual(vistos, 2 * 3 * 2 * 6)  # trampa 109: la prueba LLEGA

    def test_alfa_variado_por_pixel(self):
        """Muchos pixeles transparentes: el minimo no esta donde uno lo puso."""
        import random
        rnd = random.Random(20260905)
        vistos = 0
        for ct in (4, 6):
            for bd in (8, 16):
                tope = (1 << bd) - 1
                # < 0xFF00 en 16 bits: fuera de la zona del defecto D1.
                techo = 65279 if bd == 16 else 255
                can = 2 if ct == 4 else 4
                for k in range(4):
                    an, al = rnd.randint(1, 13), rnd.randint(1, 9)
                    px = [[tuple(rnd.randrange(tope + 1) for _ in range(can - 1))
                           + (rnd.choice([tope, tope, rnd.randrange(techo + 1)]),)
                           for _ in range(an)] for _ in range(al)]
                    for ent in (0, 1):
                        with self.subTest(ct=ct, bd=bd, an=an, al=al, ent=ent):
                            self.afirma_contra_oraculo(
                                F.png(px, ct, bd, entrelazado=ent,
                                      filtros=TODOS_LOS_FILTROS))
                            vistos += 1
        self.assertEqual(vistos, 2 * 2 * 4 * 2)

    def test_un_alfa_que_varia_EN_LAS_DOS_DIRECCIONES(self):
        """Control de discriminacion M04. Con un alfa casi opaco los vecinos
        del predictor Paeth valen todos 0xFF y `paeth(a,b,c)` es SIMETRICO en
        a y b: intercambiarlos no cambia nada y la prueba no lo veria. Hace
        falta un alfa que varie por filas Y por columnas, y que no sea opaco
        ni en la primera fila, para que el carril rapido no lo tape.
        """
        for filtro in TODOS_LOS_FILTROS:
            for ct, bd in ((6, 8), (4, 8), (6, 16)):
                tope = (1 << bd) - 1
                can = 2 if ct == 4 else 4
                paso = 1 if bd == 8 else 257

                def pixel(x, y, _c=can, _p=paso, _t=tope):
                    a = ((x * 37 + y * 53) % 200 + 10) * _p
                    return tuple([(x * 11 + y * 7) % (_t + 1)] * (_c - 1) + [a])

                px = F.rejilla(9, 7, pixel)
                for ent in (0, 1):
                    with self.subTest(filtro=filtro, ct=ct, bd=bd, ent=ent):
                        got = self.afirma_contra_oraculo(
                            F.png(px, ct, bd, entrelazado=ent, filtros=(filtro,)))
                        self.assertLess(got["alfa_min"], 0.05)

    def test_alfa_cero_es_alfa_cero(self):
        """El caso que mas importa al contrato: transparencia total."""
        for ent in (0, 1):
            with self.subTest(ent=ent):
                got = self.afirma_contra_oraculo(
                    F.png(F.rgba_con_hueco(9, 6, 4, 2, 0), 6, 8,
                          entrelazado=ent, filtros=TODOS_LOS_FILTROS))
                self.assertEqual(got["alfa_min"], 0.0)
                self.assertTrue(got["exacto"])
                self.assertTrue(got["tiene_alfa"])

    def test_el_alfa_trivial_no_es_transparencia(self):
        """Trampa 1: canal alfa declarado y enteramente opaco. Tiene que salir
        alfa_min = 1.0 EXACTO, o el contrato exigiria conservar un alfa que no
        existe."""
        for ct, bd in ((6, 8), (6, 16), (4, 8), (4, 16)):
            for ent in (0, 1):
                for filtros in ((0,), (1,), (2,), (3,), (4,), TODOS_LOS_FILTROS):
                    tope = (1 << bd) - 1
                    can = 2 if ct == 4 else 4
                    px = F.rejilla(10, 6, lambda x, y: tuple(
                        [(x * 7 + y * 3) % (tope + 1)] * (can - 1) + [tope]))
                    p = self.escribe(F.png(px, ct, bd, entrelazado=ent,
                                           filtros=filtros))
                    with self.subTest(ct=ct, bd=bd, ent=ent, filtros=filtros):
                        got = V.alfa_minimo(p, "png", exacto=True)
                        self.assertEqual(got["alfa_min"], 1.0)
                        self.assertTrue(got["tiene_alfa"])
                        self.assertTrue(got["exacto"])
                        self.assertIsNone(got["primer_transparente"])
                        self.assertEqual(
                            got["filas_leidas"],
                            F.filas_adam7(10, 6) if ent else 6,
                            "la imagen opaca hay que recorrerla ENTERA")


class SinMecanismoDeAlfa(BasePng):
    """El 90 % del corpus real: un PNG que ni tiene canal alfa ni trae tRNS es
    opaco POR CONSTRUCCION, y se resuelve leyendo la cabecera. Es el camino
    barato, y es el que mas se ejecuta en produccion."""

    def test_rgb_y_gris_sin_trns_salen_por_la_cabecera(self):
        vistos = 0
        for ct, bd in ((2, 8), (2, 16), (0, 8), (0, 16), (0, 1), (0, 4), (3, 8)):
            can = F.CANALES[ct]
            tope = (1 << bd) - 1
            px = F.rejilla(7, 5, lambda x, y: (((x * 3 + y) % (tope + 1),) * can
                                               if can > 1 else (x + y) % (tope + 1)))
            plte = [(i, i, i) for i in range(1 << min(bd, 8))] if ct == 3 else None
            for ent in (0, 1):
                p = self.escribe(F.png(px, ct, bd, plte=plte, entrelazado=ent,
                                       filtros=TODOS_LOS_FILTROS))
                with self.subTest(ct=ct, bd=bd, ent=ent):
                    got = V.alfa_minimo(p, "png", exacto=True)
                    self.assertTrue(got["evaluable"])
                    self.assertEqual(got["alfa_min"], 1.0)
                    self.assertFalse(got["tiene_alfa"])
                    self.assertTrue(got["exacto"])
                    self.assertEqual(got["via"], "cabecera")
                    self.assertEqual(got["filas_leidas"], 0,
                                     "no se puede leer un solo pixel aqui")
                    self.assertIs(got["alfa_no_trivial"], False)
                    vistos += 1
        self.assertEqual(vistos, 14)


class AtajoDeFilaOpaca(BasePng):
    """El carril rapido: una fila 100 % opaca se reconoce por el PATRON de sus
    bytes filtrados, sin desfiltrarla. Si el patron estuviera mal, una fila
    opaca se tomaria por transparente (o al reves)."""

    def test_el_patron_reconoce_la_fila_opaca_con_cada_filtro(self):
        """Opaco entero: `_rep` y `_PATRON_OPACO` deciden las 6 filas."""
        for filtro in TODOS_LOS_FILTROS:
            for bd in (8, 16):
                tope = (1 << bd) - 1
                px = F.rejilla(12, 6, lambda x, y: ((x * 11) % (tope + 1),
                                                    (y * 13) % (tope + 1),
                                                    (x + y) % (tope + 1), tope))
                p = self.escribe(F.png(px, 6, bd, filtros=(filtro,)))
                with self.subTest(filtro=filtro, bd=bd):
                    got = V.alfa_minimo(p, "png", exacto=False)
                    self.assertEqual(got["alfa_min"], 1.0)
                    self.assertEqual(got["filas_leidas"], 6)
                    self.assertTrue(got["exacto"])

    def test_la_salida_del_atajo_reconstruye_bien_la_fila_siguiente(self):
        """Fila 0 opaca (atajo) y fila 1 transparente: al salir del atajo la
        fila anterior se da por 0xFF, no por ceros. Un error ahi desplaza el
        alfa reconstruido en la fila del hueco."""
        for filtro in TODOS_LOS_FILTROS:
            for y_hueco in (1, 2, 5):
                px = F.rgba_con_hueco(10, 6, 4, y_hueco, 33)
                datos = F.png(px, 6, 8, filtros=(filtro,))
                with self.subTest(filtro=filtro, y=y_hueco):
                    got = self.afirma_contra_oraculo(datos)
                    self.assertEqual(tuple(got["primer_transparente"]),
                                     (4, y_hueco))
                    # el atajo cortocircuita las filas opacas de arriba: sin
                    # `exacto` la lectura para justo en la fila del hueco
                    flojo = V.alfa_minimo(self.escribe(datos), "png",
                                          exacto=False)
                    self.assertEqual(flojo["filas_leidas"], y_hueco + 1)

    def test_el_hueco_en_la_fila_cero_usa_ceros_como_fila_previa(self):
        for filtro in TODOS_LOS_FILTROS:
            with self.subTest(filtro=filtro):
                got = self.afirma_contra_oraculo(
                    F.png(F.rgba_con_hueco(10, 4, 6, 0, 21), 6, 8,
                          filtros=(filtro,)))
                self.assertEqual(tuple(got["primer_transparente"]), (6, 0))

    def test_rep_devuelve_el_relleno_pedido(self):
        self.assertEqual(V._rep(0, 5), b"\x00" * 5)
        self.assertEqual(V._rep(255, 4), b"\xff" * 4)
        self.assertEqual(V._rep(128, 3), b"\x80" * 3)
        self.assertEqual(V._rep(255, 0), b"")
        self.assertEqual(V._rep(7, 2), V._rep(7, 2))  # la cache no cambia nada


class Paleta(BasePng):
    """ct=3 con tRNS: 1, 2, 4 y 8 bits por pixel."""

    @staticmethod
    def _paleta(n):
        return [(i * 17 % 256, i * 29 % 256, i * 43 % 256) for i in range(n)]

    def test_todas_las_profundidades_contra_el_oraculo(self):
        vistos = 0
        for bd in (1, 2, 4, 8):
            n = 1 << bd
            pal = self._paleta(n)
            for an in (1, 3, 7, 8, 9, 17):
                trns = [255] * n
                trns[min(1, n - 1)] = 90
                px = F.indices(an, 4, lambda x, y: (x * 3 + y) % n)
                for ent in (0, 1):
                    with self.subTest(bd=bd, an=an, ent=ent):
                        self.afirma_contra_oraculo(
                            F.png(px, 3, bd, plte=pal, trns=trns,
                                  entrelazado=ent, filtros=TODOS_LOS_FILTROS))
                        vistos += 1
        self.assertEqual(vistos, 4 * 6 * 2)

    def test_los_bits_de_relleno_de_la_ultima_celda_no_son_pixeles(self):
        """an=3 con 4 bits deja media celda de relleno. Si esos bits contaran,
        el indice 0 (transparente aqui) los haria salir por transparentes."""
        pal = self._paleta(16)
        trns = [7] + [255] * 15          # SOLO el indice 0 es transparente
        px = F.indices(3, 3, lambda x, y: 1 + ((x + y) % 15))
        for ent in (0, 1):
            p = self.escribe(F.png(px, 3, 4, plte=pal, trns=trns,
                                   entrelazado=ent, filtros=TODOS_LOS_FILTROS))
            with self.subTest(ent=ent):
                got = V.alfa_minimo(p, "png", exacto=True)
                self.assertEqual(got["alfa_min"], 1.0)
                self.assertIsNone(got["primer_transparente"])

    def test_la_coordenada_x_es_del_PIXEL_y_no_del_BYTE(self):
        """El fallo que documenta `_pixel_en_byte`: con 2 bits por pixel el
        pixel (12,2) se publicaba como (3,2), un factor 4."""
        pal = self._paleta(4)
        trns = [255, 255, 255, 40]
        px = F.indices(16, 4, lambda x, y: 3 if (x, y) == (12, 2) else 0)
        for ent in (0, 1):
            p = self.escribe(F.png(px, 3, 2, plte=pal, trns=trns,
                                   entrelazado=ent, filtros=TODOS_LOS_FILTROS))
            with self.subTest(ent=ent):
                got = V.alfa_minimo(p, "png", exacto=True)
                self.assertEqual(tuple(got["primer_transparente"]), (12, 2))
                self.assertAlmostEqual(got["alfa_min"], 40 / 255.0, places=12)

    def test_la_paleta_tambien_corta_en_cuanto_encuentra_transparencia(self):
        """Con alfa 0 el barrido para en la fila del hueco aunque se pida
        `exacto`: no hay nada por debajo de 0."""
        pal = self._paleta(16)
        trns = [255] * 16
        trns[7] = 0
        px = F.indices(9, 6, lambda x, y: 7 if (x, y) == (4, 1) else 0)
        for exacto in (False, True):
            p = self.escribe(F.png(px, 3, 4, plte=pal, trns=trns,
                                   filtros=TODOS_LOS_FILTROS))
            with self.subTest(exacto=exacto):
                got = V.alfa_minimo(p, "png", exacto=exacto)
                self.assertEqual(got["alfa_min"], 0.0)
                self.assertTrue(got["exacto"])
                self.assertEqual(got["filas_leidas"], 2)
                self.assertEqual(tuple(got["primer_transparente"]), (4, 1))
        # y sin `exacto`, un alfa intermedio tambien corta
        trns[7] = 120
        p = self.escribe(F.png(px, 3, 4, plte=pal, trns=trns,
                               filtros=TODOS_LOS_FILTROS))
        flojo = V.alfa_minimo(p, "png", exacto=False)
        self.assertEqual(flojo["filas_leidas"], 2)
        self.assertFalse(flojo["exacto"])
        self.assertAlmostEqual(flojo["alfa_min"], 120 / 255.0, places=12)

    def test_trns_mas_corto_que_la_paleta(self):
        """Los indices que el tRNS no cubre son opacos (norma PNG)."""
        pal = self._paleta(256)
        trns = [255, 255, 60]            # solo tres entradas
        px = F.indices(9, 4, lambda x, y: (x * 5 + y * 3) % 256)
        for ent in (0, 1):
            with self.subTest(ent=ent):
                self.afirma_contra_oraculo(
                    F.png(px, 3, 8, plte=pal, trns=trns, entrelazado=ent,
                          filtros=TODOS_LOS_FILTROS))

    def test_trns_presente_pero_enteramente_opaco(self):
        """Trampa 1 en su version de paleta: tRNS declarado y todo 255. Se sale
        por la cabecera, sin leer un solo pixel."""
        pal = self._paleta(16)
        px = F.indices(8, 5, lambda x, y: (x + y) % 16)
        for ent, via in ((0, "cabecera"), (1, "cabecera (tRNS opaco)")):
            p = self.escribe(F.png(px, 3, 4, plte=pal, trns=[255] * 16,
                                   entrelazado=ent, filtros=TODOS_LOS_FILTROS))
            with self.subTest(ent=ent):
                got = V.alfa_minimo(p, "png", exacto=True)
                self.assertEqual(got["alfa_min"], 1.0)
                self.assertEqual(got["filas_leidas"], 0)
                self.assertEqual(got["via"], via)
                self.assertFalse(got["tiene_alfa"] if ent else False)


class Exactitud(BasePng):
    """`exacto=False` corta en cuanto encuentra transparencia; `exacto=True`
    recorre. El campo `exacto` tiene que decir cual de las dos cosas paso."""

    def test_sin_exacto_corta_en_la_primera_fila_con_alfa(self):
        px = F.rejilla(8, 6, lambda x, y: (0, 0, 0, 255 if y < 2 else (200 - y * 40)))
        p = self.escribe(F.png(px, 6, 8, filtros=TODOS_LOS_FILTROS))
        flojo = V.alfa_minimo(p, "png", exacto=False)
        estricto = V.alfa_minimo(p, "png", exacto=True)
        ref = F.referencia(F.png(px, 6, 8, filtros=TODOS_LOS_FILTROS))
        self.assertEqual(flojo["filas_leidas"], 3)
        self.assertEqual(estricto["filas_leidas"], 6)
        self.assertFalse(flojo["exacto"])
        self.assertTrue(estricto["exacto"])
        self.assertGreater(flojo["alfa_min"], estricto["alfa_min"])
        self.assertAlmostEqual(estricto["alfa_min"], ref["alfa_min"], places=12)

    def test_sin_exacto_pero_con_alfa_cero_sigue_siendo_exacto(self):
        px = F.rgba_con_hueco(8, 6, 3, 1, 0)
        p = self.escribe(F.png(px, 6, 8, filtros=TODOS_LOS_FILTROS))
        got = V.alfa_minimo(p, "png", exacto=False)
        self.assertEqual(got["alfa_min"], 0.0)
        self.assertTrue(got["exacto"])

    def test_adam7_sin_exacto_corta_la_pasada_y_el_barrido(self):
        px = F.rgba_con_hueco(16, 16, 0, 0, 64)   # el hueco cae en la pasada 1
        p = self.escribe(F.png(px, 6, 8, entrelazado=1,
                               filtros=TODOS_LOS_FILTROS))
        flojo = V.alfa_minimo(p, "png", exacto=False)
        estricto = V.alfa_minimo(p, "png", exacto=True)
        self.assertEqual(flojo["filas_leidas"], 1)
        self.assertFalse(flojo["exacto"])
        self.assertGreater(estricto["filas_leidas"], 1)
        self.assertAlmostEqual(estricto["alfa_min"], 64 / 255.0, places=12)


class CaminosDeError(BasePng):
    """Los `evaluable=False`. Un verificador que no distingue «comprobado» de
    «no he podido comprobarlo» repite el fallo de markitdown-mcp; estas son las
    ramas que lo dicen."""

    def _no_evaluable(self, datos, trozo_del_motivo, alfa_min=None):
        p = self.escribe(datos)
        got = V.alfa_minimo(p, "png", exacto=True)
        self.assertFalse(got["evaluable"])
        self.assertEqual(got["alfa_min"], alfa_min)
        self.assertIn(trozo_del_motivo, got["motivo"])
        return got

    def test_ihdr_ilegible(self):
        """Sin IHDR no hay tipo de color, y sin tipo de color no hay veredicto
        que dar. El fichero pasa la firma: es el caso peligroso.

        DEFECTO D4 (vigente): esta es la UNICA de las siete salidas
        `evaluable=False` de `_alfa_min_png` que no pone `alfa_min` a None; se
        va con el 1.0 del valor inicial. Un consumidor que lea `alfa_min` sin
        mirar `evaluable` recibe «opaco» de un fichero que el verificador
        acaba de declarar ilegible. Si esta linea se pone roja es que D4 se
        arreglo: cambia el `1.0` por `None` y anotalo.
        """
        malo = F.FIRMA + F.trozo(b"IDAT", b"x") + F.trozo(b"IEND", b"")
        got = self._no_evaluable(malo, "IHDR ilegible", alfa_min=1.0)
        self.assertFalse(got["tiene_alfa"])

    def test_trns_de_color_clave_no_es_un_canal_alfa(self):
        """ct 0 y 2 con tRNS: transparencia por VALOR de color. El verificador
        dice que no puede, en vez de inventar un numero."""
        for ct, trns in ((0, b"\x00\x05"), (2, b"\x00\x01\x00\x02\x00\x03")):
            can = F.CANALES[ct]
            px = F.rejilla(6, 4, lambda x, y: ((x + y) % 8,) * can if can > 1
                           else (x + y) % 8)
            for ent in (0, 1):
                with self.subTest(ct=ct, ent=ent):
                    got = self._no_evaluable(
                        F.png(px, ct, 8, trns=trns, entrelazado=ent,
                              filtros=TODOS_LOS_FILTROS),
                        "tRNS de color clave (ct=%d)" % ct)
                    self.assertTrue(got["tiene_alfa"])

    def test_sin_idat(self):
        px = F.rgba_con_hueco(4, 3, 1, 1, 8)
        for ent in (0, 1):
            with self.subTest(ent=ent):
                self._no_evaluable(F.png(px, 6, 8, entrelazado=ent,
                                         sin_idat=True), "sin IDAT")

    def test_profundidad_no_valida_para_un_canal_alfa(self):
        """ct 4 y 6 solo admiten 8 y 16 bits. Con 4, `bps` sale 0 y el carril
        del alfa no existe: hay que decirlo, no dividir por cero."""
        px = F.rejilla(6, 3, lambda x, y: ((x + y) % 16, 15))
        for ent in (0, 1):
            with self.subTest(ent=ent):
                self._no_evaluable(F.png(px, 4, 4, entrelazado=ent,
                                         filtros=(0,)),
                                   "profundidad 4 no valida")

    def test_filtro_de_fila_desconocido(self):
        """Un byte de filtro > 4 es un fichero corrupto, no un filtro nuevo."""
        for ent in (0, 1):
            datos = bytearray(F.png(F.rgba_con_hueco(5, 3, 2, 1, 9), 6, 8,
                                    entrelazado=ent, filtros=(0,)))
            # se reescribe el IDAT entero con un byte de filtro invalido
            import zlib
            crudo = bytearray()
            filas = 3 if not ent else 1
            ancho = 5 if not ent else 1
            for _ in range(filas):
                crudo.append(9)
                crudo += bytes(ancho * 4)
            nuevo = bytearray(F.FIRMA)
            ihdr = struct.pack(">IIBBBBB", 5, 3, 8, 6, 0, 0, ent)
            nuevo += F.trozo(b"IHDR", ihdr)
            nuevo += F.trozo(b"IDAT", zlib.compress(bytes(crudo), 6))
            nuevo += F.trozo(b"IEND", b"")
            with self.subTest(ent=ent):
                self._no_evaluable(bytes(nuevo), "filtro PNG 9 desconocido")

    def test_adam7_con_el_idat_cortado(self):
        """El generador de bloques se queda sin datos a mitad de una pasada."""
        entero = F.png(F.rgba_con_hueco(16, 16, 9, 9, 12), 6, 8,
                       entrelazado=1, filtros=TODOS_LOS_FILTROS)
        cortado = F.png(F.rgba_con_hueco(16, 16, 9, 9, 12), 6, 8,
                        entrelazado=1, filtros=TODOS_LOS_FILTROS,
                        recorta_idat=12)
        self.assertNotEqual(entero, cortado)
        self._no_evaluable(cortado, "IDAT incompleto en la pasada Adam7")

    def test_varios_idat_se_concatenan(self):
        """El flujo zlib esta partido en cinco IDAT: si `rellenar` no los
        encadenara, la imagen saldria corrupta o incompleta."""
        px = F.rgba_con_hueco(24, 20, 17, 15, 11)
        for ent in (0, 1):
            with self.subTest(ent=ent):
                self.afirma_contra_oraculo(
                    F.png(px, 6, 8, entrelazado=ent,
                          filtros=TODOS_LOS_FILTROS, trocea=5))


class Adam7Geometria(BasePng):
    """Adam7 no cambia el filtrado: cambia la GEOMETRIA. Estas pruebas juzgan
    el mapeo (pasada, fila, columna) -> (x, y) de la imagen real."""

    def test_un_solo_pixel_transparente_barriendo_toda_la_rejilla_8x8(self):
        """64 posiciones: cada una cae en una pasada distinta del mosaico."""
        vistos = 0
        for hy in range(8):
            for hx in range(8):
                px = F.rgba_con_hueco(8, 8, hx, hy, 5)
                with self.subTest(hx=hx, hy=hy):
                    got = self.afirma_contra_oraculo(
                        F.png(px, 6, 8, entrelazado=1,
                              filtros=TODOS_LOS_FILTROS))
                    self.assertEqual(tuple(got["primer_transparente"]), (hx, hy))
                    vistos += 1
        self.assertEqual(vistos, 64)

    def test_imagenes_pequenas_dejan_pasadas_vacias(self):
        """Con 1x1, 3x2 o 5x1 varias de las siete pasadas no tienen ni una
        fila: la rama que las salta tiene que saltarlas bien."""
        for an, al in ((1, 1), (1, 5), (5, 1), (3, 2), (2, 3), (7, 7), (9, 9)):
            px = F.rgba_con_hueco(an, al, an - 1, al - 1, 44)
            with self.subTest(an=an, al=al):
                got = self.afirma_contra_oraculo(
                    F.png(px, 6, 8, entrelazado=1, filtros=TODOS_LOS_FILTROS))
                self.assertEqual(tuple(got["primer_transparente"]),
                                 (an - 1, al - 1))

    def test_paleta_entrelazada_de_pocos_bits(self):
        pal = [(i * 16, 255 - i * 16, 128) for i in range(16)]
        trns = [255] * 16
        trns[5] = 12
        for an, al in ((17, 9), (8, 8), (3, 11)):
            px = F.indices(an, al, lambda x, y: 5 if (x, y) == (an - 1, 0) else 0)
            with self.subTest(an=an, al=al):
                got = self.afirma_contra_oraculo(
                    F.png(px, 3, 4, plte=pal, trns=trns, entrelazado=1,
                          filtros=TODOS_LOS_FILTROS))
                self.assertEqual(tuple(got["primer_transparente"]), (an - 1, 0))


# ---------------------------------------------------------------------------
# 2. `_leer_plte` y el desfiltrado por fila completa (`_paeth`)
# ---------------------------------------------------------------------------

class LeerPaleta(BasePng):

    PAL = [(0, 0, 0), (255, 255, 255), (255, 0, 0), (0, 255, 0)]

    @staticmethod
    def _lum(c):
        return (c[0] * 299 + c[1] * 587 + c[2] * 114) // 1000

    def _tinta_esperada(self, px, pal, x0, y0, x1, y1):
        lums = [self._lum(pal[px[y][x]]) for y in range(y0, y1)
                for x in range(x0, x1)]
        fondo = max(set(lums), key=lambda v: (lums.count(v), -v))
        return 100.0 * sum(1 for v in lums if abs(v - fondo) > 64) / len(lums)

    def test_la_paleta_leida_decide_la_tinta(self):
        """`png_tinta_cajas` sobre un PNG de paleta: si `_leer_plte` devolviera
        la paleta desplazada un byte, la luminancia de cada indice cambiaria y
        el porcentaje de tinta con ella."""
        px = F.indices(12, 8, lambda x, y: 1 if (x + y) % 3 else 0)
        p = self.escribe(F.png(px, 3, 8, plte=self.PAL, filtros=TODOS_LOS_FILTROS))
        got = V.png_tinta_cajas(p, [(0, 0, 12, 8)])
        self.assertTrue(got["evaluable"], got.get("motivo"))
        self.assertAlmostEqual(got["tinta_max_pct"],
                               round(self._tinta_esperada(px, self.PAL, 0, 0, 12, 8), 3),
                               places=3)
        self.assertEqual(got["cajas"][0]["pixeles"], 96)

    def test_un_trozo_antes_del_PLTE_se_salta(self):
        """La paleta no tiene por que ir pegada al IHDR."""
        px = F.indices(12, 8, lambda x, y: 1 if (x + y) % 3 else 0)
        relleno = F.trozo(b"cHRM", b"\x00" * 32)
        p = self.escribe(F.png(px, 3, 8, plte=self.PAL, extra=(relleno,),
                               filtros=TODOS_LOS_FILTROS))
        got = V.png_tinta_cajas(p, [(0, 0, 12, 8)])
        self.assertTrue(got["evaluable"], got.get("motivo"))
        self.assertAlmostEqual(got["tinta_max_pct"],
                               round(self._tinta_esperada(px, self.PAL, 0, 0, 12, 8), 3),
                               places=3)

    def test_paleta_ausente(self):
        px = F.indices(6, 4, lambda x, y: 0)
        p = self.escribe(F.png(px, 3, 8, filtros=(0,)))
        got = V.png_tinta_cajas(p, [(0, 0, 6, 4)])
        self.assertFalse(got["evaluable"])
        self.assertEqual(got["motivo"], "PNG de paleta sin PLTE")

    def test_el_flujo_se_acaba_antes_del_PLTE(self):
        """Rama inalcanzable desde `png_tinta_cajas` (el PNG ya tiene que
        traer IDAT para llegar aqui), asi que se juzga la funcion directa."""
        self.assertIsNone(V._leer_plte(io.BytesIO(b"")))
        self.assertIsNone(V._leer_plte(io.BytesIO(b"\x00\x00\x00\x04")))

    def test_una_paleta_de_tres_bytes(self):
        pal = V._leer_plte(io.BytesIO(F.trozo(b"PLTE", b"\x01\x02\x03")))
        self.assertEqual(pal, [(1, 2, 3)])

    def test_el_desfiltrado_por_fila_completa_reconstruye_los_colores(self):
        """`_desfiltrar_fila` (la version con `bpp`, distinta de la del carril)
        pasa por `_paeth`. Se juzga con un RGB de tres canales, donde un `bpp`
        equivocado mezcla los canales."""
        px = F.rejilla(9, 6, lambda x, y: ((x * 25) % 256, (y * 37) % 256,
                                           (x * y * 13) % 256))
        p = self.escribe(F.png(px, 2, 8, filtros=TODOS_LOS_FILTROS))
        got = V.png_tinta_cajas(p, [(0, 0, 9, 6)])
        self.assertTrue(got["evaluable"], got.get("motivo"))
        lums = [self._lum(px[y][x]) for y in range(6) for x in range(9)]
        fondo = max(set(lums), key=lambda v: (lums.count(v), -v))
        esperado = 100.0 * sum(1 for v in lums if abs(v - fondo) > 64) / len(lums)
        self.assertAlmostEqual(got["tinta_max_pct"], round(esperado, 3), places=3)

    def test_adam7_no_se_finge_capaz(self):
        px = F.indices(8, 8, lambda x, y: 0)
        p = self.escribe(F.png(px, 3, 8, plte=self.PAL, entrelazado=1,
                               filtros=(0,)))
        got = V.png_tinta_cajas(p, [(0, 0, 8, 8)])
        self.assertFalse(got["evaluable"])
        self.assertIn("Adam7", got["motivo"])


class Paeth(unittest.TestCase):
    """El predictor Paeth de la norma, contra una reescritura independiente,
    exhaustivo sobre las esquinas y a fondo sobre el rango entero."""

    def test_exhaustivo_sobre_un_octante(self):
        vistos = 0
        for a in range(0, 256, 7):
            for b in range(0, 256, 11):
                for c in range(0, 256, 13):
                    self.assertEqual(V._paeth(a, b, c), F._paeth_ref(a, b, c),
                                     "paeth(%d,%d,%d)" % (a, b, c))
                    vistos += 1
        self.assertGreater(vistos, 8000)

    def test_los_empates_van_por_a_luego_b_luego_c(self):
        """La norma fija el desempate; cambiarlo mueve pixeles sin dar error."""
        self.assertEqual(V._paeth(10, 10, 10), 10)
        self.assertEqual(V._paeth(0, 255, 0), 255)      # pb=0 gana
        self.assertEqual(V._paeth(255, 0, 0), 255)      # pa=0 gana
        self.assertEqual(V._paeth(3, 5, 4), 4)          # pa=1, pb=1, pc=0 -> c
        self.assertEqual(V._paeth(100, 100, 0), 100)    # pa=pb=100 < pc -> a
        self.assertEqual(V._paeth(0, 10, 0), 10)        # pb=0 -> b
        self.assertEqual(V._paeth(200, 0, 100), 100)    # pc=0 -> c


# ---------------------------------------------------------------------------
# 3. Predictores VP8L (WebP sin perdida)
# ---------------------------------------------------------------------------

class PredictoresVp8l(unittest.TestCase):
    """Los 14 predictores de `_predice` contra el oraculo escrito desde la
    especificacion de libwebp. El modo 13 esta aparte: divergen (defecto D2)."""

    SEMILLAS = (0x00000000, 0xFFFFFFFF, 0xFF000000, 0x0000FF00, 0x80808080,
                0x017F01FE, 0x01020304, 0xFEFDFCFB, 0x7F80817E, 0x0A0A0A0A,
                0x0F0F0F0F, 0x1E1E1E1E, 0xC0FFEE00, 0xDEADBEEF)

    @staticmethod
    def _vecindad(L, T, TL, TR):
        w = 8
        px = [0] * 32
        i = 12
        px[i - 1], px[i - w], px[i - w - 1], px[i - w + 1] = L, T, TL, TR
        return px, i, w

    def test_los_trece_modos_que_coinciden_con_libwebp(self):
        import itertools
        vistos = {m: 0 for m in range(14) if m != 13}
        for L, T, TL, TR in itertools.islice(
                itertools.product(self.SEMILLAS, repeat=4), 0, None, 7):
            px, i, w = self._vecindad(L, T, TL, TR)
            for modo in range(14):
                if modo == 13:
                    continue
                with self.subTest(modo=modo, L=L, T=T, TL=TL, TR=TR):
                    self.assertEqual(V._predice(modo, px, i, w),
                                     F.predice_ref(modo, L, T, TL, TR))
                vistos[modo] += 1
        self.assertTrue(all(v > 500 for v in vistos.values()), vistos)

    def test_el_modo_0_es_opaco_negro(self):
        px, i, w = self._vecindad(1, 2, 3, 4)
        self.assertEqual(V._predice(0, px, i, w), 0xFF000000)

    def test_los_modos_1_a_4_son_los_cuatro_vecinos(self):
        px, i, w = self._vecindad(0x11111111, 0x22222222, 0x33333333, 0x44444444)
        self.assertEqual(V._predice(1, px, i, w), 0x11111111)   # izquierda
        self.assertEqual(V._predice(2, px, i, w), 0x22222222)   # arriba
        self.assertEqual(V._predice(3, px, i, w), 0x44444444)   # arriba-derecha
        self.assertEqual(V._predice(4, px, i, w), 0x33333333)   # arriba-izquierda

    def test_un_predictor_inexistente_es_un_error_declarado(self):
        px, i, w = self._vecindad(1, 2, 3, 4)
        for modo in (14, 15, 99):
            with self.assertRaises(ValueError):
                V._predice(modo, px, i, w)

    def test_selecciona_elige_el_vecino_que_menos_se_aleja(self):
        for a, b, c in ((0x00000000, 0xFFFFFFFF, 0x00000000),
                        (0xFFFFFFFF, 0x00000000, 0x00000000),
                        (0x10203040, 0x40302010, 0x20304050),
                        (0x80808080, 0x80808080, 0x00000000)):
            with self.subTest(a=a, b=b, c=c):
                self.assertEqual(V._selecciona(a, b, c), F.selecciona_ref(a, b, c))
        # empate: la norma se queda con `a`
        self.assertEqual(V._selecciona(0x0A0A0A0A, 0x0A0A0A0A, 0x05050505),
                         0x0A0A0A0A)

    def test_clamp_full_satura_en_0_y_en_255_canal_a_canal(self):
        self.assertEqual(V._clamp_full(0xFFFFFFFF, 0xFFFFFFFF, 0x00000000),
                         0xFFFFFFFF)
        self.assertEqual(V._clamp_full(0x00000000, 0x00000000, 0xFFFFFFFF),
                         0x00000000)
        self.assertEqual(V._clamp_full(0x0A140A14, 0x0A140A14, 0x05050505),
                         F.clamp_full_ref(0x0A140A14, 0x0A140A14, 0x05050505))
        for a in self.SEMILLAS:
            for b in self.SEMILLAS:
                for c in self.SEMILLAS[:5]:
                    self.assertEqual(V._clamp_full(a, b, c),
                                     F.clamp_full_ref(a, b, c))

    def test_med2_es_la_media_entera_canal_a_canal(self):
        for a in self.SEMILLAS:
            for b in self.SEMILLAS:
                self.assertEqual(V._med2(a, b), F.med2_ref(a, b),
                                 "med2(%08X,%08X)" % (a, b))

    def test_la_tabla_de_planos_reproduce_los_ocho_primeros_de_libwebp(self):
        """`_codigo_a_plano()` GENERA la tabla `kCodeToPlane` en vez de
        copiarla. Lo que se juzga es el ORDEN, que es lo unico que decide."""
        self.assertEqual(len(V._PLANOS), 120)
        for k, cod in enumerate(F.KCODE_A_PLANO_8):
            for xsize in (1, 2, 7, 100, 4096):
                with self.subTest(cod=k + 1, xsize=xsize):
                    self.assertEqual(V._distancia_plano(xsize, k + 1),
                                     F.distancia_plano_ref(xsize, cod))

    def test_los_120_planos_son_los_desplazamientos_de_la_norma(self):
        esperados = {(dx, dy) for dy in range(8) for dx in range(-7, 9)
                     if not (dy == 0 and dx <= 0)}
        self.assertEqual(set(V._PLANOS), esperados)
        dists = [dx * dx + dy * dy for dx, dy in V._PLANOS]
        self.assertEqual(dists, sorted(dists), "la tabla no va por distancia")

    def test_por_encima_de_120_el_codigo_es_la_distancia_directa(self):
        for cod in (121, 122, 200, 1000):
            self.assertEqual(V._distancia_plano(37, cod), cod - 120)

    def test_la_distancia_nunca_baja_de_uno(self):
        """Con una imagen de 1 pixel de ancho, un dx negativo daria distancia
        negativa: la norma la sube a 1."""
        vistos = 0
        for cod in range(1, 121):
            d = V._distancia_plano(1, cod)
            self.assertGreaterEqual(d, 1)
            dx, dy = V._PLANOS[cod - 1]
            if dy * 1 + dx < 1:
                vistos += 1
        self.assertGreater(vistos, 0, "ninguna celda ejercita el suelo de 1")


@unittest.skipUnless(shutil.which("magick"), "hace falta ImageMagick nativo")
class Vp8lDeVerdad(BasePng):
    """Integracion: PNG -> WebP SIN PERDIDA con `magick` -> `alfa_minimo`. El
    decodificador VP8L completo (predictores incluidos) tiene que devolver el
    mismo min(alfa) que el PNG de partida."""

    def test_el_alfa_sobrevive_a_la_ida_y_vuelta_sin_perdida(self):
        import random
        rnd = random.Random(31337)
        casos = {
            "hueco": F.rgba_con_hueco(24, 16, 9, 7, 17),
            "azar": [[(rnd.randrange(256), rnd.randrange(256), rnd.randrange(256),
                       rnd.choice([255, 255, rnd.randrange(256)]))
                      for _ in range(24)] for _ in range(16)],
            "rampa": F.rejilla(48, 32, lambda x, y: (x * 5 % 256, y * 7 % 256,
                                                     128, min(255, x * 4 + 3))),
        }
        for nombre, px in casos.items():
            datos = F.png(px, 6, 8, filtros=TODOS_LOS_FILTROS)
            p = self.escribe(datos)
            w = p[:-4] + ".webp"
            rc = subprocess.run(["magick", p, "-define", "webp:lossless=true", w],
                                capture_output=True, timeout=120)
            with self.subTest(caso=nombre):
                self.assertEqual(rc.returncode, 0, rc.stderr[:400])
                a = V.alfa_minimo(w, "webp", exacto=True)
                self.assertTrue(a["evaluable"], a.get("motivo"))
                self.assertIn("VP8L", a["via"])
                self.assertAlmostEqual(a["alfa_min"],
                                       F.referencia(datos)["alfa_min"],
                                       places=12)


# ---------------------------------------------------------------------------
# 4. Defectos vigentes: se documentan con el caso minimo y se dejan clavados
# ---------------------------------------------------------------------------

class DefectosVigentes(BasePng):
    """Estas pruebas fijan el comportamiento ACTUAL, que es INCORRECTO.

    Se escriben asi por la trampa 116: el control positivo de un arnes es el
    sujeto CON el defecto, conservado a proposito. Si alguna se pone roja es
    que el defecto se arreglo — **quitala y anota el arreglo en
    `bench/cobertura-png.md`**, no la relajes. El carril `cob/png` tiene
    prohibido tocar `filex/`.
    """

    def test_D1_un_alfa_de_16_bits_con_el_byte_alto_a_255_se_da_por_opaco(self):
        """`_alfa_min_png` solo entra a comparar la pareja (hi, lo) si
        `min(hi) < 255`, asi que todo alfa entre 0xFF00 y 0xFFFE se pierde: se
        publica `alfa_min = 1.0` **y `exacto = True`**, que es una afirmacion
        falsa, no una duda. La rama Adam7 del mismo fichero SI lo ve.
        """
        for alfa in (65280, 65407, 65534):
            px = F.rgba_con_hueco(6, 4, 3, 2, alfa, bd=16)
            plano = self.escribe(F.png(px, 6, 16, filtros=TODOS_LOS_FILTROS))
            entre = self.escribe(F.png(px, 6, 16, entrelazado=1,
                                       filtros=TODOS_LOS_FILTROS))
            esperado = alfa / 65535.0
            with self.subTest(alfa=alfa):
                a = V.alfa_minimo(plano, "png", exacto=True)
                b = V.alfa_minimo(entre, "png", exacto=True)
                # el oraculo y la via entrelazada coinciden...
                self.assertAlmostEqual(F.referencia(F.png(
                    px, 6, 16, filtros=TODOS_LOS_FILTROS))["alfa_min"],
                    esperado, places=12)
                self.assertAlmostEqual(b["alfa_min"], esperado, places=12)
                self.assertEqual(tuple(b["primer_transparente"]), (3, 2))
                # ...y la via NO entrelazada da 1.0, exacto, y sin coordenada
                self.assertEqual(a["alfa_min"], 1.0)
                self.assertTrue(a["exacto"])
                self.assertIsNone(a["primer_transparente"])
                # la consecuencia, que es lo que se publica hacia el contrato:
                # `alfa_no_trivial` pasa de True a False, y la regla I3 da la
                # entrada por «sin zonas transparentes» sin mirar la salida.
                self.assertIs(b["alfa_no_trivial"], esperado < 0.999)
                self.assertIs(a["alfa_no_trivial"], False)

    def test_D1b_el_umbral_esta_justo_en_0xFF00(self):
        """Caso minimo del limite: 0xFEFF se ve, 0xFF00 no."""
        for alfa, se_ve in ((65279, True), (65280, False)):
            px = F.rgba_con_hueco(4, 2, 1, 1, alfa, bd=16)
            p = self.escribe(F.png(px, 6, 16, filtros=(0,)))
            got = V.alfa_minimo(p, "png", exacto=True)
            with self.subTest(alfa=alfa):
                if se_ve:
                    self.assertAlmostEqual(got["alfa_min"], alfa / 65535.0,
                                           places=12)
                else:
                    self.assertEqual(got["alfa_min"], 1.0)

    def test_D2_el_predictor_13_divide_como_Python_y_no_como_C(self):
        """libwebp calcula `a + (a - b) / 2` con division ENTERA DE C, que
        trunca hacia cero; `_clamp_half` usa `//`, que trunca hacia -infinito.
        Difieren en 1 siempre que `a - b` sea negativo e impar.

        Caso minimo: L = T = 0x0A0A0A0A, TL = 0x0F0F0F0F. Media = 10,
        10 + (10-15)/2 -> C: 10 + (-2) = 8; Python: 10 + (-3) = 7.
        """
        L = T = 0x0A0A0A0A
        TL = 0x0F0F0F0F
        self.assertEqual(V._clamp_half(L, T, TL), 0x07070707)
        self.assertEqual(F.clamp_half_ref(L, T, TL), 0x08080808)
        px, i, w = PredictoresVp8l._vecindad(L, T, TL, 0)
        self.assertEqual(V._predice(13, px, i, w), 0x07070707)
        # cuando la diferencia es par o positiva, coinciden
        for L2, T2, TL2 in ((0x0A0A0A0A, 0x0A0A0A0A, 0x0E0E0E0E),
                            (0x1E1E1E1E, 0x1E1E1E1E, 0x0A0A0A0A)):
            with self.subTest(TL=TL2):
                self.assertEqual(V._clamp_half(L2, T2, TL2),
                                 F.clamp_half_ref(L2, T2, TL2))

    def test_D3_las_dos_vias_no_dicen_lo_mismo_de_primer_transparente(self):
        """En 16 bits sin entrelazar el campo es «el primer pixel que BAJA el
        minimo corriente»; en 8 bits, en paleta y en Adam7 es «el pixel del
        MINIMO de la primera fila que lo baja». Sobre la MISMA fila de alfas,
        en escala, dan coordenadas distintas, y ninguna de las dos lecturas
        esta documentada. La regla I3 lee ese pixel de la salida con `magick`,
        asi que no es cosmetico."""
        fila8 = (254, 254, 200, 255)
        fila16 = (65534, 65534, 60000, 65535)
        p8 = self.escribe(F.png(
            F.rejilla(4, 1, lambda x, y: (0, 0, 0, fila8[x])), 6, 8, filtros=(0,)))
        p16 = self.escribe(F.png(
            F.rejilla(4, 1, lambda x, y: (0, 0, 0, fila16[x])), 6, 16, filtros=(0,)))
        a8 = V.alfa_minimo(p8, "png", exacto=True)
        a16 = V.alfa_minimo(p16, "png", exacto=True)
        self.assertEqual(tuple(a8["primer_transparente"]), (2, 0))   # el minimo
        self.assertEqual(tuple(a16["primer_transparente"]), (0, 0))  # el primero
        # los dos apuntan a un pixel que SI es transparente; lo que cambia es
        # cual de los dos criterios se aplica
        self.assertLess(fila8[2], 255)
        self.assertLess(fila16[0], 65535)


if __name__ == "__main__":
    unittest.main()

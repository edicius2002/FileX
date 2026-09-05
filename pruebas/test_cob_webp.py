"""Carril de cobertura del decodificador WebP/VP8L de `filex/verificador.py`.

**Qué había antes.** 272 líneas sin ejecutar en 517 pruebas, entre ellas el
flujo de bits VP8L entero (`_vp8l_flujo`, 148 de 162) y el cuerpo COMPLETO de
`_leer_codigo_huffman`, `_leer_simbolo`, `_BitsLSB.leer` y `_BitsLSB.ojear`. Es
un decodificador Huffman a nivel de bits escrito a mano: un error ahí no lanza
excepción, **devuelve un número**, y ese número es `alfa_min`, que es el
veredicto del «alfa trivial» (trampa 1 de `CLAUDE.md`).

**El árbitro es externo, y por eso esto no es una tautología.** Las cifras que
esperan estas pruebas —`REFERENCIA` y `FILTROS_ALPH`— salen de **libwebp 1.6.0
a través de `magick`**, no de FileX. Se comparan el mínimo, la posición del
primer píxel transparente **y el sha256 del plano alfa entero**: un
decodificador puede acertar el mínimo y equivocarse en todo lo demás
(`bench/cobertura-webp.md` §3).

**Dos defectos MEDIDOS que estas pruebas fijan como tales.** Ninguno se arregla
aquí: las funciones están dentro del cierre de llamadas de `verificar()` y
tocarlas caducaría las 232 aristas selladas.
  1. `_clamp_half` (predictor 13 de VP8L) divide con `//`, que redondea hacia
     `-inf`, donde libwebp usa la división entera de C, que **trunca hacia
     cero**. `cob/png` lo encontró (su D2) y dejó PENDIENTE su alcance sobre
     ficheros reales, porque el modo 13 no salía en ninguna de sus nueve
     imágenes. Aquí se cierra: sobre 40 semillas de 24x24, **9 disparan el modo
     13 y las 9 mueven el `alfa_min` publicado**, hasta siete niveles de alfa.
  2. `_webp` cuenta **N+1** fotogramas en un WebP animado de N.
`test_DEFECTO_*` documenta el valor equivocado de HOY y el correcto al lado; el
día que se arreglen, esas pruebas fallarán, que es justo lo que se quiere.

Ninguna prueba de este fichero usa la GPU, ni Docker, ni un motor externo:
todos los fixtures viajan como bytes en `fixtures_cob_webp.py`.
"""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fixtures_cob_webp as F                                    # noqa: E402
from filex import verificador as V                               # noqa: E402

# ---------------------------------------------------------------------------
# Verdad de terreno. NO sale de FileX: la escribió libwebp 1.6.0 y la extrajo
#   magick <fixture> -alpha extract -depth 8 gray:-
# La orden exacta y la tanda que la produjo están en
# bench/salidas-cobertura-webp/MANIFIESTO.md.
# ---------------------------------------------------------------------------

#            nombre                 ancho alto min  primer_transparente  sha256 del plano alfa
REFERENCIA = {
    "LL_TRANSFORMACIONES":   (48, 64,   0, (12, 47), "b7a01ad2de49e57419b3dbe4beeab7de1ede04de1c05c053f3824f925e56994c"),
    "LL_META_HUFFMAN":       (32, 32, 128, (0, 0),   "f991acb1e5897fe61be2decbf1d1b41b165ec8c2317284f8e3d8322c4d052e21"),
    "LL_PALETA_ANCHA":       (32, 32, 102, (0, 0),   "ccecafa07528a4891f609a632f8354daba061d4d41b0467c9d1de8ec24188ac3"),
    "LL_PALETA_EMPAQUETADA": (16, 16,   0, (0, 8),   "437bfe90cdd4b4d2e446ada70cbc5db791ad654620a67ee1ba2b2a17b2670362"),
    "LL_OPACO":              (24, 16, 255, (0, 0),   "a292bc4a1d8d3caa7dd32d1858f7d642a27373526b84cde7df8634faad708d2a"),
    "LL_DAMERO":             (64, 64,   0, (0, 0),   "f735c4f941e77bc3f5d1eb1a91a8af012e86a5adbe5a76467d3d3c091baa700c"),
    "PERDIDA_ALPH_CRUDO":    (24, 16,   0, (0, 15),  "cba031c5eca7078672fe2797369363e42526f0ae758ead428fb13ab9c053db12"),
    "PERDIDA_ALPH_VP8L":     (24, 16,   0, (0, 15),  "cba031c5eca7078672fe2797369363e42526f0ae758ead428fb13ab9c053db12"),
    "PERDIDA_ALPH_DIAG":     (32, 32,   0, (0, 0),   "4ca6c8afb514dee9982640f42f746337c5fb52ba600bdc1bb88dba0f4d0bc9d4"),
    "PERDIDA_ALPH_OPACO":    (20, 20, 255, (0, 0),   "c323c96b39b5155a4788a606c6fc05571befd551e693af4ec6b7f369cc42a834"),
    "PERDIDA_SIN_ALFA":      (24, 16, 255, (0, 0),   "a292bc4a1d8d3caa7dd32d1858f7d642a27373526b84cde7df8634faad708d2a"),
}

# El mismo plano de bytes que escribió libwebp, releído declarando cada uno de
# los cuatro filtros espaciales del trozo ALPH. Sólo cambia el nibble de la
# cabecera; los bytes del plano son los de libwebp y el árbitro sigue siendo él.
FILTROS_ALPH = {
    0: (0, (0, 15), "cba031c5eca7078672fe2797369363e42526f0ae758ead428fb13ab9c053db12"),
    1: (1, (16, 4), "be71adf06392cbbef1ca4b7eadb8b77bf3ebf08e4218697bf45c6bbd3ee616b8"),
    2: (5, (23, 7), "38b0a1b3d5830943ca17ebdd5c7e8d0c7719ea529e2da385124a4ea4d5f5e42e"),
    3: (0, (10, 7), "2a3f8386f9ef15797a4c16774493b9d2222df7630de45524f779f02b562a18f2"),
}

# El RGBA ENTERO que decodifica libwebp de los fixtures sin pérdida. Hace falta
# además del plano alfa porque hay transformaciones de VP8L —color cruzado,
# restar verde, paleta— que **no tocan el canal alfa**, y sin esta tabla cinco
# mutaciones del decodificador salían verdes (`bench/cobertura-webp.md` §4).
#   magick <fixture> -depth 8 RGBA:-
RGBA_LIBWEBP = {
    "LL_TRANSFORMACIONES":   (12288, "8061b1abac9e1fcdb4b684d0be72272077a8de914ef12942e2e1158e8d7af1be"),
    "LL_META_HUFFMAN":       (4096,  "0483d913988abb3b4dbba496d3e06fd47203cee5a140a92b86f5069b8dae8f4f"),
    "LL_PALETA_ANCHA":       (4096,  "b408dde2d0ea9ee3fa6491de30e0d29860c13d602030026c92953fb887c09f26"),
    "LL_PALETA_EMPAQUETADA": (1024,  "f1d361f1879281dd11d34c2d50cbb2f64a4865673309d10980f1cc01d24b9335"),
    "LL_OPACO":              (1536,  "4b7f2f70ca80dac01ad82cb5d6f276e287d1ca7bba4ecbca3d48811064758bdb"),
    "LL_DAMERO":             (16384, "526b478a09d8c89ef14ed080d1f9ec0113ae7ba4a1b748e66bf43860df47faef"),
}
# El séptimo VP8L, `DEFECTO_MODO13`, NO coincide con libwebp: es el fixture del
# defecto del predictor 13. libwebp da este RGBA y FileX da otro.
RGBA_LIBWEBP_DEFECTO = (2304, "abdc1591415f9007a74f28b5e5ba035db1674f833970e3a0a37c717048849809")

# El fixture donde el defecto del predictor 13 se ve en el resultado PUBLICADO.
# Sobre el MISMO píxel (20,18), libwebp mide 60 y FileX publica 53: siete
# niveles de alfa de diferencia en el número que decide el «alfa trivial».
MODO13_LIBWEBP = (60, (20, 18))
MODO13_FILEX_HOY = (53, (20, 18))


def _escribir(datos: bytes, nombre: str = "x.webp") -> str:
    d = tempfile.mkdtemp(prefix="cobwebp-")
    ruta = os.path.join(d, nombre)
    with open(ruta, "wb") as fh:
        fh.write(datos)
    return ruta


def _plano_alfa(datos: bytes) -> bytes:
    """El plano alfa que decodifica FileX, por la ruta que le toque al fichero.

    Reproduce lo que hace `_alfa_min_webp`, pero devolviendo el plano ENTERO en
    vez del mínimo: comparar sólo el mínimo deja pasar un decodificador que
    acierta un byte de mil.
    """
    alph = F.trozo(datos, b"ALPH")
    vp8l = F.trozo(datos, b"VP8L")
    vp8x = F.trozo(datos, b"VP8X")
    vp8 = F.trozo(datos, b"VP8 ")
    if vp8x is not None:
        an = 1 + int.from_bytes(vp8x[4:7], "little")
        al = 1 + int.from_bytes(vp8x[7:10], "little")
    elif vp8 is not None:
        an = int.from_bytes(vp8[6:8], "little") & 0x3FFF
        al = int.from_bytes(vp8[8:10], "little") & 0x3FFF
    else:
        an = al = None
    if alph is not None:
        cab = alph[0]
        filtro, compr = (cab >> 2) & 3, cab & 3
        crudo = (alph[1:1 + an * al] if compr == 0 else
                 V._vp8l_decodificar(alph[1:], an, al, plano_alfa=True))
        return bytes(V._alph_desfiltrar(bytearray(crudo), an, al, filtro))
    if vp8l is not None:
        _, _, rgba = V._vp8l_decodificar(vp8l, None, None, plano_alfa=False)
        return bytes(rgba[3::4])
    return b"\xff" * (an * al)          # con pérdida y sin ALPH: opaco


class Fixtures(unittest.TestCase):
    """Los bytes que las demás pruebas dan por buenos."""

    def test_el_manifiesto_cuadra_con_los_bytes(self):
        # Trampa 48: un recuento correcto no prueba un contenido correcto, así
        # que se comprueban tamaño Y sha256 de cada blob, no cuántos hay.
        self.assertEqual(len(F.MANIFIESTO), 13)
        for nombre, (tam, sha) in F.MANIFIESTO.items():
            b = getattr(F, nombre)
            with self.subTest(nombre):
                self.assertEqual(len(b), tam)
                self.assertEqual(hashlib.sha256(b).hexdigest(), sha)
                self.assertEqual(b[:4], b"RIFF")
                self.assertEqual(b[8:12], b"WEBP")

    def test_control_positivo_del_escritor_de_vp8l(self):
        """El escritor a mano produce VP8L de VERDAD, no bytes plausibles.

        Sin este control, un «falla como se esperaba» en las pruebas de
        `RamasDeError` no se distingue de «mi generador escribe basura»
        (trampas 81 y 91). La verificación externa —que `magick` lea el mismo
        color— está MEDIDA en `bench/cobertura-webp.md` §5 y aquí se comprueba
        contra el color pedido, que es una constante conocida de antemano.
        """
        for an, al, a, r, g, b in ((4, 3, 0x80, 0x20, 0x40, 0x10),
                                   (1, 1, 0x00, 0xFF, 0x00, 0x00),
                                   (7, 5, 0xC3, 0x11, 0x22, 0x33)):
            with self.subTest(tam="%dx%d" % (an, al)):
                flujo = F.vp8l_solido(an, al, a, r, g, b)
                w2, h2, rgba = V._vp8l_decodificar(flujo, None, None,
                                                   plano_alfa=False)
                self.assertEqual((w2, h2), (an, al))
                self.assertEqual(bytes(rgba), bytes([r, g, b, a]) * (an * al))


class CabeceraWebp(unittest.TestCase):
    """`_webp`: el lector de trozos RIFF, por `sondear_en_proceso`."""

    def test_dimensiones_y_alfa_de_cada_familia(self):
        esperado = {
            "LL_TRANSFORMACIONES":   (48, 64, True, False),
            "LL_OPACO":              (24, 16, False, False),
            "PERDIDA_ALPH_CRUDO":    (24, 16, True, None),
            "PERDIDA_SIN_ALFA":      (24, 16, False, True),
        }
        for nombre, (an, al, alfa, perdida) in esperado.items():
            with self.subTest(nombre):
                d = V.sondear_en_proceso(_escribir(getattr(F, nombre)))
                self.assertEqual((d["ancho"], d["alto"]), (an, al))
                self.assertEqual(d["tiene_alfa"], alfa)
                self.assertEqual(d.get("perdida"), perdida)

    def test_la_bandera_de_alfa_de_vp8x_decide_cuando_no_hay_alph(self):
        """Con un ALPH delante, estropear la bandera de VP8X no se nota: la
        otra rama vuelve a poner `tiene_alfa`. Sin ALPH, decide ella sola."""
        for alfa in (True, False):
            with self.subTest(alfa=alfa):
                d = V.sondear_en_proceso(_escribir(F.envolver_vp8x(alfa, 40, 25)))
                self.assertIs(d["tiene_alfa"], alfa)
                self.assertEqual((d["ancho"], d["alto"]), (40, 25))

    def test_el_vp8l_declara_su_alfa_en_la_cabecera(self):
        # bit 28 de los 5 bytes que siguen a la firma 0x2F
        d = V.sondear_en_proceso(_escribir(F.LL_TRANSFORMACIONES))
        self.assertTrue(d["tiene_alfa"])
        self.assertIs(d["perdida"], False)


class Vp8lSinPerdida(unittest.TestCase):
    """`_vp8l_flujo` de punta a punta contra lo que dice libwebp."""

    def test_el_plano_alfa_coincide_byte_a_byte_con_libwebp(self):
        for nombre, (an, al, mn, pos, sha) in REFERENCIA.items():
            with self.subTest(nombre):
                plano = _plano_alfa(getattr(F, nombre))
                self.assertEqual(len(plano), an * al)
                self.assertEqual(hashlib.sha256(plano).hexdigest(), sha)

    def test_el_rgba_entero_coincide_byte_a_byte_con_libwebp(self):
        """Sin pérdida quiere decir SIN PÉRDIDA: los cuatro canales.

        El plano alfa no basta —el color cruzado, el restar verde y la paleta
        pueden dejar el alfa intacto y estropear el color—, y eso está MEDIDO:
        con sólo el plano, cinco mutaciones del decodificador no se detectaban.
        """
        for nombre, (n, sha) in RGBA_LIBWEBP.items():
            with self.subTest(nombre):
                vp8l = F.trozo(getattr(F, nombre), b"VP8L")
                _, _, rgba = V._vp8l_decodificar(vp8l, None, None,
                                                 plano_alfa=False)
                self.assertEqual(len(rgba), n)
                self.assertEqual(hashlib.sha256(bytes(rgba)).hexdigest(), sha)

    def test_alfa_minimo_publica_el_minimo_y_su_posicion(self):
        for nombre, (an, al, mn, pos, sha) in REFERENCIA.items():
            with self.subTest(nombre):
                r = V.alfa_minimo(_escribir(getattr(F, nombre)))
                self.assertTrue(r["evaluable"], r.get("motivo"))
                self.assertAlmostEqual(r["alfa_min"], mn / 255.0, places=9)
                if mn < 255:
                    self.assertEqual(r["primer_transparente"], pos)
                else:
                    self.assertIsNone(r["primer_transparente"])

    def test_el_atajo_de_cabecera_no_decodifica_nada(self):
        """`alpha_is_used=0` responde sin tocar el flujo de bits."""
        r = V.alfa_minimo(_escribir(F.LL_OPACO))
        self.assertEqual(r["via"], "cabecera VP8L (alpha_is_used=0)")
        self.assertEqual(r["alfa_min"], 1.0)
        self.assertFalse(r["tiene_alfa"])

    def test_cada_fixture_llega_a_la_transformacion_que_dice_ejercitar(self):
        """Demuestra que la prueba LLEGA a lo que afirma (trampa 109).

        No basta con que el fixture decodifique: hay que enseñar por dónde pasa.
        Un espía sobre `_predice` dice qué modos de predicción usó cada uno, y
        los conjuntos son distintos entre sí —si la sonda devolviera lo mismo
        para todos, la rota sería la sonda (trampa 66)—. Los fixtures de paleta
        y los de ALPH no llaman a `_predice` NI UNA VEZ, y eso también se
        afirma: un cero esperado vale tanto como un positivo.
        """
        esperado = {
            "LL_TRANSFORMACIONES":   {2},
            "LL_META_HUFFMAN":       {7, 10},
            "LL_DAMERO":             {12},
            "DEFECTO_MODO13":        {5, 6, 7, 13},
            "PERDIDA_ALPH_DIAG":     {1},
            "LL_PALETA_ANCHA":       set(),
            "LL_PALETA_EMPAQUETADA": set(),
            "PERDIDA_ALPH_CRUDO":    set(),
        }
        real = V._predice
        try:
            for nombre, modos in esperado.items():
                vistos = []
                V._predice = (lambda m, px, i, w:
                              (vistos.append(m), real(m, px, i, w))[1])
                _plano_alfa(getattr(F, nombre))
                with self.subTest(nombre):
                    self.assertEqual(set(vistos), modos)
        finally:
            V._predice = real
        # y la unión de los fixtures toca siete de los catorce modos
        self.assertEqual(set().union(*esperado.values()),
                         {1, 2, 5, 6, 7, 10, 12, 13})

    def test_la_paleta_ancha_usa_indices_sin_empaquetar(self):
        """24 colores: `bits == 0`, un índice por píxel."""
        r = V.alfa_minimo(_escribir(F.LL_PALETA_ANCHA))
        self.assertEqual(r["via"], "VP8L")
        self.assertAlmostEqual(r["alfa_min"], 102 / 255.0, places=9)

    def test_la_paleta_estrecha_empaqueta_ocho_indices_por_byte(self):
        """3 colores: `bits == 3`, y el ancho del flujo NO es el de la imagen."""
        datos = F.LL_PALETA_EMPAQUETADA
        vp8l = F.trozo(datos, b"VP8L")
        an, al, rgba = V._vp8l_decodificar(vp8l, None, None, plano_alfa=False)
        self.assertEqual((an, al), (16, 16))     # se deshizo el empaquetado
        self.assertEqual(len(rgba), 16 * 16 * 4)


def _clip255(v):
    return 0 if v < 0 else (255 if v > 255 else v)


def _avg2(a, b):
    return (((a ^ b) & 0xFEFEFEFE) >> 1) + (a & b)


def _div2_c(x):
    """La división entera de C TRUNCA hacia cero; la de Python redondea hacia
    -inf. Es exactamente la diferencia que produce el defecto del modo 13."""
    return int(x / 2) if x < 0 else x // 2


def _ref_predice(modo, L, T, TL, TR):
    """Los catorce predictores tal y como los define la especificación.

    Fuente: *WebP Lossless Bitstream Specification*, sección «Predictor
    Transform», y `src/dsp/lossless.c` de libwebp (`Average2`, `Select`,
    `ClampAddSubtractFull`, `ClampAddSubtractHalf`).
    """
    if modo == 0:
        return 0xFF000000
    if modo == 1:
        return L
    if modo == 2:
        return T
    if modo == 3:
        return TR
    if modo == 4:
        return TL
    if modo == 5:
        return _avg2(_avg2(L, TR), T)
    if modo == 6:
        return _avg2(L, TL)
    if modo == 7:
        return _avg2(L, T)
    if modo == 8:
        return _avg2(TL, T)
    if modo == 9:
        return _avg2(T, TR)
    if modo == 10:
        return _avg2(_avg2(L, TL), _avg2(T, TR))
    if modo == 11:                                   # Select(T, L, TL)
        s = sum(abs(((L >> d) & 0xFF) - ((TL >> d) & 0xFF))
                - abs(((T >> d) & 0xFF) - ((TL >> d) & 0xFF))
                for d in (24, 16, 8, 0))
        return T if s <= 0 else L
    if modo == 12:                                   # ClampAddSubtractFull
        v = 0
        for d in (24, 16, 8, 0):
            v |= _clip255(((L >> d) & 0xFF) + ((T >> d) & 0xFF)
                          - ((TL >> d) & 0xFF)) << d
        return v
    if modo == 13:                                   # ClampAddSubtractHalf
        m = _avg2(L, T)
        v = 0
        for d in (24, 16, 8, 0):
            av = (m >> d) & 0xFF
            v |= _clip255(av + _div2_c(av - ((TL >> d) & 0xFF))) << d
        return v
    raise AssertionError(modo)


class Predictores(unittest.TestCase):
    """`_predice`: los catorce modos, contra la especificación y no contra sí
    mismos. Es la parte del decodificador donde un error no lanza excepción:
    devuelve un color plausible y equivocado.
    """

    VECINOS = [
        (0x00000064, 0x00000064, 0x00000067, 0x00000000),
        (0xF7697FB9, 0xC735DF5E, 0x70D3DA1F, 0x1A2B3C4D),
        (0xFFFFFFFF, 0x00000000, 0x80808080, 0x01020304),
        (0x00000000, 0xFFFFFFFF, 0x00FF00FF, 0xFF00FF00),
        (0x11223344, 0x11223344, 0x11223344, 0x11223344),
        (0xFF010203, 0xFF040506, 0xFF070809, 0xFF0A0B0C),
    ]

    def _pedir(self, modo, L, T, TL, TR):
        ancho = 4
        px = [0] * (2 * ancho + 2)
        i = ancho + 1
        px[i - 1], px[i - ancho] = L, T
        px[i - ancho - 1], px[i - ancho + 1] = TL, TR
        return V._predice(modo, px, i, ancho)

    def test_los_modos_0_a_12_coinciden_con_la_especificacion(self):
        for modo in range(13):
            for L, T, TL, TR in self.VECINOS:
                with self.subTest(modo=modo, L="%08X" % L):
                    self.assertEqual(self._pedir(modo, L, T, TL, TR),
                                     _ref_predice(modo, L, T, TL, TR))

    def test_DEFECTO_el_modo_13_NO_coincide_con_la_especificacion(self):
        """El único de los catorce que se desvía. Ver `DefectosMedidos`.

        Se afirma la desviación, no la coincidencia: el día que se arregle,
        esta prueba fallará y habrá que borrarla, que es lo correcto.
        """
        desviados = [(L, T, TL) for L, T, TL, TR in self.VECINOS
                     if self._pedir(13, L, T, TL, TR)
                     != _ref_predice(13, L, T, TL, TR)]
        self.assertTrue(desviados,
                        "¿arreglado el modo 13? entonces esta prueba sobra")
        # ...y coincide cuando la diferencia con TL es par en los cuatro canales
        self.assertEqual(self._pedir(13, 0x11223344, 0x11223344, 0x11223344, 0),
                         _ref_predice(13, 0x11223344, 0x11223344, 0x11223344, 0))

    def test_la_tabla_rechaza_una_longitud_de_mas_de_quince_bits(self):
        """GUARDA, no ruta: por el flujo de bits no llega nunca una longitud
        mayor de 15 —las del alfabeto de longitudes se leen con `leer(3)` (<= 7)
        y las del código principal salen de símbolos `cl < 16`—, así que
        `_huff_tabla` no puede verla desde `_vp8l_flujo`. Se fija su contrato.
        """
        with self.assertRaises(ValueError) as cm:
            V._huff_tabla([16, 16])
        self.assertIn("longitud de codigo 16 > 15", str(cm.exception))

    def test_un_modo_desconocido_se_declara_en_vez_de_devolver_un_color(self):
        with self.assertRaises(ValueError) as cm:
            self._pedir(14, 0, 0, 0, 0)
        self.assertIn("predictor VP8L 14 desconocido", str(cm.exception))


class AlphDesfiltrar(unittest.TestCase):
    """`_alph_desfiltrar`: los cuatro filtros espaciales del trozo ALPH."""

    def test_los_cuatro_filtros_coinciden_con_libwebp(self):
        for filtro, (mn, pos, sha) in FILTROS_ALPH.items():
            with self.subTest(filtro=filtro):
                datos = F.mutar_cabecera_alph(F.PERDIDA_ALPH_CRUDO, filtro=filtro)
                plano = _plano_alfa(datos)
                self.assertEqual(hashlib.sha256(plano).hexdigest(), sha)
                r = V.alfa_minimo(_escribir(datos))
                self.assertEqual(r["via"], "ALPH crudo (filtro %d)" % filtro)
                self.assertAlmostEqual(r["alfa_min"], mn / 255.0, places=9)
                self.assertEqual(r["primer_transparente"], pos)

    def test_el_alph_comprimido_pasa_por_el_vp8l_de_plano_alfa(self):
        r = V.alfa_minimo(_escribir(F.PERDIDA_ALPH_VP8L))
        self.assertEqual(r["via"], "ALPH comprimido sin perdida (VP8L)")
        self.assertEqual(r["alfa_min"], 0.0)

    def test_un_plano_mas_corto_que_la_imagen_no_revienta(self):
        """El ALPH declara 24x16 y trae menos bytes: la guarda `i >= len(out)`."""
        datos = F.envolver_alph(b"\x04" + bytes(range(40)), 24, 16)   # filtro 1
        r = V.alfa_minimo(_escribir(datos))
        self.assertTrue(r["evaluable"], r.get("motivo"))
        self.assertIsNotNone(r["alfa_min"])


class RamasDeError(unittest.TestCase):
    """Flujos malformados. Cada uno cambia UNA cosa sobre un flujo válido."""

    def _lanza(self, flujo, mensaje):
        with self.assertRaises(ValueError) as cm:
            V._vp8l_decodificar(flujo, None, None, plano_alfa=False)
        self.assertIn(mensaje, str(cm.exception))

    def test_firma_vp8l_ausente(self):
        w = F.Bits(); F.cabecera_vp8l(w, 4, 3, firma=0x2E); w.pon(0, 3)
        self._lanza(w.fin(), "firma VP8L ausente")

    def test_version_vp8l_no_soportada(self):
        w = F.Bits(); F.cabecera_vp8l(w, 4, 3, version=1); w.pon(0, 3)
        self._lanza(w.fin(), "version VP8L no soportada")

    def test_cache_de_color_de_mas_de_once_bits(self):
        w = F.Bits(); F.cabecera_vp8l(w, 4, 3)
        w.pon(0, 1)
        w.pon(1, 1); w.pon(12, 4)
        self._lanza(w.fin(), "cache de color de 12 bits")

    def test_transformacion_repetida(self):
        w = F.Bits(); F.cabecera_vp8l(w, 4, 3)
        w.pon(1, 1); w.pon(2, 2)          # restar verde
        w.pon(1, 1); w.pon(2, 2)          # otra vez
        self._lanza(w.fin(), "transformacion VP8L repetida")

    def test_simbolo_simple_fuera_del_alfabeto(self):
        # el alfabeto de distancias tiene 40 símbolos; se pide el 200
        w = F.Bits(); F.cabecera_vp8l(w, 4, 3)
        w.pon(0, 1); w.pon(0, 1); w.pon(0, 1)
        for _ in range(4):
            F.codigo_simple(w, 0x10)
        F.codigo_simple(w, 200)
        self._lanza(w.fin(), "simbolo simple fuera del alfabeto")

    def test_segundo_simbolo_simple_fuera_del_alfabeto(self):
        w = F.Bits(); F.cabecera_vp8l(w, 4, 3)
        w.pon(0, 1); w.pon(0, 1); w.pon(0, 1)
        for _ in range(4):
            F.codigo_simple(w, 0x10)
        F.codigo_simple(w, 3, segundo=200)
        self._lanza(w.fin(), "segundo simbolo fuera del alfabeto")

    def test_codigo_huffman_vacio(self):
        w = F.Bits(); F.cabecera_vp8l(w, 4, 3)
        w.pon(0, 1); w.pon(0, 1); w.pon(0, 1)
        w.pon(0, 1); w.pon(0, 4)
        for _ in range(4):
            w.pon(0, 3)               # las cuatro longitudes a cero
        self._lanza(w.fin(), "codigo Huffman vacio")

    def test_repeticion_de_longitudes_fuera_de_rango(self):
        w = F.Bits(); F.cabecera_vp8l(w, 4, 3)
        w.pon(0, 1); w.pon(0, 1); w.pon(0, 1)
        w.pon(0, 1); w.pon(0, 4)
        w.pon(0, 3); w.pon(1, 3); w.pon(0, 3); w.pon(1, 3)
        w.pon(0, 1)
        for _ in range(3):            # 3 x 138 = 414 > 280
            w.pon(1, 1); w.pon(127, 7)
        self._lanza(w.fin(), "repeticion de longitudes fuera de rango")

    def test_referencia_hacia_atras_fuera_de_rango(self):
        """El primer píxel abre una copia hacia atrás: no hay nada detrás."""
        w = F.Bits(); F.cabecera_vp8l(w, 4, 3)
        w.pon(0, 1); w.pon(0, 1); w.pon(0, 1)
        F.codigo_dos_de_un_bit(w, 280)
        for _ in range(3):
            F.codigo_simple(w, 0x10)
        F.codigo_simple(w, 0, ocho_bits=False)
        w.pon(1, 1)                   # símbolo 256
        self._lanza(w.fin(), "referencia hacia atras fuera de rango")

    def test_codigo_huffman_con_hueco(self):
        """Longitudes [1,2]: el patrón '11' no le toca a ningún símbolo."""
        w = F.Bits(); F.cabecera_vp8l(w, 4, 3)
        w.pon(0, 1); w.pon(0, 1); w.pon(0, 1)
        w.pon(0, 1); w.pon(1, 4)
        w.pon(0, 3); w.pon(1, 3); w.pon(0, 3); w.pon(2, 3); w.pon(2, 3)
        w.pon(1, 1); w.pon(0, 3); w.pon(0, 2)     # max_symbol = 2
        w.pon(1, 2); w.pon(3, 2)
        for _ in range(3):
            F.codigo_simple(w, 0x10)
        F.codigo_simple(w, 0, ocho_bits=False)
        w.pon(3, 2)
        self._lanza(w.fin(), "codigo Huffman invalido")


class DespachadorAlfa(unittest.TestCase):
    """`_alfa_min_webp`: los retornos de «no puedo evaluarlo».

    Un verificador que no distingue «comprobado» de «no he podido comprobarlo»
    repite el fallo que este proyecto documenta en markitdown-mcp, así que cada
    negativa tiene que llegar con su motivo y no con un `alfa_min` inventado.
    """

    def _motivo(self, datos):
        r = V.alfa_minimo(_escribir(datos))
        self.assertFalse(r["evaluable"])
        self.assertIsNone(r["alfa_min"])
        self.assertIsNone(r["alfa_no_trivial"])
        return r["motivo"]

    def test_riff_webp_truncado(self):
        # firma_real() ya dice "webp" con 12 bytes, así que la petición LLEGA a
        # _alfa_min_webp y no se para en el despachador (trampa 109).
        datos = b"RIFF\x04\x00\x00\x00WEBP"
        self.assertEqual(V.firma_real(_escribir(datos)), "webp")
        self.assertIn("no es un RIFF/WEBP", self._motivo(datos))

    def test_alph_sin_dimensiones(self):
        cuerpo = b"ALPH" + (5).to_bytes(4, "little") + b"\x00\xff\xff\xff\xff"
        datos = (b"RIFF" + (4 + len(cuerpo)).to_bytes(4, "little") + b"WEBP"
                 + cuerpo)
        self.assertIn("sin dimensiones", self._motivo(datos))

    def test_alph_comprimido_ilegible(self):
        datos = F.envolver_alph(b"\x01" + b"\x00" * 8, 24, 16)
        self.assertIn("VP8L del plano alfa ilegible", self._motivo(datos))

    def test_compresion_alph_desconocida(self):
        datos = F.mutar_cabecera_alph(F.PERDIDA_ALPH_CRUDO, compresion=2)
        self.assertIn("compresion ALPH 2 desconocida", self._motivo(datos))

    def test_preproceso_alph_desconocido(self):
        datos = F.mutar_cabecera_alph(F.PERDIDA_ALPH_CRUDO, preproc=2)
        self.assertIn("preproceso ALPH 2 desconocido", self._motivo(datos))

    def test_vp8l_ilegible(self):
        w = F.Bits(); F.cabecera_vp8l(w, 4, 3, firma=0x2E); w.pon(0, 3)
        self.assertIn("VP8L ilegible", self._motivo(F.envolver_vp8l(w.fin())))

    def test_animado_se_declara_no_implementado(self):
        r = V.alfa_minimo(_escribir(F.ANIMADO))
        self.assertFalse(r["evaluable"])
        self.assertTrue(r["tiene_alfa"])
        self.assertIn("animado", r["motivo"])


class DefectosMedidos(unittest.TestCase):
    """Los dos defectos que este carril encontró. NO se arreglan aquí.

    Estas pruebas fijan el comportamiento EQUIVOCADO de hoy y dejan al lado el
    correcto. El día que alguien los arregle se pondrán rojas, y eso es lo
    que se quiere: una prueba verde sobre un valor equivocado es la trampa 44.
    """

    def test_DEFECTO_el_predictor_13_redondea_al_reves_que_libwebp(self):
        """`_clamp_half` usa `//`, que redondea hacia -inf; C trunca hacia 0.

        Caso mínimo: L = T = 0x00000064 (azul 100), TL = 0x00000067 (azul 103).
        Promedio = 100; 100 - 103 = -3. Python `-3 // 2` = -2 y C `-3 / 2` = -1,
        así que FileX devuelve 98 donde la especificación pide 99.
        """
        self.assertEqual(V._clamp_half(0x00000064, 0x00000064, 0x00000067),
                         0x00000062,   # 98: lo que hace FileX HOY
                         "¿arreglado? el valor correcto es 0x00000063 (99)")
        # y donde la diferencia es PAR los dos coinciden: no es un error general
        self.assertEqual(V._clamp_half(0x00000064, 0x00000064, 0x00000068),
                         0x00000062)

    def test_DEFECTO_el_predictor_13_mueve_el_alfa_min_publicado(self):
        """El defecto no se queda en un byte interno: sale por la API pública.

        Sobre `DEFECTO_MODO13`, y en el MISMO píxel (20,18), libwebp mide
        min(alfa)=60 y FileX publica 53. Cierra el PENDIENTE 2 de
        `bench/cobertura-png.md`: el defecto SÍ llega a un fichero escrito por
        este mismo `magick`.
        """
        n, sha = RGBA_LIBWEBP_DEFECTO
        _, _, rgba = V._vp8l_decodificar(F.trozo(F.DEFECTO_MODO13, b"VP8L"),
                                         None, None, plano_alfa=False)
        self.assertEqual(len(rgba), n)
        self.assertNotEqual(hashlib.sha256(bytes(rgba)).hexdigest(), sha,
                            "¿arreglado? entonces ya coincide con libwebp")
        r = V.alfa_minimo(_escribir(F.DEFECTO_MODO13))
        self.assertTrue(r["evaluable"])
        mn_hoy, pos_hoy = MODO13_FILEX_HOY
        mn_bien, pos_bien = MODO13_LIBWEBP
        self.assertNotEqual(mn_hoy, mn_bien)          # el defecto sigue vivo
        self.assertAlmostEqual(r["alfa_min"], mn_hoy / 255.0, places=9,
                               msg="¿arreglado? libwebp mide %d" % mn_bien)
        self.assertEqual(pos_hoy, pos_bien)   # el píxel es el mismo; el valor no
        self.assertEqual(r["primer_transparente"], pos_hoy)

    def test_DEFECTO_el_webp_animado_cuenta_un_fotograma_de_mas(self):
        """`_webp` arranca `n_imagenes` en 1 y luego SUMA uno por cada ANMF.

        `ANIMADO` tiene dos trozos ANMF —dos fotogramas— y FileX dice 3.
        """
        datos = F.ANIMADO
        anmf = 0
        i = 12
        while i + 8 <= len(datos):
            tipo = datos[i:i + 4]
            ln = int.from_bytes(datos[i + 4:i + 8], "little")
            anmf += tipo == b"ANMF"
            i += 8 + ln + (ln & 1)
        self.assertEqual(anmf, 2)
        d = V.sondear_en_proceso(_escribir(datos))
        self.assertEqual(d["n_imagenes"], anmf + 1,
                         "¿arreglado? lo correcto es %d" % anmf)


class LectorDeBits(unittest.TestCase):
    """`_BitsLSB`: el lector que alimenta todo lo demás."""

    def test_lee_en_orden_lsb_primero(self):
        br = V._BitsLSB(b"\xB4\x2A")      # 1011_0100  0010_1010
        self.assertEqual(br.leer(4), 0x4)
        self.assertEqual(br.leer(4), 0xB)
        self.assertEqual(br.leer(8), 0x2A)

    def test_ojear_no_consume_y_saltar_si(self):
        br = V._BitsLSB(b"\xFF\x00")
        self.assertEqual(br.ojear(3), 7)
        self.assertEqual(br.ojear(3), 7)      # sigue ahí
        br.saltar(3)
        self.assertEqual(br.ojear(3), 7)
        br.saltar(5)
        self.assertEqual(br.ojear(3), 0)

    def test_ojear_de_cero_bits_devuelve_cero(self):
        """Un código Huffman de UN símbolo tiene `maxl == 0` y VP8L no consume
        ni un bit para leerlo: `ojear(0)` es la ruta normal de ese caso."""
        self.assertEqual(V._BitsLSB(b"\xFF").ojear(0), 0)

    def test_al_agotarse_los_datos_devuelve_ceros(self):
        br = V._BitsLSB(b"\x01")
        self.assertEqual(br.leer(1), 1)
        self.assertEqual(br.leer(16), 0)

    def test_leer_de_cero_bits_no_consume_nada(self):
        """GUARDA, no ruta: `leer(0)` no lo produce ningún sitio del flujo.

        Se enumeraron los 22 puntos donde el decodificador llama a `leer()` y
        todos piden k >= 1: las constantes lo son, `nbits = 2 + 2*leer(3)` >= 2
        y el `extra` de `_prefijo` sólo se calcula para `sim >= 4`, donde vale
        >= 1 (`bench/cobertura-webp.md` §6). Aquí se fija el contrato de la
        guarda, que es lo único que se puede afirmar de ella: no consume bits.
        """
        br = V._BitsLSB(b"\xFF\xFF")
        self.assertEqual(br.leer(0), 0)
        self.assertEqual(br.leer(8), 0xFF)      # no se comió nada
        self.assertEqual(br.leer(0), 0)
        self.assertEqual(br.leer(8), 0xFF)


if __name__ == "__main__":
    unittest.main()

"""Cobertura de los lectores de TIFF y GIF escritos a mano de `verificador.py`.

QUE SE MIDE AQUI Y POR QUE IMPORTA
==================================
`filex/verificador.py` trae dos descodificadores LZW propios (uno por dialecto:
TIFF empaqueta MSB primero con 'early change', GIF empaqueta LSB primero y sin
el), un recorrido de IFD de TIFF y un barrido de bloques de GIF. Los nueve
cuerpos que este fichero ejercita sumaban **346 lineas sin ejecutar** en las 517
pruebas de la suite: el cubo mas grande de todo `filex/`.

El modo de fallo de este codigo es el peor que hay: **un error no lanza
excepcion, devuelve un numero** — y ese numero es `alfa_min`, con el que el
punto 1 del contrato decide si una conversion conserva el canal alfa. La
trampa 1 del proyecto (el «alfa trivial») vive exactamente aqui.

LA REGLA QUE HACE QUE ESTO VALGA ALGO
=====================================
La cobertura es la unica metrica del proyecto que se puede subir sin medir
nada: un `try: f(x) except: pass` sube el porcentaje y no afirma nada. Por eso
**cada comprobacion de este fichero viene con su CONTROL DE DISCRIMINACION**:
se carga una copia de `filex/verificador.py` con UNA linea cambiada y se exige
que la misma comprobacion se ponga ROJA. Una prueba que pasa con el codigo roto
no cuenta (trampa 116: el control positivo es el sujeto CON el defecto).

El mutante se construye EN MEMORIA. No se toca `filex/` en el disco: cualquier
cambio ahi caducaria las 232 aristas selladas, porque estas funciones estan
dentro del cierre de llamadas de `verificar()` (trampa 32).

Tres controles sobre el propio mutante, y los tres los ha pagado ya el
repositorio:
  * IDENTIDAD — el texto viejo aparece exactamente una vez y la fuente mutada
    es distinta de la original (trampa 119: un A/B que compara el codigo
    consigo mismo da «11 OK» y parece decir que las pruebas son vacuas).
  * COMPILACION — la fuente mutada compila (trampa 60: una fuente que no
    compila hace pasar cualquier `assertNotEqual`).
  * ALCANCE — el mutante falla por la ASERCION, no por una excepcion; si el
    defecto solo reventara, la comprobacion no estaria demostrando que llega a
    juzgar el valor (trampa 109).

NINGUNA prueba de este fichero usa la GPU, ni un motor externo, ni la red, ni
`corpus/`. Los bytes salen de `pruebas/fixtures_cob_tiffgif.py`.
"""

from __future__ import annotations

import hashlib
import io
import os
import random
import shutil
import struct
import sys
import tempfile
import types
import unittest
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filex import verificador as V  # noqa: E402
from pruebas import fixtures_cob_tiffgif as F  # noqa: E402


# ===========================================================================
# El mutante: una copia de verificador.py con UNA linea cambiada
# ===========================================================================

with open(V.__file__, "r", encoding="utf-8") as _fh:
    _FUENTE = _fh.read()

_MUTANTES: dict = {}


def mutar(*cambios):
    """Copia de `filex.verificador` con `cambios` = (texto_viejo, texto_nuevo).

    Se cachea por clave: exec de un modulo de 5 840 lineas no es gratis y una
    misma mutacion se usa en varias comprobaciones.
    """
    clave = tuple(cambios)
    if clave in _MUTANTES:
        return _MUTANTES[clave]
    fuente = _FUENTE
    for viejo, nuevo in cambios:
        n = fuente.count(viejo)
        if n != 1:
            raise AssertionError(
                "control de identidad: %r aparece %d veces en verificador.py, "
                "no 1; la mutacion no esta anclada" % (viejo[:60], n))
        fuente = fuente.replace(viejo, nuevo)
    if fuente == _FUENTE:
        raise AssertionError("control de identidad: la fuente mutada es "
                             "IDENTICA a la original")
    codigo = compile(fuente, "<verificador mutado>", "exec")   # trampa 60
    mod = types.ModuleType("verificador_mutado")
    mod.__file__ = V.__file__
    exec(codigo, mod.__dict__)
    _MUTANTES[clave] = mod
    return mod


class Discriminada(unittest.TestCase):
    """Base con el control positivo y el directorio desechable (R18)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="filex-cob-tg-")
        cls._antes = set(os.listdir(cls.tmp))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def escribe(self, nombre, datos):
        p = os.path.join(self.tmp, "%s-%s" % (self.id().rsplit(".", 1)[-1],
                                              nombre))
        with open(p, "wb") as fh:
            fh.write(datos)
        return p

    def discrimina(self, comprobacion, *cambios):
        """Exige que `comprobacion` se ponga ROJA sobre el codigo con `cambios`.

        Se acepta como discriminacion exactamente dos cosas, y las dos prueban
        que el codigo mutado SE EJECUTO:

          * un `AssertionError` — la comprobacion llego a juzgar un valor y el
            valor era otro;
          * cualquier otra excepcion CUYA TRAZA PASE POR EL MUTANTE — la linea
            cambiada se ejecuto y reviento ahi.

        Lo que NO se acepta es una excepcion que no toca el mutante: seria un
        fallo del arnes disfrazado de deteccion (trampa 38: registra si la
        condicion que dices reproducir se dio). Y el filtro por traza es lo que
        cierra la trampa 109 en el otro sentido: si la comprobacion se parara
        en una guarda anterior, la linea mutada no apareceria en la traza.
        """
        mod = mutar(*cambios)
        anclas = [v[:48] for v, _ in cambios]
        try:
            comprobacion(mod)
        except AssertionError:
            return
        except Exception as e:                       # noqa: BLE001
            tb = e.__traceback__
            while tb is not None:
                if tb.tb_frame.f_code.co_filename == "<verificador mutado>":
                    return
                tb = tb.tb_next
            raise AssertionError(
                "la comprobacion murio con %s SIN pasar por el codigo mutado "
                "%r: es un fallo del arnes, no una deteccion"
                % (type(e).__name__, anclas)) from e
        self.fail("NO DISCRIMINA: la comprobacion paso con el codigo roto %r. "
                  "Una prueba que pasa con el defecto delante no mide nada."
                  % (anclas,))


# ===========================================================================
# 1. LZW de TIFF — el dialecto MSB con 'early change'
# ===========================================================================

# La linea que decide el dialecto. Quitarle el «+ 1» convierte el early change
# de TIFF en el cambio de ancho de GIF: no da error, da bytes plausibles.
MUT_TIFF_EARLY = ("                if prox + 1 >= (1 << ancho) and ancho < 12:",
                  "                if prox >= (1 << ancho) and ancho < 12:")
MUT_TIFF_CLEAR = ("            if cod == 256:\n"
                  "                del dic[258:]\n",
                  "            if cod == 256:\n"
                  "                del dic[4096:]\n")


class LzwTiff(Discriminada):

    # -- el testigo externo: un flujo escrito por ImageMagick --------------
    def _c_testigo(self, mod):
        """`_lzw_tiff` sobre un flujo AJENO tiene que dar los mismos bytes que
        la version sin comprimir del mismo raster.

        Es la unica comprobacion del fichero que no puede fabricar un
        codificador propio: un codificador y un descodificador que compartan el
        mismo error del early change se dan la razon el uno al otro.
        """
        crudos = {}
        for clave in ("tiff_gris_plano", "tiff_gris_lzw"):
            b = F.testigo(clave)
            self.assertEqual(hashlib.sha256(b).hexdigest(),
                             F.SHA256_TESTIGOS[clave],
                             "el testigo %s no es el que se midio" % clave)
            p = self.escribe(clave + ".tiff", b)
            with open(p, "rb") as fh:
                c = mod._tiff_ifd0(fh)
                fh.seek(c[273][0])
                crudos[clave] = (fh.read(c[279][0]), c.get(259, [1])[0])
        plano, _ = crudos["tiff_gris_plano"]
        comp, compr = crudos["tiff_gris_lzw"]
        self.assertEqual(compr, 5, "el testigo tiene que estar en LZW")
        salida = bytes(mod._lzw_tiff(comp))
        self.assertEqual(len(salida), 32 * 14)
        self.assertEqual(salida, plano,
                         "el LZW de TIFF de ImageMagick no se descodifica a los "
                         "mismos pixeles que su gemelo sin comprimir")

    def test_dialecto_contra_imagemagick(self):
        self._c_testigo(V)

    def test_dialecto_contra_imagemagick_discrimina(self):
        self.discrimina(self._c_testigo, MUT_TIFF_EARLY)

    # -- ida y vuelta a lo largo de los cuatro anchos ----------------------
    def _c_ida_y_vuelta(self, mod):
        rnd = random.Random(11)
        for n in (1, 10, 300, 3000, 30000, 120000):
            datos = bytes(rnd.randrange(256) for _ in range(n))
            self.assertEqual(bytes(mod._lzw_tiff(F.lzw_tiff_comprimir(datos))),
                             datos, "ida y vuelta LZW/TIFF con n=%d" % n)
        # repetitivo: fuerza entradas largas y el codigo KwKwK
        rep = b"abcabcabd" * 4000
        self.assertEqual(bytes(mod._lzw_tiff(F.lzw_tiff_comprimir(rep))), rep)

    def test_ida_y_vuelta(self):
        self._c_ida_y_vuelta(V)

    def test_ida_y_vuelta_discrimina(self):
        self.discrimina(self._c_ida_y_vuelta, MUT_TIFF_EARLY)

    # -- ClearCode a mitad de flujo ---------------------------------------
    def _c_clear(self, mod):
        # A B (AB) | Clear | C D (CD): tras el Clear, el codigo 258 tiene que
        # significar 'CD' y no 'AB'. Un diccionario que no se vacia devuelve
        # bytes plausibles y equivocados.
        flujo = F.flujo_tiff([(256, 9), (65, 9), (66, 9), (258, 9),
                              (256, 9), (67, 9), (68, 9), (258, 9), (257, 9)])
        self.assertEqual(bytes(mod._lzw_tiff(flujo)), b"ABABCDCD")
        # Y el ClearCode INICIAL, que es el que emite cualquier codificador
        # real: sin el, el primer codigo se leeria contra un diccionario que ya
        # trae entradas de una imagen anterior.
        self.assertEqual(bytes(mod._lzw_tiff(
            F.flujo_tiff([(256, 9), (90, 9), (257, 9)]))), b"Z")

    def test_clear_a_mitad(self):
        self._c_clear(V)

    def test_clear_a_mitad_discrimina(self):
        self.discrimina(self._c_clear, MUT_TIFF_CLEAR)

    # -- bordes: EOI, tope, flujo corrupto, KwKwK -------------------------
    def _c_bordes(self, mod):
        # EOI corta y devuelve lo escrito hasta ese punto
        self.assertEqual(bytes(mod._lzw_tiff(
            F.flujo_tiff([(256, 9), (65, 9), (257, 9), (66, 9)]))), b"A")
        # codigo adelantado SIN prefijo: flujo corrupto, se corta sin lanzar
        self.assertEqual(bytes(mod._lzw_tiff(
            F.flujo_tiff([(256, 9), (300, 9), (65, 9)]))), b"")
        # KwKwK: el codigo 258 se usa en el mismo instante en que se crea
        self.assertEqual(bytes(mod._lzw_tiff(
            F.flujo_tiff([(256, 9), (65, 9), (258, 9), (257, 9)]))), b"AAA")
        # `tope` corta la salida
        datos = bytes(range(256)) * 40
        self.assertEqual(len(mod._lzw_tiff(F.lzw_tiff_comprimir(datos), 100)),
                         100)
        # sin ClearCode inicial tambien decodifica: el descodificador no lo exige
        self.assertEqual(bytes(mod._lzw_tiff(
            F.flujo_tiff([(65, 9), (66, 9), (257, 9)]))), b"AB")
        # y SIN EndOfInformation: el flujo se agota y se devuelve lo leido. Es
        # el caso de una banda truncada, que en TIFF pasa en cuanto
        # StripByteCounts miente; no puede lanzar.
        self.assertEqual(bytes(mod._lzw_tiff(
            F.flujo_tiff([(65, 9), (66, 9)]))), b"AB")
        self.assertEqual(bytes(mod._lzw_tiff(b"")), b"")

    def test_bordes(self):
        self._c_bordes(V)

    def test_bordes_discrimina(self):
        # Si el KwKwK deja de anadir la primera letra del prefijo, 'AAA' pasa
        # a ser 'AA' y el resto de bordes siguen igual: es una mutacion que
        # SOLO mueve una de las cinco aserciones, que es lo que se quiere.
        self.discrimina(self._c_bordes,
                        ("                ent = prev + prev[:1]\n"
                         "            else:\n"
                         "                return out                      "
                         "# flujo corrupto: se corta",
                         "                ent = prev\n"
                         "            else:\n"
                         "                return out                      "
                         "# flujo corrupto: se corta"))


# ===========================================================================
# 2. LZW de GIF — el dialecto LSB, con corte en cuanto aparece el indice
# ===========================================================================

MUT_GIF_ANCHO = ("                if prox >= (1 << ancho) and ancho < 12:",
                 "                if prox + 1 >= (1 << ancho) and ancho < 12:")
# El ancho de codigo tras el ClearCode. Vale como discriminador de la rama del
# Clear entera; la OTRA linea de esa rama —`del dic[fin + 1:]`— esta cubierta
# pero NO es discriminable por la salida, y esta escrito por que en
# `test_clear_a_mitad_el_diccionario_rancio_es_INVISIBLE`.
MUT_GIF_CLEAR = ("            if cod == limpio:\n"
                 "                del dic[fin + 1:]\n"
                 "                prox, ancho, prev = fin + 1, mcs + 1, None\n",
                 "            if cod == limpio:\n"
                 "                del dic[fin + 1:]\n"
                 "                prox, ancho, prev = fin + 1, mcs + 2, None\n")


class LzwGif(Discriminada):

    def _c_propiedad(self, mod):
        """`_lzw_gif_usa` devuelve True EXACTAMENTE cuando el indice aparece.

        No es un caso: es la propiedad entera, barrida sobre cuatro anchos de
        codigo y cuatro tamanos. Con el ancho de codigo desincronizado, el
        descodificador lee indices que no estan y la equivalencia se rompe.
        """
        rnd = random.Random(23)
        for mcs in (2, 4, 7, 8):
            lim = 1 << mcs
            for n in (5, 200, 5000):
                idx = bytes(rnd.randrange(lim) for _ in range(n))
                comp = F.lzw_gif_comprimir(idx, mcs)
                for obj in range(lim):
                    self.assertEqual(
                        mod._lzw_gif_usa(comp, mcs, obj, 10 ** 9),
                        obj in idx,
                        "mcs=%d n=%d indice=%d" % (mcs, n, obj))

    def test_propiedad(self):
        self._c_propiedad(V)

    def test_propiedad_discrimina(self):
        self.discrimina(self._c_propiedad, MUT_GIF_ANCHO)

    def _c_clear(self, mod):
        # mcs=4: limpio=16, fin=17, la primera entrada libre es la 18 y el
        # ancho no sube hasta la 32, asi que caben las dos mitades a 5 bits.
        # 16=Clear, 17=EOI. El codigo 18 se usa a los dos lados del Clear y
        # tiene que significar cosas DISTINTAS: '01' antes, '23' despues.
        flujo = F.flujo_gif([(16, 5), (0, 5), (1, 5), (18, 5),
                             (16, 5), (2, 5), (3, 5), (18, 5), (17, 5)])
        # el indice 3 solo aparece DESPUES del Clear
        self.assertTrue(mod._lzw_gif_usa(flujo, 4, 3, 10 ** 9))
        # el indice 1 solo aparece ANTES, y sigue encontrandose
        self.assertTrue(mod._lzw_gif_usa(flujo, 4, 1, 10 ** 9))
        # y uno que no esta en ninguna de las dos mitades, no
        self.assertFalse(mod._lzw_gif_usa(flujo, 4, 9, 10 ** 9))

    def test_clear_a_mitad(self):
        self._c_clear(V)

    def test_clear_a_mitad_discrimina(self):
        self.discrimina(self._c_clear, MUT_GIF_CLEAR)

    def test_clear_a_mitad_el_diccionario_rancio_es_INVISIBLE(self):
        """REFUTACION de un intento propio, y es un resultado sobre la API.

        Se intento discriminar `del dic[fin + 1:]` —la linea que VACIA el
        diccionario en el ClearCode— y NO SE PUEDE por la salida de
        `_lzw_gif_usa`. El motivo es estructural, no falta de imaginacion: la
        funcion contesta una pregunta de PERTENENCIA, y toda entrada del
        diccionario se construye con literales que el descodificador ya emitio
        ANTES, asi que una entrada rancia no puede introducir ningun indice que
        no se hubiera visto ya. La linea se EJECUTA (esta cubierta) y su
        defecto es invisible por este canal.

        Aqui queda medido, que es lo unico honesto que se puede hacer: con el
        diccionario sin vaciar, el descodificador emite bytes DISTINTOS y la
        respuesta de pertenencia es la MISMA en los 16 indices.
        """
        mod = mutar(("            if cod == limpio:\n"
                     "                del dic[fin + 1:]\n",
                     "            if cod == limpio:\n"
                     "                del dic[4096:]\n"))
        flujo = F.flujo_gif([(16, 5), (0, 5), (1, 5), (18, 5),
                             (16, 5), (2, 5), (3, 5), (18, 5), (17, 5)])
        for obj in range(16):
            self.assertEqual(mod._lzw_gif_usa(flujo, 4, obj, 10 ** 9),
                             V._lzw_gif_usa(flujo, 4, obj, 10 ** 9),
                             "indice %d" % obj)

    def _c_bordes(self, mod):
        # EndOfInformation antes del indice buscado: False aunque el indice
        # estuviera detras
        flujo = F.flujo_gif([(16, 5), (0, 5), (17, 5), (3, 5)])
        self.assertFalse(mod._lzw_gif_usa(flujo, 4, 3, 10 ** 9))
        # codigo adelantado sin prefijo -> False, sin lanzar
        self.assertFalse(mod._lzw_gif_usa(F.flujo_gif([(16, 5), (25, 5)]),
                                          4, 0, 10 ** 9))
        # KwKwK: el codigo 18 se usa en el mismo instante en que se crea
        self.assertTrue(mod._lzw_gif_usa(
            F.flujo_gif([(16, 5), (7, 5), (18, 5), (17, 5)]), 4, 7, 10 ** 9))
        # el tope corta: el indice 3 esta al final y no se llega
        idx = bytes([0, 1, 2] * 300 + [3])
        comp = F.lzw_gif_comprimir(idx, 2)
        self.assertTrue(mod._lzw_gif_usa(comp, 2, 3, 10 ** 9))
        self.assertFalse(mod._lzw_gif_usa(comp, 2, 3, 10))
        # flujo vacio
        self.assertFalse(mod._lzw_gif_usa(b"", 2, 0, 10 ** 9))

    def test_bordes(self):
        self._c_bordes(V)

    def test_bordes_discrimina(self):
        self.discrimina(self._c_bordes,
                        ("            if leidos >= tope:\n"
                         "                return False",
                         "            if leidos >= tope * 10 ** 9:\n"
                         "                return False"))

    def test_un_mcs_fuera_de_rango_es_un_error_DECLARADO(self):
        """CASO MINIMO del defecto, ARREGLADO: `_lzw_gif_usa` no validaba
        `mcs`.

        `mcs` sale de un byte del fichero. Con `mcs >= 9`,
        `bytes([i]) for i in range(1 << mcs)` lanzaba `ValueError: bytes must
        be in range(0, 256)` en la PRIMERA linea util —un error de la
        implementacion, no del formato—. GIF89a fija el rango en 2..8, y el
        censo de este repositorio lo confirma: los 180 bloques de imagen de los
        GIF del arbol usan `mcs = 8`, ninguno otro valor.

        Sigue siendo un `ValueError`, asi que `_alfa_min_gif` lo captura igual y
        el contrato ve el mismo campo; lo que cambia es el MENSAJE, que ahora
        dice cual es el byte malo.
        """
        for mcs in (9, 12, 255, 1, 0):
            with self.subTest(mcs=mcs):
                with self.assertRaises(ValueError) as cm:
                    V._lzw_gif_usa(b"\x00\x01", mcs, 0, 10 ** 9)
                self.assertIn("mcs", str(cm.exception))
                self.assertIn(str(mcs), str(cm.exception))
        # ...y los del rango legitimo no lanzan
        for mcs in range(2, 9):
            with self.subTest(mcs=mcs):
                V._lzw_gif_usa(F.lzw_gif_comprimir(b"\x00\x01", mcs), mcs, 0,
                               10 ** 9)
        datos = F.gif(4, 2, [F.gif_gce(0, True),
                             F.gif_imagen(4, 2, b"\x00" * 8, mcs=9,
                                          datos=b"\x00\x01\x02")])
        r = V._alfa_min_gif(self.escribe("mcs9.gif", datos))
        self.assertFalse(r["evaluable"])
        self.assertIn("LZW del fotograma 1 ilegible", r["motivo"])
        self.assertIn("ValueError", r["motivo"])
        self.assertIn("mcs", r["motivo"])
        self.assertEqual(r["cota_alfa_min"], 0.0)


# ===========================================================================
# 3. `_tiff` — el recorrido de IFD de la sonda en proceso
# ===========================================================================

class SondaTiff(Discriminada):

    def _rgba(self, be=False, **kw):
        px = F.rgba_degradado(4, 3, 8, be)
        return F.tiff_muestras(px, 4, 3, be=be, **kw)

    def _c_endianness(self, mod):
        """El mismo raster en `II` y en `MM` tiene que sondearse igual.

        El magico de endianness es donde la trampa 71 ya mordio una vez («el
        magico de VIPS es de endianness y la tabla traia media»).
        """
        for be in (False, True):
            p = self.escribe("e%s.tiff" % be, self._rgba(be=be, resolucion=150))
            with open(p, "rb") as fh:
                d = mod._tiff(fh)
            self.assertEqual((d["ancho"], d["alto"]), (4, 3), "be=%s" % be)
            self.assertEqual(d["profundidad_bits"], 8)
            self.assertEqual(d["canales"], 4)
            self.assertEqual(d["compresion"], 1)
            self.assertTrue(d["tiene_alfa"])
            self.assertEqual(d["ppp"], 150)
            self.assertEqual(d["n_imagenes"], 1)
            self.assertEqual(d["formato"], "tiff")

    def test_endianness(self):
        self._c_endianness(V)

    def test_endianness_discrimina(self):
        self.discrimina(self._c_endianness,
                        ('    cab = fh.read(8)\n    be = cab[:2] == b"MM"\n'
                         '    d = {"formato": "tiff", "categoria": "imagen"}',
                         '    cab = fh.read(8)\n    be = cab[:2] == b"II"\n'
                         '    d = {"formato": "tiff", "categoria": "imagen"}'))

    def _c_resolucion(self, mod):
        """ResolutionUnit decide la unidad: 2 = pulgada, 3 = centimetro."""
        p = self.escribe("pulg.tiff", self._rgba(resolucion=200, unidad=2))
        with open(p, "rb") as fh:
            self.assertEqual(mod._tiff(fh)["ppp"], 200)
        p = self.escribe("cm.tiff", self._rgba(resolucion=100, unidad=3))
        with open(p, "rb") as fh:
            self.assertEqual(mod._tiff(fh)["ppp"], 254)
        # unidad 1 (ninguna): no se declara ppp, que es lo correcto
        p = self.escribe("sinu.tiff", self._rgba(resolucion=100, unidad=1))
        with open(p, "rb") as fh:
            self.assertNotIn("ppp", mod._tiff(fh))

    def test_resolucion(self):
        self._c_resolucion(V)

    def test_resolucion_discrimina(self):
        self.discrimina(self._c_resolucion,
                        ('                d["ppp"] = round(campos[282][0] * 2.54)',
                         '                d["ppp"] = round(campos[282][0] / 2.54)'))

    def _c_varias_ifd(self, mod):
        """Un TIFF multipagina y el tope de 64 IFD."""
        px = F.rgba_degradado(2, 2, 8)
        una = {256: (F.SHORT, [2]), 257: (F.SHORT, [2]),
               258: (F.SHORT, [8] * 4), 277: (F.SHORT, [4]),
               259: (F.SHORT, [1]), 273: (F.LONG, [F.Desp(0)]),
               279: (F.LONG, [len(px)])}
        p = self.escribe("tres.tiff", F.construir_tiff([una] * 3, [px]))
        with open(p, "rb") as fh:
            self.assertEqual(mod._tiff(fh)["n_imagenes"], 3)
        # 70 IFD: el lector para en 64 a proposito (no recorre un fichero
        # hostil entero)
        p = self.escribe("setenta.tiff", F.construir_tiff([una] * 70, [px]))
        with open(p, "rb") as fh:
            self.assertEqual(mod._tiff(fh)["n_imagenes"], 64)

    def test_varias_ifd(self):
        self._c_varias_ifd(V)

    def test_varias_ifd_discrimina(self):
        self.discrimina(self._c_varias_ifd,
                        ("    while desp and n_img < 64:",
                         "    while desp and n_img < 128:"))

    def _c_tipos_y_valores_externos(self, mod):
        """Tipos de entrada de IFD y el valor que NO cabe en los 4 bytes.

        `BitsPerSample` con 4 SHORT ocupa 8 bytes, asi que el campo lleva un
        DESPLAZAMIENTO y el lector tiene que ir a buscarlo y volver. Los tipos
        raros (RATIONAL con cuenta 0, ASCII con desplazamiento fuera del
        fichero) no pueden lanzar: el lector devuelve un numero, y ese numero
        es el veredicto.
        """
        px = F.rgba_degradado(4, 3, 8)
        campos = {
            256: (F.SHORT, [4]), 257: (F.SHORT, [3]),
            258: (F.SHORT, [8, 8, 8, 8]),            # 8 B: valor externo
            259: (F.SHORT, [1]), 277: (F.SHORT, [4]),
            273: (F.LONG, [F.Desp(0)]), 279: (F.LONG, [len(px)]),
            338: (F.SHORT, [2]),
            282: F.Crudo(F.RACIONAL, 0, b""),        # RATIONAL con tam < 8
            296: (F.SHORT, [2]),
            270: F.Crudo(F.ASCII, 5, struct.pack("<I", 0x0FFFFF00)),
            700: (F.BYTE, [7]),
        }
        p = self.escribe("tipos.tiff", F.construir_tiff([campos], [px]))
        with open(p, "rb") as fh:
            d = mod._tiff(fh)
        self.assertEqual(d["profundidad_bits"], 8)   # leido del valor externo
        self.assertEqual(d["canales"], 4)
        self.assertTrue(d["tiene_alfa"])
        # XResolution con cuenta 0 vale 0, y con unidad 2 eso son 0 ppp: el
        # lector responde un numero en vez de reventar, que es el contrato.
        self.assertEqual(d["ppp"], 0)

    def test_tipos_y_valores_externos(self):
        self._c_tipos_y_valores_externos(V)

    def test_tipos_y_valores_externos_discrimina(self):
        self.discrimina(self._c_tipos_y_valores_externos,
                        ("            if tam > 4:\n                pos = _u32(bruto, 0, be)",
                         "            if tam > 4000:\n                pos = _u32(bruto, 0, be)"))

    def _c_alfa_por_canales(self, mod):
        """`tiene_alfa` sale de ExtraSamples O de SamplesPerPixel en (2, 4)."""
        px = F.rgba_degradado(4, 3, 8)
        base = {256: (F.SHORT, [4]), 257: (F.SHORT, [3]),
                258: (F.SHORT, [8] * 4), 259: (F.SHORT, [1]),
                273: (F.LONG, [F.Desp(0)]), 279: (F.LONG, [len(px)])}
        casos = {1: False, 2: True, 3: False, 4: True}
        for spp, esperado in casos.items():
            c = dict(base)
            c.update({277: (F.SHORT, [spp]), 258: (F.SHORT, [8] * spp)})
            p = self.escribe("spp%d.tiff" % spp,
                             F.construir_tiff([c], [px]))
            with open(p, "rb") as fh:
                self.assertIs(mod._tiff(fh)["tiene_alfa"], esperado,
                              "SamplesPerPixel=%d" % spp)
        # y con ExtraSamples explicito, un spp de 3 tambien declara alfa
        c = dict(base)
        c.update({277: (F.SHORT, [3]), 258: (F.SHORT, [8] * 3),
                  338: (F.SHORT, [2])})
        p = self.escribe("extras.tiff", F.construir_tiff([c], [px]))
        with open(p, "rb") as fh:
            self.assertTrue(mod._tiff(fh)["tiene_alfa"])

    def test_alfa_por_canales(self):
        self._c_alfa_por_canales(V)

    def test_alfa_por_canales_discrimina(self):
        self.discrimina(self._c_alfa_por_canales,
                        ('            d["tiene_alfa"] = bool(campos.get(338, [0])[0])'
                         ' or d["canales"] in (2, 4)',
                         '            d["tiene_alfa"] = bool(campos.get(338, [0])[0])'
                         ' or d["canales"] in (2,)'))

    def test_entra_por_sondear_en_proceso(self):
        """La sonda publica llega de verdad a `_tiff` y a `_gif`.

        Sin esto, las comprobaciones de arriba estarian midiendo una funcion
        que el producto no llama por ninguna ruta (trampa 109).
        """
        p = self.escribe("via.tiff", self._rgba(resolucion=96))
        d = V.sondear_en_proceso(p)
        self.assertEqual(d["firma"], "tiff")
        self.assertEqual((d["ancho"], d["alto"]), (4, 3))
        self.assertEqual(d["ppp"], 96)
        g = self.escribe("via.gif", F.gif(4, 2, [
            F.gif_gce(0, True), F.gif_imagen(4, 2, b"\x00\x01" * 4)]))
        d = V.sondear_en_proceso(g)
        self.assertEqual(d["firma"], "gif")
        self.assertEqual((d["ancho"], d["alto"]), (4, 2))
        self.assertEqual(d["n_imagenes"], 1)


# ===========================================================================
# 4. `_tiff_ifd0` y `_tiff_descomprimir`
# ===========================================================================

class Ifd0YDescompresion(Discriminada):

    def _c_ifd0(self, mod):
        px = F.rgba_degradado(4, 3, 8)
        for be in (False, True):
            campos = {
                256: (F.SHORT, [4]), 257: (F.SHORT, [3]),
                258: (F.SHORT, [8, 8, 8, 8]),         # externo (8 B)
                259: (F.SHORT, [1]),
                273: (F.LONG, [F.Desp(0)]), 277: (F.SHORT, [4]),
                278: (F.SHORT, [3]), 279: (F.LONG, [len(px)]),
                284: (F.SHORT, [1]), 338: (F.SHORT, [2]),
                317: (F.BYTE, [1]),                   # tipo 1: lista de bytes
                339: (F.SHORT, [1]),
                270: (F.ASCII, [65, 66, 67, 0]),      # NO esta en la tabla
                322: F.Crudo(F.RACIONAL, 1, struct.pack(">II" if be else "<II",
                                                        3, 1)),
            }
            p = self.escribe("ifd0-%s.tiff" % be,
                             F.construir_tiff([campos], [px], be=be))
            with open(p, "rb") as fh:
                c = mod._tiff_ifd0(fh)
            self.assertIs(c["_be"], be)
            # `.get` y no `c[...]`: con el mutante la clave no esta, y un
            # KeyError no demostraria que la comprobacion juzgo un valor.
            self.assertEqual(c.get(258), [8, 8, 8, 8])  # valor externo leido
            self.assertEqual(c.get(277), [4])
            self.assertEqual(c.get(273), [8])           # LONG
            self.assertEqual(c.get(317), [1])           # BYTE
            self.assertNotIn(270, c, "una etiqueta fuera de la tabla del "
                                     "carril alfa no se guarda")
            # RATIONAL no es ninguno de los tipos que el lector empaqueta: la
            # etiqueta se ve (322 esta en la tabla) pero NO se guarda valor.
            self.assertNotIn(322, c)

    def test_ifd0(self):
        self._c_ifd0(V)

    def test_ifd0_discrimina(self):
        self.discrimina(self._c_ifd0,
                        ("        if etiq not in _TIFF_ETIQ_ALFA:",
                         "        if etiq in _TIFF_ETIQ_ALFA:"))

    def _c_descomprimir(self, mod):
        rnd = random.Random(5)
        datos = bytes(rnd.randrange(4) for _ in range(600)) + b"\x07" * 40
        pares = {1: bytes(datos), 5: F.lzw_tiff_comprimir(datos),
                 8: zlib.compress(datos), 32946: zlib.compress(datos),
                 32773: F.packbits_comprimir(datos)}
        for compr, comp in pares.items():
            self.assertEqual(bytes(mod._tiff_descomprimir(comp, compr,
                                                          len(datos))),
                             datos, "compresion %d" % compr)
        # HALLAZGO, ARREGLADO: `esperado` significaba dos cosas distintas segun
        # la compresion. En 1, 5, 8 y 32946 era un TOPE EXACTO; en PackBits era
        # solo una condicion de parada del bucle, que se evalua ANTES de volcar
        # un literal de hasta 128 bytes, asi que la salida se pasaba (28 bytes
        # pidiendo 17). No hacia dano —el carril alfa rebana por filas y lo que
        # sobra queda al final— pero un llamador que lo tomara por un tope se
        # llevaba una sorpresa, y el nombre del parametro invita a tomarlo por
        # un tope. Ahora es un tope en las CINCO.
        for compr in (1, 5, 8, 32946, 32773):
            self.assertEqual(len(mod._tiff_descomprimir(pares[compr], compr,
                                                        17)), 17,
                             "compresion %d: `esperado` es un tope" % compr)
        # ...y el contenido de los 17 primeros bytes no se ha movido
        for compr in (1, 5, 8, 32946, 32773):
            self.assertEqual(bytes(mod._tiff_descomprimir(pares[compr], compr,
                                                          17)),
                             datos[:17], "compresion %d" % compr)

    def test_descomprimir(self):
        self._c_descomprimir(V)

    def test_descomprimir_discrimina(self):
        self.discrimina(self._c_descomprimir,
                        ("    if compr == 32773:\n        return _packbits(datos, esperado)",
                         "    if compr == 32773:\n        return _lzw_tiff(datos, esperado)"))

    def test_descomprimir_compresion_desconocida(self):
        """La rama `raise` de `_tiff_descomprimir` es INALCANZABLE desde
        `_alfa_min_tiff`, y por eso se ejercita aqui como unidad.

        `_alfa_min_tiff` filtra antes con `_TIFF_COMPR_OK`, que contiene
        exactamente los cinco codigos que la funcion sabe tratar. Que la
        guarda y la tabla no puedan separarse es bueno; que nadie ejecutara
        nunca el `raise` significaba que un sexto codigo anadido a la tabla sin
        anadirlo a la funcion habria salido por una excepcion sin capturar.
        """
        self.assertEqual(set(V._TIFF_COMPR_OK), {1, 5, 8, 32946, 32773})
        with self.assertRaises(ValueError) as cm:
            V._tiff_descomprimir(b"\x00" * 8, 7, 8)
        self.assertIn("7", str(cm.exception))

    def test_packbits_cabecera_128_es_no_operacion(self):
        """La cabecera 128 de PackBits no es literal ni carrera: se salta.

        Ningun codificador la emite, asi que solo se llega con un flujo escrito
        a mano — y es justo la clase de byte que aparece en un fichero
        corrompido.
        """
        self.assertEqual(bytes(V._packbits(b"\x80\x02ABC", 3)), b"ABC")
        self.assertEqual(bytes(V._packbits(b"\xfeZ", 3)), b"ZZZ")
        # cabecera de carrera sin el byte que repetir: no lanza, corta
        self.assertEqual(bytes(V._packbits(b"\xfe", 3)), b"")


# ===========================================================================
# 5. `_alfa_min_tiff` — el carril del alfa, que es lo que decide el veredicto
# ===========================================================================

# Leer el carril del ROJO en vez del carril del ALFA. No lanza: devuelve otro
# numero. Es exactamente el modo de fallo que preocupa en este cubo.
MUT_CARRIL = ("            paso, desp0, por_fila = spp * ancho_m, "
              "(spp - 1) * ancho_m, an * spp * ancho_m",
              "            paso, desp0, por_fila = spp * ancho_m, "
              "0 * ancho_m, an * spp * ancho_m")


class AlfaTiff(Discriminada):

    ANCHO, ALTO = 6, 5

    def _planariza(self, px, bps):
        m = bps // 8
        out = bytearray()
        for c in range(4):
            for i in range(self.ANCHO * self.ALTO):
                o = (i * 4 + c) * m
                out += px[o:o + m]
        return bytes(out)

    def _fichero(self, *, bps=8, compr=1, predictor=1, planar=1, be=False,
                 filas_por_banda=2, alfa=None, nombre="m.tiff", **kw):
        px = F.rgba_degradado(self.ANCHO, self.ALTO, bps, be, alfa)
        if planar == 2:
            px = self._planariza(px, bps)
        b = F.tiff_muestras(px, self.ANCHO, self.ALTO, bps=bps, compr=compr,
                            predictor=predictor, planar=planar, be=be,
                            filas_por_banda=filas_por_banda, **kw)
        return self.escribe(nombre, b)

    def _c_matriz(self, mod):
        """64 celdas: 2 profundidades x 4 compresiones x 2 planares x 2
        predictores x 2 endianness, TODAS sobre el mismo alfa.

        Las 64 tienen que dar el mismo `alfa_min` normalizado. Es la unica
        forma de que un error de carril, de zancada o de orden de bytes no se
        confunda con «el fichero era asi»: el mismo alfa por caminos de codigo
        distintos tiene que dar el mismo numero.
        """
        vistos = 0
        for bps in (8, 16):
            for compr in (1, 5, 8, 32773):
                for planar in (1, 2):
                    for pred in (1, 2):
                        for be in (False, True):
                            p = self._fichero(bps=bps, compr=compr,
                                              predictor=pred, planar=planar,
                                              be=be, nombre="mx.tiff")
                            r = mod._alfa_min_tiff(p, True)
                            clave = (bps, compr, planar, pred, be)
                            self.assertTrue(r["evaluable"],
                                            "%s: %s" % (clave, r.get("motivo")))
                            self.assertTrue(r["tiene_alfa"], clave)
                            self.assertEqual(r["alfa_min"], 0.0, clave)
                            self.assertTrue(r["exacto"], clave)
                            self.assertEqual(r["primer_transparente"], (0, 1),
                                             clave)
                            vistos += 1
        self.assertEqual(vistos, 64)

    def test_matriz(self):
        self._c_matriz(V)

    def test_matriz_discrimina(self):
        self.discrimina(self._c_matriz, MUT_CARRIL)

    def _c_cota_y_exacto(self, mod):
        """`exacto=False` devuelve una COTA y lo declara; `exacto=True`, el
        minimo. Confundirlos es publicar una cota como si fuera una medida."""
        # alfa constante a la mitad: nunca llega a 0, asi que el corte temprano
        # se nota en `filas_leidas` y en `exacto`.
        def medio(x, y, _t=None):
            return 128

        for bps, mitad in ((8, 128), (16, 128)):
            def alfa(x, y, _m=mitad):
                return _m

            p = self._fichero(bps=bps, alfa=alfa, filas_por_banda=self.ALTO,
                              nombre="cota%d.tiff" % bps)
            corta = mod._alfa_min_tiff(p, False)
            larga = mod._alfa_min_tiff(p, True)
            self.assertFalse(corta["exacto"], bps)
            self.assertTrue(larga["exacto"], bps)
            self.assertEqual(corta["filas_leidas"], 1, bps)
            self.assertEqual(larga["filas_leidas"], self.ALTO, bps)
            self.assertAlmostEqual(corta["alfa_min"], larga["alfa_min"], 9)
            self.assertGreater(corta["alfa_min"], 0.0)

    def test_cota_y_exacto(self):
        self._c_cota_y_exacto(V)

    def test_cota_y_exacto_discrimina(self):
        self.discrimina(self._c_cota_y_exacto,
                        ("                if mn == 0 or (mn < tope and not exacto):\n"
                         "                    break\n"
                         "            y0 += filas_banda",
                         "                if mn == 0:\n"
                         "                    break\n"
                         "            y0 += filas_banda"))

    def _c_alfa_trivial(self, mod):
        """TRAMPA 1: un TIFF que DECLARA alfa y es enteramente opaco.

        `tiene_alfa` es True y `alfa_min` es 1.0. Un contrato que exija
        «conserva el alfa» mirando solo `tiene_alfa` da por buena una
        conversion que tira el canal, y da por mala una que no tenia nada que
        conservar. Ademas se comprueba el ATAJO DE FILA OPACA: con predictor 1
        la fila opaca es todo 0xFF y con predictor 2 es 0xFF y ceros; las dos
        formas se saltan sin mirar pixel a pixel, y `filas_leidas` lo prueba.
        """
        def opaco(x, y, _t=None):
            return 255

        for bps in (8, 16):
            tope = (1 << bps) - 1

            def op(x, y, _t=tope):
                return _t

            for pred in (1, 2):
                p = self._fichero(bps=bps, predictor=pred, alfa=op,
                                  filas_por_banda=self.ALTO,
                                  nombre="op%d-%d.tiff" % (bps, pred))
                r = mod._alfa_min_tiff(p, False)
                self.assertTrue(r["tiene_alfa"], (bps, pred))
                self.assertEqual(r["alfa_min"], 1.0, (bps, pred))
                self.assertTrue(r["exacto"], (bps, pred))
                self.assertEqual(r["primer_transparente"], None, (bps, pred))
                self.assertEqual(r["filas_leidas"], self.ALTO, (bps, pred))

    def test_alfa_trivial(self):
        self._c_alfa_trivial(V)

    def test_alfa_trivial_discrimina(self):
        # REFUTACION DE MI PROPIA HIPOTESIS, y queda escrita porque es el
        # resultado: el atajo de fila opaca NO se puede discriminar por la
        # salida. Rompiendo `op_a`, las filas dejan de saltarse pero
        # `_tiff_min_fila_8` las des-predice y devuelve el MISMO 255, y
        # `filas_leidas` se incrementa ANTES del atajo, asi que tampoco se
        # mueve. El atajo es exacto Y neutro: lo unico que cambia es el tiempo,
        # que §3 prohibe publicar. Lo que si discrimina esta comprobacion es la
        # regla de exactitud: un opaco tiene `mn == tope`, y por eso el
        # resultado se declara EXACTO aunque se haya pedido la version corta.
        self.discrimina(self._c_alfa_trivial,
                        ('        r["exacto"] = exacto or mn in (0, tope)',
                         '        r["exacto"] = exacto or mn == 0'))

    def test_sin_alfa_no_descomprime_nada(self):
        """Sin ExtraSamples y con spp que no sea 2 ni 4, la funcion sale sin
        tocar las bandas: `filas_leidas` a 0 y la via sin nombrar compresion."""
        px = bytes(range(256))[: self.ANCHO * self.ALTO]
        b = F.tiff_muestras(px, self.ANCHO, self.ALTO, spp=1, compr=5,
                            extrasamples=(), foto=1)
        r = V._alfa_min_tiff(self.escribe("gris.tiff", b), True)
        self.assertTrue(r["evaluable"])
        self.assertFalse(r["tiene_alfa"])
        self.assertEqual(r["alfa_min"], 1.0)
        self.assertEqual(r["filas_leidas"], 0)
        self.assertEqual(r["via"], "ExtraSamples/SamplesPerPixel")

    def _c_motivos(self, mod):
        """Los OCHO caminos de «no evaluable». Cada uno tiene que decir por que.

        Un verificador que no distingue «comprobado» de «no he podido
        comprobarlo» repite el fallo que este proyecto documenta de
        markitdown-mcp, asi que el mensaje es parte del contrato.
        """
        px = F.rgba_degradado(self.ANCHO, self.ALTO, 8)
        comun = dict(filas_por_banda=2)

        def hazlo(nombre, **kw):
            b = F.tiff_muestras(px, self.ANCHO, self.ALTO, **dict(comun, **kw))
            return mod._alfa_min_tiff(self.escribe(nombre, b), True)

        casos = [
            ("teselas.tiff", dict(extra={322: (F.SHORT, [8]),
                                         323: (F.SHORT, [8])}), "teselas"),
            ("jpeg.tiff", dict(extra={259: (F.SHORT, [7])}), "compresion TIFF 7"),
            ("flotante.tiff", dict(extra={339: (F.SHORT, [3])}), "SampleFormat 3"),
            ("bps32.tiff", dict(extra={258: (F.SHORT, [32] * 4)}),
             "BitsPerSample 32"),
            ("pred3.tiff", dict(extra={317: (F.SHORT, [3])}), "Predictor 3"),
            ("sinbandas.tiff", dict(extra={273: None}), "bandas TIFF ilegibles"),
            ("ancho0.tiff", dict(extra={256: (F.SHORT, [0])}),
             "bandas TIFF ilegibles"),
            ("planar3.tiff", dict(extra={284: (F.SHORT, [3])}),
             "PlanarConfiguration 3"),
            ("planar2corto.tiff", dict(extra={284: (F.SHORT, [2])}),
             "PlanarConfig=2"),
        ]
        for nombre, kw, trozo in casos:
            r = hazlo(nombre, **kw)
            self.assertFalse(r["evaluable"], nombre)
            self.assertIsNone(r["alfa_min"], nombre)
            self.assertIn(trozo, r["motivo"], nombre)
            self.assertTrue(r["tiene_alfa"], nombre)

        # banda ilegible: Deflate declarado sobre bytes que no lo son
        b = F.tiff_muestras(px, self.ANCHO, self.ALTO, compr=8, **comun)
        roto = bytearray(b)
        # el primer bloque empieza en el byte 8 (justo tras la cabecera)
        roto[8:16] = b"\x00" * 8
        r = mod._alfa_min_tiff(self.escribe("zlibroto.tiff", bytes(roto)), True)
        self.assertFalse(r["evaluable"])
        self.assertIn("ilegible", r["motivo"])
        self.assertIn("error", r["motivo"].lower())

    def test_motivos(self):
        self._c_motivos(V)

    def test_motivos_discrimina(self):
        self.discrimina(self._c_motivos,
                        ("        if 322 in c or 323 in c:", "        if False:"))

    def _c_16_bits_byte_alto_saturado(self, mod):
        """16 bits, predictor 1, con TODOS los bytes altos a 0xFF y los bajos
        variando: el minimo NO es `min(altos)<<8 | min(bajos)`.

        `_tiff_min_fila_16` tiene un atajo para ese caso —si el byte alto
        minimo ya es 255, el minimo del pixel es 65280 mas el byte bajo mas
        pequeno— y es la rama que el atajo de fila opaca NO tapa: la fila no es
        opaca (0xFF80 no es 0xFFFF) pero su byte alto si esta saturado.
        """
        def alfa(x, y, _t=None):
            return 0xFF00 | ((x * 17 + y * 5) % 200 + 20)

        for be in (False, True):
            p = self._fichero(bps=16, predictor=1, be=be, alfa=alfa,
                              filas_por_banda=self.ALTO,
                              nombre="alto%s.tiff" % be)
            r = mod._alfa_min_tiff(p, True)
            self.assertTrue(r["evaluable"], r.get("motivo"))
            esperado = min(0xFF00 | ((x * 17 + y * 5) % 200 + 20)
                           for y in range(self.ALTO)
                           for x in range(self.ANCHO))
            self.assertAlmostEqual(r["alfa_min"], esperado / 65535.0, 12,
                                   "be=%s" % be)
            self.assertGreater(r["alfa_min"], 0.99)
            self.assertLess(r["alfa_min"], 1.0)

    def test_16_bits_byte_alto_saturado(self):
        self._c_16_bits_byte_alto_saturado(V)

    def test_16_bits_byte_alto_saturado_discrimina(self):
        self.discrimina(self._c_16_bits_byte_alto_saturado,
                        ("        return 65280 + (min(lo) if lo else 255)",
                         "        return 65280 + (max(lo) if lo else 255)"))

    def test_rows_per_strip_cero_cae_al_alto(self):
        """`RowsPerStrip = 0` es una division por cero esperando: el lector cae
        al alto de la imagen. Es una linea, y sin ella el fichero revienta."""
        px = F.rgba_degradado(self.ANCHO, self.ALTO, 8)
        b = F.tiff_muestras(px, self.ANCHO, self.ALTO,
                            extra={278: (F.SHORT, [0])})
        r = V._alfa_min_tiff(self.escribe("rps0.tiff", b), True)
        self.assertTrue(r["evaluable"], r.get("motivo"))
        self.assertEqual(r["alfa_min"], 0.0)
        self.assertEqual(r["filas_leidas"], self.ALTO)

    def test_bits_por_muestra_vacio_cae_a_8(self):
        """`BitsPerSample` con cuenta 0: la lista sale vacia y el lector cae al
        valor por defecto en vez de indexar una lista vacia."""
        px = F.rgba_degradado(self.ANCHO, self.ALTO, 8)
        b = F.tiff_muestras(px, self.ANCHO, self.ALTO,
                            extra={258: F.Crudo(F.SHORT, 0, b"")})
        r = V._alfa_min_tiff(self.escribe("bpsvacio.tiff", b), True)
        self.assertTrue(r["evaluable"], r.get("motivo"))
        self.assertEqual(r["alfa_min"], 0.0)

    def test_llega_por_alfa_minimo(self):
        """El despachador publico entra de verdad en el carril del TIFF.

        Y de paso queda escrito que su valor por defecto es `exacto=False`:
        devuelve una COTA (la primera fila con alfa < 1) y la declara con
        `exacto: False`. Confundir la cota con el minimo es publicar 0,749
        donde el fichero tiene un 0.
        """
        p = self._fichero(nombre="desp.tiff")
        r = V.alfa_minimo(p)
        self.assertEqual(r["formato"], "tiff")
        self.assertTrue(r["tiene_alfa"])
        self.assertFalse(r["exacto"])
        self.assertLess(r["alfa_min"], 1.0)
        self.assertGreater(r["alfa_min"], 0.0)
        self.assertTrue(r["alfa_no_trivial"])
        self.assertEqual(V.alfa_minimo(p, exacto=True)["alfa_min"], 0.0)


# ===========================================================================
# 6. `_gif` — la sonda de GIF
# ===========================================================================

class SondaGif(Discriminada):

    def _c_recuento(self, mod):
        """Contar fotogramas exige recorrer los bloques de verdad.

        Se mezclan las cuatro cosas que hay en un GIF real: tabla global, tabla
        LOCAL (que hay que saltar por tamano), extensiones que no son GCE, y
        varios fotogramas.

        Y la tabla local lleva a proposito un 0x2C —el byte del descriptor de
        imagen— como componente de color, que es perfectamente legitimo. El
        lector tiene que saltarla por TAMANO; si se pusiera a buscar
        marcadores, contaria un fotograma de mas.
        """
        paleta = bytearray()
        for i in range(8):
            paleta += bytes([0x2C, i, 0x21])          # 0x2C y 0x21 en la paleta
        piezas = [
            F.gif_ext_aplicacion(),
            F.gif_gce(0, True),
            F.gif_imagen(4, 2, b"\x00\x01\x02\x03" * 2, mcs=2),
            F.gif_ext_comentario(b"segundo"),
            F.gif_gce(1, True),
            F.gif_imagen(4, 2, b"\x01" * 8, mcs=2, lct_bits=3,
                         lct_bytes=bytes(paleta)),
            F.gif_imagen(2, 2, b"\x02" * 4, mcs=2, izq=1, arr=0),
        ]
        p = self.escribe("tres.gif", F.gif(4, 2, piezas, gct_bits=2))
        with open(p, "rb") as fh:
            d = mod._gif(fh)
        self.assertEqual(d["n_imagenes"], 3)
        self.assertEqual((d["ancho"], d["alto"]), (4, 2))
        self.assertEqual(d["colores_paleta"], 4)
        self.assertEqual(d["profundidad_bits"], 8)
        self.assertTrue(d["tiene_alfa"])

    def test_recuento(self):
        self._c_recuento(V)

    def test_recuento_discrimina(self):
        # No saltar la tabla LOCAL desincroniza el recorrido: el lector empieza
        # a leer la paleta como si fueran longitudes de sub-bloque.
        self.discrimina(self._c_recuento,
                        ("            if desc[8] & 0x80:",
                         "            if desc[8] & 0x00:"))

    def _c_sin_tabla_global(self, mod):
        """Sin tabla global de color, `colores_paleta` es 0 y no hay salto."""
        p = self.escribe("singct.gif", F.gif(3, 3, [
            F.gif_imagen(3, 3, b"\x00" * 9, mcs=2, lct_bits=2)],
            gct_bits=None))
        with open(p, "rb") as fh:
            d = mod._gif(fh)
        self.assertEqual(d["colores_paleta"], 0)
        self.assertEqual(d["n_imagenes"], 1)
        self.assertEqual((d["ancho"], d["alto"]), (3, 3))

    def test_sin_tabla_global(self):
        self._c_sin_tabla_global(V)

    def test_sin_tabla_global_discrimina(self):
        self.discrimina(self._c_sin_tabla_global,
                        ('    d["colores_paleta"] = 2 ** ((c[4] & 0x07) + 1) '
                         'if c[4] & 0x80 else 0',
                         '    d["colores_paleta"] = 2 ** ((c[4] & 0x07) + 1)'))

    def test_la_sonda_declara_alfa_en_TODO_gif(self):
        """OBSERVACION, medida: `_gif` pone `tiene_alfa: True` como CONSTANTE
        del diccionario inicial, sin mirar el fichero.

        No es un error del lector —en GIF el canal alfa es una propiedad del
        formato, no del fichero: siempre se PUEDE declarar un indice
        transparente— pero significa que **el punto 3 del contrato no puede
        distinguir un GIF opaco de uno transparente por la sonda**: los dos
        declaran alfa. Quien lo distingue es `alfa_minimo`, que descomprime.
        Aqui queda el contraste con numero, sobre CUATRO ficheros que la sonda
        no puede separar y el carril del alfa si.
        """
        casos = [
            ("opaco sin gce", F.gif(4, 2, [F.gif_imagen(4, 2, b"\x00" * 8)]),
             1.0),
            ("gce con bandera 0", F.gif(4, 2, [
                F.gif_gce(0, False), F.gif_imagen(4, 2, b"\x00" * 8)]), 1.0),
            ("declarado y NO usado", F.gif(4, 2, [
                F.gif_gce(3, True),
                F.gif_imagen(4, 2, bytes([0, 1, 2, 0] * 2))]), 1.0),
            ("declarado Y usado", F.gif(4, 2, [
                F.gif_gce(3, True),
                F.gif_imagen(4, 2, bytes([0, 1, 2, 3] * 2))]), 0.0),
        ]
        for etiqueta, datos, alfa in casos:
            p = self.escribe("obs-%s.gif" % etiqueta.replace(" ", "_"), datos)
            with open(p, "rb") as fh:
                self.assertIs(V._gif(fh)["tiene_alfa"], True,
                              "la sonda dice alfa en los cuatro: " + etiqueta)
            self.assertEqual(V.alfa_minimo(p, exacto=True)["alfa_min"], alfa,
                             etiqueta)

    def test_truncados_la_sonda_los_SOBREVIVE_TODOS(self):
        """`_gif` devuelve un recuento sobre CUALQUIER corte del fichero.

        Se barren los 32 cortes de un GIF minimo de 44 B —de la cabecera
        completa al fichero entero—, no tres elegidos a mano: un lector de
        cabeceras que aguanta los cortes que a uno se le ocurren no ha
        demostrado nada. La guarda `if len(desc) < 9: break` y los dos
        `if not s` son justo lo que lo sostiene.
        """
        entero = F.gif(4, 2, [F.gif_gce(0, True),
                              F.gif_imagen(4, 2, b"\x00\x01" * 4)])
        self.assertGreater(len(entero), 40)
        for corte in range(13, len(entero) + 1):
            p = self.escribe("cortado%d.gif" % corte, entero[:corte])
            with open(p, "rb") as fh:
                d = V._gif(fh)
            self.assertIn("n_imagenes", d, "corte %d" % corte)
            self.assertLessEqual(d["n_imagenes"], 1, "corte %d" % corte)


class TruncadosGifDefecto(Discriminada):
    """DEFECTO ARREGLADO en `fix/verificador` — se conserva el caso minimo.

    `_gif` sobrevivia a los 32 cortes; **`_gif_bloques` NO**, y el que lo llama
    —`_alfa_min_gif`— iteraba el generador FUERA de su `try`. Dos lectores del
    mismo formato, en el mismo fichero, con dos disciplinas distintas.

    Lo que salvaba al producto era el `except` de `alfa_minimo`, dos capas mas
    arriba, que ya atrapa `struct.error` e `IndexError`. **Asi que no era un
    fallo de superficie: era una perdida de MOTIVO.** `_alfa_min_gif` esta
    escrito para explicar por que no puede («no es un GIF», «GIF sin bloques de
    imagen», «LZW del fotograma 1 ilegible: ...»), y en este camino el motivo
    que llegaba al contrato era el volcado de la excepcion. En este proyecto el
    mensaje es parte del contrato, no decoracion.

    Ahora `_gif_bloques` para donde se le acaban los datos, igual que `_gif`, y
    `_alfa_min_gif` envuelve TAMBIEN la iteracion del generador. Las tres capas
    se siguen midiendo por separado, que es lo que hace util este caso.
    """

    def test_gif_bloques_sobrevive_a_los_mismos_cortes_que_gif(self):
        entero = F.gif(4, 2, [F.gif_gce(0, True),
                              F.gif_imagen(4, 2, b"\x00\x01" * 4)])
        revientan = []
        for corte in range(13, len(entero) + 1):
            try:
                list(V._gif_bloques(entero[:corte]))
            except (struct.error, IndexError) as e:
                revientan.append((corte, type(e).__name__))
        self.assertEqual(revientan, [])
        # ...y `_gif`, sobre EXACTAMENTE los mismos cortes, tampoco lanza uno
        for corte in range(13, len(entero) + 1):
            p = self.escribe("cmp%d.gif" % corte, entero[:corte])
            with open(p, "rb") as fh:
                self.assertIn("n_imagenes", V._gif(fh), "corte %d" % corte)

    def test_el_corte_que_reventaba_ahora_da_un_MOTIVO(self):
        """El corte que dejaba el descriptor de imagen a medias (0x2C presente,
        los 8 bytes de geometria no) reventaba en el `unpack_from`. Ahora
        `_gif_bloques` no emite ese bloque y `_alfa_min_gif` contesta con una
        de sus frases, no con el volcado de una excepcion."""
        entero = F.gif(4, 2, [F.gif_gce(0, True),
                              F.gif_imagen(4, 2, b"\x00\x01" * 4)])
        i = entero.index(b"\x2c", 13)
        p = self.escribe("truncado.gif", entero[:i + 4])
        r = V._alfa_min_gif(p)
        self.assertFalse(r["evaluable"])
        self.assertEqual(r["motivo"], "GIF sin bloques de imagen")

    def test_y_el_despachador_publico_publica_ese_mismo_motivo(self):
        """La red de `alfa_minimo` sigue estando; lo que cambia es que ya no
        hace falta que la use, asi que el motivo que llega al contrato es una
        frase escrita y no un `struct.error`."""
        entero = F.gif(4, 2, [F.gif_gce(0, True),
                              F.gif_imagen(4, 2, b"\x00\x01" * 4)])
        i = entero.index(b"\x2c", 13)
        r = V.alfa_minimo(self.escribe("truncado2.gif", entero[:i + 4]))
        self.assertFalse(r["evaluable"])
        self.assertIsNone(r["alfa_min"])
        self.assertIsNone(r["alfa_no_trivial"])
        self.assertEqual(r["motivo"], "GIF sin bloques de imagen")

    def test_ningun_corte_deja_escapar_una_excepcion_por_alfa_min_gif(self):
        """La prueba ancha: los 32 cortes por la via de `_alfa_min_gif`, que es
        donde vivia el agujero (iteraba el generador fuera de su `try`)."""
        entero = F.gif(4, 2, [F.gif_gce(0, True),
                              F.gif_imagen(4, 2, b"\x00\x01" * 4)])
        for corte in range(13, len(entero) + 1):
            p = self.escribe("ancho%d.gif" % corte, entero[:corte])
            with self.subTest(corte=corte):
                r = V._alfa_min_gif(p)       # no lanza: eso es la asercion
                if not r["evaluable"]:
                    # y si no puede, lo dice con una de sus frases
                    self.assertTrue(
                        any(f in r["motivo"] for f in
                            ("no es un GIF", "GIF sin bloques de imagen",
                             "LZW del fotograma 1 ilegible",
                             "bloques del GIF ilegibles")),
                        r["motivo"])


# ===========================================================================
# 7. `_gif_bloques`
# ===========================================================================

class BloquesGif(Discriminada):

    def _c_bloques(self, mod):
        piezas = [
            F.gif_ext_aplicacion(),                       # 0x21, NO es GCE
            F.gif_gce(5, True, demora=7),
            F.gif_imagen(4, 2, b"\x00" * 8, mcs=2, lct_bits=3, izq=1, arr=2),
            F.gif_gce(0, False),
            F.gif_imagen(2, 2, b"\x01" * 4, mcs=2),
        ]
        datos = F.gif(8, 6, piezas, gct_bits=2)
        vistos = list(mod._gif_bloques(datos))
        tipos = [t for t, _ in vistos]
        self.assertEqual(tipos, ["gce", "img", "gce", "img"],
                         "la extension NETSCAPE no es un GCE y no se emite")
        self.assertEqual(vistos[0][1], {"transparente": 1, "indice": 5})
        img = vistos[1][1]
        self.assertEqual((img["izq"], img["arr"]), (1, 2))
        self.assertEqual((img["ancho"], img["alto"]), (4, 2))
        self.assertEqual(img["local"], 8, "tabla local de 8 colores")
        self.assertEqual(img["mcs"], 2)
        self.assertTrue(mod._lzw_gif_usa(img["datos"], 2, 0, 10 ** 9))
        self.assertEqual(vistos[2][1], {"transparente": 0, "indice": 0})
        self.assertEqual(vistos[3][1]["local"], 0)

    def test_bloques(self):
        self._c_bloques(V)

    def test_bloques_discrimina(self):
        # Saltar la tabla local con el numero de ENTRADAS en vez de con los
        # bytes que ocupa: los datos LZW se leen desplazados.
        self.discrimina(self._c_bloques,
                        ("            i += 3 * n_local",
                         "            i += n_local"))

    def test_lo_que_NO_es_un_gif_no_produce_bloques(self):
        self.assertEqual(list(V._gif_bloques(b"")), [])
        self.assertEqual(list(V._gif_bloques(b"GIF")), [])
        self.assertEqual(list(V._gif_bloques(b"PNG89a" + b"\x00" * 20)), [])

    def test_un_byte_inesperado_corta_el_barrido(self):
        """Un byte que no es 0x21, 0x2C ni 0x3B para el recorrido en seco.

        Es la defensa contra un fichero hostil: sin ella el barrido interpreta
        basura como descriptores y avanza a saltos arbitrarios.
        """
        datos = F.gif_cabecera(4, 2, 1) + b"\x99" + \
            F.gif_imagen(4, 2, b"\x00" * 8) + F.GIF_FIN
        self.assertEqual(list(V._gif_bloques(datos)), [])

    def test_un_gce_corto_no_se_emite(self):
        """Un GCE cuyo sub-bloque no llega a 4 bytes se salta sin lanzar."""
        corto = b"\x21\xf9\x02\x01\x00\x00"
        datos = F.gif_cabecera(4, 2, 1) + corto + \
            F.gif_imagen(4, 2, b"\x00" * 8) + F.GIF_FIN
        tipos = [t for t, _ in V._gif_bloques(datos)]
        self.assertEqual(tipos, ["img"])

    def test_el_trailer_para_el_barrido(self):
        datos = F.gif_cabecera(4, 2, 1) + F.gif_imagen(4, 2, b"\x00" * 8) + \
            F.GIF_FIN + F.gif_imagen(4, 2, b"\x01" * 8)
        self.assertEqual([t for t, _ in V._gif_bloques(datos)], ["img"])


# ===========================================================================
# 8. `_alfa_min_gif`
# ===========================================================================

class AlfaGif(Discriminada):

    def _c_declarado_y_usado(self, mod):
        """El GCE DECLARA un indice transparente; que se USE es otra cosa.

        Es la trampa 1 en el formato donde mas duele: la version anterior de
        este lector devolvia «no evaluable» con la sola declaracion, y un GIF
        opaco que declara el indice 0 se contaba como transparente.
        """
        usado = F.gif(4, 2, [F.gif_gce(3, True),
                             F.gif_imagen(4, 2, bytes([0, 1, 2, 3] * 2),
                                          mcs=2)])
        r = mod._alfa_min_gif(self.escribe("usado.gif", usado))
        self.assertTrue(r["evaluable"])
        self.assertTrue(r["tiene_alfa"])
        self.assertEqual(r["alfa_min"], 0.0)
        self.assertEqual(r["primer_transparente"], (0, 0))
        self.assertIn("indice transparente 3", r["via"])

        no_usado = F.gif(4, 2, [F.gif_gce(3, True),
                                F.gif_imagen(4, 2, bytes([0, 1, 2, 0] * 2),
                                             mcs=2)])
        r = mod._alfa_min_gif(self.escribe("nousado.gif", no_usado))
        self.assertTrue(r["evaluable"])
        self.assertFalse(r["tiene_alfa"],
                         "declarado y NO usado: el GIF es opaco de verdad")
        self.assertEqual(r["alfa_min"], 1.0)
        self.assertIsNone(r["primer_transparente"])

        # Y el caso que separa «hay GCE» de «el GCE DECLARA transparencia»: un
        # GCE con la bandera a 0 cuyo indice SI aparece en la imagen. Mirar
        # solo si hay GCE lo daria por transparente.
        bandera_0 = F.gif(4, 2, [F.gif_gce(3, False),
                                 F.gif_imagen(4, 2, bytes([0, 1, 2, 3] * 2),
                                              mcs=2)])
        r = mod._alfa_min_gif(self.escribe("bandera0.gif", bandera_0))
        self.assertTrue(r["evaluable"])
        self.assertFalse(r["tiene_alfa"],
                         "la bandera de transparencia del GCE esta a 0")
        self.assertEqual(r["alfa_min"], 1.0)
        self.assertEqual(r["via"], "bloque de control grafico")

    def test_declarado_y_usado(self):
        self._c_declarado_y_usado(V)

    def test_declarado_y_usado_discrimina(self):
        self.discrimina(self._c_declarado_y_usado,
                        ("        if not (gce and gce[\"transparente\"]):",
                         "        if not gce:"))

    def _c_lienzo(self, mod):
        """Un fotograma que no cubre el lienzo deja borde sin pintar, y eso SI
        es transparencia aunque no haya GCE. Dos caminos distintos segun haya
        GCE o no, y los dos tienen que responder 0.0."""
        sin_gce = F.gif(8, 6, [F.gif_imagen(4, 2, b"\x00" * 8, mcs=2)])
        r = mod._alfa_min_gif(self.escribe("borde.gif", sin_gce))
        self.assertTrue(r["tiene_alfa"])
        self.assertEqual(r["alfa_min"], 0.0)
        self.assertIn("no cubre el lienzo", r["via"])

        # con GCE cuyo indice NO se usa, pero el fotograma tampoco cubre
        con_gce = F.gif(8, 6, [F.gif_gce(3, True),
                               F.gif_imagen(4, 2, b"\x00" * 8, mcs=2)])
        r = mod._alfa_min_gif(self.escribe("borde2.gif", con_gce))
        self.assertEqual(r["alfa_min"], 0.0)
        self.assertIn("ademas no cubre el lienzo", r["via"])

        # y el que SI cubre y no declara nada es opaco
        cubre = F.gif(4, 2, [F.gif_imagen(4, 2, b"\x00" * 8, mcs=2)])
        r = mod._alfa_min_gif(self.escribe("cubre.gif", cubre))
        self.assertFalse(r["tiene_alfa"])
        self.assertEqual(r["alfa_min"], 1.0)

    def test_lienzo(self):
        self._c_lienzo(V)

    def test_lienzo_discrimina(self):
        self.discrimina(self._c_lienzo,
                        ('            if info["ancho"] < lan or info["alto"] < lal:\n'
                         '                r.update({"tiene_alfa": True, "alfa_min": 0.0,',
                         '            if False:\n'
                         '                r.update({"tiene_alfa": True, "alfa_min": 0.0,'))

    def _c_animado(self, mod):
        """En un GIF animado, el indice transparente de los fotogramas 2..n es
        CODIFICACION DIFERENCIAL («no repintes este pixel»), no transparencia
        visible. Se evalua el fotograma 1 y se anota el resto."""
        datos = F.gif(4, 2, [
            F.gif_gce(0, False),
            F.gif_imagen(4, 2, bytes([1, 2, 3, 1] * 2), mcs=2),
            F.gif_gce(0, True),
            F.gif_imagen(4, 2, bytes([0] * 8), mcs=2),
        ])
        r = mod._alfa_min_gif(self.escribe("anim.gif", datos))
        self.assertTrue(r["evaluable"])
        self.assertFalse(r["tiene_alfa"])
        self.assertEqual(r["alfa_min"], 1.0)
        self.assertEqual(r["n_imagenes_min"], 1)
        self.assertIn("codificacion diferencial", r.get("nota", ""))

    def test_animado(self):
        self._c_animado(V)

    def test_animado_discrimina(self):
        self.discrimina(self._c_animado,
                        ('            if n_img >= 1 and info["transparente"]:\n'
                         '                declara_despues = True',
                         '            if n_img >= 99 and info["transparente"]:\n'
                         '                declara_despues = True'))

    def test_no_evaluables(self):
        """Los dos «no puedo»: no es un GIF, y un GIF sin bloques de imagen."""
        r = V._alfa_min_gif(self.escribe("no.gif", b"PNG89a" + b"\x00" * 20))
        self.assertFalse(r["evaluable"])
        self.assertIsNone(r["tiene_alfa"])
        self.assertEqual(r["motivo"], "no es un GIF")

        r = V._alfa_min_gif(self.escribe("corto.gif", b"GIF89a"))
        self.assertFalse(r["evaluable"])
        self.assertEqual(r["motivo"], "no es un GIF")

        vacio = F.gif(4, 2, [F.gif_gce(0, True)])
        r = V._alfa_min_gif(self.escribe("vacio.gif", vacio))
        self.assertFalse(r["evaluable"])
        self.assertEqual(r["motivo"], "GIF sin bloques de imagen")

    def test_testigo_de_imagemagick(self):
        """Un GIF con transparencia REAL escrito por ImageMagick.

        Los constructores de `fixtures_cob_tiffgif` emiten el LZW con un
        codificador propio; este fichero lo emitio otro programa. Si los dos
        dialectos no coincidieran, aqui saldria `alfa_min = 1.0` sin un solo
        error por pantalla, que es justo el fallo que preocupa.
        """
        b = F.testigo("gif_transparente")
        self.assertEqual(hashlib.sha256(b).hexdigest(),
                         F.SHA256_TESTIGOS["gif_transparente"])
        p = self.escribe("magick.gif", b)
        r = V.alfa_minimo(p)
        self.assertEqual(r["formato"], "gif")
        self.assertTrue(r["tiene_alfa"])
        self.assertEqual(r["alfa_min"], 0.0)
        self.assertTrue(r["alfa_no_trivial"])
        with open(p, "rb") as fh:
            d = V._gif(fh)
        self.assertEqual((d["ancho"], d["alto"]), (8, 4))
        self.assertEqual(d["n_imagenes"], 1)


# ===========================================================================
# 9. El propio arnes: si el mutante no muerde, no hay control positivo
# ===========================================================================

class ElArnes(unittest.TestCase):

    def test_el_mutante_exige_ancla_unica(self):
        """Trampa 119 en su forma de A/B: si el texto no esta anclado, la
        mutacion no se aplica donde uno cree y el rojo no significa nada."""
        with self.assertRaises(AssertionError):
            mutar(("    return out", "    return None"))   # muchas veces
        with self.assertRaises(AssertionError):
            mutar(("esto no aparece en verificador.py", "x"))

    def test_el_mutante_es_otra_cosa_y_compila(self):
        mod = mutar(("    while desp and n_img < 64:",
                     "    while desp and n_img < 128:"))
        self.assertIsNot(mod, V)
        self.assertIsNot(mod._tiff, V._tiff)
        # el mutante es un modulo COMPLETO: las tablas de nivel superior estan
        self.assertEqual(mod._TIFF_COMPR_OK, V._TIFF_COMPR_OK)
        self.assertEqual(mod._TIFF_ETIQ_ALFA, V._TIFF_ETIQ_ALFA)

    def test_el_mutante_en_memoria_equivale_a_editar_el_FICHERO(self):
        """La pregunta que este arnes tiene que contestar con una MEDIDA.

        El procedimiento literal del carril es «rompe una linea de
        `filex/verificador.py`, comprueba que la prueba se pone roja y deshaz
        con `git checkout --`». Aqui no se toca `filex/` —eso caducaria las 232
        aristas selladas—, se `exec`uta la fuente mutada en un modulo nuevo. Que
        las dos cosas sean lo mismo es una AFIRMACION, y las afirmaciones de
        este repositorio se miden: se escribe la misma fuente mutada en un
        fichero de verdad, se IMPORTA como cualquier modulo, y se comprueba que
        los dos caminos dan el mismo resultado sobre el mismo TIFF.

        (Y de paso queda escrito por que no se usa `git stash push <fichero>`:
        sobre un fichero ya commiteado no hace nada, devuelve 0 y sin aviso, y
        el A/B sale verde comparando el codigo consigo mismo — trampa 119.)
        """
        import importlib.util

        cambio = MUT_CARRIL
        en_memoria = mutar(cambio)
        fuente = _FUENTE.replace(cambio[0], cambio[1])
        self.assertNotEqual(fuente, _FUENTE)
        tmp = tempfile.mkdtemp(prefix="filex-cob-tg-eq-")
        try:
            ruta = os.path.join(tmp, "verificador_mutado_en_disco.py")
            with open(ruta, "w", encoding="utf-8", newline="") as fh:
                fh.write(fuente)
            spec = importlib.util.spec_from_file_location("vmd", ruta)
            en_disco = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(en_disco)

            # Alfa enteramente opaco: el codigo sano da 1.0 y el que lee el
            # carril del ROJO da otra cosa, asi que la diferencia se ve.
            px = F.rgba_degradado(6, 5, 8, alfa=lambda x, y: 255)
            tif = os.path.join(tmp, "eq.tiff")
            with open(tif, "wb") as fh:
                fh.write(F.tiff_muestras(px, 6, 5, filas_por_banda=2))
            sano = V._alfa_min_tiff(tif, True)
            a = en_memoria._alfa_min_tiff(tif, True)
            b = en_disco._alfa_min_tiff(tif, True)
            self.assertEqual(a, b, "exec en memoria e import desde fichero "
                                   "tienen que dar EXACTAMENTE lo mismo")
            self.assertNotEqual(a["alfa_min"], sano["alfa_min"],
                                "y los dos tienen que diferir del codigo sano, "
                                "o la mutacion no estaba mordiendo")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_se_ha_tocado_verificador_en_el_disco(self):
        """El mutante vive en memoria. Si esta prueba falla, alguien escribio
        en `filex/` y ha caducado las 232 aristas selladas (trampa 32)."""
        with open(V.__file__, "r", encoding="utf-8") as fh:
            self.assertEqual(fh.read(), _FUENTE)


if __name__ == "__main__":
    unittest.main(verbosity=2)

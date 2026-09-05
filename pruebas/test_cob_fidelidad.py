"""Cobertura de las reglas de FIDELIDAD de `filex/verificador.py`.

Carril `cob/fidelidad`. Objetivo: las seis funciones de fidelidad y su ayudante
`_num`, que en la linea base sumaban **357 sentencias sin ejecutar** sobre 517
pruebas (`bench/cobertura-fidelidad.md`).

Tres decisiones que hay que declarar, porque cambian lo que estas pruebas
garantizan:

1. **Los `sonda`/`sonda_ent` se construyen a mano.** Las seis funciones reciben
   los diccionarios de la sonda como PARAMETRO; sondear de verdad mediria
   `sondear()`, que ya esta cubierto por `test_contrato_v.py`, y ataria cada
   celda a un fichero del corpus. A mano, cada rama se ataca por su condicion.

2. **Los motores externos se usan de VERDAD donde el camino es el normal**
   (`magick`, `gs`, `ffmpeg`/`ffprobe` sobre entradas diminutas generadas en el
   desechable), y se sustituyen por un doble **solo** en las ramas de error del
   ayudante —las que solo se alcanzan cuando `magick`/`gs`/`ffprobe` no devuelve
   nada util—. Cada prueba dice en su nombre cual de las dos cosas hace: las que
   usan doble llevan `_con_doble`.

3. **Los guardas miran el TAMAnO del activo, no su existencia** (trampa 107): un
   puntero de Git LFS sin descargar existe y pesa 130 B, asi que
   `os.path.exists` deja pasar el fichero y el motor revienta despues.

Ninguna prueba publica un tiempo absoluto (CLAUDE.md §3): todos los veredictos
son deterministas.
"""
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filex import verificador as V  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(RAIZ, "corpus")


# ---------------------------------------------------------------------------
# Guardas de entorno. Trampa 107: el tamano, no la existencia.
# ---------------------------------------------------------------------------

def _activo(*partes):
    """Ruta del corpus si el fichero esta DESCARGADO (no es un puntero LFS).

    El guarda mira la CABECERA, no el tamano: un puntero de LFS pesa ~130 B,
    pero `corpus/imagen/alpha.png` pesa 2 780 y un umbral de tamano lo habria
    saltado siempre. Y `os.path.exists` no vale (trampa 107): el puntero
    existe.
    """
    r = os.path.join(CORPUS, *partes)
    try:
        with open(r, "rb") as fh:
            cab = fh.read(48)
    except OSError:
        return None
    return None if cab.startswith(b"version https://git-lfs") else r


def _hay(binario, *args):
    """El binario existe Y responde. `shutil.which` solo dice lo primero."""
    if shutil.which(binario) is None:
        return False
    try:
        p = subprocess.run([binario] + list(args), capture_output=True,
                           timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return p.returncode == 0


HAY_MAGICK = _hay("magick", "-version")
HAY_GS = _hay("gswin64c", "-version") or _hay("gs", "--version")
HAY_FFMPEG = _hay("ffmpeg", "-version") and _hay("ffprobe", "-version")


# ---------------------------------------------------------------------------
# Constructores de ficheros. Todo en proceso: ni un motor externo.
# ---------------------------------------------------------------------------

def _trozo(tipo, datos):
    return (struct.pack(">I", len(datos)) + tipo + datos
            + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF))


def _filtrar(filas, bpp, filtro):
    """Codifica las filas CRUDAS con el filtro PNG pedido (RFC 2083 §6)."""
    fuera = []
    previo = bytearray(len(filas[0])) if filas else bytearray()
    for cruda in filas:
        cruda = bytearray(cruda)
        n = len(cruda)
        f = bytearray(n)
        for j in range(n):
            a = cruda[j - bpp] if j >= bpp else 0
            b = previo[j]
            c = previo[j - bpp] if j >= bpp else 0
            if filtro == 0:
                f[j] = cruda[j]
            elif filtro == 1:
                f[j] = (cruda[j] - a) & 255
            elif filtro == 2:
                f[j] = (cruda[j] - b) & 255
            elif filtro == 3:
                f[j] = (cruda[j] - ((a + b) >> 1)) & 255
            else:
                f[j] = (cruda[j] - V._paeth(a, b, c)) & 255
        fuera.append(bytes([filtro]) + bytes(f))
        previo = cruda
    return b"".join(fuera)


def escribe_png(ruta, an, al, bd, ct, filas, paleta=None, entrelazado=0,
                con_idat=True, filtro=0, bpp=1):
    """PNG minimo pero VALIDO (CRC incluido), en proceso.

    `filas` son las filas CRUDAS ya empaquetadas en bytes; `con_idat=False`
    produce el PNG sin datos de pixel que exige la rama 'sin IDAT'.
    """
    d = b"\x89PNG\r\n\x1a\n"
    d += _trozo(b"IHDR", struct.pack(">IIBBBBB", an, al, bd, ct, 0, 0,
                                     entrelazado))
    if paleta is not None:
        d += _trozo(b"PLTE", b"".join(bytes(c) for c in paleta))
    if con_idat:
        d += _trozo(b"IDAT", zlib.compress(_filtrar(filas, bpp, filtro)))
    d += _trozo(b"IEND", b"")
    with open(ruta, "wb") as fh:
        fh.write(d)
    return ruta


def png_gris(ruta, an, al, pintar=None, fondo=255, tinta=0, filtro=0):
    """PNG gris de 8 bits. `pintar(x, y)` decide que pixeles llevan tinta.

    `tinta` es explicita a proposito: con la tinta clavada en 0 no se puede
    construir el caso de fondo NEGRO, que es justo el que demuestra que la
    regla mide contra el fondo real y no contra el blanco.
    """
    filas = []
    for y in range(al):
        filas.append(bytes(tinta if (pintar and pintar(x, y)) else fondo
                           for x in range(an)))
    return escribe_png(ruta, an, al, 8, 0, filas, filtro=filtro, bpp=1)


def escribe_gif(ruta, paleta):
    """Cabecera GIF con tabla de color global. `_paleta_gif` lee 13 + 3n bytes;
    con eso basta para V9 y no hace falta un GIF completo."""
    n = len(paleta)
    bits = max(1, (n - 1).bit_length()) - 1 if n > 2 else 0
    while 2 ** (bits + 1) < n:
        bits += 1
    cab = b"GIF89a" + struct.pack("<HH", 4, 4) + bytes([0x80 | bits, 0, 0])
    cuerpo = b"".join(bytes(c) for c in paleta)
    cuerpo += b"\x00" * (3 * (2 ** (bits + 1)) - len(cuerpo))
    with open(ruta, "wb") as fh:
        fh.write(cab + cuerpo + b";")
    return ruta


SVG_CAB = '<svg xmlns="http://www.w3.org/2000/svg" %s>'


def escribe_svg(ruta, cuerpo, atributos='viewBox="0 0 100 100"'):
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write((SVG_CAB % atributos) + cuerpo + "</svg>")
    return ruta


def escribe_pdf(ruta, texto=None, fuente=12):
    """PDF de una pagina, con tabla xref correcta. Si `texto` es None la pagina
    va vacia (sin capa de texto), que es el caso que exige P5."""
    objs = []
    objs.append(b"<</Type/Catalog/Pages 2 0 R>>")
    objs.append(b"<</Type/Pages/Kids[3 0 R]/Count 1>>")
    objs.append(b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 200]"
                b"/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>")
    objs.append(b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>")
    if texto is None:
        flujo = b""
    else:
        lineas = []
        y = 170
        for tr in texto.split("\n"):
            tr = tr.replace("\\", "").replace("(", "").replace(")", "")
            lineas.append(b"BT /F1 %d Tf 20 %d Td (%s) Tj ET"
                          % (fuente, y, tr.encode("latin-1", "replace")))
            y -= fuente + 4
        flujo = b"\n".join(lineas)
    objs.append(b"<</Length %d>>stream\n%s\nendstream" % (len(flujo), flujo))

    salida = bytearray(b"%PDF-1.4\n")
    desplaz = []
    for i, cuerpo in enumerate(objs, 1):
        desplaz.append(len(salida))
        salida += b"%d 0 obj\n" % i + cuerpo + b"\nendobj\n"
    pos_xref = len(salida)
    salida += b"xref\n0 %d\n" % (len(objs) + 1)
    salida += b"0000000000 65535 f \n"
    for d in desplaz:
        salida += b"%010d 00000 n \n" % d
    salida += (b"trailer\n<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF\n"
               % (len(objs) + 1, pos_xref))
    with open(ruta, "wb") as fh:
        fh.write(bytes(salida))
    return ruta


class Desechable(unittest.TestCase):
    """Directorio de trabajo desechable por clase (R18)."""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="filex-cob-fid-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def r(self, nombre):
        return os.path.join(self.dir, nombre)


# ===========================================================================
# _num  --  11 sentencias, el cuerpo entero sin ejecutar en la linea base
# ===========================================================================

class Num(unittest.TestCase):

    def test_None_devuelve_el_por_defecto(self):
        self.assertEqual(V._num(None), 0.0)
        self.assertEqual(V._num(None, 7.5), 7.5)

    def test_quita_las_siete_unidades_de_longitud(self):
        # La lista del codigo, entera: si alguien quita una, esto lo dice.
        for u, v in (("px", 12), ("pt", 13), ("mm", 14), ("cm", 15),
                     ("in", 16), ("%", 17), ("em", 18)):
            with self.subTest(unidad=u):
                self.assertEqual(V._num("%d%s" % (v, u)), float(v))

    def test_solo_quita_la_PRIMERA_unidad_que_encaja(self):
        # El `break` importa: sin el, "1pxpx" seguiria pelandose.
        self.assertEqual(V._num("1pxpx"), 0.0)

    def test_espacios_alrededor(self):
        self.assertEqual(V._num("  3.5  "), 3.5)

    def test_lo_que_no_es_numero_cae_al_por_defecto(self):
        self.assertEqual(V._num("auto"), 0.0)
        self.assertEqual(V._num("auto", -1.0), -1.0)
        self.assertEqual(V._num("", 42.0), 42.0)


# ===========================================================================
# svg_textos  --  44 sentencias sin ejecutar
# ===========================================================================

class SvgTextos(Desechable):

    def test_lo_que_no_es_XML_no_es_evaluable_y_dice_por_que(self):
        p = self.r("basura.svg")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("<svg<<<no cierra")
        r = V.svg_textos(p)
        self.assertFalse(r["evaluable"])
        self.assertIn("no es un XML analizable", r["motivo"])

    def test_un_XML_cuya_raiz_no_es_svg(self):
        p = self.r("raiz.xml")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("<html><body/></html>")
        r = V.svg_textos(p)
        self.assertFalse(r["evaluable"])
        self.assertEqual(r["motivo"], "la raiz no es <svg>")

    def test_sin_viewBox_ni_width_ni_height(self):
        p = escribe_svg(self.r("sin_geom.svg"), "<text x='1' y='1'>a</text>",
                        atributos="")
        r = V.svg_textos(p)
        self.assertFalse(r["evaluable"])
        self.assertIn("sin viewBox", r["motivo"])

    def test_width_y_height_con_unidades_cuando_no_hay_viewBox(self):
        p = escribe_svg(self.r("wh.svg"),
                        '<text x="10" y="50" font-size="20">HOLA</text>',
                        atributos='width="100px" height="100px"')
        r = V.svg_textos(p)
        self.assertTrue(r["evaluable"])
        self.assertEqual((r["ancho_usuario"], r["alto_usuario"]), (100.0, 100.0))
        self.assertEqual(r["n_textos"], 1)

    def test_el_viewBox_desplaza_el_origen(self):
        # vx/vy != 0: la caja se da en coordenadas RELATIVAS al viewBox.
        p = escribe_svg(self.r("vb.svg"),
                        '<text x="30" y="70" font-size="20">HOLA</text>',
                        atributos='viewBox="20,20,100,100"')
        r = V.svg_textos(p)
        self.assertTrue(r["evaluable"])
        # x0 = 30 - 20 = 10 ; y0 = 70 - 15 - 20 = 35
        self.assertEqual(r["cajas"][0]["caja"][:2], [10.0, 35.0])

    def test_los_tres_anclajes_mueven_la_caja(self):
        cuerpo = ('<text x="50" y="50" font-size="10" text-anchor="start">AB</text>'
                  '<text x="50" y="50" font-size="10" text-anchor="middle">AB</text>'
                  '<text x="50" y="50" font-size="10" text-anchor="end">AB</text>')
        r = V.svg_textos(escribe_svg(self.r("anclas.svg"), cuerpo))
        self.assertEqual(r["n_textos"], 3)
        an = 0.50 * 10 * 2          # avance medio del codigo: 10.0
        x0 = [c["caja"][0] for c in r["cajas"]]
        self.assertEqual(x0, [50.0, 50.0 - an / 2, 50.0 - an])

    def test_el_font_size_puede_venir_dentro_de_style(self):
        # _estilo: SVG admite atributo y propiedad. Con 40 la banda vertical
        # sube a 0,75*40 = 30 sobre la linea base.
        p = escribe_svg(self.r("estilo.svg"),
                        '<text x="10" y="50" style="fill:red;font-size:40">HOLA</text>')
        r = V.svg_textos(p)
        self.assertEqual(r["cajas"][0]["font_size"], 40.0)
        self.assertEqual(r["cajas"][0]["caja"][1], 50 - 0.75 * 40)

    def test_el_text_anchor_tambien_vale_dentro_de_style(self):
        p = escribe_svg(self.r("estilo2.svg"),
                        '<text x="50" y="50" font-size="10" '
                        'style="text-anchor:end">AB</text>')
        r = V.svg_textos(p)
        self.assertEqual(r["cajas"][0]["caja"][0], 40.0)

    def test_un_text_vacio_o_de_solo_espacios_no_cuenta(self):
        cuerpo = ('<text x="10" y="50"></text>'
                  '<text x="10" y="60">   </text>'
                  '<text x="10" y="70" font-size="10">SI</text>')
        r = V.svg_textos(escribe_svg(self.r("vacios.svg"), cuerpo))
        self.assertEqual(r["n_textos"], 1)
        self.assertEqual(r["cajas"][0]["texto"], "SI")

    def test_el_texto_de_los_hijos_cuenta_itertext(self):
        p = escribe_svg(self.r("tspan.svg"),
                        '<text x="10" y="50" font-size="10">'
                        '<tspan>HO</tspan><tspan>LA</tspan></text>')
        r = V.svg_textos(p)
        self.assertEqual(r["cajas"][0]["texto"], "HOLA")

    def test_una_caja_degenerada_se_descarta_en_vez_de_publicarse(self):
        # y = 0 con font-size 10: la banda va de -7,5 a +2 y se recorta a
        # (0, 2); pero x = 100 la deja fuera por la derecha -> descartada.
        cuerpo = ('<text x="100" y="10" font-size="10">FUERA</text>'
                  '<text x="10" y="50" font-size="10">DENTRO</text>')
        r = V.svg_textos(escribe_svg(self.r("degenerada.svg"), cuerpo))
        self.assertEqual(r["n_textos"], 1)
        self.assertEqual(r["cajas"][0]["texto"], "DENTRO")

    def test_el_avance_se_topa_a_24_caracteres(self):
        largo = "A" * 60
        r = V.svg_textos(escribe_svg(
            self.r("largo.svg"),
            '<text x="0" y="50" font-size="1">%s</text>' % largo))
        # n = min(60, 24) = 24 -> an = 0,5 * 1 * 24 = 12
        self.assertEqual(r["cajas"][0]["caja"][2], 12.0)
        self.assertEqual(len(r["cajas"][0]["texto"]), 40)   # recorte a 40

    def test_el_text_sin_espacio_de_nombres_tambien_se_ve(self):
        # El codigo acepta las dos formas: con y sin el {namespace}.
        p = self.r("sinns.svg")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write('<svg viewBox="0 0 100 100">'
                     '<text x="10" y="50" font-size="10">HOLA</text></svg>')
        r = V.svg_textos(p)
        self.assertEqual(r["n_textos"], 1)

    def test_el_fichero_que_no_existe_no_es_evaluable(self):
        r = V.svg_textos(self.r("no-esta.svg"))
        self.assertFalse(r["evaluable"])
        self.assertIn("no es un XML analizable", r["motivo"])

    # ---- transform: el defecto de §5.1 del informe -------------------------

    def test_un_translate_en_el_GRUPO_mueve_la_caja(self):
        # Control de la correccion: el MISMO texto colocado de las dos formas
        # tiene que dar la MISMA caja. Si no, la caja apunta a donde el
        # rasterizador no pinto nada y I9 grita TEXTO PERDIDO sin motivo.
        a = escribe_svg(self.r("t_abs.svg"),
                        '<text x="110" y="120" font-size="24">HOLA</text>',
                        atributos='viewBox="0 0 200 200"')
        b = escribe_svg(self.r("t_grp.svg"),
                        '<g transform="translate(100,100)">'
                        '<text x="10" y="20" font-size="24">HOLA</text></g>',
                        atributos='viewBox="0 0 200 200"')
        self.assertEqual(V.svg_textos(a)["cajas"][0]["caja"],
                         V.svg_textos(b)["cajas"][0]["caja"])

    def test_un_translate_en_el_PROPIO_text_tambien_cuenta(self):
        a = escribe_svg(self.r("t_prop_a.svg"),
                        '<text x="30" y="50" font-size="10">AB</text>')
        b = escribe_svg(self.r("t_prop_b.svg"),
                        '<text x="10" y="20" font-size="10" '
                        'transform="translate(20,30)">AB</text>')
        self.assertEqual(V.svg_textos(a)["cajas"][0]["caja"],
                         V.svg_textos(b)["cajas"][0]["caja"])

    def test_los_translate_anidados_se_SUMAN(self):
        a = escribe_svg(self.r("t_anid_a.svg"),
                        '<text x="35" y="55" font-size="10">AB</text>')
        b = escribe_svg(self.r("t_anid_b.svg"),
                        '<g transform="translate(20 30)">'
                        '<g transform="translate(5,5)">'
                        '<text x="10" y="20" font-size="10">AB</text>'
                        '</g></g>')
        self.assertEqual(V.svg_textos(a)["cajas"][0]["caja"],
                         V.svg_textos(b)["cajas"][0]["caja"])

    def test_un_translate_de_un_solo_argumento_no_mueve_la_y(self):
        a = escribe_svg(self.r("t_uno_a.svg"),
                        '<text x="30" y="20" font-size="10">AB</text>')
        b = escribe_svg(self.r("t_uno_b.svg"),
                        '<g transform="translate(20)">'
                        '<text x="10" y="20" font-size="10">AB</text></g>')
        self.assertEqual(V.svg_textos(a)["cajas"][0]["caja"],
                         V.svg_textos(b)["cajas"][0]["caja"])

    def test_dos_translate_en_el_MISMO_atributo(self):
        a = escribe_svg(self.r("t_dos_a.svg"),
                        '<text x="35" y="55" font-size="10">AB</text>')
        b = escribe_svg(self.r("t_dos_b.svg"),
                        '<g transform="translate(20,30) translate(5,5)">'
                        '<text x="10" y="20" font-size="10">AB</text></g>')
        self.assertEqual(V.svg_textos(a)["cajas"][0]["caja"],
                         V.svg_textos(b)["cajas"][0]["caja"])

    def test_lo_que_NO_es_traslacion_se_declara_NO_MEDIBLE_no_se_inventa(self):
        for t in ("scale(2)", "rotate(45)", "matrix(1,0,0,1,10,10)",
                  "skewX(10)", "translate(1,2,3)", "translate()",
                  "translate(1,2"):
            with self.subTest(transform=t):
                p = escribe_svg(self.r("nomed.svg"),
                                '<g transform="%s">'
                                '<text x="10" y="50" font-size="10">AB</text>'
                                "</g>" % t)
                r = V.svg_textos(p)
                self.assertTrue(r["evaluable"])
                self.assertEqual(r["n_textos"], 0)
                self.assertEqual(r["cajas"], [])
                self.assertEqual(r["n_no_medibles"], 1)


# ===========================================================================
# png_tinta_cajas  --  71 sentencias sin ejecutar
# ===========================================================================

class PngTintaCajas(Desechable):

    def test_el_fichero_que_no_existe_da_el_error_del_sistema(self):
        r = V.png_tinta_cajas(self.r("no-esta.png"), [(0, 0, 1, 1)])
        self.assertFalse(r["evaluable"])
        self.assertTrue(r["motivo"])

    def test_lo_que_no_es_PNG_se_declara_fuera_de_la_regla(self):
        p = self.r("no.png")
        with open(p, "wb") as fh:
            fh.write(b"BM" + b"\x00" * 64)
        r = V.png_tinta_cajas(p, [(0, 0, 1, 1)])
        self.assertFalse(r["evaluable"])
        self.assertIn("no es PNG", r["motivo"])

    def test_Adam7_se_declara_no_implementado_en_vez_de_inventar_un_numero(self):
        p = escribe_png(self.r("adam7.png"), 4, 4, 8, 0,
                        [b"\xff" * 4] * 4, entrelazado=1)
        r = V.png_tinta_cajas(p, [(0, 0, 4, 4)])
        self.assertFalse(r["evaluable"])
        self.assertIn("Adam7", r["motivo"])

    def test_un_PNG_sin_IDAT(self):
        p = escribe_png(self.r("sin_idat.png"), 4, 4, 8, 0, [], con_idat=False)
        r = V.png_tinta_cajas(p, [(0, 0, 4, 4)])
        self.assertFalse(r["evaluable"])
        self.assertEqual(r["motivo"], "sin IDAT")

    def test_un_color_type_fuera_de_la_tabla(self):
        p = escribe_png(self.r("ct5.png"), 4, 4, 8, 5, [b"\xff" * 4] * 4)
        r = V.png_tinta_cajas(p, [(0, 0, 4, 4)])
        self.assertFalse(r["evaluable"])
        self.assertIn("color type 5", r["motivo"])

    def test_una_profundidad_fuera_de_la_tabla(self):
        p = escribe_png(self.r("bd3.png"), 4, 4, 3, 0, [b"\xff" * 4] * 4)
        r = V.png_tinta_cajas(p, [(0, 0, 4, 4)])
        self.assertFalse(r["evaluable"])
        self.assertIn("profundidad 3", r["motivo"])

    def test_un_PNG_de_paleta_SIN_PLTE(self):
        p = escribe_png(self.r("sin_plte.png"), 4, 4, 8, 3, [b"\x00" * 4] * 4)
        r = V.png_tinta_cajas(p, [(0, 0, 4, 4)])
        self.assertFalse(r["evaluable"])
        self.assertIn("sin PLTE", r["motivo"])

    def test_sin_cajas_que_medir(self):
        p = png_gris(self.r("vacio.png"), 4, 4)
        r = V.png_tinta_cajas(p, [])
        self.assertFalse(r["evaluable"])
        self.assertEqual(r["motivo"], "sin cajas que medir")

    def test_un_byte_de_filtro_CORRUPTO_se_declara_no_evaluable_no_revienta(self):
        # DEFECTO ARREGLADO (informe §5.3): un filtro fuera de 0-4 hacia que
        # `_desfiltrar_fila` lanzara `ValueError` y la excepcion subiera hasta
        # `verificar_fidelidad`. Todas las demas malformaciones de esta funcion
        # se declaran con motivo; esta reventaba.
        crudo = b"".join(bytes([9]) + b"\xff" * 20 for _ in range(20))
        d = b"\x89PNG\r\n\x1a\n"
        d += _trozo(b"IHDR", struct.pack(">IIBBBBB", 20, 20, 8, 0, 0, 0, 0))
        d += _trozo(b"IDAT", zlib.compress(crudo))
        d += _trozo(b"IEND", b"")
        p = self.r("filtro_malo.png")
        with open(p, "wb") as fh:
            fh.write(d)
        r = V.png_tinta_cajas(p, [(0, 0, 20, 20)])
        self.assertFalse(r["evaluable"])
        self.assertIn("PNG corrupto", r["motivo"])
        self.assertIn("filtro PNG desconocido", r["motivo"])

    def test_gris_de_8_bits_cuenta_la_tinta_contra_el_fondo_REAL(self):
        # 20x20 blanco con un bloque negro de 6x6: 36 de 400 = 9,000 %.
        p = png_gris(self.r("bloque.png"), 20, 20,
                     pintar=lambda x, y: 2 <= x < 8 and 2 <= y < 8)
        r = V.png_tinta_cajas(p, [(0, 0, 20, 20)])
        self.assertTrue(r["evaluable"])
        c = r["cajas"][0]
        self.assertEqual(c["pixeles"], 400)
        self.assertEqual(c["fondo_lum"], 255)
        self.assertEqual(c["tinta_pct"], 9.0)
        self.assertEqual(r["tinta_max_pct"], 9.0)

    def test_el_fondo_es_el_mas_frecuente_no_el_blanco(self):
        # Invertido: negro de fondo, tinta blanca. El 9,000 % tiene que salir
        # IGUAL, que es la razon de ser de "contra el fondo real".
        p = png_gris(self.r("invertido.png"), 20, 20, fondo=0, tinta=255,
                     pintar=lambda x, y: 2 <= x < 8 and 2 <= y < 8)
        r = V.png_tinta_cajas(p, [(0, 0, 20, 20)])
        self.assertEqual(r["cajas"][0]["fondo_lum"], 0)
        self.assertEqual(r["cajas"][0]["tinta_pct"], 9.0)

    def test_los_cinco_filtros_de_fila_dan_el_MISMO_numero(self):
        # Control de identidad del decodificador: los mismos pixeles con los
        # cinco filtros de la RFC 2083 tienen que dar la misma tinta.
        vistos = []
        for f in range(5):
            p = png_gris(self.r("filtro%d.png" % f), 20, 20, filtro=f,
                         pintar=lambda x, y: 2 <= x < 8 and 2 <= y < 8)
            vistos.append(V.png_tinta_cajas(p, [(0, 0, 20, 20)])["cajas"][0])
        self.assertEqual([c["tinta_pct"] for c in vistos], [9.0] * 5)

    def test_la_caja_puede_venir_como_dict_o_como_tupla(self):
        p = png_gris(self.r("dict.png"), 20, 20,
                     pintar=lambda x, y: 2 <= x < 8 and 2 <= y < 8)
        a = V.png_tinta_cajas(p, [{"caja": [0, 0, 20, 20]}])
        b = V.png_tinta_cajas(p, [(0, 0, 20, 20)])
        self.assertEqual(a["cajas"], b["cajas"])

    def test_la_escala_convierte_coordenadas_de_usuario_en_pixeles(self):
        p = png_gris(self.r("escala.png"), 20, 20,
                     pintar=lambda x, y: 2 <= x < 8 and 2 <= y < 8)
        r = V.png_tinta_cajas(p, [(0, 0, 10, 10)], esc_x=2.0, esc_y=2.0)
        self.assertEqual(r["cajas"][0]["caja"], [0, 0, 20, 20])
        self.assertEqual(r["cajas"][0]["pixeles"], 400)

    def test_solo_lee_las_filas_que_hacen_falta(self):
        # La caja llega a la fila 5: el generador no debe recorrer las 20.
        p = png_gris(self.r("corta.png"), 20, 20)
        r = V.png_tinta_cajas(p, [(0, 0, 20, 5)])
        self.assertEqual(r["filas_leidas"], 5)

    def test_una_caja_sin_pixeles_declara_tinta_None_no_cero(self):
        # x1 <= x0 tras recortar: 0 pixeles. Decir 0 % seria decir "no hay
        # tinta", que es lo contrario de "no se pudo mirar".
        p = png_gris(self.r("fuera.png"), 20, 20)
        r = V.png_tinta_cajas(p, [(0, 0, 20, 3), (25, 0, 30, 3)])
        self.assertEqual(r["cajas"][1]["pixeles"], 0)
        self.assertIsNone(r["cajas"][1]["tinta_pct"])
        self.assertEqual(r["cajas"][0]["tinta_pct"], 0.0)

    def test_varias_cajas_y_el_maximo_es_el_maximo(self):
        p = png_gris(self.r("dos.png"), 20, 20,
                     pintar=lambda x, y: y < 10 and x < 2)
        r = V.png_tinta_cajas(p, [(0, 0, 20, 10), (0, 10, 20, 20)])
        self.assertEqual(r["cajas"][0]["tinta_pct"], 10.0)
        self.assertEqual(r["cajas"][1]["tinta_pct"], 0.0)
        self.assertEqual(r["tinta_max_pct"], 10.0)

    def test_RGB_de_8_bits_usa_la_luminancia_ponderada(self):
        # Verde puro (0,255,0) -> 149 ; blanco -> 255. |149-255| = 106 > 64.
        filas = []
        for y in range(20):
            f = bytearray()
            for x in range(20):
                f += (b"\x00\xff\x00" if (x < 2 and y < 10) else b"\xff\xff\xff")
            filas.append(bytes(f))
        p = escribe_png(self.r("rgb.png"), 20, 20, 8, 2, filas, bpp=3)
        r = V.png_tinta_cajas(p, [(0, 0, 20, 20)])
        self.assertEqual(r["cajas"][0]["fondo_lum"], 255)
        self.assertEqual(r["cajas"][0]["tinta_pct"], 5.0)

    def test_gris_con_alfa_ct4_lee_solo_el_canal_gris(self):
        filas = []
        for y in range(20):
            f = bytearray()
            for x in range(20):
                f += (b"\x00\xff" if (x < 2 and y < 10) else b"\xff\xff")
            filas.append(bytes(f))
        p = escribe_png(self.r("ga.png"), 20, 20, 8, 4, filas, bpp=2)
        r = V.png_tinta_cajas(p, [(0, 0, 20, 20)])
        self.assertEqual(r["cajas"][0]["tinta_pct"], 5.0)

    def test_RGBA_de_16_bits(self):
        filas = []
        for y in range(20):
            f = bytearray()
            for x in range(20):
                v = b"\x00\x00" if (x < 2 and y < 10) else b"\xff\xff"
                f += v * 3 + b"\xff\xff"
            filas.append(bytes(f))
        p = escribe_png(self.r("rgba16.png"), 20, 20, 16, 6, filas, bpp=8)
        r = V.png_tinta_cajas(p, [(0, 0, 20, 20)])
        self.assertEqual(r["cajas"][0]["tinta_pct"], 5.0)

    def test_gris_de_16_bits(self):
        filas = []
        for y in range(20):
            f = bytearray()
            for x in range(20):
                f += b"\x00\x00" if (x < 2 and y < 10) else b"\xff\xff"
            filas.append(bytes(f))
        p = escribe_png(self.r("g16.png"), 20, 20, 16, 0, filas, bpp=2)
        r = V.png_tinta_cajas(p, [(0, 0, 20, 20)])
        self.assertEqual(r["cajas"][0]["tinta_pct"], 5.0)

    def test_las_profundidades_de_1_2_y_4_bits(self):
        # Gris empaquetado: los 4 primeros pixeles de las 10 primeras filas a 0.
        for bd in (1, 2, 4):
            with self.subTest(bd=bd):
                por_byte = 8 // bd
                tam = (16 * bd + 7) // 8
                filas = []
                for y in range(20):
                    f = bytearray(b"\xff" * tam)
                    if y < 10:
                        for x in range(4):
                            b = x // por_byte
                            desp = 8 - bd * (x % por_byte + 1)
                            f[b] &= ~(((1 << bd) - 1) << desp) & 0xFF
                    filas.append(bytes(f))
                p = escribe_png(self.r("bd%d.png" % bd), 16, 20, bd, 0, filas)
                r = V.png_tinta_cajas(p, [(0, 0, 16, 20)])
                # 4 x 10 = 40 de 320
                self.assertEqual(r["cajas"][0]["tinta_pct"], 12.5)

    def test_paleta_de_8_bits_con_PLTE(self):
        pal = [(255, 255, 255), (0, 0, 0)]
        filas = [bytes(1 if (x < 2 and y < 10) else 0 for x in range(20))
                 for y in range(20)]
        p = escribe_png(self.r("pal8.png"), 20, 20, 8, 3, filas, paleta=pal)
        r = V.png_tinta_cajas(p, [(0, 0, 20, 20)])
        self.assertEqual(r["cajas"][0]["tinta_pct"], 5.0)

    def test_paleta_de_4_bits_con_PLTE(self):
        pal = [(255, 255, 255), (0, 0, 0)]
        filas = []
        for y in range(20):
            f = bytearray(b"\x00" * 10)
            for x in range(20):
                v = 1 if (x < 2 and y < 10) else 0
                if x % 2 == 0:
                    f[x // 2] |= v << 4
                else:
                    f[x // 2] |= v
            filas.append(bytes(f))
        p = escribe_png(self.r("pal4.png"), 20, 20, 4, 3, filas, paleta=pal)
        r = V.png_tinta_cajas(p, [(0, 0, 20, 20)])
        self.assertEqual(r["cajas"][0]["tinta_pct"], 5.0)

    def test_un_indice_de_paleta_fuera_de_la_tabla_no_revienta(self):
        pal = [(255, 255, 255)]           # un solo color; el indice 1 no existe
        filas = [bytes(1 if (x < 2 and y < 10) else 0 for x in range(20))
                 for y in range(20)]
        p = escribe_png(self.r("palcorta.png"), 20, 20, 8, 3, filas, paleta=pal)
        r = V.png_tinta_cajas(p, [(0, 0, 20, 20)])
        self.assertEqual(r["cajas"][0]["tinta_pct"], 5.0)   # cae a (0,0,0)

    def test_el_PLTE_detras_de_un_trozo_ajeno(self):
        # _leer_plte tiene que saltarse los trozos que no le tocan.
        pal = [(255, 255, 255), (0, 0, 0)]
        filas = [bytes(1 if (x < 2 and y < 10) else 0 for x in range(20))
                 for y in range(20)]
        d = b"\x89PNG\r\n\x1a\n"
        d += _trozo(b"IHDR", struct.pack(">IIBBBBB", 20, 20, 8, 3, 0, 0, 0))
        d += _trozo(b"gAMA", b"\x00\x01\x86\xa0")
        d += _trozo(b"PLTE", b"".join(bytes(c) for c in pal))
        d += _trozo(b"IDAT", zlib.compress(_filtrar(filas, 1, 0)))
        d += _trozo(b"IEND", b"")
        p = self.r("gama.png")
        with open(p, "wb") as fh:
            fh.write(d)
        r = V.png_tinta_cajas(p, [(0, 0, 20, 20)])
        self.assertEqual(r["cajas"][0]["tinta_pct"], 5.0)


# ===========================================================================
# fidelidad_vectorial  --  40 sentencias sin ejecutar. TODO en proceso.
# ===========================================================================

def _svg_con_texto(ruta, n=1):
    cuerpo = "".join('<text x="10" y="%d" font-size="20">HOLA</text>'
                     % (30 + 40 * i) for i in range(n))
    return escribe_svg(ruta, cuerpo)


class FidelidadVectorial(Desechable):
    """I9: el SVG traia <text> y la salida rasterizada tiene que tener tinta.

    Caja del SVG de arriba: x0=10, an=0,5*20*4=40 -> (10, 15, 50, 34) para el
    primero. Con la salida a 100x100 la escala es 1,0.
    """

    def _fid(self, svg, png, sonda=None):
        return V.fidelidad_vectorial(png, svg, {"destino": "png"},
                                     sonda if sonda is not None
                                     else {"ancho": 100, "alto": 100},
                                     {"categoria": "vectorial"}, {})

    def test_un_origen_que_no_es_SVG_analizable_se_declara_no_aplicable(self):
        malo = self.r("malo.svg")
        with open(malo, "w", encoding="utf-8") as fh:
            fh.write("no soy xml <")
        png = png_gris(self.r("v_x.png"), 100, 100)
        h, cob = self._fid(malo, png)
        self.assertEqual(cob, {})
        self.assertEqual(h[0]["severidad"], "informativo")
        self.assertIn("no es un SVG analizable", h[0]["mensaje"])

    def test_un_SVG_sin_text_hace_que_la_regla_no_aplique(self):
        svg = escribe_svg(self.r("sintexto.svg"), '<rect width="10" height="10"/>')
        png = png_gris(self.r("v_r.png"), 100, 100)
        h, cob = self._fid(svg, png)
        self.assertEqual(cob, {})
        self.assertIn("no tiene elementos <text>", h[0]["mensaje"])

    def test_un_transform_que_no_es_traslacion_NO_es_la_regla_no_aplica(self):
        # Trampa 44: el mensaje viejo ("el SVG no tiene elementos <text>") era
        # FALSO --si los tiene-- y ademas dejaba `cobertura` vacia, o sea la
        # regla contaba como aprobada. Ahora se declara NO CUBIERTA con motivo.
        svg = escribe_svg(self.r("rot.svg"),
                          '<g transform="rotate(30)">'
                          '<text x="10" y="50" font-size="20">HOLA</text></g>')
        png = png_gris(self.r("v_rot.png"), 100, 100)
        h, cob = self._fid(svg, png)
        self.assertIs(cob["I9"], False)
        self.assertIn("no es una traslacion", h[0]["mensaje"])
        self.assertNotIn("no tiene elementos", h[0]["mensaje"])

    def test_un_texto_TRASLADADO_se_juzga_igual_que_el_absoluto(self):
        # El caso de §5.1: mismo texto, misma tinta, mismo veredicto. Antes del
        # arreglo la version con `transform` daba `fallo: TEXTO PERDIDO`.
        png = png_gris(self.r("v_tr.png"), 100, 100,
                       pintar=lambda x, y: 20 <= y < 23 and 10 <= x < 50)
        abs_ = escribe_svg(self.r("tr_abs.svg"),
                           '<text x="10" y="30" font-size="20">HOLA</text>')
        rel = escribe_svg(self.r("tr_rel.svg"),
                          '<g transform="translate(10,20)">'
                          '<text x="0" y="10" font-size="20">HOLA</text></g>')
        ha, ca = self._fid(abs_, png)
        hb, cb = self._fid(rel, png)
        self.assertEqual((ha[0]["severidad"], ha[0]["obtenido"]),
                         (hb[0]["severidad"], hb[0]["obtenido"]))
        self.assertEqual(ca, cb)
        self.assertEqual(ha[0]["severidad"], "informativo")

    def test_si_la_salida_no_declara_geometria_no_hay_escala_que_aplicar(self):
        svg = _svg_con_texto(self.r("g.svg"))
        png = png_gris(self.r("v_g.png"), 100, 100)
        h, cob = self._fid(svg, png, sonda={"ancho": None, "alto": None})
        self.assertEqual(cob, {})
        self.assertIn("no declara geometria", h[0]["mensaje"])

    def test_si_la_salida_no_es_un_PNG_legible_I9_NO_se_da_por_aprobada(self):
        # El punto de la regla: no se pudo mirar != esta bien.
        svg = _svg_con_texto(self.r("nl.svg"))
        png = self.r("v_no.png")
        with open(png, "wb") as fh:
            fh.write(b"no soy png")
        h, cob = self._fid(svg, png)
        self.assertIs(cob["I9"], False)
        self.assertIn("no se pudo leer la tinta", h[0]["mensaje"])

    def test_TEXTO_PERDIDO_es_FALLO_el_caso_resvg(self):
        svg = _svg_con_texto(self.r("perdido.svg"))
        png = png_gris(self.r("v_blanco.png"), 100, 100)   # lienzo en blanco
        h, cob = self._fid(svg, png)
        self.assertIs(cob["I9"], True)
        self.assertEqual(h[0]["severidad"], "fallo")
        self.assertIn("TEXTO PERDIDO", h[0]["mensaje"])

    def test_con_tinta_de_sobra_I9_aprueba(self):
        svg = _svg_con_texto(self.r("bien.svg"))
        # Caja (10,15,50,34): 40x19 = 760 px. Pintamos 3 filas enteras dentro.
        png = png_gris(self.r("v_bien.png"), 100, 100,
                       pintar=lambda x, y: 20 <= y < 23 and 10 <= x < 50)
        h, cob = self._fid(svg, png)
        self.assertIs(cob["I9"], True)
        self.assertEqual(h[0]["severidad"], "informativo")
        self.assertIn("dejaron tinta", h[0]["mensaje"])

    def test_poca_tinta_es_AVISO_texto_mutilado(self):
        # Entre 0,5 % y 2,0 % de 760 px: 8 pixeles = 1,053 %.
        svg = _svg_con_texto(self.r("poca.svg"))
        png = png_gris(self.r("v_poca.png"), 100, 100,
                       pintar=lambda x, y: y == 20 and 10 <= x < 18)
        h, cob = self._fid(svg, png)
        self.assertEqual(h[0]["severidad"], "aviso")
        self.assertIn("muy poca tinta", h[0]["mensaje"])

    def test_TEXTO_PARCIALMENTE_PERDIDO_cuando_solo_una_caja_esta_vacia(self):
        # Dos <text>: el de arriba (caja y 15..34) con tinta, el de abajo
        # (caja y 55..74) sin ella.
        svg = _svg_con_texto(self.r("parcial.svg"), n=2)
        png = png_gris(self.r("v_parcial.png"), 100, 100,
                       pintar=lambda x, y: 20 <= y < 23 and 10 <= x < 50)
        h, cob = self._fid(svg, png)
        self.assertEqual(h[0]["severidad"], "fallo")
        self.assertIn("PARCIALMENTE PERDIDO", h[0]["mensaje"])

    def test_cajas_fuera_del_lienzo_NO_es_un_aprobado(self):
        # Salida de 1x1: la escala hunde las cajas a cero pixeles.
        svg = _svg_con_texto(self.r("micro.svg"))
        png = png_gris(self.r("v_micro.png"), 1, 1)
        h, cob = V.fidelidad_vectorial(png, svg, {"destino": "png"},
                                       {"ancho": 1, "alto": 1},
                                       {"categoria": "vectorial"}, {})
        self.assertIs(cob["I9"], False)
        self.assertIn("fuera del lienzo", h[0]["mensaje"])

    def test_la_escala_sale_de_la_geometria_declarada_por_la_sonda(self):
        # Mismo SVG, salida al doble: la caja tiene que duplicarse.
        svg = _svg_con_texto(self.r("esc.svg"))
        png = png_gris(self.r("v_esc.png"), 200, 200,
                       pintar=lambda x, y: 40 <= y < 46 and 20 <= x < 100)
        h, cob = self._fid(svg, png, sonda={"ancho": 200, "alto": 200})
        self.assertIs(cob["I9"], True)
        self.assertEqual(h[0]["severidad"], "informativo")

    def test_es_svg_decide_por_CONTENIDO_no_por_extension(self):
        # OJO con el nombre del fichero: en Windows `CON`, `PRN`, `AUX`, `NUL`,
        # `COM1`-`COM9` y `LPT1`-`LPT9` son DISPOSITIVOS reservados con
        # cualquier extension. Este fichero se llamaba `con.txt` y `es_svg`
        # abria la CONSOLA y se quedaba esperando el teclado: un hilo, cero
        # hijos, cero CPU y ni un error. Ver el informe, §6.
        a = escribe_svg(self.r("contenido.txt"), '<rect/>')
        self.assertTrue(V.es_svg(a))
        b = self.r("cabecera.svg")
        with open(b, "w", encoding="utf-8") as fh:
            fh.write('<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg"/>')
        self.assertTrue(V.es_svg(b))
        c = self.r("noes.svg")
        with open(c, "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n")
        self.assertFalse(V.es_svg(c))
        self.assertFalse(V.es_svg(self.r("no-existe-nada.svg")))


# ===========================================================================
# fidelidad_video  --  74 sentencias sin ejecutar
# ===========================================================================

def _rejilla_generica():
    """La paleta por defecto de ffmpeg: 8x8x4 = 256 (CLAUDE.md, V9)."""
    pal = []
    for r in range(8):
        for g in range(8):
            for b in range(4):
                pal.append((r * 36, g * 36, b * 85))
    return pal


class FidelidadVideoV9(Desechable):
    """V9 (paleta del GIF) es EN PROCESO: `_paleta_gif` lee 13 + 3n bytes y la
    rama de `dest == 'gif'` sale antes de tocar ningun motor."""

    def _v9(self, salida):
        return V.fidelidad_video(salida, None, {"destino": "gif"},
                                 {"categoria": "video"},
                                 {"categoria": "video"}, {})

    def test_la_paleta_generica_de_ffmpeg_es_un_AVISO(self):
        g = escribe_gif(self.r("generica.gif"), _rejilla_generica())
        h, cob = self._v9(g)
        self.assertIs(cob["V9"], True)
        self.assertEqual(h[0]["severidad"], "aviso")
        self.assertIn("PALETA GENERICA", h[0]["mensaje"])
        self.assertIn("(8x8x4)", h[0]["mensaje"])

    def test_una_paleta_calculada_sobre_el_clip_NO_es_rejilla(self):
        # 256 colores que no son producto cartesiano de pocos valores.
        pal = [((i * 7) % 256, (i * 13) % 256, (i * 29) % 256)
               for i in range(256)]
        g = escribe_gif(self.r("clip.gif"), pal)
        h, cob = self._v9(g)
        self.assertIs(cob["V9"], True)
        self.assertEqual(h[0]["severidad"], "informativo")
        self.assertIn("calculada sobre el clip", h[0]["mensaje"])

    def test_si_no_hay_paleta_legible_V9_no_se_da_por_aprobada(self):
        p = self.r("nogif.gif")
        with open(p, "wb") as fh:
            fh.write(b"no soy un gif")
        h, cob = self._v9(p)
        self.assertIs(cob["V9"], False)
        self.assertEqual(h, [])

    def test_un_GIF_sin_tabla_de_color_global_tampoco_aprueba(self):
        p = self.r("sintabla.gif")
        with open(p, "wb") as fh:
            fh.write(b"GIF89a" + struct.pack("<HH", 4, 4) + bytes([0x00, 0, 0]))
        self.assertEqual(V._paleta_gif(p), [])
        h, cob = self._v9(p)
        self.assertIs(cob["V9"], False)

    def test_el_fichero_que_no_existe_no_revienta_la_regla(self):
        with self.assertRaises(OSError):
            V._paleta_gif(self.r("no-esta.gif"))


@unittest.skipUnless(HAY_FFMPEG, "hacen falta ffmpeg y ffprobe")
class FidelidadVideoMotor(Desechable):
    """V5/V2/V6/V8 con ffmpeg de verdad, sobre clips diminutos generados aqui.

    Los clips llevan `-frames:v` DENTRO de la orden (trampa 52): un tope que
    solo mata al cliente no es un tope.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base = os.path.join(cls.dir, "base.mkv")
        cls._ff(["-f", "lavfi", "-i", "testsrc=size=64x48:rate=5",
                 "-frames:v", "5", "-c:v", "ffv1",
                 "-metadata:s:v:0", "language=spa",
                 "-metadata:s:v:0", "title=Prueba", cls.base])
        cls.remux = os.path.join(cls.dir, "remux.mkv")
        cls._ff(["-i", cls.base, "-c", "copy", "-map", "0", cls.remux])
        cls.sin_etiq = os.path.join(cls.dir, "sinetiq.mkv")
        cls._ff(["-i", cls.base, "-c", "copy", "-map", "0",
                 "-map_metadata", "-1", cls.sin_etiq])
        cls.recod = os.path.join(cls.dir, "recod.mp4")
        cls._ff(["-i", cls.base, "-c:v", "libx264", "-crf", "18",
                 "-pix_fmt", "yuv420p", cls.recod])
        # Degradar AGRESIVAMENTE no baja del suelo: `-qp 51` con `boxblur` da
        # 11,49 dB y sigue siendo la misma imagen. Bajar del suelo exige OTRA
        # imagen: un plano negro contra `testsrc` da 5,98 dB. Sonda en
        # `bench/salidas-cobertura-fidelidad/sonda_v8.py`.
        cls.hundido = os.path.join(cls.dir, "hundido.mp4")
        cls._ff(["-i", cls.base, "-c:v", "libx264", "-qp", "51",
                 "-vf", "boxblur=10:10", "-pix_fmt", "yuv420p", cls.hundido])
        cls.negro = os.path.join(cls.dir, "negro.mkv")
        cls._ff(["-f", "lavfi", "-i", "color=c=black:size=64x48:rate=5",
                 "-frames:v", "5", "-c:v", "ffv1", cls.negro])
        cls.otro = os.path.join(cls.dir, "otro.mkv")
        cls._ff(["-f", "lavfi", "-i", "color=c=red:size=64x48:rate=5",
                 "-frames:v", "3", "-c:v", "ffv1", cls.otro])
        # Dos pistas, y la ETIQUETADA es la SEGUNDA: hace falta para las dos
        # ramas que un fichero de una sola pista no puede tocar --la pista sin
        # etiqueta que se salta, y la pista etiquetada que la salida ya no
        # tiene--.
        cls.dos = os.path.join(cls.dir, "dos.mkv")
        cls._ff(["-f", "lavfi", "-i", "testsrc=size=64x48:rate=5",
                 "-f", "lavfi", "-i", "anullsrc=r=8000:cl=mono",
                 "-map", "1:a", "-map", "0:v", "-t", "1",
                 "-c:v", "ffv1", "-c:a", "pcm_s16le",
                 "-metadata:s:v:0", "language=spa",
                 "-metadata:s:v:0", "title=Prueba", cls.dos])
        cls.dos_recortado = os.path.join(cls.dir, "dos_recortado.mkv")
        cls._ff(["-i", cls.dos, "-map", "0:a", "-c", "copy",
                 cls.dos_recortado])

    @staticmethod
    def _ff(args):
        p = subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error"] + args,
                           capture_output=True, timeout=120)
        if p.returncode != 0:
            raise unittest.SkipTest("ffmpeg fallo: %s"
                                    % p.stderr.decode("utf-8", "replace")[:200])

    SONDA = {"categoria": "video", "n_video": 1}

    def _fid(self, salida, entrada, pedido=None, sonda=None, sonda_ent=None):
        return V.fidelidad_video(salida, entrada, pedido or {"destino": "mkv"},
                                 sonda or dict(self.SONDA),
                                 sonda_ent or dict(self.SONDA), {})

    # ---- V5 ----------------------------------------------------------------

    def test_V5_las_etiquetas_de_pista_se_conservan_en_un_remux(self):
        h, cob = self._fid(self.remux, self.base)
        self.assertIs(cob["V5"], True)
        v5 = [x for x in h if x["regla"] == "V5"][0]
        self.assertEqual(v5["severidad"], "informativo")
        self.assertIn("se conservan", v5["mensaje"])

    def test_V5_perder_el_idioma_es_un_AVISO(self):
        h, cob = self._fid(self.sin_etiq, self.base)
        v5 = [x for x in h if x["regla"] == "V5"][0]
        self.assertEqual(v5["severidad"], "aviso")
        self.assertIn("se pierden etiquetas", v5["mensaje"])

    def test_V5_si_la_entrada_no_trae_etiquetas_la_regla_NO_discrimina(self):
        # Es el caso de patologico_2pistas.mkv, y el codigo lo dice en voz alta
        # en vez de aprobar en silencio.
        h, cob = self._fid(self.base, self.sin_etiq)
        v5 = [x for x in h if x["regla"] == "V5"][0]
        self.assertEqual(v5["severidad"], "informativo")
        self.assertIn("no discrimina", v5["mensaje"])

    def test_V5_una_pista_SIN_etiquetas_no_cuenta_como_perdida(self):
        # `dos.mkv` lleva audio sin etiquetar y video etiquetado. Perder el
        # audio no es perder una etiqueta; perder el VIDEO si.
        h, cob = self._fid(self.dos_recortado, self.dos)
        v5 = [x for x in h if x["regla"] == "V5"][0]
        self.assertEqual(v5["severidad"], "aviso")
        self.assertIn("pista 1 language: 'spa' -> None", v5["mensaje"])
        # Una sola perdida por campo, y ninguna atribuida a la pista 0.
        self.assertNotIn("pista 0", v5["mensaje"])

    def test_V5_empareja_por_POSICION_y_REORDENAR_le_parece_una_perdida(self):
        """DEFECTO DOCUMENTADO, NO ARREGLADO (informe §5.2).

        `y = ts[i] if i < len(ts) else None` empareja la pista `i` de la
        entrada con la `i` de la salida. Reordenar las pistas --que es lo que
        hace ffmpeg por defecto cuando no se pasa `-map 0`-- cruza el video con
        el audio y V5 declara `aviso: se pierden etiquetas` sobre una salida
        que conserva TODAS.

        Esta prueba fija el comportamiento de HOY, no el deseable: si alguien
        arregla el emparejamiento se pondra roja, y ese es el sitio donde
        encontrara el motivo (trampa 65).
        """
        reord = os.path.join(self.dir, "reordenado.mkv")
        self._ff(["-i", self.dos, "-map", "0:v", "-map", "0:a", "-c", "copy",
                  reord])
        etq_e, _ = V._ffprobe_etiquetas(self.dos)
        etq_s, _ = V._ffprobe_etiquetas(reord)

        def conjunto(l):
            return sorted((x["language"], x["title"]) for x in l
                          if x["language"] or x["title"])

        # Control: NINGUNA etiqueta ha desaparecido. Solo cambio el orden.
        self.assertEqual(conjunto(etq_e), conjunto(etq_s))
        h, cob = self._fid(reord, self.dos)
        v5 = [x for x in h if x["regla"] == "V5"][0]
        self.assertEqual(v5["severidad"], "aviso")       # <- el falso positivo
        self.assertIn("se pierden etiquetas", v5["mensaje"])

    def test_V5_no_se_evalua_hacia_los_destinos_de_un_solo_fotograma(self):
        for dest in ("wav", "bmp", "png", "jpg", "jpeg"):
            with self.subTest(destino=dest):
                h, cob = self._fid(self.remux, self.base,
                                   pedido={"destino": dest})
                self.assertNotIn("V5", cob)

    def test_V5_con_doble_cuando_ffprobe_no_devuelve_etiquetas_legibles(self):
        orig = V._ffprobe_etiquetas
        V._ffprobe_etiquetas = lambda ruta: (None, "ffprobe no pudo")
        try:
            h, cob = self._fid(self.remux, self.base)
        finally:
            V._ffprobe_etiquetas = orig
        self.assertIs(cob["V5"], False)
        v5 = [x for x in h if x["regla"] == "V5"][0]
        self.assertIn("no legibles", v5["mensaje"])

    # ---- cortes ------------------------------------------------------------

    def test_sin_pista_de_video_a_ninguno_de_los_dos_lados_se_para_en_V5(self):
        for lado in ("sonda", "sonda_ent"):
            with self.subTest(lado=lado):
                s = dict(self.SONDA)
                e = dict(self.SONDA)
                (s if lado == "sonda" else e)["n_video"] = 0
                h, cob = self._fid(self.remux, self.base, sonda=s, sonda_ent=e)
                self.assertNotIn("V2", cob)
                self.assertNotIn("V6", cob)

    def test_pedir_escala_o_recorte_retira_V2_V6_y_V8(self):
        for clave in ("escala", "recortar"):
            with self.subTest(param=clave):
                h, cob = self._fid(self.remux, self.base,
                                   pedido={"destino": "mkv",
                                           "params": {clave: "50%"}})
                self.assertNotIn("V2", cob)
                self.assertNotIn("V8", cob)

    # ---- V2 ----------------------------------------------------------------

    def test_V2_cuenta_los_fotogramas_de_verdad(self):
        h, cob = self._fid(self.remux, self.base)
        self.assertIs(cob["V2"], True)
        v2 = [x for x in h if x["regla"] == "V2"][0]
        self.assertEqual(v2["severidad"], "informativo")
        self.assertEqual(v2["obtenido"], 5)

    def test_V2_perder_fotogramas_es_FALLO(self):
        h, cob = self._fid(self.otro, self.base)
        v2 = [x for x in h if x["regla"] == "V2"][0]
        self.assertEqual(v2["severidad"], "fallo")
        self.assertEqual((v2["esperado"], v2["obtenido"]), (5, 3))

    def test_V2_apagada_se_declara_NO_CUBIERTA_no_aprobada(self):
        V.v2(False)
        try:
            h, cob = self._fid(self.remux, self.base)
        finally:
            V.v2(True)
        self.assertIs(cob["V2"], False)
        v2 = [x for x in h if x["regla"] == "V2"][0]
        self.assertIn("DESACTIVADO", v2["mensaje"])

    def test_V2_no_se_evalua_si_se_pidio_cambiar_el_fps(self):
        h, cob = self._fid(self.remux, self.base,
                           pedido={"destino": "mkv", "params": {"fps": 10}})
        self.assertNotIn("V2", cob)
        self.assertNotIn("V6", cob)          # el fps corta antes de V6

    def test_V2_con_doble_cuando_no_se_puede_contar(self):
        orig = V._ffprobe_fotogramas
        V._ffprobe_fotogramas = lambda ruta: (None, "sin nb_read_frames")
        try:
            h, cob = self._fid(self.remux, self.base)
        finally:
            V._ffprobe_fotogramas = orig
        self.assertIs(cob["V2"], False)
        v2 = [x for x in h if x["regla"] == "V2"][0]
        self.assertIn("no calculable", v2["mensaje"])

    # ---- V6 / V8 -----------------------------------------------------------

    def test_V6_un_remux_exacto_da_el_mismo_hash_por_pixel_y_aprueba_V8(self):
        h, cob = self._fid(self.remux, self.base)
        self.assertIs(cob["V6"], True)
        self.assertIs(cob["V8"], True)
        v6 = [x for x in h if x["regla"] == "V6"][0]
        self.assertIn("remux exacto", v6["mensaje"])
        self.assertEqual([x for x in h if x["regla"] == "V8"], [])

    def test_V6_pedir_COPIA_y_ver_pixeles_distintos_es_FALLO(self):
        h, cob = self._fid(self.recod, self.base,
                           pedido={"destino": "mp4", "params": {"copia": True}})
        v6 = [x for x in h if x["regla"] == "V6"][0]
        self.assertEqual(v6["severidad"], "fallo")
        self.assertIn("COPIAR", v6["mensaje"])

    def test_V6_avisa_si_cambia_el_numero_de_fotogramas(self):
        h, cob = self._fid(self.otro, self.base)
        v6 = [x for x in h if x["regla"] == "V6"][0]
        self.assertEqual(v6["severidad"], "aviso")
        self.assertIn("cambia el numero de fotogramas", v6["mensaje"])

    def test_V8_una_recodificacion_buena_pasa_el_umbral(self):
        h, cob = self._fid(self.recod, self.base)
        self.assertIs(cob["V8"], True)
        v8 = [x for x in h if x["regla"] == "V8"][0]
        self.assertEqual(v8["severidad"], "informativo")

    def test_V8_por_debajo_del_SUELO_es_FALLO_no_aviso(self):
        # "Ya no es una recodificacion de la entrada, es otra imagen."
        h, cob = self._fid(self.negro, self.base)
        v8 = [x for x in h if x["regla"] == "V8"][0]
        self.assertEqual(v8["severidad"], "fallo")
        self.assertIn("POR DEBAJO DEL SUELO", v8["mensaje"])
        self.assertLess(v8["obtenido"], V.PSNR_SUELO_VIDEO)

    def test_V8_entre_el_suelo_y_el_umbral_es_AVISO(self):
        # La MISMA imagen destrozada: pasa el suelo y no llega al umbral.
        h, cob = self._fid(self.hundido, self.base)
        v8 = [x for x in h if x["regla"] == "V8"][0]
        self.assertEqual(v8["severidad"], "aviso")
        self.assertGreaterEqual(v8["obtenido"], V.PSNR_SUELO_VIDEO)
        self.assertLess(v8["obtenido"], V.PSNR_MIN_VIDEO)

    def test_V8_con_doble_sin_componente_y(self):
        orig = V._ffmpeg_psnr
        V._ffmpeg_psnr = lambda s, e: ({"average": 30.0}, None)
        try:
            h, cob = self._fid(self.recod, self.base)
        finally:
            V._ffmpeg_psnr = orig
        v8 = [x for x in h if x["regla"] == "V8"][0]
        self.assertIn("sin componente y", v8["mensaje"])

    def test_V8_con_doble_no_calculable(self):
        orig = V._ffmpeg_psnr
        V._ffmpeg_psnr = lambda s, e: (None, "psnr fallo")
        try:
            h, cob = self._fid(self.recod, self.base)
        finally:
            V._ffmpeg_psnr = orig
        self.assertIs(cob["V8"], False)

    def test_V6_con_doble_cuando_el_framemd5_no_sale(self):
        orig = V._ffmpeg_framemd5
        V._ffmpeg_framemd5 = lambda ruta: (None, 0, "framemd5 vacio")
        try:
            h, cob = self._fid(self.recod, self.base)
        finally:
            V._ffmpeg_framemd5 = orig
        self.assertIs(cob["V6"], False)
        v6 = [x for x in h if x["regla"] == "V6"][0]
        self.assertIn("no calculable", v6["mensaje"])


# ===========================================================================
# fidelidad_imagen  --  69 sentencias sin ejecutar
# ===========================================================================

TIPICO_PNG = _activo("imagen", "tipico.png")
ALPHA_PNG = _activo("imagen", "alpha.png")


@unittest.skipUnless(HAY_MAGICK, "hace falta ImageMagick")
class FidelidadImagen(Desechable):

    IMG = {"categoria": "imagen"}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.a = png_gris(os.path.join(cls.dir, "a.png"), 32, 32,
                         pintar=lambda x, y: (x // 4 + y // 4) % 2 == 0)
        cls.a_copia = os.path.join(cls.dir, "a_copia.png")
        shutil.copyfile(cls.a, cls.a_copia)
        cls.b = png_gris(os.path.join(cls.dir, "b.png"), 32, 32,
                         pintar=lambda x, y: x < 16)

    def _fid(self, salida, entrada, pedido, sonda=None, sonda_ent=None):
        return V.fidelidad_imagen(salida, entrada, pedido,
                                  sonda if sonda is not None else dict(self.IMG),
                                  sonda_ent if sonda_ent is not None
                                  else dict(self.IMG), {})

    @staticmethod
    def _mg(args):
        p = subprocess.run(["magick"] + args, capture_output=True, timeout=120)
        if p.returncode != 0:
            raise unittest.SkipTest("magick fallo: %s"
                                    % p.stderr.decode("utf-8", "replace")[:200])

    # ---- I6 (sin perdida) --------------------------------------------------

    def test_I6_una_conversion_SIN_PERDIDA_identica_aprueba(self):
        h, cob = self._fid(self.a_copia, self.a, {"destino": "png"})
        self.assertIs(cob["I6"], True)
        self.assertEqual(h[0]["regla"], "I6")
        self.assertIn("identicos", h[0]["mensaje"])

    def test_I6_una_conversion_SIN_PERDIDA_que_cambia_pixeles_es_FALLO(self):
        h, cob = self._fid(self.b, self.a, {"destino": "png"})
        self.assertEqual(h[0]["severidad"], "fallo")
        self.assertIn("SIN PERDIDA", h[0]["mensaje"])

    def test_I6_no_calculable_no_es_un_aprobado(self):
        h, cob = self._fid(self.r("no-esta.png"), self.a, {"destino": "png"})
        self.assertIs(cob["I6"], False)
        self.assertIn("no calculable", h[0]["mensaje"])

    def test_I6_se_retira_si_se_pidio_REDUCIR_la_profundidad(self):
        # Reducir bits es una perdida pedida: exigir RMSE 0 seria un falso
        # positivo. Cae a I7.
        h, cob = self._fid(self.a_copia, self.a,
                           {"destino": "png",
                            "params": {"profundidad_bits": 8}},
                           sonda_ent={"categoria": "imagen",
                                      "profundidad_bits": 16})
        self.assertNotIn("I6", cob)
        self.assertIn("I7", cob)

    # ---- cortes ------------------------------------------------------------

    def test_si_alguno_de_los_dos_lados_no_es_imagen_no_hay_comparacion(self):
        h, cob = self._fid(self.a_copia, self.a, {"destino": "png"},
                           sonda={"categoria": "documento"})
        self.assertEqual(cob, {})
        h, cob = self._fid(self.a_copia, self.a, {"destino": "png"},
                           sonda_ent={"categoria": "documento"})
        self.assertEqual(cob, {})

    def test_pedir_geometria_retira_la_comparacion_pixel_a_pixel(self):
        for clave, valor in (("ancho", 10), ("alto", 10), ("escala", "50%"),
                             ("dpi", 300), ("densidad", 300), ("recortar", "1x1")):
            with self.subTest(param=clave):
                h, cob = self._fid(self.a_copia, self.a,
                                   {"destino": "png", "params": {clave: valor}})
                self.assertEqual(cob, {})

    # ---- I7 (con perdida) --------------------------------------------------

    def test_I7_un_JPEG_de_calidad_alta_pasa_el_umbral(self):
        j = self.r("alta.jpg")
        self._mg([self.a, "-quality", "100", j])
        h, cob = self._fid(j, self.a, {"destino": "jpg"})
        i7 = [x for x in h if x["regla"] == "I7"][0]
        self.assertIs(cob["I7"], True)
        self.assertEqual(i7["severidad"], "informativo")

    def test_I7_por_debajo_del_umbral_y_sin_excusa_es_AVISO(self):
        j = self.r("mala.jpg")
        self._mg([self.a, "-quality", "1", j])
        h, cob = self._fid(j, self.a, {"destino": "jpg"})
        i7 = [x for x in h if x["regla"] == "I7"][0]
        self.assertEqual(i7["severidad"], "aviso")
        self.assertLess(i7["obtenido"], V.PSNR_MIN_IMAGEN)

    def test_I7_la_excusa_del_GRAFISMO_tiene_suelo_de_20_dB(self):
        j = self.r("graf.jpg")
        self._mg([self.a, "-quality", "30", j])
        h, cob = self._fid(j, self.a, {"destino": "jpg"},
                           sonda_ent={"categoria": "imagen", "paleta": True})
        i7 = [x for x in h if x["regla"] == "I7"][0]
        self.assertEqual(i7["severidad"], "informativo")
        self.assertIn("grafismo, no fotografia", i7["mensaje"])
        self.assertGreaterEqual(i7["obtenido"], 20.0)

    def test_I7_la_excusa_de_los_16_BITS_cuantizados_a_8(self):
        orig = V._magick_metrica
        V._magick_metrica = lambda a, b, m, ap=False: (35.0, None)
        try:
            h, cob = self._fid(self.a_copia, self.a, {"destino": "jpg"},
                               sonda_ent={"categoria": "imagen",
                                          "profundidad_bits": 16})
        finally:
            V._magick_metrica = orig
        i7 = [x for x in h if x["regla"] == "I7"][0]
        self.assertIn("cuantizada a 8", i7["mensaje"])

    def test_I7_la_excusa_del_ALFA_de_AVIF(self):
        orig = V._magick_metrica
        V._magick_metrica = lambda a, b, m, ap=False: (38.8, None)
        try:
            h, cob = self._fid(self.a_copia, self.a, {"destino": "avif"},
                               sonda_ent={"categoria": "imagen",
                                          "tiene_alfa": True})
        finally:
            V._magick_metrica = orig
        i7 = [x for x in h if x["regla"] == "I7"][0]
        self.assertIn("plano alfa CON PERDIDA", i7["mensaje"])
        self.assertIn("(sobre blanco)", i7["mensaje"])   # aplanar = True

    def test_I7_no_calculable_no_es_un_aprobado(self):
        h, cob = self._fid(self.r("no-esta.jpg"), self.a, {"destino": "jpg"})
        i7 = [x for x in h if x["regla"] == "I7"][0]
        self.assertIs(cob["I7"], False)
        self.assertIn("no calculable", i7["mensaje"])

    # ---- I8 (grafismo con perdida a un destino que admite sin perdida) ------

    def test_I8_un_grafismo_codificado_CON_PERDIDA_en_webp_es_AVISO(self):
        w = self.r("graf.webp")
        self._mg([self.a, w])
        h, cob = self._fid(w, self.a, {"destino": "webp"},
                           sonda={"categoria": "imagen", "perdida": True},
                           sonda_ent={"categoria": "imagen",
                                      "colores_paleta": 2})
        self.assertIs(cob["I8"], True)
        i8 = [x for x in h if x["regla"] == "I8"][0]
        self.assertEqual(i8["severidad"], "aviso")

    def test_I8_no_dispara_si_el_webp_ya_es_SIN_PERDIDA(self):
        w = self.r("lossless.webp")
        self._mg([self.a, "-define", "webp:lossless=true", w])
        h, cob = self._fid(w, self.a, {"destino": "webp"},
                           sonda={"categoria": "imagen", "perdida": False},
                           sonda_ent={"categoria": "imagen", "paleta": True})
        self.assertNotIn("I8", cob)

    # ---- I3 (color del aplanado) -------------------------------------------

    @unittest.skipUnless(ALPHA_PNG, "hace falta corpus/imagen/alpha.png (LFS)")
    def test_I3_aplanado_sobre_BLANCO_es_correcto(self):
        j = self.r("blanco.jpg")
        self._mg([ALPHA_PNG, "-background", "white", "-flatten", j])
        h, cob = self._fid(j, ALPHA_PNG, {"destino": "jpg"})
        self.assertIs(cob["I3"], True)
        i3 = [x for x in h if x["regla"] == "I3"][0]
        self.assertEqual(i3["severidad"], "informativo")
        self.assertIn("BLANCO", i3["mensaje"])

    @unittest.skipUnless(ALPHA_PNG, "hace falta corpus/imagen/alpha.png (LFS)")
    def test_I3_aplanado_sobre_NEGRO_es_el_hallazgo(self):
        j = self.r("negro.jpg")
        self._mg([ALPHA_PNG, "-background", "black", "-flatten", j])
        h, cob = self._fid(j, ALPHA_PNG, {"destino": "jpg"})
        i3 = [x for x in h if x["regla"] == "I3"][0]
        self.assertEqual(i3["severidad"], "aviso")
        self.assertIn("APLANADO SOBRE NEGRO", i3["mensaje"])

    @unittest.skipUnless(ALPHA_PNG, "hace falta corpus/imagen/alpha.png (LFS)")
    def test_I3_aplanado_sobre_otro_color_tambien_avisa(self):
        j = self.r("rojo.jpg")
        self._mg([ALPHA_PNG, "-background", "red", "-flatten", j])
        h, cob = self._fid(j, ALPHA_PNG, {"destino": "jpg"})
        i3 = [x for x in h if x["regla"] == "I3"][0]
        self.assertEqual(i3["severidad"], "aviso")
        self.assertIn("que no es blanco", i3["mensaje"])

    @unittest.skipUnless(ALPHA_PNG, "hace falta corpus/imagen/alpha.png (LFS)")
    def test_I3_si_no_se_puede_leer_el_pixel_NO_se_da_por_cubierta(self):
        h, cob = self._fid(self.r("no-esta.jpg"), ALPHA_PNG, {"destino": "jpg"})
        self.assertIs(cob["I3"], False)
        i3 = [x for x in h if x["regla"] == "I3"][0]
        self.assertIn("no se pudo leer el pixel", i3["mensaje"])

    @unittest.skipUnless(TIPICO_PNG, "hace falta corpus/imagen/tipico.png (LFS)")
    def test_I3_el_ALFA_TRIVIAL_cubre_la_regla_sin_hallazgo(self):
        # Trampa 1: tipico.png declara alfa y es ENTERAMENTE OPACO. No hay
        # pixel transparente que mirar, asi que I3 esta cubierta y muda.
        j = self.r("opaco.jpg")
        self._mg([TIPICO_PNG, j])
        h, cob = self._fid(j, TIPICO_PNG, {"destino": "jpg"})
        self.assertIs(cob["I3"], True)
        self.assertEqual([x for x in h if x["regla"] == "I3"], [])

    def test_I3_no_se_evalua_si_se_declaro_el_color_de_fondo(self):
        h, cob = self._fid(self.a_copia, self.a,
                           {"destino": "jpg", "params": {"fondo": "white"}})
        self.assertNotIn("I3", cob)

    def test_I3_no_se_evalua_hacia_PDF(self):
        # Un PDF no tiene canal alfa que aplanar: marcarla no cubierta seria
        # ruido, no honestidad.
        h, cob = self._fid(self.a_copia, self.a, {"destino": "pdf"})
        self.assertNotIn("I3", cob)


# ===========================================================================
# fidelidad_pdf  --  48 sentencias sin ejecutar
# ===========================================================================

PROSA = ("Este documento contiene prosa suficiente para superar el umbral "
         "de diez caracteres imprimibles que exige la regla P6 del "
         "verificador de FileX")
ALUCINADO = "a b c d e f g h i j k l m n o p q r s t u v"


@unittest.skipUnless(HAY_GS, "hace falta Ghostscript")
class FidelidadPdf(Desechable):

    PDF = {"categoria": "pdf"}

    def _fid(self, salida, entrada, pedido=None, sonda=None, sonda_ent=None):
        return V.fidelidad_pdf(salida, entrada, pedido or {"destino": "pdf"},
                               sonda if sonda is not None else dict(self.PDF),
                               sonda_ent if sonda_ent is not None
                               else dict(self.PDF), {})

    def test_si_la_salida_no_es_un_PDF_la_regla_no_aplica(self):
        h, cob = self._fid("x", "y", sonda={"categoria": "imagen"})
        self.assertEqual((h, cob), ([], {}))

    def test_P6_cuenta_los_caracteres_imprimibles(self):
        p = escribe_pdf(self.r("prosa.pdf"), PROSA)
        h, cob = self._fid(p, p)
        self.assertIs(cob["P6"], True)
        p6 = [x for x in h if x["regla"] == "P6"][0]
        self.assertGreaterEqual(p6["obtenido"], V.TEXTO_MIN_CHARS)

    def test_P6_dos_caracteres_son_BASURA_no_una_capa_de_texto(self):
        # Trampa 4: txtwrite emite 1-3 caracteres de basura; el umbral es 10.
        p = escribe_pdf(self.r("basura.pdf"), "FX")
        h, cob = self._fid(p, p)
        basura = [x for x in h if "BASURA" in x["mensaje"]]
        self.assertEqual(len(basura), 1)
        self.assertNotIn("P9", cob)

    def test_P6_con_doble_si_txtwrite_falla_sobre_la_salida(self):
        orig = V._gs_texto
        V._gs_texto = lambda pdf: (None, "gs fallo")
        try:
            h, cob = self._fid("x", "y")
        finally:
            V._gs_texto = orig
        self.assertEqual(cob, {})
        self.assertIn("txtwrite fallo sobre la salida", h[0]["mensaje"])

    def test_P9_la_prosa_es_una_capa_de_texto_PLAUSIBLE(self):
        p = escribe_pdf(self.r("plaus.pdf"), PROSA)
        h, cob = self._fid(p, p)
        self.assertIs(cob["P9"], True)
        p9 = [x for x in h if x["regla"] == "P9"][0]
        self.assertEqual(p9["severidad"], "informativo")

    def test_P9_letras_sueltas_son_ALUCINACION_y_es_AVISO_sin_OCR(self):
        p = escribe_pdf(self.r("aluc.pdf"), ALUCINADO)
        h, cob = self._fid(p, p)
        p9 = [x for x in h if x["regla"] == "P9"][0]
        self.assertEqual(p9["severidad"], "aviso")
        self.assertIn("ALUCINACION", p9["mensaje"])

    def test_P9_la_misma_alucinacion_es_FALLO_si_se_PIDIO_OCR(self):
        # La severidad depende del pedido: si pediste OCR, el ruido no vale.
        p = escribe_pdf(self.r("aluc2.pdf"), ALUCINADO)
        h, cob = self._fid(p, p, pedido={"destino": "pdf",
                                         "params": {"ocr": True}})
        p9 = [x for x in h if x["regla"] == "P9"][0]
        self.assertEqual(p9["severidad"], "fallo")

    def test_si_la_ENTRADA_no_es_un_PDF_no_hay_P2_ni_P5(self):
        p = escribe_pdf(self.r("solo.pdf"), PROSA)
        h, cob = self._fid(p, p, sonda_ent={"categoria": "imagen"})
        self.assertNotIn("P2", cob)
        self.assertEqual([x for x in h if x["regla"] in ("P2", "P5")], [])

    def test_P2_el_texto_se_conserva_sha256_igual(self):
        p = escribe_pdf(self.r("igual.pdf"), PROSA)
        q = escribe_pdf(self.r("igual2.pdf"), PROSA)
        h, cob = self._fid(q, p)
        self.assertIs(cob["P2"], True)
        p2 = [x for x in h if x["regla"] == "P2"][0]
        self.assertEqual(p2["severidad"], "informativo")

    def test_P2_un_PDF_a_PDF_que_pierde_el_texto_es_FALLO(self):
        e = escribe_pdf(self.r("ent.pdf"), PROSA)
        s = escribe_pdf(self.r("sal.pdf"), PROSA + " Y ADEMAS OTRA COSA MAS")
        h, cob = self._fid(s, e)
        p2 = [x for x in h if x["regla"] == "P2"][0]
        self.assertEqual(p2["severidad"], "fallo")
        self.assertIn("NO conserva el texto", p2["mensaje"])

    def test_P5_sin_capa_de_texto_en_la_entrada_y_sin_OCR_no_se_exige_texto(self):
        e = escribe_pdf(self.r("vacio_e.pdf"), None)
        s = escribe_pdf(self.r("vacio_s.pdf"), PROSA)
        h, cob = self._fid(s, e)
        p5 = [x for x in h if x["regla"] == "P5"][0]
        self.assertEqual(p5["severidad"], "informativo")
        self.assertIn("no se exige texto", p5["mensaje"])

    def test_P5_se_pidio_OCR_y_la_salida_NO_trae_texto_es_FALLO(self):
        e = escribe_pdf(self.r("ocr_e.pdf"), None)
        s = escribe_pdf(self.r("ocr_s.pdf"), None)
        h, cob = self._fid(s, e, pedido={"destino": "pdf",
                                         "params": {"ocr": True}})
        p5 = [x for x in h if x["regla"] == "P5"][0]
        self.assertEqual(p5["severidad"], "fallo")
        self.assertIn("se pidio OCR", p5["mensaje"])

    def test_P5_se_pidio_OCR_y_la_salida_SI_trae_texto(self):
        e = escribe_pdf(self.r("ocr2_e.pdf"), None)
        s = escribe_pdf(self.r("ocr2_s.pdf"), PROSA)
        h, cob = self._fid(s, e, pedido={"destino": "pdf",
                                         "params": {"ocr": True}})
        p5 = [x for x in h if x["regla"] == "P5"][0]
        self.assertEqual(p5["severidad"], "informativo")
        self.assertIn("su plausibilidad la juzga P9", p5["mensaje"])

    def test_P2_con_doble_si_txtwrite_falla_sobre_la_ENTRADA(self):
        p = escribe_pdf(self.r("ent_falla.pdf"), PROSA)
        orig = V._gs_texto
        llamadas = []

        def doble(pdf):
            llamadas.append(pdf)
            return (None, "gs fallo") if len(llamadas) > 1 else (PROSA, None)

        V._gs_texto = doble
        try:
            h, cob = self._fid(p, p)
        finally:
            V._gs_texto = orig
        self.assertNotIn("P2", cob)
        self.assertIn("txtwrite fallo sobre la entrada", h[-1]["mensaje"])

    def test_senal_alucinacion_separa_prosa_de_ruido(self):
        self.assertFalse(V.senal_alucinacion(PROSA)["alucinacion"])
        self.assertTrue(V.senal_alucinacion(ALUCINADO)["alucinacion"])


if __name__ == "__main__":
    unittest.main()

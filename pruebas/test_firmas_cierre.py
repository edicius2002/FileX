#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F2 — el cierre del bloque de firmas: marcadores más allá del byte 512.

Lo que se prueba aquí, y por qué cada prueba existe:

* **Los dos accionables de la deuda** (`bench/firmas-contrato.md` §3.2): el
  marcador de PICT vive en el byte **522** y el de PCD en el **0x800**, y la
  sonda leía 512. Sin el arreglo, `.pict` sale `desconocido` y `.pcd` sale
  **`mpegaudio`** —su relleno `0xFF` casa con el sincronismo de trama de audio
  MPEG—, y eso **no es benigno**: el contrato entero devuelve `fallo` sobre un
  PCD legítimo, porque la sonda lo trata como audio y `G4` dispara *«duración
  nula o ilegible»*. `firmas-contrato.md` §10.3 lo declaraba inofensivo
  («no produce falso positivo — `.pcd` no está en la tabla») y la medida dice
  que sí: el falso positivo no lo fabricaba la TABLA, lo fabricaba la CATEGORÍA.

* **La ventana de DECISIÓN no se ensancha.** Se lee más (`_NCAB_LARGO`) pero
  las heurísticas siguen viendo 512 bytes. Si alguien ensancha `_NCAB`, la
  heurística de texto del final de `firma_real` se endurece y mueve
  clasificaciones que nadie ha pedido mover: hay una prueba que lo fija.

* **El SITIO de `FIRMAS_LARGAS` importa**: después de `FIRMAS` (un literal del
  byte 0, curado con el censo, sigue mandando) y antes de los predicados (el de
  audio MPEG es justo el que se traga hoy un PCD entero).

* **El defecto de la trampa 48, buscado en todo el paquete y sobre el AST.**
  `EXT_FAMILIA` se pobló durante meses con los CARACTERES de una cadena y nadie
  lo vio porque el recuento cuadraba. Aquí se comprueba que no queda ninguna
  tabla más con esa forma —con un **control positivo**, porque un «no detecta
  nada» sin control no significa nada (trampa 36)— y se publican **el tamaño y
  dos elementos** de cada tabla que decide el punto 1, que es lo que la trampa
  48 pide y lo que un `len()` solo no da.

**Ninguna prueba de este fichero usa la GPU, ni un motor externo, ni la red.**
Los ficheros de PICT y de PCD se fabrican byte a byte a partir del censo de tres
semillas de `bench/salidas-firmas-cierre/muestra_pict_pcd.json`, así que son
deterministas y no dependen de que `magick` esté instalado.
"""
import ast
import os
import sys
import tempfile
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from filex import verificador as V  # noqa: E402


# --------------------------------------------------------------------------
# Fixtures: los bytes REALES que escribió `magick`, no una lectura de la
# especificación. Salen del censo de tres semillas (§2.1 del informe).
# --------------------------------------------------------------------------

def bytes_pict(alto=128, ancho=192, relleno=b"\x81\x03"):
    """PICT v2 tal y como lo escribe ImageMagick 7.1.2.

    512 B de cabecera de aplicación a cero, 2 B de tamaño heredado (0x0200),
    8 B de rectángulo, y en el 522 el opcode de versión (`0011 02FF`) seguido
    del de cabecera (`0C00`).
    """
    cab = b"\x00" * 512
    cab += b"\x02\x00"                                  # 512: tamaño heredado
    cab += b"\x00\x00\x00\x00"                          # 514: top, left
    cab += alto.to_bytes(2, "big") + ancho.to_bytes(2, "big")   # 518: bottom, right
    cab += b"\x00\x11\x02\xff\x0c\x00"                  # 522: EL MARCADOR
    cab += b"\xff\xfe\x00\x00\x00\x48\x00\x00\x00\x48"  # 528: resolución
    return cab + relleno * 900


def bytes_pcd():
    """Photo CD: 2 KB de relleno `0xFF`/`0x0E` y `PCD_IPI` en el 0x800.

    El relleno importa: es lo que hace que hoy salga `mpegaudio` —`0xFF 0xFF`
    pasa el `FF Ex` y los bits de capa valen 0b11, que en ADTS son 0—.
    """
    cab = bytearray(b"\xff" * 32 + b"\x0e" * 4 + b"\x00" * 12)
    cab += b"\x00" * (2048 - len(cab))
    cab += b"PCD_IPI\x06"
    cab += b"\x00" * 512
    return bytes(cab)


class _ConFicheros(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="f2-firmas-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.d, ignore_errors=True)

    def escribe(self, nombre, datos):
        p = os.path.join(self.d, nombre)
        with open(p, "wb") as fh:
            fh.write(datos)
        return p


# --------------------------------------------------------------------------
# 1. Los dos accionables de la deuda de firmas
# --------------------------------------------------------------------------

class MarcadoresMasAllaDel512(_ConFicheros):
    """Sin el arreglo estas cinco fallan; con él pasan."""

    def test_el_marcador_de_PICT_esta_en_el_byte_522(self):
        p = self.escribe("m.pict", bytes_pict())
        self.assertEqual(V.firma_real(p), "pict")

    def test_el_marcador_de_PCD_esta_en_el_0x800(self):
        p = self.escribe("m.pcd", bytes_pcd())
        self.assertEqual(V.firma_real(p), "pcd")

    def test_un_PCD_ya_NO_se_clasifica_como_audio_MPEG(self):
        # La medida de `firmas-contrato.md` §10.3, reproducida antes de tocar
        # nada: con la ventana de 512 el relleno 0xFF pasa el predicado `FF Ex`.
        p = self.escribe("m.pcd", bytes_pcd())
        self.assertNotEqual(V.firma_real(p), "mpegaudio")

    def test_las_cuatro_extensiones_pasan_a_evaluado(self):
        for ext, esperado in ((".pict", "pict"), (".pct", "pict"),
                              (".pcd", "pcd"), (".pcds", "pcd")):
            with self.subTest(ext=ext):
                self.assertEqual(V.punto1_estado("x" + ext), "evaluado")
                self.assertIn(esperado, V.EXT_A_FIRMAS["." + ext.lstrip(".")])

    def test_el_contrato_sobre_un_PCD_legitimo_NO_dispara_fallo(self):
        """El falso positivo que `firmas-contrato.md` §10.3 declaró benigno.

        No lo fabricaba la tabla de extensiones —`.pcd` no estaba en ella— sino
        la CATEGORÍA: con firma `mpegaudio` la sonda lo lleva a `_mp3`, y de ahí
        sale `G4 fallo: duración nula o ilegible` sobre una salida perfectamente
        buena. Es la trampa 58: el hecho era cierto y la consecuencia, no.
        """
        p = self.escribe("m.pcd", bytes_pcd())
        r = V.verificar(p, {"destino": "pcd", "params": {}},
                        censo={"antes": {}, "despues": {}})
        fallos = [h for h in r["hallazgos"] if h["severidad"] == "fallo"]
        self.assertEqual(fallos, [], "un PCD legítimo no puede dar `fallo`")
        self.assertNotEqual(r["veredicto"], "fallo")


# --------------------------------------------------------------------------
# 2. Lo que el arreglo NO puede romper
# --------------------------------------------------------------------------

class LosOtrosDosQueElDatoDejaAccionables(_ConFicheros):
    """`firmas-contrato.md` §3.2 declaraba los doce «cada uno con una razón
    medida para no estar». Dos de esas razones no aguantan el dato del propio
    censo de F1, y las dos se corrigen aquí."""

    def test_3DS_su_marcador_de_dos_bytes_es_AUTOVALIDANTE(self):
        """*«su marcador son dos bytes, `MM`, que chocan con el `MM\\x00*` de
        TIFF. Añadirlo compraría un formato y arriesgaría todos los TIFF»*.

        El chunk principal 0x4D4D declara la longitud TOTAL del fichero: las dos
        muestras de assimp del censo dicen 565 y 517 y pesan 565 y 517.
        """
        cuerpo = b"\x3d\x3d" + b"\x00" * 100
        datos = b"MM" + (6 + len(cuerpo)).to_bytes(4, "little") + cuerpo
        p = self.escribe("m.3ds", datos)
        self.assertEqual(V.firma_real(p), "3ds")
        self.assertEqual(V.punto1_estado(p), "evaluado")

    def test_3DS_con_la_longitud_que_NO_cuadra_no_es_un_3DS(self):
        # La mitad que hace que esto no sea un marcador de dos bytes.
        datos = b"MM" + (999999).to_bytes(4, "little") + b"\x00" * 100
        p = self.escribe("m.3ds", datos)
        self.assertNotEqual(V.firma_real(p), "3ds")

    def test_un_TIFF_big_endian_NO_se_convierte_en_3DS(self):
        # La otra mitad: TIFF es un literal de FIRMAS y se resuelve antes.
        datos = b"MM\x00*" + b"\x00" * 200
        p = self.escribe("m.tif", datos)
        self.assertEqual(V.firma_real(p), "tiff")

    def test_un_texto_que_empieza_por_MM_sigue_siendo_texto(self):
        p = self.escribe("m.txt", b"MMemoria del proyecto\nlinea dos\n")
        self.assertEqual(V.firma_real(p), "texto")

    def test_ROCKET_EBOOK_no_es_un_marcador_de_dos_a_seis_bytes(self):
        """*«marcadores de 2 a 6 bytes de formatos con un solo adaptador: mucho
        riesgo de colisión por muy poca demanda»*.

        Las dos muestras de Calibre comparten **28 bytes**, y los diez primeros
        son `B0 0C B0 0C 02 00` más el literal `NUVO`.
        """
        datos = b"\xb0\x0c\xb0\x0c\x02\x00NUVO" + b"\x00" * 200
        p = self.escribe("m.rb", datos)
        self.assertEqual(V.firma_real(p), "rocketbook")
        self.assertEqual(V.punto1_estado(p), "evaluado")


class LosDiecisieteDelBannerDelEscritor(_ConFicheros):
    """C28. `firmas-contrato.md` §10.1 propone atacarlos con **un segundo
    escritor por formato**, y no hay: **0 de 17** tienen un segundo escritor
    entre los 20 adaptadores de esta máquina y del contenedor. Lo que sí hay es
    el dato de cada prefijo, y con él la clase se parte en cuatro."""

    def test_los_cinco_de_diapositivas_de_pandoc_son_HTML(self):
        # `<section id="` / `<div id="`: un FRAGMENTO de HTML, que es justo lo
        # que la excepción 5 de F1 resolvió para `.html`.
        for ext in (".revealjs", ".s5", ".slidy", ".slideous", ".dzslides"):
            with self.subTest(ext=ext):
                self.assertEqual(V.punto1_estado("x" + ext), "familia")

    def test_chunkedhtml_NO_es_texto_es_un_ZIP(self):
        p = self.escribe("m.chunkedhtml",
                         b"PK\x03\x04\x14\x00\x00\x00\x00\x00" + b"\x00" * 100)
        self.assertEqual(V.firma_real(p), "zip")
        self.assertEqual(V.punto1_estado(p), "evaluado")

    def test_tres_marcadores_ya_estaban_en_la_sonda_y_faltaba_la_fila(self):
        """`#FIG `, `GIMP Palette` y `solid ` llevaban en `MARCAS_TEXTO` desde
        que se escribió la tabla: `firma_real` acertaba y el punto 1 salía
        `sin_vocabulario` porque ninguna extensión los aceptaba."""
        for nombre, cuerpo, firma in (
                ("m.xfig", b"#FIG 3.2\n#created by potrace 1.16\n", "xfig"),
                ("m.gpl", b"GIMP Palette\nName: prueba\n#\n", "gimp_paleta"),
                ("m.stl", b"solid AssimpScene\n facet normal 0 0 1\n", "stl_ascii")):
            with self.subTest(nombre=nombre):
                p = self.escribe(nombre, cuerpo)
                self.assertEqual(V.firma_real(p), firma)
                self.assertEqual(V.punto1_estado(p), "evaluado")

    def test_los_cuatro_que_SI_son_banner_se_declaran_no_aplica(self):
        # `# File produced by Open Asset Import Library` es un comentario del
        # escritor. Decir `no_aplica` es la respuesta honesta; dejarlo
        # `sin_vocabulario` decía que era deuda nuestra, y no lo es.
        for ext in (".obj", ".objnomtl", ".pbrt", ".pov", ".ftxt"):
            with self.subTest(ext=ext):
                self.assertEqual(V.punto1_estado("x" + ext), "no_aplica")
                self.assertIn(ext, V.EXT_SIN_FIRMA)

    def test_dos_de_los_56_no_necesitaban_ningun_CORPUS(self):
        """El pendiente propone cerrar «los que ningún motor escribe» con el
        corpus FATE (~1 GB). De 56, **21** fallaron por la INVOCACIÓN, no por
        falta de motor, y el `rc` de cada celda lo dice: `AVERROR_EXPERIMENTAL`
        pide `-strict -2` y `EINVAL` pide una geometría o un perfil válidos.
        Escritos con dos semillas, `dts` da 20 bytes de prefijo común y `dnxhd`
        64 — sin descargar nada."""
        p = self.escribe("m.dts", b"\x7f\xfe\x80\x01" + b"\x00" * 100)
        self.assertEqual(V.firma_real(p), "dts")
        self.assertEqual(V.punto1_estado(p), "evaluado")
        q = self.escribe("m.dnxhd", b"\x00\x00\x02\x80\x01\x01\x80\xa0" + b"\x00" * 100)
        self.assertEqual(V.firma_real(q), "dnxhd")

    def test_ninguno_de_los_diecisiete_se_queda_en_sin_vocabulario(self):
        los17 = (".assjson .chunkedhtml .cip .dzslides .ftxt .gpl .hpgl .obj "
                 ".objnomtl .pbrt .pov .revealjs .s5 .slideous .slidy .stl "
                 ".xfig").split()
        self.assertEqual(len(los17), 17)
        quedan = [e for e in los17 if V.punto1_estado("x" + e) == "sin_vocabulario"]
        self.assertEqual(quedan, [])


class LaVentanaDeDecisionSigueSiendoDe512(_ConFicheros):

    def test_NCAB_no_se_ensancha(self):
        self.assertEqual(V._NCAB, 512)
        self.assertGreater(V._NCAB_LARGO, V._NCAB)

    def test_un_texto_con_un_byte_de_control_en_el_700_sigue_siendo_texto(self):
        """El motivo por el que la ventana de decisión no se ensancha.

        La heurística de texto exige que TODOS los bytes de la ventana sean
        imprimibles. Con 512 este fichero es texto; con 2056 dejaría de serlo,
        y eso movería clasificaciones que nadie ha pedido mover.
        """
        p = self.escribe("m.txt", b"a" * 600 + b"\x00" + b"b" * 600)
        self.assertEqual(V.firma_real(p), "texto")

    def test_un_literal_del_byte_0_manda_sobre_un_marcador_largo(self):
        """El SITIO de `FIRMAS_LARGAS` en `firma_real`, fijado por una prueba.

        Un JPEG que por casualidad lleve `PCD_IPI` en el 0x800 sigue siendo un
        JPEG: los literales curados del byte 0 se prueban antes.
        """
        datos = bytearray(b"\xff\xd8\xff\xe0" + b"\x00" * 2044)
        datos[2048:2055] = b"PCD_IPI"
        p = self.escribe("m.jpg", bytes(datos))
        self.assertEqual(V.firma_real(p), "jpeg")

    def test_un_fichero_mas_corto_que_la_ventana_larga_no_revienta(self):
        p = self.escribe("m.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 20)
        self.assertEqual(V.firma_real(p), "png")
        vacio = self.escribe("v.bin", b"")
        self.assertEqual(V.firma_real(vacio), "vacio")

    def test_un_PCD_truncado_antes_del_marcador_no_se_llama_PCD(self):
        p = self.escribe("m.pcd", bytes_pcd()[:2000])
        self.assertNotEqual(V.firma_real(p), "pcd")


# --------------------------------------------------------------------------
# 3. La trampa 48, buscada en todo el paquete — sobre el AST y con control
# --------------------------------------------------------------------------

class NingunaTablaMasSeConstruyeSobreCaracteres(unittest.TestCase):
    """*Cuando publiques el tamaño de una tabla, publica dos elementos de ella.*

    `EXT_FAMILIA` recorría los CARACTERES de su cadena por un `.split()` que
    faltaba, y el nivel de familia entero fue código muerto durante meses porque
    el RECUENTO cuadraba. La trampa 48 cerró esa tabla; **nadie había mirado si
    quedaban más**. Esto lo mira, y sobre el AST (trampa 42).
    """

    MODULOS = ("verificador", "formatos", "motores", "invocacion",
               "motor_contenedor", "huella", "grafo", "nucleo")

    # La forma EXACTA que tenía `EXT_FAMILIA`. Es el control positivo: sin él,
    # el «0 sospechas» de abajo no significa nada (trampa 36).
    CONTROL = ("T = set()\n"
               "for _n in (\"csv json yaml yml toml txt text md markdown\"):\n"
               "    T.add('.' + _n)\n")

    @staticmethod
    def _es_split(n):
        return (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr in ("split", "splitlines"))

    @classmethod
    def _parten(cls, arbol):
        """Funciones del módulo que hacen `.split()` por dentro.

        Sin seguir este nivel de llamada el detector acusa a `EXT_A_FIRMAS`, que
        sí parte —dentro del ayudante `_ext`— y calla la que no.
        """
        return {n.name for n in ast.walk(arbol)
                if isinstance(n, ast.FunctionDef)
                and any(cls._es_split(c) for c in ast.walk(n)
                        if isinstance(c, ast.Call))}

    @classmethod
    def sospechas(cls, fuente, nombre="<mem>"):
        arbol = ast.parse(fuente, nombre)
        parten = cls._parten(arbol)
        fuera = []
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.For) or cls._es_split(nodo.iter):
                continue
            it = nodo.iter
            if isinstance(it, ast.Constant) and isinstance(it.value, str):
                fuera.append((nombre, nodo.lineno, "cadena_pelada"))
                continue
            if isinstance(it, (ast.Tuple, ast.List)):
                cads = [c.value for c in ast.walk(it)
                        if isinstance(c, ast.Constant)
                        and isinstance(c.value, str)
                        and " " in c.value and len(c.value) > 12]
                if not cads:
                    continue
                parte = False
                for c in ast.walk(nodo):
                    if not isinstance(c, ast.Call):
                        continue
                    if cls._es_split(c) or (isinstance(c.func, ast.Name)
                                            and c.func.id in parten):
                        parte = True
                        break
                if not parte:
                    fuera.append((nombre, nodo.lineno, "tupla_sin_split"))
        return fuera

    def test_CONTROL_el_detector_encuentra_la_forma_historica(self):
        # Si esto falla, el cero de la prueba siguiente es mudo.
        self.assertEqual(len(self.sospechas(self.CONTROL, "control")), 1)

    def test_el_detector_NO_acusa_a_EXT_A_FIRMAS_que_si_parte(self):
        # El otro lado del control: un detector que marca la tabla buena es
        # ruido, y el ruido se acaba desactivando.
        src = ("def _ext(n, f):\n    return {'.'+x: set(f) for x in n.split()}\n"
               "T = {}\n"
               "for _n, _f in ((\"png png8 png24 apng jpg jpeg\", {'png'}),):\n"
               "    T.update(_ext(_n, _f))\n")
        self.assertEqual(self.sospechas(src, "bueno"), [])

    def test_ningun_modulo_de_filex_tiene_ese_defecto(self):
        malos = []
        for m in self.MODULOS:
            p = os.path.join(RAIZ, "filex", m + ".py")
            if not os.path.exists(p):
                continue
            with open(p, encoding="utf-8") as fh:
                fuente = fh.read()
            # trampa 60: comparar/analizar una fuente exige que COMPILE.
            compile(fuente, p, "exec")
            malos += self.sospechas(fuente, m)
        self.assertEqual(malos, [], "hay una tabla más con el defecto de la 48")


class LasTablasSePublicanConTamanoYConElementos(_ConFicheros):
    """Un `len()` es un control de integridad muy débil, y aquí fue peor que
    ninguno porque dio confianza. Cada tabla que decide el punto 1 se fija con
    su tamaño **y con dos elementos suyos**."""

    def test_FIRMAS_LARGAS(self):
        self.assertEqual(len(V.FIRMAS_LARGAS), 2)
        self.assertIn((522, b"\x00\x11\x02\xff\x0c\x00", "pict"), V.FIRMAS_LARGAS)
        self.assertIn((2048, b"PCD_IPI", "pcd"), V.FIRMAS_LARGAS)

    def test_EXT_FAMILIA_sigue_teniendo_extensiones_y_no_caracteres(self):
        # 42 tras la trampa 48, + 9 de C28 (los cinco de diapositivas de pandoc,
        # `assjson`, `hpgl`, `cip` y `fbxa`).
        self.assertEqual(len(V.EXT_FAMILIA), 51)
        self.assertIn(".csv", V.EXT_FAMILIA)
        self.assertIn(".gltf", V.EXT_FAMILIA)
        self.assertIn(".revealjs", V.EXT_FAMILIA)
        self.assertEqual([e for e in V.EXT_FAMILIA if len(e) < 3], [])

    def test_las_firmas_HUERFANAS_estan_acotadas(self):
        """Nombres que `firma_real` sabe devolver y que ninguna extensión acepta.

        Eran **seis**, y tres de ellas —`xfig`, `gimp_paleta`, `stl_ascii`— son
        justo tres de los diecisiete «banner del escritor» de C28: el marcador
        llevaba meses en `MARCAS_TEXTO` y lo que faltaba era la fila de
        `EXT_A_FIRMAS`. Quedan tres, y ninguna es destino declarado por ningún
        adaptador de ConvertX, así que no hay muestra con la que censarlas.
        """
        aceptadas = set()
        for fs in V.EXT_A_FIRMAS.values():
            aceptadas |= set(fs)
        for n in ("xfig", "gimp_paleta", "stl_ascii", "pict", "pcd", "3ds",
                  "rocketbook"):
            with self.subTest(firma=n):
                self.assertIn(n, aceptadas)

    def test_ninguna_extension_espera_una_firma_INALCANZABLE(self):
        """El control de integridad por el otro lado: una extensión que acepta
        un nombre que la sonda no sabe producir es una entrada muerta, y una
        entrada muerta pasa desapercibida igual que pasó `EXT_FAMILIA`."""
        posibles = {x[2] for x in V.FIRMAS} | {x[2] for x in V.FIRMAS_LARGAS}
        posibles |= set(V.MARCAS_FTYP.values()) | {x[1] for x in V.MARCAS_TEXTO}
        posibles |= set(V.MIME_ZIP.values()) | {x[1] for x in V.OOXML}
        # N4/N22: `mobi` estaba en la lista literal de abajo porque el despacho
        # del byte 60 de PalmDB era una TUPLA en el cuerpo de `firma_real`, no
        # una tabla. Ahora es `MARCAS_PALMDB` y se deriva, que es justo lo que
        # esta prueba defiende: una entrada literal es una entrada que se
        # queda atrás sola. (Único cambio de N4 en este fichero.)
        posibles |= set(V.MARCAS_PALMDB.values())
        posibles |= {"pnm", "pam", "pfm", "pcx", "mpegts", "m2ts", "flujo_es",
                     "adts", "mpegaudio", "texto", "xml", "html", "svg", "3ds",
                     "webp", "wav", "avi", "midi", "riff", "wave64", "aiff",
                     "iff", "isobmff", "zip", "cfb"}
        aceptadas = set()
        for fs in V.EXT_A_FIRMAS.values():
            aceptadas |= set(fs)
        self.assertEqual(sorted(aceptadas - posibles), [])

    def test_las_cuatro_extensiones_nuevas_estan_y_apuntan_a_lo_medido(self):
        self.assertEqual(V.EXT_A_FIRMAS[".pict"], {"pict"})
        self.assertEqual(V.EXT_A_FIRMAS[".pct"], {"pict"})
        self.assertEqual(V.EXT_A_FIRMAS[".pcd"], {"pcd"})
        self.assertEqual(V.EXT_A_FIRMAS[".pcds"], {"pcd"})
        # y ninguna se quedó también en la tabla de «no tiene marcador»
        for e in (".pict", ".pct", ".pcd", ".pcds"):
            self.assertNotIn(e, V.EXT_SIN_FIRMA)

    def test_los_cuatro_falsos_positivos_del_CONTENEDOR(self):
        """C30. La prueba ancha local da 0 de 345 y **dentro del contenedor
        aparecen cuatro**, porque el vocabulario se censó con ImageMagick y
        `ffmpeg` y ahí escriben `vips`, `graphicsmagick`, pandoc e inkscape."""
        # 1. el magico de VIPS es de ENDIANNESS y la tabla traia media
        self.assertIn((0, b"\x08\xf2\xa6\xb6", "vips"), V.FIRMAS)
        self.assertIn((0, b"\xb6\xa6\xf2\x08", "vips"), V.FIRMAS)
        # 2. GraphicsMagick escribe `id=MagickCache`, no `id=MagickPixelCache`
        self.assertIn((0, b"id=MagickCache", "mpc"), V.FIRMAS)
        self.assertIn((0, b"id=MagickPixelCache", "mpc"), V.FIRMAS)
        # 4. `.mat` son DOS formatos: MATLAB 5.0 binario y la matriz ASCII de vips
        self.assertEqual(V.EXT_A_FIRMAS[".mat"], {"mat", "texto"})

    def test_el_PCX_sin_comprimir_de_GraphicsMagick(self):
        """El tercero: el predicado exigía `cab[2] == 1` (RLE) y GM escribe PCX
        sin comprimir. La codificación es un campo, no parte del marcador."""
        p = self.escribe("m.pcx", b"\x0a\x05\x00\x08" + b"\x00" * 200)
        self.assertEqual(V.firma_real(p), "pcx")
        p2 = self.escribe("m2.pcx", b"\x0a\x05\x01\x08" + b"\x00" * 200)
        self.assertEqual(V.firma_real(p2), "pcx")
        # y no se afloja de más: la versión y los bits siguen acotados
        p3 = self.escribe("m3.pcx", b"\x0a\x09\x00\x03" + b"\x00" * 200)
        self.assertNotEqual(V.firma_real(p3), "pcx")

    def test_pict_y_pcd_tienen_categoria_para_la_sonda_por_subproceso(self):
        # Sin esto, el motor `subproceso` las dejaría sin categoría y el punto 3
        # se declararía cubierto sin haber mirado nada.
        self.assertEqual(V.CAT_POR_FIRMA["pict"], "imagen")
        self.assertEqual(V.CAT_POR_FIRMA["pcd"], "imagen")


if __name__ == "__main__":
    unittest.main()

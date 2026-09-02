"""Las dos deudas del docstring de `filex/sondeo.py`.

DEUDA 1 — el sondeo caduca al cambiar el CÓDIGO y nadie lo comprobaba.
    MEDIDO el 22/08: 21 aristas que un agente midió `nominal` quedaron obsoletas
    al arreglarse la sonda; al resondearlas, **20 de 21 salieron `real`**. El
    `build` protege contra cambiar de máquina; **nada protegía contra cambiar de
    código**. Aquí se prueba la huella que lo cierra.

DEUDA 2 — la suite lee estado del disco, así que no sería reproducible.
    **REFUTADA en magnitud, MEDIDO (`bench/deuda-sondeo.md` §4):** con
    `filex/sondeo/` apuntando a un directorio VACÍO —el grafo cae de 210 aristas
    `real` a 57, se mueven 153— la suite da **exactamente 123 passed, 6 skipped**,
    lo mismo que con el disco intacto. **0 de 129 pruebas dependen del estado del
    sondeo en disco.** Lo que sí la mueve es una perturbación que ningún sondeo
    real produce (declarar `nominal` las 215: 34 fallos). Aquí queda el cerrojo
    barato —`congelar()`— y la prueba de que sirve.

**Ninguna prueba de este fichero usa la GPU ni un motor externo.** La huella se
calcula sobre TEXTO; el sellado se comprueba sobre JSON.
"""

from __future__ import annotations

import ast
import copy
import json
import os
import sys
import tempfile
import textwrap
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filex import huella, sondeo  # noqa: E402
from filex.grafo import NOMINAL, REAL, SIN_SONDEAR, Arista  # noqa: E402
from filex.motores import FFmpeg, Ghostscript, ImageMagick  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --------------------------------------------------------------------------
# 1. La normalización: qué NO tiene que caducar el sondeo
# --------------------------------------------------------------------------


class NormalizacionAST(unittest.TestCase):
    """Una huella que caduca por todo se acaba desactivando, y entonces no
    protege nada. Estas cinco pruebas fijan el límite exacto."""

    BASE = textwrap.dedent('''
        """Un docstring de módulo."""
        UMBRAL = 10

        def decide(x):
            """Lo que hace."""
            # un comentario
            return x > UMBRAL
    ''')

    def test_un_comentario_NO_caduca_el_sondeo(self):
        otro = self.BASE.replace("# un comentario", "# un comentario con falta de hortografia")
        self.assertEqual(huella.de_fuente(self.BASE), huella.de_fuente(otro))

    def test_un_docstring_NO_caduca_el_sondeo(self):
        otro = self.BASE.replace("Lo que hace.", "Lo que hace, explicado mucho mejor.")
        self.assertEqual(huella.de_fuente(self.BASE), huella.de_fuente(otro))

    def test_mover_codigo_de_sitio_NO_caduca_el_sondeo(self):
        # `include_attributes=False`: el número de línea no entra en la huella.
        otro = self.BASE.replace("def decide", "\n\n\ndef decide")
        self.assertEqual(huella.de_fuente(self.BASE), huella.de_fuente(otro))

    def test_cambiar_una_CONSTANTE_si_caduca_el_sondeo(self):
        # `EXT_TABULARES` es exactamente esto: una constante de módulo nueva que
        # cambió el veredicto de 8 aristas (commit 9f99cae).
        otro = self.BASE.replace("UMBRAL = 10", "UMBRAL = 11")
        self.assertNotEqual(huella.de_fuente(self.BASE), huella.de_fuente(otro))

    def test_cambiar_el_CUERPO_si_caduca_el_sondeo(self):
        otro = self.BASE.replace("return x > UMBRAL", "return x >= UMBRAL")
        self.assertNotEqual(huella.de_fuente(self.BASE), huella.de_fuente(otro))

    def test_una_fuente_rota_no_tumba_el_registro(self):
        # Misma regla que un JSON ilegible o un binario que falta: se degrada,
        # no se revienta. Y tiene que dar una huella DISTINTA de cualquier
        # fuente válida, para que el sondeo no se aplique a ciegas.
        h = huella.de_fuente("def ( esto no compila")
        self.assertTrue(h.startswith("nocompila:"))


# --------------------------------------------------------------------------
# 2. La granularidad: un motor no caduca a los demás
# --------------------------------------------------------------------------


class GranularidadPorMotor(unittest.TestCase):
    """`verificador.py` tiene 5.241 líneas y `motores.py` lleva tres motores.
    Una huella de FICHERO haría que arreglar ImageMagick caducase ffmpeg."""

    FUENTE = textwrap.dedent('''
        class A:
            def orden(self):
                return ["a"]

        class B:
            def orden(self):
                return ["b"]
    ''')

    def test_tocar_una_clase_no_cambia_la_huella_de_la_otra(self):
        otra = self.FUENTE.replace('return ["b"]', 'return ["b", "-x"]')
        self.assertEqual(huella.de_clase_en_fuente(self.FUENTE, "A"),
                         huella.de_clase_en_fuente(otra, "A"))
        self.assertNotEqual(huella.de_clase_en_fuente(self.FUENTE, "B"),
                            huella.de_clase_en_fuente(otra, "B"))

    def test_la_huella_de_fichero_SI_los_confunde(self):
        # El control que justifica la decisión: sin granularidad, los dos caducan.
        otra = self.FUENTE.replace('return ["b"]', 'return ["b", "-x"]')
        self.assertNotEqual(huella.de_fuente(self.FUENTE), huella.de_fuente(otra))

    def test_los_tres_motores_nativos_tienen_huellas_distintas(self):
        hs = {huella.de_clase(c) for c in (ImageMagick, Ghostscript, FFmpeg)}
        self.assertEqual(len(hs), 3)

    def test_la_huella_de_una_clase_incluye_sus_BASES_dentro_de_filex(self):
        # `PandocEnContenedor` es un cascarón: la lógica vive en `_EnContenedor`.
        # Una huella que solo mirase el cuerpo de la subclase no vería el cambio.
        from filex.motor_contenedor import PandocEnContenedor
        cadena = huella.cadena_de_clase(PandocEnContenedor)
        nombres = [n for n, _ in cadena]
        self.assertIn("_EnContenedor", nombres)
        self.assertIn("Motor", nombres)
        self.assertNotIn("object", nombres)


# --------------------------------------------------------------------------
# 3. El alcance del contrato: el cierre de llamadas de `verificar()`
# --------------------------------------------------------------------------


class AlcanceDelContrato(unittest.TestCase):
    """La respuesta al «un cambio en la regla de fidelidad de audio no debería
    caducar las aristas de imagen»: **la fidelidad no decide la arista**, así
    que no entra en la huella. Y no hace falta un mapa a mano — el cierre de
    llamadas desde `verificar()` lo dice solo."""

    FUENTE = textwrap.dedent('''
        LIMITE = 3

        def _ayuda(x):
            return x + LIMITE

        def _lejos(x):
            return x * 99

        def verificar(x):
            return _ayuda(x)
    ''')

    def test_el_cierre_incluye_lo_que_se_llama(self):
        n = huella.nombres_alcanzados(self.FUENTE, ("verificar",))
        self.assertIn("_ayuda", n)
        self.assertIn("LIMITE", n)   # las constantes de módulo también deciden

    def test_el_cierre_EXCLUYE_lo_que_no_se_llama(self):
        n = huella.nombres_alcanzados(self.FUENTE, ("verificar",))
        self.assertNotIn("_lejos", n)

    def test_tocar_lo_no_alcanzado_no_caduca_el_sondeo(self):
        otra = self.FUENTE.replace("return x * 99", "return x * 100")
        self.assertEqual(huella.de_alcance(self.FUENTE, ("verificar",)),
                         huella.de_alcance(otra, ("verificar",)))

    def test_tocar_lo_alcanzado_SI_caduca_el_sondeo(self):
        otra = self.FUENTE.replace("LIMITE = 3", "LIMITE = 4")
        self.assertNotEqual(huella.de_alcance(self.FUENTE, ("verificar",)),
                            huella.de_alcance(otra, ("verificar",)))

    # ---- y ahora sobre el verificador de verdad ----

    def test_sobre_el_verificador_real_entra_el_contrato_y_no_la_fidelidad(self):
        with open(os.path.join(RAIZ, "filex", "verificador.py"), encoding="utf-8") as fh:
            src = fh.read()
        n = huella.nombres_alcanzados(src, huella.ENTRADAS_CONTRATO)
        for dentro in ("punto1_firma", "punto2_flujos", "punto3_propiedades",
                       "punto4_pedido", "punto5_escritura", "_pdf", "_datos",
                       "EXT_TABULARES", "firma_real", "sondear_en_proceso"):
            self.assertIn(dentro, n, f"{dentro} DECIDE la arista y quedó fuera")
        for fuera in ("fidelidad_audio", "fidelidad_video", "fidelidad_imagen",
                      "verificar_fidelidad", "main", "_imprimir"):
            self.assertNotIn(fuera, n, f"{fuera} NO decide la arista y entró")


# --------------------------------------------------------------------------
# 3 bis. Las TABLAS de datos que deciden un veredicto (trampa 49)
# --------------------------------------------------------------------------


class TablasDeDatos(unittest.TestCase):
    """*Las tablas que deciden un veredicto van en la huella, o la huella
    miente por omisión.*

    La frontera NO era «tabla contra llamada» —`_tabla()` registra los `Assign`
    desde el primer día, y `FIRMAS`, `MARCAS_FTYP` y `EXT_TABULARES` sí
    caducaban—: era **el sitio del valor**. Una tabla declarada vacía y poblada
    por un `for` de nivel superior se hasheaba vacía, y arreglar `EXT_FAMILIA`
    movió 3 de las 53 salidas del patrón oro sin caducar una sola arista.

    Toda prueba de este bloque va sobre el **AST** y sobre huellas, nunca sobre
    texto (trampa 42)."""

    FUENTE = textwrap.dedent('''
        TABLA = set()
        for _n in "csv json yaml".split():
            TABLA.add("." + _n)

        DICCIONARIO = {}
        for _k in ("a", "b"):
            DICCIONARIO[_k] = 1

        LEJOS = set()
        for _z in ("p", "q"):
            LEJOS.add(_z)

        def verificar(x):
            return x in TABLA and x in DICCIONARIO
    ''')

    def h(self, fuente):
        return huella.de_alcance(fuente, ("verificar",))

    def test_una_tabla_poblada_por_un_bucle_ESTA_en_el_cierre(self):
        n = huella.nombres_alcanzados(self.FUENTE, ("verificar",))
        self.assertIn("TABLA", n)
        self.assertIn("DICCIONARIO", n)

    def test_tocar_el_BUCLE_que_puebla_la_tabla_SI_caduca_el_sondeo(self):
        # Es la prueba que faltaba: el `Assign` inicial no cambia (`set()`
        # sigue siendo `set()`) y aun así la huella tiene que moverse.
        otra = self.FUENTE.replace('"csv json yaml"', '"csv json toml"')
        self.assertNotEqual(self.h(self.FUENTE), self.h(otra))

    def test_tocar_el_bucle_de_un_DICCIONARIO_tambien_caduca(self):
        otra = self.FUENTE.replace('DICCIONARIO[_k] = 1', 'DICCIONARIO[_k] = 2')
        self.assertNotEqual(self.h(self.FUENTE), self.h(otra))

    def test_el_bucle_de_lo_NO_alcanzado_sigue_sin_caducar_nada(self):
        # La granularidad no se pierde: un bucle de nivel superior que puebla
        # una tabla que `verificar()` no consulta no caduca nada.
        otra = self.FUENTE.replace('("p", "q")', '("p", "r")')
        self.assertEqual(self.h(self.FUENTE), self.h(otra))

    def test_el_ORDEN_de_los_bucles_importa(self):
        # `EXT_SIN_FIRMA` se llena en un bucle y se poda en el siguiente:
        # permutarlos cambia la tabla, así que tiene que cambiar la huella.
        src = textwrap.dedent('''
            T = {"a": 1}
            for _ in (0,):
                T["b"] = 2
            for _ in (0,):
                T.pop("a", None)

            def verificar(x):
                return T
        ''')
        ls = textwrap.dedent(src).strip("\n").split("\n")
        permutado = "\n".join(ls[:1] + ls[3:5] + ls[1:3] + ls[5:])
        # Un `SyntaxError` daría `nocompila:…`, que también es distinto: la
        # prueba pasaría por la razón equivocada (trampa 38). Se comprueba que
        # las dos fuentes COMPILAN antes de comparar.
        for f in (src, permutado):
            ast.parse(textwrap.dedent(f))
        self.assertNotEqual(huella.de_alcance(src, ("verificar",)),
                            huella.de_alcance(permutado, ("verificar",)))

    # ---- y ahora sobre el verificador de verdad ----

    #: Las cinco que nombra la trampa 49, más la que el docstring de
    #: `deuda-sondeo.md` sec.2.3 daba por cubierta. Se muta un elemento REAL de
    #: cada una: un recuento correcto no prueba un contenido correcto
    #: (trampa 48), y una tabla que existe no prueba una tabla que se hashea.
    MUTACIONES = [
        ("EXT_FAMILIA", 'EXT_FAMILIA.add("." + _n)',
         'EXT_FAMILIA.add(".zz" + _n)'),
        ("EXT_A_FIRMAS", "EXT_A_FIRMAS.update(_ext(_n, _f))",
         "EXT_A_FIRMAS.update(_ext(_n, _f)) or None"),
        ("EXT_SIN_FIRMA", 'EXT_SIN_FIRMA.setdefault("." + _e, _mot)',
         'EXT_SIN_FIRMA.setdefault(".zz" + _e, _mot)'),
        ("FIRMAS", 'b"\\x89PNG\\r\\n\\x1a\\n", "png"',
         'b"\\x89ZZZ\\r\\n\\x1a\\n", "png"'),
        ("MARCAS_FTYP", 'b"isom": "mp4"', 'b"zzzm": "mp4"'),
        ("EXT_TABULARES", '".csv", ".tsv"', '".zzz", ".tsv"'),
    ]

    def test_las_seis_tablas_reales_del_verificador_caducan_el_sondeo(self):
        with open(os.path.join(RAIZ, "filex", "verificador.py"),
                  encoding="utf-8") as fh:
            src = fh.read()
        base = huella.de_alcance(src, huella.ENTRADAS_CONTRATO)
        for nombre, viejo, nuevo in self.MUTACIONES:
            with self.subTest(tabla=nombre):
                self.assertIn(viejo, src,
                              f"{nombre}: la prueba se quedó obsoleta, no el "
                              f"código — busca el elemento en verificador.py")
                otro = src.replace(viejo, nuevo, 1)
                self.assertNotEqual(
                    base, huella.de_alcance(otro, huella.ENTRADAS_CONTRATO),
                    f"{nombre} DECIDE el veredicto de aristas reales y no "
                    f"mueve la huella: la huella miente por omisión")

    def test_las_seis_tablas_llevan_su_CONTENIDO_no_solo_su_tamano(self):
        # Trampa 48: `EXT_FAMILIA` tenía el recuento bueno y el contenido malo.
        # Dos elementos de cada una, comprobados de verdad.
        from filex import verificador as v
        for tabla, dos in ((v.EXT_FAMILIA, (".csv", ".gltf")),
                           (v.EXT_A_FIRMAS, (".png", ".mp4")),
                           (v.EXT_SIN_FIRMA, (".rgb", ".g4")),
                           (v.EXT_TABULARES, (".csv", ".ndjson")),
                           (v.MARCAS_FTYP, (b"isom", b"avif"))):
            for e in dos:
                self.assertIn(e, tabla)
        self.assertTrue(any(f[2] == "png" for f in v.FIRMAS))

    def test_el_componente_MOTOR_ve_las_constantes_de_MODULO(self):
        """El mismo agujero, en el otro componente: `MARGEN_TOPE` y
        `TIMEOUT_DENTRO` fijan el tope que corre DENTRO del contenedor, que
        decide el `rc` de toda arista documental, y no movían nada."""
        src = textwrap.dedent('''
            TOPE = 30

            def entorno():
                return {"A": "1"}

            class M:
                def orden(self):
                    return ["x", str(TOPE), entorno()["A"]]
        ''')
        base = huella.de_clase_en_fuente(src, "M")
        self.assertNotEqual(base, huella.de_clase_en_fuente(
            src.replace("TOPE = 30", "TOPE = 60"), "M"))
        self.assertNotEqual(base, huella.de_clase_en_fuente(
            src.replace('return {"A": "1"}', 'return {"A": "2"}'), "M"))
        # y el ruido sigue sin caducar
        self.assertEqual(base, huella.de_clase_en_fuente(
            src.replace("TOPE = 30", "TOPE = 30  # comentario"), "M"))

    def test_las_constantes_reales_de_los_motores_caducan_su_huella(self):
        for fichero, clase, viejo, nuevo in (
                ("motores.py", "ImageMagick", "HILOS = ", "HILOS = 999  #"),
                ("motor_contenedor.py", "_EnContenedor",
                 "MARGEN_TOPE = ", "MARGEN_TOPE = 999.0  #"),
                ("motor_contenedor.py", "_EnContenedor",
                 "TIMEOUT_DENTRO = ", "TIMEOUT_DENTRO = 999  #")):
            with self.subTest(constante=viejo.strip().rstrip("=")):
                with open(os.path.join(RAIZ, "filex", fichero),
                          encoding="utf-8") as fh:
                    src = fh.read()
                self.assertIn(viejo, src)
                self.assertNotEqual(
                    huella.de_clase_en_fuente(src, clase),
                    huella.de_clase_en_fuente(src.replace(viejo, nuevo, 1),
                                              clase))

    def test_el_cierre_de_una_clase_NO_se_traga_el_fichero_entero(self):
        """La granularidad por motor tiene que sobrevivir al arreglo: si el
        cierre de cada clase alcanzase todo, tocar ffmpeg caducaría
        ImageMagick, que es justo lo que la huella de FICHERO hacía mal."""
        with open(os.path.join(RAIZ, "filex", "motores.py"),
                  encoding="utf-8") as fh:
            src = fh.read()
        a = huella.nombres_alcanzados(src, ("ImageMagick",))
        self.assertNotIn("Ghostscript", a)
        self.assertNotIn("FFmpeg", a)
        self.assertIn("HILOS", a)


# --------------------------------------------------------------------------
# 4. `aplicar()`: la huella manda, y el legado no se tira
# --------------------------------------------------------------------------


def _aristas():
    return [Arista(origen="png", destino="webp", motor="m", build="b"),
            Arista(origen="png", destino="ico", motor="m", build="b")]


def _fichero(dir_, motor, cuerpo):
    with open(os.path.join(dir_, f"{motor}.json"), "w", encoding="utf-8") as fh:
        json.dump(cuerpo, fh)


class AplicarConHuella(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="filex-huella-")
        self._viejo = sondeo._DIR
        sondeo._DIR = self.d
        sondeo.descongelar()
        self.h = {"motor": "aaaa", "invocacion": "bbbb", "contrato": "cccc"}
        self.base = {
            "motor": "m", "build": "b", "huella": self.h,
            "aristas": {"png>webp": {"estado": REAL, "ms": 100.0},
                        "png>ico": {"estado": NOMINAL, "motivo": "rc=1"}},
        }

    def tearDown(self):
        sondeo._DIR = self._viejo
        sondeo.descongelar()

    def test_con_la_huella_igual_SI_se_aplica(self):
        _fichero(self.d, "m", self.base)
        out = sondeo.aplicar("m", "b", _aristas(), huella_actual=self.h)
        self.assertEqual([a.estado for a in out], [REAL, NOMINAL])

    def test_con_la_huella_DISTINTA_no_se_aplica(self):
        _fichero(self.d, "m", self.base)
        otra = dict(self.h, motor="zzzz")
        out = sondeo.aplicar("m", "b", _aristas(), huella_actual=otra)
        self.assertEqual([a.estado for a in out], [SIN_SONDEAR, SIN_SONDEAR])

    def test_basta_UN_componente_distinto(self):
        # El contrato es global: si cambia, caduca aunque el motor no se toque.
        _fichero(self.d, "m", self.base)
        otra = dict(self.h, contrato="zzzz")
        out = sondeo.aplicar("m", "b", _aristas(), huella_actual=otra)
        self.assertEqual([a.estado for a in out], [SIN_SONDEAR, SIN_SONDEAR])

    def test_un_componente_que_el_fichero_NO_declara_no_lo_invalida(self):
        # Un sondeo escrito antes de que existiera un componente no se tira por
        # un campo que su autor no pudo escribir. Se compara lo declarado.
        cuerpo = copy.deepcopy(self.base)
        del cuerpo["huella"]["contrato"]
        _fichero(self.d, "m", cuerpo)
        out = sondeo.aplicar("m", "b", _aristas(), huella_actual=self.h)
        self.assertEqual([a.estado for a in out], [REAL, NOMINAL])

    def test_un_fichero_SIN_huella_se_aplica_pero_se_DECLARA_legado(self):
        # Degradar los cinco ficheros por prudencia costaría 153 aristas MEDIDAS
        # con este mismo código. Se aplica, y se dice — callarlo sería el agujero.
        cuerpo = copy.deepcopy(self.base)
        del cuerpo["huella"]
        _fichero(self.d, "m", cuerpo)
        out = sondeo.aplicar("m", "b", _aristas(), huella_actual=self.h)
        self.assertEqual([a.estado for a in out], [REAL, NOMINAL])
        self.assertIn("m", sondeo.diagnostico()["sin_huella"])

    def test_el_BUILD_sigue_mandando_aunque_la_huella_coincida(self):
        _fichero(self.d, "m", self.base)
        out = sondeo.aplicar("m", "OTRO_BUILD", _aristas(), huella_actual=self.h)
        self.assertEqual([a.estado for a in out], [SIN_SONDEAR, SIN_SONDEAR])

    def test_el_diagnostico_nombra_el_componente_que_caduco(self):
        _fichero(self.d, "m", self.base)
        sondeo.aplicar("m", "b", _aristas(), huella_actual=dict(self.h, motor="zzzz"))
        self.assertEqual(sondeo.diagnostico()["caducados"].get("m"), ["motor"])


# --------------------------------------------------------------------------
# 4 bis. `C43`: la huella es función del intérprete — «no comparable», no
#         «caducado»
# --------------------------------------------------------------------------


class AplicarConInterprete(unittest.TestCase):
    """Trampa 105: `ast.dump` no da la misma cadena entre versiones de
    Python, y bajo un intérprete distinto el sistema decía «caducado» donde
    debía decir «no comparable» — invitando a resellar a ciegas (trampa 61)
    o a resondear 215 aristas por un cambio que no ocurrió. La decisión del
    02/09: declarar el intérprete de sellado y negarse a comparar. Aquí se
    prueba la lógica de la guarda, inyectando valores — no hace falta
    cambiar de intérprete a mitad de una prueba para probar el ORDEN de las
    guardas."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="filex-interprete-")
        self._viejo = sondeo._DIR
        sondeo._DIR = self.d
        sondeo.descongelar()
        self.h = {"motor": "aaaa", "invocacion": "bbbb", "contrato": "cccc"}
        self.base = {
            "motor": "m", "build": "b", "huella": self.h,
            "interprete": "3.11.9",
            "aristas": {"png>webp": {"estado": REAL, "ms": 100.0},
                        "png>ico": {"estado": NOMINAL, "motivo": "rc=1"}},
        }

    def tearDown(self):
        sondeo._DIR = self._viejo
        sondeo.descongelar()

    def test_con_el_interprete_igual_y_la_huella_igual_SI_se_aplica(self):
        _fichero(self.d, "m", self.base)
        out = sondeo.aplicar("m", "b", _aristas(), huella_actual=self.h,
                             interprete_actual="3.11.9")
        self.assertEqual([a.estado for a in out], [REAL, NOMINAL])

    def test_con_el_interprete_DISTINTO_no_se_aplica_AUNQUE_LA_HUELLA_COINCIDA(self):
        # El caso que reproduce la trampa 105: mismo código (huella idéntica),
        # otro intérprete. No es una arista que cambió: es una que no se
        # puede comparar.
        _fichero(self.d, "m", self.base)
        out = sondeo.aplicar("m", "b", _aristas(), huella_actual=self.h,
                             interprete_actual="3.14.4")
        self.assertEqual([a.estado for a in out], [SIN_SONDEAR, SIN_SONDEAR])

    def test_el_interprete_distinto_se_declara_APARTE_de_caducados(self):
        # La afirmación central de C43: NO es «caducado». Nunca se llega a
        # comparar la huella, así que `caducados` se queda vacío para este
        # motor aunque la huella inyectada también difiera.
        _fichero(self.d, "m", self.base)
        sondeo.aplicar("m", "b", _aristas(), huella_actual=dict(self.h, motor="zzzz"),
                       interprete_actual="3.14.4")
        diag = sondeo.diagnostico()
        self.assertIn("m", diag["interprete_distinto"])
        self.assertNotIn("m", diag["caducados"])

    def test_un_fichero_SIN_interprete_se_aplica_pero_se_DECLARA_legado(self):
        # Misma regla de legado que `huella`: un sondeo sellado antes de que
        # existiera este campo no se tira por uno que su autor no pudo
        # escribir.
        cuerpo = copy.deepcopy(self.base)
        del cuerpo["interprete"]
        _fichero(self.d, "m", cuerpo)
        out = sondeo.aplicar("m", "b", _aristas(), huella_actual=self.h,
                             interprete_actual="3.14.4")
        self.assertEqual([a.estado for a in out], [REAL, NOMINAL])
        self.assertIn("m", sondeo.diagnostico()["sin_interprete"])

    def test_el_diagnostico_se_limpia_entre_pasadas(self):
        # Igual que `caducados`/`build_distinto`: no se acumula para siempre.
        _fichero(self.d, "m", self.base)
        sondeo.aplicar("m", "b", _aristas(), huella_actual=self.h,
                       interprete_actual="3.14.4")
        self.assertIn("m", sondeo.diagnostico()["interprete_distinto"])
        sondeo.aplicar("m", "b", _aristas(), huella_actual=self.h,
                       interprete_actual="3.11.9")
        self.assertNotIn("m", sondeo.diagnostico()["interprete_distinto"])


class InterpreteActual(unittest.TestCase):
    """Ronda 7: la granularidad bajó de mayor.menor.parche a mayor.menor,
    porque `.venv-mcp-filex` sella con 3.11.9 y el runner real resuelve a
    3.11.16 — el triple completo habría declarado el sellado "no comparable"
    en CADA ejecución de la CI. Sigue protegiendo la trampa 105 real (3.11
    frente a 3.14)."""

    def test_devuelve_mayor_punto_menor(self):
        import sys
        self.assertEqual(huella.interprete_actual(),
                         "%d.%d" % sys.version_info[:2])

    def test_NO_incluye_el_parche(self):
        # La afirmación central de esta ronda: dos parches de la misma menor
        # tienen que declararse iguales. No se puede fabricar un segundo
        # intérprete 3.11.x en esta máquina (§1 del informe), así que se
        # comprueba la FORMA de la cadena en vez del valor con dos binarios.
        self.assertEqual(huella.interprete_actual().count("."), 1)

    def test_es_una_cadena_no_vacia(self):
        self.assertTrue(huella.interprete_actual())


# --------------------------------------------------------------------------
# 5. El sellado: que el disco lleve la huella del código de AHORA
# --------------------------------------------------------------------------


class SelladoDelDisco(unittest.TestCase):
    """**Esta es la prueba que salda la deuda 1.** Si alguien toca
    `motores.py`, `invocacion.py` o el contrato de `verificador.py` y no
    resondea, aquí se entera — en vez de heredar en silencio 20 medidas falsas
    de 21, que es lo que pasó el 22/08."""

    def setUp(self):
        sondeo.descongelar()

    def test_los_ficheros_del_disco_llevan_huella(self):
        # Se mira el DISCO, no `diagnostico()`: ese acumula lo de la pasada y
        # dependería del orden en que corran las clases de este fichero.
        sin = []
        for n in sorted(os.listdir(sondeo._DIR)):
            if not n.endswith(".json"):
                continue
            if not (sondeo.cargar(n[:-5]).get("huella") or {}):
                sin.append(n)
        self.assertEqual(sin, [],
                         "hay sondeo sin sellar: se está aplicando sin protección")

    def test_ningun_motor_disponible_tiene_el_sondeo_caducado(self):
        from filex import motores
        malos = {}
        for cls in list(motores.MOTORES) + motores._descubrir():
            m = cls()
            d = sondeo.cargar(m.nombre)
            if not d or not d.get("huella"):
                continue
            faltan = huella.diferencias(d["huella"], huella.de_motor(m))
            if faltan:
                malos[m.nombre] = faltan
        self.assertEqual(malos, {}, (
            "el código que decide estas aristas cambió después de sondearlas: "
            "hay que RESONDEAR y volver a sellar, no editar la huella a mano"))

    def test_los_ficheros_del_disco_declaran_su_interprete_de_sellado(self):
        """`C43`: el sello lleva ahora un cuarto dato — con qué intérprete se
        calculó la huella de arriba —, o la comparación no significa nada."""
        sin = []
        for n in sorted(os.listdir(sondeo._DIR)):
            if not n.endswith(".json"):
                continue
            if not sondeo.cargar(n[:-5]).get("interprete"):
                sin.append(n)
        self.assertEqual(sin, [],
                         "hay sondeo sellado sin declarar su intérprete: "
                         "C43 no está cerrado sobre este fichero")

    def test_ningun_motor_disponible_es_no_comparable_bajo_este_interprete(self):
        """El criterio de aceptación duro de `C43`: **no puede caducar ni una
        de las aristas selladas**, ni tampoco declararse `interprete_distinto`
        —que sería el mismo daño con otro nombre—, corriendo la suite con el
        intérprete que las selló.

        **Se llama a `m.sondear()`, no a `sondeo.aplicar()` a mano** —
        corregido en la ronda 7—. La versión de la ronda 5 llamaba a
        `sondeo.aplicar(m.nombre, m.build, ...)` sobre un `cls()` recién
        creado, y `Motor.build` es una `@property` que depende de `ruta`/
        `version`, que solo rellena `sondear()`. Sin sondear, `m.build` vale
        el nombre pelado (`"imagemagick"`), nunca coincide con el `build`
        guardado (`"imagemagick 7.1.2-21"`), y `sondeo.aplicar()` **se para
        en la guarda del `build` antes de llegar siquiera al intérprete** —
        la prueba pasaba SIEMPRE, sin ejercer nunca la ruta que dice
        proteger. MEDIDO al arreglarlo (`bench/acuerdo-y-cruce.md` §1): con
        `sondear()` real, los CINCO motores caían en `interprete_distinto`
        antes del resondeo de esta ronda — la prueba vieja nunca lo habría
        visto. `sondear()` es exactamente la ruta que usan `motores.py` y
        `motor_contenedor.py` en producción."""
        from filex import motores
        sondeo.descongelar()
        vistos = 0
        for cls in list(motores.MOTORES) + motores._descubrir():
            m = cls()
            d = sondeo.cargar(m.nombre)
            if not d or not d.get("huella"):
                continue
            m.sondear()
            if not m.disponible:
                continue
            vistos += 1
            with self.subTest(motor=m.nombre):
                diag = sondeo.diagnostico()
                self.assertNotIn(m.nombre, diag["interprete_distinto"],
                                 "se declaró no comparable con SU PROPIO sello")
                self.assertNotIn(m.nombre, diag["caducados"])
        self.assertGreater(vistos, 0, "no se comprobó ningún motor sellado")


# --------------------------------------------------------------------------
# 6. `congelar()`: el cerrojo barato de la deuda 2
# --------------------------------------------------------------------------


class Congelar(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="filex-congelar-")
        self._viejo = sondeo._DIR
        sondeo._DIR = self.d
        sondeo.descongelar()
        _fichero(self.d, "m", {"motor": "m", "build": "b",
                               "aristas": {"png>webp": {"estado": REAL}}})

    def tearDown(self):
        sondeo._DIR = self._viejo
        sondeo.descongelar()

    def test_sin_congelar_el_disco_manda_a_mitad_de_pasada(self):
        # El mecanismo de la deuda 2, reproducido en 4 líneas.
        antes = sondeo.cargar("m")
        _fichero(self.d, "m", {"motor": "m", "build": "b",
                               "aristas": {"png>webp": {"estado": NOMINAL}}})
        self.assertNotEqual(antes["aristas"]["png>webp"]["estado"],
                            sondeo.cargar("m")["aristas"]["png>webp"]["estado"])

    def test_congelado_una_escritura_de_otro_agente_ya_no_entra(self):
        sondeo.congelar()
        antes = sondeo.cargar("m")
        _fichero(self.d, "m", {"motor": "m", "build": "b",
                               "aristas": {"png>webp": {"estado": NOMINAL}}})
        self.assertEqual(antes["aristas"]["png>webp"]["estado"],
                         sondeo.cargar("m")["aristas"]["png>webp"]["estado"])

    def test_congelar_no_inventa_lo_que_no_hay(self):
        sondeo.congelar()
        self.assertEqual(sondeo.cargar("no_existe_este_motor"), {})

    def test_quien_congela_no_puede_modificar_lo_congelado_por_accidente(self):
        # Se devuelve una copia: un motor que toquetee el dict que le dan no
        # puede corromper el de los demás.
        sondeo.congelar()
        sondeo.cargar("m")["aristas"]["png>webp"]["estado"] = "BASURA"
        self.assertEqual(sondeo.cargar("m")["aristas"]["png>webp"]["estado"], REAL)


if __name__ == "__main__":
    unittest.main()

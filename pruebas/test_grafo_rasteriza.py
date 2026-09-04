# -*- coding: utf-8 -*-
"""Una arista DECLARADA tiene que poder decir la verdad sobre si rasteriza.

Hasta el 2026-09-03 no podía: `_EnContenedor._DECLARADAS` era una tupla de
pares `(origen, destino)` y `_aristas()` construía las `Arista` **sin pasar
`rasteriza=`**, así que toda arista nacida de esa tabla salía con el
`default=False` de `grafo.Arista` —mintiera o no—. Y `sondeo.aplicar()` toma
`rasteriza=a.rasteriza` de la arista **que ya existe**, nunca del sondeo, así
que el valor falso sobrevivía a la medición: medir la arista no lo arreglaba.

Por eso `pptx→png` y `svg→png` llevaban desde el 02/09 medidas `real` en
`filex/sondeo/doc_libreoffice.json` y **fuera del grafo**, excluidas a mano con
el motivo escrito en el código.

Estas pruebas cubren las tres capas del arreglo, y la última es la única que
vale como criterio de aceptación: **que un camino que rasteriza pague su
penalización y uno que no, no.**

`bench/rasteriza-declaradas.md`.
"""
from __future__ import annotations

import ast
import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from filex import formatos, grafo, motores, sondeo  # noqa: E402
from filex.grafo import NOMINAL, REAL, SIN_SONDEAR, Arista, Grafo  # noqa: E402
from filex.motor_contenedor import _EnContenedor  # noqa: E402
from filex.motor_contenedor import (CalibreEnContenedor,  # noqa: E402
                                    LibreOfficeEnContenedor, PandocEnContenedor)

FUENTE_MOTOR_CONTENEDOR = os.path.join(RAIZ, "filex", "motor_contenedor.py")


# ---------------------------------------------------------------- la FORMA


class FormaDeLaTabla(unittest.TestCase):
    """La tabla se comprueba sobre el **AST**, no sobre el texto (trampa 42).

    Y el AST, no la clase importada, porque lo que hay que impedir es que
    alguien vuelva a escribir una tupla de pares: una tupla importada y un
    `dict` importado se comportan igual ante `in` y ante `for o, d in ...`, así
    que desde el objeto la regresión es **invisible**. Desde la fuente no.
    """

    @classmethod
    def setUpClass(cls):
        with open(FUENTE_MOTOR_CONTENEDOR, encoding="utf-8") as fh:
            cls.fuente = fh.read()
        # Trampa 60: una fuente que no compila hace pasar cualquier prueba de
        # forma que la recorra. Se comprueba antes de mirar nada.
        cls.arbol = ast.parse(cls.fuente)

    def _asignaciones(self) -> list:
        """Todo `_DECLARADAS = ...` del fichero, esté donde esté."""
        out = []
        for n in ast.walk(self.arbol):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name) and t.id == "_DECLARADAS":
                        out.append(n.value)
            elif (isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
                  and n.target.id == "_DECLARADAS" and n.value is not None):
                out.append(n.value)
        return out

    def test_hay_una_tabla_por_clase_mas_la_de_la_base(self):
        """Cuatro: la de `_EnContenedor` y las de los tres motores.

        No es cosmético: es el control de que esta prueba está mirando algo.
        Una sonda que no encuentra nada pasa igual que una que lo aprueba todo
        (trampa 66).
        """
        self.assertEqual(len(self._asignaciones()), 4)

    def test_toda__DECLARADAS_es_un_dict_y_no_una_tupla_de_pares(self):
        for v in self._asignaciones():
            self.assertIsInstance(
                v, ast.Dict,
                "`_DECLARADAS` volvió a ser una secuencia de pares: entonces "
                "`_aristas()` no tiene de dónde leer `rasteriza` y toda arista "
                "declarada vuelve a mentir con el `default=False`")

    def test_toda_entrada_declara_su_rasteriza_como_booleano_LITERAL(self):
        """Un literal, no una expresión: el valor tiene que leerse en la tabla.

        `("svg", "png"): rasteriza_de(...)` cumpliría el tipo y volvería a
        esconder la decisión en otro sitio, que es de lo que iba el defecto.
        """
        for v in self._asignaciones():
            for k, val in zip(v.keys, v.values):
                self.assertIsInstance(k, ast.Tuple)
                self.assertEqual(len(k.elts), 2)
                for e in k.elts:
                    self.assertIsInstance(e, ast.Constant)
                    self.assertIsInstance(e.value, str)
                self.assertIsInstance(val, ast.Constant)
                self.assertIsInstance(
                    val.value, bool,
                    "el valor de `_DECLARADAS` tiene que ser `True` o `False` "
                    "escrito: es lo único que obliga a quien añade una arista "
                    "a pronunciarse sobre si rasteriza")

    def test_el_bucle_de__aristas_lee_el_VALOR_y_no_solo_la_clave(self):
        """`for o, d in self._DECLARADAS` sigue funcionando sobre un `dict` y
        NO lee el valor. Es el modo de fallo silencioso que queda abierto una
        vez cambiada la forma de la tabla, y por eso se comprueba aparte."""
        fn = next(n for n in ast.walk(self.arbol)
                  if isinstance(n, ast.FunctionDef) and n.name == "_aristas"
                  and any(isinstance(x, ast.Attribute) and x.attr == "_DECLARADAS"
                          for x in ast.walk(n)))
        usos = [n for n in ast.walk(fn)
                if isinstance(n, ast.Attribute) and n.attr == "_DECLARADAS"]
        self.assertTrue(usos)
        for u in usos:
            padre = next((n for n in ast.walk(fn)
                          if isinstance(n, ast.Call) and n.func is not u
                          and isinstance(n.func, ast.Attribute)
                          and n.func.value is u), None)
            self.assertIsNotNone(
                padre, "`_aristas()` usa `_DECLARADAS` sin `.items()`: estaría "
                       "iterando solo las claves y el `rasteriza` volvería a "
                       "quedarse en el defecto")
            self.assertEqual(padre.func.attr, "items")


# ------------------------------------------------- que el valor LLEGUE y VIVA


class _Falso(_EnContenedor):
    """Un motor de laboratorio. No hereda de `Motor`: `_descubrir()` recoge
    toda subclase de `Motor` del módulo y ésta no debe aparecer en el
    registro."""

    dentro = "falso"
    nombre = "falso"
    version = "v0"
    #: Los motores de verdad heredan tambien de `motores.Motor`, de donde sale
    #: `build`. Aqui no, a proposito: heredar de `Motor` metaria este juguete
    #: en `motores._descubrir()` y con el en el grafo de produccion.
    build = "falso v0"
    _MEDIDAS = {("m", "n"): ("X01", 1.5, True)}
    _MUERTAS = {("p", "q"): ("X02",)}
    _DECLARADAS = {("a", "b"): True, ("c", "d"): False, ("m", "n"): False}


class ElValorLlegaALaArista(unittest.TestCase):
    """Hermético: `_aristas()` no necesita Docker ni sondeo."""

    def setUp(self):
        self.m = _Falso()
        self.por_par = {(a.origen, a.destino): a for a in self.m._aristas()}

    def test_una_declarada_que_rasteriza_sale_con_rasteriza_True(self):
        self.assertTrue(self.por_par[("a", "b")].rasteriza)

    def test_una_declarada_que_no_rasteriza_sale_con_rasteriza_False(self):
        self.assertFalse(self.por_par[("c", "d")].rasteriza)

    def test_las_declaradas_siguen_saliendo_SIN_SONDEAR(self):
        self.assertEqual(self.por_par[("a", "b")].estado, SIN_SONDEAR)

    def test_una_MEDIDA_gana_a_la_declarada_y_conserva_SU_rasteriza(self):
        """`("m","n")` está en las dos tablas con banderas opuestas. Manda la
        medida, que es la que se ejecutó."""
        a = self.por_par[("m", "n")]
        self.assertEqual(a.estado, REAL)
        self.assertTrue(a.rasteriza)

    def test_el_valor_SOBREVIVE_a_sondeo_aplicar(self):
        """El otro medio defecto: `sondeo.aplicar()` reconstruye la `Arista`
        con `rasteriza=a.rasteriza` **de la que ya existía**, nunca del fichero
        de sondeo. Con la tabla mintiendo, medir la arista NO la arreglaba —
        salía `real` y seguía diciendo que no rasteriza."""
        fichero = {"motor": "falso", "build": "falso v0",
                   "aristas": {"a>b": {"estado": REAL, "ms": 1234.0}}}
        original = sondeo.cargar
        sondeo.cargar = lambda _m: fichero
        try:
            fuera = sondeo.aplicar("falso", "falso v0", self.m._aristas())
        finally:
            sondeo.cargar = original
        a = next(x for x in fuera if (x.origen, x.destino) == ("a", "b"))
        self.assertEqual(a.estado, REAL)
        self.assertTrue(a.rasteriza,
                        "el sondeo borró la bandera: una arista medida `real` "
                        "que rasteriza volvería a entrar como si no")


class LasDosQueEstabanFuera(unittest.TestCase):
    """`pptx→png` y `svg→png`: el motivo por el que la tabla cambió de forma."""

    def test_estan_declaradas_y_declaran_que_rasterizan(self):
        for par in (("pptx", "png"), ("svg", "png")):
            self.assertIn(par, LibreOfficeEnContenedor._DECLARADAS)
            self.assertIs(LibreOfficeEnContenedor._DECLARADAS[par], True)

    def test_llegan_al_grafo_con_la_bandera_puesta(self):
        m = LibreOfficeEnContenedor()
        por_par = {(a.origen, a.destino): a for a in m._aristas()}
        for par in (("pptx", "png"), ("svg", "png")):
            self.assertTrue(por_par[par].rasteriza)

    def test_ninguna_otra_declarada_de_los_tres_motores_dice_que_rasteriza(self):
        """Auditoría de las tres tablas, MEDIDA en
        `bench/rasteriza-declaradas.md` §4: de las 38 aristas que ya estaban
        declaradas, **0 rasterizaban** —37 devuelven el centinela y una
        (`mobi→azw3`) va con sonda ciega—. Si alguien añade una que sí, tiene
        que decirlo aquí y remedirla, no colarla con el `False` de al lado."""
        mienten = []
        for cls in (LibreOfficeEnContenedor, PandocEnContenedor,
                    CalibreEnContenedor):
            for (o, d), rast in cls._DECLARADAS.items():
                if rast and (cls, o, d) not in (
                        (LibreOfficeEnContenedor, "pptx", "png"),
                        (LibreOfficeEnContenedor, "svg", "png")):
                    mienten.append((cls.__name__, o, d))
        self.assertEqual(mienten, [])


# --------------------------------------------- el criterio de ACEPTACIÓN


def _grafo_de_tablas() -> Grafo:
    """El grafo que declaran las CLASES, sin sondear y sin Docker.

    No es el grafo de producción —las declaradas van `SIN_SONDEAR` y el sondeo
    del disco no se superpone— y por eso mismo es reproducible en cualquier
    máquina: la discriminación del planificador se puede comprobar donde no hay
    ni un motor instalado.
    """
    g = Grafo()
    for cls in list(motores.MOTORES) + motores._descubrir():
        try:
            for a in cls()._aristas():
                g.añadir(a)
        except Exception:
            continue
    return g


def _pares_con_ruta_que_rasteriza(g: Grafo) -> list:
    """Pares `(origen, destino)` con destino que ADMITE TEXTO y para los que
    existe un camino que rasteriza.

    **El predicado es de CAMINO, no de arista, y esa diferencia ya costó una
    prueba muerta.** `pruebas/test_hito4.py` busca «una arista real que
    rasterice hacia un destino con texto» y se salta siempre, porque una arista
    que rasteriza ESCRIBE PÍXELES: su destino es `png`/`jpg`/`webp`/`tif`, que
    nunca admiten texto. Lo que la penalización castiga es un salto que
    rasteriza **en medio** de un camino cuyo DESTINO FINAL sí admite texto.
    """
    exts = sorted({a.origen for a in g.aristas} | {a.destino for a in g.aristas})
    textos = [d for d in exts
              if (formatos.formato(d) is not None and formatos.formato(d).texto)]
    fuera = []
    for o in exts:
        for d in textos:
            if o == d:
                continue
            dec = g.camino(o, d)
            if not dec.hay:
                continue
            raster = [c for c, _ in dec.rechazados if c.rasteriza]
            if dec.camino.rasteriza:
                raster.append(dec.camino)
            if raster:
                fuera.append((o, d, dec, raster))
    return fuera


class ElPlanificadorDistingue(unittest.TestCase):
    """El criterio de aceptación del encargo, y no es «la arista está en la
    tabla»: es **«un camino que rasteriza paga su penalización y uno que no,
    no»**.

    El par se busca EN VIVO. Un par fijo es lo que se rompió la ronda pasada:
    `svg→pdf` dejó de resolverse rasterizando en cuanto entró una vía mejor por
    LibreOffice, y la prueba que dependía de él se cayó sin que nada estuviera
    mal.
    """

    @classmethod
    def setUpClass(cls):
        cls.g = _grafo_de_tablas()
        cls.pares = _pares_con_ruta_que_rasteriza(cls.g)

    def test_hay_al_menos_un_par_que_ejercita_la_penalizacion(self):
        """La guarda que impide que el resto pase en vacío. Separa «no hay
        motores» de «hay motores y ningún par», que son dos cosas distintas
        (trampa 43); sobre el grafo de TABLAS la primera no puede ocurrir."""
        self.assertTrue(self.g.aristas, "el grafo de tablas salió vacío: no es "
                                        "que no haya par, es que no hay grafo")
        self.assertTrue(
            self.pares,
            "ningún par alcanza su destino de texto por una ruta que rasteriza: "
            "la penalización de +1000 no está gobernando nada y las pruebas de "
            "abajo pasarían en vacío")

    def test_el_camino_que_rasteriza_paga_la_penalizacion(self):
        for o, d, dec, raster in self.pares:
            for c in raster:
                with self.subTest(par=f"{o}>{d}", camino=" ".join(c.formatos)):
                    self.assertGreaterEqual(
                        c.coste, grafo.PENALIZACION_RASTERIZAR,
                        f"'{' '.join(c.formatos)}' rasteriza hacia '{d}', que "
                        f"admite texto, y no pagó los +1000")

    def test_el_que_NO_rasteriza_no_la_paga_y_es_el_elegido(self):
        vistos = 0
        for o, d, dec, _ in self.pares:
            if dec.camino.rasteriza:
                continue          # el caso del aviso; su prueba es la de abajo
            vistos += 1
            with self.subTest(par=f"{o}>{d}"):
                self.assertLess(
                    dec.camino.coste, grafo.PENALIZACION_RASTERIZAR,
                    "el camino elegido no rasteriza y aun así paga la "
                    "penalización: el coste no distingue")
        self.assertTrue(vistos, "ningún par tiene alternativa que no rasterice")

    def test_y_el_rechazo_se_EXPLICA_diciendo_que_rasteriza(self):
        """«Alcanzar es fácil, elegir bien no»: la mitad del criterio del hito
        1 es el motivo del rechazo, no el camino elegido."""
        for o, d, dec, _ in self.pares:
            if dec.camino.rasteriza:
                continue
            motivos = [m for c, m in dec.rechazados if c.rasteriza]
            with self.subTest(par=f"{o}>{d}"):
                self.assertTrue(motivos)
                self.assertTrue(all("rasteriza" in m for m in motivos), motivos)

    def test_si_el_UNICO_camino_rasteriza_hay_aviso_y_no_silencio(self):
        for o, d, dec, _ in self.pares:
            if not dec.camino.rasteriza:
                continue
            with self.subTest(par=f"{o}>{d}"):
                self.assertTrue(dec.aviso)
                self.assertIn("texto", dec.aviso)


class LaMentiraSeNOTA(unittest.TestCase):
    """El contrafactual, hecho prueba: si la bandera miente, el grafo deja de
    explicar rechazos que sí existen.

    MEDIDO sobre el grafo de producción (`bench/rasteriza-declaradas.md` §5):
    con `pptx→png` y `svg→png` en `False` no cambia ni un camino elegido —el
    coste por salto ya las descartaba— pero los rechazos explicados que citan
    una ruta que rasteriza caen de **18 a 13**. La consecuencia que el defecto
    prometía —elegir en silencio— no se materializa hoy; la que sí, es perder
    la explicación. Aquí se comprueba el mecanismo, que es lo que no depende de
    qué aristas haya hoy.
    """

    def test_apagar_la_bandera_reduce_los_rechazos_explicados(self):
        import dataclasses

        verdad = _grafo_de_tablas()
        objetivo = {("pptx", "png"), ("svg", "png")}
        mentira = Grafo()
        for a in verdad.aristas:
            if a.motor == "doc_libreoffice" and (a.origen, a.destino) in objetivo:
                a = dataclasses.replace(a, rasteriza=False)
            mentira.añadir(a)

        def explicados(g):
            out = set()
            for o, d, dec, _ in _pares_con_ruta_que_rasteriza(g):
                for c, m in dec.rechazados:
                    if c.rasteriza:
                        out.add((o, d, " ".join(c.formatos)))
            return out

        v, m = explicados(verdad), explicados(mentira)
        self.assertTrue(v - m,
                        "apagar la bandera de dos aristas que rasterizan no le "
                        "quitó al grafo ni una explicación: o las aristas no "
                        "están, o el coste ya no las mira")


if __name__ == "__main__":
    unittest.main()

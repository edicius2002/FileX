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

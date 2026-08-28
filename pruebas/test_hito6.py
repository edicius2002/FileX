"""Hito 6 — el sidecar de IA: admisión por VRAM, TTL, LRU y reciclado.

**Lo que estas pruebas NO hacen es cargar modelos.** El registro se ejercita con
un trabajador falso y con la VRAM y el reloj inyectados, porque una regla de
recurso que solo se puede ejercitar con la tarjeta delante es una regla sin
prueba: no correría en integración continua, no correría en una máquina sin GPU
y, sobre todo, **no se podría llevar al caso límite** — nadie va a llenar 12 GiB
de VRAM de verdad para comprobar que el rechazo funciona.

Las que sí tocan la tarjeta viven detrás de `FILEX_PRUEBAS_SIDECAR=1`: cargar
RapidOCR cuesta 4 s y el lock de GPU es de máquina, así que meterlas en la suite
normal sería robarle la tarjeta a quien esté midiendo.

Y una disciplina que este hito pagó (trampa 42): las comprobaciones de forma van
sobre el **AST**, no sobre el texto de la fuente — un `assertNotIn` sobre texto
no distingue una llamada de un comentario que explica que ya no se llama.
"""
from __future__ import annotations

import ast
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filex import sidecar  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_H6 = os.path.join(RAIZ, "bench", "salidas-hito6", "img")
PRUEBAS_GPU = os.environ.get("FILEX_PRUEBAS_SIDECAR") == "1"


# ==========================================================================
class RectasDeVram(unittest.TestCase):
    """Las tres rectas, contra las cifras publicadas.

    Son la tabla de `bench/ocr-produccion-sidecar.md` §5.1, y aquí valen como
    prueba de regresión: si alguien toca `MOTORES` sin volver a medir, esto se
    pone rojo. **Un motor nuevo no hereda la recta de otro.**
    """

    def test_rapidocr_satura_en_su_tope(self):
        """RapidOCR recorta a 2 000 px (`Global.max_side_len`), así que por
        encima del recorte el coste no se mueve, por grande que sea la página."""
        m = sidecar.MOTORES["rapidocr"]
        self.assertEqual(m.coste_previsto(8.882), 1526)
        self.assertEqual(m.coste_previsto(20.0), m.coste_previsto(8.882))
        self.assertEqual(m.tope_mib, 1526)

    def test_la_recta_de_rapidocr_subestima_en_el_tramo_de_en_medio(self):
        """**La recta de RapidOCR no es un modelo: es una cota superior floja**,
        y su propio informe lo dice (r²=0,7581, cuatro puntos lineales y el
        quinto plano). En el tramo de en medio **subestima**, que es el lado malo
        para un presupuesto: a 4,352 Mpx el modelo pide 1 117 MiB y la medida de
        §3.3 fue **1 456**. Esto no es un fallo del código; es el residuo del
        modelo publicado, y va escrito para que nadie lo descubra en producción.
        """
        m = sidecar.MOTORES["rapidocr"]
        self.assertLess(m.coste_previsto(4.352), 1456)
        # El margen de 500 MiB lo cubre: 1 117 + 500 > 1 456.
        self.assertGreater(m.coste_previsto(4.352) + sidecar.MARGEN_MIB, 1456)

    def test_los_dos_sin_tope_crecen_con_los_mpx(self):
        e, p = sidecar.MOTORES["easyocr"], sidecar.MOTORES["paddleocr"]
        self.assertGreater(e.coste_previsto(8.882), e.coste_previsto(4.352))
        self.assertGreater(p.coste_previsto(8.882), p.coste_previsto(4.352))
        # Las cifras medidas de §3.3, dentro de la tolerancia de la recta.
        self.assertAlmostEqual(e.coste_previsto(8.882), 10234, delta=1)
        self.assertAlmostEqual(p.coste_previsto(8.882), 6588, delta=1)

    def test_solo_recicla_quien_no_tiene_tope(self):
        """*«Un motor sin tope propio entra en el sidecar CON su política de
        reciclado o no entra.»*"""
        self.assertFalse(sidecar.MOTORES["rapidocr"].recicla)
        self.assertTrue(sidecar.MOTORES["easyocr"].recicla)
        self.assertTrue(sidecar.MOTORES["paddleocr"].recicla)

    def test_los_mpx_admisibles_reproducen_la_tabla(self):
        """4,50 y 7,37 Mpx con los 6 000 MiB del `GPU_GUARD` y 500 de margen.

        Es la cifra que hace verificable el criterio: **el tamaño máximo de
        entrada admitido** (trampa 68)."""
        self.assertAlmostEqual(
            sidecar.MOTORES["easyocr"].mpx_admisibles(6000, 500), 4.50, places=2)
        self.assertAlmostEqual(
            sidecar.MOTORES["paddleocr"].mpx_admisibles(6000, 500), 7.37, places=2)
        self.assertEqual(
            sidecar.MOTORES["rapidocr"].mpx_admisibles(6000, 500), float("inf"))

    def test_un_a4_a_300ppp_no_entra_en_dos_de_los_tres_motores(self):
        """Un A4 a 300 ppp son **8,70 Mpx**, y con los 6 000 MiB del `GPU_GUARD`
        admiten 4,50 (EasyOCR) y 7,37 (PaddleOCR): **el límite muerde en el caso
        normal**, que es justo lo que el criterio viejo no decía. El único que lo
        traga es el que tiene tope propio."""
        A4_300PPP = 8.70
        self.assertLess(sidecar.MOTORES["easyocr"].mpx_admisibles(6000, 500), A4_300PPP)
        self.assertLess(sidecar.MOTORES["paddleocr"].mpx_admisibles(6000, 500), A4_300PPP)
        self.assertGreater(sidecar.MOTORES["rapidocr"].mpx_admisibles(6000, 500),
                           A4_300PPP)

    def test_cada_recta_declara_su_fuente(self):
        for n, m in sidecar.MOTORES.items():
            with self.subTest(motor=n):
                self.assertIn("ocr-produccion-sidecar", m.fuente)

    def test_mpx_negativos_no_se_admiten_en_silencio(self):
        with self.assertRaises(ValueError):
            sidecar.MOTORES["rapidocr"].coste_previsto(-1.0)


# ==========================================================================
class LaDecision(unittest.TestCase):
    """`admitir` / `reciclar` / `rechazar`, con la VRAM inyectada."""

    def test_admite_cuando_cabe_con_margen(self):
        d = sidecar.decidir(sidecar.MOTORES["rapidocr"], 8.882, libre_mib=6000)
        self.assertEqual(d.veredicto, "admitir")
        self.assertTrue(d.ok)
        self.assertEqual(d.coste_previsto_mib, 1526)

    def test_recicla_cuando_cabe_solo_recuperando_lo_retenido(self):
        """La diferencia entre `reciclar` y `rechazar` es exactamente lo que el
        proceso ya retiene y no va a devolver esperando."""
        d = sidecar.decidir(sidecar.MOTORES["easyocr"], 4.0, libre_mib=3000,
                            residente_mib=4000)
        self.assertEqual(d.veredicto, "reciclar")

    def test_rechaza_cuando_no_cabe_ni_reciclando(self):
        """*«Reciclar dos veces seguidas no ayuda»*: si ni con todo lo retenido
        cabe, el documento no cabe en esta máquina."""
        d = sidecar.decidir(sidecar.MOTORES["easyocr"], 8.882, libre_mib=2000,
                            residente_mib=1000)
        self.assertEqual(d.veredicto, "rechazar")
        self.assertIn("no cabe en esta maquina", d.motivo)

    def test_sin_lectura_de_vram_se_admite(self):
        """`None` no es cero. Confundir «no hay tarjeta» con «la tarjeta está
        llena» convierte una máquina sin GPU en una máquina bloqueada."""
        d = sidecar.decidir(sidecar.MOTORES["easyocr"], 8.882, libre_mib=None)
        self.assertEqual(d.veredicto, "admitir")

    def test_el_margen_de_500_decide_el_borde(self):
        m = sidecar.MOTORES["rapidocr"]
        self.assertEqual(sidecar.decidir(m, 8.882, 2026).veredicto, "admitir")
        self.assertNotEqual(sidecar.decidir(m, 8.882, 2025).veredicto, "admitir")

    def test_la_decision_lleva_los_numeros_dentro(self):
        """Un veredicto sin sus cifras no es auditable."""
        d = sidecar.decidir(sidecar.MOTORES["paddleocr"], 8.882, 6000).como_dict()
        for clave in ("veredicto", "motivo", "coste_previsto_MiB", "libre_MiB",
                      "margen_MiB", "mpx", "motor", "mpx_admisibles"):
            self.assertIn(clave, d)


# ==========================================================================
class ElOrdenDelLote(unittest.TestCase):
    def test_el_mayor_va_primero(self):
        """**Refutación medida**, no preferencia: el ascendente que proponía
        `k-por-motor.md` §6.3 cuesta +5 350 MiB en EasyOCR (×2,25)."""
        r = sidecar.orden_descendente([("a", 1.25), ("b", 8.88), ("c", 0.55)])
        self.assertEqual([x[0] for x in r], ["b", "a", "c"])

    def test_no_pierde_ni_duplica_paginas(self):
        entrada = [("a", 1.0), ("b", 1.0), ("c", 2.0)]
        self.assertCountEqual(sidecar.orden_descendente(entrada), entrada)


# ==========================================================================
class LaGeometria(unittest.TestCase):
    """Los Mpx se leen de la **cabecera**, en proceso."""

    def test_png_del_rasterizado(self):
        p = os.path.join(IMG_H6, "escaneado_d4_r400.png")
        if not os.path.exists(p):
            self.skipTest("falta el ráster (`bench/salidas-hito6/preparar_h6.py`)")
        self.assertAlmostEqual(sidecar.megapixeles(p), 8.882, places=3)

    def test_png_del_corpus(self):
        p = os.path.join(RAIZ, "corpus", "imagen", "tipico.png")
        if not os.path.exists(p) or os.path.getsize(p) < 1000:
            self.skipTest("corpus en punteros de LFS: `git lfs checkout`")
        self.assertGreater(sidecar.megapixeles(p), 0)

    def test_un_fichero_que_no_es_imagen_no_devuelve_un_numero_cualquiera(self):
        with self.assertRaises(ValueError):
            sidecar.megapixeles(os.path.join(RAIZ, "pyproject.toml"))

    def test_png_sintetico(self):
        """Sin depender de ningún binario: los rásteres del informe se borran al
        terminar (peso del repositorio) y una prueba que se salta sola cuando
        faltan no cubre nada."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.png")
            with open(p, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR"
                        + (2588).to_bytes(4, "big") + (3432).to_bytes(4, "big")
                        + b"\x08\x00\x00\x00\x00")
            self.assertAlmostEqual(sidecar.megapixeles(p), 8.882, places=3)

    def test_jpeg_sintetico(self):
        """El otro formato que produce el rasterizado de este proyecto. El alto
        va ANTES que el ancho en el SOF, y confundirlos da una geometría
        transpuesta que en un folio cuadrado nadie notaría."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.jpg")
            with open(p, "wb") as f:
                f.write(b"\xff\xd8"
                        + b"\xff\xe0" + (16).to_bytes(2, "big") + b"JFIF\x00" + b"\x00" * 9
                        + b"\xff\xc0" + (17).to_bytes(2, "big") + b"\x08"
                        + (2000).to_bytes(2, "big") + (1000).to_bytes(2, "big")
                        + b"\x03" + b"\x00" * 9
                        + b"\xff\xd9")
            self.assertAlmostEqual(sidecar.megapixeles(p), 2.0, places=6)


# ==========================================================================
class ElPresupuesto(unittest.TestCase):
    """El `Perfil` obliga a nombrar el tamaño máximo de entrada (trampa 68)."""

    def test_el_perfil_que_cumple_reproduce_los_7564(self):
        p = sidecar.Perfil("distil+rapidocr+nvenc", escritorio_mib=3448,
                           audio_mib=1847, motor=sidecar.MOTORES["rapidocr"],
                           mpx_max=8.882, nvenc_mib=743)
        v = p.evaluar()
        self.assertEqual(v["total_MiB"], 7564)
        self.assertTrue(v["cumple_techo"])

    def test_el_perfil_de_large_v3_no_cumple(self):
        p = sidecar.Perfil("large-v3+rapidocr+nvenc", escritorio_mib=3448,
                           audio_mib=4525, motor=sidecar.MOTORES["rapidocr"],
                           mpx_max=8.882, nvenc_mib=743)
        v = p.evaluar()
        self.assertEqual(v["total_MiB"], 10242)
        self.assertFalse(v["cumple_techo"])
        self.assertTrue(v["cabe_en_tarjeta"])       # no cumple, pero cabe

    def test_easyocr_a_888_mpx_no_cabe_en_la_tarjeta(self):
        """La fila que cierra la pregunta: **un** modelo, sin NVENC, sin segundo
        residente, y ya no cabe con la base de escritorio documentada."""
        p = sidecar.Perfil("solo easyocr @8,88", escritorio_mib=3448,
                           audio_mib=0, motor=sidecar.MOTORES["easyocr"],
                           mpx_max=8.882, nvenc_mib=0)
        self.assertFalse(p.evaluar()["cabe_en_tarjeta"])

    def test_el_perfil_declara_que_la_suma_es_una_hipotesis(self):
        """Mientras el total sea una suma de medidas tomadas por separado, quien
        lea el veredicto tiene que verlo."""
        p = sidecar.Perfil("x", 3448, 1847, sidecar.MOTORES["rapidocr"], 8.882)
        self.assertTrue(p.evaluar()["aditividad_supuesta"])

    def test_bajar_el_tamano_maximo_puede_cambiar_el_veredicto(self):
        """La demostración de por qué el criterio necesita el tamaño dentro: la
        MISMA configuración cumple o no según qué documento admita."""
        def perfil(mpx):
            return sidecar.Perfil("paddle", 3448, 1847,
                                  sidecar.MOTORES["paddleocr"], mpx, 743)
        self.assertFalse(perfil(8.882).evaluar()["cumple_techo"])
        self.assertTrue(perfil(2.221).evaluar()["cumple_techo"])


# ==========================================================================
class TrabajadorFalso:
    """Un trabajador sin proceso: para ejercitar TTL, LRU y reciclado."""

    def __init__(self, motor, dispositivo, reloj):
        self.motor, self.dispositivo = motor, dispositivo
        self.reloj = reloj
        self.ultimo_uso = reloj()
        self.paginas = 0
        self.mpx_max_visto = 0.0
        self.reciclados = 0
        self.arrancado_en = 0.001
        self.cerrado = False
        self._vivo = False

    def vivo(self):
        return self._vivo

    def arrancar(self):
        self._vivo = True
        self.ultimo_uso = self.reloj()

    def cerrar(self):
        self._vivo = False
        self.cerrado = True

    def reciclar(self):
        self.cerrar()
        self.reciclados += 1
        self.paginas = 0
        self.mpx_max_visto = 0.0
        self.arrancar()

    def pedir(self, orden, timeout=None):
        self.ultimo_uso = self.reloj()
        return {"ok": True, "chars": 42, "texto": "x" * 42, "ms": 1.0}


class RelojFalso:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def avanzar(self, s):
        self.t += s


class VramFalsa:
    """La VRAM libre, **mutable**: sin poder moverla no se puede llevar el
    registro al caso límite, que es justo donde vive la regla."""

    def __init__(self, mib):
        self.mib = mib

    def __call__(self):
        return self.mib


def _registro(libre_mib, reloj=None, ttl_s=300.0):
    r = reloj or RelojFalso()
    v = VramFalsa(libre_mib)
    reg = sidecar.Registro(ttl_s=ttl_s, vram_libre=v, reloj=r)
    reg._fabrica = lambda m, d: TrabajadorFalso(m, d, r)
    reg.vram = v
    return reg, r


class ElRegistro(unittest.TestCase):
    def test_ttl_descarga_por_inactividad(self):
        """«Los modelos se descargan por inactividad» es la mitad del criterio
        del hito 6 que **no** cambia en la reescritura."""
        reg, reloj = _registro(9000, ttl_s=60.0)
        reg.obtener("rapidocr")
        self.assertEqual(len(reg.residentes), 1)
        reloj.avanzar(30)
        self.assertEqual(reg.caducar(), [])
        reloj.avanzar(31)
        self.assertEqual(reg.caducar(), [("rapidocr", "cuda")])
        self.assertEqual(len(reg.residentes), 0)

    def test_usarlo_reinicia_el_ttl(self):
        reg, reloj = _registro(9000, ttl_s=60.0)
        reg.procesar("rapidocr", "x.png", mpx=1.0)
        reloj.avanzar(50)
        reg.procesar("rapidocr", "x.png", mpx=1.0)
        reloj.avanzar(50)
        self.assertEqual(reg.caducar(), [])

    def test_lru_desaloja_al_menos_reciente(self):
        """Se desaloja al que lleva más tiempo sin usarse, **no al que más
        ocupa**: el que más ocupa suele ser el que se está usando."""
        reg, reloj = _registro(9000)
        reg.obtener("rapidocr")
        reloj.avanzar(10)
        reg.obtener("easyocr")
        reloj.avanzar(10)
        reg.obtener("paddleocr")
        self.assertEqual(reg.desalojar_lru(), ("rapidocr", "cuda"))
        self.assertEqual(reg.desalojar_lru(), ("easyocr", "cuda"))

    def test_lru_no_desaloja_al_que_se_esta_salvando(self):
        reg, _ = _registro(9000)
        reg.obtener("rapidocr")
        self.assertIsNone(reg.desalojar_lru(salvar=("rapidocr", "cuda")))

    def test_lru_devuelve_none_cuando_no_queda_a_quien_desalojar(self):
        reg, _ = _registro(9000)
        self.assertIsNone(reg.desalojar_lru())

    def test_un_motor_sin_recta_medida_no_entra(self):
        """*«Una constante global hace que cada motor nuevo herede en silencio
        los ppp que le convenían a otro.»* Aquí, la VRAM."""
        reg, _ = _registro(9000)
        with self.assertRaises(KeyError):
            reg.admitir("motor_nuevo", 1.0)

    def test_rechaza_la_pagina_que_no_cabe_y_no_arranca_nada(self):
        """La admisión se evalúa **antes**: una página que no cabe no debe
        siquiera provocar la carga del modelo."""
        reg, _ = _registro(1000)
        r = reg.procesar("easyocr", "x.png", mpx=8.882)
        self.assertFalse(r["ok"])
        self.assertTrue(r["rechazada"])
        self.assertEqual(len(reg.residentes), 0)

    def test_recicla_cuando_lo_retenido_basta(self):
        """El escenario del atasco, reproducido: una página grande deja el
        proceso reteniendo 4 961 MiB; luego la tarjeta se estrecha y la
        siguiente **solo** cabe si se recupera lo retenido. Y se recupera
        matando el proceso: esperar no devuelve nada."""
        reg, _ = _registro(9000)
        reg.procesar("easyocr", "grande.png", mpx=4.0)      # retiene 4 961
        t = reg.residentes[("easyocr", "cuda")]
        self.assertEqual(t.reciclados, 0)
        self.assertEqual(t.mpx_max_visto, 4.0)
        reg.vram.mib = 3000                                 # entra un tercero
        reg.procesar("easyocr", "grande2.png", mpx=4.0)
        self.assertEqual(reg.residentes[("easyocr", "cuda")].reciclados, 1)

    def test_el_reciclado_queda_anotado(self):
        """Un campo honesto al lado de una nota falsa se lee como una respuesta
        honesta (trampa 44): lo que ocurrió tiene que quedar escrito."""
        reg, _ = _registro(9000)
        reg.procesar("easyocr", "g.png", mpx=4.0)
        reg.vram.mib = 3000
        reg.procesar("easyocr", "g2.png", mpx=4.0)
        self.assertTrue(any(s["suceso"] == "reciclado" for s in reg.sucesos))

    def test_un_proceso_sin_historia_no_tiene_nada_que_reciclar(self):
        """`reciclar` solo es distinto de `rechazar` porque hay algo retenido:
        con un trabajador recién nacido, la única respuesta honesta es rechazar."""
        reg, _ = _registro(2000)
        d = reg.admitir("easyocr", 8.882)
        self.assertEqual(d.veredicto, "rechazar")

    def test_cada_resultado_declara_dispositivo_y_via_de_entrada(self):
        """Trampas 11 y 30: las dos variables que cambian la salida y que el
        corpus esconde. Van en **cada** resultado, no en la documentación."""
        reg, _ = _registro(9000)
        r = reg.procesar("rapidocr", "x.png", mpx=1.0)
        self.assertEqual(r["dispositivo"], "cuda")
        self.assertEqual(r["via_entrada"], "ruta")
        self.assertIn("decision", r)

    def test_en_cpu_no_se_presupuesta_vram(self):
        reg, _ = _registro(100)
        d = reg.admitir("easyocr", 8.882, dispositivo="cpu")
        self.assertEqual(d.veredicto, "admitir")

    def test_el_dispositivo_va_en_la_clave_del_registro(self):
        """CPU y GPU no dan la misma salida (5 de 21 celdas): son dos
        residentes distintos, no el mismo con una bandera."""
        reg, _ = _registro(9000)
        reg.obtener("rapidocr", "cuda")
        reg.obtener("rapidocr", "cpu")
        self.assertEqual(len(reg.residentes), 2)

    def test_el_lote_procesa_en_orden_descendente(self):
        import tempfile
        reg, _ = _registro(9000)
        vistos = []
        orig = reg.procesar

        def espia(motor, ruta, **kw):
            vistos.append(kw["mpx"])
            return orig(motor, ruta, **kw)

        reg.procesar = espia
        with tempfile.TemporaryDirectory() as d:
            rutas = []
            for nombre, (an, al) in (("p", (1000, 1000)), ("g", (3000, 3000)),
                                     ("m", (2000, 2000))):
                p = os.path.join(d, nombre + ".png")
                with open(p, "wb") as f:
                    f.write(b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR"
                            + an.to_bytes(4, "big") + al.to_bytes(4, "big")
                            + b"\x08\x00\x00\x00\x00")
                rutas.append(p)
            reg.procesar_lote("rapidocr", rutas)
        self.assertEqual(vistos, sorted(vistos, reverse=True))

    def test_cerrar_se_lleva_a_todos(self):
        reg, _ = _registro(9000)
        reg.obtener("rapidocr")
        reg.obtener("easyocr")
        reg.cerrar()
        self.assertEqual(len(reg.residentes), 0)


# ==========================================================================
GUION_FALSO = r'''
import json, sys
# Un motor que imprime por su cuenta en stdout: PaddleOCR lo hace.
print("[INFO] cargando pesos ...")
# Y que escribe MUCHO en stderr: la tuberia de 64 KiB, llena, bloquea al
# escritor, y el sidecar se colgaria escribiendo un log.
for i in range(4000):
    sys.stderr.write("linea de ruido numero %d en stderr\n" % i)
sys.stderr.flush()
print(json.dumps({"evento": "listo", "motor": "falso", "pid": 1}))
sys.stdout.flush()
for linea in sys.stdin:
    o = json.loads(linea)
    if o.get("orden") == "fin":
        break
    print("[INFO] procesando ...")
    print(json.dumps({"ok": True, "chars": 3, "texto": "abc", "ms": 1.0}))
    sys.stdout.flush()
'''


class ElProtocoloDelTrabajador(unittest.TestCase):
    """El proceso de verdad, con un motor de mentira. **Sin GPU**: lo que se
    prueba aquí es el canal, no el OCR."""

    def setUp(self):
        import tempfile
        self.dir = tempfile.mkdtemp(prefix="filex-prueba-h6-")
        self.guion = os.path.join(self.dir, "falso.py")
        with open(self.guion, "w", encoding="utf-8") as f:
            f.write(GUION_FALSO)
        self.t = sidecar.Trabajador("falso", "cpu", python=sys.executable,
                                    guion=self.guion)

    def tearDown(self):
        import shutil
        self.t.cerrar()
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_arranca_pese_a_4000_lineas_de_stderr(self):
        """Sin el hilo que drena el `stderr`, esto se queda colgado hasta el
        tope: 4 000 líneas llenan de sobra los 64 KiB de la tubería."""
        self.t.arrancar()
        self.assertTrue(self.t.vivo())
        self.assertEqual(self.t.meta.get("evento"), "listo")

    def test_una_linea_ajena_al_protocolo_no_mata_al_trabajador(self):
        """El `[INFO]` que el motor imprime en `stdout` se salta, y **se
        cuenta**: un motor que empieza a imprimir es una regresión silenciosa."""
        self.t.arrancar()
        r = self.t.pedir({"orden": "ocr", "ruta": "x.png"}, timeout=30)
        self.assertTrue(r["ok"])
        self.assertGreaterEqual(self.t.intrusas, 2)   # una al arrancar, una al pedir

    def test_el_stderr_queda_para_diagnostico_pero_no_en_el_resultado(self):
        self.t.arrancar()
        r = self.t.pedir({"orden": "ocr", "ruta": "x.png"}, timeout=30)
        self.assertNotIn("stderr", r)
        self.assertTrue(any("ruido" in l for l in self.t.diagnostico()))
        self.assertLessEqual(len(self.t.diagnostico()), 50)   # es un anillo

    def test_el_desechable_se_crea_y_se_borra(self):
        """R18/R21: directorio de trabajo desechable por trabajador, censado y
        borrado entero."""
        self.t.arrancar()
        d = self.t.cwd
        self.assertTrue(os.path.isdir(d))
        self.assertEqual(self.t.sobrantes(), [])
        self.t.cerrar()
        self.assertFalse(os.path.exists(d))

    def test_reciclar_cambia_de_proceso(self):
        self.t.arrancar()
        p1 = self.t.proc.pid
        self.t.reciclar()
        self.assertNotEqual(self.t.proc.pid, p1)
        self.assertEqual(self.t.reciclados, 1)
        self.assertEqual(self.t.mpx_max_visto, 0.0)   # el historial se olvida


# ==========================================================================
class Forma(unittest.TestCase):
    """Comprobaciones estructurales, sobre el **AST** (trampa 42)."""

    @classmethod
    def setUpClass(cls):
        cls.fuente = open(sidecar.__file__, encoding="utf-8").read()
        try:
            cls.arbol = ast.parse(cls.fuente)
        except SyntaxError:                                     # pragma: no cover
            cls.arbol = None

    def test_la_fuente_compila(self):
        """Una prueba de AST puede pasar porque la fuente NO compila (trampa 60):
        se comprueba antes de comparar nada."""
        self.assertIsNotNone(self.arbol)

    def test_no_se_invoca_nada_con_shell(self):
        for n in ast.walk(self.arbol):
            if isinstance(n, ast.Call):
                for kw in n.keywords:
                    if kw.arg == "shell":
                        self.fail("hay una invocación con shell")

    def test_el_paquete_no_gana_dependencias(self):
        """`filex` no tiene dependencias, y es una decisión escrita en
        `pyproject.toml`. Los motores viven en procesos, no en `import`s de
        nivel de módulo."""
        prohibidos = {"torch", "rapidocr", "easyocr", "paddleocr", "paddle",
                      "numpy", "cv2", "onnxruntime", "faster_whisper"}
        for n in self.arbol.body:            # SOLO el nivel superior
            if isinstance(n, ast.Import):
                for a in n.names:
                    self.assertNotIn(a.name.split(".")[0], prohibidos)
            elif isinstance(n, ast.ImportFrom) and n.module:
                self.assertNotIn(n.module.split(".")[0], prohibidos)

    def test_toda_espera_de_subproceso_lleva_tope(self):
        """Timeouts explícitos en todo: estos motores dejan huérfanos vivos 13
        minutos. `wait`, `communicate` y `join` sin tope son la misma trampa."""
        sin_tope = []
        for n in ast.walk(self.arbol):
            if not isinstance(n, ast.Call) or not isinstance(n.func, ast.Attribute):
                continue
            if n.func.attr not in ("wait", "communicate", "join"):
                continue
            # `Event.wait(x)` y `Thread.join(x)` llevan el tope posicional.
            if n.args or any(k.arg == "timeout" for k in n.keywords):
                continue
            sin_tope.append(n.func.attr + f" (línea {n.lineno})")
        self.assertEqual(sin_tope, [], f"esperas sin tope: {sin_tope}")

    def test_el_stderr_del_motor_no_vuelve_crudo(self):
        """*«Nunca devolver `stderr` crudo al modelo.»* El trabajador devuelve el
        **tipo** de la excepción, no su texto."""
        cuerpo = [n for n in self.arbol.body
                  if isinstance(n, ast.FunctionDef) and n.name == "_trabajador"]
        self.assertEqual(len(cuerpo), 1)
        for n in ast.walk(cuerpo[0]):
            if isinstance(n, ast.Dict):
                for k, v in zip(n.keys, n.values):
                    if isinstance(k, ast.Constant) and k.value == "error":
                        # `type(ex).__name__` es un Attribute sobre una Call.
                        self.assertIsInstance(v, ast.Attribute)
                        self.assertEqual(v.attr, "__name__")
                        self.assertIsInstance(v.value, ast.Call)
                        self.assertEqual(getattr(v.value.func, "id", None), "type")


# ==========================================================================
@unittest.skipUnless(PRUEBAS_GPU, "necesita la tarjeta: FILEX_PRUEBAS_SIDECAR=1")
class ConLaTarjeta(unittest.TestCase):
    """El camino real. Fuera de la suite normal: el lock de GPU es de máquina."""

    def test_un_trabajador_de_verdad_lee_el_folio(self):
        img = os.path.join(IMG_H6, "escaneado_d4_r400.png")
        if not os.path.exists(img):
            self.skipTest("falta el ráster")
        py = os.environ.get("FILEX_PY_OCR")
        if not py or not os.path.exists(py):
            self.skipTest("falta FILEX_PY_OCR con el intérprete del venv de OCR")
        with sidecar.Registro(python=py) as reg:
            r = reg.procesar("rapidocr", img)
            self.assertTrue(r["ok"], r)
            self.assertGreater(r["chars"], 100)
            self.assertEqual(r["via_entrada"], "ruta")
            t = reg.residentes[("rapidocr", "cuda")]
            # R21: el trabajador no escribe fuera de lo declarado.
            self.assertEqual(t.sobrantes(), [])


if __name__ == "__main__":                                      # pragma: no cover
    unittest.main()

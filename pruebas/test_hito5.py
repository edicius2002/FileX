"""Pruebas del hito 5 — el motor documental en contenedor.

    python -m unittest pruebas.test_hito5 -v

Dos mitades, y la separación es deliberada:

* Las que **no necesitan Docker** comprueban la construcción de la invocación y
  la forma de las tablas de aristas. Corren siempre.
* Las de **integración** convierten de verdad y se saltan solas si el entorno de
  contenedor no está — «un motor cuyo binario falta se auto-excluye y se
  informa, en lugar de fallar» es criterio de aceptación del hito 1, y una suite
  que reviente cuando Docker está parado lo incumpliría desde fuera.

Cada prueba cita la medición de la que sale. Las que comprueban una POLÍTICA y
no una medición lo dicen.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filex import invocacion  # noqa: E402
from filex.grafo import NOMINAL, REAL, Grafo  # noqa: E402
from filex.motor_contenedor import (  # noqa: E402
    CalibreEnContenedor, LibreOfficeEnContenedor, PandocEnContenedor, entorno,
)
from filex.motores import ImageMagick  # noqa: E402
from filex.nucleo import FileX  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRADAS = os.path.join(RAIZ, "bench", "salidas-hito5", "entradas")
CENTINELA = "FILEXSENTINELA7743"

_ENT = None


def hay_contenedor() -> bool:
    global _ENT
    if _ENT is None:
        _ENT = entorno()
    return bool(_ENT.get("ok"))


def _forzado(cls):
    """Una instancia con las aristas cargadas SIN tocar Docker.

    Las tablas son datos: se pueden leer sin demonio. Lo que no se puede es
    ejecutar, y eso lo prueban las de integración.
    """
    m = cls()
    m.ruta = "docker"
    m.imagen = "filex-c13"
    m.version = "prueba"
    m.aristas = m._aristas()
    return m


def texto_pdf(ruta: str) -> str:
    """Texto de un PDF con el Ghostscript NATIVO de Windows.

    Trampa 4 de `CLAUDE.md`: `txtwrite` emite 1-3 caracteres de basura en un PDF
    sin texto, así que el umbral de «conserva texto» es >= 10, no > 0.
    """
    d = tempfile.mkdtemp(prefix="filex-t5-")
    dst = os.path.join(d, "t.txt")
    r = invocacion.ejecutar(["gswin64c", "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                             "-sDEVICE=txtwrite", f"-sOutputFile={dst}", ruta],
                            timeout=90)
    if not r.ok or not os.path.isfile(dst):
        return ""
    with open(dst, encoding="utf-8", errors="replace") as f:
        return f.read()


# ---------------------------------------------------------------- sin Docker


class Invocacion(unittest.TestCase):
    """Cómo se construye el `docker run`. Es lo que decide si el punto 5 existe."""

    def setUp(self):
        self.lo = _forzado(LibreOfficeEnContenedor)
        self.trabajo = tempfile.mkdtemp(prefix="filex-t5-")
        self.ent = os.path.join(ENTRADAS, "entrada.docx")

    def argv(self, o="docx", d="pdf", motor=None):
        m = motor or self.lo
        return m.orden(os.path.join(ENTRADAS, f"entrada.{o}"),
                       os.path.join(self.trabajo, f"salida.{d}"), {})

    def test_es_una_lista_y_no_hay_shell(self):
        # `invocacion.ejecutar` rechaza una cadena por diseño: aceptarla
        # implicaría shell, y morphos usa `bash -c` + `Sprintf` y tiene RCE.
        a = self.argv()
        self.assertIsInstance(a, list)
        self.assertEqual(a[0], "docker")
        self.assertNotIn("sh", a[:6])
        for x in a:
            self.assertNotIn("&&", x)
            self.assertNotIn("|", x)

    def test_la_entrada_se_monta_SOLA_y_de_solo_lectura(self):
        # Montar el directorio padre le enseñaría al contenedor todo lo que
        # hubiera al lado. MEDIDO: escribir en /ent da `Read-only file system`.
        a = self.argv()
        montajes = [a[i + 1] for i, x in enumerate(a) if x == "--mount"]
        ent = [m for m in montajes if "/ent/" in m]
        self.assertEqual(len(ent), 1, montajes)
        self.assertIn(",readonly", ent[0])
        self.assertIn("entrada.docx", ent[0])       # el FICHERO, no su carpeta
        self.assertNotIn("target=/ent,", ent[0])

    def test_el_desechable_ES_el_trabajo_del_contenedor(self):
        # Es lo que hace que el censo del punto 5 vea lo que el motor escribe
        # DENTRO del contenedor. Con `docker cp` no se vería.
        a = self.argv()
        montajes = [a[i + 1] for i, x in enumerate(a) if x == "--mount"]
        trb = [m for m in montajes if m.endswith("target=/trabajo")]
        self.assertEqual(len(trb), 1, montajes)
        self.assertIn(self.trabajo.replace("\\", "/"), trb[0])
        self.assertEqual(a[a.index("-w") + 1], "/trabajo")

    def test_sin_red(self):
        # Lo que no se necesita, no se concede: ninguno de los tres motores
        # necesita red para convertir un documento local.
        a = self.argv()
        self.assertEqual(a[a.index("--network") + 1], "none")

    def test_entrypoint_explicito(self):
        # MEDIDO: la imagen trae ENTRYPOINT ["bun","run","dist/src/index.js"].
        # Sin sustituirlo la orden se pasa como argumentos a la aplicación web
        # de ConvertX y sale `Module not found`.
        for cls, o, d, binario in ((LibreOfficeEnContenedor, "docx", "pdf", "soffice"),
                                   (PandocEnContenedor, "md", "docx", "pandoc"),
                                   (CalibreEnContenedor, "epub", "pdf", "ebook-convert")):
            a = self.argv(o, d, _forzado(cls))
            # El entrypoint es `timeout`, y el motor va detrás de la imagen.
            self.assertEqual(a[a.index("--entrypoint") + 1], "timeout")
            self.assertEqual(a[a.index("filex-c13") + 4], binario, a)

    def test_el_tope_va_DENTRO_del_contenedor(self):
        """**Matar el `docker run` NO mata el contenedor.**

        MEDIDO (`bench/hito5-documental.md` §4.4): tres `soffice` colgados
        sobrevivieron **37 minutos** a `taskkill /F /T` sobre el cliente y al
        `--rm`, y cuando R18 borró el desechable el bind mount desapareció bajo
        ellos y `docker rm -f` respondió *«tried to kill container, but did not
        receive an exit event»*.
        """
        from filex.motor_contenedor import TIMEOUT_DENTRO
        a = self.argv()
        i = a.index("filex-c13")
        self.assertEqual(a[i + 1:i + 4], ["-k", "5", str(TIMEOUT_DENTRO)], a)
        # Y por debajo del tope por defecto de fuera, para disparar primero.
        self.assertLess(TIMEOUT_DENTRO, invocacion.TIMEOUT_POR_DEFECTO)

    def test_libreoffice_nombra_la_salida_por_la_ENTRADA(self):
        # No hay forma de decirle a `soffice` «escribe aquí con este nombre»:
        # deriva el nombre de la entrada. Por eso la entrada se monta con el
        # nombre que queremos. Renombrar después sería otra escritura fuera de
        # lo declarado, y la vería el punto 5.
        a = self.lo.orden(os.path.join(ENTRADAS, "entrada.docx"),
                          os.path.join(self.trabajo, "salida.pdf"), {})
        self.assertTrue(any("target=/ent/salida.docx," in x for x in a), a)
        self.assertEqual(a[a.index("--outdir") + 1], "/trabajo")

    def test_una_ruta_con_coma_se_rechaza(self):
        # `--mount` separa sus opciones por comas y no las escapa. Mejor
        # negarse que montar otra cosa.
        with self.assertRaises(ValueError):
            self.lo.orden(os.path.join(ENTRADAS, "entrada.docx"),
                          os.path.join(self.trabajo, "a,b", "salida.pdf"), {})

    def test_una_arista_sondeada_y_muerta_no_se_puede_ni_invocar(self):
        # Doble cierre: el grafo le suma infinito Y `orden()` se niega.
        with self.assertRaises(ValueError):
            self.lo.orden(os.path.join(ENTRADAS, "entrada.epub"),
                          os.path.join(self.trabajo, "salida.pdf"), {})


class Tablas(unittest.TestCase):
    """Que lo declarado `REAL` sea lo ejecutado, y nada más."""

    def test_solo_es_REAL_lo_que_tiene_evidencia(self):
        # El 41,0 % de las aristas que los catálogos declaran no existen.
        # Declarar `real` sin haber ejecutado es el fallo central del sector.
        for cls in (LibreOfficeEnContenedor, PandocEnContenedor, CalibreEnContenedor):
            for a in _forzado(cls).aristas:
                if a.estado == REAL:
                    self.assertIn("sonda.json:", a.evidencia, str(a))

    def test_epub_pdf_es_REAL_en_calibre_y_NOMINAL_en_libreoffice(self):
        # MEDIDO dos veces con dos invocaciones distintas: `soffice` da rc=1 con
        # `source file could not be loaded`; `ebook-convert` da rc=0 y 26 817 B.
        c = {(a.origen, a.destino): a for a in _forzado(CalibreEnContenedor).aristas}
        lo = {(a.origen, a.destino): a for a in _forzado(LibreOfficeEnContenedor).aristas}
        self.assertEqual(c[("epub", "pdf")].estado, REAL)
        self.assertEqual(lo[("epub", "pdf")].estado, NOMINAL)

    def test_el_salto_que_rasteriza_esta_marcado(self):
        lo = {(a.origen, a.destino): a for a in _forzado(LibreOfficeEnContenedor).aristas}
        self.assertTrue(lo[("docx", "png")].rasteriza)
        self.assertFalse(lo[("docx", "pdf")].rasteriza)

    def test_docx_txt_por_libreoffice_esta_marcada_muerta(self):
        # Se CUELGA y escribe un `.tmp` a ~1,5 MB/s: 471 859 200 B en 240 s.
        # `odt→txt` con la MISMA orden tarda 6,2 s, así que el grafo llega
        # igual por `docx→odt→txt`.
        lo = {(a.origen, a.destino): a for a in _forzado(LibreOfficeEnContenedor).aristas}
        self.assertEqual(lo[("docx", "txt")].estado, NOMINAL)
        self.assertEqual(lo[("odt", "txt")].estado, REAL)


class ElegirBienConAristasREALES(unittest.TestCase):
    """El criterio amarillo del hito 1, ahora con aristas medidas.

    `PLAN-ORQUESTADOR.md` §7: *«el rechazo comparado NO se puede demostrar aquí:
    con ffmpeg, ImageMagick y Ghostscript no existe ningún par de formatos donde
    compitan un camino que conserva el texto y otro que lo rasteriza»*. Con el
    motor documental **existe, y con el mismo binario a los dos lados**:
    `soffice --convert-to pdf` y `soffice --convert-to png`.
    """

    def setUp(self):
        lo = _forzado(LibreOfficeEnContenedor)
        im = ImageMagick()
        im.ruta, im.version = "magick", "prueba"
        im.aristas = im._aristas()
        self.aristas_lo = {(a.origen, a.destino): a for a in lo.aristas}
        self.png_pdf = next(a for a in im.aristas
                            if (a.origen, a.destino) == ("png", "pdf"))
        # El grafo MÍNIMO con los dos caminos que compiten. Se restringe a
        # propósito: ver `test_con_el_grafo_entero_el_rechazo_deja_de_explicarse`.
        self.g = Grafo([self.aristas_lo[("docx", "pdf")],
                        self.aristas_lo[("docx", "png")],
                        self.png_pdf])

    def test_elige_el_que_conserva_el_texto(self):
        d = self.g.camino("docx", "pdf")
        self.assertEqual(d.camino.formatos, ["docx", "pdf"])
        self.assertFalse(d.camino.rasteriza)

    def test_y_dice_por_que_rechaza_el_que_rasteriza(self):
        d = self.g.camino("docx", "pdf")
        motivos = [m for _, m in d.rechazados]
        self.assertTrue(any("rasteriza" in m for m in motivos), motivos)
        self.assertTrue(any("admite texto" in m for m in motivos), motivos)

    def test_hacia_un_destino_SIN_texto_el_camino_corto_gana(self):
        # La penalización no es fobia a rasterizar: es que el DESTINO admita
        # texto. Hacia png, rasterizar es la implementación, no una pérdida.
        d = self.g.camino("docx", "png")
        self.assertEqual(d.camino.formatos, ["docx", "png"])

    def test_con_el_grafo_entero_el_rechazo_SIGUE_explicandose(self):
        """Regresión del tope que tapaba la explicación.

        `Grafo.TOPE_CANDIDATOS = 8` conserva los OCHO MÁS BARATOS, y un camino
        que rasteriza cuesta `+1000`: es siempre el último. En cuanto hubo ocho
        caminos que conservan el texto —y con solo LibreOffice ya había siete—
        el que rasteriza dejó de llegar a la lista: **la elección seguía siendo
        correcta y el grafo ya no sabía decir por qué**, que es la otra mitad
        del criterio de aceptación del hito 1.

        Cerrado reservándole un hueco propio en `Grafo._enumerar`: se explica,
        no se elige. **Esta prueba era al revés hasta que se arregló.**
        """
        g = Grafo(list(self.aristas_lo.values()) + [self.png_pdf])
        d = g.camino("docx", "pdf")
        self.assertEqual(d.camino.formatos, ["docx", "pdf"])   # elige bien
        motivos = [m for _, m in d.rechazados]
        self.assertTrue(any("rasteriza" in m for m in motivos), motivos)
        self.assertTrue(any("admite texto" in m for m in motivos), motivos)


# ------------------------------------------------------------- integración


@unittest.skipUnless(hay_contenedor(), "no hay entorno de contenedor")
class Integracion(unittest.TestCase):
    """Contra el contenedor real. Se salta solo si no está."""

    @classmethod
    def setUpClass(cls):
        cls.fx = FileX()
        cls.tmp = tempfile.mkdtemp(prefix="filex-t5-int-")

    def test_los_tres_submotores_se_sondean_en_ejecucion(self):
        doc = [m for m in self.fx.disponibles if m.nombre.startswith("doc_")]
        self.assertEqual(len(doc), 3, [m.nombre for m in doc])
        for m in doc:
            # El `build` es la quinta dimensión de la arista: lleva el ID de la
            # imagen, sin el cual la tabla miente en otra máquina.
            self.assertIn("@", m.version)

    def test_epub_a_pdf_elige_CALIBRE_y_no_LibreOffice(self):
        """El criterio que «discrimina de verdad» del hito 1 revisado."""
        dec = self.fx.planificar("x.epub", "y.pdf")
        self.assertTrue(dec.hay, dec.motivo)
        self.assertEqual(dec.camino.saltos, 1)
        a = dec.camino.pasos[0].arista
        self.assertEqual(a.motor, "doc_calibre")
        self.assertEqual(a.parametrizacion, "ebook-convert")

    def test_epub_a_pdf_de_verdad_conserva_el_centinela(self):
        sal = os.path.join(self.tmp, "epub.pdf")
        c = self.fx.convertir(os.path.join(ENTRADAS, "entrada.epub"), sal,
                              timeout=300)
        self.assertTrue(c.ok, c.motivo)
        self.assertIn(c.veredicto, ("ok", "ok_parcial"))
        t = texto_pdf(sal)
        self.assertIn(CENTINELA, t)
        self.assertIn("AX-1", t)
        # Y el punto 5 CUBIERTO, no dado por bueno porque nadie miró.
        self.assertTrue(c.saltos[-1].cobertura.get("5_escritura"))

    def test_docx_a_webp_en_DOS_saltos(self):
        """El criterio original del hito 1, que hasta hoy no tenía origen."""
        dec = self.fx.planificar("x.docx", "y.webp")
        self.assertTrue(dec.hay, dec.motivo)
        self.assertEqual(dec.camino.saltos, 2)

    def test_el_camino_que_conserva_el_texto_frente_al_que_rasteriza(self):
        """La demostración que no depende del mensaje del grafo: los BYTES.

        Se hacen los dos caminos y se mide el texto recuperado del PDF final.
        MEDIDO: 456 caracteres con centinela por la vía directa; **cero** por la
        vía que pasa por PNG, con un PDF perfectamente válido.
        """
        ent = os.path.join(ENTRADAS, "entrada.docx")

        directo = os.path.join(self.tmp, "directo.pdf")
        c1 = self.fx.convertir(ent, directo, timeout=300)
        self.assertTrue(c1.ok, c1.motivo)
        self.assertFalse(c1.camino.rasteriza)

        # El grafo NO elegiría este camino: se fuerza salto a salto.
        medio = os.path.join(self.tmp, "medio.png")
        c2 = self.fx.convertir(ent, medio, timeout=300)
        self.assertTrue(c2.ok, c2.motivo)
        self.assertTrue(c2.camino.rasteriza)
        rasterizado = os.path.join(self.tmp, "rasterizado.pdf")
        c3 = self.fx.convertir(medio, rasterizado, timeout=300)
        self.assertTrue(c3.ok, c3.motivo)

        t_ok = texto_pdf(directo)
        t_mal = texto_pdf(rasterizado)
        self.assertIn(CENTINELA, t_ok)
        self.assertGreaterEqual(len(t_ok.strip()), 400)
        self.assertNotIn(CENTINELA, t_mal)
        # Trampa 4: el umbral es >= 10, no > 0 — `txtwrite` emite basura.
        self.assertLess(len(t_mal.strip()), 10, repr(t_mal[:80]))

    def test_el_punto_5_ve_lo_que_el_motor_escribe_DENTRO_del_contenedor(self):
        """Sin esto, el contenedor sería un agujero en el contrato.

        `soffice --convert-to txt:Text` sobre un DOCX se cuelga y escribe
        `.~lock.salida.txt#` y un `.tmp` de cientos de MB. La arista está marcada
        `nominal`, así que aquí se comprueba lo que sí se puede comprobar en el
        camino caliente: que una conversión buena declara el punto 5 cubierto y
        que el censo cuenta los bytes del contenedor.
        """
        sal = os.path.join(self.tmp, "punto5.pdf")
        c = self.fx.convertir(os.path.join(ENTRADAS, "entrada.odt"), sal, timeout=300)
        self.assertTrue(c.ok, c.motivo)
        s = c.saltos[-1]
        self.assertTrue(s.cobertura.get("5_escritura"))
        self.assertEqual(s.sobrantes, {})

    def test_el_tope_de_dentro_no_deja_contenedores_vivos(self):
        """La comprobación del hallazgo de §4.4, con el motor colgado de verdad.

        Reproduce el cuelgue de `docx→txt` con la invocación del producto, con
        el tope de dentro bajado a 15 s y el de fuera 6 veces mayor, y comprueba
        lo único que importa: que **no queda ningún contenedor vivo** cuando la
        llamada vuelve. GNU `timeout` devuelve `124` cuando dispara.
        """
        import filex.motor_contenedor as mc
        from filex.trabajo import DirectorioDeTrabajo

        def vivos():
            r = invocacion.ejecutar(
                ["docker", "ps", "--filter", f"ancestor={_ENT['imagen']}",
                 "--format", "{{.Names}}"], timeout=60)
            return set((r.salida_txt or "").split())

        lo = [m for m in self.fx.disponibles if m.nombre == "doc_libreoffice"][0]
        guardado, mc.TIMEOUT_DENTRO = mc.TIMEOUT_DENTRO, 15
        antes = vivos()
        t = DirectorioDeTrabajo(prefijo="filex-t5-tope-")
        try:
            argv = lo._argv_docker(
                os.path.join(ENTRADAS, "entrada.docx"), t.ruta, "salida.docx",
                ["soffice", "--headless", "--norestore", "--convert-to",
                 "txt:Text", "--outdir", "/trabajo", "/ent/salida.docx"])
            r = invocacion.ejecutar(argv, timeout=15 * 6, cwd=t.ruta)
        finally:
            mc.TIMEOUT_DENTRO = guardado
            t.cerrar()
        self.assertFalse(r.agotado, "lo mató el tope de FUERA, no el de dentro")
        # 124 y 137 son AMBOS «disparó el tope de dentro», y cuál sale no es
        # aleatorio: `timeout -k 5 N` devuelve **124** si el proceso obedece el
        # TERM, y **137** (128+9) si hubo que matarlo con KILL cinco segundos
        # después. `CLAUDE.md` ya dice que **LibreOffice colgado ignora el
        # TERM**, y bajo carga tarda más en morir, así que cae en el 137.
        #
        # Exigir 124 hacía fallar esta prueba en la suite completa y pasar en
        # aislamiento — y una prueba que depende de la carga de la máquina no
        # prueba nada. Lo que se comprueba de verdad es la tercera línea: **cero
        # contenedores vivos**, que es el hallazgo (matar el `docker run` NO
        # mata el contenedor: tres `soffice` sobrevivieron 37 minutos).
        self.assertIn(r.rc, (124, 137), "no lo mató el tope de dentro")
        # Y la tercera es la que importa — pero con espera, porque **el borrado
        # de `--rm` lo hace el demonio de forma ASÍNCRONA**: leer `docker ps`
        # justo después de que `docker run` retorne es una carrera. Diagnóstico
        # de S3 (`bench/sondeo-documental.md`), y mejor que el mío: falló en 2 de
        # 5 pasadas completas y **0 de 4 aisladas**, y en los fallos `docker ps -a`
        # solo listaba los 5 contenedores del proyecto — el contenedor NO quedaba.
        # Una prueba que compite con el demonio no mide lo que dice medir.
        for _ in range(20):
            sobra = vivos() - antes
            if not sobra:
                break
            time.sleep(0.5)
        self.assertEqual(sobra, set(), "quedó un contenedor vivo")

    def test_si_falta_el_entorno_el_motor_se_auto_excluye_INFORMANDO(self):
        """Criterio de aceptación del hito 1, aquí con tres fallos distintos."""
        m = LibreOfficeEnContenedor()
        import filex.motor_contenedor as mc
        guardado = mc._ENTORNO
        try:
            mc._ENTORNO = {"ok": False, "motivo": "prueba: demonio parado",
                           "imagen": "", "imagen_id": "", "servidor": "",
                           "binarios": ()}
            m.sondear()
        finally:
            mc._ENTORNO = guardado
        self.assertIsNone(m.ruta)
        self.assertEqual(m.aristas, [])
        # Hasta el 22/08 esto se comprobaba sobre `m.binario`, porque el
        # motor sustituía ahí el nombre del ejecutable por el motivo: un
        # apaño declarado, a la espera de que el núcleo tuviera dónde
        # ponerlo. Ya lo tiene — `Motor.motivo_ausencia` — y la CLI lo
        # prefiere, así que el apaño se retiró y la prueba mira el sitio
        # bueno. `binario` vuelve a ser el nombre del ejecutable.
        self.assertIn("demonio parado", m.motivo_ausencia)
        self.assertEqual(m.binario, "docker")


if __name__ == "__main__":
    unittest.main(verbosity=2)

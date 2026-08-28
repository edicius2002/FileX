"""Pruebas del hito 7 — el watcher y la API HTTP, y la prueba de R10.

    python -m unittest pruebas.test_hito7 -v

**El objetivo de este fichero no es probar dos superficies: es probar R10.**

    *La validación vive en el núcleo, no en la superficie* (`RESULTADOS-MCP.md`
    §10, R10). La CLI de `kordoc` lee ficheros fuera de `KORDOC_ROOT` con
    `exit=0` porque `safePath` vivía en su capa MCP.

Con dos superficies eso es una afirmación. Con cuatro es una prueba, y solo si
se escribe como tal: la clase `CuatroSuperficies` pasa **los mismos seis
vectores por las cuatro** —CLA, MCP, watcher y API— y exige **la misma
respuesta**. Si alguna llevara su propia copia del predicado, tendría que
coincidir carácter a carácter con el núcleo en los seis, que es justo lo que no
pasa cuando alguien duplica una validación.

La clase `R10Estructural` cierra el otro lado: **lee los cuatro ficheros** y
comprueba que no contienen las piezas del confinamiento. Es la prueba que le
faltaba a `nombre_seguro`, que estuvo escrito, probado **y sin un solo llamante
fuera de su propia prueba** mientras FileX escribía 94 B en el flujo alternativo
de un fichero ajeno con `veredicto: ok`.

Cada prueba cita la medición de la que sale (`bench/hito7-superficies.md`). Las
que comprueban una POLÍTICA y no una medición lo dicen.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filex import api as _api  # noqa: E402
from filex import cli as _cli  # noqa: E402
from filex import confinamiento as _conf  # noqa: E402
from filex import nucleo as _nucleo  # noqa: E402
from filex import watcher as _watch  # noqa: E402
from filex.servicio import Servicio, Trabajos  # noqa: E402
from filex.nucleo import FileX  # noqa: E402
from filex.watcher import Huella, Memoria, Vigilante  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(RAIZ, "corpus", "imagen")
PNG = os.path.join(CORPUS, "tipico.png")
JPG = os.path.join(CORPUS, "tipico.jpg")

#: Los cuatro ficheros de superficie. Ninguno puede llevar validación propia.
SUPERFICIES = {
    "cla": os.path.join(RAIZ, "filex", "cli.py"),
    "mcp": os.path.join(RAIZ, "filex", "mcp.py"),
    "watcher": os.path.join(RAIZ, "filex", "watcher.py"),
    "api": os.path.join(RAIZ, "filex", "api.py"),
}

_FX = None
_LOCK_FX = threading.Lock()


def fx_de(raices) -> FileX:
    """Un `FileX` con lista blanca, reaprovechando el sondeo de motores.

    Construir uno cuesta **23,6 s en frío y ~750 ms en caliente** —MEDIDO,
    `bench/hito7-superficies.md` §5.1—, y una suite que lo pagase por prueba
    sería una suite que nadie ejecuta. El sondeo no depende de las raíces, así
    que se reutiliza el objeto y se le cambia el confinamiento, que es
    exactamente lo que hace la capa MCP con los *roots* del cliente.
    """
    global _FX
    with _LOCK_FX:
        if _FX is None:
            _FX = FileX()
    fx = FileX.__new__(FileX)
    fx.motores = _FX.motores
    fx.grafo = _FX.grafo
    fx.confinamiento = _conf.Confinamiento(raices) if raices else None
    return fx


def codigo_de(ruta: str) -> str:
    """El fichero **sin comentarios ni cadenas**, por `tokenize`.

    Recortar por «la línea empieza por `#`» no vale: las cadenas de
    documentación de este proyecto explican precisamente las reglas que las
    pruebas buscan, y una prueba que se dispara al DOCUMENTAR la regla castiga
    justo lo que hay que premiar. Se comparan tokens de código.
    """
    import io as _io
    import tokenize as _tok

    with open(ruta, encoding="utf-8") as fh:
        fuente = fh.read()
    piezas = []
    for t in _tok.generate_tokens(_io.StringIO(fuente).readline):
        if t.type in (_tok.COMMENT, _tok.STRING, _tok.NL, _tok.NEWLINE):
            continue
        piezas.append(t.string)
    return " ".join(piezas)


def motivo_de(texto: str) -> str:
    """El motivo que una superficie le entrega a quien pregunta.

    Las cuatro responden JSON; lo que cambia es la clave (`motivo` en la CLA y
    el watcher, `error` o `motivo` en MCP y la API). R4 es una regla sobre el
    TEXTO que el otro lado lee, así que se compara el texto.
    """
    i = texto.find("{")
    if i < 0:
        return texto.strip()
    try:
        d = json.loads(texto[i:])
    except ValueError:
        return texto.strip()
    for clave in ("motivo", "error"):
        if d.get(clave):
            return str(d[clave])
    return ""


def _png_falso(destino: str) -> str:
    """Un `.png` que no es un PNG. Sirve para provocar un fallo del motor y
    comprobar que su `stderr` no cruza a ninguna superficie."""
    with open(destino, "wb") as fh:
        fh.write(b"esto no es un PNG, es texto plano, y magick lo va a rechazar\n" * 4)
    return destino


# ==========================================================================
# 1. R10 estructural: lo que NO puede haber en una superficie
# ==========================================================================


class R10Estructural(unittest.TestCase):
    """Se lee el código de las cuatro superficies. Es una prueba de POLÍTICA.

    No mide nada: comprueba que las piezas del confinamiento no están
    duplicadas. Es barata y es la única que atrapa una regresión el día que
    alguien «arregle» un caso raro copiando tres líneas de `confinamiento.py`
    dentro de una superficie.
    """

    @staticmethod
    def _fuente(nombre: str) -> str:
        with open(SUPERFICIES[nombre], encoding="utf-8") as fh:
            return fh.read()

    @staticmethod
    def _codigo(nombre: str) -> str:
        return codigo_de(SUPERFICIES[nombre])

    def test_ninguna_superficie_evalua_una_ruta(self):
        """Las piezas del predicado viven en `confinamiento.py`. Solo ahí.

        `os.path.realpath` es el que cierra el enlace simbólico (R7);
        `nombre_seguro` es R12; `MAX_COMPONENTES` es el tope léxico de R17. Que
        una superficie los nombre significa que está decidiendo por su cuenta.
        """
        prohibidas = ("realpath", "nombre_seguro", "MAX_COMPONENTES",
                      "MAX_LONGITUD", "_RESERVADOS", "_dentro", "_lexico_ok")
        for nombre in SUPERFICIES:
            codigo = self._codigo(nombre)
            for token in prohibidas:
                with self.subTest(superficie=nombre, token=token):
                    self.assertNotIn(token, codigo,
                                     f"{nombre} nombra '{token}': la validación "
                                     f"se está duplicando en la superficie")

    def test_ninguna_superficie_importa_subprocess(self):
        """*No hay puntos de invocación: hay uno* (`filex/invocacion.py`).

        `stdin=DEVNULL` antes de las banderas es la defensa, y una disciplina
        que hay que recordar en cada punto de invocación no es una defensa:
        `video-audio-mcp` pasa `-y` en sus 7 llamadas por `subprocess` y en
        ninguna de sus 32 por `ffmpeg-python`.
        """
        for nombre in SUPERFICIES:
            with self.subTest(superficie=nombre):
                codigo = self._codigo(nombre)
                self.assertNotIn("subprocess", codigo)
                # Y tampoco por la puerta de al lado: `invocacion.ejecutar` solo
                # se llama desde el núcleo y desde los adaptadores de motor.
                self.assertNotIn("ejecutar", codigo)

    def test_solo_el_nucleo_llama_a_nombre_seguro(self):
        """La regresión del fallo que ya se pagó.

        `nombre_seguro` estuvo escrito y probado desde el hito 1 **sin un solo
        llamante** fuera de su prueba, y FileX escribió 94 B en el flujo
        alternativo de un fichero ajeno devolviendo `veredicto: ok`. Esta
        prueba fija los llamantes legítimos: la definición y el núcleo.
        """
        llamantes = []
        paquete = os.path.join(RAIZ, "filex")
        for f in sorted(os.listdir(paquete)):
            if not f.endswith(".py"):
                continue
            with open(os.path.join(paquete, f), encoding="utf-8") as fh:
                cuerpo = fh.read()
            if "nombre_seguro(" in cuerpo:
                llamantes.append(f)
        self.assertEqual(llamantes, ["confinamiento.py", "nucleo.py"],
                         "alguien más está llamando (o dejando de llamar) a "
                         "nombre_seguro")

    def test_la_api_no_reimplementa_el_servicio(self):
        """La API es transporte: usa el mismo `Servicio` que la capa MCP.

        Esa clase se separó del protocolo en el hito 4 «para poder probarla sin
        levantar un servidor», y el hito 7 descubre para qué servía de verdad.

        **La afirmación no cambia; su dirección sí (N6).** Hasta la mudanza esto
        exigía `from .mcp import ...`, que probaba lo mismo con una forma que era
        en sí un defecto: la API importaba del módulo del PROTOCOLO. Ahora el
        servicio vive en `filex/servicio.py` y lo que se exige es lo de siempre
        —que la API no reimplemente el núcleo— por la puerta correcta. Que nadie
        siga entrando por `.mcp` lo comprueba `pruebas/test_cancelacion.py`.
        """
        self.assertIn("from .servicio import Servicio, Trabajos",
                      self._fuente("api"))
        self.assertNotIn("from .mcp import", self._fuente("api"))
        # Y el detalle que lo resume: **`filex/api.py` no importa `os`.** La
        # superficie que recibe rutas por la red no toca el módulo de rutas.
        import ast

        importados = set()
        for n in ast.walk(ast.parse(self._fuente("api"))):
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                for a in n.names:
                    importados.add((a.asname or a.name).split(".")[0])
        self.assertNotIn("os", importados)
        codigo = self._codigo("api")
        # `convertir` solo aparece como cadena (la ruta `/convertir`), y las
        # cadenas ya se han descontado: si aparece aquí es que alguien llamó a
        # `FileX.convertir` desde el transporte.
        self.assertNotIn("convertir", codigo)


# ==========================================================================
# 2. Los mismos vectores por las CUATRO superficies
# ==========================================================================


class _Adaptadores:
    """Cuatro funciones `(entrada, salida) -> texto de la respuesta`.

    El texto es lo que la superficie le entrega a quien pregunta. Que se
    comparen como texto y no como estructura es deliberado: R4 es una regla
    sobre lo que el otro lado LEE.
    """

    def __init__(self, raiz: str) -> None:
        self.raiz = raiz
        self.fx = fx_de([raiz])
        self.trabajos = Trabajos(os.path.join(raiz, "_trabajos"))
        self.servicio = Servicio(fx_de([raiz]), self.trabajos)
        self.srv = _api.construir(fx_de([raiz]), trabajos=self.trabajos,
                                  host="127.0.0.1", puerto=0)
        self.puerto = self.srv.server_address[1]
        self.hilo = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.hilo.start()

    def cerrar(self) -> None:
        self.srv.shutdown()
        self.srv.server_close()

    # ------------------------------------------------------------------ CLA

    def cla(self, entrada: str, salida: str) -> str:
        salidas = io.StringIO()
        with contextlib.redirect_stdout(salidas), contextlib.redirect_stderr(salidas):
            _cli.main(["--raiz", self.raiz, "convertir", entrada, salida, "--json"])
        return salidas.getvalue()

    # ------------------------------------------------------------------ MCP

    def mcp(self, entrada: str, salida: str) -> str:
        d = self.servicio.despachar("convert", {"entrada": entrada, "salida": salida})
        if d.get("job_id"):
            d = self._esperar_mcp(d["job_id"])
        return json.dumps(d, ensure_ascii=False)

    def _esperar_mcp(self, jid: str) -> dict:
        for _ in range(1200):
            d = self.servicio.despachar("job", {"job_id": jid, "accion": "resultado"})
            if d.get("estado") != "working":
                return d
            time.sleep(0.05)
        return {"estado": "TIMEOUT"}

    # -------------------------------------------------------------- watcher

    def watcher(self, entrada: str, salida: str) -> str:
        """El watcher no acepta una ruta de salida: la DERIVA del nombre de
        entrada. Se le da el directorio y el formato, que es su interfaz real."""
        v = Vigilante(fx_de([self.raiz]), [os.path.dirname(entrada) or self.raiz],
                      os.path.dirname(salida) or self.raiz,
                      os.path.splitext(salida)[1], memoria=Memoria(),
                      trabajos=self.trabajos, sobrescribir=True)
        # Se fabrica la huella a mano en vez de esperar al sondeo: la madurez
        # se prueba aparte, y aquí lo que se ejercita es el camino a disco.
        try:
            st = os.stat(entrada)
            h = Huella(entrada, st.st_size, st.st_mtime_ns)
        except OSError:
            h = Huella(entrada, 0, 0)
        r = v.atender(h)
        return json.dumps({"estado": r.estado, "motivo": r.motivo,
                           "veredicto": r.veredicto, "salida": r.salida,
                           "cobertura": r.cobertura}, ensure_ascii=False)

    # ------------------------------------------------------------------ API

    def api(self, entrada: str, salida: str) -> str:
        cod, d = self._http("POST", "/convertir",
                            {"entrada": entrada, "salida": salida})
        if d.get("job_id"):
            d = self._esperar_api(d["job_id"])
        return json.dumps(d, ensure_ascii=False)

    def _esperar_api(self, jid: str) -> dict:
        for _ in range(1200):
            _, d = self._http("GET", f"/trabajos/{jid}?accion=resultado")
            if d.get("estado") != "working":
                return d
            time.sleep(0.05)
        return {"estado": "TIMEOUT"}

    def _http(self, metodo: str, ruta: str, cuerpo=None, cabeceras=None, tope=60):
        url = f"http://127.0.0.1:{self.puerto}{ruta}"
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        cab = {"Content-Type": "application/json"} if cuerpo is not None else {}
        cab.update(cabeceras or {})
        req = urllib.request.Request(url, data=datos, headers=cab, method=metodo)
        try:
            with urllib.request.urlopen(req, timeout=tope) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            crudo = e.read()
            try:
                return e.code, json.loads(crudo.decode())
            except ValueError:
                return e.code, {"_crudo": crudo[:200].decode("utf-8", "replace")}

    @property
    def todas(self) -> dict:
        return {"cla": self.cla, "mcp": self.mcp,
                "watcher": self.watcher, "api": self.api}


class CuatroSuperficies(unittest.TestCase):
    """Los mismos vectores por las cuatro. **Esto es la prueba de R10.**"""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="filex-h7-")
        cls.dentro = os.path.join(cls.dir, "dentro")
        cls.destino = os.path.join(cls.dir, "salida")
        os.makedirs(cls.dentro)
        os.makedirs(cls.destino)
        shutil.copy2(PNG, os.path.join(cls.dentro, "bueno.png"))
        _png_falso(os.path.join(cls.dentro, "roto.png"))
        cls.ad = _Adaptadores(cls.dir)
        # El `stderr` real del motor sobre la entrada rota, para poder exigir
        # que NO aparezca en ninguna respuesta.
        conv = fx_de([cls.dir]).convertir(
            os.path.join(cls.dentro, "roto.png"),
            os.path.join(cls.destino, "roto_ref.webp"), {})
        cls.err_motor = (conv.saltos[-1].err if conv.saltos else "") or ""

    @classmethod
    def tearDownClass(cls):
        cls.ad.cerrar()
        shutil.rmtree(cls.dir, ignore_errors=True)

    # ------------------------------------------------------------ vectores

    def test_v1_ruta_fuera_de_la_lista_blanca(self):
        """Fuera de la raíz permitida: `ruta no accesible`, en las cuatro.

        La lista blanca es `cls.dir`; se pide algo del perfil del usuario.
        """
        fuera = os.path.join(os.path.expanduser("~"), "ajeno_h7.png")
        for nombre, f in self.ad.todas.items():
            with self.subTest(superficie=nombre):
                texto = f(fuera, os.path.join(self.destino, "v1.webp"))
                self.assertIn(_conf.MENSAJE_OPACO, texto)

    def test_v2_ruta_dentro_pero_inexistente_dice_lo_mismo(self):
        """R4: el MISMO mensaje para «prohibido» y para «no existe».

        Distinguirlos convierte el conversor en un oráculo de existencia sobre
        el disco ajeno. Se comparan los dos textos, no dos códigos.
        """
        fuera = os.path.join(os.path.expanduser("~"), "ajeno_h7.png")
        no_existe = os.path.join(self.dentro, "no_existe_h7.png")
        motivos = {}
        for nombre, f in self.ad.todas.items():
            with self.subTest(superficie=nombre):
                a = motivo_de(f(fuera, os.path.join(self.destino, "v2a.webp")))
                b = motivo_de(f(no_existe, os.path.join(self.destino, "v2b.webp")))
                self.assertEqual(a, b, f"{nombre} distingue prohibido de no-existe")
                self.assertEqual(a, _conf.MENSAJE_OPACO)
                motivos[nombre] = a
        # Y las cuatro dicen EXACTAMENTE lo mismo: si alguna llevara su propia
        # copia del predicado, aquí es donde se vería la divergencia.
        self.assertEqual(len(set(motivos.values())), 1, motivos)

    def test_v3_nombre_de_salida_reservado(self):
        """R12: `CON.webp` sigue siendo `CON`. Denegado en las cuatro.

        En el watcher el nombre de salida no lo escribe nadie: se DERIVA del de
        entrada, que es el caso interesante — una superficie que construye el
        nombre por su cuenta es la que puede saltarse R12 sin querer.
        """
        ent = os.path.join(self.dentro, "CON.png")
        for nombre, f in self.ad.todas.items():
            with self.subTest(superficie=nombre):
                salida = (os.path.join(self.destino, "CON.webp")
                          if nombre != "watcher" else
                          os.path.join(self.destino, "x.webp"))
                entrada = ent if nombre == "watcher" else os.path.join(
                    self.dentro, "bueno.png")
                texto = f(entrada, salida)
                self.assertIn(_conf.MENSAJE_OPACO, texto)

    def test_v4_nombre_de_salida_con_flujo_alternativo(self):
        """R12/W9: `v4:oculto.webp` escribe en el flujo `oculto.webp` del
        fichero `v4`. **Es el único de los 29 vectores que la referencia
        oficial concede**, y el que FileX ya sirvió una vez: 94 B en el ADS de
        un fichero ajeno con `veredicto: ok`.

        El nombre conserva la extensión `.webp` a propósito: con
        `v4.webp:oculto` la extensión pasa a ser `webp:oculto`, no hay motor que
        la escriba y el rechazo vendría del grafo, no de R12. **Un vector que se
        para antes de llegar a la regla que se quiere probar no prueba nada.**
        """
        for nombre, f in self.ad.todas.items():
            with self.subTest(superficie=nombre):
                if nombre == "watcher":
                    entrada = os.path.join(self.dentro, "bueno:oculto.png")
                    salida = os.path.join(self.destino, "x.webp")
                else:
                    entrada = os.path.join(self.dentro, "bueno.png")
                    salida = os.path.join(self.destino, "v4:oculto.webp")
                self.assertEqual(motivo_de(f(entrada, salida)), _conf.MENSAJE_OPACO)
        # Y no quedó nada escrito: ni el fichero, ni su flujo alternativo.
        self.assertFalse(any(n.startswith("v4") for n in os.listdir(self.destino)))

    def test_v5_conversion_legitima_y_el_punto_5_cubierto(self):
        """Las cuatro convierten, y las cuatro traen el punto 5 CUBIERTO.

        No es un adorno: sin censo **49 de las 53 salidas del patrón oro bajan
        de `ok` a `ok_parcial`**, y el censo solo se puede tomar dentro de la
        conversión. Que las cuatro superficies lo traigan cubierto demuestra que
        ninguna convierte primero y verifica después.
        """
        ent = os.path.join(self.dentro, "bueno.png")
        veredictos = {}
        for nombre, f in self.ad.todas.items():
            with self.subTest(superficie=nombre):
                sub = os.path.join(self.destino, f"v5_{nombre}")
                os.makedirs(sub, exist_ok=True)
                salida = os.path.join(sub, "bueno.webp")
                texto = f(ent, salida)
                self.assertNotIn(_conf.MENSAJE_OPACO, texto)
                self.assertTrue(os.path.isfile(salida),
                                f"{nombre} no dejó la salida: {texto[:300]}")
                d = json.loads(texto[texto.find("{"):])
                veredictos[nombre] = (d.get("veredicto")
                                      or d.get("saltos", [{}])[-1].get("veredicto"))
                if "cobertura" in d:
                    # CLA y watcher publican la cobertura entera.
                    self.assertTrue(d["cobertura"].get("5_escritura"), nombre)
                elif d.get("saltos"):
                    self.assertTrue(d["saltos"][-1]["cobertura"].get("5_escritura"))
        # Las cuatro dan el mismo veredicto sobre la misma conversión, y ninguna
        # dice `no_verificado`: **el censo se tomó dentro** en las cuatro. MCP y
        # la API no publican la `cobertura` entera —presupuesto de tokens— pero
        # sin censo el veredicto que traerían sería otro.
        self.assertEqual(len(set(veredictos.values())), 1, veredictos)
        self.assertNotIn("no_verificado", set(veredictos.values()))

    def test_v6_el_stderr_del_motor_no_cruza_a_ninguna_superficie(self):
        """*Nunca devolver `stderr` crudo*: el error de un motor puede dirigir
        la siguiente acción del agente. Los tres servidores de referencia
        reenvían 884-1.228 tokens de banner de compilación de ffmpeg."""
        if not self.err_motor.strip():
            self.skipTest("el motor no produjo stderr con esta entrada")
        pistas = [l.strip() for l in self.err_motor.splitlines() if len(l.strip()) > 25]
        self.assertTrue(pistas, "stderr sin líneas útiles para comparar")
        ent = os.path.join(self.dentro, "roto.png")
        for nombre, f in self.ad.todas.items():
            with self.subTest(superficie=nombre):
                texto = f(ent, os.path.join(self.destino, f"v6_{nombre}.webp"))
                for pista in pistas:
                    self.assertNotIn(pista, texto,
                                     f"{nombre} filtró stderr del motor")


# ==========================================================================
# 3. El watcher
# ==========================================================================


_ESCRITOR = (
    "import sys, time\n"
    "origen, destino, trozos, pausa = sys.argv[1:5]\n"
    "trozos = int(trozos); pausa = float(pausa)\n"
    "datos = open(origen, 'rb').read()\n"
    "n = max(1, len(datos) // trozos)\n"
    "fh = open(destino, 'wb')\n"
    "for i in range(trozos):\n"
    "    fh.write(datos[i*n:(i+1)*n] if i < trozos-1 else datos[i*n:])\n"
    "    fh.flush()\n"
    "    time.sleep(pausa)\n"
    "fh.close()\n"
)


class WatcherCompletitud(unittest.TestCase):
    """«¿Está el fichero completo?» se MIDE, no se supone."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="filex-h7w-")
        self.ent = os.path.join(self.dir, "ent")
        self.sal = os.path.join(self.dir, "sal")
        os.makedirs(self.ent)
        os.makedirs(self.sal)
        self.fx = fx_de([self.dir])

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _escribir_despacio(self, destino, trozos=8, pausa=0.12):
        return subprocess.Popen(
            [sys.executable, "-c", _ESCRITOR, PNG, destino, str(trozos), str(pausa)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)

    @unittest.skipUnless(os.name == "nt", "el cerrojo de renombrado es de Windows")
    def test_el_cerrojo_ve_al_escritor_y_open_rb_no(self):
        """MEDIDO (`bench/hito7-superficies.md` §3.2), y es el resultado que
        decide el diseño: con el fichero abierto por otro proceso en modo
        escritura, `os.replace(p, p)` falla con WinError 32 y `open(p, 'rb')`
        **no falla**. «¿Puedo leerlo?» no es una prueba de completitud."""
        p = os.path.join(self.ent, "abierto.bin")
        with open(p, "wb") as fh:
            fh.write(b"x" * 512)
        self.assertTrue(_watch._estable_en_disco(p))
        fh = open(p, "ab")
        try:
            self.assertFalse(_watch._estable_en_disco(p))
            with open(p, "rb") as lector:            # y leer SÍ se puede
                self.assertEqual(len(lector.read(16)), 16)
        finally:
            fh.close()
        self.assertTrue(_watch._estable_en_disco(p))

    def test_un_solo_sondeo_convierte_ficheros_a_medias(self):
        """El watcher ingenuo. MEDIDO: con `estables=1` y sin cerrojo convierte
        **5 veces** el mismo fichero, **4 de ellas incompletas** (6 426 / 14 994
        / 23 562 / 34 272 B de 42 855), y las cuatro dan `fallo`."""
        v = Vigilante(self.fx, [self.ent], self.sal, "webp", intervalo=0.15,
                      estables=1, cerrojo=False, memoria=Memoria(),
                      sobrescribir=True)
        destino = os.path.join(self.ent, "lento.png")
        proc = self._escribir_despacio(destino)
        tamanos = []
        for _ in range(60):
            for h in v.maduros():
                tamanos.append(h.tamano)
            if tamanos and proc.poll() is not None:
                break
            time.sleep(0.15)
        proc.wait(timeout=30)
        real = os.path.getsize(destino)
        self.assertTrue(tamanos, "el watcher ingenuo no vio nada")
        self.assertTrue(any(t < real for t in tamanos),
                        f"se esperaba ver el fichero a medias: {tamanos} de {real}")

    def test_estabilidad_mas_cerrojo_solo_ve_el_fichero_completo(self):
        """La configuración por defecto. MEDIDO: **1 sola conversión** y sobre
        los 42 855 B completos, incluso con el escritor haciendo una pausa más
        larga que el intervalo de sondeo — el caso que la estabilidad de `stat`
        sola **no** ve (§3.3)."""
        v = Vigilante(self.fx, [self.ent], self.sal, "webp", intervalo=0.15,
                      estables=2, cerrojo=True, memoria=Memoria())
        destino = os.path.join(self.ent, "lento.png")
        proc = self._escribir_despacio(destino)
        vistos, hechos = [], []
        for _ in range(80):
            for h in v.maduros():
                vistos.append(h.tamano)
                hechos.append(v.atender(h))     # marca la memoria: no se repite
            if hechos and proc.poll() is not None:
                break
            time.sleep(0.15)
        proc.wait(timeout=30)
        time.sleep(0.3)
        for h in v.maduros():                   # un ciclo más, ya sin escritor
            vistos.append(h.tamano)
            hechos.append(v.atender(h))
        real = os.path.getsize(destino)
        self.assertEqual(vistos, [real],
                         f"se esperaba una sola observación completa: {vistos} de {real}")
        self.assertEqual([r.estado for r in hechos], ["convertido"])


class WatcherDuplicados(unittest.TestCase):
    """«Un fichero que aparece dos veces». MEDIDO en §4."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="filex-h7d-")
        self.ent = os.path.join(self.dir, "ent")
        self.sal = os.path.join(self.dir, "sal")
        os.makedirs(self.ent)
        os.makedirs(self.sal)
        self.fx = fx_de([self.dir])
        self.v = Vigilante(self.fx, [self.ent], self.sal, "webp", intervalo=0.0,
                           estables=2, cerrojo=True, memoria=Memoria())

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _ciclos(self, n=6):
        hechos = []
        for _ in range(n):
            for h in self.v.maduros():
                hechos.append(self.v.atender(h))
            time.sleep(0.02)
        return hechos

    def test_el_mismo_fichero_quieto_se_convierte_una_sola_vez(self):
        """MEDIDO: 8 sondeos → 1 conversión; otros 8 → 0."""
        shutil.copy2(PNG, os.path.join(self.ent, "uno.png"))
        self.assertEqual(len(self._ciclos(8)), 1)
        self.assertEqual(len(self._ciclos(8)), 0)

    def test_renombrar_produce_una_salida_nueva(self):
        """MEDIDO, y es una DECISIÓN, no un descuido: la identidad lleva la
        ruta, así que `uno.png → dos.png` es un fichero nuevo. Tiene que serlo:
        su salida se llama `dos.webp` y nadie la ha escrito todavía."""
        a = os.path.join(self.ent, "uno.png")
        shutil.copy2(PNG, a)
        self._ciclos(6)
        os.rename(a, os.path.join(self.ent, "dos.png"))
        hechos = self._ciclos(6)
        self.assertEqual(len(hechos), 1)
        self.assertEqual(hechos[0].estado, "convertido")
        self.assertTrue(os.path.isfile(os.path.join(self.sal, "uno.webp")))
        self.assertTrue(os.path.isfile(os.path.join(self.sal, "dos.webp")))

    def test_reescribir_en_sitio_no_sobrescribe_en_silencio(self):
        """R9. MEDIDO: la reescritura produce una huella nueva —y debe—, pero
        el destino ya existe y **la conversión se salta con motivo**, no se
        pisa. Es la mitad del par: la huella detecta, R9 decide."""
        a = os.path.join(self.ent, "uno.png")
        shutil.copy2(PNG, a)
        self._ciclos(6)
        time.sleep(0.02)
        with open(a, "ab") as fh:
            fh.write(b"\x00" * 8)
        hechos = self._ciclos(6)
        self.assertEqual(len(hechos), 1)
        self.assertEqual(hechos[0].estado, "saltado")
        self.assertEqual(hechos[0].motivo, "el destino ya existe")

    def test_un_touch_sin_cambio_de_bytes_cuenta_como_fichero_nuevo(self):
        """El PRECIO declarado de no hacer hash del contenido.

        MEDIDO (§4.3): `stat` cuesta 0,016–0,021 ms y `sha256` 0,44 ms sobre
        42 KB y **382,85 ms sobre 72 MB** — ×21 y ×23 311. Se paga un `touch`
        de más, no un recorrido del fichero entero por sondeo.
        """
        a = os.path.join(self.ent, "uno.png")
        shutil.copy2(PNG, a)
        self._ciclos(6)
        t = os.path.getmtime(a)
        os.utime(a, (t + 10, t + 10))
        hechos = self._ciclos(6)
        self.assertEqual(len(hechos), 1)
        self.assertEqual(hechos[0].estado, "saltado")   # R9 lo detiene igual

    def test_dos_entradas_con_el_mismo_tallo_colisionan_y_R9_lo_atrapa(self):
        """MEDIDO en la primera prueba de humo del watcher por línea de órdenes:
        `tipico.png` y `tipico.jpg` producen los dos `tipico.webp`.

        **No se pierde nada** —el segundo sale `saltado` con motivo—, pero el
        usuario pidió dos conversiones y obtiene una. `--conservar-extension`
        lo evita, y la prueba fija las dos ramas.
        """
        shutil.copy2(PNG, os.path.join(self.ent, "mismo.png"))
        shutil.copy2(JPG, os.path.join(self.ent, "mismo.jpg"))
        hechos = self._ciclos(6)
        self.assertEqual(sorted(r.estado for r in hechos),
                         ["convertido", "saltado"])
        self.assertEqual(len(os.listdir(self.sal)), 1)

        sal2 = os.path.join(self.dir, "sal2")
        os.makedirs(sal2)
        v2 = Vigilante(self.fx, [self.ent], sal2, "webp", estables=1,
                       memoria=Memoria(), conservar_extension=True)
        hechos2 = v2.paso()
        self.assertEqual(sorted(r.estado for r in hechos2),
                         ["convertido", "convertido"])
        self.assertEqual(sorted(os.listdir(sal2)),
                         ["mismo.jpg.webp", "mismo.png.webp"])

    def test_la_memoria_sobrevive_a_un_reinicio(self):
        """Sin persistencia, reiniciar el watcher reconvierte la carpeta entera."""
        fichero = os.path.join(self.dir, "memoria.json")
        shutil.copy2(PNG, os.path.join(self.ent, "uno.png"))
        v1 = Vigilante(self.fx, [self.ent], self.sal, "webp", estables=1,
                       cerrojo=True, memoria=Memoria(fichero))
        self.assertEqual(len(v1.paso()), 1)
        v2 = Vigilante(self.fx, [self.ent], self.sal, "webp", estables=1,
                       cerrojo=True, memoria=Memoria(fichero))
        self.assertEqual(len(v2.paso()), 0)


class WatcherNucleo(unittest.TestCase):
    """El watcher se apoya en el núcleo: ni valida, ni verifica aparte."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="filex-h7n-")
        self.ent = os.path.join(self.dir, "ent")
        self.sal = os.path.join(self.dir, "sal")
        os.makedirs(self.ent)
        os.makedirs(self.sal)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_se_niega_a_arrancar_fuera_de_la_lista_blanca(self):
        """Y con el mensaje opaco: un watcher que dijera «esa carpeta no
        existe» sería un mapa del disco ajeno."""
        fx = fx_de([self.dir])
        v = Vigilante(fx, [os.path.expanduser("~")], self.sal, "webp")
        with self.assertRaises(_conf.Denegado) as ctx:
            v.comprobar_raices()
        self.assertEqual(str(ctx.exception), _conf.MENSAJE_OPACO)

    def test_el_punto_5_llega_cubierto_y_no_lo_verifica_el_watcher(self):
        """El watcher no llama al contrato. No puede: el punto 5 se toma dentro
        del `with` del desechable, y **sin censo 49 de 53 salidas del patrón oro
        bajan a `ok_parcial`**."""
        codigo = codigo_de(SUPERFICIES["watcher"])
        self.assertNotIn("verificar", codigo)
        self.assertNotIn("contrato", codigo)
        shutil.copy2(PNG, os.path.join(self.ent, "uno.png"))
        v = Vigilante(fx_de([self.dir]), [self.ent], self.sal, "webp",
                      estables=1, memoria=Memoria())
        r = v.paso()[0]
        self.assertEqual(r.estado, "convertido")
        self.assertTrue(r.cobertura.get("5_escritura"))

    def test_el_trabajo_del_watcher_lo_ve_la_capa_mcp(self):
        """*«Un JSON por trabajo sirve además a la CLI, al watcher y a la API:
        los cuatro frentes ven el mismo trabajo»* (`PLAN-ORQUESTADOR.md` §5.3).

        No era una promesa retórica: el registro está persistido en disco y una
        superficie lee el trabajo que creó otra.
        """
        trabajos = Trabajos(os.path.join(self.dir, "_t"))
        shutil.copy2(PNG, os.path.join(self.ent, "uno.png"))
        v = Vigilante(fx_de([self.dir]), [self.ent], self.sal, "webp",
                      estables=1, memoria=Memoria(), trabajos=trabajos)
        r = v.paso()[0]
        self.assertTrue(r.job_id)
        # Otro registro, apuntando al mismo directorio: nada en memoria.
        otro = Trabajos(os.path.join(self.dir, "_t"))
        servicio = Servicio(fx_de([self.dir]), otro)
        d = servicio.despachar("job", {"job_id": r.job_id, "accion": "resultado"})
        self.assertEqual(d.get("estado"), "completed")
        self.assertEqual(d.get("ruta_salida"), r.salida)

    def test_el_filtro_de_extension_pregunta_al_grafo(self):
        """No hay lista de extensiones escrita a mano: se pregunta si hay
        camino, que es la misma respuesta que da `list_targets` — *«lo que no
        está aquí no se puede hacer»*."""
        shutil.copy2(PNG, os.path.join(self.ent, "uno.png"))
        with open(os.path.join(self.ent, "dos.xyzzy"), "wb") as fh:
            fh.write(b"formato inexistente")
        v = Vigilante(fx_de([self.dir]), [self.ent], self.sal, "webp",
                      estables=1, memoria=Memoria())
        rutas = [os.path.basename(h.ruta) for h in v.maduros()]
        self.assertEqual(rutas, ["uno.png"])


# ==========================================================================
# 4. La API HTTP
# ==========================================================================


class ApiDefensas(unittest.TestCase):
    """Las defensas de PROTOCOLO. Ninguna mira el disco: no son R10, son HTTP.

    Todas MEDIDAS en `bench/hito7-superficies.md` §6.
    """

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="filex-h7a-")
        shutil.copy2(PNG, os.path.join(cls.dir, "bueno.png"))
        cls.srv = _api.construir(fx_de([cls.dir]),
                                 trabajos=Trabajos(os.path.join(cls.dir, "_t")),
                                 host="127.0.0.1", puerto=0)
        cls.puerto = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        shutil.rmtree(cls.dir, ignore_errors=True)

    def _http(self, metodo, ruta, cuerpo=None, cabeceras=None, crudo=None):
        url = f"http://127.0.0.1:{self.puerto}{ruta}"
        if crudo is not None:
            datos, cab = crudo[0], dict(crudo[1])
        else:
            datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
            cab = {"Content-Type": "application/json"} if cuerpo is not None else {}
        cab.update(cabeceras or {})
        req = urllib.request.Request(url, data=datos, headers=cab, method=metodo)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                b = r.read()
                return r.status, json.loads(b.decode()), len(b)
        except urllib.error.HTTPError as e:
            b = e.read()
            try:
                return e.code, json.loads(b.decode()), len(b)
            except ValueError:
                return e.code, {"_crudo": b[:120].decode("utf-8", "replace")}, len(b)

    def test_salud_responde(self):
        cod, d, _ = self._http("GET", "/salud")
        self.assertEqual(cod, 200)
        self.assertIn("aristas", d)
        self.assertTrue(d["confinado"])

    def test_host_ajeno_rechazado(self):
        """DNS rebinding: el navegador resuelve `malo.example` a 127.0.0.1 y
        manda ese nombre en `Host`. MEDIDO: 421."""
        cod, d, _ = self._http("GET", "/salud", cabeceras={"Host": "malo.example"})
        self.assertEqual(cod, 421)

    def test_peticion_con_origin_rechazada(self):
        """Ninguna petición legítima a esta API viene de una página web."""
        cod, d, _ = self._http("GET", "/salud",
                               cabeceras={"Origin": "http://evil.test"})
        self.assertEqual(cod, 403)

    def test_post_de_formulario_rechazado(self):
        """`application/x-www-form-urlencoded` es lo ÚNICO que un `<form>`
        puede mandar sin *preflight*. Exigir `application/json` cierra el CSRF
        sin inventar un token: el *preflight* no se contesta."""
        cod, d, _ = self._http("POST", "/convertir",
                               crudo=(b"entrada=x",
                                      {"Content-Type": "application/x-www-form-urlencoded"}))
        self.assertEqual(cod, 415)

    def test_options_no_abre_cors(self):
        cod, d, _ = self._http("OPTIONS", "/salud")
        self.assertEqual(cod, 405)

    def test_sin_cabeceras_cors(self):
        url = f"http://127.0.0.1:{self.puerto}/salud"
        with urllib.request.urlopen(url, timeout=30) as r:
            cabeceras = {k.lower() for k in r.headers.keys()}
        self.assertNotIn("access-control-allow-origin", cabeceras)

    def test_cuerpo_demasiado_grande(self):
        """Sin tope, `rfile.read(Content-Length)` es una reserva de memoria
        dictada por el cliente. Aquí solo viajan rutas."""
        grande = json.dumps({"entrada": "x" * (_api.MAX_CUERPO + 10), "salida": "y"}).encode()
        cod, d, _ = self._http("POST", "/convertir",
                               crudo=(grande, {"Content-Type": "application/json"}))
        self.assertEqual(cod, 413)

    def test_metodos_y_rutas_desconocidos(self):
        self.assertEqual(self._http("PUT", "/convertir",
                                    crudo=(b"{}", {"Content-Type": "application/json"}))[0], 405)
        self.assertEqual(self._http("GET", "/no-existe")[0], 404)

    def test_es_loopback(self):
        for bueno in ("127.0.0.1", "127.0.0.1:8756", "localhost", "[::1]", "[::1]:8756"):
            self.assertTrue(_api.es_loopback(bueno), bueno)
        for malo in ("192.168.1.107", "malo.example", "0.0.0.0", ""):
            self.assertFalse(_api.es_loopback(malo), malo)

    def test_se_niega_a_escuchar_fuera_de_loopback_sin_bandera(self):
        """MEDIDO: `rc=2` y un mensaje que dice el motivo — esta API **no
        autentica a nadie**, así que la lista blanca protege el disco pero no
        decide quién pregunta."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = _api.main(["--host", "0.0.0.0", "--puerto", "8799"])
        self.assertEqual(rc, 2)
        self.assertIn("permitir-red", err.getvalue())

    def test_la_respuesta_no_lleva_contenido(self):
        """*Ruta y metadatos, nunca contenido* — y «contenido» incluye base64.
        MEDIDO: el asa cuesta **121 B** y el resultado **278 B** para un fichero
        de 13 516 B (×111 y ×48)."""
        d_sal = os.path.join(self.dir, "sal")
        os.makedirs(d_sal, exist_ok=True)
        cod, d, n = self._http("POST", "/convertir", {
            "entrada": os.path.join(self.dir, "bueno.png").replace("\\", "/"),
            "salida": os.path.join(d_sal, "b.webp").replace("\\", "/")})
        self.assertEqual(cod, 202)
        self.assertLess(n, 512)
        for _ in range(1200):
            cod, res, n2 = self._http("GET", f"/trabajos/{d['job_id']}?accion=resultado")
            if res.get("estado") != "working":
                break
            time.sleep(0.05)
        self.assertEqual(res.get("estado"), "completed")
        self.assertLess(n2, 1024)
        bytes_reales = os.path.getsize(os.path.join(d_sal, "b.webp"))
        self.assertEqual(res["bytes"], bytes_reales)
        self.assertLess(n2, bytes_reales)          # la respuesta pesa menos que el fichero

    def test_el_asa_llega_al_empezar(self):
        """§5.2: *toda operación larga devuelve un `job_id` al empezar. No
        bloquea, nunca condicionado a un booleano*. Un `ffmpeg_convert` de un
        clip de 5 s superó los 900 s del timeout del cliente **con la conversión
        ya terminada en disco**."""
        d_sal = os.path.join(self.dir, "sal2")
        os.makedirs(d_sal, exist_ok=True)
        t0 = time.perf_counter()
        cod, d, _ = self._http("POST", "/convertir", {
            "entrada": os.path.join(self.dir, "bueno.png").replace("\\", "/"),
            "salida": os.path.join(d_sal, "c.webp").replace("\\", "/")})
        ms = (time.perf_counter() - t0) * 1000
        self.assertEqual(cod, 202)
        self.assertEqual(d["estado"], "working")
        self.assertIn("camino", d)
        # El asa llega antes de que el motor termine: si bloqueara, este número
        # sería el de la conversión (≈300 ms para png→webp).
        self.assertLess(ms, 250)

    def test_sin_camino_falla_al_instante_y_sin_asa(self):
        """*El silencio es el modo de fallo peligroso, no el error.* Que no
        haya camino se sabe en microsegundos: gastar dos turnos en decir «no»
        es lo que hay que evitar."""
        cod, d, _ = self._http("POST", "/convertir", {
            "entrada": os.path.join(self.dir, "bueno.png").replace("\\", "/"),
            "salida": os.path.join(self.dir, "x.xyzzy").replace("\\", "/")})
        self.assertEqual(cod, 400)
        self.assertNotIn("job_id", d)
        self.assertIn("sugerencia", d)


class ApiConcurrencia(unittest.TestCase):
    """La primera superficie con concurrencia real. §5 del informe."""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="filex-h7c-")
        shutil.copy2(PNG, os.path.join(cls.dir, "png.png"))
        shutil.copy2(JPG, os.path.join(cls.dir, "jpg.jpg"))
        cls.srv = _api.construir(fx_de([cls.dir]),
                                 trabajos=Trabajos(os.path.join(cls.dir, "_t")),
                                 host="127.0.0.1", puerto=0)
        cls.puerto = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        shutil.rmtree(cls.dir, ignore_errors=True)

    def _post(self, entrada, salida):
        url = f"http://127.0.0.1:{self.puerto}/convertir"
        datos = json.dumps({"entrada": entrada.replace("\\", "/"),
                            "salida": salida.replace("\\", "/")}).encode()
        req = urllib.request.Request(url, data=datos,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode())

    def _esperar(self, jid):
        url = f"http://127.0.0.1:{self.puerto}/trabajos/{jid}?accion=resultado"
        for _ in range(2400):
            with urllib.request.urlopen(url, timeout=60) as r:
                d = json.loads(r.read().decode())
            if d.get("estado") != "working":
                return d
            time.sleep(0.05)
        return {"estado": "TIMEOUT"}

    def test_ocho_conversiones_simultaneas_no_se_pisan(self):
        """MEDIDO: 8 asas en **69,6 ms**, las 8 `completed`, 8 ficheros en el
        destino y **cero** ficheros no declarados — el `mkdtemp` de R18 es por
        conversión, así que el censo del punto 5 tampoco se contamina."""
        d_sal = os.path.join(self.dir, "ocho")
        os.makedirs(d_sal, exist_ok=True)
        ids, cerrojo = [], threading.Lock()

        def lanzar(i):
            cod, d = self._post(os.path.join(self.dir, "png.png"),
                                os.path.join(d_sal, f"s{i}.webp"))
            with cerrojo:
                ids.append((cod, d.get("job_id")))

        hilos = [threading.Thread(target=lanzar, args=(i,)) for i in range(8)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        self.assertEqual([c for c, _ in ids], [202] * 8)
        resultados = [self._esperar(j) for _, j in ids]
        self.assertEqual([r["estado"] for r in resultados], ["completed"] * 8)
        self.assertEqual(len(os.listdir(d_sal)), 8)
        for r in resultados:
            self.assertNotIn("ficheros_no_declarados", r)

    def test_dos_peticiones_al_mismo_destino_no_devuelven_dos_ok(self):
        """**La regresión del hallazgo del hito** (`bench/hito7-superficies.md`
        §5.3). Antes del cerrojo del núcleo, tres peticiones simultáneas con
        tres entradas distintas y la misma salida devolvían **las tres `ok`**
        declarando 13 516 / 14 402 / 647 580 B, y en el disco había **un solo
        fichero**. Dos de las tres describían un fichero que ya no existía.

        El contrato no puede atraparlo: juzga la salida dentro del desechable, y
        el atropello ocurre en el `move` al destino.
        """
        d_sal = os.path.join(self.dir, "choque")
        os.makedirs(d_sal, exist_ok=True)
        sal = os.path.join(d_sal, "choque.webp")
        res, cerrojo = [], threading.Lock()

        def lanzar(entrada):
            cod, d = self._post(entrada, sal)
            fin = self._esperar(d["job_id"]) if d.get("job_id") else d
            with cerrojo:
                res.append(fin)

        hilos = [threading.Thread(target=lanzar, args=(os.path.join(self.dir, n),))
                 for n in ("png.png", "jpg.jpg", "png.png")]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()

        exitos = [r for r in res if r.get("ok")]
        self.assertEqual(len(exitos), 1,
                         "dos conversiones simultáneas al mismo destino no "
                         "pueden devolver dos éxitos")
        self.assertEqual(len(os.listdir(d_sal)), 1)
        reales = os.path.getsize(sal)
        self.assertEqual(exitos[0]["bytes"], reales,
                         "el éxito declara un tamaño que no es el del fichero")
        for r in res:
            if not r.get("ok"):
                self.assertIn("escribiendo ya esa ruta", r.get("motivo", ""))


class NucleoDestinoEnCurso(unittest.TestCase):
    """El cerrojo de destino, probado donde vive: en el núcleo, no en la API."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="filex-h7r-")
        shutil.copy2(PNG, os.path.join(self.dir, "a.png"))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_reservar_y_soltar(self):
        p = os.path.join(self.dir, "x.webp")
        self.assertTrue(_nucleo._reservar_destino(p))
        self.assertFalse(_nucleo._reservar_destino(p))
        # R3: la comparación es `normcase`, así que en Windows no se escapa
        # cambiando la caja de una letra.
        self.assertFalse(_nucleo._reservar_destino(p.upper() if os.name == "nt" else p))
        _nucleo._soltar_destino(p)
        self.assertTrue(_nucleo._reservar_destino(p))
        _nucleo._soltar_destino(p)

    def test_convertir_rechaza_un_destino_reservado(self):
        fx = fx_de([self.dir])
        sal = os.path.join(self.dir, "x.webp")
        self.assertTrue(_nucleo._reservar_destino(sal))
        try:
            conv = fx.convertir(os.path.join(self.dir, "a.png"), sal, {})
        finally:
            _nucleo._soltar_destino(sal)
        self.assertFalse(conv.ok)
        self.assertIn("escribiendo ya esa ruta", conv.motivo)
        self.assertFalse(os.path.exists(sal))

    def test_el_cerrojo_se_suelta_aunque_la_conversion_falle(self):
        """Si no se soltara en el `finally`, un fallo dejaría el destino
        bloqueado para siempre — y eso convierte una defensa en una avería."""
        fx = fx_de([self.dir])
        roto = _png_falso(os.path.join(self.dir, "roto.png"))
        sal = os.path.join(self.dir, "y.webp")
        conv = fx.convertir(roto, sal, {})
        self.assertFalse(conv.ok)
        self.assertTrue(_nucleo._reservar_destino(sal))
        _nucleo._soltar_destino(sal)


if __name__ == "__main__":
    unittest.main(verbosity=2)

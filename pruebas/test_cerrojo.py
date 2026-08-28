"""El cerrojo de destino, probado ENTRE PROCESOS de verdad.

    python -m unittest pruebas.test_cerrojo -v

**Por qué un fichero de pruebas propio y no una clase más en `test_hito7.py`.**
El hito 7 cerró la carrera por el mismo destino con un `set` en memoria, y lo
probó con **hilos** (`ApiConcurrencia`, `NucleoDestinoEnCurso`). Esas pruebas
pasaban al 100 % mientras el agujero seguía abierto, porque **un hilo no es un
proceso**: el `set` los excluye a todos dentro del intérprete y a ninguno fuera.
Una prueba que no puede fallar por el fallo que dice cubrir no es una prueba de
ese fallo. Aquí todo se lanza con `subprocess`, que es lo único que distingue
las dos cosas.

Lo que mide cada clase está en `bench/cerrojo-de-maquina.md`:

* `CarreraEntreProcesos`  — §2: el fallo reproducido, y el mismo caso cerrado.
* `DuenoMuerto`           — §4: `taskkill /F` no ejecuta ningún `finally`.
* `TerceroQueNoCoopera`   — §5: la mitad de DETECCIÓN, la lección de L1.
* `UnSoloProceso`         — §7: que el caso normal, que es el 99 %, no se rompe.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from filex import nucleo  # noqa: E402
from filex.nucleo import FileX  # noqa: E402

CORPUS = os.path.join(RAIZ, "corpus", "imagen")
PNG = os.path.join(CORPUS, "tipico.png")
JPG = os.path.join(CORPUS, "tipico.jpg")
ES_WINDOWS = sys.platform == "win32"

#: Tope de TODO lo que se lanza aquí. `CLAUDE.md` §3: timeouts explícitos en
#: todo, que estos procesos dejan huérfanos vivos 13 minutos.
TOPE = 300


# --------------------------------------------------------------------------
# Los papeles que se lanzan como proceso aparte (ver `main()` al final)
# --------------------------------------------------------------------------

def _papel_convertidor(arg: dict) -> int:
    fx = FileX(raices_lectura=[arg["--dir"]])
    open(arg["--listo"], "w").close()
    print("LISTO", flush=True)
    t0 = time.perf_counter()
    while not os.path.exists(arg["--go"]):
        if time.perf_counter() - t0 > TOPE:
            return 2
        time.sleep(0.001)
    conv = fx.convertir(arg["--entrada"], arg["--salida"], {}, timeout=TOPE)
    print(json.dumps({"ok": conv.ok, "motivo": conv.motivo,
                      "bytes": (os.path.getsize(arg["--salida"])
                                if os.path.exists(arg["--salida"]) else None)},
                     ensure_ascii=False), flush=True)
    return 0


def _papel_reservador(arg: dict) -> int:
    """Solo toma el candado del destino y se queda quieto. No convierte: la
    pregunta es del cerrojo, no del motor."""
    ok = nucleo._reservar_destino(arg["--salida"])
    print(json.dumps({"reservado": ok}), flush=True)
    time.sleep(TOPE)
    return 0


def _papel_tercero(arg: dict) -> int:
    """Un proceso que NO es FileX, con la ruta de salida abierta. No sabe que
    los candados existen: es el navegador bajando un fichero encima."""
    f = open(arg["--salida"], "wb")
    f.write(b"SOY-UN-TERCERO" + b"\0" * 4000)
    f.flush()
    print("OCUPADO", flush=True)
    time.sleep(TOPE)
    return 0


PAPELES = {"convertidor": _papel_convertidor, "reservador": _papel_reservador,
           "tercero": _papel_tercero}


# --------------------------------------------------------------------------
# Utilidades del lado del padre
# --------------------------------------------------------------------------

def _lanzar(papel: str, modo: str = "maquina", **kw) -> subprocess.Popen:
    argv = [sys.executable, os.path.abspath(__file__), "--papel", papel]
    for k, v in kw.items():
        argv += ["--" + k, str(v)]
    return subprocess.Popen(
        argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
        cwd=RAIZ, env=dict(os.environ, FILEX_CERROJO_DESTINO=modo,
                           PYTHONIOENCODING="utf-8"))


def _matar(p: subprocess.Popen) -> None:
    """`taskkill /F /T`, que es lo que NO ejecuta ningún `finally`."""
    if ES_WINDOWS:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=60)
    else:
        p.kill()
    try:
        p.wait(timeout=60)
    except subprocess.TimeoutExpired:
        pass


def _ultima_linea_json(salida: str) -> dict:
    for linea in reversed((salida or "").strip().splitlines()):
        try:
            return json.loads(linea)
        except Exception:
            continue
    return {}


class _Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="filex-n1-")
        self.dsal = os.path.join(self.dir, "sal")
        os.makedirs(self.dsal)
        self.salida = os.path.join(self.dsal, "s.webp")
        self.png = os.path.join(self.dir, "a.png")
        self.jpg = os.path.join(self.dir, "b.jpg")
        shutil.copy2(PNG, self.png)
        shutil.copy2(JPG, self.jpg)
        self.vivos: list[subprocess.Popen] = []

    def tearDown(self):
        for p in self.vivos:
            if p.poll() is None:
                _matar(p)
        # El candado del destino no puede sobrevivir a la prueba.
        nucleo._soltar_destino(self.salida)
        shutil.rmtree(self.dir, ignore_errors=True)


# ==========================================================================
# 1. La carrera, entre procesos
# ==========================================================================

class CarreraEntreProcesos(_Base):
    """§2 del informe: dos procesos, dos entradas distintas, un destino."""

    def _carrera(self, modo: str) -> tuple[list[dict], int]:
        go = os.path.join(self.dir, "GO")
        procs = []
        for i, ent in enumerate((self.png, self.jpg)):
            listo = os.path.join(self.dir, f"listo-{i}")
            procs.append((listo, _lanzar(
                "convertidor", modo, dir=self.dir, entrada=ent,
                salida=self.salida, listo=listo, go=go)))
        self.vivos += [p for _, p in procs]
        t0 = time.perf_counter()
        while not all(os.path.exists(l) for l, _ in procs):
            if time.perf_counter() - t0 > TOPE:
                self.fail("los procesos no llegaron a la cita")
            time.sleep(0.01)
        open(go, "w").close()          # pistoletazo
        filas = []
        for _, p in procs:
            out, err = p.communicate(timeout=TOPE)
            fila = _ultima_linea_json(out)
            self.assertTrue(fila, f"el obrero no devolvió JSON: {out!r} {err[-300:]!r}")
            filas.append(fila)
        return filas, len(os.listdir(self.dsal))

    def test_sin_el_cerrojo_de_maquina_los_dos_procesos_devuelven_ok(self):
        """**La prueba que falla sin el arreglo.** Es el estado del hito 7:
        `FILEX_CERROJO_DESTINO=proceso` es exactamente el `set` en memoria.

        No es una prueba de que el fallo «podría» pasar: con el cerrojo de
        proceso, dos procesos distintos **nunca** se ven, así que los dos
        éxitos son deterministas. MEDIDO con tres procesos y las tres entradas
        del hito 7 en `bench/cerrojo-de-maquina.md` §2: tres `ok`, tres tamaños
        declarados distintos y **un fichero en el disco**.
        """
        filas, ficheros = self._carrera("proceso")
        self.assertEqual(sum(1 for f in filas if f["ok"]), 2,
                         "sin cerrojo de máquina los dos tienen que colar")
        self.assertEqual(ficheros, 1)
        declarados = {f["bytes"] for f in filas}
        reales = os.path.getsize(self.salida)
        self.assertIn(reales, declarados)
        # Y aquí está el daño: alguno declara un tamaño que no es el del disco.
        self.assertTrue(any(f["bytes"] != reales for f in filas),
                        "el fallo del hito 7 es que una respuesta describe un "
                        "fichero que ya no existe")

    def test_con_el_cerrojo_de_maquina_solo_uno_gana(self):
        """El mismo caso, con el defecto. **El ganador no es determinista; el
        invariante sí** — tres pasadas en §2 del informe, con dos ganadores
        distintos y siempre un solo éxito."""
        filas, ficheros = self._carrera("maquina")
        exitos = [f for f in filas if f["ok"]]
        self.assertEqual(len(exitos), 1, f"esperaba un solo éxito: {filas}")
        self.assertEqual(ficheros, 1)
        self.assertEqual(exitos[0]["bytes"], os.path.getsize(self.salida),
                         "el éxito declara un tamaño que no es el del fichero")
        for f in filas:
            if not f["ok"]:
                self.assertIn("escribiendo ya esa ruta", f["motivo"])


# ==========================================================================
# 2. El dueño muerto
# ==========================================================================

class DuenoMuerto(_Base):
    """§4: `taskkill /F` no ejecuta ningún `finally`.

    Es el defecto 2 del lock de GPU viejo (`bench/lock-de-maquina.md` §1.2),
    donde un huérfano hacía esperar **900 s** al siguiente. Aquí no hace falta
    ninguna lógica de recuperación: el candado es de RANGO DE BYTES y lo suelta
    el sistema operativo cuando muere el proceso.
    """

    def test_el_candado_se_recupera_solo_al_morir_su_dueno(self):
        p = _lanzar("reservador", "maquina", salida=self.salida)
        self.vivos.append(p)
        self.assertEqual(_ultima_linea_json(p.stdout.readline()),
                         {"reservado": True})
        self.assertFalse(nucleo._reservar_destino(self.salida),
                         "con el dueño VIVO no se puede entrar")
        _matar(p)
        t0 = time.perf_counter()
        self.assertTrue(nucleo._reservar_destino(self.salida),
                        "el candado de un dueño muerto tiene que ser recuperable")
        self.assertLess((time.perf_counter() - t0) * 1000, 100,
                        "la recuperación es inmediata, no una espera")
        nucleo._soltar_destino(self.salida)

    def test_el_fichero_de_candado_no_se_queda_de_basura(self):
        lock = nucleo._fichero_cerrojo(nucleo._clave_destino(self.salida))
        self.assertTrue(nucleo._reservar_destino(self.salida))
        self.assertTrue(os.path.exists(lock))
        nucleo._soltar_destino(self.salida)
        if ES_WINDOWS:
            self.assertFalse(os.path.exists(lock),
                             "en Windows el candado se barre al soltarlo")


# ==========================================================================
# 3. El que no coopera
# ==========================================================================

@unittest.skipUnless(ES_WINDOWS, "os.replace(p,p) solo es un cerrojo en Windows")
class TerceroQueNoCoopera(_Base):
    """§5: la mitad de DETECCIÓN.

    *«Mover el fichero NO habría evitado el caso que lo motivó»* — el ocupante
    de la GPU no iba a tomar el lock estuviera donde estuviera
    (`bench/lock-de-maquina.md` §0.1). Aquí pasa igual: un proceso que no es
    FileX no toma candados. Lo único que se puede hacer con él es verlo y
    negarse.
    """

    def _convertir_con_tercero_delante(self, modo: str) -> tuple[dict, tuple]:
        t = _lanzar("tercero", modo, salida=self.salida)
        self.vivos.append(t)
        self.assertEqual(t.stdout.readline().strip(), "OCUPADO")
        antes = (os.path.getsize(self.salida),
                 open(self.salida, "rb").read(14))
        go = os.path.join(self.dir, "GO")
        open(go, "w").close()
        p = _lanzar("convertidor", modo, dir=self.dir, entrada=self.png,
                    salida=self.salida, listo=os.path.join(self.dir, "l"), go=go)
        self.vivos.append(p)
        out, err = p.communicate(timeout=TOPE)
        fila = _ultima_linea_json(out)
        self.assertTrue(fila, f"{out!r} {err[-300:]!r}")
        return fila, antes

    def test_sin_deteccion_filex_pisa_el_fichero_de_un_tercero(self):
        """El estado del hito 7, y **es el caso peor**: `shutil.move` sobre un
        destino que existe cae a `copy2`, que sobrescribe **en silencio**, y
        FileX devuelve `ok`. MEDIDO: 4 014 B → 13 516 B."""
        fila, antes = self._convertir_con_tercero_delante("proceso")
        self.assertTrue(fila["ok"])
        self.assertNotEqual(os.path.getsize(self.salida), antes[0],
                            "sin detección, el fichero del tercero se pisa")

    def test_con_deteccion_filex_se_niega_y_no_lo_toca(self):
        fila, antes = self._convertir_con_tercero_delante("maquina")
        self.assertFalse(fila["ok"])
        self.assertIn("otro proceso tiene abierta", fila["motivo"])
        self.assertEqual((os.path.getsize(self.salida),
                          open(self.salida, "rb").read(14)), antes,
                         "el fichero del tercero tiene que quedar intacto")


# ==========================================================================
# 4. Que el caso normal siga funcionando
# ==========================================================================

class UnSoloProceso(_Base):
    """§7: un cerrojo que rompe el 99 % de los casos para arreglar el 1 % no es
    un arreglo. Todo esto pasa dentro de UN proceso, que es lo normal."""

    def setUp(self):
        super().setUp()
        self.fx = FileX(raices_lectura=[self.dir])

    def test_tres_conversiones_seguidas_al_mismo_destino(self):
        for i in range(3):
            conv = self.fx.convertir(self.png, self.salida, {})
            self.assertTrue(conv.ok, f"pasada {i}: {conv.motivo}")
        self.assertEqual(len(os.listdir(self.dsal)), 1)

    def test_el_destino_recien_escrito_no_se_detecta_como_ocupado(self):
        """El falso positivo que habría roto todo: FileX acaba de cerrar ese
        fichero. Si `os.replace(p,p)` viera su propio rastro, la segunda
        conversión al mismo sitio fallaría siempre."""
        self.assertTrue(self.fx.convertir(self.png, self.salida, {}).ok)
        self.assertFalse(nucleo.destino_ocupado_por_un_tercero(self.salida))

    def test_el_modo_por_defecto_es_el_seguro(self):
        """Una defensa que hay que encender no es una defensa."""
        entorno = dict(os.environ)
        entorno.pop("FILEX_CERROJO_DESTINO", None)
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, r'%s');"
             "from filex import nucleo; print(nucleo._modo_cerrojo())" % RAIZ],
            capture_output=True, text=True, timeout=60, env=entorno,
            stdin=subprocess.DEVNULL)
        self.assertEqual(r.stdout.strip(), "maquina")

    def test_la_detección_no_dispara_con_un_destino_que_no_existe(self):
        self.assertFalse(nucleo.destino_ocupado_por_un_tercero(
            os.path.join(self.dsal, "no-existe.webp")))


# ==========================================================================
# 5. La misma ruta escrita de dos maneras
# ==========================================================================

@unittest.skipUnless(ES_WINDOWS, "los nombres 8.3 son de Windows")
class AliasDeRuta(_Base):
    """§6.1: un cerrojo que se salta escribiendo la ruta de otra forma no es un
    cerrojo. El hito 7 probaba el cambio de CAJA (`normcase`); el nombre corto
    8.3 pasa por debajo de `normcase` y de `abspath` a la vez."""

    def _corto(self, ruta: str) -> str:
        import ctypes

        buf = ctypes.create_unicode_buffer(1024)
        n = ctypes.windll.kernel32.GetShortPathNameW(ruta, buf, 1024)
        return buf.value if n else ""

    def test_el_nombre_corto_8_3_no_da_un_segundo_dueno(self):
        # El prefijo de `_Base` es corto; hace falta uno que fuerce un 8.3.
        largo_dir = tempfile.mkdtemp(prefix="filex-n1-aliaslargisimo-")
        try:
            corto_dir = self._corto(largo_dir)
            if not corto_dir or corto_dir.lower() == largo_dir.lower():
                self.skipTest("este volumen no genera nombres 8.3")
            largo = os.path.join(largo_dir, "s.webp")
            alias = os.path.join(corto_dir, "s.webp")
            self.assertEqual(nucleo._clave_destino(largo),
                             nucleo._clave_destino(alias))
            self.assertTrue(nucleo._reservar_destino(largo))
            try:
                self.assertFalse(nucleo._reservar_destino(alias),
                                 "el alias 8.3 abre un segundo dueño del mismo "
                                 "fichero")
            finally:
                nucleo._soltar_destino(largo)
                nucleo._soltar_destino(alias)
        finally:
            shutil.rmtree(largo_dir, ignore_errors=True)


def main() -> int:
    if "--papel" in sys.argv:
        i = sys.argv.index("--papel")
        papel = sys.argv[i + 1]
        arg = dict(zip(sys.argv[i + 2::2], sys.argv[i + 3::2]))
        return PAPELES[papel](arg)
    unittest.main(argv=[sys.argv[0]], verbosity=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

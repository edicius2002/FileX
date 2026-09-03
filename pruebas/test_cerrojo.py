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

#: `filex.motores.MOTORES = (ImageMagick, Ghostscript, FFmpeg)` -- solo el
#: primero lee PNG/JPG. Un runner sin el binario `magick` (C42,
#: bench/ci-y-contrato.md §1: MEDIDO dentro de `python:3.12-slim-bookworm`,
#: reproduce "ningún motor disponible lee 'png'" en las 5 celdas exactas que
#: `ci/linux-apto.json` reportaba) no puede convertir NADA en este fichero:
#: no era una carrera rota ni un cerrojo roto, era que no había con qué leer
#: la entrada.
HAY_IMAGEMAGICK = shutil.which("magick") is not None

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
    # N30: `ini`/`fin` delimitan la sección que compite (la llamada a
    # `convertir()` entera, que es donde vive la escritura al destino
    # compartido). `time.perf_counter()` es comparable ENTRE procesos en esta
    # máquina -- en Windows envuelve `QueryPerformanceCounter`, sin origen por
    # proceso (`bench/oraculo-y-gotenberg.md` §1.3 lo sondeó para el mismo
    # propósito) --, así que el padre puede decidir si las dos ventanas se
    # solaparon de verdad sin necesitar un reloj compartido aparte.
    ini = time.perf_counter()
    conv = fx.convertir(arg["--entrada"], arg["--salida"], {}, timeout=TOPE)
    fin = time.perf_counter()
    print(json.dumps({"ok": conv.ok, "motivo": conv.motivo,
                      "bytes": (os.path.getsize(arg["--salida"])
                                if os.path.exists(arg["--salida"]) else None),
                      "ini": ini, "fin": fin},
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


def _papel_ventana_convertidor(arg: dict) -> int:
    """Convierte, pero **abriendo la ventana a propósito** entre la detección
    final y el `move`.

    El gancho no cambia el comportamiento de FileX: llama a la detección de
    verdad y, cuando esta ya ha dicho «libre», suelta al tercero y **espera su
    acuse**. Esa espera es lo que hace la prueba determinista — la ventana real
    dura 681,4 µs y el tercero la acierta 12 de 12 veces, pero una prueba de
    regresión no puede depender de acertar nada.

    Se engancha en la SEGUNDA llamada: `convertir()` detecta dos veces, y la
    primera ocurre antes de que exista ventana ninguna. Enganchar en la primera
    da 12 celdas verdes que no prueban nada (trampa 38).
    """
    fx = FileX(raices_lectura=[arg["--dir"]])
    original = nucleo.destino_ocupado_por_un_tercero
    estado = {"n": 0, "ventana": False}

    def gancho(ruta):
        r = original(ruta)
        estado["n"] += 1
        if estado["n"] >= 2 and not r:
            open(arg["--centinela"], "w").close()
            t0 = time.perf_counter()
            while not os.path.exists(arg["--acuse"]):
                if time.perf_counter() - t0 > 60:
                    return r          # el tercero no llegó: la celda no vale
                time.sleep(0.001)
            estado["ventana"] = True
        return r

    nucleo.destino_ocupado_por_un_tercero = gancho
    try:
        conv = fx.convertir(arg["--entrada"], arg["--salida"], {}, timeout=TOPE)
    finally:
        nucleo.destino_ocupado_por_un_tercero = original
    print(json.dumps({"ok": conv.ok, "motivo": conv.motivo,
                      "la_ventana_se_abrio": estado["ventana"],
                      "bytes": (os.path.getsize(arg["--salida"])
                                if os.path.exists(arg["--salida"]) else None)},
                     ensure_ascii=False), flush=True)
    return 0


def _papel_ventana_tercero(arg: dict) -> int:
    """Espera al centinela y **entonces** abre el destino, dentro de la ventana."""
    print("LISTO", flush=True)
    t0 = time.perf_counter()
    while not os.path.exists(arg["--centinela"]):
        if time.perf_counter() - t0 > TOPE:
            return 2
    f = open(arg["--salida"], "r+b")
    print("ABIERTO", flush=True)
    open(arg["--acuse"], "w").close()
    time.sleep(TOPE)
    f.close()
    return 0


PAPELES = {"convertidor": _papel_convertidor, "reservador": _papel_reservador,
           "tercero": _papel_tercero,
           "ventana_convertidor": _papel_ventana_convertidor,
           "ventana_tercero": _papel_ventana_tercero}


# --------------------------------------------------------------------------
# Utilidades del lado del padre
# --------------------------------------------------------------------------

def _lanzar(papel: str, modo: str = "maquina", move: str = "1",
            **kw) -> subprocess.Popen:
    argv = [sys.executable, os.path.abspath(__file__), "--papel", papel]
    for k, v in kw.items():
        argv += ["--" + k, str(v)]
    return subprocess.Popen(
        argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
        cwd=RAIZ, env=dict(os.environ, FILEX_CERROJO_DESTINO=modo,
                           FILEX_MOVE_SEGURO=move,
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

    @unittest.skipUnless(HAY_IMAGEMAGICK,
                        "no hay ImageMagick (`magick`): ningún motor lee png/jpg")
    def test_sin_el_cerrojo_de_maquina_los_dos_procesos_devuelven_ok(self):
        """**La prueba que falla sin el arreglo.** Es el estado del hito 7:
        `FILEX_CERROJO_DESTINO=proceso` es exactamente el `set` en memoria.

        No es una prueba de que el fallo «podría» pasar: con el cerrojo de
        proceso, dos procesos distintos **nunca** se ven, así que los dos
        éxitos son deterministas. MEDIDO con tres procesos y las tres entradas
        del hito 7 en `bench/cerrojo-de-maquina.md` §2: tres `ok`, tres tamaños
        declarados distintos y **un fichero en el disco**.

        N30: bajo carga, la sincronización por `GO` garantiza que los dos
        procesos SALEN a la vez, pero no que sus `convertir()` lleguen a
        SOLAPARSE dentro de la sección que compite — uno puede terminar
        entero antes de que al otro le toque CPU. Eso no es "el fallo no se
        dio": es "no se puede afirmar que se dio", y una prueba que falla en
        ese caso está midiendo el planificador, no el cerrojo (trampa 38:
        *registra si la condición que dices reproducir se dio*). Se comprueba
        con los `ini`/`fin` que cada proceso publica, y si no hubo solape se
        salta — no se relaja el `assertTrue` de más abajo, que sigue
        pudiendo fallar cuando SÍ hay solape.
        """
        filas, ficheros = self._carrera("proceso")
        if len(filas) == 2 and not (filas[0]["ini"] < filas[1]["fin"] and
                                    filas[1]["ini"] < filas[0]["fin"]):
            self.skipTest(
                "la ventana de carrera no se abrió bajo esta carga: los dos "
                "convertir() no se solaparon (proc0 %.1f-%.1f ms, proc1 "
                "%.1f-%.1f ms desde el GO) — no hay nada que esta prueba "
                "pueda afirmar sobre el fallo del hito 7 en esta pasada"
                % (filas[0]["ini"] * 1000, filas[0]["fin"] * 1000,
                   filas[1]["ini"] * 1000, filas[1]["fin"] * 1000))
        self.assertEqual(sum(1 for f in filas if f["ok"]), 2,
                         "sin cerrojo de máquina los dos tienen que colar")
        self.assertEqual(ficheros, 1)
        declarados = {f["bytes"] for f in filas}
        reales = os.path.getsize(self.salida)
        self.assertIn(reales, declarados)
        # Y aquí está el daño: alguno declara un tamaño que no es el del disco.
        self.assertTrue(any(f["bytes"] != reales for f in filas),
                        "el fallo del hito 7 es que una respuesta describe un "
                        "fichero que ya no existe -- reales=%s filas=%s"
                        % (reales, filas))

    @unittest.skipUnless(HAY_IMAGEMAGICK,
                        "no hay ImageMagick (`magick`): ningún motor lee png/jpg")
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
        """N30: `_matar` (`taskkill /F`) devuelve el control en cuanto Windows
        acepta la orden, no en cuanto el candado de rango de bytes queda
        efectivamente liberado — bajo carga esas dos cosas se separan. La
        prueba original comprobaba una sola vez justo después de matar, así
        que medía el planificador, no la recuperación. Aquí se reintenta con
        tope (trampa 65: el arreglo no es relajar el `assertTrue`, sigue
        exigiendo que se recupere). Lo que SÍ sigue siendo "inmediato" —y se
        sigue comprobando— es cada intento individual: `_reservar_destino`
        no lleva ninguna espera propia, es el sistema operativo el que tarda
        en soltar, no la función.
        """
        p = _lanzar("reservador", "maquina", salida=self.salida)
        self.vivos.append(p)
        self.assertEqual(_ultima_linea_json(p.stdout.readline()),
                         {"reservado": True})
        self.assertFalse(nucleo._reservar_destino(self.salida),
                         "con el dueño VIVO no se puede entrar")
        _matar(p)
        tope, paso = 2.0, 0.03
        t0 = time.perf_counter()
        recuperado = False
        while time.perf_counter() - t0 < tope:
            ini = time.perf_counter()
            recuperado = nucleo._reservar_destino(self.salida)
            ms_intento = (time.perf_counter() - ini) * 1000
            self.assertLess(ms_intento, 100,
                            "cada intento tiene que ser inmediato: "
                            "_reservar_destino no lleva lógica de espera propia")
            if recuperado:
                break
            time.sleep(paso)
        self.assertTrue(recuperado,
                        "el candado de un dueño muerto tiene que ser recuperable "
                        "(tope de %.1f s agotado)" % tope)
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

    def _convertir_con_tercero_delante(self, modo: str,
                                       move: str = "1") -> tuple[dict, tuple]:
        t = _lanzar("tercero", modo, salida=self.salida)
        self.vivos.append(t)
        self.assertEqual(t.stdout.readline().strip(), "OCUPADO")
        antes = (os.path.getsize(self.salida),
                 open(self.salida, "rb").read(14))
        go = os.path.join(self.dir, "GO")
        open(go, "w").close()
        p = _lanzar("convertidor", modo, move=move, dir=self.dir,
                    entrada=self.png, salida=self.salida,
                    listo=os.path.join(self.dir, "l"), go=go)
        self.vivos.append(p)
        out, err = p.communicate(timeout=TOPE)
        fila = _ultima_linea_json(out)
        self.assertTrue(fila, f"{out!r} {err[-300:]!r}")
        return fila, antes

    def test_sin_deteccion_filex_pisa_el_fichero_de_un_tercero(self):
        """El estado del hito 7, y **es el caso peor**: `shutil.move` sobre un
        destino que existe cae a `copy2`, que sobrescribe **en silencio**, y
        FileX devuelve `ok`. MEDIDO: 4 014 B → 13 516 B.

        **Desde N12 hacen falta las DOS variables para reproducirlo**
        (`FILEX_MOVE_SEGURO=0` además de `FILEX_CERROJO_DESTINO=proceso`), y
        eso no es un remiendo de la prueba: es el hallazgo. Con solo la
        primera, esta prueba pasó a rojo porque `os.replace` **ya se niega
        aunque la detección esté apagada** — ver
        `test_aun_sin_deteccion_el_move_seguro_protege_al_tercero`.
        """
        fila, antes = self._convertir_con_tercero_delante("proceso", move="0")
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

    def test_aun_sin_deteccion_el_move_seguro_protege_al_tercero(self):
        """N12: las dos mitades ya no son independientes, y esto lo mide.

        Con la detección **apagada** (`proceso`) y el `move` seguro puesto,
        FileX se niega igual: el `os.replace` final falla con `WinError 5`. La
        detección previa deja de ser la única defensa y pasa a ser un atajo
        —evita convertir 250 ms y, cruzando volúmenes, una copia entera—.
        """
        fila, antes = self._convertir_con_tercero_delante("proceso", move="1")
        self.assertFalse(fila["ok"], "el `os.replace` tenía que negarse")
        self.assertEqual((os.path.getsize(self.salida),
                          open(self.salida, "rb").read(14)), antes)


# ==========================================================================
# 3 bis. N12 — la VENTANA entre la detección y el `move`
# ==========================================================================

@unittest.skipUnless(ES_WINDOWS, "la detección solo existe en Windows")
class VentanaAntesDelMove(_Base):
    """`bench/ventana-antes-del-move.md`: la detección es un INSTANTE.

    `TerceroQueNoCoopera` prueba al ocupante que **ya estaba** cuando FileX
    miró. Aquí el tercero llega **después de mirar y antes de mover**, que es
    justo el hueco que `bench/cerrojo-de-maquina.md` §6.3 dejó PENDIENTE.

    Las dos pruebas son la misma escena con `FILEX_MOVE_SEGURO` a 0 y a 1, y
    **cada una comprueba `la_ventana_se_abrio` antes de mirar el resultado**:
    sin eso, la de abajo pasaría igual si el tercero no hubiera llegado nunca
    (trampa 38).
    """

    def _escena(self, move: str) -> tuple[dict, bytes]:
        # El destino existe y NADIE lo tiene abierto: la detección de FileX va
        # a decir «libre», y va a tener razón.
        with open(self.salida, "wb") as f:
            f.write(b"T" * 4014)
        centinela = os.path.join(self.dir, "CENTINELA")
        acuse = os.path.join(self.dir, "ACUSE")
        t = _lanzar("ventana_tercero", salida=self.salida,
                    centinela=centinela, acuse=acuse)
        self.vivos.append(t)
        self.assertEqual(t.stdout.readline().strip(), "LISTO")
        p = _lanzar("ventana_convertidor", move=move, dir=self.dir,
                    entrada=self.png, salida=self.salida,
                    centinela=centinela, acuse=acuse)
        self.vivos.append(p)
        out, err = p.communicate(timeout=TOPE)
        fila = _ultima_linea_json(out)
        self.assertTrue(fila, f"{out!r} {err[-300:]!r}")
        self.assertTrue(fila["la_ventana_se_abrio"],
                        "el tercero no llegó a colarse: la celda no prueba nada")
        with open(self.salida, "rb") as f:
            return fila, f.read(4)

    def test_con_shutil_move_el_tercero_de_la_ventana_es_atropellado(self):
        """El estado anterior a N12. **12 de 12 celdas** del arnés acabaron
        así: FileX dice `ok` y el fichero del tercero deja de existir, porque
        `shutil.move` sobre un destino existente cae a `copy2`."""
        fila, cabecera = self._escena("0")
        self.assertTrue(fila["ok"], fila["motivo"])
        self.assertNotEqual(cabecera, b"TTTT",
                            "con shutil.move el fichero del tercero se pisa")

    def test_con_os_replace_filex_se_niega_y_no_lo_toca(self):
        """`os.replace` funde la detección y la acción en una sola llamada del
        sistema, así que no queda ventana entre medias."""
        fila, cabecera = self._escena("1")
        self.assertFalse(fila["ok"])
        self.assertIn("otro proceso tiene abierta", fila["motivo"])
        self.assertEqual(cabecera, b"TTTT",
                         "el fichero del tercero tiene que quedar intacto")
        self.assertEqual(os.path.getsize(self.salida), 4014)

    def test_el_move_seguro_es_el_defecto(self):
        """Una defensa que hay que encender no es una defensa."""
        entorno = dict(os.environ)
        entorno.pop("FILEX_MOVE_SEGURO", None)
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, r'%s');"
             "from filex import nucleo; print(nucleo._move_seguro())" % RAIZ],
            capture_output=True, text=True, timeout=60, env=entorno,
            stdin=subprocess.DEVNULL)
        self.assertEqual(r.stdout.strip(), "True")

    def test_cruzar_volumen_no_se_confunde_con_ocupado(self):
        """Trampa 43 en su versión de N12: «no se puede» y «está en otro disco»
        llegan los dos como `OSError`, y solo el `errno` los separa —
        `EACCES` (13) frente a `EXDEV` (18), MEDIDO."""
        otro = os.environ.get("FILEX_VENTANA_OTRO_VOLUMEN") or os.path.join(
            RAIZ, "bench", "salidas-ventana")
        if (os.path.splitdrive(os.path.abspath(otro))[0].lower()
                == os.path.splitdrive(os.path.abspath(self.dir))[0].lower()):
            self.skipTest("no hay dos volúmenes distintos a mano")
        origen = os.path.join(self.dir, "cruza.bin")
        with open(origen, "wb") as f:
            f.write(b"X" * 1234)
        destino = os.path.join(otro, "filex-prueba-cruza.bin")
        try:
            nucleo.mover_a_destino(origen, destino)
            self.assertEqual(os.path.getsize(destino), 1234)
            self.assertFalse(os.path.exists(origen))
            # Y no deja el temporal de la copia por ahí.
            self.assertFalse([n for n in os.listdir(otro)
                              if n.startswith(".filex-") and n.endswith(".parcial")])
        finally:
            try:
                os.remove(destino)
            except OSError:
                pass


# ==========================================================================
# 4. Que el caso normal siga funcionando
# ==========================================================================

class UnSoloProceso(_Base):
    """§7: un cerrojo que rompe el 99 % de los casos para arreglar el 1 % no es
    un arreglo. Todo esto pasa dentro de UN proceso, que es lo normal."""

    def setUp(self):
        super().setUp()
        self.fx = FileX(raices_lectura=[self.dir])

    @unittest.skipUnless(HAY_IMAGEMAGICK,
                        "no hay ImageMagick (`magick`): ningún motor lee png/jpg")
    def test_tres_conversiones_seguidas_al_mismo_destino(self):
        for i in range(3):
            conv = self.fx.convertir(self.png, self.salida, {})
            self.assertTrue(conv.ok, f"pasada {i}: {conv.motivo}")
        self.assertEqual(len(os.listdir(self.dsal)), 1)

    @unittest.skipUnless(HAY_IMAGEMAGICK,
                        "no hay ImageMagick (`magick`): ningún motor lee png/jpg")
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


# ==========================================================================
# 6. N20 — un destino que es un DIRECTORIO
# ==========================================================================

class DestinoQueEsDirectorio(_Base):
    """`bench/fidelidad-y-nucleo.md` §3: FileX **se negaba, y mentía al decir
    por qué**.

    El punto 5 de «lo que no cubre» de N12 lo dejó anotado: `os.replace` se
    niega ante un destino que es un directorio, y **negarse es lo correcto**;
    lo que estaba mal era el motivo, porque el `errno` es el MISMO que el del
    ocupante de verdad (`EACCES`/`WinError 5`, MEDIDO) y los dos caían en
    `DestinoOcupado`. Es la trampa 44: un campo honesto —«fallo»— al lado de
    una frase falsa —«otro proceso tiene abierta esa ruta»—.
    """

    def setUp(self):
        super().setUp()
        self.fx = FileX(raices_lectura=[self.dir])
        # El destino existe y es un DIRECTORIO. Nadie lo tiene abierto.
        os.makedirs(self.salida)

    @unittest.skipUnless(HAY_IMAGEMAGICK,
                        "no hay ImageMagick (`magick`): ningún motor lee png/jpg")
    def test_el_motivo_no_habla_de_otro_proceso(self):
        """**La prueba que se pone roja sin el arreglo**: antes decía
        literalmente «otro proceso tiene abierta esa ruta de salida», y no
        había ningún otro proceso."""
        conv = self.fx.convertir(self.png, self.salida, {})
        self.assertFalse(conv.ok)
        self.assertEqual(conv.motivo, nucleo.MOTIVO_NO_ES_FICHERO)
        self.assertNotIn("otro proceso", conv.motivo)

    def test_se_rechaza_antes_de_convertir(self):
        """Y por el mismo motivo que la detección temprana del ocupante: si va
        a acabar en `fallo`, no hay que gastar los ~250 ms del motor. Se ve en
        que no hay ni un salto."""
        conv = self.fx.convertir(self.png, self.salida, {})
        self.assertFalse(conv.ok)
        self.assertEqual(conv.saltos, [])

    def test_no_mete_la_salida_dentro_del_directorio(self):
        """`shutil.move` metía el fichero DENTRO. Nadie pidió esa ruta."""
        self.fx.convertir(self.png, self.salida, {})
        self.assertEqual(os.listdir(self.salida), [])

    def test_la_deteccion_de_ocupante_no_ve_el_directorio(self):
        """Por qué hace falta una comprobación aparte y no vale la de N12:
        `os.replace(DIR, DIR)` **funciona**, así que la detección devuelve
        `False` — y tiene razón, nadie lo tiene abierto (MEDIDO, caso A2 de
        `bench/salidas-fidelidad-n/sonda_destino_dir.json`)."""
        self.assertFalse(nucleo.destino_ocupado_por_un_tercero(self.salida))

    def test_mover_a_destino_distingue_las_dos_negativas(self):
        """Las dos excepciones son distintas **y las dos siguen siendo
        `OSError`**: quien solo quiera saber que no se pudo, no se entera."""
        origen = os.path.join(self.dir, "x.bin")
        with open(origen, "wb") as f:
            f.write(b"X" * 16)
        with self.assertRaises(nucleo.DestinoNoEsFichero):
            nucleo.mover_a_destino(origen, self.salida)
        self.assertTrue(os.path.exists(origen), "no se ha movido nada")
        self.assertFalse(issubclass(nucleo.DestinoNoEsFichero,
                                    nucleo.DestinoOcupado),
                         "un `except DestinoOcupado` no puede tragarse el otro")
        self.assertTrue(issubclass(nucleo.DestinoNoEsFichero, OSError))


# ==========================================================================
# 7. N19 — `DirectorioDeTrabajo.recoger`, el mismo agujero un nivel más abajo
# ==========================================================================

class RecogerNoPisa(_Base):
    """`bench/fidelidad-y-nucleo.md` §4.

    `recoger()` es **pública** y la usan arneses de `bench/`. Hacía
    `shutil.move`, que sobre un destino existente cae a `copy2` y pisa en
    silencio (trampa 33) — y pisaba **incluso el fichero que otro proceso tenía
    abierto**, que es más de lo que decía el pendiente que la señaló.
    """

    def _recoger(self, destino):
        from filex.trabajo import DirectorioDeTrabajo

        t = DirectorioDeTrabajo()
        try:
            with open(t.destino("s.bin"), "wb") as f:
                f.write(b"NUEVO" * 4)
            return t.recoger("s.bin", destino)
        finally:
            t.cerrar()

    @unittest.skipUnless(ES_WINDOWS, "la detección solo existe en Windows")
    def test_no_pisa_el_fichero_de_un_tercero(self):
        """**La prueba que se pone roja sin el arreglo.** Con `shutil.move` la
        víctima pasaba de 88 B a 20 B y no saltaba ninguna excepción."""
        t = _lanzar("tercero", "maquina", salida=self.salida)
        self.vivos.append(t)
        self.assertEqual(t.stdout.readline().strip(), "OCUPADO")
        antes = os.path.getsize(self.salida)
        with self.assertRaises(nucleo.DestinoOcupado):
            self._recoger(self.salida)
        self.assertEqual(os.path.getsize(self.salida), antes,
                         "recoger() pisó el fichero de un tercero")

    def test_a_un_directorio_no_mete_dentro(self):
        """La otra mitad de N20, a este nivel: `shutil.move` metía la salida
        dentro del directorio; `mover_a_destino` se niega y lo dice bien."""
        os.makedirs(self.salida)
        with self.assertRaises(nucleo.DestinoNoEsFichero):
            self._recoger(self.salida)
        self.assertEqual(os.listdir(self.salida), [])

    def test_el_caso_normal_sigue_funcionando(self):
        """Un arreglo que rompe el 99 % para cubrir el 1 % no es un arreglo:
        el destino que NO existe se recoge igual que siempre."""
        destino = os.path.join(self.dsal, "recogido.bin")
        self.assertEqual(self._recoger(destino), destino)
        self.assertEqual(os.path.getsize(destino), 20)


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

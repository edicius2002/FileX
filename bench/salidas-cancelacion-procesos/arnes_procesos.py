"""Arnés de N10: cuánto tarda una cancelación ENTRE PROCESOS, antes y después.

`bench/cancelacion-y-servicio.md` §4.1 dejó el alcance escrito: la cancelación
de C34 es **de proceso**, y cancelar un trabajo leído del disco desde otro
`filex` devuelve `motor_detenido: false`. Aquí se mide qué pasaba de verdad y
qué pasa ahora, con **procesos de verdad** (`pruebas/hijo_de_trabajo.py`): dos
`Servicio` en el mismo intérprete comparten el registro de `filex.invocacion` y
darían verde sin canal ninguno — la trampa 38.

El antes y el después salen de la MISMA TANDA con `FILEX_MANDO=0/1`, que es la
única comparación honesta en esta máquina (`CLAUDE.md` §3, y el mismo patrón que
el `FILEX_CERROJO_MUTEX` de P).

Las cuatro medidas:

M1  **La cancelación entre procesos.** Un hijo convierte `tipico.mp4 → webm`
    (~21 s MEDIDOS por N-a) y este proceso le pide `job(..., "cancelar")` con el
    motor ya en vuelo. Se mide desde la llamada hasta que el hijo dice `fin`, y
    con qué estado termina.
      * `sin_canal`  — lo que había: la orden no llega y la conversión se hace.
      * `con_canal`  — el mando en el disco y el vigilante del dueño.
M2  **La DETECCIÓN.** Al hijo se le hace `taskkill /F /T` con el motor en vuelo.
    ¿Qué contesta `job(job_id)` después?
      * `sin_deteccion` — `working`, y se queda así.
      * `con_deteccion` — se descubre que el dueño no vive y se cierra.
M3  **El coste en el camino normal**, TROZO A TROZO y no por diferencia de
    totales (trampa 36: dentro de una tanda hay un suelo de ±70 µs).
M4  **El coste de la detección misma**: `cerrojo.esta_libre` con el candado
    libre y con el candado tomado, que son las dos respuestas posibles.

Uso:

    python bench/salidas-cancelacion-procesos/arnes_procesos.py [--n 9]

Escribe `n10_medidas.json`. No usa la GPU. No lanza contenedores.

Dos testigos de ruido, como manda `CLAUDE.md` §3: uno de deriva (bucle
monohilo) y otro de nivel (lanzamiento de proceso), este con tope propio.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import cerrojo                                       # noqa: E402
from filex import servicio as S                                 # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "n10_medidas.json")
VIDEO = os.path.join(RAIZ, "corpus", "video", "tipico.mp4")
HIJO = os.path.join(RAIZ, "pruebas", "hijo_de_trabajo.py")

#: Tope del propio testigo de nivel. Un testigo que puede tumbar la medición no
#: es un testigo (`CLAUDE.md` §3, caso P3).
TOPE_TESTIGO = 20.0

#: Cuánto se le da al hijo para arrancar y poner el motor en vuelo.
TOPE_ARRANQUE = 120.0

#: Cuánto se espera al `fin` del hijo. La conversión sin cancelar tarda ~21 s.
TOPE_FIN = 180.0

#: Cuánto se mira si un trabajo huérfano cambia solo de estado. No cambia: es
#: lo que se quiere publicar con un número al lado en vez de con un «nunca».
ESPERA_HUERFANO = 5.0


# ------------------------------------------------------------------ testigos


def testigo_deriva(n: int = 200_000) -> float:
    t0 = time.perf_counter()
    x = 0
    for i in range(n):
        x += i * i
    return (time.perf_counter() - t0) * 1000


def testigo_nivel() -> float:
    t0 = time.perf_counter()
    try:
        subprocess.run(["ffprobe", "-version"], stdin=subprocess.DEVNULL,
                       capture_output=True, timeout=TOPE_TESTIGO, check=False)
    except Exception:
        return TOPE_TESTIGO * 1000
    return (time.perf_counter() - t0) * 1000


def _mediana(v) -> float:
    return round(statistics.median(v), 3) if v else float("nan")


# -------------------------------------------------------------------- hijo


class Hijo:
    """Un `filex` de verdad convirtiendo un vídeo. Se limpia siempre."""

    def __init__(self, raiz: str, i: int, con_canal: bool):
        self.dir = os.path.join(raiz, f"h{i}")
        self.trabajos = os.path.join(self.dir, "trabajos")
        os.makedirs(self.trabajos, exist_ok=True)
        argv = [sys.executable, HIJO, "--trabajos", self.trabajos,
                "--entrada", VIDEO, "--salida", os.path.join(self.dir, "s.webm"),
                "--tope", str(TOPE_FIN)]
        if not con_canal:
            argv.append("--no-mando")
        entorno = dict(os.environ)
        entorno["FILEX_MANDO"] = "1" if con_canal else "0"
        self.proc = subprocess.Popen(
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
            errors="replace", cwd=RAIZ, env=entorno)
        self.jid = self.evento("arrancado")["job_id"]
        self.evento("en_vuelo")

    def evento(self, cual: str, tope: float = TOPE_ARRANQUE) -> dict:
        limite = time.perf_counter() + tope
        while time.perf_counter() < limite:
            linea = self.proc.stdout.readline()
            if not linea:
                break
            try:
                d = json.loads(linea)
            except ValueError:
                continue
            if d.get("evento") == cual:
                return d
        return {"evento": "TOPE", "estado": "?"}

    def matar(self) -> None:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.proc.pid)],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=30, check=False)
        else:
            self.proc.kill()
        try:
            self.proc.wait(timeout=30)
        except Exception:
            pass

    def cerrar(self) -> None:
        self.matar()
        try:
            self.proc.stdout.close()
        except Exception:
            pass
        shutil.rmtree(self.dir, ignore_errors=True)


class _FxFalso:
    """Este proceso no convierte nada: solo cancela y pregunta."""

    confinamiento = None


# ---------------------------------------------------------------------- M1


def m1(n: int, raiz: str) -> dict:
    out = {"sin_canal": {"ms": [], "estados": [], "motor_detenido": []},
           "con_canal": {"ms": [], "estados": [], "motor_detenido": []}}
    for via, con in (("sin_canal", False), ("con_canal", True)):
        for i in range(n):
            h = Hijo(raiz, f"{via}{i}", con)
            try:
                os.environ["FILEX_MANDO"] = "1" if con else "0"
                sv = S.Servicio(_FxFalso(), S.Trabajos(h.trabajos))
                t0 = time.perf_counter()
                r = sv.job(h.jid, "cancelar")
                fin = h.evento("fin", tope=TOPE_FIN)
                out[via]["ms"].append(round((time.perf_counter() - t0) * 1000, 1))
                out[via]["estados"].append(fin.get("estado", "?"))
                out[via]["motor_detenido"].append(bool(r.get("motor_detenido")))
            finally:
                os.environ.pop("FILEX_MANDO", None)
                h.cerrar()
        out[via]["mediana_ms"] = _mediana(out[via]["ms"])
    out["ganancia"] = round(out["sin_canal"]["mediana_ms"] /
                            max(out["con_canal"]["mediana_ms"], 1e-9), 1)
    return out


# ---------------------------------------------------------------------- M2


def m2(n: int, raiz: str) -> dict:
    """El dueño MUERTO. Es la mitad que un canal cooperativo no cubre."""
    out = {"sin_deteccion": {"estados": [], "ms": [], "sigue_working": []},
           "con_deteccion": {"estados": [], "ms": [], "motivos": []}}
    for via, con in (("sin_deteccion", False), ("con_deteccion", True)):
        for i in range(n):
            h = Hijo(raiz, f"{via}{i}", con)
            try:
                h.matar()
                os.environ["FILEX_MANDO"] = "1" if con else "0"
                sv = S.Servicio(_FxFalso(), S.Trabajos(h.trabajos))
                t0 = time.perf_counter()
                r = sv.job(h.jid)
                out[via]["ms"].append(round((time.perf_counter() - t0) * 1000, 3))
                out[via]["estados"].append(r.get("estado", "?"))
                if con:
                    fin = sv.job(h.jid, "resultado")
                    out[via]["motivos"].append(fin.get("motivo", "?"))
                else:
                    # ¿Cambia solo si se le da tiempo? No. Se publica el número
                    # en vez de un «nunca» sin medir.
                    time.sleep(ESPERA_HUERFANO)
                    out[via]["sigue_working"].append(
                        sv.job(h.jid).get("estado") == S.TRABAJANDO)
            finally:
                os.environ.pop("FILEX_MANDO", None)
                h.cerrar()
        out[via]["mediana_ms"] = _mediana(out[via]["ms"])
    return out


# ---------------------------------------------------------------------- M3


def m3(n: int, raiz: str) -> dict:
    """El coste en el camino normal, TROZO A TROZO (trampa 36)."""
    d = os.path.join(raiz, "m3")
    os.makedirs(d, exist_ok=True)
    trabajos = S.Trabajos(d)
    t = trabajos.nuevo("convert")

    # a) tomar y soltar el candado del trabajo: lo que `_arrancar` añade.
    tc = []
    for _ in range(n):
        t0 = time.perf_counter()
        c = S._tomar_candado(t)
        ms_tomar = (time.perf_counter() - t0) * 1000
        t1 = time.perf_counter()
        if c is not None:
            c.soltar()
        tc.append((ms_tomar, (time.perf_counter() - t1) * 1000))

    # b) un tick del vigilante: el `scandir` del directorio de trabajos.
    tick = []
    for _ in range(n):
        t0 = time.perf_counter()
        try:
            with os.scandir(d) as it:
                _ = [e.name for e in it if e.name.endswith(S.SUFIJO_MANDO)]
        except OSError:
            pass
        tick.append((time.perf_counter() - t0) * 1000)

    # c) escribir y borrar el mando: solo se paga al cancelar.
    esc, bor = [], []
    for _ in range(n):
        t0 = time.perf_counter()
        S.pedir_mando(d, t.id)
        esc.append((time.perf_counter() - t0) * 1000)
        t0 = time.perf_counter()
        S._borrar_mando(d, t.id)
        bor.append((time.perf_counter() - t0) * 1000)

    return {"candado_tomar_us": round(_mediana([a for a, _ in tc]) * 1000, 1),
            "candado_soltar_us": round(_mediana([b for _, b in tc]) * 1000, 1),
            "tick_vigilante_us": round(_mediana(tick) * 1000, 1),
            "intervalo_vigilante_s": S.INTERVALO_MANDO,
            "escribir_mando_us": round(_mediana(esc) * 1000, 1),
            "borrar_mando_us": round(_mediana(bor) * 1000, 1),
            "n": n}


# ---------------------------------------------------------------------- M4


def m4(n: int) -> dict:
    """El coste de PREGUNTAR si el dueño vive, en sus dos respuestas."""
    libre, ocupado = [], []
    clave = "filex-arnes-n10-m4"
    for _ in range(n):
        t0 = time.perf_counter()
        r = cerrojo.esta_libre(clave)
        libre.append(((time.perf_counter() - t0) * 1000, r))
    c = cerrojo.Candado(clave)
    c.tomar()
    try:
        for _ in range(n):
            t0 = time.perf_counter()
            r = cerrojo.esta_libre(clave)
            ocupado.append(((time.perf_counter() - t0) * 1000, r))
    finally:
        c.soltar()
    return {"libre_us": round(_mediana([a for a, _ in libre]) * 1000, 1),
            "libre_respuesta": sorted({b for _, b in libre}),
            "ocupado_us": round(_mediana([a for a, _ in ocupado]) * 1000, 1),
            "ocupado_respuesta": sorted({b for _, b in ocupado}),
            "n": n}


# ---------------------------------------------------------------------- main


def censo(d: str) -> dict:
    try:
        with os.scandir(d) as it:
            return {e.name: (e.stat().st_size if e.is_file() else -1) for e in it}
    except OSError:
        return {}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=9)
    p.add_argument("--micro", type=int, default=200)
    a = p.parse_args()

    raiz_tmp = tempfile.mkdtemp(prefix="n10-arnes-")
    antes_raiz = censo(RAIZ)                       # R21: listar antes y después
    d = {"n": a.n, "pid": os.getpid(),
         "testigos": {"deriva_antes_ms": round(testigo_deriva(), 2),
                      "nivel_antes_ms": round(testigo_nivel(), 2)}}
    try:
        d["M3_coste_camino_normal"] = m3(a.micro, raiz_tmp)
        d["M4_coste_deteccion"] = m4(a.micro)
        d["M1_cancelar_entre_procesos"] = m1(a.n, raiz_tmp)
        d["M2_dueno_muerto"] = m2(a.n, raiz_tmp)
    finally:
        shutil.rmtree(raiz_tmp, ignore_errors=True)
    d["testigos"]["deriva_despues_ms"] = round(testigo_deriva(), 2)
    d["testigos"]["nivel_despues_ms"] = round(testigo_nivel(), 2)
    dv = d["testigos"]["deriva_despues_ms"] / max(d["testigos"]["deriva_antes_ms"], 1e-9)
    d["testigos"]["deriva"] = round(dv, 3)
    # Con la sesión remota activa TODO sale `SUCIA`: es estructural (`CLAUDE.md`
    # §3). Se etiqueta igualmente para que se vea si además hubo deriva.
    d["etiqueta"] = "SUCIA"
    d["testigos"]["hay_deriva"] = not (0.7 <= dv <= 1.4)
    d["R21_ficheros_nuevos_en_la_raiz"] = sorted(
        set(censo(RAIZ)) - set(antes_raiz))

    with open(SALIDA, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in d.items()
                      if k != "M1_cancelar_entre_procesos"},
                     ensure_ascii=False, indent=2))
    print(json.dumps({"M1": {k: {kk: vv for kk, vv in v.items() if kk != "ms"}
                             if isinstance(v, dict) else v
                             for k, v in d["M1_cancelar_entre_procesos"].items()}},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

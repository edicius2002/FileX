"""Sonda del escenario N36, aislado del módulo de pruebas.

Reproduce **exactamente** lo que hace
`CancelarEntreProcesos::test_cancelar_alcanza_al_motor_de_otro_proceso`
—lanzar un `filex` de verdad, esperar a que su motor esté en vuelo y cancelarlo
desde otro proceso— pero **registrando la traza del sujeto** en vez de sólo el
veredicto (trampa 38: *registra si la condición que dices reproducir se dio*).

Por iteración se anota:

* `aviso_cerrojo` — lo que el hijo dijo al arrancar. Si el candado del trabajo
  no se pudo tomar, el trabajo corre **con pinta de huérfano** y quien cancele
  lo recogerá como muerto en vez de cancelarlo. El arnés de N36 lo recibe y
  **lo tira**.
* `libre_antes` — `cerrojo.esta_libre(clave_de(jid))` justo antes de cancelar.
  Es el predicado exacto que decide `_es_huerfano`, interrogado al sujeto.
* el diccionario íntegro que devuelve `job(..., "cancelar")`, con su `ms`.
* `ffmpeg_antes` / `ffmpeg_despues` — residuos (trampas 112 y 47).

`--carga N` levanta N procesos de CPU **declarados** durante la iteración, para
preguntar si la cancelación depende de la velocidad de la máquina. Es una
variable independiente puesta a propósito, no ruido heredado.

Uso::

    python bench/salidas-cancelacion-inestable/sonda_n36.py --n 8 --carga 0
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, RAIZ)

from filex import cerrojo                                       # noqa: E402
from filex import servicio as S                                 # noqa: E402

VIDEO = os.path.join(RAIZ, "corpus", "video", "tipico.mp4")
HIJO = os.path.join(RAIZ, "pruebas", "hijo_de_trabajo.py")

TOPE_ARRANQUE = 90.0
TOPE_CANCELACION = 30.0

#: Bucle de CPU para la carga declarada. Sin fin: se mata al cerrar.
_CARGA = "x=0\nwhile True:\n    x=(x*x+1)%1000003\n"


class _FxFalso:
    confinamiento = None


def _lee_evento(proc, esperado: str, tope: float = TOPE_ARRANQUE) -> dict:
    limite = time.perf_counter() + tope
    while time.perf_counter() < limite:
        linea = proc.stdout.readline()
        if not linea:
            break
        try:
            d = json.loads(linea)
        except ValueError:
            continue
        if d.get("evento") == esperado:
            return d
        if d.get("evento") == "error":
            return {"evento": "error", "detalle": d}
    return {"evento": "_sin_" + esperado}


def ffmpeg_vivos() -> int:
    if sys.platform != "win32":
        return -1
    try:
        p = subprocess.run(["tasklist", "/FI", "IMAGENAME eq ffmpeg.exe", "/NH"],
                           stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, errors="replace", timeout=20)
    except subprocess.TimeoutExpired:
        return -1
    return len(re.findall(r"^ffmpeg\.exe", p.stdout, re.M))


def _matar_arbol(pid: int) -> None:
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=60, check=False)
    else:
        try:
            os.kill(pid, 9)
        except OSError:
            pass


def una(carga: int) -> dict:
    d = tempfile.mkdtemp(prefix="n36-")
    trabajos = os.path.join(d, "trabajos")
    os.makedirs(trabajos, exist_ok=True)
    cargas = []
    proc = None
    fila: dict = {"carga": carga}
    try:
        for _ in range(carga):
            cargas.append(subprocess.Popen(
                [sys.executable, "-c", _CARGA], stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        fila["ffmpeg_antes"] = ffmpeg_vivos()
        proc = subprocess.Popen(
            [sys.executable, HIJO, "--trabajos", trabajos, "--entrada", VIDEO,
             "--salida", os.path.join(d, "s.webm")],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
            errors="replace", cwd=RAIZ)
        t_lanza = time.perf_counter()
        arr = _lee_evento(proc, "arrancado")
        if "job_id" not in arr:
            fila["fallo_arnes"] = arr
            return fila
        jid, pid_hijo = arr["job_id"], arr["pid"]
        # **Lo que el arnés de N36 tira.** Un trabajo sin candado corre con
        # pinta de huérfano, y quien cancele lo recogerá como muerto.
        fila["aviso_cerrojo"] = arr.get("aviso_cerrojo", "")
        fila["pid_hijo"] = pid_hijo
        fila["pid_popen"] = proc.pid
        fila["lanzador"] = (pid_hijo != proc.pid)
        vuelo = _lee_evento(proc, "en_vuelo")
        fila["en_vuelo"] = bool(vuelo.get("hay"))
        fila["ms_hasta_en_vuelo"] = round(
            (time.perf_counter() - t_lanza) * 1000, 1)

        clave = S.clave_de(jid)
        # El predicado EXACTO que decide `_es_huerfano`, preguntado al sujeto.
        fila["libre_antes"] = cerrojo.esta_libre(clave)
        fila["dueno_antes"] = cerrojo.dueno(clave)

        sv = S.Servicio(_FxFalso(), S.Trabajos(trabajos))
        t0 = time.perf_counter()
        r = sv.job(jid, "cancelar")
        fila["ms_job"] = round((time.perf_counter() - t0) * 1000, 1)
        fila["r"] = r
        fin = _lee_evento(proc, "fin", tope=TOPE_CANCELACION)
        fila["fin"] = fin
        fila["ms_total"] = round((time.perf_counter() - t0) * 1000, 1)
        fila["salida_existe"] = os.path.exists(os.path.join(d, "s.webm"))
        # El veredicto de N36, reproducido tal cual.
        fila["n36_ok"] = bool(
            r.get("motor_detenido") and r.get("via") == "entre procesos"
            and r.get("estado") == S.CANCELADO
            and fin.get("estado") == S.CANCELADO
            and not fila["salida_existe"])
        return fila
    finally:
        for c in cargas:
            try:
                c.kill()
                c.wait(timeout=20)
            except Exception:
                pass
        if proc is not None:
            # El PID REAL, no el del lanzador (trampa 93).
            try:
                _matar_arbol(fila.get("pid_hijo") or proc.pid)
            except Exception:
                pass
            try:
                proc.kill()
                proc.wait(timeout=20)
                proc.stdout.close()
            except Exception:
                pass
        fila["ffmpeg_despues"] = ffmpeg_vivos()
        shutil.rmtree(d, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--carga", type=int, default=0)
    ap.add_argument("--etiqueta", default="")
    args = ap.parse_args()
    et = args.etiqueta or f"carga{args.carga}"
    filas = []
    for i in range(1, args.n + 1):
        f = una(args.carga)
        f["i"] = i
        filas.append(f)
        print(json.dumps(f, ensure_ascii=False), flush=True)
    destino = os.path.join(AQUI, f"sonda-n36-{et}.json")
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(filas, fh, ensure_ascii=False, indent=1)
    ok = sum(1 for f in filas if f.get("n36_ok"))
    print(f"{ok}/{len(filas)} limpias -> {destino}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

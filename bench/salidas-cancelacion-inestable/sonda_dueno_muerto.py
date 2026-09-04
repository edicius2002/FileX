"""Sonda causal de `DuenoMuerto`: ¿quién escribe el estado del trabajo?

`test_sin_deteccion_el_trabajo_se_queda_working_para_siempre` mata al proceso
dueño y exige que el trabajo siga diciendo `working` en el disco: es el
**control positivo del defecto** que la detección vino a cerrar (trampa 116).
Falla con `'failed' != 'working'`.

La pregunta no es «¿qué estado hay?» sino **«quién lo escribió»**, y el disco lo
dice sin ambigüedad porque `Trabajos.volcar` guarda también el `resultado`:

* `{"ok": false, "motivo": "proceso_dueno_muerto"}` -> lo cerró la DETECCIÓN.
* cualquier resumen de conversión -> lo escribió **el propio dueño**, es decir
  el dueño **siguió vivo lo bastante** como para ver morir a su motor y cerrar
  su trabajo. Y entonces la condición que la prueba dice reproducir —«el dueño
  murió sin cerrar su trabajo»— **no se dio** (trampa 38).

Dos variantes, que es lo que la convierte en causal y no en descriptiva:

* **A** — `taskkill /F /T /PID <pid del Popen>`, que es lo que hace el arnés
  hoy. El `/T` recorre el árbol y **no es atómico**: si el nieto (`ffmpeg`)
  muere antes que el hijo (el `python` dueño), el dueño vuelve de
  `communicate`, ve `conv.ok == False`, comprueba que nadie pidió cancelar y
  escribe `FALLIDO`.
* **B** — `taskkill /F /PID <pid REAL del dueño>` primero, sin `/T`. Un dueño
  muerto no puede escribir nada. El motor queda huérfano y se barre después
  **por identidad** —los PID que se le censaron antes de matar—, no por nombre
  (trampa 47).

`--carga N` levanta N procesos de CPU declarados, para preguntar si la ventana
depende de la velocidad de la máquina.

Uso::

    python bench/salidas-cancelacion-inestable/sonda_dueno_muerto.py \
        --n 10 --variante A --carga 0
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

VIDEO = os.path.join(RAIZ, "corpus", "video", "tipico.mp4")
HIJO = os.path.join(RAIZ, "pruebas", "hijo_de_trabajo.py")

TOPE_ARRANQUE = 90.0
_CARGA = "x=0\nwhile True:\n    x=(x*x+1)%1000003\n"


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
    return {"evento": "_sin_" + esperado}


def hijos_de(pid: int) -> list[int]:
    """PID de los hijos directos. Identidad, no nombre (trampa 47)."""
    if sys.platform != "win32":
        return []
    orden = ("Get-CimInstance Win32_Process -Filter \"ParentProcessId=%d\" "
             "| ForEach-Object { $_.ProcessId }" % pid)
    try:
        p = subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                            "-Command", orden],
                           stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, errors="replace", timeout=60)
    except subprocess.TimeoutExpired:
        return []
    return [int(x) for x in re.findall(r"\d+", p.stdout)]


def _tk(args: list[str]) -> int:
    return subprocess.run(["taskkill", "/F"] + args, stdin=subprocess.DEVNULL,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                          timeout=60, check=False).returncode


def lee_json(trabajos: str, jid: str) -> dict:
    try:
        with open(os.path.join(trabajos, jid + ".json"), encoding="utf-8") as fh:
            return json.load(fh)
    except OSError:
        return {}


def quien(d: dict) -> str:
    """Quién escribió el estado que hay en el disco."""
    if not d:
        return "sin_fichero"
    if d.get("estado") == "working":
        return "nadie_lo_cerro"
    res = d.get("resultado") or {}
    if res.get("motivo") == "proceso_dueno_muerto":
        return "la_deteccion"
    return "el_propio_dueno"


def una(variante: str, carga: int) -> dict:
    d = tempfile.mkdtemp(prefix="dm-")
    trabajos = os.path.join(d, "trabajos")
    os.makedirs(trabajos, exist_ok=True)
    cargas, proc = [], None
    fila: dict = {"variante": variante, "carga": carga}
    try:
        for _ in range(carga):
            cargas.append(subprocess.Popen(
                [sys.executable, "-c", _CARGA], stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        proc = subprocess.Popen(
            [sys.executable, HIJO, "--trabajos", trabajos, "--entrada", VIDEO,
             "--salida", os.path.join(d, "s.webm")],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
            errors="replace", cwd=RAIZ)
        arr = _lee_evento(proc, "arrancado")
        if "job_id" not in arr:
            fila["fallo_arnes"] = arr
            return fila
        jid, pid_hijo = arr["job_id"], arr["pid"]
        fila.update(jid=jid, pid_hijo=pid_hijo, pid_popen=proc.pid,
                    lanzador=(pid_hijo != proc.pid))
        fila["en_vuelo"] = bool(_lee_evento(proc, "en_vuelo").get("hay"))

        nietos = hijos_de(pid_hijo)
        fila["nietos"] = nietos
        antes = lee_json(trabajos, jid)
        # La PRECONDICIÓN de la prueba: antes de matar tiene que decir working.
        fila["estado_antes"] = antes.get("estado")

        t0 = time.perf_counter()
        if variante == "A":
            fila["rc_kill"] = _tk(["/T", "/PID", str(proc.pid)])
        else:
            # El dueño PRIMERO y solo. Un muerto no escribe.
            fila["rc_kill"] = _tk(["/PID", str(pid_hijo)])
            for n in nietos:
                _tk(["/T", "/PID", str(n)])
            _tk(["/T", "/PID", str(proc.pid)])
        fila["ms_kill"] = round((time.perf_counter() - t0) * 1000, 1)

        d0 = lee_json(trabajos, jid)
        fila["estado_0"] = d0.get("estado")
        fila["quien_0"] = quien(d0)
        time.sleep(1.5)
        d1 = lee_json(trabajos, jid)
        fila["estado_1"] = d1.get("estado")
        fila["quien_1"] = quien(d1)
        fila["resultado_1"] = d1.get("resultado")
        # El veredicto de la prueba, reproducido tal cual: exige `working`.
        fila["prueba_ok"] = (fila["estado_1"] == "working")
        return fila
    finally:
        for c in cargas:
            try:
                c.kill()
                c.wait(timeout=20)
            except Exception:
                pass
        for n in fila.get("nietos") or []:
            try:
                _tk(["/T", "/PID", str(n)])
            except Exception:
                pass
        if proc is not None:
            for pid in (fila.get("pid_hijo"), proc.pid):
                if pid:
                    try:
                        _tk(["/T", "/PID", str(pid)])
                    except Exception:
                        pass
            try:
                proc.wait(timeout=20)
                proc.stdout.close()
            except Exception:
                pass
        shutil.rmtree(d, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--variante", choices=["A", "B"], default="A")
    ap.add_argument("--carga", type=int, default=0)
    args = ap.parse_args()
    et = f"{args.variante}-carga{args.carga}"
    filas = []
    for i in range(1, args.n + 1):
        f = una(args.variante, args.carga)
        f["i"] = i
        filas.append(f)
        print(json.dumps(f, ensure_ascii=False), flush=True)
    destino = os.path.join(AQUI, f"sonda-dueno-muerto-{et}.json")
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(filas, fh, ensure_ascii=False, indent=1)
    ok = sum(1 for f in filas if f.get("prueba_ok"))
    from collections import Counter
    print(f"{ok}/{len(filas)} con `working` -> {destino}")
    print("quien escribio:", dict(Counter(f.get("quien_1") for f in filas)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

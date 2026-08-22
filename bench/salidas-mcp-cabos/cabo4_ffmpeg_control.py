"""Cabo 4 — control a nivel de ffmpeg: aisla QUE causa el bloqueo.

El hallazgo del arnés MCP fue que `concatenate_videos` cuelga 2 de cada 3 veces **aunque
todas sus invocaciones pasan `-y`**. Este control separa las tres variables:

    (1) `-y`            -> evita el prompt de sobrescritura
    (2) `-nostdin`      -> desactiva la interaccion por teclado
    (3) `stdin=DEVNULL` -> le quita la tuberia al hijo en la construccion del proceso

Cada caso se repite N veces con salida YA EXISTENTE y con un `stdin` que es una tuberia
abierta y muda, igual que la tuberia JSON-RPC de un servidor MCP.
"""

import json
import os
import subprocess
import threading
import sys
import time
from pathlib import Path

RAIZ = Path("D:/Work/research/FileX")
SALIDA = RAIZ / "bench/salidas-mcp-cabos"
TRABAJO = SALIDA / "cabo4_ffmpeg"
ENTRADA = RAIZ / "corpus/video/trivial.mp4"
N = int(os.environ.get("CABO4_N", "5"))
TIMEOUT = float(os.environ.get("CABO4_FFT", "20"))


def matar_arbol(pid):
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, timeout=30)


def prueba(nombre, flags, stdin_modo, repeticiones=N):
    """stdin_modo: 'tuberia' (heredada y muda) | 'devnull'"""
    TRABAJO.mkdir(parents=True, exist_ok=True)
    reg = {"caso": nombre, "flags": flags, "stdin": stdin_modo,
           "n": repeticiones, "colgadas": 0, "ms": []}
    for i in range(repeticiones):
        sal = TRABAJO / f"{nombre}_{i}.mp4"
        sal.write_bytes(b"BASURA" * 32)          # la salida YA EXISTE
        cmd = ["ffmpeg", "-i", str(ENTRADA), *flags,
               "-vf", "scale=320:240", "-c:v", "libx264", str(sal)]
        if stdin_modo == "devnull":
            si = subprocess.DEVNULL
        else:
            si = subprocess.PIPE                 # tuberia abierta y muda
        t0 = time.time()
        p = subprocess.Popen(cmd, stdin=si, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        # Hay que DRENAR stdout/stderr con hilos (si no, se llena el bufer y el bloqueo
        # seria del arnes) y a la vez MANTENER stdin ABIERTO y mudo (si se cierra,
        # ffmpeg lee EOF y decide solo; `communicate()` lo cierra, y por eso no sirve).
        buf = {}
        hilos = []
        for cual in ("stdout", "stderr"):
            f = getattr(p, cual)

            def drenar(f=f, cual=cual):
                try:
                    buf[cual] = f.read()
                except Exception:  # noqa: BLE001
                    buf[cual] = b""
            h = threading.Thread(target=drenar, daemon=True)
            h.start()
            hilos.append(h)
        try:
            p.wait(timeout=TIMEOUT)
            for h in hilos:
                h.join(timeout=2)
            reg["ms"].append(round((time.time() - t0) * 1000, 1))
            reg.setdefault("ultimo_stderr",
                           buf.get("stderr", b"").decode("utf8", "replace")[-300:])
            reg.setdefault("codigos", []).append(p.returncode)
        except subprocess.TimeoutExpired:
            reg["colgadas"] += 1
            reg["ms"].append(None)
            matar_arbol(p.pid)
        finally:
            for f in (p.stdout, p.stderr, p.stdin):
                try:
                    f and f.close()
                except Exception:  # noqa: BLE001
                    pass
            reg.setdefault("bytes_salida", []).append(
                sal.stat().st_size if sal.exists() else None)
    ok = [m for m in reg["ms"] if m is not None]
    reg["ms_mediana_ok"] = sorted(ok)[len(ok) // 2] if ok else None
    return reg


def main():
    casos = [
        ("sin_y__tuberia", [], "tuberia"),
        ("con_y__tuberia", ["-y"], "tuberia"),
        ("con_y_nostdin__tuberia", ["-nostdin", "-y"], "tuberia"),
        ("sin_y__devnull", [], "devnull"),
        ("con_y__devnull", ["-y"], "devnull"),
    ]
    res = []
    for nombre, flags, modo in casos:
        r = prueba(nombre, flags, modo)
        print(f"{nombre:26s} flags={flags!s:20s} stdin={modo:8s} "
              f"colgadas={r['colgadas']}/{r['n']} mediana={r['ms_mediana_ok']} ms", flush=True)
        res.append(r)
    (SALIDA / "cabo4_ffmpeg_control.json").write_text(
        json.dumps({"n_por_caso": N, "timeout_s": TIMEOUT, "casos": res},
                   ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())

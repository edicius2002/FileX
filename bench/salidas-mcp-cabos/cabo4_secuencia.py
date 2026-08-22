"""Cabo 4 — control de la SECUENCIA de `concatenate_videos`, fuera de MCP.

Reproduce las mismas 4 invocaciones que hace la herramienta (1 ffprobe + 2 normalizaciones
+ 1 concat), **todas con `-y`**, variando solo `stdin`:

    tuberia  : una tuberia abierta y muda, como la tuberia JSON-RPC de un servidor MCP
    devnull  : `stdin=DEVNULL`

Si `-y` bastara, ninguna de las dos deberia colgarse.
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

RAIZ = Path("D:/Work/research/FileX")
SALIDA = RAIZ / "bench/salidas-mcp-cabos"
ENTRADA = str(RAIZ / "corpus/video/trivial.mp4").replace("\\", "/")
N = int(os.environ.get("CABO4_N", "5"))
TIMEOUT = float(os.environ.get("CABO4_SEQT", "25"))


def correr(cmd, stdin_modo):
    """Lanza cmd, drena stdout/stderr con hilos y MANTIENE stdin abierto si es tuberia."""
    si = subprocess.DEVNULL if stdin_modo == "devnull" else subprocess.PIPE
    p = subprocess.Popen(cmd, stdin=si, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    for f in (p.stdout, p.stderr):
        threading.Thread(target=lambda f=f: f.read(), daemon=True).start()
    t0 = time.time()
    try:
        p.wait(timeout=TIMEOUT)
        return round((time.time() - t0) * 1000, 1), False
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                       capture_output=True, timeout=30)
        return round((time.time() - t0) * 1000, 1), True


def secuencia(stdin_modo):
    td = tempfile.mkdtemp()
    pasos = []
    colgada = False
    normas = []
    for i in (0, 1):
        n = os.path.join(td, f"norm_{i}.mp4")
        ms, colg = correr(["ffmpeg", "-i", ENTRADA, "-vf", "scale=640:480", "-r", "24.0",
                           "-c:v", "libx264", "-c:a", "aac", "-y", n], stdin_modo)
        pasos.append({"paso": f"norm_{i}", "ms": ms, "colgada": colg})
        colgada = colgada or colg
        normas.append(n)
        if colg:
            break
    if not colgada:
        lista = os.path.join(td, "concat_list.txt")
        Path(lista).write_text("".join(f"file '{n}'\n" for n in normas), encoding="utf-8")
        sal = os.path.join(td, "final.mp4")
        ms, colg = correr(["ffmpeg", "-f", "concat", "-safe", "0", "-i", lista,
                           "-c", "copy", "-y", sal], stdin_modo)
        pasos.append({"paso": "concat", "ms": ms, "colgada": colg})
        colgada = colgada or colg
    return {"stdin": stdin_modo, "colgada": colgada, "pasos": pasos}


def main():
    res = {}
    for modo in ("tuberia", "devnull"):
        reps = [secuencia(modo) for _ in range(N)]
        n_colg = sum(1 for r in reps if r["colgada"])
        res[modo] = {"n": N, "secuencias_colgadas": n_colg, "repeticiones": reps}
        print(f"stdin={modo:8s} secuencias colgadas: {n_colg}/{N}", flush=True)
        for r in reps:
            print("   ", " | ".join(f"{p['paso']}={p['ms']}ms{'  COLGADA' if p['colgada'] else ''}"
                                    for p in r["pasos"]), flush=True)
    (SALIDA / "cabo4_secuencia.json").write_text(
        json.dumps({"timeout_s": TIMEOUT, "resultados": res}, ensure_ascii=False, indent=2),
        encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())

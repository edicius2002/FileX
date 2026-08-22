"""Cabo 4 — servidor MCP minimo que aisla la variable `stdin` del subproceso.

Dos herramientas identicas salvo en como construyen el proceso hijo:

    conv_heredado : `stdin` NO se toca  -> el hijo hereda la tuberia JSON-RPC del servidor
    conv_devnull  : `stdin=DEVNULL`     -> el hijo no tiene acceso a la tuberia

Ambas ejecutan exactamente la misma secuencia de ffmpeg **con `-y` en todas partes**, la
misma que `concatenate_videos`. Si `-y` bastara, las dos terminarian siempre.
"""

import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP

RAIZ = Path("D:/Work/research/FileX")
ENTRADA = str(RAIZ / "corpus/video/trivial.mp4").replace("\\", "/")

mcp = FastMCP("filex-cabo4-stdin")


def _correr(cmd, heredar_stdin: bool, timeout: float):
    kw = {}
    if not heredar_stdin:
        kw["stdin"] = subprocess.DEVNULL
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)
    for f in (p.stdout, p.stderr):
        threading.Thread(target=lambda f=f: f.read(), daemon=True).start()
    t0 = time.time()
    try:
        p.wait(timeout=timeout)
        return round((time.time() - t0) * 1000, 1), False
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                       capture_output=True, timeout=30)
        return round((time.time() - t0) * 1000, 1), True


def _secuencia(heredar_stdin: bool, timeout: float) -> str:
    td = tempfile.mkdtemp()
    partes, normas = [], []
    for i in (0, 1):
        n = os.path.join(td, f"norm_{i}.mp4")
        ms, colg = _correr(["ffmpeg", "-i", ENTRADA, "-vf", "scale=640:480", "-r", "24.0",
                            "-c:v", "libx264", "-c:a", "aac", "-y", n],
                           heredar_stdin, timeout)
        partes.append(f"norm_{i}={ms}ms{' COLGADA' if colg else ''}")
        if colg:
            return "PASO COLGADO: " + " | ".join(partes)
        normas.append(n)
    lista = os.path.join(td, "concat_list.txt")
    Path(lista).write_text("".join(f"file '{n}'\n" for n in normas), encoding="utf-8")
    sal = os.path.join(td, "final.mp4")
    ms, colg = _correr(["ffmpeg", "-f", "concat", "-safe", "0", "-i", lista,
                        "-c", "copy", "-y", sal], heredar_stdin, timeout)
    partes.append(f"concat={ms}ms{' COLGADA' if colg else ''}")
    if colg:
        return "PASO COLGADO: " + " | ".join(partes)
    return "OK " + " | ".join(partes)


@mcp.tool()
def conv_heredado(timeout: float = 20.0) -> str:
    """Secuencia ffmpeg con `-y` cuyos hijos HEREDAN el stdin del servidor MCP."""
    return _secuencia(True, timeout)


@mcp.tool()
def conv_devnull(timeout: float = 20.0) -> str:
    """La MISMA secuencia, con `stdin=DEVNULL` en la construccion del proceso."""
    return _secuencia(False, timeout)


if __name__ == "__main__":
    mcp.run()

"""Arranque en frío del servidor MCP de FileX, medido de fuera.

`RESULTADOS-MCP.md` §9.2(c): *«el arranque en frío no correlaciona con el tamaño
del catálogo, sino con lo que el servidor importa. Un FileX que delegue en ffmpeg
e ImageMagick nativos arrancará en ~1 s»*. **Es una predicción, y aquí se
comprueba.** Referencias medidas: `video-audio-mcp` 1.202 ms · `image-worker-mcp`
2.620 ms · `ffmpeg-mcp-lite` 6.689 / 817 ms · `docling-mcp` ~6.000 ms ·
`markitdown-mcp` 3.413 ms.

Mide el reloj de pared desde `Popen` hasta que el servidor contesta a
`tools/list`, por JSON-RPC crudo sobre stdio — sin cliente MCP, para no meter en
la cuenta el arranque del propio cliente.

    .venv-mcp-filex/Scripts/python.exe bench/salidas-hito4/h4_arranque.py

**El primer arranque no cuenta**: Windows Defender infla el primer acceso a un
binario (41 → 110 ms, `CLAUDE.md` §4 trampa 7). Se calienta y se reporta la
mediana de n≥9.
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
PY = os.path.join(RAIZ, ".venv-mcp-filex", "Scripts", "python.exe")
N = 9
TIMEOUT = 30.0


def _envia(p, obj):
    p.stdin.write(json.dumps(obj) + "\n")
    p.stdin.flush()


def _lee(p, tope):
    """Lee líneas hasta encontrar una respuesta JSON-RPC con `id`."""
    fin = time.perf_counter() + tope
    while time.perf_counter() < fin:
        linea = p.stdout.readline()
        if not linea:
            return None
        linea = linea.strip()
        if not linea:
            continue
        try:
            d = json.loads(linea)
        except ValueError:
            continue
        if "id" in d:
            return d
    return None


def una() -> tuple[float, float, int]:
    t0 = time.perf_counter()
    p = subprocess.Popen(
        [PY, "-m", "filex.mcp", "--raiz", RAIZ],
        cwd=RAIZ,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONPATH": RAIZ},
    )
    try:
        _envia(p, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                   "params": {"protocolVersion": "2025-11-25",
                              "capabilities": {"roots": {"listChanged": True}},
                              "clientInfo": {"name": "h4-arranque", "version": "1"}}})
        ini = _lee(p, TIMEOUT)
        t_ini = (time.perf_counter() - t0) * 1000
        _envia(p, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        _envia(p, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        lst = _lee(p, TIMEOUT)
        t_lst = (time.perf_counter() - t0) * 1000
        n = len(((lst or {}).get("result") or {}).get("tools", []))
        assert ini is not None and n, "el servidor no contestó"
        return t_ini, t_lst, n
    finally:
        try:
            p.stdin.close()
        except Exception:
            pass
        try:
            p.wait(timeout=5)
        except Exception:
            p.kill()


def main() -> int:
    una()                                   # calentar (Defender, trampa nº 7)
    inis, lsts, ns = [], [], set()
    for _ in range(N):
        a, b, n = una()
        inis.append(a)
        lsts.append(b)
        ns.add(n)
    res = {
        "n": N,
        "nota": "sesión de escritorio remoto activa: SUCIA por estructura",
        "initialize_ms_mediana": round(statistics.median(inis), 1),
        "tools_list_ms_mediana": round(statistics.median(lsts), 1),
        "initialize_ms_min": round(min(inis), 1),
        "tools_list_ms_min": round(min(lsts), 1),
        "n_herramientas": sorted(ns),
        "referencias_del_sector_ms": {
            "video-audio-mcp_27": 1202, "image-worker-mcp_2": 2620,
            "ffmpeg-mcp-lite_8_frio": 6689, "ffmpeg-mcp-lite_8_caliente": 817,
            "docling-mcp_19": 6000, "markitdown-mcp_1": 3413,
        },
        "prediccion_a_comprobar": "RESULTADOS-MCP.md §9.2(c): ~1 s",
    }
    salida = os.path.join(AQUI, "h4_arranque.json")
    with open(salida, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print(f"initialize {res['initialize_ms_mediana']} ms · "
          f"tools/list {res['tools_list_ms_mediana']} ms · "
          f"{res['n_herramientas']} herramientas · n={N}")
    print(f"-> {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

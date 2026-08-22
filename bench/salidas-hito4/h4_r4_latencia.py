"""R4: ¿es el mismo mensaje **y la misma latencia** para «prohibido» y «no existe»?

`filex/confinamiento.py:19` deja escrito el pendiente con todas las letras:

    «Y la equivalencia de latencia entre los dos casos es PENDIENTE: hoy el
    camino de "no existe" puede ser más corto y eso es un oráculo temporal.»

Aquí se cierra con números. El precedente: `servers/filesystem` mide **1,4 ms
(prohibido) frente a 1,9 ms (no existe)** y se considera equivalente
(`RESULTADOS-MCP.md` §5); `kordoc` es un oráculo completo por hacer
`realpathSync` **antes** de `assertWithinRoot`.

Cuatro celdas, no dos, porque el oráculo tiene dos ejes:

    fuera_existe      C:/Windows/win.ini            (existe, prohibido)
    fuera_no_existe   C:/Windows/no_existe_xyz.ini  (no existe, prohibido)
    dentro_existe     un fichero real de la raíz    (existe, permitido)
    dentro_no_existe  un nombre inventado en la raíz(no existe, permitido)

**Dentro de la raíz el oráculo es legítimo** —hay que decirle al usuario que su
fichero no está—; lo que no puede haber es señal **fuera**.

    .venv-mcp-filex/Scripts/python.exe bench/salidas-hito4/h4_r4_latencia.py
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, RAIZ)

from filex.mcp import Servicio, Trabajos                          # noqa: E402
from filex.nucleo import FileX                                    # noqa: E402

N = 201                     # impar: la mediana es un valor observado


def mediana(sv, ruta):
    t = []
    for _ in range(N):
        t0 = time.perf_counter()
        r = sv.despachar("inspect", {"ruta": ruta})
        t.append((time.perf_counter() - t0) * 1e6)          # µs
    return statistics.median(t), r


def main() -> int:
    raiz = tempfile.mkdtemp(prefix="h4-r4-")
    dentro = os.path.join(raiz, "dentro.png")
    with open(dentro, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 40)
    sv = Servicio(FileX(raices_lectura=[raiz]),
                  Trabajos(tempfile.mkdtemp(prefix="h4-r4t-")))

    celdas = {
        "fuera_existe": "C:/Windows/win.ini",
        "fuera_no_existe": "C:/Windows/no_existe_xyzzy_412.ini",
        "dentro_existe": dentro,
        "dentro_no_existe": os.path.join(raiz, "no_existe_xyzzy_412.png"),
        "travesia": os.path.join(raiz, "..", "..", "Windows", "win.ini"),
        "ads": dentro + ":oculto",              # R12: W9 concedió acceso a un ADS
    }
    for r in celdas.values():                   # calentar (trampa nº 7)
        sv.despachar("inspect", {"ruta": r})

    filas = {}
    for etq, ruta in celdas.items():
        us, resp = mediana(sv, ruta)
        filas[etq] = {"mediana_us": round(us, 1),
                      "respuesta": json.dumps(resp, ensure_ascii=False)[:160],
                      "denegado": "error" in resp}

    fe, fn = filas["fuera_existe"]["mediana_us"], filas["fuera_no_existe"]["mediana_us"]
    razon = max(fe, fn) / min(fe, fn)
    mismos = (filas["fuera_existe"]["respuesta"] == filas["fuera_no_existe"]["respuesta"])

    res = {
        "n": N,
        "nota": "sesión de escritorio remoto activa: SUCIA por estructura. "
                "Las cifras ABSOLUTAS de tandas distintas no comparan; la RAZÓN "
                "entre celdas de esta misma tanda, sí.",
        "celdas": filas,
        "mismo_mensaje_fuera": mismos,
        "razon_latencia_fuera": round(razon, 3),
        "veredicto": ("sin oráculo detectable fuera de la raíz"
                      if mismos and razon < 1.25 else
                      "REVISAR: hay señal distinguible fuera de la raíz"),
        "referencia": "servers/filesystem: 1,4 ms vs 1,9 ms (razón 1,36) y se "
                      "consideró equivalente (RESULTADOS-MCP.md §5)",
    }
    salida = os.path.join(AQUI, "h4_r4_latencia.json")
    with open(salida, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)

    for etq, f in filas.items():
        print(f"  {etq:<18} {f['mediana_us']:>9.1f} µs  "
              f"{'DENEGADO' if f['denegado'] else 'concedido':<10} {f['respuesta'][:70]}")
    print(f"  mismo mensaje fuera: {mismos} · razón de latencia {razon:.3f}")
    print(f"  -> {res['veredicto']}")
    print(f"  -> {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""C35 -- la latencia limpia que `bench/gotenberg-y-mcp.md` dejó PENDIENTE:
Gotenberg (servicio HTTP vivo) frente a `filex-c13` (contenedor efímero,
`docker run` por conversión), sobre la MISMA arista en las dos vías —
`txt → pdf` por LibreOffice, la única que Gotenberg y `filex-c13` resuelven
con el MISMO motor subyacente (soffice), así que la diferencia medida es la
arquitectura (servicio vivo contra contenedor por petición), no el motor.

**Misma orden que ejecuta el código (trampa 79):** para `filex-c13` esto NO
reimplementa `argv_docker()` a mano como hizo `c35_gotenberg.py` (round 1) --
llama a `filex.nucleo.FileX.convertir()` de verdad, con una única instancia
de `FileX` construida una vez y reutilizada (igual que hace `filex/api.py`,
que documenta que construirla cuesta ~23,6 s en frío y no es viable por
petición). Es la orden de PRODUCCIÓN, con `--init`, nombre único,
`--network none` y `timeout -k 5` dentro, tal como la construye
`filex/motor_contenedor.py::_argv_docker`.

Dos testigos de ruido, con tope al testigo (trampa "un testigo que puede
tumbar la medición no es un testigo"):
  A. Deriva monohilo: mediana de la primera mitad de la tanda contra la
     segunda, POR VÍA.
  B. Nivel de proceso: `cmd /c exit` antes y después de TODA la tanda, con
     tope de 20 s. worker1 está en el carril GPU usando la CPU en paralelo.

    D:\\Work\\research\\FileX\\.venv-mcp-filex\\Scripts\\python.exe bench/salidas-latencia-gotenberg/medir_latencia.py
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)

from filex.nucleo import FileX  # noqa: E402

ENTRADA = os.path.join(RAIZ, "bench", "salidas-hito5", "entradas", "entrada.txt")
GOT = "http://localhost:3200"
N = 11
TOPE_TESTIGO = 20.0


def testigo_proceso():
    ini = time.perf_counter()
    try:
        subprocess.run(["cmd", "/c", "exit", "0"], stdin=subprocess.DEVNULL,
                       capture_output=True, timeout=TOPE_TESTIGO)
        ms = (time.perf_counter() - ini) * 1000
        return {"ms": round(ms, 2), "sucia": ms > 30}
    except subprocess.TimeoutExpired:
        return {"ms": TOPE_TESTIGO * 1000, "sucia": True, "tope_alcanzado": True}


def multipart(ficheros):
    b = "----filexc35-" + uuid.uuid4().hex
    out = bytearray()
    for nombre, fichero, datos in ficheros:
        out += (f"--{b}\r\nContent-Disposition: form-data; name=\"{nombre}\"; "
                f"filename=\"{fichero}\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode()
        out += datos + b"\r\n"
    out += f"--{b}--\r\n".encode()
    return b, bytes(out)


def gotenberg_una_vez(datos_entrada):
    ficheros = [("files", "entrada.txt", datos_entrada)]
    b, cuerpo = multipart(ficheros)
    req = urllib.request.Request(GOT + "/forms/libreoffice/convert", data=cuerpo,
                                 method="POST",
                                 headers={"Content-Type": "multipart/form-data; boundary=" + b})
    ini = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            cuerpo_resp = r.read()
            ms = (time.perf_counter() - ini) * 1000
            return {"ms": ms, "http": r.status, "bytes": len(cuerpo_resp)}
    except urllib.error.HTTPError as e:
        ms = (time.perf_counter() - ini) * 1000
        return {"ms": ms, "http": e.code, "bytes": 0}


def c13_una_vez(fx, entrada, directorio, n):
    salida = os.path.join(directorio, "salida_%03d.pdf" % n)
    ini = time.perf_counter()
    conv = fx.convertir(entrada, salida)
    ms = (time.perf_counter() - ini) * 1000
    ok = not conv.motivo and os.path.isfile(salida) and os.path.getsize(salida) > 0
    return {"ms": ms, "motivo": conv.motivo, "ok": ok,
            "bytes": os.path.getsize(salida) if os.path.isfile(salida) else 0}


def resumen(tiempos):
    mitad = len(tiempos) // 2
    return {
        "n": len(tiempos),
        "mediana_ms": round(statistics.median(tiempos), 1),
        "p90_ms": round(statistics.quantiles(tiempos, n=10)[8], 1) if len(tiempos) >= 4 else None,
        "min_ms": round(min(tiempos), 1), "max_ms": round(max(tiempos), 1),
        "deriva_primera_vs_segunda_mitad": round(
            statistics.median(tiempos[mitad:]) / max(statistics.median(tiempos[:mitad]), 1e-9), 3),
    }


def docker_huerfanos_de_esta_tanda(antes, despues):
    # trampa 37: `docker ps -a`, nunca `docker ps` -- un contenedor `Created`
    # no aparece en `docker ps`. `--name` de `_argv_docker` los hace
    # nombrables; se listan por si alguno sobrevivió al `--rm`.
    return sorted(set(despues) - set(antes))


def listar_contenedores():
    p = subprocess.run(["docker", "ps", "-a", "--format", "{{.Names}}"],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       timeout=20)
    return (p.stdout or "").splitlines()


def main():
    testigo_a = testigo_proceso()
    print("testigo de proceso ANTES: %s" % testigo_a)

    with open(ENTRADA, "rb") as fh:
        datos_entrada = fh.read()
    contenedores_antes = listar_contenedores()

    print("construyendo FileX() una vez (motores + Docker)...")
    ini_fx = time.perf_counter()
    fx = FileX()
    print("  FileX() lista en %.1f s" % (time.perf_counter() - ini_fx))

    tmp = tempfile.mkdtemp(prefix="filex-c35-lat-")
    try:
        tiempos_got, tiempos_c13 = [], []
        celdas = []
        for i in range(N):
            g = gotenberg_una_vez(datos_entrada)
            c = c13_una_vez(fx, ENTRADA, tmp, i)
            tiempos_got.append(g["ms"])
            tiempos_c13.append(c["ms"])
            celdas.append({"i": i, "gotenberg": g, "c13": c})
            print("  %2d/%d  gotenberg=%8.1f ms (http=%s)   c13=%8.1f ms (ok=%s)"
                  % (i + 1, N, g["ms"], g["http"], c["ms"], c["ok"]))

        contenedores_despues = listar_contenedores()
        huerfanos = docker_huerfanos_de_esta_tanda(contenedores_antes, contenedores_despues)

        testigo_b = testigo_proceso()
        print("testigo de proceso DESPUÉS: %s" % testigo_b)

        resultado = {
            "entrada": "entrada.txt (bench/salidas-hito5/entradas/), via LibreOffice en las dos vías",
            "n": N,
            "testigo_proceso_antes": testigo_a,
            "testigo_proceso_despues": testigo_b,
            "sucia": testigo_a["sucia"] or testigo_b["sucia"],
            "celdas": celdas,
            "gotenberg": resumen(tiempos_got),
            "c13": resumen(tiempos_c13),
            "huerfanos_docker_ps_a": huerfanos,
        }
        resultado["ratio_c13_sobre_gotenberg_mediana"] = round(
            resultado["c13"]["mediana_ms"] / resultado["gotenberg"]["mediana_ms"], 2)

        print("\nGotenberg: mediana=%.1f ms p90=%.1f ms" %
              (resultado["gotenberg"]["mediana_ms"], resultado["gotenberg"]["p90_ms"]))
        print("filex-c13: mediana=%.1f ms p90=%.1f ms" %
              (resultado["c13"]["mediana_ms"], resultado["c13"]["p90_ms"]))
        print("ratio c13/gotenberg (mediana): %.2fx" % resultado["ratio_c13_sobre_gotenberg_mediana"])
        print("huérfanos docker ps -a de esta tanda: %s" % (huerfanos or "ninguno"))

        with open(os.path.join(os.path.dirname(__file__), "resultado.json"),
                  "w", encoding="utf-8") as fh:
            json.dump(resultado, fh, indent=1, ensure_ascii=False)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()

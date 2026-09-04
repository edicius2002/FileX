# -*- coding: utf-8 -*-
"""B3 -- mide `marker` (via `marker_single`, `.venv-marker`) sobre
`corpus/pdf/tipico_texto.pdf`: tiempo, memoria pico (RSS del proceso Y de
sus hijos, con `psutil`) y calidad del texto extraido contra la verdad
CONOCIDA del documento (confirmada visualmente renderizando el PDF con
`magick`, no supuesta -- el PDF tiene un defecto propio: el glifo de la
`n~` esta roto en el PDF FUENTE y se ve como `n` + un circunflejo suelto,
asi que la "verdad" declarada aqui es la que el documento realmente
muestra, no la que "deberia" mostrar).

`.venv-marker` es CPU (`torch` sin paquetes `nvidia-*`, MEDIDO): no toma el
lock de GPU. **No instala nada en el venv** (protegido, `CLAUDE.md` §1) --
solo ejecuta lo que ya esta instalado (`marker`, `psutil`).

    D:\\Work\\research\\FileX\\.venv-marker\\Scripts\\python.exe bench/salidas-suelo-n32/medir_marker.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time

import psutil

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENTRADA = os.path.join(RAIZ, "corpus", "pdf", "tipico_texto.pdf")
SALIDA_DIR = os.path.join(os.path.dirname(__file__), "marker_out")
MARKER_SINGLE = os.path.join(os.path.dirname(sys.executable), "marker_single.exe")
TOPE_S = 400.0  # CLAUDE.md: timeouts explicitos en todo. El primer intento
                 # (modo por defecto) tardo 432 s solo en intentar levantar un
                 # contenedor de GPU y se aborto por seguridad -- este segundo
                 # intento fuerza `--mode fast` (sin VLM) sobre 1 pagina trivial:
                 # no deberia necesitar tanto. Se declara el rc y el tiempo,
                 # se corte o no.

# Verdad CONOCIDA (confirmada renderizando el PDF con `magick -density 150` y
# leyendo la imagen resultante, no supuesta del texto-capa cruda): el PDF
# fuente tiene el glifo de "n~" roto -- se ve como "n" + un circunflejo
# suelto, no como una "n~" real. Se evalua lo que el documento MUESTRA.
ESPERADO = [
    "FileX - documento de prueba con texto seleccionable",
    "Segunda linea: acentos aeiou n",
    "y simbolos % & @",
    "Tabla",
    "Col A",
    "Col B",
    "Col C",
]


def _norm(s: str) -> str:
    import re
    import unicodedata
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _lev(a, b):
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def evaluar(texto: str) -> dict:
    n = _norm(texto)
    ref = _norm(" ".join(ESPERADO))
    d = _lev(ref, n)
    det = []
    for e in ESPERADO:
        ne = _norm(e)
        det.append({"esperado": e, "presente": ne in n})
    return {
        "cer_pct": round(100 * d / max(1, len(ref)), 2),
        "chars_ref": len(ref),
        "chars_salida": len(n),
        "frases_presentes": sum(1 for x in det if x["presente"]),
        "frases_totales": len(det),
        "detalle": det,
    }


def main():
    os.makedirs(SALIDA_DIR, exist_ok=True)
    if not os.path.isfile(MARKER_SINGLE):
        print("BLOQUEO: no existe %s" % MARKER_SINGLE)
        sys.exit(1)
    if not os.path.isfile(ENTRADA):
        print("BLOQUEO: no existe %s" % ENTRADA)
        sys.exit(1)

    # SEGUNDO INTENTO (CLAUDE.md: dos intentos por problema): el primero,
    # sin `--mode`, dejo que marker eligiera su modo por defecto y ese modo
    # lanzo un `docker run --gpus device=0 ... vllm/vllm-openai` (Surya-VLM)
    # SIN que nadie tomara el lock de GPU -- ver el informe. `--mode fast`
    # evita el modelo VLM de layout (solo OCR por bloques con detectores
    # ligeros de CPU, segun `marker_single --help`).
    cmd = [MARKER_SINGLE, ENTRADA, "--output_dir", SALIDA_DIR,
           "--output_format", "markdown", "--mode", "fast"]
    print("orden: %s" % " ".join(cmd))
    print("tope: %.0f s" % TOPE_S)

    env = dict(os.environ)
    env["TORCH_DEVICE"] = "cpu"  # cinturon y tirantes: fuerza CPU tambien en surya/settings.py

    ini = time.perf_counter()
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", env=env)
    p = psutil.Process(proc.pid)

    salida_texto = []

    def _drenar():
        try:
            for linea in proc.stdout:
                salida_texto.append(linea)
        except Exception:
            pass

    hilo = threading.Thread(target=_drenar, daemon=True)
    hilo.start()

    pico_rss_mb = 0.0
    muestras = 0
    tope_alcanzado = False
    abortado_por_docker = False
    cmdline_docker = []
    while True:
        try:
            hijos = p.children(recursive=True)
            total_rss = p.memory_info().rss
            for h in hijos:
                try:
                    total_rss += h.memory_info().rss
                    # SEGURIDAD: si algun hijo intenta lanzar Docker (el
                    # camino del vLLM/GPU del primer intento), abortar YA --
                    # no se tiene el lock de GPU y otro carril puede estar
                    # usando la tarjeta.
                    if h.name().lower().startswith("docker"):
                        abortado_por_docker = True
                        try:
                            cmdline_docker.append(" ".join(h.cmdline()))
                        except Exception:
                            pass
                except psutil.NoSuchProcess:
                    pass
            pico_rss_mb = max(pico_rss_mb, total_rss / (1024 * 1024))
            muestras += 1
        except psutil.NoSuchProcess:
            pass
        if abortado_por_docker:
            print("ABORTADO: un hijo de marker intento lanzar Docker (posible "
                  "contenedor de GPU) -- se mata el arbol antes de que arranque.")
            break
        if proc.poll() is not None:
            break
        if time.perf_counter() - ini > TOPE_S:
            tope_alcanzado = True
            break
        time.sleep(0.2)

    if abortado_por_docker or tope_alcanzado or proc.poll() is None:
        try:
            p.kill()
            for h in p.children(recursive=True):
                try:
                    h.kill()
                except psutil.NoSuchProcess:
                    pass
        except psutil.NoSuchProcess:
            pass
    rc = proc.wait(timeout=15) if not (abortado_por_docker or tope_alcanzado) else -1
    hilo.join(timeout=5)
    dur_s = time.perf_counter() - ini

    print("rc=%s  duracion=%.2f s  pico_rss=%.1f MB (n=%d muestras)  "
          "tope_alcanzado=%s  abortado_por_docker=%s"
          % (rc, dur_s, pico_rss_mb, muestras, tope_alcanzado, abortado_por_docker))

    resultado = {
        "rc": rc, "duracion_s": round(dur_s, 2),
        "pico_rss_mb": round(pico_rss_mb, 1), "muestras_rss": muestras,
        "tope_alcanzado": tope_alcanzado,
        "abortado_por_docker": abortado_por_docker,
        "cmdline_docker": cmdline_docker,
        "cmd": cmd,
    }

    if rc == 0 and not tope_alcanzado and not abortado_por_docker:
        base = os.path.splitext(os.path.basename(ENTRADA))[0]
        md_path = os.path.join(SALIDA_DIR, base, base + ".md")
        if os.path.isfile(md_path):
            with open(md_path, encoding="utf-8") as fh:
                md = fh.read()
            resultado["md_bytes"] = len(md.encode("utf-8"))
            resultado["md_path"] = os.path.relpath(md_path, RAIZ)
            resultado["evaluacion"] = evaluar(md)
            print("md: %d B -> cer=%.2f%%  frases %d/%d"
                  % (resultado["md_bytes"], resultado["evaluacion"]["cer_pct"],
                     resultado["evaluacion"]["frases_presentes"],
                     resultado["evaluacion"]["frases_totales"]))
        else:
            resultado["error"] = "rc=0 pero no aparecio %s" % md_path
            print("AVISO: %s" % resultado["error"])
    else:
        resultado["cola_stdout"] = "".join(salida_texto[-60:])
        print("--- ultimas lineas de stdout/stderr ---")
        print(resultado["cola_stdout"])

    with open(os.path.join(os.path.dirname(__file__), "resultado_marker.json"),
              "w", encoding="utf-8") as fh:
        json.dump(resultado, fh, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()

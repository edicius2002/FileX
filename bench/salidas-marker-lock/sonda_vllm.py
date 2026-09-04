# -*- coding: utf-8 -*-
"""Sonda: ¿POR QUÉ muere el contenedor vLLM que lanza surya?

No es un intento de medir B3: es el instrumento que convierte «no se pudo» en
«no se pudo POR ESTO». El intento 1 devolvió `SpawnError ... within 600.0s` con
los logs del contenedor perdidos —`_capture_server_logs` de surya hace
`docker logs` sobre un contenedor que `--rm` ya borró—, así que la causa raíz
se queda sin registrar. Esta sonda reproduce la MISMA orden con tres cambios,
todos del lado del instrumento y ninguno del sujeto:

1. **sin `--rm`**: el contenedor sobrevive a su propia muerte, así que se pueden
   leer sus logs enteros y su código de salida (trampa 72: *el `rc` no es una
   pista, es la respuesta*).
2. **`--name` propio con marca de tiempo**: único, así que no puede chocar
   (trampa 39: un duplicado sale con `rc=125` y «Conflict»), y sobre todo
   NOMBRADO, que es lo único que hace matable a un contenedor (trampa 37).
3. **grabadora**: un `docker logs -f` a fichero desde el instante del arranque,
   por si el contenedor se fuera igualmente.

La orden se construye desde la FUENTE —`surya/inference/backends/vllm.py:143-198`
y los valores por defecto de `surya/settings.py`—, no de la línea de órdenes que
capturó el arnés, que salió truncada en el log.

El lock de GPU se toma con `tomar()`/`soltar()`, no con el `with` (trampa 88).

    D:\\Work\\research\\FileX\\.venv-marker\\Scripts\\python.exe \\
        bench/salidas-marker-lock/sonda_vllm.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)
from filex import gpu  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
TOPE_S = 420.0
PUERTO = 58123
NOMBRE = "filex-b3-sonda-%d" % int(time.time())

# Valores por defecto de surya/settings.py, citados por línea:
#   VLLM_DOCKER_IMAGE           :96   vllm/vllm-openai:v0.20.1
#   VLLM_GPUS                   :97   0
#   VLLM_DTYPE                  :~98  bfloat16
#   VLLM_GPU_TYPE               :99   4090
#   VLLM_GPU_MEMORY_UTILIZATION :104  0.85
#   VLLM_MAX_MODEL_LEN          :~101 18000
IMAGEN = "vllm/vllm-openai:v0.20.1"
MODELO = "datalab-to/surya-ocr-2"
HF_CACHE = os.path.expanduser("~/.cache/huggingface")


def orden(nombre: str, puerto: int, extra: list[str] | None = None) -> list[str]:
    cmd = [
        "docker", "run", "-d",           # SIN --rm: ver el docstring
        "--name", nombre,
        "--runtime", "nvidia",
        "--gpus", "device=0",
        "-v", "%s:/root/.cache/huggingface" % HF_CACHE,
        "-p", "%d:8000" % puerto,
        "--ipc=host",
        IMAGEN,
        "--model", MODELO,
        "--no-enforce-eager",
        "--max-num-seqs", "32",
        "--dtype", "bfloat16",
        "--max-model-len", "18000",
        "--max-num-batched-tokens", "8192",
        "--gpu-memory-utilization", "0.85",
        "--enable-prefix-caching",
        "--mm-processor-kwargs", json.dumps({"min_pixels": 3136, "max_pixels": 6291456}),
        "--served-model-name", MODELO,
        "--speculative-config", json.dumps({"method": "mtp", "num_speculative_tokens": 2}),
    ]
    return cmd + list(extra or [])


def sh(args: list[str], tope: float = 90.0) -> tuple[int, str]:
    try:
        r = subprocess.run(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=tope)
    except (OSError, subprocess.SubprocessError) as e:
        return -1, "EXCEPCION: %r" % (e,)
    return r.returncode, r.stdout.decode("utf-8", "replace")


def vram() -> int | None:
    return gpu.vram_libre_mib()


def main() -> None:
    reg: dict = {"nombre": NOMBRE, "puerto": PUERTO, "tope_s": TOPE_S}
    lock = gpu.Lock("B3-sonda-vllm")
    t0 = time.perf_counter()
    if not lock.tomar(espera=300):
        reg["bloqueo"] = "no se pudo tomar el lock; dueño=%r" % gpu.dueno()
        print(json.dumps(reg, ensure_ascii=False, indent=1))
        return
    reg["lock_tomar_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    print("lock tomado en %.2f ms" % reg["lock_tomar_ms"], flush=True)

    ruta_log = os.path.join(AQUI, "log_contenedor_sonda.txt")
    try:
        reg["vram_libre_ini_mib"] = vram()
        cmd = orden(NOMBRE, PUERTO)
        reg["cmd"] = cmd
        print("orden: %s" % " ".join(cmd), flush=True)
        ini = time.perf_counter()
        rc, salida = sh(cmd, tope=120)
        reg["docker_run_rc"] = rc
        reg["docker_run_salida"] = salida.strip()[:400]
        if rc != 0:
            reg["veredicto"] = "docker run falló con rc=%d" % rc
            return

        # Grabadora: el log en continuo, desde el arranque.
        grab = open(ruta_log, "w", encoding="utf-8", errors="replace")
        proc_log = subprocess.Popen(["docker", "logs", "-f", NOMBRE],
                                    stdin=subprocess.DEVNULL, stdout=grab,
                                    stderr=subprocess.STDOUT)

        pico_vram_usada = 0
        estados: list[str] = []
        muerto_en = None
        while True:
            t = time.perf_counter() - ini
            rc_i, est = sh(["docker", "inspect", "-f",
                            "{{.State.Status}}|{{.State.ExitCode}}|{{.State.OOMKilled}}|{{.State.Error}}",
                            NOMBRE], tope=30)
            est = est.strip()
            if not estados or estados[-1].split("  ", 1)[-1] != est:
                estados.append("%6.1fs  %s" % (t, est))
                print("%6.1fs  %s" % (t, est), flush=True)
            libre = vram()
            if libre is not None:
                pico_vram_usada = max(pico_vram_usada, 12288 - libre)
            if est.startswith("exited") or est.startswith("dead"):
                muerto_en = round(t, 1)
                break
            if t > TOPE_S:
                estados.append("%6.1fs  TOPE" % t)
                break
            time.sleep(3.0)

        reg["estados"] = estados
        reg["muerto_en_s"] = muerto_en
        reg["pico_vram_usada_total_mib"] = pico_vram_usada
        try:
            proc_log.terminate()
            proc_log.wait(timeout=15)
        except (OSError, subprocess.SubprocessError):
            pass
        grab.close()

        # El `rc` del contenedor, que es la respuesta (trampa 72).
        _, insp = sh(["docker", "inspect", "-f",
                      "{{.State.Status}}|{{.State.ExitCode}}|{{.State.OOMKilled}}|{{.State.Error}}",
                      NOMBRE], tope=30)
        reg["inspect_final"] = insp.strip()
        if os.path.isfile(ruta_log):
            with open(ruta_log, encoding="utf-8", errors="replace") as fh:
                lineas = fh.read().splitlines()
            reg["log_lineas"] = len(lineas)
            reg["log_cola"] = "\n".join(lineas[-45:])
    finally:
        # `docker rm -f`, nunca `docker kill` (trampa 37). Y siempre: sin --rm,
        # el contenedor NO se va solo.
        rc_rm, sal_rm = sh(["docker", "rm", "-f", NOMBRE], tope=120)
        reg["docker_rm_rc"] = rc_rm
        reg["docker_rm_salida"] = sal_rm.strip()[:200]
        rc_ps, ps = sh(["docker", "ps", "-a", "--format", "{{.Names}}"], tope=60)
        reg["sobrevive"] = NOMBRE in ps
        lock.soltar()
        reg["lock_libre_tras_soltar"] = gpu.esta_libre()
        reg["vram_libre_fin_mib"] = vram()

    with open(os.path.join(AQUI, "resultado_sonda_vllm.json"), "w",
              encoding="utf-8") as fh:
        json.dump(reg, fh, indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in reg.items() if k != "log_cola"},
                     ensure_ascii=False, indent=1))
    print("--- cola del log del contenedor ---")
    print(reg.get("log_cola", "(sin log)"))


if __name__ == "__main__":
    main()

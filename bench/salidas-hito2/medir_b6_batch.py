"""B6 — el lote por la vía REAL: `Servicio.batch`, no un bucle de `convertir`.

`HUECOS.md` §4 dice que el lote sobre una carpeta real es *«el único escenario
donde el 8,39× de HEVC decide algo»*. Se mide con la operación que las cuatro
superficies usan de verdad, que devuelve `job_id` al empezar y corre en un hilo.
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)
from filex import gpu  # noqa: E402
from filex.nucleo import FileX  # noqa: E402
from filex.servicio import COMPLETADO, FALLIDO, Servicio, Trabajos  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(RAIZ, "corpus", "video")


def carpeta_real(destino):
    """Ocho clips de 5 s del corpus, recodificados (no cortados con `-c copy`:
    un corte por copia deja una duración declarada que no es la real y la regla
    A1/V1 del contrato marca `fallo` en la conversión siguiente)."""
    os.makedirs(destino, exist_ok=True)
    fuentes = [("tipico.mp4", 0), ("tipico.mp4", 5), ("tipico.mp4", 10),
               ("tipico.mp4", 15), ("trivial.mp4", 0),
               ("patologico_2pistas.mkv", 0), ("patologico_2pistas.mkv", 5),
               ("fuente_4k.mp4", 0)]
    out = []
    for i, (f, ini) in enumerate(fuentes):
        d = os.path.join(destino, f"clip{i:02d}.mp4")
        if not os.path.exists(d):
            subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-y",
                            "-ss", str(ini), "-i", os.path.join(CORPUS, f),
                            "-t", "5", "-map", "0", "-c:v", "libx264",
                            "-crf", "20", "-preset", "veryfast",
                            "-c:a", "aac", "-b:a", "128k", d],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=900)
        out.append(d)
    return out


def espera(srv, job_id, tope=1800):
    """Sin bucle de reintento ciego: se espera CON TOPE y se devuelve lo visto."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < tope:
        r = srv.job(job_id)
        if r.get("estado") in (COMPLETADO, FALLIDO, "cancelled"):
            return r
        time.sleep(0.1)
    return {"estado": "TOPE_AGOTADO"}


def main():
    tmp = tempfile.mkdtemp(prefix="h2-b6-")
    entradas = carpeta_real(os.path.join(tmp, "entrada"))
    tot = sum(os.path.getsize(e) for e in entradas)
    print(f"carpeta REAL: {len(entradas)} ficheros, {tot} B")
    for e in entradas:
        print(f"  {os.path.basename(e):14s} {os.path.getsize(e):>10} B")

    fx = FileX(raices_lectura=[tmp], raices_escritura=[tmp])
    srv = Servicio(fx, Trabajos(os.path.join(tmp, "trabajos")))
    res = {"n_ficheros": len(entradas), "bytes_entrada": tot, "filas": []}

    with gpu.Lock("H2-B6-batch") as l:
        res["aviso_guardia"] = l.aviso
        for etiqueta, cpu in (("gpu", False), ("cpu", True)):
            ms = []
            ultimo = None
            for k in range(3):
                gpu.olvidar()
                if cpu:
                    gpu._CACHE["hevc_nvenc"] = (False, 0, "forzado a CPU por el arnes")
                else:
                    gpu.capacidad("hevc_nvenc")
                sal = os.path.join(tmp, f"sal_{etiqueta}_{k}")
                os.makedirs(sal, exist_ok=True)
                t0 = time.perf_counter_ns()
                r = srv.batch(entradas, sal, "mkv",
                              {"codec_video": "hevc", "bitrate_video": "2000k"})
                fin = espera(srv, r["job_id"])
                ms.append((time.perf_counter_ns() - t0) / 1e6)
                ultimo = (fin, sal)
                if k < 2:
                    shutil.rmtree(sal, ignore_errors=True)
            fin, sal = ultimo
            det = fin.get("resultado", fin)
            salidas = sorted(glob.glob(os.path.join(sal, "*")))
            pistas = {}
            for s in salidas:
                p = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                    "stream=codec_type,codec_name", "-of",
                                    "csv=p=0", s], stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, timeout=120)
                pistas[os.path.basename(s)] = p.stdout.decode().split()
            fila = {"via": etiqueta, "n": len(ms),
                    "mediana_ms": round(statistics.median(ms), 1),
                    "todas_ms": [round(x, 1) for x in ms],
                    "estado": fin.get("estado"),
                    "convertidos": det.get("convertidos"),
                    "fallidos": det.get("fallidos"),
                    "bytes_salida": sum(os.path.getsize(s) for s in salidas),
                    "pistas": pistas}
            res["filas"].append(fila)
            print(f"\n{etiqueta.upper()}: mediana {fila['mediana_ms']} ms "
                  f"(n=3, {fila['todas_ms']})  estado={fila['estado']} "
                  f"ok={fila['convertidos']} fallos={fila['fallidos']}")
            for k2, v in pistas.items():
                print(f"    {k2:14s} {v}")
    if len(res["filas"]) == 2:
        g = res["filas"][1]["mediana_ms"] / res["filas"][0]["mediana_ms"]
        res["ganancia_lote"] = round(g, 3)
        print(f"\n--> B6 por `Servicio.batch`: GPU x{g:.2f} sobre CPU")
    salida = os.path.join(AQUI, "medicion_b6_batch.json")
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("->", salida)
    print("lock libre:", gpu.esta_libre())
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()

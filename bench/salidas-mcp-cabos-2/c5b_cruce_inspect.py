"""C5b — El punto de cruce exacto entre `inspect` y el staging de R8.

Mide, con dos testigos de ruido (deriva monohilo + lanzamiento de proceso), y en
mediana de n>=9:
  - COPIA al staging (shutil.copyfile): coste del staging de R8, funcion del tamano.
  - INSPECT externo (ffprobe): funcion casi CONSTANTE del tamano (lee cabeceras).
  - INSPECT en proceso (abrir + leer 64 KiB + firma): lo que RESULTADOS-MCP §4 pide.
Con eso acota el cruce COPIA==ffprobe con un numero, y situa el inspect en proceso.

NO usa GPU. Timeouts explicitos. Rutas Windows por barra normal (regla 13/19).
"""
import json
import os
import shutil
import statistics
import subprocess
import time
from pathlib import Path

RAIZ = Path("D:/Work/research/FileX")
SAL = RAIZ / "bench/salidas-mcp-cabos-2"
TRAB = SAL / "c5_trabajo"
STAGING = SAL / "c5_staging"
N = 11  # n>=9; se descarta el primero (calentamiento)

# Ficheros sinteticos para la curva de COPIA (bytes puros: la copia solo depende del tamano)
TAM_MB = [1, 5, 10, 25, 50, 75, 90, 100, 128, 160, 200, 256]

# Ficheros reales para ffprobe (que necesita media valido)
REALES = [
    ("trivial.mp4", RAIZ / "corpus/video/trivial.mp4"),
    ("tipico.mp4", RAIZ / "corpus/video/tipico.mp4"),
    ("patologico_16bit.tif", RAIZ / "corpus/imagen/patologico_16bit.tif"),
    ("fuente_4k.mp4", RAIZ / "corpus/video/fuente_4k.mp4"),
]
FFPROBE = "ffprobe"


def testigo_deriva(reps=200000):
    """Bucle monohilo: detecta DERIVA dentro de la tanda."""
    t0 = time.perf_counter()
    x = 0
    for i in range(reps):
        x += i * i % 7
    return (time.perf_counter() - t0) * 1000, x


def testigo_proceso():
    """Lanzamiento de proceso: detecta NIVEL de carga. Tope 20 s (regla del proyecto)."""
    t0 = time.perf_counter()
    try:
        subprocess.run([FFPROBE, "-v", "quiet", "-version"],
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=20)
    except Exception:
        return 20000.0
    return (time.perf_counter() - t0) * 1000


def medir(fn, n=N):
    ms = []
    for i in range(n):
        t0 = time.perf_counter()
        fn()
        ms.append((time.perf_counter() - t0) * 1000)
    ms = ms[1:]  # descarta calentamiento
    return {"mediana_ms": round(statistics.median(ms), 4),
            "min_ms": round(min(ms), 4), "max_ms": round(max(ms), 4)}


def copia(origen, destino):
    def _():
        shutil.copyfile(origen, destino)
        os.remove(destino)
    return _


def ffprobe_de(ruta):
    def _():
        subprocess.run([FFPROBE, "-v", "quiet", "-show_entries",
                        "format=duration,size", "-of", "json", str(ruta)],
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=30)
    return _


def inspect_en_proceso(ruta):
    def _():
        with open(ruta, "rb") as f:
            cab = f.read(65536)
        # firma minima: primeros bytes (como haria el verificador en proceso)
        _ = cab[:16]
    return _


def main():
    for d in (TRAB, STAGING):
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True, exist_ok=True)

    # Calibracion de testigos en reposo
    dr0, _ = testigo_deriva()
    pr0 = testigo_proceso()

    resultado = {"n": N, "testigos_reposo": {"deriva_ms": round(dr0, 3),
                                             "proceso_ms": round(pr0, 3)},
                 "copia": [], "ffprobe_reales": [], "inspect_proceso_reales": []}

    # --- Curva de COPIA sobre ficheros sinteticos ---
    for mb in TAM_MB:
        origen = TRAB / f"syn_{mb}.bin"
        with open(origen, "wb") as f:
            f.write(os.urandom(1024 * 1024))
            resto = mb - 1
            bloque = os.urandom(1024 * 1024)
            for _ in range(resto):
                f.write(bloque)
        destino = STAGING / f"syn_{mb}.bin"
        dr_a, _ = testigo_deriva(); pr_a = testigo_proceso()
        m = medir(copia(origen, destino))
        dr_b, _ = testigo_deriva(); pr_b = testigo_proceso()
        sucia = (max(dr_a, dr_b) > dr0 * 1.5) or (max(pr_a, pr_b) > pr0 * 1.8)
        m.update({"tam_mb": mb, "bytes": origen.stat().st_size,
                  "mbps": round(mb / (m["mediana_ms"] / 1000), 1),
                  "etiqueta": "SUCIA" if sucia else "limpia",
                  "testigo_proc_ms": round(max(pr_a, pr_b), 1)})
        resultado["copia"].append(m)
        os.remove(origen)
        print(f"[copia] {mb:4d} MB  {m['mediana_ms']:8.3f} ms  {m['mbps']:7.1f} MB/s  {m['etiqueta']}", flush=True)

    # --- ffprobe e inspect-en-proceso sobre ficheros reales ---
    for nombre, ruta in REALES:
        if not ruta.exists():
            continue
        mb = ruta.stat().st_size / (1024 * 1024)
        mf = medir(ffprobe_de(ruta))
        mp = medir(inspect_en_proceso(ruta))
        mf.update({"fichero": nombre, "tam_mb": round(mb, 1)})
        mp.update({"fichero": nombre, "tam_mb": round(mb, 1)})
        resultado["ffprobe_reales"].append(mf)
        resultado["inspect_proceso_reales"].append(mp)
        print(f"[real] {nombre:24s} {mb:7.1f} MB  ffprobe={mf['mediana_ms']:.2f} ms  proceso={mp['mediana_ms']:.4f} ms", flush=True)

    # --- Cruce COPIA == ffprobe (interpolacion sobre la curva de copia) ---
    ff_med = statistics.median([x["mediana_ms"] for x in resultado["ffprobe_reales"]])
    copia_pts = [(x["tam_mb"], x["mediana_ms"]) for x in resultado["copia"]]
    cruce = None
    for (m1, t1), (m2, t2) in zip(copia_pts, copia_pts[1:]):
        if t1 <= ff_med <= t2:
            frac = (ff_med - t1) / (t2 - t1) if t2 != t1 else 0
            cruce = round(m1 + frac * (m2 - m1), 1)
            break
    # velocidad media de copia (MB/s) para extrapolar
    mbps_med = statistics.median([x["mbps"] for x in resultado["copia"] if x["tam_mb"] >= 50])
    resultado["cruce"] = {"ffprobe_mediana_ms": round(ff_med, 2),
                          "copia_mbps_med(>=50MB)": round(mbps_med, 1),
                          "cruce_interpolado_MB": cruce,
                          "cruce_modelo_MB": round(ff_med / 1000 * mbps_med, 1)}
    print("CRUCE:", json.dumps(resultado["cruce"], ensure_ascii=False), flush=True)

    (SAL / "c5b_cruce_inspect.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")

    # limpieza
    shutil.rmtree(TRAB, ignore_errors=True)
    shutil.rmtree(STAGING, ignore_errors=True)


if __name__ == "__main__":
    main()

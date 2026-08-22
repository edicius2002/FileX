"""Cabo 5 (cuarta parte) — el unico caso en que copiar puede costar mas que la operacion.

`inspect` (ffprobe) lee metadatos: no recorre el fichero entero. Si el staging cuesta mas
que la propia operacion, R8 necesita una excepcion explicita para ese camino.
"""

import json
import shutil
import subprocess
import time
from pathlib import Path

RAIZ = Path("D:/Work/research/FileX")
SALIDA = RAIZ / "bench/salidas-mcp-cabos"
TRABAJO = SALIDA / "cabo5_trabajo"
STAGING = SALIDA / "cabo5_staging"
N = 5

CASOS = {
    "trivial.png (316 B)": RAIZ / "corpus/imagen/trivial.png",
    "tipico.mp4 (15,5 MB)": RAIZ / "corpus/video/tipico.mp4",
    "fuente_4k.mp4 (122 MB)": RAIZ / "corpus/video/fuente_4k.mp4",
    "patologico_16bit.tif (72 MB)": RAIZ / "corpus/imagen/patologico_16bit.tif",
}


def mediana(xs):
    return sorted(xs)[len(xs) // 2]


def main():
    TRABAJO.mkdir(parents=True, exist_ok=True)
    STAGING.mkdir(parents=True, exist_ok=True)
    res = {}
    for nombre, orig in CASOS.items():
        ent = TRABAJO / orig.name
        if not ent.exists() or ent.stat().st_size != orig.stat().st_size:
            shutil.copyfile(orig, ent)
        probe, copia = [], []
        for i in range(N):
            t0 = time.time()
            subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams",
                            "-of", "json", str(ent)], capture_output=True, timeout=300)
            probe.append(round((time.time() - t0) * 1000, 1))
            dst = STAGING / f"i_{i}_{ent.name}"
            t0 = time.time()
            shutil.copyfile(ent, dst)
            copia.append(round((time.time() - t0) * 1000, 1))
            dst.unlink(missing_ok=True)
        res[nombre] = {"bytes": ent.stat().st_size,
                       "ms_ffprobe_mediana": mediana(probe),
                       "ms_copia_mediana": mediana(copia),
                       "ffprobe": probe, "copia": copia}
        r = res[nombre]
        rel = (r["ms_copia_mediana"] / r["ms_ffprobe_mediana"]) if r["ms_ffprobe_mediana"] else None
        r["copia_frente_a_inspect"] = round(rel, 2) if rel else None
        print(f"{nombre:30s} {r['bytes']:>12,} B  ffprobe={r['ms_ffprobe_mediana']:>7.1f} ms  "
              f"copia={r['ms_copia_mediana']:>7.1f} ms  copia/inspect = {r['copia_frente_a_inspect']}")
    (SALIDA / "cabo5_inspect.json").write_text(json.dumps(res, ensure_ascii=False, indent=2),
                                               encoding="utf-8")


if __name__ == "__main__":
    main()

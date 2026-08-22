"""¿Sigue en pie la exención de R8/R18 para `inspect` con el `inspect` REAL?

`bench/mcp-cabos-2.md` §5.3 cerró la exención con este número: el `inspect` **en
proceso** cuesta **0,04–0,06 ms** frente a los **1,7–166 ms** del staging que R8
le impondría — «de 30× a más de 3.000× la operación a cambio de cero seguridad».

**Pero aquel 0,04–0,06 ms no midió un `inspect`: midió `abrir + leer 64 KiB de
cabecera`** (`c5b_cruce_inspect.py`). El `inspect` que el hito 4 expone de verdad
es `verificador.sondear_en_proceso`, que además calcula la firma real, parsea la
cabecera del formato y recorre las cajas de un ISOBMFF. Este arnés mide **la
operación que existe**, contra los mismos dos rivales.

    .venv-mcp-filex/Scripts/python.exe bench/salidas-hito4/h4_inspect_r8.py

Escribe `h4_inspect_r8.json`. **Los dos testigos de ruido, siempre** (`CLAUDE.md`
§3): el bucle monohilo mide la DERIVA dentro de la tanda y el lanzamiento de
proceso mide el NIVEL de carga de la máquina — el monohilo solo es ciego a la
contención multinúcleo y ya etiquetó `limpia` una tanda ×6,8. **Y el testigo
lleva su propio tope de 20 s**: un testigo que puede tumbar la medición no es un
testigo.

Con la sesión de escritorio remoto activa **todo sale `SUCIA` por estructura**.
"""

from __future__ import annotations

import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _RAIZ)

from filex import contrato                                        # noqa: E402

N = 15                          # repeticiones por celda; se reporta la MEDIANA
TOPE_TESTIGO = 20.0             # el testigo no puede tumbar la tanda


def _mediana(fn, n=N):
    t = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        t.append((time.perf_counter() - t0) * 1000)
    return statistics.median(t)


def testigo_deriva() -> float:
    """Bucle monohilo. Detecta la DERIVA dentro de la tanda."""
    t0 = time.perf_counter()
    x = 0
    for i in range(400_000):
        x += i * i
    return (time.perf_counter() - t0) * 1000


def testigo_nivel() -> tuple[float, bool]:
    """Lanzamiento de proceso. Detecta el NIVEL de carga de la máquina."""
    t0 = time.perf_counter()
    try:
        subprocess.run(["ffprobe", "-version"], stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=TOPE_TESTIGO, check=False)
    except Exception:
        return TOPE_TESTIGO * 1000, True
    return (time.perf_counter() - t0) * 1000, False


def main() -> int:
    v = contrato.verificador()
    if v is None:
        print("verificador no disponible", file=sys.stderr)
        return 2

    ficheros = [
        ("corpus/imagen/trivial.png", "PNG 64x64"),
        ("corpus/imagen/tipico.png", "PNG 1920x1080"),
        ("corpus/imagen/patologico_16bit.tif", "TIFF 16 bits"),
        ("corpus/video/tipico.mp4", "MP4"),
        ("corpus/pdf/tipico_texto.pdf", "PDF"),
    ]
    ficheros = [(os.path.join(_RAIZ, f), etq) for f, etq in ficheros]
    ficheros = [(f, e) for f, e in ficheros if os.path.isfile(f)]

    d0 = testigo_deriva()
    n0, tope0 = testigo_nivel()

    staging = tempfile.mkdtemp(prefix="h4-staging-")
    filas = []
    try:
        for ruta, etq in ficheros:
            mb = os.path.getsize(ruta) / (1 << 20)

            # calentar: Windows Defender infla el primer acceso (trampa nº 7)
            v.sondear_en_proceso(ruta)
            proceso = _mediana(lambda r=ruta: v.sondear_en_proceso(r))

            destino = os.path.join(staging, os.path.basename(ruta))
            shutil.copyfile(ruta, destino)
            copia = _mediana(lambda r=ruta, d=destino: shutil.copyfile(r, d),
                             n=max(5, N // 3))

            def _ffprobe(r=ruta):
                subprocess.run(
                    ["ffprobe", "-v", "quiet", "-print_format", "json",
                     "-show_format", "-show_streams", r],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, timeout=60, check=False)

            try:
                _ffprobe()
                externo = _mediana(_ffprobe, n=max(5, N // 3))
            except Exception:
                externo = None

            filas.append({
                "fichero": os.path.basename(ruta), "etiqueta": etq,
                "MB": round(mb, 3),
                "inspect_en_proceso_ms": round(proceso, 4),
                "staging_copia_ms": round(copia, 3),
                "inspect_externo_ffprobe_ms": round(externo, 2) if externo else None,
                "staging_sobre_inspect": round(copia / proceso, 1) if proceso else None,
            })
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    d1 = testigo_deriva()
    n1, tope1 = testigo_nivel()
    deriva = d1 / d0 if d0 else 0.0
    sucia = tope0 or tope1 or deriva > 1.25 or max(n0, n1) > 3 * min(n0, n1)

    res = {
        "nota": "sesión de escritorio remoto activa: SUCIA por estructura",
        "n_por_celda": N,
        "testigo_deriva_ms": [round(d0, 1), round(d1, 1), round(deriva, 3)],
        "testigo_nivel_ms": [round(n0, 1), round(n1, 1)],
        "testigo_agotado": bool(tope0 or tope1),
        "etiqueta": "SUCIA" if sucia else "SUCIA (estructural)",
        "filas": filas,
        "referencia_cabo5": {
            "inspect_en_proceso_ms": "0,04-0,06 (abrir + leer 64 KiB)",
            "ffprobe_ms": 57.0,
            "staging_ms": "1,7 (1 MB) a 166 (256 MB)",
        },
    }
    salida = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "h4_inspect_r8.json")
    with open(salida, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)

    print(f"testigos: deriva x{deriva:.2f} · nivel {n0:.0f}->{n1:.0f} ms · {res['etiqueta']}")
    print(f"{'fichero':<26}{'MB':>8}{'inspect ms':>12}{'copia ms':>10}"
          f"{'ffprobe ms':>12}{'copia/insp':>12}")
    for f in filas:
        print(f"{f['fichero']:<26}{f['MB']:>8.2f}{f['inspect_en_proceso_ms']:>12.3f}"
              f"{f['staging_copia_ms']:>10.2f}"
              f"{(f['inspect_externo_ffprobe_ms'] or 0):>12.1f}"
              f"{(f['staging_sobre_inspect'] or 0):>12.1f}")
    print(f"-> {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

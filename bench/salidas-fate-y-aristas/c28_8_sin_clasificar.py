# -*- coding: utf-8 -*-
"""C28 -- los 8 `sin_clasificar` de firmas-cierre.md 4.4: el censo original
(`bench/salidas-firmas/_censo_firmas.py`) truncaba el `stderr` a los ULTIMOS
400 caracteres (`(p.stderr or "")[-400:]`, linea 49). Aqui se reproduce la
MISMA invocacion -- `magick <entrada> -auto-orient <salida>.<formato>`, la
misma semilla `a1.png` (64x48, ruido aleatorio con -seed 11) -- pero
capturando el stderr ENTERO.

Formatos: 8bimwtext, app1jpeg, clip, iptcwtext, jpt, mask, matte, thumbnail.

    D:\\Work\\research\\FileX\\.venv-mcp-filex\\Scripts\\python.exe bench/salidas-fate-y-aristas/c28_8_sin_clasificar.py
"""
from __future__ import annotations

import json
import os
import subprocess

SAL = os.path.dirname(os.path.abspath(__file__))
MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
TIMEOUT = 25

FORMATOS = ["8bimwtext", "app1jpeg", "clip", "iptcwtext", "jpt", "mask",
           "matte", "thumbnail"]


def main():
    tmp = os.path.join(SAL, "tmp8")
    os.makedirs(tmp, exist_ok=True)
    antes = sorted(os.listdir(tmp))

    entrada = os.path.join(tmp, "a1.png")
    p = subprocess.run([MAGICK, "-size", "64x48", "xc:white", "-seed", "11",
                        "+noise", "Random", entrada],
                       stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
    assert p.returncode == 0 and os.path.exists(entrada), p.stderr

    # control: la MISMA invocacion, a .jp2 -- para separar "JP2 no funciona en
    # esta build" de "esta variante de JP2 (jpt) no funciona".
    control_jp2 = os.path.join(tmp, "control.jp2")
    pc = subprocess.run([MAGICK, entrada, "-auto-orient", control_jp2],
                        stdin=subprocess.DEVNULL, capture_output=True, timeout=TIMEOUT)
    control = {"rc": pc.returncode,
              "bytes": os.path.getsize(control_jp2) if os.path.exists(control_jp2) else 0}

    filas = []
    for fmt in FORMATOS:
        sal = os.path.join(tmp, "out." + fmt)
        argv = [MAGICK, entrada, "-auto-orient", sal]
        p = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                           timeout=TIMEOUT)
        # magick puede escribir sal-0.ext / sal-1.ext (multi-frame); se busca
        # cualquier candidato, igual que hacia `_censo_firmas.py::escribe()`.
        cands = [f for f in os.listdir(tmp)
                if f == os.path.basename(sal) or f.startswith("out." + fmt + "-")]
        tam = os.path.getsize(os.path.join(tmp, cands[0])) if cands else 0
        filas.append({
            "formato": fmt, "argv": argv, "rc": p.returncode,
            "bytes": tam, "ficheros_candidatos": cands,
            "stderr_completo": p.stderr.decode("utf-8", "replace").strip(),
        })
        print("%-12s rc=%-3d bytes=%-6d stderr=%r" %
              (fmt, p.returncode, tam, p.stderr.decode("utf-8", "replace").strip()[:100]))

    despues = sorted(os.listdir(tmp))
    resultado = {"entrada": "a1.png (64x48, +noise Random, -seed 11, misma "
                            "receta que _censo_firmas.py::semillas)",
                "control_jp2": control, "desechable_antes": antes,
                "desechable_despues": despues, "filas": filas}
    with open(os.path.join(SAL, "c28_8_resultado.json"), "w", encoding="utf-8") as fh:
        json.dump(resultado, fh, indent=1, ensure_ascii=False)

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    print("\ncontrol .jp2: rc=%d bytes=%d (JP2 SI funciona en general en esta build)"
          % (control["rc"], control["bytes"]))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""C25 -- «la profundidad de los crudos de terceros» (invocacion-aristas.md
§11 pendiente 2, tambien citado en §4.3): todo lo medido alli eran ficheros
`.rgb`/`.bgr`/etc. que escribio el propio ImageMagick Q16-HDRI, a 16 bits
por canal. El pendiente pregunta si la REGLA de recuperacion que ese mismo
informe prescribe -- "deriva la profundidad de bytes ÷ píxeles ... y elige
por RMSE, no por rc=0" (§4.1) -- generaliza a un crudo que otro programa
escribio a 8 bits, o si de verdad "da basura con la misma bandera" como
adivinaba el pendiente.

Metodo: un crudo RGB genuinamente de 8 bits/canal, escrito por FFMPEG (no
ImageMagick -- otra procedencia real, no una simulacion), a partir de un
frame de referencia SINTETICO que se conserva sin comprimir para tener con
que comparar sin la perdida de un códec intermedio:

  1. `ffmpeg -f lavfi -i testsrc2=size=WxH` -> un frame -> PNG de
     referencia (testsrc2 tiene bordes y degradados, no un plano liso: una
     imagen sin variacion no distingue depth=8 de depth=16 por RMSE).
  2. La MISMA referencia, reescrita a `.rgb` crudo de 8 bits/canal
     (`-pix_fmt rgb24`) -- el "crudo de tercero".
  3. La regla candidata: `bytes_totales / (ancho*alto) / 3_canales * 8` da
     los bits/canal declarados por el propio fichero. Se aplica SIN mirar
     el fichero de referencia (no hace trampa): solo bytes y geometria,
     que es la misma informacion que tendria FileX en produccion si el
     usuario declara ancho/alto.
  4. Se lee con ImageMagick en las DOS profundidades del espacio cerrado
     que ya usa el informe (`-depth {8,16}`) y se compara cada una contra
     la referencia por RMSE (`magick compare -metric RMSE`, trampa 5: NO
     SSIM). Gana la que la regla habria elegido; se publican las DOS para
     que se vea el contraste.

    D:\\Work\\research\\FileX\\.venv-mcp-filex\\Scripts\\python.exe bench/salidas-c25-grafos/c25_crudos_terceros.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess

SAL = os.path.dirname(os.path.abspath(__file__))
FFMPEG = r"D:\utils\ffmpeg\bin\ffmpeg.exe"
MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
ANCHO, ALTO = 96, 64
CANALES = 3


def corre(argv, timeout=30):
    p = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr.decode("utf-8", "replace")


def main():
    out = os.path.join(SAL, "out_crudos")
    os.makedirs(out, exist_ok=True)
    ref_png = os.path.join(out, "referencia.png")
    crudo = os.path.join(out, "tercero_8bit.rgb")

    # 1. referencia PNG, generada por ffmpeg (testsrc2: degradados + bordes)
    rc, _, err = corre([FFMPEG, "-nostdin", "-y", "-f", "lavfi", "-i",
                        "testsrc2=size=%dx%d" % (ANCHO, ALTO), "-frames:v", "1", ref_png])
    assert rc == 0 and os.path.getsize(ref_png) > 0, err[-400:]

    # 2. el "crudo de tercero": MISMOS pixeles, reescritos por FFMPEG (no
    #    ImageMagick) a rgb24 -- 8 bits/canal genuinos, no un supuesto.
    rc, _, err = corre([FFMPEG, "-nostdin", "-y", "-i", ref_png, "-f", "rawvideo",
                        "-pix_fmt", "rgb24", crudo])
    assert rc == 0, err[-400:]
    bytes_crudo = os.path.getsize(crudo)

    # 3. la regla candidata, SOLO con bytes y geometria (lo que declararia
    #    el usuario), sin mirar el origen.
    pixeles = ANCHO * ALTO
    bytes_por_pixel = bytes_crudo / pixeles
    bits_canal_derivados = round(bytes_por_pixel / CANALES * 8)
    prediccion = 8 if bits_canal_derivados <= 8 else 16

    # 4. sweep -depth {8,16}, RMSE contra la referencia (trampa 5: no SSIM)
    resultados = {}
    for depth in (8, 16):
        cand = os.path.join(out, "candidato_depth%d.png" % depth)
        rc, _, err = corre([MAGICK, "-size", "%dx%d" % (ANCHO, ALTO), "-depth", str(depth),
                            "rgb:" + crudo, cand])
        ok_lectura = rc == 0 and os.path.exists(cand) and os.path.getsize(cand) > 0
        rmse = None
        if ok_lectura:
            rc2, _, err2 = corre([MAGICK, "compare", "-metric", "RMSE", cand, ref_png,
                                  os.path.join(out, "diff_depth%d.png" % depth)])
            m = re.search(r"\(([\d.]+)\)", err2)
            rmse = float(m.group(1)) if m else None
        resultados[depth] = {"ok_lectura": ok_lectura, "rmse_normalizado": rmse}
        print("depth=%-2d  ok_lectura=%s  rmse=%s" % (depth, ok_lectura, rmse))

    ganador = min((d for d in resultados if resultados[d]["rmse_normalizado"] is not None),
                  key=lambda d: resultados[d]["rmse_normalizado"], default=None)

    salida = {
        "geometria": [ANCHO, ALTO], "canales": CANALES,
        "bytes_crudo": bytes_crudo, "bytes_por_pixel": bytes_por_pixel,
        "bits_canal_derivados_de_bytes_pixel": bits_canal_derivados,
        "prediccion_de_la_regla": prediccion,
        "resultados_por_depth": resultados,
        "ganador_por_rmse": ganador,
        "regla_acierta": ganador == prediccion,
    }
    with open(os.path.join(SAL, "resultado_crudos_terceros.json"), "w", encoding="utf-8") as fh:
        json.dump(salida, fh, indent=1, ensure_ascii=False)

    print("\nbytes/pixel=%.4f -> regla predice %d bits/canal" % (bytes_por_pixel, prediccion))
    print("ganador por RMSE: depth=%s" % ganador)
    print("LA REGLA ACIERTA" if salida["regla_acierta"] else "LA REGLA FALLA")


if __name__ == "__main__":
    main()

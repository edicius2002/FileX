"""Sonda: que clip da un PSNR de luminancia POR DEBAJO del suelo de V8 (10 dB).

Se necesita un caso real de "esto ya no es una recodificacion de la entrada"
para que `test_V8_por_debajo_del_SUELO_es_FALLO_no_aviso` pruebe la rama de
FALLO y no la de aviso. Con `-qp 51` + `boxblur` la salida sigue siendo el
MISMO plano y el PSNR se queda por encima del suelo: la degradacion agresiva no
basta, hace falta OTRA imagen.
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
from filex import verificador as V  # noqa: E402


def ff(args):
    p = subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error"] + args,
                       capture_output=True, timeout=180)
    assert p.returncode == 0, p.stderr.decode("utf-8", "replace")[:400]


d = tempfile.mkdtemp(prefix="filex-sonda-v8-")
base = os.path.join(d, "base.mkv")
ff(["-f", "lavfi", "-i", "testsrc=size=64x48:rate=5", "-frames:v", "5",
    "-c:v", "ffv1", base])

candidatos = {
    "qp51_boxblur": ["-i", base, "-c:v", "libx264", "-qp", "51",
                     "-vf", "boxblur=10:10", "-pix_fmt", "yuv420p"],
    "negro": ["-f", "lavfi", "-i", "color=c=black:size=64x48:rate=5",
              "-frames:v", "5", "-c:v", "ffv1"],
    "blanco": ["-f", "lavfi", "-i", "color=c=white:size=64x48:rate=5",
               "-frames:v", "5", "-c:v", "ffv1"],
    "gris": ["-f", "lavfi", "-i", "color=c=gray:size=64x48:rate=5",
             "-frames:v", "5", "-c:v", "ffv1"],
    "negado": ["-i", base, "-vf", "negate", "-c:v", "ffv1"],
}
print("suelo de V8 = %.1f dB ; umbral = %.1f dB"
      % (V.PSNR_SUELO_VIDEO, V.PSNR_MIN_VIDEO))
for nombre, args in candidatos.items():
    ruta = os.path.join(d, nombre + ".mkv")
    ff(args + [ruta])
    dd, err = V._ffmpeg_psnr(ruta, base)
    y = (dd or {}).get("y")
    veredicto = ("FALLO (bajo el suelo)" if y is not None
                 and y < V.PSNR_SUELO_VIDEO else "aviso o mejor")
    print("%-14s y=%s  -> %s" % (nombre, y, veredicto))

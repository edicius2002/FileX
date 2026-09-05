"""Segunda sonda: que conversion produce `aviso`, `hallazgos` o `sobrantes`."""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from filex.nucleo import FileX

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PNG = os.path.join(RAIZ, "corpus", "imagen", "tipico.png")
ALPHA = os.path.join(RAIZ, "corpus", "imagen", "alpha.png")

fx = FileX()
print("plan a xyzzy:", fx.planificar("x.png", "y.xyzzy").hay,
      fx.planificar("x.png", "y.xyzzy").motivo)
for orig, dst in (("png", "jpg"), ("png", "gif"), ("png", "bmp"), ("png", "pdf")):
    d = fx.planificar("x." + orig, "y." + dst)
    print(orig, dst, "aviso=", repr(d.aviso))

d = tempfile.mkdtemp(prefix="filex-expl-")
for fuente, dst in ((PNG, "salida.jpg"), (ALPHA, "alpha.jpg"),
                    (PNG, "salida.gif"), (PNG, "salida.pdf")):
    if not os.path.exists(fuente):
        print("falta", fuente)
        continue
    conv = fx.convertir(fuente, os.path.join(d, dst), {})
    print("--", os.path.basename(fuente), "->", dst, "ok=", conv.ok,
          "veredicto=", conv.veredicto, "aviso=", repr(conv.aviso),
          "rechazados=", len(conv.rechazados))
    for s in conv.saltos:
        print("     salto", s.arista, "hallazgos=", s.hallazgos,
              "sobrantes=", s.sobrantes)

# fichero corrupto: camino existe, conversion falla
malo = os.path.join(d, "corrupto.png")
with open(malo, "wb") as fh:
    fh.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 40)
conv = fx.convertir(malo, os.path.join(d, "corrupto.webp"), {})
print("corrupto ok=", conv.ok, "motivo=", conv.motivo,
      "camino=", conv.camino.formatos if conv.camino else None,
      "err?", bool(conv.saltos and conv.saltos[0].err))
shutil.rmtree(d, ignore_errors=True)

"""Sonda: V5 empareja las pistas POR POSICION, no por identidad.

`fidelidad_video` compara la etiqueta de la pista `i` de la entrada con la de la
pista `i` de la salida (`y = ts[i] if i < len(ts) else None`). Si el muxer
REORDENA las pistas --y reordenar es el comportamiento por defecto de ffmpeg
cuando no se pasa `-map 0`-- la comparacion cruza una pista con otra.

La sonda construye el caso minimo: un fichero con [audio sin etiquetar, video
etiquetado] y su version REORDENADA a [video etiquetado, audio sin etiquetar],
con las MISMAS etiquetas en las mismas pistas. Ninguna etiqueta se ha perdido.

Control positivo al lado (trampa 128/129: una afirmacion de fallo se publica con
su control): el mismo par SIN reordenar, que tiene que salir limpio.
"""
import json
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


d = tempfile.mkdtemp(prefix="filex-sonda-v5-")
ent = os.path.join(d, "entrada.mkv")          # [0]=audio sin etiqueta, [1]=video spa
ff(["-f", "lavfi", "-i", "testsrc=size=64x48:rate=5",
    "-f", "lavfi", "-i", "anullsrc=r=8000:cl=mono",
    "-map", "1:a", "-map", "0:v", "-t", "1",
    "-c:v", "ffv1", "-c:a", "pcm_s16le",
    "-metadata:s:v:0", "language=spa", "-metadata:s:v:0", "title=Prueba", ent])

igual = os.path.join(d, "mismo_orden.mkv")    # control positivo
ff(["-i", ent, "-map", "0", "-c", "copy", igual])

reord = os.path.join(d, "reordenado.mkv")     # [0]=video spa, [1]=audio
ff(["-i", ent, "-map", "0:v", "-map", "0:a", "-c", "copy", reord])

SONDA = {"categoria": "av", "n_video": 1}
res = {}
for nombre, sal in (("mismo_orden", igual), ("reordenado", reord)):
    etq_e, _ = V._ffprobe_etiquetas(ent)
    etq_s, _ = V._ffprobe_etiquetas(sal)
    h, cob = V.fidelidad_video(sal, ent, {"destino": "mkv"},
                               dict(SONDA), dict(SONDA), {})
    v5 = [x for x in h if x["regla"] == "V5"][0]
    res[nombre] = {"etiquetas_entrada": etq_e, "etiquetas_salida": etq_s,
                   "severidad": v5["severidad"], "mensaje": v5["mensaje"]}
    print("%-13s -> %-12s %s" % (nombre, v5["severidad"], v5["mensaje"][:110]))

# Ninguna etiqueta ha desaparecido en ninguno de los dos: el conjunto de pares
# (language, title) no vacios es el MISMO en entrada y salida.
def _conjunto(lista):
    return sorted((x["language"], x["title"]) for x in lista
                  if x["language"] or x["title"])


for nombre in res:
    a = _conjunto(res[nombre]["etiquetas_entrada"])
    b = _conjunto(res[nombre]["etiquetas_salida"])
    res[nombre]["conjunto_conservado"] = (a == b)
    print("%-13s conjunto de etiquetas conservado: %s" % (nombre, a == b))

print(json.dumps({k: {"severidad": v["severidad"],
                      "conjunto_conservado": v["conjunto_conservado"]}
                  for k, v in res.items()}, indent=1))
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "sonda_v5_orden.json"), "w", encoding="utf-8") as fh:
    json.dump(res, fh, indent=1, ensure_ascii=False)

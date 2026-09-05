"""Sonda: `svg_textos` ignora `transform`, y eso convierte a I9 en un FALSO
POSITIVO sobre una rasterizacion CORRECTA.

`svg_textos` estima la caja del texto con `x`, `y` y `font-size` del elemento y
NO mira ningun `transform`, ni el suyo ni el de sus ancestros. Si el texto vive
dentro de un `<g transform="translate(...)">`, la caja apunta a un sitio donde
el rasterizador no pinto nada -- y `fidelidad_vectorial` dice TEXTO PERDIDO
sobre una salida en la que el texto ESTA.

Dos celdas y un control, todo con el MISMO rasterizador (librsvg 2.40.20 dentro
de ImageMagick, que si honra `transform`):

  A. control positivo: el texto en su posicion absoluta, sin `transform`.
  B. el sujeto: el MISMO texto, en el MISMO sitio de la imagen, colocado con
     `<g transform="translate(...)">`.

Si A sale limpia y B sale FALLO, la diferencia es el `transform` y nada mas.
"""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
from filex import verificador as V  # noqa: E402

CAB = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" '
       'width="200" height="200">'
       '<rect width="200" height="200" fill="white"/>')
TEXTO = '<text x="%s" y="%s" font-size="24" fill="black"%s>HOLA</text>'

d = tempfile.mkdtemp(prefix="filex-sonda-i9-")
casos = {
    # El texto acaba en (110, 120) en los dos casos.
    "A_sin_transform": CAB + (TEXTO % ("110", "120", "")) + "</svg>",
    "B_con_transform": CAB + '<g transform="translate(100,100)">'
                       + (TEXTO % ("10", "20", "")) + "</g></svg>",
}
res = {}
for nombre, cuerpo in casos.items():
    svg = os.path.join(d, nombre + ".svg")
    png = os.path.join(d, nombre + ".png")
    with open(svg, "w", encoding="utf-8") as fh:
        fh.write(cuerpo)
    p = subprocess.run(["magick", "-background", "white", svg,
                        "-alpha", "remove", png],
                       capture_output=True, timeout=120)
    assert p.returncode == 0, p.stderr.decode("utf-8", "replace")[:300]
    tx = V.svg_textos(svg)
    h, cob = V.fidelidad_vectorial(png, svg, {"destino": "png"},
                                   {"ancho": 200, "alto": 200},
                                   {"categoria": "imagen"}, {})
    # Testigo independiente: ¿hay tinta en la imagen entera? Si la hay, el
    # rasterizador SI pinto el texto y el fallo es de la caja, no del motor.
    todo = V.png_tinta_cajas(png, [(0, 0, 200, 200)])
    res[nombre] = {"caja_estimada": tx["cajas"][0]["caja"],
                   "severidad": h[0]["severidad"],
                   "mensaje": h[0]["mensaje"][:90],
                   "tinta_en_la_imagen_entera_pct": todo["cajas"][0]["tinta_pct"]}
    print("%-16s caja=%s  %-11s tinta_total=%.3f %%  %s"
          % (nombre, tx["cajas"][0]["caja"], h[0]["severidad"],
             todo["cajas"][0]["tinta_pct"], h[0]["mensaje"][:60]))

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "sonda_i9_transform.json"), "w", encoding="utf-8") as fh:
    json.dump(res, fh, indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))

# -*- coding: utf-8 -*-
"""G1 — texto y maqueta de `escaneado_d4`. FUENTE UNICA DE VERDAD.

Lo importa el generador (gen_corpus_d4.py) y lo importa el evaluador
(ocr_eval_d4.py). Asi la pagina renderizada y la referencia de medida no pueden
divergir: es literalmente la misma cadena.

Diseño, y por que:
  * CASTELLANO REAL CON TILDES. Ninguna medida de OCR del proyecto las tenia.
    Hay a e i o u acentuadas, ñ/Ñ, ü, ¿ ¡ de apertura, cifras y puntuacion.
  * TRES TAMAÑOS DE LETRA en la misma pagina (24 pt / 11 pt / 7 pt). Esto es lo
    que produce CER INTERMEDIOS por construccion: un motor que detecta pero no
    reconoce se queda con el titular y pierde el cuerpo pequeño, y eso cae en
    mitad de la escala en vez de saltar de 0 a 76 como en d3.
  * REFERENCIA LARGA (≈600 caracteres frente a los 79 de d1-d3). Con 79 chars el
    CER esta cuantizado a 1,27 puntos por caracter; con ~600 el paso es 0,17.
    Sin esto no hay "gradiente" que medir, solo escalones.
"""

# --- maqueta: pagina maestra a 600 ppp (8,333 px por punto tipografico) ---
PPP_MAESTRO = 600
ANCHO = 3882          # 6,47 in  x 600 ppp   (misma proporcion que el resto del corpus)
ALTO = 5376           # 8,96 in  x 600 ppp
MARGEN_X = 320

PX_POR_PT = PPP_MAESTRO / 72.0


def pt(p):
    return int(round(p * PX_POR_PT))


# etiqueta -> (fuente, tamaño_pt, y_inicial_px, interlineado_px, lineas)
MAQUETA = [
    ("titulo", "Arial-Bold", 24, 520, 0, [
        "INFORME DE DIGITALIZACIÓN",
    ]),
    ("subtitulo", "Arial", 13, 760, 0, [
        "Expediente núm. 4.827/2026 - Archivo Histórico",
    ]),
    ("cuerpo", "Arial", 11, 1080, 148, [
        "El día 14 de marzo se recibió la solicitud de análisis",
        "técnico sobre veintiún volúmenes encuadernados en piel.",
        "La comisión determinó que la reproducción fotográfica",
        "debía realizarse con iluminación difusa y sin contacto,",
        "según la norma UNE 15-402, para evitar daños añadidos",
        "en los pliegos más frágiles del año 1893.",
    ]),
    ("pequeña", "Arial", 7, 2180, 98, [
        "¿Quién autorizó la excepción? El párrafo tercero señala",
        "que la revisión ortográfica y lingüística del legajo",
        "es responsabilidad del área de conservación preventiva.",
        "¡Atención! Los códigos 7-B, 9-Ñ y 12-K quedan anulados.",
    ]),
]

BLOQUES = {etq: lineas for etq, _f, _p, _y, _i, lineas in MAQUETA}

REFERENCIA = " ".join(" ".join(v) for v in BLOQUES.values())

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    for etq, f, p, y, i, lineas in MAQUETA:
        print(f"[{etq}] {f} {p} pt = {pt(p)} px maestro "
              f"= {pt(p)/3:.1f} px a 200 ppp   ({len(lineas)} lineas)")
    print(f"referencia: {len(REFERENCIA)} caracteres crudos")

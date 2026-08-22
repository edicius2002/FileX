#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera MANIFIESTO.md con nombre, sha256, tamano y la orden EXACTA que
reproduce cada salida binaria, y despues borra las binarias (el repositorio ya
pago una vez 986 MB de pack, 99,9 % binario).

Los .py, .json y .txt se quedan: son texto barato y son la trazabilidad.
"""
import hashlib
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
REL = "bench/salidas-verificador-gs"

CABECERA = """# MANIFIESTO — `bench/salidas-verificador-gs/`

Salidas del agente **V1 · Verificador y OCR de Ghostscript**
(informe: `bench/verificador-ghostscript.md`).

**Las binarias NO se versionan.** Aquí están su `sha256`, su tamaño y la orden
exacta que las reproduce. Todo se regenera desde este directorio, en este orden:

```
python bench/salidas-verificador-gs/gen_fixtures.py      # TIFF, GIF y PNG Adam7 con magick
python bench/salidas-verificador-gs/gen_predictor.py     # TIFF con Predictor=2, escrito a mano
python bench/salidas-verificador-gs/gen_adam7_4b.py      # PNG de paleta de 2 bits entrelazado
python bench/salidas-verificador-gs/prueba_alfa.py       # contraste contra magick (0 discrepancias)
python bench/salidas-verificador-gs/medir_gs.py cobertura
python bench/salidas-verificador-gs/medir_gs.py reglas
python bench/salidas-verificador-gs/medir_gs.py contrato
python bench/salidas-verificador-gs/medir_gs.py fidelidad
python bench/salidas-verificador-gs/medir_gs.py fallos
python bench/salidas-verificador-gs/discrimina_v2_v5.py
python bench/salidas-verificador-gs/ocr_gs.py sonda
python bench/salidas-verificador-gs/ocr_gs.py cer
python bench/salidas-verificador-gs/ocr_gs.py ppp
python bench/salidas-verificador-gs/ocr_gs.py tiempo
python bench/salidas-verificador-gs/ocr_gs.py reparacion
python bench/salidas-verificador-gs/ocr_gs.py acentos
python bench/salidas-verificador-gs/senal_alucinacion.py
```

**Requisito previo de todo lo de OCR:** el directorio `tessdata/`, que se
reconstruye con tres copias (no hay que descargar nada en esta máquina):

```
copy "C:\\Program Files\\Tesseract-OCR\\tessdata\\eng.traineddata" tessdata\\
copy "C:\\Program Files\\Tesseract-OCR\\tessdata\\osd.traineddata" tessdata\\
copy "C:\\Program Files\\PDFgear\\tessdata\\spa.traineddata"       tessdata\\
```

Y `TESSDATA_PREFIX` apuntando a ese directorio **en el entorno del proceso
hijo**, nunca en la máquina: los scripts lo hacen solos.

---

## Lo que SÍ queda versionado

| Fichero | Qué es |
|---|---|
| `gen_fixtures.py`, `gen_predictor.py`, `gen_adam7_4b.py` | Generadores de los ficheros de prueba |
| `prueba_alfa.py` | Contraste de `min(alfa)` en proceso contra `magick` |
| `medir_gs.py` | Banco de medida (copia adaptada de `medir_fid.py`, que no se toca) |
| `discrimina_v2_v5.py` | Los cuatro fallos fabricados que V2 y V5 deben atrapar |
| `ocr_gs.py` | Banco del OCR embebido de Ghostscript |
| `ocr_eval_tildes.py` | Evaluador de OCR **sensible a las tildes** (copia de `ocr_eval.py`) |
| `senal_alucinacion.py` | La señal que separa texto recuperado de ruido con forma de texto |
| `*.json` | Todos los datos crudos |
| `ocr/*.txt` | El texto que devolvió cada OCR |

---

## Binarias borradas, con su reproducción

"""


def main():
    filas = []
    for sub in ("fixtures", "ocr", "tessdata"):
        d = os.path.join(AQUI, sub)
        if not os.path.isdir(d):
            continue
        for n in sorted(os.listdir(d)):
            ruta = os.path.join(d, n)
            if not os.path.isfile(ruta) or n.endswith(".txt"):
                continue
            b = open(ruta, "rb").read()
            filas.append({"ruta": "%s/%s" % (sub, n), "bytes": len(b),
                          "sha256": hashlib.sha256(b).hexdigest()})

    ordenes = {}
    for f in ("fixtures.json", "fixtures_predictor.json", "fixtures_adam7_4b.json"):
        p = os.path.join(AQUI, f)
        if not os.path.exists(p):
            continue
        for x in json.load(open(p, encoding="utf-8")):
            n = x["nombre"]
            o = x.get("orden")
            ordenes["fixtures/" + n] = (" ".join(o) if isinstance(o, list) else
                                        ("gen_predictor.py" if "pred" in n or "p1" in n
                                         else "gen_adam7_4b.py"))

    lineas = [CABECERA,
              "| Fichero | Bytes | sha256 (12) | Orden que lo reproduce |",
              "|---|---:|---|---|"]
    for x in filas:
        o = ordenes.get(x["ruta"])
        if o is None:
            if x["ruta"].startswith("tessdata/"):
                o = "copia del tessdata del sistema (ver arriba)"
            elif "acentos" in x["ruta"]:
                o = "`ocr_gs.py acentos`"
            elif x["ruta"].startswith("ocr/i1_"):
                o = "`ocr_gs.py reparacion` (cadena I1)"
            elif "pdfocr8" in x["ruta"]:
                o = "`ocr_gs.py tiempo`"
            elif x["ruta"].startswith("ocr/"):
                o = "`ocr_gs.py reparacion`"
            else:
                o = "`gen_adam7_4b.py`"
        o = o.replace("|", "\\|")
        if len(o) > 150:
            o = o[:147] + "..."
        lineas.append("| `%s` | %d | `%s` | `%s` |"
                      % (x["ruta"], x["bytes"], x["sha256"][:12], o))

    tot = sum(x["bytes"] for x in filas)
    lineas.append("")
    lineas.append("**Total borrado: %d ficheros, %.1f MB.**"
                  % (len(filas), tot / 1048576.0))
    with open(os.path.join(AQUI, "MANIFIESTO.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lineas) + "\n")
    json.dump(filas, open(os.path.join(AQUI, "manifiesto.json"), "w",
                          encoding="utf-8"), ensure_ascii=False, indent=1)
    print("MANIFIESTO.md: %d binarias, %.1f MB" % (len(filas), tot / 1048576.0))

    if "--borrar" in sys.argv:
        for x in filas:
            os.remove(os.path.join(AQUI, x["ruta"].replace("/", os.sep)))
        print("borradas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""C28 / paso 5 - LOS 56 QUE «NINGUN MOTOR ESCRIBE», leidos por su `rc`.

El pendiente propone cerrarlos con **el corpus FATE de ffmpeg**. Antes de pedir
~1 GB de descarga —que ademas contamina cualquier medicion concurrente (hay un
error de 7,4x medido) y hay un agente midiendo en GPU— conviene mirar POR QUE
fallo cada uno. El censo guardo el `rc`, y el `rc` **no es una pista: es la
respuesta**, porque los codigos de error de ffmpeg son etiquetas de cuatro
caracteres y dicen exactamente cual de los tres remedios aplica. Es la trampa 25
otra vez: *registra el `rc` de cada celda, es lo unico que separa las dos cosas*.

  AVERROR_ENCODER_NOT_FOUND -> este ffmpeg NO trae el codificador. FATE tampoco
      lo arregla: FATE da ficheros para DECODIFICAR, y el censo necesita una
      muestra ESCRITA con la que medir el marcador.
  AVERROR_EXPERIMENTAL      -> el codificador esta y pide `-strict -2`. Es una
      bandera, no un gigabyte.
  EINVAL / AVERROR_INVALIDDATA -> el codificador esta y la INVOCACION del censo
      no cumplia las restricciones del formato (geometria, tasa, perfil).
  «No 8BIM/APP1/IPTC/color profile data is available» -> no es un formato de
      salida: es un VOLCADO DE METADATOS que solo existe si la ENTRADA lo trae.
      El remedio es una entrada con perfil, no un corpus.

Uso:  python bench/salidas-firmas-cierre/_c28_los56.py
"""
import json
import os
import re
import sys
from collections import Counter

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIRMAS_F1 = os.path.join(RAIZ, "bench", "salidas-firmas")

# rc que devuelve ffmpeg (sin signo, como los guardo el censo) -> que significa
RC_FFMPEG = {
    4294967274: ("EINVAL (-22)",
                 "el codificador ESTA y la invocacion no cumplia las "
                 "restricciones del formato"),
    3165764104: ("AVERROR_ENCODER_NOT_FOUND",
                 "este ffmpeg NO trae el codificador"),
    3561836632: ("AVERROR_EXPERIMENTAL",
                 "el codificador ESTA y pide `-strict -2`"),
    3199971767: ("AVERROR_INVALIDDATA",
                 "el codificador ESTA y la entrada no le vale"),
}
META = re.compile(r"No (8BIM|APP1|IPTC|color profile|EXIF)[^.]* data is available"
                  r"|No color profile available|No IPTC profile available"
                  r"|No APP1 data is available|No 8BIM data is available")


# Un formato se intento con VARIAS modalidades y puede traer varios `rc`. El
# orden importa: «no hay codificador» es decisivo y «argumento invalido» puede
# venir de otra modalidad que ni siquiera era la suya.
PRIORIDAD = [3165764104, 3561836632, 3199971767, 4294967274]


def clasifica(errs):
    """(clase, detalle). `errs` es la lista de cadenas que guardo el censo."""
    texto = " | ".join(errs)
    for rc in PRIORIDAD:
        if ("rc=%d" % rc) in texto:
            return RC_FFMPEG[rc]
    if META.search(texto):
        return "metadato, no formato", (
            "no es un destino de conversion: es un volcado de metadatos que "
            "solo existe si la ENTRADA lo trae")
    if "is not a known file format" in texto or "No plugin to handle output" in texto:
        return "el motor no lo sabe escribir", "el propio motor lo dice"
    if not texto.strip() or re.fullmatch(r"\s*(rc=0)?\s*", texto):
        return "rc=0 y sin fichero", (
            "el motor devolvio 0 y no dejo el fichero que se le pidio "
            "(destino de varios ficheros o directorio)")
    return "sin clasificar", texto[:120]


def main():
    cat = json.load(open(os.path.join(FIRMAS_F1, "categorias.json"),
                         encoding="utf-8"))
    censos = {}
    for nom in ("firmas_censo_local.json", "firmas_censo_contenedor.json"):
        censos[nom] = json.load(open(os.path.join(FIRMAS_F1, nom),
                                     encoding="utf-8"))
    errores = {}
    for d in censos.values():
        for motor, fs in d.items():
            if not isinstance(fs, dict):
                continue
            for f, e in fs.items():
                if isinstance(e, dict) and e.get("estado") == "no_escribible":
                    errores.setdefault(f, []).extend(e.get("errores") or [])

    filas, reparto = [], Counter()
    for fmt, e in sorted(cat.items()):
        if not isinstance(e, dict) or e.get("cat_nuevo") != "0_indeterminado":
            continue
        if (e.get("motivo") or "") != "no se pudo escribir con ningun motor disponible":
            continue
        clase, det = clasifica(errores.get(fmt, []))
        reparto[clase] += 1
        filas.append({"formato": fmt, "clase": clase, "detalle": det})

    remedio = {
        "AVERROR_ENCODER_NOT_FOUND": "otro motor, u otra build de ffmpeg",
        "AVERROR_EXPERIMENTAL": "una bandera: `-strict -2`",
        "EINVAL (-22)": "una invocacion que cumpla las restricciones del formato",
        "AVERROR_INVALIDDATA": "una entrada compatible",
        "metadato, no formato": "una ENTRADA con ese metadato dentro",
        "el motor no lo sabe escribir": "otro motor",
        "rc=0 y sin fichero": "tratar el destino como directorio",
        "sin clasificar": "mirarlo a mano",
    }
    res = {"n": len(filas),
           "reparto": {k: {"n": v, "remedio": remedio.get(k, "?")}
                       for k, v in reparto.most_common()},
           "necesitan_FATE_o_un_motor_nuevo":
               sorted(f["formato"] for f in filas
                      if f["clase"] in ("AVERROR_ENCODER_NOT_FOUND",
                                        "el motor no lo sabe escribir")),
           "filas": filas}
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

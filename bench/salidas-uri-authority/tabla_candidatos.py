"""N37 — tabla de candidatos: qué ATRAPA y qué ROMPE cada forma de tratar la *authority*.

`CLAUDE.md` trampa 51: *antes de elegir un umbral —o aquí, una política—, tabula
qué atrapa y qué rompe en cada valor candidato*. Elegir «la más segura» sin la
tabla compra regresiones con mejor pinta.

Los cuatro candidatos se implementan aquí como funciones puras y se evalúan
contra la MISMA batería, que mezcla a propósito tres clases de entrada:

  * las que hoy producen la fuga (`file://servidor/...`),
  * las legítimas que un candidato demasiado severo rompería
    (`file://localhost/...`, que RFC 8089 §2 declara EQUIVALENTE a la authority
    vacía),
  * y las que ya estaban bien, para comprobar que ningún candidato las mueve.

Se mide además QUÉ CONCEDE cada raíz resultante, no sólo qué cadena sale
(trampa 70: seguir el valor hasta donde se usa).
"""

from __future__ import annotations

import json
import os
import sys
from urllib.parse import unquote, urlparse

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import confinamiento as _conf  # noqa: E402

#: RFC 8089 §2: «file://localhost/p» es equivalente a «file:///p». Node lo
#: normaliza solo (`new URL(...).host` da ""), Python NO (`urlparse` da
#: "localhost") — MEDIDO en `productores_node.json` y `productores_py.json`.
AUTHORITY_VACIA = ("", "localhost")


def _base(uri: str):
    """El tronco común: devuelve (netloc, ruta_del_path) o None si no es file://."""
    if not uri.startswith("file://"):
        return None
    p = urlparse(uri)
    return p.netloc, unquote(p.path)


def _recorta_unidad(ruta: str) -> str:
    if os.name == "nt" and len(ruta) > 2 and ruta[0] == "/" and ruta[2] == ":":
        return ruta[1:]
    return ruta


# ------------------------------------------------------------- C1: hoy
def c1_ignorar(uri: str) -> str:
    """El código de HOY: usa `p.path` y tira `p.netloc` al suelo."""
    b = _base(uri)
    if b is None:
        return ""
    _netloc, ruta = b
    return os.path.normpath(_recorta_unidad(ruta))


# --------------------------------------------- C2: rechazar toda authority
def c2_rechazar_todo(uri: str) -> str:
    b = _base(uri)
    if b is None:
        return ""
    netloc, ruta = b
    if netloc:
        return ""
    return os.path.normpath(_recorta_unidad(ruta))


# ------------------------ C3: rechazar salvo la authority que RFC 8089 iguala
def c3_rechazar_salvo_localhost(uri: str) -> str:
    b = _base(uri)
    if b is None:
        return ""
    netloc, ruta = b
    if netloc.lower() not in AUTHORITY_VACIA:
        return ""
    ruta = _recorta_unidad(ruta)
    if not ruta:
        return ""          # `file://` y `file://localhost` no nombran ninguna ruta
    return os.path.normpath(ruta)


# ---------------------------------------------------- C4: traducir a UNC
def c4_traducir_unc(uri: str) -> str:
    b = _base(uri)
    if b is None:
        return ""
    netloc, ruta = b
    if netloc.lower() in AUTHORITY_VACIA:
        ruta = _recorta_unidad(ruta)
        if not ruta:
            return ""
        return os.path.normpath(ruta)
    if os.name != "nt":
        return ""          # fuera de Windows una UNC no significa nada
    if not ruta or ruta == "/":
        return ""          # `file://servidor` sin recurso no confina nada
    return os.path.normpath("\\\\" + netloc + ruta.replace("/", "\\"))


CANDIDATOS = [
    ("C1 ignorar (HOY)", c1_ignorar),
    ("C2 rechazar toda authority", c2_rechazar_todo),
    ("C3 rechazar salvo localhost", c3_rechazar_salvo_localhost),
    ("C4 traducir a UNC", c4_traducir_unc),
]

#: (uri, clase, qué se espera de un candidato correcto)
BATERIA = [
    ("file:///D:/Work/research/FileX", "legitimo_local",
     "tiene que seguir concediendo D:\\Work\\research\\FileX"),
    ("file:///C:/Users/krato", "legitimo_local", "ídem en otra unidad"),
    ("file://localhost/D:/Work", "legitimo_rfc8089",
     "RFC 8089 §2: idéntico a file:///D:/Work"),
    ("file://LOCALHOST/D:/Work", "legitimo_rfc8089", "y sin distinguir mayúsculas"),
    ("file://servidor/recurso", "fuga_n37", "NO puede confinar en una ruta local"),
    ("file://servidor/recurso/sub", "fuga_n37", "ídem"),
    ("file://nas-de-la-empresa/Work", "fuga_n37",
     "el caso caro: hoy concede D:\\Work entero"),
    ("file:///recurso", "sin_unidad", "path absoluto sin unidad: hoy cae en D:\\recurso"),
    ("file://", "cwd", "hoy normpath('') da '.' y confina en el cwd del servidor"),
    ("file:///", "raiz_unidad", "N35 ya lo poda"),
    ("file:///D:/", "raiz_unidad", "N35 ya lo poda"),
    ("http://servidor/x", "no_file", "se ignora, y debe seguir ignorándose"),
    ("", "no_file", "ídem"),
]

#: Objetivos sobre los que se mide QUÉ CONCEDE la raíz resultante.
OBJETIVOS = [
    "D:\\Work\\research\\FileX\\CLAUDE.md",
    "D:\\Work\\research\\ASR",
    "D:\\Work",
    "C:\\Users\\krato",
    "D:\\recurso\\secreto.txt",
    "\\\\servidor\\recurso\\dato.txt",
]


def _evalua(p: str) -> dict:
    """Qué hace el resto del sistema con la ruta que el candidato devolvió."""
    if not p:
        return {"raiz": None, "estado": "ignorada", "concede": []}
    try:
        c = _conf.Confinamiento([p])
    except ValueError:
        return {"raiz": _conf._norm(os.path.abspath(p)),
                "estado": "podada_por_N35_sin_acceso", "concede": []}
    concede = [o for o in OBJETIVOS if c._dentro(os.path.abspath(o), c.lectura)]
    return {"raiz": c.lectura[0], "estado": "confina", "concede": concede}


def main() -> int:
    filas = []
    for uri, clase, espera in BATERIA:
        fila = {"uri": uri, "clase": clase, "se_espera": espera, "por_candidato": {}}
        for nombre, fn in CANDIDATOS:
            p = fn(uri)
            fila["por_candidato"][nombre] = {"devuelve": p, **_evalua(p)}
        filas.append(fila)

    # --- Resumen: por candidato, qué atrapa y qué rompe.
    resumen = {}
    for nombre, _fn in CANDIDATOS:
        atrapa = rompe = intactas = 0
        detalle_rompe = []
        for f in filas:
            r = f["por_candidato"][nombre]
            concede_local = [c for c in r["concede"] if not c.startswith("\\\\")]
            if f["clase"] == "fuga_n37":
                # Atrapada = no confina en ninguna ruta LOCAL inventada.
                if not concede_local:
                    atrapa += 1
                else:
                    detalle_rompe.append("%s sigue concediendo %s" % (f["uri"], concede_local))
            elif f["clase"] in ("legitimo_local", "legitimo_rfc8089"):
                if r["estado"] == "confina" and r["concede"]:
                    intactas += 1
                else:
                    rompe += 1
                    detalle_rompe.append("%s (%s) deja de conceder" % (f["uri"], f["clase"]))
            elif f["clase"] in ("cwd", "sin_unidad"):
                if not concede_local and r["estado"] != "confina":
                    atrapa += 1
                elif r["estado"] == "confina":
                    detalle_rompe.append("%s sigue confinando en %s" % (f["uri"], r["raiz"]))
        resumen[nombre] = {
            "fugas_atrapadas_de_3": atrapa if True else atrapa,
            "legitimas_intactas_de_4": intactas,
            "legitimas_rotas": rompe,
            "detalle": detalle_rompe,
        }

    # --- ¿Es siquiera confinable una raíz UNC? (decide si C4 es escribible)
    unc = "\\\\servidor\\recurso"
    a = _conf._norm(os.path.abspath(unc))
    control_unc = {
        "raiz_del_recurso": unc,
        "norm": a,
        "dirname_igual_a_si_misma": os.path.dirname(a) == a,
        "la_poda_de_N35_se_la_lleva": not _conf.Confinamiento._preparar([unc]),
        "un_subdirectorio_si_confina": bool(
            _conf.Confinamiento._preparar([unc + "\\sub"])),
    }

    print(json.dumps({
        "nota": "trampa 51: la tabla de qué atrapa y qué rompe cada candidato",
        "python": sys.version.split()[0],
        "cwd": os.getcwd(),
        "control_unc": control_unc,
        "resumen": resumen,
        "filas": filas,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

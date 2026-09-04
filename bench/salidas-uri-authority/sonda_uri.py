"""N37 — sonda de `_uri_a_ruta`: sus RAMAS y a dónde va el valor.

Dos disciplinas del proyecto, aplicadas a la vez:

* **Trampa 118** — `_uri_a_ruta` y `_dentro` son predicados con ramas. Se
  enumeran las ramas y se prueba un caso de CADA una, no una muestra cómoda.
* **Trampa 70** — el daño de una traducción equivocada no aparece donde se
  mira: hay que seguir el valor hasta donde se USA. Aquí el valor sigue hasta
  `Confinamiento` y `_dentro`, que es quien concede o deniega.

No modifica nada: importa el módulo tal cual está en el árbol y lo interroga.
`inspect.getsource` deja escrito QUÉ código se midió (trampa 119: el control
de identidad no es el mandato de git, es preguntarle al sujeto).
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import confinamiento as _conf  # noqa: E402
from filex import mcp as _mcp  # noqa: E402


#: Un caso por RAMA de `_uri_a_ruta`, más los casos que la decisión necesita.
#: `rama` nombra por cuál de las tres pasa; `porque` dice qué se mira.
CASOS = [
    # -- rama 1: no empieza por `file://` -> "" (se ignora)
    ("", "R1 no-file", "cadena vacía: ni siquiera es un URI"),
    ("http://servidor/recurso", "R1 no-file", "esquema ajeno"),
    ("D:/Work", "R1 no-file", "ruta pelada, sin esquema"),
    # -- rama 2: nt + /X: -> se quita la barra inicial (letra de unidad)
    ("file:///D:/Work/research/FileX", "R2 letra-unidad", "el caso canónico local"),
    ("file:///C:/Users/krato/Escritorio%20de%20prueba", "R2 letra-unidad",
     "con %20: el unquote va antes del recorte"),
    ("file:///D:/", "R2 letra-unidad", "raíz de unidad: la poda de N35 la espera"),
    # -- rama 3: nt pero NO letra de unidad -> normpath directo, netloc perdido
    ("file://servidor/recurso", "R3 sin-letra", "UNC canónico de RFC 8089: la fila N37"),
    ("file://servidor/recurso/sub", "R3 sin-letra", "UNC con subdirectorio"),
    ("file://localhost/D:/Work", "R3 sin-letra",
     "RFC 8089 §2: `localhost` es EQUIVALENTE a authority vacía"),
    ("file://LOCALHOST/D:/Work", "R3 sin-letra", "y su authority no distingue mayúsculas"),
    ("file://///servidor/recurso", "R3 sin-letra", "barras de más"),
    ("file:///", "R3 sin-letra", "sólo la barra"),
    ("file://", "R3 sin-letra", "authority vacía y sin path: ¿qué da normpath('')?"),
    ("file:///recurso", "R3 sin-letra", "path absoluto POSIX sin unidad"),
]


def _rama_real(uri: str) -> str:
    """Reproduce la decisión de rama del código, para que el nombre no mienta."""
    if not uri.startswith("file://"):
        return "R1 no-file"
    from urllib.parse import unquote, urlparse
    ruta = unquote(urlparse(uri).path)
    if os.name == "nt" and len(ruta) > 2 and ruta[0] == "/" and ruta[2] == ":":
        return "R2 letra-unidad"
    return "R3 sin-letra"


def _netloc(uri: str) -> str:
    from urllib.parse import urlparse
    try:
        return urlparse(uri).netloc
    except Exception:
        return "<urlparse falla>"


def _sigue_el_valor(p: str) -> dict:
    """Trampa 70: qué hace el resto del sistema con lo que devolvió la traducción.

    `p` es lo que `_uri_a_ruta` entregó. `asegurar()` lo mete en `cliente` si es
    truthy, y de ahí va a `_interseca` -> `Confinamiento` -> `_dentro`.
    """
    d: dict = {"lo_toma_asegurar": bool(p)}
    if not p:
        return d
    d["abspath"] = os.path.abspath(p)
    d["norm"] = _conf._norm(os.path.abspath(p))
    # ¿La poda de N35 se la lleva? (`dirname(a) == a` -> raíz de unidad o de UNC)
    preparadas = _conf.Confinamiento._preparar([p])
    d["sobrevive_a_la_poda_de_N35"] = bool(preparadas)
    d["tras_preparar"] = preparadas
    if preparadas:
        try:
            c = _conf.Confinamiento([p])
            d["confinamiento_construye"] = True
            # Las tres ramas de `_dentro`, sobre la raíz resultante:
            r = c.lectura[0]
            d["dentro_de_la_propia_raiz"] = c._dentro(r, c.lectura)          # rama `c == r`
            d["dentro_de_un_hijo"] = c._dentro(os.path.join(r, "x"), c.lectura)  # rama startswith
            d["dentro_de_un_extraño"] = c._dentro("Z:\\nada", c.lectura)     # rama ninguna
        except ValueError as e:
            d["confinamiento_construye"] = False
            d["error"] = str(e)
    else:
        d["confinamiento_construye"] = False
        d["error"] = "podado por N35: no queda ninguna raíz (R6)"
    return d


def main() -> int:
    fuente = inspect.getsource(_mcp._uri_a_ruta)
    filas = []
    for uri, rama_declarada, porque in CASOS:
        p = _mcp._uri_a_ruta(uri)
        rama = _rama_real(uri)
        fila = {
            "uri": uri,
            "rama": rama,
            "rama_declarada_coincide": rama == rama_declarada,
            "porque": porque,
            "authority_netloc": _netloc(uri),
            "devuelve": p,
            "authority_perdida": bool(_netloc(uri)) and _netloc(uri).lower() not in (p or "").lower(),
        }
        fila["destino"] = _sigue_el_valor(p)
        filas.append(fila)

    ramas = sorted({f["rama"] for f in filas})
    salida = {
        "control_de_identidad": {
            "sha256_de_uri_a_ruta": hashlib.sha256(fuente.encode()).hexdigest()[:16],
            "lineas": len(fuente.splitlines()),
            "cwd": os.getcwd(),
            "python": sys.version.split()[0],
            "os_name": os.name,
        },
        "ramas_cubiertas": ramas,
        "ramas_esperadas": ["R1 no-file", "R2 letra-unidad", "R3 sin-letra"],
        "todas_las_ramas_cubiertas": ramas == ["R1 no-file", "R2 letra-unidad", "R3 sin-letra"],
        "filas": filas,
    }
    print(json.dumps(salida, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

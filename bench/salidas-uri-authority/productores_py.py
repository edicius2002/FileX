"""N37 — qué forma de `file://` emite/acepta el otro runtime de cliente: Python.

Complementa `productores_node.js`. Node es el runtime de Claude Code; Python es
el de cualquier cliente MCP escrito con el SDK oficial de Python, que es el que
usa el propio FileX. La decisión de N37 —rechazar la *authority* o traducirla a
UNC— depende de qué emiten los dos, no de lo que RFC 8089 permita.

Va en fichero por la TRAMPA 19 (el shell se come los backslashes).
"""

import json
import sys
from pathlib import Path, PureWindowsPath
from urllib.parse import urlparse
from urllib.request import pathname2url, url2pathname

CASOS = [
    ("local", "D:\\Work\\research\\FileX"),
    ("unc", "\\\\servidor\\recurso"),
    ("unc_sub", "\\\\servidor\\recurso\\sub"),
    ("raiz_unidad", "D:\\"),
]

CONSUMO = [
    "file://servidor/recurso",
    "file:///recurso",
    "file://localhost/D:/Work",
    "file:///D:/Work",
    "file://",
    "file:///",
]


def main() -> int:
    produccion = []
    for nombre, ruta in CASOS:
        fila = {"caso": nombre, "ruta_de_entrada": ruta}
        try:
            u = Path(ruta).as_uri()
            fila["as_uri"] = u
            fila["authority_emitida"] = urlparse(u).netloc
        except Exception as e:
            fila["as_uri"] = None
            fila["error_as_uri"] = "%s: %s" % (type(e).__name__, e)
            fila["authority_emitida"] = None
        try:
            fila["pathname2url"] = pathname2url(ruta)
        except Exception as e:
            fila["pathname2url"] = "%s: %s" % (type(e).__name__, e)
        produccion.append(fila)

    consumo = []
    for u in CONSUMO:
        p = urlparse(u)
        fila = {"uri": u, "netloc_de_urlparse": p.netloc, "path_de_urlparse": p.path}
        try:
            fila["url2pathname"] = url2pathname(p.path)
        except Exception as e:
            fila["url2pathname"] = "%s: %s" % (type(e).__name__, e)
        # Lo que haría un consumidor que SÍ mirase la authority, para tenerlo al lado:
        fila["unc_reconstruida"] = ("\\\\" + p.netloc + p.path.replace("/", "\\")
                                    if p.netloc else None)
        consumo.append(fila)

    print(json.dumps({
        "runtime": "python " + sys.version.split()[0],
        "plataforma": sys.platform,
        "produccion": produccion,
        "consumo": consumo,
        # Control: ¿PureWindowsPath reconoce la UNC reconstruida como UNC?
        "control_unc": {
            "drive_de_\\\\servidor\\recurso": PureWindowsPath("\\\\servidor\\recurso").drive,
            "es_absoluta": PureWindowsPath("\\\\servidor\\recurso").is_absolute(),
        },
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

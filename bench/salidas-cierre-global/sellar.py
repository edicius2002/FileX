"""Sella los cinco sondeos a partir del resondeo real del cierre global.

El script no ejecuta conversiones: consume únicamente los tres registros
crudos producidos por los arneses versionados y se niega a escribir si cambia
el conjunto exacto de 172 aristas, el build o un caso documental no fue real.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import sys
import tempfile
import time


RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from filex import huella  # noqa: E402
from filex.motor_contenedor import (  # noqa: E402
    CalibreEnContenedor,
    LibreOfficeEnContenedor,
    PandocEnContenedor,
)


ESPERADAS = {
    "ffmpeg": 70,
    "imagemagick": 62,
    "doc_libreoffice": 16,
    "doc_pandoc": 16,
    "doc_calibre": 8,
}
CLASES_DOC = {
    "doc_libreoffice": LibreOfficeEnContenedor,
    "doc_pandoc": PandocEnContenedor,
    "doc_calibre": CalibreEnContenedor,
}
INFORME = "bench/cierre-global.md"


def _leer(ruta: Path) -> dict:
    with ruta.open(encoding="utf-8") as f:
        dato = json.load(f)
    if not isinstance(dato, dict):
        raise ValueError(f"{ruta}: la raíz no es un objeto")
    return dato


def _tabla_ffmpeg(crudo: dict) -> dict:
    tabla = {}
    for clave, caso in sorted((crudo.get("aristas") or {}).items()):
        estado = caso.get("estado")
        if estado not in ("real", "nominal"):
            raise ValueError(f"ffmpeg:{clave}: estado ausente o inválido")
        entrada = {"estado": estado}
        if estado == "real":
            if caso.get("rc") != 0 or caso.get("veredicto") == "fallo":
                raise ValueError(f"ffmpeg:{clave}: se declaró real sin pasar")
            entrada["ms"] = caso.get("ms")
        else:
            entrada["motivo"] = (caso.get("motivo") or "conversión rechazada")[:500]
        tabla[clave] = entrada
    return tabla


def _tabla_imagemagick(reducido: dict) -> dict:
    tabla = reducido.get("aristas") or {}
    for clave, caso in tabla.items():
        if caso.get("estado") not in ("real", "nominal"):
            raise ValueError(f"imagemagick:{clave}: estado ausente o inválido")
    return dict(sorted(tabla.items()))


def _tablas_documentales(crudo: dict) -> dict[str, dict]:
    por = defaultdict(dict)
    for caso in crudo.get("casos") or []:
        clave = (caso.get("origen"), caso.get("destino"))
        por[caso.get("motor")][clave] = caso

    tablas = {}
    for motor, cls in CLASES_DOC.items():
        tabla = {}
        for origen, destino in sorted(cls._DECLARADAS):
            caso = por[motor].get((origen, destino))
            if caso is None:
                raise ValueError(f"falta {motor}:{origen}>{destino}")
            if caso.get("rc") != 0 or caso.get("contrato") == "fallo":
                raise ValueError(
                    f"{motor}:{origen}>{destino} no pasó: "
                    f"rc={caso.get('rc')} contrato={caso.get('contrato')}"
                )
            motivo = (
                f"{caso.get('bytes')} B, {caso.get('caracteres')} caracteres, "
                f"contrato {caso.get('contrato')}"
            )
            if caso.get("rasteriza_medido") == "si":
                motivo += "; rasteriza según el centinela de texto"
            elif caso.get("rasteriza_medido") == "ciego":
                motivo += "; sonda de texto ciega para este contenedor"
            tabla[f"{origen}>{destino}"] = {
                "estado": "real",
                "ms": caso.get("ms"),
                "motivo": motivo,
                "caso": caso.get("id"),
            }
        tablas[motor] = tabla
    return tablas


def _validar_claves(motor: str, tabla: dict, destino: Path) -> dict:
    viejo = _leer(destino)
    anteriores = set((viejo.get("aristas") or {}).keys())
    actuales = set(tabla.keys())
    if actuales != anteriores:
        faltan = sorted(anteriores - actuales)
        sobran = sorted(actuales - anteriores)
        raise ValueError(f"{motor}: claves distintas; faltan={faltan}, sobran={sobran}")
    if len(tabla) != ESPERADAS[motor]:
        raise ValueError(f"{motor}: {len(tabla)} aristas, se esperaban {ESPERADAS[motor]}")
    return viejo


def _escribir(destino: Path, documento: dict) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", delete=False,
        dir=destino.parent, prefix=destino.name + ".", suffix=".tmp",
    ) as f:
        temporal = Path(f.name)
        json.dump(documento, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(temporal, destino)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ffmpeg", type=Path, required=True)
    ap.add_argument("--imagemagick", type=Path, required=True)
    ap.add_argument("--documentos", type=Path, required=True)
    a = ap.parse_args()

    ffmpeg = _leer(a.ffmpeg)
    imagemagick = _leer(a.imagemagick)
    documentos = _leer(a.documentos)
    tablas = {
        "ffmpeg": _tabla_ffmpeg(ffmpeg),
        "imagemagick": _tabla_imagemagick(imagemagick),
        **_tablas_documentales(documentos),
    }
    builds = {
        "ffmpeg": ffmpeg.get("build"),
        "imagemagick": imagemagick.get("build"),
        **(documentos.get("builds") or {}),
    }

    anteriores = {}
    dir_sondeo = RAIZ / "filex" / "sondeo"
    for motor, tabla in tablas.items():
        anteriores[motor] = _validar_claves(motor, tabla, dir_sondeo / f"{motor}.json")
        if builds[motor] != anteriores[motor].get("build"):
            raise ValueError(
                f"{motor}: build medido {builds[motor]!r} != sellado "
                f"{anteriores[motor].get('build')!r}"
            )

    fecha = time.strftime("%Y-%m-%d")
    for motor, tabla in tablas.items():
        huella.olvidar()
        documento = {
            "motor": motor,
            "build": builds[motor],
            "fecha": fecha,
            "informe": INFORME,
            "huella": huella.de_motor_por_nombre(motor),
            "interprete": huella.interprete_actual(),
            "nota_huella": (
                f"RESONDEADO de verdad el {fecha} durante el cierre global tras "
                "corregir CR-002: cada arista pasó por FileX.convertir() y el "
                "contrato completo; no se copió ni reselló la tabla anterior."
            ),
            "aristas": tabla,
        }
        _escribir(dir_sondeo / f"{motor}.json", documento)
        reales = sum(x["estado"] == "real" for x in tabla.values())
        print(f"{motor}: {len(tabla)} aristas, {reales} reales, "
              f"{len(tabla) - reales} nominales")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

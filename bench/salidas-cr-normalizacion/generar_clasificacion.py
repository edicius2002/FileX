#!/usr/bin/env python3
"""Genera y verifica la clasificacion normalizada de CR-007.

La unidad es (motor, token). La clase del objeto se mantiene separada del estado
experimental: ``no_materializable`` historico no significa ``no es un fichero``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SALIDA_RELATIVA = Path("bench/salidas-cr-normalizacion/clasificacion.json")
FUENTES = (
    Path("bench/salidas-aristas/semi_entrada.json"),
    Path("bench/salidas-aristas-reclasificacion/clasificacion.json"),
    Path("bench/salidas-aristas-reclasificacion/crudo/ff-demuxers.txt"),
    Path("bench/salidas-aristas-reclasificacion/crudo/ff-muxers.txt"),
    Path("bench/salidas-aristas-reclasificacion/crudo/im-format.txt"),
    Path("bench/salidas-aristas-escribibles/recuento50.json"),
    Path("bench/salidas-aristas-escribibles/lectura.json"),
    Path("bench/salidas-invocacion/crudos_p2.json"),
    Path("bench/salidas-fate-y-aristas/c28_8_resultado.json"),
    Path("bench/salidas-fate-y-aristas/c16_semi_entrada_fate_resultado.json"),
    Path("bench/salidas-fate-completo/c16_alias_fate_resultado.json"),
    Path("bench/salidas-fate-completo/c16_alias_fate_imagemagick_resultado.json"),
    Path("filex/formatos.py"),
)
CLASES = (
    "ficheros_materializables",
    "crudos_requieren_parametros",
    "protocolos",
    "metadatos",
    "directorios_paquetes",
    "alias",
    "retirados_no_aplicables",
)
PRIORIDAD = (
    "retirados_no_aplicables",
    "crudos_requieren_parametros",
    "protocolos",
    "metadatos",
    "directorios_paquetes",
    "alias",
    "ficheros_materializables",
)
PROTOCOLOS = {"ffmpeg|rtsp", "ffmpeg|sap"}
DIRECTORIOS_PAQUETES = {"ffmpeg|hls", "ffmpeg|dash", "ffmpeg|rtp"}
METADATOS = {"imagemagick|clip", "imagemagick|mask"}
ALIAS_PRODUCTO = {"jpeg": "jpg", "tiff": "tif", "htm": "html", "markdown": "md"}


def cargar_json(raiz: Path, relativa: Path) -> Any:
    return json.loads((raiz / relativa).read_text(encoding="utf-8"))


def sha256(ruta: Path) -> str:
    resumen = hashlib.sha256()
    with ruta.open("rb") as fichero:
        for bloque in iter(lambda: fichero.read(1024 * 1024), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def catalogo_ffmpeg(ruta: Path) -> tuple[set[str], dict[str, str]]:
    nombres: set[str] = set()
    alias: dict[str, str] = {}
    patron = re.compile(r"^\s*[D ]E?\s+([^\s]+)\s+")
    for linea in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
        coincidencia = patron.match(linea)
        if not coincidencia:
            continue
        grupo = coincidencia.group(1).lower().split(",")
        nombres.update(grupo)
        for secundario in grupo[1:]:
            alias[secundario] = grupo[0]
    return nombres, alias


def modulos_imagemagick(ruta: Path) -> dict[str, str]:
    modulos: dict[str, str] = {}
    patron = re.compile(r"^\s*([A-Z0-9+-]+)\*?\s+([A-Z0-9+-]+)\s+[r-][w-][+-]\s+")
    for linea in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
        coincidencia = patron.match(linea)
        if coincidencia:
            modulos[coincidencia.group(1).lower()] = coincidencia.group(2).lower()
    return modulos


def roles_ffmpeg(
    token: str,
    clase_c49: str | None,
    demuxers: set[str],
    muxers: set[str],
    alias_demuxer: dict[str, str],
) -> list[str]:
    roles = []
    if token in demuxers:
        roles.append("demuxer")
    if token in muxers:
        roles.append("muxer")
    if clase_c49 == "ff_extension_de_demuxer" or token in alias_demuxer:
        roles.append("extension")
    if not roles:
        roles.append("extension_o_token_catalogo_sin_identidad_resuelta")
    return roles


def decidir_clase(
    clave: str,
    clasificacion_c49: dict[str, Any],
    retirados_c50: set[str],
    crudos: set[str],
    alias_demuxer: dict[str, str],
) -> tuple[str, str]:
    motor, token = clave.split("|", 1)
    dato_c49 = clasificacion_c49.get(clave)
    if dato_c49 and dato_c49["mueve"]:
        bases_c49 = {
            "no_aplica_generador": "C49: generador, no fichero",
            "no_aplica_protocolo": "C49: URL, no fichero",
            "no_aplica_dispositivo": "C49: dispositivo, no fichero",
        }
        return "retirados_no_aplicables", bases_c49[dato_c49["clase"]]
    if clave in retirados_c50:
        return "retirados_no_aplicables", "C50: dispositivo confirmado"
    if clave in crudos:
        return "crudos_requieren_parametros", "P2: crudo medido con geometria/profundidad explicita"
    if clave in PROTOCOLOS:
        return "protocolos", "CR-007: sesion/URL de protocolo, no fichero aislado"
    if clave in METADATOS:
        return "metadatos", "C28: canal o perfil requerido en la entrada"
    if clave in DIRECTORIOS_PAQUETES:
        return "directorios_paquetes", "CR-007: manifiesto y recursos/contexto asociados"
    if motor == "ffmpeg" and token in alias_demuxer:
        return "alias", "catalogo ffmpeg: nombre secundario explicito del demuxer"
    return "ficheros_materializables", "CR-007: objeto fichero; disponibilidad de muestra se informa aparte"


def fila_normalizada(
    clave: str,
    dato_historico: dict[str, Any],
    clase: str,
    base: str,
    c49: dict[str, Any] | None,
    demuxers: set[str],
    muxers: set[str],
    alias_demuxer: dict[str, str],
    modulos_im: dict[str, str],
    c50: dict[str, str],
    crudos: dict[str, Any],
) -> dict[str, Any]:
    motor, token = clave.split("|", 1)
    if motor == "ffmpeg":
        normalizado = alias_demuxer.get(token, token)
        if token in alias_demuxer or token in demuxers:
            identidad = f"demuxer:{normalizado}"
        elif token in muxers:
            identidad = f"muxer:{token}"
        else:
            identidad = f"token-catalogo:{token}"
        roles = roles_ffmpeg(token, c49.get("clase") if c49 else None, demuxers, muxers, alias_demuxer)
    else:
        modulo = modulos_im.get(token)
        normalizado = modulo or token
        identidad = f"coder:{normalizado}" if modulo else f"token-catalogo:{token}"
        roles = ["coder"] if modulo else ["token_catalogo_sin_modulo_resuelto"]

    evidencia: dict[str, Any] = {
        "historica": {
            "estado": dato_historico["estado"],
            "fuente": "bench/salidas-aristas/semi_entrada.json",
        }
    }
    if c49:
        evidencia["c49"] = {
            "clase": c49["clase"],
            "mueve": c49["mueve"],
            "fuente": "bench/salidas-aristas-reclasificacion/clasificacion.json",
        }
    if clave in c50:
        evidencia["c50"] = {
            "estado_grafo": c50[clave],
            "fuente": "bench/salidas-aristas-escribibles/recuento50.json",
        }
    if clave in crudos:
        evidencia["p2_crudo"] = {
            "estado": crudos[clave]["estado"],
            "veredicto": crudos[clave]["veredicto"],
            "fuente": "bench/salidas-invocacion/crudos_p2.json",
        }
    return {
        "clave": clave,
        "motor": motor,
        "token_motor": token,
        "roles_token": roles,
        "normalizado_motor": normalizado,
        "identidad_motor": identidad,
        "normalizacion_producto": ALIAS_PRODUCTO.get(token, token),
        "clase_objeto": clase,
        "base_clasificacion": base,
        "estado_historico": dato_historico["estado"],
        "evidencia": evidencia,
        "advertencia": "token, extension e identidad de demuxer/coder son campos distintos",
    }


def construir_clasificacion(raiz: Path) -> dict[str, Any]:
    raiz = raiz.resolve()
    historico = cargar_json(raiz, FUENTES[0])
    clasificacion_c49 = cargar_json(raiz, FUENTES[1])
    recuento_c50 = cargar_json(raiz, Path("bench/salidas-aristas-escribibles/recuento50.json"))
    crudos = cargar_json(raiz, Path("bench/salidas-invocacion/crudos_p2.json"))
    demuxers, alias_demuxer = catalogo_ffmpeg(raiz / FUENTES[2])
    muxers, _ = catalogo_ffmpeg(raiz / FUENTES[3])
    modulos_im = modulos_imagemagick(raiz / FUENTES[4])

    retirados_c50 = set(recuento_c50["dispositivos_retirados"])
    c50 = recuento_c50["reestado"]
    conjuntos = {clase: [] for clase in CLASES}
    filas = []
    for clave in sorted(historico):
        clase, base = decidir_clase(clave, clasificacion_c49, retirados_c50, set(crudos), alias_demuxer)
        conjuntos[clase].append(clave)
        filas.append(
            fila_normalizada(
                clave,
                historico[clave],
                clase,
                base,
                clasificacion_c49.get(clave),
                demuxers,
                muxers,
                alias_demuxer,
                modulos_im,
                c50,
                crudos,
            )
        )

    por_motor = Counter(fila["motor"] for fila in filas)
    por_clase = {clase: len(conjuntos[clase]) for clase in CLASES}
    fuentes = []
    for relativa in FUENTES:
        absoluta = raiz / relativa
        fuentes.append(
            {"ruta": relativa.as_posix(), "bytes": absoluta.stat().st_size, "sha256": sha256(absoluta)}
        )
    return {
        "esquema": "filex.cr-007.normalizacion.v1",
        "estado": "DERIVADO de evidencia conservada; cero conversiones nuevas",
        "unidad": "par (motor, token) de semi_entrada.json",
        "prioridad_particion": list(PRIORIDAD),
        "denominadores": {
            "universo": len(filas),
            "por_motor": dict(sorted(por_motor.items())),
            "por_clase": por_clase,
        },
        "aliases": {
            "producto": ALIAS_PRODUCTO,
            "ffmpeg_demuxers": dict(sorted(alias_demuxer.items())),
            "nota": "los modulos compartidos de ImageMagick no se tratan automaticamente como alias",
        },
        "fuentes": fuentes,
        "conjuntos": conjuntos,
        "filas": filas,
    }


def serializar(resultado: dict[str, Any]) -> str:
    return json.dumps(resultado, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--comprobar", action="store_true")
    parser.add_argument("--salida", type=Path)
    opciones = parser.parse_args(argv)
    raiz = Path(__file__).resolve().parents[2]
    salida = opciones.salida or raiz / SALIDA_RELATIVA
    esperado = serializar(construir_clasificacion(raiz))
    if opciones.comprobar:
        if not salida.is_file() or salida.read_text(encoding="utf-8") != esperado:
            print(f"DESACTUALIZADO: {salida}", file=sys.stderr)
            return 1
        print(f"OK: {salida}")
        return 0
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(esperado, encoding="utf-8", newline="\n")
    print(f"escrito {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Genera y verifica el indice portable de semillas de CR-010.

No ejecuta motores ni materializa corpus. La ausencia de una semilla historica
es un dato del indice, no un error de ejecucion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SALIDA_RELATIVA = Path("bench/salidas-cr-semillas/indice-semillas.json")
POOL_INDICE = Path("bench/salidas-invocacion/pool_indice.json")
MANIFIESTOS = (
    Path("corpus/pdf/MANIFIESTO-d4.md"),
    Path("corpus/pdf/MANIFIESTO-d5.md"),
    Path("bench/salidas-hito5/MANIFIESTO.md"),
    Path("bench/salidas-invocacion/MANIFIESTO.md"),
    Path("bench/salidas-referencia/MANIFIESTO.md"),
)
ROL_CORPUS = {
    "jpeg_exif": Path("corpus/imagen/tipico.jpg"),
    "png_alfa": Path("corpus/imagen/alpha.png"),
    "tif16": Path("corpus/imagen/tipico.png"),
}
ARGV_ROL = {
    "imagen": [
        "magick", "-size", "64x48", "gradient:red-blue", "-fill", "white",
        "-draw", "rectangle 8,8 40,30", "{salida:s.png}",
    ],
    "audio": [
        "ffmpeg", "-nostdin", "-y", "-f", "lavfi", "-i",
        "sine=frequency=440:duration=0.5", "-ar", "8000", "-ac", "1",
        "{salida:s.wav}",
    ],
    "video": [
        "ffmpeg", "-nostdin", "-y", "-f", "lavfi", "-i",
        "testsrc=size=64x48:rate=10:duration=0.5", "-f", "lavfi", "-i",
        "sine=frequency=440:duration=0.5", "-c:v", "libx264", "-pix_fmt",
        "yuv420p", "-c:a", "aac", "-shortest", "{salida:s.mp4}",
    ],
    "documento": ["copiar", "corpus/pdf/tipico_texto.pdf", "{salida:s.pdf}"],
    "video_cif": [
        "ffmpeg", "-nostdin", "-y", "-f", "lavfi", "-i",
        "testsrc=size=352x288:rate=25:duration=1", "-f", "lavfi", "-i",
        "sine=frequency=440:duration=1:sample_rate=48000", "-c:v", "libx264",
        "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "-shortest",
        "{salida:s_cif.mp4}",
    ],
    "subtitulo": ["escribir-fixture-utf8", "{salida:s.srt}"],
    "audio48": [
        "ffmpeg", "-nostdin", "-y", "-f", "lavfi", "-i",
        "sine=frequency=440:duration=1:sample_rate=48000", "-ac", "2",
        "{salida:s48.wav}",
    ],
}


def sha256(ruta: Path) -> str:
    resumen = hashlib.sha256()
    with ruta.open("rb") as fichero:
        for bloque in iter(lambda: fichero.read(1024 * 1024), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def ruta_portable(ruta: Path) -> str:
    return ruta.as_posix()


def metadatos_lfs(raiz: Path) -> dict[str, dict[str, Any]]:
    proceso = subprocess.run(
        ["git", "lfs", "ls-files", "-l"],
        cwd=raiz,
        check=True,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )
    resultado: dict[str, dict[str, Any]] = {}
    for linea in proceso.stdout.splitlines():
        partes = linea.split(maxsplit=2)
        if len(partes) == 3:
            resultado[partes[2].replace("\\", "/")] = {"oid_sha256": partes[0]}
    return resultado


def leer_puntero_lfs(ruta: Path) -> tuple[str, int] | None:
    with ruta.open("rb") as fichero:
        cabecera = fichero.read(256)
    prefijo = b"version https://git-lfs.github.com/spec/v1\n"
    if not cabecera.startswith(prefijo):
        return None
    campos: dict[str, str] = {}
    for linea in cabecera.decode("ascii").splitlines()[1:]:
        clave, _, valor = linea.partition(" ")
        campos[clave] = valor
    oid = campos.get("oid", "")
    if not oid.startswith("sha256:") or "size" not in campos:
        raise ValueError(f"puntero LFS malformado: {ruta}")
    return oid.removeprefix("sha256:"), int(campos["size"])


def datos_archivo(raiz: Path, relativa: Path, lfs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    absoluta = raiz / relativa
    clave = ruta_portable(relativa)
    gestionado = clave in lfs
    if not absoluta.is_file():
        return {
            "ruta_relativa": clave,
            "disponibilidad": "ausente",
            "sha256": lfs.get(clave, {}).get("oid_sha256"),
            "bytes": None,
            "lfs": {"gestionado": gestionado, "es_puntero": False, **lfs.get(clave, {})},
        }
    puntero = leer_puntero_lfs(absoluta) if gestionado else None
    if puntero:
        oid, tamanio = puntero
        return {
            "ruta_relativa": clave,
            "disponibilidad": "puntero_lfs",
            "sha256": oid,
            "bytes": tamanio,
            "lfs": {"gestionado": True, "es_puntero": True, "oid_sha256": oid},
        }
    return {
        "ruta_relativa": clave,
        "disponibilidad": "disponible",
        "sha256": sha256(absoluta),
        "bytes": absoluta.stat().st_size,
        "lfs": {"gestionado": gestionado, "es_puntero": False, **lfs.get(clave, {})},
    }


def licencia_desconocida() -> dict[str, str]:
    return {
        "estado": "desconocida",
        "identificador": "NO-DECLARADA",
        "fuente": "no hay metadato de licencia por semilla en las fuentes indexadas",
    }


def registro_fisico(
    raiz: Path,
    relativa: Path,
    conjunto: str,
    lfs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    token = relativa.suffix.removeprefix(".").lower()
    return {
        "id": f"{conjunto}:{ruta_portable(relativa)}",
        "origen": {
            "tipo": conjunto,
            "fuente": ruta_portable(relativa),
            "base": "arbol versionado del HEAD; identidad fijada por sha256",
        },
        "licencia": licencia_desconocida(),
        **datos_archivo(raiz, relativa, lfs),
        "formato_token": token,
        "uso_esperado": (
            "entrada documental de bench/salidas-hito5/_sonda.py"
            if conjunto == "hito5"
            else "fixture versionado para sondeos y verificaciones del repositorio"
        ),
        "argv_esperado": [],
    }


def corpus_por_extension(raiz: Path) -> dict[str, Path]:
    candidatos: dict[str, Path] = {}
    for ruta in sorted((raiz / "corpus").rglob("*")):
        if not ruta.is_file() or ruta.name.startswith("MANIFIESTO-"):
            continue
        relativa = ruta.relative_to(raiz)
        token = ruta.suffix.removeprefix(".").lower()
        previo = candidatos.get(token)
        if previo is None or ruta.stat().st_size < (raiz / previo).stat().st_size:
            candidatos[token] = relativa
    return candidatos


def registro_pool_token(
    raiz: Path,
    token: str,
    dato: dict[str, Any],
    corpus_ext: dict[str, Path],
    lfs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    procedencia = dato["procedencia"]
    relativa = corpus_ext.get(token) if procedencia == "corpus" else None
    motor, separador, rol = procedencia.partition("<-")
    if relativa:
        archivo = datos_archivo(raiz, relativa, lfs)
        argv: list[str] = []
        uso = "entrada directa elegida como el fichero menor del corpus para el token"
    else:
        esperada = Path("bench/salidas-invocacion/pool/in") / f"m.{token}"
        archivo = {
            "ruta_relativa": ruta_portable(esperada),
            "disponibilidad": "ausente",
            "sha256": None,
            "bytes": dato["bytes"] if dato["bytes"] >= 0 else None,
            "lfs": {"gestionado": False, "es_puntero": False},
        }
        argv = (
            ["ffmpeg", "-nostdin", "-y", "-i", f"{{rol:{rol}}}", f"{{salida:m.{token}}}"]
            if separador and motor == "ffmpeg"
            else ["magick", f"{{rol:{rol}}}", "-auto-orient", f"{{salida:m.{token}}}"]
        )
        uso = "salida regenerable historica; no materializada en este worktree"
    return {
        "id": f"pool-token:{token}",
        "origen": {
            "tipo": "pool_token_historico",
            "fuente": f"{ruta_portable(POOL_INDICE)}#{token}",
            "base": procedencia,
        },
        "licencia": licencia_desconocida(),
        **archivo,
        "formato_token": token,
        "uso_esperado": uso,
        "argv_esperado": argv,
        "geometria_origen": dato.get("geometria"),
    }


def registro_pool_rol(
    raiz: Path,
    rol: str,
    ruta_historica: str,
    lfs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    relativa = ROL_CORPUS.get(rol)
    if relativa:
        archivo = datos_archivo(raiz, relativa, lfs)
    else:
        nombre = Path(ruta_historica.replace("\\", "/")).name
        esperada = Path("bench/salidas-invocacion/pool") / nombre
        archivo = {
            "ruta_relativa": ruta_portable(esperada),
            "disponibilidad": "ausente",
            "sha256": None,
            "bytes": None,
            "lfs": {"gestionado": False, "es_puntero": False},
        }
    return {
        "id": f"pool-rol:{rol}",
        "origen": {
            "tipo": "pool_rol_historico",
            "fuente": f"{ruta_portable(POOL_INDICE)}#__semillas__.{rol}",
            "base": "bench/salidas-invocacion/_p2_semillas.py",
        },
        "licencia": licencia_desconocida(),
        **archivo,
        "formato_token": Path(archivo["ruta_relativa"]).suffix.removeprefix(".").lower(),
        "uso_esperado": f"rol canonico {rol} del pool historico P2",
        "argv_esperado": ARGV_ROL.get(rol, []),
    }


def construir_indice(raiz: Path) -> dict[str, Any]:
    raiz = raiz.resolve()
    lfs = metadatos_lfs(raiz)
    corpus = sorted(
        ruta.relative_to(raiz)
        for ruta in (raiz / "corpus").rglob("*")
        if ruta.is_file() and not ruta.name.startswith("MANIFIESTO-")
    )
    hito5 = sorted(
        ruta.relative_to(raiz)
        for ruta in (raiz / "bench/salidas-hito5/entradas").iterdir()
        if ruta.is_file()
    )
    pool = json.loads((raiz / POOL_INDICE).read_text(encoding="utf-8"))
    roles = pool.pop("__semillas__")
    corpus_ext = corpus_por_extension(raiz)

    semillas = [registro_fisico(raiz, ruta, "corpus", lfs) for ruta in corpus]
    semillas += [registro_fisico(raiz, ruta, "hito5", lfs) for ruta in hito5]
    semillas += [
        registro_pool_token(raiz, token, pool[token], corpus_ext, lfs)
        for token in sorted(pool)
    ]
    semillas += [registro_pool_rol(raiz, rol, roles[rol], lfs) for rol in sorted(roles)]
    semillas.sort(key=lambda registro: registro["id"])

    disponibilidad = {estado: 0 for estado in ("disponible", "puntero_lfs", "ausente")}
    for semilla in semillas:
        disponibilidad[semilla["disponibilidad"]] += 1

    manifiestos = []
    for relativa in MANIFIESTOS:
        absoluta = raiz / relativa
        manifiestos.append(
            {
                "ruta": ruta_portable(relativa),
                "sha256": sha256(absoluta),
                "bytes": absoluta.stat().st_size,
            }
        )
    return {
        "esquema": "filex.cr-010.indice-semillas.v1",
        "estado": "DERIVADO del arbol local; no ejecuta conversiones",
        "fuentes": [ruta_portable(POOL_INDICE), *(m["ruta"] for m in manifiestos)],
        "denominadores": {
            "corpus_versionado": len(corpus),
            "entradas_documentales": len(hito5),
            "pool_tokens_historicos": len(pool),
            "pool_roles_historicos": len(roles),
            "registros": len(semillas),
        },
        "disponibilidad": disponibilidad,
        "manifiestos_fuente": manifiestos,
        "semillas": semillas,
    }


def serializar(indice: dict[str, Any]) -> str:
    return json.dumps(indice, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--comprobar", action="store_true")
    parser.add_argument("--salida", type=Path)
    opciones = parser.parse_args(argv)
    raiz = Path(__file__).resolve().parents[2]
    salida = opciones.salida or raiz / SALIDA_RELATIVA
    esperado = serializar(construir_indice(raiz))
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

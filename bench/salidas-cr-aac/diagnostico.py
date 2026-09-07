"""Reproducción CPU de CR-002: duración AAC, priming y edit lists.

Los binarios se crean en un directorio temporal y se eliminan al terminar. La
salida versionable es JSON: órdenes, versiones, hashes y medidas independientes
de FFprobe, cajas ISO-BMFF y el verificador actual.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from typing import Any

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from filex import verificador as V  # noqa: E402
from filex import huella  # noqa: E402
from filex.motores import FFmpeg  # noqa: E402

TIMEOUT_S = 30
CONTENEDORAS = {b"moov", b"trak", b"mdia", b"minf", b"stbl", b"edts"}


def ejecutar(argv: list[str], *, aceptar_fallo: bool = False) -> subprocess.CompletedProcess[str]:
    r = subprocess.run(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=TIMEOUT_S,
        check=False,
    )
    if r.returncode and not aceptar_fallo:
        raise RuntimeError(f"orden falló rc={r.returncode}: {argv!r}\n{r.stderr[-1000:]}")
    return r


def version(binario: str) -> dict[str, str]:
    r = ejecutar([binario, "-version"])
    lineas = (r.stdout + r.stderr).splitlines()
    ruta = Path(shutil.which(binario) or binario)
    return {
        "primera_linea": lineas[0],
        "sha256_binario": sha256(ruta),
        "salida_completa": "\n".join(lineas),
    }


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def _cajas(datos: bytes, inicio: int, fin: int, camino: tuple[str, ...] = ()):
    pos = inicio
    indice = 0
    while pos + 8 <= fin:
        tam = struct.unpack_from(">I", datos, pos)[0]
        tipo_b = datos[pos + 4 : pos + 8]
        cab = 8
        if tam == 1:
            if pos + 16 > fin:
                return
            tam = struct.unpack_from(">Q", datos, pos + 8)[0]
            cab = 16
        elif tam == 0:
            tam = fin - pos
        if tam < cab or pos + tam > fin:
            return
        tipo = tipo_b.decode("latin-1")
        actual = camino + (f"{tipo}[{indice}]",)
        ini_datos, fin_caja = pos + cab, pos + tam
        yield actual, tipo_b, ini_datos, fin_caja
        if tipo_b in CONTENEDORAS:
            yield from _cajas(datos, ini_datos, fin_caja, actual)
        pos = fin_caja
        indice += 1


def _duracion_fullbox(payload: bytes) -> dict[str, Any] | None:
    if len(payload) < 20:
        return None
    version_ = payload[0]
    if version_ == 1 and len(payload) >= 32:
        escala = struct.unpack_from(">I", payload, 20)[0]
        unidades = struct.unpack_from(">Q", payload, 24)[0]
    elif version_ == 0:
        escala = struct.unpack_from(">I", payload, 12)[0]
        unidades = struct.unpack_from(">I", payload, 16)[0]
    else:
        return None
    return {
        "version": version_,
        "escala": escala,
        "unidades": unidades,
        "segundos": unidades / escala if escala else None,
    }


def medir_isobmff(ruta: Path) -> dict[str, Any]:
    datos = ruta.read_bytes()
    cajas: list[dict[str, Any]] = []
    for camino, tipo, ini, fin in _cajas(datos, 0, len(datos)):
        payload = datos[ini:fin]
        if tipo in (b"mvhd", b"mdhd"):
            medida = _duracion_fullbox(payload)
            if medida:
                cajas.append({"camino": "/".join(camino), "tipo": tipo.decode(), **medida})
        elif tipo == b"elst" and len(payload) >= 8:
            version_ = payload[0]
            n = struct.unpack_from(">I", payload, 4)[0]
            pos = 8
            entradas = []
            for _ in range(n):
                if version_ == 1 and pos + 20 <= len(payload):
                    segmento = struct.unpack_from(">Q", payload, pos)[0]
                    tiempo_medio = struct.unpack_from(">q", payload, pos + 8)[0]
                    pos += 20
                elif version_ == 0 and pos + 12 <= len(payload):
                    segmento = struct.unpack_from(">I", payload, pos)[0]
                    tiempo_medio = struct.unpack_from(">i", payload, pos + 4)[0]
                    pos += 12
                else:
                    break
                entradas.append({"duracion_segmento": segmento, "media_time": tiempo_medio})
            cajas.append({
                "camino": "/".join(camino),
                "tipo": "elst",
                "version": version_,
                "entradas": entradas,
            })
    return {"cajas_temporales": cajas}


def ffprobe(ruta: Path) -> dict[str, Any]:
    campos = (
        "format=start_time,duration:"
        "stream=index,codec_name,codec_type,time_base,start_pts,start_time,"
        "duration_ts,duration,sample_rate,nb_frames"
    )
    r = ejecutar([
        "ffprobe", "-v", "error", "-show_entries", campos, "-of", "json", str(ruta)
    ])
    d = json.loads(r.stdout)
    p = ejecutar([
        "ffprobe", "-v", "error", "-select_streams", "a:0", "-read_intervals", "%+0.03",
        "-show_packets", "-show_entries",
        "packet=pts,pts_time,duration,duration_time,side_data_list", "-of", "json", str(ruta)
    ])
    paquetes = json.loads(p.stdout).get("packets", [])
    d["primer_paquete_audio"] = paquetes[0] if paquetes else None
    return d


def _sin_tiempos(r: dict[str, Any]) -> dict[str, Any]:
    r = dict(r)
    r.pop("ms", None)
    return r


def verificar(salida: Path, entrada: Path) -> dict[str, Any]:
    pedido = {"destino": "m4a", "params": {"solo_audio": True}}
    return {
        motor: _sin_tiempos(V.verificar(str(salida), pedido, str(entrada), motor))
        for motor in ("proceso", "subproceso")
    }


def describir(ruta: Path, *, bmff: bool = False) -> dict[str, Any]:
    d: dict[str, Any] = {
        "bytes": ruta.stat().st_size,
        "sha256": sha256(ruta),
        "ffprobe": ffprobe(ruta),
        "verificador_proceso": V.sondear_en_proceso(str(ruta)),
    }
    if bmff:
        d["isobmff_independiente"] = medir_isobmff(ruta)
    return d


def normalizar_orden(argv: list[str], temporal: Path) -> list[str]:
    base = str(temporal)
    return [str(x).replace(base, "<TMP>") for x in argv]


def normalizar_objeto(valor: Any, temporal: Path) -> Any:
    """Quita del JSON las rutas aleatorias del directorio temporal."""
    if isinstance(valor, str):
        valor = valor.replace(str(temporal), "<TMP>")
        return re.sub(r"(?<= @ )[0-9A-Fa-f]{12,16}(?=\])", "<ADDR>", valor)
    if isinstance(valor, list):
        return [normalizar_objeto(x, temporal) for x in valor]
    if isinstance(valor, dict):
        return {k: normalizar_objeto(v, temporal) for k, v in valor.items()}
    return valor


def resumen_m4a(d: dict[str, Any]) -> dict[str, Any]:
    ff = d["ffprobe"]
    audio = next(x for x in ff.get("streams", []) if x.get("codec_type") == "audio")
    cajas = d["isobmff_independiente"]["cajas_temporales"]
    mdhd = next(x for x in cajas if x["tipo"] == "mdhd")
    elst = next((x for x in cajas if x["tipo"] == "elst"), None)
    paquete = ff.get("primer_paquete_audio") or {}
    lados = paquete.get("side_data_list") or []
    salto = next((x for x in lados if x.get("side_data_type") == "Skip Samples"), {})
    return {
        "duracion_presentada_ffprobe_s": float(audio["duration"]),
        "duracion_contenedor_ffprobe_s": float(ff["format"]["duration"]),
        "duracion_stream_mdhd_s": mdhd["segundos"],
        "priming_ffprobe_muestras": salto.get("skip_samples", 0),
        "edit_list": elst["entradas"] if elst else [],
        "duracion_verificador_contenedor_s": d["verificador_proceso"].get("duracion_s"),
        "duracion_verificador_pista_s": next(
            (x.get("duracion_s") for x in d["verificador_proceso"].get("pistas", [])
             if x.get("tipo") == "audio"), None
        ),
    }


def generar(temporal: Path) -> tuple[dict[str, Path], list[list[str]]]:
    f = {n: temporal / n for n in (
        "referencia.wav", "fuente.mkv", "fuente.mov", "desde-mkv.m4a",
        "desde-mov.m4a", "con-edit-list.m4a", "sin-edit-list.m4a", "truncada.m4a",
    )}
    ordenes = [
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-threads", "1",
         "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=1",
         "-c:a", "pcm_s16le", str(f["referencia.wav"])],
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-threads", "1",
         "-f", "lavfi", "-i", "testsrc2=size=64x64:rate=10:duration=1",
         "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=1",
         "-f", "lavfi", "-i", "sine=frequency=880:sample_rate=44100:duration=1",
         "-map", "0:v:0", "-map", "1:a:0", "-map", "2:a:0", "-c:v", "mpeg4",
         "-q:v", "8", "-c:a", "aac", "-b:a", "96k", "-fflags", "+bitexact",
         "-flags:v", "+bitexact", "-flags:a", "+bitexact", str(f["fuente.mkv"])],
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-threads", "1",
         "-i", str(f["fuente.mkv"]), "-map", "0", "-c", "copy", str(f["fuente.mov"])],
    ]
    for orden in ordenes:
        ejecutar(orden)

    motor = FFmpeg()
    for origen, salida in ((f["fuente.mkv"], f["desde-mkv.m4a"]),
                           (f["fuente.mov"], f["desde-mov.m4a"])):
        orden = motor.orden(str(origen), str(salida), {"bitrate_audio": "192k"})
        ordenes.append(orden)
        ejecutar(orden)

    for uso, salida in (("1", f["con-edit-list.m4a"]), ("0", f["sin-edit-list.m4a"])):
        orden = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                 "-threads", "1", "-i", str(f["referencia.wav"]), "-c:a", "aac",
                 "-b:a", "192k", "-use_editlist", uso, str(salida)]
        ordenes.append(orden)
        ejecutar(orden)

    f["truncada.m4a"].write_bytes(f["con-edit-list.m4a"].read_bytes()[:512])
    return f, ordenes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", type=Path, default=Path(__file__).with_name("resultados.json"))
    a = ap.parse_args()
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("se requieren ffmpeg y ffprobe nativos")

    with tempfile.TemporaryDirectory(prefix="filex-cr002-") as td:
        temporal = Path(td)
        f, ordenes = generar(temporal)
        artefactos = {
            nombre: describir(ruta, bmff=ruta.suffix in (".m4a", ".mov"))
            for nombre, ruta in f.items() if nombre != "truncada.m4a"
        }
        artefactos["truncada.m4a"] = {
            "bytes": f["truncada.m4a"].stat().st_size,
            "sha256": sha256(f["truncada.m4a"]),
            "verificador": verificar(f["truncada.m4a"], f["referencia.wav"]),
            "ffprobe_rc": ejecutar(
                ["ffprobe", "-v", "error", str(f["truncada.m4a"])], aceptar_fallo=True
            ).returncode,
        }
        for origen in ("mkv", "mov"):
            artefactos[f"desde-{origen}.m4a"]["verificacion"] = verificar(
                f[f"desde-{origen}.m4a"], f[f"fuente.{origen}"]
            )
        for tipo in ("con-edit-list", "sin-edit-list"):
            artefactos[f"{tipo}.m4a"]["verificacion_control_wav"] = verificar(
                f[f"{tipo}.m4a"], f["referencia.wav"]
            )

        resumen = {
            nombre: resumen_m4a(artefactos[nombre])
            for nombre in ("con-edit-list.m4a", "sin-edit-list.m4a",
                           "desde-mkv.m4a", "desde-mov.m4a")
        }

        resultado = {
            "esquema": 1,
            "base_diagnosticada": "0ec60d5930444077fefffbac00d19e6dc5ecb55c",
            "commit_verificador": ejecutar(
                ["git", "log", "-1", "--format=%H", "--", "filex/verificador.py"]
            ).stdout.strip(),
            "verificador": {
                "sha256_fichero": sha256(RAIZ / "filex" / "verificador.py"),
                "huella_contrato": huella.de_alcance(
                    (RAIZ / "filex" / "verificador.py").read_text(encoding="utf-8")
                ),
                "interprete_huella": huella.interprete_actual(),
            },
            "cpu_unicamente": True,
            "disable_hardware_acceleration": True,
            "timeout_s": TIMEOUT_S,
            "versiones": {"ffmpeg": version("ffmpeg"), "ffprobe": version("ffprobe")},
            "ordenes": [normalizar_orden(x, temporal) for x in ordenes],
            "artefactos_transitorios": artefactos,
            "resumen_mediciones_m4a": resumen,
            "tolerancia_frame_aac_44100_s": 1024 / 44100,
            "controles_documentales_historicos": {
                "docx->txt/libreoffice": "NOMINAL_REFUTADA: cuelgue/timeout y temporales",
                "epub->pdf/libreoffice": "NOMINAL_REFUTADA: sin lector EPUB aplicable",
                "epub->html/calibre": "NOMINAL_REFUTADA: HTML no soportado; HTMLZ no equivale a HTML",
                "revalidacion_en_esta_tarea": "no ejecutada; Docker prohibido por el alcance CR-002",
            },
        }
        a.salida.parent.mkdir(parents=True, exist_ok=True)
        resultado = normalizar_objeto(resultado, temporal)
        a.salida.write_text(
            json.dumps(resultado, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(a.salida)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

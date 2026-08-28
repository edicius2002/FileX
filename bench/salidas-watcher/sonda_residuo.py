#!/usr/bin/env python3
"""N5 — el RESIDUO: qué formato truncado pasa por bueno, y por qué.

El extremo a extremo con WAV sale bien: las cinco conversiones sobre entrada
incompleta dieron `fallo`. **Y ese resultado no se puede generalizar**, porque
lo que las atrapa no es el motor sino la DURACIÓN DECLARADA en la cabecera —la
regla de diseño del proyecto lo dice con todas las letras: *«el contrato atrapa
la pérdida cuando el contenido perdido está declarado en metadatos»*.

Así que la pregunta que queda es: **¿qué pasa con un formato cuya duración NO
está declarada, sino DEDUCIDA del tamaño del fichero?** Ahí el truncado es
coherente consigo mismo: el fichero más corto declara —por deducción— una
duración más corta, y no hay nada que no cuadre.

Se prueban cuatro entradas truncadas al 50 %, todas a `wav`, y se apunta:
la duración que `ffprobe` le saca a la entrada truncada, la de la salida, el
veredicto de FileX y lo que dice la defensa de coherencia declarada.

R21: directorio desechable, listado antes y después.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, RAIZ)


def censo(d: str) -> dict:
    try:
        return {e.name: (e.stat().st_size if e.is_file() else -1)
                for e in os.scandir(d)}
    except OSError:
        return {}


def duracion(ruta: str):
    argv = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1", ruta]
    try:
        r = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, str(e)
    txt = (r.stdout or "").strip()
    try:
        return float(txt), ""
    except ValueError:
        return None, f"rc={r.returncode} salida={txt!r}"


def cabecera_declara(ruta: str) -> str:
    from filex.watcher import _coherencia_declarada
    return _coherencia_declarada(ruta)


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tmp", required=True)
    p.add_argument("--salida", required=True)
    p.add_argument("--log", required=True)
    p.add_argument("--destino", default="wav")
    a = p.parse_args(argv)

    from filex.nucleo import FileX

    os.makedirs(a.tmp, exist_ok=True)
    antes = censo(a.tmp)
    fx = FileX()
    aud = os.path.join(RAIZ, "corpus", "audio")

    # El CANDIDATO A RESIDUO hay que fabricarlo: `tipico.mp3` trae cabecera
    # Xing/LAME, que declara la duración, y por eso NO es el caso que se busca.
    # Un MP3 CBR sin Xing deduce su duración del tamaño del fichero, así que
    # truncarlo da un fichero coherente consigo mismo.
    sin_xing = os.path.join(a.tmp, "sin_xing.mp3")
    argv = ["ffmpeg", "-nostdin", "-y", "-i", os.path.join(aud, "tipico.mp3"),
            "-c:a", "libmp3lame", "-b:a", "128k", "-write_xing", "0", sin_xing]
    rc_xing = None
    try:
        rc_xing = subprocess.run(argv, stdin=subprocess.DEVNULL,
                                 capture_output=True, timeout=120).returncode
    except (OSError, subprocess.TimeoutExpired) as e:
        rc_xing = str(e)

    entradas = {
        "wav (RIFF declara su longitud)": (os.path.join(aud, "trivial.wav"), "mp3"),
        "flac (STREAMINFO declara las muestras)": (os.path.join(aud, "tipico.flac"), "wav"),
        "mp3 CON cabecera Xing (declara la duración)": (os.path.join(aud, "tipico.mp3"), "wav"),
        "mp3 SIN Xing (la duración se DEDUCE del tamaño)": (sin_xing, "wav"),
    }

    filas = []
    with open(a.log, "w", encoding="utf-8") as log:
        log.write(f"# sonda_residuo — {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"# antes: {len(antes)} ficheros\n")
        log.write(f"# mp3 sin Xing: rc={rc_xing} argv={argv}\n")
        for etiqueta, (origen, dest_fmt) in entradas.items():
            if not os.path.isfile(origen):
                filas.append({"entrada": etiqueta, "condicion_ok": False,
                              "motivo": "no existe en el corpus"})
                continue
            ext = os.path.splitext(origen)[1]
            total = os.path.getsize(origen)
            dur_ent, _ = duracion(origen)
            for etiqueta_c, n in (("completo", total), ("50 %", total // 2)):
                sello = (etiqueta.split(" ")[0] + "_" + etiqueta_c).replace(
                    " ", "").replace("%", "p")
                cortado = os.path.join(a.tmp, f"c_{sello}{ext}")
                with open(origen, "rb") as fa, open(cortado, "wb") as fb:
                    fb.write(fa.read(n))
                cond = os.path.getsize(cortado) == n
                dur_cortada, err_c = duracion(cortado)
                destino = os.path.join(a.tmp, f"s_{sello}{ext}.{dest_fmt}")
                if os.path.exists(destino):
                    os.remove(destino)
                t0 = time.perf_counter()
                conv = fx.convertir(cortado, destino, {}, timeout=120.0)
                ms = (time.perf_counter() - t0) * 1000
                dur_sal, err_s = duracion(destino) if os.path.exists(destino) else (None, "no hay salida")
                fila = {
                    "entrada": etiqueta, "corte": etiqueta_c,
                    "destino_fmt": dest_fmt,
                    "condicion_ok": cond,
                    "condicion": "el fichero quedó con los bytes pedidos",
                    "bytes": os.path.getsize(cortado), "de": total,
                    "coherencia_declarada": cabecera_declara(cortado),
                    "dur_original_s": dur_ent,
                    "dur_entrada_truncada_s": dur_cortada,
                    "err_ffprobe_entrada": err_c,
                    "filex_ok": conv.ok, "veredicto": conv.veredicto,
                    "motivo": conv.motivo[:160],
                    "dur_salida_s": dur_sal, "err_ffprobe_salida": err_s,
                    "ms": round(ms, 1),
                    "bytes_salida": os.path.getsize(destino) if os.path.exists(destino) else -1,
                }
                fila["PASA_POR_BUENA"] = bool(conv.ok and etiqueta_c == "50 %")
                filas.append(fila)
                log.write(json.dumps(fila, ensure_ascii=False) + "\n")
        despues = censo(a.tmp)
        log.write(f"# despues: {len(despues)} ficheros\n")

    res = {"antes": antes, "despues": despues, "filas": filas}
    with open(a.salida, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    for f in filas:
        if "PASA_POR_BUENA" not in f:
            continue
        print(f"{f['entrada'][:52]:52s} {f['corte']:9s} "
              f"coh={f['coherencia_declarada']:16s} ok={str(f['filex_ok']):5s} "
              f"ver={f['veredicto']:6s} dur_ent={f['dur_entrada_truncada_s']} "
              f"dur_sal={f['dur_salida_s']} PASA_POR_BUENA={f['PASA_POR_BUENA']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

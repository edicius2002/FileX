# -*- coding: utf-8 -*-
"""C28 -- los 12 formatos restantes del techo de `firmas-cierre.md` SS4.4
(FATE cierra como mucho 15 de 56; worker2 ya midio 3 de rebote en C16:
oma/vc1 VIVOS, evc MUERTO). Este script busca DIRECTAMENTE en FATE los 12
que faltaban: ac4, avs3, bit, c2, cavs, cvg, dzi, lbc, nia, nii, pml, rcv.

Mismo metodo exacto que `c16_semi_entrada_fate.py` (trampa 79: la MISMA
invocacion que corre el censo, no una reescritura): para ffmpeg, destinos
["mkv","wav","png"] en ese orden, basta uno vivo; tope de 25 s.

Dos vias de busqueda, declaradas por separado:
  1. Directorio de FATE con el MISMO NOMBRE que el formato (metodo de C16).
  2. Busqueda recursiva por EXTENSION en todo el corpus (2 529 ficheros),
     para los alias que `bench/invocacion-aristas.md` L151 ya documento
     (bit->g729, c2->codec2, cavs->cavs, cvg->adpcm_psx, lbc->ilbc,
     rcv->wmv3) -- y para cada acierto se sondea con ffprobe si el
     contenido es GENUINO o una COLISION de extension (trampa 73/70: un
     marcador corto o una extension compartida no prueban el formato).

    D:\\Work\\research\\FileX\\.venv-mcp-filex\\Scripts\\python.exe bench/salidas-fate-completo/c28_12_restantes_fate.py
"""
from __future__ import annotations

import json
import os
import subprocess
import time

SAL = os.path.dirname(os.path.abspath(__file__))
FATE = r"D:\Work\research\fate-suite"
FFMPEG = r"D:\utils\ffmpeg\bin\ffmpeg.exe"
FFPROBE = r"D:\utils\ffmpeg\bin\ffprobe.exe"
TIMEOUT = 25
EXCLUIR = {"md5sum", "csum", "readme", "license", "changelog", "notes",
          "info.txt", "checksums"}

# Los 12 que faltaban del techo de 15/56 (firmas-cierre.md SS4.4), con el
# alias de codec real sondeado en `bench/invocacion-aristas.md` L151 y en
# ffmpeg -formats/-codecs de esta build (ver bench/fate-completo.md SS2.1).
FORMATOS = {
    "ac4":  {"codec_real": "ac4",         "clase_censo": "AVERROR_ENCODER_NOT_FOUND"},
    "avs3": {"codec_real": "avs3",        "clase_censo": "AVERROR_ENCODER_NOT_FOUND"},
    "bit":  {"codec_real": "g729",        "clase_censo": "AVERROR_ENCODER_NOT_FOUND"},
    "c2":   {"codec_real": "codec2",      "clase_censo": "AVERROR_ENCODER_NOT_FOUND"},
    "cavs": {"codec_real": "cavs",        "clase_censo": "AVERROR_ENCODER_NOT_FOUND"},
    "cvg":  {"codec_real": "adpcm_psx",   "clase_censo": "AVERROR_ENCODER_NOT_FOUND"},
    "dzi":  {"codec_real": None,          "clase_censo": "vips: no lo sabe escribir"},
    "lbc":  {"codec_real": "ilbc",        "clase_censo": "AVERROR_ENCODER_NOT_FOUND"},
    "nia":  {"codec_real": None,          "clase_censo": "vips: no lo sabe escribir"},
    "nii":  {"codec_real": None,          "clase_censo": "vips: no lo sabe escribir"},
    "pml":  {"codec_real": None,          "clase_censo": "vips: no lo sabe escribir"},
    "rcv":  {"codec_real": "wmv3",        "clase_censo": "AVERROR_ENCODER_NOT_FOUND"},
}


def corre(args, timeout=TIMEOUT):
    t0 = time.perf_counter()
    try:
        p = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=timeout, errors="replace")
        return p.returncode, (p.stderr or "")[-600:], (time.perf_counter() - t0) * 1000
    except subprocess.TimeoutExpired:
        return -9, "TIMEOUT", (time.perf_counter() - t0) * 1000
    except OSError as e:
        return -127, "OSERROR:" + str(e)[:200], (time.perf_counter() - t0) * 1000


def inv_ffmpeg(ent, dest, sal):
    return [FFMPEG, "-nostdin", "-y", "-i", ent, sal]


def smallest_file(d, excluir_ext=None):
    best = None
    for root, _, files in os.walk(d):
        for f in files:
            base = f.lower().rsplit(".", 1)[0]
            if base in EXCLUIR or f.lower() in EXCLUIR:
                continue
            if excluir_ext and f.lower().endswith(excluir_ext):
                continue
            p = os.path.join(root, f)
            try:
                sz = os.path.getsize(p)
            except OSError:
                continue
            if sz < 100:
                continue
            if best is None or sz < best[1]:
                best = (p, sz)
    return best


def buscar_por_directorio(fmt):
    """Via 1, identica a c16_semi_entrada_fate.py: subdirectorio de FATE
    con el mismo nombre que el formato."""
    d = os.path.join(FATE, fmt)
    if not os.path.isdir(d):
        return None
    bf = smallest_file(d)
    if bf:
        return {"via": "directorio_mismo_nombre", "ruta": bf[0], "bytes": bf[1]}
    return None


def buscar_por_extension(fmt):
    """Via 2: recorrido de todo el corpus por extension .{fmt}. Devuelve
    TODOS los candidatos (para poder sondear colision de extension antes
    de usar el mas pequeno como muestra)."""
    candidatos = []
    ext = "." + fmt.lower()
    for root, _, files in os.walk(FATE):
        for f in files:
            if f.lower().endswith(ext):
                p = os.path.join(root, f)
                try:
                    sz = os.path.getsize(p)
                except OSError:
                    continue
                if sz < 100:
                    continue
                candidatos.append((p, sz))
    return candidatos


def sondear_ffprobe(ruta):
    """Sondea con ffprobe SIN forzar formato -- lo mismo que hara
    ffmpeg -i al autodetectar -- para saber que codec/stream ve de
    verdad, y separar un acierto genuino de una colision de extension
    (trampa 73/70)."""
    rc, err, ms = corre([FFPROBE, "-hide_banner", ruta], timeout=15)
    # ffprobe imprime al stream a stderr
    return err.replace("\n", " | ")[-500:]


def probar_semiarista(ruta, destinos=("mkv", "wav", "png")):
    tmp = os.path.join(SAL, "tmp_c28_12")
    os.makedirs(tmp, exist_ok=True)
    vivo, det = False, []
    for dest in destinos:
        sal = os.path.join(tmp, "x.%s" % dest)
        if os.path.exists(sal):
            os.remove(sal)
        rc, err, ms = corre(inv_ffmpeg(ruta, dest, sal))
        tam = os.path.getsize(sal) if os.path.exists(sal) else -1
        det.append({"destino": dest, "rc": rc, "bytes": tam, "ms": round(ms, 1),
                   "err": err.replace("\n", " ")[-200:] if (rc != 0 or tam <= 0) else ""})
        if rc == 0 and tam > 0:
            vivo = True
            break
    for f in os.listdir(tmp):
        try:
            os.remove(os.path.join(tmp, f))
        except OSError:
            pass
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    return vivo, det


def main():
    filas = []
    t0 = time.time()
    for fmt, meta in FORMATOS.items():
        fila = {"formato": fmt, "codec_real_esperado": meta["codec_real"],
                "clase_censo": meta["clase_censo"]}

        if meta["codec_real"] is None:
            fila["resultado"] = "no_aplica_a_fate"
            fila["motivo"] = ("formato de vips (deep-zoom/NIfTI/paleta de "
                              "GIMP), no es un codec de video/audio: FATE "
                              "es el corpus de conformidad de ffmpeg y no "
                              "tiene subdirectorio ni ficheros de este tipo")
            fila["fate_dir_existe"] = os.path.isdir(os.path.join(FATE, fmt))
            filas.append(fila)
            print("  %-6s NO_APLICA (formato de vips, fuera del dominio de FATE)" % fmt)
            continue

        por_dir = buscar_por_directorio(fmt)
        candidatos_ext = buscar_por_extension(fmt)

        if por_dir is None and not candidatos_ext:
            fila["resultado"] = "no_encontrado_en_fate"
            fila["motivo"] = ("ni subdirectorio '%s' ni ficheros '.%s' en "
                              "los 2 529 ficheros / 303 subdirectorios de "
                              "FATE" % (fmt, fmt))
            filas.append(fila)
            print("  %-6s NO_ENCONTRADO en FATE (ni directorio ni extension)" % fmt)
            continue

        # Preferimos el emparejamiento por DIRECTORIO (misma logica que
        # C16); si no hay, miramos los candidatos por extension, uno a
        # uno, sondeando con ffprobe si el contenido es genuino.
        elegido = None
        origen_eleccion = None
        if por_dir is not None:
            elegido = por_dir["ruta"]
            origen_eleccion = "directorio_mismo_nombre (%s)" % os.path.basename(elegido)
        else:
            # ordenar candidatos por tamano y sondear el mas pequeno
            candidatos_ext.sort(key=lambda t: t[1])
            fila["candidatos_por_extension"] = [
                {"ruta": p, "bytes": sz} for p, sz in candidatos_ext[:10]
            ]
            probes = []
            genuino = None
            for p, sz in candidatos_ext[:5]:
                sonda = sondear_ffprobe(p)
                es_genuino = meta["codec_real"] in sonda.lower()
                probes.append({"ruta": p, "bytes": sz, "sonda_ffprobe": sonda,
                              "coincide_con_codec_esperado": es_genuino})
                if es_genuino and genuino is None:
                    genuino = (p, sz)
            fila["sondeo_extension"] = probes
            if genuino is not None:
                elegido = genuino[0]
                origen_eleccion = "extension_.%s_verificada_por_ffprobe (%s)" % (
                    fmt, os.path.basename(elegido))
            else:
                fila["resultado"] = "extension_coincide_pero_contenido_NO"
                fila["motivo"] = (
                    "hay %d fichero(s) '.%s' en FATE pero NINGUNO decodifica "
                    "como '%s' segun ffprobe sin forzar formato -- es una "
                    "COLISION de extension (misma familia que la trampa "
                    "70/73: '.bit' lo comparten HEVC/VVC/MP3 de "
                    "conformidad, no G.729)" % (len(candidatos_ext), fmt,
                                                 meta["codec_real"]))
                filas.append(fila)
                print("  %-6s COLISION de extension, %d candidato(s), ninguno genuino"
                      % (fmt, len(candidatos_ext)))
                continue

        fila["fate_ruta"] = elegido
        fila["fate_bytes"] = os.path.getsize(elegido)
        fila["origen_eleccion"] = origen_eleccion
        fila["sonda_ffprobe_elegido"] = sondear_ffprobe(elegido)

        vivo, det = probar_semiarista(elegido)
        fila["estado"] = "viva" if vivo else "muerta"
        fila["intentos"] = det
        fila["resultado"] = "medido"
        filas.append(fila)
        print("  %-6s FATE=%-40s (%s) %6d B  ->  %s  (%.0fs)"
              % (fmt, os.path.basename(elegido), origen_eleccion,
                 fila["fate_bytes"], "VIVA" if vivo else "MUERTA",
                 time.time() - t0))

    medidas = [f for f in filas if f["resultado"] == "medido"]
    vivas = sum(1 for f in medidas if f["estado"] == "viva")
    resultado = {
        "n_formatos": len(FORMATOS),
        "n_medidos": len(medidas),
        "n_vivas": vivas,
        "n_muertas": len(medidas) - vivas,
        "n_no_encontrado_en_fate": sum(1 for f in filas if f["resultado"] == "no_encontrado_en_fate"),
        "n_colision_extension": sum(1 for f in filas if f["resultado"] == "extension_coincide_pero_contenido_NO"),
        "n_no_aplica_vips": sum(1 for f in filas if f["resultado"] == "no_aplica_a_fate"),
        "filas": filas,
    }
    with open(os.path.join(SAL, "c28_12_restantes_fate_resultado.json"), "w",
             encoding="utf-8") as fh:
        json.dump(resultado, fh, indent=1, ensure_ascii=False)
    print("\nResumen: %d medidos (%d vivas / %d muertas), %d no encontrados, "
          "%d colision de extension, %d no_aplica (vips)"
          % (len(medidas), vivas, len(medidas) - vivas,
             resultado["n_no_encontrado_en_fate"],
             resultado["n_colision_extension"], resultado["n_no_aplica_vips"]))


if __name__ == "__main__":
    main()

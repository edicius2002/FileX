# -*- coding: utf-8 -*-
"""C16 -- ampliacion de la muestra estratificada de C16 con ALIAS, tal como
pide el encargo: "Buscar coincidencias no exactas: alias conocidos,
extensiones alternativas del mismo formato". `c16_semi_entrada_fate.py`
(worker2, ronda 11) solo empareja por NOMBRE DE DIRECTORIO IDENTICO al
nombre del formato -- 69 de 445. Este script busca, entre los 376 formatos
"no_materializable" restantes (291 ffmpeg + 85 imagemagick), los que tienen
un demuxer/alias CONOCIDO cuyo nombre de directorio en FATE es DISTINTO.

Cada candidato se VERIFICA antes de usarlo (sonda previa en
`_sondeo_alias.py`, no incluida en el resultado publicado): se comprueba
con `ffprobe` SIN forzar formato que el demuxer que ffmpeg autodetecta de
verdad coincide con el alias esperado -- para no repetir la trampa 73/70
(un nombre parecido no prueba el mismo formato; `.bit` lo comparten HEVC/
VVC/MP3 de conformidad con G.729 y NO son el mismo formato). Dos alias NO
pasaron la sonda natural y se declaran aparte:
  - `vc1test`: el fichero mas pequeno de `vc1/` (`SA00040.vc1`) autodetecta
    como demuxer `vc1`, no `vc1test`. Se usa en su lugar `SMM0015.rcv`
    (mismo directorio), que SI autodetecta `vc1test` de forma natural.
  - `asf_o`: ningun fichero de `asf/` autodetecta `asf_o` de forma natural
    (todos resuelven a `asf`, el demuxer moderno). Se fuerza `-f asf_o`
    explicitamente y se declara FORZADO -- no es la misma medida que un
    alias que se detecta solo.

Mismo metodo de fondo que `c16_semi_entrada_fate.py` (trampa 79): destinos
["mkv","wav","png"] en ese orden, basta uno vivo, tope 25 s.

    D:\\Work\\research\\FileX\\.venv-mcp-filex\\Scripts\\python.exe bench/salidas-fate-completo/c16_alias_fate.py
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

# formato -> (subdirectorio de FATE, fichero explicito o None para "el mas
# pequeno", forzar demuxer con -f o None). Los 23 verificados por
# `_sondeo_alias.py` antes de correr esta tanda.
ALIAS = {
    "cavsvideo":    ("cavs", None, None),
    "vc1test":      ("vc1", "SMM0015.rcv", None),
    "roq":          ("idroq", None, None),
    "anm":          ("deluxepaint-anm", None, None),
    "c93":          ("cyberia-c93", None, None),
    "dfa":          ("chronomaster-dfa", None, None),
    "iss":          ("funcom-iss", None, None),
    "wsvqa":        ("vqa", None, None),
    "wsaud":        ("westwood-aud", None, None),
    "daud":         ("d-cinema", None, None),
    "argo_asf":     ("argo-asf", None, None),
    "asf_o":        ("asf", None, "asf_o"),
    "amr":          ("amrnb", None, None),
    "ipmovie":      ("interplay-mve", None, None),
    "dsicin":       ("delphine-cin", None, None),
    "ans":          ("ansi", None, None),
    "psxstr":       ("psx-str", None, None),
    "film_cpk":     ("film", None, None),
    "bethsoftvid":  ("bethsoft-vid", None, None),
    "brender_pix":  ("brenderpix", None, None),
    "alias_pix":    ("aliaspix", None, None),
    "ea_cdata":     ("ea-cdata", None, None),
    "tiertexseq":   ("tiertex-seq", None, None),
    "mvi":          ("motion-pixels", None, None),
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


def inv_ffmpeg(ent, dest, sal, forzar):
    args = [FFMPEG, "-nostdin", "-y"]
    if forzar:
        args += ["-f", forzar]
    args += ["-i", ent, sal]
    return args


def smallest_file(d):
    best = None
    for root, _, files in os.walk(d):
        for f in files:
            base = f.lower().rsplit(".", 1)[0]
            if base in EXCLUIR or f.lower() in EXCLUIR:
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


def sondar_demuxer_natural(ruta):
    rc, err, ms = corre([FFPROBE, "-hide_banner", ruta], timeout=15)
    for ln in err.splitlines():
        ln = ln.strip()
        if ln.startswith("Input #0"):
            return ln
    return ""


def main():
    tmp = os.path.join(SAL, "tmp16b")
    os.makedirs(tmp, exist_ok=True)

    filas = []
    t0 = time.time()
    for fmt, (dirname, archivo, forzar) in ALIAS.items():
        d = os.path.join(FATE, dirname)
        if archivo:
            ruta = os.path.join(d, archivo)
            tam_fate = os.path.getsize(ruta) if os.path.exists(ruta) else -1
        else:
            bf = smallest_file(d)
            ruta, tam_fate = bf if bf else (None, -1)

        if ruta is None or not os.path.exists(ruta):
            filas.append({"formato": fmt, "fate_dir": dirname,
                         "resultado": "fichero_no_encontrado"})
            print("  %-12s SIN FICHERO en %s" % (fmt, dirname))
            continue

        sonda_natural = sondar_demuxer_natural(ruta) if not forzar else "(no aplica: forzado)"

        vivo, det = False, []
        for dest in ("mkv", "wav", "png"):
            sal = os.path.join(tmp, "x.%s" % dest)
            if os.path.exists(sal):
                os.remove(sal)
            rc, err, ms = corre(inv_ffmpeg(ruta, dest, sal, forzar))
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

        fila = {
            "formato": fmt, "fate_dir": dirname,
            "fate_ruta": ruta, "fate_bytes": tam_fate,
            "demuxer_esperado": fmt, "forzado_con_-f": forzar,
            "sonda_ffprobe_natural": sonda_natural,
            "estado": "viva" if vivo else "muerta",
            "intentos": det, "resultado": "medido",
        }
        filas.append(fila)
        print("  %-12s FATE=%-45s %8d B  %-10s -> %s (%.0fs)"
              % (fmt, os.path.basename(ruta), tam_fate,
                 "[forzado %s]" % forzar if forzar else "[natural]",
                 "VIVA" if vivo else "MUERTA", time.time() - t0))

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    medidas = [f for f in filas if f["resultado"] == "medido"]
    vivas = sum(1 for f in medidas if f["estado"] == "viva")
    resultado = {
        "n_alias_candidatos": len(ALIAS),
        "n_medidos": len(medidas),
        "n_vivas": vivas,
        "n_muertas": len(medidas) - vivas,
        "tasa_viva": round(vivas / len(medidas), 4) if medidas else None,
        "filas": filas,
    }
    with open(os.path.join(SAL, "c16_alias_fate_resultado.json"), "w",
             encoding="utf-8") as fh:
        json.dump(resultado, fh, indent=1, ensure_ascii=False)
    print("\n%d/%d VIVAS de los alias (%.1f %%)"
          % (vivas, len(medidas), 100 * vivas / len(medidas) if medidas else 0))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""C50 / worker10 - Los cierres sueltos: chk, clip/mask, gsm remediado, eml.

  (1) `chk` = muxer `webm_chunk`. C28 lo dejo fuera porque "exige otro paradigma de
      invocacion, no una bandera" -- y en la ronda 11 **no se ejecuto**: estaba en el
      diccionario OTRO_PARADIGMA, fuera del bucle. Aqui se ejecuta con su paradigma.
  (2) `clip` y `mask`: ImageMagick los declara `rw+`. Se prueban en las dos
      direcciones, escribir y leer.
  (3) `gsm` dentro del contenedor: alli SI hay `libgsm`, y el fallo no fue
      "Encoder not found" sino "Error while opening encoder", que es la firma de una
      restriccion de parametros (8 kHz mono), no de un codificador ausente.
  (4) `eml` con `msgconvert`, que SI esta en el contenedor (`/usr/bin/msgconvert`).

ESCRIBE unicamente en este directorio.
"""
import os, json, time, shutil, subprocess
import escribe_ff as E
from contenedor2 import dentro

RES = {}


def local(argv, d, tope=25):
    return E.corre(argv, d, tope)


def nuevo_dir(nom):
    d = os.path.join(E.TRABAJO, nom)
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    return d


# ------------------------------------------------------------------ (1) chk
def chk():
    sem = E.semillas()
    out = {"muxer": "webm_chunk", "celdas": []}
    casos = [
        ("nominal_un_fichero",
         ["-f", "webm_chunk", "m.chk"],
         "lo que el censo intento: un solo fichero de salida. C28 lo dio por EINVAL"),
        ("paradigma_cabecera_y_trozos",
         ["-c:v", "libvpx", "-f", "webm_chunk", "-header", "m_hdr.chk",
          "-chunk_start_index", "1", "m_%d.chk"],
         "el paradigma que webm_chunk pide: cabecera aparte + trozos numerados"),
        ("paradigma_audio",
         ["-c:a", "libvorbis", "-f", "webm_chunk", "-audio_chunk_duration", "1000",
          "-header", "a_hdr.chk", "-chunk_start_index", "1", "a_%d.chk"],
         "la variante de audio del mismo muxer"),
    ]
    for nom, extra, porque in casos:
        d = nuevo_dir("chk_" + nom)
        antes = E.censa(d)
        argv = ["ffmpeg", "-nostdin", "-y", "-i", sem["video_cif"]] + extra
        rc, err, ms = local(argv, d, 40)
        rc = E.signo(rc)
        desp = E.censa(d)
        nuevos = {k: v for k, v in desp.items() if k not in antes}
        c = {"caso": nom, "porque": porque, "argv": argv, "rc": rc,
             "clase_rc": E.clase_rc(rc, err), "ficheros_nuevos": nuevos,
             "bytes_totales": sum(v for v in nuevos.values() if v > 0),
             "ms": round(ms, 1),
             "ok": bool(rc == 0 and sum(v for v in nuevos.values() if v > 0) > 0),
             "stderr": err.replace("\r", "").replace("\n", " | ")[-700:]}
        out["celdas"].append(c)
        print("  chk %-30s rc=%-5s ficheros=%-2d bytes=%-8d %s"
              % (nom, rc, len(nuevos), c["bytes_totales"], "OK" if c["ok"] else "no"), flush=True)
        shutil.rmtree(d, ignore_errors=True)
    out["escrito"] = any(c["ok"] for c in out["celdas"])
    out["un_solo_fichero"] = any(c["ok"] and len(c["ficheros_nuevos"]) == 1 for c in out["celdas"])
    return out


# ------------------------------------------------------------------ (2) clip / mask
def clipmask():
    raiz = os.path.abspath(os.path.join(E.AQUI, "..", ".."))
    png = os.path.join(raiz, "corpus", "imagen", "tipico.png")
    out = {}
    for tok in ("clip", "mask"):
        d = nuevo_dir("im_" + tok)
        fila = {"declara": "-list format: modo rw+"}
        # a) ESCRIBIR: magick tipico.png m.<tok>
        antes = E.censa(d)
        dest = os.path.join(d, "m." + tok)
        argv = ["magick", png, "-auto-orient", dest]
        rc, err, ms = local(argv, d)
        desp = E.censa(d)
        nuevos = {k: v for k, v in desp.items() if k not in antes}
        fila["escribir"] = {"argv": argv, "rc": rc, "ficheros_nuevos": nuevos,
                            "bytes": desp.get("m." + tok, -1), "ms": round(ms, 1),
                            "ok": bool(rc == 0 and desp.get("m." + tok, -1) > 0),
                            "stderr": err.replace("\n", " | ")[-500:]}
        # b) LEER lo escrito, que es lo que el censo de ENTRADA necesita
        if fila["escribir"]["ok"]:
            sal = os.path.join(d, "leido.png")
            argv2 = ["magick", dest, "-auto-orient", sal]
            rc2, err2, ms2 = local(argv2, d)
            fila["leer"] = {"argv": argv2, "rc": rc2,
                            "bytes": os.path.getsize(sal) if os.path.exists(sal) else -1,
                            "ms": round(ms2, 1),
                            "stderr": err2.replace("\n", " | ")[-500:]}
            fila["leer"]["ok"] = bool(rc2 == 0 and fila["leer"]["bytes"] > 0)
        else:
            fila["leer"] = {"no_procede": "no hay fichero que leer"}
        out[tok] = fila
        print("  %-5s escribir rc=%-4s bytes=%-8s %s | leer %s"
              % (tok, fila["escribir"]["rc"], fila["escribir"]["bytes"],
                 "OK" if fila["escribir"]["ok"] else "no",
                 fila["leer"].get("ok", "-")), flush=True)
        shutil.rmtree(d, ignore_errors=True)
    return out


# ------------------------------------------------------------------ (3) gsm dentro
def gsm_dentro():
    orden = ("cd /tmp/c50w && rm -f m.gsm && "
             "ffmpeg -nostdin -y -i s48.wav -f gsm -ar 8000 -ac 1 m.gsm 2>e2.txt; echo RC=$?; "
             "if [ -f m.gsm ]; then stat -c 'BYTES=%s' m.gsm; else echo BYTES=-1; fi; "
             "tail -3 e2.txt")
    rc, so, se, ms = dentro(orden, 40)
    d = {"orden": orden, "salida": so.strip()[:800], "ms": round(ms, 1)}
    for ln in so.splitlines():
        if ln.startswith("RC="):
            d["rc"] = int(ln[3:])
        if ln.startswith("BYTES="):
            d["bytes"] = int(ln[6:])
    d["ok"] = (d.get("rc") == 0 and d.get("bytes", -1) > 0)
    print("  gsm dentro con -ar 8000 -ac 1: rc=%s bytes=%s -> %s"
          % (d.get("rc"), d.get("bytes"), "ESCRITO" if d["ok"] else "no"), flush=True)
    return d


# ------------------------------------------------------------------ (4) eml
def eml():
    orden = ("rm -rf /tmp/c50e && mkdir -p /tmp/c50e && cd /tmp/c50e && "
             "command -v msgconvert; msgconvert --help >/dev/null 2>&1; echo HELP_RC=$?; "
             "printf 'no soy un .msg\\n' > falso.msg && "
             "ls > _antes.txt; msgconvert falso.msg > _log.txt 2>&1; echo RC=$?; "
             "echo '--- nuevos ---'; ls | grep -v -x -F -f _antes.txt; "
             "echo '--- log ---'; head -5 _log.txt")
    rc, so, se, ms = dentro(orden, 60)
    print(so.strip()[-700:], flush=True)
    return {"orden": orden, "salida": so[-2500:], "stderr": se[-500:], "ms": round(ms, 1),
            "nota": "msgconvert convierte .msg -> .eml; el destino `eml` del censo de C28 "
                    "nunca se ejecuto y su clase salio del valor por defecto del clasificador"}


if __name__ == "__main__":
    os.makedirs(E.TRABAJO, exist_ok=True)
    print("(1) chk = webm_chunk, con su paradigma:", flush=True)
    RES["chk"] = chk()
    print("\n(2) clip y mask, que ImageMagick declara rw+:", flush=True)
    RES["clip_mask"] = clipmask()
    print("\n(3) gsm dentro del contenedor, remediado:", flush=True)
    RES["gsm_dentro"] = gsm_dentro()
    print("\n(4) eml / msgconvert:", flush=True)
    RES["eml"] = eml()
    json.dump(RES, open(os.path.join(E.AQUI, "cierres.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False, sort_keys=True)
    print("\nescrito cierres.json")

# -*- coding: utf-8 -*-
"""C50 / worker10 - Segundo y ULTIMO intento de chk, clip y mask (CLAUDE.md sec.3).

Los tres fallaron por un motivo que el `stderr` nombra, y los tres remedios salen de
ese mensaje, no de la documentacion:

  chk  - "Output file does not contain any stream": `webm_chunk` no admite las dos
         pistas de la semilla. Se le da UNA sola, con `-map` explicito y `-an`.
  clip - "image does not have a clip mask ... WriteCLIPImage": el coder no escribe la
         imagen, escribe su TRAYECTORIA DE RECORTE. Se le da una entrada que la traiga.
  mask - "image does not have an mask channel ... WriteMASKImage": idem con el canal
         de mascara. Se prueba con `alpha.png`, que es el fichero del corpus con alfa
         NO TRIVIAL (t.1: `tipico.png` declara alfa y es enteramente opaco).

Si vuelven a fallar se documenta el error exacto y se sigue: no hay tercera pasada.

ESCRIBE unicamente en este directorio.
"""
import os, json, shutil
import escribe_ff as E

RAIZ = os.path.abspath(os.path.join(E.AQUI, "..", ".."))
PNG = os.path.join(RAIZ, "corpus", "imagen", "tipico.png")
ALFA = os.path.join(RAIZ, "corpus", "imagen", "alpha.png")


def corre_en(nom, argv, tope=30):
    d = os.path.join(E.TRABAJO, nom)
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    antes = E.censa(d)
    rc, err, ms = E.corre(argv, d, tope)
    rc = E.signo(rc)
    desp = E.censa(d)
    nuevos = {k: v for k, v in desp.items() if k not in antes}
    out = {"argv": argv, "rc": rc, "clase_rc": E.clase_rc(rc, err),
           "ficheros_nuevos": nuevos,
           "bytes_totales": sum(v for v in nuevos.values() if v > 0),
           "ms": round(ms, 1),
           "stderr": err.replace("\r", "").replace("\n", " | ")[-800:]}
    out["ok"] = bool(rc == 0 and out["bytes_totales"] > 0)
    shutil.rmtree(d, ignore_errors=True)
    return out


if __name__ == "__main__":
    sem = E.semillas()
    R = {}

    # ---- chk: una sola pista
    R["chk"] = {}
    for nom, extra, porque in (
            ("solo_video", ["-map", "0:v:0", "-an", "-c:v", "libvpx", "-f", "webm_chunk",
                            "-header", "h.chk", "-chunk_start_index", "1", "m_%d.chk"],
             "'does not contain any stream': webm_chunk no admite las dos pistas"),
            ("solo_audio", ["-map", "0:a:0", "-vn", "-c:a", "libvorbis", "-f", "webm_chunk",
                            "-audio_chunk_duration", "1000",
                            "-header", "ha.chk", "-chunk_start_index", "1", "a_%d.chk"],
             "idem, la variante de audio")):
        c = corre_en("chk2_" + nom, ["ffmpeg", "-nostdin", "-y", "-i", sem["video_cif"]] + extra, 40)
        c["porque"] = porque
        R["chk"][nom] = c
        print("chk %-12s rc=%-5s ficheros=%s bytes=%d -> %s"
              % (nom, c["rc"], sorted(c["ficheros_nuevos"]), c["bytes_totales"],
                 "OK" if c["ok"] else "no"), flush=True)
        if not c["ok"]:
            print("    %s" % c["stderr"][-260:], flush=True)

    # ---- clip / mask: entrada que traiga el metadato
    R["clip_mask"] = {}
    casos = [
        ("mask_desde_alpha", ["magick", ALFA, "-alpha", "extract", "m.mask"],
         "el canal de mascara extraido de alpha.png (alfa NO trivial, t.1)"),
        ("mask_write_mask", ["magick", ALFA, "-write-mask", ALFA, "m.mask"],
         "activando la mascara de escritura de IM7"),
        ("clip_con_path", ["magick", PNG, "-alpha", "set", "-clip", "m.clip"],
         "pidiendo el recorte por trayectoria"),
        ("clip_desde_alpha", ["magick", ALFA, "-clip", "m.clip"],
         "idem desde la imagen con alfa real"),
    ]
    for nom, argv, porque in casos:
        c = corre_en("im2_" + nom, argv)
        c["porque"] = porque
        R["clip_mask"][nom] = c
        print("%-20s rc=%-4s ficheros=%s -> %s"
              % (nom, c["rc"], sorted(c["ficheros_nuevos"]), "OK" if c["ok"] else "no"), flush=True)
        if not c["ok"]:
            print("    %s" % c["stderr"][-260:], flush=True)

    json.dump(R, open(os.path.join(E.AQUI, "cierres2.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False, sort_keys=True)
    print("\nescrito cierres2.json")

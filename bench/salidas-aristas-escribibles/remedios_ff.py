# -*- coding: utf-8 -*-
"""C50 / worker10 - PASADA 2: remedios DIRIGIDOS POR EL `rc` sobre los 37 que fallaron.

t.72: el `rc` no es una pista, es la respuesta. Cada remedio de esta tabla sale del
mensaje EXACTO que la pasada 1 registro, y el mensaje va escrito al lado. Nada aqui
se deduce de la documentacion de ffmpeg: se lee del stderr medido y se ejecuta.

t.75: las banderas NO se transfieren. Cada remedio pertenece al muxer que ejecuta.
Una celda se cuenta buena con `rc == 0` **Y** `bytes > 0`.

Dos intentos por problema como maximo (CLAUDE.md sec.3): la tabla da 1 o 2 hipotesis
por token, ninguna es un reintento de la misma.

`chk` va aparte, en `chk_paradigma.py`: no es una bandera, es otro modo de escritura.

ESCRIBE unicamente en este directorio.
"""
import os, json, time, collections
import escribe_ff as E

# ---------------------------------------------------------------- la tabla
# token: [(semilla, [banderas], "mensaje medido que lo motiva"), ...]
R = {
    # --- "Error while opening encoder" de libopencore_amrnb: 8 kHz mono
    "amr":  [("audio48", ["-ar", "8000", "-ac", "1", "-b:a", "12.2k"],
              "libopencore_amrnb: Error while opening encoder - maybe incorrect parameters")],
    "3gp":  [("video_cif", ["-c:v", "libx264", "-c:a", "aac"],
              "el audio por defecto de 3gp es libopencore_amrnb y no abre"),
             ("audio48", ["-c:a", "aac", "-ar", "8000", "-ac", "1"], "idem, solo audio")],
    "3g2":  [("video_cif", ["-c:v", "libx264", "-c:a", "aac"],
              "el audio por defecto de 3g2 es libopencore_amrnb y no abre"),
             ("audio48", ["-c:a", "aac", "-ar", "8000", "-ac", "1"], "idem, solo audio")],
    # --- restricciones que el propio muxer IMPRIME
    "daud": [("audio48", ["-ac", "6", "-ar", "96000"],
              "daud: 'Invalid number of channels 1, must be exactly 6'")],
    "mmf":  [("audio48", ["-ar", "44100", "-ac", "1"],
              "mmf: 'Unsupported sample rate 48000, supported are 4000, 8000, 11025, 22050 and 44100'")],
    "filmstrip": [("video_cif", ["-pix_fmt", "rgba"],
              "filmstrip: 'only AV_PIX_FMT_RGBA is supported'")],
    "gxf":  [("video_cif", ["-s", "720x480", "-r", "30000/1001", "-c:v", "mpeg2video",
                            "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le"],
              "gxf: 'unsupported video resolution, gxf muxer only accepts PAL or NTSC'")],
    # --- codificadores con restricciones de tasa/frecuencia (mensaje generico del enc)
    "g723_1": [("audio48", ["-ar", "8000", "-ac", "1", "-b:a", "6.3k"],
              "g723_1: Error while opening encoder; G.723.1 solo admite 8 kHz mono")],
    "g726":  [("audio48", ["-ar", "8000", "-ac", "1", "-b:a", "16k"],
              "g726: Error while opening encoder; ADPCM G.726 exige 8 kHz mono y tasa fija")],
    "g726le": [("audio48", ["-ar", "8000", "-ac", "1", "-b:a", "16k"], "idem g726")],
    "alp":  [("audio48", ["-c:a", "adpcm_ima_alp", "-ar", "22050", "-ac", "1"],
              "alp: 'Could not write header (incorrect codec parameters ?)'"),
             ("audio48", ["-c:a", "pcm_u8", "-ar", "22050", "-ac", "1"], "alt: alp admite pcm_u8")],
    "roq":  [("video_cif", ["-s", "256x256", "-r", "30", "-ar", "22050", "-ac", "1"],
              "roq_dpcm: Error while opening encoder; RoQ exige 22050 Hz y lados multiplo de 16")],
    "dv":   [("video_cif", ["-s", "720x480", "-pix_fmt", "yuv411p", "-r", "30000/1001",
                            "-ar", "48000", "-ac", "2"],
              "dvvideo: Error while opening encoder; DV-NTSC exige 720x480 yuv411p 29,97")],
    # --- los tres que C28 ya escribio: control de REPRODUCCION de un resultado ajeno
    "dnxhd": [("video_cif", ["-s", "1920x1080", "-b:v", "36M", "-pix_fmt", "yuv422p", "-r", "25"],
              "C28 (firmas-cierre.md 4.4) lo escribio 2/2 con estas banderas")],
    "dts":  [("audio48", ["-strict", "-2"],
              "AVERROR_EXPERIMENTAL; C28 lo escribio 2/2 con -strict -2")],
    "mlp":  [("audio48", ["-strict", "-2", "-ar", "48000"],
              "AVERROR_EXPERIMENTAL; C28 lo escribio 2/2 con -strict -2 -ar 48000")],
    "truehd": [("audio48", ["-strict", "-2", "-ar", "48000"],
              "AVERROR_EXPERIMENTAL; mismo codificador que thd, que C28 escribio 2/2")],
    # --- "does not contain any stream": el muxer no encuentra codificador de subtitulo
    "microdvd": [("subtitulo", ["-c:s", "microdvd"], "muxer sin stream: se fuerza el codec de subtitulo"),
                 ("subtitulo", ["-c:s", "text"], "alt: codificador de texto crudo")],
    "jacosub":  [("subtitulo", ["-c:s", "jacosub"], "idem"),
                 ("subtitulo", ["-c:s", "text"], "alt")],
    "scc":      [("subtitulo", ["-c:s", "eia_608"], "idem"),
                 ("subtitulo", ["-c:s", "text"], "alt")],
    "mcc":      [("subtitulo", ["-c:s", "eia_608"], "idem"),
                 ("subtitulo", ["-c:s", "text"], "alt")],
    "sup":      [("subtitulo", ["-c:s", "dvdsub"], "sup es HDMV PGS: subtitulo de MAPA DE BITS"),
                 ("video_cif", ["-c:s", "dvdsub"], "alt: desde video")],
}

if __name__ == "__main__":
    prev = json.load(open(os.path.join(E.AQUI, "escritura_ff.json"), encoding="utf-8"))["res"]
    fallidos = sorted(k for k, v in prev.items() if not v["materializado"])
    sem = E.semillas()
    os.makedirs(E.TRABAJO, exist_ok=True)

    print("fallidos de la pasada 1: %d" % len(fallidos))
    sin_remedio = [k for k in fallidos if k not in R]
    print("sin remedio en la tabla (%d): %s\n" % (len(sin_remedio), sin_remedio))

    res, n, t0 = {}, 5000, time.time()
    for tok in fallidos:
        if tok not in R:
            res[tok] = {"materializado": False, "remedio": None,
                        "motivo": "sin remedio local: la pasada 1 dio %s"
                                  % sorted({c["clase_rc"] for c in prev[tok]["celdas"]}),
                        "celdas": []}
            continue
        celdas, ok = [], False
        for mod, extra, porque in R[tok]:
            n += 1
            c = E.celda(n, tok, mod, sem[mod], "remedio", list(extra))
            c["motivo_del_remedio"] = porque
            celdas.append(c)
            if c["ok"]:
                ok = True
                break
        res[tok] = {"materializado": ok, "celdas": celdas,
                    "remedio": " ".join(celdas[-1]["argv"][5:-1]) if ok else None,
                    "por": celdas[-1]["semilla"] if ok else None,
                    "bytes": celdas[-1]["bytes"] if ok else -1}
        print("  %-10s %s" % (tok, ("ESCRITO %d B  [%s]" % (celdas[-1]["bytes"], res[tok]["remedio"]))
                              if ok else "no (%s)" % ", ".join(sorted({c["clase_rc"] for c in celdas}))), flush=True)

    esc = sum(1 for v in res.values() if v["materializado"])
    print("\nREMEDIADOS %d de %d  (%.0fs)" % (esc, len(fallidos), time.time() - t0))
    json.dump(res, open(os.path.join(E.AQUI, "remedios_ff.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False, sort_keys=True)

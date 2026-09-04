# -*- coding: utf-8 -*-
"""C50 / worker10 - Lo que solo se puede responder DENTRO del contenedor.

Tres preguntas, las tres por EJECUCION y no por deduccion (CLAUDE.md sec.5):

  (A) Los 12 `ff_desconocido_por_el_binario`. worker9 no los movio a proposito,
      porque clasificar por el NOMBRE es justo el error que su informe corrige
      (t.122, corolario). Aqui se pregunta al ffmpeg de Linux, que es quien los
      conoce: `-devices`, `-demuxers`, `-muxers`.

  (B) Los 13 que el ffmpeg de Windows rechaza con AVERROR_ENCODER_NOT_FOUND.
      `firmas-cierre.md` 8.2 los deja como deuda de RECURSO EXTERNO ("otra build
      de ffmpeg con mas codificadores, cuyo coste no esta medido"). Hay una build
      distinta YA en la maquina y sin descargar nada: la del contenedor
      (ffmpeg 8.1.1-4 de Debian, frente a N-121159 en Windows).

  (C) `oeb` con Calibre, LISTANDO el directorio. C28 lo clasifico "el motor escribe
      un directorio" y esa palabra es una INFERENCIA de su clasificador: lo unico
      registrado era `rc=0` y ausencia de fichero regular, porque el arnes solo
      miraba `os.path.isfile`.

El tope va DENTRO del contenedor (`timeout N`), no alrededor del cliente: un tope
que solo mata al cliente de Docker no es un tope (CLAUDE.md sec.3).

ESCRIBE unicamente en este directorio.
"""
import os, json, subprocess, time

AQUI = os.path.dirname(os.path.abspath(__file__))
CONT = "filex-convertx"
DEVNULL = subprocess.DEVNULL

DESCONOCIDOS = ["alsa", "awb", "fbdev", "iec61883", "jack", "kmsgrab", "oss", "pp",
                "pulse", "sndio", "video4linux2", "x11grab"]
SIN_ENCODER = ["ac4", "aea", "avs3", "bit", "cavsvideo", "codec2", "codec2raw", "evc",
               "gsm", "ilbc", "oma", "vc1", "vc1test"]


def dentro(sh, tope=60):
    """docker exec con el tope DENTRO del contenedor."""
    args = ["docker", "exec", CONT, "sh", "-c", "timeout %d %s" % (tope, sh)]
    t0 = time.perf_counter()
    try:
        p = subprocess.run(args, stdin=DEVNULL, capture_output=True, text=True,
                           timeout=tope + 20, errors="replace")
        return p.returncode, p.stdout, (p.stderr or "")[-1500:], (time.perf_counter() - t0) * 1000
    except subprocess.TimeoutExpired:
        return -9, "", "TIMEOUT_CLIENTE", (time.perf_counter() - t0) * 1000


def listas():
    """Los tres catalogos del ffmpeg de Linux, parseados por el NOMBRE de la columna."""
    out = {}
    for cual, orden in (("devices", "ffmpeg -hide_banner -devices"),
                        ("demuxers", "ffmpeg -hide_banner -demuxers"),
                        ("muxers", "ffmpeg -hide_banner -muxers"),
                        ("encoders", "ffmpeg -hide_banner -encoders")):
        rc, so, se, ms = dentro(orden + " 2>/dev/null")
        filas = {}
        for ln in so.splitlines():
            if not ln.startswith(" ") or ln.strip().startswith("---") or "=" in ln[:12]:
                continue
            partes = ln.strip().split(None, 1)
            if len(partes) < 2:
                continue
            flags, resto = partes[0], partes[1]
            nom = resto.split(None, 1)[0]
            for alias in nom.split(","):
                filas[alias] = flags
        out[cual] = filas
        print("  %-9s %d entradas (rc=%s)" % (cual, len(filas), rc), flush=True)
    return out


if __name__ == "__main__":
    res = {"contenedor": CONT}
    rc, so, se, ms = dentro("ffmpeg -version | head -1")
    res["ffmpeg_dentro"] = so.strip()
    print("ffmpeg dentro: %s\n" % so.strip(), flush=True)

    print("(A) catalogos del ffmpeg de Linux:", flush=True)
    cat = listas()

    print("\n(A) los 12 `ff_desconocido_por_el_binario`:", flush=True)
    a = {}
    for t in DESCONOCIDOS:
        fila = {"en_devices": cat["devices"].get(t), "en_demuxers": cat["demuxers"].get(t),
                "en_muxers": cat["muxers"].get(t)}
        if fila["en_devices"] is not None:
            fila["veredicto"] = "dispositivo"
        elif fila["en_demuxers"] is not None or fila["en_muxers"] is not None:
            fila["veredicto"] = "formato de fichero"
        else:
            fila["veredicto"] = "tampoco lo conoce esta build"
        a[t] = fila
        print("  %-14s devices=%-4s demuxers=%-4s muxers=%-4s -> %s"
              % (t, fila["en_devices"], fila["en_demuxers"], fila["en_muxers"],
                 fila["veredicto"]), flush=True)
    res["desconocidos"] = a

    print("\n(B) los 13 sin codificador en el ffmpeg de Windows:", flush=True)
    b = {}
    for t in SIN_ENCODER:
        fila = {"en_muxers": cat["muxers"].get(t), "en_encoders": cat["encoders"].get(t)}
        b[t] = fila
        print("  %-11s muxers=%-5s encoders=%-6s" % (t, fila["en_muxers"], fila["en_encoders"]),
              flush=True)
    res["sin_encoder"] = b

    print("\n(C) oeb con Calibre, LISTANDO el directorio:", flush=True)
    prep = ("rm -rf /tmp/c50 && mkdir -p /tmp/c50 && cd /tmp/c50 && "
            "printf 'C50 worker10\\n' > x.txt && "
            "ebook-convert x.txt x.epub >/dev/null 2>&1 && ls -la")
    rc, so, se, ms = dentro(prep, 120)
    print("  preparar epub: rc=%s\n%s" % (rc, so[-400:]), flush=True)
    orden = ("cd /tmp/c50 && rm -rf salida* && ebook-convert x.epub salida.oeb; "
             "echo RC=$?; echo '--- find ---'; find . -newer x.epub | head -40; "
             "echo '--- tipo de salida.oeb ---'; "
             "if [ -d salida.oeb ]; then echo DIRECTORIO; ls -la salida.oeb | head -20; "
             "elif [ -f salida.oeb ]; then echo FICHERO; stat -c '%s bytes' salida.oeb; "
             "else echo NO_EXISTE; fi")
    rc, so, se, ms = dentro(orden, 180)
    print(so[-1800:], flush=True)
    res["oeb"] = {"rc_cliente": rc, "salida": so[-4000:], "stderr": se[-800:], "ms": round(ms, 1),
                  "orden": orden}

    json.dump(res, open(os.path.join(AQUI, "contenedor.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False, sort_keys=True)
    print("\nescrito contenedor.json")

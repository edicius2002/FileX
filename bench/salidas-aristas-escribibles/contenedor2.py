# -*- coding: utf-8 -*-
"""C50 / worker10 - Contenedor, segunda version. Corrige DOS defectos MIOS.

DEFECTO 1 (arnes): `contenedor.py` compone el tope como `sh -c "timeout N <orden>"`,
y cuando `<orden>` empieza por un BUILTIN (`cd /tmp/c50 && ...`) `timeout` intenta
ejecutar `cd` como binario y devuelve **127**. La celda de `oeb` publico
`RC=127 ... NO_EXISTE`, que se lee exactamente igual que "Calibre no esta en el
contenedor" -- y Calibre si esta: la orden anterior, que empezaba por `rm`, escribio
un epub de 20 721 B. Es la t.25 en el nivel del arnes: dos causas distintas con la
misma pinta. Se corrige invocando `timeout N sh -c '<orden>'`.

DEFECTO 2 (sonda): la pregunta (B) se contesto MIRANDO `-encoders`, y devolvio `None`
en 13 de 13 -- que es justo la firma de una sonda rota (t.66). Aqui va con su control
positivo (`aac`, `libx264`, `pcm_s16le` tienen que salir) y, sobre todo, **se ejecuta
en vez de deducirse**: los 13 se intentan escribir DENTRO del contenedor con la misma
escalera que en Windows.

ESCRIBE unicamente en este directorio.
"""
import os, json, subprocess, time

AQUI = os.path.dirname(os.path.abspath(__file__))
CONT = "filex-convertx"
DEVNULL = subprocess.DEVNULL

SIN_ENCODER = ["ac4", "aea", "avs3", "bit", "cavsvideo", "codec2", "codec2raw", "evc",
               "gsm", "ilbc", "oma", "vc1", "vc1test"]
# los que en Windows tampoco se cerraron por otra via
SUBTITULOS = ["jacosub", "mcc", "microdvd", "scc", "sup"]
CONTROL_ENC = ["aac", "libx264", "pcm_s16le", "flac"]


def dentro(sh, tope=60):
    """El tope va DENTRO del contenedor y envuelve un `sh`, no un builtin suelto."""
    args = ["docker", "exec", CONT, "timeout", str(tope), "sh", "-c", sh]
    t0 = time.perf_counter()
    try:
        p = subprocess.run(args, stdin=DEVNULL, capture_output=True, text=True,
                           timeout=tope + 20, errors="replace")
        return p.returncode, p.stdout, (p.stderr or "")[-2000:], (time.perf_counter() - t0) * 1000
    except subprocess.TimeoutExpired:
        return -9, "", "TIMEOUT_CLIENTE", (time.perf_counter() - t0) * 1000


if __name__ == "__main__":
    res = {"contenedor": CONT}

    # --- control positivo del arnes: el mismo gesto que dio 127
    rc, so, se, ms = dentro("cd /tmp && echo VIVO_DESDE_UN_BUILTIN")
    print("control del arnes (orden que empieza por builtin): rc=%s  %s" % (rc, so.strip()), flush=True)
    res["control_arnes"] = {"rc": rc, "salida": so.strip()}
    assert "VIVO" in so, "el arnes sigue roto"

    # --- control positivo de la sonda de encoders (t.66)
    rc, so, se, ms = dentro("ffmpeg -hide_banner -encoders 2>/dev/null")
    enc = set()
    for ln in so.splitlines():
        p = ln.strip().split(None, 1)
        if len(p) == 2 and not ln.strip().startswith("---") and "=" not in p[0]:
            enc.add(p[1].split(None, 1)[0])
    ctrl = {c: (c in enc) for c in CONTROL_ENC}
    print("control de la sonda de encoders: %s  (total %d)" % (ctrl, len(enc)), flush=True)
    res["control_sonda_encoders"] = {"control": ctrl, "total": len(enc)}
    assert all(ctrl.values()), "la sonda de encoders no ve ni los codificadores de control"

    # --- (B) EJECUTAR los 13 + los 5 de subtitulos dentro del contenedor
    print("\n(B) escribir DENTRO del contenedor lo que el ffmpeg de Windows rechaza:", flush=True)
    prep = ("rm -rf /tmp/c50w && mkdir -p /tmp/c50w && cd /tmp/c50w && "
            "ffmpeg -nostdin -y -f lavfi -i testsrc=size=352x288:rate=25:duration=1 "
            "-f lavfi -i sine=frequency=440:duration=1:sample_rate=48000 "
            "-c:v libx264 -pix_fmt yuv420p -c:a pcm_s16le -shortest s_cif.mp4 >/dev/null 2>&1 && "
            "ffmpeg -nostdin -y -f lavfi -i sine=frequency=440:duration=1:sample_rate=48000 "
            "-ac 2 s48.wav >/dev/null 2>&1 && "
            "printf '1\\n00:00:00,000 --> 00:00:02,000\\nFILEXSENTINELA C50\\n\\n' > s.srt && "
            "ls -la")
    rc, so, se, ms = dentro(prep, 120)
    print("  semillas dentro: rc=%s (%d lineas)" % (rc, len(so.splitlines())), flush=True)
    res["semillas_dentro"] = {"rc": rc, "ls": so[-700:]}

    b = {}
    for tok in SIN_ENCODER + SUBTITULOS:
        sem = "s.srt" if tok in SUBTITULOS else ("s48.wav" if tok in
              ("ac4", "aea", "bit", "codec2", "codec2raw", "gsm", "ilbc", "oma") else "s_cif.mp4")
        orden = ("cd /tmp/c50w && rm -f m.%s && "
                 "ffmpeg -nostdin -y -i %s -f %s m.%s 2>err.txt; echo RC=$?; "
                 "if [ -f m.%s ]; then stat -c 'BYTES=%%s' m.%s; else echo BYTES=-1; fi; "
                 "grep -iE 'Encoder not found|experimental|Error while opening encoder|"
                 "does not contain|only|must be|supported are|Unsupported' err.txt | head -2"
                 % (tok, sem, tok, tok, tok, tok))
        rc, so, se, ms = dentro(orden, 40)
        d = {"semilla": sem, "salida": so.strip()[:600], "ms": round(ms, 1)}
        for ln in so.splitlines():
            if ln.startswith("RC="):
                d["rc"] = int(ln[3:])
            if ln.startswith("BYTES="):
                d["bytes"] = int(ln[6:])
        d["ok"] = (d.get("rc") == 0 and d.get("bytes", -1) > 0)
        d["mensaje"] = " | ".join(l for l in so.splitlines()
                                  if not l.startswith(("RC=", "BYTES=")))[:300]
        b[tok] = d
        print("  %-11s %-11s rc=%-4s bytes=%-9s %s"
              % (tok, sem, d.get("rc"), d.get("bytes"),
                 "ESCRITO" if d["ok"] else d["mensaje"][:90]), flush=True)
    res["ejecucion_dentro"] = b
    esc = sum(1 for v in b.values() if v["ok"])
    print("\n  escritos dentro del contenedor: %d de %d" % (esc, len(b)), flush=True)

    # --- (C) oeb, ahora de verdad
    print("\n(C) oeb con Calibre, listando el directorio:", flush=True)
    orden = ("cd /tmp/c50 && rm -rf salida.oeb && ls > /tmp/c50/_antes.txt; "
             "ebook-convert x.epub salida.oeb > /tmp/c50/_conv.log 2>&1; echo RC=$?; "
             "echo '--- nuevos ---'; ls | grep -v -x -F -f /tmp/c50/_antes.txt; "
             "echo '--- que es salida.oeb ---'; "
             "if [ -d salida.oeb ]; then echo DIRECTORIO; ls -la salida.oeb; "
             "elif [ -f salida.oeb ]; then echo FICHERO; stat -c '%s bytes' salida.oeb; "
             "else echo NO_EXISTE; fi; "
             "echo '--- cola del log ---'; tail -6 /tmp/c50/_conv.log")
    rc, so, se, ms = dentro(orden, 180)
    print(so[-1500:], flush=True)
    res["oeb"] = {"rc_cliente": rc, "salida": so[-4000:], "stderr": se[-600:],
                  "ms": round(ms, 1), "orden": orden}

    # --- msgconvert / eml: comprobar si el motor EXISTE, aqui y en la maquina
    rc, so, se, ms = dentro("command -v msgconvert || echo AUSENTE")
    res["msgconvert_en_contenedor"] = so.strip()
    print("\nmsgconvert en el contenedor: %s" % so.strip(), flush=True)

    json.dump(res, open(os.path.join(AQUI, "contenedor2.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False, sort_keys=True)
    print("\nescrito contenedor2.json")

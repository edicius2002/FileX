"""H2 — ¿qué `rc` devuelve ffmpeg en cada caso, y con qué destino de sonda?

Sin shell y con `stdin=DEVNULL`, que es como lo invoca FileX. El `rc` es la
respuesta (trampa 72), así que hay que saber cuál es de verdad y no el que
devuelve una tubería de Git Bash.
"""
import json
import os
import subprocess
import sys
import tempfile

FF = "ffmpeg"
BASE = ["-hide_banner", "-nostdin", "-y", "-f", "lavfi",
        "-i", "testsrc=size=64x64:rate=25", "-frames:v", "1"]


def corre(argv):
    r = subprocess.run([FF] + argv, stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=60)
    return r.returncode, r.stdout.decode("utf-8", "replace")


def main():
    tmp = tempfile.mkdtemp(prefix="h2-rc-")
    filas = []
    destinos = [
        ("null_guion", ["-f", "null", "-"]),
        ("null_NUL", ["-f", "null", "NUL"]),
        ("null_devnull", ["-f", "null", os.devnull]),
        ("fichero_mkv", ["-f", "matroska", os.path.join(tmp, "s.mkv")]),
    ]
    for codec in ("hevc_nvenc", "av1_nvenc", "h264_nvenc", "libx265", "libsvtav1"):
        for nombre, dst in destinos:
            argv = BASE + ["-c:v", codec] + dst
            try:
                rc, txt = corre(argv)
            except subprocess.TimeoutExpired:
                rc, txt = "timeout", ""
            ruta = dst[-1]
            bytes_ = os.path.getsize(ruta) if os.path.isfile(ruta) else None
            clave = "No capable devices found" in txt or "Codec not supported" in txt
            filas.append({"codec": codec, "destino": nombre, "rc": rc,
                          "bytes": bytes_,
                          "dice_no_capable": clave,
                          "ultima": (txt.strip().splitlines() or [""])[-1][:90]})
            print(f"{codec:12s} {nombre:14s} rc={rc!s:>5s} bytes={bytes_} "
                  f"no_capable={clave}  | {filas[-1]['ultima']}")
    salida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sonda_rc.json")
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(filas, f, ensure_ascii=False, indent=1)
    print("\n-> " + salida)
    print("python:", sys.version.split()[0], "| tmp:", tmp)


if __name__ == "__main__":
    main()

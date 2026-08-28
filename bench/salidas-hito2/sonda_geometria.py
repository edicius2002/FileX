"""H2 — la GEOMETRIA de la sonda decide si NVENC dice que funciona.

Con 64x64, `hevc_nvenc` y `h264_nvenc` —que SI funcionan en esta tarjeta—
devuelven rc=-22. No es el numero de fotogramas (barrido de 1 a 25: identico).
Aqui se barre el tamano para encontrar el minimo, y se comprueba que
`av1_nvenc` falla con OTRO codigo (AVERROR_EXTERNAL) a cualquier tamano.
"""
import json
import os
import subprocess

FF = "ffmpeg"
AVERROR_EXTERNAL = -542398533


def corre(codec, tam, n=8):
    argv = [FF, "-hide_banner", "-nostdin", "-y", "-f", "lavfi",
            "-i", f"testsrc=size={tam}:rate=25", "-frames:v", str(n),
            "-c:v", codec, "-f", "null", os.devnull]
    r = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=60)
    rc = r.returncode
    if rc > 2 ** 31:
        rc -= 2 ** 32
    txt = r.stdout.decode("utf-8", "replace")
    return rc, txt


TAMANOS = ["16x16", "32x32", "48x48", "64x64", "96x96", "128x128", "144x144",
           "160x160", "176x144", "192x192", "256x256", "320x240"]


def main():
    filas = []
    for codec in ("hevc_nvenc", "h264_nvenc", "av1_nvenc"):
        for tam in TAMANOS:
            rc, txt = corre(codec, tam)
            no_cap = ("No capable devices found" in txt) or ("Codec not supported" in txt)
            filas.append({"codec": codec, "tam": tam, "rc": rc, "no_capable": no_cap,
                          "external": rc == AVERROR_EXTERNAL, "ok": rc == 0})
            marca = "OK " if rc == 0 else ("EXT" if rc == AVERROR_EXTERNAL else "err")
            print(f"{codec:12s} {tam:9s} rc={rc:12d} {marca} no_capable={no_cap}")
        print()
    salida = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "sonda_geometria.json")
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(filas, f, ensure_ascii=False, indent=1)
    print("->", salida)


if __name__ == "__main__":
    main()

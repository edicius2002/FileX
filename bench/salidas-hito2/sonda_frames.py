"""H2 — ¿cuántos fotogramas necesita una sonda de NVENC para no dar falso negativo?

La trampa 52 obliga a poner el tope DENTRO de la orden (`-frames:v N`). Con N=1
`hevc_nvenc` —que SI funciona— devuelve rc=-22, indistinguible de una averia.
Aqui se busca el N minimo y se comprueba que el mensaje de NVENC («No capable
devices found») separa las dos cosas a cualquier N.
"""
import json
import os
import subprocess
import time

FF = "ffmpeg"
AVERROR_EXTERNAL = -542398533


def corre(codec, n, tam="64x64"):
    argv = [FF, "-hide_banner", "-nostdin", "-y", "-f", "lavfi",
            "-i", f"testsrc=size={tam}:rate=25", "-frames:v", str(n),
            "-c:v", codec, "-f", "null", os.devnull]
    t0 = time.perf_counter_ns()
    r = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=60)
    ms = (time.perf_counter_ns() - t0) / 1e6
    txt = r.stdout.decode("utf-8", "replace")
    rc = r.returncode
    if rc > 2 ** 31:
        rc -= 2 ** 32
    return rc, ms, txt


def main():
    filas = []
    for codec in ("hevc_nvenc", "h264_nvenc", "av1_nvenc"):
        for n in (1, 2, 3, 4, 5, 8, 16, 25):
            rc, ms, txt = corre(codec, n)
            no_cap = ("No capable devices found" in txt) or ("Codec not supported" in txt)
            filas.append({"codec": codec, "frames": n, "rc": rc,
                          "ms": round(ms, 1), "no_capable": no_cap,
                          "es_external": rc == AVERROR_EXTERNAL})
            print(f"{codec:12s} frames={n:3d} rc={rc:12d} {ms:7.1f} ms "
                  f"no_capable={no_cap}")
        print()
    salida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sonda_frames.json")
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(filas, f, ensure_ascii=False, indent=1)
    print("->", salida)


if __name__ == "__main__":
    main()

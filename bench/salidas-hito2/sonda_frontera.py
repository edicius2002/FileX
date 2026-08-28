"""H2 — la frontera EXACTA de geometria de cada codificador NVENC."""
import json
import os
import subprocess

FF = "ffmpeg"


def rc_de(codec, w, h, n=8):
    argv = [FF, "-hide_banner", "-nostdin", "-y", "-f", "lavfi",
            "-i", f"testsrc=size={w}x{h}:rate=25", "-frames:v", str(n),
            "-c:v", codec, "-f", "null", os.devnull]
    r = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=60)
    rc = r.returncode
    return rc - 2 ** 32 if rc > 2 ** 31 else rc


def busca(codec, fijo, eje):
    """Minimo del eje pedido dejando el otro en `fijo` (holgado)."""
    lo, hi = 1, 400
    while lo < hi:
        mid = (lo + hi) // 2
        w, h = (mid, fijo) if eje == "w" else (fijo, mid)
        if rc_de(codec, w, h) == 0:
            hi = mid
        else:
            lo = mid + 1
    return lo


def main():
    out = {}
    for codec in ("hevc_nvenc", "h264_nvenc"):
        w_min = busca(codec, 400, "w")
        h_min = busca(codec, 400, "h")
        out[codec] = {"ancho_min": w_min, "alto_min": h_min}
        print(f"{codec:12s} ancho_min={w_min}  alto_min={h_min}")
        # comprobacion cruzada: el minimo justo y uno por debajo
        for w, h in ((w_min, h_min), (w_min - 1, h_min), (w_min, h_min - 1)):
            print(f"    {w}x{h} -> rc={rc_de(codec, w, h)}")
    salida = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "sonda_frontera.json")
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("->", salida)


if __name__ == "__main__":
    main()

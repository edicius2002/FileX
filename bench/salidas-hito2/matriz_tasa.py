"""H2 — la tabla `_TASA` de `motores.py`, SONDEADA en ejecucion.

Degradar `av1_nvenc` a `libsvtav1` cambiando solo el nombre del codec produce
`Max Bitrate only supported with CRF mode` y un fichero de 0 bytes. La tabla
que arregla eso no puede deducirse de la documentacion de cuatro proyectos
distintos: se ejecutan las 2 x N celdas y se registra el `rc` de cada una.
"""
import json
import os
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)
from filex import gpu, motores  # noqa: E402

ENT = os.path.join(RAIZ, "corpus", "video", "trivial.mp4")


def corre(argv):
    r = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=300)
    rc = r.returncode
    return (rc - 2 ** 32 if rc > 2 ** 31 else rc,
            r.stdout.decode("utf-8", "replace"))


def main():
    tmp = tempfile.mkdtemp(prefix="h2-tasa-")
    filas = []
    with gpu.Lock("H2-matriz-tasa"):
        for cv, fam in sorted(motores.FAMILIA_TASA.items()):
            por_b, por_q = motores._TASA[fam]
            for modo, flags in (("bitrate", por_b(2000000)), ("calidad", por_q(30))):
                sal = os.path.join(tmp, f"{cv}_{modo}.mkv")
                argv = (["ffmpeg", "-hide_banner", "-nostdin", "-y", "-threads", "4",
                         "-i", ENT, "-map", "0", "-c:v", cv] + flags +
                        ["-f", "matroska", sal])
                rc, txt = corre(argv)
                b = os.path.getsize(sal) if os.path.isfile(sal) else 0
                # `rc=0` NO basta: la trampa 23/25 del proyecto. Un fichero de
                # 0 bytes con rc=0 seria un exito declarado sobre nada.
                ok = rc == 0 and b > 0
                err = ""
                if not ok:
                    for ln in txt.splitlines():
                        if "rror" in ln or "Svt[error]" in ln:
                            err = ln.strip()[:110]
                            break
                filas.append({"codec": cv, "familia": fam, "modo": modo,
                              "rc": rc, "bytes": b, "ok": ok,
                              "flags": flags, "error": err})
                print(f"{cv:12s} {modo:8s} rc={rc:12d} bytes={b:>9} "
                      f"{'OK' if ok else 'FALLO'}  {err}")
    salida = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "matriz_tasa.json")
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(filas, f, ensure_ascii=False, indent=1)
    buenas = sum(1 for x in filas if x["ok"])
    print(f"\n{buenas} de {len(filas)} celdas OK")
    print("->", salida)


if __name__ == "__main__":
    main()

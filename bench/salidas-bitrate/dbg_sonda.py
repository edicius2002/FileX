"""Sonda mínima: ¿qué ve el verificador del bitrate de VÍDEO?

N24, paso 0. Antes de escribir una regla hay que saber si el dato existe.
La regla de audio del contrato lee `pista["bitrate_bps"]`; nadie ha comprobado
que la sonda lo publique para las pistas de vídeo, ni en qué contenedores.

Uso: python bench/salidas-bitrate/dbg_sonda.py <dir_trabajo>
"""
import json
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)
from filex import verificador  # noqa: E402

FF = "ffmpeg"
ENTRADA = os.path.join(RAIZ, "corpus", "video", "trivial.mp4")


def main():
    trabajo = sys.argv[1]
    os.makedirs(trabajo, exist_ok=True)
    filas = []
    for ext in ("mp4", "mkv", "webm", "mov"):
        codec = "libvpx-vp9" if ext == "webm" else "libx264"
        dst = os.path.join(trabajo, f"p_{ext}.{ext}")
        extra = ("-c:a", "libopus") if ext == "webm" else ()
        argv = [FF, "-hide_banner", "-nostdin", "-y", "-i", ENTRADA,
                "-map", "0", "-t", "5", "-c:v", codec, "-b:v", "1000000",
                *extra, dst]
        rc = subprocess.run(argv, stdin=subprocess.DEVNULL, timeout=300,
                            capture_output=True).returncode
        fila = {"ext": ext, "codec": codec, "rc": rc,
                "bytes": os.path.getsize(dst) if os.path.exists(dst) else 0}
        if fila["bytes"]:
            s = verificador.sondear(dst)
            fila["duracion_s"] = s.get("duracion_s")
            fila["bitrate_contenedor"] = s.get("bitrate_bps")
            fila["pistas"] = [{"tipo": p.get("tipo"), "codec": p.get("codec"),
                               "bitrate_bps": p.get("bitrate_bps")}
                              for p in s.get("pistas", [])]
        filas.append(fila)
    print(json.dumps(filas, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

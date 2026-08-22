"""Cabo 5 — La ventana TOCTOU real de FileX, medida.

Tres preguntas:

  (A) ¿Cuanto tiempo tiene la entrada abierta un motor externo? Es decir, cuanto dura la
      ventana entre «la ruta esta validada» y «ya nadie puede cambiarla por otra cosa».
      Sonda: intentar `os.replace()` sobre la entrada cada pocos ms. Mientras ffmpeg la
      tiene abierta, en Windows el renombrado FALLA; el primer exito marca el cierre.

  (B) ¿Cuanto cuesta la mitigacion (R8: copiar a un staging privado) frente a convertir?
      Se mide `shutil.copyfile` y la conversion equivalente sobre tres tamanos.

  (C) ¿Sirve la alternativa POSIX (`O_NOFOLLOW`, `dir_fd=`, descriptor abierto +
      `st_dev`/`st_ino`) en lugar del staging? Se comprueba que existe en esta plataforma.

Nada de esto toca `corpus/`: todo se copia antes a un directorio de trabajo.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path

RAIZ = Path("D:/Work/research/FileX")
SALIDA = RAIZ / "bench/salidas-mcp-cabos"
TRABAJO = SALIDA / "cabo5_trabajo"
STAGING = SALIDA / "cabo5_staging"


def ff(cmd, timeout=1800):
    t0 = time.time()
    p = subprocess.Popen(["ffmpeg", "-nostdin", "-y", *cmd],
                         stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for f in (p.stdout, p.stderr):
        threading.Thread(target=lambda f=f: f.read(), daemon=True).start()
    p.wait(timeout=timeout)
    return round((time.time() - t0) * 1000, 1), p.returncode, p


# ---------------------------------------------------------------- (A) la ventana
def ventana(nombre, entrada: Path, args_ffmpeg, salida: Path, timeout=1800):
    """Mide cuanto tiempo el motor externo mantiene la entrada inmovilizada."""
    señuelo = entrada.with_suffix(entrada.suffix + ".swap")
    reg = {"caso": nombre, "entrada": entrada.name,
           "bytes_entrada": entrada.stat().st_size}

    estado = {"t_primer_bloqueo": None, "t_liberada": None, "intentos": 0,
              "renombrado_en_caliente": False}
    parar = threading.Event()

    def sonda():
        t0 = time.time()
        bloqueada = False
        while not parar.is_set():
            estado["intentos"] += 1
            try:
                os.replace(entrada, señuelo)          # ¿puedo cambiarla por otra cosa?
                os.replace(señuelo, entrada)          # la dejo como estaba
                if bloqueada and estado["t_liberada"] is None:
                    estado["t_liberada"] = time.time() - t0
                    return
            except OSError:
                if not bloqueada:
                    bloqueada = True
                    estado["t_primer_bloqueo"] = time.time() - t0
            time.sleep(0.005)

    t0 = time.time()
    p = subprocess.Popen(["ffmpeg", "-nostdin", "-y", "-i", str(entrada),
                          *args_ffmpeg, str(salida)],
                         stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    h = threading.Thread(target=sonda, daemon=True)
    h.start()
    for f in (p.stdout, p.stderr):
        threading.Thread(target=lambda f=f: f.read(), daemon=True).start()
    p.wait(timeout=timeout)
    reg["ms_conversion_total"] = round((time.time() - t0) * 1000, 1)
    reg["returncode"] = p.returncode
    time.sleep(0.05)
    parar.set()
    h.join(timeout=5)
    reg["ms_hasta_primer_bloqueo"] = (round(estado["t_primer_bloqueo"] * 1000, 1)
                                      if estado["t_primer_bloqueo"] is not None else None)
    reg["ms_entrada_inmovilizada"] = (
        round((estado["t_liberada"] - estado["t_primer_bloqueo"]) * 1000, 1)
        if estado["t_liberada"] is not None and estado["t_primer_bloqueo"] is not None
        else None)
    reg["ms_hasta_liberada"] = (round(estado["t_liberada"] * 1000, 1)
                                if estado["t_liberada"] is not None else None)
    reg["intentos_de_sustitucion"] = estado["intentos"]
    reg["se_pudo_sustituir_en_caliente"] = estado["t_primer_bloqueo"] is None
    reg["bytes_salida"] = salida.stat().st_size if salida.exists() else None
    return reg


# ------------------------------------------------- (B) coste de copiar al staging
def coste_staging(entrada: Path, repeticiones=5):
    STAGING.mkdir(parents=True, exist_ok=True)
    ms = []
    for i in range(repeticiones):
        destino = STAGING / f"stg_{i}_{entrada.name}"
        t0 = time.time()
        shutil.copyfile(entrada, destino)
        ms.append(round((time.time() - t0) * 1000, 1))
        destino.unlink(missing_ok=True)
    med = sorted(ms)[len(ms) // 2]
    return {"bytes": entrada.stat().st_size, "ms": ms, "ms_mediana": med,
            "MB_s": (round(entrada.stat().st_size / 1e6 / (med / 1000), 1) if med > 0
                     else "por debajo de la resolucion del reloj")}


# ------------------------------------------ (C) alternativas POSIX en esta plataforma
def alternativas_posix():
    d = {"plataforma": sys.platform, "python": sys.version.split()[0]}
    d["O_NOFOLLOW"] = hasattr(os, "O_NOFOLLOW")
    d["O_PATH"] = hasattr(os, "O_PATH")
    d["open_soporta_dir_fd"] = "open" in getattr(os, "supports_dir_fd", set()) \
        or os.open in getattr(os, "supports_dir_fd", set())
    d["stat_soporta_dir_fd"] = os.stat in getattr(os, "supports_dir_fd", set())
    d["supports_dir_fd"] = sorted(f.__name__ for f in getattr(os, "supports_dir_fd", set()))
    d["supports_fd"] = sorted(f.__name__ for f in getattr(os, "supports_fd", set()))
    # ¿st_ino/st_dev son utiles aqui?
    p = TRABAJO / "_prueba_ino.txt"
    p.write_text("x", encoding="utf-8")
    st = os.stat(p)
    d["st_dev"] = st.st_dev
    d["st_ino"] = st.st_ino
    d["st_ino_no_nulo"] = st.st_ino != 0
    # ¿se puede entregar un descriptor abierto a un proceso externo por ruta?
    d["existe_proc_self_fd"] = os.path.exists("/proc/self/fd")
    d["existe_dev_fd"] = os.path.exists("/dev/fd")
    p.unlink(missing_ok=True)
    return d


def main():
    TRABAJO.mkdir(parents=True, exist_ok=True)
    for d in (STAGING,):
        d.mkdir(parents=True, exist_ok=True)

    fuentes = {
        "trivial.png (316 B)": RAIZ / "corpus/imagen/trivial.png",
        "tipico.mp4 (15,5 MB)": RAIZ / "corpus/video/tipico.mp4",
        "fuente_4k.mp4 (122 MB)": RAIZ / "corpus/video/fuente_4k.mp4",
    }
    copias = {}
    for k, v in fuentes.items():
        dst = TRABAJO / v.name
        if not dst.exists() or dst.stat().st_size != v.stat().st_size:
            shutil.copyfile(v, dst)
        copias[k] = dst

    res = {"plataforma": sys.platform}

    # (C) primero, es instantaneo
    res["alternativas_posix"] = alternativas_posix()

    # (B) coste de copiar
    res["coste_staging"] = {k: coste_staging(v) for k, v in copias.items()}

    # (A) la ventana, en tres regimenes
    ventanas = []
    ventanas.append(ventana("tipico.mp4 -> remux (-c copy)", copias["tipico.mp4 (15,5 MB)"],
                            ["-c", "copy"], TRABAJO / "v_remux.mkv"))
    ventanas.append(ventana("tipico.mp4 -> transcodificacion x264 CPU",
                            copias["tipico.mp4 (15,5 MB)"],
                            ["-c:v", "libx264", "-preset", "medium", "-crf", "23",
                             "-c:a", "aac"], TRABAJO / "v_x264.mp4"))
    ventanas.append(ventana("fuente_4k.mp4 -> remux (-c copy)",
                            copias["fuente_4k.mp4 (122 MB)"],
                            ["-c", "copy"], TRABAJO / "v4k_remux.mkv"))
    ventanas.append(ventana("fuente_4k.mp4 -> 720p x264 CPU",
                            copias["fuente_4k.mp4 (122 MB)"],
                            ["-vf", "scale=1280:720", "-c:v", "libx264",
                             "-preset", "veryfast", "-crf", "26", "-c:a", "aac"],
                            TRABAJO / "v4k_720.mp4"))
    ventanas.append(ventana("trivial.png -> webp", copias["trivial.png (316 B)"],
                            [], TRABAJO / "v_trivial.webp"))
    res["ventanas"] = ventanas

    (SALIDA / "cabo5_toctou.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(res["alternativas_posix"], ensure_ascii=False, indent=1))
    print("\n--- coste de copiar al staging ---")
    for k, v in res["coste_staging"].items():
        print(f"  {k:26s} {v['bytes']:>12,} B  mediana {v['ms_mediana']:>8.1f} ms  "
              f"{v['MB_s']} MB/s")
    print("\n--- ventana TOCTOU ---")
    for v in ventanas:
        print(f"  {v['caso']:42s} conversion={v['ms_conversion_total']:>10.1f} ms | "
              f"inmovilizada={v['ms_entrada_inmovilizada']} ms | "
              f"sustituible_en_caliente={v['se_pudo_sustituir_en_caliente']}")


if __name__ == "__main__":
    main()

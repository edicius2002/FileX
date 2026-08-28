"""C28 / paso 6 - LA PRUEBA DE QUE 21 DE LOS 56 NO NECESITAN FATE.

Clasificar por `rc` es una lectura, no una medida (regla del proyecto: sondear
en ejecucion, no deducir). Aqui se coge una muestra de cada clase «arreglable
con la invocacion» y se escribe DE VERDAD, con la restriccion que el formato
pide, dos semillas distintas, y se mira si aparece un marcador estable.

  * `h261`  -> EINVAL porque exige 176x144 o 352x288 exactos
  * `h263`  -> idem, 176x144
  * `dnxhd` -> exige un perfil valido (1080p, 8 bits, tasa de la tabla)
  * `dts`   -> AVERROR_EXPERIMENTAL: `-strict -2`
  * `mlp`   -> idem, y 44,1/48 kHz
  * `thd`   -> idem

Uso:  python bench/salidas-firmas-cierre/_c28_prueba21.py <dir_desechable>
"""
import json
import os
import subprocess
import sys

TIMEOUT = 90

# (formato, [args de fuente], [args de codificacion])  -- DOS semillas por celda
CASOS = [
    ("h261", "video", ["-s", "176x144", "-r", "15", "-c:v", "h261"]),
    ("h263", "video", ["-s", "176x144", "-r", "15", "-c:v", "h263"]),
    ("dnxhd", "video", ["-s", "1920x1080", "-r", "25", "-c:v", "dnxhd",
                        "-b:v", "36M", "-pix_fmt", "yuv422p"]),
    ("dts", "audio", ["-c:a", "dca", "-strict", "-2", "-ar", "48000", "-ac", "2"]),
    ("mlp", "audio", ["-c:a", "mlp", "-strict", "-2", "-ar", "48000", "-ac", "2"]),
    ("thd", "audio", ["-c:a", "truehd", "-strict", "-2", "-ar", "48000", "-ac", "2"]),
]

FUENTES = {
    "video": [("v1", ["-f", "lavfi", "-i", "testsrc=size=1920x1080:rate=25:duration=0.5"]),
              ("v2", ["-f", "lavfi", "-i", "smptebars=size=1920x1080:rate=25:duration=0.9"])],
    "audio": [("a1", ["-f", "lavfi", "-i", "sine=frequency=440:duration=0.5"]),
              ("a2", ["-f", "lavfi", "-i",
                      "anoisesrc=color=white:seed=7:duration=0.9"])],
}


def prefijo_comun(cabs):
    n = min(len(c) for c in cabs)
    i = 0
    while i < n and len({c[i] for c in cabs}) == 1:
        i += 1
    return cabs[0][:i]


def main():
    tmp = os.path.join(sys.argv[1], "c28_21")
    os.makedirs(tmp, exist_ok=True)
    antes = sorted(os.listdir(tmp))
    res = []
    for fmt, modo, cod in CASOS:
        celdas, cabs = [], []
        for nombre, fuente in FUENTES[modo]:
            sal = os.path.join(tmp, "%s_%s.%s" % (fmt, nombre, fmt))
            orden = (["ffmpeg", "-nostdin", "-y"] + fuente + cod +
                     ["-t", "0.5", sal])
            try:
                r = subprocess.run(orden, stdin=subprocess.DEVNULL,
                                   capture_output=True, timeout=TIMEOUT)
                rc, err = r.returncode, r.stderr.decode("utf-8", "replace")[-180:]
            except subprocess.TimeoutExpired:
                rc, err = "timeout", ""
            c = {"semilla": nombre, "rc": rc}
            if os.path.exists(sal) and os.path.getsize(sal) > 0:
                with open(sal, "rb") as fh:
                    cab = fh.read(64)
                cabs.append(cab)
                c["bytes"] = os.path.getsize(sal)
            else:
                c["stderr"] = err
            celdas.append(c)
        fila = {"formato": fmt, "orden": " ".join(cod), "celdas": celdas,
                "escrito": len(cabs)}
        if len(cabs) == 2:
            p = prefijo_comun(cabs)
            fila["prefijo_comun_n"] = len(p)
            fila["prefijo_comun_hex"] = p.hex()
            fila["prefijo_comun_ascii"] = p.decode("latin-1").replace("\x00", ".")
        res.append(fila)
    despues = sorted(os.listdir(tmp))
    print(json.dumps({"desechable_antes": antes, "desechable_despues": despues,
                      "resultados": res}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""H2 / N7 — ¿se excluyen de verdad el lock de Python y el del arnés de shell?

Con CONTROL POSITIVO en las dos direcciones, porque «no detecta nada» no
significa nada si no se ha comprobado antes que el instrumento detecta algo
(`bench/cerrojo-unico.md` §5.2, y la trampa 36).

Se comparan DOS primitivos de Python contra el `set -o noclobber` de
`bench/lib/harness.sh:173`:

  A) `filex.cerrojo.Candado`  — candado de RANGO DE BYTES + mutex con nombre
  B) `filex.gpu.Lock`         — `O_CREAT|O_EXCL`, el mismo que `noclobber`

Y también el coste de cada mitad, y el sobrecoste fijo por fichero de una
conversión de FileX, que es lo que se come la ventaja de NVENC en el lote (B6).
"""
from __future__ import annotations

import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)
from filex import cerrojo, gpu  # noqa: E402
from filex.nucleo import FileX  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))

#: **`bash` A SECAS NO ES EL GIT BASH — MEDIDO, y casi invalida este informe.**
#: Desde Python, `subprocess.run(["bash", ...])` resuelve al `bash.exe` de
#: `System32`, que es el lanzador de **WSL2**: `uname -a` devuelve
#: `Linux ... microsoft-standard-WSL2`, `$BASH_VERSION` sale VACIO y `/mnt`
#: lista `c d wsl`. `shutil.which("bash")` devuelve el de Git
#: (`MINGW64_NT-10.0-19045`, bash 5.3.9), que es el que ejecuta
#: `bench/lib/harness.sh`.
#:
#: Con el equivocado, el control negativo daba «el shell no puede tomar el lock
#: ni con nadie dentro» —cierto, y sobre OTRA MAQUINA— y el positivo salia verde
#: por el motivo equivocado. Es la trampa 38 con el agravante de la 36: la
#: explicacion plausible («los argumentos posicionales de `bash -c` no
#: funcionan aqui») era falsa; lo que pasaba es que el entorno y las rutas de
#: `%TEMP%` no cruzan a la VM, que es justo el limite que el proyecto ya tenia
#: declarado y que aqui aparecio por accidente.
BASH = shutil.which("bash") or "bash"
BASH_WSL = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                        "System32", "bash.exe")


def a_posix(ruta: str) -> str:
    """`C:\\Users\\x` -> `/c/Users/x`.

    **Sin esto el control negativo sale `False` y toda la tabla es basura**
    (MEDIDO: así salió la primera tanda). Los backslashes de una ruta de Windows
    los consume el propio `bash` como escapes, así que el shell escribía en un
    fichero con otro nombre y «no bloqueaba» — que es exactamente la conclusión
    que se buscaba, obtenida por el motivo equivocado. Es la trampa 19 en el
    argumento en vez de en el heredoc.
    """
    r = ruta.replace("\\", "/")
    if len(r) > 1 and r[1] == ":":
        r = "/" + r[0].lower() + r[2:]
    return r


def sh_toma(ruta: str, cual: str = None) -> tuple[bool, str]:
    """Lo que hace `gpu_acquire` en su mitad 1, aislado: `set -o noclobber`.

    No se llama a `gpu_acquire` entero porque espera 15 minutos y hace el censo
    de la tarjeta; lo que se compara es el PRIMITIVO, que es la línea 173.
    """
    # La ruta va por ENTORNO, no como argumento posicional. MEDIDO: en este
    # `bash` de Windows, `bash -c GUION - RUTA` deja `$0=/bin/bash` y `$1`
    # VACIO, así que el guion redirigía a la cadena vacía y devolvía
    # «BLOQUEADO» siempre — con nadie dentro. Es la trampa 38: el arnés
    # reproducía una condición distinta de la que decía, y el control positivo
    # (shell contra shell) salía verde por el motivo equivocado.
    guion = ("if (set -o noclobber; printf '%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n' "
             "sh-testigo $$ $$ bash 0 /tmp > \"$RUTA_LOCK\") 2>/dev/null; "
             "then echo TOMADO; else echo BLOQUEADO; fi")
    env = dict(os.environ, RUTA_LOCK=a_posix(ruta))
    r = subprocess.run([cual or BASH, "-c", guion], stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       env=env, timeout=60)
    out = r.stdout.decode("utf-8", "replace").strip()
    return out == "TOMADO", out


class ShellVivo:
    """Un shell que toma el lock y **sigue vivo** mientras se le mide.

    **Sin esta pieza la medida es otra.** Un `sh_toma` que arranca y termina
    deja un lock cuyo dueño está muerto, y `gpu.Lock` —que implementa la
    recogida de huérfanos del arnés— se lo lleva **con razón**: la respuesta
    «Python no queda bloqueado» sería cierta y no sería la pregunta. Es la
    trampa 38: hay que registrar que la condición se dio, y aquí la condición
    es un dueño VIVO.
    """

    def __init__(self, ruta, cual=None):
        self.ruta, self.cual, self.p = ruta, cual or BASH, None

    def __enter__(self):
        guion = ("if (set -o noclobber; printf '%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n' "
                 "sh-vivo $$ $$ bash.EXE 0 /tmp > \"$RUTA_LOCK\") 2>/dev/null; "
                 "then echo TOMADO; sleep 120; else echo BLOQUEADO; fi")
        env = dict(os.environ, RUTA_LOCK=a_posix(self.ruta))
        self.p = subprocess.Popen([self.cual, "-c", guion],
                                  stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, env=env)
        t0 = time.monotonic()
        while time.monotonic() - t0 < 20:
            if os.path.exists(self.ruta):
                # El winpid escrito es el `$$` de MSYS, que NO es el PID de
                # Windows. Se reescribe el campo 3 con el PID real del proceso
                # que sigue vivo, que es lo que `tasklist` sabe responder — el
                # arnés guarda los dos campos justo por esto.
                c = open(self.ruta, encoding="utf-8").read().rstrip("\n").split("\t")
                if len(c) >= 6:
                    c[2] = str(self.p.pid)
                    c[3] = "bash.exe"
                    with open(self.ruta, "w", encoding="utf-8") as f:
                        f.write("\t".join(c) + "\n")
                return self
            time.sleep(0.05)
        raise RuntimeError("el shell testigo no tomó el lock")

    def __exit__(self, *_e):
        try:
            self.p.kill()
            self.p.wait(timeout=10)
        except Exception:
            pass
        if os.path.exists(self.ruta):
            os.unlink(self.ruta)


def celda(nombre, tomar_py, soltar_py, ruta):
    """Las cuatro esquinas: control positivo, control negativo y las dos
    direcciones de exclusión."""
    fila = {"primitivo": nombre}

    # Control NEGATIVO: con nadie dentro, el shell tiene que poder.
    if os.path.exists(ruta):
        os.unlink(ruta)
    ok, _ = sh_toma(ruta)
    fila["sh_con_nadie"] = ok
    if os.path.exists(ruta):
        os.unlink(ruta)

    # Control POSITIVO: shell contra shell. Si esto no bloquea, el instrumento
    # está roto y cualquier «no bloquea» posterior no significa nada.
    sh_toma(ruta)
    ok, _ = sh_toma(ruta)
    fila["sh_contra_sh"] = not ok
    if os.path.exists(ruta):
        os.unlink(ruta)

    # Dirección 1: Python dentro, shell fuera.
    h = tomar_py(ruta)
    ok, _ = sh_toma(ruta)
    fila["py_dentro_sh_bloqueado"] = not ok
    fila["py_deja_fichero"] = os.path.exists(ruta)
    soltar_py(h)
    if os.path.exists(ruta):
        os.unlink(ruta)

    # Dirección 2: shell VIVO dentro, Python fuera.
    with ShellVivo(ruta):
        h = tomar_py(ruta)
        fila["sh_dentro_py_bloqueado"] = h is None
        if h is not None:
            soltar_py(h)
    if os.path.exists(ruta):
        os.unlink(ruta)

    # Y la variante con el dueño MUERTO, que es un caso distinto y legítimo:
    # el arnés recoge huérfanos a propósito, así que «no bloquea» aquí es la
    # respuesta correcta, no un fallo de exclusión.
    sh_toma(ruta)
    h = tomar_py(ruta)
    fila["sh_muerto_py_pasa"] = h is not None
    if h is not None:
        soltar_py(h)
    if os.path.exists(ruta):
        os.unlink(ruta)

    fila["excluye_de_verdad"] = bool(fila["sh_con_nadie"]
                                     and fila["sh_contra_sh"]
                                     and fila["py_dentro_sh_bloqueado"]
                                     and fila["sh_dentro_py_bloqueado"])
    return fila


def tomar_candado(ruta):
    # `cerrojo.Candado` nombra por clave, no por ruta: se le pasa la ruta como
    # nombre y se le fuerza el directorio para que el fichero sea EL MISMO.
    os.environ["FILEX_CERROJO_DIR"] = os.path.dirname(ruta)
    cerrojo._dir_cache = None
    c = cerrojo.Candado("gpu-comparativa")
    return c if c.tomar(espera=0.5) else None


def tomar_gpulock(ruta):
    gpu._PROFUNDIDAD = 0
    l = gpu.Lock("py-testigo", ruta=ruta)
    return l if l.tomar(espera=0.5) else None


def mide_n7(res):
    tmp = tempfile.mkdtemp(prefix="h2-n7-")
    # El candado de bytes escribe en SU fichero, derivado del nombre; para que
    # la comparación sea sobre EL MISMO fichero se sondea cuál es.
    os.environ["FILEX_CERROJO_DIR"] = tmp
    cerrojo._dir_cache = None
    ruta_candado = cerrojo.fichero("gpu-comparativa")
    ruta_gpu = os.path.join(tmp, "filex-gpu.lock")

    filas = [
        celda("cerrojo.Candado (rango de bytes)",
              lambda _r: tomar_candado(ruta_candado),
              lambda h: h.soltar() if h else None, ruta_candado),
        celda("gpu.Lock (O_CREAT|O_EXCL)", tomar_gpulock,
              lambda h: h.soltar() if h else None, ruta_gpu),
    ]
    for f in filas:
        print(f"  {f['primitivo']:38s} "
              f"sh/nadie={f['sh_con_nadie']!s:5s} "
              f"sh/sh={f['sh_contra_sh']!s:5s} "
              f"py>sh={f['py_dentro_sh_bloqueado']!s:5s} "
              f"sh_vivo>py={f['sh_dentro_py_bloqueado']!s:5s} "
              f"sh_muerto>py_pasa={f['sh_muerto_py_pasa']!s:5s} "
              f"-> EXCLUYE={f['excluye_de_verdad']}")
    res["n7_interop"] = filas

    # La frontera de WSL2, medida a propósito en vez de por accidente.
    if os.path.exists(BASH_WSL):
        if os.path.exists(ruta_gpu):
            os.unlink(ruta_gpu)
        neg, _ = sh_toma(ruta_gpu, BASH_WSL)
        gpu._PROFUNDIDAD = 0
        h = tomar_gpulock(ruta_gpu)
        pos, _ = sh_toma(ruta_gpu, BASH_WSL)
        if h:
            h.soltar()
        if os.path.exists(ruta_gpu):
            os.unlink(ruta_gpu)
        res["n7_wsl2"] = {"bash": BASH_WSL, "sh_con_nadie": neg,
                          "py_dentro_sh_bloqueado": not pos}
        print(f"  [WSL2] {BASH_WSL}: con nadie dentro toma={neg}; "
              f"con Python dentro bloqueado={not pos}")
        print("         (con nadie dentro TAMBIEN da False: la ruta de %TEMP% "
              "no existe en la VM. No es exclusion, es otra maquina.)")

    # Coste del ciclo tomar+soltar, aislado (trampa 36: se mide el trozo, no la
    # diferencia entre dos totales que lo contienen).
    for nombre, fn, ruta in (("gpu.Lock", tomar_gpulock, ruta_gpu),
                             ("cerrojo.Candado", tomar_candado, ruta_candado)):
        xs = []
        for _ in range(21):
            t0 = time.perf_counter_ns()
            h = fn(ruta)
            if h:
                h.soltar()
            xs.append((time.perf_counter_ns() - t0) / 1000)
        res.setdefault("n7_coste_us", {})[nombre] = {
            "n": len(xs), "mediana_us": round(statistics.median(xs), 1),
            "min_us": round(min(xs), 1), "max_us": round(max(xs), 1)}
        print(f"  coste {nombre:18s} mediana {statistics.median(xs):8.1f} us (n=21)")

    # La otra mitad: la guardia. Cuánto cuesta preguntar por la VRAM.
    xs = []
    for _ in range(9):
        t0 = time.perf_counter_ns()
        gpu.vram_libre_mib()
        xs.append((time.perf_counter_ns() - t0) / 1e6)
    res["n7_guardia_ms"] = {"n": 9, "mediana_ms": round(statistics.median(xs), 1),
                            "min_ms": round(min(xs), 1), "max_ms": round(max(xs), 1)}
    print(f"  guardia (nvidia-smi) mediana {statistics.median(xs):.1f} ms (n=9)")

    # Y la recogida de huérfanos: un `O_CREAT|O_EXCL` NO lo suelta el sistema.
    huerf = os.path.join(tmp, "huerfano.lock")
    with open(huerf, "w", encoding="utf-8") as f:
        f.write("muerto\t999999\t999999\tningun_proceso.exe\t0\t/tmp\n")
    gpu._PROFUNDIDAD = 0
    l = gpu.Lock("py-recoge", ruta=huerf)
    t0 = time.perf_counter_ns()
    tomado = l.tomar(espera=0.0)
    ms = (time.perf_counter_ns() - t0) / 1e6
    l.soltar()
    res["n7_huerfano"] = {"recogido": tomado, "ms": round(ms, 1)}
    print(f"  huérfano de un PID muerto: recogido={tomado} en {ms:.1f} ms")

    # Y el control de que NO roba un lock vivo.
    vivo = os.path.join(tmp, "vivo.lock")
    with open(vivo, "w", encoding="utf-8") as f:
        f.write(f"otro\t{os.getpid()}\t{os.getpid()}\t"
                f"{os.path.basename(sys.executable)}\t0\t/tmp\n")
    gpu._PROFUNDIDAD = 0
    l = gpu.Lock("py-no-roba", ruta=vivo)
    res["n7_no_roba_vivo"] = not l.tomar(espera=0.0)
    print(f"  NO roba un lock de dueño vivo: {res['n7_no_roba_vivo']}")

    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("FILEX_CERROJO_DIR", None)
    cerrojo._dir_cache = None


def mide_sobrecoste(res):
    """B6 — ¿dónde se come el lote la ventaja de NVENC?

    Se compara el `ffmpeg` CRUDO contra la conversión ENTERA de FileX sobre el
    mismo clip: staging, desechable, censo del punto 5, contrato y `move`.
    """
    tmp = tempfile.mkdtemp(prefix="h2-over-")
    corpus = os.path.join(RAIZ, "corpus", "video")
    clip = os.path.join(tmp, "clip.mp4")
    subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-y", "-i",
                    os.path.join(corpus, "tipico.mp4"), "-t", "5", "-map", "0",
                    "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
                    "-c:a", "aac", "-b:a", "128k", clip],
                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=600)
    fx = FileX(raices_lectura=[tmp], raices_escritura=[tmp])
    from filex import motores as M
    ff = [c for c in M.MOTORES if c.__name__ == "FFmpeg"][0]()
    ff.sondear()

    filas = {}
    for etiqueta, cpu in (("nvenc", False), ("cpu", True)):
        gpu.olvidar()
        if cpu:
            gpu._CACHE["hevc_nvenc"] = (False, 0, "forzado a CPU")
        pedido = {"codec_video": "hevc", "bitrate_video": "2000k"}

        # (a) ffmpeg crudo
        crudo = os.path.join(tmp, f"crudo_{etiqueta}.mkv")
        argv, _dec = ff.orden(clip, crudo, pedido)
        xs = []
        for _ in range(9):
            if os.path.exists(crudo):
                os.unlink(crudo)
            t0 = time.perf_counter_ns()
            subprocess.run(argv, stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=600)
            xs.append((time.perf_counter_ns() - t0) / 1e6)
        crudo_ms = statistics.median(xs)

        # (b) la conversión entera de FileX
        entero = os.path.join(tmp, f"filex_{etiqueta}.mkv")
        ys = []
        for _ in range(9):
            if os.path.exists(entero):
                os.unlink(entero)
            t0 = time.perf_counter_ns()
            c = fx.convertir(clip, entero, pedido)
            ys.append((time.perf_counter_ns() - t0) / 1e6)
            if not c.ok:
                print("    [!]", c.motivo)
                break
        filex_ms = statistics.median(ys)
        filas[etiqueta] = {"n": 9, "crudo_ms": round(crudo_ms, 1),
                           "filex_ms": round(filex_ms, 1),
                           "sobrecoste_ms": round(filex_ms - crudo_ms, 1),
                           "sobrecoste_pct": round((filex_ms / crudo_ms - 1) * 100, 1)}
        print(f"  {etiqueta:6s} ffmpeg crudo {crudo_ms:8.1f} ms | FileX entero "
              f"{filex_ms:8.1f} ms | fijo +{filex_ms - crudo_ms:7.1f} ms "
              f"(+{(filex_ms / crudo_ms - 1) * 100:.1f} %)")
    gpu.olvidar()
    if "nvenc" in filas and "cpu" in filas:
        g_crudo = filas["cpu"]["crudo_ms"] / filas["nvenc"]["crudo_ms"]
        g_filex = filas["cpu"]["filex_ms"] / filas["nvenc"]["filex_ms"]
        filas["ganancia_crudo"] = round(g_crudo, 3)
        filas["ganancia_filex"] = round(g_filex, 3)
        print(f"  --> ganancia del CODIFICADOR x{g_crudo:.2f}; "
              f"de la CONVERSION x{g_filex:.2f}")
    res["sobrecoste"] = filas
    shutil.rmtree(tmp, ignore_errors=True)


def mide_por_duracion(res):
    """La ganancia de NVENC contra la DURACION del clip.

    El ×8,39 de `HUECOS.md` §4 no dice sobre qué fichero se midió (trampa 68), y
    resulta que sí importa: el arranque de `ffmpeg` y la verificación son costes
    FIJOS, así que cuanto más corto el clip menos se nota la GPU. Un lote de
    clips cortos **diluye** la ventaja en vez de concentrarla.
    """
    tmp = tempfile.mkdtemp(prefix="h2-dur-")
    corpus = os.path.join(RAIZ, "corpus", "video")
    from filex import motores as M
    ff = [c for c in M.MOTORES if c.__name__ == "FFmpeg"][0]()
    ff.sondear()
    pedido = {"codec_video": "hevc", "bitrate_video": "2000k"}
    filas = []
    for dur in (1, 2, 5, 10, 20):
        clip = os.path.join(tmp, f"c{dur}.mp4")
        subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-y", "-i",
                        os.path.join(corpus, "tipico.mp4"), "-t", str(dur),
                        "-map", "0", "-c:v", "libx264", "-crf", "20",
                        "-preset", "veryfast", "-c:a", "aac", "-b:a", "128k",
                        clip], stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=600)
        med = {}
        for etiqueta, cpu in (("nvenc", False), ("cpu", True)):
            gpu.olvidar()
            if cpu:
                gpu._CACHE["hevc_nvenc"] = (False, 0, "forzado a CPU")
            sal = os.path.join(tmp, f"o_{dur}_{etiqueta}.mkv")
            argv, _d = ff.orden(clip, sal, pedido)
            xs = []
            for _ in range(9):
                if os.path.exists(sal):
                    os.unlink(sal)
                t0 = time.perf_counter_ns()
                subprocess.run(argv, stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=900)
                xs.append((time.perf_counter_ns() - t0) / 1e6)
            med[etiqueta] = round(statistics.median(xs), 1)
        g = round(med["cpu"] / med["nvenc"], 2)
        filas.append({"duracion_s": dur, **med, "ganancia": g})
        print(f"  {dur:3d} s  nvenc {med['nvenc']:9.1f} ms  cpu {med['cpu']:10.1f} ms"
              f"  -> x{g}")
    gpu.olvidar()
    res["ganancia_por_duracion"] = filas
    shutil.rmtree(tmp, ignore_errors=True)


def main():
    res = {"cuando": time.strftime("%Y-%m-%d %H:%M:%S")}
    print("=== N7: ¿se excluyen los dos primitivos? ===")
    mide_n7(res)
    print("\n=== B6: dónde se come el lote la ventaja ===")
    with gpu.Lock("H2-sobrecoste"):
        mide_sobrecoste(res)
        print("\n=== B6: la ganancia contra la DURACION de la entrada ===")
        mide_por_duracion(res)
    salida = os.path.join(AQUI, "medicion_n7.json")
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("\n->", salida)
    print("lock libre al terminar:", gpu.esta_libre())


if __name__ == "__main__":
    main()

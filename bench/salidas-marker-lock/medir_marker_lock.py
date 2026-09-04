# -*- coding: utf-8 -*-
"""B3 -- mide `marker` CON EL LOCK DE GPU TOMADO (camino (a) de
`bench/suelo-y-mcp.md` §3.3).

Copia propia de `bench/salidas-suelo-n32/medir_marker.py` (`CLAUDE.md` §1: un
fichero de salida por agente; los arneses ajenos no se editan). Conserva de
aquel la verdad CONOCIDA `ESPERADO` y el evaluador CER, y cambia tres cosas:

1. **Toma el lock de GPU** con `filex.gpu.Lock.tomar()` / `soltar()`, NO con el
   `with`: el `with` llama a `guardia()`, que ejecuta `nvidia-smi` y cuesta
   46,9 ms (trampa 88). La comprobación de VRAM libre se hace UNA vez, explícita
   y declarada, no dentro del camino del lock. `soltar()` va en un `finally`.
2. **No aborta al ver Docker.** Aquel arnés mataba el árbol en cuanto un hijo
   se llamaba `docker*` porque nadie tenía el lock. Aquí el lock está tomado, así
   que se DEJA correr y se mide. Lo que sí se hace es capturar el `--name` del
   contenedor: la orden la construye `surya`, no nosotros, así que no se le puede
   meter el tope DENTRO (`CLAUDE.md` §3) -- la mitigación equivalente es matarlo
   por nombre con `docker rm -f` (trampa 37: `docker kill` FALLA sobre un
   contenedor en estado `Created`, y `docker ps` no lo lista).
3. **Mide VRAM pico** por muestreo de `nvidia-smi --query-gpu=memory.used`, igual
   que `peak_vram` de `bench/lib/harness.sh`. Es el TOTAL de la máquina, nunca
   por PID (trampa 31): se publica la base antes, el pico y el delta.

Los dos testigos de ruido de `CLAUDE.md` §3 (deriva monohilo + nivel por
lanzamiento de proceso), cada uno con su propio tope de 20 s.

    D:\\Work\\research\\FileX\\.venv-marker\\Scripts\\python.exe \\
        bench/salidas-marker-lock/medir_marker_lock.py --etiqueta i1

`.venv-marker` está protegido (`CLAUDE.md` §1): esto sólo EJECUTA lo que ya hay
instalado. `filex` se importa por `sys.path`, sin instalar nada en el venv.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata

import psutil

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)  # para importar `filex.gpu` sin instalar nada
from filex import gpu  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
ENTRADA = os.path.join(RAIZ, "corpus", "pdf", "tipico_texto.pdf")
MARKER_SINGLE = os.path.join(os.path.dirname(sys.executable), "marker_single.exe")

#: prefijo de los contenedores que lanza surya (`surya-vllm-<puerto>`), MEDIDO
#: en `bench/suelo-y-mcp.md` §3.1 -- dos capturas, dos puertos.
PREFIJO_CONTENEDOR = "surya-vllm-"
#: fichero donde surya deja el descriptor del servidor vLLM (puerto, pid,
#: cleanup_id). Segunda fuente del identificador, por si el `--name` no se
#: llegara a ver en la línea de órdenes de ningún hijo.
DESCRIPTOR_VLLM = os.path.join(
    os.path.expanduser("~"), ".cache", "datalab", "surya", "vllm_server.json")

# Verdad CONOCIDA (heredada sin tocar de `medir_marker.py`, confirmada allí
# renderizando el PDF con `magick -density 150`): el PDF fuente tiene el glifo
# de "n~" roto -- se ve como "n" + un circunflejo suelto. Se evalúa lo que el
# documento MUESTRA, no lo que "debería" mostrar.
ESPERADO = [
    "FileX - documento de prueba con texto seleccionable",
    "Segunda linea: acentos aeiou n",
    "y simbolos % & @",
    "Tabla",
    "Col A",
    "Col B",
    "Col C",
]


# --------------------------------------------------------------------------
# Evaluador CER (heredado sin tocar)
# --------------------------------------------------------------------------
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _lev(a, b):
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def evaluar(texto: str) -> dict:
    n = _norm(texto)
    ref = _norm(" ".join(ESPERADO))
    d = _lev(ref, n)
    det = [{"esperado": e, "presente": _norm(e) in n} for e in ESPERADO]
    return {
        "metrica": "ciega-alfanumerica (heredada de medir_marker.py)",
        "cer_pct": round(100 * d / max(1, len(ref)), 2),
        "chars_ref": len(ref),
        "chars_salida": len(n),
        "frases_presentes": sum(1 for x in det if x["presente"]),
        "frases_totales": len(det),
        "detalle": det,
    }


# --------------------------------------------------------------------------
# Instrumentos
# --------------------------------------------------------------------------
TOPE_TESTIGO_S = 20.0  # un testigo que puede tumbar la medición no es un testigo


def testigo_deriva(vueltas: int = 400000) -> float:
    """Bucle monohilo de Python. Detecta la DERIVA dentro de la tanda.

    Ciego a la contención multinúcleo (`CLAUDE.md` §3): por eso va acompañado.
    """
    ini = time.perf_counter()
    x = 0
    for i in range(vueltas):
        x = (x + i * i) % 1000003
    return round((time.perf_counter() - ini) * 1000, 2)


def testigo_nivel() -> tuple[float, bool]:
    """Lanzamiento de proceso (`ffprobe -version`): detecta el NIVEL de carga.

    Devuelve `(ms, agotado)`. Con el tope agotado devuelve el TOPE, no un error:
    la tanda se marca SUCIA y sigue.
    """
    ini = time.perf_counter()
    try:
        subprocess.run(["ffprobe", "-version"], stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=TOPE_TESTIGO_S)
    except subprocess.TimeoutExpired:
        return TOPE_TESTIGO_S * 1000, True
    except OSError:
        return -1.0, False
    return round((time.perf_counter() - ini) * 1000, 2), False


def vram_usada_mib() -> int | None:
    """`memory.used` TOTAL de la máquina. Nunca por PID (trampa 31)."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used",
             "--format=csv,noheader,nounits"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=TOPE_TESTIGO_S)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    try:
        return int(r.stdout.decode("utf-8", "replace").strip().splitlines()[0])
    except (ValueError, IndexError):
        return None


def _docker(*args, tope: float = 60.0) -> tuple[int, str]:
    try:
        r = subprocess.run(["docker", *args], stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=tope)
    except (OSError, subprocess.SubprocessError) as e:
        return -1, "EXCEPCION: %r" % (e,)
    return r.returncode, r.stdout.decode("utf-8", "replace").strip()


def censo_contenedores() -> list[str]:
    """`docker ps -a`, NUNCA `docker ps`: un contenedor `Created` no lo lista
    el segundo (trampa 37)."""
    rc, salida = _docker("ps", "-a", "--format", "{{.Names}}\t{{.Status}}\t{{.Image}}")
    if rc != 0:
        return ["ERROR docker ps -a: %s" % salida]
    return [l for l in salida.splitlines() if l.strip()]


def nombres(censo: list[str]) -> set[str]:
    return {l.split("\t")[0] for l in censo if "\t" in l}


# --------------------------------------------------------------------------
# La medición
# --------------------------------------------------------------------------
def medir(args) -> dict:
    reg: dict = {
        "etiqueta": args.etiqueta,
        "interprete": sys.executable,
        "python": sys.version.split()[0],
        "plataforma": sys.platform,
        "tope_s": args.tope,
    }

    # --- fase 0: preflight ------------------------------------------------
    log("INICIO fase 0 (preflight)")
    reg["deriva_ini_ms"] = testigo_deriva()
    nivel_ms, agotado = testigo_nivel()
    reg["nivel_ini_ms"], reg["nivel_ini_agotado"] = nivel_ms, agotado
    reg["vram_base_mib"] = vram_usada_mib()
    reg["vram_libre_ini_mib"] = gpu.vram_libre_mib()
    censo_antes = censo_contenedores()
    reg["docker_ps_a_antes"] = censo_antes
    reg["entrada_bytes"] = os.path.getsize(ENTRADA) if os.path.isfile(ENTRADA) else None

    if not os.path.isfile(MARKER_SINGLE):
        reg["bloqueo"] = "no existe %s" % MARKER_SINGLE
        return reg
    if not os.path.isfile(ENTRADA):
        reg["bloqueo"] = "no existe %s" % ENTRADA
        return reg
    if reg["entrada_bytes"] != 3219:
        # trampa 34 / 107: un puntero de LFS EXISTE. Se comprueba el TAMAÑO.
        reg["bloqueo"] = ("la entrada mide %s B, no 3219: puntero de Git LFS "
                          "sin descargar (trampas 34 y 107)" % reg["entrada_bytes"])
        return reg
    log("FIN fase 0  vram_base=%s MiB  libre=%s MiB  contenedores=%d"
        % (reg["vram_base_mib"], reg["vram_libre_ini_mib"], len(censo_antes)))

    # --- fase 1: el lock ---------------------------------------------------
    # tomar()/soltar(), NO `with`: el `with` llama a guardia() (nvidia-smi,
    # 46,9 ms -- trampa 88).
    log("INICIO fase 1 (lock)")
    lock = gpu.Lock("B3-marker-%s" % args.etiqueta)
    t0 = time.perf_counter()
    tomado = lock.tomar(espera=args.espera_lock)
    reg["lock_tomar_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    reg["lock_tomado"] = tomado
    reg["lock_ruta"] = lock.ruta
    if not tomado:
        reg["bloqueo"] = ("no se pudo tomar el lock de GPU en %.0f s; dueño: %r"
                          % (args.espera_lock, gpu.dueno()))
        log("FIN fase 1 rc=BLOQUEO %s" % reg["bloqueo"])
        return reg
    log("FIN fase 1 rc=0  lock tomado en %.2f ms" % reg["lock_tomar_ms"])

    desechable = tempfile.mkdtemp(prefix="filex-b3-%s-" % args.etiqueta)
    salida_dir = os.path.join(desechable, "out")
    os.makedirs(salida_dir, exist_ok=True)
    reg["desechable"] = desechable
    # trampa 21: hay motores que escriben en el `cwd`. Se lista antes y después.
    reg["desechable_antes"] = sorted(os.listdir(desechable))

    try:
        reg.update(_correr(args, salida_dir, desechable))
    finally:
        # --- fase 4: limpieza y lock, pase lo que pase ---------------------
        log("INICIO fase 4 (limpieza)")
        reg["vram_fin_mib"] = vram_usada_mib()
        censo_despues = censo_contenedores()
        reg["docker_ps_a_despues"] = censo_despues
        nuevos = sorted(nombres(censo_despues) - nombres(censo_antes))
        reg["contenedores_nuevos"] = nuevos
        # `docker rm -f`, no `docker kill`: sobre un contenedor `Created` el
        # segundo FALLA con rc=1 (trampa 37).
        matados = []
        for n in nuevos:
            if n.startswith(PREFIJO_CONTENEDOR) or args.matar_todo_nuevo:
                rc, sal = _docker("rm", "-f", n)
                matados.append({"nombre": n, "rc": rc, "salida": sal[:300]})
        reg["contenedores_matados"] = matados
        reg["docker_ps_a_final"] = censo_contenedores()
        reg["desechable_despues"] = sorted(os.listdir(desechable))
        reg["deriva_fin_ms"] = testigo_deriva()
        nivel_ms, agotado = testigo_nivel()
        reg["nivel_fin_ms"], reg["nivel_fin_agotado"] = nivel_ms, agotado
        lock.soltar()
        reg["lock_soltado"] = True
        reg["lock_libre_tras_soltar"] = gpu.esta_libre()
        log("FIN fase 4 rc=0  lock_libre=%s  nuevos=%s  matados=%d"
            % (reg["lock_libre_tras_soltar"], nuevos, len(matados)))
        try:
            shutil.rmtree(desechable, ignore_errors=True)
        except OSError:
            pass

    # --- veredicto de ruido -------------------------------------------------
    d0, d1 = reg.get("deriva_ini_ms") or 0, reg.get("deriva_fin_ms") or 0
    n0, n1 = reg.get("nivel_ini_ms") or 0, reg.get("nivel_fin_ms") or 0
    reg["deriva_ratio"] = round(d1 / d0, 3) if d0 else None
    reg["nivel_ratio"] = round(n1 / n0, 3) if n0 > 0 else None
    sucia = []
    if reg["deriva_ratio"] and reg["deriva_ratio"] > 1.5:
        sucia.append("deriva x%.2f" % reg["deriva_ratio"])
    if reg["nivel_ratio"] and reg["nivel_ratio"] > 1.5:
        sucia.append("nivel x%.2f" % reg["nivel_ratio"])
    if reg.get("nivel_ini_agotado") or reg.get("nivel_fin_agotado"):
        sucia.append("testigo de nivel agotó su tope de %.0f s" % TOPE_TESTIGO_S)
    # La sesión remota está activa a propósito: TODO sale SUCIA (CLAUDE.md §3).
    reg["ruido"] = "SUCIA(" + "; ".join(sucia) + ")" if sucia else "SUCIA(sesión remota activa, estructural)"
    return reg


def _correr(args, salida_dir: str, desechable: str) -> dict:
    """Fases 2 y 3: lanza marker y lo vigila. Devuelve su parte del registro."""
    out: dict = {}
    cmd = [MARKER_SINGLE, ENTRADA, "--output_dir", salida_dir,
           "--output_format", "markdown"]
    if args.modo:
        cmd += ["--mode", args.modo]
    out["cmd"] = cmd
    env = dict(os.environ)
    for k, v in (args.env or []):
        env[k] = v
    out["env_extra"] = dict(args.env or [])

    log("INICIO fase 2 (marker)  orden: %s" % " ".join(cmd))
    ini = time.perf_counter()
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace",
                            env=env, cwd=desechable)
    # trampa 93: en Windows el `python.exe` de un venv es un lanzador y
    # `Popen.pid` no es el PID real. `marker_single.exe` es un lanzador de
    # consola de setuptools: se registran los dos PID y se vigila el árbol.
    out["popen_pid"] = proc.pid
    try:
        p = psutil.Process(proc.pid)
    except psutil.NoSuchProcess:
        p = None

    # trampa 83: un `stderr` en PIPE que nadie lee es un tope de 64 KiB.
    lineas: list[str] = []

    def _drenar():
        try:
            for linea in proc.stdout:
                lineas.append(linea)
        except Exception:
            pass

    hilo = threading.Thread(target=_drenar, daemon=True)
    hilo.start()

    pico_rss_mb = 0.0
    pico_vram = out_vram_muestras = 0
    muestras_rss = 0
    vram_serie: list[int] = []
    docker_cmdlines: list[str] = []
    nombres_vistos: set[str] = set()
    tope_alcanzado = False
    ultima_vram = 0.0

    while True:
        ahora = time.perf_counter()
        if p is not None:
            try:
                hijos = p.children(recursive=True)
                total = p.memory_info().rss
                for h in hijos:
                    try:
                        total += h.memory_info().rss
                        if h.name().lower().startswith("docker"):
                            try:
                                cl = " ".join(h.cmdline())
                            except Exception:
                                cl = "(cmdline ilegible)"
                            if cl not in docker_cmdlines:
                                docker_cmdlines.append(cl)
                                log("DOCKER visto: %s" % cl[:400])
                            m = re.search(r"--name\s+(\S+)", cl)
                            if m:
                                nombres_vistos.add(m.group(1))
                    except psutil.Error:
                        pass
                pico_rss_mb = max(pico_rss_mb, total / (1024 * 1024))
                muestras_rss += 1
            except psutil.Error:
                pass
        # VRAM a 1 s: `nvidia-smi` cuesta ~47 ms, muestrearlo a 0,25 s sería
        # gastar el 19 % de un núcleo en el instrumento.
        if ahora - ultima_vram >= 1.0:
            v = vram_usada_mib()
            if v is not None:
                vram_serie.append(v)
                pico_vram = max(pico_vram, v)
            ultima_vram = ahora
        if proc.poll() is not None:
            break
        if ahora - ini > args.tope:
            tope_alcanzado = True
            log("TOPE alcanzado a los %.1f s" % (ahora - ini))
            break
        time.sleep(0.25)

    # --- fase 3: cortar si hace falta --------------------------------------
    if tope_alcanzado or proc.poll() is None:
        # Los hijos PRIMERO: matado el padre, `children()` ya no los encuentra.
        if p is not None:
            try:
                for h in p.children(recursive=True):
                    try:
                        h.kill()
                    except psutil.Error:
                        pass
            except psutil.Error:
                pass
        try:
            proc.kill()
        except OSError:
            pass
    try:
        rc = proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        rc = None
    hilo.join(timeout=5)
    dur = time.perf_counter() - ini

    # Segunda fuente del identificador del contenedor.
    if os.path.isfile(DESCRIPTOR_VLLM):
        try:
            with open(DESCRIPTOR_VLLM, encoding="utf-8") as fh:
                out["descriptor_vllm"] = json.load(fh)
        except (OSError, ValueError) as e:
            out["descriptor_vllm"] = "ilegible: %r" % (e,)
    else:
        out["descriptor_vllm"] = None

    out.update({
        "rc": rc, "duracion_s": round(dur, 2),
        "tope_alcanzado": tope_alcanzado,
        "pico_rss_mb": round(pico_rss_mb, 1), "muestras_rss": muestras_rss,
        "pico_vram_total_mib": pico_vram or None,
        "muestras_vram": len(vram_serie),
        "vram_serie_mib": vram_serie,
        "docker_cmdlines": docker_cmdlines,
        "contenedores_nombrados": sorted(nombres_vistos),
        "stdout_lineas": len(lineas),
        "cola_stdout": "".join(lineas[-80:]),
    })
    log("FIN fase 2 rc=%s dur=%.2f s pico_rss=%.1f MB pico_vram=%s MiB tope=%s"
        % (rc, dur, pico_rss_mb, pico_vram, tope_alcanzado))

    # --- la salida ----------------------------------------------------------
    base = os.path.splitext(os.path.basename(ENTRADA))[0]
    md_path = os.path.join(salida_dir, base, base + ".md")
    out["md_path_esperado"] = md_path
    out["md_existe"] = os.path.isfile(md_path)
    if out["md_existe"]:
        with open(md_path, encoding="utf-8") as fh:
            md = fh.read()
        out["md_bytes"] = len(md.encode("utf-8"))
        out["md_texto"] = md
        out["evaluacion"] = evaluar(md)
        # trampa 25: 0 bytes puede ser un proceso que NO ARRANCÓ. El `rc` es lo
        # único que separa el silencio legítimo del fallo de arranque.
        out["nota_trampa_25"] = ("md de %d B con rc=%s" % (out["md_bytes"], rc))
    else:
        out["md_bytes"] = 0
        out["nota_trampa_25"] = (
            "NO hay .md: rc=%s, tope_alcanzado=%s. Sin fichero no hay CER que "
            "publicar; un CER del 100%% aquí sería el fallo de la trampa 99." % (rc, tope_alcanzado))
    # censo del desechable (trampa 21): ¿escribió algo fuera de lo declarado?
    fuera = []
    for raiz, _dirs, ficheros in os.walk(desechable):
        for f in ficheros:
            rel = os.path.relpath(os.path.join(raiz, f), desechable)
            if not rel.startswith("out" + os.sep):
                fuera.append(rel)
    out["escrito_fuera_del_destino"] = sorted(fuera)
    return out


_LOG = None


def log(msg: str) -> None:
    linea = "%s  %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(linea, flush=True)
    if _LOG:
        with open(_LOG, "a", encoding="utf-8") as fh:
            fh.write(linea + "\n")


def main():
    global _LOG
    ap = argparse.ArgumentParser()
    ap.add_argument("--etiqueta", default="i1")
    ap.add_argument("--modo", default=None,
                    help="valor de --mode de marker_single; por defecto NO se pasa")
    ap.add_argument("--tope", type=float, default=900.0)
    ap.add_argument("--espera-lock", type=float, default=600.0)
    ap.add_argument("--matar-todo-nuevo", action="store_true",
                    help="mata TODO contenedor nuevo, no sólo los surya-vllm-*")
    ap.add_argument("--env", nargs=2, action="append", metavar=("CLAVE", "VALOR"),
                    help="variable de entorno extra para marker (repetible)")
    args = ap.parse_args()

    _LOG = os.path.join(AQUI, "log_%s.txt" % args.etiqueta)
    reg = medir(args)
    destino = os.path.join(AQUI, "resultado_%s.json" % args.etiqueta)
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(reg, fh, indent=1, ensure_ascii=False)
    log("ESCRITO %s" % destino)
    print(json.dumps({k: v for k, v in reg.items()
                      if k not in ("cola_stdout", "md_texto", "vram_serie_mib",
                                   "docker_ps_a_antes", "docker_ps_a_despues",
                                   "docker_ps_a_final")},
                     indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

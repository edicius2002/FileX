#!/usr/bin/env python3
"""N4 — ¿hay en POSIX un equivalente de `os.replace(p, p)`? SONDEADO, no deducido.

`filex/watcher.py::_estable_en_disco` devuelve `True` sin mirar cuando
`os.name != 'nt'`, y el comentario dice *«en POSIX el único cerrojo real es la
estabilidad de `stat`»*. Eso era una **deducción**, y R7 dice que las
capacidades se sondean en ejecución. Esto lo sondea.

Se corre DENTRO de WSL2 (`wsl.exe -e python3 sonda_posix.py …`).

Siete primitivos, cinco estados, y un **control positivo** por cada primitivo
cooperativo: sin un escritor que TOME el `flock`, un «`flock` no detecta nada»
no significa nada — es la tercera lección de la trampa 36.

La trampa 38 se cumple registrando, en CADA celda, si la condición que se dice
reproducir se dio: el hijo escribe una línea `ABIERTO`/`PAUSA`/`CERRADO` en su
`stdout` y la sonda apunta `condicion_ok` con lo que vio (marcador recibido +
`poll() is None`). Una celda con `condicion_ok=False` no cuenta.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
ESCRITOR = os.path.join(AQUI, "escritor_lento.py")
TOPE_TESTIGO = 20.0


# --------------------------------------------------------------------------
# Los primitivos
# --------------------------------------------------------------------------
def p_replace(ruta: str) -> tuple[str, str]:
    """El primitivo de Windows, tal cual, en POSIX. Se espera que NO sirva."""
    try:
        os.replace(ruta, ruta)
        return "libre", ""
    except OSError as e:
        return "ocupado", f"{e.__class__.__name__}:{getattr(e, 'errno', '')}"


def p_abrir(ruta: str) -> tuple[str, str]:
    """«¿Puedo abrirlo?». Se espera que NO sirva, igual que en Windows."""
    try:
        with open(ruta, "rb") as fh:
            fh.read(1)
        return "libre", ""
    except OSError as e:
        return "ocupado", f"{e.__class__.__name__}:{getattr(e, 'errno', '')}"


def p_flock(ruta: str) -> tuple[str, str]:
    """`fcntl.flock(LOCK_EX|LOCK_NB)`. COOPERATIVO: solo ve a quien lo toma."""
    import fcntl

    try:
        fd = os.open(ruta, os.O_RDONLY)
    except OSError as e:
        return "error", str(e)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
        return "libre", ""
    except OSError as e:
        return "ocupado", f"{e.__class__.__name__}:{getattr(e, 'errno', '')}"
    finally:
        os.close(fd)


def p_lockf(ruta: str) -> tuple[str, str]:
    """`fcntl.lockf` (cerrojo de registro POSIX). También COOPERATIVO."""
    import fcntl

    try:
        fd = os.open(ruta, os.O_RDWR)
    except OSError as e:
        return "error", str(e)
    try:
        fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB, 1, 0)
        fcntl.lockf(fd, fcntl.LOCK_UN, 1, 0)
        return "libre", ""
    except OSError as e:
        return "ocupado", f"{e.__class__.__name__}:{getattr(e, 'errno', '')}"
    finally:
        os.close(fd)


def _identidad(ruta: str):
    try:
        st = os.stat(ruta)
    except OSError:
        return None
    return (st.st_dev, st.st_ino)


def escanear_proc(ruta: str, *, detalle: bool = False):
    """El candidato serio: ¿algún `/proc/<pid>/fd/*` apunta a este inodo?

    Se compara por **identidad** (`st_dev`+`st_ino`) y no por el texto del
    enlace, por el mismo motivo por el que `filex/nucleo.py::_identidad_destino`
    la usa: un alias de ruta da otro texto y el mismo fichero.

    Devuelve `(estado, pids, ilegibles, total_pids)`.
    """
    ident = _identidad(ruta)
    if ident is None:
        return "error", [], 0, 0
    yo = os.getpid()
    pids = []
    ilegibles = 0
    total = 0
    detalles = []
    try:
        entradas = os.listdir("/proc")
    except OSError as e:
        return "error", [], 0, 0
    for nombre in entradas:
        if not nombre.isdigit():
            continue
        total += 1
        pid = int(nombre)
        if pid == yo:
            continue
        d = "/proc/" + nombre + "/fd"
        try:
            fds = os.listdir(d)
        except OSError:
            ilegibles += 1        # otro usuario, o el proceso ya no está
            continue
        for f in fds:
            try:
                st = os.stat(os.path.join(d, f))
            except OSError:
                continue
            if (st.st_dev, st.st_ino) == ident:
                pids.append(pid)
                if detalle:
                    try:
                        destino = os.readlink(os.path.join(d, f))
                    except OSError:
                        destino = "?"
                    detalles.append({"pid": pid, "fd": f, "enlace": destino})
                break
    estado = "ocupado" if pids else "libre"
    if detalle:
        return estado, pids, ilegibles, total, detalles
    return estado, pids, ilegibles, total


def p_proc(ruta: str) -> tuple[str, str]:
    estado, pids, ilegibles, total = escanear_proc(ruta)
    return estado, f"pids={pids} ilegibles={ilegibles}/{total}"


def _externo(argv, tope=10.0):
    try:
        r = subprocess.run(argv, stdin=subprocess.DEVNULL,
                           capture_output=True, timeout=tope, text=True)
        return r.returncode, (r.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, str(e)


def p_lsof(ruta: str) -> tuple[str, str]:
    if not shutil.which("lsof"):
        return "error", "lsof ausente"
    rc, out = _externo(["lsof", "-t", "--", ruta])
    if rc is None:
        return "error", out
    pids = [x for x in out.split() if x.strip()]
    pids = [x for x in pids if x != str(os.getpid())]
    return ("ocupado" if pids else "libre"), f"rc={rc} pids={pids}"


def p_fuser(ruta: str) -> tuple[str, str]:
    if not shutil.which("fuser"):
        return "error", "fuser ausente"
    rc, out = _externo(["fuser", ruta])
    if rc is None:
        return "error", out
    return ("ocupado" if rc == 0 else "libre"), f"rc={rc} salida={out!r}"


PRIMITIVOS = [
    ("os.replace(p,p)", p_replace),
    ("open(p,'rb')", p_abrir),
    ("fcntl.flock", p_flock),
    ("fcntl.lockf", p_lockf),
    ("/proc/*/fd", p_proc),
    ("lsof -t", p_lsof),
    ("fuser", p_fuser),
]


# --------------------------------------------------------------------------
# El escritor, con su marcador
# --------------------------------------------------------------------------
class Hijo:
    """Lanza el escritor y ESPERA a su marcador. No duerme a ciegas."""

    def __init__(self, args: list[str]):
        self.argv = [sys.executable, ESCRITOR] + args
        self.p = subprocess.Popen(self.argv, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, text=True)
        self.lineas: list[str] = []

    def esperar(self, marcador: str, tope: float = 30.0) -> bool:
        fin = time.monotonic() + tope
        while time.monotonic() < fin:
            linea = self.p.stdout.readline()
            if not linea:
                return False
            self.lineas.append(linea.strip())
            if linea.startswith(marcador):
                return True
        return False

    @property
    def vivo(self) -> bool:
        return self.p.poll() is None

    def matar(self):
        try:
            self.p.kill()
        except OSError:
            pass
        try:
            self.p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass


# --------------------------------------------------------------------------
# Testigos de ruido
# --------------------------------------------------------------------------
def testigo_deriva(n=200000) -> float:
    t0 = time.perf_counter()
    x = 0
    for i in range(n):
        x += i * i
    return (time.perf_counter() - t0) * 1000


def testigo_nivel() -> float:
    t0 = time.perf_counter()
    try:
        subprocess.run(["/bin/true"], stdin=subprocess.DEVNULL,
                       capture_output=True, timeout=TOPE_TESTIGO)
    except (OSError, subprocess.TimeoutExpired):
        return TOPE_TESTIGO * 1000
    return (time.perf_counter() - t0) * 1000


# --------------------------------------------------------------------------
# Escenas
# --------------------------------------------------------------------------
def medir_estado(ruta: str) -> dict:
    out = {}
    for nombre, fn in PRIMITIVOS:
        try:
            estado, det = fn(ruta)
        except Exception as e:                              # noqa: BLE001
            estado, det = "error", f"{e.__class__.__name__}: {e}"
        out[nombre] = {"estado": estado, "detalle": det}
    return out


def escena(nombre: str, ruta: str, origen: str, extra: list[str],
           marcador: str, log) -> dict:
    """Una escena = un estado del fichero + los siete primitivos encima."""
    if os.path.exists(ruta):
        os.remove(ruta)
    if marcador == "":                       # estado A: nadie toca el fichero
        shutil.copyfile(origen, ruta)
        r = {"escena": nombre, "condicion_ok": True,
             "condicion": "ningún proceso tiene el fichero abierto",
             "primitivos": medir_estado(ruta)}
        log.write(f"[{nombre}] sin hijo. condicion_ok=True\n")
        return r

    if extra and extra[0] == "--solo-leer":
        shutil.copyfile(origen, ruta)        # tiene que existir para leerlo
    h = Hijo(["--origen", origen, "--destino", ruta] + extra)
    llego = h.esperar(marcador)
    vivo = h.vivo
    cond = llego and vivo
    tam = os.path.getsize(ruta) if os.path.exists(ruta) else -1
    prim = medir_estado(ruta) if cond else {}
    log.write(f"[{nombre}] marcador={marcador!r} llego={llego} vivo={vivo} "
              f"bytes_en_disco={tam} lineas={h.lineas}\n")
    h.matar()
    return {"escena": nombre, "condicion_ok": cond,
            "condicion": f"hijo con marcador {marcador} y vivo",
            "bytes_en_disco": tam, "lineas_hijo": h.lineas,
            "primitivos": prim}


def escena_ya_cerro(ruta: str, origen: str, log) -> dict:
    """Estado D: el hijo CERRÓ el fichero pero sigue vivo. Debe salir libre."""
    if os.path.exists(ruta):
        os.remove(ruta)
    h = Hijo(["--origen", origen, "--destino", ruta, "--trozos", "4",
              "--pausa", "0.01", "--tras-cerrar", "8"])
    llego = h.esperar("CERRADO")
    vivo = h.vivo
    cond = llego and vivo
    prim = medir_estado(ruta) if cond else {}
    log.write(f"[D_ya_cerro] llego={llego} vivo={vivo} lineas={h.lineas}\n")
    h.matar()
    return {"escena": "D_ya_cerro", "condicion_ok": cond,
            "condicion": "hijo VIVO con el fichero ya cerrado",
            "lineas_hijo": h.lineas, "primitivos": prim}


def coste(ruta: str, repes: int = 11) -> dict:
    """Coste de cada primitivo, mediana de n≥9, sobre un fichero QUIETO."""
    out = {}
    for nombre, fn in PRIMITIVOS:
        fn(ruta)                                        # calentar
        ms = []
        for _ in range(repes):
            t0 = time.perf_counter()
            try:
                fn(ruta)
            except Exception:                           # noqa: BLE001
                pass
            ms.append((time.perf_counter() - t0) * 1000)
        out[nombre] = {"mediana_ms": round(statistics.median(ms), 4),
                       "min_ms": round(min(ms), 4), "max_ms": round(max(ms), 4),
                       "n": repes}
    return out


def censo_proc() -> dict:
    """Cuánto de `/proc` es legible para este usuario. Es el techo del método."""
    yo = os.getpid()
    total = legibles = 0
    for nombre in os.listdir("/proc"):
        if not nombre.isdigit():
            continue
        total += 1
        try:
            os.listdir("/proc/" + nombre + "/fd")
            legibles += 1
        except OSError:
            pass
    return {"pids": total, "fd_legibles": legibles,
            "fd_ilegibles": total - legibles, "yo": yo,
            "uid": os.getuid()}


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--origen", default="")
    p.add_argument("--dir", default="/tmp/filex-n4")
    p.add_argument("--salida", required=True)
    p.add_argument("--log", required=True)
    p.add_argument("--etiqueta", default="tmpfs")
    p.add_argument("--medir-ruta", default="",
                   help="solo medir los siete primitivos sobre esta ruta y "
                        "salir. Es el CONTROL del cruce Windows->WSL2: el "
                        "tenedor lo pone el otro sistema, no esta sonda.")
    a = p.parse_args(argv)

    if a.medir_ruta:
        r = {"etiqueta": a.etiqueta, "ruta": a.medir_ruta,
             "existe": os.path.exists(a.medir_ruta),
             "bytes": os.path.getsize(a.medir_ruta) if os.path.exists(a.medir_ruta) else -1,
             "censo_proc": censo_proc(),
             "primitivos": medir_estado(a.medir_ruta)}
        with open(a.log, "w", encoding="utf-8") as log:
            log.write(json.dumps(r, ensure_ascii=False, indent=1))
        with open(a.salida, "w", encoding="utf-8") as fh:
            json.dump(r, fh, ensure_ascii=False, indent=1)
        print(json.dumps({k: v["estado"] for k, v in r["primitivos"].items()},
                         ensure_ascii=False))
        return 0
    if not a.origen:
        p.error("--origen es obligatorio salvo con --medir-ruta")

    os.makedirs(a.dir, exist_ok=True)
    ruta = os.path.join(a.dir, "sujeto.bin")
    res = {"etiqueta": a.etiqueta, "dir": a.dir,
           "python": sys.version.split()[0], "uname": os.uname().release,
           "origen": a.origen, "bytes_origen": os.path.getsize(a.origen)}

    d0, n0 = testigo_deriva(), testigo_nivel()
    with open(a.log, "w", encoding="utf-8") as log:
        log.write(f"# sonda_posix — {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"# uname={os.uname().release} python={sys.version.split()[0]}\n")
        log.write(f"# dir={a.dir} etiqueta={a.etiqueta}\n")
        res["censo_proc"] = censo_proc()
        log.write(f"# censo /proc: {res['censo_proc']}\n")

        escenas = []
        escenas.append(escena("A_quieto", ruta, a.origen, [], "", log))
        escenas.append(escena(
            "B_escribiendo", ruta, a.origen,
            ["--trozos", "20", "--pausa", "0.05", "--pausa-larga", "12",
             "--en-trozo", "10"], "PAUSA", log))
        escenas.append(escena(
            "C_solo_lee", ruta, a.origen,
            ["--solo-leer", "--mantener", "12"], "ABIERTO", log))
        escenas.append(escena_ya_cerro(ruta, a.origen, log))
        escenas.append(escena(
            "E_escribiendo_con_flock", ruta, a.origen,
            ["--flock", "--trozos", "20", "--pausa", "0.05",
             "--pausa-larga", "12", "--en-trozo", "10"], "PAUSA", log))
        res["escenas"] = escenas

        if os.path.exists(ruta):
            os.remove(ruta)
        shutil.copyfile(a.origen, ruta)
        res["coste"] = coste(ruta)
        log.write(f"# coste: {json.dumps(res['coste'])}\n")

        d1, n1 = testigo_deriva(), testigo_nivel()
        res["testigos"] = {
            "deriva_ms": [round(d0, 2), round(d1, 2)],
            "nivel_ms": [round(n0, 2), round(n1, 2)],
            "deriva_ratio": round(d1 / d0, 3) if d0 else None,
            "nivel_ratio": round(n1 / n0, 3) if n0 else None,
        }
        res["testigos"]["etiqueta"] = (
            "limpia" if (res["testigos"]["deriva_ratio"] or 9) < 1.5
            and (res["testigos"]["nivel_ratio"] or 9) < 3.0 else "SUCIA")
        log.write(f"# testigos: {json.dumps(res['testigos'])}\n")

    with open(a.salida, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print(json.dumps({"etiqueta": a.etiqueta,
                      "escenas": [(e["escena"], e["condicion_ok"]) for e in res["escenas"]],
                      "testigos": res["testigos"]["etiqueta"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

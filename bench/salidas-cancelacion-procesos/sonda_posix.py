"""N13 — los dos pendientes POSIX de `bench/cerrojo-de-maquina.md` §6.5 y §6.6.

    §6.5  «En POSIX la detección no existe. `os.replace(p, p)` allí siempre
          funciona, así que `destino_ocupado_por_un_tercero` devuelve `False`
          sin mirar.»
    §6.6  «En POSIX el fichero de candado no se barre. En Windows un borrado que
          tiene éxito DEMUESTRA que nadie lo tenía abierto; en POSIX el borrado
          siempre funciona y abriría la carrera clásica de "borro el candado de
          otro".»

Se sondea **dentro de WSL2 y sobre ext4** (`/tmp` de Ubuntu), no sobre `/mnt/d`:
`/mnt/d` es drvfs, y medir ahí sería medir el puente, no POSIX. La otra mitad de
esa advertencia ya está pagada en el proyecto —*«una explicación plausible no es
un mecanismo»*, trampa 36— así que cada «no detecta» de aquí lleva su **control
positivo** al lado.

Cuatro celdas:

A1  ¿`os.replace(p, p)` detecta en POSIX a un tercero que tiene el fichero
    abierto? (Control positivo: en Windows sí, `WinError 32`, ya MEDIDO por N-b.)
A2  ¿Lo detecta `fcntl.flock` no bloqueante sobre el destino? Con dos terceros:
    uno que solo hace `open()` y otro que además hace `flock`.
A3  ¿Lo detecta un barrido de `/proc/*/fd`? Y cuánto cuesta.
B   La carrera del barrido, construida **sin depender de tiempos**: se
    reproduce el «dos dueños» y luego se prueba el protocolo que lo cerraría
    (verificar el inodo DESPUÉS de tomar el candado), con su coste.

Uso, desde Windows::

    wsl -e python3 /mnt/d/.../sonda_posix.py

Escribe `sonda_posix.json` **junto a este fichero**. No usa la GPU.
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "sonda_posix.json")

#: Todo lo de POSIX se mide sobre ext4, no sobre el `/mnt/d` de drvfs.
BASE = "/tmp/filex-n13" if sys.platform != "win32" else tempfile.gettempdir()

#: Tope de todo subproceso auxiliar. Ninguno sin tope.
TOPE = 30.0

N_MICRO = 200


def _mediana_us(v) -> float:
    return round(statistics.median(v) * 1e6, 1) if v else float("nan")


def _tercero_que_abre(ruta: str, segundos: float, con_flock: bool):
    """Un proceso de VERDAD que tiene `ruta` abierta. Devuelve el `Popen`.

    Un hilo no sirve: la pregunta es si OTRO proceso es detectable, y un `fd`
    del mismo proceso no prueba nada.
    """
    guion = (
        "import fcntl,sys,time\n"
        "f=open(sys.argv[1],'r+b')\n"
        "if sys.argv[3]=='1': fcntl.flock(f.fileno(), fcntl.LOCK_EX)\n"
        "sys.stdout.write('listo\\n'); sys.stdout.flush()\n"
        "time.sleep(float(sys.argv[2]))\n")
    p = subprocess.Popen([sys.executable, "-c", guion, ruta, str(segundos),
                          "1" if con_flock else "0"],
                         stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         text=True)
    p.stdout.readline()                      # espera al 'listo'
    return p


def celda_a1(d: str) -> dict:
    """`os.replace(p, p)` con un tercero que solo tiene el fichero ABIERTO."""
    ruta = os.path.join(d, "a1.bin")
    with open(ruta, "wb") as fh:
        fh.write(b"x" * 64)
    p = _tercero_que_abre(ruta, 5.0, con_flock=False)
    try:
        t0 = time.perf_counter()
        try:
            os.replace(ruta, ruta)
            detecta, error = False, ""
        except OSError as e:
            detecta, error = True, f"{type(e).__name__}:{getattr(e, 'winerror', e.errno)}"
        us = (time.perf_counter() - t0) * 1e6
    finally:
        p.kill()
        p.wait(timeout=TOPE)
    return {"detecta": detecta, "error": error, "us": round(us, 1),
            "control_windows": "WinError 32 (MEDIDO por N-b, cerrojo-de-maquina.md §5.1)"}


def celda_a2(d: str) -> dict:
    """`flock` no bloqueante sobre el destino, contra los dos terceros."""
    import fcntl

    out = {}
    for etiqueta, con_flock in (("tercero_solo_abre", False),
                                ("tercero_con_flock", True)):
        ruta = os.path.join(d, f"a2-{etiqueta}.bin")
        with open(ruta, "wb") as fh:
            fh.write(b"x" * 64)
        p = _tercero_que_abre(ruta, 5.0, con_flock=con_flock)
        try:
            fd = os.open(ruta, os.O_RDWR)
            t0 = time.perf_counter()
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                detecta = False
                fcntl.flock(fd, fcntl.LOCK_UN)
            except OSError:
                detecta = True
            us = (time.perf_counter() - t0) * 1e6
            os.close(fd)
        finally:
            p.kill()
            p.wait(timeout=TOPE)
        out[etiqueta] = {"detecta": detecta, "us": round(us, 1)}
    return out


def celda_a3(d: str) -> dict:
    """Barrido de `/proc/*/fd`: la única vía que ve a un tercero NO cooperativo.

    Se mide con el tercero vivo (¿lo ve?), sin el tercero (¿falso positivo?) y
    cuánto cuesta el barrido, que es lo que decide si compensa.
    """
    ruta = os.path.join(d, "a3.bin")
    with open(ruta, "wb") as fh:
        fh.write(b"x" * 64)
    real = os.path.realpath(ruta)

    def barre() -> tuple[bool, int, int]:
        vistos = negados = 0
        encontrado = False
        yo = str(os.getpid())
        for pid in os.listdir("/proc"):
            if not pid.isdigit() or pid == yo:
                continue
            dfd = f"/proc/{pid}/fd"
            try:
                for fd in os.listdir(dfd):
                    vistos += 1
                    try:
                        if os.readlink(os.path.join(dfd, fd)) == real:
                            encontrado = True
                    except OSError:
                        pass
            except OSError:
                negados += 1
        return encontrado, vistos, negados

    p = _tercero_que_abre(ruta, 8.0, con_flock=False)
    try:
        t0 = time.perf_counter()
        visto, fds, negados = barre()
        us_con = (time.perf_counter() - t0) * 1e6
    finally:
        p.kill()
        p.wait(timeout=TOPE)
    t0 = time.perf_counter()
    visto_sin, _, _ = barre()
    us_sin = (time.perf_counter() - t0) * 1e6
    coste = []
    for _ in range(20):
        t0 = time.perf_counter()
        barre()
        coste.append(time.perf_counter() - t0)
    return {"ve_al_tercero": visto, "falso_positivo_sin_tercero": visto_sin,
            "fds_recorridos": fds, "procesos_denegados": negados,
            "us_con_tercero": round(us_con, 1), "us_sin_tercero": round(us_sin, 1),
            "mediana_us": _mediana_us(coste), "n": 20,
            "nota": "los procesos denegados son los de OTRO usuario: sin root, "
                    "esta vía es ciega justo donde el candado de fichero lo es"}


def celda_b(d: str) -> dict:
    """La carrera del barrido, y el protocolo que la cerraría. Sin tiempos.

    No hace falta ganar ninguna carrera para reproducirla: la secuencia es
    determinista porque en POSIX un fichero desenlazado **sigue vivo** mientras
    alguien lo tenga abierto, y el siguiente `open` crea otro inodo distinto.
    """
    import fcntl

    ruta = os.path.join(d, "b.lock")

    def toma(verifica: bool):
        """`(fd, ok)`. Con `verifica`, se comprueba el inodo TRAS tomar."""
        fd = os.open(ruta, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return None, False
        if verifica:
            try:
                if os.stat(ruta).st_ino != os.fstat(fd).st_ino:
                    os.close(fd)          # el candado que tomamos ya no es EL
                    return None, False    # candado: alguien lo desenlazó
            except OSError:
                os.close(fd)
                return None, False
        return fd, True

    out = {}
    for etiqueta, verifica in (("sin_verificar", False), ("verificando", True)):
        for f in (ruta,):
            try:
                os.remove(f)
            except OSError:
                pass
        # A toma el candado.
        fa, _ = toma(verifica)
        # B abre el MISMO inodo pero todavía no lo bloquea.
        fb = os.open(ruta, os.O_RDWR | os.O_CREAT, 0o600)
        # A suelta y BARRE, que es lo que Windows sí puede hacer con seguridad.
        fcntl.flock(fa, fcntl.LOCK_UN)
        os.close(fa)
        os.remove(ruta)
        # B bloquea: el inodo sigue vivo aunque ya no esté enlazado.
        try:
            fcntl.flock(fb, fcntl.LOCK_EX | fcntl.LOCK_NB)
            b_ok = True
            if verifica:
                try:
                    b_ok = os.stat(ruta).st_ino == os.fstat(fb).st_ino
                except OSError:
                    b_ok = False
        except OSError:
            b_ok = False
        # C llega después del barrido: su `open` crea un inodo NUEVO.
        fc, c_ok = toma(verifica)
        out[etiqueta] = {"B_cree_tenerlo": b_ok, "C_cree_tenerlo": c_ok,
                         "DOS_DUENOS": bool(b_ok and c_ok)}
        for fd in (fb, fc):
            try:
                if fd is not None:
                    os.close(fd)
            except OSError:
                pass
        try:
            os.remove(ruta)
        except OSError:
            pass

    # Lo que cuesta la verificación, aislada (trampa 36: el trozo, no la resta).
    coste = []
    fd0, _ = toma(False)
    for _ in range(N_MICRO):
        t0 = time.perf_counter()
        try:
            os.stat(ruta).st_ino == os.fstat(fd0).st_ino
        except OSError:
            pass
        coste.append(time.perf_counter() - t0)
    os.close(fd0)
    try:
        os.remove(ruta)
    except OSError:
        pass

    # Y lo que se ahorra barriendo: N-b midió en Windows que sin el `remove` el
    # ciclo es ×2,3 más lento, porque el `open` siguiente cae sobre un fichero
    # con contenido y se paga el `ftruncate`. ¿Pasa lo mismo en ext4?
    ciclo = {}
    for etiqueta, barrer in (("con_barrido", True), ("sin_barrido", False)):
        v = []
        for _ in range(N_MICRO):
            t0 = time.perf_counter()
            fd = os.open(ruta, os.O_RDWR | os.O_CREAT, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.ftruncate(fd, 0)
            os.write(fd, b"12345\t67890\tmetadatos de un candado\n")
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
            if barrer:
                try:
                    os.remove(ruta)
                except OSError:
                    pass
            v.append(time.perf_counter() - t0)
        ciclo[etiqueta] = _mediana_us(v)
        try:
            os.remove(ruta)
        except OSError:
            pass
    ciclo["razon_sin_entre_con"] = round(
        ciclo["sin_barrido"] / max(ciclo["con_barrido"], 1e-9), 3)
    ciclo["control_windows_N_b"] = "sin el remove, x2,3 MAS LENTO"

    out["coste_verificacion_us"] = _mediana_us(coste)
    out["ciclo_us"] = ciclo
    out["n"] = N_MICRO
    return out


def main() -> None:
    os.makedirs(BASE, exist_ok=True)
    d = tempfile.mkdtemp(prefix="n13-", dir=BASE)
    antes = sorted(os.listdir(d))
    try:
        res = {"plataforma": sys.platform, "python": sys.version.split()[0],
               "base": BASE, "es_ext4": not BASE.startswith("/mnt/")}
        if sys.platform == "win32":
            res["aplica"] = False
            res["motivo"] = "esta sonda es de POSIX; lánzala con wsl -e python3"
        else:
            res["aplica"] = True
            res["A1_os_replace"] = celda_a1(d)
            res["A2_flock"] = celda_a2(d)
            res["A3_proc_fd"] = celda_a3(d)
            res["B_barrido"] = celda_b(d)
        res["R21_sobrantes"] = sorted(set(os.listdir(d)) - set(antes))
    finally:
        import shutil

        shutil.rmtree(d, ignore_errors=True)
    with open(SALIDA, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

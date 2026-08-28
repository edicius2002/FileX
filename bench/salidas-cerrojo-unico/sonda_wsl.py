"""¿Alguna de las dos vías cruza a la VM de WSL2?

Es el límite 2 de `cerrojo-de-maquina.md` §6 y el aviso 1 de
`lock-de-maquina.md`, y hasta ahora estaba **deducido**: *«el `/tmp` de Ubuntu
es otro sistema de ficheros»*. Pero **el `%TEMP%` de Windows SÍ se ve desde
WSL2** por `/mnt/c` (9p/drvfs, comprobado), así que la deducción no cierra la
pregunta: lo que hay que medir no es si el fichero se ve, sino si el **candado**
sobre él se respeta a través del puente.

Se miden las dos direcciones de la única vía plausible, y una tercera de
control:

  1. Windows toma `msvcrt.locking` → ¿lo ve `fcntl.flock` desde WSL2?
  2. WSL2 toma `fcntl.flock`      → ¿lo ve `msvcrt.locking` desde Windows?
  3. Control dentro de WSL2: dos `flock` del MISMO lado, que sí deben excluirse.
     Sin este control, un «no excluye» podría ser que `flock` no funcione en
     9p en absoluto, que es una explicación distinta con otra consecuencia.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
TOPE = 120

# El hijo de WSL2. Se pasa por `-c` en una sola línea con `;` para no depender
# de ficheros de script dentro de la VM.
WSL_INTENTA = (
    "import fcntl,sys\n"
    "f=open(sys.argv[1],'r+b')\n"
    "try:\n"
    "    fcntl.flock(f.fileno(), fcntl.LOCK_EX|fcntl.LOCK_NB)\n"
    "    print('TOMADO')\n"
    "except OSError as e:\n"
    "    print('BLOQUEADO', e.errno, e.strerror)\n"
)
WSL_TOMA_Y_ESPERA = (
    "import fcntl,sys,time\n"
    "f=open(sys.argv[1],'r+b')\n"
    "fcntl.flock(f.fileno(), fcntl.LOCK_EX|fcntl.LOCK_NB)\n"
    "print('TOMADO', flush=True)\n"
    "time.sleep(float(sys.argv[2]))\n"
)


def a_ruta_wsl(win: str) -> str:
    p = os.path.abspath(win).replace("\\", "/")
    return "/mnt/" + p[0].lower() + p[2:]


def wsl(codigo: str, *args, espera_linea=False, timeout=TOPE):
    orden = ["wsl.exe", "-d", "Ubuntu", "-e", "python3", "-c", codigo, *args]
    if espera_linea:
        p = subprocess.Popen(orden, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             stdin=subprocess.DEVNULL, text=True)
        return p, (p.stdout.readline() or "").strip()
    r = subprocess.run(orden, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=timeout)
    return None, (r.stdout or "").strip() + (
        ("  [err] " + r.stderr.strip()[:200]) if r.returncode else "")


def _bloquear_win(fd: int) -> None:
    import msvcrt
    os.lseek(fd, 1 << 30, os.SEEK_SET)
    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)


def _soltar_win(fd: int) -> None:
    import msvcrt
    try:
        os.lseek(fd, 1 << 30, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    except OSError:
        pass
    os.close(fd)


def main() -> int:
    res: dict = {"cuando": time.strftime("%Y-%m-%dT%H:%M:%S")}
    ruta = os.path.join(tempfile.gettempdir(), f"filex-cruce-wsl-{os.getpid()}.lock")
    with open(ruta, "wb") as f:
        f.write(b"filex sonda de cruce\n" + b"\0" * 16)
    rwsl = a_ruta_wsl(ruta)
    print(f"fichero: {ruta}\n     wsl: {rwsl}")
    res["ruta"] = {"windows": ruta, "wsl": rwsl}

    # --- 1. Windows toma; WSL2 intenta --------------------------------------
    print("== 1. lo toma WINDOWS (msvcrt.locking); lo intenta WSL2 (flock) ==")
    fd = os.open(ruta, os.O_RDWR)
    _bloquear_win(fd)
    _p, salida = wsl(WSL_INTENTA, rwsl)
    excluye_1 = salida.startswith("BLOQUEADO")
    print(f"  WSL2 dice: {salida!r}  -> Windows excluye a WSL2: {excluye_1}")
    res["1_win_bloquea_wsl"] = {"salida": salida, "excluye": excluye_1}
    _soltar_win(fd)

    # --- 2. WSL2 toma; Windows intenta --------------------------------------
    print("== 2. lo toma WSL2 (flock); lo intenta WINDOWS (msvcrt.locking) ==")
    p, aviso = wsl(WSL_TOMA_Y_ESPERA, rwsl, "8", espera_linea=True)
    print(f"  el hijo de WSL2 dice: {aviso!r}")
    try:
        fd2 = os.open(ruta, os.O_RDWR)
        try:
            _bloquear_win(fd2)
            excluye_2 = False
            print("  Windows LO TOMA IGUAL -> WSL2 no excluye a Windows")
            _soltar_win(fd2)
        except OSError as e:
            excluye_2 = True
            print(f"  Windows BLOQUEADO ({e.errno} {e.strerror}) -> WSL2 sí excluye")
            os.close(fd2)
    except OSError as e:
        excluye_2 = None
        print(f"  no se pudo ni abrir: {e}")
    res["2_wsl_bloquea_win"] = {"hijo": aviso, "excluye": excluye_2}
    try:
        p.wait(timeout=30)
    except Exception:
        p.kill()

    # --- 3. control: dos flock DENTRO de WSL2 sobre el mismo /mnt/c ---------
    print("== 3. CONTROL: dos flock del MISMO lado (WSL2) sobre /mnt/c ==")
    p3, aviso3 = wsl(WSL_TOMA_Y_ESPERA, rwsl, "8", espera_linea=True)
    _p, salida3 = wsl(WSL_INTENTA, rwsl)
    control = salida3.startswith("BLOQUEADO")
    print(f"  primero: {aviso3!r}   segundo: {salida3!r}")
    print(f"  -> flock SÍ funciona sobre 9p entre dos procesos de WSL2: {control}")
    res["3_control_wsl_wsl"] = {"primero": aviso3, "segundo": salida3,
                                "excluye": control}
    try:
        p3.wait(timeout=30)
    except Exception:
        p3.kill()

    try:
        os.remove(ruta)
    except OSError:
        pass

    res["veredicto"] = {
        "el_candado_de_fichero_cruza_a_wsl2": bool(excluye_1) and bool(excluye_2),
        "flock_funciona_dentro_de_wsl2_sobre_9p": control,
    }
    print(f"== VEREDICTO: el candado de fichero cruza a WSL2: "
          f"{res['veredicto']['el_candado_de_fichero_cruza_a_wsl2']} ==")

    with open(os.path.join(AQUI, "sonda_wsl.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())

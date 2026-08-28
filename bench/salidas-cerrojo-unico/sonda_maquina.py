"""Sonda de las vías del pendiente 1 de N-b: ¿se puede tener un cerrojo de
MÁQUINA de verdad en esta máquina, y no de usuario?

R7 del proyecto: **sondear en ejecución, no deducir**. Aquí muerde especialmente
porque el espacio de nombres `Global\\` exige el privilegio
`SeCreateGlobalPrivilege`, y si esta sesión lo tiene o no es un hecho de esta
máquina, no de la documentación.

Se sondean CUATRO cosas, todas con timeout explícito:

  1. `Local\\` frente a `Global\\` en `CreateMutexW` — la prueba directa del
     privilegio: si `Local\\` va y `Global\\` da `ERROR_ACCESS_DENIED (5)`, no
     hay vía.
  2. La exclusión real entre DOS PROCESOS con el mutex que sí se pueda crear.
  3. Qué pasa cuando al dueño lo matan con `taskkill /F` — la fila que decidió
     el candado de fichero de N-b (§3 de `cerrojo-de-maquina.md`).
  4. Si el mutex deja leer QUIÉN lo tiene, que es media trampa 31.

Subcomandos (el guion se relanza a sí mismo para tener procesos de verdad):
    python sonda_maquina.py            -> la sonda entera
    python sonda_maquina.py tomar NOMBRE SEGUNDOS  -> hijo que toma y espera
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import os
import statistics
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.CreateMutexW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.LPCWSTR]
k32.CreateMutexW.restype = wt.HANDLE
k32.OpenMutexW.argtypes = [wt.DWORD, wt.BOOL, wt.LPCWSTR]
k32.OpenMutexW.restype = wt.HANDLE
k32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
k32.WaitForSingleObject.restype = wt.DWORD
k32.ReleaseMutex.argtypes = [wt.HANDLE]
k32.ReleaseMutex.restype = wt.BOOL
k32.CloseHandle.argtypes = [wt.HANDLE]
k32.CloseHandle.restype = wt.BOOL

WAIT_OBJECT_0 = 0x00000000
WAIT_ABANDONED = 0x00000080
WAIT_TIMEOUT = 0x00000102
SYNCHRONIZE = 0x00100000
MUTEX_ALL_ACCESS = 0x001F0001


def crear(nombre: str):
    """`(handle, last_error)`. `handle == 0` significa que NO se pudo crear."""
    ctypes.set_last_error(0)
    h = k32.CreateMutexW(None, False, nombre)
    return h, ctypes.get_last_error()


# ---------------------------------------------------------------------------
# El hijo: toma el mutex y se queda quieto. Sin `finally` a propósito: la
# gracia de la escena 3 es que lo maten sin que suelte nada.
# ---------------------------------------------------------------------------
def hijo_tomar(nombre: str, segundos: float) -> int:
    h, err = crear(nombre)
    if not h:
        print(json.dumps({"tomado": False, "err": err}), flush=True)
        return 2
    r = k32.WaitForSingleObject(h, 5000)
    print(json.dumps({"tomado": r in (WAIT_OBJECT_0, WAIT_ABANDONED),
                      "wait": r, "pid": os.getpid()}), flush=True)
    time.sleep(segundos)
    return 0


def _lanzar_hijo(nombre: str, segundos: float):
    p = subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "tomar", nombre, str(segundos)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL, text=True)
    linea = p.stdout.readline()          # la cita: no se sigue hasta que avisa
    return p, json.loads(linea) if linea.strip() else {}


def main() -> int:
    res: dict = {"cuando": time.strftime("%Y-%m-%dT%H:%M:%S"), "pid": os.getpid()}
    sello = f"filex-sonda-{os.getpid()}"

    # --- 1. ¿tenemos el privilegio de `Global\`? ----------------------------
    print("== 1. Local\\ frente a Global\\ ==")
    paso1 = {}
    for espacio in ("Local\\", "Global\\", ""):
        h, err = crear(espacio + sello)
        paso1[espacio or "(sin prefijo)"] = {"creado": bool(h), "last_error": err}
        print(f"  {espacio or '(sin prefijo)':14s} creado={bool(h)!s:5s} "
              f"GetLastError={err}")
        if h:
            k32.CloseHandle(h)
    res["1_espacios"] = paso1
    hay_global = paso1["Global\\"]["creado"]
    nombre = ("Global\\" if hay_global else "Local\\") + sello + "-x"
    print(f"  -> se sigue con: {nombre}")

    # --- 2. exclusión entre dos procesos ------------------------------------
    print("== 2. exclusion entre DOS PROCESOS ==")
    p, aviso = _lanzar_hijo(nombre, 6.0)
    t0 = time.perf_counter()
    h, _ = crear(nombre)
    r = k32.WaitForSingleObject(h, 0)
    dt = (time.perf_counter() - t0) * 1e6
    res["2_exclusion"] = {"hijo": aviso, "wait_padre": r,
                          "excluye": r == WAIT_TIMEOUT, "us": round(dt, 1)}
    print(f"  hijo dice: {aviso}")
    print(f"  el padre espera con timeout 0 -> {r:#x} "
          f"({'WAIT_TIMEOUT: EXCLUYE' if r == WAIT_TIMEOUT else 'NO EXCLUYE'}) "
          f"en {dt:.1f} us")

    # --- 3. al dueño lo matan con taskkill /F -------------------------------
    print("== 3. dueno muerto por taskkill /F ==")
    pid_hijo = aviso.get("pid")
    rc = subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid_hijo)],
                        capture_output=True, text=True, timeout=30).returncode
    p.wait(timeout=30)
    t0 = time.perf_counter()
    r2 = k32.WaitForSingleObject(h, 2000)
    dt2 = (time.perf_counter() - t0) * 1e6
    recuperado = r2 in (WAIT_OBJECT_0, WAIT_ABANDONED)
    res["3_huerfano"] = {"taskkill_rc": rc, "wait": r2,
                         "abandonado": r2 == WAIT_ABANDONED,
                         "recuperado": recuperado, "us": round(dt2, 1)}
    print(f"  taskkill rc={rc}; el siguiente espera -> {r2:#x} "
          f"({'WAIT_ABANDONED: el SISTEMA lo suelta' if r2 == WAIT_ABANDONED else r2}) "
          f"en {dt2:.1f} us")
    if recuperado:
        k32.ReleaseMutex(h)
    k32.CloseHandle(h)

    # --- 4. ¿se puede saber QUIÉN lo tiene? ---------------------------------
    print("== 4. metadatos: quien lo tiene ==")
    # No hay API de usuario para preguntarle a un mutex por su dueño: `OpenMutexW`
    # solo dice si EXISTE. Se mide lo único que se puede medir.
    h2 = k32.OpenMutexW(SYNCHRONIZE, False, nombre)
    res["4_metadatos"] = {
        "open_dice_si_existe": bool(h2),
        "api_de_dueno": None,
        "nota": "el mutex no lleva carga: OpenMutexW solo dice si existe; "
                "quien lo tiene no es consultable sin depurador",
    }
    print(f"  OpenMutexW tras soltarlo: handle={bool(h2)} "
          f"-> el objeto {'sigue' if h2 else 'no sigue'} vivo (lo mantiene "
          f"nuestro propio handle si lo hubiera)")
    print("  NO hay API de dueno: el mutex no lleva carga util. "
          "El fichero de candado si (pid, epoch, ruta).")
    if h2:
        k32.CloseHandle(h2)

    # --- 5. coste, n >= 9 ---------------------------------------------------
    print("== 5. coste del ciclo tomar+soltar ==")
    for _ in range(50):                       # calentamiento (trampa 7)
        hh, _e = crear(nombre + "-c")
        k32.WaitForSingleObject(hh, 0)
        k32.ReleaseMutex(hh)
        k32.CloseHandle(hh)
    muestras = []
    for _ in range(20000):
        t = time.perf_counter()
        hh, _e = crear(nombre + "-c")
        k32.WaitForSingleObject(hh, 0)
        k32.ReleaseMutex(hh)
        k32.CloseHandle(hh)
        muestras.append((time.perf_counter() - t) * 1e6)
    muestras.sort()
    res["5_coste_us"] = {
        "n": len(muestras),
        "mediana": round(statistics.median(muestras), 1),
        "p90": round(muestras[int(len(muestras) * 0.9)], 1),
    }
    print(f"  mutex crear+wait+release+close: mediana "
          f"{res['5_coste_us']['mediana']} us  p90 {res['5_coste_us']['p90']} us")

    with open(os.path.join(AQUI, "sonda_maquina.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    print("== escrito sonda_maquina.json ==")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "tomar":
        sys.exit(hijo_tomar(sys.argv[2], float(sys.argv[3])))
    sys.exit(main())

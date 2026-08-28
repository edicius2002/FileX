"""Sondeo EN EJECUCIÓN de las cinco piezas del movimiento al destino.

Ninguna carrera: todos los estados se construyen a mano, como en la §1 de
`bench/contenedor-parar.md`. Lo que se pregunta:

  M1. `shutil.move` sobre un destino que existe: ¿`rename` o `copy2`?
  M2. `shutil.move` sobre un destino que un TERCERO tiene abierto: ¿pisa?
  M3. `os.replace(origen, destino)` en ese mismo estado: ¿falla? ¿con qué?
  M4. `os.replace` cruzando volúmenes: ¿qué `errno`? (hay que distinguirlo de M3)
  M5. `CreateFileW` con `FILE_SHARE_NONE`: ¿se puede? ¿excluye al tercero?
      ¿y me excluye a MÍ del `os.replace` que vendría después?

Salida: `sonda_mecanismo.json` + log.
"""
from __future__ import annotations

import errno
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
TERCERO = os.path.join(AQUI, "tercero.py")

log_lineas: list[str] = []


def log(msg: str) -> None:
    print(msg)
    log_lineas.append(msg)


def _err(e: OSError) -> dict:
    return {"clase": e.__class__.__name__, "errno": e.errno,
            "winerror": getattr(e, "winerror", None), "texto": str(e)[:200]}


def _lanzar_tercero(modo: str, ruta: str, registro: str, **extra):
    argv = [sys.executable, TERCERO, "--modo", modo, "--ruta", ruta,
            "--registro", registro]
    for k, v in extra.items():
        argv += [f"--{k}", str(v)]
    return subprocess.Popen(argv, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _esperar_registro(registro: str, clave: str, tope: float = 15.0):
    fin = time.monotonic() + tope
    while time.monotonic() < fin:
        try:
            with open(registro, encoding="utf-8") as f:
                d = json.load(f)
            if d.get(clave) is not None:
                return d
        except (OSError, ValueError):
            pass
        time.sleep(0.01)
    return None


def m1_move_destino_existente(tmp: str) -> dict:
    """¿`shutil.move` hace `rename` cuando el destino ya existe? (trampa 33)"""
    origen = os.path.join(tmp, "m1_origen.bin")
    destino = os.path.join(tmp, "m1_destino.bin")
    with open(origen, "wb") as f:
        f.write(b"N" * 1000)
    with open(destino, "wb") as f:
        f.write(b"V" * 4014)
    # `os.rename` a pelo, para ver qué hace shutil por dentro.
    rename = None
    try:
        os.rename(origen, destino)
        rename = "ok"
    except OSError as e:
        rename = _err(e)
    r = {"os_rename_sobre_existente": rename}
    if rename != "ok":
        shutil.move(origen, destino)
        r["shutil_move_hizo"] = "copy2 (el rename había fallado)"
        r["tam_destino_despues"] = os.path.getsize(destino)
        r["origen_sigue"] = os.path.exists(origen)
    log(f"M1 os.rename sobre destino existente -> {rename}")
    log(f"M1 shutil.move deja el destino en {r.get('tam_destino_despues')} B "
        f"(era 4014, el origen 1000)")
    return r


def m2_m3_tercero_abierto(tmp: str) -> dict:
    """Destino EXISTENTE y abierto por un tercero: `shutil.move` frente a
    `os.replace`."""
    r: dict = {}
    for etiqueta, operacion in (("shutil_move", "move"), ("os_replace", "replace")):
        sub = os.path.join(tmp, etiqueta)
        os.makedirs(sub, exist_ok=True)
        origen = os.path.join(sub, "origen.bin")
        destino = os.path.join(sub, "destino.bin")
        with open(origen, "wb") as f:
            f.write(b"N" * 13516)
        registro = os.path.join(sub, "tercero.json")
        p = _lanzar_tercero("abrir", destino, registro, tope=20)
        d = _esperar_registro(registro, "abierto_ns")
        celda: dict = {"tercero_abrio": bool(d), "tam_del_tercero": 4014}
        if d is None:
            p.kill()
            r[etiqueta] = {"error": "el tercero no llegó a abrir"}
            continue
        # La DETECCIÓN de hoy, sobre el mismo estado: control positivo.
        try:
            os.replace(destino, destino)
            celda["deteccion_dice"] = "libre"
        except OSError as e:
            celda["deteccion_dice"] = "ocupado"
            celda["deteccion_error"] = _err(e)
        try:
            if operacion == "move":
                shutil.move(origen, destino)
            else:
                os.replace(origen, destino)
            celda["resultado"] = "PISÓ"
        except OSError as e:
            celda["resultado"] = "se negó"
            celda["error"] = _err(e)
        celda["tam_destino_despues"] = os.path.getsize(destino)
        p.kill()
        p.wait(timeout=10)
        r[etiqueta] = celda
        log(f"M2/M3 {etiqueta}: detección={celda.get('deteccion_dice')} "
            f"resultado={celda['resultado']} destino={celda['tam_destino_despues']} B "
            f"err={celda.get('error', {}).get('winerror')}")
    return r


def m4_cruzar_volumen(tmp: str) -> dict:
    """`os.replace` entre volúmenes: hay que poder distinguirlo de «ocupado»."""
    otro = os.environ.get("FILEX_VENTANA_OTRO_VOLUMEN") or os.path.join(RAIZ, "bench",
                                                                       "salidas-ventana")
    origen = os.path.join(tmp, "m4_origen.bin")
    with open(origen, "wb") as f:
        f.write(b"X" * 500)
    destino = os.path.join(otro, "m4_destino.tmp")
    r = {"origen_unidad": os.path.splitdrive(origen)[0],
         "destino_unidad": os.path.splitdrive(os.path.abspath(destino))[0]}
    try:
        os.replace(origen, destino)
        r["resultado"] = "ok (mismo volumen, no prueba nada)"
        os.remove(destino)
    except OSError as e:
        r["resultado"] = "falló"
        r["error"] = _err(e)
        r["es_EXDEV"] = e.errno == errno.EXDEV
    log(f"M4 os.replace {r['origen_unidad']} -> {r['destino_unidad']}: "
        f"{r['resultado']} {r.get('error', {}).get('winerror', '')} "
        f"EXDEV={r.get('es_EXDEV')}")
    return r


def m5_file_share_none(tmp: str) -> dict:
    """`CreateFileW` con `dwShareMode=0`, que es lo que propone §6.3."""
    import ctypes
    import ctypes.wintypes as wt

    GENERIC_WRITE = 0x40000000
    OPEN_ALWAYS = 4
    FILE_ATTRIBUTE_NORMAL = 0x80
    INVALID = wt.HANDLE(-1).value

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p,
                                wt.DWORD, wt.DWORD, wt.HANDLE]
    k32.CreateFileW.restype = wt.HANDLE
    k32.CloseHandle.argtypes = [wt.HANDLE]

    sub = os.path.join(tmp, "m5")
    os.makedirs(sub, exist_ok=True)
    destino = os.path.join(sub, "destino.bin")
    origen = os.path.join(sub, "origen.bin")
    with open(origen, "wb") as f:
        f.write(b"N" * 2000)

    r: dict = {}
    ctypes.set_last_error(0)
    h = k32.CreateFileW(destino, GENERIC_WRITE, 0, None, OPEN_ALWAYS,
                        FILE_ATTRIBUTE_NORMAL, None)
    r["asa_conseguida"] = h not in (0, INVALID)
    r["error_al_abrir"] = ctypes.get_last_error()
    if not r["asa_conseguida"]:
        log("M5 CreateFileW FILE_SHARE_NONE: NO se pudo abrir")
        return r

    # (a) ¿excluye al tercero?
    registro = os.path.join(sub, "tercero.json")
    p = _lanzar_tercero("martillo", destino, registro, tope=1.5)
    p.wait(timeout=30)
    try:
        with open(registro, encoding="utf-8") as f:
            d = json.load(f)
        r["tercero_intentos"] = d.get("intentos")
        r["tercero_aberturas"] = d.get("aberturas")
        r["tercero_errores"] = d.get("errores")
    except (OSError, ValueError) as e:
        r["tercero"] = f"sin registro: {e}"

    # (b) ¿me excluye a MÍ del `os.replace`, que es como acabaría el move?
    try:
        os.replace(origen, destino)
        r["os_replace_con_mi_asa_abierta"] = "ok"
    except OSError as e:
        r["os_replace_con_mi_asa_abierta"] = _err(e)

    # (c) ¿y de un `shutil.move`?
    try:
        shutil.move(origen, destino)
        r["shutil_move_con_mi_asa_abierta"] = "ok"
    except OSError as e:
        r["shutil_move_con_mi_asa_abierta"] = _err(e)

    k32.CloseHandle(wt.HANDLE(h))
    log(f"M5 FILE_SHARE_NONE: asa={r['asa_conseguida']} "
        f"tercero {r.get('tercero_aberturas')}/{r.get('tercero_intentos')} aberturas, "
        f"os.replace propio -> {r['os_replace_con_mi_asa_abierta']}")
    return r


def main() -> int:
    if sys.platform != "win32":
        print("Esta sonda es de Windows.")
        return 1
    tmp = tempfile.mkdtemp(prefix="filex-ventana-mec-")
    antes = sorted(os.listdir(tmp))
    res = {"cuando": time.strftime("%Y-%m-%d %H:%M:%S"),
           "python": sys.version.split()[0],
           "desechable": tmp,
           "listado_antes": antes}
    try:
        res["M1"] = m1_move_destino_existente(tmp)
        res.update(m2_m3_tercero_abierto(tmp))
        res["M4"] = m4_cruzar_volumen(tmp)
        res["M5"] = m5_file_share_none(tmp)
    finally:
        res["listado_despues_del_desechable"] = sorted(os.listdir(tmp))
        with open(os.path.join(AQUI, "sonda_mecanismo.json"), "w",
                  encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
        os.makedirs(os.path.join(AQUI, "logs"), exist_ok=True)
        with open(os.path.join(AQUI, "logs", "sonda_mecanismo.log"), "w",
                  encoding="utf-8") as f:
            f.write("\n".join(log_lineas) + "\n")
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

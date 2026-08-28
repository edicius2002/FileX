"""¿Se puede SOLTAR desde otro hilo un candado tomado en el hilo principal?

La pregunta no es académica: N10 quiere tomar el candado del trabajo **antes**
de arrancar su hilo —para que no exista una ventana en la que el trabajo ya
figura `working` en el disco y todavía no tiene candado, que es un falso
huérfano con horario— y soltarlo **dentro** de ese hilo, en el `finally`.

Y hay un motivo documentado para dudar: **los mutex de Windows tienen afinidad
de hilo**. `ReleaseMutex` desde un hilo que no es el dueño falla con
`ERROR_NOT_OWNER`. `filex/cerrojo.py` toma DOS primitivos —el mutex con nombre y
el candado de rango de bytes— y `_soltar_mutex` se traga el error y cierra el
asa igualmente, así que la pregunta real es la de comportamiento: **después de
`soltar()` desde otro hilo, ¿`esta_libre()` dice que sí?**

Se sondea en ejecución, no se deduce (`CLAUDE.md` §5). Tres celdas:

  A  tomar y soltar en el MISMO hilo            (control positivo)
  B  tomar en el principal, soltar en otro hilo (el caso de N10)
  C  ¿qué devuelve `ReleaseMutex` en el caso B? (el mecanismo, no el síntoma)

Uso:  python bench/salidas-cancelacion-procesos/sonda_afinidad.py
Escribe `sonda_afinidad.json`. No usa la GPU. No lanza contenedores.
"""

from __future__ import annotations

import ctypes
import json
import os
import sys
import threading

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import cerrojo  # noqa: E402

SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "sonda_afinidad.json")


def celda_a() -> dict:
    """Control positivo: tomar y soltar en el mismo hilo."""
    c = cerrojo.Candado("filex-sonda-afinidad-A")
    tomado = c.tomar()
    c.soltar()
    return {"tomado": tomado, "libre_despues": cerrojo.esta_libre(
        "filex-sonda-afinidad-A")}


def celda_b() -> dict:
    """El caso de N10: se toma en el principal y se suelta en otro hilo."""
    nombre = "filex-sonda-afinidad-B"
    c = cerrojo.Candado(nombre)
    tomado = c.tomar()
    ocupado_mientras = not cerrojo.esta_libre(nombre)
    caja = {}

    def suelta():
        c.soltar()
        caja["hilo"] = threading.get_ident()

    h = threading.Thread(target=suelta)
    h.start()
    h.join(timeout=10)
    return {"tomado": tomado,
            "ocupado_mientras_lo_teniamos": ocupado_mientras,
            "libre_despues": cerrojo.esta_libre(nombre),
            "solto_otro_hilo": caja.get("hilo") != threading.get_ident()}


def celda_c() -> dict:
    """El mecanismo: qué devuelve de verdad `ReleaseMutex` desde otro hilo.

    Se hace a mano contra `kernel32`, sin pasar por `Candado`, porque
    `_soltar_mutex` se come el resultado a propósito y aquí lo que interesa es
    justo ese resultado.
    """
    if sys.platform != "win32":
        return {"aplica": False, "motivo": "no es Windows"}
    k32, extra = cerrojo._kernel32()
    if k32 is None:
        return {"aplica": False, "motivo": str(extra)}
    ct, sa = extra
    nombre = "Global\\filex-sonda-afinidad-C"
    h = k32.CreateMutexW(ct.byref(sa), False, nombre)
    r = k32.WaitForSingleObject(h, 0)
    caja = {}

    def suelta():
        ctypes.set_last_error(0)
        caja["ok"] = bool(k32.ReleaseMutex(h))
        caja["err"] = ctypes.get_last_error()

    t = threading.Thread(target=suelta)
    t.start()
    t.join(timeout=10)
    # Y la pregunta que decide el diseño: cerrar el asa, ¿libera el nombre?
    k32.CloseHandle(h)
    h2 = k32.CreateMutexW(ct.byref(sa), False, nombre)
    r2 = k32.WaitForSingleObject(h2, 0)
    k32.ReleaseMutex(h2)
    k32.CloseHandle(h2)
    return {"aplica": True, "wait_inicial": r,
            "release_desde_otro_hilo_ok": caja.get("ok"),
            "release_desde_otro_hilo_err": caja.get("err"),
            "ERROR_NOT_OWNER": 288,
            "wait_tras_cerrar_el_asa": r2,
            "WAIT_OBJECT_0": 0, "WAIT_TIMEOUT": 0x102}


def main() -> None:
    d = {"plataforma": sys.platform, "pid": os.getpid(),
         "A_mismo_hilo": celda_a(), "B_otro_hilo": celda_b(),
         "C_release_crudo": celda_c()}
    with open(SALIDA, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=2)
    print(json.dumps(d, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

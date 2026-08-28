"""¿A quién deja entrar el mutex `Global\\` con su descriptor por defecto?

Es la pregunta que decide si el mutex sirve **para lo que se le pide**. Un mutex
de máquina que otro usuario **no puede abrir** no cierra el agujero: lo mueve.
Desde el otro usuario, `CreateMutexW` devolvería `ERROR_ACCESS_DENIED` y un
código escrito con prisa lo confundiría con «no hay infraestructura» y
**degradaría a cerrojo de usuario justo en el caso que el mutex venía a cubrir**
— la trampa 13 otra vez, un fallo que se disfraza de otra cosa.

Se mide el SDDL real del objeto en los dos casos, con `GetSecurityInfo`:
descriptor por defecto y descriptor explícito.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import os
import time

AQUI = os.path.dirname(os.path.abspath(__file__))

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
adv = ctypes.WinDLL("advapi32", use_last_error=True)

k32.CreateMutexW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.LPCWSTR]
k32.CreateMutexW.restype = wt.HANDLE

adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
    wt.LPCWSTR, wt.DWORD, ctypes.POINTER(ctypes.c_void_p),
    ctypes.POINTER(wt.ULONG)]
adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wt.BOOL
adv.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [
    ctypes.c_void_p, wt.DWORD, wt.DWORD, ctypes.POINTER(wt.LPWSTR),
    ctypes.POINTER(wt.ULONG)]
adv.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype = wt.BOOL
adv.GetSecurityInfo.argtypes = [wt.HANDLE, wt.DWORD, wt.DWORD,
                                ctypes.c_void_p, ctypes.c_void_p,
                                ctypes.c_void_p, ctypes.c_void_p,
                                ctypes.POINTER(ctypes.c_void_p)]
adv.GetSecurityInfo.restype = wt.DWORD

SE_KERNEL_OBJECT = 6
OWNER_SI, GROUP_SI, DACL_SI = 0x1, 0x2, 0x4
SDDL_REVISION_1 = 1


class SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("nLength", wt.DWORD), ("lpSecurityDescriptor", ctypes.c_void_p),
                ("bInheritHandle", wt.BOOL)]


def sddl_de(h) -> str:
    sd = ctypes.c_void_p()
    err = adv.GetSecurityInfo(h, SE_KERNEL_OBJECT,
                              OWNER_SI | GROUP_SI | DACL_SI,
                              None, None, None, None, ctypes.byref(sd))
    if err != 0:
        return f"(GetSecurityInfo error {err})"
    s = wt.LPWSTR()
    n = wt.ULONG()
    ok = adv.ConvertSecurityDescriptorToStringSecurityDescriptorW(
        sd, SDDL_REVISION_1, OWNER_SI | GROUP_SI | DACL_SI,
        ctypes.byref(s), ctypes.byref(n))
    if not ok:
        return f"(Convert error {ctypes.get_last_error()})"
    out = s.value
    k32.LocalFree(s)
    return out


def sa_desde_sddl(sddl: str):
    sd = ctypes.c_void_p()
    n = wt.ULONG()
    ok = adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        sddl, SDDL_REVISION_1, ctypes.byref(sd), ctypes.byref(n))
    if not ok:
        raise OSError(ctypes.get_last_error(), "SDDL no convertible")
    sa = SECURITY_ATTRIBUTES()
    sa.nLength = ctypes.sizeof(sa)
    sa.lpSecurityDescriptor = sd
    sa.bInheritHandle = False
    return sa


def main() -> int:
    res: dict = {"cuando": time.strftime("%Y-%m-%dT%H:%M:%S")}
    sello = f"filex-dacl-{os.getpid()}"

    print("== A. mutex Global\\ con descriptor POR DEFECTO ==")
    h = k32.CreateMutexW(None, False, "Global\\" + sello + "-def")
    s_def = sddl_de(h) if h else "(no se creo)"
    print(f"  SDDL: {s_def}")
    todos_def = "(A;;" in s_def and (";WD)" in s_def or ";BU)" in s_def)
    print(f"  -> lo puede abrir CUALQUIER usuario (WD/BU en la DACL): {todos_def}")
    res["A_por_defecto"] = {"sddl": s_def, "abierto_a_todos": todos_def}
    if h:
        k32.CloseHandle(h)

    print("== B. mutex Global\\ con descriptor EXPLICITO (Everyone) ==")
    # `D:(A;;0x1F0001;;;WD)` = MUTEX_ALL_ACCESS para «Everyone». Es lo que hace
    # falta para que el cerrojo sea de MÁQUINA y no de usuario; sin esto el
    # objeto es de máquina en el NOMBRE y de usuario en el ACCESO.
    sddl = "D:(A;;0x1F0001;;;WD)"
    try:
        sa = sa_desde_sddl(sddl)
        h2 = k32.CreateMutexW(ctypes.byref(sa), False, "Global\\" + sello + "-exp")
        e2 = ctypes.get_last_error()
        s_exp = sddl_de(h2) if h2 else "(no se creo)"
        print(f"  creado={bool(h2)} err={e2}")
        print(f"  SDDL: {s_exp}")
        res["B_explicito"] = {"pedido": sddl, "creado": bool(h2),
                              "last_error": e2, "sddl": s_exp,
                              "abierto_a_todos": ";WD)" in s_exp}
        if h2:
            k32.CloseHandle(h2)
    except OSError as e:
        print(f"  FALLO: {e}")
        res["B_explicito"] = {"error": str(e)}

    with open(os.path.join(AQUI, "sonda_dacl.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

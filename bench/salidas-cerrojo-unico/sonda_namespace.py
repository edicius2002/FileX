"""¿El mutex `Global\\` está DE VERDAD en el namespace de la máquina?

La sonda 1 midió que `CreateMutexW("Global\\...")` devuelve un handle con
`GetLastError = 0` desde un token de **integridad media, con
`BUILTIN\\Administradores` marcado «solo para denegar» y sin
`SeCreateGlobalPrivilege` en la lista**. Eso contradice lo que N-b dio por
supuesto, así que **no vale con creérselo: hay que ver el objeto donde dice
estar** (R7, y la trampa 13 en su forma general — un `'GPU'` que corre en CPU).

Tres comprobaciones independientes:

  A. `Local\\S` y `Global\\S` **vivos a la vez**: si fueran el mismo objeto, el
     segundo `CreateMutexW` devolvería `ERROR_ALREADY_EXISTS (183)`.
  B. **Enumerar `\\BaseNamedObjects`** —el directorio de objetos GLOBAL de la
     máquina, no el de la sesión— con `NtOpenDirectoryObject` /
     `NtQueryDirectoryObject`, y buscar nuestro nombre ahí. Y buscarlo también
     en `\\Sessions\\<n>\\BaseNamedObjects`, que es el de la sesión.
  C. En qué **sesión** corremos y cuántas hay, que es lo que decide si «global»
     compra algo en esta máquina.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import os
import subprocess
import time

AQUI = os.path.dirname(os.path.abspath(__file__))

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
nt = ctypes.WinDLL("ntdll")

k32.CreateMutexW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.LPCWSTR]
k32.CreateMutexW.restype = wt.HANDLE
k32.ProcessIdToSessionId.argtypes = [wt.DWORD, ctypes.POINTER(wt.DWORD)]
ERROR_ALREADY_EXISTS = 183


class UNICODE_STRING(ctypes.Structure):
    _fields_ = [("Length", wt.USHORT), ("MaximumLength", wt.USHORT),
                ("Buffer", wt.LPWSTR)]


class OBJECT_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Length", wt.ULONG), ("RootDirectory", wt.HANDLE),
                ("ObjectName", ctypes.POINTER(UNICODE_STRING)),
                ("Attributes", wt.ULONG), ("SecurityDescriptor", ctypes.c_void_p),
                ("SecurityQualityOfService", ctypes.c_void_p)]


class OBJECT_DIRECTORY_INFORMATION(ctypes.Structure):
    _fields_ = [("Name", UNICODE_STRING), ("TypeName", UNICODE_STRING)]


DIRECTORY_QUERY = 0x0001
DIRECTORY_TRAVERSE = 0x0002
MUTANT_QUERY_STATE = 0x0001
SYNCHRONIZE = 0x00100000

# Sin `argtypes` el primer intento devolvió 0 objetos en los dos directorios y
# **sin error**, que es justo el fallo que la trampa 13 describe en su forma
# general: una respuesta falsa sin un solo mensaje. `BOOLEAN` de NT es de UN
# byte (`c_ubyte`), no el `BOOL` de 4 de Windows, y los punteros hay que
# declararlos o ctypes los trunca a `int` en 64 bits.
nt.NtOpenDirectoryObject.argtypes = [ctypes.POINTER(wt.HANDLE), wt.ULONG,
                                     ctypes.c_void_p]
nt.NtOpenDirectoryObject.restype = ctypes.c_long
nt.NtQueryDirectoryObject.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.ULONG,
                                      ctypes.c_ubyte, ctypes.c_ubyte,
                                      ctypes.POINTER(wt.ULONG),
                                      ctypes.POINTER(wt.ULONG)]
nt.NtQueryDirectoryObject.restype = ctypes.c_long
nt.NtOpenMutant.argtypes = [ctypes.POINTER(wt.HANDLE), wt.ULONG,
                            ctypes.c_void_p]
nt.NtOpenMutant.restype = ctypes.c_long


def _atributos(ruta: str):
    """`(OBJECT_ATTRIBUTES, refs)` — hay que retener las referencias o el GC se
    lleva el `UNICODE_STRING` antes de la llamada."""
    us = UNICODE_STRING()
    us.Buffer = ruta
    us.Length = len(ruta) * 2
    us.MaximumLength = us.Length + 2
    oa = OBJECT_ATTRIBUTES()
    oa.Length = ctypes.sizeof(OBJECT_ATTRIBUTES)
    oa.RootDirectory = None
    oa.ObjectName = ctypes.pointer(us)
    oa.Attributes = 0x00000040          # OBJ_CASE_INSENSITIVE
    oa.SecurityDescriptor = None
    oa.SecurityQualityOfService = None
    return oa, us


def abrir_mutex_por_ruta(ruta: str) -> tuple[bool, str]:
    """**La prueba directa de dónde vive el objeto.** `NtOpenMutant` sí acepta
    una ruta absoluta del namespace, así que preguntar por
    `\\BaseNamedObjects\\<sello>` responde sin enumerar nada."""
    oa, _us = _atributos(ruta)
    h = wt.HANDLE()
    st = nt.NtOpenMutant(ctypes.byref(h), MUTANT_QUERY_STATE | SYNCHRONIZE,
                         ctypes.byref(oa))
    st &= 0xFFFFFFFF
    if st == 0:
        k32.CloseHandle(h)
        return True, "0x00000000"
    return False, f"{st:#010x}"


def listar_directorio_de_objetos(ruta: str) -> tuple[list[str], str]:
    """Los nombres que cuelgan de un directorio del namespace del kernel."""
    oa, _us = _atributos(ruta)
    h = wt.HANDLE()
    st = nt.NtOpenDirectoryObject(ctypes.byref(h),
                                  DIRECTORY_QUERY | DIRECTORY_TRAVERSE,
                                  ctypes.byref(oa))
    if st & 0xFFFFFFFF != 0:
        return [], f"NtOpenDirectoryObject NTSTATUS={st & 0xFFFFFFFF:#010x}"

    nombres: list[str] = []
    buf = ctypes.create_string_buffer(64 * 1024)
    ctx = wt.ULONG(0)
    devuelto = wt.ULONG(0)
    primera = 1
    while True:
        st = nt.NtQueryDirectoryObject(h, buf, ctypes.sizeof(buf), 0,
                                       primera, ctypes.byref(ctx),
                                       ctypes.byref(devuelto))
        primera = 0
        if st & 0xFFFFFFFF not in (0, 0x00000103):   # STATUS_MORE_ENTRIES
            if not nombres:
                k32.CloseHandle(h)
                return [], f"NtQueryDirectoryObject NTSTATUS={st & 0xFFFFFFFF:#010x}"
            break
        arr = ctypes.cast(buf, ctypes.POINTER(OBJECT_DIRECTORY_INFORMATION))
        i = 0
        while arr[i].Name.Length:
            nombres.append(arr[i].Name.Buffer[:arr[i].Name.Length // 2])
            i += 1
        if st & 0xFFFFFFFF == 0:
            break
    k32.CloseHandle(h)
    return nombres, ""


def main() -> int:
    res: dict = {"cuando": time.strftime("%Y-%m-%dT%H:%M:%S")}
    sello = f"filex-ns-{os.getpid()}"

    # --- C. en qué sesión corremos ------------------------------------------
    sid = wt.DWORD(0)
    k32.ProcessIdToSessionId(os.getpid(), ctypes.byref(sid))
    ses = int(sid.value)
    print(f"== C. sesion de este proceso: {ses} ==")
    try:
        q = subprocess.run(["qwinsta"], capture_output=True, text=True,
                           timeout=30).stdout
    except Exception as e:
        q = f"(qwinsta fallo: {e})"
    print(q.strip()[:600])
    res["C_sesion"] = {"sesion": ses, "qwinsta": q.strip()}

    # --- A. ¿son objetos distintos? -----------------------------------------
    print("== A. Local\\S y Global\\S VIVOS A LA VEZ ==")
    ctypes.set_last_error(0)
    h_local = k32.CreateMutexW(None, False, "Local\\" + sello)
    e_local = ctypes.get_last_error()
    ctypes.set_last_error(0)
    h_glob = k32.CreateMutexW(None, False, "Global\\" + sello)
    e_glob = ctypes.get_last_error()
    distintos = bool(h_local) and bool(h_glob) and e_glob != ERROR_ALREADY_EXISTS
    print(f"  Local\\  handle={bool(h_local)} err={e_local}")
    print(f"  Global\\ handle={bool(h_glob)} err={e_glob} "
          f"({'ALREADY_EXISTS: ES EL MISMO OBJETO' if e_glob == ERROR_ALREADY_EXISTS else 'objeto NUEVO'})")
    print(f"  -> son objetos DISTINTOS: {distintos}")
    res["A_distintos"] = {"local_err": e_local, "global_err": e_glob,
                          "distintos": distintos}

    # --- B. verlo en el namespace, con los dos handles aún abiertos ---------
    print("== B. buscarlo en el namespace del kernel ==")
    res["B_namespace"] = {}
    for etiqueta, ruta in (("GLOBAL (de maquina)", "\\BaseNamedObjects"),
                           (f"SESION {ses}", f"\\Sessions\\{ses}\\BaseNamedObjects")):
        nombres, err = listar_directorio_de_objetos(ruta)
        esta = sello in nombres
        print(f"  {ruta:42s} n={len(nombres):5d} "
              f"{'-> NUESTRO NOMBRE ESTA AQUI' if esta else '   (no esta)'}"
              f"{'  ERROR: ' + err if err else ''}")
        res["B_namespace"][etiqueta] = {"ruta": ruta, "objetos": len(nombres),
                                        "contiene_el_nuestro": esta, "error": err}

    # --- B2. la prueba directa: abrirlo por RUTA ABSOLUTA -------------------
    print("== B2. abrirlo por ruta absoluta del namespace ==")
    res["B2_por_ruta"] = {}
    for etiqueta, ruta in (
            ("global", "\\BaseNamedObjects\\" + sello),
            ("sesion", f"\\Sessions\\{ses}\\BaseNamedObjects\\" + sello),
            ("global_inexistente", "\\BaseNamedObjects\\" + sello + "-NO-EXISTE")):
        ok, st = abrir_mutex_por_ruta(ruta)
        print(f"  {ruta:56s} -> {'ABRE' if ok else 'no abre'}  NTSTATUS={st}")
        res["B2_por_ruta"][etiqueta] = {"ruta": ruta, "abre": ok, "ntstatus": st}

    k32.CloseHandle(h_local)
    k32.CloseHandle(h_glob)

    veredicto = distintos and (
        res["B_namespace"]["GLOBAL (de maquina)"]["contiene_el_nuestro"]
        or (res["B2_por_ruta"]["global"]["abre"]
            and not res["B2_por_ruta"]["global_inexistente"]["abre"]))
    res["veredicto_global_de_verdad"] = veredicto
    print(f"== VEREDICTO: el mutex Global\\ vive en el namespace de MAQUINA: "
          f"{veredicto} ==")

    with open(os.path.join(AQUI, "sonda_namespace.json"), "w",
              encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""S6 / hito 6 — el MECANISMO del fallo de coresidencia, sondeado en ejecucion.

La fase `coresidente` muere en 10 de 10 con
`Could not load symbol cudnnGetLibConfig. Error code 127` y `rc=0xC0000409`, y
la fase `coresidente_inv` —el mismo proceso, cargando el OCR primero— funciona.
La explicacion COMODA es «se estorban»; eso no es un mecanismo.

Esta sonda mira lo unico que decide: **cuantas `cudnn64_9.dll` hay en el venv,
de que tamano, cual exporta `cudnnGetLibConfig`, y cual se queda cargada segun
el orden de importacion**. Se sondea, no se deduce (`av1_nvenc` aparece listado
y no funciona; `paddlex` declara `limit_type='max'` y la sonda mide `'min'`).

uso: sonda_cudnn.py <inventario|orden_audio|orden_ocr>
"""
import ctypes
import ctypes.util
import glob
import hashlib
import json
import os
import sys

SP = os.path.join(os.path.dirname(os.path.dirname(sys.executable)),
                  "Lib", "site-packages")
SIMBOLO = b"cudnnGetLibConfig"


def _cargadas():
    """Las DLL cargadas en ESTE proceso cuyo nombre lleva `cudnn`.

    Se leen del propio proceso con `EnumProcessModules`: preguntar al sistema
    que hay cargado es sondear; mirar el disco es deducir.
    """
    import ctypes.wintypes as w
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    # **Los `argtypes` no son ceremonia en 64 bits**: sin ellos, ctypes pasa los
    # punteros y el HANDLE como `int` de 32 bits, `EnumProcessModules` falla y la
    # sonda devuelve una lista vacia que se lee como «no hay ninguna cargada».
    # Es el mismo error de forma que la trampa 66, y aqui lo destapo el control
    # positivo del total de modulos.
    k32.GetCurrentProcess.restype = w.HANDLE
    psapi.EnumProcessModules.argtypes = [w.HANDLE, ctypes.POINTER(w.HMODULE),
                                         w.DWORD, ctypes.POINTER(w.DWORD)]
    psapi.EnumProcessModules.restype = w.BOOL
    psapi.GetModuleFileNameExW.argtypes = [w.HANDLE, w.HMODULE, w.LPWSTR, w.DWORD]
    psapi.GetModuleFileNameExW.restype = w.DWORD
    h = k32.GetCurrentProcess()
    n = 4096
    arr = (w.HMODULE * n)()
    need = w.DWORD()
    if not psapi.EnumProcessModules(h, arr, ctypes.sizeof(arr), ctypes.byref(need)):
        return {"total_modulos": 0, "cudnn": [],
                "error": ctypes.get_last_error()}
    cuantos = need.value // ctypes.sizeof(w.HMODULE)
    fuera = []
    todos = 0
    buf = ctypes.create_unicode_buffer(1024)
    for i in range(cuantos):
        if psapi.GetModuleFileNameExW(h, arr[i], buf, 1024):
            todos += 1
            if "cudnn" in buf.value.lower():
                fuera.append(buf.value)
    # **Control positivo de la propia sonda.** Una lista vacia de `cudnn` puede
    # significar «no hay ninguna cargada» o «la sonda no lee nada», y son cosas
    # distintas (trampa 66). El total de modulos lo separa: si es 0, la rota es
    # la sonda.
    return {"total_modulos": todos, "cudnn": sorted(fuera)}


def _inventario():
    # cuDNN 9 esta PARTIDA: `cudnn64_9.dll` es un despachador que carga
    # `cudnn_graph64_9.dll`, `cudnn_ops64_9.dll`, etc. Buscar el simbolo solo en
    # el despachador es mirar el catalogo en vez del elemento (trampa 66): hay
    # que barrer TODAS las `cudnn*.dll`.
    filas = []
    for p in sorted(glob.glob(os.path.join(SP, "**", "cudnn*.dll"),
                              recursive=True)):
        d = None
        tiene = None
        try:
            d = ctypes.CDLL(p)
            tiene = bool(ctypes.cast(getattr(d, SIMBOLO.decode()), ctypes.c_void_p))
        except (OSError, AttributeError) as e:
            tiene = False if isinstance(e, AttributeError) else None
        filas.append({
            "ruta": p.replace(SP + os.sep, ""),
            "bytes": os.path.getsize(p),
            "sha256_12": hashlib.sha256(open(p, "rb").read()).hexdigest()[:12],
            "exporta_cudnnGetLibConfig": tiene})
    return filas


modo = sys.argv[1] if len(sys.argv) > 1 else "inventario"
r = {"modo": modo, "python": sys.executable}

if modo == "inventario":
    r["dlls"] = _inventario()
elif modo in ("orden_audio", "orden_ocr"):
    # **El `import` NO carga cuDNN**: la carga es perezosa y ocurre al construir
    # el modelo. Sondeado: con solo importar, la lista de modulos sale VACIA en
    # los dos ordenes. Por eso aqui se CONSTRUYE, que es lo unico que reproduce
    # el caso — «sondear en ejecucion, no deducir» tambien vale para el momento.
    def _audio():
        from faster_whisper import WhisperModel
        return WhisperModel("distil-large-v3", device="cuda",
                            compute_type="float16")

    def _ocr():
        import torch
        os.add_dll_directory(os.path.join(os.path.dirname(torch.__file__), "lib"))
        from rapidocr import (EngineType, LangDet, LangRec, ModelType,
                              OCRVersion, RapidOCR)
        return RapidOCR(params={
            "EngineConfig.onnxruntime.use_cuda": True,
            "Det.engine_type": EngineType.ONNXRUNTIME,
            "Cls.engine_type": EngineType.ONNXRUNTIME,
            "Rec.engine_type": EngineType.ONNXRUNTIME,
            "Det.lang_type": LangDet.CH, "Rec.lang_type": LangRec.CH,
            "Det.ocr_version": OCRVersion("PP-OCRv6"),
            "Rec.ocr_version": OCRVersion("PP-OCRv6"),
            "Det.model_type": ModelType("small"),
            "Rec.model_type": ModelType("small")})

    primero, segundo = ((_audio, "audio"), (_ocr, "ocr"))
    if modo == "orden_ocr":
        primero, segundo = ((_ocr, "ocr"), (_audio, "audio"))
    r["antes"] = _cargadas()
    _a = primero[0]()
    r["tras_" + primero[1]] = _cargadas()
    # Si el proceso muere aqui, el JSON no se escribe: el `rc` lo dice, y el
    # log conserva la linea de `tras_...` que si llego a imprimirse.
    print(json.dumps({"parcial": r}, ensure_ascii=False), flush=True)
    _b = segundo[0]()
    r["tras_" + segundo[1]] = _cargadas()

print(json.dumps(r, ensure_ascii=False, indent=2))

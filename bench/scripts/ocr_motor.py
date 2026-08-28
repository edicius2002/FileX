# -*- coding: utf-8 -*-
"""FASE 2-B/C: banco de motores de OCR *sin* docling, sobre las paginas ya rasterizadas.

Aisla el coste del OCR puro (deteccion + reconocimiento), sin la etapa de maquetacion
de docling, para poder comparar motores entre si y CPU contra GPU.

=============================================================================
CAMBIO DEL 2026-08-28 (B11, agente G5, informe `bench/ocr-produccion-sidecar.md`)
=============================================================================
La configuracion POR DEFECTO de `rapidocr` pasa de

    PP-OCRv5 mobile, normalizacion por defecto de RapidOCR   (hasta el 28/08)
a
    PP-OCRv6 small,  normalizacion R6                        (desde el 28/08)

**Y el cambio es de LAS DOS COSAS A LA VEZ, a proposito.** Sobre el `PP-OCRv5
mobile` que este arnes usaba, R6 **no es recomendable**: empeora 4 de 15 celdas
(`bench/ppp-y-normalizacion.md` 3.3). La unica configuracion con **0 regresiones
sobre 15 documentos** es la pareja `PP-OCRv6 small` + R6, y es la que se adopta.
Aplicar R6 sin cambiar de checkpoint seria justo la trampa 17.

**LA VIA ANTERIOR NO SE HA BORRADO.** `RO_LEGADO=1` reproduce, bit a bit, lo que
este arnes hacia antes del 28/08: v5 mobile y la normalizacion de fabrica. Las
cifras publicadas por informes que usaron este arnes se reproducen con esa
bandera, y solo con ella.

Las tres piezas se pueden mover por separado (`RO_VER`, `RO_TIPO`, `RO_NORM`),
porque **un `k`, un CER o un tiempo publicados sin su checkpoint y su
normalizacion no son un numero** (trampas 8 y 17). Por eso el resumen guarda
tambien el `mean`/`std` que el detector aplica DE VERDAD, leido del objeto ya
construido: "he puesto ImageNet" es una intencion, no una medida.

Este fichero NO evalua precision: la metrica vive en `bench/scripts/ocr_eval.py`
(canonica ACENTUADA desde el 2026-08-28). Aqui solo se producen los .txt.

uso: ocr_motor.py <easyocr|rapidocr|paddleocr> <cpu|cuda> [etiqueta]
env: REPS (9), IMG, OUT, DOCS, RO_LEGADO, RO_VER, RO_TIPO, RO_NORM
"""
import json
import os
import statistics
import subprocess
import sys
import time

IMG = os.environ.get("IMG", r"D:\Work\research\FileX\bench\salidas-fase2\img")
OUT = os.environ.get("OUT", r"D:\Work\research\FileX\bench\salidas-fase2")
DOCS = os.environ.get(
    "DOCS",
    "patologico_escaneado,escaneado_d1,escaneado_d2,escaneado_d3").split(",")
REPS = int(os.environ.get("REPS", "9"))

# --- R6: la correccion de normalizacion, con sus seis numeros ------------------
# `rapidocr/config.yaml` fija Det.mean y Det.std a 0,5 para TODAS las versiones de
# PP-OCR, mientras los ocho `inference.yml` que Baidu distribuye con los pesos
# declaran las estadisticas de ImageNet. El desajuste se aplica en
# `rapidocr/ch_ppocr_det/utils.py:71` y cuesta hasta 72,15 puntos de CER.
# Los cuatro valores de post-proceso salen del mismo `inference.yml`.
R6 = {
    "Det.mean": [0.485, 0.456, 0.406],
    "Det.std": [0.229, 0.224, 0.225],
    "Det.thresh": 0.2,
    "Det.box_thresh": 0.45,
    "Det.unclip_ratio": 1.4,
    "Det.max_candidates": 3000,
}

motor = sys.argv[1]
dispositivo = sys.argv[2] if len(sys.argv) > 2 else "cuda"
gpu = dispositivo == "cuda"

# Configuracion de rapidocr: primero el bloque (legado o vigente), luego los
# afinados sueltos, que ganan.
legado = os.environ.get("RO_LEGADO") == "1"
ro_ver = os.environ.get("RO_VER", "PP-OCRv5" if legado else "PP-OCRv6")
ro_tipo = os.environ.get("RO_TIPO", "mobile" if legado else "small")
ro_norm = os.environ.get("RO_NORM", "0" if legado else "1")

# La etiqueta por defecto lleva la configuracion DENTRO: dos configuraciones
# distintas no pueden escribir el mismo .txt (regla del fichero por agente, y
# ademas evita pisar las salidas publicadas antes del 28/08).
if len(sys.argv) > 3:
    etiqueta = sys.argv[3]
elif motor == "rapidocr":
    etiqueta = (f"motor_{motor}_{dispositivo}_{ro_ver.replace('-', '')}"
                f"{ro_tipo}_R6-{ro_norm}")
else:
    etiqueta = f"motor_{motor}_{dispositivo}"

os.makedirs(OUT, exist_ok=True)


def vram():
    try:
        return int(subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            timeout=20).stdout.strip().splitlines()[0])
    except Exception:
        return -1


base_vram = vram()
meta = {"etiqueta": etiqueta, "motor": motor, "dispositivo": dispositivo,
        "via_entrada": "ruta", "vram_base_MiB": base_vram,
        "img_dir": IMG, "docs": DOCS, "reps": REPS}

# ---------------------------------------------------------------- carga del motor
# `carga_s` se desglosa en import y construccion: para una CLI que convierte un
# fichero y termina, la carga en frio ES el coste, y las dos mitades no se
# optimizan igual.
t0 = time.perf_counter()

if motor == "easyocr":
    import torch
    import easyocr
    meta["import_s"] = round(time.perf_counter() - t0, 3)
    t1 = time.perf_counter()
    lector = easyocr.Reader(["es", "en"], gpu=gpu, verbose=False)
    meta["torch"] = torch.__version__
    meta["torch_cuda"] = torch.cuda.is_available()

    def leer(ruta):
        r = lector.readtext(ruta, detail=0, paragraph=False)
        return " ".join(r)

elif motor == "rapidocr":
    import torch
    os.add_dll_directory(os.path.join(os.path.dirname(torch.__file__), "lib"))
    from rapidocr import EngineType, LangDet, LangRec, ModelType, OCRVersion, RapidOCR
    import onnxruntime
    meta["onnxruntime"] = onnxruntime.__version__
    meta["import_s"] = round(time.perf_counter() - t0, 3)
    t1 = time.perf_counter()
    params = {
        "EngineConfig.onnxruntime.use_cuda": gpu,
        "EngineConfig.onnxruntime.cuda_ep_cfg.device_id": 0,
        "Det.engine_type": EngineType.ONNXRUNTIME,
        "Cls.engine_type": EngineType.ONNXRUNTIME,
        "Rec.engine_type": EngineType.ONNXRUNTIME,
        "Det.lang_type": LangDet.CH,
        "Rec.lang_type": LangRec.CH,
        "Det.ocr_version": OCRVersion(ro_ver),
        "Rec.ocr_version": OCRVersion(ro_ver),
        "Det.model_type": ModelType(ro_tipo),
        "Rec.model_type": ModelType(ro_tipo),
    }
    if ro_norm == "1":
        params.update(R6)
    lector = RapidOCR(params=params)
    meta["config"] = {"legado": legado, "ocr_version": ro_ver,
                      "model_type": ro_tipo, "R6": ro_norm}
    # Lo APLICADO, no lo pedido: rapidocr/ch_ppocr_det/main.py:33-34 guarda
    # mean/std como atributos del TextDetector.
    td = getattr(lector, "text_det", None)
    pp = getattr(td, "postprocess_op", None)
    meta["det_efectivo"] = {
        "mean": str(getattr(td, "mean", "?")), "std": str(getattr(td, "std", "?")),
        "thresh": getattr(pp, "thresh", "?"),
        "box_thresh": getattr(pp, "box_thresh", "?"),
        "unclip_ratio": getattr(pp, "unclip_ratio", "?"),
        "max_candidates": getattr(pp, "max_candidates", "?"),
        "limit_side_len": getattr(td, "limit_side_len", "?"),
        "limit_type": getattr(td, "limit_type", "?"),
    }
    # get_providers(), NUNCA get_device() (trampa 13): get_device() devuelve
    # 'GPU' mientras la sesion corre en CPU.
    try:
        meta["providers"] = list(lector.text_det.session.session.get_providers())
    except Exception as ex:
        meta["providers"] = f"{type(ex).__name__}: {ex}"
    # Que FICHERO de pesos se cargo DE VERDAD, para que la configuracion quede
    # en el resultado y no solo en la intencion.
    #
    # OJO, y esto costo una sonda entera: el camino `session.model_info` NO es
    # el modelo cargado, es el CATALOGO de todos los modelos que rapidocr sabe
    # descargar. Sacarle el primer `*.onnx` con una expresion regular devuelve
    # siempre `ch_PP-OCRv4_det_mobile.onnx` —el primero del catalogo— para las
    # tres tareas y para cualquier configuracion, y tiene toda la pinta de una
    # medida. El unico camino que lleva al fichero real es
    # `session.session._model_path` (sondeado en ejecucion, `sonda_pesos.py`).
    for tarea in ("text_det", "text_cls", "text_rec"):
        v = getattr(lector, tarea, None)
        for atributo in ("session", "session", "_model_path"):
            v = getattr(v, atributo, None)
            if v is None:
                break
        meta.setdefault("pesos", {})[tarea] = (
            os.path.basename(str(v)) if v is not None else "?")

    def leer(ruta):
        r = lector(ruta)
        return " ".join(r.txts) if r and r.txts else ""

elif motor == "paddleocr":
    import paddle
    from paddleocr import PaddleOCR
    meta["import_s"] = round(time.perf_counter() - t0, 3)
    t1 = time.perf_counter()
    meta["paddle"] = paddle.__version__
    meta["paddle_compiled_cuda"] = paddle.device.is_compiled_with_cuda()
    meta["paddle_device_count"] = paddle.device.cuda.device_count()
    lector = PaddleOCR(lang="es", device="gpu:0" if gpu else "cpu",
                       use_doc_orientation_classify=False,
                       use_doc_unwarping=False,
                       use_textline_orientation=True)

    def leer(ruta):
        r = lector.predict(ruta)
        out = []
        for p in r:
            d = p if isinstance(p, dict) else getattr(p, "json", {}).get("res", {})
            out.extend(d.get("rec_texts", []))
        return " ".join(out)

else:
    raise SystemExit(f"motor desconocido: {motor}")

meta["construccion_s"] = round(time.perf_counter() - t1, 3)
meta["carga_s"] = round(time.perf_counter() - t0, 2)
meta["vram_tras_carga_MiB"] = vram()
print(json.dumps(meta, ensure_ascii=False))
sys.stdout.flush()

# ---------------------------------------------------------------- medicion
pico = meta["vram_tras_carga_MiB"]
res = []
for nombre in DOCS:
    ruta = os.path.join(IMG, nombre + ".png")
    if not os.path.exists(ruta):
        continue
    try:
        texto = leer(ruta)          # calentamiento, fuera de la medicion
    except Exception as ex:
        e = {"archivo": nombre, "ok": False, "error": f"{type(ex).__name__}: {ex}"}
        res.append(e)
        print(json.dumps(e, ensure_ascii=False))
        continue
    ts = []
    for _ in range(REPS):
        t = time.perf_counter()
        texto = leer(ruta)
        ts.append((time.perf_counter() - t) * 1000)
        v = vram()
        if v > pico:
            pico = v
    dst = os.path.join(OUT, f"{etiqueta}__{nombre}.txt")
    open(dst, "w", encoding="utf-8").write(texto)
    s = sorted(ts)
    e = {"archivo": nombre, "ok": True, "ms_mediana": round(statistics.median(s), 1),
         "ms_min": round(s[0], 1), "ms_max": round(s[-1], 1), "n": len(s),
         "chars": len(texto), "salida": dst}
    res.append(e)
    print(json.dumps(e, ensure_ascii=False))
    sys.stdout.flush()

fin = {"evento": "fin", "vram_pico_MiB": pico, "vram_base_MiB": base_vram,
       "coste_propio_MiB": pico - base_vram,
       "docs_con_error": sum(1 for e in res if not e.get("ok"))}
print(json.dumps(fin, ensure_ascii=False))
json.dump({"meta": meta, "docs": res, "fin": fin},
          open(os.path.join(OUT, f"{etiqueta}__resumen.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

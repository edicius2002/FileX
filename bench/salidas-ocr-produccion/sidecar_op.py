# -*- coding: utf-8 -*-
"""G5 / B26 — el coste del reciclado de proceso del sidecar de OCR.

Mide, en UN proceso de vida larga, si el asignador de VRAM devuelve memoria
(`bench/k-por-motor.md` 6.3) y con que variable crece: numero de paginas,
megapixeles acumulados, o megapixeles del documento MAYOR visto.

Fases (`FASE` en el entorno elige cual):
  veneno      A: 3 paginas pequenas -> B: 1 folio grande -> C: 5 pequenas con
              esperas -> D: un folio aun mayor. Reproduce el atasco.
  control     lo mismo SIN el folio grande. Control positivo: sin el, un "no
              devuelve memoria" no significa nada (trampa 36).
  ascendente  0,55 -> 1,25 -> 2,22 -> 4,35 Mpx, uno detras de otro.
  repetido    la MISMA pagina de 1,25 Mpx N veces. Separa "paginas" de "Mpx".
  frio        carga el motor, procesa una pagina y sale. Para el coste de
              arranque en frio, que se mide con un proceso por repeticion.

Cada celda registra su resultado Y su excepcion: una salida de 0 bytes puede ser
un proceso que no arranco (trampa 25).

Dispositivo FIJADO por argumento: CPU y GPU no dan la misma salida (trampa 11).
Via de entrada: RUTA en los tres motores (la via vale hasta 12,58 puntos,
trampa 30; aqui es una constante declarada, no una variable).

uso: sidecar_op.py <easyocr|rapidocr|paddleocr> <cpu|cuda> <etiqueta>
env: FASE, IMGDIR, OUTDIR, REPETICIONES, ESPERA_S, RO_VER, RO_TIPO, RO_NORM
"""
import json
import os
import statistics
import subprocess
import sys
import time
import traceback

motor = sys.argv[1]
dispositivo = sys.argv[2] if len(sys.argv) > 2 else "cuda"
etiqueta = sys.argv[3] if len(sys.argv) > 3 else f"{motor}_{dispositivo}"
gpu = dispositivo == "cuda"

FASE = os.environ.get("FASE", "veneno")
IMGDIR = os.environ["IMGDIR"]
OUTDIR = os.environ["OUTDIR"]
REPETICIONES = int(os.environ.get("REPETICIONES", "12"))
ESPERA_S = float(os.environ.get("ESPERA_S", "20"))
os.makedirs(OUTDIR, exist_ok=True)
os.makedirs(os.path.join(OUTDIR, "texto"), exist_ok=True)

FFPROBE = r"D:\utils\ffmpeg\bin\ffprobe.exe"
if not os.path.exists(FFPROBE):
    FFPROBE = "ffprobe"

PEQ = "escaneado_d4_r150.png"      # 1,248 Mpx
MINI = "escaneado_d2_r100.png"     # 0,550 Mpx
MED = "escaneado_d4_r200.png"      # 2,221 Mpx
GRANDE = "escaneado_d4_r280.png"   # 4,352 Mpx  <- el folio que planto a PaddleOCR
ENORME = "escaneado_d4_r400.png"   # 8,882 Mpx


# ------------------------------------------------------- instrumentos y testigos
# Trampa 62: preguntarle al reloj su resolucion ANTES de cronometrar.
RELOJ = {"perf_counter": time.get_clock_info("perf_counter").resolution,
         "time": time.get_clock_info("time").resolution}


def _smi(consulta, tope=20):
    """Tope propio de 20 s: un testigo que puede tumbar la medicion no es un
    testigo (CLAUDE.md 3)."""
    try:
        r = subprocess.run(
            ["nvidia-smi", f"--query-gpu={consulta}",
             "--format=csv,noheader,nounits"],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=tope)
        return int(r.stdout.strip().splitlines()[0])
    except Exception:
        return -1


def vram_usada():
    return _smi("memory.used")


def vram_libre():
    return _smi("memory.free")


def testigo_monohilo(n=400000):
    """TESTIGO 1 - DERIVA. Ciego a la contencion multinucleo."""
    t = time.perf_counter()
    s = 0
    for i in range(n):
        s += i * i
    return round((time.perf_counter() - t) * 1000, 2)


def testigo_proceso(n=5, tope=20):
    """TESTIGO 2 - NIVEL. Con tope propio: si lo agota, devuelve el tope."""
    ms = []
    for _ in range(n):
        t = time.perf_counter()
        try:
            subprocess.run([FFPROBE, "-v", "quiet", "-version"],
                           stdin=subprocess.DEVNULL, capture_output=True,
                           timeout=tope)
        except Exception:
            return float(tope * 1000)
        ms.append((time.perf_counter() - t) * 1000)
    return round(statistics.median(ms), 2)


# ------------------------------------------------------------------ carga del motor
base_vram = vram_usada()
base_libre = vram_libre()
mono_ini = testigo_monohilo()
proc_ini = testigo_proceso()

meta = {"etiqueta": etiqueta, "motor": motor, "dispositivo": dispositivo,
        "fase": FASE, "via_entrada": "ruta", "reloj": RELOJ,
        "vram_base_MiB": base_vram, "vram_libre_base_MiB": base_libre,
        "testigo_mono_ini_ms": mono_ini, "testigo_proc_ini_ms": proc_ini}

t_import0 = time.perf_counter()
if motor == "easyocr":
    import torch
    import easyocr
    meta["torch"] = torch.__version__
    meta["torch_cuda"] = torch.cuda.is_available()
    t_import = time.perf_counter() - t_import0
    t_carga0 = time.perf_counter()
    lector = easyocr.Reader(["es", "en"], gpu=gpu, verbose=False)

    def leer(ruta):
        return " ".join(lector.readtext(ruta, detail=0, paragraph=False))

elif motor == "rapidocr":
    import torch
    os.add_dll_directory(os.path.join(os.path.dirname(torch.__file__), "lib"))
    from rapidocr import EngineType, LangDet, LangRec, ModelType, OCRVersion, RapidOCR
    import onnxruntime
    meta["onnxruntime"] = onnxruntime.__version__
    t_import = time.perf_counter() - t_import0
    t_carga0 = time.perf_counter()
    ver = OCRVersion(os.environ.get("RO_VER", "PP-OCRv6"))
    tipo = ModelType(os.environ.get("RO_TIPO", "small"))
    params = {
        "EngineConfig.onnxruntime.use_cuda": gpu,
        "EngineConfig.onnxruntime.cuda_ep_cfg.device_id": 0,
        "Det.engine_type": EngineType.ONNXRUNTIME,
        "Cls.engine_type": EngineType.ONNXRUNTIME,
        "Rec.engine_type": EngineType.ONNXRUNTIME,
        "Det.lang_type": LangDet(os.environ.get("RO_LANGDET", "ch")),
        "Rec.lang_type": LangRec(os.environ.get("RO_LANGREC", "ch")),
        "Det.ocr_version": ver, "Rec.ocr_version": ver,
        "Det.model_type": tipo, "Rec.model_type": tipo,
    }
    if os.environ.get("RO_NORM", "1") == "1":
        params.update({
            "Det.mean": [0.485, 0.456, 0.406],
            "Det.std": [0.229, 0.224, 0.225],
            "Det.thresh": 0.2, "Det.box_thresh": 0.45,
            "Det.unclip_ratio": 1.4, "Det.max_candidates": 3000,
        })
    lector = RapidOCR(params=params)
    meta["R6"] = os.environ.get("RO_NORM", "1")
    # Lo que el detector aplica DE VERDAD, no lo que se pidio.
    td = getattr(lector, "text_det", None)
    meta["det_efectivo"] = {"mean": str(getattr(td, "mean", "?")),
                            "std": str(getattr(td, "std", "?"))}
    # Sondeado en ejecucion, nunca get_device() (trampa 13).
    try:
        meta["providers"] = list(lector.text_det.session.session.get_providers())
    except Exception as ex:
        meta["providers"] = f"{type(ex).__name__}: {ex}"

    def leer(ruta):
        r = lector(ruta)
        return " ".join(r.txts) if r and r.txts else ""

elif motor == "paddleocr":
    import paddle
    from paddleocr import PaddleOCR
    meta["paddle"] = paddle.__version__
    meta["paddle_cuda"] = paddle.device.is_compiled_with_cuda()
    t_import = time.perf_counter() - t_import0
    t_carga0 = time.perf_counter()
    lector = PaddleOCR(lang="es", device="gpu:0" if gpu else "cpu",
                       use_doc_orientation_classify=False,
                       use_doc_unwarping=False,
                       use_textline_orientation=True)

    def leer(ruta):
        out = []
        for p in lector.predict(ruta):
            d = p if isinstance(p, dict) else getattr(p, "json", {}).get("res", {})
            out.extend(d.get("rec_texts", []))
        return " ".join(out)

else:
    raise SystemExit(f"motor desconocido: {motor}")

meta["import_s"] = round(t_import, 3)
meta["carga_modelo_s"] = round(time.perf_counter() - t_carga0, 3)
meta["arranque_frio_s"] = round(meta["import_s"] + meta["carga_modelo_s"], 3)
meta["vram_tras_carga_MiB"] = vram_usada()
print(json.dumps({"evento": "cargado", **meta}, ensure_ascii=False), flush=True)


# ------------------------------------------------------------------ una celda
celdas = []
mpx_acumulados = 0.0
mpx_maximo = 0.0


def mpx_de(nombre):
    with open(os.path.join(IMGDIR, nombre), "rb") as f:
        cab = f.read(33)
    return (int.from_bytes(cab[16:20], "big") *
            int.from_bytes(cab[20:24], "big")) / 1e6


def celda(nombre, paso, nota=""):
    global mpx_acumulados, mpx_maximo
    ruta = os.path.join(IMGDIR, nombre)
    m = mpx_de(nombre)
    antes = vram_usada()
    t = time.perf_counter()
    texto, err = "", None
    try:
        texto = leer(ruta)
    except Exception as ex:
        err = f"{type(ex).__name__}: {ex}"
        traceback.print_exc()
    ms = (time.perf_counter() - t) * 1000
    despues = vram_usada()
    mpx_acumulados += m
    mpx_maximo = max(mpx_maximo, m)
    dst = os.path.join(OUTDIR, "texto",
                       f"{etiqueta}__{paso:02d}_{nombre[:-4]}.txt")
    open(dst, "w", encoding="utf-8").write(texto)
    c = {"paso": paso, "img": nombre, "mpx": round(m, 3), "nota": nota,
         "ms": round(ms, 1), "chars": len(texto), "error": err,
         "vram_antes_MiB": antes, "vram_despues_MiB": despues,
         "vram_libre_MiB": vram_libre(),
         "delta_sobre_base_MiB": despues - base_vram,
         "mpx_acumulados": round(mpx_acumulados, 3),
         "mpx_maximo": round(mpx_maximo, 3),
         "paginas_hasta_ahora": paso, "salida": dst}
    celdas.append(c)
    print(json.dumps(c, ensure_ascii=False), flush=True)
    return c


# ------------------------------------------------------------------ las fases
paso = 0
if FASE == "frio":
    paso += 1
    celda(PEQ, paso, "unica pagina del proceso frio")

elif FASE in ("veneno", "control"):
    for _ in range(3):
        paso += 1
        celda(PEQ, paso, "A: antes")
    if FASE == "veneno":
        paso += 1
        celda(GRANDE, paso, "B: el folio grande")
    for i in range(5):
        paso += 1
        celda(PEQ, paso, "C: despues")
        if i < 4:
            # "Reiniciar el proceso lo arregla; esperar, no": aqui se ESPERA.
            time.sleep(ESPERA_S)
    paso += 1
    celda(ENORME, paso, "D: folio aun mayor")
    paso += 1
    celda(PEQ, paso, "E: tras el mayor")

elif FASE == "ascendente":
    for nombre in (MINI, PEQ, MED, GRANDE, ENORME):
        paso += 1
        celda(nombre, paso, "ascendente")
    for _ in range(2):
        paso += 1
        celda(MINI, paso, "vuelta a la mas pequena")

elif FASE == "directo":
    # El folio MAYOR sin pasar antes por los intermedios. Es la esquina que le
    # falta al factorial de "ascendente": sin ella no se puede atribuir si la
    # VRAM retenida la fija el maximo visto o TAMBIEN el camino recorrido.
    for _ in range(2):
        paso += 1
        celda(ENORME, paso, "directo al mayor")
    for _ in range(2):
        paso += 1
        celda(MINI, paso, "vuelta a la mas pequena")

elif FASE == "repetido":
    for _ in range(REPETICIONES):
        paso += 1
        celda(PEQ, paso, "misma pagina, tamano fijo")

else:
    raise SystemExit(f"fase desconocida: {FASE}")

fin = {"evento": "fin", "etiqueta": etiqueta,
       "vram_final_MiB": vram_usada(), "vram_libre_final_MiB": vram_libre(),
       "vram_base_MiB": base_vram,
       "pico_delta_MiB": max((c["vram_despues_MiB"] - base_vram) for c in celdas)
       if celdas else 0,
       "celdas_con_error": sum(1 for c in celdas if c["error"]),
       "testigo_mono_fin_ms": testigo_monohilo(),
       "testigo_proc_fin_ms": testigo_proceso()}
fin["deriva"] = round(fin["testigo_mono_fin_ms"] / max(mono_ini, 0.01), 2)
fin["nivel"] = round(fin["testigo_proc_fin_ms"] / max(proc_ini, 0.01), 2)
fin["tanda"] = "limpia" if (fin["deriva"] < 1.3 and fin["nivel"] < 1.3) else "SUCIA"
print(json.dumps(fin, ensure_ascii=False), flush=True)

json.dump({"meta": meta, "celdas": celdas, "fin": fin},
          open(os.path.join(OUTDIR, "json", f"{etiqueta}.json"), "w",
               encoding="utf-8"), ensure_ascii=False, indent=2)

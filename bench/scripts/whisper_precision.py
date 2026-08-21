# -*- coding: utf-8 -*-
"""FASE 2-E.1: large-v3 frente a distil-large-v3 sobre VOZ REAL, midiendo precision.

Fase 1 dejo abierta la pregunta: distil ahorra 2 678 MiB de VRAM, pero ¿a que coste
de calidad? Aqui se mide WER (tasa de error por palabras) y CER contra la referencia
conocida, sobre el audio limpio y sobre dos degradaciones realistas:
  * jfk_ruido    -> ruido blanco sumado (SNR bajo)
  * jfk_telefono -> banda 300-3400 Hz remuestreado a 8 kHz (calidad telefonica)

uso: whisper_precision.py <large-v3|distil-large-v3>
"""
import json
import os
import subprocess
import sys
import time

modelo = sys.argv[1] if len(sys.argv) > 1 else "large-v3"
OUT = r"D:\Work\research\FileX\bench\salidas-fase2"
C = r"D:\Work\research\FileX\corpus\audio"
A2 = os.path.join(OUT, "audio")
os.makedirs(OUT, exist_ok=True)

FRASE = ("And so my fellow Americans ask not what your country can do for you "
         "ask what you can do for your country")
REFS = {
    "jfk_limpio": FRASE,
    "jfk_ruido": FRASE,
    "jfk_telefono": FRASE,
    "largo_limpio": " ".join([FRASE] * 28),
    "largo_ruido": " ".join([FRASE] * 28),
}
TAREAS = [
    ("jfk_limpio", os.path.join(C, "habla_jfk.flac")),
    ("jfk_ruido", os.path.join(A2, "jfk_ruido.flac")),
    ("jfk_telefono", os.path.join(A2, "jfk_telefono.flac")),
    ("largo_limpio", os.path.join(C, "habla_largo.flac")),
    ("largo_ruido", os.path.join(A2, "largo_ruido.flac")),
]


def normaliza(s):
    import re
    import unicodedata
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def lev(a, b):
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def vram():
    try:
        return int(subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True).stdout.strip().splitlines()[0])
    except Exception:
        return -1


base = vram()
from faster_whisper import WhisperModel

t0 = time.time()
m = WhisperModel(modelo, device="cuda", compute_type="float16")
carga = time.time() - t0
tras_carga = vram()
print(json.dumps({"evento": "carga", "modelo": modelo, "segundos": round(carga, 2),
                  "vram_base": base, "vram_tras_carga": tras_carga}))
sys.stdout.flush()

pico = tras_carga
res = []
for nombre, ruta in TAREAS:
    if not os.path.exists(ruta):
        print(json.dumps({"evento": "falta", "archivo": ruta}))
        continue
    t0 = time.time()
    segs, info = m.transcribe(ruta, beam_size=5)
    texto = "".join(s.text for s in segs).strip()
    dt = time.time() - t0
    v = vram()
    pico = max(pico, v)
    dst = os.path.join(OUT, f"whisper2_{modelo}_{nombre}.txt")
    open(dst, "w", encoding="utf-8").write(texto)

    hip = normaliza(texto).split()
    ref = normaliza(REFS[nombre]).split()
    d_pal = lev(ref, hip)
    hc = normaliza(texto)
    rc = normaliza(REFS[nombre])
    d_car = lev(rc, hc)
    r = {"evento": "tarea", "modelo": modelo, "tarea": nombre,
         "audio_s": round(info.duration, 2), "segundos": round(dt, 2),
         "rtf": round(info.duration / dt, 1) if dt else None,
         "idioma": info.language, "prob_idioma": round(info.language_probability, 3),
         "palabras_ref": len(ref), "palabras_hip": len(hip),
         "WER_pct": round(100 * d_pal / len(ref), 2),
         "CER_pct": round(100 * d_car / len(rc), 2),
         "chars": len(texto), "salida": dst}
    res.append(r)
    print(json.dumps(r, ensure_ascii=False))
    sys.stdout.flush()

fin = {"evento": "fin", "modelo": modelo, "vram_base": base,
       "vram_tras_carga": tras_carga, "vram_pico": pico,
       "coste_carga_MiB": tras_carga - base, "coste_pico_MiB": pico - base}
print(json.dumps(fin))
json.dump({"carga_s": round(carga, 2), "tareas": res, "fin": fin},
          open(os.path.join(OUT, f"whisper2_{modelo}_resumen.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

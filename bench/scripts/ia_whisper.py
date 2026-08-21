# -*- coding: utf-8 -*-
"""FASE 1-B.1: faster-whisper large-v3 / distil-large-v3 en float16.
Mide: tiempo de carga del modelo, tiempo de transcripcion, y deja la salida
en disco para verificacion funcional. La VRAM la mide gpuwatch.py por fuera.
"""
import sys, time, json, os, gc

modelo = sys.argv[1] if len(sys.argv) > 1 else "large-v3"
modo   = sys.argv[2] if len(sys.argv) > 2 else "todo"   # todo | solo_carga | residente
OUT = r"D:\Work\research\FileX\bench\salidas-fase1\ia"
os.makedirs(OUT, exist_ok=True)

from faster_whisper import WhisperModel

t0 = time.time()
m = WhisperModel(modelo, device="cuda", compute_type="float16")
t_carga = time.time() - t0
print(json.dumps({"evento":"carga","modelo":modelo,"segundos":round(t_carga,2)}))
sys.stdout.flush()

if modo == "solo_carga":
    sys.exit(0)

if modo == "residente":
    # se queda con el modelo en VRAM para la prueba de coexistencia
    print("RESIDENTE_LISTO"); sys.stdout.flush()
    time.sleep(float(os.environ.get("RESIDENTE_SEG","60")))
    sys.exit(0)

C = r"D:\Work\research\FileX\corpus"
tareas = [
    ("habla_jfk",   os.path.join(C,"audio","habla_jfk.flac")),
    ("habla_largo", os.path.join(C,"audio","habla_largo.flac")),
    ("tipico_mp3",  os.path.join(C,"audio","tipico.mp3")),
    ("tipico_flac", os.path.join(C,"audio","tipico.flac")),
    ("trivial_wav", os.path.join(C,"audio","trivial.wav")),
    ("video_tipico_audio", os.path.join(OUT,"tipico_audio.flac")),
]
res = []
for nombre, ruta in tareas:
    if not os.path.exists(ruta):
        print(json.dumps({"evento":"falta","archivo":ruta})); continue
    t0 = time.time()
    segs, info = m.transcribe(ruta, beam_size=5)
    texto = "".join(s.text for s in segs)   # generador perezoso: aqui se ejecuta
    dt = time.time() - t0
    dst = os.path.join(OUT, f"whisper_{modelo}_{nombre}.txt")
    with open(dst, "w", encoding="utf-8") as f:
        f.write(texto.strip())
    r = {"evento":"transcripcion","modelo":modelo,"tarea":nombre,
         "audio_s":round(info.duration,2),"segundos":round(dt,2),
         "rtf": round(info.duration/dt,1) if dt else None,
         "idioma":info.language,"prob_idioma":round(info.language_probability,3),
         "chars":len(texto.strip()), "salida":dst}
    res.append(r); print(json.dumps(r, ensure_ascii=False)); sys.stdout.flush()

with open(os.path.join(OUT, f"whisper_{modelo}_resumen.json"), "w", encoding="utf-8") as f:
    json.dump({"carga_s":round(t_carga,2),"tareas":res}, f, ensure_ascii=False, indent=2)

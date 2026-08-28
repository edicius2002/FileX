# -*- coding: utf-8 -*-
"""Genera los planes de tanda. Se escribe con Python y no con un heredoc porque
los heredocs de esta shell se comen los backslashes (trampa 19).

  A — el factorial de la coresidencia con el perfil que §6.3 dice que CUMPLE:
      distil-large-v3 + RapidOCR/PP-OCRv6 small + NVENC. Cinco fases alternadas,
      10 repeticiones, la primera de cada fase se descarta (trampa 7).
  B — el perfil que §6.3 dice que NO cumple: large-v3 sobre el audio de 308 s,
      que es el que el hito 6 manda usar por encima de 30 s.
  C — controles: la duracion del audio como variable, y el folio pequeno.
"""
import json
import os

D = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
RAIZ = os.path.dirname(os.path.dirname(D))
PY = "D:/Work/research/FileX/.venv-ai/Scripts/python.exe"

FASES_A = ["base", "solo_nvenc", "solo_ocr", "solo_audio", "coresidente"]

# --- A: 10 repeticiones, fases ALTERNADAS -----------------------------------
# Alternar no es cosmetico: si una fase corre entera al principio y otra entera
# al final, la deriva de la maquina se carga sobre una sola fase y se publica
# como diferencia entre fases.
a = {"etiqueta": "S6-A-coresidencia", "python": PY, "corridas": []}
for i in range(10):
    for f in FASES_A:
        a["corridas"].append({
            "fase": f, "etiqueta": f"A_{f}_{i:02d}",
            "timeout": 900,
            "env": {"H6_WHISPER": "distil-large-v3",
                    "H6_AUDIO": f"{RAIZ}/corpus/audio/habla_jfk.flac",
                    "H6_IMG": f"{D}/img/escaneado_d4_r400.png",
                    "HF_HUB_OFFLINE": "1"}})
json.dump(a, open(os.path.join(D, "plan_a.json"), "w", encoding="utf-8"), indent=2)

# --- D: las dos vias que SI arrancan ----------------------------------------
# La tanda A demostro que `coresidente` (audio y luego OCR en el mismo proceso)
# muere en 10 de 10 con rc=0xC0000409. Estas son las dos alternativas.
d = {"etiqueta": "S6-D-vias", "python": PY, "corridas": []}
for i in range(10):
    for f in ("coresidente_inv", "dos_procesos"):
        d["corridas"].append({
            "fase": f, "etiqueta": f"D_{f}_{i:02d}", "timeout": 900,
            "env": {"H6_WHISPER": "distil-large-v3",
                    "H6_AUDIO": f"{RAIZ}/corpus/audio/habla_jfk.flac",
                    "H6_IMG": f"{D}/img/escaneado_d4_r400.png",
                    "HF_HUB_OFFLINE": "1"}})
json.dump(d, open(os.path.join(D, "plan_d.json"), "w", encoding="utf-8"), indent=2)

# --- B: el perfil `large-v3` con el audio de 308 s ---------------------------
b = {"etiqueta": "S6-B-largev3", "python": PY, "corridas": []}
for i in range(10):
    for f in ("solo_audio", "dos_procesos"):
        b["corridas"].append({
            "fase": f, "etiqueta": f"B_{f}_{i:02d}",
            "timeout": 1200,
            "env": {"H6_WHISPER": "large-v3",
                    "H6_AUDIO": f"{RAIZ}/corpus/audio/habla_largo.flac",
                    "H6_IMG": f"{D}/img/escaneado_d4_r400.png",
                    "HF_HUB_OFFLINE": "1"}})
json.dump(b, open(os.path.join(D, "plan_b.json"), "w", encoding="utf-8"), indent=2)

# --- C: controles -----------------------------------------------------------
c = {"etiqueta": "S6-C-controles", "python": PY, "corridas": []}
for i in range(3):
    # ¿mueve la VRAM la DURACION del audio? 11 s contra 308 s, mismo modelo.
    c["corridas"].append({
        "fase": "solo_audio", "etiqueta": f"C_audio_largo_distil_{i:02d}",
        "timeout": 1200,
        "env": {"H6_WHISPER": "distil-large-v3",
                "H6_AUDIO": f"{RAIZ}/corpus/audio/habla_largo.flac",
                "HF_HUB_OFFLINE": "1"}})
    # ¿y el TAMANO del folio? 2,22 Mpx (ppp nativos de d4) contra 8,88.
    c["corridas"].append({
        "fase": "solo_ocr", "etiqueta": f"C_ocr_2mpx_{i:02d}",
        "timeout": 900,
        "env": {"H6_IMG": f"{D}/img/escaneado_d4_r200.png", "HF_HUB_OFFLINE": "1"}})
    c["corridas"].append({
        "fase": "dos_procesos", "etiqueta": f"C_core_2mpx_{i:02d}",
        "timeout": 900,
        "env": {"H6_WHISPER": "distil-large-v3",
                "H6_AUDIO": f"{RAIZ}/corpus/audio/habla_jfk.flac",
                "H6_IMG": f"{D}/img/escaneado_d4_r200.png", "HF_HUB_OFFLINE": "1"}})
json.dump(c, open(os.path.join(D, "plan_c.json"), "w", encoding="utf-8"), indent=2)

print("plan_a", len(a["corridas"]), "· plan_b", len(b["corridas"]),
      "· plan_c", len(c["corridas"]), "· plan_d", len(d["corridas"]))

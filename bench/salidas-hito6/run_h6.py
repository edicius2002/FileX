# -*- coding: utf-8 -*-
"""S6 / hito 6 — lanzador de la tanda de coresidencia, **con el lock de GPU tomado
desde Python**.

`CLAUDE.md` §1 deja escrito que **0 de 15 arneses `.py` toman el lock** y que eso
sigue PENDIENTE. Aqui se toma, con `filex/gpu.py`, que implementa el protocolo de
`bench/lib/harness.sh` (`O_CREAT|O_EXCL` sobre `%TEMP%/filex-gpu.lock`) y por tanto
**excluye tambien a los 51 ficheros de `bench/` que usan el arnes**. No se usa
`filex/cerrojo.py`: su exclusion contra el shell es asimetrica (trampa 77).

Se toma UNA vez para la tanda entera y se sueltan las corridas por dentro: tomarlo
y soltarlo 45 veces deja 44 ventanas por las que se cuela otro.

uso: run_h6.py <fichero_de_plan.json>
"""
import json
import os
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)
from filex import gpu  # noqa: E402

PY_AI = os.environ.get("H6_PY", os.path.join(
    os.path.dirname(RAIZ.rstrip("\\/")), "..", ".venv-ai", "Scripts", "python.exe"))

plan = json.load(open(sys.argv[1], encoding="utf-8"))
py = plan.get("python", PY_AI)
guion = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coresidencia.py")
logs = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(logs, exist_ok=True)

resultados = []
with gpu.Lock(plan.get("etiqueta", "S6-hito6")) as l:
    if l.aviso:
        print(f"[aviso de la guardia] {l.aviso}", flush=True)
    print(f"[lock] tomado: {gpu.dueno()} · VRAM libre {gpu.vram_libre_mib()} MiB",
          flush=True)
    for corrida in plan["corridas"]:
        fase, etiq = corrida["fase"], corrida["etiqueta"]
        env = dict(os.environ)
        env.update({k: str(v) for k, v in corrida.get("env", {}).items()})
        # La guardia, ANTES de cada corrida: el lock no excluye a quien no lo toma.
        estado, motivo = gpu.ocupacion_ajena()
        if estado == 2:
            print(json.dumps({"etiqueta": etiq, "abortada": motivo}), flush=True)
            resultados.append({"etiqueta": etiq, "rc": None, "abortada": motivo})
            continue
        t = time.perf_counter()
        with open(os.path.join(logs, etiq + ".log"), "w", encoding="utf-8") as lg:
            r = subprocess.run([py, guion, fase, etiq], env=env,
                               stdin=subprocess.DEVNULL, stdout=lg,
                               stderr=subprocess.STDOUT,
                               timeout=corrida.get("timeout", 900))
        resultados.append({"etiqueta": etiq, "fase": fase, "rc": r.returncode,
                           "s": round(time.perf_counter() - t, 1),
                           "vram_libre_MiB": gpu.vram_libre_mib()})
        print(json.dumps(resultados[-1], ensure_ascii=False), flush=True)

print(json.dumps({"evento": "tanda_fin", "n": len(resultados),
                  "lock_libre": gpu.esta_libre(),
                  "vram_libre_MiB": gpu.vram_libre_mib()}, ensure_ascii=False))

"""Cabo 4 — repeticion del caso G3 de 2 videos, que dio resultados discordantes entre rondas."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import cabo4_deadlock as C  # noqa: E402

ent = str(C.RAIZ / "corpus/video/trivial.mp4").replace("\\", "/")
t = str(C.TRABAJO).replace("\\", "/")
res = []
for i in (1, 2, 3):
    r = C.caso(f"G3_concat2_rep{i}", "concatenate_videos",
               {"video_paths": [ent, ent], "output_video_path": f"{t}/g3rep{i}.mp4"},
               f"{t}/g3rep{i}.mp4")
    print(i, r["veredicto"], r.get("ms_llamada"), (r.get("respuesta") or "")[:200], flush=True)
    res.append(r)
Path(__file__).with_name("cabo4_g3_repeticiones.json").write_text(
    json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

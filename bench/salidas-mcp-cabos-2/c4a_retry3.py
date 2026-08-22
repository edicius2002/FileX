"""C4a retry — los 3 que fallaron temprano, ahora con un video CON pista de audio
(tipico.mp4) para que el grafo de ffmpeg llegue a la fase de escritura y se pueda
observar si tambien cuelgan con la salida preexistente."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import c4a_deadlock_resto as H  # reutiliza Sesion/caso/clasificar

RAIZ = H.RAIZ
t = str(H.TRABAJO).replace("\\", "/")
H.TRABAJO.mkdir(parents=True, exist_ok=True)
srt = H.TRABAJO / "sub.srt"
srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHola\n", encoding="utf-8")
srtp = str(srt).replace("\\", "/")
VIDA = H.VIDA
IMG = H.IMG

casos = [
    ("G1", "convert_video_format", {"input_video_path": VIDA, "output_video_path": f"{t}/r_cvf.mkv", "target_format": "mkv"}, "output_video_path"),
    ("G2", "add_image_overlay", {"video_path": VIDA, "output_video_path": f"{t}/r_img.mp4", "image_path": IMG}, "output_video_path"),
    ("G2", "add_subtitles", {"video_path": VIDA, "srt_file_path": srtp, "output_video_path": f"{t}/r_sub.mp4"}, "output_video_path"),
]

import json
res = []
for grupo, herr, args, sk in casos:
    etq = f"retry_{grupo}_{herr}"
    print(f"[c4a-retry] {etq} ...", flush=True)
    r = H.caso(etq, herr, args, sk)
    r["grupo"] = grupo
    print(f"   -> {r['veredicto']} ({r.get('ms_llamada')} ms) bytes_salida={r.get('bytes_salida')}", flush=True)
    res.append(r)

(H.SALIDA / "c4a_retry3.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

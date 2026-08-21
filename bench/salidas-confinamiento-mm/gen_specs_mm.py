"""Genera los spec.json de confinamiento contra los tres MCP de multimedia.

Se usa un script (no heredocs de shell) porque las rutas de Windows con
barra invertida se destrozan al escaparse en sh. json.dump escapa bien.

Convenciones de la raiz DECLARADA:
  - RAIZ = sandbox/raiz  -> el "arbol de trabajo" legitimo.
  - FUERA = sandbox/fuera -> hermana FUERA de la raiz, pero DENTRO de mi
    sandbox (asi puedo demostrar escritura fuera de la raiz sin tocar nada
    del usuario, cumpliendo la regla 4 del encargo).

  ffmpeg-mcp-lite: la unica "raiz" que entiende es FFMPEG_OUTPUT_DIR (solo
  restringe la salida por defecto). La ENTRADA no tiene raiz ninguna.
  video-audio-mcp e image-worker-mcp: NO tienen ningun concepto de raiz.

Uso: python gen_specs_mm.py
"""
import json
import os

BASE = "D:/Work/research/FileX/bench/salidas-confinamiento-mm"
SB = BASE + "/sandbox"
RAIZ = SB + "/raiz"
FUERA = SB + "/fuera"
RAIZ_W = RAIZ.replace("/", "\\")
FUERA_W = FUERA.replace("/", "\\")

REPO = "D:/Work/research/FileX/repos/mcp-refs"
PY_FF = "D:/Work/research/FileX/.venv-mm-ffmpeg/Scripts/python.exe"
PY_VA = "D:/Work/research/FileX/.venv-mm-vamcp/Scripts/python.exe"

SPECS = os.path.join(BASE.replace("/", os.sep), "specs")
os.makedirs(SPECS, exist_ok=True)


def paso(pid, tool, args, nota="", timeout=45, recorte=1400):
    return {"id": pid, "tool": tool, "args": args, "nota": nota,
            "timeout": timeout, "recorte": recorte}


# ==================================================================== A) ffmpeg-mcp-lite
# Lanzamiento: modulo -m ffmpeg_mcp_lite con PYTHONPATH al src.
# FFMPEG_OUTPUT_DIR = RAIZ  -> raiz declarada de salida.
spec_ff = {
    "nombre": "ffmpeg-mcp-lite",
    "command": PY_FF,
    "args": ["-m", "ffmpeg_mcp_lite"],
    "cwd": REPO + "/ffmpeg-mcp-lite",
    "env": {
        "PYTHONPATH": REPO + "/ffmpeg-mcp-lite/src",
        "FFMPEG_OUTPUT_DIR": RAIZ,
        "FFMPEG_PATH": "ffmpeg",
        "FFPROBE_PATH": "ffprobe",
    },
    "stderr_log": BASE + "/logs/ffmpeg.stderr.log",
    "pasos": [
        # --- LECTURA (entrada) via ffmpeg_get_info = ffprobe, solo-lectura, falla rapido ---
        paso("FF_control_info", "ffmpeg_get_info", {"file_path": RAIZ_W + "\\video.mp4"},
             "CONTROL: inspeccionar un fichero DENTRO de la raiz"),
        paso("FF_read_fuera_abs", "ffmpeg_get_info", {"file_path": FUERA_W + "\\video_fuera.mp4"},
             "LECTURA fuera de la raiz: ruta absoluta a la hermana prohibida"),
        paso("FF_read_travesia", "ffmpeg_get_info",
             {"file_path": RAIZ_W + "\\..\\fuera\\video_fuera.mp4"},
             "LECTURA por travesia: RAIZ\\..\\fuera\\..."),
        paso("FF_read_sys_exists", "ffmpeg_get_info", {"file_path": "C:\\Windows\\win.ini"},
             "LECTURA de fichero real del sistema (existe, no es media): distingue de no-existe"),
        paso("FF_read_sys_noexist", "ffmpeg_get_info", {"file_path": "C:\\Windows\\no_existe_jamas.ini"},
             "oraculo de existencia: fichero inexistente fuera de la raiz"),
        paso("FF_read_ads", "ffmpeg_get_info", {"file_path": RAIZ_W + "\\entrada.png:oculto"},
             "ADS: flujo alternativo dentro de la raiz"),
        # --- ESCRITURA (salida) ---
        paso("FF_write_convert_confina", "ffmpeg_convert",
             {"file_path": RAIZ_W + "\\video.mp4", "output_format": "mp3"},
             "convert NO tiene output_path: la salida se confina a FFMPEG_OUTPUT_DIR (RAIZ). "
             "Deberia caer en RAIZ pese a no poder elegirla.", 60),
        paso("FF_write_merge_fuera", "ffmpeg_merge",
             {"file_paths": [RAIZ_W + "\\video.mp4", RAIZ_W + "\\video2.mp4"],
              "output_path": FUERA_W + "\\merged_LEAK.mp4"},
             "FUGA declarada merge.py:38-39: output_path arbitrario FUERA de la raiz", 60),
        paso("FF_write_subs_fuera", "ffmpeg_add_subtitles",
             {"file_path": RAIZ_W + "\\video.mp4", "subtitle_path": RAIZ_W + "\\subs.srt",
              "output_path": FUERA_W + "\\subbed_LEAK.mp4"},
             "FUGA declarada subtitles.py:72-73: output_path arbitrario FUERA de la raiz", 90),
        paso("FF_write_merge_syswin", "ffmpeg_merge",
             {"file_paths": [RAIZ_W + "\\video.mp4", RAIZ_W + "\\video2.mp4"],
              "output_path": "C:\\Windows\\Temp\\filex_no_debe_existir_merge.mp4"},
             "escritura arbitraria a C:\\Windows\\Temp (deberia poder; NO se limpia por rule: "
             "es una carpeta temporal del sistema, se borra en el arnes)", 60),
    ],
}

# ==================================================================== B) video-audio-mcp
# Lanzamiento: python server.py (cwd=repo). SIN raiz de ningun tipo.
# CUIDADO: ffmpeg-python sin overwrite_output CUELGA si el destino EXISTE.
# Todos los output_path son FRESCOS y unicos; el arnes limpia FUERA/va_* antes.
spec_va = {
    "nombre": "video-audio-mcp",
    "command": PY_VA,
    "args": ["server.py"],
    "cwd": REPO + "/video-audio-mcp",
    "env": {},
    "stderr_log": BASE + "/logs/video-audio.stderr.log",
    "pasos": [
        paso("VA_health", "health_check", {}, "CONTROL: sin ruta", 20),
        # LECTURA fuera de la raiz con entrada NO-media -> ffmpeg falla rapido, sin colgar
        paso("VA_read_sys_exists", "extract_audio_from_video",
             {"video_path": "C:\\Windows\\win.ini",
              "output_audio_path": FUERA_W + "\\va_sys_out.mp3"},
             "LECTURA de win.ini (existe, no-media): ffmpeg lo abre y falla -> sin confinamiento", 30),
        paso("VA_read_noexist", "extract_audio_from_video",
             {"video_path": "C:\\no_existe_jamas_xyz.mp4",
              "output_audio_path": FUERA_W + "\\va_noexist_out.mp3"},
             "entrada inexistente: distingue no-existe de existe-pero-no-media", 30),
        paso("VA_read_travesia", "extract_audio_from_video",
             {"video_path": RAIZ_W + "\\..\\fuera\\video_fuera.mp4",
              "output_audio_path": FUERA_W + "\\va_trav_out.mp3"},
             "LECTURA por travesia RAIZ\\..\\fuera + ESCRITURA fuera (destino fresco)", 40),
        # ESCRITURA fuera de la raiz: entrada valida DENTRO de la raiz, salida FUERA (fresca)
        paso("VA_write_fuera", "extract_audio_from_video",
             {"video_path": RAIZ_W + "\\video.mp4",
              "output_audio_path": FUERA_W + "\\va_write_LEAK.mp3"},
             "ESCRITURA fuera de la raiz: mp3 en FUERA (destino fresco, no cuelga)", 40),
        paso("VA_ads", "extract_audio_from_video",
             {"video_path": RAIZ_W + "\\entrada.png:oculto",
              "output_audio_path": FUERA_W + "\\va_ads_out.mp3"},
             "ADS como entrada", 30),
    ],
}

# ==================================================================== C) image-worker-mcp
# Lanzamiento: npx -y @boomlinkai/image-worker-mcp con S3_BUCKET dummy (para
# que el constructor no muera). SIN raiz de ningun tipo.
spec_iw = {
    "nombre": "image-worker-mcp",
    "command": "npx.cmd",
    "args": ["-y", "@boomlinkai/image-worker-mcp"],
    "cwd": BASE,
    "env": {"S3_BUCKET": "dummy-no-se-usa", "UPLOAD_SERVICE": "s3"},
    "stderr_log": BASE + "/logs/image-worker.stderr.log",
    "pasos": [
        paso("IW_control", "resize_image",
             {"imagePath": RAIZ_W + "\\entrada.png", "width": 32,
              "outputPath": RAIZ_W + "\\iw_control_out.png"},
             "CONTROL: imagen dentro de la raiz -> salida dentro de la raiz", 40),
        paso("IW_read_write_fuera", "resize_image",
             {"imagePath": FUERA_W + "\\secreto.png", "width": 16,
              "outputPath": FUERA_W + "\\iw_read_LEAK.png"},
             "LECTURA imagen fuera de la raiz + ESCRITURA fuera de la raiz", 40),
        paso("IW_read_sys_exists", "resize_image",
             {"imagePath": "C:\\Windows\\win.ini", "width": 16},
             "LECTURA de win.ini: fs.readFileSync obtiene los bytes; sharp falla despues", 40),
        paso("IW_read_noexist", "resize_image",
             {"imagePath": "C:\\Windows\\no_existe_jamas.png", "width": 16},
             "oraculo: fichero inexistente -> ENOENT en el mensaje", 40),
        paso("IW_write_fuera", "resize_image",
             {"imagePath": RAIZ_W + "\\entrada.png", "width": 24,
              "outputPath": FUERA_W + "\\iw_write_LEAK.png"},
             "ESCRITURA fuera de la raiz: entrada en RAIZ, salida en FUERA", 40),
        paso("IW_travesia", "resize_image",
             {"imagePath": RAIZ_W + "\\..\\fuera\\secreto.png", "width": 16,
              "outputPath": FUERA_W + "\\iw_trav_LEAK.png"},
             "LECTURA+ESCRITURA por travesia RAIZ\\..\\fuera", 40),
        paso("IW_ads", "resize_image",
             {"imagePath": RAIZ_W + "\\entrada.png:oculto", "width": 16},
             "ADS como entrada: readFileSync del flujo alternativo", 40),
        paso("IW_write_systemp", "resize_image",
             {"imagePath": RAIZ_W + "\\entrada.png", "width": 16,
              "outputPath": "C:\\Windows\\Temp\\filex_no_debe_existir_iw.png"},
             "escritura arbitraria a C:\\Windows\\Temp (se borra en el arnes)", 40),
    ],
}

for nombre, spec in [("A_ffmpeg", spec_ff), ("B_video_audio", spec_va), ("C_image_worker", spec_iw)]:
    ruta = os.path.join(SPECS, nombre + ".json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)
    print("escrito", ruta, len(spec["pasos"]), "pasos")

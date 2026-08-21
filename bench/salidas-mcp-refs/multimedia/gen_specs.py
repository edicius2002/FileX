"""Genera los spec.json para sondear los tres MCP de multimedia.

Se genera con Python y no con heredocs de shell a proposito: las rutas de
Windows con '\' se rompen al escaparse. Aqui se usan barras normales, que
Windows acepta sin problema.

Uso:  python gen_specs.py <fase>
      fases: catalogo | conversion | errores | todas
"""

import json
import os
import sys

RAIZ = "D:/Work/research/FileX"
OUT = RAIZ + "/bench/salidas-mcp-refs/multimedia"
CORPUS = RAIZ + "/corpus"

# --- Como se lanza cada servidor -------------------------------------------

VAM = {
    "command": RAIZ + "/.venv-mcp-vam/Scripts/python.exe",
    "args": [RAIZ + "/repos/mcp-refs/video-audio-mcp/server.py"],
    "cwd": RAIZ,
    "env": {},
}

LITE = {
    "command": RAIZ + "/.venv-mcp-lite/Scripts/python.exe",
    "args": ["-m", "ffmpeg_mcp_lite"],
    "cwd": RAIZ,
    # lite IGNORA la ruta de salida que le pidas: escribe siempre en su
    # output_dir. Se le apunta a nuestro directorio de salidas.
    "env": {"FFMPEG_OUTPUT_DIR": OUT + "/salidas_lite"},
}

IMG = {
    "command": "C:/Program Files/nodejs/npx.cmd",
    "args": ["-y", "@boomlinkai/image-worker-mcp"],
    "cwd": RAIZ,
    # FALLO DE INTEGRACION DOCUMENTADO: el servidor construye
    # UploadServiceFactory.create() en el constructor, sin condicion, asi que
    # se NIEGA A ARRANCAR sin configuracion de S3 aunque solo quieras
    # resize_image, que es 100 % local y offline. Se le dan credenciales
    # falsas: no se hace ninguna llamada de red al construir el cliente S3.
    "env": {
        "UPLOAD_SERVICE": "s3",
        "S3_BUCKET": "filex-dummy-no-existe",
        "AWS_ACCESS_KEY_ID": "AKIADUMMYNOEXISTE000",
        "AWS_SECRET_ACCESS_KEY": "dummy-no-existe-secret-key-000000000000",
        "S3_REGION": "us-east-1",
    },
}

SERVIDORES = {"vam": VAM, "lite": LITE, "img": IMG}


def spec(nombre, base, pasos, sufijo):
    d = dict(base)
    d["nombre"] = nombre
    d["pasos"] = pasos
    d["stderr_log"] = "{}/{}.stderr.log".format(OUT, sufijo)
    ruta = "{}/{}.spec.json".format(OUT, sufijo)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print("escrito", ruta)


def o(nombre):
    """Ruta de salida dentro de nuestro directorio de resultados."""
    return OUT + "/salidas/" + nombre


# --- FASE 1: catalogo (sin convertir nada) ---------------------------------

def fase_catalogo():
    spec("video-audio-mcp CATALOGO", VAM, [], "cat_vam")
    spec("ffmpeg-mcp-lite CATALOGO", LITE, [], "cat_lite")
    spec("image-worker-mcp CATALOGO", IMG, [], "cat_img")


# --- FASE 2: la pregunta central -------------------------------------------

def fase_conversion():
    # video-audio-mcp: rutas de salida explicitas
    spec("video-audio-mcp CONVERSION", VAM, [
        {"id": "salud", "tool": "health_check", "args": {},
         "timeout": 60, "nota": "baseline"},
        {"id": "trivial_mp4_a_mp3", "tool": "extract_audio_from_video",
         "args": {"video_path": CORPUS + "/video/trivial.mp4",
                  "output_audio_path": o("vam_trivial.mp3"),
                  "audio_codec": "mp3"},
         "espera": "asa", "timeout": 300},
        {"id": "trivial_mp4_a_gif", "tool": "convert_video_format",
         "args": {"input_video_path": CORPUS + "/video/trivial.mp4",
                  "output_video_path": o("vam_trivial.gif"),
                  "target_format": "gif"},
         "espera": "asa", "timeout": 300},
        {"id": "trivial_mp4_a_webm", "tool": "convert_video_format",
         "args": {"input_video_path": CORPUS + "/video/trivial.mp4",
                  "output_video_path": o("vam_trivial.webm"),
                  "target_format": "webm"},
         "espera": "asa", "timeout": 600},
        {"id": "tipico_mp4_a_mp3", "tool": "extract_audio_from_video",
         "args": {"video_path": CORPUS + "/video/tipico.mp4",
                  "output_audio_path": o("vam_tipico.mp3"),
                  "audio_codec": "mp3"},
         "espera": "asa", "timeout": 600,
         "nota": "15,5 MB: cambia el patron con el tamano?"},
        {"id": "trivial_wav_a_flac", "tool": "convert_audio_format",
         "args": {"input_audio_path": CORPUS + "/audio/trivial.wav",
                  "output_audio_path": o("vam_trivial.flac"),
                  "target_format": "flac"},
         "espera": "asa", "timeout": 300},
        {"id": "trivial_wav_a_mp3", "tool": "convert_audio_format",
         "args": {"input_audio_path": CORPUS + "/audio/trivial.wav",
                  "output_audio_path": o("vam_trivial_wav.mp3"),
                  "target_format": "mp3"},
         "espera": "asa", "timeout": 300},
    ], "conv_vam")

    # ffmpeg-mcp-lite: NO acepta ruta de salida, la decide el servidor
    spec("ffmpeg-mcp-lite CONVERSION", LITE, [
        {"id": "info_trivial", "tool": "ffmpeg_get_info",
         "args": {"file_path": CORPUS + "/video/trivial.mp4"},
         "timeout": 120, "nota": "baseline: cuanto texto suelta un info"},
        {"id": "trivial_mp4_a_mp3", "tool": "ffmpeg_convert",
         "args": {"file_path": CORPUS + "/video/trivial.mp4",
                  "output_format": "mp3"},
         "espera": "asa", "timeout": 300},
        {"id": "trivial_mp4_a_gif", "tool": "ffmpeg_convert",
         "args": {"file_path": CORPUS + "/video/trivial.mp4",
                  "output_format": "gif"},
         "espera": "asa", "timeout": 600},
        {"id": "trivial_mp4_a_webm", "tool": "ffmpeg_convert",
         "args": {"file_path": CORPUS + "/video/trivial.mp4",
                  "output_format": "webm"},
         "espera": "asa", "timeout": 900},
        {"id": "tipico_mp4_a_mp3", "tool": "ffmpeg_convert",
         "args": {"file_path": CORPUS + "/video/tipico.mp4",
                  "output_format": "mp3"},
         "espera": "asa", "timeout": 600},
        {"id": "trivial_wav_a_flac", "tool": "ffmpeg_convert",
         "args": {"file_path": CORPUS + "/audio/trivial.wav",
                  "output_format": "flac"},
         "espera": "asa", "timeout": 300},
        {"id": "extraer_audio", "tool": "ffmpeg_extract_audio",
         "args": {"file_path": CORPUS + "/video/trivial.mp4",
                  "audio_format": "mp3"},
         "espera": "asa", "timeout": 300},
    ], "conv_lite")

    # image-worker-mcp: EL CASO DECISIVO.
    # outputImage=false (por defecto) vs outputImage=true, mismo fichero.
    spec("image-worker-mcp CONVERSION", IMG, [
        # --- por defecto: outputImage no se pasa (default false) ---
        {"id": "jpg_a_png_defecto", "tool": "resize_image",
         "args": {"imagePath": CORPUS + "/imagen/tipico.jpg",
                  "format": "png", "outputPath": o("img_tipico.png")},
         "espera": "asa", "timeout": 180},
        {"id": "jpg_a_webp_defecto", "tool": "resize_image",
         "args": {"imagePath": CORPUS + "/imagen/tipico.jpg",
                  "format": "webp", "outputPath": o("img_tipico.webp")},
         "espera": "asa", "timeout": 180},
        {"id": "trivial_png_a_webp_defecto", "tool": "resize_image",
         "args": {"imagePath": CORPUS + "/imagen/trivial.png",
                  "format": "webp", "outputPath": o("img_trivial.webp")},
         "espera": "asa", "timeout": 180,
         "nota": "316 bytes de entrada: devuelve el binario si es diminuto?"},
        # --- outputImage=true: se pide explicitamente el binario ---
        {"id": "trivial_png_a_webp_CONTENIDO", "tool": "resize_image",
         "args": {"imagePath": CORPUS + "/imagen/trivial.png",
                  "format": "webp", "outputImage": True,
                  "outputPath": o("img_trivial_c.webp")},
         "espera": "contenido", "timeout": 180,
         "nota": "EL CASO DECISIVO minimo"},
        {"id": "jpg_a_png_CONTENIDO", "tool": "resize_image",
         "args": {"imagePath": CORPUS + "/imagen/tipico.jpg",
                  "format": "png", "outputImage": True,
                  "outputPath": o("img_tipico_c.png")},
         "espera": "contenido", "timeout": 180,
         "nota": "EL CASO DECISIVO: imagen tipica de 88 KB"},
        {"id": "jpg_a_webp_CONTENIDO", "tool": "resize_image",
         "args": {"imagePath": CORPUS + "/imagen/tipico.jpg",
                  "format": "webp", "outputImage": True,
                  "outputPath": o("img_tipico_c.webp")},
         "espera": "contenido", "timeout": 180},
        # --- sin outputPath: solo base64, sin fichero ---
        {"id": "sin_outputPath", "tool": "resize_image",
         "args": {"imagePath": CORPUS + "/imagen/trivial.png",
                  "format": "webp", "outputImage": True},
         "espera": "contenido", "timeout": 180,
         "nota": "sin ruta de salida: el binario es la UNICA salida"},
    ], "conv_img")


# --- FASE 4: errores --------------------------------------------------------

def fase_errores():
    NOEXISTE = CORPUS + "/video/NO_EXISTE_12345.mp4"
    TRUNCADO = OUT + "/corrupto/truncado.mp4"
    TRUNC_PNG = OUT + "/corrupto/truncado.png"

    spec("video-audio-mcp ERRORES", VAM, [
        {"id": "inexistente", "tool": "convert_video_format",
         "args": {"input_video_path": NOEXISTE,
                  "output_video_path": o("err_vam_1.mkv"),
                  "target_format": "mkv"}, "timeout": 120},
        {"id": "formato_imposible", "tool": "convert_video_format",
         "args": {"input_video_path": CORPUS + "/video/trivial.mp4",
                  "output_video_path": o("err_vam_2.xyzzy"),
                  "target_format": "xyzzy"}, "timeout": 180},
        {"id": "corrupto", "tool": "convert_video_format",
         "args": {"input_video_path": TRUNCADO,
                  "output_video_path": o("err_vam_3.mkv"),
                  "target_format": "mkv"}, "timeout": 180},
    ], "err_vam")

    spec("ffmpeg-mcp-lite ERRORES", LITE, [
        {"id": "inexistente", "tool": "ffmpeg_convert",
         "args": {"file_path": NOEXISTE, "output_format": "mkv"},
         "timeout": 120},
        {"id": "formato_imposible", "tool": "ffmpeg_convert",
         "args": {"file_path": CORPUS + "/video/trivial.mp4",
                  "output_format": "xyzzy"}, "timeout": 180},
        {"id": "corrupto", "tool": "ffmpeg_convert",
         "args": {"file_path": TRUNCADO, "output_format": "mkv"},
         "timeout": 180},
    ], "err_lite")

    spec("image-worker-mcp ERRORES", IMG, [
        {"id": "inexistente", "tool": "resize_image",
         "args": {"imagePath": CORPUS + "/imagen/NO_EXISTE_12345.jpg",
                  "format": "png", "outputPath": o("err_img_1.png")},
         "timeout": 120},
        {"id": "formato_imposible", "tool": "resize_image",
         "args": {"imagePath": CORPUS + "/imagen/tipico.jpg",
                  "format": "xyzzy", "outputPath": o("err_img_2.xyzzy")},
         "timeout": 120},
        {"id": "corrupto", "tool": "resize_image",
         "args": {"imagePath": TRUNC_PNG, "format": "png",
                  "outputPath": o("err_img_3.png")},
         "timeout": 120},
    ], "err_img")


if __name__ == "__main__":
    os.makedirs(OUT + "/salidas", exist_ok=True)
    os.makedirs(OUT + "/salidas_lite", exist_ok=True)
    os.makedirs(OUT + "/corrupto", exist_ok=True)
    fase = sys.argv[1] if len(sys.argv) > 1 else "todas"
    if fase in ("catalogo", "todas"):
        fase_catalogo()
    if fase in ("conversion", "todas"):
        fase_conversion()
    if fase in ("errores", "todas"):
        fase_errores()

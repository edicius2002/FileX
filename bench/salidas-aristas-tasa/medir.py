#!/usr/bin/env python3
"""Tanda B: tasas de audio y sondas acotadas de C25 (ejecutar desde Git Bash)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.dirname(os.path.abspath(__file__))
FF = shutil.which("ffmpeg") or "ffmpeg"
FP = shutil.which("ffprobe") or "ffprobe"
MAGICK = shutil.which("magick") or "magick"
TOPE = 20


def run(argv, cwd):
    t0 = time.perf_counter()
    try:
        p = subprocess.run(argv, cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True,
                           timeout=TOPE)
        return {"rc": p.returncode, "ms": round((time.perf_counter()-t0)*1000, 1),
                "err": p.stderr.decode("utf-8", "replace")[-700:]}
    except subprocess.TimeoutExpired as e:
        return {"rc": None, "timeout_s": TOPE, "ms": round((time.perf_counter()-t0)*1000, 1),
                "err": (e.stderr or b"").decode("utf-8", "replace")[-700:]}


def audio_real(path):
    p = subprocess.run([FP, "-v", "error", "-show_entries",
                        "format=duration:stream=index,codec_type:packet=stream_index,size",
                        "-of", "json", path], stdin=subprocess.DEVNULL, capture_output=True,
                       text=True, timeout=TOPE)
    try:
        d = json.loads(p.stdout); dur = float(d["format"]["duration"])
        audio = {x["index"] for x in d["streams"] if x.get("codec_type") == "audio"}
        total = {i: 0 for i in audio}
        for x in d.get("packets", []):
            if x.get("stream_index") in total: total[x["stream_index"]] += int(x["size"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    return [round(total[i] * 8 / dur) for i in sorted(total)] if dur else None


def audio(tmp):
    filas=[]
    fuentes=[("wav_mono", "corpus/audio/trivial.wav"), ("flac", "corpus/audio/tipico.flac"),
             ("mkv_dos_pistas", "corpus/video/patologico_2pistas.mkv")]
    codecs=[("aac", "m4a"), ("libopus", "opus"), ("libmp3lame", "mp3")]
    for fuente, rel in fuentes:
        src=os.path.join(ROOT, rel)
        for codec, ext in codecs:
            for tasa in (8_000, 32_000, 96_000, 128_000, 192_000):
                dst=os.path.join(tmp, f"a_{fuente}_{codec}_{tasa}.{ext}")
                cmd=[FF,"-hide_banner","-nostdin","-y","-loglevel","error","-i",src,
                     "-map","0:a?","-t","8","-c:a",codec,"-b:a",str(tasa),dst]
                r=run(cmd,tmp); fila={"fuente":fuente,"codec":codec,"pedido_bps":tasa,
                                      "orden":cmd,**r,"bytes":os.path.getsize(dst) if os.path.exists(dst) else 0}
                if not (r["rc"]==0 and fila["bytes"]):
                    r2=run(cmd,tmp); fila["intento2"]={**r2,"bytes":os.path.getsize(dst) if os.path.exists(dst) else 0}
                else:
                    real=audio_real(dst); fila["obtenido_bps_por_pista"]=real
                    fila["desvio_por_pista"]=([(x-tasa)/tasa for x in real]
                                               if real else None)
                filas.append(fila)
    return filas


def c25(tmp):
    srcv=os.path.join(ROOT,"corpus/video/trivial.mp4")
    srcva=os.path.join(ROOT,"corpus/video/tipico.mp4")
    srca=os.path.join(ROOT,"corpus/audio/trivial.wav")
    casos=[("amv",srcv,["-map","0:v:0","-map","0:a?","-t","2","-f","amv"]),
           ("amv_perfil",srcva,["-map","0:v:0","-map","0:a:0","-t","2",
                                "-vf","scale=160:120","-r","15","-ac","1","-ar","22050",
                                "-c:v","amv","-c:a","adpcm_ima_amv","-f","amv"]),
           ("gxf",srcv,["-map","0:v:0","-map","0:a?","-t","2","-c:v","mpeg2video","-c:a","pcm_s16le","-f","gxf"]),
           ("mlp",srca,["-map","0:a:0","-t","2","-c:a","mlp","-f","mlp"]),
           ("thd",srca,["-map","0:a:0","-t","2","-c:a","truehd","-f","truehd"]),
           # Los rc anteriores nombran EXPERIMENTAL; es un remedio acotado,
           # no otro barrido de parámetros (trampa 72).
           ("mlp_strict",srca,["-strict","-2","-map","0:a:0","-t","2","-c:a","mlp","-f","mlp"]),
           ("thd_strict",srca,["-strict","-2","-map","0:a:0","-t","2","-c:a","truehd","-f","truehd"])]
    filas=[]
    for nombre, src, args in casos:
        # La variante de prueba no es parte de la extensión: ImageMagick/ffmpeg
        # vuelven a inferirla en algunas rutas antes de llegar al ``-f``.
        dst=os.path.join(tmp,"c25_"+nombre+"."+nombre.split("_",1)[0])
        cmd=[FF,"-hide_banner","-nostdin","-y","-loglevel","error","-i",src,*args,dst]
        r=run(cmd,tmp); fila={"formato":nombre,"orden":cmd,**r,"bytes":os.path.getsize(dst) if os.path.exists(dst) else 0}
        if not (r["rc"]==0 and fila["bytes"]):
            r2=run(cmd,tmp); fila["intento2"]={**r2,"bytes":os.path.getsize(dst) if os.path.exists(dst) else 0}
        filas.append(fila)
    return filas


def pendientes_p2():
    ruta=os.path.join(ROOT,"bench/salidas-invocacion/resid_p2b.json")
    with open(ruta,encoding="utf8") as f: datos=json.load(f)
    return [{k:x.get(k) for k in ("a","b","rc","bytes","p2_causa","p2_reglas")}
            for x in datos if "received no packets" in (x.get("err") or "").lower()]


def crudos(tmp):
    """C25: un RGB 8-bit de tercero y los dos Bayer sin fingir referencia."""
    src=os.path.join(ROOT,"corpus/imagen/tipico.png"); base=os.path.join(tmp,"base.png")
    filas=[]
    r=run([MAGICK,src,"-resize","64x48!",base],tmp)
    raw=os.path.join(tmp,"tercero.rgb")
    filas.append({"caso":"generar_rgb_8bit",**run([MAGICK,base,"-depth","8","RGB:"+raw],tmp),
                  "bytes":os.path.getsize(raw) if os.path.exists(raw) else 0})
    for depth in (8,16):
        out=os.path.join(tmp,f"rgb_leido_{depth}.png")
        z=run([MAGICK,"-size","64x48","-depth",str(depth),"RGB:"+raw,out],tmp)
        fila={"caso":"rgb_tercero","depth":depth,**z,"bytes":os.path.getsize(out) if os.path.exists(out) else 0}
        if z["rc"]==0 and fila["bytes"]:
            q=run([MAGICK,"compare","-metric","RMSE",base,out,"null:"],tmp); fila["rmse_stderr"]=q["err"]
        filas.append(fila)
    for fmt in ("BAYER","BAYERA"):
        rawb=os.path.join(tmp,fmt.lower()+".raw"); out=os.path.join(tmp,fmt.lower()+".png")
        w=run([MAGICK,base,"-depth","8",fmt+":"+rawb],tmp)
        z=run([MAGICK,"-size","64x48","-depth","8",fmt+":"+rawb,out],tmp)
        filas.append({"caso":fmt.lower(),"escritura":w,"lectura":z,
                      "bytes_raw":os.path.getsize(rawb) if os.path.exists(rawb) else 0,
                      "bytes_png":os.path.getsize(out) if os.path.exists(out) else 0,
                      "referencia":"PENDIENTE: un mosaico CFA no tiene RMSE directo contra RGB"})
    return filas


def main():
    with tempfile.TemporaryDirectory(prefix="filex_tanda_b_") as tmp:
        antes=sorted(os.listdir(tmp)); a=audio(tmp); c=c25(tmp); raw=crudos(tmp); despues=sorted(os.listdir(tmp))
    res={"entorno":{"ffmpeg":subprocess.run([FF,"-version"],capture_output=True,text=True).stdout.splitlines()[0],
                     "ruta_resuelta":FF,"tope_s":TOPE},"antes":antes,"despues":despues,
         "audio":a,"c25_salida":c,"crudos":raw,"received_no_packets_p2":pendientes_p2()}
    with open(os.path.join(OUT,"resultado.json"),"w",encoding="utf8") as f: json.dump(res,f,ensure_ascii=False,indent=2)

if __name__ == "__main__": main()

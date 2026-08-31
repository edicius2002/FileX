#!/usr/bin/env python3
"""N28: cotas por (codec, build) sobre la ruta de vídeo de FFmpeg."""
from __future__ import annotations
import json, os, shutil, subprocess, tempfile, time

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),"..","..")); OUT=os.path.dirname(os.path.abspath(__file__))
FF=shutil.which("ffmpeg") or "ffmpeg"; FP=shutil.which("ffprobe") or "ffprobe"; TOPE=20

def run(a,cwd):
    t=time.perf_counter()
    try:
        p=subprocess.run(a,cwd=cwd,stdin=subprocess.DEVNULL,capture_output=True,timeout=TOPE)
        return {"rc":p.returncode,"ms":round((time.perf_counter()-t)*1000,1),"err":p.stderr.decode("utf8","replace")[-500:]}
    except subprocess.TimeoutExpired as e:
        return {"rc":None,"timeout_s":TOPE,"ms":round((time.perf_counter()-t)*1000,1),"err":(e.stderr or b"").decode("utf8","replace")[-500:]}

def rates(path):
    p=subprocess.run([FP,"-v","error","-show_entries","format=duration:stream=index,codec_type:packet=stream_index,size","-of","json",path],stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=TOPE)
    try:
        d=json.loads(p.stdout); dur=float(d["format"]["duration"]); ids={s["index"] for s in d["streams"] if s.get("codec_type")=="audio"}; sums={i:0 for i in ids}
        for z in d.get("packets",[]):
            if z.get("stream_index") in sums:sums[z["stream_index"]]+=int(z["size"])
        return [round(sums[i]*8/dur) for i in sorted(sums)]
    except (KeyError,ValueError,TypeError,json.JSONDecodeError): return []

def matriz(tmp):
    filas=[]
    audios=[("mono441",["-f","lavfi","-i","sine=frequency=440:sample_rate=44100"]),
            ("stereo48",["-f","lavfi","-i","aevalsrc=0.1*sin(2*PI*440*t)|0.1*sin(2*PI*880*t):s=48000:c=stereo"]),
            ("surround51",["-f","lavfi","-i","aevalsrc=0.1*sin(2*PI*440*t)|0.1*sin(2*PI*550*t)|0.1*sin(2*PI*660*t)|0.1*sin(2*PI*770*t)|0.1*sin(2*PI*880*t)|0.1*sin(2*PI*990*t):s=48000:c=5.1"])]
    for codec,ext in (("aac","mkv"),("libopus","webm")):
      for tasa in (64000,96000,128000,256000):
       for nombre,args in audios:
        for dur in (2,8):
         for n in (1,2):
          dst=os.path.join(tmp,f"{codec}_{tasa}_{nombre}_{dur}_{n}.{ext}")
          cmd=[FF,"-hide_banner","-nostdin","-y","-loglevel","error","-f","lavfi","-i","testsrc2=size=320x240:rate=25",*args,"-t",str(dur),"-map","0:v:0"]
          # Duplicar deliberadamente la primera pista cambia n_pistas.
          ai=1
          for j in range(n): cmd += ["-map",f"{ai}:a:0"]
          cmd += ["-c:v","libx264","-crf","30","-c:a",codec,"-b:a",str(tasa),dst]
          r=run(cmd,tmp); f={"codec":codec,"pedido":tasa,"entrada":nombre,"duracion":dur,"n_audio":n,"orden":cmd,**r,"bytes":os.path.getsize(dst) if os.path.exists(dst) else 0}
          if r["rc"]==0 and f["bytes"]:
            f["obtenido_por_pista"]=rates(dst); f["factor_max"]=max(f["obtenido_por_pista"])/tasa if f["obtenido_por_pista"] else None
          else: f["intento2"]=run(cmd,tmp)
          filas.append(f)
    return filas

def tabla(filas):
    out={}
    for codec in ("aac","libopus"):
      rs=[x["factor_max"] for x in filas if x["codec"]==codec and x.get("factor_max")]
      candidatos=[1,1.05,1.10,1.15,1.20,1.25,1.30,1.35,1.40]
      out[codec]={"n":len(rs),"max_factor":max(rs),"min_factor":min(rs),"candidatos":[{"factor":q,"cubre":sum(x<=q for x in rs),"total":len(rs)} for q in candidatos]}
    return out

def regresion72(tab):
    with open(os.path.join(ROOT,"bench/salidas-bitrate/calibracion.json"),encoding="utf8") as h:d=json.load(h)["filas"]
    legit=[x for x in d if x.get("clase")=="legitima" and x.get("ok") and x.get("bitrate_contenedor") and x.get("pedido_bps")]
    # Estas 72 son AAC a 128 k/s en la ruta de vídeo original; se simula V10 alto.
    out={}
    for codec in ("aac","libopus"):
      q=tab[codec]["max_factor"]; fall=[]
      for x in legit:
       n=x.get("n_audio",0); est=x["bitrate_contenedor"]-n*128000*q
       if est > x["pedido_bps"]*1.60: fall.append(x.get("fuente","?"))
      out[codec]={"factor":q,"legitimas":len(legit),"v10_fallos":len(fall)}
    return out

def patologicas(tmp,tab):
    srcs=[("tipico",os.path.join(ROOT,"corpus/video/tipico.mp4")),("dos",os.path.join(ROOT,"corpus/video/patologico_2pistas.mkv"))]; casos=[("crf10",["-c:v","libx264","-crf","10"],300000),("x10",["-c:v","libx264","-b:v","20000000"],2000000)]
    filas=[]; q=tab["aac"]["max_factor"]
    for n,src in srcs:
     for tag,v,pedido in casos:
      dst=os.path.join(tmp,f"p_{n}_{tag}.mkv"); cmd=[FF,"-hide_banner","-nostdin","-y","-loglevel","error","-i",src,"-map","0","-t","8",*v,"-c:a","aac","-b:a","128k",dst]; r=run(cmd,tmp); f={"caso":n+"_"+tag,"pedido":pedido,"orden":cmd,**r,"bytes":os.path.getsize(dst) if os.path.exists(dst) else 0}
      if r["rc"]==0 and f["bytes"]:
       rr=rates(dst); p=subprocess.run([FP,"-v","error","-show_entries","format=bit_rate","-of","default=nw=1:nk=1",dst],capture_output=True,text=True); cont=int(float(p.stdout.strip())); est=cont-len(rr)*128000*q; f.update({"n_audio":len(rr),"contenedor":cont,"estimado_cota":est,"fallo_v10":est>pedido*1.60})
      filas.append(f)
    return filas

def main():
 with tempfile.TemporaryDirectory(prefix="filex_cota_") as tmp:
  antes=sorted(os.listdir(tmp)); m=matriz(tmp)
  with open(os.path.join(OUT,"matriz_parcial.json"),"w",encoding="utf8") as h:json.dump(m,h,ensure_ascii=False,indent=2)
  t=tabla(m); p=patologicas(tmp,t); despues=sorted(os.listdir(tmp))
 r={"ffmpeg":subprocess.run([FF,"-version"],capture_output=True,text=True).stdout.splitlines()[0],"ruta":FF,"tope_s":TOPE,"antes":antes,"despues":despues,"matriz":m,"tabla":t,"regresion72":regresion72(t),"patologicas":p,"patron53":{"v10_con_bitrate_video_pedido":0,"motivo":"el patrón oro no trae bitrate_video_bps"}}
 with open(os.path.join(OUT,"resultado.json"),"w",encoding="utf8") as h:json.dump(r,h,ensure_ascii=False,indent=2)
if __name__=="__main__":main()

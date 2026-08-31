#!/usr/bin/env python3
"""N28: compara las vías de ffprobe para tasa de audio por pista."""
from __future__ import annotations
import json, os, shutil, subprocess, tempfile, time

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),"..","..")); OUT=os.path.dirname(os.path.abspath(__file__))
FF=shutil.which("ffmpeg") or "ffmpeg"; FP=shutil.which("ffprobe") or "ffprobe"; TOPE=20
def run(a,cwd):
 t=time.perf_counter()
 try:
  p=subprocess.run(a,cwd=cwd,stdin=subprocess.DEVNULL,capture_output=True,timeout=TOPE,text=True)
  return p.returncode,p.stdout,p.stderr,round((time.perf_counter()-t)*1000,1)
 except subprocess.TimeoutExpired as e:return None,"",e.stderr or "",round((time.perf_counter()-t)*1000,1)
def probe(path):
 r={}
 for n,args in {
  "streams":["-show_entries","stream=index,codec_type,bit_rate","-of","json"],
  "count_packets":["-count_packets","-show_entries","stream=index,codec_type,bit_rate,nb_read_packets","-of","json"],
  "packets":["-show_packets","-show_entries","packet=stream_index,size","-of","json"],
 }.items():
  rc,o,e,ms=run([FP,"-v","error",*args,path],os.path.dirname(path)); r[n]={"rc":rc,"ms":ms,"err":e[-400:]}
  try:r[n]["json"]=json.loads(o)
  except json.JSONDecodeError:r[n]["json"]={}
 # Suma exactamente los paquetes por stream; duración de format da b/s obtenido.
 rc,o,e,ms=run([FP,"-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",path],os.path.dirname(path));
 try:dur=float(o.strip())
 except ValueError:dur=0
 sums={}
 for p in r["packets"]["json"].get("packets",[]):sums[p.get("stream_index")]=sums.get(p.get("stream_index"),0)+int(p.get("size",0))
 r["suma_pkt_size_bps"]={str(k):round(v*8/dur) for k,v in sums.items()} if dur else {}
 return r
def main():
 with tempfile.TemporaryDirectory(prefix="filex_n28_pista_") as d:
  antes=sorted(os.listdir(d)); filas=[]
  for ext,codec in (("mp4","aac"),("mkv","aac"),("webm","libopus"),("mov","aac")):
   dst=os.path.join(d,"p."+ext); vcodec="libvpx-vp9" if ext=="webm" else "libx264"; cmd=[FF,"-hide_banner","-nostdin","-y","-loglevel","error","-f","lavfi","-i","testsrc2=size=320x240:rate=25","-f","lavfi","-i","sine=frequency=440:sample_rate=48000","-t","2","-map","0:v:0","-map","1:a:0","-c:v",vcodec,"-crf","30","-c:a",codec,"-b:a","96k",dst]
   rc,o,e,ms=run(cmd,d); f={"contenedor":ext,"codec_audio":codec,"orden":cmd,"rc":rc,"bytes":os.path.getsize(dst) if os.path.exists(dst) else 0,"err":e[-400:],"ms":ms}
   if rc==0 and f["bytes"]:f["vias"]=probe(dst)
   filas.append(f)
  despues=sorted(os.listdir(d))
 out={"ffmpeg":run([FF,"-version"],ROOT)[1].splitlines()[0],"ruta":FF,"tope_s":TOPE,"antes":antes,"despues":despues,"filas":filas}
 with open(os.path.join(OUT,"resultado.json"),"w",encoding="utf8") as h:json.dump(out,h,ensure_ascii=False,indent=2)
if __name__=="__main__":main()

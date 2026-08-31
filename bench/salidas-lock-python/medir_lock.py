"""C38/C39: coste aislado y recuperación del lock Python, Windows solamente."""
from __future__ import annotations
import json, os, statistics, subprocess, sys, time

ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from filex.cerrojo import Candado, _tomar_mutex, _soltar_mutex

def mono(n=400000):
    t=time.perf_counter(); x=0
    for i in range(n): x += i*i
    return (time.perf_counter()-t)*1e6

def proc(n=5):
    x=[]
    for _ in range(n):
        t=time.perf_counter(); subprocess.run(["ffprobe","-version"],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20); x.append((time.perf_counter()-t)*1e6)
    return statistics.median(x)

def ciclo(mutex: bool, n=99):
    old=os.environ.get("FILEX_CERROJO_MUTEX"); os.environ["FILEX_CERROJO_MUTEX"]="1" if mutex else "0"
    try:
        v=[]
        for _ in range(n):
            if mutex:
                t=time.perf_counter_ns(); h, ocupado, aviso=_tomar_mutex("c38-coste",0); assert h and not ocupado and not aviso; _soltar_mutex(h)
            else:
                c=Candado("c38-coste",metadatos="medir"); t=time.perf_counter_ns(); ok=c.tomar(); c.soltar(); assert ok
            v.append((time.perf_counter_ns()-t)/1000)
        return {"n":n,"mediana_us":round(statistics.median(v),1),"min_us":round(min(v),1),"max_us":round(max(v),1)}
    finally:
        if old is None: os.environ.pop("FILEX_CERROJO_MUTEX",None)
        else: os.environ["FILEX_CERROJO_MUTEX"]=old

def muerto(mutex: bool):
    old=os.environ.get("FILEX_CERROJO_MUTEX"); os.environ["FILEX_CERROJO_MUTEX"]="1" if mutex else "0"
    src="import os,sys,time;sys.path.insert(0,sys.argv[1]);from filex.cerrojo import Candado;c=Candado('c38-muerto');print(os.getpid(),flush=True);assert c.tomar();time.sleep(30)"
    p=subprocess.Popen([sys.executable,"-c",src,ROOT],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,text=True)
    pid=int(p.stdout.readline().strip()); subprocess.run(["taskkill","/F","/T","/PID",str(pid)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20); p.wait(timeout=20)
    t=time.perf_counter_ns(); c=Candado("c38-muerto"); ok=c.tomar(espera=2); c.soltar(); us=(time.perf_counter_ns()-t)/1000
    if old is None: os.environ.pop("FILEX_CERROJO_MUTEX",None)
    else: os.environ["FILEX_CERROJO_MUTEX"]=old
    return {"ok":ok,"us":round(us,1)}

def proceso(codigo, n=9):
    """Arranque Windows calentado; no mezcla esta pieza con el mutex."""
    subprocess.run([sys.executable,"-c",codigo],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20)
    v=[]
    for _ in range(n):
        t=time.perf_counter_ns(); r=subprocess.run([sys.executable,"-c",codigo],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20); assert r.returncode==0; v.append((time.perf_counter_ns()-t)/1000)
    return {"n":n,"mediana_us":round(statistics.median(v),1),"min_us":round(min(v),1),"max_us":round(max(v),1)}

if __name__=="__main__":
    toma="import sys;sys.path.insert(0,%r);from filex.cerrojo import _tomar_mutex,_soltar_mutex;h,o,a=_tomar_mutex('c38-proceso',0);_soltar_mutex(h)" % ROOT
    guardia="import sys;sys.path.insert(0,%r);from filex.gpu import guardia;guardia()" % ROOT
    a={"testigo_mono_ini_us":round(mono(),1),"testigo_proc_ini_us":round(proc(),1),"archivo_rango":ciclo(False),"mutex_global":ciclo(True),"muerto_archivo":muerto(False),"muerto_compuesto":muerto(True),"arranque_python_pass":proceso("pass"),"arranque_mas_mutex":proceso(toma),"arranque_mas_guardia":proceso(guardia)}
    a["testigo_mono_fin_us"]=round(mono(),1); a["testigo_proc_fin_us"]=round(proc(),1)
    json.dump(a,open(os.path.join(os.path.dirname(__file__),"medir_lock.json"),"w",encoding="utf-8"),indent=2)
    print(json.dumps(a,ensure_ascii=False))

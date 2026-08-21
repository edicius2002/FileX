# Monitor de GPU: ejecuta un comando y reporta pico de memoria Y pico de
# utilizacion, con linea base previa. Necesario para PROBAR que un motor
# usa realmente la GPU (no basta con que no falle).
import subprocess, sys, threading, time, json, os

def smi():
    try:
        o = subprocess.check_output(
            ["nvidia-smi","--query-gpu=memory.used,utilization.gpu",
             "--format=csv,noheader,nounits"], text=True).strip().splitlines()[0]
        m,u = o.split(",")
        return int(m.strip()), int(u.strip())
    except Exception:
        return 0,0

def main():
    label = sys.argv[1]
    cmd = sys.argv[2:]
    # linea base: 8 muestras en 2 s
    b_mem=[]; b_util=[]
    for _ in range(8):
        m,u = smi(); b_mem.append(m); b_util.append(u); time.sleep(0.25)
    base_mem = min(b_mem); base_util = max(b_util)
    samples=[]
    stop = threading.Event()
    def sampler():
        while not stop.is_set():
            samples.append(smi()); time.sleep(0.2)
    th = threading.Thread(target=sampler, daemon=True); th.start()
    t0=time.time()
    rc = subprocess.call(cmd)
    dur=time.time()-t0
    stop.set(); th.join(timeout=2)
    peak_mem = max((s[0] for s in samples), default=base_mem)
    peak_util = max((s[1] for s in samples), default=0)
    res = dict(etiqueta=label, rc=rc, segundos=round(dur,2),
               base_mem_MiB=base_mem, pico_mem_MiB=peak_mem,
               delta_mem_MiB=peak_mem-base_mem,
               base_util_pct=base_util, pico_util_pct=peak_util,
               muestras=len(samples))
    print("GPUWATCH " + json.dumps(res, ensure_ascii=False))
    sys.exit(0)

main()

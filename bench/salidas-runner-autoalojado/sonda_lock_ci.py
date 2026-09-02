# -*- coding: utf-8 -*-
"""C44 -- la pregunta del lock: coste de tomar/soltar, coste de recuperar un
huerfano de verdad (proceso matado con taskkill /F, no un PID falso), y
control NEGATIVO (dueno vivo, NO se roba). Fichero de lock AISLADO en los
tres casos (ruta=), nunca el `%TEMP%/filex-gpu.lock` real: cero interferencia
con la maquina real (no toca nvidia-smi -- se usa `.tomar()`/`.soltar()`
directos, no el `with Lock(...)`, que si llama a `guardia()`).

uso: python sonda_lock_ci.py
"""
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)
from filex import gpu  # noqa: E402

HIJO = (
    "import json,sys,time,os; sys.path.insert(0,sys.argv[1]); "
    "from filex.gpu import Lock; x=Lock('hijo-ci', ruta=sys.argv[2]); "
    "ok=x.tomar(espera=5); "
    "print(json.dumps({'ok':ok,'pid':os.getpid()}),flush=True); "
    "time.sleep(float(sys.argv[3])); x.soltar()"
)


def coste_tomar_soltar(n=9):
    ruta = os.path.join(tempfile.mkdtemp(prefix="ci-lock-coste-"), "filex-gpu.lock")
    tiempos = []
    for _ in range(n):
        l = gpu.Lock("bench-coste", ruta=ruta)
        t0 = time.perf_counter()
        ok = l.tomar(espera=0.0)
        t1 = time.perf_counter()
        assert ok
        l.soltar()
        t2 = time.perf_counter()
        tiempos.append({"tomar_us": round((t1 - t0) * 1e6, 1),
                        "soltar_us": round((t2 - t1) * 1e6, 1)})
    return {
        "n": n,
        "tomar_us_mediana": round(statistics.median(t["tomar_us"] for t in tiempos), 1),
        "soltar_us_mediana": round(statistics.median(t["soltar_us"] for t in tiempos), 1),
        "detalle": tiempos,
    }


def control_negativo_dueno_vivo():
    """Dueno vivo, real (proceso hijo real, no un PID inventado): un
    `tomar(espera=corta)` NO debe robarlo. Trampa 36: un "no interfiere" sin
    un caso en que si interfiera no significa nada -- este es el caso en que
    SI hay alguien, y hay que ver que respeta."""
    ruta = os.path.join(tempfile.mkdtemp(prefix="ci-lock-negativo-"), "filex-gpu.lock")
    p = subprocess.Popen([sys.executable, "-c", HIJO, RAIZ, ruta, "20"],
                         stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True)
    linea = json.loads(p.stdout.readline())
    assert linea["ok"], "el hijo no pudo tomar su propio lock aislado"
    try:
        t0 = time.perf_counter()
        l = gpu.Lock("intento-ci", ruta=ruta)
        ok = l.tomar(espera=1.0, intervalo=0.1)
        dt = time.perf_counter() - t0
        return {"robo_indebido": ok, "dt_s": round(dt, 3),
                "pid_dueno_vivo": linea["pid"]}
    finally:
        p.kill()
        p.wait(timeout=10)
        for f in (p.stdout, p.stderr):
            if f is not None:
                f.close()


def control_positivo_recupera_huerfano_real():
    """El caso que le importa a C44: el job de CI muere a mitad (GitHub lo
    cancela, el runner se cae, un `taskkill /F` externo). `finally` NO
    corre (trampa 47): la unica red es la deteccion de huerfano de N29, que
    aqui se ejerce sobre un proceso REAL matado de verdad, no un PID
    inventado (ese caso ya lo cubre `pruebas/test_hito2.py`)."""
    ruta = os.path.join(tempfile.mkdtemp(prefix="ci-lock-positivo-"), "filex-gpu.lock")
    p = subprocess.Popen([sys.executable, "-c", HIJO, RAIZ, ruta, "30"],
                         stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True)
    linea = json.loads(p.stdout.readline())
    assert linea["ok"], "el hijo no pudo tomar su propio lock aislado"
    with open(ruta, encoding="utf-8") as f:
        campos_antes = f.readline().rstrip("\n").split("\t")

    # `taskkill /F /T` -- exactamente el mismo mecanismo que la trampa 47 y
    # el N29 real: SIGKILL/TerminateProcess, sin pasar por `finally`.
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(linea["pid"])],
                   stdin=subprocess.DEVNULL, capture_output=True, timeout=20)
    p.wait(timeout=20)
    for f in (p.stdout, p.stderr):
        if f is not None:
            f.close()

    t0 = time.perf_counter()
    l = gpu.Lock("recuperador-ci", ruta=ruta)
    ok = l.tomar(espera=10.0, intervalo=0.1)
    dt = time.perf_counter() - t0
    if ok:
        l.soltar()
    return {"recupero": ok, "dt_s": round(dt, 3),
            "pid_muerto": linea["pid"], "campos_lock_antes": campos_antes}


def main():
    print("=== coste tomar/soltar (lock aislado, n=9) ===")
    a = coste_tomar_soltar()
    print(json.dumps(a, indent=2, ensure_ascii=False))

    print("\n=== control NEGATIVO: dueno vivo, no se roba ===")
    b = control_negativo_dueno_vivo()
    print(json.dumps(b, indent=2, ensure_ascii=False))

    print("\n=== control POSITIVO: dueno muerto de verdad (taskkill /F), se recupera ===")
    c = control_positivo_recupera_huerfano_real()
    print(json.dumps(c, indent=2, ensure_ascii=False))

    out = {"coste_tomar_soltar": a, "control_negativo": b, "control_positivo": c,
           "plataforma": sys.platform, "python": sys.version.split()[0]}
    dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sonda_lock_ci.json")
    json.dump(out, open(dst, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("\nescrito", dst)


if __name__ == "__main__":
    main()

"""La carrera por el mismo destino, entre PROCESOS de verdad.

`bench/hito7-superficies.md` §5.3 reprodujo el fallo entre HILOS de un mismo
proceso (tres peticiones a la API). Ahí se cerró con un `set` en memoria, y el
propio informe declaró el límite: **dos procesos `filex` distintos siguen
pisándose**. Este arnés reproduce ese caso y mide el cierre.

    python bench/salidas-cerrojo/carrera_destino.py --modo proceso   (el ANTES)
    python bench/salidas-cerrojo/carrera_destino.py --modo maquina   (el DESPUÉS)

Cada conversión va en un proceso propio (`python -m ...`), y el disparo es una
CITA en dos tiempos, no un `sleep`: cada obrero construye su `FileX` —que es lo
caro— y solo entonces avisa; el padre espera a que estén los N y suelta el
pistoletazo tocando un fichero. Con un `sleep` se estaría midiendo el arranque
del intérprete, no la carrera.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))


def _sha(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


# ---------------------------------------------------------------------- obrero

def obrero(args) -> int:
    sys.path.insert(0, RAIZ)
    from filex.nucleo import FileX

    fx = FileX(raices_lectura=[args.dir])
    with open(args.listo, "w") as f:
        f.write(str(os.getpid()))
    t0 = time.perf_counter()
    while not os.path.exists(args.go):
        if time.perf_counter() - t0 > 120:
            print(json.dumps({"error": "la cita no llegó"}))
            return 2
        time.sleep(0.001)

    ini = time.perf_counter()
    conv = fx.convertir(args.entrada, args.salida, {}, timeout=180)
    ms = (time.perf_counter() - ini) * 1000
    existe = os.path.exists(args.salida)
    print(json.dumps({
        "pid": os.getpid(),
        "entrada": os.path.basename(args.entrada),
        "bytes_entrada": os.path.getsize(args.entrada),
        "ok": conv.ok,
        "veredicto": conv.veredicto,
        "motivo": conv.motivo,
        "aviso": conv.aviso,
        # Lo que la respuesta DECLARA del fichero de salida, que es justo lo que
        # en el hito 7 describía un fichero que ya no existía.
        "bytes_declarados": os.path.getsize(args.salida) if existe else None,
        "sha_declarado": _sha(args.salida) if existe else None,
        "ms": round(ms, 1),
    }, ensure_ascii=False))
    return 0 if conv.ok else 1


# ----------------------------------------------------------------------- padre

def carrera(dir_trabajo: str, entradas: list[str], salida: str, modo: str,
            etiqueta: str) -> dict:
    citas = os.path.join(dir_trabajo, "_cita")
    shutil.rmtree(citas, ignore_errors=True)
    os.makedirs(citas, exist_ok=True)
    go = os.path.join(citas, "GO")
    if os.path.exists(salida):
        os.remove(salida)

    entorno = dict(os.environ, FILEX_CERROJO_DESTINO=modo, PYTHONIOENCODING="utf-8")
    procs = []
    for i, ent in enumerate(entradas):
        listo = os.path.join(citas, f"listo-{i}")
        procs.append((listo, subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), "--obrero",
             "--dir", dir_trabajo, "--entrada", ent, "--salida", salida,
             "--listo", listo, "--go", go],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
            errors="replace", env=entorno, cwd=RAIZ)))

    t0 = time.perf_counter()
    while not all(os.path.exists(l) for l, _ in procs):
        if time.perf_counter() - t0 > 300:
            for _, p in procs:
                p.kill()
            raise SystemExit("TIMEOUT esperando a que los obreros estén listos")
        time.sleep(0.02)
    listos_en = time.perf_counter() - t0
    open(go, "w").close()          # pistoletazo

    filas = []
    for _, p in procs:
        out, err = p.communicate(timeout=600)
        try:
            filas.append(json.loads(out.strip().splitlines()[-1]))
        except Exception:
            filas.append({"error": (out or "")[:200], "stderr": (err or "")[-300:]})

    en_disco = os.path.getsize(salida) if os.path.exists(salida) else None
    sha_disco = _sha(salida) if os.path.exists(salida) else None
    exitos = [f for f in filas if f.get("ok")]
    mienten = [f for f in exitos if f.get("sha_declarado") != sha_disco]

    print(f"\n===== {etiqueta}  (FILEX_CERROJO_DESTINO={modo}) =====")
    print(f"  arranque de los {len(procs)} procesos hasta la cita: {listos_en:.1f} s")
    for f in filas:
        if "error" in f:
            print(f"  ERROR {f}")
            continue
        print(f"  pid {f['pid']:>6}  {f['entrada']:<22} "
              f"{'ok' if f['ok'] else 'NO':<3} "
              f"declara={str(f['bytes_declarados']):>8} B  "
              f"sha={f['sha_declarado']}  {f['ms']:>7} ms  {f['motivo'][:52]}")
    print(f"  EN EL DISCO: {en_disco} B  sha={sha_disco}")
    print(f"  éxitos={len(exitos)}   éxitos que describen un fichero que NO está: "
          f"{len(mienten)}")
    return {"modo": modo, "etiqueta": etiqueta, "filas": filas,
            "bytes_en_disco": en_disco, "sha_en_disco": sha_disco,
            "exitos": len(exitos), "exitos_mentirosos": len(mienten),
            "ficheros_en_destino": len(os.listdir(os.path.dirname(salida)))}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--obrero", action="store_true")
    p.add_argument("--dir")
    p.add_argument("--entrada")
    p.add_argument("--salida")
    p.add_argument("--listo")
    p.add_argument("--go")
    p.add_argument("--modo", default="ambos")
    p.add_argument("--json", default=None)
    args = p.parse_args()
    if args.obrero:
        return obrero(args)

    base = os.path.join(AQUI, "desechable", "carrera")
    shutil.rmtree(base, ignore_errors=True)
    dsal = os.path.join(base, "salida")
    os.makedirs(dsal, exist_ok=True)
    entradas = []
    for nombre in ("tipico.png", "tipico.jpg", "patologico_16bit.tif"):
        dst = os.path.join(base, nombre)
        shutil.copy2(os.path.join(RAIZ, "corpus", "imagen", nombre), dst)
        entradas.append(dst)
    salida = os.path.join(dsal, "salida.webp")

    print("Las tres entradas del hito 7 §5.3, tres PROCESOS, un destino:")
    for e in entradas:
        print(f"  {os.path.basename(e):<22} {os.path.getsize(e):>10} B")

    modos = ["proceso", "maquina"] if args.modo == "ambos" else [args.modo]
    res = []
    for m in modos:
        # El ganador NO es determinista y el invariante SÍ: por eso la carrera
        # con el cerrojo puesto se repite. Una sola pasada no distingue «hay un
        # cerrojo» de «hoy ha ganado siempre el mismo».
        veces = 1 if m == "proceso" else 3
        for k in range(veces):
            etiqueta = ("ANTES — solo el cerrojo de proceso del hito 7"
                        if m == "proceso" else
                        f"DESPUÉS — cerrojo de máquina (pasada {k + 1}/{veces})")
            res.append(carrera(base, entradas, salida, m, etiqueta))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

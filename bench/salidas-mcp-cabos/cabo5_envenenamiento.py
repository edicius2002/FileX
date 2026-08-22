"""Cabo 5 (segunda parte) — ¿la ventana es EXPLOTABLE, y de que forma?

Que la entrada este abierta mucho tiempo no basta: hay que saber QUE puede hacer un
tercero durante ese tiempo. Se prueban cuatro vectores mientras ffmpeg convierte:

    (a) `os.replace(entrada, otro)`  — cambiar el fichero por otro (el vector clasico)
    (b) `os.remove(entrada)`         — borrarlo
    (c) escritura EN SITIO (`r+b`)   — cambiar el CONTENIDO sin cambiar el fichero
    (d) renombrar el DIRECTORIO padre— mover el suelo bajo los pies del motor

Y ademas se mide la ventana ANTES de que el motor abra la entrada, que es donde (a) y (d)
si funcionan en cualquier sistema.
"""

import hashlib
import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

RAIZ = Path("D:/Work/research/FileX")
SALIDA = RAIZ / "bench/salidas-mcp-cabos"
TRABAJO = SALIDA / "cabo5_env"
ENTRADA_ORIG = RAIZ / "corpus/video/tipico.mp4"
ARGS = ["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-c:a", "aac"]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def lanzar(entrada, salida):
    p = subprocess.Popen(["ffmpeg", "-nostdin", "-y", "-i", str(entrada), *ARGS, str(salida)],
                         stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for f in (p.stdout, p.stderr):
        threading.Thread(target=lambda f=f: f.read(), daemon=True).start()
    return p


def limpio():
    d = TRABAJO / "limpio"
    d.mkdir(parents=True, exist_ok=True)
    ent = d / "entrada.mp4"
    shutil.copyfile(ENTRADA_ORIG, ent)
    sal = d / "salida.mp4"
    t0 = time.time()
    p = lanzar(ent, sal)
    p.wait(timeout=900)
    return {"ms": round((time.time() - t0) * 1000, 1), "sha_salida": sha(sal),
            "bytes_salida": sal.stat().st_size, "returncode": p.returncode}


def vector(nombre, accion, retardo=3.0):
    d = TRABAJO / nombre
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    ent = d / "entrada.mp4"
    shutil.copyfile(ENTRADA_ORIG, ent)
    sal = d / "salida.mp4"
    reg = {"vector": nombre, "retardo_s": retardo}
    t0 = time.time()
    p = lanzar(ent, sal)
    time.sleep(retardo)
    reg["ffmpeg_seguia_vivo"] = p.poll() is None
    try:
        reg["resultado_accion"] = accion(d, ent)
        reg["accion_permitida"] = True
    except OSError as e:
        reg["accion_permitida"] = False
        reg["error"] = f"{type(e).__name__}: {getattr(e, 'winerror', '')} {e.strerror}"
    try:
        p.wait(timeout=900)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
    reg["ms_total"] = round((time.time() - t0) * 1000, 1)
    reg["returncode"] = p.returncode
    s = d / "salida.mp4"
    if not s.exists():
        s = next((x for x in d.glob("**/salida.mp4")), None)
    reg["bytes_salida"] = s.stat().st_size if s and s.exists() else None
    reg["sha_salida"] = sha(s) if s and s.exists() else None
    return reg


def a_reemplazar(d, ent):
    otro = d / "otro.mp4"
    shutil.copyfile(RAIZ / "corpus/video/trivial.mp4", otro)
    os.replace(otro, ent)
    return "os.replace OK"


def b_borrar(d, ent):
    os.remove(ent)
    return "os.remove OK"


def c_en_sitio(d, ent):
    tam = ent.stat().st_size
    off = int(tam * 0.6)
    with open(ent, "r+b") as f:
        f.seek(off)
        f.write(b"\x00" * 65536)
    return f"escritos 65536 ceros en el offset {off} de {tam}"


def d_renombrar_padre(d, ent):
    nuevo = d.with_name(d.name + "_movido")
    os.replace(d, nuevo)
    return f"directorio renombrado a {nuevo.name}"


def main():
    TRABAJO.mkdir(parents=True, exist_ok=True)
    base = limpio()
    print("conversion limpia:", base, flush=True)
    res = {"referencia_limpia": base, "vectores": []}
    for nombre, fn in (("a_reemplazar", a_reemplazar), ("b_borrar", b_borrar),
                       ("c_escritura_en_sitio", c_en_sitio),
                       ("d_renombrar_directorio_padre", d_renombrar_padre)):
        r = vector(nombre, fn)
        print(f"{nombre:30s} permitida={r['accion_permitida']} "
              f"{r.get('error') or r.get('resultado_accion')} | rc={r['returncode']} "
              f"| salida={r['bytes_salida']} sha={r['sha_salida']} "
              f"| identica_a_la_limpia={r['sha_salida'] == base['sha_salida']}", flush=True)
        res["vectores"].append(r)
    (SALIDA / "cabo5_envenenamiento.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

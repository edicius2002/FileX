"""Cabo 5 (tercera parte) — los mismos cuatro vectores en Linux (WSL2).

En Windows tres de los cuatro los deniega el sistema. En POSIX no hay bloqueo obligatorio,
asi que se espera lo contrario. Lo que importa para R8 es QUE LEE el motor despues.

Se ejecuta DENTRO de WSL. Lector: un proceso Python que abre el fichero, lee la mitad,
duerme y lee el resto — es el modelo de un motor que lee en streaming.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

TMP = "/tmp/filex_cabo5"

LECTOR = r'''
import sys, time, hashlib
ruta = sys.argv[1]
h = hashlib.sha256()
f = open(ruta, "rb")
leidos = 0
tam = 0
import os
tam = os.fstat(f.fileno()).st_size
mitad = tam // 2
d = f.read(mitad); h.update(d); leidos += len(d)
print("ABIERTO_Y_MEDIO_LEIDO", flush=True)
time.sleep(3)
while True:
    d = f.read(1 << 20)
    if not d: break
    h.update(d); leidos += len(d)
print("LEIDOS", leidos, "SHA", h.hexdigest()[:16], flush=True)
'''


def guion():
    return f'''
set -e
rm -rf {TMP}; mkdir -p {TMP}
cat > {TMP}/lector.py <<'PYEOF'
{LECTOR}
PYEOF
python3 - <<'PYEOF'
import json, os, shutil, subprocess, time, hashlib
TMP = "{TMP}"

def sha(p):
    h = hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<20), b""): h.update(b)
    return h.hexdigest()[:16]

def caso(nombre, accion):
    d = os.path.join(TMP, nombre); os.makedirs(d, exist_ok=True)
    ent = os.path.join(d, "entrada.bin")
    with open(ent,"wb") as f: f.write(b"A"*(8<<20))
    limpio = sha(ent)
    p = subprocess.Popen(["python3", os.path.join(TMP,"lector.py"), ent],
                         stdout=subprocess.PIPE, text=True)
    p.stdout.readline()          # ABIERTO_Y_MEDIO_LEIDO
    reg = {{"vector": nombre, "sha_original": limpio}}
    try:
        reg["resultado"] = accion(d, ent); reg["permitida"] = True
    except OSError as e:
        reg["permitida"] = False; reg["error"] = f"{{type(e).__name__}}: {{e}}"
    salida = p.stdout.readline().strip()
    p.wait(timeout=60)
    reg["lo_que_leyo_el_motor"] = salida
    return reg

def a_reemplazar(d, ent):
    otro = os.path.join(d,"otro.bin")
    with open(otro,"wb") as f: f.write(b"B"*(8<<20))
    os.replace(otro, ent); return "os.replace OK"

def b_borrar(d, ent):
    os.remove(ent); return "os.remove OK"

def c_en_sitio(d, ent):
    with open(ent,"r+b") as f:
        f.seek(int((8<<20)*0.75)); f.write(b"Z"*65536)
    return "escritura en sitio OK"

def d_renombrar_padre(d, ent):
    nuevo = d + "_movido"; os.replace(d, nuevo); return "directorio renombrado"

res = [caso(n, f) for n, f in (("a_reemplazar", a_reemplazar), ("b_borrar", b_borrar),
                               ("c_escritura_en_sitio", c_en_sitio),
                               ("d_renombrar_directorio_padre", d_renombrar_padre))]
# sha de referencia de un fichero de 8 MiB de 'A' y otro con la zona envenenada
import hashlib
h = hashlib.sha256(); h.update(b"A"*(8<<20)); ref_A = h.hexdigest()[:16]
b = bytearray(b"A"*(8<<20)); off=int((8<<20)*0.75); b[off:off+65536]=b"Z"*65536
h = hashlib.sha256(); h.update(bytes(b)); ref_env = h.hexdigest()[:16]
print("__JSON__" + json.dumps({{"referencia_A": ref_A, "referencia_envenenada": ref_env,
                               "vectores": res}}))
PYEOF
'''


def main():
    r = subprocess.run(["wsl", "-e", "bash", "-lc", guion()],
                       capture_output=True, text=True, timeout=600)
    salida = r.stdout
    marca = salida.find("__JSON__")
    if marca < 0:
        print("NO SE OBTUVO JSON")
        print(salida[-3000:])
        print(r.stderr[-2000:])
        return 1
    datos = json.loads(salida[marca + len("__JSON__"):].strip())
    Path(__file__).with_name("cabo5_linux.json").write_text(
        json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    print("sha de 8 MiB de 'A'      :", datos["referencia_A"])
    print("sha con la zona envenenada:", datos["referencia_envenenada"])
    for v in datos["vectores"]:
        print(f"{v['vector']:30s} permitida={v['permitida']!s:6s} "
              f"{v.get('error') or v.get('resultado')} -> motor leyo: {v['lo_que_leyo_el_motor']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

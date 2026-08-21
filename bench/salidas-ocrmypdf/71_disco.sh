#!/usr/bin/env bash
# Cierre de dependencias de apt para el conjunto ocrmypdf + tesseract + unpaper + pngquant.
set -u
PKGS="ocrmypdf tesseract-ocr tesseract-ocr-spa unpaper pngquant"
python3 - "$PKGS" <<'PY'
import subprocess, sys, collections
raiz = sys.argv[1].split()
vistos, cola = set(), collections.deque(raiz)
while cola:
    p = cola.popleft()
    if p in vistos:
        continue
    vistos.add(p)
    try:
        s = subprocess.run(["apt-cache","depends","--recurse","--no-recommends",
                            "--no-suggests","--no-conflicts","--no-breaks",
                            "--no-replaces","--no-enhances", p],
                           capture_output=True, text=True, timeout=120).stdout
    except Exception:
        continue
    for ln in s.splitlines():
        ln = ln.strip()
        if ln and not ln.startswith(("Depends","PreDepends","|","<")) and ":" not in ln:
            vistos.add(ln)
total = 0; falt = []
for p in sorted(vistos):
    r = subprocess.run(["dpkg-query","-W","-f=${Installed-Size}",p],
                       capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip().isdigit():
        total += int(r.stdout.strip())
    else:
        falt.append(p)
print(f"paquetes en el cierre: {len(vistos)}  (sin datos dpkg: {len(falt)})")
print(f"tamano instalado del cierre COMPLETO: {total} KB = {total/1024:.0f} MB")
PY
echo "--- solo lo que apt instalaria de nuevo en un Ubuntu limpio (simulacion) ---"
apt-get install -s --no-install-recommends $PKGS 2>/dev/null | tail -3
echo "--- tamano de los binarios/datos clave ---"
du -sh /usr/share/tesseract-ocr /usr/lib/python3/dist-packages/ocrmypdf /usr/bin/unpaper 2>/dev/null

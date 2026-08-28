import os
import shutil
import subprocess

print("shutil.which('bash') =", shutil.which("bash"))
for cual in ("bash", shutil.which("bash")):
    for pregunta in ("uname -a", "echo $BASH_VERSION", "ls /mnt 2>/dev/null | head -3",
                     "cat /proc/version 2>/dev/null | head -1"):
        try:
            r = subprocess.run([cual, "-c", pregunta], stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               timeout=60)
            print(f"[{cual}] {pregunta!r:42s} -> {r.stdout.strip()!r}")
        except Exception as e:
            print(f"[{cual}] {pregunta!r} -> {type(e).__name__}: {e}")
    print()

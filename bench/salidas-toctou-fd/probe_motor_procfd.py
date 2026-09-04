#!/usr/bin/env python3
"""¿Aceptan ffmpeg/magick/gs una entrada /proc/<pid>/fd/N (sin extension)?
Decide si el arreglo puede ser zero-copy (ruta estable) o necesita staging."""
import json
import os
import subprocess

ROOT = "/mnt/d/Work/research/FileX/.claude/worktrees/agent-a78d2fadcc71efd6f"
PNG = f"{ROOT}/corpus/imagen/tipico.png"
OUT = "/tmp/probe_motor_out"
res = {}

os.makedirs(OUT, exist_ok=True)
mipid = os.getpid()

# magick: /proc/pid/fd/N -> jpg. Sin extension, magick sniffea por contenido.
fd = os.open(PNG, os.O_RDONLY)
estable = f"/proc/{mipid}/fd/{fd}"
p = subprocess.run(["magick", estable, f"{OUT}/m.jpg"], capture_output=True, text=True)
res["magick_procfd_sin_ext"] = {"rc": p.returncode, "bytes": os.path.getsize(f"{OUT}/m.jpg") if os.path.exists(f"{OUT}/m.jpg") else 0, "stderr": p.stderr.strip()[:200]}
os.close(fd)

# magick con prefijo de formato explicito: png:/proc/pid/fd/N
fd = os.open(PNG, os.O_RDONLY)
estable = f"png:/proc/{mipid}/fd/{fd}"
p = subprocess.run(["magick", estable, f"{OUT}/m2.jpg"], capture_output=True, text=True)
res["magick_procfd_prefijo_png"] = {"rc": p.returncode, "bytes": os.path.getsize(f"{OUT}/m2.jpg") if os.path.exists(f"{OUT}/m2.jpg") else 0, "stderr": p.stderr.strip()[:200]}
os.close(fd)

# ffmpeg: -i /proc/pid/fd/N (ffmpeg sondea el stream, no la extension)
fd = os.open(PNG, os.O_RDONLY)
estable = f"/proc/{mipid}/fd/{fd}"
p = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-y", "-i", estable, f"{OUT}/f.jpg"], capture_output=True, text=True)
res["ffmpeg_procfd"] = {"rc": p.returncode, "bytes": os.path.getsize(f"{OUT}/f.jpg") if os.path.exists(f"{OUT}/f.jpg") else 0, "stderr": p.stderr.strip()[-200:]}
os.close(fd)

print(json.dumps(res, ensure_ascii=False, indent=2))
subprocess.run(["rm", "-rf", OUT], check=False)

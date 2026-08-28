import os
import shutil
import subprocess
import tempfile

tmp = tempfile.mkdtemp()
ruta = os.path.join(tmp, "x.lock")


def a_posix(r):
    r = r.replace("\\", "/")
    if len(r) > 1 and r[1] == ":":
        r = "/" + r[0].lower() + r[2:]
    return r


p = a_posix(ruta)
env = dict(os.environ, RUTA_LOCK=p)
print("posix:", p)
print("env tiene RUTA_LOCK:", repr(env.get("RUTA_LOCK")))
print("bash:", shutil.which("bash"), "| 'bash' a secas:", "bash")

for cual in (shutil.which("bash"), "bash"):
    r = subprocess.run([cual, "-c", 'echo "[${RUTA_LOCK}]"'], env=env,
                       stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    print(f"  con {cual!r}: {r.stdout!r} {r.stderr!r}")

for etiqueta, guion in (
        ("llaves", 'echo hola > "${RUTA_LOCK}"; echo rc=$?'),
        ("nc_llaves", '(set -o noclobber; echo hola > "${RUTA_LOCK}"); echo rc=$?'),
):
    r = subprocess.run([shutil.which("bash"), "-c", guion], env=env,
                       stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    print(f"-- {etiqueta}: out={r.stdout!r} err={r.stderr!r} "
          f"existe={os.path.exists(ruta)}")
    if os.path.exists(ruta):
        os.unlink(ruta)
print("dir:", os.listdir(tmp))

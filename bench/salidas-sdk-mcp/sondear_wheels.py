"""Acota en que version de mcp aparece cada capacidad, sin instalar nada.

Descarga las ruedas con `pip download --no-deps` y las inspecciona como ZIP.
Uso: python sondear_wheels.py 1.9.0 1.9.4 1.23.0 ...
"""
import glob, re, subprocess, sys, zipfile, json, tempfile, os

vers = sys.argv[1:] or ["1.8.1", "1.9.0", "1.9.4", "1.21.0", "1.23.0", "1.29.0", "2.0.0"]
d = tempfile.mkdtemp()
res = {}
for v in vers:
    subprocess.run([sys.executable, "-m", "pip", "download", "-q", "--no-deps", f"mcp=={v}", "-d", d],
                   check=False, capture_output=True)
    w = glob.glob(os.path.join(d, f"mcp-{v}-*.whl"))
    if not w:
        res[v] = {"error": "no se pudo descargar"}
        continue
    z = zipfile.ZipFile(w[0]); n = z.namelist()
    cs = z.read("mcp/client/session.py").decode("utf8", "replace") if "mcp/client/session.py" in n else ""
    ty = z.read("mcp/types.py").decode("utf8", "replace") if "mcp/types.py" in n else ""
    m = re.search(r'LATEST_PROTOCOL_VERSION\s*=\s*"([^"]+)"', ty)
    res[v] = {
        "protocolo": m.group(1) if m else "(mcp_types, paquete aparte)",
        "progress_callback_en_call_tool": "progress_callback" in cs,
        "roots_solo_si_hay_callback": "is not _default_list_roots_callback" in cs,
        "tasks_experimental_servidor": any(x.startswith("mcp/server/experimental/") for x in n),
    }
print(json.dumps(res, indent=2, ensure_ascii=False))

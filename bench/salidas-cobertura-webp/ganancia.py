"""Ganancia de cob/webp contra la union BASE u cob/png, y el solape declarado."""
import ast, json, ntpath, os, subprocess, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
W = RAIZ
SRC = os.path.join(W, "filex", "verificador.py")
BASE = os.environ.get("BASE_COBERTURA",
                      os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "base-cobertura.json"))
CARRIL = ["_webp", "_alfa_min_webp", "leer", "ojear", "_leer_simbolo",
          "_leer_codigo_huffman", "_vp8l_flujo"]
EXTRA = ["_huff_tabla", "_leer_longitudes", "_predice", "_alph_desfiltrar",
         "_vp8l_decodificar", "_distancia_plano", "_prefijo", "saltar",
         "_llenar", "_med2", "_selecciona", "_clamp_full", "_clamp_half"]

arbol = ast.parse(open(SRC, encoding="utf-8").read())
rangos = {}
for n in ast.walk(arbol):
    if isinstance(n, ast.FunctionDef) and n.name in CARRIL + EXTRA:
        rangos.setdefault(n.name, (n.lineno, n.end_lineno))


def lineas(txt, clave):
    d = json.loads(txt)
    for k, v in d["files"].items():
        if ntpath.basename(k.replace("/", "\\")) == "verificador.py":
            return set(v[clave]), v
    return set(), None


base_falta, vb = lineas(open(BASE, encoding="utf-8").read(), "missing_lines")
png_txt = subprocess.run(["git", "show", "cob/png:bench/salidas-cobertura-png/cobertura.json"],
                         cwd=W, capture_output=True, text=True).stdout
png_ejec, _ = lineas(png_txt, "executed_lines")
mio_ejec, _ = lineas(open(os.path.join(
    W, "bench", "salidas-cobertura-webp", "cobertura.json"), encoding="utf-8").read(),
    "executed_lines")

falta_tras_png = base_falta - png_ejec
mio_gana_sobre_union = falta_tras_png & mio_ejec
solape = base_falta & png_ejec & mio_ejec

print("verificador.py, %d sentencias" % vb["summary"]["num_statements"])
print("  sin ejecutar en la BASE del maestro          : %d" % len(base_falta))
print("  de esas, las ejecuta cob/png                 : %d" % len(base_falta & png_ejec))
print("  quedan sin ejecutar tras cob/png             : %d" % len(falta_tras_png))
print("  de esas, las ejecuta cob/webp (MI GANANCIA)  : %d" % len(mio_gana_sobre_union))
print("  solape (las tres: base sin ejecutar, png y yo): %d" % len(solape))
print("  mi ganancia bruta sobre la base sola          : %d" % len(base_falta & mio_ejec))
print()
print("%-22s %6s %6s %6s %6s" % ("funcion", "base", "trasPNG", "yo", "quedan"))
tot = [0, 0, 0, 0]
for nom in CARRIL + EXTRA:
    if nom not in rangos:
        continue
    a, b = rangos[nom]
    bf = {l for l in base_falta if a <= l <= b}
    tp = {l for l in falta_tras_png if a <= l <= b}
    yo = tp & mio_ejec
    q = tp - mio_ejec
    if not bf:
        continue
    print("%-22s %6d %6d %6d %6d" % (nom, len(bf), len(tp), len(yo), len(q)))
    tot = [tot[0] + len(bf), tot[1] + len(tp), tot[2] + len(yo), tot[3] + len(q)]
print("%-22s %6d %6d %6d %6d" % ("TOTAL", *tot))
print()
print("proyeccion del fichero: base %.2f %% -> con cob/png %.2f %% -> con los dos %.2f %%"
      % (vb["summary"]["percent_covered"],
         100 * (1 - len(falta_tras_png) / vb["summary"]["num_statements"]),
         100 * (1 - len(falta_tras_png - mio_ejec) / vb["summary"]["num_statements"])))
json.dump({
    "base_sin_ejecutar": len(base_falta),
    "cubiertas_por_cob_png": len(base_falta & png_ejec),
    "restantes_tras_cob_png": len(falta_tras_png),
    "ganadas_por_cob_webp_sobre_la_union": sorted(mio_gana_sobre_union),
    "n_ganadas_sobre_la_union": len(mio_gana_sobre_union),
    "solape_con_cob_png": len(solape),
    "ganancia_bruta_sobre_la_base_sola": len(base_falta & mio_ejec),
}, open(os.path.join(W, "bench", "salidas-cobertura-webp", "ganancia.json"),
        "w", encoding="utf-8"), ensure_ascii=False, indent=1)

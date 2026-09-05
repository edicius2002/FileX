"""Control de DISCRIMINACION de `pruebas/test_cob_fidelidad.py`.

Una prueba que no se pone roja cuando el codigo objetivo se rompe no cuenta
(trampa 116: el control positivo es el SUJETO CON EL DEFECTO). Este arnes
rompe UNA linea de `filex/verificador.py` por celda, corre SOLO la clase de
pruebas que deberia notarlo, y registra que pruebas se pusieron rojas.

Tres defensas del propio arnes, todas medidas antes por el proyecto:

* **Control de IDENTIDAD** (trampa 119): antes de correr nada se comprueba que
  el fichero mutado es DISTINTO del original. `git stash push <fichero>` sobre
  un fichero ya commiteado no hace nada y devuelve 0, y entonces el A/B corre
  dos veces el mismo codigo y sale «11 OK», que se lee como «mis pruebas no
  discriminan».
* **Vuelta al codigo bueno con `git checkout -- <fichero>`**, nunca con
  `git stash`.
* **Control de COMPILACION** (trampa 60): si la mutacion deja el fichero sin
  compilar, la celda se marca `nocompila` y NO cuenta como discriminacion: un
  rojo por `SyntaxError` no prueba que la prueba mire lo que dice mirar.

Uso:  python bench/salidas-cobertura-fidelidad/discriminacion.py [salida.json]
"""
import ast
import json
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OBJETIVO = os.path.join(RAIZ, "filex", "verificador.py")
PY = sys.executable

#: (id, funcion tocada, texto original, texto mutado, clase de pruebas)
#: El texto original tiene que ser UNICO en el fichero: si no lo es, la celda
#: se marca `ambiguo` y no cuenta.
CELDAS = [
    # ---- _num -----------------------------------------------------------
    ("num-unidades", "_num",
     'for u in ("px", "pt", "mm", "cm", "in", "%", "em"):',
     'for u in ("px",):',
     "Num"),
    ("num-por-defecto", "_num",
     "    if v is None:\n        return por_defecto",
     "    if v is None:\n        return 0.0",
     "Num"),
    # ---- svg_textos ------------------------------------------------------
    ("svg-anchor-middle", "svg_textos",
     "        if anchor == \"middle\":\n            x0 = x - an / 2.0",
     "        if anchor == \"middle\":\n            x0 = x",
     "SvgTextos"),
    ("svg-caja-degenerada", "svg_textos",
     "        if caja[2] <= caja[0] or caja[3] <= caja[1]:\n            continue",
     "        if False:\n            continue",
     "SvgTextos"),
    ("svg-texto-vacio", "svg_textos",
     "        txt = \"\".join(el.itertext()).strip()\n        if not txt:\n            continue",
     "        txt = \"\".join(el.itertext()).strip() or \"x\"\n        if not txt:\n            continue",
     "SvgTextos"),
    ("svg-banda-vertical", "svg_textos",
     "max(y - 0.75 * fs - vy, 0.0)",
     "max(y - 0.50 * fs - vy, 0.0)",
     "SvgTextos"),
    # ---- png_tinta_cajas -------------------------------------------------
    ("png-umbral-tinta", "png_tinta_cajas",
     "tinta = sum(hk[v] for v in range(256) if abs(v - fondo) > 64)",
     "tinta = sum(hk[v] for v in range(256) if abs(v - fondo) > 200)",
     "PngTintaCajas"),
    ("png-fondo-mas-frecuente", "png_tinta_cajas",
     "fondo = max(range(256), key=lambda v: hk[v])",
     "fondo = 255",
     "PngTintaCajas"),
    ("png-corte-por-y-max", "png_tinta_cajas",
     "            if y >= y_max:\n                break",
     "            if False:\n                break",
     "PngTintaCajas"),
    ("png-guarda-entrelazado", "png_tinta_cajas",
     'if m.get("entrelazado"):',
     "if False:",
     "PngTintaCajas"),
    ("png-caja-sin-pixeles", "png_tinta_cajas",
     '            r["cajas"].append({"caja": [x0, y0, x1, y1], "pixeles": 0,\n'
     '                               "tinta_pct": None})',
     '            r["cajas"].append({"caja": [x0, y0, x1, y1], "pixeles": 0,\n'
     '                               "tinta_pct": 0.0})',
     "PngTintaCajas"),
    # ---- fidelidad_vectorial --------------------------------------------
    ("i9-umbral-minimo", "fidelidad_vectorial",
     "    elif mejor is not None and mejor < TINTA_MIN_TEXTO:",
     "    elif mejor is not None and mejor < -1.0:",
     "FidelidadVectorial"),
    ("i9-peor-por-caja", "fidelidad_vectorial",
     "    elif peor < TINTA_MIN_TEXTO:",
     "    elif peor < -1.0:",
     "FidelidadVectorial"),
    ("i9-escala", "fidelidad_vectorial",
     'an / tx["ancho_usuario"], al / tx["alto_usuario"])',
     "1.0, 1.0)",
     "FidelidadVectorial"),
    ("i9-cobertura-falsa", "fidelidad_vectorial",
     '    if not ti["evaluable"]:\n        cob["I9"] = False',
     '    if not ti["evaluable"]:\n        cob["I9"] = True',
     "FidelidadVectorial"),
    # ---- fidelidad_video (V9, en proceso) --------------------------------
    ("v9-rejilla", "fidelidad_video",
     "        if rejilla is True:",
     "        if rejilla is None:",
     "FidelidadVideoV9"),
    ("v9-cobertura", "fidelidad_video",
     '        cob["V9"] = rejilla is not None',
     '        cob["V9"] = True',
     "FidelidadVideoV9"),
    # ---- fidelidad_video (con motor) -------------------------------------
    ("v5-und", "fidelidad_video",
     '                        if v and v != "und" and w != v:',
     "                        if False:",
     "FidelidadVideoMotor"),
    ("v2-comparacion", "fidelidad_video",
     "        elif ns_ != ne_:",
     "        elif False:",
     "FidelidadVideoMotor"),
    ("v8-suelo", "fidelidad_video",
     "        elif y < PSNR_SUELO_VIDEO:",
     "        elif y < -1.0:",
     "FidelidadVideoMotor"),
    ("v6-copia", "fidelidad_video",
     "        if copia:",
     "        if False:",
     "FidelidadVideoMotor"),
    # ---- fidelidad_imagen ------------------------------------------------
    ("i6-rmse", "fidelidad_imagen",
     "        elif v > 0:",
     "        elif v > 1e9:",
     "FidelidadImagen"),
    ("i7-umbral", "fidelidad_imagen",
     "    if v >= PSNR_MIN_IMAGEN:",
     "    if v >= 0.0:",
     "FidelidadImagen"),
    ("i7-excusa-grafismo", "fidelidad_imagen",
     "    elif grafismo and v >= 20.0:",
     "    elif False:",
     "FidelidadImagen"),
    ("i3-negro", "fidelidad_imagen",
     "                elif all(v <= 2 for v in px):",
     "                elif False:",
     "FidelidadImagen"),
    ("i8-grafismo", "fidelidad_imagen",
     '    if grafismo and dest in ("webp", "avif") and sonda.get("perdida") is not False:',
     "    if False:",
     "FidelidadImagen"),
    # ---- fidelidad_pdf ---------------------------------------------------
    ("p6-umbral-basura", "fidelidad_pdf",
     "    if 0 < ns < TEXTO_MIN_CHARS:",
     "    if False:",
     "FidelidadPdf"),
    ("p9-severidad-ocr", "fidelidad_pdf",
     '            h.append(_fid("P9", "fallo" if pidio_ocr else "aviso",',
     '            h.append(_fid("P9", "aviso",',
     "FidelidadPdf"),
    ("p2-sha", "fidelidad_pdf",
     "    if hs != he:",
     "    if False:",
     "FidelidadPdf"),
    ("p5-ocr", "fidelidad_pdf",
     "            if ns < TEXTO_MIN_CHARS:",
     "            if False:",
     "FidelidadPdf"),
]


def _leer():
    with open(OBJETIVO, encoding="utf-8") as fh:
        return fh.read()


def _restaurar():
    subprocess.run(["git", "checkout", "--", "filex/verificador.py"],
                   cwd=RAIZ, capture_output=True, timeout=120)


def _rojos(clase, tope):
    """Nombres de las pruebas que fallan o dan error en esa clase."""
    p = subprocess.run(
        [PY, "-m", "unittest", "-v", "pruebas.test_cob_fidelidad." + clase],
        cwd=RAIZ, capture_output=True, timeout=tope)
    txt = p.stderr.decode("utf-8", "replace")
    malas = []
    for l in txt.splitlines():
        if (" ... FAIL" in l or " ... ERROR" in l) and l.startswith("test_"):
            malas.append(l.split(" ")[0])
    if "\nFAIL: " in txt or "\nERROR: " in txt:
        for l in txt.splitlines():
            if l.startswith(("FAIL: ", "ERROR: ")):
                n = l.split(" ", 1)[1].split(" ")[0]
                if n not in malas:
                    malas.append(n)
    return sorted(set(malas)), txt.strip().splitlines()[-1] if txt else ""


def main():
    salida = sys.argv[1] if len(sys.argv) > 1 else None
    tope = int(os.environ.get("FILEX_TOPE_CELDA", "1800"))
    original = _leer()
    fuera = []
    for ident, funcion, viejo, nuevo, clase in CELDAS:
        estado = "ok"
        if original.count(viejo) != 1:
            fuera.append({"id": ident, "funcion": funcion, "clase": clase,
                          "estado": "ambiguo",
                          "apariciones": original.count(viejo), "rojos": []})
            print("%-22s AMBIGUO (%d apariciones)"
                  % (ident, original.count(viejo)))
            continue
        mutado = original.replace(viejo, nuevo, 1)
        assert mutado != original, "control de identidad: no cambio nada"
        with open(OBJETIVO, "w", encoding="utf-8", newline="") as fh:
            fh.write(mutado)
        try:
            # Trampa 60: un rojo por SyntaxError no prueba nada.
            try:
                ast.parse(mutado)
            except SyntaxError:
                estado = "nocompila"
                rojos, ultima = [], "no compila"
            else:
                rojos, ultima = _rojos(clase, tope)
        finally:
            _restaurar()
        assert _leer() == original, "no volvio al codigo bueno"
        if estado == "ok" and not rojos:
            estado = "NO_DISCRIMINA"
        fuera.append({"id": ident, "funcion": funcion, "clase": clase,
                      "estado": estado, "rojos": rojos, "resumen": ultima})
        print("%-22s %-14s %2d rojos  %s"
              % (ident, estado, len(rojos), ", ".join(rojos[:4])))
    res = {"celdas": fuera,
           "discriminan": sum(1 for c in fuera if c["estado"] == "ok"),
           "total": len(fuera)}
    if salida:
        with open(salida, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=1, ensure_ascii=False)
    print("DISCRIMINAN %d de %d" % (res["discriminan"], res["total"]))
    return 0 if res["discriminan"] == res["total"] else 1


if __name__ == "__main__":
    sys.exit(main())

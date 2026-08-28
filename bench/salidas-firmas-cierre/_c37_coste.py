"""C37 / paso 2 - EL COSTE DE LEER MAS ALLA DEL BYTE 512, y cuando se dispara.

El encargo apunta una via: *leer mas alla del byte 512 solo cuando la extension
lo pide*. Antes de heredarla hay que ponerle numero (trampa 64: un pendiente que
propone un mecanismo lleva dentro un coste que nadie ha medido).

UN ERROR DE ARNES, PAGADO Y CORREGIDO, que es la mitad del interes de esto.
La primera version media las «variantes» como `leer(2056)` seguido de una
llamada a `V.firma_real`, que vuelve a abrir el fichero: **dos `open` por
celda**. Daba ×2,1 y ese ×2,1 era el arnes, no el diseno. Es la trampa 36 con
otra cara: no compares dos totales que contienen el trozo, mide el trozo.

Se miden TRES cosas:

  A. el primitivo AISLADO: `open + read(512)` frente a `open + read(2056)`
     sobre los mismos ficheros, y la tanda se REPITE para ver si el signo de la
     diferencia se conserva -- si no se conserva, la diferencia esta por debajo
     del suelo y no es una medida;
  B. `firma_real` ENTERA, la de HEAD contra la del arbol de trabajo, las dos en
     esta tanda y sobre los mismos ficheros (trampa 59: nada de comparar contra
     una cifra publicada en otro informe);
  C. cuantas veces se dispararia la puerta por extension sobre el censo real.

Medianas de n>=9, con los DOS testigos de ruido y tope de 20 s en el de proceso.

Uso:  python bench/salidas-firmas-cierre/_c37_coste.py <dir_desechable>
"""
import hashlib
import importlib.util
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)

N = 9
_NCORTO = 512
_NLARGO = 2056
EXT_CAB_LARGA = {".pict", ".pct", ".pcd", ".pcds"}


# ------------------------------------------------------------ testigos
def testigo_cpu(n=200000):
    t = time.perf_counter()
    h = b"x"
    for _ in range(n):
        h = hashlib.sha256(h).digest()
    return (time.perf_counter() - t) * 1000


def testigo_proc(tope=20.0):
    t = time.perf_counter()
    try:
        subprocess.run(["ffprobe", "-v", "quiet", "-version"],
                       capture_output=True, stdin=subprocess.DEVNULL, timeout=tope)
    except Exception:
        return tope * 1000, True
    return (time.perf_counter() - t) * 1000, False


def med(fn, n=N):
    return statistics.median([fn() for _ in range(n)])


def tanda(ficheros, fn):
    t = time.perf_counter()
    for p in ficheros:
        fn(p)
    return (time.perf_counter() - t) * 1000


def leer(ruta, n):
    with open(ruta, "rb") as fh:
        return fh.read(n)


def carga_head():
    tmp = os.path.join(tempfile.gettempdir(), "f2_verificador_head.py")
    r = subprocess.run(["git", "show", "HEAD:filex/verificador.py"],
                       capture_output=True, cwd=RAIZ, timeout=60,
                       stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise SystemExit("no pude sacar el verificador de HEAD")
    with open(tmp, "wb") as fh:
        fh.write(r.stdout)
    spec = importlib.util.spec_from_file_location("verificador_head", tmp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def disparo(censo):
    """Pares (motor, formato) del censo cuya extension pediria la ventana larga."""
    out = {}
    for nom, d in censo.items():
        n, dispara = 0, []
        for mot, formatos in d.items():
            if not isinstance(formatos, dict):
                continue
            for f in formatos:
                n += 1
                if "." + f.lower() in EXT_CAB_LARGA:
                    dispara.append(mot + ":" + f)
        out[nom] = {"n_destinos": n, "dispara": sorted(dispara),
                    "porcentaje": round(100.0 * len(dispara) / n, 3) if n else 0}
    return out


def main():
    tmp = sys.argv[1]
    ficheros = []
    for base in (os.path.join(RAIZ, "corpus"), tmp):
        for d, _, ns in os.walk(base):
            for n in ns:
                p = os.path.join(d, n)
                try:
                    if os.path.getsize(p) > 0:
                        ficheros.append(p)
                except OSError:
                    pass
    ficheros.sort()
    for _ in range(3):          # calentamiento (trampa 7)
        for p in ficheros:
            leer(p, _NLARGO)

    cpu0 = med(testigo_cpu, 3)
    pr0, tope0 = testigo_proc()
    res = {"n_ficheros": len(ficheros), "n": N,
           "bytes_totales": sum(os.path.getsize(p) for p in ficheros)}

    # ---- A. el primitivo, aislado, y DOS veces para ver el signo
    a = {}
    for vuelta in (1, 2):
        a["vuelta%d" % vuelta] = {
            "read_512_ms": round(med(lambda: tanda(ficheros,
                                                   lambda p: leer(p, _NCORTO))), 4),
            "read_2056_ms": round(med(lambda: tanda(ficheros,
                                                    lambda p: leer(p, _NLARGO))), 4),
        }
        v = a["vuelta%d" % vuelta]
        v["delta_us_por_fichero"] = round(
            (v["read_2056_ms"] - v["read_512_ms"]) * 1000 / len(ficheros), 2)
    a["signo_se_conserva"] = (
        (a["vuelta1"]["delta_us_por_fichero"] > 0)
        == (a["vuelta2"]["delta_us_por_fichero"] > 0))
    res["A_primitivo"] = a

    # ---- B. firma_real entera: HEAD contra arbol, pareado en esta tanda
    H = carga_head()
    from filex import verificador as V
    b = {}
    for vuelta in (1, 2):
        b["vuelta%d" % vuelta] = {
            "head_ms": round(med(lambda: tanda(ficheros, H.firma_real)), 4),
            "arbol_ms": round(med(lambda: tanda(ficheros, V.firma_real)), 4),
        }
        v = b["vuelta%d" % vuelta]
        v["delta_us_por_fichero"] = round(
            (v["arbol_ms"] - v["head_ms"]) * 1000 / len(ficheros), 2)
        v["ratio"] = round(v["arbol_ms"] / v["head_ms"], 3)
    b["signo_se_conserva"] = (
        (b["vuelta1"]["delta_us_por_fichero"] > 0)
        == (b["vuelta2"]["delta_us_por_fichero"] > 0))
    res["B_firma_real"] = b

    # ---- C. cuando se dispararia la puerta
    censo = {}
    for nom in ("firmas_censo_local.json", "firmas_censo_contenedor.json"):
        p = os.path.join(RAIZ, "bench", "salidas-firmas", nom)
        if os.path.exists(p):
            censo[nom] = json.load(open(p, encoding="utf-8"))
    res["C_disparo"] = disparo(censo)

    cpu1 = med(testigo_cpu, 3)
    pr1, tope1 = testigo_proc()
    deriva = cpu1 / cpu0 if cpu0 else 0
    nivel = max(pr0, pr1) / min(pr0, pr1) if min(pr0, pr1) else 0
    res["testigos"] = {"cpu_ms_antes": round(cpu0, 1), "cpu_ms_despues": round(cpu1, 1),
                       "deriva": round(deriva, 3),
                       "proc_ms_antes": round(pr0, 1), "proc_ms_despues": round(pr1, 1),
                       "nivel": round(nivel, 3),
                       "tope_agotado": bool(tope0 or tope1),
                       "etiqueta": "SUCIA" if (abs(deriva - 1) > 0.20 or
                                               abs(nivel - 1) > 0.20 or tope0 or tope1)
                                   else "limpia"}
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

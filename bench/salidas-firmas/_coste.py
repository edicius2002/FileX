# -*- coding: utf-8 -*-
"""F1 / paso 6 - QUE CUESTA EL VOCABULARIO AMPLIADO.

El punto 1 es el mas barato del contrato y tiene que seguir siendolo: si ampliar
el vocabulario lo saca del camino caliente, la ampliacion no compensa. Se mide
`firma_real` viejo frente a nuevo sobre los mismos ficheros, y el contrato completo
en proceso sobre las 53 salidas del patron oro.

AVISO DE COMPARABILIDAD (CLAUDE.md sec.3): con varios agentes en paralelo, los
milisegundos ABSOLUTOS no son comparables entre informes. Las cifras RELATIVAS
dentro de esta tanda si valen. Los dos testigos de ruido van al principio y al
final, con tope propio.

Uso: python _coste.py
Escribe coste.json
"""
import os, sys, json, time, statistics, subprocess

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-firmas")
REF = os.path.join(RAIZ, r"bench\salidas-referencia")
sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
sys.path.insert(0, os.path.join(RAIZ, r"bench\salidas-aristas"))
sys.path.insert(0, os.path.join(RAIZ, r"bench\salidas-verificacion"))
import verificador as V
import verificador_congelado as VC
from trabajos import TABLA

N = 9


def testigo_cpu(n=400000):
    import hashlib
    t = time.perf_counter()
    h = b"x"
    for _ in range(n):
        h = hashlib.sha256(h).digest()
    return (time.perf_counter() - t) * 1000


def testigo_proc(tope=20.0):
    t = time.perf_counter()
    try:
        subprocess.run(["ffprobe", "-v", "quiet", "-version"], capture_output=True,
                       stdin=subprocess.DEVNULL, timeout=tope)
    except Exception:
        return tope * 1000, True
    return (time.perf_counter() - t) * 1000, False


def mide(fn, n=N):
    fn()  # calentamiento (Windows Defender infla el primer arranque)
    return statistics.median([_uno(fn) for _ in range(n)])


def _uno(fn):
    t = time.perf_counter()
    fn()
    return (time.perf_counter() - t) * 1000


if __name__ == "__main__":
    t1a = testigo_cpu()
    t2a, tope = testigo_proc()
    print("testigos ANTES: cpu %.1f ms  proceso %.1f ms" % (t1a, t2a))

    casos = [
        ("png 1920x1080", os.path.join(RAIZ, "corpus", "imagen", "tipico.png")),
        ("jpeg", os.path.join(RAIZ, "corpus", "imagen", "tipico.jpg")),
        ("mp4 16 MB", os.path.join(RAIZ, "corpus", "video", "tipico.mp4")),
        ("pdf", os.path.join(RAIZ, "corpus", "pdf", "tipico_texto.pdf")),
        ("csv (texto)", os.path.join(RAIZ, "corpus", "datos", "tipico.csv")),
        ("flac", os.path.join(RAIZ, "corpus", "audio", "tipico.flac")),
    ]
    res = {"firma": []}
    for etiq, p in casos:
        if not os.path.exists(p):
            continue
        vv = mide(lambda: VC.firma_real(p))
        nn = mide(lambda: V.firma_real(p))
        res["firma"].append({"caso": etiq, "viejo_ms": vv, "nuevo_ms": nn,
                             "factor": nn / vv if vv else None,
                             "firma_vieja": VC.firma_real(p), "firma_nueva": V.firma_real(p)})
        print("  %-16s viejo %.4f ms   nuevo %.4f ms   x%.2f   (%s -> %s)"
              % (etiq, vv, nn, nn / vv if vv else 0, VC.firma_real(p), V.firma_real(p)))

    # el caso caro del vocabulario nuevo: un ZIP (docx/epub), que abre el directorio
    import zipfile, tempfile
    z = os.path.join(tempfile.gettempdir(), "f1_prueba.docx")
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("[Content_Types].xml", "<x/>")
        zf.writestr("word/document.xml", "<w/>" * 500)
    vv = mide(lambda: VC.firma_real(z))
    nn = mide(lambda: V.firma_real(z))
    res["firma"].append({"caso": "docx (ZIP: 2a pasada)", "viejo_ms": vv, "nuevo_ms": nn,
                         "factor": nn / vv, "firma_vieja": VC.firma_real(z),
                         "firma_nueva": V.firma_real(z)})
    print("  %-16s viejo %.4f ms   nuevo %.4f ms   x%.2f   (%s -> %s)"
          % ("docx (ZIP)", vv, nn, nn / vv, VC.firma_real(z), V.firma_real(z)))
    os.remove(z)

    # contrato completo sobre las 53
    def suite(mod):
        for sub, nom, ent, par, esp in TABLA:
            s = os.path.join(REF, sub, nom)
            if os.path.exists(s):
                mod.verificar(s, {"destino": os.path.splitext(nom)[1].lstrip("."),
                                  "params": dict(par)},
                              ent if os.path.exists(ent) else None, motor="proceso")

    sv = statistics.median([_uno(lambda: suite(VC)) for _ in range(5)])
    sn = statistics.median([_uno(lambda: suite(V)) for _ in range(5)])
    res["suite53"] = {"viejo_ms": sv, "nuevo_ms": sn, "factor": sn / sv,
                      "por_salida_viejo_ms": sv / 53, "por_salida_nuevo_ms": sn / 53}
    print("\n  CONTRATO sobre las 53, en proceso: viejo %.1f ms  nuevo %.1f ms  x%.2f"
          % (sv, sn, sn / sv))
    print("    por salida: %.3f ms -> %.3f ms" % (sv / 53, sn / 53))

    t1b = testigo_cpu()
    t2b, tope2 = testigo_proc()
    deriva, nivel = t1b / t1a, max(t2a, t2b) / 26.6
    etiqueta = "limpia" if (0.8 <= deriva <= 1.2 and nivel <= 1.2) else "SUCIA"
    res["testigos"] = {"cpu_antes": t1a, "cpu_despues": t1b, "proc_antes": t2a,
                       "proc_despues": t2b, "deriva": deriva, "nivel": nivel,
                       "etiqueta": etiqueta, "tope_alcanzado": tope or tope2}
    print("\ntestigos DESPUES: cpu %.1f ms  proceso %.1f ms -> deriva x%.2f nivel x%.2f -> %s"
          % (t1b, t2b, deriva, nivel, etiqueta))
    json.dump(res, open(os.path.join(SAL, "coste.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("escrito coste.json")

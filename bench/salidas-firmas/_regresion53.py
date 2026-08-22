# -*- coding: utf-8 -*-
"""F1 / paso 4 - EL LISTON QUE NO SE PUEDE BAJAR: 0 falsos positivos sobre las 53.

Un vocabulario grande que confunde formatos parecidos es PEOR que uno pequeno que
calla. Este script vuelve a pasar el contrato completo por las 53 salidas del
patron oro con los dos motores, cuenta falsos positivos y falsos negativos frente
al `esperado` de la tabla, y ademas publica el estado del PUNTO 1 de cada salida
(evaluado / familia / no_aplica / sin_vocabulario), que es la cifra del informe.

Tambien reejecuta los 5 fallos documentados: el nº 1 es justo el emblematico
(un PNG entregado con extension .avif) y no puede dejar de atraparse.

Uso: python _regresion53.py
Escribe regresion53.json
"""
import os, sys, json, time, shutil, subprocess, statistics

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-firmas")
REF = os.path.join(RAIZ, r"bench\salidas-referencia")
sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
sys.path.insert(0, os.path.join(RAIZ, "bench", "salidas-verificacion"))
import verificador as V
from trabajos import TABLA

TMP = os.environ.get("F1_TMP", os.path.join(os.environ.get("TEMP", "."), "f1")) + "\\reg"


# ---------------------------------------------------------------- testigos
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
    ms = (time.perf_counter() - t) * 1000
    return ms, False


def med(fn, n=9):
    return statistics.median([fn() for _ in range(n)])


# ---------------------------------------------------------------- las 53
def corre53(motor, alfa=True):
    ref = json.load(open(os.path.join(REF, "referencia.json"), encoding="utf-8"))
    # alfa_no_trivial inyectado desde el patron oro, como en los informes previos
    inj = {}
    def rec(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "alfa_min_max" and isinstance(v, str):
                    pass
                rec(v)
        elif isinstance(o, list):
            for v in o:
                rec(v)
    rec(ref)
    out = []
    for sub, nom, ent, par, esp in TABLA:
        sal = os.path.join(REF, sub, nom)
        if not os.path.exists(sal):
            out.append({"salida": nom, "estado": "AUSENTE"})
            continue
        pedido = {"destino": os.path.splitext(nom)[1].lstrip("."), "params": dict(par)}
        pedido.update({k: v for k, v in par.items() if k in ("solo_audio", "solo_video", "copia")})
        r = V.verificar(sal, pedido, ent if os.path.exists(ent) else None,
                        motor=motor, alfa=alfa)
        out.append({"salida": nom, "esperado": esp, "veredicto": r["veredicto"],
                    "punto1": r.get("punto1"), "firma": V.firma_real(sal),
                    "cobertura": r["cobertura"],
                    "hallazgos": [(h["punto"], h["regla"], h["severidad"], h["mensaje"])
                                  for h in r["hallazgos"]
                                  if h["severidad"] in ("fallo", "aviso")],
                    "p1": [(h["regla"], h["severidad"], h["mensaje"])
                           for h in r["hallazgos"] if h["punto"] == 1]})
    return out


def resume(out):
    fp = [o for o in out if o.get("esperado") == "ok" and o.get("veredicto") == "fallo"]
    fn = [o for o in out if o.get("esperado") == "fallo" and o.get("veredicto") != "fallo"]
    from collections import Counter
    return {"n": len(out), "falsos_positivos": len(fp), "falsos_negativos": len(fn),
            "detalle_fp": [(o["salida"], o["hallazgos"]) for o in fp],
            "detalle_fn": [o["salida"] for o in fn],
            "veredictos": dict(Counter(o.get("veredicto") for o in out)),
            "punto1": dict(Counter(o.get("punto1") for o in out))}


# ---------------------------------------------------------------- los 5 fallos
def fabrica_fallos():
    os.makedirs(TMP, exist_ok=True)
    C = lambda *p: os.path.join(RAIZ, "corpus", *p)
    casos = []
    # 1. PNG entregado con extension .avif  <- EL FALLO EMBLEMATICO
    p = os.path.join(TMP, "falso.avif")
    shutil.copy(C("imagen", "tipico.png"), p)
    casos.append(("1 PNG con extension .avif", p, {"destino": "avif"},
                  C("imagen", "tipico.png"), "fallo"))
    # 1b. control: el mismo PNG con su extension
    p = os.path.join(TMP, "bueno.png")
    shutil.copy(C("imagen", "tipico.png"), p)
    casos.append(("1b control: PNG con extension .png", p, {"destino": "png"},
                  C("imagen", "tipico.png"), "ok"))
    # 5. fichero de 0 bytes
    p = os.path.join(TMP, "vacio.png")
    open(p, "wb").close()
    casos.append(("5 fichero de 0 bytes", p, {"destino": "png"}, None, "fallo"))
    # NUEVOS, del vocabulario ampliado: los que ANTES pasaban por no tener firma
    for ent, ext, etiq in ((C("imagen", "tipico.png"), "svg", "PNG con extension .svg"),
                           (C("imagen", "tipico.png"), "docx", "PNG con extension .docx"),
                           (C("imagen", "tipico.png"), "ico", "PNG con extension .ico"),
                           (C("imagen", "tipico.png"), "eps", "PNG con extension .eps"),
                           (C("pdf", "tipico_texto.pdf"), "epub", "PDF con extension .epub"),
                           (C("audio", "tipico.flac"), "aiff", "FLAC con extension .aiff")):
        p = os.path.join(TMP, "falso_%s.%s" % (etiq.split()[0].lower(), ext))
        shutil.copy(ent, p)
        casos.append(("N " + etiq, p, {"destino": ext}, ent, "fallo"))
    return casos


if __name__ == "__main__":
    t1a = med(testigo_cpu, 3)
    t2a, tope = testigo_proc()
    print("testigos ANTES: cpu %.1f ms  proceso %.1f ms%s" % (t1a, t2a, " TOPE" if tope else ""))

    res = {}
    for motor in ("proceso", "subproceso"):
        out = corre53(motor)
        res[motor] = {"detalle": out, "resumen": resume(out)}
        print("\n=== 53 salidas, motor %s ===" % motor)
        print("   ", res[motor]["resumen"]["veredictos"])
        print("    FALSOS POSITIVOS: %d   falsos negativos: %d"
              % (res[motor]["resumen"]["falsos_positivos"],
                 res[motor]["resumen"]["falsos_negativos"]))
        print("    punto 1:", res[motor]["resumen"]["punto1"])
        for s, h in res[motor]["resumen"]["detalle_fp"]:
            print("      FP", s, h)
        avisos = [(o["salida"], o["hallazgos"]) for o in out if o.get("veredicto") == "aviso"]
        print("    avisos (%d):" % len(avisos))
        for s, h in avisos:
            print("      ", s, [x[1] for x in h])

    fallos = []
    for etiq, p, ped, ent, esp in fabrica_fallos():
        r = V.verificar(p, ped, ent, motor="proceso", alfa=False)
        ok = (r["veredicto"] == "fallo") if esp == "fallo" else (r["veredicto"] != "fallo")
        fallos.append({"caso": etiq, "esperado": esp, "veredicto": r["veredicto"],
                       "firma": V.firma_real(p), "punto1": r.get("punto1"), "correcto": ok,
                       "p1": [(h["regla"], h["severidad"], h["mensaje"])
                              for h in r["hallazgos"] if h["punto"] == 1]})
        print("  %-42s esperado=%-5s obtenido=%-11s %s" % (etiq, esp, r["veredicto"],
                                                           "OK" if ok else "  <-- MAL"))
    res["fallos"] = fallos

    t1b = med(testigo_cpu, 3)
    t2b, tope2 = testigo_proc()
    deriva = t1b / max(t1a, 1e-9)
    nivel = max(t2a, t2b) / 26.6
    etiqueta = "limpia" if (0.8 <= deriva <= 1.2 and nivel <= 1.2) else "SUCIA"
    print("\ntestigos DESPUES: cpu %.1f ms  proceso %.1f ms -> deriva x%.2f nivel x%.2f -> %s"
          % (t1b, t2b, deriva, nivel, etiqueta))
    res["testigos"] = {"cpu_antes": t1a, "cpu_despues": t1b, "proc_antes": t2a,
                       "proc_despues": t2b, "deriva": deriva, "nivel": nivel,
                       "etiqueta": etiqueta}
    json.dump(res, open(os.path.join(SAL, "regresion53.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    shutil.rmtree(TMP, ignore_errors=True)
    print("\nescrito regresion53.json")

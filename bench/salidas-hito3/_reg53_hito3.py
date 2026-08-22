# -*- coding: utf-8 -*-
"""K2 / hito 3 - LA PRUEBA DE QUE LA MUDANZA NO CAMBIA NADA.

Corre el contrato de cinco puntos sobre las 53 salidas del patron oro y sobre
los 9 fallos fabricados, con los DOS motores de sondeo, y vuelca un JSON
DETERMINISTA (sin un solo milisegundo dentro) para poder compararlo byte a byte
antes y despues de mudar el verificador a `filex/`.

    python _reg53_hito3.py --fuente bench   -> reg53_antes.json
    python _reg53_hito3.py --fuente filex   -> reg53_despues.json

`--fuente bench` importa `verificador` metiendo `bench/scripts` en sys.path,
que es EXACTAMENTE lo que hacen los 16 arneses de bench/.
`--fuente filex` hace `from filex import verificador`, que es lo que hara el
nucleo.

Deriva de bench/salidas-firmas/_regresion53.py (F1). No lo toca ni lo importa:
copiado a mi directorio de salidas, como manda CLAUDE.md.
"""
import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from collections import Counter

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SAL = os.path.join(RAIZ, "bench", "salidas-hito3")
REF = os.path.join(RAIZ, "bench", "salidas-referencia")

sys.path.insert(0, os.path.join(RAIZ, "bench", "salidas-verificacion"))
from trabajos import TABLA  # noqa: E402

TMP = os.path.join(os.environ.get("TEMP", "."), "k2_hito3", "reg")


def carga(fuente):
    """Devuelve el modulo del verificador por la via que toque."""
    if fuente == "bench":
        sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
        import verificador as V
        return V
    if fuente == "filex":
        sys.path.insert(0, RAIZ)
        from filex import verificador as V
        return V
    raise SystemExit("fuente desconocida: %s" % fuente)


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
    return (time.perf_counter() - t) * 1000, False


def med(fn, n=3):
    return statistics.median([fn() for _ in range(n)])


# ---------------------------------------------------------------- las 53
def corre53(V, motor, alfa=True):
    out = []
    for sub, nom, ent, par, esp in TABLA:
        sal = os.path.join(REF, sub, nom)
        if not os.path.exists(sal):
            out.append({"salida": nom, "estado": "AUSENTE"})
            continue
        pedido = {"destino": os.path.splitext(nom)[1].lstrip("."), "params": dict(par)}
        pedido.update({k: v for k, v in par.items()
                       if k in ("solo_audio", "solo_video", "copia")})
        r = V.verificar(sal, pedido, ent if os.path.exists(ent) else None,
                        motor=motor, alfa=alfa)
        out.append({
            "salida": nom,
            "esperado": esp,
            "veredicto": r["veredicto"],
            "punto1": r.get("punto1"),
            "firma": V.firma_real(sal),
            "cobertura": r["cobertura"],
            # TODOS los hallazgos, no solo fallo/aviso: si la mudanza cambiase
            # una severidad de 'info' a 'aviso' quiero verlo.
            "hallazgos": [(h["punto"], h["regla"], h["severidad"], h["mensaje"],
                           h.get("esperado"), h.get("obtenido"))
                          for h in r["hallazgos"]],
        })
    return out


def resume(out):
    fp = [o for o in out if o.get("esperado") == "ok" and o.get("veredicto") == "fallo"]
    fn = [o for o in out if o.get("esperado") == "fallo" and o.get("veredicto") != "fallo"]
    return {"n": len(out), "falsos_positivos": len(fp), "falsos_negativos": len(fn),
            "detalle_fp": [o["salida"] for o in fp],
            "detalle_fn": [o["salida"] for o in fn],
            "veredictos": dict(Counter(o.get("veredicto") for o in out)),
            "punto1": dict(Counter(o.get("punto1") for o in out))}


# ---------------------------------------------------------------- los fallos
def fabrica_fallos():
    shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(TMP, exist_ok=True)
    C = lambda *p: os.path.join(RAIZ, "corpus", *p)
    casos = []
    p = os.path.join(TMP, "falso.avif")
    shutil.copy(C("imagen", "tipico.png"), p)
    casos.append(("1 PNG con extension .avif", p, {"destino": "avif"},
                  C("imagen", "tipico.png"), "fallo"))
    p = os.path.join(TMP, "bueno.png")
    shutil.copy(C("imagen", "tipico.png"), p)
    casos.append(("1b control: PNG con extension .png", p, {"destino": "png"},
                  C("imagen", "tipico.png"), "ok"))
    p = os.path.join(TMP, "vacio.png")
    open(p, "wb").close()
    casos.append(("5 fichero de 0 bytes", p, {"destino": "png"}, None, "fallo"))
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


# ------------------------------------------------- el punto 5, con censo real
def corre_punto5(V):
    """El punto 5 NO se ejerce en las 53: no hay censo. Aqui si.

    Dos casos minimos y deterministas: un motor limpio (solo escribe la salida)
    y un motor sucio (deja un sobrante en el cwd, el caso `ffmpeg .mpd`).
    """
    d = os.path.join(TMP, "p5")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)
    sal = os.path.join(d, "s.png")
    shutil.copy(os.path.join(RAIZ, "corpus", "imagen", "tipico.png"), sal)
    antes = V.censar([d])
    limpio = V.censar([d])
    r_limpio = V.verificar(sal, {"destino": "png"}, None, motor="proceso",
                           censo={"antes": antes, "despues": limpio})
    with open(os.path.join(d, "sobrante.dat"), "wb") as fh:
        fh.write(b"x" * 1024)
    sucio = V.censar([d])
    r_sucio = V.verificar(sal, {"destino": "png"}, None, motor="proceso",
                          censo={"antes": antes, "despues": sucio})
    fmt = lambda r: {"veredicto": r["veredicto"], "cobertura": r["cobertura"],
                     "hallazgos": [(h["punto"], h["regla"], h["severidad"])
                                   for h in r["hallazgos"]]}
    return {"limpio": fmt(r_limpio), "sucio": fmt(r_sucio)}


# --------------------------------------------------------------- fidelidad
def corre_fidelidad(V):
    """Grupo C sobre las 53, sin V2 (que decodifica el video entero)."""
    V.v2(False)
    out = []
    for sub, nom, ent, par, esp in TABLA:
        sal = os.path.join(REF, sub, nom)
        if not os.path.exists(sal) or not os.path.exists(ent):
            out.append({"salida": nom, "estado": "AUSENTE"})
            continue
        pedido = {"destino": os.path.splitext(nom)[1].lstrip("."), "params": dict(par)}
        pedido.update({k: v for k, v in par.items()
                       if k in ("solo_audio", "solo_video", "copia")})
        try:
            r = V.verificar_fidelidad(sal, pedido, ent)
        except Exception as e:
            out.append({"salida": nom, "estado": "EXCEPCION", "error": repr(e)})
            continue
        out.append({"salida": nom, "veredicto": r["veredicto"],
                    "cobertura": r["cobertura"],
                    "hallazgos": [(h["regla"], h["severidad"], h["mensaje"])
                                  for h in r["hallazgos"]]})
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fuente", choices=["bench", "filex"], required=True)
    ap.add_argument("--salida-json", default=None)
    ap.add_argument("--con-fidelidad", action="store_true")
    a = ap.parse_args()

    V = carga(a.fuente)
    origen_real = getattr(V, "__file__", "?")
    print("modulo cargado: %s  (%s)" % (V.__name__, origen_real))

    t1a = med(testigo_cpu)
    t2a, tope = testigo_proc()
    print("testigos ANTES: cpu %.1f ms  proceso %.1f ms%s"
          % (t1a, t2a, " TOPE" if tope else ""))

    t_ini = time.perf_counter()
    res = {"fuente": a.fuente, "modulo": V.__name__, "fichero": origen_real}
    for motor in ("proceso", "subproceso"):
        out = corre53(V, motor)
        res[motor] = {"detalle": out, "resumen": resume(out)}
        print("=== 53, motor %s === %s  FP=%d FN=%d"
              % (motor, res[motor]["resumen"]["veredictos"],
                 res[motor]["resumen"]["falsos_positivos"],
                 res[motor]["resumen"]["falsos_negativos"]))

    fallos = []
    for etiq, p, ped, ent, esp in fabrica_fallos():
        r = V.verificar(p, ped, ent, motor="proceso", alfa=False)
        ok = (r["veredicto"] == "fallo") if esp == "fallo" else (r["veredicto"] != "fallo")
        fallos.append({"caso": etiq, "esperado": esp, "veredicto": r["veredicto"],
                       "firma": V.firma_real(p), "punto1": r.get("punto1"),
                       "correcto": ok,
                       "p1": [(h["regla"], h["severidad"], h["mensaje"])
                              for h in r["hallazgos"] if h["punto"] == 1]})
    res["fallos"] = fallos
    print("fallos fabricados: %d/%d correctos"
          % (sum(1 for f in fallos if f["correcto"]), len(fallos)))

    res["punto5"] = corre_punto5(V)
    print("punto 5: limpio=%s sucio=%s"
          % (res["punto5"]["limpio"]["veredicto"], res["punto5"]["sucio"]["veredicto"]))

    if a.con_fidelidad:
        res["fidelidad"] = corre_fidelidad(V)
        print("fidelidad: %s"
              % dict(Counter(o.get("veredicto") or o.get("estado")
                             for o in res["fidelidad"])))

    ms_total = (time.perf_counter() - t_ini) * 1000
    t1b = med(testigo_cpu)
    t2b, tope2 = testigo_proc()
    deriva = t1b / max(t1a, 1e-9)
    nivel = max(t2a, t2b) / 26.6
    etiqueta = "limpia" if (0.8 <= deriva <= 1.2 and nivel <= 1.2) else "SUCIA"
    print("testigos DESPUES: cpu %.1f ms proceso %.1f ms -> deriva x%.2f nivel x%.2f -> %s"
          % (t1b, t2b, deriva, nivel, etiqueta))
    print("total tanda: %.0f ms" % ms_total)

    # Los tiempos van APARTE del bloque comparable, para que el diff sea limpio.
    testigos = {"cpu_antes": t1a, "cpu_despues": t1b, "proc_antes": t2a,
                "proc_despues": t2b, "deriva": deriva, "nivel": nivel,
                "etiqueta": etiqueta, "ms_total": ms_total}

    nom = a.salida_json or ("reg53_%s.json" % ("antes" if a.fuente == "bench" else "despues"))
    with open(os.path.join(SAL, nom), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False, sort_keys=True)
    with open(os.path.join(SAL, nom.replace(".json", "_testigos.json")), "w",
              encoding="utf-8") as fh:
        json.dump(testigos, fh, indent=1, ensure_ascii=False)
    shutil.rmtree(TMP, ignore_errors=True)
    print("escrito %s" % nom)

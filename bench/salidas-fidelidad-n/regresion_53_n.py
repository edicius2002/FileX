#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA RESTRICCION QUE MANDA: cero falsos positivos sobre las 53 del patron oro.

Pasa las 53 salidas por el CONTRATO y por la FIDELIDAD, con el verificador de
HEAD (`--antes`) o el del arbol de trabajo, y compara veredicto a veredicto.
`bench/salidas-referencia/referencia.json` se LEE y no se toca.

  python bench/salidas-contrato-v/regresion_53.py --antes
  python bench/salidas-contrato-v/regresion_53.py
  python bench/salidas-contrato-v/regresion_53.py --diff
"""
import json
import os
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "bench", "salidas-verificacion"))

from trabajos import trabajos  # noqa: E402

# Las tres salidas producidas con `-c copy`, deducidas de referencia.json ->
# ordenes. Igual que en bench/salidas-verificacion-fidelidad/medir_fid.py.
COPIA = {"2pistas_mkv-to-COPY.mp4", "tipico_mp4-to.mkv", "tipico_mp4-audio-copy.m4a"}


def cargar_verificador(antes):
    if not antes:
        from filex import verificador as V
        return V, "despues"
    import importlib.util
    tmp = os.path.join(tempfile.gettempdir(), "filex_verificador_head.py")
    with open(tmp, "wb") as fh:
        fh.write(subprocess.run(["git", "show", "HEAD:filex/verificador.py"],
                                capture_output=True, cwd=RAIZ, timeout=60).stdout)
    spec = importlib.util.spec_from_file_location("verificador_head", tmp)
    V = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(V)
    return V, "antes"


# N18 — VARIANTE del arnes compartido `bench/salidas-contrato-v/regresion_53.py`,
# copiada a mi directorio de salidas como manda CLAUDE.md §1. El unico cambio de
# fondo es este: en un worktree limpio `bench/salidas-referencia/` solo trae
# `MANIFIESTO.md`, `referencia.json` y `logs/` —las 53 son binarios regenerables
# y no se versionan (§6)—, asi que hay que decirle DONDE estan las regeneradas.
# `bench/salidas-firmas-cierre/_regenera53.py` las deja en el scratchpad; esta
# variable las localiza sin tocar `bench/salidas-referencia/`, que se lee y no se
# escribe.
REF53 = os.environ.get("FILEX_REF53") or ""
REF_REPO = os.path.join(RAIZ, "bench", "salidas-referencia")


def _resitúa(ruta):
    if REF53 and ruta.startswith(REF_REPO):
        return os.path.join(REF53, os.path.relpath(ruta, REF_REPO))
    return ruta


def trabajos_fid():
    out = []
    for t in trabajos():
        t = dict(t)
        t["pedido"] = dict(t["pedido"])
        t["pedido"]["params"] = dict(t["pedido"]["params"])
        t["salida"] = _resitúa(t["salida"])
        t["entrada"] = _resitúa(t["entrada"])
        if os.path.basename(t["salida"]) in COPIA:
            t["pedido"]["params"]["copia"] = True
        out.append(t)
    return out


def main():
    if "--diff" in sys.argv:
        return diff()
    V, sufijo = cargar_verificador("--antes" in sys.argv)
    # censo vacio: el punto 5 queda CUBIERTO y sin hallazgos, que es como corre
    # dentro de una conversion real. Sin el, las 53 salen `ok_parcial` por el
    # punto 5 y ninguna diferencia de los otros cuatro se puede ver.
    censo = {"antes": {}, "despues": {}}
    filas = []
    t0g = time.perf_counter()
    for t in trabajos_fid():
        se = V.sondear(t["entrada"])
        se.update(t["extra_entrada"])
        c = V.verificar(t["salida"], t["pedido"], t["entrada"], sonda_ent=se,
                        censo=censo)
        f = V.verificar_fidelidad(t["salida"], t["pedido"], t["entrada"])
        filas.append({
            "salida": os.path.basename(t["salida"]), "cat": t["cat"],
            "esperado": t["esperado"],
            "contrato": c["veredicto"], "punto1": c["punto1"],
            "contrato_sin_cubrir": sorted(k for k, v in c["cobertura"].items() if not v),
            "contrato_reglas": sorted({h["regla"] for h in c["hallazgos"]
                                       if h["severidad"] in ("fallo", "aviso")}),
            "fidelidad": f["veredicto"],
            "fidelidad_cobertura": {k: v for k, v in sorted(f["cobertura"].items())},
            "fidelidad_reglas": sorted({h["regla"] for h in f["hallazgos"]
                                        if h["severidad"] in ("fallo", "aviso")}),
        })
        print("%-38s contrato=%-11s p1=%-9s fid=%-11s %s"
              % (filas[-1]["salida"], c["veredicto"], c["punto1"], f["veredicto"],
                 filas[-1]["contrato_reglas"] + filas[-1]["fidelidad_reglas"]))
    total = (time.perf_counter() - t0g) * 1000
    fp = [f for f in filas
          if (f["contrato"] == "fallo" or f["fidelidad"] == "fallo")
          and f["esperado"] != "fallo"]
    fn = [f for f in filas
          if f["contrato"] != "fallo" and f["esperado"] == "fallo"]
    res = {"n": len(filas), "total_ms": round(total, 1),
           "falsos_positivos": [f["salida"] for f in fp],
           "falsos_negativos": [f["salida"] for f in fn],
           "contrato": {v: sum(1 for f in filas if f["contrato"] == v)
                        for v in ("ok", "aviso", "ok_parcial", "fallo")},
           "fidelidad": {v: sum(1 for f in filas if f["fidelidad"] == v)
                         for v in ("ok", "aviso", "ok_parcial", "fallo")},
           "filas": filas}
    with open(os.path.join(AQUI, "regresion_%s.json" % sufijo), "w",
              encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    print("\n[%s] %d salidas en %.0f ms | FALSOS POSITIVOS %d %s | falsos negativos %d"
          % (sufijo, len(filas), total, len(fp), [f["salida"] for f in fp], len(fn)))
    print("  contrato  %s" % res["contrato"])
    print("  fidelidad %s" % res["fidelidad"])
    print("-> regresion_%s.json" % sufijo)


def diff():
    a = json.load(open(os.path.join(AQUI, "regresion_antes.json"), encoding="utf-8"))
    b = json.load(open(os.path.join(AQUI, "regresion_despues.json"), encoding="utf-8"))
    ia = {f["salida"]: f for f in a["filas"]}
    n = 0
    for f in b["filas"]:
        g = ia.get(f["salida"])
        if not g:
            continue
        cambios = [k for k in ("contrato", "punto1", "fidelidad",
                               "contrato_reglas", "fidelidad_reglas")
                   if f[k] != g[k]]
        if cambios:
            n += 1
            print("%-38s" % f["salida"])
            for k in cambios:
                print("    %-18s %s  ->  %s" % (k, g[k], f[k]))
    print("\n%d de %d salidas cambian de veredicto o de reglas." % (n, len(b["filas"])))
    print("FALSOS POSITIVOS: antes %s  despues %s"
          % (a["falsos_positivos"], b["falsos_positivos"]))


if __name__ == "__main__":
    main()

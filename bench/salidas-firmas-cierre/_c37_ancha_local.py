"""C37 / paso 4 - LA PRUEBA ANCHA LOCAL, ANTES Y DESPUES, sobre las MISMAS salidas.

La restriccion que manda es «cero falsos positivos». Las 53 del patron oro son
el liston corto (tocan 17 extensiones); el ancho son los 385 destinos que
`ffmpeg`, `imagemagick` y `ghostscript` saben escribir en esta maquina.

DOS DECISIONES DE ARNES, y las dos son para no medir el arnes en vez del cambio:

 1. **Las salidas se escriben UNA VEZ y se evaluan DOS.** Reescribirlas para el
    «despues» meteria la varianza del motor dentro de la comparacion, y algunos
    de estos formatos no son deterministas (`/CreationDate` de ImageMagick,
    trampa 22). Con el mismo byte a byte, toda diferencia es del verificador.
 2. **El «antes» es el `verificador.py` de HEAD**, cargado con `git show`, no una
    cifra copiada de otro informe (trampa 59): las dos versiones corren en esta
    tanda y sobre estos ficheros.

Uso:  python bench/salidas-firmas-cierre/_c37_ancha_local.py <dir_desechable>
"""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIRMAS_F1 = os.path.join(RAIZ, "bench", "salidas-firmas")
sys.path.insert(0, RAIZ)
sys.path.insert(0, FIRMAS_F1)


def carga_head():
    """El `verificador.py` de HEAD, para el lado «antes» de la comparacion."""
    tmp = os.path.join(tempfile.gettempdir(), "f2_verificador_head.py")
    r = subprocess.run(["git", "show", "HEAD:filex/verificador.py"],
                       capture_output=True, cwd=RAIZ, timeout=60,
                       stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise SystemExit("no pude sacar el verificador de HEAD: %r" % r.stderr[:200])
    with open(tmp, "wb") as fh:
        fh.write(r.stdout)
    spec = importlib.util.spec_from_file_location("verificador_head", tmp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def escribe_todo(tmp):
    """Escribe cada destino local una vez. Devuelve [(motor, formato, mod, ruta)]."""
    os.environ.setdefault("F1_TMP", os.path.join(tmp, "pool"))
    import _censo_firmas as C
    F = json.load(open(os.path.join(FIRMAS_F1, "formatos.json"), encoding="utf-8"))
    pa = F["por_adaptador"]
    sem = C.semillas()
    trabajos = ([("ffmpeg", b, ["video", "audio", "imagen", "subtitulo"])
                 for b in sorted(set(pa["ffmpeg"]["to"]))] +
                [("imagemagick", b, ["imagen"])
                 for b in sorted(set(pa["imagemagick"]["to"]))])
    salidas, fallos = [], []
    for k, (motor, b, mods) in enumerate(trabajos):
        for mod in mods:
            if mod not in sem:
                continue
            sub = os.path.join(tmp, "w%04d" % k)
            C.limpia(sub)
            antes = set(os.listdir(sub))
            sal = os.path.join(sub, "v%d.%s" % (k, b))
            ent = sem[mod][0]
            rc, err, tam, cabec = C.escribe(motor, ent, b, sal, sub)
            despues = set(os.listdir(sub))
            if rc != 0 or not cabec:
                fallos.append({"motor": motor, "formato": b, "modalidad": mod,
                               "rc": rc, "err": err[-160:]})
                continue
            reales = sorted(f for f in despues
                            if os.path.isfile(os.path.join(sub, f)))
            salidas.append({"motor": motor, "formato": b, "modalidad": mod,
                            "ruta": os.path.join(sub, reales[0]),
                            "entrada": ent, "bytes": tam, "rc": rc,
                            "satelites": sorted(despues - antes - {reales[0]})})
            break
    return salidas, fallos


def evalua(V, salidas):
    filas = []
    for s in salidas:
        try:
            son = V.sondear(s["ruta"], "proceso")
        except Exception as e:
            son = {"firma": V.firma_real(s["ruta"]), "bytes": s["bytes"],
                   "error": type(e).__name__ + ": " + str(e)[:120]}
        son_ent = {"ruta": s["entrada"], "firma": V.firma_real(s["entrada"])}
        h = V.punto1_firma(s["ruta"], son, {"destino": s["formato"], "rc": 0}, son_ent)
        filas.append({
            "motor": s["motor"], "formato": s["formato"], "modalidad": s["modalidad"],
            "firma": V.firma_real(s["ruta"]),
            "punto1": V.punto1_estado(s["ruta"]),
            "reglas": [(x["regla"], x["severidad"]) for x in h],
            "fallo": any(x["severidad"] == "fallo" for x in h),
            "g6": any(x["regla"] == "G6" for x in h),
        })
    return filas


def resumen(filas):
    return {
        "n": len(filas),
        "falsos_positivos": [f["formato"] for f in filas if f["fallo"]],
        "g6": [f["formato"] for f in filas if f["g6"]],
        "cobertura": dict(Counter(f["punto1"] for f in filas)),
    }


def main():
    tmp = sys.argv[1]
    os.makedirs(tmp, exist_ok=True)
    salidas, fallos = escribe_todo(tmp)
    antes = evalua(carga_head(), salidas)
    from filex import verificador as V
    despues = evalua(V, salidas)
    ia = {(f["motor"], f["formato"]): f for f in antes}
    cambios = []
    for f in despues:
        g = ia.get((f["motor"], f["formato"]))
        if not g:
            continue
        difs = [k for k in ("firma", "punto1", "reglas", "fallo", "g6")
                if f[k] != g[k]]
        if difs:
            cambios.append({"motor": f["motor"], "formato": f["formato"],
                            "cambia": {k: [g[k], f[k]] for k in difs}})
    with open(os.path.join(RAIZ, "filex", "verificador.py"), "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()[:16]
    res = {"sha256_verificador_despues": sha,
           "escritos": len(salidas), "no_escribibles": len(fallos),
           "satelites": [(s["motor"], s["formato"], s["satelites"])
                         for s in salidas if s["satelites"]],
           "antes": resumen(antes), "despues": resumen(despues),
           "cambios": cambios,
           "no_escritos": fallos,
           "filas_despues": despues}
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

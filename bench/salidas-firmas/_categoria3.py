# -*- coding: utf-8 -*-
"""F1 / paso 7 - LA PREGUNTA DE DISENO: si el punto 1 no aplica, ¿basta con 2-5?

Dos experimentos:

A) LOS 22 DESTINOS EN LOS QUE EL MOTOR ESCRIBE OTRA COSA. `magick x.png y.group4`
   devuelve rc=0 y entrega un PNG. Es el fallo emblematico del proyecto — un fichero
   con la extension equivocada y estado "Done" — reproducido con un motor real y con
   22 destinos distintos. Se pasa el contrato entero, con el vocabulario viejo y con
   el nuevo, y se cuenta que puntos disparan.

B) EL PUNTO CIEGO DE LA CATEGORIA 3. Un `.rgb` es pixeles crudos sin cabecera: el
   punto 1 no aplica porque no hay marcador. CLAUDE.md trampa 23 mide que releerlo
   con `-depth 8` en este ImageMagick Q16-HDRI entrega LA GEOMETRIA EXACTA PEDIDA y
   PIXELES BASURA, y pasa los cuatro puntos. Aqui se reproduce con el verificador
   ampliado para ver si algo cambia — y para medir cuanta cobertura le queda al
   contrato cuando el punto 1 se declara "no aplica".

Uso: python _categoria3.py
Escribe categoria3.json
"""
import os, sys, json, time, shutil, subprocess

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-firmas")
CORPUS = os.path.join(RAIZ, "corpus")
BASE = os.environ.get("F1_TMP") or os.path.join(os.environ.get("TEMP", "."), "f1")
TMP = os.path.join(BASE, "cat3")
sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
sys.path.insert(0, os.path.join(RAIZ, r"bench\salidas-aristas"))
import verificador as V
import verificador_congelado as VC

DESTINOS_PNG = ("b c g k m o r y p7 preview clipboard data flif group4 histogram "
                "inline msl mvg null pocketmod sparse vid").split()


def corre(args, timeout=30, cwd=None):
    try:
        p = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=timeout, errors="replace", cwd=cwd)
        return p.returncode, (p.stderr or "")[-200:]
    except Exception as e:
        return -9, str(e)[:150]


def limpia(d):
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)


def contrato(mod, sal, pedido, ent):
    try:
        r = mod.verificar(sal, pedido, ent, motor="proceso")
    except Exception as e:
        return {"veredicto": "EXCEPCION", "err": str(e)[:120]}
    return {"veredicto": r["veredicto"],
            "cobertura": r["cobertura"],
            "punto1": r.get("punto1"),
            "hallazgos": [(h["punto"], h["regla"], h["severidad"], h["mensaje"][:90])
                          for h in r["hallazgos"]]}


def experimento_a():
    limpia(TMP)
    ent = os.path.join(CORPUS, "imagen", "tipico.png")
    res = []
    for b in DESTINOS_PNG:
        sal = os.path.join(TMP, "z." + b)
        rc, err = corre(["magick", ent, "-auto-orient", sal], 40, TMP)
        cands = [x for x in os.listdir(TMP) if x.startswith("z.")]
        if rc != 0 or not cands:
            res.append({"destino": b, "rc": rc, "estado": "no_escrito", "err": err})
            for c in cands:
                os.remove(os.path.join(TMP, c))
            continue
        real = os.path.join(TMP, sorted(cands)[0])
        ped = {"destino": b, "rc": 0, "params": {}}
        fila = {"destino": b, "rc": rc, "bytes": os.path.getsize(real),
                "firma_vieja": VC.firma_real(real), "firma_nueva": V.firma_real(real),
                "viejo": contrato(VC, real, dict(ped), ent),
                "nuevo": contrato(V, real, dict(ped), ent)}
        res.append(fila)
        for c in cands:
            try:
                os.remove(os.path.join(TMP, c))
            except OSError:
                pass
    return res


def experimento_b():
    limpia(TMP)
    ent = os.path.join(CORPUS, "imagen", "tipico.png")
    # se reduce a 64x48 para que el crudo sea manejable, como en invocacion-aristas
    peq = os.path.join(TMP, "p.png")
    corre(["magick", ent, "-resize", "64x48!", peq], 40, TMP)
    crudo = os.path.join(TMP, "p.rgb")
    corre(["magick", peq, crudo], 40, TMP)
    tam = os.path.getsize(crudo)
    bpp = tam / (64 * 48)
    res = {"bytes_crudo": tam, "bytes_por_pixel": bpp,
           "profundidad_derivada": int(round(bpp / 3 * 8))}
    salidas = {}
    for etiq, depth in (("depth8_MAL", "8"), ("depth16_derivada", "16")):
        sal = os.path.join(TMP, "r_%s.png" % etiq)
        rc, err = corre(["magick", "-size", "64x48", "-depth", depth, crudo, sal], 40, TMP)
        # A 8 bits el crudo de 16 da DOS fotogramas de 64x48 y magick escribe
        # r_..-0.png y r_..-1.png: el nombre exacto NO existe. Es la otra mitad de
        # la trampa 23 y hay que contarla.
        import glob as _g
        cands = sorted(_g.glob(os.path.join(TMP, "r_%s*.png" % etiq)))
        if rc != 0 or not cands:
            salidas[etiq] = {"rc": rc, "err": err, "ficheros": 0}
            continue
        sal = cands[0]
        ped = {"destino": "png", "rc": 0, "params": {"ancho": 64, "alto": 48}}
        # RMSE frente al PNG original de 64x48: la unica sonda que ve la basura
        rc2, o2 = corre(["magick", "compare", "-metric", "RMSE", peq, sal, "null:"], 60, TMP)
        salidas[etiq] = {"rc": rc, "rmse": (o2 or "").strip()[:40],
                         "ficheros": len(cands), "nombre": os.path.basename(sal),
                         "viejo": contrato(VC, sal, dict(ped), peq),
                         "nuevo": contrato(V, sal, dict(ped), peq)}
    res["releer"] = salidas
    # y el contrato sobre el propio .rgb: aqui es donde el punto 1 NO APLICA
    ped = {"destino": "rgb", "rc": 0, "params": {}}
    res["sobre_el_crudo"] = {"firma_vieja": VC.firma_real(crudo),
                             "firma_nueva": V.firma_real(crudo),
                             "viejo": contrato(VC, crudo, dict(ped), peq),
                             "nuevo": contrato(V, crudo, dict(ped), peq)}
    return res


if __name__ == "__main__":
    a = experimento_a()
    print("=== A. 22 destinos en los que `magick` escribe OTRA COSA ===")
    ok_v = ok_n = 0
    for f in a:
        if f.get("estado") == "no_escrito":
            print("  %-11s NO ESCRITO (rc=%s)" % (f["destino"], f["rc"]))
            continue
        fv = any(h[2] == "fallo" for h in f["viejo"].get("hallazgos", []))
        fn = any(h[2] == "fallo" for h in f["nuevo"].get("hallazgos", []))
        ok_v += fv
        ok_n += fn
        print("  %-11s firma=%-6s  viejo=%-11s nuevo=%-11s p1=%-15s %s"
              % (f["destino"], f["firma_nueva"], f["viejo"]["veredicto"],
                 f["nuevo"]["veredicto"], f["nuevo"].get("punto1"),
                 "ATRAPADO" if fn else ""))
    escritos = [f for f in a if f.get("estado") != "no_escrito"]
    print("\n  escritos: %d   atrapa el VIEJO: %d   atrapa el NUEVO: %d"
          % (len(escritos), ok_v, ok_n))

    b = experimento_b()
    print("\n=== B. el punto ciego de la categoria 3 (crudo sin cabecera) ===")
    print("  .rgb de 64x48: %d B = %.2f bytes/pixel -> profundidad %d bits"
          % (b["bytes_crudo"], b["bytes_por_pixel"], b["profundidad_derivada"]))
    for k, v in b["releer"].items():
        if "viejo" not in v:
            print("  %-18s rc=%s %s" % (k, v.get("rc"), v.get("err", "")[:60]))
            continue
        print("  %-18s %d fichero(s) %-22s RMSE=%-22s contrato VIEJO=%-11s NUEVO=%-11s"
              % (k, v["ficheros"], v["nombre"], v["rmse"], v["viejo"]["veredicto"],
                 v["nuevo"]["veredicto"]))
        for h in v["nuevo"]["hallazgos"]:
            print("        ", h)
    c = b["sobre_el_crudo"]
    print("  contrato SOBRE EL .rgb: firma %s -> %s ; veredicto %s -> %s ; punto1=%s"
          % (c["firma_vieja"], c["firma_nueva"], c["viejo"]["veredicto"],
             c["nuevo"]["veredicto"], c["nuevo"].get("punto1")))
    for h in c["nuevo"]["hallazgos"]:
        print("        ", h)
    print("   cobertura viejo:", c["viejo"].get("cobertura"))
    print("   cobertura nuevo:", c["nuevo"].get("cobertura"))

    json.dump({"A": a, "B": b}, open(os.path.join(SAL, "categoria3.json"), "w",
                                     encoding="utf-8"), indent=1, ensure_ascii=False)
    shutil.rmtree(TMP, ignore_errors=True)
    print("\nescrito categoria3.json")

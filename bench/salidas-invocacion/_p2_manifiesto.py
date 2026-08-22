# -*- coding: utf-8 -*-
"""P2 - genera MANIFIESTO.md y poda lo regenerable (CLAUDE.md sec.6)."""
import os, sys, json, hashlib, shutil, time

SAL = os.path.dirname(os.path.abspath(__file__))

BORRAR_DIR = ["pool", "pool2", "pool3", "sem_c17", "tmp_in", "tmp_in2", "tmp_out",
              "tmp_out2", "tmp_res", "tmp_res2", "tmp_crudos", "tmp_val", "tmp_val2",
              "tmp_vbn", "tmp_c17", "tmp_dens", "__pycache__"]
BORRAR_FIC = ["aristas.json", "marco.json"]
# de c13/ solo se conserva el texto
C13_CONSERVA = (".tsv", ".txt", ".sh", ".json", ".log")

ORDEN = {
    "censo.json": "python _p2_censo.py",
    "agregado.json": "python _p2_agrega.py",
    "aristas.json": "python _p2_censo.py   (5,8 MB, BORRADO)",
    "marco.json": "python _p2_agrega.py   (0,9 MB, BORRADO)",
    "inventario_e1.json": "python _extrae.py",
    "pool_indice.json": "python _p2_semillas.py   (regenera pool/, 225 MB, BORRADO)",
    "semi_in_p2.json": "python _p2_semi_in.py",
    "semi_in_p2b.json": "python _p2_semi_in2.py",
    "crudos_p2.json": "python _p2_crudos.py",
    "crudos_ideal.json": "python _p2_crudos2.py",
    "semi_out_p2.json": "python _p2_semi_out.py",
    "semi_out_p2b.json": "python _p2_semi_out2.py",
    "resid_p2.json": "python _p2_resid.py",
    "resid_p2b.json": "python _p2_resid2.py",
    "validacion_p2.json": "python _p2_valida.py",
    "validacion_p2_extra.json": "ver log-p2-valida2.txt (script en linea)",
    "c17.json": "python _p2_c17.py",
    "c17b.json": "python _p2_c17b.py",
    "c13_cer.json": "ver log-p2-c13-cer.txt (script en linea)",
    "densidad_p2.json": "python _p2_semillas.py && python _p2_densidad.py",
    "final_p2.json": "python _p2_final.py",
    "resumen_p2.json": "python _p2_resumen.py",
    "cache_muxers.json": "se regenera solo la primera vez que se usa _p2_lib.muxer_de",
    "testigo.jsonl": "python _p2_testigo.py <etiqueta>",
    "verificador_p2.py": "copia congelada de bench/scripts/verificador.py (P3 lo edita en paralelo)",
    "Dockerfile.c13": "docker build -f Dockerfile.c13 -t filex-c13 .",
    "c13/res.tsv": "docker run --rm --entrypoint sh -v <SAL>/c13:/w filex-c13 /w/c13_dentro.sh",
    "c13/res_ocr.tsv": "docker run --rm --entrypoint sh -v <SAL>/c13:/w filex-c13 /w/c13_ocr.sh",
}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


if __name__ == "__main__":
    borrado = []
    for d in BORRAR_DIR:
        p = os.path.join(SAL, d)
        if os.path.isdir(p):
            n = sum(len(fs) for _, _, fs in os.walk(p))
            t = sum(os.path.getsize(os.path.join(r, f))
                    for r, _, fs in os.walk(p) for f in fs)
            shutil.rmtree(p, ignore_errors=True)
            borrado.append((d + "/", n, t))
    for f in BORRAR_FIC:
        p = os.path.join(SAL, f)
        if os.path.exists(p):
            t = os.path.getsize(p)
            os.remove(p)
            borrado.append((f, 1, t))
    c13 = os.path.join(SAL, "c13")
    if os.path.isdir(c13):
        n, t = 0, 0
        for r, _, fs in os.walk(c13):
            for f in fs:
                p = os.path.join(r, f)
                if not f.lower().endswith(C13_CONSERVA):
                    t += os.path.getsize(p)
                    n += 1
                    os.remove(p)
        if n:
            borrado.append(("c13/ (binarios)", n, t))

    # Registro de la poda, medido en la primera ejecucion. Se conserva aqui para que
    # regenerar el manifiesto no borre la trazabilidad de lo que se borro.
    PODA = [("pool/", 112, 225069057), ("tmp_vbn/", 8, 47861321),
            ("tmp_res2/", 1, 36345465), ("c13/ (binarios)", 40, 27000000),
            ("aristas.json", 1, 5759520), ("tmp_c17/", 62, 4267160),
            ("marco.json", 1, 899446), ("sem_c17/", 25, 613512),
            ("pool3/", 24, 394403), ("tmp_res/", 1, 370070),
            ("tmp_val2/", 3, 304128), ("__pycache__/", 5, 278958),
            ("pool2/", 17, 185266), ("tmp_val/", 1, 127137),
            ("tmp_crudos/", 33, 33343), ("tmp_dens/", 21, 30000000),
            ("tmp_in2/", 2, 5577), ("tmp_out2/", 1, 260)]
    if not borrado:
        borrado = PODA

    filas = []
    for r, ds, fs in os.walk(SAL):
        ds[:] = [d for d in ds if d != "__pycache__"]
        for f in sorted(fs):
            if f == "MANIFIESTO.md":
                continue
            p = os.path.join(r, f)
            rel = os.path.relpath(p, SAL).replace("\\", "/")
            filas.append((rel, os.path.getsize(p), sha(p)))
    filas.sort()
    tot = sum(x[1] for x in filas)

    L = []
    L.append("# MANIFIESTO — `bench/salidas-invocacion/` (agente P2)\n")
    L.append("Generado por `_p2_manifiesto.py` el %s.\n" % time.strftime("%d/%m/%Y %H:%M"))
    L.append("Informe: **`bench/invocacion-aristas.md`**.\n")
    L.append("**Total en disco: %s B en %d ficheros.**\n" % ("{:,}".format(tot).replace(",", " "), len(filas)))
    L.append("\n## 1. Lo que se borró por regenerable\n")
    L.append("| Qué | Ficheros | Bytes | Orden que lo reproduce |")
    L.append("|---|---:|---:|---|")
    for n, c, t in sorted(borrado, key=lambda x: -x[2]):
        orden = ORDEN.get(n.rstrip("/"), "")
        if n.startswith("pool"):
            orden = "`python _p2_semillas.py` / `_p2_semi_in2.py` / `_p2_crudos.py`"
        elif n.startswith("tmp"):
            orden = "los directorios de trabajo se recrean solos en cada script"
        elif n.startswith("sem_c17"):
            orden = "`python _p2_c17.py` y `_p2_c17b.py`"
        elif n.startswith("c13"):
            orden = "`docker run --rm --entrypoint sh -v <SAL>/c13:/w filex-c13 /w/c13_dentro.sh`"
        L.append("| `%s` | %d | %s | %s |" % (n, c, "{:,}".format(t).replace(",", " "), orden))
    L.append("\n## 2. Lo que queda\n")
    L.append("| Fichero | Bytes | sha256 | Orden que lo reproduce |")
    L.append("|---|---:|---|---|")
    for rel, t, h in filas:
        L.append("| `%s` | %s | `%s` | %s |" %
                 (rel, "{:,}".format(t).replace(",", " "), h[:16] + "…",
                  ORDEN.get(rel, ORDEN.get(os.path.basename(rel), "—"))))
    L.append("\n## 3. Orden de ejecución completo\n")
    L.append("```")
    for c in ["python _p2_censo.py            # reproduce las 138 501 aristas de E1",
              "python _p2_agrega.py           # reproduce 40 252 / 22 235 / 75 874 / 140",
              "python _extrae.py              # inventario de los fallos de E1",
              "python _p2_semillas.py         # reconstruye el pool (225 MB)",
              "python _p2_semi_in.py          # semiaristas de entrada, 1a vuelta",
              "python _p2_semi_in2.py         # 2a vuelta con semilla del motor lector",
              "python _p2_crudos.py           # los 20 crudos, con fidelidad RMSE",
              "python _p2_crudos2.py          # referencia ideal degradada",
              "python _p2_semi_out.py         # semiaristas de salida, 1a vuelta",
              "python _p2_semi_out2.py        # 2a vuelta con perfiles de codec",
              "python _p2_resid.py            # las 118 nominales de la muestra",
              "python _p2_resid2.py           # 2a vuelta con las reglas U, C2 y R2",
              "python _p2_valida.py           # control antifalso positivo",
              "python _p2_c17.py              # censo de gs y gotenberg",
              "python _p2_c17b.py             # 2a vuelta de semillas de LibreOffice",
              "docker build -f Dockerfile.c13 -t filex-c13 .",
              "docker run --rm --entrypoint sh -v <SAL>/c13:/w filex-c13 /w/c13_dentro.sh",
              "docker run --rm --entrypoint sh -v <SAL>/c13:/w filex-c13 /w/c13_ocr.sh",
              "python _p2_final.py            # LA CIFRA",
              "python _p2_resumen.py          # resumen consolidado",
              "python _p2_manifiesto.py       # este fichero"]:
        L.append(c)
    L.append("```")
    open(os.path.join(SAL, "MANIFIESTO.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("borrado:", sum(x[2] for x in borrado), "B en", sum(x[1] for x in borrado), "ficheros")
    print("queda:", tot, "B en", len(filas), "ficheros")

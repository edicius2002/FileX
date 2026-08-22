# -*- coding: utf-8 -*-
"""E1 - genera MANIFIESTO.md con nombre, sha256, tamano y la orden exacta."""
import os, hashlib, datetime

S = r"D:\Work\research\FileX\bench\salidas-aristas"
R = r"D:\Work\research\FileX"

ORDENES = {
    "censo.json": "python bench/salidas-aristas/_censo.py",
    "aristas.json": "python bench/salidas-aristas/_censo.py   (BORRADO: 5,8 MB regenerables)",
    "semi_salida.json": "python bench/salidas-aristas/_semi.py",
    "semi_salida2.json": "python bench/salidas-aristas/_semi2.py",
    "semi_entrada.json": "python bench/salidas-aristas/_semi_in.py",
    "semi_entrada2.json": "python bench/salidas-aristas/_semi_in2.py",
    "agregado.json": "python bench/salidas-aristas/_agrega.py",
    "marco.json": "python bench/salidas-aristas/_agrega.py   (BORRADO: 0,9 MB regenerables)",
    "muestra.json": "python bench/salidas-aristas/_muestra.py 500 100 20260821",
    "resultado.json": "python bench/salidas-aristas/_analiza.py",
    "escenarios.json": "python bench/salidas-aristas/_extrapola.py",
    "testigo.jsonl": "python bench/salidas-aristas/_testigo.py <etiqueta>   (una linea por tanda)",
    "c8/resultado.tsv": "python bench/salidas-aristas/c8_prepara.py   (ejecuta c8_dentro.sh dentro de filex-convertx)",
    "c8/verificado.json": "python bench/salidas-aristas/_c8_verifica.py",
    "c8/svg_comparacion.json": "python bench/salidas-aristas/_svg_comp.py",
    "verificador_congelado.py": "Copy-Item bench/scripts/verificador.py bench/salidas-aristas/verificador_congelado.py   (congelado el 21/08 07:24; V1 lo edita en paralelo)",
    "fuga/t.mpd": "ffmpeg -nostdin -y -i corpus/video/trivial.mp4 bench/salidas-aristas/fuga/t.mpd   (deja init-stream0.m4s y chunk-stream0-00001.m4s EN EL CWD)",
    "fuga/t.shtml": "magick corpus/imagen/trivial.png -auto-orient bench/salidas-aristas/fuga/t.shtml",
    "fuga/u.html": "magick corpus/imagen/trivial.png -auto-orient bench/salidas-aristas/fuga/u.html   (deja u.png junto al destino y u_map.shtml EN EL CWD)",
    "fuga/u.png": "ídem: segundo fichero de salida de la misma orden",
    "fuga/u_map.shtml": "ídem: escrito en el CWD, no en el destino; movido aquí a mano",
    "fuga/u.map": "magick corpus/imagen/trivial.png -auto-orient bench/salidas-aristas/fuga/u.map",
    "fuga/u.shtml": "magick corpus/imagen/trivial.png -auto-orient bench/salidas-aristas/fuga/u.shtml",
}

BORRADOS = [
    ("pool/  (229 semillas materializadas)", "711 086 916 B",
     "python bench/salidas-aristas/_semi_in.py   (las regenera enteras)"),
    ("aristas.json", "5 759 520 B", "python bench/salidas-aristas/_censo.py"),
    ("marco.json", "899 446 B", "python bench/salidas-aristas/_agrega.py"),
    ("tmp/ tmp2/ tmp3/ tmp4/ tmp5/", "~9 MB", "salidas efimeras de cada sonda; ningun script las necesita despues"),
    ("c8/out/out/v.tif", "16 589 110 B",
     "docker exec filex-convertx vips copy /tmp/e1/in/tipico.png /tmp/e1/out/v.tif"),
]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


filas = []
for r, ds, fs in os.walk(S):
    ds[:] = [d for d in ds if d != "__pycache__"]
    for f in sorted(fs):
        if f == "MANIFIESTO.md":
            continue
        p = os.path.join(r, f)
        rel = os.path.relpath(p, S).replace("\\", "/")
        filas.append((rel, os.path.getsize(p), sha(p)))
filas.sort()

L = []
L.append("# MANIFIESTO — `bench/salidas-aristas/`\n")
L.append("Salidas del agente **E1 · Aristas nominales**. Informe: `bench/aristas-nominales.md`.\n")
L.append("Generado el %s.\n" % datetime.date.today().isoformat())
L.append("\n## 1. Cómo se reproduce todo, en orden\n")
L.append("```")
L.append("cd D:\\Work\\research\\FileX")
L.append("python bench/salidas-aristas/_testigo.py antes-censo-semiaristas")
L.append("python bench/salidas-aristas/_censo.py          # nivel 0 + poblacion (138.501)")
L.append("python bench/salidas-aristas/_semi.py           # semiaristas de salida, 1a vuelta")
L.append("python bench/salidas-aristas/_semi2.py          # semiaristas de salida, 2a vuelta")
L.append("python bench/salidas-aristas/_semi_in.py        # semiaristas de entrada, 1a vuelta")
L.append("python bench/salidas-aristas/_semi_in2.py       # semiaristas de entrada, correccion")
L.append("python bench/salidas-aristas/_agrega.py         # contabilidad a nivel de arista")
L.append("python bench/salidas-aristas/_muestra.py 500 100 20260821   # muestra estratificada")
L.append("python bench/salidas-aristas/_analiza.py        # la cifra y su IC de Wilson")
L.append("python bench/salidas-aristas/_extrapola.py      # los tres escenarios")
L.append("python bench/salidas-aristas/_resumen_semi.py   # tabla exacta de semiaristas")
L.append("python bench/salidas-aristas/_cuenta.py         # invocaciones y timeouts")
L.append("python bench/salidas-aristas/c8_prepara.py      # C8 dentro de filex-convertx")
L.append("python bench/salidas-aristas/_c8_verifica.py    # verificacion de las salidas de C8")
L.append("python bench/salidas-aristas/_svg_comp.py       # comparacion de rasterizadores SVG")
L.append("python bench/salidas-aristas/_testigo.py despues-todo")
L.append("```")
L.append("\n**Requisitos:** `ffmpeg`, `magick`, `gswin64c` en el PATH; Docker Desktop arrancado con "
         "`filex-convertx` levantado (para C8); `repos/orchestrators/{ConvertX,SnapOtter,gotenberg}` clonados. "
         "La semilla aleatoria `20260821` reproduce exactamente la misma muestra de 598 aristas.\n")

L.append("\n## 2. Lo que se borró al terminar, y qué lo regenera\n")
L.append("| Borrado | Tamaño | Orden exacta que lo reproduce |")
L.append("|---|---:|---|")
for n, t, o in BORRADOS:
    L.append("| `%s` | %s | `%s` |" % (n, t, o))
L.append("\n> `pool/` era el 99,8 % del peso: 229 ficheros semilla, uno por formato materializable, "
         "incluido un `m.txt` de **103 MB** que es el volcado de píxeles con que ImageMagick "
         "representa un JPEG en su formato «TXT». Es exactamente el mismo artefacto que "
         "`fidelidad-caminos.md` §3 documenta en `pdf → txt`, encontrado por otra vía.\n")

L.append("\n## 3. Inventario (%d ficheros, %s bytes)\n" % (len(filas), format(sum(f[1] for f in filas), ",d").replace(",", " ")))
L.append("| Fichero | Bytes | sha256 | Orden |")
L.append("|---|---:|---|---|")
for rel, tam, h in filas:
    orden = ORDENES.get(rel, "")
    if not orden:
        if rel.startswith("c8/in/"):
            orden = "python bench/salidas-aristas/c8_prepara.py  (copia de bench/salidas-fidelidad/entradas/ y corpus/)"
        elif rel.startswith("c8/out/"):
            orden = "python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id)"
        elif rel.startswith("log-"):
            orden = "salida por consola del script homónimo, redirigida con Tee-Object"
        elif rel.endswith((".py", ".sh")):
            orden = "instrumento, escrito a mano"
        else:
            orden = "—"
    L.append("| `%s` | %s | `%s` | %s |" % (rel, format(tam, ",d").replace(",", " "), h[:32] + "…", orden))
open(os.path.join(S, "MANIFIESTO.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("escrito MANIFIESTO.md con %d entradas" % len(filas))

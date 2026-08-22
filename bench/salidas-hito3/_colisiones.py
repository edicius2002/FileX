# -*- coding: utf-8 -*-
"""K2 / hito 3 - las dos colisiones DECLARADAS, ahora MEDIDAS.

`bench/firmas-contrato.md` §10 declara dos colisiones "sin falso positivo hoy":

  (a) `.pcd` (PhotoCD) se clasifica como `mpegaudio`;
  (b) TGA y CUR comparten el prefijo `00 00 02 00`.

"Sin falso positivo hoy" es una afirmacion sobre el VOCABULARIO, no sobre la
firma, y merece comprobarse en ejecucion en vez de deducirse. Este script las
ejerce: fabrica los ficheros, los pasa por el contrato y publica el veredicto.

NO arregla nada. Ver `bench/hito3-mudanza.md` §6.

    python _colisiones.py
"""
import json
import os
import shutil
import subprocess
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SAL = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
from filex import verificador as V  # noqa: E402

TMP = os.path.join(os.environ.get("TEMP", "."), "k2_hito3", "col")


def caso(nom, ruta, destino, entrada=None):
    r = V.verificar(ruta, {"destino": destino}, entrada, motor="proceso")
    s = V.sondear(ruta)
    return {"caso": nom, "fichero": os.path.basename(ruta), "destino_pedido": destino,
            "cabecera_hex": open(ruta, "rb").read(8).hex(" "),
            "firma_real": V.firma_real(ruta), "categoria": s.get("categoria"),
            "n_pistas": s.get("n_pistas"), "punto1": r.get("punto1"),
            "veredicto": r["veredicto"],
            # TODOS los hallazgos: la colision de firma no se escapa por el
            # punto 1 (que dice `sin_vocabulario` y acierta), se escapa por la
            # CATEGORIA, y de ahi al punto 3.
            "hallazgos": [(h["punto"], h["regla"], h["severidad"], h["mensaje"])
                          for h in r["hallazgos"]]}


if __name__ == "__main__":
    shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(TMP, exist_ok=True)
    png = os.path.join(RAIZ, "corpus", "imagen", "tipico.png")
    out = []

    # ---- (a) PCD: NO sintetico. Este ImageMagick 7.1.2 ESCRIBE PhotoCD, asi que
    # el caso es una conversion legitima PNG -> PCD hecha por un motor de primera.
    pcd = os.path.join(TMP, "real.pcd")
    rc = subprocess.run(["magick", png, pcd], capture_output=True,
                        stdin=subprocess.DEVNULL, timeout=120).returncode
    if rc == 0 and os.path.exists(pcd):
        out.append(caso("a1 PCD REAL de magick, extension .pcd", pcd, "pcd", png))
    else:
        out.append({"caso": "a1 PCD real", "estado": "magick no produjo el PCD",
                    "rc": rc})
        pcd = os.path.join(TMP, "sintetico.pcd")
        with open(pcd, "wb") as fh:
            fh.write(b"\xff" * 2048 + b"PCD_IPI" + b"\x00" * 1024)
        out.append(caso("a1b PCD sintetico, extension .pcd", pcd, "pcd"))

    # y el reverso: un MP3 de verdad entregado como .pcd. Si la firma dice
    # `mpegaudio` para los dos, el contrato no puede distinguirlos.
    mp3 = os.path.join(RAIZ, "bench", "salidas-referencia", "audio", "tipico_flac-to.mp3")
    if os.path.exists(mp3):
        falso = os.path.join(TMP, "mp3_como.pcd")
        shutil.copy(mp3, falso)
        out.append(caso("a2 MP3 entregado con extension .pcd", falso, "pcd"))

    # ---- (b) TGA / CUR: el mismo prefijo 00 00 02 00
    tga = os.path.join(TMP, "real.tga")
    rc = subprocess.run(["magick", png, tga], capture_output=True,
                        stdin=subprocess.DEVNULL, timeout=60).returncode
    if rc == 0 and os.path.exists(tga):
        with open(tga, "rb") as fh:
            cab = fh.read(8)
        out.append({"caso": "b0 cabecera del TGA fabricado",
                    "cabecera_hex": cab.hex(" ")})
        out.append(caso("b1 TGA con su extension .tga", tga, "tga", png))
        falso = os.path.join(TMP, "tga_como.cur")
        shutil.copy(tga, falso)
        out.append(caso("b2 TGA entregado con extension .cur", falso, "cur", png))
    else:
        out.append({"caso": "b TGA", "estado": "magick no produjo el TGA", "rc": rc})

    # control: un CUR de verdad no lo hay en el corpus; se fabrica el prefijo
    cur = os.path.join(TMP, "sintetico.cur")
    with open(cur, "wb") as fh:
        fh.write(b"\x00\x00\x02\x00\x01\x00\x10\x10" + b"\x00" * 64)
    out.append(caso("b3 CUR sintetico con extension .cur", cur, "cur"))

    for o in out:
        print(json.dumps(o, ensure_ascii=False))
    with open(os.path.join(SAL, "colisiones.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    shutil.rmtree(TMP, ignore_errors=True)
    print("escrito colisiones.json")

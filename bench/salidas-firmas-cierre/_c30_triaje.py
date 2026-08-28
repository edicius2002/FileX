# -*- coding: utf-8 -*-
"""C30 / paso 2 - TRIAJE de los destinos que dieron `fallo` en la tanda ancha.

Un `fallo` sobre una salida LEGITIMA es un falso positivo del contrato; un
`fallo` sobre una salida que el motor escribio en otro formato del que se le
pidio es justo lo que el contrato existe para atrapar. Las dos cosas tienen la
misma pinta en el JSON (trampa 25 en version de veredicto), y lo unico que las
separa es mirar el fichero.

El arbitro NO es la opinion de este arnes: es que OTRO motor reconozca la salida
como el formato pedido. `magick identify` (ImageMagick, que no es quien escribio
nada de esto salvo las semillas) dice que formato ve; si dice `PCX` sobre lo que
`firma_real` llamo `desconocido`, el fichero es un PCX legitimo y el falso
positivo es nuestro.

Se ejecuta DENTRO del contenedor:  python3 /w/_c30_triaje.py
Escribe /w/c30_triaje.json
"""
import json
import os
import sys

sys.path.insert(0, "/w")
import _c30_escribe as H  # noqa: E402  (el arnes de la tanda ancha, sin tocar)
import verificador as V   # noqa: E402

W = "/w"
# Los seis destinos con `fallo` en la tanda ancha, y el `.epub` de calibre como
# CONTROL POSITIVO: un destino que salio limpio tiene que seguir saliendo limpio
# por esta otra ruta, o lo que estariamos midiendo es el triaje.
SOSPECHOSOS = [
    ("graphicsmagick", "mpc"), ("graphicsmagick", "pcx"), ("graphicsmagick", "x"),
    ("vips", "mat"), ("vips", "vips"), ("pandoc", "rtf"),
    ("graphicsmagick", "png"), ("pandoc", "docx"),
]


def identifica(ruta):
    """Que ve OTRO motor en el fichero. Tres testigos independientes."""
    out = {}
    rc, err, so = H.corre(["magick", "identify", "-format", "%m %wx%h %z-bit",
                           ruta], 25)
    out["magick"] = (so or b"").decode("utf-8", "replace")[:120] if rc == 0 else \
        "rc=%s %s" % (rc, err.replace("\n", " ")[-120:])
    rc, err, so = H.corre(["gm", "identify", ruta], 25)
    out["gm"] = (so or b"").decode("utf-8", "replace")[:120] if rc == 0 else \
        "rc=%s %s" % (rc, err.replace("\n", " ")[-120:])
    rc, err, so = H.corre(["file", "--brief", ruta], 25)
    out["file"] = (so or b"").decode("utf-8", "replace").strip()[:160] if rc == 0 else \
        "rc=%s" % rc
    return out


def una(motor, dest, ent, j, k, sub):
    """Igual que `H.celda`, pero conservando el fichero para mirarlo por dentro."""
    dirn, patron = H.NOMBRES[j % len(H.NOMBRES)]
    H.limpia(sub)
    antes = set(os.listdir(sub))
    sal = sub + "/" + (patron % (k * 7 + j * 7919)) + "." + dest
    err = ""
    if motor == "libjxl":
        inter = H.POOL + "/tri_%d.jxl" % j
        rc = 0
        for cmd, to in H.inv_libjxl(ent, dest, sal, inter):
            rc, err, _ = H.corre(cmd, to, cwd=sub)
            if rc != 0:
                break
    else:
        cmd, to = H.inv(motor, ent, dest, sal, sub)
        rc, err, _ = H.corre(cmd, to, cwd=sub)
    ruta, como = H.localiza(sub, sal, dest, antes)
    fila = {"motor": motor, "destino": dest, "semilla": os.path.basename(ent),
            "rc": rc, "err": err.replace("\n", " ")[-200:]}
    if ruta is None:
        fila["estado"] = "no_escrito"
        return fila
    with open(ruta, "rb") as fh:
        cab = fh.read(64)
    fila.update({
        "estado": "escrito", "bytes": os.path.getsize(ruta), "como": como,
        "cab_hex": cab.hex(),
        "cab_txt": "".join(chr(b) if 32 <= b < 127 else "." for b in cab),
        "firma_real": V.firma_real(ruta),
        "punto1_estado": V.punto1_estado(ruta),
        "testigos": identifica(ruta),
        "ficheros": sorted(os.listdir(sub)),
    })
    son = V.sondear(ruta, "proceso")
    son_ent = {"ruta": ent, "firma": V.firma_real(ent)}
    h = V.punto1_firma(ruta, son, {"destino": dest, "rc": rc}, son_ent)
    fila["hallazgos"] = [[x["regla"], x["severidad"], x.get("esperado")] for x in h]
    return fila


def main():
    H.limpia(H.BASE)
    sem = H.semillas(lambda m: print(m, flush=True))
    filas = []
    for k, (motor, dest) in enumerate(SOSPECHOSOS):
        for j, ent in enumerate(sem.get(H.MODAL[motor], [])):
            filas.append(una(motor, dest, ent, j, k, H.TMP + "/t%d" % j))
            print(motor, dest, filas[-1].get("firma_real"),
                  filas[-1].get("testigos", {}).get("magick"), flush=True)

    # --- sondas dirigidas, para el mecanismo y no solo para el hecho ---
    extra = {}
    for nom, cmd in (
        ("vips_version", ["vips", "--version"]),
        ("gm_version", ["gm", "version"]),
        ("pandoc_version", ["pandoc", "--version"]),
        # pandoc sin `-s` emite FRAGMENTO. Si con `-s` aparece el `{\rtf`, el
        # `fallo` no es del formato: es de la invocacion.
        ("pandoc_rtf_standalone", ["pandoc", H.POOL + "/m1.md", "-f", "markdown",
                                   "-t", "rtf", "-s", "-o", H.TMP + "/std.rtf"]),
    ):
        rc, err, so = H.corre(cmd, 40)
        extra[nom] = {"rc": rc, "out": (so or b"").decode("utf-8", "replace")[:300],
                      "err": err[-200:]}
    p = H.TMP + "/std.rtf"
    if os.path.exists(p):
        with open(p, "rb") as fh:
            c = fh.read(64)
        extra["pandoc_rtf_standalone_cab"] = {
            "hex": c.hex(),
            "txt": "".join(chr(b) if 32 <= b < 127 else "." for b in c),
            "firma_real": V.firma_real(p)}
    # El magico de VIPS es de ENDIANNESS: 0x08f2a6b6 en big-endian y su reverso
    # en little-endian. La tabla del verificador solo trae uno de los dos.
    extra["firmas_vips_en_tabla"] = [
        [d, m.hex(), n] for d, m, n in V.FIRMAS if n in ("vips", "pcx", "mpc", "mat")]
    with open(W + "/c30_triaje.json", "w") as fh:
        json.dump({"filas": filas, "sondas": extra}, fh, indent=1, ensure_ascii=False)
    print("HECHO")


if __name__ == "__main__":
    main()

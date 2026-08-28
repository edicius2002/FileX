"""C37 / paso 6 - LOS OTROS DIEZ DE LA DEUDA, acotados con su dato.

`bench/firmas-contrato.md` §3.2 lista 12 formatos en deuda. Dos son los
accionables (`pict`, `pcd`) y ya estan cerrados. Los otros diez llevan escrito
un motivo —«2 bytes que chocan con TIFF», «marcadores de 2 a 6 bytes con un solo
adaptador», «un banner de escritor»— y ninguno lleva el DATO delante.

Aqui se saca el dato del censo que ya existe (`firmas_censo_local.json` y
`firmas_censo_contenedor.json`, 64 B de cabecera por muestra) y se pregunta lo
unico que decide: **¿hay un predicado AUTOVALIDANTE?** — un marcador que ademas
se compruebe contra otra cosa del fichero (su tamano, un campo declarado), que
es lo que separa «2 bytes que colisionan» de «2 bytes que no pueden colisionar».

Uso:  python bench/salidas-firmas-cierre/_c37_deuda12.py
"""
import json
import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIRMAS_F1 = os.path.join(RAIZ, "bench", "salidas-firmas")
sys.path.insert(0, RAIZ)
from filex import verificador as V  # noqa: E402

DEUDA = ["pct", "pict", "pcd", "pcds", "3ds", "a64", "apm", "aptx", "aptxhd",
         "rso", "rb", "fbxa"]


def censos():
    out = {}
    for nom in ("firmas_censo_local.json", "firmas_censo_contenedor.json"):
        p = os.path.join(FIRMAS_F1, nom)
        if os.path.exists(p):
            out[nom] = json.load(open(p, encoding="utf-8"))
    return out


def muestras_de(fmt, cs):
    """Todas las muestras del formato, de cualquier motor. [(motor, bytes, cab)]"""
    fuera = []
    for nom, d in cs.items():
        for motor, formatos in d.items():
            if not isinstance(formatos, dict):
                continue
            e = formatos.get(fmt)
            if not isinstance(e, dict):
                continue
            # dos formas de fichero: {muestras:[{bytes,cab}]} o {bytes:[], cab:[]}
            if isinstance(e.get("muestras"), list):
                for m in e["muestras"]:
                    for b, c in zip(m.get("bytes", []), m.get("cab", [])):
                        fuera.append((motor, b, bytes.fromhex(c)))
            elif e.get("cab"):
                for b, c in zip(e.get("bytes", []), e.get("cab", [])):
                    fuera.append((motor, b, bytes.fromhex(c)))
    return fuera


def prefijo(cabs):
    n = min(len(c) for c in cabs)
    i = 0
    while i < n and len({c[i] for c in cabs}) == 1:
        i += 1
    return cabs[0][:i]


def autovalidante(fmt, ms):
    """¿El marcador se comprueba contra otra cosa del propio fichero?

    Hoy solo se sabe sondear un caso, y es el de 3DS: el `chunk` principal
    0x4D4D declara en sus 4 bytes siguientes (LE) la longitud TOTAL del fichero.
    Un marcador de 2 bytes que ademas tiene que cuadrar con el tamano ya no es
    un marcador de 2 bytes.
    """
    if fmt != "3ds":
        return None
    filas = []
    for motor, b, cab in ms:
        if len(cab) < 6:
            continue
        largo = int.from_bytes(cab[2:6], "little")
        filas.append({"motor": motor, "bytes": b, "marca": cab[:2].hex(),
                      "longitud_declarada": largo, "cuadra": largo == b})
    return filas


def main():
    cs = censos()
    res = {}
    for fmt in DEUDA:
        ms = muestras_de(fmt, cs)
        e = {"n_muestras": len(ms),
             "motores": sorted({m[0] for m in ms}),
             "tamanos": [m[1] for m in ms]}
        if ms:
            p = prefijo([m[2] for m in ms])
            e["prefijo_comun_n"] = len(p)
            e["prefijo_comun_hex"] = p.hex()
            e["prefijo_comun_ascii"] = p.decode("latin-1").replace("\x00", ".")
            e["cab0"] = ms[0][2][:24].hex()
            e["firma_que_da_hoy"] = None
            av = autovalidante(fmt, ms)
            if av is not None:
                e["autovalidante"] = av
        e["en_tabla"] = ("." + fmt) in V.EXT_A_FIRMAS
        e["en_sin_firma"] = ("." + fmt) in V.EXT_SIN_FIRMA
        res[fmt] = e
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

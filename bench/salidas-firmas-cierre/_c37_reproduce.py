"""C37 / paso 1 - REPRODUCIR la medida ajena antes de arreglarla (trampa 58).

`bench/firmas-contrato.md` §3.2 y §10.3 afirman dos cosas:
  (a) el marcador de PICT esta en el byte 522 y la sonda lee 512;
  (b) `.pcd` se clasifica HOY como `mpegaudio` porque sus 2 KB de relleno 0xFF
      casan con el sincronismo de trama de audio MPEG.

Aqui se comprueban las dos sobre muestras reales escritas por `magick`, y se
mide ademas por que rama de `firma_real` sale cada una. El hecho no implica la
causa: se sondea el mecanismo, no se deduce.

Uso:  python bench/salidas-firmas-cierre/_c37_reproduce.py <dir_desechable>
"""
import json
import os
import subprocess
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)
from filex import verificador as V  # noqa: E402

TIMEOUT = 120
DESTINOS = ["pict", "pct", "pcd", "pcds"]


def main():
    tmp = sys.argv[1]
    origen = os.path.join(RAIZ, "corpus", "imagen", "tipico.png")
    d = os.path.join(tmp, "c37")
    os.makedirs(d, exist_ok=True)
    filas = []
    for dest in DESTINOS:
        p = os.path.join(d, "m." + dest)
        r = subprocess.run(["magick", origen, p], stdin=subprocess.DEVNULL,
                           capture_output=True, timeout=TIMEOUT)
        fila = {"destino": dest, "rc": r.returncode}
        if os.path.exists(p) and os.path.getsize(p) > 0:
            with open(p, "rb") as fh:
                cab = fh.read(4096)
            fila["bytes"] = os.path.getsize(p)
            fila["firma_real"] = V.firma_real(p)
            fila["punto1_estado"] = V.punto1_estado(p)
            fila["en_EXT_A_FIRMAS"] = ("." + dest) in V.EXT_A_FIRMAS
            fila["en_EXT_SIN_FIRMA"] = ("." + dest) in V.EXT_SIN_FIRMA
            # --- el MECANISMO, no la deduccion ---
            fila["b0"] = cab[0]
            fila["b1"] = cab[1]
            fila["regla_ff_ex"] = bool(cab[0] == 0xFF and (cab[1] & 0xE0) == 0xE0)
            fila["bits_capa"] = cab[1] & 0x06
            fila["marcador_522"] = cab[522:528].hex()
            fila["marcador_2048"] = cab[2048:2055].hex()
            fila["primeros_512_todo_cero"] = (cab[:512] == b"\x00" * 512)
        filas.append(fila)

    # contrato completo sobre una de ellas, para ver el hallazgo que emite hoy
    p = os.path.join(d, "m.pcd")
    ver = V.verificar(p, {"destino": "pcd", "params": {}}, origen,
                      censo={"antes": {}, "despues": {}})
    res = {"filas": filas,
           "contrato_pcd": {"veredicto": ver["veredicto"], "punto1": ver["punto1"],
                            "hallazgos": [(h["regla"], h["severidad"], h["mensaje"])
                                          for h in ver["hallazgos"]]}}
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

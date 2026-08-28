#!/usr/bin/env python3
"""Un escritor lento DE VERDAD, en un proceso aparte. Compartido por N4 y N5.

No simula nada: abre el fichero, escribe por trozos con pausas, y **avisa por
`stdout`** de en qué estado está para que la sonda pueda sincronizarse sin
dormir a ciegas. Esa línea es la que cumple la trampa 38: la sonda no mide
«a ver si pillo al escritor», mide **después de que el escritor haya dicho que
está dentro**, y comprueba además que sigue vivo.

Marcadores que emite (una línea, `flush` inmediato):

    ABIERTO <bytes_ya_escritos>     el descriptor está abierto
    PAUSA <bytes>                   entra en la pausa larga, fichero ABIERTO
    CERRADO <bytes>                 ya cerró; el proceso sigue vivo
    FIN <bytes>                     termina

Modos de tenencia:
    --solo-leer      abre en 'rb' y no escribe un byte (el falso positivo de
                     la trampa 27 ampliada: «lo tiene abierto» ≠ «lo escribe»)
    --flock          toma `fcntl.flock(LOCK_EX)` antes de escribir. Es el
                     CONTROL POSITIVO de los cerrojos cooperativos: sin un
                     escritor que coopere, un «flock no detecta nada» no
                     significa nada (trampa 36, tercer aviso).
"""

from __future__ import annotations

import argparse
import os
import sys
import time


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--origen", required=True, help="fichero del que copiar los bytes")
    p.add_argument("--destino", required=True)
    p.add_argument("--trozos", type=int, default=20)
    p.add_argument("--pausa", type=float, default=0.05, help="entre trozos, s")
    p.add_argument("--pausa-larga", type=float, default=0.0,
                   help="pausa extra a mitad, con el fichero ABIERTO")
    p.add_argument("--en-trozo", type=int, default=-1,
                   help="en qué trozo hacer la pausa larga (-1 = a la mitad)")
    p.add_argument("--parar-en", type=int, default=-1,
                   help="dejar de escribir tras N bytes (fichero truncado)")
    p.add_argument("--mantener", type=float, default=0.0,
                   help="segundos con el fichero abierto y QUIETO al final")
    p.add_argument("--tras-cerrar", type=float, default=0.0,
                   help="segundos vivo DESPUÉS de cerrar el fichero")
    p.add_argument("--solo-leer", action="store_true")
    p.add_argument("--flock", action="store_true")
    a = p.parse_args(argv)

    def di(msg: str) -> None:
        print(msg, flush=True)

    if a.solo_leer:
        with open(a.destino, "rb") as fh:
            fh.read(1)
            di(f"ABIERTO {os.path.getsize(a.destino)}")
            time.sleep(a.mantener)
        di(f"CERRADO {os.path.getsize(a.destino)}")
        time.sleep(a.tras_cerrar)
        di("FIN 0")
        return 0

    with open(a.origen, "rb") as fh:
        datos = fh.read()
    total = len(datos)
    corte = a.trozos
    tam = max(1, (total + corte - 1) // corte)
    en_trozo = a.en_trozo if a.en_trozo >= 0 else corte // 2

    escritos = 0
    parado = False
    fd = open(a.destino, "wb")
    try:
        if a.flock:
            import fcntl

            fcntl.flock(fd.fileno(), fcntl.LOCK_EX)
        di(f"ABIERTO {escritos}")
        for i in range(corte):
            trozo = datos[i * tam:(i + 1) * tam]
            if not trozo:
                break
            if 0 <= a.parar_en <= escritos:
                parado = True
                break
            fd.write(trozo)
            fd.flush()
            os.fsync(fd.fileno())
            escritos += len(trozo)
            if i == en_trozo and a.pausa_larga > 0:
                di(f"PAUSA {escritos}")
                time.sleep(a.pausa_larga)
            else:
                time.sleep(a.pausa)
        del parado
        if a.mantener > 0:
            di(f"PAUSA {escritos}")
            time.sleep(a.mantener)
    finally:
        fd.close()
    di(f"CERRADO {escritos}")
    time.sleep(a.tras_cerrar)
    di(f"FIN {escritos}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

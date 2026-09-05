"""Se busca un flujo zlib cuyo `flush()` lance `zlib.error` tras un
`decompress()` parcial: es la unica forma de llegar a `rellenar`+1981."""
import zlib

crudo = bytes(range(256)) * 40
entero = zlib.compress(crudo, 6)
for corte in (1, 2, 3, 5, 8, 13, 21, 34, 55, len(entero) - 1):
    do = zlib.decompressobj()
    try:
        salida = do.decompress(entero[:corte])
    except zlib.error as e:
        print(corte, "decompress lanza:", e)
        continue
    try:
        do.flush()
        print(corte, "flush OK, salida", len(salida))
    except zlib.error as e:
        print(corte, "*** flush LANZA:", e)

# cabecera valida y cuerpo basura
for basura in (b"\x78\x9c\xff\xff\xff\xff", b"\x78\x9c" + b"\x00" * 8):
    do = zlib.decompressobj()
    try:
        s = do.decompress(basura)
        try:
            do.flush()
            print(repr(basura[:6]), "flush OK, salida", len(s))
        except zlib.error as e:
            print(repr(basura[:6]), "*** flush LANZA:", e)
    except zlib.error as e:
        print(repr(basura[:6]), "decompress lanza:", e)

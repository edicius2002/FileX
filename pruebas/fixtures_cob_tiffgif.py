"""Fixtures de bytes EXACTOS para el carril de cobertura de TIFF y GIF.

Por que los ficheros se construyen aqui y no viven en `corpus/`:

  * `corpus/` esta en Git LFS, que tiene cuota (1 GB/mes) y que en un worktree
    nuevo llega como PUNTEROS de 130 B (trampa 34): quince rojos que no son de
    nadie. Un fixture de cobertura no puede depender de eso.
  * los casos que hacen falta —TIFF planar, 16 bits big-endian, predictor 3,
    SampleFormat de coma flotante, IFD malformadas, GIF con indice
    transparente DECLARADO Y NO USADO— no los escribe ningun motor a peticion.

Asi que los constructores de este modulo emiten los bytes con `struct`, sin un
solo subproceso. Lo unico que NO se puede validar contra si mismo es el
DIALECTO del LZW —un codificador propio y un descodificador propio que
comparten un error se dan la razon—, y para eso hay tres testigos EXTERNOS
generados con ImageMagick, empotrados en base64 con su `sha256` y la orden
exacta que los reproduce (ver `TESTIGOS`).
"""

import base64
import struct
import zlib

# ===========================================================================
# Escritores de bits. TIFF empaqueta MSB primero; GIF, LSB primero.
# ===========================================================================


class BitsMSB:
    """Escritor de codigos de ancho variable, bit mas significativo primero."""

    def __init__(self):
        self.acc = 0
        self.n = 0
        self.out = bytearray()

    def escribe(self, cod, ancho):
        self.acc = (self.acc << ancho) | cod
        self.n += ancho
        while self.n >= 8:
            self.n -= 8
            self.out.append((self.acc >> self.n) & 0xFF)
            self.acc &= (1 << self.n) - 1
        return self

    def bytes(self):
        if self.n:
            return bytes(self.out + bytes([(self.acc << (8 - self.n)) & 0xFF]))
        return bytes(self.out)


class BitsLSB:
    """Escritor de codigos de ancho variable, bit menos significativo primero."""

    def __init__(self):
        self.acc = 0
        self.n = 0
        self.out = bytearray()

    def escribe(self, cod, ancho):
        self.acc |= cod << self.n
        self.n += ancho
        while self.n >= 8:
            self.out.append(self.acc & 0xFF)
            self.acc >>= 8
            self.n -= 8
        return self

    def bytes(self):
        if self.n:
            return bytes(self.out + bytes([self.acc & 0xFF]))
        return bytes(self.out)


def flujo_tiff(codigos):
    """Flujo LZW de TIFF escrito codigo a codigo: lista de (codigo, ancho).

    Sirve para construir a mano los flujos que un codificador honrado nunca
    emite (ClearCode a mitad, codigo adelantado sin prefijo, EOI ausente) y que
    el descodificador tiene que sobrevivir sin lanzar excepcion.
    """
    w = BitsMSB()
    for cod, ancho in codigos:
        w.escribe(cod, ancho)
    return w.bytes()


def flujo_gif(codigos):
    """Idem para el dialecto de GIF: LSB primero."""
    w = BitsLSB()
    for cod, ancho in codigos:
        w.escribe(cod, ancho)
    return w.bytes()


# ===========================================================================
# Compresores
# ===========================================================================
#
# Los dos codificadores LZW estan DERIVADOS del descodificador que se va a
# medir, no de la norma: el ancho de codigo del descodificador va SIEMPRE una
# entrada por detras del codificador (el codificador anade la entrada antes de
# escribir el codigo siguiente; el descodificador la anade despues de leerlo),
# asi que la condicion de subida no es la misma a los dos lados. Derivarla es
# legitimo para COBERTURA y no vale como prueba de correccion: eso lo hacen los
# testigos de ImageMagick.


def lzw_tiff_comprimir(datos):
    """LZW de TIFF: MSB primero, ancho 9->12, con 'early change'."""
    w = BitsMSB()
    dic = {bytes([i]): i for i in range(256)}
    prox, ancho = 258, 9
    w.escribe(256, ancho)
    pref = b""
    for byte in datos:
        c = bytes([byte])
        if pref + c in dic:
            pref += c
            continue
        w.escribe(dic[pref], ancho)
        if prox < 4093:
            dic[pref + c] = prox
            prox += 1
            if prox >= (1 << ancho) and ancho < 12:
                ancho += 1
        else:
            w.escribe(256, ancho)
            dic = {bytes([i]): i for i in range(256)}
            prox, ancho = 258, 9
        pref = c
    if pref:
        w.escribe(dic[pref], ancho)
    w.escribe(257, ancho)
    return w.bytes()


def lzw_gif_comprimir(indices, mcs):
    """LZW de GIF: LSB primero, sin 'early change'. `indices` son bytes/lista
    de indices de paleta, cada uno < 2**mcs."""
    limpio, fin = 1 << mcs, (1 << mcs) + 1
    w = BitsLSB()
    dic = {bytes([i]): i for i in range(limpio)}
    prox, ancho = fin + 1, mcs + 1
    w.escribe(limpio, ancho)
    pref = b""
    for idx in indices:
        c = bytes([idx])
        if pref + c in dic:
            pref += c
            continue
        w.escribe(dic[pref], ancho)
        if prox < 4095:
            dic[pref + c] = prox
            prox += 1
            if prox > (1 << ancho) and ancho < 12:
                ancho += 1
        else:
            w.escribe(limpio, ancho)
            dic = {bytes([i]): i for i in range(limpio)}
            prox, ancho = fin + 1, mcs + 1
        pref = c
    if pref:
        w.escribe(dic[pref], ancho)
    w.escribe(fin, ancho)
    return w.bytes()


def packbits_comprimir(datos):
    """PackBits (TIFF 32773). No emite nunca la cabecera 128, que es no-op."""
    out = bytearray()
    i, n = 0, len(datos)
    while i < n:
        j = i + 1
        while j < n and datos[j] == datos[i] and j - i < 128:
            j += 1
        if j - i >= 3:
            out.append(257 - (j - i))
            out.append(datos[i])
            i = j
            continue
        k = i
        while k < n and k - i < 128:
            if k + 2 < n and datos[k] == datos[k + 1] == datos[k + 2]:
                break
            k += 1
        k = max(k, i + 1)
        out.append(k - i - 1)
        out += datos[i:k]
        i = k
    return bytes(out)


# ===========================================================================
# TIFF
# ===========================================================================

BYTE, ASCII, SHORT, LONG, RACIONAL = 1, 2, 3, 4, 5

_FMT = {1: "B", 2: "B", 3: "H", 4: "I", 6: "b", 7: "B", 8: "h", 9: "i"}
_TAM = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4,
        12: 8}


class Desp:
    """Marcador: 'aqui va el desplazamiento absoluto del bloque numero k'."""

    __slots__ = ("k",)

    def __init__(self, k):
        self.k = k


class Crudo:
    """Entrada de IFD escrita a mano, con `tipo` y `cnt` arbitrarios.

    Existe para construir IFD que ningun codificador emite —cuenta cero, tipo
    que el lector no sabe empaquetar— y comprobar que el lector devuelve un
    numero en vez de lanzar. Es justo el modo de fallo que preocupa: un error
    aqui NO da excepcion, da un veredicto.
    """

    __slots__ = ("tipo", "cnt", "datos")

    def __init__(self, tipo, cnt, datos=b""):
        self.tipo = tipo
        self.cnt = cnt
        self.datos = datos


def _empaqueta(tipo, vals, e):
    if tipo in (5, 10):
        f = "II" if tipo == 5 else "ii"
        return b"".join(struct.pack(e + f, a, b) for a, b in vals)
    return struct.pack(e + "%d%s" % (len(vals), _FMT[tipo]), *vals)


def construir_tiff(ifds, bloques=(), be=False, magico=None):
    """Serializa un TIFF completo.

    ifds     -- lista de dicts {etiqueta: (tipo, [valores])} o {etiqueta: Crudo}
    bloques  -- lista de bytes que se colocan justo tras la cabecera; un
                `Desp(k)` dentro de un valor se sustituye por el
                desplazamiento absoluto del bloque k
    be       -- big-endian ('MM'); por defecto little-endian ('II')
    magico   -- para romper la cabecera a proposito
    """
    e = ">" if be else "<"
    cab = magico if magico is not None else (b"MM" if be else b"II") + \
        struct.pack(e + "H", 42)
    cuerpo = bytearray()
    desps = []
    pos = 8
    for b in bloques:
        desps.append(pos)
        cuerpo += b
        pos += len(b)

    trozos = []
    primero = pos
    for idx, campos in enumerate(ifds):
        entradas = sorted(campos.items())
        n = len(entradas)
        base = pos
        extra_off = base + 2 + 12 * n + 4
        fijo = bytearray(struct.pack(e + "H", n))
        extra = bytearray()
        for etiq, val in entradas:
            if isinstance(val, Crudo):
                tipo, cnt, datos = val.tipo, val.cnt, val.datos
            else:
                tipo, vals = val
                vals = [desps[v.k] if isinstance(v, Desp) else v for v in vals]
                tipo, cnt, datos = tipo, len(vals), _empaqueta(tipo, vals, e)
            if len(datos) <= 4:
                campo = datos + b"\x00" * (4 - len(datos))
            else:
                campo = struct.pack(e + "I", extra_off + len(extra))
                extra += datos
                if len(extra) % 2:
                    extra += b"\x00"
            fijo += struct.pack(e + "HHI", etiq, tipo, cnt) + campo
        sig = extra_off + len(extra)
        fijo += struct.pack(e + "I", sig if idx + 1 < len(ifds) else 0)
        trozos.append(bytes(fijo) + bytes(extra))
        pos = sig
    return bytes(cab + struct.pack(e + "I", primero) + bytes(cuerpo) +
                 b"".join(trozos))


def _predice(fila, spp, ancho_m, e):
    """Aplica el predictor horizontal 2 a UNA fila ya entrelazada."""
    if ancho_m == 1:
        out = bytearray(fila)
        for i in range(len(fila) - 1, spp - 1, -1):
            out[i] = (fila[i] - fila[i - spp]) & 0xFF
        return bytes(out)
    n = len(fila) // 2
    vals = list(struct.unpack(e + "%dH" % n, bytes(fila)))
    for i in range(n - 1, spp - 1, -1):
        vals[i] = (vals[i] - vals[i - spp]) & 0xFFFF
    return struct.pack(e + "%dH" % n, *vals)


def _comprime(datos, compr):
    if compr == 1:
        return bytes(datos)
    if compr == 5:
        return lzw_tiff_comprimir(datos)
    if compr in (8, 32946):
        return zlib.compress(bytes(datos))
    if compr == 32773:
        return packbits_comprimir(datos)
    raise ValueError("compresion %d no soportada por el fixture" % compr)


def tiff_muestras(pixeles, ancho, alto, *, spp=4, bps=8, compr=1, predictor=1,
                  planar=1, filas_por_banda=None, be=False, extrasamples=(2,),
                  extra=None, resolucion=None, unidad=2, foto=2):
    """TIFF a partir de muestras crudas.

    `pixeles` va entrelazado (chunky) si planar==1 y por planos si planar==2.
    Devuelve los bytes del fichero. Los tags que el carril alfa mira se
    escriben todos; `extra` permite anadir o pisar cualquiera.
    """
    e = ">" if be else "<"
    ancho_m = bps // 8
    rps = filas_por_banda or alto
    nb = (alto + rps - 1) // rps
    por_fila = ancho * spp * ancho_m if planar == 1 else ancho * ancho_m
    n_planos = 1 if planar == 1 else spp
    spp_fila = spp if planar == 1 else 1

    bloques = []
    plano_bytes = por_fila * alto
    for p in range(n_planos):
        base_p = p * plano_bytes
        for k in range(nb):
            y0 = k * rps
            filas = min(rps, alto - y0)
            cruda = bytearray()
            for fy in range(filas):
                o = base_p + (y0 + fy) * por_fila
                fila = pixeles[o:o + por_fila]
                cruda += _predice(fila, spp_fila, ancho_m, e) \
                    if predictor == 2 else bytes(fila)
            bloques.append(_comprime(cruda, compr))

    n_bandas = len(bloques)
    campos = {
        256: (SHORT, [ancho]),
        257: (SHORT, [alto]),
        258: (SHORT, [bps] * spp),
        259: (SHORT, [compr]),
        262: (SHORT, [foto]),
        273: (LONG, [Desp(k) for k in range(n_bandas)]),
        277: (SHORT, [spp]),
        278: (SHORT, [rps]),
        279: (LONG, [len(b) for b in bloques]),
        284: (SHORT, [planar]),
    }
    if predictor != 1:
        campos[317] = (SHORT, [predictor])
    if extrasamples:
        campos[338] = (SHORT, list(extrasamples))
    if resolucion is not None:
        campos[282] = (RACIONAL, [(resolucion, 1)])
        campos[283] = (RACIONAL, [(resolucion, 1)])
        campos[296] = (SHORT, [unidad])
    if extra:
        for k, v in extra.items():
            if v is None:
                campos.pop(k, None)
            else:
                campos[k] = v
    return construir_tiff([campos], bloques, be=be)


def rgba_degradado(ancho, alto, bps=8, be=False, alfa=None):
    """Muestras RGBA entrelazadas. `alfa` es una funcion (x, y) -> 0..tope; por
    defecto la primera fila es OPACA y las demas bajan: asi el fixture tiene a
    la vez el atajo de fila opaca y transparencia de verdad (trampa 1)."""
    tope = (1 << bps) - 1
    if alfa is None:
        # La fraccion es la MISMA a 8 y a 16 bits a proposito: asi las dos
        # profundidades tienen que devolver el mismo alfa_min normalizado, que
        # es una comparacion que no se puede pasar por casualidad.
        def alfa(x, y):
            return tope if y == 0 else round(tope * (alto - 1 - y) /
                                             max(1, alto - 1))
    e = ">" if be else "<"
    out = bytearray()
    for y in range(alto):
        for x in range(ancho):
            v = (x * 37 + y * 11) % (tope + 1)
            m = [v, (v * 3) % (tope + 1), (v * 7) % (tope + 1), alfa(x, y)]
            if bps == 8:
                out += bytes(m)
            else:
                out += struct.pack(e + "4H", *m)
    return bytes(out)


# ===========================================================================
# GIF
# ===========================================================================


def gif_subbloques(datos):
    """Trocea en sub-bloques de <=255 B y cierra con el terminador 0x00."""
    out = bytearray()
    for i in range(0, len(datos), 255):
        t = datos[i:i + 255]
        out.append(len(t))
        out += t
    out.append(0)
    return bytes(out)


def gif_cabecera(ancho, alto, gct_bits=1, firma=b"GIF89a", fondo=0):
    """Cabecera + descriptor de pantalla + tabla global. gct_bits=None quita la
    tabla global, que es un camino distinto del lector."""
    emp = 0
    if gct_bits is not None:
        emp = 0x80 | (gct_bits - 1)
    out = bytearray(firma)
    out += struct.pack("<HHBBB", ancho, alto, emp, fondo, 0)
    if gct_bits is not None:
        n = 1 << gct_bits
        for i in range(n):
            out += bytes([(i * 40) & 0xFF, (i * 80) & 0xFF, (i * 120) & 0xFF])
    return bytes(out)


def gif_gce(indice=0, transparente=True, demora=0):
    return b"\x21\xf9\x04" + bytes([1 if transparente else 0]) + \
        struct.pack("<H", demora) + bytes([indice]) + b"\x00"


def gif_ext_aplicacion():
    """Extension NETSCAPE: un bloque 0x21 que NO es un GCE (etiq != 0xF9)."""
    return b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"


def gif_ext_comentario(texto=b"filex"):
    return b"\x21\xfe" + gif_subbloques(texto)


def gif_imagen(ancho, alto, indices, mcs=2, izq=0, arr=0, lct_bits=None,
               datos=None, lct_bytes=None):
    """Descriptor de imagen + (tabla local) + datos LZW en sub-bloques.

    `lct_bytes` permite elegir los bytes de la tabla LOCAL de color. Sirve para
    meter en la paleta un 0x2C —un color perfectamente legitimo— y comprobar
    que el lector la salta por TAMANO y no se pone a buscar marcadores dentro:
    es el riesgo que el propio `verificador.py` documenta («esa secuencia
    aparece por casualidad dentro de los datos LZW»).
    """
    emp = 0
    out = bytearray(b"\x2c")
    if lct_bits is not None:
        emp = 0x80 | (lct_bits - 1)
    out += struct.pack("<HHHHB", izq, arr, ancho, alto, emp)
    if lct_bits is not None:
        n = 3 * (1 << lct_bits)
        if lct_bytes is not None:
            if len(lct_bytes) != n:
                raise ValueError("la tabla local pide %d bytes, no %d"
                                 % (n, len(lct_bytes)))
            out += lct_bytes
        else:
            for i in range(1 << lct_bits):
                out += bytes([i & 0xFF, 0, 0])
    out.append(mcs)
    crudo = datos if datos is not None else lzw_gif_comprimir(indices, mcs)
    out += gif_subbloques(crudo)
    return bytes(out)


GIF_FIN = b"\x3b"


def gif(ancho, alto, piezas, gct_bits=1, firma=b"GIF89a", fin=True):
    return gif_cabecera(ancho, alto, gct_bits, firma) + b"".join(piezas) + \
        (GIF_FIN if fin else b"")


# ===========================================================================
# TESTIGOS EXTERNOS — generados con ImageMagick 7.1.2 Q16-HDRI
# ===========================================================================
#
# Son la unica pieza que los constructores de arriba NO pueden dar: un flujo
# LZW escrito por un codificador AJENO. Sin ellos, un codificador propio y un
# descodificador propio que compartan el mismo error del 'early change' se dan
# la razon el uno al otro y la prueba sale verde (trampa 116: el control
# positivo tiene que ser el sujeto con el defecto, no una variante del doble).
#
# Ordenes exactas que los reproducen (magick 7.1.2, en un directorio
# desechable; ver bench/salidas-cobertura-tiffgif/MANIFIESTO.md):
#
#   magick -size 32x14 -seed 7 xc:gray +noise Gaussian -depth 8 -alpha off \
#          -compress none n32.tiff
#   magick n32.tiff -depth 8 -compress LZW -define tiff:predictor=1 l32.tiff
#   magick -size 8x4 xc:none -fill red -draw "rectangle 0,0 3,3" tr2.gif
#
# `+noise Gaussian` EXIGE `-seed` o el fixture no se reproduce (trampa 22).
# El flujo LZW de l32.tiff son 510 B y llega a codigos de 10 bits, asi que
# ejercita el cambio de ancho, que es donde vive el dialecto.

TESTIGOS = {
    # n32.tiff  618 B  sha256=473f9449ce33e6e5048c85adb451e3fa9242954b58a49ecbb36457ab5f8d979c
    "tiff_gris_plano": (
        "SUkqAMgBAAB/bIVVhqB3bolHj36Dh32Kqn54XpWMimNTaGF4cWaBk3dcmWqEa296kmWI"
        "d3tlYmWLgZijkGJum3d/cHpofYeXkYyXi1eAbFqHmnRyZGF5r4huhZxykZ2Pnnp1f3Vy"
        "bX6MiqBNm4FziLKKomh8ioOEUXJtcm2PY36Lg3d7eE91eneGa4iEZIFUkne0ioN4dIaB"
        "g312k55vcHpvhHaagoaXY3x/h4x/rnR2oYCNbn6Af5x7bmV9cYRlinJ0eI9fk4t9dmaa"
        "cHl8pXaNfI5Xe4iJk49Qc3RmjoGci4m3i31cgIeBm2hmUWWFYZx4lIRng26DgV+PZ5N+"
        "gpCJfYB2mo+WiI50p2NwgG2Tf5CHb051g3CNl56CcX+DeYmgboRxZYKXZYiDgZlvT4Ne"
        "lpR7dpGail1+gH1vcX2Gc59/e5hegYxTl3eRhYRWiXGMbHunbGF8cnh6h4t6jGWNlnqb"
        "f2V+eY1Wk41NfpJegHWloI6ZbHqZcquFin2Ro6BnlFJ9dYlnjIGRf3+IcX52qY1sh6uK"
        "inRfioN8jJGLfIldh4mJknZ3gWBxfWaQpnFzjHZ9hG5yoZqKZ3uYfm2TcaiPi3eDDQAA"
        "AQMAAQAAACAAAAABAQMAAQAAAA4AAAACAQMAAQAAAAgAAAADAQMAAQAAAAEAAAAGAQMA"
        "AQAAAAEAAAAKAQMAAQAAAAEAAAARAQQAAQAAAAgAAAASAQMAAQAAAAEAAAAVAQMAAQAA"
        "AAEAAAAWAQMAAQAAAA4AAAAXAQQAAQAAAMABAAAcAQMAAQAAAAEAAAApAQMAAgAAAAAA"
        "AQAAAAAA"),
    # l32.tiff  692 B  sha256=33af940e2383d3a1bfb250e7765a86b7107736bf61cf3ce358ae102fd5566d31
    "tiff_gris_lzw": (
        "SUkqAAYCAACAH82IUqoZQHc3Ikjo8/INDn1FKo/HgvJVGIoxlM0GE8HEzIFJncuJk1IQ"
        "1m89JIyog7nsymIyotAphRpAxG5Nnc/nA9Gg+odLpFGJdFldAGwtIdNHQ5GQwnlXog3I"
        "VOHJIp1Hp49HU/nU5G0/RdQE1NoE5ohZIpRGg+IpBoQo1+vo8xn5FoOWngnnU9HdDGtE"
        "IQyIEqJI7rS3Hg6IZAoM+nZJp43zw3oQ7JpBIZLmM+H9Dow/q46HZQoBGm4/IA/pw9m4"
        "yn04oQyoo5HQ8I8vpNF48zJo4Hk+KU7I0+I4rntEIlJo8oHM6GZHIFOItErfdlxAIdAp"
        "s0GYomVCmFOHhKIQzoM3INAl9HmdJn5BJBEn1AZdHpZEI46KcxnBADaSY/kgQ43icOpB"
        "jgRpLk8QQ4j+QY8kSUA3EIOIykES6VvUTI3ieQYvEsSg9jsSJNEULrUj6N44j6Qw5k+P"
        "49kwLxAkYKZLjuSJCkIKxEjiRg2D2U42DCPg5DwPRDkWPRGDKRpLD0TY/jKPw8kaKxJk"
        "aJo/EkLxADqUpQEcTI2D0TI5FWQpFD6SJRlAM5KCkPo6kSM5GECSI/j+RA4j8OxUkaNh"
        "DlWRRFDoL63D4RhIkWPhEi6Q5EkSSQ7DuQIwRYMxIFMOI5kYOw+kINw5FDEwzxkP0ADi"
        "VBHkWO5BoCAOAAABAwABAAAAIAAAAAEBAwABAAAADgAAAAIBAwABAAAACAAAAAMBAwAB"
        "AAAABQAAAAYBAwABAAAAAQAAAAoBAwABAAAAAQAAABEBBAABAAAACAAAABIBAwABAAAA"
        "AQAAABUBAwABAAAAAQAAABYBAwABAAAADgAAABcBBAABAAAA/gEAABwBAwABAAAAAQAA"
        "ACkBAwACAAAAAAABAD0BAwABAAAAAQAAAAAAAAA="),
    # tr2.gif  49 B  sha256=a8aa1c21aa1a2a091e8882007828f00c09371f3cae4298b1aeb48cdc575a33f5
    "gif_transparente": (
        "R0lGODlhCAAEAPAAAAAAAP8AACH5BAEAAAAALAAAAAAIAAQAAAIIjAMJh8q6DiwAOw=="),
}

SHA256_TESTIGOS = {
    "tiff_gris_plano":
        "473f9449ce33e6e5048c85adb451e3fa9242954b58a49ecbb36457ab5f8d979c",
    "tiff_gris_lzw":
        "33af940e2383d3a1bfb250e7765a86b7107736bf61cf3ce358ae102fd5566d31",
    "gif_transparente":
        "a8aa1c21aa1a2a091e8882007828f00c09371f3cae4298b1aeb48cdc575a33f5",
}


def testigo(nombre):
    return base64.b64decode(TESTIGOS[nombre])

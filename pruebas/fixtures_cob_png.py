"""Fixtures del carril `cob/png`: PNG construidos byte a byte y un
decodificador de REFERENCIA independiente que sirve de oraculo.

Por que codigo y no bytes en `corpus/`
--------------------------------------
`corpus/` esta en Git LFS. Meter aqui una docena de PNG costaria cuota (1 GB
de ancho de banda al mes contra un corpus de 254 MB, trampa 103) y arrastraria
la trampa 34 a cada *worktree* nuevo: 15 rojos que no son de nadie. Estos
ficheros se construyen con `zlib` y `struct` de la biblioteca estandar, son
texto versionable, deterministas y no necesitan red.

Por que un decodificador de referencia
--------------------------------------
`filex/verificador.py` decodifica PNG **a mano** y por un carril: en vez de
reconstruir la imagen entera extrae uno de cada `bpp` bytes (el del alfa) y lo
desfiltra por su cuenta. Es rapido y es correcto, pero un error de bit ahi
**no lanza excepcion: devuelve un numero**, y ese numero es el veredicto del
punto 1 del contrato (trampa 1, el «alfa trivial»). Una prueba que solo
comprueba que no hay excepcion no juzga nada.

El oraculo de aqui reconstruye la imagen COMPLETA con el algoritmo de libro
(RFC 2083 §6, desfiltrado por `bpp` sobre la fila entera) y saca el alfa de los
pixeles ya reconstruidos. Es lento y evidente; el del verificador es rapido y
sutil. Son dos implementaciones distintas del mismo contrato, y por eso una
puede juzgar a la otra.

**No importa NADA de `filex.verificador`** — ni `_paeth`. Si lo hiciera, un
error en el sujeto se cancelaria con el mismo error en el oraculo.
"""

from __future__ import annotations

import binascii
import struct
import zlib

FIRMA = b"\x89PNG\r\n\x1a\n"

# Canales por tipo de color (IHDR byte 9), norma PNG.
CANALES = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}

# (xini, yini, xpaso, ypaso) de las siete pasadas de Adam7. Escrito aqui a
# proposito, aunque `verificador._ADAM7` tenga la misma tabla: si el oraculo la
# importara, un error en la tabla del sujeto seria invisible.
ADAM7 = ((0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
         (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2))


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------

def trozo(tipo: bytes, datos: bytes) -> bytes:
    """Un chunk PNG con su longitud y su CRC-32 bien puestos."""
    return (struct.pack(">I", len(datos)) + tipo + datos
            + struct.pack(">I", binascii.crc32(tipo + datos) & 0xFFFFFFFF))


def _empaqueta_fila(muestras, ct, bd):
    """Serializa una fila de PIXELES a los bytes crudos de la scanline.

    `muestras` es una lista de pixeles; cada pixel es un entero (ct 0 y 3) o
    una tupla de canales (ct 2, 4 y 6), con los valores ya en el rango de `bd`.
    """
    canales = CANALES[ct]
    planos = []
    for px in muestras:
        if canales == 1:
            planos.append(px if isinstance(px, int) else px[0])
        else:
            planos.extend(px)
    if bd == 16:
        return b"".join(struct.pack(">H", v) for v in planos)
    if bd == 8:
        return bytes(planos)
    # 1, 2 o 4 bits: MSB primero, la fila se rellena hasta el byte.
    por_byte = 8 // bd
    out = bytearray()
    acc = 0
    n = 0
    for v in planos:
        acc = (acc << bd) | (v & ((1 << bd) - 1))
        n += 1
        if n == por_byte:
            out.append(acc)
            acc = 0
            n = 0
    if n:
        out.append(acc << (bd * (por_byte - n)))
    return bytes(out)


def _paeth_ref(a, b, c):
    """Predictor Paeth de la norma, escrito aparte del que usa el sujeto."""
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _filtra_fila(filtro, cruda, previa, bpp):
    """Lado ENCODER de los cinco filtros (RFC 2083 §6)."""
    out = bytearray(len(cruda))
    for j in range(len(cruda)):
        a = cruda[j - bpp] if j >= bpp else 0
        b = previa[j]
        c = previa[j - bpp] if j >= bpp else 0
        x = cruda[j]
        if filtro == 0:
            out[j] = x
        elif filtro == 1:
            out[j] = (x - a) & 255
        elif filtro == 2:
            out[j] = (x - b) & 255
        elif filtro == 3:
            out[j] = (x - ((a + b) >> 1)) & 255
        elif filtro == 4:
            out[j] = (x - _paeth_ref(a, b, c)) & 255
        else:
            raise ValueError("filtro %r" % filtro)
    return bytes(out)


def bpp_de(ct, bd):
    """Bytes por pixel para el filtrado (>= 1), segun la norma."""
    return max(1, CANALES[ct] * bd // 8)


def _scanlines(pixeles, ct, bd, filtros):
    """Convierte una rejilla de pixeles en el flujo `filtro || fila filtrada`."""
    ancho_bytes = None
    previa = None
    out = bytearray()
    bpp = bpp_de(ct, bd)
    for y, fila in enumerate(pixeles):
        cruda = _empaqueta_fila(fila, ct, bd)
        if ancho_bytes is None:
            ancho_bytes = len(cruda)
            previa = bytes(ancho_bytes)
        f = filtros[y % len(filtros)] if filtros else 0
        out.append(f)
        out += _filtra_fila(f, cruda, previa, bpp)
        previa = cruda
    return bytes(out)


def filas_adam7(an, al):
    """Cuantas sub-filas emite Adam7 para una imagen de an x al."""
    n = 0
    for xini, yini, xpaso, ypaso in ADAM7:
        anp = (an - xini + xpaso - 1) // xpaso
        alp = (al - yini + ypaso - 1) // ypaso
        if anp > 0 and alp > 0:
            n += alp
    return n


def _reparte_adam7(pixeles, an, al):
    """Las siete sub-imagenes de Adam7, en orden de pasada."""
    pasadas = []
    for xini, yini, xpaso, ypaso in ADAM7:
        sub = [[pixeles[y][x] for x in range(xini, an, xpaso)]
               for y in range(yini, al, ypaso)]
        sub = [f for f in sub if f]
        pasadas.append(sub)
    return pasadas


def png(pixeles, ct, bd, *, plte=None, trns=None, entrelazado=0, filtros=(0,),
        sin_idat=False, trocea=1, recorta_idat=None, extra=()):
    """PNG completo. `pixeles` es una rejilla [alto][ancho] de pixeles.

    - `filtros`: filtro de fila a aplicar, ciclico (para ejercitar los cinco).
    - `trocea`: en cuantos IDAT se parte el flujo comprimido.
    - `recorta_idat`: si no es None, se emiten solo esos bytes comprimidos
      (IDAT incompleto, para el camino de error).
    - `extra`: trozos ya serializados que se insertan antes del PLTE.
    """
    al = len(pixeles)
    an = len(pixeles[0]) if al else 0
    ihdr = struct.pack(">IIBBBBB", an, al, bd, ct, 0, 0, entrelazado)
    fuera = bytearray(FIRMA)
    fuera += trozo(b"IHDR", ihdr)
    for t in extra:
        fuera += t
    if plte is not None:
        fuera += trozo(b"PLTE", b"".join(bytes(c) for c in plte))
    if trns is not None:
        fuera += trozo(b"tRNS", bytes(trns))
    if not sin_idat:
        if entrelazado:
            crudo = b"".join(
                _scanlines(sub, ct, bd, filtros) for sub in _reparte_adam7(pixeles, an, al)
                if sub)
        else:
            crudo = _scanlines(pixeles, ct, bd, filtros)
        comprimido = zlib.compress(crudo, 6)
        if recorta_idat is not None:
            comprimido = comprimido[:recorta_idat]
        paso = max(1, (len(comprimido) + trocea - 1) // trocea)
        for i in range(0, len(comprimido), paso):
            fuera += trozo(b"IDAT", comprimido[i:i + paso])
        if not comprimido:
            fuera += trozo(b"IDAT", b"")
    fuera += trozo(b"IEND", b"")
    return bytes(fuera)


# ---------------------------------------------------------------------------
# Oraculo: decodificador de referencia
# ---------------------------------------------------------------------------

def _trozos(datos):
    i = len(FIRMA)
    while i + 8 <= len(datos):
        ln = struct.unpack(">I", datos[i:i + 4])[0]
        tipo = datos[i + 4:i + 8]
        yield tipo, datos[i + 8:i + 8 + ln]
        i += 12 + ln


def _desfiltra_ref(filtro, filt, previa, bpp):
    """Desfiltrado de libro: fila COMPLETA, con `bpp` de distancia al vecino."""
    out = bytearray(len(filt))
    for j in range(len(filt)):
        a = out[j - bpp] if j >= bpp else 0
        b = previa[j]
        c = previa[j - bpp] if j >= bpp else 0
        x = filt[j]
        if filtro == 0:
            out[j] = x
        elif filtro == 1:
            out[j] = (x + a) & 255
        elif filtro == 2:
            out[j] = (x + b) & 255
        elif filtro == 3:
            out[j] = (x + ((a + b) >> 1)) & 255
        elif filtro == 4:
            out[j] = (x + _paeth_ref(a, b, c)) & 255
        else:
            raise ValueError("filtro %r" % filtro)
    return out


def _muestras_de_fila(fila, an, ct, bd):
    """Devuelve [ [canal, ...] por pixel ] de una scanline ya desfiltrada."""
    canales = CANALES[ct]
    if bd == 16:
        vals = list(struct.unpack(">%dH" % (an * canales), bytes(fila[:an * canales * 2])))
    elif bd == 8:
        vals = list(fila[:an * canales])
    else:
        por_byte = 8 // bd
        masc = (1 << bd) - 1
        vals = []
        for k in range(an * canales):
            octeto = fila[k // por_byte]
            vals.append((octeto >> (8 - bd * (k % por_byte + 1))) & masc)
    return [vals[i * canales:(i + 1) * canales] for i in range(an)]


def decodifica(datos):
    """Devuelve (an, al, ct, bd, entrelazado, plte, trns, pixeles) con
    `pixeles[y][x]` = lista de canales ya reconstruida."""
    an = al = bd = ct = ent = None
    plte = None
    trns = None
    idat = bytearray()
    for tipo, cuerpo in _trozos(datos):
        if tipo == b"IHDR":
            an, al, bd, ct, _, _, ent = struct.unpack(">IIBBBBB", cuerpo)
        elif tipo == b"PLTE":
            plte = [tuple(cuerpo[i:i + 3]) for i in range(0, len(cuerpo) - 2, 3)]
        elif tipo == b"tRNS":
            trns = cuerpo
        elif tipo == b"IDAT":
            idat += cuerpo
        elif tipo == b"IEND":
            break
    crudo = zlib.decompress(bytes(idat))
    canales = CANALES[ct]
    bpp = bpp_de(ct, bd)
    pixeles = [[None] * an for _ in range(al)]
    pos = 0

    def una_pasada(x0, y0, dx, dy):
        nonlocal pos
        anp = (an - x0 + dx - 1) // dx
        alp = (al - y0 + dy - 1) // dy
        if anp <= 0 or alp <= 0:
            return
        tam = (anp * canales * bd + 7) // 8
        previa = bytearray(tam)
        for j in range(alp):
            filtro = crudo[pos]
            filt = crudo[pos + 1:pos + 1 + tam]
            pos += 1 + tam
            fila = _desfiltra_ref(filtro, filt, previa, bpp)
            previa = fila
            for i, mu in enumerate(_muestras_de_fila(fila, anp, ct, bd)):
                pixeles[y0 + j * dy][x0 + i * dx] = mu

    if ent:
        for x0, y0, dx, dy in ADAM7:
            una_pasada(x0, y0, dx, dy)
    else:
        una_pasada(0, 0, 1, 1)
    return an, al, ct, bd, ent, plte, trns, pixeles


def alfa_de(mu, ct, bd, trns):
    """Alfa CRUDO (en la escala del formato) de un pixel ya reconstruido."""
    if ct == 6:
        return mu[3]
    if ct == 4:
        return mu[1]
    if ct == 3:
        idx = mu[0]
        return trns[idx] if trns is not None and idx < len(trns) else 255
    raise AssertionError("ct=%d no tiene canal alfa" % ct)


def referencia(datos):
    """min(alfa) y `primer_transparente` esperados, calculados sobre la imagen
    reconstruida entera.

    `primer_transparente` reproduce la regla que el verificador documenta: la
    PRIMERA fila (en el orden en que el decodificador la recorre: por filas si
    no hay entrelazado, por pasadas si lo hay) que baja el minimo corriente, y
    dentro de ella la primera columna que vale ese minimo de fila.
    """
    an, al, ct, bd, ent, plte, trns, px = decodifica(datos)
    tope = 255 if ct == 3 else (1 << bd) - 1
    mn = tope
    primero = None

    def mira_fila(coords):
        """coords: lista de (x, y) de una fila logica, en orden."""
        nonlocal mn, primero
        vals = [alfa_de(px[y][x], ct, bd, trns) for x, y in coords]
        if not vals:
            return
        v = min(vals)
        if v < mn:
            mn = v
            if primero is None:
                primero = coords[vals.index(v)]

    if ent:
        for x0, y0, dx, dy in ADAM7:
            anp = (an - x0 + dx - 1) // dx
            alp = (al - y0 + dy - 1) // dy
            if anp <= 0 or alp <= 0:
                continue
            for j in range(alp):
                mira_fila([(x0 + i * dx, y0 + j * dy) for i in range(anp)])
    else:
        for y in range(al):
            mira_fila([(x, y) for x in range(an)])
    n_bajo_tope = sum(1 for y in range(al) for x in range(an)
                      if alfa_de(px[y][x], ct, bd, trns) < tope)
    return {"alfa_min": mn / float(tope), "crudo": mn, "tope": tope,
            "primer_transparente": primero, "n_transparentes": n_bajo_tope,
            "ancho": an, "alto": al}


def mapa_alfa(datos):
    """(rejilla de alfa CRUDO por pixel, tope). Sirve para juzgar que la
    coordenada `primer_transparente` apunta de verdad a un pixel transparente,
    invariante que vale bajo cualquier lectura del campo."""
    an, al, ct, bd, ent, plte, trns, px = decodifica(datos)
    tope = 255 if ct == 3 else (1 << bd) - 1
    return [[alfa_de(px[y][x], ct, bd, trns) for x in range(an)]
            for y in range(al)], tope


# ---------------------------------------------------------------------------
# Rejillas de pixeles de conveniencia
# ---------------------------------------------------------------------------

def rejilla(an, al, hacer):
    return [[hacer(x, y) for x in range(an)] for y in range(al)]


def rgba_opaco(an, al, bd=8):
    tope = (1 << bd) - 1
    return rejilla(an, al, lambda x, y: (x % (tope + 1), y % (tope + 1),
                                         (x + y) % (tope + 1), tope))


def rgba_con_hueco(an, al, hx, hy, alfa, bd=8):
    """Opaco salvo un pixel, en (hx, hy), con alfa `alfa`. Trampa 1: aqui el
    alfa NO es trivial, `min(alfa) < 1.0` de verdad."""
    tope = (1 << bd) - 1
    return rejilla(an, al, lambda x, y: (
        (x * 7) % (tope + 1), (y * 5) % (tope + 1), (x + y) % (tope + 1),
        alfa if (x, y) == (hx, hy) else tope))


def gris_alfa_con_hueco(an, al, hx, hy, alfa, bd=8):
    tope = (1 << bd) - 1
    return rejilla(an, al, lambda x, y: ((x * 3) % (tope + 1),
                                         alfa if (x, y) == (hx, hy) else tope))


def indices(an, al, hacer):
    return rejilla(an, al, hacer)


# ---------------------------------------------------------------------------
# Oraculo de los predictores VP8L (WebP sin perdida)
# ---------------------------------------------------------------------------
#
# Reescritos desde la especificacion de libwebp (`dec/vp8l_dec.c`,
# `dsp/lossless.c`), canal a canal y con aritmetica explicita, para poder
# juzgar los de `verificador.py` sin copiarlos.

def _canales_argb(v):
    return ((v >> 24) & 0xFF, (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF)


def _de_canales(c):
    return (c[0] << 24) | (c[1] << 16) | (c[2] << 8) | c[3]


def med2_ref(a, b):
    """Average2 de libwebp, canal a canal (media entera hacia abajo)."""
    return _de_canales([(x + y) >> 1 for x, y in zip(_canales_argb(a),
                                                     _canales_argb(b))])


def selecciona_ref(a, b, c):
    ca, cb, cc = _canales_argb(a), _canales_argb(b), _canales_argb(c)
    d = sum(abs(cb[k] - cc[k]) - abs(ca[k] - cc[k]) for k in range(4))
    return a if d <= 0 else b


def _clip255(x):
    return 0 if x < 0 else (255 if x > 255 else x)


def clamp_full_ref(a, b, c):
    ca, cb, cc = _canales_argb(a), _canales_argb(b), _canales_argb(c)
    return _de_canales([_clip255(ca[k] + cb[k] - cc[k]) for k in range(4)])


def _mitad_c(a, b):
    """`a + (a - b) / 2` con la division ENTERA DE C: trunca hacia cero.

    Python trunca hacia -infinito, asi que `(a - b) // 2` NO es lo mismo
    cuando `a - b` es negativo e impar. Esa diferencia es el defecto D2 del
    informe `bench/cobertura-png.md`.
    """
    d = a - b
    q = int(d / 2) if d >= 0 else -((-d) // 2)
    return _clip255(a + q)


def clamp_half_ref(a, b, c):
    """ClampedAddSubtractHalf(Average2(a, b), c) de libwebp."""
    m = _canales_argb(med2_ref(a, b))
    cc = _canales_argb(c)
    return _de_canales([_mitad_c(m[k], cc[k]) for k in range(4)])


def predice_ref(modo, L, T, TL, TR):
    if modo == 0:
        return 0xFF000000
    if modo == 1:
        return L
    if modo == 2:
        return T
    if modo == 3:
        return TR
    if modo == 4:
        return TL
    if modo == 5:
        return med2_ref(med2_ref(L, TR), T)
    if modo == 6:
        return med2_ref(L, TL)
    if modo == 7:
        return med2_ref(L, T)
    if modo == 8:
        return med2_ref(TL, T)
    if modo == 9:
        return med2_ref(T, TR)
    if modo == 10:
        return med2_ref(med2_ref(L, TL), med2_ref(T, TR))
    if modo == 11:
        return selecciona_ref(T, L, TL)
    if modo == 12:
        return clamp_full_ref(L, T, TL)
    if modo == 13:
        return clamp_half_ref(L, T, TL)
    raise ValueError("predictor VP8L %d desconocido" % modo)


# Los OCHO primeros codigos de plano de `kCodeToPlane` (libwebp,
# `dec/vp8l_dec.c`), en su forma cruda: `dist = (cod >> 4) * xsize + (8 - (cod & 15))`.
# Solo ocho: son los que se pueden citar con seguridad, y basta para juzgar el
# ORDEN del generador, que es lo unico que `_codigo_a_plano()` decide.
KCODE_A_PLANO_8 = (0x18, 0x07, 0x17, 0x19, 0x28, 0x06, 0x27, 0x29)


def distancia_plano_ref(xsize, cod_crudo):
    y = cod_crudo >> 4
    x = 8 - (cod_crudo & 0xF)
    d = y * xsize + x
    return d if d >= 1 else 1

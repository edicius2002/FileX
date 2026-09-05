"""Fixtures del carril de cobertura de WebP/VP8L (`bench/cobertura-webp.md`).

**Los bytes NO son míos.** Los trece ficheros WebP de este módulo los escribió
**libwebp 1.6.0** a través de `magick` 7.1.2 Q16-HDRI, y van empotrados como
literal base64 con su `sha256` declarado. Es la disciplina de la trampa 71 —*el
árbitro del triaje no puede ser quien escribió el fichero*—: si los construyera
yo a mano estaría midiendo mi generador en vez del decodificador de FileX.
No van a `corpus/` a propósito: son 6 672 B y `corpus/` es Git LFS (cuota de
1 GB/mes, trampa 103) y arrastra la trampa 34 (punteros de 130 B en un worktree
nuevo).

**La excepción, y su control positivo.** Las ramas de ERROR del decodificador no
se pueden alcanzar con un fichero que libwebp acepte escribir, así que hay un
escritor de flujos VP8L a mano (`Bits`, `vp8l_solido`, `codigo_normal`). Para que
sus flujos malformados signifiquen algo hay que demostrar antes que el escritor
produce VP8L de verdad: `vp8l_solido()` genera un flujo VÁLIDO y
`test_control_positivo_del_escritor` comprueba que **magick lo lee igual que
FileX**. Sin ese control, un «falla como se esperaba» no se distingue de «mi
generador escribe basura» (trampas 81 y 91).

Las órdenes exactas que reprodujeron cada blob están en
`bench/salidas-cobertura-webp/MANIFIESTO.md`.
"""

from __future__ import annotations

import base64
import hashlib

_b64decode = base64.b64decode


# 48x64 sin perdida: predictor + color cruzado + restar verde, con referencias hacia atras y cache de color
# 414 B, sha256 dcbcb3a2fb913af184239a94c2cd2f8abb9964f8acf6b95d608ca7e227aee46f
_B64_LL_TRANSFORMACIONES = (
    "UklGRpYBAABXRUJQVlA4TIoBAAAvL8APEM1VIKL/sRnwKHj/YxyQI0mSFDUiIB5/kGoRAPHQ4OwqrGrPZ05Mws6/"
    "gKDI/9GURrLVnCcWFy1lMWiG8r4nOnLbyJF6TrOhil0d33A5Sp4jHOAD9iB1Og68wX6p1bGDwbJfrY4TZ7DhxOl0"
    "nGGwMZyh0bGFO8NsodExWMbYjQ4mN3XHBkJbbMCuO0jY2Ia6I76ayd3gYAtJ1ae3usNn9tQ8MQx1Bz6BpMWEcao7"
    "zI4naSH2o+4ADqAFCOPU4LCP3A2sdhy3usPgrJNucCT1DOa6I7r7EsBkSNLUHbGY0V93ECnhdw0OG9L+Vh2xjp0J"
    "4ji1JfjEQH3p8nGyoej4EwV6Ph51RxzfhvH/UwXCGaroSOtY3P8+NVA0RH/dEX6a+OuOtP4X1Yv+YlcdTwINulYo"
    "O9L+XjQkrQ2OmA4PiqR/1x2J+yIlSXrVHTj8aiBTW+uOME6N95dknNoc7zBO77qj/T73iffFi2Ryq9Ex8GB4Nzp0"
    "UQCsTsdgDpZNq0MXtcG2+hwC"
)
LL_TRANSFORMACIONES = _b64decode(_B64_LL_TRANSFORMACIONES)

# 32x32 sin perdida con imagen meta-Huffman (mas de un grupo de codigos)
# 2410 B, sha256 925e9c5abebcf26ff9ab1b3c57097ae5ddc02f691902c12dba3affd39a495e77
_B64_LL_META_HUFFMAN = (
    "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"
)
LL_META_HUFFMAN = _b64decode(_B64_LL_META_HUFFMAN)

# 32x32 de 24 colores: transformacion de paleta con bits=0 (un indice por pixel)
# 742 B, sha256 d7f48076a5a2e33e5334ee2cc8f601406dbe574302476ee52ffa63cd5c284466
_B64_LL_PALETA_ANCHA = (
    "UklGRt4CAABXRUJQVlA4TNICAAAvH8AHEL/ANACANHhyOIHEqftqbR+4S1p3fYNNbFuNkAAGGEo0YAFV2EBNDjUl"
    "gwLauHnZBACYZJrCQ7hcSDeCEIQQrhcFuDgZsyixyv7KlSKisPgkko/67e8HxTdaPzQoo1K6AX9nLoyTr9BGI+ot"
    "/RARTQrK59vKB219cPGBwgBA2bys0DBCEf0PtCQWR1vQNlVOFjc8vnt1dwoWn+F+OaDEDyN9W228OFxvNpybw+jR"
    "2zjbwKc/Xvb9qVdwaFfcQ8o54ZEQPNZ7I/OY4ascS5qIiO3Q8pXGYRV7UGvcPzrWfOisFr3/WdEIHBLleUe3Dy7l"
    "O7j7cJyBMCsvXJVXisSJ5HjsPsDdt66Gxc6KFNKKw5mV1SAVfE2OByTDDRuDhUnFe/GNT9PvJQ/yyX4kzdsold/9"
    "VmrCe52RcAwa4lh7Wt97smtE4wz9CL/sMcf5EBbfPPeJvt4AmK/LucvcU25cu8SDZBYvzeBnbzyQtCORk/7cMdfu"
    "T5JEIl5Wpo32vWu9/wKu6t/bhkDrRkuKSga1y43uZfCwQIdbCP+6r4vxcu+WZ9JzZ5V5mgKfM/1Sn6VaN1HWp2j7"
    "yl8UeJhmWf8+aukQIRG1ZASBQIjZ5nmup/yIWwZ4r3IxXcoWk6/GrDQE82nEX33S8prj1jq0WDmiVXIE8LLoTgi+"
    "gmumBVlXeSNoMO/e+tRLRymxhzqHrffC/G9LPoclCno2KA7RFsF2xxryUSLQIEZYqOYCoKH5xUipfJ2N136ZI/Ii"
    "slTgELl+501otpbJj6mJEMVK87t13gQ91yp+vwz6uXgy4en05JrztFn/ZJ14w6QwJVJJk9LNi8Lf/eYclGhTHJBb"
    "ykgHlRdgT02Lw+h5zi4MpVdOvdAFZv1nev3N0S5NG8dM42i7zb4p2s8z0eDgtRN7zxdbY0pOR7t9R9r1GZo2OfCe"
    "jRaneQnVxii9uXWUBmTtOA=="
)
LL_PALETA_ANCHA = _b64decode(_B64_LL_PALETA_ANCHA)

# 16x16 de 3 colores: paleta con bits=3 (ocho indices por byte)
# 56 B, sha256 ae2f9e78f0d16d817b34ebb0b94b4eb80c3221ffd7f48b39beeb6d62ff236cf4
_B64_LL_PALETA_EMPAQUETADA = (
    "UklGRjAAAABXRUJQVlA4TCQAAAAvD8ADEBcw/wKCIv9HCwFB0XXLBfyCQIAwadKpg4j+T4DWww4="
)
LL_PALETA_EMPAQUETADA = _b64decode(_B64_LL_PALETA_EMPAQUETADA)

# 24x16 sin perdida y sin alfa: atajo por cabecera (alpha_is_used=0)
# 44 B, sha256 8c2e6594f8e8a03d225e8a03b212be34a8cb2f5a942083204e743cf5035346a3
_B64_LL_OPACO = (
    "UklGRiQAAABXRUJQVlA4TBgAAAAvF8ADAA8Q8x/zHwaxYDJ/6f4IIvqfvQA="
)
LL_OPACO = _b64decode(_B64_LL_OPACO)

# 64x64 damero con alfa en rampa vertical
# 104 B, sha256 3fdc38a792a8d3ec0fad10b750801c907b5a2ca9ce3121ab86c5153d685b32d4
_B64_LL_DAMERO = (
    "UklGRmAAAABXRUJQVlA4TFMAAAAvP8APEM2VIaL/AQVt20jhNE7jtOM0XPf/d1KEgrQNWJQdRW7bNsruPqV/IKgt"
    "9hguhijwKl7XXQH8MVSMIPdV9bddIeTRRlG4jQyhYH/nvz8CAAA="
)
LL_DAMERO = _b64decode(_B64_LL_DAMERO)

# 24x24 sin perdida donde el predictor 13 de FileX se desvia de libwebp
# 1748 B, sha256 c69aaeb9be7b46d92f19824bd04cc4715cad6a8b17c9f71acc105f8b58784de9
_B64_DEFECTO_MODO13 = (
    "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"
)
DEFECTO_MODO13 = _b64decode(_B64_DEFECTO_MODO13)

# 24x16 con perdida y trozo ALPH SIN comprimir (compresion 0, filtro 0)
# 492 B, sha256 c4a824f079165d852442ef6eaa4b7b926c60fff5979d51a2152078c1b1542c4e
_B64_PERDIDA_ALPH_CRUDO = (
    "UklGRuQBAABXRUJQVlA4WAoAAAAQAAAAFwAADwAAQUxQSIEBAAAA////////////////////////////////7u7u"
    "7u7u7u7u7u7u7u7u7u7u7u7u7u7u3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3dzMzMzMzMzMzMzMzMzMzMzMzMzMzM"
    "zMzMu7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqmZmZmZmZmZmZmZmZmZmZ"
    "mZmZmZmZmZmZiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiId3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3ZmZmZmZmZmZm"
    "ZmZmZmZmZmZmZmZmZmZmVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVREREREREREREREREREREREREREREREREMzMz"
    "MzMzMzMzMzMzMzMzMzMzMzMzMzMzIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiERERERERERERERERERERERERERER"
    "ERERAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFZQOCA8AAAAMAMAnQEqGAAQAD5tLJFFpCKhmAQAQAbEoAuy6Afg"
    "AAhFAAD+8JtD/5BcsLrka//ID/kB/yA//j4LswAA"
)
PERDIDA_ALPH_CRUDO = _b64decode(_B64_PERDIDA_ALPH_CRUDO)

# 24x16 con perdida y trozo ALPH comprimido como VP8L, filtro 1
# 132 B, sha256 90af9001c17e3cc6e5be822c33eff67193b417ddceb781402b5b064ae7c4a053
_B64_PERDIDA_ALPH_VP8L = (
    "UklGRnwAAABXRUJQVlA4WAoAAAAQAAAAFwAADwAAQUxQSBoAAAAFFyAQSPKn3WCNiAgHgmyb7v7oB4jofwR2DFZQ"
    "OCA8AAAAMAMAnQEqGAAQAD5tLJFFpCKhmAQAQAbEoAuy6AfgAAhFAAD+8JtD/5BcsLrka//ID/kB/yA//j4LswAA"
)
PERDIDA_ALPH_VP8L = _b64decode(_B64_PERDIDA_ALPH_VP8L)

# 32x32 con perdida y alfa diagonal
# 152 B, sha256 a23e3dba78f486db703bc3e9d4917163f616e203ac7d0acd432efe8992c4c92d
_B64_PERDIDA_ALPH_DIAG = (
    "UklGRpAAAABXRUJQVlA4WAoAAAAQAAAAHwAAHwAAQUxQSB0AAAABuYzof0Bp2wZMOv6/vKwkYgIUBASAiDOsceOe"
    "FwBWUDggTAAAANADAJ0BKiAAIAA+kSSgTSWiI6IUALASCWkAB4/ojdeio0Tm/uR3cAD++iROtAqEIl7nG55E/0uD"
    "qZ4vMOm6WH4qObhBzcIOwH6SAAA="
)
PERDIDA_ALPH_DIAG = _b64decode(_B64_PERDIDA_ALPH_DIAG)

# 20x20 con perdida, alfa totalmente opaco
# 82 B, sha256 fcd8c1e64962b71d6e375f29d6010899d1b863ce7ef9863a974ca315cfc3c0f9
_B64_PERDIDA_ALPH_OPACO = (
    "UklGRkoAAABXRUJQVlA4ID4AAACwAwCdASoUABQAPi0Sh0KhoQ3+qgAMAWJaQAMwACpCoErqJmzZ4AD+/6u1fUub"
    "v/DVv3qdDk38CmK9foAAAA=="
)
PERDIDA_ALPH_OPACO = _b64decode(_B64_PERDIDA_ALPH_OPACO)

# 24x16 con perdida y sin trozo ALPH: retorno por cabecera
# 120 B, sha256 0d633403d72dab1d2929c1696696636664a649bd6caa18b2d2e49c99d52bf207
_B64_PERDIDA_SIN_ALFA = (
    "UklGRnAAAABXRUJQVlA4IGQAAADwAwCdASoYABAAPm0skkWkIqGYBABABsS0AFiNQD8AGb/gPJALCL2AAP7ylOt/"
    "XQ7QIfv/kFyuia/JW2wGfE//kB/yA/33Y8O/tJVR/6yPh39pKqHVmCFGJZDt5wwPXF0eAAAA"
)
PERDIDA_SIN_ALFA = _b64decode(_B64_PERDIDA_SIN_ALFA)

# 8x8 animado de DOS fotogramas (dos trozos ANMF)
# 200 B, sha256 f3bd903decae8b7da817e6134605cdb89ceef4485f3e51871fa4ace8f4dd1ba9
_B64_ANIMADO = (
    "UklGRsAAAABXRUJQVlA4WAoAAAACAAAABwAABwAAQU5JTQYAAAD/////AABBTk1GSAAAAAAAAAAAAAcAAAcAAGQA"
    "AAJWUDggMAAAANABAJ0BKggACAACADQloAJ0ugH4AAOwAP7wxAv/ILlhdcjX/yA/5Af8gP/48gAAAEFOTUZEAAAA"
    "AAAAAAAABwAABwAAZAAAAFZQOCAsAAAAlAEAnQEqCAAIAAAANCWgAnS6AAOYAP75k2//kB//kB//kB//ID/iF3sg"
    "MAA="
)
ANIMADO = _b64decode(_B64_ANIMADO)

# ---------------------------------------------------------------------------
# Manifiesto: nombre -> (tamaño, sha256). Se comprueba en la propia suite, así
# que un blob corrompido al editar sale como fallo y no como un CER plausible.
# ---------------------------------------------------------------------------

MANIFIESTO = {
    "LL_TRANSFORMACIONES": (414, "dcbcb3a2fb913af184239a94c2cd2f8abb9964f8acf6b95d608ca7e227aee46f"),
    "LL_META_HUFFMAN": (2410, "925e9c5abebcf26ff9ab1b3c57097ae5ddc02f691902c12dba3affd39a495e77"),
    "LL_PALETA_ANCHA": (742, "d7f48076a5a2e33e5334ee2cc8f601406dbe574302476ee52ffa63cd5c284466"),
    "LL_PALETA_EMPAQUETADA": (56, "ae2f9e78f0d16d817b34ebb0b94b4eb80c3221ffd7f48b39beeb6d62ff236cf4"),
    "LL_OPACO": (44, "8c2e6594f8e8a03d225e8a03b212be34a8cb2f5a942083204e743cf5035346a3"),
    "LL_DAMERO": (104, "3fdc38a792a8d3ec0fad10b750801c907b5a2ca9ce3121ab86c5153d685b32d4"),
    "DEFECTO_MODO13": (1748, "c69aaeb9be7b46d92f19824bd04cc4715cad6a8b17c9f71acc105f8b58784de9"),
    "PERDIDA_ALPH_CRUDO": (492, "c4a824f079165d852442ef6eaa4b7b926c60fff5979d51a2152078c1b1542c4e"),
    "PERDIDA_ALPH_VP8L": (132, "90af9001c17e3cc6e5be822c33eff67193b417ddceb781402b5b064ae7c4a053"),
    "PERDIDA_ALPH_DIAG": (152, "a23e3dba78f486db703bc3e9d4917163f616e203ac7d0acd432efe8992c4c92d"),
    "PERDIDA_ALPH_OPACO": (82, "fcd8c1e64962b71d6e375f29d6010899d1b863ce7ef9863a974ca315cfc3c0f9"),
    "PERDIDA_SIN_ALFA": (120, "0d633403d72dab1d2929c1696696636664a649bd6caa18b2d2e49c99d52bf207"),
    "ANIMADO": (200, "f3bd903decae8b7da817e6134605cdb89ceef4485f3e51871fa4ace8f4dd1ba9"),
}


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ===========================================================================
# Escritor de flujos VP8L a mano — SOLO para las ramas de error
# ===========================================================================
#
# Su control positivo vive en test_cob_webp.py: `vp8l_solido()` produce un flujo
# válido y magick lo lee igual que FileX. Ver el docstring de la cabecera.

class Bits:
    """Escritor de bits LSB primero, el orden que exige VP8L."""

    def __init__(self) -> None:
        self.b = bytearray()
        self.acc = 0
        self.n = 0

    def pon(self, v: int, k: int) -> "Bits":
        for i in range(k):
            self.acc |= ((v >> i) & 1) << self.n
            self.n += 1
            if self.n == 8:
                self.b.append(self.acc)
                self.acc = 0
                self.n = 0
        return self

    def fin(self) -> bytes:
        return bytes(self.b + bytearray([self.acc] if self.n else []))


def codigo_simple(w: Bits, sim: int, segundo: int | None = None,
                  ocho_bits: bool = True) -> Bits:
    """Código Huffman «simple» de VP8L: uno o dos símbolos, sin tabla."""
    w.pon(1, 1)                        # es un código simple
    w.pon(0 if segundo is None else 1, 1)   # n_simbolos - 1
    w.pon(1 if ocho_bits else 0, 1)    # el primer símbolo va en 8 bits o en 1
    w.pon(sim, 8 if ocho_bits else 1)
    if segundo is not None:
        w.pon(segundo, 8)
    return w


def codigo_dos_de_un_bit(w: Bits, n: int) -> Bits:
    """Código NORMAL (no simple) sobre `n` símbolos donde el 0 y el 256 valen
    un bit cada uno. Hace falta un código normal porque el símbolo 256 —el que
    abre una referencia hacia atrás— no cabe en los 8 bits del código simple.

    Se escribe con el alfabeto de LONGITUDES: dos símbolos de longitud 1 (el 1
    y el 18) y luego el 18 como repetición larga de ceros.
    """
    w.pon(0, 1)          # no es simple
    w.pon(0, 4)          # ncod = 4: cubre 17, 18, 0 y 1 de _ORDEN_LONG
    w.pon(0, 3)          # long. del símbolo 17 = 0
    w.pon(1, 3)          # long. del símbolo 18 = 1
    w.pon(0, 3)          # long. del símbolo 0  = 0
    w.pon(1, 3)          # long. del símbolo 1  = 1
    w.pon(0, 1)          # no se usa max_symbol
    # con esa tabla: bit 0 -> símbolo 1 (longitud 1); bit 1 -> símbolo 18
    w.pon(0, 1)                          # longitudes[0] = 1
    w.pon(1, 1); w.pon(127, 7)           # 138 ceros  -> índice 139
    w.pon(1, 1); w.pon(106, 7)           # 117 ceros  -> índice 256
    w.pon(0, 1)                          # longitudes[256] = 1
    resto = n - 257
    if resto:
        w.pon(1, 1); w.pon(resto - 11, 7)
    return w


def cabecera_vp8l(w: Bits, an: int, al: int, version: int = 0,
                  firma: int = 0x2F) -> Bits:
    w.pon(firma, 8)
    w.pon(an - 1, 14)
    w.pon(al - 1, 14)
    w.pon(1, 1)          # alpha_is_used
    w.pon(version, 3)
    return w


def vp8l_solido(an: int, al: int, a: int, r: int, g: int, b: int) -> bytes:
    """Flujo VP8L VÁLIDO: `an` x `al` píxeles, todos del color ARGB dado.

    Los cuatro códigos de canal son «simples» de un solo símbolo, y VP8L no
    consume ni un bit para leerlos, así que el flujo no lleva datos de píxel.
    """
    w = Bits()
    cabecera_vp8l(w, an, al)
    w.pon(0, 1)          # sin transformaciones
    w.pon(0, 1)          # sin caché de color
    w.pon(0, 1)          # sin meta-Huffman
    codigo_simple(w, g)
    codigo_simple(w, r)
    codigo_simple(w, b)
    codigo_simple(w, a)
    codigo_simple(w, 0, ocho_bits=False)      # código de distancias
    return w.fin()


def envolver_vp8l(vp8l: bytes) -> bytes:
    """Mete un flujo VP8L en un contenedor RIFF/WEBP mínimo."""
    cuerpo = b"VP8L" + len(vp8l).to_bytes(4, "little") + vp8l
    if len(vp8l) & 1:
        cuerpo += b"\x00"
    return b"RIFF" + (4 + len(cuerpo)).to_bytes(4, "little") + b"WEBP" + cuerpo


def envolver_alph(alph: bytes, an: int, al: int) -> bytes:
    """RIFF/WEBP con VP8X (que aporta las dimensiones) y un trozo ALPH."""
    vp8x = bytearray(10)
    vp8x[0] = 0x10                                   # bandera de alfa
    vp8x[4:7] = (an - 1).to_bytes(3, "little")
    vp8x[7:10] = (al - 1).to_bytes(3, "little")
    cuerpo = b"VP8X" + (10).to_bytes(4, "little") + bytes(vp8x)
    cuerpo += b"ALPH" + len(alph).to_bytes(4, "little") + alph
    if len(alph) & 1:
        cuerpo += b"\x00"
    return b"RIFF" + (4 + len(cuerpo)).to_bytes(4, "little") + b"WEBP" + cuerpo


def envolver_vp8x(alfa: bool, an: int, al: int) -> bytes:
    """RIFF/WEBP con VP8X y un VP8 con pérdida de relleno, SIN trozo ALPH.

    Es el único montaje en el que la bandera de alfa de VP8X decide sola: en
    cuanto hay un ALPH, `_webp` pone `tiene_alfa` por esa otra rama y estropear
    la bandera de VP8X deja de notarse (MEDIDO: esa mutación salía verde,
    `bench/cobertura-webp.md` §4).
    """
    vp8x = bytearray(10)
    vp8x[0] = 0x10 if alfa else 0x00
    vp8x[4:7] = (an - 1).to_bytes(3, "little")
    vp8x[7:10] = (al - 1).to_bytes(3, "little")
    relleno = bytes(16)
    cuerpo = b"VP8X" + (10).to_bytes(4, "little") + bytes(vp8x)
    cuerpo += b"VP8 " + len(relleno).to_bytes(4, "little") + relleno
    return b"RIFF" + (4 + len(cuerpo)).to_bytes(4, "little") + b"WEBP" + cuerpo


def mutar_cabecera_alph(datos: bytes, preproc: int | None = None,
                        filtro: int | None = None,
                        compresion: int | None = None) -> bytes:
    """Cambia SOLO el nibble de control del trozo ALPH y deja los bytes del
    plano tal y como los escribió libwebp. Así el árbitro sigue siendo externo:
    magick vuelve a leer el fichero mutado y aplica el mismo desfiltrado."""
    b = bytearray(datos)
    i = 12
    while i + 8 <= len(b):
        tipo = bytes(b[i:i + 4])
        ln = int.from_bytes(b[i + 4:i + 8], "little")
        if tipo == b"ALPH":
            c = b[i + 8]
            if preproc is not None:
                c = (c & ~0x30) | ((preproc & 3) << 4)
            if filtro is not None:
                c = (c & ~0x0C) | ((filtro & 3) << 2)
            if compresion is not None:
                c = (c & ~0x03) | (compresion & 3)
            b[i + 8] = c
            return bytes(b)
        i += 8 + ln + (ln & 1)
    raise AssertionError("el fichero no tiene trozo ALPH")


def trozo(datos: bytes, tipo: bytes) -> bytes | None:
    """Devuelve el cuerpo del primer trozo RIFF del tipo pedido."""
    i = 12
    while i + 8 <= len(datos):
        t = datos[i:i + 4]
        ln = int.from_bytes(datos[i + 4:i + 8], "little")
        if t == tipo:
            return datos[i + 8:i + 8 + ln]
        i += 8 + ln + (ln & 1)
    return None

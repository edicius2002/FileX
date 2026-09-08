"""Regresiones de CR-002: la duración presentada por ``elst``.

Los fixtures son cajas ISO-BMFF mínimas construidas en memoria.  No necesitan
FFmpeg ni aceleración hardware y permiten cubrir versiones 0/1 y entradas que
el verificador debe rechazar sin inventar una duración.
"""

from __future__ import annotations

import io
from pathlib import Path
import struct
import tempfile
import unittest

from filex import verificador as V


def _caja(tipo: bytes, contenido: bytes) -> bytes:
    return struct.pack(">I4s", len(contenido) + 8, tipo) + contenido


def _fullbox(version: int) -> bytes:
    return bytes((version, 0, 0, 0))


def _mvhd(escala: int, duracion: int) -> bytes:
    return _caja(b"mvhd", _fullbox(0) + struct.pack(">IIII", 0, 0, escala, duracion))


def _tkhd(duracion: int) -> bytes:
    contenido = bytearray(80)
    contenido[:4] = _fullbox(0)
    struct.pack_into(">I", contenido, 12, 1)  # track_ID
    struct.pack_into(">I", contenido, 20, duracion)
    return _caja(b"tkhd", bytes(contenido))


def _mdhd(version: int, escala: int, duracion: int) -> bytes:
    if version == 1:
        contenido = _fullbox(1) + struct.pack(">QQIQ", 0, 0, escala, duracion)
    else:
        contenido = _fullbox(0) + struct.pack(">IIII", 0, 0, escala, duracion)
    return _caja(b"mdhd", contenido)


def _hdlr() -> bytes:
    return _caja(b"hdlr", _fullbox(0) + struct.pack(">I4s", 0, b"soun"))


def _stsd_aac(escala: int) -> bytes:
    muestra = bytearray(36)
    struct.pack_into(">I4s", muestra, 0, len(muestra), b"mp4a")
    struct.pack_into(">H", muestra, 24, 2)
    struct.pack_into(">H", muestra, 26, 16)
    struct.pack_into(">I", muestra, 32, escala << 16)
    return _caja(b"stsd", _fullbox(0) + struct.pack(">I", 1) + bytes(muestra))


def _elst(version: int, entradas: list[tuple[int, int, int, int]], *, truncar=False) -> bytes:
    contenido = bytearray(_fullbox(version) + struct.pack(">I", len(entradas)))
    for duracion, tiempo_medio, entero, fraccion in entradas:
        formato = ">Qqhh" if version == 1 else ">Iihh"
        contenido.extend(struct.pack(formato, duracion, tiempo_medio, entero, fraccion))
    if truncar:
        del contenido[-2:]
    return _caja(b"elst", bytes(contenido))


def _archivo(*, version=0, elst: bytes | None, escala=44100, cruda=45124,
             presentada=1000) -> bytes:
    mdia = _caja(b"mdia", _mdhd(version, escala, cruda) + _hdlr() +
                 _caja(b"minf", _caja(b"stbl", _stsd_aac(escala))))
    edts = _caja(b"edts", elst) if elst is not None else b""
    trak = _caja(b"trak", _tkhd(presentada) + edts + mdia)
    return _caja(b"moov", _mvhd(1000, presentada) + trak)


def _sondear(datos: bytes) -> dict:
    with tempfile.TemporaryDirectory(prefix="cr002-bmff-") as td:
        ruta = Path(td) / "caso.m4a"
        ruta.write_bytes(datos)
        return V._isobmff(io.BytesIO(datos), str(ruta))


class DuracionPresentadaISOBMFF(unittest.TestCase):
    def test_elst_v0_publica_presentacion_y_conserva_media_cruda(self):
        d = _sondear(_archivo(elst=_elst(0, [(1000, 1024, 1, 0)])))
        pista = d["pistas"][0]
        self.assertAlmostEqual(pista["duracion_s"], 1.0, places=4)
        self.assertAlmostEqual(pista["duracion_media_s"], 45124 / 44100, places=9)
        self.assertEqual(pista["priming_muestras"], 1024)
        self.assertTrue(pista["duracion_presentada_evaluable"])

    def test_elst_v1_tambien_se_interpreta(self):
        d = _sondear(_archivo(
            version=1, escala=48000, cruda=49024, presentada=1000,
            elst=_elst(1, [(1000, 1024, 1, 0)]),
        ))
        pista = d["pistas"][0]
        self.assertEqual(pista["duracion_s"], 1.0)
        self.assertAlmostEqual(pista["duracion_media_s"], 49024 / 48000, places=9)
        self.assertEqual(pista["priming_muestras"], 1024)

    def test_sin_elst_mantiene_la_duracion_mdhd(self):
        pista = _sondear(_archivo(elst=None))["pistas"][0]
        self.assertEqual(pista["duracion_s"], round(45124 / 44100, 4))
        self.assertAlmostEqual(pista["duracion_media_s"], 45124 / 44100, places=9)
        self.assertTrue(pista["duracion_presentada_evaluable"])
        self.assertNotIn("priming_muestras", pista)

    def test_lista_multiple_o_vacia_no_inventa_una_duracion(self):
        for entradas in ([(1000, -1, 1, 0)], [(10, -1, 1, 0), (990, 0, 1, 0)]):
            with self.subTest(entradas=entradas):
                pista = _sondear(_archivo(elst=_elst(0, entradas)))["pistas"][0]
                self.assertFalse(pista["duracion_presentada_evaluable"])
                self.assertNotIn("duracion_s", pista)
                self.assertIn("edit list", pista["motivo_duracion_no_evaluable"])

    def test_elst_truncada_no_cae_silenciosamente_a_mdhd(self):
        pista = _sondear(_archivo(
            elst=_elst(0, [(1000, 1024, 1, 0)], truncar=True)
        ))["pistas"][0]
        self.assertFalse(pista["duracion_presentada_evaluable"])
        self.assertNotIn("duracion_s", pista)


if __name__ == "__main__":
    unittest.main()

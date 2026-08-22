"""Propiedades de los formatos. Lo que hace falta para PONER PRECIO a una arista.

El grafo no elige por número de saltos: elige por lo que se pierde. Para eso
necesita saber, de cada formato, tres cosas que no están en su extensión:

* **si admite texto** — es lo que convierte «rasterizar» en una pérdida y no en
  una implementación. Un camino que pasa por PNG para llegar a PDF entrega un
  PDF sin una sola letra seleccionable.
* **si tiene canal alfa y hasta cuántos bits** — de aquí salen 4 de las 17
  pérdidas catalogadas del patrón oro.
* **si es con pérdida** — encadenar dos etapas con pérdida es la recodificación
  que nadie pidió.

Las pérdidas de esta tabla NO son de catálogo: salen de
`bench/salidas-referencia/referencia.json` (17 pérdidas medidas, 39 órdenes
reproducibles) y de `bench/aristas-nominales.md`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Formato:
    ext: str
    categoria: str          # imagen | video | audio | documento | vectorial | datos
    texto: bool = False     # ¿puede llevar texto que se pueda seleccionar/extraer?
    alfa: bool = False
    prof_max: int = 8       # bits por canal
    perdida: bool = False   # ¿la codificación tira información por diseño?
    #: Nota MEDIDA que explica la pérdida cuando se llega a este formato.
    nota: str = ""


_F = [
    # --- imagen -----------------------------------------------------------
    Formato("png", "imagen", alfa=True, prof_max=16,
            nota="PNG admite 16 bits y ImageMagick los conserva (RMSE 0). "
                 "Si un conversor entrega 8 bits, es un FALLO del motor."),
    Formato("tif", "imagen", alfa=True, prof_max=16),
    Formato("tiff", "imagen", alfa=True, prof_max=16),
    Formato("webp", "imagen", alfa=True, prof_max=8, perdida=True,
            nota="WebP es de 8 bits: el TIFF de 16 pasó de 11.935.622 colores "
                 "únicos a 386.041. Con -define webp:lossless=true es exacto."),
    Formato("avif", "imagen", alfa=True, prof_max=12, perdida=True,
            nota="AVIF comprime el plano alfa CON PÉRDIDA: alfa a 46,0 dB, y un "
                 "alfa 100 % opaco se degrada a 71,4 dB."),
    Formato("jpg", "imagen", alfa=False, prof_max=8, perdida=True,
            nota="JPEG no tiene canal alfa ni más de 8 bits. El color de fondo "
                 "del aplanado SÍ es decisión del motor: ImageMagick usa NEGRO, "
                 "y lo esperable es blanco."),
    Formato("jpeg", "imagen", alfa=False, prof_max=8, perdida=True),
    Formato("gif", "imagen", alfa=True, prof_max=8, perdida=True,
            nota="256 colores. Y menor tamaño NO es mejor conversión: el GIF con "
                 "paleta genérica pesa un 35 % MENOS que el bueno."),
    Formato("bmp", "imagen", prof_max=8),
    Formato("ico", "imagen", alfa=True, prof_max=8),
    # --- vectorial --------------------------------------------------------
    Formato("svg", "vectorial", texto=True, alfa=True,
            nota="Rasterizar un SVG pierde el texto y NO lo dice: resvg entrega "
                 "un PNG válido, con la geometría exacta y 0,00 % de tinta en la "
                 "banda de texto, con rc=0."),
    # --- documento --------------------------------------------------------
    Formato("pdf", "documento", texto=True, alfa=True, prof_max=16),
    Formato("docx", "documento", texto=True),
    Formato("odt", "documento", texto=True),
    Formato("epub", "documento", texto=True),
    Formato("mobi", "documento", texto=True,
            nota="MOBI comprime el texto (PalmDoc/LZ77): un centinela NO aparece "
                 "literal en el binario aunque el libro esté entero. Una sonda de "
                 "texto ingenua lo da por destruido."),
    Formato("azw3", "documento", texto=True, nota="Ídem MOBI."),
    Formato("html", "documento", texto=True),
    Formato("md", "documento", texto=True),
    Formato("txt", "documento", texto=True),
    Formato("rtf", "documento", texto=True),
    # --- video ------------------------------------------------------------
    Formato("mp4", "video", perdida=True),
    Formato("mkv", "video", perdida=True),
    Formato("webm", "video", perdida=True),
    Formato("mov", "video", perdida=True),
    Formato("avi", "video", perdida=True),
    Formato("mpd", "video", perdida=True,
            nota="DASH: el .mpd es un MANIFIESTO, no el contenido. ffmpeg deja "
                 "528 KB de segmentos en el cwd y entrega 1,2 KB inútiles."),
    # --- audio ------------------------------------------------------------
    Formato("wav", "audio"),
    Formato("flac", "audio"),
    Formato("mp3", "audio", perdida=True),
    Formato("m4a", "audio", perdida=True),
    Formato("aac", "audio", perdida=True),
    Formato("opus", "audio", perdida=True,
            nota="Opus FUERZA 48 kHz y convierte 8,000 s en 8,0065 s: cualquier "
                 "tolerancia por debajo de ±10 ms da falsos fallos."),
    Formato("ogg", "audio", perdida=True),
    # --- datos ------------------------------------------------------------
    Formato("csv", "datos", texto=True),
    Formato("json", "datos", texto=True),
    Formato("tsv", "datos", texto=True),
]

FORMATOS: dict[str, Formato] = {f.ext: f for f in _F}

#: Alias que apuntan al mismo formato real.
ALIAS = {"jpeg": "jpg", "tiff": "tif", "htm": "html", "markdown": "md"}


def normaliza(ext: str) -> str:
    e = (ext or "").lower().lstrip(".")
    return ALIAS.get(e, e)


def formato(ext: str) -> Formato | None:
    return FORMATOS.get(normaliza(ext))


def conocido(ext: str) -> bool:
    return normaliza(ext) in FORMATOS

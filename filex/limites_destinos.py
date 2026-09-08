"""C28: límites del adaptador de ficheros, no capacidades del catálogo.

Fuentes: bench/aristas-escribibles.md §§1.5, 3, 5, 6 y
bench/mcp-cabos-y-techos.md §6. No añade aristas. Una ruta realmente
registrada prevalece: estos motivos explican únicamente la ausencia de camino.
"""

LIMITES = {
    "sup": ("fichero", "requiere subtítulos de mapa de bits; no hay adaptación sondeada"),
    "clip": ("metadatos", "extracción de metadatos de recorte, no conversión genérica de imagen"),
    "eml": ("fichero", "adaptador de correo no implementado; msgconvert histórico sin Email::Address"),
    "chk": ("paquete", "requiere cabecera y fragmentos WebM; el contrato de un fichero no admite el paquete"),
    "oeb": ("directorio", "Calibre produce un directorio; falta contrato de paquete y publicación atómica"),
    "rtsp": ("protocolo", "destino de red, no fichero local"),
    "sap": ("protocolo", "destino de red, no fichero local"),
}

for _token in ("ac4 aea avs3 bit c2 cavs cvg lbc rcv cavsvideo codec2 codec2raw evc gsm ilbc oma "
               "vc1 vc1test jacosub js mcc microdvd scc").split():
    LIMITES[_token] = ("fichero", "sin encoder integrado y sondeado para este destino; no implica imposibilidad del formato")

for _token in "dzi nia nii pml".split():
    LIMITES[_token] = ("fichero", "sin escritor integrado y sondeado para esta variante; FATE sólo aporta lectores")
for _token in "8bim 8bimtext app1 exif icc icm iptc iptctext mask matte thumbnail".split():
    LIMITES[_token] = ("metadatos", "extracción condicionada a metadatos de entrada; no es conversión genérica")
for _token in "8bimwtext app1jpeg iptcwtext".split():
    LIMITES[_token] = ("metadatos", "sondeo histórico sin salida incluso con rc=0; no hay capacidad registrada")
LIMITES["jpt"] = ("fichero", "variante no admitida por el delegado medido; JP2 no demuestra soporte JPT")


def motivo(destino: str) -> str:
    limite = LIMITES.get(destino)
    return f"C28 ({limite[0]}): {limite[1]}" if limite else ""

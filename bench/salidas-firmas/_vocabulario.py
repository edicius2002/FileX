# -*- coding: utf-8 -*-
"""F1 - Inventario del vocabulario: cuantos nombres de firma y cuantas extensiones,
antes y despues. Escribe vocabulario.json."""
import os, sys, json, inspect, re

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-firmas")
sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
sys.path.insert(0, os.path.join(RAIZ, r"bench\salidas-aristas"))
import verificador as V
import verificador_congelado as VC


# `ilegible`, `vacio` y `desconocido` NO son nombres de formato: son las tres
# respuestas de "no se". Se excluyen del recuento, que es como sale el 24 que
# publica bench/aristas-nominales.md sec.2 (sesgo 3).
CENTINELAS = {"ilegible", "vacio", "desconocido"}


def nombres(mod):
    """Todos los nombres de formato que `firma_real` de ese modulo puede devolver."""
    n = set(x[2] for x in mod.FIRMAS) | set(mod.MARCAS_FTYP.values())
    # el despacho RIFF, el texto y el 'isobmff' que es el valor por defecto del
    # .get() sobre MARCAS_FTYP (con el salen los 24 nombres que publica E1)
    n |= {"webp", "wav", "avi", "riff", "texto", "isobmff"}
    for f in ("firma_real", "_firma_texto", "_firma_zip", "_firma_cfb"):
        if hasattr(mod, f):
            n |= set(re.findall(r'return "([a-z0-9_]+)"',
                                inspect.getsource(getattr(mod, f))))
    for f in ("firma_real",):
        # los diccionarios en linea: {b"AIFF": "aiff", ...}
        n |= set(re.findall(r'b"[^"]{1,8}": "([a-z0-9_]+)"',
                            inspect.getsource(getattr(mod, f))))
    if hasattr(mod, "MARCAS_TEXTO"):
        n |= set(x[1] for x in mod.MARCAS_TEXTO)
    if hasattr(mod, "MIME_ZIP"):
        n |= set(mod.MIME_ZIP.values()) | set(x[1] for x in mod.OOXML)
    return {x for x in n if x} - CENTINELAS


if __name__ == "__main__":
    nv, nn = nombres(VC), nombres(V)
    ev, en = set(VC.EXT_A_FIRMAS), set(V.EXT_A_FIRMAS)
    d = {
        "nombres_viejo": sorted(nv), "n_nombres_viejo": len(nv),
        "nombres_nuevo": sorted(nn), "n_nombres_nuevo": len(nn),
        "nombres_anadidos": sorted(nn - nv), "n_anadidos": len(nn - nv),
        "ext_viejo": sorted(ev), "n_ext_viejo": len(ev),
        "ext_nuevo": sorted(en), "n_ext_nuevo": len(en),
        "n_ext_sin_firma": len(V.EXT_SIN_FIRMA),
        "ext_sin_firma": sorted(V.EXT_SIN_FIRMA),
        "n_ext_familia": len(V.EXT_FAMILIA),
        "n_magicos_viejo": len(VC.FIRMAS), "n_magicos_nuevo": len(V.FIRMAS),
        "n_ftyp_viejo": len(VC.MARCAS_FTYP), "n_ftyp_nuevo": len(V.MARCAS_FTYP),
    }
    print("nombres de firma : %d -> %d  (+%d)" % (d["n_nombres_viejo"], d["n_nombres_nuevo"], d["n_anadidos"]))
    print("magicos en tabla : %d -> %d" % (d["n_magicos_viejo"], d["n_magicos_nuevo"]))
    print("marcas ftyp      : %d -> %d" % (d["n_ftyp_viejo"], d["n_ftyp_nuevo"]))
    print("extensiones      : %d -> %d" % (d["n_ext_viejo"], d["n_ext_nuevo"]))
    print("ext SIN firma    : %d (categoria 3, punto 1 NO APLICA)" % d["n_ext_sin_firma"])
    print("ext de FAMILIA   : %d" % d["n_ext_familia"])
    json.dump(d, open(os.path.join(SAL, "vocabulario.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("\nescrito vocabulario.json")

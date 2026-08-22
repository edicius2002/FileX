# -*- coding: utf-8 -*-
"""F1 / paso 3b - LAS TRES CATEGORIAS SOBRE LOS 502 DESTINOS DECLARADOS.

  1  EVALUABLE Y LO EVALUAMOS   : hay marcador y el verificador lo conoce
  2  EVALUABLE Y NO LO EVALUAMOS: hay marcador y falta la entrada  -> DEUDA
  3  NO EVALUABLE POR NATURALEZA: no hay marcador                  -> NO APLICA
  -  INDETERMINADO              : no se pudo escribir el formato, o la muestra no
                                  describe el formato porque el motor escribio
                                  OTRA COSA. Se declara, no se rellena.

Se calcula DOS VECES: con el vocabulario viejo (verificador_congelado.py, 24
nombres, 30 extensiones) y con el ampliado. La diferencia entre las dos columnas
es lo que ha comprado la ampliacion.

Uso: python _categorias.py
Escribe categorias.json
"""
import os, sys, json
from collections import Counter, defaultdict

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-firmas")
sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
sys.path.insert(0, os.path.join(RAIZ, r"bench\salidas-aristas"))
import verificador as V
import verificador_congelado as VC

# --- CURACION, con su motivo. La medida es la evidencia; estas 3 listas son las
# --- correcciones que la medida no puede hacer sola, y cada una lleva su razon.

# (a) La muestra NO describe el formato: el motor devolvio rc=0 y escribio OTRA
#     COSA (un PNG). Es el fallo emblematico del proyecto reproducido 22 veces.
#     No se puede deducir de ahi si el formato tiene marcador: queda indeterminado.
ESCRIBIO_OTRA_COSA = set(
    "b c g k m o r y p7 preview clipboard data flif group4 histogram inline msl "
    "mvg null pocketmod sparse vid".split())

# (b) Familias P1..P7 y PF/Pf: el marcador existe (una letra y un digito de un
#     conjunto cerrado) pero NO es un prefijo constante, y por eso la metrica de
#     "prefijo comun mas largo" las puntua como si no tuvieran marcador.
FAMILIA_P = set("pnm pbm pgm ppm pam pfm phm pgmyuv".split())

# (c) El "prefijo comun" medido es contenido, no marcador: la ruta o el nombre del
#     fichero de salida estampados en la cabecera.
PREFIJO_ES_CONTENIDO = set("info shtml pdb".split())

# (d) MARCADOR DE ESCRITOR, no de formato: el prefijo entero es el banner que
#     estampa ESE motor (`# ImageMagick pixel enumeration`, `# File produced by
#     OpenAsset...`, `solid AssimpScene`, `; FBX 7.5.0 project file`, `GIMP
#     Palette`). Otro escritor del mismo formato no lo pondria. Con un solo
#     escritor por formato no se puede separar: se declara indeterminado.
MARCADOR_DE_ESCRITOR = set(
    "txt text ftxt obj objnomtl stl gpl assjson pbrt pov beamer revealjs s5 slidy "
    "slideous dzslides chunkedhtml texinfo hpgl cip xfig uil".split())

MIN_PREFIJO = 2

# (e) CONTROL DE SESGO DE SEMILLA, MEDIDO (_cont_pandoc3.py): con una tercera
#     semilla que empieza por prosa en vez de por un titulo, 42 de los 64 destinos
#     de pandoc pierden el prefijo entero. Era el titulo de mis dos semillas, no un
#     marcador. Este fichero manda sobre la medida de dos semillas.
def sesgo_pandoc():
    try:
        d = json.load(open(os.path.join(SAL, "pandoc3.json"), encoding="utf-8"))
    except OSError:
        return {}
    return {b: (v.get("prefijo_comun", 0) >= MIN_PREFIJO)
            for b, v in d.items() if v.get("n") == 3}


def main():
    cl = json.load(open(os.path.join(SAL, "clasificacion.json"), encoding="utf-8"))
    F = json.load(open(os.path.join(SAL, "formatos.json"), encoding="utf-8"))
    filas = {f["formato"]: f for f in F["filas"]}

    p3 = sesgo_pandoc()
    out = {}
    for b, v in cl.items():
        # la extension se normaliza COMO LO HACE EL VERIFICADOR: splitext, asi que
        # el pseudoformato `av1.mkv` de ConvertX se juzga por `.mkv`.
        ext = os.path.splitext("x." + b)[1].lower()
        marcador = None      # True / False / None (indeterminado)
        motivo = ""
        if b in p3 and not p3[b]:
            marcador, motivo = False, ("control de 3 semillas: sin la semilla que "
                                       "empieza por titulo no queda ni un byte estable")
        elif b in MARCADOR_DE_ESCRITOR:
            marcador, motivo = None, "el prefijo es el banner del escritor, no del formato"
        elif b in ESCRIBIO_OTRA_COSA:
            marcador, motivo = None, "el motor escribio otro formato (PNG): la muestra no describe este"
        elif b in FAMILIA_P:
            marcador, motivo = True, "familia P1..P7 / PF: marcador de conjunto cerrado, no prefijo constante"
        elif b in PREFIJO_ES_CONTENIDO:
            marcador, motivo = False, "el prefijo comun medido es la ruta del fichero, no un marcador"
        elif v.get("evidencia") != "medida":
            marcador, motivo = None, "no se pudo escribir con ningun motor disponible"
        elif v.get("prefijo_len", 0) >= MIN_PREFIJO:
            marcador, motivo = True, "prefijo comun de %d bytes en %s muestras" % (
                v["prefijo_len"], v.get("n_muestras"))
        else:
            marcador, motivo = False, "ni un byte estable en %s muestras de contenido distinto" % v.get("n_muestras")

        def cat(tabla_ok, tabla_sin):
            if ext in tabla_ok:
                return "1_evaluado"
            if ext in tabla_sin:
                return "3_no_aplica"
            if marcador is True:
                return "2_deuda"
            if marcador is False:
                return "3_no_aplica"
            return "0_indeterminado"

        out[b] = {
            "formato": b, "marcador": marcador, "motivo": motivo,
            "prefijo": v.get("prefijo"), "prefijo_txt": v.get("prefijo_txt"),
            "prefijo_len": v.get("prefijo_len"), "motor_muestra": v.get("motor_muestra"),
            "n_muestras": v.get("n_muestras"),
            "cat_viejo": cat(VC.EXT_A_FIRMAS, {}),
            "cat_nuevo": cat(V.EXT_A_FIRMAS, V.EXT_SIN_FIRMA),
            "en_ext_sin_firma": ext in V.EXT_SIN_FIRMA,
            "familia": ext in getattr(V, "EXT_FAMILIA", set()),
            "n_adaptadores": filas.get(b, {}).get("n_adaptadores", 0),
            "en_snapotter": filas.get(b, {}).get("en_snapotter", False),
            "en_patron_oro": filas.get(b, {}).get("en_patron_oro", 0),
        }

    cv = Counter(o["cat_viejo"] for o in out.values())
    cn = Counter(o["cat_nuevo"] for o in out.values())
    n = len(out)
    print("LOS %d DESTINOS DECLARADOS POR LOS 20 ADAPTADORES DE CONVERTX\n" % n)
    print("  %-22s %-18s %-18s" % ("categoria", "vocabulario VIEJO", "vocabulario NUEVO"))
    for k in ("1_evaluado", "2_deuda", "3_no_aplica", "0_indeterminado"):
        print("  %-22s %5d (%5.1f %%)   %5d (%5.1f %%)"
              % (k, cv[k], 100 * cv[k] / n, cn[k], 100 * cn[k] / n))

    # el reparto del "88 %": de lo que NO se evaluaba antes, cuanto era deuda y
    # cuanto es propiedad de los formatos
    antes_no = [o for o in out.values() if o["cat_viejo"] != "1_evaluado"]
    rep = Counter(o["cat_nuevo"] for o in antes_no)
    print("\nDE LOS %d DESTINOS QUE EL VOCABULARIO VIEJO NO EVALUABA:" % len(antes_no))
    for k, v in sorted(rep.items()):
        print("   %-18s %4d  (%.1f %%)" % (k, v, 100 * v / len(antes_no)))

    # marcador si/no sobre lo MEDIDO (sin indeterminados)
    med = [o for o in out.values() if o["marcador"] is not None]
    con = sum(1 for o in med if o["marcador"])
    print("\nSOBRE LOS %d FORMATOS CON VEREDICTO DE MARCADOR (los %d indeterminados"
          " se declaran, no se rellenan):" % (len(med), n - len(med)))
    print("   TIENEN marcador : %d  (%.1f %%)" % (con, 100 * con / len(med)))
    print("   NO tienen       : %d  (%.1f %%)" % (len(med) - con, 100 * (len(med) - con) / len(med)))

    print("\nLOS QUE SIGUEN EN DEUDA (categoria 2) con el vocabulario nuevo:")
    deuda = sorted((o for o in out.values() if o["cat_nuevo"] == "2_deuda"),
                   key=lambda o: (-o["n_adaptadores"], o["formato"]))
    for o in deuda:
        print("   %-16s ad=%d %-24s %s" % (o["formato"], o["n_adaptadores"],
                                           (o["prefijo_txt"] or "")[:24], o["motivo"][:40]))
    json.dump(out, open(os.path.join(SAL, "categorias.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("\nescrito categorias.json")


if __name__ == "__main__":
    main()

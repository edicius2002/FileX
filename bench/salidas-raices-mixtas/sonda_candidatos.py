"""N35 — la tabla de candidatos: que ATRAPA y que ROMPE cada politica.

El encargo pide decidir si un conjunto de raices MIXTO —unas confinan y otras
no— se PODA o se RECHAZA, y pide decidirlo con una tabla, no con una intuicion
(trampa 51: tabula que atrapa y que rompe cada valor candidato).

Cuatro candidatos, los cuatro medidos en LA MISMA TANDA (CLAUDE.md §3: las
cifras relativas dentro de una tanda si son comparables; entre tandas, no):

  A  RECHAZAR  — lo de hoy. Una raiz que no confina invalida el conjunto entero.
  B  PODAR     — descartar las que no confinan, conservar las que si.
                 Si no queda ninguna de lectura, la guarda R6 del `__init__`
                 sigue lanzando `ValueError`.
  C  PODAR SIN GUARDA — igual que B pero sin la guarda R6. Esta aqui para
                 MEDIRSE, no para elegirse: es la forma que tendria el arreglo
                 si alguien «recupera el acceso» sin volver a cerrar la fuga.
  E  ACEPTAR   — relajar R3 y admitir `C:\\` como raiz confinante. Es
                 literalmente la fuga de ayer (N7) con otra ropa, y esta en la
                 tabla para que su descarte tenga numero y no sea una opinion.

TRAMPA 116 — el control positivo de este arnes es EL SUJETO CON EL DEFECTO,
conservado a proposito: el candidato A no es un doble, es la reimplementacion
literal del `_preparar` de hoy. Sin el, tras el arreglo la tabla no tendria
con que comparar y las filas de «antes» habria que ir a buscarlas a otra tanda
—donde ya no serian comparables—.

Cada celda no se queda en «que devuelve el constructor»: se mide QUE LEE DE
VERDAD sobre cuatro objetivos reales del disco, porque el veredicto que importa
es el acceso, no la excepcion.

Salida: bench/salidas-raices-mixtas/candidatos.json
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)

from filex.confinamiento import Confinamiento, Denegado, _norm  # noqa: E402


# --------------------------------------------------------------- candidatos

def _normaliza(r: str) -> str:
    return _norm(os.path.abspath(r))


def _no_confina(a: str) -> bool:
    """El predicado R3 tal cual esta escrito hoy en `_preparar`."""
    return os.path.dirname(a) == a


class CandidatoA(Confinamiento):
    """RECHAZAR — reimplementacion literal del `_preparar` de hoy (trampa 116)."""

    @staticmethod
    def _preparar(raices) -> list[str]:
        out = []
        for r in raices or []:
            a = _normaliza(r)
            if _no_confina(a):
                raise ValueError("una raíz no puede ser la raíz de una unidad (R3)")
            out.append(a)
        return out


class CandidatoB(Confinamiento):
    """PODAR — descartar las que no confinan; la guarda R6 sigue en pie."""

    @staticmethod
    def _preparar(raices) -> list[str]:
        return [a for a in (_normaliza(r) for r in (raices or []))
                if not _no_confina(a)]


#: Placebo: una ruta que SI confina, usada solo para atravesar la guarda R6 del
#: `__init__` de la clase base y poder observar el candidato C, que por
#: definicion no tiene esa guarda. No participa en ninguna medida: se sustituye
#: inmediatamente despues.
_PLACEBO = AQUI


class CandidatoC(Confinamiento):
    """PODAR SIN GUARDA — nunca lanza. Esta para medirse, no para elegirse."""

    def __init__(self, raices_lectura, raices_escritura=None, **kw) -> None:
        super().__init__([_PLACEBO], **kw)
        self.lectura = CandidatoB._preparar(raices_lectura)
        self.escritura = CandidatoB._preparar(
            raices_escritura if raices_escritura is not None else raices_lectura)


class CandidatoE(Confinamiento):
    """ACEPTAR — R3 relajada: la raiz de unidad se admite como raiz."""

    @staticmethod
    def _preparar(raices) -> list[str]:
        return [_normaliza(r) for r in (raices or [])]


CANDIDATOS = {"A_rechazar": CandidatoA, "B_podar": CandidatoB,
              "C_podar_sin_guarda": CandidatoC, "E_aceptar": CandidatoE}


# ------------------------------------------------------------------ objetivos

def construir_escenario(base: str) -> dict:
    """Cuatro objetivos REALES en disco, dos unidades distintas."""
    legit = os.path.join(base, "legit")
    hermano = os.path.join(base, "hermano")
    os.makedirs(legit, exist_ok=True)
    os.makedirs(hermano, exist_ok=True)
    o1 = os.path.join(legit, "dentro.txt")
    o2 = os.path.join(hermano, "fuera.txt")
    with open(o1, "w", encoding="utf-8") as fh:
        fh.write("dentro de la raiz legitima\n")
    with open(o2, "w", encoding="utf-8") as fh:
        fh.write("hermano NO declarado\n")
    return {
        "legit": legit,
        "objetivos": {
            # esperado LEE: es el acceso legitimo que N35 pierde hoy
            "O1_dentro_de_la_raiz_legitima": o1,
            # esperado DENIEGA: hermano no declarado, misma unidad
            "O2_hermano_no_declarado": o2,
            # esperado DENIEGA: otra unidad (el repositorio vive en D:)
            "O3_otra_unidad": os.path.join(RAIZ, "corpus", "imagen", "tipico.png"),
            # esperado DENIEGA: bajo C:\ pero fuera de la raiz legitima. Es la
            # celda que separa «podar» de «aceptar»: con E se lee.
            "O4_bajo_la_unidad_fuera_de_legit": r"C:\Windows\win.ini",
        },
    }


#: El esperado es POR FILA, no global. La primera version de este arnes usaba
#: un esperado fijo con `O1 = True` en las ocho filas, y en las tres que NO
#: declaran la raiz legitima (2, 5 y 8) eso es falso: ahi lo correcto es
#: denegar los cuatro objetivos. La columna «OK/MAL» salia enganosa en 3 de 8
#: filas y marcaba MAL a candidatos que estaban acertando. Corregido antes de
#: publicar nada: un esperado que no depende de la entrada no es un esperado.
CLAVES = ["O1_dentro_de_la_raiz_legitima", "O2_hermano_no_declarado",
          "O3_otra_unidad", "O4_bajo_la_unidad_fuera_de_legit"]


def esperado_de(raices, legit) -> dict:
    """O1 se lee si y solo si la raiz legitima esta declarada. El resto, nunca."""
    declara_legit = any(_normaliza(r) == _normaliza(legit) for r in raices)
    return {"O1_dentro_de_la_raiz_legitima": declara_legit,
            "O2_hermano_no_declarado": False,
            "O3_otra_unidad": False,
            "O4_bajo_la_unidad_fuera_de_legit": False}


def medir_celda(cls, raices, objetivos, esperado) -> dict:
    """Construye y, si se pudo, pregunta por los cuatro objetivos."""
    celda = {"raices_declaradas": list(raices)}
    try:
        c = cls(raices)
    except ValueError as e:
        celda["constructor"] = "ValueError"
        celda["mensaje"] = str(e)
        # Un constructor que lanza es «sin acceso»: no hay confinamiento con el
        # que preguntar, y el consumidor no opera. Se anota como 0 lecturas.
        celda["raices_efectivas"] = None
        celda["lee"] = {k: False for k in objetivos}
    else:
        celda["constructor"] = "ok"
        celda["raices_efectivas"] = list(c.lectura)
        lee = {}
        for nombre, ruta in objetivos.items():
            if not os.path.exists(ruta):
                lee[nombre] = None          # objetivo ausente: se declara
                continue
            try:
                c.resolver(ruta)
                lee[nombre] = True
            except Denegado:
                lee[nombre] = False
        celda["lee"] = lee
    celda["esperado"] = esperado
    celda["coincide_con_lo_esperado"] = all(
        celda["lee"].get(k) == v for k, v in esperado.items())
    return celda


def main() -> int:
    base = tempfile.mkdtemp(prefix="filex-n35-")
    esc = construir_escenario(base)
    legit = esc["legit"]
    objetivos = esc["objetivos"]
    ausentes = [k for k, v in objetivos.items() if not os.path.exists(v)]

    legit2 = os.path.join(base, "legit2")
    os.makedirs(legit2, exist_ok=True)

    filas = {
        "1_solo_legitima_CONTROL": [legit],
        "2_solo_raiz_de_unidad_N7": ["C:\\"],
        "3_MIXTA_mala_primero_N35": ["C:\\", legit],
        "4_MIXTA_buena_primero_N35": [legit, "C:\\"],
        "5_dos_malas": ["C:\\", "D:\\"],
        "6_dos_buenas": [legit, legit2],
        "7_MIXTA_con_UNC": [r"\\servidor\recurso", legit],
        "8_vacia": [],
    }

    resultado = {
        "plataforma": sys.platform,
        "python": sys.version.split()[0],
        "base_desechable": base,
        "objetivos": objetivos,
        "objetivos_ausentes": ausentes,
        "esperado_por_fila": {},
        "celdas": {},
    }
    for nombre_fila, raices in filas.items():
        esp = esperado_de(raices, legit)
        resultado["esperado_por_fila"][nombre_fila] = esp
        resultado["celdas"][nombre_fila] = {
            nombre_c: medir_celda(cls, raices, objetivos, esp)
            for nombre_c, cls in CANDIDATOS.items()
        }

    destino = os.path.join(AQUI, "candidatos.json")
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(resultado, fh, indent=2, ensure_ascii=False)

    # --- tabla legible
    cols = list(CANDIDATOS)
    print("Lee = O1(legit) O2(hermano) O3(otra unidad) O4(bajo C: fuera)")
    print("      . = deniega   L = LEE   x = constructor lanzo\n")
    print("%-28s %s" % ("fila", "  ".join("%-18s" % c for c in cols)))
    for nombre_fila in filas:
        pinta = []
        for c in cols:
            celda = resultado["celdas"][nombre_fila][c]
            ok = "OK " if celda["coincide_con_lo_esperado"] else "MAL"
            if celda["constructor"] != "ok":
                pinta.append("%-18s" % ("xxxx  %s (lanzo)" % ok))
            else:
                s = "".join("L" if celda["lee"][k] else "." for k in CLAVES)
                pinta.append("%-18s" % ("%s  %s" % (s, ok)))
        print("%-28s %s" % (nombre_fila, "  ".join(pinta)))

    print("\n-> %s" % destino)
    print("base desechable (se conserva para inspeccion): %s" % base)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

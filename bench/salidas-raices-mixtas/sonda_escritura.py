"""N35 — el eje ESCRITURA: la guarda R6 solo mira la lectura.

`Confinamiento.__init__` lanza `ValueError` si `not self.lectura`, y NO
comprueba `self.escritura`. Con la politica de hoy (RECHAZAR) eso casi no se
nota, porque una raiz de escritura que no confina invalida el conjunto entero
antes de llegar ahi. Al PODAR, aparece un camino nuevo:

    Confinamiento([legit], ["C:\\"])   ->  lectura=[legit], escritura=[]

es decir, toda la escritura denegada EN SILENCIO donde antes habia un error.
Podria ser la trampa 44 —un campo honesto al lado de una nota falsa— asi que
se mide antes de elegir la forma del arreglo, con dos sub-candidatos:

  B1  PODAR Y CALLAR — la guarda R6 se queda como esta (solo lectura).
  B2  PODAR Y AVISAR — ademas lanza si se DECLARARON raices de escritura y la
      poda se las llevo TODAS. Distingue «no declare escritura» de «declare
      escritura y ninguna sirve», que es la trampa 43: toda deteccion por
      ausencia separa «no se puede» de «no esta».

CONTROL IMPRESCINDIBLE: la fila `hoy_ya_permite_escritura_vacia` comprueba si
el caso ya era alcanzable ANTES de tocar nada. Si lo era, la poda no introduce
un estado nuevo y B2 estaria arreglando un problema que no existe (trampa 58).

Salida: bench/salidas-raices-mixtas/escritura.json
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)

from filex.confinamiento import Confinamiento, Denegado  # noqa: E402

from sonda_candidatos import CandidatoA, CandidatoB, _normaliza  # noqa: E402


class B1(CandidatoB):
    """PODAR Y CALLAR: la guarda R6 sigue mirando solo la lectura."""


class B2(CandidatoB):
    """PODAR Y AVISAR: ademas exige que la escritura DECLARADA sobreviva."""

    def __init__(self, raices_lectura, raices_escritura=None, **kw) -> None:
        super().__init__(raices_lectura, raices_escritura, **kw)
        if raices_escritura is not None and raices_escritura and not self.escritura:
            raise ValueError(
                "se declararon raíces de escritura y ninguna confina (R6+R9)")


def medir(cls, lectura, escritura, destino_bueno, destino_malo) -> dict:
    celda = {}
    try:
        c = cls(lectura, escritura)
    except ValueError as e:
        celda["constructor"] = "ValueError"
        celda["mensaje"] = str(e)
        celda["escribe_en_su_raiz"] = False
        celda["escribe_fuera"] = False
        return celda
    celda["constructor"] = "ok"
    celda["lectura"] = list(c.lectura)
    celda["escritura"] = list(c.escritura)
    for nombre, ruta in (("escribe_en_su_raiz", destino_bueno),
                         ("escribe_fuera", destino_malo)):
        try:
            c.resolver(ruta, escritura=True)
            celda[nombre] = True
        except Denegado:
            celda[nombre] = False
    return celda


def main() -> int:
    base = tempfile.mkdtemp(prefix="filex-n35-esc-")
    legit = os.path.join(base, "legit")
    escr = os.path.join(base, "escr")
    fuera = os.path.join(base, "fuera")
    for d in (legit, escr, fuera):
        os.makedirs(d, exist_ok=True)

    filas = {
        # (lectura, escritura)
        "1_CONTROL_ambas_buenas": ([legit], [escr]),
        "2_escritura_None_hereda_lectura": ([legit], None),
        "3_escritura_declarada_VACIA": ([legit], []),
        "4_escritura_SOLO_raiz_de_unidad": ([legit], ["C:\\"]),
        "5_escritura_MIXTA": ([legit], ["C:\\", escr]),
        "6_lectura_MIXTA_escritura_buena": (["C:\\", legit], [escr]),
    }

    res = {"plataforma": sys.platform, "base_desechable": base,
           "destino_bueno": escr, "destino_malo": fuera, "celdas": {}}

    # --- control: ¿el estado «escritura vacia» ya era alcanzable HOY?
    try:
        hoy = Confinamiento([legit], [])
        res["control_hoy_permite_escritura_vacia"] = {
            "construye": True, "escritura": list(hoy.escritura),
            "escribe_en_su_raiz": None}
        try:
            hoy.resolver(escr, escritura=True)
            res["control_hoy_permite_escritura_vacia"]["escribe_en_su_raiz"] = True
        except Denegado:
            res["control_hoy_permite_escritura_vacia"]["escribe_en_su_raiz"] = False
    except ValueError as e:
        res["control_hoy_permite_escritura_vacia"] = {
            "construye": False, "mensaje": str(e)}

    for nombre, (lec, esc) in filas.items():
        res["celdas"][nombre] = {
            "A_rechazar": medir(CandidatoA, lec, esc, escr, fuera),
            "B1_podar_y_callar": medir(B1, lec, esc, escr, fuera),
            "B2_podar_y_avisar": medir(B2, lec, esc, escr, fuera),
        }

    destino = os.path.join(AQUI, "escritura.json")
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)

    ctrl = res["control_hoy_permite_escritura_vacia"]
    print("CONTROL — hoy, sin tocar nada, Confinamiento([legit], []):")
    print("   construye=%s  escritura=%s  escribe_en_su_raiz=%s\n" % (
        ctrl.get("construye"), ctrl.get("escritura"),
        ctrl.get("escribe_en_su_raiz")))

    cols = ["A_rechazar", "B1_podar_y_callar", "B2_podar_y_avisar"]
    print("%-34s %s" % ("fila", "  ".join("%-26s" % c for c in cols)))
    for nombre in filas:
        pinta = []
        for c in cols:
            cel = res["celdas"][nombre][c]
            if cel["constructor"] != "ok":
                pinta.append("%-26s" % "ValueError")
            else:
                pinta.append("%-26s" % ("escr=%d  suya=%s fuera=%s" % (
                    len(cel["escritura"]), cel["escribe_en_su_raiz"],
                    cel["escribe_fuera"])))
        print("%-34s %s" % (nombre, "  ".join(pinta)))
    print("\n-> %s" % destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Registra la huella del contrato y el estado de las 172 aristas selladas.

Uso:  python bench/salidas-fix-verificador/huella_estado.py <etiqueta>

Escribe `bench/salidas-fix-verificador/huella_<etiqueta>.json` con:
  - `interprete`: el intérprete que la calculó (trampa 105).
  - `contrato_de_alcance`: `huella.de_alcance()` sobre `filex/verificador.py`.
  - `nombres_alcanzados`: cuántas funciones entran en el cierre, y su lista.
  - por cada `filex/sondeo/*.json`: los tres componentes guardados, los
    actuales, y el recuento de aristas que quedarían `sin_sondear`.

No toca nada. Sólo mide.
"""

import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import huella  # noqa: E402


def main() -> int:
    etiqueta = sys.argv[1] if len(sys.argv) > 1 else "ahora"
    fuente = open(
        os.path.join(RAIZ, "filex", "verificador.py"), encoding="utf-8"
    ).read()

    salida = {
        "etiqueta": etiqueta,
        "interprete": huella.interprete_actual(),
        "contrato_de_alcance": huella.de_alcance(fuente),
        "nombres_alcanzados": sorted(huella.nombres_alcanzados(fuente)),
        "sondeos": {},
    }
    salida["n_nombres_alcanzados"] = len(salida["nombres_alcanzados"])

    dir_sondeo = os.path.join(RAIZ, "filex", "sondeo")
    total_aristas = 0
    total_degradadas = 0
    for nombre in sorted(os.listdir(dir_sondeo)):
        if not nombre.endswith(".json"):
            continue
        motor = nombre[:-5]
        datos = json.load(open(os.path.join(dir_sondeo, nombre), encoding="utf-8"))
        guardada = datos.get("huella") or {}
        actual = huella.de_motor_por_nombre(motor)
        aristas = datos.get("aristas") or {}
        movidos = [
            c
            for c in ("motor", "invocacion", "contrato")
            if guardada.get(c) != actual.get(c)
        ]
        total_aristas += len(aristas)
        if movidos:
            total_degradadas += len(aristas)
        salida["sondeos"][motor] = {
            "guardada": guardada,
            "actual": actual,
            "componentes_movidos": movidos,
            "n_aristas": len(aristas),
            "aristas_degradadas": len(aristas) if movidos else 0,
        }

    salida["total_aristas"] = total_aristas
    salida["total_degradadas"] = total_degradadas

    destino = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), f"huella_{etiqueta}.json"
    )
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False, sort_keys=True)

    print(f"interprete           : {salida['interprete']}")
    print(f"contrato (de_alcance): {salida['contrato_de_alcance']}")
    print(f"nombres alcanzados   : {salida['n_nombres_alcanzados']}")
    for motor, d in salida["sondeos"].items():
        print(
            f"  {motor:16s} aristas={d['n_aristas']:3d} "
            f"contrato={d['guardada'].get('contrato')} -> {d['actual'].get('contrato')} "
            f"movidos={d['componentes_movidos']}"
        )
    print(f"TOTAL aristas={total_aristas}  degradadas={total_degradadas}")
    print(f"escrito: {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

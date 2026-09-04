"""Genera la tabla de inventario del MANIFIESTO con sha256 y tamanos REALES.

Existe porque la primera version del MANIFIESTO llevaba hashes de relleno, y un
hash inventado es peor que ninguno: parece verificable y no lo es. Esto los
calcula y sustituye la tabla entre los dos marcadores.
"""

from __future__ import annotations

import hashlib
import os

AQUI = os.path.dirname(os.path.abspath(__file__))

DESC = {
    "sonda_vocabulario.py": "arnés: qué cuenta como raíz que no confina",
    "vocabulario.json": "17 candidatas; raíz de unidad **y** de recurso UNC",
    "sonda_mecanismo.py": "arnés: por qué `C:\\` no abre nada",
    "mecanismo.json": "la barra doble, con control positivo y negativo",
    "sonda_candidatos.py": "arnés: 8 filas × 4 candidatos (lectura)",
    "candidatos.json": "la tabla de lectura: la meseta",
    "sonda_superficies.py": "arnés: núcleo y MCP",
    "superficies.json": "32 celdas: el eje que decide",
    "sonda_unc.py": "arnés: el viaje de una ruta por el cable MCP",
    "unc.json": "el defecto de mi doble + el de `_uri_a_ruta`",
    "sonda_escritura.py": "arnés: B1 contra B2, con el control de hoy",
    "escritura.json": "6 filas × 3 candidatos + control",
    "sonda_regresion.py": "arnés del par antes/después, clase REAL",
    "regresion_antes.json": "11 filas sobre el código de antes",
    "regresion_despues.json": "11 filas sobre el código de después",
    "comparar.py": "el diff celda a celda; `rc=0` si no hay fuga",
    "comparacion.json": "**7 SIN_CAMBIO · 4 RECUPERA · 0 fugas**",
    "sonda_coste.py": "arnés de coste: las dos versiones intercaladas",
    "coste_tanda1.json": "tanda 1, n=9 × 2000",
    "coste_tanda2.json": "tanda 2, n=9 × 2000",
    "coste_tanda3.json": "tanda 3, n=9 × 2000",
    "pruebas_ANTES.txt": "las 11 pruebas contra el código de antes",
    "suite.txt": "la suite completa",
    "hacer_inventario.py": "este generador (se incluye para no mentir por omisión)",
}

INI = "<!-- INVENTARIO:INICIO -->"
FIN = "<!-- INVENTARIO:FIN -->"


def main() -> int:
    filas = ["| fichero | bytes | sha256 | qué es |", "|---|---|---|---|"]
    faltan = []
    for nombre, desc in DESC.items():
        p = os.path.join(AQUI, nombre)
        if not os.path.exists(p):
            faltan.append(nombre)
            continue
        datos = open(p, "rb").read()
        filas.append("| `%s` | %s | `%s` | %s |" % (
            nombre, format(len(datos), ",d").replace(",", " "),
            hashlib.sha256(datos).hexdigest(), desc))
    tabla = "\n".join(filas)

    man = os.path.join(AQUI, "MANIFIESTO.md")
    texto = open(man, encoding="utf-8").read()
    a, b = texto.index(INI), texto.index(FIN)
    texto = texto[:a] + INI + "\n\n" + tabla + "\n\n" + texto[b:]
    with open(man, "w", encoding="utf-8") as fh:
        fh.write(texto)
    print("%d filas escritas en MANIFIESTO.md" % (len(filas) - 2))
    if faltan:
        print("NO ENCONTRADOS (no se inventan): %s" % ", ".join(faltan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

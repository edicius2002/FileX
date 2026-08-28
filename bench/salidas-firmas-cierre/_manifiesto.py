"""Genera el MANIFIESTO.md de bench/salidas-firmas-cierre/.

Nombre, sha256, tamano y la orden EXACTA que reproduce cada fichero. La orden
tiene que funcionar de verdad: el manifiesto de ffmpeg documentaba mal su
pipeline y costo una tanda entera (regla 11 del encargo).

Uso:  python bench/salidas-firmas-cierre/_manifiesto.py
"""
import hashlib
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
TMP = "%TEMP%\\claude\\...\\scratchpad\\F2_TMP"
ANCHA = "%TEMP%\\claude\\...\\scratchpad\\F2_ANCHA"
REF53 = "%TEMP%\\claude\\...\\scratchpad\\REF53"
C30 = "%TEMP%\\claude\\...\\scratchpad\\F2_C30"

ORDENES = {
    "muestra_pict_pcd.json":
        "python bench/salidas-firmas-cierre/_muestra_pict_pcd.py <TMP>",
    "c37_reproduce_antes.json":
        "git stash && python bench/salidas-firmas-cierre/_c37_reproduce.py <TMP>",
    "c37_reproduce_despues.json":
        "python bench/salidas-firmas-cierre/_c37_reproduce.py <TMP>",
    "c37_coste.json":
        "python bench/salidas-firmas-cierre/_c37_coste.py <TMP>",
    "c37_caducidad.json":
        "python bench/salidas-firmas-cierre/_c37_caducidad.py",
    "c37_bucles.json":
        "python bench/salidas-firmas-cierre/_c37_bucles.py",
    "c37_deuda12.json":
        "python bench/salidas-firmas-cierre/_c37_deuda12.py",
    "c37_ancha_local.json":
        "python bench/salidas-firmas-cierre/_c37_ancha_local.py <ANCHA>",
    "c28_censo.json":
        "python bench/salidas-firmas-cierre/_c28_censo.py",
    "c28_motivos.json":
        "python bench/salidas-firmas-cierre/_c28_motivos.py",
    "c28_banner.json":
        "python bench/salidas-firmas-cierre/_c28_banner.py",
    "c28_huerfanas.json":
        "python bench/salidas-firmas-cierre/_c28_huerfanas.py",
    "c28_los56.json":
        "python bench/salidas-firmas-cierre/_c28_los56.py",
    "c28_prueba21.json":
        "python bench/salidas-firmas-cierre/_c28_prueba21.py <TMP>",
    "regenera53.json":
        "python bench/salidas-firmas-cierre/_regenera53.py <REF53>",
    "regresion_antes.json":
        "F2_REF53=<REF53> python bench/salidas-firmas-cierre/"
        "_regresion_53_f2.py --antes",
    "regresion_despues.json":
        "F2_REF53=<REF53> python bench/salidas-firmas-cierre/_regresion_53_f2.py",
    "c30_contenedor.json":
        "python bench/salidas-firmas-cierre/_c30_escribe.py <C30>   "
        "(primera pasada, verificador 1812df12...)",
    "c30_triaje.json":
        "python bench/salidas-firmas-cierre/_c30_triaje.py <C30>",
    "c30_contenedor_v2.json":
        "python bench/salidas-firmas-cierre/_c30_escribe.py <C30>   "
        "(segunda pasada, verificador c023a9bc...)",
    "vocabulario_f2.json":
        "python bench/salidas-firmas-cierre/_vocabulario_f2.py",
}

QUE_ES = {
    "muestra_pict_pcd.json": "censo de 3 semillas: donde esta el marcador de PICT y de PCD",
    "c37_reproduce_antes.json": "la medida de firmas-contrato.md 3.2/10.3, reproducida sobre HEAD",
    "c37_reproduce_despues.json": "la misma, con el arreglo puesto",
    "c37_coste.json": "coste de la ventana larga: primitivo aislado, firma_real pareada, y disparo",
    "c37_caducidad.json": "que aristas caduca el cambio (172) y cuantas puede mover (0)",
    "c37_bucles.json": "busqueda del defecto de la trampa 48 en 8 modulos, con control positivo",
    "c37_deuda12.json": "los 12 de la deuda de firmas, con su prefijo comun y su n",
    "c37_ancha_local.json": "345 salidas locales legitimas, evaluadas con HEAD y con el arbol",
    "c28_censo.json": "los 86 indeterminados, con sus escritores reales",
    "c28_motivos.json": "el reparto real de los 86: 56 / 17 / 13",
    "c28_banner.json": "los 17 «banner del escritor», con su prefijo y sus escritores",
    "c28_huerfanas.json": "firmas que la sonda sabe dar y ninguna extension acepta",
    "c28_los56.json": "los 56 inescribibles, clasificados por su `rc`",
    "c28_prueba21.json": "6 de ellos escritos DE VERDAD con la invocacion correcta",
    "regenera53.json": "las 53 del patron oro regeneradas fuera del repo, con su sha256",
    "regresion_antes.json": "contrato + fidelidad sobre las 53, con el verificador de HEAD",
    "regresion_despues.json": "lo mismo con el del arbol de trabajo",
    "c30_contenedor.json": "864 celdas dentro de filex-c13, primera pasada",
    "c30_triaje.json": "triaje con testigo externo: falso positivo frente a captura legitima",
    "c30_contenedor_v2.json": "las mismas 864 celdas con los cuatro arreglos puestos",
    "vocabulario_f2.json": "las tablas del vocabulario, con tamano Y con elementos",
}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    nombres = sorted(n for n in os.listdir(AQUI)
                     if n != "MANIFIESTO.md" and not n.startswith("."))
    js = [n for n in nombres if n.endswith(".json")]
    py = [n for n in nombres if n.endswith(".py")]
    logs = [n for n in nombres if n.endswith(".txt")]
    total = sum(os.path.getsize(os.path.join(AQUI, n)) for n in nombres)

    L = []
    L.append("# Manifiesto — salidas de F2 (`bench/firmas-cierre.md`)\n")
    L.append("**Generado:** 2026-08-28 · **Ficheros:** %d "
             "(%d `.json`, %d `.py`, %d logs) · **Peso:** %.1f KB · "
             "**todo texto, nada binario**\n" %
             (len(nombres), len(js), len(py), len(logs), total / 1024.0))
    L.append("Los binarios —las 53 del patrón oro regeneradas (204,9 MB), las 345 "
             "salidas locales y las 864 celdas del contenedor— viven en un "
             "directorio desechable **fuera del repositorio** y se borran al "
             "terminar. Aquí solo hay texto.\n")
    L.append("En las órdenes, `<TMP>`, `<ANCHA>`, `<REF53>` y `<C30>` son "
             "directorios desechables cualesquiera; los que se usaron fueron\n"
             "`%s`, `%s`, `%s` y `%s`.\n" % (TMP, ANCHA, REF53, C30))
    L.append("\n## Resultados (`.json`)\n")
    L.append("| Fichero | Bytes | sha256 | Qué es | Orden exacta |")
    L.append("|---|---:|---|---|---|")
    for n in js:
        p = os.path.join(AQUI, n)
        L.append("| `%s` | %d | `%s…` | %s | `%s` |" %
                 (n, os.path.getsize(p), sha(p)[:16],
                  QUE_ES.get(n, ""), ORDENES.get(n, "—")))
    L.append("\n## Instrumentos (`.py`)\n")
    L.append("| Fichero | Bytes | sha256 |")
    L.append("|---|---:|---|")
    for n in py:
        p = os.path.join(AQUI, n)
        L.append("| `%s` | %d | `%s…` |" % (n, os.path.getsize(p), sha(p)[:16]))
    L.append("\n## Logs\n")
    L.append("| Fichero | Bytes |")
    L.append("|---|---:|")
    for n in logs:
        L.append("| `%s` | %d |" % (n, os.path.getsize(os.path.join(AQUI, n))))
    L.append("\n## Lo que NO está aquí, y dónde se regenera\n")
    L.append("- **Las 53 salidas del patrón oro** (204,9 MB): "
             "`python bench/salidas-firmas-cierre/_regenera53.py <REF53>`. "
             "35 de 53 reproducen el `sha256` de `referencia.json`; las 18 que no, "
             "con su mecanismo, en `regenera53.json`.")
    L.append("- **Las 345 salidas locales**: las escribe `_c37_ancha_local.py` en "
             "`<ANCHA>` y no las borra, para poder evaluarlas dos veces con el "
             "mismo byte a byte.")
    L.append("- **Las 864 celdas del contenedor**: las escribe `_c30_escribe.py` "
             "dentro de `filex-c13` y las recoge en `<C30>`.")
    with open(os.path.join(AQUI, "MANIFIESTO.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("MANIFIESTO.md: %d ficheros, %.1f KB" % (len(nombres), total / 1024.0))


if __name__ == "__main__":
    main()

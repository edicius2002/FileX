# -*- coding: utf-8 -*-
"""Los DOS testigos de ruido, con tope propio (CLAUDE.md §3).

Uno mide **deriva** dentro de la tanda (bucle monohilo de Python) y el otro mide
**nivel** de carga de la maquina (lanzamiento de proceso). Hacen falta los dos:
el monohilo es ciego a la contencion multinucleo —con 12 nucleos cabe en uno
libre— y etiqueto `limpia` una tanda que salio ×6,8 sobre su propio control.

**Y el testigo lleva tope**: 20 s, devolviendo el tope y marcando `SUCIA`. Un
testigo que puede tumbar la medicion no es un testigo (caso P3: `ffprobe -version`
agotando un timeout de 60 s).

Este fichero es una COPIA de la misma logica que se ha puesto en
`bench/scripts/ocr_motor.py` (N23). Se duplica a proposito: `bench/scripts/` no
puede depender de un directorio de salidas de un agente.
"""
import subprocess
import time

#: Tope del propio testigo, en segundos.
TOPE_S = 20.0

#: Umbral de deriva: cociente entre el testigo de despues y el de antes.
DERIVA_MAX = 1.30

#: Umbral de nivel: cociente entre el lanzamiento de proceso medido y el de
#: referencia de la propia tanda (la primera lectura, en frio descartada).
NIVEL_MAX = 2.00


def testigo_deriva(vueltas: int = 300_000) -> float:
    """Bucle monohilo. Devuelve milisegundos. Detecta DERIVA dentro de la tanda."""
    t = time.perf_counter()
    x = 0
    for i in range(vueltas):
        x = (x + i) % 1_000_003
    return (time.perf_counter() - t) * 1000.0


def testigo_nivel(exe: str = "ffprobe") -> tuple[float, bool]:
    """Lanzamiento de proceso. Devuelve `(ms, agotado)`.

    Detecta el NIVEL de carga de la maquina, que es lo que el monohilo no ve.
    Si agota el tope devuelve el tope y `agotado=True`: la tanda es SUCIA, pero
    la medicion sigue viva.
    """
    t = time.perf_counter()
    try:
        subprocess.run([exe, "-version"], stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=TOPE_S)
    except subprocess.TimeoutExpired:
        return TOPE_S * 1000.0, True
    except OSError:
        return -1.0, False
    return (time.perf_counter() - t) * 1000.0, False


def veredicto(deriva_ini: float, deriva_fin: float,
              nivel_ini: float, nivel_fin: float, agotado: bool) -> dict:
    """`limpia` / `SUCIA`, con los cuatro numeros y el motivo dentro.

    Con la sesion de escritorio remoto activa **todo sale SUCIA**, y eso es
    estructural, no un fallo: lo que importa es el numero, no la etiqueta.
    """
    r_der = (deriva_fin / deriva_ini) if deriva_ini > 0 else -1.0
    r_niv = (nivel_fin / nivel_ini) if nivel_ini > 0 else -1.0
    motivos = []
    if agotado:
        motivos.append(f"el testigo de nivel agoto su tope de {TOPE_S} s")
    if r_der > DERIVA_MAX:
        motivos.append(f"deriva ×{r_der:.2f} > {DERIVA_MAX}")
    if r_niv > NIVEL_MAX:
        motivos.append(f"nivel ×{r_niv:.2f} > {NIVEL_MAX}")
    return {"deriva_ini_ms": round(deriva_ini, 1), "deriva_fin_ms": round(deriva_fin, 1),
            "deriva_ratio": round(r_der, 3),
            "nivel_ini_ms": round(nivel_ini, 1), "nivel_fin_ms": round(nivel_fin, 1),
            "nivel_ratio": round(r_niv, 3), "nivel_agotado": agotado,
            "etiqueta": "SUCIA" if motivos else "limpia",
            "motivos": motivos}

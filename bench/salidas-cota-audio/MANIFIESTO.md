# MANIFIESTO — `bench/salidas-cota-audio/`

**Ningún informe de `bench/` cita este directorio** (`grep -rl "salidas-cota-audio" bench/*.md`
no da resultados). Es un intento de N28 **abandonado y con error**, de la misma tanda que
`bench/patron-multifichero.md` (commit `8765303`, "WIP N28/C22"): un primer enfoque para
calcular cotas de bitrate por (códec, build) que se descartó a favor del enfoque más simple
que sí llegó a informe (`bench/patron-multifichero.md` §N28, luego a su vez refutado y
retirado por `bench/bitrate-por-pista.md`, commit `d2bcb7b`). Se declara aquí en vez de en
`ci/evidencia-irreproducible.txt` porque **no es evidencia forense de terceros**: es un
experimento propio de FileX, incompleto, y sí es regenerable (ver abajo).

| Fichero | Tamaño (B) | SHA-256 | Orden |
|---|---:|---|---|
| `medir.py` | 5 929 | `ce1e442e9165067d2217245db26a23cea9b061865c5bb525d26134ed0194a406` | Fuente escrito a mano, commit `8765303`. |
| `ejecucion.log` | 787 | `869986b2d9f96c9623d88c74b4e0995167b6049752ef222576f4e2e7e01a7702` | `python3 bench/salidas-cota-audio/medir.py` (stderr capturado). |
| `matriz_parcial.json` | 143 859 | `088a38939414f90d6bcd57be6a4ad0b63c0a048cf73ba6edd08829365c499af3` | Salida parcial de la misma orden: el script escribe este fichero **antes** de fallar. |

**MEDIDO el 01/09/2026 (worker2, tres intentos independientes):** se reejecutó
`python3 bench/salidas-cota-audio/medir.py` tres veces (con timeout de 180 s y de 60 s).
Las tres reproducen exactamente el mismo error, en el mismo sitio:

```
ValueError: max() iterable argument is empty
```

en `tabla()` (`medir.py:54`). **Corrección sobre un borrador anterior de este mismo
manifiesto:** `matriz_parcial.json` **NO sale byte a byte idéntico** entre ejecuciones —
verificado con `sha256sum` antes/después de cada reejecución, el hash cambia siempre
(ej. `088a3893…` → `7daf429c…`) porque el fichero incluye un campo `ms` (tiempo de cada
invocación de `ffmpeg`) que no es determinista. Lo que SÍ es determinista y se comprobó
en las tres pasadas: 96 filas, la misma clasificación por `rc` (0/48 `libopus` con
`bytes>0`, 48/48 `aac` con `bytes>0`) y el mismo `ValueError` en la misma línea. Tras cada
reejecución se restauró el fichero a su versión commiteada con
`git checkout -- bench/salidas-cota-audio/matriz_parcial.json`.

**Causa raíz (leída en el código, no adivinada):** `tabla()` calcula, para cada códec en
`("aac","libopus")`, `rs=[x["factor_max"] for x in filas if x["codec"]==codec and
x.get("factor_max")]` y luego `max(rs)`. Para `libopus` todas las filas de la matriz
terminan sin `factor_max` (el códec de audio Opus dentro de contenedor `.webm` con vídeo
`libx264` falla sistemáticamente en la combinación usada por `matriz()`, dejando
`rs = []` para ese códec), así que `max([])` revienta. El bug es de construcción, no de
entorno ni de recursos.

**PENDIENTE, declarado explícitamente:** no se corrige `medir.py` en esta tanda —no es del
alcance de C41, que es documentar, no reescribir arneses ajenos— y el enfoque que este
script perseguía (cotas por códec/build) quedó descartado por el propio proyecto a favor del
criterio más simple de `bitrate-por-pista.md`. Este directorio se conserva como traza de un
camino explorado y abandonado, tal como pide CLAUDE.md ("reportar los fallos como fallos").

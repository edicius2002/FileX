# MANIFIESTO — `bench/salidas-pcd-y-memoria/`

Ronda 6, `C31(a)`. Datos crudos de `bench/pcd-y-memoria.md` §3: el pico de RAM de
`filex.verificador._datos` sobre CSV, antes y después del arreglo que deja de materializar
`csv_filas`. Todo texto, sin corpus versionado. Regla §6.

## Ficheros

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `_datos_ram_r6.py` | 3322 | `644e5696c9438e2e1bf863f913a2b49408f382b7b302da3a0cd8e6c3ceb0e5d7` |
| `datos_ram.json` | 1127 | `4f630036a212d95c65a5eafe16bf938233690469904733fde77ae6cd3ca6ce02` |

`_datos_ram_r6.py` es una **copia** de `bench/salidas-hito3/_datos_ram.py` (K2, hito 3),
**no tocado** — la regla del proyecto es "un fichero de salida por agente" y ese arnés es de
otro directorio. Copiado tal cual, sin editar una línea: mismo método (`tracemalloc`, CSV
sintético determinista de `--mb` megabytes nominales, dos ramas — normal y "campo largo",
la del TXT de ImageMagick que dispara `csv.Error`).

Orden exacta que reproduce `datos_ram.json` (con `filex/verificador.py` de esta rama,
**después** del arreglo de `C31(a)`):

```
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe bench/salidas-pcd-y-memoria/_datos_ram_r6.py --mb 1 8 32
```

## Resultado — MEDIDO el 03/09/2026, esta máquina (`C:`, no `D:` — cifras absolutas no
comparables con las de `bench/salidas-hito3/datos_ram.json`, que se midieron en `D:`)

| MB nominal | Caso | Pico (B) | Ratio sobre fichero | ms |
|---:|---|---:|---:|---:|
| 1 | csv_normal | 6 508 652 | ×6,21 | 1 963,5 |
| 1 | campo_largo | 7 865 587 | ×7,50 | 104,0 |
| 8 | csv_normal | 51 795 747 | ×6,17 | 14 946,1 |
| 8 | campo_largo | 59 245 811 | ×7,06 | 776,0 |
| 32 | csv_normal | 207 280 691 | ×6,18 | 59 193,3 |
| 32 | campo_largo | 235 406 579 | ×7,02 | 3 307,5 |

Frente al listón de `bench/hito3-mudanza.md` §6.1 (medido en `D:`, sin el arreglo): **×21,36 /
×21,33 / ×21,34** en la rama normal, **×7,50 / ×7,06 / ×7,02** en la degradada — la rama
degradada **no cambia** (nunca materializó `csv_filas`, era `csv.Error` antes de construir
nada), y es justo el control de que la mejora viene de donde se dice. El ratio de RAM es
determinista entre corridas (`tracemalloc` cuenta bytes asignados, no tiempo): repetido a 8 MB
dio ×6,18 las dos veces. El tiempo (`ms`) es indicativo, n=1, sin los dos testigos de ruido de
`CLAUDE.md` §3 — no se publica como cifra de rendimiento, solo de orden de magnitud.

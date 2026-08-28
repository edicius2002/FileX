# `bench/salidas-ventana/` — N12, la ventana entre la detección y el `move`

Todo lo de aquí es **texto** y se versiona. No hay binarios: los ficheros que
fabrican los arneses (rásteres, salidas `.webp`, ficheros de tercero) viven en
un desechable de `%TEMP%` que se borra al terminar cada tanda, y el arnés
**lista el desechable antes y después** (R21).

Informe: `bench/ventana-antes-del-move.md`.

## Los tres arneses

| Fichero | Qué hace |
|---|---|
| `tercero.py` | El proceso que **no** es FileX. Tres modos: `abrir` (ocupa y se queda), `esperar` (se cuela en la ventana avisado por un centinela), `martillo` (golpea el destino sin sincronizar con nadie). |
| `sonda_mecanismo.py` | Sondeo **en ejecución** de las cinco piezas del movimiento: `shutil.move`, `os.replace`, el `errno` de cruzar volúmenes y `CreateFileW` con `FILE_SHARE_NONE`. Sin carreras: todos los estados se construyen a mano. |
| `medir_ventana.py` | La ventana: duración (modo A), reproducción sincronizada (modo B) y control sin gancho (modo C). |
| `coste_move.py` | Lo que cuesta el arreglo, **medido aislado** (trampa 36). |

## Cómo se reproduce, exactamente

Desde la raíz del repositorio, con el corpus de LFS ya materializado
(`git lfs checkout` — trampa 34; `corpus/imagen/tipico.png` tiene que pesar
**42 855 B**, no 130):

```
python bench/salidas-ventana/sonda_mecanismo.py

python bench/salidas-ventana/medir_ventana.py --modo A --escenario E1 --n 12
FILEX_MOVE_SEGURO=0 python bench/salidas-ventana/medir_ventana.py --modo A --escenario E1 --n 15 --etiqueta antes
python bench/salidas-ventana/medir_ventana.py --modo A --escenario E1 --n 15 --etiqueta despues

FILEX_MOVE_SEGURO=0 python bench/salidas-ventana/medir_ventana.py --modo B --escenario E2 --n 12 --etiqueta antes
python bench/salidas-ventana/medir_ventana.py --modo B --escenario E2 --n 12 --etiqueta despues
FILEX_MOVE_SEGURO=0 python bench/salidas-ventana/medir_ventana.py --modo B --escenario E1 --n 12 --etiqueta antes
python bench/salidas-ventana/medir_ventana.py --modo B --escenario E1 --n 12 --etiqueta despues

FILEX_MOVE_SEGURO=0 python bench/salidas-ventana/medir_ventana.py --modo C --escenario E2 --n 40 --etiqueta antes
python bench/salidas-ventana/medir_ventana.py --modo C --escenario E2 --n 40 --etiqueta despues

python bench/salidas-ventana/coste_move.py          # FILEX_N=1500 por defecto
```

`FILEX_MOVE_SEGURO=0` devuelve el `shutil.move` anterior a N12; es la única
forma honesta de comparar el antes y el después **dentro de la misma tanda**.

`coste_move.py` usa este mismo directorio como «el otro volumen» (está en `D:`
y `%TEMP%` en `C:`) y borra su `tmp-otro-volumen/` al terminar. Con las dos
rutas en el mismo disco, las filas 5 y 6 no se emiten.

## Las salidas

| Fichero | Contenido |
|---|---|
| `sonda_mecanismo.json` · `logs/sonda_mecanismo.log` | M1–M5, deterministas. |
| `ventana_A*.json` | Duración de la ventana. Sin tercero. |
| `ventana_B*.json` | Reproducción con centinela. `la_ventana_se_abrio` por celda. |
| `ventana_C*.json` | Control sin gancho, n=40. |
| `coste_move.json` | 11 filas aisladas, n=1 500 (400 al cruzar volumen). |

**Dos tandas se descartaron y no están aquí**, porque el arnés que las produjo
estaba mal y hay que decirlo:

* la primera pasada del modo A midió con `time.time_ns()`, que en esta máquina
  tiene un tic de **15,625 ms** y publicaba ~1 ms de mediana para una ventana de
  medio milisegundo (era el reloj, no el código);
* las dos primeras del modo C topaban el registro del martillo en 5 000
  aperturas y abrían el destino en modo `append`, así que `la_ventana_se_abrio`
  salía `False` en celdas en las que sí se había abierto y el fichero crecía a
  76 MB.

Los ficheros vigentes se produjeron con los arneses tal y como están hoy.

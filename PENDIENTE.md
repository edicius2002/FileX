# Lo que queda por hacer

**Al 04/09/2026**, tras fusionar la ronda 13 (cinco carriles) y los arreglos de maestro de
`orden/arreglos-04sep`. Este fichero es la lista corta y accionable; el inventario completo
—**121 filas**— vive en [`ESTADO-Y-REPARTO.md`](ESTADO-Y-REPARTO.md) §3 y lo cuenta a
máquina `ci/integridad.py`.

```
inventario   6 ⚫ · 3 🔴 · 4 🟡 · 108 🟢   sobre 121 filas
suite        478 passed · 3 skipped · 175 subtests · 209,38 s
             (03/09, win32 3.11.9, Docker levantado, sobre el árbol unido de la
              ronda 13 — DECLARADO en `360de34`, no reverificado el 04/09)
CI           integridad ✓ · suite-linux ✓ — 18 de 19 módulos · 450 pruebas ·
             110 saltadas · 10,776 s (ejecución 33834111090)
```

Este documento **no** toca `ESTADO-Y-REPARTO.md` ni `CLAUDE.md` ni ningún módulo de
`filex/` — sólo los lee.

---

## 1. La observación que gobierna todo lo demás

**El inventario está agotado de trabajo barato y medible.** De las 7 filas vivas, **una** es
una medida que un worker puede cerrar (`B3`), **tres** son residuos que ya tienen su techo
medido por dos rutas independientes (`C28`, `C16`, `C36`) y **tres están bloqueadas por algo
que no está en esta máquina** (`C6` clave de API, `C7` datos de demanda, `C5` la VM de WSL2).

**Consecuencia para el reparto: la ronda 14 es la última que se puede despachar así.** Lo que
venga después no lo desbloquea otro worker — lo desbloquea el mundo exterior o una decisión.
Seguir despachando rondas simétricas sería fabricar trabajo, que es el defecto contra el que
se cerraron `B4` y `B5`.

---

## 2. Cerrado desde la versión anterior de este fichero (03/09)

Seis filas, y una de ellas refutando su propia hipótesis de partida:

| | Qué era | Cómo cerró |
|---|---|---|
| **`C42`** | 10 de 17 módulos no corrían en el runner | La hipótesis del sistema de ficheros era **falsa** — eran punteros de Git LFS, y por eso cinco intentos no la reprodujeron: **cada intento corría con el corpus real, y el fallo sólo existe donde el corpus no está** |
| **`N32`** | El suelo temporal de `N9` en la cola (p90 a 1,88×) | Suelo por operación, y la cola **no reproduce**: era contención de CPU, no una propiedad del suelo |
| **`C46`** | Las dos guardas del acuerdo `spa`/`eng` | Separan **8 de 8** documentos |
| **`C47`** | `ci/linux-apto.json` declaraba 7 módulos mientras el runner medía 16 | Fichero congelado contra el runner ya fusionado (`18f4602`) y `deriva` en verde sobre ese sha |
| **`B27`**, **`N33`** | Nuevas | Nacen cerradas |

Y **`B3` retrocedió de 🟡 a 🔴**, que es honesto: no se pudo medir `marker` porque lanza un
contenedor vLLM con `--gpus device=0` **sin tomar el lock de GPU**.

---

## 3. Lo que sigue abierto

### Medible por un worker — **una fila**

| | Qué falta |
|---|---|
| **`B3`** 🔴 | **marker, con el lock tomado.** Los dos intentos de worker10 se gastaron en *evitar* la GPU (`--mode fast`, `TORCH_DEVICE=cpu`) y el `docker run --gpus device=0` reapareció las dos veces. **El camino (a) del propio informe nunca se intentó**: tomar el lock y dejar que la use, aunque el venv sea CPU. El arnés y la verdad conocida ya están escritos (`bench/salidas-suelo-n32/medir_marker.py`, `corpus/pdf/tipico_texto.pdf`) |

### Residuos con su techo ya medido — **tres filas**

Ninguna se cierra midiendo más de lo mismo: se cierran **escribiendo el techo** con su coste.

| | Dónde está el techo |
|---|---|
| **`C28`** 🟡 | **15/56 con FATE**, medido por worker2 (ronda 11) y worker11 (ronda 13). Quedan **41 aristas que FATE no puede cerrar** — el propio techo lo declara |
| **`C16`** 🟡 | **95 de 445 formatos**, semiarista **91/95 viva (95,8 %)**. Quedan **350 sin fichero real conocido**. Es una **cota inferior**, no un 54,78 % pendiente |
| **`C36`** 🟡 | **2 de 7 cerrados.** De los cinco vivos, **tres son viables** (subsunción automática, idempotencia ante `Resolve(ListRoots)` doble, qué sustituye a `roots` en el protocolo 2026-07-28); el ítem 1 pide otro modelo con n≥10 y el 3 pide **una emisión real** de `notifications/roots/list_changed`, que lleva sin observarse desde el hito 4 y **no se puede forzar** |

### Bloqueado fuera de esta máquina — **tres filas**

| | Qué falta |
|---|---|
| **`C5`** 🟡 | Mitad cerrada. La carrera de symlinks en Linux: el arnés está listo y **la VM de WSL2 cae con `0x8007274c`** bajo contención. *«No es un resultado negativo: es una medición no hecha»* |
| **`C6`** 🔴 | Una clave de API que no existe en esta máquina |
| **`C7`** 🔴 | Datos de demanda real de conversiones, no una medición de máquina |

---

## 4. Decisiones abiertas, y son del usuario

1. **`.venv-marker` son 1,3 GB** y está en la lista protegida de `CLAUDE.md` §1. Si `B3` acaba
   descartada como `B4` y `B5`, no queda motivo para conservarlo. worker10 reservó esta
   pregunta explícitamente para el maestro y sigue sin respuesta.
2. **`C47`, la mitad que no es medida:** la lista se regenera **a mano**, que es el statu quo —
   el job `deriva` falla y nombra el remedio, no se autoparchea—. Convertirlo en un trabajo que
   abra el PR sería diseño nuevo; **no se ha pedido y no se ha hecho**.

---

## 5. Fuera del repositorio — sólo el usuario puede

1. **La contraseña de SnapOtter sigue viva en el contenedor.** Se borró de las 65 revisiones el
   31/08 y del residuo de `.git` el 01/09 (trampa 102), pero **eso no la cambia en el
   contenedor**.
2. **`fabian.espinoza@ucsp.edu.pe` es público** en los commits. Cambiarlo pide otra reescritura
   de historia, que volvería a matar todas las citas de hash (lo que costó reparar el 01/09).
3. **Los respaldos pre-limpieza** (`FileX-git-backup-20260831.tar.gz` y compañía, con el
   historial sin limpiar dentro) **no se localizaron** al verificarlo el 03/09. No se afirma
   aquí ni que existan ni que no existan. Si siguen en algún sitio, siguen siendo el mismo
   riesgo.

---

## 6. Un desfase que este fichero no arregla

`README.md` declara la suite en **460 passed · 3 skipped · 130 subtests · 243,58 s**, que es
una medida **anterior** a fusionar la ronda 13; el árbol unido declara **478 · 3 · 175** en
`360de34`. Las dos son honestas y miden árboles distintos. **No se toca aquí porque
reverificarla exige correr la suite**, y un recuento de suite necesita sus cuatro
declaraciones —intérprete, entorno, qué quedó fuera y estado de la máquina— o no dice qué se
ejecutó (trampas 94 y 101).

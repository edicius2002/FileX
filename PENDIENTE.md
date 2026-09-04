# Lo que queda por hacer

**Al 04/09/2026**, tras fusionar la ronda 16. Este fichero es la lista corta y accionable;
el inventario completo —**126 filas**— vive en
[`ESTADO-Y-REPARTO.md`](ESTADO-Y-REPARTO.md) §3 y lo cuenta a máquina `ci/integridad.py`.

```
inventario   6 ⚫ · 3 🔴 · 3 🟡 · 114 🟢   sobre 126 filas
             (contado a máquina el 04/09 por `ci/integridad.py`)
suite        501 passed · 3 skipped · 0 failed · 179 subtests · 265,49 s
             (04/09, win32 3.11.9, Docker 29.4.3 levantado, corpus de LFS
              materializado, máquina NO despejada — las cuatro declaraciones,
              enteras, en `README.md`)
```

> **La sección §1 y las tablas de §2 y §3 de este fichero describen el reparto tal como
> estaba tras la ronda 13**, que es cuando se escribieron. El recuento de arriba sí está
> reverificado hoy; el detalle fila a fila **no**, y la fuente vigente es
> `ESTADO-Y-REPARTO.md` §3. Se deja dicho en vez de reescribirlo de memoria: una lista de
> filas rehecha sin volver a mirar el inventario sería exactamente la cifra caducada que
> este documento existe para evitar.

> **Vocabulario, para quien llegue de fuera.** Este proyecto se desarrolla en **rondas** de
> trabajo paralelo, y cada carril de una ronda lo lleva una sesión con un identificador
> (`worker1`, `worker2`…); **«el maestro»** es quien integra y verifica lo que entrega cada
> carril. Esos nombres aparecen aquí como **atribución de quién midió cada cosa**, que es la
> trazabilidad que el repositorio exige a cualquier cifra — no como reparto de trabajo
> vigente ni como algo que un lector tenga que seguir. Las filas (`B3`, `C28`…) son
> identificadores del inventario de [`ESTADO-Y-REPARTO.md`](ESTADO-Y-REPARTO.md) §3.

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
2. **La dirección de correo del autor es pública** en los metadatos de los commits. Cambiarla
   pide otra reescritura de historia, que volvería a matar todas las citas de hash (lo que
   costó reparar el 01/09). *(Aquí no se repite la dirección literal: está en
   `git log`, que es donde el interesado puede verla, y escribirla otra vez en un fichero
   del árbol sólo añade una copia más que indexar.)*
3. **Los respaldos pre-limpieza** (`FileX-git-backup-20260831.tar.gz` y compañía, con el
   historial sin limpiar dentro) **no se localizaron** al verificarlo el 03/09. No se afirma
   aquí ni que existan ni que no existan. Si siguen en algún sitio, siguen siendo el mismo
   riesgo.

---

## 6. Un desfase que este fichero ya no arregla porque está arreglado

**CERRADO el 04/09/2026.** Este apartado decía que `README.md` declaraba la suite en
**460 passed · 3 skipped · 130 subtests · 243,58 s** —medida **anterior** a la ronda 13,
frente a los **478 · 3 · 175** del árbol unido— y que no se tocaba porque reverificarla
exigía correr la suite.

Se corrió: **501 passed · 3 skipped · 0 failed · 179 subtests · 265,49 s**, con las cuatro
declaraciones —intérprete, entorno, qué quedó fuera y estado de la máquina— escritas en
`README.md`. El recuento **reproduce exactamente** el de `bench/raices-mixtas.md` §8; el
tiempo no, y no tiene por qué: las cifras absolutas de tandas distintas no son comparables y
las relativas dentro de una tanda sí (`CLAUDE.md` §3).

**Ninguna de las dos cifras anteriores era falsa: medían árboles distintos.** Lo que era un
defecto es que el `README` no dijera cuál.

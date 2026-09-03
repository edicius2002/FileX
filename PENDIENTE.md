# Lo que queda por hacer

**Al 03/09/2026**, con `main` en `873942c`, la CI en pie y las rondas 12 de los carriles
`filex-gpu` y `filex-cpu` despachadas y en curso. Este fichero es la lista corta y
accionable; el inventario completo —**118 filas**— vive en
[`ESTADO-Y-REPARTO.md`](ESTADO-Y-REPARTO.md) §3, y se cuenta con la orden que hay ahí (la
misma que ejecuta `ci/integridad.py`).

```
inventario   6 ⚫ · 6 🔴 · 9 🟡 · 97 🟢   sobre 118 filas
suite        460 passed · 3 skipped · 0 failed · 130 subtests · 243,58 s
             (03/09, win32 3.11.9, Docker levantado, máquina despejada)
CI           integridad ✓ · suite-linux ✓
```

Este documento **no** toca `ESTADO-Y-REPARTO.md`, `CLAUDE.md` ni ningún módulo de
`filex/` — sólo los lee. Y no reparte trabajo nuevo entre `filex-gpu`/`filex-cpu`: eso lo
decide quien lleva esos carriles, no este documento.

---

## 1. Las cuatro decisiones de la ronda anterior — **LAS CUATRO YA ESTÁN RESUELTAS**

La versión de este fichero del 01/09 las listaba como abiertas. Comprobado hoy contra
`ESTADO-Y-REPARTO.md`: las cuatro se decidieron y tres de las cuatro ya están además
**implementadas y verificadas**. Se dejan aquí, tachadas, para que quien busque el
razonamiento no tenga que ir a buscarlo a otro documento — no para reabrirlas.

- ~~**`C43` — la huella y el intérprete**~~ **CERRADO el 02/09** (`bench/huella-y-runner.md`,
  verificado por el maestro). Se declara el intérprete de sellado (granularidad
  `mayor.menor`) y se niega la comparación entre intérpretes distintos: ya no caduca
  ninguna de las 215 aristas selladas. Detalle en la trampa 105 de `CLAUDE.md`.
- ~~**¿Runner autoalojado?**~~ **DECIDIDO el 02/09: autoalojado, con aprobación manual**
  para PRs de terceros. `C44` — **entregada y verificada** (commit `b582ceb`): el diseño
  está cerrado. Lo único que queda, y no es trabajo de este repositorio: **registrar el
  runner es del usuario**.
- ~~**marker / surya / MinerU**~~ **DECIDIDO el 02/09.** `B5` (MinerU) y la mitad de `B4`
  (surya) se cierran **descartados** por decisión — diez días abiertos sin una sola cifra.
  `B3` (marker) se decidió **medir**: sigue 🟡 *(`DECIDIDO, ronda 9`)*, es trabajo del
  carril GPU, no una decisión pendiente.
- ~~**¿El veredicto de un PR es la CI o soy yo?**~~ Seguía **RESUELTO** desde el 01/09: el
  maestro empuja, abre el PR y fusiona — los workers no tienen credenciales de `gh`
  (`CONTRIBUTING.md` §7).

---

## 2. Lo que los otros carriles están corriendo ahora — ronda 12, despachada el 03/09

No hace falta repetirlo aquí con detalle: `ESTADO-Y-REPARTO.md` §4 lo lleva ronda a ronda.
Resumen de a qué apunta cada carril, para no tener que ir a buscarlo:

| Carril | Filas | Informe (en curso) |
|---|---|---|
| `filex-gpu` (worker1) | `B7` + `B8` | `bench/senal-severidad-y-psm.md` — cierra la otra mitad de sus propios hallazgos de la ronda 10 |
| `filex-cpu` (worker2) | `N30` (arreglar, no sólo documentar) + `C45` (anclar acciones de CI por `sha`) | `bench/pruebas-de-carrera-y-acciones.md` |

---

## 3. Deuda que la CI cuenta — `ci/heredado.json`

De las cuatro filas que motivaron el trinquete el 01/09, **tres ya están cerradas**:

| | Qué era | Estado hoy |
|---|---|---|
| ~~`C40`~~ | 3 binarios sueltos fuera de LFS | 🟢 **CERRADO** — `ci/integridad.py` da `0 sueltos · 3 rutas declaradas evidencia` (trampa 106) |
| ~~`C41`~~ | 17 directorios `bench/salidas-*` sin manifiesto | 🟢 **CERRADO** — `0 sin MANIFIESTO heredados` |
| ~~`C43`~~ | La huella y el intérprete | 🟢 **CERRADO** — ver §1 |
| **`C42`** | 10 de 17 módulos no corrían en el runner | 🟡 **9 de 10 causas clasificadas y arregladas con código; 1 sin reproducir** (`test_watcher_n`, inestable entre tres sistemas de ficheros POSIX distintos). La promoción final de módulos a `aptos` sigue pendiente de una corrida en `ubuntu-latest` real, no en la aproximación de contenedor |

---

## 4. Abierto sin ronda asignada todavía

Dos filas nuevas de esta semana que ningún carril tiene tomadas en la ronda 12:

| | Qué es |
|---|---|
| **`C46`** | El residuo de `C20`: al acuerdo `spa`/`eng` (el sustituto de `P9`) le faltan dos guardas — una longitud mínima no vacía y una comparación que no penalice sustituciones de un solo carácter acentuado. Sin ellas, 2 de 8 documentos leen al revés. **No es una continuación de `C20`: esa fila se cerró refutando su propio enunciado**, así que esto es una hipótesis nueva (`bench/acuerdo-y-cruce.md` §2.3) |
| **`N32`** | El suelo temporal de `N9` (`PISO_TEMPORAL_S`) cierra el oráculo a la MEDIANA pero no en la cola: a p90 sigue en 1,88× sobre el denegado. Subir el suelo cierra la cola y sube el coste del rechazo — el mismo conflicto de `N9` un nivel más abajo (trampa 28). Hay una salida sin medir: un suelo por OPERACIÓN en vez de por llamada (`bench/oraculo-y-gotenberg.md` §1.4-1.5) |

---

## 5. Bloqueado, y por qué

| | Qué falta |
|---|---|
| **`C6`** | Una clave de API que no existe en esta máquina — replicar la saturación en dominio documental con `temperature` fija |
| **`C7`** | Datos de demanda real de conversiones, no una medición de máquina |

`C16`/`C28` **ya no están bloqueadas**: el corpus FATE (2 529 ficheros, 1 345 840 190 B) se
bajó fuera del repositorio el 02/09 y ambas avanzaron con él en la ronda 11
(`bench/fate-y-aristas.md`). `C28` sigue 🟡 con 56 aristas completas por resolver, pero eso
ya es trabajo, no bloqueo.

---

## 6. Fuera del repositorio — sólo el usuario puede

1. **La contraseña de SnapOtter sigue viva en el contenedor.** Se borró de las 65
   revisiones el 31/08 y del residuo de `.git` el 01/09 (trampa 102), pero **eso no la
   cambia en el contenedor** — sigue siendo la misma credencial dentro de él.
2. **`fabian.espinoza@ucsp.edu.pe` es público** en los commits. Cambiarlo pide otra
   reescritura de historia, que volvería a matar todas las citas de hash (lo que costó
   reparar el 01/09) — decisión del usuario, no automática.
3. **Los respaldos pre-limpieza citados en la versión anterior de este fichero**
   (`FileX-git-backup-20260831.tar.gz` y compañía, con el historial sin limpiar dentro) —
   **no se localizaron hoy** en `D:\Work\research\` al verificar este punto. Puede que se
   hayan movido, renombrado o ya se hayan limpiado; **no se afirma aquí ni que existan ni
   que no existan**, porque no se pudo comprobar desde este *worktree*. Si siguen en algún
   sitio con la credencial dentro, siguen siendo el mismo riesgo que describía la versión
   anterior de este documento.

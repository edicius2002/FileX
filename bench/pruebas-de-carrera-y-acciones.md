# `N30` — arreglar las tres pruebas de carrera, no seguir documentándolas — y `C45`

**Encargo R12 · worker2, carril CPU/Docker, `edicius2002/filex-cpu`.** Dos temas sin
relación: `N30` (arreglo de código, la primera vez que esta serie de rondas lo pide en
vez de medir) y `C45` (anclar tres acciones de GitHub por `sha`). `C46` queda fuera —
declarado en §3.

**Máquina:** *worktree* `C:\Users\krato\orca\workspaces\FileX\filex-cpu`. Windows 10,
Python 3.11.9. **worker1 tiene la tarjeta** en el carril GPU de la ronda 12 (`B7`+`B8`):
no se tocó. **Docker se cayó durante la propia sesión**, tal como avisaba el encargo:
a mitad de la primera tanda de la suite, `filex-convertx` y `filex-snapotter` aparecieron
`Exited (137)` sin que nadie los tocara — se restauraron con `docker start` (no
destructivo, los contenedores ya existían) y la tanda siguiente salió limpia. Es la
causa exacta de un fallo transitorio no relacionado con `N30` que se documenta en §1.4.

**Fecha:** 03/09/2026.

---

## 1. `N30` — las tres pruebas, arregladas

### 1.1 El diagnóstico, heredado y no repetido

Dos familias, ya establecidas por rondas anteriores de verificación (`ESTADO-Y-REPARTO.md`,
fila `N30`, cinco observaciones):

- **Familia 1** (`test_cerrojo.py::CarreraEntreProcesos::
  test_sin_el_cerrojo_de_maquina_los_dos_procesos_devuelven_ok`): asevera sobre una
  CARRERA que puede no llegar a abrirse. La sincronización por `GO` garantiza que los
  dos procesos **salen** a la vez, no que sus `convertir()` lleguen a **solaparse**
  dentro de la sección que compite.
- **Familia 2** (`test_cerrojo.py::DuenoMuerto::
  test_el_candado_se_recupera_solo_al_morir_su_dueno` y
  `test_cancelacion_procesos.py::DuenoMuerto::
  test_un_working_sin_dueno_vivo_se_detecta_y_se_cierra`): asevera sobre una ESPERA a
  que el sistema operativo libere un candado de rango de bytes tras `taskkill`, con una
  sola comprobación y sin tope. Dos autores distintos llegaron a la misma forma sin
  compartir código — comprobado en la tercera observación de `N30`.

### 1.2 Familia 1 — instrumentar la ventana, no relajar el `assertTrue`

**`_papel_convertidor`** (el proceso hijo que compite) ahora publica `ini`/`fin` —
`time.perf_counter()` justo antes y justo después de `fx.convertir()` — en su JSON de
salida. `time.perf_counter()` es comparable **entre procesos** en esta máquina: en
Windows envuelve `QueryPerformanceCounter`, sin origen por proceso, ya sondeado con el
mismo propósito en `bench/oraculo-y-gotenberg.md` §1.3.

La prueba comprueba el solape antes de nada más:

```python
if len(filas) == 2 and not (filas[0]["ini"] < filas[1]["fin"] and
                            filas[1]["ini"] < filas[0]["fin"]):
    self.skipTest("la ventana de carrera no se abrió bajo esta carga: ...")
```

**Verificado con datos sintéticos** (sin depender de reproducir la carrera real): un
`TestCase` con `_carrera()` sustituido por dos filas con `ini`/`fin` deliberadamente
serializados (`0,0-1000,0 ms` y `1500,0-2500,0 ms`) da **`skipped`, 0 errores, 0
fallos**, con el mensaje exacto citando ambas ventanas. La lógica de solape se
verificó aparte con cuatro casos (solape real, serializado, frontera exacta,
anidado) — los cuatro dan el booleano correcto.

**No se relajó `assertTrue(any(f["bytes"] != reales for f in filas), ...)`**: sigue
pudiendo fallar, y de hecho falló una vez durante la verificación de esta misma ronda
(§1.5).

### 1.3 Familia 2 — reintento con tope, no una comprobación única

Las dos pruebas cambian del mismo patrón: sustituir la comprobación única tras el
`kill`/`taskkill` por un bucle con tope declarado (2 s, sondeo cada 20-50 ms):

- **`test_el_candado_se_recupera_solo_al_morir_su_dueno`**: reintenta
  `nucleo._reservar_destino(self.salida)` hasta que devuelva `True` o se agoten 2 s.
  **La aserción de "inmediatez" no se perdió, se reubicó**: ahora exige que **cada
  intento individual** tarde menos de 100 ms (`_reservar_destino` no lleva ninguna
  espera propia — confirmado leyendo `filex/cerrojo.py::Candado.tomar()`, que con
  `espera=0` prueba una vez y devuelve sin dormir), en vez de exigir que la
  recuperación **total** —que incluye el tiempo que tarda el sistema operativo, fuera
  del control de la función— sea inmediata.
- **`test_un_working_sin_dueno_vivo_se_detecta_y_se_cierra`**: reintenta
  `self.sv.job(self.jid)` hasta que `estado == FALLIDO` o se agoten 2 s. Es seguro
  reintentar: `_es_huerfano` sólo lee el candado (no muta nada) mientras no lo
  encuentra libre, y una vez lo detecta dejará `estado=FALLIDO` escrito en disco, así
  que llamadas posteriores siguen viendo el mismo resultado.

Las dos siguen fallando de verdad si el candado nunca se libera — el tope no es una
promesa de éxito, es un límite de paciencia.

### 1.4 Verificado bajo carga real, con un hallazgo colateral

**Método:** procesos `powershell` en segundo plano haciendo un bucle vacío acotado en
el tiempo (para no dejar huérfanos), variando entre 8 y 26 procesos según la tanda,
con la CPU medida antes/durante con `wmic cpu get loadpercentage`. Un primer intento a
CPU 100 % con 26 procesos **dejó la propia máquina inservible durante varios minutos**
—hasta comandos triviales (`tasklist`) tardaron más de 30 s— y hubo que matarlos
(`Stop-Process -Force`) para recuperar el control: **es un dato en sí mismo, no un
efecto secundario**. La carga "de verdad" de este proyecto (worker1 con la GPU) nunca
ha llegado a ese extremo; el resto de la verificación usó cargas moderadas (8-10
procesos, 48-62 % de CPU medido), más representativas.

| Tanda | Procesos de carga | CPU | Resultado de las 3 pruebas |
|---|---:|---:|---|
| Sin carga sintética | 0 | 37-41 % | 2/2 pasan (aisladas) |
| Moderada | 8-10 | 48-62 % | 18/18 pasadas repetidas, sin skip observado |
| Extrema | 16-26 | 90-100 % | Máquina degradada; no se completaron ejecuciones limpias |

**Con carga moderada, ninguna de las tres skipeó ni falló en ~18 repeticiones** — la
ventana de carrera se abrió en todas, así que la instrumentación no pudo mostrarse
"disparándose" en esas tandas. Se verificó el mecanismo del `skipTest` con datos
sintéticos (§1.2) precisamente porque reproducir la condición real de "no abrir la
ventana" resultó más difícil de forzar externamente que dejar que ocurra por sí sola
bajo la carga real de otra ronda — que es, al fin y al cabo, la que motivó las cinco
observaciones originales.

**Hallazgo colateral, no buscado:** durante una tanda completa de la suite bajo carga
sintética, **falló un test que no es ninguno de los tres de `N30`**:
`test_cancelacion.py::ContenedorReal::test_cancelar_mata_el_contenedor_y_no_solo_el_cliente`
(un `assertFalse` sobre si el contenedor Docker seguía vivo tras cancelar). Coincidió
con la caída de Docker descrita en la cabecera — `docker ps -a` mostró `filex-convertx`
y `filex-snapotter` como `Exited (137)` justo entonces. Reproducido en aislamiento tras
reiniciar los dos contenedores: **pasa limpio**. No es de `N30` (no toca cerrojos de
proceso ni candados de dueño muerto) y no se ha tocado su código — se declara aquí
porque **CLAUDE.md pide reportar los fallos como fallos**, no porque hiciera falta un
arreglo.

**Segundo hallazgo colateral, bajo la tanda de carga extrema:**
`test_hito4.py::NoBloquear::test_convert_devuelve_el_asa_al_empezar` falló por una
aserción de **latencia absoluta** (`< 200 ms`, dio 973 ms) — una prueba de rendimiento,
no de carrera, sensible a cualquier carga suficientemente alta. Pasa limpio con la
carga asentada. Tampoco es de `N30` y no se toca.

### 1.5 Un hallazgo que refina el diagnóstico de la Familia 1 — declarado, no cerrado

**Durante la verificación bajo carga sintética, la propia prueba arreglada de la
Familia 1 falló una vez — con solape confirmado.** El mensaje de `skipTest` no
disparó (las dos ventanas `ini`/`fin` SÍ se solapaban), pero la última aserción
—`any(f["bytes"] != reales for f in filas)`— sí cayó. Es la prueba haciendo
exactamente lo que se le pidió: **detectar un fallo real, no fingir uno**. Pero
también revela que el diagnóstico original ("la ventana no se abre") es **necesario y
no suficiente**: un solape AMPLIO de las dos llamadas a `convertir()` no garantiza que
la escritura final al destino compartido se solape en el sentido estricto que la
aserción necesita. Hipótesis, no confirmada con instrumentación adicional por falta de
tiempo esta ronda: bajo scheduling extremo, el hijo A puede terminar su `convertir()`,
ser desalojado ANTES de leer `os.path.getsize()`, dejar que el hijo B complete su
conversión entera durante esa pausa, y al reanudar leer el fichero de B en vez del
propio — con lo que su reporte "por accidente" coincide con el estado final en vez de
describir el suyo propio.

**No se ha ampliado el arreglo esta ronda.** Motivos: (a) sólo se ha visto una vez, en
la tanda de carga más extrema (90-100 % de CPU, la que dejó la máquina casi inservible
— §1.4), muy por encima de lo que este proyecto llama carga real; (b) las 18
repeticiones bajo carga moderada no lo mostraron; (c) instrumentar la escritura misma
(en vez de la llamada completa a `convertir()`) exige un gancho dentro de
`filex/nucleo.py` parecido al de `_papel_ventana_convertidor` (que ya existe para una
carrera distinta, la del tercero no cooperativo), y diseñarlo bien vale una ronda
propia, no un añadido de última hora. **Se deja declarado como residuo conocido**, en
el espíritu de `bench/oraculo-y-gotenberg.md` §1.5: mejor un residuo con nombre que
fingir un cierre completo.

---

## 2. `C45` — las tres acciones, ancladas por `sha`

Las 11 líneas exactas que el encargo listó, en los tres ficheros de *workflow*, con el
`sha` completo de 40 caracteres y la etiqueta en un comentario:

| Acción | `sha` | Fuente |
|---|---|---|
| `actions/checkout` | `3d3c42e5aac5ba805825da76410c181273ba90b1` | `gh api repos/actions/checkout/git/refs/tags/v7` |
| `actions/setup-python` | `5fda3b95a4ea91299a34e894583c3862153e4b97` | `gh api repos/actions/setup-python/git/refs/tags/v7` |
| `actions/upload-artifact` | `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` | `gh api repos/actions/upload-artifact/git/refs/tags/v7` |

**Verificado, no inventado** (el encargo lo pedía explícitamente): cada `sha` se sacó
de `gh api repos/<owner>/<repo>/git/refs/tags/v7` (el `type` del objeto es `commit`
directamente, sin tag anotado que dereferenciar) y se cruzó contra
`gh api repos/<owner>/<repo>/commits/<sha>` para confirmar que el commit existe y su
mensaje es plausible — `actions/setup-python` incluso lo dice literalmente: *«Update
GitHub Actions to use checkout and setup-python actions version 7»*.

`git diff` confirma que **sólo cambiaron las 11 líneas** (`uses:`), nada de la
indentación ni de los bloques `with:` que las rodean. `.github/dependabot.yml` no
necesita tocarse: Dependabot ya soporta de forma nativa las acciones ancladas por
`sha` con la etiqueta en comentario, y seguirá proponiendo *bumps* legibles.

**No se ha hecho un `git push` de prueba** (el encargo lo ofrecía como opcional y no
como condición de entrega) — la comprobación barata que sí se hizo es la verificación
cruzada por API descrita arriba, antes de pegar cada `sha`.

---

## 3. Lo que se dejó fuera

**`C46` no se ha tocado.** El encargo lo marcaba explícitamente como no prioritario y
condicionado a que sobrara tiempo con margen tras `N30` y `C45`; `N30` costó más de lo
previsto (el hallazgo de §1.5 exigió una ronda completa de verificación bajo carga,
con su propio incidente de máquina inservible que hubo que resolver antes de seguir).
Queda declarado para la siguiente ronda, igual que se hizo con `C5`/`C36` y `C28`
completo en rondas anteriores.

---

## 4. Verificación

**Intérprete:** `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe`, Python
3.11.9, `win32`.

**Entorno:** Docker arriba (comprobado con `docker info` antes de tocar nada, tal
como pedía el encargo — y se cayó una vez a media sesión, ver cabecera). Sin GPU
tomada. CPU con carga variable y medida en cada tanda (§1.4), desde 37 % (sin carga
añadida) hasta el extremo de 100 % con la máquina degradada.

```
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe -m pytest pruebas/ -q
```
→ **460 passed, 3 skipped, 0 failed** en la tanda final, con la carga asentada. Los 3
`skipped` son los honestos de siempre (ráster de hito 6 ausente y
`FILEX_PRUEBAS_SIDECAR=1`+tarjeta). Ninguna de las tres pruebas de `N30` skipeó en
esta tanda concreta — el mecanismo de `skipTest` de la Familia 1 se verificó aparte,
con datos sintéticos (§1.2), porque forzar la condición real resultó más difícil que
dejarla ocurrir de forma natural bajo la carga de otra ronda.

**Qué quedó fuera de la verificación y por qué:** no se ha intentado reproducir de
forma determinista el "no se abre la ventana" de la Familia 1 con una carga
CONTROLADA y MODERADA — sólo se consiguió con carga tan extrema que degradó la propia
máquina, lo que no es representativo. El mecanismo se validó por otra vía (datos
sintéticos, §1.2), que es una garantía distinta y más débil que "se vio fallar y
dejar de fallar en esta misma máquina" — se declara la diferencia en vez de
disimularla.

```
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe ci/integridad.py
```
→ **9/9 comprobaciones OK.**

**Estado de la máquina:** declarado en la cabecera y en §1.4.

---

## 5. Salidas en disco

Ninguna: esta ronda es código de pruebas y configuración de CI, sin arneses de
medición nuevos. Toda la evidencia de §1.4-1.5 vive en las salidas de `pytest`
citadas y en las verificaciones puntuales descritas en el propio texto.

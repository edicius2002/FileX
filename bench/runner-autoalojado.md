# C44 — el runner autoalojado con aprobación manual: diseño, mecanismo del lock y el premio medido a medias

Informe de **worker1** (carril GPU). Encargo: `ENCARGO-C44.md`, adelantado a la ronda 6 porque
dependía de `N29` (cerrado en `bench/vivo-y-residuos.md`).

**Recordatorio del propio encargo, y se cumplió:** *«no arranques ninguna tanda de GPU: el
maestro va a estar verificando la ronda 5»*. Nada de lo medido aquí toca el lock por defecto ni
la tarjeta de verdad — ver §2 para el detalle exacto de cómo se evitó.

---

## 0. Alcance — qué es mío y qué no, tal como lo fija el encargo

| Sí es mío | Hecho aquí |
|---|---|
| El diseño de seguridad, sondeado con `gh api` | §1 |
| Los ficheros de *workflow* y los cambios en `ci/` | §3 |
| La pregunta del lock, medida | §2 |
| Qué módulos corren sobre Windows | §4 |

| NO es mío, y no lo hice | Por qué se sabe que no |
|---|---|
| Registrar el runner, instalar el servicio | No hay ningún `./config.cmd`/`./run.cmd` en este commit, ni un token pedido |
| Cambiar ajustes del repositorio en GitHub | Todas las llamadas de `gh api` de este informe son `GET`. Ninguna es `PATCH`/`PUT`/`POST`. Ver §1.3 |
| Empujar o abrir PR | `git log` de esta rama no tiene ningún `push`; se para en el commit |

---

## 1. El diseño de seguridad — sondeado, no deducido

### 1.1 Qué tiene el repositorio configurado HOY (`gh api`, `2026-09-02`)

```
$ gh auth status
✓ Logged in to github.com account edicius2002 (keyring)
  Token scopes: 'delete_repo', 'gist', 'read:org', 'repo', 'workflow'

$ gh repo view edicius2002/filex --json isPrivate,visibility,defaultBranchRef
{"defaultBranchRef":{"name":"main"},"isPrivate":false,"visibility":"PUBLIC"}

$ gh api repos/edicius2002/filex/actions/permissions
{"enabled":true,"allowed_actions":"all","sha_pinning_required":false}

$ gh api repos/edicius2002/filex/actions/permissions/workflow
{"default_workflow_permissions":"read","can_approve_pull_request_reviews":false}

$ gh api repos/edicius2002/filex/actions/permissions/fork-pr-contributor-approval
{"approval_policy":"first_time_contributors"}

$ gh api repos/edicius2002/filex/actions/runners
{"total_count":0,"runners":[]}

$ gh api repos/edicius2002/filex/branches/main/protection
{"message":"Branch not protected","status":"404"}

$ gh api repos/edicius2002/filex/actions/secrets
{"total_count":0,"secrets":[]}

$ gh api repos/edicius2002/filex/environments
{"total_count":0,"environments":[]}
```

**MEDIDO**, las nueve líneas. Lectura:

- **Repositorio público, sin ninguna protección de rama en `main`.** Ortogonal a C44
  (no cambia con quién puede correr Actions), pero es una superficie de riesgo que ya
  estaba ahí y que el runner autoalojado no crea ni empeora — se declara porque es lo
  que había, no porque C44 la cierre.
- **`allowed_actions: "all"`** — cualquier acción de cualquier repositorio de GitHub
  puede usarse en un *workflow* de este repo. No es el eje de C44 (no decide QUIÉN
  puede disparar un job en el runner), pero es la superficie que un *workflow*
  malicioso *ya mergeado* podría usar; se deja anotado y fuera de alcance.
- **`default_workflow_permissions: "read"`** — el `GITHUB_TOKEN` que recibe cualquier
  job es de sólo lectura por defecto. Bueno: aunque un job del runner autoalojado se
  viera comprometido, el token que lleva dentro no puede escribir en el repositorio
  sin que un *workflow* lo pida explícitamente (`permissions: contents: write`, que
  **ninguno** de los dos jobs de `windows-gpu.yml` pide — ver §3).
- **0 *runners*, 0 *secrets*.** Confirma que no hay nada que romper por accidente:
  no hay un *runner* ya registrado que un cambio mío pudiera desconfigurar, ni un
  secreto que un job mal diseñado pudiera filtrar.
- **`fork-pr-contributor-approval` = `first_time_contributors`. Ésta es la pieza que
  decide si el diseño de C44 es aceptable, y HOY no lo es por sí sola.** Con este
  valor, un colaborador externo necesita aprobación la PRIMERA vez; **la segunda PR
  del mismo autor corre sin que nadie la mire** — incluidos los *jobs* en el
  *runner* autoalojado. Un atacante paciente manda un PR inofensivo (una errata),
  espera a que lo aprueben, y el SEGUNDO PR ya no pide aprobación de ningún tipo.
  **Éste es el hueco exacto que hace que "aprobación manual" no sea un adorno.**

### 1.2 El mecanismo exacto que impone la aprobación — dos capas, no una

**Capa 1 — el ajuste del repositorio (`fork-pr-contributor-approval`).** Gatea el
*workflow run ENTERO* (todos los *jobs*) cuando lo dispara un `pull_request` de alguien
sin permiso de escritura. El valor de HOY, `first_time_contributors`, está **MEDIDO**
(§1.1, `GET` directo). Los otros dos valores posibles del campo
—`first_time_contributors_new_to_github` y `all_outside_collaborators`— son
**PENDIENTE de confirmar en vivo**: salen de la documentación pública de la API de
GitHub, no de una respuesta de este repositorio. No hay forma de sondear el `enum`
completo sin un `PUT` (aunque sea con un valor inválido, para leer el error de
validación), y un `PUT` es exactamente lo que este encargo prohíbe — así que se deja
como lectura de documentación, marcada como tal, en vez de disfrazarla de medida.
**El único de los tres que cierra el hueco de §1.1, según esa misma documentación, es
`all_outside_collaborators`**: pide aprobación en CADA PR de un no-colaborador, sin
excepción de "primera vez".

**Cambio propuesto, NO aplicado:**

```
gh api --method PUT repos/edicius2002/filex/actions/permissions/fork-pr-contributor-approval \
  -f approval_policy=all_outside_collaborators
```

**Capa 2 — un `environment` con revisores obligatorios, en el propio *workflow*.**
**PENDIENTE de confirmar en vivo, igual que el `enum` de arriba** — no hay ningún
`environment` en este repositorio hoy (0 configurados, no hay nada que listar con
`gh api repos/edicius2002/filex/environments` más allá de una lista vacía) y crear
uno para probarlo sería el mismo tipo de cambio de ajustes que el encargo prohíbe.
Lo que sigue es documentación de GitHub, marcada como tal: un *job* con `environment`
apuntando a un entorno con *"Required reviewers"* configurado se PAUSA hasta que
alguien de la lista lo aprueba en la UI de Actions, para cualquier disparador — no
sólo `pull_request` de *fork*. Si eso se sostiene, esta capa protege incluso si la
Capa 1 se relaja sin querer; **si no se sostiene, el diseño de §3 pasa a depender
solo de la Capa 1**, y hay que decirlo con la misma claridad el día que alguien lo
compruebe con un *runner* de verdad.

**Este entorno NO existe todavía y no lo crea este *commit*.** GitHub crea un
`environment` vacío —sin revisores, es decir **sin protección real**— la primera vez
que un *workflow* lo referencia, si nadie lo ha configurado antes a mano. Es la
diferencia entre "el YAML dice `environment:`" y "el `environment` protege algo", y
hay que decirla en voz alta porque es exactamente el tipo de defecto silencioso que
las trampas 27/33/44 de `CLAUDE.md` ya enseñaron a temer: un campo que parece una
defensa y no lo es hasta que alguien completa la otra mitad.

**Pasos que HAY que dar antes de registrar el *runner*, y que no son míos:**

1. `Settings → Environments → New environment` → nombre exacto `aprobacion-manual-gpu`.
2. Marcar *"Required reviewers"* y añadir al menos una persona (recomendado: el
   propio dueño del repositorio, que es quien tiene la máquina).
3. Cambiar `fork-pr-contributor-approval` a `all_outside_collaborators` (comando de
   arriba).
4. **Sólo entonces** registrar el *runner* (token de `gh api
   repos/edicius2002/filex/actions/runners/registration-token`, que tampoco se pidió
   aquí) con las etiquetas `self-hosted, Windows, gpu, filex` — las tres primeras las
   pone la propia instalación del *runner*; `gpu` y `filex` hay que añadirlas a mano
   al registrar.

**Orden importante:** registrar el *runner* ANTES del paso 1–3 dejaría una ventana —
aunque sea de minutos— en la que un `pull_request` ya podría disparar un *job* sin
aprobación real (la Capa 1 en `first_time_contributors` no basta, y la Capa 2 sin
revisores tampoco). El encargo pide diseñar esto con cuidado precisamente para que
nadie registre el *runner* primero y lo arregle después.

### 1.3 Qué NO se cambió, con la prueba de que no se cambió

Todas las llamadas de `gh api` de esta sesión —las nueve de §1.1 y un par más de
exploración que no dieron información útil (`fork-pr-workflows-approval`, nombre de
endpoint equivocado, `404`; `runner-groups`, que no aplica a una cuenta personal;
`selected-actions`, `409` porque `allowed_actions` ya es `all`)— son `GET`. **Ninguna
es `--method PUT/POST/PATCH/DELETE`.** MEDIDO por inspección directa: es literalmente
lo que se transcribe en §1.1, no una promesa aparte.

---

## 2. La pregunta del lock — MEDIDO, con control positivo y negativo

**Decisión: el *job* de CI se NIEGA a correr los módulos de GPU si el lock está
tomado. No espera indefinidamente.**

### 2.1 Por qué, con número

- `FILEX_GPU_ESPERA` (el que usa `Lock.__enter__` en producción) vale **900 s** por
  defecto — pensado para que un lote humano no se corte a media conversión. Un
  *runner* de CI heredando ese valor podría quedarse **15 minutos** parado encima de
  un lote real sin decir nada útil, y un lote humano puede durar **hasta 40 minutos
  entre configuraciones** (trampa 100) — hay una probabilidad nada despreciable de
  que el *job* de CI pierda contra el reloj de todos modos, sólo que 15 minutos más
  tarde y más caro.
- Tomar y soltar el lock es barato: **~0,6 ms / ~1,1 ms** de mediana (ver abajo), así
  que reintentar cada 250 ms durante una espera corta no cuesta nada por sí mismo —
  lo caro es la ESPERA, no el reintento.
- Recuperar un huérfano real cuesta **0,171 s** en esta máquina — rápido comparado con
  cualquier espera razonable, así que un *job* de CI que SÍ muere a mitad (GitHub lo
  cancela, el *runner* se cae) no dejará el lock inservible para el siguiente
  intento, ni para un *worker* humano.

**Mecanismo:** `ci/lock_preflight.py`, que comprueba el lock con una espera corta
(30 s por defecto) y lo SUELTA de inmediato si lo consigue — no lo sostiene durante
todo el *job*; cada módulo de prueba que de verdad toca la tarjeta sigue tomando el
suyo por su cuenta, con `FILEX_GPU_ESPERA=30` fijado para todo el paso (ver
`windows-gpu.yml`, que también corta ahí el tiempo de espera de cada módulo
individual, no sólo el del preflight).

### 2.2 Medido, con lock AISLADO — cero interferencia con la máquina real

**Metodología, igual que N29:** todas las medidas de esta sección usan un fichero de
lock aislado (`ruta=`), nunca `%TEMP%/filex-gpu.lock`. Ninguna llamada usa
`with gpu.Lock(...)` (que invoca `guardia()` y por tanto `nvidia-smi`); se usa
`.tomar()`/`.soltar()` directos. **Cero consultas a `nvidia-smi`, cero contacto con
el lock real, cero uso de la tarjeta** — script y datos en
`bench/salidas-runner-autoalojado/sonda_lock_ci.py` /
`bench/salidas-runner-autoalojado/sonda_lock_ci.json`.

**Coste de tomar/soltar (n=9, lock aislado):**

```
tomar:  mediana 618,5 µs  (primer intento 9 424,3 µs -- Windows Defender
                            calentando el primer arranque, trampa 7)
soltar: mediana 1 144,8 µs
```

**Control NEGATIVO — dueño vivo, de verdad (proceso hijo real, no un PID
inventado): NO se roba.** Trampa 36: un "no interfiere" sin un caso en que sí
interfiera no significa nada.

```json
{"robo_indebido": false, "dt_s": 1.014, "pid_dueno_vivo": 33592}
```

Con `espera=1.0`, el intento devuelve `False` a los 1,014 s — coincide con el tope
pedido, ni antes (no hay falso robo) ni mucho después (no se queda colgado).

**Control POSITIVO — dueño muerto DE VERDAD (`taskkill /F /T` sobre un proceso hijo
real, exactamente el mecanismo de la trampa 47: `finally` no se ejecuta): SE
recupera, y rápido.**

```json
{"recupero": true, "dt_s": 0.171, "pid_muerto": 33248,
 "campos_lock_antes": ["hijo-ci", "33248", "33248", "python.exe", "...", "..."]}
```

**0,171 s** — la mayor parte es el propio `tasklist` que `_vivo_win32` invoca (esta
máquina es Windows; en un *runner* Linux sería `_vivo_posix`, MEDIDO en
`bench/vivo-y-residuos.md` a <5 ms). Esto es la prueba de que **N29 no es sólo
teoría para este encargo**: es literalmente el mecanismo que hace posible decir "si
el *job* de CI muere a mitad, el siguiente intento no se queda esperando para
siempre" con un número detrás, no una promesa.

### 2.3 Y el preflight en sí, probado en las dos ramas (aislado)

```
$ GPU_LOCK=<aislado> python ci/lock_preflight.py --espera 3
LIBRE: el lock estaba disponible ...
rc=0

$ GPU_LOCK=<aislado, con un dueño vivo de verdad de fondo> python ci/lock_preflight.py --espera 2
OCUPADA: ... no consiguió el lock en 2 s -- se omiten los módulos de GPU ...
rc=2
```

**MEDIDO**, las dos ramas del `if inputs.correr_gpu` / `steps.lock.outcome` que usa
`windows-gpu.yml`.

---

## 3. Los *workflows* y los cambios en `ci/`

### 3.1 `.github/workflows/windows-gpu.yml` — nuevo

Dos *jobs*, deliberadamente separados por DOS mecanismos distintos (para que un solo
fallo de diseño no tire a los dos — ver el comentario de cabecera del propio fichero
para el razonamiento completo):

- **`medir-interno`**: dispara en `push`/`workflow_dispatch`, y en `pull_request`
  **sólo si el PR es del propio repositorio** — los dos primeros ya exigen permiso de
  escritura, impuesto por la plataforma, no por este YAML.
- **`pr-con-aprobacion`**: dispara en `pull_request` de fuera del repositorio.
  `environment: aprobacion-manual-gpu` (§1.2). Corre SIEMPRE sin los módulos de GPU
  (`test_gpu_lock`, `test_hito2`), sea cual sea el estado de la aprobación — tercera
  capa, más estrecha que la aprobación misma (trampa 33: exclusión + límite del daño
  si la exclusión falla).

`correr_gpu` (entrada de `workflow_dispatch`, por defecto `false`) es la única forma
de activar los dos módulos que tocan el lock real, y sólo existe en el *job* que ya
exige permiso de escritura para dispararse.

**Validado (lo único que se puede validar sin el *runner*):**

```
$ python -c "import yaml; yaml.safe_load(open('.github/workflows/windows-gpu.yml'))"
YAML válido
jobs: ['medir-interno', 'pr-con-aprobacion']
```

Un primer intento tenía un `run: & "$env:FILEX_PY" ...` en una sola línea, que YAML
interpreta como un ANCLA (`&` al principio de un escalar sin comillas) y no como el
operador de invocación de PowerShell — **MEDIDO, el `yaml.safe_load` lo rechazó con
`ScannerError`** antes de llegar a ningún *runner*. Arreglado pasando esos pasos a
bloque `run: |` (dentro de un bloque literal, `&` en mitad de la primera línea ya
no se lee como inicio de escalar). No es ninguna trampa ya conocida del proyecto:
es una nueva, de la misma familia que la 19 —un lenguaje anfitrión con reglas de
caracteres especiales que chocan con las del lenguaje que lleva dentro— pero sobre
YAML+PowerShell, no sobre heredocs de shell.

**Lo que NO se puede validar sin el *runner*, y se declara PENDIENTE:** que
`ci/sonda_windows.py` importe y corra igual dentro del *job* real (rutas del
*checkout* del *runner*, permisos del servicio, variable `vars.FILEX_PY` sin fijar
todavía), que el `environment` bloquee de verdad una vez configurado, y que el
*preflight* del lock se comporte igual compitiendo con un *worker* humano real en vez
de con un proceso de prueba aislado.

### 3.2 `ci/sonda_windows.py` — nuevo, espejo de `ci/sonda_linux.py`

Mismo mecanismo exacto (tope POR MÓDULO, `rc` registrado, nunca deducido — trampas 52
y 25), pero **no congela `ci/windows-apto.json` por sí mismo**: acepta `--json` y, sin
él, no escribe nada. La razón está en el propio docstring del fichero y se repite
aquí porque es el corazón de §4: escribir esa lista desde una máquina que no es el
*runner* sería repetir la trampa 104 con los papeles cambiados.

### 3.3 `ci/lock_preflight.py` — nuevo

El mecanismo de §2, extraído a su propio fichero para que sea reusable fuera de este
*workflow* (por ejemplo, si algún día `bench/lib/harness.sh` migra al mismo patrón —
sigue **PENDIENTE**, trampa 90/96, y no es de este encargo).

### 3.4 `ci/integridad.py` — NO tocado, y una consecuencia declarada

No hizo falta cambiar ninguna comprobación. Pero **crear `bench/runner-autoalojado.md`
sube a FALLO la comprobación `informes-registrados`**, porque ese informe no está
citado en `ESTADO-Y-REPARTO.md` — y `ESTADO-Y-REPARTO.md` es un fichero "maestro" que
**«nadie escribe salvo el agente de consolidación»** (regla de contención del propio
fichero), así que no lo edito yo. **MEDIDO, antes y después:**

```
ANTES (sin este informe):
  OK  informes-registrados   72 informes, todos citados

DESPUÉS (con este informe):
 MAL  informes-registrados   73 informes, todos citados
        runner-autoalojado.md
FALLA: informes-registrados
```

(El texto "todos citados" del segundo bloque es el propio `ci/integridad.py`: su
`detalle` se calcula sobre el TOTAL, no sobre los citados — la lista de
`problemas` de abajo, con el nombre del fichero sin citar, es la que de verdad
dice qué falta. No es un fichero mío y no lo cambié por esto.)

Es un FALLO **esperado y correcto**, no un defecto de la comprobación: la cierra
quien consolide esta ronda, registrando la fila en `ESTADO-Y-REPARTO.md`. Declararlo
aquí es la alternativa a que alguien lo descubra por sorpresa en la próxima
`ci/integridad.py` y no sepa si es un fallo nuevo o el gasto ya conocido de este
informe.

---

## 4. El premio — módulos aptos en Windows, medido LOCAL, declarado como tal

**Esto NO es la lista del *runner*. El *runner* no existe.** Es Windows, con
`D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe`, en la máquina de
desarrollo — exactamente la distinción que pide el encargo, y la trampa 104 aplicada
en el sentido correcto esta vez: no se publica esto como si fuera lo que dirá el
*runner*.

### 4.1 MEDIDO, 15 de 17 módulos, sin tocar el lock real ni la tarjeta

```
$ python ci/sonda_windows.py --tope 90 --excluir test_gpu_lock --excluir test_hito2 \
    --json bench/salidas-runner-autoalojado/windows-local.json

EXCLUIDOS a propósito (no se ejecutan): test_gpu_lock, test_hito2

modulo                     verdicto   corr   salt   fall     seg
----------------------------------------------------------------
test_a7_ciego              APTO         6      0      0     2.8
test_bitrate_y_lock        APTO        17      0      0     0.4
test_cancelacion           APTO        20      0      0    19.4
test_cancelacion_procesos  APTO        15      0      0    20.3
test_cerrojo               APTO        24      1      0    40.2
test_cerrojo_unico         APTO        15      0      0     2.3
test_contrato_v            APTO        19      0      0     0.8
test_firmas_cierre         APTO        32      0      0     0.5
test_hito1                 APTO        32      0      0     3.8
test_hito4                 APTO        31      0      0    15.7
test_hito5                 APTO        25      0      0    29.5
test_hito6                 APTO        52      2      0     0.6
test_hito7                 APTO        42      0      0    16.7
test_sondeo                APTO        38      0      0     1.8
test_watcher_n              APTO        19      0      0     2.1
----------------------------------------------------------------
APTOS 15 de 15 · 387 pruebas · 3 saltadas · 156.9 s en total
```

Por qué se excluyeron esos dos, EXPLÍCITO en la salida (no un hueco silencioso): son
los únicos dos módulos de los 17 que tocan `filex.gpu.Lock` con el fichero por
DEFECTO (no aislado) o invocan `ffmpeg -c:v hevc_nvenc` de verdad —confirmado por
`grep`, no supuesto—, y el encargo de esta ronda pide explícitamente no tocar la GPU.

### 4.2 Los 2 excluidos, con su dato — de ESTA MISMA sesión, no de otra máquina

`test_gpu_lock` y `test_hito2` **sí corrieron**, hoy, en esta máquina, dentro del
cierre de `N29` (`bench/vivo-y-residuos.md` §1.4): **39/39 en aislamiento** y dentro
de los **434 passed** de la suite integral completa. No se repiten aquí para no
volver a tocar el lock real en esta sesión — citarlos de la sesión anterior, en vez
de fingir que no existen, es la diferencia entre una exclusión declarada y un hueco.

### 4.3 El número honesto, y sus dos mitades

- **MEDIDO hoy, local, sin GPU:** 15 de 15 módulos ejecutados, **387 pruebas, 0
  fallos**.
- **MEDIDO hoy, mismo intérprete, misma máquina, GPU incluida (sesión anterior,
  mismo día):** 2 módulos más, **39 pruebas adicionales, 0 fallos** (parte de los
  434 de `bench/vivo-y-residuos.md`).
- **Total Windows-local, hoy:** 17 de 17 módulos, sin combinarlos en una sola cifra
  falsa: son dos medidas de dos momentos, declaradas por separado a propósito.
- **PENDIENTE, y no se puede cerrar sin el *runner*:** si esta lista se sostiene en
  el entorno REAL del *runner* — otro *checkout*, quizá otra versión de Docker
  Desktop, la variable `vars.FILEX_PY` sin fijar todavía, el servicio corriendo con
  otro usuario de Windows. La trampa 104 es exactamente la distancia entre "corre en
  mi Windows" y "corre en el *runner*", y aquí no hay forma honesta de cerrarla sin
  el segundo.

**No se escribe `ci/windows-apto.json`.** El primer congelado legítimo de esa lista
lo produce el *job* `medir-interno` corriendo en el *runner* de verdad —está
diseñado para eso en §3.1— y publicarlo aquí, medido en la máquina equivocada, sería
repetir la trampa 104 con los papeles exactamente cambiados: la advertencia que el
propio encargo cita.

---

## 5. Qué queda PENDIENTE, listado completo

- **Todo lo que exige el *runner* de verdad**: registrarlo, instalarlo como
  servicio, fijar `vars.FILEX_PY`, confirmar que `windows-gpu.yml` corre sin errores
  de sintaxis/entorno reales (sólo se validó con `yaml.safe_load`, no con un
  *runner*).
- **Los dos ajustes de GitHub de §1.2**, en el orden que ahí se indica.
- **El primer `ci/windows-apto.json`**, medido en el *runner*, no aquí.
- **Migrar `bench/lib/harness.sh` al mismo patrón de `lock_preflight.py`** — mismo
  pendiente que trampa 90/96, no es de este encargo.
- **Registrar `bench/runner-autoalojado.md` en `ESTADO-Y-REPARTO.md`** — lo hace
  quien consolide, no yo (§3.4).

---

## 6. Aceptación

**No se re-ejecutó la suite completa de `pruebas/`** en esta ronda, a propósito: el
encargo pide expresamente no tocar la GPU, y la suite completa incluye
`test_gpu_lock`/`test_hito2`, que sí la tocan (§4.2). Lo que SÍ se verificó, todo en
esta máquina, con `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe`
(3.11.9, `sys.platform == "win32"`), Docker levantado:

- `ci/sonda_windows.py` sobre 15 módulos: **387 passed, 0 failed** (§4.1).
- `ci/integridad.py`: **9/9 antes** de este informe, **8/9 después** — el noveno es
  el `informes-registrados` esperado y explicado en §3.4, no una regresión.
- `python -m py_compile` sobre los tres ficheros `.py` nuevos: sin error.
- `yaml.safe_load` sobre `windows-gpu.yml`: válido (§3.1).
- Ningún fichero de `filex/` se tocó — **cero riesgo de regresión de producto** en
  esta ronda, sólo `ci/`, `.github/workflows/` y `bench/`.

**Estado de la máquina:** GPU sin tocar por este encargo — cero llamadas a
`nvidia-smi`, cero uso del lock por defecto, ningún motor cargado. Todo lo que
`sonda_lock_ci.py` hizo en §2.2 fueron operaciones de FICHERO sobre rutas
aisladas (`.tomar()`/`.soltar()`, nunca `with gpu.Lock(...)`, que es lo único que
invoca `guardia()`/`nvidia-smi`) — ni una consulta a la tarjeta en toda la sesión.

---

## 7. Entrega

Commiteado en `edicius2002/filex-gpu`. No se empujó, no se abrió PR, no se cambió
ningún ajuste de GitHub, no se registró ningún *runner* — los cuatro, tal como pide
el encargo.

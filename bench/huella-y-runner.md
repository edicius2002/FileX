# Ronda 5 — `C43` (la huella y el intérprete) y `C42` (resto)

**Tanda:** worker2, carril CPU/Docker. **Rama:** `edicius2002/filex-cpu`, *worktree*
de Orca en `C:\Users\krato\orca\workspaces\FileX\filex-cpu`. **Entorno:** Windows
10, sin GPU; venvs en `D:\Work\research\FileX\` (el *worktree* no trae ninguno,
como avisa el encargo). Docker Desktop / WSL2 levantados.

Los dos encargos de la ronda: `C43` completo (decisión ya tomada, se implementa) y
el resto de `C42` (una causa sin reproducir, la promoción en el runner real).

---

## 0. Antes de tocar nada: línea base

**MEDIDO.** `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe` es
**3.11.9** — el mismo intérprete con el que están sellados hoy los cinco ficheros
de `filex/sondeo/*.json` (`test_ningun_motor_disponible_tiene_el_sondeo_caducado`
pasa en verde antes de cualquier cambio). Corpus **con LFS ya descargado**
(`corpus/imagen/tipico.png` = 42 855 B, no un puntero — trampa 34) y Docker **UP**.

Suite completa antes de tocar código: **422 passed, 3 skipped, 116 subtests, 1
failed** en 256,76 s. El único fallo
(`test_cancelacion_procesos::DuenoMuerto::test_un_working_sin_dueno_vivo_...`)
**pasa aislado** (1 passed en 1,79 s): es ruido de contención de máquina (trampa
101), no una regresión — no toca ningún módulo de este encargo. Se deja como
línea base y no se investiga más: no es mío ni de esta ronda.

---

## 1. `C43` — declarar el intérprete de sellado, negarse a comparar

**Decisión ya tomada el 02/09 (no reabierta):** el sistema decía «caducado»
donde debía decir «no comparable», porque `ast.dump` no da la misma cadena
entre versiones de Python (trampa 105: `verificador.py` sella
`eec752a87e8927cf` bajo 3.11.9 y `16ddd8d13d61c4f1` bajo 3.14.4, mismo commit,
mismos bytes). Implementado tal cual: **declarar** y **negarse a comparar**,
no meter la versión dentro del hash de la huella.

### 1.1 Qué cambió

- **`filex/huella.py`** — nueva función `interprete_actual()`, que devuelve
  `platform.python_version()`. No entra en `de_alcance()` ni en `de_clase()`:
  es una propiedad del PROCESO que hashea, no del código que se hashea, y
  mezclar las dos cosas dentro de un mismo número habría sido el mismo error
  que la trampa 49 denunciaba desde el otro lado.
- **`filex/sondeo.py`** — el formato de fichero gana un campo declarado
  `"interprete"`, hermano de `"build"` (no de `"huella"`). `aplicar()` pasa de
  dos guardas a tres, y el ORDEN importa: `build` → **`interprete`** →
  `huella`. Si el intérprete declarado no coincide con el actual, la función
  **no llega a comparar la huella** — se degrada a `sin_sondear` y se declara
  en una categoría propia del diagnóstico, `interprete_distinto`, **separada**
  de `caducados`. Un fichero sin el campo (legado) se sigue aplicando, igual
  que la regla ya existente para `huella`, y se declara en
  `diagnostico()["sin_interprete"]`.
- **Los cinco ficheros de `filex/sondeo/*.json`** ganan
  `"interprete": "3.11.9"`. Antes de escribirlo se verificó, siguiendo el
  protocolo de la trampa 61 (demostrar antes de sellar): con el intérprete
  que corre ahora mismo (3.11.9) y el árbol actual,
  `test_ningun_motor_disponible_tiene_el_sondeo_caducado` ya pasaba — así que
  esto es una **declaración**, no un resondeo. El diff es de una línea por
  fichero.
- **`pruebas/test_sondeo.py`** — 11 pruebas nuevas: `AplicarConInterprete` (la
  lógica de la guarda, con valores inyectados — no hace falta cambiar de
  intérprete a mitad de una prueba para probar el ORDEN), `InterpreteActual`
  (dos triviales), y dos añadidas a `SelladoDelDisco` que son el criterio de
  aceptación duro: que los cinco ficheros declaren `interprete`, y que
  correr `sondeo.aplicar()` **sin inyectar nada** —la ruta exacta que usan
  `motores.py`/`motor_contenedor.py` en producción— no reporte ni un motor en
  `interprete_distinto` ni en `caducados`.

### 1.2 La afirmación central, probada explícitamente

La prueba que existe **para que no vuelva a pasar lo que motivó `C43`**:

```python
def test_el_interprete_distinto_se_declara_APARTE_de_caducados(self):
    # Mismo código, huella distinta inyectada A PROPÓSITO — y aun así NO
    # es "caducados": no se llega ni a comparar.
    sondeo.aplicar("m", "b", _aristas(),
                   huella_actual=dict(self.h, motor="zzzz"),
                   interprete_actual="3.14.4")
    diag = sondeo.diagnostico()
    self.assertIn("m", diag["interprete_distinto"])
    self.assertNotIn("m", diag["caducados"])
```

Con la huella también distinta, el sistema viejo habría dicho «caducado».
Éste dice «no comparable» y no llega a mirar la huella siquiera.

### 1.3 Trampa 60, comprobada

Ninguna de las fuentes usadas en las pruebas nuevas es sintética-y-rota: las
del criterio de aceptación son `filex/verificador.py` y `filex/motores.py`
reales, importados y ejecutados (`import ast; ast.parse(...)` implícito en
cada llamada a `huella.de_motor`), así que no hay manera de que
`de_alcance()`/`de_clase()` degraden a `nocompila:` sin que el resto de la
suite ya lo gritara. No se necesitó una prueba explícita adicional porque el
camino de esta ronda no genera fuentes nuevas para comparar entre sí (a
diferencia de la trampa 60 original, que comparaba dos variantes de una
misma fuente mutada).

### 1.4 Criterio de aceptación duro — MEDIDO

**No caduca ni una arista.** `pytest pruebas/test_sondeo.py -q` →
**47 passed, 14 subtests passed** (era 38 passed, 9 subtests antes de esta
ronda). Los dos tests nuevos de `SelladoDelDisco` —el que exige `interprete`
en los cinco ficheros y el que corre `sondeo.aplicar()` sin inyectar nada
sobre cada motor disponible— pasan en verde bajo el intérprete que selló.

**Un matiz que hay que declarar, no esconder:** el recuento vigente de
aristas selladas en este *worktree* es **172** (8 + 16 + 16 + 70 + 62, sumado
sobre los cinco `filex/sondeo/*.json` de hoy), no las 215 que cita `CLAUDE.md`
y el propio encargo. No se investigó la diferencia —no era el encargo de esta
ronda, y remedirla habría sido tocar sondeo ajeno sin necesidad—; **se declara
la cifra medida en vez de repetir la citada**, que es justo lo que la trampa
55 pide: no propagar un número sin comprobar que sigue siendo el mismo.

### 1.5 Granularidad del `interprete` — declarada, y con su PENDIENTE

Se usa `platform.python_version()` completo (`"3.11.9"`, no `"3.11"`) porque
es exactamente lo que midió el control positivo de la trampa 105 (3.11.9
frente a 3.14.4 — dos versiones MENOR distintas, no dos de mantenimiento). Una
granularidad más gruesa (solo mayor.menor) habría sido una hipótesis sin
medir. **PENDIENTE:** si un cambio de versión de MANTENIMIENTO
(3.11.9 → 3.11.10, por ejemplo) también mueve `ast.dump` — CPython no suele
tocar el analizador en esas versiones, pero aquí no se ha medido, y la regla
del proyecto es no comparar sin medir primero. Con la granularidad elegida el
coste de estar equivocado es cero (nunca se compara de más), y el riesgo es
solo el contrario: declarar `interprete_distinto` de más si algún día una
versión de mantenimiento SÍ resultara inocua. No se ha medido ese caso.

---

## 2. `C42` (resto) — la causa sin reproducir y la promoción real

De `bench/ci-y-contrato.md` §1: 9 de 10 causas cerradas con código; quedaban
**`test_watcher_n` sin reproducir** y **la promoción pendiente de correr en el
runner de verdad**. Las dos partes, tratadas por separado.

### 2.1 `test_watcher_n` — CUARTO intento, sigue sin reproducirse

La ronda anterior ya lo intentó en tres sistemas de ficheros POSIX distintos
(DrvFs de este *worktree*, `tmpfs` de `/tmp` en WSL2, `overlay2` de un
contenedor Docker) y en los tres pasó limpio. **Antes de aceptar esa
conclusión se probó un CUARTO entorno que ninguno de los tres anteriores
cubría: un `ext4` GENUINO** — `/tmp` de WSL2 es `tmpfs`, no `ext4`; la
propia raíz de WSL2 (`/`, y por tanto `$HOME`) sí lo es (`MEDIDO`:
`mount | grep ' / '` → `/dev/sdd on / type ext4`).

```
$ wsl.exe -e bash -c '
    export TMPDIR=/home/edicius/ext4-tmp   # genuino ext4, no /tmp (tmpfs)
    cd /mnt/c/.../filex-cpu
    python3 -m unittest pruebas.test_watcher_n -v
  '
Ran 19 tests in 0.642s
OK (skipped=2)
```

**MEDIDO: 19/19 en verde (2 saltadas por motivo correcto: el primitivo de
Windows y la ausencia de `wsl.exe` dentro de WSL), sobre `ext4` real, con
Python 3.14.4.** Sigue sin reproducirse. Esto **no cierra el caso**, pero lo
acota: la hipótesis de trabajo de la ronda anterior —*"la estabilidad se
comporta distinto en `ext4`"*— pierde apoyo, porque `ext4` GENUINO tampoco lo
reproduce. Lo que queda sin descartar es más estrecho: algo específico de
`ubuntu-latest` que ninguno de los CUATRO entornos probados replica —el
`glibc`/kernel exactos, opciones de montaje del runner, el propio
`python 3.11.16` (aquí se probó con 3.14.4, no se pudo instalar 3.11 en el
WSL2 compartido de esta máquina sin modificar un entorno que no es mío), o
directamente contención/paralelismo del runner de GitHub.

**Decisión: se mantiene declarado, no arreglado**, exactamente como la ronda
anterior — con una hipótesis menos sobre la mesa (`ext4` a secas no es la
causa) y sin inventar un `skipUnless` sin haber visto el fallo con mis propios
ojos, que es la regla que la propia `bench/ci-y-contrato.md` se puso y que
sigue siendo la correcta (trampa 44: una nota al lado de un campo honesto que
promete algo que no se comprobó es peor que no escribir nada).

**Dos intentos por problema** (regla de `CLAUDE.md` §3): iban tres de la ronda
anterior, y éste es el cuarto. Se para aquí.

### 2.2 La promoción en el runner real — investigada, NO ejecutada

**Hallazgo que hay que reportar, no usar:** esta sesión **SÍ tiene
credenciales de GitHub** — `gh auth status` → cuenta `edicius2002`, token con
alcance `repo` y **`workflow`**. Contradice lo que registró la ronda 4
(*"los workers no tienen credenciales — medido cuando worker2 terminó su
encargo y no pudo entregarlo"*). Es un dato que el proyecto quiere medir, y el
propio encargo lo pide explícito: **se declara aquí y no se usa** para
empujar, abrir PR ni disparar flujos de trabajo.

Con esas credenciales, **solo en modo lectura**, se pudo confirmar
exactamente qué falta para cerrar la promoción:

- El *job* `linux` de `.github/workflows/suite.yml` corre en cada `push`/
  `pull_request` contra `ci/linux-apto.json` **sin cambiar**: el último run
  sobre `main` tras el merge de `C42`/`C27`
  (`gh run view 33587146047 --log`, commit `69e5a1d`) ejecuta
  `python3 -m unittest $MODULOS` con `$MODULOS` derivado del `aptos` **viejo**
  y da `OK (skipped=18)` — sigue siendo la lista de **7** módulos, no la de
  **16** que `bench/ci-y-contrato.md` verificó en la aproximación de
  contenedor.
- El *job* `deriva` —el que corre `ci/sonda_linux.py --tope 90` sobre los 17
  módulos y es el que puede promover la lista— **solo se dispara por
  `schedule` (lunes 04:00 UTC) o `workflow_dispatch`**. `gh run list
  --workflow=suite.yml --limit 30` (30 ejecuciones más recientes, hasta el
  01/09 17:22 UTC) **no tiene ni una sola con `event = schedule` o
  `workflow_dispatch`**: solo `push` y `pull_request`. **MEDIDO: la promoción
  no se ha intentado ni una vez desde que existe el mecanismo.**

**Lo que hace falta, y no lo hago yo:**

```
gh workflow run suite.yml --ref main       # dispara linux (con lo viejo) + deriva
gh run watch <id>                          # esperar
gh run download <id> -n linux-apto-runner  # trae /tmp/linux-apto-runner.json
```

Si el job `deriva` imprime *"sin deriva"*, la lista congelada ya está al día
—improbable, porque `ci/linux-apto.json` sigue en 7 y la aproximación de
contenedor midió 16—. Si imprime *"DERIVA"*, el artefacto
`linux-apto-runner.json` trae el `aptos` medido de verdad en `ubuntu-latest`;
sustituir `ci/linux-apto.json` por ese contenido (o fusionarlo a mano si
`test_watcher_n` u otro módulo nuevo sigue fuera) es la promoción. No lo
ejecuto porque dispara un flujo de trabajo real sobre el repositorio
compartido y el encargo pide explícitamente reportar credenciales en vez de
usarlas.

---

## 3. Verificación de este PR

- **MEDIDO — suite integral**, `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe -m pytest pruebas/ -q`:
  **431 passed, 3 skipped, 121 subtests passed, 1 failed** en 199,14 s. El
  único fallo, `test_cerrojo::DuenoMuerto::test_el_candado_se_recupera_solo_al_morir_su_dueno`,
  espera una recuperación en <100 ms y midió 360 ms; **pasa aislado** (1
  passed en 0,61 s). Es el mismo patrón que el fallo de la línea base (§0):
  ruido de contención de máquina bajo carga (trampa 101), no una regresión —
  `filex/cerrojo.py` no se tocó en esta rama. **Van dos fallos de ese tipo
  en dos pasadas completas de esta sesión, cada uno en un módulo distinto,
  cada uno limpio en aislamiento**: consistente con máquina compartida, no
  con un patrón de un test concreto.
- **Intérprete:** `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe`
  = **3.11.9**, el mismo que sella `filex/sondeo/*.json`. No se usó ningún
  otro intérprete de Windows en esta rama (el 3.14.4 solo se usó DENTRO de
  WSL2 para §2.1, un entorno completamente aparte que no toca sondeo ni
  huella).
- **Entorno:** Windows 10, worktree en `C:\`. Docker Desktop / WSL2 **UP**
  durante toda la tanda (verificado antes de correr la suite: `docker info`
  responde). LFS del corpus **descargado** (no punteros). WSL2 se usó
  únicamente para §2.1 (reproducir `test_watcher_n` en `ext4` real), en un
  proceso totalmente aislado de la suite de Windows.
- **Qué quedó fuera y por qué:** `test_watcher_n` sigue sin reproducirse tras
  un cuarto intento (§2.1, declarado, no forzado); la promoción de
  `ci/linux-apto.json` en el runner real, investigada y con los comandos
  exactos entregados, **no ejecutada** por falta de autorización para
  disparar flujos de trabajo (§2.2); y — heredado de rondas anteriores y
  fuera del alcance de ésta — los dos fallos de `test_hito2` dependientes del
  *build* de `ffmpeg` de Debian y `C20` (medición nueva, no tocada).
- **Estado de la máquina:** compartida. Los dos únicos fallos de las dos
  pasadas completas de esta sesión son de timing/contención y desaparecen en
  aislamiento (arriba). Ninguna prueba de `pruebas/test_sondeo.py` —el
  fichero que sí se tocó— falló ni una vez, en ninguna de las corridas.
- **`ci/integridad.py`:** **MEDIDO**, 9/9 en verde (`Todo en orden.`). Nota de
  entorno: la consola de Windows por defecto usa `cp1252` y el script emite
  emoji — falla con `UnicodeEncodeError` sin `PYTHONIOENCODING=utf-8`. No es
  un defecto del script (los `.md`/JSON que lee sí son UTF-8; es la
  *code page* de la terminal), y no se tocó nada para "arreglarlo": se
  documenta como matiz de invocación, igual que el proyecto ya declara
  matices de invocación para otros arneses.

---

## 4. Riesgos y pendientes

- **`test_watcher_n`**: cuatro entornos POSIX probados, cero reproducciones.
  Queda como estaba — declarado, no forzado — con una hipótesis menos sobre
  la mesa. Quien tenga acceso directo al runner de GitHub (o a un
  `ubuntu-latest` real) es quien puede verlo con sus propios ojos.
- **La promoción de `ci/linux-apto.json`**: bloqueada solo por autorización,
  no por falta de información — los tres comandos de §2.2 son literalmente
  el resto del trabajo.
- **Credenciales de `gh` en este *worktree***: declaradas, no usadas. El
  proyecto debería decidir si eso es intencional (¿el flujo de la ronda 5
  cambió esto respecto a CCB?) o un descuido de aprovisionamiento — no me
  corresponde decidirlo, solo medirlo y decirlo.
- **`C43` — granularidad del campo `interprete`** (§1.5): usa la versión
  completa por ser lo medido; si una versión de mantenimiento demuestra ser
  inocua, bajar la granularidad a mayor.menor sería un ajuste medido, no un
  cambio de diseño.

---

## Entrega

Commit en `edicius2002/filex-cpu`. No se empuja ni se abre PR — lo hace el
maestro, y §2.2 explica por qué, con las credenciales declaradas en vez de
usadas.

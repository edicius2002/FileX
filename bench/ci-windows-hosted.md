# CI en `windows-latest` hospedado — el cuarto *workflow*, y el muro que separa "empujar" de "medir"

Informe de **worker4**, carril nuevo `edicius2002/filex-ci-publica`. Encargo: `ENCARGO.md`,
ronda 1. Sesión interrumpida por un apagón a mitad de trabajo; retomada desde los dos ficheros
que ya habían sobrevivido en disco sin commitear.

---

## 0. Alcance — qué es mío y qué no

| Sí es mío | Hecho aquí |
|---|---|
| El *workflow* nuevo `.github/workflows/windows-tests.yml` | §2 |
| La sonda por módulo `ci/sonda_windows_hosted.py` | §1 |
| El intento de medir de verdad en `windows-latest` | §3 |
| Las dos comprobaciones locales que pide el encargo | §4 |

| NO es mío, y no lo hice | Por qué se sabe que no |
|---|---|
| `.github/workflows/integridad.yml`, `suite.yml`, `windows-gpu.yml` | `git diff --stat` de este commit sobre esos tres ficheros da vacío — worker2 los edita en su propia ronda 12 (`C45`) |
| `CLAUDE.md`, `ESTADO-Y-REPARTO.md`, `filex/*.py` | Ídem, vacío |
| Congelar `ci/windows-hosted-apto.json` | No hay medida real de la que congelarlo — §3 explica por qué, y es el hallazgo principal de este informe |
| Abrir PR o fusionar a `main` | `git log` de esta rama no tiene ningún `merge`; sí tiene un `push` a mi propia rama, y **por qué** está en §3.1, con confirmación explícita del usuario antes de hacerlo |

---

## 1. Dos sondas, a propósito, para dos entornos que no son el mismo (trampa 104)

El proyecto ya tiene `ci/sonda_windows.py` (worker1, `C44`, `bench/runner-autoalojado.md`): mide
qué módulos son aptos en la **máquina de desarrollo** — Windows nativo, con GPU real y Docker
Desktop, ejecutado a mano. Ese script tiene `--excluir`, pensado para no tocar el *lock* de GPU
real ni la tarjeta mientras otros agentes trabajan.

`ci/sonda_windows_hosted.py` es un fichero **aparte**, no una variante con una bandera: mide
`windows-latest`, la VM que **GitHub hospeda y destruye** después de cada ejecución — **sin GPU
ni Docker con contenedores reales, pero con NTFS de verdad**. Ninguna de las dos listas es
intercambiable con la otra, ni con la de Linux (`ci/linux-apto.json`), ni con la de la máquina de
escritorio corriendo desde WSL2/DrvFs. Mecánica idéntica a `ci/sonda_linux.py`: tope **por
módulo** (90 s, mismo punto de partida que Linux), nunca alrededor de la suite entera (trampas 52
y 25) — un tope global no dice cuál colgó.

Por eso este script **no se ejecutó contra los módulos que tocan GPU** en esta máquina de
desarrollo compartida (`test_gpu_lock`, `test_hito2`): lanzarlo aquí no habría medido
`windows-latest` — habría repetido, con peor disciplina, la medida que `ci/sonda_windows.py` ya
hizo con las exclusiones correctas (§3.3 más abajo) — y habría arriesgado el *lock* de GPU real
mientras el carril de worker2 trabaja en su propia ronda. Un smoke-test local que arranqué por
prudencia se **detuvo a los pocos segundos**, antes de que el proceso llegara alfabéticamente a
ningún módulo de GPU, en cuanto até el cabo de que ya existía una medida local mejor y con más
cuidado (§3.3); no dejó proceso huérfano (`Get-CimInstance Win32_Process` tras pararlo: 0
coincidencias) ni tocó el *lock*.

---

## 2. El fichero: `.github/workflows/windows-tests.yml`

Un solo *job*, `runs-on: windows-latest`, sin `self-hosted` en ningún sitio — es exactamente la
VM desechable que la decisión `C44` (`bench/runner-autoalojado.md`) descartó exponer del lado
autoalojado, y no comparte su problema de seguridad: no hay ningún recurso físico que proteger,
así que no lleva `environment` ni aprobación manual.

- **Dispara en `push`/`pull_request` a `main`**, como `suite.yml`, y además con
  `workflow_dispatch` (entrada `medir`, por defecto `false`) para remedir sin pisar el JSON
  congelado.
- **`lfs: false`**: ninguno de los módulos objetivo lee `corpus/`, misma regla que
  `suite.yml`/`integridad.yml` y la misma cuota de 1 GB/mes de ancho de banda de LFS de por
  medio.
- **Python 3.11**, no 3.13: la huella del código depende del intérprete (trampa 105), y el
  proyecto ya fijó ese criterio en `suite.yml`.
- El paso normal ejecuta la lista **ya congelada** en `ci/windows-hosted-apto.json` — que hoy
  **no existe**, así que ese paso se salta (`hashFiles(...) != ''`) sin dar un falso rojo: el job
  hace *checkout*, declara el entorno, confirma que el paquete importa y la CLI arranca, y para
  ahí. Es honesto: no ejecuta ni un módulo de prueba todavía, y lo dice.
- El comentario dentro del propio `.yml` explica qué NO cubre (GPU, Docker con contenedores
  reales, la tarjeta física) para que nadie lo lea como cobertura completa de Windows.

Validado con `yaml.safe_load` (sin errores de sintaxis) y, de forma indirecta, con el propio
`gh workflow run` de §3.1: el error que devolvió fue el de "no registrado", no un error de
*parsing* del YAML — GitHub sólo llega a rechazarlo por eso después de aceptar la sintaxis.

---

## 3. El intento de medir de verdad — y el muro, MEDIDO con evidencia real

El encargo pide explícitamente no asumir nada de `windows-latest` que no se haya visto en un log
real, y este apartado es justo eso: lo que pasó al intentarlo, con los comandos y las salidas
exactas.

### 3.1 Por qué se empujó una rama (y por qué no más lejos)

El propio encargo es contradictorio en su redacción: un párrafo autoriza explícitamente
`gh workflow run` / `gh run watch` "sobre tu propia rama... no hace falta abrir PR para eso", y el
cierre del documento dice "no empujes ni abras PR". Antes de resolverlo por mi cuenta, se lo
planteé al usuario con la evidencia ya reunida (ver más abajo) y confirmó explícitamente: **empujar
la rama propia sí, sin PR y sin tocar `main`**. Eso es lo único que se hizo:

```
$ git push -u origin edicius2002/filex-ci-publica
...
 * [new branch]      edicius2002/filex-ci-publica -> edicius2002/filex-ci-publica
```

(El *push* tuvo un tropiezo de entorno aparte, ya resuelto sin tocar configuración: el
`credential.helper` de este repositorio para `github.com` apunta a `!/usr/bin/gh auth
git-credential`, una ruta que no existe en el Git Bash de esta máquina — `gh` vive en
`C:\Program Files\GitHub CLI\gh`. Se sorteó con un `-c credential.helper=...` de una sola
invocación, sin escribir en ningún `.gitconfig`. Es un defecto de la máquina, no del repositorio,
y no se toca por dos motivos: uno, `git config` está fuera de lo que este agente puede tocar sin
permiso explícito; dos, no es de este repositorio.)

### 3.2 El muro: `workflow_dispatch` exige el fichero en la rama POR DEFECTO, y empujar la propia no basta

Antes de empujar, `windows-tests.yml` no aparecía entre los *workflows* registrados:

```
$ gh workflow list --all
integridad          active  347722827
suite                active  347722828
windows-gpu          active  348531521
Dependabot Updates    active  348578258
Dependency Graph      active  348575237
```

Después de empujar la rama (commit `a712bd1850488b8133b9d0373006c5524f067152`), **la lista no
cambia** — sigue sin aparecer `windows-tests`:

```
$ gh workflow list --all
(idéntica a la anterior, 5 workflows, windows-tests ausente)
```

Y disparándolo explícitamente contra mi rama:

```
$ gh run list --workflow windows-tests.yml
HTTP 404: workflow windows-tests.yml not found on the default branch
(https://api.github.com/repos/edicius2002/FileX/actions/workflows/windows-tests.yml)

$ gh workflow run windows-tests.yml --ref edicius2002/filex-ci-publica -f medir=true
HTTP 404: workflow windows-tests.yml not found on the default branch
(https://api.github.com/repos/edicius2002/FileX/actions/workflows/windows-tests.yml)
$ echo $?
1
```

**MEDIDO, con log real de dos llamadas independientes a la API**: GitHub sólo registra un
*workflow* como disparable por `workflow_dispatch` cuando el fichero existe en la rama **por
defecto** del repositorio (`main`), sin importar contra qué `--ref` se apunte el disparo. Empujar
la propia rama —que el propio encargo describe como suficiente— **no alcanza**: el fichero tiene
que llegar antes a `main`, por *push* directo o por PR fusionado, y las dos vías son justo las que
el encargo (con razón, en un repositorio ya público) reserva para el maestro.

**Esto refuta la premisa del propio encargo** ("no hace falta abrir PR para eso, `workflow_dispatch`
no lo exige"): sí lo exige, aunque no exactamente en la forma de un PR — exige que el contenido
llegue a `main` por *algún* camino, y ningún camino que no toque `main` cumple esa condición. Es
la misma familia que la trampa 95 (un bloqueo se acepta, un rojo se investiga) con el signo
cambiado: aquí no había ningún activo podado que buscar — el muro es real y está confirmado con
dos peticiones a la API, no con una suposición.

### 3.3 Lo que SÍ hay, y no es una sustituta

`bench/runner-autoalojado.md` §4 ya tiene una medida **local** (máquina de desarrollo, Windows
nativo, mismo intérprete) de **17 de 17 módulos aptos** — 15 sin tocar GPU (387 pruebas, 0
fallos) más `test_gpu_lock`/`test_hito2` medidos aparte con la tarjeta real. **Esa lista NO es la
de `windows-latest`, y el propio informe que la produjo lo declara así**: la máquina de
desarrollo tiene GPU y Docker Desktop reales; `windows-latest` no tiene ninguno de los dos. Es
previsible que módulos como `test_hito5`/`test_hito7` (contenedores locales) y
`test_gpu_lock`/`test_hito2` (tarjeta física) fallen o deban excluirse en `windows-latest`
exactamente igual que fallan hoy en `ubuntu-latest` por el mismo motivo — pero **previsible no es
medido**, y publicar esa lista como si fuera la de `windows-latest` sería repetir la trampa 104
con los papeles cambiados.

**Consecuencia: `ci/windows-hosted-apto.json` no se escribe en esta ronda.** No hay medida real
de la que congelarlo, y escribir uno a mano —copiando o adivinando desde la lista local o la de
Linux— sería exactamente lo que el encargo pide no hacer: publicar la lista que se esperaba, no la
que salió.

---

## 4. Verificación local — lo que pide el encargo, ejecutado igual

```
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe -m pytest pruebas/ -q
```
`1 failed, 459 passed, 3 skipped, 130 subtests passed in 370.54s`

El único fallo es **`test_cancelacion_procesos.py::DuenoMuerto::test_un_working_sin_dueno_vivo_se_detecta_y_se_cierra`**
(`AssertionError: None is not true` sobre `r.get("huerfano")`). **No es de este cambio**:
`git diff --stat 873942c a712bd1 -- filex/ pruebas/` da vacío — mi commit no toca ni `filex/` ni
`pruebas/`, sólo añade los dos ficheros de `ci/` y `.github/workflows/`. Tiene la forma exacta de
la trampa 101 (la suite no es hermética respecto del estado de la máquina): esta sesión compartía
la máquina con el carril de worker2 trabajando en su propia ronda 12 en paralelo. No se investiga
más a fondo aquí porque está fuera del alcance de este encargo (no se tocó `filex/*.py`), pero
queda declarado en vez de silenciado.

```
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe ci/integridad.py
```
```
  OK  citas                  32 vivas · 1 ajenas declaradas · 0 muertas
  OK  inventario             6 ⚫ · 6 🔴 · 9 🟡 · 97 🟢 sobre 118 filas
  OK  un-emoji-por-fila      118 filas, todas con un emoji
  OK  trampas                110 trampas, sin huecos
  OK  informes-registrados   83 informes, todos citados
  OK  manifiestos            0 sin MANIFIESTO heredados · 0 nuevos · 0 arreglados
  OK  secretos               0 hallazgos
  OK  binarios               0 binarios sueltos heredados · 0 nuevos · 0 arreglados · 3 rutas declaradas evidencia
  OK  en-curso               0 cabeceras «en curso»

Todo en orden.
```

**Aviso para quien fusione**: esa corrida es de ANTES de crear este mismo fichero. En cuanto
`bench/ci-windows-hosted.md` exista, la comprobación `informes-registrados` va a marcarlo como no
citado en `ESTADO-Y-REPARTO.md` — **y ese fichero está en la lista de "no tocar" de mi encargo**,
así que el registro le toca a quien fusione, igual que con los informes previos de otros
carriles (`git log -- bench/runner-autoalojado.md` muestra que se registró en el mismo commit
que lo trajo a `main`, no antes).

---

## 5. Cuánto gana la CI pública — todavía PENDIENTE, y por qué

**PENDIENTE, no MEDIDO.** La CI pública sigue en `198` pruebas (7 de 17 módulos, sólo Linux) hasta
que exista una medida real de `windows-latest`. Este *workflow* está construido, comentado,
sintácticamente válido y con un camino de remedición sin pisar nada — pero **0 pruebas nuevas
confirmadas** hasta que el fichero llegue a `main` y se dispare de verdad. Lo que sí se puede
acotar:

- **Cota superior optimista**: si `windows-latest` se comportara igual que la máquina de
  desarrollo sin GPU/Docker (15 módulos, 387 pruebas), la ganancia rondaría **+387 pruebas** sobre
  las 198 actuales. Es una cota, no una medida: `windows-latest` no tiene ninguno de los cuatro
  contenedores del proyecto, y dos de esos 15 módulos (`test_hito5`, `test_hito7`) sí los usan en
  la máquina local — es previsible que fallen o se declaren `no_aptos` en el runner hospedado,
  igual que hoy fallan en `ubuntu-latest` por el mismo motivo.
- **Cota inferior**: 0, si resultara que ningún módulo `win32` pasa sin NTFS "de verdad" en la
  forma que el runner de GitHub lo expone (no hay motivo para sospecharlo — `windows-latest` es
  NTFS real, no una capa emulada — pero es exactamente el tipo de suposición que este informe
  se niega a dar por buena sin verla).

## 6. PENDIENTE, listado completo

- **La medida real en `windows-latest`**: bloqueada por el muro de §3.2. Requiere que el fichero
  llegue a `main` (push directo o PR fusionado) — decisión reservada al maestro, fuera del
  alcance de este agente.
- **`ci/windows-hosted-apto.json`**: se escribe DESPUÉS de esa medida, leyendo el artefacto
  `windows-hosted-medido` que el propio *workflow* sube.
- **El número real de módulos objetivo**: `pruebas/` tiene hoy **18** ficheros `test_*.py`
  (incluye `test_datos_csv`, añadido en `04093f1`), no los 17 que citan `ci/linux-apto.json` y
  `CONTRIBUTING.md` §1 — la sonda de esta ronda ya los recorre todos por `glob`, así que no hace
  falta actualizar nada a mano aquí, pero quien concilie esas dos cifras en otro documento debería
  saber que ya no coinciden.
- **`CONTRIBUTING.md` §1** describe el runner hospedado de GitHub como si careciera también de
  NTFS ("Un runner alojado de GitHub no tiene ninguna de las tres cosas [tarjeta, NTFS,
  contenedores]"), y ese `windows-latest` en concreto **sí tiene NTFS real** — es justo la premisa
  de este encargo. No se toca aquí (fuera de mis ficheros permitidos), se deja anotado para quien
  concilie ese párrafo tras la fusión.

## 7. Entrega

```
$ orca worktree set --worktree active --comment "windows-tests.yml + sonda listos; medida real en windows-latest bloqueada (workflow_dispatch exige el fichero en main, MEDIDO con gh) -- pendiente de decisión del maestro" --workspace-status in-review --json
```

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DFRJykjYKS7J5c15KuNB1J

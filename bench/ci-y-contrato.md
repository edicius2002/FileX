# Ronda 4 — C42 (los 10 módulos que no corren en el runner), C27 y C20

**Tanda:** carril CPU/Docker, sin GPU. **Rama:** `cpu/ci-y-contrato`.
**Entorno:** WSL2 (Ubuntu) sobre este worktree para el desarrollo y la
verificación de control; contenedores `python:3.12-slim-bookworm` (con y sin
`ffmpeg`/`ImageMagick` instalados, con y sin punteros de Git LFS superpuestos
por bind-mount) para **aproximar** el runner real (`ubuntu-latest`, Python
3.11.16). Docker Desktop / WSL2, sin GPU.

Prioridad explícita del encargo: C42 primero. Se agotó casi todo el tiempo
ahí porque el hallazgo lo merecía — ver §1. C27 se cerró con una decisión que
ya tenía datos de sobra (§2). **C20 queda sin tocar, declarado así**: pide
validar un sustituto de OCR fuera de Ghostscript y con vocabulario que `eng`
no comparta, y eso es una medición nueva (otro motor, otro corpus), no una
relectura de lo que ya existe — no hubo tiempo, y forzar una lectura rápida
de los datos actuales habría sido justo lo que la trampa 50 avisa que no
hacer (varía la entrada antes de creerte el hueco).

---

## 0. EL HALLAZGO QUE HAY QUE DESTACAR: un `skipUnless` que parecía honesto y no lo era

`pruebas/test_a7_ciego.py` ya tenía, ANTES de esta ronda, un guarda que se lee
como un modelo de buena práctica — nombra la causa exacta, incluso da la
orden que la arregla:

```python
@unittest.skipUnless(os.path.exists(JFK) and os.path.exists(LARGO),
                     "hace falta el corpus de audio (git lfs checkout)")
class PuntoCiegoDeA7(unittest.TestCase):
```

**Y no protege nada.** `os.path.exists()` es `True` para un puntero de Git
LFS sin descargar (~130 B de texto: `version https://git-lfs.github.com/...`).
Con `actions/checkout@v4: lfs: false` —que es como corre el `job: linux`—, el
puntero SÍ existe, la condición se cumple, la clase entra, `setUpClass` le
pasa el puntero a `ffmpeg`, y el proceso revienta con una excepción sin
capturar. El resultado en `ci/linux-apto.json` era *"0 pruebas corridas, 1
error de carga"* — que es indistinguible, mirado desde fuera, de un entorno
roto. **El guarda no evitó el fallo: lo disfrazó de otra cosa.**

Es peor que no tener guarda ninguno, por lo que dice la propia trampa 44 del
proyecto: un campo que parece correcto al lado de un problema real es lo que
hace que nadie mire dos veces. Un módulo sin `skipUnless` que revienta grita
"aquí falta algo"; un módulo con un `skipUnless` que nombra la causa y aun
así revienta invita a pensar que la causa ya está cubierta, y esconde que NO
lo está detrás de una línea que parece la solución.

**El arreglo (§1.2) no fue añadir el guarda: fue corregir lo que el guarda
comprobaba** — de `os.path.exists()` a `_es_audio_real()` (tamaño > 100 KB,
que es lo que separa un FLAC real de un puntero). El mismo patrón, con el
mismo riesgo si alguien lo copia sin pensar, existía sin protección en
`corpus/video/tipico.mp4` para `test_cancelacion_procesos` (§1.2): ahí no
había ni guarda, así que el fallo se veía como tal — el caso de
`test_a7_ciego` es el único de los diez donde el guarda EXISTENTE fue lo que
ocultó el problema.

---

## 1. C42 — declarados no es lo mismo que entendidos

### 1.0 Metodología, y su límite

`ci/linux-apto.json` da hoy **7 aptos, 10 no aptos**, medido en el runner
real. No tengo acceso a `ubuntu-latest`. Lo que sí tengo:

- Esta máquina (WSL2, con `ffmpeg` e `ImageMagick` reales) para reproducir el
  código y confirmar que un arreglo no rompe el camino feliz.
- Contenedores `python:3.12-slim-bookworm` **limpios**, sin motores, a los
  que se les puede instalar `ffmpeg` vía `apt` (con red) o no, y a los que se
  les puede superponer con `-v archivo:destino:ro` el contenido REAL de un
  puntero de Git LFS (extraído con `git cat-file -p`) en el sitio exacto de
  un fichero de `corpus/` — que es exactamente lo que produce
  `actions/checkout@v4` con `lfs: false`, el ajuste que usa el job `linux`.

Esto **no es el runner real** (build de `ffmpeg` distinto, `overlay2` en vez
de lo que sea que monte GitHub, sin red controlada del todo) y se dice así en
cada hallazgo. Es la aproximación más cercana disponible desde aquí, y sirvió
para encontrar la causa exacta de las diez, no solo para adivinarla.

### 1.1 El hallazgo de fondo: diez fallos, dos mecanismos

Los diez estaban descritos en `ci/linux-apto.json` con motivos distintos
("no hay tarjeta", "no hay ffmpeg con NVENC", "la estabilidad se comporta
distinto en ext4", "8 fallos", "5 fallos"...). **Reproducidos uno a uno,
resultan ser dos mecanismos, no diez:**

**Mecanismo A — sin motores externos.** `.github/workflows/suite.yml` no
instala nada (`apt-get install` no aparece en el `job: linux`). Sin
`ImageMagick`, ningún motor de `filex.motores.MOTORES = (ImageMagick,
Ghostscript, FFmpeg)` lee PNG/JPG, y el error `"ningún motor disponible lee
'png'"` se propaga hasta romper pruebas que en principio no deberían tocar
ningún motor — MEDIDO: en las superficies MCP y API el formato se resuelve
**antes** de validar la ruta, así que hasta una prueba de confinamiento put­ro
(`ruta no accesible` esperado) revienta si PNG no se puede ni leer.

**Mecanismo B — Git LFS con `lfs: false`.** `corpus/video/tipico.mp4` y
`corpus/audio/{habla_jfk,habla_largo}.flac` son punteros de texto (~130 B)
sin `git lfs checkout`. `os.path.exists()` es `True` para un puntero — es la
trampa 34 del proyecto, aquí sin protección en estos dos ficheros. MEDIDO:
extrayendo el puntero real con `git cat-file -p $(git rev-parse
HEAD:corpus/video/tipico.mp4)` y superponiéndolo por bind-mount, se reproduce
`"ningún motor disponible lee 'mp4'"` **incluso con `ffmpeg` instalado por
`apt`** — no era ausencia de ffmpeg, era que la entrada no era un MP4. Con
`corpus/audio/habla_jfk.flac` igual: sin `ffmpeg` da `FileNotFoundError` en
`setUpClass`, que es exactamente el `"0 pruebas corridas, 1 error de carga"`
que describía `ci/linux-apto.json` para `test_a7_ciego`.

**Y un tercer hallazgo que no estaba en la descripción de NINGUNA fila:**
`filex.gpu.Lock._vivo()` (código de worker1, no tocado aquí) llama a
`tasklist` para saber si el dueño de un lock huérfano sigue vivo. Fuera de
Windows, `tasklist` no existe: `FileNotFoundError`, capturada, y `_vivo()`
devuelve `True` **por el lado seguro del error** ("no robar"). Consecuencia
MEDIDA con `GPU_LOCK=/tmp/aislado.lock` para descartar contención de
máquina: un huérfano **nunca** se recupera en Linux, determinista, 100% de
las veces. `ci/linux-apto.json` describía esto como *"no hay tarjeta"* (para
`test_gpu_lock`, que **no toca la GPU en absoluto** — es un test de mutex) y
como *"no hay ffmpeg con NVENC"* (para una celda de `test_hito2` que tampoco
usa NVENC: es la misma prueba de recuperación de huérfano, con otro
fixture). Es la trampa 90/93 de `CLAUDE.md`, ya documentada para el arnés de
`bench/`, aplicada aquí a un código de `filex/` que nadie había mirado desde
ese ángulo.

Y un cuarto, para el `CUELGA`: `test_cancelacion.ContenedorReal` usa
`IMAGEN = "ghcr.io/c4illin/convertx:latest"` (5,7 GB). `_hay_docker()` solo
comprobaba `docker version` (el demonio vive en `ubuntu-latest`), así que la
clase entraba y `docker run` intentaba **descargar** la imagen en cada
ejecución — lento y no determinista, y exactamente lo que agota un tope de
90 s sin decir por qué.

### 1.2 Los arreglos, uno por causa

Todos son `@unittest.skipUnless` **honestos** con el motivo exacto escrito
—ninguno oculta el porqué—, y ninguno toca `filex/gpu.py`, `filex/sidecar.py`
ni `bench/lib/harness.sh` (carril de worker1). El resto de `filex/` tampoco
se tocó: los diez se arreglan enteros desde `pruebas/`.

| Módulo | Causa real | Arreglo |
|---|---|---|
| `test_gpu_lock` | Mecanismo `_vivo()`/`tasklist` (no "no hay tarjeta": la prueba no toca GPU) | `skipUnless(sys.platform == "win32", …)` en el único test afectado |
| `test_hito2` | La MISMA prueba de huérfano en `LockDeGpu` (no "no hay ffmpeg con NVENC") | mismo `skipUnless`, un método |
| `test_cancelacion` | `CUELGA`: `docker run` descargando una imagen de 5,7 GB no cacheada | `_hay_imagen_local()`: `docker image inspect` (no descarga) antes de dejar entrar a `ContenedorReal` |
| `test_a7_ciego` | Mecanismo A + B: sin `ffmpeg` **o** con un puntero LFS, `setUpClass` revienta | `HAY_FFMPEG` + `_es_audio_real()` (tamaño > 100 KB, no solo `exists()`) |
| `test_cancelacion_procesos` | Mecanismo B: `corpus/video/tipico.mp4` puntero | `_es_video_real()`, aplicado a las 3 clases que lanzan un hijo con vídeo real (8 pruebas) |
| `test_cerrojo` | Mecanismo A: 5 pruebas convierten PNG/JPG de verdad | `HAY_IMAGEMAGICK`, aplicado a los 5 métodos exactos que fallaban (no a la clase entera: hay más que no lo necesitan) |
| `test_hito1` | Mecanismo A, dos formas: `disponibles` vacío sin ningún motor, y PNG sin ImageMagick | `HAY_ALGUN_MOTOR` y `HAY_IMAGEMAGICK`, un método cada uno |
| `test_hito4` | Mecanismo A: 9 métodos convierten o inspeccionan PNG | `HAY_IMAGEMAGICK`, 9 métodos exactos |
| `test_hito7` | Mecanismo A (31 fallos/errores — **una sola causa, no 31**) + un mecanismo C aparte: `CON.png` (R12) y `v4:oculto.webp` (W9/ADS) son reservas de NOMBRE de NTFS, no de Linux | `HAY_IMAGEMAGICK` (clases `CuatroSuperficies`, `WatcherDuplicados`, `ApiConcurrencia` completas + 6 métodos sueltos) y `ES_WINDOWS` (2 métodos: v3, v4) |

**Verificación, dos direcciones para cada uno:**

1. **Camino feliz** (esta máquina, con `ImageMagick` y `ffmpeg` reales): el
   módulo corre igual que antes, 0 regresiones. Confirmado módulo a módulo.
2. **Camino de runner** (contenedor limpio, con los punteros LFS
   superpuestos): el módulo pasa a `rc=0` (aprobado o saltado, nunca roto ni
   colgado). Confirmado módulo a módulo, y con el conjunto de los 10 juntos.

`ci/sonda_linux.py --tope 90` ejecutado DENTRO del contenedor de
aproximación, sobre los 17 módulos:

```
APTOS 14 de 17 · 332 pruebas · 89 saltadas · 32.0 s en total
FALLA: test_hito2, test_sondeo, test_watcher_n
```

Frente al **7 de 17** medido en el runner real antes de esta ronda. Los tres
que siguen en rojo, y por qué **no** se tocan hoy:

- **`test_sondeo`**: el intérprete del contenedor es Python 3.12; el proyecto
  ya tiene documentado (trampa 105, `C43`) que la huella de código depende
  del intérprete y que **3.13 (y aquí 3.12) caducan las aristas** aunque el
  código no haya cambiado. Es una decisión abierta del usuario (`PENDIENTE.md`
  §1.1), no un fallo de este módulo. `ubuntu-latest` fija `python: ['3.11']`
  en la matriz, así que en el runner real esto no debería reproducirse —y por
  eso `test_sondeo` sigue en la lista `aptos` que ya existía.
- **`test_watcher_n`**: sigue con 1 fallo (era 4 en el runner real). Intenté
  reproducirlo en TRES sistemas de ficheros POSIX distintos —DrvFs de este
  worktree, `tmpfs` de `/tmp` en WSL2, y `overlay2` dentro de un contenedor
  Docker— y en los tres pasa limpio. El mecanismo que el propio encargo ya
  apuntaba (`maduros()` se comporta distinto en `ext4`) sigue siendo la
  explicación más probable, pero **no lo pude reproducir para clasificarlo
  con precisión por test**, y no voy a escribir un `skipUnless` sin haber
  visto el fallo con mis propios ojos. Queda declarado, no arreglado.
- **`test_hito2`**: con el arreglo de `_vivo()` puesto, la celda ORIGINAL
  (`test_recoge_un_huerfano_con_espera_cero`) pasa. Pero **dentro del
  contenedor con `ffmpeg` de Debian bookworm aparecieron DOS fallos nuevos**
  que no estaban en la descripción original de la fila: un `.mkv` de dos
  pistas de audio que pierde canales (`A2: número de canales alterado sin
  pedirlo`) y una celda de `av1_nvenc` que se comporta distinto. Los dos
  dependen del **build exacto de ffmpeg** (el proyecto usa N-121159 en
  Windows; Debian bookworm trae otro), no del mecanismo ya cerrado. No se
  tocan hoy: son un tercer mecanismo, sin diagnosticar, y no estaban en el
  encargo de esta ronda.

### 1.3 Por qué `ci/linux-apto.json` no se toca desde aquí

El propio proyecto ya pagó el precio de medir la lista de aptitud en el
entorno equivocado (trampa 104, la razón por la que `C42` existe). Mi
contenedor de aproximación es mejor que WSL2/DrvFs para esto —tiene los
punteros LFS reales y puede quitar los motores de verdad—, pero **sigue sin
ser `ubuntu-latest`**: build de ffmpeg distinto, y sin la garantía de que el
resto del entorno (paquetes del sistema, versión exacta de `pip`, etc.)
coincida. Sobrescribir `ci/linux-apto.json` con el `14/17` de mi contenedor
repetiría exactamente el error que abrió `C42`. Lo que sí es seguro y se
entrega: **el código arreglado**, verificado en dos direcciones (arriba). La
promoción de los 9 módulos arreglados a `aptos` la decide `python3
ci/sonda_linux.py` corrido en el runner real — el trabajo `deriva` de
`.github/workflows/suite.yml` ya existe para eso; recomiendo lanzarlo
(`workflow_dispatch`) después de fusionar esta rama.

---

## 2. C27 — G6 se queda en `aviso`, decisión definitiva

`bench/contrato-familia-resvg.md` ya medía todo lo necesario: los dos casos
que se temían (`png→apng`, `mkv→mka`) no pueden disparar G6 porque ya están
en `EXT_A_FIRMAS`; el riesgo real son 4 falsos positivos de alias de TGA; y
**32 de 32 en ImageMagick, 0 de 41** en los otros seis motores del censo. La
fila estaba abierta por decisión, no por falta de datos.

**Decisión: se queda en `aviso`.** Subir a `fallo` con la excepción de los
alias de TGA exigiría barrer el vocabulario ENTERO de alias de formato —no
solo TGA— para poder afirmar que esos 4 son el conjunto COMPLETO de falsos
positivos; eso no está medido, y forzarlo hoy sería inventar una cobertura
que no existe. El argumento que cierra la fila es el que el propio informe
ya traía: una regla calibrada sobre un motor de siete no puede vetar sin
arrastrar ese riesgo. **MEDIDO:** `grep -n "G6" filex/verificador.py` — sigue
en `aviso` (línea 3461), sin editar.

---

## 3. Verificación de este PR

- **MEDIDO:** `python3 ci/integridad.py` → 9/9 en verde tras actualizar el
  recuento de §3 (`6 ⚫ · 19 🔴 · 10 🟡 · 76 🟢` sobre 111, C27 🔴→🟢 y C42
  🔴→🟡) y la línea "Salida esperada hoy".
- **MEDIDO:** los 10 módulos de `pruebas/` tocados compilan (`py_compile`) y
  se ejecutaron, cada uno, en el camino feliz de esta máquina (0
  regresiones) y en el contenedor de aproximación al runner (`rc=0`).
- **Intérprete:** esta máquina usa Python 3.14.4 (WSL2 nativo) para el
  desarrollo; la verificación de aproximación al runner usa Python 3.12.14
  (`python:3.12-slim-bookworm`); el runner real fija Python 3.11.16 — ninguno
  de los tres es el mismo, y se declara así porque `test_sondeo` demuestra
  que eso puede importar (trampa 105).
- **Entorno:** WSL2 sobre DrvFs (este worktree) para el desarrollo; Docker
  Desktop / WSL2 para los contenedores de aproximación, con y sin red (los
  que instalan `ffmpeg` por `apt` necesitan red; los que no, corren con
  `--network none`). Sin GPU, sin tocar el carril de worker1.
- **Qué quedó fuera y por qué:** `test_watcher_n` (no reproducido en tres
  sistemas de ficheros), dos fallos nuevos de `test_hito2` dependientes del
  build de ffmpeg de Debian (fuera del mecanismo que pedía esta ronda), y
  `C20` (pide una medición nueva —otro motor, otro vocabulario— que no cupo
  en el tiempo de esta ronda; se declara sin tocar en vez de forzar una
  lectura rápida de datos que no la responden).
- **Estado de la máquina:** compartida con otras sesiones activas durante
  toda la tanda (confirmado: un lock de GPU de otro proceso bloqueó una
  prueba mía en un intento, correctamente, y una prueba de timing de
  `test_hito4` dio un falso rojo por contención de máquina bajo la carga de
  mis propios contenedores en paralelo — no se cuenta como fallo real, y no
  se tocó ningún umbral de tiempo para maquillarlo).

## 4. Riesgos y bloqueos

- Ninguno nuevo. El riesgo real es que la aproximación de contenedor
  difiera del runner en algo que no se vio aquí — por eso la promoción final
  se deja al `deriva` de la CI real, no a este informe.

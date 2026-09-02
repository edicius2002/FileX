# N29 + B23 (resto) — la mitad de plataforma que faltaba en `_vivo()`, y las 4 configuraciones que cierran el racimo de 9

Informe de **worker1** (carril GPU), ronda 5. Encargo: `ENCARGO.md` /
`ESTADO-Y-REPARTO.md` §Ronda 5.

---

## 0. Entorno y advertencias de la ronda, tal como pide el encargo

- **Worktree:** `C:\Users\krato\orca\workspaces\FileX\filex-gpu` (rama
  `edicius2002/filex-gpu`). CCB está desmontado (decisión de ronda 5).
- **Venvs:** ninguno en el worktree. Se usan por ruta absoluta desde
  `D:\Work\research\FileX\.venv-ai\` (RapidOCR, Docling, torch CUDA) y
  `D:\Work\research\FileX\.venv-mcp-filex\` (suite de pruebas). **No se
  instaló nada en ellos.**
- **Cifras absolutas:** las 140 celdas de `bench/k-oem-acantilados.md` se
  midieron desde `D:` (worktree de CCB); las de este informe, desde `C:`
  (worktree de Orca). **Es otro volumen, no solo otra tanda** — no se
  comparan cifras absolutas de tiempo entre los dos informes; el
  arrepentimiento y el `k` (adimensionales, sobre el mismo corpus y el mismo
  evaluador) sí son comparables.
- **GPU:** `filex.gpu.Lock` tomado por configuración, conductor único y
  desprendido, reiniciando el proceso Python entre configuraciones (el
  asignador no devuelve VRAM — trampa 67). Documentos recorridos de mayor a
  menor ppp nativo dentro de cada proceso (`d5a` 90 → `d5c` 80 → `d5` 72 →
  `d5b` 60), como ya hacía `b23_k_d5.py`.
- **Sin Docker en esta parte del encargo:** carril GPU, no toca contenedores.

---

## 1. N29 — `filex.gpu.Lock._vivo()` no sabía preguntar fuera de Windows

### 1.1 El fallo, tal como lo dejó worker2 diagnosticado (`bench/ci-y-contrato.md` §1)

`_vivo(winpid, imagen)` llamaba **solo** a `tasklist` (Windows). Fuera de
Windows, `subprocess.run(["tasklist", ...])` lanza `FileNotFoundError`, el
`except` capturaba el error y devolvía `True` — "vivo" — por el lado seguro
del error de la trampa original. Consecuencia: **un lock huérfano nunca se
recupera fuera de Windows**, determinista, 100 % de las veces. No era "no hay
tarjeta" (como decía `ci/linux-apto.json` sobre `test_gpu_lock`) ni "no hay
ffmpeg con NVENC" (como decía sobre una celda de `test_hito2`): la prueba no
toca ninguna de las dos cosas, es un test de mutex.

### 1.2 El arreglo

`filex/gpu.py`: `_vivo()` ahora **despacha por plataforma**:

```python
def _vivo(winpid, imagen):
    if not winpid:
        return True
    if sys.platform == "win32":
        return _vivo_win32(winpid, imagen)   # exactamente el código de antes
    return _vivo_posix(winpid, imagen)       # NUEVO
```

`_vivo_win32` es **byte a byte** el código anterior (regresión-cero por
diseño: quien no tocaba nada de `tasklist` no puede empeorar). `_vivo_posix`
es Python puro sobre `os.kill(pid, 0)`, que en POSIX **sí** tiene semántica
estándar y no necesita ningún binario externo:

- `ProcessLookupError` (ESRCH) → el PID no existe → `False` (muerto de
  verdad, se puede robar).
- `PermissionError` (EPERM) → el PID existe pero no es nuestro → `True` (no
  robar).
- Cualquier otro `OSError` → no se pudo preguntar → `True` (lado seguro).
- Si el PID existe, se comprueba `/proc/<pid>/comm` contra `imagen` — el
  equivalente POSIX de que `_vivo_win32` compare contra la columna de
  `tasklist` — porque POSIX **también** reutiliza PID. Sin `/proc` (no Linux)
  no se puede verificar la identidad y se responde `True`.

**Por qué no es la misma media que `bench/lib/harness.sh` (trampa 90):** el
arnés de shell usa `/proc/$$/winpid` + `tasklist` sin `.exe`, que es la
mitad que la trampa 90 ya documentó rota en WSL. Esta función **no** usa
ninguna de las dos piezas: es `os.kill`, que sí funciona en el intérprete que
la ejecuta sin depender de un binario de Windows accesible desde el PATH de
otro sistema operativo.

**Por qué no se puede reutilizar como sustituto en Windows — MEDIDO en esta
misma máquina:**

```
platform win32
kill(self,0) OK
kill(fake,0) FAIL OSError [WinError 87] El parámetro no es correcto
proc exists? False
```

En Windows, `os.kill(pid_inexistente, 0)` da un `OSError` genérico
(`WinError 87`), **no** `ProcessLookupError` — así que el despacho por
`sys.platform` no es cosmético: sin él, `_vivo_posix` mal clasificaría un PID
muerto en Windows como "no se pudo preguntar, no robar", perpetuando el
mismo bug con otro disfraz.

### 1.3 Control positivo y negativo, en Linux real (trampa 40: sondear el mecanismo, no solo el resultado)

Ejecutado en **WSL2 Ubuntu, Python 3.14.4** (`wsl -e python3`, no deducido de
la documentación de `os.kill` — trampa 45), importando `filex.gpu` desde el
mismo árbol de este worktree vía `/mnt/c/...`, con `GPU_LOCK` apuntando a un
fichero aislado en `/tmp` (propio de la VM de WSL2, no cruza a Windows —
trampa 41/90).

**Sondeo directo de `_vivo()` (cinco casos, sin pasar por `Lock`):**

```
platform linux
vivo(pid propio, imagen correcta)            = True   (esperado True)
vivo(pid propio, imagen FALSA)               = False  (esperado False)
vivo(pid de un proceso ya terminado, sin imagen) = False (esperado False)
vivo(pid absurdo)                            = False  (esperado False)
vivo(sin winpid)                             = True   (esperado True)
TODO OK: mecanismo POSIX de _vivo() verificado en Linux real (WSL2 Ubuntu)
```

**Control POSITIVO, extremo a extremo sobre `filex.gpu.Lock` completo:** un
proceso hijo real toma el lock (`GPU_LOCK=/tmp/aislado-n29.lock`), se
verifica que el fichero trae **el PID real del hijo** (no el de un
lanzador — trampa 93, ya cubierta porque el propio proceso publica su
`os.getpid()`), se mata al hijo con `SIGKILL` (huérfano de verdad, sin
`finally` que limpie) y se intenta tomar el lock de nuevo:

```
hijo dice tomar()= True
campos del lock: ['prueba-n29', '2648981', '2648981', 'python3', ..., '/mnt/c/...']
recuperacion: ok= True tardo 0.001 s
N29 CERRADO EN LINUX REAL: el huerfano SI se recupera
```

**Control NEGATIVO, mismo escenario, con la `_vivo()` VIEJA reimplantada a
propósito** (monkeypatch de `gpu._vivo` a la versión que solo llama a
`tasklist`), para demostrar que sin el arreglo el mecanismo realmente fallaba
como se dijo — no solo "el nuevo código pasa", sino "el viejo código no
pasaba, por el motivo que se afirma":

```
CON EL BUG VIEJO: ok= False tardo 2.425 s (esperado False, ~2s: nunca se recupera)
CONTROL NEGATIVO CONFIRMADO: sin el arreglo, el huerfano NUNCA se recupera
```

**MEDIDO**, las dos direcciones.

### 1.4 Regresión-cero en Windows

Ejecutado en Windows (`D:\...\​.venv-mcp-filex\Scripts\python.exe`, esta
máquina):

```
pruebas/test_gpu_lock.py pruebas/test_hito2.py -q
39 passed, 11 subtests passed in 36.33s
```

Sin cambios de comportamiento en la rama Windows: `_vivo_win32` es una copia
literal del código anterior.

### 1.5 Pruebas nuevas y las que dejaron de necesitar el `skipUnless`

- **`pruebas/test_gpu_lock.py`**, dos clases nuevas de mecanismo (11
  pruebas): `VivoDespachaPorPlataforma` (espía, con `mock.patch.object`, que
  rama se invoca según `sys.platform` — no basta con que el resultado sea
  correcto, trampa 40) y `VivoPosixMecanismo` (`os.kill`/`open` controlados a
  mano, separando las tres respuestas de POSIX que Windows no distingue).
  Estas corren en **cualquier plataforma**, incluida esta máquina Windows.
- Los dos métodos que llevaban `@unittest.skipUnless(sys.platform ==
  "win32", ...)` por esta causa exacta —
  `pruebas.test_gpu_lock.GpuMutex.test_python_excluye_y_muerto_se_libera` y
  `pruebas.test_hito2.LockDeGpu.test_recoge_un_huerfano_con_espera_cero` —
  **pierden el skip**: el mecanismo que lo motivaba ya no existe. **MEDIDO
  que ahora pasan también en Linux real**, no solo deducido:

```
=== WSL2 Ubuntu, Python 3.14.4, python3 -m unittest ===
pruebas.test_gpu_lock:  Ran 2 tests ... OK
pruebas.test_hito2.LockDeGpu:  Ran 9 tests ... OK
```

  (El resto de `test_hito2.py` fuera de `LockDeGpu` no se corrió completo en
  WSL2 — no hace falta para este encargo y podría depender de `ffmpeg`/GPU
  ausentes en esa sesión concreta; se corrió la clase exacta que cambiaba.)

### 1.6 Qué NO se tocó, y por qué

- **`bench/lib/harness.sh`** (`_gpu_dueno_vivo`, la mitad de shell): sigue
  con `/proc/$$/winpid` + `tasklist`, con el problema que documenta la
  trampa 90. **No es el mismo código** que `filex.gpu._vivo()` — son dos
  primitivos distintos ya declarados así en el docstring del módulo (§1) — y
  el encargo pide arreglar `filex/gpu.py`, no el arnés de shell. Migrar el
  arnés al mutex (o darle su propia rama POSIX) sigue **PENDIENTE**, y es
  además el mismo pendiente que trampa 90/96 ya dejaban escrito sobre la
  migración de 24 de 25 arneses `.py`.
- **`filex/verificador.py`, `filex/motores.py`, `filex/api.py`,
  `filex/nucleo.py`**: no tocados (carril de worker2).

---

## 2. B23 (resto) — las 4 configuraciones que faltaban del racimo de 9

`bench/k-oem-acantilados.md` había medido 5 de 9 configuraciones (RapidOCR
v6+R6, PaddleOCR v6 medium, EasyOCR, Tesseract psm3, Tesseract psm11) sobre
la familia `d5` (4 documentos, 60/72/80/90 ppp nativos) × 7 factores (0,75 /
0,875 / 1,00 / 1,125 / 1,25 / 1,40 / 1,60). Este informe completa las 4 que
quedaban: **Docling defecto, Docling+R6, RapidOCR v6 small defecto, RapidOCR
v5 mobile defecto** — 112 celdas más (4 configuraciones × 4 documentos × 7
factores), MISMA rejilla y MISMO evaluador (`bench/scripts/ocr_eval.py`,
`evaluar(texto, "acentos", REF)` con `REF` de `d4_texto.BLOQUES`, 610 → 596
acentuados) para que el arrepentimiento sea comparable celda a celda con las
5 ya publicadas.

**Scripts nuevos** (`bench/salidas-k-oem-acantilados/`): `b23_resto_rapidocr.py`
(RapidOCR v6/v5 defecto — misma receta de raster gris, ruta, sin declarar
pHYs que `rapidocr-r6`; **reutiliza los 28 `kf####__doc.png` ya existentes**
por nombre) y `b23_resto_docling.py` (Docling defecto/+R6 — no consume PNG:
rasteriza el PDF él mismo con `RapidOcrOptions.scale`, igual que
`bench/salidas-k-motor/docling_lote_km.py`, backend `torch`, `lang=english`
— el mismo defecto histórico de aquel script, para comparabilidad con las
filas "Docling..." de `bench/k-por-motor.md`). Conductor único y desprendido
`conductor_b23_resto.sh`, reiniciando el proceso Python entre configuración y
configuración.

Los tres scripts calculan `ROOT` desde su propia ubicación (`os.path.dirname`
repetido) en vez de hardcodearlo — el `ROOT` fijo de `b23_k_d5.py` apuntaba a
`D:\...\.ccb\workspaces\worker1`, que ya no existe tras desmontar CCB en esta
misma ronda. Un `ROOT` fijo habría repetido el `rc=127` de la trampa 100 la
próxima vez que cambie la infraestructura del worktree.

### 2.1 Verificado antes de escribir (trampa 99), las 112 celdas

```
conductor_b23resto.progreso.log:
FIN docling-def       rc=0 celdas=28
FIN docling-r6         rc=0 celdas=28
FIN rapidocr-v6-def    rc=0 celdas=28
FIN rapidocr-v5-def    rc=0 celdas=28
```

Por celda (`rc_reps`, tres repeticiones por celda — cierra la brecha que
`b23_k_d5.py` dejó anotada: no registraba `rc` para los motores GPU):

| Configuración | omitidas por VRAM | no deterministas | CER=100 % | `rc≠0` |
|---|---:|---:|---:|---:|
| Docling defecto | 0/28 | 0/28 | 0/28 | 0/84 |
| Docling+R6 | 0/28 | 0/28 | 0/28 | 0/84 |
| RapidOCR v6 small defecto | 0/28 | 0/28 | 0/28 | 0/84 |
| RapidOCR v5 mobile defecto | 0/28 | 0/28 | 0/28 | 0/84 |

**Ninguna configuración se acerca a "100 % de sus celdas a CER 100 %"** —
descartado por inspección, no por confianza en el `rc` del proceso. `err.log`
de las cuatro sin una sola línea de `WARN`/`ERROR`/`Traceback` (aparte de un
`UserWarning` de PyTorch sobre `padding='same'`, benigno y ya visto en el
smoke test). VRAM libre 8,8–9,0 GiB durante toda la sesión (guardián de
Docling en `VRAM_TOPE_MIB=11500`, nunca activado).

**Ruido, honesto:** los dos testigos (CLAUDE.md §3) dan `limpia` en 3 de 4
configuraciones; **`docling-def` sale `SUCIA`** (testigo de proceso: 58,0 ms
al empezar frente a 26,7 ms de referencia en reposo, nivel 2,18) — coincide
con el arranque en frío de ese proceso (primera carga de pesos de la
sesión), no con contención sostenida (`proc_fin` baja a 40,1 ms). **No
afecta al CER ni al determinismo** (ambos verificados por celda, tabla de
arriba) — solo a los tiempos, que este informe no publica por celda. Se
declara igual, porque la regla no distingue "no importa" de "no se mide".

**Advertencia sobre el raster reutilizado, MEDIDA y no anotada en la ronda
4:** los 28 `kf####__escaneado_d5*.png` regenerados en esta sesión tienen el
**mismo tamaño en bytes, exacto, que los del `MANIFIESTO.md` original**, pero
**`sha256` distinto**. `magick compare -metric RMSE` (trampa 5: no SSIM) da
**0** entre el fichero de esta sesión y uno regenerado de nuevo en el acto —
son **píxeles idénticos**. Es la trampa 22 (`SOURCE_DATE_EPOCH` no hace
reproducible un PDF de ImageMagick) extendida al PNG: metadatos de fecha
mueven el `sha256` entre ejecuciones en días distintos sin mover un solo
píxel. **La "orden exacta que los reproduce" del `MANIFIESTO.md` reproduce
los píxeles, no el byte** — que es lo único que le importa a un motor de
OCR. Detalle y hashes nuevos en
`bench/salidas-k-oem-acantilados/MANIFIESTO.md` §Ronda 5.

### 2.2 El `k` por mínimo arrepentimiento, las 4 configuraciones

Mismo método que `bench/k-oem-acantilados.md`: por documento, `k*` es el
factor de menor CER; el arrepentimiento de un candidato `k` en un documento
es `CER(k) − CER(k*)`; el arrepentimiento del candidato es el **máximo**
sobre los 4 documentos; el `k` publicado minimiza ese máximo.

| Configuración | `k` por mínimo arrepentimiento | Arrepentimiento máx. | `k` óptimo por documento (d5a·d5c·d5·d5b) |
|---|---:|---:|---|
| Docling defecto | **1,125**¹ | 8,4 pt | 0,875 · 1,00 · 0,875 · 1,125 |
| Docling + R6 | **1,60** | 8,8 pt | 1,125 · 1,40 · 1,60 · 1,60 |
| RapidOCR v6 small defecto | **1,25** | 1,2 pt | 1,00 · 1,00 · 1,00 · 1,25 |
| RapidOCR v5 mobile defecto | **1,00** | 4,0 pt | 1,00 · 1,00 · 1,60 · 1,00 |

¹ **Empate a 8,4 pt** entre `k` = 1,125 / 1,25 / 1,40 / 1,60 (arrepentimiento
idéntico hasta la décima en los cuatro): la meseta de arrepentimiento es
plana en todo ese tramo para Docling defecto — no hay un único mínimo, hay
una región. Se publica el extremo bajo de la meseta (1,125) por convención
con el resto de la tabla (el candidato más pequeño entre los empatados), sin
que eso implique que sea "mejor" que 1,60 dentro del empate.

**Racimo de 9 completo, tabla conjunta (5 de `bench/k-oem-acantilados.md` +
4 de aquí):**

| Configuración | `k` | Arrepentimiento máx. |
|---|---:|---:|
| RapidOCR v6 + R6 | 1,00 | 4,8 pt |
| PaddleOCR v6 medium | 1,00 | 0,3 pt |
| EasyOCR | 1,60¹ | 0,2 pt |
| Tesseract `psm 3` | 1,40 | 0,7 pt |
| Tesseract `psm 11` | 1,60¹ | 0,2 pt |
| **Docling defecto** | **1,125**² | **8,4 pt** |
| **Docling + R6** | **1,60** | **8,8 pt** |
| **RapidOCR v6 small defecto** | **1,25** | **1,2 pt** |
| **RapidOCR v5 mobile defecto** | **1,00** | **4,0 pt** |

¹ En el borde de la rejilla, igual que ya declaraba `k-oem-acantilados.md`.
² En el borde de una meseta plana, ver nota 1 de la tabla anterior.

### 2.3 Lo que dice esta tabla que el racimo de 5 no podía decir

**Los dos arrepentimientos más grandes del racimo entero son los dos
Docling, y no están cerca de los demás: 8,4 y 8,8 puntos frente a un máximo
de 4,8 en las otras siete.** No es el mismo tipo de "arrepentimiento
grande" que ya tenía RapidOCR v6+R6 (4,8 pt, achacado al peine de B16): mirar
la tabla de CER por documento (`bench/salidas-k-oem-acantilados/json/b23resto_*.json`)
muestra que el mecanismo es otro. `escaneado_d5b` (el documento más pequeño,
60 ppp nativos) es una fuente de arrepentimiento sistemática para Docling:
**33,1 % a factor 0,75** en Docling defecto y **CER entre 19,3 y 36,7 %** en
Docling+R6 a lo largo de TODA la rejilla — nunca baja de 19 puntos, ni
siquiera en su propio óptimo (19,3 % a factor 1,60). Los otros tres motores del
racimo (RapidOCR v6 defecto, RapidOCR v5 defecto, y los ya publicados)
alcanzan CER de un dígito en `d5b` en al menos un factor. **Docling
degrada peor que el resto específicamente en el documento pequeño**, y eso
—no un pico aislado tipo peine— es lo que empuja su arrepentimiento máximo
por encima del resto del racimo.

**RapidOCR standalone reproduce el peine también SIN R6:** `RapidOCR v6
small defecto` da, sobre `escaneado_d5`, la secuencia 10,60 / 21,30 / 0,50 /
1,50 / 1,70 / 9,90 / 1,30 a lo largo de los 7 factores — no monótona, con un
mínimo aislado en el centro de la rejilla flanqueado por valores 10-20×
peores a un paso de distancia. Es la MISMA forma que `bench/k-oem-acantilados.md`
§B23 ya caracterizó para RapidOCR v6+R6, y el corolario de aquel informe se
sostiene: **el peine es del detector de RapidOCR (con o sin R6, con o sin
docling encima), no de la corrección R6 en concreto.**

**Sobre la comparación con `k-por-motor.md` (corpus `d4`, un solo
documento):** ese informe fijaba `k=1,80` (arrepentimiento 1,17) para
"Docling+RapidOCR torch (defecto)" y `k=0,875` para "Docling+RapidOCR torch +
R6" (tras la corrección de `ppp-y-normalizacion.md` §2.8). Sobre la familia
`d5` aquí: Docling defecto aterriza en una meseta que **incluye** 1,60 (el
valor histórico) pero cuyo mínimo formal se publica en 1,125; Docling+R6
aterriza en **1,60**, lejos del 0,875 histórico. **No se declara un `k`
nuevo "vigente" a partir de esto**: el propio racimo de 9 no reconcilia el
`k` de un corpus de un documento (`d4`) con el de mínimo arrepentimiento
sobre cuatro (`d5`) para ningún motor sin repetir el trabajo de
`k-por-motor.md` §4 (mínimo arrepentimiento sobre **ambos** corpus a la
vez) — que no estaba en el encargo de esta ronda y queda **PENDIENTE**,
igual que ya quedaba para Tesseract en `k-oem-acantilados.md`.

**Y una asimetría que sí es nueva: para RapidOCR standalone y Docling el `k`
óptimo NO coincide entre "defecto" y "+R6" en 3 de 4 documentos** (Docling:
d5a 0,875 vs 1,125; d5c 1,00 vs 1,40; d5 0,875 vs 1,60; solo d5b coincide en
1,125 vs 1,60 — ninguno coincide, de hecho). La corrección R6 no solo cambia
el CER: cambia dónde está el óptimo, documento por documento. Un `k` fijado
sin declarar si lleva R6 no es transferible entre las dos variantes del
mismo motor, ni siquiera dentro del mismo corpus.

### 2.4 Manifiesto

Los 28 rásteres PNG reutilizados se borraron de nuevo al terminar (no se
versionan). `bench/salidas-k-oem-acantilados/MANIFIESTO.md` §"Ronda 5" trae
nombre, tamaño, `sha256` (de esta sesión — ver advertencia §2.1) y la orden
exacta.

### 2.5 Qué queda PENDIENTE del racimo de 9, sin cambios respecto a la ronda 4

- La rejilla de factores por encima de 1,60 para EasyOCR y Tesseract `psm
  11` (ambos en el borde de la rejilla medida).
- Separar el efecto del pHYs del efecto del corpus en el `k` de Tesseract.
- Reconciliar el `k` de mínimo arrepentimiento entre el corpus `d4`
  (`k-por-motor.md`) y `d5` (aquí y en `k-oem-acantilados.md`) para
  cualquier motor — **nuevo**, y más urgente para Docling que para los
  demás, por la magnitud del desacuerdo (§2.3).
- Sondear las cajas de las celdas de peine de RapidOCR standalone/defecto,
  igual que `cajas-rapidocr.md` ya hizo para `d5c`/`d5a` — **nuevo, mismo
  mecanismo que B16, un motor más**.

---

## 3. Aceptación — suite integral del árbol

```
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe -m pytest pruebas/ -q -rs
434 passed, 3 skipped, 2 warnings, 116 subtests passed in 169.46s (0:02:49)
```

**0 failed.** Las cuatro declaraciones que piden las trampas 94/101 (un
recuento sin ellas no es la misma garantía):

- **Intérprete:** Python 3.11.9, `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe`,
  `sys.platform == "win32"`. Es el mismo intérprete que fija `ubuntu-latest`
  en la matriz de CI para `test_sondeo` (trampa 105) — 3.11, no 3.13/3.14 —
  así que la huella de código no caduca por este motivo.
- **Entorno:** Docker Desktop **levantado**, con los tres contenedores del
  proyecto en marcha (`filex-convertx`, `filex-snapotter`,
  `filex-snapotter-pg`, más `edicius-hq-api` de otra sesión) — `docker
  version` responde, `docker ps` los lista sanos. Este "0 failed" **sí**
  incluye el hito 5 y la cancelación real de contenedor (trampa 94: un "0
  failed" sin Docker no es la misma garantía).
- **Qué quedó fuera y por qué — los 3 `skipped`, ninguno nuevo ni tocado por
  este encargo:**
  - `test_cerrojo.py:479` — necesita dos volúmenes distintos a mano (no hay
    en esta máquina).
  - `test_hito6.py:173` — falta el ráster de `bench/salidas-hito6/preparar_h6.py`
    (no se generó en esta sesión; fuera del alcance de N29/B23).
  - `test_hito6.py:630` — pide `FILEX_PRUEBAS_SIDECAR=1` explícito (no se
    activó: no es parte del encargo de esta ronda).
- **Estado de la máquina:** GPU compartida — `nvidia-smi` mostró 86 %
  de utilización puntual justo antes de correr la suite (bajó a los niveles
  habituales durante la corrida; ninguna prueba de GPU falló ni dio
  contención). Sesión de escritorio remoto activa (estructural, no se cierra
  — CLAUDE.md §1). Sin lock de GPU tomado por nadie al empezar
  (`%TEMP%/filex-gpu.lock` ausente). El barrido de B23 (resto) ya había
  terminado y liberado el lock antes de correr la suite — no hay
  solapamiento entre "medir" y "verificar" (trampa 84).

**Regresión-cero confirmada por la propia suite integral**, no solo por los
39/39 de `test_gpu_lock.py`+`test_hito2.py` en aislamiento (§1.4): los 434
pasan juntos, incluidos los módulos de worker2 (`test_a7_ciego`,
`test_cancelacion`, `test_hito5`, `test_hito7`, `test_sondeo`, etc.) que no
se tocaron en este encargo.

---

## 4. Qué se tocó y qué no

**Tocado (carril propio):**
- `filex/gpu.py` — `_vivo()` despacha por plataforma; `_vivo_win32` (código
  viejo, sin cambios) + `_vivo_posix` (nuevo).
- `bench/salidas-k-oem-acantilados/` — 2 scripts nuevos
  (`b23_resto_rapidocr.py`, `b23_resto_docling.py`), 1 conductor nuevo
  (`conductor_b23_resto.sh`), `MANIFIESTO.md` ampliado, `json/` y `texto/`
  con las 112 celdas nuevas.

**Tocado fuera del carril estricto, con justificación:**
- `pruebas/test_gpu_lock.py` — 2 clases de prueba nuevas (mecanismo) + retiro
  de 1 `skipUnless` que ya no aplica.
- `pruebas/test_hito2.py` — retiro de 1 `skipUnless` que ya no aplica (mismo
  motivo, mismo mecanismo). Ninguna otra línea de este fichero se tocó.
  `pruebas/` no está en la lista de módulos exclusivos de ningún carril, y el
  propio `skipUnless` que se retira decía explícitamente *"el arreglo es de
  worker1, no de esta prueba"* — dejarlo vivo tras arreglar `_vivo()` habría
  repetido la trampa 94 (una suite "verde" que no ejercita el camino real).

**No tocado (carril de worker2):** `filex/verificador.py`, `filex/motores.py`,
`filex/api.py`, `filex/nucleo.py`. `bench/lib/harness.sh` es mío por reparto
pero **no se tocó**: su problema de plataforma (`_gpu_dueno_vivo`, trampa 90)
es un primitivo distinto (`/proc/$$/winpid` + `tasklist` desde shell, no
`os.kill` desde Python) y el encargo pedía arreglar `filex/gpu.py`, no el
arnés de shell — queda **PENDIENTE**, igual que ya lo dejaba la trampa 90.

---

## 5. Entrega

Commiteado en `edicius2002/filex-gpu`. **No se empujó ni se abrió PR** — no
tengo credenciales de `gh auth` verificadas en este *worktree* (no lo
intenté: el flujo de la ronda 4 en adelante es que el maestro empuja y abre
el PR).



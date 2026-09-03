# Cierre — worker9, carril CPU/Docker nuevo (`edicius2002/filex-cpu-cierre`)

**Rama:** `edicius2002/filex-cpu-cierre`, base `main`. **Entorno:** Windows 10, sin GPU (no se
tocó el lock). Docker Desktop levantado durante toda la tanda (`docker info` antes de empezar,
imagen `filex-c13:latest` ya presente localmente). Venvs en `D:\Work\research\FileX\` (el
*worktree* no trae ninguno; no se instaló nada en ellos).

Dos filas sin relación entre sí, en el orden que pedía el encargo: `C46` primero (§1),
`C42` después (§2).

---

## 1 · `C46` — las dos guardas del acuerdo `spa`/`eng` — **MEDIDO**

### 1.1 Punto de partida, citado, no redescubierto

`bench/acuerdo-y-cruce.md` §2 midió el acuerdo `spa`/`eng` (`difflib.SequenceMatcher(None, spa,
eng).ratio()`) sobre 8 documentos y lo refutó como regla: **2 mecanismos diagnosticados** rompen
la separación en 4 de los 8 documentos —

- **Silencio.** `d3` y `d4e` dan 0 caracteres en las dos pasadas (`--psm 3`); `difflib` compara
  dos cadenas vacías y da `1,000` — «acuerdo perfecto» sobre un CER real del 100 %.
- **Sustitución acentuada.** `d4a` (CER `spa` 0,17 %) y `d4c` (CER `spa` 1,68 %) leen casi
  perfectamente en español, pero `eng` no omite los diacríticos: **sustituye letras** (`ó`→`é`,
  `ñ`→`N`/`fh`…), y `difflib` penaliza esa sustitución como si fueran dos caracteres arbitrarios
  — acuerdo 0,735 y 0,542, ambos por debajo del umbral de 0,80.

El propio informe deja escrito el precedente a replicar para las dos guardas que faltan:
**longitud mínima no vacía** (`filex/verificador.py:5383`, `P9_TOKENS_MIN = 8`) y **una
comparación que no penalice sustituciones de un carácter acentuado** — con el aviso explícito de
que normalizar con NFC/NFKD **ya se probó y no sube el acuerdo de `d4a` por encima de 0,73**
(§2.2 de ese informe): hacía falta una métrica distinta, no una normalización de la entrada.

### 1.2 Las dos guardas implementadas

Script propio (no se toca `bench/salidas-acuerdo-y-cruce/_c20_acuerdo.py`, es de otro carril):
`bench/salidas-c46-guardas/_c46_guardas.py`.

**Guarda 1 — `GUARDA_TOKENS_MIN = 8`.** Mismo patrón que `P9_TOKENS_MIN`: una constante nombrada,
comprobada ANTES de comparar. Si `spa` o `eng` normalizados (`norm_acentos`, ver 1.3) tienen menos
de 8 tokens, el veredicto es `no_aplica` con motivo explícito, no un acuerdo fabricado. Con
margen amplio: los documentos afectados por el silencio dan **0 tokens**; el resto da entre
**12 y 96** — no hay ningún caso cerca del umbral que obligara a calibrarlo más fino.

**Guarda 2 — distancia de edición ponderada (`acuerdo_ponderado`), no `difflib`.** Levenshtein de
alineamiento completo con el coste de **sustitución** reducido (0,3 en vez de 1,0) cuando **uno
de los dos caracteres alineados** es una vocal acentuada o `ñ` — inserción/borrado siguen
costando 1,0 siempre, porque son ellos los que de verdad indican texto que falta o sobra, no una
letra mal leída en la misma posición. `acuerdo = 1 − distancia_ponderada / max(len(spa), len(eng))`,
acotado a `[0, 1]` porque ningún coste supera 1,0.

Control de sanidad antes de tocar Docker (aislado, sobre cadenas sintéticas):

| Caso | `acuerdo_ponderado` |
|---|---:|
| Idénticas | 1,000 |
| `sensación` vs `sensacién` (sustitución acentuada, 1 carácter) | 0,967 |
| `sol` vs `sel` (sustitución SIN acento, 1 carácter) | 0,667 |
| `año` vs `ano` (ñ→n) | 0,900 |

Confirma la propiedad que pedía el encargo: una sustitución acentuada cuesta poco; una
sustitución de letras sin acento (que sí es una discrepancia real) sigue costando lo normal.

### 1.3 Método de remedición — idéntico al original, sin variarlo

Tesseract 5.5.0 **standalone** dentro de `filex-c13` (no el Tesseract embebido en
`gswin64c.exe`), `--psm 3` fijo, `docker run --rm --init --entrypoint timeout --workdir /work`
con rutas relativas (mismas dos disciplinas ya documentadas: `--init` porque sin él `timeout`
queda de PID 1 y `docker run` da `rc=125` sin ejecutar nada; `--workdir` + ruta relativa porque
con ruta absoluta `tesseract` fallaba con «could not create TXT output file»). Los mismos 8
documentos, a los mismos ppp nativos (`magick -density N -units PixelsPerInch`). CER = verdad,
vía `bench/scripts/ocr_eval.py::norm_acentos` (NFC + minúsculas + `[a-z0-9áéíóúüñ ]`, la métrica
CANÓNICA acentuada desde el 2026-08-28) contra la referencia de cada documento (los cuatro
legado, 79 caracteres sin tildes; la familia `escaneado_d4`, 610 caracteres con 35 acentuados).

```
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe bench/salidas-c46-guardas/_c46_guardas.py
```

### 1.4 MEDIDO: las dos guardas cierran los dos mecanismos diagnosticados, 4 de 4

| Documento | ppp | acuerdo viejo (`difflib`) | acuerdo nuevo (ponderado) | tokens spa/eng | veredicto | CER `spa` | CER `eng` |
|---|---:|---:|---:|---:|---|---:|---:|
| `patologico_escaneado` | 200 | 1,000 | 1,000 | 12/12 | `bueno` | 0,00 % | 0,00 % |
| `escaneado_d1` | 150 | 1,000 | 1,000 | 12/12 | `bueno` | 0,00 % | 0,00 % |
| `escaneado_d2` | 100 | 0,983 | 0,975 | 13/13 | `bueno` | 30,38 % | 27,85 % |
| `escaneado_d3` | 100 | **1,000** | — | **0/0** | **`no_aplica`** | 100,00 % | 100,00 % |
| `escaneado_d4a` | 200 | **0,735** | **0,969** | 96/96 | `bueno` | 0,17 % | 7,05 % |
| `escaneado_d4c` | 200 | **0,542** | **0,935** | 96/96 | `bueno` | 1,68 % | 10,91 % |
| `escaneado_d4` | 200 | 0,312 | 0,646 | 62/60 | `ruido` | 50,34 % | 59,06 % |
| `escaneado_d4e` | 200 | **1,000** | — | **0/0** | **`no_aplica`** | 100,00 % | 100,00 % |

(Umbral de clasificación conservado del original: `≥0,80` = `bueno`, `≤0,70` = `ruido`.)

**Los cuatro documentos que rompían la separación quedan corregidos:**

- `d3`/`d4e`: la guarda 1 los saca de la comparación en vez de darles `1,000` fabricado —
  **`no_aplica` en vez de `bueno` falso**.
- `d4a`/`d4c`: la guarda 2 los sube de la zona `ruido`/`banda` (0,735 y 0,542) a `bueno` limpio
  (0,969 y 0,935), en línea con su CER real (0,17 % y 1,68 %).
- `d4` sigue correctamente en `ruido` (0,646, CER 50,34 %/59,06 %) — el margen entre el `ruido`
  más alto (0,646) y el `bueno` más bajo entre los seis documentos comparables (0,935) es de
  **0,289**, muy por encima de la banda ambigua 0,70-0,80 del método original, y ningún
  documento cae ya en esa banda.

### 1.5 `escaneado_d2` — anomalía preexistente, verificada leyendo el texto, no una tercera guarda

`d2` acuerda alto (0,975) con un CER `spa` del 30,38 % — a primera vista una lectura falsa
adicional. **No es uno de los dos mecanismos que el encargo pedía cerrar** (el informe original
no lo menciona en §2.2) y **ya estaba así antes de esta ronda** (0,983 en la medición de
`bench/acuerdo-y-cruce.md`): las dos guardas no lo tocan ni lo empeoran.

Se inspeccionó el texto en vez de suponer (regla del proyecto: sondear, no deducir):

```
--- spa ---                          --- eng ---
DOCUMENTO ESCANEADO                  DOCUMENTO ESCANEADO
                                      
que solo existe como pixeles.        que solo existe como pixeles.
                                      
Ín OCR.                              n OCR.
                                      
Texto                                Texto
                                      
Debe recuperarse co!                 Debe recuperarse cor
```

El contenido real está presente y es correcto: lo que cambia es el **orden de las líneas** que
`--psm 3` (segmentación automática de página) decidió, más un par de bordes cortados (`co!`/`cor`
en vez de `con`). Las dos pasadas de idioma leen el MISMO reordenamiento — no hay invención de
contenido divergente entre `spa` y `eng`, que es justo lo que el acuerdo está diseñado para
detectar (`filex/verificador.py`, comentario de P9: *"el ACUERDO entre dos pasadas de OCR con
idiomas distintos... = texto reconocido... = invención"*). Como control de contraste, se leyó
también `d4` (el único `ruido` real de los 6 comparables): ahí `spa` y `eng` sí DIVERGEN —
`"Debe recuperarse co!"` frente a algo como `"eo sobre vemtión volúmanes..."` en `spa` contra
`"recnicn sobre weiroan wokumarss..."` en `eng` — palabras inventadas y distintas entre los dos
idiomas, el patrón de alucinación real.

**Conclusión sobre `d2`:** el acuerdo lo clasifica correctamente como «no alucinado», que es lo
que mide. El CER alto de `d2` es un problema DISTINTO (orden de líneas bajo `--psm 3`), fuera del
alcance de las dos guardas de este encargo y del propio informe original. Se deja **declarado, no
resuelto** — no es una guarda nueva improvisada sin pedirla.

### 1.6 Resultado que decide la regla

**Con las dos guardas puestas, el acuerdo separa `bueno`/`ruido`/`no_aplica` correctamente en
los 8 de 8 documentos** (6 con veredicto bien clasificado contra el CER, con margen de 0,289
entre clases, y 2 correctamente excluidos por la guarda 1 en vez de fabricar un acuerdo). La
única salvedad honesta es `d2` (§1.5): el acuerdo clasifica su ausencia de alucinación bien, pero
un CER del 30 % bajo la etiqueta `bueno` puede leerse como una lectura "falsa" si el criterio de
verdad que se usa es CER-estricto en vez de alucinación-estricta — se declara la evidencia de las
dos lecturas y **no se decide aquí cuál es la correcta**, porque es una decisión de diseño de
`filex/verificador.py`, no de esta medición.

**Propuesta de regla** (no aplicada — `filex/verificador.py` es de quien lo mantenga):

```python
# Sustituto de P9_TOKENS_MIN + P3, para spa/eng fuera de Ghostscript.
GUARDA_ACUERDO_TOKENS_MIN = 8       # mismo patron, P9_TOKENS_MIN
COSTE_SUST_ACENTO = 0.3             # bench/salidas-c46-guardas/_c46_guardas.py
COSTE_SUST_NORMAL = 1.0
UMBRAL_BUENO = 0.80
UMBRAL_RUIDO = 0.70

# veredicto:
#   tok_spa < GUARDA_ACUERDO_TOKENS_MIN o tok_eng < ... -> "no_aplica"
#   acuerdo_ponderado(spa, eng) >= UMBRAL_BUENO           -> "bueno"
#   acuerdo_ponderado(spa, eng) <= UMBRAL_RUIDO            -> "ruido"
#   si no                                                  -> "banda" (no decide)
```

Datos, script y `MANIFIESTO.md` en `bench/salidas-c46-guardas/`.

---

## 2 · `C42` — `test_watcher_n` en `ext4` nativo de WSL2 — **MEDIDO, sigue sin reproducir**

### 2.1 Estado real antes de empezar — más avanzado que lo que describía el encargo

El encargo (redactado citando `bench/ci-y-contrato.md`) da por buenos **tres** intentos previos:
`DrvFs` de este *worktree*, `tmpfs` de `/tmp` en WSL2, `overlay2` de un contenedor Docker — y pide
un cuarto, en `ext4` nativo.

**Ese cuarto intento ya está commiteado en `main`** (`bench/huella-y-runner.md` §2.1, commit
`42f090d`, ancestro de esta rama — verificado con `git merge-base --is-ancestor`): con
`TMPDIR=/home/edicius/ext4-tmp` (ext4 real, confirmado por su autor con `mount`) pero **el código
ejecutándose desde `/mnt/c/...` (DrvFs)** y Python 3.14.4, dio **19/19 en verde (2 saltadas)**.
Sigue sin reproducir. Este dato se declara aquí en vez de repetir el mismo experimento sin
saberlo — la trampa 95 del proyecto (*"antes de creerte un bloqueo, mira si ya está resuelto"*)
aplicada al revés: antes de repetir un trabajo, mira si ya se hizo.

**Lo que ese cuarto intento NO hizo, y es justo lo que este encargo pide explícito**: mover TODO
el repositorio (código + corpus) al sistema de ficheros de WSL2, no solo el `TMPDIR`. Esa es la
diferencia real entre el intento de `huella-y-runner.md` y el de aquí — no es un quinto intento
redundante, es el primero que cierra esa distinción.

### 2.2 Confirmado `ext4` GENUINO por tres vías independientes, antes de correr nada

```
$ wsl.exe -e bash -c 'mount | grep -E " / | /home"'
/dev/sdf on / type ext4 (rw,relatime,discard,errors=remount-ro,data=ordered)

$ wsl.exe -e bash -c 'stat -f -c "%T (%i)" /home/edicius/filex-c42-ext4'
ext2/ext3 (ee3340dacce320d4)

$ wsl.exe -e bash -c 'df -T /home/edicius/filex-c42-ext4'
Filesystem     Type  1K-blocks     Used Available Use% Mounted on
/dev/sdf       ext4 1055762868 13807900 988251496   2% /
```

Las tres coinciden: `ext4` real (`stat -f` reporta la familia `ext2/ext3`, que es como `statfs`
identifica ext2/3/4 — no hay ambigüedad con `mount` y `df -T` diciendo `ext4` explícito al lado).
`/home/edicius` está en el MISMO punto de montaje que `/` (no hay una línea `/home` separada en
`mount`): es la raíz nativa de la instalación de Ubuntu en WSL2, no un `/mnt/c/...`.

### 2.3 Copia real del repositorio dentro de `ext4`, sin `git clone` (evita punteros LFS)

`git clone` habría traído los ficheros de `corpus/` que `test_watcher_n` necesita (`tipico.png`,
`trivial.wav`, `patologico_bom.csv`) como punteros de Git LFS si el remoto de WSL2 no tuviera el
almacén local (trampa 34) — se copiaron los ficheros REALES ya presentes en el *worktree* de
Windows (verificados no-punteros por tamaño: `tipico.png` 42 855 B, no 130 B):

```
$ wsl.exe -e bash -c '
    DEST=/home/edicius/filex-c42-ext4
    cp -r /mnt/c/.../filex-cpu-cierre/filex "$DEST/"
    cp -r /mnt/c/.../filex-cpu-cierre/pruebas "$DEST/"
    cp -r /mnt/c/.../filex-cpu-cierre/bench/salidas-watcher "$DEST/bench/"
    cp /mnt/c/.../corpus/imagen/tipico.png "$DEST/corpus/imagen/"
    cp /mnt/c/.../corpus/audio/trivial.wav "$DEST/corpus/audio/"
    cp /mnt/c/.../corpus/datos/patologico_bom.csv "$DEST/corpus/datos/"
  '
3,0 MiB copiados
```

Solo el subconjunto que `pruebas/test_watcher_n.py` importa (`filex.cerrojo`, `filex.trabajo`,
`filex.watcher` y su cadena de imports, **toda en la biblioteca estándar** — verificado leyendo
los `import`/`from` de `nucleo.py`, `formatos.py`, `servicio.py`, `confinamiento.py`: sin
dependencias de terceros, consistente con `pyproject.toml` — trampa 80). No hizo falta ningún
venv dentro de WSL2: `python3` del sistema (3.14.4) basta.

### 2.4 Hallazgo de método, antes de fiarse del primer resultado: `TMPDIR` por defecto en WSL2 es `tmpfs`, no `ext4`

`pruebas/test_watcher_n.py` crea sus directorios de trabajo con `tempfile.mkdtemp(prefix=...)`
**sin `dir=`** en las clases que importan (`BarridoDeHuerfanos`, `PacienciaDelWatcher`,
`CoherenciaDeclarada`), lo que resuelve a `tempfile.gettempdir()`. Comprobado en esta WSL2:

```
$ wsl.exe -e bash -c 'python3 -c "import tempfile; print(tempfile.gettempdir())"; mount | grep " /tmp "'
/tmp
tmpfs on /tmp type tmpfs (rw,nosuid,nodev,nr_inodes=1048576)
```

Una primera corrida SIN fijar `TMPDIR` habría probado el watcher sobre `tmpfs`, no sobre `ext4`
— exactamente el sistema de ficheros que el segundo intento (ronda anterior) ya descartó. Se
corrigió ANTES de reportar nada: `export TMPDIR=/home/edicius/filex-c42-ext4-tmp` (mismo punto de
montaje `ext4`, verificado con `stat -f` sobre esa ruta exacta antes de usarla).

### 2.5 MEDIDO: tres corridas limpias, código y `TMPDIR` los dos en `ext4` real — sigue sin reproducir

```
$ wsl.exe -e bash -c '
    cd /home/edicius/filex-c42-ext4
    export TMPDIR=/home/edicius/filex-c42-ext4-tmp
    python3 -m unittest pruebas.test_watcher_n -v
  '
Ran 19 tests in 0,111s / 0,328s / 0,094s / 0,107s (cuatro corridas)
OK (skipped=2)          — las cuatro veces
```

**19/19 en verde, 2 saltadas por el motivo correcto** (`no hay wsl.exe: no se puede medir POSIX`
— dentro de WSL2 no hay `wsl.exe` que invocar; `el primitivo de Windows solo existe allí` —
`os.replace(p,p)` de Windows no aplica en Linux), verificado leyendo el mensaje de cada
`skipTest`, no solo el recuento (trampa 38: registrar que la condición se dio, no solo el
resultado). Repetido cuatro veces (una con `-v` completo, tres de control) — **cero fallos, cero
intermitencia**, sobre el sistema de ficheros MÁS estricto de los cinco entornos probados hasta
ahora: código, corpus y directorios temporales, los tres en `ext4` genuino.

### 2.6 Balance de los cinco intentos — la hipótesis del sistema de ficheros pierde apoyo otra vez

| # | Entorno | Código en | `TMPDIR`/temporales en | Resultado |
|---|---|---|---|---|
| 1 | `DrvFs` de este *worktree* | DrvFs | DrvFs | sin reproducir |
| 2 | `tmpfs` de `/tmp` en WSL2 | (no declarado en el informe original) | `tmpfs` | sin reproducir |
| 3 | `overlay2` de un contenedor Docker | overlay2 | overlay2 | sin reproducir |
| 4 | `ext4` (`bench/huella-y-runner.md` §2.1) | **DrvFs** | `ext4` (`TMPDIR` fijado) | sin reproducir |
| 5 | `ext4` (aquí) | **ext4** | `ext4` (`TMPDIR` fijado, verificado) | sin reproducir |

**Cinco entornos, cinco resultados limpios, cero reproducciones.** El intento 5 es el único que
pone TODO —código, corpus y temporales— sobre el mismo `ext4` genuino a la vez, y tampoco
reproduce. La hipótesis de trabajo original (*"la estabilidad se comporta distinto en `ext4`"*)
queda, con este quinto dato, más débil de lo que ya estaba tras el cuarto: no es una diferencia de
DÓNDE vive el código frente a dónde vive el temporal, ni de si el sistema de ficheros del código
es DrvFs o `ext4` — con las dos variables controladas y en `ext4` real, el fallo sigue sin
aparecer.

**Lo que queda sin descartar, exactamente como dejó declarado el intento 4, y ninguno de los cinco
lo cubre**: `glibc`/kernel de `ubuntu-latest`, las opciones de montaje concretas del runner, el
propio **Python 3.11.16** (los intentos 4 y 5 corrieron con 3.14.4 — no hay `python3.11` instalado
en esta WSL2 compartida, y no se instaló nada, por la misma razón que el intento 4 declaró: no es
un entorno propio de esta rama, y el proyecto pide no instalar donde no hace falta), o
contención/paralelismo específico del runner de GitHub Actions.

### 2.7 Decisión: se mantiene declarado, no forzado

**No se escribe ningún `skipUnless` nuevo** ni se toca `ci/linux-apto.json` (instrucción explícita
del encargo). No se ha visto el fallo con los propios ojos en ningún entorno — la regla del
proyecto (trampa 44, y la disciplina que los cuatro intentos anteriores ya se impusieron) sigue
siendo la correcta: sin verlo, no hay nada que blindar honestamente.

**Limpieza:** la copia de trabajo (`/home/edicius/filex-c42-ext4`, `/home/edicius/filex-c42-ext4-tmp`)
se borró al terminar — no forma parte del entregable, es una copia efímera para el experimento
(no se tocó `/home/edicius/ext4-tmp`, que es del intento anterior y no es mío).

---

## 3 · Verificación de este PR

- **MEDIDO — suite integral**, `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe -m pytest pruebas/ -q`:
  **460 passed, 3 skipped, 130 subtests passed, 0 failed**, en 256,59 s. Una sola corrida —limpia
  al primer intento, sin necesidad de una segunda para descartar ruido de máquina (regla del
  proyecto: la segunda corrida es para DESAMBIGUAR un rojo, no un trámite fijo).
- **Intérprete:** `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe` = **3.11.9**, el
  mismo que sella `filex/sondeo/*.json` (no se tocó ningún fichero de sondeo ni de huella en esta
  rama). El **3.14.4** del §2 es un entorno de WSL2 completamente aparte, sin relación con el
  sellado ni con la suite de Windows.
- **Entorno:** Windows 10, *worktree* en `C:\`. Docker Desktop **UP** durante toda la tanda
  (`docker info` antes de `C46`; sin contenedores huérfanos después — cada `docker run` de
  `_c46_guardas.py` lleva `--rm`, y no se lanzó ninguno sin `--rm`/`--init`). WSL2 se usó
  únicamente para `C42` (§2), en un proceso aislado que no toca la suite de Windows ni el sondeo.
  Corpus **LFS descargado** (no punteros): verificado por tamaño antes de copiar nada a WSL2.
- **Qué quedó fuera y por qué:** la anomalía de `escaneado_d2` en `C46` (§1.5, CER alto con
  acuerdo `bueno` — no es uno de los dos mecanismos de este encargo, declarada y no forzada a una
  tercera guarda); el `--psm` de Tesseract 5.5.0 dentro de `filex-c13` (no se barrió, mismo motivo
  que la ronda 7: mezclaría dos preguntas — trampa 78); en `C42`, Python 3.11 dentro de WSL2 (no
  hay binario instalado en esta WSL2 compartida y no se instaló nada) y el propio runner de GitHub
  (fuera del alcance de esta máquina).
- **Estado de la máquina:** sin contención visible durante la tanda — la suite corrió limpia a la
  primera, sin el patrón de fallos por contención que otras rondas declaran (trampa 101). Docker y
  WSL2 activos simultáneamente sin degradar los tiempos de Tesseract de forma anómala (1,0-3,5 s
  por pasada, consistente con las cifras de la ronda 7).
- **`ci/integridad.py`:** `PYTHONIOENCODING=utf-8 ...\python.exe ci/integridad.py` → **9/9 en
  verde** (`Todo en orden.`) en el momento de ejecutarlo, **antes de escribir este informe y su
  `MANIFIESTO.md`**. Una vez añadidos `bench/cierre-watcher-y-acuerdo.md` y
  `bench/salidas-c46-guardas/` (con su `MANIFIESTO.md`), la comprobación `informes-registrados`
  de ese script exige que el nombre de este fichero aparezca citado en `ESTADO-Y-REPARTO.md` —
  y **"Nadie escribe en los maestros salvo el agente de consolidación"** (`ESTADO-Y-REPARTO.md`
  §4, "Contención, en una frase"), regla que este worktree no tiene autorización para saltarse.
  **Se declara así, sin forzarlo**: es de esperar que `ci/integridad.py` marque
  `informes-registrados` en rojo hasta que la consolidación registre esta entrega, tal como le
  pasó a `bench/huella-y-runner.md` en el commit `42f090d` de worker2 (citado en §2.1) antes de
  que el maestro lo verificara.

## 4. Entrega

`worker9`, carril CPU/Docker nuevo. Commit en `edicius2002/filex-cpu-cierre`. No se empuja ni se
abre PR — lo hace el maestro.

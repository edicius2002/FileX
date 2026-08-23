# El lock de GPU deja de mentir — y por qué un lock, solo, no bastaba

**Agente L1 · 23 de agosto de 2026 · máquina de siempre (RTX 3060 12 288 MiB, Windows 10 Home 19045, Git Bash)**
**Encargo C26** de `ESTADO-Y-REPARTO.md` §3.C, abierto por `bench/ppp-y-normalizacion.md` §1.3, **más el barrido de veracidad del inventario.**
**Ficheros tocados:** `bench/lib/harness.sh` (+232 / −13), `bench/lib/censo_gpu.ps1` (nuevo, 50 líneas), `ESTADO-Y-REPARTO.md`, y este informe.
**Salidas y logs:** `bench/salidas-lock/`.
**No se lanzó una sola carga en la GPU:** `nvidia-smi` solo se leyó. Las pruebas de lock usan `sleep` y `ffprobe -version`. G4 estaba midiendo OCR.

---

## 0. Lo que hay que saber, en cuatro líneas

1. **El enunciado de C26 estaba incompleto, y esa es la conclusión principal.** Mover el lock a `%TEMP%` **no cierra el caso que lo motivó**: la sesión de `D:\Work\research\ASR` **no iba a tomar ese fichero jamás**, esté donde esté. Un lock **excluye a quien coopera**; al que no coopera **solo lo ve quien mira la tarjeta**. Por eso el arreglo tiene **dos mitades** y la segunda es la que vale.
2. **La línea base de esta máquina es 3 292 / 3 356 / 3 448 MiB ocupados** (mín / mediana / máx, **n=90 muestras a 1 s**), no los ~2,5 GB que dice `CLAUDE.md` §2 — **MEDIDO**. El caso de ASR dejaba **534 MiB libres**. Entre los dos regímenes hay un orden de magnitud, así que el umbral no es delicado: **se aborta por debajo de 6 000 MiB libres**.
3. **El lock huérfano existía y está reproducido.** `taskkill /F` **no ejecuta el `trap`**: el fichero sobrevive y el siguiente agente esperaba **900 s** para abortar. Ahora el lock lleva dentro el **PID de Windows** y el **nombre de imagen** de su dueño, y la recuperación es de **1 s** — MEDIDO las dos cifras.
4. **Y un límite de la máquina que refuta media frase de `CLAUDE.md`:** *«mira los PID antes de culpar al arnés»* **no se puede automatizar del todo aquí**. En WDDM `nvidia-smi --query-compute-apps=used_memory` devuelve **`[N/A]` en los 30 procesos** y `nvidia-smi pmon` responde *«The feature is not supported in this configuration»*. **La VRAM por PID no es observable.** El censo que se ha añadido da **una lista de sospechosos ordenada**, nunca al culpable.

---

## 1. Qué hacía el lock viejo

`bench/lib/harness.sh` línea 7, tal cual estaba:

```sh
GPU_LOCK="${GPU_LOCK:-D:/Work/research/FileX/bench/.gpu.lock}"
```

y la exclusión, un `noclobber` con un `trap`:

```sh
while ! (set -o noclobber; echo "$who $$" > "$GPU_LOCK") 2>/dev/null; do
  sleep 5; waited=$((waited+5))
  if [ $waited -ge 900 ]; then ... return 1; fi
done
trap 'gpu_release' EXIT INT TERM
```

**Lo usan 47 ficheros** (`bench/salidas-corpus-d4/*.sh`, `salidas-k-motor/*.sh`, `salidas-ocr-ppp/*.sh`, `salidas-ppp-norm/*.sh`, `salidas-phys-multi/*.sh`, `bench/scripts/*.sh`…), así que cualquier cambio es en código compartido.

Tenía **tres** defectos, y los tres están medidos abajo.

### 1.1 Defecto 1 — el lock es de repositorio (el que motivó C26)

Ya estaba medido en `ppp-y-normalizacion.md` §1.3: una sesión de Claude en `D:\Work\research\ASR` ocupando **11 754 de 12 288 MiB** dejó una tanda de FileX **12 minutos sin procesar una sola imagen**, con el lock de FileX **libre y correctamente adquirido**.

### 1.2 Defecto 2 — el lock huérfano · **MEDIDO** (`bench/salidas-lock/prueba_huerfano_viejo.log`)

Reproducido con el harness viejo copiado a `bench/salidas-lock/harness_viejo.sh`:

```
== 1. arranco un tomador del lock (harness VIEJO) ==
[lock] adquirido por victima
-- contenido del lock: victima 45483
-- winpid de la victima: 11656
== 2. lo mato con taskkill /F /T ==
CORRECTO: el proceso con PID 11656 ... ha sido terminado.
== 3. estado del lock DESPUES ==
HUERFANO CONFIRMADO: el fichero sigue ahi -> victima 45483
== 4. cuanto espera el siguiente agente ==
[bloqueado] GPU en uso por: victima 45483
```

Y hay un detalle que **hace inútil el PID que el lock guardaba**: `$$` en Git Bash es el **PID de msys (45483)**, no el de Windows (**11656**). Quien encontrara el fichero no podía comprobar nada con `tasklist`, porque el número que había dentro no es el que `tasklist` conoce. **Guardar un PID que no sirve para preguntar por él es lo mismo que no guardarlo.**

### 1.3 Defecto 3 — `peak_vram` escribía en un fichero de nombre fijo

```sh
) > /tmp/_vram_samples.txt &
```

`/tmp` en este Git Bash **es `%TEMP%`** (§2.1), o sea **compartido por toda la máquina**: dos `peak_vram` a la vez —dos agentes, o dos worktrees— se pisaban las muestras. Nadie lo había notado porque `peak_vram` va dentro del lock; pero el lock era de repositorio, así que la protección era exactamente la que este informe viene a arreglar.

---

## 2. La línea base de esta máquina · **MEDIDO**

### 2.1 Dónde vive `%TEMP%` desde Git Bash

```
TEMP  = C:\Users\krato\AppData\Local\Temp
cd /tmp && pwd -W  ->  C:/Users/krato/AppData/Local/Temp
```

**`/tmp` es `%TEMP%`.** Se usa `/tmp` y no `$TEMP` porque `$TEMP` viene en forma Windows con `\`, y una ruta con backslashes en una redirección de bash es una trampa gratuita (es la trampa 19 con otra cara).

### 2.2 VRAM en reposo — 90 muestras a 1 s (`bench/salidas-lock/vram-linea-base.log`)

Escritorio normal de esta máquina: **sesión de escritorio remoto activa** (estructural, no se cierra), Chrome, Discord, Spotify, Wallpaper Engine, Steam, Epic, Notion, Slack, WhatsApp, Docker Desktop, iCUE, dos ventanas de la app de Claude.

| Magnitud | mín | mediana | p90 | máx |
|---|---|---|---|---|
| **VRAM ocupada (MiB)** | 3 292 | 3 356 | 3 397 | **3 448** |
| **VRAM libre (MiB)** | 8 996 | 8 932 | 8 891 | **8 840** |
| **Utilización (%)** | 14 | 21 | 45 | **57** |

**Dos correcciones que salen de aquí:**

- **`CLAUDE.md` §2 dice «el escritorio ocupa ~2,5 GB de forma permanente». Hoy son 3,3 GB.** No es un error de nadie: es que la línea base **depende de qué haya abierto**, y por eso el umbral **no puede ser una constante escrita a mano en el arnés** sin declarar cuándo se midió. Va como variable de entorno con su valor por defecto justificado.
- **El testigo de utilización que ya existía (`gpu_quiet_check`, umbral «< 10 % sostenido») marca `SUCIA` SIEMPRE en esta máquina**, porque el reposo va de 14 a 57 %. Es coherente con lo que el proyecto ya sabía (*«con la sesión remota todo sale SUCIA, es estructural»*), pero tiene una consecuencia práctica: **una señal que vale 1 siempre no separa nada.** La ocupación de VRAM sí separa el escritorio (3,3 GB) del intruso (11,8 GB); la utilización no.

### 2.3 El límite duro: **la VRAM por PID no es observable en esta máquina**

```
$ nvidia-smi --query-compute-apps=pid,used_memory --format=csv
pid, used_gpu_memory [MiB]
1584, [N/A]
7500, [N/A]
...   (30 procesos, TODOS [N/A])

$ nvidia-smi pmon -c 1
The feature is not supported in this configuration
Not supported on the device(s)
```

Es el comportamiento conocido de **WDDM** (la GPU la gestiona el sistema, no el driver en modo TCC). **Consecuencia de diseño, no un detalle:** ninguna automatización de *«mira los PID»* puede decir **quién** se ha comido la VRAM en esta máquina. Lo máximo que se puede hacer es **listar candidatos con su línea de órdenes**, que sí dice de qué repositorio vienen:

```
30208  python.exe  D:\Work\research\edicius-hq\services\api\.venv\Scripts\python.exe -m uvicorn ...
34120  node.exe    "node" "D:\Work\research\edicius-hq\node_modules\.bin\..\vite\bin\vite.js"
```

Eso es `bench/lib/censo_gpu.ps1`. **Es una lista de sospechosos, y se declara como tal en el propio texto que imprime.**

---

## 3. Qué hace el lock nuevo

### 3.1 Mitad 1 — exclusión

| Antes | Ahora |
|---|---|
| `bench/.gpu.lock` (dentro del repositorio) | **`/tmp/filex-gpu.lock` = `%TEMP%`**, el mismo fichero para cualquier copia o *worktree* de FileX de este usuario |
| Contenido: `etiqueta pid_msys` | `etiqueta<TAB>pid_msys<TAB>**winpid**<TAB>**imagen**<TAB>epoch<TAB>cwd` |
| Un dueño muerto dejaba el fichero para siempre | Quien lo encuentra **comprueba si el dueño vive** y lo recupera |
| `gpu_release` borraba el fichero fuera cual fuera | **Solo lo borra si es suyo** (compara el pid), para no quitárselo a quien se lo haya recuperado |

**Cómo se comprueba si el dueño vive, y por qué así.** `tasklist /FI "PID eq <winpid>"` **y además el nombre de imagen**. Lo segundo no es paranoia decorativa: `CLAUDE.md` §3 ya avisa de que *«un PID vivo no siempre es el que crees»* (los tres `soffice` que sobrevivieron 37 minutos a un `taskkill /F /T`), y en Windows los PID se reutilizan. Si el PID existe pero pertenece a `chrome.exe`, **no es el dueño del lock**: es un número reciclado.

**La carrera al recuperar** se cierra con un `mkdir "$GPU_LOCK.robo"`, que es atómico también en Windows: solo uno de los que esperan borra el fichero huérfano.

**El lock de LEGADO.** Cambiar de sitio el lock **abre durante la transición justo el agujero que el cambio viene a cerrar**: una tanda arrancada antes con el harness viejo sigue tomando `bench/.gpu.lock` y no vería el nuevo. Así que `gpu_acquire` mira **también** el fichero antiguo: si su dueño vive, espera; si es huérfano, lo borra y sigue. Es una veintena de líneas y desaparece sola cuando no queden tandas viejas.

### 3.2 Mitad 2 — detección (la que cierra el caso de ASR)

Después de tomar el lock —momento en el que cualquiera que quede ocupando la tarjeta **es, por definición, alguien que no coopera**— `gpu_acquire` mira la VRAM libre:

| VRAM libre | Qué hace | Por qué ese número |
|---|---|---|
| **≥ 7 500 MiB** | mide normal | El suelo observado del escritorio es **8 840** libres; 7 500 queda **1 340 MiB por debajo**, que son **8,6× el recorrido propio del escritorio** (156 MiB). No lo dispara el escritorio |
| **6 000 – 7 500** | mide y **marca la tanda `SUCIA(vram_libre …)`**, e imprime el censo | Banda de duda: cabe una tanda pequeña, pero el número no es comparable |
| **< 6 000 MiB** | **se niega a medir** (`rc=2`), suelta el lock e imprime el censo | Por encima del coste propio del motor más caro medido (**EasyOCR +4 430 MiB**, `ocr-ppp-nativos.md` §7.2) y **muy** por encima de los **534 MiB** que dejaba el caso de ASR |

**La decisión, y por qué abortar y no medir:** el modo de fallo documentado **no es «un número algo peor»**. Es (a) **una tanda entera sin resultado** —12 minutos sin procesar una imagen— o (b), peor, **un número malo etiquetado `limpia`**, que es exactamente lo que ya pasó tres veces en un día con los testigos de ruido (V1 ×6,8 «limpia», P1 deriva 0,83 con el testigo de proceso a ×7,18, P3 ×94,6). **Negarse cuesta cero y es reversible; medir con la tarjeta ajena cuesta la tanda y, si nadie lo nota, contamina un informe.** Por eso el defecto es `GPU_GUARD=abortar`, con tres salidas explícitas para quien sepa lo que hace: `avisar` (mide y marca `SUCIA`), `esperar` (sondea hasta `GPU_GUARD_ESPERA_MAX`, 900 s) e `ignorar`.

### 3.3 Superficie nueva, entera

```
GPU_LOCK              /tmp/filex-gpu.lock     (sobrescribible, como antes)
GPU_LOCK_DIR          /tmp
GPU_LOCK_LEGADO       D:/Work/research/FileX/bench/.gpu.lock
GPU_LIBRE_AVISO_MIB   7500
GPU_LIBRE_MIN_MIB     6000
GPU_GUARD             abortar | avisar | esperar | ignorar
GPU_GUARD_ESPERA_MAX  900
GPU_MARCA_PROPIA      FileX      (lo que distingue un proceso propio de uno ajeno)
GPU_PS                ruta absoluta a powershell.exe

funciones nuevas:  gpu_libre_mib · gpu_ocupacion_ajena · gpu_censo_ajeno
funciones intactas en nombre, firma y contrato:
                   gpu_acquire · gpu_release · measure · peak_vram
                   gpu_state · gpu_quiet_check
```

---

## 4. Las pruebas · **MEDIDO** (`bench/salidas-lock/prueba_harness_nuevo.log`, `prueba_legado.log`, `compat-run_a_png.log`)

| # | Qué prueba | Resultado |
|---|---|---|
| **P0** | Sintaxis y que las 6 funciones siguen existiendo | `bash -n` OK · **6 de 6 presentes** |
| **P1** | `GPU_LOCK` sigue siendo sobrescribible por entorno | **OK** |
| **P2** | Ciclo adquirir / liberar | OK; contenido `prueba-P2|46130|39540|bash|1787490226|…` |
| **P3** | **Lock huérfano**: `taskkill /F` al dueño y adquisición del siguiente | *«HUERFANO detectado (dueño 'victima-P3' pid 34668 muerto): lo libero»* → **adquirido en 1 s**. El viejo esperaba **900** |
| **P4** | Lock con dueño **vivo** | **20 s esperando sin robarlo.** No hay falsos positivos de huérfano |
| **P5** | Detección con la tarjeta despejada (8 816 MiB libres) | Arranca |
| **P6** | Detección con la tarjeta ocupada *(simulada subiendo el umbral, sin tocar la GPU)* | **`rc=2`, censo impreso, y suelta el lock al abortar** |
| **P7** | `GPU_GUARD=avisar` | Mide igualmente y avisa |
| **P8** | `measure` sigue funcionando y marca por VRAM | `[SUCIA(pico 47%)]` en un caso y `[SUCIA(vram_libre 8796MiB)]` en el otro. **Formato de línea intacto** |
| **P9** | `peak_vram` con fichero de muestras por PID | `pico_vram_total_MiB=3322 rc=0`, sin residuos |
| **P10** | Censo de ajenos | 22 procesos, ordenados por RAM residente, el mayor **169 MB** — o sea **ninguno con CUDA cargado**, coherente con los 3 355 MiB de línea base |
| **P11** | Lock de **legado** con dueño vivo | Espera sin adquirir |
| **P12** | Lock de **legado** huérfano | Lo borra, avisa y sigue |

### 4.1 La prueba de compatibilidad que importa: **un script real, sin modificar**

No basta con probar el arnés contra sí mismo. Se ejecutó **`bench/salidas-k-motor/run_a_png.sh` tal cual está en el repositorio**, con `GPU_LIBRE_MIN_MIB=20000` para que la detección se dispare y el script salga por su propio `|| exit 1` **antes de tocar la tarjeta** (G4 estaba midiendo):

```
[gpu] OCUPADA por terceros: 8736 MiB libres < 20000 de mínimo
[gpu] censo de procesos ajenos (no se puede atribuir VRAM por PID en WDDM):
CENSO_AJENOS 26 (ordenados por RAM residente; …)
...
[gpu] ABORTO: la tarjeta está ocupada por un tercero. …
rc=1                      <- el `|| exit 1` del propio script
--- lock residual? --- No such file or directory
```

**Un script de 2026-08-22 escrito contra el harness viejo carga el nuevo, llega a `gpu_acquire`, obtiene el código de retorno que espera, sale limpio y no deja lock.** Es la evidencia de compatibilidad, no una suposición.

**Lo que NO se ha probado y se declara:** el camino **positivo completo** de un script real —adquirir y medir de verdad sobre la GPU— **no se ha ejecutado**, porque el encargo prohibía usar la tarjeta y había un agente (G4) midiendo. Está probado por partes (P2, P5, P8 con `ffprobe`), no de extremo a extremo con carga CUDA. **PENDIENTE de la primera tanda real que alguien lance.**

---

## 5. Qué NO resuelve esto — sin adornos

1. **Un lock no obliga a cooperar a quien no lo toma.** Es la mitad del enunciado de C26 que era falsa, y conviene que quede escrita: **mover el fichero a `%TEMP%` no habría evitado el caso de ASR.** Lo que lo evita es **negarse a medir**, y eso **no libera la tarjeta**: el intruso sigue ahí. El arnés pasa de *«mide mal y no te enteras»* a *«no mide y te dice por qué»*. Es una mejora de honestidad, no de disponibilidad.
2. **`%TEMP%` es POR USUARIO, no por máquina.** Dos usuarios de Windows distintos tendrían dos locks. Para *este* proyecto es irrelevante (todos los agentes corren como `krato`), pero un **mutex con nombre** de Windows sería el mecanismo correcto y **no se puede tomar desde shell** sin añadir una dependencia. **PENDIENTE, declarado.**
3. **No cruza a la VM de WSL2.** El `/tmp` de Ubuntu es otro sistema de ficheros. Un contenedor que use la GPU no ve este lock — hoy no hay ninguno, pero el hito 5 metió Docker en el camino.
4. **La detección es un instante, no una vigilancia.** Se mira al adquirir; si el intruso llega **a mitad** de una tanda de 40 minutos, la marca `SUCIA` de `measure` lo cogerá en la siguiente llamada, pero las medidas ya hechas no se reetiquetan hacia atrás.
5. **El censo nombra sospechosos, no culpables** (§2.3). Con 22–26 procesos candidatos y sin VRAM por PID, **lo ordena por RAM residente y ya está**. Si alguien quiere el culpable de verdad, hace falta otra vía (NVML en modo elevado, o el propio `nvidia-smi` con la GPU en TCC, que en una máquina de escritorio con monitor conectado no es una opción).
6. **El umbral es de esta máquina y de este día.** 6 000 MiB sale de una línea base de 3,3 GB. Si el usuario abre un juego, el escritorio se come 6 GB y el arnés se negará a medir **con razón** — pero alguien leerá el mensaje como un fallo del arnés. Por eso el mensaje dice el número que ha visto.
7. **El lock solo existe en shell.** Ver §6.

---

## 6. El agujero de Python, declarado aunque no se arregle

**MEDIDO por censo del árbol:**

- **Ningún `.py` del repositorio llama a `gpu_acquire` ni menciona `GPU_LOCK`**: 0 resultados.
- **15 ficheros `.py` invocan `nvidia-smi`** (los `ocr_lote_*.py`, `docling_lote_*.py`, `survey_norm.py`, `ocr_motor.py`, `whisper_precision.py`, `gpuwatch.py`…), es decir, **miden GPU**.
- La mayoría se salva porque **los lanza un `.sh` que sí toma el lock**. **Dos no:** `bench/scripts/whisper_precision.py` y `bench/scripts/gpuwatch.py` **no aparecen invocados desde ningún `.sh`** — solo desde `gpu-fase1.md` y `gpu-fase2.md`, o sea a mano.

**Es un agujero real**: cualquier agente que lance uno de esos dos, o que escriba un arné nuevo en Python, **usa la GPU sin lock y sin detección**, y el resto de agentes no se entera. **No lo arreglo aquí** porque tocar 15 arneses ajenos contradice *«un fichero por agente»*, pero queda como fila **C38** del inventario. La forma barata sería un `filex/…` o un `bench/lib/gpu_lock.py` que replique las mismas cuatro operaciones sobre **el mismo fichero** de `%TEMP%` — el formato del lock ya está pensado para eso (campos separados por tabulador, PID de Windows dentro).

Y el mismo problema, una capa más arriba: **`filex/` no tiene lock de GPU en absoluto** (`hito7-superficies.md` §5.4: las apariciones de `nvenc`/`cuda` en el paquete **son tres comentarios**) → fila **N7**.

---

## 7. El barrido del inventario — recuento y **dirección** del error

`ESTADO-Y-REPARTO.md` tenía **1 009 líneas** y **63 filas de pendientes**. Estaba fechado el 22/08 y **su tabla de informes se cortaba el 21/08 a las 14:00**.

### 7.1 Lo que estaba mal, por dirección

| Dirección | Filas | Cuáles | Qué le hacía al proyecto |
|---|---|---|---|
| **Decía ABIERTO lo que estaba CERRADO** | **8** | `B12`, `B15`, las **cinco** filas históricas duplicadas (`B17`, `B18`×2, `B19`, `B14`) que llevaban `🔴 NUEVO` aunque su sustituta las cerraba tres filas más arriba, y **`M1 · Cabos MCP`** en la §4 | **El proyecto se creía más atrasado de lo que está.** Y no es inocuo: `B15` figuraba como pendiente **cuando ya había destapado un fallo aritmético de un año en la regla de ppp** |
| **No registraba trabajo que ya existía** | **15 informes sin una sola cita**, que abren **24 filas nuevas** | Los cuatro hitos (`hito3-mudanza`, `hito4-mcp`, `hito5-documental`, `hito7-superficies`), los tres sondeos (`sondeo-imagemagick/-ffmpeg/-documental`), `consolidacion-4-22ago`, y siete anteriores al inventario | **El proyecto se creía más adelantado.** La construcción entera del paquete `filex/` —cuatro superficies, 129 pruebas— **y toda su deuda** no figuraban. Es la §3.N nueva |
| **Enunciado falso o desfasado** | **8** | `C31` (**las dos cifras eran falsas**), `C24` (no era el envoltorio, era el `--psm`), `B11` (redefinido por segunda vez), `B16` (hay un segundo acantilado), `A7` (ya decidido de hecho por cuatro informes), `C16` (comparte corpus con C28), `C5` (el vector ya está identificado), `G2` en la §4 | **Es la peor de las tres**: una fila que existe y dice algo falso **dirige trabajo hacia un problema que ya no es el que hay**. `C31` mandaba a arreglar un `read()` cuando el culpable es `d["csv_filas"]`, y llamaba «colisión sin falso positivo» a **un falso positivo vivo** |
| **Ilegible a máquina** | **21 de 63 filas** | Las que usaban `✅` en la celda de estado en vez de un emoji de color, más los `🔴` dentro de texto tachado | Un `grep` daba **32 rojos** y ese número **no significaba nada** |

### 7.2 Dos correcciones a lo que se me dijo — **refutaciones, y por eso van escritas**

- **«`G2 · Motores restantes` dice sin lanzar. Se lanzó.»** **A medias, y la mitad que falla es la importante.** Un agente **con la etiqueta G2** sí corrió el 22/08 — pero hizo **B17+B18+B14** y escribió `bench/psm-y-rasterizador.md`. **El encargo B3+B4+B5 no se hizo**: `bench/motores-restantes.md` **no existe en todo el árbol**, `bench/salidas-marker/` solo tiene un `logs/` vacío y marker, surya y MinerU **no tienen una sola medida**. La fila **se queda 🔴**, con la aclaración. *(Lo mismo con «M1», que nombra a **dos** agentes distintos: `mcp-cabos-2.md` el 21/08 y `k-por-motor.md` el 22/08. **Las etiquetas de agente se están reutilizando y eso ya ha producido una lectura errónea.**)*
- **«El fichero se contradice a sí mismo» — confirmado, con el sitio exacto.** `M1 · Cabos MCP` decía `🔴 sin lanzar` en la §4 mientras `C4` decía *«CERRADO el 22/08 por M1 (`bench/mcp-cabos-2.md`)»* y `C5` *«mitad cerrada»* en la §3. **Corregido.**

### 7.3 Cómo queda

**87 filas, 87 emojis, uno por fila y en la última columna.** Verificado a máquina:

```sh
awk '/^## 3\. Inventario/{f=1} /^## 4\. El reparto/{f=0} f' ESTADO-Y-REPARTO.md \
  | grep -E '^\| (~~)?\*\*[ABCN][0-9]+'                                          \
  | grep -o '🔴\|🟡\|🟢\|⚫' | sort | uniq -c
      5 ⚫      44 🔴      6 🟡      32 🟢
```

*(El segundo filtro no es decorativo: sin él **la propia leyenda se cuenta a sí misma** y salen 47/8/35/7. Comprobado.)*

**Filas nuevas: 24.** `A9` · `B20`–`B26` · `C32`–`C38` · **la sección `N` entera (`N1`–`N9`), que es la deuda del paquete `filex/` y no tenía dónde vivir.** Ahí están las tres cosas que el encargo pedía añadir explícitamente: **el cerrojo de destino de proceso (N1)**, **las tres trampas propuestas y sin aplicar (N8)** y **las dos deudas de `filex/sondeo.py` (N2 y N3)**.

Se corrigieron además **dos bloques del §5 «contexto compartido»**, que es el que se pega en los prompts de los agentes nuevos y por tanto **propaga los errores**: la fórmula de ppp (llevaba la forma con el fallo aritmético) y el bloque del lock de GPU.

---

## 8. Propuesta para `CLAUDE.md` — **no aplicada**, va AL FINAL

`hito7-superficies.md` §10 ya dejó propuestas las trampas **26, 27 y 28**, sin aplicar. Esta sería la **29**, y **depende de que las otras tres entren primero o se renumere**; se deja el texto y no se toca el fichero.

> **29. La VRAM POR PID no es observable en esta máquina, así que «mira los PID» no se puede automatizar — MEDIDO** (`bench/lock-de-maquina.md` §2.3). En WDDM, `nvidia-smi --query-compute-apps=used_memory` devuelve **`[N/A]` en los 30 procesos** y `nvidia-smi pmon` responde *«The feature is not supported in this configuration»*. Lo único atribuible es la **línea de órdenes**, que sí dice de qué repositorio viene el proceso: un censo por `Get-CimInstance Win32_Process` da **sospechosos ordenados**, nunca al culpable. Y por el otro lado: **el total sí sirve**, porque los dos regímenes están a un orden de magnitud —**escritorio 3 292-3 448 MiB ocupados (n=90); el intruso de ASR dejaba 534 MiB libres**—. **Decide por VRAM LIBRE TOTAL, no por PID.** Y **la utilización no vale para esto**: en reposo va del 14 al 57 %, así que el testigo de «< 10 %» marca `SUCIA` siempre y no separa nada.

---

## 9. Lo que abre este informe

| # | Pendiente | Dónde queda |
|---|---|---|
| 1 | **Un lock de máquina de verdad**: mutex con nombre de Windows, o un fichero fuera de `%TEMP%` que cruce usuarios. Hoy es **por usuario** | §5 punto 2 |
| 2 | **El lock en Python** — 0 de 15 arneses lo toman; dos (`whisper_precision.py`, `gpuwatch.py`) **no los lanza ningún `.sh`** | **C38** |
| 3 | **El lock en `filex/`** — no existe, y **N1** (el cerrojo de destino, también de proceso) es el mismo problema con otro recurso. **Cerrarlos con el mismo mecanismo** | **N1**, **N7** |
| 4 | **Verificar el camino positivo de extremo a extremo** con carga CUDA real en la primera tanda que se lance | §4.1 |
| 5 | **Calibrar el umbral en otra máquina**, o hacerlo automático: hoy los 6 000 MiB salen de una línea base de un día. Una opción medible: que `gpu_acquire` muestree la línea base cuando el lock lleve mucho libre y la guarde | §5 punto 6 |
| 6 | **Retirar el bloque del lock de legado** cuando no queden tandas arrancadas con el harness viejo | §3.1 |

---

## 10. Ficheros

| Fichero | Qué es |
|---|---|
| `bench/lib/harness.sh` | El arnés, **298 líneas** (+232 / −13). `sha256` empieza por `dd30e181` |
| `bench/lib/censo_gpu.ps1` | El censo de procesos ajenos, 50 líneas. `sha256` empieza por `7788c0f9` |
| `bench/salidas-lock/vram-linea-base.log` | Las 90 muestras de la línea base |
| `bench/salidas-lock/prueba_huerfano_viejo.sh` / `.log` | Reproducción del huérfano con el harness **viejo** |
| `bench/salidas-lock/harness_viejo.sh` | Copia del harness previo, para poder reproducir |
| `bench/salidas-lock/prueba_harness_nuevo.sh` / `.log` | P0–P10 |
| `bench/salidas-lock/prueba_legado.sh` / `.log` | P11–P12 |
| `bench/salidas-lock/compat-run_a_png.log` | La prueba de compatibilidad con un script real sin modificar |
| `bench/salidas-lock/censo-ajeno.log` | Salida del censo ordenado |
| `bench/salidas-lock/ESTADO-antes-sed.bak` | Copia de seguridad del inventario antes de la pasada automática |

**Ninguna salida binaria.** Todo son `.md`, `.sh`, `.ps1` y logs de texto.

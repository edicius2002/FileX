# B3 — `marker` con el lock de GPU tomado

**Carril `gpu/`, ronda 14, worker1.** Rama `gpu/marker-con-lock`.
Arnés y salidas en [`bench/salidas-marker-lock/`](salidas-marker-lock/).

**Qué se pedía:** la medida de `B3` pendiente desde el 19/08 —tiempo, VRAM pico y CER de `marker`
sobre `corpus/pdf/tipico_texto.pdf`—, por el **camino (a)** que
[`bench/suelo-y-mcp.md`](suelo-y-mcp.md) §3.3 dejó escrito y no probó: *tomar el lock de GPU y
dejar que `marker` use la tarjeta*.

**Qué sale:** **`B3` se cierra por BLOQUEO, con la causa raíz medida y con la traza del sujeto
delante** — y la causa no es de `marker`, ni del lock, ni de la VRAM, ni de la invocación:

> **El contenedor de vLLM que `surya` lanza no puede arrancar en esta máquina, porque su PyTorch
> está compilado contra CUDA 13.0 y el driver de la máquina es CUDA 12.8.** Es una propiedad del
> par (imagen, driver), no del encargo, y ninguna variable de entorno de `marker`/`surya` la
> cambia.

Eso convierte los descartes separados de `B3`, `B4` (surya) y `B5` (MinerU) —los tres *«por el
contenedor vLLM»*— en **un solo hecho de máquina**, que ahora tiene número.

Todo se midió con **otro agente trabajando en el carril CPU**: la máquina **no** estaba
despejada, y cada tanda va con sus dos testigos.

---

## 0 · Arranque, comprobado antes de medir nada

| Comprobación | Resultado | Por qué |
|---|---|---|
| `git lfs checkout` en el *worktree* | 39 objetos, 266 MB, del almacén local | trampa 34 |
| **Tamaño** de `corpus/pdf/tipico_texto.pdf` | **3 219 B** | trampa 107: un puntero *existe*; se comprueba el tamaño |
| `python ci/integridad.py` | 9 de 9 verdes, 111 trampas sin huecos | — |
| `filex.gpu` importable desde `.venv-marker` | sí, por `sys.path`, **sin instalar nada** | `CLAUDE.md` §1: venv protegido |

El arnés comprueba el tamaño de la entrada él mismo y se declara **bloqueado** si no son 3 219 B,
para que un *worktree* sin LFS produzca un error y no un CER falso.

---

## 1 · El mecanismo, sondeado: por qué un `torch` CPU no impide el contenedor de GPU

`suelo-y-mcp.md` §3.2 midió el **hecho** —`marker` lanza `docker run --gpus device=0` aunque su
`torch` sea `+cpu`— y dejó la **causa** como conjetura: *«probablemente porque detecta la GPU de
la MÁQUINA … no la capacidad del intérprete»*. La conjetura era correcta y ahora está localizada
(**MEDIDO** por lectura del código instalado):

`.venv-marker/Lib/site-packages/surya/inference/__init__.py`, `_has_nvidia_gpu()`:

| Línea | Criterio | En esta máquina |
|---|---|---|
| 38 | `torch.cuda.is_available()` | **False** — `torch 2.13.0+cpu` |
| 47 | `os.path.exists("/dev/nvidia0")` | False — es Windows |
| **50-56** | **`shutil.which("nvidia-smi")` + `nvidia-smi -L`** | **True** — `C:\Windows\System32\nvidia-smi.exe` |

`_autodetect_backend()` (63-68) devuelve `"vllm"` en cuanto eso es cierto. El docstring dice por
qué existe el tercer criterio: *«la rueda de torch puede ser más nueva que el driver … eso nos
enrutaría en silencio al backend CPU de llama.cpp en una máquina que debería correr vllm»*.
**La comprobación que existe para no equivocarse con el driver es exactamente la que aquí lleva a
una imagen que el driver no admite.**

**Consecuencia general:** «este venv es CPU, luego no necesita el lock» es falso para **cualquier**
venv de esta máquina. El criterio de «¿necesita el lock?» no puede ser una propiedad del
intérprete, porque la biblioteca mira la **máquina**.

### 1.1 Versiones, y una nota de propiedad

| Paquete | Versión |
|---|---|
| `marker-pdf` | 2.0.0 — **editable**: el código vive en `repos/ai-engines/marker`, no en el venv |
| `surya-ocr` | 0.22.1 |
| `torch` (venv) | 2.13.0+cpu (`torch.cuda.is_available() = False`, verificado) |

Que `marker` sea editable importa por `CLAUDE.md` §1: su fuente está bajo `repos/`, que es
**intocable**. Nada de este encargo la edita.

### 1.2 Los ajustes que deciden

`surya/settings.py` es un `BaseSettings` **sin `env_prefix`**: cada campo se fija con una variable
de entorno **del mismo nombre**.

| Ajuste | Defecto | Línea |
|---|---|---|
| `SURYA_INFERENCE_BACKEND` | `None` (auto) | 49 |
| `SURYA_INFERENCE_AUTOSTART` | `True` | 51 |
| `SURYA_INFERENCE_STARTUP_TIMEOUT` | **`600.0`** | 73 |
| `VLLM_DOCKER_IMAGE` | `vllm/vllm-openai:v0.20.1` | 96 |
| `VLLM_GPU_TYPE` | `4090` (**no hay entrada `3060`** en su tabla) | 99 |
| `VLLM_GPU_MEMORY_UTILIZATION` | **`0.85`** | 104 |

*(El `0.85` se cita **de la fuente**, y confirmado por segunda vía: el propio vLLM imprime
`'gpu_memory_utilization': 0.85` en su `non-default args`. La línea de órdenes que capturó mi
arnés salió **truncada** en el log —`--gpu-memory-utilization 0`—, y tomarla de ahí habría sido
publicar un `0`.)*

---

## 2 · Lo que cambió en la máquina desde el 31/08

Esto no es un tercer reintento del mismo problema: **dos de las tres barreras de worker10 ya no
estaban** (MEDIDO el 04/09).

| `suelo-y-mcp.md`, 31/08 | Hoy |
|---|---|
| `docker images` → **ninguna imagen `vllm/*`**; su intento 1 se pasó **432 s** tirando de ella | **`vllm/vllm-openai:v0.20.1` presente, 31,8 GB**, `Metadata.LastTagTime = 2026-09-03T21:33:33Z` |
| — | `~/.cache/datalab/surya/` trae `fast_layout_server.log` y `ocr_error_server.log` **del 03/09**: los servidores locales de surya ya arrancaron bien aquí |
| — | El runtime `nvidia` **existe** (`docker info` → `nvidia:{nvidia-container-runtime}`) |

**Y una corrección de `CLAUDE.md` §1, que es un dato de entorno caducado y no una regla que
cambie** (MEDIDO): la tabla describe `.wslconfig` como *«los 2 vCPU y 1,9 GiB de la VM de
Docker»*. El fichero de hoy dice **`memory=10GB`** y **`processors=6`**, y `docker info` lo
confirma desde el otro lado: **10 429 259 776 B (9,71 GiB) y 6 CPU**. La regla —no tocarlo— vale
entera; lo que caducó es la cifra con la que se justifica, y con ella cualquier razonamiento del
tipo *«eso no cabe en la VM de Docker»*. Yo mismo estuve a punto de usarla como hipótesis.

---

## 3 · Intento 1 — el camino (a) puro

```
D:\Work\research\FileX\.venv-marker\Scripts\python.exe \
  bench/salidas-marker-lock/medir_marker_lock.py --etiqueta i1 --tope 1500 --espera-lock 300
```

que lanza `marker_single <pdf> --output_dir <desechable>/out --output_format markdown`, **sin
`--mode` y sin `TORCH_DEVICE`**: el camino (a) tal cual, dejando que `marker` elija.

### 3.1 El desenlace, con `rc` por celda

**MEDIDO** (`resultado_i1.json`, `log_i1.txt`):

| Magnitud | Valor |
|---|---|
| `rc` de `marker_single` | **1** |
| Duración | **643,87 s** |
| ¿Cortó mi tope de 1 500 s? | **No** (`tope_alcanzado = false`): murió solo |
| Pico de RSS (proceso + hijos) | 2 246,3 MB (n=2 573 muestras a 0,25 s) |
| **Pico de VRAM (total de máquina)** | **2 083 MiB** (n=586 a 1 s), sobre **1 999** de base |
| Salida `.md` | **no existe**, 0 B |
| `docker run` visto a los | **36 s** (worker10: 432 s y 20 s) |
| Contenedores nuevos al terminar | **0** · matados: 0 · huérfanos: 0 |
| Escrito fuera del destino | **0 ficheros** |
| Lock | tomado en 7,41 ms, **soltado** |
| Testigos | deriva **×1,55** (38,79 → 60,07 ms); nivel **×0,54** (88,6 → 47,63 ms) → **`SUCIA(deriva ×1,55)`** |

**No hay CER que publicar, y decirlo es parte del resultado.** Sin `.md` no hay texto: publicar
un «CER = 100 %» sería el fallo de la trampa 99 —un motor que no se ejecutó puntúa igual que uno
que no leyó nada—. El arnés lo deja escrito en el JSON (`nota_trampa_25`) en vez de rellenar el
hueco con un número.

### 3.2 La predicción registrada antes de medir, REFUTADA

El commit `b5db2f7`, hecho **antes** de lanzar, dejó escrito: *«vLLM pedirá 0,85 × 12 288 =
10 444 MiB y hay ~10 100 libres, así que se espera un fallo por VRAM»*. El número la refuta: el
pico fue **2 083 MiB sobre 1 999 de base, +84 MiB**, y el recorrido de las 586 muestras va de
1 997 a 2 083 — el vaivén del escritorio, cuyo recorrido `lock-de-maquina.md` §2.1 midió en
156 MiB con n=90. **vLLM murió sin reservar VRAM**: el fallo ocurre *antes* de que el presupuesto
llegue a comprobarse, así que el razonamiento aritmético apuntaba a un sitio por el que no se
pasa.

*(Aviso de instrumento: `12 288 − libre` y `memory.used` no son la misma medida al MiB, y el ruido
del instrumento es de ±43 MiB (`ocr-produccion-sidecar.md`). El +84 no es cero; lo firme es que no
hay rastro de una reserva de ~10 GB.)*

### 3.3 Lo nuevo frente al 31/08: el contenedor ARRANCA

`suelo-y-mcp.md` midió dos veces un contenedor que **nunca llegó a crearse** (*«seguía tirando de
la imagen»*). Hoy arranca: `docker ps -a` lo dio `Up 16 seconds` y luego `Up About a minute`, y
vLLM 0.20.1 imprimió banner, `non-default args` y configuración del modelo antes de morir con
`RuntimeError: Engine core initialization failed. See root cause above.`

**Y la causa raíz de esa muerte es lo que el intento 1 no puede decir**, no por descuido propio:
`marker` la pide y no la obtiene. Su traza —la del sujeto— termina así:

```
surya.inference.backends.spawn.SpawnError: vllm server failed to become healthy at
http://127.0.0.1:59179 within 600.0s.
--- last vllm server logs ---
Error response from daemon: No such container: surya-vllm-59179
```

### 3.4 Un fallo del instrumento AJENO: la trampa 25 en código de terceros

`spawn.py:341-350` hace justo lo que hay que hacer, con el comentario escrito:

> *«Coge los logs del propio servidor **antes** de que el cleanup se lleve el contenedor (`--rm`),
> porque si no la razón real del fallo se pierde y todo lo que ve quien llama es este timeout.»*

**Y se pierde igual.** `_capture_server_logs` (`spawn.py:141-151`) hace
`docker logs --tail 100 <nombre>`, y para entonces **el contenedor ya no existe**: salió por su
cuenta y `--rm` lo borró en ese instante, no en el `_cleanup()` posterior. La defensa cubre el
caso *«vivo pero insano»* y **no el caso «murió»**, que es el que ocurre. Resultado MEDIDO:
`--- last vllm server logs ---` seguido de `No such container`.

**Y yo caí en la misma piedra un minuto después**: al ver el `Engine core initialization failed`
lancé un `docker logs <nombre>` para guardarlo entero y me respondió `No such container` — se
había ido entre mi lectura de la cola y mi orden. Por eso la sonda de §4 lanza el contenedor
**sin `--rm`** y graba con `docker logs -f` **desde el arranque**.

---

## 4 · La sonda: por qué muere el contenedor

No es un intento de medir `B3`: es el instrumento que convierte «no se pudo» en «no se pudo POR
ESTO». Reproduce la orden **construida desde la fuente** (`vllm.py:143-198` + los defectos de
`settings.py`), con tres cambios **del instrumento y ninguno del sujeto**: sin `--rm`, con
`--name` propio y único (`filex-b3-sonda-<epoch>`) y con grabadora de log en continuo.

**MEDIDO** (`resultado_sonda_vllm.json`, `log_contenedor_sonda.txt`, 166 líneas):

| Magnitud | Valor |
|---|---|
| `docker run` | **rc=0** — el contenedor se crea y arranca |
| Estado a lo largo de 34 sondeos | `running` de 1,1 s a 102,9 s |
| **Muere a los** | **109,2 s** |
| **`docker inspect`** | **`exited｜ExitCode=1｜OOMKilled=false`** |
| Pico de VRAM usada (total) | **2 231 MiB** — la base de la máquina |
| `docker rm -f` | **rc=0**; `sobrevive = False` |
| Lock | tomado en 8,14 ms, soltado |

**`OOMKilled=false` cierra por número la hipótesis de memoria**, tanto de VRAM como de RAM de la
VM — que era mi otra sospecha, ahora que la VM tiene 9,71 GiB y no 1,9.

### 4.1 La causa raíz, con la traza delante

`log_contenedor_sonda.txt`, líneas 63 y 101 (aparece dos veces: en el `EngineCore` y al
repropagarse):

```
RuntimeError: The NVIDIA driver on your system is too old (found version 12080).
Please update your GPU driver ... Alternatively, go to: https://pytorch.org to install a
PyTorch version that has been compiled with your version of the CUDA driver.
```

Y las dos versiones que se enfrentan, **medidas cada una por su lado**:

| Lado | Valor | Cómo se midió |
|---|---|---|
| **La máquina** | driver **572.61**, **CUDA 12.8** (= `12080`) | `nvidia-smi` |
| **La imagen** | **`torch 2.11.0+cu130`**, `torch.version.cuda = 13.0` | `docker run --rm --entrypoint python3 vllm/vllm-openai:v0.20.1 -c "import torch; …"` |

El `12080` del mensaje **es exactamente el CUDA 12.8 de esta máquina**, así que la atribución no
depende de interpretar nada: el número que el contenedor dice haber encontrado es el que
`nvidia-smi` publica desde fuera.

**Esto es estructural.** No lo arregla el lock, ni la VRAM, ni `--mode`, ni `TORCH_DEVICE`, ni
ninguna de las cuatro palancas de §5: **es el par (imagen, driver)**. Las dos únicas salidas
tocan cosas que un worker no decide:

1. **Actualizar el driver de NVIDIA de la máquina.** Es del usuario, y **tiene riesgo medido
   enfrente**: `.venv-ai` (torch cu124), `.venv-paddle` y `.venv-mcp-md` están declarados
   *frágiles, no instalar* en `CLAUDE.md` §1, y las trampas 12 y 13 son las dos de esa misma
   familia. **No se propone**: se deja escrito para quien tenga esa decisión.
2. **Fijar `VLLM_DOCKER_IMAGE` a una imagen compilada contra CUDA 12.x.** Es la única palanca
   real, y su coste está a la vista: **decenas de GB** de descarga, sin garantía de que una vLLM
   más antigua sirva `datalab-to/surya-ocr-2` con `--speculative-config mtp`, que es reciente.
   **PENDIENTE**, y con la salvedad de que probarlo cambia el sujeto.

### 4.2 Es la trampa 13 otra vez, por otro camino

`CLAUDE.md` trampa 13 dice: *«`onnxruntime-gpu` 1.29.0 exige CUDA 13 y cae a CPU en silencio»*.
Éste es **el mismo hecho de máquina con otro motor y otro modo de fallo**: el ecosistema de GPU ha
pasado a CUDA 13 y esta máquina está en 12.8. Ahí caía a CPU en silencio; aquí revienta a los
109 s con `ExitCode=1`. **La frontera es la misma y ya no es de un paquete: es de la máquina.**

---

## 5 · El camino (b), sin gastar un intento en averiguarlo

`suelo-y-mcp.md` §3.3 dejó el camino (b) como *«encontrar y verificar una forma de desactivar el
backend vLLM … no probada»*. Este encargo es el (a) y **no lo prueba**; deja sondeado el mapa por
lectura, marcado `PENDIENTE` a propósito.

| Palanca | Qué haría | Estado |
|---|---|---|
| `marker_single --disable_ocr` | `builders/document.py:63` no llama al `OcrBuilder`; `scripts/convert.py:182-192` **ni importa** `SuryaInferenceManager` | **PENDIENTE** |
| `SURYA_INFERENCE_AUTOSTART=False` | `spawn.py:261-265` lanza `SpawnError` **en vez de** `docker run` | **PENDIENTE** |
| `SURYA_INFERENCE_BACKEND=llamacpp` | evita el contenedor, pero exige `llama-server`, **ausente del PATH** y sin gestor de paquetes | **PENDIENTE**, probablemente muerto |
| `SURYA_INFERENCE_URL=<servidor>` | se ataca a un servidor OpenAI-compatible existente | **PENDIENTE** |

Dos avisos **MEDIDOS** por lectura, que ahorran un intento entero:

1. **`--mode fast` no podía funcionar.** Sólo cambia el modelo de *layout* (`builders/layout.py:88-93`,
   rf-detr local); el **reconocimiento** sigue yendo al VLM (`marker/models.py:54`,
   `builders/ocr.py:99`). El intento 2 de worker10 no falló por mala suerte: `--mode` no toca esa
   decisión.
2. **`--mode quality` no existe** (`config/parser.py:86`: `click.Choice(["balanced","fast"])`), y
   con `torch` CPU `converters/pdf.py:127-135` **ya elegía `fast` solo**. Es decir: worker10 pasó
   explícitamente el valor que el programa iba a tomar por su cuenta — **no era una segunda
   mitigación, era la misma**.

**Y ninguna palanca «hace funcionar» el OCR.** En surya 0.22.1 `recognition/`, `layout/` y
`table_rec/` ya no traen modelo —sólo `__init__.py` y `schema.py`, delegando en el manager—, así
que **no queda backend de reconocimiento local en torch**. Lo que dan es un **fallo declarado** en
lugar de un contenedor. El desenlace probable del camino (b) es *«marker no hace OCR en esta
máquina»*, no *«marker hace OCR en CPU»*.

---

## 6 · El lock: la trampa 88 reproducida en esta tanda, y afinada

El encargo obliga a `tomar()`/`soltar()` en vez del `with` por la trampa 88. Las trampas 59 y 79
obligan a lo otro: **medir también la versión histórica en la propia tanda** antes de publicar un
ratio. Hecho, con `GPU_LOCK` apuntando a un fichero de **control** para no tocar el lock real
(`medir_lock.py`, **medianas de n=9**):

| Camino | Mediana | Rango | Trampa 88 (23/08) |
|---|---|---|---|
| `tomar()` + `soltar()` | **0,858 ms** | 0,768-7,796 | 1,341 ms |
| `with gpu.Lock(...)` | **47,179 ms** | 42,683-52,245 | 47,483 ms |
| `guardia()` sola | **48,720 ms** | 46,213-65,006 | (`nvidia-smi`, 46,9 ms) |
| **Ratio `with` / `tomar+soltar`** | **×54,99** | | ×35,4 |

**La conclusión de la trampa 88 se confirma y su ratio no se transfiere.** El `with` reproduce al
centésimo (47,179 frente a 47,483 ms) y `guardia()` sola cuesta **más que el `with` entero**, lo
que confirma que *todo* el coste del `with` es la guardia y no el lock. Lo que se mueve es el
denominador: `tomar+soltar` sale **0,858** frente a 1,341 ms, y con ello el ratio pasa de ×35,4 a
**×55,0**. Si hubiera dividido mi 0,858 entre su 47,483 habría publicado ×55,3 y habría acertado
por suerte; **el ratio es de la tanda, el hecho es del código.**

*(El `tomar()` en frío del primer uso de un proceso es más caro: 7,41 ms en el intento 1 y 8,14 ms
en la sonda, coherentes con el 7,796 del máximo de n=9. Un arnés que tome el lock una sola vez
paga ese valor, no la mediana.)*

---

## 7 · Verificación de limpieza, y una diferencia entre mis dos arneses

**MEDIDO al terminar:**

```
lock:        fichero inexistente · gpu.esta_libre() = True · gpu.dueno() = None
docker ps -a: los 5 de FileX en marcha + los 2 `Created` del 03/09 (16:17 y 16:24), AJENOS
nvidia-smi:  1 987 MiB usados · 10 129 MiB libres  (base: 1 999 / 10 117)
```

Ningún contenedor `surya-vllm-*` ni `filex-b3-sonda-*` sobrevive; ningún fichero fuera del
destino; los desechables borrados. **Los dos contenedores en `Created` son anteriores a esta
ronda y no se han tocado.**

### 7.1 Un defecto de MI instrumento, con control positivo

El coordinador observó, desde fuera, que tras la sonda el fichero de lock nombraba
`B3-sonda-vllm` con un `winpid` ya muerto, mientras que mi JSON declaraba
`lock_libre_tras_soltar = True`. Cuando fui a mirarlo **el fichero ya no existía**, así que **no
puedo afirmar el mecanismo de ese episodio concreto** y lo dejo como observación —una explicación
plausible no es un mecanismo (trampa 36)—.

**Lo que sí queda MEDIDO, con control positivo determinista, es que mi campo no podía haberlo
visto.** Escribiendo a mano un fichero de lock con un dueño ajeno y muerto, sobre un `GPU_LOCK`
de control:

| Estado | `gpu.esta_libre()` | `gpu.dueno()` |
|---|---|---|
| fichero de lock **presente**, dueño ajeno muerto | **`True`** | **`None`** |

**Las dos funciones miran el mutex `Global\`, no el fichero.** Así que un arnés que declare «lock
libre» con `esta_libre()` está declarando *«el mutex está libre»*, que es **la mitad de la
exclusión**: mientras 24 de los 25 arneses `.py` sigan tomando `O_CREAT|O_EXCL` sobre el fichero
(trampa 96), un fichero huérfano **es** exclusión para ellos y **es** invisible para esta
comprobación. Es la media exclusión de las trampas 77 y 96 vista desde el lado del *testigo* en
vez del lado del *tomador*, y la trampa 44 en su forma exacta: **un campo honesto —el mutex está
libre— con un nombre que promete más de lo que mira.**

Un arnés que quiera decir «no dejé el lock puesto» tiene que comprobar **las dos poblaciones**:
`esta_libre()` **y** `os.path.exists(gpu.fichero_lock())`. Mis dos arneses comprobaban una.

---

## 8 · Qué queda `PENDIENTE`

- **La medida de `B3` (tiempo/VRAM/CER de `marker`) sigue sin existir, y por el camino (a) no va a
  existir en esta máquina** mientras el driver sea CUDA 12.8. No es un pendiente de trabajo: es un
  bloqueo con causa.
- **`VLLM_DOCKER_IMAGE` con una imagen `cu12x`** — la única palanca que podría revivir el camino
  (a). Decenas de GB y sin garantía de que sirva el modelo. **PENDIENTE**, y cambia el sujeto.
- **El camino (b) entero** (§5): las cuatro palancas están localizadas y ninguna ejecutada.
- **Si `.venv-marker` (1 205 MB) sale o se queda** en la lista protegida: sigue siendo decisión del
  maestro. Con lo de hoy hay un argumento nuevo que antes no había —**su motor de OCR no puede
  funcionar en esta máquina con este driver**—, pero la decisión no es mía.
- **No se ha medido** si `marker` produce algo útil con `--disable_ocr` sobre un PDF con capa de
  texto, que es justo el caso de `tipico_texto.pdf`. Es la vía más barata de sacar `B3` del
  bloqueo y **está sin tocar**.

---

## 9 · Texto propuesto para el maestro

**No he editado `ESTADO-Y-REPARTO.md` ni `CLAUDE.md`** (hay otro worker dentro). Propongo:

### 9.1 Registro del informe (tabla de §1), para que `ci/integridad.py` pase

`ci/integridad.py` da hoy **`FALLA: informes-registrados`** con
`marker-con-lock.md` — y **es correcto que falle**: el informe existe y no está
citado. **No lo he registrado yo porque el registro vive en `ESTADO-Y-REPARTO.md`**, que el
encargo me prohíbe tocar por haber otro worker dentro. Las otras ocho comprobaciones están en
verde. Línea propuesta:

> | 04/09 | **`bench/marker-con-lock.md`** (worker1, carril `gpu/marker-con-lock`) | **`B3` cerrado por BLOQUEO, con la causa raíz medida — y no es la que nadie esperaba.** Tomado el lock de GPU (camino (a) de `suelo-y-mcp.md` §3.3) y dejando que `marker` use la tarjeta, `marker_single` da **`rc=1` a los 643,87 s sin producir `.md`**. El contenedor **sí arranca** esta vez (la imagen ya estaba, 31,8 GB, etiquetada el 03/09) y muere a los **109,2 s** con **`ExitCode=1`, `OOMKilled=false`** y `RuntimeError: The NVIDIA driver on your system is too old (found version 12080)`: la imagen trae **`torch 2.11.0+cu130`** y la máquina es **driver 572.61 / CUDA 12.8**. **No es VRAM** —pico 2 083 MiB sobre 1 999 de base, +84 MiB, y `OOMKilled=false`—, lo que **refuta la predicción que este mismo informe registró antes de medir** (`b5db2f7`: «fallará por VRAM, 0,85×12 288 = 10 444 > 10 100»). Es el par (imagen, driver): la trampa 13 otra vez, con otro motor y sin caer a CPU en silencio. Localizado además el mecanismo que `suelo-y-mcp.md` §3.2 dejó como conjetura — `surya/inference/__init__.py:50` usa **`nvidia-smi -L` como TERCER criterio** de `_has_nvidia_gpu()`, por eso un `torch +cpu` no impide nada— y por qué `--mode fast` no podía funcionar (sólo cambia el layout; `--mode quality` ni existe, y con torch CPU `fast` ya era el defecto). Reproducida en esta tanda la trampa 88: `tomar+soltar` **0,858 ms** frente a `with` **47,179 ms** (n=9) → **×55,0**, y `guardia()` sola cuesta más que el `with` entero. Propuesta de **trampa 112** dentro del informe |

### 9.2 Fila `B3` del inventario (línea 285, tres columnas)

> | **B3** | *(se conserva lo tachado y lo de worker10)* … **CAUSA RAÍZ MEDIDA el 04/09/2026 por worker1** (`bench/marker-con-lock.md`), **por el camino (a): con el lock de GPU tomado y dejando que `marker` use la tarjeta.** El contenedor **arranca** —la imagen `vllm/vllm-openai:v0.20.1` ya está en la máquina, 31,8 GB, `LastTagTime` del 03/09, y el 31/08 no estaba— y **muere a los 109,2 s con `ExitCode=1` y `OOMKilled=false`**: `RuntimeError: The NVIDIA driver on your system is too old (found version 12080)`. La imagen trae **`torch 2.11.0+cu130`** (medido con `docker run --entrypoint python3`) y esta máquina es **driver 572.61 / CUDA 12.8**. **`marker_single` devuelve `rc=1` a los 643,87 s y NO produce `.md`, así que no hay CER que publicar** —publicar 100 % sería la trampa 99—. **No es VRAM**: pico 2 083 MiB sobre 1 999 de base. **Es del par (imagen, driver) y no la evita ninguna variable de entorno de `marker`/`surya`**: las dos salidas son actualizar el driver —decisión del usuario, con `.venv-ai`/`.venv-paddle`/`.venv-mcp-md` declarados frágiles enfrente— o `VLLM_DOCKER_IMAGE` con una imagen `cu12x`, decenas de GB y sin garantía. **`B3` se cierra por decisión, igual que `B4` (surya) y `B5` (MinerU), y por el MISMO mecanismo — que ahora tiene número: el contenedor vLLM no puede funcionar en esta máquina con este driver, y eso convierte tres descartes separados en un solo hecho de máquina.** Queda sin probar la vía más barata para sacarlo del bloqueo: `marker_single --disable_ocr` sobre un PDF que **ya tiene capa de texto**, que es justo el caso de `tipico_texto.pdf` | 🔴 **CERRADO POR BLOQUEO, causa raíz medida (driver CUDA 12.8 vs imagen cu130)** · `bench/marker-con-lock.md` |

### 9.2 Retirada de un dato caducado en `CLAUDE.md` §1

La fila de `.wslconfig` dice *«los 2 vCPU y 1,9 GiB de la VM de Docker»*. **Hoy son `memory=10GB`
y `processors=6`**, confirmado desde el otro lado por `docker info` (9,71 GiB, 6 CPU). La regla no
cambia; la cifra sí, y se usa para razonar.

### 9.3 Trampa candidata (si el maestro la acepta, **al final**, como la 112)

> 112. **Un testigo de «no dejé el lock puesto» puede mirar sólo una de las dos poblaciones de la exclusión, y el campo que lo dice es honesto — MEDIDO el 04/09 con control positivo** (`bench/marker-con-lock.md` §7.1). `gpu.esta_libre()` y `gpu.dueno()` consultan el **mutex `Global\`**; con un fichero de lock **presente** y de dueño ajeno muerto devuelven **`True`** y **`None`**. La trampa 96 ya midió que *el viejo sigue siendo la exclusión hasta que migre el último consumidor* —**24 de 25 arneses `.py` toman `O_CREAT|O_EXCL` sobre el fichero**—, así que un fichero huérfano **es** exclusión para ellos y **es invisible** para este testigo. Es la trampa 44 en su forma exacta: **el campo dice la verdad («el mutex está libre») y su nombre promete otra cosa («el lock está libre»)**, y por eso nadie lo discute. Un arnés que declare limpieza tiene que comprobar **las dos**: `esta_libre()` **y** `os.path.exists(gpu.fichero_lock())`. Corolario que amplía la 77: **media exclusión es peor que ninguna, y medio TESTIGO es peor todavía**, porque el de la mitad buena informa en verde.

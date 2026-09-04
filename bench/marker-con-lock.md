# B3 — `marker` con el lock de GPU tomado

**Carril `gpu/`, ronda 14, worker1.** Rama `gpu/marker-con-lock`.
Salidas y arnés en [`bench/salidas-marker-lock/`](salidas-marker-lock/).

**Qué se pedía:** la medida de `B3` que lleva pendiente desde el 19/08 —tiempo, VRAM pico y
CER de `marker` sobre `corpus/pdf/tipico_texto.pdf`—, por el **camino (a)** que
[`bench/suelo-y-mcp.md`](suelo-y-mcp.md) §3.3 dejó escrito y no probó: *tomar el lock de GPU y
dejar que `marker` use la tarjeta*. El camino (b) —desactivar el backend vLLM— **no** es este
encargo; aquí sólo se mide qué palancas existen, para que quien lo intente no gaste sus dos
intentos averiguándolo.

Todo lo de este informe se midió con **otro agente trabajando en el carril CPU**: la máquina
**no** estaba despejada, y por eso cada tanda va con sus dos testigos de ruido.

---

## 0 · Arranque, y lo que ya estaba comprobado antes de medir nada

| Comprobación | Resultado | Por qué se hace |
|---|---|---|
| `git lfs checkout` en el *worktree* | 39 objetos, 266 MB, del almacén local | trampa 34 |
| **Tamaño** de `corpus/pdf/tipico_texto.pdf` | **3 219 B** (no ~130) | trampa 107: un puntero *existe*; se comprueba el tamaño, no la existencia |
| `python ci/integridad.py` | 9 de 9 en verde, 111 trampas sin huecos | — |
| `filex.gpu` importable desde `.venv-marker` | sí, por `sys.path`, **sin instalar nada** | `CLAUDE.md` §1: el venv está protegido |

El arnés comprueba el tamaño de la entrada él mismo y se declara **bloqueado** si no son 3 219 B,
para que un *worktree* sin LFS no produzca un CER falso en vez de un error.

---

## 1 · El mecanismo, sondeado: por qué un `torch` CPU no impide el contenedor de GPU

`bench/suelo-y-mcp.md` §3.2 midió el **hecho** —`marker` lanza `docker run --gpus device=0`
aunque su `torch` sea `+cpu`— y dejó la **causa** como conjetura: *«probablemente porque detecta
la GPU de la MÁQUINA (vía Docker/`nvidia-smi`), no la capacidad del intérprete»*. La conjetura
era correcta, y ahora está **localizada a nivel de línea** (MEDIDO, por lectura del código
instalado, no de documentación):

`.venv-marker/Lib/site-packages/surya/inference/__init__.py`, `_has_nvidia_gpu()`:

| Línea | Criterio | En esta máquina |
|---|---|---|
| 38 | `torch.cuda.is_available()` | **False** — `torch 2.13.0+cpu` |
| 47 | `os.path.exists("/dev/nvidia0")` | False — es Windows |
| **50-56** | **`shutil.which("nvidia-smi")` y `nvidia-smi -L`** | **True** — `C:\Windows\System32\nvidia-smi.exe` |

`_autodetect_backend()` (líneas 63-68) devuelve `"vllm"` en cuanto `_has_nvidia_gpu()` es cierto.
El propio docstring del fichero dice por qué no se fían de `torch`: *«la rueda de torch puede ser
más nueva que el driver … eso nos enrutaría en silencio al backend CPU de llama.cpp en una
máquina que debería correr vllm»*. Es decir: **la tercera comprobación existe a propósito, y es
exactamente la que convierte un venv "CPU" en un consumidor de la tarjeta.**

**Consecuencia que ya estaba escrita y ahora tiene mecanismo:** «este venv es CPU, luego no
necesita el lock» es falso **para cualquier venv de esta máquina**, no sólo para `.venv-marker`.
El criterio de «¿necesita el lock?» no puede ser una propiedad del intérprete, porque la
biblioteca mira la MÁQUINA.

### 1.1 Versiones y una nota de propiedad

| Paquete | Versión |
|---|---|
| `marker-pdf` | 2.0.0 — **instalado editable**: el código vive en `repos/ai-engines/marker`, no en el venv |
| `surya-ocr` | 0.22.1 |
| `torch` | 2.13.0+cpu (`torch.cuda.is_available() = False`, verificado) |

Que `marker` sea editable importa por `CLAUDE.md` §1: su código fuente está bajo `repos/`, que es
**intocable**. Nada de este encargo lo edita.

### 1.2 Los ajustes que deciden, con sus valores por defecto

`surya/settings.py` es un `BaseSettings` **sin `env_prefix`**, así que cada campo se fija con una
variable de entorno **del mismo nombre**:

| Ajuste | Defecto | Línea | Qué decide |
|---|---|---|---|
| `SURYA_INFERENCE_BACKEND` | `None` (auto) | 49 | `vllm` \| `llamacpp`; puesto a mano **cortocircuita** la autodetección |
| `SURYA_INFERENCE_AUTOSTART` | `True` | 51 | a `False`, `spawn.py` lanza `SpawnError` **en vez de** `docker run` |
| `SURYA_INFERENCE_STARTUP_TIMEOUT` | **`600.0`** | 73 | los 10 minutos esperando `/health` que la trampa 15 llama «se cuelga» |
| `VLLM_DOCKER_IMAGE` | `vllm/vllm-openai:v0.20.1` | 96 | — |
| **`VLLM_GPU_TYPE`** | **`4090`** | 99 | y **no hay entrada `3060`** en su tabla |
| **`VLLM_GPU_MEMORY_UTILIZATION`** | **`0.85`** | 104 | el 85 % de la VRAM |

---

## 2 · Lo que cambió en la máquina desde el 31/08, y que hace este intento distinto del suyo

Esto no es un tercer reintento del mismo problema: **dos de las tres barreras que tenía worker10
ya no están** (MEDIDO el 04/09).

| Lo que midió `suelo-y-mcp.md` el 31/08 | Lo que hay hoy |
|---|---|
| `docker images` → **ninguna imagen `vllm/*`**; el intento 1 se pasó **432 s** tirando de ella | **`vllm/vllm-openai:v0.20.1` presente, 31,8 GB**, con `Metadata.LastTagTime = 2026-09-03T21:33:33Z` |
| — | `~/.cache/datalab/surya/` trae `fast_layout_server.log` y `ocr_error_server.log` **del 03/09 a las 15:56 y 16:06**: los servidores locales de surya ya arrancaron bien en esta máquina |
| — | El runtime `nvidia` **existe** en este Docker (`docker info` → `nvidia:{nvidia-container-runtime}`) |

**Y una corrección de `CLAUDE.md` §1, que es un dato de entorno caducado, no una regla que
cambie** (MEDIDO): la tabla de «nunca toques esto» describe `.wslconfig` como *«los 2 vCPU y
1,9 GiB de la VM de Docker»*. El fichero de hoy dice `memory=10GB` y `processors=6`, y
`docker info` lo confirma desde el otro lado: **10 429 259 776 B (9,71 GiB) y 6 CPU**. La regla
—no tocarlo— sigue valiendo entera; lo que caducó es la cifra con la que se justifica, y con ella
cualquier razonamiento que diga «eso no cabe en la VM de Docker».

---

## 3 · Intento 1 — el camino (a) puro

**Orden exacta** (el arnés la registra en el JSON, campo `cmd`):

```
D:\Work\research\FileX\.venv-marker\Scripts\python.exe \
  bench/salidas-marker-lock/medir_marker_lock.py --etiqueta i1 --tope 1500 --espera-lock 300
```

que a su vez lanza `marker_single <pdf> --output_dir <desechable>/out --output_format markdown`,
**sin `--mode` y sin `TORCH_DEVICE`**: es el camino (a) tal cual, dejando que `marker` elija.

### 3.1 El lock, y un número que corrige por dónde se paga

| Magnitud | Valor | Nota |
|---|---|---|
| `Lock("B3-marker-i1").tomar(espera=300)` | **7,41 ms** (n=1, en frío) | sin `guardia()`: es `tomar()`, no el `with` |
| VRAM base antes de arrancar | **1 999 MiB** usados · **10 117 MiB** libres | por encima del mínimo de 6 000 de `GPU_GUARD` |
| Contenedores en `docker ps -a` antes | 7 | los 5 de FileX en marcha y 2 `Created` heredados de otro carril |

El encargo pedía `tomar()`/`soltar()` en vez del `with` por la trampa 88 —el `with` llama a
`guardia()`, que es un `nvidia-smi` de 46,9 ms—. Se cumple, y el §6 lo mide con `n=9` en vez de
con este `n=1` en frío.

### 3.2 El desenlace, con `rc` por celda

**MEDIDO** (`bench/salidas-marker-lock/resultado_i1.json`, `log_i1.txt`):

| Magnitud | Valor |
|---|---|
| `rc` de `marker_single` | **1** |
| Duración | **643,87 s** |
| ¿Cortó el tope de 1 500 s? | **No** (`tope_alcanzado = false`) — murió solo |
| Pico de RSS (proceso + hijos) | 2 246,3 MB (n=2 573 muestras a 0,25 s) |
| **Pico de VRAM (total de máquina)** | **2 083 MiB** (n=586 muestras a 1 s), sobre **1 999** de base |
| Salida `.md` | **no existe**, 0 B |
| `docker run` visto a los | **36 s** |
| Contenedores nuevos al terminar | **0** · matados: 0 · huérfanos: 0 |
| Escrito fuera del destino | **0 ficheros** |
| Lock | tomado, **soltado**, libre después |
| Testigos | deriva **×1,55** (38,79 → 60,07 ms); nivel **×0,54** (88,6 → 47,63 ms) → **`SUCIA(deriva x1,55)`** |

**No hay CER que publicar, y decirlo es parte del resultado.** No hay `.md`, así que no hay
texto: publicar un «CER = 100 %» aquí sería exactamente el fallo de la trampa 99 —un motor que no
se ejecutó puntúa igual que uno que no leyó nada—. El arnés lo deja escrito en el propio JSON
(`nota_trampa_25`) en vez de rellenar el hueco con un número.

### 3.3 La predicción registrada antes de medir, REFUTADA

El commit `b5db2f7`, hecho **antes** de lanzar la tanda, dejó escrito: *«vLLM pedirá
0,85 × 12 288 = 10 444 MiB y hay ~10 100 libres, así que se espera un fallo por VRAM»*. Y el
número la refuta: **el pico de VRAM fue 2 083 MiB sobre 1 999 de base, es decir +84 MiB**. El
recorrido entero de la serie de 586 muestras va de 1 997 a 2 083, que es el vaivén del escritorio
—`lock-de-maquina.md` §2.1 midió su recorrido en 156 MiB con n=90—. **vLLM murió sin reservar
VRAM**: el fallo ocurre *antes* de que el presupuesto llegue a comprobarse, así que el
razonamiento aritmético que parecía tan sólido apuntaba a un sitio por el que no se pasa.

*(Aviso de instrumento, por si alguien reusa este dato: 12 288 − libre y `memory.used` no son la
misma medida al MiB, y el ruido del instrumento es de ±43 MiB, `ocr-produccion-sidecar.md`. El
+84 no es cero; lo que sí es firme es que no hay ni rastro de los ~10 GB de una reserva de vLLM.)*

### 3.4 Lo que sí es nuevo frente al 31/08: el contenedor ARRANCA

`suelo-y-mcp.md` midió dos veces un contenedor que **nunca llegó a crearse** (*«seguía tirando de
la imagen»*). Hoy la imagen está, y el contenedor **arranca de verdad**: `docker ps -a` lo dio
`Up 16 seconds` y luego `Up About a minute`, y vLLM 0.20.1 llegó a imprimir su banner, su
`non-default args` completo y su configuración del modelo. Después murió con:

```
RuntimeError: Engine core initialization failed. See root cause above. Failed core proc(s): {}
```

**La causa raíz de ESA muerte es lo que el intento 1 no puede decir**, y no por descuido propio:
`marker` la pide y no la obtiene. Su traza —la del sujeto, no una deducción— termina así:

```
surya.inference.backends.spawn.SpawnError: vllm server failed to become healthy at
http://127.0.0.1:59179 within 600.0s.
--- last vllm server logs ---
Error response from daemon: No such container: surya-vllm-59179
```

### 3.5 Un fallo del instrumento AJENO, que es la trampa 25 en código de terceros

`spawn.py:341-350` hace justo lo que hay que hacer, y con el comentario escrito:

> *«Coge los logs del propio servidor **antes** de que el cleanup se lleve el contenedor (`--rm`),
> porque si no la razón real del fallo se pierde y todo lo que ve quien llama es este timeout.»*

**Y se pierde igual.** `_capture_server_logs` (`spawn.py:141-151`) hace
`docker logs --tail 100 <nombre>`, y para cuando se ejecuta **el contenedor ya no existe**: salió
por su cuenta y `--rm` lo borró en ese instante, no en el `_cleanup()` posterior. La defensa cubre
el caso *«vivo pero insano»* y **no cubre el caso «murió»**, que es justo el que ocurre.
Resultado, MEDIDO: `--- last vllm server logs ---` seguido de `No such container`.

Es la trampa 25 en código ajeno —dos causas distintas con la misma pinta de timeout— y la 103 en
su forma más cara: *un arnés que descarta la salida del caso que falla ha medido, y no ha
aprendido*. **Y yo caí en la misma piedra un minuto antes**: al ver el `Engine core
initialization failed` lancé un `docker logs <nombre>` para guardarlo entero y me respondió
`No such container` — el contenedor se había ido entre la lectura de la cola y mi orden. Por eso
la sonda de §4 graba con `docker logs -f` **desde el arranque** y lanza el contenedor **sin
`--rm`**.

<!-- 4 en adelante: sonda -->

---

---

## 5 · El camino (b), sin gastar un intento en averiguarlo

`suelo-y-mcp.md` §3.3 dejó el camino (b) como *«encontrar y verificar una forma de desactivar el
backend vLLM de Surya por completo (variable de entorno o configuración, no probada)»*. **Este
encargo es el (a) y no lo prueba**, pero sí deja sondeado el mapa, para que el siguiente no gaste
sus dos intentos en descubrirlo. Todo lo de esta sección es **lectura de código**, es decir
`PENDIENTE` hasta que alguien lo ejecute — se marca así a propósito.

| Palanca | Qué haría | Estado |
|---|---|---|
| `marker_single --disable_ocr` | `builders/document.py:63` no llama al `OcrBuilder`; `scripts/convert.py:182-192` **ni siquiera importa** `SuryaInferenceManager`. Es la única opción de `marker` que corta el VLM entero | **PENDIENTE** |
| `SURYA_INFERENCE_AUTOSTART=False` | `spawn.py:261-265` lanza `SpawnError("No running vllm server and autostart is disabled")` **en vez de** `docker run`: convierte la cuelga en un error explícito | **PENDIENTE** |
| `SURYA_INFERENCE_BACKEND=llamacpp` | evita el contenedor, pero exige el binario `llama-server`, que **no está en el PATH** de esta máquina y no hay gestor de paquetes (`CLAUDE.md` §2) | **PENDIENTE**, y probablemente muerto |
| `SURYA_INFERENCE_URL=<servidor>` | se ataca a un servidor OpenAI-compatible existente sin lanzar nada | **PENDIENTE** |

Dos avisos que sí están **MEDIDOS** por lectura y que ahorran un intento entero:

1. **`--mode fast` no puede funcionar, y ahora se sabe por qué.** Sólo cambia el modelo de
   *layout* (`builders/layout.py:88-93`, rf-detr local); el **reconocimiento** sigue yendo al VLM
   (`marker/models.py:54`, `builders/ocr.py:99`). El intento 2 de worker10 no falló por mala
   suerte: `--mode` no toca esa decisión.
2. **`--mode quality` no existe.** `config/parser.py:86` declara
   `click.Choice(["balanced", "fast"])`. Y con `torch` CPU, `converters/pdf.py:127-135` **ya
   elegía `fast` por su cuenta**, así que el intento 2 de worker10 pasó explícitamente el valor
   que el programa iba a tomar solo: no era una segunda mitigación, era la misma.

**Y ninguna de las cuatro palancas «hace funcionar» el OCR.** En surya 0.22.1 los paquetes
`recognition/`, `layout/` y `table_rec/` ya no traen modelo —sólo `__init__.py` y `schema.py`,
delegando en el manager—, así que **no queda un backend de reconocimiento local en torch**. Lo
que las palancas dan es un **fallo declarado** en lugar de un contenedor. Quien tome el camino
(b) debe saber que el desenlace probable es *«marker no hace OCR en esta máquina»*, no
*«marker hace OCR en CPU»*.

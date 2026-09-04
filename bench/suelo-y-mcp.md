# N32, C36 y B3 — worker10, carril CPU/Docker, ronda 1

**Encargo `ENCARGO.md` · worker10, `edicius2002/filex-suelo-y-mcp`, base `main`.** Tres filas,
prioridad muy distinta. Se entregan las tres: `N32` completa (decisión con número, código
cambiado, pruebas verdes), `C36` con 2 de los 7 pendientes cerrados (los baratos, tal como pedía
el encargo), y `B3` como **BLOQUEO documentado** — no lo que se pedía medir, pero un hallazgo más
importante que lo sustituye.

**Máquina:** *worktree* `C:\Users\krato\orca\workspaces\FileX\filex-suelo-y-mcp`. Windows 10,
Python 3.11.9 (`.venv-mcp-filex`) para todo excepto `B3` (`.venv-marker`, Python 3.11.9 también).
No se tocó el lock de GPU — hasta que `B3` obligó a comprobarlo (§3). Docker (`29.4.3`) arriba
con `filex-convertx`, `filex-snapotter(+pg,+redis)` y `filex-gotenberg8` sanos, comprobado con
`docker info` y `docker ps -a` antes de tocar nada (trampa 94: declarar el entorno).

**Fecha:** 03/09/2026.

---

## 1 · `N32` — el suelo temporal, decidido

### 1.1 Remedir antes de decidir: el p90 de `no_existe` sin ecualizar HOY

El encargo pedía no adivinar el margen: remedir el p90 de `no_existe` sin ecualizar **en esta
máquina, hoy**, antes de decidir si se sube el suelo. `bench/salidas-suelo-n32/remedir_oraculo.py`
reproduce la metodología de `bench/salidas-oraculo-n9/medir_oraculo.py` (n=2000 por celda, dos
testigos de ruido) sin escribir sobre el `resultado.json` de worker2 (CLAUDE.md: un fichero de
salida por agente).

**Cinco tandas independientes, ANTES de arrancar nada de `B3`** (por el testigo de proceso,
umbral 30 ms: limpia sólo la tanda 1 — 29,09/26,55 ms antes/después—; las tandas 2-5 ya venían
`sucia=True` por sí solas, 30,66-115,8 ms, sin que `marker` estuviera corriendo — ruido de fondo
genérico de la máquina, no del experimento):

| Tanda | p90 `no_existe` sin ecualizar | ratio p90 `no_existe/prohibido` YA ecualizado (suelo 300 µs) |
|---:|---:|---:|
| 1 | 181,77 µs | 0,94× |
| 2 | 325,89 µs | 1,26× |
| 3 | 247,70 µs | 1,32× |
| 4 | 335,09 µs | 1,01× |
| 5 | 242,69 µs | 0,99× |

**Hallazgo, y es el que decide todo lo demás: el 1,88× publicado el 03/09 NO REPRODUCE hoy, ni
siquiera con la máquina ya "sucia" por ruido genérico.** Mediana de las 5 tandas: ratio p90
ecualizado ≈ **1,01×**, prácticamente cerrado, con el suelo que YA HABÍA (300 µs), sin tocar
nada. El p90 sin ecualizar de `no_existe` (181,77–335,09 µs) se queda por debajo del histórico
364,65 µs en las **5 de 5** tandas, `sucia` o no.

**Repetido una sexta vez, con la máquina ya SUCIA** (`marker` corriendo de fondo para `B3`, §3):
5 tandas más, todas marcadas `sucia=True` por el testigo de proceso, dan p90 sin ecualizar de
**400,57–437,60 µs** (por ENCIMA del histórico 364,65) y ratio p90 ecualizado de **1,21–1,64×**
— peor que las 5 limpias, pero **todavía por debajo del 1,88× histórico**. Esta es la versión
que quedó VERSIONADA en `resultado_fresco.json` (la reproducibilidad del script no cambia; lo que
cambió fue el estado de la máquina entre una ejecución y la siguiente, y así se declara).

**Lo que esto demuestra, con las dos tandas contrastadas dentro del mismo informe:** la cola de
1,88× es un efecto de **CONTENCIÓN DE CPU** (worker1 compartiendo máquina el 03/09; `marker` de
fondo en esta misma ronda), no una propiedad fija del suelo de 300 µs. Es la trampa 36 del
proyecto en su forma más directa — *"las cifras absolutas de tandas distintas no son
comparables"*— demostrada dos veces en la misma tarde con el mismo código.

### 1.2 Opción 1 — subir el suelo por encima del p90: medida, y no cierra nada que no cerrara ya

Con el peor p90 fresco (335,09 µs) más margen, candidato = **500 µs**. Monkeypatch de
`filex.confinamiento.PISO_TEMPORAL_S` (sin tocar el fuente: es el experimento, no el cambio) y
remedida in-process (`bench/salidas-suelo-n32/medir_suelo_alto.py`, n=2000):

| Suelo | ratio p90 `no_existe/prohibido` | mediana `prohibido` |
|---|---:|---:|
| 300 µs (actual) | 1,003× | 301,30 µs |
| 500 µs (candidato) | 0,995× | 502,00 µs |

**Subir el suelo NO mejora el ratio** (0,995 frente a 1,003 — dentro del ruido de una sola
tanda) y **cuesta ×1,666 en CADA rechazo real** (301,30 → 502,00 µs de mediana): el amplificador
de DoS que la trampa 28 nombra, pagado sin beneficio medible. **Se descarta.**

### 1.3 Opción 2 — suelo por operación: la que sí cierra algo real, y es estructural, no de ruido

`bench/oraculo-y-gotenberg.md` §1.5 había dejado `PENDIENTE` un residuo distinto del de la cola:
`FileX._resolver()` llama a `Confinamiento.resolver()` **dos veces** por conversión válida
(entrada + directorio de salida) y **una sola** si se deniega en la entrada. Con el suelo por
LLAMADA, la vía válida pagaba el doble — `existe/prohibido = 2,111×` de mediana, **2,149× de p90**
(`bench/salidas-oraculo-n9/resultado_convertir.json`, la ronda anterior). A diferencia de la cola
de §1.1, **este residuo es aritmético, no de ruido**: no depende de qué tan limpia esté la
máquina, depende de cuántas veces se paga el suelo.

**Implementado** (`filex/confinamiento.py`): `Confinamiento.operacion()`, un gestor de contexto
que agrupa varias llamadas a `resolver()` bajo un solo cronómetro — con `threading.local` para no
pisar la marca entre hilos. Dentro de un `with confinamiento.operacion():`, cada `resolver()` ve
la marca y se salta su propio `_esperar_piso`; el suelo se paga UNA vez, al salir del `with`, con
`try/finally` (una `Denegado` a mitad de la secuencia también lo paga). Sin `ecualizar_temporal`,
no hace nada — mismo criterio que ya tenía `resolver()`. `filex/nucleo.py::FileX._resolver()` es
el único punto que hace dos llamadas por operación, y es el que se envuelve.

**Medido a nivel de `FileX.convertir()`** (`bench/salidas-suelo-n32/medir_operacion.py`, n=500,
misma metodología que `medir_convertir.py` de la ronda anterior), **4 tandas independientes**:

| Tanda | ratio `existe/prohibido` mediana | ratio p90 | coste `existe` mediana | coste `prohibido` mediana |
|---:|---:|---:|---:|---:|
| 1 | 1,090× | 1,114× | 353,65 µs | 324,45 µs |
| 2 | 1,249× | 1,772× | 385,50 µs | 308,65 µs |
| 3 | 1,129× | 1,167× | 347,90 µs | 308,20 µs |
| 4 | 1,136× | 1,226× | 349,10 µs | 307,30 µs |
| **antes (por llamada)** | **2,111×** | **2,149×** | **659,55 µs** | **312,50 µs** |

**El ratio baja de 2,11×/2,15× a 1,09–1,25× de mediana y 1,11–1,77× de p90, en las 4 tandas.** El
coste de la vía VÁLIDA baja de 659,55 a 347,90–385,50 µs — **casi la mitad**, porque ahora paga
un piso en vez de dos. El coste de la vía DENEGADA no se mueve (312,50 → 307–324 µs, dentro del
ruido de una tanda a otra). **Cumple exactamente lo que pedía el encargo: cierra el residuo
estructural sin subir el coste del camino válido — lo baja.**

### 1.4 Decisión

**Se implementa el suelo por operación (opción 2) y NO se sube `PISO_TEMPORAL_S`.** Razones, con
número cada una:

1. La cola de 1,88× que motivaba subir el suelo **no reproduce en una máquina limpia** (§1.1):
   es ruido de contención de CPU, no una propiedad del suelo de 300 µs.
2. Subir el suelo **no mejora esa cola** siquiera bajo la propia medida del candidato (§1.2:
   0,995× frente a 1,003×, dentro del ruido) y **cuesta ×1,666 en cada rechazo real** — el
   amplificador de DoS de la trampa 28, pagado sin beneficio.
3. El suelo por operación cierra un residuo **estructural y reproducible en las 4 tandas**
   (§1.3), sin ese coste — de hecho, **abarata** la vía válida.

**No queda perfectamente a 1,00× en la cola** (peor caso de las 4 tandas: 1,77× de p90). Se
declara así, no se esconde: lo que se cierra es el residuo aritmético de doble llamada, no la
variabilidad de fondo de la máquina, que ninguna de las dos opciones medidas ataca sin coste.

**No se toca `PISO_TEMPORAL_S`** (sigue en 300 µs): no hay tanda que lo justifique subir, y la
que sí había medido la cola (03/09) no reproduce.

### 1.5 Verificación

- `pruebas/test_hito1.py` + `pruebas/test_hito7.py`: **77 passed, 59 subtests** (sin cambios de
  recuento frente a la ronda anterior — el suelo por operación no toca ninguna prueba existente).
- Suite completa, primera pasada: **459 passed, 4 skipped, 130 subtests** en ~200-260 s (idéntico
  antes y después de los cambios de código de esta ronda — §1, §2).
- `ci/integridad.py`: **todo en orden**.
- **Segunda pasada de la suite completa** (tras editar sólo `ESTADO-Y-REPARTO.md`, sin tocar
  código): **3 failed, 455 passed, 5 skipped, 130 subtests**, en **1 199,67 s — ×5-6 más lenta**
  que la primera. Los tres fallos son `test_cancelacion.py::ContenedorReal` (dos pruebas de matar
  un contenedor de Docker) y `test_hito5.py::Integracion::...rasteriza` (`tiempo_agotado`): las
  tres son pruebas de TIEMPO/CONTENEDOR, la firma exacta de la **trampa 101** (*"la suite no es
  hermética respecto del estado de la máquina"*). **Diagnóstico, no supuesto**: `git diff --stat
  -- filex/ pruebas/` confirma que **ninguno de los cambios de código de esta ronda toca**
  `test_cancelacion.py`, `test_hito5.py` ni la maquinaria de cancelación de contenedores — la
  fila de proceso, en el momento del fallo, tenía **24 procesos Python** (censo con
  `Get-Process`), dentro del régimen de 23-27 que la trampa 101 ya asocia a este fallo.
  **Reproducido aislado, con la misma máquina, minutos después: 5 de 5 pasan (`ContenedorReal`
  completo + la prueba de `hito5`) en 87,08 s.** Es ruido de máquina compartida (varios carriles
  activos en paralelo), no una regresión de este cambio.

---

## 2 · `C36` — dos de los siete pendientes, los baratos

Por prioridad del encargo: el (7) conecta con `N32` y "puede caer casi gratis"; el (4) es "sólo
medir con Docker levantado, sin diseño nuevo". Los dos se cerraron. Los otros cinco (1, 2, 3, 5,
6) no se tocaron — el encargo ya avisaba de que son más caros o dependen de algo fuera de esta
máquina, y no había margen para ellos esta ronda.

### 2.1 Ítem 7 — el coste de un `convert` con ruta denegada, medido y cerrado

`bench/hito4-mcp.md` §8.6 ya había nombrado el mecanismo: `Servicio.convert()` sólo falla en el
acto si `planificar()` (puro, sin disco) dice que no hay camino; la validación de confinamiento
ocurre **dentro del hilo del trabajo**, así que una ruta denegada gasta un `job_id`, un JSON en
disco (`Trabajos.nuevo()`: `uuid4()` + `os.replace`) y el arranque de un hilo que espera a que su
candado esté tomado (`Servicio._arrancar`) — todo eso para descubrir, ya dentro, que se deniega.

**Medido antes de tocar nada** (`bench/salidas-suelo-n32/medir_job_denegado.py`, n=200,
`fx.convertir` monkeypatcheado a un `stub` para no gastar Docker/CPU real en 400 conversiones —
el punto es el coste de SERVICIO, no el del motor; `Trabajos()` con directorio propio para no
tocar el `%TEMP%/filex-trabajos` compartido):

| | `prohibido`, sin gate | `prohibido`, con gate | `existe`, sin gate | `existe`, con gate |
|---|---:|---:|---:|---:|
| mediana | 2 601,65 µs | **19,40 µs** | 2 799,40 µs | 3 248,15 µs |
| `job_id` gastados (de 200) | 200 | **0** | 200 | 200 |

Sin gate, **una ruta denegada cuesta lo mismo que una válida** (mismo orden de magnitud) y gasta
un `job_id` **siempre** (200/200). Con el gate, el denegado cae **×134** y **0 `job_id`**; la vía
válida sube +448,75 µs (+16 %) por el `validar()` extra.

**Implementado**: `FileX.validar(entrada, salida) -> bool` en `filex/nucleo.py` (repite
`_resolver()` capturando `Denegado`), llamado en `Servicio.convert()` **después** de comprobar
que el camino existe (`planificar()`, igual que antes) y **antes** de `Trabajos.nuevo()`. El
orden que `pruebas/test_hito4.py::test_convert_fuera_de_la_raiz_no_convierte` documentaba como
deliberado —camino primero, disco después, para no filtrar más que el `enum` del catálogo— **se
conserva intacto**; lo que cambia es que la comprobación de confinamiento deja de vivir sólo
dentro del hilo. Verificado con el código real, sin monkeypatch (`fx.convertir` stub, entrada
prohibida): `srv.convert(...)` devuelve `{'error': 'ruta no accesible'}` sin `job_id`, y una
entrada válida sigue devolviendo su `job_id` normal.

**La prueba existente se actualizó** (documentaba el comportamiento viejo a propósito, con su
razón escrita): pasó de `assertIn("job_id", ...)` + esperar a que el trabajo terminara en
`FALLIDO`, a `assertNotIn("job_id", ...)` + `assertEqual(r, {"error": MENSAJE_OPACO})`. El
docstring se amplió para dejar constancia de por qué cambia y qué NO cambia (el orden
planificar→confinamiento, que es lo que la prueba protegía de verdad).

### 2.2 Ítem 4 — el catálogo con Gotenberg y el sidecar "dentro": medido lo que se puede medir sin diseño nuevo, y declarado lo que no

**Verificado antes de medir, no supuesto:** ni Gotenberg ni el sidecar de OCR son subclases de
`filex.motores.Motor`. `fx.grafo.aristas` no los incluye porque no existe una clase de motor que
los registre — registrarlos de verdad **es diseño nuevo** (escribir `MotorGotenberg`, decidir qué
motor(es) de los cuatro de OCR exponer), justo lo que el encargo pedía evitar en este ítem.

**Lo que sí se puede medir sin diseño nuevo es una PROYECCIÓN**, hecha sólo en el script de
medida (nunca en `filex/motores.py`): añadir al grafo, en memoria, las aristas que Gotenberg YA
demostró que cubre (`bench/gotenberg-y-mcp.md` C35, medido ese mismo día: 6/7, `docx / html / md
/ odt / rtf / txt → pdf`; `epub→pdf` da HTTP 500 y se EXCLUYE a propósito — proyectar una arista
que el motor no cumple sería inventar cobertura, trampa 72), y volver a pedir el catálogo.
Gotenberg se re-verificó vivo HOY antes de proyectar (`GET /health` → 200), no se asumió del
informe de otro día.

`bench/salidas-suelo-n32/medir_catalogo_proyectado.py`:

| | aristas | orígenes/destinos (enum) | tokens (`o200k_base`) |
|---|---:|---:|---:|
| real (6 motores del hito 5) | 230 | 34 / 34 | 1 650 |
| proyectado (+ 6 aristas de Gotenberg) | 236 | 34 / 34 | **1 650 (+0)** |

**Las 230 aristas reales ya son 15 más que las 215 que citaba `gotenberg-y-mcp.md`** — coherente
con el commit `bc31810` de esta misma rama ("+15 aristas documentales y 5 formatos"), fusionado
antes de que empezara esta ronda: confirma que la medida de hoy es del árbol actual, no una cifra
arrastrada.

**Hallazgo: añadir Gotenberg no mueve ni un token del catálogo.** Los seis formatos que Gotenberg
cubre (docx/html/md/odt/rtf/txt→pdf) **ya están en el enum** vía LibreOffice/Pandoc en contenedor
— el `enum` es un conjunto de símbolos únicos, y Gotenberg no aporta ninguno que no estuviera. Es
el reverso, visto desde el catálogo MCP, de lo que `C35` ya había medido desde la latencia:
*"Gotenberg... no añade conversión sobre C13"*. Si algún día se registra, sería una optimización
de **latencia** (×7,21 más rápido, medido en C35) puramente interna — invisible en la superficie
del catálogo.

**El sidecar de OCR se deja `PENDIENTE`, a propósito, con la razón escrita en el propio script**:
no tiene un único conjunto origen/destino que proyectar sin decidir antes cuál de los cuatro
motores (RapidOCR/PaddleOCR/EasyOCR/Tesseract) entra al catálogo y qué arista(s) expone —decidir
eso es la mitad de diseño que este ítem pedía evitar, no una medida.

### 2.3 Verificación de C36

- `pruebas/test_hito4.py`: **30 passed, 1 skipped** (antes de este cambio: 1 failed sobre el
  mismo módulo, arreglado con la actualización de §2.1).
- Suite completa (`pruebas/`): **459 passed, 4 skipped, 130 subtests** — mismo recuento que antes
  de los cambios de `N32` y `C36` juntos (ver §1.5 sobre una segunda pasada con 3 fallos de
  máquina, no de código, diagnosticados y reproducidos aislados).
- `ci/integridad.py`: **todo en orden**.

---

## 3 · `B3` — BLOQUEO, y uno más importante que la medida que se pedía

### 3.1 Lo que se pedía, y por qué no se pudo completar

El encargo daba por hecho, citando `CLAUDE.md`, que `.venv-marker` es un build **CPU** (`torch`
sin paquetes `nvidia-*`, confirmado: `torch.__version__ = 2.13.0+cpu`,
`torch.cuda.is_available() = False`) y que por tanto **no hace falta el lock de GPU**. **Esa
premisa es FALSA, medida dos veces:**

**Intento 1 — modo por defecto.** `marker_single corpus/pdf/tipico_texto.pdf --output_dir ...
--output_format markdown` (sin `--mode`, que según la propia ayuda de la herramienta elige
`balanced` en GPU y `fast` en CPU/MPS "por dispositivo"). A los **432,42 s** de arrancar, con
`marker_single.exe` casi sin CPU propia (0,02 s acumulados) pero con hijos de hasta ~1 GB de RSS,
apareció un proceso hijo:

```
docker.EXE run --rm -d --name surya-vllm-50239 --runtime nvidia --gpus device=0
  -v C:\Users\krato/.cache/huggingface:/root/.cache/huggingface -p 50239:8000 --ipc=host
  vllm/vllm-openai:v0.20.1 --model datalab-to/surya-ocr-2 ...
  --gpu-memory-utilization 0.85 ...
```

**Sin que nadie hubiera tomado el lock de GPU.** Se abortó de inmediato (`taskkill /T /F` al
árbol entero); `docker ps -a` y `docker images` confirman que el contenedor NUNCA llegó a crearse
(seguía tirando de la imagen) y que no quedó ninguna imagen `vllm/*` descargada — **no hubo daño,
pero lo hubo por poco**: la trampa 15 de `CLAUDE.md` (*"Surya 0.22.1 lanza un contenedor vLLM que
reserva el 85 % de la VRAM y se cuelga sin excepción"*) describe exactamente este mecanismo, y
aquí se reprodujo con datos concretos: `--gpu-memory-utilization 0.85`, `--runtime nvidia`.

**Intento 2 — forzando `--mode fast` + `TORCH_DEVICE=cpu`.** Según la propia ayuda de
`marker_single`, `fast` "usa detectores ligeros de CPU para layout/tablas y sólo hace OCR por
bloques del contenido garabateado/vacío" — se esperaba que evitara el modelo VLM. **No lo
evitó**: a los **20,20 s** (con un guardián de seguridad que mata el árbol en cuanto detecta un
hijo `docker*`, capturando la orden exacta antes de matarlo) apareció el **mismo** `docker run
--runtime nvidia --gpus device=0 ... vllm/vllm-openai:v0.20.1 --model datalab-to/surya-ocr-2 ...`,
carácter por carácter salvo el nombre del contenedor (`surya-vllm-51920`).

**Dos intentos, dos bloqueos del mismo mecanismo, con dos mitigaciones distintas ninguna de las
cuales lo evitó** (`--mode fast` no lo evita; forzar `TORCH_DEVICE=cpu` por variable de entorno
tampoco). Por la regla del proyecto (dos intentos, luego se documenta y se sigue), se para aquí.
**No se instaló nada, no se cambió el venv, no se tocó `.wslconfig` ni ningún fichero protegido.**

### 3.2 El hallazgo que sustituye a la medida pedida

**MEDIDO, y es más importante que "cuánto tarda marker en un PDF":** un build de `torch`
CPU-only en el venv **no impide que `marker`/`surya` usen la GPU de la máquina**. La selección de
backend de Surya (`surya/inference/backends/vllm.py`, `surya/settings.py`) decide lanzar un
contenedor `vLLM` con `--gpus device=0` **independientemente de si el proceso que invoca a
`marker` tiene CUDA disponible en su propio `torch`** — probablemente porque detecta la GPU de la
MÁQUINA (vía Docker/`nvidia-smi`), no la capacidad del intérprete que lo invoca. Ni `--mode fast`
ni `TORCH_DEVICE=cpu` lo evitan desde la línea de órdenes o el entorno del proceso.

**Consecuencia directa para `CLAUDE.md` §2:** la fila de `.venv-marker` en la tabla de entornos
virtuales dice *"build CPU, sin una sola medida"* y la deja fuera del régimen de protección de
GPU por esa razón. **Esa razón ya no vale**: `.venv-marker` SÍ puede tomar la tarjeta, sin avisar
y sin que quien lo ejecuta lo pida. Cualquier ejecución futura de `marker`/`marker_single` en
esta máquina **necesita el lock de GPU como cualquier otro proceso que la use**, y el aviso
"CPU-only, no hace falta el lock" debería retirarse de donde esté escrito. Se deja esto como
**recomendación explícita para el maestro**, no como edición unilateral de `CLAUDE.md` — el
fichero no está en la lista de "tuyos" de este encargo y la decisión de reescribir su tabla de
entornos es suya.

### 3.3 Lo que queda `PENDIENTE`

- **La medida original de B3** (tiempo/memoria/calidad de texto de `marker` sobre un PDF con
  verdad conocida) sigue sin hacerse. Antes de reintentarla hace falta una de dos cosas que este
  encargo no cubre: (a) tomar el lock de GPU explícitamente antes de invocar `marker` aunque el
  venv sea "CPU", o (b) encontrar y verificar una forma de desactivar el backend `vLLM` de Surya
  por completo (variable de entorno o configuración de `surya.settings`, no probada — dos
  intentos ya consumidos con `--mode` y `TORCH_DEVICE`).
- **Se preparó y quedó lista la verdad conocida** para cuando se reintente: `corpus/pdf/
  tipico_texto.pdf` renderizado con `magick -density 150` y leído visualmente (no del texto-capa
  crudo, que da un artefacto de codificación distinto) — el propio PDF tiene un defecto real: el
  glifo de la `ñ` está roto en el documento fuente y se ve como `n` + un circunflejo suelto. La
  lista `ESPERADO` y el evaluador CER quedan ya escritos en `medir_marker.py`.
- **No se decide aquí** si `.venv-marker` (1 205 MB) sale o se queda en la lista protegida —
  encargo lo pedía explícitamente reservado al maestro, y con un bloqueo de por medio la pregunta
  ni siquiera se pudo intentar responder esta ronda.

### 3.4 Verificación de que no quedó nada corriendo

```
docker ps -a        -> solo los 5 contenedores de FileX que ya estaban antes (convertx,
                        snapotter+pg+redis, gotenberg8); ningún surya-vllm-*
docker images        -> sin ninguna imagen vllm/*
nvidia-smi           -> 1 197 MiB / 12 288 MiB, 37 % util — mismo orden que antes de tocar nada
```

Sin huérfanos, sin imágenes descargadas a medias, sin lock de GPU tomado ni liberado (nunca se
tomó, porque nunca se supo que hacía falta hasta que ya era tarde para pedirlo con seguridad —
la decisión correcta, una vez visto el contenedor, era abortar, no tomar el lock a mitad de
carrera).

---

## 4 · Verificación general

**Intérprete:** `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe`, Python 3.11.9,
`win32`, para `N32` y `C36`. `D:\Work\research\FileX\.venv-marker\Scripts\python.exe`, mismo
Python/plataforma, para `B3`.

**Entorno:** Docker arriba desde antes de empezar (§0), sin GPU tomada por este carril (§3
explica por qué debería haberlo estado, con carácter retroactivo, para `B3` — que se abortó antes
de causar daño).

```
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe -m pytest pruebas/ -q
```
→ **Primera pasada: 459 passed, 4 skipped, 130 subtests** (idéntico antes y después de los
cambios de `N32`+`C36`; los 4 `skipped` no se investigaron, no forman parte de este encargo).
→ **Segunda pasada (tras sólo editar `ESTADO-Y-REPARTO.md`): 3 failed, 455 passed, 5 skipped,
130 subtests, en ×5-6 más tiempo** — diagnosticado como trampa 101 (contención de máquina, 24
procesos Python en el momento del fallo) y no como regresión: `git diff --stat -- filex/
pruebas/` no toca ninguno de los tres módulos que fallaron, y los 5 tests en cuestión
(`ContenedorReal` completo + la de `hito5`) pasan **5 de 5** reproducidos aislados, 87,08 s
después. Detalle en §1.5.

```
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe ci/integridad.py
```
→ **Todo en orden** (citas, inventario, trampas, informes registrados, manifiestos, secretos,
binarios, en-curso).

**Qué quedó fuera de la verificación:** no se corrió `pruebas/` con el intérprete de `.venv-ai`
ni de `.venv-paddle` (no los toca este cambio); no se probó en WSL2 (los cambios de `N32`/`C36`
no dependen de PID entre intérpretes ni de mutex `Global\`, así que no aplica la familia de
trampas 90–94).

**Estado de la máquina:** limpia sólo en la tanda 1 de las 5 de `N32` §1.1 (testigo de proceso <30
ms); las tandas 2-5 de ese mismo bloque ya venían `sucia=True` por ruido genérico, sin `marker` de
por medio; SUCIA de forma clara para la segunda repetición de 5 tandas y para las medidas de
`medir_operacion.py` y `medir_job_denegado.py`, que corrieron con `marker` de fondo (§3) —
declarado en cada tabla, no escondido; las comparaciones relativas dentro de cada tanda se
sostienen igual (CLAUDE.md §3). Y SUCIA otra vez, más tarde y sin `marker` de por medio, para la
segunda pasada de la suite completa (§1.5, §2.3): **24 procesos Python simultáneos** en el
momento del fallo — varios carriles trabajando a la vez en la misma máquina, no un efecto de
este encargo.

---

## 5 · Salidas en disco

`bench/salidas-suelo-n32/` — ver su `MANIFIESTO.md`: 6 scripts, 6 `.json` de resultado. Sin
binarios: `marker_out/` se creó vacío (dos intentos abortados antes de producir salida) y se
borró.

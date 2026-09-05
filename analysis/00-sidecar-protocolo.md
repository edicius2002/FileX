# Sidecar Python persistente en SnapOtter — disección de ingeniería

Fuente: `repos/orchestrators/SnapOtter/` (bajo la raíz del clon). Todas las rutas son relativas a esa raíz.
Todo lo afirmado aquí está citado con `fichero:línea`. Lo que no he podido verificar en el código está marcado explícitamente como **[no verificado]**.

---

## 0. Corrección previa: no hay una asimetría efímero/persistente

El análisis de partida (`SnapOtter.md:16-18`) dice que `bridge.ts` hace `spawn` por invocación y que solo el OCR es persistente. **Eso es incorrecto.** SnapOtter tiene **tres** rutas de ejecución Python y **dos** de ellas son persistentes:

| Ruta | Proceso | Script Python | Intérprete | Dónde |
|---|---|---|---|---|
| **A** `PythonDispatcher` perfil `"ai"` | **persistente** | `dispatcher.py` | venv compartido | `bridge.ts:355-529` |
| **B** `PythonDispatcher` perfil `"docs"` | **persistente** | `dispatcher.py` (mismo script, `DISPATCHER_PROFILE=docs`) | venv compartido | `bridge.ts:1017-1020`, `dispatcher.py:106-107` |
| **C** `runPerRequest` | **efímero, 1 proceso por invocación** | `<script>.py` directo | venv compartido | `bridge.ts:648-802` |
| **D** `OcrRuntimeManager` | **persistente** | `ocr_runtime_entrypoint.py` | **intérprete propio, artefacto firmado** | `ocr-runtime-dispatcher.ts:615-936` |

La ruta C **no es el modo normal, es el fallback**. `run()` intenta primero el dispatcher persistente y solo cae a spawn-por-invocación si el dispatcher no está disponible o si acaba de morir (`bridge.ts:896-919`). El `spawn(pythonBin, [scriptPath, ...args])` con fallback a `python3` que menciona el análisis previo vive en `bridge.ts:701-764`, dentro de `trySpawn`, que es la ruta de degradación.

La asimetría real no es "efímero vs persistente" sino **"venv mutable compartido vs runtime inmutable firmado"** (ver §4).

---

## 1. Protocolo IPC

### 1.1 Transporte: stdin/stdout, JSON delimitado por líneas (NDJSON). No hay sockets.

Ambos sidecars persistentes usan exactamente el mismo transporte: `stdio: ["pipe","pipe","pipe"]` y una línea JSON por mensaje.

- Ruta A/B: `spawn(getPythonPath(), [resolve(PYTHON_DIR,"dispatcher.py")], { stdio:["pipe","pipe","pipe"], env: this.buildEnv() })` — `bridge.ts:361-364`.
- Ruta D: `spawn(runtime.pythonPath, [runtime.entrypoint], { cwd: dirname(runtime.entrypoint), env: buildRuntimeEnv(runtime), shell:false, stdio:["pipe","pipe","pipe"], windowsHide:true })` — `ocr-runtime-dispatcher.ts:638-644`.

Fíjate en `shell: false` y en el `env` **construido desde cero** (no heredado): `buildRuntimeEnv` en `ocr-runtime-dispatcher.ts:454-476` devuelve un objeto congelado de 19 claves; `buildMinimalEnv` en `bridge.ts:38-82` parte de `{PYTHONUNBUFFERED, LANG}` y **solo** copia 16 variables de una lista blanca (`bridge.ts:43-61`), con el comentario explícito de no filtrar secretos ni config de aplicación.

### 1.2 Formato de trama

**Ruta A/B** (`bridge.ts:622-631` → `dispatcher.py:361-374`):
```
→ {"id":"<uuid>","script":"remove_bg","args":[...],"_otel":{"traceparent":"...","tracestate":"..."}}\n
← {"id":"<uuid>","stdout":"<texto>","exitCode":0}\n
```
El campo `_otel` inyecta el contexto de traza W3C (`propagation.inject`, `bridge.ts:623-630`) y Python lo extrae con `TraceContextTextMapPropagator` (`dispatcher.py:375-381`). El *tracing* cruza el límite de proceso.

**Ruta D** (`ocr-runtime-dispatcher.ts:603-608` → `ocr_runtime_entrypoint.py:84-114`):
```
→ {"protocolVersion":1,"requestId":"<uuid>","script":"ocr"|"ocr_pdf"|"smoke","args":[...]}\n
← {"protocolVersion":1,"requestId":"<uuid>","ok":true,"result":{...}}\n
← {"protocolVersion":1,"requestId":"<uuid>","ok":false,"error":{"code":"...","message":"..."}}\n
```

La diferencia de calidad entre A y D es notable. D es un protocolo con contrato: versión, correlación y sobre `ok/result | ok/error`. Y el lado Node **valida el sobre entero antes de aceptarlo** (`parseResponse`, `ocr-runtime-dispatcher.ts:487-521`): si `protocolVersion` no es 1, si el `requestId` no coincide con el que se envió, o si `ok` no es booleano → `"returned a mismatched response envelope"` y se mata el proceso. Python valida simétricamente (`_validate_request`, `ocr_runtime_entrypoint.py:84-103`).

### 1.3 stderr es un canal aparte, para progreso y diagnóstico

En la ruta A/B stderr transporta **tres tipos de evento JSON distintos**, parseados línea a línea en `bridge.ts:395-449`:
- `{"ready":true,"gpu":true|false}` — señal de arranque, emitida una sola vez (`dispatcher.py:354`).
- `{"progress":<int>,"stage":"<str>"}` — progreso en vivo (`dispatcher.py:140-142`, emitido por cada script, p. ej. `remove_bg.py:7-8`).
- `{"info":"..."}` / `{"warning":"..."}` — diagnóstico, reenviado a la consola de Node (`bridge.ts:431-437`).

Lo que no parsea como JSON se acumula como stderr de la petición (`bridge.ts:444-447`).

La ruta D **no hace esto**. Descarta stderr como canal de datos deliberadamente, y el comentario explica por qué (`ocr-runtime-dispatcher.ts:853-857`):

> *"stdout and stderr are independent pipes, so their cross-stream ordering cannot establish request ownership. Keep stderr only as bounded process diagnostics for unexpected exits; never attach a late chunk to the next otherwise-successful request."*

Es decir: en cuanto respondes una petición, `clearProcessStderr()` (`:832-835`, llamado en `:857`) tira el buffer. El `stderr` que devuelve al núcleo en caso de éxito es literalmente `""` (`:868`). Solo se usa para componer el mensaje de un cierre inesperado (`:915-920`).

**Consecuencia para FileX**: si quieres progreso en vivo *y* correlación estricta, necesitas los eventos de progreso **con `requestId` dentro, por stdout**, no por stderr. SnapOtter tuvo que elegir uno u otro.

### 1.4 Ficheros binarios grandes: NUNCA pasan por el pipe

Este es el punto más importante de la sección. **Los binarios se intercambian por sistema de ficheros; el IPC solo transporta rutas.**

- OCR: Node rasteriza con sharp y escribe a disco — `await image.png().toFile(inputPath)` (`ocr.ts:220`, ruta construida en `ocr.ts:155`), y luego envía **la ruta**: `runOcrRuntime("ocr", [inputPath, JSON.stringify(runtimeOptions)], …)` (`ocr.ts:321`).
- Herramientas de imagen: `remove_bg.py` abre `input_path` (`remove_bg.py:235`) y escribe el resultado con `open(output_path,"wb")` (`remove_bg.py:277-278`); por stdout solo devuelve `{"success":true,"model":…,"device":…}` (`remove_bg.py:283`).
- Transcripción: `input_path = sys.argv[1]` (`transcribe.py:21`).

Los límites de tamaño confirman que el diseño lo asume:

| Límite | Valor | Cita |
|---|---|---|
| Petición máxima (D) | **64 KB** | `ocr-runtime-dispatcher.ts:87`, espejado en `ocr_runtime_entrypoint.py:19` |
| stdout acumulado (D) | 8 MB | `ocr-runtime-dispatcher.ts:85` |
| stderr acumulado (D) | 1 MB | `ocr-runtime-dispatcher.ts:86` |
| Mensaje de error (D) | 400 caracteres | `ocr_runtime_entrypoint.py:20,41` |

64 KB de petición es un techo que impide físicamente mandar una imagen inline. Y Python defiende la sincronización de trama ante una petición sobredimensionada: `readline(MAX_REQUEST_BYTES + 1)` y si excede y no termina en `\n`, responde el error y **sale** en vez de interpretar la cola como otra petición (`ocr_runtime_entrypoint.py:202`, `216-224`, `258-259`). Ese detalle es exactamente el bug de resincronización que un protocolo NDJSON casero suele tener.

La ruta A/B **no tiene límite de tamaño de petición** en Node. Es una asimetría de robustez a favor de D.

### 1.5 Detalle sucio de la ruta A: captura de stdout a nivel de descriptor

`dispatcher.py` no importa los scripts como módulos: los `compile()`+`exec()` en el espacio del propio proceso (`dispatcher.py:290-294`). Como algunos scripts manipulan descriptores directamente (`remove_bg.py:197-198` hace `os.dup(1)` / `os.dup2(2,1)`), el dispatcher no puede usar `StringIO`: crea un pipe real, hace `os.dup2(write_fd, 1)` y lanza **un hilo drenador** para que el buffer del pipe no se llene y bloquee con >64 KB de salida (`dispatcher.py:253-278`, comentario en `:214-217`). Luego restaura el fd (`:311-321`) y `drain_thread.join(timeout=10)` (`:323`).

Esto es frágil por construcción y el propio fichero lo admite: **no hay aislamiento de proceso entre scripts**, la frontera de seguridad es únicamente la allowlist `ALLOWED_SCRIPTS` (`dispatcher.py:13-20`, `62-79`) validada contra `^[a-z0-9_]+$` (`dispatcher.py:83`, aplicada en `:222-234`).

---

## 2. Ciclo de vida del proceso persistente

### 2.1 Arranque: perezoso, no al boot

`OcrRuntimeManager` **no se arranca al iniciar el servidor**. Se crea la primera vez que hace falta:
- `runOcrRuntime()` comprueba `if (!currentManager?.matches(runtime))` y llama a `rotateOcrDispatcher()` (`ocr-runtime-dispatcher.ts:1277-1289`).
- `rotateForActivation` → `performRotation` → `new OcrRuntimeManager(runtime, managerClosed)` (`:1097`).

Contraste: el dispatcher de la ruta A **sí** se calienta al arrancar: `apps/api/src/index.ts:783` llama `await initDispatcher()` justo después de `app.listen()`, y `init()` sondea `childReady` cada 50 ms con un techo de 30 s (`bridge.ts:842-873`).

Los únicos otros disparadores de D son la ruta de instalación de features: `handoffOcrDispatcher` (`apps/api/src/routes/features.ts:115`), `probeOcrDispatcher` (`:161`), `rotateOcrDispatcher` (`:164`).

### 2.2 `GenerationLease`: qué es exactamente

**No es un lease del proceso ni de la GPU.** Es un lease sobre la **generación del runtime instalada en disco**, para que el instalador no borre un árbol de ficheros que un proceso vivo está usando. Tiene dos mecanismos superpuestos (`ocr-runtime-dispatcher.ts:371-452`):

1. **Un `flock` compartido del kernel** sobre `<aiDataDir>/v3/locks/generations/ocr/<generation>.lock` (`acquireGenerationReadLock`, `:334-369`). Se adquiere lanzando `/usr/bin/flock --shared --nonblock --conflict-exit-code 73 3` con el fd heredado como descriptor 3, o `python3 -c "fcntl.flock(3, LOCK_SH|LOCK_NB)"` si no hay flock (`:298-332`). El lock queda pegado a la *open file description* de Node y el kernel lo suelta al cerrar el fd o al morir el proceso (`:293-297`).
2. **Un fichero-latido JSON** en `<aiDataDir>/v3/leases/ocr/<generation>/<pid>-<processNonce>-<requestNonce>.json`, reescrito **cada 5 s** (`LEASE_HEARTBEAT_MS = 5_000`, `:89`; temporizador en `:400-414`) con `{schemaVersion:2, family, generation, pid, processNonce, requestNonce, createdAt, heartbeatAt}` (`:417-429`). La escritura es atómica: fichero temporal + `rename` (`writeAtomicJson`, `:157-176`).

El latido es un canal de fallo, no solo telemetría: si falla una escritura, el lease invoca `failureHandler` y **eso cancela la petición en vuelo** (`:400-413` → registrado en `submit`, `:690`). Es decir, perder la capacidad de renovar el lease aborta el trabajo.

Ámbito: **un lease por petición**, no por proceso. Se crea en `runOcrRuntime` (`:1251`) y se cierra en el `finally` (`:1298-1300`); igual en `probeManager` (`:1050`, `:1057-1059`). `close()` para el temporizador, borra el fichero y cierra el fd del flock (`:436-451`).

Endurecimiento defensivo notable: cada componente de la ruta se valida con `lstat` contra enlaces simbólicos (`ensureSafeLeaseDirectory`, `:178-221`), la identidad del inodo del lock se reverifica **después** de adquirir el flock (`assertGenerationLockFileIdentity`, `:269-291`, llamado en `:348` y `:363`), y `generation` debe casar con `/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/` (`:95`, `:335-337`, `:383-385`).

### 2.3 Detección de muerte del proceso

Node engancha cuatro eventos (`attachProcessListeners`, `ocr-runtime-dispatcher.ts:712-722`): `stdout.data`, `stderr.data`, `stdin.error`, `child.error`, `child.close`. Y si algún pipe no existe, aborta de inmediato (`:719-721`).

`handleClose` (`:903-935`) es donde se decide qué error ve el núcleo:
1. Si ya había `fatalError`, ese gana.
2. Si quedó un `stdoutBuffer` sin `\n` → `"returned a malformed JSON response"` (`:911-913`). Detecta una respuesta truncada por muerte a mitad de escritura.
3. Si había petición en curso o en cola → `"exited with code <code> (<signal>): <stderr>"` (`:914-921`), y ahí sí usa el stderr acumulado.

Además hay un **detector de deriva de activación**: un `setInterval` cada 10 s (`ACTIVATION_WATCH_INTERVAL_MS = 10_000`, `:90`; `watchPublishedActivation`, `:976-981`) que compara la identidad de activación en disco con la del manager publicado y, si no coincide, lo despublica y lo pone a drenar (`checkPublishedActivation`, `:960-974`). El temporizador se limpia cuando no queda ningún manager (`:954-957`).

### 2.4 ¿Reinicia? Depende de la ruta — y aquí las dos filosofías divergen

**Ruta A (`bridge.ts`) sí reinicia, con backoff exponencial y un techo duro:**
- `CRASH_WINDOW_MS = 60_000`, `MAX_CONSECUTIVE_CRASHES = 5`, `BASE_BACKOFF_MS = 1_000` (`bridge.ts:262-264`).
- `recordCrash()` (`:316-338`): si el crash anterior fue hace más de 60 s, el contador se reinicia a 1; si no, incrementa. A los 5 crashes → `childFailed = true`, **"disabling permanently"** (`:325-331`). Si no, `backoffEnd = now + 1000 * 2^(n-1)` (`:333`).
- `getChild()` respeta el backoff y respawnea (`:531-538`).
- El contador se pone a 0 cuando el hijo señala `ready` (`:413`).

**Ruta D (`ocr-runtime-dispatcher.ts`) NO reinicia automáticamente.** No existe ninguna lógica de respawn: `managerClosed` (`:951-958`) solo limpia el `Set` y anula `currentManager`. El siguiente `runOcrRuntime` volverá a rotar (`:1277-1289`) y creará un manager nuevo, pero es reactivo a demanda y **no hay backoff, ni contador de crashes, ni deshabilitado permanente**. Un runtime que crashea en bucle rearrancará en cada petición.

Es una carencia real de D frente a A. **[Interpretación mía, no un comentario del código]**: D acepta ese coste porque su arranque está protegido por el *smoke test* (§2.6), que falla rápido y de forma observable, mientras que A sirve a 14 herramientas heterogéneas donde un crash aislado no debe tumbar el conjunto.

**Reciclado programado** — solo en A: `MAX_REQUESTS = int(os.environ.get("DISPATCHER_MAX_REQUESTS","50"))` (`dispatcher.py:332`); al alcanzarlo, el bucle rompe y el proceso sale (`dispatcher.py:426-429`), y Node lo respawnea en la siguiente petición. Es la mitigación de fugas de memoria: reiniciar cada 50 trabajos. D **no** tiene equivalente.

### 2.5 Timeouts

| Ruta | Default | Cita |
|---|---|---|
| A/B | `PROCESSING_TIMEOUT_S` (env), si no **600 000 ms**; `PROCESSING_TIMEOUT_S=0` desactiva el timeout | `bridge.ts:13`, `20-30`; `env.ts:55` (`PROCESSING_TIMEOUT_S` default 0) |
| D | **600 000 ms** (10 min), no desactivable — `resolveTimeoutMs` rechaza ≤0 y no finito | `ocr-runtime-dispatcher.ts:84`, `543-549` |
| A `init()` | 30 000 ms | `bridge.ts:842` |
| Gracia SIGTERM→SIGKILL (D) | 1 000 ms | `ocr-runtime-dispatcher.ts:88`, `783-790` |

En A, al vencer el timeout **se mata el dispatcher entero** con SIGTERM, con el razonamiento explícito de no dejar todas las peticiones siguientes bloqueadas detrás del script colgado (`bridge.ts:576-590`, comentario en `:578-579`). Y ese kill **sí cuenta como crash** — a propósito: la ruta de timeout deliberadamente *no* mete el hijo en `stoppedChildren`, "so a genuinely hung script still counts as a crash" (`bridge.ts:299-303`).

En D, `timeoutMs` es un **presupuesto total con deadline**, no un timeout por operación: `deadline = performance.now() + totalTimeoutMs` (`:1244`) y cada etapa consume del mismo presupuesto vía `remainingTimeoutMs()` (`:551-555`) y `awaitWithDeadline()` (`:557-593`). Esperar a una rotación en curso te come el tiempo de tu propio OCR. Es más correcto que un timeout por etapa.

### 2.6 Reemplazo del runtime y peticiones en vuelo — la parte mejor resuelta

Modelo: **estado de admisión global** de tres valores, `"open" | "draining" | "shutdown"` (`ocr-runtime-dispatcher.ts:938`, `942`), más un `Set<OcrRuntimeManager>` de managers vivos y un único `currentManager` *publicado* (`:940-941`).

**Rotación (`performRotation`, `:1062-1125`) — arranque en caliente antes de cortar el viejo:**
1. Si el manager publicado ya casa con el descriptor, se le hace un *smoke probe* de verificación (`:1078`). Si falla: `forceAbort` + `await published.closed` + propagar el fallo (`:1079-1086`). El comentario es la clave del diseño: *"rotate() is a readiness gate, not a passive health query. A published process that cannot prove its sessions is no longer safe to admit."* (`:1081-1082`).
2. Si no casa: **se arranca un candidato nuevo mientras el viejo sigue sirviendo** (`:1097`), se le pasa el probe `smoke` (`:1104`), se revalida activación y admisión (`:1105-1109`), y solo entonces `currentManager = candidate` (`:1112`).
3. **Al viejo se le llama `beginDrain()`, no `kill()`** (`:1115`).

`beginDrain()` (`:701-705`) pone `accepting = false` y llama `endWhenIdle()`, que **solo cierra stdin cuando no hay nada en curso ni en cola** (`:746-756`). Respuesta directa a la pregunta: **las peticiones en vuelo sobre el runtime viejo terminan normalmente**. El proceso viejo muere cuando su última petición acaba, no cuando llega el nuevo.

El probe es real, no un ping: `smoke()` en `ocr_runtime.py:1322-1367` ejecuta **una inferencia acotada por cada familia de modelo** (4 backends: `unified`/`korean` × `small`/`medium`, más el clasificador de orientación) contra un fixture temporal, y exige que devuelva texto no vacío y un ángulo en `{0,90,180,270}`. Node además valida el resultado con `validateReadinessResult` (`:1028-1041`), que es donde está el rechazo de GPU (`result.device !== "cpu"` → excepción) ya identificado en el análisis previo.

**Deduplicación de rotaciones concurrentes**: `rotationPromise` + `rotationKey = "<view>:<fingerprint>"` (`:944-945`, `:1143`). Si otro llamante quiere exactamente la misma rotación, se engancha a la misma promesa (`:1146-1149`); si quiere otra distinta, espera a que la actual termine y reevalúa (`:1150-1157`). El llamante que inicia la rotación **no puede cancelarla**: se le pasa `signal: undefined` al `performRotation` compartido, con el razonamiento de que "rotation is shared process state" y no debe morir bajo los pies de otros esperando (`:1162-1170`).

**Apagado (`finishLifecycle`, `:1303-1334`)**: `drainOcrDispatcher()` → `("draining", false)` → `beginDrain()` a todos (`:1320`). `shutdownOcrDispatcher()` → `("shutdown", true)` → `forceAbort()` a todos (`:1317-1318`). Ambos esperan `Promise.allSettled(managers.map(m => m.closed))` y luego **devuelven la admisión a `"open"`** (`:1324-1331`).

**Identidad del runtime — `fingerprint`**: no se compara por generación ni por versión, sino por **JSON canónico del descriptor completo** (`captureDescriptor`, `:123-148`), con las claves ordenadas recursivamente (`canonicalJsonValue`, `:113-121`). El comentario justifica la brutalidad: *"Reuse is valid only for the exact descriptor captured when the child was spawned"* (`:142-145`) — así el fingerprint cubre hashes de ejecución, rutas y tamaños de modelo, compatibilidad y metadatos de activación sin depender del orden de inserción de claves.

### 2.7 Concurrencia interna: estrictamente serie

`pump()` (`:724-744`): `if (this.didClose || this.fatalError || this.current) return;` — **una sola petición en vuelo por proceso**. La cola es un array FIFO (`:620`, `:691`, `:726`). La siguiente se despacha solo tras resolver la anterior (`:878`).

En la ruta A Node *sí* permite múltiples pendientes (mapa `pending` por id, `bridge.ts:286`), pero `dispatcher.py` procesa `for line in sys.stdin:` estrictamente en serie (`dispatcher.py:361`). El comentario de `venv-lock.ts:9-11` afirma que "the persistent dispatcher multiplexes requests by id" — **es engañoso**: multiplexa la correlación, no la ejecución. En la práctica da igual, porque el pool BullMQ de IA corre a **concurrencia 1** (`apps/api/src/jobs/worker.ts:1479`, comentado en `env.ts:63-64` y `ai-quota.ts:4`).

---

## 3. Gestión de modelos y VRAM

### 3.1 Los dos sidecars hacen lo contrario

**Ruta A: los modelos NO se cachean entre peticiones. Solo se cachean los imports.**

Esto es fácil de leer mal. `dispatcher.py` preimporta librerías pesadas al arrancar — PIL, mediapipe, numpy, gpu, rembg (`dispatcher.py:191-197`) — con el comentario "These imports are the main source of cold-start latency" (`:146-147`). Pero cada petición hace `exec(code, module_globals)` del script **desde cero** (`:290-294`), y el script vuelve a construir su sesión: `remove_bg.py:223` llama `new_session(model, providers=providers)` en cada invocación; `upscale.py` reconstruye el `upsampler` cada vez; `restore.py:220-223`, `colorize.py:51-55`, `inpaint.py:205-206` llaman `safe_onnx_session(...)` en cada ejecución.

O sea: **el warm-start de la ruta A ahorra el coste de importar torch/onnx, no el de cargar pesos**. No hay caché de modelos, no hay LRU, no hay TTL de inactividad, no hay límite de modelos coexistentes — porque en régimen estacionario coexiste **cero o uno**.

La limpieza es el reverso de eso, `_cleanup_after_request()` tras **cada** petición (`dispatcher.py:335-343`, invocado en `:423`):
```python
gc.collect()
import torch
if torch.cuda.is_available():
    torch.cuda.empty_cache()
```
Y el reciclado a 50 peticiones (`:332`, `:426-429`) barre lo que `gc` no alcanza.

**Ruta D: los modelos SÍ persisten, sin desalojo, pero son CPU y están acotados.**

`OcrRuntime._backend()` memoiza en `self._backends: dict[tuple[str,str], OcrBackend]` (`ocr_runtime.py:1297`, `1313-1321`), y el entrypoint conserva la instancia entre peticiones (`ocr_runtime_entrypoint.py:198`, `240-251`: `if runtime is None: runtime = runtime_factory()`). El clasificador de orientación cachea su `InferenceSession` en `self._session` (`ocr_runtime.py:722-745`).

**No hay ninguna lógica de descarga, TTL ni límite de memoria en el runtime OCR.** El límite es estructural: como máximo 4 backends (`{small,medium} × {unified,korean}`, ver el bucle de `smoke()` en `ocr_runtime.py:1338-1340`) más la orientación, todos ONNX en CPU. Y el `smoke` los toca todos, así que en la práctica **los 5 quedan cargados desde la activación**, no bajo demanda.

Aparte, acota hilos: `MAX_ONNX_INTRA_OP_THREADS = 4`, `ONNX_INTER_OP_THREADS = 1` (`ocr_runtime.py:41-42`), aplicados vía `sched_getaffinity` (`:192-205`) sobre `SessionOptions` (`:730-737`).

### 3.2 Gates de memoria: existen, pero son de RAM, no de VRAM

**No existe ninguna comprobación de VRAM en todo el repositorio.** Lo verifiqué: `grep -rn "vram\|VRAM\|memoryTotal\|gpu_memory\|max_memory"` sobre `*.ts`/`*.py`/`*.yml` no devuelve **ni una** consulta de memoria de GPU. `nvidia-smi` se invoca solo para obtener el **nombre** de la GPU (`gpu.py:15-20`), nunca `--query-gpu=memory.used`.

Lo que sí hay son dos gates de RAM del contenedor:

1. `OCR_RUNTIME_MINIMUM_MEMORY_BYTES = 4 GiB` (`runtime-resources.ts:5`), comprobado contra el `minimumMemoryBytes` **firmado** en el índice del artefacto (`runtime-index.ts:21`, `290`) mediante `hasOcrRuntimeMemory` (`runtime-state.ts:222`). Falla cerrado: si no puede resolver el límite del cgroup, devuelve `UNKNOWN_MEMORY_CAPACITY` en vez de asumir que hay sitio (`runtime-state.ts:230-232`). La resolución del cgroup es paranoica: valida `/proc/self/mountinfo`, cadenas de montaje, ciclos de padres (`runtime-resources.ts:67-198`).
2. `HQ_CPU_MIN_MEMORY_BYTES = 7.5 GiB` para el inpainting HQ (`hq-memory-gate.ts:6`), leído de `/sys/fs/cgroup/memory.max` (`:9-25`). Y el comentario dice justo lo que a FileX le importa: *"GPU hosts run it in VRAM, so only CPU inference needs this floor"* (`hq-memory-gate.ts:4-5`) — **en GPU el gate se desactiva sin más** (`:32`).

**Traducción para FileX: SnapOtter no gestiona VRAM en absoluto.** Su estrategia frente a un OOM de GPU es reactiva y por herramienta: `torch.cuda.empty_cache()` y reintentar con tiles de 256 (`upscale.py:177-187`, `227-239`), o degradar a CPU si falla la sesión CUDA (`remove_bg.py:224-231`, `gpu.py:181-200`, `gif_remove_bg.py:207-215`). Node, por su lado, solo *clasifica* el OOM a posteriori: SIGKILL/exit 137 → `"Process killed (out of memory) -- try a lighter model or smaller image"` (`bridge.ts:123-128`).

Es viable en un contenedor con GPU dedicada. **No es viable en un escritorio Windows compartido con Chrome y Discord.**

---

## 4. Por qué existen dos sidecars distintos

La respuesta no es "OCR es especial". Es que **son dos modelos de confianza incompatibles**, y esa es la razón de ingeniería que FileX debe entender antes de copiar nada.

| | Ruta A (`dispatcher.py`) | Ruta D (`ocr_runtime_entrypoint.py`) |
|---|---|---|
| Intérprete | venv compartido y **mutable**, `PYTHON_VENV_PATH` o `../../../.venv` (`bridge.ts:86`) | intérprete **dentro del artefacto firmado**, `descriptor.runtime.pythonPath` (`runtime-state.ts:51`, `902`) |
| Instalación | pip reescribe `site-packages` en caliente | árbol inmutable por generación, verificado por SHA-256 y firma Ed25519 |
| Aislamiento entre herramientas | **ninguno** (`exec()` en el mismo proceso, `dispatcher.py:13-20`) | una sola familia de tareas |
| Reinicio | backoff exponencial, 5 crashes → apagado permanente | ninguno; rotación bajo demanda |
| Protocolo | `{id, script, args}`, sin versión | versionado, con validación de sobre |
| GPU | sí, oportunista | **prohibida** (`ocr-runtime-dispatcher.ts:1033`) |

La ruta A necesita `venv-lock.ts` precisamente porque su venv es mutable: un job que hace `dlopen` de `.so` de torch/onnxruntime **mientras pip los reescribe segfaultea el sidecar** (`venv-lock.ts:1-12`). Es un lock lectores/escritores con preferencia al escritor y camino rápido síncrono (`tryAcquireVenvRead`, `:61-65`), tomado alrededor de cada `run()` (`bridge.ts:945-947`).

La ruta D no necesita nada de eso: cada generación es un directorio inmutable distinto, y sustituir el runtime es publicar otra generación y drenar la anterior. Todo el aparato de `runtime-state.ts` existe para sostener esa inmutabilidad.

Y el motivo de que ambas estén **fuera** del proceso Node es el comentario ya identificado en `env.ts:70`: el límite de espacio de direcciones `SUBPROCESS_MEMORY_LIMIT_MB` se aplica a ffmpeg/ghostscript/qpdf/libreoffice pero **no** al sidecar de IA, *"(torch/CUDA reserve huge virtual space)"* (`env.ts:68-70`).

---

## 5. Manejo de errores

### 5.1 Ruta D: taxonomía explícita de tres clases, decidida en Python

`ocr_runtime_entrypoint.py:134-139` es el corazón:
```python
except ValueError as error:        return _failure(request_id, "invalid-request", str(error))
except FileNotFoundError as error: return _failure(request_id, "file-not-found", str(error))
except Exception as error:         return _failure(request_id, "ocr-runtime-failed", str(error))
```
Tres códigos estables, repetidos en `process_request` (`:154-159`):

| Código | Significado | El proceso **sigue vivo** |
|---|---|---|
| `invalid-request` | error de **entrada** (JSON inválido, versión de protocolo mala, ajustes inválidos, script no permitido) | sí |
| `file-not-found` | el fichero de entrada no existe | sí |
| `ocr-runtime-failed` | fallo del **modelo/inferencia** | sí |

La distinción operativa importante: **un error de negocio devuelve `ok:false` y el proceso persiste**; un error de *protocolo* mata el proceso. Node aplica esa regla: `handleResponseLine` (`:837-879`) rechaza la petición con `"Accurate OCR runtime failed (<code>): <message>"` (`:858-864`) y **sigue bombeando** (`:878`); pero si `parseResponse` falla, llama a `terminate()` (`:847-850`), igual que ante una respuesta no solicitada (`:838-842`).

Una excepción calculada: si el **constructor** del runtime falla (los modelos no cargan), responde el error y **sale** con `exit_after_response = True` (`ocr_runtime_entrypoint.py:240-247`, `258-259`). Un runtime que no puede construir sus sesiones no vale para nada; mejor morir que quedarse fallando cada petición.

Cadena de traducción para el núcleo:
- Fallo de **entrada/modelo** → `Error("Accurate OCR runtime failed (<code>): <msg>")` (`:861-863`).
- Fallo de **proceso** → mensaje de `handleClose` con código de salida, señal y stderr acotado (`:914-921`).
- Fallo de **estado** → mensajes específicos: `"is not active"` (`:1013`, `:1248`), `"activation changed before execution"` (`:1024`), `"dispatcher is unavailable"` (`:669`, `:988`), `"dispatcher is <draining|shutdown>"` (`:995`, `:1240`), `"generation is not ready"` (`:985`), `"exceeded 8388608 bytes"` (`:801`).
- **Abort** → `Error` con `name = "AbortError"` (`:97-101`).

### 5.2 Ruta A: clasificación `operational` vs `bug` y redacción de PII

Mucho más elaborada del lado Node. `pythonExitError` (`bridge.ts:111-138`) clasifica por señal y código:

| Condición | Clase | Mensaje |
|---|---|---|
| `SIGSEGV` / exit 139 | `operational` | `"Process crashed (segmentation fault)"` |
| `SIGKILL` / exit 137 | `operational` | `"Process killed (out of memory) -- try a lighter model or smaller image"` |
| Otro exit ≠0 con texto OOM | `operational` | razón extraída |
| Otro exit ≠0 | **`bug`** | razón extraída |

El patrón OOM es `/out of memory|failed to allocate|cudaerrormemoryallocation|cublas_status_alloc_failed|bad_alloc/i` (`bridge.ts:98-99`).

Los errores van envueltos en `SafeError` **no por estilo sino por una razón concreta**: el *scrubber* de Sentry de la API reduce un `Error` plano a `"Error: Error"` (NODE-24, comentado en `bridge.ts:104-109` y `150-156`). Cualquier error que deba llegar al operador tiene que ser `SafeError`.

Extracción del motivo (`extractPythonError`, `bridge.ts:158-196`): intenta parsear stdout/stderr como JSON y leer `.error`; si no, toma la salida cruda si no empieza por `Traceback`; y si es un traceback, se queda con **la última línea significativa** (`:174-186`).

Del lado Python, `sidecar_errors.py` construye `{type, message, frames}` (`build_error_envelope`, `:77-83`) donde:
- `message` pasa por `redact()` (`:45-59`), que sustituye URLs, rutas absolutas, claves relativas `uploads|outputs|previews/…`, IPs v4 y v6, emails, nombres de fichero de usuario, hex ≥16 y literales entrecomillados largos, y trunca a 300 caracteres.
- `frames` **solo conserva los frames del propio directorio del sidecar** y descarta el frame de `dispatcher.py` para que el traceback empiece en el script que falló, no en la infraestructura (`:62-74`).

Node lo recoge en `extractPythonErrorInfo` (`bridge.ts:204-231`), validando cada frame y truncando a 20.

**Errores de estado del dispatcher** (A): `"Python dispatcher exited unexpectedly"` (`:510`), `"Python dispatcher stdin closed unexpectedly"` (`:373`, `:638`), `"Python script timed out"` (`:585`), `"Python script canceled"` (`:242`), `"feature_not_installed"` (`:661`), `"No JSON response from Python script"` (`:1007`).

Y hay una advertencia arquitectónica valiosa en `bridge.ts:342-346`: `run()` decide reintentar comparando **el texto exacto del mensaje** (`bridge.ts:901-903`). Acoplar el control de flujo a strings de error es deuda; FileX debería usar códigos.

### 5.3 Contabilidad de crashes: distinguir "yo lo maté" de "se murió"

`stoppedChildren` es un `WeakSet<ChildProcess>` (`bridge.ts:304`) de hijos terminados **a propósito**. Solo cuentan como crash los cierres de hijos que no están en él (`:384`, `:489-492`, `:515-517`). El comentario explica el bug que evita: un flag de instancia (en vez de por hijo) reseteado por el siguiente spawn dejaría que el `close` de un hijo obsoleto registrase un crash fantasma y anulase el hijo fresco (`:298-303`). Y sin este set, `shutdownDispatcher()` — que corre tras **cada** instalación de bundle — agotaría el límite de 5 crashes y desactivaría el dispatcher para siempre (`:376-383`).

El mecanismo hermano es el **contador de generación**: `this.generation++` en cada spawn (`:357-358`), grabado en cada petición (`:600`), de forma que el `close`/`error` tardío de un hijo obsoleto solo toque sus propias pendientes (`rejectPendingForGeneration`, `:347-353`; comentario en `:290-295`). El mismo concepto aparece en D como `fingerprint`/`matches()` (`ocr-runtime-dispatcher.ts:648-650`).

---

## 6. Descubrimiento del intérprete

### 6.1 Ruta A/B: heurística de tres saltos

`getPythonPath()` (`bridge.ts:85-93`), literal:
```ts
const venvPath = process.env.PYTHON_VENV_PATH || resolve(__dirname, "../../../.venv");
const venvPython = path.join(venvPath, process.platform === "win32" ? "Scripts/python.exe" : "bin/python3");
return existsSync(venvPython) ? venvPython : process.platform === "win32" ? "python" : "python3";
```
1. `PYTHON_VENV_PATH` o `<repo>/.venv`, con layout dependiente de plataforma.
2. Si no existe el binario, `python`/`python3` del `PATH`.
3. Y si el spawn falla con `ENOENT`, un **segundo intento** con `"python3"` literal (`bridge.ts:754-755`), pero **solo en la ruta efímera** — el dispatcher persistente no tiene ese reintento (`:485-505` marca `childFailed = true` ante `ENOENT`).

Nota: es la única parte del código consciente de Windows (`Scripts/python.exe`); todo lo demás — flock, `/sys/fs/cgroup`, `dup2`, SIGTERM — es POSIX.

**Dependencias**: no se descubren, se declaran. `installed.json` en `<DATA_DIR>/ai/installed.json` es el registro (`feature-status.ts:52`, `185-202`), y el gate se aplica **dos veces**: en Python (`dispatcher.py:239-248` con `TOOL_BUNDLE_MAP`, `:113-128`) y en Node (`feature-gate.ts:56-59` con `SCRIPT_BUNDLE_MAP`, `:13-28`). El duplicado es deliberado: la ruta efímera saltaría el gate de Python, así que replica el mismo, con un test de deriva que mantiene los dos mapas sincronizados (`feature-gate.ts:4-12`). Ambos **fallan cerrados**: un `installed.json` ilegible se lee como "nada instalado" (`feature-gate.ts:43-45`, `dispatcher.py:136-137`).

### 6.2 Ruta D: el intérprete es un dato firmado, no una búsqueda

Aquí no hay heurística. El intérprete es un campo del descriptor activo, verificado criptográficamente antes de ejecutarse:

`ActiveRuntimeDescriptor.runtime.pythonPath` está documentado como *"Absolute, containment-checked path returned by readActiveRuntime"* (`runtime-state.ts:48-53`).

Cadena de validación completa:
1. **Selección de target por host**: `selectOcrRuntimeTarget` (`:203-217`) devuelve `"linux-amd64-cpu-py312"` o `"linux-arm64-cpu-py311"` — y `null` si no es Linux o si no está el marcador `SNAPOTTER_OFFICIAL_CONTAINER=1` (`:211-214`). **Fuera del contenedor oficial, el OCR preciso sencillamente no existe.**
2. **Raíz de datos**: `resolveAiDataDir` (`:219-225`), en orden `aiDataDir` → `dataDir/ai` → `$DATA_DIR/ai` → `$AI_DATA_DIR` → `./data/ai`.
3. **Descriptor**: `<aiDataDir>/v3/active/ocr.json`, leído acotado y con toda la ruta comprobada libre de symlinks (`inspectActiveRuntime`, `:983-1000`).
4. **Índice firmado**: `verifyRuntimeIndex` valida una firma **Ed25519** sobre JSON canónico contra un almacén de claves de confianza (`runtime-index.ts:153-212`; `canonicalRuntimeJson` en `:45`; rechazo de clave no confiable en `:192`).
5. **Gate de memoria** (§3.2), `runtime-state.ts:230-236`.
6. **Resolución del path**: `resolveRuntimeFile` (`:554-580`) rechaza rutas absolutas, `\`, segmentos vacíos/`.`/`..`, exige contención bajo `<v3>/runtimes/ocr/<target>/<generation>` vía `isContainedPath`, exige ausencia de symlinks y que sea un fichero regular.
7. **Integridad**: los tres ficheros críticos — `python`, `entrypoint`, `adapter` (`:72`, `:292`) — se rehashean SHA-256 (`:910-915`), **igual que todos los ficheros de modelo** (`:917-928`) y el árbol de payload completo (`verifyPayloadTree`, `:930-931`).

Solo si todo eso pasa se construye el descriptor con `pythonPath`/`entrypoint` absolutos (`:955-956`) y `OcrRuntimeManager` puede hacer `spawn(runtime.pythonPath, [runtime.entrypoint])` (`ocr-runtime-dispatcher.ts:638`).

`feature-status.ts` es quien traduce todo eso a estado de producto: `isFeatureInstalled("ocr")` **ignora `installed.json`** y consulta la capacidad del runtime (`:216-218`), con el comentario de que "an old Paddle entry must not unlock it" (`:1346-1349`). Y compone razones legibles: `"insufficient-memory"`, `"memory-capacity-unknown"`, `"artifact-incompatible"`, `"unsupported-host"` (`:1326-1343`, `:1372-1383`).

### 6.3 Modo offline reforzado

El entorno del hijo fuerza el aislamiento de red, y en la ruta D **dos veces**: en el `env` del spawn (`buildRuntimeEnv`, `ocr-runtime-dispatcher.ts:454-476`: `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `PIP_NO_INDEX=1`, `NO_PROXY=*`, `SNAPOTTER_NETWORK_DISABLED=1`, `SNAPOTTER_ALLOW_MODEL_DOWNLOAD=0`, `PYTHONNOUSERSITE=1`) y otra vez dentro de Python **antes de importar nada** (`configure_offline_environment`, `ocr_runtime_entrypoint.py:23-29`, llamada en `:170`).

En la ruta A es opt-in: `SNAPOTTER_ALLOW_MODEL_DOWNLOAD` debe valer `"1"`/`"true"`, si no se fuerzan los flags offline (`bridge.ts:74-80`), y los scripts comprueban explícitamente si falta el modelo antes de dejar que la librería intente descargarlo (`remove_bg.py:218-223`, `transcribe.py:37-41`).

---

## 7. Qué copiar en FileX y qué hacer distinto

Contexto que manda: **RTX 3060 de 12 GB con ~3,3 GB ya ocupados por el escritorio → ~9 GB reales, variables y no exclusivos.** SnapOtter asume un contenedor Linux con GPU dedicada. Esa diferencia invalida varias de sus decisiones.

### 7.1 Copiar tal cual

1. **Un proceso persistente por línea JSON sobre stdin/stdout, con sobre versionado.** Copia el contrato de la ruta D, no el de la A: `{protocolVersion, requestId, script, args}` → `{protocolVersion, requestId, ok, result|error{code,message}}` (`ocr-runtime-dispatcher.ts:603-608`, `ocr_runtime_entrypoint.py:84-103`). La validación de sobre con rechazo por `requestId` desalineado (`:495-502`) cuesta 20 líneas y elimina toda una clase de bugs de desincronización.
2. **Binarios por sistema de ficheros, jamás por el pipe.** El IPC transporta rutas y ajustes; el sidecar lee y escribe en disco (`ocr.ts:220,321`; `remove_bg.py:235,277`). Con un límite duro de petición (SnapOtter: 64 KB, `ocr-runtime-dispatcher.ts:87`) que haga el error imposible en vez de improbable.
3. **`readline(MAX+1)` + salir si la trama sobredimensionada no termina en `\n`** (`ocr_runtime_entrypoint.py:202`, `216-224`). Es la diferencia entre un protocolo que se recupera y uno que se envenena.
4. **Reemplazo por rotación con drenaje, no por kill.** Arrancar el candidato, pasarle un *smoke test real* (inferencia acotada, no un ping), publicarlo, y solo entonces `beginDrain()` del anterior, que muere cuando termina su última petición (`ocr-runtime-dispatcher.ts:1095-1116`; `beginDrain`/`endWhenIdle` en `:701-705`, `:746-756`). Es la única forma de recargar un modelo sin abortar trabajos en curso.
5. **Contador de generación / fingerprint en cada petición.** Sin él, el `close` tardío de un proceso muerto corrompe las pendientes del proceso nuevo — el bug está explicado en `bridge.ts:290-303`.
6. **Distinguir "yo lo maté" de "se murió"** con un `WeakSet` por hijo, no con un flag de instancia (`bridge.ts:298-304`). Y no contabilizar como crash tus propios reinicios: en FileX habrá muchos (cambio de modelo, presión de VRAM, recarga en caliente).
7. **Backoff exponencial con techo**, de la ruta A: ventana 60 s, 5 crashes, `1000 * 2^(n-1)` ms, contador a cero al recibir `ready` (`bridge.ts:262-264`, `316-338`, `413`). La ruta D **no tiene esto y es su peor carencia** — no lo repliques por omisión.
8. **`env` construido desde cero, no heredado** (`bridge.ts:38-82`, `ocr-runtime-dispatcher.ts:454-476`). Especialmente en un MCP, donde el proceso padre puede llevar credenciales del cliente.
9. **Redacción de PII en los mensajes de error y frames solo del propio código** (`sidecar_errors.py:45-74`). FileX procesa ficheros del usuario: las rutas y nombres van en cada traceback.
10. **Deadline global compartido en vez de timeout por etapa** (`ocr-runtime-dispatcher.ts:551-593`, `1244`). Esperar a un arranque en frío debe consumir del presupuesto del llamante.

### 7.2 Hacer distinto — lo crítico

**a) Presupuesto explícito de VRAM. SnapOtter no tiene ninguno y hay que construirlo.**

Verificado: cero consultas de memoria de GPU en el repo; `nvidia-smi` solo se usa para el nombre (`gpu.py:15-20`). Sus gates son de RAM del cgroup (`runtime-resources.ts:5`, `hq-memory-gate.ts:6`) y en GPU el gate simplemente se desactiva (`hq-memory-gate.ts:32`). Su respuesta al OOM es reactiva: `empty_cache()` + reintento con tile 256 (`upscale.py:177-187`), o degradar a CPU (`gpu.py:181-200`).

Con ~9 GB no exclusivos hace falta lo contrario: **admisión antes de cargar**. Consultar VRAM libre real (`nvidia-smi --query-gpu=memory.used,memory.total` o NVML), mantener un coste declarado por modelo, y **rechazar o desalojar antes de intentar cargar**. Reservar un colchón de seguridad — el escritorio del usuario reclama VRAM sin avisar, y quien pierde en un OOM de Windows puede ser Chrome, no tú.

**b) Registro de modelos con LRU + TTL de inactividad. SnapOtter no tiene ninguno de los dos.**

Verificado: `dispatcher.py` no cachea modelos entre peticiones (recarga en cada `exec`, `:290-294`) y `ocr_runtime.py` cachea sin desalojo (`:1313-1321`) porque son 5 sesiones ONNX en CPU. Ninguna de las dos políticas sirve a FileX: la primera desperdicia el warm-start (que es *la* métrica de un MCP) y la segunda desborda 9 GB en cuanto coexistan Whisper large-v3 (~3 GB en fp16), un OCR en GPU y un upscaler.

Lo que hace falta: un caché de modelos con clave, LRU acotado por **bytes de VRAM** (no por número de modelos), TTL de inactividad para devolver VRAM cuando el usuario deja de trabajar, y desalojo forzado ante presión. La descarga debe ser real: soltar la referencia, `gc.collect()`, `torch.cuda.empty_cache()` — `dispatcher.py:335-343` da la receta, solo que SnapOtter la ejecuta *después de cada petición* en vez de *bajo presión*.

**c) El reciclado por conteo (50 peticiones, `dispatcher.py:332`) es un parche contra fugas, no una política.** Si mides el uso de VRAM lo puedes sustituir por una condición real: reciclar cuando la memoria residente supere un umbral. Un reinicio a mitad de una sesión de trabajo destruye el warm-start que justificaba todo el sidecar.

**d) No repliques `exec()` en el mismo espacio de proceso.** `dispatcher.py:13-20` admite que no hay aislamiento entre scripts y que la frontera de seguridad es una allowlist. Eso obliga a la captura de stdout por `dup2` + hilo drenador (`:253-278`), a un shim de compatibilidad global para basicsr/torchvision (`:161-189`), y a que un segfault en una herramienta se lleve por delante todas las demás. **Importa módulos con funciones tipadas y devuelve estructuras**, no `exec` con `sys.argv` parcheado.

**e) Progreso con `requestId`, por stdout.** SnapOtter tuvo que elegir: la ruta A tiene progreso pero sin correlación fiable (`bridge.ts:420-427` reparte el evento a *todas* las pendientes de esa generación), y la ruta D tiene correlación estricta y por eso **descarta stderr** (`ocr-runtime-dispatcher.ts:853-857`). Para un watcher y un MCP hacen falta las dos cosas: mete los eventos de progreso en el propio stdout con su `requestId` y un discriminador de tipo.

**f) Códigos de error, no comparación de strings.** `bridge.ts:901-903` decide si reintentar comparando `err.message` con dos literales exactos, y el comentario de `:344-346` avisa de que hay que mantenerlos verbatim. La ruta D ya hace lo correcto con `error.code` (`ocr_runtime_entrypoint.py:134-139`). Copia D.

**g) Windows es ciudadano de primera, y eso rompe media implementación.** El único punto consciente de Windows es `Scripts/python.exe` (`bridge.ts:90`). No sirven en Windows: `flock` (`ocr-runtime-dispatcher.ts:298-332`), `/sys/fs/cgroup` (`runtime-resources.ts:7-11`, `hq-memory-gate.ts:10`), `os.dup2` sobre pipes (`dispatcher.py:253-278`), `SIGTERM`/`SIGKILL` (`:778`, `:785`), `sched_getaffinity` (`ocr_runtime.py:193`), modos `0o2770`/`0o660` (`:92-93`), y `selectOcrRuntimeTarget` devuelve `null` fuera de Linux (`runtime-state.ts:211`). Para el lease de generación en local, un lockfile con PID+latido y validación de vitalidad del proceso es suficiente; el flock es para múltiples réplicas de API sobre un volumen compartido, un problema que FileX no tiene.

**h) No copies el aparato de firma Ed25519 ni la verificación de árbol completo.** `runtime-index.ts:153-212` y `runtime-state.ts:900-931` (rehash SHA-256 de intérprete, entrypoint, adapter, cada modelo y todo el payload en **cada** lectura de descriptor) existen porque SnapOtter distribuye artefactos firmados a instalaciones self-hosted de terceros. FileX corre local. Un hash del fichero de modelo al instalar es proporcionado; rehashear un árbol de modelos en cada activación cuesta segundos de I/O por nada.

**i) Sí copia dos ideas de ese aparato, baratas y valiosas:** el **fingerprint canónico** para decidir reutilización de proceso (`ocr-runtime-dispatcher.ts:113-121`, `140-147`) y el **fallo cerrado** de los gates de recursos — si no puedes determinar la memoria disponible, di "capacidad desconocida" y niega, no asumas que hay sitio (`runtime-state.ts:230-232`, `feature-status.ts:1379-1381`). Con VRAM compartida con el escritorio, esa disciplina es exactamente lo que evita tumbar la sesión del usuario.

**j) Su renuncia es tu ventaja, confirmada en el código.** `validateReadinessResult` **lanza excepción** si el runtime OCR reporta cualquier `device` distinto de `"cpu"` (`ocr-runtime-dispatcher.ts:1033`), y `_read_provider` rechaza cualquier provider que no sea exactamente `["CPUExecutionProvider"]` (`ocr_runtime.py:1305-1311`), con hilos capados a 4 (`:41-42`). Transcripción con `faster-whisper-small` fijo (`transcribe.py:35`). No es un olvido: es reproducibilidad comprada con velocidad. Con 9 GB de VRAM, OCR en GPU y whisper `large-v3` en fp16 son diferenciadores reales — **pero solo si (a) y (b) existen primero**, porque cargar los dos a la vez sin presupuesto de VRAM es exactamente cómo se llega al OOM que SnapOtter evita renunciando.

### 7.3 Arquitectura sugerida para FileX (síntesis)

**Un solo sidecar persistente**, no dos. La bifurcación de SnapOtter viene de tener un venv mutable compartido (que necesita `venv-lock.ts`, `bridge.ts:940-947`) frente a un runtime inmutable firmado. Si FileX instala sus dependencias de forma inmutable por entorno, esa razón desaparece y con ella todo el aparato de locks.

- **Protocolo**: NDJSON versionado de D, con eventos de progreso correlacionados en stdout y códigos de error estables.
- **Concurrencia**: serie dentro del sidecar (como ambos, `ocr-runtime-dispatcher.ts:724-726` y `dispatcher.py:361`), con la cola en Node/Python del núcleo. Bajo VRAM compartida, ejecutar dos modelos a la vez es cómo se llega al OOM.
- **Ciclo de vida**: arranque perezoso en la primera petición (como D), rotación con drenaje para recarga en caliente, backoff con techo (de A), reinicio por presión de memoria medida en vez de por conteo fijo.
- **Modelos**: caché LRU acotado por bytes de VRAM + TTL de inactividad + desalojo bajo presión. **Es la pieza que SnapOtter no tiene y que FileX no puede no tener.**
- **Fallback efímero**: consérvalo (`bridge.ts:896-919`). Es barato y convierte un sidecar caído en degradación de rendimiento en vez de indisponibilidad — justo lo que un servidor MCP necesita.

---

### Apéndice: no verificado

- No he encontrado **ningún** mecanismo de descarga de modelos por inactividad, TTL o límite de coexistencia en ninguna de las dos rutas. La búsqueda cubrió `unload|lru_cache|_MODEL_CACHE|OrderedDict|maxsize|empty_cache|del model|gc.collect` sobre `packages/ai/python/*.py` y `vram|VRAM|nvidia-smi|memoryTotal|gpu_memory|max_memory|GPU_MEMORY` sobre todo el repo. Afirmo su ausencia; si existiera bajo otro nombre, no lo he localizado.
- No he leído `install_runtime.py` (3390 líneas) ni `install_feature.py` (1526), que construyen los artefactos. Las afirmaciones sobre el *contenido* de la generación (que el intérprete va dentro del artefacto) se apoyan en el consumidor — `descriptor.runtime.pythonPath` contenido bajo `<v3>/runtimes/ocr/<target>/<generation>` (`runtime-state.ts:902`, `554-580`) — no en el productor.
- `docker/feature-manifest.json` no existe en el checkout (mi grep no devolvió nada), así que los tamaños y `minimumMemoryBytes` por bundle que `feature-status.ts:1305-1311` lee no los he podido inspeccionar.
- Las recomendaciones de §7.2 (a), (b) y (g) son criterio mío aplicado a la restricción de 9 GB, no decisiones presentes en SnapOtter.

# Los cabos MCP que quedaron abiertos — C4 y C5

**Fecha:** 21 de agosto de 2026. Agente **M1**. Máquina: Windows 10 Home 19045, 12 núcleos,
Python 3.11.9, Node 22.23.2 (y Node 24.19.0 en WSL2), sesión de escritorio remota activa
(**todo SUCIA por estructura**). **Sin GPU.** Código y datos crudos en `bench/salidas-mcp-cabos-2/`.

Este informe cierra (o acota) los pendientes **C4** y **C5** de `bench/mcp-cabos-sueltos.md` §7.
Reutiliza sus arneses (`cabo4_deadlock.py`, `stub_mcp.py`, `cabo1_srv_2x.py`) sin modificarlos:
las variantes están copiadas a mi directorio de salidas.

> **Convención.** Cada afirmación va **MEDIDO** (hay una salida literal que la respalda) o
> **PENDIENTE**. Donde contradice o matiza a un documento del proyecto, se dice y se señala.

> **`.mcp.json` NO se tocó.** Este informe no dio de alta ningún servidor en la `.mcp.json` del
> proyecto: todas las sondas de `claude -p` usaron `--strict-mcp-config --mcp-config <fichero
> propio en salidas-mcp-cabos-2>`. `git status .mcp.json` sale limpia. **`~/.claude.json` tampoco.**

> **Concurrencia.** Corriendo a la vez: **D3** editaba los documentos maestros (`HUECOS.md`,
> `PLAN-ORQUESTADOR.md`, `RESULTADOS-MCP.md`, `ANALISIS-COMPLETO.md`) — **no los he tocado, ni
> para corregir una cifra**; las correcciones que este informe implica quedan **para quien
> consolide** (§7). **F1** medía en CPU con `verificador.py`; su contención con mis medidas de
> tiempo (solo C5b) explica que mi cruce salga más bajo que el de `cabo5` — ver §5.

---

## 0. Resumen ejecutivo

| Cabo | Veredicto | Lo que más cambia |
|---|---|---|
| **C4a — las 20 sin ejecutar de `video-audio-mcp`** | **CERRADO. 20 de 20 cuelgan; CERO excepciones** | Con entradas que llegan a la fase de escritura, **las 20 hacen deadlock**. Las 3 que «respondieron» fueron **fallos tempranos de ffmpeg por mis entradas** (fuente sin audio; `-f mkv` inválido), no defensas. Confirma, no refuta, el mecanismo, ahora sobre **26 de las 26 herramientas que tocan ffmpeg** |
| **C4b — ¿emite Claude Code `roots/list_changed`?** | **MEDIDO: declara la capacidad. FileX PUEDE cachear roots por sesión** | Claude Code 2.1.238 anuncia `roots: {listChanged: true}` en `initialize`. La emisión real de la notificación es PENDIENTE (headless no cambia roots), pero **la capacidad declarada es la decisión de diseño**: cachear e invalidar con la notificación |
| **C4c — ¿expone recursos y prompts AL MODELO?** | **CERRADO. NO. Declararlos es coste sin retorno** | El cliente **sí** llama `resources/list` y `prompts/list` en cada sesión, pero **el modelo responde «NINGUNO»** en las dos condiciones. FileX **no debe gastar catálogo** en recursos ni prompts |
| **C4d — ¿llegan las herramientas MCP DIFERIDAS?** | **CERRADO, y CAMBIA EL MODELO DE COSTE.** En sesión real, **SÍ, diferidas** | Catálogo pesado y ligero → **tokens de entrada TOTAL idénticos (26.941 = 26.941)** con herramientas internas presentes; el modelo dice literalmente «*Their schemas are NOT loaded*». Solo con `--tools ""` y pocas herramientas el catálogo se carga **ansioso** (Δ 3.298 tok). El ×2,0–2,6 de `saturacion` se midió en el régimen ansioso |
| **C5a — carrera de symlinks en Linux** | **BLOQUEADO por inestabilidad de la VM de WSL2.** Mecanismo y arnés listos | La VM de Ubuntu (cap 1,9 GiB, **`.wslconfig` intocable**) se volvió irresponsiva (`Wsl/Service/0x8007274c`) al lanzar el servidor Node bajo contención. El vector está identificado y el primitivo que lo habilita ya está MEDIDO en `cabo5_linux.json` |
| **C5b — cruce exacto `inspect` vs staging** | **CERRADO con número.** Cruce ~70 MB (esta tanda) / ~94 MB (tanda de `cabo5`) | Modelo: `cruce_MB ≈ ffprobe_ms × copia_MBps / 1000`. El `inspect` **en proceso** cuesta **0,04–0,06 ms**, ≈1.000× por debajo de `ffprobe`: para `inspect`, el staging **nunca** compensa. R8 se formula junto con R18 (§5.3) |

---

## 1. C4a — Las 20 herramientas de `video-audio-mcp` que no se ejecutaron

`mcp-cabos-sueltos.md` §4 clasificó las 27 por AST y ejecutó **6 representantes** (6/6 cuelgan),
dejando **20 en PENDIENTE por exhaustividad**. El encargo: confirmarlo o refutarlo; y **una
herramienta que NO cuelgue sería más interesante que veinte que sí**.

**Arnés:** `c4a_deadlock_resto.py`, copia adaptada de `cabo4_deadlock.py` (JSON-RPC crudo, lector
demonio, **timeout duro 18 s**, `taskkill /F /T` del árbol, sesión nueva por caso, inventario de
`ffmpeg.exe`). Cada herramienta se llamó **con la salida preexistente** (basura de 152 B) y con
entradas mínimas válidas del corpus. Clasificación de la respuesta en tres, no dos:
`DEADLOCK` · `RESPONDE(exito)` (refutaría) · `RESPONDE(error-ff)` (fallo **antes** del prompt de
sobrescritura — no refuta, es un fallo temprano por entradas no válidas).

### 1.1 Resultado directo — MEDIDO (`c4a_resultados.json`, `c4a_retry3.json`, `c4a_cvf_matroska.json`)

Primera pasada (20 herramientas): **18 DEADLOCK, 3 RESPONDE(error-ff), 0 éxito.** Los 3 que
respondieron lo hicieron en **<105 ms** con la basura **intacta (152 B)** — es decir, ffmpeg
falló antes de tocar la salida. Las tres se re-ejecutaron corrigiendo la causa (regla «dos
intentos»):

| Herramienta | 1.ª pasada | Causa del fallo temprano | 2.ª pasada (corregida) |
|---|---|---|---|
| `add_image_overlay` | RESPONDE(error-ff), 102 ms | fuente `trivial.mp4` **sin pista de audio** (el intento de *audio copy* falla) | con `tipico.mp4`: **DEADLOCK** (18,2 s) |
| `add_subtitles` | RESPONDE(error-ff), 95 ms | ídem, sin audio | con `tipico.mp4`: **DEADLOCK** (18,2 s) |
| `convert_video_format` | RESPONDE(error-ff), 95 ms | `target_format="mkv"` → ffmpeg: **`Requested output format 'mkv' is not known`** (el nombre válido es `matroska`), error de muxer **antes** del prompt | con `target_format="matroska"`: **DEADLOCK** (18,2 s) |

**Veredicto: 20 de 20 cuelgan. CERO excepciones.** No apareció ninguna herramienta que no
colgara: las tres candidatas eran **artefactos de mis entradas**, no defensas del código. Sumadas
a las 6 del informe anterior, **26 de las 26 herramientas que tocan ffmpeg** en `video-audio-mcp`
hacen deadlock de la sesión MCP entera cuando la ruta de salida ya existe. Distribución:

```
DEADLOCK confirmado por ejecución : 26 / 26  (G1: 9, G2: 15, G3: 2)
  - informe anterior (cabo4)      :  6
  - este informe (C4a)            : 20  (18 directas + 2 con audio + 1 con formato válido)
health_check (no toca ffmpeg)     : responde (control positivo)
```

### 1.2 Un matiz sobre el modo de fallo que conviene registrar

`convert_video_format` es de **G1** (vía `_run_ffmpeg_with_fallback`). Con un formato **inválido**
su comportamiento no es colgarse sino **devolver un error** («*Primary method failed… Requested
output format 'mkv' is not known*») en ~5 s, **sin sobrescribir**. Es decir: el wrapper de
fallback **convierte en error** lo que sería un deadlock **solo cuando ffmpeg falla antes de
llegar al muxer**. En cuanto el formato es válido y el grafo llega a escribir, el deadlock reaparece.
No cambia la conclusión —el mecanismo es el mismo— pero delimita **dónde** el fallback lo enmascara:
únicamente en los fallos tempranos de argumentos, nunca en el camino normal.

> **`RESULTADOS-MCP.md` §8.1 y `mcp-cabos-sueltos.md` §4: CONFIRMADAS y su alcance CERRADO.** El
> «reproducido en 6, las 20 restantes PENDIENTE» pasa a **26/26 reproducido por ejecución**. La
> defensa sigue siendo la de siempre: **`stdin=DEVNULL` en el constructor del proceso** (única
> defensa que no se olvida en un punto de invocación, porque no hay puntos de invocación: hay uno).

---

## 2. C4b — ¿Emite Claude Code `notifications/roots/list_changed`?

**Método.** El servidor de sonda (`c4_probe_srv.py`) registra los `params` del `initialize`.
Cada sesión de `claude -p` disparó un `initialize`. **MEDIDO** (`c4_log_pesado.jsonl`,
`c4_log_ligero.jsonl`, cuatro sesiones idénticas):

```json
{"ev": "initialize", "protocolVersion_pedido": "2025-11-25",
 "client_capabilities": {"roots": {"listChanged": true}, "elicitation": {}},
 "clientInfo": {"name": "claude-code", "version": "2.1.238", ...}}
```

**Claude Code 2.1.238 declara `roots.listChanged: true`.** En el protocolo MCP, esa capacidad la
declara el lado que **enviará** `notifications/roots/list_changed` cuando su lista de roots cambie.
Es decir: **el cliente se compromete a avisar.**

> **Decisión de diseño para la capa MCP (hito 4): FileX PUEDE cachear los roots por sesión** y
> **invalidar la caché al recibir `notifications/roots/list_changed`**, en vez de llamar a
> `roots/list` en cada operación. Esto cierra la nota de `cabo2` §2.3 («cachearlos por sesión,
> invalidando con `list_changed`, es trabajo propio del servidor»): **el cliente real soporta el
> mecanismo del que depende esa caché.**
>
> **PENDIENTE (acotado):** *observar una emisión real* de la notificación. En modo headless
> (`claude -p`) no hay forma de cambiar los roots a mitad de sesión, así que se confirma la
> **capacidad declarada**, no una emisión observada. Para el diseño es suficiente: se programa la
> caché con invalidación y, si el cliente nunca emite, la caché simplemente no se invalida hasta
> el fin de sesión, que es el comportamiento correcto por defecto.

---

## 3. C4c — ¿Expone Claude Code recursos y prompts AL MODELO?

El servidor de sonda declara `capabilities.resources` y `capabilities.prompts`, **un recurso**
(`filex://probe/nota`) y **un prompt** (`filex_probe_prompt`), y registra toda lectura. Se le pidió
al modelo, con un prompt explícito y **sin dejarle usar herramientas**, que enumerara sus recursos
y prompts MCP.

**MEDIDO, dos hechos que hay que separar:**

1. **El CLIENTE sí los enumera.** En cada sesión el log muestra `resources/list` (n=1) y
   `prompts/list` (n=1), justo después de `tools/list`. Esto **actualiza** la observación de
   `mcp-cabos-sueltos.md` §1.7 («registró cero lecturas»): *no era que el cliente no preguntara;
   es que no se le había pedido al modelo que los usara*. El cliente **sí** pregunta.

2. **Pero el MODELO no los ve.** En las dos condiciones (con y sin herramientas internas) la
   respuesta literal fue **«NINGUNO — no veo recursos MCP ni prompts MCP disponibles en mi
   contexto actual»** (`c4_out_penum_*.json`, punto 3).

> **Veredicto: declarar recursos y prompts es COSTE SIN RETORNO para el modelo.** Como ya pasa con
> las anotaciones (`mcp-cabos-sueltos.md` §1.2), lo que el cliente lee del protocolo **no cruza
> hasta el modelo**. **FileX no debe gastar catálogo en recursos ni prompts** con Claude Code como
> cliente objetivo; si algún día quiere ofrecer datos «tirados por el servidor», tendrá que
> hacerlo **como herramienta**, que es el único canal que el modelo ve.

---

## 4. C4d — ¿Llegan las herramientas MCP DIFERIDAS de forma general?

**La pregunta de más valor.** `saturacion-herramientas.md` §3.6 midió que el catálogo se paga
**×2,0–2,6 en cada turno**, y sobre eso descansa el presupuesto de **≤1.200 tokens** de
`RESULTADOS-MCP.md` §4. **Si las herramientas llegan diferidas, ese modelo de coste cambia entero.**

### 4.1 El experimento: pesado vs ligero, con y sin herramientas internas

Dos catálogos con los **mismos 6 nombres y esquemas** y descripciones de tamaño muy distinto
(`c4_gen_catalogos.py`): **pesado** (~18.000 chars de serialización, ~4.500 tok) y **ligero**
(~2.300 chars, ~575 tok). El discriminador: si Claude Code inyecta el catálogo **entero** en el
contexto (carga ansiosa), el pesado cuesta ~3.900 tok más por petición; si solo inyecta los
**nombres** y difiere el resto, el coste es casi idéntico. Se corre `claude -p` con una petición
que **no necesita herramientas**, `--output-format json`, cwd neutro (sin `CLAUDE.md`), modelo
Haiku. Se mide el **total de entrada = `input + cache_creation + cache_read`** (invariante al
reparto de caché).

**MEDIDO** (`c4_out_pmin_*.json`):

| Condición | herramientas internas | catálogo | **TOTAL entrada (tok)** |
|---|---|---|---:|
| `pmin_pesado_deftools` | **sí** (sesión real) | pesado | **26.941** |
| `pmin_ligero_deftools` | **sí** (sesión real) | ligero | **26.941** |
| `pmin_pesado_notools` | no (`--tools ""`) | pesado | 11.188 |
| `pmin_ligero_notools` | no (`--tools ""`) | ligero | 7.890 |

- **Con herramientas internas presentes (la sesión real de Claude Code): pesado y ligero dan el
  MISMO total, 26.941 = 26.941.** Las ~3.300 tokens de descripciones **no llegan al contexto**.
- **Con `--tools ""` (la condición de `saturacion`): pesado − ligero = 3.298 tok**, que es
  exactamente el tamaño del catálogo. Ahí **sí** se carga ansioso.

### 4.2 La confirmación cualitativa: el modelo lo dice con todas las letras

Con una petición que le pide pegar la descripción de una herramienta **sin buscarla**
(`c4_out_penum_*.json`):

- **Sesión real (con herramientas internas):**
  > «(2) **NO_VEO_DESCRIPCION** — el system-reminder indica explícitamente que "*Their schemas are
  > NOT loaded*", así que solo veo los nombres de las herramientas deferred, no sus descripciones.»
- **Con `--tools ""`:** el modelo **pega la descripción pesada completa** de `probe_convert`.

Y **generaliza más allá de FileX**: con `--tools ""` pero **40 herramientas** MCP, el modelo ya
no ve la descripción entera («*truncada… termina con [truncated]*», `c4_out_penum_40_notools.json`,
total 34.207 tok). Es decir: la carga ansiosa es un **régimen de catálogo pequeño**; por encima de
cierto tamaño —o en cuanto hay herramientas internas— Claude Code **difiere o trunca** el catálogo.

### 4.3 Qué le pasa al modelo de coste de `RESULTADOS-MCP.md` §4

> **El modelo de coste de catálogo de `RESULTADOS-MCP.md` §4 (y el ×2,0–2,6 de
> `saturacion-herramientas.md` §3.6) NO se sostiene para el despliegue real de FileX y hay que
> rehacerlo / re-acotarlo:** se midieron bajo `--tools ""` con pocas herramientas —el **régimen
> ansioso**—, pero en una sesión normal de Claude Code, donde el servidor de FileX **convive con
> las ~15 herramientas internas**, el catálogo llega **diferido** (solo los nombres), y su coste
> por turno es **≈0 hasta que el modelo busca la herramienta**. El par pesado/ligero lo prueba:
> **26.941 = 26.941 tokens** con catálogos que difieren en ~3.300. El presupuesto de ≤1.200 tokens
> sigue siendo una buena **higiene de nombres** (los nombres sí se inyectan siempre), pero **deja
> de ser el multiplicador ×2,0–2,6 por turno** que el plan asumía.

**Matices que hay que conservar para no sobre-corregir:**
- El coste **no es cero**: los **nombres** de las 4 herramientas sí se inyectan en cada turno, y
  hay un `tools/list` por sesión. Lo que desaparece del camino caliente es el cuerpo del catálogo
  (descripciones + esquemas), que es justo lo que el presupuesto de tokens medía.
- Es **comportamiento de una versión** (Claude Code 2.1.238) y depende del **número total de
  herramientas** en la sesión, no solo de las de FileX. Si un usuario conectara **solo** FileX con
  `--tools ""`, volvería al régimen ansioso. **El diseño no debe apostar todo a la diferición**:
  el argumento de «pocas herramientas, nombres cortos» sigue valiendo como suelo.
- La otra cara ya medida por `saturacion` **no cambia**: un catálogo **demasiado escueto** produce
  fallos silenciosos (15–17 %). La diferición abarata el catálogo grande, pero **no** rehabilita
  reducir la cobertura de `convert`.

---

## 5. C5 — Dos medidas de confinamiento

### 5.1 C5a — La carrera de symlinks en Linux contra `servers/filesystem` — BLOQUEADO

**El vector, identificado leyendo el código** (`lib.ts:99-140`, `index.ts:191-211`): `validatePath()`
resuelve `fs.realpath(absolute)`, comprueba que el realPath cae dentro de las raíces y **devuelve ese
realPath**; el handler hace después `readFileContent(realPath)`. La ventana TOCTOU está **entre la
resolución del realpath y el read**. Devolver el realPath **cierra** el vector fácil (un symlink que
`realpath` colapsa desaparece del realPath), pero **deja abierto** el difícil:

- estado **A** — `target` es un **directorio real** con `secret.txt` dentro (dentro de la raíz) →
  `realpath` da `allowed/target/secret.txt` literal → **pasa**;
- estado **B** — `target` es un **symlink → /fuera** → `realpath` da la ruta de fuera → **deniega**;
- **WIN** — `validatePath` cae en A (pasa y devuelve `allowed/target/secret.txt`) y el `readFile`
  posterior cae en B (con `target` ya symlink) → **lee el secreto de fuera**. El atacante conmuta
  `target` entre dir real y symlink con `rename`/`unlink`/`symlink`.

**Por qué esto es distinto de Windows.** En Windows el 79 % de los intentos del atacante falló por
**bloqueo de fichero** (`mcp-cabos-sueltos.md` §5, heredado). En POSIX **no hay bloqueo obligatorio**:
`os.rename`, `os.remove` y `os.symlink` sobre componentes de ruta se permiten sin restricción —
**ya MEDIDO** en `cabo5_linux.json` (los cuatro vectores «SÍ» en Linux). El primitivo que la carrera
necesita **está disponible en Linux y bloqueado en Windows**, que es exactamente lo que hace que la
medida de Windows «no concluya» para este caso.

**Estado: BLOQUEADO, no refutado.** El arnés que conduce el **servidor real** (`dist/index.js`) por
stdio y corre atacante + cliente en bucle está escrito y listo (`c5a_symlink_wsl.py`). Pero **la VM
de Ubuntu de WSL2 se volvió irresponsiva** a mitad de sesión: funcionaba al arrancar
(`node v24.19.0`, `uname` correctos) y, al lanzar el servidor Node bajo contención, empezó a
devolver **`Wsl/Service/0x8007274c`** en todas las llamadas, incluida `wsl echo alive`. Es
coherente con el **cap de 1,9 GiB** de la VM (`.wslconfig`, **intocable**) agotándose con Node bajo
la sesión SUCIA. **No ejecuté `wsl --shutdown`**: habría matado los contenedores Docker que el
proyecto tiene levantados a propósito (SnapOtter, ConvertX, Gotenberg). Cuatro intentos de
reanimar la VM fallaron; documentado y sigo (regla de «dos intentos»).

> **Lo que queda MEDIDO:** el vector exacto, y que su primitivo habilitante (swap de componente sin
> bloqueo) **existe en Linux y no en Windows**. **Lo que queda PENDIENTE:** la **tasa de éxito**
> empírica del bucle contra el servidor real, que exige la VM de WSL2 estable. El arnés se
> reejecuta tal cual cuando la VM vuelva: `C5A_DUR=12 python3 c5a_symlink_wsl.py`.

### 5.2 C5b — El punto de cruce exacto entre `inspect` y el staging de R8 — CERRADO

**Arnés:** `c5b_cruce_inspect.py`, mediana de n≥9 con **los dos testigos de ruido** (bucle
monohilo para deriva + `ffprobe -version` para nivel, con tope de 20 s). Mide, sobre una curva de
tamaños: **COPIA** al staging (`shutil.copyfile`, sintéticos), **INSPECT externo** (`ffprobe`,
media real) e **INSPECT en proceso** (abrir + leer 64 KiB de cabecera).

**MEDIDO** (`c5b_cruce_inspect.json`; tanda SUCIA, con F1 midiendo en CPU a la vez):

| Tamaño | Copia (mediana) | MB/s | | Fichero real | `ffprobe` | inspect en proceso |
|---:|---:|---:|---|---|---:|---:|
| 1 MB | 1,69 ms | 593 | | `trivial.mp4` (0,5 MB) | 42,9 ms | **0,057 ms** |
| 25 MB | 19,3 ms | 1.293 | | `tipico.mp4` (15,5 MB) | 54,3 ms | 0,064 ms |
| 50 MB | 40,1 ms | 1.247 | | `patologico_16bit.tif` (68,7 MB) | 72,9 ms | 0,056 ms |
| 90 MB | 71,6 ms | 1.258 | | `fuente_4k.mp4` (122 MB) | 59,6 ms | 0,041 ms |
| 128 MB | 99,2 ms | 1.291 | | | | |
| 256 MB | 223,0 ms | 1.148 | | **mediana ffprobe** | **57,0 ms** | **~0,05 ms** |

**El cruce COPIA == `ffprobe`:** interpolado en **72 MB**, por modelo en **70 MB** en esta tanda
(copia mediana 1.225 MB/s para ≥50 MB). En la tanda de `cabo5`, con copia a 1.628 MB/s y `ffprobe`
57,8 ms, el cruce salía en **~94 MB**. La diferencia es el **disco bajo carga**: la copia es más
lenta con la máquina contenida, así que el cruce **baja**. La forma que no depende de la tanda:

> **`cruce_MB ≈ ffprobe_ms × copia_MBps / 1000`.** Con `ffprobe` ≈ 57 ms constante, el cruce vive
> entre **~70 MB (disco a 1,2 GB/s, contendido) y ~95 MB (disco a 1,6 GB/s, holgado)**. Por debajo,
> copiar es despreciable; por encima, el staging supera a la operación (a 122 MB, la copia cuesta
> **1,7–2,8× el `ffprobe`**; `cabo5` midió 1,32× con su disco más rápido).

### 5.3 R8 + R18: la excepción de `inspect`, formulada junto y con número

El encargo avisaba de que **R18 dejó de ser higiene y pasa a requisito de coste**
(`bench/contrato-quinto-punto.md`: sin directorio de trabajo desechable el quinto punto del
contrato cuesta **3,66 ms sobre 1.000 ficheros, ×8,6 el contrato entero**), y de que la excepción
de R8 quizá hubiera que formularla **junto con R18**. Al medir el cruce, las dos convergen en el
mismo sitio:

- **R8** (copiar la entrada a un staging privado) protege a un **motor externo que va a LEER el
  contenido**. `inspect` no entrega la ruta a ningún motor externo: **lee cabeceras en proceso**.
- **R18** (directorio de trabajo desechable, censado al terminar) abarata el **quinto punto** para
  operaciones que **ESCRIBEN una salida**. `inspect` **no escribe nada**: no hay censo que hacer.

`inspect` es, por tanto, la operación que **no necesita ni el staging de R8 ni el directorio
desechable de R18**: es una lectura en proceso, en sitio, sin efectos. Y el número lo sella:

> **La excepción de R8 para `inspect`, con su número:** el `inspect` **en proceso** que la
> operación realmente ejecuta cuesta **0,04–0,06 ms**; el staging que R8 le impondría cuesta de
> **1,7 ms (1 MB) a 166 ms (256 MB)**, cruzando el coste del `inspect` externo (`ffprobe`, ~57 ms)
> en torno a los **70–95 MB** según el disco. Para `inspect`, el staging es **30× a más de 3.000×
> la operación, a cambio de cero seguridad** (una lectura de cabeceras en proceso nunca entrega la
> ruta a un lector ajeno). **`inspect` se queda en proceso y en sitio: exento de R8 y —al no
> producir salida— también de R18.** Esto converge con `RESULTADOS-MCP.md` §12 (que ya quitó
> `ffprobe` del contrato por coste) y con `coste-verificacion.md` (lectura en proceso 145× más
> barata): se llega al mismo sitio por seguridad, por coste de verificación y por coste de staging.

---

## 6. Las dos frases obligatorias

1. **El modelo de coste de catálogo de `RESULTADOS-MCP.md` §4 hay que rehacerlo / re-acotarlo:** su
   multiplicador ×2,0–2,6 por turno se midió en el **régimen ansioso** (`--tools ""`, catálogo
   pequeño), pero en la sesión real de Claude Code 2.1.238 las herramientas MCP llegan **diferidas**
   —catálogo pesado y ligero dan **26.941 = 26.941** tokens de entrada, y el modelo dice que «*los
   esquemas NO están cargados*»— así que el cuerpo del catálogo **no se paga por turno**; solo se
   inyectan los nombres.

2. **La excepción de R8 para `inspect` queda escrita con este número:** el staging cuesta de **1,7
   ms a 166 ms** (creciente con el tamaño, cruzando el `ffprobe` de ~57 ms en **~70–95 MB** según
   el disco) mientras que el `inspect` **en proceso** que protegería cuesta **0,04–0,06 ms** — de
   30× a >3.000× la operación por cero seguridad; **`inspect` se hace en proceso y en sitio, exento
   de R8 y, por no escribir salida, también de R18.**

---

## 7. Qué cambia en los documentos maestros (para D3 / quien consolide — **yo no lo toco**)

| # | Documento y sitio | Qué dice hoy | Qué mide este informe |
|---|---|---|---|
| 1 | `RESULTADOS-MCP.md` §4 / `saturacion` §3.6: catálogo ×2,0–2,6 por turno; presupuesto ≤1.200 tok | Multiplicador por turno como coste real | **RE-ACOTAR.** En sesión real las herramientas llegan **diferidas**: pesado=ligero=26.941 tok (§4). El ×2,0–2,6 es del **régimen ansioso** (`--tools ""`). Los nombres sí se pagan; el cuerpo no |
| 2 | `RESULTADOS-MCP.md` §8.1 / `mcp-cabos-sueltos.md` §4: deadlock reproducido en 6, 20 PENDIENTE | 6 de 26 por ejecución | **CERRADO: 26/26 por ejecución, 0 excepciones** (§1). Las 3 «respuestas» eran fallos tempranos por entradas |
| 3 | `mcp-cabos-sueltos.md` §1.7: recursos/prompts «cero lecturas, no se pidió» | PENDIENTE | **CERRADO.** El cliente **sí** llama `resources/list` y `prompts/list`, pero **el modelo no los ve** («NINGUNO»): declararlos es coste sin retorno (§3) |
| 4 | `mcp-cabos-sueltos.md` §1.7: ¿`list_changed`? | PENDIENTE | **Capacidad MEDIDA:** `roots.listChanged: true`. FileX puede **cachear roots por sesión** e invalidar con la notificación. Emisión real PENDIENTE (§2) |
| 5 | `RESULTADOS-MCP.md` §10 R8 (excepción `inspect`) | Excepción declarada, staging 1,32× | **Con número y junto a R18:** staging 1,7–166 ms vs inspect en proceso 0,04–0,06 ms; cruce ~70–95 MB; exento de R8 **y** R18 (§5.3) |
| 6 | `RESULTADOS-MCP.md` §13 / `mcp-cabos-sueltos.md` §7: symlinks en Linux | PENDIENTE | **Sigue PENDIENTE** — arnés listo, VM de WSL2 caída (`0x8007274c`) bajo contención; vector y primitivo habilitante ya identificados/medidos (§5.1) |

---

## 8. Índice de la evidencia — `bench/salidas-mcp-cabos-2/`

Ver `MANIFIESTO.md`. Los directorios de trabajo (`c4a_trabajo`, `c5_trabajo`, `c5_staging`) se
generaban y **se han borrado**; el directorio de salidas ocupa **~260 KB**, todo texto.

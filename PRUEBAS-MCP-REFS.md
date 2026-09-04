# FileX — Pruebas pendientes sobre `repos/mcp-refs/`

> # ⛔ SUPERSEDIDO — no reasignar como trabajo pendiente
>
> **Sus seis preguntas están las seis CERRADAS**, y las contesta `RESULTADOS-MCP.md`
> —que lo dice ya en su línea 6—, completado por `bench/mcp-cabos-sueltos.md`,
> `bench/mcp-cabos-2.md` y `bench/hito4-mcp.md`. La capa MCP existe desde el
> 22/08/2026 en `filex/mcp.py`.
>
> **Se conserva por dos motivos, no por vigencia:** es el único fichero de texto que
> solo existía en las ramas `ccb/w1..w3` —se rescató el 22/08 antes de borrarlas— y
> documenta **qué se preguntó antes de medir**, que es lo que permite ver cuánto de
> lo que parecía trabajo resultó estar ya contestado.
>
> **Léelo como historia, no como lista de tareas.** Y en concreto: **§4 a §7 están escritas
> en imperativo y en futuro** —«queda solo la fase 2», «si solo se hace una cosa…», «reglas
> para el agente que lo ejecute»— porque eran un plan. **Ese plan se ejecutó y sus
> resultados están en `RESULTADOS-MCP.md`**; ninguna de esas instrucciones es trabajo
> vigente, ni describe cómo se contribuye hoy (para eso está `CONTRIBUTING.md`).

**Documento de traspaso.** Fecha: 19 de agosto de 2026.

> **Objetivo:** determinar **qué componente de qué repositorio es aprovechable** para la capa MCP de FileX. No se trata de puntuar proyectos, sino de identificar piezas concretas y reutilizables.

---

## 1. Por qué existe este documento

`mcp-refs/` es **la categoría menos trabajada de las tres**, y paradójicamente la más cercana a lo que FileX va a ser.

**Estado al 20/08/2026 — la fase 1 (lectura) ya está completa:**

| Repo | ⭐ | Leído | Ejecutado |
|---|---:|---|---|
| `servers/filesystem` | 89 685 | ✅ `00-mcp-filesystem.md` | ❌ |
| `video-audio-mcp` | 84 | ✅ `00-mcp-multimedia.md` | ❌ |
| `ffmpeg-mcp-lite` | 26 | ✅ `00-mcp-multimedia.md` | ❌ |
| `image-worker-mcp` | 18 | ✅ `00-mcp-multimedia.md` | ❌ |
| `markitdown_mcp_server` | 86 | ✅ | ✅ **sondeado por protocolo** |
| `kordoc` | 1 748 | ✅ (estructura + `describeError`) | ❌ |

**Queda solo la fase 2**: ejecución selectiva de los que la lectura marcó como prometedores.

Nota histórica que conserva el documento su valor: cuando se escribió, **ninguno de los seis se había ejecutado.** Y hay que deshacer una confusión: las pruebas de MCP se hicieron sobre `markitdown-mcp` (el oficial de Microsoft) y `docling-mcp`, que viven en `repos/ai-engines/`, **no** en esta categoría.

### Lo que eso deja abierto

Todas las reglas de diseño MCP que FileX tiene ahora —devolver asa en vez de contenido, anotar `readOnlyHint`, pocas herramientas bien nombradas— **salen de MCP documentales, donde la salida es texto**. Ninguna se ha validado contra el caso binario.

Y el caso binario es distinto en un punto que importa: **un MP4 convertido no cabe en el contexto ni queriendo**. El patrón de asa deja de ser una optimización de tokens y pasa a ser la única opción física. Aquí hay tres precedentes sin leer.

---

## 2. Corrección: la defensa que dije que había que inventar, ya existe

En `ANALISIS-COMPLETO.md` §6.3 y en `PLAN-ORQUESTADOR.md` §4.6 afirmé que la lista blanca de raíces **"hay que diseñarla desde cero"** porque ninguno de los seis orquestadores la resuelve.

**Es falso, y la fuente estaba en esta misma carpeta sin revisar.** `repos/mcp-refs/servers/src/filesystem/` (MIT, oficial del protocolo, 1 501 líneas) implementa exactamente eso:

| Fichero | Qué aporta |
|---|---|
| `index.ts:45` | `allowedDirectories` — lista blanca de raíces permitidas |
| `path-validation.ts` | Módulo dedicado a validar rutas |
| `path-utils.ts` | `normalizePath`, `expandHome` |
| `roots-utils.ts` (76 líneas) | Gestión del concepto de *roots* del protocolo MCP |
| `index.ts:51-54` | **Resuelve enlaces simbólicos al arrancar** — con comentario de seguridad explícito, y contempla el caso `/tmp` → `/private/tmp` de macOS |

Su comentario en `index.ts:42` explica la sutileza clave: *"We store BOTH the original path AND the resolved path to handle symlinks correctly"*.

**Es la referencia canónica del problema central de seguridad de FileX**, es MIT, y estaba a un `ls` de distancia. ✅ **Ya leída**: el análisis completo está en `analysis/00-mcp-filesystem.md`, e incluye un hallazgo que no se esperaba — sus propios tests documentan una condición de carrera TOCTOU con symlinks, y su manejo de errores **sí es un oráculo de existencia** que filtra la lista blanca completa.

---

## 3. Qué evaluar en cada repo

### 3.1 `servers` (oficial del protocolo) · 89,7k ⭐ · MIT

Implementaciones de referencia: `everything`, `fetch`, `filesystem`, `git`, `memory`, `sequentialthinking`, `time`.

| Componente | Por qué interesa |
|---|---|
| **`filesystem/`** | **Prioridad máxima.** La lista blanca de raíces, la validación de rutas y la resolución de symlinks (§2) |
| `everything/` | Servidor de demostración que ejercita *todas* las capacidades del protocolo. Útil para saber qué existe y FileX no está usando |
| `fetch/` | Cómo la referencia oficial maneja recursos remotos — relevante porque markitdown acepta cualquier URL http y eso es SSRF |

**Pregunta a responder:** ¿qué partes de `filesystem` se pueden portar tal cual a Python, y cuáles dependen de detalles de Node?

---

### 3.2 `video-audio-mcp` · 84 ⭐ · MIT · Python

**El más relevante de los tres de multimedia: declara 27 herramientas** (`@mcp.tool`), más que ningún otro MCP de conversión analizado. Código en `server.py` y `main.py`.

| Componente | Por qué interesa |
|---|---|
| **Las 27 declaraciones de herramientas** | ¿Cómo trocea el dominio de vídeo y audio en herramientas? ¿27 satura la selección del modelo? Contraste directo con las 19 de docling-mcp, que ya se midieron en 5 280 tokens de suelo fijo |
| **El valor de retorno tras convertir un vídeo** | **La pregunta central.** ¿Ruta, base64, resumen? Es la decisión de diseño de FileX y aquí hay un precedente |
| Nombres y descripciones | Cómo se nombra una herramienta cuando el dominio no es texto |

---

### 3.3 `ffmpeg-mcp-lite` · 26 ⭐ · MIT · Python

**El mejor estructurado de los pequeños**, pese a ser el de menos estrellas. Paquete propio en `src/ffmpeg_mcp_lite/`:

```
config.py
server.py
tools/  ->  audio.py · compress.py · convert.py · frames.py · info.py · merge.py
tests/  ->  test_audio.py · test_compress.py · test_convert.py
            test_frames.py · test_info.py · test_merge.py
```

| Componente | Por qué interesa |
|---|---|
| **`tools/` troceado por dominio** | Es la separación que FileX necesita, ya hecha. Contrasta con las 27 herramientas planas de `video-audio-mcp` |
| **`tests/` — un fichero por herramienta** | **Es el activo más valioso del repo.** Ninguno de los otros MCP de conversión tiene suite de pruebas. Sirve como plantilla de las pruebas de FileX |
| `config.py` | Cómo parametriza rutas de binarios y límites |

---

### 3.4 `image-worker-mcp` · 18 ⭐ · MIT · TypeScript

Estructura: `src/{constants,index,server,utils,version}.ts` + `services/` + `tools/` + **`libheif-js.d.ts`**.

| Componente | Por qué interesa |
|---|---|
| **`libheif-js.d.ts`** | Soporte HEIC — el formato de iPhone, presente en el corpus y en cualquier caso de uso real |
| Separación `services/` frente a `tools/` | Distinguir la lógica de conversión de su exposición como herramienta MCP: exactamente lo que FileX quiere |
| Devolución de imágenes | Una imagen *sí* podría devolverse al modelo como contenido. ¿Lo hace? ¿Con qué límite de tamaño? |

---

### 3.5 `markitdown_mcp_server` · 86 ⭐ · MIT · Python · 162 líneas

`src/markitdown_mcp_server/server.py`, 153 líneas. **Ya leído y ejecutado: no expone herramientas.** Declara solo la capacidad `prompts`; `tools/list` devuelve `-32601 Method not found`. Se identifica como `"example" v0.1.0` y lanza `os.system("notify-send ...")` al arrancar, que falla en Windows.

| Componente | Por qué interesa |
|---|---|
| Las 153 líneas enteras | ✅ **Hecho.** El techo real del sector en conversión invocable son 84 ⭐ (`video-audio-mcp`), no estas 86 |
| En qué se diferencia del oficial de Microsoft | Ambos envuelven MarkItDown. Que el de terceros tenga más estrellas que las herramientas serias del sector dice algo del mercado |

---

### 3.6 `kordoc` · 1,7k ⭐ · MIT · TypeScript

**Ya analizado a nivel de código**, y de ahí salió la estimación de que la capa MCP de FileX cuesta como la CLI. Lo que queda es **ejecutarlo**:

| Componente | Por qué interesa |
|---|---|
| `src/cli.ts` (1 205 líneas) y `src/mcp.ts` (1 177) | Verificar en ejecución que las dos superficies comparten núcleo sin divergir |
| Sus 87 esquemas zod | Cómo se describe un parámetro para que lo lea un modelo, no una persona |
| `sanitizeError`, `classifyError`, `KordocError` | Convertir excepciones en mensajes que el modelo pueda usar para corregirse — el problema que docling-mcp resuelve mal (respondió `pip install openai-whisper` al agente) |

---

## 4. Preguntas transversales que solo esta categoría responde

1. **¿Qué se devuelve tras convertir un binario?** Tres precedentes sin leer (`video-audio-mcp`, `ffmpeg-mcp-lite`, `image-worker-mcp`). Todas las reglas actuales de FileX vienen del caso texto.
2. **¿Cuántas herramientas saturan al modelo?** Se midió el coste en tokens (19 herramientas = 5 280 de suelo), pero no el efecto en la *elección* del modelo. `video-audio-mcp` con 27 es el caso extremo disponible.
3. **¿Cómo se agrupa el dominio?** Herramientas planas (`video-audio-mcp`) frente a troceado por módulos (`ffmpeg-mcp-lite`).
4. **¿Cómo se confina el sistema de ficheros?** `servers/src/filesystem` es la referencia oficial (§2).
5. **¿Qué mensaje de error llega al modelo?** `kordoc` tiene clasificación explícita; docling-mcp filtra el `stderr` crudo hacia el contexto del agente.
6. **¿Se puede devolver una imagen como contenido?** El único caso donde el patrón de asa podría no ser obligatorio.

---

## 5. Cómo probarlos

### Fase 1 — lectura de código · ✅ **COMPLETADA el 19/08/2026**

> Ejecutada con 2 agentes. Entregables: `analysis/00-mcp-filesystem.md` (56 KB) y `analysis/00-mcp-multimedia.md` (90 KB). Pendiente consolidarlos en `analysis/00-mcp-componentes.md`.

Cubre los seis repos y responde casi todas las preguntas de §4. **Es lo que aporta más por unidad de esfuerzo**, y puede correr en paralelo con cualquier otro trabajo.

**Entregable:** `analysis/00-mcp-componentes.md`, con una tabla **componente → repo → veredicto** (copiar tal cual / adaptar / solo como referencia / descartar).

Volumen a leer: `filesystem` 1 501 líneas · `video-audio-mcp` 2 494 · `image-worker-mcp` 3 400 · `ffmpeg-mcp-lite` 1 204 · `markitdown_mcp_server` 162.

### Fase 2 — ejecución selectiva

Solo de los que la fase 1 marque como prometedores. Todos son Python o Node, ligeros, sin GPU.

- **Configuración MCP de proyecto**, en `D:\Work\research\FileX\.mcp.json`. **Jamás la global del usuario.**
- **Un venv por servidor Python**: ya se sabe que `mcp~=1.8.0` y `mcp>=2.0.0` no coexisten.
- **Medir con `tiktoken`** cuántos tokens devuelve cada herramienta tras convertir un vídeo del corpus, para poder comparar con los 85 259 de markitdown frente a los 36 de docling.
- **Probar `../../` y rutas absolutas** contra cada servidor, y contrastar con lo que hace `filesystem`.

**Entregable:** `bench/mcp-refs-ejecucion.md`.

---

## 6. Orden y contención

**Ninguno de los seis necesita GPU.** No compiten con los agentes de motores de IA que describía `AGENTES-PRUEBAS-PENDIENTES.md` (documento a su vez superado, ver su cabecera), así que **podían correr en paralelo con ellos**.

| Prioridad | Qué | Por qué |
|---|---|---|
| **1ª** | Leer `servers/src/filesystem` | Resuelve el problema de seguridad central de FileX, y creí erróneamente que no existía |
| **2ª** | Leer los tres MCP de multimedia | Son los únicos precedentes del caso binario |
| **3ª** | Leer `ffmpeg-mcp-lite/tests/` | Plantilla de suite de pruebas; nadie más la tiene |
| **4ª** | Ejecutar los prometedores | Solo tras la fase 1 |
| **5ª** | `markitdown_mcp_server` y `everything` | Contexto de mercado y de protocolo |

**Si solo se hace una cosa: leer `servers/src/filesystem`.** Es MIT, es la referencia oficial, y corrige una carencia que este análisis dio por insalvable.

---

## 7. Reglas para el agente que lo ejecute

1. **Un único informe por fase**, en la ruta indicada. No tocar `analysis/` salvo el fichero propio, ni otros informes de `bench/`, ni `corpus/`, ni `repos/`.
2. **Configuración MCP solo de proyecto.** Nunca `~/.claude.json`.
3. **Venv separado por servidor Python.** No tocar `.venv-ai`, `.venv-paddle` ni `.venv-mcp-md`.
4. **No usar la GPU.** Si algo la necesitase, adquirir el lock de `bench/lib/harness.sh` y soltarlo pronto.
5. **Dos intentos por problema**, luego documentar el error exacto y seguir.
6. **El veredicto por componente es el entregable**, no el resumen del repo. La pregunta es siempre *"¿qué pieza de aquí se lleva FileX, y en qué estado?"*.

---

## 8. Documentos relacionados

| Ruta | Para qué |
|---|---|
| `analysis/00-mcp-patrones.md` | Reglas MCP actuales, derivadas del caso texto |
| `analysis/kordoc-y-mcps-menores.md` | Lo poco que se sabe hoy de esta categoría |
| `bench/mcp-ergonomia.md` | Las medidas sobre markitdown-mcp y docling-mcp (16 reglas) |
| `AGENTES-PRUEBAS-PENDIENTES.md` | Los cuatro agentes de motores de IA. **También superado**: su justificación se refutó y sus marcas están invalidadas (lo dice su propia cabecera) |
| `PLAN-ORQUESTADOR.md` §4.4 y §4.6 | Dónde encajan estos hallazgos en la construcción |

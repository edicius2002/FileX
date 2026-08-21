# FileX — Los huecos competitivos, reevaluados

**Fecha:** 19 de agosto de 2026
**Estado:** revisión crítica tras la fase de ejecución

> Este documento sustituye la lista original de cuatro huecos. Aquella se formó con **metadatos de GitHub y lectura de código**; la fase de ejecución la desmintió parcialmente. Dos huecos se debilitaron, uno hubo que reformularlo, y **el diferenciador más fuerte no estaba en la lista**.
>
> Cada afirmación va marcada como **MEDIDO** (hay dato en `bench/`) o **PENDIENTE** (no se ha comprobado).

---

## Resumen del reordenamiento

| Nuevo # | Anterior # | Diferenciador | Veredicto |
|---:|---:|---|---|
| **1** | — | **Verificación obligatoria de la salida** | **Nuevo. El más fuerte de todos** |
| **2** | 1 | Grafo con coste por arista | Real, pero reformulado |
| **3** | 3 | MCP multi-modal en un solo servidor | Real, mucho más estrecho de lo dicho |
| **4** | 2 | NVENC en vídeo | Real, pero solo importa en lote |
| **5** | 4 | OCR en GPU | Degradado: ya no es foso, es higiene |

**Los tres criterios** con que se juzga cada uno: ¿nadie lo hace? ¿es barato? ¿lo nota el usuario? **Solo el nº 1 cumple los tres.**

---

## 1 · Verificación obligatoria de la salida — **el hueco real**

No estaba en la lista original porque **solo aparece al ejecutar**. Leyendo código no se ve.

### Evidencia — toda MEDIDA

| Fallo observado | En quién | Cómo se verificó |
|---|---|---|
| `.avif` que en realidad es un **PNG**, entregado con estado "Done" | ConvertX | Bytes mágicos `89 50 4E 47`; 42 855 B frente a los 3 137 B del AVIF real |
| **Pierde una pista de audio**, en silencio | **ConvertX y SnapOtter** | `ffprobe`: 2 pistas de origen → 1 de salida, éxito reportado |
| Degrada 16 → 8 bits **sin avisar ni ofrecer parámetro** | SnapOtter | Comparación contra la referencia nativa, que sí conserva los 16 bits |
| PDF→imagen a **72 ppp fijos**; audio a **64 kbps** pidiendo 192 | ConvertX | Inspección de las salidas |
| `dasel` roto: conversiones **declaradas e inalcanzables** | ConvertX | Sintaxis v1 contra binario v2 |
| Cadena vacía con **`isError: false`** ante un PDF escaneado | markitdown-mcp | El agente concluye que el documento está vacío |
| Afirma usar la GPU **mientras corre en CPU** | onnxruntime-gpu 1.29.0 | `get_device()` devuelve `'GPU'`; las sesiones son CPU |

**Es sistémico, no anecdótico.** Siete fallos independientes, en seis proyectos distintos, todos del mismo tipo: **el software declara éxito sobre un resultado incorrecto**.

### Por qué es el más fuerte

- **Nadie lo hace.** Ninguno de los seis orquestadores verifica su salida.
- **Es barato.** Firma real del fichero, `ffprobe` de flujos, y comparación de propiedades declaradas contra medidas.
- **Lo nota el usuario.** Hoy recibe ficheros corruptos que su herramienta le dice que están bien. Los otros cuatro huecos son mejoras de rendimiento o de alcance; este es corrección.

### Corolario contraintuitivo — MEDIDO

**Un recurso alternativo sin verificación es peor que no tenerlo.** ImageMagick dentro de ConvertX emite un *warning* con código de salida 0 y devuelve el formato origen: convierte un fallo honesto en uno silencioso. Con `vips`, el mismo caso **falla limpiamente**.

### Qué está PENDIENTE

- **El coste real de implementar el contrato de verificación.** Se afirma que es bajo; no se ha construido.
- **El coste en tiempo de verificar cada conversión.** Un `ffprobe` por salida no es gratis en lote.

### Base ya disponible — MEDIDA

`bench/salidas-referencia/referencia.json`: **46 reglas de regresión**, 53 salidas caracterizadas, 39 órdenes reproducibles y **17 pérdidas catalogadas** que distinguen *pérdida inevitable* de *fallo del motor*. Es el patrón oro contra el que verificar.

---

## 2 · Grafo con coste por arista — real, pero el número lo sobrevende

### Lo MEDIDO

- **0 de 7 orquestadores implementan búsqueda de camino.** Barrido de `dijkstra|shortest.?path|conversion.?graph|multi.?hop|find.?path` sobre los siete árboles: cero coincidencias reales.
- **152 584 → 447 398 pares** alcanzables con hasta 3 saltos: **2,93×** con los mismos motores. Calculado sobre las tablas reales de los 20 adaptadores.
- `epub→png`, `docx→webp` y `tex→docx` son **imposibles hoy** y salen en 2 saltos.
- El único indicio de que la necesidad existe está resuelto **a mano dentro de un adaptador**: `transmute/backend/converters/libreoffice_convert.py:333` — *"Image output via PDF intermediary"*.
- **ConvertX elige mal el motor**: en `png→jpg` gana ffmpeg teniendo vips, ImageMagick y GraphicsMagick disponibles, por un `break` que solo rompe el bucle interno (`main.ts:213-229`).

### Lo PENDIENTE — y es lo que sobrevende la cifra

- **Qué fracción de los 447 398 caminos produce una salida aceptable. Nunca se midió.** El 2,93× es alcanzabilidad, no fidelidad: un camino de 3 saltos que rasteriza destruye el texto seleccionable.
- **Si esas conversiones se piden de verdad.** `epub→png` es nicho.

### La reformulación honesta

Nuestra propia evidencia golpea la tesis original desde otro lado: **ConvertX ya "alcanza" conversiones que entrega falsas**. Si el sector falla en producir correctamente lo que ya declara, ampliar el alcance ataca el problema equivocado.

**Lo que se sostiene del grafo es la selección correcta con coste explícito** — que arregla por construcción el bug de ConvertX. **El multi-salto es la propina, no la tesis.**

---

## 3 · MCP multi-modal en un solo servidor — real, mucho más estrecho

### Se degradó dos veces durante la investigación

**Primera:** afirmé que ningún conversor grande expone MCP. **Falso.** Stirling-PDF (89,9k ⭐) tiene un servidor MCP completo en `app/proprietary/`, con catálogo autodescubierto, ejecutor, autenticación por clave de API y configuración de seguridad. **Está detrás de una suscripción de pago** — MEDIDO leyendo su `LICENSE` y su árbol.

**Segunda:** el patrón de asa no es un hallazgo de FileX. **docling-mcp ya lo implementa bien**, con anotaciones `readOnlyHint`/`destructiveHint` correctas y liberación de memoria. Es de IBM y es MIT.

### Lo que SÍ sobrevive — MEDIDO

**Los servidores no coexisten.** `markitdown-mcp` pide `mcp~=1.8.0` y `docling-mcp` pide `mcp>=2.0.0`; negocian versiones distintas del protocolo (2024-11-05 frente a 2025-11-25). **Hubo que darle un entorno virtual a cada uno.**

Quien quiera cubrir documentos, vídeo, audio e imágenes acaba con **cuatro servidores incompatibles**, y los tres de multimedia tienen 84, 26 y 18 estrellas.

**El hueco no es "falta un MCP". Es "faltaría uno que cubra todas las modalidades a la vez".**

### Cifras de apoyo — MEDIDAS

- **85 259 tokens frente a 36** para el mismo PDF de 60 páginas: **~2 400×**. El volcado ocupa el 42,6 % de una ventana de 200 K.
- **19 herramientas = 5 280 tokens de suelo fijo**; limitando al grupo `conversion`, 880 tokens y 3 herramientas (−83 %).
- En documento pequeño **el asa pierde** (32 frente a 56 tokens): tiene coste fijo.

### Lo PENDIENTE — y no es menor

**Todas las mediciones vienen de MCP documentales, donde la salida es texto. El caso binario no se ha probado.**

- ~~**Qué devuelve un MCP tras convertir un vídeo.**~~ **RESUELTO (20/08/2026).** Los tres precedentes se ejecutaron. El asa cuesta **32-72 tokens con independencia del tamaño** (15,5 MB → 32 tokens). Pero `image-worker-mcp` **sí devuelve la imagen entera**, como base64 dentro de un `TextContent` — un patrón que la regla de FileX no cubría. Ver `RESULTADOS-MCP.md` §3.
- **Si 27 herramientas saturan la elección del modelo.** **SIGUE PENDIENTE.** Se midió el catálogo (**7.964 tokens**, el techo del sector) y su solapamiento (**39,7 % redundante**), pero el análisis es estructural, no conductual. El efecto sobre la *elección* del modelo no se ha medido en todo el proyecto.
- ~~**Si una imagen puede devolverse como contenido.**~~ **RESUELTO: no hay umbral que valga la pena.** A **0,93 tokens por byte**, el punto de rentabilidad está en 1-2 KB. Una miniatura de 10 KB cuesta 132× su ruta. La firma de las herramientas de FileX no cambia.

Ver `RESULTADOS-MCP.md`.

---

## 4 · NVENC en vídeo — real, pero solo importa en lote

### Lo MEDIDO (medianas de n=9)

- **0 de 7 orquestadores lo usan**, ni siquiera los que ya integran FFmpeg.
- **HEVC: 8,39×** (16 598 → 1 978 ms). H.264: **2,74–2,98×**. 4K: 2,67×.
- `hevc_nvenc` cuesta lo mismo que `h264_nvenc`, mientras `libx265` es 3× más lento que `libx264`: **por eso HEVC es donde la GPU se paga**.
- `av1_nvenc` **falla con `No capable devices found`** pese a aparecer en `ffmpeg -encoders`: Ampere no tiene codificador AV1.

### Lo que lo acota — también MEDIDO

- **NVENC se pasa un 8–11 % del bitrate pedido** (2 214 kbps cuando se piden 2 000), frente al +1,3 % de x264.
- **La tubería GPU completa no aporta nada**: −13 % a +3 %, y **−34 % con escalado**.
- Para una conversión suelta, 16 s frente a 2 s **no cambia el comportamiento de nadie**.

### Lo PENDIENTE

- **Rendimiento en lote sobre una carpeta real** — que es el único caso donde esto decide algo. Nunca se probó.

**Es real y baratísimo, pero no es por lo que alguien elegiría FileX.**

---

## 5 · OCR en GPU — degradado: ya no es foso

### Por qué se debilitó

Se formuló cuando parecía exigir Surya, gestión de VRAM y sidecar dedicado. **Se resolvió con un parámetro de una librería MIT que ya estaba instalada**: Docling + RapidOCR con `backend="torch"`, reutilizando el torch existente. **Coste de infraestructura GPU: cero.**

Si un ajuste de configuración cierra el hueco, **no es una ventaja defendible**: cualquiera lo replica en una tarde.

### Lo MEDIDO

| Motor | Aceleración | VRAM | CER dif. 2 | CER dif. 3 |
|---|---:|---:|---:|---:|
| RapidOCR `backend=torch` | 3,5–4,2× | +1 344 MiB | 1,3 % | **65,8 %** |
| PaddleOCR | 8,9–11,7× | +1 486 MiB | 0,0 % | **75,9 %** |
| EasyOCR | 12,4–17,0× | +2 079 MiB | 43,0 % | **57,0 %** |

Dos matices que lo encogen más:

- **La ganancia real es 3,9×** comparando el mejor CPU (RapidOCR, 763 ms) contra el mejor GPU, no los 17× de titular. Un motor lento que se acelera mucho sigue siendo lento.
- **En la dificultad 3 fallan los tres.** El OCR acelerado hace más rápido el caso fácil; **no resuelve el difícil**.

### Lo que queda

Un hueco de **producto**, no técnico: SnapOtter lo bloquea activamente (`ocr-runtime-dispatcher.ts:1033` lanza excepción si `device !== "cpu"`) y OCRmyPDF depende de Tesseract. **Nadie lo ofrece, pero cualquiera podría.**

### Lo PENDIENTE — y podría reabrir el hueco

- **OCRmyPDF como preprocesador**, no como motor: `--deskew`, `--clean`, `--remove-background` antes de pasar a RapidOCR o PaddleOCR. **Es el único candidato para la dificultad 3**, y no se ha probado.
- **Reintento de Surya** por `SURYA_INFERENCE_BACKEND=llamacpp` o `VLLM_GPU_MEMORY_UTILIZATION=0.5`. Solo se probó su backend por defecto.
- **MinerU con el extra `[vlm]`**, compatible con el torch instalado.

Ver `AGENTES-PRUEBAS-PENDIENTES.md`. **Si el preprocesado rescata la dificultad 3, la conclusión no será "añadir OCRmyPDF" sino "añadir una etapa de preprocesado antes de cualquier OCR"** — que es un hallazgo de arquitectura y sí sería defendible.

---

## Qué significa para el plan de construcción

**No cambia el orden de los hitos.** `PLAN-ORQUESTADOR.md` §7 ya sitúa el contrato de verificación en el hito 3, **antes que MCP**, precisamente porque sin él todo lo anterior puede mentir. Ese orden resulta ser el correcto por una razón más fuerte de la que se creía.

**Lo que cambia es el argumento de FileX.** No es *"convierte más cosas más rápido"* — eso es discutible y en parte replicable. Es:

> **Es el único que garantiza que lo que te entrega es lo que pediste.**

Los otros cuatro diferenciadores son apoyos de ese argumento, no el argumento.

---

## Índice de la evidencia

| Afirmación | Dónde está el dato |
|---|---|
| Los 7 fallos de verificación | `bench/competidores.md`, `bench/mcp-ergonomia.md`, `bench/gpu-fase2.md` |
| Patrón oro y 46 reglas de regresión | `bench/referencia-nativa.md`, `bench/salidas-referencia/referencia.json` |
| 0 de 7 con búsqueda de camino · el 2,93× | `analysis/00-hueco-multisalto.md`, `analysis/00-matriz-formatos.md` |
| El bug de despacho de ConvertX | `analysis/ConvertX.md` |
| MCP de pago de Stirling-PDF | `analysis/Stirling-PDF.md` |
| 85 259 frente a 36 tokens | `bench/mcp-ergonomia.md` |
| NVENC, bitrate y tubería GPU | `bench/gpu-fase1.md` |
| Los tres motores de OCR | `bench/gpu-fase2.md` |
| Lo pendiente de OCR | `AGENTES-PRUEBAS-PENDIENTES.md` |
| Los resultados de MCP | `RESULTADOS-MCP.md` |

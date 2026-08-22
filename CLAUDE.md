# CLAUDE.md — reglas de trabajo en FileX

Proyecto de investigación en español. **Escribe todo en español**, incluidos informes y comentarios.

---

## 1. Nunca toques esto

| Qué | Por qué |
|---|---|
| **`.wslconfig`** | Los 2 vCPU y 1,9 GiB de la VM de Docker son decisión deliberada del usuario, con sus motivos escritos en comentarios |
| **`.venv-ai/`, `.venv-paddle/`, `.venv-mcp-md/`, `.venv-marker/`** | Entornos CUDA funcionales y frágiles. **Usarlos para ejecutar sí; instalar en ellos, jamás** |
| **El código fuente de `repos/`** | Son clones de referencia. Instalar dependencias o construir dentro está bien (`repos/` está en `.gitignore`); editar su código no |
| **La sesión de escritorio remoto** | Está activa a propósito. No la cierres |
| **`~/.claude.json`** | Configuración MCP **solo de proyecto**, en `D:\Work\research\FileX\.mcp.json` |
| **`bench/salidas-referencia/referencia.json`** | Es el patrón oro: se lee, no se toca |
| **`bench/scripts/mcp_probe_bin.py`, `bench/salidas-mcp/mcp_probe.py`** | Arneses compartidos. Si necesitas una variante, cópiala a tu directorio de salidas |

**Un fichero de salida por agente.** Dos agentes no escriben nunca el mismo fichero.

**Y el lock de GPU no te protege de la máquina, solo del proyecto.** `gpu_acquire`/`gpu_release` usan un fichero **dentro de `bench/`**: excluye a otros agentes de FileX y **no ve nada más**. Una sesión de Claude en `D:\Work\research\ASR` ocupando **11 754 de 12 288 MiB** dejó una tanda **12 minutos sin procesar una sola imagen** (`bench/ppp-y-normalizacion.md` §1.3). **Si la GPU va lenta y el lock está libre, mira los PID antes de culpar al arnés.** Que el lock pase a ser de máquina (`%TEMP%` o mutex con nombre) es **PENDIENTE**.

## 2. Entorno verificado — no lo recompruebes

RTX 3060 12 288 MiB (compute 8.6, driver 572.61) · 12 núcleos · Windows 10 · Docker 29.4.3 + WSL2 (Ubuntu) · Python 3.11.9 · Node 22.23.2 · Go 1.22.5.

**Nativos:** `ffmpeg` N-121159 (gpl, x264, x265, cuda-llvm), `magick` 7.1.2 Q16-HDRI, `gswin64c` 10.07.

**NO instalados:** vips, LibreOffice, Pandoc, qpdf, Calibre, Inkscape, DuckDB. **No hay gestor de paquetes** (ni winget, ni choco, ni scoop) — lo que falte va en contenedor, no instalado a mano.

**Matices que cuestan tiempo si no se saben:**
- `tesseract.exe` **existe** en `C:\Program Files\Tesseract-OCR\` pero **no está en el PATH**, y solo trae `eng`+`osd`.
- **Ghostscript 10.07 lleva Tesseract y Leptonica compilados dentro**, lo que habilita `-sDEVICE=ocr` y `pdfocr*` — pero **sin datos de idioma**: falla con `Tesseract couldn't load any languages!` si no fijas `TESSDATA_PREFIX`.
- **VRAM realmente disponible: ~8,7 GB de los 12.** El escritorio ocupa ~2,5 GB de forma permanente. NVENC y NVDEC sí están libres.
- **`spa.traineddata` existe en `C:\Program Files\PDFgear\tessdata\`** (2 294 433 B, con otros 15 idiomas). **Lo puso PDFgear, no este proyecto.** ~~FileX tendría que distribuir 2–4 MB por idioma.~~ **Ya no, para la vía de contenedor — MEDIDO** (`bench/invocacion-aristas.md` §9): **ocho líneas de Dockerfile, 28,1 s de construcción y +50 MB (+0,9 %)** añaden `qpdf 12.4.0` y `Tesseract 5.5.0` a la imagen de ConvertX, y **`tesseract-ocr-spa` trae el `spa` incluido**. Distribuir `tessdata` a mano solo sigue haciendo falta para el Ghostscript **nativo** de Windows.

**Contenedores:** SnapOtter `:1349` (`admin` / `<CONTRASENA-REDACTADA>`), ConvertX `:3100`, Gotenberg `:3200`.

**Lo que NO hay en Windows sí está en la imagen `filex-convertx`** (Debian forky/sid) — comprobado con `command -v`: `soffice`, `libreoffice`, `pandoc`, `ebook-convert` (Calibre), `vips`, `inkscape`, `resvg`, `magick`, `ffmpeg`, `gs`, `assimp`, `dasel`, `potrace`, `vtracer`, `dvisvgm`, `xelatex`, `msgconvert`, `cjxl`, `djxl`, `heif-enc`, `python3`. **Ausentes: `qpdf` y `tesseract`** — son los dos únicos motores que habría que añadir a una imagen, **y ya está medido lo que cuesta: 8 líneas, 28,1 s, +50 MB** (imagen `filex-c13`, `bench/salidas-invocacion/Dockerfile.c13`).

## 3. Cómo se mide aquí

- **Medianas de n≥9**, con `bench/lib/harness.sh`: `measure`, `gpu_acquire`/`gpu_release`, `peak_vram`.
- **Lock de GPU obligatorio** para todo lo que use la tarjeta. Solo un agente a la vez.
- Con la sesión remota activa **todo sale etiquetado `SUCIA`**. Es estructural, no un fallo.
- **Medir con ruido no es medir**: una tanda que coincidió con una descarga dio un error de **7,4×**.
- **Dos testigos de ruido, siempre: uno mide deriva, el otro nivel.** El bucle monohilo de Python detecta la **deriva dentro** de la tanda; un lanzamiento de proceso (`ffprobe -version`) detecta el **nivel** de carga de la máquina. **El monohilo solo es ciego a la contención multinúcleo**: con 12 núcleos cabe en uno libre y etiquetó `limpia` una tanda que salió **×6,8** sobre el mismo control (879 ms frente a 129 ms). **Van ya tres casos en un día**: V1 (×6,8 etiquetado `limpia`), P1 (deriva 0,83 «sin deriva» mientras el testigo de proceso medía **×7,18**) y P3 (**×94,6**, con `ffprobe -version` agotando un timeout de 60 s). **Ponle tope al propio testigo** (20 s, devolviendo el tope y marcando `SUCIA`): un testigo que puede tumbar la medición no es un testigo.
- **Las cifras absolutas de tandas distintas no son comparables; las relativas dentro de una tanda, sí.** La misma suite de fidelidad sobre las mismas 53 salidas dio **46 332 ms** en V1 y **70 693 ms** en P3, con dos agentes más trabajando. **Cuando muevas un porcentaje de una tanda, muévelo; cuando muevas un milisegundo, anota la salvedad.**
- **Y hay un TERCER sesgo, que no es de ruido sino de SEMILLA.** Con dos semillas de markdown que empezaban por un título, **42 formatos de pandoc parecían tener marcador**; con una tercera que empieza por prosa, **ninguno lo tiene** (`bench/firmas-contrato.md` §2.3). Los dos testigos de ruido no lo habrían visto nunca. **Cuando midas una propiedad del FORMATO, varía la entrada; si no, estás midiendo tu entrada.**
- **Timeouts explícitos en todo.** No dejes procesos colgados: estos motores dejan huérfanos vivos 13 minutos.
- **Dos intentos por problema**, luego documenta el error exacto y sigue. **Nada de bucles de reintento.**

**Marca cada afirmación MEDIDO o PENDIENTE.** No es opcional: es lo que hace útil este repositorio.

**Reporta los fallos como fallos.** Un «no se pudo instalar» documentado mide el coste real de integración, que es justo lo que hay que saber. Y **refutar una conclusión propia es el resultado más valioso que puedes traer** — varios de los mejores hallazgos aquí son autocorrecciones.

## 4. Trampas ya pagadas — no vuelvas a caer

**De medición:**
1. **El «alfa trivial»**: `corpus/imagen/tipico.png` declara canal alfa pero es **enteramente opaco**. Solo exige conservación si `min(alfa) < 1,0`. Usa `alpha.png` para el caso real.
2. **Menor tamaño ≠ mejor conversión.** El GIF con paleta genérica pesa un 35 % *menos* que el bueno.
3. **Opus fuerza 48 kHz** y convierte 8,000 s en 8,0065 s: toda tolerancia por debajo de ±10 ms da falsos fallos.
4. **`txtwrite` emite 1-3 caracteres de basura** en PDF sin texto: el umbral de «conserva texto» es **≥10**, no >0.
5. **`magick compare -metric SSIM` devuelve 0 para imágenes idénticas** en esta build. Usa **PSNR y RMSE**.
6. **No sobremuestrees al rasterizar.** `escaneado_d2/d3.pdf` tienen imagen incrustada a **100 ppp nativos**; el arnés de la fase 2 los rasterizaba a 200 y ese ×2 de interpolación **inventó** las marcas de «fallan los tres motores» en dificultad 3. A ppp nativos, PaddleOCR resuelve d3 con **2,5 % de CER**.
7. **Windows Defender infla el primer arranque** de un binario recién compilado (41 → 110 ms). Calienta antes de medir.
8. **NO HAY UNA REGLA GLOBAL DE ppp: hay una por motor.** Las **dos** versiones anteriores de esta trampa están refutadas (`bench/ppp-y-normalizacion.md` §2, barrido de 17 puntos y 24 celdas de control):
   - ~~`clamp(nativos, 100, nativos×1,4)`~~ — refutada por `d4` en su día.
   - ~~`clamp(nativos, 100, 200)` — techo absoluto~~ — **refutada ahora, y por dos motivos.** (a) **Los ppp no son la unidad**: el mismo JPEG reempaquetado en páginas de 100/200/400 ppp da, **a los mismos ppp**, CER de **19,13 / 19,63 / 36,24 %**, y **a los mismos píxeles coincide a la centésima** en las 24 celdas. (b) Su techo **solo actúa bajando**, y bajar cuesta **12,08 puntos** (`d4` de 200 a 100 ppp: RapidOCR+R6 de 18,62 % a 30,70 %); además el caso que lo motivó —`d4` a 280 ppp— **es un punto que la regla relativa nunca produce**, porque `clamp(200, 100, 280) = 200`.
   - **Tampoco es una anchura fija en píxeles:** PaddleOCR se rompe en `d4` a **1 812 px** y **no** se rompe en `d4c` a 2 070 ni en `d4f` a 2 587.
   > **Lo vigente: `ppp_ocr = min(max(nativos, 100), nativos × 1,25) × k(motor)`, con `k` MEDIDO por motor** — ×1,25 PaddleOCR, ×1,00 RapidOCR+R6 y EasyOCR, ×1,50 Tesseract (n=1, P2). **Siete configuraciones sobre el mismo documento dan óptimos entre ×0,50 y ×1,80.** Y la elección **vive en el adaptador del motor, no en el orquestador**.
   - **Sí queda una regla global, y es de VRAM, no de precisión:** barrer hasta 400 ppp llevó a PaddleOCR a **11 942** y a EasyOCR a **12 037 de 12 288 MiB, sin dar error**. Hay que poner **algún** límite aunque no exista un techo de calidad universal.
   - **Y el mecanismo, sondeado en ejecución:** `Global.max_side_len: 2000` (`rapidocr/config.yaml:10`) hace que **por encima de 233 ppp RapidOCR reciba el array idéntico**; PaddleOCR no recorta (`limit_side_len=64, limit_type=min`). **Deducirlo del código de PaddleX daba lo contrario** y quedó documentado como error: es *«sondear en ejecución, no deducir»* otra vez.
9. **Con 79 caracteres de referencia no puede haber gradiente** aunque el documento lo tenga: cada carácter vale 1,27 puntos de CER. `escaneado_d4` usa **610** y cuantiza a 0,16.
10. **`ocr_eval.py` es ciego a las tildes** (`NFKD` + descarte de combinantes). Oculta **6,3 puntos** de CER en `eng` sobre castellano y **155 caracteres de error en 28 celdas**. Para castellano, copia el evaluador y conserva `[a-z0-9áéíóúüñ ]`.

11. **CPU y GPU NO dan la misma salida.** «Idéntica carácter a carácter» está **refutado**: **5 de 21 celdas difieren**, y la CPU es mejor en dos y peor en tres. En la zona de degradación el dispositivo cambia el resultado. **Fija el dispositivo en toda regresión de OCR.**

**De entorno:**
12. **`pip install surya-ocr` degradó torch de `2.6.0+cu124` a `+cpu` sin un solo error.** Verifica `torch.cuda.is_available()` en `.venv-ai` **después de cada instalación**.
13. **`onnxruntime-gpu` 1.29.0 exige CUDA 13** y cae a CPU en silencio. Usa **1.22.0**. Y comprueba `session.get_providers()`, **nunca `get_device()`**, que devuelve `'GPU'` mientras corre en CPU.
14. **`mcp~=1.8.0` y `mcp>=2.0.0` no coexisten** en un venv. Un venv por servidor.
15. **Surya 0.22.1 lanza un contenedor vLLM** que reserva el 85 % de la VRAM y se cuelga **sin excepción**. Pon timeout: no llegará un error.
16. **Clonar en Windows** necesita `git -c core.longpaths=true` para algunos repos.
17. **Cuando el motor y el modelo vienen de proyectos distintos, comprueba que el preprocesado que aplica el motor es el que declara el fichero de configuración del modelo — y luego mide si corregirlo mejora, porque no siempre.** RapidOCR 3.9.2 normaliza con `mean=std=0,5` mientras el `inference.yml` que Baidu distribuye con el modelo declara ImageNet: **72,2 puntos de CER**, sin un solo error por pantalla. Docling hereda el defecto. **La segunda mitad la añade `bench/ppp-y-normalizacion.md` §3.5: los OCHO `inference.yml`, de PP-OCRv3 a PP-OCRv6, declaran ImageNet y RapidOCR aplica 0,5 a los ocho — el desajuste es universal, el daño no.** Aplicar la corrección a ciegas **empeora 12 de 42 celdas**, con **+42,50 puntos** en `PP-OCRv4 mobile` sobre un documento limpio del patrón oro. **Devolverle al modelo lo que su propio fichero declara es una hipótesis, no una solución: hay que medirla checkpoint por checkpoint.** Solo `PP-OCRv6 small` sale con **0 regresiones en 15 documentos**.
18. **`-sOCRLanguage=osd` revienta Ghostscript con `0xC0000005`** y **no devuelve código de error**. **El idioma de OCR sale de lista blanca, nunca de la entrada del usuario.**

**De herramienta:**
19. **Los heredocs de shell se comen los backslashes** en este entorno. Para generar JSON con rutas de Windows, **escribe un script de Python** y usa barras normales (`D:/Work/...`), que Python acepta.
20. **`git gc` sobre este repo tarda más de 2 minutos.** Lánzalo en segundo plano y **no borres los `tmp_pack_*` mientras haya un `git.exe` vivo**: estarías corrompiendo el repack en curso.
21. **Hay motores que escriben fuera del destino, en el `cwd` del proceso.** `ffmpeg -i x out.mpd` deja los segmentos DASH ahí; `magick … out.html` deja un `_map.shtml`. **Trabaja siempre en un directorio desechable** y **lístalo antes y después**: aparecieron 33 ficheros no pedidos en la raíz del repositorio.
22. **`SOURCE_DATE_EPOCH` no hace reproducible un PDF de ImageMagick**: estampa `/CreationDate` igual. El JPEG intermedio sí lo es. Y `+noise Gaussian` **exige `-seed`** o el corpus no se reproduce.
23. **Este ImageMagick es Q16-HDRI y escribe los crudos a 16 bits por canal.** Un `.rgb` de 64×48 ocupa **6 bytes por píxel**, no 3. Releerlo con `-depth 8` **no falla**: consume la mitad del fichero, entrega **la geometría exacta pedida** y **píxeles basura**. **Pasa los cuatro puntos del contrato** (`bench/invocacion-aristas.md` §4.1). Deriva la profundidad de **bytes ÷ píxeles** y elige por **RMSE**, no por `rc=0`.
24. **Comparar una salida en gris contra una referencia en color mide la pérdida del formato, no la de la invocación.** `gray`, `graya` y `mono` dan RMSE 0,35–0,42 contra el original y **exactamente 0,000000** contra su referencia ideal degradada (`-colorspace Gray`, `-monochrome`). Sin esa columna, tres recuperaciones buenas se cuentan como destruidas (ídem §4.2).

## 5. Reglas de diseño no negociables

Salen de la evidencia y están desarrolladas en `PLAN-ORQUESTADOR.md` §5 y `RESULTADOS-MCP.md`:

- **Invocar motores como proceso separado, sin shell**, con argumentos en array, y **`stdin=DEVNULL`**. El orden importa: `stdin=DEVNULL` primero, las banderas (`-y`, `-nostdin`) después — una disciplina que hay que recordar en cada punto de invocación no es una defensa.
- **Verificar la salida siempre.** Firma real, flujos, propiedades declaradas, **propiedades pedidas frente a obtenidas** (sin este cuarto punto, un redimensionado no solicitado pasa los otros tres) **y —quinto— que el motor no escribió nada fuera de lo declarado** (`ffmpeg -i x out.mpd` deja 528 KB de segmentos DASH en el `cwd` y entrega 1,2 KB inútiles).
- **El contrato juzga la declaración de la salida; el contenido que desaparece sin dejar rastro necesita fidelidad.** `resvg` devuelve `rc=0`, un PNG válido, con la geometría exacta pedida y **sin una sola letra**: **pasa los cuatro puntos**. **Formulación precisa, ya MEDIDA** (`bench/contrato-quinto-punto.md` §4.4, §5): *el contrato atrapa la pérdida cuando el contenido perdido está **declarado en metadatos** —filas, cabecera de un CSV, pistas, páginas—, porque la sonda ya los lee; necesita fidelidad cuando el contenido solo existe como **píxeles o muestras**.* La familia tiene **al menos cinco miembros** y el contrato atrapa **uno**.
- **El punto 5 es el único del contrato que NO se puede verificar a posteriori.** Hay que estar mirando cuando el motor escribe: sin censo, **49 de las 53 salidas del patrón oro bajan de `ok` a `ok_parcial`**. **La verificación vive dentro de la conversión, no es un paso posterior.**
- **El confinamiento es un directorio de trabajo desechable por conversión, no solo una ruta validada.** Listarlo al terminar y borrarlo entero.
- **Verificar leyendo CABECERAS en proceso, no con `ffprobe`.** Con subprocesos, en el 38 % de los casos verificar cuesta más que convertir; en proceso cuesta el 0,032 %. **Pero «en proceso siempre gana» es FALSO en cuanto hay que recorrer píxeles — MEDIDO** (`bench/contrato-quinto-punto.md` §4.3): `magick` hace la misma medida de tinta en **138 ms** donde el lector en proceso tarda **2 834** sobre 1920×960. **Son dos regímenes: cabeceras y rasters pequeños en proceso (145× a favor); a partir de ~0,1 Mpx, la sonda externa.**
- **Sondear capacidades en ejecución, no deducirlas.** `av1_nvenc` aparece listado y no funciona. Y `paddlex` **lista sus ocho detectores con `limit_type='max'`** mientras la sonda mide `limit_type='min'` en la ruta que usa `paddleocr` 3.7.0.
- **Fuerza lo que el motor no puede deducir; no fuerces lo que ya deduce bien.** MEDIDO: forzar el códec por defecto del muxer `image2` **escribe un JPEG dentro de un `.ppm`** y es **peor** que no forzar nada (`bench/invocacion-aristas.md` §7.2). **Un valor que el motor declara «por defecto» no es una capacidad sondeada: es un valor por defecto, y el motor puede tener mejor lógica que él.** Fuerza el muxer, el mapeo de pistas y las restricciones del codificador.
- **La resolución de OCR la elige el ADAPTADOR DEL MOTOR, no el orquestador.** El orquestador calcula `ppp_nativos` y los pasa; cada motor aplica su `k`. Una constante global hace que cada motor nuevo herede en silencio los ppp que le convenían a otro — que es lo que le pasa hoy a Tesseract, al que R1 le asigna 100 ppp sobre `escaneado_d2` y le cuesta **32,10 puntos**.
- **`-map 0` explícito en ffmpeg.** Por defecto descarta la segunda pista de audio, en silencio.
- **El punto 1 del contrato no aplica al 23,6 % de los formatos — y donde no aplica, tampoco aplican el 2 ni el 3, porque los tres leen la cabecera.** De 381 formatos con veredicto, **90 no tienen marcador**. **No se pueden verificar 500 firmas porque no existen 500 firmas:** o se verifican las que existen y se declara **`no_aplica`** en las que no, o se declaran menos formatos. La cobertura va en **cuatro estados** (`evaluado` / `familia` / `no_aplica` / `sin_vocabulario`), **no en un booleano**: antes `1_firma` valía `True` en el 100 % de los ficheros evaluando el **12,4 %**. Con el vocabulario ampliado (24 → 147 nombres, 26 → 338 extensiones) sube al **54,2 %**.
- **Y el fallo emblemático del proyecto no lo atrapa el vocabulario: lo atrapa G6.** *Si la salida tiene la MISMA firma que la entrada y no era eso lo que se pedía, es sospechosa.* `magick x.png y.group4` devuelve `rc=0` y entrega un PNG: **22 de 22 atrapados por G6, 0 de 22 por firma** —ni con el vocabulario viejo ni con el nuevo—, porque `.group4` **no tiene firma que esperar**. Cuesta 0 y da 0 falsos positivos sobre las 53. Severidad `aviso`: calibrada sobre **un solo motor**.
- **`inspect` es la excepción a R8 y a R18: se queda en proceso y en sitio.** Lee cabeceras, no entrega la ruta a ningún motor externo y no escribe nada, así que no hay staging que justificar ni censo que hacer. **Con número:** el `inspect` en proceso cuesta **0,21–0,59 ms** *(corregido el 22/08 por `bench/hito4-mcp.md` §6.4: ~~0,04–0,06 ms~~ medía «abrir + leer 64 KiB de cabecera», no un `inspect`, que además clasifica el formato y recorre las cajas de un ISOBMFF)*; el staging que R8 le impondría, de **1,7 ms (1 MB) a 166 ms (256 MB)** — de **2,0× a 284×** la operación **a cambio de cero seguridad**. **La exención no cambia; su número sí: la primera cifra era ×4–10 optimista por medir otra cosa.** El cruce no es una constante: **`cruce_MB ≈ ffprobe_ms × copia_MBps / 1000`**, que con `ffprobe` ≈ 57 ms da **~70 MB con el disco contendido y ~95 MB holgado**.
- **MCP devuelve ruta y metadatos, nunca contenido** — y «contenido» incluye **base64 dentro de un `TextContent`**, que es como aparece de verdad. El criterio es **tokens de respuesta**, no tipos del protocolo.
- **Nunca devolver `stderr` crudo al modelo.** El error de un motor puede dirigir la siguiente acción del agente.
- **Lista blanca de raíces, denegar por defecto**, con el predicado **léxico antes de tocar el disco**, y **un mensaje opaco** para «prohibido» y «no existe».
- **La validación vive en el núcleo, no en la superficie.** FileX tendrá cuatro: CLA, MCP, watcher y API HTTP.
- **El catálogo MCP llega DIFERIDO en una sesión real, así que el ×2,0–2,6 por turno NO es el coste del despliegue.** Con las ~15 herramientas internas presentes, un catálogo pesado y uno ligero que difieren en ~3.300 tokens dan **26.941 = 26.941 tokens** de entrada: las descripciones no llegan al contexto. **Pero no apuestes el diseño a eso**: los **nombres** sí se inyectan en cada turno (el ≤1.200 tokens sigue valiendo como higiene de nombres), es comportamiento de **una versión** (2.1.238) y depende del **total** de herramientas de la sesión — con `--tools ""` y pocas, vuelve el régimen ansioso; con 40, el catálogo sale **truncado**. Y la otra cara no cambia: **un catálogo demasiado escueto produce 15–17 % de fallos silenciosos**.
- **Declarar `resources` y `prompts` es coste sin retorno.** El cliente los enumera (`resources/list`, `prompts/list`, n=1 cada uno), **pero el modelo no los ve**: responde «NINGUNO». Igual que las anotaciones. **El único canal que el modelo ve es la herramienta.**
- **Los roots se pueden cachear por sesión.** Claude Code 2.1.238 declara `roots.listChanged: true`, es decir se compromete a emitir `notifications/roots/list_changed`. **Observar una emisión real sigue PENDIENTE**; si nunca llega, la caché no se invalida hasta el fin de sesión, que es el comportamiento correcto por defecto.

## 6. Peso del repositorio

**No versiones salidas binarias regenerables.** El repositorio ya pagó una vez este error: 986 MB de pack, 99,9 % binario.

Si generas salidas, **borra las grandes al terminar** y deja un `MANIFIESTO.md` con nombre, `sha256`, tamaño y **la orden exacta que las reproduce**. `bench/salidas-referencia/referencia.json` tiene 39 de esas órdenes.

Lo que **sí** se versiona: los `.md`, los scripts, los `.json` de resultados, y **los logs** — son texto barato y son la trazabilidad de cada informe.

El `corpus/` está en **Git LFS**. Tras clonar: `git lfs pull`.

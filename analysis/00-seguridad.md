# Postura de seguridad de los orquestadores de conversión

Auditoría defensiva, solo lectura, sobre los seis orquestadores clonados en
`repos/orchestrators/`. El objetivo no es puntuar proyectos ajenos sino **decidir qué defensas
debe construir FileX**, que va a hacer exactamente lo mismo que ellos: alimentar una docena de
parsers en C con ficheros no confiables.

Todas las rutas son relativas a `repos/orchestrators/`. Cada afirmación va con `fichero:línea`.
Cuando una defensa no existe, se dice explícitamente y se indica que la ausencia se verificó por
búsqueda exhaustiva, no por inferencia.

**Modelo de amenaza de FileX, que condiciona toda la lectura:** FileX se expondrá como servidor
MCP. El que pide la conversión puede ser un agente de IA, no una persona. Eso cambia tres cosas
respecto a todos los proyectos auditados:

1. **La ruta de entrada es arbitraria.** Ninguno de estos seis recibe una ruta del sistema de
   ficheros: todos reciben una subida HTTP y escriben ellos el fichero. FileX recibirá
   `/home/user/loquesea` de un LLM. Es una clase de riesgo que **ninguno de los seis tiene que
   resolver**, y por tanto de la que no hay nada que copiar.
2. **El llamante es persuadible.** Un agente puede ser inducido por el contenido de un documento
   que acaba de leer a pedir una conversión concreta. La petición viene "autenticada" y es
   maliciosa.
3. **El volumen es no humano.** Un bucle de agente puede emitir mil peticiones en un minuto sin
   ninguna intención hostil.

---

## Tabla comparativa

| Repo | 1. Invocación de procesos | 2. Nombres y rutas | 3. Límites de recursos | 4. Aislamiento | 5. Config. de motores | 6. Superficie de red |
|---|---|---|---|---|---|---|
| **ConvertX** | Sí | Sí | **No** | **No** | **No** | Parcial |
| **transmute** | Sí | Sí | Parcial | **No** | **No** | Sí |
| **SnapOtter** | Sí | Sí | Parcial | Parcial | Parcial | Parcial |
| **gotenberg** | Sí | Sí | Parcial | Parcial | Parcial | **No** |
| **morphos** | **No** | Parcial | **No** | Parcial | **No** | **No** |
| **Stirling-PDF** | Sí | Sí | Parcial | **No** | Parcial | **No** |

Lectura rápida de la tabla:

- **La dimensión 1 está resuelta en el ecosistema.** Cinco de seis usan array de argumentos sin
  shell. La inyección de comandos clásica es un problema entendido. La excepción, morphos, es
  también el proyecto abandonado.
- **La dimensión 5 es el agujero colectivo.** **Ninguno de los seis distribuye un `policy.xml`
  propio de ImageMagick** (verificado: `find -iname policy.xml` sobre los seis árboles no devuelve
  nada). Dos de ellos además *debilitan* el de la distribución.
- **La dimensión 3 no la aprueba nadie.** El patrón repetido no es "no hay límites" sino algo
  peor de detectar: **los límites existen, están bien escritos y vienen desactivados de fábrica**.
- **La dimensión 4 la aprueba nadie.** Solo morphos y gotenberg declaran `USER` en su Dockerfile
  final; ConvertX, transmute y Stirling-PDF corren como root.

---

## Hallazgos por gravedad

### CRÍTICO

#### C1 — morphos: inyección de comandos por el nombre del fichero subido

`morphos/pkg/files/documents/docx.go:126-130`

```go
cmdStr := "libreoffice --headless --convert-to pdf:writer_pdf_Export --outdir %s %q"
cmd := exec.Command(
    "bash",
    "-c",
    fmt.Sprintf(cmdStr, "/tmp", docxFilename),
)
```

La cadena completa se pasa a `bash -c`. `docxFilename` viene de `filepath.Join("/tmp", d.filename)`
(`docx.go:84`), y `d.filename` es el nombre que el usuario puso en el multipart: fluye desde
`fileHeader.Filename` (`morphos/main.go:429`) → `files.BuildFactory(fileType, fileHeader.Filename)`
→ `NewDocumentFactory` → `documents.NewDocx(d.filename)` (`morphos/pkg/files/document_factory.go:29`).

El verbo `%q` **no es una defensa suficiente aquí**. `%q` de Go produce un literal de cadena de Go:
escapa `"` y `\`, pero deja intactos `$` y las comillas invertidas, que son precisamente los
caracteres que bash sigue expandiendo *dentro* de comillas dobles. La sustitución de comandos
sobrevive al escapado.

El mismo patrón, con la misma procedencia, en `morphos/pkg/files/documents/pdf.go:324-328`:

```go
cmdStr := "libreoffice --headless --infilter='writer_pdf_import' --convert-to %s --outdir %s %q"
cmd := exec.Command(
    "bash",
    "-c",
    fmt.Sprintf(cmdStr, `docx:"MS Word 2007 XML"`, "/tmp", pdfFile.Name()),
)
```

Aquí `pdfFile.Name()` procede de `os.CreateTemp("", p.filename)` (`pdf.go:297`), que usa el nombre
del usuario como patrón y solo le añade un sufijo aleatorio.

Matiz de precisión: la **travesía de directorios** sí está bloqueada, pero no por código de morphos
sino por la biblioteca estándar de Go, cuyo `multipart.Part.FileName()` aplica `filepath.Base`. Los
metacaracteres de shell no los toca nadie. Es una defensa accidental, y solo cubre una de las dos
clases de ataque.

Agravante de despliegue: `morphos/docker-compose.yml` monta el `/tmp` del **anfitrión** dentro del
contenedor (`volumes: - /tmp:/tmp`), y `uploadPath` es `/tmp` por defecto (`morphos/main.go:48-51`).

**Sin corregir. morphos está sin mantenimiento** — razón de más para que FileX no reutilice nada de
él, y para tratar este hallazgo como lección de diseño y no como bug ajeno pendiente.

#### C2 — Stirling-PDF: CORS comodín con credenciales y CSRF desactivado, por defecto

`Stirling-PDF/app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java:188`

```java
// Default to allowing all origins when nothing is configured
cfg.setAllowedOriginPatterns(List.of("*"));
```

y en la misma clase, `:218` → `cfg.setAllowCredentials(true);`

La segunda capa, independiente, en
`Stirling-PDF/app/core/src/main/java/stirling/software/SPDF/config/WebMvcConfig.java:241` con
`.allowedOriginPatterns("*")` y `:260` `.allowCredentials(true)`.

`allowedOriginPatterns("*")` no emite `Access-Control-Allow-Origin: *`: **refleja el `Origin` de la
petición**, lo que hace que la combinación con `allowCredentials(true)` sea aceptada por el
navegador. El valor por defecto de `system.corsAllowedOrigins` está vacío, así que esta es la
configuración de fábrica.

Y no hay contrapeso, porque CSRF está desactivado globalmente
(`SecurityConfiguration.java:269`):

```java
http.csrf(CsrfConfigurer::disable);
```

Cualquier web que visite un usuario autenticado puede invocar toda la API de conversión en su
nombre **y leer las respuestas**.

#### C3 — gotenberg: cero autenticación por defecto sobre una superficie que ejecuta JavaScript arbitrario

`gotenberg/pkg/modules/api/api.go:204-205`

```go
fs.Bool("api-enable-basic-auth", false, ...)
fs.Bool("api-enable-oidc-auth", false, ...)
```

Ambos `false`; `api-bind-ip` vacío (`api.go:196`) escucha en todas las interfaces. Y el llamante
puede hacer que Chromium evalúe una expresión arbitraria:
`gotenberg/pkg/modules/chromium/tasks.go:716` (`chromedp.Evaluate(expression, ...)`), porque
`--chromium-disable-javascript` también es `false` por defecto (`chromium.go:481`).

Se suma la SSRF de salida por webhook, con listas vacías por defecto
(`gotenberg/pkg/modules/webhook/webhook.go:45-47`) y cabeceras arbitrarias controladas por el
llamante (`gotenberg/pkg/modules/webhook/client.go:80`).

**Contexto honesto:** el modelo de amenaza declarado de gotenberg es "servicio interno detrás de un
gateway de confianza", y la distancia hasta un despliegue duro son ~6 flags. No es un descuido, es
un default. Pero para FileX la lección se invierte: **un default inseguro en un servidor MCP local
es peor**, porque no hay gateway ninguno y el "usuario" no lee documentación.

---

### ALTO

#### A1 — ConvertX: ningún timeout, en ningún conversor

Búsqueda de `timeout|kill|SIGKILL|AbortSignal|maxBuffer` sobre `ConvertX/src/converters/*.ts`:
**cero resultados**. Los 22 conversores llaman a `execFile` con un callback y nada más. Ejemplo
representativo, `ConvertX/src/converters/imagemagick.ts:476`:

```js
execFile(
  "magick",
  [...inputArgs, filePath, ...outputArgs, targetPath],
  (error, stdout, stderr) => { ... },
);
```

Un solo fichero patológico (un PDF con recursión, un SVG con `billion laughs`, un vídeo con un
stream corrupto) deja un proceso vivo indefinidamente. No hay nada que lo recoja.

#### A2 — ConvertX: la concurrencia es ilimitada por defecto, y el troceado no es un pool

`ConvertX/src/helpers/env.ts:19-22` define `MAX_CONVERT_PROCESS` con **valor por defecto `0`**, y
`ConvertX/README.md:103` lo documenta como *"Set to 0 for unlimited"*. Con ese valor,
`ConvertX/src/converters/main.ts:142-145`:

```js
function chunks<T>(arr: T[], size: number): T[][] {
  if (size <= 0) {
    return [arr];
  }
```

devuelve un único lote con todo, y `main.ts:163` lanza **todas** las conversiones a la vez.

Y aunque se configure, el mecanismo sigue sin ser un pool: `main.ts:163` trocea en lotes y espera a
que termine el lote entero antes de empezar el siguiente. Un fichero lento bloquea a sus
compañeros de lote mientras los núcleos están ociosos. La utilización real es del orden de
`1/n` en el peor caso.

#### A3 — ConvertX: sin límite de tamaño de petición

`ConvertX/src/index.tsx:30`

```js
maxRequestBodySize: Number.MAX_SAFE_INTEGER,
```

Sin tope de subida, sin tope de número de ficheros, y combinado con A1 y A2. No es una omisión: es
un valor puesto explícitamente para desactivar el límite.

#### A4 — ConvertX: el llamante elige el motor, y no se comprueba que soporte el formato de entrada

`ConvertX/src/converters/main.ts:210`

```js
converterFunc = properties[converterName]?.converter;
```

`converterName` viene del formulario (`ConvertX/src/pages/convert.tsx:59`,
`body.convert_to.split(",")[1]`). Cuando se suministra, se usa **directamente**: la rama que
verifica que el conversor declare soportar el par origen→destino es la del `else`
(`main.ts:212-229`), que solo se ejecuta cuando *no* se indicó conversor.

El resultado es que el llamante puede forzar cualquier motor sobre cualquier fichero — por ejemplo
dirigir contenido arbitrario a `latexmk` (`ConvertX/src/converters/xelatex.ts:26`), que lo
interpretará como TeX.

#### A5 — ConvertX: contenedor como root, y sandbox de Chromium desactivado para Calibre

`ConvertX/Dockerfile` no contiene ninguna directiva `USER` (verificado por búsqueda: el fichero
además fija `ENV PATH="/root/.local/bin:${PATH}"`, confirmando uid 0). Y en `Dockerfile:111`:

```dockerfile
ENV QTWEBENGINE_CHROMIUM_FLAGS="--no-sandbox"
```

Calibre renderiza HTML/EPUB no confiable con QtWebEngine, con el sandbox del renderer desactivado,
como root. No hay `seccomp`, `apparmor`, `cap_drop` ni límites en `ConvertX/compose.yaml`.

Sin `policy.xml` propio de ImageMagick (verificado) pese a instalar `imagemagick-7.q16` y
`ghostscript` (`Dockerfile:49-76`), y sin `-no-shell-escape` en la invocación de `latexmk`.

#### A6 — Stirling-PDF: toda la configuración de límites de `settings.yml` es inefectiva

`Stirling-PDF/app/common/src/main/java/stirling/software/common/util/ProcessExecutor.java:32`

```java
private static ApplicationProperties applicationProperties = new ApplicationProperties();
```

Campo estático inicializado con una instancia **vacía**. No existe ningún setter ni inyección de
Spring que lo reemplace: la búsqueda de `setApplicationProperties` sobre `Stirling-PDF/app/` no
devuelve **ningún** resultado.

Consecuencia: todos los `processExecutor.sessionLimit.*` y `processExecutor.timeoutMinutes.*` que
el operador configure se ignoran, y siempre se usan los valores por defecto compilados. Un
administrador que baje el límite de sesiones de Ghostscript para contener un DoS **no obtiene
ningún efecto, y no recibe ningún aviso**.

Este es el hallazgo más instructivo de toda la auditoría: un control de seguridad que existe, está
documentado, se configura, y no hace nada.

#### A7 — Stirling-PDF: `-dSAFER` ausente en la mayoría de invocaciones de Ghostscript

Solo dos ocurrencias en todo el repositorio, ambas en el mismo fichero:
`Stirling-PDF/app/core/src/main/java/stirling/software/SPDF/controller/api/converters/PdfVectorExportController.java:201` y `:244`.

No lo pasan, entre otras:
`.../controller/api/misc/CompressController.java:1211-1216`,
`.../common/util/GeneralUtils.java:1149-1157`,
`.../common/util/misc/ColorSpaceConversionStrategy.java:47-58`,
`.../controller/api/CropController.java:300-306`,
`.../controller/api/misc/OCRController.java:317-324`,
`.../service/PdfJsonConversionService.java:2037-2052`.

Mitigante real: Ghostscript ≥ 9.50 activa SAFER por defecto, y el Dockerfile compila 10.06.0. Pero
la defensa en profundidad no existe, y en despliegues no-Docker (escritorio, Windows) el `gs` del
sistema no está bajo control del proyecto.

#### A8 — Stirling-PDF y SnapOtter debilitan deliberadamente la `policy.xml` de ImageMagick

`Stirling-PDF/docker/base/Dockerfile:324-326`

```dockerfile
sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /usr/local/etc/ImageMagick-7/policy.xml && \
sed -i 's/rights="none" pattern="PS"/rights="read|write" pattern="PS"/' ... && \
sed -i 's/rights="none" pattern="EPS"/rights="read|write" pattern="EPS"/' ...
```

`SnapOtter/docker/Dockerfile:445-451` hace lo mismo, algo más conservador (EPS a `read|write`;
PS, PDF y XPS a `read`).

Estos coders vienen deshabilitados de fábrica en las distribuciones **precisamente porque delegan
en Ghostscript** — es la mitigación estándar heredada de ImageTragick y de la cadena de bypasses de
`-dSAFER`. Ambos proyectos los reabren para contenido no confiable.

Y ninguno de los dos compensa: **no se añade ningún `domain="resource"`** (memory, map, area, disk,
time), **ningún `domain="delegate"`**, **ningún `domain="path" pattern="@*"`**. La política queda
más abierta que la de la distribución y sin ningún techo de recursos.

#### A9 — SnapOtter: los topes de recursos están todos a `0` (ilimitado) de fábrica

`SnapOtter/apps/api/src/lib/env.ts:72-76`

```js
SUBPROCESS_MEMORY_LIMIT_MB: z.coerce.number().default(0),
MAX_PDF_PAGES: z.coerce.number().default(0),
MAX_VIDEO_DURATION_S: z.coerce.number().default(0),
MAX_AUDIO_DURATION_S: z.coerce.number().default(0),
MAX_VIDEO_BITRATE_KBPS: z.coerce.number().default(0),
```

Más `MAX_MEGAPIXELS: 0` (`env.ts:35`). La lógica que los aplica está bien escrita y consistentemente
guardada con `if (x > 0 && ...)`, lo que significa que **de fábrica no se aplica ninguna**.

El caso más delicado, `SnapOtter/apps/api/src/lib/format-decoders.ts:55`:

```js
limitInputPixels: options.maxPixels ?? false,
```

En sharp, `false` significa **sin límite**, no "por defecto". Cuando `maxPixels` es `undefined` —
que es el caso en todas las herramientas salvo OCR — esto es *peor* que omitir la clave, porque
descarta el techo integrado de 268 megapíxeles de libvips. Es la bomba de descompresión de imagen
servida en bandeja. `SnapOtter/apps/api/src/modality/image-input.ts:177` sí lo resuelve bien
(omitir la opción en vez de pasarle `false`), lo que confirma que es un desliz y no una decisión.

#### A10 — gotenberg: el bloqueo de IPs privadas está desactivado en los cuatro módulos

`gotenberg/pkg/modules/chromium/chromium.go:476`

```go
fs.Bool("chromium-deny-private-ips", false, "Reject URLs whose host resolves to a non-public IP address ...")
```

Idéntico en `gotenberg/pkg/modules/api/api.go:211` (`api-download-from-deny-private-ips`),
`gotenberg/pkg/modules/webhook/webhook.go:47` y
`gotenberg/pkg/modules/libreoffice/api/api.go:358`.

La lógica de bloqueo es excelente (ver P6 más abajo) pero está apagada: en una instalación estándar,
`POST /forms/chromium/convert/url` con `url=http://169.254.169.254/latest/meta-data/` devuelve el
endpoint de metadatos de la nube renderizado como PDF.

#### A11 — transmute: solo 5 de 25 conversores aplican timeout

Búsqueda de `timeout=` sobre `transmute/backend/converters/*.py` y `compressors/*.py`: 8
ocurrencias repartidas en **5 ficheros de 25**. Los que lo hacen, lo hacen bien — el timeout
adaptativo por tamaño de entrada de `transmute/backend/converters/ffmpeg_convert.py:152-157` es el
mejor patrón de toda la auditoría en su categoría:

```python
def get_size_based_timeout_seconds(self) -> int:
    input_size_bytes = Path(self.input_file).stat().st_size
    input_size_mb = max(1, math.ceil(input_size_bytes / (1024 * 1024)))
    timeout_seconds = self.min_timeout_seconds + (input_size_mb * self.timeout_seconds_per_mb)
    return min(timeout_seconds, self.max_timeout_seconds)
```

El problema es que **es una decisión por conversor y no una propiedad de la capa de invocación**.
Los otros 20 quedan sin protección, y cada conversor nuevo nace desprotegido por omisión.

Tampoco hay límite de tamaño de subida ni de píxeles: `transmute/backend/core/settings.py` no
contiene ningún `max_file_size`, `MAX_CONTENT_LENGTH` ni `MAX_IMAGE_PIXELS` (verificado por
búsqueda sobre el fichero completo).

#### A12 — transmute: WeasyPrint sin `url_fetcher` restringido

`transmute/backend/converters/email_convert.py:590`

```python
HTML(string=html_content).write_pdf(output_file)
```

`html_content` procede del correo que se está convirtiendo. Sin un `url_fetcher` personalizado,
WeasyPrint resolverá las referencias externas del HTML por su cuenta, incluidas `file://` y URLs
internas. La búsqueda de `url_fetcher` sobre `transmute/backend/` no devuelve **ningún** resultado.

#### A13 — Contenedores como root en cuatro de seis

Verificado por inspección directa del Dockerfile final de cada proyecto:

| Repo | `USER` en Dockerfile |
|---|---|
| morphos | `USER morphos` (`morphos/Dockerfile:40`) |
| gotenberg | `USER gotenberg` |
| SnapOtter | **ninguna** — baja privilegios en runtime con `gosu` (`docker/entrypoint.sh:260`) |
| ConvertX | **ninguna** |
| transmute | **ninguna** (`transmute/docker/Dockerfile`, `ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]`) |
| Stirling-PDF | **ninguna** en `docker/backend/Dockerfile` ni `docker/embedded/Dockerfile`; solo en el sidecar `docker/unoserver/Dockerfile:92` |

En Stirling-PDF, además, el fallback ejecuta Java **como root** con un simple aviso si `setpriv` no
está disponible (`Stirling-PDF/scripts/init-without-ocr.sh:972-974`).

Ninguno de los seis `docker-compose` aplica `seccomp` o `apparmor`. Verificado por búsqueda: cero
ocurrencias en los seis árboles.

---

### MEDIO

#### M1 — ConvertX construye una expresión regular con la extensión del usuario

`ConvertX/src/converters/main.ts:174-177`

```js
newFileName = fileName.replace(
  new RegExp(`${fileTypeOrig}(?!.*${fileTypeOrig})`),
  newFileExt,
);
```

`fileTypeOrig` es lo que hay tras el último punto del nombre subido. Va sin escapar a un constructor
de `RegExp`, duplicado. `sanitize-filename` no elimina metacaracteres de expresión regular (`(`,
`+`, `*`, `[`), así que una extensión adversa produce o bien una excepción, o bien un patrón de
retroceso catastrófico, o bien un renombrado incorrecto. Es ReDoS, no ejecución.

#### M2 — Stirling-PDF: nombre de usuario como argumento desnudo a `pdftohtml`

`Stirling-PDF/app/common/src/main/java/stirling/software/common/util/PDFToFile.java:198-201`

```java
new ArrayList<>(Arrays.asList(
        "pdftohtml", "-c", tempInputFile.toString(), pdfBaseName));
```

`pdfBaseName` deriva del nombre subido. `Filenames.toSimpleFileName` elimina componentes de ruta
pero **no un guion inicial**. Y la validación centralizada `ProcessExecutor.validateCommand`
(`ProcessExecutor.java:491-537`) no lo cubre: recorre **todos** los argumentos, pero solo para
rechazar `\0`, `\n` y `\r` (`:496-504`); las comprobaciones de `..` y de existencia se aplican
**únicamente al ejecutable** (`:506-536`). Nada rechaza un argumento que empiece por `-`, y el
separador `--` no se usa en ningún punto del repositorio. Un fichero llamado `-foo.pdf` produce un
argumento que `pdftohtml` interpretará como opción.

Es la única grieta real de la dimensión 1 en Stirling-PDF, y es exactamente la clase de fallo que
sobrevive a "usamos array de argumentos, estamos a salvo".

#### M3 — gotenberg: inyección de opciones en los mini-lenguajes de los motores

`gotenberg/pkg/modules/pdfcpu/pdfcpu.go:687`

```go
for k, v := range stamp.Options {
    descParts = append(descParts, fmt.Sprintf("%s:%s", k, v))
}
description := strings.Join(descParts, ", ")
```

`stamp.Options` es JSON arbitrario del usuario, sin lista blanca de claves ni de valores. pdfcpu
re-parsea esa cadena como su lenguaje de descripción; un valor que contenga `, ` inyecta directivas
adicionales.

Mismo patrón sin validar en `splitSpan` / `rotatePages`, que llegan a los mini-lenguajes de pdftk
(`pdftk.go:134`), qpdf (`qpdf.go:144`) y pdfcpu (`pdfcpu.go:179`, además **sin terminador `--`**), y
en LibreOffice (`libreoffice.go:326`, `fmt.Sprintf("PageRange=%s", options.PageRanges)`).

**No es inyección de shell — no hay shell en ninguna parte de gotenberg — es inyección de opciones
del motor.** Es la clase de bug que queda cuando ya has resuelto bien la dimensión 1, y es la que
FileX heredará si copia solo "argumentos como array".

#### M4 — SnapOtter: sin escalado a `SIGKILL` en el puente Python, y timeouts anulables

`SnapOtter/packages/ai/src/bridge.ts:582` mata con `SIGTERM` y no arma ningún temporizador de gracia
que escale a `SIGKILL`. Un proceso Python bloqueado en una llamada nativa (CUDA) nunca se fuerza a
morir. Además `bridge.ts:24` (`if (seconds === 0) return undefined;`) hace que
`PROCESSING_TIMEOUT_S=0` desactive el temporizador por completo.

Contrasta con los motores nativos del mismo repositorio, que **sí** escalan a `SIGKILL`
(`packages/doc-engine/src/ghostscript.ts:19`, `qpdf.ts:18`, `pandoc.ts:80`, `libreoffice.ts:70`,
`packages/media-engine/src/ffmpeg.ts:75`).

#### M5 — Stirling-PDF: el saneador de documentos Office no elimina macros

`Stirling-PDF/app/common/src/main/java/stirling/software/common/util/OfficeDocumentSanitizer.java:119-127`
solo reescribe `*.rels` y los XML de ODF, para quitar URLs externas. No hay **ninguna** referencia a
`vbaProject`, `macro`, `Basic/` ni `Scripts/` en el fichero, pese a que `.docm/.xlsm/.pptm` están
explícitamente en la lista blanca (`:47-49`).

Ningún proyecto de los seis fija explícitamente el nivel de seguridad de macros de LibreOffice
(`MacroSecurityLevel`). SnapOtter y gotenberg quedan seguros **por accidente**: al crear un
`-env:UserInstallation` vacío por conversión, LibreOffice cae en su nivel 2 por defecto. Es una
garantía implícita y no aseverada.

#### M6 — Nadie limita el tamaño de la salida ni el número de páginas

Búsqueda de límites de páginas sobre los seis árboles: solo Stirling-PDF tiene topes de píxeles
puntuales y por herramienta
(`AutoSplitPdfController.java:71`, `MAX_IMAGE_PIXELS = 100_000_000`;
`ScannerEffectController.java:69`, `16_777_216`), y ninguno es global.

Ninguno de los seis limita el **tamaño de la salida**. Una entrada de 1 MB que produce 40 GB
(un PDF de una página a 10000 DPI, un TIFF descomprimido) llena el disco en todos ellos.

#### M7 — Solo un proyecto de seis tiene limitación de tasa

Búsqueda de `rate.limit|RateLimit|bucket4j|slowapi|Limiter` sobre los seis: solo **SnapOtter** la
implementa de verdad (`apps/api/src/plugins/per-user-rate-limit.ts`,
`apps/api/src/lib/login-throttle.ts`). Y aun así es anulable
(`apps/api/src/routes/tool-factory.ts:242-246`, `RATE_LIMIT_PER_MIN === 0 → false`) y **uniforme**:
un endpoint trivial y una transcodificación de vídeo cuestan lo mismo.

Stirling-PDF tiene el mecanismo pero desactivado por defecto
(`AppConfig.java:115-120`, `Boolean.parseBoolean(null)` = `false`) y con el filtro por IP
explícitamente deshabilitado (`SecurityConfiguration.java:297-298`).

gotenberg, ConvertX, transmute y morphos: ninguna.

#### M8 — morphos: bomba de descompresión de imagen, y sin ningún límite

`morphos/pkg/files/images/png.go:96` (y `jpeg.go:96`, `webp.go:98`)

```go
rgba := image.NewRGBA(img.Bounds())
```

Asigna 4 bytes por píxel para la imagen decodificada completa, sin ningún techo de dimensiones. Un
PNG de pocos kilobytes que declare 50000×50000 provoca una asignación de 10 GB.

Y no hay nada que lo contenga: `morphos/main.go` no llama a `ParseMultipartForm` con límite ni usa
`http.MaxBytesReader` (verificado), lee la subida entera en memoria con `io.ReadAll`
(`main.go:409`), y el `http.Server` (`main.go:322-325`) se construye sin `ReadTimeout`,
`WriteTimeout` ni `MaxHeaderBytes`.

Sin autenticación de ningún tipo: `morphos/main.go:293-303` registra todas las rutas, incluidas
`POST /upload` y `Mount("/api/v1", ...)`, con el único middleware `middleware.Logger`. Y
`main.go:276` sirve el directorio de subidas entero por `/files/*` sin control de acceso.

#### M9 — Temporales huérfanos: nadie los recoge tras un `SIGKILL`

Patrón compartido: la limpieza se hace en `finally` / `defer` / cancel func, que un OOM-killer o un
`docker kill` se salta entero.

- gotenberg: `GarbageCollect` (`pkg/gotenberg/gc.go:15`) solo está cableado para artefactos de
  Chromium y LibreOffice; **los directorios UUID de petición no casan con ningún patrón**. Y se
  crean con permisos `0755` (`pkg/gotenberg/fs.go:79`).
- SnapOtter: no existe barrido de arranque ni periódico sobre el scratch root
  (`apps/api/src/lib/route-scratch.ts:9`).
- ConvertX: sí tiene barrido periódico (`src/index.tsx:76-99`), cada
  `AUTO_DELETE_EVERY_N_HOURS` (24 h por defecto) — de los seis, es el único que borra por TTL desde
  el arranque.
- Stirling-PDF: el más completo, con `TempFileManager`, `TempFileShutdownHook` y
  `TempFileCleanupService` (limpieza programada **y de arranque**).

#### M10 — Contraseñas en `argv` y en logs

`gotenberg/pkg/gotenberg/cmd.go:78` registra la línea de comandos completa en nivel debug, lo que
expone `--password` de LibreOffice, `--encrypt` de qpdf, `user_pw`/`owner_pw` de pdftk y
`--upw`/`--opw` de pdfcpu. Todas visibles además en `/proc/<pid>/cmdline` para cualquier proceso del
contenedor.

#### M11 — Stirling-PDF: trazas de pila en las respuestas de error

`Stirling-PDF/app/core/src/main/resources/application.properties:40-42`

```properties
spring.web.error.include-stacktrace=always
spring.web.error.include-exception=true
spring.web.error.include-message=always
```

Y `ProcessExecutor.java:330-334` incluye el `errorMessage` completo del proceso externo en la
excepción, que acaba en la respuesta HTTP: filtra rutas absolutas de temporales, versiones de
binarios y salida cruda de los motores.

---

### BAJO

- **ConvertX no valida el contenido contra la extensión.** Búsqueda de detección por magic bytes
  sobre `ConvertX/src`: ningún resultado. Se confía enteramente en la extensión del nombre. morphos
  (`mimetype.Detect`, `main.go:180`), transmute, SnapOtter y Stirling-PDF sí sniffan.
- **ConvertX usa `exec()` (con shell) en `src/helpers/printVersions.ts`** (18 llamadas,
  `:18`-`:188`). Todas con cadenas constantes, no inyectable — pero es el hábito el que preocupa,
  porque una futura interpolación en ese fichero no encontraría ninguna barrera.
- **Búsqueda por prototipo en objetos planos.** `ConvertX/src/converters/main.ts:210`
  (`properties[converterName]`) y `SnapOtter/apps/api/src/routes/features.ts:936`
  (`FEATURE_BUNDLES[bundleId]`) indexan objetos literales con cadenas del usuario. `"constructor"`
  supera la comprobación de existencia. En ambos casos el impacto se queda en un fallo, no en
  ejecución, pero la corrección correcta es `Object.hasOwn()` o un `Map`.
- **SnapOtter: el saneador de SVG es por expresiones regulares** y no por un parser XML
  (`apps/api/src/lib/svg-sanitize.ts:35`). El propio código lo reconoce en `:120`
  (`// Durable follow-up: replace this regex sanitizer with an XML`).
- **gotenberg: `/health` sin middleware de seguridad** (`pkg/modules/api/api.go:623-636`), ejecuta
  todos los health checks de módulos y su telemetría se descarta por defecto: amplificación barata e
  invisible en el log.
- **Stirling-PDF: `CbzUtils.java:50`** es la única lectura de ZIP que no pasa por
  `ZipSecurity.createHardenedInputStream` (sin protección anti zip-bomb).

---

### Lo que estos proyectos hacen bien (patrones a copiar)

Merece un apartado propio, porque es de donde debe salir el diseño de FileX.

**P1 — `execFile`/`spawn`/`ProcessBuilder` con array, nunca shell.** Cinco de seis. Búsqueda de
`shell=True` / `shell: true` sobre el código de producción de los seis: **cero resultados** (las
únicas ocurrencias están en scripts de desarrollo de Stirling-PDF —
`scripts/translations/auto_translate.py:26`, `frontend/scripts/update-minor.js:20` — fuera del
camino de ejecución del servidor).

**P2 — gotenberg: matar el grupo de procesos, no el proceso.** `pkg/gotenberg/cmd.go:35` y `:55`

```go
cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
```

con `syscall.Kill(-cmd.process.Process.Pid, syscall.SIGKILL)` en `cmd.go:254`. Es la diferencia
entre matar `soffice` y matar `soffice` **y toda su descendencia**. Sin esto, un timeout deja
huérfanos. Con `tini` como PID 1 para recoger zombies.

**P3 — gotenberg: el nombre del usuario nunca llega a `argv`.**
`pkg/modules/api/context.go:698` sanea (quita `/` **y** `\` — deliberadamente no usa
`filepath.Base`, que ignora `\` en Linux —, elimina C0/DEL, normaliza a NFC) y acto seguido
`context.go:465` renombra a UUID:

```go
safeName := uuid.New().String() + filepath.Ext(filename)
```

El nombre original se conserva solo en memoria, para la respuesta. **Es la defensa correcta**, y
resuelve de un golpe la inyección de argumentos, la travesía, las colisiones y los caracteres
raros.

**P4 — gotenberg: pool real con semáforo, cola acotada y reinicio periódico.**
`pkg/gotenberg/supervisor.go:143-168` construye un semáforo de concurrencia (`maxConcurrency`), un
tope de cola (`maxQueueSize`, con `ErrMaximumQueueSizeExceeded` en `:303-305`), reinicio del motor
tras N peticiones (`maxReqLimit`) y apagado por inactividad. Es exactamente lo que ConvertX no
tiene.

**P5 — gotenberg: defensa en profundidad de `file://` en Chromium, en tres capas independientes.**
Lista de denegación por defecto (`chromium.go:475`, `^file:(?!//\/tmp/).*`), rechazo de esquema a
nivel de ruta (`routes.go:451`), y denegación por defecto de sub-recursos por petición
(`events.go:149` con `events.go:351`, `if len(allowedFilePrefixes) == 0 { return false }`), donde
cada petición solo autoriza **su propio** directorio (`routes.go:606`). Resultado: la lectura
cruzada entre peticiones está bloqueada aunque los directorios sean `0755`.

**P6 — gotenberg: validación de salida con fallo cerrado y pinning de IP.**
`pkg/gotenberg/outbound.go:345` falla cerrado cuando el host no resuelve (lo que también deniega
`http://2130706433/`), la lista de denegación se aplica **siempre**, incluso a URLs de la lista de
permitidos (`outbound.go:304-319`), y el proxy de pinning (`pkg/modules/chromium/pinning_proxy.go`)
impide que Chromium haga su propia resolución DNS, cerrando la ventana de *DNS rebinding*.

Con una arista peligrosa que conviene no copiar: un acierto en la lista de permitidos activa
`Bypass: true` (`outbound.go:321`) y **desactiva** la comprobación de clase de IP y el pinning. Un
operador que añada una lista de permitidos creyendo endurecer, debilita.

**P7 — gotenberg: construcción de `argv` de exiftool.** `pkg/modules/exiftool/exiftool.go:33`

```go
var safeKeyPattern = regexp.MustCompile(`^[a-zA-Z0-9_.:][a-zA-Z0-9\-_.:]*$`)
```

El primer carácter excluye `-` a propósito (la clave no puede convertirse en un flag) y `=` está
excluido entero (no puede colar una segunda asignación). Más lista de denegación de pseudo-tags con
efectos sobre el sistema de ficheros (`:75-81`: `FileName`, `Directory`, `HardLink`, `SymLink`).

**P8 — SnapOtter: `-dSAFER` en los 11 puntos de invocación de Ghostscript.**
`packages/doc-engine/src/ghostscript.ts:48`, `:82`, `:113`, `:128`;
`apps/api/src/modality/preview.ts:46`; `packages/ai/src/tesseract-pdf.ts:374`, `:450`, `:549`.
Consistencia total, y con un test que lo asevera (`tests/unit/ai/tesseract-pdf.test.ts:227`).

**P9 — SnapOtter: límite de memoria por subproceso, seguro por construcción.**
`packages/shared/src/subprocess-limit.ts:24-25`

```js
const script = 'ulimit -v "$1" 2>/dev/null || true; shift; exec "$@"';
return ["/bin/sh", ["-c", script, "sh", String(mb * 1024), bin, ...args]];
```

Usa `/bin/sh -c` pero el script es una constante y los argumentos llegan como parámetros
posicionales: `exec "$@"` **no los re-parsea por el shell**. Es la forma correcta de aplicar un
`ulimit` sin abrir una inyección.

**P10 — SnapOtter: pandoc con `--sandbox`** (`packages/doc-engine/src/pandoc.ts:54`) y **el texto de
marca de agua nunca entra en el grafo de filtros de ffmpeg**
(`apps/api/src/routes/tools/watermark-video.ts:56-61`): se escribe a un fichero y se referencia con
`textfile=`, más `expansion=none` para bloquear `%{...}`. Es la mitigación correcta de un problema
que casi todo el mundo resuelve mal escapando.

**P11 — transmute: validación de ruta canónica contra directorios permitidos.**
`transmute/backend/core/helper_functions.py:354`, con `Path(...).resolve(strict=False)` (que
resuelve `..` y enlaces simbólicos), comprobación de pertenencia a `upload_dir`/`tmp_dir`/`output_dir`
y, además, **exigencia de que el nombre del fichero sea hexadecimal con formato UUID**
(`:406-412`). Es el patrón más cercano a lo que FileX necesita para su superficie MCP.

**P12 — transmute: cola de trabajo real y autenticación madura.**
`backend/core/settings.py:56` (`conversion_worker_concurrency: int = 5`) con recuperación de
trabajos obsoletos al arrancar (`:58-59`). Y es el único de los seis con autenticación seria y
**segura por defecto**: JWT + claves de API + OIDC, con `allow_unauthenticated: bool = False`
(`backend/core/settings.py:93`) y la sesión de invitado cerrada tras esa bandera
(`backend/api/routes/guest.py:37`).

**P13 — Stirling-PDF: zip slip cerrado en las cinco rutas de descompresión.**
`app/common/src/main/java/stirling/software/common/util/FileToPdf.java:85-96` combina
`ZipSecurity.createHardenedInputStream` con `normalize()` + `startsWith()`, más
`sanitizeZipFilename` (`:141-168`) que elimina letras de unidad, barras iniciales y `../` de forma
recursiva. Con `MAX_UNZIP_DEPTH` para archivos anidados (`ZipExtractionUtils.java:93-99`).

**P14 — Stirling-PDF: XXE cerrado de forma consistente.** `SvgSanitizer.java:88-96`,
`OfficeDocumentSanitizer.java:279-287`, `CertificateValidationService.java:615-622`: todos con
`FEATURE_SECURE_PROCESSING`, `disallow-doctype-decl`, entidades externas desactivadas,
`setXIncludeAware(false)` y `setExpandEntityReferences(false)`.

**P15 — Stirling-PDF: el único MCP del grupo, y con el modelo de autorización correcto.** Es el
único de los seis con superficie MCP (`app/proprietary/.../mcp/`, bajo licencia de pago). Y
`McpServerController.java:203-206` **falla cerrado**:

```java
// Fail closed: no/unauthenticated principal yields an empty context so scoped ops are refused.
if (auth == null || !auth.isAuthenticated() || auth.getName() == null) {
    return new McpCallContext(null, Set.of(), scopesEnabled);
}
```

con ámbitos por herramienta (`SCOPE_` en `:210-213`) y una capa de filtros dedicada:
`McpApiKeyAuthFilter`, `McpAudienceValidator`, `McpUserBindingFilter` y **`McpRequestSizeFilter`**,
que acota el cuerpo *antes* de parsear el JSON. El único proyecto que ya se ha enfrentado al modelo
de amenaza de FileX lo resolvió con clave de API, OAuth, ámbitos y límite de tamaño.

**P16 — ConvertX: `sanitize-filename` aplicado consistentemente** en las cuatro rutas que tocan
nombres (`src/pages/upload.tsx:28,32`, `download.tsx:25`, `deleteFile.tsx:27`,
`convert.tsx:62`), con comprobación de propiedad del trabajo antes de servir o borrar
(`download.tsx:17-22`) y borrado por TTL desde el arranque (`src/index.tsx:76-99`). Su dimensión 2
es sólida; son las otras las que fallan.

---

## Defensas que FileX debe incorporar desde el día 1

Priorizadas. Las cinco primeras son innegociables porque son las que resultan **caras o imposibles
de añadir después**: definen la frontera de proceso y la forma de las APIs.

### Prioridad 1 — Las que hay que construir antes de la primera conversión

**1. Una única capa de invocación, y que sea la única que puede lanzar procesos.**

Ni un solo `subprocess.run` suelto en un módulo de conversor. Un `run_engine(binario, args, ...)`
que sea el **único** punto del código que llama a `subprocess`, con una prueba que falle si aparece
otro. La lección es A11 y M2: en transmute el timeout es excelente pero es una decisión por
conversor, así que 20 de 25 no lo tienen; en Stirling-PDF la validación centralizada existe y
recorre todos los argumentos, pero solo busca bytes nulos y saltos de línea — no la clase de abuso
que de verdad importa en `argv`, el argumento que empieza por guion.

Esa capa debe, sin excepción y sin posibilidad de que un conversor la eluda:

- Pasar `args` como lista. Nunca `shell=True`. (P1)
- **Insertar `--` antes de los operandos** siempre que el binario lo soporte, y rechazar cualquier
  argumento que empiece por `-` y no proceda de una lista blanca. Esto es M2, y es el fallo que
  sobrevive a "usamos listas".
- Aplicar un **timeout obligatorio y adaptativo al tamaño de la entrada**, con techo absoluto
  (P11/A11). Sin parámetro por defecto que signifique "sin límite".
- **Matar el grupo de procesos**, no el proceso: `start_new_session=True` en Python y
  `os.killpg(os.getpgid(p.pid), SIGKILL)`. (P2) Sin esto, matar `soffice` deja hijos vivos.
- **Escalar `SIGTERM` → espera de gracia → `SIGKILL`.** Es exactamente el fallo M4 de SnapOtter.
- Aplicar un límite de memoria por hijo, vía `resource.setrlimit(RLIMIT_AS, ...)` en un
  `preexec_fn` (más limpio en Python que el truco del `ulimit` de P9, que existe porque Node no
  tiene equivalente).
- Acotar la lectura de `stdout`/`stderr` y **nunca devolver la salida cruda del motor al llamante**
  (M11): filtra rutas y versiones.

**2. Ninguna ruta ni ningún nombre del llamante llega jamás a `argv`.**

Este es el punto donde el modelo de amenaza de FileX se aparta de los seis auditados, y donde más
hay que resistirse a copiar.

- Copiar/enlazar la entrada a un directorio de trabajo por petición y **renombrar a UUID +
  extensión normalizada** antes de invocar nada. (P3) Es la defensa que hace irrelevantes de golpe
  la inyección de argumentos, la travesía, las colisiones y el `-foo.pdf` de M2.
- El nombre original se conserva solo como metadato, para la respuesta.
- **La ruta de salida la elige FileX, no el llamante.** Si la API permite indicar destino, debe
  validarse con el patrón de P11 —`Path.resolve()` canónico y pertenencia a una raíz permitida— y
  jamás por comparación de cadenas sobre la ruta sin resolver.

**3. Una lista blanca de raíces, obligatoria, aplicada al entrar.**

Consecuencia directa de que el llamante sea un agente: **FileX recibe rutas del sistema de ficheros,
cosa que ningún proyecto auditado hace.** Ninguno de los seis tiene esta defensa porque ninguno la
necesita. Hay que diseñarla, no copiarla.

- Configuración explícita de directorios legibles y escribibles. Sin valor por defecto que sea
  "todo el disco" ni "el directorio actual".
- `Path.resolve()` antes de comparar, para resolver enlaces simbólicos y `..`. Después, comprobación
  de pertenencia por componentes de ruta, no por `startswith` sobre cadenas (que acepta
  `/data/uploads-evil` como si estuviera dentro de `/data/uploads`).
- **Denegar por defecto**, y devolver un error idéntico para "fuera de la lista blanca" y "no
  existe": si no, la herramienta se convierte en un oráculo de existencia de ficheros para el
  agente.
- Rechazar enlaces simbólicos que apunten fuera, y comprobar de nuevo **después** de abrir
  (`TOCTOU`).

**4. Un pool de procesos de verdad, no troceado en lotes.**

Semáforo con cola acotada, según P4, no el `chunks()` de ConvertX (A2). Concretamente:
concurrencia máxima configurable con **valor por defecto finito** (nunca `0 = ilimitado`, que es
justo el fallo A2), cola con tope que rechaza con un error claro cuando se llena, y reinicio del
motor tras N conversiones para los que acumulan estado (LibreOffice).

Esto es defensa de disponibilidad frente a un llamante no humano: un bucle de agente emitirá mil
peticiones sin malicia, y la diferencia entre encolar y morir la decide esta pieza.

**5. Herramientas MCP anotadas, con ámbitos y fallo cerrado.**

Siguiendo P15, que es el único precedente real del grupo:

- `readOnlyHint` / `destructiveHint` en cada herramienta. Convertir crea ficheros; sobrescribir
  destruye. El cliente debe poder distinguirlo.
- **Separar las herramientas por privilegio**: convertir a un directorio gestionado por FileX es una
  operación; escribir en una ruta arbitraria indicada por el llamante es otra distinta, y debe
  poder desactivarse por completo.
- **Sobrescribir nunca por defecto.** Si el destino existe, fallar y exigir un parámetro explícito.
  Un agente que reintenta no debe destruir el original.
- Fallo cerrado ante un contexto no autenticado o ambiguo (P15).
- Un tope de tamaño **antes** de parsear la petición (`McpRequestSizeFilter`).

### Prioridad 2 — Antes de exponerlo a contenido no confiable

**6. `policy.xml` propio de ImageMagick, distribuido con FileX y verificado al arrancar.**

Es el agujero unánime: **ninguno de los seis lo hace**, y dos lo empeoran (A8). FileX debe enviar el
suyo, apuntar `MAGICK_CONFIGURE_PATH` a él, y **comprobar al arrancar que está activo** (con
`magick -list policy`), fallando ruidosamente si no. Con lo que nadie pone:

- `domain="resource"` para `memory`, `map`, `area`, `disk`, `time`, `width`, `height`.
- `domain="delegate" rights="none"` — en particular para `gs`, `https`, `show`, `ephemeral`.
- `domain="path" rights="none" pattern="@*"` (bloquea la lectura de ficheros por indirección).
- `coder` en `none` para `PS`, `EPS`, `PDF`, `XPS`, `MSL`, `MVG`, y encaminar el PDF a Ghostscript o
  a PyMuPDF de forma explícita y controlada, nunca por delegado implícito.

**7. `-dSAFER` explícito en cada invocación de Ghostscript, más `--permit-file-read/write`.**

No confiar en el valor por defecto de la versión instalada (A7): es defensa en profundidad barata, y
FileX es local-first, así que la versión de `gs` del sistema **no está bajo su control** — que es
exactamente el escenario en el que el mitigante de Stirling-PDF deja de aplicar. Acotar además la
lectura y escritura al directorio de trabajo, como hace `ConvertPDFToPDFA.java:371-376`.

**8. LibreOffice: perfil aislado por conversión y macros desactivadas explícitamente.**

`-env:UserInstallation=file:///<uuid>` por invocación (P4/P8 de SnapOtter y gotenberg). Esto no es
solo seguridad: sin ello, **dos conversiones simultáneas se pisan el perfil y la segunda falla o se
cuelga**, que es un bug de corrección que ConvertX tiene hoy (su
`src/converters/libreoffice.ts:176` no pasa `-env:UserInstallation`).

Y fijar `MacroSecurityLevel` de forma explícita en vez de depender del valor por defecto implícito
(M5), más `--norestore --nolockcheck --nodefault --nofirststartwizard`.

**9. Topes de recursos con valores por defecto finitos.**

El patrón a **no** copiar es el de A9 y M1 de SnapOtter: límites bien escritos, todos a `0`. En
FileX:

- Tamaño máximo de entrada, **y de salida** (M6, que no cubre nadie): matar la conversión si el
  fichero de salida supera un techo. Es la única defensa real contra la bomba de descompresión de
  salida.
- Megapíxeles máximos. Y cuidado con el `?? false` de A9: en Pillow es `Image.MAX_IMAGE_PIXELS`
  (que ya trae un valor por defecto — no ponerlo a `None`); en libvips/pyvips, no desactivar el
  techo integrado.
- Páginas máximas de PDF, duración máxima de audio y vídeo.
- Espacio máximo del directorio de trabajo.

Todos con un valor por defecto **razonable y distinto de cero**, y que el operador pueda subir, no
"activar".

**10. Aislamiento: no-root siempre, y contenedor endurecido cuando lo haya.**

Cuatro de seis corren como root (A13). Para el proceso local, FileX debe negarse a ejecutar los
motores como root (o al menos avisar de forma prominente). Para el despliegue en contenedor:
`USER` no-root en el Dockerfile —no solo en el entrypoint—, `cap_drop: ALL`,
`no-new-privileges:true`, perfil `seccomp` y sistema de ficheros de solo lectura salvo el
directorio de trabajo. Ninguno de los seis tiene seccomp o apparmor: verificado.

**11. Recolección de temporales que sobreviva a un `SIGKILL`.**

`finally` no basta (M9). Barrido por TTL **al arrancar** y periódico sobre el directorio de trabajo,
al estilo de `TempFileCleanupService` de Stirling-PDF y del barrido de ConvertX
(`src/index.tsx:76-99`), que en esto son los mejores del grupo. Directorios de trabajo en `0700`, no
`0755` (M9, gotenberg).

### Prioridad 3 — Cuando exista superficie de red

**12. Sin autenticación no se escucha en red.** Si FileX expone HTTP, que no repita C3: nada de
"activable". Si no hay credencial configurada, ligar solo a `localhost` o negarse a arrancar.
Y `allow_unauthenticated` con valor por defecto `False`, como transmute (P12) — el único que lo hace
bien.

**13. Limitación de tasa ponderada por coste.** Solo uno de seis la tiene, y uniforme (M7). Para un
llamante que es un agente, el límite debe ser por **coste estimado de la conversión** (megapíxeles,
duración, páginas), no por número de peticiones: mil listados de formatos y mil transcodificaciones
de vídeo no pueden valer lo mismo.

**14. Nada de CORS comodín con credenciales, ni CSRF desactivado** (C2). Y si hay salida de red
(descarga de URL, webhooks), la validación de C3/A10/P6: fallo cerrado, bloqueo de IPs privadas y de
metadatos de la nube **activado por defecto**, revalidación en cada redirección y pinning de IP. Sin
copiar la arista de A2 en la que un acierto en la lista de permitidos desactiva el resto de
comprobaciones.

---

### Una observación final sobre el llamante no humano

Tres de estos hallazgos cambian de gravedad cuando el que llama es un agente, y conviene decirlo
explícitamente porque es fácil pasarlos por alto:

- **A4 (el llamante elige el motor).** En una interfaz web es una rareza; con un agente al otro lado
  es un vector directo. Si FileX deja elegir motor, debe validar que ese motor declare soportar el
  par origen→destino real del fichero — validado por contenido, no por extensión.
- **Sobrescritura y borrado.** Ninguno de los seis lo trata como algo delicado porque todos trabajan
  sobre ficheros que ellos mismos han creado. FileX trabajará sobre los ficheros del usuario. Un
  agente que reintenta una operación fallida es el caso normal, no el excepcional.
- **Los mensajes de error son entrada del modelo.** M11 (trazas de pila en la respuesta) deja de ser
  solo una fuga de información: el texto de error de un motor externo entra en el contexto del
  agente y puede influir en su siguiente acción. Los errores que FileX devuelva por MCP deben ser
  estructurados y de vocabulario cerrado, nunca la salida cruda de `stderr`.

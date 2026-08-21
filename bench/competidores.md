# FileX — Cara a cara real contra los competidores: SnapOtter vs ConvertX

**Fecha:** 2026-08-19. **Estado:** cerrado. **96 invocaciones reales de conversión**
(38 casos de matriz + 1 reintento + 57 pasadas cronometradas), todas ejecutadas
**de una en una** contra los contenedores ya levantados.

Este documento cierra el criterio que quedaba incumplido del plan: hasta ahora se sabía que
SnapOtter y ConvertX *respondían*, y qué hacía SnapOtter *según su código*, pero **ninguno de
los dos había convertido un solo fichero**. Aquí se les hace convertir el corpus, se guardan
todas las salidas y se comprueban una a una.

Salidas: `D:\Work\research\FileX\bench\salidas-competidores\` (`snapotter\`, `convertx\`,
`gotenberg\`) — 45 ficheros y 47 MB de SnapOtter, 42 y 82 MB de ConvertX, 4 y 40 KB de
Gotenberg. 128 MB en total. Se conservan **todas** las salidas de la matriz; de las
repeticiones cronometradas sólo se descartaron los PNG duplicados de 31 y 70 MB del TIFF
patológico.

---

## 0. Advertencia que condiciona la lectura entera

La VM de Docker tiene **2 vCPU y 1,86 GiB de RAM** (`docker info` → `NCPU=2`,
`MemTotal=1996603392`), frente a los 12 núcleos y 32 GB del anfitrión. Es una decisión
deliberada del usuario en su `.wslconfig` y **no se ha tocado**.

Consecuencias, que deben acompañar a cualquier cita de este informe:

1. **Los tiempos de §7 sólo sirven para comparar SnapOtter contra ConvertX entre sí.**
   Ambos corren en la misma VM estrangulada y sufren idéntica restricción, así que la
   comparación *relativa* es legítima. Compararlos con los tiempos nativos de
   `bench/results.md` **no lo es**: son magnitudes de mundos distintos.
2. **Los cinco contenedores comparten esos 1,86 GiB.** Cualquier cifra absoluta está
   inflada por contención de memoria y por 2 vCPU repartidos entre PostgreSQL, Redis,
   SnapOtter, ConvertX y Gotenberg.
3. **Todo se ejecutó estrictamente en serie.** Con 2 vCPU, lanzar dos conversiones a la vez
   habría falseado ambas. No hay ni una sola medición concurrente en este informe.

Resultado relevante sobre el punto 2: **no hubo ningún OOM.** Se vigiló
`OOMKilled`/`RestartCount` de ambos contenedores antes y después de cada caso pesado
(TIFF de 72 MB, PDF escaneado de 8,5 MB, MKV de 4 MB, vídeo 1080p de 16 MB) y siempre
quedó en `OOMKilled=false Restarts=0 running`. El límite de 1,86 GiB **no llegó a ser el
factor limitante** con este corpus; sí lo es el tiempo de CPU.

---

## 1. Resumen ejecutivo

| | SnapOtter | ConvertX |
|---|---|---|
| Casos de la matriz intentados | 19 | 19 |
| Éxitos | **18** | 15 |
| Fallos | 1 | 4 |
| Fallos *silenciosos* (HTTP éxito, fichero inservible) | 0 | **1** |
| Degradaciones silenciosas de calidad | **1** (16→8 bits) | 2 (DPI fijo, bitrate fijo) |

Los tres hallazgos que más importan a FileX:

1. **ConvertX puede declarar "Done" y entregar un fichero que no es del formato pedido.**
   `png → avif` con ImageMagick devuelve estado *Done* y un fichero `.avif` que es un
   **PNG** (`89 50 4E 47`). El error real (`no encode delegate for this image format 'AVIF'`)
   sólo aparece como *warning* en el log del contenedor y nunca llega al usuario. Es
   exactamente el caso "HTTP 200 con fichero corrupto = fallo" del encargo.
2. **Los dos motores descartan silenciosamente la segunda pista de audio.** El MKV de
   2 pistas sale con 1 en ambos, sin aviso. Es un fallo compartido y una oportunidad
   directa para FileX.
3. **SnapOtter clava el CSV patológico y ConvertX ni siquiera puede intentarlo**: su
   conversor de datos (`dasel`) está roto en la imagen publicada.

---

## 2. Cómo se invoca cada motor (descubrimiento de la API)

Esta sección es el entregable reutilizable: si algún día FileX usa estos motores como
referencia o como back-end, esto es lo que necesita.

### 2.1 SnapOtter v2.2.0 — REST documentada, un solo POST por conversión

**Bloqueo de primer arranque (imprescindible).** La cuenta `admin`/`admin` nace con
`mustChangePassword: true` y **toda** la API devuelve `403 {"error":"Password change
required","code":"MUST_CHANGE_PASSWORD"}` hasta que se completa el cambio. No es opcional:
sin este paso no se puede convertir nada por API.

```
POST /api/auth/login             {"username":"admin","password":"admin"}  -> {"token": "..."}
POST /api/auth/change-password   {"currentPassword":"...","newPassword":"..."}  -> {"ok":true}
POST /api/auth/login             (de nuevo: el cambio invalida las demás sesiones y las API keys)
```

> En este banco de pruebas la contraseña de `admin` quedó cambiada a `<CONTRASENA-REDACTADA>`
> (contenedor local de investigación, no es un secreto real). Sin ese cambio, `bench/docker.md`
> no habría podido ir más allá de comprobar que el servicio responde — que es justo donde
> se quedó.

**No hay paso de subida previo.** Un único POST multipart lleva el fichero y los ajustes:

```bash
TOKEN=...   # de /api/auth/login
curl -X POST http://localhost:1349/api/v1/tools/<seccion>/<toolId> \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@entrada.png" \
  -F 'settings={"format":"webp","quality":85}'
```

- `<seccion>` ∈ `image | video | audio | pdf | files`. Cuidado: las hojas de cálculo caen
  en **`files`**, no en `pdf`.
- `settings` es un JSON en un campo de texto (máx. 65 536 B). El nombre del campo de
  fichero no se valida.
- Autenticación: `Authorization: Bearer <token>`; sirve igual una API key
  (`POST /api/v1/api-keys` → `si_<96 hex>`).

**Respuesta híbrida, síncrona o asíncrona según la herramienta:**

- Herramientas rápidas → **200** con
  `{"jobId":..., "downloadUrl":"/api/v1/download/<jobId>/<fichero>", "originalSize":..., "processedSize":...}`
- Herramientas largas (`convert-video`, `video-to-gif`, `excel-to-pdf`,
  `convert-spreadsheet`) → **siempre 202** `{"jobId":...,"async":true}`.
  También caen aquí las rápidas que se pasen de la ventana `SYNC_WAIT_MS` (8 s).

**El seguimiento es SSE, no hay endpoint de sondeo de estado:**

```bash
curl -N http://localhost:1349/api/v1/jobs/<jobId>/progress
# data: {"phase":"processing","percent":42,...}
# data: {"phase":"complete","percent":100,"result":{"downloadUrl":"/api/v1/download/..."}}
```

El flujo se autocierra en `phase: complete|failed`; el frame final trae el `downloadUrl`,
que es la única forma de saber el nombre del fichero de salida en los trabajos asíncronos.
Late un `{"type":"heartbeat"}` cada 20 s, así que el cliente necesita un *read timeout* > 30 s.

**Descarga:** `GET /api/v1/download/<jobId>/<fichero>` — **pública**, sin cabecera de
autenticación: el UUID del trabajo actúa de *capability token*.

**Descubrimiento del catálogo:** no hay un endpoint que liste todas las herramientas.
Lo que hay es `GET /api/v1/tools/popular`, `GET /api/v1/pipeline/tools` (incompleto: omite
rutas propias como `pdf-to-image` e `image-to-pdf`) y, lo único fiable,
`GET /api/v1/openapi.yaml` más `/llms.txt` y `/llms-full.txt`.

Identificadores usados en esta prueba:

| Operación | Ruta |
|---|---|
| imagen → imagen | `/api/v1/tools/image/convert` `{"format":"webp\|avif\|png...","quality":1-100}` |
| imagen → PDF | `/api/v1/tools/image/image-to-pdf` `{"pageSize":"A4","orientation":...,"margin":...}` |
| PDF → imagen | `/api/v1/tools/pdf/pdf-to-image` `{"format":"png","dpi":36-2400,"pages":"all"}` |
| hoja de cálculo → PDF | `/api/v1/tools/files/excel-to-pdf` `{}` (acepta xlsx/xls/ods/csv) |
| vídeo → vídeo | `/api/v1/tools/video/convert-video` `{"format":"mp4\|webm\|...","quality":"high\|balanced\|small"}` |
| vídeo → GIF | `/api/v1/tools/video/video-to-gif` `{"fps":1-30,"width":64-1280,"startS":...,"durationS":...}` |
| extraer audio | `/api/v1/tools/video/extract-audio` `{"format":"mp3\|wav\|m4a\|ogg"}` |
| audio → audio | `/api/v1/tools/audio/convert-audio` `{"format":...,"bitrateKbps":32-320,"sampleRate":...}` |
| CSV ↔ JSON | `/api/v1/tools/files/csv-json` `{"pretty":true}` (dirección inferida por la extensión) |

Límites relevantes: `MAX_UPLOAD_SIZE_MB=100` por fichero (→ **413**), `SYNC_WAIT_MS=8000`,
`JOB_TIMEOUT_FAST_S=120`, `JOB_TIMEOUT_LONG_S=7200`, `LIBREOFFICE_TIMEOUT_S=120`,
`FILE_MAX_AGE_HOURS=72` (las salidas caducan).

**Trampa encontrada en el código**, no documentada: en los *presets* del grupo `registry`
el esquema de ajustes se estrecha a `z.object({})` salvo unas pocas excepciones. Es decir,
llamar a `/video/mp4-to-gif` con `{"fps":24,"width":800}` **descarta esos parámetros en
silencio** y aplica los valores por defecto. Hay que llamar a la herramienta base
(`video-to-gif`) para que los ajustes surtan efecto. Esto es una degradación silenciosa
de calidad camuflada de comodidad — justo lo que FileX debe evitar.

### 2.2 ConvertX v0.18.0 — no hay API, hay un formulario web

ConvertX **no expone API REST**: es una aplicación Elysia/Bun con rutas pensadas para un
navegador. Se conduce con multipart + cookies, en cuatro pasos y manteniendo la sesión:

```
GET  /                         -> fija cookies `auth` (JWT) y `jobId`; CREA un trabajo nuevo
POST /upload                   -> multipart, campo `file` (admite varios)
POST /convert                  -> form-urlencoded:
                                    file_names = ["entrada.png"]      (JSON en una cadena)
                                    convert_to = "webp,vips"          ("<formato>,<conversor>")
                                  responde 302 -> /results/<jobId>
POST /progress/<jobId>         -> HTML; el estado por fichero es texto plano:
                                    "Done" | "Failed, check logs" | "File type not supported"
GET  /download/<userId>/<jobId>/<fichero>   (el userId de la URL se ignora: manda la cookie)
GET  /archive/<jobId>          -> tar con todas las salidas
```

Detalles que costó descubrir y que hacen falta para automatizarlo:

- **Cada `GET /` crea un trabajo nuevo** y reescribe la cookie `jobId`. Sin ese GET previo,
  `/upload` y `/convert` redirigen a `/` y no hacen nada.
- El nombre de salida es **el de entrada con la extensión sustituida** (`tipico.png` →
  `tipico.webp`). No lo devuelve ningún JSON: hay que construirlo.
- `convert_to` es un par `"<formato>,<conversor>"`. El conversor es obligatorio y
  **sensible a mayúsculas** (`markitDown`, no `markitdown`).
- No hay estado JSON en ninguna parte: el progreso se lee **raspando HTML**.
- `ALLOW_UNAUTHENTICATED=true` + `UNAUTHENTICATED_USER_SHARING` hacen que el `user.id` sea
  `0`, de ahí que las rutas internas sean `./data/uploads/0/<jobId>/`.

**Inventario declarado** (`GET /converters`, tabla HTML): 20 conversores. Los relevantes:

| Conversor | Entradas declaradas | Salidas declaradas |
|---|---:|---:|
| `ffmpeg` | 473 | 202 |
| `imagemagick` | 245 | 183 |
| `graphicsmagick` | 167 | 130 |
| `assimp` (3D) | 77 | 23 |
| `pandoc` | 43 | 65 |
| `vips` | 45 | 23 |
| `libreoffice` | 41 | 22 |
| `calibre` (ebooks) | 26 | 20 |
| `libjxl`, `libheif`, `inkscape`, `potrace`, `vtracer`, `resvg`, `dvisvgm`, `xelatex`, `dasel`, `vcf`, `msgconvert`, `markitDown` | — | — |

Sobre el papel ConvertX cubre **muchísimo más terreno** que SnapOtter (3D, ebooks, LaTeX,
vectorización, wikis). §4 y §5 muestran cuánto de eso resiste el contacto con un fichero real.

### 2.3 Gotenberg 8.36 — usado aquí como testigo, no como competidor

No entra en la matriz (no es un conversor universal, es LibreOffice + Chromium tras HTTP),
pero se usó como **control independiente**: los `hoja.xlsx` y `hoja.ods` que necesitaba §4
no existían en el corpus y hubo que generarlos. Antes de usarlos se validaron contra
Gotenberg:

```bash
curl -X POST http://localhost:3200/forms/libreoffice/convert --form "files=@hoja.xlsx"
# HTTP 200 -> 14 268 B, %PDF-1.7
curl -X POST http://localhost:3200/forms/libreoffice/convert --form "files=@hoja.ods"
# HTTP 200 -> 15 042 B, %PDF-1.7
```

Así, cualquier fallo posterior de SnapOtter o ConvertX con esos ficheros sería atribuible
al motor y no a una entrada defectuosa. (Los ficheros se generaron en el *scratchpad*;
**no se escribió nada en `corpus/`**.)

---

## 3. Matriz de cobertura funcional

`OK` = éxito con salida verificada. `OK*` = éxito con **degradación de calidad**
(detalle en §5). `FALLO` = no produce salida. `FALSO OK` = el motor dice que ha funcionado
y el fichero **no** es lo que se pidió.

| # | Conversión | Entrada | SnapOtter | ConvertX | Nota |
|---|---|---|---|---|---|
| 1 | png → webp | `tipico.png` | OK | OK | equivalentes |
| 2 | png → avif | `tipico.png` | OK | **FALLO** (vips) / **FALSO OK** (imagemagick) | §5.1 |
| 3 | png → webp con alfa | `alpha.png` | OK | OK | transparencia conservada en ambos |
| 4 | jpg → png | `tipico.jpg` | OK | OK | |
| 5 | **tif 16 bits 72 MB → png** | `patologico_16bit.tif` | **OK\*** 16→8 bits | **OK** conserva 16 bits | §5.2 |
| 6 | imagen → pdf | `tipico.png` | OK (A4) | OK\* (página 1920×1080 pt) | §5.3 |
| 7 | pdf → png | `tipico_texto.pdf` | OK (150 dpi) | OK\* (72 dpi fijos) | §5.4 |
| 8 | **pdf escaneado → png** | `patologico_escaneado.pdf` | OK (150 dpi) | OK\* (72 dpi fijos) | §5.4 |
| 9 | **xlsx → pdf** | `hoja.xlsx` (generado) | OK | **OK** (¡no declarado!) | §4.1 |
| 10 | **ods → pdf** | `hoja.ods` (generado) | OK | **OK** (¡no declarado!) | §4.1 |
| 11 | csv → pdf | `patologico_bom.csv` | OK | OK | texto seleccionable en ambos |
| 12 | mp4 → webm | `trivial.mp4` | OK | OK | vp9 640×480 en ambos |
| 13 | **mkv 2 pistas → mp4** | `patologico_2pistas.mkv` | **OK\*** pierde 1 pista | **OK\*** pierde 1 pista | §5.5 |
| 14 | vídeo → gif | `trivial.mp4` | OK (fps/ancho aplicados) | OK\* (sin control) | §5.6 |
| 15 | extraer audio de vídeo | `tipico.mp4` | OK (192 kbps) | OK\* (64 kbps) | §5.7 |
| 16 | flac → mp3 | `tipico.flac` | OK (192 kbps) | OK\* (64 kbps) | §5.7 |
| 17 | wav → flac | `trivial.wav` | OK | OK | idénticos, 104 320 B ambos |
| 18 | **csv con BOM → json** | `patologico_bom.csv` | **OK** (perfecto) | **FALLO** | §4.2, §5.8 |
| 19 | json → csv | `tipico.json` | FALLO (razonado) | FALLO (roto) | §4.3 |

**Cobertura efectiva: SnapOtter 18/19, ConvertX 15/19** (16/19 si se cuenta el `.avif`
falso como éxito, que es justo lo que no hay que hacer).

### 3.1 Sobre el reparto de victorias

No es un barrido: cada uno gana en cosas distintas. ConvertX es el único que **conserva
los 16 bits** del TIFF patológico, que es un acierto de fidelidad de primer orden.
SnapOtter gana en control de parámetros, en el CSV y en no mentir sobre el formato de salida.

---

## 4. Verificaciones que el encargo pedía explícitamente

### 4.1 «ConvertX no declara hojas de cálculo: verifica si realmente falla»

**No falla: convierte xlsx y ods a PDF correctamente.** La declaración es la que está mal.

El conversor `libreoffice` de ConvertX declara 41 entradas y **ninguna es `xlsx`, `xls` ni
`ods`**: son el juego de filtros de *Writer* (`doc docm docx odt rtf ...`) más `csv`, `tab`
y `tsv`. Sin embargo, al forzar `convert_to=pdf,libreoffice` por la API, el log del
contenedor muestra:

```
convert /app/data/uploads/0/18/hoja.ods as a Calc document
   -> /app/data/output/0/18/hoja.pdf using filter : calc_pdf_Export
Converted ./data/uploads/0/18/hoja.ods from ods to pdf successfully using libreoffice. Done
```

Y el PDF resultante contiene el texto real y seleccionable:

```
$ pdftotext convertx/xlsx2pdf__convertx.pdf -
producto tornillo tuerca arandela  unidades precio  1200  0.05  800  0.03  450  0.02
```

**Conclusión:** ConvertX no valida la entrada contra su propia lista declarada; se la pasa
tal cual a `soffice`, que la acepta porque LibreOffice trae Calc. La capacidad **existe
pero está oculta**: la interfaz web construye la lista de destinos a partir de las entradas
declaradas, así que un usuario que suelte un `.xlsx` en el navegador **no verá la opción
PDF**. Sólo es alcanzable llamando a `/convert` directamente.

Es un defecto de catálogo, no de motor. Y es una lección para FileX: **la lista de formatos
declarada y lo que el motor realmente hace tienen que salir de la misma fuente**, o acabas
escondiendo funciones que ya tienes.

### 4.2 El CSV patológico (BOM, comas, comillas escapadas, salto embebido)

Entrada (`corpus/datos/patologico_bom.csv`, 88 B), con las cuatro trampas a la vez:

```
ef bb bf                          <- BOM UTF-8
id,nombre,notas
1,"Pérez, Juan","dijo ""hola"" y se fue"     <- coma en campo + comillas escapadas
2,Ñandú,"salto
de linea"                                     <- salto de línea dentro del campo
```

**SnapOtter — impecable.** `/api/v1/tools/files/csv-json`:

```json
[
  { "id": "1", "nombre": "Pérez, Juan", "notas": "dijo \"hola\" y se fue" },
  { "id": "2", "nombre": "Ñandú",      "notas": "salto\nde linea" }
]
```

Verificado punto por punto:

| Comprobación | Resultado |
|---|---|
| Coma dentro de campo intacta | ✔ |
| Comillas escapadas (`""` → `"`) | ✔ |
| UTF-8 (é, Ñ, ú) intacto | ✔ |
| Salto de línea embebido conservado | ✔ |
| **BOM consumido, no pegado a la cabecera** (clave `id`, no `\ufeffid`) | ✔ |
| **JSON de salida sin BOM** (correcto según RFC 8259) | ✔ |

El quinto punto es el que más se falla en la práctica y SnapOtter lo hace bien: si el BOM
no se consume, la primera columna pasa a llamarse `\ufeffid` y cualquier consumidor
posterior deja de encontrarla.

**ConvertX — no puede intentarlo.** Ver §4.3.

### 4.3 El conversor de datos de ConvertX está roto en la imagen publicada

`csv → json` y `json → csv` fallan los dos, con el mismo error:

```
Failed to convert ./data/uploads/0/20/patologico_bom.csv from csv to json using dasel.
error: Error: Command failed: dasel --file ./data/uploads/0/20/patologico_bom.csv --read csv --write json
dasel: error: unknown flag --file
```

No es que falte el binario: **está y responde**, pero ConvertX lo invoca con la sintaxis de
`dasel` v1 (`--file`) contra un `dasel` v2, que ya no acepta esa bandera. El propio log de
arranque del contenedor lo delataba a medias (`dasel is not installed`), porque su sonda de
versión también falla. Consecuencia: **ConvertX ofrece en su interfaz las conversiones
`yaml/toml/json/xml/csv` y ninguna puede funcionar.** Es publicidad de una capacidad
inexistente.

SnapOtter falla el `json → csv` **pero por una razón legítima y bien explicada**:

```
HTTP 422 {"error":"Processing failed",
          "details":"JSON input must be an array of objects to convert to CSV"}
```

`tipico.json` es `{"items":[...]}`, un objeto envolvente, no un array de objetos en la
raíz. La conversión no es representable como una tabla plana sin decidir por el usuario
qué rama aplanar. El contraste es lo interesante: SnapOtter dice **qué** pasa y **por qué**;
ConvertX dice `Failed, check logs` y esconde el motivo en el log del contenedor.

### 4.4 El TIFF de 72 MB: no hay OOM, hay pérdida de bits

`patologico_16bit.tif`, 4000×3000 a 16 bits, 68,7 MiB reales (72 MB en disco). Está por
debajo del tope de SnapOtter (`MAX_UPLOAD_SIZE_MB=100`), así que no se rechaza.

**Ninguno de los dos contenedores cayó.** Antes y después:
`OOMKilled=false Restarts=0 running` en los dos. Con 1,86 GiB compartidos, un PNG de
4000×3000 a 16 bits (≈ 69 MB de salida) se procesó sin tumbar nada. El resultado esperado
—"el OOM sería un hallazgo valioso"— **no se produjo**, y eso también es un dato: el límite
de RAM de esta VM aguanta este corpus.

Lo que sí apareció es una diferencia de fidelidad (§5.2).

### 4.5 El PDF escaneado

`patologico_escaneado.pdf` (8,5 MB, sin capa de texto, inclinado, con ruido) se rasteriza
sin problema en los dos motores. Pero conviene decir qué **no** se probó y por qué: **ninguno
de los dos hizo OCR**, porque no se les pidió y porque, según `bench/docker.md` §5.6, el
contenedor de SnapOtter arrancó **sin `torch`, `rembg` ni `mediapipe`**; sus herramientas de
IA devolverían `501 FEATURE_NOT_INSTALLED`. Recuperar la capa de texto de este PDF sigue
siendo terreno del carril de IA, no del de conversión.

Como comprobación de que la entrada no tiene capa de texto:
`pdftotext patologico_escaneado.pdf -` no devuelve texto útil, coherente con "escaneado".

---

## 5. Calidad de salida: donde se separan de verdad

Un HTTP 200 no es un éxito. Todas las salidas se verificaron con `magick identify`,
`ffprobe`, `pdftotext` y comprobación de firma de fichero.

### 5.1 El `.avif` que en realidad es un PNG (ConvertX)

Primer intento, `vips` — **falla limpiamente**, y el error es informativo:

```
Failed to convert ... from png to avif using vips.
error: Command failed: vips copy ./data/uploads/0/9/tipico.png ./data/output/0/9/tipico.avif
heifsave: Unsupported compression
```

Es decir: el `libvips 8.18.3` de la imagen trae libheif pero **sin codificador AV1**
(aom/rav1e/svt-av1), así que no puede escribir AVIF. Hasta aquí, correcto: falla y lo dice.

Segundo intento, `imagemagick` — **aquí está el problema**. ConvertX reporta:

```
Converted ./data/uploads/0/13/tipico.png from png to avif successfully using imagemagick. Done
stderr: magick: no encode delegate for this image format `AVIF' @ warning/constitute.c/WriteImage/1402.
```

`Done`. Y el fichero descargado:

```
$ head -c 16 img-png2avif__convertx-imagemagick.avif | xxd
00000000: 8950 4e47 0d0a 1a0a 0000 000d 4948 4452  .PNG........IHDR
$ magick identify img-png2avif__convertx-imagemagick.avif
... PNG 1920x1080 16-bit sRGB 42855B
```

**Es un PNG con extensión `.avif`.** ImageMagick, al no tener delegado AVIF, emite un
*warning* (no un error), cae de vuelta al formato de origen y sale con código 0. ConvertX
sólo mira el código de salida y comprueba que el fichero existe, así que lo da por bueno.

Frente a esto, SnapOtter produce un AVIF real:

```
$ head -c 16 img-png2avif__snapotter.avif | xxd
00000000: 0000 001c 6674 7970 6176 6966 0000 0000  ....ftypavif....
$ magick identify img-png2avif__snapotter.avif
... AVIF 1920x1080 8-bit sRGB 3137B
```

3 137 B frente a 42 855 B: **13,7 veces más pequeño**, que es justo el motivo por el que se
pide AVIF. El usuario de ConvertX se lleva un fichero 13,7× mayor que además reventará en
cualquier consumidor que lo abra por extensión.

**Esta es la lección más importante del informe para FileX** y se desarrolla en §8.

### 5.2 TIFF de 16 bits: ConvertX conserva, SnapOtter degrada

| | Formato | Dimensiones | Profundidad | Tamaño |
|---|---|---|---|---|
| Origen `patologico_16bit.tif` | TIFF | 4000×3000 | **16 bits** | 68,7 MiB |
| SnapOtter | PNG | 4000×3000 ✔ | **8 bits** ✘ | 31,7 MB |
| ConvertX (vips) | PNG | 4000×3000 ✔ | **16 bits** ✔ | 69,9 MB |

SnapOtter **tira la mitad del rango dinámico sin avisar**. Para una foto de consumo da
igual; para imagen científica, médica o de archivo —que es exactamente el tipo de fichero
que llega en TIFF de 16 bits— es una pérdida irreversible. Y no hay ningún parámetro en
`/api/v1/tools/image/convert` para pedir que se conserve: el esquema sólo admite `format`
y `quality`.

Aquí ConvertX gana claramente, y es su mejor resultado de toda la matriz.

### 5.3 imagen → PDF: página de documento vs página de píxeles

| | Versión PDF | Tamaño de página | Interpretación |
|---|---|---|---|
| SnapOtter | %PDF-1.3 | **595×842 pt** | A4 real, con margen: es un documento |
| ConvertX | %PDF-1.4 | **1920×1080 pt** | los píxeles convertidos en puntos: 67,7×38,1 cm |

SnapOtter expone `pageSize` (A4/Letter/A3/A5), `orientation`, `margin` y `collate`.
ConvertX no ofrece ningún parámetro: entrega una página de 68 cm de ancho que ninguna
impresora va a aceptar. Los dos son "PDF válido"; sólo uno es un documento.

### 5.4 PDF → imagen: 150 dpi contra 72 dpi fijos

| Caso | SnapOtter (dpi=150) | ConvertX (vips) |
|---|---|---|
| `tipico_texto.pdf` | 1240×1755 | 595×842 |
| `patologico_escaneado.pdf` | 971×1344 | 466×645 |

ConvertX rasteriza **1 punto = 1 píxel**, o sea 72 dpi, y no expone ningún control. Para un
PDF escaneado que luego haya que leer u OCRizar, 72 dpi es inservible: 150 dpi es el mínimo
práctico y 300 lo habitual. SnapOtter admite `dpi` de 36 a 2400, más `pages`, `colorMode`
y `quality`.

Además SnapOtter devuelve **todas las páginas** —un ZIP con `page-1.png`, `page-2.png`…
más una lista `pages[]` con la URL y el tamaño de cada una y un `pageCount`— mientras que
ConvertX entrega **un solo PNG**. Con este corpus no se nota (los dos PDF son de una
página, verificado), pero con un PDF de 50 páginas la diferencia es entre tenerlo todo y
tener la portada.

### 5.5 El MKV de 2 pistas: **los dos pierden una, en silencio**

| | Vídeo | Pistas de audio | Duración |
|---|---|---|---|
| Origen `patologico_2pistas.mkv` | h264 1280×720 | **2** (aac mono, aac mono) | 10,023 s |
| SnapOtter → mp4 | h264 1280×720 ✔ | **1** ✘ | 10,008 s |
| ConvertX → mp4 | h264 1280×720 ✔ | **1** ✘ | 10,008 s |

Los dos reportan éxito. Los dos entregan un fichero donde **falta la mitad del audio**.

La causa es la misma en ambos: envuelven `ffmpeg` sin `-map 0`, y la selección de flujos
por defecto de ffmpeg coge **un** flujo de cada tipo (el "mejor"). Es el comportamiento
por defecto de la herramienta, heredado sin pensar por los dos envoltorios.

Para un fichero con pista original + doblada, con comentario del director, o con audio
descriptivo, esto es una pérdida de datos que el usuario no tiene forma de detectar salvo
comparando con `ffprobe`. **Es el hueco más claro que este informe le encuentra a los dos
competidores a la vez.**

### 5.6 vídeo → GIF: parámetros que se aplican y parámetros que no existen

Se pidió `fps=12`, `width=480`, `durationS=5`:

| | Dimensiones | fps | Fotogramas | Tamaño |
|---|---|---|---|---|
| SnapOtter | **480×360** ✔ | **12** ✔ | 60 | 1,42 MB |
| ConvertX | 640×480 | 24 | 120 | 2,29 MB |

SnapOtter aplica lo pedido. ConvertX no tiene dónde pedirlo: reproduce el vídeo entero a
resolución y cadencia originales, y sale un GIF **61 % mayor**. (Recordatorio de §2.1: en
SnapOtter hay que llamar a `video-to-gif`, no al *preset* `mp4-to-gif`, o los parámetros se
descartan en silencio.)

### 5.7 Audio: 192 kbps contra 64 kbps

| Caso | SnapOtter | ConvertX |
|---|---|---|
| `tipico.flac` → mp3 | mp3 **192 kbps** (pedido) | mp3 **64 kbps** |
| `tipico.mp4` → mp3 | mp3 **192 kbps** | mp3 **64 kbps** |
| `trivial.wav` → flac | flac, 104 320 B | flac, 104 320 B (idéntico) |

Frecuencia de muestreo (44 100 Hz), canales (mono) y duración se conservan en todos los
casos en los dos motores. La diferencia está en el bitrate: SnapOtter expone
`bitrateKbps` (32–320) y `sampleRate`; ConvertX **no expone ninguno** y se queda con el
valor por defecto de `libmp3lame` para mono, 64 kbps. Triplicar la compresión sin
preguntar es una degradación audible.

En sin pérdidas (wav → flac) los dos producen exactamente el mismo número de bytes, como
debe ser.

### 5.8 Lo que ambos hacen bien

Para no dejar sólo la lista de defectos:

- **Transparencia:** `alpha.png` (200×200, alfa *Blend*) → webp con alfa conservado en los dos.
- **Dimensiones:** ni un solo caso de la matriz cambió las dimensiones sin que se pidiera.
- **Duración de medios:** conservada al milisegundo en los dos (10,008 s de 10,023 s en el
  remultiplexado, diferencia normal de contenedor).
- **Texto seleccionable:** los PDF generados desde xlsx/ods/csv conservan el texto extraíble
  con `pdftotext` en los dos motores, con idéntico contenido.
- **vp9 en webm:** los dos eligen vp9 y respetan 640×480 y 5 s.

---

## 6. Todos los fallos, con su error exacto

| # | Motor | Caso | Error literal | Naturaleza |
|---|---|---|---|---|
| 1 | ConvertX (`vips`) | png → avif | `heifsave: Unsupported compression` | **Fallo honesto.** libvips sin codificador AV1 |
| 2 | ConvertX (`imagemagick`) | png → avif | `magick: no encode delegate for this image format 'AVIF' @ warning/constitute.c/WriteImage/1402` — reportado como `Done` | **Fallo silencioso.** Entrega un PNG con extensión `.avif` |
| 3 | ConvertX (`dasel`) | csv → json | `dasel: error: unknown flag --file` → `ENOENT: no such file or directory, open './data/output/0/20/patologico_bom.json'` | Incompatibilidad de versión (v1 vs v2). Al usuario le llega `Failed, check logs` |
| 4 | ConvertX (`dasel`) | json → csv | idéntico al anterior | íd. |
| 5 | SnapOtter | json → csv | `HTTP 422 {"error":"Processing failed","details":"JSON input must be an array of objects to convert to CSV"}` | **Fallo legítimo y bien explicado**: la entrada no es representable como tabla |

Fallos de infraestructura: **ninguno**. Cero OOM, cero reinicios de contenedor, cero
timeouts, cero 413, cero 429 en las 96 invocaciones. Los únicos incidentes de transporte
fueron 3 resets de conexión durante la subida de cargas grandes, detallados en §7.4.

Nota de método sobre el caso 2: el encargo permitía dos intentos por problema. El intento 1
(`vips`) falló de forma honesta; el intento 2 (`imagemagick`) es el que destapó el fallo
silencioso. Sin ese segundo intento, ConvertX habría quedado registrado simplemente como
"no soporta AVIF", que es una conclusión mucho menos grave y **falsa**.

---

## 7. Tiempos comparados

> **Léase §0 antes que esta tabla.** Estas cifras salen de una VM de Docker con **2 vCPU y
> 1,86 GiB** compartidos entre cinco contenedores. **Sirven para comparar SnapOtter con
> ConvertX y para nada más.** Ponerlas junto a los tiempos nativos de `bench/results.md`
> sería un error de lectura: aquellos se midieron sin esta restricción.

### 7.1 Método

- **9 conversiones** que los dos motores completan con éxito, **3 pasadas cronometradas
  cada una por motor**: 54 mediciones, más 3 repeticiones de recuperación (§7.4) = 57.
- **Estrictamente en serie.** Nunca dos conversiones a la vez, ni entre motores. Con
  2 vCPU la concurrencia habría falseado ambas columnas.
- El cronómetro cubre la **operación completa de extremo a extremo**: subida HTTP +
  conversión + espera del resultado (SSE en SnapOtter, sondeo de `/progress` en ConvertX)
  + descarga del fichero. Es lo que mide un cliente real, y es idéntico para los dos.
- Estadístico: **mediana** de las 3 pasadas, no media. La dispersión de esta VM (§7.3) hace
  que la media sea inservible.
- Las mediciones de la matriz (§3) **no** entran aquí: son primeras invocaciones en frío
  (§7.2).

### 7.2 El arranque en frío domina todo lo demás

Antes de comparar motores, el efecto más grande del banco no es ninguno de los dos:

| Caso | 1.ª invocación (frío) | Mediana en caliente | Factor |
|---|---:|---:|---:|
| `pdf2png` SnapOtter | 8,42 s | 0,16 s | **53×** |
| `pdf2png` ConvertX | 13,18 s | 0,41 s | **32×** |
| `xlsx2pdf` SnapOtter | 10,78 s | 2,41 s | 4,5× |
| `xlsx2pdf` ConvertX | 3,90 s | 0,76 s | 5,1× |
| `vid-audio` SnapOtter | 2,63 s | 0,88 s | 3,0× |
| `img-png2webp` ConvertX | 1,34 s | 0,37 s | 3,6× |

Coincide con lo que ya avisaba `bench/docker.md` §5.5 para Gotenberg: **la primera medición
de cada motor hay que descartarla siempre**. Un 53× de diferencia entre la primera llamada
y la segunda arruinaría cualquier comparación que mezclara ambas.

### 7.3 Mediana de 3 pasadas (segundos, menos es mejor)

| Conversión | SnapOtter (crudos) | **med.** | ConvertX (crudos) | **med.** | Más rápido |
|---|---|---:|---|---:|---|
| `png → webp` | 0,28 · 0,76 · 1,58 | **0,76** | 0,37 · 0,37 · 0,67 | **0,37** | ConvertX 2,1× |
| `jpg → png` | 0,14 · 0,14 · 0,24 | **0,14** | 0,37 · 0,38 · 0,69 | **0,38** | SnapOtter 2,7× |
| `imagen → pdf` | 1,25 · 1,37 · 2,56 | **1,37** | 0,37 · 0,38 · 0,73 | **0,38** | ConvertX 3,7× |
| `pdf → png` | 0,13 · 0,16 · 1,10 | **0,16** | 0,41 · 0,41 · 0,42 | **0,41** | SnapOtter 2,6× |
| `xlsx → pdf` | 1,84 · 2,41 · 3,64 | **2,41** | 0,71 · 0,76 · 4,80 | **0,76** | ConvertX 3,2× |
| `flac → mp3` | 0,32 · 0,39 · 2,94 | **0,39** | 0,39 · 0,45 · 2,26 | **0,45** | SnapOtter 1,2× |
| `vídeo → gif` | 2,45 · 2,59 · 5,43 | **2,59** | 0,68 · 0,83 · 1,39 | **0,83** | ConvertX 3,1× |
| `extraer audio` | 0,73 · 0,88 · 2,77 | **0,88** | 0,66 · 0,74 · 1,40 | **0,74** | ConvertX 1,2× |
| `tif 16b 72 MB → png` | 3,41 · 4,28 · 13,77 | **4,28** | 4,33 · 4,55 · 24,66 | **4,55** | SnapOtter 1,1× |

**5 a 4 para ConvertX en número de casos**, pero el reparto no es aleatorio y las
diferencias grandes tienen explicación arquitectónica, no de motor:

- **Donde ConvertX gana por 3×** (`imagen→pdf`, `xlsx→pdf`, `vídeo→gif`) SnapOtter está
  pagando su **arquitectura asíncrona**: esas herramientas llevan `executionHint: "long"`,
  así que **siempre** responden `202` y obligan a abrir una conexión SSE aparte y esperar
  el frame `complete`. Es un coste fijo de ida y vuelta que no tiene nada que ver con la
  conversión. ConvertX, que ejecuta y deja el fichero en disco, se lo ahorra.
- **Donde SnapOtter gana** (`jpg→png`, `pdf→png`) son rutas síncronas, y ahí su
  respuesta directa `200 + downloadUrl` bate al ciclo de ConvertX de
  `GET /` + `POST /upload` + `POST /convert` + sondeo de `/progress` cada 300 ms.
- En `pdf → png` conviene recordar que **SnapOtter es 2,6× más rápido haciendo más
  trabajo**: rasteriza a 150 dpi (1240×1755) frente a los 72 dpi (595×842) de ConvertX,
  es decir ~4,3× más píxeles. Normalizado por píxel, la diferencia real es mucho mayor.
- En `vídeo → gif` pasa lo contrario: ConvertX es más rápido porque hace **menos**
  (no reescala a 480 px ni baja a 12 fps), y por eso entrega un GIF 61 % mayor (§5.6).

**Conclusión de rendimiento:** entre estos dos motores, en esta VM, **no hay un ganador
claro de velocidad**. Las diferencias medidas se explican por el modelo de invocación
(síncrono contra cola + SSE) y por cuánto trabajo hace realmente cada uno, no por que un
motor de conversión sea más rápido que el otro. Por debajo, los dos llaman a las mismas
herramientas: ffmpeg, LibreOffice, libvips/ImageMagick.

### 7.4 Dispersión y estabilidad: el dato más útil de esta sección

La variabilidad es enorme y es **el efecto directo de la restricción de la VM**:

| Caso | Mínimo | Máximo | Dispersión |
|---|---:|---:|---:|
| `tif 16b → png` ConvertX | 4,33 s | 24,66 s | **5,7×** |
| `tif 16b → png` SnapOtter | 3,41 s | 13,77 s | **4,0×** |
| `flac → mp3` SnapOtter | 0,32 s | 2,94 s | **9,2×** |
| `png → webp` SnapOtter | 0,28 s | 1,58 s | 5,6× |

Con 2 vCPU repartidos entre cinco contenedores, **la misma conversión del mismo fichero
tarda hasta 9 veces más según lo que estuviera haciendo la VM en ese instante.** Por eso
se usa la mediana y por eso cualquier diferencia inferior a ~2× de esta tabla (los casos
de 1,1×, 1,2×) debe considerarse **ruido, no señal**.

**Tres resets de conexión en 57 pasadas (5,3 %)**, todos durante la **subida** de las
cargas grandes:

```
ConnectionError: ('Connection aborted.',
  ConnectionResetError(10054, 'Se ha forzado la interrupción de una conexión
  existente por el host remoto'))
```

Dos en el TIFF de 72 MB (uno por motor) y uno en SnapOtter justo después de un caso
pesado. **No son OOM** —`OOMKilled=false`, `RestartCount=0` en todo momento— sino que el
servidor corta la conexión bajo presión de CPU mientras recibe el cuerpo multipart. Las
tres se repitieron y completaron a la primera (§ regla de dos intentos), y esas
repeticiones son las que aparecen en la tabla de §7.3.

Para FileX es una observación operativa útil: **subir por HTTP ficheros de decenas de MB a
un servicio con poca CPU falla de vez en cuando y hay que reintentar.** Un cliente sin
reintento habría registrado esos tres casos como fallos de conversión, que es justo lo que
no eran.

---

## 8. Qué hace mejor cada uno que el otro, y qué debe aprender FileX de ambos

### 8.1 Lo que SnapOtter hace mejor

1. **Es la única de las dos con una API pensada para máquinas.** REST documentada,
   `Bearer`, un POST por conversión, respuesta JSON con `downloadUrl`, `originalSize` y
   `processedSize`, y SSE para lo largo. ConvertX obliga a raspar HTML.
2. **Expone los parámetros que deciden la calidad**: `dpi`, `quality`, `bitrateKbps`,
   `sampleRate`, `fps`, `width`, `pageSize`, `margin`, `colorMode`, `pages`. Es la
   diferencia entre convertir y *controlar* la conversión, y explica casi todas las
   columnas "OK\*" de ConvertX en §3.
3. **Falla explicando por qué.** El `422 ... "JSON input must be an array of objects"` es
   accionable. `Failed, check logs` no lo es.
4. **Trata los documentos como documentos**: A4 real en imagen→PDF, todas las páginas más
   `pageCount` y URLs por página en PDF→imagen.
5. **Borda el CSV patológico**, incluido el detalle del BOM que casi todo el mundo falla.
6. **Codifica AVIF de verdad**, con 13,7× de reducción.

### 8.2 Lo que ConvertX hace mejor

1. **Fidelidad de bits en imagen.** Es el único que conserva los 16 bits del TIFF. Para
   imagen científica o de archivo, este punto solo puede pesar más que todo lo demás.
2. **Amplitud bruta de catálogo, sin comparación.** 20 conversores y territorios donde
   SnapOtter no entra: modelos 3D (`assimp`, 77 formatos), ebooks (`calibre`), LaTeX
   (`xelatex`, `dvisvgm`), vectorización rasterizado→SVG (`potrace`, `vtracer`),
   documentos y wikis (`pandoc`, 43→65 formatos), JPEG XL (`libjxl`).
3. **Se puede elegir el motor.** `convert_to="avif,imagemagick"` frente a
   `"avif,vips"` permite esquivar un motor que no puede con un formato. SnapOtter no
   ofrece esa elección: si su ruta falla, no hay plan B.
4. **Cero fricción de acceso.** Sin login, sin cambio de contraseña obligatorio, sin
   token. SnapOtter bloquea el 100 % de su API hasta que se cambia la contraseña de
   `admin` — el motivo por el que la fase anterior no pudo convertir nada.
5. **Sin límite de tamaño de subida.** `maxRequestBodySize: Number.MAX_SAFE_INTEGER`,
   frente a los 100 MB de SnapOtter.

### 8.3 Lo que **ninguno de los dos** hace, y FileX debería

1. **Conservar todas las pistas.** El fallo compartido de §5.5. Un conversor serio pasa
   `-map 0` (o pregunta), y si de verdad hay que descartar algo, **lo dice**.
2. **Verificar la salida antes de declarar el éxito.** Ni uno solo de los dos comprueba
   que el fichero producido sea del formato pedido. Un `head -c 12` y una tabla de números
   mágicos habrían atrapado el `.avif`-que-es-PNG en microsegundos.
3. **Distinguir "convertido" de "convertido sin pérdidas".** 16→8 bits, 192→64 kbps,
   150→72 dpi: los tres son degradaciones que el usuario no pidió y de las que no se entera.

### 8.4 Lo que FileX debe llevarse, en orden de importancia

**1. Un contrato de verificación posterior a la conversión, obligatorio.**
Es la conclusión central. Ninguna conversión debería poder declararse correcta sin pasar,
como mínimo:

- **firma del fichero** (número mágico) contra el formato pedido — atrapa el `.avif`/PNG;
- **flujos esperados frente a flujos obtenidos** (`ffprobe`) — atrapa la pista perdida;
- **propiedades declaradas frente a obtenidas**: profundidad de bits, dimensiones, dpi,
  bitrate, número de páginas — atrapa los tres casos de §8.3.3.

Y si un motor externo emite un *warning* pero sale con código 0, **eso no es un éxito**:
ImageMagick avisó y ConvertX no lo escuchó.

**2. Una única fuente de verdad para el catálogo de formatos.**
El caso xlsx→PDF de §4.1 es un aviso en los dos sentidos: ConvertX **esconde** una función
que sí tiene porque su tabla declarada no coincide con lo que el motor acepta. Si la lista
de formatos y el despachador no salen del mismo sitio, o mientes prometiendo de más, o te
saboteas prometiendo de menos.

**3. Un informe de fidelidad en cada conversión.**
No basta con devolver el fichero. Devolver junto a él qué se conservó y qué no —
"16 bits → 8 bits", "2 pistas de audio → 1", "192 kbps → 64 kbps", "150 dpi" — convierte
tres degradaciones invisibles en tres decisiones informadas. SnapOtter ya devuelve
`originalSize`/`processedSize`/`pageCount`; es el embrión correcto, sólo que se queda en
el tamaño.

**4. Parámetros de calidad de primera clase, con valores por defecto sensatos.**
Copiar de SnapOtter el conjunto (`dpi`, `quality`, `bitrateKbps`, `sampleRate`, `fps`,
`width`, `pageSize`, `margin`, `pages`, `colorMode`) y de ConvertX **nada** en este apartado:
sus valores por defecto (72 dpi, 64 kbps, página de 68 cm) son precisamente el problema.
Y no repetir el error de los *presets* de SnapOtter (§2.1), que **aceptan** parámetros y
los tiran a la basura sin avisar: un parámetro no soportado debe ser un error, nunca un
silencio.

**5. Varios motores por formato, con recurso alternativo — pero con verificación.**
La elección de conversor de ConvertX es buena idea (`vips` falló en AVIF donde otro podía
servir) y FileX debería tener esa cadena de recurso automática. Pero el mismo caso enseña
la trampa: **un recurso alternativo sin verificación es peor que no tenerlo**, porque
convierte un fallo honesto en un fallo silencioso. Recurso alternativo + verificación de
firma, siempre juntos.

**6. Errores accionables.** El `422 {"details":"JSON input must be an array of objects to
convert to CSV"}` de SnapOtter es el modelo. `Failed, check logs` es el antimodelo: obliga
al usuario a tener acceso al log del contenedor, que casi nunca tiene.

**7. Cuidado con la fricción de entrada.** El bloqueo `MUST_CHANGE_PASSWORD` de SnapOtter
es defendible en seguridad, pero es exactamente lo que impidió a la fase anterior convertir
un solo fichero. Si FileX obliga a algo antes del primer uso, que el mensaje de error diga
**cómo** desbloquearlo, no sólo que está bloqueado.

**8. Que el modo por defecto sea el fiel.** ConvertX conserva los 16 bits porque `vips`
lo hace por defecto, no por decisión de diseño. Da igual: el resultado es el correcto.
En FileX debería ser una decisión explícita — **preservar por defecto, degradar sólo si se
pide**.

---

## 9. Reproducibilidad

Clientes usados (en el *scratchpad* de la sesión, no en el repositorio):
`so_auth.py` (desbloqueo de primer arranque de SnapOtter), `so.py` (cliente REST + SSE),
`cx.py` (cliente multipart + cookies de ConvertX), `mkcalc.py` (generación de `hoja.xlsx`
y `hoja.ods`), `run.py` (matriz), `reps.py` (repeticiones).

Herramientas de verificación, todas en el anfitrión (no perturban la VM):
`magick identify` (ImageMagick 7.1.2), `ffprobe` (ffmpeg), `pdftotext` (poppler), y
`zipfile`/`json` de Python.

Ficheros **no** tocados, según el encargo: `analysis/`, `bench/docker.md`,
`bench/gpu-fase1.md`, `bench/gpu-fase2.md`, `bench/results.md`, `corpus/`, `repos/`,
`.wslconfig`, `.venv-ai`, `.venv-paddle`. No se usó la GPU. No se reinició ningún
contenedor.

Único cambio de estado en el entorno: **la contraseña de `admin` en SnapOtter**, que pasó
de `admin` a `<CONTRASENA-REDACTADA>` porque su API lo exige antes de atender ninguna petición
(§2.1). Es un contenedor de investigación local.

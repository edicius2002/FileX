# BENCHMARKS — los números que sostienen a FileX, en un sitio

**Curado el 03/09/2026.** Este documento no mide nada
nuevo: extrae de los informes de `bench/` —**100** a fecha de 04/09/2026, contados con
`git ls-files`— las cifras que ya están **MEDIDAS**, con
`n` declarado, y que le sirven a alguien que se pregunta *«¿debería usar esto?»* — no a
alguien investigando OCR, ppp o normalización, que tiene su propio rincón en `bench/`.

**Regla de esta curación, heredada de `CLAUDE.md` §3:** cada cifra cita el informe de
`bench/` y la sección exacta de donde sale. Antes de escribir cada fila de este documento se
reabrió el informe citado y se confirmó que el número coincide **literalmente** — es la misma
disciplina que exige la trampa 55 (*«una cifra citada entre informes puede venir de otra
métrica, y el texto no lo dice»*). Donde una cifra sólo vale con una salvedad, la salvedad
va al lado, nunca en una nota aparte que nadie lee.

---

## Resumen

| # | Cifra | Qué significa | Fuente |
|---|---|---|---|
| 1 | **Verificar cuesta el 0,032 % de convertir** (24,2 ms de verificación frente a 74,865 s de conversión, sobre las 39 órdenes del patrón oro) — **si se lee la cabecera en proceso**. Con `ffprobe`/`magick identify` la ratio sube al 9,6 % sostenido, y en 15 de las 39 órdenes verificar cuesta **más** que convertir | El «barato» del diferenciador nº 1 es cierto sólo con la implementación correcta | `bench/coste-verificacion.md` §3 |
| 2 | **Leer cabeceras en proceso es 145× más barato que lanzar un subproceso** (0,372 ms frente a 54,06 ms por fichero, mediana de 53 salidas × 15 repeticiones) | El coste no está en leer los bytes: está en crear el proceso | `bench/coste-verificacion.md` §0 y §4 |
| 3 | **GPU en un vídeo largo suelto: ×7,68. En un lote de 8 clips cortos: ×4,10** — el lote **diluye** la ventaja de la GPU, no la anula | Un «×N» sin la duración de la entrada no es un número | `bench/hito2-nvenc.md` §5 |
| 4 | **FileX añade +3,6 % (27,2 ms) sobre un `ffmpeg` NVENC crudo** de 753,5 ms (n=9, clip de 5 s) | El orquestador no se come la ventaja de la GPU | `bench/hito2-nvenc.md` §5 |
| 5 | **La exclusión de máquina (mutex + candado de fichero + identidad NTFS) cuesta el 0,319 % de una conversión** (1.169,7 µs de cerrojo, n=20.000 por celda, sobre una conversión `png→webp` de 367,0 ms, n=11) | Cerrar la carrera entre dos procesos `filex` no cuesta rendimiento medible | `bench/cerrojo-unico.md` §5 |
| 6 | **Frente a Gotenberg, mismo día y misma máquina: FileX-en-contenedor cubre 7/7 conversiones (Gotenberg 6/7, falla `epub→pdf`), pero es ×7,21 más lento por mediana** (n=11 por vía) | Cobertura completa tiene un precio de latencia, medido y no escondido | `bench/gotenberg-y-mcp.md` (C35) + `bench/oraculo-y-gotenberg.md` §2.2 |

---

## 1. Coste de verificación — el contrato de 5 puntos

**La cifra central: 0,032 %.** Las 39 órdenes del patrón oro convierten en 74.865 ms;
verificarlas las 39 con el motor en proceso cuesta 24,2 ms. Por categoría, la ratio va del
0,14 % (pdf) al 0,36 % (datos), y **la peor ratio individual de las 39 es el 3,14 %** — no
hay ni un caso en que verificar se acerque a costar lo que convertir. *(`bench/coste-verificacion.md`
§2 y §3.)*

**La salvedad que no se puede separar de la cifra:** esa cifra exige leer cabeceras en
proceso. Con `ffprobe`/`magick identify` —la implementación "obvia" que un lector daría por
sentada— el coste por fichero sube a 54,06 ms (**145× más caro**) y, en tanda sostenida,
la ratio verificar/convertir sube al **9,6 %** sobre las 39 órdenes; en **15 de las 39
(38 %)**, verificar con subprocesos cuesta **más** que convertir, hasta **397 %** en
`flac → wav`. El paralelismo no lo salva: el escalado se estanca en ×1,79 con 24 hilos sobre
12 núcleos, porque el cuello es la creación de proceso, no la CPU ni el disco.
*(`bench/coste-verificacion.md` §3 y §5; el 145× también en §0 y §4.)*

**Lo que la verificación atrapa, y a qué coste.** Reproducidos con los dos motores (en
proceso y por subproceso), el verificador atrapa los cinco fallos reales documentados en el
proyecto, con **0 falsos positivos sobre las 53 salidas del patrón oro**:

| Fallo | Origen | Coste de detectarlo (en proceso) |
|---|---|---:|
| PNG con extensión `.avif` | ConvertX | 22,4 ms (en frío; en caliente, igual al resto) |
| Pierde una pista de audio (`ffmpeg` sin `-map 0`) | ConvertX y SnapOtter | 0,99 ms |
| Degradación de 16 a 8 bits sin avisar | SnapOtter | 0,28 ms |
| Redimensionado no solicitado con barras | `image-worker-mcp` | 0,43 ms |
| Fichero de 0 bytes declarado como éxito | `video-audio-mcp` | 0,25 ms |

*(`bench/coste-verificacion.md` §6.)* Los tres primeros son exactamente los fallos que
`bench/competidores.md` §5.1, §5.2 y §5.5 documentó al hacer convertir el corpus real a
SnapOtter y ConvertX (ver §4 más abajo).

**Un fallo que ni el vocabulario de firmas atrapa, y que sí atrapa una regla de 0 coste.**
`magick x.png y.group4` (y otros 21 pseudoformatos de ImageMagick) devuelve `rc=0` y entrega
un **PNG** con la extensión pedida — el mismo patrón que el `.avif` de ConvertX, producido por
un motor de primera línea, 22 veces en la misma sesión. Ni el vocabulario de firmas viejo ni
el ampliado lo detectan (0 de 22): hace falta la regla **G6** (*la salida comparte firma con
la entrada y no era eso lo que se pedía*), que no necesita saber nada del formato de destino
y **cuesta 0** porque las dos firmas ya están calculadas. Sobre las 53 salidas del patrón oro,
G6 no da ni un falso positivo. *(`bench/firmas-contrato.md` §7.1.)*

**El quinto punto (que el motor no escribió nada fuera de lo declarado) tiene un coste
medido y depende del confinamiento.** Con directorio de trabajo desechable (censo sólo
después), el contrato completo pasa de 0,4254 ms a 0,4722 ms: **+11,0 %**. Sin directorio
desechable, sobre un directorio compartido real de 1.000 ficheros, el censo antes+después
cuesta 3,66 ms: **×8,6 el contrato entero**, y sale del camino caliente.
*(`bench/contrato-quinto-punto.md` §2.2.)*

**Cuánto costaría a un tercero replicar esto.** El verificador completo (sin dependencias
externas: sólo la biblioteca estándar de Python) son 1.503 líneas, de las que sólo el 26 %
(333 líneas) es la lógica de los cuatro puntos; el 53 % (671 líneas) es escribir los parsers
de cabecera de cada formato — PNG, JPEG, WebP, GIF, TIFF, ISO-BMFF, EBML, Ogg, RIFF, FLAC,
MP3, PDF, CSV/JSON — que es lo que compra el factor 145×. Y la primera versión, escrita al
pie de la letra del contrato, dio un **17-19 % de falsos positivos** antes de las
correcciones: el coste de implementación real no es la especificación, es la parte que no se
ve hasta ejecutar contra un patrón oro. *(`bench/coste-verificacion.md` §1.2 y §7.)*

---

## 2. GPU / NVENC en vídeo — la ventaja depende del tamaño de la entrada

**La refutación central: el lote diluye, no concentra.** `HUECOS.md` había declarado el lote
como *«el único escenario donde el 8,39× de HEVC decide algo»*. Medido con la vía real
(`Servicio.batch`, la que usan las cuatro superficies) sobre una carpeta de 8 clips de 5 s:
GPU 7.645,6 ms frente a CPU 31.330,0 ms (n=3), **×4,10** (un segundo arnés independiente dio
×4,43: el orden de magnitud se reproduce). Sobre la **misma tanda**, una conversión suelta de
20 s da **×7,68** (14.588,6 ms frente a 1.899,7 ms). *(`bench/hito2-nvenc.md` §5.)*

**El mecanismo, medido, no supuesto:** el arranque de `ffmpeg`, el confinamiento y el censo
del punto 5 son costes fijos que un clip corto no llega a amortizar:

| Duración del clip | `hevc_nvenc` | `libx265` | Ganancia (tanda A) | Ganancia (tanda B) |
|---:|---:|---:|---:|---:|
| 1 s | 660,4 ms | 3.871,5 ms | ×5,86 | ×2,44 |
| 2 s | 753,1 ms | 2.158,6 ms | ×2,87 | ×3,39 |
| 5 s | 775,1 ms | 3.934,1 ms | ×5,08 | ×4,68 |
| 10 s | 1.184,9 ms | 8.347,4 ms | **×7,04** | **×6,38** |
| 20 s | 1.932,5 ms | 15.202,3 ms | **×7,87** | **×6,83** |

**Salvedad obligatoria:** las celdas de 10 s y 20 s se reproducen entre las dos tandas; las
de 1 s y 2 s no (×5,86 frente a ×2,44 sobre el mismo fichero) — por debajo de ~5 s la
diferencia es el suelo del instrumento, no una medida. *(`bench/hito2-nvenc.md` §5, misma
sección.)*

**El coste de FileX sobre el motor crudo, aislado (n=9, clip de 5 s):**

| Vía | `ffmpeg` crudo | `FileX.convertir` entero | Fijo |
|---|---:|---:|---:|
| `hevc_nvenc` | 753,5 ms | 780,7 ms | **+27,2 ms (+3,6 %)** |
| `libx265` | 4.047,4 ms | 4.488,8 ms | +441,4 ms (+10,9 %) |

*(`bench/hito2-nvenc.md` §5.)*

**El desvío de bitrate de NVENC no es una constante, y hay que decirlo con el bitrate al que
se midió.** Frente al objetivo pedido: +9,82 % a 8 Mbps, +15,11 % a 2 Mbps, **+24,59 % a
1 Mbps** — el desvío **crece** al bajar el bitrate. El de `libx265` en el mismo barrido va de
+2,10 % a +10,35 %. Y una salvedad de diseño: el contrato de FileX da `ok` a las ocho celdas,
incluida la de +24,59 %, porque hoy sólo hay regla de bitrate para pistas de **audio**, no de
vídeo — queda declarado como hueco abierto, no oculto. *(`bench/hito2-nvenc.md` §4.3.)*

---

## 3. Exclusión de máquina — la seguridad no cuesta rendimiento medible

**0,319 % de una conversión.** El primitivo vigente (mutex `Global\` con DACL explícita +
candado de rango de bytes + identidad NTFS del destino) cuesta 1.169,7 µs (n=20.000 por
celda) sobre una conversión `png→webp` de 367,0 ms medida en la misma tanda (n=11). El mutex en sí cuesta
**18,1 µs**: por ese precio se toman los dos primitivos, porque ninguno cubre lo que cubre el
otro (el mutex cruza entre usuarios de Windows; el candado de fichero funciona en POSIX y dice
quién lo tiene). *(`bench/cerrojo-unico.md` §1.2 y §5.)*

**Se recupera solo, sin lógica de huérfanos:** un `taskkill /F` a mitad de conversión deja al
siguiente proceso entrar en **551,9 µs**, porque el sistema operativo suelta el candado al
morir el dueño — la alternativa (`O_CREAT|O_EXCL`) habría dejado un huérfano eterno.
*(`bench/cerrojo-de-maquina.md` §4.)*

**Sobrescribir un destino ya existente: ×18,0 más rápido que antes** (556,5 µs frente a
10.041,1 µs), porque el camino anterior copiaba 17 KB donde ahora se renombra con
`os.replace`. Cruzando de volumen sí hay un cargo real de +712,3 µs (+7,7 %), que sobre la
conversión de referencia es el 0,18 % adicional. *(`bench/ventana-antes-del-move.md` §5.1.)*

---

## 4. Frente a los competidores

**Lo que se descubrió haciéndolos convertir el corpus real** (96 invocaciones, 38 casos de
matriz, contra los contenedores ya levantados de SnapOtter y ConvertX): **SnapOtter 18/19
casos, ConvertX 15/19** (16/19 si se cuenta como éxito el `.avif` que en realidad es un PNG,
que es justo lo que no hay que hacer). El AVIF real de SnapOtter pesa 3.137 B; el PNG con
extensión `.avif` de ConvertX, 42.855 B — **13,7 veces más grande**, y revienta en cualquier
consumidor que lo abra por extensión. Los dos motores, además, descartan en silencio la
segunda pista de audio de un MKV de dos pistas — el mismo fallo, en los dos, por la misma
causa (`ffmpeg` sin `-map 0`). *(`bench/competidores.md` §3, §5.1 y §5.5.)*

**Salvedad que gobierna toda esta sección:** los contenedores de SnapOtter y ConvertX
corrieron en una VM de Docker con **2 vCPU y 1,86 GiB**, deliberadamente estrangulada. Sus
tiempos sólo son comparables entre sí — **nunca** contra los tiempos nativos de
`bench/results.md`, ni contra FileX corriendo fuera de esa VM. El propio informe lo dice en su
§0 y esta curación lo respeta: **no existe, en `bench/`, una medición directa de velocidad de
FileX nativo contra SnapOtter o ConvertX** — sólo la comparación de esos dos competidores
entre sí, y la comparación de FileX-en-contenedor contra Gotenberg que sigue abajo.
*(`bench/competidores.md` §0.)*

**Frente a Gotenberg, la única comparación directa que existe entre FileX y un competidor
real.** Con el mismo motor subyacente (LibreOffice) en las dos vías, para que la diferencia
medida sea de arquitectura y no de motor, sobre las mismas siete entradas del banco
documental:

| Entrada → PDF | Gotenberg | `filex-c13` |
|---|---:|---:|
| `docx`, `html`, `md`, `odt`, `rtf`, `txt` | 200, con bytes | `rc=0`, con bytes |
| `epub` | **500 · 0 B** | `rc=0` · 26.817 B (Calibre) |

**Cobertura: Gotenberg 6/7, `filex-c13` 7/7.** *(`bench/gotenberg-y-mcp.md`, sección C35.)*

Y en latencia, `txt → pdf`, n=11 por vía, mismo momento y misma máquina:

| Vía | mediana | p90 |
|---|---:|---:|
| Gotenberg | **483,2 ms** | 3.597,8 ms |
| `filex-c13` | **3.481,5 ms** | 5.862,4 ms |

**`filex-c13` es ×7,21 más lento que Gotenberg, por mediana.** *(`bench/oraculo-y-gotenberg.md`
§2.2.)* **Salvedad obligatoria, declarada por el propio informe:** la tanda salió etiquetada
`SUCIA` (CPU compartida con otro carril de trabajo en la misma máquina); se publica porque la
comparación es relativa dentro de la misma tanda y el efecto es grande (un orden de magnitud
más allá del ruido declarado), no porque la tanda estuviera limpia. El propio informe cierra
el balance con las dos mitades: *«cobertura, en contra (−1 arista); latencia, a favor (×7 más
rápido)»* — la decisión de si compensa es del proyecto, no de esta cifra.
*(`bench/oraculo-y-gotenberg.md` §2.1 y §2.4.)*

---

## 5. Coste de integrar lo que falta, medido en contenedor

Los dos únicos motores que no trae ninguna imagen levantada del proyecto (`qpdf` y
`tesseract`, que cierran 2 de los 7 casos `no_evaluable` del patrón oro) cuestan, añadidos a
la imagen de ConvertX: **ocho líneas de Dockerfile, 28,1 s de construcción (17,3 s de
`apt-get`) y +50 MB (+0,9 %)** sobre una imagen de 5,73 GB. Incluye `tesseract-ocr-spa`, que
de paso resuelve la distribución de `tessdata` en español sin copiar ficheros a mano.
*(`bench/invocacion-aristas.md` §9.)*

**La frontera del contenedor efímero (un `docker run` por conversión) cuesta 864 ms por
conversión** (mediana n=9) — el 13,2 % de un `docx→pdf` (6.523 ms) y el 4,2 % de un
`epub→pdf` (20.615 ms) con Calibre. El resto es el motor, no el arranque del contenedor: *«no
hay que optimizar el `docker run`, hay que optimizar Calibre, o no llamarlo»*. Aparte, y sin
confundirlo con el coste anterior: el arranque en frío de **Docker** tras reiniciar el propio
demonio es un suceso de una sola vez, no un coste por conversión — **34.672 ms** la primera
vez frente a una mediana normal de 6.523 ms. *(`bench/hito5-documental.md` §3.2 y §8, filas 6
y 7.)*

---

## 6. Coste de exponer FileX a un agente de IA (MCP)

Relevante para quien piensa usar FileX **desde un agente** (Claude u otro), no sólo desde la
línea de comandos.

**El catálogo MCP completo de FileX —5 herramientas (`convert`, `inspect`, `list_targets`,
`batch`, `job`), 215 aristas de conversión, 6 motores— cuesta 1.605 tokens.** Añadir tres
motores nuevos al registro sólo sube el catálogo +102 tokens (+6,8 %), sin herramientas
nuevas: el coste crece con las aristas, no con la superficie de la API. **MEDIDO** dos veces
por vías independientes con el mismo resultado. *(`bench/hito4-mcp.md` resumen ejecutivo #1,
§2 y §3; `bench/gotenberg-y-mcp.md`, sección C36.)*

**En un banco de 15 peticiones a un agente real (Claude Haiku) usando las herramientas MCP de
FileX: 0 % de fallos silenciosos, frente al 15–17 % que da un catálogo de referencia peor
diseñado** (sin `enum` de formatos válidos en el esquema de cada herramienta). **Salvedad de
potencia que el propio informe declara**: con n=15 (n=3 por caso), «0 % de fallo silencioso»
no se distingue de un 5 % real — sólo descarta con seguridad un fallo del orden del 15–17 %,
que es justo lo que había que descartar. Medido con un solo modelo (Haiku); una medición
relacionada indica que Sonnet falla **más** (17 %) con el catálogo escueto, y repetir este
banco con Sonnet queda `PENDIENTE`. *(`bench/hito4-mcp.md` §4.1 y §4.4.)*

**Leer la cabecera de un fichero en proceso (`inspect`) para no copiarlo antes de pasarlo a un
sondeo externo cuesta de 2,0× a 284× menos que copiar + `ffprobe`**, según el tamaño: de 2,0×
en un PNG de 0,04 MB a 284,4× en un TIFF de 68,7 MB (con un PNG casi vacío en 2,6× y un MP4 de
15,5 MB en 27,6×, en el mismo barrido de cinco ficheros); el propio `inspect` cuesta 0,21–0,59 ms.
**MEDIDO**, con una corrección explícita del proyecto sobre sí mismo: una medición anterior
había estimado el margen «de 30× a más de 3.000×» midiendo por error sólo «abrir y leer 64
KiB», no un `inspect` completo — el número de aquí es el corregido.
*(`bench/hito4-mcp.md` §6.4 y resumen ejecutivo #6.)*

**Un tercer punto de exclusión, de proceso y no de máquina, con el mismo patrón de coste
irrisorio:** el conjunto de destinos en curso que evita que dos conversiones simultáneas
dentro del mismo proceso pisen el mismo fichero de salida (el fallo real que lo motivó: tres
peticiones concurrentes con tres entradas distintas a la misma ruta de salida terminaban las
tres en `completed` con veredicto aprobado —dos `ok`, una `ok_parcial`— y sólo un fichero real
en disco) cuesta **3,2 µs — el 0,0013 % de una conversión de ~250 ms**. **MEDIDO**, n=20.000.
*(`bench/hito7-superficies.md`, citado también en `CLAUDE.md` trampa 26.)*

---

## 7. Qué NO está aquí, y por qué

Esta curación fue selectiva, no exhaustiva por pereza. Fuera quedó, con su motivo:

- **Cualquier cifra de OCR** (elección de `ppp`, factor `k` por motor, VRAM de PaddleOCR o
  EasyOCR, `--psm` de Tesseract). Son el grueso numérico de `bench/` — decenas de informes —
  pero responden a *«cómo calibrar OCR dentro de FileX»*, no a *«debería usar FileX»*. Quien
  lo necesite tiene `bench/k-por-motor.md`, `bench/ppp-y-normalizacion.md`,
  `bench/suelo-ppp.md` y compañía.
- **Una comparación de velocidad entre FileX nativo (sin contenedor) y SnapOtter o
  ConvertX.** No existe medida en `bench/`: lo único medido es SnapOtter contra ConvertX entre
  sí (`bench/competidores.md`, en una VM restringida) y FileX-en-contenedor contra Gotenberg
  (`bench/oraculo-y-gotenberg.md`, en la máquina nativa). Inventar la primera comparación
  habría violado la regla explícita de este encargo. **Queda como hueco real, declarado, no
  medido esta ronda.**
- **Las cifras de `bench/gpu-fase1.md`/`bench/gpu-fase2.md` tal como se publicaron
  originalmente.** El ×8,39 de HEVC que ahí se cita quedó **refutado por incompleto** en
  `bench/hito2-nvenc.md` §5 (era real para un clip largo suelto, pero se citaba como el
  escenario de lote, que es justo el que la GPU pierde). Se usa aquí la versión corregida.
- **El coste de `min(alfa)`, PSNR, RMSE y demás reglas de fidelidad (grupo C).** Son entre
  70× y 8.200× el contrato de 5 puntos (`bench/verificador-fidelidad.md` §2.2) y sólo se pagan
  si se pide comparación píxel a píxel — no forman parte del argumento de «verificar es
  barato», que es sobre el contrato de declaración, no sobre fidelidad de contenido.
- **Bugs de infraestructura encontrados durante la construcción de FileX** (contenedores
  `soffice` que sobreviven 37 minutos a un `taskkill /F /T`, Docker Desktop tardando 45
  minutos en volver a arrancar). Son reales y están en `bench/hito5-documental.md` §4.4 y
  §2.1, pero documentan robustez de la propia obra en construcción, no una cifra que ayude a
  decidir si usarla.
- **Cualquier cifra de `bench/` sin `n` declarado o marcada `PENDIENTE`/`INFERIDO`.**

---

*Cada cifra de este documento fue reabierta en su fichero de origen y confirmada literalmente
antes de publicarse aquí — la disciplina de la trampa 55 de `CLAUDE.md`. Este documento no
sustituye a `bench/`: es un mapa hacia él.*

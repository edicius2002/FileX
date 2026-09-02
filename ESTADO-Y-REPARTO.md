# FileX — Estado del repositorio y reparto del trabajo pendiente

**Fecha:** 21 de agosto de 2026, 03:30 · **actualizado a las 10:00 con la oleada 1 y E1 cerrados.** **Sustituye a** `AGENTES-PRUEBAS-PENDIENTES.md` (19 de agosto), cuyo bloque de contexto compartido y cuyas «marcas a batir» han quedado **invalidados** por `bench/ocr-ppp-nativos.md`.

> **Uso rápido:** §1 y §3 dicen dónde estamos y qué falta. §4 dice quién hace qué. Los prompts de §7 se copian tal cual: cada uno ya incluye el contexto que su agente necesita.

> ## ⚠️ Actualización del 21/08/2026, 10:00 — **cuatro agentes han cerrado**
>
> | Agente | Informe | Estado |
> |---|---|---|
> | **D1 · Consolidación** (A1-A5) | `bench/consolidacion-21ago.md` | ✅ **CERRADO** |
> | **G1 · Corpus d4 + asimetría** (B1+B2) | `bench/corpus-d4.md` | ✅ **CERRADO**, con `corpus/pdf/escaneado_d4*.pdf` y su `MANIFIESTO-d4.md` |
> | **V1 · Verificador + OCR de gs** (C1+C2) | `bench/verificador-ghostscript.md` | ✅ **CERRADO** |
> | **E1 · Aristas nominales** (C3+C8) | `bench/aristas-nominales.md` | ✅ **CERRADO** |
> | **D2 · Segunda consolidación** | `bench/consolidacion-2-21ago.md` | ✅ **CERRADO** — integra los tres anteriores en los maestros |
>
> **Sin lanzar: G2 (B3+B4+B5) y M1 (C4+C5).** §3 y §4 están actualizados abajo; **§5 (contexto compartido) y §6 (reglas comunes) también, y hay que pegar la versión nueva, no la vieja.**
>
> **Y tres resultados obligan a leer §5 antes de lanzar nada:** ~~el techo de ppp pasa a **absoluto (200)**~~ **(refutado a las 14:00, ver abajo)**, la **normalización del detector de RapidOCR** cambia la tabla de selección de motor, y **CPU y GPU no dan la misma salida**.

> ## ⚠️ Actualización del 23/08/2026, 08:30 — **BARRIDO DE VERACIDAD del inventario (L1)**
>
> Este documento **se contradecía a sí mismo** y llevaba **dos días sin registrar trabajo hecho**. Lo que se ha corregido, y en qué dirección:
>
> | Dirección del error | Cuántas filas | Efecto sobre el proyecto |
> |---|---|---|
> | **Decía ABIERTO lo que estaba CERRADO** | **8** | El proyecto se creía **más atrasado** de lo que está |
> | **No registraba trabajo abierto que ya existía** | **24 filas nuevas**, de **15 informes sin una sola cita** | El proyecto se creía **más adelantado**: planificaba sin saber qué deuda había dejado el paquete `filex/` |
> | **Enunciado falso o desfasado** (la fila existía pero decía otra cosa) | **8** | Peor que las dos anteriores: **dirigía trabajo hacia un problema que ya no es el que hay** |
> | **Ilegible a máquina** | **21 de 63 filas de la §3 no tenían un solo emoji de color** (usaban ✅), y había 🔴 dentro de texto tachado | Un `grep` daba **32 rojos** sin que ese número significara nada |
>
> **Reglas de conteo, para que un `grep` valga:** el estado de una fila viva es **🟢 CERRADO · 🟡 EN CURSO o PARCIAL · 🔴 ABIERTO**, y **va en la última columna, una sola vez por fila**. Las filas históricas —las tachadas, que se conservan porque documentan una refutación— llevan **⚫ histórico** y **no cuentan**. Ningún emoji de estado dentro de texto tachado.
>
> **Y una precisión que corrige a quien lea la §4 de memoria:** un agente llamado **G2 sí corrió el 22/08**, pero **no hizo B3+B4+B5**: hizo B17+B18+B14 y escribió `bench/psm-y-rasterizador.md`. **`bench/motores-restantes.md` no existe** (comprobado sobre el árbol entero) y **marker, surya y MinerU siguen sin una sola medida**. La etiqueta de agente se reutilizó; el trabajo no se hizo. Lo mismo pasa con **M1**, que nombra a **dos** agentes distintos (`mcp-cabos-2.md` el 21/08 y `k-por-motor.md` el 22/08).

> ## ⚠️ Actualización del 21/08/2026, 14:00 — **tres agentes más han cerrado, y CORRIGEN a los anteriores**
>
> | Agente | Informe | Estado |
> |---|---|---|
> | **P1 · Curva de ppp + normalización** (B9+B10) | `bench/ppp-y-normalizacion.md` | ✅ **CERRADO** |
> | **P2 · Invocación de aristas** (C15+C17+C13) | `bench/invocacion-aristas.md` | ✅ **CERRADO** |
> | **P3 · Quinto punto, I9, `P9`, V2** (C9+C10+C11+C12) | `bench/contrato-quinto-punto.md` | ✅ **CERRADO** |
> | **D3 · Tercera consolidación** | `bench/consolidacion-3-21ago.md` | ✅ **CERRADO** — integra los tres en los maestros |
>
> **Y lo que hay que saber ANTES de lanzar nada más, porque corrige lo que este documento decía hace unas horas:**
>
> 1. **⚠️ EL BLOQUE DE ppp DE §5 ESTÁ REESCRITO. `clamp(nativos, 100, 200)` está REFUTADO, igual que el ×1,4 que lo precedió. NO HAY UNA REGLA GLOBAL DE ppp: hay una por motor, y la elección baja al ADAPTADOR de cada motor.** Si copias §5, copia la versión nueva.
> 2. **La corrección de normalización solo es segura sobre `PP-OCRv6 small`.** Aplicarla a la familia entera **empeora 12 de 42 celdas**, con +42,50 puntos en `PP-OCRv4 mobile`. **B11 cambia de contenido.**
> 3. **`P9` está refutada.** Si tu trabajo la usaba como señal, no la uses: **8,3 % de sensibilidad**. El sustituto medido es el acuerdo entre dos idiomas de OCR.
> 4. **El lock de GPU es de PROYECTO, no de máquina.** Una sesión de Claude en otro repositorio de la misma máquina dejó una tanda 12 minutos colgada. **Mira los PID antes de culpar al arnés.**
> 5. **⚠️ Y hay al menos un agente MÁS trabajando que no está en este documento.** Al consolidar aparecieron **`bench/salidas-firmas/` y `bench/salidas-mcp-cabos-2/` escribiéndose a las 14:05, sin informe `.md` que los explique**, y **`bench/scripts/verificador.py` ha pasado de las 4 185 líneas que dejó P3 a 4 567**. **Los dos directorios quedan fuera del commit y el verificador conviene esperarlo.** Si eres tú: cierra tu informe.

---

## 0. Lo que cambió desde el documento anterior

`AGENTES-PRUEBAS-PENDIENTES.md` se escribió para cerrar cuatro motores de IA sin probar. Desde entonces:

- **El agente A (OCRmyPDF) se ejecutó** → `bench/ocrmypdf.md`. Veredicto: **descartado como preprocesador**.
- **El agente B (marker) se quedó a medias**: instalado en `.venv-marker`, **sin una sola medida**. Ver la advertencia de §5.
- **Los agentes C (surya) y D (MinerU) nunca se lanzaron.**
- **La justificación entera de aquel documento se cayó.** Decía: *«en la dificultad 3 fallaron los tres motores de OCR probados»*. Era un artefacto de rasterización. **PaddleOCR resuelve d3 con 2,5 % de CER.** Las marcas que aquel documento manda batir no existen.

**Consecuencia:** los motores pendientes ya no se justifican por «nadie resuelve d3». Se justifican, si acaso, por completar el mapa — y eso los baja de prioridad. Lo que sube de prioridad es **construir un caso difícil que sí discrimine**.

---

## 1. Estado material del repositorio

**Ochenta y dos commits**, de `f0a0858` a `0b1946f`, y tras el último el árbol de trabajo quedó **limpio**. ~~Dieciséis commits, de `87091fe` a `69f08df`~~ — **los dos hashes murieron el 31/08**: el `git filter-repo --replace-text` que borró la credencial reescribió las 65 revisiones, así que **ningún hash citado antes de esa fecha resuelve**. El mapa exacto sobrevive en `.git/filter-repo/commit-map` y con él se repararon las **cuatro** citas del repositorio (§10). ~~**Un solo commit** (`87091fe`, *Investigación del ecosistema de conversión de archivos*). Todo lo posterior está sin versionar~~ — **CORREGIDO el 27/08: esa frase era del 21/08 y sobrevivió a quince commits**, entre ellos los cinco hitos y el paquete `filex/` entero. La tabla de abajo es el `git status` de aquel día y se conserva como registro histórico, no como estado:

| Estado | Ficheros |
|---|---|
| **Modificados sin commit** | `ANALISIS-COMPLETO.md`, `HUECOS.md`, `PLAN-ORQUESTADOR.md`, `RESULTADOS-MCP.md`, `analysis/00-licencias.md`, `analysis/00-mcp-componentes.md`, `analysis/00-mcp-filesystem.md`, `analysis/00-mcp-patrones.md`, `analysis/OCRmyPDF.md`, `bench/gpu-fase2.md`, `bench/scripts/verificador.py` |
| **Sin versionar** | `bench/mcp-cabos-sueltos.md`, `bench/ocr-ppp-nativos.md`, `bench/saturacion-herramientas.md`, `bench/verificador-fidelidad.md` + `bench/salidas-mcp-cabos/`, `salidas-ocr-ppp/`, `salidas-saturacion/`, `salidas-verificacion-fidelidad/` |

**La deuda documental es real y está fechada.** `HUECOS.md` se revisó a las **00:32**; los cuatro informes nuevos son de las **02:44–03:07**. Ninguno está integrado en ningún documento maestro.

### Informes por orden de antigüedad (los últimos)

> **Corregido el 23/08 (L1): esta tabla se cortaba el 21/08 a las 14:00 y le faltaban DIECISÉIS informes.** Entre lo que no figuraba estaba **la construcción entera del paquete `filex/`** —cuatro superficies, 129 pruebas, cuatro hitos del `PLAN-ORQUESTADOR.md` marcados HECHO— y **los tres sondeos que llevaron el grafo de 132 aristas `sin_sondear` a ~0**. Un inventario que no registra el trabajo hecho hace que el proyecto se planifique como si no existiera.

| Fecha | Informe | Qué cierra |
|---|---|---|
| 02/09 | **`bench/ci-y-contrato.md`** (worker2) | **`C27` cerrada** (G6 se queda en `aviso`, decisión definitiva) **y `C42` avanzada a 🟡.** Los 10 módulos que no corrían en el runner eran DOS mecanismos, no diez: sin ImageMagick instalado, y `corpus/video/tipico.mp4`+`corpus/audio/*.flac` como punteros de Git LFS sin descargar (trampa 34, sin proteger). Y un tercero que nadie había visto: `filex.gpu.Lock._vivo()` llama a `tasklist` (Windows) y en Linux siempre responde «vivo», así que un huérfano nunca se recupera — las descripciones "no hay tarjeta"/"no hay ffmpeg con NVENC" eran incorrectas. Arreglados con `skipUnless` honestos en 9 de 10 módulos (0 tocado en `filex/gpu.py`); `test_watcher_n` sin reproducir en tres sistemas de ficheros POSIX distintos. `ci/linux-apto.json` no se sobrescribe: la aproximación de contenedor no es el runner real |
| 01/09 | **`bench/k-oem-acantilados.md`** (worker1) | **`B16` cerrada refutando su propio enunciado, `B24` cerrada, `B23` a medias.** `B16`: con 13 puntos entre ×1,25 y ×1,40 no hay acantilado, hay un **peine** — celdas casi perfectas junto a colapsos totales de modo (verificado en el texto: 5 celdas devuelven sólo la primera línea de 3). `B24`: `--oem` no es un parámetro libre (legacy falla siempre con este `.traineddata`) y Ghostscript ya coincide con ImageMagick declarando el pHYs, 10/10. `B23`: el `k` de RapidOCR+R6 y PaddleOCR **se confirma** sobre un segundo corpus (`d5`); el de Tesseract no es comparable porque mezcla corpus y pHYs |
| 01/09 | **`bench/cajas-rapidocr.md`** (worker1) | **`B22` cerrada.** El pico de RapidOCR v6+R6 sobre `escaneado_d5c` no es del detector: **las 12 cajas y el área de página se mantienen estables en las 12 celdas**; lo que falla es el reconocedor sobre **una línea del bloque de 7 pt**, y el déficit reproduce byte a byte el «523 B frente a 641» ya citado. `escaneado_d5a` (control) no lo sufre por encima de su nativo |
| 01/09 | **`bench/saneo-inventario.md`** (worker2) | **El saneo de veracidad de las 111 filas de §3, y `C41`.** Dos filas verdes/rojas contradecían su propia evidencia y nadie las había movido: **`C28`** estaba 🟢 y su informe fuente declara sin resolver justo lo que la fila daba por cerrado (FATE «no lo he descargado», 17/23 de invocación sin probar); **`C32`** pedía arbitrar una contradicción que **`C31`/`C37` ya habían arbitrado**. Más `C22` (emoji equivocado puro) y `C41`/`C42` (enunciado desactualizado). Y los **17 manifiestos** que `C41` pedía, con un huérfano encontrado y documentado: `bench/salidas-cota-audio/`, un intento abandonado de N28 que **reproduce su propio error de forma determinista** |
| 01/09 | **`bench/psm-suelo-ppp.md`** (worker1) | **`B21` cerrada, `B22` a medias.** Las 96 celdas de Tesseract que faltaban: **el suelo de 100 ppp le INVIERTE el signo respecto de RapidOCR** y le gana hasta **20 puntos** en el documento de 60 ppp nativos. Y **se niega a comparar sus décimas con los 42,78 puntos publicados**, porque aquéllos se midieron con el `pHYs` **sin declarar**: con el verdadero en los dos lados el hueco comparable es **10,74**, y la diferencia que queda se deja **PENDIENTE** en vez de forzar una lectura |
| 01/09 | **`bench/suelo-ppp.md`** (worker1) | **`B21` y `B22`, a medias.** **El suelo de 100 ppp es DEL MOTOR y la media global lo oculta**: 336 celdas, 7 configuraciones, y el saldo 14/9/5 es un **empate engañoso** —sobre `escaneado_d5c` el suelo cuesta **+17,8** a RapidOCR v6+R6 y **gana −17,9** a docling+R6—. La curva **no es suave** y los picos son **pérdida de texto**, no mala lectura |
| 01/09 | **`bench/gotenberg-y-mcp.md`** (worker2) | **`C35` y `C36`, las dos a medias.** Gotenberg **no añade conversión sobre `filex-c13`**: 6 de 7 contra 7 de 7. Y §13 no tenía ocho pendientes sino **NUEVE**, de los que dos ya estaban cerrados: quedan **siete** |
| 31/08 | **`bench/lock-desde-python.md`** (worker1) | **`C38` y `C39`.** El lock desde Python, en dos intentos: **el primero rompía 5 pruebas y las 5 tenían razón**. La exclusión sólo en el mutex deja **dos poblaciones que no se ven** — trampa 96 |
| 31/08 | **`bench/bitrate-por-pista.md`** (worker2) | **`N28`, y `C25` a medias.** La resta de `-b:a` **se retira**: *pedido no equivale a obtenido*. Y el «bloqueo» de las semillas P2 era falso — **trampa 95**, el espejo de la 89 |
| 30/08 | **`bench/patron-multifichero.md`** | **`C22`.** El patrón oro no tenía ni una salida multifichero, así que el «0 falsos positivos» del punto 5 se apoyaba en cuatro casos fabricados |
| 30/08 | **`bench/aristas-y-tasa-audio.md`** | Las aristas y la tasa de audio |
| 29/08 | **`bench/hito6-sidecar.md`** | **Hito 6.** Dos `cudnn64_9.dll` distintas en el mismo venv: **quien carga primero decide** (trampa 82). Y un `stderr` en `PIPE` que nadie drena es un tope de **64 KiB** que cuelga el arranque |
| 29/08 | **`bench/lock-entre-interpretes.md`** (master) | **`C39`.** El lock de GPU **no cruza entre interpretes, y no falla callandose: BORRA el del otro**. Una sola celda verde de cuatro, y **WSL no se excluye ni consigo mismo**. El arnes mato a su propio sujeto **dos veces** y lo destapo el control positivo |
| 28/08 | **`bench/metrica-ocr.md`** (W) | **A7.** La métrica de OCR canónica pasa a ser la **acentuada**. Cuesta **4 celdas de 628, 0 inversiones**. Y *«el evaluador acentuado»* eran **DOS métricas**: la otra habría cambiado el ganador en **21 familias** |
| 28/08 | **`bench/contrato-familia-resvg.md`** (V) | **C19, C21, C29** y la respuesta medida a **C27**. La regla **A7** de fidelidad, el suelo de V8 —**refutado y puesto igualmente**— y el defecto que nadie había visto: **`EXT_FAMILIA` era código muerto** |
| 28/08 | **`bench/watcher-y-desechables.md`** (U) | **N4, N5, N14.** *«En POSIX no hay equivalente»* era una deducción **y era falsa**; el residuo de N5 hubo que **fabricarlo**; y **978 desechables huérfanos en cinco horas** |
| 28/08 | **`bench/cancelacion-entre-procesos.md`** (T) | **N10, N11, N13.** Cancelar entre procesos **de nunca a 456,8 ms**, y el mutex de la ronda anterior **se soltaba por accidente** |
| 28/08 | **`bench/contenedor-parar.md`** (Q) | **a4.** La orden **declara** el contenedor con `--name`: identificarlo pasa de 217,35 ms a **0,01**. Descarta `--cidfile` **sonándolo**, y encuentra el estado `Created`, que `docker ps` no lista |
| 28/08 | **`bench/cerrojo-unico.md`** (P) | **b1, b4.** `filex/cerrojo.py`, y el mutex `Global\` **refuta que hiciera falta elevar**. La trampa estaba dentro de la vía buena: la **DACL por defecto** no incluye a «Everyone» |
| 27/08 | **`bench/cerrojo-de-maquina.md`** (N-b) | **N1.** El cerrojo de destino entre procesos — y **la exclusión sola no bastaba**: FileX pisaba el fichero abierto de un tercero devolviendo `ok` |
| 27/08 | **`bench/cancelacion-y-servicio.md`** (N-a) | **C34, N6.** El asa del `Popen` **no se devuelve, se hace alcanzable**; `mcp.py` baja un **40,2 %** |
| 23/08 | **`bench/deuda-sondeo.md`** (D1) | **N3**, y **N2 refutada**: la huella del código, la **sexta dimensión** de la arista. 0 de 129 pruebas dependían del sondeo en disco |
| 23/08 | **`bench/phys-multimotor.md`** (G4) | **El `pHYs` fuera de Tesseract.** Veredicto provisional: PaddleOCR, RapidOCR y EasyOCR son **inmunes** (300 celdas, un solo `md5` por fila motor×documento). ~~NO ESTÁ CERRADO: hay un agente escribiéndolo ahora~~ **CERRADO ese mismo día**; la frase sobrevivió nueve días al agente que la escribió |
| 23/08 08:30 | **`bench/lock-de-maquina.md`** (L1) | **C26**: el lock de GPU pasa a `%TEMP%`, deja de quedarse huérfano y **detecta al ocupante que no coopera**. Más este barrido del inventario |
| 23/08 | **`bench/hito7-superficies.md`** (H7) | **Hito 7**: watcher + API HTTP + la prueba de R10. **Y el fallo que nadie veía: tres conversiones a la misma ruta de salida devolvían las tres `ok`** |
| 22/08 | **`bench/sondeo-documental.md`** (S3) | Las 23 aristas documentales `sin_sondear` en contenedor → 0 |
| 22/08 | **`bench/sondeo-ffmpeg.md`** (S2) | Las 70 aristas `sin_sondear` de ffmpeg |
| 22/08 | **`bench/sondeo-imagemagick.md`** (S1) | Las 62 aristas `sin_sondear` de ImageMagick |
| 22/08 | **`bench/hito5-documental.md`** (K1) | **Hito 5**: el motor documental en contenedor (`filex-c13`, no Gotenberg). **Matar el `docker run` NO mata el contenedor: 37 minutos** |
| 22/08 | **`bench/hito4-mcp.md`** (K3) | **Hito 4**: la capa MCP de FileX. **Dos criterios incumplidos y medidos** (catálogo 1.503 tok; latencia de R4 ×20,6) |
| 22/08 | **`bench/hito3-mudanza.md`** (K2) | **Hito 3**: el verificador al núcleo. **Y refuta dos cifras de `firmas-contrato.md` §10** |
| 22/08 | **`bench/consolidacion-4-22ago.md`** (D4) | La cuarta pasada: `mcp-cabos-2.md` y `firmas-contrato.md` en los maestros. **Abre el tercer sesgo, el de SEMILLA** |
| 22/08 | **`bench/corpus-d5.md`** (G3) | **B15, B19 y B12.** El fallo aritmético de la regla de ppp (16,78 puntos) y **el rasterizador vale CERO** |
| 22/08 | **`bench/psm-y-rasterizador.md`** (G2) | **B17, B18 y B14.** El `--psm` vale 42,78 puntos y **no es separable del `k`**; el `pHYs`, hasta 33 |
| 22/08 | **`bench/k-por-motor.md`** (M1, el segundo) | **B13.** El `k` es del **par (motor, documento)**: interacción 76,7 % |
| 22/08 | **`bench/firmas-contrato.md`** (F1) | **C14.** 24 → 147 nombres; el punto 1 pasa del 12,4 % al 54,2 %. **90 de 381 formatos no tienen marcador** |
| 21/08 14:17 | **`bench/mcp-cabos-2.md`** (M1, el primero) | **C4 entero y la mitad de C5.** Las herramientas MCP llegan **diferidas** |
| 21/08 14:00 | **`bench/consolidacion-3-21ago.md`** | La tercera pasada: los tres informes de la tarde en los maestros. **Corrige a la segunda en tres sitios** |
| 21/08 13:40 | **`bench/ppp-y-normalizacion.md`** | **La curva de ppp (B9) y la validación de la normalización (B10).** **Refuta las dos versiones de la regla de ppp**; la regla es **por motor** |
| 21/08 13:20 | **`bench/invocacion-aristas.md`** | **El 18,8 % del 50,5 % que era invocación** (C15), el censo de gs+Gotenberg (C17) y **`qpdf`+`tesseract`** (C13) |
| 21/08 13:00 | **`bench/contrato-quinto-punto.md`** | **El quinto punto y R18** (C9), **la regla I9** (C10), **`P9` refutada y `ocr: true`** (C11) y **el interruptor de V2** (C12) |
| 21/08 10:00 | **`bench/consolidacion-2-21ago.md`** | La segunda pasada de consolidación: los tres informes de la mañana en los maestros |
| 21/08 09:40 | **`bench/verificador-ghostscript.md`** | `min(alfa)` de TIFF/GIF/Adam7, V2/V5, el **OCR sin GPU** de Ghostscript y el **segundo testigo de ruido** |
| 21/08 09:20 | **`bench/aristas-nominales.md`** | **El 50,5 % de aristas nominales** (cierra el hueco 2), el quinto punto del contrato y 5 de los 7 `no_evaluable` |
| 21/08 09:10 | **`bench/corpus-d4.md`** | **`escaneado_d4`** y la **causa real de la asimetría de PaddleOCR** |
| 21/08 04:30 | `bench/consolidacion-21ago.md` | La primera pasada de consolidación |
| 21/08 03:07 | `bench/ocr-ppp-nativos.md` | La tabla canónica de OCR. Sustituye a `gpu-fase2.md` §5 |
| 21/08 02:49 | `bench/saturacion-herramientas.md` | El último pendiente conductual de MCP, con 540 ejecuciones |
| 21/08 02:48 | `bench/mcp-cabos-sueltos.md` | Los cinco cabos de `RESULTADOS-MCP.md` §13 |
| 21/08 02:44 | `bench/verificador-fidelidad.md` | `min(alfa)` en proceso y las reglas de fidelidad |
| 20/08 23:26 | `bench/ocrmypdf.md` | El artefacto de ppp y el descarte de OCRmyPDF |
| 20/08 23:21 | `bench/fidelidad-caminos.md` | 69 caminos ejecutados: refuta el multi-salto |
| 20/08 23:16 | `bench/coste-verificacion.md` | El coste del contrato: 0,032 % |
| 20/08 23:00 | `bench/sdk-mcp-capacidades.md` | Las tres eras de protocolo MCP |
| 20/08 22:48 | `bench/confinamiento-multimedia.md` | — |
| 20/08 22:08 | `bench/mcp-refs-multimedia.md` | — |
| 21/08 03:07 | `bench/gpu-fase2.md` | El carril GPU, fase 2: ¿es alcanzable el OCR en GPU? **Sustituido en su §5 por `ocr-ppp-nativos.md`**, y **hoy no es auditable** (N17): sus salidas de texto ya no existen |
| 20/08 | `bench/gpu-fase1.md` | El carril GPU, fase 1. Único material sobre **surya** (B4): *«NO FUNCIONA en GPU en esta máquina»* |
| 20/08 | `bench/referencia-nativa.md` | **El patrón oro**: qué producen `ffmpeg`, `magick` y `gswin64c` nativos. Es el que no se toca |
| 20/08 | `bench/mcp-ergonomia.md` | Ergonomía MCP medida: `markitdown-mcp` frente a `docling-mcp` |
| 20/08 | `bench/mcp-refs-confinamiento.md` | Confinamiento y mensaje de error al modelo, sobre la referencia oficial del protocolo |
| 19/08 | `bench/competidores.md` | Cara a cara real: SnapOtter frente a ConvertX, **96 invocaciones**. De aquí salen los tres fallos que el hito 3 reproduce |
| 19/08 | `bench/docker.md` | El entorno Docker de los competidores: los tres servicios en pie |
| 19/08 | `bench/results.md` | Fase 2, mediciones en la máquina real. El primero de todos |

---

## 2. Hallazgos consolidados

### 2.1 El argumento del producto, cerrado con su coste

**Hueco 1 — verificación obligatoria de la salida.** Único de los cinco que cumple los tres criterios (*nadie lo hace · es barato · lo nota el usuario*).

| Dato | Valor | Fuente |
|---|---|---|
| Fallos de verificación documentados | **7**, en **6** proyectos distintos | `HUECOS.md` §1 |
| Contrato en proceso | **0,372 ms** = **0,032 %** de convertir | `coste-verificacion.md` |
| Contrato con `ffprobe`/`magick identify` | **145× más caro**; en **15 de 39 órdenes (38 %)** verificar cuesta más que convertir | ídem |
| Punto 4 del contrato (*pedido vs obtenido*) | **187 de 333 líneas**, y lo único que atrapa el redimensionado no solicitado | ídem |
| Prototipo | **3.035 líneas**, sin dependencias. **5/5 fallos atrapados, 0 falsos positivos sobre 53 salidas** | `verificador-fidelidad.md` |
| `min(alfa)` en proceso | **66,0 ms** peor caso vs 734,6 ms de `magick`; **7 de 12 casos no leen un píxel** | ídem §1 |
| Fidelidad | **1.100× el contrato** (28.858 ms vs 26,1 ms sobre 53 salidas) → **fuera del camino caliente** | ídem §2 |

**La constante que se repite en las dos versiones del verificador:** entre el **5 y el 7 %** del código son *excepciones justificadas por datos* que **no son deducibles de la especificación escrita**. Salen de ejecutar contra el patrón oro. Es la parte que no se ve leyendo el contrato y es inseparable de él.

### 2.2 Lo refutado — el material más valioso del repositorio

| Tesis | Veredicto | Dónde |
|---|---|---|
| Multi-salto: **×2,93** de alcance | **REFUTADA.** Con motores instalados **1,93×**; solo **610 pares plausibles** (**+32,7 %**, no +193 %); **51 %** son «pásalo por PDF»; y **31,9 %** de acierto frente al 54,5 % de un salto | `fidelidad-caminos.md` |
| «Un catálogo de 27 herramientas satura la elección» | **REFUTADA con 540 ejecuciones.** 27 acertó **100 %/98 %**; 8 acertó **85 %/77 %**. El grande eligió **mejor** | `saturacion-herramientas.md` |
| «Los tres motores fallan en d3» | **REFUTADA.** Era un **×2 de interpolación** del arnés. PaddleOCR: **2,5 %** de CER | `ocrmypdf.md`, `ocr-ppp-nativos.md` |
| OCRmyPDF como preprocesador | **DESCARTADO.** Salida **bit a bit idéntica** a no usarlo; atravesar su ciclo sube RapidOCR de 1,3 % a **44,3 %** | `ocrmypdf.md` |
| «`-y` basta contra el deadlock de ffmpeg» | **REFUTADA, A/B causal.** `stdin` heredado cuelga **2/5**; `stdin=DEVNULL`, **0/5** | `mcp-cabos-sueltos.md` §4.3 |
| «El vector TOCTOU es sustituir el fichero» | **REFUTADA.** No funciona ni en Windows ni en Linux. El que **sí** funciona es **escribir en sitio**. Ventana: **99,6 %** de la conversión | ídem §5.2 |
| «RapidOCR falla en d3 por ser PP-OCRv5 mobile frente al medium» | **REFUTADA DEL TODO (21/08).** No es el tamaño (el **mismo** v6 small da 3,80 % en Paddle y 75,95 % en RapidOCR), no es el idioma del reconocedor (en v6 `es` y `en` son el mismo checkpoint) ni el del detector (en v6 hay uno solo). **Es que RapidOCR normaliza con `mean=std=0,5` lo que el modelo declara con ImageNet: 72,2 puntos por seis números** | `corpus-d4.md` §7 |
| «CPU y GPU dan salida idéntica carácter a carácter» | **REFUTADA.** **5 de 21 celdas difieren**, y la CPU es mejor en dos y peor en tres | `corpus-d4.md` §9.3 |
| «El techo ×1,4 de la regla de ppp» | **REFUTADO PARCIALMENTE.** Sobre `d4` (200 ppp nativos) el ×1,4 **empeora** a PaddleOCR 16,9 puntos. Propuesta: techo **absoluto** de 200. **PENDIENTE de barrer la curva** | `corpus-d4.md` §8 |
| **«El techo ABSOLUTO de 200 que sustituyó al relativo»** | **REFUTADO TAMBIÉN (21/08, 14:00), y por dos vías.** (a) **Los ppp no son la unidad**: el mismo mapa de bits en tres páginas da **19,13 / 19,63 / 36,24 %** a los mismos ppp y **coincide a la centésima** a los mismos píxeles (24 celdas). (b) Su techo **solo actúa bajando, y bajar cuesta 12,08 puntos**; además **el caso que lo motivó —`d4` a 280 ppp— es un punto que la regla relativa nunca produce** (`clamp(200,100,280)=200`). **Se escribió para arreglar un problema que la regla anterior no podía causar.** Tampoco vale una anchura fija en píxeles: **la regla es POR MOTOR**, con óptimos entre ×0,50 y ×1,80 | **`ppp-y-normalizacion.md` §2** |
| **«`P9` separa el texto recuperado de la alucinación de OCR»** | **REFUTADA al validarla.** **8,3 % de sensibilidad** sobre 32 capas OCR reales y **36 % de falsos positivos** sobre 14 capas legítimas. Falla porque supone que alucinar produce **ruido corto**, y Ghostscript alucina **palabras largas y plausibles** (hasta 7 130 caracteres). **Sustituto medido, 16/16: el acuerdo entre dos pasadas de OCR con idiomas distintos** | **`contrato-quinto-punto.md` §6** |
| **«Verificar en proceso siempre gana»** | **REFUTADA PARA PÍXELES.** Cierta para cabeceras (**145×** a favor) y **falsa en cuanto hay que recorrer píxeles**: `magick` mide la misma tinta en **138 ms** donde el lector en proceso tarda **2 834** (×20,5 a 1,8 Mpx). **El cruce está en ~0,1 Mpx. Son dos regímenes** | ídem §4.3 |
| **«El lock de GPU protege la medición»** | **REFUTADA.** Es un lock **de proyecto**, no de máquina: otra sesión de Claude en `D:\Work\research\ASR` ocupó **11 754 de 12 288 MiB** y dejó una tanda **12 minutos sin procesar una sola imagen** | **`ppp-y-normalizacion.md` §1.3** |
| **«`resvg` es un caso aislado»** | **REFUTADA: es una familia de al menos cinco miembros** en cinco modalidades. **I9 atrapa uno, el contrato otro, y uno sigue sin cubrir** (canal de audio silenciado hacia destino con pérdida) | **`contrato-quinto-punto.md` §5** |
| «Corregir la normalización mejora el motor» | **ACOTADA.** **El desajuste es universal —los ocho `inference.yml` declaran ImageNet— y el daño no.** Aplicarla a ciegas empeora **12 de 42 celdas**, con **+42,50 puntos** en `PP-OCRv4 mobile` sobre un documento **limpio**. Solo `PP-OCRv6 small` sale con 0 regresiones | **`ppp-y-normalizacion.md` §3.4, §3.5** |
| «El 50,5 % de aristas nominales es el sector» | **ACOTADA: el 18,8 % era INVOCACIÓN.** Con los mismos motores y build la tasa baja a **41,0 %**, y **3 226 aristas (10,2 %) son ganancia automática**. **Pero el 81,2 % sigue siendo irrecuperable**, y **58,5 % de las nominales son declaraciones sin sentido, no órdenes mal escritas** | **`invocacion-aristas.md` §0, §5** |
| «Los cuatro puntos del contrato atrapan los fallos del sector» | **ACOTADA, no refutada.** El **octavo** fallo del catálogo —`resvg` devolviendo un PNG perfecto **sin una sola letra**— **pasa los cuatro puntos**. El contrato juzga la declaración; el contenido que desaparece necesita **fidelidad** | `aristas-nominales.md` §8.2 |
| «`epub→pdf` es el mejor ejemplo de arista nominal del proyecto» | **REFUTADA COMO UNIVERSAL.** Es nominal **de un motor**: falla con LibreOffice (rc=1 también en Linux) y **funciona con Calibre** (26 817 B, centinela y tabla intactos) | `aristas-nominales.md` §8.1 |
| «El testigo de ruido del proyecto detecta las tandas sucias» | **REFUTADA.** Es **ciego a la contención multinúcleo**: etiquetó `limpia` una tanda que salió **×6,8** sobre el mismo control. Hacen falta **dos** testigos | `verificador-ghostscript.md` §4 |

### 2.3 Lo nuevo que cambia decisiones de diseño

1. **Regla de ppp: NO EXISTE UNA GLOBAL — hay una POR MOTOR, y vive en el ADAPTADOR.** ~~`clamp(ppp_nativos, 100, ppp_nativos × 1,4)`~~ → ~~`clamp(ppp_nativos, 100, 200)`~~ → **`ppp_ocr = min(max(nativos, 100), nativos × 1,25) × k(motor)`**, con `k` medido: **1,25 PaddleOCR · 1,00 RapidOCR+R6, Docling+R6 y EasyOCR · 1,50 Tesseract** (n=1). **Los ppp no son la unidad** —24 celdas: el mismo mapa de bits en tres páginas da 19,13 / 19,63 / 36,24 % a los mismos ppp y coincide **a la centésima** a los mismos píxeles— **y tampoco lo son un factor fijo ni una anchura fija.** Siete configuraciones sobre el mismo documento dan **óptimos entre ×0,50 y ×1,80**, y a ×1,4 sobre `d3` el mismo fichero es **seguro para PaddleOCR (3,80 %) y catastrófico para RapidOCR+R6 (46,84 %)**. **Techo de coste = el tope interno del motor** (RapidOCR recorta a 2 000 px: por encima de 233 ppp recibe el array idéntico). **Y hay que poner ALGÚN límite por VRAM:** a 400 ppp con una página, PaddleOCR llegó a **11 942** y EasyOCR a **12 037 de 12 288 MiB, sin dar error**. `OcrOptions.scale` **hay que fijarlo siempre**, pero **fijarlo a los ppp NATIVOS era la parte equivocada**: su defecto de 3,0 es indiferente en 4 de 5 escaneados y **mejor en `d3` (−17,72 puntos)**. **PENDIENTE: el valor de cada `k` es una estimación de UN documento.**
2. **El presupuesto de VRAM del sidecar se fija por motor *y por resolución*.** EasyOCR: **5.026 MiB** con imagen extraída, **11.877 MiB** a 300 ppp. El «+2.079 MiB» de la fase 2 subestimaba el peor caso **4×**.
3. **Extraer la imagen sin rasterizar y rasterizar a ppp nativos dan el mismo CER en las 16 celdas.** Extraer no compra precisión: se elige porque es más barato (221 ms vs 465 ms) y porque **no depende de que la cabecera diga la verdad**.
4. **Las anotaciones MCP `readOnlyHint`/`destructiveHint` no llegan al modelo** en Claude Code 2.1.238: solo cruzan `description` e `inputSchema`. La advertencia va en la descripción; **la defensa, en el núcleo**.
5. **Claude Code negocia `2025-11-25`, no `2026-07-28`.** La maquinaria de `NoBackChannelError`/`InputRequiredResult` no se ejercita hoy.
6. **El catálogo se paga en cada turno, ×2,0–2,6.** El presupuesto real de las cuatro herramientas no es 1.200 tokens: son **2.400–3.100 por petición**.
7. **R8 necesita una excepción explícita para `inspect`:** ahí el staging cuesta **1,32×** la operación. La salida correcta es leer metadatos en proceso, que ya pedía `coste-verificacion.md`.
8. **El riesgo nuevo va en dirección contraria a la intuición:** un catálogo **demasiado escueto** produce **fallos silenciosos** — el modelo llama a la herramienta más parecida y **declara éxito con un dato falso** (15–17 % de las peticiones con 8 herramientas). Eso convierte la **cobertura declarada de `convert` en requisito de seguridad**, no de comodidad.

### 2.4 El hallazgo incómodo que motivó a G1 — **RESUELTO el 21/08**

> ~~**El corpus de OCR ya no mide dificultad: mide selección de motor.** Tres documentos que todos resuelven al 0,0 % y uno que es un interruptor (2,5 % o 75,9 %, casi sin estados intermedios).~~
>
> ~~**Y ninguna medición de OCR de todo el proyecto lleva tildes ni castellano real.**~~

**Resuelto por `bench/corpus-d4.md`:**

- **`escaneado_d4` existe y cumple los cuatro criterios y el de éxito declarado antes de medir:** 19,30 / 36,91 / 41,78 / 61,41 % — **tres motores en la banda 15–60 % y 17,6 puntos entre el primero y el segundo.**
- **Y parte del «interruptor» de d3 era un artefacto de escala:** con **79 caracteres de referencia cada carácter vale 1,27 puntos de CER**, así que **no puede haber gradiente aunque el documento lo tenga**. `d4` usa **610** y cuantiza a 0,16.
- **La ceguera a las tildes está medida:** **155 caracteres de error ocultos en 28 celdas** (máximo 23 en una), y **6,3 puntos** en `eng` sobre castellano acentuado. **`bench/scripts/ocr_eval.py` sigue intacto y sigue siendo ciego** —los dos informes lo copiaron en vez de modificarlo—, así que **queda abierto decidir si la métrica acentuada pasa a ser la canónica del proyecto (A7).**
- **Las 296 celdas de `ocr-ppp-nativos.md` siguen siendo válidas para lo que miden** (su referencia no tiene una sola tilde: `cer_ascii == cer_acentos` por construcción); **lo que no se puede es extrapolarlas a castellano.**

---

## 3. Inventario de pendientes

Agrupado por **el recurso que lo limita**, que es lo que decide el reparto. Cada uno lleva identificador para citarlo en los prompts.

> ### Cómo se cuenta esto (23/08, L1)
>
> **Una fila = un identificador = exactamente un emoji de estado, y va en la última columna.** Verificado a máquina: **107 filas, 107 emojis** *(29/08: 106 → 107 con `C39`)*.
>
> | Emoji | Significa | Cuántos hoy |
> |---|---|---|
> | 🟢 | **CERRADO** con informe que lo prueba | **78** |
> | 🟡 | **EN CURSO o PARCIAL** (una mitad cerrada, o hay un agente dentro) | **11** |
> | 🔴 | **ABIERTO** | **17** |
> | ⚫ | **histórico**: la fila se conserva porque documenta una refutación, pero **no cuenta** | **6** |
>
> *(114 filas desde el 02/09: `N29` —el hallazgo de `filex.gpu.Lock._vivo()` al clasificar C42— y `C44` —el runner autoalojado con aprobación manual, decidido el 02/09— se añadieron como pendientes nuevos del carril GPU, y `N30` lo abrió la verificación de la ronda 5.)*
>
> La orden que lo comprueba. Hay que acotar **dos** veces: a la §3, porque la §4 usa ✅ para el estado de los *agentes*; y **a las filas cuya primera celda es un identificador**, porque si no la propia leyenda se cuenta a sí misma (comprobado: sin el segundo filtro salen 47/8/35/7 en vez de 44/6/32/5):
>
> ```sh
> awk '/^## 3\. Inventario/{f=1} /^## 4\. El reparto/{f=0} f' ESTADO-Y-REPARTO.md \
>   | grep -E '^\| (~~)?\*\*[ABCN][0-9]+'                                          \
>   | grep -o '🔴\|🟡\|🟢\|⚫' | sort | uniq -c
> ```
>
> Salida esperada hoy: `6 ⚫ · 12 🔴 · 11 🟡 · 88 🟢` sobre **117** filas *(verificado a máquina el 02/09, tras la ronda 4 del carril CPU/Docker — ver `bench/ci-y-contrato.md` — y desde hoy lo verifica también `ci/integridad.py` en cada PR, que es lo que impide que esta línea vuelva a quedarse tres días diciendo otra cosa)*. La ronda 4 cerró **C27** (🔴→🟢, decisión: G6 se queda en `aviso`) y avanzó **C42** sin cerrarla del todo (🔴→🟡: 9 de 10 módulos de la CI clasificados y arreglados con código, 1 sin reproducir, la promoción final de `ci/linux-apto.json` pendiente de correr en el runner real). El resto del movimiento desde la ronda 3 (`6 · 19 · 10 · 76` → `6 · 16 · 11 · 78`) es del carril GPU en paralelo (`gpu/k-oem-acantilados`). *(23/08: `5 ⚫ · 44 🔴 · 6 🟡 · 32 🟢` sobre 87; 27/08: `6 · 40 · 5 · 36`; 28/08 tras la ronda 1: `6 · 42 · 5 · 39`; 29/08 con C39: `6 · 29 · 3 · 69` sobre 107; 01/09 antes del saneo: `6 · 24 · 8 · 73` sobre 111; 01/09 tras el saneo de la ronda 3: `6 · 19 · 10 · 76`.)* **El saneo de la ronda 3 no movió filas por trabajo nuevo: movió DOS filas porque su propio color contradecía su propia evidencia** — `C28` estaba 🟢 y su informe fuente (`firmas-cierre.md` §8) declara sin resolver justo lo que la fila daba por cerrado; `C32` pedía arbitrar una contradicción que `C31`/`C37` ya habían arbitrado sin que nadie cerrara esta fila. **Esta línea estuvo TRES DÍAS diciendo 95 filas mientras la leyenda de arriba decía 107: es la trampa 44 dentro del documento que gobierna el reparto — un recuento honesto con una nota falsa al lado.** **La ronda 1 cerró tres y abrió cinco; la ronda 2 cerró dos y medio cerró dos. Cerrar bien un pendiente casi siempre destapa los que tapaba — pero la proporción mejora cuando el encargo trae el mecanismo hecho: N10 se cerró rápido porque N1 ya había construido `filex/cerrojo.py`.**
>
> **Y el segundo barrido encontró algo que el primero no buscaba: cuatro de las cinco filas movidas ya estaban cerradas ANTES de este repaso, y una —C33— llevaba cuatro días marcada como *«lo más urgente de esta sección»* sobre un fallo de seguridad **cerrado en el commit `c2f6a59`**.** El barrido del 23/08 comprobó que **cada fila tuviera un emoji**; no comprobó que **el emoji fuera verdad**. Son dos revisiones distintas y hacen falta las dos: la primera se hace con `grep`, la segunda **solo contra el código y el `git log`**.
>
> **Antes de este barrido el conteo no significaba nada:** había emojis 🔴 dentro de texto tachado y en filas ya cerradas, y el estado de las filas antiguas se escribía con ✅ en unas y con 🟢 en otras. **Ahora `grep` da el número.**

### A · Deuda documental — bloquea a todos, **no se paraleliza**

| # | Pendiente | Estado |
|---|---|---|
| ~~**A1**~~ | Integrar los cuatro informes del 21/08 03:07 en los maestros | 🟢 **CERRADO** por D1 (`bench/consolidacion-21ago.md`) |
| ~~**A2**~~ | Las 12 correcciones de `mcp-cabos-sueltos.md` §6 en `analysis/00-mcp-patrones.md` | 🟢 **CERRADO** por D1 |
| ~~**A3**~~ | `RESULTADOS-MCP.md` §13 | 🟢 **CERRADO** por D1: 5 de 6 cerrados, §13 reescrita en dos partes |
| ~~**A4**~~ | `AGENTES-PRUEBAS-PENDIENTES.md` con marcas invalidadas | 🟢 **CERRADO** por D1: marcado como superado por este documento |
| ~~**A6**~~ | Integrar `verificador-ghostscript.md`, `aristas-nominales.md` y `corpus-d4.md` en los maestros | 🟢 **CERRADO** por D2 (`bench/consolidacion-2-21ago.md`) |
| ~~**A8**~~ | Integrar `ppp-y-normalizacion.md`, `invocacion-aristas.md` y `contrato-quinto-punto.md` en los maestros | 🟢 **CERRADO** por D3 (`bench/consolidacion-3-21ago.md`) |
| **A5** | ✅ **CERRADO el 22/08/2026: commit `dcd4057` ejecutado**, 1.799 ficheros, +271.130/−210, los 6 PDF de `d4` por Git LFS y los ~30 binarios regenerables de `salidas-aristas/` excluidos por `.gitignore` con su `MANIFIESTO.md`. Entran los doce informes. Se recuperó además `PRUEBAS-MCP-REFS.md`, que solo existía en las ramas `ccb/w1..w3`, ya borradas. ~~**SIGUE ABIERTO, y es lo más urgente del inventario** — no se ha ejecutado ni `git add` ni `git commit`. **Van SIETE agentes sin commit y `git status` tiene 44 entradas.** La lista vigente está en `bench/consolidacion-3-21ago.md` §6~~ | 🟢 **CERRADO** |
| **A7** | **Decidir si la métrica de OCR canónica del proyecto pasa a ser la acentuada.** Hoy `bench/scripts/ocr_eval.py` sigue intacto y sigue siendo ciego; hay **dos copias** con acentos (`ocr_eval_d4.py`, `ocr_eval_tildes.py`) y ninguna es la oficial. **Actualizado el 23/08: de hecho ya está decidido y nadie lo ha escrito.** Cuatro informes seguidos —`corpus-d5.md`, `psm-y-rasterizador.md`, `k-por-motor.md` §1.2 y `phys-multimotor.md`— **declaran que no abren `ocr_eval.py` porque es ciego** y copian `ocr_eval_d4.py` byte a byte con su `sha256`. ~~Lo que falta es **el acto formal**~~ — **HECHO el 28/08 por W** (`bench/metrica-ocr.md`): la canónica es la acentuada, la vía ciega vive tras `--ciego` y `evaluar()` devuelve la clave `metrica` en cada celda. **Cuesta 4 celdas de 628 y 0 inversiones de orden.** Y el censo desmiente el enunciado: no eran tres copias sino **13 ficheros, 5 `md5`, tres implementaciones**, con la «no oficial» usada por 14 arneses frente a 5 | 🟢 **CERRADO** |
| **A9** | **Registrar en este inventario el trabajo del 22 y 23/08.** **Quince informes de `bench/` no tenían una sola cita aquí**, y ocho son de esos dos días: los cuatro hitos (`hito3-mudanza`, `hito4-mcp`, `hito5-documental`, `hito7-superficies`), los tres sondeos (`sondeo-imagemagick`, `sondeo-ffmpeg`, `sondeo-documental`) y `consolidacion-4-22ago`. ~~**La §1 ya está corregida (23/08, L1)**~~ — **no lo estaba: seguía diciendo «un solo commit»; corregida de verdad el 27/08.** Los pendientes que abren esos ocho sí están repartidos en la §3.N. **CERRADO el 28/08: el índice de §1 cubre ya los 51 informes de `bench/`, comprobado a máquina.** Faltaban **17**, y solo nueve eran de las rondas: los otros ocho —`competidores`, `docker`, `results`, `gpu-fase1`, `gpu-fase2`, `referencia-nativa`, `mcp-ergonomia`, `mcp-refs-confinamiento`— llevaban sin citar **desde antes del primer barrido**, incluido el del **patrón oro**. El barrido del 23/08 dijo «faltan dieciséis» y tampoco los vio | 🟢 **CERRADO** |

### B · Requieren GPU — **estrictamente uno a la vez** (lock exclusivo)

| # | Pendiente | Estado / origen |
|---|---|---|
| ~~**B1**~~ | Construir `escaneado_d4` | 🟢 **CERRADO** por G1. **Cumple los cuatro criterios y el de éxito.** `corpus/pdf/escaneado_d4{,a,b,c,e,f}.pdf` + `MANIFIESTO-d4.md` |
| ~~**B2**~~ | Aislar la asimetría de PaddleOCR | 🟢 **CERRADO** por G1, y **no era ninguna de las tres candidatas**: era la normalización del detector de RapidOCR. **72,2 puntos por seis números** |
| **B3** | **marker** — instalado y sin medir. `torch 2.13.0` **sin paquetes `nvidia-*`**: es build **CPU**. **Confirmado el 23/08: sigue sin una sola medida.** `bench/salidas-marker/` solo contiene un `logs/` vacío y hereda el bloqueo de surya (`surya-ocr>=0.22.1,<0.23.0`). **DECIDIDO el 02/09: SE MIDE** (ronda 9) — y con una consecuencia que nadie había escrito: **al ser build CPU, B3 NO necesita el lock de la tarjeta**, así que el carril GPU se vacía en la ronda 8 y worker1 lo toma sólo porque ya no tiene GPU que hacer. Al cerrarlo, `.venv-marker` (1 205 MB) sale de la lista protegida de `CLAUDE.md` §1 | 🟡 **DECIDIDO, ronda 9** |
| **B4** | **surya** por `SURYA_INFERENCE_BACKEND=llamacpp` o `VLLM_GPU_MEMORY_UTILIZATION=0.5`. **Único material: `bench/gpu-fase1.md` §B.3 — «NO FUNCIONA en GPU en esta máquina».** VRAM: sin dato. **CERRADO POR DECISIÓN el 02/09: se descarta.** El motivo está medido y es el propio bloqueo —Surya 0.22.1 lanza un contenedor vLLM que reserva el 85 % de la VRAM y **se cuelga sin excepción** (trampa 15)—, y un «no se pudo medir» documentado **es** un resultado en este proyecto | 🟢 **CERRADO, descartado** |
| **B5** | **MinerU `[vlm]`** (no `[vllm]`). **Cero menciones en todo `bench/`**. **CERRADO POR DECISIÓN el 02/09: se descarta.** Diez días abierto sin una sola cifra y sin material de partida, frente a ocho filas del carril GPU que sí traen hallazgo dentro | 🟢 **CERRADO, descartado** |
| **B6** | **NVENC en lote sobre carpeta real** — el único pendiente del hueco 4, y el único caso donde decide algo. **Y ahora tiene un segundo motivo:** `bench/hito7-superficies.md` §5.4 mide que en `filex/` **no hay uso de GPU ni lock de GPU** —las apariciones de `nvenc`/`cuda` en el paquete son **tres comentarios**—, así que el hito 2 seguía sin empezar. **CERRADO el 28/08 por H2 — y la premisa de esta fila queda REFUTADA: el lote DILUYE.** ×4,10 sobre 8 clips frente a **×7,68 sobre una conversión larga suelta**; la ganancia crece con la **duración**, no con el número de ficheros, y FileX añade solo **27,2 ms (+3,6 %)** sobre el `ffmpeg` crudo. **El escenario donde la GPU decide es el fichero LARGO.** Es la trampa 76 | 🟢 **CERRADO** · `hito2-nvenc.md` |
| **B7** | Heurística de «degradación severa». **Ahora hay contra qué calibrarla (`d4`) y dos señales candidatas medidas**: cajas detectadas frente a área de texto, y el tiempo (d3 cuesta ×4,5 lo que d2 en Ghostscript) | 🟡 `corpus-d4.md` §11, `verificador-ghostscript.md` §5.4 |
| **B8** | R1 sobre PDF que **no** son «una imagen a página completa»; e interacción de **`magick -deskew 40%`** con el techo, ahora sobre la familia d4 (rotada de −4° a +4°). **Comprobado el 23/08: ningún informe posterior menciona `deskew`** | 🔴 ídem · **ABIERTO** |
| ~~**B9**~~ | Barrer la curva de ppp sobre `d4` | 🟢 **CERRADO** por P1, **y el techo absoluto queda REFUTADO igual que el relativo.** 17 puntos × 7 configuraciones + 24 celdas de control: **los ppp no son la unidad, ni el factor, ni la anchura en píxeles. La regla es POR MOTOR y baja al adaptador** |
| ~~**B10**~~ | Validar la corrección de normalización fuera del corpus d4 | 🟢 **CERRADO** por P1. **0 regresiones en 15 documentos sobre `PP-OCRv6 small`** (incluidas 4 rasterizaciones del patrón oro) — **y 12 de 42 celdas peores si se aplica a la familia**, con **+42,50 puntos** en `PP-OCRv4 mobile` sobre un documento limpio |
| **B11** | **Llevar la corrección a producción — y su contenido CAMBIA.** No es «añadir R6 a `bench/scripts/ocr_motor.py`»: **sobre el `PP-OCRv5 mobile` que usa hoy, R6 NO es recomendable** (4 de 15 celdas peores). Es **cambiar a `PP-OCRv6 small` Y añadir R6**. **Saldo medido, declarado entero: 7 mejor, 2 igual, 2 PEOR** (`d4a` +5,87 y `d4f` +1,01, por el cambio de checkpoint, no por R6). El parche exacto está en `ppp-y-normalizacion.md` §4, **propuesto y NO aplicado**. **Redefinido OTRA VEZ el 22/08:** `k-por-motor.md` §4.2 corrige dos `k` (Docling+R6 ×1,00→**×0,875**; Tesseract ×1,50→**×0,875/×0,75**) y `psm-y-rasterizador.md` §7 añade que **un `k` publicado sin su `--psm` no es un número**. Tres informes verifican que `ocr_motor.py` **sigue intacto**. **CERRADO el 28/08 por G5**: `PP-OCRv6 small` + R6 por defecto en `bench/scripts/ocr_motor.py`, con `RO_LEGADO=1` para la vía anterior. **Saldo sobre 20 documentos: 14 mejor / 3 igual / 3 peor** —reproduce casi al centésimo las dos regresiones publicadas **y encuentra una tercera mayor que ambas** (`realista_d5e` +7,40), de una familia que el corpus de 11 no tenía—. Y sale gratis: **−24 % de tiempo, +1 MiB**. Es la trampa 69 | 🟢 **CERRADO** · `ocr-produccion-sidecar.md` |
| **B13** | ✅ **CERRADO el 22/08** (`bench/k-por-motor.md`, 396 celdas deterministas: 9 configuraciones × 4 documentos × 11 factores). **El `k` óptimo es del PAR (motor, documento)** — motor 23,2 % de la varianza de `log2(k*)`, documento 0,1 %, **interacción 76,7 %**, que es justo el término que `nativos × k(motor)` supone nulo. **No tumba la regla: le cambia el fundamento.** Lo refutado es «el `k` de `d4` es el `k` del motor» —su argmin gana en **3 de 9** configuraciones—, así que `k` se fija por **mínimo arrepentimiento** sobre varios documentos (0,34–2,81 puntos en 9 de 9). **Corregidos: Docling+RapidOCR+R6 ×1,00 → ×0,875 y Tesseract ×1,50 → ×0,875/×0,75.** Abre B17-B19 | 🟢 **CERRADO** |
| **B17** | ✅ **CERRADO el 22/08** (`bench/psm-y-rasterizador.md`, 547 celdas deterministas). **El `--psm` es del PAR y NO es separable del `k`**: interacción `--psm`×documento 29–40 %, con `k` 13,7–41,2 %; el ganador cambia a lo largo de `k` en 4 de 4 documentos y al revés en 4 de 4. **Pero lo que la interacción rompe NO es el procedimiento** —elegir `--psm` a ×1,00 y luego el `k` llega a la misma pareja que barrer la rejilla— **sino la TRANSFERIBILIDAD**: el ×0,75 de `psm 11` no vale para `psm 3` ni `psm 6`. **Un `k` publicado sin su `--psm` no es un número.** Cierra además el pendiente 7 de `invocacion-aristas.md` en dos documentos | 🟢 **CERRADO** |
| ~~**B17**~~ | ~~**El `--psm` de Tesseract pesa MÁS que el `k`: 42,78 puntos**~~ frente a los 19,30 del barrido entero de `k`. Y cierra el pendiente 7 de `invocacion-aristas.md`: sobre el mismo `d3`, **`psm 3/4` devuelven 0 bytes y `psm 6/11` devuelven 113,92 % y 188,61 %** — **silencio y alucinación son el mismo motor con distinto modo de segmentación**. Hay que barrerlo como se barrió `k`, y **elegirlo en el adaptador** | ⚫ **histórico** (lo cerró la fila B17 de arriba) |
| **B18** | ✅ **REFUTADO Y CERRADO el 22/08 por DOS agentes por rutas independientes** (`bench/psm-y-rasterizador.md` §2 y `bench/corpus-d5.md` §4). **El rasterizador vale CERO: ImageMagick NO TIENE rasterizador de PDF, delega en Ghostscript** — `magick -list delegate` lo dice y los dos rásteres tienen el mismo `md5` de píxeles crudos. La variable es el **`pHYs`**, que `magick` escribe con `unidad=0`: Tesseract se inventa **403 ppp** sobre un ráster de 200 y cambia su análisis de maquetación. **Prueba simétrica, 126 de 126:** `magick -density 200` ≡ `gs`, y `gs -r70` ≡ `magick`. Es **una regla de una línea, gratis, en el adaptador**. Dos matices: **`psm 6` nunca cambia con la resolución** (0 de 22) y **declarar un valor FALSO empeora 11 de 93** | 🟢 **CERRADO** |
| ~~**B18**~~ | ~~la atribución vieja~~ (`bench/corpus-d5.md` §4). **No son 33 puntos del rasterizador: son del trozo `pHYs` del PNG.** Los dos rasters tienen el **mismo `sha256` de píxeles crudos**, y escribir `-units PixelsPerInch -density N` **sin tocar un píxel** reproduce la cifra de Ghostscript en **16 de 16 celdas a la centésima**. Mecanismo sondeado en ejecución: sin unidades válidas Tesseract imprime `Estimating resolution as 403` sobre un raster de 200 ppp y **cambia su análisis de maquetación** (36 → 51 diacríticos). Convierte un problema de comparabilidad en **una regla de una línea, gratis, en el adaptador**. **Pero NO es «declarar siempre gana»:** en `realista_d5e` con `psm 3` declarar **empeora 15,44 puntos** — es del par (documento, configuración). **Pendiente de contraste con G2**, que sigue midiendo B18 | ⚫ **histórico** (el contraste con G2 ya se hizo: 126 de 126 celdas) |
| ~~**B18**~~ | ~~**El RASTERIZADOR es una variable oculta de 33 puntos.** Misma geometría (1294×1716) y misma profundidad: Tesseract da **84,56 %** desde ImageMagick y **51,34 %** desde Ghostscript — y ese 51,34 % **reproduce el 51,15 % de P2 con 0,19 de diferencia**. Sobre `d3` y `d4c` los dos coinciden: **también es del par**. **Ningún `k` se transfiere entre informes sin declarar con qué se rasterizó** | ⚫ **histórico** (la atribución al rasterizador está REFUTADA) |
| **B19** | ✅ **CERRADO el 22/08** (`bench/corpus-d5.md`): **12 PDF nuevos, 266 celdas de Tesseract, CERO celdas a 0,00 %** (mínimo 0,17 %), frente a las 88 de 99 a cero de `patologico_escaneado`. Referencia importada de `d4` (610 caracteres, 35 acentuados), así que son comparables celda a celda con las 396 de `k-por-motor.md`. **Y el hallazgo de método: la iluminación no uniforme es la patología más potente (74,67 puntos) y es INSERVIBLE para construir corpus — es un interruptor y no es monótona** (5,03 → 72,82 en cuatro puntos de gris, luego 79,4 / 82,2 / 78,4 / 54,9). El polvo sí es gradual y es lo que sostiene la escalera | 🟢 **CERRADO** |
| ~~**B19**~~ | ~~**`patologico_escaneado` NO discrimina**: **0,00 % en las 11 celdas de 8 de las 9 configuraciones, 88 celdas a cero**. Era uno de los tres documentos que B13 pedía barrer y **no sirve para caracterizar `k`**. Hay que sustituirlo en el corpus de barrido | ⚫ **histórico** (sustituido por el corpus `d5`) |
| **B14** | ✅ **REFUTADO SU ENUNCIADO el 22/08.** **A 100 ppp nativos, `--psm 6` lee `escaneado_d2` con 0,00 % de CER: los 32,10 puntos no eran de los ppp, eran del `--psm`.** Y la curva **no es monótona**: el punto nativo es un **máximo local** (1,27 % → **30,38 %** → 0,00 % en un 12,5 % de resolución), idéntico a la centésima en tres tandas, así que tampoco es del metadato | 🟢 **CERRADO** |
| ~~**B14**~~ | ~~**Barrer la curva de ppp de Tesseract.**~~ `escaneado_d2` refuta la regla con n=1 (**0,00 % a 150 ppp frente a 32,10 % a sus 100 nativos**) y `d4` va en la dirección contraria. **Ni siquiera dentro de un motor hay un factor único** | ⚫ **histórico** (su enunciado está refutado: era el `--psm`) |
| **B15** | ✅ **CERRADO el 22/08** (`bench/corpus-d5.md` §0 puntos 2-3, §2). `escaneado_d5b` (**60 ppp**) y `d5a` (**90 ppp**) existen, y en la primera celda destaparon **un fallo ARITMÉTICO de un año**: `min(max(n,100), n×1,25)` aplica el suelo **antes** del techo, así que **para `n ≤ 80` el techo cae por debajo de 100 y anula el suelo** (con 60 ppp la regla ordena **75**). Cuesta **16,78 puntos**. Y donde el suelo sí decide (80 < n < 100) **también empeora**: 1,17 % a nativos frente a 2,68 % a 100. La forma correcta es **`max(min(n × 1,25, techo), 100)`** | 🟢 **CERRADO** |
| **B16** | **Refinar `escaneado_d3` entre ×1,25 y ×1,4**, que es donde está el acantilado de RapidOCR+R6 (2,53 → 46,84) y solo hay dos puntos. **Es el mismo defecto que B9 vino a corregir en `d4`, en otro documento.** **AMPLIADO el 22/08** (`k-por-motor.md` §9): hay **un segundo acantilado sin puntos intermedios**, el de PaddleOCR entre **×1,40 y ×1,60** (3,80 → 75,95). **CERRADO el 01/09, REFUTANDO su propio enunciado** (`bench/k-oem-acantilados.md`): con 13 puntos **no hay acantilado, hay un PEINE** — RapidOCR+R6 da 2,53/**73,42**/25,32/6,33/**0,00**/**75,95**/46,84 % entre ×1,25 y ×1,40, deterministas. **El 75,95 % que se repite EXACTO en `k` no contiguos (×1,38/×1,52/×1,60, en los dos motores) es colapso de modo, verificado leyendo el texto**: las cinco celdas devuelven, letra por letra, sólo `"DOCUMENTO ESCANEADO"` (la primera línea) y pierden el cuerpo entero (60 de 79 caracteres) — no es mala lectura, es que el detector deja de proponer caja para el cuerpo. Y a un paso de rejilla, ×1,35 lee el cuerpo **sin un solo error** | 🟢 **CERRADO** · `k-oem-acantilados.md` |
| **B12** | ✅ **CERRADO en lo esencial el 22/08** (`bench/corpus-d5.md` §0 punto 8, §5), **con residuo declarado**. Las tres degradaciones están **medidas en el píxel y con control de cero**: sombra de encuadernación (luminancia izq/dcha 0,87-0,78 frente al 0,99 de `d4`), curvatura (residuo 1,9-7,3 px frente a 0,4 del control `onda=0`) y transparencia del papel (1,00 → 0,74). **El residuo va a B20** | 🟢 **CERRADO** |
| **B20** | **El residuo de B12: la curvatura NO es la perilla dominante y su ablación sale al revés** con `psm 3`, y la sonda **satura por encima de ~3,5° de giro y con polvo ≥0,35** | 🔴 **NUEVO** · `corpus-d5.md` §8 |
| **B21** | **MITAD CERRADA el 31/08** (`bench/suelo-ppp.md`, 336 celdas). Las **siete configuraciones no-Tesseract** medidas, y la respuesta **invierte el signo según el motor**: RapidOCR **11 peor / 0 mejor**; EasyOCR y docling+R6 **7 mejor / 0 peor**; PaddleOCR y docling por defecto, indiferentes. Sobre `escaneado_d5c` el suelo **cuesta +17,8 puntos a RapidOCR v6+R6 y gana −17,9 a docling+R6**. **El saldo global —14/9/5— es un empate ENGAÑOSO: promediarlo destruye la interacción motor×documento.** **Sigue abierto: Tesseract `psm 3` y `psm 11`**, que no entran en estas celdas. **CERRADA el 01/09** (`bench/psm-suelo-ppp.md`, 96 celdas): **Tesseract INVIERTE el signo de RapidOCR y se empareja con EasyOCR — 3 mejor / 1 peor en las dos configuraciones**, y en los dos documentos donde el suelo decide de verdad gana mucho: `escaneado_d5` (72 nativos) de **10,1 % a 2,2 %** y `escaneado_d5b` (60) de **28,7 % a 8,7 %** con `psm 3`. Con las **nueve** configuraciones medidas el saldo global es **16 peor / 15 mejor / 5 igual** — sigue siendo un empate y sigue siendo engañoso por el mismo motivo. **El único documento donde el suelo empeora a Tesseract es `d5a`**, el de nativos más altos (90) y menor CER de partida: ya tenía píxeles de sobra y subir sólo interpola. **No hay corrección de la regla que generalice: la interacción ES el hallazgo** | 🟢 **CERRADA** · `psm-suelo-ppp.md` |
| **B22** | **MITAD CERRADA el 31/08** (ídem). **No hay óptimo global cerca de 125: la curva NO ES SUAVE.** `d5c` en RapidOCR v6+R6 da 0,7 % a 80 ppp, **18,5 a 100**, 9,7 a 120, 0,8 a 125, 0,3 a 130 y 5,0 a 135, **deterministas** y con **pérdida de texto** (523 B frente a 641), no mala lectura. **Refutado el mecanismo del tamaño efectivo por su propio autor**: `d5a` y `d5c` a 100 ppp aterrizan los dos en `736x1024` y dan **1,0 % contra 18,5 %** — el pico es del par (documento, ppp). Y **`d5b` no es curva con picos: es régimen malo persistente** (3,5–24,3 %). **Sigue abierto: los dos `--psm` de Tesseract, y sondear las CAJAS detectadas**, que es la siguiente sonda útil. **MEDIDA la mitad de Tesseract el 01/09** (ídem): la curva **tampoco es suave** aquí —hay picos de un solo paso de 5 ppp— **pero la amplitud es otra magnitud**: máximo **4,2 puntos** en las 96 celdas frente a los **~18** que RapidOCR v6+R6 hace sobre `d5c` él solo. Y al revés que las siete configuraciones anteriores, **en Tesseract el óptimo SÍ agrupa en 125–150 ppp en los cuatro documentos y en las dos configuraciones**, con el entorno del óptimo plano — confirmación **parcial y sólo de Tesseract** del ~125 que este pendiente dejaba abierto, y la ganancia de ir de 100 al óptimo es **modesta** (máx. 2,4 puntos) frente a los hasta 20 del salto nativo→100. Y un pico documentado que **no aparece con el otro `--psm`**: `d5` da 1,7 % a 130, **3,4 a 135** y 2,0 a 140 con `psm 3`, y 2,3 / 1,8 / 2,0 con `psm 11` (**corregido el 01/09**: se citó mal como 1,8/1,8/2,0 al integrar; reverificado contra el JSON, la conclusión no cambia) — **el pico es del TRIPLE (documento, ppp, `--psm`)**, no del par. **CERRADA el 01/09** (`bench/cajas-rapidocr.md`, 25 celdas GPU deterministas): sondeadas las cajas de `escaneado_d5c` y `d5a` con RapidOCR v6+R6, y **la hipótesis de partida —«el pico apunta al detector»— NO se sostiene: se sostiene la contraria**. En las 12 celdas de `d5c` (0,7/**18,5**/…/**9,7**/…/**5,0**/…) las **12 cajas y ~20 % de área de página se mantienen estables**; lo que colapsa es el RECONOCEDOR sobre **una línea del bloque `pequeña` (7 pt)**, y el déficit de texto reproduce, byte a byte, el «523 B frente a 641» ya citado. `d5a` (nativo 90) no sufre este mecanismo en ningún punto de 90–150 ppp; sólo pierde una caja (11 de 12) **por debajo** de su nativo, a 80 ppp — un mecanismo distinto, y también en el bloque `pequeña`. **PENDIENTE, y fuera del alcance de este cierre:** por qué el reconocedor falla justo en 100/120/135 y no en los nueve puntos vecinos, con la misma caja — exigiría inspeccionar el recorte que llega al reconocedor, no sólo la caja | 🟢 **CERRADA** · `cajas-rapidocr.md` |
| **B23** | **El `k` sigue ajustado sobre CUATRO documentos y uno no discrimina: en la práctica son TRES**, que además **comparten geometría de página (465,84 pt)** y tres salen del **mismo generador**. **A MEDIAS el 01/09** (`bench/k-oem-acantilados.md`): `k` por mínimo arrepentimiento sobre la familia `d5` (4 geometrías distintas, discrimina), pero en rejilla REDUCIDA (**5 de 9 configuraciones, 7 de 11 factores**, declarado así, no disimulado). RapidOCR v6+R6 y PaddleOCR (inmunes al pHYs) **confirman** el `k` ya publicado (×1,00 y ×1,00–1,25) sobre un corpus independiente. **El `k` de Tesseract con pHYs declarado (×1,40/×1,60) NO es comparable con el publicado (×0,875/×0,75, medido sin declarar)** — mezcla dos variables, corpus y pHYs, sin celda que las separe. **PENDIENTE: las 4 configuraciones que faltan (Docling, RapidOCR defecto), la rejilla por encima de ×1,60 (EasyOCR y `psm 11` mejoran hasta el borde) y separar pHYs de corpus en Tesseract** | 🟡 **PARCIAL** · `k-oem-acantilados.md` |
| **B24** | **El `--oem` de Tesseract no se ha tocado** — es el otro parámetro estructural, y `--psm` ya demostró pesar más que el `k`. Con él: **los otros ocho `--psm` sin barrer**, y **la tabla de `k` de Tesseract habría que rehacerla con Ghostscript**, que es la vía que FileX usaría. **CERRADO el 01/09** (ídem): `--oem 0/2` (legacy) **fallan siempre** — el `spa.traineddata` de PDFgear no trae datos legacy —, y `--oem 1/3` dan CER **idéntico**: no hay parámetro que barrer, sólo hay un motor posible. Los 8 `--psm` restantes colapsan a **3 clases** (auto-layout ≡ `psm 3`; disperso ≡ `psm 11`; bloque único, peor; y 5 de ellos son silencio/cuenta atómica sobre una página completa — trampa 25 confirmada). **Ghostscript y ImageMagick, con pHYs declarado en los dos, dan píxeles y texto IDÉNTICOS en 10 de 10 celdas** (control `d4` + familia `d5`): la tabla de `k` **no** necesita rehacerse con Ghostscript, ya vale para el contenedor | 🟢 **CERRADO** · `k-oem-acantilados.md` |
| **B25** | **CERRADO el 23/08 por G4** (`bench/phys-multimotor.md`, 300 celdas GPU + 150 de control): el `pHYs` es una trampa de **UN SOLO MOTOR**. PaddleOCR, RapidOCR y EasyOCR devuelven **un solo `md5` de texto en las 18 filas motor×documento** — recorrido de CER **0,00** — y no es que no les afecte: **no lo consultan**. Los mismos ficheros mueven a Tesseract hasta **47,15 puntos**. Ya es la trampa 29 de `CLAUDE.md`. ~~**NO LO CIERRES: es de G4**~~ | 🟢 **CERRADO** · `phys-multimotor.md` |
| **B26** | **El reciclado de proceso del sidecar de OCR no está medido en coste.** Es la consecuencia arquitectónica de que el asignador **no devuelva la VRAM** (9 y 24 lecturas idénticas al MiB). **CERRADO el 28/08 por G5 — y la variable NO era la que decía el pendiente.** No crece con las páginas ni con los Mpx acumulados (20 páginas de 1,25 Mpx mueven 39-42 MiB; **una** de 4,35 mueve 3 209): crece con el **documento MAYOR y el CAMINO**. **REFUTA además el «orden ascendente» de `k-por-motor.md` §6.3: es la PEOR opción, ×2,25 y +5 350 MiB**, replicado en dos tandas. Reciclar cuesta **4,08 / 6,74 / 7,05 s** y el criterio es `ordenada + pendiente × Mpx` contra la VRAM libre. Trampa 67 | 🟢 **CERRADO** |

### C · Sin GPU — paralelizables entre sí

| # | Pendiente | Estado / origen |
|---|---|---|
| ~~**C1**~~ | `min(alfa)` de TIFF comprimido, GIF y Adam7; reglas V2 y V5 | 🟢 **CERRADO** por V1. **36 de 36 contra `magick`, 0 falsos positivos.** Coste real ×2,9 y ×3,6 sobre lo estimado; **V2 no era barata: +60,6 % de la suite** |
| ~~**C2**~~ | OCR con el Tesseract embebido de Ghostscript | 🟢 **CERRADO** por V1. **0,0 % de CER en patológico, d1 y d2 con `spa`; VRAM 0; carga en frío 122 ms.** Fracasa en d3 **alucinando** |
| ~~**C3**~~ | Cuántas de las 138 501 aristas son nominales | 🟢 **CERRADO** por E1. **50,5 %** [48,2–53,0], cota inferior — **pero 3,0 % en el estrato PDF** |
| ~~**C8**~~ | Los 7 casos `no_evaluable` de `referencia.json` | 🟢 **CERRADO** (5 de 7 entonces; los otros dos los cerró C13) por E1 dentro del contenedor. **Siguen abiertos `qpdf` y `tesseract`** → C13 |
| **C4** | ✅ **CERRADO el 22/08 por M1** (`bench/mcp-cabos-2.md`). Las 20 herramientas: **26/26 cuelgan por ejecución, cero excepciones** (las 3 que respondieron eran fallos tempranos por entradas mías). `roots.listChanged: true` **declarado** — emisión real, PENDIENTE acotado. Recursos y prompts: **el cliente los enumera, el modelo NO los ve**. Y la de más valor: **las herramientas llegan DIFERIDAS** (pesado = ligero = 26.941 tok), lo que **re-acota el modelo de coste de `RESULTADOS-MCP.md` §4** | 🟢 **CERRADO** |
| **C5** | **MITAD CERRADA.** El cruce `inspect` vs staging: **`cruce_MB ≈ ffprobe_ms × copia_MBps / 1000`**, entre **~70 MB** (disco contendido) y **~95 MB** (holgado) — y de ahí sale que **`inspect` queda exento de R8 y de R18**. **La carrera de symlinks en Linux sigue BLOQUEADA**: el arnés (`c5a_symlink_wsl.py`) está listo, el vector está identificado y medido (swap dir-real/symlink, primitivo disponible en POSIX y bloqueado en Windows), y la **VM de WSL2 cae con `0x8007274c`** bajo contención. *«No es un resultado negativo: es una medición no hecha»* | 🟡 `mcp-cabos-2.md` §5.1 |
| **C6** | Replicar la saturación en **dominio documental** (docling-mcp, 19 herramientas), con API y `temperature` fija | 🔴 `saturacion-herramientas.md` §8. **Requiere clave de API, que no existe en esta máquina** |
| **C7** | Si esas conversiones **se piden de verdad**. El catálogo de SnapOtter es un proxy de demanda | 🔴 `HUECOS.md` §2 |
| ~~**C9**~~ | Implementar y medir el quinto punto del contrato y R18 | 🟢 **CERRADO** por P3. **+0,047 ms = +11,0 % del contrato CON R18; ×8,6 el contrato entero SIN él sobre un directorio de 1 000 ficheros. 0 falsos positivos** sobre las 39 órdenes del patrón oro y **0 avisos** en tres salidas multifichero legítimas. **Y el hallazgo que no se esperaba: sin censo, 49 de las 53 salidas bajan a `ok_parcial`, porque el punto 5 NO es verificable a posteriori** |
| ~~**C10**~~ | La regla de fidelidad que atraparía a `resvg` | 🟢 **CERRADO** por P3. **I9 discrimina 6/6** (0,00 % de tinta frente a 20,01 % y 23,61 %). **Su coste real es 32–59 ms a 400×200 y 2 454 ms a 1920×960: la estimación de 26 ms se quedaba corta ×94.** **Y `resvg` resultó ser una familia de cinco miembros** → C19 |
| ~~**C11**~~ | Validar `P9` y añadir `ocr: true` al `pedido` | 🟢 **CERRADO** por P3, **y `P9` queda REFUTADA**: 8,3 % de sensibilidad sobre 32 capas OCR reales, 36 % de falsos positivos sobre 14 legítimas. Se deja en el código **marcada como no fiable**. **`ocr: true` implementado**: P5 invierte la exigencia y P9 sube de `aviso` a `fallo` → C20 |
| ~~**C12**~~ | Interruptor propio para V2 | 🟢 **CERRADO** por P3 (`--sin-v2`). **Ahorra el 46,3 % de la suite (70 693 → 37 947 ms) sin cambiar ni un aviso**, y sube los `ok_parcial` de 8 a 13 — *apagar una regla reduce cobertura, no aprueba*. **V2 encendida en regresión, apagada por defecto en un vídeo largo** |
| ~~**C13**~~ | `qpdf` y `tesseract` | 🟢 **CERRADO** por P2. **8 líneas de Dockerfile, 28,1 s, +50 MB (+0,9 %).** qpdf 12.4.0: **7 de 7 operaciones**. Tesseract 5.5.0 **con `spa` incluido**. **El coste real de los 7 `no_evaluable` era dos motores, 50 MB y 28 segundos** |
| **C14** | ✅ **CERRADO el 22/08 por F1** (`bench/firmas-contrato.md`), **y con la conclusión invertida.** 24 → **147 nombres**, 26 → **338 extensiones**, más una tercera tabla de **112 extensiones sin marcador**; el punto 1 pasa del **12,4 % al 54,2 %** con **0 falsos positivos** sobre las 53. **Pero no se pueden verificar 500 firmas porque no existen 500 firmas: 90 de 381 formatos (23,6 %) no tienen marcador**, y ahí tampoco aplican los puntos 2 y 3. **Y el fallo emblemático lo atrapa G6, no el vocabulario: 22 de 22 frente a 0 de 22** | 🟢 **CERRADO** |
| **C27** | **Subir G6 de `aviso` a `fallo`** — hoy está calibrada sobre **22 casos de un solo motor**. **CERRADO el 02/09 por worker2, decisión: SE QUEDA EN `aviso`, definitivo.** `contrato-familia-resvg.md` ya deja la fila sin bloqueo de datos, solo sin decidir: los dos casos temidos (`png→apng`, `mkv→mka`) no pueden disparar G6 porque ya están en `EXT_A_FIRMAS`; el riesgo real son 4 falsos positivos de alias de TGA; y **32 de 32 en ImageMagick, 0 de 41** en los otros seis motores (ffmpeg, Ghostscript, vips, soffice, inkscape, pandoc) — la calibración sigue siendo de **un motor de siete**. Subir a `fallo` con la excepción de los alias de TGA exigiría barrer el vocabulario ENTERO de alias (no solo TGA) para poder decir que esos 4 son el conjunto COMPLETO de falsos positivos, y eso no está medido ni es parte de este cierre. **El argumento que cierra la fila es el que la propia fila ya traía: una regla calibrada sobre un motor de siete no puede vetar** — subirla a `fallo` convertiría un aviso razonable en un bloqueo sin la cobertura que lo justificaría. Verificado en código: G6 sigue en `aviso` en `filex/verificador.py:3461`, sin tocar | 🟢 **CERRADO, se queda en `aviso`** · `contrato-familia-resvg.md` |
| **C28** | **Los 86 destinos indeterminados del censo de firmas**: 79 que ningún motor de esta máquina escribe y 7 donde la muestra describe al escritor y no al formato. **REVISADO el 01/09 por worker2: el enunciado "CERRADO" era más cerrado de lo que dice su propio informe (trampa 58/44).** Lo que sí cerró F2 el 28/08 (`firmas-cierre.md`): los 86 no eran «79 + 7» sino **56 + 17 + 13** (tercera clase no prevista), y de los 17 «banner del escritor» los **17 de 17** quedan cerrados por prefijo (0 de 20 adaptadores con segundo escritor). **Pero de los 56, el propio §8 del informe («Lo que este informe deja PENDIENTE») declara sin resolver justo lo que esta fila daba por hecho:** «FATE cierra 15» es la propuesta, no el cierre — ítem 2: *«Aquí sí hace falta FATE o una build de ffmpeg con más codificadores. **No lo he descargado**, como pedía el encargo»* (comparte ese mismo recurso con **C16**); de los que la fila llamaba «21 con invocación mejor» el informe cuenta **23**, de los que **solo 6 están probados y 17 siguen pendientes** (ítem 3); y quedan **8 `sin_clasificar`** sin resondear (ítem 4, `stderr` truncado a 400 caracteres). Lo genuinamente cerrado: la reclasificación 56+17+13 y los 17/17 de banner. Trampas 72 y 73 | 🟡 **PARCIAL** · `firmas-cierre.md` §4.4, §8 |
| **C29** | **Llevar el nivel de `familia` al veredicto.** Hoy `G5` es `informativo` y la cobertura cuenta la comprobación de familia como cubierta; una lectura estricta las dejaría en `ok_parcial`. **CERRADO el 28/08 por V, y destapó un defecto que nadie había visto**: `EXT_FAMILIA` se construía **sin `.split()`** y contenía los *caracteres* de la cadena, así que **el nivel de familia entero era código muerto** —`G5` no se emitió ni una vez— **y nadie lo vio porque el recuento cuadraba** (28 caracteres distintos; 42 extensiones reales). Ya con la pregunta formulable: **mueve 3 de 53** y son `.csv`/`.json` que la sonda parsea entera, así que degradarlas sería mentir por pesimismo. **Decisión: no.** Es la trampa 48 | 🟢 **CERRADO** |
| **C30** | **Repetir la prueba ancha de falsos positivos DENTRO del contenedor.** Cubre los **385 destinos locales**, no los 162 del contenedor. **CERRADO el 28/08 por F2, y encontró lo que se buscaba:** la prueba ancha local da **0 falsos positivos sobre 345** y dentro del contenedor **11 celdas en 4 destinos** —el mágico de VIPS es de **endianness** y la tabla traía media; GraphicsMagick escribe `id=MagickCache`; su PCX va sin comprimir—. Reejecutada con los arreglos: **11 → 0, cero regresiones**, y las dos capturas legítimas siguen atrapadas. `sin_vocabulario` **27 → 11**. **G6 sigue siendo 100 % GraphicsMagick**: el segundo motor resultó ser el clon del primero. Trampa 71 | 🟢 **CERRADO** |
| **C31** | ~~**`_datos` lee el fichero entero en memoria** — 156 MB de RAM para contar comas en el TXT de ImageMagick. Y dos colisiones declaradas **sin falso positivo hoy**: `.pcd` como `mpegaudio` y TGA/CUR compartiendo `00 00 02 00`~~ **LAS DOS CIFRAS DEL ENUNCIADO SON FALSAS — MEDIDO el 22/08** (`bench/hito3-mudanza.md` §6.1-6.3). **(a) No es ×1 la RAM: es ×21,3** en la rama normal (y ×7,0 en la degradada); el culpable **no es el `read()` sino guardar `d["csv_filas"]`**, así que sobre el TXT de 156 MB son **≈1,1 GB de pico**, y el tiempo **no es lineal** (65 s para 32 MB). **(b) `.pcd` NO es «una colisión sin falso positivo»: es un falso positivo VIVO** — este ImageMagick escribe PhotoCD, y un `png→pcd` legítimo con `rc=0` sale **`veredicto: FALLO`**. **(c) TGA/CUR es un falso NEGATIVO confirmado en ejecución** (un TGA con extensión `.cur` sale `ok_parcial` con cero hallazgos). Ninguno arreglado; §6.2 deja tres opciones con su tensión de diseño y recomienda la **C**: no derivar la categoría de una firma que el punto 1 ya marcó dudosa. **CERRADO el 02/09 por worker2 (`6e98c44`), verificado por el maestro** (`bench/pcd-y-memoria.md`): la RAM baja de **×21,3 a ×6,2**, y el falso positivo vivo de `.pcd` y el falso negativo de TGA/CUR quedan arreglados | 🟢 **CERRADO** · `bench/pcd-y-memoria.md` |
| **C32** | **La contradicción viva entre dos informes.** `hito3-mudanza.md` §7 pide *«una corrección a `bench/firmas-contrato.md` §10, que no es mío y cuyo autor (F1) debería revisar»*: el ratio de RAM (×21,3/×7,0, no ×1) y que `.pcd` **sí** produce un falso positivo. **REVISADO el 01/09 por worker2: la arbitración YA OCURRIÓ, en otras dos filas de este mismo inventario, aunque nadie lo cerrara aquí.** **C31** (abierta, enunciado corregido) ya declara MEDIDAS las dos cifras exactas que `hito3-mudanza.md` pedía arbitrar (×21,3/×7,0 de RAM, `.pcd` como falso positivo vivo), citando `hito3-mudanza.md` §6.1-6.3 contra `firmas-contrato.md` §10.2-10.4/§10.8. **C37** (cerrada) mide además la consecuencia: el contrato completo sobre un `.pcd` legítimo devuelve `fallo`. **Lo que sigue sin pasar es solo la acción literal pedida** — nadie ha editado el texto de `firmas-contrato.md` §10, que sigue con las cifras originales (verificado línea por línea) — pero la pregunta de fondo («¿quién tiene razón?») está resuelta y documentada con número, no es una contradicción viva. **CERRADO el 02/09 por worker2 (`6e98c44`)**: la acción literal que faltaba —escribir la corrección en `firmas-contrato.md` §10— está hecha, como **corrección fechada** y sin borrar el texto viejo | 🟢 **CERRADO** · `bench/pcd-y-memoria.md` |
| **C33** | **YA ESTABA CERRADO CUANDO SE ESCRIBIÓ ESTA FILA, y nadie lo comprobó — VERIFICADO el 27/08 sobre el código.** El diff de W9 se aplicó en el commit `c2f6a59`, cuyo título lo dice: *«Hitos 3 y 4, y W9 cerrado dentro del propio núcleo de FileX»*. `nombre_seguro` se llama hoy en `filex/confinamiento.py:119` (lectura) y `filex/nucleo.py:192` (escritura). ~~**Es lo más urgente de esta sección**~~ — lo fue durante cuatro días **sobre un fallo que no existía**. La fila se copió del informe de K3 sin mirar el árbol: **un inventario que se escribe desde los informes y no desde el código envía agentes a arreglar lo ya arreglado** | 🟢 **CERRADO** · commit `c2f6a59` |
| **C34** | **`job cancelar` sigue sin matar el árbol** de procesos. Heredado del hito 4 y reconfirmado en el 7. Con el precedente medido de los tres `soffice` que sobrevivieron **37 minutos** a un `taskkill /F /T`, no es teórico. **CERRADO el 27/08 por N-a** (`bench/cancelacion-y-servicio.md`): el asa del `Popen` **no se devuelve, se hace ALCANZABLE** —un registro `{ident → Popen}` en `invocacion.py`, porque un trabajo corre entero en su hilo—, y `nucleo.py` no cambia ni una línea. **De 21 741,8 ms a 279,6 (×77,8) de extremo a extremo**; el registro cuesta **0,7 µs** en el camino normal. El salto en contenedor también muere (9 de 9), y Q lo mejoró después | 🟢 **CERRADO** · `cancelacion-y-servicio.md` |
| **C35** | **Gotenberg, que es lo que el título del hito 5 pedía.** El hito se cerró por `filex-c13`, no por Gotenberg. Con él, los otros siete de `hito5-documental.md` §8: fidelidad más allá del centinela, `epub→mobi/azw3` con un lector de MOBI, una segunda semilla de documento, `xlsx/pptx/csv/svg/tex` dentro del contenedor, el arranque en frío (**34 672 ms** el primer `docker run`) y reutilizar contenedor vivo sin perder el punto 5. **MEDIDO el 01/09 por worker2** (`bench/gotenberg-y-mcp.md`): **SUPERADA con número** — sobre las siete entradas del banco del hito 5, Gotenberg cubre **6 de 7** y `filex-c13` **7 de 7**, así que **Gotenberg no añade conversión sobre C13** y pierde `epub→pdf`, donde su petición válida devuelve **HTTP 500** y Calibre en C13 entrega 26 817 B. El primer intento destapó **dos defectos del arnés** —el nombre de salida de LibreOffice y el `index.html` obligatorio para Markdown—, y el 500 de EPUB **sobrevivió a corregirlos**: es del motor, no de la entrada. **PENDIENTE: la latencia limpia con n≥9 y testigos**, que esta tanda no midió — Gotenberg exige un servicio HTTP vivo y C13 usa contenedor efímero, y esa diferencia operativa no está convertida en ms | 🟡 **PARCIAL** · `bench/gotenberg-y-mcp.md` |
| **C36** | ~~Los **ocho** pendientes restantes de `hito4-mcp.md` §13~~ **SON NUEVE, y DOS YA ESTABAN CERRADOS — recontado el 01/09 por worker2** (`bench/gotenberg-y-mcp.md`): W9 se cerró en el commit `c2f6a59` —reproducido ahora, 2 de 2 pruebas de ADS pasan— y `job cancelar` por C34/N10. **Quedan siete vivos.** Uno de ellos ya trae medida: el registro real cargado da **215 aristas, 30 orígenes, 29 destinos, cinco herramientas y 1 605 tokens** (`o200k_base`), medido sobre el árbol actual y no extrapolado — con Gotenberg y el sidecar **aún fuera del registro**, así que su curva final no se inventa. Los siete restantes: repetir §4 con otro modelo y n≥10, qué sustituye a `roots` en el protocolo 2026-07-28, la caché de roots invalidada por **una emisión real** (sigue sin observarse), medir el catálogo con el registro completo del hito 5, una prueba de subsunción automática, idempotencia ante `Resolve(ListRoots)` doble y el coste de un `convert` con ruta denegada (**gasta un `job_id`**) | 🟡 **PARCIAL, enunciado corregido** · `bench/gotenberg-y-mcp.md` |
| **C37** | **Los 12 formatos de la deuda de firmas** (`firmas-contrato.md` §3.2). **Los dos accionables son `pict` y `pcd`**: bastaría leer más allá del byte 512 **solo cuando la extensión lo pide**. **CERRADO el 28/08 por F2 — y el caso «benigno» no lo era:** `firmas-contrato.md` §10.3 declaró que un `.pcd` mal clasificado *«no produce falso positivo»*, y el contrato completo sobre un `.pcd` legítimo devolvía **`fallo`**, porque la firma alimenta también al **despachador**. **Y la vía propuesta queda refutada con número**: la puerta por extensión no se paga —la diferencia entre leer 2 056 y 512 bytes está bajo el suelo de la tanda—, así que se lee siempre. Dos accionables más de los previstos (**3DS** autovalidante, **Rocket eBook** de 28 bytes). Trampas 70 y 73 | 🟢 **CERRADO** |
| **C38** | ✅ **CERRADO el 31/08 por worker1** (`bench/lock-desde-python.md`). `filex/gpu.py` expone `Lock(etiqueta)`, y el censo corregido da **25** `.py` con `nvidia-smi` frente a **1** con `gpu_acquire` —no 15—. **El primitivo se decide con número y en la misma tanda**: mutex `Global\` **11,6 µs** contra **472,2 µs** del candado de rango, **×40,7**. **Pero la primera versión rompió 5 pruebas y las 5 tenían razón**: poner la exclusión solo en el mutex y dejar el fichero como metadato crea **dos poblaciones que no se ven** —los 24 arneses sin migrar toman `O_EXCL` sobre el fichero y no aparecen en el mutex—, que es la **media exclusión** de la trampa 77 reproducida dentro del cambio que venía a cerrarla. Se toman **los dos, fichero primero**. **Salvedad que no se redondea: el ×40,7 compara PRIMITIVOS; la ruta entregada cuesta ~484 µs mientras dure la migración.** **PENDIENTE: migrar los 24 arneses** | 🟢 **CERRADO** |
| ~~**C15**~~ | Cuánto del 50,5 % se recupera con una invocación mejor | 🟢 **CERRADO** por P2. **El 18,8 %** [16,8–21,3]: la tasa baja a **41,0 %** con los mismos motores y build. **3 226 aristas (10,2 %) son ganancia automática** —se puede prometer—, 2 704 exigen un parámetro del usuario, y **25 603 (81,2 %) son irrecuperables**. **`-frames:v 1 -update 1` recupera 13 de las 27** del residuo |
| **C16** | **El 54,78 % de aristas indeterminadas.** Exige un corpus de 445 formatos que ningún motor local escribe (vía: corpus FATE de ffmpeg, ~1 GB). Es lo único que convierte el escenario central (48,6 %) en un número medido. **Y desde el 22/08 tiene un segundo cliente: C28 exige el MISMO corpus FATE**, así que cerrar uno abarata el otro | 🔴 **ABIERTO** · ídem §7, §11.1 · `firmas-contrato.md` §10.1 |
| ~~**C17**~~ | Censar las 140 aristas de Ghostscript y Gotenberg | 🟢 **CERRADO** por P2. **3,1 % nominal** [0,9–10,7], con **censo COMPLETO de Ghostscript (9/9 reales) y de Gotenberg/Chromium (25/25 reales)**. **Coincide con el 3,0 % del estrato PDF de E1 por un camino independiente.** Las dos nominales son de LibreOffice. **Sesgo declarado: 72 de las 102 extensiones de LibreOffice no se pudieron materializar → cota inferior** |
| **C18** | **Publicar los parámetros de I1 de `fidelidad-caminos.md`** (ppp de rasterizado, idioma de OCR, fórmula de similitud) para poder cerrar su 99,0 %, que **no se reproduce** (94,7–97,1 %). **Sigue NO REPRODUCIDO, no refutado** | 🔴 · `verificador-ghostscript.md` §5.7 |
| **C19** | **El miembro de la familia de `resvg` que sigue DESCUBIERTO:** audio con **un canal silenciado hacia un destino con pérdida**. El contrato ve 2 canales, frecuencia y duración correctas; A4/A5 no aplican porque no hay PCM que comparar. **El mismo fallo hacia FLAC sí lo atrapa A4: la cobertura depende del destino, no del fallo.** Propuesta sin medir: energía por canal con `ffmpeg -af astats` (sonda externa, grupo C). **CERRADO el 28/08 por V** con la regla **A7**, en fidelidad y decidido con número: 110–147 ms frente a los 0,37 del contrato, y **la energía no está en ninguna cabecera**. Margen de 28,48 dB por el lado del falso positivo. **Con punto ciego publicado:** por debajo de 48 kb/s Opus rellena el canal mudo y A7 no dispara | 🟢 **CERRADO** · `contrato-familia-resvg.md` |
| **C20** | **Validar el sustituto de `P9` a escala.** El acuerdo entre dos pasadas de OCR con idiomas distintos separa **16 de 16 sin error** (banda vacía de 0,19 puntos), **pero está medido sobre 16 pares y un solo motor**: dos idiomas del mismo motor **podrían acordar en su propio error**. Falta validarlo **fuera de Ghostscript** y sobre vocabulario que `eng` no comparta. **Y decidir si `P9` se retira o se sustituye**. **CERRADO el 02/09 por worker2 (`6e98c44`) POR REFUTACIÓN, verificado por el maestro** (`bench/acuerdo-y-cruce.md` §2): **la separación de 16/16 NO se reproduce** fuera de Ghostscript, y los dos mecanismos están diagnosticados. Con `escaneado_d4` y los cuatro legado el patrón se sostiene; **con la familia completa, 2 de 8 documentos dan una lectura falsa** (una `bueno` marcada `ruido`, dos `ruido` marcadas `bueno`). **Decisión: NO entra como regla, ni siquiera informativa, en esta forma.** Es la **trampa 78** confirmada: un umbral calibrado con un solo motor describe a ese motor | 🟢 **CERRADO, refutada** · `bench/acuerdo-y-cruce.md` §2 |
| **C46** | **El residuo de `C20`: al acuerdo `spa`/`eng` le faltan DOS guardas, y remedir con ellas es un encargo nuevo — declarado el 02/09** (`bench/acuerdo-y-cruce.md` §2.3). Las dos que su autor nombra: una **longitud mínima no vacía** (al estilo de `P9_TOKENS_MIN`) y una **comparación que no penalice sustituciones de un solo carácter acentuado**. Sin ellas, 2 de 8 documentos leen al revés. **No se hereda como «casi hecho»**: la fila que lo midió se cerró **refutando** su propio enunciado, así que esto es una hipótesis nueva, no una continuación | 🔴 **NUEVO** · `bench/acuerdo-y-cruce.md` §2.3 |
| **C21** | **Un suelo duro de PSNR para V8.** Un vídeo **enteramente negro** sale con **5,39 dB** y severidad `aviso`, porque V8 está calibrada para «recodificación con pérdida». **5,39 dB no es una recodificación agresiva: es otra imagen.** **CERRADO el 28/08 por V — y el suelo está REFUTADO y puesto igualmente:** las dos clases **se solapan 15,66 dB** (un vídeo congelado da más PSNR que siete recodificaciones legítimas), así que no existe umbral que las separe. Lo decide la tabla: **10 dB da cero falsos positivos**, y 12/15/18 atrapan las mismas 12 patológicas **añadiendo 3 falsos positivos**. El negro (5,39 dB) pasa a `fallo`. Es la trampa 51 | 🟢 **CERRADO** |
| **C22** | ~~**Ampliar el patrón oro con una salida multifichero** (una HLS y una secuencia `%d`). `referencia.json` **no tiene ni una**, así que el «0 falsos positivos» del punto 5 se apoya en cuatro casos fabricados a propósito~~ **CERRADO el 30/08 por worker2** (`bench/patron-multifichero.md`). **Criterio MEDIDO:** una salida es multifichero legítima si sus ficheros extra aparecen **en el directorio de destino** y están declarados por formato (`m3u8`) o por patrón de nombre (`%03d`); no se usa número de ficheros ni porcentaje de bytes como disparador. Los dos casos fabricados (HLS `h.m3u8` y secuencia `f%03d.png`) cubren el hueco del patrón oro y añaden **0 falsos positivos**. *(Esta fila estuvo marcada en rojo nueve días con el informe ya escrito y citado en §1 — es la trampa 44/58 dentro del propio inventario: un informe registrado no es lo mismo que una fila movida.)* | 🟢 **CERRADO** · `patron-multifichero.md` |
| **C23** | **La curva fina del punto de cruce «en proceso / sonda externa» para píxeles.** Medido en tres tamaños (0,08 / 0,32 / 1,84 Mpx), con el cruce en **~0,1 Mpx**. **Decide en qué régimen corre cada regla de fidelidad**, y hoy la implementación usa el camino en proceso **porque no añade dependencias**, con un precio medido. **CERRADO el 02/09 por worker2 (`6e98c44`), verificado por el maestro** (`bench/acuerdo-y-cruce.md` §3): la curva pasa de **3 puntos a 11**, y el cruce se confirma entre **0,08 y 0,16 Mpx** | 🟢 **CERRADO** · `bench/acuerdo-y-cruce.md` §3 |
| **C24** | **MITAD CERRADA el 22/08, y el enunciado cambia.** La mitad EXTERNA está explicada y **no era el envoltorio: era el `--psm`.** Sobre el mismo `d3`, `psm 3/4` devuelven **0 bytes** y `psm 6/11` devuelven **113,92 %** y **188,61 %** — *silencio y alucinación son el mismo motor con distinto modo de segmentación*, y **los tres devuelven `rc=0`**. Añadido: **0 bytes puede además ser un proceso que NO ARRANCÓ** (`rc=0xC0000142`), indistinguible del silencio legítimo si no se registra el `rc` (trampa 25). **Sigue abierta la mitad de Ghostscript: qué `--psm` usa su Tesseract embebido no se ha sondeado** | 🟡 **REDEFINIDO** · `psm-y-rasterizador.md` §2.2 §9, `k-por-motor.md` §6.1 |
| **C25** | **MITAD CERRADA el 31/08 por worker2** (ídem). `gxf` escribe; `mlp` y `thd` con **`-strict -2`** —eran `EXPERIMENTAL`, no «ningún motor lo escribe»—; **`amv` cerrado como fallo documentado** (`rc=-22`, dos intentos gastados). El residuo eran **15** y no 11, y **su «bloqueo» era falso**: `pool_indice.json` está versionado y el `MANIFIESTO.md` nombra `python _p2_semillas.py` (**trampa 95**). Reejecutadas: **0/15 buenas**, y clasificadas por lo que dice el `stderr` en vez de agruparlas bajo EINVAL — **5 `no_aplica`** (4 de imagen hacia muxer de audio, más `ass→m3u8`), **9 candidatas** de grafo de filtros, **1** de soporte de codificador. **Sigue abierto: las 9 candidatas y los crudos de TERCEROS** | 🟡 **PARCIAL** |
| **C26** | ✅ **CERRADO el 23/08 por L1** (`bench/lock-de-maquina.md`). El lock pasa a **`/tmp/filex-gpu.lock` = `%TEMP%`** (MEDIDO: `cd /tmp && pwd -W` → `C:/Users/krato/AppData/Local/Temp`), deja de quedarse **huérfano** —lleva dentro el **winpid** y el nombre de imagen del dueño, y la recuperación baja de **900 s a 1 s**— y se le añade **la mitad que el enunciado no pedía y que es la que cierra el caso real: DETECCIÓN.** **Un lock no obliga a cooperar a quien no lo toma**: la sesión de ASR nunca iba a tomar este fichero, esté donde esté. Así que `gpu_acquire` mira ahora la **VRAM libre** y **se niega a medir** por debajo de **6 000 MiB**. Línea base medida de esta máquina: **3 292 / 3 356 / 3 448 MiB ocupados** (mín/mediana/máx, n=90 a 1 s). **Y un límite medido que hay que saber: en WDDM la VRAM POR PID no es observable** (`--query-compute-apps` devuelve `[N/A]` en los 30 procesos y `pmon` responde *«not supported in this configuration»*), así que *«mira los PID»* solo puede dar **una lista de sospechosos**, nunca al culpable | 🟢 **CERRADO** |
| **C39** | ✅ **CERRADO el 31/08 por worker1** (ídem). Las **cuatro** celdas de cruce Git Bash×WSL bloquean, con el dueño vivo antes y después — antes era **una verde de cuatro**, y WSL no se excluía ni consigo mismo. **Lo que las hace significar algo son los controles E y F**, que la primera entrega no traía: sin dueño, `rc_eval=0` en los dos intérpretes. Con las cuatro a `124` y ninguna verde, «respetó el mutex» era indistinguible de «el evaluador no arrancó y el tope saltó igual» — trampa 91, en el mismo arnés que la escribió. Dos hallazgos de interoperabilidad: **`wslpath -w`** —sin él Windows Python abría `D:\mnt\d\…`— y **`taskkill /PID` en WSL contra `//PID` en Git Bash** | 🟢 **CERRADO** |

| **C40** | ~~**Diez binarios versionados fuera de LFS, 17 MB**, que habría que borrar dejando la orden que los reproduce~~ **REFUTADA EN 7 DE 10 EL MISMO DÍA QUE SE ABRIÓ, y por su propio repositorio.** Siete están en `bench/salidas-competidores/`, cuyo `MANIFIESTO-retirado.md` (2026-08-20) declara *«evidencia forense irreproducible: los contenedores de ConvertX y SnapOtter cambian de versión, así que sus fallos no se regeneran»* — y por eso su poda de 110,5 MB fue conservadora, *«no se ha retirado ninguna prueba»*. **Son la evidencia de la tesis central del proyecto**, y borrarlas la destruye. La regla §6 dice *«no versiones salidas binarias **regenerables**»* y yo cité la mitad. Declaradas en `ci/evidencia-irreproducible.txt`, que **exige un motivo y su documento**: no es una lista de perdón. **Quedan 3 abiertos**, los de `salidas-mcp-refs/multimedia/`, que sí son salidas de terceros con byte declarado y sin orden que las reproduzca. **CERRADO el 02/09 por worker2 (`6e98c44`)**: los tres se **declaran** en `ci/evidencia-irreproducible.txt` con su motivo —el mux de Matroska/WebM es **aleatorio en cada pasada**, así que no se regeneran—, no se borran. `ci/integridad.py` pasa de `3 binarios sueltos` a **`0 sueltos · 3 rutas declaradas evidencia`** | 🟢 **CERRADO** · trampa 106 |
| **C41** | **Diecisiete directorios `bench/salidas-*` sin manifiesto** ~~veinte~~ — la cifra bajó dos veces en el mismo día y **ninguna por trabajo**: primero por medir el árbol en vez del repositorio (trampa 104), y luego porque la sonda exigía el nombre **exacto** `MANIFIESTO.md` y no veía ni `MANIFIESTO-retirado.md` ni `MANIFIESTO-img.md`, escritos los dos a propósito. La regla §6 los exige, y no es burocracia: sin manifiesto, un activo podado parece un **bloqueo**, que es la trampa 95 — y un bloqueo se acepta donde un rojo se investiga. Mismo trinquete: los diecisiete estaban congelados y el dieciocho rompía. **CERRADA el 01/09 por worker2: los 17 escritos, con `sha256`, tamaño y la orden, recalculados hoy; `ci/heredado.json["manifiestos"]` queda VACÍO.** Y de propina un hallazgo que nadie buscaba: **`bench/salidas-cota-audio/` es un directorio huérfano** —ningún informe lo cita— de un intento de N28 abandonado con un `ValueError` que worker2 **reprodujo determinísticamente en tres reejecuciones** antes de documentarlo, en vez de inventarle una orden. *(La fila se quedó ABIERTA tras hacer el trabajo: el propio saneo cometió el defecto que venía a cazar, y lo corrigió el master al integrarlo.)* | 🟢 **CERRADA** · `saneo-inventario.md` |

| **C42** | **La lista de módulos aptos para la CI estaba medida en la plataforma equivocada — CERRADO EN PARTE el 01/09 por el master (commit `0999538`).** `ci/linux-apto.json` ya mide **en el runner de verdad** (`ubuntu-latest`, Python 3.11.16): **7 aptos, 198 pruebas**, y el `continue-on-error` a nivel de trabajo ya se quitó. **RONDA 4 — worker2: los 10 no aptos, clasificados uno a uno contra su traza real, no contra su nombre.** Los diez eran **UN SOLO mecanismo repetido, no diez causas**: (a) `.github/workflows/suite.yml` no instala ningún motor externo, así que sin ImageMagick "ningún motor disponible lee 'png'" hace caer en cascada `test_cerrojo` (5), `test_hito1` (2), `test_hito4` (9) y **las 31 de `test_hito7`** — incluidas comprobaciones de confinamiento que en teoría no deberían tocar un motor, porque MCP/API resuelven el formato antes de validar la ruta; (b) `corpus/video/tipico.mp4` y `corpus/audio/*.flac` son punteros de Git LFS con `lfs: false` (trampa 34, sin proteger en estos dos ficheros): `test_a7_ciego` entraba en `setUpClass` con un puntero y reventaba con «0 pruebas corridas, 1 error de carga» —MEDIDO, reproducido exacto dentro de un contenedor limpio—, y las 8 de `test_cancelacion_procesos` fallaban igual con "ningún motor disponible lee 'mp4'" **incluso con ffmpeg instalado**: no era ffmpeg, era el puntero; (c) `filex.gpu.Lock._vivo()` llama a `tasklist` (Windows) para saber si el dueño de un lock huérfano sigue vivo — fuera de Windows falla con `FileNotFoundError` y responde "vivo" por el lado seguro del error, así que un huérfano **nunca** se recupera en Linux: esto, y NO "no hay tarjeta"/"no hay ffmpeg con NVENC` como decían las descripciones viejas, es lo que rompía `test_gpu_lock` y una celda de `test_hito2` (trampa 90/93 de CLAUDE.md, aplicada a un código que nadie había mirado desde ese ángulo; el arreglo de fondo es de `filex/gpu.py`, carril GPU — aquí solo se documenta con un `skipUnless` honesto); (d) el `CUELGA` de `test_cancelacion` era `docker run` intentando descargar `ghcr.io/c4illin/convertx:latest` (5,7 GB) en cada ejecución porque `_hay_docker()` solo comprobaba que el DEMONIO estuviera vivo, no que la IMAGEN estuviera cacheada. **Las cuatro causas se arreglaron con `skipUnless` honestos** (no se tocó `filex/verificador.py`, `filex/motores.py`, `filex/api.py` ni `filex/nucleo.py` de este carril, y NO se tocó `filex/gpu.py`, que es de worker1) y se verificaron en dos entornos: la máquina real (con ImageMagick y ffmpeg, 0 fallos) y un contenedor `python:3.12-slim-bookworm` limpio que aproxima `ubuntu-latest` (LFS con punteros reales, sin motores) — de 7/17 a **16/17 módulos sin fallos ni cuelgues** en esa aproximación. **PENDIENTE, declarado y no forzado:** (1) `test_watcher_n` (4 fallos, "la estabilidad se comporta distinto en ext4") no se pudo reproducir en tres entornos POSIX distintos (DrvFs, tmpfs de WSL2, overlay2 de un contenedor) — sigue en `no_aptos` sin arreglo, tal como pide el proyecto en vez de forzar un skip sin evidencia; (2) dentro del contenedor de aproximación aparecieron DOS fallos nuevos en `test_hito2` con el ffmpeg de Debian bookworm (canales de audio alterados en un `.mkv` de dos pistas, y `av1_nvenc` listado de otra forma) que dependen del BUILD exacto de ffmpeg, no del mecanismo ya arreglado — **no se tocan hoy**, y `ci/linux-apto.json` **no se sobrescribe desde aquí**: la aproximación de contenedor no es el runner real (la propia regla del proyecto, trampa 104), así que la promoción final de módulos a `aptos` la decide `python3 ci/sonda_linux.py` ejecutado en `ubuntu-latest` de verdad, no una simulación | 🟡 **9 de 10 causas clasificadas y arregladas con código, 1 sin reproducir, promoción pendiente de correr en el runner real** · `bench/ci-y-contrato.md` §1 |

| **C43** | **La huella del código es función del INTÉRPRETE, así que las 215 aristas selladas sólo valen bajo el Python que las selló — MEDIDO con control positivo.** Mismo runner y mismos bytes: con 3.11 `test_sondeo` pasa y con **3.13 caducan los siete motores a la vez**; y `filex/verificador.py` da `eec752a87e8927cf` bajo 3.11.9 y `16ddd8d13d61c4f1` bajo 3.14.4. **Hay que decidir entre dos cosas, y ninguna es gratis**: meter la versión del intérprete en la huella —que caduca todo hoy, una vez, a cambio de que el aviso sea verdadero— o **declarar el intérprete de sellado** y negarse a comparar huellas de intérpretes distintos. Hoy no hace ninguna de las dos y **el modo de fallo es el peor: dice «caducado» donde debería decir «no comparable»**. **DECIDIDO el 02/09: se declara el intérprete de sellado y se niega la comparación entre versiones distintas** — no caduca ni una arista y convierte un falso positivo en un error honesto. **CERRADO el 02/09 por worker2 (`42f090d`), verificado por el maestro** (`bench/huella-y-runner.md`): **ningún motor caducado ni no comparable**, con línea base medida **antes** de tocar nada | 🟢 **CERRADO, con su implementación CORREGIDA el 02/09** (`bench/acuerdo-y-cruce.md` §1): la versión de la ronda 5 comparaba `platform.python_version()` **completo**, y el runner corre **3.11.16** frente al **3.11.9** del venv — habría declarado `interprete_distinto` **en cada ejecución de la CI**, es decir *el propio arreglo de `C43` habría bloqueado la fusión que vino a proteger*. Ahora la granularidad es **`mayor.menor`**, que es la que la CI declara estable (`python: ['3.11']`) y sigue separando 3.11 de 3.14. **PENDIENTE declarado, no supuesto:** si `ast.dump` puede diferir entre dos parches de la misma menor · `bench/huella-y-runner.md` · trampa 105 |
| **C44** | **Runner autoalojado con aprobación manual para PRs de terceros — DECIDIDO el 02/09.** Es lo único que cubriría GPU, NTFS y contenedores locales, que es casi todo el valor del proyecto: hoy la CI de GitHub no toca **nada** de eso. Dos cosas que van dentro del alcance y no fuera: **(a)** el runner es un **TERCER ACTOR sobre el lock de la tarjeta**, y el lock no excluye a quien no lo toma —**24 de 25 arneses `.py` siguen tomando el fichero y no el mutex** (trampa 96), así que va **después de `N29`**; **(b)** sobre un runner de **Windows**, `ci/linux-apto.json` deja de tener sentido —podrían correr los **17** módulos, no 7—, y ese es el premio real. **DISEÑO CERRADO el 02/09 por worker1 (`b582ceb`), verificado por el maestro** (`bench/runner-autoalojado.md`, `.github/workflows/windows-gpu.yml`, `ci/lock_preflight.py`, `ci/sonda_windows.py`). **(1) El lock, con los dos controles:** el job **se niega** si la tarjeta está ocupada en vez de esperar los 900 s de producto —negativo, un dueño vivo real no se roba; positivo, un `taskkill /F` sobre un proceso real se recupera en **0,171 s**, que es `N29` funcionando fuera de su propio informe—. **(2) La seguridad se apoya en DOS mecanismos distintos a propósito** —permiso de escritura de la plataforma para `push`/`workflow_dispatch`, y `environment` con revisores para `pull_request`— más una tercera capa: `correr_gpu` por defecto **`false`**, así que un PR aprobado por error sigue sin poder tocar el lock. **(3) El premio, medido y NO congelado:** **15 de 15 módulos aptos en Windows local, 387 pruebas, 0 fallos** —frente a 7 de 17 en Linux—, y **no escribió `ci/windows-apto.json`** porque Windows local **no es el runner** (trampa 104 respetada, no citada). **Y lo que NO puede hacer un agente, verificado con `gh api` por el maestro:** el repositorio **YA es público** (`private: false`), su `approval_policy` es **`first_time_contributors`** —un externo aprobado una vez pasa sin aprobación para siempre— y **hay 0 entornos**, así que `aprobacion-manual-gpu` no existe y GitHub lo crearía **vacío, sin revisores**. **De ahí sale una regla de ORDEN que ninguno de los dos había escrito: el entorno con revisores obligatorios se crea ANTES de registrar el runner.** Al revés hay una ventana en la que el runner existe, el *workflow* está en `main`, y la única defensa viva es el filtro de `head.repo.full_name` que el propio diseño declara *«una comodidad, NO la defensa»* | 🟡 **DISEÑO CERRADO; registrar el runner y fijar los ajustes es del usuario** · `bench/runner-autoalojado.md` |
| **C45** | **Las tres acciones de terceros están ancladas por ETIQUETA, no por `sha` — y una de ellas corre en el runner AUTOALOJADO.** `actions/checkout@v4`, `actions/setup-python@v5` y `actions/upload-artifact@v4`: una etiqueta es MUTABLE, así que quien controle el repositorio de la acción puede cambiar lo que `@v4` apunta. En `ubuntu-latest` eso ejecuta código ajeno en una máquina de GitHub; en `windows-gpu.yml` —que usa `checkout@v4` y `upload-artifact@v4` en las líneas 124, 176, 206 y 227— lo ejecutaría **en el escritorio del usuario**, que es justo lo que `C44` viene a proteger. El remedio es anclar por `sha` con el tag en un comentario, y `.github/dependabot.yml` (añadido el 02/09) los sigue moviendo igual. **Encontrado el 02/09 auditando la CI**, no midiendo | 🔴 **NUEVO** · auditoría de CI/CD del 02/09 |

### N · Deuda del paquete `filex/` — **nace el 23/08 y no tenía sección**

> El paquete de producción se construyó los días 22 y 23 (hitos 3, 4, 5 y 7 marcados HECHO en `PLAN-ORQUESTADOR.md` §7) **sin que este inventario registrara ni el trabajo ni la deuda que dejó**. Estas filas salen de `bench/hito7-superficies.md` §7.3 y del docstring de `filex/sondeo.py`.

| # | Pendiente | Estado / origen |
|---|---|---|
| **N1** | **El cerrojo de destino de FileX es DE PROCESO, no de máquina.** Tres peticiones simultáneas con tres entradas distintas a la misma ruta de salida devolvían **las tres `ok`**, declarando 13 516 / 14 402 / 647 580 B con **un solo fichero en el disco**. El arreglo está puesto en `filex/nucleo.py` (**3,2 µs de mediana, p90 4,6 µs, n=20 000 — el 0,0013 % de una conversión**), pero **una API y un watcher en procesos distintos siguen pudiendo pisarse**. Es **la misma clase de problema que C26**, y quien lo cierre debería reutilizar el mecanismo. **CERRADO EN DOS PASOS.** N-b reprodujo el fallo entre procesos de verdad —las tres cifras del hito 7 al byte— y lo cerró con candado de fichero **más detección**: la exclusión sola no bastaba, FileX pisaba el fichero abierto de un tercero devolviendo `ok`. P lo subió de usuario a **máquina** con un mutex en `Global\` que **no exige elevar**, y cerró el enlace duro con la identidad NTFS. Coste **1 169,7 µs, 0,319 %** de una conversión. Es la trampa 33 y la 35 | 🟢 **CERRADO** · `cerrojo-de-maquina.md`, `cerrojo-unico.md` |
| ~~**N2**~~ | ~~**La suite de pruebas lee estado del disco, así que NO es reproducible mientras se sondea.**~~ **REFUTADA EN MAGNITUD por D1 el 23/08 — MEDIDO, cuatro pasadas de 129** (`bench/deuda-sondeo.md` §4): con `_DIR` en un directorio VACÍO el grafo cae de **210 aristas `real` a 57** —se mueven **153**— y la suite da **exactamente `123 passed, 6 skipped`**, lo mismo que con el disco intacto. **0 de 129 pruebas dependen del estado del sondeo en disco.** Lo que sí la mueve —34 fallos— es declarar `nominal` las 215, y eso **ningún sondeo real lo produce**: es la cota superior del radio de explosión, no una medida de lo que pasa. Queda `congelar()`, ofrecido y **deliberadamente no puesto por defecto**. El enunciado original: OBSERVADO: una pasada de las 88 falló justo cuando el grafo pasó de 142 a 190 aristas `real` porque otro agente escribió su fichero a mitad; las dos siguientes dieron 88 en verde. **O las pruebas fijan su propio sondeo, o se declara que la suite no vale mientras se sondea** | ⚫ **histórico** (su enunciado está refutado) · `deuda-sondeo.md` §4 |
| **N3** | **El sondeo caduca al cambiar el CÓDIGO de FileX, no solo el `build` del motor — y hoy NO se comprueba.** MEDIDO el 22/08: 21 aristas medidas `nominal` quedaron obsoletas en cuanto se arreglaron la sonda y la invocación; al resondearlas, **20 de 21 salieron `real`**. El `build` protege contra cambiar de máquina; **nada protege contra cambiar de código**. ~~Arreglo propuesto: **una huella de `motores.py` y `verificador.py` junto al `build`**~~ — **CERRADO el 23/08 por D1** (`filex/huella.py`, `bench/deuda-sondeo.md`, commit `13181f6`), **y la lista propuesta estaba corta por los dos lados**: entra `invocacion.py`, y **3 de los 5 ficheros de sondeo los decide `motor_contenedor.py`**, que no se nombraba. Se hashea el **AST normalizado** —no el fichero: un `sha256` crudo caducaría las 215 al editar un comentario— en tres componentes, y lo que no coincide **se degrada a `sin_sondear`, nunca a `nominal`**. Es la trampa 32 de `CLAUDE.md`. **Queda PENDIENTE** resondear las 215 para elevar a MEDIDO el sellado de §3.3 | 🟢 **CERRADO** · `deuda-sondeo.md` |
| **N4** | **`_estable_en_disco` en POSIX devuelve `True` y el único cerrojo es `stat`.** En Windows el cerrojo real es `os.replace(p, p)` → `WinError 32`; ~~en POSIX no hay equivalente~~ — **REFUTADO y CERRADO el 28/08 por U**: era una deducción, no una medida. **`/proc/<pid>/fd` acierta los cinco estados en 5,6 ms**, frente a 110,6 de `lsof`. Con techo declarado: **51 de 96 descriptores legibles**, así que un escritor de otro usuario es invisible y la defensa POSIX es **estrictamente más débil, no equivalente**. Es la trampa 45 | 🟢 **CERRADO** · `watcher-y-desechables.md` |
| **N5** | **«Fichero incompleto» con un formato SIN suma de comprobación** (CSV, WAV): el watcher no tiene con qué detectarlo. **CERRADO el 28/08 por U, con el enunciado corregido: no es la suma de comprobación, es que la longitud esté DECLARADA y no DEDUCIDA.** El WAV truncado **sí** se atrapa (5 de 5 por `A1/V1`); el residuo real hubo que **fabricarlo** —un MP3 sin cabecera Xing al 50 % devuelve `ok` con 4,02 s de entrada y 4,02 de salida—. Declarado frente a bytes: **8 de 8, 58–116 µs y O(1)**. Es la trampa 46 | 🟢 **CERRADO** |
| **N6** | ~~**Mover `Servicio` y `Trabajos` a `filex/servicio.py`**~~ — **HECHO por N-a el 27/08**: `filex/mcp.py` baja de 45 123 B a 26 968 (**−40,2 %**). **Sin reexportar**, y con una prueba que recorre el AST de todo `filex/` y `pruebas/` y falla si alguien vuelve a entrar por `filex.mcp` —con un alias esa prueba no se podría escribir | 🟢 **CERRADO** · `cancelacion-y-servicio.md` §5 |
| **N7** | **No hay lock de GPU en `filex/`**, ni uso de GPU: las apariciones de `nvenc`/`cuda` en el paquete **son tres comentarios**. **CERRADO el 28/08 por H2 con `filex/gpu.py`**, que usa **el protocolo de `harness.sh`** (`O_CREAT|O_EXCL`, mismo fichero, mismo TSV) y no el candado de rango de bytes. **Y la medida destapa algo peor que la incompatibilidad limpia: `cerrojo.Candado` NO excluye al `noclobber`, pero SÍ lo bloquea a él de rebote** — la exclusión es **asimétrica** y desde el lado del `.py` parece funcionar. Media exclusión es peor que ninguna. NVENC cuesta ~211 MiB, ×21 menos que el margen del `GPU_GUARD`. Emparejado con **C38** (el lock de `bench/` tampoco existe en Python) | 🟢 **CERRADO** · `hito2-nvenc.md` §6 |
| **N8** | **Las TRES TRAMPAS propuestas y NO aplicadas a `CLAUDE.md`** (§10 de `hito7-superficies.md`, numeradas 26, 27 y 28 para ir **al final**): (26) dos peticiones simultáneas al mismo destino devuelven las dos `ok` y **el contrato no puede verlo** porque juzga dentro del desechable de R18; (27) *«si puedo abrirlo, está completo»* es falso **y la estabilidad de `stat` sola tampoco basta**; (28) **R1 y R4 están en tensión y ya hay número: 9,4 µs frente a 193,3 µs, ×20,6** — el mensaje y el código son idénticos y **lo que distingue es el reloj**. ~~**Nadie ha decidido si entran**~~ — **ENTRARON: son las trampas 26, 27 y 28 de `CLAUDE.md`**, al final y sin renumerar nada, como pedía el encargo. Verificado el 27/08 | 🟢 **CERRADO** |
| **N9** | **El oráculo temporal de R4 sigue sin resolverse**, que es lo que la trampa 28 describe: igualar por arriba convierte el rechazo en un **amplificador de DoS**; igualar por abajo pierde el `realpath`. **Se decide por superficie, y se dice** — pero no se ha decidido | 🔴 **NUEVO** · ídem §7.2 |
| **N10** | **La cancelación es DE PROCESO**, como lo era el cerrojo de destino: el registro `{ident → Popen}` vive en la memoria de un `filex`. La respuesta lo dice (`motor_detenido: false`) en vez de fingirlo. Cerrarlo pide un canal con nombre o un fichero de mando por trabajo — **y ahora hay primitivo: `filex/cerrojo.py`** — **CERRADO el 28/08 por T**, en dos mitades como manda la trampa 33: **mando** (fichero por trabajo, un vigilante por proceso) y **detección** (candado libre + disco diciendo `working` = huérfano, **sin consultar un PID**). **De nunca a 456,8 ms**, `motor_detenido: true` 9/9, y un dueño muerto pasa de `working` eterno a `proceso_dueno_muerto` | 🟢 **CERRADO** · `cancelacion-entre-procesos.md` |
| **N11** | **`olvidar_hilo()` es una DISCIPLINA que hay que recordar**, y este repositorio evita justamente eso en las invocaciones: los `ident` de hilo se reciclan y quien añada una tercera clase de trabajo tiene que llamarla. **CERRADO el 28/08 por T**: `invocacion.hilo_de()` + `servicio.en_curso()` + `Servicio._arrancar` como única puerta. `olvidar_hilo()` a mano **de 2 sitios a 0**, con tres pruebas sobre el AST que lo impiden —incluida la que pedía N-a: *toda función que llame a `trabajos.nuevo` tiene que llamar a `_arrancar`* | 🟢 **CERRADO** |
| **N12** | **La ventana entre la detección y el `move`.** `os.replace(p,p)` es un instante, no una vigilancia; se cierra abriendo el destino con `FILE_SHARE_NONE`. **CERRADO el 28/08 por Y — y NO se encogió al medirla: se ensanchó, y lo que se cayó fue el remedio propuesto.** La ventana dura **681,4 µs**, **×34 la detección**, y se reprodujo entre procesos en **12 de 12 celdas** (control sin gancho: 5 de 40). `FILE_SHARE_NONE` funciona —0 aberturas de 12 393 intentos— **pero excluye también al dueño** y obliga a convertir el `rename` en copia. Lo que la cierra es **`os.replace` en vez de `shutil.move`**: detección y acción en la misma llamada, 12/12 → **0 atropellos**, y **×18,0 MÁS RÁPIDO** sobre destino existente. Son las trampas 63 y 64 | 🟢 **CERRADO** · `ventana-antes-del-move.md` |
| **N13** | **POSIX se queda a medias en las dos mitades**: sin detección equivalente a `os.replace` y sin barrido del candado. Emparejado con **N4**. **CERRADO el 28/08 por T como DECISIÓN MEDIDA, no como código:** la detección POSIX existe y cuesta **×182** (3 679,8 µs frente a 20,2), con 47 procesos denegados; y **barrer NO compensa** —en ext4 el ciclo es **×1,77 más LENTO** con barrido, **al revés que en Windows**, y abre la carrera del inodo desenlazado con dos dueños. Es la trampa 41 | 🟢 **CERRADO** |
| **N14** | **Un `taskkill /F` deja sin borrar un desechable de R18** por conversión en vuelo. **CERRADO el 28/08 por U, y era peor de lo que parecía: 978 desechables y 211,8 MiB en menos de cinco horas.** Barrido que sabe si el dueño vive sin preguntar por PID. **Dos fallos propios que encontró midiendo:** su primera versión habría borrado `filex-destinos` entero —los candados de toda la máquina— por compartir prefijo. Es la trampa 47 | 🟢 **CERRADO** |
| **N15** | **La huella NO ve las TABLAS de datos, solo el código que las lee.** `EXT_FAMILIA` movió el `punto 1` de **3 de las 53 salidas del patrón oro** y **no caducó ni una arista**: el componente `contrato` no se movió. **CERRADO el 28/08 por X — y la trampa 49 acertaba el HECHO y erraba la CAUSA:** las cinco tablas **sí** estaban en el cierre y tres **sí** caducaban; el agujero era de **3 de 5**, y la frontera era **el sitio del valor**, no el tipo (una tabla declarada vacía y poblada por un `for` de nivel superior se hashea vacía). Arreglado con **+196 líneas de cobertura y cero falsos positivos nuevos**, **y con el agujero gemelo del componente `motor`** que la trampa no miraba —`TIMEOUT_DENTRO` es el tope que corre dentro del contenedor—. **0 minutos de resondeo.** Es la trampa 58 | 🟢 **CERRADO** · `huella-y-tablas.md` |
| **N16** | **El punto ciego de A7**: por debajo de **48 kb/s** Opus rellena el canal mudo y la regla no dispara. **CERRADO el 28/08 por Y como MEDICIÓN, sin tocar `verificador.py`: la señal existe y no es la que proponía el pendiente.** La ventaja cruzada **no separa** (hueco −0,7983); **`corr(Rsal, Rent)` a secas sí, en las nueve tasas**, con meseta de umbral 0,008–0,13 donde atrapa **27 de 27 con 0 falsos de 45** (A7 hoy: 9 de 27). ~~Cuesta **183,1 ms** donde A7 ya gasta 364,0~~ — **el ahorro estaba MAL MEDIDO: los 364,0 son una orden que A7 no ejecuta.** En la misma tanda, A7 gasta **166,24 ms** y esta vía **231,85 = ×1,395**, no ×0,50. Es la trampa 79 | 🟢 **CERRADO, y su continuación N18 también** · `fidelidad-y-nucleo.md` |
| **N17** | ~~**`gpu-fase2.md` no es auditable**~~ — **la LECCIÓN está aplicada desde el 28/08**: G5 y S6 versionan el TEXTO del OCR (283 y 118 `.txt`), así que sus cifras sí se podrán recalcular. Lo de `gpu-fase2.md` no tiene arreglo —sus salidas ya no existen— y queda como aviso histórico | 🟢 **CERRADO por regla** · `metrica-ocr.md` §3 |
| **N18** | ~~**Aplicar la señal de N16 a `verificador.py`**~~ — **CERRADO el 28/08 por N3 como REFUTACIÓN.** Reproducida al centésimo (nueve tasas, 27/27, 0 falsos de 45) **y no sobrevive a su corpus**: sobre 264 celdas da **11 falsos de 152 legítimas, 6 irreductibles**, y las clases se solapan — Opus colapsa el estéreo a mono y se come un canal legítimamente flojo. **Hay una versión que sí separa y NO se puede escribir**: exige una FFT, y `filex` no tiene dependencias por decisión escrita. Lo que SÍ se aplica: el punto ciego **no es de bitrate, es de OPUS**, y A7 ya declara `cobertura = False`. Trampas 78, 79 y 80 | 🟢 **CERRADO** |
| **N19** | ~~**`DirectorioDeTrabajo.recoger` sigue siendo pública y pisa en silencio.**~~ **CERRADO el 28/08 por N3, y era peor: no solo pisaba un destino existente — pisaba el fichero que otro proceso tenía ABIERTO** (88 B → 20 B, sin excepción). Delega en `mover_a_destino`: la misma solución que el `move` | 🟢 **CERRADO** |
| **N20** | ~~**Un destino que es un DIRECTORIO se rechaza con el motivo equivocado.**~~ **CERRADO el 28/08 por N3, y la causa es limpia:** `os.replace` contra un directorio y contra un ocupante dan **el mismo `errno` 13 / `WinError` 5**, así que el motivo **mentía por construcción**. `DestinoNoEsFichero`, con el `isdir` **después** del fallo. **No abre canal R1/R4**: la ruta ya pasó el confinamiento | 🟢 **CERRADO** |
| **N21** | ~~**El criterio del hito 6 NO es alcanzable**~~ — **CERRADO el 28/08 por S6, y el motivo era peor que el número: su premisa MATABA EL PROCESO.** Con `faster-whisper` antes que RapidOCR, **10 de 10 con `rc=0xC0000409` sin excepción que capturar** —dos `cudnn64_9.dll` en `.venv-ai`—; invertido, 0 de 10. **«Dos modelos residentes» tenía que decir en cuántos PROCESOS.** Criterio nuevo en seis cláusulas, todas verificadas, con el tamaño máximo de entrada dentro. Trampa 82 | 🟢 **CERRADO** · `hito6-sidecar.md` §4 |
| **N22** | ~~**`.pdb` lo escriben DOS motores y son dos formatos distintos**~~ — **REFUTADO y CERRADO el 28/08 por N4: ni dos formatos ni dos escritores.** Es **un contenedor PalmDB**, y el motivo publicado era cierto **midiendo otra cosa**: **los 32 primeros bytes son el NOMBRE del fichero** y el censo de prefijos miraba ahí. El marcador está en el byte 60 (`vIMGView`, `TEXtREAd`, `PNRdPPrs`). **Aquí sí se gana detección**, al revés que `vips:mat`: los tres pasan a `evaluado` | 🟢 **CERRADO** · `bitrate-y-lock.md` |
| **N23** | ~~**`ocr_motor.py` sigue sin los dos testigos de ruido**~~ — **CERRADO el 28/08 por S6**, con tope propio de 20 s en el testigo y la resolución del reloj declarada | 🟢 **CERRADO** · `hito6-sidecar.md` |
| **N24** | ~~**El contrato no tiene regla de bitrate de VÍDEO**~~ — **CERRADO el 28/08 por N4, refutando la CAUSA: no faltaba la regla, faltaba el DATO.** Quitar el filtro de audio **no habría producido ni una comparación** —ni la sonda ni `ffprobe` publican `bitrate_bps` en vídeo, 4 contenedores de 4 con `None`—, **y tampoco en audio dentro de un contenedor**. Sobre lo único observable las clases **se solapan**, y el solape lo fabrica el audio; pero el audio solo SUMA, así que la regla es **asimétrica por desigualdad**: `BITRATE_VIDEO_TOL = 0.60`, **8 de 12 patológicas a `fallo`, 0 falsos sobre 72 y sobre las 53**. Trampas 86 y 87 | 🟢 **CERRADO** |
| **N25** | ~~**El lock de GPU no rodea al CODIFICADO**~~ — **CERRADO el 28/08 por N4, y la cifra del parche estaba mal por ×35.** `tomar()+soltar()` reproduce (1 341,1 µs, −4,5 %), pero `Lock.__enter__` llama a `guardia()` —`nvidia-smi`, 46,9 ms— y el `with` entero cuesta **47 482,6 µs**, contradiciendo a la §6.3 del propio informe que lo proponía. Aplicado con la guardia **fuera** de la reentrada. Trampa 88 | 🟢 **CERRADO** |
| **N26** | **La suma de VRAM sobreestima, pero el margen es DEL PERFIL**: 1,2 % con `distil` y **7,2 % con `large-v3`**. Presupuestar por suma es conservador, y cuánto de conservador **depende del modelo**, no del sistema | 🔴 **NUEVO** · `hito6-sidecar.md` |
| **N27** | **La recta de RapidOCR SUBESTIMA 339 MiB en el tramo medio** (r²=0,7581, residuo negativo en 2 de 5 puntos). No rompe nada porque el margen de 500 lo tapa por 161 — **y eso convierte el margen en la pieza que sostiene el modelo**: bajarlo deja una celda en descubierto. Trampa 85. **CERRADO el 02/09 por worker1 (`456b1ea`), verificado por el maestro** (`bench/vram-rapidocr.md`): **el fallo era la FORMA, no los coeficientes** — **dos de los cinco puntos ya estaban en la meseta**, así que la recta se ajustaba sobre puntos recortados. El recorte ata en **233 ppp = ~2,984 Mpx** (`Global.max_side_len: 2000`), la recta nueva sale de los **tres** puntos sin recortar (`428 + 235 × Mpx`) y el tope es el **máximo de tres medidas**, no la primera publicada. Seis pruebas de `test_hito6.py` actualizadas | 🟢 **CERRADO** · `bench/vram-rapidocr.md` |
| **N31** | **El coste de VRAM de RapidOCR NO depende sólo del array que ve la red: la meseta cuesta 300-400 MiB MÁS de lo que predice su propio tamaño — INFERIDO el 02/09, no medido directamente** (`bench/vram-rapidocr.md` §1.3, hallazgo no pedido de `N27`). Extrapolando la recta de los tres puntos sin recortar (`428 + 235 × Mpx`) a los 2,984 Mpx donde ata el recorte salen **1 129 MiB**; la meseta mide **1 456-1 533**. Si el único factor fuera el array final, deberían coincidir. La explicación candidata es el **PNG original antes de recortar** —decodificarlo y el `cv2.resize` piden sus propios buffers transitorios, y **el asignador no devuelve la memoria**— pero **es una inferencia, y el propio informe se niega a llamarla medida**: cerrarla exige instrumentar el proceso de RapidOCR **fase a fase**, que es trabajo nuevo. Importa porque explica por qué "arreglar" el modelo tocando sólo el tamaño del array no funcionaría | 🔴 **NUEVO** · `bench/vram-rapidocr.md` §1.3 |
| **N28** | ✅ **CERRADO el 31/08 por worker2** (`bench/bitrate-por-pista.md`), **retirando su propio parche de la ronda anterior**. `-b:a` **no es cota superior por pista** —AAC pedido 8 kb/s entrega 15,6 y 17,0; desvíos de −54,79 % a **+112,62 %**—, así que la resta puede **sobreestimar** el vídeo. Queda **media regla, y es la demostrable**: lado bajo `fallo` porque el contenedor es cota superior; lado alto `fallo` **solo sin audio**. Saldo con número: **8 de 12 atrapadas, 4 declaradas**, 0 falsos nuevos. Y la pregunta que faltaba, respondida: `stream=bit_rate` da `None` en MKV y WEBM, `-count_packets` solo cuenta, y **solo `-show_packets` + suma de `pkt_size` por `stream_index` es uniforme, y es cara**. ***Pedido no equivale a obtenido*** | 🟢 **CERRADO** |

---

| **N29** | **`filex.gpu.Lock._vivo()` pregunta por el dueño con `tasklist`, que sólo existe en Windows, así que FUERA de Windows todo dueño parece VIVO y un lock huérfano no se recupera jamás — MEDIDO el 02/09 por worker2** al clasificar C42. Es un fallo del producto, no de la prueba: rompía `test_gpu_lock` y una celda de `test_hito2`, y las descripciones viejas lo achacaban a *«no hay tarjeta»* y *«no hay ffmpeg con NVENC»* — **dos causas inventadas para un síntoma real**, que es la trampa 58. worker2 **no lo arregló y obró bien**: `filex/gpu.py` es del carril GPU. Enlaza con la trampa 90, que ya midió que el criterio *«¿vive el dueño?»* no tiene respuesta que cruce las dos máquinas — **pero aquélla hablaba de PID de Windows ausentes en WSL, y ésta de que la ORDEN no existe**. El mutex `Global\` no depende del PID y cuesta 18,1 µs. **CERRADO el 02/09 por worker1 (`58eeca4`), verificado por el maestro** (`bench/vivo-y-residuos.md`): con el arreglo el huérfano se recupera en **<5 ms**; con la versión vieja reimplantada, **nunca** — control positivo, no deducción— y sin regresión en Windows | 🟢 **CERRADO** · `bench/vivo-y-residuos.md` |
| **N30** | **Una prueba de carrera de la suite no distingue «la defensa aguantó» de «la carrera no llegó a abrirse», y bajo carga produce un ROJO FALSO — MEDIDO el 02/09 al verificar la ronda 5.** `test_cerrojo.py::test_sin_el_cerrojo_de_maquina_los_dos_procesos_devuelven_ok` apaga el cerrojo de máquina y **exige** que los dos procesos cuelen, para reproducir el fallo histórico del hito 7. Con la máquina en **23 procesos de Python y la CPU al 48 %** —la firma exacta de la trampa 101— los dos procesos **se serializan**, la ventana no se abre y el `assertTrue` cae; **aislada pasa 3 de 3 en ~2 s**. Ningún carril había tocado `filex/cerrojo.py` ni `filex/nucleo.py`. Es la **trampa 38 dentro de la suite**: *registra si la condición que dices reproducir SE DIO, no sólo el resultado*. **El arreglo no es relajar la aserción** (eso sería la trampa 65 al revés): es que la prueba **compruebe que la ventana se abrió** y se declare `skip` —no `fail`— cuando no se abre. **SEGUNDA OBSERVACIÓN el 02/09, y cambia el diagnóstico a mejor:** en la verificación de `C44`, con la máquina en el **mismo régimen** (23 procesos de Python, CPU al 54 %), la misma prueba **PASÓ** —444 passed, 0 failed—. Así que **no es «falla bajo carga»: es INTERMITENTE**, lo que la hace peor de detectar y descarta calibrar un umbral de carga como remedio. Refuerza el arreglo propuesto: la única señal fiable es **si la ventana se abrió**, que la prueba puede observar directamente en vez de inferirla | 🔴 **NUEVO, confirmado intermitente** · verificación de las rondas 5 y `C44` |

## 4. El reparto

**Dos criterios lo deciden:** la GPU es el recurso escaso (lock exclusivo, un agente a la vez) y **los documentos maestros son la sección crítica** — dos agentes editándolos a la vez se pisan.

### Oleada 1 — **EJECUTADA Y CERRADA (21/08, 03:30–09:40)**

| Agente | Trabajo | Informe | Estado |
|---|---|---|---|
| **D1 · Consolidación** | A1–A5 | `bench/consolidacion-21ago.md` | ✅ **CERRADO.** *(A5, el commit, sigue sin ejecutar)* |
| **G1 · Corpus d4** | B1 + B2 | `bench/corpus-d4.md` | ✅ **CERRADO.** d4 cumple; la asimetría **tenía otra causa** |
| **V1 · Verificador** | C1 + C2 | `bench/verificador-ghostscript.md` | ✅ **CERRADO.** `verificador.py`: 3 035 → **3 859 líneas** |

### Oleada 2 — **una de tres ejecutada**

| Agente | Trabajo | Escribe en | Recurso | Estado |
|---|---|---|---|---|
| **E1 · Aristas nominales** | C3 + C8 | `bench/aristas-nominales.md`, `bench/salidas-aristas/` | CPU + Docker | ✅ **CERRADO** |
| **G2 · Motores restantes** | B3 + B4 + B5, en ese orden y con timeout duro. **Un solo agente para los tres**, porque comparten el lock y el riesgo de tumbar CUDA | `bench/motores-restantes.md`, `bench/salidas-motores-restantes/` | **GPU (lock)** | 🔴 **sin lanzar** — **confirmado el 23/08**: `bench/motores-restantes.md` **no existe** en todo el árbol y marker/surya/MinerU no tienen una sola medida. ⚠️ **La etiqueta «G2» sí se usó el 22/08, pero para OTRO trabajo** (B17+B18+B14 → `bench/psm-y-rasterizador.md`). Un agente corrió; este encargo no |
| **M1 · Cabos MCP** | C4 + C5 | `bench/mcp-cabos-2.md`, `bench/salidas-mcp-cabos-2/` | CPU | ✅ **CERRADO el 21/08 a las 14:17** — C4 entero, C5 a medias. **Esta fila decía «sin lanzar» mientras las filas C4 y C5 de la §3, tres pantallas más arriba, lo daban por cerrado: el documento se contradecía a sí mismo.** ⚠️ **Y «M1» nombra a DOS agentes**: este y el de `k-por-motor.md` (B13, 22/08) |

> **Aviso para quien lance G2:** su prompt de §7.4 sigue siendo válido, **pero su premisa ha cambiado otra vez.** Decía que estos tres motores «se evalúan por coste de integración y por si aportan algo que la ruta actual no dé». **Ahora la ruta actual es mejor de lo que era**: con la corrección de normalización, **RapidOCR ONNX cubre el corpus entero (0,00 / 0,00 / 0,00 / 3,80 / 18,62 %), gana a PaddleOCR en cuatro de cinco filas y funciona en CPU.** El listón que marker, surya y MinerU tienen que superar **ha subido**, y el único hueco real es **`escaneado_d4`, donde nadie baja del 18,62 %**.

### Oleada 3 — **EJECUTADA Y CERRADA (21/08, 11:10–13:40)**

| Agente | Trabajo | Informe | Estado |
|---|---|---|---|
| **P1 · ppp y normalización** | B9 + B10 | `bench/ppp-y-normalizacion.md` | ✅ **CERRADO.** **Refuta las dos versiones de la regla de ppp**; B11 queda **redefinido** |
| **P2 · Invocación de aristas** | C15 + C17 + C13 | `bench/invocacion-aristas.md` | ✅ **CERRADO.** El 50,5 % baja a **41,0 %** |
| **P3 · Contrato y fidelidad** | C9 + C10 + C11 + C12 | `bench/contrato-quinto-punto.md` | ✅ **CERRADO.** **`P9` refutada**; el verificador queda en **4 185 líneas** |
| **D3 · Tercera consolidación** | A8 | `bench/consolidacion-3-21ago.md` | ✅ **CERRADO** |

*(Los tres corrieron en paralelo —P1 en GPU, P2 y P3 en CPU—, y **el testigo de proceso lo notó**: llegó a ×94,6 y a agotar 60 s en un `ffprobe -version`. **Las cifras absolutas de P3 no son comparables con las de V1**; las relativas dentro de cada tanda, sí.)*

### Oleada 4 — lo que abre esta tanda

**Prioridad alta, porque cambian diseño y no solo documentación:**

| # | Trabajo | Recurso |
|---|---|---|
| ~~**B13**~~ | ✅ **CERRADO el 22/08.** El `k` resultó ser del **par (motor, documento)**: interacción 76,7 %. Ver §3.B | — |
| **B11** | Llevar la corrección a `ocr_motor.py` **con su contenido nuevo**: cambiar a `PP-OCRv6 small` **y** añadir R6, declarando el saldo (7 mejor, 2 igual, 2 peor) | GPU |
| **C19 + C21** | El miembro descubierto de la familia (canal de audio silenciado hacia destino con pérdida) y el suelo duro de PSNR para V8 | CPU |
| **C20** | Validar el sustituto de `P9` fuera de Ghostscript — es lo único que separa una reparación buena de una alucinada | CPU |
| ~~**A5**~~ | ~~**Ejecutar el commit.** Siete agentes sin versionar~~ — **HECHO**: `dcd4057` el 22/08 y `13181f6` el 27/08 | — |

**Prioridad normal:** B6 (NVENC en lote), B7 y B8 (heurística de degradación —que ahora tiene **una señal más**, C24—, y R1 fuera del caso simple), ~~B12~~, ~~B14~~, ~~B15~~, B16, C6, C7, ~~C14~~, C16, C18, C22–C25. **Sin lanzar todavía: solo G2 (B3+B4+B5); M1 cerró el 21/08 a las 14:17.**

### Oleada 5 — **EJECUTADA Y CERRADA (22/08)** · *no estaba registrada aquí hasta el 23/08*

| Agente | Trabajo | Informe | Estado |
|---|---|---|---|
| **M1 (el segundo)** | B13 | `bench/k-por-motor.md` | ✅ **CERRADO.** El `k` es del **par (motor, documento)**: interacción 76,7 % |
| **G2 (la etiqueta, no el encargo)** | B17 + B18 + B14 | `bench/psm-y-rasterizador.md` | ✅ **CERRADO.** El `--psm` vale **42,78 puntos** y no es separable del `k` |
| **G3** | B19 + B15 + B12 | `bench/corpus-d5.md` | ✅ **CERRADO.** El fallo aritmético de la regla de ppp: **16,78 puntos** |
| **F1** | C14 | `bench/firmas-contrato.md` | ✅ **CERRADO,** con la conclusión invertida: **90 de 381 formatos no tienen marcador** |
| **K2** | Hito 3 | `bench/hito3-mudanza.md` | ✅ **CERRADO.** Y **refuta dos cifras de F1** → C31, C32 |
| **K3** | Hito 4 | `bench/hito4-mcp.md` | ✅ **CERRADO** con **dos criterios incumplidos y medidos** → C33, C36 |
| **K1** | Hito 5 | `bench/hito5-documental.md` | ✅ **CERRADO** por `filex-c13`, **no por Gotenberg** → C35 |
| **S1 · S2 · S3** | Sondeo de aristas | `sondeo-imagemagick.md`, `sondeo-ffmpeg.md`, `sondeo-documental.md` | ✅ **CERRADOS.** 132 + 23 aristas `sin_sondear` → ~0 |
| **D4 · Cuarta consolidación** | — | `bench/consolidacion-4-22ago.md` | ✅ **CERRADO.** Abre el **tercer sesgo, el de SEMILLA** |

### Oleada 6 — **EJECUTADA Y CERRADA (23/08)**

| Agente | Trabajo | Informe | Estado |
|---|---|---|---|
| **H7** | Hito 7 (watcher + API + R10) | `bench/hito7-superficies.md` | ✅ **CERRADO.** Abre la §3.N entera |
| **G4** | El `pHYs` fuera de Tesseract (**B25**) | `bench/phys-multimotor.md`, `bench/salidas-phys-multi/` | ✅ **CERRADO.** Los otros tres motores son **inmunes** y **ni siquiera consultan el metadato**: la regla del ráster es buena por determinismo, pero su beneficio es **de un motor de cuatro** |
| **L1** | **C26** + el barrido de veracidad de este documento | `bench/lock-de-maquina.md`, `bench/lib/harness.sh`, este fichero | ✅ **CERRADO** |
| **D1 (el segundo)** | **N3** + **N2**, las dos deudas de `filex/sondeo.py` | `bench/deuda-sondeo.md`, `filex/huella.py`, `pruebas/test_sondeo.py` | ✅ **CERRADO.** La arista tiene **seis** dimensiones; y N2 **resultó no existir** |

### Ronda 1 — **EJECUTADA Y CERRADA (31/08)** · *registrada al DESPACHARLA, no al cerrarla*

> **El reparto cambia de forma: se acabaron los turnos, ahora hay CARRILES.** De los 29
> abiertos, **12 necesitan la GPU** (los 10 de B más N26 y N27) y el lock es de uno a la
> vez. Si los dos workers se turnan la tarjeta hay que coordinar el lock en cada ronda — y
> **C39 acaba de demostrar que el lock no falla callándose: borra el del otro**. Con
> **worker1 siempre en GPU y worker2 siempre en CPU/Docker**, la contención no se gestiona:
> **no existe**. Es exclusión estructural en vez de cooperativa, que es la lección de las
> trampas 33 y 90. Y arrastra la mitad de la trampa 84 gratis: **cada carril POSEE unos
> módulos** —worker1 `filex/gpu.py`, `filex/sidecar.py`, `bench/lib/harness.sh`; worker2
> `filex/verificador.py`, `filex/motores.py`, `filex/api.py`, `filex/nucleo.py`— y nadie más
> los toca.

| Agente | Trabajo | Informe | Estado |
|---|---|---|---|
| **Ronda 0** (master) | Arrancar Docker y relanzar la suite | — | ✅ **CERRADA.** **420 passed · 2 skipped · 0 failed**, frente a 408/14/0 sin demonio y 414/8/0 con Python de WSL. **Las 12 que faltaban PASAN**, y es la primera vez que se ejecutan sobre Windows con demonio: no estaban rotas, **no se habían ejecutado nunca**. Corrige la trampa 94, que se quedaba corta — un recuento necesita **tres** declaraciones: intérprete, entorno y qué quedó fuera |
| **worker1** | **C38 + C39** | `bench/lock-desde-python.md`, `filex/gpu.py`, `bench/lib/harness.sh` | ✅ **CERRADO en dos intentos.** El primero se **sacó de `main`**: rompía 5 pruebas, y las 5 tenían razón —tomaba el lock de un dueño vivo Y no recogía el huérfano, que son los dos modos de C39 a la vez—. Causa: la exclusión solo en el mutex deja **dos poblaciones que no se ven**. Arreglado tomando **los dos, fichero primero**. Su sesión murió sin responder y el trabajo se verificó **ejecutando las pruebas, no leyendo el resumen** |
| **worker2** | **N28** | `bench/bitrate-por-pista.md`, `filex/verificador.py`, `filex/motores.py` | ✅ **CERRADO.** La resta se **retira**: `-b:a` no es cota superior por pista. Saldo dicho con número: **8 de 12 atrapadas por el lado bajo, 4 declaradas**. Y trae lo que faltaba —¿existe la magnitud?—: `stream=bit_rate` da `None` en MKV y WEBM, `-count_packets` sólo cuenta, y **sólo `-show_packets` + suma de `pkt_size` por `stream_index` es uniforme, y es cara**. La regla que queda escrita: ***pedido no equivale a obtenido*** |
| **worker2** (2ª y 3ª pasada) | **C25**, residuo | ídem | ✅ **MITAD CERRADA, con dos autocorrecciones suyas.** El «bloqueo» era falso (**trampa 95**); reejecutadas las 15 con el pool reconstruido, **0/15 buenas**; y el `0/15` se convirtió en el número que sirve: **5 `no_aplica`, 9 candidatas, 1 de codificador** |

> #### El espejo de la trampa 89, y es más caro que el original
>
> worker2 declaró *«BLOQUEO MEDIDO: sus semillas P2 fueron podadas… sin entradas no se puede
> cumplir la reejecución honesta»*. **Lo refuta el propio repositorio:**
> `bench/salidas-invocacion/pool_indice.json` está **versionado**, 20 187 B, con las **112
> entradas** del pool —`aptx`, `msbc`, `tta` y `mjpeg` incluidas—; `_p2_semillas.py` está
> versionado; y el `MANIFIESTO.md` lo dice **en dos sitios**:
> `| pool/ | 112 | 225 069 057 | python _p2_semillas.py |`.
>
> Las semillas **no se perdieron: se podaron a propósito**, que es literalmente la regla §6
> —*borra los bytes, deja la orden que los reproduce*—. Miró el disco y no el manifiesto.
>
> **La trampa 89 decía: antes de creerte un rojo, mira si el activo que juzgas está
> versionado. Falta la otra mitad, y es peor: antes de creerte un BLOQUEO, mira si el activo
> que falta está PODADO CON SU ORDEN.** Un rojo se investiga; un bloqueo se acepta. Esa
> asimetría es lo que lo hace más caro, porque la disciplina de §6 —que es buena— fabrica
> exactamente este falso muro cada vez que alguien mira el disco antes que el manifiesto.

### Ronda 2 — **EJECUTADA Y CERRADA (01/09)** · *registrada AL CERRARLA, incumpliendo la regla de la ronda 1*

> **Esta cabecera es el defecto que este barrido vino a arreglar.** La ronda 1 dejó escrito
> *«registrada al DESPACHARLA, no al cerrarla»*, y la ronda 2 se despachó, se ejecutó y se
> cerró **sin aparecer en esta sección ni una vez**. Durante un día el documento que gobierna
> el reparto no sabía que había dos agentes trabajando. Es la **trampa 44** dentro del
> fichero que ya la documenta sobre sí mismo: un recuento honesto con una nota falsa al lado
> —y aquí ni siquiera había nota.

| Agente | Trabajo | Informe | Estado |
|---|---|---|---|
| **worker1** (carril GPU) | **B21 + B22** — el suelo de 100 ppp y la forma de la curva | `bench/suelo-ppp.md`, `bench/salidas-suelo-ppp/` | 🟡 **MITAD CERRADA.** 336 celdas deterministas, `rc=0` en todas. **El suelo es DEL MOTOR**: RapidOCR sale 11 peor y 0 mejor; EasyOCR y docling+R6, 7 mejor y 0 peor. **Publica la tabla por configuración, nunca la media.** Pendiente declarado por él mismo: **Tesseract `psm 3` y `psm 11` no entran en estas 336 celdas** |
| **worker2** (carril CPU/Docker) | **C35 + C36** | `bench/gotenberg-y-mcp.md` | 🟡 **LAS DOS A MEDIAS** ~~🟢 CERRADO~~ — **mi registro fue demasiado generoso y lo corrige el propio informe**, que declara un `PENDIENTE` en C35 (latencia n≥9) y deja **siete** de §13 vivos en C36. La autocorrección de worker2 es más fuerte de lo que yo escribí: no es que «de los ocho, dos estaban cerrados», es que **son NUEVE**, y el enunciado de la fila llevaba mal el recuento |

> #### Lo que costó, y no fue la medición
>
> **Cuatro configuraciones se lanzaron con el entorno contaminado y dos fallaron EN SILENCIO**
> —proceso `rc=0`, 48 celdas cada una con `rc=[1]*9`, texto vacío y CER 100 %—, pasaron por
> buenas **dos horas** y llegaron a un informe de estado. **Yo propuse además declararlas
> `no_aplica`**, lo que habría enterrado un fallo total bajo una categoría legítima del
> proyecto; **lo paró worker1, negándose a publicar el saldo con ellas dentro**. Es la
> **trampa 99**. Causa raíz, con control positivo: `expanduser('~')` en Windows usa
> `USERPROFILE`, no `HOME`.
>
> Y el reparto perdió **40 minutos medidos** en un solo relevo porque el bucle que lanza la
> configuración siguiente vivía dentro del turno del agente: **desprender salva la TAREA, no
> la SECUENCIA** (trampa 100). La forma correcta es un **conductor único, desprendido**, que
> recorra las configuraciones en serie reiniciando el proceso entre ellas.

---

### Ronda 3 — **EJECUTADA Y CERRADA (01/09)** · *registrada AL DESPACHARLA, que es la regla que la ronda 2 incumplió*

> **Dos encargos, no cuatro.** La ronda 2 perdió **40 minutos medidos** en un solo relevo
> (trampa 100) y esta ronda estrena dos variables nuevas: el **flujo de PR con CI**, y unos
> workers que **acaban de nacer como `claude` con el contexto vacío** —los de `codex`
> conocían el proyecto; éstos no—, así que el encargo tiene que traer el contexto dentro.
> Con dos veo si el flujo funciona antes de multiplicarlo.
>
> Y una condición previa que no había en rondas anteriores: **los *worktrees* iban 12 y 15
> commits por detrás de `main`**, que es donde vive la CI que va a juzgar sus PRs.

| Agente | Trabajo | Informe | Estado |
|---|---|---|---|
| **worker1** (carril GPU) | **B21 + B22** — Tesseract `psm 3` y `psm 11`, y luego el residuo de B22: el mecanismo de los picos | `bench/psm-suelo-ppp.md`, `bench/cajas-rapidocr.md` | 🟢 **LAS DOS CERRADAS.** El suelo de 100 ppp **le invierte el signo a Tesseract** —hasta 20 puntos de ganancia en el documento de 60 ppp nativos—, y con las nueve configuraciones el saldo es **16/15/5**, un empate que sigue siendo engañoso. Y los picos de RapidOCR **son del RECONOCEDOR, no del detector**: las 12 cajas están en las 12 celdas con área estable, y lo que se hunde es **una línea de 7 pt**, de ~96 % a 27–46 % de similitud. **Refuta la hipótesis con la que el master abrió el encargo** |
| **worker2** (carril CPU/Docker) | **Saneo de veracidad del inventario** + **C41** | `bench/saneo-inventario.md` | 🟢 **CERRADO.** Las 111 filas contra su cita. **C28 era el peor tipo de fila: VERDE y contradicha por su propia evidencia** —daba por cerrado «FATE cierra 15» y el informe dice literalmente *«no lo he descargado»*—; **C32** pedía una arbitración que ya existía en C31/C37; **C22** llevaba dos días con informe y en rojo. Los 17 manifiestos escritos y la **deuda a 0**. *(Y el saneo cometió el defecto que buscaba: hizo C41 entera y dejó su propia fila abierta.)* |

> #### Por qué el saneo va primero, y por qué no lo hace la CI
>
> `ci/integridad.py` comprueba que **cada fila tenga un emoji**; no comprueba que **el emoji
> sea verdad**. Es el mismo límite que el barrido del 23/08 dejó escrito, y es por diseño:
> la segunda revisión sólo se hace **contra el código, el informe y el `git log`**.
>
> Y hacía falta: preparando este reparto encontré **tres filas obsoletas en una tarde** —
> `C22` tiene informe desde el 30/08 y seguía 🔴; `C35` y `C36` las movió la ronda 2 y
> seguían 🔴 un día después, **y mi propio registro decía «🟢 CERRADO» cuando el informe
> declara pendientes en las dos**. Un inventario cuyo color no se puede creer no sirve para
> planificar, que es su única función.

---

### Ronda 4 — **EJECUTADA Y CERRADA (01–02/09)** · *registrada al despacharla*

> **Los encargos de GPU van en RACIMO porque interactúan.** `B23`, `B24` y `B16` no son tres
> tareas que quepan en un agente: son **una sola rejilla**. El `k` está ajustado sobre tres
> documentos que comparten generador y geometría (B23), el `--oem` no se ha tocado nunca y la
> tabla de Tesseract habría que rehacerla con Ghostscript (B24), y B16 son los dos acantilados
> sin puntos intermedios. Separarlos obliga a repetir el barrido entero.
>
> Y esta ronda estrena el flujo decidido en el PR #8: **el worker entrega la rama commiteada y
> el maestro empuja y abre el PR**, porque `gh auth` vive en el `home` de cada agente y los
> workers no tienen credenciales — medido cuando worker2 terminó su encargo y no pudo
> entregarlo.

| Agente | Trabajo | Informe | Estado |
|---|---|---|---|
| **worker1** (carril GPU) | **B23 + B24 + B16** | `bench/k-oem-acantilados.md` | 🟢 **B16 y B24 CERRADAS, B23 a medias.** 234 celdas. **B16 refuta su propio enunciado**: no hay acantilado, hay un **peine** —2,53 / 73,42 / 25,32 / 6,33 / **0,00** / 75,95 en `k` consecutivos, 13 de 13 deterministas—, y el 75,95 % que se repite exacto es **colapso de modo verificado LEYENDO EL TEXTO**: las celdas devuelven sólo la primera línea, 60 caracteres de 79 = 75,95 % exacto. **B24 cierra sin trabajo pendiente**: `oem 0` y `oem 2` fallan 16 de 16 porque el `spa.traineddata` de PDFgear es LSTM-only, `oem 1` y `oem 3` dan CER idéntico letra por letra, los once `--psm` se reducen a **tres comportamientos**, y **Ghostscript ≡ ImageMagick en 10 de 10** con el pHYs declarado — la tabla de `k` **no** hay que rehacerla |
| **worker2** (carril CPU/Docker) | **C42 + C27 + C20** | `bench/ci-y-contrato.md` | 🟢 **C27 cerrada, C42 avanzada, C20 declarada intacta.** **7/17 → 14/17** módulos limpios. Los diez rotos eran **dos mecanismos, no diez causas** —sin motores externos, y el corpus como punteros de LFS— más dos no previstos: **`_vivo()` pregunta con `tasklist`** (→ `N29`, fallo de PRODUCTO que **no tocó porque es del otro carril**) y un `docker run` bajando **5,7 GB** en cada ejecución. Y el hallazgo que da la **trampa 107**: un `skipUnless` que nombra su causa y **no protege nada**, porque `os.path.exists()` es `True` para un puntero de LFS. **No sobrescribió `ci/linux-apto.json`** —su contenedor no es el runner— y dejó `test_watcher_n` **sin resolver en vez de forzarlo** |

---

### Ronda 5 — **EJECUTADA, VERIFICADA Y CERRADA (02/09)**, sobre *worktrees* de Orca · *registrada al despacharla*

> **Verificación del maestro, con las cuatro declaraciones que exigen las trampas 94 y 101.**
> **Intérprete:** `.venv-mcp-filex` — Python **3.11.9, win32**. **Entorno:** Docker **levantado**
> (5 contenedores, `filex-convertx` y `filex-snapotter` incluidos). **Qué quedó fuera:** 2 saltadas,
> las dos honestas y declaradas —falta el ráster de `preparar_h6.py`, y la otra pide
> `FILEX_PRUEBAS_SIDECAR=1` y la tarjeta—. **Estado de la máquina:** **23 procesos de Python y CPU
> al 48 %**, GPU en 3 282 de 12 288 MiB (la base del escritorio, sin intruso).
>
> Sobre el árbol con **los dos carriles fusionados** —que es la combinación que ningún worker había
> probado—: **443 passed · 1 failed · 2 skipped · 121 subtests** en 188,42 s, más `ci/integridad.py`
> en verde (9 de 9, 73 informes, 31 citas vivas y 0 muertas). **El único rojo no es de la ronda: es
> `N30`**, abierto abajo — una prueba de carrera que bajo carga no puede abrir su propia ventana.
> Ningún carril había tocado su código, y aislada pasa 3 de 3.
>
> **Y la propiedad de módulos aguantó entera:** worker2 movió `filex/huella.py` y `filex/sondeo.py`,
> worker1 `filex/gpu.py`, **cero solape**, y **ninguno de los dos escribió en este documento**.

> **Cambia la infraestructura, no la forma.** CCB queda desmontado —directorio `.ccb/` (651 MB),
> los dos *workspaces*, once ramas locales, dos remotas y su subárbol de estado en WSL (266 MB)— y
> los dos carriles pasan a *worktrees* de Orca con **Claude Sonnet 5**. Lo que NO cambia: worker1
> siempre GPU, worker2 siempre CPU/Docker, y **cada carril posee sus módulos**.
>
> **Y hay un coste nuevo que el encargo tiene que llevar dentro.** Los *worktrees* de Orca viven en
> `C:\Users\krato\orca\workspaces\FileX\`, mientras los venvs —`.venv-ai`, `.venv-paddle`,
> `.venv-marker`, `.venv-mcp-md`, `.venv-mcp-filex`— siguen en `D:\Work\research\FileX\` y **no
> viajan: en el *worktree* hay CERO**. Un conductor que apunte a `$ROOT/.venv-*` da `rc=127` en las
> cuatro configuraciones a la vez, que es exactamente la tanda que costó la **trampa 100**. **Ruta
> absoluta en el encargo, o no hay encargo.** Y por lo mismo, una cifra absoluta medida desde `C:`
> **no es comparable** con las históricas: ahora cambia el volumen, no sólo la tanda.

**Cuatro decisiones tomadas el 02/09 — es lo que redefine esta ronda y las cinco siguientes:**

| | Decisión | Consecuencia |
|---|---|---|
| **`C43`** | **Declarar el intérprete de sellado y negarse a comparar** entre versiones distintas | No caduca ninguna de las 215 aristas. Es el encargo de worker2 en esta ronda |
| **`B3`/`B4`/`B5`** | **Sólo marker se mide**; surya y MinerU se **cierran** con su motivo escrito | El carril GPU se acaba en la ronda 9. `.venv-marker` (1 205 MB) sale de la lista protegida al cerrar B3 |
| **`C16`/`C28`** | **Corpus FATE bajado**: 2 529 ficheros, 1 345 840 190 B, en `D:\Work\research\fate-suite\` (fuera del repositorio, por §6) | Deja de ser bloqueo. **Pero compra menos de lo que parecía**: `firmas-cierre.md` §4.4 ya midió que cierra **15 de 56** en C28, *«y ni siquiera bien»* —FATE es corpus para DECODIFICAR y el censo necesita una muestra ESCRITA—. Para `C16` sí es la vía |
| **Runner** | **Autoalojado, con aprobación manual** para PRs de terceros | Fila nueva **`C44`**, carril GPU, y **después de `N29`**: el runner es un **tercer actor sobre el lock de la tarjeta**, y hoy el lock no excluye a todo el mundo (24 de 25 arneses toman el fichero, no el mutex) |

| Agente | Trabajo | Informe | Estado |
|---|---|---|---|
| **worker1** (carril GPU) · `edicius2002/filex-gpu` | **N29 + B23 (resto)** — el `_vivo()` que sólo sabe preguntar con `tasklist`, y las 4 configuraciones que la rejilla reducida no cubrió | `bench/vivo-y-residuos.md` | 🟢 **VERIFICADA Y CERRADA (`58eeca4`).** DECLARA: huérfano recuperado en **<5 ms** con el arreglo y **nunca** con la versión vieja reimplantada; **112 celdas** en las 4 configuraciones que faltaban del racimo de 9, **0 fallos, 0 no deterministas, 0 celdas a CER 100 %**; y un hallazgo que no se esperaba — **los dos Docling tienen el arrepentimiento MÁXIMO del racimo entero (8,4-8,8 pt)**, y no por el «peine» ya conocido de RapidOCR sino por degradar sistemáticamente en el documento más pequeño. Suite: **434 passed · 0 failed · 3 skipped** |
| **worker2** (carril CPU/Docker) · `edicius2002/filex-cpu` | **C43 + C42 (resto)** — sellar el intérprete y negarse a comparar; la causa sin reproducir y la promoción en el runner real | `bench/huella-y-runner.md` | 🟢 **VERIFICADA Y CERRADA (`42f090d`).** DECLARA: `C43` cerrada —ningún motor caducado ni no comparable— con línea base **medida antes de tocar nada** (422 passed · 3 skipped · 1 failed que **pasa aislado**, atribuido a contención y declarado *no es mío ni de esta ronda*). `C42` **avanzada y no cerrable**: cuarto intento de reproducir `test_watcher_n`, ahora sobre **ext4 genuino de WSL2** —que ninguno de los tres previos había probado—, sigue sin reproducirse, **lo documenta y para**. **Y trae el dato que el proyecto no tenía: esta sesión SÍ tiene credenciales de `gh`**, y lo declaró en el informe **en vez de usarlas** |

> **`C44` se adelanta a la ronda 6.** Su requisito previo era `N29`, que la ronda 5 acaba de cerrar,
> y su riesgo entero —el runner como **tercer actor sobre el lock de la tarjeta**— vive en el módulo
> que worker1 tiene recién reescrito. Además **no toca la GPU**, así que deja la máquina libre para
> verificar la ronda 5 sin contención (trampa 101). **Alcance acotado al despacharlo:** el diseño de
> seguridad, los *workflows*, los cambios en `ci/` y la medición son del agente; **registrar el runner
> e instalar el servicio, y cambiar los ajustes del repositorio en GitHub, NO** — y eso importa más
> ahora que se sabe que **sí hay credenciales de `gh`** en las sesiones de los workers.
>
> **Por qué estas cuatro y no otras: son el instrumento que juzga a las demás.** Hasta que `N29`
> cierre, un lock huérfano no se recupera fuera de Windows —y los dos *worktrees* nuevos son justo
> otro sitio desde donde tomarlo—; hasta que `C43` cierre, la huella dice «caducado» donde debería
> decir «no comparable». Medir cualquier otra cosa antes es medir con el instrumento roto.

---

### Rondas 6 a 11 — **PLANIFICADAS, no despachadas**

> **24 filas encargadas · 2 cerradas por decisión (`B4`, `B5`) · 2 que siguen bloqueadas
> (`C6` clave de API, `C7` datos de demanda) · 1 nueva (`C44`).** El plan está limitado por el
> **carril CPU, no por la GPU**: 14 encargos contra 10. Por eso la ronda 11 va con un solo worker,
> y se dice en vez de disimularlo.

| Ronda | worker1 · GPU | worker2 · CPU/Docker | Qué la une |
|---|---|---|---|
| **6** | **C44** · 🟢 **ENTREGADA Y VERIFICADA (`b582ceb`)** — diseño cerrado; registrar el runner es del usuario | **C31** + **C32** + **C40** · 🟡 **DESPACHADA el 02/09** — `bench/pcd-y-memoria.md` | El carril GPU **adelantó `C44`** (su requisito era `N29`) y el CPU recoge las tres filas de veracidad: un falso positivo VIVO, un falso negativo, una contradicción sin cerrar y 3 binarios |
| **7** | **N27** · 🟢 **ENTREGADA Y VERIFICADA (`456b1ea`)** | **C20** + **C23** + **el resondeo** · 🟢 **ENTREGADA Y VERIFICADA (`6e98c44`)** — 172 aristas resondeadas, **0 diferencias de veredicto** | El carril GPU **adelanta `N27`** porque es re-análisis de puntos ya medidos y **no toca la tarjeta**: worker2 va a correr la suite varias veces en la ronda 6 y medir encima es la trampa 101 |
| **8** | **B8** + **C18** · 🟡 **DESPACHADA el 02/09** — `bench/deskew-y-fidelidad.md` | **C24** + **C25** | Cuatro umbrales que no se cierran sin variar la entrada |
| **9** | **N26** + **B3** (marker, build CPU) + cerrar **B4**/**B5** | **N9** + **C5** | El otro margen que sostiene un presupuesto, y aquí sale `.venv-marker` de la lista protegida |
| **10** | **B20** + **B7** | **C35** + **C36** | Las dos mayores del carril CPU, y el residuo de B12 con la heurística ya calibrable contra `d4` |
| **11** | — | **C16** + **C28** (corpus FATE, ya en disco) | Convierte el 48,6 % estimado en número medido |

---

### Contención, en una frase

> **Nunca dos agentes de GPU a la vez.** Desde el 23/08 el lock **es de máquina** (`/tmp/filex-gpu.lock` = `%TEMP%`), se recupera solo si su dueño muere, y **`gpu_acquire` se niega a medir con la tarjeta ocupada por un tercero**. Pero **no obliga a cooperar a quien no lo toma**: por eso hay detección además de exclusión. **Nadie escribe en los maestros salvo el agente de consolidación.** **Un fichero de informe por agente**, sin excepciones.

---

## 5. Contexto compartido — pégalo en cualquier prompt

Este bloque **sustituye** al §2 de `AGENTES-PRUEBAS-PENDIENTES.md`, cuyas marcas de OCR están invalidadas.

```
ENTORNO VERIFICADO (21 ago 2026) — no lo recompruebes

Hardware
- RTX 3060, 12 288 MiB, compute 8.6, driver 572.61, CUDA 12.8
- 12 nucleos · Windows 10 Home 19045 · Docker 29.4.3 + WSL2 (Ubuntu)
- VRAM realmente disponible: ~8,7 GB. El escritorio ocupa ~2,5 GB de forma permanente.
  REMEDIDO el 23/08 (n=90 muestras a 1 s): ocupados 3 292 / 3 356 / 3 448 MiB
  (min/mediana/max) -> libres 8 996 / 8 932 / 8 840. El recorrido del propio
  escritorio es de 156 MiB. La UTILIZACION en reposo va de 14 a 57 %, asi que el
  testigo de "quieto por debajo del 10 %" marca SUCIA SIEMPRE: es estructural.
- Hay una SESION DE ESCRITORIO REMOTO activa a proposito. NO la cierres. Por eso
  casi todo sale etiquetado SUCIA: es estructural, no un fallo. NVENC y NVDEC libres.
- Python 3.11.9 · Node 22.23.2 · Go 1.22.5

Nativos disponibles
- ffmpeg/ffprobe N-121159 (gpl, x264, x265, cuda-llvm)
- magick 7.1.2-21 Q16-HDRI  (C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe)
- gswin64c 10.07
- tesseract.exe EXISTE en C:\Program Files\Tesseract-OCR\ pero NO esta en el PATH,
  y solo trae eng+osd.
- Ghostscript 10.07 lleva Tesseract y Leptonica COMPILADOS DENTRO de gsdll64.dll:
  habilita -sDEVICE=ocr, hocr y pdfocr8/24/32 sin binario externo. Pero SIN datos de
  idioma: falla con "Tesseract couldn't load any languages!" si no fijas TESSDATA_PREFIX.

NO instalados, y NO hay gestor de paquetes (ni winget, ni choco, ni scoop)
- vips, LibreOffice, Pandoc, qpdf, Calibre, Inkscape, DuckDB, poppler/pdfimages.
  Lo que falte va en contenedor, no instalado a mano.

Contenedores levantados
- SnapOtter :1349 (admin / <CONTRASENA-REDACTADA>) · ConvertX :3100 · Gotenberg :3200

Entornos virtuales — USARLOS PARA EJECUTAR SI; INSTALAR EN ELLOS, JAMAS
- .venv-ai/      torch 2.6.0+cu124 (CUDA True), docling 2.120.3, rapidocr 3.9.2,
                 easyocr 1.7.2, faster-whisper 1.2.1, surya-ocr 0.22.1,
                 onnxruntime-gpu 1.22.0, pypdfium2 5.13.0
- .venv-paddle/  paddleocr 3.7.0 + paddlepaddle-gpu 3.2.0, pypdfium2 5.13.0 (aislado)
- .venv-marker/  marker_pdf 2.0.0 + surya 0.22.1 + torch 2.13.0 SIN NVIDIA -> es CPU
- .venv-mcp-md/  markitdown 0.1.7 + markitdown-mcp (mcp~=1.8.0)
- .venv-mcp-sdk-18 / -1x / -2x, .venv-mcp-lite, .venv-mcp-vam, .venv-mm-ffmpeg,
  .venv-mm-vamcp  (arneses MCP; un venv por servidor, no coexisten)

Corpus (D:\Work\research\FileX\corpus\, en Git LFS)
- pdf/tipico_texto.pdf          CON capa de texto extraible (105 chars por txtwrite)
- pdf/patologico_escaneado.pdf  200 ppp nativos, sin capa de texto
- pdf/escaneado_d1.pdf          150 ppp nativos
- pdf/escaneado_d2.pdf          100 ppp nativos
- pdf/escaneado_d3.pdf          100 ppp nativos, JPEG q25, contraste muy bajo
- pdf/escaneado_d4.pdf          200 ppp nativos, CASTELLANO CON TILDES, 610 chars de
                                referencia, cuatro tamanos de letra (24/13/11/7 pt).
                                Variantes d4a/b/c/e/f + corpus/pdf/MANIFIESTO-d4.md.
                                d4c = escalon intermedio; d4e = cota superior (los 4
                                motores >70 %); d4f = 240 ppp. (bench/corpus-d4.md)
- video/, audio/, imagen/, datos/ para el resto

TEXTO DE REFERENCIA de los 4 escaneados d1-d3 y patologico (identico, SIN TILDES):
  "DOCUMENTO ESCANEADO"
  "Texto que solo existe como pixeles."
  "Debe recuperarse con OCR."
  -> 79 caracteres: cada caracter vale 1,27 puntos de CER. CON 79 CARACTERES NO PUEDE
     HABER GRADIENTE aunque el documento lo tenga. d4 usa 610 (0,16 puntos/caracter).

TABLA CANONICA DE OCR (bench/ocr-ppp-nativos.md §3 + bench/corpus-d4.md §4) — CER %
a ppp NATIVOS. SUSTITUYE a la de gpu-fase2.md §5, que medía un ×2 de interpolacion.
  Motor                              patologico   d1     d2      d3       d4
  PaddleOCR (PP-OCRv6 medium)          0,0 %     0,0 %   0,0 %    2,5 %   19,30 %
  Docling+RapidOCR torch (v6 small)    0,0 %     0,0 %   0,0 %   75,9 %   36,91 %
  RapidOCR (PP-OCRv5 mobile, ONNX)     1,3 %     0,0 %   0,0 %   77,2 %   41,78 %
  EasyOCR (CRAFT + latin_g2)           0,0 %     0,0 %  43,0 %   54,4 %   61,41 %
  gs -sDEVICE=ocr, spa (CPU, VRAM 0)   0,0 %     0,0 %   0,0 %  165,8 %      -
  RapidOCR v6 small + NORMALIZACION    0,0 %     0,0 %   0,0 %    3,80 %  18,62 %

  OJO 1: el "es" de PaddleOCR es una etiqueta VACIA en PP-OCRv6: lang="es" y lang="en"
         resuelven al mismo checkpoint y dan salida identica.
  OJO 2: gs en d3 no falla, ALUCINA (salida mas larga que la referencia, ruido puro).
         Los motores GPU que fallan devuelven POCO texto. Son modos de fallo distintos.
  OJO 3: la columna d4 es CER CON ACENTOS. La metrica ascii da 18,46/36,24/38,59/59,56.

LA CORRECCION MAS BARATA DEL PROYECTO (bench/corpus-d4.md §7, §10) — 72,2 puntos de CER
por seis numeros. RapidOCR 3.9.2 normaliza el PP-OCRv6 con mean=std=0,5 cuando el
inference.yml que Baidu distribuye CON el modelo declara ImageNet. Docling lo hereda.
  Det.mean = [0.485, 0.456, 0.406]   Det.thresh        = 0.2
  Det.std  = [0.229, 0.224, 0.225]   Det.box_thresh    = 0.45
                                     Det.unclip_ratio  = 1.4
                                     Det.max_candidates= 3000
  A/B: la normalizacion sola vale 64,6 puntos; el post-proceso solo, 0,0; los dos
  juntos reproducen la cifra de PaddleOCR EXACTAMENTE. El detector pasa de encontrar
  1 renglon de 3 a 3 de 3 en d3.

  VALIDADA el 21/08 a las 14:00 (ppp-y-normalizacion.md §3) — CON CONDICION:
  - Sobre PP-OCRv6 SMALL: 15 documentos, n=9, incluidas 4 rasterizaciones del patron
    oro -> 6 mejoras, 9 empates, 0 EMPEORAMIENTOS.
  - Sobre CUALQUIER OTRO checkpoint, NO LA APLIQUES A CIEGAS: 12 de 42 celdas del
    cribado empeoran. +42,50 puntos en PP-OCRv4 mobile sobre tipico_texto del patron
    oro (0,83 -> 43,33 %), un documento LIMPIO. +16,45 y +13,60 en PP-OCRv6 tiny.
    4 de 15 celdas peores en PP-OCRv5 mobile.
  - LOS OCHO inference.yml (PP-OCRv3 a v6) declaran ImageNet y rapidocr aplica 0,5 a
    los ocho: EL DESAJUSTE ES UNIVERSAL, EL DANO NO. Corregirlo es una HIPOTESIS, no
    una solucion: hay que medirlo checkpoint por checkpoint.
  - Docling: 7 de 7, 4 mejoras grandes, 0 regresiones, coste en tiempo NULO, via
    RapidOcrOptions.rapidocr_params (sin parchear el paquete).
  - COMPRUEBA QUE LLEGO: lee lector.text_det.mean / .std del objeto ya construido.
    "He puesto ImageNet" es una intencion, no un hecho.

REGLA DE PPP — NO HAY UNA GLOBAL: HAY UNA POR MOTOR (ppp-y-normalizacion.md §2, 14:00)
  Las DOS versiones anteriores estan REFUTADAS: ni clamp(nat,100,nat*1,4) ni
  clamp(nat,100,200). Y no vale ninguna de las tres unidades candidatas:

    ppp absolutos  -> d3 se rompe a 160; d4c/d4f/patologico NO se rompen a 400.
    factor fijo    -> PaddleOCR se rompe en d4 a x1,4, en d3 a x1,6, nunca en d4c/d4f.
    anchura en px  -> d3 se rompe a 1 035 px; d4c NO se rompe a 2 070 px.

  EL EXPERIMENTO QUE LO DECIDE (24 celdas): el MISMO JPEG de d4 reempaquetado en tres
  paginas de 100/200/400 ppp nativos da, A LOS MISMOS 200 ppp, CER de
  19,13 / 19,63 / 36,24 %; A LOS MISMOS PIXELES coincide A LA CENTESIMA.
  Los ppp no son una propiedad del documento: son px / (tamano que el PDF dice).

  REGLA VIGENTE — la elige el ADAPTADOR DEL MOTOR, no el orquestador:
    ppp_nativos = ancho_imagen_px / (ancho_pagina_pt / 72)     <- lo da el orquestador
    ppp_ocr     = max(min(ppp_nativos * 1.25, techo), 100) * k_motor
      ^^^ CORREGIDA EL 22/08 (corpus-d5.md §2): la forma anterior
          min(max(n,100), n*1,25) aplicaba el SUELO ANTES DEL TECHO, asi que para
          n <= 80 el techo caia por debajo de 100 y ANULABA el suelo (con 60 ppp
          ordenaba 75). Cuesta 16,78 puntos. Nadie lo vio en un año porque no habia
          un solo documento del corpus por debajo de 100 ppp.
          Y el SUELO de 100 es una suposicion sin medir: donde decide (80<n<100)
          EMPEORA (1,17 % a nativos vs 2,68 % a 100). Optimo real ~125 ppp, y eso
          es una hipotesis (B22), no un numero.
      k: PaddleOCR v6 medium 1,25 · RapidOCR v6 small+R6 1,00
         Docling+RapidOCR+R6 0,875 [CORREGIDO: el 1,00 costaba 7,72 puntos en d4c]
         EasyOCR 1,00 [se publica pero NO se recomienda]
         Tesseract 0,875 con psm 3 / 0,75 con psm 11
                   [CORREGIDO: el 1,50 de n=1 tenia arrepentimiento 176,31 vs 2,51]
      OJO: el k OPTIMO ES DEL PAR (motor, documento) — interaccion 76,7 % de la
      varianza de log2(k*), motor 23,2 %, documento 0,1 % (k-por-motor.md). Se fija
      por MINIMO ARREPENTIMIENTO sobre varios documentos, y SE PUBLICA EL
      ARREPENTIMIENTO, no el CER del documento donde se midio.
      Y UN k SIN SU --psm NO ES UN NUMERO (psm-y-rasterizador.md §3).
      Suelo: subir hacia 100 ppp, NUNCA mas de x1,25 (x1,4 solo es seguro en 4 de 8).
      Techo de CALIDAD: no existe global. Techo de COSTE: el tope interno del motor.
    Siete configuraciones sobre el MISMO documento dan optimos entre x0,50 y x1,80.
    Sobre d3 a x1,4: PaddleOCR sigue bien (3,80 %) y RapidOCR+R6 SE CAE (46,84 %).
    PENDIENTE: el valor de cada k sale de UN documento (escaneado_d4).

  TOPES INTERNOS, SONDEADOS EN EJECUCION (no deducidos):
    RapidOCR : Global.max_side_len=2000 (config.yaml:10). Sobre d4, de 233 ppp en
               adelante recibe el array IDENTICO. Su "tolerancia" es que no los ve.
    PaddleOCR: limit_side_len=64, limit_type=min. NO recorta. Ve los 2 588 px.
    (Leyendo el codigo de PaddleX se deduce lo contrario, y es FALSO para la ruta de
     paddleocr 3.7.0. Sondear en ejecucion, no deducir.)

  Y SI HAY UN LIMITE GLOBAL, PERO ES DE VRAM, NO DE PRECISION: barrer hasta 400 ppp
  con UNA pagina llevo a PaddleOCR a 11 942 y a EasyOCR a 12 037 de 12 288 MiB,
  SIN DAR ERROR. RapidOCR+R6 se queda en 4 439 (plano por encima de 233 ppp).

  docling: OcrOptions.scale vale 3,0 por defecto -> 216 ppp fijos. FIJALO SIEMPRE
  (scale = ppp_objetivo / 72) — pero "fijarlo A LOS PPP NATIVOS" era la parte
  equivocada: su defecto es indiferente en 4 de 5 escaneados y MEJOR en d3
  (58,23 % frente a 75,95 %, -17,72 puntos).

CPU vs GPU (corpus-d4.md §9) — DOS COSAS QUE HAY QUE SABER:
  1. "CPU y GPU dan salida identica caracter a caracter" es FALSO: 5 de 21 celdas
     difieren, y la CPU es mejor en dos y peor en tres. FIJA EL DISPOSITIVO.
  2. RapidOCR en CPU es solo x2,3-3,8 mas lento (0,32-1,18 s/pagina). PaddleOCR es
     x9,8-13,8 (hasta 5,42 s). Para RapidOCR la GPU es comodidad; para Paddle, requisito.
     En CPU, onnxruntime bate a torch en las 5 filas de docling, con CER IDENTICO.

VRAM POR MOTOR *Y POR RESOLUCION* (ocr-ppp-nativos.md §7.2):
  EasyOCR 5 026 MiB con imagen extraida -> 11 877 MiB a 300 ppp.
  PaddleOCR pico a 12 025 de 12 288 MiB a 600 ppp: a 263 MiB de agotar la tarjeta.
  Sobre la familia d4 a ppp nativos (200-240), coste propio: Docling+Rapid +1 484,
  RapidOCR ONNX +2 565, PaddleOCR +2 708, EasyOCR +4 430 MiB. Nada se acerca al peor
  caso PORQUE AQUI NO SE SOBREMUESTREA: aplicar R1 es lo que hace predecible el
  presupuesto de VRAM.

EVALUADOR DE OCR — bench/scripts/ocr_eval.py ES CIEGO A LAS TILDES (NFKD + descarte de
combinantes + [^a-z0-9 ]). Oculta 6,3 puntos de CER en `eng` sobre castellano y 155
caracteres de error en 28 celdas de d4. NO lo modifiques (es arnes compartido): copialo.
Hay dos copias con acentos ya escritas, en bench/salidas-corpus-d4/ocr_eval_d4.py y en
bench/salidas-verificador-gs/ocr_eval_tildes.py. Reporta SIEMPRE las dos lecturas.

Arnes de medicion: bench/lib/harness.sh
  gpu_acquire "<etiqueta>" / gpu_release   -> lock EXCLUSIVO de GPU (rc=2 si la
                                              tarjeta esta ocupada por un tercero)
  measure "etiqueta" N -- comando args...  -> mediana, rango, etiqueta limpia/SUCIA
  peak_vram comando args...                -> VRAM maxima durante la ejecucion
  gpu_libre_mib / gpu_censo_ajeno          -> nuevos el 23/08 (C26)
  Variables de entorno: GPU_LOCK, GPU_LOCK_DIR, GPU_LIBRE_MIN_MIB (6000),
  GPU_LIBRE_AVISO_MIB (7500), GPU_GUARD (abortar|avisar|esperar|ignorar),
  GPU_GUARD_ESPERA_MAX (900), GPU_MARCA_PROPIA (FileX).

EL LOCK DE GPU — CORREGIDO EL 23/08 (bench/lock-de-maquina.md, C26):
  ~~Era de PROYECTO: un fichero dentro de bench/, que excluia a otros agentes de FileX
  y NO VEIA NADA MAS.~~ AHORA:
  - EXCLUSION: el lock vive en /tmp/filex-gpu.lock, que en este Git Bash ES %TEMP%
    (cd /tmp && pwd -W -> C:/Users/krato/AppData/Local/Temp). Excluye tambien a otra
    copia o worktree de FileX. GPU_LOCK sigue siendo sobrescribible por entorno.
  - NO SE QUEDA HUERFANO: lleva dentro el winpid y el nombre de imagen del dueño.
    Un taskkill /F NO ejecuta el trap; el siguiente agente comprueba si el PID sigue
    vivo y lo recupera en 1 s en vez de esperar 900. (MEDIDO las dos cosas.)
  - DETECCION, que es la mitad que cierra el caso de ASR: un lock NO OBLIGA A COOPERAR
    a quien no lo toma. gpu_acquire mira la VRAM LIBRE y SE NIEGA A MEDIR por debajo de
    6 000 MiB (GPU_GUARD=abortar por defecto; avisar/esperar/ignorar para forzar).
    Linea base de esta maquina, n=90: 3 292 / 3 356 / 3 448 MiB ocupados.
  - LIMITE MEDIDO, no lo intentes: EN WDDM LA VRAM POR PID NO ES OBSERVABLE.
    nvidia-smi --query-compute-apps=used_memory -> [N/A] en los 30 procesos, y pmon
    dice "not supported in this configuration". "Mira los PID" solo da SOSPECHOSOS
    (el censo los ordena por RAM residente); nunca al culpable.
  - LO QUE SIGUE SIN RESOLVER: %TEMP% es POR USUARIO y no cruza a la VM de WSL2; y
    ningun .py del repositorio toma el lock (0 de 15 arneses que usan nvidia-smi).

DOS TESTIGOS DE RUIDO, NO UNO (verificador-ghostscript.md §4):
  El bucle monohilo de Python detecta DERIVA dentro de la tanda; es CIEGO a la
  contencion multinucleo. Etiqueto "limpia" una tanda que salio x6,8 sobre el mismo
  control (879 ms vs 129 ms). Anade un segundo testigo de LANZAMIENTO DE PROCESO:
      subprocess.run(["ffprobe","-v","quiet","-version"], stdin=DEVNULL, timeout=60)
  Calibracion en reposo: ffprobe -version 26,5-26,8 ms; gswin64c --version 121,7 ms.
  Y si lanzas powershell desde Git Bash, USA RUTA ABSOLUTA: el PATH unix heredado da
  FileNotFoundError [WinError 2] y la sonda devuelve -1 sin que te enteres.
  VAN TRES CASOS EN UN DIA: V1 (x6,8 etiquetado "limpia"), P1 (deriva 0,83 "sin
  deriva" mientras el de proceso media x7,18) y P3 (x94,6, con ffprobe -version
  AGOTANDO UN TIMEOUT DE 60 s y tumbando una tanda entera).
  PONLE TOPE AL PROPIO TESTIGO (20 s, devolviendo el tope y marcando SUCIA): un
  testigo que puede tumbar la medicion no es un testigo.
  Y LAS CIFRAS ABSOLUTAS DE TANDAS DISTINTAS NO SON COMPARABLES: la misma suite de
  fidelidad sobre los mismos 53 ficheros dio 46 332 ms en una sesion y 70 693 en otra.
  Mueve porcentajes; si mueves milisegundos, anota la salvedad.

EL VERIFICADOR, ESTADO AL 21/08 14:00 (contrato-quinto-punto.md):
  bench/scripts/verificador.py = 4 185 lineas cuando P3 cerro, biblioteca estandar y
  nada mas. OJO: al consolidar a las 14:10 el fichero tiene 4 567 lineas -> HAY OTRO
  AGENTE EDITANDOLO (hay un bench/salidas-firmas/ escribiendose y sin informe).
  No lo edites tu tambien, y no des por buena una cifra de lineas sin recontar.
  CONTRATO DE CINCO PUNTOS. verificar(...) acepta censo=; sin censo,
  cobertura["5_escritura"]=False y el veredicto baja a ok_parcial (49 de 53 salidas).
  EL PUNTO 5 NO ES VERIFICABLE A POSTERIORI: hay que censar el directorio de trabajo
  MIENTRAS el motor escribe. Con R18 cuesta +11,0 % del contrato; sin R18, sobre un
  directorio de 1 000 ficheros, x8,6 el contrato entero.
  15 REGLAS DE FIDELIDAD (se anadieron I9 y P9). CLI: --censo, --censar, --sin-v2.
  pedido["params"]["ocr"]=true -> P5 invierte la exigencia y P9 sube a fallo.
  P9 ESTA REFUTADA Y MARCADA NO FIABLE EN EL CODIGO: 8,3 % de sensibilidad sobre 32
  capas OCR reales, 36 % de falsos positivos sobre 14 legitimas. NO la uses como
  criterio. El sustituto medido (16/16) es el ACUERDO ENTRE DOS PASADAS DE OCR CON
  IDIOMAS DISTINTOS: bueno >=0,887, ruido <=0,700, umbral 0,80. Cuesta una segunda
  pasada de OCR (240-1 100 ms): es grupo C.
  --sin-v2 ahorra el 46,3 % de la suite sin cambiar ni un aviso.
  Y _gs_texto ya NO lee por tuberia: devolvia vacio 6 de 430 veces (0 de 430 por
  fichero temporal, al mismo coste) y contaba 107 caracteres en vez de 105.

"EN PROCESO SIEMPRE GANA" TIENE DOS REGIMENES (contrato-quinto-punto.md §4.3):
  CABECERAS -> en proceso, 145x a favor. Eso no cambia.
  PIXELES   -> magick gana. 138 ms frente a 2 834 del lector en proceso sobre
               1920x960 (x20,5). El punto de cruce esta en ~0,1 Mpx.
```

---

## 6. Reglas comunes — pégalas en todos los prompts

```
REGLAS DE TRABAJO (de CLAUDE.md, no negociables)

 1. UN FICHERO DE INFORME POR AGENTE. Dos agentes no escriben nunca el mismo fichero.
    No toques analysis/, ni los documentos maestros, ni informes de bench/ que no
    sean el tuyo. Los maestros (HUECOS.md, PLAN-ORQUESTADOR.md, RESULTADOS-MCP.md,
    ANALISIS-COMPLETO.md) los lleva OTRO agente en paralelo: NO los edites.
 2. NUNCA instales en .venv-ai, .venv-paddle, .venv-mcp-md ni .venv-marker.
    Venv nuevo por motor. Usarlos para ejecutar si; instalar en ellos, jamas.
 3. Verifica torch.cuda.is_available() en .venv-ai DESPUES de cada instalacion.
    `pip install surya-ocr` degrado torch de 2.6.0+cu124 a +cpu SIN UN SOLO ERROR.
    Si pasa a False, aborta esa via y documentalo.
 4. LOCK DE GPU OBLIGATORIO para todo lo que use la tarjeta: gpu_acquire/gpu_release.
    Solo un agente a la vez. Si el lock esta tomado, espera o trabaja en otra cosa.
 5. Medianas de n>=9, con etiqueta limpia/SUCIA. Con la sesion remota activa casi
    todo saldra SUCIA: es estructural. Calienta antes de medir (Windows Defender
    infla el primer arranque de un binario reciente: 41 -> 110 ms).
 6. TIMEOUTS EXPLICITOS EN TODO. Estos motores dejan huerfanos vivos 13 minutos.
    Surya se cuelga SIN EXCEPCION ni traza cuando no puede reservar VRAM: no esperes
    un error que no va a llegar.
 7. DOS INTENTOS POR PROBLEMA, luego documenta el error exacto y sigue.
    Nada de bucles de reintento.
 8. Marca cada afirmacion MEDIDO o PENDIENTE. No es opcional.
 9. Reporta los fallos como fallos. Un "no se pudo instalar" documentado mide el
    coste real de integracion, que es justo lo que hay que saber. Y refutar una
    conclusion propia es el resultado mas valioso que puedes traer.
10. No versiones salidas binarias regenerables. Borra las grandes al terminar y deja
    un MANIFIESTO.md con nombre, sha256, tamaño y la orden exacta que las reproduce.
11. No cierres la sesion de escritorio remoto, no toques .wslconfig, no edites el
    codigo de repos/, no toques ~/.claude.json (la config MCP es de proyecto, en
    D:\Work\research\FileX\.mcp.json), y no toques
    bench/salidas-referencia/referencia.json (es el patron oro: se lee, no se toca).
12. Los heredocs de shell se comen los backslashes en este entorno. Para generar JSON
    con rutas de Windows, escribe un script de Python y usa barras normales
    (D:/Work/...), que Python acepta.
```

---

## 7. Los prompts, listos para copiar

### 7.1 Agente D1 — Consolidación documental

> **Lánzalo primero y solo.** Mientras corra, ningún otro agente debe tocar los maestros. Es el único que no mide nada: reconcilia.

```
Proyecto FileX (D:\Work\research\FileX\), investigacion en español. Escribe en español.

TAREA: consolidar los cuatro informes nuevos del 21 de agosto en los documentos
maestros. Ningun otro agente esta tocando los maestros mientras tu corres.

SITUACION: HUECOS.md se reviso a las 00:32. Los cuatro informes siguientes son de las
02:44-03:07 y NO estan integrados en ningun sitio:
  - bench/verificador-fidelidad.md   (02:44)
  - bench/mcp-cabos-sueltos.md       (02:48)
  - bench/saturacion-herramientas.md (02:49)
  - bench/ocr-ppp-nativos.md         (03:07)

TAREAS CONCRETAS:

A1. Integrar los cuatro en HUECOS.md, RESULTADOS-MCP.md, PLAN-ORQUESTADOR.md y
    ANALISIS-COMPLETO.md. En concreto, y comprobandolo tu mismo contra los informes:
    - HUECOS.md §1 "Lo que sigue PENDIENTE": min(alfa) y las reglas de pixeles estan
      CERRADOS por verificador-fidelidad.md. min(alfa) en proceso cuesta 66,0 ms en el
      peor caso frente a los 734,6 ms de magick que este documento cita.
    - HUECOS.md §3 "Si 27 herramientas saturan la eleccion del modelo. SIGUE
      PENDIENTE": RESUELTO por saturacion-herramientas.md, y en contra de la hipotesis
      — 27 herramientas eligieron MEJOR que 8 (100%/98% frente a 85%/77%, n=540).
      El objetivo de 4 herramientas se sostiene SOLO por coste. Y aparece un riesgo
      nuevo en direccion contraria: un catalogo demasiado escueto produce fallos
      silenciosos (15-17%). Eso hace de la cobertura declarada de `convert` un
      requisito de seguridad.
    - HUECOS.md §5: la tabla de CER tachada se sustituye por la tabla canonica de
      ocr-ppp-nativos.md §3. Y el aviso de gpu-fase2.md hay que MATIZARLO en dos
      sentidos medidos: en d2 el artefacto es CERO para PaddleOCR y EasyOCR (las
      cifras de d2 publicadas eran correctas, incluido el 43,0 % de EasyOCR, que es
      real); y en d3 el artefacto es de UN SOLO motor — los 73,4 puntos son todos de
      PaddleOCR, mientras que para RapidOCR y Docling+RapidOCR torch la cifra vieja de
      200 ppp era su MEJOR resultado, no el peor.
    - PLAN-ORQUESTADOR.md §4.2 y §4.5: añadir la regla de ppp con techo ×1,4 y suelo
      100, el OcrOptions.scale explicito, y el presupuesto de VRAM por motor Y por
      resolucion. §5.3: la restriccion mcp>=2.0.0 sigue, pero Claude Code negocia
      2025-11-25, no 2026-07-28.
    - PLAN-ORQUESTADOR.md §4.6 (las 17 reglas): R8 necesita una EXCEPCION explicita
      para `inspect`, donde el staging cuesta 1,32× la operacion.

A2. Aplicar las 12 correcciones de la tabla de mcp-cabos-sueltos.md §6 y las de
    RESULTADOS-MCP.md §12 a analysis/00-mcp-patrones.md, que lleva dias marcado como
    "pendiente de las correcciones de §12". Las dos mas importantes:
    - las anotaciones readOnlyHint/destructiveHint NO llegan al modelo en Claude Code
      2.1.238: la advertencia va en la description y la defensa en el nucleo;
    - `-y` es necesario y NO suficiente contra el deadlock: con stdin heredado cuelga
      2/5 y con stdin=DEVNULL 0/5. Es un resultado causal medido A/B.

A3. RESULTADOS-MCP.md §13: de sus 6 pendientes, 5 estan cerrados por
    mcp-cabos-sueltos.md y saturacion-herramientas.md. Reescribe la tabla dejando solo
    lo realmente abierto, y añade lo que abrieron los informes nuevos
    (mcp-cabos-sueltos.md §7 tiene su propia lista).

A4. AGENTES-PRUEBAS-PENDIENTES.md cita como "marcas a batir" cifras de d2/d3 que estan
    invalidadas, y justifica los cuatro agentes con "en d3 fallaron los tres motores",
    que es falso. Marcalo como SUPERADO por este documento (ESTADO-Y-REPARTO.md) en su
    cabecera, sin reescribirlo entero.

A5. Preparar el commit. Hay 11 ficheros modificados y 8 sin versionar. Revisa que de
    bench/salidas-* debe entrar: el repositorio ya pago una vez 986 MB de pack, 99,9 %
    binario. Se versionan los .md, los scripts, los .json de resultados y los logs.
    NO ejecutes el commit: deja preparada la lista de que incluir y que excluir, y el
    mensaje, en tu informe.

REGLA DE ORO DE ESTA TAREA: no inventes ni una cifra. Cada numero que muevas a un
maestro tiene que estar literalmente en uno de los informes, y lo citas con su fichero
y su seccion. Si dos informes se contradicen, NO elijas: escribe la contradiccion y
señala los dos sitios. (Ya hay un precedente resuelto asi: la discrepancia
PP-OCRv5/PP-OCRv6 entre ocrmypdf.md y gpu-fase2.md, que ocr-ppp-nativos.md §6 cerro.)

ENTREGABLE: los maestros actualizados + un informe de lo que cambiaste en
bench/consolidacion-21ago.md, con una tabla "documento · seccion · que decia · que dice
ahora · fuente".

[PEGA AQUI EL BLOQUE DE CONTEXTO COMPARTIDO DE §5]
[PEGA AQUI LAS REGLAS COMUNES DE §6, salvo la nº 1, que para ti se invierte:
 TU eres el unico que edita los maestros]
```

### 7.2 Agente G1 — Corpus `escaneado_d4` y la asimetría de PaddleOCR · **GPU**

> El pendiente de mayor valor. Sin d4 no hay forma de medir margen de mejora en OCR.

```
Proyecto FileX (D:\Work\research\FileX\), investigacion en español. Escribe en español.

TAREA: construir un caso de OCR que mida MARGEN DE MEJORA, y aislar por que PaddleOCR
es el unico motor que resuelve escaneado_d3.

POR QUE: bench/ocr-ppp-nativos.md §8 demostro que el corpus de OCR de FileX ya no mide
dificultad, mide seleccion de motor. Tiene tres documentos que todos resuelven al 0,0 %
y uno (d3) que para PaddleOCR es un interruptor —2,5 % o 75,9 %, casi sin estados
intermedios— y para los otros tres una pared plana que no se mueve con nada.
Un caso dificil util es el que separa configuraciones DENTRO de un mismo motor.

TRAMPA CRITICA QUE TIENES QUE RESOLVER ANTES DE MEDIR NADA:
bench/scripts/ocr_eval.py normaliza con unicodedata.normalize("NFKD") + descarte de
combinantes + re.sub(r"[^a-z0-9 ]+", " "). Es decir: LA METRICA ACTUAL ES CIEGA A LAS
TILDES. Añadir un documento acentuado sin tocar el evaluador no mide nada. Necesitas un
evaluador nuevo, y como bench/scripts/ es compartido, COPIALO a tu directorio de
salidas en vez de modificar el original. Reporta las dos metricas —con y sin
normalizacion de acentos— para que las cifras nuevas sigan siendo comparables con las
296 celdas ya medidas.

TAREAS CONCRETAS:

FASE 1 — construir escaneado_d4.
  El generador existente es bench/scripts/gen_corpus_ocr.sh: renderiza una pagina
  maestra de 1941x2688 a 300 ppp con `magick -annotate` y luego aplica, en este orden,
  rotar -> reducir a los ppp objetivo -> desenfocar -> +level (bajar contraste) ->
  ruido gaussiano -> JPEG. Copialo a tu directorio y adaptalo; no lo modifiques in situ.
  El d4 tiene que cumplir las cuatro condiciones que ocr-ppp-nativos.md §8 dedujo:
   a) ppp nativos >= 200, para que no se pueda "arreglar" bajando la resolucion y para
      que la degradacion este en el papel, no en el muestreo;
   b) atacar al RECONOCEDOR, no al detector: en d3 los tres motores que fallan detectan
      el titular y pierden el cuerpo (frases_exactas 0-1 de 3, salida < 30 caracteres).
      Texto mas pequeño, mas variedad de caracteres;
   c) tildes y castellano de verdad. Ninguna medida de OCR de este proyecto las tiene;
   d) producir CER INTERMEDIOS en la meseta, no un interruptor. Si un motor da 0 % o
      76 % y nada en medio, el documento no mide una escala.
  Genera VARIAS candidatas (d4a, d4b, ...) barriendo los parametros de degradacion, y
  quedate con la que produzca el mejor gradiente. Documenta las descartadas y por que.
  El criterio de exito del corpus es explicito: al menos un motor entre 15 % y 60 % de
  CER, y al menos dos motores separados por >10 puntos.

FASE 2 — validar d4 contra los cuatro motores.
  PaddleOCR (.venv-paddle), RapidOCR ONNX, EasyOCR y Docling+RapidOCR backend="torch"
  (.venv-ai). Aplica la regla R1 de ppp (clamp con techo ×1,4) y fija OcrOptions.scale
  explicitamente en docling. Medianas n>=9, peak_vram por motor.

FASE 3 — la asimetria de PaddleOCR (B2).
  PaddleOCR (PP-OCRv6 medium, es) resuelve d3 con 2,5 %. Docling+RapidOCR torch corre
  PP-OCRv6 SMALL y falla con 75,9 %. Luego el limite NO es la generacion del backbone,
  que es lo que HUECOS.md daba por hecho y ocr-ppp-nativos.md §6 ya refuto en parte.
  Aisla la variable cruzando, sobre d3 y sobre d4, las tres candidatas:
    - tamaño de modelo (mobile / small / medium),
    - idioma del RECONOCEDOR,
    - idioma del DETECTOR.
  Esta es la pregunta de seleccion de motor que queda abierta, y con d4 acentuado el
  idioma pasa a ser una variable de verdad, no una etiqueta.

ENTREGABLE: UN UNICO informe en bench/corpus-d4.md, salidas en bench/salidas-corpus-d4/,
y los PDF nuevos en corpus/pdf/escaneado_d4*.pdf con su MANIFIESTO. NO toques los
escaneados existentes (d1, d2, d3, patologico): son la base de 296 celdas ya medidas.
El informe debe decir, con todas las letras, si el d4 cumple o no los cuatro criterios
—y si no los cumple, decirlo es el resultado, no un fracaso.

[PEGA AQUI EL BLOQUE DE CONTEXTO COMPARTIDO DE §5]
[PEGA AQUI LAS REGLAS COMUNES DE §6]
```

### 7.3 Agente V1 — Verificador: píxeles que faltan y OCR de Ghostscript · **CPU**

```
Proyecto FileX (D:\Work\research\FileX\), investigacion en español. Escribe en español.

TAREA: cerrar dos de los siete PENDIENTE de bench/verificador-fidelidad.md §7, y
ejercitar por primera vez el Tesseract embebido en Ghostscript.

ESTADO DE PARTIDA: bench/scripts/verificador.py son 3.035 lineas de biblioteca estandar
de Python y nada mas. Atrapa los 5 fallos documentados y da 0 falsos positivos sobre las
53 salidas del patron oro. Su CLI tiene --sondear, --alfa-min, --alfa, --fidelidad,
--solo-fidelidad, --lote, --motor {proceso,subproceso} y --json. Lee
bench/verificador-fidelidad.md ENTERO antes de tocar nada: explica el diseño, la
separacion contrato/fidelidad en tres grupos, y por que las excepciones existen.

TAREAS CONCRETAS:

C1. Ampliar la cobertura de min(alfa), que hoy devuelve "no evaluable" con su motivo en
    varios formatos. Por orden de coste estimado en el propio informe:
      - TIFF comprimido y GIF: exigen LZW/Deflate + predictor. Estimacion del informe:
        120-180 lineas. Abordable.
      - PNG entrelazado (Adam7): unas 40 lineas.
      - AVIF/HEIF: NO lo intentes. Exigiria un decodificador AV1 en proceso, y el
        informe ya lo declaro fuera de discusion. Que siga diciendo "no evaluable".
    Implementa tambien las reglas de fidelidad V2 (numero de fotogramas con
    -count_frames) y V5 (etiquetas de idioma y titulo), que el informe llama baratas.
    Mide el coste de cada una, mediana n>=9, y comprueba que los falsos positivos sobre
    las 53 salidas siguen siendo 0. Si suben, ESA es la noticia del informe.

C2. Ghostscript 10.07 lleva Tesseract y Leptonica compilados dentro de gsdll64.dll
    (122 apariciones de "tesseract", 9 de "leptonica"), lo que habilita -sDEVICE=ocr,
    hocr y pdfocr8/24/32 SIN invocar ningun binario externo. Nunca se ha ejercitado.
    Es la pieza que HUECOS.md §5 y bench/fidelidad-caminos.md llaman "arista de
    reparacion" y a la que atribuyen recuperar el 99,0 % del texto de un PDF ya
    rasterizado.
      - Hazlo funcionar. Hay .traineddata (eng, osd) en
        C:\Program Files\Tesseract-OCR\tessdata y hace falta fijar TESSDATA_PREFIX;
        sin eso falla con "Tesseract couldn't load any languages!".
      - Consigue y coloca spa.traineddata. Si no puedes descargarlo, DOCUMENTALO como
        coste de distribucion: FileX tendria que distribuir los datos de idioma.
      - Mide CER sobre los cuatro PDF escaneados del corpus, en eng y en spa, con el
        mismo bench/scripts/ocr_eval.py que usaron los demas motores, para que la cifra
        sea comparable con la tabla canonica de ocr-ppp-nativos.md §3.
      - AVISO: ese evaluador normaliza QUITANDO LOS ACENTOS. Para la comparabilidad con
        lo ya medido esta bien; para juzgar la calidad en castellano no sirve. Reporta
        las dos lecturas.
      - Mide tambien el coste en tiempo frente a los motores GPU, y verifica que el
        99,0 % de recuperacion de fidelidad-caminos.md se reproduce.
      - Aplica la regla R1 de ppp: NO sobremuestrees. d2 y d3 son de 100 ppp nativos.

ENTREGABLE: UN UNICO informe en bench/verificador-ghostscript.md, salidas en
bench/salidas-verificador-gs/, y las lineas nuevas en bench/scripts/verificador.py
(eres el unico agente que lo toca). Sin dependencias nuevas: el verificador es
biblioteca estandar y nada mas — si algo exige una dependencia, di que exige y no la
instales.

[PEGA AQUI EL BLOQUE DE CONTEXTO COMPARTIDO DE §5]
[PEGA AQUI LAS REGLAS COMUNES DE §6]
```

### 7.4 Agente G2 — Los tres motores restantes · **GPU** · *oleada 2*

```
Proyecto FileX (D:\Work\research\FileX\), investigacion en español. Escribe en español.

TAREA: cerrar los tres motores de IA que quedan sin medir: marker, surya y MinerU.
Un solo agente para los tres porque comparten el lock de GPU y el riesgo de tumbar CUDA.

AVISO PREVIO, Y ES EL QUE MAS TIEMPO TE AHORRA: la justificacion original de estos tres
agentes era "en la dificultad 3 fallaron los tres motores de OCR probados". ES FALSA.
Era un ×2 de interpolacion del arnes. PaddleOCR resuelve d3 con 2,5 % de CER.
Estos tres motores YA NO se evaluan como candidatos a resolver un caso que nadie
resuelve: se evaluan por COSTE DE INTEGRACION y por si aportan algo que la ruta actual
(Docling + RapidOCR backend="torch", que da 0,0 % en patologico, d1 y d2) no de.
Un "no se pudo instalar" documentado es un resultado valido y util.

ORDEN Y FICHAS:

B3. marker — el mas barato, y esta a medias.
    .venv-marker YA TIENE marker_pdf 2.0.0 + surya 0.22.1 instalados, y
    bench/salidas-marker/ contiene solo un pip-install.log del 20 de agosto: se instalo
    y no se midio nada.
    TRAMPA MEDIDA: ese venv tiene torch 2.13.0 y CERO paquetes nvidia-*. Es build CPU.
    Si mides asi, mides CPU y no lo sabras. Comprueba torch.cuda.is_available() DENTRO
    de .venv-marker antes de nada, y si es False decide y documenta: o reinstalas torch
    con CUDA en un venv NUEVO (no en .venv-marker), o mides CPU y lo declaras.
    Fase 1, casi gratis: convertir corpus/pdf/tipico_texto.pdf, que TIENE capa de texto.
    Segun su propio codigo (marker/builders/ocr.py:82, "clean pages already skip OCR
    entirely via pdftext") no debe arrancar ningun servidor de inferencia. Verificalo
    con nvidia-smi y con los logs. Si esto funciona, marker es utilizable y ya tienes la
    respuesta principal.
    Fase 2, solo si la 1 funciona: OCR real sobre los escaneados con
    inference_backend="llamacpp" (marker/models.py:13,43 lo expone como parametro
    publico). NO intentes el backend vLLM: reserva 10,4 GB de los ~8,7 libres y se
    cuelga sin excepcion.

B4. surya — reintento con backend y VRAM configurables.
    La fase 2 concluyo "surya no funciona" tras probar SOLO el backend por defecto.
    Tiene cuatro (vllm.py, llamacpp.py, openai_client.py, spawn.py) y settings.py es un
    BaseSettings de pydantic: todo es configurable por variable de entorno.
      Via A (preferible): SURYA_INFERENCE_BACKEND=llamacpp. Sin contenedor, sin reserva
        del 85 %. Necesita el binario llama-server.
      Via B: VLLM_GPU_MEMORY_UTILIZATION=0.5 -> 6,1 GB en vez de 10,4. Con los ~2,5 GB
        del escritorio suman 8,6 de 12: cabe, sin margen. Descarga de 10-20 GB.
      Via C, si las dos fallan: surya <=0.17.1 en venv aparte. Las anteriores a la 0.20
        son PyTorch en proceso, sin servidor.
    Venv NUEVO (.venv-surya). Su instalacion ya tumbo CUDA una vez en silencio:
    verifica .venv-ai despues. TIMEOUT en todo (300 s): surya se cuelga sin excepcion.

B5. MinerU con el extra [vlm] — NO [vllm], que es el pesado (vllm>=0.10.1.1).
    Su extra vlm pide torch>=2.6.0,<3: compatible con el torch instalado, no obliga a
    version nueva. Venv nuevo .venv-mineru. Licencia ya resuelta (Apache-2.0 con
    umbrales irrelevantes): no la investigues.
    Alternativa si pip da problemas: repos/ai-engines/MinerU/docker/global/compose.yaml,
    viable ahora que el NVIDIA Container Toolkit esta verificado.
    El dato decisivo es el TIEMPO DE CARGA EN FRIO frente a caliente: su pila de modelos
    es el motivo por el que se aplazo.

QUE DEBE CONTENER EL INFORME, para los tres y en el mismo formato:
 1. Que se instalo y cuanto ocupo (du -sh del venv, tamaño de los modelos).
 2. Si arranco o no, con el error EXACTO si no.
 3. Precision: CER y distancia de edicion contra el texto de referencia, para las
    4 variantes de dificultad, comparable con la tabla canonica de
    bench/ocr-ppp-nativos.md §3 (que es la buena; la de gpu-fase2.md §5 NO lo es).
    Aplica la regla R1 de ppp: d2 y d3 son de 100 ppp nativos, NO los sobremuestrees.
 4. Velocidad: mediana n>=9 con etiqueta limpia/SUCIA.
 5. VRAM de pico (peak_vram), por motor y por resolucion.
 6. Tiempo de carga en frio frente a caliente.
 7. Verificacion de que .venv-ai sigue con torch.cuda.is_available() == True.
 8. Veredicto: ¿entra en FileX, en que papel, y a que coste de integracion?

ENTREGABLE: UN UNICO informe en bench/motores-restantes.md, salidas en
bench/salidas-motores-restantes/.

[PEGA AQUI EL BLOQUE DE CONTEXTO COMPARTIDO DE §5]
[PEGA AQUI LAS REGLAS COMUNES DE §6]
```

### 7.5 Agente M1 — Los cabos que dejó abiertos `mcp-cabos-sueltos.md` · **CPU** · *oleada 2*

```
Proyecto FileX (D:\Work\research\FileX\), investigacion en español. Escribe en español.

TAREA: cerrar los pendientes que bench/mcp-cabos-sueltos.md §7 dejo abiertos.
Lee ese informe entero primero: su arnes esta en bench/salidas-mcp-cabos/ y es
reutilizable (cabo1_srv_2x.py, cabo2_roots.py, cabo1_escribir_mcpjson.py).

C4. Cuatro preguntas sobre el cliente real (Claude Code 2.1.238), todas medibles con el
    servidor de sonda que ya existe:
    a) Las 20 herramientas de video-audio-mcp que no se ejecutaron. La clasificacion por
       AST las cubre; la ejecucion no. Es exhaustividad, no duda sobre el mecanismo:
       6 de 6 representantes cuelgan con la salida preexistente y el mecanismo esta
       demostrado A/B (stdin heredado 2/5 vs stdin=DEVNULL 0/5). Confirmalo o refutalo.
    b) ¿Emite Claude Code notifications/roots/list_changed? Decide si FileX puede
       cachear los roots por sesion o tiene que preguntarlos cada vez.
    c) ¿Expone Claude Code recursos y prompts AL MODELO? Si no lo hace, declararlos es
       coste sin retorno. Ya se sabe que las anotaciones readOnlyHint/destructiveHint
       NO cruzan: solo llegan description e inputSchema.
    d) ¿Llegan las herramientas MCP DIFERIDAS de forma general? Cambiaria entero el
       modelo de coste de catalogo de RESULTADOS-MCP.md §4 y el multiplicador ×2,0-2,6
       de bench/saturacion-herramientas.md §3.6.

C5. Dos medidas de confinamiento:
    a) La carrera de SYMLINKS EN LINUX contra servers/filesystem. En Windows el 79 % de
       los intentos del atacante fallo por bloqueo de fichero, asi que la medida de
       Windows no concluye. Usa WSL2. Es una carrera distinta de la de lectura por un
       motor externo, que ya esta cerrada en cabo5_linux.json.
    b) El punto de cruce exacto entre `inspect` y el staging de R8. Aqui esta en
       ~90-100 MB y depende del disco: por debajo, copiar es despreciable; por encima,
       el staging cuesta 1,32× la operacion y R8 necesita su excepcion. Acota la curva.

REGLA ESPECIFICA E IMPORTANTE: .mcp.json es config SOLO DE PROYECTO. Si la tocas, haz
copia antes y restaurala al terminar, como hizo el informe anterior
(bench/salidas-mcp-cabos/mcp.json.bak). ~/.claude.json NO SE TOCA EN NINGUN MOMENTO.
Deja `git status` limpia respecto a .mcp.json.

ENTREGABLE: UN UNICO informe en bench/mcp-cabos-2.md, salidas en
bench/salidas-mcp-cabos-2/. NO escribas en bench/salidas-mcp-cabos/, que es del informe
anterior: leelo, no lo modifiques.

[PEGA AQUI EL BLOQUE DE CONTEXTO COMPARTIDO DE §5]
[PEGA AQUI LAS REGLAS COMUNES DE §6]
```

### 7.6 Agente E1 — Cuántas aristas declaradas son reales · **CPU + Docker** · *oleada 2*

```
Proyecto FileX (D:\Work\research\FileX\), investigacion en español. Escribe en español.

TAREA: medir que fraccion de las aristas de conversion DECLARADAS son nominales, es
decir, estan en la tabla del motor y no funcionan.

POR QUE ES LA MEDICION QUE CIERRA EL HUECO 2: analysis/00-matriz-formatos.md extrajo del
codigo de los 20 adaptadores de ConvertX 896 formatos de entrada y 503 de salida.
bench/fidelidad-caminos.md redujo el multiplicador del multi-salto de ×2,93 a ×1,93 con
los motores realmente instalados (138.501 aristas) y ejecuto 69 caminos. Y ya hay CUATRO
aristas declaradas refutadas por ejecucion: epub->pdf, txt->png, pdf->txt y mp4->pdf.
HUECOS.md §2 lo dice sin rodeos: "sondearlas todas es la medicion que cerraria el hueco
del todo". La tesis a contrastar es que UNA ARISTA DECLARADA POR EL CATALOGO DE UN MOTOR
NO ES UNA ARISTA.

C3. Sondeo de aristas.
    - 138.501 aristas no se ejecutan una a una en una sesion. Diseña un MUESTREO
      declarado: estratifica por motor y por par de familias, di cuantas sondeas y con
      que criterio, y da el intervalo de confianza. Un muestreo honesto y declarado vale
      mas que un censo a medias — bench/fidelidad-caminos.md §2 ya declaro su sesgo asi
      y es el modelo a seguir.
    - Prioriza donde mas duele: las aristas que el grafo usa como INTERMEDIAS. 820 de
      los 1.599 pares "pedidos" tienen PDF como unico intermedio posible; si una arista
      hacia PDF es nominal, se cae media tesis del multi-salto.
    - No basta con "el comando devuelve 0". Usa bench/scripts/verificador.py, que ya
      atrapa exactamente este fallo: un PNG entregado como .avif, un fichero de 0 bytes
      con estado "Done", un redimensionado no solicitado. La categoria correcta para una
      arista que "funciona" y entrega basura es NOMINAL, igual que la que falla.
    - Clasifica con el mismo vocabulario del patron oro: INTEGRO / PERDIDA INEVITABLE /
      DEGRADADO / DESTRUIDO / FALLO.

C8. Los 7 casos no_evaluable de bench/salidas-referencia/referencia.json (DOCX<->PDF,
    EPUB, SVG, OCR, qpdf, vips) siguen sin motor en esta maquina y NO se han dado por
    buenos: no tienen salida que verificar. Lo que falta va en CONTENEDOR, no instalado
    a mano: Gotenberg ya esta levantado en :3200 y ConvertX en :3100.
    OJO con un resultado ya medido que te ahorra tiempo: Gotenberg DECLARA .epub entre
    sus extensiones pero LibreOffice NO TIENE FILTRO DE IMPORTACION de EPUB — solo lo
    exporta. HTTP 500 con tres EPUB distintos, incluidos los de los corpus de transmute
    y docling. Es, en si mismo, el mejor ejemplo de arista nominal del proyecto.

ENTREGABLE: UN UNICO informe en bench/aristas-nominales.md, salidas en
bench/salidas-aristas/. NO toques bench/salidas-referencia/referencia.json: es el patron
oro, se lee y no se toca. La cifra que tiene que salir del informe es una sola y clara:
QUE PORCENTAJE DE LAS ARISTAS DECLARADAS NO EXISTE, con su intervalo y su metodo.

[PEGA AQUI EL BLOQUE DE CONTEXTO COMPARTIDO DE §5]
[PEGA AQUI LAS REGLAS COMUNES DE §6]
```

---

## 8. Oleada 3 — esbozos

No los desarrollo porque conviene decidirlos **después** de leer los informes de las oleadas 1 y 2.

| # | Trabajo | Nota |
|---|---|---|
| **B6** | NVENC en lote sobre una carpeta real | Único pendiente del hueco 4. Es el único escenario donde el 8,39× de HEVC decide algo: para una conversión suelta, 16 s frente a 2 s no cambia el comportamiento de nadie |
| **B7 + B8** | Heurística de degradación severa; R1 sobre PDF que no son «una imagen a página completa»; `-deskew` × techo ×1,4 | Depende de que G1 entregue d4: sin un caso con gradiente, la heurística no tiene contra qué calibrarse |
| **C6** | Saturación replicada en dominio documental, con `temperature` fija y modelos no-Claude | Requiere clave de API, que **no existe en esta máquina**. Es la limitación nº 1 declarada de `saturacion-herramientas.md` §8 |
| **C7** | Demanda real de conversiones | No es una medición de máquina: el catálogo de SnapOtter es un proxy. Probablemente sea trabajo de producto, no de banco |

---

## 9. La pregunta que no es de reparto — **revisada el 21/08 a las 14:00**

Los huecos **2, 3 y 4 están cerrados o refutados**, y el **2 lo está ahora con sus TRES cifras, que hay que citar juntas**: el **50,5 %** de las aristas declaradas verificables no existe **con la invocación del sector**, baja a **41,0 % con una invocación cuidada** —y **3 226 aristas, el 10,2 %, son ganancia automática para FileX**—, y **el estrato que el multi-salto usa —el que toca PDF— sale al 3,0 %**, confirmado por un segundo camino independiente (censo completo de Ghostscript y Gotenberg: **3,1 %**). El **1** está cerrado con su coste medido —**una semana de trabajo, no un trimestre**— y `bench/scripts/verificador.py` (**4 185 líneas**) es ya un prototipo funcional del **hito 3**, con **contrato de cinco puntos**, 15 reglas de fidelidad y 0 falsos positivos sobre 53 salidas. El **5** tiene por fin un corpus que mide margen (`d4`) y **un motor único que lo cubre entero en CPU**.

> **Los hitos 1, 2 y 3 de `PLAN-ORQUESTADOR.md` §7 siguen sin estar bloqueados por ninguna medición pendiente.**

**Lo que dijo este documento la vez anterior se cumplió, y con una corrección:** *«solo dos cosas cambiarían una decisión de diseño: el d4 y el OCR de Ghostscript en castellano»*. **Las dos se midieron y las dos cambiaron algo** — pero **el cambio de diseño más grande no vino de ninguna de las dos, sino de un subproducto de la primera**: la normalización del detector de RapidOCR, que nadie había puesto en el inventario. *(Ni el quinto punto del contrato, que salió de una campaña de aristas cuyo objetivo era contar, no verificar.)* **Conviene no leer eso como un fallo de planificación, sino como el argumento a favor de ejecutar: lo que más movió el diseño no estaba en la lista de lo que se iba a medir.**

~~**Las tres cosas que hoy cambian diseño**~~ **— actualizado a las 14:00, y son otras cuatro, con una de las tres anteriores refutada:** la **regla de ppp que BAJA AL ADAPTADOR DE CADA MOTOR** (y con ella cae el techo absoluto que este documento proponía hace unas horas), **R18 como requisito de coste y no como higiene**, **el punto 5 que no es verificable a posteriori** —y por tanto la verificación tiene que vivir dentro de la conversión—, y **los dos regímenes de «en proceso frente a subproceso»**. Están desarrolladas en `bench/consolidacion-3-21ago.md` §2, y su trabajo derivado en §3 (B11, B13, C19–C23).

**Y hay un patrón que ya se puede afirmar con cuatro casos:** *lo que más ha movido el diseño de FileX no estaba en la lista de lo que se iba a medir.* La normalización del detector salió de un encargo sobre corpus; el quinto punto, de una campaña que iba a **contar** aristas; el fallo de `_gs_texto`, de un encargo sobre el contrato; y **la refutación de «en proceso siempre gana», de medir el coste de una regla de fidelidad**. **No es un fallo de planificación: es el argumento a favor de ejecutar.**

**Si el objetivo es construir y no seguir midiendo:** **está hecho todo lo que desbloquea, y ahora con más margen que antes.** Lo que queda —G2 (tres motores más), M1 (cabos MCP), C16 (cerrar el 54,78 % indeterminado), B13 (el `k` por motor sobre más documentos)— es **exhaustividad o calibración fina**, valiosa pero no bloqueante. **G2 sigue bajando de prioridad**, y **B13 sube**: sin él, el `k` de cada motor es una estimación de un solo documento, aunque **con `k = 1,00` por defecto la regla ya es segura** (el nativo nunca es el peor punto del barrido en ninguna de las siete configuraciones).

**Lo único con prioridad real antes de construir: ejecutar el commit (A5).** **Van siete agentes sin versionar y `git status` tiene 44 entradas.**

---

## 10. Documentos de referencia

| Ruta | Para qué |
|---|---|
| `CLAUDE.md` | Las reglas de trabajo, las **109** trampas ya pagadas y las reglas de diseño no negociables. ~~24~~ — **la cifra llevaba setenta y ocho trampas desfasada**, que es el mismo defecto que esta sección viene a arreglar |
| **`bench/salidas-publicacion/MANIFIESTO.md`** | **El mapa `viejo → nuevo` de los 64 commits que reescribió el `filter-repo` del 31/08**, y el residuo que dejó la herramienta: 48 ocurrencias de la credencial en un `fast-export.original` de 57 MB **dentro de `.git`** |
| `HUECOS.md` | Los cinco diferenciadores, con su veredicto y su evidencia |
| `PLAN-ORQUESTADOR.md` | El plan de construcción: 7 hitos con criterio de aceptación |
| `ANALISIS-COMPLETO.md` | El análisis del ecosistema, 21 tablas |
| `RESULTADOS-MCP.md` | Las reglas MCP y las 15 de confinamiento |
| `bench/ocr-ppp-nativos.md` | **La tabla canónica de OCR** para d1-d3 y patológico. Sustituye a `gpu-fase2.md` §5. ⚠️ **Su regla de ppp está SUPERADA por `ppp-y-normalizacion.md`** |
| **`bench/corpus-d4.md`** | **`escaneado_d4`**, la causa real de la asimetría de PaddleOCR y las dos refutaciones CPU/GPU. ⚠️ **Su techo absoluto de ppp (§8) está REFUTADO** |
| **`bench/aristas-nominales.md`** | **El 50,5 % de aristas nominales** con su método, el estrato PDF al 3,0 %, el quinto punto del contrato y los 5 de 7 `no_evaluable` cerrados |
| **`bench/verificador-ghostscript.md`** | **El OCR sin GPU**, la arista de reparación de dos saltos, `P9` contra la alucinación *(refutada después)*, V2 y su coste, y **los dos testigos de ruido** |
| **`bench/ppp-y-normalizacion.md`** | **LA REFERENCIA VIGENTE DE ppp.** El barrido de 17 puntos, la refutación de las tres unidades candidatas, **el `k` por motor y dónde vive**, los topes internos sondeados en ejecución, y **la validación de la normalización por checkpoint** con sus 12 empeoramientos |
| **`bench/invocacion-aristas.md`** | **El 18,8 % del 50,5 % que era invocación**, con sus tres categorías; los crudos y sus cuatro datos; `imagen → pdf` con densidad ajustada; el **censo completo de Ghostscript y Gotenberg al 3,1 %**; y **el coste de `qpdf` + `tesseract`** |
| **`bench/contrato-quinto-punto.md`** | **El quinto punto medido** (+11,0 % con R18, ×8,6 sin él, **no verificable a posteriori**), **la regla I9** y su coste real, **la familia de cinco miembros**, **`P9` refutada con su sustituto**, el interruptor de V2, y **el fallo de la sonda `_gs_texto`** |
| **`bench/consolidacion-3-21ago.md`** | **Qué cambió en cada maestro el 21/08 a las 14:00**, las cuatro cosas que cambian el diseño, y **la lista de lo que el proyecto se ha refutado a sí mismo en un día** |
| **`bench/consolidacion-2-21ago.md`** | **Qué cambió en cada maestro el 21/08 a las 10:00**, y las tres cosas que cambian el diseño de FileX |
| `bench/verificador-fidelidad.md` | El verificador hasta la fidelidad, y sus siete pendientes |
| `bench/mcp-cabos-sueltos.md` | Los cinco cabos MCP, con su tabla de 12 correcciones en §6 |
| `bench/saturacion-herramientas.md` | 540 ejecuciones: el catálogo grande no degrada la elección |
| `bench/fidelidad-caminos.md` | 69 caminos ejecutados: la refutación del multi-salto |
| `bench/coste-verificacion.md` | El coste del contrato: 0,032 % en proceso, 145× con subprocesos |
| `bench/referencia-nativa.md` | El patrón oro: 53 salidas, 46 reglas, 39 órdenes, 17 pérdidas |
| `bench/lib/harness.sh` | El arnés: `gpu_acquire`, `measure`, `peak_vram` |
| `AGENTES-PRUEBAS-PENDIENTES.md` | **Superado por este documento.** Su contexto y sus marcas están invalidados |

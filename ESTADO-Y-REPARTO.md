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

**Un solo commit** (`87091fe`, *Investigación del ecosistema de conversión de archivos*). Todo lo posterior está sin versionar:

| Estado | Ficheros |
|---|---|
| **Modificados sin commit** | `ANALISIS-COMPLETO.md`, `HUECOS.md`, `PLAN-ORQUESTADOR.md`, `RESULTADOS-MCP.md`, `analysis/00-licencias.md`, `analysis/00-mcp-componentes.md`, `analysis/00-mcp-filesystem.md`, `analysis/00-mcp-patrones.md`, `analysis/OCRmyPDF.md`, `bench/gpu-fase2.md`, `bench/scripts/verificador.py` |
| **Sin versionar** | `bench/mcp-cabos-sueltos.md`, `bench/ocr-ppp-nativos.md`, `bench/saturacion-herramientas.md`, `bench/verificador-fidelidad.md` + `bench/salidas-mcp-cabos/`, `salidas-ocr-ppp/`, `salidas-saturacion/`, `salidas-verificacion-fidelidad/` |

**La deuda documental es real y está fechada.** `HUECOS.md` se revisó a las **00:32**; los cuatro informes nuevos son de las **02:44–03:07**. Ninguno está integrado en ningún documento maestro.

### Informes por orden de antigüedad (los últimos)

> **Corregido el 23/08 (L1): esta tabla se cortaba el 21/08 a las 14:00 y le faltaban DIECISÉIS informes.** Entre lo que no figuraba estaba **la construcción entera del paquete `filex/`** —cuatro superficies, 129 pruebas, cuatro hitos del `PLAN-ORQUESTADOR.md` marcados HECHO— y **los tres sondeos que llevaron el grafo de 132 aristas `sin_sondear` a ~0**. Un inventario que no registra el trabajo hecho hace que el proyecto se planifique como si no existiera.

| Fecha | Informe | Qué cierra |
|---|---|---|
| 23/08 (en curso) | **`bench/phys-multimotor.md`** (G4) | **El `pHYs` fuera de Tesseract.** Veredicto provisional: PaddleOCR, RapidOCR y EasyOCR son **inmunes** (300 celdas, un solo `md5` por fila motor×documento). **NO ESTÁ CERRADO: hay un agente escribiéndolo ahora** |
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
> **Una fila = un identificador = exactamente un emoji de estado, y va en la última columna.** Verificado a máquina: **87 filas, 87 emojis.**
>
> | Emoji | Significa | Cuántos hoy |
> |---|---|---|
> | 🟢 | **CERRADO** con informe que lo prueba | **32** |
> | 🟡 | **EN CURSO o PARCIAL** (una mitad cerrada, o hay un agente dentro) | **6** |
> | 🔴 | **ABIERTO** | **44** |
> | ⚫ | **histórico**: la fila se conserva porque documenta una refutación, pero **no cuenta** | **5** |
>
> La orden que lo comprueba. Hay que acotar **dos** veces: a la §3, porque la §4 usa ✅ para el estado de los *agentes*; y **a las filas cuya primera celda es un identificador**, porque si no la propia leyenda se cuenta a sí misma (comprobado: sin el segundo filtro salen 47/8/35/7 en vez de 44/6/32/5):
>
> ```sh
> awk '/^## 3\. Inventario/{f=1} /^## 4\. El reparto/{f=0} f' ESTADO-Y-REPARTO.md \
>   | grep -E '^\| (~~)?\*\*[ABCN][0-9]+'                                          \
>   | grep -o '🔴\|🟡\|🟢\|⚫' | sort | uniq -c
> ```
>
> Salida esperada hoy: `5 ⚫ · 44 🔴 · 6 🟡 · 32 🟢`.
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
| **A5** | ✅ **CERRADO el 22/08/2026: commit `1fb5024` ejecutado**, 1.799 ficheros, +271.130/−210, los 6 PDF de `d4` por Git LFS y los ~30 binarios regenerables de `salidas-aristas/` excluidos por `.gitignore` con su `MANIFIESTO.md`. Entran los doce informes. Se recuperó además `PRUEBAS-MCP-REFS.md`, que solo existía en las ramas `ccb/w1..w3`, ya borradas. ~~**SIGUE ABIERTO, y es lo más urgente del inventario** — no se ha ejecutado ni `git add` ni `git commit`. **Van SIETE agentes sin commit y `git status` tiene 44 entradas.** La lista vigente está en `bench/consolidacion-3-21ago.md` §6~~ | 🟢 **CERRADO** |
| **A7** | **Decidir si la métrica de OCR canónica del proyecto pasa a ser la acentuada.** Hoy `bench/scripts/ocr_eval.py` sigue intacto y sigue siendo ciego; hay **dos copias** con acentos (`ocr_eval_d4.py`, `ocr_eval_tildes.py`) y ninguna es la oficial. **Actualizado el 23/08: de hecho ya está decidido y nadie lo ha escrito.** Cuatro informes seguidos —`corpus-d5.md`, `psm-y-rasterizador.md`, `k-por-motor.md` §1.2 y `phys-multimotor.md`— **declaran que no abren `ocr_eval.py` porque es ciego** y copian `ocr_eval_d4.py` byte a byte con su `sha256`. Lo que falta es **el acto formal**, no la evidencia | 🔴 **ABIERTO** |
| **A9** | **Registrar en este inventario el trabajo del 22 y 23/08.** **Quince informes de `bench/` no tenían una sola cita aquí**, y ocho son de esos dos días: los cuatro hitos (`hito3-mudanza`, `hito4-mcp`, `hito5-documental`, `hito7-superficies`), los tres sondeos (`sondeo-imagemagick`, `sondeo-ffmpeg`, `sondeo-documental`) y `consolidacion-4-22ago`. **La §1 ya está corregida (23/08, L1); falta que los pendientes que abren esos ocho estén repartidos**, y por eso nace la §3.N | 🟡 **PARCIAL** |

### B · Requieren GPU — **estrictamente uno a la vez** (lock exclusivo)

| # | Pendiente | Estado / origen |
|---|---|---|
| ~~**B1**~~ | Construir `escaneado_d4` | 🟢 **CERRADO** por G1. **Cumple los cuatro criterios y el de éxito.** `corpus/pdf/escaneado_d4{,a,b,c,e,f}.pdf` + `MANIFIESTO-d4.md` |
| ~~**B2**~~ | Aislar la asimetría de PaddleOCR | 🟢 **CERRADO** por G1, y **no era ninguna de las tres candidatas**: era la normalización del detector de RapidOCR. **72,2 puntos por seis números** |
| **B3** | **marker** — instalado y sin medir. `torch 2.13.0` **sin paquetes `nvidia-*`**: es build **CPU**. **Confirmado el 23/08: sigue sin una sola medida.** `bench/salidas-marker/` solo contiene un `logs/` vacío y hereda el bloqueo de surya (`surya-ocr>=0.22.1,<0.23.0`) | 🔴 **ABIERTO** |
| **B4** | **surya** por `SURYA_INFERENCE_BACKEND=llamacpp` o `VLLM_GPU_MEMORY_UTILIZATION=0.5`. **Único material: `bench/gpu-fase1.md` §B.3 — «NO FUNCIONA en GPU en esta máquina».** VRAM: sin dato | 🔴 **ABIERTO** |
| **B5** | **MinerU `[vlm]`** (no `[vllm]`). **Cero menciones en todo `bench/`** | 🔴 **ABIERTO** |
| **B6** | **NVENC en lote sobre carpeta real** — el único pendiente del hueco 4, y el único caso donde decide algo. **Y ahora tiene un segundo motivo:** `bench/hito7-superficies.md` §5.4 mide que en `filex/` **no hay uso de GPU ni lock de GPU** —las apariciones de `nvenc`/`cuda` en el paquete son **tres comentarios**—, así que el hito 2 del `PLAN-ORQUESTADOR.md` sigue sin empezar | 🔴 `HUECOS.md` §4 · **ABIERTO** |
| **B7** | Heurística de «degradación severa». **Ahora hay contra qué calibrarla (`d4`) y dos señales candidatas medidas**: cajas detectadas frente a área de texto, y el tiempo (d3 cuesta ×4,5 lo que d2 en Ghostscript) | 🟡 `corpus-d4.md` §11, `verificador-ghostscript.md` §5.4 |
| **B8** | R1 sobre PDF que **no** son «una imagen a página completa»; e interacción de **`magick -deskew 40%`** con el techo, ahora sobre la familia d4 (rotada de −4° a +4°). **Comprobado el 23/08: ningún informe posterior menciona `deskew`** | 🔴 ídem · **ABIERTO** |
| ~~**B9**~~ | Barrer la curva de ppp sobre `d4` | 🟢 **CERRADO** por P1, **y el techo absoluto queda REFUTADO igual que el relativo.** 17 puntos × 7 configuraciones + 24 celdas de control: **los ppp no son la unidad, ni el factor, ni la anchura en píxeles. La regla es POR MOTOR y baja al adaptador** |
| ~~**B10**~~ | Validar la corrección de normalización fuera del corpus d4 | 🟢 **CERRADO** por P1. **0 regresiones en 15 documentos sobre `PP-OCRv6 small`** (incluidas 4 rasterizaciones del patrón oro) — **y 12 de 42 celdas peores si se aplica a la familia**, con **+42,50 puntos** en `PP-OCRv4 mobile` sobre un documento limpio |
| **B11** | **Llevar la corrección a producción — y su contenido CAMBIA.** No es «añadir R6 a `bench/scripts/ocr_motor.py`»: **sobre el `PP-OCRv5 mobile` que usa hoy, R6 NO es recomendable** (4 de 15 celdas peores). Es **cambiar a `PP-OCRv6 small` Y añadir R6**. **Saldo medido, declarado entero: 7 mejor, 2 igual, 2 PEOR** (`d4a` +5,87 y `d4f` +1,01, por el cambio de checkpoint, no por R6). El parche exacto está en `ppp-y-normalizacion.md` §4, **propuesto y NO aplicado**. **Redefinido OTRA VEZ el 22/08:** `k-por-motor.md` §4.2 corrige dos `k` (Docling+R6 ×1,00→**×0,875**; Tesseract ×1,50→**×0,875/×0,75**) y `psm-y-rasterizador.md` §7 añade que **un `k` publicado sin su `--psm` no es un número**. Tres informes verifican que `ocr_motor.py` **sigue intacto** | 🟡 **REDEFINIDO ×2** · `ppp-y-normalizacion.md` §3.5 §4, `k-por-motor.md` §4.2, `psm-y-rasterizador.md` §7 |
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
| **B16** | **Refinar `escaneado_d3` entre ×1,25 y ×1,4**, que es donde está el acantilado de RapidOCR+R6 (2,53 → 46,84) y solo hay dos puntos. **Es el mismo defecto que B9 vino a corregir en `d4`, en otro documento.** **AMPLIADO el 22/08** (`k-por-motor.md` §9): hay **un segundo acantilado sin puntos intermedios**, el de PaddleOCR entre **×1,40 y ×1,60** (3,80 → 75,95) | 🔴 **ABIERTO, ampliado** · `ppp-y-normalizacion.md` §8, `k-por-motor.md` §9 |
| **B12** | ✅ **CERRADO en lo esencial el 22/08** (`bench/corpus-d5.md` §0 punto 8, §5), **con residuo declarado**. Las tres degradaciones están **medidas en el píxel y con control de cero**: sombra de encuadernación (luminancia izq/dcha 0,87-0,78 frente al 0,99 de `d4`), curvatura (residuo 1,9-7,3 px frente a 0,4 del control `onda=0`) y transparencia del papel (1,00 → 0,74). **El residuo va a B20** | 🟢 **CERRADO** |
| **B20** | **El residuo de B12: la curvatura NO es la perilla dominante y su ablación sale al revés** con `psm 3`, y la sonda **satura por encima de ~3,5° de giro y con polvo ≥0,35** | 🔴 **NUEVO** · `corpus-d5.md` §8 |
| **B21** | **Todo `corpus-d5.md` es Tesseract.** Ninguna conclusión suya sobre el suelo de 100 ppp puede darse por buena para PaddleOCR, RapidOCR, EasyOCR ni docling — **y el suelo es la parte de la regla que hoy no tiene medida detrás** | 🔴 **NUEVO** · `corpus-d5.md` §8 |
| **B22** | **El óptimo de ~125 ppp es una hipótesis, no un número:** hay que barrer 100-150 con las nueve configuraciones | 🔴 **NUEVO** · ídem |
| **B23** | **El `k` sigue ajustado sobre CUATRO documentos y uno no discrimina: en la práctica son TRES**, que además **comparten geometría de página (465,84 pt)** y tres salen del **mismo generador** | 🔴 **NUEVO** · `k-por-motor.md` §9 |
| **B24** | **El `--oem` de Tesseract no se ha tocado** — es el otro parámetro estructural, y `--psm` ya demostró pesar más que el `k`. Con él: **los otros ocho `--psm` sin barrer**, y **la tabla de `k` de Tesseract habría que rehacerla con Ghostscript**, que es la vía que FileX usaría | 🔴 **NUEVO** · `psm-y-rasterizador.md` §9, `k-por-motor.md` §9 |
| **B25** | **El efecto del `pHYs` solo está medido con Tesseract.** `bench/phys-multimotor.md` (**G4, escribiéndose ahora**) lo está midiendo sobre PaddleOCR, RapidOCR y EasyOCR; veredicto provisional **inmunes**. **NO LO CIERRES: es de G4** | 🟡 **EN CURSO (G4)** · `psm-y-rasterizador.md` §9, `corpus-d5.md` §4.1 |
| **B26** | **El reciclado de proceso del sidecar de OCR no está medido en coste.** Es la consecuencia arquitectónica de que el asignador **no devuelva la VRAM** (9 y 24 lecturas idénticas al MiB): reiniciar el proceso lo arregla, esperar no | 🔴 **NUEVO** · `k-por-motor.md` §6.3, §9 |

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
| **C27** | **Subir G6 de `aviso` a `fallo`** — hoy está calibrada sobre **22 casos de un solo motor**. Exige medirla con más motores y comprobar que no marca conversiones legítimas entre formatos equivalentes (`png` → `apng`, `mkv` → `mka`) | 🔴 **NUEVO** · `firmas-contrato.md` §10.5 |
| **C28** | **Los 86 destinos indeterminados del censo de firmas**: 79 que ningún motor de esta máquina escribe y 7 donde la muestra describe al escritor y no al formato. Mismo corpus FATE que **C16**, o un segundo escritor por formato | 🔴 **NUEVO** · ídem §10.1 |
| **C29** | **Llevar el nivel de `familia` al veredicto.** Hoy `G5` es `informativo` y la cobertura cuenta la comprobación de familia como cubierta; una lectura estricta las dejaría en `ok_parcial`, igual que discutió `verificador-ghostscript.md` §2.4 para V5 | 🔴 **NUEVO** · ídem §10.6 |
| **C30** | **Repetir la prueba ancha de falsos positivos DENTRO del contenedor.** Cubre los **385 destinos locales**, no los 162 del contenedor: allí solo se guardaron 64 bytes de cabecera por muestra | 🔴 **NUEVO** · ídem §10.7 |
| **C31** | ~~**`_datos` lee el fichero entero en memoria** — 156 MB de RAM para contar comas en el TXT de ImageMagick. Y dos colisiones declaradas **sin falso positivo hoy**: `.pcd` como `mpegaudio` y TGA/CUR compartiendo `00 00 02 00`~~ **LAS DOS CIFRAS DEL ENUNCIADO SON FALSAS — MEDIDO el 22/08** (`bench/hito3-mudanza.md` §6.1-6.3). **(a) No es ×1 la RAM: es ×21,3** en la rama normal (y ×7,0 en la degradada); el culpable **no es el `read()` sino guardar `d["csv_filas"]`**, así que sobre el TXT de 156 MB son **≈1,1 GB de pico**, y el tiempo **no es lineal** (65 s para 32 MB). **(b) `.pcd` NO es «una colisión sin falso positivo»: es un falso positivo VIVO** — este ImageMagick escribe PhotoCD, y un `png→pcd` legítimo con `rc=0` sale **`veredicto: FALLO`**. **(c) TGA/CUR es un falso NEGATIVO confirmado en ejecución** (un TGA con extensión `.cur` sale `ok_parcial` con cero hallazgos). Ninguno arreglado; §6.2 deja tres opciones con su tensión de diseño y recomienda la **C**: no derivar la categoría de una firma que el punto 1 ya marcó dudosa | 🔴 **ABIERTO, enunciado corregido** · `hito3-mudanza.md` §6, `firmas-contrato.md` §10.2-10.4 §10.8 |
| **C32** | **La contradicción viva entre dos informes.** `hito3-mudanza.md` §7 pide *«una corrección a `bench/firmas-contrato.md` §10, que no es mío y cuyo autor (F1) debería revisar»*. **Dos informes del repositorio se contradicen y nadie lo ha arbitrado.** Precedente de cómo se hace: `ocr-ppp-nativos.md` §6 | 🔴 **NUEVO** · `hito3-mudanza.md` §7 |
| **C33** | **Aplicar el diff de W9** de `hito4-mcp.md` §8.1 y §8.2 — su propio informe lo llama *«un fallo de seguridad abierto, con las dos direcciones reproducidas»*. **Es lo más urgente de esta sección** | 🔴 **NUEVO** · `hito4-mcp.md` §8, §13 |
| **C34** | **`job cancelar` sigue sin matar el árbol** de procesos. Heredado del hito 4 y reconfirmado en el 7. Con el precedente medido de los tres `soffice` que sobrevivieron **37 minutos** a un `taskkill /F /T`, no es teórico | 🔴 **NUEVO** · `hito4-mcp.md` §13, `hito5-documental.md` §1 |
| **C35** | **Gotenberg, que es lo que el título del hito 5 pedía.** El hito se cerró por `filex-c13`, no por Gotenberg. Con él, los otros siete de `hito5-documental.md` §8: fidelidad más allá del centinela, `epub→mobi/azw3` con un lector de MOBI, una segunda semilla de documento, `xlsx/pptx/csv/svg/tex` dentro del contenedor, el arranque en frío (**34 672 ms** el primer `docker run`) y reutilizar contenedor vivo sin perder el punto 5 | 🔴 **NUEVO** · `hito5-documental.md` §8 |
| **C36** | **Los ocho pendientes restantes de `hito4-mcp.md` §13**: repetir §4 con otro modelo y n≥10, qué sustituye a `roots` en el protocolo 2026-07-28, la caché de roots invalidada por **una emisión real** (sigue sin observarse), medir el catálogo con el registro completo del hito 5, una prueba de subsunción automática, idempotencia ante `Resolve(ListRoots)` doble y el coste de un `convert` con ruta denegada (**gasta un `job_id`**) | 🔴 **NUEVO** · `hito4-mcp.md` §13 |
| **C37** | **Los 12 formatos de la deuda de firmas** (`firmas-contrato.md` §3.2). **Los dos accionables son `pict` y `pcd`**: bastaría leer más allá del byte 512 **solo cuando la extensión lo pide** — y `pcd` es justo el falso positivo vivo de C31 | 🔴 **NUEVO** · `firmas-contrato.md` §3.2, §10 |
| **C38** | **El lock de GPU solo existe en shell.** Ningún `.py` del repositorio llama a `gpu_acquire` (**0 de 15** arneses de Python que invocan `nvidia-smi`). Hoy se salva porque casi todos se lanzan desde un `.sh` que sí lo toma — **salvo `bench/scripts/whisper_precision.py` y `bench/scripts/gpuwatch.py`, que no los lanza ningún `.sh`.** En el paquete de producción no hay lock ninguno (→ N7) | 🔴 **NUEVO** · `lock-de-maquina.md` §6 |
| ~~**C15**~~ | Cuánto del 50,5 % se recupera con una invocación mejor | 🟢 **CERRADO** por P2. **El 18,8 %** [16,8–21,3]: la tasa baja a **41,0 %** con los mismos motores y build. **3 226 aristas (10,2 %) son ganancia automática** —se puede prometer—, 2 704 exigen un parámetro del usuario, y **25 603 (81,2 %) son irrecuperables**. **`-frames:v 1 -update 1` recupera 13 de las 27** del residuo |
| **C16** | **El 54,78 % de aristas indeterminadas.** Exige un corpus de 445 formatos que ningún motor local escribe (vía: corpus FATE de ffmpeg, ~1 GB). Es lo único que convierte el escenario central (48,6 %) en un número medido. **Y desde el 22/08 tiene un segundo cliente: C28 exige el MISMO corpus FATE**, así que cerrar uno abarata el otro | 🔴 **ABIERTO** · ídem §7, §11.1 · `firmas-contrato.md` §10.1 |
| ~~**C17**~~ | Censar las 140 aristas de Ghostscript y Gotenberg | 🟢 **CERRADO** por P2. **3,1 % nominal** [0,9–10,7], con **censo COMPLETO de Ghostscript (9/9 reales) y de Gotenberg/Chromium (25/25 reales)**. **Coincide con el 3,0 % del estrato PDF de E1 por un camino independiente.** Las dos nominales son de LibreOffice. **Sesgo declarado: 72 de las 102 extensiones de LibreOffice no se pudieron materializar → cota inferior** |
| **C18** | **Publicar los parámetros de I1 de `fidelidad-caminos.md`** (ppp de rasterizado, idioma de OCR, fórmula de similitud) para poder cerrar su 99,0 %, que **no se reproduce** (94,7–97,1 %). **Sigue NO REPRODUCIDO, no refutado** | 🔴 · `verificador-ghostscript.md` §5.7 |
| **C19** | **El miembro de la familia de `resvg` que sigue DESCUBIERTO:** audio con **un canal silenciado hacia un destino con pérdida**. El contrato ve 2 canales, frecuencia y duración correctas; A4/A5 no aplican porque no hay PCM que comparar. **El mismo fallo hacia FLAC sí lo atrapa A4: la cobertura depende del destino, no del fallo.** Propuesta sin medir: energía por canal con `ffmpeg -af astats` (sonda externa, grupo C) | 🔴 **NUEVO** · `contrato-quinto-punto.md` §5, §10 |
| **C20** | **Validar el sustituto de `P9` a escala.** El acuerdo entre dos pasadas de OCR con idiomas distintos separa **16 de 16 sin error** (banda vacía de 0,19 puntos), **pero está medido sobre 16 pares y un solo motor**: dos idiomas del mismo motor **podrían acordar en su propio error**. Falta validarlo **fuera de Ghostscript** y sobre vocabulario que `eng` no comparta. **Y decidir si `P9` se retira o se sustituye** | 🔴 **NUEVO** · ídem §6.3, §10 |
| **C21** | **Un suelo duro de PSNR para V8.** Un vídeo **enteramente negro** sale con **5,39 dB** y severidad `aviso`, porque V8 está calibrada para «recodificación con pérdida». **5,39 dB no es una recodificación agresiva: es otra imagen.** El precedente existe: I7 ya lleva un suelo de 20 dB | 🔴 **NUEVO** · ídem §5, §10 |
| **C22** | **Ampliar el patrón oro con una salida multifichero** (una HLS y una secuencia `%d`). `referencia.json` **no tiene ni una**, así que el «0 falsos positivos» del punto 5 se apoya en cuatro casos fabricados a propósito | 🔴 **NUEVO** · ídem §3.3, §10 |
| **C23** | **La curva fina del punto de cruce «en proceso / sonda externa» para píxeles.** Medido en tres tamaños (0,08 / 0,32 / 1,84 Mpx), con el cruce en **~0,1 Mpx**. **Decide en qué régimen corre cada regla de fidelidad**, y hoy la implementación usa el camino en proceso **porque no añade dependencias**, con un precio medido | 🔴 **NUEVO** · ídem §4.3, §10 |
| **C24** | **MITAD CERRADA el 22/08, y el enunciado cambia.** La mitad EXTERNA está explicada y **no era el envoltorio: era el `--psm`.** Sobre el mismo `d3`, `psm 3/4` devuelven **0 bytes** y `psm 6/11` devuelven **113,92 %** y **188,61 %** — *silencio y alucinación son el mismo motor con distinto modo de segmentación*, y **los tres devuelven `rc=0`**. Añadido: **0 bytes puede además ser un proceso que NO ARRANCÓ** (`rc=0xC0000142`), indistinguible del silencio legítimo si no se registra el `rc` (trampa 25). **Sigue abierta la mitad de Ghostscript: qué `--psm` usa su Tesseract embebido no se ha sondeado** | 🟡 **REDEFINIDO** · `psm-y-rasterizador.md` §2.2 §9, `k-por-motor.md` §6.1 |
| **C25** | **Lo que dejó abierto P2:** las 4 semiaristas de salida que resistieron el barrido (`amv`, `gxf`, `mlp`, `thd`) y las 11 aristas con `received no packets` *(dos intentos gastados en cada una)*; **la profundidad de los crudos de TERCEROS** —todo lo medido son ficheros que escribió el propio ImageMagick a 16 bits, y uno de 8 bits daría basura con la misma bandera—; `bayer`/`bayera` **sin referencia ideal** (≈366 aristas supuestas); y **el coste en tiempo de la invocación cuidada frente a la de ConvertX**, que añade dos lanzamientos de proceso por arista y **no está cuantificado** | 🔴 **NUEVO** · ídem §11 |
| **C26** | ✅ **CERRADO el 23/08 por L1** (`bench/lock-de-maquina.md`). El lock pasa a **`/tmp/filex-gpu.lock` = `%TEMP%`** (MEDIDO: `cd /tmp && pwd -W` → `C:/Users/krato/AppData/Local/Temp`), deja de quedarse **huérfano** —lleva dentro el **winpid** y el nombre de imagen del dueño, y la recuperación baja de **900 s a 1 s**— y se le añade **la mitad que el enunciado no pedía y que es la que cierra el caso real: DETECCIÓN.** **Un lock no obliga a cooperar a quien no lo toma**: la sesión de ASR nunca iba a tomar este fichero, esté donde esté. Así que `gpu_acquire` mira ahora la **VRAM libre** y **se niega a medir** por debajo de **6 000 MiB**. Línea base medida de esta máquina: **3 292 / 3 356 / 3 448 MiB ocupados** (mín/mediana/máx, n=90 a 1 s). **Y un límite medido que hay que saber: en WDDM la VRAM POR PID no es observable** (`--query-compute-apps` devuelve `[N/A]` en los 30 procesos y `pmon` responde *«not supported in this configuration»*), así que *«mira los PID»* solo puede dar **una lista de sospechosos**, nunca al culpable | 🟢 **CERRADO** |

### N · Deuda del paquete `filex/` — **nace el 23/08 y no tenía sección**

> El paquete de producción se construyó los días 22 y 23 (hitos 3, 4, 5 y 7 marcados HECHO en `PLAN-ORQUESTADOR.md` §7) **sin que este inventario registrara ni el trabajo ni la deuda que dejó**. Estas filas salen de `bench/hito7-superficies.md` §7.3 y del docstring de `filex/sondeo.py`.

| # | Pendiente | Estado / origen |
|---|---|---|
| **N1** | **El cerrojo de destino de FileX es DE PROCESO, no de máquina.** Tres peticiones simultáneas con tres entradas distintas a la misma ruta de salida devolvían **las tres `ok`**, declarando 13 516 / 14 402 / 647 580 B con **un solo fichero en el disco**. El arreglo está puesto en `filex/nucleo.py` (**3,2 µs de mediana, p90 4,6 µs, n=20 000 — el 0,0013 % de una conversión**), pero **una API y un watcher en procesos distintos siguen pudiendo pisarse**. Es **la misma clase de problema que C26**, y quien lo cierre debería reutilizar el mecanismo | 🔴 **NUEVO** · `hito7-superficies.md` §5.3, §7.3 |
| **N2** | **La suite de pruebas lee estado del disco, así que NO es reproducible mientras se sondea.** OBSERVADO: una pasada de las 88 falló justo cuando el grafo pasó de 142 a 190 aristas `real` porque otro agente escribió su fichero a mitad; las dos siguientes dieron 88 en verde. **O las pruebas fijan su propio sondeo, o se declara que la suite no vale mientras se sondea** | 🔴 **NUEVO** · `filex/sondeo.py` (docstring), `sondeo-documental.md` |
| **N3** | **El sondeo caduca al cambiar el CÓDIGO de FileX, no solo el `build` del motor — y hoy NO se comprueba.** MEDIDO el 22/08: 21 aristas medidas `nominal` quedaron obsoletas en cuanto se arreglaron la sonda y la invocación; al resondearlas, **20 de 21 salieron `real`**. El `build` protege contra cambiar de máquina; **nada protege contra cambiar de código**. Arreglo propuesto: **una huella de `motores.py` y `verificador.py` junto al `build`** | 🔴 **NUEVO** · `filex/sondeo.py` (docstring) |
| **N4** | **`_estable_en_disco` en POSIX devuelve `True` y el único cerrojo es `stat`.** En Windows el cerrojo real es `os.replace(p, p)` → `WinError 32`; en POSIX no hay equivalente | 🔴 **NUEVO** · `hito7-superficies.md` §3.2, §7.3 |
| **N5** | **«Fichero incompleto» con un formato SIN suma de comprobación** (CSV, WAV): el watcher no tiene con qué detectarlo. Precedente medido: convirtió el **55 %** de un PNG | 🔴 **NUEVO** · ídem §3.3 |
| **N6** | **Mover `Servicio` y `Trabajos` a `filex/servicio.py`** — *«ya no son de MCP… Lo dejo señalado, no hecho»* | 🔴 **NUEVO** · ídem §2.4 |
| **N7** | **No hay lock de GPU en `filex/`**, ni uso de GPU: las apariciones de `nvenc`/`cuda` en el paquete **son tres comentarios**. Cuando entren NVENC (B6) y el sidecar de IA, la API lo descubrirá a base de contención. Emparejado con **C38** (el lock de `bench/` tampoco existe en Python) | 🔴 **NUEVO** · ídem §5.4 |
| **N8** | **Las TRES TRAMPAS propuestas y NO aplicadas a `CLAUDE.md`** (§10 de `hito7-superficies.md`, numeradas 26, 27 y 28 para ir **al final**): (26) dos peticiones simultáneas al mismo destino devuelven las dos `ok` y **el contrato no puede verlo** porque juzga dentro del desechable de R18; (27) *«si puedo abrirlo, está completo»* es falso **y la estabilidad de `stat` sola tampoco basta**; (28) **R1 y R4 están en tensión y ya hay número: 9,4 µs frente a 193,3 µs, ×20,6** — el mensaje y el código son idénticos y **lo que distingue es el reloj**. **Nadie ha decidido si entran** | 🔴 **NUEVO** · `hito7-superficies.md` §10 |
| **N9** | **El oráculo temporal de R4 sigue sin resolverse**, que es lo que la trampa 28 describe: igualar por arriba convierte el rechazo en un **amplificador de DoS**; igualar por abajo pierde el `realpath`. **Se decide por superficie, y se dice** — pero no se ha decidido | 🔴 **NUEVO** · ídem §7.2 |

---

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
| **A5** | **Ejecutar el commit.** Siete agentes sin versionar | — |

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

### Oleada 6 — **23/08, en curso**

| Agente | Trabajo | Informe | Estado |
|---|---|---|---|
| **H7** | Hito 7 (watcher + API + R10) | `bench/hito7-superficies.md` | ✅ **CERRADO.** Abre la §3.N entera |
| **G4** | El `pHYs` fuera de Tesseract (**B25**) | `bench/phys-multimotor.md`, `bench/salidas-phys-multi/` | 🟡 **EN CURSO — NO TOQUES SUS FICHEROS** |
| **L1** | **C26** + el barrido de veracidad de este documento | `bench/lock-de-maquina.md`, `bench/lib/harness.sh`, este fichero | ✅ **CERRADO** |

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
| `CLAUDE.md` | Las reglas de trabajo, las **24** trampas ya pagadas y las reglas de diseño no negociables |
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

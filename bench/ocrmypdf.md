# OCRmyPDF en WSL — ¿preprocesado antes del OCR?

Agente A de `AGENTES-PRUEBAS-PENDIENTES.md` §4.1. Entorno: WSL2 / Ubuntu 26.04 LTS
(2 vCPU, 1,9 GiB por decisión del usuario en su `.wslconfig`). Sin GPU: OCRmyPDF es CPU.

**El agujero que se quería tapar:** en la variante de dificultad 3 fallaron los tres motores
de OCR probados (RapidOCR 65,8 %, PaddleOCR 75,9 %, EasyOCR 57,0 % de CER). La hipótesis
era que el preprocesado de OCRmyPDF (`--deskew`, `--clean`, `--remove-background`,
`--rotate-pages`) rescataría el documento.

> **Resultado en una línea:** el preprocesado de OCRmyPDF **no rescata nada** — dos de sus
> cuatro banderas están rotas o son inertes en esta versión. Pero al montar los controles
> para demostrarlo apareció otra cosa: **la dificultad 3 sí se resuelve, con CER del 2,5 %,
> y lo que la bloqueaba era el propio arnés de medición**, que rasterizaba a 200 ppp un
> original de 100 ppp. El hallazgo no es de catálogo ni de preprocesado: es que **la
> resolución de rasterización es un parámetro de primer orden y estaba mal fijado.**

Reproducible con los scripts numerados de `bench/salidas-ocrmypdf/` (00 → 71) y sus
`logs/`.

---

## 1. Qué se instaló y cuánto ocupó

**Ya estaba instalado** de un intento anterior de esta misma tarea (20/08 09:49). No hizo
falta instalar nada; los directorios `bench/salidas-ocrmypdf/{img,logs}` estaban vacíos, así
que del intento previo no había **nada aprovechable** salvo los propios paquetes de WSL.

| Componente | Versión |
|---|---|
| ocrmypdf | 16.13.0+dfsg1 |
| tesseract | 5.5.0 (leptonica 1.86.0) |
| tessdata | `eng`, `spa`, `osd` |
| unpaper | 7.0.0 |
| ghostscript | 10.06.0 |
| pngquant | 4.0.3 |

Coste en disco (`71_disco.sh`):

| Medida | Tamaño |
|---|---:|
| Los 11 paquetes directos (`dpkg Installed-Size`) | **25,1 MB** |
| Cierre **completo** de dependencias (302 paquetes) | **502 MB** |
| `/usr/share/tesseract-ocr` (modelos) | 17 MB |
| `/usr/lib/python3/dist-packages/ocrmypdf` | 1,4 MB |
| `/usr/bin/unpaper` | 80 KB |

Los 502 MB coinciden con la estimación de la ficha. Ojo: buena parte es Ghostscript +
Python + Qt/imagen que un Ubuntu de escritorio ya tiene; en un contenedor limpio el coste
real ronda esa cifra.

## 2. ¿Arrancó?

Sí. `ocrmypdf -l spa --force-ocr corpus/escaneado_d3.pdf out.pdf` termina con rc=0 en ~1,5 s.

Tres avisos/fallos que sí importan para la integración:

1. **`--remove-background` no existe.** No es un fallo de entorno, es código muerto:
   ```
   File "/usr/lib/python3/dist-packages/ocrmypdf/_pipeline.py", line 576,
       in preprocess_remove_background
     raise NotImplementedError("--remove-background is temporarily not implemented")
   NotImplementedError: --remove-background is temporarily not implemented
   ```
   Aborta con rc=15 en las 4 variantes. La bandera sigue anunciada en `--help`.

2. **Aviso permanente de Ghostscript** en cada invocación:
   `Ghostscript 10.6.x contains JPEG encoding errors that may corrupt images. OCRmyPDF will
   attempt to mitigate, but this version is strongly not recommended.` — Ubuntu 26.04 trae
   gs 10.06.0, que es a la vez la última versión y la que OCRmyPDF desaconseja. No hay
   salida limpia por apt.

3. **`--deskew` es un no-op** (ver §3.2). No falla: devuelve 0,000° siempre.

## 3. Precisión

Referencia (idéntica en las 4 variantes), 79 caracteres normalizados:
`DOCUMENTO ESCANEADO / Texto que solo existe como pixeles. / Debe recuperarse con OCR.`
Métrica: `bench/scripts/ocr_eval.py`, la misma de la fase 2.

### 3.1 Fase 2 — OCRmyPDF como motor completo (línea base)

CER % / distancia de edición. Motor real: Tesseract 5.5 en CPU.

| receta | patologico | d1 | d2 | **d3** |
|---|---:|---:|---:|---:|
| `--force-ocr` (base) | 0,0 % / 0 | 0,0 % / 0 | 30,4 % / 24 | **100,0 % / 79** |
| `+ --deskew` | 0,0 % / 0 | 0,0 % / 0 | 30,4 % / 24 | **100,0 % / 79** |
| `+ --clean-final` | 0,0 % / 0 | 0,0 % / 0 | 30,4 % / 24 | **100,0 % / 79** |
| `+ --rotate-pages` | 0,0 % / 0 | 0,0 % / 0 | 30,4 % / 24 | **100,0 % / 79** |
| `+ los tres juntos` | 0,0 % / 0 | 0,0 % / 0 | 30,4 % / 24 | **100,0 % / 79** |
| `+ --oversample 300` | 0,0 % / 0 | 0,0 % / 0 | 0,0 % / 0 | 78,5 % / 62 |
| `+ --oversample 400` | 0,0 % / 0 | 0,0 % / 0 | 0,0 % / 0 | 100,0 % / 79 |
| `+ --remove-background` | — | — | — | **no ejecuta (rc=15)** |
| `--clean-final --unpaper-args` agresivo | — | — | 100,0 % / 79 | 100,0 % / 79 |

Como se esperaba, **no gana**: es perfecto hasta d1, se degrada en d2 y en d3 el sidecar
sale **literalmente vacío** (CER 100 %). Con `--oversample 300` saca 23 caracteres de basura
(`RES E o) 14? Y A o | U % 4 ó ñ e A 3`), que es peor que no sacar nada.

Detalle no menor: forzar unpaper con sus filtros reales (`--unpaper-args` sin
`--no-grayfilter --no-blackfilter`) **destruye** la página — d2 pasa de 30,4 % a 100 % de CER.

### 3.2 Por qué las banderas no hacen nada — comprobación pixel a pixel

Comparé el PNG rasterizado de cada receta contra el de `base` (RMSE, `magick compare`):

| receta | d3 | d2 | patologico |
|---|---:|---:|---:|
| `--deskew` | **0** | **0** | **0** |
| `--clean-final` | **0** | **0** | 434 |
| `--rotate-pages` | **0** | **0** | **0** |
| `--oversample 300` | 1547 | 1186 | 732 |

Es decir: **`--deskew`, `--clean-final` y `--rotate-pages` producen una imagen de salida
bit a bit idéntica a no usarlas**. Los logs verbosos (`logs/12_diagnostico.log`) explican
cada caso:

- **`--deskew` → `Deskew angle: 0.000`.** OCRmyPDF delega en
  `ocrmypdf/_exec/tesseract.py::get_deskew`, que lanza `tesseract --psm 2` y parsea el
  campo `Deskew angle`. **Control decisivo** (`14_control_deskew.sh`): sobre una página
  sintética *nítida, alto contraste, 300 ppp, girada exactamente 5°*, `tesseract --psm 2`
  devuelve:
  ```
  Orientation: 0
  WritingDirection: 0
  TextlineOrder: 2
  Deskew angle: 0.0000
  ```
  No es que d3 sea demasiado malo: **el `--deskew` de OCRmyPDF con el motor Tesseract por
  defecto no corrige inclinación fina, nunca.** El `-deskew 40%` de ImageMagick, en cambio,
  sí encuentra y corrige el ángulo en las 4 variantes.

- **`--clean-final`.** OCRmyPDF invoca unpaper desactivando precisamente los filtros que
  limpiarían ruido:
  `unpaper --layout none --mask-scan-size 100 --no-border-align --no-mask-center
  --no-grayfilter --no-blackfilter --no-deskew`. Sobre ruido gaussiano en JPEG q25 eso es
  un no-op. Activarlos a mano destruye el texto (§3.1).

- **`--rotate-pages`.** Funciona correctamente y decide bien: `page is facing ⇧,
  confidence 1.19 - no change`. Solo maneja múltiplos de 90°, no inclinación fina. Aquí no
  hay nada que rotar, así que su aportación es cero por diseño.

- **`--oversample`** es la única bandera con efecto medible sobre la imagen. Y es
  exactamente la hipótesis barata de la fase 4: re-rasterizar a otros ppp.

### 3.3 Fase 3 — la prueba principal: OCRmyPDF como preprocesador

Salidas PDF de cada receta rasterizadas a **200 ppp en escala de grises** —idéntico a como
se generaron las imágenes de la fase 2— y pasadas por RapidOCR (`.venv-ai`) y PaddleOCR
(`.venv-paddle`), con la misma configuración de motor que `bench/scripts/ocr_motor.py`.

**Validación del control:** `ctrlppp200` = PDF original sin tocar, rasterizado a 200 ppp.
Reproduce las marcas publicadas **exactamente**, 4 de 4: RapidOCR d2 1,3 % / d3 65,8 %;
PaddleOCR d2 0,0 % / d3 75,9 %. La cadena de medición es fiel.

CER %, RapidOCR:

| receta | patologico | d1 | d2 | **d3** |
|---|---:|---:|---:|---:|
| **ctrlppp200 (marca)** | 1,3 | 0,0 | **1,3** | **65,8** |
| base (OCRmyPDF sin banderas) | 1,3 | 0,0 | 44,3 | 73,4 |
| `--deskew` | 1,3 | 0,0 | 44,3 | 73,4 |
| `--clean-final` | 1,3 | 0,0 | 44,3 | 73,4 |
| `--rotate-pages` | 1,3 | 0,0 | 44,3 | 73,4 |
| los tres juntos | 1,3 | 0,0 | 44,3 | 73,4 |
| `--oversample 300` | 1,3 | 0,0 | 1,3 | **58,2** |
| `--oversample 400` | 1,3 | 0,0 | 1,3 | 59,5 |
| deskew magick (sin OCRmyPDF) | 1,3 | 0,0 | 0,0 | 73,4 |

CER %, PaddleOCR:

| receta | patologico | d1 | d2 | **d3** |
|---|---:|---:|---:|---:|
| **ctrlppp200 (marca)** | 0,0 | 0,0 | 0,0 | **75,9** |
| base y **todas** las recetas de preprocesado | 0,0 | 0,0 | 0,0 | **75,9** |
| `--oversample 300 / 400` | 0,0 | 0,0 | 0,0 | 75,9 |
| **deskew magick (sin OCRmyPDF)** | 0,0 | 0,0 | 0,0 | **20,3** |

**Respuesta a la pregunta concreta de la tarea:**

- ¿Baja el 65,8 % de RapidOCR en d3? Marginalmente, **a 58,2 %**, y solo con
  `--oversample`, que no es preprocesado sino re-rasterización.
- ¿Baja el 75,9 % de PaddleOCR? **No. Ni un punto.** Todas las banderas de preprocesado dan
  75,9 % exacto porque, como demuestra §3.2, no alteran la imagen.
- **Peor aún: el paso por OCRmyPDF *degrada*.** RapidOCR en d2 pasa de 1,3 % a 44,3 % de
  CER solo por atravesar el ciclo rasterizar→JPEG q95→Ghostscript→PDF/A de OCRmyPDF. Su
  pasada no es neutra.
- El único preprocesado que sí ayuda —`magick -deskew`, 20,3 % en PaddleOCR— **no es de
  OCRmyPDF**, y es justo lo que OCRmyPDF no sabe hacer.

### 3.4 Fase 4 — aislar la causa: matriz ppp × deskew

Sobre el **PDF original**, sin OCRmyPDF de por medio. CER % en `escaneado_d3`
(original: 100 ppp, inclinado 5°, contraste 38–72 %, JPEG q25):

| ppp de rasterizado | RapidOCR | RapidOCR +deskew | **PaddleOCR** | PaddleOCR +deskew |
|---|---:|---:|---:|---:|
| 75 | 75,9 | **53,2** | 11,4 | 10,1 |
| **100 (nativo)** | 77,2 | 54,4 | **2,5** | 3,8 |
| 125 | 75,9 | 77,2 | 5,1 | **2,5** |
| 150 | 75,9 | 77,2 | 31,6 | 5,1 |
| 175 | 75,9 | 75,9 | 75,9 | **2,5** |
| **200 ← el del arnés** | **65,8** | 73,4 | **75,9** | 20,3 |
| 250 | 70,9 | 72,2 | 75,9 | 55,7 |
| 300 | 77,2 | 75,9 | 75,9 | 58,2 |
| imagen incrustada, **sin rasterizar** | 77,2 | — | **2,5** | — |

Texto realmente recuperado por PaddleOCR en d3:

| condición | salida | CER |
|---|---|---:|
| 200 ppp (la marca) | `DOCUMENTO ESCANEADO` | 75,9 % |
| **100 ppp (nativo)** | `DOCUMENTO ESCANEADO Texto que sola existe como pikeles. Debe recuperarse con OCR.` | **2,5 %** |
| imagen incrustada tal cual | idéntico al anterior | **2,5 %** |
| 200 ppp + deskew magick | `DOCUMENTO ESCANEADO texto que solo existe como uperarse con OCR` | 20,3 % |

Dos errores de un carácter (`solo`→`sola`, `pixeles`→`pikeles`) sobre 79. El documento
"que nadie resolvió" **está resuelto y es perfectamente legible**. Confirmado tres veces de
forma independiente (`ctrlppp100`, `m_ppp100`, `nat`), con salida idéntica.

**Diagnóstico de la causa.** La ganancia no es del preprocesado. Se reparte así:

1. **Prácticamente toda la ganancia es no sobremuestrear.** A los ppp nativos el deskew ya
   no aporta nada (2,5 % sin él, 3,8 % con él): la resolución explica los 73,4 puntos de
   CER recuperados, y el preprocesado, cero. El arnés de la fase 2 rasterizaba a
   200 ppp un PDF cuya imagen incrustada es de 100 ppp: un **×2 de interpolación** que
   convierte el grano JPEG q25 en manchas del tamaño de un trazo y hunde al detector.
   Rasterizar a los ppp nativos (o simplemente extraer la imagen incrustada) lleva
   PaddleOCR de 75,9 % a 2,5 %. Coste: cero — es *menos* trabajo.
2. **El deskew real aporta robustez, no el mínimo.** `magick -deskew 40%` baja el 200 ppp
   de 75,9 % a 20,3 % y aplana la curva: con deskew, PaddleOCR se mantiene ≤5,1 % entre 75
   y 175 ppp, mientras que sin él se derrumba de golpe a partir de 150 ppp. Es el seguro
   contra elegir mal los ppp, no la fuente de la ganancia.
3. **Nada de esto lo aporta OCRmyPDF.** Su `--deskew` es inerte y su `--oversample` va en la
   dirección contraria (sube ppp, que es justo lo que hace daño).

**Asimetría entre motores, que es un hallazgo aparte:** RapidOCR **no resuelve d3 a ninguna
resolución** (mejor caso 53,2 % a 75 ppp + deskew). PaddleOCR sí, con holgura. No es un
problema de preprocesado sino de modelo: RapidOCR corre PP-OCRv5 *mobile*, PaddleOCR corre
PP-OCRv6 *medium*. En degradación severa la diferencia es la que separa "ilegible" de
"legible".

## 4. Velocidad

n=9, mediana, dentro de WSL sobre su FS nativo (`~/ocrx`). Todo `SUCIA` por la sesión de
escritorio remoto activa (picos de GPU 26–44 %); es estructural, y en todo caso OCRmyPDF no
usa GPU, así que solo afecta a la contención de CPU.

| trabajo | mediana | rango |
|---|---:|---|
| d3 `--force-ocr` (base) | **1 480 ms** | 1 120–1 781 |
| d3 `--deskew` | 1 671 ms | 1 503–1 751 |
| d3 `--clean-final` | 2 095 ms | 1 551–2 660 |
| d3 `--rotate-pages` | 4 645 ms | 3 964–5 964 |
| d3 `--oversample 300` | 8 247 ms | 7 661–10 867 |
| d3 deskew+clean+rotate | 5 914 ms | 5 423–7 376 |
| patologico (8,5 MB) base | 7 150 ms | 5 441–7 572 |
| tipico_texto `--skip-text` | 956 ms | 717–10 490 |

**Coste medido de banderas que no hacen nada:** `--rotate-pages` triplica el tiempo (1 480
→ 4 645 ms) para decidir "no change"; el paquete completo lo cuadruplica (5 914 ms) sin
cambiar un solo píxel de la salida.

Invocado **desde Windows** vía `wsl.exe`, que es lo que pagaría FileX (arnés
`bench/lib/harness.sh`, n=9):

| trabajo | mediana | etiqueta |
|---|---:|---|
| `wsl -- ocrmypdf --version` (coste del puente) | 625 ms | SUCIA (pico 44 %) |
| `wsl -- ocrmypdf` d3, entrada en `/mnt/d` | **2 181 ms** | SUCIA (pico 26 %) |
| `wsl -- ocrmypdf` d3, entrada en FS nativo | **1 832 ms** | SUCIA (pico 27 %) |
| `magick -density 100` d3 (nativo Windows) | **544 ms** | SUCIA (pico 26 %) |
| `magick -density 100 -deskew 40%` d3 (nativo Windows) | **1 635 ms** | SUCIA (pico 28 %) |

Sobre la **trampa conocida de `/mnt/d`**: medida y cuantificada. Dentro de WSL, d3 cuesta
1 480 ms en `~` y 1 299 ms en `/mnt/d`; patologico (8,5 MB) 7 150 ms en `~` y 5 708 ms en
`/mnt/d`. **Con ficheros de este tamaño la penalización de `/mnt/d` no se manifiesta** —
queda enterrada bajo los ~430 ms de arranque de Python y el trabajo de Tesseract. Desde
Windows sí se ve: 2 181 ms (`/mnt/d`) frente a 1 832 ms (FS nativo), ~350 ms. Aun así, se
midió todo en el FS nativo por precaución.

## 5. VRAM de pico

**No aplica a OCRmyPDF: es 100 % CPU** (Tesseract sin compilar contra GPU). No se midió, y
no se tomó el lock de GPU para las fases 1 y 2.

Sí se midió, y se documenta aquí porque es coste de la cadena compuesta de la fase 3
(lock de GPU adquirido y liberado en `31_run_ocr.sh` y `42_run_matriz.sh`):

| motor | VRAM base | pico | coste propio |
|---|---:|---:|---:|
| RapidOCR CUDA | 1 632 MiB | 4 047 MiB | **2 415 MiB** |
| PaddleOCR CUDA | 1 640 MiB | 12 025 MiB | **10 385 MiB** |

**Aviso para FileX:** PaddleOCR llegó a **12 025 MiB sobre 12 288 MiB disponibles** — a 263
MiB de agotar la tarjeta. El pico lo provocan las imágenes grandes de la matriz de control
(3 882×5 100 a 600 ppp, que PaddleOCR reescala solo al superar `max_side_limit=4000`).
Refuerza la conclusión de §3.4 desde otro ángulo: **rasterizar por encima de lo necesario
no solo empeora la precisión, casi tumba la GPU.**

## 6. Carga en frío frente a caliente

| medida | tiempo |
|---|---:|
| d3 `--force-ocr` en frío (primera invocación) | **2 871 ms** |
| d3 `--force-ocr` en caliente (segunda) | **1 592 ms** |
| coste fijo de arranque: `ocrmypdf --version`, sin trabajo | **434 ms** |

El diferencial frío→caliente es de ~1 280 ms (importación de Python, `libgs`, tessdata
`spa`+`osd` desde disco). No se pudo purgar `/proc/sys/vm/drop_caches` (sin sudo sin
contraseña), así que el "frío" es el de una caché de página ya tibia: **el frío real de un
arranque de máquina será mayor**.

El **suelo de 434 ms por invocación** es lo relevante para FileX: OCRmyPDF es un proceso de
un solo disparo, sin modo servidor. Convertir 500 documentos son 500 arranques de Python.
Comparar con RapidOCR/PaddleOCR, que pagan la carga una vez (21–52 s RapidOCR, 34–168 s
PaddleOCR en frío la primera vez) y luego amortizan.

## 7. Verificación de `.venv-ai` (regla 3)

Tras todo el trabajo:

```
torch 2.6.0+cu124
cuda_disponible True
dispositivo NVIDIA GeForce RTX 3060
```

`.venv-paddle`: `paddle 3.2.0`, `compilado_con_cuda True`, `gpus 1`.
Lock de GPU liberado. **No se instaló nada en ningún venv** — solo se ejecutaron.
Todo lo instalado vive en el espacio de nombres de WSL, ya presente antes de empezar.

## 8. Veredicto

### ¿Entra OCRmyPDF en FileX? No como preprocesador. Quizá como empaquetador de PDF/A.

**Como preprocesador de OCR: NO.** Es la respuesta directa a la pregunta de la tarea, y no
por medio punto de CER sino por construcción:

- `--remove-background`: `NotImplementedError`. No existe.
- `--deskew`: inerte. Delega en `tesseract --psm 2`, que devuelve `Deskew angle: 0.0000`
  incluso sobre una página sintética perfecta girada 5° exactos.
- `--clean-final`: llamado con los filtros útiles desactivados; activarlos destruye el texto.
- `--rotate-pages`: correcto pero solo múltiplos de 90°, irrelevante aquí, y cuesta ×3.
- Neto: **imagen de salida idéntica bit a bit** en d1–d3, y CER de la cadena idéntico a no
  usarlo — cuando no peor (RapidOCR d2: 1,3 % → 44,3 %).

De las cuatro banderas que motivaban la prueba, **una está sin implementar, una es un
no-op, una es inaplicable y la cuarta hace daño si se le da potencia.**

**Como motor: NO**, como estaba previsto. CER 100 % en d3 (sidecar vacío).

**Como empaquetador de PDF/A con capa de texto: SÍ, con reservas.** Es lo único que hace
bien y que ningún otro componente del banco hace: PDF de entrada → PDF/A-2b con capa de
texto buscable, `--skip-text` para no pisar el texto existente, sidecar `.txt`. Si FileX
necesita emitir *PDF buscables* (no solo texto extraído), OCRmyPDF es la herramienta, y el
plugin de motor permitiría enchufarle PaddleOCR en lugar de Tesseract. Coste de
integración: 502 MB, WSL o contenedor, ~430 ms de arranque por documento, y un aviso
permanente de Ghostscript en `stderr` que hay que filtrar. En ese papel **no toca el
hueco 5**.

### La conclusión NO es "añadir OCRmyPDF" ni "añadir una etapa de preprocesado"

Es la tercera opción, que no estaba en el guion:

> **FileX debe elegir la resolución de rasterización a partir de los ppp reales de la
> imagen incrustada, y por defecto NO sobremuestrear.**

Esto es un hallazgo de arquitectura, y es más barato que las dos alternativas:

- **Es una decisión, no una etapa.** No añade un binario, ni una dependencia, ni una
  pasada de imagen. Es leer los ppp del `XObject` del PDF y no multiplicarlos. Cuesta
  *menos* CPU que lo que se hace ahora, y menos VRAM (§5).
- **Su efecto es de otro orden de magnitud.** PaddleOCR en dificultad 3: **75,9 % → 2,5 %
  de CER**. El mejor preprocesado real medido (`magick -deskew`) llega a 20,3 %. La
  resolución correcta gana por ocho veces al mejor preprocesado.
- **Camino óptimo, además, ya conocido:** para un PDF de una sola imagen escaneada, el
  mejor resultado se obtiene **extrayendo la imagen incrustada sin rasterizar en absoluto**
  (`pdfimages -png`) — 2,5 % de CER, sin Ghostscript, sin interpolación y sin decidir ppp.

**Un deskew barato sí merece entrar, pero como segundo plato.** `magick -deskew 40%`
(1 635 ms en Windows nativo, sin WSL) no mejora el óptimo, pero **aplana la curva**: con
deskew, PaddleOCR se mantiene ≤5,1 % de CER entre 75 y 175 ppp; sin él se derrumba a 75,9 %
a partir de 150. Es la red de seguridad para cuando los ppp declarados del PDF mienten o
no se pueden leer. Cabe en una llamada a ImageMagick, ya presente en el proyecto — **no
justifica traer OCRmyPDF ni WSL.**

### Consecuencia para `HUECOS.md` hueco 5

**El hueco 5 se reabre, pero por un motivo distinto al que se buscaba, y hay que revisar
las cifras de la fase 2.** Las marcas de dificultad 3 (RapidOCR 65,8 %, PaddleOCR 75,9 %,
EasyOCR 57,0 %) **no miden la capacidad de los motores frente a un documento degradado**:
miden en buena parte un ×2 de interpolación introducido por el arnés. `ctrlppp200`
reproduce esas marcas exactamente (4 de 4), así que la cadena es fiel y el sesgo está
localizado. **Recomendación: repetir la fase 2 rasterizando a los ppp nativos**, con lo que
la conclusión "nadie resuelve la dificultad 3" pasa a ser "PaddleOCR la resuelve con 2,5 %
de CER; RapidOCR no la resuelve a ninguna resolución" — que además da un criterio real de
selección de motor para FileX.

---

## Ficheros

Scripts (ejecutar en orden), en `bench/salidas-ocrmypdf/`:

| script | qué hace |
|---|---|
| `00_entorno.sh` | inventario de versiones y tamaño instalado (WSL) |
| `10_recetas.sh` | 11 recetas × 4 variantes → sidecars + PDF preprocesados (WSL) |
| `11_inspeccion.sh` | error exacto de `--remove-background` y textos crudos |
| `12_porque_no_cambia.sh` | trazas `-v 1`: deskew 0,000 / línea de mando de unpaper |
| `13_deskew_unpaper.sh` | fuente de `preprocess_deskew` + unpaper agresivo |
| `14_control_deskew.sh` | **control**: página sintética nítida girada 5° |
| `20/21_rasterizar*.sh` | saca los PDF de WSL y rasteriza a 200 ppp + controles de ppp |
| `30_ocr_cadena.py` | pasa las imágenes por RapidOCR/PaddleOCR y calcula CER |
| `31_run_ocr.sh` | fase 3 con lock de GPU |
| `40/41_*.sh` | matriz ppp × deskew + extracción de la imagen incrustada |
| `42_run_matriz.sh` | fase 4 con lock de GPU |
| `50_velocidad.sh` | medianas n=9 dentro de WSL, frío/caliente, `/mnt/d` |
| `60_tablas.py`, `61_cer_motor.sh` | tablas de CER |
| `70_cierre.sh`, `71_disco.sh` | coste en disco, puente WSL, verificación de venvs |

Salidas: `pdf/` (41 PDF de OCRmyPDF + `pdf/ctrl/` con los originales), `img/` (65 PNG a 200 ppp),
`img2/` (69 PNG de la matriz ppp × deskew), `sidecar/` (texto de Tesseract),
`texto/` (texto de RapidOCR/PaddleOCR + `*_cer.json`), `logs/` (todas las trazas).

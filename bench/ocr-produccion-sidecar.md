# El sidecar de OCR en producción: el precio del reciclado y la configuración que lo evita

**Agente G5 · 2026-08-28 · encargos B26 y B11**
Salidas y arneses: `bench/salidas-ocr-produccion/` · Informe: este fichero.

---

## 0. Lo que hay que llevarse

1. **MEDIDO — el atasco se reproduce en 2 de 3 motores, y el tercero es inmune.**
   Un folio de 4,35 Mpx deja a **EasyOCR** en +4 442 MiB sobre su base y a **PaddleOCR**
   en +3 048, **y ahí se quedan**: cinco páginas de 1,25 Mpx después, con 20 s de espera
   entre ellas, las cinco lecturas caen dentro de **±43 MiB**, que es el ruido de fondo
   medido (§3.1). **RapidOCR ONNX no se atasca**: pasa de +945 a +1 457 y **no vuelve a
   crecer ni con un folio de 8,88 Mpx**.
2. **MEDIDO — y la variable no es la que decía el pendiente. No es el número de páginas
   ni los megapíxeles acumulados: es el megapíxel del documento MAYOR.** Veinte páginas
   de 1,25 Mpx seguidas —24,97 Mpx acumulados— dejan la VRAM **plana**: el recorrido de
   los tres motores en 20 celdas es de **39, 41 y 42 MiB**, y la pendiente por página es
   de **+0,05 a +0,43 MiB**. Un recuento de páginas o de megapíxeles acumulados **no
   predice nada**.
3. **MEDIDO, y esto REFUTA una de las tres salidas que proponía `k-por-motor.md` §6.3:
   «procesa en orden ascendente de tamaño» es el PEOR orden.** Llegando al mismo folio de
   8,88 Mpx en escalera (0,55 → 1,25 → 2,22 → 4,35 → 8,88) EasyOCR retiene **9 646 MiB**;
   llegando **directo**, **4 296**. **×2,25 y +5 350 MiB por el camino, con el mismo
   documento mayor.** PaddleOCR: 6 626 frente a 4 887, **×1,36**. RapidOCR: **×0,98**, es
   decir nada. **El signo se conserva en una segunda tanda independiente** (fases veneno
   y control de la tanda A: +3 354 y +1 124 MiB), que es lo que exige la trampa 36.
4. **MEDIDO — reciclar el proceso cuesta 4,08 s (RapidOCR), 6,74 (EasyOCR) y 7,05
   (PaddleOCR)**, n=9 con un proceso por repetición y la primera descartada. Contra un
   régimen estacionario de 0,31 / 0,75 / 0,31 s por página, **reciclar cada 13, 9 y 23
   páginas dobla el coste**; para quedarse en un +10 % hay que reciclar cada **131, 90 y
   229 páginas**.
5. **MEDIDO — el criterio de reciclado tiene que ser de VRAM LIBRE, y sale una fórmula
   de una línea por motor.** El coste propio es lineal en los megapíxeles del documento:
   **1 080 MiB/Mpx (EasyOCR, r²=0,957)**, **719 (PaddleOCR, r²=0,9995)** y **109
   (RapidOCR, saturado)**. Con los 6 000 MiB libres que el `GPU_GUARD` exige, eso da
   **4,50 Mpx para EasyOCR y 7,37 para PaddleOCR** — y **un A4 a 300 ppp son 8,70 Mpx**,
   así que el límite ya muerde en el caso normal.
6. **MEDIDO — el criterio del hito 6 NO es alcanzable como está escrito, y no por el
   número: por la forma.** «El pico de VRAM no supera los ~8,7 GB con dos modelos
   residentes más NVENC» supone que el pico es función de **qué modelos hay cargados**.
   La medida dice que es función del **documento mayor que ese proceso haya visto** y del
   **camino**. Con `large-v3` + RapidOCR + NVENC el total sale **10,0 GB**; con PaddleOCR
   sobre un folio de 8,88 Mpx, **12,4 GB**, es decir la tarjeta entera. §6 propone la
   reescritura, con las tres rectas dentro.
7. **MEDIDO — B11 aplicado, y el saldo es 14 mejor / 3 igual / 3 peor sobre 20
   documentos** (métrica **`acentos`**, `bench/scripts/ocr_eval.py`). Reproduce las dos
   regresiones que `ppp-y-normalizacion.md` §4 declaró (`d4a` +5,90 frente a su +5,87;
   `d4f` +1,00 frente a +1,01) **y encuentra una tercera, mayor que las dos suyas**:
   `realista_d5e` **+7,40**, sobre un documento que su corpus no incluía. **La vía
   anterior sigue accesible con `RO_LEGADO=1`.**
8. **MEDIDO — y B11 resuelve B26 de paso.** El motor que el A/B elige es el único de los
   tres que **no necesita reciclarse nunca por VRAM**. El sidecar deja de necesitar una
   política de reciclado cuando el motor tiene techo propio; la necesita, y cara, cuando
   no lo tiene.
9. **MEDIDO — un campo de trazabilidad de dos informes publicados es basura.** La sonda
   de pesos de `ocr_lote_pn.py` y `ocr_lote_km.py` devuelve
   `ch_PP-OCRv4_det_mobile.onnx` en **las 10 configuraciones de `salidas-ppp-norm/json/`
   y en las 6 de `salidas-k-motor/json/`**, incluidas las de PP-OCRv5 y PP-OCRv6, porque
   busca por expresión regular dentro de `session.model_info`, que **no es el modelo
   cargado sino el CATÁLOGO entero** y empieza por PP-OCRv4. El camino bueno,
   sondeado, es `session.session._model_path`. **No invalida ningún CER** —el modelo
   pedido sí quedaba registrado— pero el campo que decía cuál se cargó **nunca dijo la
   verdad**.
10. **MEDIDO — «arranca en 3,7 s en vez de 18,4» ya no vale, y la diferencia se ha
    encogido.** Medido **pareado, en la misma tanda**: RapidOCR v6 small + R6 arranca en
    **4,085 s** y PaddleOCR en **7,048**. Son **×1,73**, no ×5. Los 18,4 s no se
    reproducen.

**PENDIENTE, y se dice al principio:** todo lo de VRAM está medido con **un solo
documento base** (`escaneado_d4`) reescalado, en **una** tarjeta y con **una** versión de
cada motor; y el modelo lineal MiB/Mpx se ajusta sobre **cinco** puntos por motor.

---

## 1. Cómo se midió

### 1.1 El lock de GPU, que es responsabilidad del agente y no del arnés

`CLAUDE.md` deja escrito que **0 de 15 arneses `.py` toman el lock**. Aquí no se ha
arreglado eso —no es el encargo— pero **no se ha repetido**: los cinco arneses `.py` de
este informe se invocan **siempre** desde un `.sh` que hace `source bench/lib/harness.sh`
y envuelve la tanda entera en `gpu_acquire … gpu_release`, con `trap` de salida.
`bench/lib/harness.sh` se ha **usado y no editado**.

| tanda | script | qué mide | lock |
|---|---|---|---|
| A | `run_a_veneno.sh` | el atasco (fase `veneno`) y su control positivo (fase `control`) | sí |
| B | `run_b_b11.sh` | A/B de configuración de RapidOCR, 21 documentos, n=9 | sí |
| C | `run_c_frio.sh` | arranque en frío, 8 configuraciones × n=10 procesos | sí |
| D | `run_d_criterio.sh` | fases `repetido`, `ascendente` y `directo` | sí |
| E | `run_e_verif.sh` | verificación del instrumento (CPU, sin GPU) | no aplica |

**`timeout` explícito en las 5 plantillas de invocación de motor de los `.sh`**, que
cubren las **100 ejecuciones** de esta ronda (98 de `sidecar_op.py` y 2 de
`ocr_motor.py`). Ningún proceso quedó colgado.

### 1.2 Los dos testigos, con tope propio

Cada corrida mide **deriva** (bucle monohilo) y **nivel** (mediana de 5 `ffprobe
-version`) al principio y al final, y etiqueta `limpia`/`SUCIA` con umbral 1,30 en
cualquiera de los dos. El testigo de proceso lleva **tope propio de 20 s** y, si lo
agota, devuelve el tope y la tanda sale `SUCIA`: un testigo que puede tumbar la medición
no es un testigo.

**Resultado: 7 de las 98 corridas de `sidecar_op.py` salieron `SUCIA`.** Seis son celdas
sueltas de la tanda C —`C_easyocr_cpu_i2`, `C_paddleocr_cpu_i5`, `C_ro5mob_def_cpu_i4` y
`_i7`, `C_ro6small_R6_cpu_i2`, `C_ro6small_R6_cuda_i6`, con deriva 1,18-1,40 o nivel
1,36-1,45— y **no se descartan**: la tanda C publica **medianas de 9**, que es
precisamente la defensa contra una celda ruidosa. La séptima es
**`D_paddleocr_ascendente`** (deriva 1,42), y esa sí es una fila publicada: se acepta
porque su serie de VRAM cae en la recta a **r²=0,9995** y el efecto medido —6 626 MiB—
es dos órdenes de magnitud mayor que el ruido de VRAM observado (41 MiB en 20 celdas).
**Sus tiempos no se usan para nada.**

**Y un defecto propio que hay que declarar: `ocr_motor.py` NO lleva los dos testigos**, y
la tanda B (el A/B de B11) corre sobre él. No se le han añadido porque es arnés
compartido y ampliar su contrato es un cambio aparte. **Consecuencia honesta: los CER de
§7.2 son deterministas y no dependen del ruido, pero los milisegundos de §7.3 son de una
tanda sin testigos y solo valen como cifra RELATIVA dentro de ella.** Queda **PENDIENTE**.

### 1.3 El reloj, antes de cronometrar

`time.get_clock_info` en cada corrida: `perf_counter` da **1e-07 s** y `time` da
**0,015625 s**. Todo lo que se cronometra aquí usa `perf_counter`; el tic de 15,625 ms de
`time.time()` habría sido el 5 % de una página de RapidOCR.

### 1.4 La métrica de CER, declarada

**`bench/scripts/ocr_eval.py`, métrica `acentos`** —la canónica desde el 2026-08-28—,
**importado, no copiado**. `evaluar()` devuelve `metrica` en cada celda y el evaluador de
este informe la propaga a cada fila del saldo. Las cifras de CER de §7 llevan **un
decimal**, que es lo que `ocr_eval.py` publica; las tablas de `ppp-y-normalizacion.md`
llevan dos porque las produjo `ocr_eval_d4.py`. **Al comparar las dos, la diferencia de
±0,05 es de redondeo.**

Dos referencias, y no son intercambiables: la **legado** de 79 caracteres (sin un solo
diacrítico, paso de 1,27 puntos por carácter) y la de **`d4_texto.BLOQUES`**, 610
caracteres con tildes, paso 0,17. Cada fila publica cuál usó.

### 1.5 Las constantes declaradas

- **Vía de entrada: RUTA** en los tres motores. La trampa 30 dice que vale hasta 12,58
  puntos; aquí es una **constante** de todo el informe, no una variable.
- **Rasterizador: Ghostscript 10.07**, `pnggray`, un solo motor (ImageMagick delega en
  él). **No se declara `pHYs`**, y la omisión es deliberada: los tres motores de este
  informe son inmunes (trampa 29).
- **Dispositivo fijado** en cada corrida (trampa 11). Las tandas de VRAM son todas
  `cuda`; la tanda C mide las dos y lo dice en el nombre.
- **ppp NATIVOS** en el corpus de B11, sacados de `MANIFIESTO-d4.md` y `MANIFIESTO-d5.md`.
  **No se aplica la regla R1 a propósito**: la variable del A/B es el par (checkpoint,
  normalización) y los ppp tienen que ser constantes entre las dos ramas.

### 1.6 La base de escritorio de estas tandas — salvedad importante

`CLAUDE.md` documenta que el escritorio ocupa **3 292–3 448 MiB**. **En estas tandas
ocupaba 1 175–1 864 MiB** (leído al arrancar cada proceso). Todas las cifras de este
informe son **`delta` sobre la base del propio proceso**, así que el coste propio del
motor es comparable; **pero el margen absoluto no lo es, y eso importa en §6**: la celda
más cara de todas (EasyOCR, 9 646 MiB de coste propio) **no habría cabido** con la base
documentada — 3 448 + 9 646 = 13 094 MiB sobre una tarjeta de 12 288.

---

## 2. B26 · El atasco, reproducido y con su control

**Diseño (fase `veneno`):** 3 páginas de 1,25 Mpx → **1 folio de 4,35 Mpx** → 5 páginas
de 1,25 Mpx **con 20 s de espera entre ellas** → 1 folio de 8,88 Mpx → 1 página de
1,25 Mpx. La fase `control` es idéntica **sin el folio de 4,35**: sin ese control
positivo, un «no devuelve memoria» no significa nada (trampa 36).

Todas las celdas devolvieron texto y **ninguna dio error** — se registra el error de cada
celda precisamente porque una salida vacía y un proceso que no arrancó se parecen
(trampa 25).

### 2.1 Con el folio grande — MEDIDO, `delta` sobre la base del proceso

| paso | Mpx | nota | RapidOCR | PaddleOCR | EasyOCR |
|---:|---:|---|---:|---:|---:|
| 1-3 | 1,248 | antes | 689 → **945** | 977 → **1 106** | 1 190 → **1 233** |
| 4 | **4,352** | el folio grande | **1 457** | **3 048** | **4 442** |
| 5-9 | 1,248 | después, con 20 s entre cada una | 1 457 · 1 516 · 1 480 · 1 480 · **1 454** | 3 048 · 3 048 · 3 089 · 3 091 · **3 048** | 4 442 · 4 442 · 4 485 · 4 442 · **4 442** |
| 10 | **8,882** | el folio mayor | **1 454** | **6 710** | **8 145** |
| 11 | 1,248 | después | 1 454 | 6 710 | 8 104 |

**Las cinco lecturas del paso 5 al 9 son el hallazgo:** entre ellas hay **80 segundos de
espera repartidos**, y las cinco de cada motor caben en **±43 MiB** — es decir, sobre un
pico de 3 048 y 4 442 MiB, **el asignador no devuelve nada distinguible del ruido**.
Reproduce `k-por-motor.md` §6.3 con otro arnés y otro corpus. *(Ese informe lo enunció
como «ni un solo MiB en 24 muestras»; con el ruido de fondo medido aquí, lo defendible
es «nada por encima de ±43 MiB» — §8.3.)*

**Y lo que ese informe no separaba: RapidOCR no se atasca.** Su +1 457 después del folio
de 4,35 Mpx **es el mismo +1 454 después del de 8,88** — no crece porque **no ve** el
folio entero: `Global.max_side_len: 2000` lo recorta antes del detector. Su techo no es
una política del sidecar: es una propiedad del motor.

### 2.2 Sin el folio grande — el control positivo

| paso | Mpx | RapidOCR | PaddleOCR | EasyOCR |
|---:|---:|---:|---:|---:|
| 1-8 | 1,248 (ocho seguidas) | 680…**926** | 937…**1 110** | 1 185…**1 129** |
| 9 | **8,882** | **1 436** | **5 586** | **4 791** |

**Ocho páginas seguidas dejan la VRAM donde estaba** —EasyOCR incluso **baja** de 1 226 a
1 129—, así que lo que la mueve no es procesar, es procesar **algo grande**.

Y comparando las dos tablas aparece el segundo hallazgo, que §3.3 aísla: el **mismo**
folio de 8,88 Mpx deja **8 145 MiB** si antes pasó por el de 4,35 y **4 791** si no.

---

## 3. B26 · Con qué variable crece — las cuatro preguntas

### 3.1 ¿Con el número de páginas? — **NO**

Fase `repetido`: la **misma** página de 1,248 Mpx, **20 veces**, sin esperas.

| motor | páginas | Mpx acumulados | delta 1.ª | delta 20.ª | **recorrido** | pendiente MiB/página |
|---|---:|---:|---:|---:|---:|---:|
| EasyOCR | 20 | 24,968 | 1 187 | 1 187 | **42** | **+0,05** |
| PaddleOCR | 20 | 24,968 | 936 | 1 147 | **41** | **+0,43** |
| RapidOCR | 20 | 24,968 | 689 | 949 | **39** | **+0,27** |

*(El salto de la 1.ª a la 2.ª celda es la reserva inicial del motor; el régimen
estacionario empieza en la 2.ª y la pendiente se ajusta sobre él.)*

**Un contador de páginas no sirve como criterio de reciclado**: a este ritmo harían falta
más de **veinte mil** páginas para que EasyOCR retuviera lo que retiene con **un** folio
de 4,35 Mpx.

### 3.2 ¿Con los megapíxeles acumulados? — **NO, y es la misma tabla**

Los mismos 20 pasos acumulan **24,968 Mpx**, casi tres veces el folio de 8,88 que sí
mueve 4 000 MiB. La VRAM no se entera. **Los megapíxeles acumulados no son una
magnitud del asignador.**

### 3.3 ¿Con los megapíxeles del documento MAYOR? — **SÍ, y es lineal**

Fase `ascendente`, un proceso por motor: 0,550 → 1,248 → 2,221 → 4,352 → 8,882 Mpx.

| motor | serie (Mpx → MiB) | **MiB/Mpx** | ordenada | r² |
|---|---|---:|---:|---:|
| EasyOCR | 0,55→682 · 1,25→1 636 · 2,22→3 298 · 4,35→6 571 · 8,88→**9 646** | **1 080** | 641 | 0,9571 |
| PaddleOCR | 0,55→608 · 1,25→1 118 · 2,22→1 830 · 4,35→3 236 · 8,88→**6 626** | **719** | 202 | 0,9995 |
| RapidOCR | 0,55→556 · 1,25→688 · 2,22→944 · 4,35→1 456 · 8,88→**1 456** | 109 | 643 | 0,7581 |

**PaddleOCR es lineal a r²=0,9995 sobre cinco puntos y un factor 16 de tamaño.** El r²
malo de RapidOCR **no es ruido: es la saturación** — sus cuatro primeros puntos son
lineales (109 MiB/Mpx no describe nada, la recta es una cota superior floja) y el quinto
**no se mueve**, porque el recorte a 2 000 px hace que 4,35 y 8,88 Mpx sean el mismo
array. **Para RapidOCR el modelo correcto no es una recta: es `min(recta, 1 526)`.**

**Y el aviso operativo:** en esa celda EasyOCR dejó **728 MiB libres de 12 288** y
**devolvió texto sin dar ningún error**. Es exactamente el modo de fallo que el proyecto
ya tenía anotado, esta vez con el margen medido.

### 3.4 ¿Y con el CAMINO? — **SÍ, y es lo que refuta el pendiente**

Fase `directo`: el folio de 8,88 Mpx **dos veces seguidas**, sin pasar por los
intermedios. Es la esquina que le faltaba al factorial: sin ella no se puede atribuir si
la VRAM la fija el máximo visto o **también** el camino.

| motor | en escalera (MiB) | directo (MiB) | diferencia | ratio |
|---|---:|---:|---:|---:|
| **EasyOCR** | **9 646** | **4 296** | **+5 350** | **×2,25** |
| **PaddleOCR** | **6 626** | **4 887** | **+1 739** | **×1,36** |
| RapidOCR | 1 456 | 1 487 | −31 | ×0,98 |

**Réplica independiente, exigida por la trampa 36** (una diferencia entre dos totales
necesita que el signo se conserve en otra tanda). Las fases `veneno` y `control` de la
tanda A miden lo mismo con otro camino —8,88 Mpx **con** y **sin** un 4,35 previo— y dan:

| motor | tras 4,35 (MiB) | sin él | diferencia | ¿mismo signo? |
|---|---:|---:|---:|---|
| EasyOCR | 8 145 | 4 791 | **+3 354** | **sí** |
| PaddleOCR | 6 710 | 5 586 | **+1 124** | **sí** |
| RapidOCR | 1 454 | 1 436 | +18 | irrelevante (ruido: 39-42 MiB) |

**Consecuencia, y es una refutación:** `k-por-motor.md` §6.3 proponía tres salidas —*«o
procesa en orden ascendente de tamaño, o presupuesta la VRAM por lote, o recicla el
proceso»*—. **La primera es la peor de las tres.** Procesar en orden ascendente hace que
el asignador vea todos los tamaños intermedios y no reutilice ninguno: cuesta **+5 350
MiB en EasyOCR** frente a ir directo al mayor. Si hay que ordenar el lote, el orden que
sale de esta medida es **descendente**, no ascendente — el bloque grande primero, y el
resto cabe en lo ya reservado.

---

## 4. B26 · Cuánto cuesta reciclar, y cada cuántas páginas sale a cuenta

### 4.1 El arranque en frío — 8 configuraciones, un proceso por repetición

n=10 procesos por configuración, **la primera descartada** (Windows Defender infla el
primer arranque, trampa 7), medianas de las 9 restantes. Medir el arranque en frío
**dentro** de un proceso de vida larga no lo mide: por eso es un proceso por repetición.

| configuración | n | import s | construcción s | **frío s** | 1.ª página ms |
|---|---:|---:|---:|---:|---:|
| RapidOCR v6 small +R6 · **cpu** | 9 | 3,613 | 0,374 | **3,987** | 1 206,0 |
| RapidOCR v6 small +R6 · cuda | 9 | 3,575 | 0,537 | **4,085** | 1 038,5 |
| RapidOCR v5 mobile def. · cpu | 9 | 3,810 | 0,398 | **4,194** | 1 262,1 |
| RapidOCR v5 mobile def. · cuda | 9 | 3,657 | 0,715 | **4,308** | 961,6 |
| PaddleOCR · cpu | 9 | 3,681 | 2,018 | **5,646** | 4 723,5 |
| EasyOCR · cpu | 9 | 4,379 | 2,190 | **6,583** | 5 730,0 |
| EasyOCR · cuda | 9 | 4,363 | 2,354 | **6,743** | 1 061,2 |
| PaddleOCR · cuda | 9 | 4,073 | 2,956 | **7,048** | 848,5 |

Tres cosas que solo se ven al desglosar:

- **El `import` domina: de 3,6 a 4,4 s de los 4 a 7 totales.** Es coste de Python y de
  las bibliotecas nativas, no de los pesos. Un sidecar que recicle **forkeando** un
  proceso ya importado se ahorraría la mitad larga del coste; en Windows no hay `fork`,
  así que **eso es un pendiente con nombre**, no una solución.
- **La construcción del modelo separa a los motores mucho más que el import:** 0,37-0,72 s
  en RapidOCR frente a 2,0-3,0 en PaddleOCR y EasyOCR. **×5,5.**
- **Reciclar en CPU es más barato que en GPU** para los tres (no hay que reservar
  contexto CUDA), pero la primera página cuesta **×4,5 a ×5,6** más. La CPU solo compensa
  si el sidecar procesa **una** página por proceso, que es justo el caso de la CLI.

### 4.2 La amortización

Régimen estacionario tomado de la fase `repetido` (20 celdas, sin la primera):
RapidOCR **310,8 ms**, PaddleOCR **307,9 ms**, EasyOCR **750,4 ms** por página de
1,25 Mpx en GPU.

| motor | frío s (GPU) | ms/página | páginas para **+10 %** | +25 % | +50 % | **+100 %** |
|---|---:|---:|---:|---:|---:|---:|
| RapidOCR | 4,08 | 310,8 | **131** | 53 | 26 | **13** |
| PaddleOCR | 7,05 | 307,9 | **229** | 92 | 46 | **23** |
| EasyOCR | 6,74 | 750,4 | **90** | 36 | 18 | **9** |

**Cómo se lee:** reciclar cada 13 páginas dobla el coste de RapidOCR; reciclar cada 131
lo encarece un 10 %. **Y el número que decide no es este:** con PaddleOCR, **una** página
de 8,88 Mpx obliga a reciclar, y ninguna política de «cada N páginas» lo habría visto
venir. El contador de páginas es un mal criterio también por aquí.

---

## 5. B26 · Cuándo reciclar — los tres criterios, medidos

| criterio | ¿predice el atasco? | coste de medirlo | veredicto |
|---|---|---|---|
| **número de páginas** | **No.** 20 páginas mueven 39-42 MiB; **una** página grande mueve 4 000 | 0 | **descartado** |
| **Mpx acumulados** | **No.** 24,97 Mpx acumulados < 1 folio de 8,88 | 0 | **descartado** |
| **Mpx del documento mayor visto** | **Sí**, y con recta (r² 0,957 / 0,9995) | 0 (se sabe antes de procesar) | **sirve para ADMITIR** |
| **VRAM libre total** | **Sí**, es el estado real | ~30-60 ms de `nvidia-smi` | **sirve para DECIDIR** |

**Los dos últimos no compiten: se combinan, y cada uno hace una mitad.** La VRAM libre
dice cuánto queda **ahora**; la recta dice cuánto va a costar **la página siguiente**, y
eso se sabe **antes** de procesarla, que es lo único que permite evitar el atasco en vez
de descubrirlo. Y la VRAM **por PID no es observable** en esta máquina (trampa 31): el
total es lo único que hay.

### 5.1 La regla, con sus números

```
antes de cada página:
    coste_previsto = ordenada[motor] + pendiente[motor] * mpx_pagina     # MiB
    if coste_previsto + MARGEN > vram_libre_total():
        reciclar_proceso()          # 4,1-7,0 s, medido en 4.1
        # y si aun asi no cabe, el documento no cabe en esta maquina: se
        # rechaza o se baja de ppp. Reciclar dos veces seguidas no ayuda.
```

| motor | ordenada MiB | MiB/Mpx | tope propio | Mpx admisibles con 6 000 MiB libres | con 4 000 | con 2 000 |
|---|---:|---:|---:|---:|---:|---:|
| EasyOCR | 641 | **1 080** | ninguno | **4,50** | 2,65 | 0,80 |
| PaddleOCR | 202 | **719** | ninguno | **7,37** | 4,59 | 1,80 |
| RapidOCR | 643 | 109 | **1 526 MiB** | sin límite práctico | sin límite | sin límite |

*(margen de seguridad 500 MiB. Los 6 000 MiB no son un número inventado: es el umbral de
aborto de `GPU_GUARD`.)*

**Y el tamaño de referencia que hace falta para leer la tabla: un A4 rasterizado a
150 ppp son 2,18 Mpx; a 200 ppp, 3,87; a 300 ppp, 8,70.** Es decir: **con EasyOCR y
6 000 MiB libres, un A4 a 300 ppp ya no entra**, y con 4 000 libres no entra ni a
200 ppp. Con RapidOCR entra cualquiera.

### 5.2 Y la conclusión de arquitectura, corregida

La regla que `k-por-motor.md` dejó escrita sin número es:

> *«el sidecar de OCR no puede ser un proceso de vida larga con documentos de tamaño
> arbitrario»*

**MEDIDO, sigue siendo cierta, y ahora se puede decir mejor: es una regla POR MOTOR, no
del sidecar.** Con RapidOCR ONNX + PP-OCRv6 small el proceso puede vivir indefinidamente
—su techo de VRAM es **1 526 MiB** para cualquier documento medido hasta 8,88 Mpx— y
**no hace falta reciclar nunca por memoria**. Con PaddleOCR o EasyOCR hace falta, cuesta
**7,05 / 6,74 s** cada vez, y la decisión hay que tomarla **antes** de cada página.

---

## 6. B26 · Qué le pasa al hito 6

**El criterio actual** (`PLAN-ORQUESTADOR.md`, hito 6):

> *«los modelos se descargan por inactividad y el pico de VRAM no supera los ~8,7 GB con
> dos modelos residentes más NVENC»*

### 6.1 ¿Es alcanzable? — depende del motor, y con dos de tres NO

Presupuesto con las cifras publicadas del proyecto (escritorio **3 448 MiB** en su peor
caso medido; NVENC 4K **743**; whisper `large-v3` **4 525**, `distil-large-v3` **1 847**)
y el coste propio de OCR medido aquí:

| escenario | escritorio | modelo 1 | OCR | NVENC | **total** | ¿≤ 8,7 GB? |
|---|---:|---:|---:|---:|---:|---|
| distil + **RapidOCR** + NVENC | 3 448 | 1 847 | **1 526** | 743 | **7 564** | **sí** (7,4 GB) |
| `large-v3` + **RapidOCR** + NVENC | 3 448 | 4 525 | **1 526** | 743 | **10 242** | **no** (10,0 GB) |
| distil + **PaddleOCR** @8,88 Mpx + NVENC | 3 448 | 1 847 | **6 626** | 743 | **12 664** | **no: no cabe en la tarjeta** |
| **EasyOCR** @8,88 Mpx en escalera, **solo** | 3 448 | — | **9 646** | — | **13 094** | **no: no cabe en la tarjeta** |

**La última fila es la que cierra la pregunta.** Con **un** modelo, **sin** NVENC y
**sin** segundo residente, EasyOCR sobre un folio a 300 ppp **ya no cabe** con la base de
escritorio documentada. Aquí cupo por 728 MiB **porque ese día el escritorio ocupaba
1 742 MiB en vez de 3 448**.

### 6.2 Por qué hay que reescribirlo, y no solo bajarle el número

El criterio supone que **el pico de VRAM es una propiedad del conjunto de modelos
residentes**. Las cuatro medidas de §3 dicen que no lo es:

- **no depende de cuántas páginas lleve el proceso** (§3.1: 39-42 MiB en 20 páginas),
- **sí depende del documento mayor que ese proceso haya visto** (§3.3: 719-1 080
  MiB/Mpx),
- **y también del camino** (§3.4: ×2,25 por llegar en escalera),
- **y no se recupera esperando** (§2.1: cinco lecturas idénticas con 80 s por medio).

Un criterio de aceptación que no nombra ni el tamaño del documento ni el motor **no se
puede verificar**: la misma implementación lo cumple o no lo cumple según qué PDF le
entre. Es la forma del criterio lo que falla.

### 6.3 La reescritura propuesta — con las tres rectas dentro

> **Aceptación (hito 6), propuesta.** Los modelos se descargan por inactividad. Y sobre
> la VRAM, **tres condiciones en vez de una**:
>
> 1. **Techo declarado por motor.** Cada adaptador de OCR declara su coste propio como
>    `min(ordenada + pendiente × Mpx, tope)` con los valores medidos en
>    `bench/ocr-produccion-sidecar.md` §5.1, y **el sidecar rechaza o recicla antes de
>    procesar** una página cuyo coste previsto más 500 MiB de margen no quepa en la VRAM
>    libre total.
> 2. **El pico total no supera 8,7 GB en el perfil declarado**, y el perfil se declara
>    entero: *(escritorio + modelo de audio + motor de OCR + NVENC)* **y el mayor
>    documento admitido**. Con `distil-large-v3` + RapidOCR ONNX/PP-OCRv6 small + NVENC
>    4K y documentos de hasta 8,88 Mpx: **7 564 MiB, cumple**. Con `large-v3` **no
>    cumple**, y eso ya lo decía `PLAN-ORQUESTADOR.md` §534 (*«no caben dos
>    `large-v3`»*): ahora también se sabe que **no cabe uno con OCR y NVENC**.
> 3. **Reciclado obligatorio, con su coste declarado**, para todo motor sin tope propio:
>    **7,05 s (PaddleOCR) y 6,74 s (EasyOCR)**, frente a **0 (RapidOCR)**. Un motor sin
>    tope propio entra en el sidecar **con** su política de reciclado o no entra.
>
> **Y el criterio de precisión sigue siendo el de `escaneado_d4`**: ningún motor bajaba
> del 18,62 %; la configuración de B11 lo deja en **18,60 %** (§7), es decir **el margen
> que el hito 6 tiene que mover sigue intacto**. B11 no lo mueve: lo que mueve son las
> otras 19 filas.

---

## 7. B11 · La configuración de producción, aplicada

### 7.1 Qué cambia, y por qué las dos cosas a la vez

`bench/scripts/ocr_motor.py` fijaba `PP-OCRv5 mobile` con la normalización de fábrica de
RapidOCR. **Ahora fija `PP-OCRv6 small` + R6.** El cambio es de las dos cosas juntas a
propósito: sobre `PP-OCRv5 mobile`, R6 **empeora 4 de 15 celdas**
(`ppp-y-normalizacion.md` §3.3), y el único checkpoint con 0 regresiones es v6 small.
Aplicar R6 sin cambiar de checkpoint sería la trampa 17 otra vez.

**La vía anterior no se ha borrado: `RO_LEGADO=1` la reproduce.** Y las tres piezas se
mueven por separado (`RO_VER`, `RO_TIPO`, `RO_NORM`), porque un CER publicado sin su
checkpoint y su normalización no es un número.

**Lo APLICADO, leído del objeto ya construido** (no de lo pedido):

| | `mean` | `std` | thresh | box_thresh | unclip | max_cand | pesos det / rec |
|---|---|---|---:|---:|---:|---:|---|
| `RO_LEGADO=1` | `[0.5, 0.5, 0.5]` | `[0.5, 0.5, 0.5]` | 0,3 | 0,50 | 1,6 | 1 000 | `ch_PP-OCRv5_det_mobile.onnx` / `ch_PP-OCRv5_rec_mobile.onnx` |
| **vigente** | `[0.485, 0.456, 0.406]` | `[0.229, 0.224, 0.225]` | 0,2 | 0,45 | 1,4 | 3 000 | **`PP-OCRv6_det_small.onnx`** / **`PP-OCRv6_rec_small.onnx`** |

`providers` = `['CUDAExecutionProvider', 'CPUExecutionProvider']` en las dos, leído con
`get_providers()` y nunca con `get_device()` (trampa 13).

**Y el `latin` que la propuesta descartaba, ahora sondeado en ejecución y no deducido:**
`Rec.lang_type='latin'` sobre PP-OCRv6 small **lanza
`ValueError: Unsupported rec.lang_type='latin' for PP-OCRv6 small model.`** La nota del
parche propuesto era correcta; ahora está medida.

### 7.2 El saldo — MEDIDO, 21 documentos a ppp nativos, n=9, GPU, métrica `acentos`

| documento | ppp | ref. | legado | **vigente** | delta | veredicto |
|---|---:|---|---:|---:|---:|---|
| `patologico_escaneado` | 200 | legado | 0,00 | 0,00 | 0,00 | igual |
| `escaneado_d1` | 150 | legado | 0,00 | 0,00 | 0,00 | igual |
| `escaneado_d2` | 100 | legado | 0,00 | 0,00 | 0,00 | igual |
| `escaneado_d3` | 100 | legado | 77,20 | **3,80** | **−73,40** | mejor |
| `escaneado_d4` | 200 | d4 | 41,80 | **18,60** | **−23,20** | mejor |
| `escaneado_d4a` | 200 | d4 | 1,50 | 7,40 | **+5,90** | **peor** |
| `escaneado_d4b` | 200 | d4 | 2,20 | 0,30 | −1,90 | mejor |
| `escaneado_d4c` | 200 | d4 | 15,60 | **1,20** | **−14,40** | mejor |
| `escaneado_d4e` | 200 | d4 | 92,40 | 77,50 | −14,90 | mejor |
| `escaneado_d4f` | 240 | d4 | 6,00 | 7,00 | **+1,00** | **peor** |
| `escaneado_d5` | 72 | d4 | 13,40 | **0,80** | **−12,60** | mejor |
| `escaneado_d5a` | 90 | d4 | 2,00 | 0,30 | −1,70 | mejor |
| `escaneado_d5b` | 60 | d4 | 17,10 | 9,70 | −7,40 | mejor |
| `escaneado_d5c` | 80 | d4 | 4,20 | 0,70 | −3,50 | mejor |
| `patologico_d5a` | 200 | d4 | 11,40 | **0,70** | **−10,70** | mejor |
| `patologico_d5b` | 200 | d4 | 23,30 | **2,30** | **−21,00** | mejor |
| `patologico_d5e` | 200 | d4 | 41,80 | **5,20** | **−36,60** | mejor |
| `realista_d5a` | 200 | d4 | 1,70 | 0,50 | −1,20 | mejor |
| `realista_d5b` | 200 | d4 | 4,00 | 0,70 | −3,30 | mejor |
| `realista_d5e` | 200 | d4 | 26,80 | 34,20 | **+7,40** | **peor** |
| `tipico_texto` | 150 | *(ver §7.4)* | 1,70 | 0,00 | — | **fuera del saldo** |

**SALDO: 14 mejor · 3 igual · 3 peor** (20 documentos con referencia; suma de deltas
**−209,0 puntos**). **Se publica entero, con las tres regresiones.**

### 7.3 Lo que este saldo añade a lo publicado

`ppp-y-normalizacion.md` §4 declaró **7 mejor / 2 igual / 2 peor** sobre 11 documentos.
Aquí, con 20 y otro arnés:

- **Las dos regresiones que declaró se reproducen casi exactas:** `d4a` **+5,90** frente
  a su +5,87 y `d4f` **+1,00** frente a +1,01. Reproducción independiente, con otro
  rasterizador de invocación y otro evaluador.
- **Aparece una TERCERA regresión, y es mayor que las dos suyas:** `realista_d5e`
  **+7,40** (26,80 → 34,20). Es un documento de la familia `d5` que su corpus no
  incluía. **Un saldo de 11 documentos no cubría el peor caso.**
- **Y la ganancia crece donde nadie había mirado:** los cuatro `patologico_d5*` y
  `realista_d5*` aportan **−10,70, −21,00, −36,60, −1,20, −3,30**; y los documentos de
  **bajo ppp** (60-90) aportan **−12,60, −7,40, −3,50, −1,70**. Nada de eso estaba en el
  saldo publicado.

**Y el cambio sale gratis en tiempo y en memoria** (misma tanda, pareado):

| | suma de las 21 medianas | pico VRAM | coste propio | arranque en frío |
|---|---:|---:|---:|---:|
| legado (v5 mobile) | 10 096 ms | 3 282 MiB | 1 538 MiB | 4,308 s |
| **vigente (v6 small + R6)** | **7 672 ms** | 3 283 MiB | 1 541 MiB | **4,085 s** |

**−24 % de tiempo total, +1 MiB de VRAM y −0,22 s de arranque.** Las tres celdas que
empeoran en tiempo son `d4e` (×1,57) y `realista_d5e` (×1,49) —los dos documentos más
degradados, donde el detector con R6 encuentra más cajas— y `d3` (×1,09).

### 7.4 Un defecto del arnés, encontrado y declarado

`tipico_texto.pdf` **no contiene el texto de la referencia legado**. Su capa de texto
dice *«FileX - documento de prueba con texto seleccionable / Segunda linea: acentos
aeiou n ˆ y simbolos % & @ / Tabla: Col A Col B Col C / 1 2 3»*. Un arnés que deduce la
referencia del nombre del fichero le asigna la de 79 caracteres y publica **96,2 %** y
**98,7 %**, que no dicen nada del motor. Es el mismo fallo que
`ppp-y-normalizacion.md` §5 punto 4 documentó sobre `oro__trivial_p1`, en otro fichero.

**Y la referencia obvia tampoco vale:** `gs -sDEVICE=txtwrite` la extrae **ya sin
tildes** (`aeiou n ˆ`), así que penalizaría a un motor que sí las lea. **Se saca del
saldo y se publica marcado** —contra su propia capa de texto, la vía vigente da 0,00 % y
la legado 1,70 %— en vez de inventarle una referencia.

### 7.5 Lo que queda caducado

Ninguna cifra publicada queda caducada por este cambio, y la razón es que **la etiqueta
por defecto del arnés ahora lleva la configuración dentro**
(`motor_rapidocr_cuda_PPOCRv6small_R6-1`), así que las salidas nuevas **no pisan** las
viejas. Lo que sí hay que leer con cuidado:

| informe | qué dice | estado |
|---|---|---|
| `ocr-ppp-nativos.md` §273 | «RapidOCR aislado usa **PP-OCRv5 mobile**» | **caducado como descripción del arnés**; sus CER siguen siendo válidos y reproducibles con `RO_LEGADO=1` |
| `gpu-fase2.md`, `phys-multimotor.md` §175 | usan `ocr_motor.py` como referencia de configuración | **misma nota**: la configuración de la que hablan es la de `RO_LEGADO=1` |
| `consolidacion-2-21ago.md` §236 | «`ocr_motor.py` fija `LangRec.CH`» | **sigue siendo cierto**, y §7.1 explica por qué no se cambia: en PP-OCRv6 `latin` no existe |

---

## 8. Lo que falló, y lo que refuté

1. **Mi primera sonda de pesos mintió, y mintió bonito.** Copiada del patrón de
   `ocr_lote_pn.py`, devolvió `ch_PP-OCRv4_det_mobile.onnx` para `det`, `cls` y `rec`
   **y en las dos configuraciones del A/B**, que es imposible. La causa, sondeada con
   `sonda_pesos.py`: el camino `session.model_info` **no es el modelo cargado, es el
   catálogo entero de modelos descargables**, y su primer `*.onnx` es el de PP-OCRv4. El
   camino real es `session.session._model_path`. **Y el defecto no es mío: está en dos
   arneses publicados** —`bench/salidas-ppp-norm/json/*.json` (10 configuraciones) y
   `bench/salidas-k-motor/json/*.json` (6)— donde ese campo dice PP-OCRv4 en todas.
   **No invalida ningún CER**, porque el modelo pedido sí quedaba registrado aparte y el
   log de arranque de RapidOCR nombra el fichero real; invalida **el campo que servía
   para no tener que fiarse del log**.
2. **REFUTADO: «procesa en orden ascendente de tamaño»** (`k-por-motor.md` §6.3). Es el
   peor de los tres remedios que proponía: cuesta **+5 350 MiB en EasyOCR** y **+1 739
   en PaddleOCR** frente a ir directo al mayor, con réplica de signo en una segunda
   tanda. §3.4.
3. **MATIZADO: «el asignador no devuelve un solo MiB».** Sobre el pico es exacto para
   PaddleOCR y EasyOCR. Pero **al MiB no se puede afirmar**, porque el ruido de fondo de
   la propia lectura es de **39-42 MiB** (§3.1) y EasyOCR llegó a bajar **97 MiB** —de
   1 226 a 1 129— a lo largo de la fase de control, es decir algo por encima de ese
   ruido. **Lo defendible es «no devuelve la memoria del PICO, y nada por encima de
   ±43 MiB»**, no «ni un solo MiB»: un enunciado al MiB necesita conocer la resolución
   efectiva del instrumento, y aquí no es el MiB.
4. **REFUTADO: «arranca en 3,7 s en vez de 18,4»** (`PLAN-ORQUESTADOR.md`, hito 6).
   Medido pareado en la misma tanda: **4,085 s (RapidOCR) frente a 7,048 (PaddleOCR)**,
   **×1,73**. Los 18,4 s no se reproducen en esta máquina con estas versiones. **Lo que
   sí se confirma es la segunda mitad de esa frase**: RapidOCR funciona en CPU y su
   primera página cuesta **1,21 s** frente a **4,72** de PaddleOCR y **5,73** de EasyOCR.
5. **Mi propio corpus escondía un documento sin referencia fiable** y estuvo a punto de
   entrar en el saldo con un CER de 96-98 % que no dice nada. §7.4.
6. **Siete de las 98 corridas salieron `SUCIA`** (§1.2): seis son celdas sueltas de la
   tanda C, que publica medianas de 9 y por eso las absorbe; la séptima
   (`D_paddleocr_ascendente`, deriva 1,42) **es una fila publicada**, se acepta con
   argumento y **sus tiempos no se usan**.
7. **Y un defecto de arnés que NO he arreglado, a propósito:** `ocr_motor.py` sigue sin
   los dos testigos de ruido, así que la tanda B no los tiene. Añadírselos habría sido un
   segundo cambio de contrato sobre un arnés compartido en el mismo commit. **Los
   milisegundos de §7.3 valen como cifra relativa dentro de su tanda y nada más.**

---

## 9. Lo que este informe NO cubre

- **Un solo documento base para toda la parte de VRAM.** Las cinco resoluciones salen de
  `escaneado_d4`. Si el coste dependiera del **contenido** (número de cajas detectadas) y
  no solo del tamaño del array, aquí no se vería. **PENDIENTE**, y es sondeable: dos
  documentos de los mismos Mpx con muy distinta densidad de texto.
- **Ni una sola medida con dos modelos residentes a la vez.** El presupuesto de §6.1
  **suma cifras de informes distintos**, y la suma es una hipótesis: los asignadores
  podrían compartir o estorbarse. **PENDIENTE**, y es lo que de verdad falta para cerrar
  el hito 6.
- **Docling no se ha medido.** El hito 6 lo nombra explícitamente
  (`Docling con RapidOCR en backend="torch"`) y aquí solo hay RapidOCR ONNX suelto. El
  backend `torch` puede tener otro asignador y **no se puede suponer que hereda el techo
  de 1 526 MiB**.
- **El reciclado no se ha implementado, solo medido.** No hay código de sidecar en
  `filex/`: este informe no tocó `filex/` en absoluto.
- **`fork` no existe en Windows**, así que la observación de §4.1 sobre ahorrarse el
  `import` es una idea, no una medida.
- **Las tres rectas de §5.1 se ajustan sobre cinco puntos** y una sola tarjeta. La de
  RapidOCR es explícitamente una cota superior floja, no un modelo.
- **B11 no toca `Rec.lang_type`** porque en PP-OCRv6 `latin` no existe (§7.1). La tabla
  de `corpus-d4.md` §7.2 que lo justificaba **sigue sin reverificarse**, y ahora se sabe
  que solo sería aplicable volviendo a PP-OCRv5.

---

## 10. Reglas del encargo

| regla | estado |
|---|---|
| Escribir solo en `bench/ocr-produccion-sidecar.md`, `bench/salidas-ocr-produccion/` y `bench/scripts/ocr_motor.py` | **Cumplida.** Nada de `filex/`, `analysis/`, maestros ni informes ajenos |
| No tocar `ocr_eval.py`, `mcp_probe*.py`, `harness.sh`, `referencia.json` | **Cumplida.** `ocr_eval.py` y `harness.sh` **importados/usados**, no editados; `referencia.json` ni abierto |
| Suite en `266 passed, 6 skipped` | **Cumplida.** `266 passed, 6 skipped in 167,02 s` tras el cambio |
| Corpus LFS | `corpus/imagen/tipico.png` venía en **130 B**; `git lfs checkout` (266 MB, sin red) antes de medir |
| Lock de GPU en todo lo que usa la tarjeta | **Cumplida.** Las 4 tandas de GPU lo toman desde `.sh`; la 5.ª es CPU |
| Medianas de n≥9 y dos testigos | **Cumplida.** n=9 en B11 y en el arranque en frío; n=20 en la fase `repetido`. Los dos testigos en las 98 corridas de `sidecar_op.py`, con tope de 20 s; **`ocr_motor.py` no los lleva y se declara** (§1.2) |
| Marcar MEDIDO/PENDIENTE | **Cumplida** |
| Dispositivo fijado (trampa 11) | **Cumplida.** VRAM siempre `cuda`; la tanda C mide las dos y lo dice en el nombre |
| Vía de entrada declarada (trampa 30) | **Cumplida.** `ruta` en los tres motores, constante en todo el informe |
| `pHYs` no usado como variable (trampa 29) | **Cumplida**, y declarado como omisión deliberada |
| Referencia de 610 caracteres (trampa 9) | **Cumplida.** 16 de los 21 documentos usan la de `d4_texto`; los otros 5 declaran su paso de 1,27 |
| Métrica declarada en cada tabla (trampa 55) | **Cumplida.** `acentos`, con el redondeo declarado en §1.4 |
| Timeouts explícitos | **Cumplida.** Las 100 ejecuciones de motor, todas bajo `timeout` |
| Dos intentos por problema | **Cumplida.** La sonda de pesos: un intento fallido, una sonda para averiguar el camino, y arreglo |
| Directorio desechable y censo (R21) | **Cumplida.** `git status` al terminar: solo `ocr_motor.py` modificado y el directorio de salidas. **Cero ficheros sueltos** |
| No versionar binarios regenerables | **Cumplida.** 23 MB de PNG borrados, `sha256` en el `MANIFIESTO.md`; los **283 `.txt` de OCR se quedan** (239 de B26 + 44 de B11) (fila N17) |
| Nada instalado en los venv | **Cumplida.** `.venv-ai`: `torch 2.6.0+cu124`, `cuda True`, `onnxruntime 1.22.0`. `.venv-paddle`: `paddle 3.2.0` con CUDA |
| GPU libre al terminar | **Cumplida.** `gpu_release` en las 4 tandas; lock inexistente y **10 639 MiB libres** al cerrar; cero procesos de Python de OCR vivos |

---

## 11. Trampas propuestas para `CLAUDE.md` — **NO APLICADAS**

Rango 66-69, cerrado. **No se han escrito en `CLAUDE.md`.**

> **66. Una sonda que busca por expresión regular dentro de un objeto puede estar leyendo
> el CATÁLOGO en vez del elemento, y siempre devuelve el primero — MEDIDO**
> (`bench/ocr-produccion-sidecar.md` §8.1). El campo `text_det`/`text_cls`/`text_rec` de
> `bench/salidas-ppp-norm/json/*.json` (10 configuraciones) y de
> `bench/salidas-k-motor/json/*.json` (6) dice **`ch_PP-OCRv4_det_mobile.onnx` en todas**,
> incluidas las de PP-OCRv5 y PP-OCRv6, porque `session.model_info` de RapidOCR es el
> catálogo de todo lo descargable y empieza por PP-OCRv4. El camino real es
> `session.session._model_path`. **No invalidó ningún CER** —el modelo pedido se
> registraba aparte— pero durante dos informes el campo de trazabilidad **fue idéntico en
> configuraciones distintas y nadie lo miró**. Es la trampa 48 en su forma más barata de
> detectar: **si una sonda devuelve el MISMO valor para dos configuraciones que sabes que
> son distintas, la sonda está rota, y esa comprobación cuesta una línea.**

> **67. La VRAM que un motor de OCR no devuelve no crece con las páginas ni con los
> megapíxeles acumulados: crece con el documento MAYOR y con el CAMINO hasta él —
> MEDIDO** (ídem §3). Veinte páginas de 1,25 Mpx (24,97 Mpx acumulados) mueven **39-42
> MiB** en los tres motores; **un** folio de 4,35 Mpx mueve **3 209** en EasyOCR y no lo
> devuelve. Y **llegar al mismo folio de 8,88 Mpx en escalera cuesta ×2,25 más VRAM que
> ir directo** (9 646 frente a 4 296 MiB), lo que **refuta** la primera de las tres
> salidas que proponía `k-por-motor.md` §6.3 (*«procesa en orden ascendente de tamaño»*):
> el orden bueno es **descendente**. El coste propio es lineal en Mpx —**1 080 MiB/Mpx
> (EasyOCR), 719 (PaddleOCR, r²=0,9995)**— y **RapidOCR es inmune porque recorta a
> 2 000 px**: satura en **1 526 MiB**. **Un contador de páginas no puede ser el criterio
> de reciclado; la fórmula es `ordenada + pendiente × Mpx` contra la VRAM libre, evaluada
> ANTES de cada página.**

> **68. Un criterio de aceptación que no nombra el tamaño de la entrada no se puede
> verificar: la misma implementación lo cumple o no según qué fichero le entre — MEDIDO**
> (ídem §6). El hito 6 pide *«el pico de VRAM no supera los ~8,7 GB con dos modelos
> residentes más NVENC»*, y eso supone que el pico es propiedad de **qué modelos hay
> cargados**. Con EasyOCR y **un solo** modelo, sin NVENC y sin segundo residente, un A4
> a 300 ppp (8,88 Mpx) pide **9 646 MiB** de coste propio: **13 094 con la base de
> escritorio documentada, sobre una tarjeta de 12 288**. Aquí cupo por **728 MiB** solo
> porque ese día el escritorio ocupaba 1 742 en vez de 3 448. **Un presupuesto de recurso
> lleva dentro el tamaño máximo de entrada admitido, o no es un presupuesto.**

> **69. Reproducir un saldo ajeno con MÁS documentos puede confirmarlo y encontrar un
> caso peor que el suyo, y las dos cosas hay que publicarlas — MEDIDO** (ídem §7.3). El
> A/B de B11 sobre 20 documentos reproduce **casi al centésimo** las dos regresiones que
> `ppp-y-normalizacion.md` §4 declaró (`d4a` +5,90 frente a +5,87; `d4f` +1,00 frente a
> +1,01) **y encuentra una tercera mayor que ambas**, `realista_d5e` **+7,40**, en una
> familia de documentos que su corpus de 11 no incluía. **Un saldo «7 mejor / 2 igual /
> 2 peor» no es falso por eso: es el saldo DE SU CORPUS.** Cuando publiques un saldo,
> publica el corpus con él; y cuando heredes uno, **el modo de comprobarlo no es repetir
> sus filas: es añadir filas que no tenía.**

---

## 12. Ficheros

| ruta | qué es |
|---|---|
| `bench/scripts/ocr_motor.py` | **modificado** — configuración vigente, `RO_LEGADO=1`, sonda de pesos corregida, `IMG`/`OUT`/`DOCS` por entorno |
| `bench/salidas-ocr-produccion/sidecar_op.py` | arnés de B26: fases `veneno`, `control`, `ascendente`, `directo`, `repetido`, `frio` |
| `bench/salidas-ocr-produccion/preparar_op.py`, `preparar_b11.py` | rasterizado con Ghostscript, con índice de px/Mpx/`sha256` |
| `bench/salidas-ocr-produccion/evaluar_b11.py` | saldo de B11 con `ocr_eval.py` importado |
| `bench/salidas-ocr-produccion/analisis_op.py`, `tablas_op.py` | las tablas de §3, §4 y §5 |
| `bench/salidas-ocr-produccion/sonda_pesos.py` | la sonda que destapó §8.1 |
| `bench/salidas-ocr-produccion/run_{a,b,c,d,e}_*.sh` | las cinco tandas, con `gpu_acquire`/`gpu_release` |
| `bench/salidas-ocr-produccion/{json,logs,texto,ab}/` | resultados crudos, trazas y **283 salidas de OCR** |
| `bench/salidas-ocr-produccion/MANIFIESTO.md` | cómo se reproduce todo y `sha256` de lo borrado |

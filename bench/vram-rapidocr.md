# N27 — la recta de VRAM de RapidOCR: por qué subestimaba, y el modelo corregido

Informe de **worker1** (carril GPU). Encargo: `ENCARGO-N27.md`.

**Sin tanda de GPU nueva.** worker2 está en la ronda 6 (`C31`+`C32`+`C40`) corriendo
la suite integral varias veces; todo lo que sigue sale de datos **ya en disco**
(`bench/ocr-produccion-sidecar.md`, `bench/hito6-sidecar.md`, `bench/ppp-y-normalizacion.md`
y sus `MANIFIESTO.md`) más aritmética sobre ellos. La única "medida" nueva de este
informe es aritmética, no un proceso que toque la tarjeta — declarado en cada sitio.

---

## 0. El fallo, tal como lo dejó `hito6-sidecar.md` §8.3

`ocr-produccion-sidecar.md` §5.1 ajustó `min(643 + 109·Mpx, 1526)` sobre **cinco**
puntos (0,55 / 1,25 / 2,22 / 4,35 / 8,88 Mpx), con r²=0,7581, y leyó el r² malo
como *«no es ruido: es la saturación»* — cierto en el extremo, **falso en el
sentido de que por eso ya no hacía falta mirar el residuo**. `hito6-sidecar.md`
tabuló el residuo y encontró **−339 MiB a 4,352 Mpx**: el modelo pide 1 117 y la
medida fue 1 456. El margen de 500 MiB lo tapaba por 161, y el propio informe dejó
escrito que bajar el margen a 300 dejaría esa celda al descubierto.

---

## 1. Por qué subestima — el mecanismo, no solo el número

### 1.1 Dos de los cinco puntos ya estaban en la meseta, y se puede decir en qué píxeles

`bench/ppp-y-normalizacion.md` §2.5 (**ya MEDIDO, con sonda enganchada al
reescalado interno del motor, no deducido**) da la tabla completa de qué array
recibe la red por cada raster de `escaneado_d4`:

| ppp | PNG de entrada | **RapidOCR → red** |
|---:|---|---|
| 100 | 647×858 | 736×960 *(sube — hay un suelo, `Det.limit_side_len: 736`)* |
| 150 | 970×1 287 | 960×1 280 |
| 200 | 1 294×1 716 | 1 280×1 728 |
| 250 | 1 617×2 145 | **1 504×1 984** |
| 280 | 1 812×2 402 | **1 504×1 984** |
| 320 | 2 070×2 746 | **1 504×1 984** |
| 400 | 2 588×3 432 | **1 504×1 984** |

**El recorte ata a 233 ppp** (`Global.max_side_len: 2000`, `rapidocr/config.yaml:10`,
aplicado en `rapidocr/utils/process_img.py:113-114`): con la página de `d4` a
617,76 pt (8,58 in) de lado largo, 2 000 px de tope se alcanzan a `2000/8.58 =
233,1 ppp`. **De ahí en adelante el array que ve la red es literalmente el mismo,
1 504×1 984 px = 2,984 Mpx**, sea cual sea el tamaño del PNG de entrada.

Los cinco puntos de `§5.1` fueron rasterizados a **100 / 150 / 200 / 280 / 400 ppp**
(`escaneado_d2_r100`, `_d4_r150`, `_d4_r200`, `_d4_r280`, `_d4_r400`, `MANIFIESTO.md`
de `bench/salidas-ocr-produccion/`). Cruzando con la tabla de arriba:

| punto (Mpx) | ppp | array que ve la red | ¿recortado? |
|---:|---:|---|---|
| 0,550 | 100 (`d2`, otro doc) | — *(no está en la tabla de `d4`; d2 es más pequeño y no llega al tope)* | no |
| 1,248 | 150 | 960×1 280 | no |
| 2,221 | 200 | 1 280×1 728 | no |
| **4,352** | **280** | **1 504×1 984** | **SÍ** |
| **8,882** | **400** | **1 504×1 984** | **SÍ** |

**Los puntos 4 y 5 de la rejilla original no son parte del tramo lineal: son la
MISMA celda medida dos veces con dos PNG de entrada distintos.** Ajustar una recta
sobre "tres puntos que crecen + dos puntos idénticos que no crecen" sesga la
pendiente hacia abajo exactamente en el tramo de transición — es la misma
distorsión que produce un ajuste lineal sobre cualquier curva que satura: la recta
"reparte" el aplanamiento entre todos los puntos en vez de reconocer que dos de
ellos no pertenecen al mismo régimen.

### 1.2 ¿Dónde ata el recorte, en Mpx? — dos números, no uno, y los dos con fuente

- **El Mpx del PNG de *entrada* en el que empieza a recortar**: en algún punto
  entre 200 ppp (2,221 Mpx, sin recortar) y 250 ppp (recortado). Con la fórmula
  del propio informe (`233,1 ppp`) y escalando por Mpx ∝ ppp²:
  `2,221 × (233,1/200)² ≈ 3,02 Mpx`. **Aritmética sobre una medida ya publicada,
  no una medida nueva** — declarado como tal.
- **El Mpx del array que la red efectivamente ve, una vez recortado**: **2,984
  Mpx exactos** (1 504×1 984, de la tabla de §1.1) — **este sí es un número medido
  directamente**, no derivado.

Los dos números coinciden dentro del redondeo (≈3,0 Mpx), lo cual tiene sentido:
justo en el umbral, recortar o no recortar da casi el mismo array.

### 1.3 Y aquí hay un hallazgo que no estaba pedido, y es el más interesante de los tres

**Si el coste de VRAM fuera una función lineal del array que REALMENTE ve la red
(no del PNG de entrada), la meseta debería costar lo que cuesta ~2,984 Mpx sobre
la recta de los tres puntos sin recortar — y no es así.**

Extrapolando la recta de §2 (`428 + 235 × Mpx`) a 2,984 Mpx dan **1 129 MiB**. La
meseta mide **1 456-1 533 MiB** (§3): **300-400 MiB más** que lo que "el mismo
array de siempre" predeciría si el único factor fuera su tamaño final.

**Conclusión, con la salvedad de que es una inferencia y no una medida directa de
VRAM por fase:** el coste de VRAM no depende solo del array que llega a la red —
depende también, en alguna medida, del **PNG original antes de recortar**
(decodificarlo, y el propio `cv2.resize` u operación equivalente necesitan sus
propios buffers transitorios, y **el asignador no devuelve la memoria** — trampa 8,
ya establecida para otros mecanismos de este mismo proyecto). Esto **no** se puede
cerrar sin instrumentar el propio proceso de RapidOCR fase a fase, que es trabajo
nuevo y **PENDIENTE** — pero explica por qué intentar "arreglar" el modelo haciendo
que la recta llegue exactamente al tope en Mpx=2,984 (el break mecánico) sería
FALSO: el tope no es "lo que cuesta esa imagen recortada", es más caro que eso, por
un motivo que no está en la imagen recortada.

---

## 2. La recta nueva — de qué tres puntos sale, y por qué no de cinco

**No se sube la ordenada hasta que cuadre contra los cinco puntos** (lo que el
encargo pide explícitamente no hacer). Se ajusta sobre los **tres puntos
confirmados sin recorte** — 0,550→556, 1,248→688, 2,221→944, de
`ocr-produccion-sidecar.md` §3.3 — y sólo esos:

```
regresión OLS, 3 puntos:  pendiente = 234,15   ordenada = 415,65   r² = 0,9923
```

**r²=0,9923 contra el 0,7581 de los cinco puntos: la forma SÍ estaba mal, no sólo
los coeficientes** — exactamente lo que el encargo pedía mirar primero.

**Residuos de los tres puntos (misma convención `modelo − medido` que el resto
del informe), y el redondeo mínimo que los cubre:**

| Mpx | medido | OLS (3 pts) | residuo (OLS−medido) |
|---:|---:|---:|---:|
| 0,550 | 556 | 544,4 | **−11,6** (subestima) |
| 1,248 | 688 | 707,9 | +19,9 |
| 2,221 | 944 | 935,7 | **−8,3** (subestima) |

El único ajuste que se aplica es **subir la ordenada lo justo para cubrir el peor
de los tres** (+11,57) y **redondear los dos coeficientes al alza** al entero
siguiente — no para que cuadre un cuarto o quinto punto (eso sí sería "calibrar
contra cinco puntos" con otro disfraz), sólo para que los TRES puntos que
justifican la forma lineal queden cubiertos:

```
ordenada = 428     pendiente = 235     (r² contra los 3 puntos: 0,9853)
```

---

## 3. El tope — el máximo de tres medidas, no la primera publicada

Tres sesiones independientes midieron el mismo `sha256` de píxeles (1 504×1 984,
la imagen ya recortada, cualquiera que sea el PNG de origen a 250 ppp o más):

| fuente | valor | contexto |
|---|---:|---|
| `ocr-produccion-sidecar.md` §3.3 (`ascendente`, esta tanda) | 1 456 | 4,352 y 8,882 Mpx, la misma cifra en las dos |
| cifra publicada originalmente (anterior a `ocr-produccion-sidecar.md`) | 1 526 | "el tope propio", citado en `§5.1` y en `sidecar.py` hasta este cambio |
| `hito6-sidecar.md` §3.3 (réplica independiente, otro día, otro arnés) | 1 533 | +7 MiB sobre 1 526, "la confirmación más fuerte de aquel informe" |

**Recorrido: 77 MiB entre la más baja (1 456) y la más alta (1 533)** — más ancho
que el ruido de una sola medida (±43 MiB), lo que sugiere que hay variación
real de sesión a sesión en esta zona (quizá ligada al mecanismo de §1.3: si el
coste depende de buffers transitorios del PNG de origen, el estado previo del
asignador entre sesiones podría pesar más aquí que en el tramo lineal). **No se
investiga esa variación hoy** — no hace falta tomar la tarjeta para lo que pide
este encargo, que es tener una cota superior, y **la cota superior tiene que
cubrir la MAYOR de las tres, no la primera publicada ni la más baja**:

```
tope = 1533
```

Usar 1 456 (la cifra de la tanda de este mismo informe) habría sido, literalmente,
publicar un modelo que ya sabíamos que otra sesión refuta por 77 MiB — el mismo
error de fondo que motiva todo este encargo, sólo que con un tope en vez de con
una pendiente.

---

## 4. El modelo completo, contra los cinco puntos publicados

```
coste_previsto(Mpx) = min(428 + 235 × Mpx, 1533)
```

**Convención de la tabla, declarada porque el encargo y este informe la usan
igual: `residuo = modelo − medido`. Positivo = el modelo pide MÁS que lo medido
(sobreestima, lado seguro para un presupuesto). Negativo = el modelo pide MENOS
(subestima, el lado que rompe un presupuesto).**

| Mpx | modelo VIEJO (643+109·Mpx, tope 1526) | residuo viejo | modelo NUEVO (428+235·Mpx, tope 1533) | medido | residuo nuevo |
|---:|---:|---:|---:|---:|---:|
| 0,550 | 703 | +147 | 557 | 556 | **+1** |
| 1,248 | 779 | +91 | 721 | 688 | **+33** |
| 2,221 | 885 | −59 | 950 | 944 | **+6** |
| 4,352 | 1 117 | **−339** | 1 451 | 1 456 | **−5** |
| 8,882 | 1 526 | +70 | 1 533 | 1 456¹ | **+77** |

¹ *La celda de 8,882 Mpx de esta tanda concreta midió 1 456; el modelo usa el
máximo de las tres tandas (§3), así que el residuo grande y positivo aquí es
correcto y esperado — el modelo está por ENCIMA de esta medida en particular a
propósito, porque otra tanda midió 1 533 para el mismo píxel.*

**Lectura de la tabla que importa: con el modelo nuevo hay UN solo residuo
negativo (subestimación) en las cinco filas, y es de −5 MiB, a 4,352 Mpx** —
justo el punto que el encargo señaló con −339. Los otros cuatro son positivos
(el modelo sobreestima, que es el lado seguro), con el mayor de +77 en el punto
donde el modelo usa deliberadamente el tope más alto de las tres sesiones en
vez del medido en esta.

**Con número, el antes y el después:**

- **Modelo viejo:** máxima subestimación real, **339 MiB** (≈8× el ruido del
  instrumento, ±43 MiB).
- **Modelo nuevo:** máxima subestimación real, **5 MiB** (dentro del ruido) — y
  es la única fila donde el modelo se queda corto de las cinco.

---

## 5. El hueco de muestreo — declarado, no rellenado hoy

**Entre 2,221 Mpx (confirmado sin recorte) y 4,352 Mpx (confirmado ya en la
meseta) no hay ningún punto medido.** El umbral mecánico cae dentro de ese hueco
(≈2,98-3,02 Mpx, §1.2), así que **la forma exacta de la curva en esa franja
—¿sigue lineal un tramo más y luego salta, o la transición es suave?— no se
puede afirmar con los datos de hoy.**

**No se ha tomado la tarjeta para cerrar esto**, siguiendo la instrucción
explícita del encargo. Y hay que decir con precisión hasta dónde llega la
garantía del modelo de §4, sin inflarla:

- **En los dos extremos confirmados del hueco (2,221 y 4,352 Mpx) el modelo
  cubre con margen o se queda a sólo 5 MiB (§4).** Eso es sólido.
- **En el INTERIOR del hueco (2,221 a 4,352 Mpx) el modelo usa la RECTA, no el
  tope** —`recta(2,984)=428+235×2,984=1 129`, muy por debajo de 1 533— porque
  la recta no cruza el tope hasta **4,70 Mpx**. Eso presupone que la VRAM sigue
  subiendo aproximadamente en línea recta hasta ahí. **§1.3 da un motivo
  concreto para dudarlo**: el recorte mecánico es un umbral DURO en ≈3,0 Mpx
  (el array que ve la red deja de crecer ahí mismo), y ya se midió que el
  coste no es sólo función de ese array — así que no hay garantía de que el
  coste real "espere" hasta 4,70 Mpx para acercarse a la meseta. **Si la VRAM
  real sube más deprisa que la recta justo después del umbral mecánico
  (≈3,0 Mpx), el modelo SUBESTIMARÍA en algún punto de esa franja, y hoy no
  hay ningún dato que lo confirme ni lo descarte.**

**Esto no es un matiz cosmético: es el límite real de lo que este informe
puede afirmar sin tomar la tarjeta.** El modelo es la mejor cota superior que
los datos de hoy permiten construir sin calibrar contra los puntos ya
recortados (que es justo lo que produjo el error original), pero **"cota
superior en todo el rango admitido" no está demostrado entre 2,221 y 4,352
Mpx — sólo en sus dos extremos.**

**Para cerrar esto con precisión** harían falta **al menos dos puntos nuevos
entre 2,221 y 4,352 Mpx** — el más informativo, justo después del umbral
mecánico (p.ej. 240-250 ppp sobre `d4`, que la tabla de §1.1 ya sitúa
recortado a 1 504×1 984): si ESE punto ya mide cerca de la meseta, la
franja de riesgo se cierra casi entera de un solo golpe. **PENDIENTE**, y es
exactamente el tipo de medida que exige tomar el lock con la máquina
tranquila, no ahora.

---

## 6. El rango admitido — y una advertencia sobre el aspecto del documento

**El modelo (§4) está confirmado en 0,550/1,248/2,221 Mpx (recta) y en 4,352/8,882
Mpx (tope), para el aspecto de `escaneado_d4` (≈0,754). NO está confirmado entre
2,221 y 4,352 Mpx (§5) — ahí es una extrapolación de la recta, no una medida.**
Dos límites más, ninguno cubierto por los cinco puntos:

1. **Mpx de entrada por encima de 8,882**: el mecanismo (recorte duro a 2 000 px
   de lado largo) garantiza que el array que ve la red no crece más allá de
   1 504×1 984 para la MISMA proporción de página, así que el tope debería
   seguir aguantando — pero es una consecuencia del mecanismo, **no una medida**
   por encima de 8,882 Mpx. PENDIENTE.
2. **Documentos MÁS CUADRADOS que `d4`.** El recorte actúa sólo sobre el lado
   LARGO. Un documento con aspecto más cercano a 1 (más cuadrado) que se recorte
   a 2 000×2 000 px tiene **1,34× más píxeles** que los 1 504×1 984 de `d4`
   (4,0 Mpx contra 2,984). Si el coste de VRAM en la meseta depende del tamaño
   del array recortado —y §1.3 ya muestra que depende de algo MÁS que sólo ese
   array, lo que hace la extrapolación aún menos segura—, **el tope de 1 533 MiB
   podría no aplicar a un documento cuadrado**. No hay ninguna medida sobre un
   documento de aspecto distinto en el corpus de este informe. **PENDIENTE,
   y es una limitación real del modelo, no un detalle**: `filex/sidecar.py` no
   recibe el aspecto del documento como parámetro (sólo `mpx`), así que hoy el
   sidecar no puede ni siquiera preguntarse esta cuestión. Ampliar la firma de
   `coste_previsto` para que reciba el aspecto es un cambio de API que cruza a
   quien llama (`nucleo.py`, no mío) y **no se hace en este encargo**: queda
   escrito como el pendiente que es.

---

## 7. Lo que NO se hizo, con el motivo

- **No se bajó el margen de 500 MiB.** El encargo lo prohíbe explícitamente
  aunque el modelo nuevo lo haría innecesario en el punto que motivó el aviso
  (4,352 Mpx: antes 1 117+500=1 617 > 1 456 por 161; ahora 1 451+500=1 951 > 1 456
  por 495). **Se mide y se dice, no se aplica**: bajar el margen es una decisión
  de otra fila (N26, ronda 8) y de otro presupuesto (afecta también a EasyOCR y
  PaddleOCR, que no se tocan aquí).
- **No se tocó `N26`** (el margen de la suma, `filex/sidecar.py::Perfil`, es del
  perfil: 1,2 % `distil`, 7,2 % `large-v3`) — no es de este encargo.
- **No se midió el hueco de muestreo con la tarjeta** (§5) — instrucción
  explícita de esta ronda.
- **No se investigó la variación de 77 MiB entre sesiones del tope** (§3) más
  allá de tomar el máximo — requeriría instrumentar VRAM fase a fase dentro del
  proceso de RapidOCR, trabajo nuevo.
- **No se cambió la firma de `coste_previsto`** para admitir el aspecto del
  documento (§6) — cruza a `filex/nucleo.py`, que no es mío.
- **No se tocó `N30`** (`test_cerrojo.py::test_sin_el_cerrojo_de_maquina_los_dos_procesos_devuelven_ok`,
  intermitente). No salió roja en ninguna de las corridas de este informe —
  declarado por si acaso, no investigado.

---

## 8. Cambios en código y pruebas

### 8.1 `filex/sidecar.py`

- `Motor.__doc__`: explica por qué la recta de RapidOCR ya no sale de los cinco
  puntos publicados.
- `MOTORES["rapidocr"]`: `Motor("rapidocr", 643, 109, 1526, …, r2=0.7581)` →
  `Motor("rapidocr", 428, 235, 1533, …, r2=0.9853)`.
- `_F_RAPIDOCR`: fuente nueva, declarando las dos procedencias (los tres puntos
  de `ocr-produccion-sidecar.md`, el tope y el ajuste de este informe) —
  conserva la subcadena `"ocr-produccion-sidecar"` para no romper
  `test_cada_recta_declara_su_fuente`, que sigue siendo cierto: los tres puntos
  base siguen viniendo de ahí.

### 8.2 `pruebas/test_hito6.py` — seis pruebas tocadas, todas por el cambio de constantes

| prueba | qué cambió |
|---|---|
| `test_rapidocr_satura_en_su_tope` | `1526` → `1533`, docstring explica el porqué (máximo de 3 sesiones) |
| `test_la_recta_de_rapidocr_subestima_en_el_tramo_de_en_medio` | **renombrada** a `test_la_recta_de_rapidocr_ya_no_subestima_mas_alla_del_ruido`; ya no afirma que subestima 339 MiB, afirma que el residuo que queda (≤5 MiB) está dentro del ruido del instrumento |
| `test_admite_cuando_cabe_con_margen` | `1526` → `1533` |
| `test_el_margen_de_500_decide_el_borde` | el borde se mueve de `2026/2025` a `2033/2032` (`1533+500` en vez de `1526+500`) |
| `test_el_perfil_que_cumple_reproduce_los_7564` | **renombrada** a `test_el_perfil_que_cumple_reproduce_los_7571`; `7564`→`7571` (+7, la misma diferencia que `hito6-sidecar.md` §3.3 ya medía) |
| `test_el_perfil_de_large_v3_no_cumple` | `10242` → `10249` |

Ninguna otra prueba del módulo cambió: `test_los_mpx_admisibles_reproducen_la_tabla`,
`test_un_a4_a_300ppp_no_entra_en_dos_de_los_tres_motores` y las de `LaGeometria`
siguen pasando sin tocarlas — el nuevo tope (1 533) sigue muy por debajo del
umbral de 5 500 MiB que las hace devolver `inf`, así que el comportamiento
cualitativo (RapidOCR "sin límite práctico" frente a los 6 000 MiB del
`GPU_GUARD`) no cambia.

**MEDIDO, `pruebas/test_hito6.py` en aislamiento:**

```
D:\...\.venv-mcp-filex\Scripts\python.exe -m pytest pruebas/test_hito6.py -q
50 passed, 2 skipped, 3 subtests passed in 0.66s
```

Los 2 saltados son los de siempre (falta el ráster de `preparar_h6.py`;
`FILEX_PRUEBAS_SIDECAR=1` sin fijar) — no relacionados con este cambio.

---

## 9. Aceptación — las cuatro declaraciones

```
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe -m pytest pruebas/ -q -rs
443 passed, 3 skipped, 2 warnings, 121 subtests passed in 193.65s (0:03:13)

D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe ci/integridad.py
(antes de crear este informe)  9/9 OK
(después de crear este informe) 8/9 -- MAL informes-registrados: 75 informes,
  vram-rapidocr.md sin citar en ESTADO-Y-REPARTO.md
```

**El noveno es esperado, no una regresión** — es la misma mecánica que ya dejó
`bench/runner-autoalojado.md` en la ronda anterior (`C44`): `ESTADO-Y-REPARTO.md`
es un fichero "maestro" que **«nadie escribe salvo el agente de consolidación»**,
así que no lo edito yo, y `ci/integridad.py` marca correctamente que este informe
nuevo no está citado todavía. Lo cierra quien consolide.

- **Intérprete:** Python 3.11.9, `sys.platform == "win32"`,
  `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe`.
- **Entorno:** Docker levantado (mismos tres contenedores del proyecto,
  confirmado con `docker ps` antes de correr). GPU sin tocar por este encargo
  más allá de las consultas de `nvidia-smi` que ya hace la suite normal
  (`test_hito2`/`test_gpu_lock`, sin cambios de mi parte) — nada de este
  informe lanzó una tanda de medición nueva.
- **Qué quedó fuera y por qué:** los mismos 3 `skipped` de siempre
  (`test_cerrojo.py` necesita dos volúmenes distintos; `test_hito6.py` necesita
  el ráster de `preparar_h6.py` y `FILEX_PRUEBAS_SIDECAR=1`) — ninguno nuevo,
  ninguno relacionado con este cambio.
- **Estado de la máquina, y un fallo que NO es mío — declarado por trampa 101:**
  la primera corrida de la suite completa dio **1 failed**:
  `test_cancelacion_procesos.py::DuenoMuerto::test_un_working_sin_dueno_vivo_se_detecta_y_se_cierra`,
  con la CPU al **76 %** antes de empezar (medido con `wmic cpu get
  loadpercentage`, no con PID — trampa 31 aplicada a CPU, no sólo a VRAM). `git
  diff --stat -- pruebas/test_cancelacion_procesos.py filex/nucleo.py
  filex/verificador.py filex/api.py` da **vacío**: mi cambio no puede haberlo
  roto. Aislada, con la CPU ya en 54 %, la prueba **pasa en 1,91 s**. Repetida
  la suite completa con la CPU en 34 %: **443 passed, 0 failed**. Es la misma
  forma que `CLAUDE.md` ya documenta para este mismo test
  (`test_cancelacion_procesos` da 2 failed con la CPU al 50 % y pasa limpio con
  la máquina tranquila) — **no se investiga más porque no es mío y ya está
  identificado**, y se declara en vez de callarlo.

---

## 10. Entrega

Commiteado en `edicius2002/filex-gpu`. No se empujó, no se abrió PR, no se
lanzó ninguna tanda de medición de GPU.

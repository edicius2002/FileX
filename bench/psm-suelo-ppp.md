# B21 + B22 — Tesseract, `psm 3` y `psm 11`, sobre el suelo de 100 ppp

Cierra el pendiente que `bench/suelo-ppp.md` dejó escrito: *«Tesseract `psm 3` y `psm
11` no forman parte de estas 336 celdas»*. Con esto, las **9 configuraciones** que
`CLAUDE.md` (trampa 8) cita para el `k` por motor —las mismas 7 de `suelo-ppp.md` más
estas dos— quedan medidas sobre el suelo.

## Estado y condiciones de medida

**MEDIDO: 96 celdas limpias** (2 configuraciones Tesseract × 4 documentos × 12 ppp:
nativo + rejilla fina 100–150 cada 5), mediana n=9. Las 96 con `rc=0` en las nueve
repeticiones, las 96 deterministas (`determinista: true`), 0 celdas con CER 100 % — no
aplica la marca «corrida fallida» de la trampa 99. Cada fila declara `metrica: acentos`
(la canónica desde el 28/08), el `psm`, el dispositivo y el ráster.

Los mismos cuatro documentos y el mismo barrido de ppp que `bench/suelo-ppp.md`
(`escaneado_d5a` nativo 90, `d5c` 80, `d5` 72, `d5b` 60; rejilla fina 100,105,…,150),
para que las filas sean comparables celda a celda. Referencia: `d4_texto.BLOQUES` (610
caracteres de origen, 596 tras normalización acentuada; **no** se parsea
`REFERENCIA-d5.txt`, trampa 92). Cuantización de la referencia: **±0,16 puntos** por
carácter; una diferencia por debajo no se cuenta como señal.

**Rasterizador: `magick -density N …[0] -units PixelsPerInch -density N -colorspace
sRGB -alpha remove -background white -flatten`** — el mismo criterio que
`suelo-ppp.md`, y aquí es más importante que allí: Tesseract **sí** consulta el `pHYs`
(trampa 29) y una invocación sin `-units PixelsPerInch` le hace inventar la resolución.
El pHYs declarado es el verdadero en las 96 celdas; el detalle exacto está en
`salidas-psm-suelo/MANIFIESTO.md`.

**Tesseract es CPU: no toma `filex.gpu.Lock`.** Mismo criterio que
`bench/salidas-suelo-ppp/b21b22.py`, que ya distinguía `config.startswith("tess")`
para no tomar el lock de una tarjeta que el motor no usa. `GPU_GUARD` no aplicaba a
esta tanda por el mismo motivo, y no se esquivó: sencillamente no había nada que
guardar.

**Reproduce**, desde Git Bash de Windows, con `USERPROFILE`/`HOME` **locales** de
Windows (nunca heredados de WSL — ver §4):

```
"/d/Work/research/FileX/.venv-ai/Scripts/python.exe" \
  bench/salidas-psm-suelo/b21b22_tess.py tess3 \
  --ppp 100,105,110,115,120,125,130,135,140,145,150 --reps 9
"/d/Work/research/FileX/.venv-ai/Scripts/python.exe" \
  bench/salidas-psm-suelo/b21b22_tess.py tess11 \
  --ppp 100,105,110,115,120,125,130,135,140,145,150 --reps 9
```

**Dos testigos de ruido, tope 20 s cada uno:**

| Config | Deriva monohilo | Testigo de proceso (nivel) | Etiqueta | Duración |
|---|---:|---:|---|---:|
| `tess3` | 1,24× | 1,36× sobre reposo | **limpia** | 359,1 s |
| `tess11` | 0,80× | 1,48× sobre reposo | **limpia** | 376,0 s |

## B21 — el suelo de 100 ppp es del motor, y en Tesseract el signo se INVIERTE

**MEDIDO**, dos configuraciones. Delta = CER a 100 ppp − CER al nativo; positivo
empeora. Se marca igual cuando |delta| < 0,16.

| Configuración | Peor / mejor / igual | Diferencias por documento d5a, d5c, d5, d5b (pp) |
|---|---:|---|
| Tesseract `psm 3` | 1 / 3 / 0 | +1,5; −1,2; −7,9; −20,0 |
| Tesseract `psm 11` | 1 / 3 / 0 | +0,3; −0,7; −8,4; −16,7 |

Con cifras exactas en los dos documentos donde el suelo decide de verdad (nativo <
100 ppp):

| Documento | Nativo | CER a nativo (`psm 3`) | CER a 100 ppp (`psm 3`) | CER a nativo (`psm 11`) | CER a 100 ppp (`psm 11`) |
|---|---:|---:|---:|---:|---:|
| `escaneado_d5` | 72 | 10,1 % | **2,2 %** | 10,2 % | **1,8 %** |
| `escaneado_d5b` | 60 | 28,7 % | **8,7 %** | 25,3 % | **8,6 %** |

**Esto invierte el signo que `suelo-ppp.md` midió para RapidOCR (11 peor / 0 mejor) y
lo empareja con el de EasyOCR y Docling+R6 (7 mejor / 0 peor).** Con Tesseract el
saldo global de las 9 configuraciones sigue siendo un empate —ahora **16 peor / 15
mejor / 5 igual**— y sigue siendo engañoso por el mismo motivo: promediarlo destruye
la interacción motor×documento, que es el término que la regla `max(min(nativos×1,25,
techo),100)` supone nulo.

**El único documento donde el suelo empeora en Tesseract es `escaneado_d5a` (nativo
90, el más alto de los cuatro y el de menor CER de partida)**, en las dos
configuraciones (+1,5 en `psm 3`, +0,3 en `psm 11` — este último apenas por encima del
umbral de cuantización, pero real). Es consistente con el mecanismo: `d5a` ya tiene
pixeles de sobra para el análisis de maquetación de Tesseract; subir a 100 sólo
introduce interpolación. En los otros tres documentos (72, 80 y 60 ppp nativos) el
suelo da a Tesseract la resolución que su análisis de maquetación necesita, y por eso
gana mucho — hasta 20 puntos en `d5b`.

**Conclusión, con las 9 configuraciones ya medidas: el suelo de 100 ppp no tiene un
signo global ni siquiera dentro de un mismo par (documento, régimen de nativos bajos);
lo decide el motor, documento por documento.** No hay una corrección de la regla que
generalice: la interacción es el hallazgo.

## B22 — la curva no es suave, y en Tesseract el óptimo SÍ agrupa cerca de 125–150 ppp

**MEDIDO**, dos configuraciones, n=9. La rejilla fina no es monótona en ningún
documento — hay picos locales de 1 a 2 puntos entre valores adyacentes de 5 ppp— pero
la amplitud es mucho menor que la de RapidOCR:

| Documento | Amplitud rejilla fina, `psm 3` | Amplitud rejilla fina, `psm 11` | Amplitud RapidOCR v6+R6 (`suelo-ppp.md`) |
|---|---:|---:|---:|
| `escaneado_d5a` | 2,4 pp | 1,2 pp | — |
| `escaneado_d5c` | 0,8 pp | 0,8 pp | **~18 pp** (0,7→18,5→9,7→0,8→0,3→5,0) |
| `escaneado_d5` | 2,1 pp | 1,0 pp | — |
| `escaneado_d5b` | 3,0 pp | 4,2 pp | — |

El máximo de las 96 celdas de Tesseract es **4,2 puntos** (`d5b`, `psm 11`); el pico de
RapidOCR sobre `d5c` solo, por sí solo, es **más de cuatro veces mayor**. Ejemplo de
no monotonía en Tesseract, para que quede la forma exacta del pico y no sólo el
rango: `escaneado_d5` con `psm 3` da 1,7 % a 130 ppp, **3,4 % a 135** y 2,0 % a 140 —
un pico de un solo paso (5 ppp) que **no aparece en el mismo documento con `psm 11`**
(1,8 / 1,8 / 2,0 en el mismo tramo). El pico es del triple (documento, ppp, `--psm`),
no sólo del par (documento, ppp) que ya proponía `suelo-ppp.md`.

**Y, a diferencia de las siete configuraciones de `suelo-ppp.md`, en Tesseract el
mínimo SÍ agrupa cerca de 125–150 ppp en los cuatro documentos y en las dos
configuraciones:**

| Documento | `psm 3` (ppp óptimo, CER) | `psm 11` (ppp óptimo, CER) | CER a 100 ppp (referencia) |
|---|---:|---:|---:|
| `escaneado_d5a` | 130 ppp, 0,3 % | 130 ppp, 0,3 % | 2,7 % / 1,5 % |
| `escaneado_d5c` | 145 ppp, 0,7 % | 145 ppp, 0,7 % | 1,3 % / 1,3 % |
| `escaneado_d5` | 145 ppp, 1,3 % | 145 ppp, 1,5 % | 2,2 % / 1,8 % |
| `escaneado_d5b` | 125 ppp, 6,9 % | 150 ppp, 6,2 % | 8,7 % / 8,6 % |

**Esto es una confirmación parcial y sólo de Tesseract** de la hipótesis de ~125 ppp
que `suelo-ppp.md` dejó abierta (B22) por otra vía y que las siete configuraciones
no-Tesseract refutaron como óptimo global (picos idiosincráticos, sin agrupación).
**No generaliza**: RapidOCR v6+R6 sobre `d5c` tiene su óptimo en 130 (0,3 %) pero con
un régimen de picos violentos alrededor (18,5 % a sólo 30 ppp de distancia), mientras
que en Tesseract el entorno del óptimo es plano. La ganancia de ir de 100 ppp al
óptimo de Tesseract es real pero modesta frente al salto nativo→100 (máximo 2,4 puntos
en `d5a`, frente a los hasta 20 puntos de B21) — es una segunda mejora, mucho más
pequeña que la primera.

**Sigue sin medir, y no lo cubre este encargo:** sondear las cajas detectadas para
explicar el mecanismo de los picos de RapidOCR, que `suelo-ppp.md` dejó como «la
siguiente sonda útil». Esa mitad de B22 permanece PENDIENTE.

## `psm 3` frente a `psm 11`: el hueco aquí es de DÉCIMAS, y el titular de 42,78 puntos no es comparable sin más

**MEDIDO**, 48 pares de celdas (mismo documento, mismo ppp, las dos configuraciones).

| Documento | Ganador más frecuente en la rejilla | Reparto (psm3 / psm11 / empate) | Mayor hueco en una celda |
|---|---|---:|---:|
| `escaneado_d5a` | empate | 1 / 1 / 10 | 1,2 pp (ppp 100) |
| `escaneado_d5c` | empate | 4 / 4 / 4 | 0,5 pp |
| `escaneado_d5` | `psm 3` | 6 / 4 / 2 | 1,6 pp (ppp 135) |
| `escaneado_d5b` | `psm 11` | 3 / 9 / 0 | 3,4 pp (ppp nativo 60) |

**Hueco medio sobre las 48 celdas: 0,435 puntos. El máximo, 3,4 (y sólo al ppp
nativo, fuera de la rejilla fina).** El ganador cambia celda a celda —confirmando que
el `--psm` no es separable de `k`, como ya decía `CLAUDE.md`— pero aquí la magnitud es
de décimas, no de puntos.

**Esto NO se puede leer como una contradicción directa de los 42,78 puntos publicados
en `bench/psm-y-rasterizador.md`, y hay que decir por qué en vez de compararlos a
ciegas.** Ese informe trae su propia advertencia, añadida el 23/08: los 84,56 % (`psm
3`) contra 41,78 % (`psm 11`) de `escaneado_d4` que dan los 42,78 puntos **se
midieron con un `pHYs` SIN DECLARAR** (`magick -density N` sin `-units
PixelsPerInch`), justo la invocación que aquí se evita a propósito. El propio informe
dice que esas cifras «no cruzan» con nada medido con el pHYs verdadero.

Tomando del mismo informe (§4.5) la fila que SÍ declara el pHYs verdadero —`d4` a 200
ppp reales, columna en negrita—: `psm 3` da **51,34 %** y `psm 11` **40,60 %**, un
hueco de **10,74 puntos**. Eso ya es la comparación correcta con pHYs declarado en los
dos lados, y sigue siendo **~25 veces mayor** que el hueco medio que mido aquí (0,435
puntos) sobre `escaneado_d5*` en la rejilla 100–150 ppp. **La métrica coincide en los
dos informes (acentos); lo que no coincide es el documento (`d4` frente a la familia
`d5`) ni el régimen de ppp (200 fijo frente a 100–150), así que esta diferencia sigue
sin explicación mecánica** — puede ser del documento, del régimen de ppp, o de ambos,
y **no se puede atribuir a uno sin medir la celda que falta** (`d4` en la rejilla
100–150, o `d5*` a 200 ppp). Queda **PENDIENTE**, y se declara así en vez de forzar
una lectura.

## Ejecución e integración

**MEDIDO:** `USERPROFILE`/`HOME` heredados de WSL se resuelven a
`\\wsl.localhost\Ubuntu\...`, el mismo síntoma que `suelo-ppp.md` documentó para
Docling. Se fijaron a `C:\Users\krato` antes de invocar el `python.exe` de Windows;
sin ese fijado, cualquier caché que lea `HOME` fallaría por la misma vía UNC. Aquí no
llegó a manifestarse porque ni `ocr_eval` ni `filex.gpu` leen `HOME`, pero se fijó de
todas formas por disciplina, no porque hiciera falta demostrarlo esta vez.

**Riesgo que NO se materializó, y hay que dejarlo escrito como lo que es — no como un
acierto.** El encargo pedía un conductor único y desprendido entre configuraciones
(trampa 100: desprender salva la tarea, no la secuencia). Aquí `tess3` se lanzó en
segundo plano dentro del propio turno y, **una vez confirmado que terminó bien**,
`tess11` se lanzó también dentro del turno. Si `tess3` hubiera fallado a mitad de
sesión — o si la sesión se hubiera cortado entre las dos tandas — nadie habría
lanzado `tess11`, y no habría habido un proceso reiniciado y desprendido que retomara
la secuencia. Con sólo 2 configuraciones y ~6 minutos cada una el riesgo era pequeño,
pero es exactamente el mismo mecanismo que costó 40 minutos en la ronda anterior con
7 configuraciones más pesadas: la disciplina correcta es el conductor desprendido
aunque la tanda sea corta.

**Verificación de las 96 celdas, ejecutada sobre el propio JSON, no leída de un
resumen:** `rc=0` en las 96×9 repeticiones, 0 celdas con CER 100 %, 96/96
deterministas — no hace falta la marca «corrida fallida» de la trampa 99.

## Manifiesto

Los 48 rásteres PNG (5,9 MB, compartidos por `tess3` y `tess11`) se borraron;
`bench/salidas-psm-suelo/MANIFIESTO.md` trae nombre, tamaño, `sha256` y la orden
exacta que los reproduce. Los JSON, el texto de las 96 celdas y los logs se
versionan (son texto barato, y son la trazabilidad).

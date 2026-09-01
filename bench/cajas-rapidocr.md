# B22 (residuo) — el mecanismo de los picos de RapidOCR: el RECONOCEDOR, no el detector

Cierra el último pendiente de B22: *«sondear las cajas detectadas para explicar el
mecanismo de los picos de RapidOCR»*, que `bench/suelo-ppp.md` dejó como la siguiente
sonda útil y `bench/psm-suelo-ppp.md` no cubría (era de Tesseract).

**La hipótesis de partida —«un pico con pérdida de texto y no con mala lectura apunta
al DETECTOR»— se sondeó en ejecución y no se sostiene. Se sostiene la contraria: el
detector es estable y el reconocedor es el que falla, concentrado en el bloque de
letra más pequeña (7 pt).**

## Estado y condiciones de medida

**MEDIDO: 25 celdas** (`escaneado_d5c`, nativo 80 ppp: 12 puntos; `escaneado_d5a`,
nativo 90 ppp: 13 puntos — mismo barrido fino 100–150 más el nativo de cada uno).
Config: **RapidOCR v6 +R6** (`PP-OCRv6 small`, `Det.mean/std` ImageNet, `Det.thresh
.2`, `Det.box_thresh .45`, `Det.unclip_ratio 1.4`, `Det.max_candidates 3000`), la
misma que dio los picos en `suelo-ppp.md`. Entrada por **ndarray BGR de tres canales**
desde PNG sRGB — la misma vía que `suelo-ppp.md`, declarada porque la vía no es
intercambiable con la ruta (trampa 30). `filex.gpu.Lock` tomado por documento; VRAM
libre 9,0–9,1 GiB antes y después de cada tanda, muy por encima del guardián de
6 000 MiB.

**n = 3, no n ≥ 9, y hay que decir por qué.** Lo que se mide aquí —número de cajas,
área y texto por caja— es **determinista por construcción** (ya lo establecía
`suelo-ppp.md`: RapidOCR es determinista GPU en las 336 celdas), no una medida de
tiempo con ruido de máquina encima. n=3 sólo confirma que sigue siéndolo: **25 de 25
celdas dieron el mismo número de cajas y el mismo texto en las 3 repeticiones**. El
convenio de medianas de n≥9 del proyecto es para magnitudes con ruido (tiempo,
VRAM); esto no lo es, y forzar n=9 no habría cambiado un solo bit de la respuesta.

**Reproduce:**

```
"/d/Work/research/FileX/.venv-ai/Scripts/python.exe" \
  bench/salidas-cajas-rapidocr/cajas_rapidocr.py escaneado_d5c --native 80 --reps 3
"/d/Work/research/FileX/.venv-ai/Scripts/python.exe" \
  bench/salidas-cajas-rapidocr/cajas_rapidocr.py escaneado_d5a --native 90 --reps 3
```

**Dos testigos de ruido, tope 20 s:** `d5c` deriva 0,76×, nivel 1,37× (**limpia**,
80,2 s); `d5a` deriva 0,76×, nivel 1,24× (**limpia**, 75,5 s).

**Sondeado en ejecución, no deducido** (para no repetir el error ya pagado de deducir
de PaddleX y obtener lo contrario): `x.text_det.limit_side_len == 736`,
`x.text_det.limit_type == "min"` con esta config R6. Y el tamaño real que recibe el
detector, llamando al mismo `get_preprocess()` que usa `TextDetector.__call__`
internamente (no una reimplementación de la fórmula): a 80 ppp nativos de `d5c`
(708×517) el detector recibe **736×992**; a 100 ppp (885×646), **736×1024** — la
misma cifra que ya citaba `suelo-ppp.md`/`CLAUDE.md` sin decir de dónde salía. Por
encima de ~113 ppp para este documento el lado corto del ráster ya supera 736 y el
detector deja de reescalar: sólo redondea a múltiplos de 32 (120 ppp, min 775 →
768; 135 ppp, min 872 → 864).

## El hallazgo: 12 cajas, área estable, y el texto que falta se concentra en UNA línea de 7 pt

**MEDIDO**, `escaneado_d5c` (el documento con los picos: 0,7 % a 80, **18,5 a 100**,
9,7 a 120, 0,8 a 125, 0,3 a 130, **5,0 a 135**):

| ppp | cajas detectadas | área/página | caracteres de salida | bytes UTF-8 | CER |
|---:|---:|---:|---:|---:|---:|
| 80 (nativo) | 12 | 0,2165 | 609 | 642 | 0,7 % |
| **100** | **12** | 0,2230 | **499** | **523** | **18,5 %** |
| 105 | 12 | 0,2002 | 608 | 641 | 0,7 % |
| 110 | 12 | 0,2107 | 609 | 643 | 0,3 % |
| 115 | 12 | 0,2087 | 609 | 643 | 0,7 % |
| **120** | **12** | 0,1977 | **555** | **584** | **9,7 %** |
| 125 | 12 | 0,1914 | 609 | 641 | 0,8 % |
| 130 | 12 | 0,1893 | 608 | 642 | 0,3 % |
| **135** | **12** | 0,1907 | **581** | **614** | **5,0 %** |
| 140 | 12 | 0,1864 | 610 | 643 | 0,7 % |
| 145 | 12 | 0,1928 | 608 | 642 | 0,3 % |
| 150 | 12 | 0,1927 | 609 | 643 | 0,3 % |

**Las 12 celdas dan 12 cajas y un área de página del 19–22 %: ninguna caída de cajas
ni de área acompaña a los tres picos.** Lo que sí cambia es el texto de salida: en
las celdas buenas ronda 608–610 caracteres (641–643 bytes); en las tres pico cae a
**499 (100 ppp), 555 (120 ppp) y 581 (135 ppp)**. **Los 499 caracteres / 523 bytes a
100 ppp SON, byte a byte, la cifra que `suelo-ppp.md` ya citaba** («523 B frente a
641»): esta sonda la reproduce y le pone mecanismo detrás.

**El texto que desaparece es casi siempre el mismo bloque: `pequeña` (7 pt, las 4
líneas más chicas de la maqueta de `d4_texto.py`).** Con el detalle línea a línea
(`evaluar(...)` con la referencia como lista de líneas, no concatenada — así ya
consumía `suelo-ppp.md`, sólo que no publicaba el detalle):

| ppp | Línea que colapsa (bloque `pequeña`) | Similitud | Déficit aprox. |
|---|---|---:|---:|
| 100 | «¿Quién autorizó la excepción?…» | **28,3 %** | |
| 100 | «que la revisión ortográfica…» | **46,2 %** | ~110 car. (2 líneas) |
| 120 | «que la revisión ortográfica…» | **46,2 %** | ~54 car. (1 línea) |
| 135 | «¡Atención! Los códigos 7-B…» | **27,5 %** | ~29 car. (1 línea, parcial) |

**En TODAS las demás celdas —incluidas las siete sin pico— 1 a 3 de las 4 líneas de
`pequeña` ya muestran «FALLO» con similitud 86–98 %: ruido de fondo del cuerpo de
7 pt, presente en el documento entero y ajeno al pico.** Lo que separa una celda
buena de una celda pico no es que aparezca fallo en `pequeña` —eso pasa siempre—,
es que **una de esas líneas se hunde de ~96 % a 27–46 %**. `titulo`, `subtitulo` y
las 6 líneas de `cuerpo` (11 pt) están intactas o casi intactas (sim ≥98 %) en las
12 celdas: el pico no las toca.

## Control: `escaneado_d5a` (documento limpio) no reproduce los picos con las mismas cajas

**MEDIDO**, 13 celdas (80–150 ppp, nativo 90). De 90 a 150 ppp —el rango por encima
de su nativo, que es el que importa para el suelo— **12 cajas y 608–610 caracteres
en las 12 celdas, CER ≤1,0 % siempre**. La única celda con pérdida real es **80 ppp
(por DEBAJO de su nativo de 90)**: ahí sí bajan las cajas, **11 en vez de 12**, y el
texto cae a 553 caracteres (CER 10,7 %) — y la línea que colapsa (sim 27,8 %) es,
otra vez, **una línea del bloque `pequeña`** («es responsabilidad del área…»).

**Esto separa dos mecanismos distintos, y hay que no confundirlos:**

1. **Por debajo del nativo del documento (aquí sólo `d5a` a 80 < 90), sí hay pérdida
   de CAJA** (11 de 12): con menos información en el ráster de origen, el detector
   deja de proponer una región para la línea más pequeña. Es el mecanismo que uno
   esperaría — menos píxeles, menos caja — y no es sorprendente.
2. **Por encima del nativo (el régimen que importa para el suelo de 100 ppp y para
   B22), la pérdida NO es de caja: las 12 cajas siguen ahí, con área estable, y lo
   que falla es el RECONOCEDOR sobre el recorte de una línea concreta de 7 pt.**
   `escaneado_d5a` no sufre este segundo mecanismo en ningún punto de 90 a 150;
   `escaneado_d5c` lo sufre en tres puntos no contiguos (100, 120, 135) y no en los
   otros nueve. **La caja es la misma, el recorte que le llega al reconocedor no lo
   es** — algo en la interacción entre el degradado propio de `d5c` (sombra,
   curvatura o transparencia del papel, `bench/corpus-d5.md`) y el reescalado del
   recorte a la altura fija que usa el reconocedor decide, línea por línea y ppp por
   ppp, si esa lectura sale bien o sale rota.

## Conclusión sobre el mecanismo — y lo que NO queda resuelto

**MEDIDO: los picos de RapidOCR v6+R6 sobre `escaneado_d5c` no son un problema de
DETECCIÓN (cajas y área estables, 12/12 y ~20 % de página en las 12 celdas) sino de
RECONOCIMIENTO, y se concentran casi exclusivamente en el bloque de letra más
pequeña (7 pt) de la maqueta.** Esto refuta la hipótesis con la que se abrió esta
sonda («apunta al detector, no al reconocedor») y confirma la otra mitad: **es del
reconocedor**. Y como el mismo bloque `pequeña` es también el único que colapsa por
DEBAJO del nativo en `d5a` (mecanismo 1, pérdida de caja), **el bloque de 7 pt es el
punto frágil del documento en los dos regímenes, por dos mecanismos distintos**.

**PENDIENTE, y no lo cubre este informe:** por qué el reconocedor falla exactamente
en 100/120/135 ppp sobre `d5c` y no en los ocho puntos vecinos, cuando el recorte
detectado (misma caja, área estable) no cambia de forma visible en los metadatos que
esta sonda captura. Explicarlo exigiría inspeccionar el recorte (`crops`) que
`detect_and_crop` entrega al reconocedor —tamaño exacto tras su propio reescalado a
altura fija, no el de la caja— en los tres puntos pico contra los nueve buenos, y no
se ha hecho aquí. Es una sonda más fina que la pedida por el pendiente de B22 (que
pedía cajas y área, ya medidas) y queda como pregunta abierta, no como bloqueo de
este cierre.

## Manifiesto

Los 25 rásteres PNG (3,5 MB) se borraron; `bench/salidas-cajas-rapidocr/MANIFIESTO.md`
trae nombre, tamaño, `sha256` y la orden exacta que los reproduce. JSON, texto y logs
se versionan.

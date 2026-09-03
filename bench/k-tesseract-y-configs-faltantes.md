# B23, cierre — las 4 configuraciones que faltaban (ya cerradas por otro agente) y la rejilla 2×2 de pHYs/corpus en el `k` de Tesseract

**worker8, carril GPU nuevo** (`edicius2002/filex-ocr-k`). Encargo: cerrar `B23`
en sus dos pendientes declarados por `k-oem-acantilados.md` — las 4
configuraciones que faltaban del racimo de 9, y separar el efecto del `pHYs`
del efecto del corpus en el `k` de Tesseract con una rejilla 2×2.

## 0. Lo primero: la mitad 1 del encargo YA ESTABA CERRADA

Antes de tocar nada se comprobó `git log` sobre `bench/salidas-k-oem-acantilados/`:
**las 4 configuraciones que faltaban (Docling defecto, Docling+R6, RapidOCR v6
small defecto, RapidOCR v5 mobile defecto) ya están medidas**, por worker1, en
`bench/vivo-y-residuos.md` (commit `58eeca4`, 02/09), **ya integrado en esta
rama** — `git merge-base --is-ancestor 58eeca4 HEAD` confirma que es ancestro
del `HEAD` de este *worktree*. Los cuatro `k` publicados allí:

| Configuración | `k` por mínimo arrepentimiento | Arrepentimiento máx. |
|---|---:|---:|
| Docling defecto | 1,125¹ | 8,4 pt |
| Docling + R6 | 1,60 | 8,8 pt |
| RapidOCR v6 small defecto | 1,25 | 1,2 pt |
| RapidOCR v5 mobile defecto | 1,00 | 4,0 pt |

¹ curva plana en ese tramo, no un único mínimo.

Los cuatro caen **dentro** del rango ×0,875–×1,60 que `ENCARGO.md` cita como ya
publicado — no hay hallazgo de rango que reportar ahí. **No se repite esta
medición**: repetirla habría sido la trampa 69 al revés (medir de nuevo lo que
ya está medido no añade nada; lo que sí se hace es la mitad 2, que es la que de
verdad faltaba). Esta sección existe solo para que quien lea `ENCARGO.md`
entienda por qué este informe no trae una rejilla nueva para esas 4
configuraciones.

Lo único que este informe **añade** sobre la mitad 1: el resto del documento se
dedica entero a la mitad 2, que es la que seguía `PENDIENTE` de verdad tras
`bench/vivo-y-residuos.md`.

---

## 1. La rejilla 2×2 de pHYs y corpus en el `k` de Tesseract

### 1.1 El problema, tal como estaba declarado

`k-oem-acantilados.md` §B23 midió el `k` de Tesseract sobre la familia `d5` **con
pHYs declarado** (×1,40 `psm 3` / ×1,60 `psm 11`) y lo declaró **no comparable**
con el `k` publicado en `CLAUDE.md` (×0,875 / ×0,75, medido **sin** declarar pHYs
sobre el corpus viejo — `escaneado_d3`, `escaneado_d4`, `escaneado_d4c`,
`patologico_escaneado`), porque mezclaba dos variables a la vez: **corpus** y
**pHYs**. Faltaban las dos celdas cruzadas para separarlas.

### 1.2 Método: el mismo ya usado, sin inventar uno nuevo

- **`k` por mínimo arrepentimiento**, la misma fórmula de `tablas_km.py` y
  `CLAUDE.md` trampa 8: `regret(k) = media_documentos[CER(doc,k) − min_f
  CER(doc,f)]`, nunca el óptimo de un solo documento.
- **Rejilla de 7 factores**, la de `k-oem-acantilados.md`/B23
  (×0,75/×0,875/×1,00/×1,125/×1,25/×1,40/×1,60) — **no** los 11 factores del
  `k-por-motor.md` original. Se eligió ésta, y no la más ancha, para que **las
  cuatro celdas del 2×2 compartan exactamente la misma rejilla**: comparar un
  óptimo hallado en 11 puntos con uno hallado en 7 mezclaría rejilla con pHYs y
  corpus, una tercera variable no controlada que el propio encargo advierte
  evitar (ahí lo advierte para el `--psm`; aplica igual de bien aquí).
- **`--psm` fijado por celda** (3 y 11 por separado, nunca mezclados), como pide
  el encargo citando `CLAUDE.md` trampa 8 (el `--psm` no es separable del `k`).
- **Documentos**: los mismos cuatro de cada corpus que ya usaban las celdas
  publicadas — `escaneado_d3`/`escaneado_d4c`/`patologico_escaneado`/`escaneado_d4`
  (corpus viejo) y `escaneado_d5a`/`escaneado_d5c`/`escaneado_d5`/`escaneado_d5b`
  (familia `d5`).
- **Evaluador**: `ocr_eval_d4.py` (copia byte a byte de
  `bench/salidas-k-motor/`, `sha256` verificado antes de usarla) para el corpus
  viejo — el mismo que produjo las cifras ya publicadas de `d3`/`d4`/`d4c`/`patológico` —
  y `bench/scripts/ocr_eval.py` con `REF = d4_texto.BLOQUES` aplanado para la
  familia `d5` — el mismo que usó `b23_k_d5.py`. Verificado que las dos vías dan
  el **mismo cálculo** (Levenshtein global sobre la referencia aplanada,
  normalización `norm_acentos` idéntica) antes de mezclarlas en una tabla.

### 1.3 Las CUATRO celdas: dos ya medidas (no se repiten), dos nuevas

| | **sin pHYs** | **con pHYs** |
|---|---|---|
| **corpus viejo** | ya medida — `bench/salidas-k-motor/json/tesseract_cpu_*` | **NUEVA** — `b25_phys_corpus.py viejo-phys` |
| **corpus `d5`** | **NUEVA** — `b25_phys_corpus.py d5-nophys` | ya medida — `bench/salidas-k-oem-acantilados/json/b23_tess{3,11}.json` |

**Receta de ráster, declarada para que cada comparación diga qué aísla:**

- Fila **corpus viejo**: las dos celdas usan `-colorspace Gray` (la que ya
  usaba `preparar_km.py`); la nueva celda (con pHYs) le añade **solo**
  `-units PixelsPerInch -density N`. La comparación sin-pHYs↔con-pHYs de esta
  fila aísla el pHYs solo.
- Fila **`d5`**: las dos celdas usan `-colorspace sRGB` (la que ya usaba
  `b23_k_d5.py:raster_declarado` para Tesseract); la nueva celda (sin pHYs) le
  **quita solo** `-units PixelsPerInch`. Misma propiedad: aísla el pHYs solo.
- Las dos filas no comparten colorspace entre sí (Gray el corpus viejo, sRGB
  la familia `d5`) porque cada una hereda la receta que su celda ya publicada
  tenía — no se cambia una convención ya usada solo para este informe.

**Control, porque ese colorspace distinto entre filas podría ser una cuarta
variable sin comprobar — MEDIDO, 4 de 4 celdas idénticas.** Se rasterizó
`escaneado_d5a`×1,00 en Gray+pHYs-declarado y `escaneado_d4c`×1,00 en
sRGB+sin-declarar, y se comparó contra la celda ya existente con el colorspace
contrario y el mismo tratamiento de pHYs:

| documento | pHYs | Gray | sRGB | ¿coincide? |
|---|---|---:|---:|---|
| `escaneado_d5a` ×1,00, `psm 3` | declarado | 1,2 % | 1,2 %publicado | **sí** |
| `escaneado_d5a` ×1,00, `psm 11` | declarado | 1,2 % | 1,2 % publicado | **sí** |
| `escaneado_d4c` ×1,00, `psm 3` | sin declarar | 1,85 % publicado | 1,85 % | **sí** |
| `escaneado_d4c` ×1,00, `psm 11` | sin declarar | 2,68 % publicado | 2,68 % | **sí** |

**El colorspace no mueve el CER de Tesseract en ninguna de las 4 celdas
comprobadas**: el 2×2 aísla el pHYs, no un pHYs+colorspace confundidos.

### 1.4 Medición: 112 celdas nuevas, deterministas salvo una, `rc=0` en todas

`b25_phys_corpus.py viejo-phys --reps 3` (56 celdas: 4 docs × 7 factores × 2
`psm`) y `b25_phys_corpus.py d5-nophys --reps 3` (56 celdas) — CPU pura
(Tesseract nativo, no toca la GPU; **no se tomó el lock**, no hace falta
declarar VRAM para esto). Las dos tandas salieron `limpia` por los dos testigos
de ruido (deriva 0,97/0,66, nivel 1,29×/1,69× sobre el reposo, ningún testigo
topado). **56/56 y 55/56 deterministas** (3 repeticiones idénticas), **112/112
con `rc=0`** en el proceso de Tesseract.

**La única celda no determinista, investigada, no reproducida (ronda de 9
repeticiones): `escaneado_d5a` ×1,60 `psm 3`, sin pHYs — `[0,5, 0,5, 2,0]` en
las 3 repeticiones originales.** Repetida con 9 repeticiones más: **9 de 9 dan
0,5 %**. El 2,0 % de la primera tanda fue un evento raro y no reproducido de
Tesseract (posible condición de carrera interna del motor LSTM, no
investigada más allá — dos intentos, y el segundo la resuelve). El valor que
se usa en el análisis de abajo es **0,5 %**, que además coincide exacto con la
celda con-pHYs de ese mismo punto — **de haber quedado el 2,0 % sin repetir, se
habría contado como un efecto de pHYs de 1,5 puntos que en realidad era ruido
de medición del motor**, no de la variable que se está midiendo.

### 1.5 El 2×2, con el `k` por mínimo arrepentimiento y su arrepentimiento

**MEDIDO.**

**`--psm 3`**

| | sin pHYs | con pHYs |
|---|---|---|
| **corpus viejo** | **×0,875** (regret 0,34/1,34) — ya publicado | **×1,00** (regret 0,25/0,84) — nueva |
| **corpus `d5`** | **×1,40** (regret 0,30/0,70) — nueva | **×1,40** (regret 0,30/0,70) — ya publicado |

**`--psm 11`**

| | sin pHYs | con pHYs |
|---|---|---|
| **corpus viejo** | **×0,75** (regret 2,51/7,88) — ya publicado | **×0,75** (regret 3,65/12,41) — nueva |
| **corpus `d5`** | **×1,60** (regret 0,08/0,20) — nueva | **×1,60** (regret 0,08/0,20) — ya publicado |

(`regret medio/regret máx.`, en puntos de CER, sobre los 7 factores comunes.)

**El resultado central: en la familia `d5`, con pHYs y sin pHYs dan EL MISMO
`k` óptimo y EL MISMO arrepentimiento, en los dos `--psm`.** Con `psm 11` el
arrepentimiento coincide a la centésima (0,08/0,20 en las dos celdas) porque
**las 28 celdas son idénticas byte a byte** entre con-pHYs y sin-pHYs — 0,00
puntos de diferencia media, 0,00 de diferencia máxima. Con `psm 3` casi
idénticas: 25 de 28 celdas exactas, y las 3 que difieren mueven como mucho 8,2
puntos en una sola celda (ver §1.7).

**En el corpus viejo, pHYs sí mueve el óptimo — pero solo en `psm 3`, y
poco: de ×0,875 a ×1,00 (un paso de rejilla), con el arrepentimiento BAJANDO de
0,34 a 0,25.** En `psm 11` el óptimo no se mueve (×0,75 en las dos), aunque el
arrepentimiento sí sube (2,51 → 3,65), por un mecanismo que §1.7 aísla: no es
degradación real del documento informativo, es una zona de alucinación de
`escaneado_d3` que ya estaba documentada.

### 1.6 Refutación parcial del enunciado de `B23`

El enunciado decía que el `k` con pHYs y el `k` sin pHYs **no eran
comparables** porque mezclaban corpus y pHYs sin una celda que los separara.
Con las celdas que faltaban medidas: **la parte de "mezclan dos variables" era
cierta, pero el peso de las dos NO es simétrico.** El corpus explica casi toda
la diferencia entre ×0,875/×0,75 y ×1,40/×1,60; el pHYs, aislado, mueve el
óptimo **como mucho un paso de rejilla (×0,875→×1,00) y en una sola de las
cuatro combinaciones (corpus viejo, `psm 3`)** — en las otras tres el óptimo no
se mueve un solo factor.

**Descomposición del salto ×0,875→×1,40 (`psm 3`):**

| paso | de | a | tamaño |
|---|---:|---:|---:|
| corpus, sin pHYs (C→B) | ×0,875 | ×1,40 | ×1,60 |
| corpus, con pHYs (A→D) | ×1,00 | ×1,40 | ×1,40 |
| pHYs, corpus viejo (C→A) | ×0,875 | ×1,00 | ×1,14 |
| pHYs, corpus `d5` (B→D) | ×1,40 | ×1,40 | ×1,00 (sin cambio) |

El corpus mueve el óptimo ×1,40–1,60; el pHYs, aislado, ×1,00–1,14. **No es un
reparto a medias: es abrumadoramente el corpus.**

Y para `psm 11` el reparto es aún más desequilibrado: el corpus mueve el
óptimo ×2,13 (×0,75→×1,60) en las dos filas por igual, y el pHYs no lo mueve
en absoluto en ninguna de las dos (×0,75→×0,75 en el corpus viejo, ×1,60→×1,60
en `d5`).

### 1.7 Por qué el pHYs parecía valer «hasta 47 puntos», y sigue siendo cierto — el mecanismo es DE UN DOCUMENTO, no del corpus

Esto no contradice `CLAUDE.md` trampa 8/29 (el pHYs mueve Tesseract hasta 33-47
puntos): **ese efecto es real, sigue siendo real, y este informe lo reproduce
exacto** (`escaneado_d4` ×1,00 `psm 3`: 84,56 % sin pHYs, 51,34 % con pHYs —
33,22 puntos, el mismo número publicado). Lo que cambia es la **atribución**:
ese efecto grande **no es del corpus viejo en general — es de UN documento
dentro de él, `escaneado_d4`**, con un patrón caótico y no monótono a lo largo
de la rejilla:

| factor | sin pHYs | con pHYs | diferencia |
|---:|---:|---:|---:|
| ×0,75 | 87,25 % | 81,88 % | −5,37 |
| ×0,875 | 72,48 % | 50,50 % | **−21,98** |
| ×1,00 | 84,56 % | 51,34 % | **−33,22** |
| ×1,125 | 89,09 % | 86,41 % | −2,68 |
| ×1,25 | 85,57 % | 89,60 % | +4,03 |
| ×1,40 | 89,26 % | 91,61 % | +2,35 |
| ×1,60 | 86,58 % | 71,14 % | −15,44 |

Los otros tres documentos del corpus viejo **casi no se mueven**:
`escaneado_d4c` (misma familia de generador que `d4`, geometría distinta) se
mueve como mucho 0,17 puntos en las 7 celdas; `escaneado_d3` y
`patologico_escaneado` no discriminan en absoluto en `psm 3` (siempre 100,00 %
y 0,00 % respectivamente, ya lo decía `k-por-motor.md` §2.1). **El «hasta 33-47
puntos» del pHYs es la huella de un documento (`escaneado_d4`), no la huella
del corpus** — y ese documento pertenece solo al corpus viejo: en la familia
`d5` no hay ningún documento con este comportamiento, y por eso el efecto
desaparece casi entero al cambiar de corpus.

Para `psm 11`, la celda que más se mueve con pHYs no es `d4` (que se mueve
como mucho 8,4 puntos) sino `escaneado_d3`, y ahí el mecanismo es otro ya
documentado: la zona es de **alucinación** (CER de 68 % a 887 %, `CLAUDE.md`
"la curva de Tesseract en `d3` no tiene un óptimo: tiene una pendiente"), así
que una diferencia de 32,91 puntos entre dos números ya sin sentido (541,77 %
frente a 574,68 %) no es una señal real de degradación — es ruido dentro de
una zona ya marcada como no informativa (‡ en `k-por-motor.md` §2.1).

**En la familia `d5`, las 3 celdas de 28 que sí difieren con `psm 3` (excluida
la no determinista de §1.4, que resultó ser ruido)** están en `escaneado_d5`
×1,25 (2,30 %→2,20 %, 0,10 pt) y `escaneado_d5b` ×1,25 (25,50 %→17,30 %, **8,20
pt, la mayor diferencia real medida en toda la familia `d5`**). Ninguna se
acerca a la magnitud de `escaneado_d4`.

### 1.8 Respuesta a la pregunta del encargo

**«Cuánto de la diferencia ×1,40/×1,60 → ×0,875/×0,75 es pHYs y cuánto es
corpus»: con la rejilla de 7 factores compartida y las cuatro celdas medidas,
el reparto es abrumadoramente de CORPUS.** El pHYs, aislado del corpus, mueve
el óptimo como mucho un paso de rejilla en una sola de las cuatro
combinaciones (corpus viejo × `psm 3`: ×0,875→×1,00) y no lo mueve en absoluto
en las otras tres. **No se puede separar del todo con un solo número porque el
efecto de pHYs no es aditivo ni uniforme — es la huella de UN documento
(`escaneado_d4`) que solo existe en el corpus viejo**, así que la pregunta
"cuánto pesa el pHYs" tiene una respuesta distinta según si `escaneado_d4`
está en la muestra o no. Con él dentro (que es como se midió el `k` publicado
en `CLAUDE.md`), el pHYs sube el arrepentimiento del `psm 11` un 45 % (2,51→3,65)
y baja el del `psm 3` un 26 % (0,34→0,25); sin él —la familia `d5` entera— el
pHYs no mueve el arrepentimiento ni un centésimo en ninguno de los dos `--psm`.

**El `k` con pHYs declarado y el `k` sin declarar SÍ son comparables** —el
enunciado original de `B23` queda refutado en la parte que importa para el
adaptador: fijar `--psm` y usar mínimo arrepentimiento sobre ≥4 documentos
(la disciplina que ya exige `CLAUDE.md` trampa 8) absorbe casi toda la
diferencia. Lo que NO es comparable, y sigue sin serlo, es el **CER de un
documento suelto** (`escaneado_d4`) medido con y sin declarar: eso sigue
moviendo hasta 33 puntos, y **esa cifra —no el `k` fijo— es la que exige
declarar el pHYs con el que se midió**, como ya decía la trampa 29.

---

## 2. Declaraciones

- **Intérprete**: `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe`
  (Windows, no WSL) para todo lo de este informe — mediciones nuevas y
  `pytest`/`ci/integridad.py`. No hace falta `.venv-ai` ni `.venv-paddle`:
  Tesseract se invoca como proceso externo, sin dependencias de GPU/torch.
- **Entorno**: sin Docker levantado (no hace falta para Tesseract nativo ni
  para la suite de este *worktree*); ImageMagick 7.1.2-21 nativo; Tesseract
  5.5.0.20241111 nativo con `TESSDATA_PREFIX` apuntando a
  `C:\Program Files\PDFgear\tessdata`.
- **Qué quedó fuera y por qué**: la rejilla de factores por encima de ×1,60
  para EasyOCR y `psm 11` (pendiente ya declarado en `k-oem-acantilados.md`,
  no forma parte de este encargo). `ci/integridad.py` corre `2 skipped` en la
  suite general por motivos ya conocidos y no relacionados con este trabajo
  (falta el ráster de `preparar_h6.py` y `FILEX_PRUEBAS_SIDECAR=1`).
- **Estado de la máquina**: VRAM libre 10 907 de 12 288 MiB al momento de
  escribir esto (`nvidia-smi`), muy por encima del guardián de 6 000 — **no se
  usó ni se tomó el lock de GPU**, porque las cuatro celdas de este informe son
  Tesseract puro (CPU); tomarlo habría sido ceremonia sin función. Sesión
  remota activa (no verificado si lo estaba durante esta sesión concreta, y es
  irrelevante: sin GPU, sin contención de VRAM que declarar).

**Suite de pruebas** (`.venv-mcp-filex`, Windows, con Docker no levantado):

```
pytest pruebas/ -q
```

**460 passed · 3 skipped · 130 subtests passed** (`207,09 s`), con **1 fallo
transitorio** en la primera pasada:
`DuenoMuerto::test_un_working_sin_dueno_vivo_se_detecta_y_se_cierra` —
exactamente el que `ENCARGO.md` anticipa como el residuo conocido de `N30`
bajo carga (worker2 ya lo documentó como falso positivo intermitente,
`bench/pruebas-de-carrera-y-acciones.md`). **Repetido aislado: pasa** (`1
passed in 3,18s`). No se investigó más porque ya está diagnosticado y no toca
ningún fichero de este informe.

```
python ci/integridad.py
```

Las 9 comprobaciones en **OK** tras registrar este informe y sus dos ficheros
nuevos en `ESTADO-Y-REPARTO.md` (`informes-registrados`, `manifiestos`).

## 3. Ficheros de este informe

- `bench/salidas-k-tesseract-configs/b25_phys_corpus.py` — mide las dos celdas
  nuevas del 2×2.
- `bench/salidas-k-tesseract-configs/analisis_2x2.py` — carga las cuatro
  celdas (dos ya medidas, dos nuevas) y calcula el `k` por mínimo
  arrepentimiento sobre la rejilla común de 7 factores.
- `bench/salidas-k-tesseract-configs/ocr_eval_d4.py`, `d4_texto.py` — copias
  byte a byte, `sha256` verificado.
- `bench/salidas-k-tesseract-configs/{json,texto,logs}/` — celdas crudas,
  texto de cada lectura de Tesseract y logs de las dos tandas.
- `bench/salidas-k-tesseract-configs/MANIFIESTO.md` — los 58 rásteres PNG
  (no versionados), con `sha256` y la orden exacta que los reproduce.

# La señal de A7 no sobrevive fuera de su corpus, su ahorro se midió contra otra orden, y dos agujeros del núcleo que sí se cierran

**Agente N3** · 2026-08-28 · worktree aislado, **sin GPU** (H2 la tenía en
exclusiva; no se tocó su lock).
Encargos: **N18** (llevar a producción la señal que midió N16), **N19**
(`DirectorioDeTrabajo.recoger`), **N20** (un destino que es un directorio).

Salidas y órdenes exactas: `bench/salidas-fidelidad-n/MANIFIESTO.md`.

---

## 0. Lo que sale de aquí, en nueve líneas

1. **La medida de N16 se reproduce al centésimo.** Las nueve tasas separan, la
   meseta va de 0,008 a 0,13, 27 de 27 y 0 falsos de 45. **Idéntica.** — MEDIDO
2. **Y no sobrevive al corpus siguiente.** Con tres fuentes que N16 no tenía y
   tres códecs más: **11 falsos positivos de 152 conversiones legítimas, y 6 de
   ellos irreductibles** —los otros 5 ya son `fallo` hoy—, con las clases
   **solapadas** (peor mala +0,0059, mejor buena −0,6724). — MEDIDO
3. **El mecanismo es el que ya mató al escalón de asimetría en §2.4:** Opus
   colapsa el estéreo a mono y **se come un canal legítimamente flojo**. Desde
   la salida, «Opus tiró un canal de −56 dBFS» y «alguien lo silenció antes de
   codificar» son el mismo suceso. — MEDIDO
4. **Hay una versión que sí separa** —correlación < 0,05 **con suelo relativo de
   −12 dB**: 15 de 23, **0 falsos de las 147 buenas que hoy pasan**— y **no se
   puede escribir**: necesita
   alineamiento, el alineamiento necesita una FFT, y `filex` **no tiene
   dependencias por decisión escrita**. Sin alinear son **19 falsos**. — MEDIDO
5. **El ahorro de N16 se midió contra una orden que A7 no ejecuta.** Sus
   «364,0 ms» son `astats=metadata=1:reset=0`; A7 corre
   `measure_overall=none:measure_perchannel=…`. En la misma tanda: **166,24 ms
   lo que A7 gasta, 465,89 ms el control de N16 (×2,80), y su vía cuesta ×1,395
   de A7, no ×0,50.** — MEDIDO
6. **Los dos `astats` NO hacen falta** —una sola invocación da los mismos RMS—
   **y sustituirlos no ahorra nada medible**: ×0,987 y ×0,955 en dos tandas, por
   debajo del ruido entre configuraciones (trampa 36). **No se aplica.** — MEDIDO
7. **Lo que sí se aplica: el punto ciego no es de bitrate, es de OPUS, y se
   DECLARA.** A 32 kb/s sobre el mismo fallo, mp3 y aac atrapan **6 de 6** y
   Opus **1 de 6**. A7 devolvía `cobertura = True` donde provablemente no ve.
   Ahora devuelve `False`. Coste: cero procesos. — MEDIDO
8. **N19 era peor de lo que decía el pendiente:** `recoger()` pisaba **también
   el fichero que otro proceso tenía abierto** (88 B → 20 B, sin excepción). Le
   vale la misma solución que al `move`. — MEDIDO
9. **N20: el `errno` NO distingue los dos casos** —directorio y ocupante dan los
   dos `EACCES`/`WinError 5`—, así que el motivo mentía por construcción. — MEDIDO

**La restricción que manda: 0 falsos positivos sobre las 53, antes y después, y
0 de 53 salidas cambian de veredicto o de reglas.** Suite en **312 pruebas
(311 pass + 1 de reloj que pasa sola), 6 skipped**; base 298. **La huella NO
caduca** — y es la tercera vez que un encargo lo da por hecho.

---

## 1. Método, y lo que hubo que arreglar antes de medir

* **Corpus.** `git lfs checkout` en el worktree: `corpus/imagen/tipico.png`
  pasó de 130 B a **42 855**. Trampa 34, pagada por sexto agente consecutivo.
* **Las 53.** No se versionan; se regeneraron con
  `bench/salidas-firmas-cierre/_regenera53.py`, que las deja en el scratchpad.
  **`bench/salidas-referencia/` no se escribe**: `regresion_53_n.py` —variante
  propia del arnés compartido— las localiza con `FILEX_REF53`.
* **Confinamiento.** Todos los arneses trabajan en un `mkdtemp` que se lista
  antes y después y se borra entero (R18, trampa 21). Ningún fichero apareció
  fuera; los censos están en cada JSON.
* **Timeouts** explícitos (180–300 s) en toda invocación, `stdin=DEVNULL`,
  argumentos en array, sin shell.
* **Sin GPU** y sin tocar el lock de GPU.

---

## 2. N18 — la señal

### 2.1 Reproducida, al centésimo — MEDIDO

`a7_repro_n.py` es la **copia literal** del arnés de N16 (trampa 58: reproduce
la medida ajena antes de arreglarla). 90 celdas, deterministas.

| | N16 publicó | Reproducido aquí |
|---|---:|---:|
| Ventaja cruzada, hueco (todas las tasas) | −0,7983 | **−0,7983** |
| `corr(Rsal,Rent)`, hueco a 6k / 8k / 12k | +0,1312 / +0,1493 / +0,1599 | **+0,1312 / +0,1493 / +0,1599** |
| … a 16k / 24k / 32k | +0,1658 / +0,7556 / +0,9652 | **+0,1658 / +0,7556 / +0,9652** |
| … a 48k / 64k / 96k | +0,9687 / +0,9903 / +0,9932 | **+0,9687 / +0,9903 / +0,9932** |
| Meseta del umbral | 0,008 – 0,13, 27/27, 0 falsos de 45 | **idéntica** |

**No hay nada que discutir del trabajo de N16 dentro de su corpus.** Lo que
sigue no lo contradice: lo saca de él.

### 2.2 Fuera de su corpus, el hueco desaparece — MEDIDO

`a7_corr_ancho.py`: **264 celdas** = 8 fuentes × 14 destinos × 2 clases, más 5
recodificaciones legítimas brutales por fuente. Los tres ejes nuevos responden a
tres trampas concretas:

* **Trampa 53 (la cobertura depende del DESTINO).** El mismo fallo va a `opus`,
  `mp3`, `aac` (con pérdida) **y a `flac` y `wav`** (sin pérdida).
* **Trampa 50 (varía la entrada).** Tres fuentes que N16 no tenía: **ruido**
  descorrelacionado —lo que peor lleva un códec—, **fase invertida**
  (`corr(L,R) = −1`) y **canal derecho flojo** (−40 dB respecto al otro, pero
  audible: −56,42 dBFS, muy por encima del umbral de −60 de A7).
* **La tercera clase**: `lowpass=500`, `highpass=3000`, remuestreo a 8 kHz,
  `pcm_u8` y una mezcla a mono. Destrozan la onda **sin perder un canal**.

Con el umbral que N16 propone (0,05) sobre el mínimo de las correlaciones de los
canales audibles:

| Umbral | atrapa | FP buenas | FP brutales |
|---:|---:|---:|---:|
| < 0,008 | 84/84 | **6/112** | **5/40** |
| < 0,05 | 84/84 | **6/112** | **5/40** |
| < 0,13 | 84/84 | 7/112 | 6/40 |

**La meseta de «0 falsos» ya no existe: es 6 falsos en toda la meseta.** Y el
hueco por destino se invierte justo donde N16 lo medía:

| Destino | peor mala | mejor buena | hueco | A7 hoy |
|---|---:|---:|---:|---:|
| opus 6k | +0,0029 | **−0,0386** | **−0,0415** | 0/6 |
| opus 8k | +0,0059 | **−0,0356** | **−0,0415** | 0/6 |
| opus 16k | +0,0048 | **−0,0350** | **−0,0398** | 0/6 |
| opus 32k | +0,0056 | +0,1894 | +0,1838 | 1/6 |
| opus 96k | +0,0044 | +0,6001 | +0,5957 | 6/6 |
| mp3 32k | +0,0000 | +0,2768 | +0,2768 | 6/6 |
| aac 32k | +0,0000 | +0,3397 | +0,3397 | 6/6 |
| flac / wav | +0,0000 | +1,0000 | +1,0000 | 6/6 |

### 2.3 El mecanismo, celda a celda — MEDIDO

`a7_rejilla.py`. Primero hay que quitar el doble recuento: **de las 84 malas,
61 ya son `fallo` HOY** por el escalón de silencio de A7, y **5 de los 11 falsos
positivos brutos también lo son** — y son exactamente las cinco de `fase_inv`:
Opus mezcla L y −L, la salida entera queda en **−98,49 dBFS**, la conversión es
realmente mala y A7 ya la suspende. Contarlas como falso positivo nuevo sería
contarlas dos veces (trampa 25 en versión de recuento).

Con eso fuera quedan **23 malas que hoy se escapan** y **147 buenas vivas**, y
los seis falsos positivos que quedan son de dos familias:

| Fuente | Destinos que rompe | corr | nivel del canal |
|---|---|---:|---|
| `flojo` | opus 6k, 8k, 16k, y dos brutales | −0,0386 … −0,0350 | **−40,04 dB** bajo el otro |
| `distintos` | `highpass=3000` | **−0,6724** | −15,15 dB bajo el otro |

**Es la trampa 50 otra vez, y sobre la misma regla.** `contrato-familia-resvg.md`
§2.4 retiró el escalón de asimetría porque *«Opus a tasa baja colapsa el estéreo
a mono, y eso es una conversión legítima»*. **La correlación cae por lo mismo:**
cuando un canal va 40 dB por debajo, el colapso lo **sustituye**, y desde la
salida eso es indistinguible del canal silenciado a mano. La señal no ve
intención.

### 2.4 La versión que SÍ separa — y por qué no se puede escribir — MEDIDO

Añadiendo una segunda variable —el nivel del canal **relativo al canal más
fuerte de la entrada**, que es un dato de la entrada y por tanto conocido antes
de juzgar—:

| corr < | rel ≥ −100 dB | ≥ −40 | ≥ −20 | ≥ −15 | **≥ −12** | ≥ −6 |
|---:|---|---|---|---|---|---|
| 0,008 | 23/23 · FP 6 | 19/23 · FP 1 | 19/23 · FP 1 | 15/23 · **FP 0** | 15/23 · **FP 0** | 12/23 · FP 0 |
| 0,05 | 23/23 · FP 6 | 19/23 · FP 1 | 19/23 · FP 1 | 15/23 · **FP 0** | 15/23 · **FP 0** | 12/23 · FP 0 |
| 0,13 | 23/23 · FP 8 | 19/23 · FP 3 | 19/23 · FP 3 | 15/23 · FP 2 | 15/23 · FP 2 | 13/23 · FP 2 |

Hay meseta —`corr < 0,008…0,10` × `rel ≥ −15…−6`— y su celda es **15 de 23
capturas nuevas con 0 falsos de las 147 buenas vivas**. A7 pasaría de 61/84 a 76/84.

**Y ahí se acaba, porque hay un requisito que no se puede pagar.** La celda
buena es la de `r_ref`: la correlación **alineada**, con la FFT de N16. Sin
alinear:

| `r_grafo` − `r_ref` (528 pares) | mediana | p10 | peor caída |
|---|---:|---:|---:|
| | **0,0000** | **−0,2166** | **−1,9785** |

y la misma rejilla con la métrica no alineada da, en su mejor celda,
**15/23 con 19 FALSOS POSITIVOS**. El desfase importa exactamente donde importa
el corpus: **es 0 en las 191 celdas de mp3, aac, flac y wav, y solo Opus (y el
remuestreo) lo mueven** —de −181 a +7 muestras—, que es justo el punto ciego que
la señal venía a cubrir.

**Alinear necesita una FFT o un barrido, y `filex` no tiene dependencias.** No es
una preferencia: `pyproject.toml` lo dice —*«añadir una dependencia aquí obliga a
justificar por qué no se puede hacer en proceso»*—, y el verificador entero está
escrito con biblioteca estándar. Se sondearon dos vías antes de rendirse:

* **La identidad de los tres RMS**, `RMS(x−y)² = RMS(x)² + RMS(y)² − 2·cov(x,y)`,
  evaluada en **una sola invocación de ffmpeg**. Funciona —FLAC idéntico da
  r = 1,0000 exacto— y es la que da los 19 falsos por no alinear.
* **`audioop`** (que sí traería `findfit` en C) **está deprecado en 3.11 y
  eliminado en 3.13**, y `requires-python` es `>=3.11`: una regla que
  desaparece sola en la siguiente versión de Python es peor que no tenerla.

**Conclusión aplicada: la señal NO entra.** Está medida, está el valor exacto de
lo que daría (+15 capturas, 0 falsos), y está el precio (una dependencia o una
FFT en Python puro). Es una decisión de arquitectura, no de este reparto.

### 2.5 ¿Sustituye a A7 o se suma? — la pregunta estaba mal planteada, y hay número

N16 §8bis.4 lo dejó así: *«Si sustituye a los dos `astats`: 183,1 ms frente a
364,0. La mitad. Esta es la propuesta.»*

**Los 364,0 ms no son los de A7.** El arnés de N16 midió su control con
`ffmpeg -i X -af astats=metadata=1:reset=0 -f null -`, es decir **todas** las
medidas de `astats`, sin `-map 0:a:0` y sin `-vn`. A7 corre
`astats=measure_overall=none:measure_perchannel=Peak_level+RMS_level` con
`-map 0:a:0 -vn -sn`, que es otra cosa. Y el propio informe del que N16 parte lo
decía: `contrato-familia-resvg.md` §2.2 publica **«A7 completa (dos sondas):
≈ 110–147 ms»**. Nadie cruzó las dos cifras.

Medido **todo en la misma tanda** (n=15, testigos limpios: deriva 17,5 → 19,7 ms,
ratio 1,12; proceso 42,3 → 35,9 ms), sobre 8,0 s de estéreo a 48 kHz — trampa 59,
que exige medir también la versión histórica:

| Trozo | mediana | p90 |
|---|---:|---:|
| `astats` de la entrada (mitad de A7) | 96,23 ms | 101,05 |
| `astats` de la salida (mitad de A7) | 70,01 ms | 74,52 |
| **A7 hoy, las dos** | **166,24 ms** | |
| El grafo, una sola invocación | 164,04 ms | 171,46 |
| La vía de N16 (numpy, FFT) | 231,85 ms | 261,38 |
| **CONTROL — los dos `astats=metadata=1:reset=0` de N16** | **465,89 ms** | |

**Las dos respuestas, con número:**

* **¿Sustituye o se suma?** Ni una cosa ni otra en los términos de N16: su vía
  **no es la mitad, es ×1,395** de lo que A7 gasta hoy (×1,460 en una segunda
  tanda). El «×0,50» venía de dividir entre un control **×2,80 más caro que la
  regla real**.
* **¿Siguen haciendo falta los dos `astats`?** **Técnicamente no**: una sola
  invocación devuelve los mismos RMS por canal —y encima el RMS de la
  diferencia—. **Pero sustituirlos no ahorra nada medible**: ×0,987 y ×0,955 en
  dos tandas, es decir 2,2 y 7,4 ms sobre 166, **por debajo del ruido entre
  configuraciones de la misma tanda** (trampa 36: mide el trozo, no la
  diferencia entre dos totales que lo contienen). Y trae dos modos de fallo
  nuevos —`amerge` exige `channel_layouts` declarado, y solo se saben nombrar
  mono y estéreo—. **No se aplica.**

*(El acuerdo numérico sí está medido, por si alguien retoma la vía: RMS desde
PCM contra `astats`, **528 canales, |dif| máx 0,0011 dB, mediana 0,00, 0
discordes**. La sustitución es correcta; lo que no se sostiene es su motivo.)*

### 2.6 Lo que SÍ se aplica: el punto ciego no es de bitrate, es de Opus — MEDIDO

`contrato-familia-resvg.md` §2.5 lo tituló *«el punto ciego de A7 a bitrate
bajo»*, y midió nueve celdas, **las nueve con `libopus`**. Con el mismo fallo y
la misma tasa contra otros dos códecs:

| Destino a 32 kb/s | A7 atrapa |
|---|---:|
| `libopus` | **1 de 6** |
| `libmp3lame` | **6 de 6** |
| `aac` | **6 de 6** |
| `libopus` a 16k / 8k / 6k | 0 de 6 |
| `mp3 -q:a 9`, `flac`, `wav` | 6 de 6 |

**No es la tasa: es que Opus colapsa el estéreo a mono y los demás no.** Es la
trampa 53 —la cobertura de una regla de fidelidad depende del DESTINO— y decide
dónde va el remedio: no en un umbral nuevo, sino en **decirlo**. Donde A7
provablemente no ve, `cobertura['A7']` vale `False`, que es la disciplina que el
verificador ya aplica cuando el pedido mueve la energía. Un `ok` de A7 sobre un
Opus estéreo de 8 kb/s era **un aprobado que nadie había examinado**.

**Tres detalles que hubo que sondear, no deducir:**

1. **La tasa hay que deducirla.** En un `.opus` la sonda devuelve
   `bitrate_bps = None` en la pista (MEDIDO, `dbg_opus.py`), así que una
   condición basada en ese campo **no dispararía nunca en el único formato al
   que apunta**. Se deriva de `8·bytes/duración`, y **solo en ficheros sin
   vídeo**: en un contenedor con imagen el tamaño no es del audio.
2. **La deducción lleva el sobrecoste del contenedor**, del 11 al 14 %: 24k →
   27 830, 32k → 36 450, 40k → 44 560, **48k → 53 601**. El escalón de 48 000
   cae por tanto en ~43 kb/s de tasa pedida, que está dentro del hueco medido
   (ciego a 32k, vidente a 48k).
3. **Hacen falta ≥ 2 canales.** Con uno solo no hay de dónde copiar: un mono
   silenciado sale silencioso y A7 lo ve. **Es lo que deja intactas las dos
   salidas Opus del patrón oro, que son mono.**

`a7_ciego_opus.py`, 54 celdas con el verificador de `HEAD` y con el del árbol:

| | Resultado |
|---|---|
| Declaran punto ciego | **6**: `libopus` estéreo a 6k, 8k, 16k, 24k, 32k, 40k |
| `libopus` estéreo a 48k, 64k, 96k | no ciego (correcto: A7 atrapa 6/6) |
| `libmp3lame` y `aac`, las 18 celdas | no ciego (correcto: 6/6) |
| `libopus` **mono**, las 9 | no ciego |
| Cambian de veredicto | 6, todas `ok` → **`ok_parcial`** |
| **Fallos nuevos** | **0** |

**El escalón de silencio se sigue evaluando** aunque se declare el punto ciego:
un fallo encontrado es un fallo, y a 32 kb/s todavía atrapa 1 de 6. Lo que
cambia es que su **silencio** deja de contar como aprobado.

### 2.7 Qué NO cubre esto — sin adornos

1. **La señal sigue sin aplicarse.** Los 15 fallos que atraparía (de 23 que hoy
   se escapan) **siguen escapándose**. Lo único que cambia es que ahora, en 6 de
   las 54 configuraciones medidas, FileX **dice** que no puede verlos.
2. **El punto ciego declarado es de UN códec.** Se declaró `libopus` porque es
   el único donde está medido. Vorbis, HE-AAC v2 (que usa *parametric stereo* y
   podría hacer exactamente lo mismo) y cualquier códec futuro **no están
   sondeados**. **PENDIENTE**, y el arnés que lo mide ya existe.
3. **El umbral de 48 kb/s es del par (códec, contenido).** Con voz mono-céntrica
   Opus colapsa antes; con música ancha, después. Está medido sobre **dos
   fuentes**.
4. **En un contenedor con vídeo no se declara nada**, porque la tasa no se puede
   deducir y la sonda no la publica. Un MKV con audio Opus estéreo a 8 kb/s
   sigue devolviendo `cobertura = True`. **PENDIENTE.**
5. **`ok_parcial` no es gratis para quien lo lee.** Seis configuraciones
   perfectamente legítimas bajan de `ok` a `ok_parcial`. Es lo correcto —no
   estaban examinadas— pero es un cambio de comportamiento y se declara.
6. **Todo el corpus de calibración es fabricado.** El corpus del proyecto **no
   tiene un solo fichero estéreo de canales desiguales**: `habla_jfk.flac` da
   `corr(L,R) = 0,9997` y el audio de `tipico.mp4` es **mono**. Es el aviso 1 de
   N16 y sigue igual.

---

## 3. N20 — el destino que es un directorio: se negaba bien y mentía al decir por qué

### 3.1 El mecanismo, sondeado sin una sola carrera — MEDIDO

`sonda_destino_dir.py`, determinista:

| Caso | Excepción | `errno` | `WinError` |
|---|---|---:|---:|
| A1 `os.replace(fichero, DIRECTORIO existente)` | `PermissionError` | **13** | **5** |
| A3 `os.replace(fichero, fichero ABIERTO por un tercero)` | `PermissionError` | **13** | **5** |
| A2 `os.replace(DIR, DIR)` — la detección previa | **ninguna** | — | — |

**El `errno` no separa los dos casos**, así que los dos acababan en
`DestinoOcupado` y el cliente leía *«otro proceso tiene abierta esa ruta de
salida»* — **falso**: no hay ningún otro proceso. Es la trampa 44 sobre el
camino que N12 acababa de arreglar: un veredicto honesto (`fallo`) al lado de
una frase que promete algo que no ha ocurrido.

Y A2 explica por qué no bastaba la defensa que ya había: **`os.replace(DIR, DIR)`
funciona**, así que `destino_ocupado_por_un_tercero` devuelve `False` — y tiene
razón, nadie tiene ese directorio abierto.

### 3.2 El arreglo, y la arista de R1/R4

`filex/nucleo.py`: excepción nueva `DestinoNoEsFichero`, y `_negativa()` que
elige cuál lanzar preguntando `os.path.isdir(destino)`.

**Se pregunta DESPUÉS del fallo, y eso no es un «comprobar y luego actuar» de
los que prohíbe la trampa 63.** La acción ya está decidida y es la misma en los
dos casos: negarse. Lo único que depende del `isdir` es **qué frase se escribe**,
así que la peor consecuencia de una carrera aquí es un mensaje equivocado, nunca
un atropello.

**¿Abre un canal de información que R1/R4 cierran? No — y la comprobación es del
proyecto, no mía.** La opacidad de R1/R4 protege rutas que el cliente **no**
tiene permitidas: no ser un oráculo del sistema de ficheros. Aquí la ruta **ya
pasó el confinamiento** —está dentro de una raíz de la lista blanca— y **la pidió
el propio cliente**. Es literalmente el argumento que `nucleo.py` ya tiene
escrito tres líneas más arriba para *«otra conversión está escribiendo ya esa
ruta de salida»*: *«el cliente **pidió** esta ruta, así que nombrarla no le dice
nada que no supiera»*. Y por el lado del reloj (trampa 28, el ×20,6 entre R1 y
R4): **los dos caminos de negativa pagan el mismo `isdir`**, así que no aparece
una diferencia temporal nueva entre ellos.

Se añade además la comprobación **temprana**, junto a la detección de ocupante
que ya existía: si el destino ya es un directorio, la conversión va a acabar en
`fallo` igual y no hay por qué gastar los ~250 ms del motor. Se ve en que
`conv.saltos` queda **vacío**.

### 3.3 Qué NO cubre

* **Un directorio que aparece MIENTRAS se convierte** lo atrapa la segunda
  comprobación, la del `except`, no la temprana. Las dos hacen falta.
* **`FILEX_MOVE_SEGURO=0`** sigue metiendo la salida dentro del directorio: es
  el camino del hito 7, conservado a propósito para poder medir el antes.
* **POSIX**: `os.replace(fichero, dir)` da `IsADirectoryError` (errno 21) en vez
  de `EACCES`, pero el remedio no cambia porque no mira el `errno` sino el
  `isdir`. **PENDIENTE de medir allí.**

---

## 4. N19 — `recoger()` pisaba, y también al que tenía el fichero abierto

### 4.1 El fallo, MEDIDO — y es peor que el pendiente que lo señaló

`ventana-antes-del-move.md` §6.6 lo dejó así: *«hoy es una función pública que
pisa en silencio»*. Sondeado (`sonda_destino_dir.py`, casos C1 y C2):

| Caso | Antes | Después |
|---|---|---|
| C1 destino EXISTENTE, nadie lo tiene abierto | 88 B → **20 B**, sin excepción | 88 B → 20 B, sin excepción |
| C2 destino **ABIERTO por otro proceso** | 88 B → **20 B**, sin excepción | **88 B → 88 B**, `DestinoOcupado` |

**C1 no cambia y es lo correcto**: sobrescribir un destino que existe y que nadie
tiene abierto es exactamente lo que se le pide a un `move`, y es el punto 1 de
«lo que no cubre» de N12. **C2 es el agujero**, y es el mismo de la trampa 33 —
`shutil.move` sobre un destino que existe no hace `rename`, cae a `copy2` y
sobrescribe en silencio— un nivel por debajo del que N12 cerró.

### 4.2 El arreglo: le vale la misma solución

`recoger()` delega en `nucleo.mover_a_destino`, que hace **la detección y la
acción en la misma llamada del sistema** (trampa 63). Hereda gratis las tres
cosas: el `os.replace` que no deja ventana, el camino de volúmenes distintos con
su temporal en el destino, y ahora **el motivo correcto ante un directorio**.

**El `import` es local a la función**, y no por gusto: `filex.nucleo` importa
`filex.trabajo`, así que a nivel de módulo sería un ciclo. En tiempo de llamada
no lo hay —`trabajo` está entero en `sys.modules` antes de que nadie pueda
llamar aquí— y cuesta una búsqueda en `sys.modules`.

### 4.3 Qué NO cubre

* **Lo mismo que no cubre `mover_a_destino`**: el tercero que escribe y cierra
  dentro de la ventana, POSIX (donde `os.replace` sobrescribe aunque el fichero
  esté abierto), y el lector que basta para negarse.
* **`recoger()` sigue sin llamarla nadie en producción.** Se arregla porque es
  **pública** y la usan arneses de `bench/` (`salidas-hito5/_sonda.py`,
  `salidas-sondeo-doc/_sonda_p5.py`), no porque el núcleo dependa de ella.

---

## 5. La restricción que manda: cero falsos positivos sobre las 53

`regresion_53_n.py`, con el verificador de `HEAD` (`--antes`) y el del árbol.
`bench/salidas-referencia/referencia.json` **se lee y no se toca**.

| | Antes (`HEAD`) | **Después** |
|---|---|---|
| **Falsos positivos** | **0** | **0** |
| Falsos negativos | 0 | 0 |
| Contrato | ok 39 · aviso 3 · ok_parcial 10 · fallo 1 | **idéntico** |
| Fidelidad | ok 37 · aviso 8 · ok_parcial 8 · fallo 0 | **idéntico** |

**`--diff`: 0 de 53 salidas cambian de veredicto o de reglas.** El motivo está
medido y no es suerte: **las dos únicas salidas Opus del patrón oro son MONO**
(`tipico_flac-to.opus`, `trivial_wav-to.opus`, las dos a 96 kb/s), y la
declaración exige ≥ 2 canales **y** tasa por debajo de 48 kb/s.

*(No publico la diferencia entre los dos totales —47 564 ms y 50 250 ms—: son
2 686 ms con otro agente en la máquina, y la trampa 36 dice exactamente que eso
no es una medida. Lo que sí está medido en aislamiento es la pieza: el punto
ciego cuesta **cero procesos** —un `getsize`, una división y una comparación de
cadena— y solo se evalúa dentro de A7, que ya corre.)*

---

## 6. La suite

**311 passed, 6 skipped** en la tanda completa, más **1 fallo que pasa al
ejecutarlo solo**: `test_hito7.py::ApiDefensas::test_el_asa_llega_al_empezar`
mide que el asa HTTP llegue en < 250 ms y devolvió 278,2 con H2 trabajando en
paralelo. Es un aserto de reloj y no toca nada de este reparto; aislado da
`1 passed` en 4,08 s. **Efectivamente 312 pruebas verdes sobre una base de 298.**

**+14 pruebas nuevas**, todas en ficheros de este reparto:

| Fichero · clase | Prueba | Qué documenta |
|---|---|---|
| `test_cerrojo.py::DestinoQueEsDirectorio` | `test_el_motivo_no_habla_de_otro_proceso` | **ROJA sin el arreglo.** Decía «otro proceso tiene abierta esa ruta» sin que hubiera ninguno. |
| | `test_se_rechaza_antes_de_convertir` | **ROJA sin el arreglo.** `conv.saltos == []`: los ~250 ms del motor no se gastan. |
| | `test_no_mete_la_salida_dentro_del_directorio` | El comportamiento del hito 7 que N12 ya había cambiado. |
| | `test_la_deteccion_de_ocupante_no_ve_el_directorio` | Por qué hace falta una comprobación aparte: `os.replace(DIR,DIR)` funciona. |
| | `test_mover_a_destino_distingue_las_dos_negativas` | **ROJA sin el arreglo.** Y que `DestinoNoEsFichero` **no** herede de `DestinoOcupado`: un `except` del viejo no puede tragarse el nuevo. |
| `test_cerrojo.py::RecogerNoPisa` | `test_no_pisa_el_fichero_de_un_tercero` | **ROJA sin el arreglo**, con un tercero en otro proceso de verdad. |
| | `test_a_un_directorio_no_mete_dentro` | **ROJA sin el arreglo.** |
| | `test_el_caso_normal_sigue_funcionando` | Un arreglo que rompe el 99 % no es un arreglo. |
| `test_a7_ciego.py::PuntoCiegoDeA7` | `test_opus_estereo_a_tasa_baja_no_se_declara_aprobada` | **ROJA sin el arreglo.** |
| | `test_la_tasa_se_deduce_cuando_la_sonda_no_la_da` | **ROJA sin el arreglo.** Y comprueba que `bitrate_bps` es `None` en la pista. |
| | `test_opus_estereo_a_96k_si_se_declara_aprobada` | El otro lado: no declararse ciego donde sí se ve. |
| | `test_mp3_y_aac_a_la_misma_tasa_baja_NO_son_ciegos` | Lo que refuta el nombre viejo. |
| | `test_un_opus_MONO_no_es_punto_ciego` | Lo que deja intactas las 53. |
| | `test_el_fallo_de_verdad_sigue_saliendo_fallo` | Declarar un punto ciego no puede apagar la regla. |

**Cinco de las ocho de `test_cerrojo.py` y dos de las seis de `test_a7_ciego.py`
se comprobaron ROJAS** con `git stash` de los ficheros de `filex/` y verdes al
restaurarlos.

---

## 7. El impacto sobre el sondeo: la huella NO caduca — MEDIDO, y es la tercera vez

El aviso 3 del encargo decía: *«Tu trabajo caduca el componente `contrato` de la
huella — `verificador.py` lo es. Está aceptado.»*

**No lo caduca** (`huella_impacto.py`, con control positivo de compilación de las
dos fuentes, trampa 60):

| | HEAD | Árbol |
|---|---|---|
| `huella.de_alcance(verificador.py)` | `38626025e73df9e1` | **`38626025e73df9e1`** |
| Nombres en el cierre de `verificar()` | 121 | **121** |
| De lo que he tocado, cuántos están en el cierre | | **0 de 5** |

`ENTRADAS_CONTRATO = ("verificar",)`: la huella hashea el cierre de llamadas de
**`verificar()`**, y A7 vive en **`verificar_fidelidad()`**, que es otra raíz.
`pruebas/test_sondeo.py` sigue verde y **no hay ninguna arista que resondear por
este trabajo**.

**No es un hallazgo nuevo: es la confirmación de uno.**
`contrato-familia-resvg.md` §6 ya lo midió y lo publicó (con la versión anterior
del algoritmo: `6af6b556299b`). Lo que aporta esta repetición es que **ha vuelto
a pasar con otro cambio, otro agente y otro algoritmo de huella**, y que el
encargo volvió a darlo por hecho. La conclusión de §6 sigue en pie y sin
arreglar: **la mitad de FIDELIDAD del verificador no está en la huella**, así que
mover A7 —que decide `fallo` sobre aristas reales— no caduca nada. `huella.py`
no es de este reparto.

---

## 8. Ficheros tocados

| Fichero | Qué cambia |
|---|---|
| `filex/verificador.py` | `A7_OPUS_CIEGO_BPS`, `A7_CIEGO_MIN_CANALES`, `_a7_tasa_efectiva`, `_a7_punto_ciego`; `_a7_energia_por_canal` recibe la sonda y declara el punto ciego. **La API pública solo AÑADE nombres**: no se quita ni se cambia de firma nada, así que los 19 arneses que importan por `bench/scripts/verificador.py` siguen igual. *(La única firma que cambia es la de `_a7_energia_por_canal`, privada y sin un solo uso fuera del módulo — comprobado con `grep` sobre todo el repositorio.)* |
| `filex/nucleo.py` | `DestinoNoEsFichero`, `_negativa()`, `MOTIVO_OCUPADO`, `MOTIVO_NO_ES_FICHERO`, la comprobación temprana en `convertir` y el `except` nuevo en `_un_salto`. |
| `filex/trabajo.py` | `recoger()` delega en `mover_a_destino`. |
| `pruebas/test_cerrojo.py` | +2 clases, +8 pruebas. |
| `pruebas/test_a7_ciego.py` | Nuevo, +6 pruebas. |
| `bench/salidas-fidelidad-n/` | 13 arneses y sus JSON, todo texto. `MANIFIESTO.md` con las órdenes. |

**No se ha tocado** `filex/motores.py`, `filex/gpu.py`, `filex/cerrojo.py`,
`huella.py`, `sondeo.py`, `sondeo/*.json`, `pruebas/test_sondeo.py`,
`invocacion.py`, `servicio.py`, `mcp.py`, `api.py`, `watcher.py`,
`motor_contenedor.py`, `bench/lib/harness.sh`, `bench/salidas-referencia/`,
ni ningún informe ajeno.

---

## 9. Pendientes que dejo abiertos

1. **Los 15 fallos que la señal atraparía siguen sin atraparse.** La celda buena
   está medida (`corr < 0,05` **y** canal a ≥ −12 dB del más fuerte: 15/23, 0 FP
   de 147) y el precio también (numpy, o una FFT en Python puro). **Es una
   decisión de arquitectura: `filex` sin dependencias, o A7 con esta cobertura.**
2. **El punto ciego, en los demás códecs.** HE-AAC v2 usa *parametric stereo* y
   podría hacer exactamente lo que hace Opus. `a7_corr_ancho.py` lo mide
   añadiendo una fila a `DESTINOS`.
3. **El punto ciego dentro de un contenedor con vídeo**, donde la tasa no se
   puede deducir. Hoy no se declara nada.
4. **Un estéreo REAL de canales desiguales en el corpus.** Las ocho fuentes de
   aquí y las cinco de N16 son fabricadas, y el corpus no tiene ninguna. Es el
   aviso 1 de N16, sin cerrar, y es lo que hace que todos estos umbrales sean
   provisionales.
5. **La mitad de FIDELIDAD del verificador fuera de la huella** (§7). Reincidente.
6. **N20 en POSIX**: allí el `errno` sí separa (`EISDIR`), pero no está medido.

---

## 10. Propuestas para `CLAUDE.md` — **NO APLICADAS** (rango 78–81, cerrado)

> **78. Un umbral calibrado con un solo MOTOR describe a ese motor, y la trampa
> de al lado ya lo había dicho de la ENTRADA — MEDIDO**
> (`bench/fidelidad-y-nucleo.md` §2.2, §2.6). `contrato-familia-resvg.md` §2.5
> tituló *«el punto ciego de A7 a bitrate bajo»* con nueve celdas, **las nueve
> de `libopus`**. Sobre el mismo fallo y la misma tasa de 32 kb/s,
> `libmp3lame` y `aac` atrapan **6 de 6** y `libopus` **1 de 6**: no era la
> tasa, era que **Opus colapsa el estéreo a mono y los demás no**. El nombre
> importa porque decide dónde va el remedio — con el nombre viejo se habría
> movido un umbral global; con el bueno, se declara `cobertura = False` en un
> códec. **La trampa 50 dice «varía la entrada»; esta dice «varía el MOTOR del
> destino», y las dos hacen falta:** N16 varió la entrada a conciencia y siguió
> midiendo un solo códec.
>
> **Y el corolario del corolario:** con la entrada variada de verdad —ruido
> descorrelacionado, fase invertida y un canal 40 dB más flojo— la señal que N16
> midió con 0 falsos de 45 da **11 falsos de 152, 6 de ellos irreductibles**, y
> las clases **se solapan**.
> No se refuta su medida, que se reproduce al centésimo: se refuta su alcance.

> **79. Un ratio contra una cifra ajena hay que rehacerlo con LA MISMA ORDEN, no
> solo en la misma tanda — MEDIDO** (ídem §2.5). La trampa 59 ya obliga a medir
> la versión histórica en tu propia tanda. **Falta la otra mitad: comprobar que
> lo que mediste es lo que el código ejecuta.** N16 publicó *«183,1 ms frente a
> 364,0: la mitad»*, y esos 364,0 son
> `astats=metadata=1:reset=0` —todas las medidas, sin `-map` y sin `-vn`—
> mientras A7 corre `astats=measure_overall=none:measure_perchannel=…`. Medidos
> los dos en la misma tanda: **166,24 ms lo que A7 gasta y 465,89 ms el control,
> ×2,80**, así que la propuesta no costaba la mitad sino **×1,395**. Y el aviso
> estaba escrito en el informe del que N16 partía: `contrato-familia-resvg.md`
> §2.2 publica *«A7 completa (dos sondas) ≈ 110–147 ms»*. **Cuando una cifra de
> control salga de un arnés, pega al lado la orden exacta; y cuando la heredes,
> compárala con la que el código ejecuta antes de dividir.**

> **80. Una restricción del PROYECTO puede invalidar una propuesta ya medida, y
> hay que mirarla antes de medir nada — MEDIDO** (ídem §2.4). La señal de N16
> está bien medida y **no se puede escribir**: su alineamiento necesita una FFT,
> y `filex` **no tiene dependencias por decisión escrita en `pyproject.toml`**
> (*«añadir una dependencia aquí obliga a justificar por qué no se puede hacer
> en proceso»*). Sin alinear, la misma señal pasa de **0 a 19 falsos positivos**
> —el desfase vale hasta **−1,9785** de correlación, y es **0 en las 191 celdas
> de mp3, aac, flac y wav pero no en las de Opus**, que es justo el caso que
> venía a cubrir—. Las dos salidas que quedaban también estaban cerradas: la
> identidad de los tres RMS por grafo de ffmpeg no alinea, y `audioop` —que sí
> trae `findfit` en C— **está eliminado desde Python 3.13** con
> `requires-python = ">=3.11"`. **Antes de medir una propuesta, escribe la línea
> de `pyproject.toml`/`CLAUDE.md` que la permitiría; si no existe, lo que estás
> midiendo es una decisión de arquitectura, y hay que decirlo así.**

> **81. Un grafo de `ffmpeg` falla ENTERO por lo que parece decoración, y su
> fallo se disfraza de «no hay señal» — MEDIDO** (ídem §2.4, `proto_diag.py`,
> `proto_graf.py`). Dos celdas, las dos caras de lo mismo:
>
> * **`amix=inputs=2:weights=1 -1:normalize=0` NO resta.** Sobre dos FLAC
>   idénticos devuelve `RMS(dif) = 2·RMS(x)`, es decir la SUMA, y una
>   correlación deducida de ahí da **−0,88 para dos ficheros iguales**. La
>   negación explícita (`volume=-1` antes del `amix`) sí resta: `-inf` y
>   r = 1,0000 exacto.
> * **`aformat=…:channel_layouts=` no es decoración.** Sin él, `amerge` de tres
>   ramas devuelve `Error reinitializing filters!` y `rc=-5` **en mono, en
>   estéreo y en vídeo con audio**. Un arnés de 264 celdas corrió **16 minutos**
>   y devolvió `None` en las 264: un `None` uniforme se parece muchísimo a «la
>   señal no existe» (trampa 25 en versión de arnés), y solo se destapó porque
>   un prototipo anterior, que sí lo llevaba, funcionaba.
>
> **Todo grafo de `filter_complex` necesita un control positivo de identidad
> antes de creerse una sola celda**: el mismo fichero contra sí mismo tiene que
> dar el valor perfecto —r = 1, diferencia `-inf`—, y si no lo da, lo que has
> medido es el grafo. *(Y una tercera del mismo día, de arnés: una fuente
> fabricada con `atrim=20:28` sobre un audio más corto sale **vacía**, el `.opus`
> pesa 136 B y las 27 celdas estéreo dicen «no cambia nada». Trampa 38:
> registra si la condición que dices reproducir se dio — un `assert` de tamaño
> sobre la fuente cuesta una línea.)*

---

## 11. Reproducir

```bash
git lfs checkout                                    # trampa 34
python bench/salidas-firmas-cierre/_regenera53.py   # las 53, fuera del repo
export FILEX_REF53="<...>/scratchpad/REF53"

python bench/salidas-fidelidad-n/regresion_53_n.py --antes
python bench/salidas-fidelidad-n/regresion_53_n.py
python bench/salidas-fidelidad-n/regresion_53_n.py --diff

python bench/salidas-fidelidad-n/a7_repro_n.py        # reproducir a N16
python bench/salidas-fidelidad-n/a7_corr_ancho.py     # sacarlo de su corpus
python bench/salidas-fidelidad-n/a7_rejilla.py        # la rejilla de decisión
python bench/salidas-fidelidad-n/a7_grafo.py          # sin numpy y sin alinear
python bench/salidas-fidelidad-n/a7_coste_grafo.py    # el coste, con su control
python bench/salidas-fidelidad-n/a7_ciego_opus.py     # lo aplicado
python bench/salidas-fidelidad-n/sonda_destino_dir.py # N19 y N20
python bench/salidas-fidelidad-n/huella_impacto.py    # ¿caduca? no

python -m pytest pruebas -q
```

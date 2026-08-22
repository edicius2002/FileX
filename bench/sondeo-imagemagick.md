# Sondeo de las 62 aristas `sin_sondear` de ImageMagick

**Agente S1 · 22/08/2026 · build `imagemagick 7.1.2-21` (Q16-HDRI)**
Dato entregado: `filex/sondeo/imagemagick.json` · Salidas: `bench/salidas-sondeo-im/`

---

## 0. Resumen

Se ejecutaron las **62 aristas** que `filex/motores.py` declaraba `sin_sondear`
para ImageMagick, **dos semillas cada una**, con `FileX.convertir()` — es decir
con el contrato de cinco puntos, el directorio desechable y el censo del punto 5
dentro de la conversión, no después.

| | |
|---|---|
| Aristas sondeadas | **62** (124 celdas: 62 × 2 semillas) |
| **`real`** | **62** |
| **`nominal`** | **0** |
| Escrituras fuera de lo declarado (punto 5) | **0 de 124** |
| Salidas con el formato equivocado | **0 de 117** |
| ImageMagick tras aplicar el sondeo | **67 real, 0 `sin_sondear`** (eran 5 real / 62 sin sondear) |
| Grafo completo | 119 real · 93 `sin_sondear` · 3 nominal |
| Pruebas | **82 pasadas + 6 saltadas**, igual que antes |

**Cero `nominal` es el resultado menos interesante posible, y hay que decirlo
así: en el terreno raster→raster de un solo motor los catálogos NO mienten.**
El 41,0 % de aristas fantasma de `bench/aristas-nominales.md` no aparece aquí, y
tiene sentido: aquellas eran aristas *entre motores y familias distintas*; estas
son ocho formatos de imagen dentro del mismo códec-hub. **La lección es del
método, no del número: si el sondeo hubiera parado en `rc==0` habría dado 62 de
62 igual, y se habría perdido todo lo de §1 a §4.** Lo que sigue es lo que
aparece cuando se mira lo que el `rc=0` tapa.

---

## 1. El hallazgo principal: `*→ico` devuelve `rc=0` y declara una anchura que no tiene

**MEDIDO.** El `ICONDIRENTRY` de un fichero ICO guarda ancho y alto en **un byte
cada uno** (0 significa 256). ImageMagick 7.1.2-21 escribe ahí `ancho & 0xFF` sin
comprobar nada, y **el error solo aparece por encima de 512 px**.

Tres regímenes, con el umbral acotado a un píxel:

| Lado | `rc` | Qué escribe | Qué ve un lector externo |
|---|---|---|---|
| 1–256 px | 0 | correcto | correcto |
| **257–512 px** | **0** | ICO válido en firma, **`ICONDIRENTRY` con `lado & 0xFF`** | **la geometría equivocada** |
| ≥513 px | 1 | fichero de **0 bytes** | — |

Bytes 6–7 del fichero (ancho, alto del directorio del icono):

```
t255.ico  ... 0100 ff8f ...  -> 255 x 143      correcto
t256.ico  ... 0100 0090 ...  -> 0(=256) x 144  correcto
t257.ico  ... 0100 0191 ...  ->   1 x 145      la imagen es 257x145
t320.ico  ... 0100 40b4 ...  ->  64 x 180      la imagen es 320x180
s512.ico  ... 0100 0000 ...  -> 0(=256) x 256  la imagen es 512x512
```

**Confirmado por un lector independiente** (Pillow 10.4.0, `.venv-ai`, solo
lectura). Pillow lee el directorio, no el BMP incrustado, y avisa:

```
t257.ico  PIL ve (257,145)  sizes=[(1, 145)]     UserWarning: Image was not the expected size
t320.ico  PIL ve (320,180)  sizes=[(64, 180)]    UserWarning: Image was not the expected size
s512.ico  PIL ve (512,512)  sizes=[(256, 256)]   UserWarning: Image was not the expected size
```

**`magick identify` lo relee bien** —dice 320×180— porque lee la cabecera del BMP
incrustado, que sí guarda la anchura en 32 bits. **El motor que lo escribe mal es
el único que lo lee bien.** Es exactamente el patrón `magick x.png y.group4`:
`rc=0`, firma correcta, contenido que no es el que se declara. Y aquí es peor,
porque no hay ni un aviso en `stderr`.

**El contrato de FileX no lo atrapa**, y por un motivo concreto que se mide en §4:
la sonda del verificador reconoce la **firma** `ico` pero no sabe leer su
**cabecera**, así que los puntos 3 y 4 quedan sin cubrir y el veredicto se queda
en `ok_parcial`. Ni el punto 4 (pedido frente a obtenido) ni la regla G6 pueden
decir nada.

El umbral es por dimensión, no por área: `1920×100` y `100×1920` fallan los dos.
El límite superior está acotado entre **512 (escribe) y 513 (`rc=1`)**, medido
punto a punto en 513, 520, 528, 544, 560, 568 y 576.

**Y el `rc=1` deja basura:** el censo del directorio desechable devuelve
`{'salida.ico': 0}`. Sin R18, un fichero de 0 bytes con el nombre pedido se
quedaría en el destino. **R18 lo contiene; sin R18 esto es un fallo silencioso
de siete aristas.**

### Consecuencia práctica

Las siete aristas `*→ico` (`png`, `jpg`, `webp`, `avif`, `gif`, `bmp`, `tif`)
fallan con `rc=1` sobre la semilla A (1920×1080) y funcionan sobre la B (200×200).
Se declaran **`real` con la precondición escrita en el `motivo`**, porque la
capacidad existe: lo que hay es un límite de FORMATO, no un motor que no sabe.
Lo que FileX debería hacer con eso está en §6.

---

## 2. `bmp→pdf` entrega una página **2,54× más pequeña**, con `veredicto: ok`

**MEDIDO.** Los mismos 1920×1080 píxeles, la misma orden, el mismo `-density 150`:

| Origen | `/MediaBox` del PDF | ppp implícitos |
|---|---|---|
| `avif`, `gif`, `jpg`, `tif`, `webp` | `0 0 921.6 518.4` | 150 |
| **`bmp`** | **`0 0 362.835 204.094`** | **381** |
| `ico` (256×144) | `0 0 122.88 69.12` | 150 |

`921,6 / 362,835 = **2,540**`. Y con la semilla B (200×200): 96×96 pt en todos,
**37,7953** en `bmp` — `96 / 37,7953 = **2,540**` otra vez. Es el factor
centímetro→pulgada, exacto en las dos semillas.

**La causa: `-density N` no fija ppp, fija un NÚMERO en las unidades que declara
la imagen.** El BMP que escribe ImageMagick declara `Units: PixelsPerCentimeter`,
así que `-density 150` son 150 px/cm = 381 ppp, y la página sale de 12,8×7,2 cm
en vez de 32,5×18,3 cm.

**Autocorrección:** mi primera hipótesis fue el ORDEN de los argumentos —
`motores.py` pone `-density` **después** del fichero de entrada, y en ImageMagick
eso normalmente cambia el significado. **Refutada, con el A/B de cuatro celdas:**

```
magick A.bmp -density 150 out.pdf                       -> 362.835 x 204.094
magick -density 150 A.bmp out.pdf                       -> 362.835 x 204.094   (el orden NO importa)
magick A.bmp -units PixelsPerInch -density 150 out.pdf  -> 921.6 x 518.4
magick A.bmp -density 150 -units PixelsPerInch out.pdf  -> 921.6 x 518.4
```

La corrección es **`-units PixelsPerInch`**, en cualquiera de las dos posiciones.

Y hay un agravante de declaración: la arista `imagen→pdf` se registra en
`filex/motores.py` con `parametrizacion="densidad_ajustada_a_pagina"` y el
docstring del módulo dice *«la densidad de `imagen→pdf` se AJUSTA a la página, no
se fija — con `-density 150` sale un A3 y medio»*. **El código pone
`-density 150` fijo** (`motores.py:189`). La parametrización declarada no es la
que se ejecuta, y **la parametrización es una de las cinco dimensiones de la
arista**: una arista cuyo nombre de parametrización miente es una arista que
miente.

**Los píxeles están bien.** Rasterizando cada PDF a 400 ppp y remuestreando a la
geometría del origen, RMSE **0,0020–0,0035** en las siete. Lo que está mal es la
caja de la página — y **el contrato lo declara `ok` (6/6)** porque el punto 3 no
mira el `/MediaBox`.

---

## 3. El barrido

### 3.1 Método

- **`FileX.convertir()`, nunca `magick` a pelo.** Contrato, desechable y censo
  entran solos, que es el diseño.
- **Grafo de UNA arista por medición.** Sin esto el planificador no ejecuta la
  arista que se quiere sondear: `tif→pdf` sin sondear cuesta 3,2 y
  `tif→png→pdf` (dos aristas reales) cuesta 2,2, así que gana el camino de dos
  saltos y la arista sondeada nunca corre. Es una trampa del propio diseño del
  coste y hay que decirla.
- **Dos semillas, por la regla del tercer sesgo** (`CLAUDE.md` §3): A =
  `tipico.png` 1920×1080 con **alfa trivial** (`min(α)=1`, trampa 1); B =
  `alpha.png` 200×200 con **alfa real** (`min(α)=0`). Sirvió, y con número:
  **8 de 62 aristas cambian de `fallo` a no-`fallo` según la semilla, y 14 de 62
  cambian de veredicto.** Con una sola semilla, siete aristas serían `nominal`
  (§1) o una sería `nominal` (§4.2) según cuál se hubiera elegido.
- `ms` = **mediana de 3** en la semilla A. n=1 en la B, que es testigo de semilla,
  no de tiempo.
- Calentamiento de 3 arranques de `magick` antes de cronometrar (trampa 7).
- Timeout explícito de **120 s** en cada invocación. Ningún agotamiento.

### 3.2 Testigos de ruido — tanda `SUCIA`

| Testigo | Antes | Después | Lectura |
|---|---|---|---|
| Deriva (bucle monohilo) | 26,6 ms | 26,5 ms | ratio **0,997**, sin deriva |
| Nivel (lanzar `magick -version`, tope 20 s) | 20,9 ms | 17,2 ms | sin tope alcanzado |

Los dos testigos limpios, y aun así **la tanda va etiquetada `SUCIA`**: sesión
remota activa y **dos agentes más trabajando** (S2 en ffmpeg, S3 en contenedor).
**Los `ms` de este informe sirven para desempatar dentro de la tanda, no para
comparar con otro informe.**

Y las siete `*→ico` no tienen tiempo comparable con las demás: su semilla es
**D, de 256×144**, porque a 1920×1080 la arista no existe. Está marcado
`"semilla": "D-256px"` en el JSON.

### 3.3 Coste por destino (mediana de las 7 orígenes, semilla A, 1920×1080)

| Destino | ms | | Destino | ms |
|---|---:|---|---|---:|
| `bmp` | 87,6 | | `webp` | 271,3 |
| `tif` | 123,7 | | `png` | 336,4 |
| `pdf` | 220,3 | | `avif` | 640,0 |
| `jpg` | 229,3 | | **`gif`** | **815,3** |

Mediana global 233,4 ms. Extremos: `ico→tif` **30,4 ms**, `avif→gif`
**1 922,7 ms** — un factor **63×** entre la arista más barata y la más cara del
mismo motor. Es justo lo que el campo `ms` del sondeo existe para desempatar.

### 3.4 Tabla completa

`RMSE A` es contra el origen **sin corregir por pérdida de formato**: sirve para
detectar destrucción, no para juzgar calidad (ver §5).

| arista | estado | ms (A) | veredicto A | veredicto B | RMSE A | salvedad |
|---|---|---|---|---|---|---|
| `avif→bmp` | real | 179.7 | ok_parcial | ok_parcial | 0.0010 |  |
| `avif→gif` | real | 1922.7 | ok_parcial | ok_parcial | 0.0051 |  |
| `avif→ico` | real | 38.3 | **fallo** | ok_parcial | — | ≤256 px |
| `avif→jpg` | real | 270.2 | ok_parcial | ok_parcial | 0.0029 |  |
| `avif→pdf` | real | 340.5 | ok_parcial | ok_parcial | 0.2592 |  |
| `avif→png` | real | 485.8 | ok_parcial | ok_parcial | 0.0000 |  |
| `avif→tif` | real | 270.9 | ok_parcial | ok_parcial | 0.0001 |  |
| `avif→webp` | real | 310.0 | ok_parcial | ok_parcial | 0.0037 |  |
| `bmp→avif` | real | 700.8 | ok | ok | 0.0046 |  |
| `bmp→gif` | real | 815.3 | ok | ok | 0.0085 |  |
| `bmp→ico` | real | 26.1 | **fallo** | ok_parcial | — | ≤256 px |
| `bmp→jpg` | real | 229.3 | ok | ok | 0.0033 |  |
| `bmp→pdf` | real | 355.2 | ok | ok | 0.4060 | **página 2,54× menor (§2)** |
| `bmp→png` | real | 389.4 | ok | ok | 0.0000 |  |
| `bmp→tif` | real | 123.7 | ok | ok | 0.0000 |  |
| `bmp→webp` | real | 278.8 | ok | ok | 0.0033 |  |
| `gif→avif` | real | 1075.3 | ok_parcial | ok_parcial | 0.0099 |  |
| `gif→bmp` | real | 77.9 | ok_parcial | ok_parcial | 0.0000 |  |
| `gif→ico` | real | 27.3 | **fallo** | ok_parcial | — | ≤256 px |
| `gif→jpg` | real | 233.4 | ok_parcial | ok_parcial | 0.0095 |  |
| `gif→pdf` | real | 275.5 | ok_parcial | ok_parcial | 0.2945 |  |
| `gif→png` | real | 538.6 | ok_parcial | **fallo** | 0.0000 | **falso positivo de I4 (§4.2)** |
| `gif→tif` | real | 175.0 | ok_parcial | ok_parcial | 0.0000 |  |
| `gif→webp` | real | 271.3 | ok_parcial | ok_parcial | 0.0091 |  |
| `ico→avif` | real | 77.6 | ok | ok | 0.0065 |  |
| `ico→bmp` | real | 32.1 | ok_parcial | ok_parcial | 0.0000 |  |
| `ico→gif` | real | 81.4 | ok | ok | 0.0081 |  |
| `ico→jpg` | real | 39.9 | ok | ok | 0.0049 |  |
| `ico→pdf` | real | 38.3 | ok | ok | 0.2575 |  |
| `ico→png` | real | 33.6 | ok | ok | 0.0000 |  |
| `ico→tif` | real | 30.4 | ok | ok | 0.0000 |  |
| `ico→webp` | real | 31.4 | ok | ok | 0.0054 |  |
| `jpg→avif` | real | 516.2 | ok | ok | 0.0053 |  |
| `jpg→bmp` | real | 86.1 | ok_parcial | ok_parcial | 0.0000 |  |
| `jpg→gif` | real | 741.9 | ok | ok | 0.0065 |  |
| `jpg→ico` | real | 28.8 | **fallo** | ok_parcial | — | ≤256 px |
| `jpg→pdf` | real | 215.0 | ok | ok | 0.3005 |  |
| `jpg→png` | real | 336.4 | ok | ok | 0.0000 |  |
| `jpg→tif` | real | 83.4 | ok | ok | 0.0000 |  |
| `jpg→webp` | real | 208.1 | ok | ok | 0.0041 |  |
| `png→bmp` | real | 194.8 | ok_parcial | ok_parcial | 0.0010 |  |
| `png→gif` | real | 888.4 | ok_parcial | ok_parcial | 0.0089 |  |
| `png→ico` | real | 30.7 | **fallo** | ok_parcial | — | ≤256 px |
| `png→tif` | real | 193.5 | ok_parcial | ok_parcial | 0.0000 |  |
| `svg→jpg` | real | 82.9 | ok | ok | 0.0219 | rasteriza |
| `svg→png` | real | 92.2 | ok | ok | 0.0000 | rasteriza |
| `svg→webp` | real | 87.7 | ok | ok | 0.0209 | rasteriza |
| `tif→avif` | real | 939.2 | ok_parcial | ok_parcial | 0.0040 |  |
| `tif→bmp` | real | 292.2 | ok_parcial | ok_parcial | 0.0010 |  |
| `tif→gif` | real | 877.8 | ok_parcial | ok_parcial | 0.0089 |  |
| `tif→ico` | real | 30.9 | **fallo** | ok_parcial | — | ≤256 px |
| `tif→jpg` | real | 236.6 | ok_parcial | ok_parcial | 0.0032 |  |
| `tif→pdf` | real | 209.6 | ok_parcial | ok_parcial | 0.2609 |  |
| `tif→webp` | real | 306.8 | ok_parcial | ok_parcial | 0.0032 |  |
| `webp→avif` | real | 579.1 | ok | ok_parcial | 0.0056 |  |
| `webp→bmp` | real | 87.6 | ok_parcial | ok_parcial | 0.0000 |  |
| `webp→gif` | real | 771.3 | ok | ok_parcial | 0.0062 |  |
| `webp→ico` | real | 31.3 | **fallo** | ok_parcial | — | ≤256 px |
| `webp→jpg` | real | 177.8 | ok | ok_parcial | 0.0038 |  |
| `webp→pdf` | real | 220.3 | ok | ok_parcial | 0.3011 |  |
| `webp→png` | real | 331.4 | ok | ok_parcial | 0.0000 |  |
| `webp→tif` | real | 100.7 | ok | ok_parcial | 0.0000 |  |

---

## 4. Lo que el contrato NO pudo juzgar

**29 de 62 aristas salen `ok` y 33 salen `ok_parcial`.** `ok_parcial` no es un
defecto de la conversión: es el contrato diciendo *«no he podido comprobarlo»*, y
saber exactamente qué no pudo comprobar vale más que el veredicto.

### 4.1 La sonda no sabe leer las cabeceras de BMP ni de ICO — 21 de 116 celdas

```
sondear(png2bmp_A.bmp)  -> firma='bmp', categoria='desconocida', ancho=None, alto=None, profundidad=None
sondear(avif2ico_B.ico) -> firma='ico', categoria='desconocida', ancho=None, alto=None, profundidad=None
punto1_estado(...)      -> 'evaluado'   (la FIRMA sí está en el vocabulario)
```

El punto 1 pasa —la firma está—, pero los puntos **3 (propiedades declaradas)** y
**4 (pedido frente a obtenido)** se declaran **no cubiertos** en las 14 celdas
`*→bmp` y las 7 celdas `*→ico`. Consecuencia: **todo destino `bmp` o `ico` tiene
techo `ok_parcial`, y el hallazgo de §1 pasa por delante del contrato sin que
nadie pueda verlo.**

Es la misma familia que el punto de `CLAUDE.md` §5 sobre los cuatro estados de
cobertura, pero **un escalón distinto**: aquí la firma sí está en el vocabulario
y lo que falta es el **lector de cabecera**. Un formato puede estar `evaluado` en
el punto 1 y ser opaco en el 3 y el 4.

### 4.2 `gif→png` con 2 colores: el contrato dice `fallo` y la conversión es EXACTA

Con la semilla B (`alpha.png` → GIF de **2 colores**), `magick B.gif salida.png`
devuelve `rc=0` y el contrato lo tumba:

```
I4 · fallo · DEGRADACION DE PROFUNDIDAD no pedida ni inevitable
```

La entrada declara `Depth: 8-bit`; la salida, `Depth: 2/8-bit`. Pero en un PNG
**paletizado** ese 2 son los bits del **índice de paleta**, no los del canal: los
componentes de la paleta siguen siendo de 8 bits.

```
magick compare -metric RMSE B.gif salida.png null:   ->   0 (0)
```

**RMSE 0,000000 — píxel a píxel idéntico.** La regla I4 confunde profundidad de
índice con profundidad de canal, y **borra una conversión perfecta**: como el
veredicto es `fallo`, `nucleo._un_salto` devuelve antes de `t.recoger()` y la
salida se va con el directorio desechable. **La arista se marca `real` con el
motivo escrito en el JSON**; marcarla `nominal` habría sacado del grafo una
arista exacta por un falso positivo, que es peor que la enfermedad.

### 4.3 El punto `4_alfa` no se cubre nunca que la entrada declare alfa — 57 de 116 celdas

`filex/contrato.py:verificar()` llama a `verificador.verificar(...)` **sin
`alfa=True`**, así que `min(α)` no se calcula y el punto queda sin cubrir en
cuanto la entrada declara canal alfa. Y **la trampa 1 sale confirmada con
número**: de las semillas A, `A.png`, `A.gif` y `A.tif` declaran alfa y las tres
dan **`min(α) = 1,0` — trivial**. El contrato no puede distinguirlo, así que no
puede exigir conservación ni perdonarla.

Lo que costaría cerrarlo, **MEDIDO** (mediana de 5):

| Fichero | `verificador.alfa_minimo` (en proceso) | `magick -format "%[fx:minima.a]"` |
|---|---:|---:|
| `A.png` 1920×1080 (2,07 Mpx) | **115,95 ms** | 667,77 ms |
| `A.tif` 1920×1080 | **104,59 ms** | 679,00 ms |
| `B.png` 200×200 (0,04 Mpx) | **0,43 ms** | 78,69 ms |

**Y esto MATIZA la regla de `CLAUDE.md` §5** *(«a partir de ~0,1 Mpx, la sonda
externa»)*: para `min(α)` **el lector en proceso gana 5,8× a 2,07 Mpx**. No
contradice a `bench/contrato-quinto-punto.md` §4.3, que medía **tinta** (recorrer
y promediar todo el raster) y no `min(α)` (una reducción que trabaja sobre un
solo canal). **El cruce de los 0,1 Mpx es POR MEDIDA, no una constante del
régimen.** Salvedad honesta: `A.png` son 42 855 B para 2,07 Mpx —es una imagen
sintética que se descomprime muy barata— y el lanzamiento de proceso de `magick`
pesa ~30–40 ms del total.

En números de conversión: cerrar `4_alfa` costaría **+54 %** sobre `png→tif` en
la semilla A (115,95 sobre 193,5 ms) y **+1,3 %** en la B (0,43 sobre 33,9 ms).
**No es gratis y no es caro siempre: es una decisión por tamaño.**

### 4.4 El punto 5 sale limpio, y es un resultado

**0 sobrantes en 124 celdas.** La regla N9 informa en las 117 celdas que llegaron
al contrato que *«el fichero declarado lleva el 100,0 % de los bytes escritos»*.
Ninguno de estos ocho destinos genera ficheros auxiliares — a diferencia de
`magick … out.html`, que deja un `_map.shtml`. **Un punto 5 que sale limpio 124
veces seguidas no demuestra que sobre: demuestra que el conjunto de destinos que
lo activan es pequeño y hay que saber cuál es.**

---

## 5. Fidelidad: la trampa 24, con números

`*→jpg` con la semilla B da un RMSE **contra el origen** que parece catastrófico,
y no lo es: el origen tiene alfa y el motor lo aplana sobre blanco
(`-background white -flatten`, que es lo correcto).

| arista | RMSE vs origen (`B.png`, con alfa) | RMSE vs **referencia ideal degradada** |
|---|---:|---:|
| `avif→jpg` | 0,8017 | **0,0185** |
| `bmp→jpg` | 0,8017 | **0,0168** |
| `gif→jpg` | 0,7994 | **0,0432** |
| `ico→jpg` | 0,7994 | **0,0432** |
| `tif→jpg` | 0,8017 | **0,0168** |
| `webp→jpg` | 0,8017 | **0,0168** |

Referencia ideal = `magick B.png -background white -flatten ref.png`.
**Sin esa columna, seis conversiones correctas se contarían como destruidas** —
que es literalmente la trampa 24, ahora medida también en el eje del alfa y no
solo en el del gris.

**Conservación de alfa: 7 de 7 destinos que la admiten la conservan.** Con la
semilla B (`min(α)=0`), las salidas `png`, `tif`, `webp`, `bmp`, `ico`, `avif` y
`gif` dan todas `min(α)=0`. `jpg` y `pdf` no la admiten y salen sin canal alfa,
que es lo esperado.

**`svg→png` SÍ rasteriza el texto** — no es el fallo de `resvg`. Midiendo la
banda de texto (y 165–232) de `svg2png_A.png`: tinta **8,38 %**, `min = 0,067`
(hay glifos negros). Recordatorio: la pérdida de `svg→raster` es que el texto deja
de ser seleccionable, no que desaparezca; el grafo ya la penaliza con
`rasteriza=True`.

---

## 6. Cambios que pido

**No he tocado ningún `.py` de `filex/`.** Aquí van los tres, con el diff exacto.

### 6.1 GRAVE — el `pedido` que lee el motor y el que lee el contrato no son el mismo

**MEDIDO, tres celdas que lo cierran por los dos lados.** `filex/motores.py` lee
`pedido["ancho"]` (línea 168); `filex/verificador.py` lee
`pedido["params"]["ancho"]` (líneas 3359, 4380, 4516, 4669). Nadie traduce.

| `pedido` | ¿El motor redimensiona? | Veredicto | Salida |
|---|---|---|---|
| `{"ancho": 800}` | **sí**, 800×450 | **`fallo` I1/V7** | **se pierde** |
| `{"ancho": 800, "params": {"ancho": 800}}` | sí, 800×450 | `ok_parcial` | 800×450 |
| `{"params": {"ancho": 800}}` | **no**, 1920×1080 | `fallo` I1 | se pierde |

La primera fila es lo que entrega la CLI: `filex/cli.py:86` hace
`pedido = json.loads(args.params)` **plano**. Es decir, hoy
`filex convertir a.png b.tif --params '{"ancho":800}'` produce una salida
correcta y la tira. Y sobre `gif`, `webp` y `tif` lo hace; sobre `bmp` e `ico`
**no**, porque ahí la sonda es ciega (§4.1) — el mismo pedido pasa o falla según
si el destino tiene lector de cabecera.

El verificador **ya acepta la forma plana en dos sitios**
(`par.get("solo_audio") or pedido.get("solo_audio")`, línea 3254;
`pedido.get("params",{}).get("ocr") or pedido.get("ocr")`, línea 4798), así que
esto es una inconsistencia interna, no un contrato deliberado. El arreglo más
barato es **una línea en el núcleo**, que no obliga a tocar el verificador ni a
cambiar lo que la CLI entrega:

```diff
--- a/filex/nucleo.py
+++ b/filex/nucleo.py
@@ _un_salto
-        res = contrato.verificar(dentro, entrada, dict(pedido, destino=arista.destino),
-                                 censo)
+        # El motor lee el pedido PLANO y el verificador lo lee bajo "params".
+        # Sin este espejo, `--params '{"ancho":800}'` sale `fallo I1/V7`: el
+        # motor obedece y el contrato, que no ve la peticion, llama al
+        # redimensionado "no pedido". MEDIDO en bench/sondeo-imagemagick.md §6.1.
+        espejo = {k: v for k, v in pedido.items() if k != "params"}
+        res = contrato.verificar(
+            dentro, entrada,
+            dict(pedido, params={**espejo, **(pedido.get("params") or {})},
+                 destino=arista.destino),
+            censo)
```

**Verificado en memoria** (parcheando `contrato.verificar` en una sesión de
prueba, sin tocar el fichero): con el parche, `{"ancho": 800}` da `ok_parcial` y
**800×450**.

### 6.2 GRAVE — el `pedido` solo llega al ÚLTIMO salto, y el contrato del último salto compara contra el intermedio

`nucleo._un_salto` recibe `pedido if ultimo else {}`. Medido **antes** de aplicar
este sondeo, cuando `png→tif` se resolvía como `png→pdf→tif`:

```
filex convertir A.png cli.tif --params '{"ancho":800}'
  png→pdf [imagemagick]  rc=0  379 ms  contrato 5/6 → ok_parcial
  pdf→tif [ghostscript]  rc=0  717 ms  contrato 6/6 → ok
  salida: 1920x1080          <-- el ancho pedido se ignoró, y el veredicto es ok_parcial
```

**El ancho pedido se perdió sin que ningún punto del contrato lo notara**, porque
el primer salto no recibió el pedido y el segundo lo comparó contra el PDF
intermedio, no contra `A.png`.

**Este sondeo lo arregla por accidente para ese par** —`png→tif` pasa a ser
directo, coste 1,0019 frente a 2,2 del camino de dos saltos— **pero el mecanismo
sigue vivo, y sobre `svg→pdf` da algo peor**, medido con el árbol tal como queda
después de este sondeo:

```
filex convertir svg_A.svg out.pdf --params '{"dpi":400}'
  svg→jpg [imagemagick]  rc=0  126 ms  contrato 6/6 → ok      <-- NO recibe dpi: rasteriza a 480x240
  jpg→pdf [imagemagick]  rc=0  157 ms  contrato 6/6 → ok      <-- recibe dpi=400
  veredicto: ok        /MediaBox 0 0 86.4 43.2     (3,0 x 1,5 cm)
```

**Pedir MÁS resolución produjo una página MÁS pequeña con exactamente los mismos
480×240 píxeles, y los dos saltos pasan el contrato 6 de 6.** El `dpi` es un
parámetro del **primer** salto —el que rasteriza el vector— y llega solo al
último, donde no significa lo mismo.

**No propongo el diff porque no es una línea: hay que decidir qué parte del
pedido es del CAMINO (geometría, ppp, el `dpi` de rasterizado) y qué parte es del
DESTINO (calidad, códec), y esa decisión es de arquitectura.** Lo dejo como
pendiente nombrado, con el caso reproducible arriba.

### 6.3 La sonda del verificador no lee cabeceras de BMP ni de ICO

Es la causa de §4.1 y de que §1 pase inadvertido. **BMP e ICO son cabeceras
triviales** —`BITMAPINFOHEADER` da ancho, alto y bits por píxel en 12 bytes;
el `ICONDIRENTRY` da ancho y alto en dos—, y leer el ICO es además lo único que
permitiría atrapar el `ancho & 0xFF` de §1: bastaría comparar el byte del
directorio con la anchura del BMP incrustado y avisar cuando difieran. **Es una
regla de dos comparaciones que atrapa un `rc=0` con basura.**

No pongo diff porque `filex/verificador.py` es de otro agente y la sonda tiene
una estructura por formato que no me toca decidir.

---

## 7. Pendientes

1. **La resolución de `imagen→pdf`.** §2 deja abierto si la corrección es
   `-units PixelsPerInch` o **calcular la densidad para ajustar a la página**,
   que es lo que el docstring de `motores.py` afirma que ya se hace y no se hace.
   Medir las dos contra un A4 exacto. PENDIENTE.
2. **La ventana 257–512 px del ICO.** Sondeada en tres puntos (257, 320, 512) y
   acotada por arriba entre 512 y 513. **No está medido si la corrupción es
   siempre `lado & 0xFF`** o si hay algún tamaño intermedio que se comporte
   distinto. PENDIENTE.
3. **Las 93 aristas `sin_sondear` que quedan en el grafo** son de Ghostscript, del
   motor de contenedor y de ffmpeg (S2 y S3 lo están haciendo). ImageMagick queda
   a **67 real, 0 sin sondear**.
4. **`avif→gif` cuesta 1 922,7 ms**, 63× la arista más barata del mismo motor. No
   se ha investigado si es el decodificador AVIF o el `palettegen` interno.
   PENDIENTE.

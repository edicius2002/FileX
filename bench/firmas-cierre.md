# El cierre del bloque de firmas: los marcadores que no caben en 512 bytes, los 86 indeterminados y la prueba ancha dentro del contenedor

**Agente F2 · 2026-08-28 · worktree aislado, sin GPU y sin su lock**
**Encargo:** C37 (los 12 formatos de la deuda de firmas), C30 (repetir la prueba ancha
de falsos positivos **dentro** del contenedor) y C28 (los 86 destinos indeterminados
del censo).
**Fuentes que se leen y no se tocan:** `bench/firmas-contrato.md` (F1),
`bench/contrato-familia-resvg.md`, `bench/salidas-referencia/referencia.json`,
`bench/salidas-firmas/` entero.

---

## 0. Las frases obligatorias

1. **`.pcd` no era un caso benigno: era un falso positivo VIVO — MEDIDO.**
   `firmas-contrato.md` §10.3 escribió *«`.pcd` se clasifica hoy como `mpegaudio`…
   **No produce falso positivo** —`.pcd` no está en la tabla— pero está declarado»*.
   El hecho es cierto y la consecuencia es falsa: el contrato **completo** sobre un
   `.pcd` legítimo devolvía **`fallo`**, porque con firma `mpegaudio` la sonda lo
   lleva a `_mp3` y de ahí sale `G4 fallo: duración nula o ilegible`. **El falso
   positivo no lo fabricaba la tabla de extensiones: lo fabricaba la CATEGORÍA**, que
   es un sitio que nadie estaba mirando. Es la trampa 58 otra vez.

2. **Leer 2 056 bytes cuesta lo mismo que leer 512, así que la puerta por extensión
   que proponía el pendiente no se paga en tiempo — MEDIDO.** `open+read(2056)` menos
   `open+read(512)` sobre los mismos 78 ficheros da **−5,93 µs por fichero en una
   vuelta y +3,20 en la siguiente**: el signo **no se conserva**, o sea que la
   diferencia está por debajo del suelo de la tanda (trampa 36). La puerta se
   dispararía en **4 de 403 destinos locales (0,99 %)** y **4 de 331 del contenedor
   (1,21 %)**, y lo que costaría es el invariante de `firma_real` —*«ningún
   subproceso, ninguna extensión»*—. **Se lee siempre.**

3. **El reparto «79 + 7» de los 86 indeterminados es «56 + 17 + 13», y son TRES
   clases con tres remedios distintos — MEDIDO** sobre el mismo `categorias.json`
   que produjo la frase.

4. **De los 56 que «ningún motor de esta máquina escribe», el corpus FATE cerraría
   como mucho 15. Otros 21 se cierran con una INVOCACIÓN mejor, y lo he probado
   escribiendo seis — MEDIDO.** El `rc` de cada celda lo dice sin ambigüedad:
   `AVERROR_ENCODER_NOT_FOUND` (11) es «no está el codificador»,
   `AVERROR_EXPERIMENTAL` (3) es «pide `-strict -2`» y `EINVAL` (18) es «la
   invocación no cumplía las restricciones del formato». **Otros 8 no son formatos:
   son volcados de METADATOS** (`8bim`, `app1`, `exif`, `icc`, `iptc`…) que solo
   existen si la ENTRADA los trae, y ningún corpus de salidas los produce.
   **No pido la descarga: no la necesita el 73 % del problema.**

5. **De los 17 «la muestra describe al escritor», CERO tienen un segundo escritor
   entre los 20 adaptadores de esta máquina y del contenedor — MEDIDO.** El remedio
   que propone el pendiente no tiene ingredientes. Lo que sí lo cierra es mirar el
   prefijo de cada uno: **tres de ellos ya tenían su marcador dentro de la sonda**
   (`#FIG `, `GIMP Palette` y `solid ` llevan en `MARCAS_TEXTO` desde que se escribió
   la tabla) y lo que faltaba era **la fila de `EXT_A_FIRMAS` que lo acepta**.
   **17 de 17 cerrados sin escribir una sola muestra nueva.**

6. **La prueba ancha local da 0 falsos positivos sobre 345 salidas y la del
   CONTENEDOR da 4 — MEDIDO.** Es el motivo por el que el pendiente 7 de F1 valía la
   pena: **el vocabulario se censó con ImageMagick y `ffmpeg`**, y dentro escriben
   `vips`, `graphicsmagick`, pandoc e inkscape. Los cuatro son de una línea: el
   mágico de VIPS es de **endianness** y la tabla traía media; GraphicsMagick escribe
   `id=MagickCache` y no `id=MagickPixelCache`; su PCX va **sin comprimir** y el
   predicado exigía RLE; y `.mat` son **dos formatos** de dos escritores.

7. **Tocar `firma_real` caduca 172 aristas selladas, y NINGUNA de las 172 puede
   moverse — MEDIDO.** La huella hace exactamente su trabajo (trampa 32) y su
   granularidad es del par (motor, componente), no de la arista: los 32 formatos que
   el cambio toca no aparecen ni como origen ni como destino en ninguna de las 172.
   **Deja la suite en rojo por una prueba, y esa prueba tiene razón.** (§2.7)

8. **`EXT_FAMILIA` era la única tabla con el defecto de la trampa 48 — MEDIDO, y con
   control positivo.** Un detector de AST sobre los ocho módulos de `filex/` que
   deciden algo devuelve **0 sospechas**, y el mismo detector marca la forma
   histórica exacta de `EXT_FAMILIA` (control positivo, sin el cual el cero no
   significa nada). El detector tuvo que aprender a **seguir un nivel de llamada**:
   sin eso acusaba a `EXT_A_FIRMAS`, que sí parte pero dentro del ayudante `_ext`.

9. **Una auditoría que nadie había hecho: había 6 firmas HUÉRFANAS** —nombres que
   `firma_real` sabe devolver y que **ninguna extensión acepta**—, y tres eran justo
   tres de los 17 de C28. Quedan 3, y ninguna es destino declarado por ningún
   adaptador. **En el otro sentido, 0**: ninguna extensión espera un nombre que la
   sonda no sepa producir.

---

## 1. Método y confinamiento

- **Directorio desechable** para todo (`%TEMP%\claude\…\scratchpad\F2_*`), listado
  antes y después. **La raíz del repositorio quedó limpia.** Los satélites de R21 se
  observaron en vivo: `imagemagick → .htm/.html` deja un `_map.shtml` y un `.png`,
  y `ffmpeg → .m3u8` deja el `.ts` (§5.2).
- **Ningún subproceso sin `stdin=DEVNULL`, sin array de argumentos y sin `timeout=`
  explícito.** Los ficheros se escribieron con la herramienta de escritura, nunca
  por heredoc (trampa 19).
- **Ni GPU ni su lock.** El otro agente la tenía en exclusiva durante toda la tanda.
- **Medianas de n≥9** con los dos testigos, tope de 20 s en el de proceso. La tanda
  de coste salió `limpia` (deriva 0,944, nivel 1,104), que es inusual en esta
  máquina y por eso se declara: **las cifras absolutas no se comparan con las de
  otro informe**; los ratios de dentro de la tanda, sí.
- **`bench/salidas-referencia/referencia.json` se leyó y no se tocó.** Las 53 salidas
  del patrón oro **no están versionadas** (195 MB de binarios regenerables), así que
  se regeneraron **fuera del repositorio** con `_regenera53.py` (§5.1).
- **Censo de `docker ps -a` antes y después, con `-a`** (trampa 37). Cero huérfanos.

---

## 2. C37 — los 12 formatos de la deuda de firmas

### 2.1 El censo, con TRES semillas — MEDIDO

`firmas-contrato.md` §3.2 dice que el marcador de PICT está en el byte 522 y el de
PCD en el 0x800. Antes de creerlo se midió, escribiendo cada destino desde **tres
entradas de contenido y geometría distintos** (§3 de `CLAUDE.md`, el sesgo de
semilla) y sacando los tramos en los que coinciden **las tres**:

| Destino | n | Tramo común | Qué es |
|---|---:|---|---|
| `pict`, `pct` | 3 | bytes 0–518 (ceros + tamaño heredado) y **522–544** | `00 11 02 FF 0C 00` en el **522**: opcode de versión 2 + opcode de cabecera |
| `pcd`, `pcds` | 3 | **los 4 096 primeros bytes, enteros** | relleno `FF`/`0E` y **`PCD_IPI` en el 2048** |
| `map`, `hrz` | 3 | **ninguno** | confirma que están bien en `EXT_SIN_FIRMA` |
| `palm`, `otb`, `wbmp` | 3 | tramos sueltos de relleno `00`/`FF` | contenido, no marcador |

**Los dos marcadores son literales de longitud 6 y 7 en un desplazamiento fijo**, o
sea exactamente la forma que la tabla `FIRMAS` ya sabe tratar. Lo único que sobraba
era la ventana.

### 2.2 Reproducir la medida ajena antes de arreglarla — MEDIDO

Trampa 58: *«antes de arreglar una trampa ajena, reproduce su medida y sondea su
mecanismo»*. Con el `verificador.py` de HEAD y muestras reales de `magick`:

| Destino | `firma_real` | `punto1_estado` | Mecanismo sondeado |
|---|---|---|---|
| `.pict`, `.pct` | `desconocido` | `sin_vocabulario` | 512 bytes a cero: no casa con nada y cae al final |
| `.pcd`, `.pcds` | **`mpegaudio`** | `sin_vocabulario` | `cab[0]=0xFF`, `cab[1]=0xFF` → pasa `FF Ex`; bits de capa = `0b11` ≠ 0 → no es ADTS |

Las dos afirmaciones de F1 se reproducen. **Y aparece la tercera, que F1 no vio:**

```
CONTRATO sobre un .pcd LEGITIMO, con el verificador de HEAD
  veredicto: fallo
  [G3 informativo] extension sin firma conocida: .pcd
  [G4 FALLO]       duracion nula o ilegible
  [G4 aviso]       bitrate no positivo
```

**`firmas-contrato.md` §10.3 declara este caso inofensivo y no lo es.** El punto 1
efectivamente no dispara —`.pcd` no estaba en `EXT_A_FIRMAS`—, pero la firma no
solo alimenta al punto 1: **alimenta al despachador de `sondear_en_proceso`**, y una
firma `mpegaudio` manda el fichero a `_mp3`. La lección transferible es la de la
trampa 58 con un caso nuevo: *el hecho no implica la consecuencia, y menos cuando la
consecuencia vive en otro módulo del que la trampa mira.*

Después del arreglo, el mismo fichero: **`veredicto: ok_parcial`, `punto1:
evaluado`, cero hallazgos de severidad `fallo`.**

### 2.3 El coste de la ventana larga, y por qué NO hay puerta por extensión — MEDIDO

El encargo pedía medir *«el coste de esa lectura extendida y cuándo se dispara»*.
Se midieron las dos cosas **y un error de arnés propio, que es la mitad del interés**:

> **Refutación de mi primera medida.** La primera versión medía las variantes como
> `leer(2056)` seguido de una llamada a `V.firma_real`, **que vuelve a abrir el
> fichero**: dos `open` por celda. Daba **×2,1** y ese ×2,1 era el arnés, no el
> diseño. Es la trampa 36 con otra cara: *no compares dos totales que contienen el
> trozo; mide el trozo*.

**A · el primitivo, aislado, y la tanda repetida** (78 ficheros, 273,5 MB, n=9):

| | `read(512)` | `read(2056)` | Δ por fichero |
|---|---:|---:|---:|
| vuelta 1 | 5,9225 ms | 5,4599 ms | **−5,93 µs** |
| vuelta 2 | 5,6971 ms | 5,9469 ms | **+3,20 µs** |

**El signo no se conserva.** Por la regla de la trampa 36, eso no es una medida: es
ruido. **Leer 2 KB y leer 512 B es la misma cifra en este disco**, y tiene una
explicación mecánica —el clúster de NTFS son 4 KB y las dos lecturas son la misma
página—, pero lo que la sostiene es el control, no la explicación.

**B · `firma_real` entera, HEAD contra árbol, pareado en esta tanda** (trampa 59: la
versión histórica se mide también, no se cita):

| | HEAD | árbol | Δ por fichero | ratio |
|---|---:|---:|---:|---:|
| vuelta 1 | 6,178 ms | 6,8706 ms | +8,88 µs | ×1,112 |
| vuelta 2 | 6,7326 ms | 6,9507 ms | +2,80 µs | ×1,032 |

Aquí **el signo sí se conserva**, así que la diferencia es real: **+2,8 a +8,9 µs por
fichero**. Y no es la lectura —A dice que la lectura es gratis—: son las dos
comparaciones de `FIRMAS_LARGAS`, el predicado de 3DS y las cinco entradas nuevas de
`FIRMAS`. Sobre un `inspect` de 0,21–0,59 ms es el **0,5–4 %**; sobre una conversión,
indistinguible de cero.

**C · cuándo se dispararía la puerta:**

| Censo | destinos | dispararían | % |
|---|---:|---|---:|
| local (`ffmpeg`, `imagemagick`, `gs`) | 403 | `imagemagick:{pcd,pcds,pct,pict}` | **0,99 %** |
| contenedor (13 motores) | 331 | `graphicsmagick:{pcd,pcds,pct,pict}` | **1,21 %** |

**Decisión, y va contra la vía que apuntaba el encargo:** *se lee siempre*. La puerta
ahorraría algo que está por debajo del suelo de medición y costaría el invariante que
el propio docstring de `firma_real` declara —*«ningún subproceso, ninguna
extensión»*—. Con la puerta, un PICT entregado con extensión `.png` seguiría saliendo
`desconocido`; sin ella, sale `pict` y `G3` dice la verdad en vez de encogerse de
hombros. **La ventana de DECISIÓN sigue siendo de 512 bytes**: ensancharla endurece
la heurística de texto del final de `firma_real` —exigiría que fuesen imprimibles
2 056 bytes en vez de 512— y movería clasificaciones que nadie ha pedido mover. Hay
una prueba que lo fija (`test_un_texto_con_un_byte_de_control_en_el_700…`).

### 2.4 El SITIO de `FIRMAS_LARGAS`, elegido midiendo

Va **después** de la tabla `FIRMAS` y **antes** de los predicados:

- **después de `FIRMAS`**, para que un literal del byte 0 —curado con el censo de
  F1— siga mandando. Hay una prueba con un JPEG que lleva `PCD_IPI` en el 0x800 y
  sigue siendo un JPEG.
- **antes de los predicados**, porque el predicado de audio MPEG (`FF Ex`) es
  justo el que se traga un PCD entero.

### 2.5 Dos accionables MÁS de los que el encargo daba, y los dos refutan un motivo publicado — MEDIDO

El encargo daba por accionables `pict` y `pcd`. Mirando el dato del censo de F1 —que
ya estaba escrito y nadie había vuelto a leer— salen dos más:

| Formato | Motivo publicado en §3.2 | Lo que dice el dato |
|---|---|---|
| **`3ds`** | *«su marcador son dos bytes, `MM`, que chocan con el `MM\x00*` de TIFF. Añadirlo compraría un formato y arriesgaría todos los TIFF»* | **Las dos mitades se caen.** (a) TIFF y BigTIFF son literales de `FIRMAS` y ya se resolvieron arriba: llegar al predicado significa que no era un TIFF. (b) **El marcador no es de dos bytes: es AUTOVALIDANTE.** El chunk principal `0x4D4D` declara en sus 4 bytes siguientes (LE) la **longitud total del fichero**, y las dos muestras de assimp dicen **565 y 517** y pesan **565 y 517** |
| **`rb`** | *«marcadores de 2 a 6 bytes de formatos con un solo adaptador: mucho riesgo de colisión por muy poca demanda»* | **Falso para `rb`.** Las dos muestras de Calibre comparten **28 bytes**, y los diez primeros son `B0 0C B0 0C 02 00` más el literal **`NUVO`**. Diez bytes no son dos |

El `3ds` es además el caso que **da la regla general**: *un marcador corto deja de ser
corto en cuanto se comprueba contra otra cosa del propio fichero.* Cuesta un `fstat`
sobre un descriptor ya abierto, y solo lo paga quien empieza por `MM`.

### 2.6 Los seis restantes, acotados con su prefijo — MEDIDO

| Formato | n | Prefijo común medido | Veredicto |
|---|---:|---|---|
| `a64` | 3 | `00 40` (2 B) | dirección de carga del C64: **un campo, no una constante**. Se queda |
| `apm` | 3 | `00 20 01 00` (4 B) | cabecera de APM; 4 bytes con dos ceros. Se queda |
| `aptx` | 3 | `4b bf 4b bf` (4 B) | **es la SEÑAL, no un marcador**: son dos tramas idénticas de 2 B. Es el falso positivo (a) del método de F1, en otro formato |
| `aptxhd` | 3 | `73 be ff 73 be ff` (6 B) | ídem, dos tramas de 3 B. Se queda |
| `rso` | 3 | `01 00` (2 B) | código de formato (1 = 8 bits): campo. Se queda |
| `fbxa` | 2 | 64 B: `; FBX 7.5.0 project file\n; Created by the Open Asset Import Libr` | **banner con la versión dentro** → no puede ser literal. **Cerrado como FAMILIA** (`{"texto"}`). Y un aviso: **las dos muestras pesan 9 157 B las dos**, o sea que ahí hay n=1 disfrazado de n=2 — **PENDIENTE** |

**Balance de C37: de los 12, cerrados 5** (`pict`, `pct`, `pcd`, `pcds` como formato;
`3ds`, `rb` y `fbxa` por sus tres vías) **y 5 acotados con el dato delante**.

### 2.7 Lo que el arreglo CADUCA, y lo que de eso podía moverse — MEDIDO

Tocar `firma_real` está dentro del cierre de llamadas de `verificar()`, así que caduca
el componente `contrato` de la huella de **todos** los motores sellados:

| Motor | aristas selladas | componentes caducados | aristas que el cambio PUEDE mover |
|---|---:|---|---:|
| `imagemagick` | 62 | `contrato` | **0** |
| `ffmpeg` | 70 | `contrato` | **0** |
| `doc_libreoffice` | 16 | `contrato` | **0** |
| `doc_pandoc` | 16 | `contrato` | **0** |
| `doc_calibre` | 8 | `contrato` | **0** |
| **Total** | **172** | | **0** |

Los 32 formatos que el cambio toca no aparecen **ni como origen ni como destino** en
ninguna de las 172. **La huella funciona y su granularidad es del par (motor,
componente), no de la arista**: la trampa 32 midió que cambiar `-quality 85` por `90`
caduca 62 aristas de ImageMagick y 0 de las otras 148, y aquí se ve el otro extremo
del mismo diseño —un cambio confinado a 4 destinos de 403 caduca las 172—.

**No he resondeado, y no lo he hecho a propósito.** La trampa 61 dice que resellar
solo es legítimo cuando el cambio es **de algoritmo de huella** y el código medido es
el mismo; aquí el código medido **sí cambió**, así que resellar sería indulgencia.
El resondeo exige escribir en `filex/sondeo/*.json` y en tres informes de `bench/`
que no son míos. **Queda para quien integre**, y con el número de arriba delante: es
un resondeo que no puede cambiar ninguna de las 172.

---

## 3. C30 — la prueba ancha de falsos positivos DENTRO del contenedor

`firmas-contrato.md` §10.7 lo dejaba así: *«La verificación del censo dentro del
contenedor solo guardó 64 bytes de cabecera por muestra, así que la prueba ancha de
falsos positivos cubre los 385 destinos locales, no los 162 del contenedor.»*

**Hecha.** Se llevó `filex/verificador.py` dentro de `filex-c13` (es solo biblioteca
estándar; el contenedor trae `python3`) y se escribieron **288 destinos × 3 semillas
= 864 celdas, 857 escritas**, con 13 motores.

### 3.1 Cuatro falsos positivos, y la prueba local no podía verlos — MEDIDO

**La prueba ancha local da 0 de 345. La del contenedor da 4 destinos / 11 celdas.**
El motivo es de una línea y vale como regla: **el vocabulario se censó con
ImageMagick y `ffmpeg`, y describe a ImageMagick y a `ffmpeg`.**

El arnés crudo daba 17 celdas y 6 destinos; un **triaje con testigo externo** —
`magick identify`, `gm identify`, `vipsheader`, ida y vuelta con el propio motor —
separa dos cosas con la misma pinta, porque **el árbitro no puede ser quien escribió
el fichero**:

| # | Celda | Qué pasaba | Arreglo |
|---|---|---|---|
| 1 | `vips → .vips` (3) | **el mágico de VIPS es de ENDIANNESS y la tabla traía media**: `FIRMAS` declaraba `08 F2 A6 B6` y vips 8.18.3 en x86 escribe `B6 A6 F2 08`. `magick identify` lo lee como `VIPS 64x48 16-bit` | las dos formas en la tabla |
| 2 | `graphicsmagick → .mpc` (3) | GM escribe **`id=MagickCache`**; la tabla solo traía el `id=MagickPixelCache` de ImageMagick | una entrada más |
| 3 | `graphicsmagick → .pcx` (2) | el predicado exigía `cab[2] == 1` (RLE) y **GM escribe PCX sin comprimir**, byte 2 = `0x00` | `cab[2] in (0, 1)`: la codificación es un campo, no parte del marcador |
| 4 | `vips → .mat` (3) | **colisión de extensión, no laguna de firma**: la tabla espera `MATLAB 5.0` y vips escribe su **matriz ASCII** (`64 48\n57847 …`, que `vipsheader` lee como `64x48 double, 1 band, matrixload`) | aceptar los dos y **declarar la colisión**, como se hizo con `.avs` |

**Los tres primeros son lagunas del vocabulario; el cuarto no lo es y no lo puede
ser:** ninguna firma puede decidir cuál de los dos `.mat` se pidió.

### 3.2 Dos capturas LEGÍTIMAS que conviene no perder — MEDIDO

De las 17 celdas crudas, 6 eran verdaderos positivos:

- **`graphicsmagick → .x`**: un PNG entregado con extensión `.x`. Es el fallo
  emblemático del proyecto, y lo atrapa **`G3`, no `G6`** — porque `.x` **sí** está
  en el vocabulario, como el `directx_x` de assimp. **Dos motores del mismo
  contenedor se reparten la misma extensión**, y esa es la única razón por la que
  aquí gana la firma y en el caso `.group4` gana G6.
- **`pandoc → .rtf`**: un fragmento `{\pard \ql \f0 …` sin `{\rtf1`. Con `-s` la
  misma semilla da `{\rtf1\ansi…` y `firma_real` devuelve `rtf`: **es un defecto de
  la invocación de ConvertX**, no del formato ni de la tabla.

### 3.3 Dos defectos de invocación heredados, destapados por la prueba de humo — MEDIDO

El arnés del censo de F1 daba por `escrito` lo que el punto 1 atrapa:

- **`cjxl` escribe SIEMPRE un JXL**, mire la extensión que mire: `.apng` y `.exr`
  salían con `firma_real = jxl`.
- **`dvisvgm -o x.svgz` sin `-z` escribe un SVG en claro.**

Los dos son el fallo emblemático con motores del contenedor, y **el punto 1 los
atrapa**: es evidencia adicional para el pendiente 5 de F1 (G6 calibrada sobre un
solo motor).

### 3.4 G6 en el contenedor: 48 celdas, 16 destinos, **100 % GraphicsMagick** — MEDIDO

`b c g k m o r y p7 histogram info msl mvg null preview vid`, todos png→png. **0 de
los 13 motores restantes.** Eso **extiende** la nota de F1 —*«G6 está calibrada sobre
un solo motor»*— con el matiz que faltaba: no es que solo se haya probado con
ImageMagick, es que **el comportamiento es de la familia ImageMagick**, y aparece
también en su clon. Sigue siendo `aviso`, y con más razón.

### 3.5 La tanda repetida con los arreglos: 11 → 0, y sin una sola regresión — MEDIDO

Con los cuatro arreglos puestos se **reescribieron las 864 celdas** y se volvieron a
evaluar. Las dos tandas son comparables celda a celda (857 comparables, 0 solo en una
de ellas), y el `sha256` del verificador se anota en las dos
(`1812df12…` → `c023a9bc…`):

| | antes | después |
|---|---:|---:|
| **falsos positivos (celdas)** | **11** | **0** |
| falsos positivos (destinos) | 4 | **0** |
| **capturas legítimas que siguen atrapadas** | `gm→.x` (3), `pandoc→.rtf` (3) | **las mismas 6 celdas** |
| avisos `G6` | 48 celdas / 16 destinos | **48 / 16, idéntico** |
| fallos nuevos | — | **ninguno** |
| `G6` que desaparecen | — | **ninguno** |

**Que las dos capturas legítimas sigan es la mitad que importa:** una corrección que
apaga una detección buena no es una corrección, es una regresión con mejor pinta
(trampa 51). Y el `G6` idéntico dice que los arreglos tocaron la firma y nada más.

### 3.6 Reparto de cobertura, contenedor contra local — MEDIDO

| estado | contenedor antes (288) | contenedor después | % | local después (345) | % |
|---|---:|---:|---:|---:|---:|
| `evaluado` | 158 | **162** | 56,3 | 249 | 72,2 |
| `no_aplica` | 69 | **73** | 25,3 | 61 | 17,7 |
| `familia` | 34 | **42** | 14,6 | 10 | 2,9 |
| `sin_vocabulario` | **27** | **11** | **3,8** | 25 | 7,2 |

**`sin_vocabulario` cae de 27 a 11 en el contenedor** —48 celdas cambian de estado, y
las 48 desde `sin_vocabulario`— porque el cierre de los 17 de C28 (§4.2) es
precisamente de formatos que **solo el contenedor escribe**. Los 11 que quedan:
`calibre:pdb`, `gm:{histogram, info, msl, mvg, null, p7, pdb, preview, shtml, vid}`
— y **todos menos `pdb` y `shtml` son de la clase «el motor escribió otro formato»**
(§4.3), es decir G6, no vocabulario.

**El contenedor sigue evaluando 16 puntos menos que la máquina y quintuplicando
`familia`**, y no es un déficit nuestro: es que pandoc e inkscape escriben *markup*,
que es justo donde el marcador de formato no existe (§2.3 de `firmas-contrato.md`, el
control de tres semillas). **Publicar una sola cifra de cobertura sin decir con qué
motores se midió es publicar el catálogo de motores, no el del vocabulario.**

### 3.7 Un aviso de método que sale gratis y ahorra una hora

**La receta de tope de `CLAUDE.md` §3 no funciona tal cual en `filex-c13` — MEDIDO.**
`docker run --entrypoint timeout filex-c13 -k 5 N <orden>` devuelve **`rc=125` sin un
solo byte** en stdout ni en stderr, para cualquier orden (también
`timeout 30 /bin/echo hi`), porque `timeout` (coreutils 9.10) queda de **PID 1**. Con
**`--init`** la misma orden sale `rc=0`, y `timeout -k 5 3 sleep 30` devuelve **124 en
3 s**: el tope sí mata. Y el 125 es la trampa 25 otra vez — **es exactamente el código
que devuelve `docker run` cuando falla él**, así que un arnés con prisa lo lee como
«el motor no sabe escribir ese formato».

Y otro, del mismo sitio: **la colisión TGA/`cur` que el comentario de `firma_real`
declara depende de la SEMILLA.** `tga/icb/vda/vst` salen `cur` con dos semillas y
`desconocido` con la tercera. Hoy es inerte —están en `EXT_SIN_FIRMA`— pero con una
sola semilla se habría publicado como constante.

---

## 4. C28 — los 86 destinos indeterminados

### 4.1 El reparto real es de TRES clases, no de dos — MEDIDO

Reproduciendo el censo de F1 sobre su propio `categorias.json`, el reparto de
categorías **sale idéntico** (`1_evaluado: 298`, `2_deuda: 12`, `3_no_aplica: 106`,
`0_indeterminado: 86`), lo que valida la lectura. El reparto **de dentro de los 86**,
no:

| Motivo que guardó el censo | n | Lo que dice §10.1 | Remedio que admite |
|---|---:|---|---|
| «no se pudo escribir con ningún motor disponible» | **56** | «79» | §4.4 |
| «el prefijo es el banner del escritor, no del formato» | **17** | «7» | §4.2 |
| «el motor escribió otro formato (PNG): la muestra no describe este» | **13** | *(no aparece)* | §4.3 |

**La tercera clase no está en el pendiente y es la más interesante de las tres:** son
13 destinos en los que el motor **entregó un PNG**, es decir el fallo emblemático del
proyecto en estado puro. No son un problema del vocabulario: son la evidencia de que
G6 tiene trabajo.

### 4.2 Los 17: el remedio propuesto no tiene ingredientes, y no hace falta — MEDIDO

El pendiente dice que estos *«sí se pueden atacar con un segundo escritor por
formato — y tienes seis motores en el contenedor `filex-c13`»*. Contado:

> **0 de 17 tienen un segundo escritor**, ni real (en los dos censos) ni declarado
> (en los 20 adaptadores de `formatos.json`). `obj`/`objnomtl`/`stl`/`pbrt`/`assjson`
> solo los escribe assimp; los cinco de diapositivas y `chunkedhtml`, solo pandoc;
> `gpl`/`hpgl`/`pov`, solo inkscape; `xfig`, solo potrace; `cip`/`ftxt`, solo
> ImageMagick.

**Lo que sí cierra los 17 es mirar el prefijo de cada uno**, que estaba guardado y
nadie había vuelto a leer. La clase se parte en cuatro:

| Subclase | n | Formatos | Qué se hizo |
|---|---:|---|---|
| **El prefijo YA era un marcador, y la sonda ya lo tenía** | 3 | `xfig` (`#FIG `), `gpl` (`GIMP Palette`), `stl` (`solid `) | **`MARCAS_TEXTO` los traía desde que se escribió la tabla**: `firma_real` acertaba y el punto 1 salía `sin_vocabulario` porque ninguna extensión los aceptaba. Se añadió la fila |
| **El formato es HTML (o JSON, o XML)** | 8 | `revealjs s5 slidy slideous dzslides` (`<section id="`, `<div id="`), `assjson` (JSON), `cip` (`<CiscoIPPhoneImage>`), `hpgl` (`IN;`) | **nivel de FAMILIA**, que es la excepción 5 de F1 aplicada donde tocaba |
| **No es texto: es un ZIP** | 1 | `chunkedhtml` | pandoc entrega `PK\x03\x04`. Llamarlo «banner» fue un error de lectura del censo |
| **Sí es el banner del escritor** | 5 | `obj`, `objnomtl`, `pbrt`, `pov`, `ftxt` | **`EXT_SIN_FIRMA` con el motivo escrito** → `no_aplica`. Decir «no aplica» es honesto; dejarlo en `sin_vocabulario` decía que era deuda nuestra, y no lo es |

**17 de 17 cerrados, y ninguna muestra nueva escrita.**

**Y de ahí sale una auditoría que nadie había hecho.** Si tres marcadores estaban en
la sonda sin extensión que los aceptara, ¿cuántos más? Se contó: **6 firmas
huérfanas** —`alp`, `gimp_paleta`, `iff`, `rar`, `stl_ascii`, `xfig`—. Tres eran
estas. **Quedan 3, y ninguna es destino declarado por ningún adaptador**, así que no
hay muestra con la que censarlas. En el sentido contrario, **0 inalcanzables**:
ninguna extensión espera un nombre que `firma_real` no sepa producir.

### 4.3 Los 13 del PNG: no son vocabulario, son G6 — MEDIDO

`clipboard data flif histogram inline msl mvg null p7 pocketmod preview sparse vid`.
El motor no reconoció la extensión y devolvió el formato de la entrada, que es la
definición de G6. **5 de los 13 tienen dos escritores** (`histogram`, `msl`, `mvg`,
`null`, `vid`: ImageMagick y GraphicsMagick), y **los dos hacen lo mismo**, lo que
refuerza §3.4: el comportamiento es de la familia, no de una build.

**No se les añade firma, y es lo correcto:** no hay un formato que aprender, hay un
fallo que declarar. Es la misma conclusión que F1 sacó para `.group4`.

### 4.4 Los 56: el `rc` de cada celda dice cuál de los cinco remedios aplica — MEDIDO

El pendiente propone el corpus FATE (**~1 GB**, y una descarga concurrente ya costó
un error de **7,4×** en este proyecto). Antes de pedirlo, se leyó el `rc` que el censo
guardó de cada fallo. **Los códigos de error de ffmpeg son etiquetas de cuatro
caracteres y no dejan lugar a interpretación:**

| Clase (por `rc`) | n | Qué significa | Remedio |
|---|---:|---|---|
| `EINVAL (-22)` | **18** | el codificador **está** y la invocación no cumplía las restricciones | una invocación correcta |
| `AVERROR_ENCODER_NOT_FOUND` | **11** | esta build de ffmpeg **no trae** el codificador | otro motor u otra build |
| «metadato, no formato» | **8** | *«No 8BIM / APP1 / IPTC / color profile data is available»* — **no es un destino de conversión**: es un volcado que solo existe si la ENTRADA lo trae | una entrada con ese metadato |
| sin clasificar (`rc=1` de ImageMagick, `stderr` truncado) | **8** | — | mirarlo a mano |
| `el motor no lo sabe escribir` | **4** | `dzi`, `nia`, `nii` (vips: *«is not a known file format»*), `pml` | otro motor |
| `AVERROR_EXPERIMENTAL` | **3** | `dts`, `mlp`, `thd`: el codificador **está** y pide `-strict -2` | **una bandera** |
| `rc=0` y sin fichero | **2** | `eml`, `oeb`: el motor escribe un **directorio** | tratar el destino como directorio |
| `AVERROR_INVALIDDATA` | **2** | `dv`, `flm` | una entrada compatible |

**FATE cerraría, como mucho, 15 de 56** (los 11 sin codificador + los 4 que el motor
dice que no sabe escribir) **y ni siquiera bien**: FATE es un corpus de ficheros para
**decodificar**, y lo que el censo necesita es una muestra **escrita** con la que
medir el marcador. Una muestra de FATE serviría como muestra, pero sería **n=1 y de
un escritor desconocido**, que es exactamente el sesgo contra el que F1 diseñó el
método de las tres semillas.

**Y 21 de 56 se cierran con una invocación mejor. No lo deduje: los escribí — MEDIDO.**

| Formato | Restricción que faltaba | ¿escrito? | Prefijo común (2 semillas) |
|---|---|:--:|---|
| `h261` | `-s 176x144` | sí (2/2) | **6 B** `00 01 00 16 00 01` |
| `h263` | `-s 176x144` | sí (2/2) | **5 B** `00 00 80 02 08` |
| `dnxhd` | `-s 1920x1080 -b:v 36M -pix_fmt yuv422p` | sí (2/2) | **64 B** `00 00 02 80 01 01 80 A0 …` |
| `dts` | `-strict -2` | sí (2/2) | **20 B** `7F FE 80 01 …` (sync word de DTS) |
| `mlp` | `-strict -2 -ar 48000` | sí (2/2) | 1 B (su sync está en el byte 4) |
| `thd` | `-strict -2 -ar 48000` | sí (2/2) | 1 B (ídem) |

**6 de 6 escritos y 4 de 6 con marcador estable en la primera pasada.** Coste: seis
invocaciones de ffmpeg, segundos. **`dts` y `dnxhd` quedan ya en la tabla**; `h261` y
`h263` tienen marcadores de 3 bytes con ceros y **se publican aquí sin añadirlos**,
para que quien los añada lo haga con su propia prueba de falsos positivos.

**Los 79 (que son 56), acotados con su precio:**

| Remedio | destinos | precio |
|---|---:|---|
| invocación correcta (`EINVAL` + `EXPERIMENTAL` + `INVALIDDATA`) | 23 | **minutos de ffmpeg**, 0 bytes de red. 6 ya probados |
| entrada con el metadato dentro | 8 | construir una entrada con perfil ICC/IPTC/EXIF: **minutos** |
| tratar el destino como directorio | 2 | un cambio de arnés |
| mirar el `stderr` completo | 8 | el censo lo truncó a 400 caracteres: **volver a correr esas 8** |
| **otro motor u otra build de ffmpeg** | **15** | aquí sí: **~1 GB de FATE, o compilar ffmpeg con más codificadores**. **NO lo he descargado.** Es lo único que justifica programarlo aparte, y **es el 27 % de los 56, no el 100 %** |

---

## 5. La restricción que manda: cero falsos positivos

### 5.1 Las 53 del patrón oro — MEDIDO, antes y después

Las 53 **no están versionadas** (195 MB de binarios regenerables). Se regeneraron
**fuera del repositorio** desde las 39 órdenes de `referencia.json` más el convenio de
nombres para las 14 que no tienen orden: **53 de 53 escritas, `rc=0` en las 53, 35
reproducen el `sha256` exacto**, y las 18 que no lo hacen **tienen su mecanismo
sondeado** (no deducido: se corrió la misma orden dos veces en la misma tanda y se
comparó consigo misma).

| Familia | n | Mecanismo de la no reproducibilidad |
|---|---:|---|
| PNG de ImageMagick | 6 | `tEXt date:create/modify/timestamp` con el reloj de pared: **10 bytes cambian entre dos ejecuciones idénticas** |
| PDF de ImageMagick | 5 | `/CreationDate` y `/ModDate` (confirma la trampa 22) |
| Matroska/WebM de ffmpeg | 3 | `SegmentUID` aleatorio: 60 bytes |
| Ogg/Opus de ffmpeg | 2 | número de serie del flujo, aleatorio: 88 bytes |
| TIFF de Ghostscript | 1 | etiqueta `DateTime` |
| `pdfwrite` de Ghostscript | 1 | `/CreationDate`, `/ModDate` y un `/ID` aleatorio; **el tamaño oscila** (3 282/3 284/3 291 B) porque se mueven los desplazamientos del `xref` |

Con ellas, el contrato **y** la fidelidad, con el verificador de HEAD y con el del
árbol de trabajo, sobre **los mismos ficheros**:

| | antes (HEAD) | después |
|---|---|---|
| **Falsos positivos** | **0** | **0** |
| Falsos negativos | 0 | 0 |
| contrato | `ok 39 · aviso 3 · ok_parcial 10 · fallo 1` | **idéntico** |
| fidelidad | `ok 37 · aviso 8 · ok_parcial 8 · fallo 0` | **idéntico** |
| salidas que cambian de veredicto o de reglas | — | **0 de 53** |

El único `fallo` del contrato es el contraejemplo deliberado del patrón oro
(`esperado: "fallo"`), y sigue atrapado.

### 5.2 La prueba ancha local: 345 salidas legítimas — MEDIDO, antes y después

Escritas **una sola vez** y evaluadas **dos**: con el mismo byte a byte, toda
diferencia es del verificador y no del motor (varios de estos formatos no son
deterministas).

| | antes (HEAD) | después |
|---|---:|---:|
| salidas escritas | 345 | 345 (las mismas) |
| **falsos positivos** | **0** | **0** |
| avisos `G6` | 12 | 12 |
| `evaluado` | 245 | **249** |
| `familia` | 9 | **10** |
| `no_aplica` | 60 | **61** |
| `sin_vocabulario` | **31** | **25** |
| celdas que cambian | — | **6** |

Las 6 que cambian, una a una: `pcd` y `pcds` (`mpegaudio` → `pcd`), `pct` y `pict`
(`desconocido` → `pict`), `cip` (`sin_vocabulario` → `familia`) y `ftxt`
(`sin_vocabulario` → `no_aplica`). **Ninguna otra se movió**, incluidas las 12 de G6.

**Satélites observados en vivo (R21):** `imagemagick → .htm` y `→ .html` dejan un
`_map.shtml` y un `.png` en el `cwd`; `ffmpeg → .m3u8` deja el `.ts`;
`imagemagick → .mpc` deja su `.mpc` de caché. **Se escribieron dentro del desechable
y no salieron de ahí.**

### 5.3 El vocabulario, con su tamaño Y con sus elementos — MEDIDO

La trampa 48 pide exactamente esto, así que aquí van las dos cosas:

| Tabla | antes | después | dos elementos de la de después |
|---|---:|---:|---|
| `FIRMAS` | 116 | **121** | `(0, b"\x89PNG\r\n\x1a\n", "png")` … `(0, b"Width: ", "brf")` |
| **`FIRMAS_LARGAS`** | — | **2** | `(522, b"\x00\x11\x02\xff\x0c\x00", "pict")`, `(2048, b"PCD_IPI", "pcd")` — **las dos, que para eso son dos** |
| `MARCAS_FTYP` | 39 | 39 | *(sin cambios)* |
| `MARCAS_TEXTO` | 18 | 18 | *(sin cambios)* |
| `EXT_A_FIRMAS` | 338 | **361** | `".264" → {"flujo_es"}`, `".265" → {"flujo_es"}` |
| `EXT_SIN_FIRMA` | 112 | **117** | `".aai" → "cabecera sin constante"`, `".al" → "muestras PCM crudas"` |
| `EXT_FAMILIA` | 42 | **51** | `".assjson"`, `".assxml"` |
| nombres que `firma_real` puede devolver | 126 | **131** | + `pict`, `pcd`, `rocketbook`, `dts`, `dnxhd` |

---

## 6. La trampa 48, buscada en TODO el paquete — MEDIDO, y con control positivo

El encargo pedía mirar *«si hay más tablas del mismo fichero con ese defecto: nadie
lo ha comprobado»*. Se hizo sobre el **AST** (trampa 42: una prueba estructural que
busca texto no distingue una llamada de una mención) y sobre **ocho módulos**, no uno:
`verificador`, `formatos`, `motores`, `invocacion`, `motor_contenedor`, `huella`,
`grafo`, `nucleo`.

**Resultado: 0 sospechas en los ocho.**

Y **dos controles**, porque un «no detecta nada» sin control no significa nada:

- **Control positivo:** la forma histórica exacta de `EXT_FAMILIA`
  (`for _n in ("csv json yaml …"):` sin `.split()`) **se marca**. Si esta prueba se
  pusiera verde, el cero de arriba dejaría de valer.
- **Control negativo:** `EXT_A_FIRMAS`, que **sí** parte pero **dentro del ayudante
  `_ext`**, **no se marca**. La primera versión del detector la acusaba: hubo que
  enseñarle a **seguir un nivel de llamada**. *Un detector que marca la tabla buena
  es ruido, y el ruido se acaba desactivando.*

Y se comprueba que la fuente **compila** antes de analizarla (trampa 60: el camino de
degradación de un módulo bien escrito es también un camino de falso verde).

---

## 7. La suite

| | antes | después |
|---|---|---|
| `python -m pytest pruebas -q` | `266 passed, 6 skipped` | **`297 passed, 6 skipped, 1 failed`** |

- **+32 pruebas nuevas**, todas en `pruebas/test_firmas_cierre.py`, que es fichero
  mío. Ninguna usa GPU, ni un motor externo, ni la red: los PICT y los PCD se
  fabrican byte a byte a partir del censo, así que son deterministas.
- **La que falla es `pruebas/test_sondeo.py::SelladoDelDisco::test_ningun_motor_disponible_tiene_el_sondeo_caducado`,
  y NO la he tocado.** Es un fichero que no es mío y **la prueba tiene razón**: dice
  `{'doc_calibre': ['contrato'], 'doc_libreoffice': ['contrato'], 'doc_pandoc':
  ['contrato'], 'ffmpeg': ['contrato'], 'imagemagick': ['contrato']}`, que es
  exactamente lo que tiene que decir cuando alguien toca el contrato y no resondea
  (§2.7). **Se cierra resondeando, no editando la prueba ni la huella.**
- **Un aviso honesto:** en una de las pasadas apareció además
  `pruebas/test_hito7.py::CuatroSuperficies::test_v5_conversion_legitima_y_el_punto_5_cubierto`,
  que **pasa en aislado y volvió a pasar en las dos pasadas siguientes**. Ocurrió con
  otro agente escribiendo 864 celdas en Docker en la misma máquina; convierte un PNG
  a WebP por las cuatro superficies —incluido el watcher, que es de reloj— y **no
  toca nada de lo que he cambiado**. Lo dejo escrito como **inestabilidad observada
  bajo carga**, no como regresión: es la clase de cosa que la trampa 38 pide
  registrar aunque se explique sola.

---

## 8. Lo que este informe deja PENDIENTE

1. **El resondeo de las 172 aristas.** Es obligatorio (§2.7) y **no puede cambiar
   ninguna**: los 32 formatos tocados no son ni origen ni destino de ninguna. Exige
   escribir en `filex/sondeo/*.json` y en tres informes que no son míos.
2. **Los 15 de los 56 que sí necesitan otro motor** (`ac4 avs3 bit c2 cavs cvg dzi
   evc lbc nia nii oma pml rcv vc1`). Aquí sí hace falta FATE o una build de ffmpeg
   con más codificadores. **No lo he descargado**, como pedía el encargo.
3. **Los 23 que se cierran con la invocación**, de los que **6 ya están probados**.
   Faltan 17, y `h261`/`h263` tienen su prefijo publicado en §4.4 listo para añadir.
4. **Los 8 `sin clasificar` de los 56**: el censo truncó el `stderr` a 400
   caracteres y no se puede decidir. Volver a correr esas 8 celdas.
5. **`fbxa` tiene n=1 disfrazado de n=2**: las dos muestras del censo pesan 9 157 B
   las dos. Hay que rehacerlas con entradas distintas antes de creerse su prefijo.
6. **Las 3 firmas huérfanas que quedan** (`alp`, `iff`, `rar`): ningún adaptador las
   declara como destino, así que no hay muestra. O se les da entrada, o se retiran de
   la sonda.
7. **`mlp` y `thd` tienen su marcador en un desplazamiento**, no en el byte 0. Son
   candidatos naturales a `FIRMAS_LARGAS`, que ya existe.
8. **Los 11 que siguen en `sin_vocabulario` dentro del contenedor** (§3.6): nueve son
   de la clase «el motor escribió otro formato», que no es una laguna de vocabulario;
   `gm:pdb`, `calibre:pdb` y `gm:shtml` son los tres que F1 dejó con el motivo *«el
   prefijo común medido es la ruta del fichero, no un marcador»* y no se han tocado.
9. **G6 sigue siendo `aviso`**, y ahora con más evidencia de la misma familia
   (§3.4): 48 celdas más, 16 destinos más, **y el segundo motor resultó ser el clon
   del primero**. Un segundo motor de verdad sigue sin aparecer.

---

## 9. Propuestas de trampa para `CLAUDE.md` — **NO APLICADAS**

> **70. Una firma no solo alimenta al punto 1: alimenta al DESPACHADOR, y el falso
> positivo aparece en el otro lado — MEDIDO** (`bench/firmas-cierre.md` §2.2).
> `firmas-contrato.md` §10.3 declaró inofensivo que un `.pcd` se clasificara como
> `mpegaudio` —*«no produce falso positivo: `.pcd` no está en la tabla»*— y el
> contrato completo sobre un `.pcd` legítimo devolvía **`fallo`**: con firma
> `mpegaudio`, `sondear_en_proceso` lo manda a `_mp3` y de ahí sale `G4 fallo:
> duración nula o ilegible`. **Cuando midas el daño de una clasificación equivocada,
> sigue el valor hasta donde se usa, no hasta donde lo miraste.** Es la trampa 58 en
> otro eje: el hecho era cierto y la consecuencia estaba un módulo más allá.

> **71. Un vocabulario censado con UN escritor describe a ese escritor, y la prueba
> ancha que lo comprueba tiene que correr donde están los otros — MEDIDO**
> (ídem §3.1). La prueba ancha de falsos positivos da **0 sobre 345 salidas locales**
> y **4 dentro del contenedor**, con motores que la tabla nunca vio: el mágico de
> VIPS es de **endianness** y la tabla traía media (`08 F2 A6 B6` frente a
> `B6 A6 F2 08`); GraphicsMagick escribe `id=MagickCache` donde ImageMagick escribe
> `id=MagickPixelCache`; su PCX va **sin comprimir** y el predicado exigía RLE. **Y
> el árbitro del triaje no puede ser quien escribió el fichero:** las 17 celdas
> crudas eran 11 falsos positivos y 6 capturas buenas, y solo un testigo externo
> (`magick identify`, `vipsheader`, ida y vuelta) las separa. Corolario del mismo
> sitio: **`--entrypoint timeout` sin `--init` devuelve `rc=125` y cero bytes** en
> `filex-c13`, porque `timeout` queda de PID 1 — y 125 es justo el código de «falló
> `docker run`».

> **72. El `rc` de un fallo de escritura dice CUÁL de los remedios aplica, y
> agruparlos todos bajo «ningún motor lo escribe» compra el remedio más caro —
> MEDIDO** (ídem §4.4). De los 56 destinos que el censo dio por inescribibles, el `rc`
> los separa en cinco clases: **11** `AVERROR_ENCODER_NOT_FOUND` (falta el
> codificador), **3** `AVERROR_EXPERIMENTAL` (basta `-strict -2`), **18** `EINVAL`
> (la invocación no cumplía las restricciones del formato), **8** que **no son
> formatos** sino volcados de metadatos que solo existen si la entrada los trae, y
> **2** en los que el motor escribe un directorio. **El corpus de ~1 GB que proponía
> el pendiente cierra 15 de 56**; 21 se cierran con una bandera o una geometría, y
> **seis se escribieron para probarlo, con marcador estable en cuatro**. Es la trampa
> 25 subida de nivel: *el `rc` no es una pista, es la respuesta*.

> **73. Un marcador corto deja de ser corto si se comprueba contra otra cosa del
> propio fichero, y «este marcador ya lo tenemos» no significa que se use — MEDIDO**
> (ídem §2.5, §4.2). Dos motivos publicados para no cerrar una deuda de firmas se
> caen con el dato que el propio censo guardaba: **3DS** se descartó por *«dos bytes
> que chocan con TIFF»* y su chunk principal **declara la longitud total del
> fichero** (565 y 517 declarados, 565 y 517 en disco: **autovalidante**); **Rocket
> eBook** se descartó por *«marcadores de 2 a 6 bytes»* y su prefijo común es de
> **28**. Y en la otra dirección: **`#FIG `, `GIMP Palette` y `solid ` llevaban en la
> tabla de marcadores desde que se escribió**, con el punto 1 saliendo
> `sin_vocabulario` porque **ninguna extensión los aceptaba**. **Audita las dos
> direcciones de una tabla de despacho**: firmas que nadie acepta (había **6**) y
> extensiones que esperan una firma que la sonda no sabe dar (había **0**).

---

## 10. Reproducir

Todo en `bench/salidas-firmas-cierre/`, con su `MANIFIESTO.md`: **texto, nada
binario**. Los binarios (las 53 regeneradas, las 345 locales, las 864 celdas del
contenedor) viven en un desechable fuera del repositorio y se borran al terminar.

```
python bench/salidas-firmas-cierre/_muestra_pict_pcd.py   <tmp>   # el censo de 3 semillas
python bench/salidas-firmas-cierre/_c37_reproduce.py      <tmp>   # la medida de F1, reproducida
python bench/salidas-firmas-cierre/_c37_coste.py          <tmp>   # el coste, pareado
python bench/salidas-firmas-cierre/_c37_caducidad.py              # 172 aristas, 0 movibles
python bench/salidas-firmas-cierre/_c37_bucles.py                 # la trampa 48, con control
python bench/salidas-firmas-cierre/_c37_deuda12.py                # los 12, con su prefijo
python bench/salidas-firmas-cierre/_c28_censo.py                  # los 86, separados
python bench/salidas-firmas-cierre/_c28_motivos.py                # 56 / 17 / 13
python bench/salidas-firmas-cierre/_c28_banner.py                 # los 17, uno a uno
python bench/salidas-firmas-cierre/_c28_huerfanas.py              # firmas sin extension
python bench/salidas-firmas-cierre/_c28_los56.py                  # los 56, por su rc
python bench/salidas-firmas-cierre/_c28_prueba21.py       <tmp>   # 6 escritos de verdad
python bench/salidas-firmas-cierre/_regenera53.py         <REF53> # el patron oro, fuera del repo
F2_REF53=<REF53> python bench/salidas-firmas-cierre/_regresion_53_f2.py --antes
F2_REF53=<REF53> python bench/salidas-firmas-cierre/_regresion_53_f2.py
                 python bench/salidas-firmas-cierre/_regresion_53_f2.py --diff
python bench/salidas-firmas-cierre/_c37_ancha_local.py    <tmp>   # 345 salidas, antes y despues
python bench/salidas-firmas-cierre/_c30_escribe.py                # 864 celdas en filex-c13
python bench/salidas-firmas-cierre/_vocabulario_f2.py             # las tablas, tamano y elementos
python -m pytest pruebas/test_firmas_cierre.py -q
```

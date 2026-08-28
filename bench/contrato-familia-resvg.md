# La familia de `resvg`, el suelo de V8, G6 y el nivel de familia

**Agente V · rama `integracion-r2` · 28/08/2026**
**Encargo:** C19, C21, C27 y C29 de `ESTADO-Y-REPARTO.md` §3.C.
**Ficheros tocados:** `filex/verificador.py`, `pruebas/test_contrato_v.py` (nuevo).
**Datos crudos:** `bench/salidas-contrato-v/` (todo texto, con `MANIFIESTO.md`).
**Máquina:** Windows 10, 12 núcleos, Python 3.11.9, ffmpeg N-121159, ImageMagick
7.1.2-21 Q16-HDRI, Ghostscript 10.07, contenedor `filex-convertx`. Sin GPU.
**Suite:** `231 passed, 6 skipped, 1 failed` → **`250 passed, 6 skipped, 1 failed`**,
con el mismo único rojo esperado (`test_sondeo.py::SelladoDelDisco`, del agente T).

---

## 0. Lo que sale de aquí, en seis líneas

1. **C19 CERRADO.** El quinto miembro de la familia de `resvg` está fabricado, se
   demuestra que pasaba los cinco puntos del contrato y las quince reglas de
   fidelidad, y lo cierra la regla nueva **A7** con **28,48 dB de margen** por el
   lado del falso positivo y **88,44 dB** por el del falso negativo (§2).
2. **Y A7 tiene un punto ciego MEDIDO que hay que publicar con ella:** por debajo
   de **48 kb/s, Opus colapsa el estéreo a mono** y devuelve el canal silenciado
   **audible**; A7 no dispara. A 32 kb/s falla por **1,03 dB** (§2.5).
3. **C21 CERRADO, y con el suelo REFUTADO tal como se pedía.** Las dos clases se
   solapan **15,66 dB**: no existe un suelo de PSNR que las separe. El mejor
   compromiso medido es **10 dB** — y subirlo a 12, 15 o 18 **atrapa exactamente
   las mismas 12 celdas** y añade **3 falsos positivos** (§3).
4. **C27: NO SE PUEDE SUBIR G6 a `fallo`, y aquí está la lista.** Cuatro falsos
   positivos reproducidos (`vda → icb/vst/tga/vid`) y, de **siete motores**, solo
   ImageMagick produce el fallo que G6 atrapa: **32 de 32 en `magick`, 0 de 41 en
   los otros seis** (§4).
5. **C29 destapó un DEFECTO, no una decisión.** `EXT_FAMILIA` se construía **sin
   `.split()`**: contenía los *caracteres* de la cadena. El nivel de familia era
   **código muerto** — `punto1_estado` no devolvió `familia` ni una vez en las 53
   ni en las 54 del conjunto ancho. Arreglado. Y con la pregunta ya formulable, la
   respuesta es **no**: mueve **3 de 53 (5,7 %)** y son justo las tres que la sonda
   `_datos` verifica **mejor** que la firma (§5).
6. **Y hay una refutación del propio encargo: mi cambio NO caduca la huella.** El
   aviso decía que caducaría el componente `contrato`. **MEDIDO: no lo caduca**
   (`6af6b556299b` antes y después), y eso destapa un hueco de la trampa 32 (§6).

**Cero falsos positivos sobre las 53 del patrón oro, demostrado con la tanda
entera antes y después** (§7). `bench/salidas-referencia/referencia.json` se leyó
y no se tocó.

---

## 1. Método y confinamiento

- Las 53 salidas del patrón oro **no están versionadas** (`MANIFIESTO.md`: 195,4 MB
  retirados). Viven en el árbol principal; el *worktree* las alcanza por **cinco
  uniones de directorio** (`New-Item -ItemType Junction`) sobre
  `bench/salidas-referencia/{audio,datos,imagen,pdf,video}`, que están en
  `.gitignore`. Se leen; no se escriben.
- **Trampa 34 pagada antes de creerse ningún rojo:** el *worktree* traía
  `corpus/` como punteros de LFS (`tipico.png` = 130 B). `git lfs checkout`
  restauró 266 MB del almacén local, sin red, y dejó `tipico.png` en **42 855 B**.
- Todo corre en directorios desechables bajo `%TEMP%`, listados antes y después
  (R21). Ninguna tanda dejó fichero no declarado.
- **Contenedores censados con `docker ps -a`** (trampa 37) antes y después:
  6 antes, 6 después, **cero huérfanos**. No se creó ninguno: solo `docker exec`
  sobre `filex-convertx`, con el tope **dentro** (`timeout -k 5 60`).
- Medianas de **n≥9** para los costes; los veredictos son deterministas y se
  publican como cuenta, no como mediana.

---

## 2. C19 — el quinto miembro de la familia de `resvg`

### 2.1 El caso, y la prueba de que hoy no lo ve nadie — MEDIDO

`bench/contrato-quinto-punto.md` §5 lo dejó escrito y aquí se reproduce antes de
tocar nada (`bench/salidas-contrato-v/c19_antes.json`, generado contra el
verificador de `HEAD`, no contra el del árbol de trabajo):

| Salida | Contrato | Fidelidad | Reglas evaluadas | Quién lo atrapa |
|---|---|---|---|---|
| `bueno.mp3` (control) | `ok_parcial` | `ok` | V5 | — correcto |
| **`malo.mp3`** | `ok_parcial` | **`ok`** | V5 | **NADIE** |
| **`malo.opus`** | `ok_parcial` | **`ok`** | V5 | **NADIE** |
| **`malo.m4a`** | `ok_parcial` | **`ok`** | V5 | **NADIE** |
| `malo.flac` | `ok_parcial` | `fallo` | A4, V5 | **A4** |
| `bueno.flac` (control) | `ok_parcial` | `ok` | A4, V5 | — correcto |
| `atenuado20.mp3` | `ok_parcial` | `ok` | V5 | NADIE |
| `atenuado6.mp3` | `ok_parcial` | `ok` | V5 | NADIE |
| `mono2estereo.mp3` (control) | `ok_parcial` | `ok` | V5 | — correcto |

La entrada es un WAV estéreo de 8,000 s a 44 100 Hz con **dos tonos distintos**,
440 Hz en el izquierdo y 880 Hz en el derecho. Con dos canales iguales el caso
**no existiría**: perder uno no se notaría. El fallo se fabrica con
`-af "pan=stereo|c0=c0|c1=0*c0"`, que es lo que hace un `pan` mal escrito.

**Por qué pasa los cinco puntos, punto por punto:**

1. **firma**: MP3/Opus/M4A válidos, firma correcta para la extensión → `evaluado`.
2. **flujos**: 1 pista de audio en la entrada, 1 en la salida.
3. **propiedades declaradas frente a medidas**: **2 canales, 44 100 Hz, 8,000 s**
   — la cabecera declara exactamente lo que hay, porque el canal derecho *existe*:
   está lleno de ceros. El punto 3 lee la verdad y la verdad es correcta.
4. **pedido frente a obtenido**: no se pidió nada que no se entregara.
5. **escritura**: nada fuera de lo declarado.

Y las quince reglas de fidelidad tampoco: **A4/A5 se retiran en su primera línea**
porque el destino tiene pérdida y **no hay PCM que comparar**. Es la frase exacta
de P3: *«la cobertura depende del DESTINO, no del fallo»* — el mismo error hacia
FLAC sí lo atrapa A4, y aquí queda reproducido en la fila `malo.flac`.

### 2.2 Dónde vive la regla: fidelidad, no contrato — DECIDIDO CON NÚMERO

La formulación de `contrato-quinto-punto.md` §4.4 decide sola: *el contrato atrapa
la pérdida cuando el contenido perdido está **declarado en metadatos**; necesita
fidelidad cuando el contenido solo existe como **píxeles o muestras**.* La energía
de un canal **no está en ninguna cabecera** de MP3, Opus ni AAC: solo existe como
muestras, y para leerla hay que decodificar.

Los dos números que lo cierran:

| | Coste (mediana n=9) |
|---|---:|
| Contrato de cinco puntos sobre una salida de audio | **~0,37 ms** (cifra de `verificador-fidelidad.md` §3.1) |
| `ffmpeg -af astats` sobre un WAV estéreo de 8 s | **69,85 ms** |
| `ffmpeg -af astats` sobre el MP3 de 8 s | **54,34 ms** |
| `ffmpeg -af astats` sobre el audio de `tipico.mp4` | **73,40 ms** |
| **A7 completa (dos sondas: entrada y salida)** | **≈ 110–147 ms** |

Meterla en el contrato lo multiplicaría por **300–400**. Es el mismo orden de
magnitud que llevó a I9 a fidelidad (×75–5 700) y a A4/A5, que ya usan `ffmpeg`.
Y del lado del régimen: **no hay opción en proceso** — leer energía por canal en
proceso exigiría un decodificador de MP3/AAC/Opus, que es exactamente lo que este
verificador de 5 241 líneas de biblioteca estándar no tiene ni quiere tener. La
regla de los dos regímenes (*cabeceras en proceso; a partir de ~0,1 Mpx, la sonda
externa*) aquí no se aplica: no hay cabecera que leer.

**A7 vive en fidelidad, grupo C.** Se declara con `measure_overall=none` y solo las
dos medidas que usa (`Peak_level+RMS_level`), que es lo que la abarata.

### 2.3 Los dos umbrales: 136 celdas legítimas, cero puestos a ojo — MEDIDO

La regla es **«un canal que llevaba señal sale MUDO»**, no «un canal baja X dB».
La diferencia la decidió la medida, y se explica en §2.4.

```
A7 fallo  ⇔  RMS_entrada(canal i) > −60 dBFS   Y   RMS_salida(canal i) ≤ −80 dBFS
```

Tres tandas, con la entrada VARIADA a propósito (el tercer sesgo de `CLAUDE.md`
§3, el de la SEMILLA): 17 salidas de audio del patrón oro, 28 recodificaciones
deliberadamente brutales de cuatro fuentes, y 45 celdas con fuentes estéreo de
**canales desiguales**, que es donde el estéreo conjunto puede mover la energía de
un canal y no del otro.

| Clase | Celdas (canal × salida) | Peor nivel de salida de un canal audible |
|---|---:|---:|
| **Legítimas** (patrón oro + agresivas + desiguales) | **132** | **−51,52 dBFS** (`desigual30dB` + `mp3 8k`, canal 2) |
| **Fallo de C19** | **4** | −271,31 / −168,44 / −inf / −inf dBFS |

**Márgenes:**

- Al umbral de silencio (−80 dBFS): **28,48 dB** por encima del peor legítimo y
  **88,44 dB** por debajo del mejor de los cuatro fallos.
- El umbral de *audible* (−60 dBFS) no es decorativo. **A −100 dBFS aparece un
  falso positivo real**: `mp3 -q:a 9` convierte un canal de **−91,57 dBFS** en
  **−inf**, y es legítimo — un códec con pérdida tirando algo inaudible. El −60
  deja **31,57 dB** de margen contra ese caso.

Sobre el patrón oro, las 17 salidas con audio dan una **caída máxima de 0,26 dB**
en cualquier canal. No hay ni asomo de riesgo.

### 2.4 REFUTADO: el segundo escalón de A7 (caída asimétrica) es imposible — MEDIDO

La primera tanda dejaba una tentación: además del silencio, avisar cuando un canal
cae mucho más que el otro. `atenuado20.mp3` (canal derecho a −20 dB) da **20,00 dB
de asimetría** y hoy no lo ve nadie. Con **una** medida legítima en contra
(`lowpass=500`, 8,23 dB) el umbral parecía caber en medio.

**Con la entrada variada, se cae.** Opus a tasa baja **colapsa el estéreo a mono**,
y eso es una conversión perfectamente legítima:

| Fuente | Códec | RMS entrada | RMS salida | Asimetría |
|---|---|---|---|---:|
| `desigual12dB` | opus 8k | −21,07 / −33,07 | −27,12 / −27,12 | **12,00 dB** |
| `desigual30dB` | opus 8k | −21,07 / −51,08 | −27,80 / −27,80 | **30,01 dB** |
| `derecho_-70dB` | opus 8k | −21,07 / −91,57 | −27,42 / −27,42 | **70,50 dB** |

El canal flojo **sube 64 dB**. Cualquier umbral de asimetría por debajo de 70,50 dB
marca como sospechosa una conversión buena, y por encima ya no atrapa los 20,00 dB
del canal atenuado. **No hay hueco.**

**Consecuencia publicada:** un canal **atenuado pero no mudo** no es distinguible
de un Opus a tasa baja, y A7 no lo intenta. `atenuado20.mp3` y `atenuado6.mp3`
siguen sin atrapar a nadie, y eso está medido, no ignorado.

*(Y refuerza el escalón que sí existe: el criterio tenía que ser el SILENCIO, no
la caída. La medida lo eligió por mí.)*

### 2.5 El punto ciego de A7, sondeado en ejecución — MEDIDO

Si Opus a 8 kb/s hace audible un canal de −91 dBFS, ¿qué le hace a un canal
*exactamente* silenciado? No se deduce: se sondea (nueve celdas, el mismo canal
derecho silenciado hacia Opus a nueve tasas).

| Tasa | RMS de salida | ¿A7 dispara? |
|---|---|---|
| 6k | −27,43 / −27,43 | **NO — punto ciego** |
| 8k | −27,47 / −27,47 | **NO** |
| 12k | −27,13 / −27,13 | **NO** |
| 16k | −27,18 / −27,18 | **NO** |
| 24k | −21,52 / −47,28 | **NO** |
| 32k | −21,07 / **−78,97** | **NO — por 1,03 dB** |
| 48k | −21,09 / −168,26 | sí |
| 64k | −21,06 / −168,29 | sí |
| 96k | −21,07 / −168,44 | sí |

**Por debajo de 48 kb/s, Opus rellena el canal mudo con una copia del otro y A7 no
puede verlo.** No es un defecto de la regla: el fichero de salida **ya no tiene el
canal mudo**, tiene dos canales con señal. A esa tasa Opus está inventando el
canal, no conservándolo.

**Y el caso de 32 kb/s es la razón de no tocar el umbral.** Falla por **1,03 dB**.
Bajar el silencio a −70 dBFS lo atraparía y dejaría el margen legítimo en 18,48 dB
en vez de 28,48. **Un umbral movido para atrapar una celda que falla por 1 dB es
un umbral ajustado a esa celda**, que es justo lo que este proyecto llama poner un
suelo a ojo. Se queda en −80 y el punto ciego se publica.

### 2.6 El resultado, y lo que no cambia

`bench/salidas-contrato-v/c19_despues.json`:

| Salida | Contrato | Fidelidad antes | Fidelidad **después** |
|---|---|---|---|
| `bueno.mp3` | `ok_parcial` | `ok` | `ok` (A7 cubierta) |
| **`malo.mp3`** | `ok_parcial` | `ok` | **`fallo` (A7)** |
| **`malo.opus`** | `ok_parcial` | `ok` | **`fallo` (A7)** |
| **`malo.m4a`** | `ok_parcial` | `ok` | **`fallo` (A7)** |
| `malo.flac` | `ok_parcial` | `fallo` (A4) | `fallo` (A7 **y** A4) |
| `bueno.flac` | `ok_parcial` | `ok` | `ok` |
| `atenuado20/6.mp3` | `ok_parcial` | `ok` | `ok` (§2.4) |
| `mono2estereo.mp3` | `ok_parcial` | `ok` | `ok_parcial` (A7 **no cubierta**) |

Esa última fila es deliberada: cuando el número de canales cambia (1 → 2), A7 **no
se declara aprobada, se declara no cubierta**. Cambiar el número de canales es una
propiedad *declarada* y la juzga el punto 3 del contrato en microsegundos; A7 no la
duplica. Lo mismo cuando el pedido trae `canales`, `mezclar`, `volumen`,
`recortar` o un filtro: A7 se retira con un hallazgo `informativo` y
`cobertura: False`. Es la disciplina de A4/A5 con `sample_rate`.

**Sobre las 53 del patrón oro A7 se evalúa en 17 salidas, las 17 con cobertura
`True`, cero avisos y cero fallos.**

---

## 3. C21 — el suelo duro de V8, y la refutación que trajo

### 3.1 Lo que se pedía

*Un vídeo enteramente negro sale con 5,39 dB y severidad `aviso`. 5,39 dB no es una
recodificación agresiva: es otra imagen.* El precedente existe: I7 lleva un suelo
de 20 dB desde `verificador-fidelidad.md` §2.3.

### 3.2 La calibración: 48 celdas fabricadas + las 6 del patrón oro — MEDIDO

Tres fuentes (`trivial.mp4` 640×360 sintético, `tipico.mp4` 1920×1080,
`patologico_2pistas.mkv`), nueve recodificaciones **legítimas** todo lo agresivas
que los codificadores permiten, y cinco formas **patológicas** de que el envase
sea correcto y el contenido no tenga nada que ver.

| Clase | n | Mínimo | Máximo |
|---|---:|---:|---:|
| Legítima, **sin filtro declarado** (x264 crf 51 / 20 k, x265 crf 51, VP9 crf 63 / 20 k, MPEG-4 q31, MPEG-1 50 k) | 21 | **19,84 dB** (`tipico.mp4` → x264 20 k) | 37,05 dB |
| Legítima, **con filtro declarado** (`format=gray`, `format=gray,eq=contrast=40`) | 6 | **10,10 dB** (`2pistas.mkv` → gris + contraste) | 46,84 dB |
| Patológica **sin el congelado** (negro, blanco, ruido, negativo) | 12 | 5,13 dB | **8,88 dB** (ruido) |
| Patológica: **vídeo congelado** | 3 | **22,78 dB** | **25,76 dB** |
| **Patrón oro** (las 6 salidas con vídeo) | 6 | **29,63 dB** (`trivial_mp4-to.webm`) | ∞ (dos remux exactos) |

El negro reproduce el 5,39 dB de P3 al centésimo: **5,385942 dB** sobre
`trivial.mp4`.

### 3.3 REFUTADO: no existe un suelo que separe las dos clases — MEDIDO

Las dos clases **se solapan sobre 15,66 dB**: legítimas de 10,10 a 46,84 dB;
patológicas de 5,13 a 25,76 dB.

- Por arriba, **el vídeo CONGELADO (22,78–25,76 dB) cae dentro del rango legítimo
  y por encima de siete recodificaciones buenas.** Ningún umbral de PSNR lo
  separa. El suelo cierra **cuatro de las cinco** formas patológicas, no cinco.
- Por abajo, **una conversión a gris con contraste da 10,10 dB**, por debajo de
  cualquier suelo «redondo» que uno pondría a ojo.

### 3.4 El valor, elegido por su tabla, no por su forma — MEDIDO

| Suelo | Falsos positivos sobre las 21 legítimas sin filtro | Falsos positivos sobre las 6 con filtro | Celdas patológicas atrapadas | Salidas del patrón oro movidas |
|---:|---:|---:|---:|---:|
| **10 dB** | **0** | **0** | **12 de 15** | **0 de 53** |
| 12 dB | 0 | **3** | 12 de 15 | 0 de 53 |
| 15 dB | 0 | **3** | 12 de 15 | 0 de 53 |
| 18 dB | 0 | **3** | 12 de 15 | 0 de 53 |
| 20 dB | **1** (x264 20 k) | 3 | 12 de 15 | 0 de 53 |

**Subir el suelo de 10 a 18 dB atrapa exactamente las mismas 12 celdas y añade 3
falsos positivos.** Comprar cero detección con tres falsos positivos no es un
cambio: es una regresión con mejor pinta. Y este proyecto cuida más los falsos
positivos que los negativos, con 53 salidas buenas que no se pueden marcar.

**`PSNR_SUELO_VIDEO = 10.0`.** Por debajo, V8 pasa de `aviso` a **`fallo`**.

Márgenes publicados, con su salvedad: **1,12 dB** sobre el peor patológico
atrapado (ruido, 8,88 dB) y **0,10 dB** bajo el peor legítimo medido
(`h264_2colores`, 10,10 dB). El segundo margen es fino y hay que decirlo; lo que
lo hace tolerable es que **ese caso necesita un filtro de vídeo que el pedido de
FileX no sabe expresar hoy** — contra lo que FileX puede producir de verdad, el
margen es de **9,84 dB** hasta `x264 -b:v 20k`, y de **19,63 dB** hasta el mínimo
del patrón oro.

### 3.5 Lo que sigue abierto

- **El vídeo congelado no lo atrapa el PSNR.** Lo atraparía comparar el hash por
  fotograma de la salida **consigo misma** (todos los fotogramas iguales) — es una
  regla nueva, no un umbral. **PENDIENTE, sin medir.**
- El suelo está calibrado con **tres fuentes** y siete codificadores. No cubre AV1,
  ni HDR, ni vídeo entrelazado.

---

## 4. C27 — G6 NO se puede subir a `fallo`, y estos son los casos

### 4.1 Primera refutación, y es del propio enunciado — MEDIDO

C27 nombra dos riesgos: *«que no marque conversiones legítimas entre formatos
equivalentes (`png` → `apng`, `mkv` → `mka`)»*. **Ninguno de los dos puede
disparar G6, y no hace falta convertir nada para saberlo:** G6 exige, como primera
condición, que la extensión de destino **no esté en `EXT_A_FIRMAS`**, y las dos
están:

| Extensión | Estado | Firmas admisibles |
|---|---|---|
| `.apng` | `EXT_A_FIRMAS` | `png` |
| `.mka` | `EXT_A_FIRMAS` | `matroska` |

Comprobado además convirtiendo: `png → apng` y `mkv → mka` con `G6 = False`, junto
con otras **doce** conversiones legítimas entre formatos equivalentes
(`mkv → webm`, `mp4 → mov`, `mp4 → m4a`, `jpg → jfif`, `tif → tiff`,
`flac → oga`, `png → tga/vda/icb/vst`, `png → g4`, `png → bgr`). **G6 dispara 0
de 14.**

*(Dos apuntes honestos de esa tanda, que no son de G6: `png → apng` sale `fallo`
por **I4** — `magick` escribe el APNG a 8 bits desde un PNG de 16, que es una
degradación de profundidad real y no pedida; y tres filas salen `fallo` por V3/V7
porque mi arnés pidió `-vn`/`-map 0:v:0` sin declararlo en el pedido. Ninguna es
un falso positivo del verificador.)*

### 4.2 Dónde SÍ se equivoca G6: los alias sin marcador — 4 falsos positivos MEDIDOS

`firmas-contrato.md` §5.4 lo había anticipado (*«`pcds → pcd` y `vda → vid` son
conversiones dentro de la misma familia»*). Aquí está reproducido en ejecución:

| Conversión | rc | Firma entrada → salida | G6 | Veredicto |
|---|---:|---|---|---|
| `vda → icb` | 0 | `cur` → `cur` | **dispara** | `aviso` |
| `vda → vst` | 0 | `cur` → `cur` | **dispara** | `aviso` |
| `vda → tga` | 0 | `cur` → `cur` | **dispara** | `aviso` |
| `vda → vid` | 0 | `cur` → `cur` | **dispara** | `aviso` |

Los cuatro son **alias de TGA en ImageMagick**: la conversión es legítima y el
formato del fichero **no cambia por construcción**. Con G6 en `fallo`, las cuatro
serían salidas buenas tiradas a la basura. Y el agravante ya conocido sigue ahí:
la firma que G6 publica es **`cur`**, que está mal — es la colisión TGA/CUR
(`hito3-mudanza.md`, C31).

**El conjunto de riesgo no es una lista a ojo: es exactamente `EXT_SIN_FIRMA` (112
extensiones) más lo que no esté en el vocabulario.** Dentro de él viven varias
familias de alias — TGA (`tga icb vda vst`), CCITT (`g3 g4 fax group4`), píxeles
crudos (`rgb rgba bgr bgra…`), PCM crudo (`s16le sb ub sw…`) — y cualquier
conversión entre dos miembros de la misma familia dispara G6 con razón formal y
sin razón práctica.

### 4.3 Segunda condición: más motores. **No aparece un segundo motor** — MEDIDO

68 celdas, siete motores, cada una con su `rc` registrado (trampa 25):

| Motor | Celdas | Escribieron fichero | **G6 dispara** | Qué hace con una extensión que no reconoce |
|---|---:|---:|---:|---|
| **`magick` (nativo)** | 27 | 27 | **27** | `rc=0` y **entrega el PNG de la entrada** |
| **`magick` (contenedor)** | 5 | 5 | **5** | idéntico |
| `ffmpeg` | 16 | **0** | 0 | `rc=−22`, sin fichero → lo atrapa **G1** |
| `vips` | 5 | **0** | 0 | `rc=1`, sin fichero → **G1** |
| `soffice` | 5 | **0** | 0 | `rc=1`, sin fichero → **G1** |
| `gswin64c` | 5 | **0** | 0 | **`rc=0` y sin fichero** → **G1** («el fichero de salida no existe») |
| `inkscape` | 5 | **0** | 0 | **`rc=0` y sin fichero** → **G1** |
| `pandoc` | 5 | **5** | **0** | escribe **texto**, y `texto` está en `FIRMAS_INDEFINIDAS` |

Los 22 pseudoformatos de `firmas-contrato.md` §7.1 se reproducen **22 de 22**, y
las cinco extensiones inventadas (`.zzz .xyz .formato .dat .out`) — que es el caso
real de un usuario — también: **27 de 27 en ImageMagick**.

**Conclusión: G6 sigue siendo una regla de UN motor.** No porque no se haya
buscado, sino porque los otros seis fallan de una manera que el contrato ya
atrapa: o `rc≠0`, o `rc=0` sin escribir. Dos de ellos (Ghostscript e Inkscape)
devuelven **`rc=0` sin producir nada**, que es un fallo silencioso distinto y ya
cubierto por G1.

**Y hay un punto ciego nuevo, medido:** **pandoc escribe fichero en 5 de 5** con
extensión desconocida y G6 **no puede verlo**, porque su salida es `texto` y
`texto` está en `FIRMAS_INDEFINIDAS`. La guarda que evita falsos positivos en los
contenedores genéricos (`zip`, `isobmff`, `riff`, `cfb`, `texto`) es también la que
ciega a G6 ante toda la familia de markup. **PENDIENTE.**

### 4.4 La decisión

**G6 se queda en `aviso`.** No se cumple ninguna de las dos condiciones que C27
exigía: no hay un segundo motor que produzca el fallo (0 de 41 celdas en seis
motores), y sí hay falsos positivos sobre conversiones legítimas (4 de 4 entre
alias de TGA). *«Si sale que no se puede subir, esa es una respuesta buena
siempre que traiga la lista de los casos que lo impiden»* — la lista es §4.2.

**Lo que sí abre camino, y es medible:** los cuatro falsos positivos comparten una
forma. Si `EXT_SIN_FIRMA` llevara, además del motivo, una **etiqueta de familia**
(`tga`, `ccitt`, `pixeles_crudos`, `pcm`, `markup`), G6 podría callarse cuando
origen y destino son de la misma familia y subir a `fallo` cuando no. Serían ~112
etiquetas sobre una tabla que ya existe. **PENDIENTE, sin medir.**

---

## 5. C29 — la pregunta no se podía formular: `EXT_FAMILIA` estaba rota

### 5.1 El defecto — MEDIDO

```python
for _n in ("csv json yaml yml toml txt text md markdown tab tsv srt lrc sub scc "
           "jss xml html htm xhtml ... opendocument"):      # ← falta .split()
    EXT_FAMILIA.add("." + _n)
```

Sin `.split()`, el bucle recorre los **caracteres** de la cadena. El resultado real
era:

```
EXT_FAMILIA = {'. ', '.2', '.4', '.5', '.a', '.b', '.c', '.d', '.e', '.f', '.g',
               '.h', '.i', '.j', '.k', '.l', '.m', '.n', '.o', '.p', '.r', '.s',
               '.t', '.u', '.v', '.w', '.x', '.y'}
```

**28 entradas de un carácter.** Y `bench/firmas-contrato.md` §4 publica
«`EXT_FAMILIA`: 28 extensiones de comprobación de familia». **El recuento cuadraba
por casualidad**, porque esa cadena tiene exactamente 28 caracteres distintos. Es
la razón de que nadie lo viera: el número era el correcto y el contenido no.

**Consecuencia, medida sobre dos conjuntos:**

| Conjunto | `punto1 == familia` antes | después |
|---|---:|---:|
| Las 53 del patrón oro | **0** | **3** |
| Conjunto ancho (54 salidas de `g6.json`) | **0** | 0 |

`punto1_estado` **no devolvió `familia` ni una sola vez**, y el hallazgo `G5` —el
que dice *«marcador de FAMILIA, no de formato»*— **no se emitió nunca** desde que
se escribió. El nivel de familia entero, con sus 42 extensiones y su cuarto estado
de cobertura, era código muerto.

*(El vocabulario declarado tampoco eran 28: arreglado, `EXT_FAMILIA` tiene **42**
extensiones. Es una corrección a `firmas-contrato.md` §4, que no es mi fichero.)*

Arreglado con un `.split()`. Comprobado que **ninguna de las 8 extensiones de un
carácter que sí existen** (`.b .c .g .k .m .o .r .y`, píxeles crudos de
ImageMagick) producía un `familia` falso: `punto1_estado` consulta `EXT_A_FIRMAS`
primero y ninguna está ahí, así que salían `no_aplica`, que es lo correcto.

### 5.2 Ya con la pregunta formulable: la respuesta es NO — MEDIDO

Con el censo del punto 5 provisto (si no, las 53 salen ya `ok_parcial` por el
punto 5 y la pregunta no se puede ni plantear):

| | n |
|---|---:|
| Salidas del patrón oro | 53 |
| `punto1 == evaluado` | 50 |
| `punto1 == familia` | **3** |
| **Se moverían de `ok` a `ok_parcial` con la lectura estricta** | **3 (5,7 %)** |

Y las tres son: `patologico_bom_csv-to-normalizado.csv`,
`patologico_bom_csv-to.json` y `tipico_json-to.csv`.

**Ahí está el argumento para no hacerlo.** Las tres son `.csv`/`.json`, y para esos
dos formatos el contrato **no se queda en la firma**: la sonda `_datos` abre el
fichero, lo parsea entero y comprueba cabecera, número de columnas y número de
filas — son las reglas **D1, D2, D4 y D5**, y es justo lo que atrapó al cuarto
miembro de la familia de `resvg` (CSV → JSON con una columna perdida). Degradarlas
a `ok_parcial` diría *«no pude comprobar el formato»* sobre **las tres salidas
mejor verificadas de su categoría**.

El precedente que C29 invoca —*«antes `1_firma` valía `True` en el 100 % de los
ficheros evaluando el 12,4 %»*— es un caso de **mentir por optimismo**. Aplicarlo
aquí sería **mentir por pesimismo**, que es el mismo defecto con el signo cambiado:
el veredicto dejaría de describir lo que se comprobó.

**Decisión: `familia` sigue contando como cobertura del punto 1, y `G5` sigue
siendo `informativo`.** Lo que cambia es que **ahora se emite de verdad**, que es
lo que C29 quería de fondo: que el nivel de familia sea visible.

**Y la formulación que sale de aquí, y que sí es transferible:** *el nivel de
`familia` cuenta como cobertura cuando otra parte del contrato identifica el
formato; no cuenta cuando la firma es lo único que hay.* Sobre las 53 la
distinción no cambia nada (las tres son de datos). Sobre las otras 39 extensiones
de `EXT_FAMILIA` —`.xml`, `.html`, `.srt`, `.gltf`, `.dxf`…— **no hay sonda que las
identifique, y esas sí deberían caer a `ok_parcial`**. Medirlo exige salidas
reales de esos 39 destinos, que este encargo no tiene. **PENDIENTE.**

---

## 6. Refutación del propio encargo: la huella NO caduca — MEDIDO

El aviso 2 del encargo decía: *«Tu trabajo caduca el componente `contrato` de la
huella —`verificador.py` es exactamente ese componente— y está aceptado.»*

**No lo caduca.** Componente `contrato` de los cinco motores sondeados:

| | Almacenado en `filex/sondeo/*.json` | Calculado con mi `verificador.py` |
|---|---|---|
| `contrato` | `6af6b556299b` | **`6af6b556299b`** |

`huella.diferencias()` devuelve `['invocacion']` para los cinco motores, antes y
después de mi cambio. **Cero aristas caducadas por este trabajo.**

**El mecanismo, y por qué es un hueco y no una suerte.** La trampa 32 eligió
hashear *«el AST normalizado del cierre de llamadas de `verificar()`»*, y esa
elección es buena: aísla del ruido de comentarios. Pero mi trabajo tocó tres
sitios, y **ninguno está en ese cierre**:

1. `verificar_fidelidad()` → `fidelidad_audio` → `_a7_energia_por_canal` — otra
   raíz, otro cierre.
2. `fidelidad_video` y la constante `PSNR_SUELO_VIDEO` — ídem.
3. **`EXT_FAMILIA`, que es una TABLA DE DATOS de nivel de módulo.**

El tercero es el que importa. `EXT_FAMILIA` **decide el veredicto del punto 1** —lo
acabo de mover en 3 de las 53 salidas— y el cierre de llamadas **no lo ve**, porque
no es una llamada: es un `set` que `punto1_estado` consulta. Es la trampa 32 un
nivel más abajo:

> **El cierre de llamadas hashea el CÓDIGO que decide, no los DATOS que ese código
> lee.** Cambiar `EXT_A_FIRMAS`, `EXT_FAMILIA`, `EXT_SIN_FIRMA`, `FIRMAS` o
> `MARCAS_FTYP` cambia el veredicto de aristas reales y **no caduca ninguna**.

Y el aviso lo dice sin quererlo: *«ya está caducado por `invocacion`, así que no
cuesta nada extra»*. Esta vez, por casualidad, otra cosa había caducado la huella.
No siempre la habrá.

**Lo he MEDIDO y lo REPORTO; no lo he arreglado** — `filex/huella.py` no es mío y
el encargo lo prohíbe expresamente. Propuesta en §9.

---

## 7. La restricción que manda: cero falsos positivos sobre las 53

`bench/salidas-contrato-v/regresion_53.py` pasa las 53 por el **contrato** y por la
**fidelidad**, con el verificador de `HEAD` (`--antes`) o el del árbol de trabajo,
y compara veredicto a veredicto. `referencia.json` se lee; no se toca.

| | Antes (`HEAD`) | **Después** |
|---|---|---|
| **Falsos positivos** | **0** | **0** |
| Falsos negativos | 0 | 0 |
| Contrato | ok 39 · aviso 3 · ok_parcial 10 · fallo 1 | **idéntico** |
| Fidelidad | ok 37 · aviso 8 · ok_parcial 8 · fallo 0 | **idéntico** |

Los ocho avisos de fidelidad son **los mismos ocho** de `verificador-fidelidad.md`
§5.3 y de `contrato-quinto-punto.md` §7. El único `fallo` es
`2pistas_mkv-to-DEFAULT.mp4`, el contraejemplo deliberado del patrón oro.

**Las únicas tres diferencias en las 53 son de cobertura, no de veredicto:**

```
patologico_bom_csv-to-normalizado.csv   punto1  evaluado -> familia
patologico_bom_csv-to.json              punto1  evaluado -> familia
tipico_json-to.csv                      punto1  evaluado -> familia
```

Son el arreglo de `EXT_FAMILIA` haciéndose visible. **A7 se evalúa en 17 de las 53
con cobertura `True` en las 17 y cero hallazgos de severidad**; el suelo de V8 no
toca ninguna (el mínimo del patrón oro es 29,63 dB, **19,63 dB por encima**).

**Coste.** No publico la diferencia entre los dos totales (50 279 ms y 51 063 ms):
son 784 ms **por debajo del ruido entre configuraciones de la misma tanda**, y la
trampa 36 dice exactamente que eso no es una medida. Lo que sí está medido en
aislamiento es la pieza: A7 son **dos `astats`, 54,34–73,40 ms cada uno**, sobre
las 17 salidas con audio — del orden de **1,9–2,5 s** añadidos a una suite de
~50 s, es decir **~4 %**. El suelo de V8 y el arreglo de `EXT_FAMILIA` cuestan
**cero**: una comparación y una tabla que ya se construía.

---

## 8. El envoltorio de `bench/scripts/`

`bench/scripts/verificador.py` aliasea en `sys.modules`, así que **hay un solo
objeto-módulo**: comprobado, `bench.scripts.verificador is filex.verificador` →
`True`, con `A7` en `REGLAS_FIDELIDAD` y `EXT_FAMILIA` de 42 entradas por las dos
vías. **La API pública no cambia: solo se AÑADEN nombres** (`A7_AUDIBLE_DBFS`,
`A7_SILENCIO_DBFS`, `PSNR_SUELO_VIDEO`, `_ffmpeg_astats`, `_a7_energia_por_canal`,
`_db`, `_dbfs`) y se corrige el contenido de `EXT_FAMILIA`. Nada se quita ni cambia
de firma, así que los 19 arneses de `bench/` siguen importando lo mismo.

**Aviso a quien reejecute arneses viejos:** los `punto1` de destinos `.csv`,
`.json`, `.xml`, `.html`, `.md`, `.txt`, `.srt`… pasan de `evaluado` a `familia`, y
`G5` empieza a aparecer como hallazgo `informativo`. Es la corrección del §5.1, no
una regresión. Ningún veredicto se mueve.

**Ninguna prueba de un fichero ajeno se rompe.** Suite: `250 passed, 6 skipped,
1 failed`, con el único rojo esperado (`test_sondeo.py::SelladoDelDisco::
test_ningun_motor_disponible_tiene_el_sondeo_caducado`, del agente T, intacto).

---

## 9. Pendientes que dejo abiertos

1. **El vídeo CONGELADO no lo atrapa ningún umbral de PSNR** (22,78–25,76 dB,
   dentro del rango legítimo). Haría falta una regla nueva: el hash por fotograma
   de la salida **contra sí misma**. Sin medir.
2. **El punto ciego de A7 con Opus por debajo de 48 kb/s** (§2.5): el códec
   rellena el canal mudo. No hay solución por energía; habría que comparar la
   **correlación** entre canales de entrada y salida. Sin medir.
3. **A7 solo mira la pista de audio 0**, igual que A4/A5. Un fichero con dos
   pistas y la segunda silenciada no lo ve nadie. Sin medir.
4. **G6 y las familias sin marcador** (§4.4): etiquetar `EXT_SIN_FIRMA` con una
   familia permitiría callar los 4 falsos positivos y subir G6 a `fallo` fuera de
   ellas. ~112 etiquetas. Sin medir.
5. **G6 es ciega a todo el markup** porque `texto` está en `FIRMAS_INDEFINIDAS`, y
   pandoc escribe 5 de 5 con extensión desconocida (§4.3). Sin medir.
6. **El nivel de `familia` en las otras 39 extensiones** (§5.2): sobre `.xml`,
   `.html`, `.srt`, `.gltf`… no hay sonda que identifique el formato y **sí**
   deberían caer a `ok_parcial`. Hacen falta salidas reales de esos destinos.
7. **La huella no ve las tablas de datos** (§6). `filex/huella.py` no es mío.
8. **La firma que G6 publica para TGA es `cur`** y está mal (colisión TGA/CUR, ya
   abierta como C31 en `hito3-mudanza.md`). G6 acierta y **publica un nombre
   falso**.
9. **`bench/firmas-contrato.md` §4 necesita una corrección**: `EXT_FAMILIA` no
   tiene 28 extensiones sino 42, y hasta hoy tenía **cero**. No es mi fichero.

---

## 10. Propuestas para `CLAUDE.md` — NO APLICADAS

> Numeradas desde la 48, como pide el encargo. **No las he aplicado yo.**

**48. Un recuento correcto no prueba un contenido correcto, y un `for` sobre una
cadena es la forma más barata de tener las dos cosas a la vez — MEDIDO**
(`bench/contrato-familia-resvg.md` §5.1). `EXT_FAMILIA` se construía con
`for _n in ("csv json yaml …"):` **sin `.split()`**, así que contenía los
*caracteres* de la cadena: `{'. ', '.2', '.4', '.5', '.a', … '.y'}`. El nivel de
familia entero —cuarto estado de cobertura, hallazgo `G5`, 42 extensiones— era
**código muerto**: `punto1_estado` no devolvió `familia` ni una vez en las 53 del
patrón oro ni en las 54 del conjunto ancho. **Y nadie lo vio porque el RECUENTO
cuadraba**: `bench/firmas-contrato.md` §4 publicó «28 extensiones» y la cadena
tiene exactamente 28 caracteres distintos. **Cuando publiques el tamaño de una
tabla, publica también dos elementos de ella**; un `len()` es un control de
integridad muy débil y aquí fue peor que ninguno, porque dio confianza.

**49. El cierre de llamadas de la huella hashea el CÓDIGO que decide, no los DATOS
que ese código lee — MEDIDO** (ídem §6). La trampa 32 eligió el AST normalizado del
cierre de llamadas de `verificar()` y acertó contra el ruido de comentarios, pero
**`EXT_A_FIRMAS`, `EXT_FAMILIA`, `EXT_SIN_FIRMA`, `FIRMAS` y `MARCAS_FTYP` son
tablas de módulo, no llamadas**. Arreglar `EXT_FAMILIA` movió el `punto1` de **3
de las 53 salidas del patrón oro** y **no caducó ni una arista**: el componente
`contrato` seguía en `6af6b556299b` antes y después. **Las tablas que deciden un
veredicto van en la huella, o la huella miente por omisión.**

**50. Cuando calibres un umbral, VARÍA LA ENTRADA antes de creerte el hueco —
MEDIDO** (ídem §2.4). Con una sola fuente estéreo de canales iguales, un escalón de
«caída asimétrica ≥ 12 dB» parecía separar limpiamente un canal atenuado 20 dB de
todo lo legítimo (peor legítimo: 8,23 dB). Con fuentes de canales **desiguales**,
Opus a 8 kb/s **colapsa el estéreo a mono** y produce **70,50 dB de asimetría en
una conversión perfectamente buena**, subiendo el canal flojo 64 dB. No hay hueco,
y el escalón se retiró. Es el tercer sesgo de `CLAUDE.md` §3 —el de la SEMILLA—
aplicado a un umbral en vez de a una firma: **si calibras con una entrada, estás
midiendo tu entrada.**

**51. Un suelo que no atrapa nada nuevo y añade falsos positivos no es un suelo más
seguro: es una regresión con mejor pinta — MEDIDO** (ídem §3.4). El suelo de V8
puesto en 10, 12, 15 o 18 dB atrapa **exactamente las mismas 12 celdas
patológicas**; de 12 en adelante añade **3 falsos positivos**. La intuición
—«pongámoslo generoso, como el de 20 dB de I7»— habría comprado **cero detección
con tres salidas buenas tiradas**. **Antes de elegir un umbral, tabula qué atrapa y
qué rompe en cada valor candidato: casi siempre hay una meseta, y el borde de
abajo de la meseta es la respuesta.** Y el corolario que trajo la misma tanda:
**las dos clases se solapaban 15,66 dB**, así que la pregunta correcta no era
«¿dónde está el suelo?» sino «¿existe?».

**52. `ffmpeg` tiene filtros que generan un flujo INFINITO, y el tope del cliente
no basta — MEDIDO** (ídem §1). `-vf "loop=loop=-1:size=1:start=0"` sin
`-frames:v`/`-t` no termina nunca. `subprocess.run(timeout=…)` mató al cliente y
**el `ffmpeg.exe` siguió vivo 9 minutos** con el fichero abierto; la tanda
siguiente murió con `PermissionError [WinError 32]` al borrar su desechable. Es la
misma forma que el `docker run` de `CLAUDE.md` §3 sobre otro proceso: **el tope
tiene que estar DENTRO de la orden** (`-frames:v N`, `-t D`), no solo alrededor de
ella. Y el censo que lo identificó fue por **línea de órdenes** — trampa 31 al
revés: no sirve para atribuir VRAM, sirve perfectamente para saber de qué
*worktree* salió un proceso colgado.

**53. La cobertura de una regla de fidelidad depende del DESTINO, no del fallo, y
eso es un agujero con nombre — MEDIDO** (ídem §2.1, confirmando
`contrato-quinto-punto.md` §5). El mismo fichero mal convertido —estéreo con un
canal silenciado— sale `fallo` hacia FLAC (A4 compara el PCM) y salía **`ok` hacia
MP3, Opus y AAC**, porque A4/A5 se retiran cuando el destino tiene pérdida. **Antes
de dar por cubierta una familia de fallos, prueba el MISMO fallo contra un destino
con pérdida y contra uno sin pérdida**: si solo lo atrapa uno, lo que tienes es una
regla del destino, no del fallo.

---

## 11. Reproducir

Desde la raíz del proyecto, con las 53 salidas del patrón oro presentes en
`bench/salidas-referencia/{audio,datos,imagen,pdf,video}` (`MANIFIESTO.md` de ese
directorio lleva las 39 órdenes que las regeneran):

```
python bench/salidas-contrato-v/fabricar_c19.py --antes   # C19, estado previo
python bench/salidas-contrato-v/fabricar_c19.py           # C19, con A7
python bench/salidas-contrato-v/calibrar_a7.py            # 54 filas + coste n=9
python bench/salidas-contrato-v/calibrar_a7_asimetria.py  # 45 filas, la refutación
python bench/salidas-contrato-v/a7_margenes.py            # márgenes + punto ciego
python bench/salidas-contrato-v/calibrar_v8.py            # C21, 48 celdas + oro
python bench/salidas-contrato-v/medir_g6.py               # C27, 68 + 18 celdas
python bench/salidas-contrato-v/medir_familia.py          # C29
python bench/salidas-contrato-v/regresion_53.py --antes
python bench/salidas-contrato-v/regresion_53.py
python bench/salidas-contrato-v/regresion_53.py --diff
python -m pytest pruebas/test_contrato_v.py -q            # 19 pruebas
```

`fabricar_c19.py --antes` y `regresion_53.py --antes` cargan el verificador con
`git show HEAD:filex/verificador.py`, así que la tabla del «antes» se regenera
**después** de aplicar el arreglo. Una comparación que no se puede volver a hacer
no es una comparación.

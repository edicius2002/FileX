# El watcher fuera de Windows, el fichero a medias y el desechable que nadie borra

**Agente U · 28/08 · N4, N5 y N14.** Suite: **213 passed, 6 skipped** (venía de
194 + 6; +19 pruebas, cero movimiento en las existentes). Sondeo intacto antes y
después: `{'real': 210, 'nominal': 5}`, `caducados = {}`.

---

## 0. Lo que hay que saber, en siete líneas

1. **En POSIX SÍ hay equivalente de `os.replace(p,p)`, y el hito 7 lo dio por
   inexistente sin mirar.** `/proc/<pid>/fd` acierta los cinco estados por
   **5,6 ms**; `lsof` cuesta **110,6** y `fuser` **40,0**. — §1
2. **Los cerrojos cooperativos no valen aquí, y hace falta control positivo
   para decirlo:** `flock` solo ve al escritor que toma `flock`, y **en tmpfs
   `lockf` no ve al que tiene el `flock`** mientras que en DrvFs sí. La
   semántica **depende del sistema de ficheros**. — §1.1
3. **La observación no cruza Windows↔WSL2 en ninguna dirección**, con control
   positivo en las dos. Un escritor de WSL2 es invisible para el
   `os.replace(p,p)` de Windows. — §1.4
4. **El pendiente del hito 7 queda medio refutado y medio confirmado.** Un WAV
   truncado **no** «se convierte tan ricamente»: las 5 conversiones sobre
   entrada incompleta dieron `fallo`, y lo que las atrapa es la **duración
   DECLARADA**. — §2.3
5. **Y el residuo existe, y es un formato concreto: un MP3 sin cabecera Xing
   truncado al 50 % devuelve `ok`, veredicto `ok`**, con 4,02 s de entrada y
   4,02 s de salida. La variable no es «suma de comprobación»: es **declarada o
   deducida**. — §2.4
6. **Un `taskkill /F` deja un desechable por conversión en vuelo, y en el
   `%TEMP%` de esta máquina hay 978 de ellos con 211,8 MiB.** El barrido los
   quita sabiendo si el dueño vive, **sin preguntar por PID**. — §3
7. **Y el barrido tenía un agujero propio que encontró la primera celda:**
   `cerrojo.directorio()` se llama `filex-destinos` y **empieza por el mismo
   prefijo**. La primera versión lo habría borrado entero. — §3.3

---

## 1. N4 — el cerrojo del watcher en POSIX — **MEDIDO**

El hito 7 dejó escrito, en `filex/watcher.py` y en `hito7-superficies.md` §3.2:

> **En POSIX este cerrojo no existe** —un `rename` sobre un fichero abierto es
> legal— y `_estable_en_disco` devuelve `True` ahí en vez de inventar una
> defensa. **Medirlo en Linux está PENDIENTE**.

La primera mitad es cierta y ahora está medida. **La segunda es falsa**: que el
primitivo de Windows no sirva no significa que no haya ninguno.

Medido en **WSL2 Ubuntu, kernel 6.18.33.2-microsoft-standard-WSL2, Python
3.14.4**, uid 1000. Sonda: `bench/salidas-watcher/sonda_posix.py`;
resultados en `posix_tmpfs.json` (tmpfs) y `posix_drvfs.json` (DrvFs sobre
`/mnt/d`). Tandas etiquetadas `limpia` las dos.

### 1.1 Siete primitivos × cinco estados, sobre tmpfs

| primitivo | A quieto | B escribiendo | C solo lee | D ya cerró | E escribe **con `flock`** |
|---|---|---|---|---|---|
| `os.replace(p,p)` | libre | **libre** | libre | libre | **libre** |
| `open(p,'rb')` | libre | libre | libre | libre | libre |
| `fcntl.flock` | libre | **libre** | libre | libre | **ocupado** |
| `fcntl.lockf` | libre | libre | libre | libre | **libre** |
| `/proc/*/fd` | libre | **ocupado** | **ocupado** | libre | **ocupado** |
| `lsof -t` | libre | ocupado | ocupado | libre | ocupado |
| `fuser` | libre | ocupado | ocupado | libre | ocupado |

Lo verdadero es `ocupado` en B, C y E; `libre` en A y D. **Aciertan los cinco
estados `/proc`, `lsof` y `fuser`. No acierta ninguno de los otros cuatro.**

Tres lecturas:

* **`os.replace(p,p)` da `libre` en los cinco.** Lo que en Windows es *el único
  cerrojo real* aquí no es nada. Confirmado, y ya no por deducción.
* **`flock` es cooperativo, y el control positivo es lo que lo dice.** La
  columna E existe precisamente para eso: sin un escritor que tome el `flock`,
  un «`flock` no detecta nada» significaría *«no funciona»* o *«nadie lo
  usaba»*, y son cosas distintas. Es la tercera lección de la trampa 36.
* **`lockf` no ve al que tiene el `flock`** — en Linux son dos espacios de
  cerrojos independientes — **y en DrvFs sí lo ve** (`posix_drvfs.json`, misma
  fila, `ocupado`). **La semántica de un cerrojo cooperativo depende del
  sistema de ficheros**, que es otra razón para sondear y no deducir.

### 1.2 El coste, y por qué `/proc` y no `lsof`

Mediana de n=11, misma tanda, fichero quieto:

| primitivo | tmpfs | DrvFs (`/mnt/d`) |
|---|---:|---:|
| `os.replace(p,p)` | 0,0034 ms | 1,5855 ms |
| `open(p,'rb')` | 0,0170 ms | 3,4187 ms |
| `fcntl.flock` | 0,0044 ms | 2,5285 ms |
| `fcntl.lockf` | 0,0059 ms | 2,5413 ms |
| **`/proc/*/fd`** | **5,6181 ms** | **7,2105 ms** |
| `lsof -t` | 110,6187 ms | 110,2583 ms |
| `fuser` | 40,0320 ms | 44,4511 ms |

**`/proc` es ×19,7 más barato que `lsof` y ×7,1 que `fuser`**, y además **no
depende de que estén instalados**. Se paga con la comparación en Windows: el
`os.replace(p,p)` cuesta **128–179 µs** (§2.6), así que la defensa POSIX es
**×31–44 más cara** que la de Windows. Se paga una vez por fichero **ya maduro**
—la comprobación va después de `estables` sondeos—, no por sondeo ni por
fichero visto.

### 1.3 Lo que NO cubre — el techo del método

**51 de 96 `/proc/<pid>/fd` son legibles** para este usuario; **45 no**. Un
escritor de **otro usuario** o de `root` es **invisible**, y en Windows
`os.replace(p,p)` los ve a todos. **La defensa POSIX no es equivalente: es
estrictamente más débil**, y esto es el hermano pequeño de la trampa 31 —lo que
no se puede observar no se puede automatizar—.

Y hereda entera la ampliación de la trampa 27 que hizo N-b: **no distingue un
LECTOR de un ESCRITOR**. La columna C lo enseña: un hijo que solo hace
`open(p,'rb')` sale `ocupado` en `/proc`, en `lsof` y en `fuser`. Es un falso
positivo posible y se acepta a sabiendas, con el mismo argumento que allí:
aplazar cuesta un sondeo; convertir a medias cuesta la salida.

### 1.4 El cruce Windows ↔ WSL2 — **con control positivo en las dos direcciones**

P midió que **el candado** no cruza. Esto es otra pregunta —una es de exclusión,
la otra de observación— y no se puede deducir de aquella.
`bench/salidas-watcher/cruce_win.py`, sobre el **mismo fichero** en `/mnt/d`:

| tenedor | quién mira | resultado |
|---|---|---|
| **Windows** | Windows | **`os.replace` → ocupado, WinError 32** ← control positivo |
| **Windows** | WSL2 | **libre en los siete primitivos** |
| **WSL2** | WSL2 | **`/proc`, `lsof`, `fuser` → ocupado** ← control positivo |
| **WSL2** | Windows | **`os.replace` → libre** |

**No cruza en ninguna dirección**, y los dos controles positivos dispararon, así
que los dos «no» significan algo. Corolario que no estaba escrito: **un escritor
de WSL2 es invisible para la mitad de DETECCIÓN de `filex/nucleo.py`** — el
`destino_ocupado_por_un_tercero` que N-b puso para no pisar el fichero de un
tercero **no ve a un tercero que viva en la VM**, aunque el fichero sea el mismo
por `/mnt/c`.

### 1.5 Lo implementado

`filex/watcher.py::_tenedores_posix` + la rama POSIX de `_estable_en_disco`.
Compara por **identidad** (`st_dev` + `st_ino`), no por el texto del enlace, por
lo mismo que `filex/nucleo.py::_identidad_destino`. `FILEX_WATCHER_PROC=0` lo
apaga, para poder medir el antes y el después en la misma tanda.

**El antes y el después, con el mismo escritor y la misma máquina:**

```
CON el arreglo:  proc_con_escritor=ocupado  estable_con_escritor=False
SIN el arreglo:  proc_con_escritor=libre    estable_con_escritor=True
(condicion=True en los dos: el tenedor había abierto el fichero y seguía vivo)
```

Si no se puede mirar —no hay `/proc`, o la variable lo apaga— devuelve `True` y
**no se inventa una defensa**: queda la estabilidad de `stat`, que es lo que
había.

---

## 2. N5 — «fichero incompleto» sin suma de comprobación — **MEDIDO**

El pendiente, con las palabras de `hito7-superficies.md` §3.3:

> Las 5 conversiones incompletas del watcher ingenuo dieron `rc != 0` y veredicto
> `fallo` […] **Pero eso es una propiedad de este par (formato, motor), no una
> garantía**: un CSV o un WAV truncados se convierten tan ricamente.
> **PENDIENTE**: repetir con un formato sin suma de comprobación.

Sondas: `sonda_incompletos.py` → `incompletos.json`; `sonda_residuo.py` →
`residuo.json`. Las dos tandas, `limpia`.

### 2.1 La matriz: qué detecta cada defensa

Tres defensas candidatas sobre tres formatos y varios puntos de truncado. Cada
celda comprueba que el fichero quedó con los bytes que se pidieron
(`condicion_ok`), y todas dieron `True`.

| formato | corte | bytes | **coherencia declarada** | **última línea** | **reposo 0,6 s** |
|---|---|---:|---|---|---|
| wav | 10 % | 70 567 | **incompleto** | no aplica | completo |
| wav | 50 % | 352 839 | **incompleto** | no aplica | completo |
| wav | 90 % | 635 110 | **incompleto** | no aplica | completo |
| wav | todo menos 1 B | 705 677 | **incompleto** | no aplica | completo |
| wav | completo | 705 678 | completo | no aplica | completo |
| png | 10 / 50 / 90 % / −1 B | … | **incompleto** ×4 | no aplica | completo |
| png | completo | 42 855 | completo | no aplica | completo |
| csv | 10 / 50 / 90 % | … | **sin_declaracion** | **incompleto** | completo |
| csv | **50 % + fin de línea** | 71 263 | **sin_declaracion** | **completo** ⚠ | completo |
| csv | todo menos 1 B | 142 470 | sin_declaracion | incompleto | completo |
| csv | completo | 142 471 | sin_declaracion | completo | completo |

Tres conclusiones:

* **La coherencia declarada acierta 8 de 8 truncados y 2 de 2 completos** en los
  formatos que declaran su longitud (RIFF y el trozo `IEND` de PNG). Incluido el
  caso difícil, **un solo byte de menos**.
* **El reposo no detecta NADA.** Es útil —es la defensa (a) del watcher— pero
  contra un fichero truncado que ya no se mueve no dice nada, y por eso hace
  falta la (c).
* **Y hay una fila con ⚠**: un CSV cortado **en un fin de línea** es
  indistinguible de uno completo para las tres defensas. Es el residuo de este
  formato, y era predecible; ahora es un número.

### 2.2 Los falsos positivos — donde una defensa se cae

| caso | ¿completo de verdad? | qué dice la defensa |
|---|---|---|
| WAV completo escrito **a una tubería** (`ffmpeg -f wav pipe:1`) | **sí** | RIFF declara **4 294 967 295** → **`sin_declaracion`** |
| `corpus/datos/patologico_bom.csv` (salto de línea **dentro de comillas**) | **sí** | versión ingenua «contar comas» → **`incompleto`** ❌ · versión con el módulo `csv` → `completo` |
| CSV completo **sin salto de línea final** | **sí** | «última línea» → **`incompleto`** ❌ |

El primero es el que obliga a una cláusula en el código: **el mismo `ffmpeg`
escribe dos cabeceras distintas según si la salida es buscable**. A un fichero no
buscable no puede volver a rellenarle el tamaño y estampa el marcador de relleno.
Sin tratarlo, la defensa marcaría *incompleto* un fichero entero y correcto — y
sería, además, un falso positivo **estructural**, no de una máquina.

Los otros dos son de la defensa de «última línea», y pesan en su descarte.

### 2.3 El extremo a extremo, con el `Vigilante` de verdad

Un WAV de 705 678 B copiado en 16 trozos con una pausa larga de 3,0 s a mitad
—que es el contraejemplo del hito 7—, watcher a 0,3 s de intervalo, destino
`mp3`. Se registra **los bytes que tenía la entrada al atenderla**, no solo el
resultado.

| configuración | conversiones | **sobre entrada incompleta** | ms desperdiciados | aplazadas |
|---|---:|---:|---:|---:|
| ingenua (`estables=1`, sin cerrojo, sin coherencia) | **6** | **5** | 1 422,8 | 0 |
| estabilidad sola (`estables=2`, sin cerrojo, sin coherencia) | **2** | **1** | 123,4 | 0 |
| **`estables=1` + SOLO coherencia** | **1** | **0** | 0,0 | **17** |
| defecto del hito 7 (`estables=2` + cerrojo) | **1** | **0** | 0,0 | 8 (por abierto) |
| **defecto nuevo** (`estables=2` + cerrojo + coherencia) | **1** | **0** | 0,0 | 9 (por abierto) |

*(Salvedad obligatoria: los milisegundos son de esta tanda y el primer testigo de
nivel salió en 699,62 ms contra 32,64 al final — arranque en frío, trampa 7. Las
columnas que se publican como resultado son las discretas: conversiones y
entradas incompletas.)*

Dos cosas:

* **La fila 3 es el hallazgo.** La coherencia declarada **sola**, con la
  configuración más ingenua de estabilidad y **sin cerrojo ninguno**, da lo
  mismo que estabilidad + cerrojo. Importa porque **es la única de las tres
  defensas que vale igual en Windows y en POSIX**, donde la (b) es más débil
  (§1.3).
* **Y las 5 conversiones malas de la fila 1 dieron las 5 `fallo`**, con motivo
  `A1/V1: la duración cambia más de la tolerancia`. **El pendiente predecía lo
  contrario para el WAV, y es falso**: lo que las atrapa no es que ffmpeg
  rechace nada —codifica un WAV truncado sin rechistar— sino que **el RIFF
  declara una duración que la salida ya no tiene**. Es la regla de diseño del
  proyecto funcionando: *el contrato atrapa la pérdida cuando el contenido
  perdido está declarado en metadatos*.

### 2.4 ⚠ EL RESIDUO: el formato cuya longitud se DEDUCE

Si lo que salva al WAV es la declaración, la pregunta correcta no es *«¿tiene
suma de comprobación?»* sino **«¿su longitud está declarada o deducida?»**.
Cuatro entradas al 50 %, `sonda_residuo.py`:

| entrada | coherencia | FileX `ok` | veredicto | dur. entrada | dur. salida |
|---|---|---|---|---:|---:|
| wav → mp3 (RIFF declara) | **incompleto** | `False` | fallo | 4,00 s | — |
| flac → wav (STREAMINFO declara) | sin_declaracion | `False` | fallo | 8,00 s | — |
| mp3 **con Xing** → wav (declara) | sin_declaracion | `False` | fallo | 8,00 s | — |
| **mp3 SIN Xing → wav** | **sin_declaracion** | **`True`** | **`ok`** | **4,02 s** | **4,02 s** |

**Un MP3 sin cabecera Xing truncado a la mitad pasa el contrato entero.** Y no
por descuido de nadie: su duración **se deduce del tamaño del fichero**, así que
el fichero a medias es **coherente consigo mismo** — declara 4,02 s y entrega
4,02 s. No hay nada que no cuadre. Se pierde la mitad del audio y ni la
coherencia declarada, ni el contrato, ni la fidelidad de duración lo ven.

*(El `mp3` del corpus **sí** trae Xing, así que el residuo hubo que fabricarlo:
`ffmpeg … -write_xing 0`. Sin fabricarlo, la conclusión habría sido «no hay
residuo», que es exactamente el sesgo de semilla de `CLAUDE.md` §3.)*

**La familia del residuo, declarada:**

1. Formatos cuya longitud se **deduce** del tamaño: MP3/AAC crudos sin cabecera
   de índice, PCM sin contenedor, y todo flujo concatenable.
2. Formatos que **no declaran nada**: CSV, TSV, texto, NDJSON. Aquí el corte en
   un fin de línea es indetectable por construcción (§2.1). *(En esta máquina el
   CSV no tiene ni un destino: `fx.destinos('csv')` devuelve `[]`, así que el
   watcher ni lo mira. El residuo es real y no es alcanzable **hoy**.)*
3. WAV escritos a una tubería (§2.2): cabecera de relleno, ninguna comprobación.

### 2.5 Lo implementado, y lo que se midió y NO se implementa

**Implementado:** `filex/watcher.py::_coherencia_declarada` (RIFF y PNG) como
tercera defensa, con `--sin-coherencia` para apagarla.

**Descartado con número: la estructura de la última línea del CSV.** Detecta 4
de 5 truncados, pero: (a) cuesta **4,07 ms en 142 KB** porque tiene que parsear
el fichero **entero** para respetar las comillas —es O(n), frente a los 0,06 ms
O(1) de la otra—; (b) da **dos falsos positivos medidos** (§2.2); y (c) se le
escapa justo el corte interesante. **Medir que algo no compensa también es un
resultado.**

**Y una decisión que no estaba en el encargo y hacía falta: la PACIENCIA.** Una
defensa que aplaza es un **veto perpetuo** si no tiene tope: un fichero truncado
de verdad —su escritor murió— no se mueve nunca más, nunca se marca en la
memoria, y el watcher lo re-sondearía para siempre sin atenderlo jamás. Con
`paciencia=3` (por defecto) la defensa **aplaza tres sondeos maduros y luego
deja pasar**; el veredicto lo sigue dando el contrato, que sobre el WAV lo
atrapa. Los contadores `aplazados_incompletos` y `rendidos` separan las dos
cosas en la bitácora.

### 2.6 El coste, sobre el código real (no sobre la copia de la sonda)

Mediana de n=21, misma tanda, `limpia`. `coste_defensas.json`:

| fichero | `_coherencia_declarada` | `_estable_en_disco` | `os.stat` |
|---|---:|---:|---:|
| wav 705 678 B | **60,30 µs** | 128,70 µs | 17,10 µs |
| png 42 855 B | **108,10 µs** | 127,60 µs | 17,70 µs |
| **tif 72 001 016 B** | **58,00 µs** | 179,30 µs | 28,80 µs |
| csv 92 B | 116,10 µs | 154,30 µs | 28,90 µs |

**La coherencia declarada NO depende del tamaño, y el TIFF de 72 MB lo
demuestra: es la celda más barata de las cuatro** (58,0 µs). Lee 64 bytes de
cabecera y 12 de cola. Es **más barata que el cerrojo** que ya estaba, y se paga
una vez por fichero maduro.

---

## 3. N14 — el desechable de R18 que un `taskkill /F` deja sin borrar — **MEDIDO**

### 3.1 Cuánto se deja, y dónde se acumula

**Escena controlada** (`sonda_desechables.py`, `%TEMP%` privado para no tocar el
de otro agente): 5 conversiones del TIFF de 72 MB a `webp`, matadas con
`taskkill /F /T` **dentro de la conversión**. Las 5 celdas válidas —arrancó,
existía el desechable con contenido dentro, y **no llegó a imprimir su línea de
resultado**—:

```
matados 5 · celdas válidas 5 · huérfanos 5 · 1 295 160 B
```

**Uno por conversión en vuelo. Sin límite superior.**

**Y el censo del `%TEMP%` REAL de esta máquina** (`censo_temp.py`, **solo
lectura**, 28/08):

| | |
|---|---:|
| entradas totales en `%TEMP%` | 2 526 |
| **directorios `filex-*`** | **978** |
| **bytes** | **222 041 261 (211,8 MiB)** |
| vacíos / con contenido | 406 / 561 |
| **edad máxima** | **0,20 días** |

Los mayores son 15 lotes de **17 014 670 B** cada uno con un solo `salida.webm`
dentro: **conversiones de vídeo canceladas**. **Casi mil desechables y 212 MiB
en menos de cinco horas de una ronda**, y el reloj no para: entre la primera
medida y la última, 967 → 978.

### 3.2 Quién limpia, y cómo sabe si el dueño vive

`filex/trabajo.py::barrer_huerfanos`, llamado **una vez por proceso** desde
`FileX.__init__`. La liveza se sabe **sin preguntar por PID** (trampa 31): cada
`DirectorioDeTrabajo` toma un `cerrojo.Candado` con el nombre de **su propia
ruta**, y ese candado **lo suelta el sistema operativo** cuando matan al dueño —
que es exactamente el mecanismo que N-b eligió para el cerrojo de destino, y por
el mismo motivo.

| estado del desechable | qué se hace |
|---|---|
| candado **tomado** | nada: el dueño vive |
| candado libre **y su fichero existe** | se borra: el dueño **murió** |
| **sin** fichero de candado | se borra solo si tiene más de **24 h** |

La tercera fila es para un `filex` anterior a esto o uno cuyo candado se degradó.
Es la única que decide por edad, y la edad es holgada a propósito.

**Escena B, con un `filex` vivo en la misma tanda:**

```
mirados 7 · vivos 1 · borrados 6 · 1 295 160 B recuperados · 73,986 ms
el vivo sobrevivió: True
```

**Escena E, control negativo:** con `FILEX_BARRER=0`, el huérfano **sigue ahí**.
Sin esta escena, la B no probaría que quien borra es el barrido.

### 3.3 ⚠ Un agujero propio, encontrado por la primera celda de la sonda

`cerrojo.directorio()` es `%TEMP%/filex-destinos`. **Empieza por `filex-`.** La
primera versión de `barrer_huerfanos` lo trataba como un desechable más, y la
primera celda de la escena A lo cazó porque el arnés informó de su contenido:

```
A 0 ... desechable_en_vuelo=…\filex-destinos
       contenido=['99047760….lock', 'c8d4769b….lock']
```

**Un barrido que se lleva por delante el directorio de candados de toda la
máquina** es la trampa 26 cometida por el propio remedio, sobre el recurso que
lo protege. Cerrado excluyendo **por identidad**, no por nombre, para que quien
mueva `FILEX_CERROJO_DIR` siga protegido. Prueba:
`test_no_toca_el_directorio_de_candados`.

Y un segundo fallo propio, de la misma familia: **`cerrojo.esta_libre()` CREA el
fichero de candado** al tomarlo y soltarlo. Preguntando por el fichero
*después*, el segundo barrido veía *«tenía candado y murió»* donde el primero
veía *«nunca tuvo»* — y **se saltaba la guarda de edad**. Arreglado mirando
antes y deshaciendo el fichero que `esta_libre` deja. Prueba:
`test_dos_barridos_seguidos_no_cambian_la_decision`.

### 3.4 El peligro reproducido — y una premisa MÍA refutada a medias

**Escena C**: un barrido ingenuo (`rmtree` por prefijo, o «por antigüedad» con
la antigüedad a cero — son el mismo barrido) mientras un `filex` convierte:

```
condición reproducida: True (el vivo tenía su desechable con salida.webp dentro)
ficheros arrancados: 0 · directorio borrado: False
el hijo terminó: FIN True ok · produjo el fichero: True
```

**No se llevó nada.** Windows protege el fichero que el motor tiene abierto, y
`rmtree` no puede con el directorio. **La forma fuerte de mi premisa —«un
barrido ingenuo rompe una conversión en curso»— es FALSA en Windows mientras el
motor escribe.**

**Pero no está cerrada, y las dos escenas que faltaban lo dicen**
(`sonda_ventana.py`):

**F — el primitivo aislado, con control positivo en los dos lados:**

| lado | tenedor con el fichero abierto | directorio borrado | fichero borrado |
|---|---|---|---|
| **Windows** | sí (`ABIERTO`, vivo) | **False** | **False** |
| **WSL2** (tenedor y `rm -rf` los dos dentro) | sí (`ABIERTO`, vivo) | **True** | **True** |

**El peligro del barrido ingenuo es un peligro de POSIX mientras el motor
escribe.** En Windows el sistema lo tapa.

**G — la ventana del fichero ya cerrado, que es donde sí muerde en Windows.**
Entre que el motor cierra su salida y `recoger()` la mueve al destino hay un
tramo —el censo del punto 5 y **el contrato entero**— en el que dentro del
desechable **no hay nada abierto**. Se reproduce ese estado exacto (se verifica
con `os.replace` que efectivamente no hay nada abierto) y se lanzan los dos
barridos contra un `filex` **vivo de otro proceso**:

| barrido | nada abierto dentro | sigue el directorio | sigue el fichero | lo que vio el hijo |
|---|---|---|---|---|
| **ingenuo** | True | **False** | **False** | `RESULTADO False False` |
| **bueno** | True | **True** | **True** | `RESULTADO True True` |

**El barrido ingenuo le arranca el suelo a un `filex` vivo también en Windows**;
solo hace falta llegar en el tramo bueno. Y ese tramo no es estrecho: sobre un
ráster grande, el contrato son cientos de milisegundos.

Y el agravante ya medido por el proyecto sigue en pie: si el desechable es el
origen de un *bind mount*, borrarlo por debajo deja a Docker respondiendo *«did
not receive an exit event»* (`hito5-documental.md` §1).

### 3.5 El coste — **medido aislado, no por diferencia** (trampa 36)

Mediana de n=11, misma tanda, `limpia`:

| trozo | mediana |
|---|---:|
| candado de vida: `tomar()` + `soltar()` | **592,6 µs** |
| `mkdtemp` + `rmtree` a secas (la escala del desechable) | 369,9 µs |
| `DirectorioDeTrabajo` completo (con candado) | 1 134,6 µs |
| barrido con **0** desechables | **0,063 ms** |
| barrido con **20** desechables | **16,832 ms** |

De donde: **0,838 ms por desechable mirado**, dominados por el `esta_libre` que
lo toma y lo suelta. Consecuencias que hay que decir:

* **El barrido es proporcional a los desechables que haya, no al `%TEMP%`.** Con
  los **978** de esta máquina costaría **~0,82 s**, una vez por proceso y solo la
  primera vez: después no quedan. En régimen (0 huérfanos) cuesta **0,063 ms**.
* **El candado de vida sube el `DirectorioDeTrabajo` de ~370 a ~1 135 µs.** Sobre
  una conversión de ~250 ms (§2.3) es el **0,45 %**, y hay uno por salto.
  Es el mismo orden que el cerrojo de destino de N-b (1 169,7 µs, 0,319 %).

### 3.6 Lo que este barrido **NO** cubre

1. **No cruza de usuario ni a WSL2.** `%TEMP%` es por usuario, `cerrojo` también.
   Es el mismo límite de `cerrojo-de-maquina.md` §6.1 y §6.2.
2. **No borra los ficheros de candado huérfanos que no son suyos.** Borra el del
   desechable que entierra (seguro incluso en POSIX: un nombre de `mkdtemp` no
   se repite, así que nadie va a volver a tomarlo). Los demás `.lock` de
   `filex-destinos` —los de destinos, ~120 B cada uno— siguen **PENDIENTE**, y no
   son míos.
3. ⚠ **Los 978 huérfanos que hay HOY no los va a barrer nadie hasta mañana**, y
   eso es correcto aunque no lo parezca: los dejó un `filex` **anterior a este
   candado**, así que no tienen fichero de candado y caen en la tercera fila de
   la tabla — la de la edad, 24 h. Es la guarda haciendo su trabajo: desde
   fuera, un desechable sin candado de un `filex` viejo y uno de un `filex` vivo
   cuyo candado se degradó son **indistinguibles**, y el barrido prefiere
   esperar. **El barrido cierra el problema hacia adelante, no hacia atrás**;
   la deuda ya acumulada se va sola en un día, o a mano.
4. **La guarda de 24 h es una suposición sin medir.** Se eligió holgada porque
   el coste de esperar son unos megas y el de equivocarse es la conversión de
   otro. **PENDIENTE**: no hay dato que diga que 24 sea mejor que 1 o que 72.
5. **No hay barrido periódico**, solo al arrancar. Un proceso de vida larga —la
   API, el watcher— acumula sus propios huérfanos si le matan hijos, y no volverá
   a barrer hasta que reinicie. **PENDIENTE**, declarado.
6. **Un desechable de un `filex` que arrancó con `FILEX_BARRER=0` y murió** es
   indistinguible de uno normal: tiene su candado, el candado está libre, se
   barre. Eso está bien. Lo que no se cubre es el revés: **un `filex` vivo cuyo
   candado se degradó** (`cerrojo` sin ninguna de las dos mitades) queda sin
   protección tras 24 h. Es el mismo «nunca se degrada en silencio» de P: el
   aviso existe, pero el barrido no lo lee.

---

## 4. Arneses que midieron otra cosa — la trampa 38, tres veces en un día

Se registra porque es la trampa que este encargo tenía asignada y **cayó tres
veces**, siempre con la misma pinta: un número plausible.

1. **La escena A dio «5 muertes válidas, 2 huérfanos».** No era que el sistema
   limpiara: **cada hijo nuevo barría al anterior** en su propio
   `FileX.__init__`. La defensa funcionando destruía la medida del daño.
   Arreglado lanzando los hijos de la escena A con `FILEX_BARRER=0`.
2. **La escena B dio «6 huérfanos borrados» con `parte.borrados = 0`.** Los había
   borrado el arranque del `filex` vivo, no la llamada que se estaba midiendo.
   Mismo arreglo.
3. **La condición «el hijo imprimió ARRANCA» no es la condición.** Entre ese
   `print` y el `mkdtemp` hay validación de rutas y planificación: matando ahí no
   queda huérfano ninguno, y saldrían ceros que parecen un éxito de la defensa.
   La condición correcta —**y la que se registra en cada celda**— es *«existe un
   desechable nuevo y tiene algo dentro»* (`esperar_desechable`).

Y una **autocorrección de conclusión**, que es lo que más vale: §3.4 refuta la
premisa con la que empecé N14. El barrido ingenuo no rompe una conversión en
Windows **mientras el motor escribe**; hubo que buscar la ventana donde sí
—el fichero ya cerrado— y medirla aparte, y hubo que ir a WSL2 para ver el caso
en el que el peligro es directo.

---

## 5. Las pruebas — y las que fallan sin el arreglo

`pruebas/test_watcher_n.py`, **19 pruebas**, `python -m pytest pruebas/test_watcher_n.py -q`
→ **19 passed en 3,86 s**.

| clase | qué fija |
|---|---|
| `CerrojoPosix` | `os.replace(p,p)` sí sirve en Windows (**control positivo**) · `/proc` ve al escritor y `os.replace` no, **corrida entera dentro de WSL2** con un tenedor que también vive allí · con `FILEX_WATCHER_PROC=0` no se inventa una defensa |
| `CoherenciaDeclarada` | WAV y PNG truncados al 10/50/90 % y a **un byte de menos** · el RIFF de relleno **no** es un incompleto · el CSV devuelve `sin_declaracion`, que no es un aprobado |
| `PacienciaDelWatcher` | **el ANTES**: sin coherencia, el `Vigilante` madura un WAV a medias · con ella lo aplaza · **la paciencia se acaba**: no hay veto perpetuo · un WAV entero no se aplaza |
| `BarridoDeHuerfanos` | borra al muerto · respeta al vivo del mismo proceso **y al de otro proceso** (con la ventana del fichero cerrado, comprobada) · **no toca `filex-destinos`** · la guarda de edad · **dos barridos seguidos deciden lo mismo** · `FILEX_BARRER=0` (control negativo) · `cerrar()` suelta y borra su candado |

**Falla sin el arreglo, comprobado:** `test_proc_ve_al_escritor_y_replace_no`
afirma `estable_con_escritor == False`, y con `FILEX_WATCHER_PROC=0` la misma
sonda devuelve `True` (§1.5). `test_sin_coherencia_madura_un_wav_a_medias` es el
control explícito del antes. Las de `BarridoDeHuerfanos` no existían porque no
existía el barrido.

**Un rojo que fue mío y enseñó algo:** `test_borra_al_muerto` fallaba porque
simulaba al dueño muerto con `tomar()` + `soltar()`, y **`soltar()` borra el
fichero de candado en Windows** — eso simula a un dueño que **terminó bien**. Un
`taskkill /F` no ejecuta `soltar()`: el sistema libera el candado y **el fichero
se queda con su carga dentro**. La simulación buena escribe el fichero a mano.

---

## 6. Resumen de coste

| defensa | dónde | coste | cuándo se paga |
|---|---|---:|---|
| estabilidad de `stat` | las dos | 17–29 µs (`os.stat`) | por fichero y sondeo |
| abierto: `os.replace(p,p)` | Windows | **128–179 µs** | por fichero **maduro** |
| abierto: `/proc/*/fd` | POSIX | **5,6 ms** (tmpfs) · 7,2 (DrvFs) | por fichero **maduro** |
| coherencia declarada | las dos | **58–116 µs, O(1)** | por fichero **maduro** |
| ~~última línea del CSV~~ | — | 4,07 ms / 142 KB, **O(n)** | **descartada** |
| candado de vida del desechable | las dos | **592,6 µs** | por salto |
| barrido de huérfanos | las dos | 0,063 ms vacío · **0,838 ms/desechable** | una vez por proceso |

---

## 7. N12 — **NO EMPEZADO**

La ventana entre la detección y el `move` en `filex/nucleo.py`, que se cerraría
abriendo el destino con `FILE_SHARE_NONE` vía `ctypes`. Era explícitamente lo
último del encargo y N4, N5 y N14 se llevaron el tiempo. **Sigue abierta y
declarada** en `cerrojo-de-maquina.md` §6 punto 3.

Lo único que N4 le añade, y conviene que quede escrito: **esa ventana no es lo
único que le falta a la detección.** §1.4 mide que **un tercero que viva en WSL2
es invisible para `destino_ocupado_por_un_tercero`**, con control positivo. Un
`FILE_SHARE_NONE` cierra la carrera y no cierra ese caso.

---

## 8. Propuestas para `CLAUDE.md` — **NO APLICADAS** (van AL FINAL, desde la 45)

*(T usa desde la 40; estas empiezan en la 45 para no chocar.)*

**45. «No hay equivalente en el otro sistema» es una deducción hasta que se
sondea, y aquí era falsa — MEDIDO** (`bench/watcher-y-desechables.md` §1). El
hito 7 escribió que en POSIX no hay cerrojo porque `os.replace(p,p)` no falla:
lo primero es cierto (5 de 5 estados dan `libre`) y **lo segundo no se sigue**.
`/proc/<pid>/fd` acierta los cinco estados por **5,6 ms**, frente a **110,6** de
`lsof` y **40,0** de `fuser`. Dos corolarios que no se pueden deducir: los
cerrojos **cooperativos** (`flock`, `lockf`) solo ven a quien toma *el mismo*
primitivo —hace falta un escritor de control que lo tome, o el «no detecta nada»
no significa nada—, y **su semántica depende del sistema de ficheros**: en tmpfs
`lockf` **no** ve al que tiene el `flock` y en DrvFs **sí**. Y el techo del
método: **51 de 96 `/proc/<pid>/fd` son legibles**; un escritor de otro usuario
es invisible, así que la defensa POSIX es **estrictamente más débil** que la de
Windows, no equivalente.

**46. Lo que salva a un fichero truncado no es su suma de comprobación: es que
su longitud esté DECLARADA y no DEDUCIDA — MEDIDO** (ídem §2). El pendiente del
hito 7 decía que *«un CSV o un WAV truncados se convierten tan ricamente»*: para
el WAV es **falso** —5 de 5 conversiones sobre entrada incompleta dieron `fallo`
por `A1/V1`, porque el RIFF declara una duración que la salida ya no tiene— y
para el caso general es **cierto, con un ejemplo exacto**: un **MP3 sin cabecera
Xing** truncado al 50 % devuelve `ok`, veredicto `ok`, **4,02 s de entrada y
4,02 s de salida**, porque su duración se deduce del tamaño y el fichero a
medias es coherente consigo mismo. Comparar «declarado en cabecera» con «bytes
en disco» detecta **8 de 8** truncados de WAV/PNG —incluido *un byte de menos*—
por **58–116 µs y O(1)**: el TIFF de 72 MB es la celda más barata. Y dos
matices que cuestan un falso positivo cada uno: **`ffmpeg` escribiendo a una
tubería estampa `0xFFFFFFFF` en el RIFF** de un fichero perfectamente entero, y
la defensa de «última línea» del CSV **se descarta con número** (O(n), 4,07 ms
en 142 KB, dos falsos positivos, y se le escapa justo el corte en fin de línea).
**Una defensa que solo aplaza necesita PACIENCIA**, o es un veto perpetuo sobre
el fichero cuyo escritor murió.

**47. Un barrido de recursos huérfanos tiene que saber si el dueño VIVE, y en
Windows el sistema tapa el fallo justo lo bastante para que no lo veas —
MEDIDO** (ídem §3). Un `taskkill /F` no ejecuta `finally`: deja **un desechable
de R18 por conversión en vuelo**, y el `%TEMP%` de esta máquina llegó a **978
directorios y 211,8 MiB en menos de cinco horas de una ronda**. El barrido sabe
quién vive **sin preguntar por PID** (trampa 31): cada desechable toma un
candado con el nombre de su propia ruta y el sistema lo suelta al matar al
dueño; cuesta **592,6 µs** por desechable y **0,838 ms** por directorio mirado.
**Y el peligro del barrido ingenuo se mide distinto en cada sistema:** con el
motor escribiendo, en Windows `rmtree` **no se lleva nada** (el fichero abierto
lo protege) y en POSIX se lo lleva **todo** —los dos con control positivo—;
**pero en Windows sí muerde en la ventana en la que el motor ya cerró su salida
y `recoger()` aún no la ha movido**, que es todo el contrato: ahí el barrido
ingenuo deja al `filex` vivo sin directorio y sin fichero, y el bueno no.
**Corolario que casi cuesta caro: el prefijo del barrido cazaba a
`cerrojo.directorio()`**, que se llama `filex-destinos` — el remedio habría
borrado el directorio de candados de la máquina entera. **Excluye por identidad,
no por nombre.**

---

## 9. Reproducir

```bash
# Antes que nada, si el corpus son punteros (trampa 34)
git lfs checkout

# N4 — POSIX, dentro de WSL2 (las rutas van en formato /mnt/…)
W=/mnt/d/Work/research/FileX/.claude/worktrees/agent-ae00d82508a52ef45
wsl.exe -e python3 $W/bench/salidas-watcher/sonda_posix.py \
  --origen $W/corpus/imagen/tipico.png --dir /tmp/filex-n4 --etiqueta tmpfs \
  --salida $W/bench/salidas-watcher/posix_tmpfs.json \
  --log    $W/bench/salidas-watcher/logs/posix_tmpfs.log
# (con --dir $W/bench/salidas-watcher/tmp-n4 y --etiqueta drvfs_mnt_d sale posix_drvfs.json)

# N4 — el cruce, desde Windows (PowerShell)
python bench\salidas-watcher\cruce_win.py --origen corpus\imagen\tipico.png ^
  --dir %TEMP%\filex-cruce --salida bench\salidas-watcher\cruce.json ^
  --log bench\salidas-watcher\logs\cruce.log --segundos 30

# N5 — la matriz, los falsos positivos y el extremo a extremo
python bench\salidas-watcher\sonda_incompletos.py --tmp %TEMP%\filex-n5 ^
  --salida bench\salidas-watcher\incompletos.json ^
  --log bench\salidas-watcher\logs\incompletos.log

# N5 — el residuo (fabrica el mp3 sin Xing él mismo)
python bench\salidas-watcher\sonda_residuo.py --tmp %TEMP%\filex-n5r ^
  --salida bench\salidas-watcher\residuo.json ^
  --log bench\salidas-watcher\logs\residuo.log

# N14 — el daño, el barrido y el coste. TEMP PRIVADO: si no, se barren los
# desechables de otro agente. Poner TMP y TEMP antes de lanzar.
set FILEX_TEMP_REAL=%TEMP%
set TMP=%TEMP%\filex-n14-privado
set TEMP=%TMP%
python bench\salidas-watcher\sonda_desechables.py ^
  --entrada corpus\imagen\patologico_16bit.tif --tmp %TMP%\salidas ^
  --salida bench\salidas-watcher\desechables.json ^
  --log bench\salidas-watcher\logs\desechables.log --matados 5 --espera 1.0

# N14 — el primitivo aislado y la ventana del fichero cerrado
python bench\salidas-watcher\sonda_ventana.py --tmp %TEMP%\filex-n14-ventana ^
  --salida bench\salidas-watcher\ventana.json ^
  --log bench\salidas-watcher\logs\ventana.log

# N14 — el censo del %TEMP% real. SOLO LECTURA, no borra nada.
python bench\salidas-watcher\censo_temp.py --salida bench\salidas-watcher\censo_temp.json

# El coste de las defensas, sobre el código real
python bench\salidas-watcher\coste_defensas.py --salida bench\salidas-watcher\coste_defensas.json

# Las pruebas
python -m pytest pruebas/test_watcher_n.py -q      # 19 passed
python -m pytest pruebas/ -q                       # 213 passed, 6 skipped
```

---

## 10. Ficheros

**Código (mío):**

* `filex/watcher.py` — `_tenedores_posix`, la rama POSIX de `_estable_en_disco`,
  `_coherencia_declarada`, la paciencia, `--sin-coherencia`, `--paciencia`.
* `filex/trabajo.py` — `barrer_huerfanos`, `_nombre_candado`, el candado de vida
  del `DirectorioDeTrabajo`.
* `filex/nucleo.py` — la llamada al barrido, una vez por proceso, en el arranque.
* `pruebas/test_watcher_n.py` — 19 pruebas.

**Sondas y arneses** (`bench/salidas-watcher/`): `escritor_lento.py`,
`tenedor.py`, `sonda_posix.py`, `prueba_posix.py`, `cruce_win.py`,
`sonda_incompletos.py`, `sonda_residuo.py`, `hijo_convierte.py`,
`hijo_desechable.py`, `sonda_desechables.py`, `sonda_ventana.py`,
`censo_temp.py`, `coste_defensas.py`.

**Resultados:** `posix_tmpfs.json`, `posix_drvfs.json`, `cruce.json`,
`incompletos.json`, `residuo.json`, `desechables.json`, `ventana.json`,
`censo_temp.json`, `coste_defensas.json`, y `logs/*.log`.

**Nada binario**: 301 610 B en total, todo texto. Los desechables y ficheros
temporales que se generan se borran; el `MANIFIESTO.md` de la carpeta lleva la
orden exacta de cada salida.

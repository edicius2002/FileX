# Cobertura de la FIDELIDAD: las siete funciones pasan de 357 sentencias sin ejecutar a 0

**Carril `cob/fidelidad`** · rama `cob/fidelidad`. Datos, arneses y sondas en
[`bench/salidas-cobertura-fidelidad/`](salidas-cobertura-fidelidad/).

**Intérprete, entorno y estado de la máquina** (trampas 94 y 101, las cuatro
declaraciones): `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe`,
**Python 3.11.9 win32**; `magick` 7.1.2 Q16-HDRI (con RSVG 2.40.20 dentro),
`gswin64c` 10.07 y `ffmpeg` N-121159 presentes, así que **0 pruebas saltadas**;
Docker **no** hace falta aquí; y la máquina tenía **cinco carriles más midiendo
a la vez**. Por eso **no publico ni un tiempo absoluto** (§3): todo lo de abajo
son veredictos deterministas, recuentos de sentencias y presencia/ausencia.

---

## 0. Titular

| Función | Sin ejecutar en la base | Ahora |
|---|---:|---:|
| `_num` | 11 | **0** |
| `svg_textos` | 44 | **0** |
| `png_tinta_cajas` | 71 | **0** |
| `fidelidad_imagen` | 69 | **0** |
| `fidelidad_video` | 74 | **0** |
| `fidelidad_pdf` | 48 | **0** |
| `fidelidad_vectorial` | 40 | **0** |
| **TOTAL** | **357** | **0** |

**MEDIDO** por `bench/salidas-cobertura-fidelidad/delta.py` cruzando la
cobertura base del maestro (517 pruebas sobre `main`) con la que produce
`pruebas/test_cob_fidelidad.py` **por sí solo**: 128 pruebas, `OK`, 0 saltadas.
`_translate_acumulado`, el ayudante nuevo de §5.1, también queda a **0**.

Y el aviso que exige la trampa 48 —*un `len()` es un control de integridad muy
débil*—: al lado del recuento va la lista de las líneas que quedan, que está
**vacía en las siete**, y va el fichero de cobertura entero
(`cobertura.json`) para que cualquiera rehaga la cuenta.

---

## 1. Qué solapa con `cpu/fidelidad-impl` y qué no — MEDIDO

La rama sin fusionar `cpu/fidelidad-impl` (sobre `cpu/fidelidad-crudos`) toca
`filex/verificador.py` en 331 líneas y añade `pruebas/test_fidelidad_crudos.py`
con 11 pruebas. Comparando los **cuerpos de función por AST y por nombre**
(`solape.py`, y por nombre porque los dos árboles insertan en sitios distintos
y las coordenadas no coinciden):

| | funciones tocadas |
|---|---|
| **La rama** | `_ajustar_pedido_crudo`, `_fps_num`, `_pista`, `_pistas_ffprobe`, `_redecodifica_crudo`, `_spec_relectura_pcm`, **`fidelidad_audio`**, **`verificar_fidelidad`** |
| **Yo** | `_translate_acumulado` (nuevo), **`svg_textos`**, **`png_tinta_cajas`**, **`fidelidad_vectorial`** |
| **Intersección** | **∅ — ninguna** |

**Ninguna de mis siete funciones aparece en su diff, y ninguna de las suyas en
el mío.** El reparto es limpio por construcción: su encargo vive en
`fidelidad_audio` y en el despachador `verificar_fidelidad`, y el mío en las
reglas de imagen, vídeo, PDF y vectorial. **Las dos ramas se pueden fusionar
sin resolver un solo conflicto de contenido en estas funciones** —el fichero
sí tendrá conflictos de posición, porque las dos insertan bloques—.

**Lo que sí solapa, y hay que decirlo: la COBERTURA, no el código.** Su
`test_una_conversion_dv_legitima_NO_es_fallo` llama a `verificar_fidelidad`
sobre un `.dv`, que la sonda clasifica `av`, y el despachador manda eso a
`fidelidad_video` y `fidelidad_audio`. Así que **parte de las 74 sentencias de
`fidelidad_video` las ejercitan también sus pruebas**. **Cuánto exactamente es
PENDIENTE**: medirlo exige fusionar las dos ramas y volver a correr `coverage`,
y no lo he hecho porque mi árbol no puede llevar su `verificador.py`.

Lo que **no** puede solapar es el resto: sus 11 pruebas no tocan un SVG, ni un
PNG de paleta, ni un PDF, ni el `.gif` de V9.

Tres cosas de su informe que confirmo desde este lado, porque las he vuelto a
medir por mi cuenta:

* **La huella `contrato` de `main` es `fe41b4d52413299c`**, la misma cifra que
  publica su §2.
* **Ninguna de las siete funciones del carril está en el cierre de llamadas de
  `verificar()`** — `huella.nombres_alcanzados` devuelve 123 nombres y las
  siete dan `False`, antes y después de mis cambios.
* Y por tanto **su conclusión de que la fidelidad no caduca aristas se sostiene
  también con mis dos arreglos dentro**: ver §3.

---

## 2. Qué garantizan estas pruebas, y qué no

`pruebas/test_cob_fidelidad.py`, 128 pruebas en ocho clases:

| Clase | Pruebas | Motor externo |
|---|---:|---|
| `Num` | 5 | ninguno |
| `SvgTextos` | 20 | ninguno |
| `PngTintaCajas` | 26 | ninguno |
| `FidelidadVectorial` | 13 | ninguno |
| `FidelidadVideoV9` | 5 | ninguno (V9 lee 13+3n bytes en proceso) |
| `FidelidadVideoMotor` | 23 | `ffmpeg` + `ffprobe` |
| `FidelidadImagen` | 21 | `magick` |
| `FidelidadPdf` | 15 | `gswin64c` |

**Tres decisiones que cambian lo que las pruebas garantizan, y por eso van
declaradas también aquí y en la cabecera del módulo:**

1. **Los `sonda`/`sonda_ent` se construyen a mano.** Las seis funciones reciben
   los diccionarios de la sonda como parámetro; sondear de verdad mediría
   `sondear()`, que ya cubre `test_contrato_v.py`, y ataría cada celda a un
   fichero concreto del corpus. A mano, cada rama se ataca por su condición.
2. **Los motores se usan de VERDAD en el camino normal** —`magick compare` y
   `magick` para I3/I6/I7/I8, `gs -sDEVICE=txtwrite` para P2/P5/P6/P9,
   `ffmpeg`/`ffprobe` para V2/V5/V6/V8 sobre clips de 64×48 y 5 fotogramas
   generados en el desechable— y **sólo se sustituyen por un doble las ramas
   de error del ayudante**, las que exigen que `ffprobe` devuelva algo
   inservible. Esas pruebas llevan `_con_doble` **en el nombre**, para que se
   vea cuáles son sin leer el cuerpo: son **7 de 128**.
3. **Los guardas miran la CABECERA del activo, no su existencia ni su tamaño**
   (trampa 107). Y aquí hay una autocorrección: mi primera versión usaba
   `os.path.getsize(r) > 4096`, que **saltaba `corpus/imagen/alpha.png` para
   siempre** —pesa 2 780 B— y por tanto habría dejado las cuatro pruebas de I3
   permanentemente en `skipped` sin que nadie lo notara. Lo destapó que la
   pasada imprimiera `skipped 'hace falta corpus/imagen/alpha.png (LFS)'`
   **con el corpus ya descargado**. Un umbral de tamaño no distingue «puntero
   de LFS» de «fichero pequeño»; la cabecera `version https://git-lfs…` sí.

Los topes van **dentro de la orden** (`-frames:v 5`, `-t 1`), no alrededor
(trampa 52). Todo se escribe en un desechable por clase (R18).

---

## 3. La huella: 0 aristas caducadas — MEDIDO

```
contrato ANTES  (main, sin tocar nada):        fe41b4d52413299c
contrato DESPUÉS (con los dos arreglos de §5): fe41b4d52413299c   ← IDÉNTICO
nombres alcanzados por verificar():            123 antes y después
```

`python -m unittest pruebas.test_sondeo` → **48 pruebas, OK**, antes y después.
**Cero aristas caducadas, cero que resondear, cero que resellar.**

Los dos arreglos de §5 **sí cambian comportamiento**, así que además de la
huella hay que mirar quién más pisa esas funciones. Los módulos de prueba que
mencionan `svg_textos`, `png_tinta_cajas`, `fidelidad_vectorial`, `I9` o
`verificar_fidelidad` son **cuatro**, y los tres que no son el mío corren en
verde con los arreglos puestos: `test_sondeo` **48 OK**, `test_contrato_v`
**19 OK**, `test_a7_ciego` **6 OK**. **No he lanzado la suite completa**, y es
deliberado: hay cinco carriles más midiendo en esta máquina y seis suites a la
vez fabrican la carga que pone roja `test_cancelacion_procesos` sin que nadie
toque el código (trampas 101 y 123). **La suite integral la corre quien integre**
— y ése es el sitio donde se acepta un encargo, no el fichero de pruebas que
escribió su propio autor (trampa 98).

`ci/integridad.py` pasa **8 de 9**; la que falla es `informes-registrados`,
porque este informe tiene que citarse en `ESTADO-Y-REPARTO.md`, que es del
maestro y este carril no toca.

Y el motivo estructural, comprobado y no supuesto: `verificar()` no llama a
ninguna de las siete, ni a `_translate_acumulado`. La frontera de la trampa 32
aguanta también para un cambio que **sí** modifica el comportamiento de la
fidelidad — que es lo que ya había medido `cpu/fidelidad-impl` por su lado, y
esto lo reproduce por otra ruta.

---

## 4. El control de discriminación: 37 celdas, 37 discriminan — MEDIDO

**La cobertura es la única métrica de este proyecto que se puede subir sin
medir nada**, así que cada regla lleva su control positivo: se rompe **una
línea** del código objetivo y se comprueba que la prueba se pone **roja**
(trampa 116 — *el control positivo es el sujeto CON el defecto*).

`bench/salidas-cobertura-fidelidad/discriminacion.py` aplica 37 mutaciones de
una línea, corre **sólo** la clase que debería notarlo y registra qué pruebas
caen. **37 de 37 discriminan**; el detalle por celda está en
`discriminacion.json`. Ejemplos del reparto, que es lo interesante:

| Mutación | Pruebas que se ponen rojas |
|---|---|
| `for u in ("px","pt",…)` → `("px",)` | 1 (`test_quita_las_siete_unidades_de_longitud`) |
| `y - 0.75*fs` → `y - 0.50*fs` | 2 |
| `abs(v-fondo) > 64` → `> 200` | 1 |
| `fondo = max(range(256), key=…)` → `fondo = 255` | 1 |
| `if v >= PSNR_MIN_IMAGEN` → `if v >= 0.0` | 4 (las tres excusas de I7 y el aviso) |
| `if v and v != "und" and w != v` → `if False` | 3 (las tres de V5) |
| `tx += _num(piezas[0])` → `tx += 0.0` | 5 |

Tres defensas **del propio arnés**, porque un arnés de A/B tiene más formas de
mentir que el código que mide:

* **Control de IDENTIDAD** (trampa 119): se comprueba que el texto mutado es
  distinto del original **antes** de correr nada, y que el original vuelve
  después. El `git stash push <fichero>` sobre un fichero ya commiteado no hace
  nada, devuelve 0 y no avisa; aquí se restaura con `git checkout -- <fichero>`
  y se **verifica leyendo el fichero**.
* **Control de COMPILACIÓN** (trampa 60): si la mutación deja la fuente sin
  compilar, la celda se marca `nocompila` y **no cuenta**. Un rojo por
  `SyntaxError` no prueba que la prueba mire lo que dice mirar. (Ninguna de las
  37 cayó ahí, pero la comprobación está.)
* **Control de UNICIDAD**: si el texto a sustituir aparece más de una vez en el
  fichero, la celda se marca `ambiguo` y no cuenta.

---

## 5. Tres defectos, dos arreglados y uno documentado

### 5.1 `svg_textos` ignoraba `transform`, y eso hacía que I9 gritara «TEXTO PERDIDO» sobre una rasterización CORRECTA — MEDIDO, ARREGLADO

**El caso mínimo**, con el mismo rasterizador (librsvg 2.40.20 dentro de
ImageMagick, que sí honra `transform`) y el mismo texto en el mismo sitio de la
imagen (`sonda_i9_transform.py`, `sonda_i9_transform.json`):

| Celda | Caja estimada | Tinta en la imagen entera | Veredicto de I9 |
|---|---|---:|---|
| **A** `<text x=110 y=120>` | `[110, 102, 158, 124.8]` | 0,870 % | `informativo` (24,37 % en la caja) |
| **B** `<g transform="translate(100,100)"><text x=10 y=20>` | `[10, 2, 58, 24.8]` | **0,870 %** | **`fallo`: TEXTO PERDIDO** |

**La tinta es la misma al tercer decimal en las dos: el rasterizador pintó el
texto igual de bien.** La única variable es el `transform`, y produce el
veredicto **más fuerte que tiene la regla**, sobre una conversión buena. A es el
control positivo, y hace falta: sin él, «B da fallo» no distinguiría un defecto
del `transform` de un estimador de cajas que simplemente no funciona.

**El arreglo compone las TRASLACIONES y declara no medible todo lo demás.**
Componer traslaciones es **exacto** y conmutativo, así que la caja resultante es
tan buena como la del caso sin `transform` — y eso es comprobable, no una
promesa: **con el arreglo, A y B dan la caja idéntica `[110, 102, 158, 124.8]`
y el mismo `informativo` con 24,37 %**. Para `scale`, `rotate`, `matrix` o
`skew` la caja sería una invención, así que el elemento se cuenta en
`n_no_medibles` y `fidelidad_vectorial` declara `cobertura["I9"] = False` con su
motivo.

**Y ese segundo camino arregla de paso una nota falsa (trampa 44).** Antes, un
SVG cuyos `<text>` llevaran un `rotate` caía en la rama *«el SVG de origen no
tiene elementos <text>: la regla no aplica»* —que es **falso**, sí los tiene— y
**dejaba `cobertura` vacía**, es decir la regla contaba como aprobada. Ahora
dice qué pasa y se declara NO CUBIERTA, que es la disciplina que este
verificador ya aplica en todas partes: *una regla que no se pudo evaluar no
cuenta como aprobada*.

**Lo que el arreglo NO hace, y por qué**: no implementa `scale`/`rotate`/
`matrix`. Eso es una función nueva, no una corrección de cobertura, y habría que
medirla contra un rasterizador para cada tipo de transformación. Queda
**PENDIENTE**. El riesgo de la elección conservadora está declarado: si algún
día un SVG que resvg mutila lleva un `rotate`, I9 pasará de detectarlo a decir
que no puede mirar. Prefiero eso a un `fallo` que no he comprobado, y lo digo
para que quien no esté de acuerdo pueda cambiarlo con este párrafo delante.

### 5.2 V5 empareja las pistas por POSICIÓN: reordenarlas sin perder una etiqueta se declara pérdida — MEDIDO, **NO ARREGLADO**

`fidelidad_video` hace `y = ts[i] if i < len(ts) else None`: compara la pista
`i` de la entrada con la pista `i` de la salida. Reordenar las pistas —que es
lo que hace `ffmpeg` **por defecto** cuando no se pasa `-map 0`— cruza el vídeo
con el audio.

Caso mínimo, con control positivo (`sonda_v5_orden.py`,
`sonda_v5_orden.json`): un `.mkv` con `[0]=audio sin etiquetar, [1]=vídeo con
language=spa y title=Prueba`, contra dos salidas.

| Salida | Conjunto de etiquetas conservado | V5 |
|---|---|---|
| mismo orden (`-map 0`) | **sí** | `informativo`: «las 1 etiquetas de pista se conservan» |
| reordenada (`-map 0:v -map 0:a`) | **sí** | **`aviso`: «se pierden etiquetas de pista: pista 1 language: 'spa' → None; pista 1 title: 'Prueba' → None»** |

**No se ha perdido ninguna etiqueta en ninguno de los dos**: el conjunto de
pares `(language, title)` no vacíos es idéntico en entrada y salida en las dos
filas. Es un falso positivo puro.

**No lo arreglo, y el motivo es de alcance, no de dificultad.** Emparejar por
tipo de pista (`codec_type` más el orden dentro de su tipo) cambiaría el
veredicto de V5 sobre entradas multipista, y **no puedo revalidarlo contra el
patrón oro desde este worktree**: `bench/salidas-referencia/` sólo trae
`MANIFIESTO.md` y `referencia.json` porque las binarias no se versionan
(trampa 89). Cambiar una regla de severidad `aviso` sin poder mirar sus 53
salidas es exactamente lo que este proyecto llama indulgencia.

Lo que sí dejo es **la prueba que fija el comportamiento de hoy**
(`test_V5_empareja_por_POSICION_y_REORDENAR_le_parece_una_perdida`), con el
control de que ninguna etiqueta desapareció y con el motivo escrito dentro: si
alguien arregla el emparejamiento **se pondrá roja, y ahí encontrará por qué**
(trampa 65). Queda **PENDIENTE**.

*Salvedad honesta: FileX invoca `ffmpeg` con `-map 0` explícito por regla de
diseño (§5), así que sus propias conversiones conservan el orden. El falso
positivo aparece cuando la fidelidad juzga una salida que produjo **otro**, que
es justo lo que hace `--solo-fidelidad`.*

### 5.3 `png_tinta_cajas` reventaba con un byte de filtro PNG corrupto — MEDIDO, ARREGLADO

`_desfiltrar_fila` lanza `ValueError("filtro PNG desconocido: %r")` para
cualquier byte fuera de 0-4. `png_tinta_cajas` **no lo capturaba**, así que un
PNG corrupto propagaba la excepción por `fidelidad_vectorial` y tumbaba
`verificar_fidelidad` entera. **La asimetría es lo que lo delata**: esa función
declara con `motivo` las otras siete malformaciones que conoce —no es PNG,
Adam7, sin IDAT, color type fuera de tabla, profundidad fuera de tabla, paleta
sin PLTE, sin cajas— y sólo ésta reventaba. Ahora devuelve
`{"evaluable": False, "motivo": "PNG corrupto: filtro PNG desconocido: 9"}`.

*(Cómo apareció: no lo buscaba. La línea del `raise` era una de las **dos**
sentencias que seguían sin ejecutar en los ayudantes vecinos después de la
primera pasada de cobertura, y preguntarse cómo se llega a ella es lo que
enseñó que se llega **desde fuera**, con un fichero de entrada.)*

---

## 6. Del arnés: un fichero llamado `con.txt` cuelga el proceso para siempre

Vale la pena escribirlo porque costó dos pasadas y no se parece a nada de lo
que uno busca. `test_es_svg_decide_por_CONTENIDO_no_por_extension` escribía un
SVG en un fichero llamado **`con.txt`**. En Windows, **`CON`, `PRN`, `AUX`,
`NUL`, `COM1`–`COM9` y `LPT1`–`LPT9` son nombres de DISPOSITIVO reservados con
cualquier extensión y en cualquier directorio**: `open("…/con.txt", "rb")` abre
la **consola**, y `read()` se queda esperando el teclado.

**El cuadro clínico es exactamente el de un interbloqueo, y ninguna de sus
piezas apunta al sitio bueno:** un hilo, **cero procesos hijos**, **0,45 s de
CPU en diez minutos**, ni un error, ni un `timeout` que salte —porque no hay
subproceso al que ponérselo—. Sobrevivió a la primera pasada disfrazado de «la
máquina está cargada, hay cinco carriles midiendo», que además **era verdad** y
es lo que lo hizo creíble: la trampa 36, una explicación plausible no es un
mecanismo.

Lo que lo destapó fue **la reproducción aislada**: correr sólo esa clase y ver
que se paraba en el mismo test con la máquina tranquila. Con el nombre
cambiado, las 128 pruebas terminan en una fracción de minuto.
El log del cuelgue se conserva en
`bench/salidas-cobertura-fidelidad/cuelgue-dispositivo-CON.log`.

**Regla para los arneses de este repositorio: un nombre de fichero de prueba no
se elige por lo corto.** Y el corolario, que es la trampa 25 una vez más: *«el
proceso está bloqueado»* y *«la máquina va lenta»* tienen la misma pinta desde
fuera, y lo único que los separa es el reloj de CPU del proceso.

---

## 7. Del instrumento: un delta de cobertura por NÚMERO DE LÍNEA compara dos ficheros distintos

La primera versión de `delta.py` mapeaba las líneas ausentes de la cobertura
**base** sobre los rangos de función del fichero **actual**. Funcionó
perfectamente hasta que el arreglo de §5.1 metió 54 líneas en mitad del
fichero; a partir de ahí publicó:

```
TOTAL carril: 299 sin ejecutar -> 209 ganadas (69,9 %), quedan 90
```

Eso **no era una regresión**: era el desfase. La línea 4826 de `main` y la 4826
de ahora no son la misma sentencia, y el número resultante es perfectamente
publicable y perfectamente falso. Es la trampa 62 en otro eje —*pregúntale a tu
instrumento su resolución*— y la 59 en el suyo: **cuando compares dos versiones,
no supongas que sus coordenadas son las mismas.**

`delta.py` compara ahora **por nombre de función**, con cada lado usando el AST
de su propia fuente: la base sale de `git show main:filex/verificador.py` y la
nueva del árbol de trabajo. Lleva dentro un control de integridad —las siete
funciones tienen que aparecer en los dos lados— porque un mapeo por nombre que
no encuentra un nombre devuelve 0 en silencio, que es la trampa 66.

---

## 8. Lo que queda PENDIENTE

1. **`svg_textos` no soporta `scale`, `rotate`, `matrix` ni `skew`** (§5.1). Hoy
   se declaran no medibles, que es honesto y es una pérdida de detección.
2. **V5 empareja por posición** (§5.2). Documentado con prueba, sin arreglar,
   por no poder revalidar contra el patrón oro desde un worktree.
3. **Cuánta cobertura de `fidelidad_video` aporta también
   `cpu/fidelidad-impl`** (§1): exige fusionar las dos ramas y remedir.
4. **`_leer_plte` tiene una línea inalcanzable desde `png_tinta_cajas`**: su
   camino de EOF exige un fichero que `_png_meta` habría rechazado antes con
   «sin IDAT». No está en el carril y no la fuerzo con un doble: decir que una
   línea no se puede alcanzar desde su único llamador vale más que taparla.
5. **`fidelidad_video` propaga el `OSError` de `_paleta_gif`** si el `.gif` de
   salida desaparece entre el sondeo y la regla. `verificar_fidelidad` lo tapa
   hoy con su guarda `not sonda_sal.get("error")`, así que **no he podido
   construir el caso por la vía normal** y no lo arreglo: sería código para un
   problema que no he sabido reproducir (trampa 86).
6. **Estas 128 pruebas no se han corrido en Linux.** La aptitud de un entorno se
   mide EN ese entorno (trampa 104), y `ci/linux-apto.json` es del maestro.
   Aviso concreto para quien lo mida: **las clases `FidelidadImagen`,
   `FidelidadPdf` y `FidelidadVideoMotor` se saltan enteras sin `magick`, `gs` y
   `ffmpeg`**, que es lo que pasa en el runner de GitHub (trampa 110); las cinco
   clases restantes —69 de las 128— no usan ningún motor externo.

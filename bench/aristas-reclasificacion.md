# Reclasificación de los 445 «no materializables» — C49

**Qué contesta.** `bench/aristas-nominales.md` publica que el **54,78 %** de las 138 501
aristas del grafo instalado queda **indeterminado**, y ese estrato cuelga entero de los
**445** formatos que `bench/salidas-aristas/semi_entrada.json` marca `no_materializable`.
La sospecha del encargo era que **una parte de esos 445 no son formatos de fichero** —
generadores, protocolos, dispositivos— y que llamarlos «no materializables» **infla** la
cifra.

**Aquí se comprueba, derivándolo de los metadatos que los propios motores publican** y no
de los nombres. Toda afirmación va marcada **[MEDIDO]** o **[PENDIENTE]**.

- Datos crudos e instrumentos: `bench/salidas-aristas-reclasificacion/` (con su `MANIFIESTO.md`)
- **Máquina consumida: siete listados de metadatos, una vez cada uno.** Ninguna conversión,
  ningún contenedor, ninguna suite, ninguna GPU, ni un fichero del `corpus/` leído. §9.
- **No se ha escrito nada en `bench/salidas-aristas/`**, que es la salida medida de otro
  agente (`CLAUDE.md` §1).

---

## 0. Las tres cifras

> ### 1. La sospecha es **CIERTA y PEQUEÑA**: de los 445, **16** no son ficheros. Los otros **429** están bien clasificados. **[MEDIDO]**
>
> ### 2. El **54,78 % pasa al 53,88 %**: una caída de **0,90 puntos**, no la corrección de bulto que la sospecha sugería. **[MEDIDO]**
>
> ### 3. Y el hallazgo grande está en otro sitio: para **73 de los 445 el MOTIVO es falso** — `ffmpeg -muxers` declara que el binario **sí sabe escribirlos** —, y **54 de esos 73 no se probaron nunca**. Son **12 242 aristas, el 16,13 % del estrato indeterminado**. **[MEDIDO]**

La tercera es la que cambia qué hay que hacer, y **no requiere el corpus FATE de ~1 GB que
`aristas-nominales.md` §7 declara PENDIENTE**: son formatos que ffmpeg escribe.

---

## 1. Antes de tocar nada: cómo decidió el censo (trampa 58)

*«Antes de arreglar una medida ajena, reproduce su medida y sondea su mecanismo: el hecho no
implica la causa.»* El mecanismo está en `bench/salidas-aristas/_semi_in.py`, función
`materializa()`, y es **de tres ramas**: **[MEDIDO]**

1. ¿está en el `corpus/` por extensión? → se usa;
2. ¿el token está en `viva_ff_out`? → se intenta escribirlo con **ffmpeg** desde 4 semillas;
3. ¿está en `viva_im_out`? → se intenta con **magick** desde 2 semillas;
4. si no → `no_materializable`, motivo `"ningún motor local lo escribe"`.

**Dos propiedades de ese mecanismo deciden todo lo que sigue:**

- **`viva_ff_out` y `viva_im_out` NO salen de `-muxers` ni de `-list format`: salen del censo
  de SALIDA** (`semi_salida.json`), que sólo cubrió los **202** destinos que ConvertX declara
  para ffmpeg. Un formato que ffmpeg sabe muxear pero que no está en esos 202 **nunca entra
  en la rama 2**, así que no se intenta y cae al motivo por defecto.
- **Las entradas `no_materializable` guardan sólo `{"estado", "motivo"}`.** Las vivas guardan
  además `procedencia`, `bytes_entrada` e `intentos` con el `rc` de cada celda. Verificado
  sobre el JSON: **[MEDIDO]**

  ```
  claves de una entrada no_materializable: ['estado', 'motivo']
  claves de una entrada viva             : ['bytes_entrada', 'estado', 'intentos', 'procedencia']
  ```

**Y el motivo es literalmente el mismo string en las 445.** Un `Counter` sobre el campo da
**una sola clave**. Es la firma de la trampa 66 —*si una sonda devuelve el mismo valor para
cosas que sabes distintas, la sonda está rota*— con el agravante de que aquí **no hay sonda**:
el campo es una constante escrita en el `return`. **[MEDIDO]**

> **Consecuencia de método, y es el motivo de que este informe use metadatos y no `rc`:** el
> precedente `C28` (`firmas-cierre.md` §4.4) resolvió su reclasificación **leyendo el `rc` de
> cada celda** — *«el `rc` no es una pista, es la respuesta»*. **Esa vía no existe en el lado
> de ENTRADA**, porque para las 445 no se ejecutó nada y no hay `rc` que leer. §7 lo compara
> en detalle.

### 1.1 Reproducción exacta, que es lo que autoriza a seguir

| Cifra | Publicada | Reproducida | |
|---|---:|---:|:--:|
| Formatos censados | 719 | **719** | ✅ |
| `viva` / `no_materializable` / `muerta` | 218 / 445 / 56 | **218 / 445 / 56** | ✅ |
| Aristas del grafo A | 138 501 | **138 501** | ✅ |
| viva / muerta / indeterminada / otro | 40 252 / 22 235 / 75 874 / 140 | **40 252 / 22 235 / 75 874 / 140** | ✅ |

**[MEDIDO]** — `log-recuento.txt`, `log-rehace.txt`.

> **`aristas.json` está podado con su orden, y esa orden estaba prohibida esta ronda**
> (trampa 95: mira el `MANIFIESTO` antes que el disco). Regenerarlo con `_censo.py` relanza
> **~590 sondas `ffmpeg -h demuxer=…`**. No hizo falta: el grafo A es un **producto cartesiano
> de conjuntos declarados**, y los cinco se obtienen sin ejecutar un motor —`ffmpeg.ts` es un
> fichero, `im-format.txt` ya estaba volcado, y `censo.json` publica los conjuntos de
> Ghostscript y Gotenberg—. `rehace_aristas.py` da **138 501 exactas**. **[MEDIDO]**

---

## 2. El criterio: qué metadato decide, motor por motor

**ffmpeg publica cuatro listas SEPARADAS**, y esa separación es el dato: **[MEDIDO]**

| Lista | Entradas | Qué significa estar en ella |
|---|---:|---|
| `-demuxers` | 405 nombres | ffmpeg **lee** ese formato de fichero |
| `-muxers` | 184 nombres | ffmpeg **escribe** ese formato de fichero |
| `-protocols` | 41 de entrada | es un **transporte**, no un formato |
| `-devices` | 5 de entrada | es una **fuente de captura**, no un fichero |

**ImageMagick lo publica en el campo `Module` de `magick -list format`**, que agrupa los
coders y no depende de cómo se llame el formato: **[MEDIDO]**

```
     FILE* URL       r--   Uniform Resource Locator (file://)
      FTP* URL       r--   Uniform Resource Locator (ftp://)
     HTTP* URL       r--   Uniform Resource Locator (http://)
    HTTPS* URL       r--   Uniform Resource Locator (https://)
       XC* XC        r--   Constant image uniform color
   CANVAS* XC        r--   Constant image uniform color
 GRADIENT* GRADIENT  r--   Gradual linear passing from one shade to another
```

Las cuatro primeras comparten **`Module = URL`** y la descripción dice *«Uniform Resource
Locator»*: **el motor declara que son localizadores, no formatos.** `XC` y `GRADIENT` sirven
a dos nombres cada uno, lo que confirma que el agrupador correcto es el módulo y no el nombre.

**Control de sonda (trampa 66), y es de una línea.** Mi parseo tiene que reproducir el del
censo, y dos tokens que sé distintos no pueden salir iguales: **[MEDIDO]**

```
control sonda IM: reproducidas 246, censo 246, difieren NINGUNA
control positivo: png={'modulo':'PNG','modo':'rw-',...'Portable Network Graphics (libpng 1.6.58)'}
                   xc={'modulo':'XC', 'modo':'r--',...'Constant image uniform color'}
```

### 2.1 Lo que el metadato NO decide, y por qué se dice

El `*` del listado de ImageMagick **no marca pseudo-formato**: es `blob_support`
(`ListMagickInfo`), y lo llevan `AAI*` y `PNG` igual que `XC*`. **El modo `r--` tampoco
separa**: lo comparten `XC` (generador) y `ARW` (un fichero de cámara perfectamente real).
**No hay una bandera de «esto no es un fichero»**; lo que hay es el módulo y la descripción,
que son metadatos publicados por el motor pero no una bandera. **Por eso cada miembro de las
clases movidas se publica entero en §3 con su fila cruda: la afirmación es verificable una a
una, no un argumento de autoridad.**

---

## 3. La clasificación de los 445 — [MEDIDO]

Nueve clases, con el metadato que decide cada una. Suman **445**.

| Clase | n | ¿sale de la población? | Metadato que la decide | Ejemplos |
|---|---:|:--:|---|---|
| `ff_solo_demuxer` | **174** | no | en `-demuxers`, **no** en `-muxers` | `3dostr`, `4xm`, `ape`, `concat`, `sdp` |
| `ff_extension_de_demuxer` | **98** | no | no es nombre de demuxer/muxer y **no** está en `censo.muertos_in` → por complemento está en las «Common extensions» de algún demuxer | `302`, `722`, `mka`, `s3m`, `thd` |
| `ff_declarado_muxer` | **73** | no | **está en `-muxers`** → el motivo del censo es **falso** | `dts`, `dnxhd`, `hls`, `rawvideo`, `webvtt` |
| `im_formato_real_solo_lectura` | **65** | no | `-list format` modo `r--`, módulo de decodificador real | `arw`, `cr3`, `heic`, `ttf`, `xcf` |
| `ff_desconocido_por_el_binario` | **12** | no | en `censo.json` `ffmpeg.muertos_in`: ninguna de las cuatro listas lo reconoce | `alsa`, `pulse`, `x11grab`, `video4linux2` |
| **`no_aplica_generador`** | **10** | **SÍ** | `-list format`: módulo sintetizador, modo `r--` | `xc`, `gradient`, `plasma`, `caption` |
| `im_pseudo_operador` | **7** | no | pseudo-formato que **sí consume** un fichero o una imagen | `msl`, `pango`, `text`, `tile` |
| **`no_aplica_protocolo`** | **4** | **SÍ** | `-list format`: **`Module = URL`** | `file`, `ftp`, `http`, `https` |
| **`no_aplica_dispositivo`** | **2** | **SÍ** | `ffmpeg -devices`, y **no** es demuxer | `lavfi`, `openal` |

### 3.1 Las tres clases que se mueven, publicadas ENTERAS

Son 16 afirmaciones, y cada una va con su fila cruda del motor. **[MEDIDO]**

**`no_aplica_dispositivo` (2)** — `crudo/ff-devices.txt`, y ninguno aparece en `-demuxers`:

```
 D  lavfi           Libavfilter virtual input device
 D  openal          OpenAL audio capture device
```

**`no_aplica_protocolo` (4)** — `crudo/im-format.txt`, `Module = URL`:

| Token | Módulo | Modo | Descripción |
|---|---|---|---|
| `file` | `URL` | `r--` | Uniform Resource Locator (file://) |
| `ftp` | `URL` | `r--` | Uniform Resource Locator (ftp://) |
| `http` | `URL` | `r--` | Uniform Resource Locator (http://) |
| `https` | `URL` | `r--` | Uniform Resource Locator (https://) |

**`no_aplica_generador` (10)** — el motor describe la imagen que **sintetiza o captura**:

| Token | Módulo | Modo | Descripción |
|---|---|---|---|
| `xc` | `XC` | `r--` | Constant image uniform color |
| `canvas` | `XC` | `r--` | Constant image uniform color |
| `gradient` | `GRADIENT` | `r--` | Gradual linear passing from one shade to another |
| `radial-gradient` | `GRADIENT` | `r--` | Gradual radial passing from one shade to another |
| `plasma` | `PLASMA` | `r--` | Plasma fractal image |
| `fractal` | `PLASMA` | `r--` | Plasma fractal image |
| `pattern` | `PATTERN` | `r--` | Predefined pattern |
| `caption` | `CAPTION` | `r--` | Caption |
| `label` | `LABEL` | `r--` | Image label |
| `screenshot` | `SCREENSHO` | `r--` | Screen shot |

### 3.2 Las siete que NO se mueven, y por qué — la parte incómoda

*«Cada reclasificación es una afirmación verificable: si no puedes sostenerla, déjala en su
clase y dilo.»* Siete pseudo-formatos de ImageMagick **se quedan donde estaban**, aunque la
sospecha del encargo nombraba a cuatro de ellos: **[MEDIDO]**

| Token | Módulo / modo | Por qué NO se mueve |
|---|---|---|
| `msl` | `MSL` `r--` | *Magick Scripting Language*: lee un **fichero XML de script**. Es un fichero |
| `pango` | `PANGO` `r--` | lee **marcado Pango**, que puede venir de fichero |
| `text` | `TXT` `r--` | renderiza un **fichero de texto** como imagen |
| `tile` | `TILE` `r--` | toma **otra imagen** como textura |
| `stegano` | `STEGANO` `r--` | toma **otra imagen** como portadora |
| `clip` | `CLIP` `rw+` | modo `rw+`: **ImageMagick declara que lo escribe** |
| `mask` | `MASK` `rw+` | ídem |

`clip` y `mask` son el caso más claro: **están declarados escribibles por el propio motor**,
así que si algo son, es la clase `ff_declarado_muxer` de §4 en versión ImageMagick — un
motivo falso, no un no-formato.

---

## 4. El hallazgo grande: 73 motivos falsos, 54 sin probar

El motivo de las 445 dice *«ningún motor local lo escribe»*. **Para 73 de ellas, `ffmpeg
-muxers` dice lo contrario.** Y el mecanismo de §1 explica por qué el censo no lo vio:
**[MEDIDO]** (`log-gate.txt`)

| De los 73 que ffmpeg declara muxer… | n | Qué pasó |
|---|---:|---|
| se intentó escribirlos y falló | **5** | el motivo es inexacto pero la conclusión aguanta |
| se probaron como **destino** y salieron muertos | **14** | no entraron en `viva_ff_out`, así que la rama 2 **no se ejecutó** |
| **nunca se probaron como destino** | **54** | el censo de salida sólo cubrió los 202 destinos de ConvertX |

Los 54, enteros:

```
aea, alaw, alp, argo_asf, cavsvideo, codec2, codec2raw, dash, daud, dirac, f32be, f32le,
f64be, f64le, ffmetadata, film_cpk, filmstrip, g723_1, g726, g726le, h264, hls, ilbc,
image2, jacosub, kvag, mcc, microdvd, mpjpeg, mulaw, rawvideo, rtp, rtsp, s16be, s16le,
s24be, s24le, s32be, s32le, s8, sap, smjpeg, truehd, u16be, u16le, u24be, u24le, u32be,
u32le, u8, vc1test, vidc, webvtt, wsaud
```

**Son 10 908 aristas del grafo A.** Y muchos son triviales de escribir: `rawvideo`, `s16le`,
`u8`, `image2`, `webvtt` son formatos que ffmpeg produce todos los días.

### 4.1 Y el repositorio ya había refutado cuatro de ellos, sin saberlo

`firmas-cierre.md` §4.4 (`C28`) escribió **seis formatos** con una invocación mejor,
**2 de 2 cada uno**. Cruzando esa lista con los 445: **[MEDIDO]**

| Formato | Estado en `semi_entrada.json` | Clase | ¿lo escribió C28? |
|---|---|---|:--:|
| `dnxhd` | `no_materializable` — *«ningún motor local lo escribe»* | `ff_declarado_muxer` | **sí (2/2)**, con `-s 1920x1080 -b:v 36M -pix_fmt yuv422p` |
| `dts` | `no_materializable` — ídem | `ff_declarado_muxer` | **sí (2/2)**, con `-strict -2` |
| `mlp` | `no_materializable` — ídem | `ff_declarado_muxer` | **sí (2/2)**, con `-strict -2 -ar 48000` |
| `thd` | `no_materializable` — ídem | `ff_extension_de_demuxer` | **sí (2/2)**, con `-strict -2 -ar 48000` |
| `h261` | `viva` | — | sí |
| `h263` | `viva` | — | sí |

> **Cuatro formatos llevan en el estrato indeterminado con el motivo «ningún motor local lo
> escribe» mientras otro informe del mismo repositorio los tenía escritos.** Ninguno de los
> dos informes podía verlo: `C28` mira el lado de SALIDA y `aristas-nominales.md` el de
> ENTRADA, y **el censo de entrada no consulta el de salida más que a través de
> `viva_ff_out`, que se calculó antes**. Es la trampa 106 —*busca dónde el repositorio ya
> declaró su excepción*— y esta vez la excepción estaba en un informe hermano.

---

## 5. El número corregido, con su derivación

**Qué se retira y por qué.** Una arista `xc → png` no es una arista que falte por medir: es
una arista que **no existe**, porque su origen no es un fichero. Sale de la **población**, no
sólo del numerador — si sólo se restara del numerador se estaría afirmando que la conversión
existe y es viable, que es lo contrario de lo medido.

Una arista se retira **sólo si TODOS sus motores la declaran desde un origen que no es un
fichero para ese motor** (las aristas mixtas ffmpeg+imagemagick sobreviven si alguno la
sostiene).

| | Antes | Después | |
|---|---:|---:|---|
| **Población** | 138 501 | **135 535** | −2 966 aristas retiradas |
| Vivas (marco muestral) | 40 252 (29,06 %) | 40 252 (**29,70 %**) | ninguna se pierde |
| Refutadas por ejecución | 22 235 (16,05 %) | 22 113 (**16,32 %**) | −122 |
| **Indeterminadas** | **75 874 (54,78 %)** | **73 030 (53,88 %)** | **−2 844** |
| Ghostscript / Gotenberg | 140 (0,10 %) | 140 (0,10 %) | — |

**[MEDIDO]** — `recuento.py`, `log-recuento.txt`.

> ### El 54,78 % pasa al **53,88 %**. La sospecha es cierta y vale **0,90 puntos**.

Las 2 966 se reparten así, y el desglose importa porque muestra que la corrección es
pequeña **por aritmética, no por casualidad**: cada token retirado multiplica por las salidas
vivas de su motor, y sólo se retiran 16 tokens de 445.

| Clase retirada | Tokens | Aristas indeterminadas | Aristas retiradas totales |
|---|---:|---:|---:|
| `no_aplica_generador` | 10 | 1 790 | |
| `no_aplica_protocolo` | 4 | 716 | |
| `no_aplica_dispositivo` | 2 | 338 | |
| **suma** | **16** | **2 844** | **2 966** (2 844 indeterminadas + 122 que ya estaban refutadas) |

### 5.1 Dónde está el peso de verdad — y no es donde miraba la sospecha

| Clase de origen | Aristas indeterminadas | % del estrato |
|---|---:|---:|
| `ff_solo_demuxer` | 29 406 | **38,76 %** |
| `ff_extension_de_demuxer` | 16 470 | **21,71 %** |
| **`ff_declarado_muxer`** | **12 242** | **16,13 %** |
| `im_formato_real_solo_lectura` | 11 451 | 15,09 % |
| `ff_desconocido_por_el_binario` | 2 028 | 2,67 % |
| `no_aplica_generador` | 1 790 | 2,36 % |
| `im_pseudo_operador` | 1 253 | 1,65 % |
| `no_aplica_protocolo` | 716 | 0,94 % |
| `no_aplica_dispositivo` | 338 | 0,45 % |
| mixtas (dos motores) | 180 | 0,24 % |

**Las tres clases `no_aplica` juntas son el 3,75 % del estrato. `ff_declarado_muxer` sola es
el 16,13 %, y se cierra con invocaciones de ffmpeg, no con un corpus descargado.**

---

## 6. Lo que refuto, incluida la lista del encargo

El encargo daba una lista «hecha mirando nombres» y pedía expresamente no darla por buena.
**Contrastada con los metadatos, acierta 15 de 26 — el 57,7 %.** **[MEDIDO]**

| Token propuesto | Veredicto | Por qué |
|---|---|---|
| `xc`, `gradient`, `radial-gradient`, `plasma`, `canvas`, `label`, `caption`, `pattern`, `screenshot` | **acierta** (9) | módulos sintetizadores, modo `r--` |
| `file`, `ftp`, `http`, `https` | **acierta** (4) | `Module = URL` |
| `lavfi`, `openal` | **acierta** (2) | `ffmpeg -devices` |
| `text`, `tile`, `stegano`, `msl` | **falla** (4) | son pseudo-formatos, pero **consumen un fichero o una imagen**: §3.2 |
| `concat`, `sdp` | **falla** (2) | son **demuxers reales**; el fichero de `concat` es una lista de texto y el de `sdp` una descripción de sesión |
| `hls`, `dash`, `rtsp`, `rtp`, `mpjpeg` | **falla** (5) | son **muxers**: ffmpeg los escribe. Están en los 54 de §4 |
| — | **se le escapa** (1) | **`fractal`**, que es el mismo módulo `PLASMA` que `plasma` |

**Las dos refutaciones que importan:**

1. **En el lado de ffmpeg la sospecha falla 7 de 9.** `hls`, `dash`, `rtp`, `rtsp` y `mpjpeg`
   parecen protocolos por el nombre y son formatos de fichero que ffmpeg **escribe** — un
   `.m3u8` y un `.mpd` son ficheros. Y `rtp`/`hls` aparecen **a la vez** en `-protocols` y en
   `-muxers`: **estar en la lista de protocolos no impide ser un formato**, que es justo el
   matiz que el criterio de nombres no puede tener.
2. **También refuto una parte de mi propio primer cruce.** Mi sonda inicial declaró **110
   tokens «desconocidos por el binario»** porque sólo miraba los **nombres** de
   `-demuxers`/`-muxers`; el censo también contaba las **«Common extensions»** de cada
   demuxer. Cruzado contra `censo.json`, **98 de los 110 sí eran conocidos** y sólo **12** lo
   son de verdad. Publicar los 110 habría sido una regresión con mejor pinta.

---

## 7. Contra el precedente `C28`, como pedía el encargo

`firmas-cierre.md` §4.4 hizo esta misma reclasificación sobre sus 56 destinos.
**Los dos criterios no chocan: miden ejes distintos, y ninguno de los dos vale en el eje del
otro.** **[MEDIDO]**

| | `C28` (`firmas-cierre.md` §4.4) | `C49` (este informe) |
|---|---|---|
| Eje | semiarista de **salida** (56 destinos) | semiarista de **entrada** (445 orígenes) |
| Evidencia | **el `rc` de cada celda** | **los listados de metadatos del motor** |
| Clase «no es un formato» | *«metadato, no formato»*, **8 de 56 (14,3 %)** | `no_aplica_*`, **16 de 445 (3,6 %)** |
| Remedio principal | una invocación mejor: **21 de 56** | una invocación mejor: **73 de 445** |

**Coinciden en lo que importa y por eso me da confianza:** los dos encuentran una clase «esto
no es un destino/origen de conversión», los dos concluyen que **el corpus FATE de ~1 GB no es
el remedio principal**, y los dos apuntan a *«una invocación correcta»* como la vía barata.

**Y donde no coinciden, la causa está identificada:** `C28` pudo usar el `rc` porque su censo
**ejecutó** las 56 celdas y guardó el código. El censo de entrada **no ejecutó nada** en las
445 y guardó una constante (§1). **No es que yo prefiera los metadatos al `rc`: es que en
este eje el `rc` no existe.** El arreglo de §8 es, precisamente, hacer que exista.

---

## 8. Dónde vive el arreglo

**Sí: el censo debe emitir un cuarto estado.** El proyecto ya usa `no_aplica` en el punto 1
del contrato con exactamente esta semántica —*la propiedad no se puede evaluar porque el
objeto no la tiene*— y `CLAUDE.md` §5 ya dice que **la cobertura va en cuatro estados y no en
un booleano**. Aquí el booleano encubierto es «materializable sí/no».

**Fichero exacto: `bench/salidas-aristas/_semi_in.py`.** Dos cambios, los dos en
`materializa()` y en el `res[...]` de `__main__`. **No los he escrito: el fichero es la salida
medida de otro agente y esta rama no toca `filex/` ni `pruebas/`.**

**(a) Un cuarto estado `no_aplica`, decidido ANTES de intentar materializar.** Una tabla
derivada de los listados —no una lista a mano— con los 16 tokens de §3.1:

```python
# ffmpeg: en `-devices` y no en `-demuxers`  ->  fuente de captura, no fichero
# imagemagick: Module == "URL"               ->  localizador, no fichero
# imagemagick: modulo sintetizador, modo r-- ->  generador, no fichero
if es_no_aplica(motor, a):
    res["%s|%s" % (motor, a)] = {"estado": "no_aplica",
                                 "motivo": evidencia_del_listado(motor, a)}
    continue
```

Y en `_agrega.py`, las aristas cuyo origen es `no_aplica` **para todos sus motores** salen de
la población en vez de contarse como indeterminadas — es el bloque que `recuento.py` ya
implementa y que reproduce las cifras de §5.

**(b) El motivo deja de ser una constante.** Es el arreglo más barato y el que más habría
ahorrado: hoy las 445 comparten un string que para **73 de ellas es falso**. Basta con
registrar **qué se intentó**, aunque no se intentara nada:

```python
return None, {"corpus": False,
              "ffmpeg_intentado": a in viva_ff_out,
              "ffmpeg_declara_muxer": a in mux_nombres,   # <- lo que faltaba
              "magick_intentado": a in viva_im_out,
              "magick_modo": im_modo.get(a),
              "intentos": det}                            # con su `rc`, como las vivas
```

Con ese campo, los 54 de §4 se habrían visto **el día del censo** y sin ejecutar nada: el
propio JSON habría dicho *«ffmpeg declara muxer y no se intentó»*. **Es la lección de `C28`
—registra el `rc` de cada celda— extendida al caso en que no hubo celda: registra también que
NO la hubo, y por qué.**

**(c) `aristas-nominales.md` §7 pide un matiz, no una corrección.** Su PENDIENTE dice que
cerrar el estrato *«exige un corpus de esos 445 formatos… fabricarlos no es posible con los
motores locales — por definición, son los que ningún motor local escribe»*. **La definición no
se cumple para 73 de los 445**, así que el PENDIENTE es correcto para ~372 y falso para 73.

---

## 9. Máquina consumida, y qué queda PENDIENTE

**Consumo: siete listados de metadatos, una vez cada uno** —`magick -list format`,
`magick -list delegate`, `ffmpeg -hide_banner` con `-protocols`, `-devices`, `-demuxers`,
`-muxers`, `-formats`—, todos instantáneos y de sólo lectura. **Cero conversiones, cero
contenedores, cero suite, cero GPU, cero lecturas del `corpus/`.** El resto son lecturas de
JSON y de texto ya en disco. `git lfs checkout` **no hizo falta y no se ejecutó**: ningún
instrumento de este informe abre un fichero del corpus. **[MEDIDO]**

**PENDIENTE, por orden de lo que devuelve:**

1. **Escribir los 54 de §4.1 con ffmpeg** y materializarlos. Cierra hasta **10 908 aristas**
   (14,4 % del estrato) con **invocaciones de segundos y 0 bytes de red**. Cuatro ya están
   escritos por `C28`: `dnxhd`, `dts`, `mlp`, `thd`.
2. **Los 10 dispositivos de otra plataforma.** De los 12 `ff_desconocido_por_el_binario`,
   diez son capturas de Linux —`alsa`, `oss`, `pulse`, `jack`, `sndio`, `fbdev`, `kmsgrab`,
   `x11grab`, `video4linux2`, `iec61883`—. **No los he movido, porque decirlo por el nombre es
   exactamente el error que este informe vino a corregir** y esta build de Windows no los
   declara en ninguna lista. Se confirma con **una orden** en la ronda que pueda usar
   contenedores: `docker exec filex-convertx ffmpeg -hide_banner -devices`. Si aparecen, son
   `no_aplica_dispositivo` y el 53,88 % baja otras **~2 028 aristas**, hasta ~**53,4 %**.
3. **`clip` y `mask`** (§3.2) están declarados `rw+` por ImageMagick: comprobar si el censo de
   salida los probó, como los 73 de ffmpeg.
4. **Los 98 `ff_extension_de_demuxer`** se clasifican aquí **por complemento** contra
   `censo.muertos_in`, no por lectura directa: la lectura directa exige las ~590 sondas
   `ffmpeg -h demuxer=…`. El complemento es exacto dado `censo.json`, pero **no publica de qué
   demuxer es extensión cada uno**, que es lo que diría si son materializables.

---

### 9.1 `ci/integridad.py`: 8 de 9, y el rojo que queda es de encargo

**Al terminar, `python ci/integridad.py` da 8 verdes y UNA roja:** **[MEDIDO]**

```
MAL  informes-registrados   103 informes, todos citados
      aristas-reclasificacion.md
FALLA: informes-registrados
```

**Es correcta y no la puedo arreglar.** La comprobación exige que todo informe de `bench/`
esté citado en la tabla de §1 de `ESTADO-Y-REPARTO.md`, y **el encargo me prohíbe
expresamente editar ese fichero**. Las dos instrucciones chocan, y la resolución honesta es
**no tocar el fichero prohibido y declarar el rojo**, no colar una edición para poner verde
un comprobador. **La fila que lo cierra está escrita literal en §10.1: pegarla en
`ESTADO-Y-REPARTO.md` §1 pone la comprobación en verde y no hace falta nada más.** Las otras
ocho —`citas` (57 vivas, 0 muertas), `manifiestos`, `binarios`, `trampas`, `secretos`,
`inventario`, `un-emoji-por-fila`, `en-curso`— pasan.

*(Y va con su control: antes de empezar, sobre el árbol limpio, las nueve pasaban. El rojo lo
introduce el informe nuevo y sólo él.)*

---

## 10. Texto propuesto para los documentos que no debo editar

### 10.1 Para `ESTADO-Y-REPARTO.md` §1

> | 04/09 | **`bench/aristas-reclasificacion.md`** (worker9, `cpu/aristas-reclasificacion`) | **`C49` cerrada: la sospecha es CIERTA y vale 0,90 puntos — el 54,78 % pasa al 53,88 %.** De los 445 `no_materializable`, **16 no son ficheros** (10 generadores de ImageMagick, 4 de `Module=URL`, 2 dispositivos de ffmpeg) y salen de la población: 138 501 → **135 535** aristas, indeterminadas 75 874 → **73 030**. Los otros **429 están bien clasificados**. **El hallazgo grande está en el MOTIVO, no en el estado:** para **73 de los 445** `ffmpeg -muxers` declara que el binario **sí los escribe** —**12 242 aristas, el 16,13 % del estrato**— y **54 no se probaron nunca**, porque el censo de salida sólo cubrió los 202 destinos de ConvertX. **Cuatro de ellos —`dnxhd`, `dts`, `mlp`, `thd`— ya los había escrito `C28` 2/2**, en un informe hermano que ninguno de los dos podía cruzar. Refuta 11 de las 26 conjeturas del encargo (`hls`, `dash`, `rtp`, `rtsp`, `mpjpeg` son **muxers**, no protocolos) **y una propia**: el primer cruce dio 110 «desconocidos» y son **12**. Reproduce 138 501 / 40 252 / 22 235 / 75 874 / 140 exactas antes de tocar nada. **Consumo: siete listados de metadatos.** Trampa **122** |

### 10.2 Para `CLAUDE.md` §4 — trampa nueva, AL FINAL

> 122. **Un campo de motivo que es una CONSTANTE del `return` no es una medida, y sobrevive porque nadie compara su valor entre casos — MEDIDO el 04/09** (`bench/aristas-reclasificacion.md`). Las **445** entradas `no_materializable` de `bench/salidas-aristas/semi_entrada.json` comparten **un solo string**: *«no materializable (ningún motor local lo escribe)»*. **Para 73 de ellas es falso**, y lo desmiente el propio motor: `ffmpeg -muxers` las declara escribibles —`rawvideo`, `s16le`, `image2`, `webvtt`, `hls`—. La causa no es un fallo de sonda sino que **no hubo sonda**: `materializa()` sólo intenta con ffmpeg si el token está en `viva_ff_out`, que sale del censo de **salida** y sólo cubrió los 202 destinos que ConvertX declara, así que **54 de los 73 nunca se probaron** y cayeron al motivo por defecto. Es la trampa 66 sin sonda que romper —*el mismo valor para cosas que sabes distintas*— y la **25** un nivel más arriba: *«no se pudo»* y *«no se intentó»* se escriben igual. **El precio de no verlo se mide en el repositorio: `firmas-cierre.md` §4.4 había ESCRITO `dnxhd`, `dts`, `mlp` y `thd` 2 de 2** mientras seguían marcados «ningún motor local los escribe», y ninguno de los dos informes podía cruzarlo porque uno mira la salida y el otro la entrada. **Y el remedio de `C28` —«el `rc` no es una pista, es la respuesta»— NO es aplicable aquí: las entradas no materializables guardan `{estado, motivo}` y las vivas guardan `intentos` con su `rc`, así que en el eje de entrada el `rc` no existe.** La regla que queda: **un estado negativo registra QUÉ se intentó, y cuando no se intentó nada, registra eso y la razón** —basta `{"ffmpeg_declara_muxer": True, "ffmpeg_intentado": False}` para que el fallo se vea el día del censo y sin ejecutar nada—. Corolario del otro lado, y es una refutación propia: **clasificar por el NOMBRE falla 7 de 9** en ffmpeg (`hls`, `dash`, `rtp`, `rtsp` y `mpjpeg` parecen protocolos y son **muxers**; `rtp` y `hls` están **a la vez** en `-protocols` y en `-muxers`), así que **estar en la lista de protocolos no impide ser un formato**, y la lista separada sólo decide cuando el token **no** está también en `-demuxers`.

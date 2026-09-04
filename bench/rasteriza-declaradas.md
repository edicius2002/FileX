# `_DECLARADAS` no sabía llevar la bandera `rasteriza` — worker14, ronda 13

Rama `edicius2002/filex-rasteriza-declaradas`, base `main`.
Salidas y arneses en `bench/salidas-rasteriza-declaradas/`.

---

## 0. El titular, y no es el que traía el encargo

**El defecto era real y el daño que se le atribuía NO se materializa hoy.**

`_DECLARADAS` era una tupla de pares y `_aristas()` construía las `Arista` sin
pasar `rasteriza=`, así que **toda arista declarada nacía en `False` mintiera o
no**, y `sondeo.aplicar()` conserva `rasteriza` de la arista que ya existe —
nunca del fichero de sondeo—, así que **medirla no lo arreglaba**. Eso está
arreglado: `_DECLARADAS` es ahora un `dict` `{(origen, destino): rasteriza}`, el
valor hay que escribirlo, y `pptx→png` y `svg→png` entran al grafo con
`rasteriza=True`.

Lo que **no** se sostiene es la consecuencia. El encargo —y el comentario que
worker7 dejó en el código— predecían que *«el planificador elegiría un camino
que rasteriza sin pagar la penalización de +1000»*. Medido con el contrafactual
exacto (las dos aristas nuevas forzadas a `False` sobre el grafo de producción,
544 pares, `max_saltos=4`, el de producción):

| | verdad | mentira |
|---|---:|---:|
| caminos elegidos que cambian | — | **0** |
| pares que eligen un camino que rasteriza **sin saberlo** | — | **0** |
| rechazos explicados que citan una ruta que rasteriza | **18** | **13** |

**Ni un solo par cambia de camino elegido, y ninguno rasteriza en silencio.** Lo
que la mentira destruye es la **EXPLICACIÓN**: se pierden 7 rechazos y aparecen
2 sustitutos. Y eso no es un detalle menor en este proyecto, porque la mitad del
criterio de aceptación del hito 1 es exactamente eso — «*alcanzar es fácil,
elegir bien no*», `grafo.py:6`.

**Por qué no llega a elegir mal: el coste por salto ya la descartaba.** Una ruta
que rasteriza necesita 2 saltos como mínimo (`pptx→png→pdf` = 2,23) contra 1 de
la directa (`pptx→pdf` = 1,05). La penalización de +1000 **no decidió ninguno de
los 544 pares**; lo decidió el conteo de saltos. La bandera sigue haciendo falta
—el día que exista un par cuyo único camino pase por una arista rasterizadora,
+1000 es lo único que separa un aviso de un silencio—, pero **hoy es una defensa
en profundidad, no la defensa**. Es la trampa 58 aplicada a un encargo: el hecho
era cierto y la causa que se le atribuía, no.

**Segundo hallazgo, de propina y de otro carril:** `epub→epub` con Calibre **no
es determinista** — 4 corridas, 4 `sha256`, y los bytes van de 17 712 a 141 175
(×7,97). §6.

**Tercero:** `pruebas/test_hito4.py::test_el_aviso_de_rasterizacion_viaja_al_modelo`
**no puede ejecutarse nunca** con el predicado que tiene. §7. **No lo toco: el
fichero es de otra rama** (el encargo lo prohíbe explícitamente).

Resondeo: **40 aristas, 40 con `rc=0`, 40 de 40 reproducen su veredicto
anterior, 0 movidos, 0 huérfanos**. §3.

---

## 1. Estado declarado — las cuatro declaraciones (trampas 94 y 101)

| Qué | Valor |
|---|---|
| **Intérprete** | `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe`, CPython **3.11.9**, `win32` |
| **Entorno** | Docker **29.4.3**, demonio arriba. `docker ps -a` = **7** contenedores, 5 vivos. Imágenes `filex-c13:latest` (5,78 GB) y `ghcr.io/c4illin/convertx:latest` presentes |
| **Qué quedó fuera** | ver §8 |
| **Estado de la máquina** | ver §8 |

**Docker, declarado antes de empezar como pide el encargo.** `docker info` →
`29.4.3 · containers=7 · running=5`. `docker ps -a` lista **dos contenedores en
estado `Created`** —`filex-956c-1951e7fc5494422d8d21238fcefef29e` (`filex-c13`)
y `filex-956c-3b173cd69d8342c4867ae7f7aff7d4cd` (`convertx`)—, de 4 horas antes
de que yo empezara. **No son míos y no los toco.** Son exactamente el caso de la
trampa 37: `docker ps` **no los lista** y `docker ps` solo habría dicho «5
contenedores, todo en orden». Mi arnés cuenta los dos recuentos por separado
(`contenedores(todos=True)`) y **al terminar el resondeo hay los mismos 7: 0
huérfanos nuevos**.

**LFS:** el *worktree* llegó con el corpus materializado —`corpus/imagen/tipico.png`
pesa **42 855 B**, no 130— así que la trampa 34 no aplicó y no hizo falta
`git lfs checkout`. Se comprobó antes de creerse ningún rojo.

**GPU:** no se tocó. Este carril no toma el lock de la tarjeta.

---

## 2. Lo que estaba sellado ANTES de tocar nada (trampa 61)

La trampa 61 obliga a comprobar, **con el algoritmo de ahora y antes de
escribir**, si lo sellado coincide con el árbol: si ya estaba caducado, resellar
es indulgencia y hay que resondear igual. **MEDIDO, y salió limpio:**

```
interprete actual: 3.11
doc_calibre      interprete=3.11 OK | caducados=ninguno
doc_libreoffice  interprete=3.11 OK | caducados=ninguno
doc_pandoc       interprete=3.11 OK | caducados=ninguno
ffmpeg           interprete=3.11 OK | caducados=ninguno
imagemagick      interprete=3.11 OK | caducados=ninguno
```

**Los cinco ficheros del disco coincidían con el árbol en los tres componentes y
declaraban el intérprete correcto.** No hay hallazgo aparte por este lado: el
punto de partida era honesto, y por tanto todo lo que caduque después es
atribuible a mi cambio y a nada más.

---

## 3. El cambio, y lo que caducó

### 3.1 La forma

`_DECLARADAS` pasa de `tuple` de pares a **`dict` `{(origen, destino): rasteriza}`**,
que es la forma que ya tenían sus dos tablas hermanas `_MEDIDAS` y `_MUERTAS`.

**Por qué un `dict` y no un tercer campo en la tupla ni una tabla aparte.** Una
tabla aparte (`_DECLARADAS_QUE_RASTERIZAN = {...}`) deja vivo el mismo modo de
fallo: quien añade un par a una tabla y se olvida de la otra vuelve a mentir en
silencio, con las dos tablas bien escritas. Con un `dict` **el valor no es
opcional**: no hay defecto que mienta porque no hay defecto.

**Y queda un modo de fallo dentro de la vía buena, que hay que decir:**
`for o, d in self._DECLARADAS` **sigue funcionando** sobre un `dict` y **no lee
el valor**, así que una migración a medias dejaría `rasteriza=False` otra vez con
la tabla perfectamente escrita. Es la trampa 48 —*un recuento correcto no prueba
un contenido correcto*— en su versión de bucle. Por eso `_aristas()` itera
`.items()`, que revienta contra una tupla de pares, y por eso hay una prueba de
AST que **exige el `.items()`** (§5).

### 3.2 Las dos aristas que estaban fuera

`pptx→png` y `svg→png` llevaban desde el 02/09 **medidas `real` en
`filex/sondeo/doc_libreoffice.json` y fuera del grafo**, con el motivo escrito.
Ahora entran con `rasteriza=True`. El grafo pasa de **230 a 232 aristas** y de
**7 a 9** con `rasteriza=True`:

```
docx  ->png    doc_libreoffice  real
pptx  ->png    doc_libreoffice  real   ← nueva
svg   ->png    doc_libreoffice  real   ← nueva
pdf   ->jpg    ghostscript      real
pdf   ->png    ghostscript      real
pdf   ->tif    ghostscript      real
svg   ->jpg    imagemagick      real
svg   ->png    imagemagick      real
svg   ->webp   imagemagick      real
```

### 3.3 Qué caducó, y el resondeo

Tocar `_EnContenedor._aristas()` y las tres tablas caducó el componente `motor`
de **los tres** motores documentales — los tres comparten la base por MRO, así
que tocar el bucle de la base los caduca a todos aunque solo se editara una
tabla:

```
caducados: {'doc_libreoffice': ['motor'], 'doc_pandoc': ['motor'], 'doc_calibre': ['motor']}
```

| motor | huella `motor` antes | después |
|---|---|---|
| `doc_libreoffice` | `48e14e7a35210f60` | `ae44ff79d26ded79` |
| `doc_pandoc` | `08817e0e76ef187f` | `f82b19cb9263ef45` |
| `doc_calibre` | `5ccb326907e06e1e` | `2291ddcd4246f75a` |

`invocacion` (`3a2c16603bb46673`) y `contrato` (`fe41b4d52413299c`) **no se
tocaron y no se movieron**, en los cinco ficheros.

**Se resondearon 40 aristas de verdad, no se reselló nada.** El alcance es
exactamente lo que caduca: las **16 + 16 + 8** entradas que los tres
`filex/sondeo/doc_*.json` aplican. Las `_MEDIDAS` **no entran a propósito** y
esto corrige el alcance de worker7 sin quitarle mérito: nacen `REAL` en
`_aristas()` **sin pasar por `sondeo.aplicar()`**, así que ninguna huella las
gobierna y remedirlas no cierra ninguna deuda. Las **8 de Calibre, en cambio,
nadie las había remedido en la ronda 12** y aquí sí entran.

**Resultado — MEDIDO** (`bench/salidas-rasteriza-declaradas/resondeo40.json`,
`FileX.convertir()` real: `motor.orden()`, `invocacion.ejecutar()` contra Docker,
contrato de cinco puntos y censo del punto 5):

| | |
|---|---:|
| aristas remedidas | **40** |
| `rc = 0` | **40 / 40** |
| veredicto de contrato **reproducido** | **40 / 40** |
| veredictos **movidos** | **0** |
| tiempo de motor acumulado | 138,3 s (tanda entera: 141,4 s) |
| más rápida / más lenta | `pandoc epub→docx` 820,7 ms / `calibre mobi→pdf` 9 203,2 ms |
| contenedores huérfanos nuevos (`docker ps -a`) | **0** |

**Ningún veredicto se movió, y ése es el resultado que el encargo pedía por
encima de las dos aristas nuevas.** El código que decide estas 40 aristas
—`_cmd()`, la invocación, el contrato— sigue dando lo mismo; lo que cambió es
únicamente la forma de la tabla y la bandera que ahora sabe llevar.

---

## 4. La auditoría de las TRES tablas: cuántas mentían

El encargo pide auditar las tres tablas, no solo las dos aristas nuevas, y decir
**cuántas aristas estaban mintiendo**.

**El criterio no es «el motor sabe escribir un PNG»** —eso es el hecho por la
causa, trampa 58—: es **si el texto de la entrada sobrevive en la salida**. Una
arista rasteriza cuando el contenido llega como píxeles donde entró como texto,
y eso cubre los dos miembros de la misma familia: el destino que no puede llevar
texto (`png`) y el destino que **sí** puede y aun así llegó sin él, que es el
fallo de `resvg` y el que nadie ve. Se mide con el centinela `FILEXSENTINELA7743`
y el recuento de caracteres, con el umbral **≥10** de la trampa 4 (`txtwrite`
emite 1-3 caracteres de basura en un PDF sin texto).

### 4.1 El recuento

| tabla | declaradas | `rasteriza` medido `no` | medido `sí` | sonda **ciega** | **mentían** |
|---|---:|---:|---:|---:|---:|
| `LibreOfficeEnContenedor` | 14 (+2 nuevas) | 14 | 2 (las nuevas) | 0 | **0** |
| `PandocEnContenedor` | 16 | 16 | 0 | 0 | **0** |
| `CalibreEnContenedor` | 8 | 7 | 0 | 1 | **0** |
| **total** | **38 (+2)** | **37** | **2** | **1** | **0** |

**Ninguna de las 38 aristas que ya estaban declaradas mentía.** El `False`
forzado que llevaban era, por casualidad, el valor correcto en las 38. Las dos
que sí rasterizan son exactamente las dos que worker7 dejó fuera **porque no
podían decirlo** — su exclusión era correcta y ahora es innecesaria.

Que el saldo sea 0 no vacía el hallazgo: **lo que estaba roto no era el
contenido de la tabla, era su capacidad de expresarlo**, y esa incapacidad tenía
dos aristas medidas `real` fuera del grafo como prueba.

### 4.2 El comentario de `pandoc`: el hecho era cierto, la causa era una
### afirmación

`motor_contenedor.py:590` decía: *«ninguna rasteriza (`pandoc` no produce
imágenes desde estos pares)»*. **El hecho se confirma —16 de 16 devuelven el
centinela— y la causa que daba es la equivocada.** «No produce imágenes» y «no
rasteriza» no son la misma proposición: `svg→pdf` con LibreOffice **tampoco
produce una imagen** y podría perfectamente entregar un PDF con la geometría y
sin texto —es lo que hace `resvg`—, y sin embargo conserva el texto (44
caracteres, centinela presente). El razonamiento correcto pasa por el texto, no
por el formato de salida, y ahora eso está medido y escrito en el propio
comentario.

### 4.3 `mobi→azw3`: la sonda es ciega y se dice

AZW3 comprime el texto (PalmDoc/LZ77), así que el centinela sale `False` y **eso
no significa que se haya perdido**. La celda se registra con
`rasteriza_medido = "ciego"` en vez de concluir. Su no-rasterización se apoya en
la ida y vuelta a `epub` ya medida en `bench/salidas-sondeo-doc/d2.json` §C. Es
el único de los 40 casos cuyo veredicto de rasterización **no** lo decide esta
tanda, y por eso va declarado en el propio `filex/sondeo/doc_calibre.json`.

### 4.4 Los 40 casos

`bench/salidas-rasteriza-declaradas/resondeo40.json` lleva por celda: `rc`, `ms`,
bytes, `sha256`, caracteres recuperados, centinela, veredicto del contrato,
cobertura, sobrantes del punto 5, hallazgos, `rasteriza_declarado` y
`rasteriza_medido`. El log completo con la tabla legible está en
`resondeo40.log`.

---

## 5. El criterio de aceptación: que el planificador DISTINGA

El encargo lo dice sin ambigüedad: el criterio no es «la arista está en la
tabla», es **«un camino que rasteriza paga su penalización y uno que no, no»**.

### 5.1 Medido sobre el grafo de producción

232 aristas, 35 orígenes × 16 destinos que admiten texto, `max_saltos=4`:

| | |
|---|---:|
| pares donde el camino **elegido** rasteriza | 0 |
| pares donde se **rechaza** un camino que rasteriza, con su motivo | **18** |
| coste típico del rechazado | **1 002,0 – 1 003,3** |
| coste típico del elegido | **1,02 – 1,21** |

Tres pares ganan explicación gracias a las aristas nuevas
(`pptx→pdf` vía `pptx png pdf`, `md→pdf` vía `md pptx png pdf`, y una segunda
ruta `svg png pdf` por LibreOffice además de la de ImageMagick).

### 5.2 El contrafactual, que es lo que mide el DAÑO

Ya está en §0 y es el hallazgo que corrige el encargo: **0 caminos elegidos
cambian, 0 rasterizaciones silenciosas, y los rechazos explicados caen de 18 a
13** (7 perdidos, 2 sustitutos). Los tres pares afectados —`md→pdf`,
`pptx→pdf`, `svg→pdf`— **siguen recibiendo al menos un aviso**, así que ni
siquiera se pierde la advertencia: se pierde su precisión.

Perdidos con la mentira:

```
('md','pdf','md pptx png pdf')      ('svg','pdf','svg png pdf')
('pptx','pdf','pptx png pdf')       ('svg','pdf','svg png webp pdf')
('svg','pdf','svg jpg pdf')         ('svg','pdf','svg png ico pdf')
                                    ('svg','pdf','svg webp ico pdf')
```

Aparecidos con la mentira (el hueco de `mejor_raster` lo ocupa otra ruta):

```
('md','pdf','md docx png pdf')      ('pptx','pdf','pptx md docx png pdf')
```

### 5.3 Las pruebas — `pruebas/test_grafo_rasteriza.py`, 18 casos

Tres capas, y **la tercera es dinámica**, como pide el encargo:

1. **`FormaDeLaTabla` (4)** — sobre el **AST** de `motor_contenedor.py`, no
   sobre el texto (trampa 42), y comprobando que la fuente **compila** antes de
   recorrerla (trampa 60). Exige que las cuatro `_DECLARADAS` sean `ast.Dict`,
   que cada valor sea un booleano **literal** —una expresión cumpliría el tipo y
   volvería a esconder la decisión en otro sitio— y que `_aristas()` use
   `.items()`. Esta última existe porque desde el **objeto** la regresión es
   invisible: una tupla y un `dict` se comportan igual ante `in` y ante
   `for o, d in ...`.
2. **`ElValorLlegaALaArista` (5) + `LasDosQueEstabanFuera` (3)** — herméticas,
   sin Docker ni sondeo. Incluyen el medio defecto que nadie miraba:
   **`test_el_valor_SOBREVIVE_a_sondeo_aplicar`**, que comprueba que superponer
   un sondeo `real` no borra la bandera. Ése era el mecanismo por el que
   *medir la arista no la arreglaba*.
3. **`ElPlanificadorDistingue` (5) + `LaMentiraSeNOTA` (1)** — sobre un grafo
   construido de las **tablas de las clases**, sin sondear: reproducible en una
   máquina sin un solo motor instalado. Busca el par **en vivo** y comprueba que
   el camino que rasteriza cuesta ≥ `PENALIZACION_RASTERIZAR` y el elegido <, que
   el rechazo se explica diciendo «rasteriza», y que si el único camino
   rasterizara habría aviso. Lleva una guarda que separa «no hay grafo» de «hay
   grafo y ningún par» (trampa 43) para que el resto no pueda pasar en vacío.

**Control negativo — MEDIDO.** Contra `HEAD:filex/motor_contenedor.py`, es decir
el código de antes del arreglo, la misma suite da **9 failed / 9 passed**. Las 9
que fallan son las que blindan el defecto; las 5 de `ElPlanificadorDistingue`
pasan en los dos, y **es correcto que pasen**: son el criterio de aceptación del
grafo, no la regresión de esta ronda. Sin este control las pruebas serían de la
familia de la trampa 109 —*un `assert` que nunca se evalúa es indistinguible de
uno que se cumple*—.

---

## 6. Hallazgo lateral: `epub→epub` con Calibre NO es determinista

Salió de una discrepancia que era fácil ignorar: `epub→epub` dio **19 596 B**
donde el sellado anterior (`doc_calibre.json`, caso S22) declaraba **33 749 B**,
con la misma entrada. Tres corridas más, misma orden, mismo contenedor:

| corrida | bytes | `sha256` (16) | caracteres | centinela | contrato |
|---|---:|---|---:|---|---|
| resondeo40 | 19 596 | `5ca032a5bcb7a0a4` | 564 | sí | `ok_parcial` |
| 1 | 18 555 | `4f7fadabcdce4d21` | 564 | sí | `ok_parcial` |
| 2 | **141 175** | `4b2c783ca477ea0a` | 564 | sí | `ok_parcial` |
| 3 | 17 712 | `4204566fbba6c51a` | 564 | sí | `ok_parcial` |

**Cuatro `sha256` distintos y un recorrido de ×7,97 en bytes**, con el texto
recuperado idéntico en las cuatro. **El mecanismo, sondeado y no deducido:** de
las 11 entradas del zip, **8 son idénticas al CRC** y varían tres —
`cover_image.jpg` (la portada que **Calibre genera**, de 46 184 a 153 474 B),
`content.opf` y `toc.ncx` (mismo tamaño, distinto CRC: identificadores)—.

**Consecuencia práctica:** para esta arista **los bytes y el `sha256` no son una
identidad**, y una regresión que los compare contra lo sellado daría un falso
positivo garantizado. Lo estable es el veredicto del contrato y el texto. Queda
escrito en el `nota_huella` de `filex/sondeo/doc_calibre.json`, que es donde lo
lee quien vaya a comparar. Datos en
`bench/salidas-rasteriza-declaradas/determinismo_epub.json`.

**PENDIENTE:** no he barrido las otras 7 aristas de Calibre buscando el mismo
comportamiento; solo `epub→epub` está medida con n=4. Las diferencias de bytes
que sí observé frente al sellado anterior en `mobi→epub` (30 875 contra 20 195)
y `md→epub` (11 844 contra 10 781) **tienen otra explicación disponible** —mis
semillas `entrada.mobi` y `entrada.azw3` se fabrican en cada tanda y no son las
mismas de la ronda anterior— y **no las he separado de la no-determinación**.
Decirlo es la mitad honesta: son dos causas posibles y no he hecho el
experimento que las distingue.

---

## 7. Lo que NO toco, y por qué: `pruebas/test_hito4.py`

**`test_el_aviso_de_rasterizacion_viaja_al_modelo` se salta siempre, y con mi
cambio se sigue saltando.** Su motivo es exacto y sale en el `-rs`:

```
SKIPPED pruebas\test_hito4.py:221: ningún par real rasteriza hacia un destino
con texto en esta máquina — ver bench/aristas-documentales-cierre.md §9
```

**No es que hoy no haya candidato: es que el predicado no puede tener uno.** La
prueba busca *«una arista real que rasterice **hacia** un destino con texto»*:

```python
def _rasteriza_hacia_texto(a):
    if not a.rasteriza: return False
    d = F.formato(a.destino)
    return d is not None and d.texto
```

Una arista que rasteriza **escribe píxeles**: su destino es `png`, `jpg`, `webp`
o `tif`, y ninguno admite texto. Las 9 aristas con `rasteriza=True` del grafo de
hoy —las 7 de antes y las 2 que acabo de meter— van todas a un formato ráster,
así que el filtro devuelve la lista vacía por construcción. **Añadir aristas
rasterizadoras no lo arregla; con la definición de `rasteriza` que tiene el
proyecto, ninguna arista puede satisfacerlo.**

Lo que la penalización de +1000 castiga —y lo que `Decision.aviso` explica— es
un salto que rasteriza **en medio** de un camino cuyo **destino final** admite
texto. Es un predicado de **camino**, no de arista, y es estrictamente más ancho:
hoy da **18 pares**. Mi `_pares_con_ruta_que_rasteriza()` (§5.3) usa el correcto
y por eso encuentra candidatos donde el de `test_hito4` no puede.

**El arreglo cabe en una línea** —buscar sobre `dec.rechazados` y `dec.camino`
en vez de sobre `grafo.aristas`— **y no lo aplico**: el encargo prohíbe tocar
`pruebas/test_hito4.py`, que es de dos ramas sin fusionar, y avisa de que ese
fichero «va a tentar». Efectivamente. **Lo dejo aquí para quien fusione.**

Es la familia de las trampas 107 y 109: un guarda que nombra su causa
correctamente —el par fijo era frágil, y la corrección de la intención era
buena— y cuyo predicado no puede cumplirse, así que produce **una tercera cosa**
que no es ni un salto honesto ni un fallo honesto, y sobrevive a las revisiones
porque el motivo del salto suena a diagnóstico de máquina.

---

## 8. Qué quedó fuera y estado de la máquina

**Suite: intérprete de Windows (`.venv-mcp-filex`, CPython 3.11.9), Docker
levantado, la suite entera y no solo mi módulo.**

| tanda | resultado | duración |
|---|---|---:|
| **antes** de tocar nada | `458 passed · 5 skipped · 0 failed · 130 subtests` | 359,40 s |
| **después**, máquina contendida | `470 passed · 7 failed · 4 skipped · 175 subtests` | **1 340,20 s** |
| **después**, máquina tranquila | **`476 passed · 5 skipped · 0 failed · 175 subtests`** | 234,60 s |

Las **+18 pruebas y +45 subtests** son exactamente
`pruebas/test_grafo_rasteriza.py`; los saltos son los mismos cinco que antes.

**Los 7 fallos de la tanda de en medio son la trampa 101, y hay que contarlos.**
La tanda duró **×3,7** lo que la anterior y los siete fallos fueron
`test_gpu_lock` (2), `test_hito2` (4) y `test_bitrate_y_lock` (1) — **los siete
diciendo `la tarjeta está ocupada` o `no se pudo tomar el lock de GPU`**, porque
el otro carril tenía el lock legítimamente tomado. **No es un fallo: es C38
funcionando**, y es literalmente el caso (a) de la trampa 101 reproducido.

Lo comprobé como manda el corolario de esa trampa —*antes de culpar al cambio,
comprueba si el cambio tocó código*—: `git diff --name-only` da
`filex/motor_contenedor.py` y los tres `filex/sondeo/doc_*.json`, **ni una línea
de `gpu.py`, `motores.py` ni nada de ffmpeg**. Con el lock libre
(`filex-gpu.lock` inexistente, 1 964 MiB de VRAM en uso) los tres módulos dan
**66 passed / 1 failed**, y ese último —`test_hito2.py:404`— **pasa al ejecutar
su módulo solo** (`37 passed`): es interferencia entre módulos por el estado del
mutex, no del cambio. La tanda limpia posterior lo confirma: **0 failed**.

**Los cinco saltos, uno a uno.** Ninguno es mío y ninguno cambia con este trabajo:

| prueba | motivo |
|---|---|
| `test_cerrojo.py:532` | no hay dos volúmenes distintos a mano |
| `test_hito4.py:221` | el predicado insatisfacible de §7 |
| `test_hito6.py:186` | falta el ráster de `bench/salidas-hito6/preparar_h6.py` |
| `test_hito6.py:697` | necesita la tarjeta: `FILEX_PRUEBAS_SIDECAR=1` |
| `test_watcher_n.py:130` | no hay `wsl.exe`: no se puede medir POSIX |

**`ci/integridad.py`: 8 de 9 comprobaciones OK, y la que falla no la puedo
arreglar.**

```
OK  citas · inventario · un-emoji-por-fila · trampas · manifiestos
OK  secretos · binarios · en-curso
MAL informes-registrados → rasteriza-declaradas.md
```

`informes_registrados()` exige que cada `bench/*.md` aparezca citado en
`ESTADO-Y-REPARTO.md`, **y mi encargo me prohíbe tocar ese fichero** («es del
consolidador»). El único informe que falta es el mío. **Queda declarado como
bloqueo, no sorteado:** basta una línea en la tabla de §1 del inventario, y es
del consolidador. Todo lo demás pasa, incluidos `manifiestos` (`0 nuevos`) y
`binarios` (`0 binarios sueltos nuevos`).

**Y un aviso de método que casi me cuesta la regla §6:** un `git add -A` metió
en el índice los **40 ficheros de `out/` y las 4 semillas de `entradas/`**, y
`ci/integridad.py` **dio `OK` en `binarios`** — su comprobación busca binarios
*sueltos*, y los míos estaban dentro de un `bench/salidas-*` que ya tenía
`MANIFIESTO.md`. **El trinquete no cubre este caso.** Se quitaron del índice y
se borraron a mano; lo que queda versionado son los `.py`, los `.json` de
resultados, los logs y el `MANIFIESTO.md` con la orden que reproduce el resto.

**Estado de la máquina (trampa 101).** El resondeo corrió con Docker sirviendo
solo a este carril; hay **otro carril midiendo con la GPU**, que no comparte
recurso con esto salvo CPU y el lock de la tarjeta —que yo no tomo—. Las cifras
de `ms` de esta tanda son **comparables entre sí y no comparables con las de
rondas anteriores**: mi `pandoc html→epub` da 1 308 ms donde worker7 midió
721,8, **×1,81 sobre la misma arista y el mismo contenedor**, que es la
advertencia de `CLAUDE.md` §3 al pie de la letra. **Por eso nada de este informe
cuelga de un milisegundo**: el resondeo se juzga por el veredicto del contrato,
que es relativo a sí mismo, y ése reproduce 40 de 40.

**Finales de línea, porque se pagó en esta ronda.** `_sellar.py` escribía con el
`open()` por defecto de Windows y los tres JSON salieron en **CRLF**, contra el
`* text=auto eol=lf` del `.gitattributes` — que documenta con número lo que eso
cuesta: **3 002 de 3 006 rojos que eran puro CR**. Se detectó porque el diff
declaraba los tres ficheros modificados **enteros**. Arreglado con
`newline="\n"` explícito en los dos arneses. Y el intento de arreglarlo *por la
shell* volvió a caer en la **trampa 19** —los backslashes se comen y el fichero
quedó con un `SyntaxError`—: se arregló con la herramienta de escritura, que es
lo que la trampa manda.

**Lo que NO hice:**

- **No toqué la GPU** ni tomé su lock, como pide el encargo.
- **No toqué `ESTADO-Y-REPARTO.md`**, `filex/confinamiento.py`, `filex/nucleo.py`,
  `filex/servicio.py` ni `pruebas/test_hito4.py`.
- **No remedí las `_MEDIDAS`** (10 de LibreOffice, 15 de Pandoc, 8 de Calibre):
  no las gobierna ninguna huella, §3.3. Es una diferencia de alcance deliberada
  con worker7 y está argumentada, no omitida.
- **No barrí las otras 7 aristas de Calibre** buscando no-determinismo, §6.
- **No arreglé `test_hito4`**, §7.

---

## 9. Para el inventario (no toco `ESTADO-Y-REPARTO.md`)

- `_DECLARADAS` ya puede decir la verdad sobre `rasteriza`: es un `dict`
  `{(o,d): rasteriza}` con el valor obligatorio, en las tres clases y en la base.
- `pptx→png` y `svg→png` entran al grafo con `rasteriza=True`. Grafo: 230 → 232
  aristas, 7 → 9 rasterizadoras.
- Auditoría de las tres tablas: **0 de 38 aristas declaradas mentían**; el
  comentario de `pandoc` acertaba el hecho y erraba la causa, y ahora es una
  medida.
- Resondeo real de **40 aristas**: 40/40 `rc=0`, **40/40 veredicto reproducido**,
  0 huérfanos. Los tres `filex/sondeo/doc_*.json` reseñados con huella nueva y
  `nota_huella` que distingue resondeo de resello.
- **Corrige el encargo:** el daño previsto («el planificador elegiría un camino
  que rasteriza sin pagar +1000») **no ocurre hoy** — 0 caminos elegidos cambian;
  lo que se pierde son 7 de 18 rechazos explicados.
- **Bloqueo declarado, no resuelto:** `pruebas/test_hito4.py:221` tiene un
  predicado insatisfacible por construcción y se salta siempre. Es de otra rama;
  el arreglo está descrito en §7.
- **Aviso para quien compare bytes:** `calibre epub→epub` no es determinista
  (4 `sha256` en 4 corridas, ×7,97 en bytes).
- **Falta una línea en la tabla de §1 del inventario**: `rasteriza-declaradas.md`.
  Es la única comprobación de `ci/integridad.py` que no pasa y no la toco porque
  el encargo me prohíbe editar `ESTADO-Y-REPARTO.md`.
- **Y un hueco del trinquete, de propina:** `ci/integridad.py` da `OK` en
  `binarios` con 44 binarios regenerables en el índice, porque solo busca
  binarios **sueltos** y los míos estaban dentro de un `bench/salidas-*` con
  `MANIFIESTO.md`. La regla §6 no está cubierta para ese caso. No lo arreglo
  —`ci/` no es mío— pero conviene saberlo.

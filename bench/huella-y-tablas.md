# N15 — la huella y las TABLAS de datos

**Agente X · 2026-08-28 · rama de worktree aislado**

Encargo: cerrar la **trampa 49** —*«el cierre de llamadas de la huella hashea el
CÓDIGO que decide, no los DATOS que ese código lee»*—, entendiendo primero **por
qué** el autor de `filex/huella.py` creía que las constantes entraban y el agente
V midió que `EXT_FAMILIA` no entraba.

Ficheros tocados: `filex/huella.py`, `pruebas/test_sondeo.py`, el campo `huella`
de los cinco `filex/sondeo/*.json`, y `bench/salidas-huella/` (arneses y
resultados). **No se ha tocado `filex/verificador.py`** — ni ha hecho falta.

---

## 0. Lo que sale de aquí, en ocho líneas

1. **La trampa 49 EXAGERA, y el docstring de `huella.py` también se equivocaba:
   ninguno de los dos tenía la frontera bien.** Las cinco tablas que la trampa
   nombra **sí estaban en el cierre**; de las cinco, **`FIRMAS` y `MARCAS_FTYP`
   ya caducaban** el sondeo. El agujero era de **3 de 5**, no de 5 de 5 (§2).
2. **La frontera real es el SITIO DEL VALOR, no su tipo.** Una tabla declarada
   vacía (`EXT_FAMILIA = set()`) y poblada por un `for` de nivel superior se
   hasheaba **vacía**: `_tabla()` solo miraba `FunctionDef`, `ClassDef` y
   `Assign` (§2.2).
3. **Y había un SEGUNDO agujero que nadie había mirado, en el componente
   `motor`:** `HILOS`, `MARGEN_TOPE`, `TIMEOUT_DENTRO`, `_HILO` y la función
   `entorno()` no movían nada — y `TIMEOUT_DENTRO` es el tope que corre DENTRO
   del contenedor, que decide el `rc` de toda arista documental (§3).
4. **Un solo arreglo cierra los dos**, y es el mismo cierre de nombres con otra
   entrada. **+196 líneas de cobertura sobre `verificador.py` y cero falsos
   positivos nuevos** (§4).
5. **Coste: ×1,25 en frío dentro de la misma tanda**, ×1,13 la primera huella,
   sin cambio medible en caliente. **Y el ×1,59 contra las cifras de D1 es
   falso**: esta tanda entera va ×1,59 más lenta (§6).
6. **Validado contra la historia: `2f2fba0` —el commit que arregló
   `EXT_FAMILIA`— mueve la huella nueva y NO movía la vieja.** Es la trampa 49
   reproducida sobre el commit real que la produjo (§5.1).
7. **REFUTACIÓN de mi propia ganancia: en el componente `motor`, sobre las 9
   filas de la historia real, viejo y nuevo dan EL MISMO veredicto.** Ese
   agujero es real y **nunca se ha disparado**: la ganancia ahí es preventiva,
   no retrospectiva, y hay que decirlo así (§5.2).
8. **NO hay que resondear.** Se resella —el código medido es el mismo y se
   demuestra antes de tocar nada—; el grafo sigue en **210 `real`, 5 `nominal`,
   `caducados: {}`** (§7).

---

## 1. Método y confinamiento

Todo lo de aquí se calcula **sobre texto y AST**: ni un motor externo, ni la GPU,
ni el corpus. Los dos únicos arneses que tocan el disco del proyecto
(`resellar.py`, `sin_arreglo.py`) escriben en `filex/sondeo/` y en
`filex/huella.py`, y el segundo **restaura comparando `sha256`** en un `finally`.
Los dos que miden tiempo trabajan en **directorio desechable**, listado antes y
después (R21); no apareció ningún fichero no pedido en la raíz.

**El corpus del worktree venía en punteros de LFS** (`tipico.png` a 130 B en vez
de 42 855). `git lfs checkout` lo arregló *antes* de creerse ningún rojo — es la
trampa 34, y sigue pasando en cada worktree nuevo.

Las pruebas de forma van **sobre el AST**, nunca sobre texto (trampa 42).

---

## 2. El mecanismo, sondeado en ejecución — MEDIDO

El encargo pedía entender **por qué**, no arreglar a ciegas. El sondeo es
`bench/salidas-huella/censo_alcance.py`: para cada tabla, **muta un elemento
real de su contenido en el fuente y mira si `de_alcance()` se mueve**. No se
deduce nada de leer `_tabla()`.

### 2.1 Las cinco tablas SÍ estaban en el cierre — la trampa 49 exagera

`nombres_alcanzados()` sobre el `verificador.py` de HEAD devuelve **114
nombres**, de los cuales **40 son constantes de módulo**. Las cinco de la
trampa 49 están las cinco dentro. Lo que decide no es estar, sino qué se hashea
al estar:

| Tabla | ¿en el cierre? | Cómo se define | **¿caduca el sondeo?** |
|---|:--:|---|:--:|
| `FIRMAS` | sí | literal (`FIRMAS = [ … ]`) | **SÍ** |
| `MARCAS_FTYP` | sí | literal (`MARCAS_FTYP = { … }`) | **SÍ** |
| `EXT_TABULARES` | sí | literal | **SÍ** |
| `EXT_A_FIRMAS` | sí | `= {}` + `for` (líneas 398-556) | **NO** |
| `EXT_FAMILIA` | sí | `= set()` + `for` (líneas 570-574) | **NO** |
| `EXT_SIN_FIRMA` | sí | `= {}` + `for` (589-615, 617-619) | **NO** |

Control positivo en la misma tanda: mutar `verificar` o `punto1_estado` **sí**
caduca. Control de ruido: **un comentario nuevo no caduca** (huella
`6af6b556299be217` antes y después, con el `sha256` crudo moviéndose de
`d1b63439d74a` a `c17d1df1990e`), y **tocar `fidelidad_audio` tampoco**.

**Así que la formulación de la trampa 49 —*«son tablas de módulo, no llamadas»*—
no es el mecanismo.** `_tabla()` registra los `Assign` de nivel superior desde
el primer commit; el ejemplo del docstring (`EXT_TABULARES`) era correcto. Lo
que la trampa acertó es el HECHO —arreglar `EXT_FAMILIA` no caducó nada— y lo
que erró es la CAUSA, y con ella el alcance del arreglo.

### 2.2 La frontera real: el sitio del valor

`_tabla()` recorría `arbol.body` y solo reconocía `FunctionDef`, `AsyncFunctionDef`,
`ClassDef`, `Assign` y `AnnAssign`. **Toda sentencia ejecutable de nivel superior
quedaba fuera de la tabla, y por tanto fuera de cualquier cierre.** En
`verificador.py` son cinco, **196 líneas**:

| Sentencia | Líneas | Puebla | ¿la ve el cierre nuevo? |
|---|---:|---|:--:|
| `for` 398-556 | 159 | `EXT_A_FIRMAS` (338 extensiones) | sí |
| `for` 570-574 | 5 | `EXT_FAMILIA` (42 extensiones) | sí |
| `for` 589-615 | 27 | `EXT_SIN_FIRMA` | sí |
| `for` 617-619 | 3 | poda de `EXT_SIN_FIRMA` | sí |
| `if __name__ …` | 2 | *(nada de módulo)* | **no, a propósito** |

El `Assign` que sí se hasheaba era literalmente `EXT_FAMILIA = set()`: idéntico
antes y después del arreglo de V, porque **su contenido nunca vivió ahí**.

`invocacion.py` **no tiene el problema** —se hashea el fichero entero— y tampoco
tiene ni una sentencia ejecutable de nivel superior. Es coherente.

---

## 3. El SEGUNDO agujero, que la trampa 49 no vio — MEDIDO

La trampa 49 miró solo el componente `contrato`. `cadena_de_clase()` hashea las
`ClassDef` y sus bases por MRO, así que **las constantes y funciones de módulo
que esas clases leen tenían el mismo agujero, y peor**: aquí no hacía falta un
bucle, bastaba con ser una constante.

Censo (`bench/salidas-huella/censo_motor.py`): nombres de nivel superior
**referenciados por alguna clase de motor y no hasheados**:

| Fichero | Invisibles a la huella |
|---|---|
| `filex/motores.py` | `HILOS` |
| `filex/motor_contenedor.py` | `MARGEN_TOPE`, `TIMEOUT_DENTRO`, `_HILO`, **`entorno()`** |

`TIMEOUT_DENTRO` y `MARGEN_TOPE` fijan el `timeout -k` que corre **dentro** del
contenedor —la defensa de la §3 de `CLAUDE.md`, *«el tope tiene que estar DENTRO
del contenedor»*—, y decide el `rc` de las 3 aristas documentales de cada motor.
`entorno()` es una **función**, no una constante: el agujero no era ni siquiera
específico de los datos.

Control positivo, con la huella de **producción** reproducida
(`bench/salidas-huella/control_motor.py`):

| Constante mutada | fichero | viejo caduca | **nuevo caduca** |
|---|---|:--:|:--:|
| `HILOS` | `motores.py` | **no** | **sí** |
| `MARGEN_TOPE` | `motor_contenedor.py` | **no** | **sí** |
| `TIMEOUT_DENTRO` | `motor_contenedor.py` | **no** | **sí** |
| *(control de ruido)* un comentario en `motores.py` | | no | **no** |

### 3.2 La granularidad por motor sobrevive — y hay que enseñarlo, no afirmarlo

El riesgo del arreglo es evidente: si el cierre de cada clase se traga el
fichero, tocar ffmpeg caducaría ImageMagick, que es justo el defecto que la
huella por clase venía a evitar. **MEDIDO**
(`bench/salidas-huella/alcance_por_clase.py`):

| Fichero | nombres de nivel superior | cierre de cada motor |
|---|---:|---|
| `motores.py` | 8 | **3** (`Motor`, `HILOS`, la propia clase) |
| `motor_contenedor.py` | 17 | **15** |

En `motores.py` **ImageMagick no alcanza a Ghostscript ni a FFmpeg**: la
granularidad queda intacta. En `motor_contenedor.py` los tres documentales
alcanzan casi todo, **pero ahí no había granularidad que perder**: los tres
comparten `_EnContenedor` entera por MRO desde el hito 5, y los dos nombres que
sobran son las clases hermanas.

---

## 4. El arreglo, y su granularidad justificada

Dos cambios en `filex/huella.py`, ninguno en `verificador.py`:

1. **`_tabla()` devuelve una LISTA de nodos por nombre**, y adjunta cada
   sentencia ejecutable de nivel superior a **los nombres de módulo que MUTA**.
   `_mutados()` es conservador con la misma filosofía que `_referidos()`: todo
   `Name` en contexto `Store`/`Del`, y todo `X` que reciba un método o un
   subíndice. Un nombre de más solo añade sensibilidad; uno de menos deja pasar
   un cambio que decide.
2. **`_clases_de_fichero()` hashea el cierre desde el nombre de la clase**, no
   la `ClassDef` suelta. Misma maquinaria, otra entrada.

Y una tercera pieza pequeña que no es cosmética: `_sello()` concatena los nodos
de un nombre **en su orden de aparición**, porque `EXT_SIN_FIRMA` se llena en un
bucle y se poda en el siguiente y **permutarlos cambia la tabla**. Hay prueba.

### 4.1 Por qué no el fichero entero — con número

*Hashear el fichero entero es la respuesta fácil y es la mala.* El número
(`bench/salidas-huella/granularidad.py`), sobre `verificador.py`, 5.421 líneas:

| Opción | nombres | líneas cubiertas | un comentario caduca |
|---|---:|---:|---|
| **Fichero entero** | 179 | 5.421 (100 %) | **las 215 aristas** |
| Cierre **viejo** | 114 | 3.181 (58,7 %) | 0 |
| **Cierre nuevo** | **119** | **3.377 (62,3 %)** | **0** |

El arreglo **añade 196 líneas de cobertura (+6,2 % sobre el viejo) y no añade un
solo falso positivo**. Es la mitad buena del equilibrio de §2.8: más sensibilidad
donde decide, cero donde es ruido.

### 4.2 Lo que se dejó fuera a propósito

Una sentencia ejecutable de nivel superior que **no muta ningún nombre de
módulo** sigue sin entrar. El único caso en `verificador.py` es
`if __name__ == "__main__": main()`; meterlo **caducaría las 215 aristas cada vez
que se toque el CLI**, que es ruido puro. Queda declarado como el nuevo límite 6.

---

## 5. Validación contra la HISTORIA del repositorio — MEDIDO

Como validó D1: recorriendo commits reales con `git show` y calculando la huella
de cada versión con **los dos algoritmos** (`bench/salidas-huella/historia.py`).

### 5.1 Componente `contrato`: el commit que la trampa 49 denunció

| commit | `sha256` crudo | huella **vieja** | huella **NUEVA** | asunto |
|---|---|---|---|---|
| `c2f6a59` | `97323bd07ec9` | `7e3e6c6fe4140d26` | `43dede629fe3d884` | Hitos 3 y 4 |
| `67320b6` | cambia | `c18aef206f16668d` ← cambia | `f91f6866fa876905` ← cambia | Sondeo completo |
| `9f99cae` | cambia | `6af6b556299be217` ← cambia | `2e704b65856e9147` ← cambia | Arregla la sonda, mueve 8 aristas |
| **`2f2fba0`** | cambia | **`6af6b556299be217` = NO SE MUEVE** | **`5761de1dcf0ab811` ← CAMBIA** | **El commit de V que arregló `EXT_FAMILIA`** |

**La fila `2f2fba0` es el encargo entero en una línea.** Es el commit real que
movió el `punto1` de 3 de las 53 salidas del patrón oro, y el algoritmo viejo
devolvía el mismo `6af6b556299b` antes y después. El nuevo se mueve.

Y el control de ruido no se ha perdido: en las cuatro filas el `sha256` crudo se
mueve más veces que la huella, y un comentario nuevo sigue sin caducar nada
(§2.1).

### 5.2 REFUTACIÓN de mi propia ganancia en el componente `motor`

La primera tabla que saqué del componente `motor` decía que el algoritmo nuevo
detectaba cambios que el viejo no veía en **`2450766`** y en tres commits de
`motor_contenedor.py`. **Es falso, y el error era mío:** esa tabla usa
`de_clase_en_fuente()`, que **no recorre el MRO**, mientras que la huella de
producción (`cadena_de_clase()`) sí. Reproduciendo la huella de producción sobre
el fuente histórico (`bench/salidas-huella/historia_motor.py`):

| Fichero | filas de historia | commits donde **solo el nuevo** se mueve |
|---|---:|---:|
| `filex/motores.py` | 5 | **0** |
| `filex/motor_contenedor.py` | 4 | **0** |

**En las 9 filas los dos algoritmos dan el mismo veredicto.** `2450766` cambió
`Motor.sondear`, que es una clase base: el viejo ya lo cogía por MRO.

**Conclusión honesta: el agujero del componente `motor` es real —está demostrado
con la mutación de §3— pero NUNCA se ha disparado en esta historia.** Cada vez
que cambió una constante de módulo, cambió también alguna clase del MRO. La
ganancia ahí es **preventiva**, y publicarla como retrospectiva habría sido
exactamente lo que la trampa 38 llama medir la carrera equivocada y salir verde.
La ganancia **retrospectiva y demostrada** es la del componente `contrato`, fila
`2f2fba0`.

---

## 6. El coste — MEDIDO, y con una corrección metodológica

Primera medida, contra las cifras que D1 publicó en `deuda-sondeo.md` §2.7
(`bench/salidas-huella/coste.py`, n=9, testigos `limpia`):

| | D1 | esta tanda, huella nueva | ratio |
|---|---:|---:|---:|
| Primera huella del proceso | 168,93 ms | 222,61 ms | ×1,32 |
| Los 6 motores en frío | 162,04 ms | 257,27 ms | **×1,59** |
| Los 6 motores en caliente | 0,0028 ms | 0,0028 ms | ×1,00 |

**Ese ×1,59 es falso y no mide el arreglo.** *Las cifras absolutas de tandas
distintas no son comparables* (`CLAUDE.md` §3), y con un agente más en la
máquina la mía va más lenta. La medida correcta es **pareada dentro de la misma
tanda**, alternando las dos versiones —con el `huella.py` de HEAD montado en un
paquete `filex` desechable— (`bench/salidas-huella/coste_pareado.py`, n=9,
testigos `limpia`):

| | **viejo** | **nuevo** | ratio |
|---|---:|---:|---:|
| Primera huella del proceso | 245,82 ms | 277,99 ms | **×1,131** |
| Los 6 motores en frío | 257,59 ms | 321,91 ms | **×1,250** (+64,3 ms) |
| Los 6 motores en caliente | 0,0031 ms | 0,0035 ms | ×1,129 |

Los **257,59 ms** del algoritmo viejo frente a los **162,04** de D1 son la prueba
de que la tanda entera va ×1,59: **casi todo el «coste» de la primera tabla era
la máquina, no el código.**

Dos salvedades:

* **El +0,4 µs del caliente está por debajo del suelo de la tanda** y no debe
  publicarse como una diferencia (trampa 36). Lo que sí se sostiene: sigue
  siendo del orden del microsegundo y se paga **una vez por proceso**.
* Los **+64,3 ms de frío** son un **0,27 %** de un `FileX()` en frío (~23,6 s) y
  un **8,6 %** de uno en caliente (~750 ms), una sola vez.

---

## 7. ¿Hay que resondear? **NO** — y la prueba va antes del cambio

Cambiar el ALGORITMO cambia el valor de la huella aunque el código medido no
haya cambiado ni una letra, así que **los cinco ficheros de sondeo quedaron
caducados por construcción** y hubo que resellarlos. Eso sería indulgencia si el
código hubiera cambiado; aquí no, y **se demuestra antes de tocar nada**:

| | `diagnostico()` |
|---|---|
| **Antes de mi cambio** | `{"sin_huella": [], "caducados": {}, "build_distinto": []}` |
| Con el algoritmo viejo, huella guardada vs. calculada | **`diferencias()` vacía en los cinco ficheros** |
| **Después del resellado** | `{"sin_huella": [], "caducados": {}, "build_distinto": []}` |

Es el argumento de `deuda-sondeo.md` §3.3: **las medidas se tomaron con ESTE
código, así que se SELLAN, no se tiran.** El script
(`bench/salidas-huella/resellar.py`) **comprueba esa coincidencia por fichero y
se niega a resellar el que no la cumpla**, diciendo que hay que resondearlo.

Resellado por script, con `sha256` de antes y después
(`bench/salidas-huella/resellado.json`); sustitución **textual** de cada valor
para no reformatear 210 aristas:

| fichero | `sha256` antes | `sha256` después | `contrato` | `motor` |
|---|---|---|---|---|
| `doc_calibre.json` | `6ddaf432968df306…` | `9b90f564bce5a80f…` | `6af6b556299be217` → `5761de1dcf0ab811` | `3da2baca1ac6a142` → `5ccb326907e06e1e` |
| `doc_libreoffice.json` | `3665baef1ee6c8fb…` | `33bc2c00aa77d3c8…` | ídem | `1bff3e5f4b6bb247` → `ffe3c41451f77538` |
| `doc_pandoc.json` | `bae8f1fe1513e700…` | `7b11eab77a4dd49d…` | ídem | `a456af70d46d7aac` → `f750a96c5bcb196a` |
| `ffmpeg.json` | `918d9722601939b0…` | `d6dae33a8793e55f…` | ídem | `8f6a26c1b2ac3a5f` → `7ae39d39a9f5b509` |
| `imagemagick.json` | `cd6a0d4691f69076…` | `78d8fc7d996c8a48…` | ídem | `9021aa532cdfdc5a` → `277736c49b765989` |

*(Ese `sha256` de después es el del resellado. Los ficheros llevan además una
`nota_resellado` añadida en un segundo paso, así que el del árbol final es otro:*
`doc_calibre` `8aa31ecc2182225a…`, `doc_libreoffice` `ad857071e6440a21…`,
`doc_pandoc` `4ee7cee92031081f…`, `ffmpeg` `c5c38aa82500bddc…`, `imagemagick`
`7fc148ee95b673d8…`.*)*

**`invocacion` no se movió** (`3a2c16603bb46673` en los diez casos): ese
componente hashea el fichero entero con `normalizar()` y el arreglo no lo toca.

Cada fichero lleva ahora una `nota_resellado` que dice **que fue por cambio de
algoritmo y no por resondeo**. Es la trampa 44: la `nota_huella` que traían
seguía siendo cierta y ya no explicaba los valores escritos, y quien la leyera
habría deducido un resondeo que no existió.

**El grafo, después de todo:**

```
{"por_estado": {"real": 210, "nominal": 5}, "total": 215,
 "diagnostico": {"sin_huella": [], "caducados": {}, "build_distinto": []}}
```

**Cero minutos de máquina. No hay que resondear.**

---

## 8. Las pruebas: 6 fallan sin el arreglo, 38 pasan con él — MEDIDO

Clase nueva `TablasDeDatos` en `pruebas/test_sondeo.py`, 10 pruebas. Ejecutadas
con el `huella.py` de HEAD puesto en el disco y restaurado por `sha256` en un
`finally` (`bench/salidas-huella/sin_arreglo.py`):

| | con el arreglo | **sin el arreglo** |
|---|---|---|
| `pruebas/test_sondeo.py` | **38 passed** | 32 passed, **6 failed** |

Las seis que caen sin el arreglo:

* `test_tocar_el_BUCLE_que_puebla_la_tabla_SI_caduca_el_sondeo`
* `test_tocar_el_bucle_de_un_DICCIONARIO_tambien_caduca`
* `test_el_ORDEN_de_los_bucles_importa`
* `test_las_seis_tablas_reales_del_verificador_caducan_el_sondeo`
* `test_el_componente_MOTOR_ve_las_constantes_de_MODULO`
* `test_las_constantes_reales_de_los_motores_caducan_su_huella`

Las cuatro que pasan en los dos son controles de **no regresión** —granularidad
por motor, el bucle de lo no alcanzado, el contenido de las tablas—, y tienen
que pasar en los dos: son la mitad del equilibrio.

**Un fallo propio que hay que reportar.** `test_el_ORDEN_de_los_bucles_importa`
pasaba en la primera versión **por la razón equivocada**: mi permutación cortaba
un bucle por la mitad, la fuente no compilaba, `de_alcance()` devolvía
`nocompila:…` y el `assertNotEqual` salía verde. Es la trampa 38 exacta —dos
causas distintas con la misma pinta de éxito— y por eso no aparecía en la lista
de fallos sin el arreglo. Corregida: la prueba **compila las dos fuentes con
`ast.parse` antes de comparar**.

Y el requisito de la trampa 48 —*cuando publiques el tamaño de una tabla,
publica dos elementos de ella*— está como prueba, no como frase:
`test_las_seis_tablas_llevan_su_CONTENIDO_no_solo_su_tamano` comprueba dos
elementos reales de cada una de las seis (`.csv`/`.gltf` en `EXT_FAMILIA`,
`.png`/`.mp4` en `EXT_A_FIRMAS`, `.rgb`/`.g4` en `EXT_SIN_FIRMA`,
`.csv`/`.ndjson` en `EXT_TABULARES`, `b"isom"`/`b"avif"` en `MARCAS_FTYP`).

### Suite completa

**`260 passed, 1 failed, 6 skipped`** en 224 s. Partíamos de `251 passed,
6 skipped` y añadí 10 pruebas: **261 − 1**.

El fallo es `test_hito7.py::ApiDefensas::test_el_asa_llega_al_empezar`, un
**umbral de tiempo** (`assertLess(ms, 250)`, midió 417,2). **No es mío y es
ruido de máquina**: `test_hito7.py` no se ha tocado y no consulta la huella;
reejecutada aislada, **pasa**. Es la trampa 36 con otro traje: hay otro agente
en la máquina y esa prueba tiene el umbral pegado al suelo de ruido. Lo dejo
anotado como pendiente ajeno, no lo arreglo (no es mi fichero).

---

## 9. Qué sigue sin ver esta huella

Los seis límites de `huella.py` §2.8, con los cambios marcados:

1. **No es por CATEGORÍA.** Sin cambios: tocar la sonda de audio sigue caducando
   las aristas de imagen. Sigue siendo la concesión consciente.
2. **El cierre es ESTÁTICO.** Sin cambios en la naturaleza, **mejor en el
   alcance**: ahora también entra lo que un bucle de nivel superior escribe. Un
   `getattr`, una tabla de despacho construida en ejecución o un `importlib`
   siguen invisibles.
3. **No ve fuera de `filex`.** Sin cambios. Sigue **PENDIENTE** que el `build`
   cubra el intérprete y las bibliotecas.
4. **No ve los DATOS.** **Sin cambios, y conviene subrayarlo porque es justo la
   confusión que este encargo podía crear:** una tabla escrita **en el código**
   entra desde hoy; `bench/salidas-referencia/referencia.json` y el `corpus/`
   siguen fuera y **eso no cambia**. La huella es del código, no de los datos de
   entrada.
5. **Un fichero sin `huella` se aplica igual.** Sin cambios (regla de legado).
6. **NUEVO: una sentencia ejecutable de nivel superior que no muta ningún nombre
   de módulo sigue fuera**, y es deliberado (§4.2). Si algún día una de ellas
   muta un objeto **importado**, cae en el límite 3 y no la ve nadie.

Y uno que no estaba escrito y ahora sí: **la huella editada a mano la sigue
anulando entera** (límite 6 de D1, renumerado aquí como parte del 5). El
resellado por script con `sha256` de antes y después es la defensa de
procedimiento, no de código.

---

## 10. Pendientes que dejo abiertos

1. **`test_hito7.py::test_el_asa_llega_al_empezar` tiene el umbral pegado al
   suelo de ruido** (250 ms declarados; 417 medidos con otro agente en la
   máquina, 3,4 s aislada). No es mi fichero. **PENDIENTE de otro reparto.**
2. **`_mutados()` no distingue un método mutador de uno de consulta.** `X.get(k)`
   hace entrar la sentencia igual que `X.add(k)`. Es deliberado —conservador—
   pero significa que un `for` de nivel superior que solo LEE una tabla la
   arrastra al cierre. En `verificador.py` no ocurre; en un fichero futuro sí
   podría, y sería un falso positivo. **PENDIENTE de medir si alguna vez
   molesta.**
3. **El componente `contrato` sigue teniendo una sola entrada, `verificar()`.**
   El punto 5 vive dentro de la conversión, no de `verificar()`; si algún día
   `nucleo.py` decide parte del veredicto, la huella no lo verá. **PENDIENTE**,
   y no es mío (`nucleo.py` es del agente Y).

---

## 11. Propuestas de trampa para `CLAUDE.md` — **NO APLICADAS**

Rango 58-61, agrupadas para caber.

> **58. Una trampa puede acertar el HECHO y errar la CAUSA, y entonces su
> arreglo se queda corto — MEDIDO** (`bench/huella-y-tablas.md` §2). La trampa
> 49 denunció que *«`EXT_A_FIRMAS`, `EXT_FAMILIA`, `EXT_SIN_FIRMA`, `FIRMAS` y
> `MARCAS_FTYP` son tablas de módulo, no llamadas»*, y el hecho era cierto:
> arreglar `EXT_FAMILIA` movió 3 de las 53 salidas sin caducar una arista. Pero
> **las cinco estaban en el cierre**, y **`FIRMAS`, `MARCAS_FTYP` y
> `EXT_TABULARES` sí caducaban**: el agujero era de **3 de 5**. La frontera no
> era «tabla contra llamada» sino **el SITIO DEL VALOR**: una tabla declarada
> vacía y poblada por un `for` de nivel superior se hashea vacía. Quien hubiera
> arreglado *«que las tablas entren»* habría escrito código para un problema que
> no existía y **habría dejado el que sí**. **Antes de arreglar una trampa
> ajena, reproduce su medida y sondea su mecanismo: el hecho no implica la
> causa.** Corolario del mismo sitio: **el arreglo correcto apareció en un
> SEGUNDO componente que la trampa no miraba** —`HILOS`, `MARGEN_TOPE`,
> `TIMEOUT_DENTRO` y `entorno()` tenían el mismo agujero en la huella de motor,
> y `TIMEOUT_DENTRO` es el tope que corre dentro del contenedor.
>
> **59. Un ratio contra una cifra publicada en otro informe mide dos máquinas,
> no dos códigos — MEDIDO** (ídem §6). La huella nueva dio **257,27 ms** frente
> a los **162,04** que publicó D1: **×1,59**, y parecía el coste del arreglo.
> Medido **pareado dentro de la misma tanda**, el algoritmo **viejo** dio
> **257,59 ms** en esta máquina: el coste real es **×1,25**, y el resto era la
> tanda. Es la regla de §3 —*las cifras absolutas de tandas distintas no son
> comparables*— aplicada al caso que más invita a saltársela: **cuando compares
> tu versión con una cifra histórica, mide TAMBIÉN la versión histórica en tu
> tanda, o no publiques el ratio.**
>
> **60. Una prueba de AST puede pasar porque la fuente NO COMPILA — MEDIDO**
> (ídem §8). `test_el_ORDEN_de_los_bucles_importa` permutaba dos bucles cortando
> uno por la mitad; la fuente no compilaba, `de_alcance()` devolvía su valor de
> degradación `nocompila:<sha>` —distinto de cualquier huella válida por
> diseño— y el `assertNotEqual` **salía verde con el arreglo y sin él**. Se
> descubrió solo porque no aparecía en la lista de fallos esperados. Es la
> trampa 38 en el arnés de la huella y la 42 un nivel más abajo: **toda prueba
> que compare huellas de dos fuentes tiene que comprobar que las dos COMPILAN
> antes de compararlas** — el camino de degradación de un módulo bien escrito es
> también un camino de falso verde.
>
> **61. Un cambio de ALGORITMO de huella caduca todo lo sellado sin que el
> código medido haya cambiado, y la diferencia se demuestra ANTES de tocar
> nada — MEDIDO** (ídem §7). Resellar los cinco ficheros de sondeo es legítimo
> aquí y sería indulgencia en el caso contrario, y lo único que separa las dos
> cosas es una comprobación que hay que hacer **con el algoritmo viejo, antes de
> escribir**: si la huella guardada coincide con la que el algoritmo anterior
> calcula sobre el árbol de ahora, el código medido es el mismo y se **sella**;
> si no, ese fichero ya estaba caducado y hay que **resondearlo**. El script lo
> comprueba por fichero y se niega a resellar el que no cumpla. Con eso, cambiar
> el algoritmo costó **0 minutos de máquina** y el grafo siguió en **210 `real`,
> 5 `nominal`**. Y va acompañado, porque si no la trampa 44 muerde: **una
> `nota_huella` que sigue siendo cierta puede dejar de explicar los valores que
> tiene al lado**, así que el resellado deja escrito que fue por algoritmo y no
> por resondeo.

---

## 12. Reproducir

Todo desde la raíz del repositorio, sin GPU y sin motores externos:

```
python bench/salidas-huella/censo_alcance.py      # el mecanismo (sec.2)
python bench/salidas-huella/censo_motor.py        # el segundo agujero (sec.3)
python bench/salidas-huella/alcance_por_clase.py  # la granularidad (sec.3.2)
python bench/salidas-huella/control_motor.py      # control positivo (sec.3)
python bench/salidas-huella/historia.py           # historia, contrato (sec.5.1)
python bench/salidas-huella/historia_motor.py     # la refutacion (sec.5.2)
python bench/salidas-huella/granularidad.py       # la tabla de opciones (sec.4.1)
python bench/salidas-huella/coste_pareado.py      # el coste real (sec.6)
python bench/salidas-huella/resellar.py --comprobar   # sin escribir
python bench/salidas-huella/estado.py             # diagnostico() (sec.7)
python bench/salidas-huella/grafo.py              # 210 real, 5 nominal
python bench/salidas-huella/sin_arreglo.py        # las 6 que fallan (sec.8)
python -m pytest pruebas/test_sondeo.py -q        # 38 passed
```

`censo_alcance.py`, `historia*.py`, `granularidad.py`, `control_motor.py` y
`resellar.py` cargan `HEAD:filex/huella.py` en `_huella_head.py`, que es un
temporal regenerable y no se versiona.

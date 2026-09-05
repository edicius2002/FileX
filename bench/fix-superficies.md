# Dos defectos de superficie, arreglados: el hilo que esperaba 30 s por 5 bytes, y la bandera cuyo valor contaba como fichero

Carril `fix/superficies`, partiendo de `integra/cobertura`. Sujeto:
`filex/api.py` y `filex/cli.py`, **y nada más de `filex/`**.

Los dos defectos los localizó y midió el carril `cob/superficies`
(`bench/cobertura-superficies.md` §3.1 y §3.2), que los dejó con su caso
mínimo y sin parchear a propósito. Aquí se **reproducen antes de tocar nada**
(trampa 58: el hecho no implica la causa), se arreglan, y las dos pruebas que
afirmaban el comportamiento roto pasan a afirmar el correcto.

**Los dos están ARREGLADOS y los dos eran defectos de verdad.** Ninguno de los
dos resultó ser un espejismo del informe ajeno; lo que sí resultó equivocada
fue mi primera idea sobre cómo arreglar el segundo, y está en §2.2.

**Entrega:** `filex/api.py`, `filex/cli.py`, `pruebas/test_cob_superficies.py`
(77 → 82 pruebas), `bench/salidas-fix-superficies/` (dos arneses con su
control, sus JSON y el `MANIFIESTO.md`).

---

## 0. Lo primero, porque decide si algo de esto vale: la huella no se movió

**MEDIDO.** `api.py` y `cli.py` no están en el cierre de llamadas de
`verificar()` ni en la cadena de clases de ningún motor, así que **no deberían
caducar ni una de las 172 aristas selladas**. Eso se comprueba, no se supone
(trampas 32, 97 y 105: un refactor puro cae del lado que sí caduca, y para la
huella es indistinguible de un cambio semántico).

Los tres componentes de los cinco ficheros de `filex/sondeo/*.json`, **antes y
después**, con el mismo intérprete (`.venv-mcp-filex`, Windows, 3.11.9 — la
huella es función del intérprete, trampa 105):

| Motor | `motor` | `invocacion` | `contrato` | Aristas |
|---|---|---|---|---:|
| `doc_calibre` | `2291ddcd4246f75a` | `3a2c16603bb46673` | `fe41b4d52413299c` | 8 |
| `doc_libreoffice` | `ae44ff79d26ded79` | `3a2c16603bb46673` | `fe41b4d52413299c` | 16 |
| `doc_pandoc` | `f82b19cb9263ef45` | `3a2c16603bb46673` | `fe41b4d52413299c` | 16 |
| `ffmpeg` | `52bd204369ca3053` | `3a2c16603bb46673` | `fe41b4d52413299c` | 70 |
| `imagemagick` | `277736c49b765989` | `3a2c16603bb46673` | `fe41b4d52413299c` | 62 |

**15 de 15 componentes idénticos, 0 diferencias, 172 aristas intactas.** Los
quince valores de arriba son los de después; los de antes son **los mismos
quince**, y por eso hay una sola tabla en vez de dos: publicar dos columnas
idénticas habría sido más aparatoso y no más verificable.
`pruebas/test_sondeo.py`: **48 de 48, OK**.

Y publico también el número al lado de los hashes (trampa 48: un recuento
correcto no prueba un contenido correcto, pero un hash sin su recuento tampoco
dice cuántas medidas protege).

---

## 1. `api.py`: el cuerpo se leía dos veces, y la segunda esperaba 30 s

### 1.1 Reproducido antes de tocar nada

**MEDIDO.** Sobre `integra/cobertura` sin modificar, la prueba que el carril
anterior dejó escrita —`test_el_cuerpo_se_lee_dos_veces_y_el_segundo_read_no_
tiene_nada`— pasa en verde afirmando `pedidos == [5, 5]`: dos lecturas de cinco
bytes, y la segunda no tiene nada que leer. El mecanismo es el que describe
§3.1 del informe ajeno, tal cual.

### 1.2 Qué se cambió, y por qué no es «quitar la segunda lectura»

`_rechazo` descarta el cuerpo **a propósito**: con `keep-alive`, rechazar sin
consumirlo deja bytes en el socket y la petición siguiente se lee sobre la
mitad de la anterior — MEDIDO como `WinError 10053` en la primera pasada del
hito 7. Quitar esa lectura arregla un fallo y abre el otro.

Lo que se hizo es marcar el cuerpo como consumido:

* `Manejador._cuerpo_consumido`, atributo **de clase** con valor `False`.
* `_cuerpo` lo pone a `True` **justo después del `read(n)`**, no al rechazar:
  así vale también para el **tercer** camino, el `404` con que `do_POST` cierra
  una ruta desconocida, que es el único que no se ve desde `_cuerpo`.
* `_rechazo` lee sólo `if not self._cuerpo_consumido and 0 < n <= MAX_CUERPO`.

### 1.3 La trampa que casi me como: la marca es de la PETICIÓN, no del manejador

**Y esta es la parte que el remedio evidente no traía.** `BaseHTTPRequest
Handler` **reutiliza el mismo objeto** para todas las peticiones de una
conexión `keep-alive`. Con la marca puesta como simple atributo de instancia,
la secuencia *«petición 1: `POST` válido con cuerpo (se consume, marca a
`True`, la conexión NO se cierra) → petición 2 por el mismo socket: un `415`,
que rechaza antes de leer»* dejaría la petición 2 **sin descartar su cuerpo**:
el arreglo de un fallo habría reintroducido exactamente el `WinError 10053`
que la lectura de `_rechazo` existe para impedir.

Por eso hay un `handle_one_request` que rearma la marca en cada petición, y por
eso hay una prueba que ejercita esa secuencia **sobre un socket crudo**
(`test_la_marca_de_consumido_se_rearma_en_cada_peticion`), no sobre `urllib`:
la conexión tiene que gobernarla la prueba o no hay segunda petición que medir.
Es la forma de la trampa 65 al revés — aquí una defensa nueva podía tapar a la
vieja, y la única manera de saberlo era escribir la prueba de la vieja.

### 1.4 Rojo antes, verde después

| Prueba | Antes del arreglo | Después |
|---|---|---|
| `test_el_cuerpo_se_lee_UNA_sola_vez` | **FAIL** (`[5, 5] != [5]`) | ok |
| `test_los_tres_caminos_..._leen_el_cuerpo_UNA_vez` | **FAIL en los 3 subtests** | ok |
| `test_un_rechazo_ANTES_de_leer_sigue_descartando_el_cuerpo` | ok | ok |
| `test_la_marca_de_consumido_se_rearma_en_cada_peticion` | ok | ok |
| `test_un_cuerpo_vacio_no_lee_nada` | ok | ok |

Las dos filas de en medio **tienen que pasar en los dos lados**: son las
propiedades que el arreglo no puede romper, no la señal del arreglo. Que estén
verdes antes es lo que las hace útiles después. La traza del rojo está en
`bench/salidas-fix-superficies/rojo-antes.log` (8 rojos: 4 de `api` y 4 de
`cli`).

### 1.5 Por qué la prueba cuenta LECTURAS y no mira el reloj

La espera de 30 s es la **consecuencia**; la segunda lectura es el
**mecanismo**. Un umbral de tiempo dentro de la suite sería un rojo que depende
del estado de la máquina (trampas 101 y 123: hay seis agentes en este equipo y
un módulo que se acopla consigo mismo por CPU). Así que la aserción es
determinista —cuántas veces se lee el cuerpo— y **el reloj se mide aparte**, en
un arnés con su control positivo al lado.

`bench/salidas-fix-superficies/reloj.py`, con `_Vulnerable` —el `_rechazo` de
antes del arreglo, conservado a propósito (trampa 116: el control positivo de
un arnés no es una variante del doble, es el SUJETO CON EL DEFECTO)— y el
arreglado **en la misma tanda** (trampa 59). Plazo acortado a 3 s: lo que se
compara es «agota el plazo» contra «no lo agota», y con los 30 s de producción
la tanda costaría tres minutos y mediría lo mismo. Se publica el cociente
contra el plazo, no un tiempo absoluto (`CLAUDE.md` §3):

| Celda | Vulnerable | Arreglado |
|---|---:|---:|
| cuerpo que no es JSON (`400`) | **×1,006 del plazo** | ×0,001 |
| cuerpo que no es objeto (`400`) | **×1,001** | ×0,001 |
| ruta desconocida (`404`) | **×1,007** | ×0,003 |
| `415`, que rechaza ANTES *(control negativo)* | ×0,001 | ×0,001 |

**3 de 4 celdas agotan el plazo con el defecto, 0 de 4 con el arreglo**, y la
cuarta —el `415`, que rechaza antes de leer— no dispara en **ninguna** de las
dos configuraciones: si también se hubiera disparado, lo que estaría midiendo
el arnés sería el socket y no el defecto. **Las ocho celdas devuelven el código
HTTP correcto**, que es justo lo que hacía invisible el fallo: la respuesta era
buena, sólo llegaba tarde.

Consecuencia que se cierra: con `ThreadingHTTPServer` cada petición ocupa un
hilo, así que un cliente **sin autenticar** retenía un hilo 30 s con 5 bytes.
La API escucha en loopback por defecto, así que **no era una brecha**; era un
amplificador barato para quien ya estuviera en la máquina, y una espera de 30 s
para un cliente legítimo que mandara un JSON mal formado.

---

## 2. `cli.py`: el VALOR de una bandera contaba como posicional

### 2.1 Reproducido antes de tocar nada

**MEDIDO.** `test_defecto_el_VALOR_de_una_bandera_cuenta_como_posicional` pasa
en verde sobre `integra/cobertura`: `filex --raiz D a.png b.webp` sale con
`SystemExit(2)` y `filex --raiz D motores` también, con el error nombrando a
`convertir`. Los dos síntomas, la misma causa — el filtro
`[a for a in argv if not a.startswith("-")]` quita las banderas y no sus
valores.

### 2.2 Mi primer arreglo estaba mal, y lo dijo el parser

La corrección obvia es contar bien los posicionales y dejar el resto igual.
**Y el resto no puede quedarse igual.** La línea de antes anteponía el
subcomando a todo el `argv`:

```python
argv = ["convertir", *argv]
```

Con `--raiz` delante, eso produce `["convertir", "--raiz", "D", "a.png",
"b.webp"]`, y **MEDIDO**: `parse_args` sale con `SystemExit(2)` y
*«unrecognized arguments: --raiz b.webp»*, porque `--raiz` es del parser
principal y deja de reconocerse en cuanto va detrás del subcomando. Es decir:
contar bien los posicionales y no tocar nada más habría cambiado un
`SystemExit(2)` por **otro `SystemExit(2)`** — un arreglo con la pinta exacta
de un arreglo, y un caso que la prueba «sale 2» no habría distinguido.

Lo que se hizo: `_posicionales` devuelve también el **índice del primer
posicional**, y el subcomando se inserta ahí:

```python
argv = [*argv[:primero], "convertir", *argv[primero:]]
```

Con el `argv` de la forma corta desnuda `primero == 0`, así que la reescritura
histórica no cambia ni un token: la compatibilidad es por construcción, no por
suerte.

### 2.3 De dónde salen las banderas con valor: del parser, medido

El encargo pedía que la fuente fuera `construir_parser()` y no una lista a
mano —*«pero mídelo, no lo supongas: si consultar el parser antes de
`parse_args` no es viable, dilo»*—. **Es viable, y está medido**:
`_banderas_con_valor` recorre `parser._actions`, baja a los subparsers por
`argparse._SubParsersAction` y se queda con las opciones de `nargs != 0`.
Devuelve exactamente `{--params, --raiz, --timeout}`, y **no** `--json`, `-v`,
`--verboso`, `--version`, `-h` ni `--help`.

La deuda que esto sí tiene, y la digo: **`_actions` y `_SubParsersAction` son
API privada de `argparse`**. Se paga a sabiendas, porque la alternativa
—duplicar la tabla— es literalmente el fallo que se está arreglando, y porque
`test_las_banderas_con_valor_salen_del_PARSER_y_no_de_una_lista_a_mano` la
comprueba **en las dos direcciones** (trampa 73: audita las dos, las que están
y las que no deberían estar), así que una versión de Python que mueva esos
nombres se vería como un rojo y no como un silencio.

### 2.4 El alcance, entero: qué gana, qué no cambia y qué SIGUE sin funcionar

`bench/salidas-fix-superficies/argv.py` compara el detector viejo y el nuevo
sobre 15 formas de `argv`, **al nivel de la detección**, con el viejo
conservado como control positivo. `discrimina: true`, `pierden: []`.

**Gana 5:**

| Forma | Antes | Ahora |
|---|---|---|
| `filex --raiz D a.png b.webp` | `SystemExit(2)` | `convertir` |
| `filex --raiz=D a.png b.webp` | `SystemExit(2)` | `convertir` |
| `filex a.png b.webp --params '{...}'` | `SystemExit(2)` | `convertir` |
| `filex a.png b.webp --timeout 5` | `SystemExit(2)` | `convertir` |
| `filex --raiz D motores` | `SystemExit(2)` *(reescrito a `convertir`)* | `motores` |

Las dos de `--params`/`--timeout` **no estaban en el informe de origen**: son
el mismo defecto por la puerta del subparser, y aparecieron al variar la
entrada en vez de repetir sus filas (trampa 69).

**No pierde ninguna**, y las que siguen dando `SystemExit(2)` en los dos lados
son tres, de las que **sólo una es una limitación**:

* `filex a.png` y `filex a.png b.webp c.gif` — **no son defectos**: la forma
  corta es de exactamente dos posicionales, y su `2` es el error de USO
  correcto. Lo digo porque la etiqueta del JSON invita a leerlas como rotas, y
  un campo honesto con un nombre engañoso se lee como una respuesta honesta
  (trampa 44); por eso el arnés las separa en `rechazados_en_los_dos` y
  `limitacion_que_queda`.
* **`filex a.png b.webp --raiz D` — ESTO SÍ, y queda PENDIENTE.** La bandera
  global detrás de los posicionales sigue sin funcionar: el subcomando se
  inserta antes de `a.png` y `--raiz` acaba, otra vez, detrás de `convertir`.
  Fallaba antes y falla ahora, así que **no es una regresión**, pero tampoco
  está cerrado. El remedio sería mover las banderas del parser principal al
  frente del `argv`, y **no lo he hecho**: reordenar los argumentos del usuario
  es una decisión más grande que contar bien, y la ronda pedía dos arreglos
  localizados.

### 2.5 Y una prueba que no me pidió nadie: que la raíz siga confinando

«`--raiz D a.png b.webp` ya funciona» es compatible con haber colado `--raiz`
dentro del subparser y **perderla por el camino**: la orden analizaría
sintácticamente igual de bien y el confinamiento no existiría. Es la forma de
la trampa 118 —una afirmación sobre lo que un valor CONCEDE hay que
comprobarla con el valor delante—, así que
`test_la_forma_corta_con_raiz_SIGUE_confinando` mete una entrada de fuera de la
raíz por la forma corta y exige `rc == 1`, que no se escriba la salida, y que
el mensaje no nombre la carpeta ajena (R4).

### 2.6 Rojo antes, verde después

| Prueba | Antes | Después |
|---|---|---|
| `test_el_VALOR_de_una_bandera_ya_no_cuenta_como_posicional` | **ERROR** (`SystemExit(2)`) | ok |
| `test_la_forma_corta_con_raiz_SIGUE_confinando` | **ERROR** (`SystemExit(2)`) | ok |
| `test_una_bandera_del_subcomando_con_valor_tampoco_cuenta` | **ERROR** (`SystemExit(2)`) | ok |
| `test_las_banderas_con_valor_salen_del_PARSER_...` | **ERROR** (`AttributeError`) | ok |

---

## 3. Lo que se ejecutó, con sus cuatro declaraciones

El recuento de una suite necesita **intérprete, entorno, qué quedó fuera y el
estado de la máquina** (trampas 94, 101 y 104):

* **Intérprete:** `.venv-mcp-filex/Scripts/python.exe`, Windows, 3.11.9, por
  ruta absoluta. Comprobado que `import filex` resuelve **a este worktree**.
* **Entorno:** sin GPU y sin tomar su lock; el corpus, materializado
  (`corpus/imagen/tipico.png` = 42 855 B tras `git lfs checkout` — llegó como
  puntero de 130 B, trampa 34).
* **Qué quedó fuera, y por qué:** **la suite entera NO se corrió**, por encargo
  explícito: hay otro carril en la máquina y seis suites a la vez fabrican la
  carga que pone roja `test_cancelacion_procesos` sin que nadie toque el código
  (trampas 101 y 123). La pasada íntegra la corre el maestro.
* **Estado de la máquina:** otro carril activo (`fix/verificador`).

| Módulo | Resultado |
|---|---|
| `pruebas.test_cob_superficies` | **82 OK** (eran 77; +5 netas) |
| `pruebas.test_hito7` | **42 OK** |
| `pruebas.test_hito1` | **44 OK** |
| `pruebas.test_sondeo` | **48 OK** |

`test_cob_superficies` y `test_hito7` son **los dos únicos módulos de la suite
que importan `filex.api` o `filex.cli`** —comprobado con `grep`, no supuesto—,
así que el radio de este cambio queda cubierto por lo ejecutado.

---

## 4. Lo que rompí midiendo, y que es una trampa nueva

**MEDIDO, y me lo hice yo.** Para comprobar que el procedimiento de reversión
del `MANIFIESTO` funcionaba, restauré `filex/api.py` y `filex/cli.py` desde sus
blobs previos… **con el arreglo aún sin commitear**. El `git status --porcelain
-- filex/` de control salió **vacío**, que era la respuesta correcta y
significaba lo peor: el árbol había vuelto a `HEAD`, y `HEAD` era el código sin
arreglar. **El único ejemplar del arreglo estaba en el árbol de trabajo y lo
acababa de sobrescribir.**

No costó nada porque las ediciones eran reproducibles, y el control de
identidad —preguntarle al módulo qué código tiene dentro con
`inspect.getsource`, que es lo que la trampa 119 prescribe— dijo la verdad en
los dos sentidos: `False` tras revertir, `True` tras rehacerlo. Pero el
enunciado que queda es más ancho que el de la 119:

> **Un A/B entre dos versiones de un fichero necesita que la versión NUEVA
> también esté guardada en algún sitio, no sólo la vieja.** La trampa 119 avisa
> de que `git stash push` sobre un fichero commiteado no hace nada; el reverso
> es que `git checkout <blob>` sobre un fichero **no** commiteado hace
> demasiado. **Se commitea el arreglo ANTES de correr el A/B que lo compara con
> el código de antes**, o el experimento se lleva por delante a su propio
> sujeto. Y el `git status` limpio, que parece el control de que todo está en
> orden, es aquí justo la señal de que ya no lo está.

---

## 5. Lo que dejo PENDIENTE, y una corrección que propongo y no aplico

**PENDIENTE 1 — `filex a.png b.webp --raiz D`.** Documentado en §2.4 con su
medida. No es una regresión y no lo he cerrado; el remedio conocido —reordenar
el `argv` del usuario— es una decisión de más calado que la de esta ronda.

**PENDIENTE 2 — el arnés de discriminación del carril anterior queda caducado
en tres filas, y NO lo he tocado.** `bench/salidas-cobertura-superficies/
discriminacion.py` cita por nombre pruebas que aquí se renombran, y una de sus
mutaciones cita texto de `api.py` que aquí cambia. Tres filas de sus 72:

| Fila | Qué cita | Por qué ya no vale |
|---|---|---|
| `api.py`, *«el rechazo deja de descartar el cuerpo»* | el texto `if 0 < n <= MAX_CUERPO:\n            try:\n                self.rfile.read(n)` | esa línea es ahora `if not self._cuerpo_consumido and 0 < n <= MAX_CUERPO:` |
| ídem | `ApiCuerpoLeidoDosVeces.test_el_cuerpo_se_lee_dos_veces_...` | la clase es `ApiCuerpoLeidoUnaSolaVez` y el método `test_el_cuerpo_se_lee_UNA_sola_vez` |
| `api.py`, *«un cuerpo que no es un objeto JSON pasa al servicio»* | el mismo nombre de prueba | ídem |

**No las he corregido** porque el `.json` de al lado es la MEDIDA de su autor
—72 de 72 sobre el código de antes— y editar el arnés sin reejecutarlo dejaría
harness y medida diciendo cosas distintas, que es peor que la caducidad. El
texto de reemplazo, para quien lo reejecute: la primera mutación pasa a
`("api.py", "if not self._cuerpo_consumido and 0 < n <= MAX_CUERPO:", "if
False:", ...)` y las tres referencias de prueba, a los nombres nuevos. El fallo
es **benigno por diseño**: el propio arnés exige que la mutación sea única y
saca `MUTACION_NO_UNICA` cuando el texto aparece 0 veces, así que degrada a un
rojo visible y no a un falso «discrimina» (trampa 116 evitada por su autor).

**PENDIENTE 3 — la corrección que propongo para `bench/cobertura-superficies.md`
y no aplico** (es de su autor). Su §3.1 dice *«el remedio evidente es que
`_cuerpo` marque el cuerpo como consumido»*, y el remedio evidente **está
incompleto**: sin rearmar la marca en cada petición de una conexión
`keep-alive`, reintroduce el `WinError 10053` que la lectura de `_rechazo`
existe para impedir (§1.3). Texto propuesto para esa frase:

> El remedio —que no se aplica aquí— es que `_cuerpo` marque el cuerpo como
> consumido, **y que esa marca se rearme en cada petición**: el manejador se
> reutiliza a lo largo de una conexión `keep-alive`, así que una marca de
> instancia sin rearme dejaría a la petición siguiente rechazando sin
> descartar su cuerpo, que es el `WinError 10053` de vuelta.

Y su §3.2 acierta el hecho y se queda corto en el remedio por el mismo motivo
que §2.2: contar bien los posicionales **no basta**, porque anteponer
`convertir` a todo el `argv` deja `--raiz` detrás del subcomando y produce otro
`SystemExit(2)`. No es un error suyo —el informe describe el defecto, no el
parche—, pero quien leyera sólo esa sección escribiría el arreglo que no
funciona.

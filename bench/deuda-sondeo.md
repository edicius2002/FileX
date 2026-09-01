# Las dos deudas de `filex/sondeo.py`

**Agente D1 · 2026-08-23 · a solas** (lo que se toca aquí caduca el sondeo de
todo el proyecto a la vez). Sin GPU.

**Resumen:** la deuda 1 se cierra con una huella de tres componentes sobre el
**AST normalizado**, granular **por motor**, que valida contra la historia real
del repositorio. La deuda 2 **queda refutada en magnitud: 0 de 129 pruebas
dependen del estado del sondeo en disco**, medido moviendo 153 aristas debajo de
ellas sin que se inmute ni una. Las **210 aristas `real` siguen intactas**, con
la misma firma `sha256` antes y después.

---

## 1. Lo que había, medido antes de tocar nada

| Testigo | Valor | Cómo |
|---|---|---|
| Suite | **123 passed, 6 skipped** (129), 67,39 s | `python -m pytest pruebas/ -q` |
| Grafo | **210 `real`, 5 `nominal`, 0 `sin_sondear`** (215) | `sondear_todos()` |
| Firma del grafo | `b72858bdf750c2c2707ad572c59736c71998f5eca27b2f343599f8a9351d91be` | `sha256` de las 215 aristas `motor\|o>d\|param\|estado` |
| Sondeo en disco | 5 ficheros, **171 `real` + 2 `nominal`** | `filex/sondeo/*.json` |

Las 210 no salen todas del disco: **57 las declara el CÓDIGO** con evidencia de
`referencia.json` y `sonda.json`, y **153 las superpone el disco**. Ese reparto
es el que hace medible todo lo que sigue.

---

## 2. DEUDA 1 — el sondeo caduca al cambiar el código

> **PENDIENTE:** meter una huella del código que decide la arista —`motores.py`
> y `verificador.py`— junto al `build`.

### 2.1 La trampa, y por qué no se cae en ella

Comparar una huella como se compara el `build` habría invalidado los cinco
ficheros de golpe: **el grafo caería de 210 aristas `real` a 57**. Y sería
además incorrecto, porque esas medidas **se tomaron con el código de ahora**
(§3.3). Lo que hay que hacer es **sellarlas**, no tirarlas. Hecho.

### 2.2 Huella de QUÉ: tres componentes, y cada uno con su granularidad

Vive en **`filex/huella.py`**. Se hashea el **AST normalizado**, no el fichero:
`ast.dump(..., include_attributes=False)` sin docstrings, y los comentarios ya no
existen en un AST. Así, **mover una función de sitio o arreglar una falta de
ortografía no caduca nada**.

| Componente | Qué hashea | Granularidad |
|---|---|---|
| `motor` | La CLASE del motor y sus bases **dentro de `filex`**, en orden de MRO | **Por motor** |
| `invocacion` | `filex/invocacion.py` entero | Global (200 líneas) |
| `contrato` | Las funciones de `verificador.py` **alcanzables desde `verificar()`** | Por contrato |

Se comparan **por separado**, y **lo que no coincide no se aplica: se degrada a
`sin_sondear`**, nunca a `nominal` — una medida que ya no vale no es prueba de
que la arista esté muerta.

**Las bases entran porque hacen falta:** `PandocEnContenedor` es un cascarón de
30 líneas y la lógica vive en `_EnContenedor`; una huella que solo mirase la
subclase no vería el cambio. Y aun compartiendo esa base, **los tres motores
documentales salen con huellas de `motor` distintas** (`dda90b2e…`, `28a9e681…`,
`9f5c1c38…`), que es justo lo que se quería.

### 2.3 El `contrato`: por qué el cierre de llamadas y no el fichero

El encargo lo plantea bien: *«`verificador.py` tiene más de 5.000 líneas: un
cambio en la regla de fidelidad de audio no debería caducar las aristas de
imagen»*. **La respuesta no necesita un mapa a mano** —que se queda obsoleto en
silencio, que es exactamente el fallo que veníamos a arreglar—: **la fidelidad no
decide la arista**, `verificar()` no la llama, y el cierre estático de llamadas
lo dice solo.

**MEDIDO** sobre `filex/verificador.py` (5.241 líneas, 166 nombres de nivel
superior contando funciones, clases **y constantes**):

| | Nombres | Líneas de nivel superior |
|---|---|---|
| **En** el cierre de `verificar()` — caducan el sondeo | **114 (68,7 %)** | 3.181 (71,8 %) |
| **Fuera** — no caducan nada | **52** | 1.250 |

Lo más gordo que queda fuera: `fidelidad_video` (149 líneas), `fidelidad_imagen`
(124), `main` (121), `fidelidad_pdf` (93), `png_tinta_cajas` (87),
`fidelidad_vectorial` (66), `svg_textos` (61), **`fidelidad_audio` (56)**,
`verificar_fidelidad` (53).

El cierre incluye **las constantes de módulo**, y no es un adorno:
`EXT_TABULARES` es una constante nueva y su llegada cambió el veredicto de 8
aristas.

### 2.4 ¿Entra `invocacion.py`? **SÍ — y la lista del docstring estaba corta por los dos lados**

El docstring nombraba «`motores.py` y `verificador.py`». **Le faltaban dos cosas:**

1. **`filex/invocacion.py` SÍ decide la arista.** Es el punto único de
   invocación: fija `stdin=DEVNULL`, el tope, el matar-el-árbol y el
   `arrancado` con el que se distingue «el motor rechazó» de «el binario no
   está». Cambiar cualquiera de esos mueve el `rc` de **toda** arista.
   Entra como componente propio, global. **El coste de esa globalidad está
   medido y es cero: `invocacion.py` ha cambiado 0 veces desde el commit
   inicial `a35ef8f`** (`git log -- filex/invocacion.py` da un solo commit).

2. **`motores.py` no es donde vive la mayoría del código de motor.** **3 de los
   5 ficheros de sondeo** —`doc_libreoffice`, `doc_pandoc`, `doc_calibre`— los
   decide `filex/motor_contenedor.py`, que el docstring ni menciona. Hashear la
   **clase y su MRO** cubre los dos ficheros sin nombrar ninguno, y cubrirá al
   siguiente motor que se descubra sin tocar nada.

Y un matiz de la cita original: *«se arreglaron la sonda **y la invocación**»* —
esa «invocación» **no fue `invocacion.py`**, fue la construcción del `argv` en
`motores.py` (el `-map 0:v:0` de `*→gif`). Los dos sitios entran en la huella,
pero por componentes distintos.

### 2.5 La huella, validada contra la HISTORIA del repositorio

No basta con que la huella cambie: tiene que cambiar **cuando toca**. MEDIDO
recorriendo los commits reales con `git show`:

**Componente `contrato`, sobre `filex/verificador.py`:**

| commit | huella de alcance | |
|---|---|---|
| `c2f6a59` | `7e3e6c6fe4140d26` | |
| `67320b6` | `c18aef206f16668d` | ← cambia |
| `9f99cae` | `6af6b556299be217` | ← **cambia: es el commit que arregló la sonda y movió 8 aristas** |
| `HEAD` | `6af6b556299be217` | (igual) |

**Componente `motor`, sobre `filex/motores.py`:**

| commit | ImageMagick | Ghostscript | FFmpeg |
|---|---|---|---|
| `89b1e9d` | `ecd3f0f7…` | `3804e729…` | `f55a23cd…` |
| `8fa3dfe` | `09196dd9…` | `e522f4c5…` | `98992b23…` |
| `2450766` | `09196dd9…` | `e522f4c5…` | `98992b23…` |
| `67320b6` | `09196dd9…` | `e522f4c5…` | **`a4a7346a…`** ← solo ffmpeg |
| `HEAD` | `09196dd9…` | `e522f4c5…` | `a4a7346a…` |

**La fila `67320b6` es la prueba de la granularidad sobre un caso real:** ese
commit arregló `*→gif` con `-map 0:v:0`, y `ffmpeg.json` dice en su propia nota
que las cinco aristas `*→gif` **hubo que resondearlas** por ello. La huella mueve
**solo ffmpeg**; ImageMagick y Ghostscript, que comparten fichero, no se enteran.
Una huella de FICHERO habría caducado los tres.

**Y el control de ruido, sobre el mismo `verificador.py` de HEAD:**

| perturbación | `sha256` del fichero crudo | huella elegida |
|---|---|---|
| editar un **comentario** | `d1b63439…` → `d02befe2…` **caducaría las 215** | `6af6b556…` → `6af6b556…` **no caduca nada** |
| tocar **`fidelidad_audio`** | (cambia) | `6af6b556…` → `6af6b556…` **no caduca nada** |

### 2.6 De extremo a extremo: se toca `motores.py` de verdad

Con `filex/motores.py` editado en el disco y el grafo reconstruido en un
subproceso (**restaurado después con `sha256` idéntico**):

| escenario | grafo | `diagnostico()` |
|---|---|---|
| **A.** control, sin tocar | 210 `real`, 5 `nominal` | `caducados: {}` |
| **B.** editar un **comentario** | **210 `real`**, 5 `nominal` | `caducados: {}` |
| **C.** `-quality 85` → `90` en ImageMagick | **148 `real`, 62 `sin_sondear`** | `{'imagemagick': ['motor']}` |

En **C** caducan **exactamente las 62 aristas de ImageMagick que vienen del
disco** —le quedan sus 5 declaradas en código— y **ffmpeg (83), Ghostscript (4)
y `doc_pandoc` (24) no se mueven**. El diagnóstico **nombra el componente**, que
es lo que convierte «no se aplicó» en algo accionable.

### 2.7 Coste

| | MEDIDO |
|---|---|
| Primera huella del proceso (parsea `verificador.py` entero) | **168,93 ms** |
| Los 6 motores, en frío, todo incluido | **162,04 ms** |
| Los 6 motores, en caliente (mediana de n=9) | **0,0028 ms** |
| Contra un `FileX()` **en caliente** (~750 ms) | **21,6 %, una sola vez por proceso** |
| Contra un `FileX()` **en frío** (~23,6 s) | **0,7 %** |

Se paga **una vez por proceso**. Dos optimizaciones dejaron el frío en un tercio
de lo que costaba al principio (478,72 ms): parsear cada fuente **una** vez —
`de_alcance` la parseaba dos— y cachear las clases **por fichero**, porque
`inspect.getsource` vuelve a barrer el fichero entero en cada llamada.

### 2.8 Lo que esta huella **NO** protege

Declararlo es parte del diseño: *una huella que caduca por todo se acaba
desactivando, y entonces no protege nada*.

1. **No es por CATEGORÍA.** El cierre de `verificar()` incluye todas las sondas
   —`_wav` y `_png` viven las dos ahí—, así que **tocar la sonda de audio caduca
   también las aristas de imagen**. Separarlo exigiría un mapa
   categoría→funciones mantenido a mano, y **un mapa que se queda obsoleto sin
   avisar es peor que un falso positivo que se paga resondeando**. Es la
   concesión consciente de este diseño.
2. **El cierre es ESTÁTICO.** Una llamada por `getattr`, por tabla de despacho
   construida en ejecución o por `importlib` no se ve. Se compensa siendo
   conservador —entra todo nombre **referenciado**, se llame o no— pero no es una
   garantía.
3. **No ve fuera de `filex`.** Otra versión de Python o de una biblioteca cambia
   el resultado sin mover la huella. El `build` es del MOTOR, no del intérprete:
   **PENDIENTE**.
4. **No ve los DATOS.** `referencia.json` y el `corpus/` pueden cambiar bajo una
   medida sin que la huella se entere.
5. **Un fichero sin `huella` se aplica igual** (regla de legado, §3.3). Se
   aplica **y se declara** en `sondeo.diagnostico()["sin_huella"]`.
6. **Una huella editada a mano la anula entera.** Es dato en un JSON que un
   agente con prisa puede copiar del error. Contra eso solo hay la prueba de
   §5 y decirlo aquí.

---

## 3. El sellado de los cinco ficheros

### 3.1 Qué se hizo

Copia de seguridad primero, y solo entonces se insertó un campo `huella` (y una
`nota_huella` que explica el sellado) entre `informe` y `aristas`. **Ni una
entrada de arista tocada:** `git diff --stat` da **31 inserciones y 1 supresión**
en los cinco ficheros, y la supresión es la llave final del JSON por el salto de
línea. Copia en el directorio de trabajo del agente; `sha256` de antes y después
en el guion `sellar.py`.

| fichero | aristas | `sha256` antes → después |
|---|---|---|
| `doc_calibre.json` | 8 | `114ebbee8d796406` → `a119aa29747f6e53` |
| `doc_libreoffice.json` | 16 | `adbf91fcbcf30de1` → `3545ead3b3fecef9` |
| `doc_pandoc.json` | 16 | `ba111b7394962599` → `d1513141480fc348` |
| `ffmpeg.json` | 71 | `a790331eb6fe267b` → `933b09a76fc50f58` |
| `imagemagick.json` | 62 | `bb046b26be04f905` → `50594d85f9441878` |

**Después del sellado el grafo es idéntico al bit:** 210 `real`, 5 `nominal`,
firma `b72858bd…` — **la misma cadena de 64 caracteres que antes de empezar.**

### 3.2 EL FALLO QUE HAY QUE REPORTAR: un fichero NO se midió con el código vigente

El encargo pedía comprobarlo antes de darlo por hecho, y **la comprobación sale
que no**:

```
filex/sondeo/*.json   mtime 10:36 – 11:04   commit 67320b6 (11:12:25)
filex/verificador.py  mtime 11:15           commit 9f99cae (11:18:51)  <-- POSTERIOR
```

**`verificador.py` cambió DESPUÉS de que se escribieran los cinco ficheros de
sondeo**, y el componente `contrato` lo detecta: `c18aef20…` en `67320b6` frente
a `6af6b556…` en `9f99cae` (§2.5). Literalmente, **los cinco ficheros se
midieron con un contrato que ya no existe**.

`motores.py`, `motor_contenedor.py` e `invocacion.py` **sí** son los de entonces:
`motores.py` no cambia desde `67320b6`, `motor_contenedor.py` tiene *mtime* 10:18
—anterior a los JSON— e `invocacion.py` no cambia desde el commit inicial.

### 3.3 Por qué se sellan igual, y no es indulgencia

Tres razones, y la primera es la que decide:

1. **El cambio de `9f99cae` es MONOTÓNAMENTE MÁS PERMISIVO.** Leído el diff
   entero, hace dos cosas y las dos van en la misma dirección:
   `punto3_propiedades` convierte un `fallo` en `aviso` (`if not n:` →
   `if not n and /ObjStm: aviso; elif not n: fallo`), y `_datos` **deja de**
   aplicar D1/D2 a las extensiones no tabulares. **Un contrato que acepta más
   no puede convertir un `real` en falso.** El riesgo va en el otro sentido:
   que algo marcado `nominal` antes del arreglo fuese en realidad `real`.
2. **Y por ese otro sentido la exposición es CERO.** En el disco solo hay **2
   entradas `nominal`**, las dos de ffmpeg, y las dos por `rc`, no por
   contrato: `mov>gif` («no se pudo preparar una fuente .mov») y `mkv>m4a`
   («rc=-2 del propio ffmpeg… **no es tolerancia del contrato**»). El arreglo
   del contrato no las toca.
3. **Corroboración del propio autor:** el mensaje de `9f99cae` —escrito
   *después* del arreglo— reporta «Grafo: 210 real, 5 nominal, 0 sin sondear».
   **Son las mismas tres cifras que se miden hoy.**

Las razones 1 y 2 son **ARGUMENTADAS sobre el diff**, no medidas por resondeo;
la 3 es MEDIDA por su autor. Resondear las 215 para elevarlas a MEDIDO cuesta
horas de contenedor y queda **PENDIENTE**; el próximo resondeo lo cerrará solo,
porque ya reescribirá la huella.

### 3.4 La regla de legado, y por qué existe

**Un fichero sin campo `huella` se aplica igual, y se declara.** Es deliberado:
degradar por prudencia costaba **153 aristas medidas con este mismo código** a
cambio de nada. Perder trabajo bueno por no saber leerlo no es prudencia. La
regla es transitoria —los cinco están sellados— y mientras exista, quien la use
sale nombrado en `sondeo.diagnostico()["sin_huella"]`, que es lo que la convierte
en una decisión en vez de en el agujero que veníamos a tapar.

---

## 4. DEUDA 2 — **REFUTADA en magnitud: 0 de 129**

> **PENDIENTE:** o las pruebas fijan su propio sondeo, o se declara que la suite
> no vale mientras se sondea.

### 4.1 La medida que decide

Cuatro pasadas completas de las 129, perturbando el sondeo del disco **sin tocar
`filex/sondeo/`** (un plugin de pytest reescribe `sondeo._DIR` o `sondeo.cargar`
en memoria, cargado antes de recolectar la primera prueba):

| perturbación | aristas movidas | resultado |
|---|---|---|
| ninguna (control) | 0 | **123 passed, 6 skipped** |
| **`_DIR` a un directorio VACÍO** | **153** (210 `real` → 57; 155 `sin_sondear`) | **123 passed, 6 skipped** |
| quitar las **2 entradas `nominal`** del disco | 2 | **123 passed, 6 skipped** |
| declarar **`nominal` las 215** | 215 | **34 failed**, 87 passed, 8 skipped |

**Con 153 aristas moviéndose debajo, la suite no se inmuta ni en una prueba.**

El control de que la perturbación muerde es explícito y hacía falta —«123 con el
disco vacío» no prueba nada si el plugin no se cargó—: con `_DIR` vacío,
`sondeo.resumen()` pasa de cinco motores a `{}` y el grafo cae a
`{'sin_sondear': 155, 'real': 57, 'nominal': 3}`.

### 4.2 Por qué son cero, que es lo que hay que entender

Dos mecanismos, ninguno accidental:

1. **Las pruebas que miran TABLAS ya estaban aisladas.** `test_hito5.py` usa
   `_forzado(cls)`, que rellena `m.aristas = m._aristas()` **sin llamar a
   `sondear()`** — y `sondeo.aplicar` solo se invoca desde `sondear()`. Las
   pruebas que afirman `epub→pdf` es `REAL` en Calibre y `NOMINAL` en
   LibreOffice leen la tabla del CÓDIGO, no el disco. Estaba resuelto y no
   escrito.
2. **Las pruebas de INTEGRACIÓN solo necesitan que exista *un* camino.** Con el
   sondeo vacío las aristas quedan `sin_sondear`, que cuesta `+2` pero **se
   puede usar**. El grafo sigue resolviendo, la conversión sigue ocurriendo y el
   contrato sigue diciendo lo mismo.

### 4.3 Dónde sí está la ventana, y por eso el cerrojo se ofrece igual

Los 34 fallos de la cuarta fila delimitan el riesgo: **lo que rompe la suite no
es que falte sondeo, es que el sondeo diga `nominal`**, porque eso suma coste
infinito y borra el camino. Y eso explica **exactamente** el fallo que se OBSERVÓ
el 22/08 —el grafo pasando de 142 a 190 `real` con un fichero escribiéndose a
mitad—: lo que tumbó aquella prueba no fue el salto de 142 a 190, fue que en el
mismo fichero **llegaron entradas `nominal`** que antes no estaban.

Hoy ese riesgo es teórico: solo hay 2 entradas `nominal` en disco y ninguna es
portante (fila 3 de la tabla). **34 de 129 es la cota superior del radio de
explosión, no una medida de lo que pasa.**

Queda `sondeo.congelar()` / `descongelar()`: una instantánea del disco por
proceso, una lectura por motor, que cierra la ventana entera.
**Deliberadamente NO es el comportamiento por defecto y NO se ha metido en la
suite.** Dos razones: con 0 de 129 no hay nada que arreglar, y **congelar por
sistema le escondería un sondeo recién escrito a quien quiere justamente eso**,
que es el caso normal de la CLI. Se ofrece para cuando el margen se estreche.

### 4.4 Veredicto sobre las dos salidas que planteaba el docstring

- *«las pruebas fijan su propio sondeo»* — **no hace falta hoy**: el mecanismo
  queda disponible y probado, sin imponerlo.
- *«se declara que la suite no vale mientras se sondea»* — **es FALSO y no debe
  declararse**: la suite vale mientras se sondea, y hay 3 pasadas de 129 que lo
  dicen. Declarar una limitación que no existe cuesta lo mismo que una que sí:
  la próxima persona se cree las dos.

---

## 5. Lo que queda vigilando

`pruebas/test_sondeo.py`, **28 pruebas**, ninguna con GPU ni con motor externo.
La que salda de verdad la deuda 1 es
`SelladoDelDisco::test_ningun_motor_disponible_tiene_el_sondeo_caducado`: si
alguien toca la clase de un motor, `invocacion.py` o el contrato de
`verificador.py` **y no resondea**, la suite se pone roja **nombrando el motor y
el componente**, en vez de heredar en silencio 20 medidas falsas de 21.

**Suite después: `151 passed, 6 skipped` = 157.** Las 129 de antes siguen en
verde una a una; las 28 nuevas son mías. **Ninguno de los cuatro ficheros de
prueba existentes se ha tocado.**

---

## 6. Propuesta de trampa nueva para `CLAUDE.md` (NO aplicada)

> 32. **Una medida caduca por CÓDIGO, no solo por `build`, y el fichero no tenía
>     forma de saberlo — MEDIDO** (`bench/deuda-sondeo.md`). 21 aristas medidas
>     `nominal` quedaron obsoletas al arreglarse la sonda: **20 de 21 salieron
>     `real` al resondear**. La arista mínima viable tiene **seis** dimensiones,
>     no cinco: `(origen, destino, motor, parametrización, build, huella del
>     código)`. **Pero la huella hay que elegirla, y un `sha256` del fichero no
>     vale:** editar un comentario de `verificador.py` mueve el `sha256` crudo y
>     **caducaría las 215 aristas**, mientras que el AST normalizado del cierre
>     de llamadas de `verificar()` **no se mueve** — y sí se mueve, en el commit
>     exacto que arregló la sonda. Granularidad medida: cambiar `-quality 85` por
>     `90` caduca **62 aristas de ImageMagick y 0 de las otras 148**. Y hay un
>     corolario que se salta solo: **el módulo que decide una arista casi nunca
>     es el que uno nombraría** — 3 de los 5 ficheros de sondeo los decide
>     `motor_contenedor.py`, que no aparecía en la lista de la deuda; hashea la
>     **clase y su MRO**, no ficheros por su nombre.

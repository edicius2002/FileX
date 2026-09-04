# La dependencia de contenedor, publicable

**Ronda 20 · worker11 · 2026-09-04 · rama `orden/contenedor-publicable`**

FileX invoca tres motores dentro de un contenedor —LibreOffice, Pandoc y Calibre
(`filex/motor_contenedor.py`)—, y esos tres sostienen **40 de las 172 aristas selladas**.
El repositorio pasa a ser público, así que un tercero que clone tiene que poder reproducir
eso. Este informe hace tres cosas: **fija la base por digest**, **saca la receta de dentro
de las salidas de un experimento**, y **declara con número qué pierde quien no tenga
Docker**.

**Titular, y es una autocorrección:** el riesgo que motivaba el encargo —que el `:latest`
ajeno se hubiera movido— **es real como mecanismo y HOY no se había materializado**; llegué
a afirmar lo contrario a mitad de trabajo y estaba comparando dos magnitudes distintas
(§1.3). Lo que sí resultó cierto, y es más caro, es que **fijar el digest no basta**: la
receta reconstruida hoy da otra imagen y hace caducar **exactamente las 40** aristas (§4).

---

## 0. Preflight

| | |
|---|---|
| `git lfs checkout` | 39 objetos, 266 MB, del almacén local |
| `corpus/imagen/tipico.png` | **42 855 B**, cabecera `\x89PNG…IHDR` real — **no** un puntero de 130 B (trampas 34 y 107) |
| `python ci/integridad.py` | **9 de 9 OK** antes de tocar nada |
| Otro agente en la máquina | worker10, midiendo aristas de ffmpeg. No comparte ficheros. **Usé Docker y red; no toqué la GPU ni su lock** |

`ci/integridad.py` aborta con `UnicodeEncodeError` bajo la consola cp1252 de esta máquina;
con `PYTHONIOENCODING=utf-8` corre entero. Es del terminal, no del comprobador — anotado en
§6 como pendiente menor.

---

## 1. El riesgo real: `FROM …convertx:latest`

### 1.1 Por qué es el riesgo del propio proyecto, no uno teórico

El repositorio tiene **medido** que un `:latest` ajeno destruye la reproducibilidad, y lo
midió **mordiéndole a otros**: `bench/salidas-competidores/MANIFIESTO-retirado.md` conserva
evidencia forense declarada *«irreproducible: los contenedores de ConvertX y SnapOtter
cambian de versión, así que sus fallos no se regeneran»*. Esa frase es el motivo por el que
la poda del 20/08 fue conservadora y por el que existe `ci/evidencia-irreproducible.txt`
(trampa 106).

Y `bench/salidas-invocacion/Dockerfile.c13` empezaba por `FROM ghcr.io/c4illin/convertx:latest`.

### 1.2 El digest — MEDIDO

`ghcr.io/c4illin/convertx:latest` es un **índice OCI multi-plataforma**, no una imagen suelta:

| capa del identificador | digest |
|---|---|
| **índice** (lo que resuelve `FROM`) | `sha256:b515b04bfd25298a5cdc775b2fcd48b9399bab658ce13e2598b65df1b16098c8` |
| manifiesto `linux/amd64` | `sha256:081d1638e8c6dfb6b5e69f47ff90e6f6037cdee29a2f25ddd44ddc6d2e52451d` |
| manifiesto `linux/arm64` | `sha256:c65ab84cab4c3e3ede28853f9dfcbaf5ddf1e52fd27e2c9ee5d02c77218eed60` |
| config del manifiesto amd64 | `sha256:a5b16e0b7d225f154757672dee1ccde32a0772f666115492e8ff1df2d54efe38` |

Se fija el **índice**: es lo que `FROM` resuelve y conserva la portabilidad a arm64. Todas
las medidas del proyecto son de **amd64**, de ahí el `--platform linux/amd64` en la orden.

**Control positivo independiente:** ese `b515b04bfd25` es exactamente el id que
`bench/docker.md` línea 49 registró el **22/08/2026**. El `:latest` del registro **no se
había movido** en trece días. La imagen se creó el `2026-06-21`.

### 1.3 La autocorrección, y cómo casi publico lo contrario

A mitad de trabajo escribí *«hallazgo grave: el `:latest` ya se movió»*, porque comparé el
**config** del manifiesto amd64 (`a5b16e0b…`, sacado del registro) contra el **`.Id`** local
(`b515b04…`). Son magnitudes de **niveles distintos** —config contra índice—, así que
diferían por construcción. La comparación no significaba nada.

Lo que lo destapó fue `docker buildx imagetools inspect`, que imprime el digest del índice
en su cabecera: `b515b04…` **es** el índice, y coincidía con lo local.

Dos avisos de instrumento del mismo sitio, los dos de la familia de la **trampa 66**:

- **`docker images --digests` no sirve para esto.** En Docker 29 con almacén containerd, su
  columna `Digest` **coincide con `.ID`** en las dos imágenes —incluida una construida en
  local, que no debería tener repo digest ninguno—. Una sonda que devuelve el mismo valor
  para dos cosas que sé distintas está rota.
- **Y `docker manifest inspect <ref>@<digest>` parecía ignorar el digest**: pedirle el local
  devolvía `rc=0` y el índice de hoy. **Control negativo obligatorio** (trampa 111): con un
  digest inventado devuelve `rc=1` y `manifest unknown`. La sonda **sí** discrimina; lo que
  pasaba es que el digest que le daba era el bueno.

Es la **trampa 36** —una explicación plausible no es un mecanismo— y la **58** —el hecho no
implica la causa—. El «hecho» (dos cadenas distintas) era cierto; la causa que le atribuí,
falsa.

### 1.4 Verificado CONSTRUYENDO, no sólo consultando — MEDIDO

El encargo pide declarar cuál de las dos cosas hice. **Construí**, una sola vez:

```
docker build --platform linux/amd64 -f docker/Dockerfile.c13 -t filex-c13-w11 docker/
```

| | |
|---|---|
| Resultado | **`rc=0`, 29 s** (histórico comparable: 28,1 s) |
| Etiqueta | `filex-c13-w11` — **propia**, para no pisar `filex-c13` |
| Motores dentro | `soffice`, `libreoffice`, `pandoc`, `ebook-convert` presentes; `qpdf 12.4.1`, `tesseract 5.5.0` con `eng osd spa` |
| Tamaño | 5,78 GB (base 5,73 → **+50 MB**) |
| Después | `docker rmi filex-c13-w11` |

La comprobación de los motores se hizo con el tope **dentro** del contenedor y `--init`,
como manda §3: `docker run --rm --init --entrypoint timeout … -k 5 120 sh -c …`.

---

## 2. El sitio: qué costó moverlo

### 2.1 Lo que había

La receta de la imagen que **usa el producto** vivía en
`bench/salidas-invocacion/Dockerfile.c13`, es decir dentro de las salidas de un experimento
de agosto, mientras `docker/` es de primer nivel y sólo tenía compose de competidores.

### 2.2 El censo de citas, antes de mover — `git grep`, no `glob` (trampa 104)

**10 citas de la ruta, en 8 ficheros:**

| Fichero | Citas | ¿Puedo tocarlo? | Qué hice |
|---|---:|---|---|
| `bench/salidas-invocacion/MANIFIESTO.md` | 2 | sí | **arreglado** |
| `bench/salidas-invocacion/_p2_manifiesto.py` | 2 | sí | **arreglado** (es el generador) |
| `CLAUDE.md` §2 | 1 | **vedado** | texto propuesto en §7 |
| `filex/motor_contenedor.py` línea 105 | 1 | **vedado** (carril) | texto propuesto en §7 |
| `bench/hito5-documental.md` | 1 | histórico | **no tocado**, a propósito |
| `bench/invocacion-aristas.md` | 1 | histórico | **no tocado** |
| `bench/consolidacion-3-21ago.md` | 1 | histórico | **no tocado** |
| `bench/salidas-hito5/_sonda.py` | 1 | histórico | **no tocado** |

### 2.3 La decisión, y por qué no fue «copiar»

Copiar la receta a `docker/` y dejar la vieja habría creado **dos ficheros con el mismo
nombre y contenido distinto** —uno con `:latest`, otro con digest—, que es una trampa 92
esperando: un tercero construiría el equivocado. Se movió con **`git mv`**, así que hay una
sola fuente de verdad y el historial registra el *rename*.

**El coste, pagado y declarado:** cuatro informes históricos citan una ruta que ya no
existe. **No se reescriben**: son documentos fechados, y el proyecto conserva la evidencia
en vez de adaptarla al comprobador (trampa 115). La cita queda resoluble por dos vías: el
`MANIFIESTO.md` del experimento, que ahora dice adónde fue el fichero y con qué `sha256`
salió de allí (367 B, `268e4f2c2f95676a…`, verificado contra el manifiesto antes de mover), y
el propio historial de git.

**Y el arreglo se puso en el GENERADOR, no sólo en el `.md`.** `_p2_manifiesto.py` construye
la tabla escaneando el directorio, así que una nota escrita sólo en el `MANIFIESTO.md`
**desaparecería en la siguiente regeneración** (trampa 92: la fuente de verdad es el módulo
que se ejecuta, no el texto). La nota de traslado vive ahora en los dos, con el mismo
contenido. El generador **compila** tras el cambio, comprobado con `ast.parse` (trampa 60).

**No regeneré el `MANIFIESTO.md` ejecutando el script**, a propósito: reescribiría con datos
de hoy el registro de un experimento cerrado en agosto. Se editaron los dos a mano y de
forma coherente. *(PENDIENTE menor: eso no está verificado por máquina, sólo por lectura.)*

### 2.4 Un argumento del encargo que se debilita — hallazgo

El encargo decía que el fichero era *«fácil de barrer en una poda»*. **Medido, lo era menos
de lo que parece:** `bench/salidas-invocacion/MANIFIESTO.md` lo listaba con su `sha256`, y
`ci/integridad.py` comprueba manifiestos, así que estaba protegido por el mismo mecanismo
que la trampa 106 puso en pie. **El argumento que sí aguanta entero es el otro**: un tercero
que clona no busca la receta de la imagen del producto dentro de las salidas de un
experimento. Lo digo porque de los dos motivos del encargo, uno se sostiene y el otro no, y
el traslado se justifica por el que se sostiene.

---

## 3. Qué pierde exactamente quien no tenga Docker — MEDIDO

Derivado de `filex/sondeo/*.json` contando aristas una a una, **no estimado**.

### 3.1 Aristas selladas

| Motor | Fichero de sondeo | Aristas | ¿Contenedor? |
|---|---|---:|---|
| ffmpeg | `ffmpeg.json` | 70 | no |
| ImageMagick | `imagemagick.json` | 62 | no |
| LibreOffice | `doc_libreoffice.json` | **16** | **sí** |
| Pandoc | `doc_pandoc.json` | **16** | **sí** |
| Calibre | `doc_calibre.json` | **8** | **sí** |
| | **Total** | **172** | **40 de contenedor = 23,26 %** |

`ghostscript` es motor nativo y **no tiene fichero de sondeo**: 0 aristas selladas.

### 3.2 Aristas del grafo (no sólo lo sellado)

Lo sellado es una cosa; lo que el estrato ofimático aporta al grafo es otra, porque el
código trae además `_MEDIDAS` y `_MUERTAS`:

| Motor | Declaradas | Medidas | Muertas | **Grafo** |
|---|---:|---:|---:|---:|
| LibreOffice | 16 | 10 | 2 | **28** |
| Pandoc | 16 | 15 | 0 | **31** |
| Calibre | 8 | 8 | 1 | **17** |
| | | | | **76** |

Así que hay **dos cifras honestas y no son intercambiables**: **40** es lo que se pierde de
lo *sellado*; **76** es lo que desaparece del *grafo*. *(El docstring del módulo dice «36
aristas»: cifra anterior al crecimiento de `_DECLARADAS`, PENDIENTE de corregir por su
carril.)*

### 3.3 Qué desaparece en la práctica

El estrato documental entero: nada de `docx→*`, `epub→*`, `xlsx→*`, `tex→*`, `md→pptx`,
`mobi/azw3→*`. **Intactas las 132 nativas** (imagen, vídeo, audio, PDF).

### 3.4 El fallo es honesto, y eso es parte de la respuesta

`entorno()` distingue **cuatro** motivos de ausencia, no uno: no hay `docker` en el `PATH`;
lo hay pero el demonio no responde; el demonio responde pero **no está ninguna de las
imágenes** (`filex-c13`, `ghcr.io/c4illin/convertx:latest`); o la imagen está pero no trae
ningún motor documental. Más un quinto a nivel de submotor: *«la imagen X no trae
`soffice`»*. En todos los casos el motor **se auto-excluye informando**, y sus aristas no
entran al grafo. No hay silencio.

### 3.5 Pruebas

**12 métodos se saltan sin Docker**, en 2 ficheros y 2 clases: `test_hito5.py::Integracion`
(8) y `test_cancelacion.py::ContenedorReal` (4). Coincide exactamente con lo que declara la
trampa 94. **Matiz que evita una lectura pesimista:** `test_hito5.py` tiene 25 pruebas en 4
clases, y las **17** de las otras tres **sí corren sin Docker**, porque leen las tablas como
datos. Lo que se pierde no es el módulo, son esas 12.

---

## 4. Lo que el digest NO compra — MEDIDO, y es el hallazgo caro

Fijar la base es **necesario y no suficiente**, y esto no estaba escrito en ninguna parte.

El `build` que sellan los tres JSON es `doc_libreoffice 29.4.3 · filex-c13@6d359bad483e`:
**lleva dentro el id de la imagen**. Y ese id cambia al reconstruir, porque la capa
`apt-get` no está fijada y Debian forky/sid se mueve:

| | id de imagen | qpdf |
|---|---|---|
| sellada en `filex/sondeo/doc_*.json` | `6d359bad483e` | 12.4.0 |
| reconstruida el 04/09/2026, misma receta, misma base fijada | `0210178ee7b3` | **12.4.1** |

**Efecto medido en ejecución** (sondeado, no deducido), pareado dentro de la misma tanda y
repetido en dos tandas con resultado idéntico:

| | doc_libreoffice | doc_pandoc | doc_calibre | **medidas** |
|---|---|---|---|---:|
| con la imagen **sellada** | 28 aristas (**26**) | 31 (**31**) | 17 (**16**) | **73** |
| con la **reconstruida** | 28 aristas (**10**) | 31 (**15**) | 17 (**8**) | **33** |

**La diferencia es exactamente 40**: las 40 aristas selladas. Quien reconstruya la imagen
**no hereda los sellos** — los ve caducar, y se queda con las 33 medidas que viven en el
código.

**Eso no es un fallo: es el sistema de huella funcionando** (trampas 32 y 105). Pero hay que
decirlo, porque el modo de fallo es el peor de los descritos en la 105: el sistema no dice
«no comparable», dice **«caducado»**, que invita a resellar a ciegas.

**Y no se arregla fijando las versiones de `apt`:** Debian sid **retira** las versiones
viejas de sus índices, así que un `qpdf=12.4.0-1` haría que la receta dejara de construir en
semanas. Se prefiere **una receta que construye siempre y un sello que caduca a la vista**
sobre una receta que se rompe. Queda escrito dentro del propio Dockerfile.

*(De paso, y es una cifra caducada de `CLAUDE.md` §2: dice `qpdf 12.4.0`. Hoy son **12.4.1**
—trampa 44—. Propuesta en §7.)*

---

## 5. Lo que NO hice, y por qué

- **No toqué `filex/` ni `pruebas/`.** El único punto de `filex/` afectado es un **comentario**
  en `motor_contenedor.py:105` que cita la ruta vieja; no cambia comportamiento.
- **No reescribí los cuatro informes históricos** (§2.3).
- **No borré el Dockerfile viejo dejando sólo su `sha256`.** Habría sido defendible por §6,
  pero es la clase de gesto que la trampa 106 castiga: antes de borrar, se busca dónde el
  repositorio declaró su excepción. Moverlo conserva todo y no destruye nada.
- **No construí más de una vez** (el encargo lo pedía explícitamente).
- **No dejé la imagen de prueba** ocupando 5,78 GB.

---

## 6. Pendientes

1. **PENDIENTE — `ci/integridad.py` fallará en `informes-registrados`** hasta que este
   informe se registre en `ESTADO-Y-REPARTO.md`, que tengo vedado. Fila propuesta en §7.
   **Esto es esperado y declarado, no una sorpresa.**
2. **PENDIENTE — `informes_registrados()` usa `glob()` sobre el disco, no `git ls-files`.**
   Es literalmente la trampa 104, que el proyecto corrigió en `_md()` y dejó aquí: un `.md`
   sin commitear ya cuenta como informe. No lo arreglo porque `ci/` no es mi encargo, pero
   queda señalado.
3. **PENDIENTE — el digest no está vigilado.** Nadie se entera si el `:latest` de upstream se
   mueve. La orden que lo comprueba está escrita dentro del Dockerfile
   (`docker buildx imagetools inspect`), pero **no hay comprobación automática**. Podría ser
   una comprobación de `ci/integridad.py`, con la salvedad de que necesitaría **red**, que
   hoy ninguna de las nueve necesita — es una decisión de arquitectura, no un despiste.
4. **PENDIENTE — `README.md` dice «bench/ Las mediciones: 100 informes»** y
   `ci/integridad.py` cuenta **104** (105 con éste). No lo toco: es un contador que otros
   agentes de esta ronda están moviendo, y pisarlo sería peor.
5. **PENDIENTE — no verifiqué que `_p2_manifiesto.py` regenere un `MANIFIESTO.md` idéntico
   al que edité a mano** (§2.3). Ejecutarlo habría reescrito con datos de hoy un registro de
   agosto.
6. **PENDIENTE — `ci/integridad.py` revienta con `UnicodeEncodeError`** bajo la consola
   cp1252 de esta máquina; funciona con `PYTHONIOENCODING=utf-8`. Es del terminal, no del
   comprobador, pero un tercero en Windows se lo va a encontrar.
7. **PENDIENTE — el detalle de `informes-registrados` es una nota falsa al lado de un campo
   honesto** (trampa 44). Al fallar imprime:

   ```
   MAL  informes-registrados   105 informes, todos citados
         contenedor-publicable.md
   ```

   **«todos citados» es exactamente lo contrario de lo que acaba de detectar.** El recuento
   (105) es verdadero y la frase pegada a él es falsa; sólo la lista de debajo dice la
   verdad. La cadena se construye igual en el camino de éxito y en el de fallo. Es barato de
   arreglar y no lo toco porque `ci/` no es mi encargo.

---

## 6bis. Estado de la suite tras el cambio

No toqué `filex/` ni `pruebas/`, así que no correspondía la suite entera; sí los dos módulos
del área afectada. **Las cuatro declaraciones que exige el proyecto** (trampas 94 y 101):

| | |
|---|---|
| **Intérprete** | `.venv-mcp-filex/Scripts/python.exe` — **win32**, 3.11.9 |
| **Entorno** | Docker 29.4.3 **levantado**, imagen `filex-c13` presente, corpus de LFS materializado |
| **Qué quedó fuera** | Los otros 17 módulos (no toqué su código). **0 saltadas** en los dos ejecutados: las 8 de `Integracion` **sí corrieron** |
| **Estado de la máquina** | worker10 midiendo ffmpeg en paralelo; sin disputa por la GPU |

`pytest pruebas/test_hito5.py pruebas/test_sondeo.py -q` → **73 passed · 14 subtests · 0
failed · 0 skipped**, 46,76 s. Que `test_sondeo` pase importa especialmente: es el módulo
que compara huellas y `build`, es decir el que habría cantado si mover el fichero hubiera
tocado algo real.

---

## 7. Texto propuesto para los ficheros vedados

### 7.1 `CLAUDE.md` §2 — **obligatorio, porque la ruta cambió**

En el párrafo que empieza *«**Lo que NO hay en Windows sí está en `filex-convertx`**…»*,
sustituir el final —desde *«**Ausentes: `qpdf` y `tesseract`**»*— por:

> **Ausentes: `qpdf` y `tesseract`** — son los dos únicos motores que habría que añadir a
> una imagen, **y ya está medido lo que cuesta: 8 líneas, 28,1 s, +50 MB** (imagen
> `filex-c13`, **`docker/Dockerfile.c13`** — trasladado el 04/09/2026 desde
> `bench/salidas-invocacion/`, donde vivía dentro de las salidas de un experimento, y
> **fijado por digest** al índice OCI
> `sha256:b515b04bfd25298a5cdc775b2fcd48b9399bab658ce13e2598b65df1b16098c8`, porque un
> `:latest` ajeno es justo lo que este repositorio tiene medido como destructor de
> reproducibilidad; `bench/contenedor-publicable.md`). **Y fijar la base NO basta — MEDIDO
> el 04/09:** la capa `apt-get` no está fijada, reconstruir da otro id
> (`6d359bad483e` → `0210178ee7b3`, `qpdf` **12.4.1**, no 12.4.0) y eso **caduca exactamente
> las 40 aristas selladas de contenedor** (73 medidas → 33). Se prefiere una receta que
> construye siempre a una que se rompe: Debian sid retira las versiones viejas.

### 7.2 `filex/motor_contenedor.py` línea 105 — carril ajeno

Comentario, sin efecto en el comportamiento:

```python
#: (`docker/Dockerfile.c13`, fijado por digest; antes en
#: `bench/salidas-invocacion/Dockerfile.c13`). Se prueban en orden y se usa la
```

### 7.3 `ESTADO-Y-REPARTO.md` §1 — fila del informe

| Informe | Ronda | Qué cierra |
|---|---|---|
| `bench/contenedor-publicable.md` | 20 (worker11) | La dependencia de contenedor queda publicable: `Dockerfile.c13` **trasladado a `docker/`** y **fijado por digest** (índice OCI `b515b04bfd25…`), verificado **construyendo** (`rc=0`, 29 s). **MEDIDO que el digest no basta:** reconstruir da otro id y caduca **exactamente las 40** aristas selladas (73 → 33 medidas). Degradación sin Docker declarada con número: **40 de 172 selladas (23,3 %)**, **76** del grafo, **12** pruebas. Autocorrección: la alarma de que el `:latest` se había movido era **falsa** (comparé config contra índice) |

---

## 8. Consumo de máquina

| Recurso | Uso |
|---|---|
| **GPU** | **ninguno.** No tomé el lock ni lo necesité |
| **Docker** | 1 construcción (29 s), 1 `docker run` de verificación (~10 s), varios `inspect`/`manifest inspect` de segundos. **La imagen se retiró** |
| **Red** | 4 consultas al registro `ghcr.io` (manifiestos, bytes) + un `apt-get update/install` dentro del build (~50 MB) |
| **Disco** | +5,78 GB transitorios, devueltos con `docker rmi`. En el repositorio: 4 ficheros de texto nuevos, ~12 KB |
| **CPU** | Dos ejecuciones de `python -m filex motores` (segundos). **No ejecuté la suite entera**: no toqué `filex/` ni `pruebas/` |
| **Otro agente** | worker10 (ffmpeg). Sin ficheros compartidos y sin disputa por la GPU |

# Documentación apta para terceros — qué se cambió, qué no, y por qué

**Fecha:** 04/09/2026 · **Carril:** `orden/documentacion-publica` · **Alcance:** sólo
documentación. **No se ha tocado una línea de `filex/` ni de `pruebas/`.**

**Encargo:** dejar la documentación del repositorio en condiciones de ser leída por alguien
de fuera, que llega sin el contexto de 100 informes y quiere entender qué es FileX, qué
demuestra y cómo se usa.

**Línea base y línea final de `ci/integridad.py`:** **9 de 9 al empezar**, y **9 de 9 tras
cada uno de los cuatro commits** — salvo la comprobación `informes-registrados`, que exige
que este mismo fichero esté citado en `ESTADO-Y-REPARTO.md` §1 y **que no puedo satisfacer
porque ese documento es de los maestros**. Ver §6.

---

## 1. La medida propia: la suite, con sus cuatro declaraciones

**MEDIDO el 04/09/2026.** Se ejecutó la suite entera para poder publicar un recuento en
primera persona en vez de heredarlo:

```
501 passed · 3 skipped · 0 failed · 179 subtests · 265,49 s
```

1. **Intérprete** — `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe`, **win32,
   3.11.9**, comprobado con `sys.version`/`sys.platform` antes de lanzar. Las pruebas
   `win32` **sí** corren.
2. **Entorno** — **Docker 29.4.3 levantado**, comprobado con `docker info` antes de lanzar.
   Corpus de Git LFS materializado: `corpus/imagen/tipico.png` = **42 855 B** (trampas 34 y
   107 — se comprobó el **tamaño**, no la existencia, porque `os.path.exists()` devuelve
   `True` sobre un puntero de 130 B).
3. **Qué quedó fuera** — los 3 saltados, listados con `-rs` en vez de suponerlos:
   `test_hito4.py:221` (*«ningún par real rasteriza hacia un destino con texto en esta
   máquina»*), `test_hito6.py:186` (*«falta el ráster»*) y `test_hito6.py:697` (*«necesita la
   tarjeta: FILEX_PRUEBAS_SIDECAR=1»*). Son los tres mismos que declara la tanda de
   referencia.
4. **Estado de la máquina** — **NO estaba despejada, y se comprobó en vez de suponerlo:** la
   tanda convivió con tres procesos de análisis del propio repositorio. Tardó **265,49 s**
   frente a los **208,05 s** de la referencia. El lock de GPU quedó libre y no se usó la
   tarjeta.

**El recuento reproduce EXACTAMENTE el de `bench/raices-mixtas.md` §8 (501 · 3 · 0 · 179) y
el tiempo no**, que es justo lo que predice `CLAUDE.md` §3: *las cifras absolutas de tandas
distintas no son comparables; las relativas dentro de una tanda, sí*. **Una pasada limpia no
cierra `N36`**, que documenta esa prueba como inestable bajo carga: se dice en el `README`.

### 1.1 Una cifra del encargo que NO pude rastrear — PENDIENTE

El encargo daba como última medida buena **«500 passed · 1 failed · 3 skipped · 179 subtests
· 224,56 s»**, con el fallo atribuido a `N36`. **Ni `224,56` ni `500 passed · 1 failed`
aparecen en ningún fichero del repositorio** (`grep` sobre todos los `.md`). Lo que sí está,
y con sus cuatro declaraciones escritas, es el **501 · 3 · 0 · 179 · 208,05 s** de
`bench/raices-mixtas.md` §8. **No la copié**, que es lo que pide la regla de no publicar una
cifra que no se puede rastrear: la medí yo y publiqué la mía. Lo más probable es que la del
encargo sea una pasada de verificación no volcada a un informe; queda anotada por si el
maestro quiere registrarla.

---

## 2. Cifras caducadas encontradas, y qué se hizo con cada una

Todas verificadas contra la fuente antes de tocarlas. **La columna «Real» es MEDIDO hoy.**

| Dónde | Decía | Real (04/09/2026) | Cómo se comprobó |
|---|---|---|---|
| `README.md` | suite `460 passed · 3 skipped · 130 subtests · 243,58 s` | `501 · 3 · 0 · 179 · 265,49 s` | ejecutada (§1) |
| `README.md` | inventario `118 filas: 97 cerradas, 9 en curso, 6 abiertas` | **126 filas**: 114 🟢 · 3 🟡 · 3 🔴 · 6 ⚫ | `ci/integridad.py` |
| `README.md` | `corpus/` **20 ficheros** | **44** versionados, **39** en LFS | `git ls-files` |
| `README.md` | **18** ficheros de pruebas | **19** | `git ls-files 'pruebas/test_*.py'` |
| `CONTRIBUTING.md` | **107 trampas** | **119** | `ci/integridad.py`; iba **doce** por detrás |
| `CONTRIBUTING.md` | deuda heredada: *«3 binarios sueltos y 17 directorios sin manifiesto»* | **las dos listas de `ci/heredado.json` están VACÍAS** | lectura del fichero |
| `GUIA-DE-USO.md` | `filex motores`: **215 aristas (210 medidas)** | **232 aristas (227 medidas)** | `python -m filex motores` |
| `GUIA-DE-USO.md` | LibreOffice **18** aristas · Pandoc **24** | **28** · **31** | ídem |
| `PENDIENTE.md` | *«tras fusionar la ronda 13»*, **121 filas**, suite `478 · 3 · 175` | ronda **16**, **126 filas**, suite §1 | `git log`, `ci/integridad.py` |
| `RESULTADOS-MCP.md` | *«la regla de ≤1.200 tokens se confirma»* | el catálogo real va por **1 650** y crece ≈2,6 tokens por arista | `CLAUDE.md` §5 (medido el 04/09) |
| `BENCHMARKS.md` | *«más de 80 informes»* | **100** | `git ls-files` |

### 2.1 Una cifra que parecía caducada y NO lo era — y por poco la «arreglo»

`README.md` declaraba el corpus en **254 MB** y `git lfs checkout` imprime **266 MB**.
Parecía un desfase evidente. **Medido: 266 209 628 B, que son 253,9 MiB.** Las dos cifras
son **el mismo número en unidades distintas**, y la del README era correcta. Se conserva el
254 y se le añade la unidad (**MiB**).

Es la **trampa 58** en su forma más barata: *reproduce la medida antes de arreglar el hecho*.
Corregirlo a 266 habría metido un error donde no lo había, y encima habría roto la
comparación que da sentido a la cifra —la cuota de 1 GB/mes de ancho de banda de LFS—.

### 2.2 Una cifra mía caducó DENTRO de la sesión, y sólo se vio al mirar el diff

**MEDIDO.** Publiqué el inventario en **125 filas (113 🟢)**, contado a máquina sobre mi base
`7bd0927`. Mientras trabajaba, `main` avanzó a `2498f4b` (*«C6 descartada y C7 aplazada… nace
N37»*), que **mueve el inventario a 126 filas (114 🟢)**. Mis dos cifras eran correctas
respecto de mi base y **caducadas respecto de `main`**: exactamente el defecto que este
encargo venía a corregir, reproducido por quien lo corregía.

**Lo que lo destapó no fue una comprobación, fue leer el `git diff --stat`** — que mostraba
`ESTADO-Y-REPARTO.md` con 9 líneas cambiadas en un carril que tiene prohibido tocarlo. La
primera lectura («he editado un maestro sin darme cuenta») era **falsa**: el diff se estaba
tomando contra `main`, que ya no era mi base. `git diff 7bd0927..HEAD` lo desmiente en una
línea, y `git diff --name-only … -- CLAUDE.md ESTADO-Y-REPARTO.md PLAN-ORQUESTADOR.md filex
pruebas` sale **vacío**. Se rebasó sobre `main` y se actualizaron las dos cifras.

**Dos lecciones, y la segunda es la cara:**

- **Un recuento tomado de un fichero que otro carril puede mover caduca sin que nadie toque
  tu rama.** No basta con contarlo a máquina: hay que contarlo **contra la punta con la que
  se va a fusionar**, y volver a contarlo antes de entregar.
- **Un `diff --stat` contra `main` no es un diff de tu trabajo si `main` se ha movido**, y el
  modo de fallo es el peor: parece que has tocado un fichero prohibido. Es la trampa 101 en
  su corolario de método —*antes de culpar al cambio, comprueba si el cambio tocó código*—
  aplicado al propio instrumento: **compara siempre contra la BASE, no contra la rama que
  crees que es la base.**

---

## 3. Lo que se cambió, documento por documento

### `README.md` — reescrito entero
Era un índice para alguien de dentro. Ahora: qué es FileX y qué **no** es (no convierte, invoca
y verifica) en el primer párrafo, la tesis con sus siete fallos, una tabla de entrada por
intención, el estado con la suite y sus cuatro declaraciones, y la CI con **lo que no cubre
por delante de lo que cubre**. Se conserva íntegra la convención MEDIDO/PENDIENTE y **la cita
de las 119 trampas**, que `ci/integridad.py` exige que coincida en tres sitios.

Se explicita además **la excepción de la regla de peso** —`ci/evidencia-irreproducible.txt`—
porque es justo lo que la trampa 106 dice que hay que citar entero: *la regla dice «binarios
**regenerables**», y hay evidencia que no lo es*.

### `CONTRIBUTING.md`
Las tres cifras caducadas de §2, y el flujo de entrega, que daba por supuesto que quien
contribuye es una sesión de agente sin credenciales de GitHub. Ahora separa **el colaborador
externo** (fork y PR, el camino corriente) de ese caso, sin perder la medida que lo respalda.

### `GUIA-DE-USO.md`
**Los ejemplos se reejecutaron hoy, no se editaron a mano.** Los dos de `filex plan`
reproducen **literalmente** y no se tocaron. `filex convertir` da los mismos bytes
(`3966842 de 3966842`) y otro tiempo, así que se actualizó el ms y se advirtió que **los
tiempos son de la tanda**. Se añadieron las rutas de Linux/macOS y se dijo dónde están
medidas las garantías fuertes, en vez de dejar que el lector lo suponga.

### `PENDIENTE.md`
Cabecera y recuentos al día. **Se declara explícitamente que el detalle fila a fila es de la
ronda 13 y NO está reverificado**, en vez de rehacerlo de memoria: una lista rehecha sin
volver a mirar el inventario sería exactamente el defecto que este documento existe para
evitar. Se cerró su §6 (*«un desfase que este fichero no arregla»*) ejecutando la suite. Se
añadió un glosario del vocabulario de rondas y carriles.

### `PRUEBAS-MCP-REFS.md`
Su cabecera ya avisaba de que está superado, **pero sus §4–§7 siguen en imperativo**
(*«reglas para el agente que lo ejecute»*), y un lector que se salte el aviso lee un plan
vigente. Se dice en la propia cabecera. Ruta absoluta `D:\Work\research\FileX\.mcp.json` →
relativa.

### `RESULTADOS-MCP.md` — una cita de commit MUERTA que la CI no ve
Mandaba `git show 23b8d3c:PRUEBAS-MCP-REFS.md`, y **ese hash no resuelve**
(`git cat-file -e` → *Not a valid object name*). **No es la reescritura de historia del
31/08**: no aparece en `bench/salidas-publicacion/commit-map-20260831.txt`. Era un commit de
las ramas `ccb/w1..w3`, muerto al borrarlas — **la trampa 115**. Se deja escrito que murió y
por qué, y se da el commit **vivo** desde el que sí se recupera el fichero (`dcd4057`,
comprobado). **No se borró la afirmación**: una cita muerta declarada vale más que una cita
borrada.

### `HUECOS.md` y `ANALISIS-COMPLETO.md`
Sólo un bloque de orientación delante de cada uno: qué es el documento, para quién, y la
convención MEDIDO/PENDIENTE —que `ANALISIS-COMPLETO.md` **no declaraba**, y en vez de fingir
que la aplica se dice que es anterior a ella—. **No se les tocó ni una cifra**: son
documentos fechados, y reescribirlos borraría la historia intelectual que justifica
conservarlos. Los dos declaran ahora que no están actualizados tras el 21/08 y que **manda
`bench/`**.

### `informe-filex.html`
El más desfasado del árbol (19/08). Aviso de instantánea fechada delante, **nombrando las
cuatro afirmaciones centrales que el propio repositorio refutó después** —el ×8,4 de NVENC,
la salida CPU/GPU «idéntica», *«fallan los tres motores en dificultad 3»* y marker heredando
el bloqueo de Surya—, cada una con quién la refuta. **Ninguna se borró.** Se quitó la
segunda persona (*«en tu RTX 3060»*, *«medido en tu máquina»*…), que es lo que más delata que
no se escribió para publicar: **5 de 5 sustituciones, 0 ocurrencias restantes**, y el HTML
quedó balanceado (88 `<div>` abiertos, 88 cerrados).

---

## 4. Lo que NO se tocó, y por qué

| Qué | Por qué |
|---|---|
| **`CLAUDE.md`, `ESTADO-Y-REPARTO.md`, `PLAN-ORQUESTADOR.md`** | Son los maestros. Propuestas en §5 |
| **`filex/` y `pruebas/`** | Fuera del encargo. `filex/api.py:62` y `filex/mcp.py:42` traen `--raiz D:/Work/research/FileX` en sus docstrings: **es un defecto de documentación que vive en el código**, y un tercero copiaría esa ruta. Lo reporto, no lo arreglo |
| **`.mcp.json`** | **Está versionado** y trae **5 rutas absolutas** a `D:\Work\research\FileX\.venv-*`. Es el fichero de primer nivel que peor se lee en público — y es la **configuración MCP viva** de la máquina: editarlo rompe el servidor MCP en uso. Decisión del maestro (§5.4) |
| **`ci/windows-hosted-apto.json`** | Sus líneas 45 y 56 contienen `C:\Users\krato\AppData\Local\Temp`. Es un **extracto de traza medida**: editarlo falsearía un registro de medición, que es peor que la fuga de un nombre de usuario ya público en el historial |
| **`docker/*.yml`** | `POSTGRES_PASSWORD: snapotter` y un `JWT_SECRET` autoexplicativo de relleno. Son contenedores **locales** de investigación y las bases ya están inicializadas con ellos: cambiarlos rompe el banco de pruebas sin ganar seguridad real. Se reporta |
| **Las cifras de `HUECOS.md` / `ANALISIS-COMPLETO.md`** | Documentos fechados. Se declara su fecha y que manda `bench/`, en vez de reescribir la historia |
| **`ci/integridad.py`** | Encontré un hueco real en su comprobación `citas` (§5.3). No toco el instrumento en el mismo commit en que uso sus resultados |
| **`AGENTES-PRUEBAS-PENDIENTES.md`** | **No se borró.** Ver §4.1 |

### 4.1 El documento invalidado: por qué se conserva y qué se hizo

`ESTADO-Y-REPARTO.md` lo declara *«superado por este documento; su contexto y sus marcas
están invalidados»*, y `A4` está cerrada por ese motivo. **La respuesta obvia era borrarlo, y
es la equivocada por tres razones MEDIDAS:**

1. **Ya lleva su propio aviso.** Sus primeras 12 líneas son un `⛔ DOCUMENTO SUPERADO` que
   explica que **su justificación entera se cayó** y por qué. **El documento no confunde a
   quien lo abre.**
2. **Lo que confundía era el `README`**, que lo listaba como *«los motores de IA que faltan
   por probar»* — una entrada con pinta de tarea viva, en el índice de entrada. **Eso es lo
   que se quitó**, que es la corrección de coste cero.
3. **Borrarlo dejaría colgadas 6 referencias en `ESTADO-Y-REPARTO.md`**, que no puedo editar,
   y destruiría la historia intelectual que su propia cabecera dice conservar: *«qué se creyó
   y por qué cambió»*.

Es la forma de la **trampa 106**: la regla de higiene aplicada sin su matiz manda destruir
evidencia. Se arregló el puntero, no el documento. **Si el maestro prefiere borrarlo, en §5.2
va la propuesta.**

---

## 5. Propuestas para los tres maestros — texto exacto para pegar

### 5.1 `CLAUDE.md` §1 — la ruta absoluta de la tabla «Nunca toques esto»

La fila de `~/.claude.json` dice `en D:\Work\research\FileX\.mcp.json`. En un repositorio
público, sustituir por:

> | **`~/.claude.json`** | Configuración MCP **solo de proyecto**, en el `.mcp.json` de la raíz del repositorio |

### 5.2 `ESTADO-Y-REPARTO.md` — decidir sobre `AGENTES-PRUEBAS-PENDIENTES.md`

Si se prefiere borrarlo, hay que quitar antes sus **6** referencias (líneas 3, 57, 277, 704,
1064 y 1456). **Mi recomendación es conservarlo**, por §4.1. Si se conserva, basta añadir a
la fila de la tabla final:

> | `AGENTES-PRUEBAS-PENDIENTES.md` | **Superado por este documento.** Su contexto y sus marcas están invalidados. **Se conserva a propósito como historia intelectual**, con su aviso en cabecera; ya no se enlaza desde el `README.md` |

### 5.3 `CLAUDE.md` §4 — trampa nueva propuesta (sería la **120**, al final)

**MEDIDO hoy.** `ci/integridad.py` da `0 muertas` y hay una cita muerta en el árbol:

> 120. **Un comprobador de citas de commit puede pasar en verde con una cita muerta delante, porque busca la PALABRA y no el HASH — MEDIDO el 04/09.** `ci/integridad.py` nació de que *«el `filter-repo` del 31/08 mató 16 citas de hash y no hubo un solo error»*, y su patrón es `(?:commit|revisi[oó]n)e?s? +\`([0-9a-f]{7,40})\``: exige la palabra **pegada** al hash entrecomillado. `RESULTADOS-MCP.md` §nota de trazabilidad mandaba `git show 23b8d3c:PRUEBAS-MCP-REFS.md` —el hash **dentro** de una orden, no solo—, así que la comprobación **no lo miraba** y publicaba `50 vivas · 0 muertas` con `23b8d3c` muerto desde el borrado de las ramas `ccb/w*` (trampa 115; **no** está en el `commit-map` del 31/08, luego no fue la reescritura de historia). **Es la trampa 66 sobre el instrumento del propio repositorio:** una sonda que sólo mira donde el defecto ya se corrigió confirma su corrección y nada más. El remedio es barato y hay que medirlo antes de adoptarlo: buscar **todo** `[0-9a-f]{7,40}` que parezca un hash produce falsos positivos con `sha256`, `md5` y componentes de huella —lo dice la propia trampa 102, cuya primera sonda dio *«243 hashes citados, 0 vivos»* por eso—, así que la ampliación razonable es reconocer también `git show <hash>:`, `git log <hash>` y `<hash>..<hash>`. **Y el corolario general: cuando una comprobación nazca de un incidente, el patrón que se le escribe describe ese incidente, no la clase entera.**

### 5.4 Decisión del usuario — `.mcp.json` versionado

**MEDIDO:** `git ls-files .mcp.json` lo devuelve, y contiene **5** rutas absolutas a
`D:\Work\research\FileX\.venv-*`. Un tercero que clone se encuentra una configuración MCP que
**no funciona en ninguna otra máquina**. Las salidas son excluirlo del repositorio y dejar un
`.mcp.json.ejemplo` con rutas relativas, o dejarlo y documentarlo. **No lo he tocado porque
es la configuración viva de la máquina**, y romperla no es una decisión de documentación.

---

## 6. Estado de `ci/integridad.py` al entregar

**9 de 9 en las cuatro comprobaciones intermedias.** Al añadir este informe, la comprobación
`informes-registrados` pasa a fallar —exige que todo `bench/*.md` esté citado en
`ESTADO-Y-REPARTO.md` §1— y el resultado queda en **8 de 9 hasta que el maestro registre este
fichero**, que es el reparto declarado en el encargo. **Ninguna de las otras ocho se movió**,
y en particular `trampas` sigue en **119, sin huecos**, con los tres sitios de acuerdo.

## 7. Lo que queda PENDIENTE

1. **La cifra de suite del encargo (§1.1)** no se pudo rastrear a ningún informe.
2. **`.mcp.json`**, `filex/api.py:62` y `filex/mcp.py:42` siguen con rutas absolutas de esta
   máquina: son decisiones fuera de mi alcance (§4, §5.4).
3. **La trampa 120 propuesta (§5.3)** está medida pero no escrita: `CLAUDE.md` es del maestro.
4. **`HUECOS.md` y `ANALISIS-COMPLETO.md` conservan cifras del 19–21/08 que mediciones
   posteriores matizaron** —el ×8,39 de HEVC, el «6,3 puntos» del evaluador ciego, el
   `clamp(nativos, 100, 200)`—. **Están declaradas como fechadas, no corregidas en su
   sitio.** Corregirlas es un trabajo de contenido, no de forma, y quien lo haga debe
   reproducir cada medida antes de tocarla (trampa 58).

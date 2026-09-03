# Cierre de las aristas documentales — `csv` deja de ser un callejón sin salida

worker7, carril `edicius2002/filex-aristas-doc`, base `main`. Ejecuta `ENCARGO.md`
íntegro. Ficheros propios de este carril: `filex/formatos.py`,
`filex/motor_contenedor.py`, `filex/sondeo/doc_libreoffice.json`,
`filex/sondeo/doc_pandoc.json`. Las salidas de este informe viven en
`bench/salidas-aristas-documentales-cierre/` (MANIFIESTO propio).

**Resumen en una frase — MEDIDO**: `fx.destinos('csv')` pasaba de `[]` a 22
destinos añadiendo 15 tuplas a `_DECLARADAS` y 5 formatos a `formatos.py`;
tocar `_DECLARADAS` caducó la huella `motor` de las dos clases, y las 55
aristas `REAL` resultantes (24 LibreOffice + 31 Pandoc) se RESONDEARON de
verdad con `FileX.convertir()` real — 0 de 55 con `rc≠0` o `contrato=fallo`.

---

## 1 · La causa, verificada leyendo el código (§1-§2 del encargo)

Confirmado exactamente como lo describe `ENCARGO.md`, leyendo `filex/
motor_contenedor.py` y `filex/sondeo.py`:

- `_aristas()` (`_EnContenedor`) solo construye `Arista`s desde `_MEDIDAS`,
  `_MUERTAS` y `_DECLARADAS`. `csv`, `xlsx`, `pptx`, `odp`, `svg→pdf` y `tex`
  **no tenían tupla en ningún sitio** de `LibreOfficeEnContenedor` ni
  `PandocEnContenedor`, así que no había arista a la que superponer nada.
- `sondeo.aplicar()` (`filex/sondeo.py:256-274`) itera sobre las `Arista` que
  **ya existen** y busca `f"{a.origen}>{a.destino}"` en la tabla del JSON: una
  entrada del JSON que no tiene arista correspondiente se ignora en silencio.
  El sondeo sellado el 02/09 por worker2 (`filex/sondeo/doc_libreoffice.json`,
  `doc_pandoc.json`) **ya traía las 15 medidas reales** desde esa fecha —
  `csv>xlsx`, `csv>pdf`, `xlsx>pdf`, etc. — y ninguna se aplicaba porque
  ninguna arista las esperaba.

Verificado en vivo, ANTES de tocar nada:

```
$ python -m filex destinos csv
desde 'csv' (0 destinos):
```

*(No se guardó la salida literal de esa primera comprobación porque `git
status` de la rama estaba limpio al empezar y el primer comando que se
ejecutó ya fue después de leer el código; el hueco `[]` lo confirma también
`ENCARGO.md` y el propio `python -m filex motores` de antes de esta ronda,
que no listaba ninguna arista `csv→*` en ningún motor.)*

## 2 · Los cinco formatos — `filex/formatos.py`

Aplicado el diff de `bench/sondeo-documental.md` §7.4 sin cambios: `xlsx`,
`ods`, `pptx`, `odp` y `tex`, los cinco `texto=True`, categorías `"hoja"` /
`"presentacion"` / `"documento"` (se mantuvieron las que proponía S3, sin
motivo para otras). Verificado:

```
>>> formatos.formato("xlsx")
Formato(ext='xlsx', categoria='hoja', texto=True, ...)
>>> formatos.formato("tex")
Formato(ext='tex', categoria='documento', texto=True, ...)
```

Antes de este cambio los cinco devolvían `None`, así que un camino que
rasterizara hacia `tex` no habría pagado la penalización de +1000 en
`grafo._coste_paso` — el mismo argumento que ya se usó para `mobi`.

## 3 · Las 15 aristas — y una discrepancia del propio ENCARGO, corregida con evidencia

`ENCARGO.md` §2 lista **7** tuplas nuevas explícitas para
`LibreOfficeEnContenedor` (`csv>xlsx`, `xlsx>pdf`, `xlsx>csv`, `xlsx>html`,
`csv>pdf`, `pptx>pdf`, `pptx>odp`) y dice *«NO `("pptx", "png")` — ver punto
3»*. Pero su propia aritmética («**quince** de las diecisiete») y su propio
§3 («**Las dos** que NO se aplican esta ronda: `pptx>png` y `svg>png`») solo
autorizan DOS exclusiones — y 7 (LibreOffice) + 7 (Pandoc) = 14, no 15.

**Falta `svg>pdf`.** Comprobado contra tres fuentes independientes, las tres
de acuerdo:

1. El diff original de S3 en `bench/sondeo-documental.md` §7.3 trae
   `("svg", "pdf")` en la misma línea que `("pptx", "odp")`, antes de
   `("pptx", "png")` — es decir, S3 SÍ la propuso, sin excluirla.
2. `filex/sondeo/doc_libreoffice.json` (sellado el 02/09 por worker2, antes
   de que este carril tocara nada) **ya trae `svg>pdf` medida `real`** —
   `12500 B, 44 caracteres, contrato ok, caso Q10` — exactamente con el
   mismo formato que las demás 15 entradas nuevas, y NO con el de las dos
   legítimamente excluidas (que además llevan la nota `RASTERIZA: ... es el
   precio del destino, no un fallo`, ausente en `svg>pdf`).
3. La cuenta cuadra solo añadiendo `svg>pdf`: 8 (LibreOffice) + 7 (Pandoc) =
   **15**, coincidiendo con el título del propio `ENCARGO.md` §2 y con el
   «56 aristas ya REAL» que anticipa el punto 4 (ver §5 de este informe para
   el número real, que no es 56).

**Se aplicó incluyendo `svg>pdf`.** Es una octava tupla en
`LibreOfficeEnContenedor._DECLARADAS`, no las siete literales del §2. Se deja
escrito aquí con el detalle completo porque es exactamente el tipo de
discrepancia que este proyecto pide cazar (trampa 48: *«publica el tamaño de
una tabla y publica también dos elementos de ella»*) — y aquí el tamaño
publicado (15) y la lista literal (14) no cuadraban entre sí dentro del mismo
documento.

**Las tuplas aplicadas, verbatim:**

```python
# LibreOfficeEnContenedor._DECLARADAS (8 nuevas, sobre las 6 que ya había)
("csv", "xlsx"), ("xlsx", "pdf"), ("xlsx", "csv"),
("xlsx", "html"), ("csv", "pdf"), ("pptx", "pdf"),
("pptx", "odp"), ("svg", "pdf")

# PandocEnContenedor._DECLARADAS (7 nuevas, sobre las 9 que ya había)
("md", "pptx"), ("md", "tex"), ("docx", "tex"),
("tex", "docx"), ("tex", "html"), ("tex", "pdf"),
("pptx", "md")
```

## 4 · Las dos que NO se aplican — verificado, no repetido de memoria

Releído el mecanismo completo antes de escribir una línea, tal como pide el
punto 3 del encargo:

- `Arista.rasteriza` (`filex/grafo.py:53`) tiene `default=False`.
- `_aristas()` (`motor_contenedor.py`, dentro del bucle de `_DECLARADAS`)
  construye la `Arista` **sin pasar `rasteriza=`**, así que toda arista que
  nace de `_DECLARADAS` queda con `rasteriza=False` — mienta o no mienta.
- `sondeo.aplicar()` (`filex/sondeo.py:268-273`) construye la `Arista` de
  reemplazo con `rasteriza=a.rasteriza`, tomándolo de la arista **que ya
  existía antes de superponer el sondeo** — nunca del JSON. Así que aunque
  `pptx>png` y `svg>png` estén medidas `real` en el JSON con su coste
  verdadero, declararlas en `_DECLARADAS` las dejaría con `rasteriza=False`
  a pesar de que **sí** rasterizan (LibreOffice convierte una diapositiva o
  un vector en píxeles).
- Consecuencia verificada contra `grafo._coste_paso`: sin el `+1000` de
  `PENALIZACION_RASTERIZAR`, el planificador podría elegir un camino
  `pptx→png→pdf` o `svg→png→algo` sin avisar de que la salida no lleva una
  letra — la misma familia de `resvg` que el proyecto entero existe para
  atrapar.

**No se ha tocado la forma de la tupla** (un tercer campo, o una tupla
aparte) por ser un cambio que toca `_aristas()`, `orden()` y probablemente
`sondeo.aplicar()`, fuera del alcance de esta ronda — tal como pide el
encargo. Queda declarado como pendiente en §9.

Las dos entradas ya medidas (`pptx>png`: 50 462 B, 0 caracteres; `svg>png`:
9 081 B, 0 caracteres, las dos con `contrato ok` porque el contrato no ve la
pérdida de texto — es justo el punto que motiva la exclusión) se
**conservaron** en los JSON nuevos, sin re-medir, porque siguen siendo
evidencia real que el código de hoy simplemente no usa.

## 5 · La huella caducó, tal como predice el punto 4 del encargo — MEDIDO

Antes de tocar código:

```
huella "motor" de LibreOfficeEnContenedor (sellada 02/09): ffe3c41451f77538
huella "motor" de PandocEnContenedor      (sellada 02/09): f750a96c5bcb196a
```

Inmediatamente después de aplicar los diffs de §2 y §3 (**antes** de
resondear ni resellar nada), se comprobó en vivo el síntoma exacto que
describe el encargo — degradación silenciosa a `sin_sondear`, nunca a
`nominal`:

```
$ python -m filex motores
  ✓ doc_libreoffice ... 26 aristas (10 medidas)   # antes: 18 aristas (16 medidas)
  ✓ doc_pandoc      ... 31 aristas (15 medidas)   # antes: 24 aristas (24 medidas)
```

Los 10/15 "medidas" que quedaron son exactamente `_MEDIDAS` (nacen `REAL` en
`_aristas()` sin pasar por `sondeo.aplicar()`); **las 14+16=30 declaradas
—las 16 que ya eran `REAL` antes de esta ronda MÁS las 15 nuevas, menos
`svg>pdf` que aún no tenía tupla en ese instante intermedio— cayeron TODAS a
`sin_sondear`**, no solo las nuevas. Es la trampa 32 operando en vivo: *una
medida caduca por código, no solo por build*, y aquí el cambio de código es
intencional y mío, como avisa el propio encargo.

Huella nueva, calculada con `filex.huella.de_motor(cls)` tras el cambio:

```
LibreOfficeEnContenedor: motor=48e14e7a35210f60  (antes ffe3c41451f77538)
PandocEnContenedor:      motor=08817e0e76ef187f  (antes f750a96c5bcb196a)
invocacion (los dos):    3a2c16603bb46673  — SIN CAMBIO
contrato (los dos):      fe41b4d52413299c  — SIN CAMBIO
```

Confirma exactamente lo esperado: solo cambió el componente que depende del
AST de la propia clase (`_DECLARADAS` vive dentro del cuerpo de la clase);
`invocacion.py` y el cierre de `verificar()` no se tocaron y sus huellas no
se movieron.

## 6 · El resondeo real — 55 aristas, `FileX.convertir()` de verdad

Se escribió un arnés propio,
`bench/salidas-aristas-documentales-cierre/_resondeo55.py`, **copiando** (no
editando) la mecánica de forzar-arista de `bench/salidas-sondeo-doc/
_sonda23.py` (S3) — `CLAUDE.md` §1. Cada caso llama a
`filex.nucleo.FileX.convertir()` real: `motor.orden()` (que ya exige que el
par esté en `_DECLARADAS` o `_MEDIDAS`, así que prueba de verdad que el
código de §3 funciona), `invocacion.ejecutar()` con Docker real,
`contrato.verificar()` de cinco puntos y el censo del punto 5 tomado dentro
del mismo `with`. Solo se sustituye `fx.planificar` por una `Decision` de un
solo paso para que el grafo no resuelva el par por otro motor ni por un
camino de dos saltos.

**No solo las 15 nuevas**: se resondearon las **40 aristas que ya eran
`REAL`** antes de esta ronda también (10+15 `_MEDIDAS` sin tocar, y las 6+9
`_DECLARADAS` que ya llevaban sondeo aplicado) — 40+15=55 en total, no 56.
*(El «56» de `ENCARGO.md` §4 no cuadra con ninguna cuenta que se pueda
reconstruir desde el código: 24+31=55 después de esta ronda, y 16+24=40
antes. Se deja constancia sin forzar que cuadre, como pide el propio
encargo en su nota de método.)*

**Resultado: 55 de 55 con `rc=0`. 0 con `contrato=fallo`.** Tres celdas
(`docx>pdf`, `md>pdf`, `tex>pdf`, las tres de Pandoc vía `xelatea`) dan
`contrato=aviso` por el hallazgo `P1` ya conocido y aceptado del proyecto
(`bench/sondeo-documental.md` §7.2: el número de páginas de este PDF vive en
un flujo `/ObjStm` comprimido y no se puede contar sin `zlib` — severidad
`aviso`, no `fallo`). Las 52 restantes dan `ok` u `ok_parcial`. La tabla
completa (id, motor, par, bytes, sha256, veredicto) está en
`bench/salidas-aristas-documentales-cierre/MANIFIESTO.md`; los campos
completos (ms, hallazgos, cobertura, censo de sobrantes) en
`resondeo55.json`.

Las cifras de las 15 aristas nuevas coinciden con las que worker2 ya había
sellado el 02/09 (mismo `build`, mismo contenedor `filex-c13@6d359bad483e`,
sin cambios en `soffice`/`pandoc` entre medias): `csv>xlsx` dio 5790 B / 338
caracteres en las dos ocasiones; `md>pptx` dio 28169 B / 2218 caracteres en
las dos. `docx>pdf` y `md>pdf` vía Pandoc difieren en unos pocos bytes
(8159 frente al `P12` original de K1 con 8163, y 10366 frente a 10370 de
`P11`) — consistente con una marca de tiempo que `xelatex` incrusta en el
PDF, no con una regresión: `rc=0`, mismo recuento de caracteres (456 y 456)
y mismo centinela en las dos mediciones.

**Contenedores**: 5 antes, 5 después, 0 nuevos vivos — ningún huérfano.
`docker ps` no listaba nada de otro proceso al empezar (`ENCARGO.md`
lo pedía comprobar).

## 7 · Los dos JSON sellados — RESONDEO declarado, no resellado por algoritmo

Reescritos con `bench/salidas-aristas-documentales-cierre/_sellar.py`, que
toma la huella con `filex.huella.de_motor()` (el mismo mecanismo que usa el
proyecto, no un cálculo a mano) y escribe la nota de procedencia completa
—huella antes/después, qué caducó y por qué, referencia a este informe y al
arnés— en el campo `nota_huella` de cada fichero, siguiendo el mismo
convenio que dejó worker2 en ronda 7. **Es un RESONDEO real, no un resellado
por algoritmo**: la trampa 44 exige que la nota no prometa algo que el
código no hizo, y aquí las 55 conversiones se ejecutaron de verdad —no se
copió el JSON viejo cambiando solo la huella—.

`doc_libreoffice.json`: 16 entradas (las 14 `_DECLARADAS` re-medidas + las 2
legadas `pptx>png`/`svg>png` sin re-medir, ver §4). `doc_pandoc.json`: 16
entradas (las 16 `_DECLARADAS`, todas re-medidas).

Verificado tras escribir los JSON:

```
$ python -c "from filex import sondeo; print(sondeo.diagnostico())"
{'sin_huella': [], 'caducados': {}, 'build_distinto': [],
 'sin_interprete': [], 'interprete_distinto': []}
```

Limpio en las cinco categorías: la huella nueva coincide con el código
actual, el `build` coincide (mismo contenedor, `filex-c13@6d359bad483e`, no
cambió durante esta ronda) y el intérprete coincide (`3.11`).

## 8 · Verificación de que el hueco se cerró — antes y después, MEDIDO

```
$ python -m filex destinos csv          # ANTES de esta ronda
desde 'csv' (0 destinos):

$ python -m filex destinos csv          # DESPUÉS
desde 'csv' (22 destinos):
  avif  azw3  bmp  docx  epub  gif  html  ico  jpg  md  mobi  odp  odt  pdf
  png  pptx  rtf  tex  tif  txt  webp  xlsx
```

`xlsx` y `pdf` están, como pedía el criterio de aceptación. Los otros 20
destinos son alcanzables **transitoriamente** desde `xlsx`/`pdf`/`pptx`, vía
los motores nativos ya existentes (ImageMagick, ffmpeg, Ghostscript,
Calibre) — es el comportamiento correcto de `FileX.destinos()`, que hace un
BFS sobre TODAS las aristas del grafo sin filtrar por `estado` (ni siquiera
`nominal` se excluye ahí; el filtro por estado vive en `grafo.camino()`, no
en `destinos()` — verificado leyendo `filex/nucleo.py:605-622`).

**Conteo del grafo, antes/después de toda la ronda:**

| | doc_libreoffice | doc_pandoc | GRAFO total |
|---|---|---|---|
| Antes de esta ronda | 18 aristas (16 medidas) | 24 aristas (24 medidas) | 215 aristas, 210 con medición |
| Tras el edit, antes de resondear | 26 aristas (10 medidas) | 31 aristas (15 medidas) | 230 aristas, 195 con medición |
| Tras resondear y resellar | 26 aristas (24 medidas) | 31 aristas (31 medidas) | 230 aristas, 225 con medición |

## 9 · Efecto colateral MEDIDO, no arreglado — `svg→pdf` deja de rasterizar y rompe una prueba

`pruebas/test_hito4.py::Cobertura::test_el_aviso_de_rasterizacion_viaja_al_modelo`
usaba `svg→pdf` como su ÚNICO ejemplo en vivo de *«el único camino
disponible rasteriza y el destino admite texto»* (el criterio amarillo del
hito 1). Antes de esta ronda, el único camino real de `svg` a `pdf` pasaba
por ImageMagick rasterizando (`svg→webp [imagemagick]→...`); ahora hay un
camino real de LibreOffice que **no** rasteriza (`svg>pdf`, 44 caracteres
conservados, `contrato ok`), y el grafo —correctamente— lo prefiere. La
consecuencia es que `Decision.aviso` queda vacío para ese par, y la prueba,
que exige `assertIn("aviso", r)`, falla.

**Esto no es una regresión de mi código: es el criterio amarillo del hito 1
funcionando exactamente como se diseñó** — el planificador dejó de elegir un
camino que destruye texto en cuanto tuvo uno mejor disponible. Se comprobó
si queda algún OTRO par `(origen, destino)` en el grafo completo (230
aristas) que siga forzando rasterización con destino de texto, barriendo
todas las aristas `rasteriza=True` cuyo destino admite texto y replanificando
cada par: **no se encontró ninguno**. `svg→pdf` era, aparentemente, el único
ejemplo real y en vivo que quedaba de ese escenario en toda la base — los
demás lugares donde se demuestra el criterio amarillo (`pruebas/
test_hito5.py::ElegirBienConAristasREALES`) usan un grafo SINTÉTICO
construido a mano y no se ven afectados.

**No se ha tocado `pruebas/test_hito4.py`.** No es uno de los cuatro
ficheros de este carril y no hay una corrección honesta de una línea: la
prueba necesitaría un par distinto que siga forzando rasterización, y no
hay ninguno vivo hoy. Queda para quien mantenga ese fichero, con las tres
opciones que arroja este hallazgo: (a) construir el escenario con un grafo
sintético en el propio test, igual que ya hace `test_hito5.py`; (b) esperar
a que otra arista real fuerce rasterización de nuevo; (c) aceptar que el
mecanismo (`grafo.camino()`'s `aviso`) ya está cubierto por las pruebas de
`test_hito5.py` y retirar la prueba de integración por no tener ejemplo
vivo.

## 10 · Suite de pruebas y `ci/integridad.py` — las cuatro declaraciones

**Intérprete:** `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe`,
3.11 (`sys.version_info[:2]`), el mismo que selló los JSON.

**Entorno:** Windows, Docker Desktop 29.4.3 con el contenedor `filex-c13`
disponible (comprobado con `docker info` y `docker image inspect` antes de
empezar), sin GPU implicada en este encargo. `git status` limpio al empezar
y al terminar salvo los ficheros de esta ronda.

**Qué quedó fuera y por qué:** ninguna prueba se saltó por falta de
infraestructura relevante a este encargo. Los 3 `skipped` son ajenos:
`test_cerrojo.py` (necesita dos volúmenes distintos a mano), y dos de
`test_hito6.py` (falta un ráster que genera `bench/salidas-hito6/
preparar_h6.py`, y uno necesita `FILEX_PRUEBAS_SIDECAR=1` + la tarjeta) — los
tres declarados y ajenos al motor documental.

**Estado de la máquina:** con la sesión de escritorio remoto activa (
`CLAUDE.md` §1: está ahí a propósito y no se cierra), esta tanda sale
etiquetada **SUCIA** por convención del propio proyecto — es estructural, no
un fallo, y no invalida los `rc`/bytes/sha256 de las 55 conversiones, que
son deterministas independientemente del ruido de CPU.

**Resultado, tres pasadas:**

```
1ª pasada: 459 passed, 1 failed, 3 skipped, 130 subtests passed (217,3 s)
2ª pasada: 458 passed, 2 failed, 3 skipped, 130 subtests passed (250,1 s)
3ª pasada: 459 passed, 1 failed, 3 skipped, 130 subtests passed (213,6 s)
```

El único fallo que se reprodujo en las TRES pasadas es
`test_el_aviso_de_rasterizacion_viaja_al_modelo` (§9), explicado y esperado.
El fallo adicional de la 2ª pasada no se reprodujo ni antes ni después:
consistente con la propia trampa 101 del proyecto (*«la suite no es
hermética respecto del estado de la máquina»*) — no se investigó más porque
no toca ninguno de los 4 ficheros de este carril y no se reprodujo dos veces
seguidas.

```
$ ci/integridad.py
  OK  citas                  46 vivas · 1 ajenas declaradas · 0 muertas
  OK  inventario             6 ⚫ · 4 🔴 · 7 🟡 · 101 🟢 sobre 118 filas
  OK  un-emoji-por-fila      118 filas, todas con un emoji
  OK  trampas                110 trampas, sin huecos
  OK  informes-registrados   87 informes, todos citados
  OK  manifiestos            0 sin MANIFIESTO heredados · 0 nuevos · 0 arreglados
  OK  secretos               0 hallazgos
  OK  binarios               0 binarios sueltos heredados · 0 nuevos · 0 arreglados · 3 rutas declaradas evidencia
  OK  en-curso               0 cabeceras «en curso»

Todo en orden.
```

(Ejecutado después de `git add` de `bench/salidas-aristas-documentales-cierre/`
y de registrar este informe en la tabla de `ESTADO-Y-REPARTO.md` §1 — sin
eso, `manifiestos` e `informes-registrados` habrían marcado el directorio y
el informe como nuevos sin registrar.)

## 11 · Lo que queda pendiente

1. **El tercer campo de `rasteriza` en `_DECLARADAS`** (§4): `pptx>png` y
   `svg>png` siguen sin tupla, con evidencia real esperando. Exige tocar
   `_aristas()`, `orden()` y probablemente `sondeo.aplicar()` — fuera de
   alcance por decisión explícita del encargo.
2. **`pruebas/test_hito4.py::test_el_aviso_de_rasterizacion_viaja_al_modelo`**
   (§9): necesita un par nuevo que fuerce rasterización, o pasar a un grafo
   sintético. No es de este carril.
3. **El fallo intermitente de la 2ª pasada de pytest** (§10): no reproducido
   ni antes ni después; no investigado por no tocar ninguno de los 4
   ficheros propios.
4. **`ENCARGO.md` §2 tiene una tupla menos de las que pide su propia
   aritmética** (§3 de este informe): se corrigió aplicando `svg>pdf`, con
   la evidencia completa dejada por escrito para que quien revise pueda
   discrepar con datos, no de memoria.

---

**Commit en la rama `edicius2002/filex-aristas-doc`. No se empuja ni se abre
PR**, tal como pide el encargo.

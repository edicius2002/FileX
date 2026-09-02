# Ronda 6 — `C31` (RAM, `.pcd`, TGA/CUR), `C32` (la corrección) y `C40` (los 3 binarios)

**Tanda:** worker2, carril CPU/Docker. **Rama:** `edicius2002/filex-cpu`, al día con `main`
(`eaaf4de`) antes de empezar. **Entorno:** Windows 10, sin GPU; venvs en
`D:\Work\research\FileX\` (el *worktree* no trae ninguno). Docker Desktop / WSL2 levantados.

**Aviso de N30:** no salió roja en ninguna de las corridas de esta ronda (§4). Si hubiera
salido, per el encargo, no era mía y no se tocaba.

---

## 0. Antes de tocar nada: trampa 58, aplicada a las TRES filas

El encargo insiste en reproducir antes de creer un informe de hace once días
(`bench/hito3-mudanza.md`, 22/08). Se hizo, y cambió el plan: **`.pcd` YA NO es un defecto
vivo** — lo cerró `C37`/F2 el 28/08 y tiene pruebas propias
(`pruebas/test_firmas_cierre.py::MarcadoresMasAllaDel512`) que ya pasaban antes de que yo
tocara nada. Reproducido de nuevo con un fichero real (`magick tipico.png real.pcd`, `rc=0`,
788 480 B): `veredicto: ok_parcial`, cero `fallo`. **Los otros dos defectos de `C31` SÍ
seguían vivos**, y se arreglaron los dos:

| Defecto | Estado al empezar | Estado al terminar |
|---|---|---|
| (a) RAM de `_datos` | **×21,3 medido, sin arreglar** | **Arreglado. ×6,2** |
| (b) `.pcd` falso positivo | **Arreglado el 28/08 (C37), la fila del inventario no se había actualizado** | Sin tocar, reverificado |
| (c) TGA/CUR falso negativo | **Confirmado en ejecución, sin arreglar** | **Arreglado** |

---

## 1. `C31(a)` — la RAM de `_datos`: de ×21,3 a ×6,2, MEDIDO

### 1.1 El diagnóstico de `hito3-mudanza.md` era correcto; su remedio propuesto, parcial

El culpable no era `fh.read()`: era `d["csv_filas"] = filas`, materializado con
`list(csv.reader(...))` y retenido dentro de la sonda. Pero **quitar solo la asignación no
basta** — con `tracemalloc`, el "pico" ya incluye el momento en que `list(...)` termina de
construirse, se retenga después o no. La reducción real exige el arreglo que el propio informe
recomendaba y no aplicaba: **un solo recorrido de `csv.reader` sin materializar la lista
completa**, calculando en línea los cuatro agregados que las reglas D1/D2 consumen
(`csv_n_filas`, `csv_n_campos_por_fila`, `csv_cabecera`, `filas_datos`).

**Verificado antes de tocar nada que nada más lee `csv_filas`** (`grep` sobre todo el
repositorio: la única aparición viva era la asignación misma) — el propio informe avisaba de
reglas que sí la leían y no era cierto sobre el código de hoy.

### 1.2 El arreglo — `filex/verificador.py`, `_datos()`

```python
cabecera = None
n_filas = 0
campos_por_fila = []
try:
    for fila in csv.reader(io.StringIO(texto, newline="")):
        if not fila:
            continue
        if cabecera is None:
            cabecera = fila
        campos_por_fila.append(len(fila))
        n_filas += 1
except csv.Error as e:
    ...  # misma degradación que antes: 0 filas, sin `filas`
```

La rama de `csv.Error` (el "TXT" de ImageMagick) **no cambia**: nunca llegó a materializar
`filas`, y el arreglo no la toca — es el control de que la mejora viene de donde se dice, no
de un efecto colateral en otra parte.

### 1.3 MEDIDO — `bench/salidas-pcd-y-memoria/_datos_ram_r6.py` (copia del arnés de K2, sin editar)

| MB nominal | Caso | Pico ANTES (×fichero) | Pico DESPUÉS (×fichero) |
|---:|---|---:|---:|
| 1 | csv normal | ×21,36 | **×6,21** |
| 8 | csv normal | ×21,33 | **×6,17** |
| 32 | csv normal | ×21,34 | **×6,18** |
| 1/8/32 | campo largo (degradada) | ×7,50/7,06/7,02 | **igual** (7,50/7,06/7,02) |

Datos crudos y orden exacta en `bench/salidas-pcd-y-memoria/MANIFIESTO.md`. **Nota de volumen**:
esta tabla se midió desde `C:` (este *worktree*); el ×21,3 histórico se midió desde `D:`. Es
otro volumen, no solo otra tanda — se declara, no se compara a la centésima.

Sobre el TXT de 156 520 548 B de ImageMagick que motivó la medida original: **≈1,1 GB de pico
pasa a ≈970 MB** en la rama degradada (sin cambio, porque esa rama no materializaba nada) — el
caso que de verdad se arregla es cualquier CSV real de tamaño comparable que SÍ entra por la
rama normal, no el TXT en sí.

### 1.4 Pruebas — `pruebas/test_datos_csv.py` (nuevo)

- **Correctud**: los cuatro agregados coinciden, campo a campo, con una reimplementación
  DELIBERADA del algoritmo viejo (el oráculo, no el código a probar) sobre seis casos —
  normal, líneas en blanco, solo cabecera, sin salto final, campos desiguales, vacío.
- **`csv_filas` ya no se escribe** — prueba explícita, para que una regresión futura no la
  reintroduzca en silencio.
- **La rama degradada sigue igual.**
- **Integración**: D2 (`csv_n_campos_por_fila`) sigue disparando sobre un CSV real.
- **RAM, MEDIDO con `tracemalloc`** dentro de la propia suite (no solo en el arnés aparte):
  umbral de ×10 —con margen generoso sobre el ×6,2 medido y muy por debajo del ×21,3
  histórico— para que una regresión hacia `csv_filas` lo dispare sin ser un test frágil.

---

## 2. `C31(c)` — TGA/CUR: el falso negativo confirmado, cerrado

### 2.1 Reproducido primero, con la extensión exacta del informe

```
$ magick tipico.png real.tga   # 00 00 02 00 00 00 ... (tipo=2, sin mapa de color)
$ cp real.tga tga_como.cur
```

`firma_real('tga_como.cur') == 'cur'`; `verificar(..., {"destino":"cur"})` → `ok_parcial`,
**cero hallazgos**. Confirmado byte a byte lo que el informe describía.

### 2.2 El arreglo — la MISMA forma que ya existía dos líneas más arriba

`filex/verificador.py` ya resolvía JBIG/ICO así: *«un ICO válido no puede llevar 0 imágenes,
así que `00 00 01 00 00 00` nunca es un ICO»* — un patrón más largo y más específico, probado
ANTES que el corto, en la misma tabla `FIRMAS` (el primer match gana). Un CUR válido tampoco
puede llevar 0 imágenes (bytes 4-5), y `00 00 02 00 00 00` es exactamente lo que escribe
`magick` para el TGA sin ID ni mapa de color:

```python
(0, b"\x00\x00\x02\x00\x00\x00", "desconocido"),   # NUEVO, antes de "cur"
(0, b"\x00\x00\x02\x00", "cur"),
```

`"desconocido"` no es un formato inventado: es el mismo centinela que `firma_real()` ya
devuelve al final si nada casa, y ya está en `FIRMAS_INDEFINIDAS` (no dispara G6 por
coincidencia con la entrada). Con eso, `punto1_firma` compara `"desconocido"` contra
`{"cur", "ico"}`, no coincide, y dispara `G3 fallo` — el mecanismo ya existía, solo hacía falta
que la firma dejara de mentir.

### 2.3 MEDIDO — antes y después, y los dos controles que importan

| Caso | firma_real | veredicto |
|---|---|---|
| TGA como `.cur` (el falso negativo) | `cur` → **`desconocido`** | `ok_parcial` → **`fallo` (G3)** |
| TGA con su extensión `.tga` (control: no debe cambiar) | `cur` → `desconocido` | `ok_parcial` (sin cambio: `.tga` no tiene firma, `no_aplica`) |
| CUR sintético con cuenta=1 (control: un CUR real no puede volverse sospechoso) | `cur` (sin cambio) | `ok_parcial` (sin cambio) |
| ICO real (control: el patrón nuevo es de "cur", no toca "ico") | `ico` (sin cambio) | — |

Cinco pruebas nuevas en `pruebas/test_firmas_cierre.py::TGAEntregadoComoCUR`, con los cuatro
casos de la tabla más el hallazgo `G3` exacto que dispara.

### 2.4 Auditoría de la tabla en las DOS direcciones (trampa 73), tal como pedía el encargo

Repetida de forma independiente (no solo las pruebas ya existentes que cubren un subconjunto
con nombre):

- **Extensiones que esperan una firma inalcanzable: 0.** Limpio.
- **Firmas que ninguna extensión acepta: 7** — `alp`, `desconocido`, `iff`, `ilegible`, `rar`,
  `riff`, `vacio`. Cuatro son centinelas deliberados (`desconocido`, `ilegible`, `riff`,
  `vacio` — ya están en `FIRMAS_INDEFINIDAS`, orfandad esperada). **Quedan tres reales:
  `alp`, `iff`, `rar`** — `firma_real()` los sabe reconocer pero ninguna extensión los declara
  aceptables, así que un motor que algún día escriba `.alp`/`.iff`/`.rar` caería en
  `sin_vocabulario` en vez de `evaluado`. **PENDIENTE, no arreglado aquí**: decidir qué
  extensiones deberían aceptarlos es una medición nueva (¿qué motor los escribe realmente?,
  trampa 58), no una lectura rápida de la tabla — y no era parte de los tres defectos con
  medida ya en mano que pedía `C31`.

---

## 3. `C32` — la corrección, escrita por fin en `bench/firmas-contrato.md` §10

Los items 3 (`.pcd`), 4 (TGA/CUR) y 8 (RAM) del §10 quedan **tachados, no borrados**, con la
corrección fechada y firmada al lado — el patrón que ya usa el resto del repositorio. También
se corrigió el item 2 (la puerta "solo cuando la extensión lo pide"), que **trampa 44** obligaba
a marcar: dejarla sin corregir al lado de la corrección de los items 3/4/8, siendo la MISMA
deuda de `pict`/`pcd`, habría sido *arreglar la mitad*. Las cuatro correcciones citan su fuente
exacta (`hito3-mudanza.md`, `firmas-cierre.md`, y esta ronda) y no reescriben el texto de F1.

---

## 4. `C40` — los 3 binarios, decididos uno a uno (no en bloque)

**Lección de la trampa 106, aplicada:** decidir cada fichero por separado, no perdonarlos con
la misma frase. Los tres compartían la etiqueta *"salidas de terceros con byte declarado y sin
orden que las reproduzca"* en el inventario — **medido de nuevo, esa frase era cierta para dos
y falsa para uno.**

### 4.1 `trivial_converted.gif` — SÍ era reproducible. Se BORRÓ.

Leída la fuente de `ffmpeg-mcp-lite` (`repos/mcp-refs/ffmpeg-mcp-lite/src/ffmpeg_mcp_lite/tools/convert.py`,
todavía en disco aunque el venv que lo ejecuta esté borrado): el comando que arma es literal,
**sin un solo flag propio** cuando no se piden códec/escala —
`[ffmpeg, -i, <entrada>, -y, <salida>]`. Con el `ffmpeg` nativo de este proyecto:

```
$ ffmpeg -i corpus/video/trivial.mp4 -y trivial_converted.gif
$ sha256sum trivial_converted.gif
03f07fa28389cb574bb995ba91a3747409888dca9378da4eff07de2cb99927e7
```

**Idéntico byte a byte** al fichero que estaba versionado (mismo `sha256`, mismos 2 290 244 B),
**sin necesitar el venv `.venv-mcp-lite`** que `CLAUDE.md` §2 ya lista como borrado. Control
independiente: dos GIF nativos consecutivos del mismo fichero dieron el mismo `sha256` entre
sí también — el codificador GIF de este `ffmpeg` es determinista en esta máquina. **Borrado con
`git rm`**, con la orden y el `sha256` dejados en `bench/salidas-mcp-refs/MANIFIESTO.md` §9.

### 4.2 `vam_trivial.mkv` y `trivial_converted.webm` — NO son reproducibles, y ahora con mecanismo medido

Control que refuta la hipótesis fácil ("es el venv, o es la versión del tool"): reproducido con
el **mismo** `ffmpeg` nativo del proyecto, **dos veces seguidas**, mismo comando exacto que
`video-audio-mcp` usó (`-c copy`, sin reencodificar — su propia nota en el spec dice *"copy
funciona -> NO entra en fallback"*):

```
$ ffmpeg -i corpus/video/trivial.mp4 -c copy -f matroska t1.mkv
$ ffmpeg -i corpus/video/trivial.mp4 -c copy -f matroska t2.mkv
$ cmp t1.mkv t2.mkv
t1.mkv t2.mkv differ: byte 221
```

Mismo tamaño exacto (552 079 B — **el mismo que `vam_trivial.mkv`**), `sha256` distinto. Los
bytes que difieren son el campo EBML `0x73C5` (un UID de pista/segmento) — **libavformat lo
genera aleatoriamente en cada mux**, incluso copiando el flujo sin recodificar. Repetido con
WebM (`libvpx`/`libvorbis`): mismo patrón, mismo campo EBML, offset distinto pero el mismo
mecanismo. **No es un problema de venv ni de versión de herramienta: el formato en sí no
garantiza reproducibilidad byte a byte.** Confirma con mecanismo medido lo que el manifiesto
ya sospechaba con una frase genérica ("metadatos de timestamp").

**Declarados en `ci/evidencia-irreproducible.txt`**, con la medida citada. `ci/heredado.json`
queda con `"binarios": []`.

### 4.3 Estado final

| Fichero | Antes | Después |
|---|---|---|
| `trivial_converted.gif` | binario suelto heredado | **borrado**, reproducible (§4.1) |
| `vam_trivial.mkv` | binario suelto heredado | **declarado en evidencia-irreproducible.txt** (§4.2) |
| `trivial_converted.webm` | binario suelto heredado | **declarado en evidencia-irreproducible.txt** (§4.2) |

`ci/integridad.py` → `binarios`: **0 heredados · 0 nuevos · 0 arreglados · 3 rutas declaradas
evidencia** (era 1 antes de esta ronda — 2 nuevas líneas, `vam_trivial.mkv` y
`trivial_converted.webm`).

---

## 5. Efecto colateral esperado, y por qué NO se arregla en esta ronda: `test_sondeo` caduca

Arreglar `.pcd`... espera, no: arreglar TGA/CUR y la RAM de `_datos` **toca código dentro del
cierre de llamadas de `verificar()`** (`FIRMAS`, `_datos`). Eso mueve el componente `contrato`
de la huella de `filex/huella.py` — es exactamente el mecanismo que `C43` (ronda 5) cerró: **el
sistema está diseñado para que esto pase**, y aquí lo hace.

**MEDIDO, con el propio arnés del proyecto** (`bench/salidas-huella/resellar.py
--comprobar`, sin escribir): las cinco huellas guardadas en `filex/sondeo/*.json` **NO
coinciden** con las que calcula el algoritmo de HOY sobre el árbol de ahora
(`coincide_con_algoritmo_viejo: False` en los cinco). Es la comprobación exacta que exige la
trampa 61 antes de decidir entre resellar y resondear, y da la respuesta: **esto NO es un
cambio de algoritmo — es código real que cambió. Hay que RESONDEAR, no resellar.**

Consecuencia en la suite: `pruebas/test_sondeo.py::SelladoDelDisco::test_ningun_motor_disponible_tiene_el_sondeo_caducado`
**falla**, con los cinco motores (`imagemagick`, `ffmpeg`, `doc_calibre`, `doc_libreoffice`,
`doc_pandoc`) reportando `['contrato']` caducado. **No lo arreglo editando la huella a mano**
—eso sería exactamente el sellado a ciegas que `C43` vino a evitar— y **no resondeo los cinco
motores en esta ronda**: son medidas reales sobre ImageMagick/ffmpeg/LibreOffice/Pandoc/Calibre,
un trabajo de la escala de los sondeos originales (`bench/sondeo-imagemagick.md`,
`bench/sondeo-ffmpeg.md`, etc.), no algo que quepa al final de `C31`/`C32`/`C40`.

**Se deja rojo, a propósito, y se declara aquí con todas sus letras**: es el sistema de huella
funcionando exactamente como se diseñó, no un fallo mío que arreglar. **PENDIENTE nuevo:
resondear los cinco motores tras `C31`** — cualquiera que lo haga puede partir de
`bench/salidas-huella/resellar.py --comprobar` para confirmar en cada fichero si de verdad hace
falta resondear o si el árbol ya cambió más desde entonces.

---

## 6. Verificación de este PR

- **MEDIDO — suite integral**, `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe -m pytest pruebas/ -q`:
  **451 passed, 3 skipped, 127 subtests passed, 2 failed** en 207,62 s.
  - **1 fallo ESPERADO y explicado** (§5): `test_sondeo::SelladoDelDisco::test_ningun_motor_disponible_tiene_el_sondeo_caducado`.
    No es ruido ni una regresión — es determinista, mecanicista, y confirmado por el propio
    arnés `resellar.py` del proyecto.
  - **1 fallo de RUIDO de máquina**, no de código: `test_cancelacion_procesos::DuenoMuerto::test_un_working_sin_dueno_vivo_se_detecta_y_se_cierra`
    (el mismo test que ya salió flaky en la línea base de la ronda 5, mismo mecanismo — trampa
    101). **Pasa aislado** (1 passed en 2,08 s). No toca ningún módulo de esta rama.
- **Intérprete:** `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe` = **3.11.9**
  (el mismo que sella `filex/sondeo/*.json`, aunque esta ronda no resondea nada).
- **Entorno:** Windows 10, *worktree* en `C:\`. Docker Desktop / WSL2 **UP** durante toda la
  tanda (verificado con `docker info` antes de la suite; usado además para el corte de
  reproducibilidad de `.mkv`/`.webm`/`.gif` de §4, con el `ffmpeg` **nativo** del proyecto, no
  contenedores).
- **Qué quedó fuera y por qué:** resondear los cinco motores tras `C31` (§5, declarado, fuera de
  alcance); las tres firmas huérfanas `alp`/`iff`/`rar` de la auditoría bidireccional (§2.4,
  necesitan medir qué motor las escribe antes de decidir la extensión); `git_ls-files` confirma
  que todo lo tocado está `git add`, incluida la línea de `evidencia-irreproducible.txt` y el
  `git rm` del GIF.
- **Estado de la máquina:** compartida durante toda la tanda — el único fallo de timing (arriba)
  es consistente con contención, no con un defecto de esta rama.
- **`ci/integridad.py`:** **MEDIDO**, 9/9 en verde (`Todo en orden.`), con `PYTHONIOENCODING=utf-8`
  (la consola de Windows usa `cp1252` por defecto y el script emite emoji — matiz de invocación,
  no un defecto del script, ya observado en la ronda anterior).

## 7. Riesgos y pendientes

- **Resondear los cinco motores** (§5) es el pendiente más caro y más urgente que deja esta
  ronda: mientras no se haga, esos cinco ficheros de `filex/sondeo/*.json` se aplican en modo
  `sin_sondear` para el componente `contrato` — degradado, no falso, pero degradado.
- **`alp`/`iff`/`rar` huérfanas** (§2.4): tres líneas de tabla, PENDIENTE de decidir con medida,
  no con lectura.
- **Candidatas a trampa nueva de `CLAUDE.md`**, que no escribo yo (solo la consolidación toca
  maestros): (a) el UID EBML aleatorio de Matroska/WebM como causa MEDIDA de irreproducibilidad
  binaria, más general que "metadatos de timestamp"; (b) arreglar un defecto real del contrato
  casi siempre caduca `contrato` en todo el sondeo — el coste de una corrección de
  `verificador.py` no es solo la corrección, es el resondeo que sigue.

## Entrega

Commit en `edicius2002/filex-cpu`. No se empuja ni se abre PR — lo hace el maestro.

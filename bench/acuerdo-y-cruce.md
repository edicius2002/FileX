# Ronda 7 — la interacción `C43`/resondeo, `C20`, `C23`, y el resondeo pendiente

**Tanda:** worker2, carril CPU/Docker. **Rama:** `edicius2002/filex-cpu`. **Entorno:** Windows
10, sin GPU; venvs en `D:\Work\research\FileX\` (el *worktree* no trae ninguno). Docker Desktop
levantado durante toda la tanda. **Máquina cargada**, tal como avisaba el encargo: 24-28
procesos de Python simultáneos y CPU entre 63 % y 96 % en las muestras tomadas (declarado en
cada medición sensible al reloj).

**Orden seguido, tal como pedía el encargo:** primero la interacción de `C43` (§1, es una
corrección de diseño, no una medida que dependa de `C20`/`C23`), luego `C20` (§2) y `C23` (§3)
—que no tocan ningún módulo que decida aristas—, y **el resondeo al final** (§4), una sola vez.

---

## 0. Aviso de N30

No salió roja en ninguna de las **dos** corridas completas de la suite (§5). Si hubiera salido,
por el propio encargo, no era mía y no se tocaba.

---

## 1. La interacción `C43` ↔ resondeo — comprobada, y corregida antes de resondear

### 1.1 El riesgo, tal como lo planteaba el encargo

`C43` (ronda 5) hizo que la huella declare el intérprete de sellado y se niegue a comparar entre
intérpretes distintos. El sellado de esta ronda se hace con `.venv-mcp-filex` —**3.11.9,
Windows**—; el runner de la CI corre **3.11 sobre Linux**. El encargo pedía comprobar, no
deducir, si el sellado de hoy le sale «no comparable» al runner.

### 1.2 MEDIDO: la versión exacta de la CI, y por qué el diseño de `C43` (ronda 5) fallaba

```
$ gh run view <última ejecución de suite.yml> --log | grep "Successfully set up CPython"
Successfully set up CPython (3.11.16)
```

`.venv-mcp-filex` es **3.11.9**. La implementación de `C43` en la ronda 5 usaba
`platform.python_version()` completo —el triple mayor.menor.parche—, porque así se había medido
la trampa 105 (3.11.9 frente a 3.14.4, **dos MENORES distintas**). Con esa implementación,
sellar con 3.11.9 y comparar en el runner (3.11.16) declara **`interprete_distinto`
siempre**, en cada ejecución de la CI, aunque el código mida exactamente lo mismo: el propio
arreglo de `C43` habría bloqueado la fusión que vino a proteger.

**Verificado empíricamente que el defecto era real** con la prueba que ya existía (§1.4
detalla el hallazgo de test roto que esto destapó).

### 1.3 El arreglo: bajar la granularidad a mayor.menor

`filex/huella.py::interprete_actual()` pasa de `platform.python_version()` a
`"%d.%d" % sys.version_info[:2]`. Razones, las dos medidas donde se pudo:

- **Coincide con lo que la propia CI se compromete a mantener**: `.github/workflows/suite.yml`
  fija `python: ['3.11']` en su matriz, no un parche exacto — la granularidad mayor.menor es la
  que el proyecto YA declara estable, la del parche NO (cambia sola con la caché de
  `actions/setup-python`, sin que este repositorio lo controle).
- **Sigue protegiendo la trampa 105 real**: 3.11 y 3.14 se siguen declarando distintos.

**Lo que NO se pudo medir, y se declara PENDIENTE en vez de suponerlo:** si `ast.dump` puede
diferir entre dos parches de la misma menor (3.11.9 frente a 3.11.16). Se intentó conseguir un
segundo intérprete 3.11.x en esta máquina para medirlo con control positivo, como pide la trampa
61: **CPython 3.11 ya no publica binarios de Windows** (`https://www.python.org/ftp/python/3.11.16/`
solo trae `.tar.xz`/`.tgz`, código fuente — MEDIDO, la petición al índice lo confirma), y
compilarlo desde fuente en WSL2 estaba fuera del alcance de esta ronda. Lo que **sí** se
comprobó: leyendo el `ast.py` que trae la instalación de 3.11.9 (`grep` sobre el módulo), **no
hay ni una rama condicionada a `sys.platform` u `os.name`** en `dump()`/`parse()` — la
plataforma no debería entrar en el resultado para un mismo intérprete. La estabilidad entre
parches de la misma menor queda como razonamiento apoyado en la política de CPython (sin nuevas
características en versiones de mantenimiento), **no como medida con dos intérpretes reales**.

### 1.4 Un hallazgo de propina: mi propia prueba de la ronda 5 nunca protegió nada

Al verificar el arreglo, `pruebas/test_sondeo.py::SelladoDelDisco::test_ningun_motor_disponible_es_no_comparable_bajo_este_interprete`
—la prueba que yo mismo escribí en la ronda 5 para blindar exactamente este caso— **pasaba
siempre, incluso antes del arreglo de granularidad**, y no debía. Causa: llamaba a
`sondeo.aplicar(m.nombre, m.build, ...)` sobre un `cls()` recién creado, y `Motor.build` es una
`@property` que depende de `ruta`/`version`, que solo rellena `sondear()`. Sin sondear, `m.build`
vale el nombre pelado (`"imagemagick"`), nunca coincide con el `build` guardado
(`"imagemagick 7.1.2-21"`), y `sondeo.aplicar()` se para en la guarda del `build` **antes de
llegar siquiera a comparar el intérprete**. Arreglado llamando a `m.sondear()` de verdad —la
ruta que usan `motores.py`/`motor_contenedor.py` en producción—: con eso, **MEDIDO antes del
arreglo de granularidad, los cinco motores caían en `interprete_distinto`**, confirmando el
riesgo con la prueba correcta en vez de con una que nunca lo había ejercido.

**Este es el motivo de que el orden del encargo importe tanto**: sin corregir esto ANTES de
resondear, habría sellado los cinco ficheros con la granularidad vieja (el triple completo) y
habría hecho falta resondear una segunda vez solo para arreglar el campo `interprete`.

---

## 2. `C20` — el acuerdo `spa`/`eng` fuera de Ghostscript: VALIDADO y REFUTADO

**Corrección escrita en `bench/contrato-quinto-punto.md` §6.3** (tachada y firmada, sin
reescribir el texto de P3).

### 2.1 Método

Tesseract 5.5.0 **estandalone** dentro de `filex-c13` (no el Tesseract compilado dentro de
`gswin64c.exe`: proceso, binario y build distintos de la medida original). `--psm 3`. Ocho
documentos: los cuatro legado (sin tildes) más `escaneado_d4`/`d4a`/`d4c`/`d4e` (castellano CON
tildes — el vocabulario que pedía el encargo). Acuerdo = `difflib.SequenceMatcher(None, spa,
eng).ratio()`. Verdad = CER acentuado (`bench/scripts/ocr_eval.py::norm_acentos`) contra la
referencia de cada documento.

| Documento | ppp | acuerdo `spa`/`eng` | CER `spa` | CER `eng` |
|---|---:|---:|---:|---:|
| `patologico_escaneado` | 200 | 1,000 | 0,00 % | 0,00 % |
| `escaneado_d1` | 150 | 1,000 | 0,00 % | 0,00 % |
| `escaneado_d2` | 100 | 0,983 | 30,38 % | 27,85 % |
| `escaneado_d3` | 100 | **1,000** | **100,00 %** | **100,00 %** |
| `escaneado_d4a` | 200 | **0,735** | **0,17 %** | 7,05 % |
| `escaneado_d4c` | 200 | **0,542** | **1,68 %** | 10,91 % |
| `escaneado_d4` | 200 | 0,312 | 50,34 % | 59,06 % |
| `escaneado_d4e` | 200 | **1,000** | **100,00 %** | **100,00 %** |

### 2.2 La separación de 16/16 NO se reproduce — dos mecanismos, los dos diagnosticados

**Trampa de silencio.** `d3` y `d4e` dan **0 caracteres en las dos pasadas** con `--psm 3`. Dos
cadenas vacías son idénticas para `difflib` (`ratio()==1.000`): el acuerdo dice «perfecto» sobre
un CER real del 100 %. Confirmado que el mecanismo es el `--psm`, no el documento: con `--psm 6`
u `11` el mismo `d3` **deja de estar en silencio** y pasa a alucinar (`psm6_d3_spa.txt`, 151 B de
ruido; `psm11_d3_spa.txt`, 249 B) — la misma forma que `CLAUDE.md` ya documenta para otro motor
(*«silencio y alucinación son el mismo motor con distinto modo de segmentación»*, trampa 25). No
se barrió el `--psm` a fondo: hacerlo aquí habría sido variar dos preguntas a la vez (trampa 78
aplicada al propio arnés).

**Trampa del idioma en vocabulario acentuado.** `d4a` reconoce casi perfectamente (CER `spa` =
0,17 %) y el acuerdo da 0,735 — por debajo del umbral 0,80 —, porque `eng` no falla por ausencia
de tildes: **sustituye letras incorrectas** para los glifos acentuados (comprobado leyendo las
dos salidas lado a lado: `ó`→`é`, `ñ`→`N`/`fh`…), no solo las omite. Probado que no es cuestión
de normalización: ni conservar los diacríticos (NFC) ni descartarlos (NFKD ciega) suben el
acuerdo de `d4a` por encima de 0,73.

### 2.3 Decisión: NO entra como regla, ni informativa — en esta forma

Media regla demostrable vale más que una regla entera calibrada a ojo (trampa 87): con
`escaneado_d4` y los cuatro legado el patrón se sostiene; con la familia completa, **dos de ocho
documentos dan una lectura falsa** (una `bueno` marcada `ruido`, dos `ruido` marcadas `bueno`).
Faltan dos guardas —longitud mínima no vacía (como `P9_TOKENS_MIN`) y una comparación que no
penalice sustituciones de un solo carácter acentuado— y remedir con ellas puestas es un encargo
nuevo, no una continuación de este.

---

## 3. `C23` — la curva de once puntos del cruce en proceso/`magick`

**Ampliación escrita en `bench/contrato-quinto-punto.md` §4.3** (con nota de comparabilidad
explícita, no una sustitución de las cifras originales).

Con tres puntos no había curva, solo la sospecha de una. Once puntos (PNG sintéticos
deterministas, caja proporcional, mediana n=9 con calentamiento):

| Mpx | en proceso (ms) | `magick` (ms) | gana |
|---:|---:|---:|---|
| 0,0098 – 0,0800 | 4,5 – 59,0 | 47,6 – 134,9 | proceso (×2,3 a ×11,9) |
| **0,1602** | **128,2** | **55,4** | **magick empieza a ganar** |
| 0,32 – 5,12 | 135,0 – 2265,3 | 55,4 – 291,6 | magick (×2,1 a ×10,4) |

**El cruce cae entre 0,08 y 0,16 Mpx** — confirma el «~0,1 Mpx» original con un punto a cada
lado en vez de extrapolarlo desde dos. La forma, con once puntos, es más cercana a **lineal en
Mpx** de lo que sugerían los tres originales (377–516 ms/Mpx en proceso desde 1,28 hasta 5,12
Mpx, sin el salto abrupto que insinuaban los tres puntos viejos); `magick` se queda dominado por
un coste **casi fijo** (47–292 ms) en todo el rango.

**Aviso de comparabilidad, con número:** contenido sintético frente a rasters de SVG reales,
`standard_deviation` frente al umbral de tinta de I9, máquina `C:` bajo carga (63–96 % de CPU)
frente a la tanda `D:` original. Se sostiene la DIRECCIÓN y el ORDEN DE MAGNITUD del cruce, no
los ratios exactos punto a punto — declarado así en la propia corrección del documento.

---

## 4. El resondeo — al final, una sola vez, y con `contrato` verificado antes de tocar nada

### 4.1 El diagnóstico previo, con la herramienta correcta

`bench/salidas-huella/resellar.py --comprobar` (sin escribir) sobre los cinco ficheros, **antes**
de resondear nada:

```
doc_calibre.json       coincide_viejo=False resellado=False
doc_libreoffice.json   coincide_viejo=False resellado=False
doc_pandoc.json        coincide_viejo=False resellado=False
ffmpeg.json            coincide_viejo=False resellado=False
imagemagick.json       coincide_viejo=False resellado=False
```

Los cinco `coincide_con_algoritmo_viejo=False`: no es un cambio de algoritmo de huella (ronda 5
lo cerró), es código real de `C31` (ronda 6) dentro del cierre de `verificar()`. **Hacía falta
RESONDEAR, no resellar** — exactamente la trampa 61 aplicada, y la comprobación es la que exige
antes de decidir.

### 4.2 MEDIDO: 0 diferencias de veredicto en las 172 aristas

Los cinco motores se resondearon de verdad —`FileX.convertir()` real, con el contrato de cinco
puntos, el directorio desechable y (donde aplica) el censo del punto 5, no una simulación—,
usando los arneses que ya existían (`bench/salidas-sondeo-{im,ff,doc}/`, copiados a
`bench/salidas-acuerdo-y-cruce/` solo donde escriben fuera de `filex/sondeo/` — el de los tres
motores de contenedor se corrió EN SITIO, es infraestructura compartida diseñada para
re-ejecutarse). Detalle metodológico completo, con las órdenes exactas y los `sha256`, en
`bench/salidas-acuerdo-y-cruce/MANIFIESTO.md`.

| Motor | Aristas | Antes (real/nominal) | Después (real/nominal) | Diferencias de veredicto |
|---|---:|---|---|---:|
| ImageMagick | 62 | 62 / 0 | 62 / 0 | **0** |
| ffmpeg | 70 | 68 / 2 | 68 / 2 | **0** |
| doc_calibre | 8 | 8 / 0 | 8 / 0 | **0** |
| doc_libreoffice | 16 | 16 / 0 | 16 / 0 | **0** |
| doc_pandoc | 16 | 16 / 0 | 16 / 0 | **0** |
| **Total** | **172** | | | **0** |

Comparación hecha campo a campo (`estado` de cada arista, viejo contra nuevo, con
`git show HEAD:filex/sondeo/<motor>.json` como referencia del "antes") — no es una suposición de
que el código midiera lo mismo: es la comparación real que el encargo exigía en vez de
resellar por argumento.

**De propina, un hallazgo confirmando algo ya cerrado**: `_d2.py` (parte del arnés de los
motores de contenedor) reproduce el escenario exacto que motivó la trampa del `D2` histórico
—prosa con comas clasificada como CSV— y hoy da `ok_parcial`, no `fallo`. No es un efecto de
`C31`: `.txt`/`.md` no están en `EXT_TABULARES` desde antes de esta ronda (cerrado en
`bench/sondeo-documental.md` §2.3), así que nunca entran por la rama CSV de `_datos()`. Se
confirma que el arreglo de la RAM de `_datos()` (`C31(a)`, ronda 6) no reabre ese caso.

### 4.3 Sellado — RESONDEO declarado, no resellado por algoritmo

Los cinco `filex/sondeo/*.json` llevan ahora `"interprete": "3.11"` (la granularidad nueva de
§1) y `nota_huella` diciendo explícitamente que es un resondeo, con el motivo — la trampa 44 pide
que la nota no pueda leerse como lo que no es.

```
sellado filex/sondeo/imagemagick.json      interprete= 3.11
sellado filex/sondeo/ffmpeg.json           interprete= 3.11
sellado filex/sondeo/doc_calibre.json      interprete= 3.11
sellado filex/sondeo/doc_libreoffice.json  interprete= 3.11
sellado filex/sondeo/doc_pandoc.json       interprete= 3.11
```

**Verificado tras el sellado** (`pruebas/test_sondeo.py -q`): **48 passed, 14 subtests passed,
0 failed** — ni un motor en `interprete_distinto` ni en `caducados`.

---

## 5. Verificación de este PR

- **MEDIDO — suite integral**, `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe -m pytest pruebas/ -q`,
  **dos corridas completas** (la máquina está cargada, y una corrida con rojo no dice nada sin
  repetirla):
  - 1ª corrida: **453 passed, 3 skipped, 127 subtests, 1 failed** —
    `test_cancelacion_procesos::DuenoMuerto::test_sin_deteccion_el_trabajo_se_queda_working_para_siempre`,
    con `'failed' != 'working'`. **Pasa aislado** (1 passed en 2,49 s): mismo patrón de ruido de
    máquina que ya se vio en las rondas 5 y 6, siempre dentro de la misma clase
    (`DuenoMuerto`/cancelación con temporización real), nunca en un módulo que esta rama toque.
  - 2ª corrida: **454 passed, 3 skipped, 127 subtests, 0 failed**, en 202,53 s. **VERDE**, que es
    el criterio del encargo.
- **Intérprete:** `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe` = **3.11.9**, el
  mismo que sella los cinco `filex/sondeo/*.json` (ahora con `interprete: "3.11"`, granularidad
  nueva).
- **Entorno:** Windows 10, *worktree* en `C:\`. Docker Desktop **UP** durante toda la tanda
  (usado para el resondeo de los tres motores de contenedor y para `C20`; verificado con
  `docker ps` antes de cada tramo, y sin contenedores huérfanos después —"contenedores NUEVOS
  vivos: 0" en el log de `_sonda23.py`).
- **Qué quedó fuera y por qué:** la estabilidad de `ast.dump` entre parches de la misma menor
  de Python (§1.3, PENDIENTE declarado — no hay binario de Windows para un segundo 3.11.x en
  esta máquina); un barrido de `--psm` para `C20` (§2.2, habría mezclado dos preguntas); las dos
  guardas que le faltan al acuerdo `spa`/`eng` para entrar como regla (§2.3, encargo nuevo).
- **Estado de la máquina:** cargada durante toda la tanda (24-28 procesos de Python, 63-96 % de
  CPU en las muestras). El único fallo de las dos corridas de la suite es de esa clase —
  declarado, reproducido en aislamiento, y la segunda corrida limpia confirma que no es
  estructural a esta rama.
- **`ci/integridad.py`:** **MEDIDO**, 9/9 en verde (`Todo en orden.`), con `PYTHONIOENCODING=utf-8`
  (matiz de consola ya declarado en la ronda 6, no un defecto nuevo).

## 6. Riesgos y pendientes

- **`ast.dump` entre parches 3.11.x**: sin medir con dos intérpretes reales (§1.3). Si algún día
  se puede compilar un segundo parche, es la medida que cerraría el PENDIENTE de raíz.
- **`C20` con las dos guardas** (longitud mínima, comparación tolerante a sustitución
  acentuada): encargo nuevo, con el corpus y el método ya preparados aquí.
- **`--psm` de Tesseract 5.5.0 dentro de `filex-c13`**: no se ha medido su tabla completa (solo
  el control puntual de §2.2). Dado que la trampa 78 del proyecto ya midió que el `--psm` vale
  hasta 42,78 puntos con OTRO Tesseract, no hay que asumir que la tabla se transfiere.
- **Fallo de ruta absoluta en `tesseract` dentro del contenedor** (nota en el MANIFIESTO §1):
  reproducido y evitado con `--workdir` + rutas relativas, pero no diagnosticado más allá de dos
  intentos (regla de `CLAUDE.md` §3). Candidato a trampa nueva, junto con `--workdir` de Docker
  mal interpretado por Git Bash sin `MSYS_NO_PATHCONV` — los dos hallazgos son de esta ronda y
  no los añado yo a `CLAUDE.md` (solo la consolidación toca maestros).

## Entrega

Commit en `edicius2002/filex-cpu`. No se empuja ni se abre PR — lo hace el maestro.

# B7 y B8 — la otra mitad: un proxy que sí cubre a RapidOCR, y el barrido de `--psm` ya cerrado

worker1, carril GPU, ronda 12, `edicius2002/filex-gpu`. Rama al día con `main`
(`ce1ad2d`), ronda 11 fusionada. **Todo MEDIDO salvo donde se marca `PENDIENTE`.**
Dos filas, las dos continuación directa de trabajo propio de rondas anteriores.

- Datos crudos: `bench/salidas-severidad-y-curvatura/json/b7_cajas_rapidocr.json`
  (nuevo) y `bench/salidas-severidad-y-curvatura/json/b8_psm_sweep_deskew.json`
  (de la ronda 10, sin repetir)
- Instrumento nuevo: `b7_cajas_rapidocr.py`, reproducible — ver `MANIFIESTO.md`

---

## 1 · B7 — el proxy de cajas SÍ cubre el fallo de RapidOCR, con un hueco limpio

### 1.1 Dónde se quedó esto

`bench/severidad-y-curvatura.md` §1 (ronda 10) encontró `razon =
bytes_salida/bytes_referencia` con dos huecos limpios sobre 112 celdas de
Tesseract y RapidOCR — pero **las 20 celdas de RapidOCR caían todas en
«normal»**, con CER de 0,2 a 88,6 %: la señal calibrada con Tesseract era
ciega al modo de fallo de RapidOCR entero. Quedó pendiente el proxy de
`bytes_esperados` sin verdad conocida, con **cajas del detector** como
candidato ya nombrado.

### 1.2 El método

`bench/salidas-severidad-y-curvatura/b7_cajas_rapidocr.py` engancha
`TextDetector.__call__` (misma clase, misma técnica que
`bench/salidas-presupuesto-vram/n31_fases_child.py` de la ronda 11 — la GPU
ya sabe hacer esto) sobre los **20 rásteres de la ronda 8** (familia `d4`,
200/280 ppp, base/deskew, sin generar nada nuevo), y registra por celda:
número de cajas detectadas y área total de cajas como porcentaje del área de
la imagen que llega a la red (**no** del PNG original — es el área tras el
recorte/reescalado, el mismo array cuyo coste midió `N31`).

Lock de GPU tomado para toda la tanda, `.venv-ai`, RapidOCR PP-OCRv6 small +
R6 (idéntico a la ronda 8), un solo proceso (no hace falta reiniciar entre
imágenes: aquí no se mide VRAM, se miden cajas y bytes, deterministas con
independencia del estado del asignador).

### 1.3 El resultado — MEDIDO: hueco limpio en `área de cajas`, y también en `n_cajas`

| señal | `escaneado_d4e` (4 celdas, CER 49,7-88,6 %) | el resto (16 celdas, CER 0,2-28,9 %) | ¿hueco? |
|---|---:|---:|---|
| **área de cajas / área de página** | **4,28 % – 9,41 %** | **10,17 % – 13,05 %** | **SÍ, limpio: [9,41 ; 10,17], 0,76 puntos** |
| **número de cajas** | **2 – 9** | **10 – 13** | **SÍ, limpio: entre 9 y 10** |

**Las 20 celdas se separan exactamente en las mismas dos clases que ya
importaban**: `escaneado_d4e` (el único documento donde RapidOCR falla de
verdad, per `bench/deskew-y-fidelidad.md` §1) queda del lado de abajo en
CUALQUIERA de las dos variantes de la señal, sin una sola celda a caballo.
Regla candidata: `area_cajas_pct < 10` (o, más barato, `n_cajas < 10` — el
documento tiene 12 renglones reales, `corpus-d4.md` §7.6) → severo.

### 1.4 El límite honesto de esta señal — MEDIDO, y hay que decirlo

**No separa «muy bueno» de «moderado» dentro del resto.** `escaneado_d4` (CER
18,5-28,9 %, la peor calidad del grupo «normal») tiene **10-13 cajas y
10,30-13,05 % de área** — **el mismo rango** que `escaneado_d4a/b/c` (CER
0,2-9,6 %, 12 cajas, 10,17-12,66 % de área). La señal detecta cuando el
**DETECTOR** deja de encontrar los 12 renglones reales (que es justo lo que
le pasa a `d4e`: 2-9 cajas en vez de 12), pero es ciega a que el
**RECONOCEDOR** lea mal un renglón que sí detectó bien — que es exactamente
lo que degrada a `d4` frente a `d4a/b/c` (la rotación intermedia afecta a la
legibilidad del carácter, no a si la línea se detecta).

### 1.5 Veredicto de B7

**Hay una heurística que cubre el fallo de RapidOCR, y es del PAR
motor×tarea, no universal — exactamente como predecía la trampa 78.**
`bytes/referencia` (Tesseract) y `área_cajas/área_página` (RapidOCR) **no son
la misma fórmula**, cubren tipos de fallo distintos (inanición/alucinación
por longitud de salida contra colapso del detector), y ninguna de las dos se
ha probado en el motor de la otra. **Lo que SÍ generaliza es el
PROCEDIMIENTO**: engancha la etapa de detección del motor que sea, mide algo
que el motor ya calcula sin necesitar verdad conocida (cajas, en este caso),
y busca el hueco antes de publicar un umbral (trampa 51) — eso funcionó las
dos veces.

**No se prueba** si `área_cajas` de RapidOCR generaliza a un documento fuera
de la familia `d4`, ni si Tesseract tiene un proxy equivalente vía su propio
TSV/hOCR de cajas. **PENDIENTE**, y de coste no trivial (exigiría corpus
adicional para RapidOCR y una instrumentación nueva para Tesseract).

---

## 2 · B8 — el barrido de `--psm` YA ESTÁ CERRADO desde la ronda 10, sin repetir

### 2.1 Lo que este encargo pedía, y lo que ya existe

El encargo pide barrer `--psm 6` y `--psm 11` sobre las tres celdas
catastróficas de `-deskew` (`d4`@200, `d4c`@200, `d4c`@280, Tesseract `psm 3`,
`rc=0`, 0 bytes). **Esto ya se hizo en la ronda 10** —como parte opcional
«si sobra tiempo»— y **con una celda más de margen** (también `d4`@280,
que en la ronda 8 no fue la más catastrófica pero comparte el mismo
mecanismo): `bench/salidas-severidad-y-curvatura/b8_psm_sweep_deskew.py`,
citado en `bench/severidad-y-curvatura.md` §3.

**Resultado, ya publicado y no repetido**: las **12 celdas** (4 documentos ×
3 `--psm`) dan **0 bytes, `rc=0`**, sin excepción. La ESTADO-Y-REPARTO.md de
entonces no se actualizó para reflejar este cierre porque no era el foco de
la ronda 10 — **se corrige aquí** (§4).

### 2.2 Verificación de que el resultado sigue siendo válido

Se releyó el script y su salida (`json/b8_psm_sweep_deskew.json`, versionado
desde la ronda 10) en vez de repetir la tanda: los tres parámetros —`spa`,
`TESSDATA_PREFIX` de PDFgear, los mismos 4 rásteres de `img/`— son
deterministas y ya se demostró determinismo de Tesseract en esta familia
(20/20 en la ronda 8). No hay motivo para dudar de la cifra ni para gastar
tiempo de máquina en repetirla.

**Conclusión, sin cambios respecto a la ronda 10**: no es «cosa de `psm 3`»;
**es Tesseract en general** sobre estos rásteres deskeados, en las tres
clases reales de comportamiento (`k-oem-acantilados.md` §B24: auto-layout,
bloque único, disperso). Cierra la fila `B8` en la parte que faltaba.

### 2.3 El corpus de R1 — declarado, no fabricado

**No abordado, y sigue sin ser prioritario.** El estado es idéntico al de
las rondas 8 y 10: **21 de 23 PDF del corpus son «una sola imagen a página
completa»**, 1 no tiene ninguna imagen (`tipico_texto.pdf`), y **0
representan los otros tres casos PENDIENTE de R1** (varias imágenes, imagen
parcial, texto+escaneo mezclados). Construir tres documentos nuevos que
representen esos casos con cuidado —no como relleno apresurado— es trabajo
de corpus (como B15/B21 en su día) y no cupo en esta ronda, que se dedicó al
proxy de B7. **PENDIENTE**, con el motivo exacto: sigue siendo caro y sigue
sin haber tiempo.

---

## 3 · Estado de la máquina y las cuatro declaraciones

- **Intérprete**: `.venv-ai` (Windows, Python, torch 2.6.0+cu124, CUDA
  disponible) para `b7_cajas_rapidocr.py` (necesita `rapidocr`); `.venv-mcp-filex`
  (Windows, Python 3.11.9) para la suite y `ci/integridad.py`.
- **Entorno**: GPU limpia al empezar y al terminar (lock libre, ~9,3 GB
  libres de 12 288, línea base de escritorio ~2 700-2 900 MiB). El lock se
  tomó una vez para la tanda de `b7_cajas_rapidocr.py` (20 celdas, un solo
  proceso, sin reiniciar entre imágenes porque no se mide VRAM aquí) y se
  liberó al terminar. `docker info` comprobado ANTES de la suite (el
  encargo avisaba de dos caídas esta semana): **arriba**. worker2 en la
  ronda 12 del carril CPU arreglando `N30`+`C45`, sin tocar la tarjeta.
- **Qué quedó fuera**: si `área_cajas` generaliza fuera de la familia `d4`
  o a Tesseract vía su propio TSV/hOCR (§1.5, PENDIENTE); el corpus de los
  tres casos de R1 sin representante (§2.3, declarado, no intentado, mismo
  motivo que en rondas anteriores).
- **No se tocó** ningún fichero de worker2 (`verificador.py`, `motores.py`,
  `api.py`, `nucleo.py`, `huella.py`, `sondeo.py`, `confinamiento.py`).
  **`N30` no es mía esta ronda** — ver §4 sobre su fallo en la suite.

## 4 · Verificación

- `docker info`: comprobado antes de la suite (el encargo avisaba de dos
  caídas esta semana) — **arriba**.
- `ci/integridad.py`: **`Todo en orden`** (`.venv-mcp-filex`, Python 3.11.9).
  Se registró este informe en `ESTADO-Y-REPARTO.md` (B7 y B8, 🟡→🟢 los dos)
  y se corrigió el recuento de emojis: `6 ⚫ · 6 🔴 · 9 🟡 · 97 🟢` →
  `6 ⚫ · 6 🔴 · 7 🟡 · 99 🟢`.
- `pytest pruebas/ -q`: **457 passed, 3 skipped, 3 failed, 130 subtests** en
  213,4 s (`.venv-mcp-filex`, Windows, Python 3.11.9). **worker2 corría en
  paralelo, durante toda la tanda, una `pytest` DIRIGIDA a
  `test_cerrojo.py` + `test_cancelacion_procesos.py::…test_un_working_…`
  (arreglando `N30`) — confirmado con `wmic process ... get CommandLine`,
  no deducido —, así que la lentitud (213 s frente a los ~160 de una máquina
  tranquila) es de **contención de lock real, no sólo de CPU**: esos tests
  toman mutex y ficheros de candado que son de MÁQUINA, no de proceso.
  **Los 3 fallos, ninguno mío** (`git status --porcelain -- filex/ pruebas/`
  vacío esta ronda — no toqué ningún fichero de esos dos directorios):
  - `test_cancelacion.py::ContenedorReal::test_cancelar_mata_el_contenedor_y_no_solo_el_cliente`
    y `test_cancelacion_procesos.py::DuenoMuerto::test_un_working_sin_dueno_vivo_se_detecta_y_se_cierra`
    — el mismo par de la ronda 8 (trampa 101): pasan los 2 en aislado
    (`2 passed in 4,54 s`) apenas terminó la suite completa.
  - `test_watcher_n.py::CerrojoPosix::test_proc_ve_al_escritor_y_replace_no`
    — **nuevo, y de infraestructura, no de código**: `rc=4294967295`,
    *`Wsl/Service/E_UNEXPECTED`*. `wsl.exe -e echo ok` respondía normal
    justo después, y la prueba **pasa sola** (`1 passed in 1,19 s`): el
    servicio WSL2 tuvo un fallo transitorio durante la tanda más cargada de
    la sesión (coincide con el aviso del encargo de que Docker se cayó dos
    veces esta semana sin aviso — aquí es WSL, mismo patrón de
    infraestructura inestable bajo carga, no relacionado con `N30`).

## 5 · Ficheros de esta sesión

- `bench/salidas-severidad-y-curvatura/b7_cajas_rapidocr.py` — nuevo,
  `json/b7_cajas_rapidocr.json` (20 celdas).
- `bench/senal-severidad-y-psm.md` — este informe.

**Commiteado en `edicius2002/filex-gpu`. No se ha empujado ni abierto PR.**

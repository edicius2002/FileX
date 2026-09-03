# N31 y N26 — el presupuesto de VRAM: de dónde sale el sobrecoste, y cómo se suma

worker1, carril GPU, ronda 11, `edicius2002/filex-gpu`. Rama al día con `main`
(`7fd4bb8`), ronda 10 fusionada. **Todo MEDIDO salvo donde se marca `INFERIDO`
o `PENDIENTE`.** Un solo tema, dos filas que se refuerzan: N31 mide fase a
fase de dónde sale el sobrecoste de RapidOCR; N26 decide cómo se suma un
presupuesto de VRAM con varios modelos residentes. Las dos convergen en una
regla, al final (§3).

- Datos crudos: `bench/salidas-presupuesto-vram/json/{n31_fases,n31_resumen}.json`
- Instrumentos: `n31_fases.py` (conductor), `n31_fases_child.py` (proceso
  instrumentado), reproducibles — ver `MANIFIESTO.md`
- Código: `filex/sidecar.py` (`Perfil.medido_mib`, nuevo), `pruebas/test_hito6.py`
  (3 pruebas nuevas)

---

## 1 · N31 — instrumentado fase a fase: la explicación candidata es FALSA

### 1.1 La pregunta, tal como la dejó N27

`bench/vram-rapidocr.md` §1.3 (hallazgo no pedido): extrapolar la recta de los
tres puntos sin recortar (`428 + 235 × Mpx`) al punto donde ata el recorte
(2,984 Mpx) predice **1 129 MiB**; la meseta real mide **1 456-1 533**. Faltan
**300-400 MiB** que el tamaño del array final no explica. La explicación
candidata, **declarada como inferencia, no como medida**: el PNG original
antes de recortar —decodificarlo, y el propio `cv2.resize` piden sus propios
buffers transitorios, y el asignador no los devuelve.

### 1.2 El método: enganchar las clases reales, no deducir del código

Siguiendo la misma técnica que `bench/salidas-ppp-norm/sonda_detector.py`
(enganchar `DetPreProcess.resize`, no leer el código y suponer), se instrumentó
**todo el pipeline** de `rapidocr.RapidOCR.__call__` con `nvidia-smi` en ocho
puntos, monkeypatcheando las clases reales del paquete (`LoadImage`,
`RapidOCR.preprocess_img`, `TextDetector`, `RapidOCR.crop_text_regions`,
`TextClassifier`, `TextRecognizer`):

```
P_muy_inicio → P_arranque_import → P0_modelo_cargado →
P1_antes_decode → P2_tras_decode → P3_tras_resize →
P4_tras_det → P5_tras_crop → P6_tras_cls → P7_tras_rec
```

**Un proceso fresco por medida** (trampas 67/100: el asignador no libera
memoria, así que reutilizar el proceso entre imágenes contaminaría la
atribución por fase con lo que dejó la imagen anterior). Config idéntica a
`bench/salidas-ocr-produccion/sidecar_op.py` (PP-OCRv6 small, CUDA, R6). n=3
por caso, GPU limpia, lock tomado para toda la tanda.

Tres casos, los mismos rásteres que N27 usó (Ghostscript, deterministas,
`sha256` verificable en `MANIFIESTO.md`):

| caso | ppp | Mpx del PNG | Mpx que ve la red | ¿recortado? |
|---|---:|---:|---:|---|
| `sin_recorte` | 200 | 2,221 | 2,211 (1280×1728) | no |
| `recortado_A` | 280 | 4,352 | **2,984** (1504×1984) | sí |
| `recortado_B` | 400 | 8,882 | **2,984** (1504×1984, el MISMO array) | sí |

### 1.3 El resultado, por fase — MEDIDO, n=3, deltas de mediana

| fase | `sin_recorte` (Δ MiB) | `recortado_A` (Δ MiB) | `recortado_B` (Δ MiB) |
|---|---:|---:|---:|
| arranque → modelo cargado | +170 | +177 | +182 |
| **decode** (LoadImage) | **0** | **+4** (ruido) | **0** |
| **resize/recorte** (preprocess_img) | **0** | **0** | **0** |
| **detección** (TextDetector) | **+558** | **+1 098** | **+1 102** |
| crop (CPU, `crop_text_regions`) | 0 | 0 | 0 |
| clasificación (TextClassifier) | +16 | +16 | +16 |
| reconocimiento (TextRecognizer) | +234 | +234 | +237 |
| **TOTAL** (P8 − P_muy_inicio) | **992** | **1 572** | **1 531** |

n_cajas detectadas: 12 (sin_recorte), 10 (los dos recortados).

### 1.4 La explicación candidata queda REFUTADA — MEDIDO

**El decode y el resize no mueven la VRAM en ninguno de los tres casos**: 0 MiB
en 8 de 9 corridas, y +4 MiB en la novena — por debajo del ruido del
instrumento (±43 MiB, `ocr-produccion-sidecar.md`). **La hipótesis de N27 —que
el PNG original y los buffers transitorios de `cv2.resize` explican el
sobrecoste— es FALSA.** Ni decodificar la imagen de 8,882 Mpx ni recortarla a
2 000 px de lado cuestan un MiB medible en esta instrumentación.

**Todo el sobrecoste vive dentro del propio paso de DETECCIÓN**, y es **una
propiedad del array que llega a la red**, no del PNG de origen:

- `sin_recorte` (red = 2,211 Mpx): detección cuesta **558 MiB**.
- `recortado_A` (red = 2,984 Mpx, PNG de 4,352): detección cuesta **1 098**.
- `recortado_B` (red = 2,984 Mpx, el MISMO array, PNG de 8,882 — el doble que
  `recortado_A`): detección cuesta **1 102** — **4 MiB de diferencia sobre un
  PNG el DOBLE de grande**, dentro del ruido del instrumento.

**Los dos casos recortados dan el mismo coste de detección con PNG de entrada
que difieren ×2,04 en Mpx.** Esto es la confirmación positiva que le faltaba a
N27: el coste depende del array que ve la red, punto, y **no** del tamaño del
fichero de origen. `recortado_A` y `recortado_B` son, para el asignador, la
MISMA operación.

### 1.5 Entonces, ¿de dónde sale el 1 129 → 1 456-1 533? — MEDIDO: la curva de detección NO es lineal

Si el coste dependiera linealmente del array-red con la MISMA pendiente que
predice la recta de N27, `2,984/2,211 = 1,350×` más píxeles debería costar
`1,350×` más VRAM en detección: `558 × 1,350 ≈ 753 MiB`. **La medida real es
1 098-1 102 MiB — ×1,97, no ×1,35.** La relación entre el tamaño del array que
entra al detector y su coste de VRAM **no es lineal**: crece más rápido que
los píxeles, en algún punto entre 2,211 y 2,984 Mpx que este informe no
localiza con más precisión (**PENDIENTE**, exigiría barrer más puntos de
array-red, y el motor sólo entrega 2 valores discretos —recortado o no— salvo
que se cambie `Global.max_side_len`, que es tocar el propio motor).

**Esto es lo que la recta de tres puntos pequeños (0,55 / 1,25 / 2,22 Mpx) no
podía ver**: esos tres puntos están todos en la parte de la curva donde el
crecimiento SÍ es aproximadamente lineal (r²=0,9923 contra ellos, N27 §2). La
curvatura aparece más adelante, cerca del array máximo que el motor puede
producir — justo donde la extrapolación necesitaba ser fiel y no podía serlo,
porque un ajuste lineal no tiene manera de saber que hay un codo más allá de
sus propios puntos.

### 1.6 Por qué "arreglar el modelo tocando sólo el array" no funcionaría — la pregunta que cierra la fila

Con el mecanismo ya localizado: **aunque se reformulara `Motor.coste_previsto`
para usar el Mpx del array-red (2,984 fijo) en vez del Mpx del PNG de entrada,
seguiría haciendo falta un SEGUNDO punto de calibración cerca del recorte**,
porque la relación no es lineal en todo el rango — un modelo `ordenada +
pendiente × Mpx_red` ajustado sólo con los tres puntos pequeños **seguiría
subestimando** en el array grande, por el mismo motivo que subestimaba antes:
la forma, no las unidades, era el problema. **La respuesta correcta ya estaba
en el propio N27: un TOPE medido directamente (el máximo de tres medidas,
1 533), no una recta que intente alcanzar ese punto por extrapolación.** Este
informe confirma por qué esa elección fue la acertada y no una prudencia de
sobra: **la curva tiene un codo que ninguna recta puede seguir sin medirlo**.

---

## 2 · N26 — el presupuesto: por suma (con matiz) y no por perfil sin medir

### 2.1 Lo que ya estaba medido, sin repetirlo

`bench/hito6-sidecar.md` §3 y V7 ya midieron, con los tres componentes vivos a
la vez (Cláusula C), que **sumar componentes medidos por separado siempre
sobreestima** (nunca al revés, en los 3 perfiles medidos) pero **por una
cantidad que depende del perfil**:

| perfil | suma de componentes | medido, vivos a la vez | diferencia | sobreestimación |
|---|---:|---:|---:|---:|
| A · `distil-large-v3`, audio 11 s | 3 784 | **3 739** | −45 | **1,2 %** |
| C · `large-v3`, audio 308 s | 6 554 | **6 083** | −471 | **7,2 %** |

Factor **×6** entre los dos. `filex/sidecar.py`'s `Perfil.total_mib` sumaba
componentes SIEMPRE, y lo declaraba honestamente (`aditividad_supuesta: True`
en cada veredicto) — pero no tenía manera de usar una medida conjunta ya
existente cuando la había.

### 2.2 La decisión, con número detrás

**No se trata de elegir "por suma" o "por perfil" en abstracto: las dos
conviven, y la regla es cuál se usa cuándo:**

- **Un perfil YA MEDIDO conjuntamente** (Cláusula C: A/B/C de `hito6-sidecar.md`
  §V7) **usa la medida**, porque la suma nunca ha infravalorado — preferir la
  medida no introduce riesgo de aceptar algo que no cabe, y **recupera hasta
  el 7,2 % de capacidad que la suma tira a la basura** en el perfil donde más
  pesa (`large-v3`).
- **Un perfil SIN medir conjuntamente** sigue usando la suma, como **cota
  superior conservadora** — sabiendo que sobreestimará entre ~1 % y ~7 % según
  el perfil, **sin publicar ese porcentaje como una propiedad del sistema**
  (es del perfil, trampa 78 en otro eje).
- **`MARGEN_MIB=500`** (el margen de `decidir()`, para la admisión por página)
  sigue siendo global, y eso **sí es correcto**: cubre el RUIDO de sesión a
  sesión (±43-77 MiB, `vram-rapidocr.md` §3), que **no** varía por perfil de la
  misma manera que el sesgo de la suma — son dos magnitudes distintas y no hay
  que confundirlas. Bajarlo o subirlo por perfil no tiene evidencia que lo
  pida.

### 2.3 Implementado — `Perfil.medido_mib`

Cambio mínimo, aditivo, sin tocar el comportamiento por defecto:

```python
Perfil(nombre, escritorio_mib, audio_mib, motor, mpx_max,
       nvenc_mib=0, techo_mib=8909, medido_mib=None)
```

- **Sin `medido_mib`** (por defecto): `total_mib` sigue siendo la suma, igual
  que antes de esta ronda. Cero cambio de comportamiento para el código
  existente.
- **Con `medido_mib`** (el "coste propio medido" de la Cláusula C, sin el
  escritorio — misma convención que ya usa `suma_mib`): `total_mib =
  escritorio_mib + medido_mib`, y `evaluar()` declara `aditividad_supuesta:
  False`. `suma_mib` sigue expuesto en el veredicto para comparar las dos
  cifras lado a lado, nunca se oculta.

**Tres pruebas nuevas en `pruebas/test_hito6.py`** (53 pasan, 0 rotas):

1. `test_medido_mib_ausente_se_comporta_igual_que_antes` — el default no cambia.
2. `test_los_tres_perfiles_medidos_de_hito6_sidecar_V7` — los tres veredictos
   exactos de §V7 (7 187 cumple / 8 917 no cumple por 8 MiB / 9 531 no cumple),
   reproducidos con `medido_mib` en vez de la suma.
3. `test_la_suma_sobreestima_mas_para_large_v3_que_para_distil` — con los
   componentes reales de las tandas F y H, la sobreestimación de `large-v3`
   es mayor que la de `distil`, y las dos son positivas (la suma nunca
   infravalora).

---

## 3 · Dónde convergen las dos filas

**Las dos dicen la misma cosa a dos escalas distintas.** N31: incluso UN solo
componente bien medido (RapidOCR, r²=0,9923 en su tramo lineal) tiene una
curva con un codo que un modelo simple no ve sin medir cerca de él. N26:
incluso con CADA componente bien medido por separado, la SUMA de componentes
no es el todo — el todo, medido junto, es sistemáticamente menor, y por una
cantidad que no se puede adivinar sin medirla para ESE perfil.

**La regla que converge:**

> **Preferir siempre la medida conjunta más cercana a la configuración real
> que se va a desplegar — del array que entra a un motor, o de los modelos
> que conviven en un proceso —, y usar un modelo aditivo/lineal sólo como cota
> superior declarada para lo que aún no se ha medido así. Nunca extrapolar un
> modelo lineal más allá de sus propios puntos sin, como mínimo, un tope
> medido que lo recorte por arriba.**

Es literalmente lo que `Motor.coste_previsto` ya hace (`min(recta, tope
medido)`) y lo que `Perfil.medido_mib` ahora permite hacer también al nivel
del perfil completo. **No hace falta una regla nueva: hace falta aplicar la
misma regla en el segundo sitio donde el proyecto todavía no la aplicaba.**

---

## 4 · Estado de la máquina y las cuatro declaraciones

- **Intérprete**: `.venv-mcp-filex` (Windows, Python 3.11.9) para
  `filex.gpu`/`ci`/pruebas; `.venv-ai` (Windows, Python, torch 2.6.0+cu124,
  CUDA disponible, `torch.cuda.is_available()` comprobado) para los procesos
  hijo de N31 (`rapidocr`, `onnxruntime-gpu`).
- **Entorno**: GPU limpia al empezar (lock libre, ~9 150 MiB libres de
  12 288, línea base de escritorio ~2 960-3 060 MiB). El lock se tomó UNA vez
  para toda la tanda de N31 (9 corridas, ~1 min en total) y se liberó al
  terminar — confirmado (`gpu.esta_libre()` → `True` después). worker2 en la
  ronda 11 del carril CPU con el corpus FATE (CPU y disco, no GPU). Docker
  levantado.
- **Qué quedó fuera**: localizar con más precisión el punto exacto donde la
  curva de detección deja de ser lineal, entre 2,211 y 2,984 Mpx (§1.5,
  PENDIENTE — exigiría tocar `Global.max_side_len` del propio motor); el
  mecanismo INTERNO por el que la detección es super-lineal (ONNX
  Runtime/cuDNN, selección de algoritmo o tamaño de *workspace* — no se
  investigó, es arqueología de biblioteca ajena y no cambia la conclusión
  operativa).
- **No se tocó** ningún fichero de worker2 (`verificador.py`, `motores.py`,
  `api.py`, `nucleo.py`, `huella.py`, `sondeo.py`, `confinamiento.py`).

## 5 · Verificación

- `ci/integridad.py`: **`Todo en orden`** (`.venv-mcp-filex`, Python 3.11.9).
  Se registró este informe en `ESTADO-Y-REPARTO.md` (N31 y N26, 🔴→🟢 los dos)
  y se corrigió el recuento de emojis: `6 ⚫ · 9 🔴 · 8 🟡 · 95 🟢` →
  `6 ⚫ · 7 🔴 · 8 🟡 · 97 🟢`.
- `pytest pruebas/ -q`: **459 passed, 3 skipped, 1 failed, 130 subtests** en
  321,0 s (`.venv-mcp-filex`, Windows, Python 3.11.9). **CPU compartida con el
  carril CPU de worker2 (corpus FATE) durante toda la corrida, 94-100 %.** El
  único fallo es
  `test_cerrojo.py::DuenoMuerto::test_el_candado_se_recupera_solo_al_morir_su_dueno`
  — exactamente el segundo de los dos casos de **N30** que el propio encargo
  nombra por adelantado ("si cualquiera de las dos te sale roja, no es tuya y
  no relajes la aserción"). **No es mío y no se toca la aserción.** Ningún
  fallo relacionado con `filex/sidecar.py` ni `pruebas/test_hito6.py` (53/53
  verdes, incluidas las 3 nuevas de N26).

## 6 · Ficheros de esta sesión

- `bench/salidas-presupuesto-vram/n31_fases.py`, `n31_fases_child.py` —
  instrumentación fase a fase, reproducible (`MANIFIESTO.md`).
- `bench/salidas-presupuesto-vram/json/{n31_fases,n31_resumen}.json` — datos
  crudos y agregados.
- `filex/sidecar.py` — `Perfil.medido_mib` (aditivo, sin romper nada).
- `pruebas/test_hito6.py` — 3 pruebas nuevas.
- `bench/presupuesto-vram.md` — este informe.

**Commiteado en `edicius2002/filex-gpu`. No se ha empujado ni abierto PR.**

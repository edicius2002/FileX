# El `--psm` embebido de Ghostscript, las 9 aristas de grafo de filtros y la profundidad de un crudo de tercero

**Encargo R9b · worker2, carril CPU/Docker, `edicius2002/filex-cpu` — continuación tras un
cuelgue de máquina.** `C24` estaba cerrado en disco desde antes del cuelgue, sin commitear;
`C25` (grafos de filtros y crudos de terceros) no se había empezado.

**Máquina:** *worktree* en `C:\Users\krato\orca\workspaces\FileX\filex-cpu` (no
`D:\Work\research\FileX`; las cifras absolutas no son comparables con las históricas de `D:`).
RTX 3060 12 288 MiB — **no se tomó el lock de GPU**: todo este trabajo es CPU (Tesseract,
Ghostscript, ffmpeg, ImageMagick). Windows 10, Python 3.11.9. **worker1 estaba en el carril
GPU en la misma máquina durante toda la tanda**: `CPU al 100 %` en el momento de escribir esto
(`wmic cpu get loadpercentage`), con Docker Desktop y varios `python.exe` residentes. **La
tanda es `SUCIA`** en el sentido de `CLAUDE.md` §3 — no hay dos testigos de ruido ni n≥9 en
nada de este informe, pero **nada de lo que se mide aquí es sensible al reloj**: son `rc`,
bytes, y CER determinista sobre ficheros pequeños, exactamente el tipo de medida que la
propia regla exime («las relativas dentro de una tanda» no aplica ni hace falta que aplique
aquí — no hay milisegundos que comparar).

**Fecha:** 03/09/2026.

---

## 0. Estado de la máquina, verificado antes de escribir

- **Docker está arriba** (`docker info` → versión `29.4.3`, `docker ps` lista `filex-convertx`,
  `filex-snapotter(+pg,+redis)` y `filex-gotenberg8` corriendo). Se cayó con el cuelgue y el
  encargo pedía comprobarlo antes de la suite: **MEDIDO, arriba**.
- **`%TEMP%` de `filex-*` limpio**: la barrida de 887 huérfanos que dejó la sesión anterior
  ya se hizo; no se ha vuelto a acumular nada de este agente (todos sus temporales viven en
  `bench/salidas-c25-grafos/{in,out,out_crudos}/`, dentro del repositorio, y se borraron al
  terminar cada script — regla §6, no regla de `%TEMP%`).
- **`worker1` sigue en el carril GPU**: no se tocó `filex/gpu.py`, `filex/sidecar.py` ni
  `bench/lib/harness.sh`, y no se tomó el lock en ningún momento.
- **`N30`** (`test_cerrojo.py::test_sin_el_cerrojo_de_maquina_los_dos_procesos_devuelven_ok`)
  no salió roja en esta tanda (§4). Si sale roja en otra, no es de este informe.

---

## 1. `C24` — el Tesseract embebido en Ghostscript se comporta como `--psm 6`

**INFERIDO por huella de comportamiento, no sondeado directamente: no hay switch que exponga
el parámetro.** `gswin64c -h` no lista nada de `psm`/`ocr`/`segmentation`, y un
`-dOCRPageSegMode=N` inventado no produce ni error ni efecto — Ghostscript simplemente no
tiene ese parámetro expuesto por fuera. La honestidad de la etiqueta importa tanto como el
hallazgo: esto **no** es una medida directa, es la conclusión más fuerte que un experimento
indirecto permite.

### 1.1 Método: la misma forma de experimento que ya usó este informe

`bench/psm-y-rasterizador.md` §4.4 mide que `--psm 6` **nunca cambia con la resolución**
(0 de 22 celdas) porque el análisis de maquetación no entra a ese nivel, mientras que
`--psm 3/4/11` sí cambian. Esa es una huella distinguible. Se reproduce el mismo
experimento — variar la resolución, mirar si el CER se mueve — sobre `gs -sDEVICE=ocr` y
sobre Tesseract standalone con `--psm 3/6/11`, con el **mismo mecanismo de variación**
(remuestreo real vía `-r`/`-density`, no declaración de `pHYs` sobre píxeles fijos: ese
experimento exacto no se puede replicar porque `-sDEVICE=ocr` rasteriza el PDF él mismo y no
admite un PNG con cabecera mentirosa como entrada — diferencia de mecanismo declarada, no
oculta).

Documentos: `escaneado_d2` y `escaneado_d3` (100 ppp nativos los dos), 5 resoluciones
(75/100/150/200/300 ppp), evaluador acentuado (`norm_acentos`, el mismo criterio que
`ocr_eval_tildes.py`). **Con dos documentos**, no tres — es el hueco que el propio encargo
pedía declarar antes de que lo declarase otro; no se gastó tiempo en un tercero porque el
grueso de la ronda era `C25` (§2–§3) y la evidencia con dos ya es consistente en las tres vías.

### 1.2 Tres controles, cada uno en su sección

**A — presencia del aviso «Estimating resolution»** (`control_a_estimating.json`): con `-r`
declarando la resolución real (no un `pHYs` mentiroso), Tesseract **no** necesita estimarla.
`rc=0` en las dos, `estimating_resolution: false` en las dos. Esto **descarta** que la huella
de §1.3 esté contaminada por la trampa del `pHYs` (trampa 29 de `CLAUDE.md`): el ráster que
consume `gs` internamente declara su resolución de verdad.

**B — la curva de CER**, la comparación central (`curva_psm_gs.json`, 10 filas × 4 vías):

| Documento | res | `gs` | `psm 3` | `psm 6` | `psm 11` |
|---|---:|---:|---:|---:|---:|
| `d2` | 75 | 3,80 | 1,27 | 3,80 | 2,53 |
| `d2` | 100 | **0,00** | 30,38 | **0,00** | 13,92 |
| `d2` | 150 | 0,00 | 0,00 | 0,00 | 34,18 |
| `d2` | 200 | 0,00 | 0,00 | 0,00 | 5,06 |
| `d2` | 300 | 0,00 | 0,00 | 0,00 | 5,06 |
| `d3` | 75 | 105,06 | 100,00 | 105,06 | 68,35 |
| `d3` | 100 | 165,82 | 100,00 | 113,92 | 183,54 |
| `d3` | 150 | 402,53 | 100,00 | 402,53 | 782,28 |
| `d3` | 200 | 715,19 | 100,00 | 713,92 | 1760,76 |
| `d3` | 300 | 834,18 | 100,00 | 832,91 | 1511,39 |

Tres lecturas:

1. **La curva de `gs` sobre `d2` es plana** (3,80/0,00/0,00/0,00/0,00): recorrido 3,80 puntos,
   igual de plana que `psm 6` (mismo recorrido exacto, 3,80) y muy distinta de `psm 11`
   (recorrido 31,65) y de `psm 3` (recorrido 30,38). Es la huella invariante-a-resolución de
   §4.4 de `psm-y-rasterizador.md`, reproducida en un documento nuevo.
2. **Sobre `d3`, `psm 3` es plano al 100,00 % en las 5 resoluciones — silencio puro — mientras
   `gs` varía de 105,06 a 834,18 %.** `gs` no es `psm 3`: si lo fuera, `d3` habría dado
   silencio en las 5 celdas, y da alucinación creciente.
3. **`gs` y `psm 6` coinciden dentro de 0,04–1,27 puntos en 4 de 5 celdas de `d3`** (113,92 vs
   165,82 a 100 ppp es la excepción, con 51,90 puntos de separación — discutido en §1.4) y
   **exactamente en 3 de 5 de `d2`** (150/200/300 ppp, las tres a 0,00 %). `psm 11` diverge
   mucho más: hasta 1 760,76 % donde `gs` da 715,19 %.

**C — el `rc` de cada celda**, para no confundir silencio con «no arrancó» (trampa 25): las
**20 celdas de `gs` y las 30 de Tesseract dan `rc=0`**. Ningún cero de la tabla es un proceso
que no arrancó.

### 1.3 Lo que la huella NO afirma

`gs` y `psm 6` **no son bit-a-bit idénticos**: a `d3`/100 ppp difieren 51,90 puntos de CER
(165,82 frente a 113,92), y en ninguna de las 10 celdas el CER es exactamente igual salvo las
3+3 ya citadas. La afirmación es más estrecha y es la que el propio encargo pedía: **la forma
de la curva (invariante a la resolución) y el signo del error (alucinación creciente, no
silencio) coinciden con `psm 6` y no con `psm 3` ni con `psm 11`.** Con 10 celdas y sin acceso
al binario de Ghostscript-Tesseract por dentro, esto es lo más fuerte que se puede decir sin
cruzar la línea a «sondeado directamente».

### 1.4 Cierra el pendiente 7 de `invocacion-aristas.md`

La causa que el informe original daba por buena — *«la diferencia tiene que estar en el
preprocesado que aplica cada envoltorio»* — **era la hipótesis incorrecta.** Silencio (externo,
`--psm` 3 de fábrica, sin declarar) y alucinación (embebido, `--psm 6` inferido) son **el
mismo motor con un `--psm` por defecto distinto**, exactamente la forma que `CLAUDE.md`
trampa 8 ya documentaba para el Tesseract externo un `--psm` a la vez. Es una refutación de
la causa que el propio informe daba por buena antes de este trabajo — trampa 58 en estado
puro, *el hecho no implica la causa*. `bench/invocacion-aristas.md` y `bench/psm-y-rasterizador.md`
ya quedaron editados con esta corrección (commiteado antes de empezar esta ronda: el trabajo
de la sesión anterior, recuperado sin repetirlo).

---

## 2. `C25` — las 9 aristas «candidatas a grafo de filtros»: cerradas, 9/9

`bench/bitrate-por-pista.md` (tercera pasada de C25, ronda 1) clasificó 9 aristas del residuo
de P2 por la forma del `stderr` (`[af#0:0 …]` / `[vf#0:0 …] Task finished with error code: -22`)
como «candidatas a otra invocación del grafo de filtros», sin bajar al mensaje del encoder.
Esta ronda baja a ese mensaje y encuentra que **ninguna de las 9 necesitaba de verdad un
GRAFO** (nodos conectados con `;`/`[etiquetas]`, el sentido estricto de `filter_complex`):
basta un único filtro (`-af` o `-vf`) por celda. Se reducen a **tres familias**, cada una con
su propio mecanismo, no una sola causa «de filtros»:

| Familia | Aristas | Mensaje real del encoder | Arreglo |
|---|---|---|---|
| **A — channel layout ambiguo** | `aptx→isma`, `msbc→ismv`, `tta→h265.mp4` | `[aac] Unsupported channel layout "N channels"` | `-channel_layout {stereo,mono}` explícito |
| **B — frecuencia fija del codificador** | `loas→roq`, `uw→roq` (22 050 Hz); `avi→rco`, `mov→tco` (8 000 Hz) | `[roq_dpcm] Audio must be 22050 Hz` (textual); `g723_1` exige 8 000 Hz sin mensaje textual — es conocimiento externo del códec, no leído del `stderr` | `-ar` al valor exacto que el codificador exige |
| **C — geometría inválida para el codificador** | `webp→rm`, `bmp→3gp` | `h263`: *«The specified picture size of 1920x1080 is not valid… Valid sizes are 128x96, 176x144, 352x288, 704x576, and 1408x1152»*; `rv10`: *«width and height must be a multiple of 16»* y además un techo de **4 096 macrobloques** (`Encoding frames with 8040 (>= 4096) macroblocks is not implemented`, a 1920×1072 — múltiplo de 16 pero por encima del techo) | `-vf scale=704:576` (dentro del techo de `rv10` y una de las 5 tallas válidas de `h263`) |

**9/9 confirmadas rotas en la línea base** (reconstrucción exacta del `argv` de P2, ejecutada
en esta tanda contra las mismas entradas — no se reejecuta el JSON de P2, se reproduce la
condición, que es más fuerte: confirma que el fallo no era un artefacto de aquella máquina).
**9/9 arregladas** con el filtro de un solo nodo (`rc=0`, `bytes>0`, criterio de la trampa 75).
**9/9 se releen sin error** con `ffprobe` (`avi→rco` y `mov→tco` necesitan `-f g723_1`
explícito en la lectura: es un formato **crudo sin cabecera**, como PCM, y `ffprobe` no lo
adivina solo — no es un defecto del arreglo, es la naturaleza del formato de salida).

### 2.1 Control positivo de aparato

Antes de creerse cualquiera de las 9 celdas, la misma función `corre()`/`con_cota()` que
mide las 9 se aplicó primero a una arista **sin patología conocida** (`m.tta → .flac`,
sin restricciones de layout/frecuencia/geometría): `rc=0`, `21 558` bytes, `ffprobe` la
decodifica sin error. Si el aparato de medida (el `subprocess.run` con `stdin=DEVNULL`,
`-t 8` insertado dentro de la orden, timeout externo de 30 s) tuviera un defecto que
fabricara éxitos o fallos falsos, este control lo habría mostrado ahí primero, en el caso
más simple. Es la forma de la trampa 81 (*«el mismo fichero contra sí mismo tiene que dar
r=1»*) adaptada a un fallo que no es de identidad de señal sino de restricción de
codificador: el control que corresponde aquí no es una comparación de fidelidad, es
demostrar que el arnés no miente en el caso fácil antes de creerle en el difícil.

### 2.2 Ejemplo completo, para que quede citado el `argv`

```
# base (P2, tercera pasada): rc=-22, 0 B
ffmpeg -nostdin -y -i m.aptx -map 0:a -c:a aac -ar 96000 -sample_fmt fltp -f ismv -t 8 salida
#   [aac] Unsupported channel layout "2 channels"

# arreglo: rc=0, 17604 B, ffprobe decodifica (aac, 96000 Hz, stereo)
ffmpeg -nostdin -y -i m.aptx -map 0:a -c:a aac -ar 96000 -sample_fmt fltp \
  -channel_layout stereo -f ismv -t 8 salida
```

Las 9 filas completas (`argv` de las dos vías, `rc`, bytes, la línea exacta del `stderr` que
identifica la causa, y el resultado de `ffprobe`) están en
`bench/salidas-c25-grafos/resultado_c25.json`.

### 2.3 Lo que esto NO cierra

- **No se ha tocado `filex/motores.py`** para aplicar estos arreglos en producción — es
  investigación de causa, no cambio de comportamiento. Aplicarlos exigiría decidir de dónde
  sale el `-channel_layout`/`-ar`/`-vf scale` correctos por PAR (codificador, entrada), no una
  tabla fija: `aac` acepta layouts no ambiguos de otras entradas sin declarar nada, así que la
  regla no es «declara siempre», es «declara cuando el decodificador entrega un layout
  genérico», que es justo lo que dice el propio mensaje de error — un caso más para la regla
  del proyecto de **sondear la capacidad en ejecución, leyendo el mensaje del motor, no
  deduciéndola**.
- **`bmp`/`webp` a `704×576` deforma el aspecto** (origen 16:9, destino 11:9): es el tamaño
  válido más cercano dentro del techo de macrobloques de `rv10`, no el que preserva la
  relación de aspecto. Con `-vf "scale=704:576:force_original_aspect_ratio=decrease,pad=704:576"`
  se conservaría el aspecto a costa de barras — no se midió esa variante en esta ronda.
- **`w64 → amr`** (la décima celda del residuo de C25) sigue cerrada como en la ronda 1: dos
  intentos ya gastados, `Function not implemented` al abrir `libopencore_amrnb`, fallo de
  soporte de códec, no de invocación. No se reintentó.

---

## 3. `C25` — la profundidad de los crudos de terceros: cerrado, y el riesgo no era el que parecía

`bench/invocacion-aristas.md` §11 pendiente 2: *«Todo lo medido son ficheros que escribió el
propio ImageMagick a 16 bits. Un `.rgb` de 8 bits de otra procedencia daría basura con la
misma bandera, y no se sabe cuánta gente lo tiene a 8 bits.»* La regla que ese mismo informe
prescribe en §4.1 — *«deriva la profundidad de bytes ÷ píxeles… y elige por RMSE, no por
`rc=0`»* — nunca se había probado contra un crudo que NO fuera de la convención de 16 bits de
ImageMagick Q16-HDRI.

### 3.1 Método

Un crudo RGB genuinamente de 8 bits/canal, escrito por **ffmpeg**, no por ImageMagick — otra
procedencia real, no una simulación con la misma herramienta:

1. `ffmpeg -f lavfi -i testsrc2=size=96x64 -frames:v 1 referencia.png` — imagen sintética con
   bordes y degradados (una imagen de un solo plano de color no distingue `depth=8` de
   `depth=16` por RMSE: hace falta variación).
2. `ffmpeg -i referencia.png -f rawvideo -pix_fmt rgb24 tercero_8bit.rgb` — el «crudo de
   tercero»: 8 bits/canal reales, escrito por un decodificador/codificador ajeno al que
   produjo todas las filas de la tabla original.
3. **La regla candidata, sin mirar el origen**: `bytes_totales ÷ (ancho·alto) ÷ 3 canales × 8`
   — sólo bytes y geometría, la misma información que declararía un usuario en producción.
   `18 432 B ÷ (96·64) ÷ 3 × 8 = 8,0` → la regla predice **8 bits/canal**.
4. Sweep `-depth {8,16}` (el mismo espacio cerrado que usa el informe original) leyendo con
   ImageMagick, y RMSE contra la referencia con `magick compare -metric RMSE` (trampa 5:
   nunca SSIM).

### 3.2 Resultado

| `-depth` | ¿Lee? | RMSE contra la referencia |
|---:|---|---:|
| **8** (el que predice la regla) | sí | **0 — exacto** |
| 16 (el que asumiría ciegamente la convención de ImageMagick) | **no**: `rc=1`, `unexpected end-of-file` | — (no hay fichero que comparar) |

**La regla acierta.** Y el modo de fallo de la dirección contraria es más informativo de lo
que el pendiente suponía: leer un crudo NATIVAMENTE DE 16 BITS con `-depth 8` (el caso que
`invocacion-aristas.md` §4.1 ya midió) **consume la mitad del fichero y entrega, en silencio,
una imagen con la geometría exacta pedida y píxeles basura** — el fallo peligroso, porque no
avisa. Leer un crudo genuinamente de **8 bits** con `-depth 16` hace lo contrario: pide el
doble de bytes de los que el fichero tiene, ImageMagick lo detecta y **rehúsa escribir nada**
(`rc≠0`, cero ficheros de salida). Los dos errores de profundidad NO son simétricos:
sobre-asumir profundidad (`8→16`) es autoprotector; sub-asumir (`16→8`) es silencioso. La
regla del bytes-por-píxel evita el primero por construcción (deriva el valor correcto en vez
de asumirlo) y el segundo directamente no puede ocurrir si la regla se aplica — sólo ocurre si
alguien la salta y asume 16 a ciegas, que es justo la costumbre que la tabla de
`invocacion-aristas.md` §4.2 normalizó sin querer al medir solo semillas propias.

### 3.3 Lo que esto deja abierto — y lo que NO cierra

- **Un solo formato (`rgb` plano, sin alfa), una sola geometría, un solo productor externo
  (ffmpeg).** No prueba que la regla generalice a `bgra`/`cmyk`/`bayer`/etc. de OTRAS
  herramientas (una cámara, un driver de escáner, MATLAB…), sólo que **la premisa de la regla
  —derivar en vez de asumir— es sólida frente a al menos una procedencia real y no-ImageMagick**.
  El pendiente original preguntaba *«no se sabe cuánta gente lo tiene a 8 bits»*: eso sigue
  siendo una pregunta de prevalencia en el mundo real, no medible desde este repositorio, y
  sigue **PENDIENTE** en ese sentido estricto.
- **No se ha tocado ningún código de producción.** Es la confirmación de que la regla
  *propuesta* en `invocacion-aristas.md` §4.1 no tiene el agujero que el pendiente 2 temía;
  no hay regla implementada en `filex/` que cerrar.
- **El caso `bayer`/`bayera`** (pendiente separado, §4.3 del informe original: «no hay
  referencia ideal trivial para un mosaico CFA») sigue sin tocar.

---

## 4. Verificación

**Intérprete:** `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe`, Python 3.11.9,
`win32` — el intérprete de Windows que exige la trampa 94/105 para que los `skipUnless` de
plataforma y la huella de código midan lo que dicen medir.

**Entorno:** Docker arriba (§0), sin GPU tomada, CPU compartida con worker1 al 100 % de carga
en el momento de la tanda.

```
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe -m pytest pruebas/ -q
```
→ **453 passed, 3 skipped, 1 failed, 127 subtests** en 244,66 s.

**Qué quedó fuera y por qué:** los 3 `skipped` son los honestos de siempre (ráster ausente de
`bench/salidas-hito6/preparar_h6.py` y `FILEX_PRUEBAS_SIDECAR=1` + tarjeta) — no se tocó nada
de hito 6/sidecar esta ronda. El **1 failed**
(`test_cancelacion_procesos.py::DuenoMuerto::test_un_working_sin_dueno_vivo_se_detecta_y_se_cierra`)
**es de estado de máquina, no de este trabajo**: reejecutado en aislamiento (módulo solo, sin
el resto de la suite compitiendo por CPU) da **15 passed en 49,05 s, 0 failed**. Es
exactamente la forma de la trampa 101 — un test sensible al reloj falla bajo contención
multinúcleo y pasa limpio con la máquina tranquila — y `git status`/`git diff --stat -- filex/`
confirman que **esta ronda no tocó una sola línea de `filex/`**: no hay cambio de código que
pueda haberlo roto. No se relajó la aserción.

```
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe ci/integridad.py
```
→ falla primero con `UnicodeEncodeError: 'charmap' codec can't encode character '\u26ab'`
al imprimir el emoji ⚫ del resumen de `inventario` — **es la consola de Windows en `cp1252`,
no el chequeo**: con `PYTHONIOENCODING=utf-8` la misma orden da **9/9 comprobaciones `OK`**
(`citas`, `inventario`, `un-emoji-por-fila`, `trampas`, `informes-registrados`,
`manifiestos`, `secretos`, `binarios`, `en-curso`) y `Todo en orden.`. Se declara el matiz de
entorno explícitamente porque es justo lo que las trampas 94/104 piden: el mismo comando puede
comportarse distinto según algo del entorno que no es ni el código ni el intérprete — aquí,
la página de códigos del terminal.

**Estado de la máquina:** declarado en §0.

---

## 5. Salidas en disco

`bench/salidas-psm-gs-y-crudos/` (33 ficheros, heredado de la sesión anterior — commiteado al
empezar esta ronda, ver `MANIFIESTO.md` ahí) y `bench/salidas-c25-grafos/` (4 ficheros: dos
scripts, dos `.json`; los binarios intermedios se regeneran al vuelo y no se versionan, regla
§6 — ver `MANIFIESTO.md` ahí, con `sha256`, tamaños y las órdenes exactas).

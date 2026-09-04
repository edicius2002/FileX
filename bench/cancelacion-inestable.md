# N36 — la inestabilidad de `test_cancelacion_procesos`: mecanismo, no correlación

**worker8, ronda 18, carril `cpu/cancelacion-inestable`.** Salidas en
`bench/salidas-cancelacion-inestable/` con su `MANIFIESTO.md`.

**Resumen en tres frases.** La prueba que la fila `N36` nombra —
`test_cancelar_alcanza_al_motor_de_otro_proceso`— **no falla nunca**: 0 fallos en
**23 pasadas del módulo** y 16 de 16 en una sonda aislada, incluso con la máquina
saturada a propósito. La que sí falla es
**`DuenoMuerto::test_sin_deteccion_el_trabajo_se_queda_working_para_siempre`** (y,
menos, su hermana `test_un_working_sin_dueno_vivo_se_detecta_y_se_cierra`), y su
mecanismo tiene **dos piezas**: la causa próxima es que `taskkill /F /T` **no es
atómico** y deja al dueño vivo lo bastante para cerrar su propio trabajo como
`failed`; la condición necesaria es que el módulo **se dejaba 3 `ffmpeg.exe`
codificando VP9 por pasada**, que es la carga bajo la que esa ventana se abre.
**El arreglo es de ARNÉS, y lo digo con esas palabras** — el producto queda
descartado con medida, no con opinión.

---

## 0. Estado de la máquina, y por qué va lo primero

El encargo decía que yo era el único agente y que el maestro no correría nada
pesado. **Eso es cierto para FileX y falso para la máquina**, y en este encargo el
sujeto *es* la carga, así que hay que decirlo.

**MEDIDO al empezar** (`Get-CimInstance Win32_Process`): había procesos vivos de
**otros proyectos** — `uvicorn` de `edicius-hq` (dos), un driver de Playwright,
`vite`/`npm run dev`, el `ui-server.js` de `prospector`, `precios_pe.cli web`, y
un `scripts/_sonda_grandes.py` sobre una base de datos. CPU en 5 muestras a 700 ms:
**91 / 55 / 28 / 13 / 33 %**. Antes de la suite final: **24 / 22 / 29 / 22 / 44 %**,
418 procesos, 9 716 MB de RAM libre, **0 `ffmpeg.exe`**.

Consecuencia honesta: **ninguna tanda de este informe se midió con la máquina
tranquila.** Lo que salva las conclusiones es que **todas las comparaciones son
A/B con la misma carga declarada**, y que la carga externa la puse yo a propósito
(`--carga N`) para no depender de la ambiental. Las cifras absolutas de segundos
entre tandas distintas **no son comparables** (§3 de `CLAUDE.md`); los saldos
`limpias/n` dentro de la misma configuración, sí.

---

## 1. Lo primero que hay que reproducir es el punto de partida (trampa 58)

La fila `N36` dice, del maestro, el 04/09: módulo entero **1 de 3** limpias con el
código de la ronda 16, **2 de 3** con `filex/` de `main` como control, y la prueba
**aislada 3 de 3**. De ahí concluye *«es una interacción DENTRO del módulo»* y
**nombra a `test_cancelar_alcanza_al_motor_de_otro_proceso`** como la prueba
inestable.

**El orden de ejecución, MEDIDO y no deducido** (`pytest --collect-only -q`,
pytest 9.1.1, **sin plugins**: la única línea de `pip list | grep pytest` es
`pytest 9.1.1`, así que no hay `pytest-randomly` ni `-xdist` que reordenen):

```
1  CancelarEntreProcesos::test_cancelar_alcanza_al_motor_de_otro_proceso
2  CancelarEntreProcesos::test_el_candado_del_trabajo_se_suelta_al_terminar
3  CancelarEntreProcesos::test_el_dueno_se_puede_saber_sin_preguntar_por_ningun_PID
4  CancelarEntreProcesos::test_el_mando_se_borra_al_terminar_el_trabajo
5  SinCanalNoSeAlcanza::test_sin_canal_la_cancelacion_no_llega_y_se_dice
6  DuenoMuerto::test_sin_deteccion_el_trabajo_se_queda_working_para_siempre
7  DuenoMuerto::test_un_trabajo_vivo_NO_se_declara_huerfano
8  DuenoMuerto::test_un_working_sin_dueno_vivo_se_detecta_y_se_cierra
9-15  UnJobIdEsUnaEntrada (2) y ElAndamiajeEsUnMecanismo (5), sin procesos
```

**El orden es estable y la prueba de `N36` es la PRIMERA del módulo.** Eso ya
tensiona la hipótesis heredada: dentro de una pasada **no hay ninguna prueba antes
que ella** que pueda interactuar. La interacción, si existe, tiene que venir de
otro sitio.

### 1.1 La refutación: `N36` no es la prueba inestable — MEDIDO

| Tanda | Carga declarada | n | Limpias | Fallos de `test_cancelar_alcanza…` |
|---|---|---|---|---|
| `piloto-modulo` | 0 | 3 | **3** | **0** |
| `modulo` | 0 | 12 | **10** | **0** |
| `modulo-carga8` | 8 procesos | 8 | **3** | **0** |
| **Total pasadas del módulo** | — | **23** | 16 | **0 de 23** |

Los **7 fallos** de esas 23 pasadas se reparten así, y **ninguno** es de la prueba
que la fila nombra:

* **6 ×** `DuenoMuerto::test_sin_deteccion_el_trabajo_se_queda_working_para_siempre`
* **1 ×** `DuenoMuerto::test_un_working_sin_dueno_vivo_se_detecta_y_se_cierra`

**La correlación con la lentitud sí se reproduce, y con más n**: sin carga, la
mediana de las pasadas limpias es **59,82 s** y la de las sucias **76,79 s**; con
carga 8 la mediana sube a **87,75 s** y el saldo cae de 10/12 a **3/8**. Pero
—trampa 111— **eso sigue siendo una correlación**; el mecanismo está en §3.

### 1.2 Y `N36` tampoco se rompe forzándola — MEDIDO

`bench/salidas-cancelacion-inestable/sonda_n36.py` reproduce **solo** el escenario
de `N36` fuera de pytest: lanza un `filex` real, espera a que su motor esté en
vuelo y lo cancela desde otro proceso, registrando la traza del sujeto.

| Configuración | n | `n36_ok` | `ms` de `job(…, "cancelar")` |
|---|---|---|---|
| sin carga añadida | 8 | **8/8** | 418,3 – 543,3 (mediana ≈ 430) |
| **12 procesos de CPU** | 8 | **8/8** | 514,1 – 1 635,3 (mediana ≈ 824) |

**La condición SE DIO** (trampa 38, y se interroga al sujeto, no al mandato): con
los 12 procesos de carga, el tiempo del hijo hasta publicar `en_vuelo` pasa de
~2-3 s a **7 602,9 – 12 834,1 ms**, es decir la carga mordió de verdad. Aun así el
presupuesto de la cancelación —`ESPERA_MANDO = 3,0 s` en `filex/servicio.py`— se
consume al **27 %** en el peor caso y al **14 %** por mediana: margen **×3,6 con
la máquina saturada** y **×7 sin ella**.

**Conclusión de §1, y es una refutación del punto de partida:** *«una cancelación
que sólo funciona cuando la máquina va rápida sería un fallo de producto»* — el
encargo tenía razón en el criterio, y **el antecedente es falso**: la cancelación
entre procesos funciona igual con la máquina saturada. Las 4 pruebas de
`CancelarEntreProcesos` **no fallaron ni una vez en 23 pasadas**.

De paso, un dato que la trampa 93 predice y aquí queda **medido en el sujeto**:
`lanzador: true` en las 16 iteraciones — `Popen.pid` **nunca** coincide con el
`os.getpid()` que publica el hijo con el `python.exe` de `.venv-mcp-filex`.

---

## 2. La traza del fallo real

La primera versión del arnés reproducía el fallo pero no lo explicaba: el mensaje
era `AssertionError: 'failed' != 'working'`, que dice el **qué** y no el **quién**.
Añadí `_ConHijo._en_disco()`, que lee el JSON del trabajo y lo mete en el mensaje
de la aserción, porque **`Trabajos.volcar` guarda también el `resultado`** y ese
campo separa sin ambigüedad las dos causas posibles:

* `resultado.motivo == "proceso_dueno_muerto"` → lo cerró **la DETECCIÓN**.
* cualquier resumen de conversión → lo escribió **el propio dueño**.

**Las cinco trazas de la tanda `modulo-carga8` dicen las cinco lo mismo**
(`logs/modulo-carga8-{01,04,05,06,08}.log`). Una, literal:

```
AssertionError: 'failed' != 'working'
 : sin detección un huérfano parece vivo; en disco:
 {'job_id': '9cff4041128d', 'tipo': 'convert', 'estado': 'failed',
  'creado': 1788546602.237266, 'fin': 1788546603.5109305,
  'resultado': {'ok': False, 'veredicto': 'fallo',
                'camino': ['mp4', 'webm'], 'motores': ['ffmpeg'],
                'ms_motor': 1068.8,
                'motivo': 'el_motor_rechazo_la_conversion'}}
```

Tres cosas se leen ahí y ninguna es opinable:

1. **Lo escribió el dueño**, no la detección — el `resultado` es un resumen de
   conversión.
2. **`ms_motor` = 1 068,8 ms** (575,9 y 713,6 en las otras), cuando la conversión
   buena de `tipico.mp4 → webm` dura **~21 s**: el motor no terminó, **lo mataron**.
3. **`cancelado` no está puesto** — el motivo `el_motor_rechazo_la_conversion` sale
   de `Resultado.motivo` con `arrancado=True`, `cancelado=False`, `agotado=False`,
   `rc != 0` (`filex/invocacion.py:153`). Es decir: **lo mató alguien de fuera de
   FileX**, no `cancelar_hilo`.

`creado → fin` son **1,274 s**, y la prueba llama a `_matar_al_hijo()` justo
después de que `setUp` vea `en_vuelo`. Encajan.

---

## 3. El mecanismo, en dos piezas

### 3.1 La causa próxima: `taskkill /F /T` no es atómico

`DuenoMuerto._matar_al_hijo` hacía:

```python
subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.proc.pid)], ...)
self.proc.wait(timeout=30)
```

El árbol es **lanzador → `python` dueño → `ffmpeg`**. El `/T` recorre ese árbol y
**no garantiza el orden**. Si el nieto muere antes que el hijo, el dueño vuelve de
`communicate`, ve `conv.ok == False`, comprueba que **nadie pidió cancelar** y cae
en la rama `else: estado = FALLIDO` de `Servicio.convert.corre`
(`filex/servicio.py:687-690`), escribiendo `failed` en el disco antes de morir.

Y entonces **la condición que la prueba dice reproducir —*«el dueño murió SIN
cerrar su trabajo»*— no se dio**: lo que se está midiendo no es un huérfano. Es la
trampa 38 exacta.

**Control positivo determinista (trampa 116: el sujeto con el defecto, conservado
a propósito).** Forcé el orden malo —matar el motor, esperar 1 s, matar al dueño—
y el defecto sale **2 de 2**, con `ms_motor` 285,0 y 288,6 ms:

```
AssertionError: el dueño cerró su trabajo ANTES de morir, así que no hay
huérfano que medir y el veredicto de esta prueba no valdría (trampa 38).
En disco: {... 'motivo': 'el_motor_rechazo_la_conversion'}
```

La tercera prueba de la clase —`test_un_trabajo_vivo_NO_se_declara_huerfano`, que
**no mata a nadie**— pasa en esa misma pasada. Ese parche temporal se revirtió con
`git checkout --`, **no con `git stash`** (trampa 119), y lo verifiqué
**interrogando al fichero restaurado**, no al mandato.

**El control que ya estaba en los datos** y que separa «lo mató el kill» de «el
motor falló solo»: `test_un_trabajo_vivo_NO_se_declara_huerfano` tiene el **mismo
`setUp`**, la **misma carga** y **no llama a `_matar_al_hijo`** — y **no falló ni
una vez en 23 pasadas**. Las dos únicas pruebas que fallan son las dos que matan.

### 3.2 La condición necesaria: el módulo se dejaba 3 `ffmpeg` codificando

`_ConHijo.tearDown` hacía `self.proc.kill()`. Eso mata **sólo al lanzador** —el
`python.exe` de un venv lo es (trampa 93)—, así que **el `filex` dueño y su
`ffmpeg` sobrevivían a pytest**.

**MEDIDO:** el módulo dejaba **3 `ffmpeg.exe` vivos por pasada** (`ffmpeg_despues`
= 3 en 13 de las 15 pasadas sin carga; 2 en las otras dos). Uno por cada prueba
que **ni cancela ni mata**: `test_el_dueno_se_puede_saber_sin_preguntar_por_ningun_PID`,
`SinCanalNoSeAlcanza::test_sin_canal_…` y `test_un_trabajo_vivo_NO_se_declara_huerfano`.
Los censé por identidad y no por nombre: uno de ellos era

```
ffmpeg -hide_banner -nostdin -y -threads 4 -i …\corpus\video\tipico.mp4
       -map 0 -c:v libvpx-vp9 -crf 33 -b:v 0 -row-mt …
```

nacido a las 13:05:03, **de mi propio worktree**, vivo después de que pytest
terminara y muerto solo ~60 s más tarde. Tres de esos, a `-threads 4` cada uno,
sobre 12 núcleos, **dentro de la pasada siguiente**. Es la trampa 112 —el motor
termina y sus hijos no— cruzada con la 93.

**El control que separa las dos piezas — MEDIDO.** Con el **kill viejo** puesto y
**sólo** la fuga de huérfanos arreglada, el módulo entero bajo la misma carga 8:

| Configuración | n | Limpias | Mediana | `ffmpeg` tras la pasada |
|---|---|---|---|---|
| kill viejo **+ fuga** (estado heredado) | 8 | **3/8** | 87,75 s | 2 |
| kill viejo **sin fuga** | 6 | **6/6** | 37,73 s | **0** |
| kill nuevo **sin fuga** (entregado) | 8 | **8/8** | 42,13 s | **0** |

**Los huérfanos son la condición necesaria; la carrera del `/T` es la causa
próxima.** Sin los huérfanos la ventana no se abre ni con 8 procesos de carga
externa. *(Salvedad declarada, §3 de `CLAUDE.md`: las tres filas son tandas
distintas aunque compartan la carga declarada; lo que comparo son saldos y no
milisegundos, y el efecto en segundos —87,75 → 37,73— es de ×2,3, muy por encima
del ruido entre tandas.)*

### 3.3 Por qué la prueba de `N36` nunca cayó y la aislada pasaba 3/3

Encaja todo:

* **`test_cancelar_alcanza…` es la primera del módulo**, así que corre antes de que
  la pasada haya fabricado un solo huérfano — y su margen es ×3,6 aun saturada.
* **Aislada, la clase `DuenoMuerto` da 6/6 limpias** incluso con el kill viejo y
  carga 8 (`tanda-control-killviejo`, 13,64 s de mediana): sin las cinco pruebas
  previas no hay huérfanos, y sin huérfanos no hay ventana. **Eso es exactamente
  el «aislada 3 de 3» del maestro**, con el mecanismo detrás.
* **Las pasadas lentas son las que fallan** porque «lenta» y «con huérfanos
  encima» son la misma cosa.

Así que la fila `N36` acertó en la forma —**sí es una interacción dentro del
módulo**— y erró en el sujeto: no es un par de pruebas que compartan estado, es
que **cinco pruebas dejan procesos vivos que cargan la máquina para la sexta**. El
acoplamiento no es por memoria ni por disco: es **por CPU**.

---

## 4. El arreglo, y es de ARNÉS

**Lo digo con esas palabras: el arreglo es del arnés, no del producto**, y el
producto se descartó con medida antes de decirlo (§1.2: 16/16 con la máquina
saturada; §2: el `resultado` en disco es honesto y el motivo es correcto —a
`ffmpeg` lo mató un `taskkill` ajeno a FileX, y `el_motor_rechazo_la_conversion`
es justo lo que `Resultado.motivo` debe decir cuando `cancelado` es `False`).

**No se ha tocado una línea de `filex/`.** Tocado: `pruebas/test_cancelacion_procesos.py`
—que poseo— y su ayudante `pruebas/hijo_de_trabajo.py`, que declaro aquí
explícitamente porque el encargo sólo me nombraba el primero.

Tres cambios:

1. **`_matar_al_hijo` mata al DUEÑO primero y solo**, por su PID real (trampa 93);
   luego **los motores por identidad** (trampa 47), porque al morir el dueño el
   `ffmpeg` pierde padre y un `/T` sobre el abuelo ya no lo alcanzaría; y el
   lanzador al final. **Un muerto no escribe**: no hay ventana que cerrar porque no
   queda nadie que la aproveche.
2. **`_matar_al_hijo` REGISTRA que la precondición se dio** (trampa 38): si el
   disco no dice `working` tras el kill, falla diciendo *eso*, no otra cosa.
3. **`tearDown` mata el árbol del dueño** en vez de sólo al lanzador, más los
   motores por identidad.

Para (1) y (3) hace falta el PID del motor, y **lo publica el hijo** en su evento
`en_vuelo`. `_pids_motores()` lee el registro **privado** `invocacion._EN_VUELO` a
propósito: añadir un accesor público a `filex/` por comodidad de una prueba movería
el AST de un módulo sellado y podría caducar aristas (trampas 32 y 97). Es un
arnés; lo honesto es que se vea.

**Coste medido:** el módulo pasa de una mediana de **61,29 s** (sin carga, estado
heredado) a **27,41 s** en la pasada de comprobación sin carga — el arnés no sólo
deja de fallar, **deja de contaminar la máquina para lo que venga después**.

---

## 5. Lo que refuté, incluido de mi propio trabajo

1. **Refutado el sujeto de la fila `N36`.** `test_cancelar_alcanza_al_motor_de_otro_proceso`
   no falla: **0 de 23** pasadas del módulo, **16 de 16** en sonda aislada con y
   sin carga. La prueba inestable es `test_sin_deteccion_el_trabajo_se_queda_working_para_siempre`.
2. **Refutada mi primera hipótesis sobre el `ms_job`.** Sospeché que la
   cancelación se comía el presupuesto de `ESPERA_MANDO`, y también que
   `_matar_contenedor_de` podía cobrar sus `ESPERA_CONTENEDOR = 3,0 s` en el
   camino de un `ffmpeg`. **Las dos son falsas**: la función sale al instante para
   un binario que no es `docker` (`filex/invocacion.py:409`), y el `ms_job` medido
   nunca pasó de 1 635 ms sobre un presupuesto de 3 000.
3. **Refutada mi propia sonda, y es lo más caro del día.** `sonda_dueno_muerto.py`
   censaba los nietos con una consulta CIM de PowerShell **antes** del `taskkill`.
   Esa consulta cuesta ~1 s, y con ella la variante A dio **20 de 20 celdas
   verdes**, que es exactamente la pinta de *«el mecanismo no existe»*. Quitando la
   demora —y usando los PID que el hijo ya publica— la misma variante reprodujo el
   fallo. **Una sonda tiene que hacer lo que hace el sujeto, y en el mismo
   instante**; es la trampa 119 sobre un instrumento en vez de sobre `git stash`.
4. **El poder de esa sonda es bajo, y lo digo:** fuera de pytest reproduce **1 de
   26** con carga 8, mientras el módulo reproduce **5 de 8**. El reproductor bueno
   es el módulo entero, porque su carga es la que él mismo fabrica. **No publico la
   sonda como el reproductor**: es el control que confirma la traza fuera de
   pytest.

---

## 6. La suite completa, con sus cuatro declaraciones (trampas 94 y 101)

```
514 passed · 3 skipped · 0 failed · 198 subtests passed · 191,91 s
```

1. **Intérprete:** `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe`,
   **CPython 3.11.9, `win32`**.
2. **Entorno:** Docker **29.4.3** levantado (12 imágenes, 5 contenedores), corpus
   de LFS materializado (`corpus/imagen/tipico.png` = **42 855 B**, no 130 —
   trampas 34 y 107).
3. **Qué quedó fuera:** **3 saltadas**, las tres con motivo escrito y **ninguna
   por Docker ausente** (`logs/suite-completa-rs.log`, segunda pasada,
   `514 · 3 · 0 · 198` en 193,36 s — reproduce la primera):

   ```
   test_hito4.py:221  ningún par real rasteriza hacia un destino con texto en esta
                      máquina — ver bench/aristas-documentales-cierre.md §9
   test_hito6.py:186  falta el ráster (`bench/salidas-hito6/preparar_h6.py`)
   test_hito6.py:697  necesita la tarjeta: FILEX_PRUEBAS_SIDECAR=1
   ```

   Los dos de `test_hito6` son exactamente los dos que la trampa 94 dejó
   declarados el 31/08; el de `test_hito4` es de la ronda de aristas
   documentales. **Ninguno es mío ni lo he movido.**
4. **Estado de la máquina:** **NO tranquila** — §0. CPU en 5 muestras justo antes:
   **24 / 22 / 29 / 22 / 44 %**, 418 procesos, 9 716 MB de RAM libre, **0
   `ffmpeg.exe`** (comprobado a propósito: con el arnés viejo habría habido
   huérfanos míos ahí dentro).

La referencia del encargo era **514 · 3 · 0 · 198 · 202,45 s**: **coincide en las
cuatro cifras** y sale 10,5 s más rápida, lo que es ruido entre tandas y no una
mejora que yo publique.

---

## 7. PENDIENTE

* **PENDIENTE: por qué la sonda fuera de pytest reproduce tan poco** (1 de 26
  frente a 5 de 8 del módulo). La hipótesis cómoda es que la carga del módulo
  —3 `ffmpeg` a `-threads 4`— muerde distinto que 8 bucles de Python monohilo,
  pero **no la he medido y no la escribo como causa** (trampa 111).
* **PENDIENTE: si las otras clases del módulo tienen la misma fuga en POSIX.** El
  arreglo de `tearDown` usa `os.kill(pid, SIGKILL)` en la rama no-Windows y **no
  lo he ejecutado en Linux**: `test_cancelacion_procesos` está clasificado como
  «cuelga» en `ci/linux-apto.json`, así que la rama POSIX de este arreglo está
  **escrita y sin medir**.
* **PENDIENTE: el módulo no está protegido contra la fuga en el CAMINO DE
  EXCEPCIÓN.** Si `setUp` revienta después de lanzar el hijo pero antes de leer
  `en_vuelo`, `self.pids_motores` no existe y el `getattr` devuelve `()`: el árbol
  del dueño sí se mata (por `pid_hijo`), pero un motor ya reparentado no. No lo he
  visto ocurrir; lo dejo escrito porque es la trampa 112 por la puerta de al lado.
* **No es de este encargo pero lo dejo apuntado:** `filex/servicio.py` no
  distingue *«mi motor murió porque alguien mató el proceso desde fuera»* de
  *«mi motor rechazó la conversión»* — los dos salen como
  `el_motor_rechazo_la_conversion`. `Resultado.cancelado` cubre sólo la
  cancelación **propia**. Es la familia de la trampa 25 y **no propongo tocarlo**:
  no tengo medida de que haga daño a nadie, y el campo es honesto dentro de su
  alcance.

---

## 8. Texto propuesto (NO lo he escrito yo: `ESTADO-Y-REPARTO.md` y `CLAUDE.md` están vedados)

### 8.1 Fila `N36` de `ESTADO-Y-REPARTO.md`

> | **N36** | **La prueba que esta fila nombraba NO es la inestable — REFUTADO el 04/09/2026 con n=23.** `test_cancelar_alcanza_al_motor_de_otro_proceso` da **0 fallos en 23 pasadas del módulo** y **16 de 16** en sonda aislada, la mitad de ellas con la máquina saturada a propósito (`ms` de la cancelación: mediana 430 sin carga y 824 con 12 procesos, sobre un presupuesto `ESPERA_MANDO` de 3 000 → margen ×3,6 en el peor caso). **La inestable es `DuenoMuerto::test_sin_deteccion_el_trabajo_se_queda_working_para_siempre`** (6 de los 7 fallos; el séptimo es su hermana `test_un_working_sin_dueno_vivo_se_detecta_y_se_cierra`). **Mecanismo en dos piezas, con la traza delante:** la causa próxima es que `taskkill /F /T` no es atómico y el dueño sobrevive a su motor lo bastante para escribir `failed` con `motivo: el_motor_rechazo_la_conversion` y `ms_motor` de 0,3-1,1 s; la condición necesaria es que `tearDown` hacía `self.proc.kill()` sobre el **lanzador** (trampa 93) y el módulo **dejaba 3 `ffmpeg.exe` codificando VP9 por pasada** (trampa 112), que es la carga que abre la ventana. **A/B con carga 8: 3/8 → 8/8 limpias, mediana 87,75 → 42,13 s, huérfanos 2 → 0**; y con el kill viejo pero sin la fuga, **6/6**. **Arreglo de ARNÉS, `filex/` sin tocar.** Suite: `514 passed · 3 skipped · 0 failed · 198 subtests · 191,91 s` (3.11.9 win32, Docker 29.4.3, máquina NO tranquila) | 🟢 **CERRADO** · `bench/cancelacion-inestable.md` |

Y en la tabla de §1 de informes: `bench/cancelacion-inestable.md` — *N36: la
inestabilidad de `test_cancelacion_procesos` es una fuga de huérfanos, no una
cancelación frágil* (worker8, ronda 18).

### 8.2 Trampa 122 propuesta para `CLAUDE.md` (al final, nunca en medio)

> 122. **Un módulo de pruebas puede acoplarse consigo mismo POR CPU, y entonces la prueba que falla no es la que tiene el defecto — MEDIDO el 04/09** (`bench/cancelacion-inestable.md`). `test_cancelacion_procesos` era inestable y la fila que lo registraba **nombraba a la prueba equivocada**: la que fallaba (6 de 7 fallos en 23 pasadas) era `DuenoMuerto::test_sin_deteccion…`, no `test_cancelar_alcanza…`, que **no falló ni una vez** ni con la máquina saturada a propósito. El acoplamiento no era por memoria ni por disco: **tres de las ocho pruebas ni cancelan ni matan, y `tearDown` hacía `self.proc.kill()` sobre el LANZADOR** (trampa 93), así que el módulo **dejaba 3 `ffmpeg.exe` codificando VP9 a `-threads 4` por pasada** (trampa 112) — vivos dentro de la pasada siguiente. Sobre esa carga se abre la ventana de la causa próxima: **`taskkill /F /T` no es atómico**, el nieto muere antes que el hijo, y el dueño alcanza a cerrar su propio trabajo como `failed` con `motivo: el_motor_rechazo_la_conversion` y `ms_motor` de 0,3-1,1 s frente a los ~21 s de la conversión buena. **Entonces la condición que la prueba dice reproducir —«el dueño murió SIN cerrar su trabajo»— no se dio** (trampa 38), y el veredicto no medía lo que dice. **Las dos piezas se separan con número**: con el kill viejo pero **sin** la fuga, 6/6 limpias bajo la misma carga; con la fuga, 3/8. Tres corolarios: **(a)** el reproductor de un acoplamiento por CPU es el **módulo entero**, no la prueba aislada —aislada da 6/6 justo porque no hay quien fabrique la carga, que es por qué el «3 de 3 aislada» del diagnóstico previo era verdadero y engañoso—; **(b)** **una prueba que mata a un proceso para simular un dueño muerto tiene que matar al DUEÑO primero y solo**, y barrer sus motores **por identidad** después (trampa 47), porque un muerto no escribe y porque al morir el dueño sus hijos pierden el padre por el que un `/T` los alcanzaría; y **(c)** mi propia sonda dio **20 de 20 celdas verdes** —la pinta exacta de «el mecanismo no existe»— porque censaba los nietos con una consulta CIM de ~1 s **antes** del `taskkill`, es decir metía una demora que el sujeto real no tiene: **una sonda tiene que hacer lo que hace el sujeto, y en el mismo instante**.

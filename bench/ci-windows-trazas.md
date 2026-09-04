# Las TRAZAS de `windows-latest`: cinco módulos «no aptos», dos mecanismos

**worker13, carril de CI, ronda 13 · 03/09/2026 · rama `filex-ci-windows-trazas`**

`ci/windows-hosted-apto.json` declaraba, con una honestidad que hay que
conservar, **recuento sin causa**: cinco módulos con «N de M fallos —
PENDIENTE de traza, motivo no verificado». Este informe los clasifica **contra
su traceback real, medido en el runner**, y el resultado reproduce el patrón de
`C42` en Linux: **lo que parecían cinco causas son dos mecanismos**, uno de
entorno y otro **de producto**.

| | Antes (33788937291) | Ahora (33827476219) |
|---|---|---|
| Módulos aptos | 13 de 18 | **14 de 18** |
| Fallos con causa verificada | 1 de 5 filas, y **era falsa** | **4 de 5** |
| `test_cerrojo` | 9 fallos, PENDIENTE | **1 fallo**, fallo de producto F1 |
| `test_hito1` | 4 fallos, PENDIENTE | **3 fallos**, fallo de producto F1 |
| `test_watcher_n` | 4 fallos, PENDIENTE | **APTO** (0 fallos, 8 saltos honestos) |
| `test_hito7` | 16 fallos, «CONFIRMADO: Docker» | **16 fallos**, F1 — **la causa anterior queda REFUTADA** |
| `test_hito4` | 3 fallos, PENDIENTE | **3 fallos, PENDIENTE a propósito** (§7) |

---

## 0 · Las cinco declaraciones

El proyecto exige cuatro (trampas 94 y 101) y el encargo añade la quinta:

1. **Intérprete.** Todo lo de aquí, **Python 3.11.9 de `actions/setup-python@v7`
   sobre `win32`**. El control local del instrumento, `3.11.9` de
   `D:\Work\research\FileX\.venv-mcp-filex` — la misma versión, y aun así
   **otra máquina**, que es justo el punto de la trampa 104.
2. **Entorno.** `windows-latest` hospedado por GitHub. `magick` 7.1.2-Q16-HDRI
   **presente**; `gswin64c`, `ffmpeg`, `ffprobe`, `tesseract`, `nvidia-smi`
   **ausentes**; `docker` presente, demonio vivo, **0 imágenes**; `corpus/` en
   **punteros de Git LFS** (`lfs: false` en el *checkout*); `%TEMP%` =
   `C:\Users\RUNNER~1\AppData\Local\Temp` (**nombre corto 8.3**), `USERNAME` =
   `runneradmin`, repositorio en `D:\a\FileX\FileX`.
3. **Qué quedó fuera.** `test_hito4` (§7), la GPU (no la toco: hay otro carril
   midiendo con la tarjeta), y el arreglo de F1 (§3.4: el fichero es de dos
   ramas sin fusionar).
4. **Estado de la máquina.** Irrelevante para las cifras del runner —cada
   ejecución es una VM nueva—, y **eso es una ventaja de este carril**, no un
   descuido: las tres ejecuciones dan los mismos recuentos para el mismo código.
   El control local se corrió con la máquina tranquila.
5. **Qué ejecución respalda cada fila.** Va escrito en cada fila y en el propio
   `ci/windows-hosted-apto.json`. Las tres son: **33826410849** (trazas del
   estado inicial), **33827215958** (la que **refutó** mi primera hipótesis) y
   **33827476219** (la que se congela).

---

## 1 · El instrumento primero: el recuento no separa causas

`ci/sonda_windows_hosted.py` medía `failures=N` con una expresión regular y
tiraba el resto. **«9 de 24 fallos» tiene exactamente la misma pinta viniendo
de un motor ausente, de un puntero de LFS, de una ruta de Windows o de un fallo
del producto**, y los cuatro remedios son distintos: es la trampa 25 subida al
nivel del arnés.

Lo que se le añadió — **MEDIDO**, ejecución 33826410849:

* **Parseo de los bloques `FAIL:`/`ERROR:`** de `unittest -v`, con el nombre del
  test y su traceback completo, en el JSON y por pantalla. Verificado contra una
  salida real antes de gastar un runner: **3 de 3 bloques, con un subtest entre
  ellos** (los subtests salen como `test (…) (ruta='x.txt')`, y sin eso las dos
  celdas de `OraculoTemporalN9` habrían quedado sin nombre).
* **Volcado íntegro** de la salida de cada módulo a `--logs/<modulo>.log`,
  **incluida la de los que fallan y la de los que cuelgan**. La trampa 103 se
  pagó por canalizar a `tail` justo la salida del caso que fallaba: *un arnés
  que descarta la salida del caso que falla ha medido y no ha aprendido.*
* En el *workflow*, `upload-artifact` con **`always()`**: una sonda que reviente
  a mitad no puede llevarse lo ya medido.

**Cosecha: 36 trazas** donde antes había cinco números. Y un control que importa
—la ejecución 33826410849 reproduce **exactamente** los cinco recuentos de la
33788937291 (9/4/3/16/4)—, así que las trazas describen el mismo fenómeno que el
fichero congelado, no otro.

---

## 2 · Las 36 trazas, repartidas

| Mecanismo | Trazas | Módulos |
|---|---|---|
| **A — fallo de producto F1** (§3) | **28** | `test_cerrojo` 9/9, `test_hito7` 16/16, `test_hito1` 3/4 |
| **B — puntero de Git LFS** (§4) | **5** | `test_watcher_n` 4/4, `test_hito1` 1/4 |
| Fuera de alcance | 3 | `test_hito4` |

**Dos mecanismos, no cinco causas.** Es la misma forma que `C42` encontró en
Linux —diez módulos, dos mecanismos— y sólo se ve leyendo la traza.

---

## 3 · Mecanismo A: `Confinamiento` no resuelve sus raíces — **FALLO DE PRODUCTO**

### 3.1 · La primera hipótesis, y su refutación

La traza de `test_watcher_n` imprimía la pista sin querer:

```
Huella(ruta='C:\\Users\\RUNNER~1\\AppData\\Local\\Temp\\prueba-n5v-mwxome9m\\ent\\medio.wav', ...)
```

`RUNNER~1` es un **nombre corto 8.3**, y el proyecto ya tiene la lección escrita
para otro recurso: la trampa 33 midió que *«`normcase(abspath)` NO identifica un
destino: el nombre corto 8.3 que genera Windows daba dos dueños del mismo
fichero»*, y por eso `filex/cerrojo.py` usa `realpath`. `Confinamiento._preparar`
normaliza sus raíces con `normcase(normpath(abspath(r)))` — **sin `realpath`**—
mientras `_resolver_sin_ecualizar` valida la ruta **RESUELTA** (R7). Hipótesis
obvia: *«la raíz en 8.3 cierra la lista blanca; pásala resuelta y entra»*.

**Falsa, y la refutó mi propio control negativo** (33827215958):

```
"puede_leer_con_raiz_TAL_CUAL": false,
"puede_leer_con_raiz_RESUELTA": false,      ← el control decía que no
"control_positivo_raiz_larga_del_repo": true,
"veredicto": "el 8.3 NO explica el fallo: mirar otra cosa"
```

Una traza es una pista, **no un mecanismo** (trampa 36), y el hecho no implica la
causa (trampa 58). Sin ese control negativo habría publicado un enunciado que
suena bien, cita la trampa correcta y **es incorrecto**.

### 3.2 · El enunciado bueno, con las tres celdas

Faltaba una tercera celda: la raíz **y** la ruta, las dos resueltas. Con ella
(33827476219, `c1_nombre_corto`) — **MEDIDO**:

| Raíz | Ruta pedida | Resultado | Dónde muere |
|---|---|---|---|
| 8.3 | 8.3 | **DENEGADO** | `confinamiento.py:242`, el `_dentro` de la ruta **resuelta** |
| resuelta | 8.3 | **DENEGADO** | antes: el predicado léxico de R1, que compara la ruta **tal cual** |
| resuelta | resuelta | **PERMITIDO** | — |
| larga (`D:\a\FileX\FileX\bench\...`) | larga | **PERMITIDO** | control positivo |

**F1: `Confinamiento` guarda sus raíces en UNA sola forma, y valida contra
DOS.** El predicado léxico de R1 —que corre antes del `realpath` a propósito,
porque `realpath` es un vector de DoS (R17)— compara la ruta **sin resolver**;
la segunda comprobación compara la **resuelta**. Consecuencia exacta, que
conviene no exagerar:

* **Una raíz registrada en su forma 8.3 es inservible**: la petición en 8.3
  muere en la segunda comprobación y la petición resuelta muere en la primera.
  Ninguna de las dos formas de pedir pasa las dos comprobaciones.
* **Una raíz registrada resuelta sirve, pero sólo para peticiones resueltas** —
  y quien la usa no controla la forma en que le llega la ruta.

Y eso es justo lo que hace `tempfile.mkdtemp()` en este runner: devuelve la
forma 8.3, y las pruebas la usan tal cual para las dos cosas.

### 3.3 · Por qué es del producto y no del arnés

* La raíz que se le pasa es **legítima**: una ruta absoluta a un directorio que
  existe, la que devuelve `tempfile.mkdtemp()`. Ningún contrato de
  `Confinamiento` pide una ruta canónica.
* **Falla cerrando**: deniega de más, nunca de menos. **No es un agujero de
  seguridad**; es un «no» donde tocaba un «sí». Severidad: usabilidad.
* Le pasaría igual a un usuario cuyo `%TEMP%` sea 8.3, o a cualquiera que
  invoque FileX con una raíz que contenga un componente corto — que es lo normal
  cuando la ruta viene de `%TEMP%` de una cuenta con nombre largo.
* **En la máquina del proyecto no se puede ver**: allí `%TEMP%` es
  `C:\Users\krato\AppData\Local\Temp`, largo, y las tres celdas dan `true`
  (control local, §6). Lo destapó **meter el código en otro Windows**, que es el
  mismo tipo de control positivo que la trampa 105 obtuvo metiendo un segundo
  Python en la matriz.

### 3.4 · Qué NO he hecho, y de quién es

**No lo arreglo.** `filex/confinamiento.py` es de dos ramas sin fusionar
(`edicius2002/filex-suelo-y-mcp` y `edicius2002/filex-fate-completo`), y el
encargo lo pone fuera. Además **no es un arreglo de una línea**: resolver las
raíces a secas rompería el lado léxico de R1, que necesita comparar la ruta tal
cual. La forma que parece correcta —guardar **las dos** formas de cada raíz y
validar cada comprobación contra la suya— **está sin medir: PENDIENTE**, y con
ella hay que medir también qué le hace al coste de R1 (la trampa 28 ya midió que
la asimetría entre «prohibido» y «no existe» es de ×20,6).

---

## 4 · Mecanismo B: el puntero de Git LFS, y un `skipUnless` que no protegía

**MEDIDO** (33827476219, `c2_lfs`): con `actions/checkout` a `lfs: false`,
`tipico.png` pesa **130 B**, `tipico.jpg` **130 B**, `trivial.wav` **131 B** y
`habla_jfk.flac` **132 B**, los cuatro con cabecera
`version https://git-lfs.github.com/spec/`. `corpus/datos/patologico_bom.csv`
(88 B) **no está en LFS** y es real.

El `lfs: false` **es correcto y no se toca**: el corpus son 254 MB contra una
cuota de 1 GB de ancho de banda al mes (§103 de las trampas). Lo que falta son
los guardas.

### 4.1 · `test_watcher_n` — 4 rojos y **2 verdes** del mismo mecanismo

Los cuatro rojos son aritmética: `trivial.wav` es un puntero de 131 B, cortarlo
por la mitad da los **65 B** que aparecían literalmente en la traza,
`_coherencia_declarada` responde `sin_declaracion` en vez de `completo`, y el
`Vigilante` madura un fichero a medias.

Y hay una **segunda mitad que nadie había mirado**: `test_riff_de_relleno_no_es_un_incompleto`
y `test_un_wav_entero_no_se_aplaza` **pasaban en verde** con el puntero, porque
un puntero es `sin_declaracion` mires lo que mires. Un verde por el motivo
equivocado es peor que un rojo (trampas 60 y 109), así que también llevan
guarda. `CerrojoPosix` usa el PNG **como blob que alguien tiene abierto**, no
como imagen: ahí un puntero sirve, y **no lleva guarda**. *El guarda se pone por
ACTIVO, no por clase.*

**Resultado, MEDIDO: `test_watcher_n` pasa a APTO** — 19 corridas, 8 saltos
honestos, 0 fallos.

### 4.2 · `test_hito1` — el guarda que nombraba su causa y no protegía de ella

```python
if not os.path.isfile(ent):
    self.skipTest("falta el corpus")
```

Es la **trampa 107 exacta**: un puntero de 130 B *existe*, así que la condición
no se cumple, la prueba no se salta, y `magick` devuelve
`el_motor_rechazo_la_conversion`. Cambiado a comprobar la **cabecera**, que es
exacta y no necesita umbral. (El proyecto ya tenía el patrón por tamaño en
`test_a7_ciego`; por cabecera no hace falta elegir un umbral.)

### 4.3 · Un aviso sobre lo que estos guardas SÍ y NO explican

**Los 8 guardas nuevos de `test_cerrojo` bajan su recuento de 9 a 1, y eso NO
significa que 8 de los 9 rojos fueran de LFS.** En el runner de hoy **los 9 son
F1**: la resolución de rutas ocurre *antes* de invocar al motor, así que la
conversión ni llega a mirar el fichero. Lo que hacen los guardas es retirar de
la cuenta las pruebas que **en este entorno no se pueden medir de ninguna
manera** —necesitan un PNG real que el runner nunca va a tener con `lfs:
false`—, dejando el rojo del módulo apuntando a **una sola** causa. Decir «eran
8 de LFS» sería cometer, dentro de este informe, justo el error que vino a
arreglar.

Que la segunda capa existe **no es deducción**: la sonda la mide aparte (C5,
33827476219). Con la raíz y la ruta ya resueltas —esquivando F1— la conversión
del PNG del corpus llega al motor y devuelve
`ok: false, motivo: "el_motor_rechazo_la_conversion"` sobre una entrada de
**130 B**. Las dos capas son reales e independientes.

---

## 5 · `test_hito7`: la única causa que alguien había escrito, y es **FALSA**

El fichero congelado decía:

> `"test_hito7": "16 de 42 fallos -- CONFIRMADO: el demonio Docker responde
> ('docker: presente') pero no está ninguna imagen del proyecto (filex-c13,
> ghcr.io/c4illin/convertx:latest); mismo mecanismo que C42 en ubuntu-latest"`

**REFUTADO, por dos vías** (33826410849 y 33827476219):

1. **La salida íntegra de las 42 pruebas de `test_hito7` no menciona a Docker ni
   una vez.** `grep -in "docker\|contenedor\|convertx\|filex-c13"` sobre
   `logs-33826410849/test_hito7.log` → **0 líneas**. En cambio, `ruta no
   accesible` aparece **6 veces** y `RUNNER~1`, **2**.
2. **Las 16 pruebas que fallan están en clases que construyen su FileX con
   `fx_de([mkdtemp()])`** — las 16 llamadas a `fx_de` del módulo pasan un
   directorio temporal como raíz. Es F1, y F1 dispara antes de que ningún motor,
   en contenedor o no, entre en escena.

**Lo que sí es cierto es el ENTORNO**: `docker images` devuelve **0 imágenes**
(medido), y por eso los tres motores en contenedor salen ausentes con el motivo
correcto. El error no fue el dato: fue **atribuirlo al módulo equivocado**
leyendo el paso «El paquete importa y la CLI arranca» en vez de la traza del
módulo. Es la trampa 36 —una explicación plausible no es un mecanismo— y **la
palabra «CONFIRMADO» la hacía indiscutible**. Un `PENDIENTE` honesto habría
costado menos que este `CONFIRMADO`.

---

## 6 · El instrumento, controlado en las dos máquinas

`bench/salidas-ci-windows-trazas/sonda_causa_windows.py` se corrió también en la
máquina del proyecto, y **tiene que dar lo contrario**: `tempdir_es_nombre_corto:
false`, las tres celdas de C1 en `true`, `es_puntero_lfs: false` en los cuatro
ficheros, y C5 con `ok: true` sobre una entrada de **42 855 B**. Lo da. Una sonda
que respondiera lo mismo en dos entornos que sé distintos estaría rota, y esa
comprobación cuesta una línea (trampa 66).

---

## 7 · Lo que queda fuera, y por qué

* **`test_hito4` (3 de 31): PENDIENTE a propósito.** La rama sin fusionar
  `edicius2002/filex-suelo-y-mcp` **modifica `pruebas/test_hito4.py`**;
  clasificarlo ahora sería medir un fichero que está a punto de cambiar. Su
  traza está guardada —`logs-33827476219/test_hito4.log`, y los nombres son
  `NoBloquear.test_el_trabajo_se_persiste_en_disco`,
  `NoBloquear.test_la_salida_preexistente_no_cuelga` y
  `Respuestas.test_inspect_esta_exento_del_presupuesto_pero_no_del_confinamiento`—
  para quien lo retome **después** de la fusión. El tercero huele a F1 por el
  nombre, y **oler no es medir**.
* **El arreglo de F1** (§3.4), por dueño y por falta de medida.
* **Si otros módulos APTOS están verdes por el motivo equivocado.**
  `test_watcher_n` tenía **dos** verdes falsos por punteros de LFS; nada dice que
  sea el único módulo con ese problema, y auditar los 14 aptos es un encargo
  aparte. **PENDIENTE**, y declarado.

---

## 8 · Método: cómo se disparó el runner, y qué hay que saber

`workflow_dispatch` exige que el fichero exista en la **rama por defecto** —
worker4 lo midió con dos llamadas a la API (`HTTP 404: not found on the default
branch`)—. `.github/workflows/windows-tests.yml` ya está en `main`, así que se
puede disparar; **pero el runner ejecuta el fichero de la `ref` que se le pasa**,
y una sonda que sólo existe en un disco local no se puede medir en un runner.

Para las tres medidas empujé una rama **desechable**,
`tmp-medicion-w13-trazas`, disparé sobre ella y **la borré al terminar**. La
rama de entrega, `filex-ci-windows-trazas`, **no se ha empujado y no hay PR**,
como pide el encargo. Queda dicho porque es una acción sobre el remoto y el
consolidador tiene derecho a saberla: sin ella, «mídelo en el runner» y «no
empujes» no se pueden cumplir a la vez.

Un hallazgo de propina del camino: el **`pre-push` hizo su trabajo** y paró el
segundo empujón porque `bench/salidas-ci-windows-trazas` no tenía todavía su
`MANIFIESTO.md`. Ese trinquete no es decorativo.

---

## 9 · Para el inventario (no toco `ESTADO-Y-REPARTO.md`)

1. **Registrar este informe.** `ci/integridad.py` exige que todo `bench/*.md`
   figure en `ESTADO-Y-REPARTO.md`, así que **la comprobación
   `informes-registrados` falla mientras `bench/ci-windows-trazas.md` no esté
   citado allí**. No lo añado yo: el fichero es del consolidador. Es la única
   comprobación en rojo de `ci/integridad.py` en esta rama (§10).
2. **Abrir fila para F1**, el fallo de producto de §3: `Confinamiento` no
   resuelve sus raíces. Dueño natural: quien fusione `filex/confinamiento.py`.
   Con el arreglo, tres módulos (`test_cerrojo`, `test_hito1`, `test_hito7`)
   dejan de tener causa de entorno, aunque **no** pasen automáticamente a aptos
   (§4.3: la segunda capa, el corpus, sigue).
3. **`test_hito4` se retoma tras fusionar `edicius2002/filex-suelo-y-mcp`.**
4. La fila de `bench/ci-windows-hosted.md` (worker4) sigue siendo válida en todo
   salvo en el motivo de `test_hito7`, que este informe refuta con dos vías.
5. **Trampa nueva, redactada aquí y no pegada en `CLAUDE.md`** — ese fichero lo
   gobierna el maestro y dos workers añadiendo al final a la vez se pisan. Si le
   parece bien, va **al final**, como manda la regla:

   > **111. Un `CONFIRMADO` puede salir de mirar el paso de al lado en vez de la
   > traza del módulo, y entonces vale menos que un `PENDIENTE` — MEDIDO el
   > 03/09** (`bench/ci-windows-trazas.md` §5). `ci/windows-hosted-apto.json`
   > declaraba cuatro filas `PENDIENTE` y **una** `CONFIRMADO`: *«`test_hito7`:
   > el demonio Docker responde pero no está ninguna imagen»*. El dato del
   > entorno era **cierto** —`docker images` devuelve 0— y la atribución
   > **falsa**: las 42 pruebas del módulo **no mencionan a Docker ni una vez** en
   > su salida íntegra (`grep -i`, 0 líneas), y las 16 que fallan lo hacen por un
   > fallo de producto que dispara antes que ningún motor. Se escribió leyendo el
   > log del paso «El paquete importa y la CLI arranca», que estaba **al lado**.
   > **La asimetría es lo caro**: los cuatro `PENDIENTE` invitaban a mirar y el
   > `CONFIRMADO` invitaba a no mirar, así que el único motivo escrito era el
   > único que nadie iba a revisar. Es la trampa 36 —una explicación plausible no
   > es un mecanismo— con la agravante de una etiqueta que desalienta la
   > comprobación. **Un motivo se escribe con la traza del sujeto delante, o se
   > deja en `PENDIENTE`.** Y su corolario positivo, del mismo informe: la
   > hipótesis que sustituyó a ésta —«la raíz en 8.3 cierra la lista blanca»—
   > citaba la trampa correcta (la 33), sonaba bien y **también era falsa**; la
   > tumbó **el control negativo dentro de la propia sonda**, que dijo `false`
   > donde la hipótesis exigía `true`. **Toda sonda de causa lleva dentro la
   > celda que la refutaría.**

---

## 10 · Verificación

* **Los tres módulos tocados**, en la máquina del proyecto con
  `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe` (win32, 3.11.9),
  corpus real y Docker vivo: **78 pruebas · OK · 1 saltada** — los guardas
  nuevos son **inocuos donde el activo está**, que es la mitad que ningún runner
  puede comprobar.
* **Suite completa en esta máquina: `1 failed · 458 passed · 4 skipped · 130
  subtests` en 293,92 s**, y **el rojo no es mío** — es la **cuarta
  declaración** de la trampa 101, el estado de la máquina:

  * El fallo es `test_hito7.py::ApiDefensas::test_cuerpo_demasiado_grande`, que
    muere en un `ConnectionResetError` de `urllib` contra su propio servidor
    HTTP de prueba.
  * **Mi rama no toca ese código**: `git diff --stat main..HEAD -- filex/
    pruebas/test_hito7.py` devuelve **0 líneas**. La trampa 101 pide justo esto
    —*antes de culpar al cambio, comprueba si el cambio tocó código*— y aquí
    convierte «lo rompió worker13» en imposible.
  * **Reproducción intentada, 3 de 3 verdes**: `pytest -k ApiDefensas` da
    **13 passed** en 3,09 s / 3,43 s / 3,02 s.
  * Y el estado de la máquina lo explica: la tanda duró **293,92 s frente a los
    ~165 s** de la línea base de `CLAUDE.md` (**×1,78**), con **otra sesión
    corriendo `pytest pruebas/`** y el carril de GPU con `b26_borde.py` encima.
    Es la misma forma que la trampa 101 ya midió: 2 rojos a ×3,4 de duración con
    la máquina cargada, 15 verdes en tres pasadas con la máquina tranquila, sin
    una línea de diferencia en el código.
  * **Lo que sí es mío está verde**: los tres módulos que toqué —
    `test_cerrojo`, `test_hito1`, `test_watcher_n`— dan **78 pruebas, OK, 1
    saltada**, y los 8 guardas nuevos se saltan **cero** veces aquí, que es la
    prueba de que son inocuos donde el activo está.

  *(Nota de método pagada en el camino: mis dos primeros intentos se solaparon
  entre sí por mi culpa y el primero dio una `F`. Antes de culpar a los guardas
  miré quién estaba vivo por línea de órdenes —trampa 31—, y el proceso que más
  CPU gastaba no era mío: era `b26_borde.py` del otro carril. Matarlo «para
  limpiar» habría tirado una tanda de GPU ajena.)*
* **`ci/integridad.py`**: todo en verde salvo `informes-registrados`, por §9.1.
* **Runner**: ejecución **33827476219**, `success`, 18 módulos, **14 aptos ·
  331 pruebas · 67 saltos · 10,8 s · 0 colgados**.

# Cancelar de verdad, y sacar el servicio del módulo del protocolo

**Agente N-a.** Dos pendientes del inventario: **C34** (`job cancelar` no mataba
el árbol de procesos) y **N6** (`Servicio` y `Trabajos` ya no eran de MCP).

Salidas: `bench/salidas-cancelacion/` (`MANIFIESTO.md`, `c34_medidas.json`,
`c34_carrera_arranque.json`, `arnes_cancelacion.py`).
Pruebas: `pruebas/test_cancelacion.py` (13, todas fallan sin el arreglo).

> **Tanda etiquetada `SUCIA`** — la sesión de escritorio remoto está activa a
> propósito (`CLAUDE.md` §3). Testigos de la tanda publicada: deriva **0,798**
> (sin deriva) y nivel **34,92 → 26,97 ms**. Medianas de **n = 9**. Sin GPU.

---

## 0. Resumen en cinco líneas

| | Antes | Después | |
|---|---:|---:|---|
| Cancelar un motor en vuelo (invocación) | **5 156,14 ms** (= su tope) | **155,13 ms** | ×33,2 — MEDIDO |
| Cancelar una conversión por `Servicio` | **21 741,8 ms** (hasta el final) | **279,6 ms** | ×77,8 — MEDIDO |
| Contenedor tras cancelar | **vivo, 9 de 9** | **muerto, 9 de 9** | MEDIDO |
| Coste del asa en el camino normal | — | **0,7 µs (0,0026 %)** | MEDIDO |
| `filex/mcp.py` | **45 123 B / 994 líneas** | **26 968 B / 579 líneas** | −40,2 % |

Y el precio, que se paga entero y no se disimula: **tocar `filex/invocacion.py`
caduca el sondeo de los cinco motores y el grafo cae de 210 aristas `real` a
57** (§4). Es el mecanismo del commit `69f08df` funcionando exactamente como se
diseñó.

---

## 1. C34 — qué había, y por qué no era teórico

`filex/mcp.py:826-833` decía la verdad sobre sí mismo:

> *PENDIENTE, y se dice: esto detiene el trabajo ENTRE saltos, no mata el motor
> en vuelo. […] para eso `invocacion.ejecutar` tendría que devolver un asa del
> `Popen`.*

`job(job_id, "cancelar")` ponía un `threading.Event` que solo se consultaba en
el bucle de `batch`. Consecuencias medidas:

- **A nivel de invocación** el motor seguía hasta agotar su tope. En el arnés,
  con un tope de 5 s: **5 156,14 ms** de mediana, y `motivo == "tiempo_agotado"`
  en **9 de 9**. Con el tope real de MCP (`TIMEOUT_MCP = 300 s`) la espera sería
  de **hasta cinco minutos**.
- **Extremo a extremo**, `tipico.mp4 → webm` por `Servicio`: cancelar no cambiaba
  nada y el trabajo terminaba en **21 741,8 ms**, con estado `completed`. Es
  decir: *se pedía cancelar una conversión y salía la conversión hecha*.

No es teórico por un motivo más, ya MEDIDO en este repositorio (`CLAUDE.md` §3,
`bench/hito5-documental.md` §1): **matar el `docker run` no mata el contenedor**,
y tres `soffice` colgados sobrevivieron 37 minutos a un `taskkill /F /T`.

## 2. C34 — la solución: el asa no se devuelve, se hace ALCANZABLE

El comentario pedía que `ejecutar` **devolviera** el `Popen`. Eso obliga a
enhebrar el asa por `FileX.convertir` → `_un_salto` → `ejecutar` y a inventar un
identificador de trabajo que el núcleo no tiene por qué conocer. **Y no hacía
falta**, por una observación que el propio diseño ya garantizaba:

> **Un trabajo corre entero en su propio hilo.** `servicio.py` lanza
> `threading.Thread(target=corre, …)` y toda la conversión —los N saltos, el
> contrato, el desechable— ocurre ahí. Así que *«la invocación en vuelo de este
> trabajo»* y *«la invocación en vuelo de este hilo»* son la misma cosa.

`filex/invocacion.py` lleva ahora un registro `{ident de hilo → (Popen, argv)}`
y tres funciones: `cancelar_hilo`, `hilo_cancelado`, `olvidar_hilo`.
**`filex/nucleo.py` no cambia ni una línea** — que además era un requisito de
reparto, porque lo tenía otro agente.

Tres detalles que no son adorno:

1. **La marca, además del asa.** `cancelar_hilo` marca el hilo *y* mata. Entre
   dos saltos no hay ningún `Popen` que alcanzar, y sin la marca la cancelación
   se perdería justo en esa ventana; `ejecutar()` la consulta antes de arrancar,
   así que un camino de dos saltos cancelado en el primero **no empieza el
   segundo** (`test_un_hilo_cancelado_no_arranca_el_siguiente_motor`).
2. **La ventana entre `Popen()` y el registro.** Se cierra comprobando la marca
   *dentro* del mismo cerrojo con el que se registra: si la cancelación pasó por
   ahí, no vio el asa y se mata en ese punto. Sin esto, esa ventana deja un
   motor inmortal.
3. **`cancelado` no es `agotado` ni «el motor rechazó».** `Resultado` gana un
   campo y `motivo` devuelve `"cancelado"`. Es la trampa 25 de `CLAUDE.md` en
   otra forma: *dos causas distintas con la misma pinta de fallo*. Con ello el
   trabajo termina en **`cancelled`**, no en `failed` — MEDIDO, 9 de 9.

### Números (M1 y M2, `c34_medidas.json`)

| Medida | Vía | Mediana (n=9) | Recorrido |
|---|---|---:|---|
| M1 invocación (`ffmpeg` eterno, tope 5 s) | cooperativa (lo que había) | **5 156,14 ms** | 5 127–5 202 |
| M1 invocación | `cancelar_hilo` | **155,13 ms** | 134–175 |
| M2 servicio (`tipico.mp4 → webm`) | sin cancelar | **21 741,8 ms** | 21 164–24 003 |
| M2 servicio | `job(…, "cancelar")` | **279,6 ms** | 270–329 |

**×33,2 y ×77,8.** Los 155 ms de M1 son el coste del `taskkill /F /T` y del
`communicate` posterior; los 280 ms de M2 añaden el contrato abortado y el
borrado del desechable de R18.

## 3. El salto EN CONTENEDOR — lo que pedía el encargo, con las palabras exactas

**Sí lo resuelve, y hubo que medirlo dos veces para creérselo.**

Un salto documental es `docker run --rm --init --entrypoint timeout … -k 5 N`.
Matar el árbol mata al **cliente** de Docker. Reproducido aquí sobre 9 celdas
(M3, `docker run … sleep 120` con bind mount):

| Qué se mata | Contenedor 2 s después |
|---|---|
| solo el cliente (`_matar_arbol`) | **`contenedor_vivo` 9 de 9** |
| cliente **y** contenedor | **`contenedor_muerto` 9 de 9** |

Es la confirmación independiente del MEDIDO de `CLAUDE.md` §3 por una tercera
ruta, y sobre `--rm`, que tampoco basta.

El remedio vive en `invocacion._matar_contenedor_de(argv)` y solo se dispara si
`argv` es un `docker run`: identifica al contenedor por el **origen de su bind
mount de escritura**, que Docker devuelve **literalmente** en `.Mounts.Source`
—sondeado en ejecución, no deducido: en esta máquina la ruta de Windows con
barras normales vuelve tal cual, sin traducirse a `/run/desktop/mnt/host/…`—.
Coste: **527,2 ms** de mediana (`docker ps` + `docker inspect` + `docker kill`
con 5 contenedores en pie).

Tres decisiones que salieron de medir, no de pensar:

- **El contenedor PRIMERO, el cliente después.** En cuanto el cliente muere, el
  hilo del trabajo sale de `communicate`, vuelve al núcleo y su `finally`
  **borra el desechable**, que es el origen del bind mount. Ése es exactamente
  el agravante ya medido —con el origen borrado, `docker rm -f` responde *«did
  not receive an exit event»*—. Al revés no hay carrera.
- **Los montajes `readonly` no identifican nada.** El motor monta dos cosas: el
  desechable (escritura, único por conversión) y la **entrada** en solo lectura,
  que es un fichero del usuario. Dos conversiones del mismo fichero comparten la
  segunda, así que contarla convertiría la cancelación en un arma contra el
  trabajo del vecino — la trampa 26 otra vez, con otro recurso compartido.
- **Hay una CARRERA DE ARRANQUE, y se vio porque se midió — MEDIDO.** En la
  primera tanda de M5, **1 de 9** cancelaciones dejó un contenedor huérfano
  (`c34_carrera_arranque.json`, `contenedores_vivos_despues = [1,0,0,0,0,0,0,0,0]`),
  y fue justo la cancelación más rápida (399 ms). El motivo: entre que se lanza
  el cliente y que el demonio **crea** el contenedor pasan cientos de
  milisegundos, y en esa ventana `docker ps` no lo ve. Se cierra insistiendo
  hasta `ESPERA_CONTENEDOR = 3 s` **mientras el cliente siga vivo** —que es la
  ventana en la que el desechable todavía no se ha borrado—. Tras el arreglo:
  **0 huérfanos en 9 de 9**, dos tandas seguidas.

### M5 — extremo a extremo con un motor en contenedor

`html → pdf` por `doc_libreoffice`, por la misma puerta que usan las cuatro
superficies:

| | Mediana (n=9) |
|---|---:|
| sin cancelar | **1 770,6 ms** (`completed` 9/9) |
| `job(…, "cancelar")` | **589,2 ms** (`cancelled` 9/9, `motor_detenido=True`) |
| contenedores vivos 2 s después | **0, nueve de nueve** |

**La ganancia de tiempo aquí es solo ×3,0, y decirlo importa:** el valor de C34
en contenedor **no es la latencia, es que no queda un contenedor vivo**. Con una
conversión documental pesada la ganancia de tiempo sería la de M2; con una
ligera es pequeña — y el huérfano de 37 minutos habría dado igual.

## 4. Lo que C34 **NO** cubre

1. **Es de PROCESO.** El registro vive en la memoria de un `filex`. Cancelar un
   trabajo leído del disco desde otro proceso no alcanza su `Popen`, **y la
   respuesta lo dice en vez de fingirlo**: `motor_detenido: false` y *«el trabajo
   no corre en este proceso»*. Es el mismo alcance declarado que el cerrojo de
   destinos de `nucleo.py` (trampa 26). **PENDIENTE**: cerrarlo entre procesos
   necesita un canal con nombre o un fichero de mando por trabajo.
2. **Un hilo, una invocación.** Si un salto lanzara algún día dos motores en
   paralelo desde el mismo hilo, en el registro solo estaría el último.
3. **Los `ident` de hilo se reciclan.** `olvidar_hilo()` no es opcional:
   `servicio.py` la llama en un `finally` en los dos trabajos. Quien añada una
   tercera clase de trabajo tiene que hacer lo mismo, y **eso es una disciplina
   que hay que recordar**, que es justo lo que este repositorio evita en las
   invocaciones. Cerrarlo bien pide un envoltorio `with invocacion.hilo_de(t):`
   — **PENDIENTE**.
4. **El identificador del contenedor sigue siendo indirecto.** Se deduce del
   bind mount porque la orden no lo declara. Lo limpio es **`--cidfile`** (o un
   `--name` único) en `_argv_docker` y un `_EnContenedor.parar()` de verdad —hoy
   `Motor.parar()` es un `return None` que **ninguna** subclase sobrescribe—.
   No se ha hecho aquí por dos razones, y las dos se dicen: `filex/motor_contenedor.py`
   es de otro reparto, y tocarlo **caducaría además la huella `motor` de los tres
   sondeos documentales**, que es un coste mayor que el que ya se paga.
   **PENDIENTE, con el fichero y la línea nombrados.**
5. **No hay inventario de huérfanos.** `_matar_arbol` ya declaraba que matar el
   árbol *«es lo mínimo, no la garantía»*. Sigue igual para los motores nativos.

---

## 5. N6 — el servicio fuera del módulo del protocolo

`filex/mcp.py` eran **45 123 B / 994 líneas** y contenía `Trabajo`, `Trabajos` y
`Servicio`. La prueba de que ya no eran de MCP estaba en dos importaciones:

```
filex/api.py:76      from .mcp import Servicio, Trabajos
filex/watcher.py:59  from .mcp import COMPLETADO, FALLIDO, Trabajos
```

**Dos superficies que no hablan MCP importando del módulo del protocolo.** Es
R10 en su forma inversa: no es validación que se cae a la superficie, es
**núcleo atrapado dentro de una**.

Ahora: `filex/servicio.py` (**24 134 B / 524 líneas**) con `Trabajo`, `Trabajos`,
`Servicio`, los presupuestos de tope (`TIMEOUT_MCP`, `TIMEOUT_MAXIMO`,
`SONDEO_MS`) y el vocabulario de estado de SEP-1686. `filex/mcp.py` queda en
**26 968 B / 579 líneas** (−40,2 %) con lo que sí es del protocolo: el catálogo,
los *roots* y el servidor.

### La decisión que pedía el encargo: **NO se reexporta**

`filex/mcp.py` **no** deja un alias de compatibilidad. Razones, por orden:

1. Un alias mantendría viva la respuesta vieja a *«¿dónde viven los trabajos?»*,
   que es exactamente la que N6 refuta. El acoplamiento seguiría, en silencio.
2. **No hay usuarios externos**: es un repositorio de investigación y el censo de
   importadores cabía en cuatro líneas.
3. La comprobación de que la separación es real se puede automatizar, y se ha
   hecho: `test_ninguna_superficie_entra_por_la_puerta_vieja` recorre el AST de
   todos los `.py` de `filex/` y `pruebas/` y falla si alguno toma `Servicio`,
   `Trabajo`, `Trabajos` o los cuatro estados de `filex.mcp`. Con una
   reexportación esa prueba sería imposible de escribir.

**Matiz honesto:** `filex/mcp.py` sí hace `from .servicio import Servicio,
Trabajos`, porque no se puede construir un servidor sin su servicio, y eso deja
`filex.mcp.Servicio` accesible. Es una importación **para uso propio**, no un
alias documentado, y la prueba anterior se encarga de que nadie más entre por
ahí. La flecha ahora apunta en el sentido correcto: el protocolo depende del
servicio, y `test_servicio_no_importa_el_protocolo` comprueba que no hay vuelta.

### La prueba estructural de R10 (`pruebas/test_hito7.py:225`)

Afirmaba el texto literal `"from .mcp import Servicio, Trabajos"` dentro de
`api.py`. **Se ha actualizado, no borrado**: sigue probando lo mismo —que la API
no reimplementa el núcleo— con la forma correcta (`from .servicio import …`), y
se le ha añadido `assertNotIn("from .mcp import", …)`. La afirmación no cambia;
cambia su dirección, que era en sí parte del defecto.

---

## 6. El impacto sobre el sondeo — la huella funcionó, y se paga entera

Antes de tocar nada, y después:

```
antes    {'sin_huella': [], 'caducados': {}, 'build_distinto': []}
         {'real': 210, 'nominal': 5}

después  caducados: {'imagemagick': ['invocacion'], 'ffmpeg': ['invocacion'],
                     'doc_libreoffice': ['invocacion'], 'doc_pandoc': ['invocacion'],
                     'doc_calibre': ['invocacion']}
         {'sin_sondear': 155, 'real': 57, 'nominal': 3}
```

**La caída exacta: 210 → 57 aristas `real` y 5 → 3 `nominal`; 155 pasan a
`sin_sondear`** (153 reales + 2 nominales). El aviso del encargo predecía «210 a
57 y las 153 del disco a `sin_sondear`»: **coincide a la unidad**, con la
precisión de que las que se pierden son 155, no 153, porque también caen dos
`nominal`.

Componentes de la huella, antes y después:

| Componente | Antes | Después |
|---|---|---|
| `invocacion` | `de4a69976377acb8` | `9cc8c5ee57d3f27d` |
| `contrato` | `6af6b556299be217` | `6af6b556299be217` (sin mover) |
| `motor` (los cinco) | — | **sin mover** |

**El mecanismo se comportó bien y lo digo como refutación de mi propia sospecha
inicial.** Entré a este encargo buscando una solución que no tocara
`invocacion.py`, porque el aviso decía que la mejor solución sería ésa. **No la
hay, y la caducidad además es CORRECTA, no un falso positivo:**

- `nucleo.py` está fuera de mi reparto y es quien llama a `ejecutar`, así que el
  único sitio donde el asa se puede publicar es dentro de `ejecutar`.
- Y aunque la huella de `invocacion` fuera un **cierre de llamadas** desde
  `ejecutar` —como la de `contrato`, en vez del fichero entero— **caducaría
  igual**: el cambio está dentro de `ejecutar`. Así que la granularidad gruesa de
  este componente no ha costado nada en este caso concreto: la afinidad fina
  habría dado el mismo resultado.
- Y la caducidad no es supersticiosa: `ejecutar` puede ahora **devolver sin
  lanzar el proceso** (hilo ya cancelado) y **morir por una mano ajena**. Eso
  cambia el `rc` de una arista en un régimen nuevo. Marcarlo es lo correcto.

**Lo que NO he hecho, por instrucción explícita del encargo: resondear.** Cuesta
horas de contenedor y no era el trabajo. Queda **PENDIENTE, nombrado**:

> Volver a ejecutar los tres arneses de sondeo —`bench/salidas-sondeo-im/sonda_im.py`,
> `bench/salidas-sondeo-ff/sondear_ff.py` y `bench/salidas-sondeo-doc/_sonda23.py`
> con sus escritores de JSON— y volver a sellar `filex/sondeo/*.json` con la
> huella nueva. Hasta entonces el grafo declara **57 aristas `real`** y las otras
> 155 `sin_sondear`, que es la degradación honesta que el diseño quería:
> **prefiere decir «no lo sé» a heredar 20 medidas falsas de 21.**

**Y esto tiene una consecuencia de coordinación que conviene escribir:** cualquier
cambio futuro en `invocacion.py` cuesta un resondeo completo de los cinco
motores. Es el fichero más caro del repositorio para tocar, y hasta hoy había
cambiado **0 veces desde el commit inicial** —lo dice el propio `huella.py`—.
Este es el primero. Agrupar cambios de `invocacion.py` y resondear una sola vez
vale más que cinco arreglos sueltos.

---

## 7. La suite

| | Antes | Después |
|---|---|---|
| `python -m pytest pruebas/ -q` | 151 passed, 6 skipped | **163 passed, 6 skipped, 1 failed** |

Los tres movimientos, uno a uno:

1. **+13**: `pruebas/test_cancelacion.py`, nuevo. Las 13 fallan sin el arreglo
   (4 de asa, 2 de servicio extremo a extremo, 3 de contenedor, 4 de N6).
2. **−1 fallo nuevo**: `test_sondeo.py::SelladoDelDisco::test_ningun_motor_disponible_tiene_el_sondeo_caducado`.
   **Es la prueba que N-huella escribió para que esto no pasara en silencio, y
   está haciendo su trabajo.** Su mensaje es explícito: *«hay que RESONDEAR y
   volver a sellar, no editar la huella a mano»*, así que **no se ha tocado la
   huella de los ficheros de sondeo**. Se cierra resondeando (§6), no editando.
3. **0 movimientos en el resto**: las 151 de antes siguen pasando, incluida
   `test_hito7.py::test_la_api_no_reimplementa_el_servicio` con su afirmación
   estructural actualizada.

> **Aviso de reproducción:** el *worktree* venía con `corpus/` en punteros de Git
> LFS y eso hacía fallar 15 pruebas por «el motor rechazó la conversión» —nada
> que ver con este trabajo—. `git lfs pull` dentro del *worktree* lo arregla.
> Merece estar escrito: el modo de fallo es indistinguible de una regresión real.

---

## 8. Coste del arreglo en el camino normal

`M4`: el registro son dos tomas del cerrojo, una inserción y un borrado en un
diccionario. **0,7 µs de mediana**, frente a **27,3 ms** de la invocación más
barata que existe (`ffmpeg -version`): **0,0026 %**. Sobre una conversión real de
21,7 s es **0,000003 %**. La caza del contenedor **no se paga nunca** en el
camino normal: solo se dispara al cancelar, y solo si `argv[0]` es `docker` y
`argv[1:3]` contiene `run`.

## 9. Ficheros tocados

| Fichero | Qué |
|---|---|
| `filex/servicio.py` | **nuevo**: `Trabajo`, `Trabajos`, `Servicio`, topes y estados |
| `filex/mcp.py` | −40,2 %: queda catálogo, *roots* y servidor |
| `filex/invocacion.py` | registro por hilo, `cancelar_hilo`, `Resultado.cancelado`, muerte del contenedor |
| `filex/api.py` | una línea de importación |
| `filex/watcher.py` | una línea de importación |
| `pruebas/test_hito4.py` | `M.*` → `S.*` donde el nombre se mudó |
| `pruebas/test_hito7.py` | solo la afirmación estructural de R10 (línea 225) y su importación |
| `pruebas/test_cancelacion.py` | **nuevo**, 13 pruebas |
| `bench/salidas-cancelacion/` | **nuevo**: arnés, dos JSON y `MANIFIESTO.md` |

**No se ha tocado** `filex/nucleo.py`, `filex/motores.py`, `filex/motor_contenedor.py`,
`filex/sondeo/*.json` ni ningún documento maestro.

# Parar un contenedor deja de ser una deducción

**Agente Q.** El residuo que N-a dejó nombrado al cerrar C34
(`bench/cancelacion-y-servicio.md` §4.4):

> *«El identificador del contenedor sigue siendo indirecto. Se deduce del bind
> mount porque la orden no lo declara. Lo limpio es **`--cidfile`** (o un
> `--name` único) en `_argv_docker` y un `_EnContenedor.parar()` de verdad —hoy
> `Motor.parar()` es un `return None` que **ninguna** subclase sobrescribe—.»*

Salidas: `bench/salidas-contenedor/` (`MANIFIESTO.md`, `sonda_id.py`,
`sonda_id.json`, `arnes_contenedor.py`, `a4_medidas.json`).
Pruebas: `pruebas/test_cancelacion.py`, que pasa de 13 a 20.

> **Tanda etiquetada `SUCIA`** — la sesión de escritorio remoto está activa a
> propósito (`CLAUDE.md` §3). Testigos de la tanda publicada: deriva **0,978**
> (sin deriva) y nivel **34,18 → 34,15 ms**, ninguno agotado. Medianas de
> **n = 9**. Sin GPU y sin tomar el lock. **Hay otro agente (P) trabajando en la
> máquina**: las cifras absolutas no son comparables con las de la tanda de N-a,
> y donde se comparan se dice.

---

## 0. Resumen en seis líneas

| | Línea base (N-a) | a4 | |
|---|---|---|---|
| Matando solo el cliente, contenedor 2 s después | **vivo 9 de 9** | **vivo 9 de 9** | premisa reproducida — MEDIDO |
| Cancelar: contenedor muerto | **9 de 9** en 527,2 ms | **9 de 9** en **344,08 ms** | MEDIDO, con salvedad de tanda |
| Carrera de arranque | 0 huérfanos de 9 | **0 huérfanos de 9** | MEDIDO |
| Cancelar una conversión mata la de al lado | *no se pudo comprobar* | **no: vecino vivo 9 de 9** | MEDIDO — nuevo |
| Coste de IDENTIFICAR al contenedor | 217,35 ms (`ps` + `inspect`) | **0,01 ms** (leer `argv`) | **×21 735** — MEDIDO |
| `Motor.parar()` | gancho muerto, 0 subclases | **3 subclases**, probado extremo a extremo | MEDIDO |

Y el precio, que se paga entero: **tocar `filex/motor_contenedor.py` caduca el
componente `motor` de los tres sondeos documentales**, además del `invocacion`
que ya había caducado N-a. Estaba previsto y aceptado por el encargo (§6).

---

## 1. La decisión de diseño no se dedujo: se sondeó

`CLAUDE.md` §5 lo exige, y aquí importaba porque **la documentación de Docker
describe las dos banderas, no cuál sirve para MATAR**. Lo que decide es *cuándo*
está disponible el identificador y *qué pasa cuando el cliente muere*
(`sonda_id.json`, imagen `alpine:latest`).

| Sonda | Pregunta | Resultado — MEDIDO |
|---|---|---|
| **S1** | ¿Docker rechaza un `--name` duplicado? | **Sí**: `rc=125`, *«Conflict. The container name "/filexq-sonda-…" is already in use»* |
| **S2** | ¿`docker kill <nombre>` mata igual que por ID? | Sí, `rc=0` en **238,7 ms**, contenedor no vivo después |
| **S3a** | ¿Cuándo aparece el `--cidfile`? | El fichero a **107,9 ms**, con el ID dentro a **225,6 ms** |
| **S3b** | ¿Docker se niega si el cidfile ya existe? | **Sí**: `rc=125`, *«container ID file found, make sure the other container isn't running or delete …»* |
| **S3c** | ¿`--rm` borra el cidfile al salir? | **No. Sobrevive** |
| **S4** | ¿Cuánto tarda cada identificador en servir? (n=9) | cidfile **314,7 ms** · nombre **686,1 ms** · barrido de montajes **880,0 ms** |
| **S5** | ¿Resuelve el nombre con el CLIENTE ya muerto? | **Sí**, y ahí está el caso real: tras `taskkill /F /T` el contenedor sigue vivo y `docker kill <nombre>` lo mata en **260,4 ms** |
| **S6** | El estado **`Created`**: ¿quién lo ve y quién lo mata? | `docker ps` **NO lo lista**; `docker ps -a` sí. `docker kill` **falla** (`rc=1`, *«cannot kill container: … is not running»*); **`docker rm -f` sí lo borra**, `rc=0` en 120,3 ms |

### Se eligió `--name`, y S4 dice lo contrario — por qué se ignoró

**S4 favorece al `cidfile` (314,7 frente a 686,1 ms) y aun así se descartó.** Dos
motivos, y el segundo es el que decide:

1. **La medida de S4 tiene un sesgo de orden que declaro**: el bucle comprueba
   primero el cidfile —una lectura de fichero local, microsegundos— y después el
   nombre, que exige una ida y vuelta al demonio (~120–240 ms). La ventaja real
   del cidfile no es que el contenedor exista antes, es que **detectarlo es
   local**. La cifra de S4 mide en parte mi bucle, no solo a Docker.
2. **Y da igual, porque el cidfile es un FICHERO con ciclo de vida propio, y su
   sitio natural es justo el que no puede ser.** El cidfile viviría en el
   directorio desechable de R18 — y ése es exactamente el directorio que el
   `finally` del núcleo borra en cuanto el cliente muere. Es el agravante ya
   medido (`CLAUDE.md` §3: con el origen del bind mount borrado, `docker rm -f`
   responde *«did not receive an exit event»*) reaparecido en otro recurso:
   **con el cidfile dentro del desechable, matar al cliente destruye el
   identificador**. Sacarlo fuera obliga a inventar un directorio con su propia
   limpieza — y S3b/S3c dicen que **el fichero sobrevive al `--rm` y que Docker
   se niega a arrancar si ya existe**, así que una limpieza que falle deja el
   motor inservible.

**El `--name` no tiene ninguno de esos problemas: está DENTRO del `argv`.** Quien
cancela ya tiene el `argv` —`_EN_VUELO[ident] = (proc, argv)`—, así que
identificar cuesta cero lecturas del demonio y cero ficheros. Y S1 añade lo que
faltaba: **la unicidad no es una promesa de mi generador, la impone el demonio**.

**Lo que el `--name` NO arregla, y hay que decirlo: la carrera de arranque.** El
nombre no existe antes que el contenedor. S4 lo mide (686,1 ms de mediana hasta
que responde) y M7 lo cuantifica en huérfanos. La espera de N-a sigue haciendo
falta entera.

---

## 2. Lo que se hizo

### 2.1 `filex/motor_contenedor.py` — la orden declara el contenedor

`_argv_docker` añade `--name <nombre>` justo después de `--rm --init`. El nombre
lo acuña **`invocacion.nombre_de_contenedor()`** y tiene la forma
`filex-<pid en hex>-<uuid4>`.

Dos decisiones que no son estéticas:

- **El formato lo conoce `invocacion` y nadie más.** Quien acuña y quien valida
  son la misma pieza, así que no pueden divergir. `motor_contenedor` pide un
  nombre; no sabe cómo es.
- **El PID va dentro a propósito.** `CLAUDE.md` §4.31 dice que en esta máquina lo
  único atribuible de un proceso es su línea de órdenes. Aquí el **nombre del
  contenedor** dice qué proceso `filex` lo lanzó, que es lo que hoy no se puede
  saber de un huérfano. Y el prefijo `filex-` hace censable la familia entera:
  `docker ps -a --filter name=filex-`.

También lleva nombre el `docker run` de `_sondear_binarios`: pasa por
`invocacion.ejecutar`, luego está en el registro por hilo y es cancelable, y sin
`--name` sería **el único contenedor de FileX que una cancelación no alcanzaría**.

### 2.2 `filex/motor_contenedor.py` — `parar()` de verdad

El problema no era escribir el método, era **a quién parar**. `Motor.parar()` no
recibe argumentos y **la instancia del motor es única para todo el proceso** —
`nucleo._un_salto` hace `self.motores[arista.motor]`—. Guardar el nombre en
`self` haría que dos conversiones simultáneas se pisaran el identificador y una
parara el contenedor de la otra: **la trampa 26 con un tercer recurso**.

Se guarda **por HILO** (`_HILO = threading.local()`), que es la misma
observación con la que N-a resolvió C34: un trabajo corre entero en su propio
hilo. Y lo escribe `_argv_docker`, que es el único sitio donde se construye un
`docker run` de un motor — **no hay vía que se lo salte**, así que no es «un
valor que hay que acordarse de fijar», que es el defecto que este mismo fichero
ya había documentado con `self._tope_dentro`.

`parar()` hace `docker kill` **y** `docker rm -f`: el primero para el que corre,
el segundo para el que se creó y no llegó a arrancar. Los dos son seguros porque
el nombre lo acuñó FileX y S1 garantiza que es único.

### 2.3 `filex/invocacion.py` — la deducción, sustituida

`_fuentes_de_montaje` y `_victimas` **se han borrado**. En su lugar,
`_nombre_contenedor_de(argv)`, que lee el `--name` del propio `argv`.

**Y hay una garantía nueva que antes no existía.** La vieja identificación se
protegía del vecino con una *convención*: no contar los montajes `readonly`,
porque la entrada es un fichero del usuario que dos conversiones del mismo
fichero comparten. La nueva se protege con un *predicado sobre el
identificador*: `_nombre_contenedor_de` **solo devuelve un nombre que case con
`_RE_NOMBRE`**, es decir uno acuñado por este módulo. Un `--name` que llegara
dentro de la orden del motor, o de datos del usuario, no lo cumple.
`matar_contenedor` y `barrer_contenedor` repiten la comprobación en su puerta:
**no hay vía en FileX para matar un contenedor que FileX no haya lanzado.**

### 2.4 Lo que se AÑADE sobre N-a: el barrido de cierre

`cancelar_hilo` hace ahora tres cosas en este orden: **contenedor, cliente,
barrido**.

El tercero es nuevo y cierra un agujero que la deducción no podía cerrar. El
cliente de `docker run` hace dos cosas —**crear** el contenedor y **arrancarlo**—
y si el `taskkill` cae entre las dos queda un contenedor **creado y no
arrancado**. Las tres propiedades de ese estado están **MEDIDAS y son
deterministas** (S6, `sonda_id.json`): construyéndolo a mano con
`docker create`,

- **`docker ps` no lo lista** y `docker ps -a` sí — así que un censo de
  huérfanos con `docker ps` es ciego a él, y el barrido por montajes tampoco lo
  veía nunca;
- **`docker kill` falla**, con `rc=1` y *«cannot kill container: … is not
  running»*, de modo que la vía de cancelación no lo alcanza;
- **`docker rm -f` sí lo borra**, `rc=0` en **120,3 ms** — y eso **exige tener un
  identificador**, que es justo lo que la deducción perdía al morir el cliente,
  porque el desechable desaparecía con él.

**Y el estado aparece de verdad en la ventana de cancelación, aunque de forma
intermitente.** En el brazo sin defensas de M7 salió **1 de 9 en estado
`Created`** en una tanda (`a4_m7_estado_created.json`) y **0 de 9** en otra: es
la misma forma que el huérfano de 1 de 9 que persiguió N-a. **Dicho con
honestidad: sobre esa celda mis dos observadores llegaron a discrepar** —dos
`docker ps -a` consecutivos, uno lo veía y el otro no—, y por eso la trampa se
apoya en S6, que es determinista, y no en esa observación.

**El barrido solo se dispara si el `kill` NO lo consiguió**, que es cuando el
estado raro puede existir. Si el contenedor llegó a correr y se mató, `--rm` lo
limpia solo y un `docker rm -f` de más costaría otra ida y vuelta al demonio
(**238,7 ms**, S2) sin cambiar nada.

---

## 3. Las medidas (`a4_medidas.json`, n=9)

### M1 — la premisa, reproducida antes de nada

Matando **solo** el árbol del cliente, sin tocar el contenedor:

| | Mediana | Recorrido | Contenedor 2 s después |
|---|---:|---|---|
| `_matar_arbol` a secas | **188,25 ms** | 167,5–199,6 | **vivo, 9 de 9** |

Es la confirmación independiente, por cuarta ruta, del MEDIDO de `CLAUDE.md` §3
(*matar el `docker run` no mata el contenedor, y `--rm` tampoco*). **Si esto
dejara de reproducirse, todo lo demás sobraría**, y por eso va primero.

### M2 — el remedio

| | Mediana | Recorrido | |
|---|---:|---|---|
| N-a, deduciendo del bind mount | 527,2 ms | — | muerto 9 de 9 |
| **a4, por el nombre declarado** | **344,08 ms** | 332,9–385,1 | **muerto 9 de 9** |

`motivo == "cancelado"` en **9 de 9**, asa encontrada en **9 de 9**, cliente
muerto en **9 de 9**.

> **Salvedad, y va en negrita porque `CLAUDE.md` §3 la exige:** son **dos tandas
> distintas**, con otro agente en la máquina, y *«las cifras absolutas de tandas
> distintas no son comparables»*. Lo que sí es defendible es el **mecanismo**: la
> vía vieja hacía `docker ps -q` + `docker inspect` de toda la máquina antes de
> matar (M3: **217,35 ms**), y la nueva no hace ninguna de las dos. La diferencia
> de 183 ms cae dentro de ese ahorro.

### M3 — el coste de IDENTIFICAR, A/B dentro de la misma tanda

Con un contenedor real en pie y los 6 del proyecto en la máquina. **No incluye el
`docker kill`, que es el mismo por las dos vías**: lo que se compara es solo lo
que la declaración se ahorra.

| Vía | Mediana | Aciertos |
|---|---:|---|
| Deducción por montajes (`ps -q` + `inspect`) | **217,35 ms** | 9 de 9 |
| Declaración (leer `--name` del `argv`) | **0,01 ms** | 9 de 9 |

**×21 735.** Y hay algo que el cociente no dice: **la deducción escala con el
número de contenedores de la máquina** —`docker inspect` recibe la lista
entera—, mientras que la declaración es O(1). En una máquina de 6 contenedores
cuesta 217 ms; en una de 60, más.

### M4 — la carrera de arranque sigue cerrada

Se cancela **con el `Popen` ya registrado** —el cliente CORRE— y sin esperar a
que el contenedor exista:

| | |
|---|---|
| El contenedor existía al cancelar | **0 de 9** *(la ventana es real)* |
| Huérfanos después | **0 de 9** |
| Mediana de `cancelar_hilo` | 711,38 ms |

Los 711 ms son la espera: `docker kill` falla hasta que el contenedor arranca, y
S4 mide esa aparición en 686,1 ms de mediana. **Es tiempo que se paga solo al
cancelar en el primer segundo de una conversión.**

> **Y aquí hay una autocorrección que vale la pena.** La primera versión de este
> arnés esperaba a que el **hilo** arrancara, no a que el `Popen` estuviera
> registrado. Con eso `cancelar_hilo` devolvía `False` en **0,01 ms**,
> `ejecutar()` salía por la marca sin lanzar nada y **no llegaba a existir
> ningún contenedor**: salían **0 huérfanos de 9 que no probaban absolutamente
> nada**. Es la trampa 25 en versión de arnés — dos causas distintas con la
> misma pinta de éxito — y estuvo a punto de publicarse como «la carrera sigue
> cerrada».

### M5 — lo que N-a no pudo comprobar: el vecino

Dos conversiones simultáneas que **comparten hasta el directorio de trabajo** —el
peor caso imaginable, que en producción no ocurre porque el desechable de R18 es
privado— y se cancela una:

| | |
|---|---|
| Arrancaron los dos contenedores | 9 de 9 |
| El cancelado muere | **9 de 9** |
| **El vecino sigue vivo** | **9 de 9** |

Éste es el fallo que el montaje `readonly` habría causado si se hubiera contado
como identificador: dos conversiones **del mismo fichero de entrada** comparten
el `.Mounts.Source` de la entrada. Con el nombre no hay recurso compartido que
confundir. **El identificador es del CONTENEDOR, no de un recurso.**

### M6 — el coste en el camino normal

| | Mediana (n=2001) |
|---|---:|
| Acuñar el nombre | **2,9 µs** |
| `_argv_docker` completo, con nombre | **4,0 µs** |

Sobre una conversión documental de **1 770,6 ms** (la de N-a, `html→pdf`), acuñar
el nombre es el **0,00016 %**. Es lo único del a4 que se paga siempre; todo lo
demás corre al cancelar o al agotarse el tope.

### M7 — las dos defensas, una contra la otra

M4 mide la **espera**, no el **barrido**: la espera encuentra el contenedor,
`docker kill` lo mata, y el barrido no llega a dispararse nunca. Para que tenga
algo que hacer hay que devolver la cancelación al régimen de antes de C34
(`ESPERA_CONTENEDOR = 0`). Tres brazos, cliente corriendo y contenedor todavía
no, n=9 cada uno:

| Brazo | Huérfanos | Mediana |
|---|---|---:|
| **Ni espera ni barrido** (antes de C34) | **9 de 9** | 256,75 ms |
| Solo barrido (`rm -f` del nombre, sin esperar) | **0 de 9** | 520,25 ms |
| Solo espera (lo de N-a) | **0 de 9** | 685,75 ms |

Tres cosas se leen aquí:

1. **Sin ninguna de las dos, el huérfano es sistemático en esta ventana: 9 de
   9.** N-a vio 1 de 9 porque su arnés esperaba al hilo; con el `Popen` ya
   registrado, la ventana se acierta siempre.
2. **Cualquiera de las dos, por separado, basta**: 0 de 9. No son redundantes por
   descuido: la espera mata el contenedor **mientras el cliente vive**, que es lo
   que garantiza el orden «contenedor antes que cliente» y evita el *«did not
   receive an exit event»*. El barrido corre después y compite con el `finally`
   del núcleo. Por eso la espera va primero y el barrido es la red.
3. **El barrido cierra la carrera SIN ESPERAR**, y en 165 ms menos. Es una opción
   que la deducción por montajes **no podía ofrecer**, porque cuando el cliente
   muere el origen del bind mount desaparece y no queda nada que nombrar.

---

## 4. Lo que a4 **NO** cubre

1. **La cancelación sigue siendo de PROCESO.** El registro por hilo vive en la
   memoria de un `filex`. Es el residuo 1 de N-a y no se toca: el nombre
   declarado **sí** cruza procesos —está en el `argv` y en el demonio—, pero
   quien quiera usarlo desde otro proceso necesita antes leer ese `argv`, y eso
   exige el canal con nombre o el fichero de mando por trabajo que N-a dejó
   **PENDIENTE**.
2. **El barrido cubre el estado `Created`, pero no lo he visto cubrirlo *en la
   configuración de producción*.** Lo MEDIDO es: (a) sobre un `Created`
   construido a mano, `docker kill` falla y `docker rm -f` funciona (S6,
   determinista); (b) el estado aparece en la ventana de cancelación, 1 de 9 en
   una tanda de M7; y (c) el barrido solo, sin espera, deja 0 huérfanos de 9.
   Lo que **no** he conseguido provocar a voluntad es la conjunción exacta
   —contenedor `Created` **y** espera agotada **y** barrido salvándolo—, porque
   con `ESPERA_CONTENEDOR = 3 s` la espera casi siempre llega antes. Que el
   barrido sea *necesario* en producción, y no solo suficiente, es **PENDIENTE**.
3. **`parar()` es del HILO, no del trabajo.** Si un salto lanzara algún día dos
   contenedores desde el mismo hilo, `_HILO.contenedor` solo tendría el último.
   Es el residuo 2 de N-a con otra cara.
4. **No hay inventario de huérfanos, pero ahora se puede hacer.** El prefijo
   `filex-` y el PID en el nombre hacen que un censo sea
   `docker ps -a --filter name=filex-` filtrado por `_RE_NOMBRE` — que es lo que
   hace el arnés. **Nadie lo ejecuta en producción**: sigue **PENDIENTE**, pero
   ha dejado de ser imposible, que es lo que era.
5. **Un solo `docker`, una sola máquina.** Todo esto vale para un demonio local.
   Con `DOCKER_HOST` remoto o `docker context`, `docker kill <nombre>` va al
   demonio que diga el entorno, y ese entorno no lo fija FileX. **PENDIENTE.**
6. **Los motores NATIVOS siguen igual.** `_matar_arbol` ya declaraba que matar el
   árbol *«es lo mínimo, no la garantía»*. El a4 no toca eso.

---

## 5. La suite

| | Antes | Después |
|---|---|---|
| `python -m pytest pruebas/ -q` | 175 passed, 6 skipped, 1 failed | **182 passed, 6 skipped, 1 failed** |

**+7 pruebas, y el mismo único rojo.** Movimientos, uno a uno:

1. **+7 netas en `pruebas/test_cancelacion.py`** (13 → 20). Se quitan 2 y se
   añaden 9:
   - **Quitada** `test_la_entrada_readonly_no_identifica_al_contenedor`: afirmaba
     una propiedad de `_fuentes_de_montaje`, que ya no existe. **Lo que afirmaba
     sigue probado, y mejor**: `test_cancelar_una_conversion_NO_toca_el_contenedor_de_la_de_al_lado`
     lo comprueba con dos contenedores reales en vez de con una lista de cadenas.
   - **Reescrita** `test_un_motor_nativo_no_dispara_la_caza_de_contenedores`,
     que ahora cubre también `_barrer_contenedor_de`.
   - **Nuevas**: la orden declara el contenedor · cada invocación acuña un nombre
     distinto (50 de 50) · solo se acepta un nombre acuñado por FileX · el gancho
     `parar()` ya no está muerto · `parar()` sin contenedor en este hilo no hace
     nada · cancelar en el arranque no deja huérfano · el vecino sobrevive ·
     `parar()` para el contenedor cuando dispara el tope de fuera.
2. **El rojo esperado sigue siendo el mismo**,
   `test_sondeo.py::SelladoDelDisco::test_ningun_motor_disponible_tiene_el_sondeo_caducado`,
   y ahora nombra **más**: al `invocacion` de los cinco motores se le suma el
   **`motor`** de los tres documentales (`doc_libreoffice`, `doc_pandoc`,
   `doc_calibre`), porque `motor_contenedor.py` cambió. **Estaba previsto y
   aceptado por el encargo.** No se ha tocado `filex/huella.py`, ni el campo
   `huella` de ningún `filex/sondeo/*.json`, ni se ha resondeado.
3. **0 movimientos en el resto**, incluidas las 6 pruebas de `test_hito5.py` que
   indexan el `argv` de `_argv_docker`: todas lo hacen **relativas al nombre de
   la imagen** (`a[a.index("filex-c13") + 4]`), así que insertar `--name` antes
   de la imagen no las movió.

### Una prueba de otro fichero que **no** he arreglado

Ninguna. Pero sí hay un **arnés** ajeno roto, y lo digo aquí porque es el mismo
tipo de deuda:

> **`bench/salidas-cancelacion/arnes_cancelacion.py` (de N-a) ya no ejecuta sus
> bloques M3 y M5.** Llama a `invocacion._fuentes_de_montaje`, que este trabajo
> ha borrado. **No lo he tocado** —es de su reparto— y sus cifras siguen
> publicadas en `c34_medidas.json` y reproducidas aquí por la vía nueva (M1 y
> M2). Quien quiera revivirlo tiene que sustituir esas dos llamadas por
> `invocacion._nombre_contenedor_de`.

---

## 6. Censo de contenedores

`docker ps -a`, **antes y después de cada una de las cuatro tandas**:

```
filex-convertx           Up 40 hours
filex-snapotter          Up 40 hours (healthy)
filex-snapotter-pg       Up 40 hours (healthy)
filex-snapotter-redis    Up 40 hours (healthy)
filex-gotenberg8         Up 40 hours (healthy)
filex-gotenberg          Exited (255) 3 weeks ago
```

**6 antes, 6 después. Huérfanos con la forma `filex-<pid>-<uuid4>`: 0.**

Y un aviso sobre el propio censo, que costó una lectura falsa: **filtrar por el
prefijo `filex-` a secas no vale**, porque los cinco contenedores permanentes del
proyecto empiezan igual. La primera versión del arnés dio
`huerfanos_de_filex: ["filex-snapotter-redis"]`. El filtro correcto es la
expresión regular completa, que es la que acuña `nombre_de_contenedor()`.

---

## 7. Reproducción

```
python bench/salidas-contenedor/sonda_id.py            # S1-S5, ~2 min
python bench/salidas-contenedor/arnes_contenedor.py    # M1-M7, ~15 min
python -m pytest pruebas/test_cancelacion.py -q        # 20 pruebas, ~22 s
```

**Aviso, que se repite porque volvió a pasar:** un *worktree* nuevo trae
`corpus/` como **punteros de Git LFS** y eso hace fallar 15 pruebas por «el
motor rechazó la conversión», indistinguible de una regresión real.
`corpus/imagen/tipico.png` debe pesar **42 855 B**; si pesa 130, `git lfs
checkout` dentro del *worktree* lo arregla sin red.

---

## 8. Ficheros tocados

| Fichero | Qué |
|---|---|
| `filex/invocacion.py` | `nombre_de_contenedor`, `_nombre_contenedor_de`, `matar_contenedor`, `barrer_contenedor`, `_barrer_contenedor_de`, `_docker_ok`; **borradas** `_fuentes_de_montaje` y `_victimas` |
| `filex/motor_contenedor.py` | `--name` en `_argv_docker` y en `_sondear_binarios`, `_HILO`, `_EnContenedor.parar()` |
| `pruebas/test_cancelacion.py` | 13 → 20 pruebas |
| `bench/contenedor-parar.md` | este informe |
| `bench/salidas-contenedor/` | **nuevo**: sonda, arnés, dos JSON y `MANIFIESTO.md` |

**No se ha tocado** `filex/nucleo.py`, `filex/cerrojo.py`, `filex/motores.py`,
`filex/servicio.py`, `filex/mcp.py`, `filex/api.py`, `filex/watcher.py`,
`filex/huella.py`, `filex/sondeo.py`, `filex/sondeo/*.json`, `pruebas/test_hito5.py`,
`pruebas/test_sondeo.py`, `pruebas/test_cerrojo.py`, ningún documento maestro ni
ningún informe de `bench/` que no sea el mío.

> `filex/motores.py` estaba en mi reparto y **no ha hecho falta tocarlo**:
> `Motor.parar()` ya tenía la firma y la documentación correctas; lo que faltaba
> era una subclase que lo implementara.

---

## 9. Trampas propuestas — **NO APLICADAS**

Numeradas desde la 35 (N-b propuso la 33 y la 34). **No las he escrito en
`CLAUDE.md`.**

**35. `docker ps` NO ve todos los contenedores, y el que se le escapa es justo el
que deja huérfano — MEDIDO** (`bench/contenedor-parar.md` §1 S6, §2.4). El
cliente de `docker run` **crea** el contenedor y luego lo **arranca**; matar al
cliente entre las dos cosas deja un contenedor en estado `Created`, y sobre ese
estado —construido a propósito con `docker create`, sin carreras— las tres
respuestas son: **`docker ps` NO lo lista** (solo lista los que corren) mientras
`docker ps -a` sí; **`docker kill` FALLA** con `rc=1` y *«cannot kill container:
… is not running»*; y **`docker rm -f` sí lo borra**, `rc=0` en 120,3 ms. En la
ventana de cancelación aparece de forma intermitente: **1 de 9** en un brazo sin
defensas, 0 de 9 en otro. **Cuenta los huérfanos con `docker ps -a`, nunca con
`docker ps`, y mátalos con `docker rm -f`, no con `docker kill`.** Corolario de
diseño: **eso solo se puede hacer si la orden DECLARA el identificador** — cuando
el cliente muere, el desechable de R18 desaparece y con él el `.Mounts.Source`
del que se deducía, así que un contenedor `Created` sin `--name` es innombrable
e inmatable.

**36. Un arnés de carrera que espera al HILO mide la carrera equivocada, y sale
verde — MEDIDO** (ídem §3 M4). Esperar a que el hilo del trabajo arranque no es
esperar a que el `Popen` exista: cancelando en esa ventana, `cancelar_hilo`
devuelve `False` en **0,01 ms**, `ejecutar()` sale por la marca **sin lanzar el
proceso** y no llega a existir ningún contenedor. Salen **0 huérfanos de 9 que
no prueban nada**, y con la ventana correcta —esperando a `_EN_VUELO[ident]`—
el mismo régimen sin defensas da **9 huérfanos de 9**. Es la trampa 25 en
versión de arnés: **dos causas distintas con la misma pinta de éxito.**
**Registra si la condición que dices reproducir se dio** (`existia_al_cancelar`
en cada celda), no solo el resultado.

**37. Un `--cidfile` es un FICHERO, con todo lo que eso arrastra — MEDIDO**
(ídem §1, `sonda_id.json` S3). Tres cosas que la documentación no destaca y que
lo descartan como identificador de un contenedor que hay que matar: (a) **`--rm`
NO lo borra al salir**; (b) **Docker se niega a arrancar si el fichero ya
existe**, con `rc=125` y *«container ID file found»*, así que una limpieza que
falle deja el motor inservible; y (c) su sitio natural sería el directorio
desechable de R18, **que es justo el que se borra cuando muere el cliente** —el
mismo agravante ya medido, reaparecido en otro recurso—. Un `--name` único vive
DENTRO del `argv`, no tiene ciclo de vida, y **su unicidad la impone el
demonio**: un duplicado sale con `rc=125` y *«Conflict. The container name … is
already in use»*, es decir un error visible en vez de un atropello silencioso.

# Hito 7 — el watcher y la API HTTP, y la prueba de R10

**Agente H7 · 23 de agosto de 2026 · máquina de siempre (RTX 3060, Windows 10, Python 3.11.9)**

Entregado: `filex/watcher.py`, `filex/api.py`, `pruebas/test_hito7.py` (41 pruebas)
y un arreglo en `filex/nucleo.py` que sale de una refutación medida aquí.

**Estado de la suite:** antes `82 passed, 6 skipped` (88); después
`123 passed, 6 skipped` (129). **Las 88 anteriores intactas y en verde.**

> **Aviso de comparabilidad, y este informe lo necesita más que otros.** Las
> cifras absolutas de tandas distintas no son comparables. Aquí casi todo lo
> interesante es **relativo dentro de una tanda** (una configuración del watcher
> contra otra, una petición contra tres simultáneas) y así se presenta. Los dos
> números absolutos que se citan fuera de un cociente —el coste de construir
> `FileX` y el del cerrojo de destino— van con su salvedad. La sesión de
> escritorio remoto estaba activa: todo es `SUCIA` por construcción.

---

## 1. La pregunta del hito

> **La validación vive en el núcleo, no en la superficie** (R10,
> `RESULTADOS-MCP.md` §10). La CLI de `kordoc` lee ficheros fuera de
> `KORDOC_ROOT` con `exit=0` porque `safePath` vivía en su capa MCP.

Con dos superficies eso es una afirmación. Con cuatro se puede **probar**, y la
prueba no es «lo he escrito con cuidado»: es pasar **los mismos vectores por las
cuatro y exigir la misma respuesta**, más leer los cuatro ficheros y comprobar
que no contienen las piezas del confinamiento.

**Respuesta corta: R10 aguantó, y el hito además encontró un agujero que no es
de R10 y que solo se ve con concurrencia.** El detalle, por partes.

---

## 2. R10 con cuatro superficies — MEDIDO

### 2.1 Los mismos seis vectores por las cuatro (`CuatroSuperficies`)

Cada superficie se envuelve en un adaptador con la firma
`(entrada, salida) -> texto de la respuesta`, y se comparan **los textos**,
porque R4 es una regla sobre lo que el otro lado lee.

| Vector | Qué se exige | CLA | MCP | watcher | API |
|---|---|:--:|:--:|:--:|:--:|
| **V1** entrada fuera de la lista blanca | `ruta no accesible` | ✅ | ✅ | ✅ | ✅ |
| **V2** entrada dentro pero inexistente | **el MISMO texto que V1**, y los cuatro idénticos entre sí | ✅ | ✅ | ✅ | ✅ |
| **V3** nombre de salida reservado (`CON.webp`) | denegado (R12) | ✅ | ✅ | ✅ | ✅ |
| **V4** flujo alternativo (`v4:oculto.webp`) | denegado (R12/W9) y **nada escrito** | ✅ | ✅ | ✅ | ✅ |
| **V5** conversión legítima | sale bien **y el punto 5 llega cubierto** | ✅ | ✅ | ✅ | ✅ |
| **V6** el motor falla | **el `stderr` del motor no aparece** en la respuesta | ✅ | ✅ | ✅ | ✅ |

**24 de 24 celdas.** Y dos precisiones que hacen la prueba honesta:

- **V2 no compara «contiene el mensaje»: compara los cuatro motivos entre sí y
  exige un solo valor distinto.** Si alguna superficie llevara su propia copia
  del predicado tendría que coincidir carácter a carácter con el núcleo en los
  seis vectores, que es justo lo que no pasa cuando alguien duplica.
- **V4 tuvo que corregirse durante la escritura, y la corrección es la lección.**
  El vector original era `v4.webp:oculto`; con ese nombre la extensión pasa a
  ser `webp:oculto`, **no hay motor que la escriba y el rechazo lo daba el
  grafo, no R12**. Es un falso verde: la prueba pasaba sin llegar a la regla que
  decía probar. El vector bueno es `v4:oculto.webp` —fichero `v4`, flujo
  `oculto.webp`—, que conserva la extensión y llega hasta `nombre_seguro`.
  **Un vector que se para antes de la regla que quiere probar no prueba nada.**

### 2.2 Lo que NO puede haber en una superficie (`R10Estructural`)

Se leen los cuatro ficheros **sin comentarios ni cadenas** (por `tokenize`, no
por «la línea empieza por `#`»: en este proyecto las cadenas de documentación
explican precisamente las reglas que la prueba busca, y una prueba que se
dispara al DOCUMENTAR la regla castiga lo que hay que premiar).

| Comprobación | Resultado |
|---|---|
| Ninguna superficie nombra `realpath`, `nombre_seguro`, `MAX_COMPONENTES`, `MAX_LONGITUD`, `_RESERVADOS`, `_dentro`, `_lexico_ok` | ✅ 28 de 28 celdas |
| Ninguna superficie nombra `subprocess` ni `ejecutar` | ✅ 8 de 8 |
| `nombre_seguro(` se llama **exactamente** desde `confinamiento.py` y `nucleo.py` | ✅ |
| `filex/api.py` no llama a `FileX.convertir`: usa el `Servicio` de la capa MCP | ✅ |
| **`filex/api.py` no importa `os`** | ✅ |
| `filex/watcher.py` no nombra `contrato` ni `verificar` | ✅ |

La cuarta fila salió sola al pasar un detector de importes sin usar, y resume el
hito mejor que ninguna frase: **la superficie que recibe rutas por la red no
toca el módulo de rutas.** El watcher sí usa `os` —tiene que recorrer
directorios y derivar nombres—, pero tampoco decide con él.

La tercera es la regresión del fallo que el proyecto ya pagó: **`nombre_seguro`
estuvo escrito y probado desde el hito 1 sin un solo llamante fuera de su propia
prueba**, mientras FileX escribía 94 B en el flujo alternativo de un fichero
ajeno devolviendo `veredicto: ok`. La prueba de hoy fija la lista de llamantes:
si mañana alguien la quita de `nucleo.py`, o la copia a una superficie, salta.

### 2.3 La única superficie que tuvo que aportar lógica propia, y por qué no es R10

**La API HTTP.** Y la lógica que aporta no es de rutas: es de **protocolo**.

| Defensa | Qué evita | Medido |
|---|---|---|
| `Host` de loopback (o la dirección declarada, o una IP literal) | **DNS rebinding**: `malo.example` resuelto a 127.0.0.1 | `421` |
| `Origin` presente → rechazo | ninguna petición legítima viene de una página | `403` |
| `Content-Type: application/json` obligatorio en `POST` | **CSRF de formulario**: `x-www-form-urlencoded` es lo único que un `<form>` puede mandar sin *preflight*, y el *preflight* no se contesta | `415` |
| Tope de cuerpo (64 KiB) | `rfile.read(Content-Length)` es una reserva de memoria dictada por el cliente | `413` |
| `OPTIONS` → `405`, cero cabeceras CORS | que una página pueda **leer** la respuesta | `405`, sin `access-control-allow-origin` |
| Plazo de socket 30 s | una conexión abierta que no manda nada es una invocación sin tope con otro nombre | política |

**Ninguna de las seis mira el disco**, y esa es la línea: R10 habla del predicado
que decide si se puede tocar un fichero, y ese sigue viviendo en un solo sitio.
Las otras tres superficies no necesitan estas defensas porque no abren un puerto.

**Y hay que decir que el watcher SÍ llama al confinamiento, una vez, al
arrancar** (`Vigilante.comprobar_raices`): pide al núcleo que resuelva los
directorios vigilados y el de salida, para negarse a arrancar en vez de girar en
vacío denegando fichero a fichero. **Es una llamada al predicado, no una copia
del predicado** —el mismo patrón que `Servicio.inspect` en la capa MCP— y falla
con el mismo `Denegado` opaco. Comprobado por línea de órdenes:

```
$ python -m filex.watcher --vigilar C:/Users/krato --salida .../sal --destino webp --raiz .../humo
ruta no accesible
rc=2
```

### 2.4 Un hallazgo de arquitectura: `Servicio` no es de MCP

`filex/mcp.py` separó `Servicio` del protocolo «para poder probarlo sin levantar
un servidor». El hito 7 descubre para qué servía de verdad: **la API HTTP no
reimplementa nada; importa `Servicio` y `Trabajos` y se limita a parsear HTTP y
serializar JSON.** De ahí sale gratis el `job_id` al empezar (`202 Accepted`),
que es §5.2 del plan, y de ahí sale que las dos superficies no puedan divergir.

Lo mismo con `Trabajos`, cuyo docstring del hito 4 decía: *«un JSON por trabajo
sirve además a la CLI, al watcher y a la API: los cuatro frentes ven el mismo
trabajo»*. **No era retórica: hay una prueba que crea un trabajo desde el
watcher y lo lee desde la capa MCP con otro objeto `Trabajos` apuntando al mismo
directorio** (`test_el_trabajo_del_watcher_lo_ve_la_capa_mcp`).

> **PENDIENTE, y con nombre:** `Servicio` y `Trabajos` viven en `filex/mcp.py` y
> ya no son de MCP. Mover a `filex/servicio.py` con re-exportación desde
> `filex/mcp.py` no rompería `pruebas/test_hito4.py`, pero es el fichero de otro
> agente y no lo toco. **Lo dejo señalado, no hecho.**

---

## 3. El watcher: ¿cuándo está completo un fichero? — MEDIDO

### 3.1 El problema

El watcher ve el fichero **mientras se escribe**. Un escritor externo copia
`corpus/imagen/tipico.png` (42 855 B) en 20 trozos con pausas; el watcher sondea
cada 300 ms.

### 3.2 «¿Puedo leerlo?» NO es una prueba de completitud

Cuatro estados sobre el mismo fichero, en esta máquina:

| Estado | `os.replace(p, p)` | `open(p, 'rb')` |
|---|---|---|
| quieto | **OK** | OK |
| abierto en `'ab'` por **este** proceso | **FALLA** `PermissionError` WinError 32 | **OK** |
| abierto en `'ab'` por **otro** proceso | **FALLA** `PermissionError` WinError 32 | **OK** |
| el otro proceso ya cerró | **OK** | OK |

**Leer un fichero a medio escribir es perfectamente legal**, así que un watcher
que compruebe «¿lo puedo abrir?» no comprueba nada. El renombrado sobre sí mismo
sí, porque un fichero abierto sin `FILE_SHARE_DELETE` hace fallar `MoveFileEx`.

**En POSIX este cerrojo no existe** —un `rename` sobre un fichero abierto es
legal— y `_estable_en_disco` devuelve `True` ahí en vez de inventar una defensa.
**Medirlo en Linux está PENDIENTE**; en Linux el único cerrojo es la estabilidad
de `stat` (y, si se quisiera, `fcntl`/`/proc`, que es otra investigación).

### 3.3 Las tres configuraciones, sobre el mismo escritor

| Configuración | Conversiones | Tamaños vistos (de 42 855 B) | Veredictos |
|---|---:|---|---|
| **ingenua**: `estables=1`, sin cerrojo | **5** | 6 426 · 14 994 · 23 562 · 34 272 · **42 855** | 4 × `fallo`, 1 × ok |
| estabilidad sola: `estables=2`, sin cerrojo | **1** | 42 855 | ok |
| **defecto**: `estables=2` + cerrojo | **1** | 42 855 | ok |

Y el caso que separa las dos últimas: **un escritor que hace una pausa de 1,2 s
a mitad**, más larga que dos intervalos de sondeo, de modo que
`(tamaño, mtime_ns)` se queda quieto **con el fichero aún abierto**:

| Configuración | Conversiones | Tamaños vistos | ¿Escritor vivo al atender? |
|---|---:|---|---|
| `estables=2`, **sin** cerrojo | **2** | **23 562** (55 %) · 42 855 | **sí** la primera |
| `estables=2`, **con** cerrojo | **1** | 42 855 | no |

> **La estabilidad de `stat` sola NO basta, y el contraejemplo no es exótico:
> es un escritor que se para más de lo que dura el intervalo de sondeo.** Subir
> `estables` solo desplaza el umbral; el cerrojo cierra la clase entera.

**Lo bueno de la noticia:** las 5 conversiones incompletas del watcher ingenuo
dieron **`rc != 0` y veredicto `fallo`** — ImageMagick rechaza un PNG truncado.
No hubo ni un caso de «salida buena a partir de entrada a medias». **Pero eso es
una propiedad de este par (formato, motor), no una garantía**: un CSV o un WAV
truncados se convierten tan ricamente. **PENDIENTE**: repetir con un formato sin
suma de comprobación ni longitud declarada.

**Coste de la defensa:** `estables × intervalo` de latencia mínima. Con los
valores por defecto (2 × 1,0 s) son 2 s desde que el fichero deja de moverse.

### 3.4 Números que hay que leer con cuidado

`ms_hasta_primero` fue 2 928 / 5 118 / 4 179 / 3 856 / 4 286 ms en las cinco
configuraciones. **No los uso para nada**: dependen del escritor, del intervalo
y del momento en que arrancó el sondeo, y las tandas no son comparables entre
sí. Lo que sí es del experimento es la columna «tamaños vistos», que es una
propiedad discreta y reproducible.

---

## 4. El watcher: un fichero que aparece dos veces — MEDIDO

La identidad es `(ruta con normcase, tamaño, mtime_ns)`. No es un hash.

| Escenario | Atenciones nuevas | Resultado |
|---|---:|---|
| el mismo fichero quieto, **8 sondeos** | **1** | convertido |
| otros 8 sondeos después | **0** | — |
| **renombrado** `uno.png` → `dos.png` | **1** | **convertido** → `dos.webp` |
| **reescritura en sitio** (append de 8 B) | **1** | **`saltado`: el destino ya existe** |
| **`touch`** sin cambiar un byte | **1** | **`saltado`: el destino ya existe** |

Tres lecturas, y las tres son decisiones, no descuidos:

1. **El renombrado ES un fichero nuevo, y tiene que serlo:** su salida se llama
   `dos.webp` y nadie la ha escrito. La identidad lleva la ruta a propósito.
2. **La reescritura y el `touch` producen huella nueva —y deben— pero no pisan
   nada**, porque el destino ya existe y R9 dice *no sobrescribir en silencio*.
   **La huella detecta; R9 decide.** Son dos mecanismos y hacen falta los dos.
3. **El `touch` es el precio declarado de no hacer hash**, y el precio del hash
   está medido:

| Fichero | bytes | `os.stat` | `sha256` | veces |
|---|---:|---:|---:|---:|
| `corpus/imagen/tipico.png` | 42 855 | 0,0207 ms | 0,44 ms | **×21,1** |
| `corpus/imagen/patologico_16bit.tif` | 72 001 016 | 0,0164 ms | 382,85 ms | **×23 311,5** |

Hacer el hash **antes** de decidir si el fichero merece conversión significa
recorrer cada fichero entero en cada sondeo. Se paga un `touch` de más.

### 4.1 Y una colisión que destapó la primera prueba de humo

Una carpeta con `tipico.png` y `tipico.jpg` produce **dos veces `tipico.webp`**.
No se pierde nada —el segundo sale `saltado` con motivo— pero el usuario pidió
dos conversiones y obtiene una. Está fijado con prueba en las dos ramas, y hay
`--conservar-extension` (`tipico.png.webp`, feo y sin colisión). **El defecto
sigue siendo el nombre limpio**: la mayoría de las carpetas vigiladas no mezclan
formatos y un fallo ruidoso es mejor que un nombre que nadie reconoce.

### 4.2 Persistencia

Sin memoria en disco, reiniciar el watcher reconvierte la carpeta entera.
`--memoria fichero.json` lo evita, y hay prueba (`v1.paso()` → 1,
`v2.paso()` con el mismo fichero de memoria → 0).

---

## 5. La API: la primera superficie con concurrencia real — MEDIDO

### 5.1 Lo primero, un número que decide la arquitectura

| Operación | ms |
|---|---:|
| `FileX()` **en frío** (sondea los seis motores y el demonio de Docker) | **23 586** |
| `FileX()` **en caliente**, mismo proceso | **750** |

*(Absolutos, de una sola tanda, con la sesión remota activa: valen para el orden
de magnitud, no para comparar con nada de otro informe.)*

**Consecuencia:** el `FileX` se construye **una vez** y se comparte entre todas
las peticiones. Un servidor que lo construyera por petición tardaría más en
saber qué sabe hacer que en hacerlo.

### 5.2 Ocho conversiones simultáneas

| Tanda | Asas entregadas | Total | Ficheros | Sobrantes (punto 5) |
|---|---:|---:|---:|---:|
| 1 petición | 5,4 ms | 1 019 ms | 1 | 0 |
| 4 en paralelo | 28,7 ms | **643 ms** | 4 | 0 |
| 8 en paralelo | 69,6 ms | 693 ms | 8 | 0 |
| **4 en secuencia** (control) | — | **2 082 ms** | 4 | 0 |

- **×3,24** de 4 secuenciales a 4 en paralelo, con 12 núcleos. Relativo dentro
  de la misma tanda, que es lo único comparable.
- **El asa llega en 5–70 ms**, muy por debajo de los ~300 ms que tarda
  `png→webp`: §5.2 del plan se cumple, y hay prueba que exige `< 250 ms`.
- **R18 aguanta la concurrencia sin tocar nada**: el directorio desechable es un
  `mkdtemp` por conversión, así que **el censo del punto 5 no se contamina** —
  0 ficheros no declarados en las 8.

### 5.3 ⚠ El hallazgo del hito: **el contrato tiene un agujero que solo se ve con concurrencia**

Tres peticiones **simultáneas**, con **tres entradas distintas**, a **la misma
ruta de salida**:

| Petición | Estado | Veredicto | `bytes` declarados |
|---|---|---|---:|
| `tipico.png` (42 855 B) | `completed` | `ok_parcial` | **13 516** |
| `tipico.jpg` (87 954 B) | `completed` | `ok` | **14 402** |
| `patologico_16bit.tif` (72 MB) | `completed` | `ok` | **647 580** |

**En el disco: UN fichero de 647 580 B.** Las tres devolvieron éxito, las tres
declararon la misma `ruta_salida`, y **dos de las tres describieron un fichero
que ya no existe**.

**Y el contrato no puede atraparlo, ni es culpa suya:** juzga la salida **dentro
del directorio desechable**, que es privado de cada conversión; el atropello
ocurre después, en el `shutil.move` al destino. **El punto 5 mira el desechable;
al destino no lo miraba nadie.**

Es el fallo emblemático del sector visto desde dentro de FileX: `rc=0`, contrato
aprobado, y la salida que el cliente recibe **no es la que se le describe**.

#### El arreglo va en el NÚCLEO, y eso es R10 funcionando

`filex/nucleo.py` gana un conjunto de destinos en curso con su cerrojo. Se
reserva **después** de saber que hay camino y se suelta en el `finally`.

- **Lo encontró la cuarta superficie y el remedio no vive en ella.** La CLA, MCP
  y el watcher tenían exactamente el mismo agujero; se cierra una vez.
- **Después del arreglo, la misma prueba:** 1 éxito, 2 rechazos con motivo
  explícito (`otra conversión está escribiendo ya esa ruta de salida`), 1 fichero
  en el destino y **los bytes declarados por el éxito coinciden con el disco**.
  Reproducido dos veces con ganador distinto: **el ganador no es determinista;
  el invariante sí.**
- **Coste:** `reservar + soltar` = **3,2 µs** de mediana (p90 4,6 µs) sobre
  n = 20 000. Frente a una conversión de ~250 ms es el **0,0013 %**.
- **El motivo NO es opaco, a propósito.** El cliente **pidió** esa ruta, así que
  nombrarla no le dice nada que no supiera; R4 protege del oráculo sobre el disco
  ajeno, no de repetir lo que el propio cliente escribió.

> **ALCANCE DECLARADO, sin adornos: es un cerrojo DE PROCESO.** Una API y un
> watcher en **procesos distintos** siguen pudiendo pisarse. Cerrarlo entre
> procesos necesita un fichero de cerrojo o un mutex con nombre — el mismo
> problema que `gpu_acquire` de `bench/`, que también es de proyecto y no de
> máquina. **PENDIENTE.**

### 5.4 El lock de GPU

**No hay lock de GPU en `filex/`, ni uso de GPU** — las únicas apariciones de
`gpu`/`nvenc`/`cuda` en el paquete son **tres comentarios** (dos citando
`av1_nvenc` como ejemplo de «sondear, no deducir» y uno que escribí yo en §5.3).
Hoy ningún motor del grafo usa la tarjeta (ImageMagick, Ghostscript,
ffmpeg sin NVENC, y los tres motores documentales en contenedor), así que la
concurrencia no puede romper lo que no existe. **Cuando entren NVENC (hito 2) y
el sidecar de OCR (hito 6), la API es exactamente la superficie que va a
descubrir que falta.** PENDIENTE, y anotado aquí para que no sorprenda.

### 5.5 Ruta y metadatos, nunca contenido

| Respuesta | bytes |
|---|---:|
| `POST /convertir` → `202` con el asa | **121** |
| `GET /trabajos/{id}?accion=resultado` | **278** |
| `GET /inspeccionar?ruta=…` | **280** |
| *(el fichero convertido)* | *13 516* |

**×111 y ×48** a favor del asa, sin subir un solo byte del fichero. La API **no
acepta bytes**: no hay `multipart`, no hay base64, no hay subida. Se mandan y se
devuelven rutas, igual que en MCP, y por el mismo criterio: **tokens de
respuesta, no tipos del protocolo**.

---

## 6. La API expuesta a la red — MEDIDO

### 6.1 Por qué `127.0.0.1` por defecto

| Escucha en | Desde 127.0.0.1 | Desde la LAN (192.168.1.107) |
|---|---|---|
| `127.0.0.1` | `200` | **`ConnectionRefusedError` (WinError 10061)** |
| `0.0.0.0` | `200` | **`200`** |

**Esta API no autentica a nadie.** La lista blanca de raíces protege el disco;
no decide quién pregunta. Escuchando en `0.0.0.0`, cualquiera que llegue al
puerto puede convertir dentro de las raíces permitidas. Por eso `--host` no
loopback **exige además `--permitir-red`**, y aun así avisa:

```
$ python -m filex.api --host 0.0.0.0 --puerto 8795
me niego a escuchar fuera de 127.0.0.1 sin --permitir-red: esta API no autentica a nadie
rc=2
```

### 6.2 Y una autocorrección: las dos defensas se anulaban entre sí

Primera versión: el cerrojo anti-*rebinding* exigía `Host` de loopback **siempre**.
Con eso, `--permitir-red` **no servía para nada**: una petición legítima desde la
LAN llega con `Host: 192.168.1.107` y se rechazaba.

Segunda versión: admitir además la dirección declarada al arrancar. Con
`--host 0.0.0.0` no hay «la» dirección, así que admitía cualquier cosa —y
**medido, `Host: malo.example` respondía `200`**: el cerrojo entero desactivado
por escribir `0.0.0.0`.

Tercera y vigente: se admite loopback, la dirección declarada, **o una IP
literal**. El *rebinding* necesita un **nombre** —el ataque es que
`malo.example` resuelva a esta máquina—, así que con una IP no hay nada que
rebindear. Medido con el servidor en `0.0.0.0` y petición desde la LAN:

| Petición | Antes | Ahora |
|---|---|---|
| `Host: 192.168.1.107` | 200 | **200** |
| `Host: malo.example` | **200** ⚠ | **421** |

**Dos defensas que se anulan entre sí no son dos defensas.** Solo se vio al
medirlas juntas.

---

## 7. Lo que quedó refutado, y lo que queda pendiente

### 7.1 Refutado

1. **~~«El contrato de cinco puntos cubre lo que el motor escribe»~~.** Cubre lo
   que escribe **en el desechable**. Con dos conversiones simultáneas al mismo
   destino, **tres respuestas `ok` y un solo fichero** (§5.3). Arreglado en el
   núcleo, y el arreglo es de proceso, no de máquina.
2. **~~«Con estabilidad de `stat` basta para saber que un fichero está
   completo»~~.** Un escritor que se para más que el intervalo de sondeo la
   engaña, y el watcher convierte el 55 % de un PNG (§3.3).
3. **~~«Si puedo abrirlo para leer, está completo»~~.** `open(p,'rb')` funciona
   en los cuatro estados, incluido «otro proceso lo tiene abierto escribiendo»
   (§3.2).
4. **~~«El `Host` de loopback y `--permitir-red` son dos defensas
   independientes»~~.** Se anulaban entre sí en las dos primeras versiones
   (§6.2).

### 7.2 Y una tensión entre dos reglas del propio proyecto — MEDIDO, sin arreglar

`confinamiento.py` marca como PENDIENTE que R4 exige *«la misma latencia»* para
«prohibido» y «no existe». **Ahora hay número**, medido en el núcleo, n = 2 000
por celda:

| Caso | mediana | p90 |
|---|---:|---:|
| **prohibido** (fuera de la lista blanca) | **9,4 µs** | 11,3 µs |
| dentro pero **no existe** | **193,3 µs** | 385,2 µs |
| dentro y **existe** | 150,3 µs | 321,6 µs |

**El prohibido es ×20,6 MÁS RÁPIDO**, y la causa es **R1**: el predicado léxico
corta antes de tocar el disco, así que el caso denegado nunca paga el
`realpath`. **Cumplir R1 es exactamente lo que crea el oráculo temporal que R4
prohíbe.** No son compatibles sin un retardo artificial.

Por HTTP el cociente se diluye —**1,913 ms frente a 2,630 ms** de mediana, ×1,37,
n = 30 intercalados— porque el coste de la conexión TCP domina; **pero no
desaparece y va en la dirección que le sirve al atacante**. El mensaje y el
código son idénticos (`404`, 30 B, `{"error": "ruta no accesible"}`): lo que
distingue es el reloj.

> **Propuesta, sin implementar:** igualar por abajo es imposible (hay que tocar
> el disco para saber si existe); igualar por arriba significa dormir ~200 µs en
> el camino denegado, lo que convierte el rechazo en un amplificador de DoS
> barato. **Lo honesto es medirlo, decirlo, y decidir por superficie**: en la
> CLA no hay atacante que cronometre; en la API sí. **PENDIENTE.**

### 7.3 Pendientes nombrados

| Qué | Por qué importa |
|---|---|
| El cerrojo de destino es **de proceso**, no de máquina | Una API y un watcher en procesos distintos siguen pisándose |
| El oráculo temporal de R4 (§7.2) | R1 y R4 en tensión, con número |
| `_estable_en_disco` **en POSIX** | Ahí devuelve `True` y el único cerrojo es `stat` |
| «Fichero incompleto» con un formato **sin suma de comprobación** (CSV, WAV) | Aquí los 5 truncados dieron `fallo` **porque PNG lo detecta** |
| Mover `Servicio`/`Trabajos` a `filex/servicio.py` | Ya no son de MCP; los usan tres superficies |
| El **lock de GPU** no existe en `filex/` | Cuando entren NVENC y el sidecar, la API lo va a descubrir |
| `job cancelar` sigue sin matar el árbol | Heredado del hito 4, y ahora lo ve también la API |

---

## 8. Reproducir

```
# la suite entera (129 pruebas)
python -m pytest pruebas/ -q

# solo el hito 7 (41 pruebas, ~17 s con el sondeo en caliente)
python -m pytest pruebas/test_hito7.py -q

# el watcher, de verdad
python -m filex.watcher --vigilar D:/entrada --salida D:/salida --destino webp \
                        --raiz D:/entrada --raiz D:/salida --ciclos 4

# la API, de verdad
python -m filex.api --raiz D:/Work/research/FileX
curl http://127.0.0.1:8756/salud
```

Las mediciones de §3, §4, §5 y §6 salen de tres arneses de un solo uso que
viven fuera del repositorio (directorio temporal del agente) porque `bench/` no
es mío en este hito salvo este fichero. **Lo que sí está versionado y ejecuta
las mismas comprobaciones es `pruebas/test_hito7.py`**: las 41 pruebas incluyen
la configuración ingenua contra la de defecto (§3.3), los cinco escenarios de
duplicado (§4), la tanda de 8 simultáneas y la carrera por el mismo destino
(§5), y las seis defensas de protocolo (§6). Los tres arneses solo añaden los
**números** —medianas, tamaños, microsegundos—, que son los que están en las
tablas de arriba.

---

## 9. Los marcadores de hito que faltaban

`PLAN-ORQUESTADOR.md` §7 solo tenía marcado el hito 1. **Marcados el 23/08, con
la evidencia delante y sin dar por hecho nada:**

| Hito | Marcado | Evidencia | Salvedad que se escribió al marcarlo |
|---|---|---|---|
| **3** — contrato de verificación | HECHO 22/08 | `filex/verificador.py` (5 241 líneas, biblioteca estándar), `filex/contrato.py`, `bench/hito3-mudanza.md` (K2) | el patrón oro sigue sin **una sola salida multifichero**, así que es un test flojo para el punto 5 |
| **4** — capa MCP | HECHO 22/08 | `filex/mcp.py`, `pruebas/test_hito4.py`, `bench/hito4-mcp.md` (K3) | **dos criterios de aceptación incumplidos y medidos**: el catálogo son 1.503 tokens (≤1.200 pedidos) y **la latencia de R4 no es equivalente** (§7.2, medido en este hito) |
| **5** — ofimática en contenedor | HECHO 22/08 | `filex/motor_contenedor.py`, `pruebas/test_hito5.py`, `bench/hito5-documental.md` (K1) | **el título del hito quedó desmentido por su propio informe**: la vía no es Gotenberg sino `filex-c13` |
| **7** — watcher y API | HECHO 23/08 | este informe | el cerrojo de destino es **de proceso**, no de máquina |

**Los hitos 2 (NVENC) y 6 (sidecar de IA) NO se marcan**: no hay código suyo en
`filex/` y no me consta que estén hechos.

**Y una nota sobre marcar un hito con criterios incumplidos.** El hito 4 se marca
HECHO **y** se escribe en el plan que dos de sus criterios no se cumplen, con los
números. Marcarlo sin decirlo sería mentir; no marcarlo sería tirar el trabajo
hecho. En los dos casos el problema está en el criterio, no en el código: el de
los 1.200 tokens choca con las dos reglas de cobertura que evitan un 15–17 % de
fallos silenciosos, y el de la latencia choca con R1.

---

## 10. Propuesta para `CLAUDE.md` (no aplicada — va AL FINAL, nunca en medio)

> **APLICADAS el 23/08 por el orquestador, como las trampas 26, 27 y 28.**
> G4 propuso a la vez otras dos con los números 26 y 27; las suyas quedaron
> como 29 y 30. El texto es el de abajo; solo cambia el número de cabecera.

> **26. Dos peticiones simultáneas a la MISMA ruta de salida devolvían las dos
> `ok` — MEDIDO** (`bench/hito7-superficies.md` §5.3). Tres conversiones a la vez
> con tres entradas distintas y un solo destino: **tres `completed`, tres
> `veredicto` aprobado, tres tamaños distintos declarados (13 516 / 14 402 /
> 647 580 B) y UN fichero en el disco**. **El contrato no puede verlo**: juzga la
> salida dentro del directorio desechable de R18, que es privado, y el atropello
> ocurre en el `move` al destino. **El punto 5 mira el desechable; al destino no
> lo miraba nadie.** Cerrado con un conjunto de destinos en curso en
> `filex/nucleo.py` (3,2 µs, 0,0013 % de una conversión), **de proceso, no de
> máquina**: dos procesos `filex` siguen pisándose y eso sigue PENDIENTE.
>
> **27. «Si puedo abrirlo, está completo» es FALSO, y la estabilidad de `stat`
> sola tampoco basta — MEDIDO** (ídem §3.2, §3.3). `open(p,'rb')` funciona
> aunque otro proceso tenga el fichero abierto escribiendo; `os.replace(p, p)`
> falla con WinError 32 justo en ese caso y es el único cerrojo real en Windows.
> Y con un escritor que se para más que el intervalo de sondeo, `(tamaño,
> mtime_ns)` se queda quieto **con el fichero abierto**: el watcher convirtió el
> **55 %** de un PNG. **Estabilidad + cerrojo; ninguno de los dos por su cuenta.**
>
> **28. R1 y R4 están en tensión, y ahora hay número — MEDIDO** (ídem §7.2).
> Denegar por lista blanca cuesta **9,4 µs** y «existe pero no» cuesta
> **193,3 µs**: **×20,6**, porque el predicado léxico de R1 corta antes del
> `realpath`. El mensaje y el código son idénticos; **lo que distingue es el
> reloj**. Igualar por arriba convierte el rechazo en un amplificador de DoS.
> **Se decide por superficie, y se dice.**

# Cobertura de las cuatro superficies: once funciones que nunca se habían llamado

Carril `cob/superficies`. Sujeto: `filex/cli.py`, `filex/__main__.py`,
`filex/api.py` y `filex/watcher.py` — las cuatro superficies de usuario, y las
únicas cuatro que un tercero toca.

**Entrega:** `pruebas/test_cob_superficies.py` (77 pruebas),
`bench/salidas-cobertura-superficies/` (datos, arneses y `MANIFIESTO.md`).
**No se ha tocado `filex/`**: los tres defectos encontrados van con su caso
mínimo y sin parche.

---

## 0. El titular, y por qué no es un porcentaje

**MEDIDO: once funciones y un módulo entero pasan de NUNCA HABERSE EJECUTADO a
ejecutarse enteras.** Ésa es la cifra que dice algo; el porcentaje es
consecuencia.

| Módulo | Función | Estado antes |
|---|---|---|
| `__main__.py` | *el módulo entero* | **0 de 3 sentencias**: ninguna prueba invocaba `python -m filex` |
| `watcher.py` | `informar` | **0 de 4** |
| `cli.py` | `_fmt_ms`, `_inventario`, `_destinos`, `_plan` | sólo la línea del `def` |
| `api.py` | `_es_ip_literal` | sólo la línea del `def` |
| `watcher.py` | `main`, `correr`, `_linea`, `__len__` | sólo la línea del `def` |

*«Sólo la línea del `def`»* es lo que mide `coverage` cuando una función se
define al importar el módulo y **no se llama nunca**: `cli._plan` tenía 1 de 17
sentencias, `watcher.main` 1 de 45, `cli._inventario` 1 de 15. En números
redondos: **cuatro de los cinco subcomandos de la CLI (`motores`, `destinos`,
`plan`, y la mitad humana de `convertir`) y el `main` del watcher entero no se
habían ejecutado nunca en la suite.**

Y hay una segunda mitad que sí es un porcentaje, con su métrica declarada
(trampa 55) — **es la COMBINADA de coverage, sentencias más ramas**, que es la
que trae la medida base del maestro:

| Módulo | Antes | Después (unión) | Sentencias ganadas | Ramas ganadas |
|---|---|---|---|---|
| `filex/__main__.py` | **0,0 %** | **100,0 %** | 3 de 3 | 2 de 2 |
| `filex/cli.py` | **35,2 %** | **100,0 %** | 81 de 81 | 44 de 44 |
| `filex/watcher.py` | **58,9 %** | **100,0 %** | 129 de 129 | 41 de 41 |
| `filex/api.py` | **65,3 %** | **100,0 %** | 66 de 66 | 28 de 28 |
| **total** | | | **279** | **115** |

**279 de 279.** No queda ni una sentencia ni una rama sin ejecutar en los
cuatro ficheros. *(Y las ramas están ahí porque publicar sólo las sentencias
habría sido publicar media medida: `cli.py` tenía el **42,6 %** de sentencias y
el **15,4 %** de ramas, y el 35,2 % del que se partía es la mezcla de las dos.)*

---

## 1. La base, y cómo se calcula el delta sin reejecutar la suite

La base la midió el maestro el 04/09 sobre la suite entera (517 pruebas), con
`coverage` 7.16.0 y `--branch`:

```
filex\__main__.py     3 sentencias +  2 ramas    0,0 %
filex\cli.py        141 sentencias + 52 ramas   35,2 %
filex\watcher.py    328 sentencias + 86 ramas   58,9 %
filex\api.py        205 sentencias + 66 ramas   65,3 %
```

**Este carril no puede reejecutar la suite entera** —hay cinco agentes más en
la máquina, y seis suites a la vez fabrican la carga que pone roja
`test_cancelacion_procesos` sin que nadie toque el código (trampas 101 y 123)—.
Así que el delta se calcula por intersección:

    ganadas = (sin ejecutar en la base) ∩ (ejecutadas por este módulo solo)

**Es exacto, no una estimación**: la cobertura es monótona bajo la unión de
ejecuciones, así que una línea que la base no tenía y este módulo sí ejecuta
está ejecutada en la unión. Lo que este cálculo **no** puede decir es cuánto se
mueve el resto de `filex/`, y por eso el informe no publica ni una cifra de los
otros dieciocho ficheros.

Y un dato que el maestro dejó dicho y **no hacía falta volver a comprobar**:
midió la base **dos veces**, la segunda instrumentando los procesos hijo (27
capturados), y `cli.py` no se movió de 35,2 % ni `__main__.py` de 0,0 %. *La
CLI no estaba sin cobertura porque se probara en un proceso hijo; estaba sin
cobertura.* Este carril lo confirma por el otro lado: **no lanza ni un proceso
hijo** — los cuatro puntos de entrada se ejecutan en proceso con
`runpy.run_module(..., run_name="__main__")`, que corre el mismo fichero con el
mismo nombre de módulo que `python -m`.

---

## 2. Lo que se ejecuta, por módulo

### 2.1 `filex/__main__.py` — de 0,0 % a 100 %

Tres sentencias y dos ramas. Las dos ramas son las dos mitades del
`if __name__ == "__main__"`, y **las dos importan**:

* **La verdadera** (`python -m filex`): `runpy.run_module("filex",
  run_name="__main__")` con `sys.argv = ["filex"]` imprime la ayuda y sale con
  `SystemExit(0)`. Se eligió ese argumento porque **vuelve antes de construir
  un `FileX`**: el objetivo de la prueba es la línea `raise SystemExit(main())`,
  no el sondeo de motores.
* **La falsa** (`import filex.__main__`): tiene que ser **inerte**. Un punto de
  entrada que hiciera algo al importarse convertiría cualquier herramienta que
  recorra el paquete —un `pydoc`, un `pkgutil.walk_packages`— en un lanzador de
  la CLI. La prueba comprueba que no se escribe nada en `stdout` ni en
  `stderr`.

Los otros tres `if __name__ == "__main__"` (`cli.py:262`, `api.py:436`,
`watcher.py:734`) se ejecutan igual, cada uno con los argumentos que vuelven
antes de tocar un motor: `--host 203.0.113.9` para la API (`rc=2`, se niega a
salir de loopback) y `--params {roto` para el watcher (`rc=2`).

### 2.2 `filex/cli.py` — de 35,2 % a 100 %

Lo que faltaba era **casi todo el producto de la CLI**: `_inventario`,
`_destinos`, `_plan` y la mitad humana de `_convertir`. La rama JSON de
`convertir` sí estaba cubierta, y por eso el fichero no salía peor.

Se prueban las tres decisiones que la CLI toma y que nadie estaba comprobando:

* **Los tres códigos de salida son un contrato para terceros** y se separan:
  `2` es error de USO (`--params` que no es JSON, `--params` que es JSON pero
  no un objeto, formato desconocido en `destinos`, `--raiz` que no confina),
  `1` es fallo de NEGOCIO (sin camino, sin destinos alcanzables, conversión
  rechazada) y `0` incluye la ayuda.
* **`--params null` NO se rechaza**, y es la excepción que confirma la regla:
  `None` cae en `pedido or {}` del núcleo. Está en el comentario del código y
  ahora también en una prueba.
* **El `stderr` del motor sólo cruza con `-v`**, y los descartes que «enseñan
  algo» (rasteriza / pierde) se enseñan siempre.

### 2.3 `filex/watcher.py` — de 58,9 % a 100 %

Los dos bloques grandes eran `main` (44 sentencias) y `_tenedores_posix` (33).

**`main` se prueba de extremo a extremo**, con `magick` de verdad y el tope
DENTRO de la orden (`--ciclos 1`): una carpeta con `tipico.png`, un ciclo, y el
`.webp` en el disco con `punto5=` en la línea. No hay proceso hijo que matar
después —y eso no es comodidad: matar por `Popen.pid` en Windows no alcanza a
quien uno cree, porque el `python.exe` de un venv es un lanzador (trampa 93)—.
Se cubren además `--json`, `--conservar-extension`, `--memoria`, la entrada
rota (`[fallido]`), el `Denegado` de `comprobar_raices` (`rc=2` con mensaje
opaco), el aviso de «sin lista blanca» y el `KeyboardInterrupt`.

**`_tenedores_posix` es de POSIX y esto es Windows.** No se marca `no_aplica`:
se ejecuta contra un **`/proc` simulado**. `os.listdir` y `os.stat` se desvían
sólo para las rutas que empiezan por `/proc` y delegan en el disco real para
todo lo demás; los descriptores de los procesos ficticios son **enlaces duros
de verdad**, así que la coincidencia por `(st_dev, st_ino)` —que es el
algoritmo entero— **no está simulada: se mide**. Se cubren los cinco caminos:
el tenedor encontrado, el proceso que no lo tiene, el `/proc/<pid>/fd`
ilegible (otro usuario), el `fd` que muere entre el listado y el `stat`, y el
propio PID, que **no debe mirarse** —el doble lanza `AssertionError` si se
mira—. Y las tres respuestas que no son una lista: sin `/proc`, sin fichero, y
sin identidad de inodo, las tres `None` («no se pudo saber»), que es lo que la
trampa 43 exige separar de `[]` («no lo tiene nadie»).

Lo declarado y honesto: **esto no sustituye a la medida en Linux de
`bench/watcher-y-desechables.md` §1**. Prueba el algoritmo, no la plataforma.

### 2.4 `filex/api.py` — de 65,3 % a 100 %

Faltaban las defensas de protocolo que ningún cliente educado dispara y todo el
`main`.

* **`main` se arranca y se para de verdad**, sin tope alrededor: se corre en un
  hilo, se captura el servidor por el mismo sitio por el que `main` lo
  construye y se le pide `shutdown()`. El `KeyboardInterrupt` se inyecta
  sustituyendo `threading` en el módulo por un `Thread` que arranca de verdad y
  cuyo `join` interrumpe — **el `shutdown()` de después necesita un
  `serve_forever` VIVO**, o se quedaría esperando su propio evento para
  siempre.
* **No se abre ni un puerto fuera de loopback.** El aviso de `--permitir-red`
  se comprueba haciendo que `construir` reviente: si el aviso estuviera después
  del `construir`, no se vería. Y todos los servidores usan **puerto 0**: lo
  asigna el sistema. Un puerto fijo chocaría con otro carril y el fallo
  parecería del producto.
* **`_host_admitido` se prueba sin socket**, sobre el atributo `host_declarado`
  que es exactamente lo que `main` le pone: las dos defensas que *«se anulaban
  entre sí»* (§6.2 del hito 7) y el caso `0.0.0.0`, donde pasa una IP literal y
  se rechaza todo nombre.
* **`_responder`, `_rechazo` y `_cuerpo` se prueban con un manejador sin
  socket** (`_ManejadorDeBanco`): `BaseHTTPRequestHandler.__init__` atiende la
  petición dentro del propio constructor, así que no hay forma de instanciarlo
  para inspeccionarlo. Se sustituye el constructor y las tres llamadas de
  cabecera; **los tres métodos bajo prueba son los de producción**.

---

## 3. Tres defectos, con su caso mínimo

Ninguno se parchea: esta ronda no toca `filex/`.

### 3.1 `api.py`: el cuerpo se lee DOS VECES, y la segunda se queda esperando

**MEDIDO.** `_cuerpo()` consume el cuerpo del `POST` y, cuando el JSON no vale,
llama a `_rechazo()`, **que vuelve a leerlo**. `_rechazo` descarta el cuerpo a
propósito —con `keep-alive`, rechazar sin consumirlo deja bytes en el socket y
la petición siguiente se lee sobre la mitad de la anterior, MEDIDO como
`WinError 10053` en la primera pasada del hito 7— pero cuando quien llama es
`_cuerpo`, **ya no queda nada que leer**: el segundo `rfile.read(n)` se bloquea
hasta que salta el plazo del socket, `TIMEOUT_SOCKET = 30 s`.

Alcance, medido: pasa en los **tres** caminos en que `do_POST` rechaza DESPUÉS
de `_cuerpo` —cuerpo que no es JSON, cuerpo que no es un objeto, y `POST` a una
ruta desconocida— y **no** pasa en los que rechazan antes (`415`, `413`, `421`,
`403`), que son justo los que la suite ya tenía. Por eso llevaba ahí sin que
nadie lo viera: **las cuatro defensas probadas eran las cuatro que no lo
disparan**.

El mecanismo está aislado sin socket y sin plazo, contando las llamadas a
`read`: **`[5, 5]` — dos lecturas de cinco bytes, y la segunda no tiene nada
que leer.**

Consecuencia: con `ThreadingHTTPServer` cada petición ocupa un hilo, así que un
cliente **sin autenticar** retiene un hilo **30 segundos con 5 bytes**. La API
escucha en loopback por defecto, así que no es una brecha; es un amplificador
barato para quien ya esté en la máquina, y una espera de 30 s para un cliente
legítimo que mande un JSON mal formado.

El remedio evidente —que no se aplica aquí— es que `_cuerpo` marque el cuerpo
como consumido antes de rechazar.

*(Cómo se descubrió, porque importa: la primera versión de las pruebas de
encaminado **se colgó**, y el `TimeoutError` de `urllib` se leía como un fallo
del arnés. Lo separó mirar qué caminos sí respondían.)*

### 3.2 `cli.py`: el VALOR de una bandera cuenta como posicional

**MEDIDO, dos síntomas y una sola causa.** La forma corta —`filex a.png
b.webp`— se detecta **antes** de `parse_args`, con:

```python
resto = [a for a in argv if not a.startswith("-")]
if resto and resto[0] not in _ORDENES and len(resto) == 2:
    argv = ["convertir", *argv]
```

Ese filtro quita las **banderas** pero no sus **valores**. Entonces:

a. **`filex --raiz D a.png b.webp`** da `resto` de 3 elementos, la forma corta
   **no** se activa, argparse ve `a.png` donde espera un subcomando y aborta
   con `SystemExit(2)`. Es decir: **la forma corta y el confinamiento son
   incompatibles**, y el confinamiento es justo lo que escribiría un usuario
   prudente. Con `convertir` explícito, la misma orden funciona.
b. **`filex --raiz D motores`** da `resto == ["D", "motores"]`, que **sí** mide
   2, así que la forma corta se activa **por error** y la orden se reescribe a
   `convertir --raiz D motores`: el subcomando del usuario se convierte en el
   primer posicional de otro, y el error que sale nombra a `convertir`.

El docstring de `main` ya documenta un *«hallazgo sin corregir»* sobre los
códigos de salida; éste es otro, y de la misma función.

### 3.3 `watcher.py`: el `os.makedirs` de `main` es redundante en el camino normal

**MEDIDO, y es una refutación de mi propia primera prueba.** Escribí una prueba
que comprobaba que el directorio de salida existía **después** de convertir, y
el control de discriminación la tumbó: **pasa igual con el `os.makedirs`
borrado**, porque lo crea el núcleo al mover la salida. Aquella aserción no
medía la línea que decía medir (trampa 116).

Lo que la línea sí garantiza —y **sólo se ve con la carpeta vigilada VACÍA**—
es que un watcher arrancado antes de que llegue el primer fichero deja el
destino listo. La prueba se reescribió así y ahora discrimina. No es un defecto
del producto: es un defecto de mi prueba, y el mecanismo que lo encontró es el
mismo que justifica todo el §4.

---

## 4. El control que hace que esto valga algo

**La cobertura es la única métrica de este proyecto que se puede subir sin
medir nada.** Un `try: main([...]) except SystemExit: pass` sube el porcentaje
de un `main()` entero y no afirma nada — y en un carril de puntos de entrada es
la tentación número uno.

Por eso cada prueba tiene un control: **se rompe UNA línea del módulo objetivo
y se comprueba que la prueba se pone ROJA.**

**MEDIDO: 72 mutaciones, 72 discriminan.** La tabla completa, con el módulo, la
prueba, qué rompe cada mutación y el `rc` observado, está en
`bench/salidas-cobertura-superficies/discriminacion.json`; el arnés que la
produce, en `discriminacion.py`.

Cómo evita las trampas que este proyecto ya pagó:

* **Restaura con `git checkout -- filex/<modulo>.py`, nunca con `git stash
  push`** (trampa 119: sobre un fichero ya commiteado no hace nada, devuelve 0
  y no avisa, y el arnés acaba comparando el código nuevo contra sí mismo).
* **Exige que la mutación sea ÚNICA en el fichero.** Si el texto aparece 0 o 2
  veces, la fila sale `MUTACION_NO_UNICA` en vez de contarse como buena — y
  ocurrió: una mutación de `_tenedores_posix` tenía la indentación mal y daba
  **0 ocurrencias**, es decir *«la prueba no se puso roja»* por no haber
  mutado nada.
* **Registra que la condición se dio** (trampa 38): comprueba que la mutación
  está en el disco, que el árbol está sucio **durante**, y que vuelve a estar
  limpio **después**. Una fila sólo cuenta si las tres son ciertas.

Dos pruebas se reescribieron porque el control las tumbó, y las dos habrían
pasado con el arreglo y sin él:

1. **La del IPv6** capturaba el `OSError` de `construir` y hacía `skipTest`.
   Quitando la línea `self.address_family = socket.AF_INET6`, el `bind` a `::1`
   falla… y la prueba **se saltaba**, que no es rojo. Ahora la disponibilidad
   de IPv6 se sondea **antes**, con un `bind` propio, y el `skipUnless` va en
   la clase: si la línea desaparece, la prueba se pone roja.
2. **La del sistema de ficheros sin `st_ino`** se medía sin el `/proc`
   simulado, así que devolvía `None` con el guarda y sin él. Ahora se mide con
   el `/proc` delante: sin el guarda devuelve `[4242]`.

Y un tercer caso, el §3.3, ya contado.

**`filex/` queda limpio**: `git status --porcelain -- filex/` vacío después de
las 72.

---

## 5. Lo que NO se cubre, y por qué — declarado

### 5.1 Ramas que esta máquina no puede producir, alimentadas a mano

Tres ramas del código no las produce **ningún** par (origen, destino) con los
seis motores de esta máquina. Se ejecutan construyendo la entrada con las
**dataclases reales del núcleo** (`nucleo.Conversion`, `nucleo.Salto`,
`grafo.Arista`, `grafo.Camino`, `grafo.Decision`) — nunca un duplicado del
tipo, siempre el tipo:

| Rama | Por qué no sale sola | MEDIDO |
|---|---|---|
| `_plan`: el `AVISO` de rasterización | ningún plan lleva `aviso` | **0 de 1 122 pares** (34 orígenes × 33 destinos), `explorar3.py` |
| `_convertir`: `conv.aviso` y los ficheros `sobrantes` | ninguna arista deja sobrantes; **`mpd` no está entre los destinos de `mp4`** | `explorar3.py` |
| `_inventario`: el bucle de motores ausentes | **0 motores ausentes**: los seis están | `explorar4.py` |

Al lado de cada una hay una prueba **de extremo a extremo con `magick` de
verdad** por el mismo camino, para que la forma construida a mano no se separe
de la real sin que alguien se entere.

### 5.2 Lo que el `/proc` simulado no prueba

Prueba el **algoritmo** de `_tenedores_posix` sobre inodos reales. **No prueba
la plataforma**: que `/proc/<pid>/fd` responda bien los cinco estados en Linux
está medido en `bench/watcher-y-desechables.md` §1 y no se reproduce aquí. Y
sigue valiendo el techo que aquel informe midió: **51 de 96 `/proc/<pid>/fd`
son legibles**, así que la defensa POSIX es **estrictamente más débil** que la
de Windows, no equivalente.

### 5.3 Lo que 100 % NO significa

Cobertura de **sentencias y ramas**, no de comportamiento. Una rama ejecutada
con un solo valor sigue siendo una rama probada con un solo valor. En concreto:

* El `main` de la API se arranca **una vez en loopback**; el camino de red
  (`--permitir-red` con un `bind` real fuera de loopback) **no se abre a
  propósito**, con cinco agentes en la máquina.
* El watcher se ejecuta con `--ciclos 1` y `--intervalo 0`: **la temporización
  real del bucle no se prueba**, sólo sus dos topes.
* Las tres ramas del §5.1 se prueban con entrada construida. **Si el grafo
  cambia y empieza a producir avisos o sobrantes de verdad, esas pruebas
  seguirán pasando aunque el formateo se rompa para el caso real** — el seguro
  es la prueba de extremo a extremo de al lado, no ésta.

---

## 6. PENDIENTE

1. **Medir la cobertura de la UNIÓN ejecutando la suite entera.** El delta de
   este informe es exacto por monotonía, pero el porcentaje global de `filex/`
   no lo mide nadie hasta que la máquina esté tranquila.
2. **Los tres defectos del §3 no están arreglados.** El de la API (§3.1) es el
   que tiene coste: 30 s de hilo por petición mal formada.
3. **`_tenedores_posix` en Linux de verdad.** El `/proc` simulado prueba el
   algoritmo; la lista de aptitud de `ci/linux-apto.json` es el sitio donde
   sabríamos si estas 77 pruebas corren allí — **no se ha medido**, y la
   trampa 104 dice exactamente que no se puede deducir.
4. **`filex/servicio.py` es el suelo de dos de estas cuatro superficies** —la
   API y el watcher lo llaman por debajo— y en la base va al **79,7 %** (359
   sentencias); `filex/mcp.py`, la superficie que este carril no toca, al
   **81,1 %** (190). No son de este carril, pero son el vecindario.

   *(Y una corrección de este mismo informe, que es la trampa 55 en directo:
   la primera versión de este punto decía «`mcp.py` al 0,0 % y `servicio.py`
   al 40 %». Esos dos números salían de **mi** medida aislada —donde `mcp.py`
   no se importa y `servicio.py` sólo se ejecuta por lo que la API le pide— y
   los puse al lado de la palabra «la base», que es otra medida. Los buenos
   son 81,1 % y 79,7 %.)*

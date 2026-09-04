# C5 — La carrera de symlinks (TOCTOU) en Linux: el servidor de referencia y FileX

**worker12, ronda 21, carril `cpu/symlink-toctou`.** Todo MEDIDO en WSL2 salvo lo marcado
`PENDIENTE`. El maestro se comprometió a no correr nada pesado: el arnés **fabrica
contención a propósito** (un hilo atacante que conmuta un componente de ruta miles de
veces por segundo) para abrir la ventana TOCTOU, así que un vecino habría arruinado la
medida.

## 0. Titular

**La carrera GANA, y los DOS son vulnerables — MEDIDO.**

| Sujeto | Patrón | Wins / intentos | Tasa | Tanda |
|---|---|---|---|---|
| **servidor de referencia** `servers/filesystem` (node) | `validatePath`→`readFile` | **1 180 / 13 169** | **8,96 %** | 12 s |
| **FileX** `Confinamiento.resolver`→`open` (patrón de `nucleo.py`) | resolver→open del motor | **15 170 / 86 621** | **17,51 %** | 12 s |
| control **positivo** (puro-python vulnerable, natural) | realpath-check-then-open | 23,58 % | ✓ gana | 12 s |
| control **negativo** (patrón seguro por descriptor `fd`) | open→validar `/proc/self/fd` | **0 / 15 959–17 000** | **0,00 %** | �both |

*(Las tasas absolutas entre sujetos y tandas distintas NO son comparables —`CLAUDE.md` §3—;
lo que se compara y es válido es **dentro** de cada tanda: el patrón vulnerable gana y el
patrón seguro gana 0 % bajo el MISMO ataque. Reproducido en dos tandas por arnés, 2 s y
12 s: el signo se conserva.)*

El `ejemplo_win` del servidor muestra el secreto de fuera devuelto por la herramienta MCP
real, palabra por palabra:
`{"result":{"content":[{"type":"text","text":"SECRETO-DE-FUERA-ENVENENADO\n"}]…}`.

## 1. El vector, leído del código

`servers/filesystem/lib.ts:99-140` — `validatePath(requestedPath)`:

1. Comprobación **léxica** de la ruta pedida contra las raíces (siempre pasa: la ruta
   pedida está literalmente dentro).
2. `realPath = await fs.realpath(absolute)` (línea 116).
3. Comprueba `realPath` dentro de las raíces (línea 118).
4. **DEVUELVE `realPath`** (línea 121).

`index.ts:191-211` — el handler `read_text_file` hace luego `readFileContent(validPath)`
(= `fs.readFile(realPath)`, línea 204). **La ventana TOCTOU está entre el `realpath`
(lib.ts:116) y el `readFile` (index.ts:204).**

El vector que gana: `TARGET = allowed/target` es un **directorio real** con `secret.txt`
dentro cuando corre `realpath` (así el `realPath` contiene el componente `target` literal
y pasa la comprobación); el atacante lo convierte en **symlink a `/tmp/…/outside`** antes
del `readFile`. Reabrir la cadena devuelta re-resuelve `target` → lee el secreto de fuera.

## 2. Construcción del servidor de referencia — NO hizo falta

**El encargo apuntaba a `repos/servers/…`, que no existe; el arnés apunta a
`repos/mcp-refs/servers/…`, que SÍ está clonado Y construido** (`dist/index.js`,
28 217 B, `Aug 20`; `node_modules` presente). Prueba de humo: arranca bajo `node v24` de
WSL con los `node_modules` instalados en Windows (paquetes puros-JS: SDK MCP y zod),
`initialize` y `read_text_file` responden. **MEDIDO**, no hizo falta reconstruir.

## 3. Los controles — por qué el «0 gana» significa algo (trampas 38, 81, 91)

- **Control positivo (puro-python vulnerable)**: replica exacta del patrón (realpath,
  comprobar, devolver, reabrir la cadena). Gana **23,58 %** natural y **14,12 %** con la
  ventana forzada a 2 ms. → el fs y el arnés **sí** producen wins; un «0 gana» no sería
  «arnés roto».
- **Control negativo (patrón seguro por `fd`)**: abre el descriptor primero y valida qué se
  abrió de verdad con `os.readlink('/proc/self/fd/N')`. **0 wins de ~16 000** bajo el mismo
  ataque. → el «0 gana» del seguro es del PATRÓN, no del instrumento.
- **Control de estado estático**: con `TARGET` fijo como symlink, lectura directa =
  `SECRETO-DE-FUERA` (envenenamiento real) y el servidor **deniega** (la comprobación
  actúa); con `TARGET` fijo como dir real, el servidor lee **dentro**. Las tres celdas
  correctas → el arnés clasifica bien los tres desenlaces.
- **Vida del sujeto (trampa 91)**: el servidor node estaba **vivo antes Y después**
  (`vivo_antes=true`, `vivo_despues=true`), y **la carrera se intentó de verdad**
  (`toggles_atacante=395 931`, trampa 38). El win no viene de haber matado al sujeto.

## 4. FileX es vulnerable por su PROPIO primitivo — MEDIDO

`filex/confinamiento.py:400-420` — `resolver()` comprueba y **devuelve
`resuelta = os.path.realpath(ruta)`**. `filex/nucleo.py:632-653,731-768` — `_resolver`
devuelve ese `ent_abs`, hace `os.path.isfile(ent_abs)`, y lo pasa al MOTOR
(`motor.orden(entrada, dentro, …)`), que **abre `entrada` directamente**
(`ffmpeg -i entrada`, `magick entrada …`). **La entrada NO se copia a un desechable para
los motores locales** (`filex/motores.py:orden` recibe la ruta directamente; solo la
SALIDA va al desechable). Es el mismo patrón que el servidor de referencia, y la ventana
`resolver()`→apertura-del-motor es **más ancha** (resolver → isfile → planificar →
reservar destino → `DirectorioDeTrabajo` → `motor.orden` → lock GPU → subprocess → open
del motor).

**Medida (`c5_filex.py`)**: importa el `Confinamiento` real y replica el uso de `nucleo`
(`ent = resolver(p); open(ent)`), con `ecualizar_temporal=False` (el caso de CLI/MCP/
watcher, y el más conservador). Gana **17,51 %** (15 170/86 621); estáticos correctos
(`B_resolver=denegado`, `A_resolver=DENTRO`); el control seguro por `fd`, **0 de 6 805**.
Esta medida es una **COTA INFERIOR**: la ventana de una conversión real es más ancha, así
que la tasa real sería ≥ esta.

**El propio código lo tenía escrito como `PENDIENTE`** (`confinamiento.py:374-378`): *«R7…
En Linux esto debería ser además `O_NOFOLLOW` + `dir_fd` segmento a segmento; PENDIENTE, y
en Windows no existe ninguno de los dos primitivos (MEDIDO). Nada de esto sustituye al
staging de R8: lo complementa.»* — pero la carrera no estaba medida hasta hoy, y la medida
la mueve de `PENDIENTE` a `MEDIDO`.

### 4bis. Refutación de una defensa que se creía activa

El comentario de `resolver()` dice que el **staging de R8** «lo complementa». **Refutado
para los motores locales — MEDIDO leyendo el código**: `motores.py:orden` recibe la ruta y
la pasa al motor sin copiarla a un desechable; el único `copy2` de `nucleo.py` (línea 505)
es para MOVER la SALIDA entre volúmenes. Así que **en la vía de motor local no hay staging
de entrada que complemente nada**: la única defensa sería `O_NOFOLLOW`+`dir_fd`, que no
está. (El motor de CONTENEDOR hace `ent_abs = os.path.abspath(entrada)` y lo monta con
bind; Docker re-resuelve el origen del mount en tiempo de `run`, misma clase de ventana —
**PENDIENTE de medir** con Docker levantado.)

## 5. Qué distingue a los dos

| | Servidor de referencia | FileX |
|---|---|---|
| Patrón de lectura | comprobar realpath → `readFile` **back-to-back** | comprobar realpath → … pipeline … → open del motor |
| Anchura de la ventana | estrecha (dos líneas) | **más ancha** (toda la conversión) |
| Mitigación de ESCRITURA | sí: `writeFile` con flag `wx` + rename atómico (`lib.ts:161-185`) | cerrojo de destinos + `os.replace` (trampas 26/63) |
| Mitigación de LECTURA | **ninguna** | **ninguna** para motor local (staging NO aplica; `O_NOFOLLOW` PENDIENTE) |
| Plataforma medida | Linux/WSL2 tmpfs | Linux/WSL2 tmpfs |

**Lo que los une**: el mismo antipatrón —comprobar la ruta resuelta, devolverla, y volver a
abrirla más tarde—, que es exactamente lo que el control negativo por `fd` evita.

**Lo que los separa**: la ventana de FileX es **más ancha**, y su mitigación documentada
(staging) no existe en la vía de motor local. El servidor de referencia sí cerró su vía de
ESCRITURA (`wx`+rename); ninguno de los dos cerró la de LECTURA.

## 6. Plataforma: por qué esto es Linux y no se vio en Windows

En Windows el vector **no** se pudo medir: el 79 % de los intentos del atacante fallaba por
**bloqueo de fichero** (`mcp-cabos-sueltos.md` §5, heredado), y crear un symlink exige
privilegio. En Linux, `rename`/`unlink` sobre directorios y symlinks **no** tienen bloqueo
obligatorio, así que la ventana está abierta. FileX es un proyecto **primario de Windows**,
donde el sistema operativo da protección incidental; pero el **código es el mismo** y
FileX es Python multiplataforma. **En Windows: PENDIENTE (el heredado dice 79 % de fallo
por lock). En Linux: MEDIDO, gana.**

Sistema de ficheros de esta tanda: `/tmp` es **tmpfs** (declarado en cada JSON), no ext4.
Para este vector basta «sin bloqueo obligatorio en rename/unlink de dirs y symlinks», que
tmpfs cumple igual que ext4 (trampa 41: el rendimiento no se extrapola, pero la ausencia de
bloqueo obligatorio es de la misma clase).

## 7. El arreglo propuesto (NO implementado — el encargo pedía medir, no arreglar)

El control negativo YA demuestra el arreglo: **abrir el descriptor primero y validar el
descriptor, no la cadena.** En la vía de FileX:

- **Sitio**: `filex/confinamiento.py`, un método nuevo `abrir_confinado(ruta)` que devuelva
  un `fd` (o un `os.open` + validación por `/proc/self/fd` en Linux; en Windows, ver abajo),
  y `filex/nucleo.py` que pase el `fd`/una ruta ya-anclada al motor. El problema: los
  motores externos toman una **ruta**, no un `fd`, así que un `fd` puro no basta.
- **Opción robusta en Linux**: resolver segmento a segmento con `O_NOFOLLOW` + `dir_fd`
  (lo que el comentario ya nombra) y entregar al motor una ruta bajo `/proc/self/fd/<dir_fd>`
  o `/dev/fd/`, de modo que el componente conmutable ya esté anclado a un inodo.
- **Opción portable y ya bendecida por el proyecto**: **staging de entrada de verdad** —
  copiar la entrada al `DirectorioDeTrabajo` desechable ANTES de invocar el motor, y que el
  motor lea la copia. La copia sigue teniendo su propia micro-ventana (la copia reabre la
  ruta), pero el motor deja de leer una ruta bajo control del atacante. R8 ya está escrito
  como regla de diseño; hoy no se ejecuta para motores locales. **Coste: `inspect` ya midió
  el staging en 1,7 ms (1 MB) a 166 ms (256 MB)** (`servicio.py:599`), así que no es gratis
  y hay que medir el A/B por tamaño antes de adoptarlo.
- En **Windows** ninguno de los dos primitivos existe (MEDIDO, ya escrito); la defensa allí
  es la del sistema (lock) más el staging.

**Un arreglo de seguridad sin medida es lo que este repositorio no quiere**: queda como
propuesta con su sitio, medido el problema y demostrado el patrón que lo cierra (0/15 959).

## 8. Qué refuté y qué queda PENDIENTE

- **Refutado**: que el staging de R8 «complemente» la comprobación en la vía de motor
  local — no hay staging de entrada ahí (leído en `motores.py`/`nucleo.py`).
- **Confirmado con número**: los dos sujetos son vulnerables; el patrón seguro por `fd` es
  inmune bajo el mismo ataque.
- **PENDIENTE**: (a) medir el vector sobre el motor de **contenedor** (bind mount, con
  Docker levantado); (b) medir en **Windows** (el heredado dice 79 % de fallo por lock, sin
  número de wins); (c) medir la ventana de una **conversión FileX real** (no solo el
  primitivo) con un motor en WSL — mi cifra de FileX es una cota inferior.

## 9. Barrido y limpieza (trampas 47, 52)

Cada arnés borra su `BASE` en `/tmp`; tras las tandas: **0 procesos node vivos, 0
directorios `c5*` en `/tmp`** (comprobado, no supuesto). Topes duros DENTRO de la orden
(`timeout -k 5`), invocación de WSL por ruta (`wsl.exe -e`, no `bash` — trampa 77).

---

## Anexo A — Texto propuesto para `CLAUDE.md` (NO editado; el maestro decide)

> **128. El antipatrón «comprobar la ruta resuelta y volver a abrirla» es una carrera
> TOCTOU que GANA en Linux, y FileX lo tiene por su propio primitivo — MEDIDO el 04/09**
> (`bench/symlink-toctou.md`). `Confinamiento.resolver()` devuelve `os.path.realpath(ruta)`
> y `nucleo.py` pasa esa cadena al motor, que la reabre; entre el `realpath` y la apertura,
> un atacante conmuta un componente de directorio (dir real → symlink a fuera) y el motor
> lee el fichero de fuera. Con un hilo que conmuta miles de veces/s en tmpfs: **el
> primitivo de FileX gana 17,5 %** (15 170/86 621, cota inferior: la ventana de una
> conversión real es más ancha) y **el servidor de referencia `servers/filesystem`, 8,96 %**
> (1 180/13 169). El control negativo —abrir el `fd` y validar `/proc/self/fd`— gana **0 de
> ~16 000** bajo el mismo ataque, así que el «0 gana» significa algo (trampas 38/81/91:
> control positivo que gana 23,6 %, sujeto vivo antes y después, toggles registrados). **El
> staging de R8 NO complementa nada en la vía de motor local: no hay staging de entrada
> ahí** (refutado leyendo `motores.py`). En Windows el vector rinde 79 % de FALLO por
> bloqueo de fichero (heredado, `mcp-cabos-sueltos.md` §5), así que el riesgo práctico es de
> Linux; el código es el mismo. **La defensa es abrir el descriptor y validar el descriptor
> —o hacer staging de entrada de verdad—, no volver a abrir una cadena que el atacante
> controla; `O_NOFOLLOW`+`dir_fd` ya estaba escrito como PENDIENTE y esta medida lo mueve de
> creído a medido.**

## Anexo B — Línea propuesta para `ESTADO-Y-REPARTO.md` §1 (NO editado)

Registrar el informe en la tabla de informes de §1:

`| bench/symlink-toctou.md | worker12 | C5: la carrera de symlinks (TOCTOU) gana en Linux; el servidor de referencia (8,96 %) y FileX (17,5 %, cota inferior) son vulnerables; el patrón seguro por fd, 0 |`

Y mover la fila `C5` del inventario de `bloqueado` (motivo caducado: la VM de WSL ya no cae)
a `cerrado`, con el resultado: **carrera MEDIDA en Linux, ambos vulnerables, arreglo
propuesto sin implementar**.

> **Nota de integridad**: al añadir este `.md` sin poder editar `ESTADO-Y-REPARTO.md`,
> `ci/integridad.py` marcará `informes-registrados: 1 SIN citar`. Es esperado; se cierra con
> la línea de arriba cuando el maestro integre.

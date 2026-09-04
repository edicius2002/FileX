# N38 — El arreglo de la carrera symlink-TOCTOU: abrir el descriptor, no reabrir la cadena

**worker13, ronda 22, carril `nucleo/toctou-fd`.** Arreglo del fallo que la
**trampa 128** midió (`bench/symlink-toctou.md`, worker12). Todo MEDIDO salvo lo
marcado `PENDIENTE`. Soy el único agente de la ronda; la contención la fabrica el
arnés a propósito (un hilo atacante que conmuta un componente de ruta miles de
veces/s), así que un vecino habría arruinado la medida.

## 0. Titular

**La carrera se CIERRA, y hay número de los dos lados — MEDIDO.**

| Sujeto | Patrón | Wins / intentos | Tasa |
|---|---|---|---|
| **FileX vulnerable** `resolver()`+reabrir (antes de N38) | comprobar realpath → reabrir la cadena | **14 189 / 85 867** | **16,52 %** |
| **FileX N38** `abrir_confinado` + lector EN PROCESO | abrir fd → validar `/proc/self/fd` → reabrir ruta anclada | **0 / 217 716** | **0,00 %** |
| **FileX N38** `abrir_confinado` + **MOTOR EXTERNO** (`cat`) | abrir fd → entregar `/proc/<pid>/fd/N` → el motor la reabre | **0 / 60 585** | **0,00 %** |

Total del arreglo bajo el mismo ataque: **0 de 278 301** (Linux/tmpfs). El
control positivo vulnerable reproduce el 17,51 % de worker12 (16,52 % aquí; las
tasas absolutas entre tandas no son comparables, `CLAUDE.md` §3, pero el patrón
vulnerable gana ≈17 % y el arreglo gana 0 bajo el MISMO ataque, que es lo que se
compara). 69 881 toggles del atacante registrados, sujeto vivo (trampas 38/81/91).

**Windows (medido, dato nuevo):** el vector gana **0,067 %** (3/4504) con el
patrón vulnerable —el heredado decía «79 % de fallo del atacante» sin número de
wins; ahora lo hay— y **0 / 35 513** con N38. El mecanismo del cierre es
DISTINTO al de Linux (ver §4).

## 1. El vector, ya medido (trampa 128)

`Confinamiento.resolver()` devuelve `os.path.realpath(ruta)`; `nucleo.py` pasa esa
**cadena** al motor, que la **reabre** (`ffmpeg -i ent`, `magick ent …`). Entre el
`realpath` (comprobación) y la apertura del motor un atacante conmuta un componente
de directorio: `allowed/target` es un **dir real** cuando corre `realpath` (así el
realpath contiene el componente literal y pasa la comprobación) y un **symlink a
fuera** antes de la apertura. Reabrir la cadena re-resuelve el componente → el
motor lee el fichero de fuera de la raíz. El antipatrón es *comprobar la ruta
resuelta y volver a abrirla*; la defensa es *abrir una vez y validar QUÉ se abrió*.

`confinamiento.py:375` ya lo tenía escrito como `PENDIENTE` (`O_NOFOLLOW`+`dir_fd`).

## 2. El arreglo — `Confinamiento.abrir_confinado`

**Sitio: `filex/confinamiento.py` (método nuevo) + `filex/nucleo.py` (uso).** El
método abre el descriptor, valida **el descriptor** (no una cadena), y devuelve un
`_EntradaConfinada` (gestor de contexto) con:

- `.fd`: el descriptor abierto y validado (para un lector en proceso).
- `.ruta`: la ruta ESTABLE que se le entrega al motor externo.
- `.real`: la ruta real que se abrió, ya validada dentro de la raíz.

El mecanismo, con las dos mitades de la carrera cubiertas:

1. **Si el atacante ganó la carrera de apertura** (el componente ya era symlink
   cuando `os.open` corrió), se abre el fichero de FUERA — y `_ruta_real_de_fd`
   (readlink `/proc/self/fd/N` en Linux) lo delata: cae fuera de la raíz →
   `Denegado`. Nunca se lee ni se entrega. En la tanda del arreglo esto es el
   grueso de los «denegado» (207 315 en proceso): el atacante gana la apertura y
   se le detecta, que es el desenlace SEGURO.
2. **Si no la ganó**, se ancla el inodo de DENTRO. La ruta que se le da al motor
   es `/proc/<pid>/fd/N`, que **un motor externo que reabre por ruta alcanza al
   INODO FIJADO** aunque el atacante conmute la ruta original después.

### 2.1. Por qué `/proc/<pid>/fd/N` es viable con un motor que reabre por ruta — MEDIDO

No se dedujo, se sondeó (`probe_procfd.py`, `probe_motor_procfd.py`):

- **Cross-proceso**: tras envenenar la ruta, la lectura directa da `SECRETO-FUERA`
  (envenenamiento real); `/proc/<pid>/fd/N` reabierto **por otro proceso** (`cat`)
  da `CONTENIDO-DENTRO` — alcanza el inodo fijado, **no re-traversa** la ruta.
- **Los tres motores la aceptan**: `magick /proc/pid/fd/N out.jpg` (rc=0, 87 954 B,
  sniffea por contenido, no por extensión), `ffmpeg -i /proc/pid/fd/N` (rc=0), y
  `cat`. El `fd` debe seguir ABIERTO mientras el motor lee (cerrarlo invalida la
  ruta): por eso `nucleo` sostiene el `_EntradaConfinada` durante toda la conversión.

### 2.2. El motor de CONTENEDOR NO recibe la ruta anclada

`motor_contenedor.py:orden` deduce el formato de la **extensión** de `entrada` y la
monta por **bind**; una ruta `/proc/...` (sin extensión, magic-symlink) rompe las
dos cosas. `nucleo` le entrega `ent_seg.real` en su lugar (detectando el tipo por
`isinstance(_EnContenedor)`, sin tocar la huella de `motores.py`/`motor_contenedor.py`
— trampa 32: un atributo nuevo en la clase habría caducado sus aristas; `test_sondeo`
sigue en 48/48). **Su vector TOCTOU es aparte y sigue `PENDIENTE`** (worker12 §4bis:
Docker re-resuelve el origen del mount en tiempo de `run`). En Windows `.ruta` ==
`.real`, así que esto solo decide en Linux.

## 3. Coste del camino de denegación (trampa 28) — MEDIDO

Windows, n=20 000, mediana (µs):

| Camino | Mediana | p90 |
|---|---|---|
| `resolver()` denegado (léxico) — el de la trampa 28, intacto | **13,1** | 15,7 |
| `abrir_confinado()` denegado (léxico) | **11,8** | 15,1 |
| `abrir_confinado()` VÁLIDO (abre fd + valida + cierra) | 107,7 | 170,4 |
| `resolver()` válido (referencia) | 129,7 | 228,8 |

**El camino de denegación de una conversión no se toca:** `abrir_confinado` solo
se invoca en la vía VÁLIDA, después de que `_resolver` haya denegado en la entrada
(13,1 µs, sin cambio). Su propia guarda léxica (R1/R17) corta antes de tocar el
disco, así que aunque se le alcance con una ruta mala cuesta 11,8 µs — no es un
amplificador de DoS. El coste AÑADIDO por conversión es **107,7 µs en la vía
válida** (~0,04 % de una conversión de ~250 ms), y es incluso más barato que el
`resolver()` válido que ya se pagaba, porque `open`+`GetFinalPathNameByHandle` es
más rápido aquí que `realpath`.

**No paga el suelo temporal de N9 a propósito:** añadir un suelo a `abrir_confinado`
reabriría el residuo `existe/prohibido` que N32 cerró (la vía válida pagaría dos
suelos). Su `Denegado` es un artefacto de carrera, no un oráculo de existencia
cronometrable (el fichero existía: `_resolver` ya pasó).

## 4. Windows — MEDIDO, y el mecanismo es DISTINTO (trampas 41, 45)

En esta máquina se pueden crear symlinks (modo desarrollador), así que el vector se
PUDO medir en vez de solo declararlo.

| Lector | Wins / intentos | Tasa |
|---|---|---|
| vulnerable `resolver()`+open | **3 / 4 504** | **0,067 %** |
| N38 `abrir_confinado` + motor reabre `.ruta` (lo que hace nucleo) | **0 / 35 513** | 0,00 % |
| N38 `abrir_confinado` + leer por fd | **0 / 24 184** | 0,00 % |

Windows no tiene `/proc` ni `O_NOFOLLOW`, así que `.ruta` = ruta real validada. El
cierre a 0 NO viene de anclar la ruta, sino de **dos cosas medidas**: (a) mantener
el `fd` abierto **bloquea el rename del directorio padre** mientras dura la ventana
—5 268 errores del atacante en esa tanda, el «79 % de fallo por lock» del heredado
llevado a ~100 % al sostener el handle toda la ventana—, y (b)
`GetFinalPathNameByHandle` **detecta** el envenenamiento pre-apertura (25 414
denegados). El vector vulnerable gana 0,067 % justo porque NO sostiene un handle
durante la reapertura.

**Matiz honesto:** el arnés conmuta el componente inmediato (`target`). El cierre
por handle-bloquea-rename cubre esa clase; un swap de un componente MÁS ARRIBA
(`allowed`) es de la misma familia (Windows también rechaza renombrar un dir con
ficheros abiertos en su subárbol) pero no se midió celda a celda. La detección por
`GetFinalPathNameByHandle` sí es independiente del nivel. **La defensa Windows
depende del bloqueo incidental del sistema + detección, no de anclaje**, y eso es
un mecanismo distinto del de Linux, no una extrapolación (trampas 41/45).

## 5. No se rompió N34/N35/N37 — demostrado discriminante

`git diff main` toca **solo** `filex/confinamiento.py` (+178, **0 deleciones** → las
funciones `_preparar`/`_dentro`/`_lexico_ok` son byte-idénticas) y `filex/nucleo.py`.
N34 y N37-authority viven en `filex/mcp.py`, **intacto**.

Prueba VERDE con N38 + ROJA contra el defecto de cada N reintroducido sobre el
código de hoy (`discriminancia_n34_n35_n37.py`, trampas 60/109/119):

| Prueba | Con N38 (hoy) | Con el bug de su N reintroducido |
|---|---|---|
| `RaicesMixtasN35` (N35) | VERDE (9, 0 fallos) | **10 fallos** — discrimina |
| `RaicesEnConcurrencia` (N34) | VERDE (3, 0 fallos) | (mcp.py intacto; no reintroducido) |
| `AuthorityDeUriN37` (N37) | VERDE (10, 0 fallos) | **18 fallos** — discrimina |
| `RaizVaciaN37` (N37) | VERDE (3, 0 fallos) | **2 fallos** — discrimina |
| `RaicesMixtasPorMCP` (N35) | VERDE (3, 0 fallos) | — |

Bugs reintroducidos: N35 = `_preparar` que lanza `ValueError` en vez de podar;
N37-vacía = `_preparar` sin el salto de raíz vacía (`abspath("")`→cwd);
N37-authority = `_uri_a_ruta` que se queda con `p.path` y tira el `netloc`. Cada uno
pone roja su prueba, así que las pruebas no son vacuas y N38 no las neutralizó.
N34 se declara verde por alcance del diff (su código en `mcp.py` no se tocó) más su
prueba pasando; no se reintrodujo su bug asíncrono.

## 6. La suite completa — las cuatro declaraciones (trampas 94, 101)

**514 passed · 3 skipped · 0 failed · 198 subtests · 205,95 s** — idéntica a la
referencia de máquina despejada.

1. **Intérprete:** `.venv-mcp-filex\Scripts\python.exe`, win32, Python 3.11.9.
2. **Entorno:** Docker 29.4.3 levantado; `FILEX_PRUEBAS_SIDECAR=0` (sin sidecar GPU).
3. **Qué quedó fuera (3 saltos, honestos, ninguno de mi cambio):**
   `test_hito4.py:221` (ningún par real rasteriza hacia texto en esta máquina),
   `test_hito6.py:186` (falta el ráster de `preparar_h6.py`),
   `test_hito6.py:697` (pide `FILEX_PRUEBAS_SIDECAR=1` y la tarjeta).
4. **Estado de la máquina:** única sesión (worker13), despejada — 205,95 s ≈ la
   referencia (187–202 s), no la tanda saturada de 544 s.

## 7. Qué refuté y qué queda PENDIENTE

- **Confirmado con número, los dos lados:** el patrón vulnerable gana (16,52 %
  Linux, 0,067 % Windows); `abrir_confinado` gana 0 (278 301 Linux, 35 513 Windows).
- **Refutado de la propuesta de worker12** («el `fd` puro no basta porque el motor
  toma una ruta»): sí basta, entregando `/proc/<pid>/fd/N` — MEDIDO que un motor
  externo que reabre por ruta alcanza el inodo fijado, y que `magick`/`ffmpeg`/`gs`
  la aceptan. **No hizo falta staging de entrada** (que worker12 daba como la opción
  portable): habría costado 1,7–166 ms por conversión frente a los 107,7 µs de esto.
- **Refutado que Windows necesite anclaje:** el bloqueo incidental del sistema +
  detección por `GetFinalPathNameByHandle` cierran a 0 sin `/proc`.
- **PENDIENTE:** (a) el motor de **contenedor** (bind mount, Docker re-resuelve el
  origen) — recibe `ent_seg.real`, sin regresión respecto a hoy pero sin cierre; su
  vector no se midió con Docker levantado. (b) El swap de un componente por ENCIMA
  del inmediato en Windows no se midió celda a celda (la detección es independiente
  del nivel; el bloqueo por handle también debería serlo, pero no está medido).

## 8. Barrido y limpieza (trampas 47, 52)

Cada arnés borra su `BASE` en `/tmp` (Linux) o `%TEMP%` (Windows) al terminar; sin
lock de GPU (no toca la tarjeta). Comprobado tras las tandas: sin procesos `cat`
huérfanos, sin directorios `n38_*`/`n38-win-*`. Los `.json` de resultados y los
`.py` de arnés se versionan (texto); no hay binarios en `bench/salidas-toctou-fd/`.

---

## Anexo A — Texto propuesto para `ESTADO-Y-REPARTO.md` §1 (NO editado)

Registrar el informe en la tabla de informes de §1:

`| bench/toctou-fd.md | worker13 | N38: abrir_confinado cierra la carrera symlink-TOCTOU (trampa 128) por descriptor; 0/278301 en Linux (motor externo incluido) y 0/35513 en Windows, frente a 16,52%/0,067% vulnerable; coste +107,7µs en la via valida, denegacion intacta |`

> **Nota de integridad**: al añadir este `.md` sin poder editar `ESTADO-Y-REPARTO.md`,
> `ci/integridad.py` marcará `informes-registrados: 1 SIN citar`. Es esperado; se
> cierra con la línea de arriba cuando el maestro integre.

## Anexo B — Texto propuesto para `CLAUDE.md` §4 (trampa 129, NO editado; el maestro decide)

> **129. La defensa contra la carrera symlink-TOCTOU es abrir el descriptor y
> entregar una ruta ANCLADA al motor, y el anclaje de Linux (`/proc/<pid>/fd/N`)
> lo alcanza otro proceso — MEDIDO el 04/09** (`bench/toctou-fd.md`, arregla la
> trampa 128). `Confinamiento.abrir_confinado` abre el `fd`, valida el descriptor
> (`readlink /proc/self/fd` en Linux, `GetFinalPathNameByHandle` en Windows) y
> entrega al motor `/proc/<pid>/fd/N`, que un motor externo que reabre por ruta
> alcanza al INODO FIJADO —sondeado cross-proceso con `cat`, y `magick`/`ffmpeg`/`gs`
> la aceptan porque sniffean el formato por contenido, no por extensión—, con el
> `fd` VIVO durante toda la conversión (cerrarlo invalida la ruta). Gana **0 de
> 278 301** frente al 16,52 % del patrón vulnerable, motor externo incluido. **El
> mecanismo del cierre es DISTINTO en cada plataforma** (trampas 41/45): Linux
> ancla con `/proc` porque no hay bloqueo obligatorio; Windows no tiene `/proc` y
> cierra a **0/35 513** con otra cosa —mantener el `fd` abierto BLOQUEA el rename
> del directorio padre (el «79 % de fallo por lock» del heredado llevado a ~100 % al
> sostener el handle toda la ventana) más la detección por `GetFinalPathNameByHandle`—.
> **El motor de CONTENEDOR no acepta la ruta anclada** (deduce el formato por
> extensión y monta por bind) y recibe la ruta real: su vector sigue PENDIENTE.
> **No hizo falta staging de entrada** (107,7 µs frente a 1,7–166 ms), y el coste de
> DENEGACIÓN queda intacto porque `abrir_confinado` solo corre en la vía válida.

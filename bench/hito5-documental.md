# Hito 5 — el motor documental en contenedor

**Agente K1 · 22 de agosto de 2026 · máquina del proyecto (Windows 10, RTX 3060, Docker 29.4.3 + WSL2)**

Encargo: construir `filex/motor_contenedor.py`, hacer demostrable el criterio amarillo del hito 1, y decir qué se ha ejecutado y qué no.

Código entregado: `filex/motor_contenedor.py`, `pruebas/test_hito5.py` (25 pruebas), `bench/salidas-hito5/` (6 arneses + 5 `.json` + `MANIFIESTO.md`). **No se ha tocado ningún fichero de otro agente.** Los cambios que necesito del núcleo están en §7 con su diff exacto y **no aplicados**.

**Todas las cifras de este informe salen de `bench/salidas-hito5/*.json`.** Cada afirmación va marcada **[MEDIDO]** o **[PENDIENTE]**.

---

## 0. Resumen: lo que cambia

| | Antes del hito 5 | Después |
|---|---:|---:|
| Aristas del grafo | 156 | **215** |
| Aristas `real` (ejecutadas) | 24 | **57** |
| Destinos alcanzables desde `docx` | **0** | **17** |
| Destinos alcanzables desde `epub` | **0** | **17** |
| Destinos alcanzables desde `md` | **0** | **17** |
| Pruebas en verde | 32 | **57** |

**[MEDIDO]** — `python -m filex motores` y `filex.nucleo.FileX().grafo`.

**Seis hallazgos, y tres son refutaciones:**

1. **`filex-convertx` NO es una imagen: es un contenedor.** `CLAUDE.md` §2 y `bench/aristas-nominales.md` §8 la llaman «la imagen `filex-convertx`»; `docker image inspect filex-convertx` responde **`No such image`** (§2). **REFUTA una línea de `CLAUDE.md`.**
2. **`soffice --convert-to txt:Text` sobre un DOCX se cuelga y escribe 471 859 200 B de `.tmp` en el `cwd`.** Es el caso del punto 5 más caro que ha medido el proyecto, y **ninguno de los dos ficheros que deja se llama como la salida** (§4).
3. **Poner el tiempo medido como coste de arista hace que el grafo elija peor.** Con el coste en segundos, `docx→pdf` se resuelve como `docx→html→pdf`: **la mitad de tiempo y una conversión peor**. **REFUTA mi propia primera versión** (§6).
4. **El mecanismo que explica el rechazo por rasterizar funciona, y `TOPE_CANDIDATOS = 8` lo tapa.** Con solo LibreOffice ya hay **siete** caminos `docx→pdf` que conservan el texto; el que rasteriza cuesta `+1000` y nunca entra en la lista (§5.3). **REFUTA «el hito 5 basta para cerrar el criterio amarillo»**: hace falta además un cambio de tres líneas en `grafo.py`.
5. **El contrato de cinco puntos da `ok` a las DOS mitades del par.** El PDF rasterizado —14 851 B, cero caracteres— pasa los cinco puntos. Es un miembro nuevo de la familia de `resvg` (§5.2).
6. **Matar el `docker run` NO mata el contenedor.** Tres `soffice` colgados sobrevivieron **37 minutos** al `taskkill /F /T` de `invocacion.py` y al `--rm`; y como R18 les había borrado el origen del bind mount por debajo, **`docker rm -f` tampoco pudo con ellos a la primera** (§4.4). **REFUTA que `invocacion.ejecutar()` sea un tope para un motor en contenedor.** Arreglado dentro de `motor_contenedor.py` y verificado.

---

## 1. Qué se ha ejecutado, y qué no

**36 aristas candidatas, ejecutadas una por una** en su propio directorio desechable, con censo, el 22/08 entre las 08:33 y las 08:43. `bench/salidas-hito5/sonda.json` guarda de cada una: `argv` completo, `rc`, ms, bytes, `sha256`, censo del punto 5, caracteres recuperados y si sobrevivió el centinela `FILEXSENTINELA7743`.

| Submotor | Ejecutadas | `real` | `nominal` | `sin_sondear` (declaradas, **no ejecutadas**) |
|---|---:|---:|---:|---:|
| LibreOffice (`soffice`) | 12 | **10** | **2** | 6 |
| Pandoc | 15 | **15** | 0 | 9 |
| Calibre (`ebook-convert`) | 9 | **8** | **1** | 8 |
| **Total** | **36** | **33** | **3** | **23** |

**El criterio de `real` es mecánico y está en `_tabla.py`, no escrito a mano:** `rc == 0`, la salida existe **y el centinela sobrevive**. Las tablas de `filex/motor_contenedor.py` se generan desde el JSON con `python bench/salidas-hito5/_tabla.py`; ninguna entrada se ha tecleado.

> **Dónde el criterio no puede aplicarse, y se dice:** en `epub→mobi` y `epub→azw3` la sonda de texto es **ciega** — MOBI y AZW3 comprimen el texto (PalmDoc/LZ77) y el centinela no aparece literal en el binario aunque el libro esté entero. Esas dos entran como `real` **solo por `rc` y bytes**, y queda anotado. **[PENDIENTE]** verificarlas con un lector de MOBI.

**Las 23 `sin_sondear` son deliberadamente pocas.** LibreOffice declara 132 extensiones y Calibre 26 de entrada por 20 de salida: volcarlas al grafo sería exactamente el fallo que este proyecto mide en los demás — el 41,0 % de aristas nominales. Las que hay son pares cuyo **filtro de importación** ya está medido con otro filtro de exportación (`rtf→odt` cuando `rtf→pdf` funciona), y el grafo les suma `+2,0` para que no adelanten jamás a una medida.

---

## 2. El entorno: dos horas de Docker, y una refutación

### 2.1 Docker Desktop estaba parado y tardó 45 minutos en volver — **[MEDIDO]**

Al empezar: `npipe:////./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`. Relanzarlo dejó el demonio **colgado en `starting` durante 11 min 49 s**, con el CLI devolviendo `HTTP 500` y este mensaje en `com.docker.backend.exe.log`:

```
[com.docker.backend.exe.enginedependencies] still waiting for init control API
to respond after 11m49.8626207s
```

Lo que se probó, en orden, y qué dio:

| Intento | Resultado |
|---|---|
| `Docker Desktop.exe` (arranque normal) | **colgado en `starting`**, 500 en toda la API |
| `docker desktop restart` | **`✗ Failed to stop Docker Desktop … context deadline exceeded`** — su propio CLI no puede pararlo |
| `wsl --terminate docker-desktop` | rc=0, **y no arregla nada**: el proceso colgado es el backend de Windows, no la VM |
| `docker desktop stop` + `start` | ídem: `Failed to stop`, y `start` responde «already running» |
| `taskkill /F /T /IM com.docker.backend.exe` + `wsl --terminate docker-desktop` + relanzar | **funcionó**: `SessionID` nueva y el motor arriba |

**Lección con número: el `Status: starting` de Docker Desktop no tiene tope propio.** Estuvo 45 minutos diciendo «arrancando». **Cualquier sonda que espere a que Docker esté listo necesita su propio tope**, exactamente como los testigos de ruido de `CLAUDE.md` §3. En `motor_contenedor.py` ese tope son `TIMEOUT_SONDA = 45 s` y `TIMEOUT_SONDA_IMAGEN = 120 s`.

**Y un detalle que cambia el código de la sonda:** Docker Desktop **a medio arrancar responde `HTTP 500` con `rc=0`**. Mirar el código de salida de `docker version` no basta; hay que mirar que la salida **no esté vacía**. Está así en `entorno()`.

### 2.2 REFUTADO: `filex-convertx` no es una imagen — **[MEDIDO]**

```
$ docker image inspect filex-convertx --format '{{.Id}}'
Error response from daemon: No such image: filex-convertx:latest

$ docker ps --format '{{.Names}}\t{{.Image}}'
filex-convertx    ghcr.io/c4illin/convertx:latest
```

`filex-convertx` es **el nombre del contenedor**; la imagen es `ghcr.io/c4illin/convertx:latest`. Y hay una tercera, mejor: **`filex-c13`** (5,78 GB), que es esa misma con `qpdf` y `tesseract` encima (`bench/salidas-invocacion/Dockerfile.c13`). El motor las prueba **en orden** y usa la primera que exista — `FILEX_IMAGEN_DOC` la sobreescribe.

**Todo lo medido aquí es sobre `filex-c13`, `sha256:6d359bad483e…`**, que es el `build` que llevan las 59 aristas.

### 2.3 Los binarios, sondeados dentro de la imagen — **[MEDIDO]**

`command -v` dentro de `filex-c13`: `soffice`, `pandoc`, `ebook-convert`, `qpdf`, `tesseract`, `magick`, `gs`, `inkscape`, `resvg` — **los nueve presentes**. Confirma `CLAUDE.md` §2 y añade que `filex-c13` **sí** trae los dos que faltaban.

**No se deduce de aquí: se sondea en cada arranque y se cachea por ID de imagen** (`%TEMP%/filex-sonda-contenedor.json`). Si la imagen cambia, el ID cambia y la sonda se repite sola. Cuesta **un arranque de contenedor: 864 ms** (mediana de n=9, §3.2).

### 2.4 `--entrypoint` no es opcional — **[MEDIDO]**

La imagen trae `ENTRYPOINT ["bun","run","dist/src/index.js"]` y `WorkingDir /app`. Sin sustituirlo, la orden se le pasa **como argumentos a la aplicación web de ConvertX**:

```
$ docker run --rm ... -w /trabajo filex-c13 sh -c '...'
error: Module not found "dist/src/index.js"
```

Es el caso de libro de *«sondear capacidades en ejecución, no deducirlas»*: el `docker run image cmd` del manual **no funciona con esta imagen**, y el error no menciona el entrypoint por ningún lado.

---

## 3. Coste

### 3.1 Las 36, con n=1 — **[MEDIDO]**

Extracto; la tabla completa con `sha256` y la orden exacta está en `bench/salidas-hito5/MANIFIESTO.md`.

| id | submotor | arista | rc | ms | bytes | caracteres | centinela |
|---|---|---|---:|---:|---:|---:|:---:|
| L01 | LibreOffice | `docx→pdf` | 0 | 6 339 | 22 820 | 456 | sí |
| L02 | LibreOffice | `odt→pdf` | 0 | 4 181 | 31 976 | 456 | sí |
| L04 | LibreOffice | `html→pdf` | 0 | 2 167 | 32 807 | 456 | sí |
| L09 | LibreOffice | `docx→png` | 0 | 5 746 | 38 798 | **0** | **no** |
| **L10** | LibreOffice | **`epub→pdf`** | **1** | 7 894 | 0 | 0 | no |
| **L11** | LibreOffice | **`docx→txt`** | **1** | **240 228** | 0 | 0 | no |
| L12 | LibreOffice | `odt→txt` | 0 | 10 433 | 458 | 456 | sí |
| P02 | Pandoc | `md→html` | 0 | 1 407 | 4 525 | 3 131 | sí |
| P11 | Pandoc | `md→pdf` (xelatex) | 0 | 12 414 | 10 370 | 456 | sí |
| P12 | Pandoc | `docx→pdf` (xelatex) | 0 | 7 242 | 8 163 | 456 | sí |
| **C01** | Calibre | **`epub→pdf`** | **0** | 17 652 | **26 817** | 456 | **sí** |
| **C06** | Calibre | **`epub→html`** | **1** | 2 073 | 0 | 0 | no |
| C09 | Calibre | `docx→pdf` | 0 | 10 152 | 19 896 | 456 | sí |

**Pandoc es el barato del estrato: 12 de sus 15 aristas bajan de 2,5 s.** LibreOffice está entre 2,2 y 10,4 s, y Calibre entre 4,9 y 20,6.

### 3.2 Las cuatro que deciden el hito, con n=9 — **[MEDIDO]**

`bench/salidas-hito5/medianas.json`. **Tanda etiquetada `SUCIA`** (sesión de escritorio remoto activa a propósito: es estructural, `CLAUDE.md` §3).

| caso | submotor | arista | mediana n=9 |
|---|---|---|---:|
| `_vacio` | — | **arranque de contenedor en vacío** | **864 ms** |
| P01 | Pandoc | `md→docx` | 3 288 ms |
| L09 | LibreOffice | `docx→png` | 4 602 ms |
| L01 | LibreOffice | `docx→pdf` | 6 523 ms |
| C01 | Calibre | `epub→pdf` | 20 615 ms |

**El dato de diseño está en la primera fila: la frontera del contenedor cuesta 864 ms, o sea el 13,2 % de un `docx→pdf` y el 4,2 % de un `epub→pdf`.** El resto es el motor. **No hay que optimizar el `docker run`: hay que optimizar Calibre, o no llamarlo.**

> **Testigos de ruido, los dos** (`CLAUDE.md` §3): deriva **0,97** (bucle monohilo, 59,9 → 58,0 ms) y nivel **66,0 → 63,9 ms** (`ffprobe -version`, con su propio tope de 20 s, no agotado). Tanda limpia por los dos, y **`SUCIA` igual** por la sesión remota. **Las cifras absolutas no son comparables con las de otras tandas; las relativas dentro de esta, sí.**

> **Y una salvedad honesta sobre la comparación con el 21/08:** `bench/aristas-nominales.md` §8.1 midió `epub→pdf` con Calibre en **7 045 ms** por `docker exec` sobre un contenedor ya vivo; aquí sale **20 615 ms** por `docker run`. **No son la misma medida y no se pueden comparar así.** Lo que sí es comparable, y coincide, es **el resultado**: 26 817 B exactos y el centinela.

---

## 4. El punto 5, y por qué el contenedor no es un agujero en el contrato

### 4.1 La decisión: `docker run` con bind mount, no `docker exec` + `docker cp`

`docker exec` sobre el contenedor ya levantado obligaría a `docker cp` de ida y de vuelta —tres procesos por conversión— y, sobre todo, **mataría el quinto punto del contrato**: `docker cp` trae lo que se le nombra, así que lo que el motor escribiera de más dentro del contenedor **no se vería nunca**.

Con `docker run` y `--mount type=bind,source=<desechable>,target=/trabajo`, **el directorio desechable del anfitrión ES el `/trabajo` del contenedor**. El censo de `trabajo.py` ve lo que el motor escribió, esté el motor donde esté. **El punto 5 sobrevive a la frontera del contenedor porque la frontera se cruza con un montaje y no con una copia.**

### 4.2 Y no es teórico: 471 859 200 B — **[MEDIDO]**

`soffice --headless --convert-to txt:Text` sobre `entrada.docx` (1 354 B):

| intento | timeout | rc | censo del desechable |
|---|---:|---:|---|
| L11 (sonda completa) | 240 s | 1, **agotado** | `.~lock.salida.txt#` 70 B · `lu2714hzc.tmp` **471 859 200 B** |
| X1 (confirmación) | 60 s | 1, **agotado** | `.~lock.salida.txt#` 70 B · `lu281cznl.tmp` **93 065 216 B** |
| X2 (`--convert-to txt` sin filtro) | 60 s | 1, **agotado** | `.~lock.salida.txt#` 70 B · `lu271e8p3.tmp` **89 882 624 B** |
| X3 (**el mismo filtro sobre ODT**) | 60 s | **0**, 6 214 ms | **vacío** — 458 B de salida, centinela intacto |

`bench/salidas-hito5/sonda-txt.json`.

**Cuatro cosas se leen de esa tabla:**

1. **No es una salida grande: es una fuga, y acelera.** Con cuatro observaciones —8,0 MB a los 20 s, 89,9 y 93,1 MB a los 60, 471,9 MB a los 240— el ritmo va de **0,40 a 1,97 MB/s** y **no es constante**. Sin tope, llena el disco.
2. **No es el nombre del filtro.** `txt:Text` y `txt` a secas dan lo mismo.
3. **No es el destino.** `odt→txt` con la orden idéntica tarda 6,2 s y sale bien. **Es el filtro de importación de DOCX el que se rompe hacia texto plano.**
4. **Ninguno de los dos ficheros se llama como la salida.** El punto 4 del contrato (pedido = obtenido) no los ve; el punto 5 sí. **Con `docker cp` no se habría visto ninguno.**

> **Y el grafo llega igual al destino:** `docx→txt` está marcada `nominal`, y el orquestador resuelve **`docx→odt→txt`** con dos aristas `real`. Es exactamente la tesis del hito 1: *alcanzar es fácil, elegir bien no.*

### 4.3 Confinamiento en el borde del contenedor — **[MEDIDO]**

Tres decisiones, y las tres están probadas en `pruebas/test_hito5.py::Invocacion`:

* **La entrada se monta fichero a fichero y de solo lectura.** Montar su directorio padre le enseñaría al contenedor todo lo que hubiera al lado. Comprobado en ejecución: `echo x >> /ent/salida.md` → `Read-only file system`.
* **`--network none`.** Ninguno de los tres motores necesita red para convertir un documento local.
* **`--mount` y no `-v`**, porque una ruta de Windows lleva `D:` y `-v` parte por `:`. El precio: `--mount` separa sus opciones por comas y **no las escapa**, así que una ruta con coma se rechaza en vez de montar otra cosa.

> **Trampa de herramienta, nueva:** en Git Bash, `-w /trabajo` se convierte en `-w 'C:/Program Files/Git/trabajo'` y `docker` responde *«the working directory … is invalid»*. Hace falta `MSYS_NO_PATHCONV=1` **para probar a mano**. **Por el código no pasa**, porque `invocacion.ejecutar()` no usa shell — que es otro argumento a favor de la regla.

### 4.4 Y el hallazgo que solo aparece al recoger: **matar el `docker run` no mata el contenedor** — **[MEDIDO]**

Al terminar todo y listar los contenedores para dejar la máquina como estaba:

```
$ docker ps --format '{{.Names}}|{{.Image}}|{{.Status}}|{{.Command}}'
stupefied_engelbart|filex-c13|Up 29 minutes|"soffice --headless …"
silly_carver       |filex-c13|Up 30 minutes|"soffice --headless …"
happy_driscoll     |filex-c13|Up 37 minutes|"soffice --headless …"
```

**Son L11, X1 y X2: los tres `docx→txt` colgados.** `invocacion.ejecutar()` había agotado su timeout y llamado a `_matar_arbol()` —`taskkill /F /T` sobre el PID— **hace media hora**. Y llevaban `--rm`.

**`docker run` es un CLIENTE de la API. El proceso vive en el demonio.** Matar al cliente deja el contenedor corriendo, y `--rm` solo dispara cuando el contenedor **para**, cosa que no había pasado.

**Y hay una segunda mitad, peor, que nace de combinar R18 con el bind mount:**

```
$ docker exec e5f1b9516da6 ls -la /trabajo
ls: cannot access '/trabajo': No such file or directory

$ docker rm -f e5f1b9516da6
Error response from daemon: cannot remove container "e5f1b9516da6":
could not kill container: tried to kill container, but did not receive an exit event
```

Cuando `nucleo._un_salto` termina, su `finally` llama a `t.cerrar()` y **R18 borra el desechable** — que es el **origen del bind mount de un contenedor que sigue vivo**. El montaje desaparece bajo él y el contenedor queda en un estado del que **`docker rm -f` no lo saca a la primera**. *(Sí lo sacó: la orden devolvió error y la eliminación se completó sola alrededor de un minuto después. **[MEDIDO]**)*

**Tres consecuencias, y la primera es una regla:**

1. **El tope de un motor en contenedor tiene que estar DENTRO del contenedor.** `invocacion.ejecutar()` es un tope para el cliente, no para el motor. Es exactamente la trampa que `CLAUDE.md` §3 ya avisa —*«estos motores dejan huérfanos vivos 13 minutos»*— **con un agravante nuevo: aquí el huérfano no lo ve `taskkill`, porque no está en Windows.**
2. **El orden del desmontaje importa: parar el contenedor, y después borrar.** Borrar primero deja al contenedor en un estado del que cuesta sacarlo.
3. **La sonda de §1 encontró esto porque NO llevaba el tope de dentro.** Está así a propósito y se deja así: `_sonda.py` es el registro de lo que se midió, y lo que se midió incluye el fallo. **El producto sí lo lleva.**

**El arreglo, dentro de `filex/motor_contenedor.py`:** el entrypoint deja de ser el motor y pasa a ser `timeout -k 5 110` de coreutils (9.10, sondeado dentro de la imagen). Mata al motor desde dentro, el contenedor sale con `rc=124` y `--rm` lo limpia. `TIMEOUT_DENTRO = 110` está **por debajo** de `invocacion.TIMEOUT_POR_DEFECTO = 120` a propósito: el de dentro tiene que disparar primero.

Verificado con el motor colgado de verdad (`bench/salidas-hito5/tope.json`, y `pruebas/test_hito5.py::test_el_tope_de_dentro_no_deja_contenedores_vivos`):

| | resultado |
|---|---|
| tope dentro / tope fuera | 20 s / 120 s |
| `rc` | **124** (GNU `timeout` disparó) |
| `agotado` por `invocacion` | **no** — no le dio tiempo |
| tiempo real | **24 532 ms** para un tope de 20 s |
| **contenedores nuevos vivos al volver** | **ninguno** |
| censo del punto 5 | `.~lock.salida.txt#` 70 B · `lu292ks5t.tmp` 8 015 872 B |

> **Los 4,5 s de más son el `-k 5`: LibreOffice colgado ignora el SIGTERM y hace falta el KILL.** Un `timeout` sin `-k` no habría matado nada. **[MEDIDO]**

---

## 5. El criterio amarillo del hito 1

`PLAN-ORQUESTADOR.md` §7 lo deja abierto: *«el rechazo comparado NO se puede demostrar aquí: con ffmpeg, ImageMagick y Ghostscript no existe ningún par de formatos donde compitan un camino que conserva el texto y otro que lo rasteriza»*.

### 5.1 El par existe, y con el mismo binario a los dos lados — **[MEDIDO]**

```
soffice --headless --convert-to pdf --outdir /trabajo /ent/salida.docx
soffice --headless --convert-to png --outdir /trabajo /ent/salida.docx
```

Mismo motor, misma versión, misma entrada, misma máquina. **La diferencia no está en la calidad del motor: está en el camino.**

### 5.2 Los dos caminos, hechos de verdad por el núcleo — **[MEDIDO]**

`bench/salidas-hito5/camino.json`, generado por `_camino.py`, que llama a `FileX.convertir()` — no a la sonda:

| camino | ok | ms | bytes | caracteres | centinela | **contrato** |
|---|:---:|---:|---:|---:|:---:|---|
| **A · `docx→pdf`** (LibreOffice) | sí | 8 812 | 22 820 | **456** | **sí** | `ok` 6/6 |
| **B · `docx→png→pdf`** (LibreOffice + ImageMagick) | sí | **8 030** | 14 851 | **0** | **no** | **`ok` 6/6** |

**Tres lecturas, y la tercera es la importante:**

1. **El camino que destruye el texto es el más RÁPIDO** (8 030 frente a 8 812 ms). Un orquestador que optimice tiempo elige el malo.
2. **El PDF rasterizado es válido.** Firma correcta, geometría correcta, 14 851 B, se abre.
3. **El contrato de cinco puntos le da `ok`.** Los cinco. Es un **miembro nuevo de la familia de `resvg`** (`bench/contrato-quinto-punto.md` §4.4, «al menos cinco miembros y el contrato atrapa uno») y encaja exactamente en su formulación: *el contenido perdido solo existe como píxeles, así que hace falta fidelidad, no contrato.* **Lo único que separa A de B es el GRAFO**, que se niega a tomar B.

### 5.3 El mecanismo funciona… y el tope lo tapa — **[MEDIDO]**

Con el grafo mínimo de tres aristas **reales** (`docx→pdf`, `docx→png`, `png→pdf`) el grafo elige A **y explica el rechazo de B**: *«rasteriza en 'docx→png [doc_libreoffice]' y 'pdf' admite texto: el resultado tendría la geometría correcta y ni una letra seleccionable»*. `pruebas/test_hito5.py::ElegirBienConAristasREALES`.

**Con el grafo entero, la elección sigue siendo correcta y la explicación desaparece.** Y no por falta de motores:

```
docx → pdf              (LibreOffice)   ← elegido, coste 1,065
docx → html → pdf                       ← rechazado, "válido pero más caro"
docx → odt  → pdf                       ← rechazado, "válido pero más caro"
docx → rtf  → pdf                       ← rechazado, "válido pero más caro"
docx → odt  → txt → pdf                 ← rechazado, "válido pero más caro"
docx → odt  → html → pdf                ← rechazado, "válido pero más caro"
docx → html → odt → pdf                 ← rechazado, "válido pero más caro"
docx → html → odt → txt → pdf           ← rechazado, "válido pero más caro"
docx → png  → pdf                       ← NO APARECE
```

`Grafo.TOPE_CANDIDATOS = 8` conserva **los ocho más baratos**, y un camino que rasteriza cuesta `+1000`: es **siempre** el último. **Con solo LibreOffice ya hay siete caminos que conservan el texto.** En cuanto hay ocho, el rechazo que hay que explicar es justo el que el tope tira.

> **Esto REFUTA la premisa del encargo.** «Con el motor documental el criterio amarillo se puede demostrar» es **verdad a medias**: la mitad *«elige bien»* se demuestra hoy y está probada; la mitad *«y dice por qué»* necesita además **tres líneas en `grafo.py`** (§7.2). Está escrito como prueba en verde —`test_con_el_grafo_entero_el_rechazo_deja_de_explicarse`— con la instrucción de borrarla cuando el núcleo reserve el hueco.

### 5.4 Y el criterio que «discrimina de verdad»: `epub→pdf` — **[MEDIDO]**

```
$ python -m filex plan a.epub b.pdf
CAMINO (1 salto(s), coste 1.2):
  epub → pdf
      1. epub→pdf [doc_calibre]
```

| Vía | Resultado |
|---|---|
| `soffice --headless --convert-to pdf entrada.epub` | **rc=1**, sin salida, `Error: source file could not be loaded` |
| `ebook-convert entrada.epub salida.pdf` | **rc=0**, **26 817 B** —el mismo número que midió otro agente el 21/08 con otra invocación—, 456 caracteres, centinela y tabla `AX-1` |

**Confirmado, no refutado.** LibreOffice exporta EPUB y no lo importa. La arista está `REAL` en `CalibreEnContenedor` y `NOMINAL` en `LibreOfficeEnContenedor`, y una arista `nominal` **sale del grafo** (`_coste_paso` le suma infinito): el orquestador no puede elegirla ni por accidente. Está probado a los dos niveles —planificación y conversión con centinela— en `pruebas/test_hito5.py::Integracion`.

**Y con eso, `epub→png` y `epub→docx` dejan de ser inalcanzables:** `filex plan a.epub b.png` resuelve `epub→docx→png` en dos saltos. `bench/fidelidad-caminos.md` §1.4 los daba por muertos; lo que estaba muerto era la elección de motor.

---

## 6. REFUTACIÓN de mi propia primera versión: el coste no puede ser el tiempo

La primera versión de `_tabla.py` ponía **los segundos medidos** como coste de arista. Parecía lo más honesto —una cifra medida en vez de una constante— y **da una elección peor. [MEDIDO]**

```
$ python -m filex plan a.docx b.pdf        # con coste = segundos
CAMINO (2 salto(s), coste 3.2):
  docx → html → pdf
      1. docx→html [doc_pandoc]        1,0 s
      2. html→pdf  [doc_libreoffice]   2,2 s

DESCARTADO  docx → pdf
  porque más corto, pero pierde más información
```

**Es la mitad de tiempo (3,2 s frente a 6,5) y una conversión peor:** pasar un DOCX por HTML tira la maquetación. El grafo no lo sabe porque **nadie le ha dado un precio al salto de más**.

La corrección: **`coste = 1,0 + ms / 100 000`** — un salto vale 1,0 y un segundo medido vale 0,01. Con eso el número de saltos vuelve a mandar (que es la convención de los motores nativos, todos entre 1,0 y 1,2) y **el tiempo decide entre motores que hacen la MISMA arista**, que es justo donde el tiempo es la variable correcta:

| `docx→pdf` | mediana | coste |
|---|---:|---:|
| LibreOffice | 6 523 ms | **1,065** ← elegido |
| Pandoc (xelatex) | 7 242 ms | 1,072 |
| Calibre | 10 152 ms | 1,102 |

> **Y hay un segundo defecto ahí dentro, del núcleo:** el mensaje `«más corto, pero pierde más información»` se emite **siempre que un candidato rechazado tiene menos saltos que el elegido**, sin haber medido ninguna pérdida. En el ejemplo de arriba el grafo **afirmó una pérdida de información que nunca midió**, y era falsa. Es precisamente lo que este proyecto le critica al resto del sector. Diff en §7.4.

---

## 7. Cambios que pido al núcleo (**NO aplicados**)

Los cuatro son de `filex/`, que no es mío. Van con diff exacto para que el consolidador los aplique o los rechace.

### 7.1 `Motor.motivo_ausencia` — el mensaje de la CLI miente

Hoy `cli.py` imprime «falta el ejecutable '{m.binario}'» para todo motor ausente. Aquí lo que falta puede ser **`docker`**, **el demonio**, **la imagen** o **un binario dentro de ella** — cuatro cosas distintas, y R14 pide nombrar **la capacidad**, no el comando. Mientras tanto, `_marcar_binario()` sustituye el nombre del binario por el motivo, que es un apaño y está marcado como tal en el código.

```diff
--- a/filex/motores.py
+++ b/filex/motores.py
@@ class Motor:
     nombre: str
     binario: str
     version: str = ""
     ruta: str | None = None
     aristas: list[Arista] = field(default_factory=list)
+    #: Por qué NO está disponible, cuando no lo está. «Falta el ejecutable X»
+    #: no siempre es verdad: puede faltar el demonio, la imagen, o un binario
+    #: dentro de ella. R14: se nombra la CAPACIDAD, no el comando que la instala.
+    motivo_ausencia: str = ""
```

```diff
--- a/filex/cli.py
+++ b/filex/cli.py
@@ def _inventario(fx, args):
-        print(f"  ✗ {m.nombre:<14} no disponible — falta el ejecutable "
-              f"'{m.binario}'")
+        print(f"  ✗ {m.nombre:<14} no disponible — "
+              + (getattr(m, "motivo_ausencia", "")
+                 or f"falta el ejecutable '{m.binario}'"))
```

Y entonces `_marcar_binario()` de `motor_contenedor.py` desaparece.

### 7.2 `Grafo`: reservarle un hueco al camino que rasteriza — **el que cierra el criterio amarillo**

```diff
--- a/filex/grafo.py
+++ b/filex/grafo.py
@@ def _enumerar(self, o, d, max_saltos):
         mejores: list[tuple[float, int, Camino]] = []   # montículo-máximo por coste
+        # Un camino que rasteriza cuesta +1000: NUNCA entra en los ocho más
+        # baratos. Y es justo el rechazo que hay que EXPLICAR. MEDIDO: con solo
+        # LibreOffice ya hay siete caminos `docx→pdf` que conservan el texto, y
+        # el octavo tapa al que rasteriza (`bench/hito5-documental.md` §5.3).
+        mejor_raster: Camino | None = None
         gasto = 0
@@
             if actual == d:
                 contador += 1
                 camino.coste = coste + _penalizacion_perdida(camino)
+                if camino.rasteriza and (mejor_raster is None
+                                         or camino.coste < mejor_raster.coste):
+                    mejor_raster = camino
                 heapq.heappush(mejores, (-camino.coste, contador, camino))
@@
-        return sorted((c for _, _, c in mejores), key=lambda c: (c.coste, c.saltos))
+        salida = [c for _, _, c in mejores]
+        if mejor_raster is not None and mejor_raster not in salida:
+            salida.append(mejor_raster)      # se explica, no se elige: cuesta +1000
+        return sorted(salida, key=lambda c: (c.coste, c.saltos))
```

Con esto, `pruebas/test_hito5.py::test_con_el_grafo_entero_el_rechazo_deja_de_explicarse` **debe pasar a fallar**, y hay que borrarla. Está dicho en su propio docstring.

### 7.3 `formatos.py`: faltan `mobi` y `azw3`

Las uso en 5 aristas medidas y `formatos.formato()` devuelve `None` para las dos. No rompe nada —el grafo lo tolera—, pero el orquestador no sabe que llevan texto ni puede razonar sobre ellas.

```diff
--- a/filex/formatos.py
+++ b/filex/formatos.py
@@     Formato("epub", "documento", texto=True),
+    Formato("mobi", "documento", texto=True,
+            nota="MOBI comprime el texto (PalmDoc/LZ77): un centinela NO "
+                 "aparece literal en el binario aunque el libro esté entero. "
+                 "Una sonda de texto ingenua lo da por destruido."),
+    Formato("azw3", "documento", texto=True, nota="Ídem MOBI."),
```

### 7.4 `Grafo.camino`: no afirmar una pérdida que no se ha medido

```diff
--- a/filex/grafo.py
+++ b/filex/grafo.py
@@ for c in encontrados[1:]:
             elif c.saltos < elegido.saltos:
-                rechazados.append((c, "más corto, pero pierde más información"))
+                # Lo único que se ha comparado es el COSTE. Decir «pierde más
+                # información» es afirmar una medida que no se ha hecho — y
+                # MEDIDO que puede ser falsa (`hito5-documental.md` §6).
+                rechazados.append((c, "más corto, pero más caro en el coste "
+                                      "medido de sus aristas"))
```

### 7.5 Lo que NO pido, y por qué

Pensé pedir que `Motor.orden()` recibiera la `Arista` elegida, porque un motor que envuelve tres binarios tiene que volver a derivar cuál. **No hace falta: la solución correcta era una clase por submotor**, y entonces el grafo elige y `orden()` no adivina nada. Queda como nota de diseño: si un motor necesita saber qué arista se eligió, es que son varios motores.

### 7.6 `Motor.orden()` debería recibir el timeout — y `nucleo` debería parar antes de borrar

Las dos salen de §4.4 y las dos son de `nucleo.py`/`motores.py`.

**(a)** Hoy `TIMEOUT_DENTRO = 110` es una constante del motor que **adivina** el tope del que llama. Si alguien invoca `convertir(..., timeout=30)`, el de dentro no dispara nunca y volvemos al huérfano. Lo correcto es que el motor sepa cuánto tiene:

```diff
--- a/filex/nucleo.py
+++ b/filex/nucleo.py
-            argv = motor.orden(entrada, dentro, pedido if ultimo else {})
+            # Un motor que delega en un proceso remoto (contenedor, servicio)
+            # necesita poner SU tope por dentro: el de aquí solo alcanza al
+            # cliente. MEDIDO: `bench/hito5-documental.md` §4.4.
+            argv = motor.orden(entrada, dentro, pedido if ultimo else {},
+                               timeout=timeout)
```

…con `Motor.orden(self, entrada, salida, pedido, *, timeout=None)` para no romper a los tres nativos.

**(b)** El `finally` que borra los desechables corre **antes** de que nadie garantice que el motor ha parado. Con motores nativos da igual —`_matar_arbol` sí los mata—; con un contenedor, borrar el origen de un bind mount vivo lo deja atascado. **PENDIENTE** de una forma limpia de expresarlo: lo mínimo sería que `Motor` pudiera declarar un `parar()` que `nucleo` llamase antes de `t.cerrar()` cuando `r.agotado`.

---

## 8. Lo que queda PENDIENTE

| # | Qué | Por qué importa |
|---|---|---|
| 1 | **Fidelidad más allá del centinela.** Todo lo medido aquí comprueba que `FILEXSENTINELA7743` y `AX-1` sobreviven; **nada comprueba la maquetación**. Es lo que haría falta para justificar «LibreOffice es mejor que Pandoc para `docx→pdf`», que hoy **no está medido** — se elige por tiempo | Es la mitad del argumento contra `docx→html→pdf` de §6, y hoy se sostiene solo con el sentido común |
| 2 | **Las 23 aristas `sin_sondear`** de las tres clases | Cada una es una arista que el grafo puede intentar y que nadie ha ejecutado |
| 3 | **`epub→mobi` y `epub→azw3` verificadas con un lector** de MOBI, no con un `grep` binario | Hoy entran como `real` solo por `rc` y bytes |
| 4 | **Una segunda semilla de documento.** Todo sale de `entrada.docx/epub/md/odt/…`, que son **un** documento en seis formatos. `CLAUDE.md` §3 avisa: *«cuando midas una propiedad del FORMATO, varía la entrada; si no, estás midiendo tu entrada»* — y ya costó 42 falsos positivos una vez | El cuelgue de `docx→txt` podría ser de **este** DOCX, no del filtro |
| 5 | **`xlsx`, `pptx`, `csv`, `svg` y `tex`** dentro del contenedor | LibreOffice y Pandoc los hacen; no se han ejecutado aquí |
| 6 | **El coste de arranque en frío.** Los 864 ms son con la imagen ya en caché de página; el primer `docker run` tras arrancar Docker tardó **34 672 ms** en una conversión cuya mediana es 6 523 | Un orquestador que prometa latencia tiene que saberlo |
| 7 | **Reutilizar un contenedor vivo sin perder el punto 5** | 864 ms × cada conversión es el precio de la garantía. Si hubiera forma de bajarlo conservando el censo, valdría el 13,2 % de `docx→pdf` |
| 8 | **Gotenberg**, que es lo que el enunciado original del hito 5 pedía (`:3200`, levantado y `healthy`) | Aquí no se ha usado: LibreOffice directo dentro de la imagen cubre lo mismo sin HTTP, y **sin el HTTP 500 de EPUB** que motivó todo esto |

---

## 9. Reproducir

```
docker image inspect filex-c13 --format '{{.Id}}'
python bench/salidas-hito5/_sonda.py          # 36 aristas, ~400 s
python bench/salidas-hito5/_medianas.py       # n=9 + testigos, ~500 s
python bench/salidas-hito5/_tabla.py          # las tablas de motor_contenedor.py
python bench/salidas-hito5/_camino.py         # los dos caminos
python bench/salidas-hito5/_tope.py           # el tope DENTRO del contenedor
python bench/salidas-hito5/_manifiesto.py
python -m unittest pruebas.test_hito1 pruebas.test_hito5   # 57 pruebas
```

**Toda invocación de este trabajo pasa por `filex.invocacion.ejecutar()`** —incluidas las de `docker`— en un `DirectorioDeTrabajo` desechable que se censa antes de borrarse. No hay ningún `subprocess` fuera de `invocacion.py`.

**Salidas binarias borradas**, con `sha256`, tamaño y la orden exacta en `bench/salidas-hito5/MANIFIESTO.md`.

**Docker queda levantado**, igual que lo dejó la sesión del 21/08. No se ha cerrado ningún contenedor.

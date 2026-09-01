# El cerrojo de destino deja de ser de proceso — y la mitad que lo cierra no es el cerrojo

**Agente N-b · 23 de agosto de 2026 · máquina de siempre (Windows 10 Home 19045, Python 3.11.9, Git Bash)**
**Encargo N1** de `ESTADO-Y-REPARTO.md` §3.N, abierto por `bench/hito7-superficies.md` §5.3 y §7.3.
**Ficheros tocados:** `filex/nucleo.py` (+251 / −6), `pruebas/test_cerrojo.py` (nuevo, 11 pruebas), la clase `NucleoDestinoEnCurso` de `pruebas/test_hito7.py` (+1 prueba), y este informe.
**Salidas y logs:** `bench/salidas-cerrojo/`.
**No se usó la GPU.** El encargo no la necesita y había lock de máquina; `nvidia-smi` no se llamó ni una vez.

---

## 0. Lo que hay que saber, en cinco líneas

1. **El fallo del hito 7 está reproducido ENTRE PROCESOS, con las mismas tres cifras — MEDIDO.** Tres `python` distintos, tres entradas distintas, una ruta de salida: **tres `ok`**, declarando **13 516 / 14 402 / 647 580 B**, y **un fichero de 647 580 B** en el disco. Dos respuestas describen un fichero que ya no existe. Es el §5.3 del hito 7 llegando por una ruta independiente, con el cerrojo de proceso puesto y funcionando.
2. **Cerrado, y con la lección de L1 aplicada: el arreglo tiene DOS mitades.** La **exclusión** (candado de fichero por destino en `%TEMP%/filex-destinos/`) cierra a los otros `filex`. La **detección** (`os.replace(p, p)`, la trampa 27) es lo único que se puede hacer contra quien nunca iba a tomar el candado. **Sin la segunda, FileX pisaba el fichero abierto de un tercero y devolvía `ok`: 4 014 B → 13 516 B — MEDIDO.**
3. **El candado se recupera solo. No hay lógica de huérfanos, y es deliberado.** Se eligió un candado de **rango de bytes** (`msvcrt.locking` / `fcntl.flock`) y no un `O_CREAT|O_EXCL` porque lo suelta el **sistema operativo**: `taskkill /F` a un `filex` **a mitad de conversión** deja el siguiente entrando en **551,9 µs**. Con `O_EXCL` habría un huérfano eterno y un censo de PID que en esta máquina ya se sabe que no se puede hacer bien (trampa 31).
4. **Cuesta 976,6 µs por conversión, el 0,249 %** de una conversión de 391,5 ms medida en la misma tanda. **Y el reparto es contraintuitivo: solo 713 µs son el candado; los otros ~215 son de un agujero propio que encontré midiendo** —dos escrituras de la misma ruta (nombre corto 8.3) daban **dos dueños del mismo fichero**— y que se cierra resolviendo el directorio.
5. **Lo que NO cubre está en §6, y lo primero es lo mismo que avisó L1: `%TEMP%` es POR USUARIO.** Dos usuarios de Windows, o la VM de WSL2, tendrían candados distintos. Y la detección **no distingue un lector de un escritor** — MEDIDO.

---

## 1. Lo que había, y por qué no bastaba

`filex/nucleo.py` tenía desde el hito 7 un `set` de destinos en curso con un `threading.Lock`. Estaba bien puesto —en el **núcleo**, no en la API, que es R10 funcionando— y su propio comentario declaraba el límite:

> **Alcance declarado, sin adornos: es un cerrojo DE PROCESO.** Dos procesos `filex` distintos —una API y un watcher, por ejemplo— siguen pudiendo pisarse. […] queda **PENDIENTE**.

**Y las pruebas no podían verlo.** `ApiConcurrencia` y `NucleoDestinoEnCurso` lanzan **hilos**, y un `set` en memoria los excluye a todos dentro del intérprete y a ninguno fuera. **Pasaban al 100 % con el agujero abierto.** Una prueba que no puede fallar por el fallo que dice cubrir no es una prueba de ese fallo; por eso lo primero de este encargo fue un fichero de pruebas que lanza `subprocess`.

---

## 2. La reproducción, entre procesos de verdad — **MEDIDO**

`bench/salidas-cerrojo/carrera_destino.py`, log completo en `logs/carrera_destino.log`.

Tres procesos, las **tres entradas del hito 7 §5.3** (`tipico.png` 42 855 B, `tipico.jpg` 87 954 B, `patologico_16bit.tif` 72 001 016 B), **un solo `salida.webp`**. El disparo es una **cita en dos tiempos**, no un `sleep`: cada obrero construye su `FileX` —que es lo caro, 23,6 s en frío— y solo entonces avisa; el padre espera a los tres y suelta el pistoletazo tocando un fichero. Con un `sleep` se estaría midiendo el arranque del intérprete.

### 2.1 El ANTES (`FILEX_CERROJO_DESTINO=proceso`, que es exactamente el hito 7)

| Proceso | entrada | veredicto | `bytes` declarados | `sha256` declarado |
|---|---|---|---:|---|
| pid 30040 | `tipico.png` | **ok** | **13 516** | `fc2234fdc39cb987` |
| pid 21016 | `tipico.jpg` | **ok** | **14 402** | `f03f6604a420ec42` |
| pid 34724 | `patologico_16bit.tif` | **ok** | **647 580** | `dc117310b229bc4c` |
| | **EN EL DISCO** | | **647 580** | `dc117310b229bc4c` |

**Tres éxitos, un fichero, y dos respuestas que describen un fichero que ya no existe.** Las tres cifras coinciden con las del hito 7 al byte, por una ruta independiente y con superficies distintas (allí la API, aquí la CLA del núcleo). **El cerrojo de proceso estaba puesto y activo en los tres**: no se saltó ninguna defensa, es que la defensa no llegaba.

### 2.2 El DESPUÉS (`maquina`, el defecto), tres pasadas

| Pasada | éxitos | ganador | en el disco | éxitos que mienten |
|---|---:|---|---:|---:|
| 1 | **1** | `patologico_16bit.tif` | 647 580 B | **0** |
| 2 | **1** | `patologico_16bit.tif` | 647 580 B | **0** |
| 3 | **1** | `tipico.png` | 13 516 B | **0** |

Los dos perdedores devuelven `ok=False` con **`otra conversión está escribiendo ya esa ruta de salida`**, en **10,7–15,8 ms** (el tiempo de construir el plan; el candado se toma después de saber que hay camino). **El ganador no es determinista; el invariante sí** — lo mismo que observó el hito 7 entre hilos, ahora entre procesos.

> **El motivo NO es opaco, y sigue sin deber serlo (R4).** El cliente **pidió** esa ruta: nombrarla no le dice nada que no supiera.

---

## 3. Qué mecanismo, y por qué NO los otros dos — **MEDIDO**

Los tres candidatos tienen semántica distinta y la documentación no basta. `bench/salidas-cerrojo/sonda_primitivos.py` los sondea **en ejecución**, con un hijo que toma el candado y se queda quieto (`logs/sonda_primitivos.log`):

| Prueba, desde OTRO proceso | `O_CREAT|O_EXCL` | `msvcrt.locking(LK_NBLCK)` | `os.replace(p, p)` |
|---|---|---|---|
| Con el dueño **vivo** | `errno 17 File exists` | `errno 13 Permission denied` (54,1 µs) | `WinError 32` |
| Con el dueño **muerto** por `taskkill /F` | **sigue fallando: huérfano eterno** | **OK en 22,1 µs** | OK |
| ¿Metadatos legibles desde fuera? | sí | **sí** (`b'pid=27884\r\n'`) | — |

**Se elige el candado de rango de bytes por la fila del medio.** `taskkill /F` **no ejecuta ningún `finally`** —es el defecto 2 del lock de GPU viejo, que hacía esperar **900 s** al siguiente agente (`bench/lock-de-maquina.md` §1.2)—, y aquí no hace falta escribir una sola línea de recuperación de huérfanos: **lo suelta el sistema operativo**. Eso además evita tener que preguntar por el PID del dueño, que es justo lo que la **trampa 31** dice que en esta máquina no se puede automatizar bien.

**Un detalle que parece cosmético y no lo es:** el byte que se bloquea está en el offset `1 << 30`, muy lejos del principio. Así el candado excluye **y** los metadatos (`pid`, epoch, ruta) **siguen siendo legibles desde otro proceso** mientras está tomado — comprobado en el paso 2 de la sonda. Un candado que además impidiera leer quién lo tiene sería un candado que no se puede depurar.

**Dónde vive:** `%TEMP%/filex-destinos/<sha256(clave)[:32]>.lock`, con `%TEMP%` = `C:\Users\krato\AppData\Local\Temp` (medido por L1 en `lock-de-maquina.md` §2.1). Se resume la ruta en vez de usarla como nombre por dos motivos: una ruta de 200 caracteres no cabe como nombre de fichero, y el directorio de candados es común, así que **no debe filtrar a qué ficheros está accediendo otro**. Sobrescribible con `FILEX_CERROJO_DIR`.

---

## 4. El dueño muerto — **MEDIDO** (`logs/huerfano_y_deteccion.log`, escena A)

Un `filex` de verdad convirtiendo el TIFF de 72 MB (≈1,3 s), matado con `taskkill /F /T` a los 350 ms:

```
candado tomado por el que va a morir: True  -> '13968\t1787885017\td:\work\...\sal_a\s.webp'
muerto con taskkill /F (rc=1); murió a mitad de la conversión: True (dijo '')
el fichero de candado sigue ahí: True
el SIGUIENTE toma el candado: True   en 551.9 us
y CONVIERTE de verdad: {'ok': True, 'veredicto': 'ok_parcial', 'ms': 361.5}
en el destino: ['s.webp']
```

La comprobación de *«murió a mitad»* no es adorno: si el hijo hubiera terminado, su `finally` habría soltado el candado y la escena no probaría nada. Se verifica que **no llegó a imprimir su línea de resultado**.

**El fichero de candado sobrevive al `taskkill`; el candado no.** Esa es toda la diferencia, y es la que convierte una espera de 900 s en 551,9 µs.

### 4.1 Y lo que el `taskkill` SÍ se deja: un desechable de R18 — **MEDIDO**

```
desechables de R18 que el taskkill dejó sin borrar: 1
```

`DirectorioDeTrabajo` borra su `mkdtemp` en el `finally` de `convertir()`, y un `taskkill /F` no ejecuta `finally`. **El cerrojo se cura solo; R18 no.** No lo arreglo aquí —no es mi encargo y el fichero es del hito 1—, pero queda medido: **matar un `filex` a mitad deja exactamente un directorio en `%TEMP%` por conversión en vuelo.** Sin límite superior si alguien mata muchos.

---

## 5. El que no coopera: la mitad de DETECCIÓN — **MEDIDO** (escena B)

Es la lección que `bench/lock-de-maquina.md` §0.1 dejó escrita con todas las letras:

> Mover el lock a `%TEMP%` **no cierra el caso que lo motivó**: la sesión de `D:\Work\research\ASR` **no iba a tomar ese fichero jamás**, esté donde esté. Un lock **excluye a quien coopera**.

Aquí el equivalente exacto del intruso de ASR es **un proceso que no es FileX y tiene abierta la ruta de salida** — un navegador bajando un fichero, un editor, otro conversor. No va a tomar el candado. Un proceso arranca, abre `s.webp` en modo `wb`, escribe 4 014 B y se queda quieto; entonces se lanza FileX contra esa misma ruta:

| Modo | qué dice FileX | el fichero del tercero | |
|---|---|---|---|
| `proceso` (hito 7) | **`ok`**, `ok_parcial`, 295,9 ms | 4 014 B `65701abe…` → **13 516 B `fc2234fd…`** | **PISADO** |
| `maquina` (defecto) | **`ok=False` — «otro proceso tiene abierta esa ruta de salida»**, 4,9 ms | 4 014 B `65701abe…` → **4 014 B `65701abe…`** | **intacto** |
| `maquina`, **control sin tercero** | `ok`, 291,5 ms, 13 516 B | — | convierte |

**El caso `proceso` es el peor de todo el informe** y no lo había mirado nadie: `shutil.move` sobre un destino que existe **no** hace `rename` —falla— sino que cae a `copy2`, que **sobrescribe en silencio**. FileX destruye el fichero de otro proceso y devuelve éxito.

El mecanismo de la detección es la **trampa 27** usada al revés: `open(p,'rb')` funciona en los cuatro estados y no prueba nada; `os.replace(p, p)` falla con `WinError 32` en cuanto otro proceso lo tiene abierto, y **es el único cerrojo real en Windows**. Se comprueba en **dos sitios**: al reservar (para no gastar 300 ms y negarse igual) y **justo antes del `shutil.move`**, que es la ventana más estrecha posible.

### 5.1 Y un límite de la detección que hay que declarar, porque amplía la trampa 27 — **MEDIDO**

`sonda_primitivos.log` §5: un hijo que **solo abre el fichero para LEER** (`open(p,'rb')`, sin escribir un byte) hace fallar igualmente `os.replace(p, p)` con `WinError 32`.

> **`os.replace(p,p)` NO dice «alguien lo está escribiendo». Dice «alguien lo tiene abierto».**

La trampa 27 lo enuncia como *«otro proceso escribiendo»* y **eso es más estrecho que lo que el primitivo mide**. Consecuencia práctica: un visor de imágenes con la salida abierta hace que una conversión legítima se niegue. **Es un falso positivo posible, y se acepta a sabiendas**: negarse cuesta un reintento; pisar cuesta el fichero de otro. Es la misma decisión que tomó L1 con `GPU_GUARD=abortar`.

---

## 6. Lo que este cerrojo **NO** cubre — sin adornos

1. **`%TEMP%` es POR USUARIO, no por máquina.** Es el mismo aviso 1 de L1 y no lo he cerrado: dos usuarios de Windows tendrían dos directorios de candados. Para este proyecto es irrelevante (todos los agentes corren como `krato`) y hay `FILEX_CERROJO_DIR` para apuntarlos al mismo sitio, pero **«de máquina» en el título significa «de máquina y de usuario»**. Un **mutex con nombre** en el espacio `Global\` sería lo correcto y exige el privilegio `SeCreateGlobalPrivilege`, que un proceso interactivo sin elevar no tiene. **PENDIENTE.**
2. **No cruza a la VM de WSL2.** El `/tmp` de Ubuntu es otro sistema de ficheros. Mismo límite que el lock de GPU.
3. **La detección es un INSTANTE, no una vigilancia.** Entre el `os.replace(p,p)` y el `shutil.move` hay una ventana. Se ha hecho lo más estrecha que se puede —son las dos líneas siguientes— pero no es cero, y quien llegue dentro de esa ventana pisa igual. **Cerrarlo del todo exigiría abrir el destino con `FILE_SHARE_NONE` y escribir a través de ese handle**, que en Python no se puede sin `ctypes` y `msvcrt.open_osfhandle`. **PENDIENTE, declarado.**
4. **La detección no distingue un LECTOR de un ESCRITOR** (§5.1). Falso positivo posible.
5. **En POSIX la detección no existe.** `os.replace(p, p)` allí siempre funciona, así que `destino_ocupado_por_un_tercero` devuelve `False` sin mirar. La **exclusión** sí funciona en POSIX (`fcntl.flock`). Es el mismo pendiente que `_estable_en_disco` del watcher (`hito7-superficies.md` §7.3).
6. **En POSIX el fichero de candado no se barre.** En Windows un borrado que tiene éxito **demuestra** que nadie lo tenía abierto (medido), así que barrer es seguro; en POSIX el borrado siempre funciona y abriría la carrera clásica de «borro el candado de otro». Allí el fichero se queda, y son ~120 B por destino distinto. **PENDIENTE.**
7. **No protege el fichero DESPUÉS de escrito.** El candado se suelta en el `finally`; lo que pase con la salida un milisegundo más tarde no es de este cerrojo.
8. **Y el que no está en la lista porque lo encontré midiendo: el ALIAS DE RUTA.** Estaba abierto, está cerrado, y va en §6.1 por lo que enseña.

### 6.1 Un agujero propio, encontrado y cerrado: el nombre corto 8.3 — **MEDIDO**

El hito 7 probaba que la clave del destino usa `normcase` (R3), de modo que en Windows no se escapa cambiando la caja de una letra. **Eso no basta**, y no hace falta ningún truco exótico para demostrarlo:

```
largo : C:\Users\krato\AppData\Local\Temp\filex-aliaslargisimo-t0huurpm\salida.webp
alias : C:\Users\krato\AppData\Local\Temp\FI09A7~1\salida.webp
clave largo: c:\users\krato\appdata\local\temp\filex-aliaslargisimo-t0huurpm\salida.webp
clave alias: c:\users\krato\appdata\local\temp\fi09a7~1\salida.webp
MISMA CLAVE: False
reserva largo: True   reserva alias: True   -> DOS DUEÑOS: True
```

**Dos dueños del mismo fichero**, que es exactamente lo que el cerrojo viene a impedir, y el nombre corto 8.3 lo genera Windows solo. Un `subst`, un enlace de directorio o una UNC harían lo mismo. `abspath` **no** los resuelve; `realpath` **sí**. Cerrado resolviendo el **directorio** y volviendo a pegarle el nombre:

```
MISMA CLAVE: True
reserva largo: True   reserva alias: False   -> DOS DUEÑOS: False
```

**Se resuelve el directorio y NO la ruta entera, a propósito.** El destino puede no existir al reservar y sí existir al soltar; una clave que se mueve entre las dos llamadas dejaría el candado tomado hasta que muera el proceso. El precio de esa decisión es que **un destino que sea un enlace a otro fichero sigue dando dos claves**. **PENDIENTE**, y es un caso mucho más raro que un nombre 8.3.

Prueba: `pruebas/test_cerrojo.py::AliasDeRuta`.

---

## 7. Lo que cuesta — **MEDIDO**, n = 20 000 por celda, todo en la MISMA tanda

`bench/salidas-cerrojo/coste_cerrojo.py` → `coste.json`, `logs/coste_cerrojo.log`.

| Operación | mediana | p90 | % de una conversión |
|---|---:|---:|---:|
| `reservar+soltar` **[proceso]** (solo el `set`) | **223,0 µs** | 356,0 | 0,057 % |
| `reservar+soltar` **[maquina]** (candado de fichero) | **936,2 µs** | 1 344,9 | 0,239 % |
| `reservar+soltar` **[ninguno]** | 271,1 µs | 399,6 | — |
| detección, **destino que existe** | 138,7 µs | 208,8 | — |
| detección, **destino que no existe** (el caso normal) | 20,2 µs | 26,6 | — |
| **conversión `png→webp` completa** (n=11) | **391,5 ms** | 414,0 | 100 % |
| **TOTAL por conversión** (reserva + 2 detecciones) | **976,6 µs** | | **0,249 %** |

*(Sobreescribiendo un destino que ya existe, las dos detecciones cuestan 277,4 µs en vez de 40,4 y el total sube a 1 213,6 µs, el 0,31 %.)*

**Testigos de ruido:** deriva monohilo **0,97**; testigo de proceso **38,1 → 32,3 ms**, sin agotar el tope de 20 s → **`limpia`**. *(Con la sesión remota activa; el testigo no la ve porque no hay contención de CPU en esta tanda.)*

### 7.1 La salvedad obligatoria, y una corrección al número que se publicó

**El hito 7 publicó 3,2 µs y el 0,0013 %** para `reservar+soltar`. **Aquí el mismo modo `proceso` da 223,0 µs.** No es una regresión del `set`: es que **la clave dejó de calcularse con `abspath` y pasa a resolver el directorio** (§6.1), y eso son ~215 µs de `realpath`. **Las cifras absolutas de tandas distintas no son comparables**, pero esta diferencia no es de tanda: es de código, y hay que decirlo así.

**El reparto, entonces:**

| Trozo | µs | qué compra |
|---|---:|---|
| `set` + `abspath` (lo del hito 7) | ~8 | exclusión entre hilos |
| **`realpath` del directorio** | **~215** | que un alias de ruta no dé dos dueños |
| **candado de fichero** | **~713** | exclusión entre procesos |
| **2 × detección** | **~40** | que no se pise a un tercero |

**El 0,249 % es asumible y la alternativa medida es peor**, así que no se optimiza. Si alguien lo necesitara, el trozo barato de quitar es el `realpath`, cacheando el directorio: los destinos de un watcher comparten directorio. **PENDIENTE, y no hace falta hoy.**

### 7.2 Dónde se van los 713 µs del candado — **MEDIDO** (tanda aparte, `desglose.json`)

| Cada fila añade UNA operación | µs |
|---|---:|
| 1. `open(O_CREAT)` + `close` | 57,0 |
| 2. + `locking`/`flock` | 63,1 |
| 3. + `ftruncate` + `write` (metadatos) | **1 195,9** |
| 4. + `unlock` + `remove` — **el ciclo entero** | **488,45** |
| 5. ciclo **sin** el `remove` final | 1 117,5 |
| 6. ciclo entero **sin** los metadatos | 312,1 |

**Dos cosas contraintuitivas, y la segunda es la interesante:**

- **El candado en sí cuesta ~6 µs** (fila 2 − fila 1). Todo lo demás es el fichero.
- **Borrar el candado al soltarlo hace el ciclo ×2,3 MÁS RÁPIDO** (1 117,5 → 488,45). No es un ahorro de limpieza: sin el `remove`, el siguiente `open(O_CREAT)` cae sobre un fichero que **ya tiene contenido**, y el `ftruncate` a 0 se paga entero. Con el `remove`, el fichero siguiente nace vacío. **La limpieza de `%TEMP%` sale gratis y encima paga.**
- Los metadatos cuestan **176 µs** (fila 4 − fila 6). Se dejan: es lo que permite saber quién tiene un candado sin adivinarlo, que es media trampa 31.

---

## 8. Que el caso normal —el 99 %— no se rompe — **MEDIDO**

Un cerrojo que arregla el 1 % rompiendo el 99 % no es un arreglo.

| Comprobación | Resultado |
|---|---|
| **La suite entera** | **163 passed, 6 skipped** en 62,1 s *(base: 151 + 6; +11 de `test_cerrojo.py`, +1 en `NucleoDestinoEnCurso`)*. **Cero movimientos en las 151 anteriores.** |
| Tres conversiones **seguidas** al mismo destino, un proceso | 3 de 3 `ok`, 1 fichero |
| El destino **recién escrito por FileX** no se detecta como ocupado | `False` — el falso positivo que lo habría roto todo |
| El destino que **no existe** no se detecta como ocupado | `False` |
| El modo **por defecto** es el seguro | `maquina`, comprobado en un intérprete limpio sin la variable |
| **La huella del sondeo** (`filex/huella.py`, commit `13181f6`) | **`caducados: {}` · `{'real': 210, 'nominal': 5}` — idéntico antes y después.** `nucleo.py` no está en ninguno de los tres componentes, como declaraba su autor |

---

## 9. Las pruebas, y la que falla sin el arreglo

`pruebas/test_cerrojo.py`, **11 pruebas, 9,7 s**. Todo se lanza con `subprocess`, que es **lo único que distingue un hilo de un proceso**.

| Clase | Qué cierra |
|---|---|
| `CarreraEntreProcesos` | §2. Dos procesos, dos entradas, un destino, con cita en dos tiempos |
| `DuenoMuerto` | §4. `taskkill /F` y la recuperación; y que el fichero de candado no queda de basura |
| `TerceroQueNoCoopera` | §5. Las dos direcciones: sin detección **pisa**, con detección **no toca** |
| `UnSoloProceso` | §8. El caso normal, incluido que el defecto es el seguro |
| `AliasDeRuta` | §6.1. El nombre corto 8.3 |

**La prueba que falla sin el arreglo, ejecutada de verdad contra el `nucleo.py` del hito 7** (`git checkout HEAD -- filex/nucleo.py`, ejecutar, restaurar):

```
FAILED CarreraEntreProcesos::test_con_el_cerrojo_de_maquina_solo_uno_gana
E  AssertionError: 2 != 1 : esperaba un solo éxito:
   [{'ok': True, 'bytes': 13516}, {'ok': True, 'bytes': 14402}]
1 failed, 1 passed
```

Y la que **pasa** con el código viejo es `test_sin_el_cerrojo_de_maquina_los_dos_procesos_devuelven_ok`, que documenta el estado anterior. **No es una prueba de que el fallo «podría» pasar:** con el cerrojo de proceso, dos procesos distintos **nunca** se ven, así que los dos éxitos son deterministas.

---

## 10. Un tropiezo de entorno que no es de nadie de este encargo, y cuesta 15 rojos

**El worktree recién creado trae `corpus/` como PUNTEROS de Git LFS**, no como ficheros. `corpus/imagen/tipico.png` pesaba **130 B** y `magick` respondía `improper image header`. **La suite base daba `15 failed, 136 passed, 6 skipped`** y ninguno de los quince fallos tenía que ver con el código.

```
$ git lfs checkout
Checking out LFS objects: 100% (39/39), 266 MB | 9.8 MB/s, done.
$ python -m pytest pruebas/ -q
151 passed, 6 skipped
```

`CLAUDE.md` §6 ya lo dice (*«tras clonar: `git lfs pull`»*) pero **no dice «tras crear un worktree»**, y es donde muerde: un agente nuevo ve 15 rojos que parecen suyos. **MEDIDO**, y propuesto abajo.

---

## 11. Propuestas para `CLAUDE.md` — **NO APLICADAS** (van AL FINAL, nunca en medio)

La última trampa es la **32**. Estas serían la **33** y la **34**. Y la **26** necesita cambiar su última frase, que ha dejado de ser verdad.

> **Cambio en la trampa 26**, última frase: ~~«**Es un cerrojo DE PROCESO: dos procesos `filex` distintos siguen pisándose, y eso sigue PENDIENTE.**»~~ → **«Cerrado el 23/08 entre procesos (`bench/cerrojo-de-maquina.md`): candado de fichero en `%TEMP%/filex-destinos/` **más** detección del ocupante ajeno. **La exclusión sola no bastaba** —FileX pisaba el fichero abierto de un tercero devolviendo `ok`, 4 014 B → 13 516 B— y sigue siendo **de usuario**, no de máquina.»**

> **33. Un cerrojo que solo excluye a quien lo toma resuelve la mitad del problema, y la otra mitad se llama DETECCIÓN — MEDIDO** (`bench/cerrojo-de-maquina.md`). Es la misma forma que el lock de GPU (trampa del §1 de `CLAUDE.md`) sobre otro recurso, y esta vez con el caso ajeno reproducido: con solo exclusión, FileX **sobrescribió el fichero que otro proceso tenía abierto y devolvió `ok`** (4 014 B → 13 516 B), porque `shutil.move` sobre un destino existente **no hace `rename`: cae a `copy2`, que pisa en silencio**. La detección es la trampa 27 al revés —`os.replace(p, p)` es el único cerrojo real en Windows— y **cuesta 20,2 µs** cuando el destino no existe. **Y amplía la trampa 27: `os.replace(p,p)` no dice «alguien lo está escribiendo», dice «alguien lo tiene ABIERTO»** — un hijo que solo hace `open(p,'rb')` dispara el mismo `WinError 32` (MEDIDO). Dos elecciones más, medidas: el candado es de **rango de bytes** (`msvcrt.locking`/`flock`) y no `O_CREAT|O_EXCL` porque **lo suelta el sistema operativo** —un `taskkill /F` a mitad de conversión deja al siguiente entrar en **551,9 µs**, frente a un huérfano eterno—; y **`normcase(abspath)` NO identifica un destino**: el nombre corto 8.3 que genera Windows solo daba **dos dueños del mismo fichero** (`…\filex-aliaslargisimo-t0huurpm\` y `…\FI09A7~1\`), y hace falta `realpath` **del directorio** (~215 µs). Coste total: **976,6 µs, el 0,249 %** de una conversión.

> **34. Un worktree nuevo trae `corpus/` como PUNTEROS de LFS, y son 15 rojos que no son tuyos — MEDIDO** (`bench/cerrojo-de-maquina.md` §10). `corpus/imagen/tipico.png` pesa **130 B**, `magick` dice `improper image header` y la suite da **`15 failed, 136 passed`** sin que nadie haya tocado el código. `git lfs checkout` en el worktree (266 MB, del almacén local, sin red) lo deja en **`151 passed, 6 skipped`**. **Antes de creerte un rojo, mira si el corpus son punteros.**

---

## 12. Lo que abre este informe

| # | Pendiente | Dónde |
|---|---|---|
| 1 | **Cerrojo de MÁQUINA de verdad**: mutex con nombre en `Global\`, o un directorio de candados fuera de `%TEMP%`. Hoy es **por usuario** — el mismo pendiente 1 de `lock-de-maquina.md` | §6.1 |
| 2 | **La ventana entre la detección y el `move`.** Se cierra abriendo el destino con `FILE_SHARE_NONE` vía `ctypes` | §6.3 |
| 3 | **POSIX**: sin detección y sin barrido del candado | §6.5, §6.6 |
| 4 | **Un destino que sea un ENLACE a otro fichero** sigue dando dos claves | §6.1 |
| 5 | **`taskkill /F` deja un desechable de R18 por conversión en vuelo.** No es de este encargo, pero está medido | §4.1 |
| 6 | **El mismo primitivo sirve para el lock de GPU en Python** —fila **C38** de `lock-de-maquina.md`, «0 de 15 arneses `.py` toman el lock»—. `_tomar_candado`/`_soltar_candado` son 40 líneas y no dependen de nada de `filex`: **extraerlas a `filex/cerrojo.py` o `bench/lib/gpu_lock.py` es una mudanza, no un diseño** | §3 |

---

## 13. Ficheros

| Fichero | Qué es |
|---|---|
| `filex/nucleo.py` | El cerrojo, +251 / −6. Las dos mitades y `_clave_destino` |
| `pruebas/test_cerrojo.py` | 11 pruebas **entre procesos**. 9,7 s |
| `pruebas/test_hito7.py` | Solo la clase `NucleoDestinoEnCurso`: +1 prueba y la nota de alcance |
| `bench/salidas-cerrojo/sonda_primitivos.py` + `logs/` | §3 y §5.1: los tres primitivos sondeados en ejecución |
| `bench/salidas-cerrojo/carrera_destino.py`, `carrera.json`, `logs/` | §2: la reproducción y las tres pasadas del cierre |
| `bench/salidas-cerrojo/coste_cerrojo.py`, `coste.json`, `logs/` | §7: el coste, con los dos testigos de ruido |
| `bench/salidas-cerrojo/desglose_cerrojo.py`, `desglose.json`, `logs/` | §7.2: dónde se van los µs |
| `bench/salidas-cerrojo/huerfano_y_deteccion.py`, `.json`, `logs/` | §4 y §5: dueño muerto y tercero que no coopera |
| `bench/salidas-cerrojo/MANIFIESTO.md` | Cómo se reproduce todo |

**Ninguna salida binaria.** Todo son `.py`, `.json`, `.md` y logs de texto. El directorio desechable (`bench/salidas-cerrojo/desechable/`) se lista y se borra en cada arnés; al terminar, `git status` no muestra un solo fichero suelto en la raíz (R21 comprobado).

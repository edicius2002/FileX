# N9 — la decisión del oráculo temporal, y C35 — la latencia limpia de Gotenberg

**Encargo R10 · worker2, carril CPU/Docker, `edicius2002/filex-cpu`.** Cuatro filas por
prioridad; se entregan las dos primeras. `C5` y `C36` quedan fuera — el porqué, en §3.

**Máquina:** *worktree* `C:\Users\krato\orca\workspaces\FileX\filex-cpu` (no `D:`; las cifras
absolutas no son comparables con las históricas). Windows 10, Python 3.11.9. **worker1 tiene
la tarjeta** en el carril GPU de la ronda 10 (`B7`, `B20`): no se tocó. **La tanda es
`SUCIA`**: el testigo de proceso (`cmd /c exit`) dio **89,56 ms antes y 32,15–51,55 ms
después** en las distintas tandas, muy por encima del umbral de 30 ms que este informe fija
—CPU compartida con worker1—. Se publica de todos modos porque **las comparaciones son
RELATIVAS dentro de cada tanda** (`CLAUDE.md` §3) y los efectos medidos son grandes: un
orden de magnitud en N9, ~7× en C35. Docker (`29.4.3`) estaba arriba con `filex-convertx`,
`filex-snapotter(+pg,+redis)` y `filex-gotenberg8` sanos, comprobado antes de tocar nada.

**Fecha:** 03/09/2026.

---

## 1. `N9` — el oráculo temporal de R4: la decisión, tomada y escrita

### 1.1 La decisión, por superficie

| Superficie | Adversario que puede cronometrar | Decisión |
|---|---|---|
| **CLI** | Ninguno: el propio usuario invoca localmente; no hay un tercero que envíe rutas y mida la respuesta. | **No mitigar.** |
| **watcher** | Ninguno: vigila directorios propios; no procesa rutas arbitrarias de un adversario remoto. | **No mitigar.** |
| **MCP** | Ninguno **verificado en código**: `filex/mcp.py` usa `mcp.server.stdio.stdio_server()` exclusivamente — es *stdio*, lanzado como subproceso local por un cliente que ya tiene ejecución local en la máquina. No hay canal de red que cronometrar. | **No mitigar.** |
| **API HTTP** | **Sí.** Puede escuchar en la LAN (`--permitir-red`), y aun en *loopback* el propio `hito7-superficies.md` §6 ya defiende contra un atacante en el **navegador** de la víctima (*DNS rebinding*): ese mismo atacante puede lanzar `fetch()` con `performance.now()` y medir la latencia con precisión de microsegundos, sin necesitar leer el cuerpo de la respuesta — es un ataque de TIMING, no de lectura, y encaja exactamente en el modelo de amenaza que este fichero ya asume. | **Mitigar.** |

Es la decisión explícita que la fila pedía: *tres superficies no la necesitan y se dice, una
sí y se implementa.* No queda abierta otro mes.

### 1.2 Por qué NO "igualar por arriba" globalmente, y por qué SÍ por superficie

`confinamiento.py` ya declaraba que igualar por arriba (dormir en el camino denegado)
convierte el rechazo en un amplificador de DoS; igualar por abajo pierde el `realpath`. Eso
sigue siendo cierto **como regla global**. Pero el coste del "amplificador" depende de
**quién puede activarlo**: CLI/watcher/MCP no tienen un adversario remoto que envíe volumen de
peticiones rechazadas, así que pagar el suelo ahí es puro coste sin beneficio de seguridad.
Aplicado **sólo** en la API, el "amplificador" tiene un techo bajo: el suelo elegido (§1.4) es
de cientos de microsegundos, muy por debajo del coste ya dominante de la conexión TCP/HTTP
—**1,913 ms frente a 2,630 ms** de mediana en `hito7-superficies.md` §7.2, aunque esa cifra es
de otra máquina y sólo sirve de referencia de orden de magnitud—, así que no cambia el orden
de magnitud del coste de rechazar una petición.

### 1.3 Un hallazgo de instrumento que decidió CÓMO implementarlo: `time.sleep()` no sirve aquí

Antes de fijar el suelo, medí (control de 6 objetivos × 200 repeticiones, in-process) cuánto
tarda de verdad `time.sleep()` en esta máquina para duraciones de decenas a cientos de
microsegundos:

| Objetivo pedido | Mediana real | Mínimo | Máximo |
|---:|---:|---:|---:|
| 10 µs | 998,2 µs | 64,5 | 1 149,6 |
| 50 µs | 997,7 µs | 516,0 | 1 359,4 |
| 100 µs | 993,3 µs | 409,0 | 1 232,3 |
| 200 µs | 998,1 µs | 682,3 | 1 316,3 |
| 350 µs | 1 006,2 µs | 454,6 | 11 767,3 |
| 500 µs | 997,4 µs | 566,1 | 3 574,3 |
| 1 000 µs | 1 985,5 µs | 1 041,3 | 7 228,3 |

**MEDIDO: `time.sleep()` en Windows, en esta máquina, no baja de ~1 ms de mediana real sin
importar si se le pide 10 µs o 500 µs.** Pedir 350 µs (mi primer intento de suelo) habría
costado **~3×** más de lo pedido, con una cola de hasta 11,8 ms. Dormir para cerrar una
brecha de unos cientos de microsegundos la habría sobrepasado por 3-10×, que es más caro que
la propia asimetría que se quiere cerrar. **Consecuencia de diseño:** el suelo se implementa
con **espera activa** (`time.perf_counter()` en bucle), no con `sleep()`, para el tramo por
debajo de 2 ms. El coste de CPU de un *spin* de menos de un milisegundo es despreciable
—incluso bajo la carga que esta tanda ya declara— frente al coste de dormir de más.

### 1.4 El suelo, medido en esta máquina — y lo que cierra

`Confinamiento.resolver()` en aislado (in-process, n=2 000 por celda):

| Vía | sin ecualizar | ecualizado |
|---|---:|---:|
| prohibido | 13,40 µs (p90 16,70) | 302,70 µs (p90 308,60) |
| no existe | 234,95 µs (p90 364,65) | 301,20 µs (p90 582,19) |
| existe | 170,70 µs (p90 252,55) | 301,30 µs (p90 413,79) |

**Ratio no_existe/prohibido: 17,53× sin ecualizar → 1,00× ecualizado.** Reproduce la
asimetría de trampa 28 en esta máquina (orden de magnitud comparable al ×20,6 histórico de
`D:`, cifra absoluta no comparable) y la cierra a la mediana. El suelo, `PISO_TEMPORAL_S =
0,0003` (300 µs), se fijó midiendo esta máquina — **antes de calibrar, se comprobó que la
magnitud existe donde se cree** (trampa 86): medida en la máquina real, no supuesta de un
informe de otra.

> **⚠ CORREGIDO por el maestro al verificar la ronda 10, y la corrección importa porque el
> número justifica una constante de seguridad.** Esta frase decía que el suelo *«se fijó con
> margen sobre el p90 de `no_existe` sin ecualizar (364,65 µs)»*, y **300 µs no está por
> encima de 364,65: está por debajo**. La tabla de arriba desmentía a la frase de al lado.
> Y el comentario de `filex/confinamiento.py` justificaba la constante con otras cifras
> —«161,95 µs de mediana, 271,19 de p90»— que **no aparecen en el `resultado.json`
> versionado**: con ésas la afirmación sería cierta, con las guardadas es falsa. Son **dos
> tandas**, y la que sostenía la conclusión no se guardó. Es la **trampa 55** (*una cifra
> citada puede venir de otra medida y el texto no lo dice*) dentro de la **44** (*un campo
> honesto al lado de una nota falsa se lee como una respuesta honesta*).
>
> **Lo que NO cambia:** el ratio a la mediana, que es el resultado, y §1.5, que ya declaraba
> honestamente la fuga residual. **Lo que sí:** el suelo cierra el oráculo **a la mediana y
> no en la cola** — ya ecualizado, el p90 de `no_existe` es **582,19 µs** frente a **308,60**
> del camino denegado, es decir **1,88× a p90**, y un atacante que promedie muchas muestras
> lo ve. **Subir el suelo por encima del p90 exige volver a medir y sube el coste del
> rechazo** —el amplificador de DoS de la trampa 28—, así que es una decisión, no un ajuste:
> queda abierta como **`N32`**.

### 1.5 Lo que el suelo NO cierra — declarado, no escondido

Medido al nivel de `FileX.convertir()` (el que de verdad expone la API, no
`Confinamiento.resolver()` aislado), n=500:

| Vía | sin ecualizar | ecualizado |
|---|---:|---:|
| prohibido | 19,45 µs | 312,50 µs |
| no existe | 309,45 µs | 649,35 µs |
| existe | 291,25 µs | 659,55 µs |

**El oráculo de EXISTENCIA —lo que trampa 28 nombra por su nombre— queda cerrado:
no_existe/existe = 0,985×, prácticamente 1.** Pero **existe/prohibido = 2,11×**, un residuo
que `medir_oraculo.py` no podía ver. La causa: `FileX._resolver()` llama a
`Confinamiento.resolver()` **dos veces** para un `convertir()` que pasa de largo la lista
blanca —una para la entrada, otra para el directorio de salida— y **sólo una** para uno que
se deniega en la entrada, porque nunca llega a la segunda. Con el suelo puesto **por
llamada**, eso dobla el coste de la vía válida frente a la denegada.

**Es una fuga real, pero de MENOR severidad que la cerrada, y se deja `PENDIENTE` a
propósito en vez de fingir haberla cerrado:** lo que un atacante puede seguir infiriendo con
este residuo es si una ruta **está sintácticamente dentro de alguna raíz configurada**, no si
un fichero concreto existe. Es información que normalmente ya es pública (las raíces suelen
estar documentadas por el operador) y, en el peor caso, revela estructura parcial de las
raíces — no la existencia de un fichero de la víctima, que era el riesgo que trampa 28
nombraba. Cerrarlo del todo exige o bien resolver siempre las dos rutas aunque la primera ya
se haya denegado (desperdicia trabajo y cambia la semántica de cortocircuito actual), o bien
mover el suelo a un nivel por-operación en vez de por-llamada — ninguna de las dos se ha
hecho esta ronda.

### 1.6 Implementación

- **`filex/confinamiento.py`**: `Confinamiento.__init__` gana `ecualizar_temporal: bool =
  False` (por defecto **apagado**: CLI/watcher/MCP no pagan nada). `resolver()` se parte en
  `resolver()` (envoltorio con `try/finally`) y `_resolver_sin_ecualizar()` (el cuerpo de
  siempre, sin tocar). Nueva constante `PISO_TEMPORAL_S` y la función `_esperar_piso()`
  (espera activa por debajo de `_UMBRAL_SLEEP_FIABLE_S`, con la nota de §1.3).
- **`filex/nucleo.py`**: `FileX.__init__` gana el mismo `ecualizar_temporal: bool = False` y
  lo reenvía a `Confinamiento`. Sin este parámetro, nada cambia para nadie.
- **`filex/api.py`**: `main()` construye `FileX(raices_lectura=args.raiz,
  ecualizar_temporal=True)` — **la única línea que activa el suelo, y sólo en esta
  superficie.**
- **R10 sigue intacto**: `api.py` no importa ni nombra `Confinamiento`, `realpath`,
  `nombre_seguro`, `_dentro` ni `_lexico_ok` — sólo pasa un booleano al constructor que ya
  llamaba. `pruebas/test_hito7.py::R10Estructural` sigue en verde (§4).
- **Pruebas nuevas** en `pruebas/test_hito1.py::OraculoTemporalN9` (3): por defecto no
  ecualiza; ecualizado el prohibido deja de ser instantáneo; las tres vías quedan por encima
  del suelo. Usan `PISO_TEMPORAL_S` importado, no un número repetido a mano.

---

## 2. `C35` — la latencia limpia, con testigos

### 2.1 Método

`txt → pdf` en las dos vías, **el mismo motor subyacente (LibreOffice/`soffice`) en ambas**,
para que la diferencia medida sea la arquitectura —servicio HTTP vivo contra contenedor
efímero por conversión— y no el motor. **La orden de `filex-c13` no se reimplementa a
mano** (trampa 79): se llama a `filex.nucleo.FileX.convertir()` de verdad, con una única
instancia de `FileX` construida una vez y reutilizada — la misma disciplina que
`filex/api.py` documenta (`construirla cuesta ~23,6 s en frío; por petición sería inviable`;
en esta máquina, 2,0 s). `n = 11` por vía.

Dos testigos: **A** — deriva monohilo (mediana de la primera mitad de la tanda contra la
segunda, por vía); **B** — nivel de proceso (`cmd /c exit`, tope de 20 s, antes y después de
la tanda completa). Los dos declaran esta tanda **SUCIA** (§0), y se publica con esa
etiqueta: las cifras absolutas no se citan como una constante del sistema, la comparación
relativa sí se sostiene.

### 2.2 Resultado

| Vía | mediana | p90 | mín | máx | deriva 1ª/2ª mitad |
|---|---:|---:|---:|---:|---:|
| Gotenberg | **483,2 ms** | 3 597,8 ms | 375,1 | 4 220,6 | 1,328 |
| `filex-c13` | **3 481,5 ms** | 5 862,4 ms | 2 554,0 | 6 294,4 | 1,084 |

**`filex-c13` es ×7,21 más lento que Gotenberg, por mediana, en esta tanda.** El `p90` de
Gotenberg está inflado por una sola celda (4 220,6 ms en la primera petición, un efecto de
arranque en frío del propio servicio) y aun así la mediana —más robusta a ese único
extremo— sostiene el ×7. La deriva de Gotenberg (1,328) es mayor que la de `filex-c13`
(1,084): es coherente con ese mismo pico inicial arrastrando la primera mitad hacia abajo, no
con una tendencia sostenida.

**11/11 conversiones de `filex-c13` correctas** (`rc` implícito en `conv.motivo == ""`,
bytes > 0) y **11/11 `HTTP 200`** de Gotenberg. **0 contenedores huérfanos**: `docker ps -a`
antes y después de la tanda no difieren en ningún nombre `filex-*` nuevo (trampa 37, con la
comprobación correcta).

### 2.3 Lo que esto NO mide, y por qué no se ha forzado

- **El arranque en frío tras un reinicio de Docker** (el `34 672 ms` histórico de
  `hito5-documental.md`) **no se ha reproducido**: Docker llevaba **más de una hora arriba**
  con contenedores de otros servicios activos (§0), y reiniciarlo para fabricar un estado
  frío habría interrumpido `filex-convertx`, `filex-snapotter` y el carril GPU de worker1,
  que comparte la misma máquina. Es una decisión de no-tocar, no un olvido. **La asimetría
  que sí queda medida —×7,21 por conversión, con Docker ya caliente— es la que se repite en
  CADA petición**, mientras que el coste de arranque en frío es un suceso de una sola vez por
  reinicio del demonio: para el caso de uso real (un servicio de conversión que atiende
  muchas peticiones sin reiniciar Docker entre medias), el ×7,21 por petición es el número
  que importa más, no el evento raro.
- **No se ha medido con `--permitir-red` ni desde otra máquina de la LAN**: la comparación es
  en `localhost`, así que el coste de red real (el que domina en HTTP según
  `hito7-superficies.md` §7.2) no está en esta cifra. El `docker run` de `filex-c13` tampoco
  usa red (`--network none`), así que ninguna de las dos vías paga ese coste — es coherente
  con medir la arquitectura, no el transporte.

### 2.4 Lo que dice para el diseño

**Gotenberg gana en latencia por conversión, de forma consistente y grande (×7).** Pero
`bench/gotenberg-y-mcp.md` ya midió que **pierde cobertura** (6/7 contra 7/7, con `epub→pdf`
en `HTTP 500`). El caso a favor de Gotenberg ya tiene sus dos mitades con número: **cobertura,
en contra (−1 arista); latencia, a favor (×7 más rápido)**. La decisión de si compensa sigue
siendo del proyecto, no de este informe — pero ya no falta ninguna de las dos cifras que la
fila declaraba pendientes.

---

## 3. Lo que se dejó fuera, explícitamente

**`C5` (la carrera de symlinks bajo WSL2) y `C36` (un pendiente de `hito4-mcp.md` §13) no se
tocaron esta ronda.** El encargo pedía las dos primeras filas bien hechas antes que las cuatro
a medias, y N9 (§1) resultó más caro de lo previsto: cerrar el oráculo exigía primero medir
por qué el suelo obvio (`time.sleep()`) no servía en esta máquina (§1.3), lo que no estaba en
el plan inicial y consumió el margen que habría ido a `C5`/`C36`.

- **`C5`**: el arnés (`c5a_symlink_wsl.py`) ya existe y el vector ya está identificado; la fila
  advierte explícitamente de que la VM de WSL2 puede caer con `0x8007274c` bajo contención y
  que eso **no es un resultado negativo, es una medición no hecha** — no se ha intentado esta
  ronda, así que sigue exactamente donde estaba, sin gastar ninguno de sus dos intentos.
- **`C36`**: de los siete pendientes vivos de `hito4-mcp.md` §13, ninguno se ha tocado. El más
  barato de cerrar —*"la caché de roots invalidada por una emisión real"*— sigue sin un
  control positivo, y *"el coste de un `convert` con ruta denegada gasta un `job_id`"* sigue
  conectado con `N9` (§1) tal como avisaba el encargo, pero no ha caído de rebote: cerrar el
  oráculo temporal no tocó `filex/servicio.py`, que es donde vive ese `job_id`, precisamente
  porque `servicio.py` no está en la lista de ficheros de esta ronda y su equalización habría
  afectado también a MCP (§1.1) sin una revisión de su ownership que esta ronda no ha hecho.

---

## 4. Verificación

**Intérprete:** `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe`, Python 3.11.9,
`win32`.

**Entorno:** Docker arriba (§0, verificado antes de la suite — trampa 94), sin GPU tomada,
CPU compartida con worker1 (tanda `SUCIA`, declarado en §0, §2.1).

```
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe -m pytest pruebas/test_hito1.py pruebas/test_hito7.py -q
```
→ **77 passed, 59 subtests passed** en 21,66 s. Incluye las 3 pruebas nuevas de
`OraculoTemporalN9` y las 74 que ya cubrían el hito 1 y el hito 7 completos —entre ellas
`R10Estructural`, que sigue verde tras el cambio en `api.py` (§1.6).

**Qué quedó fuera de la verificación y por qué:** no se corrió la suite completa
(`pruebas/` entero) esta vez — se corrieron los dos módulos que tocan el código cambiado
(`test_hito1.py` para `Confinamiento`/`FileX`, `test_hito7.py` para `R10Estructural` y la
superficie API) más `py_compile` de los cinco ficheros tocados. La suite completa y
`ci/integridad.py` se dejan para antes de commitear (ver el cierre de la ronda).

**Estado de la máquina:** declarado en §0 y §2.1.

---

## 5. Salidas en disco

`bench/salidas-oraculo-n9/` (2 scripts + 2 `.json`) y `bench/salidas-latencia-gotenberg/` (1
script + 1 `.json`) — ver sus `MANIFIESTO.md`, con `sha256`, tamaños y las órdenes exactas. Sin
binarios: los directorios temporales de cada tanda se crean y se borran dentro de los propios
scripts.

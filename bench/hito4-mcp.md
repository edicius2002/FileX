# Hito 4 — la capa MCP de FileX

**Fecha:** 22 de agosto de 2026. Agente **K3**. Máquina: Windows 10 Home 19045,
12 núcleos, Python 3.11.9, **Claude Code 2.1.239**, `mcp 2.0.0` en un venv propio
(`.venv-mcp-filex`). Sesión de escritorio remoto activa: **todo SUCIA por
estructura**. Sin GPU. Código y datos crudos en `bench/salidas-hito4/`.

> **Convención.** Cada afirmación va **MEDIDO** (hay una salida literal que la
> respalda, con su fichero) o **PENDIENTE**. Donde contradice o matiza a un
> documento del proyecto, se dice y se señala.

> **Concurrencia declarada.** K1 (motor documental), K2 (mudanza del verificador)
> y M1 (GPU) trabajaban a la vez. **No he tocado ningún fichero suyo.** Dos de
> sus entregas cruzaron mis medidas y lo digo donde toca: `filex/verificador.py`
> apareció a las 08:10 y `filex/motor_contenedor.py` a las 08:58 — **todo lo que
> hay aquí entre 08:19 y 08:56 está medido con los tres motores nativos**.

> **`.mcp.json`:** se le añadió el servidor `filex` (es fichero mío en el
> encargo). **`~/.claude.json` no se tocó.** Las 15 ejecuciones contra el cliente
> real usaron `--strict-mcp-config --mcp-config <fichero propio>`, no la del
> proyecto.

---

## 0. Resumen ejecutivo

| # | Hallazgo | Veredicto |
|---|---|---|
| **1** | **El presupuesto de ≤1.200 tokens de catálogo NO se puede cumplir, y la quinta herramienta no tiene la culpa** | **REFUTADO con la curva completa.** El catálogo son **1.605 tok**; con las **cuatro del plan** serían **1.452** — también fuera. Lo que lo rompe son las dos reglas de cobertura: `description` por parámetro **460 tok** y `enum` del registro **337 tok**. Quitando las dos: **728 tok**, que es exactamente el catálogo estilo FastMCP con el que se midió **15–17 % de fallos silenciosos** |
| **2** | **«Cuatro herramientas» y «job_id al empezar» son incompatibles** | **Son cinco.** `PLAN-ORQUESTADOR.md` §4.4 fija cuatro y §5.2 fija que `convert` no bloquea, sin bifurcar; §5.3 añade que Tasks fue **eliminado de la especificación**. Con `convert` no bloqueante hace falta una herramienta que consulte el trabajo |
| **3** | **`list_targets` NO es el mecanismo que evita el fallo silencioso. Es uno de tres, y no el más usado** | **MATIZADO por ejecución.** 15/15 aciertos, **0 % de fallo silencioso** frente al 15–17 % de referencia — pero de las 9 peticiones fuera de cobertura, `list_targets` se llamó en **6**; en **2** actuó el **rechazo síncrono de `convert`** y en **1** bastó **leer el `enum`** sin llamar a nada |
| **4** | **La diferición del catálogo se confirma en 2.1.239, con servidor real y catálogo real** | **CONFIRMADO, 15/15.** El modelo tuvo que emitir `ToolSearch {"select:mcp__filex__convert,..."}` en **todas** las ejecuciones. La re-acotación de `bench/mcp-cabos-2.md` §4 aguanta el cambio de versión y deja de ser «un catálogo de sonda» |
| **5** | **W9 está abierto DENTRO del núcleo de FileX: se lee y se escribe por un flujo alternativo de datos** | **FALLO DE SEGURIDAD, MEDIDO.** `inspect` devuelve **72 B** de un ADS y `convert` escribe **94 B** en el ADS de un fichero ajeno, con `veredicto: ok`. `nombre_seguro()` existe, está probado… y **en todo el paquete solo lo llama `pruebas/test_hito1.py`**. Diff exacto en §8; con él, **61 pruebas en verde** |
| **6** | **La exención de R8 para `inspect` se sostiene, pero su número está inflado ×4–10** | **MATIZADO.** Los «0,04–0,06 ms» de `bench/mcp-cabos-2.md` §5.3 medían *abrir + leer 64 KiB*, no un `inspect`. El `inspect` real cuesta **0,21–0,59 ms**, y el «de 30× a más de 3.000×» pasa a **de 2,0× a 284×** sobre este corpus |
| **7** | **La equivalencia de latencia de R4, que el núcleo dejó PENDIENTE, queda CERRADA** | **MEDIDO, n=201:** «existe y prohibido» **6,5 µs** vs «no existe y prohibido» **6,4 µs** — razón **1,016**, mejor que el 1,36 de la referencia oficial. Mismo mensaje literal |
| **8** | **La predicción de arranque «~1 s» falla ×1,9, y el culpable no es lo que se pensaba** | **MEDIDO:** **1.882 ms**, de los cuales **1.601 ms son `import mcp`**. El sondeo de los motores son 524 ms y **no crece** al pasar de 3 a 6 motores |
| **9** | **`roots` está DEPRECADO en el protocolo 2026-07-28 (SEP-2577)** | **MEDIDO** en el `stderr` del servidor. R13 y la caché de roots de `bench/mcp-cabos-2.md` §2 se apoyan en una capacidad que la especificación retira. Funciona hoy porque Claude Code negocia `2025-11-25` |
| **10** | **`PRUEBAS-MCP-REFS.md` no aporta nada nuevo: está enteramente contestado** | Se me entregó como «recuperado de ramas borradas, nadie lo ha usado». **Su propio sucesor lo dice en la línea 6:** *«Este documento sustituye a `PRUEBAS-MCP-REFS.md`»*. Sus 6 preguntas transversales están **las 6 cerradas** en `RESULTADOS-MCP.md` §2 |

---

## 1. Qué se entrega

| Fichero | Qué es |
|---|---|
| `filex/mcp.py` | El servidor. **988 líneas, cero validación propia de rutas** — y `subprocess` no aparece ni una vez |
| `pruebas/test_hito4.py` | **553 líneas, 31 pruebas**: 29 en verde y **2 fallos esperados a propósito** (el W9 del §5) |
| `bench/salidas-hito4/**` | 7 arneses, 7 JSON de resultados y 15 trazas `stream-json`. 628 KB, todo texto |
| `.mcp.json` | Alta del servidor `filex`, con `--raiz` del proyecto |

**Arquitectura:** toda la lógica de las cinco herramientas vive en
`filex.mcp.Servicio`, que **no importa el protocolo**. `construir()` le pone
encima las 40 líneas de MCP. Es lo que permite que 29 de las 31 pruebas corran
sin levantar un servidor, y lo que hace evidente —no argumentable— que aquí no
hay una segunda copia de la validación.

---

## 2. Las cinco herramientas, y por qué no son cuatro — **hallazgo 2**

`PLAN-ORQUESTADOR.md` §4.4 fija **cuatro**: `convert`, `inspect`,
`list_targets`, `batch`. Y §5.2 fija, con evidencia independiente y en negrita:

> **No bloquea. Nunca condicionado a un booleano, nunca bifurcando entre «rápido
> bloquea» y «lento devuelve asa»: una firma, un comportamiento.**

…porque un clip de **5 segundos** superó los **900 s** del timeout del cliente y
la conversión ya estaba hecha en disco. Y §5.3 remata: **Tasks (SEP-1686) fue
eliminado de la especificación**, así que `job_status` / `job_result` /
`job_cancel` hay que construirlos enteros.

**Con `convert` no bloqueante, alguien tiene que consultar el trabajo, y con
cuatro herramientas no cabe.** No es una decisión de gusto: son dos requisitos
del mismo documento que no se pueden satisfacer a la vez.

La resolución elegida —y su precio, medido— es **una sola herramienta `job` con
un `accion: enum[estado, resultado, cancelar]`**, en vez de las tres de SEP-1686.
Cuesta **153 tokens**; las tres por separado costarían del orden de 400.

> **Lo que se conserva no es el número, es lo que está medido.** El propio §4.4
> dice que *«el presupuesto se fija en tokens de catálogo, no en número de
> herramientas»* (el coste por herramienta varía **×11**), y las 540 ejecuciones
> de `bench/saturacion-herramientas.md` **refutaron** que un catálogo grande
> elija peor: 27 herramientas acertaron **100 %/98 %** frente al **85 %/77 %** de
> 8, con **0 %/2 %** de elecciones trampa frente al **15 %/17 %**. Un catálogo de
> cinco no tiene ningún problema conductual medido.

### Lo que hace cada una

| Herramienta | Qué hace | Tokens |
|---|---|---:|
| `convert` | Convierte y verifica. Devuelve `job_id` **al empezar**, con el camino y el aviso de rasterización ya dentro. **Falla en el acto** si no hay camino | 653 |
| `inspect` | Cabeceras en proceso, en sitio. Exento de R8 y R18 | 129 |
| `list_targets` | Qué conversiones existen de verdad. Con destino: el camino, los motores, la evidencia y lo que se pierde | 309 |
| `batch` | Varias entradas, un destino, un trabajo | 359 |
| `job` | `estado` / `resultado` / `cancelar`. **Nunca bloquea** | 153 |

**El `enum` sale del registro, la herramienta no.** Es el criterio de aceptación
del hito, y está probado de la forma dura (`test_un_motor_nuevo_no_toca_este_fichero`):
se inyecta una arista con un motor inventado y el `enum` crece **sin que el
número de herramientas cambie**. Generar una herramienta por motor es el
mecanismo exacto que produce las 27 planas de `video-audio-mcp`, de las que
**13 son casos particulares de 2**.

Y el criterio se comprobó solo, sin querer: **a las 08:58 apareció
`filex/motor_contenedor.py`** (K1) con LibreOffice, Pandoc y Calibre. El
catálogo pasó de **1.503 a 1.605 tokens** y el grafo de **156 a 215 aristas**,
**sin una línea tocada en `filex/mcp.py`**. **Tres motores nuevos cuestan +102
tokens de catálogo (+6,8 %) y cero herramientas nuevas** — MEDIDO.

### Un cambio que salió de la sonda: `convert` falla en el acto

La primera versión devolvía un `job_id` **también** cuando no había camino, y el
modelo se enteraba dos turnos después. Que no exista camino se sabe en
microsegundos, sin tocar el disco. Corregido: `convert` con `png → mp3` devuelve
**81 tokens, `isError: true`, en 17,5 ms**, y la respuesta nombra la salida:
`"sugerencia": "list_targets con formato_origen dice a qué formatos se llega de
verdad desde ahí"`. **El asa es para lo que tarda, no para lo que es imposible.**

*(El orden es deliberado: primero se consulta el grafo —que no toca el disco y no
dice nada que el `enum` del catálogo no diga ya— y solo después el sistema de
ficheros. El orden que sí filtraría es el de `kordoc`, que hace `realpathSync`
antes de `assertWithinRoot` y por eso enumera el disco entero.)*

---

## 3. El presupuesto de catálogo: **REFUTADO, con la curva** — hallazgo 1

**MEDIDO** (`h4_tokens_catalogo.json`), método idéntico al de
`bench/scripts/mcp_probe_bin.py:262` —`tiktoken`/`o200k_base` sobre el catálogo
serializado como viaja por el cable— para que las cifras comparen con las de
`RESULTADOS-MCP.md` §4. **Confirmado por segunda vía**: el arnés compartido midió
`tokens_catalogo = 1503` a las 08:34, la misma cifra que mi script con el mismo
registro.

| Variante | Tokens | Δ | Qué se pierde |
|---|---:|---:|---|
| **A · vigente (5 herr., 6 motores)** | **1.605** | — | nada |
| A′ · vigente con los 3 motores nativos | 1.503 | −102 | *(estado anterior a las 08:58)* |
| B · sin anotaciones | 1.527 | −78 | nada **del lado del modelo** |
| **E · las CUATRO del plan (sin `job`)** | **1.452** | −153 | el asa deja de ser consultable |
| F · cuatro y sin anotaciones | 1.384 | −221 | ídem |
| **D · sin los `enum` del registro** | **1.268** | −337 | **la cobertura declarada** |
| **C · sin `description` por parámetro** | **1.145** | −460 | **la semántica de los parámetros** |
| **G · mínimo estilo FastMCP** (sin enum, sin descripciones, sin anotaciones) | **728** | −877 | las tres cosas a la vez |

> **La conclusión, y es incómoda:** el presupuesto de **≤1.200 tokens** y las dos
> reglas de cobertura **no pueden cumplirse a la vez**, y **el número de
> herramientas no es lo que decide**. Con cuatro serían 1.452 — también fuera. La
> única forma de entrar en 1.200 es renunciar a la `description` por parámetro
> (variante C), es decir volver al catálogo que produce **15–17 % de fallos
> silenciosos**.

**Cuál de los dos requisitos cede, y por qué ese:**

- El **≤1.200** entró en `RESULTADOS-MCP.md` §4 como *«Propuesta»*, y su
  justificación —el multiplicador **×2,0–2,6 por turno**— fue **re-acotada** por
  `bench/mcp-cabos-2.md` §4: en sesión real el cuerpo del catálogo llega
  **diferido** y **no se paga por turno**. Este informe lo confirma con el
  servidor real (§4).
- La **`description` por parámetro** está MEDIDA en **0 de 193** parámetros de
  los tres catálogos de referencia, con el caso `add_b_roll` (un `array of
  object` sin una sola clave y una descripción que remite a «mensajes
  anteriores») como demostración de a dónde lleva.
- Los **`enum` del registro** están MEDIDOS como mecanismo de seguridad contra el
  15–17 %, y este informe los ve funcionar literalmente: el modelo **citó la
  lista de formatos de origen palabra por palabra** en sus abstenciones (§4).

> **Lo que queda vivo del presupuesto es el que sí se paga siempre: los NOMBRES.**
> `convert inspect list_targets batch job` = **6 tokens**. Ese es el número que
> se inyecta en cada turno, y es el que hay que vigilar.

**Comparación con el sector**, para calibrar: `video-audio-mcp` 7.964 (27
herr.) · `kordoc` 7.759 (15) · `docling-mcp` 5.280 (19) · `servers/filesystem`
3.360 (14) · `ffmpeg-mcp-lite` 2.322 (8) · `image-worker-mcp` 1.177 (2) ·
**FileX 1.605 (5)** · `markitdown-mcp` 79 (1).

**Las anotaciones cuestan 78 tokens y compran cero del lado del modelo** — MEDIDO
aquí y en `bench/mcp-cabos-sueltos.md` §1.2. Se mantienen porque son correctas
según la especificación y otros clientes pueden usarlas, pero **queda escrito el
precio** para que la decisión sea informada y no inercia.

**Ni `resources` ni `prompts`.** El arnés compartido lo confirma:
`resources/list` y `prompts/list` devuelven `McpError: Method not found`
(`h4_sonda.json`). El cliente pregunta, el modelo no los ve.

### Un parámetro que se quitó del catálogo, con su precio

`timeout_s` costaba **55 tokens** por un valor que el servidor sabe mejor que el
modelo y que, mal puesto, deja un motor colgado. Fuera del catálogo; el tope
existe siempre (`TIMEOUT_MCP = 300 s`, `TIMEOUT_MAXIMO = 900 s`) y la API de
`Servicio.convert` sí lo acepta, para la CLI y las pruebas.

---

## 4. Contra el cliente REAL: 15 ejecuciones — hallazgos 3 y 4

**El experimento que ningún informe anterior había hecho.** La afirmación de
`PLAN-ORQUESTADOR.md` §4.4 —*«`list_targets` es el mecanismo de seguridad, no una
comodidad»*— **no estaba medida: se dedujo** del resultado de `saturacion`. Aquí
se mide, con el diseño de `saturacion` invertido: catálogo real de FileX,
peticiones **fuera de su cobertura**, y **el criterio de acierto es la
abstención**.

**Arnés:** `h4_cliente.py`. `claude -p`, modelo Haiku, `--strict-mcp-config` con
un `.mcp.json` propio (**no el del proyecto**), `--setting-sources ""`, cwd
neutro, `--output-format stream-json --verbose` para tener **la traza de
herramientas**, no solo el texto final. **La arena se resiembra antes de cada
ejecución.** n=3 por caso, 5 casos, **15 ejecuciones**.

### 4.1 El resultado — MEDIDO (`h4_cliente.json`)

| | n | aciertos |
|---|---:|---:|
| **Fuera de cobertura** (acierto = abstenerse) | 9 | **9** |
| **Controles** (acierto = convertir) | 6 | **6** |
| **Total** | **15** | **15** |

**Cero fallos silenciosos, frente al 15–17 % de referencia.** Mediana de 5 turnos
y 116.297 tokens de entrada por ejecución.

### 4.2 Pero el mecanismo **no es el que decía el plan** — hallazgo 3

De las **9** peticiones fuera de cobertura:

| Cómo se evitó el fallo | Ejecuciones | Traza |
|---|---:|---|
| Llamó a **`list_targets`** | **6** | `ToolSearch → Glob → mcp__filex__list_targets` |
| Llamó a **`convert`** y recibió su **rechazo síncrono** | **2** | `ToolSearch → mcp__filex__convert` → `{"error": "ningún motor disponible lee 'docx'"}` |
| **No llamó a ninguna de las dos**: leyó el `enum` del esquema | **1** | solo `ToolSearch` |

> **`list_targets` es una de tres patas, y en 3 de 9 no fue la que aguantó.** La
> formulación de §4.4 hay que corregirla: el mecanismo de seguridad es
> **la cobertura declarada**, que se manifiesta de tres formas —el `enum` del
> esquema, el rechazo explícito de `convert`, y `list_targets` como consulta— y
> **el modelo elige cuál usa**. El plan ya nombra las tres, pero llama
> «mecanismo» solo a la primera; **la medición dice que hay que declararlas las
> tres o el diseño se apoya en la que el modelo puede saltarse.**

El detalle que lo demuestra, literal, de `h4_cli_fuera_docx_pdf_0.jsonl`:

```
TOOL_USE  ToolSearch {"query": "select:mcp__filex__convert,mcp__filex__list_targets"}
TOOL_USE  mcp__filex__convert {"entrada": "...\\informe.docx", "salida": "...\\informe.pdf", ...}
RESULT    {"error": "ningún motor disponible lee 'docx'",
           "sugerencia": "list_targets con formato_origen dice a qué formatos se llega..."}
TEXT      **No se puede convertir.** ... FileX no tiene ningún motor instalado que lea .docx
```

Cargó los dos esquemas, **ignoró `list_targets`**, llamó a `convert`, y lo que lo
detuvo fue el rechazo síncrono. Y en la respuesta final **citó el `enum` entero**:
*«los formatos que FileX soporta son: avi, avif, bmp, flac, gif, ico, jpg, m4a,
mkv, mov, mp3, mp4, ogg, opus, pdf, png, svg, tif, wav, webm, webp»* — que es
exactamente el `enum` de `list_targets.formato_origen` generado del registro.

**Un hueco de cobertura que esto destapó y que no estaba previsto:** el `enum` de
`convert` declara los formatos de **destino**; el de **origen** no existe en
`convert`, porque el origen sale de la ruta del fichero. Así que **la
combinación imposible SÍ es expresable en `convert`** y solo la detiene el
rechazo síncrono. Que ese rechazo exista dejó de ser una mejora de ergonomía para
ser **la mitad de la defensa**.

### 4.3 La diferición, confirmada en una versión nueva — hallazgo 4

**MEDIDO: 15 de 15 ejecuciones emitieron `ToolSearch`** antes de poder llamar a
ninguna herramienta de FileX. El modelo no tenía los esquemas cargados.

> Esto **confirma y refuerza** `bench/mcp-cabos-2.md` §4 en los tres puntos donde
> aquel informe se declaraba a sí mismo frágil:
> - era **Claude Code 2.1.238**; esto es **2.1.239**;
> - era un **servidor de sonda con catálogos fabricados**; esto es el **servidor
>   real** con su catálogo real de 1.503 tokens;
> - era una **medida indirecta** (tokens totales idénticos); esto es la
>   **traza literal** del mecanismo, con el nombre de la llamada.
>
> **El cuerpo del catálogo no se paga por turno en el despliegue real de FileX.**
> Y por eso el exceso de 405 tokens sobre el presupuesto de §3 es, hoy, casi
> gratis. **Pero sigue sin apostarse el diseño a ello:** es comportamiento de una
> versión y depende del total de herramientas de la sesión.

### 4.4 Lo que este experimento NO demuestra

- **La temperatura no es fijable desde el CLI.** Limitación nº 1 heredada de
  `saturacion-herramientas.md` §8. Sigue sin haber clave de API en esta máquina.
- **n=3 por caso.** Con 15 ejecuciones, **«0 % de fallo silencioso» no es
  distinguible de un 5 %**. Lo que sí se descarta con esta potencia es un fallo
  del orden del 15–17 %, que es lo que había que descartar.
- **Un solo modelo** (Haiku). `saturacion` midió que Sonnet falla **más** en el
  catálogo escueto (17 % frente a 15 %). **PENDIENTE** repetirlo con Sonnet.
- **La cobertura cambió a las 08:58**: con `motor_contenedor.py` levantado,
  `docx→pdf` ya se puede. Quien reejecute esto tiene que elegir casos fuera de la
  cobertura **de ese momento**.

---

## 5. W9 abierto en el núcleo — hallazgo 5, y el más grave

**MEDIDO** (`h4_ads_w9.json`). `RESULTADOS-MCP.md` §5 dejó escrito que la
referencia oficial deniega **28 de 29** vectores y que **el único concedido son
los flujos alternativos de datos** (ADS): bytes distintos de los del fichero que
se validó, dentro de la raíz permitida. De ahí sale **R12**.

**El núcleo de FileX tiene la defensa escrita, probada y desconectada.**

`filex/confinamiento.py:51` define `nombre_seguro()`, que devuelve `False` para
`x.txt:oculto` con este comentario:

```python
    Prohíbe flujos alternativos (ADS), nombres reservados, y puntos o espacios
    finales. **W9 concedió acceso a un ADS** en un servidor de referencia.
```

Y en todo el paquete, **el único que la llama es `pruebas/test_hito1.py`**:

```
$ grep -rn "nombre_seguro" filex/ pruebas/
filex/confinamiento.py:51:def nombre_seguro(nombre: str) -> bool:
pruebas/test_hito1.py:191:  self.assertFalse(nombre_seguro("x.txt:oculto"))  # ADS: W9 lo concedió
```

**Consecuencia, reproducida en las dos direcciones:**

| Vector | Hoy | Qué devuelve |
|---|---|---|
| `inspect` sobre `«raíz»/dentro.png:oculto` | **CONCEDIDO** | **72 B** de un flujo oculto, con `firma: png` — bytes que no son los del fichero validado |
| `convert` con `salida = «raíz»/victima.txt:carga.webp` | **CONCEDIDO** | **94 B** escritos en un flujo de un fichero ajeno, `veredicto: ok`, contenido visible de la víctima intacto |

`Confinamiento.resolver()` no mira los componentes de la ruta de entrada, y
`FileX._resolver()` valida el **directorio** del destino pero **no el nombre del
fichero de salida**. Son dos huecos, no uno: el parche de solo lectura cierra la
lectura y **deja la escritura abierta** — está medido en la fila
`media_correccion` de `h4_ads_w9.json`.

**No lo he arreglado, y es deliberado.** Meter el predicado en `filex/mcp.py`
sería cometer exactamente el pecado de `kordoc`: la defensa en la superficie MCP
y la CLI sin ella. R10 dice que la validación vive en el núcleo. El diff va en
§8, ya probado.

En `pruebas/test_hito4.py` quedan **dos pruebas marcadas `@unittest.expectedFailure`**
que documentan el hueco. Cuando alguien aplique el diff darán **«unexpected
success»**, que es la señal de quitar la marca.

---

## 6. Confinamiento y contrato: lo que sí está en su sitio

### 6.1 R4 — la equivalencia de latencia, CERRADA — hallazgo 7

`filex/confinamiento.py:19` dejó el pendiente con todas las letras: *«la
equivalencia de latencia entre los dos casos es PENDIENTE: hoy el camino de "no
existe" puede ser más corto y eso es un oráculo temporal»*.

**MEDIDO, n=201 por celda** (`h4_r4_latencia.json`):

| Celda | Mediana | Respuesta |
|---|---:|---|
| fuera, **existe** (`C:/Windows/win.ini`) | **6,5 µs** | `{"error": "ruta no accesible"}` |
| fuera, **no existe** | **6,4 µs** | `{"error": "ruta no accesible"}` |
| travesía `../../Windows/win.ini` | 7,9 µs | ídem |
| dentro, existe | 606,0 µs | los metadatos |
| dentro, no existe | 319,9 µs | ídem opaco |

> **Razón de latencia fuera de la raíz: 1,016. Mismo mensaje literal.** Mejor que
> el 1,36 de `servers/filesystem` (1,4 vs 1,9 ms), y por el mismo motivo: **el
> predicado es léxico y corre antes de tocar el disco** (R1). Fuera de la raíz el
> servidor no le pregunta nada al sistema de ficheros, así que no puede filtrar
> lo que no sabe.
>
> **Dentro** de la raíz sí hay señal (**1,9×**), y es legítima: al usuario hay
> que decirle que su fichero no está. Coincide con el matiz de
> `RESULTADOS-MCP.md` §5.

Y confirmado también **de fuera**, por el arnés compartido: `inspect_fuera`
**2,4 ms** vs `inspect_no_existe` **2,3 ms**, con las respuestas byte a byte
iguales (**9 tokens** cada una).

### 6.2 R13 — roots intersecados y cacheados por sesión

Implementado en `filex.mcp.Raices`, con las tres reglas: **intersección**, no
sustitución (`servers/filesystem` `index.ts:181` **sustituye**); comparación por
**segmentos** (`permitido` no deja pasar `permitido_secreto`); y **caché por
sesión** invalidada con `on_roots_list_changed`, que es la capacidad que
`bench/mcp-cabos-2.md` §2 midió declarada. Probado en las cuatro
configuraciones (`test_interseccion_de_roots_no_sustitucion`).

**R6 se aplica encima:** sin raíz del servidor y sin roots del cliente, **no se
opera**, y se dice con el mismo mensaje opaco.

**Idempotencia (§5.3):** los roots se resuelven **al principio del cuerpo de cada
herramienta, antes de cualquier efecto**, porque con `mcp 2.0.0` el
`Resolve(ListRoots)` puede ejecutar el cuerpo dos veces. Hoy Claude Code negocia
`2025-11-25` y usa la vía clásica —una sola ejecución— pero la regla se respeta.

### 6.3 `roots` está DEPRECADO — hallazgo 9

**MEDIDO**, en el `stderr` del servidor durante la sonda
(`h4_sonda_stderr.txt`):

```
filex\mcp.py:937: MCPDeprecationWarning: The roots capability is deprecated as of 2026-07-28 (SEP-2577).
filex\mcp.py:535: MCPDeprecationWarning: The roots capability is deprecated as of 2026-07-28 (SEP-2577).
```

`mcp 2.0.0` marca `@deprecated` tanto `list_roots()` como el manejador de
`roots/list_changed` (y también `logging`, por el mismo SEP).

> **R13 y la caché de roots están construidas sobre una capacidad que la
> especificación está retirando.** No es urgente —Claude Code negocia
> `2025-11-25`, donde `roots` es plenamente vigente, y el servidor funciona sin
> un error— pero **`RESULTADOS-MCP.md` §10 R13 y `PLAN-ORQUESTADOR.md` §4.6
> deberían anotarlo**: lo que hoy es «la forma canónica de que el cliente acote
> el servidor» tiene fecha de caducidad, y **la lista blanca del servidor
> (`--raiz`) es la que no la tiene**. Qué la sustituye en 2026-07-28 es
> **PENDIENTE**: no lo he investigado.

### 6.4 La exención de R8 para `inspect`: se sostiene, con el número corregido — hallazgo 6

**MEDIDO** (`h4_inspect_r8.json`), n=15 por celda, dos testigos de ruido (deriva
×0,78, nivel 73→42 ms, ninguno agotado), tanda **SUCIA por estructura**:

| Fichero | MB | `inspect` en proceso | staging (copia) | `ffprobe` | staging / `inspect` |
|---|---:|---:|---:|---:|---:|
| `trivial.png` | 0,00 | **0,218 ms** | 0,56 ms | 43,6 ms | **2,6×** |
| `tipico.png` | 0,04 | **0,248 ms** | 0,50 ms | 94,7 ms | **2,0×** |
| `tipico_texto.pdf` | 0,00 | **0,251 ms** | 0,69 ms | 34,9 ms | **2,8×** |
| `tipico.mp4` | 15,49 | **0,589 ms** | 16,26 ms | 53,5 ms | **27,6×** |
| `patologico_16bit.tif` | 68,67 | **0,214 ms** | 60,93 ms | 93,1 ms | **284,4×** |

> **La conclusión de `bench/mcp-cabos-2.md` §5.3 aguanta; su número no.** Aquel
> «0,04–0,06 ms» midió `abrir + leer 64 KiB de cabecera` (`c5b_cruce_inspect.py`),
> **no un `inspect`**. El `inspect` que el hito 4 expone de verdad —
> `verificador.sondear_en_proceso`, que calcula la firma real, parsea la cabecera
> del formato y recorre las cajas de un ISOBMFF— cuesta **0,21–0,59 ms**, de
> **×4 a ×10** más.
>
> **El «de 30× a más de 3.000× la operación» pasa a «de 2,0× a 284×».** La
> dirección no cambia —el staging siempre cuesta más que el `inspect` y compra
> cero seguridad, porque una lectura de cabeceras en proceso nunca entrega la
> ruta a un lector ajeno— pero **en el extremo pequeño el margen es un factor 2,
> no un factor 30**, y eso importa si alguien quisiera argumentar «pues stagea
> siempre, total».
>
> Y el otro extremo se refuerza: **el `inspect` externo (`ffprobe`) cuesta de
> 140× a 430× el interno**, lo que confirma por tercera vía que verificar
> leyendo cabeceras en proceso es lo correcto.

**Lo que la exención NO incluye:** el confinamiento. `inspect` se salta la copia,
no el permiso — probado en `test_inspect_esta_exento_del_presupuesto_pero_no_del_confinamiento`.

### 6.5 R18 y el quinto punto llegan gratis

La capa MCP no reimplementa ni el directorio desechable ni el censo: los hereda
de `FileX.convertir`. El punto 5 cruza al modelo como
`"ficheros_no_declarados": [...]` (hasta 5 nombres, sin tamaños), que es la
lectura de modelo del «el motor escribió cosas que nadie pidió».

**Los hallazgos `informativo` no cruzan.** «El fichero declarado lleva el 100,0 %
de los bytes escritos» son **25 tokens para decir que todo fue bien**; el criterio
operativo es tokens de respuesta.

---

## 7. Respuestas: ruta y metadatos, y el presupuesto se cumple

**MEDIDO por el arnés compartido** (`h4_sonda.json`, 12 llamadas, cliente
`mcp 1.29.0` contra servidor `mcp 2.0.0`):

| Llamada | ms | Patrón | tok texto | tok binario | bytes binario |
|---|---:|---|---:|---:|---:|
| `list_targets(png)` | 5,3 | PROSA | **66** | 0 | 0 |
| `list_targets(png→mp3)` | 9,7 | PROSA | **80** | 0 | 0 |
| `inspect(trivial.png, 316 B)` | 3,1 | ASA | **108** | 0 | 0 |
| **`inspect(tipico.mp4, 15,5 MB)`** | 3,8 | ASA | **234** | 0 | 0 |
| `inspect` fuera de la raíz | 2,4 | — | **9** | 0 | 0 |
| `inspect` no existe | 2,3 | — | **9** | 0 | 0 |
| **`convert` con la salida YA EXISTENTE** | **10,7** | ASA | **50** | 0 | 0 |
| **`convert` de un MP4 de 15,5 MB** | 19,2 | ASA | **49** | 0 | 0 |
| `convert` imposible | 17,5 | — | **81** | 0 | 0 |
| `convert` con la entrada rota | 12,9 | ASA | **49** | 0 | 0 |
| `job` desconocido | 9,9 | — | **9** | 0 | 0 |
| `batch` de dos | 12,6 | ASA | **34** | 0 | 0 |

**Todas por debajo de 200 tokens salvo `inspect` del MP4 (234), que es la
excepción declarada.** Y la propiedad que hace viable el diseño se reproduce:
**la respuesta de `convert` no crece con la entrada** — 50 tokens para un PNG de
316 B, 49 para un MP4 de 15,5 MB.

**Cero bytes binarios en las doce**, y `test_ninguna_respuesta_lleva_base64`
busca rachas de ≥512 caracteres base64 en las respuestas, que es la forma en que
el antipatrón aparece de verdad (`image-worker-mcp`, ×87,6). El criterio es
**tokens de respuesta**, no tipos del protocolo.

### 7.1 El deadlock de las 26 de 26: no se hereda

**MEDIDO.** El disparador exacto —**la ruta de salida ya existe**— devuelve el
asa en **10,7 ms**. Dos defensas, y la segunda es la que vale:

1. `convert` no bloquea: el trabajo corre en un hilo y el bucle de eventos sigue.
2. **Toda invocación pasa por `filex/invocacion.ejecutar()`**, que construye el
   proceso con `stdin=DEVNULL` **antes** de las banderas. Es la defensa que no se
   puede olvidar en un punto de invocación **porque no hay puntos de invocación:
   hay uno**.

`filex/mcp.py` **no importa `subprocess`**.

### 7.2 Nunca `stderr` crudo

`test_nunca_stderr_crudo` convierte un fichero con firma de PNG y cuerpo basura y
comprueba que en la respuesta no aparecen `ffmpeg version`, `configuration:`,
`libavcodec`, `pip install`, `npm install` ni `traceback`. **Sale 49 tokens**,
frente a los **884-1.228** de los tres servidores de referencia para el mismo
tipo de fallo. La respuesta lleva `motivo`, la clasificación opaca que
`invocacion.Resultado` ya separaba de `err`.

Y el `except` general del despachador devuelve **la clase de la excepción, no su
mensaje**: el mensaje de una excepción de Python puede llevar una ruta.

---

## 8. Cambios que pido en el núcleo

**No he tocado ninguno de estos ficheros.** Los tres primeros son un solo
problema —W9— y van juntos.

### 8.1 `filex/confinamiento.py` — cerrar W9 en la LECTURA · **crítico**

```diff
@@ class Confinamiento:
     def _lexico_ok(self, ruta: str) -> bool:
         """R1 + R17: todo lo que se puede decidir SIN tocar el disco, primero."""
         if not ruta or len(ruta) > MAX_LONGITUD:
             return False
         if ruta.count(os.sep) + (ruta.count(os.altsep) if os.altsep else 0) > MAX_COMPONENTES:
             return False
         if "\x00" in ruta:
             return False
+        # R12 sobre CADA COMPONENTE de la ruta, no solo sobre el nombre de
+        # salida. `nombre_seguro` está escrito y probado desde el hito 1 y no lo
+        # llamaba nadie más que `pruebas/test_hito1.py`: W9 —el único de los 29
+        # vectores que la referencia oficial concede— estaba abierto aquí.
+        # MEDIDO (`bench/salidas-hito4/h4_ads_w9.json`): `inspect` devolvía 72 B
+        # de `dentro.png:oculto`, bytes distintos de los del fichero validado.
+        resto = os.path.splitdrive(os.path.abspath(ruta))[1]
+        if os.altsep:
+            resto = resto.replace(os.altsep, os.sep)
+        for comp in resto.split(os.sep):
+            if comp in ("", ".", ".."):
+                continue
+            if not nombre_seguro(comp):
+                return False
         return True
```

### 8.2 `filex/nucleo.py` — cerrar W9 en la ESCRITURA · **crítico**

El parche anterior **no basta**: `_resolver` valida el *directorio* del destino y
**el nombre del fichero de salida no lo mira nadie** (fila `media_correccion` de
`h4_ads_w9.json`).

```diff
@@ class FileX:
     def _resolver(self, entrada: str, salida: str) -> tuple[str, str]:
+        # R12 sobre el NOMBRE DE SALIDA. Sin esto se escriben 94 B en el flujo
+        # alternativo de un fichero ajeno con `veredicto: ok`, y el contenido
+        # visible de la víctima queda intacto: nadie lo nota.
+        from .confinamiento import nombre_seguro
+        if not nombre_seguro(os.path.basename(os.path.abspath(salida))):
+            raise Denegado()
         if self.confinamiento is None:
             return os.path.abspath(entrada), os.path.abspath(salida)
```

**MEDIDO con los dos parches aplicados en memoria** (`h4_ads_w9.py`): lectura
denegada, escritura denegada, ningún ADS en disco, los dos controles legítimos
intactos, y **`pruebas/test_hito1.py` + `pruebas/test_hito4.py` = 61 pruebas, 0
fallos, 0 errores**.

### 8.3 `pruebas/test_hito4.py` — quitar los `@unittest.expectedFailure`

Cuando se apliquen 8.1 y 8.2, las dos pruebas de `W9_FlujosAlternativos` darán
«unexpected success». Es la señal, no un fallo.

### 8.4 `filex/invocacion.py` — que `job cancelar` pueda matar el árbol · **medio**

`PLAN-ORQUESTADOR.md` §5.3 pide que `job_cancel` **mate el árbol de procesos**,
no que marque un estado. Hoy `ejecutar()` no expone ningún asa del `Popen`, así
que `job(accion="cancelar")` solo detiene el trabajo **entre saltos**; el salto en
curso lo acota su timeout. Pido un parámetro opcional:

```diff
-def ejecutar(argv, *, timeout=TIMEOUT_POR_DEFECTO, cwd=None, entorno=None) -> Resultado:
+def ejecutar(argv, *, timeout=TIMEOUT_POR_DEFECTO, cwd=None, entorno=None,
+             al_arrancar=None) -> Resultado:
@@
     proc = subprocess.Popen(...)
+    if al_arrancar is not None:
+        # Le entrega el proceso a quien lo lanzó para que pueda matarlo. Sigue
+        # siendo el ÚNICO punto de invocación: no se abre una segunda vía.
+        al_arrancar(proc)
```

y que `FileX.convertir` lo propague. **PENDIENTE** medir cuánto tarda de verdad
una cancelación con y sin esto.

### 8.5 `filex/nucleo.py` — un `inspeccionar()` en el núcleo · **bajo**

Hoy `filex/mcp.py` compone `fx.confinamiento.resolver(...)` +
`contrato.verificador().sondear_en_proceso(...)` para `inspect`. Usa las piezas
del núcleo y no duplica ningún predicado, pero **la composición vive en la
superficie**, y el watcher y la API HTTP van a necesitarla igual. Pido
`FileX.inspeccionar(ruta) -> dict` con ese cuerpo exacto, para que las cuatro
superficies compartan también esto.

### 8.6 `filex/nucleo.py` — que `convertir()` distinga «no hay camino» de «ruta denegada» · **bajo**

`convert` ya rechaza en el acto lo imposible porque `planificar()` es puro. Pero
la validación de rutas solo ocurre dentro de `convertir()`, ya en el hilo, así
que una ruta denegada **gasta un `job_id`**. Un `FileX.validar(entrada, salida)`
público —o que `_resolver` deje de ser privado— permitiría rechazarla también en
el acto, con el mismo mensaje opaco.

---

## 9. Arranque en frío: la predicción falla, y no por lo que se pensaba — hallazgo 8

**MEDIDO** (`h4_arranque.json`), n=9 con calentamiento, JSON-RPC crudo sobre
stdio para no meter en la cuenta el arranque del cliente:

| | mediana |
|---|---:|
| `initialize` respondido | **1.881,8 ms** |
| `tools/list` respondido | **1.884,1 ms** |

`RESULTADOS-MCP.md` §9.2(c) predijo *«un FileX que delegue en ffmpeg e
ImageMagick nativos arrancará en ~1 s»*. **Son 1,9 s: la predicción falla ×1,9.**

Pero **el mecanismo que aquel apartado afirmaba queda CONFIRMADO y afilado**: *«no
correlaciona con el tamaño del catálogo, sino con lo que el servidor importa»*.
El desglose:

| Parte | ms | % |
|---|---:|---:|
| **`import mcp` (el SDK)** | **1.601** | **85 %** |
| `FileX()` — sondeo de motores | 524 | 28 % |
| `import filex` | 18 | 1 % |
| **`tools/list` sobre `initialize`** | **+2,3** | **0,1 %** |

- **Lo que se importa es el SDK, no los motores.** Es la parte que un servidor
  MCP no puede evitar.
- **`tools/list` cuesta 2,3 ms**: el catálogo, con 5 herramientas y 1.605 tokens,
  **no pesa en el arranque**. Segundo argumento independiente de que el
  presupuesto de §3 no es un problema de latencia.
- **El sondeo de motores no crece con el registro:** 539 ms con 3 motores y
  **524 ms con 6**, después de que K1 añadiera LibreOffice, Pandoc y Calibre.

Contexto del sector: `ffmpeg-mcp-lite` 6.689 ms en frío / 817 en caliente ·
`docling-mcp` ~6.000 · `markitdown-mcp` 3.413 · `image-worker-mcp` 2.620 ·
**FileX 1.882** · `video-audio-mcp` 1.202. **FileX es el segundo más rápido de
los seis.**

---

## 10. Compatibilidad de eras: §5.3 confirmada

**MEDIDO.** La sonda corrió con un **cliente `mcp 1.29.0`** (`.venv-mcp-lite`)
contra el **servidor `mcp 2.0.0`** (`.venv-mcp-filex`): **12 de 12 llamadas
correctas, cero errores de protocolo**. Y las 15 ejecuciones contra **Claude Code
2.1.239** funcionaron igual.

> *«Construir sobre `mcp>=2.0.0` es lo correcto precisamente porque negocia hacia
> abajo»* — confirmado con dos clientes de dos eras distintas.

**Un venv por servidor**, como manda la trampa nº 14: `.venv-mcp-filex` es
propio, con `mcp 2.0.0` + `tiktoken` + `pytest`. **No se instaló nada en
`.venv-ai`, `.venv-paddle`, `.venv-mcp-md` ni `.venv-marker`.**

**El aviso operativo se reproduce, y con un matiz útil.** Tras añadir `filex` a
la `.mcp.json` del proyecto:

```
markitdown: ... - ✔ Connected
docling:    ... - ✔ Connected
filex:      ... - ⏸ Pending approval (run `claude` to approve)
```

> **El «Pending approval» es del servidor NUEVO, no de todo el fichero.** Los dos
> que ya estaban aprobados **siguieron conectados**. Eso acota el aviso de
> `bench/mcp-cabos-sueltos.md` §1.6: un `filex init` que escriba la `.mcp.json`
> **no deja SU servidor conectado** —hace falta un paso humano interactivo— pero
> **no rompe los que ya lo estaban**.

---

## 11. Sobre `PRUEBAS-MCP-REFS.md` — hallazgo 10

Se me entregó como *«documento de traspaso del 19 de agosto… se recuperó hoy de
unas ramas borradas y nadie lo ha usado todavía»*, y como «la mitad del encargo».

**No lo es, y conviene que conste para que nadie vuelva a gastar tiempo en él.**
Su sucesor lo dice en su sexta línea:

> `RESULTADOS-MCP.md:6` — *«Este documento **sustituye a `PRUEBAS-MCP-REFS.md`**,
> que era la especificación de lo pendiente. Aquí están las respuestas.»*

Sus **seis preguntas transversales** (§4) están **las seis cerradas** en
`RESULTADOS-MCP.md` §2, y sus dos fases están ejecutadas: la fase 1 produjo
`analysis/00-mcp-filesystem.md` y `00-mcp-multimedia.md`, consolidados en
`00-mcp-componentes.md` (**90 componentes con veredicto**); la fase 2 produjo
`bench/mcp-refs-multimedia.md` y `bench/mcp-refs-confinamiento.md`.

**Lo único suyo que sigue siendo útil, y lo he usado:**

- **§7.2 y §7.3** — las reglas de trabajo: `.mcp.json` **solo de proyecto**, y
  **un venv por servidor Python**. Aplicadas las dos.
- **§5, fase 2** — *«medir con `tiktoken` cuántos tokens devuelve cada
  herramienta»*. Es el método de §7.
- **§2** — su autocorrección (*«la defensa que dije que había que inventar, ya
  existe»*). Es la genealogía de las 18 reglas de confinamiento.

**Recomendación para quien consolide:** darle a `PRUEBAS-MCP-REFS.md` una
cabecera de «SUPERSEDIDO por `RESULTADOS-MCP.md`, se conserva como historia
intelectual», igual que se hizo con `analysis/OCRmyPDF.md`. Sin ella, el
documento se lee como trabajo pendiente y **hoy me lo han vuelto a asignar como
tal**.

---

## 12. Qué cambia en los documentos maestros (para quien consolide — **yo no lo toco**)

| # | Documento y sitio | Qué dice hoy | Qué mide este informe |
|---|---|---|---|
| 1 | `PLAN-ORQUESTADOR.md` §4.4 y §7 hito 4; `RESULTADOS-MCP.md` §4: **≤1.200 tokens** para **cuatro** herramientas | Presupuesto y número | **Ninguno de los dos es alcanzable con las reglas de cobertura.** Son **cinco** herramientas (§2) y **1.605 tokens**; con cuatro serían 1.452. `description` por parámetro cuesta **460** y los `enum` **337**. **Lo que queda es el presupuesto de NOMBRES: 6 tokens** (§3) |
| 2 | `PLAN-ORQUESTADOR.md` §4.4: *«`list_targets` es el mecanismo de seguridad»* | Deducido de `saturacion` | **MATIZADO por ejecución (§4.2):** 15/15 aciertos, pero `list_targets` actuó en **6 de 9**; en 2 fue el **rechazo síncrono de `convert`** y en 1 bastó el **`enum`**. El mecanismo es **la cobertura declarada en sus tres formas** |
| 3 | `bench/mcp-cabos-2.md` §4 / `RESULTADOS-MCP.md` §4, recuadro de re-acotación | Diferición medida en 2.1.238 con catálogos de sonda | **CONFIRMADO y reforzado (§4.3):** 2.1.239, servidor real, catálogo real, **15/15 con `ToolSearch`** y la traza literal del mecanismo |
| 4 | `RESULTADOS-MCP.md` §10 R12 / §5: W9 como defecto de un servidor **ajeno** | «W9 concedió acceso a un ADS» | **W9 ESTÁ ABIERTO EN FILEX (§5).** Lee 72 B y escribe 94 B por ADS con `veredicto: ok`. `nombre_seguro()` solo lo llama una prueba. Diff en §8 |
| 5 | `bench/mcp-cabos-2.md` §5.3 / `RESULTADOS-MCP.md` §10 R8: `inspect` **0,04–0,06 ms**, staging **30× a 3.000×** | Medía «abrir + leer 64 KiB» | **El `inspect` real cuesta 0,21–0,59 ms** y el margen es **2,0× a 284×** (§6.4). **La exención no cambia; su número sí** |
| 6 | `filex/confinamiento.py:19`: equivalencia de latencia de R4 **PENDIENTE** | Pendiente declarado en el código | **CERRADA (§6.1):** razón **1,016** con n=201, mismo mensaje literal |
| 7 | `RESULTADOS-MCP.md` §9.2(c): arranque **«~1 s»** | Predicción | **1.882 ms (§9), ×1,9.** Pero su mecanismo se confirma: **1.601 ms son `import mcp`** y `tools/list` cuesta **2,3 ms** |
| 8 | `RESULTADOS-MCP.md` §10 R13 y `PLAN-ORQUESTADOR.md` §4.6: roots como mecanismo canónico | Vigente | **`roots` está DEPRECADO en 2026-07-28 (SEP-2577)** (§6.3). Funciona hoy porque el cliente negocia `2025-11-25`. **La lista blanca del servidor es la que no caduca** |
| 9 | `bench/mcp-cabos-sueltos.md` §1.6: cambiar la `.mcp.json` deja «el servidor» pendiente | Sin acotar | **Es el servidor NUEVO, no el fichero** (§10): los ya aprobados siguen conectados |
| 10 | `PRUEBAS-MCP-REFS.md`, sin cabecera de estado | Se lee como trabajo pendiente | **Está enteramente contestado por `RESULTADOS-MCP.md`** (§11). Necesita una cabecera de «SUPERSEDIDO» |

---

## 13. Lo que queda PENDIENTE

| Pendiente | Por qué importa |
|---|---|
| **Aplicar el diff de W9 (§8.1 y §8.2)** | Es un fallo de seguridad abierto, con las dos direcciones reproducidas. El parche está probado y no rompe nada |
| **Repetir §4 con Sonnet y con n≥10** | `saturacion` midió que Sonnet falla **más** (17 % vs 15 %) con catálogo escueto. Con n=3 y un modelo, «0 %» no se distingue de «5 %» |
| **Qué sustituye a `roots` en el protocolo 2026-07-28** | R13 entera depende de ello. No lo he investigado |
| **`job cancelar` que mate el árbol de procesos** | Hoy solo detiene entre saltos (§8.4). El salto en curso lo acota su timeout |
| **La caché de roots invalidada por una emisión REAL** | Heredado de `bench/mcp-cabos-2.md` §2: en headless no hay forma de cambiar los roots a media sesión |
| **Medir el catálogo con el registro completo del hito 5** | Con 6 motores son 1.605 tok. Con Gotenberg y el sidecar de IA, los `enum` crecerán: **hay que volver a medir la curva, no extrapolarla** |
| **Una prueba de subsunción automática** | `PLAN-ORQUESTADOR.md` §4.4 la propone (*si el esquema de A es subconjunto estricto del de B, A sobra*). Con cinco herramientas se comprueba a ojo; con más, no |
| **Idempotencia real ante `Resolve(ListRoots)` doble** | El cuerpo está escrito idempotente hasta la línea de roots, pero **no se ha ejercitado un cliente que lo dispare**: Claude Code usa hoy la vía clásica |
| **El coste de `convert` con una ruta denegada** | Gasta un `job_id` porque la validación vive dentro del hilo (§8.6) |

---

## 14. Índice de la evidencia

Todo en `bench/salidas-hito4/`, con su `MANIFIESTO.md`: **7 arneses, 7 JSON de
resultados, 15 trazas `stream-json`, 628 KB, todo texto.** Ninguna salida binaria
versionada.

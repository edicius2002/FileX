# ¿Un catálogo grande de herramientas MCP hace que el modelo elija peor?

**Agente C3.** Medido el 2026-08-21 sobre Windows 10, Python 3.11.9, Claude Code 2.1.238.
Sin GPU (no se tocó ninguna: el experimento no ejecuta ninguna conversión).

Datos crudos, catálogos, arnés y puntuaciones en `bench/salidas-saturacion/`.
Cada afirmación va marcada **MEDIDO**, **ESTIMADO**, **DISEÑO (sin ejecutar)** o **PENDIENTE**.

---

## 0. Cuál de los tres casos aplica, en la primera línea

> **Aplica el caso 2, en una variante mucho más controlada que la prevista.**
> No hay ninguna clave de API en esta máquina (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`: ausentes;
> `GOOGLE_APPLICATION_CREDENTIALS` existe pero apunta a un fichero que no existe y es de subida a
> GCS, no de inferencia). **Sí** se pudo usar **Claude Code en modo headless (`claude -p`) como
> sujeto**, una vez por petición, en proceso nuevo, con el prompt de sistema fijado, las
> herramientas internas desactivadas y el catálogo MCP inyectado. Eso convierte el caso 2 de
> «poco controlado, pocas repeticiones» en un experimento con **540 ejecuciones independientes**
> y dos modelos.
>
> **El resultado es real y está medido. No hay ninguna cifra conductual inventada en este informe.**

Y la respuesta, también en la primera página:

> **MEDIDO: no. En este dominio y con estas peticiones, pasar de 8 a 27 herramientas no degradó la
> elección.** El catálogo de 27 acertó *más* que el de 8, no menos. Lo que sí degrada la elección no
> es el tamaño del catálogo sino **la falta de cobertura**: el catálogo pequeño, cuando no puede
> hacer lo que se le pide, **no se abstiene — llama a otra herramienta y declara éxito con un dato
> falso.** Detalle en §3 y §6.
>
> **Consecuencia para FileX:** el objetivo de **4 herramientas se sostiene, pero por el coste en
> tokens, que ya estaba medido — no por la calidad de la elección.** El segundo argumento
> independiente que se buscaba **no aparece.** En su lugar aparece un riesgo nuevo, y va en
> dirección contraria: un catálogo demasiado escueto para su dominio produce **fallos silenciosos**.

---

## 1. El instrumento: qué se usó y por qué es válido

### 1.1 Lo que se descartó primero (MEDIDO)

| Medio | Estado |
|---|---|
| `ANTHROPIC_API_KEY` | **ausente** en el entorno |
| `OPENAI_API_KEY` y cualquier otra clave de inferencia | **ausentes** |
| `GOOGLE_APPLICATION_CREDENTIALS` | presente, pero apunta a `C:\Users\krato\onpe-eg2026\credentials\pdfs-uploader.json`, que **no existe**, y es una credencial de subida a GCS, no de un modelo |

No se creó ninguna clave, no se pidió ninguna, y no se tocó `~/.claude.json`.

### 1.2 El sujeto: `claude -p` con el entorno amordazado (MEDIDO)

Cada petición es **un proceso nuevo**, sin memoria de las anteriores. La invocación es:

```
claude -p "<petición>"
  --model <haiku|sonnet>
  --system-prompt "<fijo, idéntico en las tres condiciones>"
  --tools ""                       # ninguna herramienta interna: Read, Bash, Edit… fuera
  --strict-mcp-config --mcp-config <catálogo>   # solo el catálogo del experimento
  --setting-sources ""             # sin settings de usuario, proyecto ni local
  --disable-slash-commands
  --no-session-persistence
  --output-format json
```

`--tools ""` es lo que hace que el experimento mida lo que dice medir: **el espacio de decisión del
modelo contiene exactamente las herramientas del catálogo y nada más.** Sin ese aislamiento, el
modelo elegiría entre el catálogo *y* las ~15 herramientas internas de Claude Code, y la
comparación no significaría nada. El directorio de trabajo es un temporal neutro, fuera del
proyecto, para que no se cargue el `CLAUDE.md` de FileX.

### 1.3 El catálogo se sirve, no se ejecuta (MEDIDO)

`bench/salidas-saturacion/stub_mcp.py` es un servidor MCP stdio de **biblioteca estándar pura, sin
dependencias**, que:

1. Sirve en `tools/list` el catálogo **exacto** —`name`, `description`, `inputSchema`,
   `annotations`— tal como se capturó de los servidores reales en
   `bench/salidas-mcp-refs/multimedia/cat_vam.json` y `cat_lite.json`. No se reescribió ni una coma.
2. En `tools/call` **registra la llamada y sus argumentos** y devuelve un éxito sintético con una
   ruta. **No ejecuta ffmpeg.**

Esto tiene tres virtudes y conviene declararlas:

- **Evita el deadlock conocido** de `video-audio-mcp`, que cuelga la sesión en toda conversión que
  reencodifica (`bench/mcp-refs-multimedia.md`). Sin el stub, este experimento no se podía hacer.
- Hace posible el **catálogo C** (§2.2), que no existe como servidor.
- Es **barato**: 540 ejecuciones en lugar de 540 transcodificaciones.

Lo que el stub **no** replica es el comportamiento del servidor tras la llamada. Como lo que se mide
es **la elección**, eso no afecta al resultado; sí lo declararía si se midiera recuperación de
errores. Verificación del instrumento: en las 540 ejecuciones el modelo hizo `tools/list`
exactamente **una vez** por ejecución, y ninguna llamada fue a un nombre inexistente.

---

## 2. El diseño experimental

### 2.1 La propiedad que hace la comparación válida

Los dos catálogos reales **cubren el mismo dominio** —conversión de vídeo y audio— así que para una
misma petición **existe una respuesta correcta comparable en los dos**. Sin esa propiedad la
comparación no diría nada sobre la elección: diría solo que un servidor hace cosas que el otro no.

**Esa propiedad se cumple parcialmente, y donde no se cumple lo declaramos antes de medir**
(tareas `E2d`, `E4a`, `E4c`: §2.3).

### 2.2 Las tres condiciones

| Cond. | Catálogo | Herr. | `tokens_catalogo` | Diseño |
|---|---|---:|---:|---|
| **A** | `video-audio-mcp` completo | **27** | **7.886** | plano, agrupado por *parámetro de ffmpeg*, 39,7 % redundante |
| **C** | `video-audio-mcp` **sin las 13 subsumidas** | **14** | **4.749** | *idéntico* a A en estilo, nombres y descripciones — **solo se le quita la redundancia** |
| **B** | `ffmpeg-mcp-lite` | **8** | **2.306** | agrupado por *intención del usuario* |

**El catálogo C es la aportación metodológica de este informe.** A y B difieren a la vez en tamaño,
en autor, en estilo de nombres y en filosofía de agrupación: comparar solo A con B no permite
atribuir nada al tamaño. **C aísla la variable**: es A menos exactamente las 13 herramientas que
`bench/mcp-refs-multimedia.md` §5.1 demostró estrictamente subsumidas. Mismo autor, mismos nombres,
mismas descripciones, mismo estilo. **A vs C mide el efecto de la redundancia con todo lo demás
constante.** A vs B mide el efecto conjunto de tamaño y diseño.

Los tres `tokens_catalogo` están recontados aquí con el mismo tokenizador que el resto del proyecto
(`tiktoken`/`o200k_base`) sobre la serialización del catálogo; salen 1 % por debajo de las cifras
publicadas (7.886 frente a 7.964; 2.306 frente a 2.322) por un detalle de serialización, y **la
proporción entre catálogos es la misma**. El de C, 4.749, coincide con los «4.801 tokens y 14
herramientas» que §5.1 estimó.

### 2.3 Las peticiones: cuatro estratos, 12 tareas

Todas en español, redactadas como las escribiría un usuario. La lista literal, con la clave de
corrección de cada una y para cada catálogo, está en `bench/salidas-saturacion/tareas.json`.

| Estrato | Qué prueba | Tareas |
|---|---|---|
| **1** | **Control.** Inequívocas. Si aquí falla algo, el experimento está mal montado. | `E1a` extraer audio · `E1b` recortar · `E1c` cambiar contenedor |
| **2** | **Ambiguas por solapamiento**, con una pista explícita en la petición. Caen en la zona de las 13 subsumidas y de las cinco `set_video_audio_track_…`. | `E2a` bajar resolución · `E2b` códec de la pista de audio · `E2c` formato **y** bitrate de audio (la trampa de subsunción) · `E2d` bitrate de la pista de audio de un vídeo (**el par peor** según §5.2) |
| **3** | **Exigen encadenar** dos herramientas, en orden. | `E3a` recortar → extraer audio · `E3b` unir → reescalar |
| **4** | **Ambiguas sin pista.** Añadidas tras el piloto y **antes** de medir el grid, porque el piloto mostró efecto techo. | `E4a` ablación de `E2d` sin la pista · `E4b` petición al nivel de la intención («pesa 4 GB, arréglalo») · `E4c` capacidad que **solo** tiene el catálogo pequeño |

`E4a` es la pieza más informativa del diseño: **es `E2d` con la pista quitada**, así que el par
`E2d`/`E4a` mide cuánto de la elección correcta venía de la petición y cuánto del catálogo.

### 2.4 El criterio de acierto, declarado antes de medir

Está escrito en `tareas.json` y fue fijado **antes** de lanzar el grid. Ataca de frente el sesgo
obvio —un catálogo con más herramientas tiene más formas de acertar *y* más de fallar— midiendo
**las dos cosas a la vez**:

| Métrica | Definición |
|---|---|
| **Acierto estricto** | la primera llamada sustantiva es **la mejor** herramienta: la que resuelve la petición entera sin perder ningún requisito |
| **Acierto permisivo** | la primera llamada sustantiva está en **`acepta`**: *alguna* que resuelve la tarea |
| **Petición cumplida entera** | los valores pedidos (`192`, `720`, `96`…) **aparecen en los argumentos** de alguna llamada. Es la métrica que castiga elegir una herramienta subsumida: `convert_audio_format` no tiene dónde meter el bitrate |
| **Elección trampa** | la primera llamada sustantiva está en el conjunto `trampa` **declarado de antemano**: produce un fichero incorrecto **sin dar error** |
| **Abstención** | ninguna llamada sustantiva. **Es el acierto** en las tareas donde el catálogo no puede hacer lo que se pide (`E2d`/`E4a` en B, `E4c` en A y C) |

Reglas auxiliares: `health_check` y `ffmpeg_get_info` son diagnóstico y **no cuentan** como llamada
sustantiva (son preámbulo legítimo). En el estrato 3 el acierto estricto exige **la secuencia
ordenada** completa.

La lista de `requisitos_args` de cada tarea se fijó tras el piloto y **antes** de puntuar el grid.

### 2.5 Repeticiones, temperatura y potencia

- **Haiku 4.5: 10 repeticiones** × 12 tareas × 3 catálogos = **360 ejecuciones**.
- **Sonnet: 5 repeticiones** × 12 tareas × 3 catálogos = **180 ejecuciones**.
- **Total: 540 ejecuciones independientes.**
- **La temperatura no es fijable por el CLI y no se declara.** Es la limitación más seria del
  instrumento y se trata en §8. Las repeticiones miden la variabilidad real del sujeto tal como
  FileX se lo encontrará, no la de un parámetro controlado.
- Contraste: **Fisher exacto bilateral**; intervalos: **Wilson al 95 %**.
- Con n = 120 por celda en Haiku, el experimento detecta una caída de 100 % a ≈ 93 % con potencia
  razonable. **No** detecta caídas de 2-3 puntos: eso queda **PENDIENTE** y así se dice en §6.

---

## 3. Resultados

### 3.1 Lo primero: el control funciona (MEDIDO)

**Estrato 1, los tres catálogos, los dos modelos: 100 % de acierto estricto y 0 % de trampas en las
90 ejecuciones de control.** El experimento está bien montado: cuando la petición es inequívoca y la
herramienta existe, el modelo la encuentra tanto entre 8 como entre 27.

Y el instrumento se comporta: en las **540** ejecuciones el código de salida fue **0** siempre, el
modelo pidió `tools/list` **exactamente una vez** por ejecución, y **no hubo ni una sola llamada a un
nombre de herramienta inexistente**.

### 3.2 El resultado que se buscaba, en una tabla (MEDIDO)

| | **A · 27 herr.** | **C · 14 herr.** | **B · 8 herr.** |
|---|---:|---:|---:|
| **Haiku 4.5** (n = 120 por celda) | | | |
| acierto estricto | 93 % | **100 %** | 82 % |
| acierto permisivo | **100 %** | **100 %** | 85 % |
| **elección trampa** | **0 %** | **0 %** | **15 %** |
| **Sonnet 4.5** (n = 60 por celda) | | | |
| acierto estricto | 90 % | 93 % | 68 % |
| acierto permisivo | **98 %** | 93 % | 77 % |
| **elección trampa** | **2 %** | 7 % | **17 %** |

**El catálogo de 27 herramientas no eligió peor que el de 8. Eligió mejor, y por un margen amplio y
significativo en los dos modelos** (acierto permisivo, Fisher exacto bilateral: p < 0,001 en Haiku,
p < 0,001 en Sonnet).

### 3.3 La predicción estructural más fuerte del proyecto **no se cumplió** (MEDIDO)

`bench/mcp-refs-multimedia.md` §5.2 señaló un par como «el peor»:

> El par **`set_audio_bitrate` / `set_video_audio_track_bitrate`** es el peor: nombres casi
> idénticos, descripciones casi idénticas, y la equivocación **no da error** — produce un fichero
> incorrecto.

Las tareas `E2d` y `E4a` apuntan exactamente a ese par, con pista y sin ella. El resultado sobre el
catálogo A completo:

| Modelo | Tarea | Elección | n |
|---|---|---|---:|
| Haiku | `E2d` (con pista) | `set_video_audio_track_bitrate` | **10 / 10** |
| Haiku | `E4a` (**sin** pista) | `set_video_audio_track_bitrate` | **10 / 10** |
| Sonnet | `E2d` | `set_video_audio_track_bitrate` | **5 / 5** |
| Sonnet | `E4a` | `set_video_audio_track_bitrate` | **5 / 5** |

**30 de 30. Ni una sola vez eligió `set_audio_bitrate`.** El análisis de firmas predijo un fallo que
el comportamiento no produce: la distinción `input_audio_path` / `input_video_path` —lo único que
separa las dos herramientas (§5.3)— **basta**. Es el resultado que cierra la Pregunta 2, y es un
resultado negativo: **la ambigüedad estructural que se puede medir en un catálogo no se traduce
automáticamente en errores de elección.**

### 3.4 Quitar la redundancia no mejora la elección (MEDIDO)

El contraste **A vs C** —27 herramientas frente a las mismas 27 menos las 13 subsumidas, con todo lo
demás idéntico— es la medida limpia del efecto de la redundancia:

| Modelo | Métrica | A (27) | C (14) | p |
|---|---|---:|---:|---:|
| Haiku | estricta | 93 % | 100 % | **0,007** |
| Haiku | permisiva | **100 %** | **100 %** | 1,000 |
| Sonnet | estricta | 90 % | 93 % | 0,743 |
| Sonnet | permisiva | 98 % | 93 % | 0,364 |

La única diferencia significativa es el acierto **estricto** en Haiku, y **procede íntegramente de
una sola tarea, `E4b`, cuya clave de «mejor herramienta» es un juicio discutible mío**, no un fallo
del modelo. En `E4b` («boda.mp4 pesa 4 GB, arréglalo») declaré `set_video_bitrate` como la mejor; el
modelo eligió `convert_video_properties` y bajó a la vez resolución y bitrates —una solución al
menos tan buena, contada como «resuelve» pero no como «mejor». En C esa herramienta no existe, así
que allí la elección coincide con la clave por construcción.

**Análisis de sensibilidad (MEDIDO), quitando esa única tarea:**

| Modelo | Excluyendo | A (27) | C (14) | p |
|---|---|---:|---:|---:|
| Haiku | `E4b` | **100 %** (110/110) | **100 %** (110/110) | 1,000 |
| Sonnet | `E4b` | 98 % (54/55) | 93 % (51/55) | 0,363 |
| Haiku | `E4b` y `E4c` | **100 %** (100/100) | **100 %** (100/100) | 1,000 |
| Sonnet | `E4b` y `E4c` | **100 %** (50/50) | **100 %** (50/50) | 1,000 |

> **MEDIDO: el 39,7 % de redundancia del catálogo A no produce ningún error de elección atribuible
> a ella.** Ni en los 351 pares posibles, ni en las 13 herramientas subsumidas, ni en las cinco
> `set_video_audio_track_…`.

### 3.5 Dónde sí falla la elección: cobertura, no tamaño (MEDIDO)

Las 28 trampas del experimento —18 en Haiku, 10 en Sonnet— se concentran **todas** en tareas que el
catálogo elegido **no puede hacer**, y la mayoría son del catálogo pequeño:

| Tarea | Qué se pide | Catálogo que no puede | Comportamiento medido |
|---|---|---|---|
| `E2d`, `E4a` | fijar el bitrate de la pista de audio de un vídeo | **B (8)** — ninguna de sus 8 herramientas tiene ese parámetro | llama a `ffmpeg_convert` y **declara éxito**: acierto estricto 10 % (Haiku), 0 % (Sonnet) |
| `E4c` | sacar un fotograma como imagen | **A (27) y C (14)** — ninguna extrae fotogramas | Haiku se abstiene **100 %** en las dos; Sonnet se abstiene 80 % en A y solo **20 % en C** |

Las respuestas literales son lo más elocuente del informe:

> **B · `E2d` · Haiku** — llamó a `ffmpeg_convert`, que no acepta bitrate de audio:
> «*El archivo entrevista_lig.mp4 se ha creado con el audio re-codificado en AAC, **reduciendo el
> bitrate del audio desde los 320 kbps originales** sin recomprimir el video.*»
> El dato es **falso** y los 96 kbps que pidió el usuario **no se han aplicado**. No hay error.

> **C · `E4c` · Sonnet** — llamó a `convert_video_properties`, que no extrae fotogramas:
> «*He extraído un fotograma de intro.mp4 y lo guardé como imagen de portada en **portada.jpg**.*»
> También es falso.

> **A · `E4c` · Haiku** — la conducta correcta, y la que se dio el 100 % de las veces:
> «*No tengo una herramienta disponible para extraer fotogramas de un vídeo. […] Te recomendaría
> usar otro software.*»

**El fallo que importa no es elegir mal entre muchas herramientas: es inventar que una herramienta
hace algo que no hace, cuando la que hace falta no está.** Y ese fallo lo produce el **hueco de
cobertura**, en cualquier catálogo, grande o pequeño.

### 3.6 Lo que el catálogo grande sí cuesta: tokens en cada turno (MEDIDO)

| Modelo | Catálogo | `tokens_catalogo` | **Tokens de entrada por petición** | Turnos medios |
|---|---|---:|---:|---:|
| Sonnet | A (27) | 7.886 | **23.583** | 2,12 |
| Sonnet | C (14) | 4.749 | **15.734** | 2,18 |
| Sonnet | B (8) | 2.306 | **8.826** | 2,23 |
| Haiku | A (27) | 7.886 | **19.182** | 2,08 |
| Haiku | C (14) | 4.749 | **12.869** | 2,08 |
| Haiku | B (8) | 2.306 | **8.264** | 2,17 |

De ahí sale el multiplicador marginal: **cada token de catálogo cuesta entre 2,0 y 2,6 tokens de
entrada por petición**, porque el catálogo **se paga en cada turno del intercambio, no una vez**.
(Las cifras de Haiku para B están afectadas por un reparto desigual de aciertos de caché entre
ejecuciones concurrentes; las de Sonnet son limpias y las tres están dominadas por lectura de caché.)

> **Ese es el argumento que sostiene el objetivo de FileX, y es el único: el coste.** Un catálogo de
> 7.886 tokens cuesta ≈ 23.600 tokens de entrada por petición sencilla; uno de 2.306, ≈ 8.800.
> **×2,7, y sin ninguna mejora de elección a cambio.**

---

## 4. Las tablas completas

<details>
<summary><b>Haiku 4.5 — 360 ejecuciones (desplegar)</b></summary>

#### Modelo: Haiku 4.5 — n = 360 ejecuciones

##### Global

| Catálogo | n | Acierto estricto (IC 95 %) | Acierto permisivo | Petición cumplida entera | Elección trampa |
|---|---:|---:|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 120 | **93 %** [0.87–0.97] | 100 % | 92 % | 0 % |
| C · 14 herr. · 4.749 tok | 120 | **100 %** [0.97–1.00] | 100 % | 92 % | 0 % |
| B · 8 herr. · 2.306 tok | 120 | **82 %** [0.74–0.88] | 85 % | 86 % | 15 % |

##### Estrato 1 · inequívocas (control)

| Catálogo | n | Acierto estricto (IC 95 %) | Acierto permisivo | Petición cumplida entera | Elección trampa |
|---|---:|---:|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 30 | **100 %** [0.89–1.00] | 100 % | 100 % | 0 % |
| C · 14 herr. · 4.749 tok | 30 | **100 %** [0.89–1.00] | 100 % | 100 % | 0 % |
| B · 8 herr. · 2.306 tok | 30 | **100 %** [0.89–1.00] | 100 % | 100 % | 0 % |

##### Estrato 2 · ambiguas con pista

| Catálogo | n | Acierto estricto (IC 95 %) | Acierto permisivo | Petición cumplida entera | Elección trampa |
|---|---:|---:|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 40 | **100 %** [0.91–1.00] | 100 % | 100 % | 0 % |
| C · 14 herr. · 4.749 tok | 40 | **100 %** [0.91–1.00] | 100 % | 100 % | 0 % |
| B · 8 herr. · 2.306 tok | 40 | **70 %** [0.55–0.82] | 78 % | 75 % | 22 % |

##### Estrato 3 · encadenadas

| Catálogo | n | Acierto estricto (IC 95 %) | Acierto permisivo | Petición cumplida entera | Elección trampa |
|---|---:|---:|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 20 | **100 %** [0.84–1.00] | 100 % | 100 % | 0 % |
| C · 14 herr. · 4.749 tok | 20 | **100 %** [0.84–1.00] | 100 % | 100 % | 0 % |
| B · 8 herr. · 2.306 tok | 20 | **95 %** [0.76–0.99] | 100 % | 100 % | 0 % |

##### Estrato 4 · ambiguas sin pista

| Catálogo | n | Acierto estricto (IC 95 %) | Acierto permisivo | Petición cumplida entera | Elección trampa |
|---|---:|---:|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 30 | **73 %** [0.56–0.86] | 100 % | 67 % | 0 % |
| C · 14 herr. · 4.749 tok | 30 | **100 %** [0.89–1.00] | 100 % | 67 % | 0 % |
| B · 8 herr. · 2.306 tok | 30 | **70 %** [0.52–0.83] | 70 % | 77 % | 30 % |

##### Por tarea (acierto estricto)

| Tarea | Estrato | A (27) | C (14) | B (8) |
|---|---:|---:|---:|---:|
| E1a | 1 | 100 % | 100 % | 100 % |
| E1b | 1 | 100 % | 100 % | 100 % |
| E1c | 1 | 100 % | 100 % | 100 % |
| E2a | 2 | 100 % | 100 % | 70 % |
| E2b | 2 | 100 % | 100 % | 100 % |
| E2c | 2 | 100 % | 100 % | 100 % |
| E2d | 2 | 100 % | 100 % | 10 % |
| E3a | 3 | 100 % | 100 % | 100 % |
| E3b | 3 | 100 % | 100 % | 90 % |
| E4a | 4 | 100 % | 100 % | 10 % |
| E4b | 4 | 20 % | 100 % | 100 % |
| E4c | 4 | 100 % | 100 % | 100 % |

##### Contrastes (Fisher exacto bilateral)

| Métrica | A (27) | C (14) | p (A vs C) | B (8) | p (A vs B) |
|---|---:|---:|---:|---:|---:|
| acierto estricto | 93 % | 100 % | 0.007 **\*** | 82 % | 0.010 **\*** |
| acierto permisivo | 100 % | 100 % | 1.000 | 85 % | 0.000 **\*** |
| petición cumplida entera | 92 % | 92 % | 1.000 | 86 % | 0.220 |
| elección trampa | 0 % | 0 % | 1.000 | 15 % | 0.000 **\*** |

##### Coste de la decisión (no de la conversión)

| Catálogo | Coste medio USD/petición | Latencia media | Llamadas sustantivas medias |
|---|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 0.0066 | 12.2 s | 1.08 |
| C · 14 herr. · 4.749 tok | 0.0065 | 12.1 s | 1.08 |
| B · 8 herr. · 2.306 tok | 0.0168 | 18.1 s | 1.17 |

##### Distribución de clases

| Catálogo | abstencion | incompleta | mejor | resuelve | secuencia_exacta | trampa |
|---|---|---|---|---|---|---|
| A · 27 herr. · 7.886 tok | 10 | 0 | 82 | 8 | 20 | 0 |
| C · 14 herr. · 4.749 tok | 10 | 0 | 90 | 0 | 20 | 0 |
| B · 8 herr. · 2.306 tok | 2 | 1 | 77 | 3 | 19 | 18 |

</details>

<details>
<summary><b>Sonnet 4.5 — 180 ejecuciones (desplegar)</b></summary>

#### Modelo: Sonnet 4.5 — n = 180 ejecuciones

##### Global

| Catálogo | n | Acierto estricto (IC 95 %) | Acierto permisivo | Petición cumplida entera | Elección trampa |
|---|---:|---:|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 60 | **90 %** [0.80–0.95] | 98 % | 93 % | 2 % |
| C · 14 herr. · 4.749 tok | 60 | **93 %** [0.84–0.97] | 93 % | 98 % | 7 % |
| B · 8 herr. · 2.306 tok | 60 | **68 %** [0.56–0.79] | 77 % | 90 % | 17 % |

##### Estrato 1 · inequívocas (control)

| Catálogo | n | Acierto estricto (IC 95 %) | Acierto permisivo | Petición cumplida entera | Elección trampa |
|---|---:|---:|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 15 | **100 %** [0.80–1.00] | 100 % | 100 % | 0 % |
| C · 14 herr. · 4.749 tok | 15 | **100 %** [0.80–1.00] | 100 % | 100 % | 0 % |
| B · 8 herr. · 2.306 tok | 15 | **100 %** [0.80–1.00] | 100 % | 100 % | 0 % |

##### Estrato 2 · ambiguas con pista

| Catálogo | n | Acierto estricto (IC 95 %) | Acierto permisivo | Petición cumplida entera | Elección trampa |
|---|---:|---:|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 20 | **100 %** [0.84–1.00] | 100 % | 100 % | 0 % |
| C · 14 herr. · 4.749 tok | 20 | **100 %** [0.84–1.00] | 100 % | 100 % | 0 % |
| B · 8 herr. · 2.306 tok | 20 | **35 %** [0.18–0.57] | 55 % | 75 % | 25 % |

##### Estrato 3 · encadenadas

| Catálogo | n | Acierto estricto (IC 95 %) | Acierto permisivo | Petición cumplida entera | Elección trampa |
|---|---:|---:|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 10 | **100 %** [0.72–1.00] | 100 % | 100 % | 0 % |
| C · 14 herr. · 4.749 tok | 10 | **100 %** [0.72–1.00] | 100 % | 100 % | 0 % |
| B · 8 herr. · 2.306 tok | 10 | **90 %** [0.60–0.98] | 100 % | 100 % | 0 % |

##### Estrato 4 · ambiguas sin pista

| Catálogo | n | Acierto estricto (IC 95 %) | Acierto permisivo | Petición cumplida entera | Elección trampa |
|---|---:|---:|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 15 | **60 %** [0.36–0.80] | 93 % | 73 % | 7 % |
| C · 14 herr. · 4.749 tok | 15 | **73 %** [0.48–0.89] | 73 % | 93 % | 27 % |
| B · 8 herr. · 2.306 tok | 15 | **67 %** [0.42–0.85] | 67 % | 93 % | 33 % |

##### Por tarea (acierto estricto)

| Tarea | Estrato | A (27) | C (14) | B (8) |
|---|---:|---:|---:|---:|
| E1a | 1 | 100 % | 100 % | 100 % |
| E1b | 1 | 100 % | 100 % | 100 % |
| E1c | 1 | 100 % | 100 % | 100 % |
| E2a | 2 | 100 % | 100 % | 20 % |
| E2b | 2 | 100 % | 100 % | 100 % |
| E2c | 2 | 100 % | 100 % | 20 % |
| E2d | 2 | 100 % | 100 % | 0 % |
| E3a | 3 | 100 % | 100 % | 100 % |
| E3b | 3 | 100 % | 100 % | 80 % |
| E4a | 4 | 100 % | 100 % | 0 % |
| E4b | 4 | 0 % | 100 % | 100 % |
| E4c | 4 | 80 % | 20 % | 100 % |

##### Contrastes (Fisher exacto bilateral)

| Métrica | A (27) | C (14) | p (A vs C) | B (8) | p (A vs B) |
|---|---:|---:|---:|---:|---:|
| acierto estricto | 90 % | 93 % | 0.743 | 68 % | 0.006 **\*** |
| acierto permisivo | 98 % | 93 % | 0.364 | 77 % | 0.000 **\*** |
| petición cumplida entera | 93 % | 98 % | 0.364 | 90 % | 0.743 |
| elección trampa | 2 % | 7 % | 0.364 | 17 % | 0.008 **\*** |

##### Coste de la decisión (no de la conversión)

| Catálogo | Coste medio USD/petición | Latencia media | Llamadas sustantivas medias |
|---|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 0.0147 | 10.2 s | 1.12 |
| C · 14 herr. · 4.749 tok | 0.0129 | 10.5 s | 1.18 |
| B · 8 herr. · 2.306 tok | 0.0118 | 11.5 s | 1.23 |

##### Distribución de clases

| Catálogo | abstencion | incompleta | mejor | parcial | resuelve | secuencia_exacta | trampa |
|---|---|---|---|---|---|---|---|
| A · 27 herr. · 7.886 tok | 4 | 0 | 40 | 0 | 5 | 10 | 1 |
| C · 14 herr. · 4.749 tok | 1 | 0 | 45 | 0 | 0 | 10 | 4 |
| B · 8 herr. · 2.306 tok | 0 | 1 | 32 | 4 | 4 | 9 | 10 |

</details>


---

## 5. Lo medible sin modelo

Estas métricas son **deterministas y reproducibles sin ningún LLM**:
`bench/salidas-saturacion/estatico.py` → `estatico.json`. Miden la ambigüedad que un catálogo
**presenta**, no la que un modelo **sufre** — y el interés de tenerlas junto a §3 es precisamente
poder comparar las dos cosas.

### 5.1 Ambigüedad léxica de los nombres

Similitud por `difflib.SequenceMatcher` sobre el nombre, y Jaccard sobre los tokens de `snake_case`.

| Métrica | **A (27)** | **C (14)** | **B (8)** |
|---|---:|---:|---:|
| Pares posibles | 351 | 91 | 28 |
| Pares con similitud de **nombre** ≥ 0,70 | **22** | 2 | 2 |
| Familias de prefijo con ≥ 3 miembros | `set_video` (8), `set_video_audio_track` (4), `set_video_audio` (4), `set_audio` (3) | **ninguna** | **ninguna** |

Los cinco peores pares del catálogo A son los cinco cruces de la familia
`set_video_audio_track_…`, con similitud de nombre 0,77–0,84 **y de descripción 0,88–0,94**.

### 5.2 Herramientas indistinguibles por su descripción sola

Se recorta la descripción a su parte útil (se elimina el bloque `Args:`/`Returns:`, que es donde
está la única información que las separa) y se comparan.

| Métrica | **A (27)** | **C (14)** | **B (8)** |
|---|---:|---:|---:|
| Pares con similitud de **descripción** ≥ 0,70 | **31** | 1 | 1 |
| … ≥ 0,85 (prácticamente el mismo texto) | **13** | **0** | **0** |
| Herramientas con al menos un gemelo por descripción | **51,9 %** | 14,3 % | 25,0 % |
| **Confundibles por nombre *y* descripción a la vez** | **48,1 %** (13 de 27) | 14,3 % (2) | 25,0 % (2) |

**Casi la mitad del catálogo A tiene otra herramienta con la que se confunde por los dos canales a
la vez.** Y las 13 que salen de este filtro puramente léxico son **exactamente las mismas 13** que
`bench/mcp-refs-multimedia.md` §5.1 identificó como estrictamente subsumidas por análisis de
firmas. Dos métodos independientes, el mismo conjunto: es una validación cruzada, no una
coincidencia.

### 5.3 Solapamiento de los esquemas de parámetros

Se define la **firma de forma** de una herramienta: la multiplicidad ordenada de
`(tipo JSON, obligatorio)` de sus argumentos. **Dos herramientas con la misma firma de forma son
indistinguibles para quien mire solo el esquema: mismo número de argumentos, mismos tipos, misma
obligatoriedad. Solo los *nombres* de los argumentos las separan.**

| Métrica | **A (27)** | **C (14)** | **B (8)** |
|---|---:|---:|---:|
| Pares con parámetros anidados (uno ⊆ otro) | **40** | 14 | 6 |
| Herramientas en una **forma de esquema compartida** | **15 (55,6 %)** | 2 (14,3 %) | **0 (0 %)** |
| **Indistinguibles salvo por el nombre de sus argumentos** | **10 (37,0 %)** | **0** | **0** |

Las dos formas compartidas grandes de A:

- `(string obl., string obl., string obl.)` → **8 herramientas**: `convert_audio_format`,
  `set_audio_bitrate`, `convert_video_format`, `set_video_resolution`, `set_video_codec`,
  `set_video_bitrate`, `set_video_audio_track_codec`, `set_video_audio_track_bitrate`.
- `(integer obl., string obl., string obl.)` → **5 herramientas**: `set_audio_sample_rate`,
  `set_audio_channels`, `set_video_frame_rate`, `set_video_audio_track_sample_rate`,
  `set_video_audio_track_channels`.

**Trece herramientas de A —el 48 %— caben en dos moldes.** `set_audio_bitrate` y
`set_video_audio_track_bitrate` tienen la misma forma, descripciones con similitud 0,88, y lo único
que las distingue es que una llama a su primer argumento `input_audio_path` y la otra
`input_video_path`. Ese es, literalmente, **todo** el margen que el catálogo le da al modelo para
no equivocarse.

### 5.4 El hallazgo que no se buscaba: ningún parámetro está documentado

| Métrica | **A (27)** | **C (14)** | **B (8)** |
|---|---:|---:|---:|
| Parámetros declarados | 102 | 63 | 28 |
| Parámetros **con `description` en el JSON Schema** | **0** | **0** | **0** |

**MEDIDO: 0 de 193 parámetros, en los tres catálogos, lleva descripción en su esquema.** Solo
llevan un `title` autogenerado (`"input_audio_path"` → `"Input Audio Path"`), que no añade nada.
FastMCP deriva el esquema de las anotaciones de tipo, y **la semántica de los argumentos vive
únicamente en la prosa del docstring**.

Eso convierte el defecto de §5.5 en un fallo total, no parcial. `add_b_roll` declara como
obligatorio:

```json
"broll_clips": { "items": { "additionalProperties": true, "type": "object" },
                 "title": "Broll Clips", "type": "array" }
```

—un array de objetos arbitrarios sin una sola clave— y su descripción dice *«Args listed in
previous messages»*. **Entre esquema y descripción, la información disponible para construir la
llamada es cero.**

### 5.5 Descripciones que remiten a documentos invisibles y esquemas opacos

| | **A (27)** | **C (14)** | **B (8)** |
|---|---:|---:|---:|
| Descripciones marcadas por el filtro léxico | 4 | 4 | **0** |
| … **verdaderos positivos** tras revisión | **3** | 3 | **0** |
| Esquemas opacos (`object`/`array of object` sin claves declaradas) | **3** | 3 | **0** |

En A los verdaderos positivos son `convert_video_properties` y `change_aspect_ratio` («Args listed
in PRD») y `add_b_roll` («previous messages», «for brevity») — **los mismos tres** que
`bench/mcp-refs-multimedia.md` §5.3 había marcado leyéndolos a mano. El filtro marca además
`remove_silence`, y es un **falso positivo**: su «*the noise level below which is considered
silence*» es un uso legítimo de la palabra. Conviene registrarlo, porque la prueba automática que
se propone en §7 tendrá esa tasa de falsos positivos y debe permitir excepciones anotadas.

Esquemas opacos en A: `add_subtitles.font_style`, `add_text_overlay.text_elements`,
`add_b_roll.broll_clips`.

**`ffmpeg-mcp-lite` tiene cero de las dos cosas.** Es su ventaja real, y no tiene nada que ver con
el tamaño.

### 5.6 Qué fracción del catálogo no sabría desambiguar un lector

Uniendo los tres canales —nombre, descripción y forma del esquema—:

| Catálogo | Fracción confundible por nombre + descripción | Fracción indistinguible salvo por el nombre de los argumentos |
|---|---:|---:|
| **A (27)** | **48,1 %** | **37,0 %** |
| **C (14)** | 14,3 % | **0 %** |
| **B (8)** | 25,0 % | **0 %** |

Esas son las cifras que un lector humano —y cualquier prueba automática— puede calcular sobre un
catálogo **antes de exponerlo**, sin ejecutar un modelo. Son la base de la regla que se propone en
§7.

---

## 6. Veredicto

### 6.1 ¿27 herramientas degradan la elección?

> **MEDIDO: no.** En 540 ejecuciones, dos modelos y cuatro estratos de dificultad, el catálogo de
> **27** herramientas obtuvo **100 % / 98 %** de acierto permisivo (Haiku / Sonnet) y **0 % / 2 %**
> de elecciones trampa. El de **8**, **85 % / 77 %** y **15 % / 17 %**. **El catálogo grande eligió
> mejor, no peor.**
>
> **MEDIDO: la redundancia tampoco.** El contraste limpio A (27) vs C (14) —el mismo catálogo con y
> sin las 13 herramientas subsumidas— no muestra ninguna diferencia una vez se quita la única tarea
> cuya clave de corrección era un juicio discutible: **100 % vs 100 %** en Haiku y en Sonnet.
>
> **MEDIDO: la ambigüedad estructural no predijo el comportamiento.** El par que
> `bench/mcp-refs-multimedia.md` §5.2 declaró «el peor» del catálogo acertó **30 de 30**.

**Y la parte incómoda del resultado:** el 48,1 % de herramientas confundibles, el 37 % de
indistinguibles salvo por el nombre de sus argumentos y los 13 pares con descripciones casi
idénticas de §5 **son reales y están medidos** — pero **el modelo los desambigua igual**. La
ambigüedad léxica de un catálogo es un indicador de **mala higiene de interfaz**, no un predictor
de errores de elección. Este informe es la evidencia de que no hay que confundir las dos cosas.

### 6.2 ¿Se sostiene el objetivo de cuatro herramientas de FileX?

> **Sí, pero por una sola razón: el coste. La conductual no aparece.**

Era exactamente la pregunta del encargo, y la respuesta es la que no se esperaba:

| Argumento para exponer pocas herramientas | Estado |
|---|---|
| **Coste en tokens** | **MEDIDO y confirmado, y peor de lo que se creía**: el catálogo se paga **en cada turno**, con un multiplicador de **×2,0–2,6**. Un catálogo de 7.886 tokens cuesta ≈ 23.600 tokens de entrada por petición sencilla. |
| **Calidad de la elección** | **MEDIDO: no aporta nada.** 27 herramientas no degradaron la elección frente a 8 ni frente a 14. **El segundo argumento independiente que se buscaba no existe.** |
| **Riesgo nuevo, en dirección contraria** | **MEDIDO**: un catálogo demasiado escueto para su dominio produce **fallos silenciosos**: el modelo llama a la herramienta más parecida y **declara éxito con un dato falso**. 15–17 % de las peticiones en el catálogo de 8. |

La decisión de FileX —cuatro herramientas— **no cambia**. Lo que cambia es su **justificación** y,
sobre todo, **lo que hay que hacer además**: si las cuatro herramientas de FileX no cubren lo que el
usuario pide, el modelo **no dirá que no puede**; inventará que sí. Eso convierte la **cobertura
declarada** de `convert` en un requisito de seguridad, no de comodidad.

### 6.3 Lo que este experimento **no** demuestra

- **No** demuestra que el tamaño del catálogo sea irrelevante **en general**. Demuestra que **entre
  8 y 27 herramientas, en un dominio, con dos modelos de la familia Claude, no se detectó
  degradación.** Nada dice de 60, ni de 200, ni de varios servidores MCP a la vez. **PENDIENTE.**
- **No** descarta caídas pequeñas: con n = 120 por celda, una caída de 100 % a 97 % pasaría
  desapercibida. **PENDIENTE.**
- **No** dice nada de modelos de otras familias ni de modelos pequeños locales, que es un escenario
  que FileX contempla. **PENDIENTE.**


---

## 7. Qué presupuesto de catálogo recomendar para FileX

### 7.1 En qué unidad se mide el presupuesto

> **En tokens, no en número de herramientas.** Y este experimento añade la razón conductual de por
> qué el número no sirve: **el número no predijo nada** (27 no eligió peor que 8), mientras que los
> tokens **sí** se pagan, y se pagan **más de una vez**.

La regla vigente (`RESULTADOS-MCP.md` §4) es **≤ 1.200 tokens para las cuatro herramientas**.
**Se confirma, y se le añade la cifra que le faltaba:**

> **MEDIDO: cada token de catálogo cuesta ×2,0–2,6 tokens de entrada por petición**, porque el
> catálogo viaja en cada turno y un intercambio típico tuvo **2,1 turnos**.
>
> **Un catálogo de 1.200 tokens costará ≈ 2.400–3.100 tokens de entrada por petición sencilla.**
> Ese, y no 1.200, es el número que hay que comparar con el resto del presupuesto de contexto.

### 7.2 Las tres reglas que se recomiendan, y de dónde sale cada una

**Regla 1 — presupuesto de tokens (se mantiene, con el multiplicador explícito).**

| | Valor |
|---|---:|
| `tokens_catalogo` de `convert` + `inspect` + `list_targets` + `batch` | **≤ 1.200** |
| Coste real esperado por petición (×2,0–2,6) | **≈ 2.400–3.100 tokens** |
| Referencia: `video-audio-mcp` | 7.886 → **≈ 19.000–23.600** |
| Referencia: `ffmpeg-mcp-lite` | 2.306 → **≈ 8.300–8.800** |

**Regla 2 — el solapamiento se mide, pero como higiene, no como predictor de errores.**

Las métricas de §5 son deterministas, cuestan un segundo y se pueden meter en una prueba automática.
Umbrales que **los tres catálogos de referencia permiten calcular** y que un catálogo de cuatro
herramientas debe cumplir con holgura:

| Métrica (`estatico.py`) | Umbral propuesto | A (27) | C (14) | B (8) |
|---|---:|---:|---:|---:|
| Pares con similitud de nombre ≥ 0,70 | **0** | 22 | 2 | 2 |
| Pares con similitud de descripción ≥ 0,85 | **0** | 13 | 0 | 0 |
| Herramientas **indistinguibles salvo por el nombre de sus argumentos** | **0** | **10 (37 %)** | 0 | 0 |
| Familias de prefijo con ≥ 3 miembros | **0** | 4 | 0 | 0 |
| Descripciones con `PRD` / `previous` / `see` / `above` / `brevity` / `TODO` | **0** (con lista de excepciones anotadas: §5.5 dio 1 falso positivo de 4) | 3 | 3 | 0 |
| Esquemas opacos (`object`/`array of object` sin claves) | **0** | 3 | 3 | 0 |
| **Parámetros sin `description` en el JSON Schema** | **0** | **102 / 102** | **63 / 63** | **28 / 28** |

**La última fila es la más importante y es un hallazgo nuevo de este informe.** **MEDIDO: ninguno de
los 193 parámetros de los tres servidores de referencia lleva descripción en su esquema.** FastMCP
deriva el esquema de las anotaciones de tipo y deja toda la semántica en la prosa del docstring. Para
FileX, cuya herramienta `convert` va a tener parámetros con `enum` generados desde el registro
(`PLAN-ORQUESTADOR.md`), eso es inaceptable: **cada parámetro debe llevar su `description` en el
esquema**, con `Field(description=...)` o equivalente. Es lo que impide que una herramienta acabe
como `add_b_roll`, con un array de objetos arbitrarios y una descripción que remite a documentos
invisibles.

**Regla 3 (nueva, y la que este experimento obliga a añadir) — presupuesto de cobertura.**

El fallo medido no es de exceso, es de defecto: **cuando el catálogo no cubre lo que se pide, el
modelo no se abstiene — inventa que sí lo ha hecho** (§3.5). En el catálogo de 8 herramientas eso
ocurrió en el **15–17 %** de las peticiones. Por tanto:

- **`list_targets` deja de ser una comodidad y pasa a ser el mecanismo de seguridad**: es la única
  herramienta que puede decirle al modelo, **en tiempo de ejecución y sin inventar**, qué
  conversiones existen. Debe ser la respuesta canónica a «¿puedo hacer X?».
- **`convert` debe fallar explícitamente** ante una combinación no soportada, con un mensaje que
  nombre la alternativa. El silencio es el modo de fallo peligroso, no el error.
- **La descripción de `convert` debe declarar sus límites**, no solo sus capacidades. Los tres
  servidores de referencia describen lo que hacen; **ninguno describe lo que no hace**, y ahí es
  exactamente donde se producen los fallos silenciosos.
- **Prueba de regresión recomendada:** un conjunto de peticiones **fuera** de la cobertura de FileX,
  cuyo criterio de acierto es **la abstención**. Es barata (el arnés de este informe la ejecuta tal
  cual) y es la única que detecta este modo de fallo.

### 7.3 Resumen del presupuesto recomendado

| Dimensión | Recomendación | Base |
|---|---|---|
| **Tokens de catálogo** | **≤ 1.200** para las cuatro herramientas | `RESULTADOS-MCP.md` §4, **confirmado** |
| **Coste real a presupuestar** | **≈ 2.400–3.100 tokens/petición** (×2,0–2,6) | **MEDIDO aquí**, §3.6 |
| **Número de herramientas** | **no es el presupuesto**; 4 está bien, pero por coste | **MEDIDO aquí**, §6.2 |
| **Solapamiento** | **0** en las seis métricas de la Regla 2 | **MEDIDO aquí**, §5 — higiene, no predictor |
| **Documentación de parámetros** | **100 %** de los parámetros con `description` | **MEDIDO aquí**, §5.4 |
| **Cobertura** | declarada, consultable vía `list_targets`, y con prueba de abstención | **MEDIDO aquí**, §3.5 |


---

## 8. Limitaciones, dichas sin adornos

1. **La temperatura no está fijada y no se puede fijar.** El CLI de Claude Code no la expone. Las
   repeticiones miden la variabilidad real del sujeto tal como FileX se lo va a encontrar, no la de
   un parámetro controlado. **Es la limitación más seria del instrumento.** Con una clave de API se
   arreglaría en una tarde: el diseño de §2 se ejecuta igual contra la API, fijando `temperature` y
   declarándola. **PENDIENTE.**

2. **Dos modelos, y de la misma familia.** Haiku 4.5 y Sonnet 4.5. El resultado se replica en los
   dos, lo que descarta que sea un artefacto de un modelo, pero **no dice nada de modelos de otras
   familias ni de modelos pequeños locales**, que es un escenario que FileX contempla. **PENDIENTE.**

3. **Un solo dominio, doce peticiones.** Multimedia. Las conclusiones son sobre catálogos de
   conversión de vídeo y audio. **PENDIENTE** replicarlo en el dominio documental
   (`docling-mcp`, 19 herramientas).

4. **El criterio de «mejor herramienta» es un juicio.** `E4b` lo demuestra: mi clave declaraba
   `set_video_bitrate` y el modelo eligió algo al menos igual de bueno. Por eso el informe da
   **siempre las dos métricas** y hace el análisis de sensibilidad de §3.4. **La métrica permisiva
   —«eligió una herramienta que resuelve la tarea»— es la robusta, y es la que sostiene el
   veredicto.**

5. **Los catálogos no son perfectamente pareables.** `video-audio-mcp` no extrae fotogramas;
   `ffmpeg-mcp-lite` no fija el bitrate de la pista de audio de un vídeo. Se declaró **antes de
   medir** (§2.4) que en esos casos la abstención es el acierto, lo que convierte el desajuste en
   una medida útil en lugar de un defecto. Aun así, **las tareas `E2d`, `E4a` y `E4c` no son
   comparaciones de elección entre catálogos equivalentes**, y así están marcadas.

6. **El servidor es un stub.** Sirve los catálogos exactos y registra las llamadas, pero no ejecuta
   ffmpeg. Eso es correcto para medir la **elección** —que es lo que se pedía— y era además la única
   forma de hacerlo sin el deadlock de `video-audio-mcp`. **No sirve** para medir recuperación de
   errores ni corrección real de los ficheros. **PENDIENTE.**

7. **Potencia estadística.** n = 120 por celda en Haiku, 60 en Sonnet. Detecta caídas de ~7 puntos
   desde el 100 %; **no** detecta caídas de 2–3 puntos. Las afirmaciones de «no hay diferencia» son
   **«no se detectó diferencia con esta potencia»**, no «no hay».

8. **Un fallo del arnés, documentado.** La ejecución de Haiku murió en la iteración 274 de 360 con
   `FileNotFoundError: [WinError 2]` al crear el proceso hijo, con 5 hilos concurrentes. Se relanzó
   con 3 hilos y terminó sin incidencias; `correr.py` es reanudable y no repitió ninguna celda.
   Las 360 filas están completas y ninguna tiene `rc != 0`.


---

## 9. Cómo reproducirlo

```bash
# 1. catálogos (ya extraídos de las capturas reales de bench/salidas-mcp-refs/multimedia/)
#    catalogo_A_vam27.json  catalogo_C_vam14.json  catalogo_B_lite8.json

# 2. lo medible sin modelo (determinista, sin LLM, ~1 s)
python bench/salidas-saturacion/estatico.py

# 3. el grid conductual (requiere `claude` autenticado; ~2 h las 540 ejecuciones)
python bench/salidas-saturacion/correr.py --modelo haiku  --reps 10 --hilos 5 --salida grid_haiku.jsonl
python bench/salidas-saturacion/correr.py --modelo sonnet --reps 5  --hilos 4 --salida grid_sonnet.jsonl

# 4. puntuación con el criterio de tareas.json y tablas del informe
python bench/salidas-saturacion/puntuar.py grid_haiku.jsonl
python bench/salidas-saturacion/tablas.py  grid_haiku_puntuado.jsonl "Haiku 4.5"
```

`correr.py` es **reanudable**: relee la salida y no repite ninguna celda `(catálogo, tarea, rep)`
que ya exista.

### Ficheros

| Fichero | Qué es |
|---|---|
| `stub_mcp.py` | servidor MCP stdio sin dependencias que sirve un catálogo y registra las llamadas |
| `tareas.json` | las 12 peticiones y **el criterio de acierto declarado de antemano** |
| `catalogo_A_vam27.json` · `catalogo_C_vam14.json` · `catalogo_B_lite8.json` | los tres catálogos |
| `correr.py` | el arnés |
| `puntuar.py` · `tablas.py` | puntuación y tablas |
| `estatico.py` · `estatico.json` | lo medible sin modelo |
| `grid_haiku.jsonl` · `grid_sonnet.jsonl` | **datos crudos**: una línea por ejecución, con la secuencia de herramientas y sus argumentos |
| `grid_haiku_puntuado.jsonl` · `grid_sonnet_puntuado.jsonl` | los mismos, con la puntuación aplicada |
| `resumen_haiku.txt` · `resumen_sonnet.txt` | la salida completa de `puntuar.py` |
| `tablas_haiku.md` · `tablas_sonnet.md` | las tablas de §4, generadas por `tablas.py` |
| `piloto_haiku.jsonl` | el piloto de 18 ejecuciones que validó el arnés |
| `_seccion*.md` · `_ensamblar.py` | fuentes y ensamblado de este informe (sin transcripción a mano) |

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

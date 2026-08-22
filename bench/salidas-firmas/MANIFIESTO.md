# `bench/salidas-firmas/` — datos crudos de F1 (el vocabulario de firmas del contrato)

**Todo lo que queda aquí es TEXTO** (scripts, `.json` de resultados y logs): **1,9 MB**.
No hay una sola salida binaria versionada. Los ficheros que los censos escriben —los
423 formatos de salida, las 598 aristas reejecutadas y las semillas— **se generan y se
borran dentro de un directorio desechable** (`%TEMP%/…/scratchpad/f1`, fijado con la
variable de entorno `F1_TMP`) y **nunca tocan la raíz del repositorio ni `bench/`**.

**No se ha modificado nada de `bench/salidas-aristas/`**: se lee `muestra.json`,
`semi_entrada.json`, `semi_salida*.json` y se importa `verificador_congelado.py`.
Tampoco se ha tocado `bench/salidas-referencia/referencia.json`, ni `corpus/`, ni
`repos/`, ni ningún documento maestro. **No se ha usado la GPU ni se ha pedido su lock.**

---

## Instrumentos

| Fichero | Qué hace | Orden exacta |
|---|---|---|
| `_analiza_muestra.py` | Lee (sin tocar) `bench/salidas-aristas/muestra.json` y recalcula el punto de partida de E1: cuántos destinos tenían el punto 1 evaluable y **por qué** no lo tenían los demás | `python bench/salidas-firmas/_analiza_muestra.py` |
| `_formatos.py` | Extrae de los 20 adaptadores de ConvertX los formatos de entrada y salida y construye los tres proxies de demanda (patrón oro, SnapOtter, nº de adaptadores) | `python bench/salidas-firmas/_formatos.py` |
| `_censo_firmas.py` | **El censo empírico en Windows**: escribe cada formato de salida de ffmpeg / ImageMagick / Ghostscript 2-3 veces con contenidos distintos y mide qué posiciones de los 64 primeros bytes coinciden | `set F1_TMP=<dir desechable>` · `python bench/salidas-firmas/_censo_firmas.py local` |
| `_cont_firmas.py` | Lo mismo dentro de `filex-convertx` para graphicsmagick, pandoc, calibre, libreoffice, vips, inkscape, potrace, assimp, dasel, libjxl, libheif, vtracer, resvg y dvisvgm | `docker cp bench/salidas-firmas/_cont_firmas.py filex-convertx:/tmp/f1/` · `docker cp bench/salidas-firmas/formatos.json filex-convertx:/tmp/f1/` · `docker exec filex-convertx python3 /tmp/f1/_cont_firmas.py` · `docker cp filex-convertx:/tmp/f1/cont_firmas.json bench/salidas-firmas/firmas_censo_contenedor.json` |
| `_cont_pandoc3.py` | **Control de sesgo de semilla**: repite los 64 destinos de pandoc con una tercera semilla que empieza por prosa en vez de por un título | `docker cp bench/salidas-firmas/_cont_pandoc3.py filex-convertx:/tmp/f1/` · `docker exec filex-convertx python3 /tmp/f1/_cont_pandoc3.py` · `docker cp filex-convertx:/tmp/f1/pandoc3.json bench/salidas-firmas/pandoc3.json` |
| `_clasifica.py` | Junta los dos censos y agrupa los 502 destinos por prefijo común | `python bench/salidas-firmas/_clasifica.py` |
| `_categorias.py` | **Las tres categorías**, con la curación (y su motivo) de los cuatro sesgos del método | `python bench/salidas-firmas/_categorias.py` |
| `_vocabulario.py` | Inventario del vocabulario viejo frente al nuevo | `python bench/salidas-firmas/_vocabulario.py` |
| `_valida_tabla.py` | **La prueba de falsos positivos ancha**: escribe los 385 destinos locales y pasa el punto 1 sobre cada salida legítima | `python bench/salidas-firmas/_valida_tabla.py` |
| `_regresion53.py` | **El listón**: las 53 salidas del patrón oro con los dos motores, más los fallos fabricados | `python bench/salidas-firmas/_regresion53.py` |
| `_remuestra.py` | Reejecuta **la misma muestra de E1** (498 + 100) y mide el punto 1 con el vocabulario viejo y con el nuevo | `python bench/salidas-firmas/_remuestra.py` |
| `_analiza_remuestra.py` | La cifra del informe y el reparto del 88 % | `python bench/salidas-firmas/_analiza_remuestra.py` |
| `_g6.py` | Aplica la regla **G6** a las 598 filas ya medidas rematerializando solo las 188 semillas de entrada, sin volver a convertir | `python bench/salidas-firmas/_g6.py` |
| `_categoria3.py` | La pregunta de diseño: los 22 destinos en los que `magick` entrega un PNG, y el punto ciego del crudo sin cabecera | `python bench/salidas-firmas/_categoria3.py` |
| `_coste.py` | Coste del vocabulario ampliado, con los dos testigos de ruido | `python bench/salidas-firmas/_coste.py` |
| `_inventario_cont.sh` | `command -v` de los 24 binarios dentro del contenedor | `docker cp … filex-convertx:/tmp/inv.sh` · `docker exec filex-convertx sh /tmp/inv.sh` |

## Resultados

| Fichero | Contenido | Sección del informe |
|---|---|---|
| `formatos.json` | Los 895 formatos de entrada y 502 de salida, por adaptador, con los tres proxies de demanda | §1 |
| `firmas_censo_local.json` | Censo empírico de ffmpeg (202), ImageMagick (183) y Ghostscript (18): cabeceras en hexadecimal de cada muestra | §2 |
| `firmas_censo_contenedor.json` | Ídem para los 14 motores del contenedor | §2 |
| `pandoc3.json` | El control de tres semillas sobre los 64 destinos de pandoc | §2.3 |
| `clasificacion.json` | Los 502 destinos con su prefijo común, su longitud y las cabeceras de dos muestras | §2 |
| `categorias.json` | **Los 502 destinos en las tres categorías**, con vocabulario viejo y nuevo, y el motivo de cada veredicto | §3 |
| `vocabulario.json` | Los 24 nombres viejos, los 147 nuevos y las 338 extensiones | §4 |
| `valida_tabla.json` | 385 destinos locales escritos y pasados por el punto 1 | §6.2 |
| `regresion53.json` | Las 53 salidas del patrón oro × 2 motores, más 9 fallos fabricados | §6.1 |
| `remuestra.json` | Las 598 aristas de E1 reejecutadas, con firma vieja, firma nueva y veredicto del punto 1 | §5 |
| `resumen_remuestra.json` | La cifra, el reparto del 88 % y la lista de sospechosos | §5 |
| `g6.json` | Las 19 aristas de la muestra en las que G6 se dispara, con la firma de la entrada de cada uno de los 188 formatos | §5.4 |
| `categoria3.json` | Los 22 destinos que devuelven un PNG y el experimento del crudo | §7 |
| `coste.json` | Coste de `firma_real` viejo/nuevo y del contrato sobre las 53 | §6.3 |
| `muestra_inventario.json` | Los 257 destinos y 188 orígenes distintos de la muestra de E1 | §5 |
| `log-*.txt` | La salida por pantalla de cada tanda, incluidos los testigos de ruido | — |

## Reproducción completa

```
set F1_TMP=%TEMP%\f1
python bench/salidas-firmas/_formatos.py
python bench/salidas-firmas/_censo_firmas.py local
docker cp bench/salidas-firmas/_cont_firmas.py filex-convertx:/tmp/f1/_cont_firmas.py
docker cp bench/salidas-firmas/formatos.json  filex-convertx:/tmp/f1/formatos.json
docker exec filex-convertx python3 /tmp/f1/_cont_firmas.py
docker cp filex-convertx:/tmp/f1/cont_firmas.json bench/salidas-firmas/firmas_censo_contenedor.json
docker cp bench/salidas-firmas/_cont_pandoc3.py filex-convertx:/tmp/f1/_cont_pandoc3.py
docker exec filex-convertx python3 /tmp/f1/_cont_pandoc3.py
docker cp filex-convertx:/tmp/f1/pandoc3.json bench/salidas-firmas/pandoc3.json
python bench/salidas-firmas/_clasifica.py
python bench/salidas-firmas/_categorias.py
python bench/salidas-firmas/_vocabulario.py
python bench/salidas-firmas/_valida_tabla.py
python bench/salidas-firmas/_regresion53.py
python bench/salidas-firmas/_remuestra.py
python bench/salidas-firmas/_analiza_remuestra.py
python bench/salidas-firmas/_g6.py
python bench/salidas-firmas/_categoria3.py
python bench/salidas-firmas/_coste.py
```

**Nada de esto necesita GPU.** El censo local tarda ~4 min, el del contenedor ~13 min
(LibreOffice y Calibre son el 90 %), la reejecución de la muestra ~12 min.

**Semillas.** El censo usa tres imágenes de ruido con semillas y geometrías distintas
(64×48, 100×70, 37×23), tres vídeos con distinto patrón, duración **y pista de audio**,
tres audios (seno 440 Hz, ruido blanco, seno 110 Hz), dos subtítulos y dos PDF. Las
razones de que sean distintos hasta ese punto están en §2.2 del informe: con dos senos
de la misma fase, los formatos de PCM crudo salían con un «marcador» de 64 bytes que era
la señal.

# N28 y C22 — bitrate con audio y patrón multifichero

**Tanda:** A · **recurso:** CPU; GPU no usada.  
**Entorno efectivo:** WSL (`python3` y `ffmpeg` nativos), no Git Bash; los cuatro
contenedores ya existentes se inspeccionaron con `docker ps -a` y no se creó
ninguno. **Etiqueta:** SUCIA: la tanda convivió con la suite integral y no se
levantaron los dos testigos de ruido, por lo que no se publican tiempos como
medida de rendimiento. Las comprobaciones funcionales y cada `rc` sí quedan
registrados.

## N28 — el dato faltante cierra el lado alto

**MEDIDO.** Antes del cambio, la sonda expone `bitrate_bps` del contenedor pero
`None` en las pistas de vídeo y audio de los contenedores. Se reproduce la
trampa 58: quitar un filtro de tipo no habría creado una magnitud que la sonda
no publica.

Se conserva `BITRATE_VIDEO_TOL = 0,60` y la desigualdad original: el lado bajo
se compara contra el contenedor porque el audio sólo suma. Para el lado alto,
`motores.FFmpeg` publica en `decidido` el valor de su `-b:a` como
`bitrate_audio_bps` (por pista); V10 descuenta `n_audio × bitrate_audio_bps`
únicamente cuando aquel dato existe. Sin él, se conserva el `informativo`:
ninguna salida de un motor externo queda aprobada por una suposición.

| Patología con audio | pistas | contenedor b/s | vídeo estimado tras resta | desvío | V10 antes | V10 con dato |
|---|---:|---:|---:|---:|---|---|
| `tipico_crf10_supra` | 1 | 14 185 114 | 14 057 114 | +4 585,70 % | informativo | fallo |
| `tipico_diez_veces_mas` | 1 | 19 608 385 | 19 480 385 | +874,02 % | informativo | fallo |
| `dos_pistas_crf10_supra` | 2 | 6 968 640 | 6 712 640 | +2 137,55 % | informativo | fallo |
| `dos_pistas_diez_veces_mas` | 2 | 15 054 757 | 14 798 757 | +639,94 % | informativo | fallo |

**Conclusión MEDIDA:** N28 se cierra: **4 de 4** celdas patológicas antes
declaradas pasan a `V10 fallo`; junto a las 8 que ya atrapaba el lado bajo,
son **12 de 12**. La prueba de regresión mantiene como no fallo los cuatro
desvíos NVENC históricos, incluido +24,59 %; no se tocó GPU.

**Refutado:** «basta quitar el filtro de audio»; el defecto era ausencia de
dato de pista. También queda refutada la necesidad de una nueva tolerancia:
la de 60 % sigue siendo la decisión.

## C22 — criterio para el quinto punto

**Criterio MEDIDO:** una salida es multifichero legítima si sus ficheros extra
aparecen **en el directorio de destino** y están declarados por formato
(`m3u8`) o por el patrón de nombre (`%03d`). No se usa número de ficheros ni
porcentaje de bytes como disparador: N9 es informativo. Todo fichero nuevo
fuera del destino sigue siendo N5/N6, incluso con `multifichero: true`.

| Caso | rc | antes → después en trabajo | después en destino | punto 5 |
|---|---:|---|---|---|
| HLS `h.m3u8` | 0 | sólo `destino` → igual | manifiesto 114 B + `h000.ts` 244 400 B | N7 y N9 informativos; 0 aviso/fallo |
| Secuencia `f%03d.png` | 0 | sólo `destino` → igual | 20 PNG (`f001`…`f020`) | N9 informativo; 0 aviso/fallo |

**Conclusión MEDIDA:** los dos casos fabricados cubren exactamente el hueco
del patrón oro (que no contiene salidas multifichero) y añaden **0 falsos
positivos**. La reproducción inicial dio N8 espurio porque el arnés medía el
tamaño de un directorio; quedó **REFUTADO** y se corrigió para usar
`censar_dir`, que representa directorios como `-1`, igual que el producto.

## Cambios y verificación

- `filex/motores.py`: publica `bitrate_audio_bps` en el `decidido` de la ruta
  de vídeo.
- `filex/verificador.py`: V10 descuenta esa tasa declarada por cada pista sólo
  para decidir el exceso superior.
- Pruebas nuevas: publicación del dato y detección superior con dos pistas.
- **MEDIDO:** 19 pruebas dirigidas de bitrate/degradación pasan; `py_compile`
  pasa; `git diff --check` no informa espacios erróneos.
- **MEDIDO:** la suite completa se lanzó con
  `python3 -m unittest discover -s pruebas -p 'test_*.py' -v` y no queda verde:
  apareció `test_cancelacion.ContenedorReal.
  test_cancelar_mata_el_contenedor_y_no_solo_el_cliente`. Segundo intento,
  aislado: falla igual en 0,978 s con `AssertionError: True is not false: el
  cliente murió y el CONTENEDOR siguió vivo`. Es ajeno a N28/C22 y no se
  modifica en esta tanda.
- **PENDIENTE:** testigos de ruido y medianas `n>=9`; esta tanda valida
  semántica, no rendimiento.

## Salidas reproducibles

No se versionaron binarios regenerables. Los dos ficheros de salida son:

| fichero | tamaño | SHA-256 | orden |
|---|---:|---|---|
| `bench/salidas-patron-multi/reproducir.py` | 5 343 B | `2431a67b6ccb4780bfdafa8fd1520312dc8d32bed7035171378ed20b4f95374f` | `python3 bench/salidas-patron-multi/reproducir.py` |
| `bench/salidas-patron-multi/resultado.json` | 9 756 B | `6945f7b51b5fb32859349eef1973c0e1e9f59716681e1efe5a31dfac7d8c209f` | salida de la orden anterior; tope explícito de 180 s por celda |

Cada celda registra `rc`, bytes, orden y `stderr`; se acepta como buena sólo
con `rc == 0` y bytes positivos. Las cuatro de N28 y las dos de C22 cumplen
ambas condiciones.

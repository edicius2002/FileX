# CR-007 — Normalización de tokens y clases de objeto

**Base de entrada:** `0ec60d5930444077fefffbac00d19e6dc5ecb55c` más el commit
CR-010, que no modifica ninguna fuente de esta clasificación. **Estado:** DERIVADO de
evidencia histórica conservada y MEDIDO localmente el 2026-09-07. Se ejecutaron cero
conversiones y no se usó red, Docker, GPU ni sidecar.

## Universo y partición

La unidad es el par **`(motor, token)`** de
`bench/salidas-aristas/semi_entrada.json`, no una extensión, un fichero ni una arista de
conversión. El universo tiene **719/719 semiaristas: 473 ffmpeg + 246 ImageMagick**.

| Clase disjunta | Total | ffmpeg | ImageMagick | Base de decisión |
|---|---:|---:|---:|---|
| Ficheros materializables/candidatos de fichero | 659 | 449 | 210 | remanente que representa un objeto consumible; la muestra se declara aparte |
| Crudos que requieren parámetros | 22 | 2 | 20 | `crudos_p2.json`: geometría/profundidad explícitas |
| Protocolos | 2 | 2 | 0 | `rtsp`, `sap`: sesión/URL, no fichero aislado |
| Metadatos | 2 | 0 | 2 | `clip`, `mask`: canal/máscara en la entrada |
| Directorios/paquetes | 3 | 3 | 0 | `dash`, `hls`, `rtp`: manifiesto y recursos/contexto |
| Alias | 6 | 6 | 0 | nombres secundarios explícitos de dos demuxers ffmpeg |
| Retirados/no aplicables | 25 | 11 | 14 | 16 C49 + 9 dispositivos C50 |
| **Total** | **719** | **473** | **246** | conjuntos sin intersección |

La partición aplica esta prioridad reproducible: retirado, crudo, protocolo, metadato,
paquete, alias y fichero. El JSON incluye los siete conjuntos completos y una fila por
unidad; las pruebas comprueban que no falta ni se duplica ninguna.

## Materializable no significa disponible

La clase describe el tipo de objeto, no la existencia de una semilla ni el éxito de una
conversión. De los **659 candidatos de fichero**, el estado histórico separado es **215
`viva`, 34 `muerta` y 410 `no_materializable`**. Por ejemplo, `ffmpeg|302` permanece como
objeto fichero con estado histórico `no_materializable`: la campaña no tuvo muestra, no
demostró que el formato sea imposible.

Los 22 crudos figuran históricamente como `muerta`, pero P2 midió una invocación que exige
parámetros externos. `clip` y `mask`, las tres unidades de paquete y los dos protocolos
siguen mostrando `no_materializable`; la clase explica qué objeto faltaba sin inventar un
fixture.

## Normalización y alias

Cada fila separa `token_motor`, `roles_token`, `normalizado_motor`, `identidad_motor` y
`normalizacion_producto`:

- ffmpeg se normaliza contra sus nombres de demuxer/muxer. Sus dos líneas con alias son
  `matroska,webm` y `mov,mp4,m4a,3gp,3g2,mj2`; por eso los seis nombres secundarios son
  alias y conservan además el rol `extension` cuando corresponde.
- ImageMagick se normaliza contra el módulo/coder publicado por `-list format`. Compartir
  módulo **no basta para declarar alias**: `DNG` agrupa formatos RAW de cámaras distintos
  y `VIDEO` agrupa contenedores distintos.
- Los cuatro alias del producto (`jpeg→jpg`, `tiff→tif`, `htm→html`, `markdown→md`) se
  documentan aparte desde `filex/formatos.py`; no se proyectan automáticamente sobre las
  identidades de motor.

Así, `ffmpeg|webm` tiene token `webm` e identidad `demuxer:matroska`, mientras
`imagemagick|png` tiene token `png` e identidad `coder:png`. Ninguna igualdad textual se
usa como prueba de que token, extensión y demuxer/coder sean la misma cosa.

## Retirados y denominador nuevo

Los **25/719 retirados** son los 16 de C49 (diez generadores, cuatro URL de ImageMagick y
dos dispositivos ffmpeg) más nueve dispositivos Linux confirmados por C50. `sndio` no se
añade: C50 no pudo confirmarlo en ninguna de sus dos builds. Este denominador es de
semiaristas; no debe confundirse con las **133 717** parejas del catálogo amplio que la
auditoría obtiene después de C49/C50.

## Reproducción

Desde la raíz:

```powershell
python -B -X utf8 bench/salidas-cr-normalizacion/generar_clasificacion.py
python -B -X utf8 bench/salidas-cr-normalizacion/generar_clasificacion.py --comprobar
python -B -X utf8 bench/salidas-cr-normalizacion/test_clasificacion.py
```

`clasificacion.json` registra para cada fuente su ruta, tamaño y SHA-256. El generador usa
sólo biblioteca estándar y evidencia conservada; no sondea motores ni modifica sus
fuentes.

## Límites

- Es una taxonomía de objetos de entrada, no una promesa de adaptadores ni de contrato de
  cinco puntos.
- `rtp` se agrupa con paquetes/contexto siguiendo la auditoría; una aplicación concreta
  podría consumirlo como sesión de red. Esa decisión no convierte el token en extensión.
- Los seis alias son sólo los declarados en líneas multi-nombre del catálogo ffmpeg. No se
  deducen alias adicionales por compartir módulo, descripción o sufijo.
- No se cambia ninguna celda de C28 ni se incorporan sus tokens externos (`sup`, `eml`,
  `chk`, `oeb`) al universo de 719; sólo se usa su evidencia conservada para clasificar
  `clip` y `mask`.

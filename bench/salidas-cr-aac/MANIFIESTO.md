# Manifiesto reproducible de CR-002

Todo lo aquí versionado es texto. Los ocho fixtures binarios se generan en
`%TEMP%`, se miden y se eliminan al salir; no se incorporan al repositorio.

## Reproducción

Desde la raíz del repositorio, con Python 3.11 y la build registrada de FFmpeg:

```powershell
python bench/salidas-cr-aac/diagnostico.py
python -m unittest -v bench/salidas-cr-aac/test_diagnostico.py
```

Salida esperada de la segunda orden: `Ran 1 test` y `OK`. La prueba comprueba
que las dos aristas son rojas únicamente con la sonda en proceso, que FFprobe
no emite A1/V1, que hay tres pistas en cada contenedor fuente, que los controles
con/sin `elst` se distinguen y que el truncado es rechazado.

## Ficheros versionados

| fichero | función |
|---|---|
| `diagnostico.py` | genera fixtures CPU, ejecuta FFmpeg/FFprobe y ambos modos del verificador, analiza `mvhd`/`mdhd`/`elst`, normaliza rutas y escribe resultados |
| `test_diagnostico.py` | prueba end-to-end en otro temporal |
| `resultados.json` | órdenes exactas, builds completas, hashes y medidas; reproducible byte a byte en dos ejecuciones consecutivas |

`resultados.json` tiene SHA-256
`258b0cd86a8086f8c72adcd8eb4406c32a07dc09ef3f3c3d0800e17f711c4b80`
en la ejecución documentada. La comprobación de determinismo produjo ese mismo
hash en dos corridas consecutivas.

## Binarios transitorios y hashes esperados

| fixture | bytes | SHA-256 |
|---|---:|---|
| `referencia.wav` | 88 278 | `f9f6f1874f408ac1bd7f159e76e5190ce89713b0d9d8bc3d9b05361f91177676` |
| `fuente.mkv` | 32 145 | `aa0d2e99a5d02fe4b83723d20d7fc53150d7995b21d276e1bec68d0369ad0df3` |
| `fuente.mov` | 33 586 | `18159dcfda6bcdbb2dc3ecc2d61a2a19047b10db9f833981c5b378c5f07a01da` |
| `desde-mkv.m4a` | 16 417 | `c8e727e785093e999bbff6b0528bbb16ca09bbc872d5811a80f7016d23ae5c1a` |
| `desde-mov.m4a` | 16 417 | `c8e727e785093e999bbff6b0528bbb16ca09bbc872d5811a80f7016d23ae5c1a` |
| `con-edit-list.m4a` | 17 652 | `bf46c7797e6744d3fe7decc4fd916b36485b028e6eada6cb1d7ee7b3aee43a48` |
| `sin-edit-list.m4a` | 17 616 | `d3c44d127bcfc389381fe429cd8fe849c117fb1278eb6ae78231a496619e9c4f` |
| `truncada.m4a` | 512 | `d5eca43929798826ecd9f3c5e1a8677c4ee3818e767a11ca39cc31cdac6b6c42` |

Las órdenes completas están en `resultados.json`. Todas llevan `-nostdin`,
timeout externo de 30 s y codificación por CPU; el generador declara además
`-threads 1` y modo bit-exacto para estabilizar Matroska. No se usa GPU,
sidecar, Docker ni aceleración hardware.

## Herramientas selladas

| objeto | identidad |
|---|---|
| FFmpeg | `N-121159-g0bd5a7d371-20250921`; binario SHA-256 `98dc41cfdba89990d114cd8ceb7b360fd54fef12dc357d86343cadffa5541388` |
| FFprobe | misma build; binario SHA-256 `9f3ef519f02ba640fb24095f220fd937e5188efa4386d46954f67e30eb51e02f` |
| `filex/verificador.py` | commit de último cambio `483a7e881191752023ff862b476586ad312ff815`; fichero SHA-256 `9e91ae3bf76374f7bc4625c19d77d285b4c57b00d4b9b591ef4c6bf3cf345853`; huella de contrato `80791e4b492afc94`, intérprete `3.11` |

---

# Informe CR-002: duración AAC y `elst`

**Base diagnosticada:** `0ec60d5930444077fefffbac00d19e6dc5ecb55c`.
**Fecha:** 07/09/2026. **Recursos:** CPU únicamente,
`disable-hardware-acceleration=true`; cero GPU, sidecar o Docker.

## Veredicto por arista

| arista | veredicto en este HEAD | medida decisiva |
|---|---|---|
| `mkv→m4a` / FFmpeg | **FALLO DEL VERIFICADOR AÚN EXISTE** | proceso compara 1,0230 s con `mdhd` 1,0679 s: Δ=44,9 ms > 23,220 ms; FFprobe compara la presentación 1,0230/1,043991 s: Δ=20,991 ms y no falla |
| `mov→m4a` / FFmpeg | **FALLO DEL VERIFICADOR AÚN EXISTE** | proceso compara los `mdhd` redondeados 1,0445/1,0679 s: Δ=23,4 ms > 23,220 ms; FFprobe ve 1,044467/1,043991 s: Δ=0,476 ms y no falla |

**MEDIDO.** Las dos conversiones producen exactamente el mismo M4A: 16 417 B,
SHA-256 `c8e727e785093e999bbff6b0528bbb16ca09bbc872d5811a80f7016d23ae5c1a`.
FFmpeg devuelve `rc=0`; FFprobe abre ambas salidas. La diferencia de veredicto
no procede del codificador ni del fichero producido, sino de la medida.

La auditoría de `474227b` acertaba en la causa pero no acreditaba este HEAD.
Desde entonces el lector MOV ya caracteriza sus pistas, la tolerancia se calcula
por trama y `solo_audio` compara pista con pista. Esos arreglos no alcanzaron
`elst`: las dos aristas siguen rojas, ahora sin la ceguera MOV anterior.

## Controles y capas de tiempo

Las fuentes MKV/MOV contienen 1 vídeo MPEG-4 + 2 audios AAC. Los controles
legítimos con y sin edit list parten de un WAV de exactamente 44 100 muestras.

| caso M4A | presentación FFprobe | stream crudo `mdhd` | priming señalado | `elst` | verificador, pista |
|---|---:|---:|---:|---|---:|
| control con edit list | 1,000000 s | 1,023219955 s | 1 024 muestras | `media_time=1024`, segmento=1 000/1 000 s | 1,0232 s |
| control sin edit list | 1,023220 s | 1,023219955 s | 0 | ausente | 1,0232 s |
| salida desde MKV | 1,043991 s | 1,067913832 s | 1 024 muestras | `media_time=1024`, segmento=1 044/1 000 s | 1,0679 s |
| salida desde MOV | 1,043991 s | 1,067913832 s | 1 024 muestras | `media_time=1024`, segmento=1 044/1 000 s | 1,0679 s |

**MEDIDO.** Una trama AAC a 44,1 kHz dura
`1024/44100 = 0,02321995465 s`. Los controles válidos dan `ok_parcial` con
ambas sondas; la parcialidad es sólo el punto 5, imposible a posteriori. El
truncado de 512 B da `rc=1` en FFprobe y `fallo` en los dos modos del
verificador. El instrumento distingue válido, borde legítimo y corrupción.

## Causa raíz y superficie

**MEDIDO en código y ejecución.** `_isobmff()` recorre `edts` pero no interpreta
`elst`. Publica para cada pista sólo `mdhd.duration / mdhd.timescale`, la línea
de medios antes de ediciones. `punto4_pedido()`, con `solo_audio=true`, sustituye
correctamente la duración de contenedor por la primera pista y aplica la
tolerancia del códec; el dato que recibe es el equivocado.

La superficie demostrada es extracción/reencodificación hacia AAC en ISO-BMFF
cuando la salida recorta priming mediante edit list y los lados no presentan el
mismo sesgo crudo. MKV lo expone; MOV puede cancelarlo o quedar al filo según
edit lists, timescales y redondeos. No es un defecto general de FFmpeg, `rc`,
número de pistas ni `MUESTRAS_TRAMA`.

**PENDIENTE fuera de este diagnóstico:** listas múltiples, ediciones vacías,
tasas distintas de 1 y otros escritores deben quedar no evaluables cuando no se
puedan representar sin inventar semántica.

## Por qué no relajar el umbral

La tolerancia ya modela una trama. El control sin edit list cae correctamente
dentro de ella. Ensancharla hasta ocultar 44,9 ms aceptaría pérdidas reales
adicionales en audio PCM y otros códecs, y escondería que se comparan dos líneas
de tiempo distintas. Hay que corregir la magnitud, no la aceptación global.

## Prueba roja mínima y parche recomendado, no aplicado

Generar el WAV de 44 100 muestras, codificar con `-use_editlist 1` y exigir:

```python
sonda = verificador.sondear_en_proceso(m4a)
audio = next(p for p in sonda["pistas"] if p["tipo"] == "audio")
assert audio["duracion_s"] == pytest.approx(1.0, abs=0.001)
assert audio["duracion_media_s"] == pytest.approx(1.023219955, abs=1e-9)
assert audio["priming_muestras"] == 1024
```

Hoy la primera aserción da 1,0232 y los otros campos no existen. La integración
debe añadir el mismo contenido remuxeado a MKV/MOV y exigir paridad de A1/V1
entre proceso y FFprobe. `test_diagnostico.py` fija la reproducción del defecto;
no se presenta como prueba de la futura corrección.

Parche propuesto:

1. Conservar por pista duración cruda de `mdhd` y duración presentada.
2. Leer `tkhd` y `elst` v0/v1 asociados al `trak`, validando tamaños,
   timescales y `media_rate==1`; corroborar AAC antes de llamar priming a una
   edición positiva.
3. Usar la duración presentada en A1/V1 y caer explícitamente a `mdhd` cuando no
   haya edit list. Una lista no representable queda no evaluable.
4. Probar `elst` v0/v1, ausencia, edición vacía, truncado, tres pistas y las dos
   integraciones FFmpeg.

Riesgos: asociar la lista a la pista equivocada por el estado recursivo actual;
mezclar timescale de película/medios; sumar una edición vacía como audio audible;
romper AVIF/HEIF, que comparten `_isobmff`; o crear un falso verde con una lista
compleja. El parche debe fallar cerrado.

## Sellos y huellas que caducarían

**MEDIDO.** El HEAD calcula contrato `80791e4b492afc94`, pero los cinco sondeos
guardan `fe41b4d52413299c` por el cambio previo. El parche volvería a mover sólo
el componente global `contrato` alcanzable desde `verificar()`:

| sello | aristas |
|---|---:|
| `filex/sondeo/ffmpeg.json` | 70 |
| `filex/sondeo/imagemagick.json` | 62 |
| `filex/sondeo/doc_libreoffice.json` | 16 |
| `filex/sondeo/doc_pandoc.json` | 16 |
| `filex/sondeo/doc_calibre.json` | 8 |
| **total** | **172** |

Aunque ya estén degradadas, no se deben resellar: tras el parche requieren
resondeo real. `motor` e `invocacion` deben permanecer iguales.

## Negativas documentales históricas

No se lanzó Docker. Se revisaron `salidas-hito5/sonda.json` y
`hito5-documental.md`:

| control | evidencia conservada | veredicto |
|---|---|---|
| `docx→txt` LibreOffice L11 | 240 227,8 ms, agotado, `rc=1`, 0 B; lock 70 B + temporal 471 859 200 B | **NOMINAL_REFUTADA** |
| `epub→pdf` LibreOffice L10 | 7 894,0 ms, `rc=1`, fuente no cargable, 0 B | **NOMINAL_REFUTADA**; Calibre no valida esta arista |
| `epub→html` Calibre C06 | 2 073,1 ms, `rc=1`, sin plugin HTML, 0 B | **NOMINAL_REFUTADA**; HTMLZ no es HTML |

Ningún `rc=0` de una ruta alternativa vuelve verdes esos pares de motor.

## Verificación de esta entrega

**MEDIDO antes del commit:** generación doble con el mismo SHA-256; arnés
end-to-end `1/1 OK`; `git diff --check`, limpio. `ci/integridad.py` necesitó
`PYTHONUTF8=1` por la consola CP1252: ocho reglas quedaron `OK` y
`informes-registrados` quedó `MAL` por ocho informes basales sin citar
(`cobertura-{contrato,fidelidad,png,superficies,tiffgif,webp}.md`,
`fix-superficies.md`, `fix-verificador.md`). Consolidar este informe en el
manifiesto evita añadir un noveno; el alcance prohíbe tocar el inventario.

# MANIFIESTO — `bench/salidas-phys-multi/`

Salidas binarias de G4 / B19. **Borradas del repositorio**: son regenerables con dos órdenes.

- ficheros: **52**
- bytes: **61,243,097** (61.2 MB)

## Cómo se reproducen

**Paso 1 — rasterizar y generar las variantes de cabecera** (una sola orden; rasteriza UNA vez por documento y factor y genera las variantes por cirugía de bytes sobre el `pHYs`, sin tocar los IDAT):

```
cd bench/salidas-phys-multi
../../.venv-ai/Scripts/python.exe preparar_pm.py \
    escaneado_d3:1.0 escaneado_d4:1.0 escaneado_d4c:1.0 \
    escaneado_d4e:1.0 escaneado_d4f:1.0
../../.venv-ai/Scripts/python.exe preparar_pm.py escaneado_d4:1.25
```

La orden de rasterizado que ejecuta por dentro es la del corpus:

```
magick -density <ppp> corpus/pdf/<doc>.pdf[0] -colorspace Gray -alpha remove -background white -flatten <doc>__k<kkkk>__sin.png
```

**Paso 1-bis — los dos rásteres EN COLOR de la tanda E** (`img_color/`), que existen para separar el orden de canales del modo paleta:

```
magick img/escaneado_d4__k1000__sin.png -colorspace sRGB \
    -channel R -evaluate multiply 0.55 +channel \
    -channel B -evaluate multiply 0.85 +channel \
    img_color/escaneado_d4__k1000__color.png
    # ^ magick lo escribe en PALETA (mode P), a proposito del hallazgo
magick img/escaneado_d4__k1000__sin.png -colorspace sRGB \
    -channel R -evaluate multiply 0.55 +channel \
    -channel B -evaluate multiply 0.85 +channel \
    PNG24:img_color/escaneado_d4__k1000__color24.png
    # ^ el mismo, forzado a truecolor
```

**Paso 2 — las tandas**:

```
bash run_a_tess.sh      # control Tesseract, CPU, sin lock de GPU
bash run_b_gpu.sh       # los tres motores GPU, con lock
bash run_c_color.sh     # tanda E: la via sobre raster en color
# y las tres sondas:
#   sonda_pixeles_pm.py, sonda_lectura_pm.py, sonda_canales_pm.py
```

> **El `sha256` de un PNG de `magick` NO es reproducible entre tandas**: escribe trozos `tEXt` con `date:create`, `date:modify` y `date:timestamp`. Lo que sí es reproducible es el **`md5` de los IDAT**, que es lo que garantiza que las variantes de cabecera comparten píxeles. Se dan los dos.

## Ficheros

| fichero | bytes | px | ppp render | ppp declarados | `pHYs` | `md5` IDAT | `sha256` |
|---|---:|---|---:|---|---|---|---|
| `escaneado_d3__k1000__ninguno.png` | 364,098 | 647×850 | 100 | None | - | `22fe5d6e02b6` | `aea6c285f89dc35a` |
| `escaneado_d3__k1000__p0070.png` | 364,119 | 647×850 | 100 | 70 | u=1 x=2756 | `22fe5d6e02b6` | `84a242bdb0d95170` |
| `escaneado_d3__k1000__p0100.png` | 364,119 | 647×850 | 100 | 100 | u=1 x=3937 | `22fe5d6e02b6` | `282f9db4dcabf737` |
| `escaneado_d3__k1000__p0150.png` | 364,119 | 647×850 | 100 | 150 | u=1 x=5906 | `22fe5d6e02b6` | `d951843b7571bccb` |
| `escaneado_d3__k1000__p0200.png` | 364,119 | 647×850 | 100 | 200 | u=1 x=7874 | `22fe5d6e02b6` | `3469a0284978de73` |
| `escaneado_d3__k1000__p0300.png` | 364,119 | 647×850 | 100 | 300 | u=1 x=11811 | `22fe5d6e02b6` | `b36cad81b444e216` |
| `escaneado_d3__k1000__p0400.png` | 364,119 | 647×850 | 100 | 400 | u=1 x=15748 | `22fe5d6e02b6` | `32094ff31ec855a2` |
| `escaneado_d3__k1000__sin.png` | 364,119 | 647×850 | 100 | 0 | u=0 x=100 | `22fe5d6e02b6` | `eada72378cf3c331` |
| `escaneado_d4__k1000__ninguno.png` | 1,172,509 | 1294×1716 | 200 | None | - | `b184e62dfd02` | `2f3f36891336ca30` |
| `escaneado_d4__k1000__p0070.png` | 1,172,530 | 1294×1716 | 200 | 70 | u=1 x=2756 | `b184e62dfd02` | `8b2ee4aaa3676dcc` |
| `escaneado_d4__k1000__p0100.png` | 1,172,530 | 1294×1716 | 200 | 100 | u=1 x=3937 | `b184e62dfd02` | `49d9a8f3361f6484` |
| `escaneado_d4__k1000__p0150.png` | 1,172,530 | 1294×1716 | 200 | 150 | u=1 x=5906 | `b184e62dfd02` | `dfb80b1bfc46cf5c` |
| `escaneado_d4__k1000__p0200.png` | 1,172,530 | 1294×1716 | 200 | 200 | u=1 x=7874 | `b184e62dfd02` | `850d08549f855d33` |
| `escaneado_d4__k1000__p0300.png` | 1,172,530 | 1294×1716 | 200 | 300 | u=1 x=11811 | `b184e62dfd02` | `c5bfb0bc32f07cf2` |
| `escaneado_d4__k1000__p0400.png` | 1,172,530 | 1294×1716 | 200 | 400 | u=1 x=15748 | `b184e62dfd02` | `90cfe79241e9eeb8` |
| `escaneado_d4__k1000__sin.png` | 1,172,530 | 1294×1716 | 200 | 0 | u=0 x=200 | `b184e62dfd02` | `77409188e08846b4` |
| `escaneado_d4__k1250__ninguno.png` | 1,338,326 | 1617×2145 | 250 | None | - | `9b4963100711` | `5143bdaf916edb9e` |
| `escaneado_d4__k1250__p0070.png` | 1,338,347 | 1617×2145 | 250 | 70 | u=1 x=2756 | `9b4963100711` | `d0269913316bb628` |
| `escaneado_d4__k1250__p0100.png` | 1,338,347 | 1617×2145 | 250 | 100 | u=1 x=3937 | `9b4963100711` | `18971ee2cd7d2bea` |
| `escaneado_d4__k1250__p0150.png` | 1,338,347 | 1617×2145 | 250 | 150 | u=1 x=5906 | `9b4963100711` | `84e6c1621a53153e` |
| `escaneado_d4__k1250__p0200.png` | 1,338,347 | 1617×2145 | 250 | 200 | u=1 x=7874 | `9b4963100711` | `5f79f7d38d21e78f` |
| `escaneado_d4__k1250__p0250.png` | 1,338,347 | 1617×2145 | 250 | 250 | u=1 x=9843 | `9b4963100711` | `0bd26cc0f2e62d1e` |
| `escaneado_d4__k1250__p0300.png` | 1,338,347 | 1617×2145 | 250 | 300 | u=1 x=11811 | `9b4963100711` | `b3ef7c3aba66567c` |
| `escaneado_d4__k1250__p0400.png` | 1,338,347 | 1617×2145 | 250 | 400 | u=1 x=15748 | `9b4963100711` | `ab55246468c78ce8` |
| `escaneado_d4__k1250__sin.png` | 1,338,347 | 1617×2145 | 250 | 0 | u=0 x=250 | `9b4963100711` | `e4be7c22eeccb9c1` |
| `escaneado_d4c__k1000__ninguno.png` | 1,141,577 | 1294×1734 | 200 | None | - | `02394c0359f3` | `390a9e2e0e4536c0` |
| `escaneado_d4c__k1000__p0070.png` | 1,141,598 | 1294×1734 | 200 | 70 | u=1 x=2756 | `02394c0359f3` | `c4dec5ccbcad8481` |
| `escaneado_d4c__k1000__p0100.png` | 1,141,598 | 1294×1734 | 200 | 100 | u=1 x=3937 | `02394c0359f3` | `0fe85eadaa179b01` |
| `escaneado_d4c__k1000__p0150.png` | 1,141,598 | 1294×1734 | 200 | 150 | u=1 x=5906 | `02394c0359f3` | `d6a3dd0cccafd1cd` |
| `escaneado_d4c__k1000__p0200.png` | 1,141,598 | 1294×1734 | 200 | 200 | u=1 x=7874 | `02394c0359f3` | `3dc6168d4752561e` |
| `escaneado_d4c__k1000__p0300.png` | 1,141,598 | 1294×1734 | 200 | 300 | u=1 x=11811 | `02394c0359f3` | `19cbbc3f3938a496` |
| `escaneado_d4c__k1000__p0400.png` | 1,141,598 | 1294×1734 | 200 | 400 | u=1 x=15748 | `02394c0359f3` | `4413d5e1ec9b57ce` |
| `escaneado_d4c__k1000__sin.png` | 1,141,598 | 1294×1734 | 200 | 0 | u=0 x=200 | `02394c0359f3` | `4a4c973ccb07e4cc` |
| `escaneado_d4e__k1000__ninguno.png` | 1,153,548 | 1294×1716 | 200 | None | - | `0ad02e8a8793` | `7ed3687830a1f5df` |
| `escaneado_d4e__k1000__p0070.png` | 1,153,569 | 1294×1716 | 200 | 70 | u=1 x=2756 | `0ad02e8a8793` | `6137abe57aded726` |
| `escaneado_d4e__k1000__p0100.png` | 1,153,569 | 1294×1716 | 200 | 100 | u=1 x=3937 | `0ad02e8a8793` | `a7da83dca920d4fb` |
| `escaneado_d4e__k1000__p0150.png` | 1,153,569 | 1294×1716 | 200 | 150 | u=1 x=5906 | `0ad02e8a8793` | `5c531cbe590cb0a0` |
| `escaneado_d4e__k1000__p0200.png` | 1,153,569 | 1294×1716 | 200 | 200 | u=1 x=7874 | `0ad02e8a8793` | `2b85a2383626d832` |
| `escaneado_d4e__k1000__p0300.png` | 1,153,569 | 1294×1716 | 200 | 300 | u=1 x=11811 | `0ad02e8a8793` | `cc3b2688e447c563` |
| `escaneado_d4e__k1000__p0400.png` | 1,153,569 | 1294×1716 | 200 | 400 | u=1 x=15748 | `0ad02e8a8793` | `df3a515807b5f7e4` |
| `escaneado_d4e__k1000__sin.png` | 1,153,569 | 1294×1716 | 200 | 0 | u=0 x=200 | `0ad02e8a8793` | `46fdcdf1948f42dc` |
| `escaneado_d4f__k1000__ninguno.png` | 1,635,760 | 1552×2080 | 240 | None | - | `c8f3380438f2` | `f0dd9874fb2f6dc3` |
| `escaneado_d4f__k1000__p0070.png` | 1,635,781 | 1552×2080 | 240 | 70 | u=1 x=2756 | `c8f3380438f2` | `f96a46c3ee419bec` |
| `escaneado_d4f__k1000__p0100.png` | 1,635,781 | 1552×2080 | 240 | 100 | u=1 x=3937 | `c8f3380438f2` | `177874bc68a657ad` |
| `escaneado_d4f__k1000__p0150.png` | 1,635,781 | 1552×2080 | 240 | 150 | u=1 x=5906 | `c8f3380438f2` | `4b518e55a7613b66` |
| `escaneado_d4f__k1000__p0200.png` | 1,635,781 | 1552×2080 | 240 | 200 | u=1 x=7874 | `c8f3380438f2` | `e34df9af05c6ebe8` |
| `escaneado_d4f__k1000__p0240.png` | 1,635,781 | 1552×2080 | 240 | 240 | u=1 x=9449 | `c8f3380438f2` | `cb2059dcc4d8a41e` |
| `escaneado_d4f__k1000__p0300.png` | 1,635,781 | 1552×2080 | 240 | 300 | u=1 x=11811 | `c8f3380438f2` | `99237aaec3544727` |
| `escaneado_d4f__k1000__p0400.png` | 1,635,781 | 1552×2080 | 240 | 400 | u=1 x=15748 | `c8f3380438f2` | `9207bdb5f29502ed` |
| `escaneado_d4f__k1000__sin.png` | 1,635,781 | 1552×2080 | 240 | 0 | u=0 x=240 | `c8f3380438f2` | `bac63a49ecc37a79` |
| `img_color/escaneado_d4__k1000__color.png` | 1,317,383 | 1294×1716 | 200 | None | - | `` | `cb3c9953a40ea30a` |
| `img_color/escaneado_d4__k1000__color24.png` | 2,504,160 | 1294×1716 | 200 | None | - | `` | `41fd000d6326f5b1` |

## Lo que SÍ queda versionado

Los scripts, los `.json` de celda (`json/`), la salida literal de OCR de cada celda (`texto/`) y los logs (`logs/`). Son texto y son la trazabilidad del informe.

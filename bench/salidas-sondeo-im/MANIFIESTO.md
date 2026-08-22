# MANIFIESTO — `bench/salidas-sondeo-im/`

Sondeo de las **62 aristas `sin_sondear` de ImageMagick** (agente S1, 22/08/2026).
Build: **`imagemagick 7.1.2-21`** (Q16-HDRI). Informe: `bench/sondeo-imagemagick.md`.
Dato entregado: `filex/sondeo/imagemagick.json`.

**Ninguna salida binaria se versiona.** Las 124 salidas del barrido (109 MB) y las
semillas derivadas se generaron en un directorio desechable y **se borraron al
terminar**. Aquí queda lo que es texto: los scripts, los dos SVG de origen y los
dos `.json` de resultados.

---

## 1. Lo que sí está en este directorio

| Fichero | Bytes | sha256 | Qué es |
|---|---|---|---|
| `sonda_im.py` | 8 508 | — | El arnés. Llama a `FileX.convertir()`, no a `magick` |
| `hacer_json.py` | 3 879 | — | Convierte `barrido.json` en `filex/sondeo/imagemagick.json` |
| `svg_A.svg` | 579 | — | Semilla A de SVG, 480×240, con texto |
| `svg_B.svg` | 386 | — | Semilla B de SVG, 200×200, con `fill-opacity` y texto |
| `barrido.json` | 107 452 | — | Las 124 celdas crudas: rc, ms, veredicto, hallazgos, censo, `identify` |
| `ico256.json` | 338 | — | Remedida de las 7 aristas `*→ico` con semilla de 256 px |

Los `sha256` de los ficheros de texto no se listan porque están versionados: el
propio git los tiene.

---

## 2. Cómo se reproducen las SEMILLAS (borradas)

Todas salen de `corpus/imagen/tipico.png` (1920×1080, alfa **trivial**: `min(α)=1`)
y `corpus/imagen/alpha.png` (200×200, alfa **real**: `min(α)=0`).
`$S` es el directorio desechable de semillas.

### Semilla A — 1920×1080, alfa trivial

```
cp corpus/imagen/tipico.png $S/A.png
cp corpus/imagen/tipico.jpg $S/A.jpg
cp corpus/imagen/tipico.webp $S/A.webp
magick corpus/imagen/tipico.png -define tiff:predictor=2 -compress zip $S/A.tif
magick corpus/imagen/tipico.png -quality 50 $S/A.avif
magick corpus/imagen/tipico.png $S/A.bmp
magick corpus/imagen/tipico.png $S/A.gif
magick corpus/imagen/tipico.png -resize 256x256 $S/C.ico
```

| Fichero | Bytes | sha256 |
|---|---:|---|
| `A.png` | 42 855 | `e645f85a6eec4e4d50f29f6b5336cf4916f2ed196e43913f04ca80e9bc1d0953` |
| `A.jpg` | 87 954 | `920a3d6f7e0a10e580e699225611f33dc203bf3d2bb993455b5e0fc7cb711cc0` |
| `A.webp` | 12 796 | `d2b9dbd6f068e14cec6772509bf9c1372020a97104d5d091fdacabe4c22f92cd` |
| `A.tif` | 46 986 | `b4798f6f194b62d6b1957c49a2df5b499527a3102438b73ebb9d35f59fc659f2` |
| `A.avif` | 1 595 | `04eb85707ee966c6ee016d4ed3ee54ccfd198f9c6b847f10c1721d223b0f5980` |
| `A.bmp` | 8 294 538 | `215decbf0f6a730f8167189cdb76f975a3f01c88adf399f3e5ec2162f2e1b1ea` |
| `A.gif` | 99 945 | `83a186b1acbf098a4cda72387b26b6bdcacf2201f120f1584c141b24f223e492` |
| `C.ico` | 152 126 | `d6ce922ef1c1ee566c9cca5de8caa0e920948bda78023dc2574d692791284de1` |

**`A.ico` no existe y no puede existir**: `magick corpus/imagen/tipico.png A.ico`
devuelve `rc=1` (`width or height exceeds limit`) y deja un fichero de **0 bytes**.
Por eso el origen `ico` de la semilla A es `C.ico`, a 256×144.

### Semilla B — 200×200, alfa real

```
magick corpus/imagen/alpha.png $S/B.png
magick corpus/imagen/alpha.png -background white -flatten -quality 85 $S/B.jpg
magick corpus/imagen/alpha.png -define webp:lossless=true $S/B.webp
magick corpus/imagen/alpha.png -compress zip $S/B.tif
magick corpus/imagen/alpha.png -quality 50 $S/B.avif
magick corpus/imagen/alpha.png $S/B.bmp
magick corpus/imagen/alpha.png $S/B.gif
magick corpus/imagen/alpha.png $S/B.ico
```

| Fichero | Bytes | sha256 |
|---|---:|---|
| `B.png` | 2 780 | `57cc7db8dae2cf63efd76ff0e3666943ebeab7ccc3ee2ecbb71f1a1a8383de74` |
| `B.jpg` | 4 389 | `31873cfcf4a8391a07f32d1b4d55d2cb6b19e8fc56f6996c274d0e72cedce2ad` |
| `B.webp` | 1 292 | `38d49c330da6a0ddc18595233a2424d3efd2a5ee8c54e8137cf37452897f760b` |
| `B.tif` | 3 746 | `68888a65618036fae43cf3a7b246cfaacfe03d7d9bd22699ce94a73916988b65` |
| `B.avif` | 1 670 | `d4f22409580573a2eec42474d7862a6fb405edde7b42948198fc6c94f832d9fa` |
| `B.bmp` | 160 138 | `5f21b6d5c25f8751481bd26a15bb97ecf9a87cbd5a79489cc5ca01558b027213` |
| `B.gif` | 2 598 | `0affa28523910c70774f64f1e399f0348dcc3b98a9413ec6b47a02fff30e79e5` |
| `B.ico` | 46 686 | `238e32c22f35b27475b3e8f0f92f6ddee4ce49038843b7dfefd2a988ae048ba7` |

### Semilla D — 256×144, para remedir las siete `*→ico`

```
magick corpus/imagen/tipico.png -resize 256x256 $S/D.png
magick $S/D.png -quality 85 $S/D.jpg
magick $S/D.png $S/D.webp
magick $S/D.png -quality 50 $S/D.avif
magick $S/D.png $S/D.gif
magick $S/D.png $S/D.bmp
magick $S/D.png -compress zip $S/D.tif
```

| Fichero | Bytes | sha256 |
|---|---:|---|
| `D.png` | 4 393 | `91b8d2dee04c09184e9af1a2169dfd14f42b03097c1cd61eaa944bcf08b8faad` |
| `D.jpg` | 1 873 | `ffefdf102201ddfed41328c1fd119dd36041d6189d482bd8cf1de5101e915ee7` |
| `D.webp` | 622 | `537e0f8af329cb205002bb831ca456007af64869fd5167c5eb97ba729eab6e57` |
| `D.avif` | 664 | `38e79c523bcbca9c2bc8e200376bcbeab8d9c7557207609b3545c2191bf8c88f` |
| `D.gif` | 4 276 | `aa8eeafdf9b2b82be7eea71cb3d1fd89b73b4ff25a13f2c8acdb47dfe32141bb` |
| `D.bmp` | 147 594 | `2da7c76b7b0e2e75e8b2639b8ae0ed3303db6dc55a9ca9c74229791be6885822` |
| `D.tif` | 5 204 | `0a1e47e426256dca55b2d5a5839012682ccd160143ff226ea10414387592f5a4` |

---

## 3. La orden exacta que reproduce el barrido entero

Desde la raíz del repositorio, con `$S` (semillas) y `$O` (salidas) en un
directorio **desechable fuera del repositorio**:

```
python bench/salidas-sondeo-im/sonda_im.py  $S  $O  $S/barrido.json
python bench/salidas-sondeo-im/hacer_json.py $S/barrido.json $S/ico256.json \
       filex/sondeo/imagemagick.json
```

`sonda_im.py` **no llama a `magick`**: usa `filex.nucleo.FileX.convertir()` con el
grafo sustituido por uno de **una sola arista**, para que el planificador no
escoja otro camino. Cada conversión trae de serie el contrato de cinco puntos, el
directorio desechable de `filex/trabajo.py` y el censo del punto 5.

`ico256.json` sale del bloque de remedida documentado en
`bench/sondeo-imagemagick.md` §3.2 (las siete `*→ico` con semilla D, n=3).

**Duración medida: 98 s** las 124 celdas (n=3 en la semilla A, n=1 en la B), más
~9 s de la remedida.

---

## 4. Evidencia del hallazgo del ICONDIRENTRY (§2 del informe)

Reproducible sin conservar binarios:

```
magick corpus/imagen/tipico.png -resize 257x257 t257.png && magick t257.png t257.ico
magick corpus/imagen/tipico.png -resize 320x320 t320.png && magick t320.png t320.ico
xxd -l 22 t320.ico
```

Bytes 6 y 7 del fichero (ancho y alto del `ICONDIRENTRY`):

```
t255.ico  0000 0100 0100 ff8f ...   -> 255 x 143   correcto
t256.ico  0000 0100 0100 0090 ...   -> 0(=256) x 144   correcto
t257.ico  0000 0100 0100 0191 ...   -> 1 x 145     MAL (real: 257x145)
t320.ico  0000 0100 0100 40b4 ...   -> 64 x 180    MAL (real: 320x180)
```

Lector independiente (Pillow 10.4.0, desde `.venv-ai`, solo lectura):

```
.venv-ai/Scripts/python.exe -c "from PIL import Image; im=Image.open('t320.ico'); print(im.size, sorted(im.ico.sizes()))"
```

---

## 5. Ficheros de trabajo BORRADOS

| Directorio | Contenido | Bytes |
|---|---|---|
| `$O` (salidas del barrido) | 117 salidas de las 124 celdas | 109 MB |
| `$O/out256` | 7 salidas de la remedida `*→ico` | 960 KB |
| `$O/ico` | 24 ficheros del barrido de umbral del ICO | 1,3 MB |
| `$S` (semillas A, B, C, D) | 23 ficheros | 8,9 MB |

Se reproducen con las órdenes de §2 y §3.

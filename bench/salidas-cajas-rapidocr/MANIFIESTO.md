# MANIFIESTO — bench/salidas-cajas-rapidocr/img/

Los **25 rásteres PNG** de este directorio (3,5 MB) **no se versionan**: son
regenerables. Son `escaneado_d5c` (nativo 80 ppp, 12 puntos) y `escaneado_d5a`
(nativo 90 ppp, 13 puntos), el mismo barrido fino 100–150 que usan
`bench/salidas-suelo-ppp/` y `bench/salidas-psm-suelo/`.

**Orden que los reproduce:** desde Git Bash de Windows, con `USERPROFILE`/`HOME`
locales (nunca heredados de WSL):

```
"/d/Work/research/FileX/.venv-ai/Scripts/python.exe" \
  bench/salidas-cajas-rapidocr/cajas_rapidocr.py escaneado_d5c --native 80 --reps 3
"/d/Work/research/FileX/.venv-ai/Scripts/python.exe" \
  bench/salidas-cajas-rapidocr/cajas_rapidocr.py escaneado_d5a --native 90 --reps 3
```

Rasterizador: `magick -density N …[0] -units PixelsPerInch -density N -colorspace
sRGB -alpha remove -background white -flatten` (el pHYs declarado es el verdadero).

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `ppp080__escaneado_d5a.png` | 106099 | `650ebdfdc9a83663d905c3a32593c4c6e321110fd70320006f89769ad3e1102a` |
| `ppp080__escaneado_d5c.png` | 116022 | `ada8d40c6ab8a6cafd330684d8ab3030dd8b6c2d5673c2ca4be0a6546ffe17df` |
| `ppp090__escaneado_d5a.png` | 124796 | `6f1ffafb4e187894f93fe4933515d671fba9bae68857fd098725360748e9869d` |
| `ppp100__escaneado_d5a.png` | 135472 | `8a56bbd5946edbcff3b1f3e3a62d9c6c58e5c2367d10a8fd9b0fa38ecd5637f4` |
| `ppp100__escaneado_d5c.png` | 128239 | `41259f62b681a53de419553f24234e3e9a74159eca5ed7c672fa2a37f9260b94` |
| `ppp105__escaneado_d5a.png` | 138658 | `7a5db959d0e0942967f2e57045926b68a97f1a75d5b7cdc72769b1ba7dcb2265` |
| `ppp105__escaneado_d5c.png` | 133465 | `4e8f828b8ccf405c844ea827482aa556d7117f88b06ce91d94ebc4287cedb5a5` |
| `ppp110__escaneado_d5a.png` | 142603 | `da23981eb8f65cd0998170d4a8bc7f1fd5e0a285eede23c7b84eeeacbd933862` |
| `ppp110__escaneado_d5c.png` | 134045 | `d8695cc17ff1d59d56ec48af560074488be873b2461d89c9abccad6670a1c0a4` |
| `ppp115__escaneado_d5a.png` | 144903 | `b126946bdf5fde08de77a35cf5b7a568ee0c2c25d029f28f33ef4000fcde877a` |
| `ppp115__escaneado_d5c.png` | 138782 | `7c3b816f42e18f2dbb95fbc359513d7ae467d0acdf895a2aae78034b6d9f1103` |
| `ppp120__escaneado_d5a.png` | 146489 | `877968bc1ba7dde1f98178bb76be226ae35e393c0cec0828fb9407048a5067ef` |
| `ppp120__escaneado_d5c.png` | 138152 | `f42165286800110d62e47aa00af9d1c8c021ed31f663dbbf12671d816e713296` |
| `ppp125__escaneado_d5a.png` | 148747 | `889c3539165e23c0a9e3857cf0a12618e357c1141f1a68fbde238388e6c7776a` |
| `ppp125__escaneado_d5c.png` | 143601 | `f32cb10e95684150d1d13308af653e3fb739228ef68043366d4bc535d12eed52` |
| `ppp130__escaneado_d5a.png` | 150242 | `9d9b13071dc1e9c8f527ee6e2db6883ad39f0cf51271a6a4b0a33f6e3c092c1c` |
| `ppp130__escaneado_d5c.png` | 143313 | `e9bd581c3661b1e2bd31e0a3202bf4fa52a2e1a79477a4b59f356c14b1b12b2a` |
| `ppp135__escaneado_d5a.png` | 148928 | `c655ebbb6a6e68bc326f9975f47f01205b1737daf846286ee296ac57a5acbe8d` |
| `ppp135__escaneado_d5c.png` | 148071 | `17be607fc9416e45893d962a3c93d7e95b337d6c3832f83680917780de6a5fe7` |
| `ppp140__escaneado_d5a.png` | 156235 | `d8ad9d60e4d42996a39fa66a4965ed1ade9b4644b072b0e5a8fa5d2804deb91e` |
| `ppp140__escaneado_d5c.png` | 146913 | `ffac75aa03dc3d5a5bdfa0d02bb6de0cff488568828ee9625fa9e11b0d3a4585` |
| `ppp145__escaneado_d5a.png` | 158529 | `09ce72b04c423dd4d7d6fa9857cdfc636f2e279d0a7dc6541d253f3187a784a4` |
| `ppp145__escaneado_d5c.png` | 151610 | `de53cdb1b08321e44812e121feeecce79b6efbbd18b53d4970ad260698f266d7` |
| `ppp150__escaneado_d5a.png` | 160006 | `33e4b9f8f8ae11c0b19232b559cd0af2d2c58cb980d87437f154c290fa38fc5e` |
| `ppp150__escaneado_d5c.png` | 149674 | `457143338ff1930fdf838d75c43263e5c454c07b633800b328e347fadee38b74` |

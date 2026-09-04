# MANIFIESTO — `bench/salidas-k-borde-rejilla/` (worker12, 3 de septiembre de 2026)

Informe: **`bench/k-borde-rejilla.md`**. Cierra el residuo de `B23`: la rejilla de `k`
por encima de ×1,60 para las tres configuraciones cuyo óptimo publicado tocaba ese borde.

**GPU usada, lock tomado y soltado por configuración.** EasyOCR y Docling+R6 son GPU;
Tesseract es CPU y no toma el lock.

---

## 1. Lo que se ha borrado y por qué

**128 rásteres PNG, 17 638 864 bytes (17.6 MB), borrados al terminar** según `CLAUDE.md` §6:
son salidas binarias regenerables y no se versionan. Son los 16 factores × 4 documentos
en las **dos** recetas de ráster (gris sin `pHYs` para EasyOCR, prefijo `kf`; sRGB con
`-units PixelsPerInch` para Tesseract, prefijo `kd`). Docling no usa ninguno: rasteriza
él mismo por `RapidOcrOptions.scale`.

**Lo que SÍ se conserva es texto:** los cinco scripts, los `.json` de las 192 celdas,
las 192 lecturas literales de OCR y todos los logs.

## 2. La orden exacta que lo reproduce todo

```bash
# 1. las 192 celdas (regenera de paso los 128 PNG en img/)
bash bench/salidas-k-borde-rejilla/conductor_b26.sh

# 2. el k por minimo arrepentimiento y el coste del borde
D:/Work/research/FileX/.venv-mcp-filex/Scripts/python.exe \n    bench/salidas-k-borde-rejilla/analisis_b26.py

# 3. la recta de VRAM de cada motor (un proceso FRESCO por punto)
for f in 1.60 2.50 4.00 6.00; do for c in docling-r6 easyocr; do \n  D:/Work/research/FileX/.venv-ai/Scripts/python.exe \n    bench/salidas-k-borde-rejilla/sonda_vram_b26.py $c escaneado_d5a $f; done; done

# 4. el recorte, sondeado en ejecucion
for f in 1.60 4.00; do for c in easyocr docling-r6; do \n  D:/Work/research/FileX/.venv-ai/Scripts/python.exe \n    bench/salidas-k-borde-rejilla/sonda_recorte_b26.py $c escaneado_d5a $f; done; done
```

Un PNG suelto se reproduce con la receta que usa `b26_borde.py:raster()`, donde
`N = round(ppp_nativos × factor)`:

```bash
# prefijo kf (gris, pHYs NO declarado) -- el que consume EasyOCR
magick -density N corpus/pdf/<doc>.pdf[0] -colorspace Gray \n       -alpha remove -background white -flatten kf<factor*1000>__<doc>.png

# prefijo kd (sRGB, pHYs DECLARADO) -- el que consume Tesseract
magick -density N corpus/pdf/<doc>.pdf[0] -units PixelsPerInch -density N \n       -colorspace sRGB -alpha remove -background white -flatten kd<factor*1000>__<doc>.png
```

ppp nativos: `escaneado_d5a` 90 · `escaneado_d5c` 80 · `escaneado_d5` 72 · `escaneado_d5b` 60.

## 3. Los ficheros que se conservan

| fichero | `sha256` | bytes |
|---|---|---:|
| `b26_borde.py` | `e7645d9ca7aa45be40348d159e64baa47ddf7d8043e00b28fef40208cb2e368a` | 19 907 |
| `conductor_b26.sh` | `fda57c1a24f67576c09d4841a6a9873aa88d6f89bcac052e1039c99bbe203b1b` | 2 944 |
| `analisis_b26.py` | `97d7eecf8ce9283a642d95db1199b6993b3de369fcd476f6e9032d4b0ca16e63` | 6 658 |
| `sonda_vram_b26.py` | `ad7ff09346831c50ac5c258780978782ba2476c87c79d2db21ecaa7754e2b183` | 3 525 |
| `sonda_recorte_b26.py` | `a85887a7ddfc4585fb4c4e50b6fc83c286b9a70882f227c0e5c86d4c86d49d37` | 4 492 |

Los `sha256` de los 128 PNG borrados están, uno a uno, en
`json/b26_img_sha256.json` (versionado, 24 KB de texto).

## 4. Los 128 rásteres borrados

| fichero | `sha256` | bytes |
|---|---|---:|
| `kd0750__escaneado_d5.png` | `59433df5836cdbf5bd205d95d54745183e20550150ceaaf3f8ccb5ff48dc0fe6` | 62 653 |
| `kd0750__escaneado_d5a.png` | `7dc3e023a86aa95439882698ff9426584831e0549c550664f902f476a5b60d84` | 81 520 |
| `kd0750__escaneado_d5b.png` | `0cc80ae49fc6d08498bd8fe6ef58ad312601d14cad50b9dfcaeb6c3251535901` | 43 977 |
| `kd0750__escaneado_d5c.png` | `ea0373d464289206c1de9d3292ab6d2499e7dd9f88937944c9ea845b06526b67` | 74 438 |
| `kd0875__escaneado_d5.png` | `ac12c53fa090f48ccc891056ef30c54e1078fa082f59d82a682f2e8dd490f971` | 78 461 |
| `kd0875__escaneado_d5a.png` | `464d0cf943dd7fab8213b5549eeec338a415982aa143996fe941a2df9b2e9a2c` | 103 444 |
| `kd0875__escaneado_d5b.png` | `290e88b2a1321c3cce74e2a3f2b703a786d8f8c30ad16a276649ecfb173f084e` | 56 844 |
| `kd0875__escaneado_d5c.png` | `046f53790ebf815460dd20a70d1b7f02feda4b16f4ff065654f1473d307c4fb6` | 91 823 |
| `kd1000__escaneado_d5.png` | `8c58dc1221acdd562c2d74d2466cdd73a1666e0fb50f51775b2722b47ce3ef3b` | 97 718 |
| `kd1000__escaneado_d5a.png` | `df4ad08d4832bed7976a5d4207a8cf7cd81b8dfc345eecd87f8b367acbf25fa1` | 124 796 |
| `kd1000__escaneado_d5b.png` | `aa98dba048a34fa20aab6532af8b78145a3b5db5389286d09222cbdce0e546d5` | 71 068 |
| `kd1000__escaneado_d5c.png` | `32d84cf07192de0704d4d944cc95b3df5af2a429653b54acfee4eb9a1ac8b0d5` | 116 022 |
| `kd1125__escaneado_d5.png` | `1b59caa85012ec76c1cb726275a16d682bbc893f0e3c73455c633835a99a9725` | 104 396 |
| `kd1125__escaneado_d5a.png` | `6009ea4e049ca375975bfaa6096c693895af6ec54eced794497ca86fc986aef9` | 135 698 |
| `kd1125__escaneado_d5b.png` | `4c46746b318f9d2432f0ce268bf681692992a6093c619d56debccd88e7232aa5` | 76 742 |
| `kd1125__escaneado_d5c.png` | `3ccb046c6cc776d8e67c4b3258a1104d520d5b63f63a9e39589095123565b705` | 122 500 |
| `kd1250__escaneado_d5.png` | `ea11877e8ff3e538c19952c18997abf232549474bbaf00b6da1596cb33c2b7f6` | 108 902 |
| `kd1250__escaneado_d5a.png` | `96d76477891e837da180d67cc381aeb9fdf7c550ed502b4b09eb85a81709cd32` | 143 032 |
| `kd1250__escaneado_d5b.png` | `13927ea108c0f425a471f4adaecf0ce8df15c67ff71354895db04206c3e9d1c0` | 77 830 |
| `kd1250__escaneado_d5c.png` | `8b029d9b94327c64fa5a962135ba1c9a4aa67a98ce9bad4fee6dbe6bf9c1dd3d` | 128 239 |
| `kd1400__escaneado_d5.png` | `ea041cea69dcb242de554114ebedd7f7298a8c20ddbe082d6fccef7c185dd3f1` | 115 583 |
| `kd1400__escaneado_d5a.png` | `0c6dfec00f0e87545ed0b13e2d27c135cff9c76aac787d5d10ffb5bcc2a8394c` | 149 002 |
| `kd1400__escaneado_d5b.png` | `d437eafe220d65f45719ccdf2c48ee6e19afc5cb1a2db1a2e8b685dee13ec16c` | 84 438 |
| `kd1400__escaneado_d5c.png` | `ec0164a15127b7b4c5410efd0439fe990ed1877135129f460a8b1293b5049fc4` | 138 969 |
| `kd1600__escaneado_d5.png` | `91460112507e9d352a0d3f815e93cd511d9de9afaab776ecaa2d0f6bb909c31e` | 123 535 |
| `kd1600__escaneado_d5a.png` | `7bf7ea319db5b592ca21ff4cd7e06529a8c10f2f3f272cbc7febd395b8e8f9ca` | 158 068 |
| `kd1600__escaneado_d5b.png` | `94a3279a947a2db60e7ffeeba7cf28220d3193e0413c89f37fb72d070409833b` | 89 652 |
| `kd1600__escaneado_d5c.png` | `08f2d19c8e84397eba57f0066d874b23f9892a5ee69a63867410d5a81628230d` | 146 624 |
| `kd1750__escaneado_d5.png` | `6d7fcaaa27845586abd5f0fdbe76af043367ca1e0885764882e439fc47d1f390` | 124 996 |
| `kd1750__escaneado_d5a.png` | `f4f3857fad018f838d964c18078d190f23849c89db1dcd42c6a21e999f63c1f6` | 163 364 |
| `kd1750__escaneado_d5b.png` | `1025bea6f4789db9a077cfeffaaca7d35103faf6cf5e0bda3a0cb7e02406b867` | 90 437 |
| `kd1750__escaneado_d5c.png` | `cb8fce9cb864398e6c644e03db2fefe64f425758d3d8aef5afbe1d91990fa3a7` | 146 913 |
| `kd2000__escaneado_d5.png` | `bb84715e3831b07231c0f5cfcc091e7c1238b312ff24c96e0232a911a0612652` | 128 497 |
| `kd2000__escaneado_d5a.png` | `81b35d5900c7136ec91af17ff6e28c7930f1bf98c0e7ceae4d73fdc124827f70` | 164 609 |
| `kd2000__escaneado_d5b.png` | `9970a5479c42eae147ca057c8d32f91e0f68a7e5ba15172e5db1b393d558a521` | 93 010 |
| `kd2000__escaneado_d5c.png` | `e666d2d8428b012c99549a3ea2c094ee2a52112a0186f1a542f3bf23a1495cc6` | 150 870 |
| `kd2250__escaneado_d5.png` | `b36289d9a4a8d3ef5cb45e8cf50779bf5071a7263d0a7a5a4daf6a8602bd3290` | 139 140 |
| `kd2250__escaneado_d5a.png` | `2bdd057253fce667f5a4185d28bad2dab4fb10cde77e42530a00285e574d3e20` | 179 984 |
| `kd2250__escaneado_d5b.png` | `df4612021bfb3499042006857d360d6990755b4314ed38236097bbb2f4c948e4` | 100 513 |
| `kd2250__escaneado_d5c.png` | `497dea6d2ead48279cb3b15ff1e994ed6749a10032f4dd05afe62cf44e7019c0` | 162 571 |
| `kd2500__escaneado_d5.png` | `b25e484f23140c9229bbaf81d154bfbae7c6cb7beee755d8fde9a4f53ee10754` | 144 516 |
| `kd2500__escaneado_d5a.png` | `aee55a4a597978a1eb4500a8518cd58cb9027300aa0bd77d00a4fdf4793b63eb` | 183 735 |
| `kd2500__escaneado_d5b.png` | `ac0a6ea1b0fa7794465e3bb3b775fadc3373e43ba87a4ce3e87dfb1467e08ced` | 104 367 |
| `kd2500__escaneado_d5c.png` | `0ccca1775d30b386175a82d580c27dee6ff62478c534d239dc1b9f01fa46e31f` | 167 874 |
| `kd3000__escaneado_d5.png` | `b83d71daf57f8c413ea77bff243c837c173a87c225f0c12d520a5dbbcf8ed144` | 150 234 |
| `kd3000__escaneado_d5a.png` | `85bce7131ace51ed28ce4165b037f3925c2022e81f8733330fba74df0cd4360e` | 191 088 |
| `kd3000__escaneado_d5b.png` | `2c7bff028035462dc480c91cca9634dc7973146b53d7b968cf6fef0380993422` | 108 159 |
| `kd3000__escaneado_d5c.png` | `ce4305860057e785bf05a8871d0f2eb86f05fad5af2aedc15aabe1e430a2f7b0` | 175 382 |
| `kd3500__escaneado_d5.png` | `05056b45f8cfdd4457e9871c59d60b96be5e0f0f460331cc73272c8917269fff` | 167 419 |
| `kd3500__escaneado_d5a.png` | `ec9f650a504b44416203860aaaf3f080630382ea3dbedfe62237f9be78032255` | 214 608 |
| `kd3500__escaneado_d5b.png` | `bb9c380b0a2fca66d6b987bf2c42e9abfb75a0028fd7df0cf946e51d276bfe69` | 120 745 |
| `kd3500__escaneado_d5c.png` | `b97a7850a5b775da4a2653032e635983b1aaf15ef416e9d72f3976f75cd7fd47` | 195 490 |
| `kd4000__escaneado_d5.png` | `adf89feb3e6e9d09b46056b9ee2013ad555db699fbd94887b34c4e6a0be9b64f` | 170 683 |
| `kd4000__escaneado_d5a.png` | `5f0fb011cec579847d33438e66408cf03154147c01596789d1668e38d247e1dc` | 221 258 |
| `kd4000__escaneado_d5b.png` | `683e43ec7da51cff2a0c00df7b526a923351dc0626a5c0afb99eb6dbc36cdcbe` | 124 322 |
| `kd4000__escaneado_d5c.png` | `0fc24390dd17579e1dedd0b345b0884cf8b35de7744b4213b9a42cf21a39e951` | 203 551 |
| `kd5000__escaneado_d5.png` | `1e1ca1c78e8932f18e1827051e32a8811232f6ffc90a7ef488a77ac3cb305cd5` | 188 045 |
| `kd5000__escaneado_d5a.png` | `8a916b3958dbf14ec3875624a60eeea29a068ec027ce59e3d4ec9d71f3c635ad` | 240 588 |
| `kd5000__escaneado_d5b.png` | `cc28078db945313343cc029b2e56447ac1ff901f43ff55ad064c7d9393808aae` | 137 367 |
| `kd5000__escaneado_d5c.png` | `f7d0e8bcc286d709ad3e0a97d665964b732adb8ca6176dc07a272c984e5be41a` | 221 895 |
| `kd6000__escaneado_d5.png` | `4b7de64c5fdaf03246e4ad363106c39dfb4006932f10766396ba92dd88737963` | 201 290 |
| `kd6000__escaneado_d5a.png` | `07d12b2d47f98bde2a3d0f3af6a31452cb23df3074f63276ed530043ffae55fe` | 258 012 |
| `kd6000__escaneado_d5b.png` | `b8941bb3da6e34a773db6610478d0719f196ef49be5e4315e2456a2d0ed377d3` | 143 794 |
| `kd6000__escaneado_d5c.png` | `e472c92b039ef149adcaf7a81c79863b8b952df4221df37c9ce160d715322b41` | 235 540 |
| `kf0750__escaneado_d5.png` | `505a29e8bc9d2578bea56b4c5402499f666dc7ac6aece801a67a54e8c40288b0` | 62 609 |
| `kf0750__escaneado_d5a.png` | `3a28bc18bca16183d5982211595d7176acdbe28ad90f9072aabbfcce4f977dcc` | 81 476 |
| `kf0750__escaneado_d5b.png` | `1e44bb516fd2238bb3fe2b964807543059306df29fac5cd448f189eae3deb67b` | 43 933 |
| `kf0750__escaneado_d5c.png` | `dce136e5cb1d0985e4c3d71c3334d3bfe83c1a3db71325eed0d8b1869ae80052` | 74 394 |
| `kf0875__escaneado_d5.png` | `512295a195da65904a19729d65f41bc6303a5e39d88e9d76ce2e458508b76a99` | 78 417 |
| `kf0875__escaneado_d5a.png` | `fb24c0a62c170623998137d6e5268cfba58a0d9b90e73ebe2dafd8b6853d90c8` | 103 400 |
| `kf0875__escaneado_d5b.png` | `4fa6a9dcf6219bd7454bbce70f3b4057a6477e2c8d62ec0fee4c637f8d8ced34` | 56 800 |
| `kf0875__escaneado_d5c.png` | `88b74a048553ea1af9faa40b4e3cee0bd50f6a3d8cb3eb8d7489d1c893363a36` | 91 779 |
| `kf1000__escaneado_d5.png` | `f89c86d84c13605686f3765acb93d16d84964c76e9251b217309df8aa0facd67` | 97 674 |
| `kf1000__escaneado_d5a.png` | `e6e50b926b8a276c011e1fc232342e0061c4e7471bf4d203a64597737cb1aa5d` | 124 752 |
| `kf1000__escaneado_d5b.png` | `7680d8fa56ef1fd3ffce2fd335a8a8717bb38c36ba6c0b86036bd7d16dd2525f` | 71 024 |
| `kf1000__escaneado_d5c.png` | `1753ccdb0ec478c86ef4215090327a5b6f40c1159bf3cce75fe0dd72738cc4c9` | 115 978 |
| `kf1125__escaneado_d5.png` | `c78ccaa109011f312ac3655aa2954554157889cda6b6a00224c0f664134841db` | 104 352 |
| `kf1125__escaneado_d5a.png` | `1df6b8c8e21e84bf0b859b9a747d47a6a57bb1a911e397f4f1b2d531d79f81bc` | 135 654 |
| `kf1125__escaneado_d5b.png` | `372d5cc133edced996344f25ddd43c0f9f9f37b3d7c7d400f433ad8358e26c0a` | 76 698 |
| `kf1125__escaneado_d5c.png` | `e827deac5b91d00dcf20bec3cca2e0d4557837362994737d9bfb674f8d766885` | 122 456 |
| `kf1250__escaneado_d5.png` | `b8147f5debfe0c1e1f75ef4bd1d434fbd4607b2d84d7a9c35ba35b11d832a5ad` | 108 858 |
| `kf1250__escaneado_d5a.png` | `ed33eb1fa1d40ecb1962f6f0731d26efac2f4edff37b4319ffe5cb570d76e2be` | 142 988 |
| `kf1250__escaneado_d5b.png` | `1017c2fcac3f7f721b53475f15bd0e26f7071ef932c7856f1bb5a729e06fbc50` | 77 786 |
| `kf1250__escaneado_d5c.png` | `6ca45f181714614d646aff1e10bb78db86bdb330020ee8d5f125a6e45f6a8bea` | 128 195 |
| `kf1400__escaneado_d5.png` | `eea831df4c3627d2980142d7253a6618f839d2d1acaa0034dcbe45d6c78977d0` | 115 539 |
| `kf1400__escaneado_d5a.png` | `73198a39162b7d337d93d001b97c961dfb7c2a3bca2bdf624e3e10912f413bdd` | 148 958 |
| `kf1400__escaneado_d5b.png` | `cca7aa274dea26fd0d48b8094937ab27a1fe721b549365c9aae43e50a29005d1` | 84 394 |
| `kf1400__escaneado_d5c.png` | `22cb6c28259fd88c3c57b45a15ff2c774ab9ada7447dca716550ed18ce14f8a1` | 138 925 |
| `kf1600__escaneado_d5.png` | `d82e9da36a1f10c25d7e49f9fb9ca79d73622a6ff28f3fc5a391dabd62c77fe2` | 123 491 |
| `kf1600__escaneado_d5a.png` | `3df275e45c137b7f202901ffd8b779e992f4afc4f5c5fbc7ed25b70a1124f9fd` | 158 024 |
| `kf1600__escaneado_d5b.png` | `d4fa3383d261f8359081803c7857af382c5db97f6be324c0f5bcf3b8acc4ed21` | 89 608 |
| `kf1600__escaneado_d5c.png` | `cb6a5a1275528e4c0495d180b4b36aafd7c70e832599d43ea0bb41ec7563f22d` | 146 580 |
| `kf1750__escaneado_d5.png` | `a9c27b1f560715c7f114e6e7799fec7b86f19e980b6f6eec07c023dddd0df956` | 124 952 |
| `kf1750__escaneado_d5a.png` | `f7208a80fd85693d99d3399021293f453b734902e280eceef98c7facfb44180c` | 163 320 |
| `kf1750__escaneado_d5b.png` | `2faa869c8900b0e8edaaf571303022d042d27c1fea627cc605f1c283df3678e2` | 90 393 |
| `kf1750__escaneado_d5c.png` | `20a114f6c0ca2657119a50d5e4db0fbddb04b97b09e32905775bf31ac60130e4` | 146 869 |
| `kf2000__escaneado_d5.png` | `4bd4014a33f579a1d4f0a2d46a84ff7cec7d0f1aa2c734a89eaed5be49fd0b61` | 128 453 |
| `kf2000__escaneado_d5a.png` | `50bee206fd6ee9fb1044620fdcc69a928722ffb5560d5325a0c60e8a707746b4` | 164 565 |
| `kf2000__escaneado_d5b.png` | `c6cdd6bbcda68ee66e7b24ca7a2d86846f1d61729b8b0001576e5fd2ebb12d28` | 92 966 |
| `kf2000__escaneado_d5c.png` | `b6810674c5de7bdf6b79a9ff9ce69b4d8cd2d583850f7fdc9ab4d14e1e7be2cc` | 150 826 |
| `kf2250__escaneado_d5.png` | `633be2587a70da102f32fe240cf4c03d6285bdf3d8d3ed41f62f887d8db13bee` | 139 096 |
| `kf2250__escaneado_d5a.png` | `75f6423a51d734979bffb4607b34f9b1003442519666b405de37de47c6deebdd` | 179 940 |
| `kf2250__escaneado_d5b.png` | `c5e321021b2f563368e9a9da216b67f04b6b96cc1f189e0bae3d0abbe7d3b587` | 100 469 |
| `kf2250__escaneado_d5c.png` | `7af1cf578ac57a59c4b6237dcf255c6f7bd2db9c5a6cc5df35d9b5941cceea6a` | 162 527 |
| `kf2500__escaneado_d5.png` | `0b485aeed158a413a2c304057545d3007dd9e88db48aa88c6a4c4624e33db6da` | 144 472 |
| `kf2500__escaneado_d5a.png` | `75f17b40c4fa077f6eed05ff5570c8d6ec50db1e053ed788b98bc5091c7dfae6` | 183 691 |
| `kf2500__escaneado_d5b.png` | `04a7e823c3e49db2b4097ce32e3a426f372a5b6820861d11b83615e50bce146d` | 104 323 |
| `kf2500__escaneado_d5c.png` | `238880a227a16a5ea3b753ac727e7eb53477877a18e5ee9dda63856a34fc0c9a` | 167 830 |
| `kf3000__escaneado_d5.png` | `bc267d061f14096c46d1ac2f0f6a636402d2048ad2aa17b057dcef5007962623` | 150 190 |
| `kf3000__escaneado_d5a.png` | `b1e8f02b61b051a597d5a7dd2b30eb2b75faf721840cda3917daf9999ec7712d` | 191 044 |
| `kf3000__escaneado_d5b.png` | `feea3ba7106cc698354cc85c639a5de4b20f65f70afafcc25f87085aecd2efd9` | 108 115 |
| `kf3000__escaneado_d5c.png` | `b72d67c8583ccb33e0f9a37cc6266d0234877cdd8ff7a866f977d478152cf497` | 175 338 |
| `kf3500__escaneado_d5.png` | `2ec20540cb13113f3f8d70c86c7d0e0079cedfc5b495700068c23c2f68e52bb6` | 167 375 |
| `kf3500__escaneado_d5a.png` | `acbd822bf62f1a7c3ebe267de4c5d4541c34a584828e1dde4673ece1a7802bdd` | 214 564 |
| `kf3500__escaneado_d5b.png` | `0fc704766017fadefc67b8172504e6a3d4e4c82962484073eb04556f3ebbdabf` | 120 701 |
| `kf3500__escaneado_d5c.png` | `98682b514e94de5369cee8e1083dccb537cee5666dbca1287fd2b2e25e06431d` | 195 446 |
| `kf4000__escaneado_d5.png` | `f3c7fe994c4122e248fd7061270242ad462387183499d8dc198e79563c0bda87` | 170 639 |
| `kf4000__escaneado_d5a.png` | `7d4837f55c4f083ab71d138414feeb55ca63ea94a11e92eaa6b422fe9f3b7d07` | 221 214 |
| `kf4000__escaneado_d5b.png` | `d518a06e8f481c8be2bb48db5caaa98e7e88e8c25f74cbdbd6078450a0f3453a` | 124 278 |
| `kf4000__escaneado_d5c.png` | `7aa5601cfe93a02399f37b1ab402eb2f7ee2c7464f7df55e86585bb782b469a5` | 203 507 |
| `kf5000__escaneado_d5.png` | `8c79cb4564848c1350942981d79b878baf837f7af16fa2e50055ff99dde75ff8` | 188 001 |
| `kf5000__escaneado_d5a.png` | `f20fb350800b0be4b165aae840eda59f811b9a62fb21a5afc03b75b435634225` | 240 544 |
| `kf5000__escaneado_d5b.png` | `e3261384310cac22b14143c25cea70366c06564d839cddcbebbce969592bd0ab` | 137 323 |
| `kf5000__escaneado_d5c.png` | `8325e38b11773024fe7e286b4d44c80f885fa9969bc5c64c3646c8f04bdcabf3` | 221 851 |
| `kf6000__escaneado_d5.png` | `8dacf4a2c553cb3a065db38cbccb8bd7fa3467aa256f68023226aa7c83f1bcc7` | 201 246 |
| `kf6000__escaneado_d5a.png` | `d7cb089c35f08a9a8295801828ccf17d84d346d07779390e8465a03abf3e423e` | 257 968 |
| `kf6000__escaneado_d5b.png` | `d90ce32f16da2ee8e76f8dbdaf67d287f6208f33d243f685cbf7ea534c0b4b42` | 143 750 |
| `kf6000__escaneado_d5c.png` | `8db96401662bfd828f7f5a2da03858b1a9ca46582b05a9ebe56e535eba97012e` | 235 496 |

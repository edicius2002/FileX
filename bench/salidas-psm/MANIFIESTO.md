# MANIFIESTO — `bench/salidas-psm/` (agente G2, B17 · B18 · B14)

**Las rasterizaciones son binarios regenerables y NO se versionan**
(`CLAUDE.md` §6). Aquí quedan su `sha256`, su tamaño, su geometría y la orden
exacta que las reproduce.

**133 ficheros, 120.1 MB**, borrados al terminar.

## 1. Las órdenes exactas

Desde `D:\Work\research\FileX\bench\salidas-psm`:

```
python raster_psm.py <variante> <f,f,...> <doc> [doc ...]
```

que ejecuta, por variante:

- **`im`** — `magick -density <ppp> corpus/pdf/<doc>.pdf[0] -colorspace Gray -alpha remove -background white -flatten <salida>`
- **`im_ppi`** — `magick -density <ppp> corpus/pdf/<doc>.pdf[0] -colorspace Gray -alpha remove -background white -flatten -units PixelsPerInch -density <ppp> <salida>`
- **`im_sincs`** — `magick -density <ppp> corpus/pdf/<doc>.pdf[0] -alpha remove -background white -flatten <salida>`
- **`gs`** — `gswin64c -dNOPAUSE -dBATCH -dSAFER -q -dFirstPage=1 -dLastPage=1 -sDEVICE=pnggray -r<ppp> -sOutputFile=<salida> corpus/pdf/<doc>.pdf`
- **`gs_aa1`** — `gswin64c ... -sDEVICE=pnggray -r<ppp> -dTextAlphaBits=1 -dGraphicsAlphaBits=1 -sOutputFile=<salida> corpus/pdf/<doc>.pdf`
- **`gs_aa4`** — `gswin64c ... -sDEVICE=pnggray -r<ppp> -dTextAlphaBits=4 -dGraphicsAlphaBits=4 -sOutputFile=<salida> corpus/pdf/<doc>.pdf`
- **`gs16m_im`** — `gswin64c ... -sDEVICE=png16m -r<ppp> -sOutputFile=<tmp> corpus/pdf/<doc>.pdf  &&  magick <tmp> -colorspace Gray <salida>`
- **`gs16m_im601`** — `gswin64c ... -sDEVICE=png16m -r<ppp> ...  &&  magick <tmp> -intensity Rec601Luma -grayscale Rec601Luma <salida>`
- **`gs16m_im709`** — `gswin64c ... -sDEVICE=png16m -r<ppp> ...  &&  magick <tmp> -intensity Rec709Luma -grayscale Rec709Luma <salida>`

con `<ppp> = round(ppp_nativos × factor)` y `ppp_nativos` leído de la imagen incrustada del PDF con `pypdfium2` (`raster_psm.geometria`).

Y las tandas de OCR:

```
REPS=9 python tess_psm.py "<glob>" "<psm,psm,...>" "<etiqueta>" spa
TESS_DPI=<n> REPS=9 python tess_psm.py ...   # para el eje de resolucion
bash run_bcd.sh                              # tandas B, C y D en serie
python tablas_psm.py                         # tablas.md + json/resumen.json
```

**Entorno de las tandas de OCR:** `TESSDATA_PREFIX=C:\Program Files\PDFgear\tessdata` (16 idiomas, **los puso PDFgear, no este proyecto**), binario `C:\Program Files\Tesseract-OCR\tesseract.exe` v5.5.0.20241111, `-l spa`, `stdin=DEVNULL`, `timeout=600` por llamada.

## 2. Las rasterizaciones

| fichero | variante | documento | factor | ppp | px | Mpx | bytes | sha256 |
|---|---|---|---:|---:|---|---:|---:|---|
| `gs16m_im601__k1000__escaneado_d2.png` | gs16m_im601 | escaneado_d2 | ×1 | 100 | 647x850 | 0.55 | 318948 | `26adc52848b43eb94cdad330df1db795ab3abff9e73fd9fe4e0b5cc0cdc75c79` |
| `gs16m_im601__k1000__escaneado_d3.png` | gs16m_im601 | escaneado_d3 | ×1 | 100 | 647x850 | 0.55 | 364085 | `f9789b3a6954712da906e94a8d67dd77a41348925039860bebda3ff62768f547` |
| `gs16m_im601__k1000__escaneado_d4.png` | gs16m_im601 | escaneado_d4 | ×1 | 200 | 1294x1716 | 2.221 | 1172493 | `30b0218d28ea00fe22b5d840698b1ea5f737ac2fccb92e937829b4a265c7a942` |
| `gs16m_im601__k1000__escaneado_d4c.png` | gs16m_im601 | escaneado_d4c | ×1 | 200 | 1294x1734 | 2.244 | 1141561 | `4fbaf840c7a9f1a0a314388a74a7e183bb88950677de0a9e4a5424d98398d54f` |
| `gs16m_im601__k1000__escaneado_d4e.png` | gs16m_im601 | escaneado_d4e | ×1 | 200 | 1294x1716 | 2.221 | 1153532 | `4bfae776ad117824247cec7cc1b48da00ff6df6fa78da454f25d61a55b14b5e2` |
| `gs16m_im601__k1000__escaneado_d4f.png` | gs16m_im601 | escaneado_d4f | ×1 | 240 | 1552x2080 | 3.228 | 1635748 | `da2ced35beb58f5466c05b2069b7ec946190631bb17afda5d3432d30ebefaae4` |
| `gs16m_im709__k1000__escaneado_d2.png` | gs16m_im709 | escaneado_d2 | ×1 | 100 | 647x850 | 0.55 | 318948 | `e4f1e9a8d5e4a297aab6d3a9f39183b0f1015c3832d26a324f575530e79bd919` |
| `gs16m_im709__k1000__escaneado_d3.png` | gs16m_im709 | escaneado_d3 | ×1 | 100 | 647x850 | 0.55 | 364085 | `b9d33ec3930045b9f4741a28b3b9688df02fd45ef68b47251e59d754a86d84fb` |
| `gs16m_im709__k1000__escaneado_d4.png` | gs16m_im709 | escaneado_d4 | ×1 | 200 | 1294x1716 | 2.221 | 1172493 | `0e448b382cdbf96f17c92db725bbf0dbe8970e8a3b498d356694090950254aa6` |
| `gs16m_im709__k1000__escaneado_d4c.png` | gs16m_im709 | escaneado_d4c | ×1 | 200 | 1294x1734 | 2.244 | 1141561 | `a97ac09de57d74a53d7cc59388014e802ee178190a09d3bd76cdedc83d2f909a` |
| `gs16m_im709__k1000__escaneado_d4e.png` | gs16m_im709 | escaneado_d4e | ×1 | 200 | 1294x1716 | 2.221 | 1153532 | `317b20499cf483b4a98e0e6f36c108a612626bea664a0bf1312f527b32e70695` |
| `gs16m_im709__k1000__escaneado_d4f.png` | gs16m_im709 | escaneado_d4f | ×1 | 240 | 1552x2080 | 3.228 | 1635748 | `8a473caf67f363d4cdcba7ca7d5d64b32b3303c17b8ac4a05a32124efae86b77` |
| `gs16m_im__k1000__escaneado_d2.png` | gs16m_im | escaneado_d2 | ×1 | 100 | 647x850 | 0.55 | 318948 | `519969af513448299b679207309d91da7a33fa710e5b46ec57e767e349792b42` |
| `gs16m_im__k1000__escaneado_d3.png` | gs16m_im | escaneado_d3 | ×1 | 100 | 647x850 | 0.55 | 364085 | `2fc459df901d6defb534c58fcd17ce0788cfe63a097b88f12c2cb203566aa1e5` |
| `gs16m_im__k1000__escaneado_d4.png` | gs16m_im | escaneado_d4 | ×1 | 200 | 1294x1716 | 2.221 | 1172493 | `319e1949233d2c0e9bdbfba1efb8b33729ad76d50cab2c6799f386631a85b2db` |
| `gs16m_im__k1000__escaneado_d4c.png` | gs16m_im | escaneado_d4c | ×1 | 200 | 1294x1734 | 2.244 | 1141561 | `d7e283b51ae57b97d4884770fdeb3f44cc23f43a8b102ea176c6d665d9bd0807` |
| `gs16m_im__k1000__escaneado_d4e.png` | gs16m_im | escaneado_d4e | ×1 | 200 | 1294x1716 | 2.221 | 1153532 | `3b7d93df063c8b74c9aff1138fff7476e8e5402422ddc293a3bb1f779733ca28` |
| `gs16m_im__k1000__escaneado_d4f.png` | gs16m_im | escaneado_d4f | ×1 | 240 | 1552x2080 | 3.228 | 1635748 | `6ff5db27e256aae78890b88d80fbdf5b0a7f8d8d7077350160cf5ee31cd961ec` |
| `gs__k1000__escaneado_d2.png` | gs | escaneado_d2 | ×1 | 100 | 647x850 | 0.55 | 322014 | `215b41e64b342645503e2d2ceba23f4e5569c0660de52bea597ce47879824898` |
| `gs__k1000__escaneado_d3.png` | gs | escaneado_d3 | ×1 | 100 | 647x850 | 0.55 | 367433 | `8aa0105b1360163d5c2e62564f876409963e11cf780e2400f2d204d692becc02` |
| `gs__k1000__escaneado_d4.png` | gs | escaneado_d4 | ×1 | 200 | 1294x1716 | 2.221 | 1179035 | `99613281cc45f7a68f6d204a2bcd0df6af4c3884867eb73e76b445a65cf08a7e` |
| `gs__k1000__escaneado_d4c.png` | gs | escaneado_d4c | ×1 | 200 | 1294x1734 | 2.244 | 1148678 | `b55e24e2695b75317f6180e8c2f279b4f20516e5bbccd29e623d539a59a2fcac` |
| `gs__k1000__escaneado_d4e.png` | gs | escaneado_d4e | ×1 | 200 | 1294x1716 | 2.221 | 1159871 | `c0a9ad4edbca0389a76be7d7ff4cc83b2bf8a35579808b49d86e23d6b08f377b` |
| `gs__k1000__escaneado_d4f.png` | gs | escaneado_d4f | ×1 | 240 | 1552x2080 | 3.228 | 1644741 | `ac388ea86697d7330933f1edc7c85b91aa43a57d09ae60def834d4d204c52d31` |
| `gs_aa1__k1000__escaneado_d2.png` | gs_aa1 | escaneado_d2 | ×1 | 100 | 647x850 | 0.55 | 322014 | `215b41e64b342645503e2d2ceba23f4e5569c0660de52bea597ce47879824898` |
| `gs_aa1__k1000__escaneado_d3.png` | gs_aa1 | escaneado_d3 | ×1 | 100 | 647x850 | 0.55 | 367433 | `8aa0105b1360163d5c2e62564f876409963e11cf780e2400f2d204d692becc02` |
| `gs_aa1__k1000__escaneado_d4.png` | gs_aa1 | escaneado_d4 | ×1 | 200 | 1294x1716 | 2.221 | 1179035 | `99613281cc45f7a68f6d204a2bcd0df6af4c3884867eb73e76b445a65cf08a7e` |
| `gs_aa1__k1000__escaneado_d4c.png` | gs_aa1 | escaneado_d4c | ×1 | 200 | 1294x1734 | 2.244 | 1148678 | `b55e24e2695b75317f6180e8c2f279b4f20516e5bbccd29e623d539a59a2fcac` |
| `gs_aa1__k1000__escaneado_d4e.png` | gs_aa1 | escaneado_d4e | ×1 | 200 | 1294x1716 | 2.221 | 1159871 | `c0a9ad4edbca0389a76be7d7ff4cc83b2bf8a35579808b49d86e23d6b08f377b` |
| `gs_aa1__k1000__escaneado_d4f.png` | gs_aa1 | escaneado_d4f | ×1 | 240 | 1552x2080 | 3.228 | 1644741 | `ac388ea86697d7330933f1edc7c85b91aa43a57d09ae60def834d4d204c52d31` |
| `gs_aa4__k1000__escaneado_d2.png` | gs_aa4 | escaneado_d2 | ×1 | 100 | 647x850 | 0.55 | 322014 | `215b41e64b342645503e2d2ceba23f4e5569c0660de52bea597ce47879824898` |
| `gs_aa4__k1000__escaneado_d3.png` | gs_aa4 | escaneado_d3 | ×1 | 100 | 647x850 | 0.55 | 367433 | `8aa0105b1360163d5c2e62564f876409963e11cf780e2400f2d204d692becc02` |
| `gs_aa4__k1000__escaneado_d4.png` | gs_aa4 | escaneado_d4 | ×1 | 200 | 1294x1716 | 2.221 | 1179035 | `99613281cc45f7a68f6d204a2bcd0df6af4c3884867eb73e76b445a65cf08a7e` |
| `gs_aa4__k1000__escaneado_d4c.png` | gs_aa4 | escaneado_d4c | ×1 | 200 | 1294x1734 | 2.244 | 1148678 | `b55e24e2695b75317f6180e8c2f279b4f20516e5bbccd29e623d539a59a2fcac` |
| `gs_aa4__k1000__escaneado_d4e.png` | gs_aa4 | escaneado_d4e | ×1 | 200 | 1294x1716 | 2.221 | 1159871 | `c0a9ad4edbca0389a76be7d7ff4cc83b2bf8a35579808b49d86e23d6b08f377b` |
| `gs_aa4__k1000__escaneado_d4f.png` | gs_aa4 | escaneado_d4f | ×1 | 240 | 1552x2080 | 3.228 | 1644741 | `ac388ea86697d7330933f1edc7c85b91aa43a57d09ae60def834d4d204c52d31` |
| `im__k0500__escaneado_d3.png` | im | escaneado_d3 | ×0.5 | 50 | 323x425 | 0.137 | 103689 | `f7b68a89a8983853a989f85ea32e0b767bb043668a9e8bcbb15960d09f1da5d5` |
| `im__k0500__escaneado_d4.png` | im | escaneado_d4 | ×0.5 | 100 | 647x858 | 0.555 | 370313 | `f50b1cde71c5208fbd3e4656284e0d6a07e7134efc92a82b8a7e3aaa69ebb4cd` |
| `im__k0625__escaneado_d3.png` | im | escaneado_d3 | ×0.625 | 62 | 401x527 | 0.211 | 153779 | `4089d4df41efa4d82074dee6efdae36497296cfbf942ad69e7df90e519849c94` |
| `im__k0625__escaneado_d4.png` | im | escaneado_d4 | ×0.625 | 125 | 809x1073 | 0.868 | 551597 | `a34fa0a828b7c8b98d1c5ca05318e69678196d7f9664b9a59a2bc5a6b8d3408c` |
| `im__k0750__escaneado_d3.png` | im | escaneado_d3 | ×0.75 | 75 | 485x638 | 0.309 | 217118 | `0936da846574dfb5d11b0e42200b6c725dd3b1228a864d11b4a8b16bbc339e1f` |
| `im__k0750__escaneado_d4.png` | im | escaneado_d4 | ×0.75 | 150 | 970x1287 | 1.248 | 755752 | `d84bf789337c2722c9997e0f8b4639e4d29313a570d286b0c6fced696642346d` |
| `im__k0875__escaneado_d3.png` | im | escaneado_d3 | ×0.875 | 88 | 569x748 | 0.426 | 289788 | `3a1a53844ff7c80a213463bc65ee43833187bec364efdb25dd261e0b0a88924a` |
| `im__k0875__escaneado_d4.png` | im | escaneado_d4 | ×0.875 | 175 | 1132x1502 | 1.7 | 933249 | `9f1d9c2a5e63b27512ec426859d0286a829b652ce0386a8d5e4c7c22646fdafa` |
| `im__k1000__escaneado_d2.png` | im | escaneado_d2 | ×1 | 100 | 647x850 | 0.55 | 318982 | `92a84ba2b723a612dedc7ac5e51418effd834bd4c805f6ca877c6fc692e92fd1` |
| `im__k1000__escaneado_d3.png` | im | escaneado_d3 | ×1 | 100 | 647x850 | 0.55 | 364119 | `d005f629e8644dfe4e62b3bded71fd02b2110c515e131fe0098351b2d1ea2c3c` |
| `im__k1000__escaneado_d4.png` | im | escaneado_d4 | ×1 | 200 | 1294x1716 | 2.221 | 1172530 | `19c3839766b6e4770d4ac1848fb8b7575b92889ef42a6d896cabf0767edf21e3` |
| `im__k1000__escaneado_d4c.png` | im | escaneado_d4c | ×1 | 200 | 1294x1734 | 2.244 | 1141598 | `a0223e882cb756fe7712097c1e692ad31a42f58721b6e7282044a7b81d7c9b30` |
| `im__k1000__escaneado_d4e.png` | im | escaneado_d4e | ×1 | 200 | 1294x1716 | 2.221 | 1153569 | `6aa4475ab92c2a87262b47e9b65a8bc429b5506a938f9ff16c0d4bc956480e57` |
| `im__k1000__escaneado_d4f.png` | im | escaneado_d4f | ×1 | 240 | 1552x2080 | 3.228 | 1635781 | `950616632c33135b9e5d69f0f0607d318c0297336e5acc1ec9493b5a01fdb05f` |
| `im__k1125__escaneado_d3.png` | im | escaneado_d3 | ×1.125 | 112 | 725x952 | 0.69 | 393120 | `389b9ea6babb119e7a27754f49be681ad5c7e827e6179c5620b07cfeaaf5eb08` |
| `im__k1125__escaneado_d4.png` | im | escaneado_d4 | ×1.125 | 225 | 1456x1931 | 2.812 | 1262467 | `588b21c813bd06dd58a318ef005c4d291209a34a1721abb476a0d110385b72ad` |
| `im__k1250__escaneado_d3.png` | im | escaneado_d3 | ×1.25 | 125 | 809x1063 | 0.86 | 414307 | `5cdbad2d2821c5047a85be2d8804b4af4d79d2c111c6244a4ddaaa7726719bca` |
| `im__k1250__escaneado_d4.png` | im | escaneado_d4 | ×1.25 | 250 | 1617x2145 | 3.468 | 1338347 | `f863a3e8c6df4269e4ff4a35ee1459ba199b89399ec14bf6cdc4a70f95e9581f` |
| `im__k1400__escaneado_d3.png` | im | escaneado_d3 | ×1.4 | 140 | 906x1190 | 1.078 | 436391 | `c5a0c6d5d25e0762bf4e34207245b076b7514c3ad8e19186d7a472ab841d8cac` |
| `im__k1400__escaneado_d4.png` | im | escaneado_d4 | ×1.4 | 280 | 1812x2402 | 4.352 | 1441993 | `94973c5157ea91044b61737184d816257d5b8b5388afaf2723132c295fa20069` |
| `im__k1500__escaneado_d3.png` | im | escaneado_d3 | ×1.5 | 150 | 970x1275 | 1.237 | 447327 | `5d783ba3cb1fafd115c6e5c48b5e46654a6b3decf05da7bf7afddf7ecd96561d` |
| `im__k1500__escaneado_d4.png` | im | escaneado_d4 | ×1.5 | 300 | 1941x2574 | 4.996 | 1442471 | `7fdc525f948904953782c711e1183e27e12e9fe485706f24cc9d841a0af2f2e5` |
| `im__k1600__escaneado_d3.png` | im | escaneado_d3 | ×1.6 | 160 | 1035x1360 | 1.408 | 464948 | `207dc6bd053dfa7fdd741b96ed0c1ca1214d8e2ea33d476dc6d0e8981f570217` |
| `im__k1600__escaneado_d4.png` | im | escaneado_d4 | ×1.6 | 320 | 2070x2746 | 5.684 | 1537339 | `989cd7421bf45fc14df58b896354761c5c3123ec3e1000232f9169ad8e2a585f` |
| `im__k1800__escaneado_d3.png` | im | escaneado_d3 | ×1.8 | 180 | 1165x1530 | 1.782 | 485234 | `0a3426b8decb7ce5b278d1b4239e7e09602db73763f5d97ce2772e9f0916efe5` |
| `im__k1800__escaneado_d4.png` | im | escaneado_d4 | ×1.8 | 360 | 2329x3089 | 7.194 | 1612308 | `85845ff196e0c1dd3c5b86ce7533bc9fe2972694cb1fa5e300e4aad7dfe99674` |
| `im_ppi__k0500__escaneado_d2.png` | im_ppi | escaneado_d2 | ×0.5 | 50 | 323x425 | 0.137 | 93356 | `a669a7ee59d11d5467545ea44b47c595c9dc2fd0119a4d5286f0fcf1c94a370f` |
| `im_ppi__k0500__escaneado_d3.png` | im_ppi | escaneado_d3 | ×0.5 | 50 | 323x425 | 0.137 | 103689 | `bfcbf0a766f2834ef1437e91e751e44074e8b9eef6c5206c13ff82d936f15a54` |
| `im_ppi__k0500__escaneado_d4.png` | im_ppi | escaneado_d4 | ×0.5 | 100 | 647x858 | 0.555 | 370313 | `293a6032bc6801141568abe0cea09b1680a1e1ff03574dd3bc06d78630791ccf` |
| `im_ppi__k0500__escaneado_d4c.png` | im_ppi | escaneado_d4c | ×0.5 | 100 | 647x867 | 0.561 | 356774 | `45479b8895151348affb358b523015fcdcd7d73dc8d6315804b02693281273f8` |
| `im_ppi__k0500__escaneado_d4e.png` | im_ppi | escaneado_d4e | ×0.5 | 100 | 647x858 | 0.555 | 381917 | `1a343fc8b9c0f008525423b1eb4d313980efa62019d9b395231e1d416615d9bc` |
| `im_ppi__k0500__escaneado_d4f.png` | im_ppi | escaneado_d4f | ×0.5 | 120 | 776x1040 | 0.807 | 518236 | `236149636b80e77f4baca881519c882e9d7e23e50cdb82a087913460d2e6f475` |
| `im_ppi__k0625__escaneado_d2.png` | im_ppi | escaneado_d2 | ×0.625 | 62 | 401x527 | 0.211 | 136882 | `6fab87859dc7f12b3919b559ec0135d924f212a7075bacadf31df8bf368786af` |
| `im_ppi__k0625__escaneado_d3.png` | im_ppi | escaneado_d3 | ×0.625 | 62 | 401x527 | 0.211 | 153779 | `b6552f5b2ccfc3ced6a6a5cef48670985cdded0c06abc9526bbe590f2fb94445` |
| `im_ppi__k0625__escaneado_d4.png` | im_ppi | escaneado_d4 | ×0.625 | 125 | 809x1073 | 0.868 | 551597 | `1b74c7a60067e00854eae2e44c9c8fe4283254a5d08b5456559d255ebe05090e` |
| `im_ppi__k0625__escaneado_d4c.png` | im_ppi | escaneado_d4c | ×0.625 | 125 | 809x1084 | 0.877 | 535665 | `0b7cbb1101c9475288a4f6f1471dbbbd9fa957165d227f81bb45c2c1dfc6032c` |
| `im_ppi__k0625__escaneado_d4e.png` | im_ppi | escaneado_d4e | ×0.625 | 125 | 809x1073 | 0.868 | 563357 | `9e37ac30cc4c4d418fdc29fe15f799411a01a22ff8a0c02bc9ea7aaa592bbdfd` |
| `im_ppi__k0625__escaneado_d4f.png` | im_ppi | escaneado_d4f | ×0.625 | 150 | 970x1300 | 1.261 | 803451 | `a7d6fed0e3258ea288719099a5e951dbdc03e0874ef315c1907ad61c9a2fe5b1` |
| `im_ppi__k0750__escaneado_d2.png` | im_ppi | escaneado_d2 | ×0.75 | 75 | 485x638 | 0.309 | 191485 | `84332adbc06021d7b41f5db10fdd4f6efbd2530e5a909b39b5e327771baf0707` |
| `im_ppi__k0750__escaneado_d3.png` | im_ppi | escaneado_d3 | ×0.75 | 75 | 485x638 | 0.309 | 217118 | `ffb296ec29e97ed1db49a7772806f54cdbab3735246b228155b675b9747fa90d` |
| `im_ppi__k0750__escaneado_d4.png` | im_ppi | escaneado_d4 | ×0.75 | 150 | 970x1287 | 1.248 | 755752 | `cc92461dfb69b2b780316f9f51e59f2069e059b106db08ba2f0dd16a0d4bda37` |
| `im_ppi__k0750__escaneado_d4c.png` | im_ppi | escaneado_d4c | ×0.75 | 150 | 970x1300 | 1.261 | 714895 | `3eeef2be1478ddb956828081c83efe8b4ff3c0a1ae9827ad060d5f5ed810a166` |
| `im_ppi__k0750__escaneado_d4e.png` | im_ppi | escaneado_d4e | ×0.75 | 150 | 970x1287 | 1.248 | 758654 | `ca7f377c7be8eaf7bb110ab651128046c048c36751dff70b9d6f18342a452f53` |
| `im_ppi__k0750__escaneado_d4f.png` | im_ppi | escaneado_d4f | ×0.75 | 180 | 1164x1560 | 1.816 | 1054840 | `b6af4456e98739749eae4b92f61c07cb727a406a46e2bf0c7ac20e8382060cc3` |
| `im_ppi__k0875__escaneado_d2.png` | im_ppi | escaneado_d2 | ×0.875 | 88 | 569x748 | 0.426 | 254798 | `f0d518b75a37fea3f550ed727608a21ec9258ff4388cebe0c16f07b8397a359f` |
| `im_ppi__k0875__escaneado_d3.png` | im_ppi | escaneado_d3 | ×0.875 | 88 | 569x748 | 0.426 | 289788 | `122a0edaec3ec1fc5188859e84b675f2959ab58271026fa75d5a91172d910401` |
| `im_ppi__k0875__escaneado_d4.png` | im_ppi | escaneado_d4 | ×0.875 | 175 | 1132x1502 | 1.7 | 933249 | `ce59f58d3ba8907b390861bbf4abbc93d87c4fa2a49fff475e60cb0aa926a722` |
| `im_ppi__k0875__escaneado_d4c.png` | im_ppi | escaneado_d4c | ×0.875 | 175 | 1132x1517 | 1.717 | 921522 | `f9f41901a5945cca38165d88d75f0d360904c0f19a710f7de637699838149b48` |
| `im_ppi__k0875__escaneado_d4e.png` | im_ppi | escaneado_d4e | ×0.875 | 175 | 1132x1502 | 1.7 | 924508 | `7e3ed3419e6dd5ecee294b4997146bbe86d987ab507d396ca3b07d7a9917fa9d` |
| `im_ppi__k0875__escaneado_d4f.png` | im_ppi | escaneado_d4f | ×0.875 | 210 | 1358x1820 | 2.472 | 1334166 | `1da8efdae6a240dd71a9d50a5df724a30a21ea9cf85aa02c007eed23afaf50db` |
| `im_ppi__k1000__escaneado_d2.png` | im_ppi | escaneado_d2 | ×1 | 100 | 647x850 | 0.55 | 318982 | `27b9be0e11717c31a011e5f2da20f56cdc4fcd03ab67e06a46f33fd5bb729b1d` |
| `im_ppi__k1000__escaneado_d3.png` | im_ppi | escaneado_d3 | ×1 | 100 | 647x850 | 0.55 | 364119 | `d36847b352c2aebe40fe9afb1c079fc57dbf6066819e3930ba6ad2b7ad587864` |
| `im_ppi__k1000__escaneado_d4.png` | im_ppi | escaneado_d4 | ×1 | 200 | 1294x1716 | 2.221 | 1172530 | `eaea09181577109301f0cc904e2dd0ac01a687980e21ba63815a1c9f0ba4e709` |
| `im_ppi__k1000__escaneado_d4c.png` | im_ppi | escaneado_d4c | ×1 | 200 | 1294x1734 | 2.244 | 1141598 | `3f69956e7882b9b8b1c6cc922a653940c40e5e99ed6ffe93b39b3b9dba910011` |
| `im_ppi__k1000__escaneado_d4e.png` | im_ppi | escaneado_d4e | ×1 | 200 | 1294x1716 | 2.221 | 1153569 | `87adbf15c38a26e8044298794cd8e1a855b197a09d153301d90856dcb307ef08` |
| `im_ppi__k1000__escaneado_d4f.png` | im_ppi | escaneado_d4f | ×1 | 240 | 1552x2080 | 3.228 | 1635781 | `9b42a5dc0271ff64e154ae4821d37ae0d624529b3c0b5a56873cc7f6539b30fe` |
| `im_ppi__k1125__escaneado_d2.png` | im_ppi | escaneado_d2 | ×1.125 | 112 | 725x952 | 0.69 | 345489 | `f4fd515317debe7bd9ae6a8b8c0ebbc19463c6780500d53a0f63739dc795f5eb` |
| `im_ppi__k1125__escaneado_d3.png` | im_ppi | escaneado_d3 | ×1.125 | 112 | 725x952 | 0.69 | 393120 | `4daa334aa6118c4a8fc668771a9cf0a1d6aadc2c9b9cd3e35702b50325577e3d` |
| `im_ppi__k1125__escaneado_d4.png` | im_ppi | escaneado_d4 | ×1.125 | 225 | 1456x1931 | 2.812 | 1262467 | `9a92b2ae40e8c0d482ee9fa6b0b73417e154ee2574d9a6f5f333dd8f1c953c82` |
| `im_ppi__k1125__escaneado_d4c.png` | im_ppi | escaneado_d4c | ×1.125 | 225 | 1456x1951 | 2.841 | 1231183 | `7d8f7ca2781f0f3317f9995c12f2829341862d1368b4100df839308b2aa39880` |
| `im_ppi__k1125__escaneado_d4e.png` | im_ppi | escaneado_d4e | ×1.125 | 225 | 1456x1931 | 2.812 | 1238947 | `01ad31289553f10068084404f7fe998cb36fb44fb6b9331a1072eeb954f6d2a0` |
| `im_ppi__k1125__escaneado_d4f.png` | im_ppi | escaneado_d4f | ×1.125 | 270 | 1746x2340 | 4.086 | 1758034 | `a4feec98c6edda7c42c63d7099886b0cf515a3e44227ec96ce0686a7713e4a0f` |
| `im_ppi__k1250__escaneado_d2.png` | im_ppi | escaneado_d2 | ×1.25 | 125 | 809x1063 | 0.86 | 366097 | `97f57d99698a4d63d8d138034447141f1e15418189dd20e6ec6818448c5f748f` |
| `im_ppi__k1250__escaneado_d3.png` | im_ppi | escaneado_d3 | ×1.25 | 125 | 809x1063 | 0.86 | 414307 | `e401111429e0a64a18e8b874bd95ceb8006fb99a921c1f27e847b7cb916cdea7` |
| `im_ppi__k1250__escaneado_d4.png` | im_ppi | escaneado_d4 | ×1.25 | 250 | 1617x2145 | 3.468 | 1338347 | `bc38b11ae27f3c02046fc73c01595bea1473b0d1b86833e1bc794f061f7971de` |
| `im_ppi__k1250__escaneado_d4c.png` | im_ppi | escaneado_d4c | ×1.25 | 250 | 1617x2167 | 3.504 | 1306838 | `4306feec838f92d19ad9cb1d69084329c0958d8f71006c42de43fb4e1947bd2e` |
| `im_ppi__k1250__escaneado_d4e.png` | im_ppi | escaneado_d4e | ×1.25 | 250 | 1617x2145 | 3.468 | 1312131 | `ac9c2e2738a285137265a517413f59a19a954ca727fcfd389770b7e333470efb` |
| `im_ppi__k1250__escaneado_d4f.png` | im_ppi | escaneado_d4f | ×1.25 | 300 | 1940x2600 | 5.044 | 1869280 | `29e934dbd91a8f0238ab7f6b533861d167fd5bcab169d059de9b132a2239c222` |
| `im_ppi__k1400__escaneado_d2.png` | im_ppi | escaneado_d2 | ×1.4 | 140 | 906x1190 | 1.078 | 389306 | `acad460064009b923f025664f9dcfe492a6ff1eaf55667623295b6973fff6f53` |
| `im_ppi__k1400__escaneado_d3.png` | im_ppi | escaneado_d3 | ×1.4 | 140 | 906x1190 | 1.078 | 436391 | `e9e7ca8f5a863dc204af457c9d78437e1f010e729f9f159b4d210fc87c291a62` |
| `im_ppi__k1400__escaneado_d4.png` | im_ppi | escaneado_d4 | ×1.4 | 280 | 1812x2402 | 4.352 | 1441993 | `a0b0ee83d7b5d3c2f840c28edc5c98033eac2388060f1874b050254edc113694` |
| `im_ppi__k1400__escaneado_d4c.png` | im_ppi | escaneado_d4c | ×1.4 | 280 | 1812x2428 | 4.4 | 1405447 | `990dfd11ae5e1f1bd793a8594c1a71c3e45da4ff466cb806af68e5eaef2bd368` |
| `im_ppi__k1400__escaneado_d4e.png` | im_ppi | escaneado_d4e | ×1.4 | 280 | 1812x2402 | 4.352 | 1426060 | `a01814e8c4c99e86ebe4d20886d809f0bcde1b798d2f24ceb3e2e10934648469` |
| `im_ppi__k1400__escaneado_d4f.png` | im_ppi | escaneado_d4f | ×1.4 | 336 | 2173x2912 | 6.328 | 2015343 | `155c38d597a0af2a367b4fc06cb686574d534910ac4e2f90aefd96a5b8c98d38` |
| `im_ppi__k1500__escaneado_d2.png` | im_ppi | escaneado_d2 | ×1.5 | 150 | 970x1275 | 1.237 | 396259 | `4390e302952ae3d14b9e584d2d5fabea9863aab02264462b034694fa40b3a7b4` |
| `im_ppi__k1500__escaneado_d3.png` | im_ppi | escaneado_d3 | ×1.5 | 150 | 970x1275 | 1.237 | 447327 | `d439baabd31951d38ed406a91c6d816be1a95ea9c44154606a284b9a504eeabb` |
| `im_ppi__k1500__escaneado_d4.png` | im_ppi | escaneado_d4 | ×1.5 | 300 | 1941x2574 | 4.996 | 1442471 | `70f2985cb1f59ceffdf87fa33eefaeaa011250de4639c06ddc888b58450531fe` |
| `im_ppi__k1500__escaneado_d4c.png` | im_ppi | escaneado_d4c | ×1.5 | 300 | 1941x2601 | 5.049 | 1408487 | `11a8dc7f2704fdce0b5302e35170ef9dc49158fe694d2b8443f0fe9fca26fbd7` |
| `im_ppi__k1500__escaneado_d4e.png` | im_ppi | escaneado_d4e | ×1.5 | 300 | 1941x2574 | 4.996 | 1409603 | `a2e7b17fd4f43e184f531e21e2715c6e82c13bd8d975fbaeff4a5759f0ca44d7` |
| `im_ppi__k1500__escaneado_d4f.png` | im_ppi | escaneado_d4f | ×1.5 | 360 | 2328x3120 | 7.263 | 2011071 | `6bb1339d1e0178f935c8559074fe10e8d11496a4b5c84fa6aab37058fdab4a86` |
| `im_ppi__k1600__escaneado_d2.png` | im_ppi | escaneado_d2 | ×1.6 | 160 | 1035x1360 | 1.408 | 416002 | `b5c0de53f4a46bc755a4e1e32a69e64538b3dc02c7a3577e2605361be402e3f7` |
| `im_ppi__k1600__escaneado_d3.png` | im_ppi | escaneado_d3 | ×1.6 | 160 | 1035x1360 | 1.408 | 464948 | `d955924d03630b5a3708201a40cb14ae5695cb499d2abe98311d80740a91a38f` |
| `im_ppi__k1600__escaneado_d4.png` | im_ppi | escaneado_d4 | ×1.6 | 320 | 2070x2746 | 5.684 | 1537339 | `5adc5b05f5e202fe3aef0bb39b4c6e92a8470a96e905bad010b0d8526098c48d` |
| `im_ppi__k1600__escaneado_d4c.png` | im_ppi | escaneado_d4c | ×1.6 | 320 | 2070x2774 | 5.742 | 1501746 | `43ba5fabda232f4046835c4ec521f6f3ea63cfc53a4c17c12e09236d3ace4ce0` |
| `im_ppi__k1600__escaneado_d4e.png` | im_ppi | escaneado_d4e | ×1.6 | 320 | 2070x2746 | 5.684 | 1515035 | `231d507e1210820c88af0ed2850de4f7f9bf416d9de02baab6dffa3c0061bb8a` |
| `im_ppi__k1600__escaneado_d4f.png` | im_ppi | escaneado_d4f | ×1.6 | 384 | 2483x3328 | 8.263 | 2153158 | `5fb37dd7285403097bebe535fe10e1c575ebf5733dc291c59efa2b45369aa443` |
| `im_ppi__k1800__escaneado_d2.png` | im_ppi | escaneado_d2 | ×1.8 | 180 | 1165x1530 | 1.782 | 437255 | `7a3c8f8ccdf0f1e3a0f2383cb29814c0bdab83e6e15d0f819c7e6f731c13ab1f` |
| `im_ppi__k1800__escaneado_d3.png` | im_ppi | escaneado_d3 | ×1.8 | 180 | 1165x1530 | 1.782 | 485234 | `4c5517ff91c315d80548e8f9cdc3c1b8b8e5a4c9d6fd8baeb70ac8cafed5cf6e` |
| `im_ppi__k1800__escaneado_d4.png` | im_ppi | escaneado_d4 | ×1.8 | 360 | 2329x3089 | 7.194 | 1612308 | `511764cbcc9fed5f8b10c245e0940812c056920faef72cce58c5268f3aa58b45` |
| `im_ppi__k1800__escaneado_d4c.png` | im_ppi | escaneado_d4c | ×1.8 | 360 | 2329x3121 | 7.269 | 1576364 | `3e36c567bb84d14285810d2e50d0de463461b3e1e91f923ad19de0034cc1c264` |
| `im_ppi__k1800__escaneado_d4e.png` | im_ppi | escaneado_d4e | ×1.8 | 360 | 2329x3089 | 7.194 | 1590876 | `0b760db3acd90f624f39a546d124804a5a95aee47f51d6f04e8381178687f3f5` |
| `im_sincs__k1000__escaneado_d2.png` | im_sincs | escaneado_d2 | ×1 | 100 | 647x850 | 0.55 | 319026 | `61c2a1f672cfe2f60aa944de8585ee024cdf8a3858fba79d4a06435b51566952` |
| `im_sincs__k1000__escaneado_d3.png` | im_sincs | escaneado_d3 | ×1 | 100 | 647x850 | 0.55 | 364163 | `f95782062d5a57506d73c3c97dd422ccd11fa216096a8ae9707c367bbfd56ccf` |
| `im_sincs__k1000__escaneado_d4.png` | im_sincs | escaneado_d4 | ×1 | 200 | 1294x1716 | 2.221 | 1172574 | `d53d50a3c929e7c99df6bb19b02b4f2b61f2cc786bf15dfe86a1272aaad94bc7` |
| `im_sincs__k1000__escaneado_d4c.png` | im_sincs | escaneado_d4c | ×1 | 200 | 1294x1734 | 2.244 | 1141642 | `1345a1aa9ab8b7fa7233f40911409d937a10e7413335e36f1d81f482e37231ca` |
| `im_sincs__k1000__escaneado_d4e.png` | im_sincs | escaneado_d4e | ×1 | 200 | 1294x1716 | 2.221 | 1153613 | `bcd5af209dda7034b9e7a8a301ae0e8d80fe270314c985abc0f0831fa46a5b27` |
| `im_sincs__k1000__escaneado_d4f.png` | im_sincs | escaneado_d4f | ×1 | 240 | 1552x2080 | 3.228 | 1635825 | `ce1f7791bcd32728b22049aea64b7f8e50173e7078703decf58452a579971cd4` |

## 3. Los ficheros que SÍ se versionan (texto)

| fichero | bytes | sha256 |
|---|---:|---|
| `d4_texto.py` | 2837 | `fa4b8d5d74980b29f0e640911c42ea07e59ca3910f364bd599407cb79c3cf011` |
| `manifiesto_psm.py` | 6430 | `90a5049ff0b600a3327ad577d7effcf71f02ec68fdf18dfe503be14a14e52742` |
| `ocr_eval_d4.py` | 6418 | `350354b261aef60b018b196204648c4c27effc0683f93a4fbcb5f2d551a30d82` |
| `ocr_eval_psm.py` | 2619 | `4c86a550a9523c9d55f9edad6ea03a2b675d5385130193c3f80b835e9243c894` |
| `raster_psm.py` | 7467 | `dc9126bb272c23a2b5f489dfde4724ebfcc3f35ffa4ef244159cf387947c48f8` |
| `run_bcd.sh` | 1254 | `83aa5c696c9fc3fd86aa8ed12abd6e669a930dcaca6962576de256cf8a01eed6` |
| `sonda_phys.py` | 5605 | `fdb35df05e2ad370881b2fef517453b040d388f9ac83c29574907172b2685b26` |
| `sonda_raster.py` | 5940 | `91db5199b1df7dc6a57536c282bb8148d575d4cefdeb8c42e2fb33adefea36e4` |
| `tablas.md` | 21449 | `702400d8c7a67abf8988f6cc5551539adfd032e50deaa4484e754ec0fd772321` |
| `tablas_psm.py` | 19302 | `3cae72efbf699d6e5a2fa6fa87d86c3c56a4a13c9f048f9f5673f63befa26493` |
| `tess_psm.py` | 8159 | `73e545d87f227f64d593de0ca1790c93d32ca9701690339048ba2aa4731052b1` |

**Copias byte a byte, verificadas:** `ocr_eval_d4.py` y `d4_texto.py` tienen el mismo `sha256` que los originales de `bench/salidas-corpus-d4/`, y `ocr_eval_psm.py` el mismo que `bench/salidas-k-motor/ocr_eval_km.py`. `bench/scripts/ocr_eval.py` **no se ha abierto**.

Además, sin listar aquí por volumen: `json/` (resultados por celda y las dos sondas), `texto/` (la salida literal de OCR de cada celda) y `logs/` (el registro completo de cada tanda). Son **texto** y se versionan.
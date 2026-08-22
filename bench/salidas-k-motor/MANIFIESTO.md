# MANIFIESTO — `bench/salidas-k-motor/` (M1 / B13)

Las **44 rasterizaciones** y los ficheros intermedios **se han borrado**: son regenerables y pesaban 78,7 MB (`CLAUDE.md` §6). Aquí quedan su `sha256`, su tamaño y la orden exacta que los reproduce.

Lo que **sí** queda versionado: los `.py`, los `.sh`, `tablas.md`, `json/` (resultados), `texto/` (la salida literal de OCR de las 397 celdas) y `logs/`.


## 1. Cómo se regenera todo, de cero

```bash
cd D:/Work/research/FileX/bench/salidas-k-motor
# 1. las 44 rasterizaciones (4 documentos x 11 factores)
../../.venv-ai/Scripts/python.exe preparar_km.py \
    0.5,0.625,0.75,0.875,1.0,1.125,1.25,1.4,1.6,1.8 \
    escaneado_d3 escaneado_d4c patologico_escaneado escaneado_d4
../../.venv-ai/Scripts/python.exe preparar_km.py 1.5 \
    escaneado_d3 escaneado_d4c patologico_escaneado escaneado_d4
# 2. las tandas, en este orden (todas las de GPU toman gpu_acquire/gpu_release)
bash run_a_png.sh          # PaddleOCR + RapidOCR x3
bash run_b_easy.sh         # EasyOCR
bash run_d_paddle_resto.sh # las 9 celdas que la guardia de VRAM omitio
bash run_e_resto.sh        # la celda de EasyOCR omitida
bash run_c_docling.sh      # docling defecto + docling R6
bash run_h_easy_resto.sh   # las 23 celdas de EasyOCR omitidas
bash run_f_tesseract.sh    # Tesseract --psm 3   (CPU, sin lock)
bash run_i_tess_psm.sh     # Tesseract --psm 11  (CPU, sin lock)
bash run_g_k150.sh         # el punto x1,50 en las nueve configuraciones
# 3. sonda de diagnostico y tablas
../../.venv-ai/Scripts/python.exe sonda_tess.py
python tablas_km.py
python manifiesto_km.py    # este fichero, y borra los binarios
```


## 2. Las 44 rasterizaciones (borradas)

Todas con **la misma orden** que `bench/salidas-corpus-d4/preparar_img.py` y `bench/salidas-ppp-norm/preparar_pn.py`, para que las cifras sean comparables con las celdas ya medidas:

```
"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe" -density <PPP> <corpus/pdf/DOC.pdf>[0] \
    -colorspace Gray -alpha remove -background white -flatten \
    img/k<FACTORx1000>__<DOC>.png
```

| fichero | documento | factor | ppp | píxeles | bytes | sha256 |
|---|---|---:|---:|---:|---:|---|
| `k0500__escaneado_d3.png` | `escaneado_d3` | ×0.5 | 50 | 323×425 | 103689 | `b7b9f15c0ddd940e4270b81647d3d60fa8a506deeae2f7f14b0a06b9f973852c` |
| `k0500__escaneado_d4.png` | `escaneado_d4` | ×0.5 | 100 | 647×858 | 370313 | `243e5165cfbdfcdb36f42a7f9cc409920a4309c8a2b2195ea7710e703d015b15` |
| `k0500__escaneado_d4c.png` | `escaneado_d4c` | ×0.5 | 100 | 647×867 | 356774 | `31c51793ddc0fa5d56a92aa2f31078443c7cd5d3a96fe738070377e6fb4b660a` |
| `k0500__patologico_escaneado.png` | `patologico_escaneado` | ×0.5 | 100 | 647×896 | 1031747 | `8f316075227a28cb690f9fa80530d91fc1d202adc5ad22184caf1fd881b01207` |
| `k0625__escaneado_d3.png` | `escaneado_d3` | ×0.625 | 62 | 401×527 | 153779 | `5ed23f891ef0e247aa25d9ab1e2425697dc7bb94118f61874a552b5f6b459334` |
| `k0625__escaneado_d4.png` | `escaneado_d4` | ×0.625 | 125 | 809×1073 | 551597 | `6c6a5e343deccfd39521c8d2f196f63ea100f85a147b895a59a97c0852945c60` |
| `k0625__escaneado_d4c.png` | `escaneado_d4c` | ×0.625 | 125 | 809×1084 | 535665 | `5a139de875a0afeb18c5bdb9aa962adac37d179d9bfce349c5d1268710e83d4f` |
| `k0625__patologico_escaneado.png` | `patologico_escaneado` | ×0.625 | 125 | 809×1120 | 1582158 | `280c9722814f7446cb47adf1e79a62297e63d1be533da0971ae1db47670d0e05` |
| `k0750__escaneado_d3.png` | `escaneado_d3` | ×0.75 | 75 | 485×638 | 217118 | `3104bf111e0e8dfcef22bd97a4bcb2f49bda42e808ebbe431287d81cdb112902` |
| `k0750__escaneado_d4.png` | `escaneado_d4` | ×0.75 | 150 | 970×1287 | 755752 | `c6e53ab6017521bcbfad7abbbdcba5be03569eab1a5153398b5e5808d7afa261` |
| `k0750__escaneado_d4c.png` | `escaneado_d4c` | ×0.75 | 150 | 970×1300 | 714895 | `2dbbb6fe1eb9ccf6ee04f69d190e0ca08880979557d306695fecdf64f76c28d3` |
| `k0750__patologico_escaneado.png` | `patologico_escaneado` | ×0.75 | 150 | 970×1344 | 2265789 | `e1022a87e7cebac4e63817894ae3ff91061d47628b32261a2dd59e9815e81899` |
| `k0875__escaneado_d3.png` | `escaneado_d3` | ×0.875 | 88 | 569×748 | 289788 | `0485724eb5e0deebb2360ceb61e003f0aaee8f16254df4c12212eeaf0ec39431` |
| `k0875__escaneado_d4.png` | `escaneado_d4` | ×0.875 | 175 | 1132×1502 | 933249 | `6ed6f493da81954db0bf5105e54e5c9b06afdb599135764cb8f9ee8eddece782` |
| `k0875__escaneado_d4c.png` | `escaneado_d4c` | ×0.875 | 175 | 1132×1517 | 921522 | `ac74b4828075dbcedd407b54b3fc47327e20e5279ce40e5971c7fd7e66380bae` |
| `k0875__patologico_escaneado.png` | `patologico_escaneado` | ×0.875 | 175 | 1132×1568 | 3090321 | `6b884934f6084eb49618cc6613c034fe22e10194f0b1e07ef085a26893bac7b8` |
| `k1000__escaneado_d3.png` | `escaneado_d3` | ×1.0 | 100 | 647×850 | 364119 | `1a63ac11e063be911477d1803da718be4694d188a287f18dc24d116366e7e85c` |
| `k1000__escaneado_d4.png` | `escaneado_d4` | ×1.0 | 200 | 1294×1716 | 1172530 | `40411314e59f67778eb6e9d5aa1aa73edad6812703c12b27015b250686cdd821` |
| `k1000__escaneado_d4c.png` | `escaneado_d4c` | ×1.0 | 200 | 1294×1734 | 1141598 | `ec58c2ec478842bcaf4900e0a6252c8583e4aa2deb84e8cfd7fd8e43ec776ae7` |
| `k1000__patologico_escaneado.png` | `patologico_escaneado` | ×1.0 | 200 | 1294×1792 | 4016393 | `239a0d83a3311bc7a556946ef8f99f627dfdc71dfd374ac522c9a71aa07e7ab6` |
| `k1125__escaneado_d3.png` | `escaneado_d3` | ×1.125 | 112 | 725×952 | 393120 | `8f3bdd8e432bd58823d374c7b0bc8300c574653973f5bf4a6f7e12d0a8294da2` |
| `k1125__escaneado_d4.png` | `escaneado_d4` | ×1.125 | 225 | 1456×1931 | 1262467 | `9f577d555deb9b71e0ae93a47d505664b4a8e74a13cfe5fcf66218bdc9813add` |
| `k1125__escaneado_d4c.png` | `escaneado_d4c` | ×1.125 | 225 | 1456×1951 | 1231183 | `5c81145acac2c7356ebdb1f7de1dc360b36bcbf709c74978a20aed3277545f1c` |
| `k1125__patologico_escaneado.png` | `patologico_escaneado` | ×1.125 | 225 | 1456×2016 | 5054850 | `8edbe6ed57d5d00b72f54998f33b6f67b13781f374f2a13e87546468c6934b90` |
| `k1250__escaneado_d3.png` | `escaneado_d3` | ×1.25 | 125 | 809×1063 | 414307 | `d7245933e2ac5a4c418a6fd58ad96fc4a877ea36f0fef02b21da354831e910a2` |
| `k1250__escaneado_d4.png` | `escaneado_d4` | ×1.25 | 250 | 1617×2145 | 1338347 | `8ec60d3b7542b30b45b06c91bf891ab685644fbd59801e83c95e3b440fa233a9` |
| `k1250__escaneado_d4c.png` | `escaneado_d4c` | ×1.25 | 250 | 1617×2167 | 1306838 | `457a4d597ee2634fe33cc4bf0aa51919e46bf893aac6cd673aa7cec71705ea60` |
| `k1250__patologico_escaneado.png` | `patologico_escaneado` | ×1.25 | 250 | 1617×2240 | 5296386 | `97439eed4dc04e4ff2ed9e0d06e29c1fe421c0e91ad94660fded70e71645ae4d` |
| `k1400__escaneado_d3.png` | `escaneado_d3` | ×1.4 | 140 | 906×1190 | 436391 | `c78d199f172be9cfa152abf7d6e07b8f12264627a641bb1405ad533142497ca9` |
| `k1400__escaneado_d4.png` | `escaneado_d4` | ×1.4 | 280 | 1812×2402 | 1441993 | `0c09a95fbc9d2eb7957880d87fbd2ef2606e2b43f4d58548202e88d60bfafe95` |
| `k1400__escaneado_d4c.png` | `escaneado_d4c` | ×1.4 | 280 | 1812×2428 | 1405447 | `a3bc12689f53015e832e27ea479af60ca6d3373f622368852bdd9f7352c340cb` |
| `k1400__patologico_escaneado.png` | `patologico_escaneado` | ×1.4 | 280 | 1812×2509 | 5533080 | `66a96007b94f8359eb4dd32e1d20a93003d5a86908d6f96c52ae7a28f0ba4ef4` |
| `k1500__escaneado_d3.png` | `escaneado_d3` | ×1.5 | 150 | 970×1275 | 447327 | `0aa461958eb04c03b505c77cbfabbe4a408ad081e9495b2b8f01b39aade526a7` |
| `k1500__escaneado_d4.png` | `escaneado_d4` | ×1.5 | 300 | 1941×2574 | 1442471 | `a75438d952de916b4e8e770eb092af0730bfb025d6acf2fc4040f6305e9dd5c9` |
| `k1500__escaneado_d4c.png` | `escaneado_d4c` | ×1.5 | 300 | 1941×2601 | 1408487 | `4b7e89c33c05daf6c28c45a0174261df9bfb2ee8ecc434d9ac0949fcff82c371` |
| `k1500__patologico_escaneado.png` | `patologico_escaneado` | ×1.5 | 300 | 1941×2688 | 5648022 | `4e1c371a05e87e182cdc9c2819e36c4afbadc7d5c4968984b802ee0f606b67f2` |
| `k1600__escaneado_d3.png` | `escaneado_d3` | ×1.6 | 160 | 1035×1360 | 464948 | `09fcb38ddda3779202cdc7adfaf31c92a61dfbd30e9a105be597637e3cd2860d` |
| `k1600__escaneado_d4.png` | `escaneado_d4` | ×1.6 | 320 | 2070×2746 | 1537339 | `c6454c7b49ba685644e67354ec4b148b12e1d44e9789e814ff0c881069f3e275` |
| `k1600__escaneado_d4c.png` | `escaneado_d4c` | ×1.6 | 320 | 2070×2774 | 1501746 | `f5132f0dd1e428f03c95c0ac638c05840c75ea8fe5d6195a37aef5e3439f9fe3` |
| `k1600__patologico_escaneado.png` | `patologico_escaneado` | ×1.6 | 320 | 2070×2867 | 5739663 | `ada42e26aa36dd5c2a4ac296f913807be96bb4a9ea7a0dbe0200b85c91291df0` |
| `k1800__escaneado_d3.png` | `escaneado_d3` | ×1.8 | 180 | 1165×1530 | 485234 | `7be81b7c2d4a7eb89baf87e151ae31652d602a644e7250dc5cbd2224517f7759` |
| `k1800__escaneado_d4.png` | `escaneado_d4` | ×1.8 | 360 | 2329×3089 | 1612308 | `dcc9b65707a68d76e57dd84476e1623dfe32c2b2cb7282b4d7ae58d947257d79` |
| `k1800__escaneado_d4c.png` | `escaneado_d4c` | ×1.8 | 360 | 2329×3121 | 1576364 | `bc992594ab6ae653bcf9ff9ece7199f9335496aea42f907526b83222c834a657` |
| `k1800__patologico_escaneado.png` | `patologico_escaneado` | ×1.8 | 360 | 2329×3226 | 5824829 | `9721fd1b73c76eb8abfd082ba506cec70c444cfb7ede4a5fe8bc36aa2b80ee4b` |

## 3. Intermedios de la sonda de Tesseract (borrados)

Reproducibles con `sonda_tess.py`. La rasterización de Ghostscript es:

```
"C:\Program Files\gs\gs10.07.0\bin\gswin64c.exe" -dNOPAUSE -dBATCH -dSAFER -q -sDEVICE=pnggray -r<PPP> \
    -dFirstPage=1 -dLastPage=1 -sOutputFile=tmp/sonda_gs_<DOC>.png <PDF>
```

| fichero | bytes | sha256 |
|---|---:|---|
| `tmp/sonda_gs_escaneado_d3.png` | 367433 | `8aa0105b1360163d5c2e62564f876409963e11cf780e2400f2d204d692becc02` |
| `tmp/sonda_gs_escaneado_d4.png` | 1179035 | `99613281cc45f7a68f6d204a2bcd0df6af4c3884867eb73e76b445a65cf08a7e` |
| `tmp/sonda_gs_escaneado_d4c.png` | 1148678 | `b55e24e2695b75317f6180e8c2f279b4f20516e5bbccd29e623d539a59a2fcac` |
| `tmp/sonda_im_escaneado_d3.png` | 364119 | `f2b08905c97ab847ca8a982b9b7ac2ab98d42f7f77be7be9e76d031ccb53dc9c` |
| `tmp/sonda_im_escaneado_d4.png` | 1172530 | `dd46ea58a18a8273528b4c730ebba97b32093e21f4221ae772c45981ceeb894a` |
| `tmp/sonda_im_escaneado_d4c.png` | 1141598 | `0de4052d0ae08e6fdc036d5d6e2d5b9a25974b92f30f270f2272735324644692` |

## 4. Lo que se conserva

| directorio | qué es | ficheros |
|---|---|---:|
| `json/` | resultados de CER por celda, geometría y la sonda de Tesseract | 30 |
| `texto/` | la salida literal de OCR de cada celda | 397 |
| `logs/` | el registro completo de las nueve tandas | 29 |

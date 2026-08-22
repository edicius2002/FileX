# MANIFIESTO — `bench/salidas-aristas/`

Salidas del agente **E1 · Aristas nominales**. Informe: `bench/aristas-nominales.md`.

Generado el 2026-08-21.


## 1. Cómo se reproduce todo, en orden

```
cd D:\Work\research\FileX
python bench/salidas-aristas/_testigo.py antes-censo-semiaristas
python bench/salidas-aristas/_censo.py          # nivel 0 + poblacion (138.501)
python bench/salidas-aristas/_semi.py           # semiaristas de salida, 1a vuelta
python bench/salidas-aristas/_semi2.py          # semiaristas de salida, 2a vuelta
python bench/salidas-aristas/_semi_in.py        # semiaristas de entrada, 1a vuelta
python bench/salidas-aristas/_semi_in2.py       # semiaristas de entrada, correccion
python bench/salidas-aristas/_agrega.py         # contabilidad a nivel de arista
python bench/salidas-aristas/_muestra.py 500 100 20260821   # muestra estratificada
python bench/salidas-aristas/_analiza.py        # la cifra y su IC de Wilson
python bench/salidas-aristas/_extrapola.py      # los tres escenarios
python bench/salidas-aristas/_resumen_semi.py   # tabla exacta de semiaristas
python bench/salidas-aristas/_cuenta.py         # invocaciones y timeouts
python bench/salidas-aristas/c8_prepara.py      # C8 dentro de filex-convertx
python bench/salidas-aristas/_c8_verifica.py    # verificacion de las salidas de C8
python bench/salidas-aristas/_svg_comp.py       # comparacion de rasterizadores SVG
python bench/salidas-aristas/_testigo.py despues-todo
```

**Requisitos:** `ffmpeg`, `magick`, `gswin64c` en el PATH; Docker Desktop arrancado con `filex-convertx` levantado (para C8); `repos/orchestrators/{ConvertX,SnapOtter,gotenberg}` clonados. La semilla aleatoria `20260821` reproduce exactamente la misma muestra de 598 aristas.


## 2. Lo que se borró al terminar, y qué lo regenera

| Borrado | Tamaño | Orden exacta que lo reproduce |
|---|---:|---|
| `pool/  (229 semillas materializadas)` | 711 086 916 B | `python bench/salidas-aristas/_semi_in.py   (las regenera enteras)` |
| `aristas.json` | 5 759 520 B | `python bench/salidas-aristas/_censo.py` |
| `marco.json` | 899 446 B | `python bench/salidas-aristas/_agrega.py` |
| `tmp/ tmp2/ tmp3/ tmp4/ tmp5/` | ~9 MB | `salidas efimeras de cada sonda; ningun script las necesita despues` |
| `c8/out/out/v.tif` | 16 589 110 B | `docker exec filex-convertx vips copy /tmp/e1/in/tipico.png /tmp/e1/out/v.tif` |

> `pool/` era el 99,8 % del peso: 229 ficheros semilla, uno por formato materializable, incluido un `m.txt` de **103 MB** que es el volcado de píxeles con que ImageMagick representa un JPEG en su formato «TXT». Es exactamente el mismo artefacto que `fidelidad-caminos.md` §3 documenta en `pdf → txt`, encontrado por otra vía.


## 3. Inventario (97 ficheros, 1 229 038 bytes)

| Fichero | Bytes | sha256 | Orden |
|---|---:|---|---|
| `_agrega.py` | 3 836 | `c72b1365e40434bb550c5b777f17c6b0…` | instrumento, escrito a mano |
| `_analiza.py` | 4 173 | `946dc03eb2ded4b84b736352406e46f1…` | instrumento, escrito a mano |
| `_c8_verifica.py` | 4 452 | `5997415b9836ae59e9e32c83e1c19290…` | instrumento, escrito a mano |
| `_censo.py` | 10 531 | `ff900017580835ddbc62ba482bd96a7b…` | instrumento, escrito a mano |
| `_cuenta.py` | 1 299 | `d223dd46c9928df067a60aae16220273…` | instrumento, escrito a mano |
| `_extrapola.py` | 4 383 | `76e982bd6761bc095c714a08e2aa19d0…` | instrumento, escrito a mano |
| `_manifiesto.py` | 7 267 | `b6b5bfdcd9f21b2f51bb7769e87499de…` | instrumento, escrito a mano |
| `_muestra.py` | 10 416 | `a7650f475ab9630b16ac705948232181…` | instrumento, escrito a mano |
| `_resumen_semi.py` | 1 656 | `5eba49cd7c5d2e7646553289c710348b…` | instrumento, escrito a mano |
| `_semi.py` | 7 459 | `e1749943c2bbd80d7bfc195281212995…` | instrumento, escrito a mano |
| `_semi2.py` | 4 133 | `4f3e4ff237c33b688d22d54e8545f4bd…` | instrumento, escrito a mano |
| `_semi_in.py` | 5 574 | `dc43133829dc83b6d58efd178299313a…` | instrumento, escrito a mano |
| `_semi_in2.py` | 3 413 | `3dc9eb61350366b7f3a2885a10c2c647…` | instrumento, escrito a mano |
| `_svg_comp.py` | 2 046 | `c2d76e99dd5f81010bc667b0d2d4021a…` | instrumento, escrito a mano |
| `_testigo.py` | 1 291 | `a7aaa5db9d0e8d389efb654908105068…` | instrumento, escrito a mano |
| `agregado.json` | 127 | `ac1c76605dac192309def23132b00f79…` | python bench/salidas-aristas/_agrega.py |
| `c8/c8_dentro.sh` | 3 829 | `7b08b479cbcff5e8a30f43c9736d76b3…` | instrumento, escrito a mano |
| `c8/in/e1.svg` | 649 | `6d9a3d94831a7ba87ebd1c78826bf0f6…` | python bench/salidas-aristas/c8_prepara.py  (copia de bench/salidas-fidelidad/entradas/ y corpus/) |
| `c8/in/entrada.csv` | 189 | `273c770b8c363b3d1ee20b4cbdff6d1d…` | python bench/salidas-aristas/c8_prepara.py  (copia de bench/salidas-fidelidad/entradas/ y corpus/) |
| `c8/in/entrada.docx` | 1 354 | `d74e7fceff4a80cb9aee6cd3611cb712…` | python bench/salidas-aristas/c8_prepara.py  (copia de bench/salidas-fidelidad/entradas/ y corpus/) |
| `c8/in/entrada.epub` | 1 685 | `918e7022ef5627819117b828271c120c…` | python bench/salidas-aristas/c8_prepara.py  (copia de bench/salidas-fidelidad/entradas/ y corpus/) |
| `c8/in/entrada.html` | 733 | `4c1d99ca350fff21760f8a0b639c3c6e…` | python bench/salidas-aristas/c8_prepara.py  (copia de bench/salidas-fidelidad/entradas/ y corpus/) |
| `c8/in/entrada.md` | 518 | `84f5f085a6f5f6dd2c27015089fc1a9b…` | python bench/salidas-aristas/c8_prepara.py  (copia de bench/salidas-fidelidad/entradas/ y corpus/) |
| `c8/in/entrada.odt` | 1 097 | `fc0587fd3a6c196a56c4cf8559589e39…` | python bench/salidas-aristas/c8_prepara.py  (copia de bench/salidas-fidelidad/entradas/ y corpus/) |
| `c8/in/entrada.rtf` | 534 | `a80c01df4e380cd60bf9b7a6eb3ff372…` | python bench/salidas-aristas/c8_prepara.py  (copia de bench/salidas-fidelidad/entradas/ y corpus/) |
| `c8/in/entrada.txt` | 385 | `f10940d617738e02ebdb89364cba05f3…` | python bench/salidas-aristas/c8_prepara.py  (copia de bench/salidas-fidelidad/entradas/ y corpus/) |
| `c8/in/entrada.xlsx` | 1 719 | `b0cb834f224163d1939075daa3abfd01…` | python bench/salidas-aristas/c8_prepara.py  (copia de bench/salidas-fidelidad/entradas/ y corpus/) |
| `c8/in/tipico.png` | 42 855 | `e645f85a6eec4e4d50f29f6b5336cf49…` | python bench/salidas-aristas/c8_prepara.py  (copia de bench/salidas-fidelidad/entradas/ y corpus/) |
| `c8/in/tipico_texto.pdf` | 3 219 | `a99692f0985e6f8ae9ed0d3b1bccbc99…` | python bench/salidas-aristas/c8_prepara.py  (copia de bench/salidas-fidelidad/entradas/ y corpus/) |
| `c8/out/out/c_azw3.epub` | 23 712 | `229903d8cc454fa6921d808680b8a332…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/c_epub.azw3` | 11 706 | `721db72457c3bed9d747630b7e283c9b…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/c_epub.docx` | 4 480 | `b98bf97a51d257cc307857a80839057e…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/c_epub.mobi` | 10 196 | `17dbf5ccac0775b8c83eb18280a8de89…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/c_epub.pdf` | 26 817 | `4a002e824d06da87da1a87538a776ec9…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/c_epub.pdf.txt` | 587 | `fac0a1db08c3e8029cb6615690d36fd5…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/c_mobi.epub` | 20 975 | `36e12f779cdf9a85729ca47da7a13591…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/d/entrada.odt` | 13 561 | `21d5470af7dd06a12c4b009ed05810df…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/entrada.pdf` | 22 840 | `838246a36a2cd00f43274151293c3aea…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/entrada.pdf.txt` | 601 | `4b4723eb282c40d7f1f0d6d871711f10…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/o/entrada.pdf` | 31 996 | `f0a840983bce6c44cc19376c16888a63…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/o/entrada.pdf.txt` | 579 | `9af2cc69e57154a479a7ae0cb854c77c…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/p/tipico_texto.docx` | 6 162 | `e8923de89e8ea4ec7c99d62a3e33cc19…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/p_docx.md` | 566 | `9b4bb779f5b8e7c658683b525a6917a3…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/p_docx.pdf` | 8 165 | `658a4727b6aa2ff8537490dc7745b13f…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/p_docx.pdf.txt` | 964 | `b2da85953c57c5138d15e36222df30f1…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/p_docx.rtf` | 1 481 | `1830031f5f3995a7130b5443a571eeba…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/p_epub.md` | 585 | `b1d024c7b12e2b8011da278df79bd970…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/p_html.docx` | 10 880 | `542f31c965376c74cd49b83f89bad35f…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/p_md.docx` | 10 860 | `4baab29e08f75f49f0792be05ad9cbbd…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/p_md.epub` | 5 273 | `98a2ed699a71d40d2472117a29966af3…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/p_md.html` | 695 | `3ddc9beacdfdd021d4eec5fdc740ab90…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/s_ink.pdf` | 17 818 | `f95b72b1e0e0df1ae05b97912e2a6948…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/s_ink.pdf.txt` | 78 | `5a2852130fc862f4d4cef3fe58205163…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/s_ink.png` | 13 456 | `96819da0c7b7bcffe3cdb978a26ec93d…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/s_resvg.png` | 8 973 | `ab4decb4557bd757010405bb1ad012f9…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/v.jpg` | 61 126 | `446e3cbd6f7980572e3cd9bd20e344b7…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/v.webp` | 13 194 | `6d5d6625fc22917dc22faa724e77b72c…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/x/entrada.pdf` | 20 983 | `61f310036e38bfb7f5406ed7ae1b1269…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/out/x/entrada.pdf.txt` | 250 | `ab096ed3564a60ac88a0a92b19df10b9…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/out/s_magick_win.png` | 8 628 | `a1ecb7fb0688544591af5bc6494b8504…` | python bench/salidas-aristas/c8_prepara.py  (ver la línea de c8/resultado.tsv con su id) |
| `c8/ref.txt` | 189 | `be5a29a812723da83bf2290039328e9f…` | — |
| `c8/resultado.tsv` | 3 879 | `ad3f710863542e74dc8f2d00be1096f8…` | python bench/salidas-aristas/c8_prepara.py   (ejecuta c8_dentro.sh dentro de filex-convertx) |
| `c8/svg_comparacion.json` | 858 | `113e1f6bd3f8c2150c95847a6dc860b2…` | python bench/salidas-aristas/_svg_comp.py |
| `c8/verificado.json` | 5 496 | `529aeec603bfae96cdcb19793cb4747f…` | python bench/salidas-aristas/_c8_verifica.py |
| `c8_dentro.sh` | 3 829 | `7b08b479cbcff5e8a30f43c9736d76b3…` | instrumento, escrito a mano |
| `c8_prepara.py` | 2 502 | `665e63d24b45ff90bf36a082e70f0d65…` | instrumento, escrito a mano |
| `censo.json` | 4 065 | `66542fc43c1b586929ca450b8d396762…` | python bench/salidas-aristas/_censo.py |
| `escenarios.json` | 198 | `4638c565ab0f8be6d30611bbc4c67b33…` | python bench/salidas-aristas/_extrapola.py |
| `fuga/t.mpd` | 1 234 | `ec1d118f6c4c2a801da0a124c12a5b51…` | ffmpeg -nostdin -y -i corpus/video/trivial.mp4 bench/salidas-aristas/fuga/t.mpd   (deja init-stream0.m4s y chunk-stream0-00001.m4s EN EL CWD) |
| `fuga/t.shtml` | 121 | `211b9d7cb0691dae187366733a49e4fd…` | magick corpus/imagen/trivial.png -auto-orient bench/salidas-aristas/fuga/t.shtml |
| `fuga/u.html` | 506 | `5f54f961caae26e9b4d31029b315955e…` | magick corpus/imagen/trivial.png -auto-orient bench/salidas-aristas/fuga/u.html   (deja u.png junto al destino y u_map.shtml EN EL CWD) |
| `fuga/u.map` | 4 102 | `656d688792c6661764e9ce9a1b1c74a7…` | magick corpus/imagen/trivial.png -auto-orient bench/salidas-aristas/fuga/u.map |
| `fuga/u.png` | 329 | `7d7e470f58463a2d4eefb458854becf4…` | ídem: segundo fichero de salida de la misma orden |
| `fuga/u.shtml` | 121 | `f38bc5d23f3fe417070163f3095cc5cc…` | magick corpus/imagen/trivial.png -auto-orient bench/salidas-aristas/fuga/u.shtml |
| `fuga/u_map.shtml` | 98 | `8a05eeda904dfdb528a71bc05566404b…` | ídem: escrito en el CWD, no en el destino; movido aquí a mano |
| `inventario_convertx.sh` | 388 | `cb825b4a3d1cf548352931320cf92998…` | instrumento, escrito a mano |
| `log-agregado.txt` | 386 | `346f2f3ca33575a74883cc625c80f40b…` | salida por consola del script homónimo, redirigida con Tee-Object |
| `log-analisis.txt` | 1 885 | `b6b19a1ccfb987cdfaca30db9375d6bc…` | salida por consola del script homónimo, redirigida con Tee-Object |
| `log-c8-verif.txt` | 2 480 | `a2aa01814e8042c26d86f1403f0106b9…` | salida por consola del script homónimo, redirigida con Tee-Object |
| `log-c8.txt` | 74 | `a3a05174371031da088202c92d0d1f64…` | salida por consola del script homónimo, redirigida con Tee-Object |
| `log-cuenta.txt` | 370 | `17a86e8986f0f32c092b4ab150a396df…` | salida por consola del script homónimo, redirigida con Tee-Object |
| `log-escenarios.txt` | 602 | `e7e93580664718bb6fd6a5765a0ec108…` | salida por consola del script homónimo, redirigida con Tee-Object |
| `log-muestra.txt` | 1 602 | `9fcb24805193b32caf6e8c412094b5aa…` | salida por consola del script homónimo, redirigida con Tee-Object |
| `log-resumen-semi.txt` | 873 | `eba39b10d41ec98b1b3ca8f8dccdf93e…` | salida por consola del script homónimo, redirigida con Tee-Object |
| `log-semi-entrada.txt` | 461 | `1933e575f86b42a5adf021ee86dcc1a4…` | salida por consola del script homónimo, redirigida con Tee-Object |
| `log-semi-entrada2.txt` | 5 076 | `c96fce45e055e412c5fa5427896795b8…` | salida por consola del script homónimo, redirigida con Tee-Object |
| `log-semi-salida.txt` | 760 | `0731dbbcf8dedcec2eb5d893bdb8f80c…` | salida por consola del script homónimo, redirigida con Tee-Object |
| `log-semi-salida2.txt` | 1 975 | `e56d623316da08d21ea2c05ae3713bc5…` | salida por consola del script homónimo, redirigida con Tee-Object |
| `log-svg.txt` | 564 | `61ecb6760b9d8591f19b9a8973ba5433…` | salida por consola del script homónimo, redirigida con Tee-Object |
| `muestra.json` | 247 007 | `6a22f7f5da5c776874a42adf885d7f9a…` | python bench/salidas-aristas/_muestra.py 500 100 20260821 |
| `resultado.json` | 642 | `eb07b577fcd8dce416d95581e37469ee…` | python bench/salidas-aristas/_analiza.py |
| `semi_entrada.json` | 117 217 | `c448947416e2b0f9cea3987b3b193814…` | python bench/salidas-aristas/_semi_in.py |
| `semi_entrada2.json` | 26 829 | `ba5f4373dc1dcaec5a84cf2a585e8e73…` | python bench/salidas-aristas/_semi_in2.py |
| `semi_salida.json` | 117 048 | `91c5ea9ae433fb32968134abf64919e5…` | python bench/salidas-aristas/_semi.py |
| `semi_salida2.json` | 48 085 | `f5609552dc331efb4cdaa373d334bea2…` | python bench/salidas-aristas/_semi2.py |
| `testigo.jsonl` | 885 | `11a00bdb84421baaaffa04eefb12bbd2…` | python bench/salidas-aristas/_testigo.py <etiqueta>   (una linea por tanda) |
| `verificador_congelado.py` | 137 293 | `c753ca43aa3e5e24eeac5f9c10228c58…` | Copy-Item bench/scripts/verificador.py bench/salidas-aristas/verificador_congelado.py   (congelado el 21/08 07:24; V1 lo edita en paralelo) |

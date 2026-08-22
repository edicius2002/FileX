# MANIFIESTO — `bench/salidas-sondeo-doc/` (agente S3)

**Las salidas binarias están BORRADAS** (`CLAUDE.md` §6). Aquí queda de
cada una el tamaño, el `sha256` y la orden que la reproduce.

Lo que SÍ se versiona de este directorio: los arneses (`_*.py`), los
`.json` de resultados, los `.log` y **las tres semillas escritas a mano**
(`entradas/entrada.csv`, `.svg`, `.tex`), que son fuente y no salida.

> **AVISO: los `sha256` de las salidas de CALIBRE no reproducen — MEDIDO**
> (`bench/sondeo-documental.md` §5). Con n=3, `mobi→epub` dio **tres
> tamaños distintos** (18 333 / 24 270 / 30 876 B) y `epub→pdf` dio el
> mismo tamaño con **tres `sha256` distintos**. El motivo está al miembro:
> de los 11 ficheros del EPUB, **8 son idénticos byte a byte —incluido el
> texto—** y cambian `content.opf`, `toc.ncx` (UUID) y `cover_image.jpg`,
> que es una **portada generada**. Las salidas de **pandoc sí son byte a
> byte reproducibles** (`md→html`: un solo `sha` en 3 ejecuciones).
> **Para una salida de Calibre, lo que hay que comparar es el `sha256` del
> miembro que lleva el texto, no el del fichero.**

**Reproducir, en este orden** (Docker levantado, imagen `filex-c13`):

```
python bench/salidas-sondeo-doc/_sonda23.py       # 23 aristas, ~190 s
python bench/salidas-sondeo-doc/_sonda_p5.py      # pendiente 5, ~150 s
python bench/salidas-sondeo-doc/_d2.py            # defectos del verificador + ida y vuelta
python bench/salidas-sondeo-doc/_repro.py         # reproducibilidad, n=3
python bench/salidas-sondeo-doc/_tabla_sondeo.py  # escribe filex/sondeo/doc_*.json
python bench/salidas-sondeo-doc/_manifiesto.py
```

`_sonda23.py` fabrica las semillas que le falten (`entrada.mobi` y
`entrada.azw3`, desde `epub→mobi`/`epub→azw3`, C03/C04 de K1);
`_sonda_p5.py` fabrica `entrada.xlsx` (Q01) y `entrada.pptx` (Q02). Las
siete semillas de texto se REUSAN de `bench/salidas-hito5/entradas/` sin
copiarlas.

| fichero | bytes | sha256 | reproduce |
|---|---:|---|---|
| `out/S01_libreoffice_rtf2odt.odt` | 14176 | `a27bee30320014e9a12de597781226ad…` | `_sonda23.py --solo S01` |
| `out/S02_libreoffice_rtf2docx.docx` | 5293 | `7a1e4a2fc7fc4808e3205ba1ec91f08d…` | `_sonda23.py --solo S02` |
| `out/S03_libreoffice_html2odt.odt` | 8125 | `0f1e293b951d89df6a438e2f2196fbbb…` | `_sonda23.py --solo S03` |
| `out/S04_libreoffice_txt2odt.odt` | 12125 | `9afa110b714df6d26aa31a7ca153823c…` | `_sonda23.py --solo S04` |
| `out/S05_libreoffice_odt2html.html` | 2476 | `a9e64ee428e3c21e6898265973189aca…` | `_sonda23.py --solo S05` |
| `out/S06_libreoffice_docx2rtf.rtf` | 8213 | `6625c6c16010f425ff6637d215460650…` | `_sonda23.py --solo S06` |
| `out/S07_pandoc_html2epub.epub` | 5286 | `b75ab90bc831e8907b4670873998ba7b…` | `_sonda23.py --solo S07` |
| `out/S08_pandoc_html2odt.odt` | 7286 | `727c7a05f6b8edd6c4f7a16ef136e695…` | `_sonda23.py --solo S08` |
| `out/S09_pandoc_html2rtf.rtf` | 1756 | `a89e37f5d3731e7d1197188a1141d560…` | `_sonda23.py --solo S09` |
| `out/S10_pandoc_docx2odt.odt` | 7203 | `907591cc1fed3358bacc41aaa6b1c5ef…` | `_sonda23.py --solo S10` |
| `out/S11_pandoc_epub2docx.docx` | 10993 | `8e41d4fcd143c1f4444ccd434f64fabf…` | `_sonda23.py --solo S11` |
| `out/S12_pandoc_epub2txt.txt` | 566 | `9b4bb779f5b8e7c658683b525a6917a3…` | `_sonda23.py --solo S12` |
| `out/S13_pandoc_rtf2md.md` | 471 | `b7f1b3f7c07d311650cf613a2f6af4eb…` | `_sonda23.py --solo S13` |
| `out/S14_pandoc_rtf2html.html` | 4324 | `d190a684c87c1fafcfb383fcb03da86b…` | `_sonda23.py --solo S14` |
| `out/S15_pandoc_md2rtf.rtf` | 1700 | `a70efd2528eca365c6b05c2343be95dc…` | `_sonda23.py --solo S15` |
| `out/S16_calibre_mobi2epub.epub` | 18336 | `b571c7ef0d33b1211fabb3cccc8624f8…` | `_sonda23.py --solo S16` |
| `out/S17_calibre_azw32epub.epub` | 18602 | `e0d59246990aacfc1d0faf20d50f9cd0…` | `_sonda23.py --solo S17` |
| `out/S18_calibre_mobi2pdf.pdf` | 31178 | `c7c351c96205ca6469579d17f8e9fedd…` | `_sonda23.py --solo S18` |
| `out/S19_calibre_azw32pdf.pdf` | 27387 | `40994d9aa95c63d0feaf8151e097c6c8…` | `_sonda23.py --solo S19` |
| `out/S20_calibre_txt2epub.epub` | 26406 | `5d5449b5eb4fe6fc2377df4d13313158…` | `_sonda23.py --solo S20` |
| `out/S21_calibre_md2epub.epub` | 11851 | `132b5038bbe37076b8ae10c34bae088e…` | `_sonda23.py --solo S21` |
| `out/S22_calibre_epub2epub.epub` | 20209 | `fcf1abfd73c54198149fa473926ccd81…` | `_sonda23.py --solo S22` |
| `out/S23_calibre_mobi2azw3.azw3` | 12614 | `ec137a87ba799b5b447128fc7aed4b79…` | `_sonda23.py --solo S23` |
| `out-p5/Q01_csv2xlsx.xlsx` | 5790 | `8aa0def3019877091e2bbb23bb6f20b4…` | `_sonda_p5.py --solo Q01` |
| `out-p5/Q02_md2pptx.pptx` | 28170 | `a3d387a1ecec95827ee490a1b0b0cfed…` | `_sonda_p5.py --solo Q02` |
| `out-p5/Q03_xlsx2pdf.pdf` | 27403 | `db65a4d2b81c86a67f473611321b76b7…` | `_sonda_p5.py --solo Q03` |
| `out-p5/Q04_xlsx2csv.csv` | 109 | `c19d31f488b5f0baabc98079ae3682a3…` | `_sonda_p5.py --solo Q04` |
| `out-p5/Q05_xlsx2html.html` | 2902 | `f33778451253dfcddb23821850d2feb7…` | `_sonda_p5.py --solo Q05` |
| `out-p5/Q06_csv2pdf.pdf` | 20944 | `45a0ac9cd9bcf0a06a938f15787ecad3…` | `_sonda_p5.py --solo Q06` |
| `out-p5/Q07_pptx2pdf.pdf` | 24534 | `79aacf055343586c033a5244820b7f34…` | `_sonda_p5.py --solo Q07` |
| `out-p5/Q08_pptx2odp.odp` | 32669 | `fe87f505c7c0699d8ced2566e3b70c98…` | `_sonda_p5.py --solo Q08` |
| `out-p5/Q09_pptx2png.png` | 50462 | `4d587e300819a90e511cc533b7268412…` | `_sonda_p5.py --solo Q09` |
| `out-p5/Q10_svg2pdf.pdf` | 12500 | `b1305218034972b7119fc39b3c7d0e17…` | `_sonda_p5.py --solo Q10` |
| `out-p5/Q11_svg2png.png` | 9081 | `a234bdbc0ad1652dc7b6ac57d86a7308…` | `_sonda_p5.py --solo Q11` |
| `out-p5/Q12_md2tex.tex` | 2748 | `2a2b2b9a26cd3095cf9d15f071f6360c…` | `_sonda_p5.py --solo Q12` |
| `out-p5/Q13_docx2tex.tex` | 2698 | `3669682677bcf4a7a84d848ccbb9872d…` | `_sonda_p5.py --solo Q13` |
| `out-p5/Q14_tex2docx.docx` | 10771 | `79523e452120467e3fbb927db82430b6…` | `_sonda_p5.py --solo Q14` |
| `out-p5/Q15_tex2html.html` | 4651 | `2196e8bd81dda130b4c4a48a08f1c736…` | `_sonda_p5.py --solo Q15` |
| `out-p5/Q16_tex2pdf.pdf` | 9754 | `5c56572121d1c1b3f0fb74336c47481b…` | `_sonda_p5.py --solo Q16` |
| `out-p5/Q17_pptx2md.md` | 549 | `5e9b6868661ba5e35d7005ad8e6ecdbd…` | `_sonda_p5.py --solo Q17` |
| `out-d2/R_libreoffice_odt2txt.txt` | 458 | `80d4fe7cad8d9eb77c3e759183640ca4…` | `_d2.py` |
| `out-d2/R_pandoc_md2txt.txt` | 535 | `e936439bd27a42ce93077fdd360f535a…` | `_d2.py` |
| `out-d2/R_pandoc_docx2md.md` | 566 | `9b4bb779f5b8e7c658683b525a6917a3…` | `_d2.py` |
| `out-d2/R_pandoc_epub2md.md` | 585 | `b1d024c7b12e2b8011da278df79bd970…` | `_d2.py` |
| `out-d2/R_pandoc_html2md.md` | 568 | `54f71421a0895bbe9776e905d7295183…` | `_d2.py` |
| `out-d2/R_calibre_epub2txt.txt` | 468 | `1f1069a7421942ba65474c77fe9293f9…` | `_d2.py` |
| `out-d2/R_pandoc_md2pdf.pdf` | 10370 | `4871b60d438bd95f15ce1a57a22a1936…` | `_d2.py` |
| `out-d2/R_pandoc_docx2pdf.pdf` | 8163 | `1636913b7d49a89cb6c973ab75402d5c…` | `_d2.py` |
| `out-d2/R_libreoffice_docx2pdf.pdf` | 22820 | `242ea9610ca6887b29325a344fa1a453…` | `_d2.py` |
| `out-d2/R_libreoffice_docx2html.html` | 2399 | `b2b2b31ae926929df1e620001124e3f7…` | `_d2.py` |
| `out-repro/calibre_mobi2epub_0.epub` | 18333 | `dcbf12e6db28ef66e2afbd2d192be735…` | `_repro.py` (**no reproducible**) |
| `out-repro/calibre_mobi2epub_1.epub` | 30876 | `8753a096693ef0587f2453f46b7a1e14…` | `_repro.py` (**no reproducible**) |
| `out-repro/calibre_mobi2epub_2.epub` | 24270 | `4551fb33235b3015777c518c29568223…` | `_repro.py` (**no reproducible**) |
| `out-repro/calibre_epub2pdf_0.pdf` | 26817 | `a6b4a8819b61511b08ba5ac52cd21607…` | `_repro.py` (**no reproducible**) |
| `out-repro/calibre_epub2pdf_1.pdf` | 26817 | `59b976b5c2025f196b0f159923ade6cd…` | `_repro.py` (**no reproducible**) |
| `out-repro/calibre_epub2pdf_2.pdf` | 26817 | `4736aa96136ec70be042b73c67aabba6…` | `_repro.py` (**no reproducible**) |
| `out-repro/pandoc_md2html_0.html` | 4525 | `7d4c69233c6cce6999d120bc311a7da9…` | `_repro.py` (**no reproducible**) |
| `out-repro/pandoc_md2html_1.html` | 4525 | `7d4c69233c6cce6999d120bc311a7da9…` | `_repro.py` (**no reproducible**) |
| `out-repro/pandoc_md2html_2.html` | 4525 | `7d4c69233c6cce6999d120bc311a7da9…` | `_repro.py` (**no reproducible**) |

## Las órdenes exactas

* `sonda-p5.json` lleva el **`argv` literal** de cada caso, con el
  `docker run`, los dos `--mount` y el tope de dentro.
* `sonda23.json` **no lleva `argv` a propósito**: esas 23 conversiones
  las hace `FileX.convertir()`, y la orden la construye
  `filex.motor_contenedor._argv_docker`. Reproducirlas es llamar al
  núcleo, no copiar una línea.
* `d2.json` §A no invoca ningún motor: son tres ficheros escritos a mano
  pasados por `filex.contrato.verificar()`.


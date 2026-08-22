# MANIFIESTO — `bench/salidas-hito5/`

**Generado por `_manifiesto.py`. No se edita a mano.**

Las salidas binarias de este directorio **se han borrado**: son regenerables y el repositorio ya pagó una vez el error de versionarlas (986 MB de pack, 99,9 % binario). Lo que queda es esta tabla y los `.json` con las medidas.

## Cómo se reproduce todo

```
# 1. Docker Desktop arrancado y la imagen presente:
docker image inspect filex-c13 --format '{{.Id}}'
# 2. las 36 aristas candidatas (~400 s):
python bench/salidas-hito5/_sonda.py
# 3. las medianas de n=9 de las cuatro que deciden el hito (~500 s):
python bench/salidas-hito5/_medianas.py
# 4. las tablas de aristas que van en filex/motor_contenedor.py:
python bench/salidas-hito5/_tabla.py
# 5. la comparación de los dos caminos:
python bench/salidas-hito5/_camino.py
# 5b. que el tope DENTRO del contenedor no deja huérfanos:
python bench/salidas-hito5/_tope.py
# 6. este manifiesto:
python bench/salidas-hito5/_manifiesto.py
```

Cada invocación de la sonda es un `docker run` construido por `argv_docker()` y lanzado por `filex.invocacion.ejecutar()`, en un `DirectorioDeTrabajo` desechable que se censa antes de borrarse.

> **La sonda NO lleva el tope `timeout -k 5 N` dentro del contenedor, y el producto SÍ.** Está así a propósito: es el registro de lo que se midió, y lo que se midió incluye el fallo que ese tope arregla (`bench/hito5-documental.md` §4.4). Por eso las órdenes de esta tabla no coinciden con las que construye hoy `filex/motor_contenedor.py`.

## Entradas (SÍ se versionan: 23 KB de texto)

Copiadas de `bench/salidas-aristas/c8/in/`, que las generó el 21/08. Todas llevan el centinela `FILEXSENTINELA7743` y la tabla `AX-1 / BX-2 / CX-3`.

| fichero | bytes | sha256 |
|---|---:|---|
| `entrada.docx` | 1354 | `d74e7fceff4a80cb9aee6cd3611cb71207241ffd55a441c57e21e5fc2b72309d` |
| `entrada.epub` | 1685 | `918e7022ef5627819117b828271c120c4fa70d4d56f8fe5b05473a2671097c26` |
| `entrada.html` | 733 | `4c1d99ca350fff21760f8a0b639c3c6e8197840cc7ea1e2e371de0eadbe8c82c` |
| `entrada.md` | 518 | `84f5f085a6f5f6dd2c27015089fc1a9bf0111aa7203b11f964619cf1ac6dfeb3` |
| `entrada.odt` | 1097 | `fc0587fd3a6c196a56c4cf8559589e396500612193c9c792cbb6bd8b9a7be566` |
| `entrada.rtf` | 534 | `a80c01df4e380cd60bf9b7a6eb3ff3726d417b9964ca74a588672c2b78107db8` |
| `entrada.txt` | 385 | `f10940d617738e02ebdb89364cba05f385154c33b55b2a47e69c926b3c50113b` |

## Salidas de la sonda (BORRADAS — la tabla es el registro)

`orden` es lo que se ejecuta **dentro** del contenedor; el `docker run` que lo envuelve es idéntico para todas y está en `_sonda.py::argv_docker`.

| id | motor | arista | rc | ms | bytes | car. | centinela | sha256 | orden dentro del contenedor |
|---|---|---|---:|---:|---:|---:|:---:|---|---|
| C01 | calibre | `epub→pdf` | 0 | 17652 | 26817 | 456 | sí | `c87ee12163b17b65` | `ebook-convert /ent/salida.epub /trabajo/salida.pdf` |
| C02 | calibre | `epub→docx` | 0 | 7371 | 4483 | 574 | sí | `4c3f07aafc2ed55f` | `ebook-convert /ent/salida.epub /trabajo/salida.docx` |
| C03 | calibre | `epub→mobi` | 0 | 7836 | 10196 | 10192 | — | `2148c64f3e86dc23` | `ebook-convert /ent/salida.epub /trabajo/salida.mobi` |
| C04 | calibre | `epub→azw3` | 0 | 4997 | 11692 | 11683 | — | `8cbe0eee86b6e36b` | `ebook-convert /ent/salida.epub /trabajo/salida.azw3` |
| C05 | calibre | `epub→txt` | 0 | 4886 | 468 | 456 | sí | `1f1069a7421942ba` | `ebook-convert /ent/salida.epub /trabajo/salida.txt` |
| C06 | calibre | `epub→html` | 1 | 2073 | 0 | 0 | — | `—` | `ebook-convert /ent/salida.epub /trabajo/salida.html` |
| C07 | calibre | `docx→epub` | 0 | 7521 | 13579 | 558 | sí | `0a5be13739cb19e9` | `ebook-convert /ent/salida.docx /trabajo/salida.epub` |
| C08 | calibre | `html→epub` | 0 | 5330 | 21015 | 564 | sí | `868adce7ac3fd725` | `ebook-convert /ent/salida.html /trabajo/salida.epub` |
| C09 | calibre | `docx→pdf` | 0 | 10152 | 19896 | 456 | sí | `e63f2fd3fd9c08c7` | `ebook-convert /ent/salida.docx /trabajo/salida.pdf` |
| L01 | libreoffice | `docx→pdf` | 0 | 6339 | 22820 | 456 | sí | `807ca6e49a6d858a` | `soffice --headless --convert-to pdf --outdir /trabajo /ent/salida.docx` |
| L02 | libreoffice | `odt→pdf` | 0 | 4181 | 31976 | 456 | sí | `0d8adb20662a9701` | `soffice --headless --convert-to pdf --outdir /trabajo /ent/salida.odt` |
| L03 | libreoffice | `rtf→pdf` | 0 | 2494 | 21412 | 458 | sí | `d99971598e11d2a3` | `soffice --headless --convert-to pdf --outdir /trabajo /ent/salida.rtf` |
| L04 | libreoffice | `html→pdf` | 0 | 2167 | 32807 | 456 | sí | `6aaf5d00aa71226c` | `soffice --headless --convert-to pdf --outdir /trabajo /ent/salida.html` |
| L05 | libreoffice | `txt→pdf` | 0 | 2490 | 16940 | 383 | sí | `3f3aa25beb7504af` | `soffice --headless --convert-to pdf --outdir /trabajo /ent/salida.txt` |
| L06 | libreoffice | `docx→odt` | 0 | 3771 | 13562 | 1757 | sí | `5d9633f657f759a9` | `soffice --headless --convert-to odt --outdir /trabajo /ent/salida.docx` |
| L07 | libreoffice | `odt→docx` | 0 | 3492 | 6063 | 540 | sí | `0c0d1e913cfa7e42` | `soffice --headless --convert-to docx --outdir /trabajo /ent/salida.odt` |
| L08 | libreoffice | `docx→html` | 0 | 4474 | 2399 | 571 | sí | `b2b2b31ae926929d` | `soffice --headless --convert-to html --outdir /trabajo /ent/salida.docx` |
| L09 | libreoffice | `docx→png` | 0 | 5746 | 38798 | 0 | — | `7e4bb0c2864c4d20` | `soffice --headless --convert-to png --outdir /trabajo /ent/salida.docx` |
| L10 | libreoffice | `epub→pdf` | 1 | 7894 | 0 | 0 | — | `—` | `soffice --headless --convert-to pdf --outdir /trabajo /ent/salida.epub` |
| L11 | libreoffice | `docx→txt` | 1 | 240228 | 0 | 0 | — | `—` | `soffice --headless --convert-to txt:Text --outdir /trabajo /ent/salida.docx` |
| L12 | libreoffice | `odt→txt` | 0 | 10433 | 458 | 456 | sí | `80d4fe7cad8d9eb7` | `soffice --headless --convert-to txt:Text --outdir /trabajo /ent/salida.odt` |
| P01 | pandoc | `md→docx` | 0 | 4100 | 10861 | 586 | sí | `478702b518336cf7` | `pandoc /ent/salida.md -o /trabajo/salida.docx` |
| P02 | pandoc | `md→html` | 0 | 1407 | 4525 | 3131 | sí | `7d4c69233c6cce69` | `pandoc -s /ent/salida.md -o /trabajo/salida.html` |
| P03 | pandoc | `md→epub` | 0 | 1096 | 5276 | 523 | sí | `641bfde0eb444550` | `pandoc /ent/salida.md -o /trabajo/salida.epub` |
| P04 | pandoc | `docx→md` | 0 | 987 | 566 | 514 | sí | `9b4bb779f5b8e7c6` | `pandoc /ent/salida.docx -o /trabajo/salida.md` |
| P05 | pandoc | `docx→html` | 0 | 999 | 4487 | 3131 | sí | `f618673cac084894` | `pandoc -s /ent/salida.docx -o /trabajo/salida.html` |
| P06 | pandoc | `docx→rtf` | 0 | 895 | 1634 | 1632 | sí | `9045a7b88b8598c3` | `pandoc -s /ent/salida.docx -o /trabajo/salida.rtf` |
| P07 | pandoc | `html→docx` | 0 | 2288 | 10879 | 614 | sí | `bba2a0afec9181b2` | `pandoc /ent/salida.html -o /trabajo/salida.docx` |
| P08 | pandoc | `html→md` | 0 | 867 | 568 | 516 | sí | `54f71421a0895bbe` | `pandoc /ent/salida.html -o /trabajo/salida.md` |
| P09 | pandoc | `epub→md` | 0 | 9568 | 585 | 532 | sí | `b1d024c7b12e2b80` | `pandoc /ent/salida.epub -o /trabajo/salida.md` |
| P10 | pandoc | `epub→html` | 0 | 1494 | 4629 | 3152 | sí | `cf055a01032163a9` | `pandoc -s /ent/salida.epub -o /trabajo/salida.html` |
| P11 | pandoc | `md→pdf` | 0 | 12414 | 10370 | 456 | sí | `668ea341ed59c2af` | `pandoc /ent/salida.md --pdf-engine=xelatex -o /trabajo/salida.pdf` |
| P12 | pandoc | `docx→pdf` | 0 | 7242 | 8163 | 456 | sí | `2ac4d521b223c1d1` | `pandoc /ent/salida.docx --pdf-engine=xelatex -o /trabajo/salida.pdf` |
| P13 | pandoc | `md→odt` | 0 | 2517 | 7304 | 515 | sí | `8a5ff71ec968e18c` | `pandoc /ent/salida.md -o /trabajo/salida.odt` |
| P14 | pandoc | `docx→epub` | 0 | 856 | 5243 | 509 | sí | `1e4b3065499ec83e` | `pandoc /ent/salida.docx -o /trabajo/salida.epub` |
| P15 | pandoc | `md→txt` | 0 | 959 | 535 | 485 | sí | `e936439bd27a42ce` | `pandoc /ent/salida.md -t plain -o /trabajo/salida.txt` |

## Los dos caminos (`_camino.py`, salidas borradas)

| camino | ok | bytes | caracteres | centinela | contrato | sha256 |
|---|:---:|---:|---:|:---:|---|---|
| A · docx→pdf (LibreOffice) | sí | 22820 | 456 | sí | ok | `72b82e6852ffd443` |
| B · docx→png→pdf (LibreOffice + ImageMagick) | sí | 14851 | 0 | **no** | ok | `6db53c7063b69f6d` |

## Ficheros que SÍ se quedan

| fichero | qué es |
|---|---|
| `_sonda.py` | ejecuta las 36 aristas candidatas, una por directorio desechable, con censo |
| `_medianas.py` | medianas de n=9 con los dos testigos de ruido |
| `_tabla.py` | genera las tablas `_MEDIDAS`/`_MUERTAS` de `filex/motor_contenedor.py` |
| `_camino.py` | los dos caminos `docx→pdf`, por el núcleo |
| `_tope.py` | reproduce el cuelgue y comprueba que no queda contenedor vivo |
| `_manifiesto.py` | esto |
| `sonda.json` | rc, ms, bytes, sha256, censo del punto 5 y centinela de las 36 |
| `sonda-txt.json` | las tres reejecuciones del cuelgue de `docx→txt` |
| `medianas.json` | las cuatro medianas de n=9 y los testigos |
| `camino.json` | la comparación de los dos caminos |
| `tope.json` | el `rc=124` del tope de dentro y el censo de huérfanos |
| `entradas/` | 23 KB de documentos con centinela |


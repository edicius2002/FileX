# MANIFIESTO — `bench/salidas-rasteriza-declaradas/`

worker14, carril `edicius2002/filex-rasteriza-declaradas`, ronda 13.
Informe completo: **`bench/rasteriza-declaradas.md`**.

Cierra el defecto de `filex/motor_contenedor.py`: `_DECLARADAS` era una tupla de
pares y `_aristas()` construía las `Arista` sin pasar `rasteriza=`, así que toda
arista declarada nacía con el `default=False` de `grafo.Arista` **mintiera o
no** — y `sondeo.aplicar()` conserva `rasteriza` de la arista que ya existe, así
que medirla no lo arreglaba. Ahora es un `dict` `{(origen, destino): rasteriza}`
con el valor obligatorio, y `pptx→png` y `svg→png` entran al grafo con
`rasteriza=True`.

## Qué se versiona

| fichero | qué es |
|---|---|
| `_resondeo40.py` | el arnés. Copia de la mecánica de `bench/salidas-aristas-documentales-cierre/_resondeo55.py` (worker7) al propio directorio, no lo edita (`CLAUDE.md` §1). Llama a `filex.nucleo.FileX.convertir()` de verdad: `motor.orden()`, `invocacion.ejecutar()` contra Docker, contrato de cinco puntos y censo del punto 5 |
| `_sellar.py` | reconstruye los tres `filex/sondeo/doc_*.json` desde `resondeo40.json`, con la huella nueva y la `nota_huella` que distingue RESONDEO de resello |
| `resondeo40.json` | las 40 medidas crudas: `rc`, `ms`, bytes, `sha256`, caracteres, centinela, veredicto, cobertura, sobrantes, hallazgos, `rasteriza_declarado` y `rasteriza_medido` |
| `contrafactual.json` | el barrido de §5.2 del informe: qué pierde el planificador si las dos aristas nuevas mienten |
| `planificador_despues.json` | los pares que eligen y los que rechazan una ruta que rasteriza, tras el cambio |
| `determinismo_epub.json` | las 4 corridas de `calibre epub→epub` y qué entradas del zip varían (§6 del informe) |
| `resondeo40.log`, `sellar.log`, `pytest-antes.log`, `pytest-despues.log`, `pytest-gpu-repeticion.log` | la trazabilidad de la ronda |

## Qué NO se versiona (binarios regenerables, `CLAUDE.md` §6)

- `out/` — 40 ficheros de salida más las copias-espía del desechable, ~602 KB.
- `entradas/` — `entrada.xlsx`, `entrada.pptx`, `entrada.mobi` y `entrada.azw3`,
  ~64 KB. **No son fuente:** las fabrica el propio arnés con aristas reales
  (`csv→xlsx` y `md→pptx` son los casos W01 y W17; `epub→mobi` y `epub→azw3` son
  las `_MEDIDAS` C03 y C04). Las semillas de verdad —`entrada.csv`, `.svg`,
  `.tex`, `.docx`, `.epub`, `.html`, `.md`, `.odt`, `.rtf`, `.txt`— ya están
  versionadas por K1 y S3 en `bench/salidas-hito5/entradas/` y
  `bench/salidas-sondeo-doc/entradas/`.

**AVISO sobre reproducir esto byte a byte: no se puede, y está medido.**
`calibre epub→epub` no es determinista (4 corridas, 4 `sha256`, de 17 712 a
141 175 B; la varianza está en la portada que Calibre GENERA). Lo reproducible
es el **veredicto del contrato** y el texto recuperado, no el `sha256`.

## La orden que lo reproduce

```
D:\Workesearch\FileX\.venv-mcp-filex\Scripts\python.exe bench/salidas-rasteriza-declaradas/_resondeo40.py
D:\Workesearch\FileX\.venv-mcp-filex\Scripts\python.exe bench/salidas-rasteriza-declaradas/_sellar.py
```

Requiere **Docker levantado** con la imagen `filex-c13` (`soffice`, `pandoc` y
`ebook-convert` dentro) y el Ghostscript nativo `gswin64c` en el PATH, que es lo
que recupera el texto de un PDF. Sin Docker el arnés sale con `rc=2` y el
mensaje «NO hay motores documentales disponibles».

## Las 40 aristas remedidas

`rasteriza` medido con el centinela `FILEXSENTINELA7743` y el umbral de ≥10
caracteres de la trampa 4. `ciego` = el formato comprime el texto y la sonda no
puede concluir.

| id | motor | par | rc | ms | bytes | car | cent | rasteriza | contrato |
|---|---|---|---:|---:|---:|---:|---|---|---|
| W01 | libreoffice | `csv→xlsx` | 0 | 3804 | 5790 | 338 | sí | no | ok_parcial |
| W02 | libreoffice | `rtf→odt` | 0 | 2834 | 14173 | 1767 | sí | no | ok_parcial |
| W03 | libreoffice | `rtf→docx` | 0 | 2938 | 5293 | 542 | sí | no | ok_parcial |
| W04 | libreoffice | `html→odt` | 0 | 3825 | 8122 | 1190 | sí | no | ok_parcial |
| W05 | libreoffice | `txt→odt` | 0 | 3148 | 12117 | 1104 | sí | no | ok_parcial |
| W06 | libreoffice | `odt→html` | 0 | 3902 | 2476 | 895 | sí | no | ok |
| W07 | libreoffice | `docx→rtf` | 0 | 3312 | 8213 | 8213 | sí | no | ok |
| W08 | libreoffice | `xlsx→pdf` | 0 | 7410 | 27403 | 119 | sí | no | ok |
| W09 | libreoffice | `xlsx→csv` | 0 | 3575 | 109 | 108 | sí | no | ok |
| W10 | libreoffice | `xlsx→html` | 0 | 3405 | 2902 | 464 | sí | no | ok |
| W11 | libreoffice | `csv→pdf` | 0 | 4496 | 20944 | 119 | sí | no | ok |
| W12 | libreoffice | `pptx→pdf` | 0 | 4560 | 24534 | 456 | sí | no | ok |
| W13 | libreoffice | `pptx→odp` | 0 | 5171 | 32669 | 2825 | sí | no | ok_parcial |
| W14 | libreoffice | `svg→pdf` | 0 | 2435 | 12500 | 44 | sí | no | ok |
| W15 | libreoffice | `pptx→png` | 0 | 3223 | 50462 | 0 | no | si | ok |
| W16 | libreoffice | `svg→png` | 0 | 5297 | 9081 | 0 | no | si | ok |
| W17 | pandoc | `md→pptx` | 0 | 4636 | 28170 | 2218 | sí | no | ok_parcial |
| W18 | pandoc | `html→epub` | 0 | 1308 | 5284 | 554 | sí | no | ok_parcial |
| W19 | pandoc | `html→odt` | 0 | 2564 | 7285 | 543 | sí | no | ok_parcial |
| W20 | pandoc | `html→rtf` | 0 | 1747 | 1756 | 1754 | sí | no | ok |
| W21 | pandoc | `docx→odt` | 0 | 1121 | 7202 | 515 | sí | no | ok_parcial |
| W22 | pandoc | `epub→docx` | 0 | 821 | 10993 | 635 | sí | no | ok_parcial |
| W23 | pandoc | `epub→txt` | 0 | 1163 | 566 | 514 | sí | no | ok |
| W24 | pandoc | `rtf→md` | 0 | 1852 | 471 | 466 | sí | no | ok |
| W25 | pandoc | `rtf→html` | 0 | 1805 | 4324 | 3133 | sí | no | ok |
| W26 | pandoc | `md→rtf` | 0 | 835 | 1700 | 1698 | sí | no | ok |
| W27 | pandoc | `md→tex` | 0 | 1602 | 2748 | 2699 | sí | no | ok |
| W28 | pandoc | `docx→tex` | 0 | 865 | 2698 | 2649 | sí | no | ok |
| W29 | pandoc | `tex→docx` | 0 | 1931 | 10772 | 394 | sí | no | ok_parcial |
| W30 | pandoc | `tex→html` | 0 | 895 | 4651 | 2939 | sí | no | ok |
| W31 | pandoc | `tex→pdf` | 0 | 5613 | 9758 | 268 | sí | no | aviso |
| W32 | pandoc | `pptx→md` | 0 | 1232 | 549 | 499 | sí | no | ok |
| W33 | calibre | `mobi→epub` | 0 | 7078 | 30875 | 610 | sí | no | ok_parcial |
| W34 | calibre | `azw3→epub` | 0 | 4111 | 20029 | 564 | sí | no | ok_parcial |
| W35 | calibre | `mobi→pdf` | 0 | 9203 | 31178 | 488 | sí | no | ok |
| W36 | calibre | `azw3→pdf` | 0 | 6524 | 27387 | 456 | sí | no | ok |
| W37 | calibre | `txt→epub` | 0 | 6840 | 10022 | 484 | sí | no | ok_parcial |
| W38 | calibre | `md→epub` | 0 | 3980 | 11844 | 558 | sí | no | ok_parcial |
| W39 | calibre | `epub→epub` | 0 | 4064 | 19596 | 564 | sí | no | ok_parcial |
| W40 | calibre | `mobi→azw3` | 0 | 3133 | 12614 | 12603 | no | ciego | ok_parcial |

**40 de 40 con `rc=0`. 40 de 40 reproducen el veredicto de contrato que estaba
sellado: 0 movidos.** 0 contenedores huérfanos nuevos, contados con
`docker ps -a` y no con `docker ps` (trampa 37).

## Sumas de comprobación de lo versionado

| fichero | bytes | `sha256` (16) |
|---|---:|---|
| `_resondeo40.py` | 19402 | `35428031f9cce4ea` |
| `_sellar.py` | 7666 | `856233740971ac85` |
| `contrafactual.json` | 2108 | `9d9cd08888a0f09a` |
| `determinismo_epub.json` | 1211 | `41c63d839ce20294` |
| `planificador_despues.json` | 1087 | `2a9271817245098c` |
| `pytest-antes.log` | 1122 | `94f5133caea075d4` |
| `pytest-despues.log` | 50 | `dd89800342a2adde` |
| `pytest-gpu-repeticion.log` | 1066 | `799512728ecfd36b` |
| `resondeo40.json` | 43919 | `14c022b0e73080cb` |
| `resondeo40.log` | 6934 | `58809d0a5d8c97de` |
| `sellar.log` | 242 | `6b0ca085e82597eb` |

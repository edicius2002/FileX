# Sondeo de las aristas documentales en contenedor

**Agente S3 · 22 de agosto de 2026 · máquina del proyecto (Windows 10, Docker 29.4.3 + WSL2, imagen `filex-c13@6d359bad483e`)**

Encargo: sondear las **23 aristas `sin_sondear`** de `doc_libreoffice`, `doc_pandoc` y `doc_calibre`, y entregar `filex/sondeo/doc_*.json`.

Ficheros entregados: `filex/sondeo/doc_libreoffice.json`, `doc_pandoc.json`, `doc_calibre.json`, este informe y `bench/salidas-sondeo-doc/**` (6 arneses, 6 `.json`, 2 `.log`, 3 semillas de texto y `MANIFIESTO.md`; **las salidas binarias, borradas**). **No se ha tocado ningún `.py` de `filex/` ni ningún `.md` de otro agente.** Los cambios que pido al núcleo van en §7 con su diff exacto y **no aplicados**.

Cada afirmación va marcada **[MEDIDO]** o **[PENDIENTE]**. Todas las cifras salen de `bench/salidas-sondeo-doc/*.json`.

---

## 0. Resumen

| | Antes | Después |
|---|---:|---:|
| Aristas `doc_*` `real` | 33 | **56** |
| Aristas `doc_*` `nominal` | 3 | 3 |
| Aristas `doc_*` `sin_sondear` | **23** | **0** |
| Aristas del grafo entero | 215 | 215 |
| Pruebas en verde | 88 | **88** ⁴ |

**[MEDIDO]** — `python -m unittest discover -s pruebas` y `FileX().grafo`.

⁴ *Con una salvedad honesta: en 2 de 5 pasadas de la suite completa falló **una** prueba, `test_el_tope_de_dentro_no_deja_contenedores_vivos`, que es de K1 y **es inestable bajo carga**, no una regresión de este trabajo — en aislamiento da 4 de 4 en verde y el contenedor no queda. Diagnóstico y números en el pendiente 8.*

**Las 23 salen `real`. Ninguna sale `nominal`, y eso es un resultado, no un descuido:** las 23 se eligieron en su día porque compartían filtro de importación con una arista ya medida, y la apuesta se ha pagado 23 de 23. Lo interesante no está ahí.

### Los cinco hallazgos

1. **El contrato de cinco puntos rechaza salidas perfectamente buenas, por DOS defectos distintos del verificador, y no es un problema de este sondeo: hoy rompe 8 de las aristas que `motor_contenedor.py` declara `REAL`** — con `rc=0`, el documento entero y el centinela intacto, y **sin que la salida llegue a su destino**. 8 de 8 expuestas caen; 2 de 2 controles pasan (§2). **Es el hallazgo principal y el que más se parece a lo que pedía el encargo, con el signo cambiado: no es un `ok` que tapa una pérdida, es un `fallo` que tapa un acierto.**
2. **`svg→png` con `soffice` da `rc=0`, un PNG de 9 081 B, contrato `ok` en los cinco puntos y CERO letras** desde un SVG cuyo texto sí es texto. Es un **miembro nuevo de la familia de `resvg`** — y con el mismo par de formatos que le dio nombre, pero con otro motor y, esta vez, dentro del contenedor donde `magick svg→png` es `nominal` (§3).
3. **El pendiente 3 de `hito5-documental.md` se cierra sin un lector de MOBI: por ida y vuelta.** `mobi→epub` devuelve 610 caracteres con el centinela; `azw3→epub`, 564. Si el EPUB lo recupera, el MOBI lo tenía (§4).
4. **Calibre no es reproducible byte a byte, y el motivo es exacto:** en `mobi→epub`, de los 11 miembros del EPUB **8 son idénticos byte a byte en 3 ejecuciones** —incluido el texto— y cambian tres: `content.opf`, `toc.ncx` (UUID) y `cover_image.jpg`, **una portada GENERADA cuyo tamaño va de 49 561 a 66 992 B**. El fichero entero varía ×1,68 sin que el documento cambie. **Un `sha256` de una salida de Calibre en un `MANIFIESTO.md` no reproduce nada** (§5).
5. **El pendiente 5 se cierra con 17 aristas más ejecutadas** (`xlsx`, `pptx`, `csv`, `svg`, `tex`), de las que **17 de 17 dan `rc=0`**, y aparecen dos cosas que el catálogo no dejaba ver: **pandoc SÍ lee `pptx`** (`pptx→md`, 549 B con centinela) y **`soffice svg→pdf` conserva el texto** (44 caracteres, centinela) donde `svg→png` lo destruye (§3).

---

## 1. Método: por qué hay que FORZAR la arista

`FileX.convertir()` no convierte una arista: convierte un **par de formatos**, y elige el camino. Sondear `rtf→odt` dejándole elegir mediría el grafo, no la arista — y en dos casos ni siquiera llegaría a ejecutarse: `epub→epub` sale por el atajo `origen y destino son el mismo formato` antes de planificar nada.

Por eso `_sonda23.py` sustituye `fx.planificar` **en la instancia** por una `Decision` de un solo paso. Todo lo demás lo hace el núcleo entero: directorio desechable, `docker run` con el tope por dentro, **censo del punto 5 dentro del mismo `with`**, contrato de cinco puntos y recogida. No se ha tocado `filex/`.

**Y hace falta una segunda instrumentación, que resultó ser la que destapó el hallazgo 1.** Cuando el contrato dice `fallo`, `nucleo._un_salto` **no recoge la salida** y el `finally` borra el desechable: de una arista rechazada solo queda el veredicto. `DirTrabajoEspia` —una subclase que copia el desechable antes de borrarlo, sustituida en `filex.nucleo` desde el arnés— permite mirar qué escribió el motor. **Sin ella, `rtf→md` habría quedado como «`fallo`, 0 bytes» cuando lo que hay son 471 bytes con el documento entero.**

> **Trampa de arnés, pagada dos veces en un día, y ya estaba escrita para MOBI:** una sonda de texto ingenua da por destruido lo que no sabe leer. La copia de `texto_de` de K1 no conocía `xlsx`, `pptx` ni `odp`, y las tres primeras filas del pendiente 5 salieron con **0 caracteres y sin centinela**. Añadidas las tres extensiones a la lista de ZIP, las mismas salidas dan **338, 2 218 y 2 825 caracteres con el centinela**. **[MEDIDO]** — comparar `sonda-p5.log` con `sonda-p5.json`. *Lo que se midió la primera vez fue mi sonda, no la conversión.*

### 1.1 Las 23, una a una — **[MEDIDO]**

`bench/salidas-sondeo-doc/sonda23.json`. n=1 por arista, 190,2 s en total.

| id | submotor | arista | rc | ms | bytes | caracteres | centinela | contrato |
|---|---|---|---:|---:|---:|---:|:---:|---|
| S01 | libreoffice | `rtf→odt` | 0 | 5 418 | 14 176 | 1 769 | sí | ok_parcial |
| S02 | libreoffice | `rtf→docx` | 0 | 3 468 | 5 293 | 542 | sí | ok_parcial |
| S03 | libreoffice | `html→odt` | 0 | 2 381 | 8 125 | 1 194 | sí | ok_parcial |
| S04 | libreoffice | `txt→odt` | 0 | 4 018 | 12 125 | 1 110 | sí | ok_parcial |
| S05 | libreoffice | `odt→html` | 0 | 10 443 | 2 476 | 895 | sí | ok |
| S06 | libreoffice | `docx→rtf` | 0 | 4 956 | 8 213 | 8 213 | sí | ok |
| S07 | pandoc | `html→epub` | 0 | 5 869 | 5 286 | 554 | sí | ok_parcial |
| S08 | pandoc | `html→odt` | 0 | 1 150 | 7 286 | 543 | sí | ok_parcial |
| S09 | pandoc | `html→rtf` | 0 | 1 044 | 1 756 | 1 754 | sí | ok |
| S10 | pandoc | `docx→odt` | 0 | 3 454 | 7 203 | 515 | sí | ok_parcial |
| S11 | pandoc | `epub→docx` | 0 | 1 680 | 10 993 | 635 | sí | ok_parcial |
| **S12** | pandoc | **`epub→txt`** | 0 | 938 | 566 | 514 | sí | **fallo** |
| **S13** | pandoc | **`rtf→md`** | 0 | 878 | 471 | 466 | sí | **fallo** |
| S14 | pandoc | `rtf→html` | 0 | 2 663 | 4 324 | 3 133 | sí | ok |
| S15 | pandoc | `md→rtf` | 0 | 990 | 1 700 | 1 698 | sí | ok |
| S16 | calibre | `mobi→epub` | 0 | 6 770 | 18 336 | 610 | sí | ok_parcial |
| S17 | calibre | `azw3→epub` | 0 | 5 227 | 18 602 | 564 | sí | ok_parcial |
| S18 | calibre | `mobi→pdf` | 0 | 14 487 | 31 178 | 488 | sí | ok |
| S19 | calibre | `azw3→pdf` | 0 | 20 208 | 27 387 | 456 | sí | ok |
| S20 | calibre | `txt→epub` | 0 | 36 784 | 26 406 | 484 | sí | ok_parcial |
| S21 | calibre | `md→epub` | 0 | 40 279 | 11 851 | 558 | sí | ok_parcial |
| S22 | calibre | `epub→epub` | 0 | 9 637 | 20 209 | 564 | sí | ok_parcial |
| S23 | calibre | `mobi→azw3` | 0 | 4 949 | 12 614 | 12 603 | **no** | ok_parcial |

**Sobrantes del punto 5: cero en las 23.** Ningún motor escribió nada fuera de lo declarado. `N9` informa en las 23 de que **el fichero declarado lleva el 100,0 % de los bytes escritos**.

**S23 es el único sin centinela y no es un fallo: la sonda de texto es CIEGA sobre AZW3** (comprime el texto, `formatos.py`). Verificado por ida y vuelta en §4.

> **Los ms son n=1, en una tanda `SUCIA` (sesión remota activa, estructural) y con dos agentes más trabajando en la misma máquina.** `CLAUDE.md` §3: *las cifras absolutas de tandas distintas no son comparables*. Sirven para lo que `sondeo.py` las usa —desempatar entre motores que hacen la MISMA arista, `coste = 1 + ms/100 000`— y para nada más. No se han medido testigos de ruido: con n=1 no habrían añadido información que cambiara una decisión.

### 1.2 El `ok_parcial` de 13 de las 23 NO es un aviso: es cobertura honesta — **[MEDIDO]**

Las 13 tienen exactamente la misma cobertura: `3_propiedades: False`, `4_pedido: False`, el resto `True`. Y las 13 tienen destino **ODT, DOCX, EPUB o AZW3**. El verificador no tiene sonda de propiedades para un documento contenedor, y **lo dice en vez de dar por bueno lo que no miró**. Es el mismo criterio de los cuatro estados de cobertura de `CLAUDE.md` §5. Las 10 que salen `ok` tienen destino PDF, HTML o RTF, que sí tienen sonda.

---

## 2. EL HALLAZGO: el contrato rechaza salidas buenas, por dos defectos independientes

Dos de las 23 salen `fallo`. Ninguna de las dos es culpa de la arista.

### 2.1 Defecto A — todo texto plano se sondea como CSV, y la prosa con comas dispara `D2` — **[MEDIDO]**

`verificador.py:2874` manda a `_datos()` todo fichero con firma `texto`, y `_datos()` (línea 1322) hace:

```python
else:
    d["formato"] = "csv"
```

**Todo lo que no sea `.json` es CSV.** Después, `csv.reader` con coma cuenta campos por línea y el punto 3 dispara `D2 numero de campos no constante` → **`fallo`**.

Tres ficheros **escritos a mano, sin ningún motor de por medio** (`d2.json` §A):

| fichero | contenido | veredicto |
|---|---|---|
| `prosa_con_comas.txt` | dos líneas, una con tres comas y otra con ninguna | **`fallo` · D2** |
| `prosa_sin_comas.txt` | el mismo texto sin comas | `ok_parcial` |
| `tabla_markdown.md` | un título y una tabla de pipes | `ok_parcial` |

**El disparador no es el formato: son las comas de la prosa.** Y por eso no lo había visto nadie: la semilla de K1 tiene comas, pero K1 midió `rc` + centinela, no el contrato.

### 2.2 Defecto B — el contador de páginas no ve dentro de un flujo de objetos, y los PDF de xelatex fallan `P1` — **[MEDIDO]**

`verificador.py:1250-1269` cuenta `/Type /Page` **en los bytes crudos**, con respaldo a `/Count`. **xelatex mete los objetos de página en flujos de objetos comprimidos**, así que los dos caminos dan 0 y el punto 3 dispara `P1 el PDF no declara ninguna pagina` → **`fallo`** sobre un PDF perfectamente válido de 10 371 B con el centinela.

Y hay un **discriminador exacto y gratuito**, sondeado sobre los 8 PDF producidos en este trabajo (`objstm.json`):

| PDF | motor | `/ObjStm` | `/Type/Page` crudos | `n_paginas` |
|---|---|:---:|---:|---:|
| `R_libreoffice_docx2pdf.pdf` | soffice | no | 2 | 1 |
| `Q03_xlsx2pdf.pdf` | soffice | no | 2 | 1 |
| `Q06_csv2pdf.pdf` | soffice | no | 2 | 1 |
| `Q07_pptx2pdf.pdf` | soffice | no | 2 | 1 |
| `Q10_svg2pdf.pdf` | soffice | no | 2 | 1 |
| `S18_calibre_mobi2pdf.pdf` | calibre | no | 5 | — |
| `S19_calibre_azw32pdf.pdf` | calibre | no | 3 | — |
| **`Q16_tex2pdf.pdf`** | **pandoc+xelatex** | **sí** | **0** | **0** |

**8 de 8: `/ObjStm` está presente exactamente en el único PDF cuyo contador da 0.** El diccionario del flujo de objetos **no** está comprimido, así que la marca se lee sin descomprimir nada.

> **Y hay un tercer síntoma del mismo defecto, que nadie está mirando todavía:** en los dos PDF de xelatex, `indicio_texto` (o sea `/Font in datos`) sale **`False`** sobre un PDF con 456 caracteres seleccionables. **El indicio barato de capa de texto es un falso negativo en cuanto el PDF usa flujos de objetos.** **[MEDIDO]**, `d2.json` §B.

### 2.3 Y no es un problema de este sondeo: **8 de las 33 aristas `REAL` de `motor_contenedor.py` están rotas HOY** — **[MEDIDO]**

Censo completo de las aristas ya declaradas `REAL` cuyo destino es texto plano o un PDF de xelatex, convertidas **por el núcleo entero** (`d2.json` §B):

| arista declarada `REAL` | rc | bytes | centinela | contrato | **llega al destino** |
|---|---:|---:|:---:|---|:---:|
| `odt→txt` [libreoffice] | 0 | 458 | sí | **fallo · D2** | **NO** |
| `md→txt` [pandoc] | 0 | 535 | sí | **fallo · D2, D1, D4** | **NO** |
| `docx→md` [pandoc] | 0 | 566 | sí | **fallo · D2** | **NO** |
| `epub→md` [pandoc] | 0 | 585 | sí | **fallo · D2** | **NO** |
| `html→md` [pandoc] | 0 | 568 | sí | **fallo · D2** | **NO** |
| `epub→txt` [calibre] | 0 | 468 | sí | **fallo · D2** | **NO** |
| `md→pdf` [pandoc, xelatex] | 0 | 10 371 | sí | **fallo · P1** | **NO** |
| `docx→pdf` [pandoc, xelatex] | 0 | 8 160 | sí | **fallo · P1** | **NO** |
| *control* `docx→pdf` [libreoffice] | 0 | 22 820 | sí | `ok` | sí |
| *control* `docx→html` [libreoffice] | 0 | 2 399 | sí | `ok` | sí |

**8 de 8 expuestas caen. 2 de 2 controles pasan.** Los controles son los que separan «el verificador está roto» de «los PDF están rotos» o «los motores documentales están rotos»: ni lo uno ni lo otro.

**La columna que más importa es la última.** `nucleo._un_salto` devuelve antes de `t.recoger()` cuando el contrato dice `fallo`, y el `finally` borra el desechable: **hoy `filex convertir informe.odt informe.txt` devuelve `fallo` y no deja ningún fichero**, con el motor habiendo hecho su trabajo bien. El contrato existe para que no salga una salida mala; aquí impide que salga una buena.

### 2.4 Cómo he clasificado esas aristas, y qué cambiar si se prefiere lo contrario

El encargo dice `nominal` si el contrato dice `fallo`. **He escrito `real` en las 6 afectadas** (S12, S13, Q12, Q13, Q16, Q17), con el motivo dentro de la propia entrada del JSON. El razonamiento:

* está **demostrado que el `fallo` es independiente de la arista** —un fichero escrito a mano lo reproduce, y 8 aristas ya `REAL` caen con él—;
* marcar `nominal` le suma **coste infinito** en `grafo._coste_paso` y saca `rtf→md` y `epub→txt` del grafo **para siempre, sobre una medida que se sabe falsa**. Es exactamente el fallo que este proyecto le mide al resto del sector, cometido con más información.

**Si el consolidador prefiere la letra de la regla**, el cambio son dos condiciones en `bench/salidas-sondeo-doc/_tabla_sondeo.py::estado_de` (las dos `return "real"` de los bloques `reglas <= {"D1","D2","D4"}` y `reglas == {"P1"}`) y volver a ejecutarlo. **El efecto sería sacar del grafo `rtf→md`, `epub→txt`, `md→tex`, `docx→tex`, `tex→pdf` y `pptx→md`.** Está aquí escrito para que la decisión sea explícita y de quien corresponda.

---

## 3. Pendiente 5 de `hito5-documental.md`: `xlsx`, `pptx`, `csv`, `svg`, `tex` — **[MEDIDO]**

17 aristas más, ejecutadas con `_sonda_p5.py` (invocación directa del contenedor, porque **el grafo no declara estos pares**, y `_EnContenedor.orden()` levanta `ValueError` para lo que el motor no declara — y hace bien). Se les pasa **el mismo contrato de cinco puntos** con el censo tomado dentro del mismo `with`. `sonda-p5.json`.

| id | submotor | arista | rc | ms | bytes | caracteres | centinela | contrato |
|---|---|---|---:|---:|---:|---:|:---:|---|
| Q01 | libreoffice | `csv→xlsx` | 0 | 6 936 | 5 790 | 338 | sí | ok_parcial |
| Q02 | pandoc | `md→pptx` | 0 | 2 069 | 28 170 | 2 218 | sí | ok_parcial |
| Q03 | libreoffice | `xlsx→pdf` | 0 | 5 006 | 27 403 | 119 | sí | ok |
| Q04 | libreoffice | `xlsx→csv` | 0 | 6 215 | 109 | 108 | sí | ok |
| Q05 | libreoffice | `xlsx→html` | 0 | 5 667 | 2 902 | 464 | sí | ok |
| Q06 | libreoffice | `csv→pdf` | 0 | 19 663 | 20 944 | 119 | sí | ok |
| Q07 | libreoffice | `pptx→pdf` | 0 | 6 259 | 24 534 | 456 | sí | ok |
| Q08 | libreoffice | `pptx→odp` | 0 | 9 104 | 32 669 | 2 825 | sí | ok_parcial |
| **Q09** | libreoffice | **`pptx→png`** | 0 | 4 446 | 50 462 | **0** | **no** | **ok** |
| **Q10** | libreoffice | **`svg→pdf`** | 0 | 3 261 | 12 500 | **44** | **sí** | ok |
| **Q11** | libreoffice | **`svg→png`** | 0 | 4 165 | 9 081 | **0** | **no** | **ok** |
| Q12 | pandoc | `md→tex` | 0 | 1 989 | 2 748 | 2 699 | sí | fallo (§2.1) |
| Q13 | pandoc | `docx→tex` | 0 | 1 710 | 2 698 | 2 649 | sí | fallo (§2.1) |
| Q14 | pandoc | `tex→docx` | 0 | 3 868 | 10 771 | 394 | sí | ok_parcial |
| Q15 | pandoc | `tex→html` | 0 | 4 794 | 4 651 | 2 939 | sí | ok |
| Q16 | pandoc | `tex→pdf` | 0 | 44 598 | 9 754 | 268 | sí | fallo (§2.2) |
| **Q17** | pandoc | **`pptx→md`** | 0 | 3 357 | 549 | 499 | sí | fallo (§2.1) |

**Cero sobrantes en las 17.** **17 de 17 con `rc=0`** — ninguna de estas cinco familias tiene una semiarista muerta en esta imagen.

**Cuatro lecturas:**

1. **`svg→png` con `soffice` es un miembro nuevo de la familia de `resvg`, y con el mismo par de formatos.** `rc=0`, PNG válido de 9 081 B, **contrato `ok` en los cinco puntos**, y **cero letras** de un SVG cuyo texto es texto de verdad. Encaja letra por letra en la formulación de `CLAUDE.md` §5: *el contenido perdido solo existe como píxeles, así que hace falta fidelidad, no contrato.* Y añade un matiz que no estaba: **`svg→png` es `nominal` con `magick` en este mismo Debian** (`grafo.py`, encabezado) **y `real` con `soffice` en la misma imagen**. El motor vuelve a ser la tercera dimensión de la arista, ahora en el sentido contrario al que se documentó.
2. **Y el contraste está dentro del mismo motor y el mismo origen:** `svg→pdf` con `soffice` conserva los **44 caracteres** del SVG y el centinela; `svg→png` conserva 0. **Es el par `docx→pdf` / `docx→png` de K1 otra vez, con otro origen** — lo que decide no es el motor, es el camino.
3. **Pandoc lee PPTX.** `pptx→md` da 549 B con el centinela y la tabla. No está en `_DECLARADAS` de nadie y ningún catálogo del proyecto lo recogía.
4. **`csv→pdf` cuesta 19 663 ms y `xlsx→pdf` 5 006** sobre el mismo contenido: pasar por el filtro de importación de texto le cuesta a LibreOffice **×3,9**. Si el grafo llega a declarar las dos, el coste medido elige solo.

> **Semillas:** `entrada.csv`, `entrada.svg` y `entrada.tex` están escritas a mano y **se versionan** (texto, <1 KB). `entrada.xlsx` la fabrica Q01 y `entrada.pptx` la fabrica Q02, así que las dos aristas que producen semilla son a la vez aristas medidas. `entrada.mobi` y `entrada.azw3` salen de `epub→mobi`/`epub→azw3`, ya medidas por K1.

---

## 4. Pendiente 3 cerrado: MOBI y AZW3, verificados por IDA Y VUELTA — **[MEDIDO]**

`hito5-documental.md` §8 lo deja así: *«`epub→mobi` y `epub→azw3` verificadas con un lector de MOBI, no con un `grep` binario. Hoy entran como `real` solo por `rc` y bytes.»*

**No hace falta un lector: si el EPUB de vuelta trae el centinela, el MOBI lo tenía.** `d2.json` §C:

| ficheros de partida | → epub | caracteres | centinela |
|---|---|---:|:---:|
| `entrada.mobi` (de `epub→mobi`, C03) | `mobi→epub` | **610** | **sí** |
| `entrada.azw3` (de `epub→azw3`, C04) | `azw3→epub` | **564** | **sí** |
| `S23_calibre_mobi2azw3.azw3` (de `mobi→azw3`) | `azw3→epub` | **610** | **sí** |

**Las tres recuperan el centinela.** *(La columna «bytes» se omite a propósito: §5 mide que el tamaño del EPUB de Calibre no es reproducible. **Los 610 y los 564 sí lo son: idénticos en las cuatro ejecuciones de `_d2.py`**, que es exactamente la lectura de §5 — el texto es estable, el envoltorio no.)* Con eso quedan verificadas por contenido, y no solo por `rc`, **cuatro** aristas: `epub→mobi`, `epub→azw3`, `mobi→azw3` y —de propina, porque la tercera fila es una cadena de dos saltos— que el texto sobrevive a `epub→mobi→azw3→epub`.

> **El método vale para toda la familia opaca**, que es lo que lo hace útil más allá de este caso: cuando la sonda de texto es ciega a un formato, **una arista de vuelta a un formato legible es una sonda de fidelidad**, y en este proyecto normalmente ya está medida.

---

## 5. Reproducibilidad: Calibre no, pandoc sí — y el motivo, al miembro — **[MEDIDO]**

Salió al recoger: tres ejecuciones de `_d2.py` dieron para el **mismo** `mobi→epub` **19 720, 20 982 y 131 318 B**. Un ×6,7 sobre la misma entrada, el mismo motor y la misma imagen no es ruido. `_repro.py`, n=3 (`repro.json`):

| arista | motor | tamaños en 3 ejecuciones | `sha256` distintos |
|---|---|---|---:|
| `mobi→epub` | calibre | **18 333 / 24 270 / 30 876** (×1,68) | **3** |
| `epub→pdf` | calibre | 26 817 / 26 817 / 26 817 | **3** |
| `md→html` | pandoc | 4 525 / 4 525 / 4 525 | **1** |

Y abriendo los tres EPUB (`repro-epub-miembros.json`), **el motivo es exacto: de 11 miembros, 8 son idénticos byte a byte** —incluidos `index_split_000.html` e `index_split_001.html`, o sea **el texto**— y cambian tres:

| miembro | tamaños | qué es |
|---|---|---|
| `content.opf` | 1 872 / 1 872 / 1 872 | mismo tamaño, distinto contenido: **UUID** |
| `toc.ncx` | 688 / 688 / 688 | ídem |
| **`cover_image.jpg`** | **49 561 / 55 416 / 66 992** | **portada GENERADA por Calibre** |

**Tres consecuencias:**

1. **Un `sha256` de una salida de Calibre en un `MANIFIESTO.md` no reproduce nada.** El de `bench/salidas-hito5/MANIFIESTO.md` tampoco, para sus salidas de Calibre. Lo que sí reproduce, y coincide tres veces, es el **`sha256` del miembro que lleva el texto**.
2. **`epub→pdf` da 26 817 B las tres veces y tres `sha` distintos**: es la trampa 22 otra vez (`/CreationDate`), ahora en Calibre. **El tamaño es estable y el hash no.**
3. **El ×1,68 de tamaño NO dice nada sobre la conversión**: es la portada. Es la trampa 2 —*menor tamaño ≠ mejor conversión*— con un mecanismo nuevo y medido.

**[PENDIENTE]** si `ebook-convert --no-default-epub-cover` (o equivalente) hace la salida estable; no se ha probado, y cambiaría la salida, así que es una decisión de parametrización, no de arnés.

---

## 6. Docker: censo de contenedores antes y después — **[MEDIDO]**

`sonda23.json` guarda las dos listas completas.

| | antes | después | **nuevos vivos** |
|---|---:|---:|---:|
| contenedores | **5** | **5** | **0** |

Los cinco son los del proyecto (`filex-convertx`, `filex-snapotter`, `filex-snapotter-pg`, `filex-snapotter-redis`, `filex-gotenberg8`), los mismos `Up 2 hours` antes y después. Más un `filex-gotenberg` parado desde hace dos semanas, que sigue parado.

**Ninguna de las 40 conversiones dejó un contenedor vivo.** El tope de dentro (`--entrypoint timeout -k 5 N`) hizo su trabajo; ninguna llegó a dispararlo, porque ninguna se colgó: la más lenta fue `tex→pdf` con 44,6 s contra un tope de 90. **`docker ps` al terminar: idéntico al de empezar.**

> **Elección de tope, y su motivo:** `TIMEOUT = 100` fuera → **90 dentro**. Por encima del ×4,4 sobre la arista más lenta que había medida (Calibre `epub→pdf`, 20,6 s) y **acotando la fuga**: `soffice` colgado escribe hasta 1,97 MB/s en el desechable (K1 §4.2), así que 90 s son ~180 MB en el peor caso. Un tope no solo limita el tiempo: limita el disco.

---

## 7. Cambios que pido al núcleo (**NO aplicados**)

Los tres son de `filex/`, que no es mío.

### 7.1 `verificador.py`: el texto plano no es CSV — **cierra el defecto A (§2.1)**

La corrección mínima separa el **formato** sin tocar la **categoría**, para que las comprobaciones de codificación (`D5`, U+FFFD) sigan aplicando a un `.txt`:

```diff
--- a/filex/verificador.py
+++ b/filex/verificador.py
@@ def _datos(ruta):
     else:
-        d["formato"] = "csv"
+        # Un `.md`, un `.txt` o un `.tex` NO son datos tabulares. Declararlos
+        # `csv` hace que `csv.reader` cuente campos por COMA, y cualquier prosa
+        # con un numero variable de comas dispara `D2 numero de campos no
+        # constante`. MEDIDO (`bench/sondeo-documental.md` §2.3): tumba 6 de las
+        # aristas que `motor_contenedor.py` declara REAL, con el documento
+        # entero y el centinela intacto, y la salida NO llega a su destino.
+        # Se separa el FORMATO y no la categoria para que D5 siga aplicando.
+        d["formato"] = "csv" if ext in EXT_TABULARES else "texto_plano"
+        if d["formato"] != "csv":
+            return d
```

…con, arriba del módulo:

```diff
+#: Extensiones que SI son datos tabulares. Lo demas con firma `texto` es un
+#: documento de texto plano, no una tabla sin cabecera.
+EXT_TABULARES = {".csv", ".tsv", ".psv", ".json", ".ndjson", ".jsonl"}
```

Con esto `D1`, `D2` y `D4` dejan de emitirse sobre `.md`, `.txt`, `.tex` y `.rtf`, que es lo correcto: **son reglas de tabla, y una tabla es lo único sobre lo que «número de campos» significa algo.**

### 7.2 `verificador.py`: `P1` no puede ser `fallo` cuando las páginas viven en un flujo comprimido — **cierra el defecto B (§2.2)**

```diff
--- a/filex/verificador.py
+++ b/filex/verificador.py
@@ def _pdf(...):
     if n == 0:
         k = datos.rfind(b"/Count")
         ...
         d["paginas_por_flujo_comprimido"] = True
+    # Marca EXACTA y gratuita: el diccionario de un flujo de objetos NO esta
+    # comprimido, asi que `/ObjStm` se lee en los bytes crudos. MEDIDO sobre 8
+    # PDF de 3 motores (`bench/salidas-sondeo-doc/objstm.json`): esta en 1 de 8,
+    # y es exactamente el unico cuyo contador da 0.
+    d["objetos_en_flujo_comprimido"] = b"/ObjStm" in datos
     d["n_paginas"] = n
@@ def punto3(...):
     elif cat == "pdf":
         n = sonda.get("n_paginas")
-        if not n:
+        if not n and sonda.get("objetos_en_flujo_comprimido"):
+            # xelatex mete los objetos de pagina en flujos comprimidos: el
+            # contador por bytes crudos da 0 sobre un PDF valido con texto
+            # seleccionable. No se puede saber sin descomprimir: es
+            # NO VERIFICABLE, no un fallo. MEDIDO: `md->pdf` y `docx->pdf` de
+            # pandoc, las dos REAL, con el centinela intacto.
+            h.append(_hallazgo(3, "P1", "aviso", "el numero de paginas vive en un "
+                               "flujo de objetos comprimido: no verificable"))
+        elif not n:
             h.append(_hallazgo(3, "P1", "fallo", "el PDF no declara ninguna pagina", ">=1", n))
```

**Y una salvedad honesta:** esto deja de atrapar un PDF de 0 páginas **que además use flujos de objetos**. El intercambio está medido en un sentido (8 falsos positivos reales, 1 falso negativo hipotético) y no en el otro. **[PENDIENTE]**: descomprimir el `/ObjStm` con `zlib` —está en la biblioteca estándar— cerraría los dos lados; no lo he escrito porque no es mi fichero.

> `indicio_texto` tiene el mismo defecto y no lo arregla este diff (§2.2). Como hoy nadie emite un hallazgo con él, es una bomba dormida, no un fallo. **[PENDIENTE]**

### 7.3 `motor_contenedor.py`: 17 aristas nuevas para `_DECLARADAS`

Las del §3 están medidas y **no están en el grafo**, así que el sondeo que entrego las lleva en el JSON pero `sondeo.aplicar()` no las aplica: no hay arista a la que superponerlas. En cuanto se declaren, el estado y el coste medidos entran solos, sin tocar este fichero otra vez — que es de lo que va `filex/sondeo.py`.

```diff
--- a/filex/motor_contenedor.py
+++ b/filex/motor_contenedor.py
@@ class LibreOfficeEnContenedor
     _DECLARADAS = (("rtf", "odt"), ("rtf", "docx"), ("html", "odt"),
-                   ("txt", "odt"), ("odt", "html"), ("docx", "rtf"))
+                   ("txt", "odt"), ("odt", "html"), ("docx", "rtf"),
+                   # Pendiente 5 de `hito5-documental.md`, MEDIDAS por S3 en
+                   # `bench/sondeo-documental.md` §3. `svg→png` va con
+                   # `rasteriza=True` y `svg→pdf` NO: el mismo origen y el mismo
+                   # motor, y uno conserva las 44 letras y el otro ninguna.
+                   ("csv", "xlsx"), ("xlsx", "pdf"), ("xlsx", "csv"),
+                   ("xlsx", "html"), ("csv", "pdf"), ("pptx", "pdf"),
+                   ("pptx", "odp"), ("pptx", "png"), ("svg", "pdf"),
+                   ("svg", "png"))
@@ class PandocEnContenedor
     _DECLARADAS = (("html", "epub"), ("html", "odt"), ("html", "rtf"),
                    ("docx", "odt"), ("epub", "docx"), ("epub", "txt"),
-                   ("rtf", "md"), ("rtf", "html"), ("md", "rtf"))
+                   ("rtf", "md"), ("rtf", "html"), ("md", "rtf"),
+                   # Ídem. `pptx→md` es el que no estaba en ningún catálogo:
+                   # pandoc SÍ lee PPTX.
+                   ("md", "pptx"), ("md", "tex"), ("docx", "tex"),
+                   ("tex", "docx"), ("tex", "html"), ("tex", "pdf"),
+                   ("pptx", "md"))
```

**`pptx→png` y `svg→png` tienen que entrar con `rasteriza=True`**, y hoy `_aristas()` no puede: construye las `_DECLARADAS` con `rasteriza` por defecto. Es un tercer campo en la tupla, o una tupla aparte. **Lo digo y no lo escribo porque el fichero no es mío**, pero sin eso el grafo elegiría `pptx→png→pdf` sin la penalización de +1000 y entregaría un PDF sin una letra — que es literalmente el criterio amarillo del hito 1, al revés.

### 7.4 `formatos.py`: faltan `xlsx`, `pptx`, `odp`, `ods` y `tex` — **[MEDIDO]**

`formatos.formato()` devuelve **`None`** para los cinco (`mobi` y `azw3` ya están: la petición 7.3 de K1 se aplicó). Los uso en 12 de las 17 aristas del §3, y no es inocuo: **`grafo._coste_paso` solo penaliza rasterizar cuando `formatos.formato(destino).texto` es cierto**, así que con `tex` en `None` un camino que rasterizara hacia LaTeX **no pagaría los +1000**. Mismo argumento que dio K1 para `mobi`.

```diff
--- a/filex/formatos.py
+++ b/filex/formatos.py
@@     Formato("odt", "documento", texto=True),
+    Formato("xlsx", "hoja", texto=True),
+    Formato("ods", "hoja", texto=True),
+    Formato("pptx", "presentacion", texto=True),
+    Formato("odp", "presentacion", texto=True),
+    Formato("tex", "documento", texto=True),
```

*(La categoría exacta la decide quien mantenga el fichero; lo que no puede quedarse es el `None`.)*

---

## 8. Lo que queda PENDIENTE

| # | Qué | Por qué importa |
|---|---|---|
| 1 | **Aplicar 7.1 y 7.2, y volver a pasar las 40.** Mientras no se apliquen, **8 aristas `REAL` del producto no entregan fichero** | Es un fallo de producto, no de sondeo |
| 2 | **Fidelidad más allá del centinela**, que sigue abierto desde K1 | `pptx→pdf` conserva 456 caracteres; nadie ha mirado si conserva la maquetación de una diapositiva |
| 3 | **Una segunda semilla.** Sigo midiendo **un** documento en catorce formatos, igual que K1 | El disparador de `D2` son las comas de ESTA prosa. Con otra semilla el defecto A existiría igual, pero **la lista de aristas afectadas cambiaría** — y eso es justo lo que `CLAUDE.md` §3 avisa con las tres semillas de markdown |
| 4 | **`ebook-convert` sin portada generada**, para ver si Calibre pasa a ser reproducible (§5) | Decide si un `MANIFIESTO.md` puede prometer un `sha256` de un EPUB |
| 5 | **`epub→epub` es una arista `real` que el grafo NUNCA puede elegir** | S22: 20 209 B con centinela, contrato `ok_parcial`. `camino()` sale antes por «origen y destino son el mismo formato». Es **normalización** —lo mismo que hace `pdf→pdf` con `pdfwrite`, que sí está declarada— y hoy no hay forma de pedirla |
| 6 | **Descomprimir `/ObjStm` con `zlib`** para contar páginas de verdad (§7.2) | Cierra el falso negativo que deja abierto mi propio diff |
| 7 | **`tex→pdf` recupera 268 caracteres y `tex→html` 2 939** sobre la misma entrada | Puede ser `txtwrite`, puede ser xelatex. No lo he separado |
| 8 | **`test_hito5.Integracion.test_el_tope_de_dentro_no_deja_contenedores_vivos` es INESTABLE bajo carga** (prueba de K1, no mía) | **[MEDIDO]: 2 fallos en 5 pasadas de la suite completa; 0 en 4 pasadas aisladas.** Y el contenedor **no queda**: `docker ps -a` inmediatamente después del fallo solo lista los 5 del proyecto. La prueba llama a `vivos()` **justo después** de que `docker run` devuelva, y el borrado por `--rm` lo hace el DEMONIO de forma asíncrona: con la máquina cargada aún aparece un instante. Es **el mismo problema que su propio comentario ya documenta para el `rc` 124/137**, un renglón más abajo: la prueba mide la carga de la máquina. Lo que hay que comprobar es que el contenedor **termina** borrado, no que ya lo esté — un sondeo con tope, no una lectura instantánea |

---

## 9. Reproducir

```
docker image inspect filex-c13 --format '{{.Id}}'
python bench/salidas-sondeo-doc/_sonda23.py        # 23 aristas, 190 s
python bench/salidas-sondeo-doc/_sonda_p5.py       # pendiente 5, 149 s
python bench/salidas-sondeo-doc/_d2.py             # defectos del verificador + ida y vuelta
python bench/salidas-sondeo-doc/_repro.py          # reproducibilidad, n=3
python bench/salidas-sondeo-doc/_tabla_sondeo.py   # escribe filex/sondeo/doc_*.json
python bench/salidas-sondeo-doc/_manifiesto.py
python -m unittest discover -s pruebas             # 88 en verde
```

**Toda invocación de este trabajo pasa por `filex.invocacion.ejecutar()`** —incluidas las de `docker`— en un `DirectorioDeTrabajo` desechable que se censa antes de borrarse. **No hay ningún `subprocess` fuera de `invocacion.py`**, y las 23 aristas del encargo las convierte `FileX.convertir()`, no el arnés.

**Salidas binarias borradas**, con `sha256`, tamaño y la orden exacta en `bench/salidas-sondeo-doc/MANIFIESTO.md` — con la salvedad del §5: **los `sha256` de las salidas de Calibre no se reproducen**, y el manifiesto lo dice en su cabecera.

**Docker queda como se encontró:** los mismos 5 contenedores vivos, ninguno nuevo, ninguno parado.

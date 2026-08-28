# La métrica de OCR canónica — censo, coste de cambiarla y decisión

**Agente A7** · rama `integracion-r2` · 2026-08-28
Salidas: `bench/salidas-metrica-ocr/` · arnés modificado: `bench/scripts/ocr_eval.py`

---

## 0. Resumen: qué se decidió y qué costó

**La métrica canónica pasa a ser la ACENTUADA, en su variante `[a-z0-9áéíóúüñ ]`
—la de `ocr_eval_d4.py`—, y la vía ciega se queda accesible tras una bandera.**
El precio, MEDIDO recalculando las **2 917 salidas de OCR que ya están en
disco**:

| | celdas | cambia el número | cambia la conclusión |
|---|---:|---:|---:|
| Informes que usaron el evaluador **ciego** | **628** | **4 (0,6 %)** | **0** |
| — de ellas, `ocr-ppp-nativos.md` (la tabla canónica de 296 celdas) | 296 | **0** | **0** |
| Informes que ya usaron el acentuado de `ocr_eval_d4.py` | 2 279 | — *(ya son esas cifras)* | 0 |
| `invocacion-aristas.md`, que usó el **otro** acentuado | 10 | 3 | 0 |

**Y el hallazgo que no esperaba encontrar, que es el que de verdad importa:
no hay tres métricas, hay tres y son DOS EJES, y el proyecto ha estado
llamando «el evaluador acentuado» a dos cosas que no miden lo mismo.**
`ocr_eval_tildes.py` no sólo conserva los diacríticos: **conserva también la
puntuación**, y ese segundo factor —que nadie declaró nunca— es **el más
grande de los dos**. Adoptarlo a él como canónico habría costado **285 de
628 celdas** en los informes ciegos y habría **cambiado el motor ganador en
21 familias de comparación**, incluida la tabla canónica de cuatro motores de
`ocr-ppp-nativos.md`. **Eso sí habría sido una retractación, y por el
carácter equivocado.** [MEDIDO, §4]

**Corolario para `CLAUDE.md`: la trampa 10 prescribe una regla
(`[a-z0-9áéíóúüñ ]`) y cita un número (6,3 puntos) que NO produce esa regla,
sino la otra** — con la regla que prescribe salen **7,14**. Va en «NO
APLICADAS» (§8), no la toco yo.

---

## 1. El censo: quién usa qué — MEDIDO

### 1.1 Los ficheros: no son tres copias, son 13 ficheros y **tres implementaciones**

`md5sum` sobre todos los `ocr_eval*.py` del repositorio:

| `md5` | ficheros | qué implementa |
|---|---|---|
| `d5b570d3…` | `bench/scripts/ocr_eval.py` | **M1 · ciega.** `NFKD` + descarte de combinantes + `[^a-z0-9 ]` |
| `a75d066c…` | `salidas-corpus-d4/ocr_eval_d4.py` **y sus 4 copias byte a byte** en `salidas-corpus-d5/`, `salidas-k-motor/`, `salidas-ppp-norm/`, `salidas-psm/`, `salidas-phys-multi/` | **M2 · acentuada castellana.** `NFC` + `[^a-z0-9áéíóúüñ ]`. Reporta *las dos* lecturas |
| `9f5dea18…` | `salidas-verificador-gs/ocr_eval_tildes.py` y `salidas-invocacion/ocr_eval_p2.py` | **M3 · acentuada latina + puntuación.** `NFC` + `[^0-9a-zÀ-ɏ .,;:!?¿¡]` |
| `2f1f5240…` | `salidas-k-motor/ocr_eval_km.py`, `salidas-ppp-norm/ocr_eval_pn.py`, `salidas-psm/ocr_eval_psm.py` | **envoltorio de M2.** `import ocr_eval_d4`; añade la referencia `tipico` y `ref_de_nombre` |
| `985cc3a4…` | `salidas-phys-multi/ocr_eval_pm.py` | **envoltorio de M2.** `from ocr_eval_d4 import evaluar`; añade un mapa documento→referencia **cerrado** |

**Cinco `md5` distintos, pero sólo tres métricas**: los dos últimos no
reimplementan nada, importan M2. El inventario del proyecto («hay dos copias
acentuadas») **se queda corto en el recuento y largo en la conclusión**: hay
más ficheros de los que dice y menos métricas, pero las dos que hay **no son
la misma** (§4).

### 1.2 Los informes

| informe | métrica | cómo se declara |
|---|---|---|
| `ocr-ppp-nativos.md` | **M1 ciega** | *«`bench/scripts/ocr_eval.py` sin modificar»*, §9 |
| `ocrmypdf.md` | **M1 ciega** | *«la misma de la fase 2»*, §79 |
| `gpu-fase2.md` | **M1 ciega** | tabla de arneses, §728 |
| `verificador-ghostscript.md` | **M1 y M3, las dos** | M1 para la tabla canónica (§468); M3 para §5.5, la tabla de tildes |
| `corpus-d4.md` | **M2** | §80, §85 |
| `corpus-d5.md` | **M2** | §31-34, con `sha256` |
| `k-por-motor.md` | **M2** | §33-35, §156-160. Dice explícitamente que M3 *«no se ha usado»* |
| `ppp-y-normalizacion.md` | **M2** | §101-115 |
| `psm-y-rasterizador.md` | **M2** | §36-38 |
| `phys-multimotor.md` | **M2** | §26-34 |
| `invocacion-aristas.md` | **M3** | §399: *«`ocr_eval_p2.py`, copia de `ocr_eval_tildes.py`»* |
| `consolidacion-21ago.md`, `consolidacion-3-21ago.md` | **no la declaran** | citan cifras de otros informes; heredan la de origen |
| `contrato-quinto-punto.md` | **NO LA DECLARA** | §426 fija un umbral *«CER con tildes > 50 % = ruido»* y **no dice con qué evaluador**. Es el único que usa la palabra «tildes» sin nombrar fichero |

### 1.3 Los arneses (quién importa qué, medido con `grep` sobre los `import`)

| importa | arneses |
|---|---|
| `from ocr_eval import evaluar` (**M1**) | `salidas-ocr-ppp/20_ocr_lote.py`, `21_docling_lote.py`, `22_docling_img.py`; `salidas-ocrmypdf/30_ocr_cadena.py` y `61_cer_motor.sh` |
| `import ocr_eval as EV_CIEGO` (**M1**) + `import ocr_eval_tildes as EV_TILDE` (**M3**) | `salidas-verificador-gs/ocr_gs.py` — el único que usa dos a la vez |
| `from ocr_eval_d4 import evaluar` (**M2**) | `salidas-corpus-d4/ocr_lote_d4.py`, `docling_lote_d4.py`; `salidas-corpus-d5/tess_lote_d5.py`, `sonda_densidad.py` |
| vía envoltorio (**M2**) | `salidas-k-motor/{ocr,docling,tess}_lote_km.py`, `sonda_tess.py`; `salidas-ppp-norm/{ocr,docling}_lote_pn.py`, `survey_norm.py`; `salidas-psm/tess_psm.py`, `sonda_phys.py`; `salidas-phys-multi/ocr_lote_pm.py`, `tess_pm.py`, `sonda_canales_pm.py` |
| ninguno | `salidas-invocacion/ocr_eval_p2.py` — está en el `MANIFIESTO` con su `sha256` pero **ningún `.py` ni `.sh` del repositorio lo importa**: se usó a mano |

**Lectura del censo: la métrica canónica del proyecto la usan 5 arneses y
3 informes; la «no oficial» M2, 14 arneses y 6 informes.** El arnés compartido
lleva desde el 21/08 siendo minoritario en su propio repositorio.

---

## 2. Qué se recalculó, y el control positivo — MEDIDO

**2 917 ficheros de texto de OCR** en `bench/salidas-*/texto/`, `sidecar/` y
`ocr/`, mapeados a su documento y a su referencia por
`01_inventario.py`. Referencias:

| id | caracteres (normalizados M1 / M2 / M3) | qué es |
|---|---|---|
| `legado` | 79 / 79 / **81** | los cuatro escaneados de fase 1-2. **Ni un diacrítico.** `CLAUDE.md` trampa 9: cuantiza a 1,27 puntos |
| `d4` | 596 / 596 / **608** | `escaneado_d4` y toda la familia d5, que reutiliza su texto. 35 acentuados. Cuantiza a 0,16 |
| `tipico` | 120 / 120 / **122** | `corpus/pdf/tipico_texto.pdf` |
| `acentos_gs` | 98 / 98 / **103** | el fixture de tres frases de `verificador-ghostscript.md` §5.5 |

**Ojo a la tercera columna: M3 cambia el DENOMINADOR.** Es la primera pista de
que M3 no es «M2 con tildes».

**No se pudieron recalcular 7 ficheros** (`d5_limpio__*`, `c13/out/chk.txt`) y
**4 celdas publicadas de `ocr-ppp-nativos.md`** (`docling_torch_cuda_defecto__pppdefecto__*`)
cuyo texto no está en disco. **Y `gpu-fase2.md` no se puede recalcular en
absoluto: `bench/salidas-fase2/` contiene UN fichero, el `MANIFIESTO.md`.**
Sus cifras de CER son las que están y no hay con qué revisarlas. Eso es parte
del coste y va dicho. [MEDIDO]

### 2.1 Control positivo — **no se publica una diferencia sin demostrar que la línea base se reproduce**

1. **`rapidfuzz` ≡ el `lev` en Python puro** de los tres evaluadores: 8 pares
   de prueba, **0 discrepancias**. Si falla, `02_recalculo.py` aborta.
2. **Mi M1 reproduce las cifras PUBLICADAS**: de las **564** celdas que tienen
   `cer_pct` guardado por celda en JSON (`salidas-ocr-ppp/json/*__cer.json` y
   `salidas-ocrmypdf/texto/*__cer.json`), **560 se reproducen exactamente y
   0 discrepan**; las 4 restantes no tienen texto en disco.
3. **Los titulares de los informes M2 salen exactamente de M2**, no de M1 ni de
   M3: el `84,56 %` / `41,78 %` del `--psm` de la trampa 8, el `51,34 %` de
   Ghostscript, el `19,30 / 18,62 / 36,91 / 41,78 / 61,41 %` de los cinco
   motores sobre `d4`, el `25,50 %` / `8,72 %` de `escaneado_d5b`. Y los de
   `invocacion-aristas.md` (`82,89 / 51,15 / 32,10 / 100,00 %`) salen
   **exactamente de M3**.

**Con eso la línea base está probada y las diferencias de §3-§4 son de la
métrica, no mías.**

---

## 3. El coste de cambiar, tabla por tabla — MEDIDO

### 3.1 ¿Cambia el número?

Celdas cuyo CER se mueve al menos 0,01 puntos:

| informe | métrica que publicó | n | **cambian con M2** | máx \|Δ\| | cambian con M3 | máx \|Δ\| |
|---|---|---:|---:|---:|---:|---:|
| `ocr-ppp-nativos.md` | M1 | 296 | **0 (0,0 %)** | **0,00** | 153 (51,7 %) | 2,73 |
| `ocrmypdf.md` | M1 | 317 | **3 (0,9 %)** | 1,27 | 125 (39,4 %) | 2,47 |
| `verificador-ghostscript.md` | M1 + M3 | 15 | **1 (6,7 %)** | 7,14 | 7 (46,7 %) | 15,66 |
| **total informes ciegos** | | **628** | **4 (0,6 %)** | **7,14** | **285 (45,4 %)** | **15,66** |
| `invocacion-aristas.md` | M3 | 10 | *(3 respecto de M3, máx 1,72)* | | — | |
| `corpus-d4.md` … `phys-multimotor.md` | M2 | 2 279 | *(ya son cifras M2: 0 caducan)* | | | |

**Las cuatro celdas que cambian, una por una:**

| celda | M1 (publicado) | M2 | Δ |
|---|---:|---:|---:|
| `salidas-verificador-gs/ocr/acentos_eng.txt` | 9,18 % | **16,33 %** | +7,14 |
| `salidas-ocrmypdf/sidecar/os300__escaneado_d3.txt` | 78,48 % | 79,75 % | +1,27 |
| `salidas-ocrmypdf/sidecar/clean_os300__escaneado_d3.txt` | 78,48 % | 79,75 % | +1,27 |
| `salidas-ocrmypdf/sidecar/deskew_os300__escaneado_d3.txt` | 78,48 % | 79,75 % | +1,27 |

Los tres de `ocrmypdf` son **un solo carácter** sobre una referencia de 79
(1,27 puntos exactos, trampa 9). El de `verificador-ghostscript.md` es el
fixture de tildes, **que ya se publicó con las dos lecturas**: lo que cambia
no es una cifra oculta, es cuál de las dos es la canónica.

### 3.2 ¿Cambia la conclusión?

Una conclusión de este repositorio casi siempre tiene la forma *«sobre el mismo
documento, A es mejor que B»* o *«el óptimo de este eje está en X»*: no depende
del valor del CER, depende del **orden**. `05_conclusiones.py` lo mecaniza:
descompone el nombre de cada fichero en sus factores (`motor`, `k`, `ppp`,
`psm`, `pHYs`, …), forma **1 043 familias** de un solo factor variando con
todo lo demás fijo, y compara el orden bajo cada métrica sobre **21 544 pares**.

Se separan tres cosas que no son lo mismo:

* **inversión estricta** — A<B con una y A>B con la otra. **Esto sí retracta.**
* **empate roto** — A=B con una y A≠B con la otra. **Esto no retracta nada:**
  es resolución que antes no había (la métrica ciega empataba porque no veía).
* **empate creado**.

| | pares | inversiones | empates rotos | familias con **otro ganador** |
|---|---:|---:|---:|---:|
| **M2** frente a M1 | 21 544 | **132 (0,61 %)** | 189 | **52 de 1 043** |
| **M3** frente a M1 | 21 544 | **229 (1,06 %)** | 641 | **100 de 1 043** |

Y desglosado, que es donde está la decisión:

| informe | métrica que publicó | familias | inversiones **M2** | otro ganador **M2** | inversiones **M3** | otro ganador **M3** |
|---|---|---:|---:|---:|---:|---:|
| `ocr-ppp-nativos.md` | **M1** | 78 | **0** | **0** | 4 | **21** |
| `ocrmypdf.md` | **M1** | 154 | **0** | **0** | 2 | **10** |
| `corpus-d4.md` | M2 | 58 | 81 | 2 | 108 | 5 |
| `corpus-d5.md` | M2 | 161 | 6 | 7 | 10 | 17 |
| `k-por-motor.md` | M2 | 80 | 21 | 14 | 37 | 19 |
| `ppp-y-normalizacion.md` | M2 | 93 | 22 | 8 | 35 | 12 |
| `psm-y-rasterizador.md` | M2 | 185 | 2 | 4 | 28 | 15 |
| `phys-multimotor.md` | M2 | 234 | 0 | 17 | 5 | 1 |

**Léase la primera fila dos veces.** Las columnas M2 de los dos informes que
usaron la métrica ciega son **cero y cero**: adoptar M2 no retracta ni un
hallazgo suyo. Las columnas de los informes M2 dicen lo contrario — lo que
mide es cuánto se habría perdido si el proyecto hubiera usado la ciega en
ellos, es decir **cuánta razón tenían al no usarla**: hasta **21 inversiones y
14 cambios de ganador** en `k-por-motor.md`, que es justo el informe del que
salen los `k` publicados en `CLAUDE.md` trampa 8.

**Tres conclusiones que NO se mueven con ninguna métrica, y conviene decirlo:**

* **`phys-multimotor.md` §: «los tres motores neuronales devuelven un solo
  `md5` de texto en las 18 filas, recorrido de CER 0,00».** Es una afirmación
  sobre **textos idénticos**: ninguna métrica puede cambiarla. Invariante por
  construcción.
* **Las cinco celdas `rc=0xC0000142` de la trampa 25** y todo el argumento de
  «0 bytes no es lo mismo que silencio»: no es una cifra de CER.
* **El `pHYs` y el `--psm`**: sus 33 y 42,78 puntos son cifras M2 y se quedan
  como están.

---

## 4. Las tres copias comparadas — y el problema es peor de lo que dice el inventario

### 4.1 No se diferencian en una cosa, se diferencian en DOS

| | diacríticos | puntuación `. , ; : ! ? ¿ ¡` | conjunto |
|---|---|---|---|
| **M1** `ocr_eval.py` | **no** (NFKD + descarte) | **no** | `[a-z0-9 ]` |
| **M2** `ocr_eval_d4.py` | **sí** | **no** | `[a-z0-9áéíóúüñ ]` |
| **M3** `ocr_eval_tildes.py` | **sí** | **sí** | `[0-9a-zÀ-ɏ .,;:!?¿¡]` |

Con esas tres esquinas no se puede repartir la culpa: **falta la cuarta**. Se
construyó (métrica auxiliar `A=no/B=sí`, **no se propone como canónica**: existe
sólo para poder atribuir) y se midió el 2×2 completo sobre las 2 917 celdas:

| efecto | n | celdas iguales | mediana | máx \|Δ\| |
|---|---:|---:|---:|---:|
| **sólo acentos** (M1→M2) | 2 917 | 1 431 | +0,168 | **7,14** |
| **sólo puntuación** (M1→auxiliar) | 2 917 | 657 | **+0,454** | **15,66** |
| ambos (M1→M3) | 2 917 | 645 | +0,822 | 15,66 |

**La puntuación pesa MÁS que los acentos: mueve 2 260 celdas frente a 1 486, y
su peor caso es más del doble.** Y sobre el corpus **legado**, cuya referencia
no tiene un solo diacrítico:

| efecto, sólo corpus legado (n=1 295) | celdas que se mueven | máx \|Δ\| |
|---|---:|---:|
| sólo acentos | **14** | 2,53 |
| sólo puntuación | **694** | **15,66** |

**Es decir: casi todo lo que `ocr_eval_tildes.py` añade sobre las tablas
históricas del proyecto no son tildes. Son puntos y comas.**

### 4.2 El caso que lo demuestra sin discusión, y está citado en `CLAUDE.md`

`CLAUDE.md` §5 dice: *«a Tesseract, al que R1 le asigna 100 ppp sobre
`escaneado_d2` y le cuesta **32,10 puntos**»*. Esa cifra viene de
`invocacion-aristas.md`, medida con M3. Recalculada:

| celda | M1 | M2 | M3 (publicado) |
|---|---:|---:|---:|
| `salidas-invocacion/…/escaneado_d2.txt` | 30,38 % | **30,38 %** | **32,10 %** |

`escaneado_d2` es del corpus legado: **su referencia no tiene ni una tilde**.
M1 y M2 coinciden al decimal. **Los 1,72 puntos de diferencia del número que
`CLAUDE.md` cita son 100 % puntuación y 0 % acentos** — en un párrafo que
habla de resolución de OCR. [MEDIDO]

### 4.3 Y por qué M3 no puede ser la canónica: cambia quién gana

Bajo M3, en `ocr-ppp-nativos.md` —la tabla canónica de cuatro motores— el
conjunto ganador cambia en **21 familias**. Ejemplos literales del
`conclusiones_tildes.json`:

```
escaneado_d1 : ganan {doclingimg, easyocr, easyocr_t, paddleocr}
             -> ganan {doclingimg, paddleocr, paddleocr_t, rapidocr}
escaneado_d2 : ganan {docling, paddleocr, paddleocr_t}   (4 inversiones estrictas)
             -> gana  {docling}
escaneado_d3 : gana  {docling}
             -> ganan {docling, easyocr, easyocr_t}
```

**EasyOCR entra y sale del podio según se cuente o no el punto final.**
Eso no es afinar una cifra: es reescribir la conclusión de la tabla de
motores del proyecto, y por un carácter que la trampa 10 nunca mencionó.

Y hay un efecto secundario que ninguna tabla sobrevive: de las **650 celdas
que valen 0,00 % con la métrica ciega**, dejan de estar a cero **88 con
acentos** (todas en informes que ya usan M2, así que ya lo están) y **125 con
puntuación** — estas últimas **incluyen `ocr-ppp-nativos.md` y `ocrmypdf.md`**.
El «0,0 %» de una tabla publicada es una afirmación fuerte y M3 la rompe en
sitios donde nadie escribió mal una tilde.

### 4.4 El mecanismo, sondeado y no deducido

Antes de publicar «las 296 celdas no se mueven» había que saber por qué, porque
hay dos explicaciones incompatibles: (a) no hay acentos en esas salidas, o (b)
los hay y la coincidencia es casual. Se contaron los caracteres:

| referencia | celdas | celdas con algún acento | acentos | celdas con puntuación |
|---|---:|---:|---:|---:|
| `legado` | 1 295 | **65** | 106 | 911 |
| `d4` | 1 604 | **1 496** | 28 965 | 1 545 |
| `acentos_gs` | 3 | 3 | 23 | 3 |
| `tipico` | 15 | 0 | 0 | 15 |

**Explicación (a) es FALSA:** 65 salidas del corpus legado sí traen acentos.
Lo que pasa es que son 106 caracteres repartidos en 1 295 ficheros y sólo 3
celdas se mueven — y las tres exactamente 1,27 puntos, un carácter. **La
inmunidad de la tabla canónica no es que no haya acentos: es que la referencia
no los tiene y las alucinaciones acentuadas del motor son raras.** [MEDIDO]

### 4.5 La cifra de la trampa 10, reproducida y corregida

`verificador-ghostscript.md` §5.5, fixture de tres frases, recalculado:

| idioma | M1 (publicado 9,2 / 2,0) | **M2** | **M3 (publicado 15,5 / 1,9)** |
|---|---:|---:|---:|
| `spa` | 2,04 % | **2,04 %** | 1,94 % |
| `eng` | 9,18 % | **16,33 %** | 15,53 % |
| `spa+eng` | 2,04 % | **2,04 %** | 1,94 % |

Reproduce la tabla publicada al decimal. **Y aparecen dos cosas nuevas:**

1. **Los «6,3 puntos» de la trampa 10 son un número de M3. Con la regla que la
   propia trampa prescribe (`[a-z0-9áéíóúüñ ]`, es decir M2) son 7,14.**
2. **El «−0,1» de `spa`** que la tabla publica como si la métrica ciega
   *sobreestimara* el error **no existe**: bajo M2 es exactamente 0,00. Ese
   −0,1 es el denominador de M3 (98 → 103 caracteres), no una lectura mejor.

---

## 5. La decisión, y lo que cuesta

### 5.1 Qué se hizo

`bench/scripts/ocr_eval.py` **modificado** (es arnés compartido; cambiarlo es
el encargo). Las tres condiciones que `CLAUDE.md` §1 impone quedan cubiertas:

* **La vía ciega no se borra, se pone tras una bandera.**
  `evaluar(t, "ciego")`, `python ocr_eval.py --ciego f.txt`, y `norm(...)`
  **sigue apuntando a la normalización ciega sin un solo cambio** — la importa
  `ocr_gs.py` para normalizar su propia referencia y cambiársela por debajo
  habría alterado cifras suyas en silencio.
* **El fichero declara qué mide y desde cuándo.** Cabecera con la regla, la
  fecha (`METRICA_DESDE = "2026-08-28"`), el porqué y el precio medido.
* **El resultado se autodeclara.** `evaluar()` devuelve **siempre las dos
  lecturas** (`cer_acentos_pct`, `cer_ciego_pct`), la clave `metrica` que dice
  cuál está copiada en `cer_pct`, y `puntos_que_ocultaba_la_ciega`. **Una tabla
  de CER de este repositorio sin esa clave es una tabla que no se puede juntar
  con otra**, que es exactamente el problema que motivó el encargo.

### 5.2 La regresión del arnés compartido — VERDE

| | resultado |
|---|---|
| **Nivel A**, las 2 917 celdas: la vía **ciega** da lo mismo que el fichero original (`ocr_eval_ciego.py`, copia byte a byte tomada *antes* de tocarlo) | **2 917 / 2 917**, 0 discrepancias |
| **Nivel A**: la vía **canónica** da exactamente `ocr_eval_d4.py::norm_acentos` | **2 917 / 2 917**, 0 discrepancias |
| **Nivel B**, 118 celdas repartidas por informe: el **diccionario entero** de `evaluar()`, `detalle` por frase incluido | **118 / 118**, 0 discrepancias |
| API (`norm`, `norm_ciega`, `norm_acentos`, `lev`, `evaluar`, `ESPERADO`, `REFERENCIA`), `norm` sigue siendo la ciega, `lev` sin cambios | **OK** |

*(El nivel B es una muestra y no las 2 917 por coste: el `detalle` por frase es
una ventana deslizante con `lev` en Python puro, O(|salida|·|frase|²), y sobre
el corpus entero no termina en un tiempo razonable — se midió intentándolo.)*

**Suite del proyecto: `231 passed, 6 skipped, 1 failed`** antes y después, con
el mismo y único rojo esperado
(`test_ningun_motor_disponible_tiene_el_sondeo_caducado`, que es de otro
agente). El encargo no tocó `filex/`.

### 5.3 Las cifras publicadas que quedan CADUCAS

Cortas, y ninguna cambia una conclusión. **Yo no las corrijo: no son mis
ficheros.**

| fichero | qué caduca | quién debería tocarlo |
|---|---|---|
| `bench/verificador-ghostscript.md` §5.5 | la tabla de 3 filas pasa a `spa` 2,04 / `eng` **16,33** / `spa+eng` 2,04, y los **«6,3 puntos»** pasan a **7,14**. El **«−0,1»** de `spa` desaparece (es 0,00) | el autor de G5 |
| `bench/ocrmypdf.md` | 3 celdas de sidecar: 78,48 % → **79,75 %**. Ninguna tabla del informe cambia de orden | el autor de ese informe |
| `bench/invocacion-aristas.md` §399 «Caso 5» | publicó con M3: `d2` 32,10 → **30,38**, `d4` 82,89 → **82,72** y 51,15 → **50,34**. **Y hay algo peor que las cifras: el punto 3 compara su 51,15 % (M3) contra el 19,30 / 18,62 / 36,91 / 41,78 / 61,41 % de `corpus-d4.md` (M2). Es una comparación entre métricas distintas.** Con M2 en las dos, Tesseract queda en **50,34 %** y **la conclusión —«el peor de los cinco»— se mantiene** | el autor de P2 |
| `CLAUDE.md` §5 | *«le cuesta 32,10 puntos»* → **30,38** con la canónica nueva (§4.2) | el integrador, vía §8 |
| `CLAUDE.md` trampa 10 | prescribe M2 y cita un número de M3 (§8) | el integrador, vía §8 |
| `bench/ocr-ppp-nativos.md` | **nada.** 296 de 296 celdas idénticas | — |
| `bench/gpu-fase2.md` | **no verificable**: sus salidas de texto ya no existen (§2) | — |

### 5.4 Lo que NO se hizo, y por qué

* **No se adoptó `ocr_eval_tildes.py`** pese a ser el más «completo». Su
  factor extra —la puntuación— es defendible por sí mismo (un punto que falta
  *es* un error de OCR), **pero es una decisión distinta, con un precio 71 veces
  mayor en celdas y que cambia ganadores**, y no puede colarse dentro de la
  palabra «acentuada». **Si alguien la quiere, que la mida como decisión propia:
  ya está el 2×2 hecho en `07_factorial.py` y la esquina que faltaba
  construida.** [PENDIENTE, a propósito]
* **No se tocaron `ocr_eval_d4.py` ni `ocr_eval_tildes.py`.** Son de sus
  autores. Ahora que la canónica coincide con M2, **la deuda real es de
  BORRADO, no de código**: `ocr_eval_d4.py` y sus 5 copias podrían pasar a
  importar el arnés compartido. No lo hago yo: son 6 directorios ajenos.
  [PENDIENTE]
* **No se usó la GPU ni se tomó el lock.** El encargo es aritmética sobre texto
  ya en disco: 2 917 celdas × 3 métricas en ~40 s de CPU.

### 5.5 ¿Y si la respuesta hubiera sido «no compensa»?

Era una salida legítima y estuvo cerca de serlo por el lado contrario al que
esperaba: **la métrica ciega no está escondiendo puntos en las tablas
publicadas** —esconde 4 celdas de 628—, así que el argumento «hay que cambiarla
porque las cifras están mal» es **débil**. Lo que sostiene el cambio no es el
tamaño del error escondido, es **la comparabilidad**: hoy hay dos tablas de CER
del mismo repositorio medidas con evaluadores distintos que **no se pueden
juntar sin leerse el código**, y ya hay un caso publicado donde se juntaron
igualmente (`invocacion-aristas.md` §399, punto 3). **El cambio cuesta 4 celdas
y cierra eso.** Ése es el argumento, y conviene que quede escrito porque es más
honesto que el que trae la trampa 10.

---

## 6. Cumplimiento de las reglas

| regla | cómo |
|---|---|
| Un fichero de informe por agente | `bench/metrica-ocr.md`. Ningún otro `.md` de `bench/` tocado |
| Marcar MEDIDO / PENDIENTE | cada afirmación de §1-§5 |
| Dos intentos por problema | la regresión completa sobre 2 917 celdas **no terminó** (ventana deslizante cúbica); segundo intento: dos niveles (todas las celdas para lo que se publica, muestra de 118 para el diccionario entero). Documentado en §5.2 |
| Timeouts explícitos | `timeout` en todas las órdenes; ninguna tanda quedó viva |
| Heredocs (trampa 19) | **ningún script generado por shell.** Los 8 `.py` escritos con la herramienta de escritura. Con clases de caracteres Unicode (`[^a-z0-9áéíóúüñ ]`, `À-ɏ`) esto no era opcional |
| Sin GPU, sin lock | §5.4 |
| Directorio desechable y censo (R21) | no se invocó ningún motor externo, así que no hay `cwd` que ensuciar. Censo al terminar: `git status` = `bench/scripts/ocr_eval.py` modificado + `bench/salidas-metrica-ocr/` nuevo. **0 ficheros inesperados en la raíz** |
| No versionar salidas grandes regenerables | `inventario.json` (854 KB) y `factorial.json` (760 KB) borrados, con su orden exacta en el `MANIFIESTO.md` |
| Corpus LFS (trampa 34) | `git lfs checkout` al empezar: `corpus/imagen/tipico.png` = **42 855 B**, no 130 |
| Arneses compartidos | `mcp_probe_bin.py`, `mcp_probe.py`, `harness.sh`, `referencia.json`, `ocr_motor.py` **ni abiertos**. `ocr_eval_d4.py` y `ocr_eval_tildes.py` **copiados**, no editados |

---

## 7. Pendientes que deja este informe

1. **`bench/contrato-quinto-punto.md` §426 fija un umbral operativo (*«CER con
   tildes > 50 % = ruido»*) sin declarar evaluador.** Con M2 y M3 el mismo
   texto puede quedar a los dos lados de 50 en la zona de degradación. **Hay
   que averiguar cuál usó y anotarlo.** [PENDIENTE]
2. **`gpu-fase2.md` no es auditable**: sus salidas de OCR no están en disco.
   Cualquier cifra suya que se cite hoy es de fe. [PENDIENTE]
3. **Las 5 copias de `ocr_eval_d4.py` y las 4 de sus envoltorios podrían
   colapsar** ahora que la canónica coincide con ellas. Es trabajo de sus
   autores. [PENDIENTE]
4. **`salidas-invocacion/ocr_eval_p2.py` no lo importa ningún script**: la
   tanda que produjo el «Caso 5» no es reproducible con una orden. [PENDIENTE]
5. **Decidir la puntuación como decisión propia**, con el 2×2 ya construido.
   [PENDIENTE]

---

## 8. Trampas propuestas — **NO APLICADAS** (numeradas desde la 52)

> No las aplico yo. Y **la trampa 10 hay que corregirla**: la propuesta 52
> dice cómo, pero **no la he tocado**.

**52. La trampa 10 prescribe una regla y cita el número de OTRA — MEDIDO**
(`bench/metrica-ocr.md` §4.5). Dice *«conserva `[a-z0-9áéíóúüñ ]`»* (que es
`ocr_eval_d4.py`) y a continuación *«oculta 6,3 puntos»*, pero **ese 6,3 lo
produjo `ocr_eval_tildes.py`, que además conserva la puntuación**. Con la regla
que la propia trampa prescribe salen **7,14**. Y su segundo ejemplo, el
*«−0,1»* de `spa` del informe de origen, **no existe con la regla prescrita**:
es 0,00, y el −0,1 era el denominador (98 → 103 caracteres). **Corrección
propuesta:** *«oculta **7,14** puntos con `[a-z0-9áéíóúüñ ]` (6,35 si además se
conserva la puntuación) sobre `eng` en un fixture de tres frases, y **4 celdas
de las 628 publicadas con la métrica ciega**; la métrica canónica es la
acentuada desde el 2026-08-28 y la vía ciega vive tras `--ciego`»*.

**53. «El evaluador acentuado» son DOS métricas, y el factor grande no son los
acentos: es la PUNTUACIÓN — MEDIDO** (ídem §4, 2×2 completo sobre 2 917
celdas). `ocr_eval_d4.py` conserva `[a-z0-9áéíóúüñ ]`; `ocr_eval_tildes.py`
conserva además `. , ; : ! ? ¿ ¡` **y todo el bloque latino `À-ɏ`**. Separados,
el factor acentos mueve **1 486 celdas, mediana +0,168, máx 7,14** y el factor
puntuación **2 260 celdas, mediana +0,454, máx 15,66**. **Sobre el corpus
legado, cuya referencia no tiene un solo diacrítico, los acentos mueven 14
celdas de 1 295 y la puntuación 694.** Consecuencia: **adoptar
`ocr_eval_tildes.py` habría cambiado el motor ganador en 21 familias de
`ocr-ppp-nativos.md`** —EasyOCR entra y sale del podio según se cuente el punto
final— y habría roto **125 de las 650 celdas que valen 0,00 %**. **Cuando dos
normalizaciones difieran, cuenta los EJES antes de llamarlas variantes de lo
mismo, y construye la esquina que falta del factorial: con tres esquinas no se
puede atribuir nada.**

**54. Una cifra citada entre informes puede venir de otra métrica, y el texto
no lo dice — MEDIDO** (ídem §4.2, §5.3). `CLAUDE.md` §5 cita *«32,10 puntos»*
sobre `escaneado_d2`; ese documento **no tiene ni una tilde en su referencia** y
la cifra sale de M3: los **1,72 puntos** que la separan de la canónica son
**100 % puntuación**. Peor: `invocacion-aristas.md` §399 punto 3 pone el
**51,15 % (M3)** de Tesseract al lado del **19,30 / 18,62 / 36,91 / 41,78 /
61,41 % (M2)** de los otros cinco motores **en la misma frase**. *(La conclusión
aguanta —con M2 en las dos, 50,34 % sigue siendo el peor—, pero aguantó por
suerte.)* **Una tabla de CER declara su evaluador o no es comparable, y el sitio
donde declararlo es el propio resultado**: por eso `evaluar()` devuelve ahora
`metrica` en cada celda.

**55. Un «no se mueve» necesita saber POR QUÉ no se mueve — MEDIDO** (ídem
§4.4). Las 296 celdas de `ocr-ppp-nativos.md` dan CER idéntico con la métrica
ciega y con la acentuada, y la explicación cómoda —*«esas salidas no tienen
acentos»*— es **FALSA**: 65 de las 1 295 salidas del corpus legado sí los
traen, 106 caracteres. Lo que ocurre es que **la REFERENCIA no los tiene** y las
alucinaciones acentuadas son raras, así que sólo 3 celdas se mueven, y las tres
exactamente **1,27 puntos = un carácter** (trampa 9). **Un resultado nulo con la
explicación equivocada es un resultado nulo que se cae en cuanto cambie el
corpus.**

**56. Una regresión que no termina no es una regresión, y el arreglo no es
esperar — MEDIDO** (ídem §5.2). Comprobar el diccionario entero de `evaluar()`
sobre las 2 917 celdas **no termina**: el `detalle` por frase es una ventana
deslizante con `lev` en Python puro, **O(|salida|·|frase|²)**, y son ~24 G
operaciones. **Se parte en dos niveles con criterio, no por comodidad:** todas
las celdas para **lo que se publica** (normalización + CER global) y una
muestra estratificada de 118 para el resto. **Di cuál de los dos niveles
respalda cada afirmación** — «2 917 / 2 917» y «118 / 118» no son la misma
garantía y mezclarlas es exactamente lo que la trampa 38 llama medir la carrera
equivocada.

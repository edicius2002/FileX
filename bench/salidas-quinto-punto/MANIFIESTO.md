# `bench/salidas-quinto-punto/` — datos crudos del encargo P3

**Agente P3** (C9 + C10 + C11 + C12). 21 de agosto de 2026.
Informe: `bench/contrato-quinto-punto.md`.

**355 KB, todo texto.** Los binarios generados están **borrados**; abajo van con
`sha256`, tamaño y **la orden exacta que los reproduce**. Nada de lo que hay aquí
se escribió fuera de este directorio: los directorios de trabajo desechables
(`tmp/`) se borran al terminar cada subcomando, y la raíz del repositorio quedó
limpia (`git status` sin ficheros nuevos ajenos a este encargo).

---

## Instrumentos

| Fichero | Qué es |
|---|---|
| `medir_p5.py` | El banco de medida. **Copia adaptada** de `bench/salidas-verificador-gs/medir_gs.py`, que es de V1 y no se toca. Once subcomandos: `coste`, `ordenes`, `fuga`, `multi`, `i9`, `familia`, `p9`, `v2`, `txtvacio`, `contrato53`, `fallos5`. Lleva **los dos testigos de ruido** (monohilo para la deriva, lanzamiento de proceso para el nivel) |
| `txtvacio2.py` | Sonda dedicada al `txtwrite` que devuelve vacío: 250 ejecuciones × 3 rutas (tubería antigua, fichero, sonda actual) sobre el mismo PDF |
| `fixtures/*.svg` | Tres SVG de control escritos a mano para I9: sin `<text>`, con texto de 2 caracteres y con `text-anchor="middle"` |

## Resultados

| Fichero | Contenido | Sección del informe |
|---|---|---|
| `coste_p5.json` | Coste del punto 5: censo de 1/2/10/100/1000 entradas, `mtime` del directorio, y el contrato completo en cinco configuraciones. Mediana n=15 | §2 |
| `ordenes39.json` | Las **39 órdenes del patrón oro reejecutadas** en directorio desechable con censo antes/después. Falsos positivos del punto 5 y recuento de salidas multifichero | §3 |
| `fuga.json` | Los **dos casos reproducidos por E1** (DASH y `magick → .html`) con el veredicto de 4 puntos y el de 5 | §3.1 |
| `multi.json` | Cuatro salidas **legítimamente multifichero** (HLS, secuencia `%03d` de ffmpeg, secuencia `%d` de Ghostscript, DASH declarado en el pedido) | §3.2 |
| `contrato53.json` | Las 53 salidas del patrón oro por el contrato de **cinco** puntos, 2 motores × 2 modos de censo | §3.3 |
| `fallos5.json` | Los 5 fallos documentados con el contrato de cinco puntos, 2 motores. **12 de 12** | §3.3 |
| `i9.json` | Discriminación de I9 sobre 6 casos y su coste por tamaño de raster, con la comparación contra `magick`. Mediana n=9 | §4 |
| `familia.json` | Los 10 miembros/controles de la familia «el envase es correcto y el contenido no está», con qué los atrapa | §5 |
| `p9.json` | **32 capas OCR reales** (8 documentos × 2 idiomas × 2 resoluciones) y **19 capas de texto legítimo**, con las señales y el acuerdo `spa`/`eng` | §6 |
| `texto/*.txt` | El texto extraído de cada una de las 32 capas OCR. Es lo que hace reanalizable el §6 sin volver a pasar el OCR | §6 |
| `v2.json` | La suite de fidelidad completa sobre las 53 salidas, **con y sin V2**, con el detalle por salida | §7 |
| `txtvacio.json` | Primera tanda: 60 ejecuciones × 3 PDF × 2 rutas | §8 |
| `txtvacio2.json` | Tanda decisiva: **250 ejecuciones × 3 rutas** sobre `corpus/pdf/tipico_texto.pdf` | §8 |

---

## Binarios borrados, con su orden de reproducción

Todos se regeneran desde el repositorio. Ninguno se versiona.

| Fichero | Bytes | `sha256` | Orden exacta |
|---|---:|---|---|
| `fixtures/e1_800.png` | 144 574 | `9921bc7b7e668cb5978c55509d1af90971162b21f111d5f348dbcb3dc0dd1833` | `magick -density 144 bench/salidas-aristas/c8/in/e1.svg -resize 800x400 fixtures/e1_800.png` |
| `fixtures/e1_1920.png` | 434 323 | `9bf84c98393d4c3d3ce8b3a61e82b404b7d233a490e92c3ffe37fb8ccf183ddc` | `magick -density 345 bench/salidas-aristas/c8/in/e1.svg -resize 1920x960 fixtures/e1_1920.png` |
| `fixtures/sin_texto.png`, `texto_corto.png`, `texto_medio.png` | 2 577 / 760 / 1 186 | — (se conservan: 4,4 KB) | `python medir_p5.py i9` los regenera |
| `tmp/**` (32 PDF con capa OCR, 20 PNG de secuencia, segmentos DASH y HLS, PDF fabricados) | ~9 MB | — | cada subcomando de `medir_p5.py` los crea en `tmp/` y **los borra al empezar el siguiente**; ninguno sobrevive a la tanda |

**Reproducción completa**, en este orden y desde `bench/salidas-quinto-punto/`:

```
python medir_p5.py coste        #  ~3 min
python medir_p5.py ordenes      #  ~2 min   (reejecuta las 39 ordenes del patron oro)
python medir_p5.py fuga         #  ~15 s
python medir_p5.py multi        #  ~30 s
python medir_p5.py i9           #  ~4 min
python medir_p5.py familia      #  ~1 min
python medir_p5.py p9           #  ~8 min   (32 pasadas de OCR con Ghostscript)
python medir_p5.py v2           #  ~2 min
python medir_p5.py contrato53   #  ~3 min
python medir_p5.py fallos5      #  ~20 s
python txtvacio2.py 250         #  ~4 min
```

`p9` necesita `TESSDATA_PREFIX`; el banco lo fija **solo en el entorno del
proceso hijo**, apuntando a `C:\Program Files\PDFgear\tessdata` (trae `eng` y
`spa`). **No se ha tocado ninguna variable de entorno del sistema.**

## Lo que este directorio NO contiene

- **Ninguna salida de otro agente.** No se ha escrito en `bench/salidas-aristas/`
  (se lee), ni en `bench/salidas-referencia/` (patrón oro), ni en
  `bench/salidas-verificador-gs/` (arnés de V1), ni en `corpus/`.
- **Ningún documento maestro** ni ningún informe que no sea
  `bench/contrato-quinto-punto.md`.



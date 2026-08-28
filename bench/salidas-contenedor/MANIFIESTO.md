# `bench/salidas-contenedor/` — agente Q, a4

Todo lo de aquí es **texto** y se versiona (`CLAUDE.md` §6). No hay salidas
binarias regenerables: los contenedores que producen estas medidas se matan
dentro de la propia tanda y `docker ps -a` queda igual antes y después.

| Fichero | Qué es | Cómo se reproduce |
|---|---|---|
| `sonda_id.py` | Sonda de semántica de Docker: `--cidfile` frente a `--name` (S1–S5) y el estado `Created` (S6). Imagen `alpine:latest` | `python bench/salidas-contenedor/sonda_id.py` |
| `sonda_id.json` | Su salida. La decisión de diseño del a4 sale de aquí | — |
| `arnes_contenedor.py` | Arnés de medidas M1–M7. Imagen `ghcr.io/c4illin/convertx:latest` | `python bench/salidas-contenedor/arnes_contenedor.py` |
| `a4_medidas.json` | **Tanda publicada**, M1–M7, n=9, con testigos de ruido | ídem |
| `a4_medidas_barrido_incondicional.json` | Tanda anterior, con `_barrer_contenedor_de` disparándose SIEMPRE en vez de solo cuando el `kill` falla. Se conserva porque es el A/B que justifica la condición | *(el código ya no hace esto; para reproducirla hay que quitar el `if not muertos:` de `invocacion.cancelar_hilo`)* |
| `a4_m7_estado_created.json` | Solo M7. Se conserva porque es la tanda en la que el estado **`Created`** aparece en la ventana de cancelación (1 de 9 en `sin_nada`). Es intermitente: la tanda publicada da 0 de 9 | `python bench/salidas-contenedor/arnes_contenedor.py --saltar=m1,m2,m3,m4,m5,m6` |

Selección de bloques del arnés:

    python bench/salidas-contenedor/arnes_contenedor.py --saltar=m1,m3,m6

Bloques: `m1` control, `m2` remedio, `m3` coste de identificar, `m4` carrera de
arranque, `m5` vecino, `m6` coste normal, `m7` espera frente a barrido.

**Censo de contenedores.** Antes y después de cada tanda, `docker ps -a` da los
**mismos 6** contenedores permanentes del proyecto (`filex-convertx`,
`filex-snapotter`, `filex-snapotter-pg`, `filex-snapotter-redis`,
`filex-gotenberg8`, `filex-gotenberg`). Huérfanos con la forma que acuña FileX
(`filex-<pid>-<uuid4>`): **0**. El arnés lo comprueba solo y lo deja en
`huerfanos_de_filex`.

**Sin GPU.** Ninguno de los dos ficheros toca la tarjeta ni toma el lock.

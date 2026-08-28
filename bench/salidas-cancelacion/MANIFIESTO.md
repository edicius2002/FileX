# MANIFIESTO — `bench/salidas-cancelacion/`

Salidas del agente N-a (C34 y N6). Todo es texto: no hay binarios que borrar.
El informe que las lee es `bench/cancelacion-y-servicio.md`.

| Fichero | Bytes | `sha256` (32 primeros) |
|---|---:|---|
| `arnes_cancelacion.py` | 16 147 | `d68321e20e5715be9384d6cdc2e9dea9` |
| `c34_carrera_arranque.json` | 4 654 | `8a87b76c58d9bf305c90e25761827255` |
| `c34_medidas.json` | 4 299 | `db4043adc02c680947b2bcb6dd3e1818` |

## Órdenes exactas que las reproducen

Desde la raíz del repositorio (o del *worktree*), **sin GPU** y con Docker en pie:

```
python bench/salidas-cancelacion/arnes_cancelacion.py --n 9
```

Escribe `c34_medidas.json` con las cinco medidas (M1 invocación, M2 servicio,
M3 contenedor, M4 coste del registro, M5 contenedor extremo a extremo).

Para una submedida sola:

```
python bench/salidas-cancelacion/arnes_cancelacion.py --n 9 --saltar m1,m2,m3,m4
```

`c34_carrera_arranque.json` es una tanda **anterior al último arreglo** y no se
regenera: se conserva porque contiene el hallazgo que lo motivó
(`m5.contenedores_vivos_despues = [1,0,0,0,0,0,0,0,0]`). Reproducirlo exige
quitar `ESPERA_CONTENEDOR` de `filex/invocacion.py`, es decir volver a abrir la
carrera; el fichero está para no tener que hacerlo.

## Salvedades de medición

- Tanda etiquetada **`SUCIA`**: la sesión de escritorio remoto está activa a
  propósito. Es estructural (`CLAUDE.md` §3).
- Testigos de la tanda publicada: deriva **0,798** (sin deriva) y nivel
  **34,92 → 26,97 ms** con `ffprobe -version`, los dos dentro de lo normal de
  esta máquina.
- Las cifras **relativas** dentro de una tanda son comparables; las absolutas
  entre tandas, no. Las tres tandas que se corrieron dan ×27,7–33,5 en M1 y
  ×77,8–91,3 en M2: el orden de magnitud es estable, la centena de milisegundos
  no.
- Ninguna medida usa la GPU y ninguna toma el lock: no le hace falta.

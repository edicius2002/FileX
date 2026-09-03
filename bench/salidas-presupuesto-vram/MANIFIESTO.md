# MANIFIESTO — bench/salidas-presupuesto-vram/

Ronda 11, carril GPU: N31 (instrumentación fase a fase de RapidOCR) y N26
(código en `filex/sidecar.py`, sin salidas propias aquí).

## img/ — NO se versiona (4,1 MB, regenerable)

Los tres rásteres son la MISMA receta de Ghostscript que usó `N27`
(`bench/salidas-ocr-produccion/preparar_op.py`), reproducidos de forma
independiente y verificados con el mismo Mpx publicado (2,221 / 4,352 / 8,882).

**Orden que los reproduce:**
```
GS="C:\Program Files\gs\gs10.07.0\bin\gswin64c.exe"
for ppp in 200 280 400; do
  "$GS" -q -dNOPAUSE -dBATCH -dSAFER -sDEVICE=pnggray -r$ppp -dFirstPage=1 -dLastPage=1 \
    -sOutputFile="bench/salidas-presupuesto-vram/img/escaneado_d4_r${ppp}.png" \
    corpus/pdf/escaneado_d4.pdf
done
```

| fichero | Mpx | sha256 |
|---|---:|---|
| `escaneado_d4_r200.png` | 2,221 | `99613281cc45f7a68f6d204a2bcd0df6af4c3884867eb73e76b445a65cf08a7e` |
| `escaneado_d4_r280.png` | 4,352 | `6b145e7b0426febdedc03c9b4684a1262f8c6f407b87a2b442e1b648ef49ea7f` |
| `escaneado_d4_r400.png` | 8,882 | `3d010eaba780bdf03d50796a018410d06f2af4cb2cb89acb330dd30b705275c0` |

## json/, scripts — SÍ se versionan

- `n31_fases_child.py` — proceso hijo: una sola imagen, una sola llamada real
  a RapidOCR, VRAM sondeada en 8 fases enganchando las clases reales del
  paquete (misma técnica que `bench/salidas-ppp-norm/sonda_detector.py`).
- `n31_fases.py` → `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe bench/salidas-presupuesto-vram/n31_fases.py`
  — conductor: toma el lock de GPU una vez para toda la tanda (9 corridas,
  ~1 min), lanza el hijo en un PROCESO FRESCO por repetición (el asignador no
  libera memoria: reutilizar el proceso entre imágenes contaminaría la
  atribución por fase). Produce `json/n31_fases.json` (9 corridas, n=3 por
  caso × 3 casos).
- `json/n31_resumen.json` — medianas y deltas entre fases por caso, agregado
  de `n31_fases.json`.

Informe: `bench/presupuesto-vram.md`.

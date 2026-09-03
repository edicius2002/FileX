# MANIFIESTO — `bench/salidas-psm-gs-y-crudos/`

Salidas de `C24` (ronda 9, worker2): qué `--psm` usa el Tesseract embebido en Ghostscript,
inferido por huella de comportamiento. Ver `bench/psm-gs-y-crudos.md` §1.

**Orden que reproduce todo el directorio** (script versionado, `_huella_psm_gs.py`):

```
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe bench/salidas-psm-gs-y-crudos/_huella_psm_gs.py
```

## Ficheros de resultado (versionados, son JSON/texto barato — regla §6)

| Fichero | Qué contiene |
|---|---|
| `control_a_estimating.json` | Control A: si `gs -sDEVICE=ocr` emite «Estimating resolution» (no lo emite — declara `-r` real, no un `pHYs` mentiroso). |
| `curva_psm_gs.json` | Control B: la curva completa `d2`/`d3` × 5 resoluciones (75/100/150/200/300 ppp) × {`gs`, `psm 3`, `psm 6`, `psm 11`}, con `rc`, CER y recuento de caracteres por celda (control C: el `rc` de cada celda, para no confundir silencio con «no arrancó», trampa 25). |
| `escaneado_d{2,3}_{75,100,150,200,300}ppp_psm{3,6,11}.txt` (30 ficheros) | Salida cruda de Tesseract 5.5.0 standalone por celda de la curva B — evidencia de las cifras de `curva_psm_gs.json`. |

Los 5 PNG intermedios (`escaneado_d{2,3}_{res}ppp.png`) que generó el script **no se han
versionado**: son regenerables al vuelo con la orden de arriba (`magick -density`, la misma
invocación que usa el resto de este informe) y no aportan nada que el `.txt` correspondiente
no diga ya.

## Notas

- No hay `sha256` por fichero: son textos de bytes bajos (0–2 067 B) y el contenido íntegro
  vale más que su hash. El `curva_psm_gs.json` es la fuente de verdad de las cifras citadas
  en `bench/psm-gs-y-crudos.md` §1 y en las correcciones de `bench/invocacion-aristas.md`
  (pendiente 7) y `bench/psm-y-rasterizador.md` (§6.5 y §7).

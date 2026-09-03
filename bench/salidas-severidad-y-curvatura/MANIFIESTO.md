# MANIFIESTO — bench/salidas-severidad-y-curvatura/

Ronda 10, carril GPU: `B7` (heurística de degradación severa) y `B20` (residuo de
`B12`, saturación de la sonda de curvatura). Ronda 12: proxy de cajas para
RapidOCR (`b7_cajas_rapidocr.py`), el resto de B7.

## img/ y tmp/ — NO se versionan (7,6 MB, regenerables)

| fichero | bytes | sha256 |
|---|---:|---|
| `img/magick_ppp200__abl_r5_sinonda.png` | ver `json/b20_psm_sweep.json` | `c0ff7655f8422c0763e118927c610043d79aaa921180f50a196bd5195ef9369e` |
| `img/magick_ppp200__realista_d5.png` | ver `json/b20_psm_sweep.json` | `9dacff2a24fdb0ef737af5a57dd7b32e02972d0ac37facd66efd61a042359132` |
| `tmp/abl_r5_sinonda.jpg` | 82085 | `64b3a7929bb3c4f12a8bc3a3f87e94a08ca774db11de227048e7bf8b9c062015` (idéntico al original de `corpus-d5.md`) |

**Orden que los reproduce:**
```
python bench/salidas-severidad-y-curvatura/repro_abl_r5_sinonda.py
D:\Work\research\FileX\.venv-ai\Scripts\python.exe bench/salidas-severidad-y-curvatura/b20_psm_sweep.py
```

`repro_abl_r5_sinonda.py` reconstruye `abl_r5_sinonda` (el control de la sonda de
curvatura, onda=0) **importando** `bench/salidas-corpus-d5/gen_corpus_d5.py` sin
tocarlo, con los globals de ruta redirigidos a este worktree. El JPEG intermedio es
**bit a bit idéntico** al original (`sha256` igual); el PDF no, porque `magick`
estampa `/CreationDate` (trampa 22, ya documentada) — el criterio de fidelidad es
el JPEG, que es el que de verdad se rasteriza para OCR.

## json/, texto/, scripts — SÍ se versionan

- `repro_abl_r5_sinonda.py` — ver arriba.
- `b20_psm_sweep.py` → produce `json/b20_psm_sweep.json` y `texto/*.txt` (6 celdas:
  `realista_d5` × `abl_r5_sinonda` × `psm{3,6,11}`, spa, ppp nativo 200).
- `b7_heuristica.py` → produce `json/b7_heuristica.json` (112 celdas). **No mide
  nada nuevo**: combina la tabla ya publicada en `bench/psm-y-rasterizador.md` §2.1
  (72 celdas, transcritas a mano con su cita) con los datos propios de la ronda 8
  (`bench/salidas-deskew-y-fidelidad/json/{b8_tesseract,b8_rapidocr}.json`, 40
  celdas, dos motores).
- `b7_tiempo.py` → `python bench/salidas-severidad-y-curvatura/b7_tiempo.py --reps 5`
  — produce `json/b7_tiempo.json`. Mide tiempo de Tesseract sobre los 20 rásteres
  YA generados en la ronda 8 (`bench/salidas-deskew-y-fidelidad/img/`, no
  regenera nada), con los dos testigos de ruido del proyecto.
- `json/b8_psm_sweep_deskew.json` — barrido `--psm {3,6,11}` sobre las 4 celdas
  catastróficas de la ronda 8 (`escaneado_d4`/`d4c` × 200/280 ppp × deskew).
  Reproducible con el script equivalente descrito en `bench/severidad-y-curvatura.md`
  §3 (usa los mismos rásteres de `bench/salidas-deskew-y-fidelidad/img/`).
- `b7_cajas_rapidocr.py` (ronda 12) →
  `D:\Work\research\FileX\.venv-ai\Scripts\python.exe bench/salidas-severidad-y-curvatura/b7_cajas_rapidocr.py`
  — engancha `TextDetector.__call__` de RapidOCR (misma técnica que
  `bench/salidas-presupuesto-vram/n31_fases_child.py`) sobre los 20 rásteres de
  la ronda 8. Produce `json/b7_cajas_rapidocr.json` (20 celdas: cajas, área,
  bytes, CER). Toma el lock de GPU para toda la tanda, un solo proceso (no mide
  VRAM, así que no hace falta reiniciar entre imágenes).

Informes: `bench/severidad-y-curvatura.md` (ronda 10), `bench/senal-severidad-y-psm.md` (ronda 12).

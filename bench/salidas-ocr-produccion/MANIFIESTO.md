# MANIFIESTO — `bench/salidas-ocr-produccion/` (agente G5, 2026-08-28)

Salidas de `bench/ocr-produccion-sidecar.md` (encargos **B11** y **B26**).

**Los PNG rasterizados NO se versionan** (23 MB, regenerables en segundos). Se
borran al terminar y se reproducen con las dos órdenes de abajo. **Los `.txt` de
OCR SÍ se versionan**: la fila N17 existe porque `gpu-fase2.md` borró los suyos y
hoy no es auditable.

---

## 1. Cómo se reproduce todo

```bash
R=/d/Work/research/FileX
D=$R/.claude/worktrees/agent-a4c547156ef35c38f/bench/salidas-ocr-produccion

# 1. los rásteres (Ghostscript 10.07, deterministas: mismo sha256)
$R/.venv-ai/Scripts/python.exe $D/preparar_op.py  "$(cygpath -w $D/img)"
$R/.venv-ai/Scripts/python.exe $D/preparar_b11.py "$(cygpath -w $D/img_b11)"
gswin64c -q -dNOPAUSE -dBATCH -dSAFER -sDEVICE=txtwrite -dFirstPage=1 \
  -dLastPage=1 -sOutputFile=$D/img_b11/REFERENCIA-tipico_texto.txt \
  $R/corpus/pdf/tipico_texto.pdf

# 2. las cuatro tandas de medida (cada .sh toma el lock de GPU él mismo)
bash $D/run_a_veneno.sh    # B26 · atasco y control          ~25 min
bash $D/run_b_b11.sh       # B11 · A/B de configuración      ~12 min
bash $D/run_d_criterio.sh  # B26 · repetido/ascendente/directo ~12 min
bash $D/run_c_frio.sh      # B26 · arranque en frío, n=10     ~25 min

# 3. las tablas del informe
$R/.venv-ai/Scripts/python.exe $D/analisis_op.py "$(cygpath -w $D)"
$R/.venv-ai/Scripts/python.exe $D/tablas_op.py   "$(cygpath -w $D)"
$R/.venv-ai/Scripts/python.exe $D/evaluar_b11.py "$(cygpath -w $D/ab)" \
    B11_legado B11_vigente "$(cygpath -w $D/json/b11_saldo.json)"

# 4. las dos sondas de instrumento (CPU, sin GPU)
$R/.venv-ai/Scripts/python.exe $D/sonda_pesos.py cpu
bash $D/run_e_verif.sh
```

---

## 2. Qué hay aquí, y qué NO

| ruta | se versiona | qué es |
|---|---|---|
| `*.py`, `*.sh` | **sí** | arneses |
| `json/` | **sí** | resultados crudos de las cuatro tandas y el saldo de B11 |
| `logs/` | **sí** | trazas completas, incluidas las líneas JSON por celda |
| `texto/` | **sí** | 239 salidas de OCR de B26 (una por celda) |
| `ab/*.txt` | **sí** | 42 salidas de OCR de B11 (21 documentos × 2 configuraciones) |
| `img/`, `img_b11/*.png` | **NO** | 23 MB de rásteres regenerables (tablas §3) |
| `img_b11/indice.json`, `img/indice.json` | **sí** | px, Mpx, bytes y `sha256` de cada ráster |
| `img_b11/REFERENCIA-tipico_texto.txt` | **sí** | 0,2 KB, y es una entrada de medida |

---

## 3. Los rásteres borrados, con su `sha256`

Ghostscript es determinista aquí: re-rasterizar reproduce el `sha256` byte a byte
(comprobado al regenerar `img_b11` tras cambiar la etiqueta de referencia de
`tipico_texto`).

### `img/` — rejilla de megapíxeles de B26

| fichero | px | Mpx | bytes | sha256 |
|---|---|---:|---:|---|
| `escaneado_d4_r100.png` | 647x858 | 0,555 | 373 589 | `68e8a434f394c461...` |
| `escaneado_d4_r150.png` | 970x1287 | 1,248 | 760 570 | `e199d9cc5f555253...` |
| `escaneado_d4_r200.png` | 1294x1716 | 2,221 | 1 179 035 | `99613281cc45f7a6...` |
| `escaneado_d4_r280.png` | 1812x2402 | 4,352 | 1 449 399 | `6b145e7b0426febd...` |
| `escaneado_d4_r400.png` | 2588x3432 | 8,882 | 1 592 617 | `3d010eaba780bdf0...` |
| `escaneado_d2_r100.png` | 647x850 | 0,550 | 322 014 | `215b41e64b342645...` |
| `patologico_escaneado_r200.png` | 1294x1792 | 2,319 | 1 181 954 | `190e9bad2c710d23...` |

### `img_b11/` — corpus del A/B, a ppp NATIVOS

| fichero | px | Mpx | bytes | sha256 |
|---|---|---:|---:|---|
| `patologico_escaneado.png` | 1294x1792 | 2,319 | 1 181 954 | `190e9bad2c710d23...` |
| `escaneado_d1.png` | 970x1300 | 1,261 | 596 280 | `4e86f2ffdad3c4c2...` |
| `escaneado_d2.png` | 647x850 | 0,550 | 322 014 | `215b41e64b342645...` |
| `escaneado_d3.png` | 647x850 | 0,550 | 367 433 | `8aa0105b1360163d...` |
| `tipico_texto.png` | 1240x1754 | 2,175 | 13 022 | `77839223e12f1125...` |
| `escaneado_d4.png` | 1294x1716 | 2,221 | 1 179 035 | `99613281cc45f7a6...` |
| `escaneado_d4a.png` | 1294x1752 | 2,267 | 822 622 | `b6f1d5fb6d3acf9c...` |
| `escaneado_d4b.png` | 1294x1734 | 2,244 | 1 060 583 | `04dbdd3af3befc37...` |
| `escaneado_d4c.png` | 1294x1734 | 2,244 | 1 148 678 | `b55e24e2695b7531...` |
| `escaneado_d4e.png` | 1294x1716 | 2,221 | 1 159 871 | `c0a9ad4edbca0389...` |
| `escaneado_d4f.png` | 1552x2080 | 3,228 | 1 644 741 | `ac388ea86697d733...` |
| `escaneado_d5.png` | 465x636 | 0,296 | 100 293 | `e2d0e902c10acfdb...` |
| `escaneado_d5a.png` | 582x801 | 0,466 | 128 132 | `dc12182d1ef7c177...` |
| `escaneado_d5b.png` | 388x531 | 0,206 | 73 298 | `18af243c58bae07d...` |
| `escaneado_d5c.png` | 517x708 | 0,366 | 118 616 | `8f1611a26b297c8f...` |
| `patologico_d5a.png` | 1294x1752 | 2,267 | 1 334 235 | `a0dede6b16149271...` |
| `patologico_d5b.png` | 1294x1752 | 2,267 | 1 671 019 | `b6c4f4487dd3b2b5...` |
| `patologico_d5e.png` | 1294x1752 | 2,267 | 1 961 439 | `e8caf607234610d3...` |
| `realista_d5a.png` | 1294x1782 | 2,306 | 572 140 | `97f777366e1fba6f...` |
| `realista_d5b.png` | 1294x1771 | 2,292 | 779 449 | `352b304e2250620b...` |
| `realista_d5e.png` | 1294x1752 | 2,267 | 786 849 | `a66c220b4dc59f0e...` |

Los `sha256` completos están en `img/indice.json` e `img_b11/indice.json`, que sí
se versionan.

---

## 4. Entorno de las tandas

`.venv-ai` (torch 2.6.0+cu124, `cuda True`, onnxruntime 1.22.0, rapidocr 3.9.2) ·
`.venv-paddle` (paddle 3.2.0 con CUDA, paddleocr 3.7.0) · **nada instalado en
ninguno de los dos.** RTX 3060, dispositivo **fijado** en cada tanda.
Evaluador: `bench/scripts/ocr_eval.py`, métrica **`acentos`** (canónica desde el
2026-08-28), importado y no copiado.

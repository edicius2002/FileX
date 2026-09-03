# MANIFIESTO — bench/salidas-deskew-y-fidelidad/

Barrido B8(b): `-deskew 40% +repage` sobre la familia `escaneado_d4*` (200/280 ppp),
con Tesseract (`psm 3`, `spa`) y RapidOCR v6 small + R6.

## img/ — NO se versiona (26 MB, regenerable)

Los **20 rásteres PNG** (5 documentos × 2 ppp × base/deskew) se reproducen desde el
corpus versionado en LFS (`corpus/pdf/escaneado_d4*.pdf`), sin generar nada nuevo.

**Orden que los reproduce:**
```
python bench/salidas-deskew-y-fidelidad/raster_b8.py
```

| fichero | geometria | bytes | sha256 |
|---|---|---:|---|
| `escaneado_d4__ppp200__base.png` | 1294x1716 | 1172530 | `a69574472eff965f51e60f2b4f4295ab54bfbd000dba8d97cf91d397a12c6229` |
| `escaneado_d4__ppp200__deskew.png` | 1413x1804 | 1212182 | `ab5cde6813da73cb00bd07027ad95de1b795be710c001e04e40521c58cf8f386` |
| `escaneado_d4__ppp280__base.png` | 1812x2402 | 1441993 | `907d2bdfe23032677fb7ad883843e5e2b84e6500edc74d6397010f6c6469d968` |
| `escaneado_d4__ppp280__deskew.png` | 1978x2525 | 2038761 | `8bd34b0b3e684e64f884c28c1f0be12837ef9923d76faf5fa5612af902137feb` |
| `escaneado_d4a__ppp200__base.png` | 1294x1752 | 812717 | `5270078becd59f5ffb81dc81ad3a7981570f898d957a102fba55a600520bd862` |
| `escaneado_d4a__ppp200__deskew.png` | 1357x1798 | 859709 | `c220cc921abafb13bd863b7c7cab1344808c585196d9524d6977e9264e506937` |
| `escaneado_d4a__ppp280__base.png` | 1812x2453 | 996989 | `f37648d995ee099524d9079e971e85003b2a011bd347192534b688fa57934f04` |
| `escaneado_d4a__ppp280__deskew.png` | 1898x2517 | 1338960 | `a5afa02a9d5563f482b484a7bb2a94034b32727c42d6cba6532380e821b109e2` |
| `escaneado_d4b__ppp200__base.png` | 1294x1734 | 1054083 | `a8f0e0c78df22738cbcbc09eaa1af7d7a440f8f4ba27e582151caccd99d51855` |
| `escaneado_d4b__ppp200__deskew.png` | 1384x1801 | 1061774 | `b3d9a2702f926de41129553f71ddf064aba98a9864277651e9cce24f27c1d93d` |
| `escaneado_d4b__ppp280__base.png` | 1812x2428 | 1303130 | `b90f84070a75b26cc4957e71529274d75ce8699201c27932a9d476601d3cb86e` |
| `escaneado_d4b__ppp280__deskew.png` | 1939x2522 | 1757219 | `e9f3a58c1912da4f7f9ddca807c513e92389c5237236de2fbd789a34031ef28d` |
| `escaneado_d4c__ppp200__base.png` | 1294x1734 | 1141598 | `c1d27663784d6979630e010b600862e01b94fbebb24c73b682fc5e86f0d26ade` |
| `escaneado_d4c__ppp200__deskew.png` | 1385x1802 | 1156047 | `e69fce8c39658d2b1a5e6d95a58141b57f7c6ff43ff95df91cc3fe3c011e91ef` |
| `escaneado_d4c__ppp280__base.png` | 1812x2428 | 1405447 | `c804b44955ea612bb183319ae3f5bdf469af9c38ecf690321d005c7e9712ee07` |
| `escaneado_d4c__ppp280__deskew.png` | 1939x2522 | 1927490 | `bd8d6cbb9c614b148e959a8ad7382d84b60e3e78ebc49b6343af5f8516005d50` |
| `escaneado_d4e__ppp200__base.png` | 1294x1716 | 1153569 | `fd3f8954a8f6a38ee7ed53af8d9494f494d3a2cd6111e9a1c6601335a3ae6856` |
| `escaneado_d4e__ppp200__deskew.png` | 1403x1798 | 1244348 | `f970893de1728a0bbcf332aae18fc365ec70c2488413540039fbb84e3b664452` |
| `escaneado_d4e__ppp280__base.png` | 1812x2402 | 1426060 | `ec8613762911f6d5e170ccbe864869df687027dbde373d8c2927044db539768f` |
| `escaneado_d4e__ppp280__deskew.png` | 1977x2524 | 2088692 | `b08b68072418edea0f2db2018be7ce13b2af4fdf38277dba1a113ca3d42fee7c` |

(Tabla idéntica a `rasteres.json`, que sí se versiona y es la fuente de verdad.)

## texto/, json/, scripts — SÍ se versionan (texto barato)

- `raster_b8.py` — genera `img/` y `rasteres.json`.
- `b8_tesseract.py` → `python bench/salidas-deskew-y-fidelidad/b8_tesseract.py --reps 3`
  — produce `json/b8_tesseract.json` y `texto/tesseract__*.txt` (20 celdas, n=3, 97,7 s).
- `b8_rapidocr.py` → `python bench/salidas-deskew-y-fidelidad/b8_rapidocr.py --reps 3`
  — produce `json/b8_rapidocr.json` y `texto/rapidocr__*.txt`. Toma el lock de GPU
  (`gpu.Lock("B8-rapidocr")`) para toda la tanda.

Informe: `bench/deskew-y-fidelidad.md`.

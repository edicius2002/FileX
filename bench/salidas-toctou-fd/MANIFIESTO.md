# Salidas de N38 — arreglo de la carrera symlink-TOCTOU (`bench/toctou-fd.md`)

worker13, ronda 22, carril `nucleo/toctou-fd`. Todo es texto (arneses `.py` y
resultados `.json`); **no hay binarios**. Los `.json` son los resultados
versionados (trazabilidad); los `.py` son los arneses que los reproducen.

| Fichero | Bytes | sha256 (16) | Qué es / orden que lo reproduce |
|---|---|---|---|
| `probe_procfd.py` | 2953 | 08f579122e323fc5 | Sonda: `/proc/<pid>/fd/N` reabierto por otro proceso alcanza el inodo fijado. `wsl.exe -e python3 .../probe_procfd.py` |
| `probe_motor_procfd.py` | 1797 | f810a595eb8baa90 | Sonda: `magick`/`ffmpeg` aceptan `/proc/pid/fd/N`. `wsl.exe -e python3 .../probe_motor_procfd.py` |
| `arnes_toctou_fd.py` | 7101 | 2b7492a4023466e5 | Arnés Linux: vulnerable vs `abrir_confinado` (en proceso y motor externo cat). `wsl.exe -e python3 .../arnes_toctou_fd.py` |
| `arnes_toctou_fd.json` | 1697 | f0ab1b7bf815fb9a | Resultado del anterior: vulnerable 16,52 %, arreglo 0/278301 |
| `arnes_toctou_windows.py` | 5184 | 45ad253d7d7d65ba | Arnés Windows: vulnerable vs `abrir_confinado`. `PYTHONUTF8=1 .venv-mcp-filex/Scripts/python.exe .../arnes_toctou_windows.py` |
| `arnes_toctou_windows.json` | 1246 | 0d2197e495b6f521 | Resultado: vulnerable 0,067 %, arreglo 0/35513 |
| `coste_denegacion.py` | 2722 | f8037c15fe4fed5f | Coste de denegación (trampa 28). `PYTHONUTF8=1 .venv-mcp-filex/Scripts/python.exe .../coste_denegacion.py` |
| `coste_denegacion.json` | 436 | 81a19d48e744b2e5 | Resultado: denegación 13,1 µs (intacta), vía válida +107,7 µs |
| `discriminancia_n34_n35_n37.py` | 4887 | 05beff1cd8d33996 | A/B: N34/N35/N37 verdes con N38, rojas con su bug reintroducido. `PYTHONUTF8=1 .venv-mcp-filex/Scripts/python.exe .../discriminancia_n34_n35_n37.py` |

Los `sha256` de los `.json` pueden variar entre máquinas (kernel, python, número
de intentos en el tiempo fijo del arnés); lo estable es la CONCLUSIÓN, no el byte.
Rutas absolutas de los arneses: `bench/salidas-toctou-fd/<fichero>` desde la raíz
del worktree; el arnés Linux apunta a la ruta WSL del worktree en su cabecera.

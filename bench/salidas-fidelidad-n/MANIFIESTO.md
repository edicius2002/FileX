# Manifiesto — salidas de N3 (`bench/fidelidad-y-nucleo.md`)

**Generado:** 2026-08-28 · **Todo es TEXTO**: no hay un solo binario versionado.
Los medios que fabrica cada arnés viven en un directorio desechable (`mkdtemp`)
que se lista antes y después y se borra entero al terminar (R18, trampa 21).
Cada JSON lleva `censo_antes` y `censo_despues`.

## Antes de reproducir nada

1. **El corpus viene como punteros de LFS en un worktree nuevo** (trampa 34):

   ```
   git lfs checkout
   ls -l corpus/imagen/tipico.png     # 42 855 B, no 130
   ```

2. **Las 53 salidas del patrón oro no se versionan** (§6 de `CLAUDE.md`). Hay que
   regenerarlas antes de la regresión, y el regenerador las deja **fuera** del
   repositorio:

   ```
   python bench/salidas-firmas-cierre/_regenera53.py
   # -> %TEMP%\claude\...\scratchpad\REF53\{audio,datos,imagen,pdf,video}
   ```

## Inventario

| Fichero | Qué es | Orden exacta | Coste |
|---|---|---|---|
| `a7_repro_n.py` · `.json` | **Copia literal** de `bench/salidas-ventana/a7_bitrate_bajo.py` (N16), cambiados solo los nombres de salida. Trampa 58: reproducir antes de aplicar. 90 celdas. | `python bench/salidas-fidelidad-n/a7_repro_n.py` | ~190 s |
| `a7_corr_ancho.py` · `.json` | La misma señal **fuera** de las condiciones de N16: 8 fuentes (3 nuevas) × 14 destinos (opus, mp3, aac, **flac y wav**) × 2 clases + 5 recodificaciones legítimas brutales. **264 celdas.** También el acuerdo RMS `PCM` vs `astats`. | `python bench/salidas-fidelidad-n/a7_corr_ancho.py` | ~16 min |
| `a7_rejilla.py` · `.json` | Aritmética sobre `a7_corr_ancho.json`: cuántas celdas ya son fallo hoy, si queda hueco, y la rejilla (umbral de correlación) × (suelo relativo de canal). **No lanza nada.** | `python bench/salidas-fidelidad-n/a7_rejilla.py` | <1 s |
| `a7_grafo.py` · `.json` | La misma rejilla con la métrica **sin numpy y sin alinear** (identidad de los tres RMS), comparada celda a celda con la de N16. | `python bench/salidas-fidelidad-n/a7_grafo.py` | ~16 min |
| `a7_coste_grafo.py` · `.json` | Coste **aislado** (n=15, dos testigos con tope): los dos `astats` de A7, el grafo, la vía de N16, y **el control que faltaba** — la orden exacta con la que N16 midió sus «364,0 ms». | `python bench/salidas-fidelidad-n/a7_coste_grafo.py` | ~4 min |
| `a7_ciego_opus.py` · `.json` | Lo aplicado: 54 celdas (2 fuentes × 9 tasas × 3 códecs) con el verificador de `HEAD` y con el del árbol. Tasa deducida, `cobertura['A7']` y veredicto, antes y después. | `python bench/salidas-fidelidad-n/a7_ciego_opus.py` | ~2 min |
| `sonda_destino_dir.py` · `.json` | N19/N20: sonda de **mecanismo**, sin una sola carrera. `errno` de cada negativa, y si `recoger()` pisa. | `python bench/salidas-fidelidad-n/sonda_destino_dir.py` | ~1 s |
| `huella_impacto.py` · `.json` | ¿Caduca este trabajo el componente `contrato`? Con control positivo de compilación (trampa 60). | `python bench/salidas-fidelidad-n/huella_impacto.py` | <1 s |
| `regresion_53_n.py` · `regresion_{antes,despues}.json` | **Variante propia** del arnés compartido `bench/salidas-contrato-v/regresion_53.py` (CLAUDE.md §1). Único cambio de fondo: `FILEX_REF53` localiza las 53 regeneradas sin escribir en `bench/salidas-referencia/`. | `FILEX_REF53=…/REF53 python bench/salidas-fidelidad-n/regresion_53_n.py [--antes\|--diff]` | ~50 s |
| `proto_graf.py` | Prototipo que destapó que **`amix=…:weights=1 -1` no resta**: sobre dos FLAC idénticos daba `RMS(dif)=2·RMS(x)`. | `python bench/salidas-fidelidad-n/proto_graf.py` | ~20 s |
| `proto_diag.py` | Prototipo que destapó que **`channel_layouts` no es decorativo**: sin él `amerge` da `Error reinitializing filters!` en mono, estéreo y vídeo. | `python bench/salidas-fidelidad-n/proto_diag.py` | ~30 s |
| `proto_mono.py` | El grafo sobre lo que hay **de verdad** en las 53: mono, vídeo con audio y 44,1 → 48 kHz. | `python bench/salidas-fidelidad-n/proto_mono.py` | ~20 s |
| `dbg_opus.py` | La sonda de un `.opus`: `bitrate_bps = None` en la pista, y de ahí que la tasa haya que deducirla. | `python bench/salidas-fidelidad-n/dbg_opus.py` | ~10 s |
| `logs/` | La salida por pantalla de los arneses largos. |  |  |

## Lo que NO se toca desde aquí

`bench/salidas-referencia/referencia.json` se **lee**. Ningún arnés de este
directorio escribe en `bench/salidas-referencia/`, en `bench/salidas-ventana/`
ni en `bench/salidas-contrato-v/`.

# CR-010 — Índice reproducible de semillas y manifiestos

**Base de entrada:** `0ec60d5930444077fefffbac00d19e6dc5ecb55c`.
**Estado:** DERIVADO del árbol versionado y MEDIDO localmente el 2026-09-07.
No se ejecutó ninguna conversión, no se usó red, Docker, GPU ni sidecar.

## Resultado y denominadores

`indice-semillas.json` contiene **170/170 registros** dentro de su universo declarado:

| Fuente | Registros | Base |
|---|---:|---|
| `corpus/`, excluidos sus manifiestos | 42 | ficheros presentes en el HEAD de entrada |
| `bench/salidas-hito5/entradas/` | 7 | ficheros presentes en el HEAD de entrada |
| tokens de `pool_indice.json` | 111 | 111 claves distintas de `__semillas__` |
| roles de `pool_indice.json` | 10 | claves de `__semillas__` |
| **Total** | **170** | suma disjunta por tipo de registro |

**MEDIDO local.** Hay **59/170 referencias disponibles** y **111/170 ausentes**:
104 tokens históricos y 7 roles históricos cuyo `pool/` fue podado por ser regenerable.
Las 59 referencias disponibles resuelven a **49 ficheros únicos**; diez registros del
pool reutilizan una semilla ya presente. La ausencia se conserva como resultado válido
con hash nulo cuando la evidencia histórica no publicó uno, tamaño histórico cuando
existe y argv/uso de reconstrucción.

**MEDIDO local.** Los 170 registros declaran licencia. Son **0 conocidas y 170
desconocidas**: las fuentes inspeccionadas no aportan licencia por semilla, por lo que no
se infiere una desde la licencia del repositorio. Cada fila lo expresa como
`NO-DECLARADA`.

**MEDIDO local.** Hay **49/170 referencias gestionadas por LFS**, correspondientes a
**39 rutas únicas**, y **0 punteros sin materializar** en este worktree. El índice
distingue `gestionado` de `es_puntero`: un objeto LFS materializado se hashea por sus
bytes; un puntero presente se clasificaría como `puntero_lfs` y usaría el OID y tamaño
declarados por el puntero.

## Portabilidad y reproducción

No se conserva ninguna ruta absoluta de `pool_indice.json`. Todas las rutas usan `/` y
son relativas a la raíz. Cada registro incluye origen y base, licencia, SHA-256, bytes,
formato/token, uso, argv esperado, disponibilidad y metadatos LFS. Cinco manifiestos
fuente quedan inventariados con hash completo y tamaño.

Desde la raíz:

```powershell
python -B -X utf8 bench/salidas-cr-semillas/generar_indice.py
python -B -X utf8 bench/salidas-cr-semillas/generar_indice.py --comprobar
python -B -X utf8 bench/salidas-cr-semillas/test_indice_semillas.py
```

La generación sólo lee el corpus, las entradas documentales, `pool_indice.json`, sus
manifiestos y `git lfs ls-files -l`. No crea `pool/`, no copia corpus y no invoca motores.

## Límites

- El universo no afirma contener cada fixture mencionado por cada informe histórico:
  cubre las dos raíces de semillas conservadas y el índice histórico P2 señalado por la
  auditoría. Los usos secundarios quedan trazados mediante los manifiestos fuente.
- Los 111 registros ausentes no pueden adquirir un SHA-256 de contenido sin volver a
  materializarlos; inventarlo rompería la trazabilidad.
- El tamaño histórico no prueba que una regeneración futura sea byte a byte idéntica.
  El argv documenta el uso esperado, no eleva disponibilidad ni licencia.

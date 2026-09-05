# `bench/salidas-fix-verificador/` — instrumentos y salidas del carril `fix/verificador`

Informe: `bench/fix-verificador.md`. Rama: `fix/verificador`, partiendo de
`integra/cobertura` (`4333278`).

**Aquí no hay un solo binario.** Todo es script y JSON, que es lo que la regla §6
de `CLAUDE.md` sí manda versionar. Nada que borrar al terminar.

**Declaraciones de la medida** (trampas 94 y 101): intérprete
`.venv-mcp-filex\Scripts\python.exe`, win32, **3.11.9**; sin Docker y sin GPU;
`corpus/` resuelto con `git lfs checkout` antes de medir (trampa 34).

## Instrumentos, y la orden exacta que reproduce cada salida

Todas se lanzan desde la raíz del *worktree* con el intérprete de arriba.

| Salida | Orden que la reproduce | Qué mide |
|---|---|---|
| `huella_antes.json` | `python bench/salidas-fix-verificador/huella_estado.py antes` | huella `contrato` y estado de las 172 aristas **antes** de tocar nada |
| `huella_despues.json` | `python bench/salidas-fix-verificador/huella_estado.py despues` | lo mismo **después** de los siete arreglos |
| `control_huella_v5.json` | `python bench/salidas-fix-verificador/control_huella_v5.py 4333278` | que el arreglo 7 **solo** no mueve la huella, y los otros seis sí |
| `rojo_antes.txt` | `python bench/salidas-fix-verificador/correr_modulos.py bench/salidas-fix-verificador/rojo_antes.txt` — **con las pruebas dadas la vuelta y `filex/verificador.py` sin tocar** | el rojo de cada defecto antes de su arreglo |
| `verde_despues.txt` | `python bench/salidas-fix-verificador/correr_modulos.py bench/salidas-fix-verificador/verde_despues.txt` | el verde de los siete módulos afectados |
| `sonda_png16.json` | `python bench/salidas-fix-verificador/sonda_png16.py` | que las dos vías de `_alfa_min_png` coinciden entre sí y con el oráculo |
| `sonda_png16_base.json` | `python bench/salidas-fix-verificador/sonda_png16.py 4333278` | **el control**: la misma sonda contra el código de partida (16 discrepancias de 26) |
| `ab_sonda_alfa.json` | `python bench/salidas-fix-verificador/ab_sonda_alfa.py` | A/B de `sondear_en_proceso` y `alfa_minimo` sobre 94 ficheros reales |
| `ab_contrato_oro.json` | `python bench/salidas-fix-verificador/ab_contrato_oro.py` | A/B de `verificar()` **entero** sobre las 39 órdenes del patrón oro |
| `revalidar_v5.json` | `python bench/salidas-fix-verificador/revalidar_v5.py` | la revalidación de V5 que el carril anterior declaró imposible |
| `censo_alcance.json` | `python bench/salidas-fix-verificador/censo_alcance.py` | **por qué** el A/B ancho sale en cero: qué ficheros podrían tocar lo arreglado |
| `espia_modo13.json` | `python bench/salidas-fix-verificador/espia_modo13.py` | cuántos WebP reales usan el predictor 13, **con control positivo** |

## Dos avisos para quien las reproduzca

1. **Cuatro de las doce necesitan el patrón oro**, y `bench/salidas-referencia/`
   sólo versiona `MANIFIESTO.md`, `referencia.json` y `logs/` (trampa 89). Los
   scripts lo resuelven **remapeando por nombre base** desde la ruta absoluta que
   `referencia.json` guarda, y aceptan el directorio como argumento:
   `python …/revalidar_v5.py <dir con las 53 salidas>`. Si ese directorio no
   existe en tu máquina, la salida dirá `faltan: 53` y no será comparable.
2. **`rojo_antes.txt` no se reproduce con el árbol de ahora.** Es una medida de
   ORDEN TEMPORAL: las pruebas ya dadas la vuelta contra el `verificador.py` de
   `4333278`. Para rehacerla:
   `git show 4333278:filex/verificador.py > filex/verificador.py`, correr, y
   revertir con `git checkout -- filex/verificador.py` — **nunca con
   `git stash push`, que sobre un fichero ya commiteado no hace nada y devuelve
   0 sin avisar** (trampa 119).

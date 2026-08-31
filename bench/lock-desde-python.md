# C38 + C39 — lock GPU desde Python

**MEDIDO, 31-08-2026, Git Bash salvo las celdas WSL de cruce.** La API es
`filex.gpu.Lock`, basada en `Candado("gpu")`: mutex `Global\\filex-gpu` con
SDDL explícito más candado de rango para metadatos. El arnés shell conserva un
proceso Python retenedor; una llamada Python que tomase y terminase liberaría el
mutex inmediatamente.

## Decisión

**Usar el mutex `Global\\` como primitivo de exclusión y el fichero de rango
como compatibilidad/metadatos.** El mutex puro cuesta **11,3 µs** de mediana
(n=99), frente a **490,3 µs** del candado de rango: **×43,4 más rápido**. La
API compuesta recuperó un dueño muerto por `taskkill /F` en **11 037,1 µs**;
el fichero solo, en **8 793,9 µs**. No hay PID en el veredicto del mutex.

Tomarlo desde `harness.sh` sí cuesta **957 ms** de mediana (n=9, rango
778–1 578 ms). La descomposición calentada explica su naturaleza: arrancar
Python y salir son **41,3 ms**; arrancarlo e importar/tomar/soltar mutex,
**82,0 ms**; arrancarlo e importar/ejecutar `guardia()`, **128,1 ms**. La ruta
actual `gpu_acquire_mutex` **no llama `guardia()`**: conserva la guardia de
VRAM del arnés después de adquirir. La tanda quedó **SUCIA** por escritorio
(pico GPU 19 %, estructural). Es aceptable por tanda; **PENDIENTE** si se
pretendiera adquirir por página o imagen.

## C38 — API Python

**MEDIDO.** `filex/gpu.py` expone `Lock(etiqueta)` como gestor de contexto y
`tomar(espera=...)`/`soltar()`. Las pruebas nuevas verifican exclusión Python,
liberación tras `taskkill /F` y contexto: `2/2 OK` con Python Windows 3.11.

El censo actual da **25** `.py` con `nvidia-smi` y **1** con `gpu_acquire`.
Esto refuta que el lock de shell baste para los consumidores Python.

**Compatibilidad durante la migración (MEDIDO por las regresiones de H2):** el
fichero heredado no es sólo metadato mientras queden arneses sin migrar. Un
`filex.gpu.Lock` toma primero el fichero `O_CREAT|O_EXCL` y después el mutex;
por ello un arnés viejo bloquea a uno migrado, y el migrado bloquea tanto a
viejos como a migrados. El dueño vivo no se roba y un huérfano se recupera aun
con `espera=0`. Sin esta doble toma habría «media exclusión».

## C39 — cruce de intérpretes

**MEDIDO.** Dueño vivo antes y después (`kill -0` rc=0); el evaluador recibió
timeout de 3 s (`rc=124`), que aquí significa que respetó el mutex:

| dueño | evaluador | resultado |
|---|---|---|
| Git Bash | Git Bash | bloquea |
| Git Bash | WSL | bloquea |
| WSL | Git Bash | bloquea |
| WSL | WSL | bloquea |

**Controles positivos MEDIDOS:** E (sin dueño, evaluador Git Bash) y F (sin
dueño, evaluador WSL) dan `rc_eval=0`. Por tanto los `rc_eval=124` de A–D no
son un intérprete que no arrancó: son el timeout de una toma bloqueada.

La celda WSL necesitó convertir la ruta del script con `wslpath -w`; sin ello
Windows Python intentaba abrir `D:\\mnt\\d\\…` y el retenedor nunca publicaba
listo. Su liberación también usa `/PID` (WSL), mientras Git Bash exige `//PID`.
También se corrigió el arnés de cruce: las primeras dos versiones eran inválidas
(`dueño` no es identificador Bash; `timeout` no ejecuta funciones). No se usan
esos rc=127. La repetición final terminó con `esta_libre(gpu)=True`.

## Pendientes y límites

- **PENDIENTE:** medir el coste compuesto en una tanda OCR real; este encargo
  mide la exclusión aislada.
- **PENDIENTE:** migrar los 25 arneses Python a `filex.gpu.Lock`; C38 entrega
  la API, no una migración masiva concurrente.
- La guardia sigue decidiendo por VRAM libre total, nunca por PID.

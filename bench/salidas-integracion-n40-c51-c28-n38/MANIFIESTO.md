# Evidencia individual N40/C51/C28/N38

Base solicitada: `0ec60d5930444077fefffbac00d19e6dc5ecb55c`.
CPU exclusivamente, disable-hardware-acceleration=true; sin GPU ni sidecar.
Las campañas no son medidas de rendimiento: la máquina tiene carga compartida.

`n38-antes.json`: 100 intentos naturales sobre trabajo.py original, 0 fallos.
`n38-despues.json`: 100 intentos naturales con el umbral cero corregido, 0 fallos.
Orden: `python ci/repetir_n38.py --n 100 --json <resultado>`.
No son ejecuciones del runner hospedado; se conservan aparte los 2/47 históricos.
Las fechas y duraciones no se usan como garantía de reproducibilidad byte a byte.

Los logs de construcción se conservan cuando están disponibles; las etiquetas
de prueba no reemplazan filex-c13. No se versionan imágenes ni salidas binarias.
El informe de cierre enumera controles rojos, verdes y limitaciones externas.

`suite-cpu.txt`: suite completa CPU, Python 3.11.9 del venv MCP / pytest 9.1.1,
con exclusiones explícitas de test_hito2, test_hito6 y test_gpu_lock. Resultado:
889 aprobadas, 4 saltadas, 6 fallos heredados por sellos caducados, 77688 subtests
aprobados. No se borra el rojo ni se edita ninguna huella para hacerlo pasar.

`n38-*-interrumpida.json` y `n38-*-checkpoint.json`: dos campañas del arnés de
checkpoint por replace que falló; 74/75 y 96/97 intentos conservados. Cada
pareja es una sola campaña incompleta (n solicitado=100), no se suman.
`n38-diario-final.json` y `.jsonl`: la campaña final con diario append-only,
100/100 completados, cero fallos. Se conserva cada intento antes de continuar.
El resumen final no se escribe si la campaña se interrumpe.

`builds-c51.json`: nueve invocaciones del builder, incluida la exportación
fallida y su reparación reutilizando caché. Tres construcciones finales
independientes sin caché coinciden; no se cuentan los pilotos como réplicas
de la receta final. `docker/c13.lock.json` fija la identidad aceptada.

`registro-head.json` y `registro-head-c51.json`: mismo código de producto,
primero con imagen histórica y luego FILEX_IMAGEN_DOC=filex-c51-entrega.
Ambos tienen 232 aristas (172 sin sondeo vigente, 57 históricas, 3 nominales).
El segundo añade build_distinto en los tres motores documentales. Órdenes:
`python bench/salidas-integracion-n40-c51-c28-n38/recalcular.py`, y luego con
la variable de imagen y `--registro registro-head-c51.json`.

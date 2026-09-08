# Integración individual N40, C51, C28 y N38

Base: `0ec60d5930444077fefffbac00d19e6dc5ecb55c`, integra/cobertura.
Trabajo individual, sin delegación, GPU, sidecar, push, PR ni merge externo.
`disable-hardware-acceleration=true`. Evidencia propia en
[salidas-integracion-n40-c51-c28-n38](salidas-integracion-n40-c51-c28-n38/MANIFIESTO.md).

## Estado y definición de terminado

| ID | Estado inicial comprobado | Resultado | Definición de terminado y límite |
|---|---|---|---|
| N40 | Descriptor local integrado, pero el primer motor de contenedor recibía la ruta real reabrible | **MEDIDO: corregido**, control Linux original lee AJENO; integrado lee PERMITIDO. Pandoc real recibe el centinela permitido | El bind recibe una copia del descriptor validado, extensión conservada, directorio privado vivo y limpieza al terminar. Se mantienen las comprobaciones de raíces, destino y censo. No promete inmutabilidad frente a escritura sobre el mismo inodo por otro proceso |
| C51 | Digest de base fijado, apt móvil; reconstruir alteraba imagen y 40 sellos | **MEDIDO: build reproducible y arranque CPU**. Tres builds finales sin caché con el mismo manifest y config; tres motores comprobados | Base amd64, snapshot firmado, caché auxiliar eliminada, epoch explícito y exportador fijados; verificador rechaza otra identidad. No se publica imagen ni se heredan sellos |
| C28 | Clasificación dispersa; chk/oeb medidos, eml mal clasificado; sin encoder mezclado con objetos ajenos al contrato | **MEDIDO/DERIVADO: cierre de alcance por clasificación y rechazo**, 56/56 particionados sin duplicados | Rechazos explican objeto y soporte integrado. Cero aristas nuevas. No se implementan codecs, correo ni contratos de paquetes no autorizados; no se afirma inviabilidad universal |
| N38 | 2 fallos/47 ejecuciones hospedadas, mecanismo sin traza | **MEDIDO: defecto de edad negativa corregido y estabilización local; validación hospedada PENDIENTE** | Rojo/verde determinista, 100 intentos naturales antes y 100 después conservados; CI guarda cada intento por run_id/run_attempt. Falta ejecutar esta revisión en windows-latest y atribuir allí los dos fallos históricos |

N38 no se declara cerrado en el inventario: el permiso de esta entrega excluye
push/PR, por lo que la revisión no puede probarse allí mediante ese flujo. No se
equiparan cien observaciones de Windows local con cien ejecuciones hospedadas.

## Historia reconciliada

**MEDIDO por comparación Git:** los contenidos de `filex/nucleo.py` y
`filex/confinamiento.py` en `nucleo/toctou-fd` ya estaban en la base. Sus commits
`2e66cde`, `7db672a`, `46aea7c` y `5f00e67` usan el nombre histórico N38, pero el
inventario los identifica como **N39**, no como el N38 de CI. No se cherry-pickean.
La receta `docker/Dockerfile.c13` de `orden/contenedor-publicable` también estaba
integrada: `a178966` y `3f788dd` no son trabajo pendiente de integración.

Se consultaron las ramas `cpu/cancelacion-inestable`, `cpu/mcp-cabos-y-techos`,
`cpu/aristas-escribibles`, `cpu/aristas-reclasificacion`, los cierres remotos N38
y el historial C28. La corrección N36 de huérfanos no equivale a resolver N38.
`edicius2002/filex-cierre-restantes` sólo aportaba un plan adicional. Se preserva
el producto ya integrado; las correcciones nuevas son commits convencionales
separables. No se incorporan commits ni ficheros de la rama auditora.

## N40: control de seguridad

**MEDIDO.** `pruebas/test_n40_contenedor.py` reproduce la frontera con dos inodos
distintos. Sobre el código original, lee `CONTENIDO AJENO` donde exige
`CONTENIDO PERMITIDO`. La corrección copia mediante `os.dup(fd)` y
`shutil.copyfileobj`, nunca mediante la ruta real vulnerable. La copia vive en
un `DirectorioDeTrabajo` distinto de la salida: no contamina el quinto punto.

**MEDIDO en Linux, Python 3.13 dentro de la imagen CPU:** se abre y valida el
descriptor real; se renombra su directorio y se sustituye por un symlink a otra
raíz. Control original: **2 fallos y 1 salto**; integrado: **2 aprobadas y 1 salto**.
La prueba de Docker anidado se omite allí explícitamente. Los logs
`n40-linux-antes.txt` y `n40-linux-despues.txt` conservan ambos resultados.
`control_n40.py` permite cargar el código original extraído con
`git show 0ec60d5:filex/nucleo.py`, sin modificar el producto.

**MEDIDO en Windows, Python 3.11.9:** `FILEX_PRUEBA_DOC=1` con la imagen histórica
por ID ejecuta Pandoc real: **2 aprobadas y 1 salto** (el ataque Linux). El HTML
contiene `FILEXSENTINELA7743` y no `CONTENIDOAJENO`. La regresión comprueba cierre
del descriptor, eliminación de copia y extensión `.md`. Es una propiedad de
aislamiento de entrada; no una evaluación general de fidelidad documental.

## C51: las condiciones que faltaban

**MEDIDO.** La imagen histórica `6d359bad483e…` sigue identificada; arrancó en CPU:
qpdf 12.4.0, Pandoc 3.9.0.2, LibreOffice 26.2.4.2 y Calibre 9.9.0.
La receta nueva usa el manifiesto base amd64
`sha256:081d1638e8c6dfb6b5e69f47ff90e6f6037cdee29a2f25ddd44ddc6d2e52451d`
y snapshot Debian `20260904T000000Z`, sustituyendo **todas** las fuentes móviles.
Los índices históricos mantienen firmas y hashes; sólo se desactiva su caducidad.

**MEDIDO: no se borran los intentos que refutaron reproducibilidad.**

| Condición ensayada | Resultado |
|---|---|
| Snapshot, exportación normal | Build rc=0, manifest `c3579f40…`; no demuestra repetibilidad |
| rewrite-timestamp con unpack por defecto | rc=1: `exporter option "rewrite-timestamp" conflicts with "unpack"` |
| unpack=false, epoch sólo como ARG por defecto | Exportación funciona; builds `13a65e55…` y `6c1f8e51…` distintos |
| Comparar /etc y /var | Difiere `/var/cache/ldconfig/aux-cache`; `/etc/hostname` pertenece al contenedor de comprobación y no identifica la imagen |
| Eliminar aux-cache, epoch sólo por defecto | Builds `e2c17f4d…` y `6281d327…` distintos; Created sigue siendo la hora de construcción |
| Pasar además `--build-arg SOURCE_DATE_EPOCH=1788480000` | **Tres construcciones finales sin caché, manifest y config idénticos** |

Manifest final:
`sha256:85334f0c0482e4aaf780f1789ca7cde7608a6e24c47f15b2fdd4e95a2673e472`.
Config: `sha256:1d06c17e036361a62fb161819065a05d4a975655584b42f4e5ce27982a831779`.
Docker 29.4.3, Buildx v0.33.0-desktop.1. El contrato del exportador está descrito
en la [documentación oficial de Docker](https://docs.docker.com/build/exporters/image-registry/);
la necesidad de pasar epoch explícito aquí se comprobó en ejecución.

Órdenes públicas comprobadas:

```powershell
python docker/construir_c13.py --tag filex-c13-repro
python docker/verificar_c13.py filex-c13-repro
$env:FILEX_IMAGEN_DOC='filex-c13-repro'
python -m filex motores
```

**MEDIDO.** El wrapper se ejecutó con la etiqueta propia `filex-c51-entrega` y
produjo el mismo digest. El verificador comprobó Pandoc md→html con centinela,
Pandoc md→docx, LibreOffice docx→pdf y `qpdf --check`, Calibre docx→epub con
centinela; tesseract enumera eng/osd/spa y qpdf es 12.4.1. Cada proceso tiene
tope, el contenedor usa init, timeout interno, CPU y red deshabilitada.
Control negativo: la imagen histórica recibe rc=1 por digest distinto antes de
ejecutar conversiones. **Fidelidad general no evaluada.**

**PENDIENTE externo:** disponibilidad futura del registro base y snapshot;
publicación de un artefacto OCI sólo si se autoriza aparte. El digest local no
es una URL pública. El comprobador falla si otra herramienta produce otra
identidad. No se cambian los sellos para hacer pasar una reconstrucción.

## C28: 56 casos, sin atribuir capacidad

**DERIVADO con asserts:** `c28-clasificacion.json` conserva la población exacta
de `c28_los56.json`: 20 escrituras históricas, 12 sin encoder integrado, 4 sin
escritor integrado, 12 extracciones condicionadas a metadatos, 3 sin bytes en
el sondeo, 1 variante no admitida, sup, chk, oeb y eml. Total **56**.
`rtsp` y `sap` se clasifican fuera de esos 56 como destinos de red.

La evidencia histórica de escritura no se convierte en contrato aprobado.
`sup` requiere mapa de bits; `clip` necesita recorte; `chk` necesita cabecera y
fragmentos; `oeb` es directorio; `eml` nunca se había ejecutado en aquel censo,
y el msgconvert histórico estaba roto por Email::Address. No se mantiene la
deducción falsa «sin stderr = directorio». Las diferencias de encoders entre
las dos builds de C50 no prueban soporte integrado ni inviabilidad universal.

**MEDIDO.** La prueba del diagnóstico falla antes y pasa después. La segunda
regresión añadió las clases c2/dzi/8bim/jpt/iptcwtext: volvió a fallar antes
de completar esos rechazos y pasó después. El diagnóstico sólo complementa una
decisión **sin camino**; no bloquea una ruta real ya registrada.

## N38: denominadores conservados

**MEDIDO.** Si mtime está 15,625 ms por delante de `time.time()`, la edad es
negativa y la condición original `edad < 0` conserva el directorio pese al
umbral cero. La regresión falla con `sin_candado_jovenes=1`, `errores=0`.
Se aplica edad sólo con umbral positivo; los directorios futuros siguen
protegidos con un umbral positivo. **10 pruebas focalizadas aprobadas**.

Campaña natural local: **0/100 antes y 0/100 después**, ambos JSON completos.
No es un bucle de reruns hasta verde: se predeclaran cien intentos y se guardan
todos. El historial hospedado permanece **2/47**, con sus dos run IDs en el
inventario. **PENDIENTE:** no hay traza que atribuya aquellos dos incidentes
al mecanismo reproducido localmente; no se inventa esa atribución.

La CI añade la regresión y una campaña de cien intentos, conservada con nombre
`n38-<run_id>-intento-<run_attempt>` incluso si falla. El paso devuelve fallo si
cualquier intento falla. No se modifica cancel-in-progress ni se ocultan
cancelaciones previas (los nueve cancelados históricos no son éxitos).

**MEDIDO y corregido en el propio arnés:** un checkpoint que reemplazaba el
JSON por cada intento recibió WinError 5 tanto en sandbox como fuera. Se
conservan ambas campañas incompletas: resumen con **74/100** y checkpoint
con 75; resumen con **96/100** y checkpoint con 97. Cada pareja son los mismos
intentos, no dos campañas distintas. La atribución inicial al sandbox queda
**REFUTADA** por el segundo control. El arnés final mantiene un handle abierto
y añade registros JSONL con flush; escribe el resumen una sola vez y rechaza
nombres de campañas existentes. **0/100** en la comprobación final. Si se
interrumpe, la CI conserva el diario parcial y no lo cuenta como cien éxitos.
Una regresión adicional demuestra que una excepción del barrido se registra
como intento fallido: **rojo antes, verde después**. No se atribuye este defecto
del checkpoint nuevo al incidente histórico del producto.

## Cobertura recalculada y validación

**MEDIDO/DERIVADO sobre HEAD**, `registro-head.json`: **232 aristas disponibles =
172 sin_sondear + 57 reales basales históricas + 3 nominales**. Los cinco sellos
discrepan en la huella de contrato: **172 registros sellados** afectados
(62 ImageMagick, 70 ffmpeg, 16 LibreOffice, 16 Pandoc, 8 Calibre). Esto ya viene
de la base integrada: diff de contrato/verificador/huella/sondeos y sus pruebas
contra la base, vacío. La auditoría consultada contaba 170 selladas vigentes,
57 históricas y 5 nominales sobre su otra base; **ya no es el estado efectivo**.
El recuento no ejecuta conversiones ni escribe sellos.

**MEDIDO:** suite en sandbox interrumpida tras acumular fallos; no se declara
aprobada. Pasada amplia fuera del sandbox, Python 3.11.9 / pytest 8.4.2:
859 aprobadas, 10 saltadas y 1 fallo antes de maxfail, por sellos caducados.
Módulos finales y MCP con el venv existente / pytest 9.1.1: 123 aprobadas,
1 saltada, 30 subtests aprobados y **6 fallos** (5 subtests de los mismos sellos
y la comprobación agregada). No se parchean esas pruebas ni las huellas.
La suite CPU final completa se conserva en `suite-cpu.txt`.

**MEDIDO, suite CPU completa final con el venv MCP existente:** **889 aprobadas,
4 saltadas, 6 fallos, 77 688 subtests aprobados y 6 avisos**, 247,84 s.
Los seis fallos son los cinco subtests y la comprobación agregada de sellos
caducados; no hay otro fallo. La mejora posterior del diario N38 pasó sus
**3 pruebas focalizadas** y su campaña de cien intentos, sin repetir la suite
de producto que esa mejora no modifica.

Excluidos por política: test_hito2.py, test_hito6.py y test_gpu_lock.py
(GPU/sidecar/guardias). Los tests de invocación CPU y los dobles que no acceden
a hardware sí se ejecutan. Python de Windows 3.11.9; Docker local disponible
fuera del sandbox; máquina compartida, sin deducir rendimiento de duraciones.

Integridad inicial: **8 OK/1 MAL**, ocho informes heredados sin registrar.
Se registran sin editar su contenido. **MEDIDO final: integridad 9/9**, 117
informes citados, inventario 6 históricos/1 abierto/2 parciales/123 cerrados;
`git diff --check` y compilación de los arneses sin errores. La comprobación
focalizada posterior a la revisión da **5 aprobadas y 2 saltadas** (Docker
optativo y Linux, ejercitados por separado antes). Los hashes de entrega van
en la respuesta del terminal; el informe no contiene un hash autorreferencial.

# Saneo de veracidad del inventario (ronda 3) y C41 — worker2

**Tanda:** carril CPU/Docker, sin GPU. **Rama:** `cpu/saneo-y-manifiestos`.
**Entorno:** WSL2 (Ubuntu) sobre este worktree, Python 3.x nativo de WSL para
los scripts de verificación de este informe; `git`, `sha256sum`, `stat` de
coreutils. No se usó Docker en esta tanda (no hizo falta: todo el trabajo es
lectura de reportes/código y escritura de manifiestos/documentación).

Dos tareas, pedidas por el master en la Ronda 3: **A)** revisar las 111 filas
de `ESTADO-Y-REPARTO.md` §3 contra la evidencia (no solo contra "¿tiene un
emoji?", que ya lo comprueba `ci/integridad.py`, sino "¿el emoji es VERDAD?").
**B)** C41: escribir manifiesto real a los 17 directorios `bench/salidas-*`
que no lo tenían.

---

## 1. Metodología de la Tarea A

Para las **24 filas rojas y las 8 amarillas** que había al empezar la ronda
(`6 ⚫ · 24 🔴 · 8 🟡 · 73 🟢`, la línea vigente en `origin/main` antes de esta
rama), se hizo lo mismo para cada una:

1. Localizar el informe/commit/código que la fila cita.
2. Confirmar que existe (`ls bench/<informe>.md`, `git log -1 -- <ruta>`,
   `git cat-file -e <hash>`, o leer el código).
3. **`grep -rl "<identificador>" bench/*.md` y `git log --all --grep`**: buscar
   si existe un informe o commit MÁS NUEVO que la cierre y que el inventario
   no refleje — es el defecto exacto que ya había mordido tres veces antes de
   esta ronda (C22, C35, C36).
4. Cuando el informe citado tiene una sección de conclusiones o de
   pendientes ("Lo que este informe deja PENDIENTE", "§8", etc.), leerla
   entera y comprobar que ninguna frase contradice el veredicto de la fila.

Para las **73 filas verdes y las 6 históricas**, verificación más ligera pero
real: la cita existe, y se buscó (mismo `grep`) si el informe que la sostiene
declara, en su propia sección de pendientes, algo que la fila da por cerrado.

**Resultado:** de 111 filas, **106 estaban bien** (el emoji y el enunciado
son fieles a su evidencia) y **5 tenían un defecto**, con dos clases de
defecto distintas:

- **C22** — emoji equivocado puro: el informe que la cierra existe desde el
  30/08 (`bench/patron-multifichero.md`, commit `8765303`) y la fila seguía
  🔴. Ya estaba corregida en el registro de main antes de que esta rama
  arrancara del todo, pero **no** en el `origin/main` real contra el que se
  rebasó esta rama — se corrigió aquí.
- **C28** — el peor tipo de defecto, y el que ninguna comprobación automática
  puede cazar: **una fila verde cuya propia evidencia la contradice.** Ver
  §2.1.
- **C32** — una fila roja que pedía "arbitrar una contradicción" cuando la
  arbitración **ya había ocurrido**, en otras dos filas del mismo inventario,
  sin que nadie cerrara ésta. Ver §2.2.
- **C41** — inconsistencia interna menor: decía "diecisiete" al principio y
  "los veinte están congelados" al final, residuo de una redacción anterior
  a que la cifra bajara de 20 a 17. Corregido a "diecisiete… dieciocho".
- **C42** — enunciado caducado por un commit del propio master (`0999538`,
  01/09) que resolvió justo lo que la fila describía como pendiente
  (medición en la plataforma equivocada + `continue-on-error` ocultando
  fallos), sin que la fila se hubiera actualizado. Ver §2.3.

Emojis movidos: **C22** 🔴→🟢, **C28** 🟢→🟡, **C32** 🔴→🟡. C41 y C42 cambian
de texto, no de color. Saldo neto: 🔴 −2, 🟡 +2, 🟢 sin cambio neto (−1 +1).

---

## 2. Los tres hallazgos con detalle

### 2.1 · C28 — verde y contradicha por su propio informe (trampa 58/44)

La fila decía, y seguía en 🟢 **CERRADO**: *"de los 56, el `rc` dice cuál de
cinco remedios aplica: **FATE cierra 15**, ocho no son formatos y **21 se
cierran con una invocación mejor**"*.

`bench/firmas-cierre.md` §8 ("Lo que este informe deja PENDIENTE"), que es el
informe que la propia fila cita, dice lo contrario en dos ítems:

> 2. Los 15 de los 56 que sí necesitan otro motor... Aquí sí hace falta FATE
>    o una build de ffmpeg con más codificadores. **No lo he descargado**,
>    como pedía el encargo.
> 3. Los 23 que se cierran con la invocación, de los que **6 ya están
>    probados**. Faltan 17...

Es decir: "FATE cierra 15" era la PROPUESTA, no el cierre (MEDIDO: el propio
texto dice "no lo he descargado"); y la cifra de la fila ("21 con invocación
mejor") ni siquiera coincide con la del informe (23, de los que solo 6
probados, 17 pendientes). Verificado además que no hay ningún corpus FATE ni
`MANIFIESTO.md` en el árbol que indique que se materializó después (no es un
caso de la trampa 95 — el bloqueo es real, no un activo podado).

**Movida a 🟡 PARCIAL**, conservando lo genuinamente cerrado (la
reclasificación 86 = 56+17+13, y los 17/17 de "banner del escritor") y
declarando el residuo real: FATE-15 sin descargar (comparte bloqueo con
`C16`), 17/23 de invocación sin probar, 8 `sin_clasificar` sin resondear.

### 2.2 · C32 — roja pidiendo algo que ya se hizo en otro sitio

La fila pedía arbitrar una contradicción entre `hito3-mudanza.md` §6 y
`firmas-contrato.md` §10 sobre dos cifras: el ratio de RAM (×1 según
`firmas-contrato.md`, ×21,3/×7,0 según `hito3-mudanza.md`) y si `.pcd`
produce un falso positivo.

**Esa arbitración ya está en el inventario**, en dos filas que nadie conectó
con C32:

- **C31** (🔴, enunciado ya corregido en una ronda anterior) declara MEDIDAS
  las dos cifras exactas que C32 pedía arbitrar, citando `hito3-mudanza.md`
  §6.1-6.3 contra `firmas-contrato.md` §10.2-10.4/§10.8.
- **C37** (🟢 CERRADO) mide además la consecuencia downstream: el contrato
  completo sobre un `.pcd` legítimo devuelve `fallo`.

Verificado línea por línea que `bench/firmas-contrato.md` §10 **nunca se
editó** — sigue con las cifras originales. Es decir, la ACCIÓN literal que
`hito3-mudanza.md` §7 pedía ("corrige `firmas-contrato.md` §10") no se hizo,
pero la PREGUNTA de fondo ("¿quién tiene razón?") está resuelta y con número
desde hace días, en otro sitio del mismo documento.

**Movida a 🟡 PARCIAL, arbitrada por C31/C37** — ni "contradicción viva" (ya
no lo es) ni "cerrada" (la edición pedida no se hizo).

### 2.3 · C42 — enunciado caducado por un commit del mismo día

La fila describía `ci/linux-apto.json` como medido en la plataforma
equivocada (WSL2/DrvFs/Python 3.14, "11 aptos, 262 pruebas") con el job
`linux` de la CI escondiendo fallos detrás de `continue-on-error: true`, y
proponía como cierre "quitar ese `continue-on-error`".

El commit `0999538` (01/09, 12:40, del propio master, título *"La lista de
aptos, medida donde toca: 7 de 17, y se acaba el falso verde"*) ya hizo
exactamente eso, verificado hoy contra el código:

- `ci/linux-apto.json` trae hoy `"medido_en": "runner de GitHub Actions,
  ejecución 33538561732"`, con **7 aptos, 198 pruebas, 3,4 s** — de las dos
  listas (11 y 7) **solo coinciden cinco módulos**.
- `.github/workflows/suite.yml`, job `linux`: **no tiene** `continue-on-error`
  (verificado leyendo el fichero completo); el comentario del propio job lo
  dice: *"Con la lista medida donde toca, ya no hace falta esconder nada"*.
  Sólo el job `deriva` (cron/manual, informativo por diseño) lo conserva.

**Reescrita, sin cambiar el color** (sigue 🔴): lo que la fila describía como
problema ya está resuelto, pero el residuo real —10 de 17 módulos que no
corren en el runner de Linux por pedir GPU/motores/NTFS, 1 se cuelga y 9
fallan— sigue siendo deuda genuina y así lo dice ya `PENDIENTE.md` §3. No se
cierra con más CI: es la brecha estructural de `CONTRIBUTING.md` §1.

---

## 3. Tabla de las 111 filas

`E0` = emoji con el que empezó la ronda (el de `origin/main` antes de esta
rama). `E1` = emoji tras el saneo. Cuando difieren, van en **negrita**. La
columna "cita" es la primera cláusula de cita de la fila ya en
`ESTADO-Y-REPARTO.md` §3 (informe, commit o sección) — todas verificadas
existentes en este árbol.

### A · Deuda documental (9 filas + 6 tachadas históricas ya integradas en A5/A7/A9)

| # | E0 | E1 | Cita |
|---|:-:|:-:|---|
| A1 | 🟢 | 🟢 | `consolidacion-21ago.md` |
| A2 | 🟢 | 🟢 | `consolidacion-21ago.md` |
| A3 | 🟢 | 🟢 | `consolidacion-21ago.md` |
| A4 | 🟢 | 🟢 | `consolidacion-21ago.md` |
| A6 | 🟢 | 🟢 | `consolidacion-2-21ago.md` |
| A8 | 🟢 | 🟢 | `consolidacion-3-21ago.md` |
| A5 | 🟢 | 🟢 | commit `dcd4057` |
| A7 | 🟢 | 🟢 | `metrica-ocr.md` |
| A9 | 🟢 | 🟢 | índice de §1 verificado (67 informes citados hoy, `ci/integridad.py` en verde) |

### B · GPU (31 filas incl. históricas)

| # | E0 | E1 | Cita |
|---|:-:|:-:|---|
| B1 | 🟢 | 🟢 | `MANIFIESTO-d4.md` |
| B2 | 🟢 | 🟢 | G1 |
| B3 | 🔴 | 🔴 | sin informe — `bench/salidas-marker/` sigue solo un `logs/` vacío |
| B4 | 🔴 | 🔴 | `gpu-fase1.md` §B.3, sin dato de VRAM |
| B5 | 🔴 | 🔴 | cero menciones en `bench/` |
| B6 | 🟢 | 🟢 | `hito2-nvenc.md` |
| B7 | 🟡 | 🟡 | `corpus-d4.md` §11, `verificador-ghostscript.md` §5.4 (verificado: ambas secciones existen y dicen lo citado) |
| B8 | 🔴 | 🔴 | sin informe posterior sobre `-deskew` |
| B9 | 🟢 | 🟢 | P1 |
| B10 | 🟢 | 🟢 | P1 |
| B11 | 🟢 | 🟢 | `ocr-produccion-sidecar.md` |
| B12 | 🟢 | 🟢 | `corpus-d5.md` §0.8, §5 |
| B13 | 🟢 | 🟢 | `k-por-motor.md` |
| B14 | 🟢 | 🟢 | refutado su enunciado, cerrado |
| B15 | 🟢 | 🟢 | `corpus-d5.md` |
| B16 | 🔴 | 🔴 | `ppp-y-normalizacion.md` §8, `k-por-motor.md` §9 — sin cerrar, previsto para ronda 4 (`gpu/k-y-oem`, `PENDIENTE.md` §2) |
| B17 | 🟢 | 🟢 | `psm-y-rasterizador.md` |
| B18 | 🟢 | 🟢 | `psm-y-rasterizador.md` §2, `corpus-d5.md` §4 |
| B19 | 🟢 | 🟢 | `corpus-d5.md` |
| B20 | 🔴 | 🔴 | `corpus-d5.md` §8 — sin informe posterior |
| B21 | 🟢 | 🟢 | `psm-suelo-ppp.md` — MOVIDA por el carril GPU en esta misma ronda 3, ya en `origin/main` (commit `f33e47f`/`2102556`); confirmado texto y cifras contra el informe |
| B22 | 🟡 | 🟡 | ídem — PARCIAL confirmado, queda sondear cajas detectadas |
| B23 | 🔴 | 🔴 | `k-por-motor.md` §9 — previsto ronda 4 |
| B24 | 🔴 | 🔴 | `psm-y-rasterizador.md` §9 — previsto ronda 4 |
| B25 | 🟢 | 🟢 | `phys-multimotor.md` |
| B26 | 🟢 | 🟢 | G5, trampa 67 |

### C · Sin GPU (45 filas incl. históricas)

| # | E0 | E1 | Cita |
|---|:-:|:-:|---|
| C1 | 🟢 | 🟢 | V1 |
| C2 | 🟢 | 🟢 | V1 |
| C3 | 🟢 | 🟢 | E1 |
| C4 | 🟢 | 🟢 | `mcp-cabos-2.md` |
| C5 | 🟡 | 🟡 | `mcp-cabos-2.md` §5.1 — bloqueado por `0x8007274c`, confirmado |
| C6 | 🔴 | 🔴 | `saturacion-herramientas.md` §8 — confirmado: no hay clave de API en el entorno |
| C7 | 🔴 | 🔴 | `HUECOS.md` §2 |
| C8 | 🟢 | 🟢 | E1 |
| C9 | 🟢 | 🟢 | P3 |
| C10 | 🟢 | 🟢 | P3 |
| C11 | 🟢 | 🟢 | P3 |
| C12 | 🟢 | 🟢 | P3 |
| C13 | 🟢 | 🟢 | P2 |
| C14 | 🟢 | 🟢 | F1 |
| C15 | 🟢 | 🟢 | P2 |
| C16 | 🔴 | 🔴 | comparte bloqueo FATE con C28 — confirmado, ninguno de los dos lo tiene |
| C17 | 🟢 | 🟢 | P2 |
| C18 | 🔴 | 🔴 | `verificador-ghostscript.md` §5.7 — sin reproducir aún |
| C19 | 🟢 | 🟢 | `contrato-familia-resvg.md` |
| C20 | 🔴 | 🔴 | sin validar fuera de Ghostscript |
| C21 | 🟢 | 🟢 | trampa 51 |
| C22 | **🔴** | **🟢** | `patron-multifichero.md`, commit `8765303` — **corregida en esta ronda** |
| C23 | 🔴 | 🔴 | `contrato-quinto-punto.md` §4.3 |
| C24 | 🟡 | 🟡 | `psm-y-rasterizador.md` §2.1/§6.1 — residuo de Ghostscript sin sondear |
| C25 | 🟡 | 🟡 | `bitrate-por-pista.md` (3 pasadas reconciliadas) |
| C26 | 🟢 | 🟢 | `lock-de-maquina.md` |
| C27 | 🔴 | 🔴 | `contrato-familia-resvg.md` — abierta por decisión, confirmada |
| C28 | **🟢** | **🟡** | `firmas-cierre.md` §4.4/§8 — **corregida en esta ronda, ver §2.1** |
| C29 | 🟢 | 🟢 | trampa 48 |
| C30 | 🟢 | 🟢 | F2 |
| C31 | 🔴 | 🔴 | `hito3-mudanza.md` §6 — abierta, confirmada |
| C32 | **🔴** | **🟡** | `hito3-mudanza.md` §6-7 — **corregida en esta ronda, ver §2.2** |
| C33 | 🟢 | 🟢 | commit `c2f6a59` |
| C34 | 🟢 | 🟢 | `cancelacion-y-servicio.md` |
| C35 | 🟡 | 🟡 | `gotenberg-y-mcp.md` — ya corregida en `origin/main` antes de esta rama; confirmado que sigue pendiente la latencia n≥9 |
| C36 | 🟡 | 🟡 | ídem — confirmado que siguen 7 vivos de 9 |
| C37 | 🟢 | 🟢 | F2 |
| C38 | 🟢 | 🟢 | worker1, `lock-desde-python.md` |
| C39 | 🟢 | 🟢 | worker1, `lock-desde-python.md` |
| C40 | 🟡 | 🟡 | trampa 106, confirmado `ci/heredado.json["binarios"]` = 3 |
| C41 | 🔴 | 🔴 | esta misma tarea — texto corregido ("diecisiete…dieciocho"), ver §4 |
| C42 | 🔴 | 🔴 | **reescrita en esta ronda, ver §2.3** — commit `0999538`, residuo real 10/17 |
| C43 | 🔴 | 🔴 | trampa 105 — decisión pendiente, confirmada sin resolver en el código |

### N · Deuda del paquete `filex/` (28 filas)

Auditadas las 28: **todas correctas, ninguna requiere cambio.** Verificación
específica de las tres que llevaban más riesgo:

| # | E0 | E1 | Cita / verificación |
|---|:-:|:-:|---|
| N1–N8, N10–N25, N28 | 🟢 | 🟢 | 23 filas cerradas, citas confirmadas contra código e informe (ver detalle abajo) |
| N9 | 🔴 | 🔴 | Confirmado en código: `filex/confinamiento.py` sigue aplicando el predicado léxico (R1) antes de `realpath` — el oráculo temporal de R4 sigue sin decidirse |
| N15 | 🟢 | 🟢 | `huella-y-tablas.md` — el incidente de la trampa 97 (revert que caducó 70 aristas de ffmpeg) es posterior y NO contamina esta fila; se resondeó aparte |
| N26 | 🔴 | 🔴 | `hito6-sidecar.md` — sin informe posterior que lo cierre |
| N27 | 🔴 | 🔴 | ídem §8.3 — sin informe posterior |
| N28 | 🟢 | 🟢 | Confirmada la cita correcta: `bitrate-por-pista.md` (commit `d2bcb7b`, 31/08 13:27) es el informe que cierra N28 retirando el parche; `patron-multifichero.md` (commit `8765303`, 31/08 11:10, más temprano) proponía el enfoque de restar `bitrate_audio_bps`, que quedó refutado por el propio N28. Las dos citas no compiten: son antes/después del mismo pendiente |

**N1, N6**: confirmado `filex/mcp.py` mide hoy 26 968 B (−40,2 % desde 45 123
B, como dice la fila). **N7, N38(C38)**: mutex `Global\filex-*` presente en
`filex/cerrojo.py` y `filex/gpu.py`. **N11**: `olvidar_hilo()` sin llamadas
manuales fuera de las pruebas AST que lo prohíben.

---

## 4. Tarea B — C41: los 17 manifiestos

Los 17 directorios de `ci/heredado.json["manifiestos"]` tienen ya
`bench/salidas-<nombre>/MANIFIESTO.md`, cada uno con tabla de fichero /
tamaño / SHA-256 / orden exacta. La clave `manifiestos` de `ci/heredado.json`
queda **vacía** — el trinquete lo exige (regla de encoger, `CONTRIBUTING.md`
§6).

Los hashes de todos los manifiestos se recalcularon **hoy** contra el árbol
actual (`sha256sum`/`stat`), no se copiaron a ciegas de los informes
originales, y en los casos donde el informe fuente ya traía su propia tabla
de sha256 se usó como referencia y se confirmó que coincide (no hubo
discrepancias).

| Directorio | Ficheros | Informe(s) | Nota |
|---|--:|---|---|
| `salidas-aristas-tasa` | 2 | `aristas-y-tasa-audio.md` | Completo, hashes confirmados contra el informe |
| `salidas-bitrate-pista` | 5 | `bitrate-por-pista.md` | Completo |
| `salidas-confinamiento-mm` | 34 | `confinamiento-multimedia.md` | Completo, 3 PENDIENTE declarados (venvs `.venv-mm-ffmpeg`/`.venv-mm-vamcp` ya borrados, ruta absoluta de otro checkout) |
| `salidas-cota-audio` | 3 | **ninguno** — huérfano | Ver detalle abajo |
| `salidas-fidelidad` | 9 | `fidelidad-caminos.md`, `fidelidad-y-nucleo.md` | Completo |
| `salidas-hito3` | 12 | `hito3-mudanza.md` §8 | Completo, el propio informe ya traía la tabla |
| `salidas-huella` | 23 | `huella-y-tablas.md` | Completo |
| `salidas-lock` | 10 | `lock-de-maquina.md` | Completo. **PENDIENTE declarado**: las 5 pruebas dependen de Git Bash en Windows real (`/proc/$$/winpid`, `tasklist`) y no son reproducibles desde este WSL2 (trampa 90) |
| `salidas-lock-interpretes` | 4 | `lock-entre-interpretes.md` | Completo, sí se pudo reejecutar parcialmente desde WSL2 |
| `salidas-mcp` | 31 | `mcp-cabos-sueltos.md`, `mcp-ergonomia.md`, `saturacion-herramientas.md` | Completo, incluye fixtures de entrada declaradas como tales (no confundidas con salidas) |
| `salidas-mcp-cabos` | 75 | `mcp-cabos-sueltos.md`, `mcp-cabos-2.md` | Completo, agrupado por "cabo" donde una misma orden genera varios `.txt` casi idénticos (declarado explícitamente, no oculto) |
| `salidas-mcp-refs` | 109 | `mcp-refs-confinamiento.md`, `mcp-refs-multimedia.md`, `saturacion-herramientas.md` | Completo, incluidos los 2 ficheros con el carácter especial `<U+F03A>` (ADS de Windows, `dentro.txt<U+F03A>oculto`/`secreto.txt<U+F03A>oculto`) — **no confundir con los ficheros `:oculto` de un solo proceso, NO versionados, que quedan fuera del manifiesto por diseño** |
| `salidas-patron-multi` | 2 | `patron-multifichero.md` | Completo |
| `salidas-saturacion` | 26 | `saturacion-herramientas.md` | Completo; 1 PENDIENTE declarado por requerir clave de API (C6) |
| `salidas-sdk-mcp` | 59 | `sdk-mcp-capacidades.md` | Completo, matriz cliente×servidor documentada con la orden parametrizada |
| `salidas-verificacion` | 18 | `coste-verificacion.md`, `verificador-fidelidad.md`, `bitrate-y-lock.md` | Completo |
| `salidas-verificacion-fidelidad` | 13 | `verificador-fidelidad.md` §8 | Completo, orden por subcomando de `medir_fid.py` |

### El caso `salidas-cota-audio`: huérfano, sin informe, con error reproducido

Ningún informe de `bench/` cita este directorio (`grep -rl
"salidas-cota-audio" bench/*.md` no da resultados). Es un intento **abandonado
y con error** de N28, de la misma tanda que `bench/patron-multifichero.md`
(commit `8765303`): calcular cotas de bitrate por (códec, build) — enfoque
descartado a favor del más simple que sí llegó a informe y que a su vez fue
refutado y retirado por `bench/bitrate-por-pista.md` (commit `d2bcb7b`).

**MEDIDO, tres reejecuciones independientes** (timeouts de 180 s y 60 s):
`python3 bench/salidas-cota-audio/medir.py` reproduce el mismo `ValueError:
max() iterable argument is empty` en `tabla()` (`medir.py:54`), en las tres
pasadas. Causa raíz leída en el código, no adivinada: para `libopus` las 48
filas de la matriz fallan sistemáticamente por incompatibilidad de contenedor
(`.webm` con vídeo `libx264`, cuando WebM sólo admite VP8/VP9/AV1), dejando
la lista de `factor_max` vacía y `max([])` revienta. **Corrección sobre un
borrador propio anterior de este mismo manifiesto**: se había afirmado que
`matriz_parcial.json` sale "byte a byte idéntico" entre ejecuciones; **es
falso**, verificado con `sha256sum` (el hash cambia siempre porque el campo
`ms` de cada invocación de `ffmpeg` no es determinista) — lo que sí es
determinista es la estructura (96 filas, misma clasificación por `rc`, mismo
punto de fallo). El manifiesto quedó corregido con esa distinción.

**PENDIENTE, declarado**: no se corrige `medir.py` (fuera del alcance de
C41, que es documentar) ni se declara en `ci/evidencia-irreproducible.txt`
(no es evidencia forense de terceros: es un experimento propio, incompleto,
y regenerable — sólo que reproduce un fallo, no un éxito).

---

## 5. Verificación de este PR

- **MEDIDO:** `python3 ci/integridad.py` → `Todo en orden` (9/9 comprobaciones
  en verde), tras corregir dos defectos que el propio saneo introdujo y que
  la CI cazó en el acto: dos filas (`C22`, `C32`) llevaban emoji de OTRAS
  filas citadas dentro de su propia prosa (`**C31** (🔴 ...)`, `**C37** (🟢
  ...)`), lo que rompía `un-emoji-por-fila`; se reescribieron sin emoji en la
  prosa.
- **MEDIDO:** recuento de §3 actualizado a `6 ⚫ · 22 🔴 · 10 🟡 · 73 🟢` sobre
  111 filas, en la tabla de la leyenda y en la línea "Salida esperada hoy",
  coincide con lo que mide `ci/integridad.py inventario`.
- **MEDIDO:** `ci/heredado.json["manifiestos"]` vacío; `ci/integridad.py
  manifiestos` → `0 sin MANIFIESTO heredados · 0 nuevos · 0 arreglados`.
- **Interprete:** Python de WSL2 (3.x nativo del contenedor de este
  worktree), no el `python.exe` de Windows del proyecto — esta tanda es
  documental y de lectura de código, no ejecuta la suite `win32`.
- **Entorno:** sin Docker levantado en esta tanda (no hizo falta); sin GPU
  (no se tocó, carril ajeno); WSL2 sobre este worktree, no la máquina de
  Windows del proyecto.
- **Qué queda fuera y por qué:** la suite completa de `pruebas/` no se
  corrió en esta tanda — el trabajo es documental (§3 de `ESTADO-Y-REPARTO.md`
  y 17 manifiestos), no toca `filex/`. La aceptación de la medición del
  proyecto (trampa 98) se hace ejecutando la suite en Windows con Docker,
  responsabilidad del master antes de fusionar, según `CONTRIBUTING.md` §1.
- **Estado de la máquina:** sin indicios de contención — todas las
  operaciones de esta tanda son lectura de ficheros, `git`, y tres
  reejecuciones cortas de `bench/salidas-cota-audio/medir.py` (con `ffmpeg`
  nativo de WSL2), sin otro proceso pesado corriendo a la vez que se
  detectara.

## 6. Riesgos y bloqueos

- Ninguno nuevo. C16 y C28 comparten el mismo bloqueo real (corpus FATE de
  ffmpeg, ~1 GB, no descargado) — cerrar uno abarata el otro, como ya decía
  C16 antes de esta ronda.
- `salidas-cota-audio` queda como deuda documental menor: un experimento
  propio, abandonado, con manifiesto honesto (incluye el error). No bloquea
  nada y no se declaró en `ci/evidencia-irreproducible.txt` porque no es la
  clase de evidencia que esa lista protege.

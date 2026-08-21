# 00 — Implementación de referencia oficial MCP: `filesystem`, `everything`, `fetch`

Repo analizado: `D:\Work\research\FileX\repos\mcp-refs\servers\src\` (modelcontextprotocol/servers, MIT).
Tarea de solo lectura. Todas las afirmaciones técnicas llevan cita `fichero:línea`. Lo que no he podido verificar en el código está marcado como **[no verificado]**.

---

## 0. Corrección de una afirmación previa del proyecto

`ANALISIS-COMPLETO.md:593` afirma:

> «La lista blanca de raíces —denegar por defecto, resolución canónica, y error indistinguible entre "prohibido" y "no existe" para no ser un oráculo de existencia— hay que diseñarla desde cero.»

y `PLAN-ORQUESTADOR.md:266-271` la repite bajo el epígrafe «Seguridad — lo que hay que inventar».

**Es falsa en su primera mitad y correcta en la segunda.**

- **Falsa**: la lista blanca de raíces con denegación por defecto y resolución canónica **ya existe, está probada y es MIT**, en `repos/mcp-refs/servers/src/filesystem/`. Son ~200 líneas de lógica de seguridad real (`lib.ts:99-140` + `path-validation.ts:11-86`) más ~1000 líneas de tests que documentan explícitamente qué ataques para y cuáles **no** (`__tests__/path-validation.test.ts`, 997 líneas). No hay que diseñarla desde cero: hay que **portarla a Python y arreglar sus tres huecos conocidos**.
- **Correcta**: lo del oráculo de existencia sí es trabajo propio, porque **la referencia oficial no lo hace** — distingue explícitamente "prohibido" de "no existe" y además filtra rutas absolutas y la lista blanca completa en los mensajes de error (§A.4).

Además el proyecto se está perdiendo un mecanismo del propio protocolo: **MCP Roots** (§A.5), que resuelve la negociación cliente↔servidor de qué directorios son accesibles sin inventar nada.

---

## A) `servers/src/filesystem` — el confinamiento

Ficheros y tamaños (1 501 líneas totales):

| Fichero | Líneas | Contenido |
|---|---|---|
| `index.ts` | 785 | arranque, resolución de la allowlist, registro de 14 herramientas, negociación de roots |
| `lib.ts` | 415 | `validatePath` y las operaciones de fichero |
| `path-utils.ts` | 125 | normalización sintáctica y `expandHome` |
| `path-validation.ts` | 86 | **el predicado de contención**, lógica pura sin E/S |
| `roots-utils.ts` | 76 | conversión de `Root[]` MCP → directorios validados |

### A.1 Algoritmo completo de confinamiento

El confinamiento tiene **dos capas**: un predicado puramente léxico (`isPathWithinAllowedDirectories`) y un envoltorio con E/S (`validatePath`) que resuelve enlaces simbólicos. La clave del diseño es que **el predicado léxico se aplica ANTES de tocar el sistema de ficheros** (`lib.ts:107-111`, comentario `// Security: Check if path is within allowed directories before any file operations`).

#### Paso 0 — construcción de la allowlist (arranque)

`index.ts:45-67`. Por cada directorio pasado por argumentos:

1. `expandHome(dir)` — expande `~` (`path-utils.ts:119-124`, solo `~/…` o `~` exacto; **no** expande `~usuario`).
2. `path.resolve(expanded)` → absoluto (`index.ts:48`).
3. `normalizePath(absolute)` → forma canónica sintáctica (`index.ts:49`).
4. `fs.realpath(absolute)` → resolución de enlaces simbólicos (`index.ts:53`), con el comentario `// Security: Resolve symlinks in allowed directories during startup`.
5. **Se guardan ambas formas si difieren** (`index.ts:57-59`): `[normalizedOriginal, normalizedResolved]`.
6. Si `realpath` falla (directorio inexistente) se guarda solo la forma sintáctica (`index.ts:61-65`), «*This allows configuring allowed dirs that will be created later*».

Después se filtra a los que existen y son directorios (`index.ts:70-82`) y se aborta solo si **ninguno** es accesible (`index.ts:85-88`). La lista final se inyecta en el estado global de `lib.ts` vía `setAllowedDirectories` (`index.ts:93`, `lib.ts:14-16`).

#### Paso 1 — `validatePath(requestedPath)` (`lib.ts:99-140`)

Orden exacto de comprobaciones:

1. **`expandHome`** (`lib.ts:100`) — `~` → `os.homedir()`.
2. **Absolutización** (`lib.ts:101-103`):
   - si ya es absoluta → `path.resolve`;
   - si es **relativa** → `resolveRelativePathAgainstAllowedDirectories` (`lib.ts:76-96`): prueba a resolverla contra *cada* directorio permitido y devuelve el primer candidato que caiga dentro de la allowlist (`lib.ts:83-91`); si ninguno vale, usa el primer directorio permitido como base (`lib.ts:95`), o `process.cwd()` si la allowlist está vacía (`lib.ts:77-80`).
3. **`normalizePath`** (`lib.ts:105`) — ver §A.3.
4. **Predicado léxico** `isPathWithinAllowedDirectories` (`lib.ts:108`). Si falla → `throw` inmediato, **sin haber tocado el disco** (`lib.ts:109-111`).
5. **Resolución real** `fs.realpath(absolute)` (`lib.ts:116`) y **segunda aplicación del predicado** sobre la ruta real (`lib.ts:118`). Si la ruta real cae fuera → `throw` (`lib.ts:119`). Si pasa, **devuelve `realPath`**, no la ruta pedida (`lib.ts:121`) — el resto del servidor opera siempre sobre la ruta canónica.
6. **Camino ENOENT** (`lib.ts:122-137`): si el fichero no existe (caso normal al crear ficheros nuevos), se coge `path.dirname(absolute)` (`lib.ts:126`), se hace `realpath` **del padre** (`lib.ts:128`) y se vuelve a aplicar el predicado sobre el padre real (`lib.ts:130`). Si el padre real cae fuera → `throw` (`lib.ts:131`). Si pasa, devuelve `absolute` — **la ruta sin resolver**, no `realParentPath + basename` (`lib.ts:133`). Si el padre tampoco existe → `throw 'Parent directory does not exist'` (`lib.ts:135`).
7. Cualquier otro error de E/S se propaga tal cual (`lib.ts:138`).

#### Paso 2 — `isPathWithinAllowedDirectories` (`path-validation.ts:11-86`)

Predicado puro, **sin E/S**, "fail-closed" en todos los caminos de error salvo dos:

1. Tipos: si `absolutePath` no es `string` o `allowedDirectories` no es array → `false` (`path-validation.ts:13-15`).
2. Vacíos: ruta vacía **o allowlist vacía** → `false` (`path-validation.ts:18-20`). Es decir, **allowlist vacía = denegar todo**.
3. **Byte nulo** en la ruta → `false` (`path-validation.ts:23-25`). Protege contra truncamiento `foo.txt\x00.png`.
4. `path.resolve(path.normalize(absolutePath))` (`path-validation.ts:30`) — colapsa `.` y `..` **léxicamente** (sin tocar disco).
5. Si tras normalizar no es absoluta → **`throw`**, no `false` (`path-validation.ts:36-38`). Es una de las dos excepciones al fail-closed silencioso.
6. Para **cada** directorio permitido (`path-validation.ts:41`):
   - entrada no-string o vacía → se salta (`path-validation.ts:42-44`);
   - byte nulo en el directorio permitido → se salta (`path-validation.ts:47-49`);
   - misma normalización (`path-validation.ts:54`); si tras normalizar no es absoluto → **`throw`** (`path-validation.ts:60-62`);
   - **igualdad exacta** → `true` (`path-validation.ts:66-68`);
   - caso raíz Unix `/` → basta con que empiece por el separador (`path-validation.ts:72-74`);
   - caso raíz de unidad Windows `C:\` → compara la **letra de unidad en minúsculas** y luego prefijo (`path-validation.ts:77-82`). Es el **único** punto de todo el código donde hay comparación case-insensitive;
   - caso general → **`normalizedPath.startsWith(normalizedDir + path.sep)`** (`path-validation.ts:84`).

El `+ path.sep` de la línea 84 es lo que cierra la **vulnerabilidad de prefijo**: `/home/user/project_backup` no cae dentro de `/home/user/project`. Está explícitamente testeado en `__tests__/path-validation.test.ts:63` (`'blocks similar directory names (prefix vulnerability)'`) y en Windows en `:75-76` (`C:\Users\project2`, `C:\Users\project_backup` → `false`).

**Resumen de lo que rechaza**: rutas relativas no resolubles, `..` que escapan (normalización léxica previa), bytes nulos, tipos no-string, allowlist vacía, hermanos con prefijo común, enlaces simbólicos cuyo destino real cae fuera, ficheros nuevos cuyo directorio padre real cae fuera, y cruces de unidad en Windows.

### A.2 Enlaces simbólicos: por qué guarda original **y** resuelta

`index.ts:41-44` lo dice literalmente:

> *We store BOTH the original path AND the resolved path to handle symlinks correctly. This fixes the macOS `/tmp` -> `/private/tmp` symlink issue where users specify `/tmp` but the resolved path is `/private/tmp`.*

**El motivo NO es de seguridad, es de usabilidad — pero tiene consecuencia de seguridad.** El razonamiento:

- `validatePath` **siempre** devuelve la ruta canonizada por `realpath` (`lib.ts:116,121`). Por tanto todo lo que se compara contra la allowlist en el paso 5 está ya en forma real.
- Si el usuario arranca el servidor con `--allow /tmp` en macOS y la allowlist solo guardara `/tmp`, entonces `realpath('/tmp/x.pdf') = '/private/tmp/x.pdf'` **no** empezaría por `/tmp/` y todo quedaría denegado: falso negativo total.
- Si la allowlist solo guardara `/private/tmp`, entonces el predicado léxico del paso 4 (que se aplica sobre la ruta **pedida**, sin resolver) rechazaría `/tmp/x.pdf` antes de llegar a resolverla.
- Guardando ambas, ambos pasos encuentran una coincidencia. Esto está testeado en `__tests__/path-validation.test.ts:527` (`'validates paths correctly when allowed directory is resolved from symlink'`) y `:570` (`'allows paths through both original and resolved symlink directories'`).

**Qué ataque previene la resolución en sí** (que es cosa distinta): que el agente cree, o encuentre, un enlace simbólico *dentro* de la raíz permitida apuntando *fuera*, y lo use como puerta. El comentario de `lib.ts:113-114` es explícito: *«This prevents attackers from creating symlinks that point outside allowed directories»*. Cubre también **cadenas anidadas** de enlaces, porque `realpath` resuelve la cadena entera — testeado en `__tests__/path-validation.test.ts:614` (`'resolves nested symlink chains completely'`).

#### ¿Valida los enlaces creados **después** del arranque?

**Sí, pero con un hueco de TOCTOU que la propia referencia documenta como test.**

- **Sí**: `fs.realpath` se ejecuta **en cada llamada** a `validatePath` (`lib.ts:116`), no una sola vez al arrancar. Un enlace creado a las 12:00 se detecta en la llamada de las 12:01. Lo mismo vale para un **directorio intermedio** convertido en enlace: `realpath` resuelve la ruta completa, componente a componente.
- **Pero**: entre la validación (`lib.ts:116`) y la operación real (`fs.readFile`, `fs.writeFile`…) hay una ventana. La referencia tiene **tests que demuestran el agujero, no que lo tapen**:
  - `__tests__/path-validation.test.ts:679` — `'demonstrates symlink race condition allows writing outside allowed directories'`;
  - `__tests__/path-validation.test.ts:932` — `'demonstrates race condition in read operations'`: se valida `readable.txt`, se sustituye por un enlace a `secret.txt` fuera de la raíz, y la lectura devuelve `SECRET CONTENT` (`:958-960`);
  - `__tests__/path-validation.test.ts:784` — `'demonstrates parent directory symlink traversal'`: si `sub1/` se convierte en enlace hacia el directorio prohibido, se escribe fuera.

Mitigaciones que **sí** aplica la referencia, pero solo en escritura:
- `writeFileContent` abre con flag `'wx'` (creación exclusiva) — `lib.ts:161-165`, comentario `// Security: 'wx' flag ensures exclusive creation - fails if file/symlink exists, preventing writes through pre-existing symlinks`.
- Si ya existe, escribe a `${filePath}.${randomBytes(16).toString('hex')}.tmp` y hace `fs.rename` **atómico** (`lib.ts:167-180`), porque `rename` **no sigue enlaces**: reemplaza el enlace por un fichero regular en vez de escribir a través de él. Verificado en `__tests__/path-validation.test.ts:964` (`'verifies rename does not follow symlinks'`).
- Idéntico patrón en `applyFileEdits` (`lib.ts:265-279`).

**No hay mitigación equivalente para lectura.** `readFileContent` es un `fs.readFile` desnudo (`lib.ts:157-159`).

Detalle adicional: `searchFilesWithValidation` recursa solo cuando `entry.isDirectory()` sobre un `Dirent` de `readdir({withFileTypes:true})` (`lib.ts:404-406`); por la semántica de `Dirent` un enlace a directorio reporta `isSymbolicLink()===true` e `isDirectory()===false`, así que la búsqueda recursiva no entra en directorios enlazados. **[no verificado en tests de este repo]** — no encontré test que lo fije; lo deduzco de la API de Node, no del código.

### A.3 Casos límite contemplados (y los que no)

`normalizePath` (`path-utils.ts:39-112`) hace, en este orden: quita comillas y espacios envolventes (`:41`), decide si es ruta Unix a preservar (`:46-53`), colapsa `//`→`/` y quita barra final (`:58`), convierte rutas estilo `/c/…` a `C:\…` solo en Windows (`:63` → `convertToWindowsPath:19-23`), normaliza `\\` preservando el prefijo UNC (`:66-78`), añade separador a una letra de unidad desnuda `C:` → `C:\` (`:82-84`, con el comentario de que si no `path.normalize` devuelve `C:.` «*which can break path validation*»), aplica `path.normalize` (`:87`), restaura la barra UNC que `normalize` se come (`:90-92`) y **capitaliza la letra de unidad** (`:98-100`).

| Caso | ¿Contemplado? | Dónde |
|---|---|---|
| Rutas relativas | **Sí**, con semántica propia: se resuelven contra cada raíz permitida hasta encontrar una que encaje | `lib.ts:76-96`, `lib.ts:101-103` |
| `..` | **Sí**, colapso léxico antes de comparar | `path-validation.ts:30`; tests `:270`, `:286`, `:294` |
| `..` en la propia allowlist | **Sí**, se normaliza igual | `path-validation.ts:54`; test `:413` |
| Rutas absolutas | **Sí**, obligatorias tras normalizar; si no, `throw` | `path-validation.ts:36-38`, `:60-62` |
| `~` | **Sí**, solo `~` y `~/…`. **No** soporta `~usuario` | `path-utils.ts:119-124`; también en roots `roots-utils.ts:16-18` |
| Bytes nulos | **Sí**, rechazo explícito en ruta y en allowlist | `path-validation.ts:23-25`, `:47-49`; tests `:311`, `:320` |
| Separadores mixtos `/` y `\` | **Sí** en Windows | `path-utils.ts:96`, `:107`; test `:372` |
| Barra final | **Sí** | `path-utils.ts:58`; tests `:118`, `:144` |
| UNC `\\server\share\…` | **Sí**, con preservación del `\\` inicial | `path-utils.ts:66-78`, `:90-92`; test `:432-442` (bloquea `\\other\share\project`) |
| Unidades distintas | **Sí**, comparación de letra de unidad | `path-validation.ts:77-82`; test `:64` (`D:\other` contra allowlist `/` → `false`) |
| Rutas WSL `/mnt/c/…` | **Sí**, se preservan deliberadamente sin convertir | `path-utils.ts:11-15`, `:44-48` |
| Unicode y espacios | **Sí** (tests) | tests `:196`, `:207` |
| `%` en nombres | **Sí** (tests) | tests `:329`, `:342` |
| `...`, `....` como nombres válidos | **Sí** | test `:422-430` |
| Rutas muy largas | **Solo léxicamente**. Test de 1000 componentes; ningún manejo de `MAX_PATH`/260 ni del prefijo `\\?\` | test `:399-410` |
| **Mayúsculas/minúsculas en Windows** | **NO**, salvo la letra de unidad | `path-validation.ts:66,84` comparan case-sensitive; `path-utils.ts:98-100` solo capitaliza la unidad |
| **Nombres reservados Windows** (`CON`, `NUL`, `AUX`, `PRN`, `COM1-9`, `LPT1-9`, y variantes `CON.txt`) | **NO**. Cero apariciones en todo el directorio | `grep -rn "CON\b\|NUL\b\|AUX\|COM[1-9]\|LPT" *.ts` → 0 coincidencias funcionales |
| **Alternate Data Streams** `fichero.txt:oculto` | **NO** verificado ni mencionado en el código | — |
| **Puntos/espacios finales** en Windows (`foo.` → `foo`) | **NO** manejado explícitamente | — |
| **Nombres cortos 8.3** (`PROGRA~1`) | **Parcial e implícito**: `realpath` los resuelve en ficheros existentes; para el componente final inexistente (camino ENOENT, `lib.ts:133`) no se canoniza | — |
| Prefijo `\\?\` / espacio de dispositivos `\\.\` | **NO** manejado explícitamente; cae en la rama UNC de `path-utils.ts:66-78` con efecto **[no verificado]** | — |

Sobre la case-insensitivity: es un **falso negativo**, no un bypass. `C:\Users\Project\x.pdf` contra allowlist `C:\Users\project` da `false` y deniega una ruta legítima. No permite escapar, porque el `..` ya se colapsó antes. Aun así, para FileX en Windows es un fallo funcional serio y hay que arreglarlo (`os.path.normcase`).

### A.4 Mensajes de error: **sí es un oráculo, y además filtra rutas**

Cuatro mensajes distintos, todos en `validatePath`:

| # | Situación | Mensaje | Línea |
|---|---|---|---|
| 1 | Ruta fuera de la allowlist (léxico) | `Access denied - path outside allowed directories: ${absolute} not in ${allowedDirectories.join(', ')}` | `lib.ts:110` |
| 2 | Enlace cuyo destino real cae fuera | `Access denied - symlink target outside allowed directories: ${realPath} not in ${…}` | `lib.ts:119` |
| 3 | Padre real fuera de la allowlist | `Access denied - parent directory outside allowed directories: ${realParentPath} not in ${…}` | `lib.ts:131` |
| 4 | Padre inexistente | `Parent directory does not exist: ${parentDir}` | `lib.ts:135` |

Fijados como contrato en `__tests__/lib.test.ts:172` y `:205`.

**Veredicto: sí distingue "prohibido" de "no existe" — FileX no debe copiar esto tal cual.** Concretamente:

1. **Oráculo de existencia acotado.** El mensaje 4 es distinguible de los 1-3. Para una ruta que pasa el filtro léxico (es decir, *dentro* de la allowlist), el agente puede sondear la existencia del árbol de directorios: "padre no existe" vs. éxito. Es un oráculo **limitado al interior de la allowlist**, porque la comprobación léxica del paso 4 corta antes de tocar el disco para todo lo de fuera (`lib.ts:107-111`). Eso es una decisión de diseño acertada que **sí conviene copiar**: primero el predicado puro, después la E/S.
2. **Fuga de la allowlist completa** en los mensajes 1-3 (`allowedDirectories.join(', ')`). En este servidor no importa porque la allowlist ya se publica al modelo mediante la herramienta `list_allowed_directories` (`index.ts:702`, `index.ts:715`). En FileX, si la política de raíces es sensible (p. ej. contiene rutas de otros usuarios o de un tenant), **esto sí es una fuga**.
3. **Fuga de rutas de fuera del sandbox**: el mensaje 2 imprime `realPath`, que **por definición está fuera de la allowlist** (`lib.ts:119`). Y el 3 imprime `realParentPath`, ídem (`lib.ts:131`). El agente aprende dónde apunta el enlace. Esto es filtración de información sobre el sistema de ficheros del host, y es el peor de los cuatro.
4. **Amplificador de sondeo**: `read_multiple_files` no propaga la excepción, la **serializa por ruta** en el resultado (`index.ts:345`, `return \`${filePath}: Error - ${errorMessage}\``). Un solo `tools/call` con N rutas devuelve N respuestas del oráculo. Igual en `searchFilesWithValidation`, que silencia el error y sigue (`lib.ts:407-409`).

**Recomendación para FileX**: un único mensaje constante para los cuatro casos, del tipo `ruta no accesible`, sin interpolar la ruta pedida, sin la allowlist, y desde luego sin la ruta resuelta. El detalle va al log del servidor (stderr), no a la respuesta MCP. Y `read_multiple_files`-equivalentes deben devolver el mismo mensaje opaco por elemento.

### A.5 `roots-utils.ts` y el concepto de *roots* de MCP

**Qué es.** *Roots* es un mecanismo del propio protocolo MCP en el que **el cliente** (Claude Desktop, VS Code, …) declara al servidor qué directorios son su ámbito de trabajo. Es una capacidad del cliente, no del servidor: se anuncia en `capabilities.roots` durante el `initialize`.

**Cómo se negocia** — el flujo está en `index.ts:748-773` y descrito en `README.md:36-63`:

1. El servidor arranca, opcionalmente con directorios por argumentos (`index.ts:45-67`). Si no hay ninguno, arranca vacío y lo dice por stderr (`index.ts:777-779`).
2. En `server.server.oninitialized` (`index.ts:750`) consulta `getClientCapabilities()` (`index.ts:751`).
3. Si el cliente soporta roots (`index.ts:752`), el **servidor pide** la lista al cliente con `listRoots()` — petición **servidor→cliente**, dirección inversa a lo habitual (`index.ts:754`).
4. `getValidRootDirectories` (`roots-utils.ts:52-77`) valida cada root: acepta `file://…` (vía `fileURLToPath`) o ruta llana (`roots-utils.ts:15`), expande `~` (`:16-18`), `path.resolve` (`:19`), **`fs.realpath`** (`:20`, con el comentario `Includes symlink resolution for security` en `:47`), `normalizePath` (`:21`), y descarta lo que no exista o no sea directorio (`:65-70`). Los descartes van a stderr, **no** al cliente (`:60`, `:69`, `:72`).
5. **Los roots del cliente REEMPLAZAN por completo la allowlist previa**, no se suman (`index.ts:181` `allowedDirectories = [...validatedRootDirs]`; `README.md:29` *«completely replace any server-side Allowed directories»*). Si el cliente devuelve 0 roots válidos, se conserva la anterior (`index.ts:184-186`).
6. **Actualización en caliente**: el servidor registra un handler de `notifications/roots/list_changed` (`index.ts:736`) que vuelve a pedir la lista y re-reemplaza la allowlist (`index.ts:738-742`). Sin reiniciar el servidor.
7. Si el cliente **no** soporta roots y no había argumentos → el servidor **falla al inicializar** con un mensaje que explica las dos alternativas (`index.ts:767`). Fail-closed.

**Relevancia para FileX**: es exactamente el problema que `PLAN-ORQUESTADOR.md:266-271` describe como "hay que inventar". No hay que inventarlo: es protocolo. FileX debería (a) declarar que la allowlist se puede alimentar por roots, (b) reemplazar y no acumular, (c) fallar al inicializar si no hay ninguna raíz. La versión Python del SDK MCP expone `session.list_roots()` y la notificación equivalente **[no verificado — no he inspeccionado el SDK Python en este repo]**.

Matiz de confianza que FileX debe evaluar: los roots vienen **del cliente**, es decir del entorno donde vive el LLM. Si el modelo de amenaza de FileX incluye un cliente comprometido o un prompt injection que manipule la configuración del cliente, aceptar roots arbitrarios amplía la superficie. El servidor de referencia lo acepta sin restricción. Un diseño más conservador para FileX: **intersecar** los roots del cliente con una allowlist de servidor inmutable, en vez de reemplazarla.

### A.6 Portabilidad a Python

#### Lógica pura (portable 1:1, sin dependencias de Node)

`path-validation.ts:11-86` **entero** es lógica pura: comprobaciones de tipo, bytes nulos, normalización sintáctica y comparación de prefijos. Ninguna llamada a `fs`. Es lo que hay que traducir literalmente, incluida la disciplina de fail-closed y el `+ sep` de la línea 84.

Traducción concreta:

| Node | Python | Trampa |
|---|---|---|
| `path.normalize(p)` | `os.path.normpath(p)` | Equivalente léxico. En POSIX `normpath` **conserva** un `//` inicial (POSIX lo permite); `path.normalize` de Node también. Sin diferencia práctica. |
| `path.resolve(p)` | `os.path.abspath(p)` | **NO usar `Path.resolve()` ni `Path(p).absolute()`**. `Path.resolve()` resuelve enlaces simbólicos, y aquí hace falta la forma **léxica sin resolver** para la primera capa. `os.path.abspath` = `normpath(join(getcwd(), p))`, que es lo que hace `path.resolve`. |
| `path.isAbsolute(p)` | `os.path.isabs(p)` | En Windows `os.path.isabs('\\foo')` devuelve `True` aunque sea relativa a la unidad. Hay que reforzarlo: en Windows exigir letra de unidad o prefijo UNC. Node tiene el mismo defecto pero la capa 1 lo cubre porque ya se hizo `resolve`. |
| `path.sep` | `os.sep` | — |
| `normalizedPath.startsWith(dir + sep)` | `PurePath(p).is_relative_to(PurePath(d))` (3.9+) **o** `os.path.commonpath([p, d]) == d` | `is_relative_to` es puramente léxico → correcto aquí. `commonpath` lanza `ValueError` si las rutas están en unidades distintas: capturarlo y devolver `False`. Ojo: `str.startswith` sin el `+ sep` reintroduce la vulnerabilidad de prefijo. |
| capitalizar unidad (`path-utils.ts:98-100`) | `os.path.normcase(p)` | **Mejora sobre la referencia**: `normcase` en Windows pasa todo a minúsculas y `/`→`\`, cerrando de paso el hueco de mayúsculas/minúsculas de §A.3. En POSIX es la identidad, así que se puede aplicar siempre. |
| `p.includes('\x00')` | `'\x00' in p` | Python además lanza `ValueError: embedded null byte` en las llamadas de `os`, pero la comprobación léxica debe ir antes igualmente. |

#### Dependiente de APIs de Node (hay que reescribir, no traducir)

| Node | Python | Nota |
|---|---|---|
| `fs.realpath(p)` (`lib.ts:116`, `:128`, `index.ts:53`, `roots-utils.ts:20`) | `os.path.realpath(p, strict=True)` (3.10+) o `Path(p).resolve(strict=True)` | **Usar `strict=True`**: con `strict=False` (por defecto en `os.path.realpath`) no hay `FileNotFoundError` y se pierde la rama ENOENT de `lib.ts:122-137`, que es donde vive la validación del directorio padre. |
| `os.homedir()` (`path-utils.ts:121`) | `Path.home()` / `os.path.expanduser('~')` | `expanduser` de Python **también** expande `~usuario`, cosa que la referencia no hace. Decidir si se quiere; lo conservador es no permitirlo. |
| `fs.writeFile(…, {flag:'wx'})` (`lib.ts:165`) | `os.open(p, os.O_WRONLY \| os.O_CREAT \| os.O_EXCL)` | Equivalente exacto. |
| `fs.rename` atómico (`lib.ts:174`, `:272`) | `os.replace(src, dst)` | `os.replace` es atómico y sobrescribe en ambas plataformas (`os.rename` falla si existe en Windows). |
| `fileURLToPath` (`roots-utils.ts:6,15`) | `urllib.request.url2pathname` + `urlparse`, o `Path(urlparse(u).path)` con des-escapado | Cuidado con `file:///C:/…` en Windows: hay que quitar la barra inicial. |
| `fs.stat` / `isDirectory` (`index.ts:73-74`, `roots-utils.ts:65-66`) | `os.stat` / `stat.S_ISDIR` | — |
| `path-utils.ts` completo (`convertToWindowsPath`, WSL, `/c/`) | **descartar salvo que haga falta** | Son parches para que `fs` de Node funcione dentro de WSL (`path-utils.ts:11-15`). FileX solo lo necesita si acepta rutas en forma `/c/…` o `/mnt/c/…` como entrada del LLM. Si no, es complejidad sin beneficio y superficie de bugs. |

#### Donde Python puede hacerlo **mejor** que la referencia

Node no tiene forma de abrir un fichero sin seguir enlaces ni de operar relativo a un descriptor de directorio; por eso la referencia se queda con el TOCTOU documentado en §A.2. Python sí:

- `os.open(p, os.O_RDONLY | os.O_NOFOLLOW)` (POSIX) — falla con `ELOOP` si el componente final es un enlace. Cierra el caso del test `__tests__/path-validation.test.ts:932`.
- `os.open(name, flags, dir_fd=fd_del_directorio)` — resolución relativa a un fd ya validado, inmune a que el padre se convierta en enlace después. Cierra el caso de `:784`.
- Validar y **quedarse con el descriptor abierto** durante toda la conversión, en vez de re-abrir por ruta. Es el patrón correcto para FileX porque las conversiones son largas.
- `os.stat(fd)` sobre el fd ya abierto para comprobar `st_dev`/`st_ino` contra lo validado.

En Windows no hay `O_NOFOLLOW`; el equivalente es abrir con `FILE_FLAG_OPEN_REPARSE_POINT` vía `ctypes`, o aceptar el riesgo y compensar con permisos del directorio de trabajo. **[no verificado — fuera del alcance de este repo]**

---

## B) `servers/src/everything` — inventario de capacidades del protocolo

Servidor de demostración que ejercita todo el protocolo (`README.md:11`: *«not intended to be a useful server, but rather a test server for builders of MCP clients»*). Inventario completo en `docs/features.md`.

### B.1 Capacidades declaradas por el servidor

`server/index.ts:53-74`:

```
tools:     { listChanged: true }        // server/index.ts:54-56
prompts:   { listChanged: true }        // server/index.ts:57-59
resources: { subscribe: true,
             listChanged: true }        // server/index.ts:60-63
logging:   {}                           // server/index.ts:64
tasks:     { list, cancel,
             requests: { tools.call } } // server/index.ts:65-73
```

Más `instructions` (`server/index.ts:37`, `:75`) — texto de instrucciones a nivel de servidor que el cliente entrega al modelo.

### B.2 Capacidades que se consumen **del cliente**

- **roots** — `server/roots.ts:31-89`. Solo se sincroniza si `clientCapabilities?.roots !== undefined` (`server/roots.ts:32-33`); cachea por `sessionId` (`server/roots.ts:8-11`, `:44`) y registra el handler de `list_changed` (`server/roots.ts:78-81`).
- **sampling** — el servidor pide al **cliente** que ejecute una inferencia LLM: `tools/trigger-sampling-request.ts` (`docs/features.md:27`).
- **elicitation** — el servidor pide **datos al usuario** a mitad de una llamada: `tools/trigger-elicitation-request.ts`, modo formulario con strings/números/booleanos/enums y validación de formato (`docs/features.md:25`; esquema en `tools/trigger-elicitation-request.ts:56`; el resultado trae `action` ∈ `accept`/`decline`/`cancel`, `tools/trigger-elicitation-request.ts:184`, `:213`, `:218`).
- **elicitation en modo URL** — `mode:"url"`, para mandar al usuario a completar algo en el navegador; incluye el error MCP `-32042` `UrlElicitationRequiredError` (`docs/features.md:26`).
- **tasks bidireccionales** — el cliente ejecuta como tarea de fondo peticiones del servidor (`docs/features.md:87-98`).

### B.3 Otros mecanismos ejercitados

- **Progress notifications**: `notifications/progress` con `progressToken` del `_meta` de la petición (`tools/trigger-long-running-operation.ts:50`, `:57-64`).
- **Resource subscriptions**: `resources/subscribe` / `unsubscribe` + `notifications/resources/updated` por sesión (`docs/features.md:46-51`).
- **Logging estructurado**: 8 niveles, con `logging/setLevel` controlado por el cliente (`docs/features.md:53-57`); envío vía `server.sendLoggingMessage` (`server/roots.ts:47-54`).
- **Completions**: autocompletado de argumentos de prompt con el helper `completable` del SDK (`prompts/completions.ts`; `docs/features.md:36`). Nótese que **no** aparece en el bloque `capabilities` de `server/index.ts:53-74` — el SDK la añade sola al registrar un prompt completable. **[no verificado en el SDK]**
- **Resource templates**: URIs parametrizadas `demo://resource/dynamic/text/{index}` (`docs/features.md:41-42`).
- **Recursos de sesión**: registro dinámico con `demo://resource/session/<name>`, vivos solo mientras dure la sesión (`resources/session.ts:17-19`, `:32-80`; re-registro seguro borrando el anterior, `resources/session.ts:57-62`).
- **`resource_link` como tipo de contenido de resultado**: `{type:"resource_link", ...}` (`resources/session.ts:79`; `tools/get-resource-links.ts:43`).
- **`structuredContent` + `outputSchema`**: resultado tipado con compatibilidad hacia atrás (`docs/features.md:19`).
- **Annotations de herramienta**: `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint` (`tools/gzip-file-as-resource.ts:50-55`).
- **Annotations de contenido**: `priority` y `audience` por bloque (`docs/features.md:13`).
- **Registro condicional de herramientas** según las capacidades del cliente, tras `oninitialized` (`server/index.ts:94-97`).
- **Tres transportes**: stdio, SSE (deprecado) y Streamable HTTP (`index.ts:11-24`).

### B.4 Lo que FileX se está perdiendo

FileX solo contempla **tools**. Ordenado por utilidad real para un conversor:

| Capacidad | Utilidad concreta en un conversor | Prioridad |
|---|---|---|
| **`resource_link` como salida** | Es **la respuesta correcta** para un conversor. En vez de devolver 40 MB en base64 dentro del `CallToolResult` (o una ruta que el cliente quizá no puede leer), se devuelve un enlace a un recurso que el cliente lee cuando quiera y como quiera. Patrón exacto en `tools/gzip-file-as-resource.ts:100-121`: convierte → registra recurso de sesión → devuelve `resourceLink` o `resource` según el parámetro `outputType` (`tools/gzip-file-as-resource.ts:35-40`). Es literalmente el caso de uso de FileX con gzip en vez de una conversión. | **Alta** |
| **Recursos de sesión** | Sostén del punto anterior: la salida convertida vive mientras dura la sesión, sin ensuciar el disco del usuario ni exigir que el LLM elija una ruta de escritura (que es de donde viene la mitad del riesgo de §D). `resources/session.ts:32-80`. | **Alta** |
| **Progress notifications** | Una conversión PDF→Markdown con OCR tarda minutos. Sin progreso, el cliente no distingue "trabajando" de "colgado" y el usuario cancela. `tools/trigger-long-running-operation.ts:50-64`. | **Alta** |
| **Roots** | Alimentar la allowlist desde el cliente (§A.5). Elimina la configuración manual de rutas y es el mecanismo previsto por el protocolo. `server/roots.ts:31-89`, `filesystem/index.ts:748-773`. | **Alta** |
| **Elicitation** | Preguntar al **usuario**, no al modelo, cuando la conversión es ambigua o destructiva: "el PDF está protegido, ¿contraseña?", "el destino ya existe, ¿sobrescribo?", "esto va a tardar 8 min y usar la GPU, ¿sigo?". Es el punto de consentimiento humano que a un conversor con escritura le falta. `tools/trigger-elicitation-request.ts`, resultado `accept`/`decline`/`cancel` (`:184`, `:213`, `:218`). | **Alta** |
| **Tasks (SEP-1686)** | Conversiones largas como tarea con `taskId`, polling de estado, cancelación (`tasks.cancel`). Alternativa estructurada al progreso para trabajos de minutos. `docs/features.md:59-105`, capacidad en `server/index.ts:65-73`. Es reciente; verificar soporte en el SDK Python antes de comprometerse. **[no verificado]** | Media |
| **Logging** | Enviar diagnóstico de la conversión (qué motor eligió el orquestador, por qué cayó a un fallback) al cliente con nivel controlable por él, en vez de a stderr. `docs/features.md:53-57`. Encaja con la idea de orquestador multi-motor de `PLAN-ORQUESTADOR.md`. | Media |
| **`structuredContent` + `outputSchema`** | Devolver `{formato_origen, formato_destino, motor, paginas, tiempo, avisos[]}` tipado en vez de prosa que el modelo tiene que parsear. `docs/features.md:19`. | Media |
| **Annotations de herramienta** | `destructiveHint:true` en las herramientas que escriben, `readOnlyHint:true` en las que inspeccionan. Los clientes las usan para decidir cuándo pedir confirmación. Ver el uso sistemático en `filesystem/index.ts:370`, `:400`, `:425`, `:629`. Coste: cero. | Media (fruta baja) |
| **Resources + templates** | Exponer el catálogo de formatos soportados y la matriz de conversión como recurso legible, en vez de meterlo en la descripción de la herramienta. `docs/features.md:41-44`. | Baja |
| **Prompts** | Flujos guiados ("convierte esta carpeta a Markdown para RAG"). Poco valor frente a lo anterior. `docs/features.md:32-37`. | Baja |
| **Completions** | Autocompletar el formato destino en clientes que lo soporten. `prompts/completions.ts`. | Baja |
| **Sampling** | El servidor pediría al cliente una inferencia. Para un conversor, difícil de justificar salvo para post-procesar (p. ej. describir imágenes). Riesgo de coste no acotado. `docs/features.md:27`. | Baja / evitar |
| **Resource subscriptions** | "Avísame cuando cambie este fichero y reconviértelo". Interesante pero fuera de alcance. `docs/features.md:46-51`. | Baja |

---

## C) `servers/src/fetch` — recursos remotos

Un solo fichero relevante: `fetch/src/mcp_server_fetch/server.py`, 288 líneas, **en Python** (útil como referencia directa para FileX). Expone una herramienta `fetch` (`server.py:200-206`) y un prompt `fetch` (`server.py:212-220`).

### C.1 Qué hace

| Control | ¿Lo hace? | Evidencia |
|---|---|---|
| **`robots.txt`** | **Sí**, y es su rasgo distintivo. Antes de cada fetch autónomo llama a `check_may_autonomously_fetch_url` (`server.py:234-235`), que descarga `<esquema>://<host>/robots.txt` (`server.py:48-63`, `:77-81`), lo parsea con **Protego** (`server.py:98`) y niega si `can_fetch` es falso (`server.py:99-108`). Un 401/403 al pedir robots.txt se interpreta como "prohibido" (`server.py:87-91`); un 4xx cualquiera se interpreta como "permitido" (`server.py:92-93`). Se puede desactivar con `--ignore-robots-txt` (`server.py:183`, `:234`). | |
| **User-Agent diferenciado** | **Sí**, y es un detalle de diseño notable: UA distinto para fetch autónomo del agente (`ModelContextProtocol/1.0 (Autonomous; …)`, `server.py:23`) y para fetch iniciado por el usuario vía prompt (`(User-Specified; …)`, `server.py:24`). La ruta del prompt **no** comprueba robots.txt (`server.py:265` llama a `fetch_url` directamente), porque hay un humano en el bucle. | |
| **Truncado del contenido devuelto** | **Sí**: `max_length` por defecto 5000, tope 1 000 000 (`server.py:155-163`), con `start_index` para paginar (`server.py:164-171`, aplicado en `server.py:244`). | |
| **Timeout** | **Parcial**: 30 s explícitos en el fetch principal (`server.py:125`). La petición de `robots.txt` **no lleva `timeout`** (`server.py:77-81`) y queda con el defecto de httpx. | |
| **Proxy configurable** | Sí (`server.py:119`, `:184`). | |
| **Validación del destino / bloqueo de rangos privados** | **NO** | |
| **Límite de tamaño de descarga** | **NO** | |
| **Restricción de esquema** | **NO** más allá de lo que acepte `pydantic.AnyUrl` (`server.py:154`) | |
| **Re-validación tras redirección** | **NO**: `follow_redirects=True` sin comprobar el destino final (`server.py:123`) | |

### C.2 Lo que **no** hace: la referencia oficial es vulnerable a SSRF y lo admite

`fetch/README.md:12`:

> *This server can access local/internal IP addresses and may represent a security risk. Exercise caution when using this MCP server to ensure this does not expose any sensitive data.*

Es decir: **la referencia oficial no resuelve el SSRF, lo declara como riesgo asumido.** En detalle:

1. **Sin lista negra de rangos privados**: nada impide `http://127.0.0.1:8080/admin`, `http://[::1]/`, `http://169.254.169.254/latest/meta-data/` (metadatos de instancia cloud), `http://10.0.0.5/`, ni nombres internos. No hay ni una resolución DNS previa ni comprobación de la IP destino en todo `server.py`.
2. **Sin restricción de esquema**: `AnyUrl` (`server.py:154`) acepta cualquier esquema; el filtrado efectivo lo hace httpx al fallar. No hay una comprobación explícita `scheme in {"http","https"}` como sí existe en `everything/tools/gzip-file-as-resource.ts:139-147`.
3. **Redirecciones sin re-validar** (`server.py:123`, y también en robots.txt `server.py:79`): aunque se validara la URL inicial, un `302` hacia `169.254.169.254` la esquivaría. Éste es el fallo que hace inútil cualquier validación hecha solo sobre la URL de entrada.
4. **Sin límite de bytes**: `response.text` (`server.py:135`) materializa el cuerpo **completo** en memoria. `max_length` (`server.py:244`) trunca **después**. Un endpoint que sirva 5 GB tumba el proceso. La única barrera es el timeout de 30 s.
5. **El robots.txt es en sí mismo un vector**: `check_may_autonomously_fetch_url` hace una petición HTTP a `host/robots.txt` (`server.py:77-81`) **antes** de cualquier otra comprobación, sin timeout explícito y siguiendo redirecciones. La "defensa" es el primer disparo del SSRF.

**Conclusión para FileX**: `fetch` **no** es la referencia a copiar para recursos remotos. Lo único aprovechable es (a) el patrón de UA autónomo/manual y (b) el uso de Protego para robots.txt, si FileX llegara a descargar por su cuenta.

### C.3 La referencia buena está en `everything`, no en `fetch`

`everything/tools/gzip-file-as-resource.ts` **sí** implementa los controles que a `fetch` le faltan, y es de hecho el análogo más cercano a FileX (recibe una URL, procesa el fichero, devuelve un recurso):

- **Allowlist de esquemas** explícita: solo `http:`, `https:`, `data:` (`gzip-file-as-resource.ts:139-147`).
- **Allowlist de dominios** por variable de entorno `GZIP_ALLOWED_DOMAINS`, con coincidencia exacta o de sufijo `.dominio` (`gzip-file-as-resource.ts:21-24`, `:148-159`). Vacía = todo permitido (elección de demo, no de producción).
- **Límite de tamaño real, no solo de cabecera** (`gzip-file-as-resource.ts:180-244`). El comentario de `:200-201` es el punto pedagógico:
  > *we can't trust the Content-Length header: a malicious or clumsy server could return much more data than advertised. We check it here for early bail-out, but we still need to monitor actual bytes read below.*
  Comprueba `content-length` para abortar pronto (`:202-210`) **y además** cuenta bytes leídos chunk a chunk, cancelando el reader al pasarse (`:219-231`). 10 MB por defecto (`:11-13`).
- **Timeout con `AbortController`** y `clearTimeout` en `finally` (`gzip-file-as-resource.ts:184-191`, `:245-247`), 30 s por defecto (`:16-18`).
- **Todo configurable por entorno**, no hardcodeado (`:11-24`).

Lo que **tampoco** cubre: bloqueo de IPs privadas ni re-validación tras redirección (`fetch(url, {signal})` en `:195` sigue redirecciones por defecto). Si FileX acepta URLs, eso sigue siendo trabajo propio: resolver el DNS, comprobar la IP contra los rangos privados/link-local/loopback/CGNAT, y **repetir la comprobación en cada salto de redirección** (o desactivar las redirecciones y seguirlas a mano).

---

## D) Lo que FileX debe hacer distinto

`filesystem` protege la **lectura y escritura de ficheros por un agente**. FileX hace tres cosas más que la referencia no contempla en absoluto: **elige rutas de salida**, **lanza procesos externos** sobre esas rutas, y **procesa contenido no confiable**. Lo que sigue es lo que no está cubierto.

### D.1 Escritura de salidas

- **Una sola allowlist para leer y escribir.** `validatePath` no distingue operación: la misma lista sirve para `read_text_file` y para `write_file` (`lib.ts:99` se llama igual desde `index.ts:192` y desde el handler de escritura). Para un conversor eso es demasiado permisivo: el modelo puede pedir escribir el resultado **encima** de cualquier fichero legible. FileX necesita **raíz de lectura ≠ raíz de escritura**, con la de escritura por defecto en un staging propio del servidor.
- **Sobrescritura silenciosa.** `writeFileContent` sobrescribe sin avisar mediante `rename` atómico (`lib.ts:167-180`). Un conversor que escriba `informe.pdf` sobre un `informe.pdf` existente destruye datos del usuario sin recurso. FileX: **no-clobber por defecto**, sufijo automático o `elicitation` (§B.4) para pedir confirmación.
- **Nombre de salida elegido por el modelo.** La referencia no sanea el `basename`: no hay filtro de nombres reservados de Windows (§A.3), ni de puntos/espacios finales, ni de ADS, ni de extensiones peligrosas (`.lnk`, `.url`, `.desktop`, `.scf`), ni control de que la extensión resultante case con el formato realmente producido.
- **Temporales dentro del espacio del usuario.** Tanto `writeFileContent` (`lib.ts:171`) como `applyFileEdits` (`lib.ts:269`) crean `${filePath}.${hex}.tmp` **junto al fichero destino**, es decir dentro de la raíz permitida. Si el proceso muere, queda basura en el directorio del usuario. FileX, que produce ficheros grandes y usa procesos externos que pueden morir, debe usar un directorio de staging propio con limpieza garantizada, y mover al destino solo al final.

### D.2 Procesos externos — **cero cobertura en la referencia**

`filesystem` no ejecuta nada. Todo esto es trabajo propio de FileX:

- **Option injection.** LibreOffice, ffmpeg, ghostscript, pandoc y qpdf interpretan argumentos que empiezan por `-`/`--`. Un fichero llamado `--outdir=/etc` pasa el filtro de `validatePath` sin problema (es un nombre de fichero válido dentro de la raíz permitida) y luego es una opción para el binario. Mitigación: separador `--` cuando el binario lo soporte, o rutas siempre absolutas y nunca relativas, o mejor: **renombrar a un nombre opaco en el staging** antes de invocar.
- **Nunca `shell=True`.** `subprocess` con lista de argumentos, sin `shell`, `env` mínimo y controlado, `cwd` fijado al staging.
- **Argumentos que el modelo controla parcialmente** (calidad, DPI, rango de páginas, filtros de ffmpeg): validar contra enumeraciones y rangos numéricos cerrados, nunca pasar cadenas libres. Los filtergraphs de ffmpeg y las opciones `-sDEVICE`/`-dSAFER` de ghostscript son lenguajes completos.
- **Límites de recursos del hijo**: tiempo de pared, CPU, RSS, tamaño de fichero producido (`RLIMIT_FSIZE`), número de procesos. Sin esto, una conversión maliciosa es un DoS trivial.
- **Aislamiento del hijo**: LibreOffice y ghostscript han tenido RCE. La validación de rutas de `filesystem` no protege de que el propio conversor sea el vector. Contenedor, usuario sin privilegios, sin red, o al menos perfil restringido. El proyecto ya tiene `docker/` — es el sitio.
- **Herencia de descriptores y de entorno**: el hijo no debe heredar el stdio del transporte MCP ni variables sensibles.

### D.3 Contenido, no rutas

`filesystem` **no mira el contenido en ningún momento**. Peor: `read_media_file` decide el `mimeType` **por la extensión** (`index.ts:281-295`, tabla en `:282-294` y `mimeTypes[extension] || "application/octet-stream"` en `:295`). Para un servidor de lectura es aceptable; **para un conversor sería un fallo de diseño**, porque determina qué motor se invoca sobre el fichero. FileX necesita:

- **Sniffing del tipo real** (magic bytes / libmagic) y comparación con la extensión declarada; discrepancia = rechazo o al menos aviso.
- **Zip bombs y descompresión anidada**: ratio de compresión, tamaño descomprimido acumulado, profundidad. Aplica a `.docx`/`.xlsx`/`.pptx`/`.odt`/`.epub`, que son ZIP.
- **Zip slip**: entradas con `../` en el nombre dentro del contenedor OOXML/ODF. Nótese que la validación de `path-validation.ts` es reutilizable aquí — el mismo predicado, aplicado a las entradas del ZIP contra el directorio de extracción.
- **XXE y entidades externas** en SVG, ODF, OOXML, XML.
- **PDF con JavaScript, acciones de lanzamiento, o recursos remotos**; **macros de Office**; **fuentes embebidas maliciosas**.
- **Límite de tamaño de entrada y de salida.** La referencia no tiene ninguno: `readFileContent` lee el fichero entero en memoria (`lib.ts:157-159`) y `searchFilesWithValidation` recursa sin límite de profundidad ni de número de resultados (`lib.ts:374-415`).

### D.4 TOCTOU: FileX lo tiene **peor** que la referencia

En `filesystem` la ventana entre `validatePath` y la operación son microsegundos. En FileX, entre validar la ruta y que ffmpeg termine de leerla pueden pasar **minutos**, y la lectura la hace **otro proceso** que no sabe nada de la allowlist. La mitigación de la referencia (`'wx'` + `rename`, `lib.ts:161-185`) no se puede aplicar a un binario externo que abre la ruta por su cuenta.

Estrategia recomendada: **copiar la entrada al staging privado tras validarla** y pasar al proceso externo la ruta del staging, nunca la del usuario. Así el binario externo nunca ve una ruta que el agente controle, y la ventana de TOCTOU se reduce a la copia. Adicionalmente, mantener el fd abierto durante la copia (`O_NOFOLLOW`, §A.6) y comprobar `st_dev`/`st_ino`.

### D.5 Modelo de confianza de los roots

`filesystem` acepta los roots del cliente **reemplazando** la allowlist del servidor sin más (`index.ts:181`, `README.md:29`). Si FileX escribe ficheros y lanza procesos, conviene ser más conservador: **intersecar** los roots del cliente con una allowlist de servidor inmutable, en vez de sustituirla.

### D.6 Errores opacos

Ver §A.4. FileX no debe copiar los mensajes de `lib.ts:110,119,131,135`.

---

## E) Tabla de veredictos

| Componente | Fichero:línea | Veredicto | Nota |
|---|---|---|---|
| `isPathWithinAllowedDirectories` — predicado de contención | `path-validation.ts:11-86` | **adaptar a Python** | Lógica pura. Traducción casi 1:1. Conservar orden y fail-closed. Sustituir `startsWith(dir+sep)` por `is_relative_to` y añadir `os.path.normcase`. |
| Disciplina "léxico antes que E/S" | `lib.ts:107-111` | **copiar tal cual** | Decisión de diseño, no código. Evita que el disco filtre información sobre rutas prohibidas. |
| Doble validación: ruta pedida + ruta real | `lib.ts:108` y `lib.ts:118` | **copiar tal cual** | El patrón, no el código. |
| Devolver siempre la ruta canónica al llamante | `lib.ts:121` | **copiar tal cual** | Que ninguna capa posterior vuelva a ver la ruta del modelo. |
| Rama ENOENT → validar el padre real | `lib.ts:122-137` | **adaptar a Python** | `os.path.realpath(p, strict=True)` + `FileNotFoundError`. Imprescindible para ficheros de salida. |
| Guardar original **y** resuelta en la allowlist | `index.ts:41-67` | **adaptar a Python** | Necesario en macOS (`/tmp`→`/private/tmp`) y con cualquier raíz enlazada. |
| Filtrado de raíces inaccesibles + abortar si ninguna | `index.ts:70-88` | **adaptar a Python** | Fail-closed al arrancar. |
| `expandHome` (`~`) | `path-utils.ts:119-124` | **adaptar a Python** | `Path.home()`. Decidir si permitir `~usuario` (la referencia no lo permite; recomendado no permitirlo). |
| Rechazo de bytes nulos | `path-validation.ts:23-25,47-49` | **copiar tal cual** | Trivial y necesario. |
| `+ path.sep` contra la vulnerabilidad de prefijo | `path-validation.ts:84` | **copiar tal cual** | El bug clásico que evita. Test en `__tests__/path-validation.test.ts:63`. |
| Manejo de raíz de unidad Windows | `path-validation.ts:77-82` | **adaptar a Python** | Único punto case-insensitive. En Python, generalizar con `normcase`. |
| Resolución de rutas relativas contra cada raíz | `lib.ts:76-96` | **solo como referencia** | Comportamiento discutible: elige "la primera raíz que encaje", lo que es ambiguo con varias raíces. FileX: **exigir rutas absolutas** y rechazar las relativas. |
| `normalizePath` (WSL, `/c/`, UNC, comillas) | `path-utils.ts:39-112` | **solo como referencia** | Casi todo son parches para `fs` de Node en WSL. Portar solo el manejo UNC y el de la letra de unidad si FileX soporta Windows. |
| `convertToWindowsPath` | `path-utils.ts:9-32` | **no aplica a FileX** | Salvo que FileX acepte `/c/…` o `/mnt/c/…` del LLM. |
| Mensajes de error detallados | `lib.ts:110,119,131,135` | **no aplica a FileX** | Oráculo de existencia + fuga de la allowlist y de rutas de fuera del sandbox. Sustituir por un mensaje opaco único. |
| `list_allowed_directories` | `index.ts:702-717` | **solo como referencia** | Decisión de política: publicar las raíces al modelo es cómodo, pero es divulgación. |
| Escritura `'wx'` + `rename` atómico | `lib.ts:161-185` | **adaptar a Python** | `os.open(O_EXCL)` + `os.replace`. Cambiar el temporal a un staging privado, no junto al destino. |
| `applyFileEdits` (edición por texto + diff) | `lib.ts:194-282` | **no aplica a FileX** | Un conversor no edita ficheros por coincidencia de texto. |
| `tailFile` / `headFile` | `lib.ts:285-372` | **no aplica a FileX** | |
| `searchFilesWithValidation` | `lib.ts:374-415` | **solo como referencia** | El patrón "validar cada entrada durante el recorrido" (`lib.ts:390`) es bueno; falta límite de profundidad y de resultados. |
| `getFileStats` | `lib.ts:144-155` | **adaptar a Python** | Trivial (`os.stat`). Útil para el chequeo de tamaño previo a convertir. |
| `read_media_file` (MIME por extensión) | `index.ts:280-295` | **no aplica a FileX** | Antipatrón para un conversor: el tipo debe venir del contenido. |
| Anotaciones de herramienta (`destructiveHint`…) | `index.ts:370,400,425,629` | **copiar tal cual** | Coste cero, valor inmediato para los clientes. |
| `roots-utils.ts` — validación de roots MCP | `roots-utils.ts:13-77` | **adaptar a Python** | Con un cambio de política: **intersecar** con la allowlist del servidor en vez de reemplazarla. |
| Negociación de roots (init + `list_changed`) | `index.ts:723-773` | **adaptar a Python** | Es protocolo, no invención. Incluye el fail-closed de `index.ts:767`. |
| Tests de TOCTOU como documentación de huecos | `__tests__/path-validation.test.ts:679,784,932` | **copiar tal cual** | Copiar los **casos**, no el código: son el catálogo de lo que FileX debe cerrar con `O_NOFOLLOW`/`dir_fd`. |
| `everything` — patrón `resource_link` + recurso de sesión | `everything/tools/gzip-file-as-resource.ts:94-121`, `everything/resources/session.ts:32-80` | **adaptar a Python** | El molde exacto para devolver el fichero convertido. |
| `everything` — `fetchSafely` (límite de bytes real + timeout) | `everything/tools/gzip-file-as-resource.ts:180-248` | **adaptar a Python** | Si FileX acepta URLs. Añadir bloqueo de IPs privadas y re-validación de redirecciones, que le faltan. |
| `everything` — `validateDataURI` (allowlist de esquema y dominio) | `everything/tools/gzip-file-as-resource.ts:135-168` | **adaptar a Python** | Idem. |
| `everything` — progress notifications | `everything/tools/trigger-long-running-operation.ts:50-64` | **adaptar a Python** | Conversiones de minutos sin progreso = cancelaciones. |
| `everything` — elicitation | `everything/tools/trigger-elicitation-request.ts` | **adaptar a Python** | Contraseña de PDF, confirmación de sobrescritura, coste de GPU. |
| `everything` — tasks (SEP-1686) | `everything/docs/features.md:59-105` | **solo como referencia** | Verificar soporte en el SDK Python antes de comprometerse. **[no verificado]** |
| `everything` — sampling | `everything/docs/features.md:27` | **no aplica a FileX** | Coste no acotado, sin caso de uso claro. |
| `fetch` — robots.txt con Protego + UA autónomo/manual | `fetch/…/server.py:23-24,66-108` | **solo como referencia** | Buen patrón de "hay humano en el bucle → distinta política". |
| `fetch` — todo lo demás | `fetch/…/server.py` | **no aplica a FileX** | SSRF sin mitigar, admitido en `fetch/README.md:12`. Sin límite de tamaño, sin re-validación de redirecciones, sin filtro de esquema. **No copiar.** |

---

## F) Resumen ejecutivo

1. **La allowlist de raíces no hay que inventarla.** `path-validation.ts` (86 líneas) + `validatePath` (`lib.ts:99-140`) son MIT, están probados con ~1000 líneas de tests y resuelven traversal, prefijos comunes, bytes nulos, enlaces simbólicos anidados, ficheros inexistentes vía directorio padre y unidades Windows. Es un fin de semana de porte a Python, no un diseño desde cero.
2. **Lo que la referencia sí deja abierto, y sus propios tests lo demuestran**: TOCTOU en lectura (`__tests__/path-validation.test.ts:932`) y en padres enlazados (`:784`). Python puede cerrarlo mejor que Node con `O_NOFOLLOW` y `dir_fd`.
3. **Tres huecos de Windows** que la referencia no cubre y FileX sí necesita: comparación case-insensitive, nombres de dispositivo reservados (`CON`, `NUL`, `AUX`…) y saneado del `basename` de salida.
4. **Los mensajes de error de la referencia no se pueden copiar**: distinguen "prohibido" de "no existe" (`lib.ts:131` vs `lib.ts:135`), publican la allowlist completa y filtran rutas resueltas de fuera del sandbox (`lib.ts:119`). `read_multiple_files` (`index.ts:345`) convierte el oráculo en una consulta por lotes.
5. **MCP Roots es protocolo, no invención** (`index.ts:723-773`, `roots-utils.ts:13-77`). FileX debería usarlo, pero **intersecando** con una allowlist de servidor en vez de reemplazándola.
6. **FileX solo contempla tools y se pierde lo que más le conviene**: `resource_link` + recursos de sesión para devolver la salida (`everything/tools/gzip-file-as-resource.ts:94-121`), progress notifications para conversiones largas, y elicitation para el consentimiento humano en sobrescrituras y contraseñas.
7. **`fetch` es un antimodelo de seguridad** (SSRF admitido en su propio README). La referencia correcta para descarga con límites es `everything/tools/gzip-file-as-resource.ts:135-248`, y aun así hay que añadirle bloqueo de rangos privados y re-validación de redirecciones.
8. **Lo genuinamente nuevo de FileX** (y por tanto el trabajo real de seguridad) es lo que ningún servidor de referencia hace: **elegir rutas de escritura**, **lanzar procesos externos** sobre ellas y **procesar contenido hostil**. Ahí sí no hay de dónde copiar — pero es un problema distinto y más pequeño que "diseñar la lista blanca desde cero".

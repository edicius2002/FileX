# FileX — Entorno Docker de los conversores competidores

**Carril B (preparación).** Fecha: 2026-08-19. Estado: **entorno listo, los tres servicios arrancados y verificados**.

> **No se han ejecutado cargas de GPU ni mediciones de rendimiento.** El compose con CUDA
> (`docker/snapotter-gpu-compose.yml`) queda escrito y documentado pero **sin arrancar**.
> Las únicas latencias que aparecen en este documento son arranques en frío anotados
> como incidencia de configuración, no como medición comparable.

---

## 1. Resumen

| Servicio | Imagen | Puerto host | Estado | Credenciales |
|---|---|---|---|---|
| SnapOtter | `snapotter/snapotter:latest` | **1349** | Arrancado, `healthy` | `admin` / `admin` (obliga a cambiarla) |
| ConvertX | `ghcr.io/c4illin/convertx:latest` | **3100** | Arrancado, responde 200 | Sin login (`ALLOW_UNAUTHENTICATED=true`) |
| Gotenberg | `gotenberg/gotenberg:8` (8.36.0) | **3200** | Arrancado, `healthy` | Sin autenticación |
| SnapOtter GPU | `snapotter/snapotter:latest` | 1350 (reservado) | **NO arrancado, a propósito** | `admin` / `admin` |

Servicios de apoyo del stack de SnapOtter (sin puerto publicado al host):
`postgres:17-alpine` (5432 interno) y `redis:8-alpine` (6379 interno).

Ficheros producidos:

```
D:\Work\research\FileX\docker\
├── snapotter-compose.yml        # CPU  — arrancado
├── snapotter-gpu-compose.yml    # CUDA — preparado, NO arrancado
├── convertx-compose.yml         # arrancado
├── gotenberg-compose.yml        # arrancado
├── up-all.ps1                   # arranca los tres (solo CPU)
├── down-all.ps1                 # para / purga
└── verify-out\                  # PDFs de la prueba de humo de Gotenberg
    ├── chromium.pdf             # 13 645 B — HTML → PDF
    └── patologico_bom.pdf       # 15 839 B — CSV con BOM → PDF
```

---

## 2. Imágenes descargadas y tamaño real

Medido con `docker manifest inspect` (lo que cruza la red, comprimido) y con
`docker images` (lo que ocupa descomprimido en el disco de la VM de Docker).

| Imagen | Descarga (comprimida) | En disco | Capas | ID |
|---|---:|---:|---:|---|
| `snapotter/snapotter:latest` | 3,82 GB | **12,3 GB** | 71 | `2e11b4fa9138` |
| `ghcr.io/c4illin/convertx:latest` | 1,55 GB | **5,73 GB** | 11 | `b515b04bfd25` |
| `gotenberg/gotenberg:8` | 0,70 GB | **2,44 GB** | 18 | `87c16b9f3642` |
| `postgres:17-alpine` | (ya presente) | 399 MB | — | `979c4379dd69` |
| `redis:8-alpine` | 0,06 GB | 160 MB | — | `978f0e01593e` |
| **Total nuevo** | **≈ 6,1 GB** | **≈ 20,6 GB** | | |

Notas sobre el presupuesto de ~15 GB:

- Lo **descargado** son ~6,1 GB, holgadamente dentro del límite.
- Lo **ocupado en disco** es ~20,6 GB, por encima de esa cifra. La responsable es
  SnapOtter: 3,82 GB comprimidos se expanden a 12,3 GB (ratio 3,2×) porque la imagen
  unificada incluye las bibliotecas CUDA y los runtimes de IA. Se decidió traerla igualmente
  porque es **el competidor directo del proyecto** y sin ella el carril de evaluación no
  tiene objeto. ConvertX expande de forma parecida (1,55 → 5,73 GB) por su enorme conjunto
  de herramientas embebidas (ImageMagick, GraphicsMagick, LibreOffice 26.2, ffmpeg 8.1,
  Inkscape, calibre, pandoc, XeTeX, libvips, libheif…).
- Espacio libre tras la operación: **C: 101 GB, D: 97 GB**. Sin presión de disco.
  Ojo: la VM de Docker Desktop guarda las imágenes en `/var/lib/docker` dentro del disco
  virtual de WSL2, que por defecto vive en **C:**, no en D:.

### Variantes CPU / GPU de SnapOtter: sólo existe una imagen

Se comprobó explícitamente que **no hay una imagen GPU separada**:

```bash
docker manifest inspect snapotter/snapotter:cuda         # no existe
docker manifest inspect snapotter/snapotter:latest-cuda  # no existe
docker manifest inspect snapotter/snapotter:gpu          # no existe
```

Lo confirma su propia documentación (`repos/orchestrators/SnapOtter/apps/docs/guide/docker-tags.md`,
sección *Migration from previous tags*): el antiguo tag `:cuda` se fusionó en `:latest`.
La imagen `linux/amd64` lleva el soporte CUDA dentro y **autodetecta la GPU en tiempo de
ejecución**; la diferencia CPU/GPU es únicamente si se le pasa `--gpus all` (o la sección
`deploy.resources.reservations.devices` en Compose). Por tanto:

- "Descargar ambas variantes" se cumple con **una sola descarga**; no hay una segunda imagen que traer.
- Se verificó que el arranque actual va **en CPU**, como exigía la tarea. El log lo confirma:
  `[python] [gpu] torch not importable` → `[bridge] Python dispatcher ready (GPU: false)` →
  `[WARN] No GPU detected -- AI tools will use CPU (slower)`.

El manifiesto también publica `linux/arm64` (sólo CPU); se forzó `--platform linux/amd64`
en todas las descargas para no traer la arquitectura equivocada.

---

## 3. Puertos, volúmenes y credenciales

### Mapa de puertos

| Puerto host | Servicio | Puerto contenedor | Por qué |
|---|---|---|---|
| 1349 | SnapOtter (CPU) | 1349 | Puerto documentado por el proyecto |
| 1350 | SnapOtter (GPU) | 1349 | Reservado; evita chocar con el CPU si se levantan a la vez |
| 3000 | *(ocupado)* | — | Lo reserva `filex-gotenberg`, un contenedor **preexistente** parado, de un build local `filex/gotenberg:snapshot` de trabajo anterior. No se ha tocado |
| 3100 | ConvertX | 3000 | Desplazado desde el 3000 por defecto |
| 3200 | Gotenberg 8 | 3000 | Desplazado desde el 3000 por defecto |

Postgres y Redis del stack de SnapOtter **no publican puerto al host**: sólo son alcanzables
desde la red interna `filex-snapotter_default`. Es deliberado, para no chocar con
instalaciones locales de Postgres/Redis del equipo.

### Volúmenes

| Volumen | Contenido | Se puede borrar |
|---|---|---|
| `filex-snapotter_SnapOtter-data` | Datos de SnapOtter: ficheros subidos, venv de IA (~425 MB), logs | Sí, se recrea |
| `filex-snapotter_SnapOtter-workspace` | Temporales de conversión (`/tmp/workspace`) | Sí |
| `filex-snapotter_SnapOtter-pgdata` | Base de datos PostgreSQL | Sí, pierde cuentas e historial |
| `filex-snapotter_SnapOtter-redisdata` | Cola/caché Redis | Sí |
| `filex-convertx_convertx-data` | SQLite de ConvertX + ficheros convertidos | Sí |
| *(Gotenberg)* | — | No tiene: es un servicio **sin estado** |

Además, `docker/snapotter-compose.yml` y `docker/snapotter-gpu-compose.yml` montan
`../corpus` en `/corpus` en **solo lectura**, por comodidad. La UI sube ficheros por HTTP,
así que ese montaje no es imprescindible; está en modo `read_only` para que ningún
contenedor pueda alterar el corpus de pruebas.

### Credenciales

- **SnapOtter**: `admin` / `admin`. Verificado por API:
  `POST http://localhost:1349/api/auth/login` con `{"username":"admin","password":"admin"}`
  devuelve `200` y un token, con `"mustChangePassword": true`. El endpoint `/api/v1/auth/login`
  **no** es el correcto (devuelve 401); la ruta buena es `/api/auth/login`.
- **ConvertX**: sin credenciales. Se arrancó con `ALLOW_UNAUTHENTICATED=true` +
  `HTTP_ALLOWED=true` para que la evaluación posterior no dependa de registrar una cuenta.
  Si se prefiere con login, poner ambas a `false` y registrar la primera cuenta en
  `http://localhost:3100/register` (la primera cuenta que se registre es la administradora).
  El `JWT_SECRET` está fijado en el compose (cadena de investigación, no es un secreto real).
- **Gotenberg**: sin autenticación. Tiene basic auth opcional
  (`GOTENBERG_API_BASIC_AUTH_USERNAME`/`_PASSWORD` + `--api-enable-basic-auth`), no activada.

---

## 4. Verificación de que cada uno responde

### Gotenberg — verificado con conversión real del corpus

```bash
curl http://localhost:3200/health
# {"status":"up","details":{"chromium":{"status":"up",...},"libreoffice":{"status":"up",...}}}
curl http://localhost:3200/version
# 8.36.0
```

Dos conversiones de prueba, ambas **HTTP 200 con PDF válido** (cabecera `%PDF`):

```bash
cd D:\Work\research\FileX

# 1) Ruta LibreOffice: ofimática/datos -> PDF. Fichero patológico: CSV con BOM UTF-8,
#    comillas embebidas, comas dentro de campo y salto de línea dentro de campo.
curl -X POST http://localhost:3200/forms/libreoffice/convert \
  --form "files=@corpus/datos/patologico_bom.csv" \
  -o docker/verify-out/patologico_bom.pdf
# HTTP 200 -> 15 839 B, %PDF-1.7

# 2) Ruta Chromium: HTML -> PDF
curl -X POST http://localhost:3200/forms/chromium/convert/html \
  --form "files=@index.html" \
  -o docker/verify-out/chromium.pdf
# HTTP 200 -> 13 645 B, %PDF-1.4
```

Esto confirma la hipótesis de partida: **Gotenberg cubre ofimática→PDF sin instalar
LibreOffice en Windows**. Trae LibreOffice 26.2 y Chromium dentro de la imagen y los
expone como API HTTP.

### SnapOtter — interfaz y API responden

```bash
curl -o /dev/null -w "%{http_code}" http://localhost:1349/      # 200, <title>SnapOtter</title>
curl -o /dev/null -w "%{http_code}" http://localhost:1349/api/docs  # 301 (redirección, esperado)
curl http://localhost:1349/api/v1/admin/health                  # 401 {"error":"Authentication required"} — correcto sin token
docker inspect -f '{{.State.Health.Status}}' filex-snapotter    # healthy
```

Log de arranque: `SnapOtter v2.2.0 running on port 1349`, `Edition: Community`,
`Storage: local`, `Rate limit: 1000/min`, `Upload limit: unlimited`.

### ConvertX — interfaz responde

```bash
curl -o /dev/null -w "%{http_code}" http://localhost:3100/   # 200, <title>ConvertX</title>
```

Su log de arranque enumera los conversores detectados, útil como inventario previo:
ImageMagick 7.1.2, GraphicsMagick 1.3.46, vips 8.18.3, LibreOffice 26.2.4.2,
ffmpeg 8.1.1, pandoc 3.9.0.2, XeTeX (TeX Live 2026), Inkscape 1.4.3, calibre 9.9.0,
libheif 1.21.2, assimp 6.0, djxl 0.11.2. Declara ausentes `dasel` y `msgconvert`.

---

## 5. Problemas encontrados en Windows / WSL2

### 5.1 El demonio de Docker no estaba arrancado

`docker version` respondía por el cliente pero fallaba contra el demonio:

```
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine;
check if the path is correct and if the daemon is running:
open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
```

Sólo estaba vivo el proceso `wslservice`. Se resolvió lanzando
`"C:\Program Files\Docker\Docker\Docker Desktop.exe"`. **Es el primer paso a comprobar
en cualquier sesión posterior, incluido el carril GPU.**

### 5.2 La VM de Docker está muy limitada: 2 vCPU y 1,86 GiB de RAM

```
docker info --format '{{.NCPU}} {{.MemTotal}}'   # NCPU=2, MEM=1996603392 (1,86 GiB)
```

Esto es lo más relevante de todo el informe para el carril de medición. Con ~2 GB de RAM
compartidos entre los cinco contenedores, cualquier cifra de rendimiento saldrá
estrangulada por la VM y **no será comparable con una ejecución nativa en Windows**.
Recomendación antes de medir nada: subir CPU y memoria en Docker Desktop
(*Settings → Resources*, o `%UserProfile%\.wslconfig` con `memory=` y `processors=`) y
dejar constancia del ajuste, porque cambia todos los números.

Uso actual, para referencia (`docker stats`, en reposo, sin carga):

| Contenedor | Memoria |
|---|---|
| `filex-snapotter` | 87 MiB |
| `filex-convertx` | 104 MiB |
| `filex-gotenberg8` | 57 MiB |
| `filex-snapotter-pg` | 36 MiB |
| `filex-snapotter-redis` | 8 MiB |

### 5.3 Descarga de ConvertX cortada a mitad (resuelto al segundo intento)

```
short read: expected 1432715521 bytes but got 996147200: unexpected EOF
```

La capa grande (1,43 GB) de `ghcr.io/c4illin/convertx` se cortó. El `docker pull` reintentado
tal cual, sin cambios, completó correctamente aprovechando las capas ya bajadas.
Fallo de red transitorio, no de configuración.

### 5.4 SnapOtter en bucle de reinicio: `database "snapotter" does not exist`

El problema que más tiempo costó. Síntoma: `filex-snapotter` alternaba `starting`/`unhealthy`
sin llegar a servir nunca, con este error en bucle:

```
error: database "snapotter" does not exist
  severity: 'FATAL', code: '3D000', routine: 'InitPostgres'
```

**Causa.** El primer `initdb` del contenedor de Postgres se interrumpió a medias (el arranque
del stack se alargó mucho por la lentitud de WSL2). Quedó creado el **rol** `snapotter` pero
**no la base de datos** `snapotter` — comprobado con `\l`, que sólo listaba `postgres`,
`template0` y `template1`, todas con owner `snapotter`.

**Agravante: el healthcheck no lo detecta.** El healthcheck que la propia documentación de
SnapOtter recomienda es `pg_isready -U snapotter -d snapotter`, que **devuelve sano igualmente**
porque sólo comprueba que el servidor acepta conexiones, no que la base de datos exista.
Así que `depends_on: condition: service_healthy` daba luz verde a una BD inservible.

**Arreglo aplicado** (una sola vez, sin recrear volúmenes):

```bash
docker exec filex-snapotter-pg psql -U snapotter -d postgres \
  -c 'CREATE DATABASE snapotter OWNER snapotter;'
docker restart filex-snapotter
```

Tras esto SnapOtter arrancó y quedó `healthy` en ~20 s. La incidencia y su arreglo están
anotados como comentario dentro de `docker/snapotter-compose.yml`. Alternativa limpia si
vuelve a pasar: `docker compose ... down -v` y levantar de nuevo sin interrumpir el arranque.

### 5.5 Gotenberg: LibreOffice agota su timeout de arranque en frío bajo WSL2

Primera conversión ofimática → `HTTP 503`:

```
The request exceeded the time limit. Increase it with --api-timeout, or reduce the workload.
```

En el log del contenedor:

```
convert to PDF: supervisor run task: process first start: start process:
execute LibreOffice: context done: context deadline exceeded    (latency 21,5 s)
```

El culpable no es `--api-timeout` (que ya estaba en 120 s) sino **`--libreoffice-start-timeout`,
cuyo valor por defecto es 20 s**. Arrancar LibreOffice en frío dentro de WSL2 con 2 vCPU se
pasa de ahí. Chromium rozó el mismo límite: su primera petición HTML→PDF tardó 23,4 s
(sí completó, pero por poco).

**Arreglo aplicado** en `docker/gotenberg-compose.yml`:

```yaml
- "--libreoffice-start-timeout=90s"
- "--chromium-start-timeout=90s"
- "--libreoffice-auto-start=true"        # precalienta al iniciar, no en la 1a petición
- "--libreoffice-idle-shutdown-timeout=0" # que no se apague por inactividad
- "--api-timeout=180s"
```

Con esto la conversión pasó a `HTTP 200` a la primera.

> **Aviso para el carril de medición.** Esos 21 s y 23 s son **arranques en frío de los
> subprocesos**, no coste de conversión. `--libreoffice-auto-start=true` los saca de la
> primera petición, pero conviene descartar igualmente la primera medición de cada motor.

### 5.6 SnapOtter: los paquetes pesados de IA no están instalados

El log muestra:

```
[python] [dispatcher] Module 'rembg' not available: No module named 'rembg'
[python] [dispatcher] Module 'mediapipe' not available: No module named 'mediapipe'
[python] [gpu] torch not importable: No module named 'torch'
[python] [dispatcher] Ready. GPU: False. Modules: ['PIL', 'numpy', 'gpu']
```

El contenedor imprime `First run: bootstrapping AI venv from base image...` al primer arranque
y deja ~425 MB en `/data/ai`, pero **sin `torch`, `rembg` ni `mediapipe`**. Es coherente con lo
que documenta el proyecto (los packs de precisión se instalan bajo demanda), pero significa
que **las herramientas de IA —quitar fondo, escalado, transcripción— no funcionarán tal cual**.
Quien haga el carril GPU debe contar con que la primera invocación de una herramienta de IA
disparará una instalación adicional, o instalarlas antes de medir. Sin `torch` no hay CUDA
posible, así que esto es requisito previo del carril GPU, no un detalle.

### 5.7 Contenedor preexistente ocupando el puerto 3000

Ya existía en la máquina un contenedor `filex-gotenberg` (imagen local `filex/gotenberg:snapshot`,
2,43 GB), parado desde hace dos semanas con `Exited (255)` y con el puerto 3000 reservado.
**No se ha tocado** (no formaba parte del encargo). Es la razón por la que ConvertX y Gotenberg
se movieron a 3100 y 3200. Si alguien quiere recuperar el 3000, ese contenedor y su imagen son
candidatos a limpieza, pero conviene confirmarlo antes con quien lo creó.

---

## 6. Comandos exactos para reproducir cada arranque

Requisito previo en cualquier sesión: **Docker Desktop tiene que estar corriendo.**

```powershell
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
# esperar a que responda:
docker info --format '{{.ServerVersion}}'
```

### Descarga de imágenes (ya hecha; sólo si hay que rehacerla)

```bash
docker pull --platform linux/amd64 snapotter/snapotter:latest
docker pull --platform linux/amd64 ghcr.io/c4illin/convertx:latest
docker pull --platform linux/amd64 gotenberg/gotenberg:8
```

### Arranque de los tres (CPU)

```powershell
powershell -File D:\Work\research\FileX\docker\up-all.ps1
```

O uno a uno, desde `D:\Work\research\FileX\docker`:

```bash
docker compose -f snapotter-compose.yml -p filex-snapotter  up -d
docker compose -f convertx-compose.yml  -p filex-convertx   up -d
docker compose -f gotenberg-compose.yml -p filex-gotenberg8 up -d
```

Equivalente sin Compose para SnapOtter (el one-liner de su README, modo *embedded*:
Postgres y Redis dentro del propio contenedor, sin stack de tres piezas):

```bash
docker run -d --name SnapOtter -p 1349:1349 -v SnapOtter-data:/data snapotter/snapotter:latest
```

### Comprobación de que todo responde

```bash
curl -o /dev/null -w "snapotter %{http_code}\n" http://localhost:1349/
curl -o /dev/null -w "convertx  %{http_code}\n" http://localhost:3100/
curl              -w "\ngotenberg\n"            http://localhost:3200/health
docker ps --filter "name=filex-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Parada y borrado limpio

```powershell
# Parar y eliminar contenedores y redes, CONSERVANDO los datos:
powershell -File D:\Work\research\FileX\docker\down-all.ps1

# Además borrar los volúmenes de datos:
powershell -File D:\Work\research\FileX\docker\down-all.ps1 -Purge

# Además borrar las imágenes descargadas (libera ~20,6 GB):
powershell -File D:\Work\research\FileX\docker\down-all.ps1 -Purge -Images
```

Equivalente manual:

```bash
cd D:\Work\research\FileX\docker
docker compose -f snapotter-compose.yml -p filex-snapotter  down -v --remove-orphans
docker compose -f convertx-compose.yml  -p filex-convertx   down -v --remove-orphans
docker compose -f gotenberg-compose.yml -p filex-gotenberg8 down -v --remove-orphans
docker rmi snapotter/snapotter:latest ghcr.io/c4illin/convertx:latest gotenberg/gotenberg:8
```

`down-all.ps1` recoge también el proyecto `filex-snapotter-gpu` por si alguien lo hubiera
levantado, y borra el volumen suelto `SnapOtter-data` que crea el one-liner del README.
No toca el contenedor preexistente `filex-gotenberg` ni la imagen `filex/gotenberg:snapshot`.

---

## 7. Variante GPU: preparada, NO arrancada

`docker/snapotter-gpu-compose.yml` está escrito y listo, con la reserva de dispositivo NVIDIA:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

Usa el puerto **1350** y volúmenes propios (`SnapOtter-gpu-*`) para poder convivir con la
variante CPU sin pisarla.

**Deliberadamente no se ha ejecutado.** Motivos: el encargo lo prohíbe, el carril GPU es
exclusivo de otro agente, y la RTX 3060 (12 GB) tiene ya ~3,3 GB de VRAM ocupados por
aplicaciones de escritorio.

Pendientes que el carril GPU debería resolver **antes** de medir:

1. **Verificar el NVIDIA Container Toolkit en el backend WSL2**, que aquí no se ha comprobado
   (habría requerido ejecutar un contenedor con GPU):
   ```bash
   docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
   ```
2. **Instalar los paquetes de IA que faltan** (`torch`, `rembg`, `mediapipe`) — ver §5.6.
   Sin `torch` no hay CUDA por mucho que se pase `--gpus all`.
3. **Subir los recursos de la VM de Docker** (§5.2): con 2 vCPU y 1,86 GiB, cualquier medida
   es un artefacto de la VM, y menos aún cabrá un modelo de IA en memoria.
4. Confirmar que CUDA está realmente activo tras la primera petición de IA:
   ```bash
   curl -H "Authorization: Bearer $TOKEN" http://localhost:1350/api/v1/admin/health
   # esperado: {"ai": {"gpu": true}}
   ```

Recordatorio: `--gpus all` con `docker run`, o la sección `deploy` de arriba con Compose.
Es la **misma imagen** en ambos casos.

---

## 8. Estado final

```
NOMBRE                  IMAGEN                            ESTADO              PUERTOS
filex-snapotter         snapotter/snapotter:latest        Up (healthy)        0.0.0.0:1349->1349/tcp
filex-snapotter-pg      postgres:17-alpine                Up (healthy)        5432/tcp (interno)
filex-snapotter-redis   redis:8-alpine                    Up (healthy)        6379/tcp (interno)
filex-convertx          ghcr.io/c4illin/convertx:latest   Up                  0.0.0.0:3100->3000/tcp
filex-gotenberg8        gotenberg/gotenberg:8             Up (healthy)        0.0.0.0:3200->3000/tcp
filex-gotenberg         filex/gotenberg:snapshot          Exited (preexistente, no tocado)
```

Nada quedó sin arrancar salvo la variante GPU, por diseño. No se ejecutó ninguna medición
de rendimiento ni ninguna carga sobre la GPU.

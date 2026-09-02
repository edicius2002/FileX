# Lo que queda por hacer

**Al 01/09/2026**, con `main` en verde y la CI en pie. Este fichero es la lista corta y
accionable; el inventario completo —**111 filas**— vive en
[`ESTADO-Y-REPARTO.md`](ESTADO-Y-REPARTO.md) §3, y se cuenta con la orden que hay ahí.

```
inventario   6 ⚫ · 26 🔴 · 7 🟡 · 72 🟢   sobre 111 filas
CI           integridad ✓ · suite ✓        9 comprobaciones, 7 módulos, 198 pruebas
PRs          #1 y #2 fusionados
```

---

## 1. Decisiones que no puedo tomar yo

Estas cuatro no son trabajo: son elecciones. Ninguna se puede resolver midiendo más.

### 1.1 · `C43` — la huella y el intérprete · **la más urgente**

**El sistema dice «caducado» donde debería decir «no comparable».** La huella del código es
función del intérprete (`ast.dump` no da la misma cadena entre versiones), así que el día
que alguien ejecute la suite con otro Python verá **215 aristas falsamente vencidas** y hará
una de las dos cosas malas: resellar a ciegas —indulgencia, justo lo que la trampa 61 vino a
impedir— o resondear 215 aristas para obtener exactamente los mismos números.

Medido con control positivo, mismo runner y mismos bytes:

| | `verificador.py` | `motores.py` |
|---|---|---|
| **3.11.9** | `eec752a87e8927cf` | `c918f1be90ef0652` |
| **3.14.4** | `16ddd8d13d61c4f1` | `605a04d57983eaa5` |

Dos salidas, y no son equivalentes:

- **Meter la versión del intérprete en la huella.** Caduca todo hoy, una vez, y a partir de
  ahí el aviso es verdadero.
- **Declarar el intérprete de sellado y negarse a comparar** entre intérpretes distintos.
  **Recomendada:** no caduca nada y convierte un falso positivo en un error honesto.

> Detalle en la **trampa 105** de `CLAUDE.md`.

### 1.2 · ¿Runner autoalojado?

Es lo único que cubriría GPU, NTFS y los contenedores locales — hoy la CI no toca **nada**
de eso, que es casi todo el valor del proyecto (`CONTRIBUTING.md` §1). Y expondría el
escritorio de esta máquina a cualquier PR de un tercero, que es exactamente lo que un
repositorio público no debería hacer sin pensarlo.

### 1.3 · marker / surya / MinerU — `B3`, `B4`, `B5`

**Se miden o se cierran como descartados.** Llevan sin una sola medida desde el 23/08:
`bench/salidas-marker/` sólo contiene un `logs/` vacío. Si se cierran, `.venv-marker`
(**1 205 MB**) sale de la lista protegida de `CLAUDE.md` §1.

### 1.4 · ¿El veredicto de un PR es la CI o soy yo? · **RESUELTO el 01/09**

Sin runner local, un `✅` de GitHub **no dice que la medición esté bien**: dice que la
documentación es coherente y que el código importa en Linux.

**Decidido: el maestro empuja, abre el PR y fusiona.** Los workers entregan la rama
commiteada y nada más — no por jerarquía, sino porque `gh auth` vive en el `home` de cada
agente y **no tienen credenciales**: se midió cuando worker2 terminó su encargo entero y no
pudo entregarlo (`git push` → *«could not read Username»*). La alternativa —autenticar `gh`
en cada worker— reparte credenciales entre cuatro sesiones para ahorrar una orden, y no
compensa. Escrito en `CONTRIBUTING.md` §7.

---

## 2. Listo para despachar — ronda 3

Los dos carriles llevan parados desde la mañana del 01/09. **Dos encargos, no cuatro**: la
ronda 2 perdió **40 minutos medidos** en un solo relevo (trampa 100), y hay una variable
nueva —los *worktrees* van **12 y 15 commits por detrás de `main`**, donde está la CI que va
a juzgar sus PRs—. Con dos veo si el flujo de PR funciona antes de multiplicarlo.

| PR | Rama | Carril | Qué cierra |
|---|---|---|---|
| #3 | `gpu/psm-suelo-ppp` | worker1 | **`B21` + `B22`** con `psm 3` y `psm 11` — el pendiente que worker1 declaró él mismo al cerrar la ronda 2 |
| #4 | `cpu/manifiestos-y-ci` | worker2 | **`C41` + `C42`** — los 17 manifiestos y por qué 10 de 17 módulos no corren en el runner |

**Antes de empezar, cada worker hace `git fetch && git rebase origin/main` en su worktree.**

### Ronda 4, ya con el flujo rodado

| Rama | Carril | Qué cierra |
|---|---|---|
| `gpu/k-y-oem` | worker1 | **`B23` + `B24` + `B16`** — el `k` sobre tres documentos que comparten generador, el `--oem`, y los dos acantilados sin puntos intermedios |
| `cpu/g6-y-acuerdo-ocr` | worker2 | **`C27` + `C20`** |

---

## 3. Deuda que la CI cuenta

Las cuatro salieron del barrido del 01/09 y están **congeladas en `ci/heredado.json`**: no
rompen la CI, pero el trinquete impide que crezcan, y **obliga a encoger la lista** cuando
una se arregla.

| | Qué es | Estado |
|---|---|---|
| **`C40`** | 3 binarios sueltos fuera de LFS, en `salidas-mcp-refs/multimedia/` | 🟡 **refutada en 7 de 10** — ver abajo |
| **`C41`** | 17 directorios `bench/salidas-*` sin manifiesto | 🔴 |
| **`C42`** | 10 de 17 módulos no corren en el runner: 1 cuelga, 9 fallan | 🔴 |
| **`C43`** | La huella y el intérprete | 🔴 · §1.1 |

> **`C40` estaba mal y la refutó el propio repositorio, el mismo día que la abrí.** La regla
> §6 dice *«no versiones salidas binarias **regenerables**»* y yo cité la mitad. Siete de los
> diez binarios están en `bench/salidas-competidores/`, declarada desde el 20/08 como
> *«evidencia forense irreproducible»* — son las salidas de los **siete fallos independientes
> en seis proyectos** que son el argumento entero de FileX. **Borrarlas para cumplir la regla
> de peso habría destruido la prueba.** Trampa 106.

**`C41` no es mecánico.** Cada manifiesto exige `sha256`, tamaño y **la orden exacta que lo
reproduce**. Escribir diecisiete a ojo produce diecisiete manifiestos falsos, que es peor
que ninguno.

---

## 4. Bloqueado, y por qué

| | Qué falta |
|---|---|
| **`C6`** | Una clave de API que no existe en esta máquina |
| **`C16`** | El corpus FATE de ffmpeg, ~1 GB. Tiene un segundo cliente: **`C28` exige el mismo corpus**, así que cerrar uno abarata el otro |
| **`C7`** | Datos de demanda, no una medición |

---

## 5. Fuera del repositorio — sólo tú puedes

1. **La contraseña de SnapOtter sigue viva en el contenedor.** Se borró de las 65 revisiones
   el 31/08 y del residuo de `.git` el 01/09 (48 ocurrencias en `fast-export.original`,
   trampa 102), pero **eso no la cambia en el contenedor**.
2. **`fabian.espinoza@ucsp.edu.pe` es público** en los 82 commits. Cambiarlo pide otra
   reescritura de historia — y esa mataría otra vez todas las citas de hash, que es
   exactamente lo que costó reparar el 01/09.
3. **Tres respaldos en `D:\Work\research\`**, y el primero **contiene el historial sin
   limpiar, con la credencial**:
   - `FileX-git-backup-20260831.tar.gz`
   - `FileX-worktrees-backup-20260831.tar.gz`
   - `FileX-worker2-parche-N28.patch`

---

## 6. CCB — los dos workers pasan a `claude`

`.ccb/ccb.config` **ya está cambiado**:

```toml
workers = "worker1:claude(worktree), worker2:claude(worktree)"
```

**Pero no está aplicado, y hace falta que lo apliques tú.** `ccb reload` es **aditivo** y un
cambio de proveedor se clasifica como `replace_agent`:

```
reload_status: noop        safe_to_apply: false        future_safe_to_apply: true
reload_operation: op=replace_agent agent=worker1 fields=provider
reload_operation: op=replace_agent agent=worker2 fields=provider
reload_drain_active_count: 0        ← no hay trabajo en vuelo: es seguro
```

Aplicarlo pide **reiniciar el runtime**, y eso **respawnea los paneles — el mío incluido**,
así que no lo hago yo:

```sh
ccb -n      # rebuild del estado de runtime, preservando config e historia de agentes
```

Dos avisos:

- **Se pierde el contexto de los workers**, que hoy es de sesiones de `codex`
  (`.ccb/.codex-worker1-session`). No hay trabajo en vuelo —la ronda 2 cerró—, así que el
  coste es cero, pero los ficheros de sesión viejos quedan ahí y **no** se reutilizan.
- `ccb restart worker1` **murió con `137`** al intentarlo por agente. No insistí: el runtime
  es tu entorno y ya se me fue una orden.

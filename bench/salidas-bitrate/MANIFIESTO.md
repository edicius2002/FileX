# `bench/salidas-bitrate/` — manifiesto (agente N4)

Salidas de `bench/bitrate-y-lock.md`: N24 (regla de bitrate de vídeo), N25 (el
lock de GPU alrededor del codificado) y N22 (`.pdb`).

**Aquí no hay un solo binario.** Los 88 ficheros de vídeo de la campaña
(≈400 MB) vivieron en un directorio desechable de `%TEMP%` y se borraron al
terminar (`CLAUDE.md` §6). Las tres muestras de `.pdb` viven **en base64 dentro
de `muestras_pdb.py`**, que las reconstruye y se autocomprueba.

**La GPU no se usó.** Otro agente la tenía. Ninguna orden de aquí codifica en la
tarjeta y ninguna toma el lock de máquina: `medir_lock.py` apunta `GPU_LOCK` a un
fichero propio, y `calibrar_bitrate.py` veta NVENC precargando `gpu._CACHE`.

---

## Cómo se reproduce todo

Con el corpus de LFS restaurado (`git lfs checkout`; `corpus/imagen/tipico.png`
debe pesar 42 855 B) y desde la raíz del repositorio. `$W` es un directorio
desechable **vacío**, fuera del repositorio.

```sh
W=$TEMP/n4-trabajo && mkdir -p "$W"

# 1. El mecanismo: ¿publica la sonda el bitrate de una pista de vídeo?  (§2.1)
python bench/salidas-bitrate/dbg_sonda.py "$W"

# 2. Las 84 celdas de calibración.  ~35 min, solo CPU.                  (§2.2)
python bench/salidas-bitrate/calibrar_bitrate.py "$W"
python bench/salidas-bitrate/calibrar_bitrate.py "$W" --solo=2pistas

# 3. Las tablas de meseta y de solape.                                  (§2.4-2.5)
python bench/salidas-bitrate/analizar_bitrate.py

# 4. El contrato entero sobre las 84, antes y después.                  (§2.6)
python bench/salidas-bitrate/verificar_v10.py --antes "$W"
python bench/salidas-bitrate/verificar_v10.py "$W"

# 5. Las 53 del patrón oro, antes y después.                            (§2.7)
python bench/salidas-bitrate/regresion_53_n4.py --antes
python bench/salidas-bitrate/regresion_53_n4.py
python bench/salidas-bitrate/regresion_53_n4.py --diff

# 6. El coste del lock y de la guardia.  Con la máquina en reposo.      (§3.1)
python bench/salidas-bitrate/medir_lock.py "$W"

# 7. Las tres muestras de .pdb, reconstruidas y comprobadas.            (§4.2)
python bench/salidas-bitrate/muestras_pdb.py "$W"

rm -rf "$W"
```

### Las muestras de `.pdb`, producidas de cero

Necesita el contenedor `filex-c13` (ConvertX + `qpdf` + `tesseract`), que trae
`magick`, `gm` y `ebook-convert`. `--init` es obligatorio: sin él, `timeout`
queda de PID 1 y `docker run` devuelve `rc=125` y cero bytes (trampa 71).

```sh
docker run --rm --init --name n4-pdb --entrypoint timeout filex-c13 -k 5 900 sh -c '
  cd /tmp && mkdir -p w && cd w &&
  magick -size 64x48 gradient:red-blue s.png &&
  magick s.png im.pdb &&
  gm convert s.png gm.pdb &&
  printf "Titulo\n\nParrafo de prueba.\n" > s.txt &&
  ebook-convert s.txt cal_doc.pdb >/dev/null 2>&1 &&
  ebook-convert s.txt cal_ereader.pdb -f ereader >/dev/null 2>&1;
  for f in im.pdb gm.pdb cal_doc.pdb cal_ereader.pdb; do
    echo "@@$f"; base64 -w0 $f; echo; done' > b64.txt

# y el diccionario del fixture se REGENERA, no se teclea (§4.4)
python bench/salidas-bitrate/gen_muestras_pdb.py b64.txt
```

---

## Resultados versionados (todos texto)

| fichero | contenido | de qué sección |
|---|---|---|
| `calibracion.json` | 84 celdas: `trivial`+`tipico` legítimas, `2pistas` en blanco (destino mal elegido, registrado), y las 12 patológicas | §2.2 |
| `calibracion_2pistas.json` | las 24 legítimas de `2pistas` contra `.mp4` y sus 4 patológicas | §2.2 |
| `v10_antes.json` / `v10_despues.json` | el contrato entero sobre las 84, con `HEAD` y con el árbol | §2.6 |
| `regresion_antes.json` / `regresion_despues.json` | las 53 del patrón oro, contrato y fidelidad | §2.7 |
| `medicion_lock_tanda1.json` | la tanda **contaminada** por mi propia campaña. Se publica para que se vea la diferencia | §3.1 |
| `medicion_lock.json` | la tanda limpia (deriva ×1,018). **Es la que compara con H2** | §3.1 |

## Scripts

`dbg_sonda.py` · `calibrar_bitrate.py` · `analizar_bitrate.py` ·
`verificar_v10.py` · `regresion_53_n4.py` · `medir_lock.py` ·
`muestras_pdb.py` · `gen_muestras_pdb.py`

`regresion_53_n4.py` es **copia** de `bench/salidas-contrato-v/regresion_53.py`
(agente V) con dos cambios declarados en su cabecera: escribe en este directorio
y remapea las 53 salidas a su ruta absoluta, porque **en un worktree no existen**
(§1.1). El original se lee y no se toca.

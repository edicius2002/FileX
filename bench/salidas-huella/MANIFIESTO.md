# MANIFIESTO — `bench/salidas-huella/`

C41. Todo el contenido es texto (`.py`/`.json`) y se versiona entero (regla
§6). La mayoría de las órdenes ya estaban escritas en `bench/huella-y-tablas.md`
§12 ("Reproducir"); este manifiesto añade `sha256`/tamaño verificados contra
el árbol actual y documenta los tres scripts que ese §12 no listaba.

**MEDIDO** (`sha256sum`/`stat`, 01/09/2026). Último commit que tocó el
directorio: `6e90a34` ("La trampa 49 exageraba: eran 3 de 5, y el agujero
gemelo estaba en el motor").

## Pares script → salida (orden citada en `bench/huella-y-tablas.md` §12)

| Script | Tamaño (B) | SHA-256 | Salida | Tamaño (B) | SHA-256 | Orden |
|---|---:|---|---|---:|---|---|
| `censo_alcance.py` | 7 991 | `bede347f5bbecf0bf61ff14c8ebcafc1cce60755f20d49a5cdb201954ae35d0d` | `censo_alcance.json` | 2 926 | `346da9e216c642da1d8d52f44703b82accce81c28774e1ef053d632085420581` | `python bench/salidas-huella/censo_alcance.py` — el mecanismo (§2) |
| `censo_motor.py` | 1 442 | `eb025946222747a9ed7e53468782c85fa4fe223bb37dcb18f36a4f9286667dc2` | *(sin JSON propio — imprime a stdout, citado en §3)* | — | — | `python bench/salidas-huella/censo_motor.py` |
| `alcance_por_clase.py` | 1 137 | `21b7e2fc10374c250bf96b1e68f6c0842d3ae68959cab00195d706b3d9a18e32` | *(sin JSON propio — imprime a stdout, §3.2)* | — | — | `python bench/salidas-huella/alcance_por_clase.py` |
| `control_motor.py` | 2 803 | `41cb52baea8f40b7bffb963344d587f56f2839c26f10da60ca21986600f538ea` | `control_motor.json` | 539 | `f150129a33cc2d2b92384032248171d3471303982fc5dd298ac68900047f6a68` | `python bench/salidas-huella/control_motor.py` — control positivo (§3) |
| `historia.py` | 4 509 | `0c8cd97a3723bc76fb13be86fb1d2836543a226085de7217aec8e5e6db7597ba` | `historia.json` | 4 216 | `95d209c6244c7572acd8bb72e587a7e1adb481e1eb03a9fcc1d7aa55cc6a7afe` | `python bench/salidas-huella/historia.py` — validación histórica, componente `contrato` (§5.1) |
| `historia_motor.py` | 4 857 | `fecb0bc38a8ae6dc5d6620abc9824b07606921df9139854dd5abb18ebda59388` | `historia_motor.json` | 3 826 | `e5aaf2bdf2428bef00c0f403fa13153deb19a08e587c315df11e3f0c38fed046` | `python bench/salidas-huella/historia_motor.py` — refutación propia, componente `motor` (§5.2) |
| `granularidad.py` | 3 141 | `56fd7185eb3bb7024cab86e48e007d854ebc660775042364e3b2f38ad536f86c` | `granularidad.json` | 1 346 | `a52287751e20f729b39713752788b960806c6eae79d2d331d2f4886bb678d319` | `python bench/salidas-huella/granularidad.py` — tabla de opciones de granularidad (§4.1) |
| `coste.py` | 4 280 | `0ce96cb8b639f8f6d879c19bbad8481d71d4b0914bd875f6e4c5ed26d524aa68` | `coste.json` | 490 | `4498e60f5d756c7a578dc32c7b7689c7d17720ed802baed6e48f9c80a4efba43` | `python bench/salidas-huella/coste.py` (n=9) — primera medida de coste, §6, **superada por el pareado siguiente** |
| `coste_pareado.py` | 4 759 | `d409e15d02e857f675cc3317ebb1394a11e5eb0f35074dd822b820f8ad910806` | `coste_pareado.json` | 487 | `5350b5079edc451f1abbb5d09c840775877f80da6e8fcf5ac56ad678e887b007` | `python bench/salidas-huella/coste_pareado.py` (n=9) — el coste real, pareado (§6) |
| `resellar.py` | 5 666 | `30ea307aa2fbf7199a977a52e13e71c7af23dff4b38b7e04f9b8b0123d71c79c` | `resellado.json` | 2 904 | `342b59cd5977d854be855786cfba0eb8ddefda781203c94df48e41a61c917bfb` | `python bench/salidas-huella/resellar.py --comprobar` (no escribe) o `--escribir` (§7); comprueba ANTES de resellar que las huellas ya guardadas en `filex/sondeo/*.json` coinciden con el algoritmo vigente sobre el árbol actual |
| `grafo.py` | 896 | `5468a79e194e87950ae6f58fcbb9343cfdb7bd19eab2144777086a84f0728acb` | `grafo.json` | 152 | `6fb3f7cbde1c58708a74e658179afc777b571cdb84f82b16417b0ac43ccbaeb3` | `python bench/salidas-huella/grafo.py` — 210 aristas `real`, 5 `nominal` |
| `sin_arreglo.py` | 2 229 | `9bd126a20d5661f1137173a0cf98ac3c1bc02bb9887439f182beb81451013d5b` | *(sin JSON propio — corre la suite y reporta a stdout, §8)* | — | — | `python bench/salidas-huella/sin_arreglo.py` — reproduce las 6 pruebas que fallan sin el arreglo |

## Utilidad sin salida propia dentro del directorio

| Fichero | Tamaño (B) | SHA-256 | Qué hace | Orden |
|---|---:|---|---|---|
| `estado.py` | 1 171 | `378e2038813cdd32d710c2f7c2a51fcd7c71a22afd0b48ab8fd4ec5698773a95` | Imprime `sondeo.diagnostico()` a stdout, antes y después del arreglo (§7). No escribe fichero. | `python bench/salidas-huella/estado.py` |
| `nota.py` | 1 848 | `a817655e86ac1c6b9b002fb8133a036f8022692a2ee62b7d6958ae4a4b367fe1` | **No genera nada en este directorio**: añade a los CINCO ficheros de `filex/sondeo/*.json` (fuera de `bench/`) el campo `nota_resellado` explicando la trampa 44 (una nota que seguía siendo cierta pero dejó de explicar el valor). Es un parche de un solo uso sobre datos de producto, no un generador de esta carpeta. | `python bench/salidas-huella/nota.py` |

## No genera fichero propio (documentado en §12 pero sin JSON de salida)

`python -m pytest pruebas/test_sondeo.py -q` — 38 passed (§8), no es parte de este directorio.

## MEDIDO — verificación de consistencia

`censo_alcance.py`, `historia*.py`, `granularidad.py`, `control_motor.py` y
`resellar.py` cargan `HEAD:filex/huella.py` en un fichero temporal
`_huella_head.py` que es regenerable y correctamente **no** está versionado
(no aparece en `git ls-files`, confirmado).

## Salvedad de reproducibilidad, declarada

Estos scripts miden el estado de `filex/huella.py`, `filex/verificador.py`,
`filex/motores.py` y `filex/motor_contenedor.py` **en el momento en que se
ejecutan**. Como advierte la trampa 32/61 de `CLAUDE.md`, re-ejecutarlos hoy
sobre un árbol que ya avanzó de ronda no reproduce necesariamente los mismos
valores — el manifiesto documenta la orden que generó el fichero committeado,
no una garantía de identidad futura.

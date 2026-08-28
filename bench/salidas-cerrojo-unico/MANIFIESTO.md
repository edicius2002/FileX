# Salidas del agente P — `bench/cerrojo-unico.md`

**Ninguna salida binaria.** Todo es `.py`, `.json` y logs de texto, así que se
versiona entero (`CLAUDE.md` §6). El único directorio desechable que usan los
arneses se crea con `mkdtemp`, se lista antes y después (R21) y se borra dentro
del propio arnés.

**No se usó la GPU.** El encargo no la necesita; `nvidia-smi` no se llamó ni una
vez, y no se tomó el lock de GPU porque no había nada que proteger.

Todo se ejecuta desde la raíz del *worktree*, con `python` 3.11.9 en el PATH.
**Antes de nada: `git lfs checkout`**, o `corpus/imagen/tipico.png` pesa 130 B y
el arnés de coste no puede convertir nada (trampa 34 propuesta por N-b).

| Fichero | Qué mide | Orden exacta |
|---|---|---|
| `sonda_maquina.py` / `.json` / `logs/sonda_maquina.log` | §2.1: `Local\` frente a `Global\`, exclusión entre dos procesos, `taskkill /F`, metadatos y coste del mutex | `python bench/salidas-cerrojo-unico/sonda_maquina.py` |
| `sonda_namespace.py` / `.json` / `logs/sonda_namespace.log` | §2.2: que el objeto vive **de verdad** en `\BaseNamedObjects`, por `NtOpenMutant` con ruta absoluta y control negativo | `python bench/salidas-cerrojo-unico/sonda_namespace.py` |
| `sonda_dacl.py` / `.json` / `logs/sonda_dacl.log` | §2.3: el SDDL real del mutex con descriptor por defecto y con descriptor explícito | `python bench/salidas-cerrojo-unico/sonda_dacl.py` |
| `sonda_wsl.py` / `.json` / `logs/sonda_wsl.log` | §3: si el candado cruza a WSL2, en las **dos** direcciones, con control positivo dentro de WSL2 | `python bench/salidas-cerrojo-unico/sonda_wsl.py` (necesita `wsl.exe -d Ubuntu` con `python3`) |
| `sonda_enlaces.py` / `.json` / `logs/sonda_enlaces.log` | §4: b4 — enlace duro, enlace simbólico y unión de directorio; y el coste de la identidad NTFS | `python bench/salidas-cerrojo-unico/sonda_enlaces.py` |
| `coste_cerrojo_unico.py` / `coste.json` / `logs/coste_cerrojo_unico.log` | §5: las cinco configuraciones, el desglose y la conversión de referencia, **todo en la misma tanda**, con los dos testigos de ruido | `python bench/salidas-cerrojo-unico/coste_cerrojo_unico.py` |

## Cómo se reproduce el antes y el después sin tocar `git`

Las dos mitades nuevas se apagan con una variable, igual que el
`FILEX_CERROJO_DESTINO` de N-b, para poder comparar **dentro de la misma tanda**:

```
FILEX_CERROJO_MUTEX=0      python -m pytest pruebas/test_cerrojo_unico.py -q
FILEX_CERROJO_IDENTIDAD=0  python -m pytest pruebas/test_cerrojo_unico.py -q
```

La primera deja `1 failed` (b1, `test_dos_directorios_de_candados_distintos_siguen_excluyendose`);
la segunda, `2 failed` (b4, las dos de `EnlaceComoDestino`). Sin ninguna de las
dos: `11 passed`.

## Nota sobre una sonda que falló, y se deja como falló

`sonda_namespace.py` intenta **enumerar** `\BaseNamedObjects` con
`NtQueryDirectoryObject`. El primer intento devolvió **0 objetos y ningún
error** —sin `argtypes`, `BOOLEAN` de NT es de un byte y no el `BOOL` de
cuatro—; el segundo, ya con las firmas declaradas, devuelve
`NTSTATUS=0x00000105` en la primera llamada. **Dos intentos y se para**
(`CLAUDE.md` §3). El veredicto no depende de ella: lo da `NtOpenMutant` con la
ruta absoluta, que es más directo y trae su propio control negativo
(`0xC0000034` sobre un nombre inventado).

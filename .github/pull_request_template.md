<!--
La CI comprueba coherencia documental y que el código importa en Linux. NO puede
ejecutar la GPU, ni los contenedores locales, ni las pruebas `win32`, que son
casi todo el valor del proyecto. Por eso el recuento de la suite lo declaras tú.
Ver CONTRIBUTING.md §1.
-->

## Qué cierra

<!-- Identificadores del inventario de ESTADO-Y-REPARTO.md §3: B21, C27, N9… -->

## El resultado, en una frase

<!-- El hallazgo, no la lista de tareas. Si refuta algo, dilo aquí: refutar una
     conclusión propia es el resultado más valioso que se puede traer. -->

---

## Las cuatro declaraciones de la suite

> Un `0 failed` no significa nada sin las cuatro. Trampas 94 y 101.

| | |
|---|---|
| **Intérprete** | <!-- p.ej. .venv-mcp-filex\Scripts\python.exe · win32 · 3.11.9 --> |
| **Entorno** | <!-- ¿demonio de Docker levantado? ¿GPU libre? --> |
| **Qué quedó fuera, y por qué** | <!-- los saltados, uno a uno --> |
| **Estado de la máquina** | <!-- carga, y si el lock de GPU estaba tomado --> |

```
<!-- pega aquí la línea de recuento: N passed · N skipped · N failed · Ns -->
```

---

## Comprobaciones

- [ ] `python3 ci/integridad.py` en verde
- [ ] Cada afirmación marcada **MEDIDO** o **PENDIENTE**, y las medidas traen su `n` y la
      orden que las reproduce
- [ ] El informe va en `bench/`, **uno por agente**, y está registrado en la tabla de §1 de
      `ESTADO-Y-REPARTO.md`
- [ ] Las filas del inventario que cierro están movidas, y la línea «Salida esperada hoy»
      actualizada
- [ ] No he tocado módulos de otro carril (`CONTRIBUTING.md` §2)
- [ ] Si genero salidas grandes: borradas, con `MANIFIESTO.md` y la orden que las reproduce
- [ ] Si añado una trampa: **al final**, y el número actualizado en `README.md` y en §10

## Lo que dejo abierto

<!-- PENDIENTES explícitos. Un pendiente declarado vale; uno callado es deuda que
     alguien pagará sin saber que existía. -->

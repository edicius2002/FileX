### 6.1 ¿27 herramientas degradan la elección?

> **MEDIDO: no.** En 540 ejecuciones, dos modelos y cuatro estratos de dificultad, el catálogo de
> **27** herramientas obtuvo **100 % / 98 %** de acierto permisivo (Haiku / Sonnet) y **0 % / 2 %**
> de elecciones trampa. El de **8**, **85 % / 77 %** y **15 % / 17 %**. **El catálogo grande eligió
> mejor, no peor.**
>
> **MEDIDO: la redundancia tampoco.** El contraste limpio A (27) vs C (14) —el mismo catálogo con y
> sin las 13 herramientas subsumidas— no muestra ninguna diferencia una vez se quita la única tarea
> cuya clave de corrección era un juicio discutible: **100 % vs 100 %** en Haiku y en Sonnet.
>
> **MEDIDO: la ambigüedad estructural no predijo el comportamiento.** El par que
> `bench/mcp-refs-multimedia.md` §5.2 declaró «el peor» del catálogo acertó **30 de 30**.

**Y la parte incómoda del resultado:** el 48,1 % de herramientas confundibles, el 37 % de
indistinguibles salvo por el nombre de sus argumentos y los 13 pares con descripciones casi
idénticas de §5 **son reales y están medidos** — pero **el modelo los desambigua igual**. La
ambigüedad léxica de un catálogo es un indicador de **mala higiene de interfaz**, no un predictor
de errores de elección. Este informe es la evidencia de que no hay que confundir las dos cosas.

### 6.2 ¿Se sostiene el objetivo de cuatro herramientas de FileX?

> **Sí, pero por una sola razón: el coste. La conductual no aparece.**

Era exactamente la pregunta del encargo, y la respuesta es la que no se esperaba:

| Argumento para exponer pocas herramientas | Estado |
|---|---|
| **Coste en tokens** | **MEDIDO y confirmado, y peor de lo que se creía**: el catálogo se paga **en cada turno**, con un multiplicador de **×2,0–2,6**. Un catálogo de 7.886 tokens cuesta ≈ 23.600 tokens de entrada por petición sencilla. |
| **Calidad de la elección** | **MEDIDO: no aporta nada.** 27 herramientas no degradaron la elección frente a 8 ni frente a 14. **El segundo argumento independiente que se buscaba no existe.** |
| **Riesgo nuevo, en dirección contraria** | **MEDIDO**: un catálogo demasiado escueto para su dominio produce **fallos silenciosos**: el modelo llama a la herramienta más parecida y **declara éxito con un dato falso**. 15–17 % de las peticiones en el catálogo de 8. |

La decisión de FileX —cuatro herramientas— **no cambia**. Lo que cambia es su **justificación** y,
sobre todo, **lo que hay que hacer además**: si las cuatro herramientas de FileX no cubren lo que el
usuario pide, el modelo **no dirá que no puede**; inventará que sí. Eso convierte la **cobertura
declarada** de `convert` en un requisito de seguridad, no de comodidad.

### 6.3 Lo que este experimento **no** demuestra

- **No** demuestra que el tamaño del catálogo sea irrelevante **en general**. Demuestra que **entre
  8 y 27 herramientas, en un dominio, con dos modelos de la familia Claude, no se detectó
  degradación.** Nada dice de 60, ni de 200, ni de varios servidores MCP a la vez. **PENDIENTE.**
- **No** descarta caídas pequeñas: con n = 120 por celda, una caída de 100 % a 97 % pasaría
  desapercibida. **PENDIENTE.**
- **No** dice nada de modelos de otras familias ni de modelos pequeños locales, que es un escenario
  que FileX contempla. **PENDIENTE.**

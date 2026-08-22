### 7.1 En qué unidad se mide el presupuesto

> **En tokens, no en número de herramientas.** Y este experimento añade la razón conductual de por
> qué el número no sirve: **el número no predijo nada** (27 no eligió peor que 8), mientras que los
> tokens **sí** se pagan, y se pagan **más de una vez**.

La regla vigente (`RESULTADOS-MCP.md` §4) es **≤ 1.200 tokens para las cuatro herramientas**.
**Se confirma, y se le añade la cifra que le faltaba:**

> **MEDIDO: cada token de catálogo cuesta ×2,0–2,6 tokens de entrada por petición**, porque el
> catálogo viaja en cada turno y un intercambio típico tuvo **2,1 turnos**.
>
> **Un catálogo de 1.200 tokens costará ≈ 2.400–3.100 tokens de entrada por petición sencilla.**
> Ese, y no 1.200, es el número que hay que comparar con el resto del presupuesto de contexto.

### 7.2 Las tres reglas que se recomiendan, y de dónde sale cada una

**Regla 1 — presupuesto de tokens (se mantiene, con el multiplicador explícito).**

| | Valor |
|---|---:|
| `tokens_catalogo` de `convert` + `inspect` + `list_targets` + `batch` | **≤ 1.200** |
| Coste real esperado por petición (×2,0–2,6) | **≈ 2.400–3.100 tokens** |
| Referencia: `video-audio-mcp` | 7.886 → **≈ 19.000–23.600** |
| Referencia: `ffmpeg-mcp-lite` | 2.306 → **≈ 8.300–8.800** |

**Regla 2 — el solapamiento se mide, pero como higiene, no como predictor de errores.**

Las métricas de §5 son deterministas, cuestan un segundo y se pueden meter en una prueba automática.
Umbrales que **los tres catálogos de referencia permiten calcular** y que un catálogo de cuatro
herramientas debe cumplir con holgura:

| Métrica (`estatico.py`) | Umbral propuesto | A (27) | C (14) | B (8) |
|---|---:|---:|---:|---:|
| Pares con similitud de nombre ≥ 0,70 | **0** | 22 | 2 | 2 |
| Pares con similitud de descripción ≥ 0,85 | **0** | 13 | 0 | 0 |
| Herramientas **indistinguibles salvo por el nombre de sus argumentos** | **0** | **10 (37 %)** | 0 | 0 |
| Familias de prefijo con ≥ 3 miembros | **0** | 4 | 0 | 0 |
| Descripciones con `PRD` / `previous` / `see` / `above` / `brevity` / `TODO` | **0** (con lista de excepciones anotadas: §5.5 dio 1 falso positivo de 4) | 3 | 3 | 0 |
| Esquemas opacos (`object`/`array of object` sin claves) | **0** | 3 | 3 | 0 |
| **Parámetros sin `description` en el JSON Schema** | **0** | **102 / 102** | **63 / 63** | **28 / 28** |

**La última fila es la más importante y es un hallazgo nuevo de este informe.** **MEDIDO: ninguno de
los 193 parámetros de los tres servidores de referencia lleva descripción en su esquema.** FastMCP
deriva el esquema de las anotaciones de tipo y deja toda la semántica en la prosa del docstring. Para
FileX, cuya herramienta `convert` va a tener parámetros con `enum` generados desde el registro
(`PLAN-ORQUESTADOR.md`), eso es inaceptable: **cada parámetro debe llevar su `description` en el
esquema**, con `Field(description=...)` o equivalente. Es lo que impide que una herramienta acabe
como `add_b_roll`, con un array de objetos arbitrarios y una descripción que remite a documentos
invisibles.

**Regla 3 (nueva, y la que este experimento obliga a añadir) — presupuesto de cobertura.**

El fallo medido no es de exceso, es de defecto: **cuando el catálogo no cubre lo que se pide, el
modelo no se abstiene — inventa que sí lo ha hecho** (§3.5). En el catálogo de 8 herramientas eso
ocurrió en el **15–17 %** de las peticiones. Por tanto:

- **`list_targets` deja de ser una comodidad y pasa a ser el mecanismo de seguridad**: es la única
  herramienta que puede decirle al modelo, **en tiempo de ejecución y sin inventar**, qué
  conversiones existen. Debe ser la respuesta canónica a «¿puedo hacer X?».
- **`convert` debe fallar explícitamente** ante una combinación no soportada, con un mensaje que
  nombre la alternativa. El silencio es el modo de fallo peligroso, no el error.
- **La descripción de `convert` debe declarar sus límites**, no solo sus capacidades. Los tres
  servidores de referencia describen lo que hacen; **ninguno describe lo que no hace**, y ahí es
  exactamente donde se producen los fallos silenciosos.
- **Prueba de regresión recomendada:** un conjunto de peticiones **fuera** de la cobertura de FileX,
  cuyo criterio de acierto es **la abstención**. Es barata (el arnés de este informe la ejecuta tal
  cual) y es la única que detecta este modo de fallo.

### 7.3 Resumen del presupuesto recomendado

| Dimensión | Recomendación | Base |
|---|---|---|
| **Tokens de catálogo** | **≤ 1.200** para las cuatro herramientas | `RESULTADOS-MCP.md` §4, **confirmado** |
| **Coste real a presupuestar** | **≈ 2.400–3.100 tokens/petición** (×2,0–2,6) | **MEDIDO aquí**, §3.6 |
| **Número de herramientas** | **no es el presupuesto**; 4 está bien, pero por coste | **MEDIDO aquí**, §6.2 |
| **Solapamiento** | **0** en las seis métricas de la Regla 2 | **MEDIDO aquí**, §5 — higiene, no predictor |
| **Documentación de parámetros** | **100 %** de los parámetros con `description` | **MEDIDO aquí**, §5.4 |
| **Cobertura** | declarada, consultable vía `list_targets`, y con prueba de abstención | **MEDIDO aquí**, §3.5 |

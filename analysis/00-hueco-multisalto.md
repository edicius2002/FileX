# Hueco sectorial verificado: nadie encadena conversiones

Barrido sobre los 7 orquestadores clonados, buscando `dijkstra|shortest.?path|conversion.?graph|multi.?hop|conversion.?chain|find.?path` en su código fuente (excluyendo tests, node_modules y falsos positivos de rutas de fichero):

| Orquestador | Coincidencias |
|---|---|
| ConvertX | 0 |
| SnapOtter | 0 |
| transmute | 0 |
| VERT | 0 |
| morphos | 0 |
| gotenberg | 0 |
| Stirling-PDF | 0 |

**Ninguno implementa búsqueda de camino.** Todos hacen lookup directo `(origen, destino) → un motor`; si ningún motor cubre el par, la conversión no existe.

La única pista de que la necesidad es real está en `transmute/backend/converters/libreoffice_convert.py:333`:
> `# Image output via PDF intermediary (all input formats, all pages)`

Es decir: el salto intermedio se resuelve **a mano, dentro de un adaptador concreto**. Nadie lo ha generalizado.

## Por qué importa para FileX

Modelar el catálogo como **grafo dirigido con coste por arista** y aplicar Dijkstra da tres cosas gratis:

1. **Cobertura combinatoria.** `.epub → .png` no lo hace ningún motor solo, pero `calibre: epub→pdf` + `vips: pdf→png` sí. Cada motor nuevo multiplica la cobertura en vez de sumarla.
2. **Prioridad correcta por construcción.** El coste de la arista (velocidad, fidelidad, si usa GPU) elige el motor. Es exactamente el bug que ConvertX tiene por resolverlo con un bucle.
3. **Degradación explicable.** Si no hay camino, se puede decir *por qué* — dato valioso cuando quien pregunta es un agente vía MCP.

Es el diferenciador más barato de construir de los tres detectados (los otros dos: GPU y MCP), porque es puramente algorítmico: no añade dependencias ni motores nuevos.

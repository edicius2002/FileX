# ConvertX — `C4illin/ConvertX`

18.5k ⭐ · AGPL-3.0 · TypeScript/Bun+Elysia · 8 commits en 30 días · analizado sobre clon del 2026-08-19

**Veredicto: copiar el mapa de motores, descartar la arquitectura de despacho.**

## 1. Qué resuelve y qué no
Servidor web self-hosted que convierte subiendo ficheros por navegador. Anuncia "1000+ formatos", cifra que sale de sumar las tablas `from`/`to` de 20 adaptadores. No hace OCR, no transcribe, no usa GPU, no tiene CLI ni MCP.

## 2. Arquitectura
`src/converters/main.ts` (350 líneas) es un `Record` con 20 entradas, cada una `{properties, converter}`, importadas de forma estática. Cada adaptador declara su matriz de formatos y expone `convert(filePath, fileType, convertTo, targetPath, options)`.

El propio autor dejó escrito en `main.ts:28`:
> *"This should probably be reconstructed so that the functions are not imported instead the functions hook into this to make the converters more modular"*

**Despacho de un solo salto.** No existe encadenamiento: si ningún motor hace `A→B` directo, devuelve `"File type not supported"`. Búsquedas de `chain|graph|bfs|intermediate` en todo `src/`: cero resultados reales. Un `.docx → .png` solo funciona si un único motor cubre ambos extremos.

### ⚠️ Defecto de selección confirmado (`main.ts:213-229`)
```js
for (converterName in properties) {          // 213 — bucle EXTERNO
  for (const key in converterObj.properties.from) {
    if (from.includes(fileType) && to.includes(convertTo)) {
      converterFunc = converterObj.converter;
      break;                                  // 226 — rompe SOLO el interno
    }
  }
}                                             // el externo nunca se corta
```
El `break` no sale del bucle externo, así que **gana el último conversor que coincide, no el primero**. Consecuencias verificadas:

- El orden del `Record` es prioridad *declarada* (inkscape #1 … markitDown #20) pero actúa como **prioridad inversa**. El comentario "Prioritize Inkscape for EMF files" del código es inoperante.
- Para `png→jpg` coinciden vips(#4), imagemagick(#13), graphicsmagick(#14) y **ffmpeg(#16), que es el que gana** — el peor de los cuatro para imagen fija.
- `converterName` es la variable del `for...in`, así que al terminar vale **la última clave del Record**, no la del motor elegido. El log `"...using ${converterName}"` reporta casi siempre `markitDown`. El registro de ejecución es poco fiable.

**Lección para FileX:** el registro debe ser un **grafo dirigido con coste por arista** y búsqueda de camino mínimo (habilita multi-salto *y* prioridad correcta), no una lista con lookup lineal.

## 3. Frontera de proceso
`execFile` de `node:child_process` en todos los adaptadores — **sin shell**, argumentos como array. Inmune a inyección de shell y **sin contaminación GPL**: ffmpeg, LibreOffice, Calibre e ImageMagick se invocan como procesos externos. Es el patrón correcto y FileX debe conservarlo.

## 4. GPU
**Ninguna.** `grep` de `nvenc`/`cuda`: 0 coincidencias. Con ffmpeg ya integrado, añadir `h264_nvenc` sería trivial y nadie lo ha hecho. Este es el hueco competitivo.

## 5. Extensibilidad
Añadir un motor = crear `src/converters/x.ts` + 2 líneas de import + 1 entrada en el `Record` de `main.ts`. Barato, pero **requiere recompilar**: no hay carga dinámica ni plugins de terceros.

## 6. Seguridad
A favor: `execFile` sin shell; `MAX_CONVERT_PROCESS` limita concurrencia. En contra: el troceado (`chunks()`, `main.ts:142-163`) es por lotes, no un pool real — un fichero lento bloquea todo su lote; sin timeout por conversión ni límites de memoria/disco por trabajo.

## 7. Licencia
**AGPL-3.0.** Usar su código obliga a publicar FileX como AGPL, incluso ofreciéndolo solo por red. Su *lista de motores* (qué binario cubre qué formato) no es código y sí es reutilizable.

## 8. Salud
8 commits/30d — vivo pero lento. Un mantenedor principal: bus factor 1.

## 9. Qué extraer para FileX
1. **La tabla de motores**: inkscape, libjxl, resvg, vips, libheif, xelatex, calibre, dasel, libreoffice, pandoc, msgconvert, dvisvgm, imagemagick, graphicsmagick, assimp, ffmpeg, potrace, vtracer, vcf, markitdown. Es el consenso del sector sobre qué binario usar para cada familia.
2. **Las matrices `from`/`to`** de cada adaptador: años de conocimiento acumulado sobre extensiones reales.
3. **El patrón `execFile` sin shell** como frontera de proceso.
4. **Qué NO copiar**: el despacho lineal de un salto, y su bug de prioridad.

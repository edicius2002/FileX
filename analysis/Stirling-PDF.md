# Stirling-PDF — `Stirling-Tools/Stirling-PDF`

89.9k ⭐ · **MIT con excepciones propietarias** · Java/Spring · ~571k líneas · 100+ commits/30d

**Veredicto: no es base (es solo PDF y es Java), pero su MCP es la señal estratégica más importante de toda la investigación.**

## ⚠️ Corrección sobre los metadatos de GitHub
La API de GitHub reporta `NOASSERTION` y ninguna señal de MCP. **Ambas cosas son engañosas.** Leyendo el repositorio:

- El `LICENSE` raíz es **MIT**, seguido de *"Portions of this software are licensed as follows"*, con **10 directorios excluidos**: `app/proprietary/`, `app/saas/`, `engine/`, y siete rutas de `frontend/editor/src/`.
- `app/proprietary/LICENSE` es la **"Stirling PDF User License"**: *"Production use of the Stirling PDF Software is only permitted with a valid Stirling PDF User License."* Uso libre solo para evaluación o "minimal use".

## El dato que cambia el análisis: su MCP existe y es de pago
`app/proprietary/src/main/java/stirling/software/proprietary/mcp/` contiene un servidor MCP completo:

| Fichero | Función |
|---|---|
| `catalog/McpToolCatalog.java` | Descubre las operaciones y las publica como herramientas |
| `tools/McpOperationExecutor.java` | Ejecuta la operación solicitada |
| `tools/DescribeOperationTool.java` | Introspección de operaciones |
| `security/McpApiKeyAuthFilter.java` | Autenticación por clave de API |
| `security/McpConfigValidator.java`, `McpSecurityConfig.java` | Configuración y validación de seguridad |

**El líder del mercado (89.9k ⭐) ya construyó MCP para operaciones de ficheros y lo puso detrás de una suscripción.** Eso reformula el hueco: no es que nadie lo haya pensado — es que **quien lo pensó lo está monetizando**. Valida que el ángulo vale dinero, y advierte de que la ventana no es infinita.

## La idea técnica que merece copiarse
`McpToolCatalog` **no declara las herramientas a mano**: escanea los beans `RequestMappingHandlerMapping` de Spring y convierte los endpoints REST existentes en herramientas MCP:

```java
log.info("MCP tool catalog discovered {} PDF operation(s)", pdfOps.size());
// "Only POST/PUT endpoints are exposed as tools; DELETE and GET are excluded."
```
Más: un ámbito `mcp.tools.write` para separar lectura de escritura, y listas de permitidos/bloqueados administrables.

**Para FileX:** el catálogo MCP debe **generarse desde el registro de conversores**, no escribirse a mano. Un motor nuevo aparece como herramienta sin tocar la capa MCP. Combinado con el grafo de conversión, el servidor MCP es casi gratis.

## GPU
Cero. 571k líneas de Java y ni una llamada a CUDA o NVENC. Su OCR delega en OCRmyPDF/Tesseract, en CPU.

## Qué extraer
1. **Generación automática del catálogo MCP** desde el registro de operaciones.
2. **La separación lectura/escritura por ámbitos** y la exclusión de verbos destructivos.
3. **La lección de negocio**: el troceado MIT-con-excepciones les permite tener 89.9k ⭐ de comunidad y cobrar por MCP, SaaS y escritorio. Es el modelo que FileX podría imitar si algún día se comercializa.
4. **Qué no copiar**: Java/Spring para un CLI. El arranque de una JVM es incompatible con una herramienta que un agente invoca cientos de veces.

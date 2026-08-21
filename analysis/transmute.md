# transmute — `transmute-app/transmute`

1.3k ⭐ · **MIT** · Python (FastAPI) + frontend + k8s · 22.2k líneas Python en 132 ficheros · 15 commits/30d

**Veredicto: la mejor base reutilizable del conjunto. Es el único candidato con licencia permisiva Y arquitectura sana.**

## 1. Qué resuelve
Conversor y compresor self-hosted: imágenes, vídeo, audio, JSON, Excel "y más". Menos ambicioso que SnapOtter, mucho mejor estructurado que ConvertX.

## 2. Arquitectura — registro por auto-descubrimiento
`backend/` separa `converters/`, `compressors/`, `downloaders/`, `registry/`, `background/` (colas), `api/routes/`, `db/`, `tests/`.

`registry/registry.py` **descubre los conversores por reflexión**, no por imports hardcodeados:
```python
for _name, obj in inspect.getmembers(converters, inspect.isclass):
    if issubclass(obj, ConverterInterface) and obj is not ConverterInterface:
        if skip_unregisterable and not obj.can_register():
            continue          # ← el binario no está instalado: no se registra
        self.register_converter(obj)
```
Dos aciertos que ConvertX no tiene:
- **`can_register()`**: un conversor cuyo binario falta se auto-excluye. Degradación elegante en vez de fallo en tiempo de ejecución.
- **`_get_preferred_converter()`** (`registry.py:209`): resolución *explícita* de preferencia cuando varios motores cubren el mismo par. ConvertX resuelve esto por accidente, y mal.

`ConverterInterface` declara `supported_input_formats` / `supported_output_formats` como atributos de clase y expone `can_convert()`, `get_quality_options()`, `convert(overwrite, quality)`. Interfaz limpia y copiable tal cual.

## 3. Cobertura — 24 conversores, varios únicos
`archive`, `calibre`, `cbz`, `drawio`, `email`, `ezdxf` (DXF/CAD), `ffmpeg`, `fonttools` (**fuentes**), `inkscape`, `libreoffice`, `mesh_render`, `ocrmypdf`, `pandas` (**tabulares**), `pdf2docx`, `pillow`, `pkcs7`, `pymupdf`, `pypandoc`, `pysubs2` (**subtítulos**), `rename`, `tgs`, `trimesh`.

Cubre nichos que ConvertX no toca: fuentes tipográficas, subtítulos, correo electrónico, datos tabulares vía pandas y diagramas draw.io.

## 4. Limitaciones
- **Sin GPU.** Cero coincidencias de `cuda`/`nvenc`/`torch`.
- **Sin MCP, sin CLI, sin watcher.** Es una API web con frontend.
- **Un solo salto**, igual que todos: `get_converter_for_conversion(input, output)` devuelve un conversor o nada.
- Comunidad pequeña (1.3k ⭐, 15 commits/30d): menos validación en producción que ConvertX o SnapOtter.

## 5. Licencia — la ventaja decisiva
**MIT.** Copyright 2026 Chase Roohms. Se puede copiar, modificar, cerrar y vender sin obligación de publicar nada. Es **el único orquestador del conjunto que permite todos los escenarios de negocio**; los demás son AGPL-3.0.

## 6. Qué extraer para FileX
1. **El registro por reflexión con `can_register()`** — el patrón correcto, ya escrito y probado, y bajo MIT.
2. **`ConverterInterface`** como contrato base.
3. **Los adaptadores de nicho** (`fonttools`, `pysubs2`, `pandas`, `email`, `ezdxf`): trabajo hecho y legalmente reutilizable.
4. **La separación conversor/compresor/descargador**: comprimir no es convertir, y mezclarlos ensucia el modelo.

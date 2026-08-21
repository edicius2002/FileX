# Gotenberg — `gotenberg/gotenberg`
12.9k estrellas · **MIT** · Go · 38.4k líneas

**Veredicto: no es base, es una dependencia candidata. Su arquitectura modular sí merece copiarse.**

API HTTP que convierte a PDF orquestando binarios en un contenedor. `pkg/modules/` es una lista de módulos independientes:
`api`, `chromium`, `exiftool`, `libreoffice`, `pdfcpu`, `pdfengines`, `pdftk`, `prometheus`, `qpdf`, `webhook`.

**Lo bueno:** cada motor es un módulo aislado con su ciclo de vida propio; incluye `prometheus` (métricas) y `webhook` (asincronía) como módulos de primera clase, no como añadidos. Mantiene **LibreOffice residente** en lugar de arrancarlo por petición — justo la estrategia que recomiendan las mediciones de arranque en frío de `bench/results.md`.

**Uso recomendado en FileX:** en lugar de pelearse con la instalación de LibreOffice en Windows, levantar Gotenberg en Docker y usarlo como motor de ofimática a PDF. Es MIT, así que no impone nada.

**Nota de clonado:** falló con `--depth 1` por el límite de rutas de Windows (un fichero de prueba en sueco con nombre larguísimo). Se resolvió con `git -c core.longpaths=true clone`.

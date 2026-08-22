# OCRmyPDF — `ocrmypdf/OCRmyPDF`
34.5k estrellas · **MPL-2.0** · Python · 41.1k líneas

> ⚠️ **Veredicto revocado el 21/08/2026 tras ejecutarlo.** Lo que sigue es el análisis de código original; su
> conclusión sobre el preprocesado **quedó refutada al medirlo**. Ver el aviso al final y `bench/ocrmypdf.md`.

**Veredicto (original, de lectura de código): usar como referencia de calidad y como ruta de compatibilidad, no como motor principal de OCR.**

El estándar de facto para añadir capa de texto a PDF escaneados. Delega en **Tesseract**, es decir, **CPU pura**: 0 ficheros con CUDA en 41k líneas.

Su verdadero valor no es el OCR sino todo lo que lo rodea: rotación automática, corrección de inclinación, eliminación de ruido, optimización del PDF resultante y preservación del original. Ese trabajo de fontanería es exactamente lo que exige el caso `corpus/pdf/patologico_escaneado.pdf`, inclinado 1,7 grados, con ruido gaussiano y sin capa de texto.

**MPL-2.0** es copyleft *por fichero*: se puede combinar con código propietario siempre que se publiquen los ficheros MPL modificados. Mucho más permisivo que AGPL.

**Papel en FileX (original):** ruta por defecto para PDF escaneado a PDF buscable, por ser compatible y estar probada, con Surya en GPU como ruta de alta calidad y velocidad. Su preprocesado de imagen es la referencia a imitar.

---

## Revocación — MEDIDO (21/08/2026)

**«Su preprocesado de imagen es la referencia a imitar» es falso.** Se ejecutó en WSL2 (ocrmypdf 16.13, tesseract 5.5, unpaper 7.0; cierre de dependencias 502 MB) y **su preprocesado no hace nada**. Comprobado pixel a pixel con `magick compare`: `--deskew`, `--clean-final` y `--rotate-pages` producen una imagen de salida **bit a bit idéntica** a no usarlas, en las tres variantes degradadas.

| Bandera | Qué hace realmente |
|---|---|
| `--remove-background` | `NotImplementedError: temporarily not implemented` (rc=15), en las 4 variantes |
| `--deskew` | Delega en `tesseract --psm 2`, que devuelve `Deskew angle: 0.0000` **incluso sobre una página sintética nítida girada 5° exactos**. Es inerte siempre |
| `--clean-final` | Invoca unpaper con `--no-grayfilter --no-blackfilter --no-deskew`; activarlos a mano **destruye** el texto (d2: 30,4 % → 100 % CER) |

Y **degrada**: atravesar su ciclo rasterizar→JPEG→PDF/A lleva a RapidOCR en dificultad 2 de **1,3 % a 44,3 % de CER**. Coste: `--rotate-pages` 4.645 ms y el paquete completo 5.914 ms **sin cambiar un solo píxel**, frente a 1.480 ms del caso base.

**Papel vigente en FileX: ninguno.** No entra como motor (100 % de CER en dificultad 3, sidecar vacío) ni como preprocesador. Solo tendría sentido como empaquetador de PDF/A buscable, y ahí no toca ningún hueco competitivo.

**Lo que sí salió de intentarlo** es el hallazgo que reabre el hueco 5, y no tiene que ver con OCRmyPDF: el arnés de la fase 2 **rasterizaba a 200 ppp unos PDF cuya imagen incrustada es de 100 ppp**. A ppp nativos, PaddleOCR resuelve la dificultad 3 con **2,5 % de CER**. La conclusión de arquitectura no es «añadir una etapa de preprocesado» sino **leer los ppp de la imagen incrustada y no sobremuestrear** — una decisión, no una etapa, y más barata que lo que se hacía.

**Nota sobre Tesseract:** OCRmyPDF necesita el binario real y **no puede aprovechar** el Tesseract embebido en Ghostscript 10.07. Ver `PLAN-ORQUESTADOR.md` §2.

# OCRmyPDF — `ocrmypdf/OCRmyPDF`
34.5k estrellas · **MPL-2.0** · Python · 41.1k líneas

**Veredicto: usar como referencia de calidad y como ruta de compatibilidad, no como motor principal de OCR.**

El estándar de facto para añadir capa de texto a PDF escaneados. Delega en **Tesseract**, es decir, **CPU pura**: 0 ficheros con CUDA en 41k líneas.

Su verdadero valor no es el OCR sino todo lo que lo rodea: rotación automática, corrección de inclinación, eliminación de ruido, optimización del PDF resultante y preservación del original. Ese trabajo de fontanería es exactamente lo que exige el caso `corpus/pdf/patologico_escaneado.pdf`, inclinado 1,7 grados, con ruido gaussiano y sin capa de texto.

**MPL-2.0** es copyleft *por fichero*: se puede combinar con código propietario siempre que se publiquen los ficheros MPL modificados. Mucho más permisivo que AGPL.

**Papel en FileX:** ruta por defecto para PDF escaneado a PDF buscable, por ser compatible y estar probada, con Surya en GPU como ruta de alta calidad y velocidad. Su preprocesado de imagen es la referencia a imitar.

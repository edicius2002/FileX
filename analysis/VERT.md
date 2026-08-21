# VERT — `VERT-sh/VERT`
15.4k estrellas · AGPL-3.0 · Svelte · 10.6k líneas · **1 commit/30d (moribundo)**

**Veredicto: descartar como base. Valioso solo como demostración de los límites del enfoque WASM.**

Convierte **en el navegador**, sin servidor: `@ffmpeg/ffmpeg` (ffmpeg.wasm), `@imagemagick/magick-wasm` y `vert-wasm`. Privacidad perfecta — el fichero nunca sale del equipo — e instalación cero.

**Los límites son estructurales, no de implementación:**
- **Ni un ápice de GPU es posible.** WASM no accede a NVENC ni a CUDA. En la 3060, VERT es varias veces más lento que un ffmpeg nativo para el mismo trabajo.
- Sin LibreOffice ni Calibre: la ofimática y los ebooks quedan fuera del alcance de WASM.
- Límite de memoria del navegador: el TIFF de 72 MB del corpus es problemático.

Con 15.4k estrellas y 1 commit/mes, el proyecto está efectivamente parado. **Lección para FileX:** local-first no exige el navegador; un binario nativo da la misma privacidad sin renunciar a la GPU.

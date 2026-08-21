# faster-whisper — `SYSTRAN/faster-whisper`
25k estrellas · **MIT** · Python · 4k líneas

**Veredicto: adoptar tal cual para audio y vídeo a texto. Decisión sin discusión.**

Whisper reimplementado sobre CTranslate2. 4k líneas: un envoltorio delgado y bien hecho sobre un runtime en C++.

`faster_whisper/utils.py` lista los modelos, incluidos **`large-v3`** y los destilados **`distil-large-v3`** y `distil-large-v2`, notablemente más rápidos con pérdida mínima de calidad.

**En la 3060:** `large-v3` en `float16` ocupa alrededor de 5 GB de VRAM. Cabe con holgura en 12 GB, dejando sitio para que Surya coexista.

Detalle competitivo: **SnapOtter empaqueta solo `faster-whisper-small`** (`packages/ai/python/transcribe.py`) para no inflar su imagen Docker. FileX, al ser local, no tiene esa restricción y puede ofrecer `large-v3` desde el primer día. Es una ventaja de calidad gratuita.

Selección de dispositivo idéntica a la de SnapOtter: `cuda` con `float16` si hay GPU, `cpu` con `int8` si no. Buen patrón de degradación, copiable.

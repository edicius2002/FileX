# Surya y Marker — `datalab-to/surya` y `datalab-to/marker`
Surya: 21.3k estrellas · Apache-2.0 · 13.5k líneas · 15 ficheros CUDA
Marker: 38.9k estrellas · Apache-2.0 · 16.5k líneas · 7 ficheros CUDA

**Veredicto: Surya es la pieza que materializa la ventaja competitiva de FileX, porque hace OCR en GPU justo donde SnapOtter renuncia.**

**Surya** hace OCR, análisis de maquetación, orden de lectura y reconocimiento de tablas en más de 90 idiomas. **Marker** es la capa PDF a Markdown construida sobre Surya.

### El dato que importa para tu hardware
`surya/settings.py:100-102`:
```python
# bfloat16 needs an Ampere+ GPU (compute capability >= 8.0). On older cards
# (e.g. T4 / Turing) vllm refuses to start with bf16 -- set float16 there.
VLLM_DTYPE: str = "bfloat16"
```
**Tu RTX 3060 es compute capability 8.6**, verificado con `nvidia-smi --query-gpu=compute_cap`. Cumple el requisito: entra por el camino rápido de bfloat16, no por el de compatibilidad. Los tamaños de lote son configurables (`DETECTOR_BATCH_SIZE`, `FAST_LAYOUT_BATCH_SIZE`) para ajustarse a 12 GB.

Marker autodetecta el dispositivo: `TORCH_DEVICE_MODEL` devuelve `cuda` si `torch.cuda.is_available()`.

**Ambos Apache-2.0**, sin obligaciones de copyleft. Aviso: los *pesos de los modelos* pueden llevar licencia propia. Verificar en Hugging Face antes de cualquier uso comercial, porque código y pesos se licencian por separado.

**Posición en FileX:** Surya y Marker en GPU son la respuesta directa al candado `device !== "cpu"` de SnapOtter. Es la ventaja más defendible detectada en toda la investigación.

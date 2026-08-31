# B21 + B22 — suelo y barrido de 100–150 ppp

## Estado

**PENDIENTE — no hay una cifra publicable aún.** La primera ejecución se detuvo y se
descartó antes de terminar: el lector de `REFERENCIA-d5.txt` incluía la sección
documental `[cadena plana que usa el evaluador]`, duplicando el texto de referencia.
La referencia correcta tiene 610 caracteres de origen y 596 tras la normalización
canónica acentuada. No se usan las salidas de esa ejecución.

## Arnés corregido para el reintento

- Salida y programa: `bench/salidas-suelo-ppp/b21b22.py`.
- Métrica declarada por celda: `acentos` (canónica); también guarda `cer_ciego_pct`.
- Dispositivo: GPU `cuda:0` para RapidOCR/PaddleOCR/EasyOCR/Docling; Tesseract CPU.
- Entrada: ruta de PNG RGB (no ndarray) para los motores de imagen; Docling recibe PDF
  con `OcrOptions.scale` explícito.
- Rasterizador: ImageMagick, `-units PixelsPerInch -density N`; `identify` de cada PNG
  queda en la fila, incluido pHYs.
- Cada celda prevista es mediana de n=9, con vector de rc, determinismo y tiempos.
- El orden de páginas es d5a, d5c, d5, d5b (mayor a menor) y toda ejecución GPU toma
  `gpu_acquire`/`gpu_release` desde Git Bash.

## B21

**PENDIENTE.** Falta medir, para las siete configuraciones no-Tesseract, cada nativo
(90, 80, 72 y 60 ppp) frente a 100 ppp con el arnés corregido.

## B22

**PENDIENTE.** Falta el barrido fino 100–150 ppp, n=9, de las siete configuraciones y
Tesseract `--psm 3` / `--psm 11`.

## Bloqueo resuelto

El lock de la tanda descartada quedó huérfano tras detener su proceso; Git Bash lo
detectó por PID de Windows, lo liberó y una adquisición/liberación de comprobación
terminó correctamente. No queda proceso de medición ni lock activo.

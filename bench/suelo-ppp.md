# B21 + B22 — suelo y barrido de 100–150 ppp

## Estado y condiciones de medida

**MEDIDO:** 336 celdas limpias: siete configuraciones no-Tesseract × cuatro
documentos × (nativo y 100–150 ppp) × mediana n=9. Cada fila JSON declara `metrica:
acentos`, vector `rc`, dispositivo, entrada, píxeles y pHYs. La referencia se toma de
`d4_texto.BLOQUES`: 610 caracteres de origen y 596 tras normalización acentuada.

Los adaptadores de imagen recibieron `ndarray` BGR de tres canales; Docling recibió PDF
con escala explícita. GPU `cuda:0`, orden d5a→d5c→d5→d5b y lock fichero+mutex por
configuración. Los PNG regenerables y sus SHA-256 constan en `salidas-suelo-ppp/MANIFIESTO.md`.

## B21 — el suelo de 100 ppp es del motor, no global

**MEDIDO, siete configuraciones.** Se compara CER a 100 ppp menos CER al ppp nativo;
positivo empeora. ±0,16 puntos es la cuantización de la referencia, por lo que se marca
igual cuando no hay señal por encima de ella.

| Configuración | Peor / mejor / igual | Diferencias por documento d5a, d5c, d5, d5b (pp) |
|---|---:|---|
| RapidOCR v5 defecto | 4 / 0 / 0 | +0,7; +9,1; +4,4; +9,6 |
| RapidOCR v6 defecto | 4 / 0 / 0 | +0,7; +0,2; +0,2; +9,1 |
| RapidOCR v6 +R6 | 3 / 0 / 1 | +0,7; +17,8; −0,1; +8,9 |
| Docling + RapidOCR torch defecto | 2 / 1 / 1 | 0,0; +0,4; −2,2; +7,2 |
| PaddleOCR v6 medium | 1 / 1 / 2 | 0,0; +0,5; −0,3; +0,1 |
| EasyOCR CRAFT + latin_g2 | 0 / 3 / 1 | −2,3; +0,1; −1,1; −4,6 |
| Docling + RapidOCR torch +R6 | 0 / 4 / 0 | −9,0; −17,9; −9,4; −7,0 |

**Arrepentimiento MEDIDO:** mi conclusión inicial, «el suelo no se sostiene», generalizaba
desde RapidOCR. Es falsa como regla global. RapidOCR aporta 11 peor y 0 mejor; EasyOCR y
Docling +R6 aportan 7 mejor y 0 peor. El saldo global (14 peor / 9 mejor / 5 igual) es un
empate engañoso: la media destruye la interacción motor×documento. El ejemplo más claro es
d5c: 100 ppp cuesta +17,8 puntos en RapidOCR v6 +R6 y gana −17,9 en Docling +R6.

## B22 — la curva no es suave

**MEDIDO, siete configuraciones, n=9.** No hay un óptimo global cercano a 125 ppp. En
RapidOCR v6 +R6, d5c pasa de 0,7 % a 80 ppp a 18,5 % a 100, 9,7 % a 120, 0,8 % a 125,
0,3 % a 130 y 5,0 % a 135. Las salidas son deterministas: son picos aislados de detección,
no ruido. Elegir un ppp sin conocer esos picos es una lotería.

**Refutación MEDIDA de mi hipótesis de tamaño efectivo:** el detector sí usa mínimo 736 y
redondea a múltiplos de 32, pero no explica los picos. d5a y d5c a 100 ppp aterrizan ambos
en 736×1024 y dan respectivamente 1,0 % y 18,5 %. El pico pertenece al par
documento×ppp, no al tamaño efectivo. La siguiente sonda útil son las cajas detectadas.

**MEDIDO:** d5b no es una curva de picos: en RapidOCR v6 +R6 permanece entre 3,5 y 24,3 %.
Es un régimen persistentemente malo y no debe entrar en un recuento de picos con umbral fijo.

**PENDIENTE:** Tesseract psm 3 y psm 11 no forman parte de estas 336 celdas; B22 para esos
dos controles todavía no se ha medido.

## Operación e integración

**MEDIDO:** desprender una tarea salva la tarea, no la secuencia. Con el bucle entre
configuraciones dentro de un turno, el barrido se detuvo 40 minutos tras cada relevo. Un
conductor único, desprendido, con Python reiniciado y lock tomado/liberado por configuración,
cerró las restantes sin retener GPU innecesariamente.

**MEDIDO:** cuatro configuraciones lanzadas desde WSL fallaron por entorno. Paddle falló
ruidosamente con `WinError 1` en `filelock` y EasyOCR con `UnicodeEncodeError` de `█`;
ambas rc=1. Docling falló silenciosamente: rc de proceso 0, pero las 48 celdas de cada
configuración tenían rc=1, texto vacío y CER 100 %, por `FileNotFoundError` hacia
`\\wsl.localhost`. `expanduser('~')` en Windows toma `USERPROFILE`, que estaba heredado a
UNC. Con `USERPROFILE`/`HOME` locales de Windows y `PYTHONUTF8=1`, las cuatro relanzadas
cerraron correctamente.

**Regla propuesta, PENDIENTE de implementar:** una configuración con 100 % de celdas a CER
100 % se marca corrida fallida hasta inspeccionar su rc por celda y sus textos; no se publica
como resultado. El rc del proceso no distingue «no leyó nada» de «no se ejecutó».

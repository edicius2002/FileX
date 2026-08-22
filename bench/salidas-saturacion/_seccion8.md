1. **La temperatura no está fijada y no se puede fijar.** El CLI de Claude Code no la expone. Las
   repeticiones miden la variabilidad real del sujeto tal como FileX se lo va a encontrar, no la de
   un parámetro controlado. **Es la limitación más seria del instrumento.** Con una clave de API se
   arreglaría en una tarde: el diseño de §2 se ejecuta igual contra la API, fijando `temperature` y
   declarándola. **PENDIENTE.**

2. **Dos modelos, y de la misma familia.** Haiku 4.5 y Sonnet 4.5. El resultado se replica en los
   dos, lo que descarta que sea un artefacto de un modelo, pero **no dice nada de modelos de otras
   familias ni de modelos pequeños locales**, que es un escenario que FileX contempla. **PENDIENTE.**

3. **Un solo dominio, doce peticiones.** Multimedia. Las conclusiones son sobre catálogos de
   conversión de vídeo y audio. **PENDIENTE** replicarlo en el dominio documental
   (`docling-mcp`, 19 herramientas).

4. **El criterio de «mejor herramienta» es un juicio.** `E4b` lo demuestra: mi clave declaraba
   `set_video_bitrate` y el modelo eligió algo al menos igual de bueno. Por eso el informe da
   **siempre las dos métricas** y hace el análisis de sensibilidad de §3.4. **La métrica permisiva
   —«eligió una herramienta que resuelve la tarea»— es la robusta, y es la que sostiene el
   veredicto.**

5. **Los catálogos no son perfectamente pareables.** `video-audio-mcp` no extrae fotogramas;
   `ffmpeg-mcp-lite` no fija el bitrate de la pista de audio de un vídeo. Se declaró **antes de
   medir** (§2.4) que en esos casos la abstención es el acierto, lo que convierte el desajuste en
   una medida útil en lugar de un defecto. Aun así, **las tareas `E2d`, `E4a` y `E4c` no son
   comparaciones de elección entre catálogos equivalentes**, y así están marcadas.

6. **El servidor es un stub.** Sirve los catálogos exactos y registra las llamadas, pero no ejecuta
   ffmpeg. Eso es correcto para medir la **elección** —que es lo que se pedía— y era además la única
   forma de hacerlo sin el deadlock de `video-audio-mcp`. **No sirve** para medir recuperación de
   errores ni corrección real de los ficheros. **PENDIENTE.**

7. **Potencia estadística.** n = 120 por celda en Haiku, 60 en Sonnet. Detecta caídas de ~7 puntos
   desde el 100 %; **no** detecta caídas de 2–3 puntos. Las afirmaciones de «no hay diferencia» son
   **«no se detectó diferencia con esta potencia»**, no «no hay».

8. **Un fallo del arnés, documentado.** La ejecución de Haiku murió en la iteración 274 de 360 con
   `FileNotFoundError: [WinError 2]` al crear el proceso hijo, con 5 hilos concurrentes. Se relanzó
   con 3 hilos y terminó sin incidencias; `correr.py` es reanudable y no repitió ninguna celda.
   Las 360 filas están completas y ninguna tiene `rc != 0`.

# MinerU — `opendatalab/MinerU`
78k estrellas · **Apache-2.0 con términos adicionales** · Python · 71.6k líneas · 15 ficheros CUDA

**Veredicto: la licencia resulta ser inofensiva; el peso del proyecto es el verdadero inconveniente.**

Convierte PDF y ofimática compleja a Markdown y JSON para flujos con agentes. Excelente en documentos difíciles: artículos científicos a dos columnas, fórmulas, tablas anidadas.

### Licencia: riesgo descartado tras leerla
La API de GitHub reporta `NOASSERTION`, que en el plan se marcó como riesgo a verificar. `LICENSE.md` aclara que es **Apache-2.0 más términos adicionales**:

1. **Licencia comercial obligatoria solo por encima de 100 millones de usuarios activos mensuales o 20 millones de dólares de ingresos mensuales.** Irrelevante en la práctica.
2. **Atribución obligatoria** si se ofrece un servicio online basado en MinerU.
3. Terminación automática de la licencia si se incumple 1 o 2.

En la práctica es **utilizable sin problema**, con la única obligación de citar a MinerU si FileX llegara a ofrecerse como servicio en línea.

### El inconveniente real
71.6k líneas y una pila de modelos pesada. Frente a Docling (MIT, modular, con `docling-serve` ya listo) o Marker (Apache-2.0, 16.5k líneas), MinerU aporta calidad marginal a cambio de una complejidad de despliegue considerable.

**Recomendación:** no incluirlo en la primera versión. Reservarlo como motor de máxima calidad, activable bajo demanda, si Docling y Marker se quedan cortos en documentos científicos.

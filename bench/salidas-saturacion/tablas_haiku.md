## Modelo: Haiku 4.5 — n = 360 ejecuciones

### Global

| Catálogo | n | Acierto estricto (IC 95 %) | Acierto permisivo | Petición cumplida entera | Elección trampa |
|---|---:|---:|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 120 | **93 %** [0.87–0.97] | 100 % | 92 % | 0 % |
| C · 14 herr. · 4.749 tok | 120 | **100 %** [0.97–1.00] | 100 % | 92 % | 0 % |
| B · 8 herr. · 2.306 tok | 120 | **82 %** [0.74–0.88] | 85 % | 86 % | 15 % |

### Estrato 1 · inequívocas (control)

| Catálogo | n | Acierto estricto (IC 95 %) | Acierto permisivo | Petición cumplida entera | Elección trampa |
|---|---:|---:|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 30 | **100 %** [0.89–1.00] | 100 % | 100 % | 0 % |
| C · 14 herr. · 4.749 tok | 30 | **100 %** [0.89–1.00] | 100 % | 100 % | 0 % |
| B · 8 herr. · 2.306 tok | 30 | **100 %** [0.89–1.00] | 100 % | 100 % | 0 % |

### Estrato 2 · ambiguas con pista

| Catálogo | n | Acierto estricto (IC 95 %) | Acierto permisivo | Petición cumplida entera | Elección trampa |
|---|---:|---:|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 40 | **100 %** [0.91–1.00] | 100 % | 100 % | 0 % |
| C · 14 herr. · 4.749 tok | 40 | **100 %** [0.91–1.00] | 100 % | 100 % | 0 % |
| B · 8 herr. · 2.306 tok | 40 | **70 %** [0.55–0.82] | 78 % | 75 % | 22 % |

### Estrato 3 · encadenadas

| Catálogo | n | Acierto estricto (IC 95 %) | Acierto permisivo | Petición cumplida entera | Elección trampa |
|---|---:|---:|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 20 | **100 %** [0.84–1.00] | 100 % | 100 % | 0 % |
| C · 14 herr. · 4.749 tok | 20 | **100 %** [0.84–1.00] | 100 % | 100 % | 0 % |
| B · 8 herr. · 2.306 tok | 20 | **95 %** [0.76–0.99] | 100 % | 100 % | 0 % |

### Estrato 4 · ambiguas sin pista

| Catálogo | n | Acierto estricto (IC 95 %) | Acierto permisivo | Petición cumplida entera | Elección trampa |
|---|---:|---:|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 30 | **73 %** [0.56–0.86] | 100 % | 67 % | 0 % |
| C · 14 herr. · 4.749 tok | 30 | **100 %** [0.89–1.00] | 100 % | 67 % | 0 % |
| B · 8 herr. · 2.306 tok | 30 | **70 %** [0.52–0.83] | 70 % | 77 % | 30 % |

### Por tarea (acierto estricto)

| Tarea | Estrato | A (27) | C (14) | B (8) |
|---|---:|---:|---:|---:|
| E1a | 1 | 100 % | 100 % | 100 % |
| E1b | 1 | 100 % | 100 % | 100 % |
| E1c | 1 | 100 % | 100 % | 100 % |
| E2a | 2 | 100 % | 100 % | 70 % |
| E2b | 2 | 100 % | 100 % | 100 % |
| E2c | 2 | 100 % | 100 % | 100 % |
| E2d | 2 | 100 % | 100 % | 10 % |
| E3a | 3 | 100 % | 100 % | 100 % |
| E3b | 3 | 100 % | 100 % | 90 % |
| E4a | 4 | 100 % | 100 % | 10 % |
| E4b | 4 | 20 % | 100 % | 100 % |
| E4c | 4 | 100 % | 100 % | 100 % |

### Contrastes (Fisher exacto bilateral)

| Métrica | A (27) | C (14) | p (A vs C) | B (8) | p (A vs B) |
|---|---:|---:|---:|---:|---:|
| acierto estricto | 93 % | 100 % | 0.007 **\*** | 82 % | 0.010 **\*** |
| acierto permisivo | 100 % | 100 % | 1.000 | 85 % | 0.000 **\*** |
| petición cumplida entera | 92 % | 92 % | 1.000 | 86 % | 0.220 |
| elección trampa | 0 % | 0 % | 1.000 | 15 % | 0.000 **\*** |

### Coste de la decisión (no de la conversión)

| Catálogo | Coste medio USD/petición | Latencia media | Llamadas sustantivas medias |
|---|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 0.0066 | 12.2 s | 1.08 |
| C · 14 herr. · 4.749 tok | 0.0065 | 12.1 s | 1.08 |
| B · 8 herr. · 2.306 tok | 0.0168 | 18.1 s | 1.17 |

### Distribución de clases

| Catálogo | abstencion | incompleta | mejor | resuelve | secuencia_exacta | trampa |
|---|---|---|---|---|---|---|
| A · 27 herr. · 7.886 tok | 10 | 0 | 82 | 8 | 20 | 0 |
| C · 14 herr. · 4.749 tok | 10 | 0 | 90 | 0 | 20 | 0 |
| B · 8 herr. · 2.306 tok | 2 | 1 | 77 | 3 | 19 | 18 |

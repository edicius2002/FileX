## Modelo: Sonnet 4.5 — n = 180 ejecuciones

### Global

| Catálogo | n | Acierto estricto (IC 95 %) | Acierto permisivo | Petición cumplida entera | Elección trampa |
|---|---:|---:|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 60 | **90 %** [0.80–0.95] | 98 % | 93 % | 2 % |
| C · 14 herr. · 4.749 tok | 60 | **93 %** [0.84–0.97] | 93 % | 98 % | 7 % |
| B · 8 herr. · 2.306 tok | 60 | **68 %** [0.56–0.79] | 77 % | 90 % | 17 % |

### Estrato 1 · inequívocas (control)

| Catálogo | n | Acierto estricto (IC 95 %) | Acierto permisivo | Petición cumplida entera | Elección trampa |
|---|---:|---:|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 15 | **100 %** [0.80–1.00] | 100 % | 100 % | 0 % |
| C · 14 herr. · 4.749 tok | 15 | **100 %** [0.80–1.00] | 100 % | 100 % | 0 % |
| B · 8 herr. · 2.306 tok | 15 | **100 %** [0.80–1.00] | 100 % | 100 % | 0 % |

### Estrato 2 · ambiguas con pista

| Catálogo | n | Acierto estricto (IC 95 %) | Acierto permisivo | Petición cumplida entera | Elección trampa |
|---|---:|---:|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 20 | **100 %** [0.84–1.00] | 100 % | 100 % | 0 % |
| C · 14 herr. · 4.749 tok | 20 | **100 %** [0.84–1.00] | 100 % | 100 % | 0 % |
| B · 8 herr. · 2.306 tok | 20 | **35 %** [0.18–0.57] | 55 % | 75 % | 25 % |

### Estrato 3 · encadenadas

| Catálogo | n | Acierto estricto (IC 95 %) | Acierto permisivo | Petición cumplida entera | Elección trampa |
|---|---:|---:|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 10 | **100 %** [0.72–1.00] | 100 % | 100 % | 0 % |
| C · 14 herr. · 4.749 tok | 10 | **100 %** [0.72–1.00] | 100 % | 100 % | 0 % |
| B · 8 herr. · 2.306 tok | 10 | **90 %** [0.60–0.98] | 100 % | 100 % | 0 % |

### Estrato 4 · ambiguas sin pista

| Catálogo | n | Acierto estricto (IC 95 %) | Acierto permisivo | Petición cumplida entera | Elección trampa |
|---|---:|---:|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 15 | **60 %** [0.36–0.80] | 93 % | 73 % | 7 % |
| C · 14 herr. · 4.749 tok | 15 | **73 %** [0.48–0.89] | 73 % | 93 % | 27 % |
| B · 8 herr. · 2.306 tok | 15 | **67 %** [0.42–0.85] | 67 % | 93 % | 33 % |

### Por tarea (acierto estricto)

| Tarea | Estrato | A (27) | C (14) | B (8) |
|---|---:|---:|---:|---:|
| E1a | 1 | 100 % | 100 % | 100 % |
| E1b | 1 | 100 % | 100 % | 100 % |
| E1c | 1 | 100 % | 100 % | 100 % |
| E2a | 2 | 100 % | 100 % | 20 % |
| E2b | 2 | 100 % | 100 % | 100 % |
| E2c | 2 | 100 % | 100 % | 20 % |
| E2d | 2 | 100 % | 100 % | 0 % |
| E3a | 3 | 100 % | 100 % | 100 % |
| E3b | 3 | 100 % | 100 % | 80 % |
| E4a | 4 | 100 % | 100 % | 0 % |
| E4b | 4 | 0 % | 100 % | 100 % |
| E4c | 4 | 80 % | 20 % | 100 % |

### Contrastes (Fisher exacto bilateral)

| Métrica | A (27) | C (14) | p (A vs C) | B (8) | p (A vs B) |
|---|---:|---:|---:|---:|---:|
| acierto estricto | 90 % | 93 % | 0.743 | 68 % | 0.006 **\*** |
| acierto permisivo | 98 % | 93 % | 0.364 | 77 % | 0.000 **\*** |
| petición cumplida entera | 93 % | 98 % | 0.364 | 90 % | 0.743 |
| elección trampa | 2 % | 7 % | 0.364 | 17 % | 0.008 **\*** |

### Coste de la decisión (no de la conversión)

| Catálogo | Coste medio USD/petición | Latencia media | Llamadas sustantivas medias |
|---|---:|---:|---:|
| A · 27 herr. · 7.886 tok | 0.0147 | 10.2 s | 1.12 |
| C · 14 herr. · 4.749 tok | 0.0129 | 10.5 s | 1.18 |
| B · 8 herr. · 2.306 tok | 0.0118 | 11.5 s | 1.23 |

### Distribución de clases

| Catálogo | abstencion | incompleta | mejor | parcial | resuelve | secuencia_exacta | trampa |
|---|---|---|---|---|---|---|---|
| A · 27 herr. · 7.886 tok | 4 | 0 | 40 | 0 | 5 | 10 | 1 |
| C · 14 herr. · 4.749 tok | 1 | 0 | 45 | 0 | 0 | 10 | 4 |
| B · 8 herr. · 2.306 tok | 0 | 1 | 32 | 4 | 4 | 9 | 10 |

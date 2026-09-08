# Cierre global de integración, CR-002 y cobertura real

**Fecha:** 07/09/2026. **Rama:** `integra/cobertura`. **Entorno local:**
Windows, Python 3.11.9, pytest 8.4.2. Se respetó
`disable-hardware-acceleration=true`: FFmpeg usó sus rutas CPU e ImageMagick
corrió con OpenCL apagado.

## Integración

Se fusionaron sin conflictos las tres ramas terminadas:

- N40/C51/C28/N38: `ec87051`, merge `d904fbb`;
- CR-010/CR-007: `3b1dd0b`, merge `18728a2`;
- diagnóstico CR-002: `e4d4760`, merge `ee4ddf6`.

CR-002 se corrigió en `d9d7892` mediante rojo/verde. La sonda ISO-BMFF separa
la duración cruda `mdhd` de la presentación `elst`, soporta versiones 0 y 1 y
no inventa semántica para listas complejas. El arnés real de FFmpeg deja
`mkv→m4a` y `mov→m4a` en `ok_parcial` con las dos sondas y sin A1/V1.

## Resondeo real

Se ejecutaron las 172 aristas gobernadas por el componente `contrato`:

| motor | aristas | reales | nominales nuevas |
|---|---:|---:|---:|
| FFmpeg | 70 | 70 | 0 |
| ImageMagick | 62 | 62 | 0 |
| LibreOffice | 16 | 16 | 0 |
| Pandoc | 16 | 16 | 0 |
| Calibre | 8 | 8 | 0 |
| **total** | **172** | **172** | **0** |

Las dos nominales anteriores de FFmpeg eran exactamente CR-002 y pasaron a
reales. Los tres nominales históricos del grafo (`docx→txt` y `epub→pdf` por
LibreOffice, `epub→html` por Calibre) no pertenecen a estas tablas y conservan
su evidencia negativa. Resultado efectivo: 232 aristas, 229 reales medidas y
3 nominales históricas; cero aristas sin sondear.

Los 40 casos Docker dieron `rc=0`; el arnés contó cinco contenedores del
usuario antes y después, y cero nuevos. Los cinco sellos usan la huella de
contrato `cc1e0253f7da074f`, el mismo build que antes y Python 3.11.

## Verificación local

- CR-002 y regresiones relacionadas: 134 aprobadas; el arnés específico añade
  6 pruebas aprobadas entre unidad y conversión real.
- `pruebas/test_sondeo.py`: 48 aprobadas.
- Suite completa final, tras el ajuste hospedado de N40,
  `python -X utf8 -m pytest pruebas -q -p no:cacheprovider`:
  **995 aprobadas, 11 omitidas, 0 fallos, 4 avisos**, 177,71 s.
- `python -X utf8 ci/integridad.py`: 9 comprobaciones en orden.

## Windows hospedado

La ejecución [34175258765](https://github.com/edicius2002/FileX/actions/runs/34175258765)
sobre `623b302` validó N38 en `windows-latest`: **100/100 intentos completos,
0 fallos**. Ocho intentos observaron un `delta_s` negativo; ninguno borró el
directorio joven y los 100 barridos posteriores sí borraron el vencido. El
artefacto íntegro está versionado como
`salidas-cierre-global/n38-windows-34175258765.json`.

El mismo run destapó un fallo independiente en N40. El arnés abría el HANDLE
antes del orden productivo y Windows 3.11 impedía el `stat` posterior; corregido
el orden del arnés, apareció el defecto real: la raíz corta `RUNNER~1` pasaba el
filtro léxico, pero su ruta final larga se comparaba otra vez contra la raíz
corta y era denegada. `Confinamiento` conserva ahora raíces léxicas para R1 y
raíces canónicas para validar rutas ya resueltas, sin reintroducir raíces de
unidad. La copia al staging se endureció además para leer el descriptor
autorizado directamente, sin duplicarlo mediante el CRT.

La ejecución final
[34177718923](https://github.com/edicius2002/FileX/actions/runs/34177718923)
sobre `ed2bf09` quedó completamente verde: **339 pruebas, 69 omitidas y 0
fallos** en la lista congelada, más **100/100 intentos N38**. Localmente, las
194 pruebas focalizadas de N40/confinamiento quedaron verdes (8 omitidas),
incluido el control Docker CPU, y la suite completa mantuvo 995/11/0.

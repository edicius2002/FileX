# Plan individual N40/C51/C28/N38

Objetivo: reconciliar los cuatro encargos sobre integra/cobertura, sin delegación,
GPU, sidecar, publicación ni cambios en los directorios reservados.

- [x] N40: regresión de sustitución de ruta tras abrir descriptor; materializar
  la entrada desde ese descriptor en un desechable vivo antes del bind. Probar
  extensión, limpieza, denegación y conservación de las defensas existentes.
- [x] N38 local: repetir el barrido conservando todos los intentos; aislar edad negativa
  por reloj/mtime y errores de borrado; regresión determinista antes del arreglo.
  Conservar 2/47 históricos y separar Windows local del runner hospedado.
- [ ] N38 externo: ejecutar esta revisión en windows-latest y atribuir los dos
  incidentes históricos; bloqueado por la entrega sin publicación a otra rama.
- [x] C28: cruzar las clasificaciones históricas, cerrar por rechazo los destinos
  sin contrato autorizado y probar que no aparecen como capacidad nueva.
- [x] C51: verificar la imagen efectiva en CPU; congelar entradas de construcción
  y verificar arranque/build, con caducidad de sellos explícita. No publicar.
- [x] Pruebas focalizadas, suite CPU razonable, integridad y diff --check;
  informe registrado, commits separables con correo noreply y worktree limpio.

Cada defecto sigue investigación → prueba roja → cambio mínimo → prueba verde.
Los cambios históricos ya equivalentes se documentan; no se cherry-pickean.

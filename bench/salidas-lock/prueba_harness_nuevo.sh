#!/usr/bin/env bash
# Prueba del harness NUEVO (C26). NO TOCA LA GPU: solo lee nvidia-smi y usa
# procesos de mentira (sleep) para ocupar el lock.
# Uso: bash prueba_harness_nuevo.sh
set -u

R="/d/Work/research/FileX"
D="$R/bench/salidas-lock"
export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"

echo "############ P0. Sintaxis y firmas ############"
bash -n "$R/bench/lib/harness.sh" && echo "  sintaxis: OK"
. "$R/bench/lib/harness.sh"
for f in gpu_acquire gpu_release measure peak_vram gpu_state gpu_quiet_check; do
  if declare -F "$f" >/dev/null; then echo "  funcion $f: PRESENTE"; else echo "  funcion $f: FALTA <<<<"; fi
done
echo "  GPU_LOCK por defecto = $GPU_LOCK"
( cd /tmp && echo "  /tmp resuelve a: $(pwd -W)" )

echo
echo "############ P1. GPU_LOCK sigue siendo sobrescribible por entorno ############"
(
  export GPU_LOCK="$D/.lock.p1"
  . "$R/bench/lib/harness.sh"
  echo "  GPU_LOCK = $GPU_LOCK"
  [ "$GPU_LOCK" = "$D/.lock.p1" ] && echo "  OK: respeta el valor del entorno" || echo "  FALLO <<<<"
)

echo
echo "############ P2. Ciclo normal adquirir / liberar ############"
(
  export GPU_LOCK="$D/.lock.p2"
  rm -f "$GPU_LOCK"
  . "$R/bench/lib/harness.sh"
  gpu_acquire "prueba-P2" && echo "  contenido: $(tr '\t' '|' < "$GPU_LOCK")"
  gpu_release
  [ -f "$GPU_LOCK" ] && echo "  FALLO: el lock sigue ahi <<<<" || echo "  OK: liberado"
)

echo
echo "############ P3. Lock HUERFANO: taskkill /F al dueño ############"
(
  export GPU_LOCK="$D/.lock.p3"
  rm -f "$GPU_LOCK" ; rm -rf "$GPU_LOCK.robo"
  bash -c '
    export GPU_LOCK="'"$D"'/.lock.p3"
    . '"$R"'/bench/lib/harness.sh
    gpu_acquire "victima-P3" >/dev/null
    cat /proc/$$/winpid > "'"$D"'/.winpid.p3"
    sleep 120
  ' &
  BG=$!
  sleep 4
  WP=$(cat "$D/.winpid.p3" 2>/dev/null)
  echo "  lock tomado por winpid $WP: $(tr '\t' '|' < "$GPU_LOCK" 2>/dev/null)"
  taskkill //F //T //PID "$WP" >/dev/null 2>&1
  sleep 2
  [ -f "$GPU_LOCK" ] && echo "  el fichero sigue ahi tras el taskkill (esperado: el trap no corre)"
  echo "  -- ahora el SIGUIENTE agente intenta adquirirlo:"
  INI=$(date +%s)
  timeout 60 bash -c '
    export GPU_LOCK="'"$D"'/.lock.p3"
    . '"$R"'/bench/lib/harness.sh
    gpu_acquire "siguiente-P3" && echo "     ADQUIRIDO" && gpu_release
  ' 2>&1 | sed 's/^/     /'
  FIN=$(date +%s)
  echo "  tardó $((FIN-INI)) s  (el harness viejo habria esperado 900 s y abortado)"
  kill $BG 2>/dev/null
  rm -f "$GPU_LOCK" "$D/.winpid.p3"
)

echo
echo "############ P4. Lock OCUPADO por un dueño VIVO: no se roba ############"
(
  export GPU_LOCK="$D/.lock.p4"
  rm -f "$GPU_LOCK"
  bash -c '
    export GPU_LOCK="'"$D"'/.lock.p4"
    . '"$R"'/bench/lib/harness.sh
    gpu_acquire "vivo-P4" >/dev/null
    sleep 40
  ' &
  BG=$!
  sleep 4
  INI=$(date +%s)
  timeout 20 bash -c '
    export GPU_LOCK="'"$D"'/.lock.p4"
    . '"$R"'/bench/lib/harness.sh
    gpu_acquire "intruso-P4" && echo "     ROBO INDEBIDO <<<<"
  ' 2>&1 | sed 's/^/     /'
  FIN=$(date +%s)
  echo "  esperó $((FIN-INI)) s sin robar el lock (correcto: el dueño esta vivo)"
  kill $BG 2>/dev/null; rm -f "$GPU_LOCK"
)

echo
echo "############ P5. DETECCION: tarjeta despejada ############"
(
  export GPU_LOCK="$D/.lock.p5"
  rm -f "$GPU_LOCK"
  . "$R/bench/lib/harness.sh"
  echo "  VRAM libre ahora: $(gpu_libre_mib) MiB"
  gpu_acquire "detec-despejada" && echo "  OK: arranca" || echo "  ABORTADO (rc=$?)"
  gpu_release
)

echo
echo "############ P6. DETECCION: tarjeta OCUPADA (simulada subiendo el umbral) ############"
echo "  -- no se ocupa la GPU de verdad: se sube GPU_LIBRE_MIN_MIB por encima de lo libre."
(
  export GPU_LOCK="$D/.lock.p6" GPU_LIBRE_MIN_MIB=20000 GPU_LIBRE_AVISO_MIB=20000
  rm -f "$GPU_LOCK"
  . "$R/bench/lib/harness.sh"
  gpu_acquire "detec-ocupada" ; rc=$?
  echo "  rc=$rc  (2 = se niega a medir, que es el defecto GPU_GUARD=abortar)"
  [ -f "$GPU_LOCK" ] && echo "  FALLO: dejo el lock tomado <<<<" || echo "  OK: soltó el lock al abortar"
)

echo
echo "############ P7. GPU_GUARD=avisar mide igualmente ############"
(
  export GPU_LOCK="$D/.lock.p7" GPU_LIBRE_MIN_MIB=20000 GPU_LIBRE_AVISO_MIB=20000 GPU_GUARD=avisar
  rm -f "$GPU_LOCK"
  . "$R/bench/lib/harness.sh"
  gpu_acquire "detec-avisar" ; echo "  rc=$?"
  gpu_release
)

echo
echo "############ P8. measure() sigue funcionando y marca SUCIA por VRAM ############"
(
  export GPU_LOCK="$D/.lock.p8"
  . "$R/bench/lib/harness.sh"
  echo "  -- con la tarjeta como esta:"
  measure "control-ffprobe" 3 -- ffprobe -v quiet -version | sed 's/^/     /'
)
(
  export GPU_LOCK="$D/.lock.p8b" GPU_LIBRE_AVISO_MIB=20000
  . "$R/bench/lib/harness.sh"
  echo "  -- con el umbral de aviso por las nubes (simula VRAM ajena):"
  measure "control-ffprobe" 3 -- ffprobe -v quiet -version | sed 's/^/     /'
)

echo
echo "############ P9. peak_vram: fichero de muestras con PID, sin colision ############"
(
  export GPU_LOCK="$D/.lock.p9"
  . "$R/bench/lib/harness.sh"
  peak_vram ffprobe -v quiet -version | sed 's/^/     /'
  ls /tmp/_vram_samples.*.txt 2>/dev/null | sed 's/^/     residuo: /' || echo "     sin residuos en /tmp: OK"
)

echo
echo "############ P10. Censo de procesos ajenos ############"
(
  . "$R/bench/lib/harness.sh"
  gpu_censo_ajeno | head -8 | sed 's/^/     /'
)

rm -f "$D"/.lock.p* 2>/dev/null
echo
echo "############ FIN ############"

#!/usr/bin/env bash
# Reproduce el defecto del lock VIEJO: un proceso muerto con taskkill /F no ejecuta
# el trap EXIT y deja el fichero de lock huerfano.
# Uso: bash prueba_huerfano_viejo.sh
# No toca la GPU: solo el fichero de lock.
set -u

RAIZ="D:/Work/research/FileX"
LOCK="$RAIZ/bench/salidas-lock/.gpu.lock.prueba"
export GPU_LOCK="$LOCK"

rm -f "$LOCK"

echo "== 1. arranco un tomador del lock en segundo plano (harness VIEJO) =="
bash -c '
  source '"$RAIZ"'/bench/salidas-lock/harness_viejo.sh
  gpu_acquire "victima"
  cat /proc/$$/winpid > '"$RAIZ"'/bench/salidas-lock/.winpid.prueba
  sleep 120
' &
BGPID=$!
sleep 3

echo "-- contenido del lock:"; cat "$LOCK" 2>&1
WINPID=$(cat "$RAIZ/bench/salidas-lock/.winpid.prueba" 2>/dev/null)
echo "-- winpid de la victima: $WINPID"

echo "== 2. lo mato con taskkill /F /T (no ejecuta el trap) =="
taskkill //F //T //PID "$WINPID" 2>&1 | head -3
sleep 2

echo "== 3. estado del lock DESPUES de la muerte violenta =="
if [ -f "$LOCK" ]; then
  echo "HUERFANO CONFIRMADO: el fichero sigue ahi -> $(cat "$LOCK")"
else
  echo "el lock se liberó (el trap si corrio)"
fi

echo "== 4. cuanto espera el siguiente agente (harness VIEJO, tope 900 s) =="
INI=$(date +%s)
timeout 25 bash -c '
  source '"$RAIZ"'/bench/salidas-lock/harness_viejo.sh
  gpu_acquire "siguiente" && echo "ADQUIRIDO"
' 2>&1 | head -3
FIN=$(date +%s)
echo "-- el intento se cortó a los $((FIN-INI)) s por MI timeout de 25 s; el harness viejo habria esperado 900"

kill $BGPID 2>/dev/null
rm -f "$LOCK" "$RAIZ/bench/salidas-lock/.winpid.prueba"
echo "== fin =="

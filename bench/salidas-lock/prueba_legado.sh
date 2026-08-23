#!/usr/bin/env bash
# P11/P12 — el lock de LEGADO (bench/.gpu.lock) durante la transición.
# No toca la GPU.
set -u
R="/d/Work/research/FileX"
D="$R/bench/salidas-lock"
export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"
LEG="$D/.legado.prueba"

echo "############ P11. Lock de legado VIVO: el harness nuevo espera ############"
rm -f "$LEG"
bash -c 'echo "tanda-vieja $$" > '"$LEG"'; sleep 40' &
BG=$!
sleep 2
echo "  contenido del legado: $(cat "$LEG")"
INI=$(date +%s)
timeout 18 bash -c '
  export GPU_LOCK="'"$D"'/.lock.p11" GPU_LOCK_LEGADO="'"$LEG"'"
  . '"$R"'/bench/lib/harness.sh
  gpu_acquire "nuevo-P11" && echo "     ADQUIRIDO SIN ESPERAR <<<< FALLO"
' 2>&1 | sed 's/^/     /'
FIN=$(date +%s)
echo "  esperó $((FIN-INI)) s por un lock que ni siquiera es el suyo: correcto"
kill $BG 2>/dev/null; rm -f "$LEG" "$D/.lock.p11"

echo
echo "############ P12. Lock de legado HUERFANO: lo borra y sigue ############"
echo "tanda-muerta 999999" > "$LEG"
timeout 40 bash -c '
  export GPU_LOCK="'"$D"'/.lock.p12" GPU_LOCK_LEGADO="'"$LEG"'"
  . '"$R"'/bench/lib/harness.sh
  gpu_acquire "nuevo-P12" && echo "     ADQUIRIDO" && gpu_release
' 2>&1 | sed 's/^/     /'
[ -f "$LEG" ] && echo "  FALLO: el legado sigue ahi <<<<" || echo "  OK: legado huerfano borrado"
rm -f "$LEG" "$D/.lock.p12"
echo "############ FIN ############"

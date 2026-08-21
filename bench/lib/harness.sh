#!/usr/bin/env bash
# Arnés de medición del carril GPU.
# Premisa: la 3060 es una GPU de escritorio compartida con Chrome, Discord,
# Wallpaper Engine, etc. Una medición sin línea base no es un dato, es ruido
# con aspecto de dato. Todo lo que se mide aquí lleva su contexto pegado.

GPU_LOCK="${GPU_LOCK:-D:/Work/research/FileX/bench/.gpu.lock}"

# --- exclusión mutua: solo un agente puede tocar la GPU a la vez ---
gpu_acquire(){
  local who="${1:-anon}" waited=0
  while ! (set -o noclobber; echo "$who $$" > "$GPU_LOCK") 2>/dev/null; do
    if [ $waited -eq 0 ]; then echo "[bloqueado] GPU en uso por: $(cat "$GPU_LOCK" 2>/dev/null)" >&2; fi
    sleep 5; waited=$((waited+5))
    if [ $waited -ge 900 ]; then echo "[abortado] 15 min esperando el lock de GPU" >&2; return 1; fi
  done
  trap 'gpu_release' EXIT INT TERM
  echo "[lock] adquirido por $who"
}
gpu_release(){ rm -f "$GPU_LOCK" 2>/dev/null; }

# --- estado de la GPU: se registra ANTES de cada medición ---
gpu_state(){
  nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu \
             --format=csv,noheader,nounits 2>/dev/null | tr -d ' '
}

# --- ¿está la GPU lo bastante tranquila para medir? ---
# Umbral: <10% de utilización sostenida. Si no, la medición se marca SUCIA.
gpu_quiet_check(){
  local peak=0
  for _ in 1 2 3 4 5; do
    u=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null | tr -d ' ')
    [ "${u:-0}" -gt "$peak" ] && peak=$u
    sleep 1
  done
  echo "$peak"
}

# --- medición con contexto ---
# uso: measure "etiqueta" N -- comando args...
measure(){
  local label="$1" n="$2"; shift 3   # descarta el "--"
  local before after quiet times=() t
  quiet=$(gpu_quiet_check)
  before=$(gpu_state)
  for _ in $(seq "$n"); do
    local s e
    s=$(date +%s%N); "$@" >/dev/null 2>&1; e=$(date +%s%N)
    times+=( $(( (e-s)/1000000 )) )
  done
  after=$(gpu_state)
  # mediana, no media: resiste mejor un pico de Chrome a mitad de tanda
  local sorted median
  sorted=$(printf '%s\n' "${times[@]}" | sort -n)
  median=$(echo "$sorted" | awk '{a[NR]=$1} END{print (NR%2)?a[(NR+1)/2]:int((a[NR/2]+a[NR/2+1])/2)}')
  local flag="limpia"; [ "${quiet:-0}" -ge 10 ] && flag="SUCIA(pico ${quiet}%)"
  printf '%-38s mediana:%6s ms  n=%-3s  rango:%s-%s  [%s]  gpu_antes:%s  gpu_despues:%s\n' \
    "$label" "$median" "$n" "$(echo "$sorted"|head -1)" "$(echo "$sorted"|tail -1)" \
    "$flag" "$before" "$after"
}

# --- VRAM máxima consumida durante un comando (muestreo en paralelo) ---
# uso: peak_vram comando args...
peak_vram(){
  local pidfile peak=0 sampler
  ( while :; do
      nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | tr -d ' '
      sleep 0.25
    done ) > /tmp/_vram_samples.txt &
  sampler=$!
  "$@" >/dev/null 2>&1
  local rc=$?
  kill $sampler 2>/dev/null; wait $sampler 2>/dev/null
  peak=$(sort -n /tmp/_vram_samples.txt 2>/dev/null | tail -1)
  echo "pico_vram_total_MiB=$peak rc=$rc"
  rm -f /tmp/_vram_samples.txt
  return $rc
}

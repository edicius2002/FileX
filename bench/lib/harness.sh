#!/usr/bin/env bash
# Arnés de medición del carril GPU.
# Premisa: la 3060 es una GPU de escritorio compartida con Chrome, Discord,
# Wallpaper Engine, etc. Una medición sin línea base no es un dato, es ruido
# con aspecto de dato. Todo lo que se mide aquí lleva su contexto pegado.
#
# ─────────────────────────────────────────────────────────────────────────────
# REVISIÓN DEL 23/08/2026 (C26) — `bench/lock-de-maquina.md`
#
# El lock vivía en `bench/.gpu.lock`, DENTRO del repositorio. Eso deja fuera a
# cualquier cosa que no sea este árbol de trabajo, y ya costó 12 minutos de una
# tanda (`bench/ppp-y-normalizacion.md` §1.3): una sesión de Claude en
# `D:\Work\research\ASR` ocupaba 11 754 de 12 288 MiB con el lock de FileX LIBRE.
#
# El arreglo tiene DOS MITADES, y la segunda es la que cierra aquel caso:
#
#   1. EXCLUSIÓN — el lock pasa a `%TEMP%` (de máquina, no de repositorio), así
#      que también excluye a otra copia o worktree de FileX. Y deja de quedarse
#      huérfano: lleva dentro el PID de Windows y el nombre de imagen del dueño,
#      y quien lo encuentre comprueba si sigue vivo antes de esperar.
#
#   2. DETECCIÓN — antes de arrancar una tanda se mira la VRAM LIBRE. Un lock no
#      obliga a cooperar a quien no lo toma: la sesión de ASR nunca iba a tomar
#      este fichero, esté donde esté. Lo único que ve a un ocupante que no
#      coopera es mirar la tarjeta.
#
# Compatibilidad: `gpu_acquire`, `gpu_release`, `measure` y `peak_vram` mantienen
# nombre, firma y contrato de uso. `GPU_LOCK` sigue siendo sobrescribible por
# entorno: lo único que cambia es su valor POR DEFECTO.
# ─────────────────────────────────────────────────────────────────────────────

# --- dónde vive el lock -------------------------------------------------------
# Por defecto, `/tmp`, que en este Git Bash resuelve a %TEMP%
# (`cd /tmp && pwd -W` -> C:/Users/krato/AppData/Local/Temp, MEDIDO el 23/08).
# Es decir: el mismo fichero para cualquier copia de FileX de este usuario.
# Sigue habiendo un límite declarado: %TEMP% es POR USUARIO y no cruza a la VM
# de WSL2. Un mutex con nombre de Windows sería de máquina de verdad, pero no se
# puede tomar desde shell sin añadir una dependencia.
GPU_LOCK_DIR="${GPU_LOCK_DIR:-/tmp}"
GPU_LOCK="${GPU_LOCK:-$GPU_LOCK_DIR/filex-gpu.lock}"

# Lock de LEGADO: el sitio donde vivía hasta el 23/08. Mientras haya tandas
# arrancadas con el harness viejo todavía vivas, siguen tomando ESE fichero y no
# el nuevo. Cambiar de sitio sin mirar el sitio antiguo abriría, durante la
# transición, justo el agujero que este cambio viene a cerrar.
GPU_LOCK_LEGADO="${GPU_LOCK_LEGADO:-D:/Work/research/FileX/bench/.gpu.lock}"

# --- umbrales de la mitad de DETECCIÓN ---------------------------------------
# Calibrados sobre la línea base REAL de esta máquina, no supuestos
# (n=90 muestras a 1 s, 23/08 07:56-07:58, escritorio + sesión remota + Chrome +
#  Discord + Spotify + Wallpaper Engine):
#     VRAM ocupada  3 292 / 3 356 / 3 448 MiB  (mín / mediana / máx)
#     VRAM libre    8 996 / 8 932 / 8 840 MiB
#     recorrido intra-tanda: 156 MiB
# El caso que motivó C26 dejaba 534 MiB libres. Los dos regímenes están a un
# orden de magnitud, así que el umbral no es delicado:
#   - AVISO  a 7 500 MiB libres: 1 340 MiB por debajo del suelo observado, que es
#            8,6× el recorrido del propio escritorio. No lo dispara el escritorio.
#   - ABORTO a 6 000 MiB libres: por encima del coste propio del motor más caro
#            medido (EasyOCR +4 430 MiB, `ocr-ppp-nativos.md` §7.2), y muy por
#            encima de los 534 MiB del intruso. Un escritorio normal no lo toca.
GPU_LIBRE_AVISO_MIB="${GPU_LIBRE_AVISO_MIB:-7500}"
GPU_LIBRE_MIN_MIB="${GPU_LIBRE_MIN_MIB:-6000}"
# Qué hacer si la tarjeta está ocupada por alguien que no coopera:
#   abortar (por defecto) · esperar · avisar · ignorar
GPU_GUARD="${GPU_GUARD:-abortar}"
GPU_GUARD_ESPERA_MAX="${GPU_GUARD_ESPERA_MAX:-900}"
# Marca que distingue lo PROPIO de lo AJENO en el censo de procesos.
GPU_MARCA_PROPIA="${GPU_MARCA_PROPIA:-FileX}"

_GPU_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GPU_PS="${GPU_PS:-/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe}"

# --- estado de la GPU: se registra ANTES de cada medición ---
gpu_state(){
  nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu \
             --format=csv,noheader,nounits 2>/dev/null | tr -d ' '
}

# VRAM libre en MiB. Devuelve vacío si nvidia-smi no responde: quien llama decide.
gpu_libre_mib(){
  nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits 2>/dev/null \
    | tr -d ' ' | head -1
}

# --- censo de ocupantes AJENOS ------------------------------------------------
# No mide VRAM por proceso: en esta máquina NO SE PUEDE.
#   nvidia-smi --query-compute-apps=used_memory -> [N/A] en los 30 procesos
#   nvidia-smi pmon -> "The feature is not supported in this configuration"
# (MEDIDO el 23/08.) Lo que sí es atribuible es la línea de órdenes, y ahí sí se
# ve de qué repositorio viene el proceso. Tope propio de 20 s: un testigo que
# puede tumbar la medición no es un testigo (`verificador-ghostscript.md` §4).
gpu_censo_ajeno(){
  if [ ! -x "$GPU_PS" ] && [ ! -f "$GPU_PS" ]; then
    echo "CENSO_NO_DISPONIBLE (no encuentro powershell en $GPU_PS)"
    return 0
  fi
  timeout 20 "$GPU_PS" -NoProfile -ExecutionPolicy Bypass \
      -File "$_GPU_LIB_DIR/censo_gpu.ps1" "$GPU_MARCA_PROPIA" 2>/dev/null \
    || echo "CENSO_AGOTADO (20 s)"
}

# --- ¿hay alguien que no coopera ocupando la tarjeta? -------------------------
# Devuelve: 0 despejado · 1 banda de aviso · 2 ocupada de verdad
# Imprime siempre una línea legible por máquina en la salida de error.
gpu_ocupacion_ajena(){
  local libre; libre="$(gpu_libre_mib)"
  if [ -z "$libre" ]; then
    echo "[gpu] nvidia-smi no responde: no se puede comprobar la ocupación" >&2
    return 1
  fi
  if [ "$libre" -lt "$GPU_LIBRE_MIN_MIB" ]; then
    echo "[gpu] OCUPADA por terceros: ${libre} MiB libres < ${GPU_LIBRE_MIN_MIB} de mínimo" >&2
    return 2
  fi
  if [ "$libre" -lt "$GPU_LIBRE_AVISO_MIB" ]; then
    echo "[gpu] ESTRECHA: ${libre} MiB libres < ${GPU_LIBRE_AVISO_MIB} de aviso" >&2
    return 1
  fi
  return 0
}

# --- exclusión mutua: solo un agente puede tocar la GPU a la vez ---
# El fichero lleva DENTRO lo que hace falta para saber si su dueño sigue vivo:
#   etiqueta<TAB>pid_msys<TAB>winpid<TAB>imagen<TAB>epoch<TAB>raiz
# El `$$` de Git Bash NO es el PID de Windows (MEDIDO: 45483 frente a 11656),
# así que hay que guardar los dos.
_gpu_lock_campo(){ awk -F'\t' -v n="$1" 'NR==1{print $n}' "$GPU_LOCK" 2>/dev/null; }

# ¿sigue vivo el dueño del lock? 0 = sí, 1 = no (lock huérfano)
# Comprueba PID **y nombre de imagen**: en Windows los PID se reutilizan, y
# «un PID vivo no siempre es el que crees» (CLAUDE.md §3, los soffice de R18).
_gpu_dueno_vivo(){
  local winpid imagen linea
  winpid="$(_gpu_lock_campo 3)"; imagen="$(_gpu_lock_campo 4)"
  [ -z "$winpid" ] && return 0          # formato viejo, sin PID: no lo robo
  linea="$(timeout 15 tasklist //FI "PID eq $winpid" //NH //FO CSV 2>/dev/null | head -1)"
  case "$linea" in
    *"$winpid"*) ;;                     # hay un proceso con ese PID
    *) return 1 ;;                      # no hay nadie: huérfano
  esac
  [ -n "$imagen" ] && case "$linea" in
    *"$imagen"*) ;;
    *) return 1 ;;                      # PID reutilizado por otro programa
  esac
  return 0
}

gpu_acquire(){
  local who="${1:-anon}" waited=0 winpid imagen linea esperado_gpu=0
  winpid="$(cat /proc/$$/winpid 2>/dev/null)"; : "${winpid:=$$}"
  imagen="$(basename "${BASH:-bash}")"
  linea="$(printf '%s\t%s\t%s\t%s\t%s\t%s' "$who" "$$" "$winpid" "$imagen" "$(date +%s)" "${PWD}")"

  # ── mitad 0: el lock de LEGADO, solo durante la transición ──────────────────
  # Formato viejo: "etiqueta pid_msys" separados por espacio y sin winpid.
  if [ "$GPU_LOCK" != "$GPU_LOCK_LEGADO" ] && [ -f "$GPU_LOCK_LEGADO" ]; then
    local vpid; vpid="$(awk '{print $2}' "$GPU_LOCK_LEGADO" 2>/dev/null)"
    if [ -n "$vpid" ] && kill -0 "$vpid" 2>/dev/null; then
      echo "[bloqueado] lock de LEGADO vivo en $GPU_LOCK_LEGADO: $(cat "$GPU_LOCK_LEGADO")" >&2
      while [ -f "$GPU_LOCK_LEGADO" ] && kill -0 "$vpid" 2>/dev/null; do
        sleep 5; waited=$((waited+5))
        if [ $waited -ge 900 ]; then echo "[abortado] 15 min esperando el lock de legado" >&2; return 1; fi
      done
    else
      echo "[lock] lock de LEGADO huérfano en $GPU_LOCK_LEGADO ('$(cat "$GPU_LOCK_LEGADO" 2>/dev/null)'): lo borro" >&2
      rm -f "$GPU_LOCK_LEGADO" 2>/dev/null
    fi
    waited=0
  fi

  # ── mitad 1: exclusión ──────────────────────────────────────────────────────
  while ! (set -o noclobber; echo "$linea" > "$GPU_LOCK") 2>/dev/null; do
    if ! _gpu_dueno_vivo; then
      # Lock huérfano: su dueño murió sin ejecutar el trap (taskkill /F no lo
      # ejecuta — MEDIDO). Robarlo bajo un mkdir atómico para que dos que
      # esperan no lo roben a la vez.
      if mkdir "$GPU_LOCK.robo" 2>/dev/null; then
        echo "[lock] HUERFANO detectado (dueño '$(_gpu_lock_campo 1)' pid $(_gpu_lock_campo 3) muerto): lo libero" >&2
        rm -f "$GPU_LOCK" 2>/dev/null
        rmdir "$GPU_LOCK.robo" 2>/dev/null
      fi
      continue
    fi
    if [ $waited -eq 0 ]; then echo "[bloqueado] GPU en uso por: $(cat "$GPU_LOCK" 2>/dev/null)" >&2; fi
    sleep 5; waited=$((waited+5))
    if [ $waited -ge 900 ]; then echo "[abortado] 15 min esperando el lock de GPU" >&2; return 1; fi
  done
  trap 'gpu_release' EXIT INT TERM

  # ── mitad 2: detección ──────────────────────────────────────────────────────
  # El lock ya es nuestro: quien pueda estar ocupando la tarjeta AHORA es alguien
  # que no coopera, y ningún lock lo va a echar.
  gpu_ocupacion_ajena; local oc=$?
  if [ "$oc" -ge 1 ]; then
    echo "[gpu] censo de procesos ajenos (no se puede atribuir VRAM por PID en WDDM):" >&2
    gpu_censo_ajeno >&2
  fi
  if [ "$oc" -eq 2 ]; then
    case "$GPU_GUARD" in
      ignorar) echo "[gpu] GPU_GUARD=ignorar: sigo con la tarjeta ocupada" >&2 ;;
      avisar)  echo "[gpu] GPU_GUARD=avisar: la tanda entera queda marcada SUCIA" >&2 ;;
      esperar)
        while [ "$esperado_gpu" -lt "$GPU_GUARD_ESPERA_MAX" ]; do
          sleep 15; esperado_gpu=$((esperado_gpu+15))
          gpu_ocupacion_ajena >/dev/null 2>&1 && break
        done
        if [ "$esperado_gpu" -ge "$GPU_GUARD_ESPERA_MAX" ]; then
          echo "[gpu] ABORTO: ${GPU_GUARD_ESPERA_MAX}s esperando a que se libere la VRAM ajena" >&2
          gpu_release; return 2
        fi
        echo "[gpu] la VRAM ajena se liberó tras ${esperado_gpu}s" >&2 ;;
      *)
        # Por defecto NO se mide. La evidencia dice que el modo de fallo no es
        # «un número algo peor» sino una tanda entera sin resultado (12 min sin
        # procesar una imagen) o —peor— un número malo etiquetado `limpia`.
        # Negarse cuesta 0; medir con la tarjeta ajena cuesta la tanda.
        echo "[gpu] ABORTO: la tarjeta está ocupada por un tercero. Repite cuando se libere," >&2
        echo "      o fuerza con GPU_GUARD=avisar (mide y marca SUCIA) / esperar / ignorar." >&2
        gpu_release; return 2 ;;
    esac
  fi
  echo "[lock] adquirido por $who  (lock: $GPU_LOCK · libre: $(gpu_libre_mib) MiB)"
}

# Solo borra el lock si es NUESTRO: si otro nos lo robó por huérfano, no se lo
# quitamos de debajo.
gpu_release(){
  local mio; mio="$(_gpu_lock_campo 2)"
  if [ -z "$mio" ] || [ "$mio" = "$$" ]; then rm -f "$GPU_LOCK" 2>/dev/null; fi
}

# --- ¿está la GPU lo bastante tranquila para medir? ---
# Umbral: <10% de utilización sostenida. Si no, la medición se marca SUCIA.
# (Aviso MEDIDO el 23/08: con la sesión remota y el escritorio, la utilización
# en reposo va de 14 a 57 % — n=90 en 90 s. Este testigo marca SUCIA SIEMPRE en
# esta máquina. Es estructural, y por eso no basta: la ocupación de VRAM sí
# separa la línea base de un intruso, y la utilización no.)
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
  local libre_ini; libre_ini="$(gpu_libre_mib)"
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
  # La VRAM ajena manda sobre la utilización: es la señal que distinguió el caso
  # de ASR, y la que la utilización no vio.
  if [ -n "$libre_ini" ] && [ "$libre_ini" -lt "$GPU_LIBRE_AVISO_MIB" ]; then
    flag="SUCIA(vram_libre ${libre_ini}MiB)"
  fi
  printf '%-38s mediana:%6s ms  n=%-3s  rango:%s-%s  [%s]  gpu_antes:%s  gpu_despues:%s\n' \
    "$label" "$median" "$n" "$(echo "$sorted"|head -1)" "$(echo "$sorted"|tail -1)" \
    "$flag" "$before" "$after"
}

# --- VRAM máxima consumida durante un comando (muestreo en paralelo) ---
# uso: peak_vram comando args...
peak_vram(){
  # El fichero de muestras llevaba nombre FIJO en /tmp, que es %TEMP% y por tanto
  # COMPARTIDO por todas las sesiones de la máquina: dos peak_vram a la vez se
  # pisaban. Ahora lleva el PID.
  local muestras="/tmp/_vram_samples.$$.txt"
  local peak=0 sampler
  ( while :; do
      nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | tr -d ' '
      sleep 0.25
    done ) > "$muestras" &
  sampler=$!
  "$@" >/dev/null 2>&1
  local rc=$?
  kill $sampler 2>/dev/null; wait $sampler 2>/dev/null
  peak=$(sort -n "$muestras" 2>/dev/null | tail -1)
  echo "pico_vram_total_MiB=$peak rc=$rc"
  rm -f "$muestras"
  return $rc
}

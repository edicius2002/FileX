#!/usr/bin/env bash
# C39: cuatro direcciones, control positivo. Ejecutar desde WSL; no toca GPU.
set -u
ROOT='/mnt/d/Work/research/FileX/.ccb/workspaces/worker1'
GIT='/mnt/c/Program Files/Git/bin/bash.exe'
OUT="$ROOT/bench/salidas-lock-python/cruce_mutex.log"
: > "$OUT"
owner_git(){ "$GIT" -lc "cd /d/Work/research/FileX/.ccb/workspaces/worker1; source bench/lib/harness.sh; gpu_acquire c39-git; sleep 12; gpu_release"; }
owner_wsl(){ cd "$ROOT"; source bench/lib/harness.sh; gpu_acquire c39-wsl; sleep 12; gpu_release; }
eval_git(){ "$GIT" -lc "cd /d/Work/research/FileX/.ccb/workspaces/worker1; source bench/lib/harness.sh; gpu_acquire c39-eval; gpu_release"; }
eval_wsl(){ cd "$ROOT"; source bench/lib/harness.sh; gpu_acquire c39-eval; gpu_release; }
celda(){
  local n="$1" owner_fn="$2" eval_fn="$3" log="/tmp/c39-$1.$$.log" rc antes despues
  "$owner_fn" >"$log" 2>&1 & local pid=$!
  for _ in $(seq 1 100); do grep -q 'mutex adquirido' "$log" 2>/dev/null && break; sleep 0.1; done
  kill -0 "$pid" 2>/dev/null; antes=$?
  case "$eval_fn" in
    eval_git) timeout 3 "$GIT" -lc "cd /d/Work/research/FileX/.ccb/workspaces/worker1; source bench/lib/harness.sh; gpu_acquire c39-eval; gpu_release" >/dev/null 2>&1 ;;
    eval_wsl) timeout 3 bash -lc "cd '$ROOT'; source bench/lib/harness.sh; gpu_acquire c39-eval; gpu_release" >/dev/null 2>&1 ;;
  esac
  rc=$?
  kill -0 "$pid" 2>/dev/null; despues=$?
  wait "$pid" 2>/dev/null
  printf '%s antes=%s rc_eval=%s despues=%s\n' "$n" "$antes" "$rc" "$despues" | tee -a "$OUT"
}
celda_libre(){
  local n="$1" eval_fn="$2" rc
  case "$eval_fn" in
    eval_git) timeout 3 "$GIT" -lc "cd /d/Work/research/FileX/.ccb/workspaces/worker1; source bench/lib/harness.sh; gpu_acquire c39-control; gpu_release" >/dev/null 2>&1 ;;
    eval_wsl) timeout 3 bash -lc "cd '$ROOT'; source bench/lib/harness.sh; gpu_acquire c39-control; gpu_release" >/dev/null 2>&1 ;;
  esac
  rc=$?
  printf '%s sin_dueno rc_eval=%s\n' "$n" "$rc" | tee -a "$OUT"
}
celda_libre E eval_git
celda_libre F eval_wsl
celda A owner_git eval_git
celda B owner_git eval_wsl
celda C owner_wsl eval_git
celda D owner_wsl eval_wsl

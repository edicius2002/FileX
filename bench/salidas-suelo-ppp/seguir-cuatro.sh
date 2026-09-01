#!/usr/bin/env bash
# Conductor desprendible: una configuración = un Python nuevo y un lock nuevo.
set -u
ROOT=/d/Work/research/FileX/.ccb/workspaces/worker1
OUT="$ROOT/bench/salidas-suelo-ppp"
PROGRESO="$OUT/logs/seguir-cuatro.progreso.log"
PPP=100,105,110,115,120,125,130,135,140,145,150

ejecutar() {
  local entorno=$1 config=$2 rc
  printf '%s INICIO config=%s entorno=%s\n' "$(date -Iseconds)" "$config" "$entorno" >> "$PROGRESO"
  "$ROOT/$entorno/Scripts/python.exe" "$OUT/b21b22.py" "$config" --ppp "$PPP" --reps 9 \
    > "$OUT/logs/${config}-bgr.log" 2>&1
  rc=$?
  printf '%s FIN config=%s rc=%s\n' "$(date -Iseconds)" "$config" "$rc" >> "$PROGRESO"
  return 0                         # registra el fallo y continúa con la siguiente
}

mkdir -p "$OUT/logs"
ejecutar .venv-ai docling-r6
ejecutar .venv-paddle paddle
ejecutar .venv-ai docling-def
ejecutar .venv-ai easy

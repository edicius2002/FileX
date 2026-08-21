#!/usr/bin/env bash
# Fase 0 — clonado de candidatos (shallow, sin historial)
set -u
ROOT="D:/Work/research/FileX/repos"
LOG="D:/Work/research/FileX/bench/clone.log"
: > "$LOG"

clone(){ # $1=grupo $2=owner/repo
  local dir="$ROOT/$1/$(basename "$2")"
  if [ -d "$dir/.git" ]; then echo "SKIP  $2 (ya existe)" | tee -a "$LOG"; return; fi
  if git clone --depth 1 --quiet "https://github.com/$2.git" "$dir" 2>>"$LOG"; then
    echo "OK    $2  ($(du -sh "$dir" 2>/dev/null | cut -f1))" | tee -a "$LOG"
  else
    echo "FAIL  $2" | tee -a "$LOG"
  fi
}

# --- orchestrators: candidatos a base arquitectónica ---
clone orchestrators snapotter-hq/SnapOtter
clone orchestrators C4illin/ConvertX
clone orchestrators transmute-app/transmute
clone orchestrators VERT-sh/VERT
clone orchestrators danvergara/morphos
clone orchestrators gotenberg/gotenberg
clone orchestrators Stirling-Tools/Stirling-PDF

# --- ai-engines: la mitad GPU del ecosistema ---
clone ai-engines microsoft/markitdown
clone ai-engines docling-project/docling
clone ai-engines docling-project/docling-mcp
clone ai-engines docling-project/docling-serve
clone ai-engines opendatalab/MinerU
clone ai-engines datalab-to/marker
clone ai-engines datalab-to/surya
clone ai-engines SYSTRAN/faster-whisper
clone ai-engines ocrmypdf/OCRmyPDF

# --- mcp-refs: patrones CLI+MCP ---
clone mcp-refs chrisryugj/kordoc
clone mcp-refs KorigamiK/markitdown_mcp_server
clone mcp-refs misbahsy/video-audio-mcp
clone mcp-refs kevinwatt/ffmpeg-mcp-lite
clone mcp-refs BoomLinkAi/image-worker-mcp
clone mcp-refs modelcontextprotocol/servers

echo "=== TOTAL ===" | tee -a "$LOG"
du -sh "$ROOT" 2>/dev/null | tee -a "$LOG"

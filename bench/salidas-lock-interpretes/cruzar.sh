#!/usr/bin/env bash
# Cruza las cuatro combinaciones de (quien RETIENE el lock) x (quien lo EVALÚA).
#
# Coreografía, y es la mitad del experimento: el dueño se lanza en SEGUNDO PLANO
# y se queda vivo; sólo cuando el lock existe en disco se evalúa desde el otro
# intérprete; después se espera a que el dueño muera solo. Una versión anterior
# escribía y salía, y las cuatro celdas daban «huérfano» porque el dueño ya
# estaba muerto — el control positivo (celda A) fue lo único que lo destapó.
#
# Se lanza desde WSL2. El Git Bash se invoca por RUTA RESUELTA, nunca por nombre
# (trampa 77: `bash` a secas desde WSL no es el Git Bash).
set -u

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SONDA_WSL="$BASE/sonda_lock.sh"
GITBASH="/mnt/c/Program Files/Git/bin/bash.exe"
RETENCION=25

# El fichero de lock vive en %TEMP% de Windows: visible desde los DOS mundos.
# Ése es justo el "arreglo obvio" que esta sonda viene a evaluar.
# %TEMP% real, preguntado a Windows en vez de deducido.
TEMPWIN="$(/mnt/c/Windows/System32/cmd.exe /c "echo %TEMP%" 2>/dev/null | tr -d '\r')"
TMPWIN_WSL="$(echo "$TEMPWIN" | sed 's|\\|/|g; s|^C:|/mnt/c|')"
LOCK_WSL="$TMPWIN_WSL/sonda-lock-interpretes.lock"
LOCK_GIT="$(echo "$TEMPWIN" | sed 's|\\|/|g; s|^C:|/c|')/sonda-lock-interpretes.lock"
SONDA_GIT="$(echo "$BASE" | sed 's|^/mnt/d|/d|')/sonda_lock.sh"

echo "lock (WSL)      : $LOCK_WSL"
echo "lock (Git Bash) : $LOCK_GIT"
echo "retención       : ${RETENCION}s"
echo

# ⚠ La salida del hijo va a /dev/null A PROPÓSITO. Con `$(ret_git)` capturando
# stdout, la sustitución de órdenes espera a que el hijo CIERRE stdout —es decir,
# a que muera— y para cuando se evaluaba el lock su dueño llevaba 25 s muerto.
# Segunda vez que la misma coreografía muerde en esta sonda.
ret_wsl(){ bash "$SONDA_WSL" retener "$LOCK_WSL" "$RETENCION" >/dev/null 2>&1 & echo $!; }
ret_git(){ "$GITBASH" -c "bash '$SONDA_GIT' retener '$LOCK_GIT' $RETENCION" >/dev/null 2>&1 & echo $!; }
ev_wsl(){  timeout 120 bash "$SONDA_WSL" evaluar "$LOCK_WSL"; }
ev_git(){  timeout 120 "$GITBASH" -c "bash '$SONDA_GIT' evaluar '$LOCK_GIT'"; }

celda(){
  local titulo="$1" retener="$2" evaluar="$3"
  echo "########## CELDA $titulo ##########"
  rm -f "$LOCK_WSL" "$LOCK_WSL.quien"

  local pid; pid="$($retener)"

  # Espero a que el lock EXISTA. Sin esto mediría la carrera equivocada.
  local esperado=0
  while [ ! -s "$LOCK_WSL" ] && [ "$esperado" -lt 200 ]; do
    sleep 0.1; esperado=$((esperado+1))
  done
  if [ ! -s "$LOCK_WSL" ]; then
    echo "  ABORTADA: el lock no llegó a existir (la condición NO se dio)"
    kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null
    echo; return
  fi

  # Registro que la condición SÍ se dio, no sólo el resultado (trampa 38).
  cat "$LOCK_WSL.quien" 2>/dev/null | sed 's/^/  /'
  local vivo_antes="no"; kill -0 "$pid" 2>/dev/null && vivo_antes="SI"
  echo "  lock_aparecio_en=$((esperado*100))ms  dueño_vivo_ANTES=$vivo_antes"
  $evaluar | sed 's/^/  /'
  local vivo_despues="no"; kill -0 "$pid" 2>/dev/null && vivo_despues="SI"
  echo "  dueño_vivo_DESPUES=$vivo_despues"
  if [ "$vivo_antes" != "SI" ] || [ "$vivo_despues" != "SI" ]; then
    echo "  ⚠ CELDA NO VÁLIDA: el dueño no estuvo vivo toda la evaluación"
  fi

  kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null
  echo
}

celda "A · retiene Git Bash -> evalúa Git Bash  (CONTROL POSITIVO)" ret_git ev_git
celda "B · retiene Git Bash -> evalúa WSL2"                         ret_git ev_wsl
celda "C · retiene WSL2     -> evalúa Git Bash"                     ret_wsl ev_git
celda "D · retiene WSL2     -> evalúa WSL2   (¿se excluye consigo mismo?)" ret_wsl ev_wsl

rm -f "$LOCK_WSL" "$LOCK_WSL.quien"
echo "lock de sonda borrado."

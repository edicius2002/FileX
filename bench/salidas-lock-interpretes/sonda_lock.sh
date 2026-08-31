#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Sonda: ¿el lock de GPU de `bench/lib/harness.sh` excluye entre INTÉRPRETES?
#
# El lock guarda dentro lo que hace falta para saber si su dueño sigue vivo:
#     etiqueta<TAB>pid_msys<TAB>winpid<TAB>imagen<TAB>epoch<TAB>raiz
# y `_gpu_dueno_vivo()` lo comprueba con `tasklist`. La pregunta es qué pasa
# cuando quien ESCRIBE el lock y quien lo EVALÚA no son el mismo intérprete.
#
# Dos modos, para poder cruzarlos desde fuera:
#   retener <fichero> <s> -> escribe el lock con la MISMA lógica que gpu_acquire
#                            y SIGUE VIVO <s> segundos
#   evaluar <fichero>     -> carga el harness y llama a _gpu_dueno_vivo
#
# ⚠ El dueño tiene que seguir VIVO mientras se le evalúa. Una primera versión
# tenía un modo `escribir` que salía en cuanto escribía: las CUATRO celdas daban
# «huérfano», y con razón —el dueño estaba muerto—, así que la sonda no medía el
# cruce de intérpretes sino su propia coreografía. Lo destapó el control
# positivo (trampa 38: un arnés que mide la carrera equivocada).
#
# No toca el lock real: trabaja sobre el fichero que se le pase.
# ─────────────────────────────────────────────────────────────────────────────

set -u

modo="${1:-}"
lock="${2:-}"
[ -z "$modo" ] || [ -z "$lock" ] && { echo "uso: sonda_lock.sh escribir|evaluar <fichero>"; exit 9; }

# El harness vive en D:. Cada intérprete lo ve por una ruta distinta.
for cand in /mnt/d/Work/research/FileX/bench/lib/harness.sh \
            /d/Work/research/FileX/bench/lib/harness.sh; do
  [ -f "$cand" ] && { HARNESS="$cand"; break; }
done
[ -z "${HARNESS:-}" ] && { echo "NO_ENCUENTRO_HARNESS"; exit 9; }

sistema="$(uname -s)"

case "$modo" in
  retener)
    segundos="${3:-30}"
    # Copia literal de las tres líneas de gpu_acquire que construyen la línea.
    winpid="$(cat /proc/$$/winpid 2>/dev/null)"; : "${winpid:=$$}"
    imagen="$(basename "${BASH:-bash}")"
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
      "sonda" "$$" "$winpid" "$imagen" "$(date +%s)" "${PWD}" > "$lock"
    echo "escrito_por=$sistema pid_shell=$$ winpid=$winpid imagen=$imagen" > "$lock.quien"
    # Sigo vivo: el dueño de un lock que se evalúa tiene que estar vivo.
    sleep "$segundos"
    ;;

  evaluar)
    export GPU_LOCK="$lock"
    # shellcheck source=/dev/null
    source "$HARNESS" >/dev/null 2>&1 || { echo "NO_PUDE_CARGAR_HARNESS"; exit 9; }
    GPU_LOCK="$lock"   # el harness lo fija con :- ; lo reafirmo por claridad

    echo "evaluado_por=$sistema"
    echo "  campo3_winpid=$(_gpu_lock_campo 3)  campo4_imagen=$(_gpu_lock_campo 4)"
    if _gpu_dueno_vivo; then
      echo "  VEREDICTO=DUENO_VIVO (rc=0) -> respeta el lock"
    else
      echo "  VEREDICTO=HUERFANO  (rc=1) -> BORRA el lock y entra"
    fi
    ;;

  *) echo "modo desconocido: $modo"; exit 9 ;;
esac

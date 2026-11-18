#!/usr/bin/env bash
# Stop: si hay trabajo sin anotar en PROGRESS.md, pide al agente (una vez) que
# lo anote antes de terminar. Ver AGENTS.md §1.
entrada=$(cat)
# Si ya se le pidió en este mismo ciclo, no insistir (evita bucles).
if printf '%s' "$entrada" | grep -Eq '"stop_hook_active"[[:space:]]*:[[:space:]]*true'; then
  exit 0
fi
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

# PROGRESS.md ya modificado y sin commit: el trabajo se está anotando.
[ -n "$(git status --porcelain -- PROGRESS.md)" ] && exit 0

motivo=""
if [ -n "$(git status --porcelain -- . ':(exclude)PROGRESS.md')" ]; then
  motivo="hay cambios sin commit"
else
  ultimo=$(git log -1 --format=%H -- PROGRESS.md)
  if [ -n "$ultimo" ] && [ -n "$(git rev-list "$ultimo"..HEAD)" ]; then
    motivo="hay commits posteriores al último cambio de PROGRESS.md"
  fi
fi
[ -z "$motivo" ] && exit 0

cat <<JSON
{"decision": "block", "reason": "Antes de terminar: $motivo y PROGRESS.md no lo refleja. Si se ha hecho trabajo (código, docs, PRs, decisiones), actualiza en PROGRESS.md el Estado actual, los Próximos pasos y la entrada de hoy del Registro (AGENTS.md §1). Si de verdad no hay nada que anotar (p. ej. solo una pregunta), termina sin cambios."}
JSON
exit 0

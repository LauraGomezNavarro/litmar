#!/usr/bin/env bash
# SessionStart: inyecta en el contexto el estado de PROGRESS.md y de git.
# Lo que este script escribe en stdout lo recibe el agente al empezar.
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

echo "=== Memoria del proyecto (hook SessionStart; flujo en AGENTS.md §1) ==="
if [ -f PROGRESS.md ]; then
  # Todo hasta el registro, más las dos últimas entradas del registro.
  awk '
    /^## Registro de sesiones/ { registro = 1; print; next }
    registro && /^### / { entradas++ }
    !registro || entradas <= 2 { print }
  ' PROGRESS.md
else
  echo "Falta PROGRESS.md: créalo siguiendo AGENTS.md §1."
fi

if git rev-parse --git-dir >/dev/null 2>&1; then
  echo
  echo "=== Git (sin fetch: ejecuta 'git fetch origin' y 'gh pr list') ==="
  git status -sb | head -20
  echo "Últimos commits:"
  git log --oneline -5
fi
exit 0

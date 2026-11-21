#!/usr/bin/env bash
# Remove this isolated installation. Existing ~/.claude files are never touched.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MAGPIE="${MAGPIE:-/Applications/Magpie.app/Contents/MacOS/magpie}"
ZSHRC="$HOME/.zshrc"
ALIAS_BEGIN="# >>> commlaude isolated launcher >>>"
ALIAS_END="# <<< commlaude isolated launcher <<<"
DRY_RUN=0
ASSUME_YES=0
REMOVE_MAGPIE=0

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --yes|-y) ASSUME_YES=1 ;;
    --magpie) REMOVE_MAGPIE=1 ;;
    --help|-h)
      printf 'Usage: %s [--dry-run] [--yes] [--magpie]\n' "$0"
      printf '  --dry-run  list actions without changing anything\n'
      printf '  --yes      do not ask for confirmation\n'
      printf '  --magpie   also remove the six group/role-* Magpie groups\n'
      exit 0
      ;;
    *) printf 'Unknown option: %s\n' "$arg" >&2; exit 2 ;;
  esac
done

if [[ ! -f "$ROOT/.commlaude-installation" ]] \
  || ! grep -Fxq 'installation=commlaude-isolated-orchestra' "$ROOT/.commlaude-installation" \
  || [[ "$ROOT" == "/" || "$ROOT" == "$HOME" ]]; then
  printf 'Safety check failed: expected a marked, non-home installation at %s.\n' "$ROOT" >&2
  exit 1
fi

PATHS=(
  "$ROOT/bin"
  "$ROOT/scripts"
  "$ROOT/tests"
  "$ROOT/.claude"
  "$ROOT/.orchestra"
  "$ROOT/.smoke"
  "$ROOT/logs"
  "$ROOT/setup-magpie.sh"
)
ROLE_GROUPS=(role-communicator role-architect role-supervisor role-worker-code role-worker-long role-auto-mode)

printf 'This removes the isolated Claude Code configuration, sessions, and run artifacts in:\n  %s\n' "$ROOT"
printf 'It does not touch %s/.claude or change Magpie main/tier/subagent bindings.\n' "$HOME"
printf '\nLocal paths to remove:\n'
for path in "${PATHS[@]}"; do
  [[ -e "$path" ]] && printf '  %s\n' "$path"
done
if [[ -f "$ZSHRC" ]] && grep -Fq "$ALIAS_BEGIN" "$ZSHRC"; then
  printf '\nShell alias to remove: commlaude in %s\n' "$ZSHRC"
else
  printf '\nNo marked commlaude alias found in %s.\n' "$ZSHRC"
fi
if (( REMOVE_MAGPIE )); then
  printf '\nMagpie groups to remove: %s\n' "${ROLE_GROUPS[*]}"
else
  printf '\nMagpie role groups will be left intact (add --magpie to remove them).\n'
fi
printf 'PLAN.md, README.md, docs/, backups/, uninstall.sh, and the rollback profile record are kept.\n'

if (( DRY_RUN )); then
  printf '\nDry run only; nothing changed.\n'
  exit 0
fi
if (( ! ASSUME_YES )); then
  printf '\nContinue? [y/N] '
  read -r answer
  [[ "$answer" == "y" || "$answer" == "Y" ]] || { printf 'Cancelled.\n'; exit 0; }
fi

if [[ -f "$ZSHRC" ]] && grep -Fq "$ALIAS_BEGIN" "$ZSHRC"; then
  python3 -I - "$ZSHRC" "$ALIAS_BEGIN" "$ALIAS_END" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
begin, end = sys.argv[2:4]
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
output = []
inside = False
for line in lines:
    stripped = line.rstrip("\r\n")
    if stripped == begin:
        inside = True
        continue
    if inside:
        if stripped == end:
            inside = False
        continue
    output.append(line)
if inside:
    print("Refusing to modify zshrc: alias block has no end marker.", file=sys.stderr)
    raise SystemExit(1)
path.write_text("".join(output), encoding="utf-8")
PY
  printf 'Removed marked commlaude alias from %s\n' "$ZSHRC"
fi

for path in "${PATHS[@]}"; do
  if [[ -e "$path" ]]; then
    rm -rf -- "$path"
    printf 'Removed %s\n' "$path"
  fi
done

if (( REMOVE_MAGPIE )); then
  if [[ ! -x "$MAGPIE" ]]; then
    printf 'Magpie not found at %s; local files were removed but groups remain.\n' "$MAGPIE" >&2
    exit 1
  fi
  "$MAGPIE" group rm "${ROLE_GROUPS[@]}"
  printf 'Removed orchestra Magpie groups.\n'
fi

printf '\nUninstall complete. No global Claude Code settings were modified.\n'
if [[ -f "$ROOT/.magpie-setup-state" ]]; then
  printf 'The Magpie snapshot name remains in %s for optional manual restoration.\n' "$ROOT/.magpie-setup-state"
fi

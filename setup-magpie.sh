#!/usr/bin/env bash
# User-run Magpie setup. It creates role groups only; no Claude binding is changed.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MAGPIE="${MAGPIE:-/Applications/Magpie.app/Contents/MacOS/magpie}"
STATE="$ROOT/.magpie-setup-state"
ROLE_GROUPS=(role-communicator role-architect role-supervisor role-worker-code role-smart-worker role-auto-mode)

if [[ ! -x "$MAGPIE" ]]; then
  printf 'Magpie not found at %s; set MAGPIE to its executable.\n' "$MAGPIE" >&2
  exit 1
fi
"$MAGPIE" status --json >/dev/null

if [[ ! -f "$STATE" ]]; then
  existing="$("$MAGPIE" groups 2>/dev/null || true)"
  for group in "${ROLE_GROUPS[@]}"; do
    if grep -Fq "group/$group" <<<"$existing"; then
      printf 'Refusing to replace pre-existing group/%s.\n' "$group" >&2
      printf 'Rename it or inspect it first; no groups were changed.\n' >&2
      exit 1
    fi
  done

  PROFILE="before-orchestra-$(date -u +%Y%m%dT%H%M%SZ)"
  printf 'Saving Magpie rollback profile: %s\n' "$PROFILE"
  "$MAGPIE" save "$PROFILE"
  umask 077
  printf 'profile=%s\ncreated_at=%s\n' "$PROFILE" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >"$STATE"
else
  printf 'Existing setup state found; refreshing only the six orchestra groups.\n'
fi

# Reference defaults for the six semantic role groups. Override any group via
# environment variables (comma-separated model IDs in priority order) to adapt
# to your own provider/model pool without editing agents or skills.
ROLE_COMMUNICATOR_MODELS="${ROLE_COMMUNICATOR_MODELS:-agy-cli/gemini-4-neon,agy-cli/claude-sonnet-5-5}"
ROLE_ARCHITECT_MODELS="${ROLE_ARCHITECT_MODELS:-codex/gpt-6.2-astra:xhigh,codex/gpt-6.2-sol:high,agy-cli/claude-opus-5-5}"
ROLE_SUPERVISOR_MODELS="${ROLE_SUPERVISOR_MODELS:-kimi/k3.1-pro,agy-cli/gemini-4-neon,agy-cli/claude-opus-5-5}"
ROLE_WORKER_CODE_MODELS="${ROLE_WORKER_CODE_MODELS:-agy-cli/gemini-4-hydrogen,deepseek/deepseek-flash}"
ROLE_SMART_WORKER_MODELS="${ROLE_SMART_WORKER_MODELS:-kimi/k3.1-pro,codex/gpt-6.2-sol:high}"
ROLE_AUTO_MODE_MODELS="${ROLE_AUTO_MODE_MODELS:-deepseek/deepseek-flash,zcode/GLM-5.3-Flash}"

"$MAGPIE" group add role-communicator \
  "models=$ROLE_COMMUNICATOR_MODELS" \
  routing=order stays=session

"$MAGPIE" group add role-architect \
  "models=$ROLE_ARCHITECT_MODELS" \
  routing=order stays=session

"$MAGPIE" group add role-supervisor \
  "models=$ROLE_SUPERVISOR_MODELS" \
  routing=order stays=session

"$MAGPIE" group add role-worker-code \
  "models=$ROLE_WORKER_CODE_MODELS" \
  routing=order stays=auto

"$MAGPIE" group add role-smart-worker \
  "models=$ROLE_SMART_WORKER_MODELS" \
  routing=order stays=session

"$MAGPIE" group add role-auto-mode \
  "models=$ROLE_AUTO_MODE_MODELS" \
  routing=order stays=off

printf '\nCreated/verified role groups:\n'
"$MAGPIE" groups
printf '\nDone. Existing Magpie main, tier, and subagent bindings were not changed.\n'
printf 'Next: %s/bin/claude-orchestra\n' "$ROOT"

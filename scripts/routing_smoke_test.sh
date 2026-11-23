#!/usr/bin/env bash
# Live routing probe: invokes all four subagents once through the isolated launcher.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
MAGPIE="${MAGPIE:-/Applications/Magpie.app/Contents/MacOS/magpie}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SMOKE="$ROOT/.smoke/routing-$STAMP"
mkdir -p "$SMOKE"

ROLE_GROUPS=(role-communicator role-architect role-supervisor role-worker-code role-smart-worker)
GROUP_LIST="$("$MAGPIE" groups 2>/dev/null)"
for group in "${ROLE_GROUPS[@]}"; do
  if ! grep -Fq "group/$group" <<<"$GROUP_LIST"; then
    printf 'Missing group/%s. Run %s/setup-magpie.sh first.\n' "$group" "$ROOT" >&2
    exit 1
  fi
done

START="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '%s\n' "$START" >"$SMOKE/started-at.txt"
PROMPT='This is a routing smoke test, not an engineering task. Use the Agent tool once for each of these four subagent types: astra-architect, kimi-supervisor, worker, smart-worker. Make all four independent Agent calls in the same message. Give each agent this exact prompt: "Routing probe only: return OK without inspecting or changing files." Do not invoke any skill and do not perform other work. After the calls finish, report one line per agent with its returned status.'

printf 'Running live probe; this makes model requests through Magpie.\n'
if ! (cd "$SMOKE" && "$ROOT/bin/claude-orchestra" \
  --print --output-format json --allowedTools Agent -- "$PROMPT" \
  >"$SMOKE/result.json" 2>"$SMOKE/stderr.log"); then
  printf 'Claude Code probe failed. See %s/stderr.log\n' "$SMOKE" >&2
  exit 1
fi

python3 -I - "$SMOKE/result.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    result = json.loads(path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as error:
    print(f"Cannot parse probe result: {error}", file=sys.stderr)
    raise SystemExit(1)
print(result.get("result", "No result text returned."))
if result.get("is_error"):
    print("Claude Code reported an API error.", file=sys.stderr)
    raise SystemExit(1)
PY

"$ROOT/bin/orchestra-audit" --since "$START" | tee "$SMOKE/audit.md"

python3 -I - "$START" "${ROLE_GROUPS[@]}" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

since = datetime.fromisoformat(sys.argv[1].replace("Z", "+00:00"))
expected = {f"group/{name}" for name in sys.argv[2:]}
seen = set()
served = set()
path = Path.home() / ".config/magpie/usage.jsonl"
for line in path.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    try:
        row = json.loads(line)
        timestamp = datetime.fromisoformat(str(row.get("t", "")).replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.astimezone()
        if timestamp.astimezone(timezone.utc) < since:
            continue
    except (ValueError, TypeError):
        continue
    requested = row.get("req") or row.get("requested")
    if requested in expected:
        seen.add(requested)
        if row.get("served"):
            served.add(str(row["served"]))
missing = sorted(expected - seen)
print("Role groups observed:", ", ".join(sorted(seen)) or "none")
print("Upstream models observed:", ", ".join(sorted(served)) or "none")
if missing:
    print("Missing role requests: " + ", ".join(missing), file=sys.stderr)
    raise SystemExit(1)
print("PASS: all five role groups emitted requests; inspect served models above for fallback attribution.")
PY

printf 'Smoke artifacts: %s\n' "$SMOKE"

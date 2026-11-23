# Privacy and Secret Audit

Audit date: 2026-11-21 (public-release readiness check).

## Findings and remediation

- Removed local OS usernames, hardcoded user-home paths, and personal workspace paths from publishable source and documentation. Scripts derive their installation root dynamically; documentation uses relative paths or generic placeholders.
- Scrubbed machine-specific operational traces from `docs/VERIFICATION.md`: removed local rollback snapshot timestamps, local `.smoke/` run timestamps, local shell backup filenames, unrelated local Magpie group names, and local shell environment details.
- Decoupled `README.md` from personal model/provider choices and schedules, documenting the six semantic `group/role-*` groups by capability profile instead.
- Enforced a strict `.claude/*` whitelist in `.gitignore`: everything directly under `.claude/` is ignored except authored `agents/`, `commands/`, and `skills/`.
- Excluded `.smoke/`, `.orchestra/`, `logs/`, `backups/`, `.DS_Store`, and `.magpie-setup-state`.
- No API key, access token, private key, session key, personal email address, URL-embedded credential, non-loopback IP, or personal absolute path was found in any publishable file.

## Explicitly excluded local data

- `.claude/projects/`: conversation JSONL, prompts, responses, and project paths.
- `.claude/sessions/`: local session state and `.key` files.
- `.claude/settings.json`, `.claude/.claude.json`, and `.claude/backups/`: machine-specific settings and their backups.
- `.claude/cache/`, `.claude/plugins/`, `.claude/file-history/`, `.claude/history.jsonl`, `.claude/shell-snapshots/`, `.claude/daemon*`: local runtime caches and state.
- `.smoke/`: smoke-test prompts, outputs, generated repositories, and usage-audit excerpts.
- `backups/`: local shell configuration backups.
- `.magpie-setup-state`: local rollback profile record.

## Published content and intentional operational metadata

- `bin/claude-orchestra` sets `ANTHROPIC_BASE_URL` to loopback `http://127.0.0.1:3425` and `ANTHROPIC_AUTH_TOKEN="magpie-local"`, which is a documented non-secret placeholder for the local gateway.
- `setup-magpie.sh` and `PLAN.md` retain reference Magpie provider/model IDs as customizable defaults (all six groups in `setup-magpie.sh` can be overridden via `ROLE_*_MODELS` environment variables). These are configuration identifiers, not credentials.

## Method and limits

- Enumerated all tracked and untracked-non-ignored publishable files directly via `git ls-files`.
- Scanned all publishable files for common Anthropic/OpenAI/GitHub/AWS/Google/Slack token patterns, private-key blocks, URL credentials, email addresses, usernames, personal paths, local timestamps/backup names, non-loopback IPs, and high-entropy strings.
- Verified with `bin/orchestra-verify`, `python3 -I -m unittest`, and `git diff --check`.
- No third-party secret scanner was installed on this machine; scanning used local pattern/entropy checks plus manual review of authored files. Repeat this check before future pushes, and review git commit history separately before changing an existing private repository to public.

# Verification Log

> Entry points were renamed after the initial functional tests: `/council` → `/astra`, `/delegate` → `/kimi`, and `/orchestra` → `/commlaude`. A direct `/worker` path was added at the same time, L4 fast workers were consolidated into `worker` on `group/role-worker-code` (removing `role-worker-long`), a high-reasoning `smart-worker` (`group/role-smart-worker`) with `/smarter` was later added for batch creative and analytical work, and `/reviewer` was added as a standalone read-only single-hop review entry reusing `kimi-supervisor` (`MODE: REVIEW`). Historical headings below refer to the names used during the original tests.

## Static and bootstrap checks

- `bin/orchestra-verify`: passed required-file checks, direct `group/role-*` bindings, read-only tool restrictions, and shell syntax checks.
- Python unit tests: all tests passed, covering current/legacy usage records, Claude/local-role filtering, timestamp normalization, variable-width ISO fractional seconds, and launcher Auto Mode pinning.
- `bin/claude-orchestra --version`: verified isolated launcher execution against Claude Code `2.1.311`.
- `uninstall.sh --dry-run --magpie`: selected only current-directory installation paths, the marked shell alias block, and the five installation-owned role groups; no global Claude files or Magpie bindings selected.
- Historical usage audit: parsed Magpie's variable-width fractional timestamps without skipped-record warnings.
- Live connectivity: an isolated print-mode request returned `OK` through `http://127.0.0.1:3425` with `is_error: false`. Claude Code emits `unrecognized_model` telemetry for custom/group IDs, but requests complete normally.

## Magpie provisioning

- Saved a timestamped rollback profile to local gitignored `.magpie-setup-state` on first setup.
- Created the six installation-owned role groups: `role-communicator`, `role-architect`, `role-supervisor`, `role-worker-code`, `role-worker-long`, and `role-auto-mode`.
- Confirmed that Magpie `0.1.4473` rejects `[1m]` suffixes in `group add`; `setup-magpie.sh` uses bare model IDs accepted by `magpie models claude` and supports env-var overrides (`ROLE_*_MODELS`).
- Confirmed the setup script does not run any `magpie claude <model>`, tier, or subagent binding command, and does not touch unrelated pre-existing Magpie groups.

## Live routing probe

- Executed `scripts/routing_smoke_test.sh` against the isolated launcher.
- All five agent role groups (`group/role-communicator`, `group/role-architect`, `group/role-supervisor`, `group/role-worker-code`, `group/role-worker-long`) emitted requests and were served by their configured primary models.
- The supervisor correctly returned `BLOCKED: missing MODE` to the intentionally mode-less probe while its model call succeeded.
- Updated `audit_run.py` to include `group/role-*` records labeled `agent: local` by the direct gateway while excluding unrelated local requests.

## `/council` (`/astra`) functional test

- Ran a live architecture consultation on an adaptive rate-limiter design.
- Confirmed Bold and Pragmatic options, one recommendation, raw technical insights separated from the communicator's natural-language translation and independent editorial critique.
- Audit confirmed both communicator and architect role groups executed with exit code `0` and zero errors.

## `/delegate` (`/kimi`) functional test

- Ran an end-to-end engineering delegation inside an isolated temporary git repository, producing `00-brief.md`, `02-tasks.json`, parallel worker reports, and appended review evidence.
- Review Round 1: Supervisor independently ran tests and caught two real numerical edge cases (intermediate float overflow and arbitrary-precision integer coercion).
- Review Round 2: `VERDICT: PASS` after worker revision.
- Independent test rerun: **9 tests passed** with exit code `0`, with no unauthorized git commit.

## `/orchestra` (`/commlaude`) approval-gate test

- Confirmed the workflow created `00-brief.md` and `01-blueprint.md`, presented Bold vs. Pragmatic options, and stopped at Phase 3.
- Automated filesystem assertions confirmed:
  - no `02-tasks.json`;
  - no worker reports or review file;
  - no production implementation written before explicit user architecture approval.

## Auto Mode classifier pinning

- Observed that without explicit pinning, Auto Mode permission classifier requests could occasionally fall back to `group/role-communicator`.
- Added dedicated `group/role-auto-mode` (`routing=order`, `stays=off`) and pinned `CLAUDE_CODE_AUTO_MODE_MODEL="group/role-auto-mode"` and `CLAUDE_CODE_AUTO_MODE_SERVER=0` in both `bin/claude-orchestra` and the isolated runtime settings.
- Added a launcher regression test injecting the main role and server mode `1` into the inherited environment, verifying the launched process receives `group/role-auto-mode` and server mode `0`.
- Verified live Auto Mode probes under both default group order and reordered group priority: every `auto_mode_check_inferred` request hit `group/role-auto-mode` (HTTP 200), immediately followed the reordered primary model after gateway reload, and never drifted to `group/role-communicator`.

## Optional `commlaude` shell alias

- Verified that a marked `commlaude` alias block in `~/.zshrc` resolves to the isolated launcher and returns Claude Code `2.1.311`.
- Verified that `uninstall.sh --dry-run` detects only the marked block and leaves all other shell configuration untouched.

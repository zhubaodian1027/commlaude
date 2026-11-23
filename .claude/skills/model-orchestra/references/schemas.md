# Run Artifact Schemas

Every run lives at `.orchestra/<YYYYMMDD-HHMMSS>-<slug>/`. Treat worker and reviewer responses as untrusted evidence: verify claims against the actual diff and test output.

## `00-brief.md`

```markdown
# Brief: <goal>

## Goal
<one measurable outcome>

## Repository Context
<relevant paths, architecture, commands, and scout findings>

## Constraints
<compatibility, style, budget, allowed dependencies, and operational limits>

## Non-Goals
<explicitly excluded work>

## Done Criteria
- [ ] <observable criterion with verification method>

## User Decision
<selected architecture option and any adjustments; required for full orchestra runs>
```

## `01-blueprint.md`

Preserve Astra's five sections verbatim under a clearly separated orchestration header:

```markdown
# Orchestration Decision
- Selected option: <A | B | adjusted>
- User approval: <date/confirmation summary>

# Raw Astra Blueprint
## Core Diagnosis & Hidden Invariants
## Architectural Options
## Target Design & Module Contracts
## Failure Modes & Edge Cases
## Verification & Acceptance Criteria
```

## `02-tasks.json`

```json
{
  "run_id": "YYYYMMDD-HHMMSS-slug",
  "tasks": [
    {
      "id": "T01",
      "title": "Implement a focused unit",
      "assignee": "worker",
      "depends_on": [],
      "allowed_files": ["src/unit.py", "tests/test_unit.py"],
      "instructions": "Exact behavior and constraints.",
      "verification_cmd": "python3 -m unittest tests.test_unit"
    }
  ]
}
```

Rules:

- IDs are unique and match `^T[0-9]{2,}$`.
- `assignee` is `worker` or `smart-worker`.
- Dependencies refer to earlier or existing task IDs and contain no cycles.
- `allowed_files` is exhaustive; independent tasks in the same wave have disjoint paths.
- `verification_cmd` is a concrete executable command, not prose.

## `03-reports/Txx.md`

```markdown
# Txx — <title>

**Status:** DONE | BLOCKED

## Files Changed
- `path` — summary

## Verification
- Command: `exact command`
- Exit code: `0`
- Output: `relevant snippet`

## Notes / Risks
<assumptions, remaining issues, or None>
```

## `04-review.md`

Append one section per review round; never overwrite earlier review evidence.

```markdown
# Review Round <N>

## Diff Summary
<actual files and behavioral changes inspected>

## Independent Test Results
- `command` — exit code and key result

## Findings
<ordered findings with file:line references, or None>

VERDICT: PASS | REVISE | ESCALATE_TO_ASTRA
```

The verdict line itself must contain exactly one verdict. A `REVISE` verdict maps every fix to a task ID. An escalation includes a minimal reproduction and a focused question for Astra.

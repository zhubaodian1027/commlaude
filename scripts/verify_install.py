#!/usr/bin/env python3
"""Static checks for the isolated orchestration installation."""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = {
    "astra-architect": "group/role-architect",
    "kimi-supervisor": "group/role-supervisor",
    "worker": "group/role-worker-code",
    "smart-worker": "group/role-smart-worker",
}
REQUIRED = [
    *(ROOT / ".claude/agents" / f"{name}.md" for name in AGENTS),
    ROOT / ".claude/skills/model-orchestra/SKILL.md",
    ROOT / ".claude/skills/model-orchestra/references/schemas.md",
    ROOT / ".claude/skills/model-orchestra/scripts/audit_run.py",
    ROOT / ".claude/skills/astra-council/SKILL.md",
    ROOT / ".claude/skills/fast-delegate/SKILL.md",
    ROOT / ".claude/skills/worker-direct/SKILL.md",
    ROOT / ".claude/skills/smart-worker-direct/SKILL.md",
    ROOT / ".claude/commands/commlaude.md",
    ROOT / ".claude/commands/astra.md",
    ROOT / ".claude/commands/kimi.md",
    ROOT / ".claude/commands/worker.md",
    ROOT / ".claude/commands/smarter.md",
    ROOT / "bin/claude-orchestra",
    ROOT / "setup-magpie.sh",
    ROOT / "uninstall.sh",
]


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise ValueError(f"{path}: missing YAML frontmatter")
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line or line.startswith((" ", "#")):
            continue
        key, separator, value = line.partition(":")
        if separator:
            fields[key.strip()] = value.strip()
    return fields


def main() -> int:
    errors: list[str] = []
    for path in REQUIRED:
        if not path.is_file():
            errors.append(f"missing: {path.relative_to(ROOT)}")

    for obsolete in ("council.md", "delegate.md", "orchestra.md", "myclaude.md"):
        path = ROOT / ".claude/commands" / obsolete
        if path.exists():
            errors.append(f"obsolete command still present: {path.relative_to(ROOT)}")

    for obsolete_agent in ("worker-deepseek.md", "worker-hydrogen.md"):
        path = ROOT / ".claude/agents" / obsolete_agent
        if path.exists():
            errors.append(f"obsolete agent still present: {path.relative_to(ROOT)}")

    for name, model in AGENTS.items():
        path = ROOT / ".claude/agents" / f"{name}.md"
        if not path.is_file():
            continue
        try:
            fields = frontmatter(path)
            if fields.get("name") != name:
                errors.append(f"{path.name}: name must be {name}")
            if fields.get("model") != model:
                errors.append(f"{path.name}: model must be {model}")
            tools = {item.strip() for item in fields.get("tools", "").split(",")}
            if name in {"astra-architect", "kimi-supervisor"}:
                forbidden = tools & {"Edit", "Write", "MultiEdit"}
                if forbidden:
                    errors.append(f"{path.name}: read-only agent has {sorted(forbidden)}")
            if name == "kimi-supervisor" and "Bash" not in tools:
                errors.append("kimi-supervisor: Bash is required for independent tests")
            if not fields.get("description"):
                errors.append(f"{path.name}: description is empty")
        except ValueError as error:
            errors.append(str(error))

    for directory, skill in (
        ("model-orchestra", "model-orchestra"),
        ("astra-council", "astra-council"),
        ("fast-delegate", "fast-delegate"),
        ("worker-direct", "worker-direct"),
        ("smart-worker-direct", "smart-worker-direct"),
    ):
        path = ROOT / ".claude/skills" / directory / "SKILL.md"
        if path.is_file():
            try:
                fields = frontmatter(path)
                if fields.get("name") != skill:
                    errors.append(f"{path.relative_to(ROOT)}: wrong skill name")
                if not fields.get("description"):
                    errors.append(f"{path.relative_to(ROOT)}: description is empty")
            except ValueError as error:
                errors.append(str(error))

    audit = ROOT / ".claude/skills/model-orchestra/scripts/audit_run.py"
    if audit.is_file():
        try:
            ast.parse(audit.read_text(encoding="utf-8"), filename=str(audit))
        except SyntaxError as error:
            errors.append(f"audit_run.py: {error}")

    for script in (
        ROOT / "bin/claude-orchestra",
        ROOT / "bin/orchestra-audit",
        ROOT / "bin/orchestra-verify",
        ROOT / "setup-magpie.sh",
        ROOT / "uninstall.sh",
    ):
        if script.is_file():
            result = subprocess.run(
                ["bash", "-n", str(script)], capture_output=True, text=True, check=False
            )
            if result.returncode:
                errors.append(f"{script.relative_to(ROOT)}: {result.stderr.strip()}")

    launcher = ROOT / "bin/claude-orchestra"
    if launcher.is_file():
        text = launcher.read_text(encoding="utf-8")
        for required in (
            "CLAUDE_CONFIG_DIR",
            "CLAUDE_CODE_SUBAGENT_MODEL",
            "CLAUDE_CODE_AUTO_MODE_MODEL",
            "CLAUDE_CODE_AUTO_MODE_SERVER",
            "127.0.0.1:3425",
        ):
            if required not in text:
                errors.append(f"launcher missing isolation setting: {required}")

    if errors:
        print("Configuration verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"OK: {len(REQUIRED)} required files, agent routing, tool restrictions, and script syntax verified.")
    print(f"Isolated config: {ROOT / '.claude'}")
    print("Live Magpie routing is checked separately by scripts/routing_smoke_test.sh.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

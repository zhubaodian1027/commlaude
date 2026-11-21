from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / ".claude/skills/model-orchestra/scripts/audit_run.py"
SPEC = importlib.util.spec_from_file_location("audit_run", MODULE_PATH)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class AuditTests(unittest.TestCase):
    def test_current_and_legacy_record_shapes(self) -> None:
        rows = AUDIT.aggregate(
            [
                {
                    "t": "2026-11-20T01:00:00Z",
                    "agent": "claude",
                    "req": "group/role-supervisor",
                    "served": "k3.1-pro",
                    "in": 100,
                    "out": 20,
                    "reasoning": 5,
                    "cache_read": 50,
                    "ms": 1000,
                    "status": 200,
                },
                {
                    "time": "2026-11-20T01:01:00Z",
                    "agent": "claude",
                    "requested": "group/role-supervisor",
                    "served": "k3.1-pro",
                    "tokens": {"input_tokens": 30, "output_tokens": 10},
                    "ms": 500,
                    "status": 429,
                    "cost": 0.25,
                }
            ]
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["calls"], 2)
        self.assertEqual(row["input"], 130)
        self.assertEqual(row["output"], 30)
        self.assertEqual(row["reasoning"], 5)
        self.assertEqual(row["cache_read"], 50)
        self.assertEqual(row["errors"], 1)
        self.assertEqual(row["cost"], 0.25)
        self.assertIn("group/role-supervisor", AUDIT.markdown_table(rows))

    def test_timestamp_normalization(self) -> None:
        value = AUDIT.parse_timestamp("2026-11-20T08:00:00+08:00")
        self.assertEqual(value, datetime(2026, 11, 20, tzinfo=timezone.utc))
        short_fraction = AUDIT.parse_timestamp("2026-10-27T21:08:18.85944+08:00")
        self.assertEqual(short_fraction.microsecond, 859440)
        long_fraction = AUDIT.parse_timestamp("2026-10-27T21:08:18.859449123+08:00")
        self.assertEqual(long_fraction.microsecond, 859449)

    def test_cli_filters_agents_and_time(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            log = Path(directory) / "usage.jsonl"
            records = [
                {"t": "2026-11-20T01:00:00Z", "agent": "claude", "req": "a", "served": "b"},
                {"t": "2026-11-20T01:00:00Z", "agent": "codex", "req": "x", "served": "y"},
                {"t": "2026-11-20T01:00:00Z", "agent": "local", "req": "group/role-architect", "served": "gpt-6.2-astra"},
                {"t": "2026-11-20T01:00:00Z", "agent": "local", "req": "other/model", "served": "other"},
                {"t": "2026-11-19T01:00:00Z", "agent": "claude", "req": "old", "served": "old"},
            ]
            log.write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = AUDIT.main(["--log", str(log), "--since", "2026-11-20T00:00:00Z"])
            self.assertEqual(result, 0)
            self.assertIn("| a | b | 1 |", output.getvalue())
            self.assertIn("| group/role-architect | gpt-6.2-astra | 1 |", output.getvalue())
            self.assertNotIn("| x | y |", output.getvalue())
            self.assertNotIn("| other/model | other |", output.getvalue())
            self.assertNotIn("| old | old |", output.getvalue())


if __name__ == "__main__":
    unittest.main()

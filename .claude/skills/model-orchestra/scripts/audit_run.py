#!/usr/bin/env python3
"""Summarize Magpie routing metadata without reading prompts or credentials."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


def parse_timestamp(value: Any) -> datetime:
    """Parse an ISO-8601 or epoch timestamp and normalize it to UTC."""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("missing timestamp")
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    # Magpie/Go emits variable-width fractional seconds; Python accepts at most 6.
    text = re.sub(
        r"\.(\d+)(?=(?:[+-]\d{2}:?\d{2})?$)",
        lambda match: "." + match.group(1)[:6].ljust(6, "0"),
        text,
    )
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        epoch = float(text)
        return datetime.fromtimestamp(epoch, tz=timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone(timezone.utc)


def record_time(record: dict[str, Any]) -> datetime:
    for key in ("t", "time", "timestamp", "created_at"):
        if key in record:
            return parse_timestamp(record[key])
    raise ValueError("record has no supported timestamp")


def numeric(record: dict[str, Any], *keys: str) -> float:
    containers = [record]
    if isinstance(record.get("tokens"), dict):
        containers.append(record["tokens"])
    for container in containers:
        for key in keys:
            value = container.get(key)
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                try:
                    return float(value)
                except ValueError:
                    pass
    return 0.0


def is_error(record: dict[str, Any]) -> bool:
    status = record.get("status")
    if isinstance(status, (int, float)):
        return not 200 <= int(status) < 300
    if status is None:
        return False
    return str(status).lower() not in {"200", "201", "202", "204", "ok", "success"}


def aggregate(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "calls": 0,
            "input": 0.0,
            "output": 0.0,
            "reasoning": 0.0,
            "cache_read": 0.0,
            "latency": 0.0,
            "errors": 0,
            "cost": 0.0,
            "has_cost": False,
        }
    )
    for record in records:
        requested = str(
            record.get("requested")
            or record.get("req")
            or record.get("model")
            or "(unknown)"
        )
        served = str(record.get("served") or record.get("model") or "(unknown)")
        row = groups[(requested, served)]
        row["requested"] = requested
        row["served"] = served
        row["calls"] += 1
        row["input"] += numeric(record, "in", "input", "input_tokens")
        row["output"] += numeric(record, "out", "output", "output_tokens")
        row["reasoning"] += numeric(record, "reasoning", "reasoning_tokens")
        row["cache_read"] += numeric(record, "cache_read", "cache_read_input_tokens")
        row["latency"] += numeric(record, "ms", "latency_ms")
        row["errors"] += int(is_error(record))
        if "cost" in record and isinstance(record["cost"], (int, float, str)):
            row["cost"] += numeric(record, "cost")
            row["has_cost"] = True
    return sorted(groups.values(), key=lambda row: (row["requested"], row["served"]))


def integer(value: float) -> str:
    return str(round(value))


def markdown_table(rows: list[dict[str, Any]]) -> str:
    headers = (
        "Requested",
        "Served",
        "Calls",
        "Input",
        "Output",
        "Reasoning",
        "Cache read",
        "Avg ms",
        "Errors",
        "Cost",
    )
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    totals = {
        "calls": 0,
        "input": 0.0,
        "output": 0.0,
        "reasoning": 0.0,
        "cache_read": 0.0,
        "latency": 0.0,
        "errors": 0,
        "cost": 0.0,
        "has_cost": False,
    }
    for row in rows:
        for key in totals:
            if key == "has_cost":
                totals[key] = totals[key] or row[key]
            else:
                totals[key] += row[key]
        values = (
            row["requested"].replace("|", "\\|"),
            row["served"].replace("|", "\\|"),
            str(row["calls"]),
            integer(row["input"]),
            integer(row["output"]),
            integer(row["reasoning"]),
            integer(row["cache_read"]),
            integer(row["latency"] / row["calls"]),
            str(row["errors"]),
            f"{row['cost']:.6f}" if row["has_cost"] else "—",
        )
        lines.append("| " + " | ".join(values) + " |")
    if rows:
        total_values = (
            "**Total**",
            "",
            str(totals["calls"]),
            integer(totals["input"]),
            integer(totals["output"]),
            integer(totals["reasoning"]),
            integer(totals["cache_read"]),
            integer(totals["latency"] / totals["calls"]),
            str(totals["errors"]),
            f"{totals['cost']:.6f}" if totals["has_cost"] else "—",
        )
        lines.append("| " + " | ".join(total_values) + " |")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Aggregate safe Magpie request metadata as a Markdown table."
    )
    parser.add_argument(
        "--since",
        help="ISO-8601 start time (default: 30 minutes ago); naive values use local time",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=Path("~/.config/magpie/usage.jsonl"),
        help="Magpie usage JSONL path (default: ~/.config/magpie/usage.jsonl)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="include all agents instead of only Claude agents and group/role-* requests",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        since = (
            parse_timestamp(args.since)
            if args.since
            else datetime.now(timezone.utc) - timedelta(minutes=30)
        )
    except (ValueError, OSError) as error:
        print(f"Invalid --since value: {error}", file=sys.stderr)
        return 2

    path = args.log.expanduser()
    selected: list[dict[str, Any]] = []
    skipped = 0
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    if not isinstance(record, dict):
                        raise ValueError("not an object")
                    requested = record.get("req") or record.get("requested") or ""
                    is_role_request = str(requested).startswith("group/role-")
                    is_claude_agent = "claude" in str(record.get("agent", "")).lower()
                    if not args.all and not (is_claude_agent or is_role_request):
                        continue
                    if record_time(record) < since:
                        continue
                    selected.append(record)
                except (ValueError, TypeError, json.JSONDecodeError, OSError):
                    skipped += 1
    except OSError as error:
        print(f"Cannot read usage log {path}: {error}", file=sys.stderr)
        return 1

    print(f"Usage since {since.isoformat()} ({'all agents' if args.all else 'Claude agents + role groups'})")
    print()
    if selected:
        print(markdown_table(aggregate(selected)))
    else:
        print("No matching Magpie usage records.")
    if skipped:
        print(f"\nSkipped {skipped} malformed or undated records.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

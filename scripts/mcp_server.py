#!/usr/bin/env python3
"""Minimal stdlib-only stdio MCP server exposing commlaude's isolated subagents."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = Path(os.environ.get("COMMLAUDE_LAUNCHER", str(ROOT / "bin/claude-orchestra")))
AGENTS_DIR = ROOT / ".claude/agents"
SUPPORTED_PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
DEFAULT_TIMEOUT = int(os.environ.get("COMMLAUDE_MCP_TIMEOUT", "600"))
DEFAULT_WRITE_PERM = os.environ.get("COMMLAUDE_MCP_PERMISSION_MODE", "auto")
READ_ONLY_DENY = ("Edit", "Write", "MultiEdit", "NotebookEdit")
STRICT_READ_ONLY_DENY = (*READ_ONLY_DENY, "Bash")
VALID_WRITE_PERMS = ("auto", "acceptEdits", "bypassPermissions")


def _load_agent_meta(agent: str) -> dict[str, str]:
    path = AGENTS_DIR / f"{agent}.md"
    if not path.is_file():
        return {}
    match = re.match(r"\A---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.DOTALL)
    if not match:
        return {}
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line or line.startswith((" ", "#")):
            continue
        key, sep, val = line.partition(":")
        if sep:
            meta[key.strip()] = val.strip()
    return meta


def _common_props(*, writable: bool = False) -> dict[str, Any]:
    props: dict[str, Any] = {
        "prompt": {"type": "string", "description": "Task or review prompt for the subagent."},
        "cwd": {"type": "string", "description": "Optional working directory (project root)."},
        "session_id": {"type": "string", "description": "Optional session_id from a prior call to --resume."},
        "timeout_seconds": {"type": "integer", "minimum": 10, "description": "Optional execution timeout in seconds."},
    }
    if writable:
        props["worktree"] = {
            "type": "boolean",
            "description": "Run the subagent in an isolated git worktree (--worktree).",
        }
        props["permission_mode"] = {
            "type": "string",
            "enum": list(VALID_WRITE_PERMS),
            "description": "Claude Code headless permission mode (default: auto).",
        }
    return props


TOOLS: list[dict[str, Any]] = [
    {
        "name": "ask_astra",
        "description": (
            "Invoke astra-architect (group/role-architect, strictly read-only + Web) "
            "for first-principles vs. pragmatic architectural blueprints and deep root-cause diagnosis."
        ),
        "inputSchema": {"type": "object", "properties": _common_props(), "required": ["prompt"]},
    },
    {
        "name": "run_supervisor",
        "description": (
            "Invoke kimi-supervisor (group/role-supervisor, read-only + safe Bash verification). "
            "Defaults to MODE: REVIEW for standalone or pipeline review; pass mode='DECOMPOSE' for 02-tasks.json."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                **_common_props(),
                "mode": {
                    "type": "string",
                    "enum": ["REVIEW", "DECOMPOSE"],
                    "description": "Supervisor mode (default: REVIEW).",
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "run_worker",
        "description": (
            "Invoke worker (group/role-worker-code) for scoped implementation, tests, docs, "
            "long-task launch/checks, or read-only scouting (mode='scout')."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                **_common_props(writable=True),
                "mode": {
                    "type": "string",
                    "enum": ["execution", "scout"],
                    "description": "Execution Mode (default) or strictly read-only Scout Mode.",
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "run_smart_worker",
        "description": (
            "Invoke smart-worker (group/role-smart-worker, effort=high, read/write + Web) "
            "for deep paper reading, literature synthesis, research writing, and complex analysis."
        ),
        "inputSchema": {
            "type": "object",
            "properties": _common_props(writable=True),
            "required": ["prompt"],
        },
    },
]

TOOL_SPECS: dict[str, dict[str, Any]] = {
    "ask_astra": {"agent": "astra-architect", "default_model": "group/role-architect", "writable": False},
    "run_supervisor": {"agent": "kimi-supervisor", "default_model": "group/role-supervisor", "writable": False},
    "run_worker": {"agent": "worker", "default_model": "group/role-worker-code", "writable": True},
    "run_smart_worker": {"agent": "smart-worker", "default_model": "group/role-smart-worker", "writable": True},
}


def _parse_claude_json(stdout: str) -> dict[str, Any] | None:
    text = stdout.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    for line in reversed(text.splitlines()):
        candidate = line.strip()
        if not candidate.startswith("{"):
            continue
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict) and ("result" in parsed or parsed.get("type") == "result"):
                return parsed
        except json.JSONDecodeError:
            continue
    return None


def _build_invocation(tool_name: str, args: dict[str, Any]) -> tuple[list[str], dict[str, str], str, Path, int, str]:
    spec = TOOL_SPECS[tool_name]
    agent = spec["agent"]
    meta = _load_agent_meta(agent)
    model = meta.get("model") or spec["default_model"]

    prompt = args.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("`prompt` must be a non-empty string.")

    cwd_arg = args.get("cwd")
    cwd = Path(cwd_arg).expanduser().resolve() if cwd_arg else Path.cwd()
    if not cwd.is_dir():
        raise ValueError(f"`cwd` is not an existing directory: {cwd}")

    timeout = args.get("timeout_seconds", DEFAULT_TIMEOUT)
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout < 10:
        raise ValueError("`timeout_seconds` must be an integer >= 10.")

    session_id = args.get("session_id")
    if session_id is not None and (not isinstance(session_id, str) or not session_id.strip()):
        raise ValueError("`session_id` must be a non-empty string when provided.")

    effective_prompt = prompt
    disallowed: tuple[str, ...] = ()
    perm_mode = "auto"

    if tool_name == "ask_astra":
        disallowed = STRICT_READ_ONLY_DENY
    elif tool_name == "run_supervisor":
        mode = args.get("mode", "REVIEW")
        if mode not in ("REVIEW", "DECOMPOSE"):
            raise ValueError("`mode` must be 'REVIEW' or 'DECOMPOSE'.")
        disallowed = READ_ONLY_DENY
        if not re.search(r"\bMODE:\s*(REVIEW|DECOMPOSE)\b", effective_prompt):
            effective_prompt = f"MODE: {mode}\n\n{effective_prompt}"
    elif tool_name == "run_worker":
        mode = args.get("mode", "execution")
        if mode not in ("execution", "scout"):
            raise ValueError("`mode` must be 'execution' or 'scout'.")
        if mode == "scout":
            disallowed = READ_ONLY_DENY
            if "scout mode" not in effective_prompt.lower():
                effective_prompt = f"Scout Mode (strictly read-only)\n\n{effective_prompt}"
        else:
            perm_mode = args.get("permission_mode", DEFAULT_WRITE_PERM)
    elif tool_name == "run_smart_worker":
        perm_mode = args.get("permission_mode", DEFAULT_WRITE_PERM)

    if perm_mode not in VALID_WRITE_PERMS:
        raise ValueError(f"`permission_mode` must be one of {VALID_WRITE_PERMS}.")

    cmd = [
        str(LAUNCHER),
        "-p",
        "--agent",
        agent,
        "--output-format",
        "json",
        "--permission-mode",
        perm_mode,
        "--permission-prompts",
        "none",
    ]
    if disallowed:
        cmd.extend(["--disallowedTools", ",".join(disallowed)])
    if spec["writable"] and args.get("worktree") is True:
        cmd.append("--worktree")
    if session_id:
        cmd.extend(["--resume", session_id.strip()])

    env = os.environ.copy()
    env["ORCHESTRA_MAIN_MODEL"] = model
    if meta.get("effort"):
        env["ORCHESTRA_EFFORT"] = meta["effort"]

    return cmd, env, effective_prompt, cwd, timeout, model


def execute_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    if tool_name not in TOOL_SPECS:
        return {"content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}], "isError": True}
    try:
        cmd, env, effective_prompt, cwd, timeout, model = _build_invocation(tool_name, args or {})
    except ValueError as exc:
        return {"content": [{"type": "text", "text": f"Invalid arguments: {exc}"}], "isError": True}

    agent = TOOL_SPECS[tool_name]["agent"]
    try:
        proc = subprocess.run(
            cmd,
            input=effective_prompt,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "content": [{"type": "text", "text": f"{agent} timed out after {timeout}s."}],
            "isError": True,
        }
    except OSError as exc:
        return {
            "content": [{"type": "text", "text": f"Failed to launch {LAUNCHER}: {exc}"}],
            "isError": True,
        }

    payload = _parse_claude_json(proc.stdout)
    if payload is None:
        detail = (proc.stderr or proc.stdout or f"exit code {proc.returncode}").strip()
        return {
            "content": [{"type": "text", "text": f"{agent} failed (exit {proc.returncode}):\n{detail[-4000:]}"}],
            "isError": True,
        }

    is_error = bool(payload.get("is_error")) or proc.returncode != 0
    header = [
        f"agent: {agent}",
        f"model: {model}",
        f"session_id: {payload.get('session_id', '')}",
        f"duration_ms: {payload.get('duration_ms', 0)}",
        f"num_turns: {payload.get('num_turns', 0)}",
    ]
    denials = payload.get("permission_denials") or []
    if denials:
        header.append(f"permission_denials: {json.dumps(denials, ensure_ascii=False)}")
    body = str(payload.get("result") or "").strip()
    if is_error and not body and proc.stderr.strip():
        body = proc.stderr.strip()[-2000:]
    text = f"[commlaude-mcp]\n" + "\n".join(header) + f"\n---\n{body}"
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def _read_message(stream: Any) -> tuple[dict[str, Any] | None, str]:
    while True:
        line = stream.readline()
        if not line:
            return None, "ndjson"
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith(b"content-length:"):
            length = int(stripped.split(b":", 1)[1].strip())
            while True:
                hdr = stream.readline()
                if not hdr or hdr in (b"\r\n", b"\n"):
                    break
            body = stream.read(length)
            return json.loads(body.decode("utf-8")), "lsp"
        return json.loads(stripped.decode("utf-8")), "ndjson"


def _write_message(stream: Any, lock: threading.Lock, msg: dict[str, Any], framing: str) -> None:
    encoded = json.dumps(msg, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with lock:
        if framing == "lsp":
            stream.write(f"Content-Length: {len(encoded)}\r\n\r\n".encode("ascii") + encoded)
        else:
            stream.write(encoded + b"\n")
        stream.flush()


def _handle_request(req: dict[str, Any]) -> dict[str, Any] | None:
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params") or {}
    if req_id is None:
        return None  # Notifications require no response.

    if method == "initialize":
        requested = params.get("protocolVersion")
        version = requested if requested in SUPPORTED_PROTOCOLS else SUPPORTED_PROTOCOLS[0]
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "commlaude-mcp", "version": "0.1.0"},
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        result = execute_tool(str(params.get("name", "")), params.get("arguments") or {})
        return {"jsonrpc": "2.0", "id": req_id, "result": result}
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def serve(stdin: Any = None, stdout: Any = None) -> int:
    in_stream = stdin or sys.stdin.buffer
    out_stream = stdout or sys.stdout.buffer
    lock = threading.Lock()
    threads: list[threading.Thread] = []

    while True:
        try:
            req, framing = _read_message(in_stream)
        except Exception as exc:  # noqa: BLE001
            _write_message(
                out_stream,
                lock,
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"Parse error: {exc}"}},
                "ndjson",
            )
            continue
        if req is None:
            break

        if req.get("method") == "tools/call" and req.get("id") is not None:
            def _run(message: dict[str, Any] = req, mode: str = framing) -> None:
                resp = _handle_request(message)
                if resp is not None:
                    _write_message(out_stream, lock, resp, mode)

            thread = threading.Thread(target=_run, daemon=False)
            thread.start()
            threads.append(thread)
        else:
            resp = _handle_request(req)
            if resp is not None:
                _write_message(out_stream, lock, resp, framing)

    for thread in threads:
        thread.join()
    return 0


if __name__ == "__main__":
    raise SystemExit(serve())

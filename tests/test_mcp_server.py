from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MCP_BIN = ROOT / "bin/commlaude-mcp"


def _make_fake_launcher(path: Path, *, sleep_sec: float = 0.0, fail: bool = False) -> None:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys, time\n"
        f"if {sleep_sec!r} > 0:\n"
        f"    time.sleep({sleep_sec!r})\n"
        "prompt = sys.stdin.read()\n"
        "sys.stderr.write('[claude-code:unrecognized_model] noise\\n')\n"
        f"if {fail!r}:\n"
        "    sys.stderr.write('simulated crash\\n')\n"
        "    sys.exit(2)\n"
        "out = {\n"
        "    'type': 'result',\n"
        "    'is_error': False,\n"
        "    'session_id': 'sess-1234',\n"
        "    'duration_ms': 42,\n"
        "    'num_turns': 1,\n"
        "    'permission_denials': [],\n"
        "    'result': json.dumps({\n"
        "        'argv': sys.argv[1:],\n"
        "        'model': os.environ.get('ORCHESTRA_MAIN_MODEL'),\n"
        "        'effort': os.environ.get('ORCHESTRA_EFFORT'),\n"
        "        'cwd': os.getcwd(),\n"
        "        'prompt': prompt,\n"
        "    }),\n"
        "}\n"
        "print(json.dumps(out))\n",
        encoding="utf-8",
    )
    path.chmod(0o700)


def _rpc_roundtrip(launcher: Path, messages: list[dict]) -> list[dict]:
    env = os.environ.copy()
    env["COMMLAUDE_LAUNCHER"] = str(launcher)
    payload = "\n".join(json.dumps(m) for m in messages) + "\n"
    proc = subprocess.run(
        [str(MCP_BIN)],
        input=payload,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]


def _extract_fake_result(resp: dict) -> dict:
    text = resp["result"]["content"][0]["text"]
    _, body = text.split("\n---\n", 1)
    return json.loads(body)


class McpServerTests(unittest.TestCase):
    def test_handshake_and_tools_list(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            fake = Path(tmp) / "fake-launcher"
            _make_fake_launcher(fake)
            resps = _rpc_roundtrip(
                fake,
                [
                    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}},
                    {"jsonrpc": "2.0", "method": "notifications/initialized"},
                    {"jsonrpc": "2.0", "id": 2, "method": "ping"},
                    {"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
                ],
            )
            self.assertEqual([r["id"] for r in resps], [1, 2, 3])
            self.assertEqual(resps[0]["result"]["protocolVersion"], "2025-03-26")
            self.assertEqual(resps[0]["result"]["serverInfo"]["name"], "commlaude-mcp")
            tool_names = [t["name"] for t in resps[2]["result"]["tools"]]
            self.assertEqual(tool_names, ["ask_astra", "run_supervisor", "run_worker", "run_smart_worker"])

    def test_role_routing_permissions_and_resume(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            temp = Path(tmp)
            fake = temp / "fake-launcher"
            workdir = temp / "repo"
            workdir.mkdir()
            _make_fake_launcher(fake)

            resps = _rpc_roundtrip(
                fake,
                [
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {"name": "ask_astra", "arguments": {"prompt": "Compare A vs B", "cwd": str(workdir)}},
                    },
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {"name": "run_supervisor", "arguments": {"prompt": "Check diff", "cwd": str(workdir)}},
                    },
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {
                            "name": "run_worker",
                            "arguments": {"prompt": "Scan repo", "mode": "scout", "cwd": str(workdir)},
                        },
                    },
                    {
                        "jsonrpc": "2.0",
                        "id": 4,
                        "method": "tools/call",
                        "params": {
                            "name": "run_smart_worker",
                            "arguments": {
                                "prompt": "Synthesize paper",
                                "cwd": str(workdir),
                                "worktree": True,
                                "session_id": "prev-99",
                                "permission_mode": "acceptEdits",
                            },
                        },
                    },
                ],
            )
            by_id = {r["id"]: r for r in resps}

            astra = _extract_fake_result(by_id[1])
            self.assertEqual(astra["model"], "group/role-architect")
            self.assertIn("--disallowedTools", astra["argv"])
            self.assertIn("Bash", astra["argv"][astra["argv"].index("--disallowedTools") + 1])

            sup = _extract_fake_result(by_id[2])
            self.assertEqual(sup["model"], "group/role-supervisor")
            self.assertTrue(sup["prompt"].startswith("MODE: REVIEW\n\n"))
            denied = sup["argv"][sup["argv"].index("--disallowedTools") + 1]
            self.assertIn("Edit", denied)
            self.assertNotIn("Bash", denied)

            scout = _extract_fake_result(by_id[3])
            self.assertEqual(scout["model"], "group/role-worker-code")
            self.assertIn("Scout Mode", scout["prompt"])
            self.assertIn("--disallowedTools", scout["argv"])

            smart = _extract_fake_result(by_id[4])
            self.assertEqual(smart["model"], "group/role-smart-worker")
            self.assertEqual(smart["effort"], "high")
            self.assertIn("--worktree", smart["argv"])
            self.assertIn("--resume", smart["argv"])
            self.assertEqual(smart["argv"][smart["argv"].index("--resume") + 1], "prev-99")
            self.assertEqual(smart["argv"][smart["argv"].index("--permission-mode") + 1], "acceptEdits")
            self.assertEqual(Path(smart["cwd"]).resolve(), workdir.resolve())

    def test_parallel_dispatch_and_error_handling(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            temp = Path(tmp)
            slow = temp / "slow-launcher"
            _make_fake_launcher(slow, sleep_sec=0.6)
            # Three 0.6s calls run concurrently (serial would be >= 1.8s plus process startup).
            import time

            t0 = time.monotonic()
            resps = _rpc_roundtrip(
                slow,
                [
                    {"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": "run_worker", "arguments": {"prompt": f"T0{i}"}}}
                    for i in (1, 2, 3)
                ],
            )
            elapsed = time.monotonic() - t0
            self.assertEqual(len(resps), 3)
            self.assertLess(elapsed, 1.5)

            failing = temp / "fail-launcher"
            _make_fake_launcher(failing, fail=True)
            err_resps = _rpc_roundtrip(
                failing,
                [
                    {"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": {"name": "ask_astra", "arguments": {"prompt": "hi"}}},
                    {"jsonrpc": "2.0", "id": 11, "method": "tools/call", "params": {"name": "ask_astra", "arguments": {"prompt": ""}}},
                ],
            )
            err_by_id = {r["id"]: r for r in err_resps}
            self.assertTrue(err_by_id[10]["result"]["isError"])
            self.assertIn("simulated crash", err_by_id[10]["result"]["content"][0]["text"])
            self.assertTrue(err_by_id[11]["result"]["isError"])


if __name__ == "__main__":
    unittest.main()

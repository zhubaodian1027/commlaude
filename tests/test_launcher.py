from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = ROOT / "bin/claude-orchestra"


class LauncherTests(unittest.TestCase):
    def test_auto_mode_classifier_is_pinned(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            temp = Path(directory)
            capture = temp / "capture.txt"
            fake_claude = temp / "claude"
            fake_claude.write_text(
                "#!/usr/bin/env bash\n"
                "{\n"
                "  printf 'model=%s\\n' \"$CLAUDE_CODE_AUTO_MODE_MODEL\"\n"
                "  printf 'server=%s\\n' \"$CLAUDE_CODE_AUTO_MODE_SERVER\"\n"
                "  printf 'config=%s\\n' \"$CLAUDE_CONFIG_DIR\"\n"
                "  printf 'arg=%s\\n' \"$@\"\n"
                "} > \"$CAPTURE_PATH\"\n",
                encoding="utf-8",
            )
            fake_claude.chmod(0o700)
            env = os.environ.copy()
            env.update(
                CLAUDE_BIN=str(fake_claude),
                CAPTURE_PATH=str(capture),
                CLAUDE_CODE_AUTO_MODE_MODEL="group/role-communicator",
                CLAUDE_CODE_AUTO_MODE_SERVER="1",
            )
            env.pop("ORCHESTRA_AUTO_MODE_MODEL", None)

            result = subprocess.run(
                [str(LAUNCHER), "--version"],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            lines = capture.read_text(encoding="utf-8").splitlines()
            fields = dict(line.split("=", 1) for line in lines)
            self.assertEqual(fields["model"], "group/role-auto-mode")
            self.assertEqual(fields["server"], "0")
            self.assertEqual(fields["config"], str(ROOT / ".claude"))
            self.assertEqual(fields["arg"], "--version")


if __name__ == "__main__":
    unittest.main()

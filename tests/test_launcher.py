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
                ORCHESTRA_GLOBAL_SKILLS_DIR=str(temp / "empty-global-skills"),
            )
            env.pop("ORCHESTRA_AUTO_MODE_MODEL", None)
            env.pop("ORCHESTRA_INHERIT_SKILLS", None)

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

    def test_global_skills_bridging_and_cleanup(self) -> None:
        skills_dir = ROOT / ".claude/skills"
        bridged_name = "_test_bridged_skill_docx"
        symlinked_name = "_test_bridged_symlink_skill"
        bridged_dest = skills_dir / bridged_name
        symlinked_dest = skills_dir / symlinked_name
        builtin_dir = skills_dir / "model-orchestra"

        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            temp = Path(directory)
            fake_claude = temp / "claude"
            fake_claude.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            fake_claude.chmod(0o700)

            global_skills = temp / "global-skills"
            global_skills.mkdir()

            # Normal skill directory
            (global_skills / bridged_name).mkdir()
            (global_skills / bridged_name / "SKILL.md").write_text(
                "---\nname: test\ndescription: test\n---\n", encoding="utf-8"
            )

            # Skill directory that is itself a symlink in global skills
            external_target = temp / "external-skill"
            external_target.mkdir()
            (global_skills / symlinked_name).symlink_to(external_target)

            # Same name as a built-in skill (must never override)
            (global_skills / "model-orchestra").mkdir()

            # Non-directory file (must be ignored)
            (global_skills / "not-a-skill.txt").write_text("ignore", encoding="utf-8")

            env = os.environ.copy()
            env.update(
                CLAUDE_BIN=str(fake_claude),
                ORCHESTRA_GLOBAL_SKILLS_DIR=str(global_skills),
                ORCHESTRA_INHERIT_SKILLS="1",
            )

            try:
                # 1. Bridges directory and symlinked directory, preserves built-in, ignores files
                result = subprocess.run(
                    [str(LAUNCHER), "--version"],
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(bridged_dest.is_symlink())
                self.assertEqual(os.readlink(bridged_dest), str(global_skills / bridged_name))
                self.assertTrue(symlinked_dest.is_symlink())
                self.assertEqual(os.readlink(symlinked_dest), str(global_skills / symlinked_name))
                self.assertFalse(builtin_dir.is_symlink())
                self.assertFalse((skills_dir / "not-a-skill.txt").exists())

                # 2. Removing a global skill prunes its stale symlink on next launch
                (global_skills / symlinked_name).unlink()
                result = subprocess.run(
                    [str(LAUNCHER), "--version"],
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(symlinked_dest.is_symlink())
                self.assertTrue(bridged_dest.is_symlink())

                # 3. ORCHESTRA_INHERIT_SKILLS=0 removes bridged symlinks from this global dir
                env["ORCHESTRA_INHERIT_SKILLS"] = "0"
                result = subprocess.run(
                    [str(LAUNCHER), "--version"],
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(bridged_dest.is_symlink())
                self.assertFalse(builtin_dir.is_symlink())
            finally:
                for path in (bridged_dest, symlinked_dest):
                    if path.is_symlink():
                        path.unlink()


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Prove both legacy homes must migrate before their source checkouts are retired."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

MANAGER = Path(__file__).resolve().parents[1] / "manage-dotfiles.py"


class TwoMacMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.origin = self.base / "source"
        self.origin.mkdir()
        self.env = dict(os.environ, HOME=str(self.base / "unused-home"), GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, PYTHONDONTWRITEBYTECODE="1")
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
            self.env.pop(key, None)
        Path(self.env["HOME"]).mkdir()
        self.git(self.origin, "init", "-q")
        for relative, text in {
            "dotfiles/link/claude/CLAUDE.md": "shared instructions v1\n",
            "dotfiles/link/claude/agents/ordinary.md": "shared agent\n",
            "dotfiles/link/codex/agents/retiring.toml": 'model = "worker"\n',
            "dotfiles/link/claude/skills/synced/local/SKILL.md": "historical skill\n",
            "dotfiles/link/codex/hooks.json": '{"hooks": {}}\n',
            "dotfiles/link/codex/hooks.json.bak": "historical backup\n",
        }.items():
            self.write(self.origin / relative, text)
        for relative, target in (("codex/AGENTS.md", "../claude/CLAUDE.md"), ("gemini/GEMINI.md", "../claude/CLAUDE.md"), ("gemini/agents", "../claude/agents")):
            path = self.origin / "dotfiles/link" / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.symlink_to(target)
        self.git(self.origin, "add", ".")
        self.git(self.origin, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Shared source fixture")
        self.macs = {}
        for name in ("personal", "work"):
            clone, home = self.base / name / "checkout", self.base / name / "home"
            home.mkdir(parents=True)
            self.git(self.base, "clone", "-q", "--no-hardlinks", str(self.origin), str(clone))
            command = f'echo "${{ORCA_PANE_KEY-}} {name}-local"'
            hooks = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": command}]}]}}
            self.write(clone / "dotfiles/link/codex/hooks.json", json.dumps(hooks))
            self.write(clone / "dotfiles/link/claude/projects/private/sentinel", name + " project\n")
            self.write(clone / "dotfiles/link/claude/skills/synced/local/SKILL.md", name + " skill\n")
            for agent in ("claude", "codex", "gemini"):
                (home / ("." + agent)).symlink_to(clone / "dotfiles/link" / agent)
            self.macs[name] = (clone, home, hooks)

    @staticmethod
    def write(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def git(self, root, *args):
        return subprocess.check_output(["git", "-c", "core.fsmonitor=false", "-C", str(root), *args], env=self.env, stderr=subprocess.PIPE)

    def install(self, name):
        clone, home, _ = self.macs[name]
        result = subprocess.run([
            sys.executable, "-B", str(MANAGER), "apply", "--root", str(clone),
            "--home", str(home), "--state-dir", str(home / ".local/state/knapsack"),
        ], env=dict(self.env, HOME=str(home)), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_local_state(self, name):
        _, home, hooks = self.macs[name]
        self.assertEqual(json.loads((home / ".codex/hooks.json").read_text()), hooks)
        self.assertEqual((home / ".claude/projects/private/sentinel").read_text(), name + " project\n")
        self.assertEqual((home / ".claude/skills/synced/local/SKILL.md").read_text(), name + " skill\n")

    def cleanup_runtime_source(self, name):
        clone, _, _ = self.macs[name]
        self.git(clone, "rm", "-qrf", "dotfiles/link/claude/skills", "dotfiles/link/codex/hooks.json", "dotfiles/link/codex/hooks.json.bak")

    def test_both_migrations_precede_cleanup_and_survive_checkout_removal(self):
        personal_clone, personal_home, _ = self.macs["personal"]
        work_clone, work_home, _ = self.macs["work"]
        self.install("personal")
        self.assertTrue((personal_home / ".local/state/knapsack/stage-one.json").is_file())
        self.assertFalse((work_home / ".local/state/knapsack/stage-one.json").exists())
        self.cleanup_runtime_source("personal")
        self.assert_local_state("personal")
        # Work still depends on its own checkout: first-Mac evidence cannot authorize
        # deleting this source before the work-Mac migration has detached its links.
        self.assertTrue((work_home / ".claude").is_symlink())
        self.assertTrue((work_home / ".codex/hooks.json").samefile(work_clone / "dotfiles/link/codex/hooks.json"))
        self.assert_local_state("work")
        self.assertTrue((work_clone / "dotfiles/link/claude/skills/synced/local/SKILL.md").is_file())

        self.install("work")
        self.assertTrue((work_home / ".local/state/knapsack/stage-one.json").is_file())
        self.cleanup_runtime_source("work")
        self.assert_local_state("work")

        # Transfer only committed shared source, never either Mac's runtime files.
        self.write(self.origin / "dotfiles/link/claude/CLAUDE.md", "shared instructions v2\n")
        self.git(self.origin, "rm", "-q", "dotfiles/link/codex/agents/retiring.toml")
        self.git(self.origin, "add", ".")
        self.git(self.origin, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Update shared instructions and retire agent")
        for name, (clone, home, _) in self.macs.items():
            self.git(clone, "fetch", "-q", "origin")
            self.git(clone, "restore", "--source=FETCH_HEAD", "--staged", "--worktree", "--", "dotfiles/link/claude/CLAUDE.md", "dotfiles/link/codex/agents/retiring.toml")
            self.install(name)
            self.assertFalse((home / ".codex/agents/retiring.toml").exists())
            for relative in (".claude/CLAUDE.md", ".codex/AGENTS.md", ".gemini/GEMINI.md"):
                path = home / relative
                self.assertFalse(path.is_symlink())
                self.assertEqual(path.read_text(), "shared instructions v2\n")
            self.assertFalse((home / ".gemini/agents").is_symlink())
            self.assertEqual((home / ".gemini/agents/ordinary.md").read_text(), "shared agent\n")
            self.assert_local_state(name)

        shutil.rmtree(personal_clone)
        shutil.rmtree(work_clone)
        shutil.rmtree(self.origin)
        for name, (_, home, _) in self.macs.items():
            self.assert_local_state(name)
            self.assertEqual((home / ".codex/AGENTS.md").read_text(), "shared instructions v2\n")
            self.assertEqual((home / ".gemini/agents/ordinary.md").read_text(), "shared agent\n")
            self.assertFalse((home / ".claude").is_symlink())
            self.assertFalse((home / ".codex").is_symlink())


if __name__ == "__main__":
    unittest.main()

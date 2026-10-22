#!/usr/bin/env python3
"""Exercise two independent Stage 1 migrations followed by Stage 2 cleanup."""

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
        # Reuse the installation engine with the historical source layout and
        # receipt contract, so Stage 1 writes real destination-based ledgers.
        self.stage_one_manager = self.base / "stage-one/manage-dotfiles.py"
        self.stage_one_manager.parent.mkdir()
        self.stage_one_manager.write_text(
            MANAGER.read_text().replace("dotfiles/shared", "dotfiles/link")
            .replace("dotfiles/seed", "dotfiles/copy")
            .replace("stage-two", "stage-one").replace('"stage": 2', '"stage": 1')
        )
        shutil.copytree(MANAGER.parent / "lib", self.stage_one_manager.parent / "lib")
        self.env = dict(os.environ, HOME=str(self.base / "unused-home"), GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, PYTHONDONTWRITEBYTECODE="1")
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
            self.env.pop(key, None)
        Path(self.env["HOME"]).mkdir()
        self.git(self.origin, "init", "-q")
        for relative, text in {
            "dotfiles/link/claude/CLAUDE.md": "shared instructions v1\n",
            "dotfiles/link/claude/agents/ordinary.md": "shared agent\n",
            "dotfiles/copy/gitconfig_local": "seed settings\n",
            "dotfiles/link/zshrc": "shared shell\n",
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

    def install(self, name, stage_one=False, expected=0):
        clone, home, _ = self.macs[name]
        result = subprocess.run([
            sys.executable, "-B", str(self.stage_one_manager if stage_one else MANAGER), "apply", "--root", str(clone),
            "--home", str(home), "--state-dir", str(home / ".local/state/knapsack"),
        ], env=dict(self.env, HOME=str(home)), capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def assert_local_state(self, name):
        _, home, hooks = self.macs[name]
        self.assertEqual(json.loads((home / ".codex/hooks.json").read_text()), hooks)
        self.assertEqual((home / ".claude/projects/private/sentinel").read_text(), name + " project\n")
        self.assertEqual((home / ".claude/skills/synced/local/SKILL.md").read_text(), name + " skill\n")

    def cleanup_runtime_source(self, name):
        clone = self.origin if name == "origin" else self.macs[name][0]
        self.git(clone, "rm", "-qrf", "dotfiles/link/claude/skills", "dotfiles/link/codex/hooks.json", "dotfiles/link/codex/hooks.json.bak")

    def test_both_migrations_precede_cleanup_and_survive_checkout_removal(self):
        personal_clone, personal_home, _ = self.macs["personal"]
        work_clone, work_home, _ = self.macs["work"]
        self.install("personal", stage_one=True)
        self.assertTrue((personal_home / ".local/state/knapsack/stage-one.json").is_file())
        self.assertFalse((work_home / ".local/state/knapsack/stage-one.json").exists())
        self.assert_local_state("personal")
        # Work still depends on its own checkout: first-Mac evidence cannot authorize
        # deleting this source before the work-Mac migration has detached its links.
        self.assertTrue((work_home / ".claude").is_symlink())
        self.assertTrue((work_home / ".codex/hooks.json").samefile(work_clone / "dotfiles/link/codex/hooks.json"))
        self.assert_local_state("work")
        self.assertTrue((work_clone / "dotfiles/link/claude/skills/synced/local/SKILL.md").is_file())

        self.install("work", stage_one=True)
        self.assertTrue((work_home / ".local/state/knapsack/stage-one.json").is_file())
        self.assert_local_state("work")

        snapshots = {}
        for name, (clone, home, _) in self.macs.items():
            state = home / ".local/state/knapsack"
            snapshots[name] = {
                "receipt": (state / "stage-one.json").read_bytes(),
                "ledger": (state / "ledger.json").read_bytes(),
                "backups": {str(path.relative_to(state)): path.read_bytes()
                            for path in (state / "backups").rglob("*") if path.is_file()},
            }
            self.write(home / ".gitconfig_local", name + " seed override\n")
            self.write(home / ".codex/local-runtime.json", name + " runtime\n")
        self.write(personal_home / ".zshrc", "personal shell override\n")

        # Stage 2 removes historical runtime artifacts and renames the source
        # trees only after each clone's home has detached its legacy links.
        self.cleanup_runtime_source("origin")
        self.git(self.origin, "mv", "dotfiles/link", "dotfiles/shared")
        self.git(self.origin, "mv", "dotfiles/copy", "dotfiles/seed")
        self.git(self.origin, "add", ".")
        self.git(self.origin, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Clean up and rename migrated source")
        for name, (clone, home, _) in self.macs.items():
            # Runtime bytes are already in the home and backups. Restore only
            # the known historical tracked artifacts before updating the clone.
            self.git(clone, "restore", "dotfiles/link/claude/skills", "dotfiles/link/codex/hooks.json")
            self.git(clone, "pull", "-q", "--ff-only")
            self.assertEqual(self.git(clone, "ls-files", "--", "dotfiles/link"), b"")
            # Git leaves untracked historical runtime state in the old tree;
            # cleanup never recursively deletes it to make the rename look tidy.
            self.assertEqual((clone / "dotfiles/link/claude/projects/private/sentinel").read_text(), name + " project\n")
            output = self.install(name, expected=1 if name == "personal" else 0)
            if name == "personal":
                self.assertIn("local content", output)
                self.assertEqual((home / ".zshrc").read_text(), "personal shell override\n")
            self.assertNotIn("retire:", output)
            self.assertNotIn("adopt:", output)
            state = home / ".local/state/knapsack"
            self.assertEqual((state / "ledger.json").read_bytes(), snapshots[name]["ledger"])
            self.assertEqual((state / "stage-one.json").read_bytes(), snapshots[name]["receipt"])
            if name == "work":
                self.assertEqual(json.loads((state / "stage-two.json").read_text())["stage"], 2)
            self.assertEqual({str(path.relative_to(state)): path.read_bytes()
                              for path in (state / "backups").rglob("*") if path.is_file()},
                             snapshots[name]["backups"])
            self.assert_local_state(name)

        # Transfer only committed shared source, never either Mac's runtime files.
        self.write(self.origin / "dotfiles/shared/claude/CLAUDE.md", "shared instructions v2\n")
        self.git(self.origin, "rm", "-q", "dotfiles/shared/codex/agents/retiring.toml")
        self.git(self.origin, "add", ".")
        self.git(self.origin, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Update shared instructions and retire agent")
        for name, (clone, home, _) in self.macs.items():
            self.git(clone, "fetch", "-q", "origin")
            self.git(clone, "restore", "--source=FETCH_HEAD", "--staged", "--worktree", "--", "dotfiles/shared/claude/CLAUDE.md", "dotfiles/shared/codex/agents/retiring.toml")
            self.install(name, expected=1 if name == "personal" else 0)
            self.assertFalse((home / ".codex/agents/retiring.toml").exists())
            for relative in (".claude/CLAUDE.md", ".codex/AGENTS.md", ".gemini/GEMINI.md"):
                path = home / relative
                self.assertFalse(path.is_symlink())
                self.assertEqual(path.read_text(), "shared instructions v2\n")
            self.assertFalse((home / ".gemini/agents").is_symlink())
            self.assertEqual((home / ".gemini/agents/ordinary.md").read_text(), "shared agent\n")
            self.assert_local_state(name)
            self.assertEqual((home / ".gitconfig_local").read_text(), name + " seed override\n")
            self.assertEqual((home / ".codex/local-runtime.json").read_text(), name + " runtime\n")

        # A managed file edited locally stays a conflict across the source rename.
        self.write(personal_clone / "dotfiles/shared/zshrc", "shared shell v2\n")
        self.assertIn("local content", self.install("personal", expected=1))
        self.assertEqual((personal_home / ".zshrc").read_text(), "personal shell override\n")
        self.assertFalse((personal_home / ".local/state/knapsack/stage-two.json").exists())
        self.assertEqual((personal_home / ".local/state/knapsack/stage-one.json").read_bytes(), snapshots["personal"]["receipt"])

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

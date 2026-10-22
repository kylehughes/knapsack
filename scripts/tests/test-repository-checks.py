#!/usr/bin/env python3
"""Exercise source guardrails and hook ownership using disposable Git repositories."""

import json
import os
import runpy
import stat
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "repo"
        self.root.mkdir()
        home = Path(self.temporary.name) / "home"
        home.mkdir()
        self.env = dict(os.environ, HOME=str(home), GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, PYTHONDONTWRITEBYTECODE="1")
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
            self.env.pop(key, None)
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "Fixture")
        self.write("README", "fixture\n")
        self.git("add", ".")
        self.git("commit", "-qm", "Fixture")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], env=self.env, stderr=subprocess.PIPE)

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def script(self, script="check-repository.py", *args):
        return subprocess.run([sys.executable, "-B", str(SCRIPTS / script), "--root", str(self.root), *args], env=self.env, capture_output=True, text=True)

    def test_clean_source_and_untracked_runtime(self):
        self.write("__pycache__/untracked.pyc", "local")
        self.assertEqual(self.script().returncode, 0)
        self.assertEqual(self.script("check-repository.py", "--staged").returncode, 0)

    def test_forbidden_new_paths(self):
        names = ["a.pyc", "a.pyo", "a.bak", "x/__pycache__/x"]
        for source in ("dotfiles/shared", "dotfiles/link"):
            names.extend(f"{source}/{relative}" for relative in (
                "claude/skills/synced/bucket/file",
                "config/zsh/functions-local/private",
                "codex/auth.json",
                "claude/projects/private/state",
                "gemini/trustedFolders.json",
            ))
        for name in names:
            with self.subTest(name=name):
                self.write(name, "{}")
                self.git("add", name)
                for args in ((), ("--staged",)):
                    result = self.script("check-repository.py", *args)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(f"{name}: runtime artifact must stay local", result.stderr)
                self.git("rm", "--cached", name)

    def test_former_baseline_bytes_are_rejected(self):
        for name in ("scripts/__pycache__/old.pyc", "dotfiles/shared/claude/projects/old/state", "dotfiles/link/claude/projects/old/state"):
            with self.subTest(name=name):
                self.write(name, "old")
                blob = self.git("hash-object", str(self.root / name)).decode().strip()
                self.write("scripts/runtime-artifacts-stage-one.json", json.dumps({name: blob}))
                self.git("add", name, "scripts/runtime-artifacts-stage-one.json")
                for args in ((), ("--staged",)):
                    result = self.script("check-repository.py", *args)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(f"{name}: runtime artifact must stay local", result.stderr)
                self.git("rm", "--cached", name)

    def test_index_snapshot_preserves_executable_modes(self):
        executable = self.write("tool", "#!/bin/sh\nexit 0\n")
        executable.chmod(0o755)
        ordinary = self.write("ordinary", "source\n")
        ordinary.chmod(0o644)
        self.git("add", "tool", "ordinary")
        # Worktree permissions must not change the recorded index snapshot modes.
        executable.chmod(0o644)
        ordinary.chmod(0o755)
        snapshot = Path(self.temporary.name) / "snapshot"
        snapshot.mkdir()
        with mock.patch.dict(os.environ, self.env, clear=True):
            checker = runpy.run_path(str(SCRIPTS / "check-repository.py"))
            checker["snapshot_index"](self.root, snapshot, checker["entries"](self.root))
        self.assertEqual(stat.S_IMODE((snapshot / "tool").stat().st_mode), 0o755)
        self.assertEqual(stat.S_IMODE((snapshot / "ordinary").stat().st_mode), 0o644)

    def test_staged_check_does_not_apply_checkout_filters(self):
        self.write("source.py", "value = 1\n")
        self.write(".gitattributes", "*.py filter=fixture\n")
        self.git("add", ".")
        marker = self.root / "filter-ran"
        self.git("config", "filter.fixture.smudge", f"touch {marker}")
        self.assertEqual(self.script("check-repository.py", "--staged").returncode, 0)
        self.assertFalse(marker.exists())

    def test_index_bytes_win_over_worktree(self):
        self.write("source.py", "def broken(\n")
        self.git("add", "source.py")
        self.write("source.py", "value = 1\n")
        self.assertNotEqual(self.script("check-repository.py", "--staged").returncode, 0)
        self.git("add", "source.py")
        self.write("source.py", "def broken(\n")
        self.assertEqual(self.script("check-repository.py", "--staged").returncode, 0)
        self.assertFalse(list(self.root.rglob("__pycache__")))

    def test_aliases_and_cycles(self):
        self.write("dotfiles/shared/claude/CLAUDE.md", "Instructions")
        self.write("dotfiles/shared/claude/agents/a.md", "Agent")
        for name, target in (("codex/AGENTS.md", "../claude/CLAUDE.md"), ("gemini/GEMINI.md", "../claude/CLAUDE.md"), ("gemini/agents", "../claude/agents")):
            path = self.root / "dotfiles/shared" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.symlink_to(target)
        self.git("add", ".")
        self.assertEqual(self.script("check-repository.py", "--staged").returncode, 0)
        (self.root / "cycle").symlink_to("cycle")
        self.git("add", "cycle")
        self.assertNotEqual(self.script("check-repository.py", "--staged").returncode, 0)

    def test_external_and_unexpected_directory_aliases(self):
        for name, target in (("external", "/etc/passwd"), ("directory", "scripts")):
            (self.root / "scripts").mkdir(exist_ok=True)
            self.write("scripts/source.py", "pass\n")
            (self.root / name).symlink_to(target)
            self.git("add", ".")
            self.assertNotEqual(self.script("check-repository.py", "--staged").returncode, 0)
            self.git("rm", "-f", name)

    def test_hook_preserves_custom_and_effective_path(self):
        self.git("config", "core.hooksPath", "custom-hooks")
        hook = self.write("custom-hooks/pre-commit", "#!/bin/sh\necho custom\n")
        before = hook.read_bytes()
        result = self.script("set-up-repository-hook.py")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--staged', result.stderr)
        self.assertEqual(hook.read_bytes(), before)
        hook.unlink()
        self.assertEqual(self.script("set-up-repository-hook.py").returncode, 0)
        self.assertTrue(os.access(hook, os.X_OK))
        self.assertEqual(self.script("set-up-repository-hook.py").returncode, 0)
        self.assertEqual(self.git("config", "core.hooksPath").decode().strip(), "custom-hooks")

    def test_customized_managed_hook_is_preserved(self):
        self.assertEqual(self.script("set-up-repository-hook.py").returncode, 0)
        hook = self.root / ".git/hooks/pre-commit"
        with hook.open("a") as output:
            output.write("echo custom-check\n")
        before = hook.read_bytes()
        mode = hook.stat().st_mode
        result = self.script("set-up-repository-hook.py")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--staged", result.stderr)
        self.assertEqual(hook.read_bytes(), before)
        self.assertEqual(hook.stat().st_mode, mode)

    def test_legacy_hook_allows_source_but_rejects_staged_orca_runtime(self):
        name = "dotfiles/shared/codex/hooks.json"
        old = {"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": 'python3 "$HOME/.codex/hooks/validate-agent-route.py"'}]}]}}
        self.write(name, json.dumps(old))
        self.git("add", name)
        self.assertEqual(self.script("check-repository.py", "--staged").returncode, 0)
        generated = json.loads(json.dumps(old))
        generated["hooks"]["SessionStart"] = [{"hooks": [{"type": "command", "command": 'test -n "$ORCA_PANE_KEY" && sh "$ORCA_AGENT_HOOK_ROOT/agent-hooks/codex-hook.sh"'}]}]
        self.write(name, json.dumps(generated))
        self.git("add", name)
        # A clean worktree copy cannot hide generated commands already in the index.
        path = self.write(name, json.dumps(old))
        before = path.read_bytes()
        indexed = self.git("show", ":" + name)
        result = self.script("check-repository.py", "--staged")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Orca runtime hook commands", result.stderr)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.git("show", ":" + name), indexed)
        self.assertEqual(self.script().returncode, 0)
        # Documentation may describe Orca variables without becoming runtime state.
        self.write("ORCA.md", "Use ORCA_PANE_KEY in your local hook.\n")
        self.git("add", "ORCA.md", name)
        self.assertEqual(self.script("check-repository.py", "--staged").returncode, 0)

    def test_external_hooks_path_is_preserved(self):
        outside = Path(self.temporary.name) / "shared-hooks"
        self.git("config", "core.hooksPath", str(outside))
        result = self.script("set-up-repository-hook.py")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(outside.exists())
        self.assertIn("--staged", result.stderr)

    def test_linked_worktree_hook(self):
        linked = Path(self.temporary.name) / "linked"
        self.git("worktree", "add", "-qb", "fixture-linked", str(linked))
        self.root = linked
        self.assertEqual(self.script("set-up-repository-hook.py").returncode, 0)
        hook = Path(self.temporary.name) / "repo/.git/hooks/pre-commit"
        self.assertTrue(hook.exists())
        self.assertIn("git rev-parse --show-toplevel", hook.read_text())

    def test_hook_survives_repository_move(self):
        (self.root / "scripts").mkdir()
        shutil.copy(SCRIPTS / "check-repository.py", self.root / "scripts/check-repository.py")
        self.git("add", ".")
        self.assertEqual(self.script("set-up-repository-hook.py").returncode, 0)
        moved = self.root.with_name("moved")
        self.root.rename(moved)
        self.root = moved
        result = subprocess.run([str(self.root / ".git/hooks/pre-commit")], cwd=self.root, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.write("bad.pyc", "bad")
        self.git("add", "bad.pyc")
        result = subprocess.run([str(self.root / ".git/hooks/pre-commit")], cwd=self.root, env=self.env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()

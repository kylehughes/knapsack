#!/usr/bin/env python3
"""Fixture tests for isolated dotfile installation and legacy recovery."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "manage-dotfiles.py"
SPEC = importlib.util.spec_from_file_location("manage_dotfiles", SCRIPT)
MANAGER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MANAGER)
OWNED = {
    "matcher": "^(spawn_agent|Agent|collaborationspawn_agent)$",
    "hooks": [{"type": "command", "command": MANAGER.reconcile_codex_hooks.__globals__["ROUTING_COMMAND"], "timeout": 3}],
}


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "checkout"
        self.home = self.base / "home"
        self.root.mkdir()
        self.home.mkdir()
        self.state = self.home / ".local/state/knapsack"
        self.git("init", "-q")
        self.git("config", "core.fsmonitor", "false")
        self.write("dotfiles/shared/zshrc", "tracked shell\n")
        self.write("dotfiles/shared/config/zsh/functions/tool-run", "#!/bin/zsh\n", 0o755)
        self.write("dotfiles/shared/claude/CLAUDE.md", "shared instructions\n")
        self.write("dotfiles/shared/claude/agents/ordinary.md", "worker\n")
        self.write("dotfiles/shared/codex/agents/ordinary.toml", 'model = "worker"\n')
        self.write("dotfiles/shared/claude/skills/local/SKILL.md", "runtime tracked historically\n")
        self.write("dotfiles/shared/codex/hooks.json", '{"local":"old runtime artifact"}\n')
        self.write("dotfiles/shared/codex/hooks.json.bak", "retained backup\n")
        self.write("dotfiles/seed/gitconfig_local", "seed\n")
        self.write("dotfiles/merge/claude/settings.json", '{"model":"worker","enabledPlugins":{}}\n')
        self.write("dotfiles/merge/codex/hooks.json", json.dumps({"hooks": {"PreToolUse": [OWNED]}}))
        for relative, target in (
            ("dotfiles/shared/codex/AGENTS.md", "../claude/CLAUDE.md"),
            ("dotfiles/shared/gemini/GEMINI.md", "../claude/CLAUDE.md"),
            ("dotfiles/shared/gemini/agents", "../claude/agents"),
        ):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.symlink_to(target)
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.com", "commit", "-qm", "Fixture")

    def git(self, *arguments):
        return subprocess.check_output(["git", "-C", str(self.root), *arguments], stderr=subprocess.DEVNULL)

    def write(self, relative, contents, mode=0o644, home=False):
        path = (self.home if home else self.root) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
        path.chmod(mode)
        return path

    def installer(self):
        return MANAGER.Installer(self.root, self.home, self.state)

    def run_command(self, command, expected=0):
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            status = MANAGER.main([
                command, "--root", str(self.root), "--home", str(self.home),
                "--state-dir", str(self.state),
            ])
        self.assertEqual(status, expected, output.getvalue() + errors.getvalue())
        return output.getvalue() + errors.getvalue()

    def tree(self, root):
        if not root.exists():
            return None
        return self.installer().snapshot_digest(root)

    def test_install_isolated_aliases_seed_and_idempotent_check(self):
        self.run_command("apply")
        self.assertEqual((self.home / ".codex/AGENTS.md").read_text(), "shared instructions\n")
        self.assertFalse((self.home / ".codex/AGENTS.md").is_symlink())
        self.assertFalse((self.home / ".gemini/agents").is_symlink())
        self.assertEqual((self.home / ".gemini/agents/ordinary.md").read_text(), "worker\n")
        self.assertFalse((self.home / ".claude/skills").exists())
        self.assertFalse((self.home / ".codex/hooks.json.bak").exists())
        self.assertEqual((self.home / ".gitconfig_local").read_text(), "seed\n")
        self.assertEqual(MANAGER.load_json(self.home / ".claude/settings.machine.json"), {})
        ledger = MANAGER.load_json(self.state / "ledger.json")
        self.assertNotIn(".gitconfig_local", ledger["files"])
        self.assertNotIn(".claude/settings.machine.json", ledger["files"])
        self.assertNotIn(".claude/skills/local/SKILL.md", ledger["files"])
        self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((self.state / "ledger.json").stat().st_mode), 0o600)
        self.assertEqual(self.run_command("apply"), "")
        self.run_command("check")
        self.write("dotfiles/shared/zshrc", "new source\n")
        self.assertEqual((self.home / ".zshrc").read_text(), "tracked shell\n")

    def test_plan_and_check_never_create_state_or_bytecode(self):
        before = self.tree(self.root), self.tree(self.home)
        self.run_command("plan")
        self.run_command("check", 1)
        self.assertEqual((self.tree(self.root), self.tree(self.home)), before)
        self.assertFalse(self.state.exists())
        self.assertFalse(list(self.root.rglob("__pycache__")))

    def test_update_retire_and_preserve_content_and_execute_mode_conflicts(self):
        historical_receipt = self.write(".local/state/knapsack/stage-one.json", '{"stage":1}\n', home=True)
        self.run_command("apply")
        self.assertTrue((self.state / "stage-two.json").is_file())
        self.write("dotfiles/shared/zshrc", "updated shell\n")
        self.git("rm", "-q", "dotfiles/shared/codex/agents/ordinary.toml")
        self.write(".config/zsh/functions/tool-run", "#!/bin/zsh\n", 0o644, home=True)
        text = self.run_command("apply", 1)
        self.assertIn("execute mode", text)
        self.assertEqual((self.home / ".zshrc").read_text(), "updated shell\n")
        self.assertFalse((self.home / ".codex/agents/ordinary.toml").exists())
        self.write(".zshrc", "local shell\n", home=True)
        self.write("dotfiles/shared/zshrc", "third shell\n")
        self.run_command("apply", 1)
        self.assertEqual((self.home / ".zshrc").read_text(), "local shell\n")
        self.assertFalse((self.state / "stage-two.json").exists())
        self.assertEqual(historical_receipt.read_bytes(), b'{"stage":1}\n')

    def test_retired_local_file_and_seed_are_preserved(self):
        self.run_command("apply")
        self.write(".zshrc", "local shell\n", home=True)
        self.write(".gitconfig_local", "local seed\n", home=True)
        self.git("rm", "-q", "dotfiles/shared/zshrc")
        self.run_command("apply", 1)
        self.assertEqual((self.home / ".zshrc").read_text(), "local shell\n")
        self.assertEqual((self.home / ".gitconfig_local").read_text(), "local seed\n")

    def test_bootstrap_semantic_claude_and_runtime_codex_preservation(self):
        self.write(".claude/settings.machine.json", '{"enabledPlugins":{"local":true}}', home=True)
        current = self.write(".claude/settings.json", '{"enabledPlugins":{"local":true},"model":"worker"}', home=True)
        local = {"type": "command", "command": "orca-local", "timeout": 5}
        hook_json = {"description": "Orca", "hooks": {"PreToolUse": [
            {"matcher": "all", "hooks": [local]}, deepcopy(OWNED),
        ]}, "future": {"keep": 1}}
        self.write(".codex/hooks.json", json.dumps(hook_json), home=True)
        original = current.read_bytes()
        self.run_command("apply")
        self.assertEqual(current.read_bytes(), original)
        self.assertEqual(MANAGER.load_json(self.home / ".codex/hooks.json"), hook_json)
        hook_json["future"]["new"] = 2
        self.write(".codex/hooks.json", json.dumps(hook_json), home=True)
        self.run_command("apply")
        self.assertEqual(MANAGER.load_json(self.home / ".codex/hooks.json"), hook_json)

    def test_claude_drift_conflict_reports_keys_without_values(self):
        current = self.write(".claude/settings.json", '{"model":"private-value","secret":"do-not-print"}', home=True)
        original = current.read_bytes()
        text = self.run_command("apply", 1)
        self.assertIn("model, secret", text)
        self.assertNotIn("private-value", text)
        self.assertNotIn("do-not-print", text)
        self.assertEqual(current.read_bytes(), original)

    def test_malformed_composition_is_untouched(self):
        for contents in ('{"hooks":[]}', '{"hooks": {"PreToolUse": [1]}}', "bad-json"):
            with self.subTest(contents=contents):
                path = self.write(".codex/hooks.json", contents, home=True)
                self.run_command("apply", 1)
                self.assertEqual(path.read_text(), contents)

    def test_legacy_whole_tree_preserves_local_hidden_files_and_materializes_aliases(self):
        self.write("dotfiles/shared/claude/.local-hidden", "keep hidden\n")
        self.write("dotfiles/shared/claude/skills/untracked/SKILL.md", "local skill\n")
        self.write("dotfiles/shared/config/zsh/functions-local/private-tool", "local function\n")
        external = self.base / "external"
        external.mkdir()
        (self.root / "dotfiles/shared/claude/external").symlink_to(external)
        for name in ("claude", "codex", "gemini"):
            (self.home / ("." + name)).symlink_to(self.root / "dotfiles/shared" / name)
        (self.home / ".config").mkdir()
        (self.home / ".config/zsh").symlink_to(self.root / "dotfiles/shared/config/zsh")
        # The original mutable hook contents must be valid to reconcile, and
        # must survive in source and migration backup after local migration.
        original_hooks = json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "local"}]}]}})
        self.write("dotfiles/shared/codex/hooks.json", original_hooks)
        before = self.tree(self.root / "dotfiles/shared")
        self.run_command("plan")
        self.run_command("apply")
        self.assertEqual(self.tree(self.root / "dotfiles/shared"), before)
        self.assertFalse((self.home / ".claude").is_symlink())
        self.assertEqual((self.home / ".claude/.local-hidden").read_text(), "keep hidden\n")
        self.assertEqual((self.home / ".claude/skills/untracked/SKILL.md").read_text(), "local skill\n")
        self.assertEqual((self.home / ".config/zsh/functions-local/private-tool").read_text(), "local function\n")
        self.assertTrue((self.home / ".claude/external").is_symlink())
        self.assertFalse((self.home / ".gemini/GEMINI.md").is_symlink())
        self.assertFalse((self.home / ".gemini/agents").is_symlink())
        self.assertGreaterEqual(len(list((self.state / "backups").iterdir())), 4)
        self.run_command("check")

    def test_unknown_internal_nested_link_refuses_detachment(self):
        (self.root / "dotfiles/shared/claude/unknown").symlink_to(self.root / "dotfiles/shared/zshrc")
        (self.home / ".claude").symlink_to(self.root / "dotfiles/shared/claude")
        self.run_command("apply", 1)
        self.assertTrue((self.home / ".claude").is_symlink())
        self.assertFalse(self.state.exists())

    def test_relative_external_links_keep_referent_in_home_and_content_backup(self):
        external = self.base / "external"
        external.mkdir()
        (external / "private-file").write_text("external contents stay external\n")
        link = self.root / "dotfiles/shared/claude/external"
        link.symlink_to("../../../../external")
        self.assertEqual(link.resolve(strict=True), external)
        (self.home / ".claude").symlink_to(self.root / "dotfiles/shared/claude")
        self.run_command("apply")
        migrated = self.home / ".claude/external"
        self.assertTrue(migrated.is_symlink())
        self.assertEqual(migrated.resolve(strict=True), external)
        self.assertEqual((migrated / "private-file").read_text(), "external contents stay external\n")
        backups = list((self.state / "backups").iterdir())
        self.assertEqual(len(backups), 1)
        self.assertTrue((backups[0] / "external").is_symlink())
        self.assertEqual((backups[0] / "external").resolve(strict=True), external)
        self.assertEqual(os.readlink(link), "../../../../external")
        self.run_command("check")

    def test_external_link_indirection_survives_retargeting_after_migration(self):
        first, second = self.base / "v1", self.base / "v2"
        first.mkdir()
        second.mkdir()
        current = self.base / "current"
        current.symlink_to(first)
        source = self.root / "dotfiles/shared/claude"
        (source / "absolute-external").symlink_to(current)
        (source / "relative-external").symlink_to("../../../../current")
        (self.home / ".claude").symlink_to(source)
        self.run_command("apply")
        backup = next((self.state / "backups").iterdir())
        for parent in (source, self.home / ".claude", backup):
            for name in ("absolute-external", "relative-external"):
                self.assertEqual((parent / name).resolve(strict=True), first)
        self.assertEqual(os.readlink(self.home / ".claude/absolute-external"), str(current))
        self.assertEqual(os.readlink(self.home / ".claude/relative-external"), str(current))
        current.unlink()
        current.symlink_to(second)
        for parent in (source, self.home / ".claude", backup):
            for name in ("absolute-external", "relative-external"):
                self.assertEqual((parent / name).resolve(strict=True), second)
        self.run_command("check")

    def test_dangling_external_path_through_checkout_link_is_refused(self):
        outside_alias = self.base / "checkout-alias"
        outside_alias.symlink_to(self.root)
        (self.root / "dotfiles/shared/claude/dangling").symlink_to(outside_alias / "missing")
        (self.home / ".claude").symlink_to(self.root / "dotfiles/shared/claude")
        self.run_command("apply", 1)
        self.assertTrue((self.home / ".claude").is_symlink())
        self.assertFalse(self.state.exists())

    def test_unexpected_home_state_and_destination_ancestors_refused(self):
        outside = self.base / "outside"
        outside.mkdir()
        (self.home / ".config").symlink_to(outside)
        self.run_command("apply", 1)
        self.assertFalse(self.state.exists())
        (self.home / ".config").unlink()
        self.state.parent.mkdir(parents=True)
        self.state.symlink_to(outside)
        self.run_command("plan", 1)
        self.assertEqual(list(outside.iterdir()), [])
        self.state.unlink()
        real_home = self.home.with_name("real-home")
        self.home.rename(real_home)
        self.home.symlink_to(real_home)
        self.run_command("apply", 1)

    def test_prepare_only_migrates_requested_scope_and_no_receipt(self):
        (self.home / ".claude").symlink_to(self.root / "dotfiles/shared/claude")
        (self.home / ".config").mkdir()
        (self.home / ".config/zsh").symlink_to(self.root / "dotfiles/shared/config/zsh")
        self.run_command("prepare-skills")
        self.assertFalse((self.home / ".claude").is_symlink())
        self.assertTrue((self.home / ".config/zsh").is_symlink())
        self.assertFalse((self.home / ".zshrc").exists())
        self.assertFalse((self.state / "ledger.json").exists())
        self.assertFalse((self.state / "stage-two.json").exists())
        self.run_command("prepare-functions")
        self.assertFalse((self.home / ".config/zsh").is_symlink())

    def test_untracked_templates_are_not_deployed_and_dirty_bytes_are(self):
        self.write("dotfiles/shared/untracked", "never install\n")
        self.write("dotfiles/shared/zshrc", "deliberate dirty edit\n")
        self.run_command("apply")
        self.assertEqual((self.home / ".zshrc").read_text(), "deliberate dirty edit\n")
        self.assertFalse((self.home / ".untracked").exists())

    def test_receipt_invalidates_with_dirty_template_and_implementation(self):
        self.run_command("apply")
        self.run_command("check")
        self.write("dotfiles/shared/zshrc", "dirty\n")
        self.assertIn("receipt", self.run_command("check", 1))
        self.run_command("apply")
        self.write("scripts/manage-dotfiles.py", "changed implementation\n")
        self.assertIn("receipt", self.run_command("check", 1))

    def test_runtime_source_edits_do_not_invalidate_receipt(self):
        self.run_command("apply")
        self.write("dotfiles/shared/codex/hooks.json", "runtime change\n")
        self.write("dotfiles/shared/codex/hooks.json.bak", "backup change\n")
        self.write("dotfiles/shared/claude/skills/local/SKILL.md", "runtime skill change\n")
        self.run_command("check")

    def test_remaining_unmanaged_hook_backlink_blocks_completion(self):
        self.run_command("apply")
        path = self.home / ".codex/hooks/unmanaged.py"
        path.parent.mkdir(exist_ok=True)
        path.symlink_to(self.root / "dotfiles/shared/zshrc")
        self.assertIn("symlink", self.run_command("apply", 1))
        self.assertFalse((self.state / "stage-two.json").exists())

    def test_unrecorded_canonical_codex_hook_ownership_fails_check(self):
        self.run_command("apply")
        ledger = MANAGER.load_json(self.state / "ledger.json")
        ledger.pop("codex_owned")
        MANAGER.atomic_write(self.state / "ledger.json", MANAGER.json_bytes(ledger))
        self.assertIn("ownership", self.run_command("check", 1))

    def test_changed_composed_hook_is_preserved_and_old_baseline_retained(self):
        self.run_command("apply")
        self.write("dotfiles/merge/codex/hooks.json", json.dumps({"hooks": {"PreToolUse": [{
            "matcher": OWNED["matcher"], "hooks": [dict(OWNED["hooks"][0], timeout=4)],
        }]}}))
        installer = self.installer()
        managed, seeds = installer.manifest()
        ledger = installer.ledger()
        installer.special_files(ledger, managed)
        current = MANAGER.load_json(self.home / ".codex/hooks.json")
        current["app-written"] = "keep"
        self.write(".codex/hooks.json", json.dumps(current), home=True)
        installer.apply_files(managed, seeds, ledger, write=True)
        self.assertTrue(installer.conflicts)
        self.assertEqual(MANAGER.load_json(self.home / ".codex/hooks.json"), current)
        self.assertEqual(ledger["codex_owned"], OWNED)

    def test_atomic_replacement_checks_preimage_after_staging(self):
        path = self.write(".zshrc", "before\n", home=True)
        expected = (True, MANAGER.file_signature(path))
        chmod = MANAGER.os.chmod

        def changing_chmod(name, mode):
            chmod(name, mode)
            path.write_text("app changed while staging\n")

        with mock.patch.object(MANAGER.os, "chmod", side_effect=changing_chmod):
            with self.assertRaises(MANAGER.InstallError):
                MANAGER.atomic_write(path, b"replacement\n", expected=expected)
        self.assertEqual(path.read_text(), "app changed while staging\n")

    def interrupted_journal(self, state):
        destination = self.home / ".claude"
        destination.symlink_to(self.root / "dotfiles/shared/claude")
        installer = self.installer()
        self.state.mkdir(parents=True)
        backup = self.state / "backups/fixture"
        backup.parent.mkdir()
        stage = self.home / "..claude.knapsack-stage-fixture"
        fingerprint = installer.snapshot_digest(destination.resolve(), backup)
        installer.snapshot_digest(backup, stage)
        journal = {"schema": 1, "destination": str(destination), "backup": str(backup),
                   "stage": str(stage), "fingerprint": fingerprint, "link": os.readlink(destination)}
        MANAGER.atomic_write(self.state / "migration-journal.json", MANAGER.json_bytes(journal))
        if state in {"missing", "swapped"}:
            destination.unlink()
        if state == "swapped":
            os.replace(stage, destination)
        return installer, destination, stage, backup

    def test_recovery_link_present_destination_missing_and_completed_swap(self):
        for state in ("linked", "missing", "swapped"):
            with self.subTest(state=state):
                installer, destination, stage, backup = self.interrupted_journal(state)
                installer.recover()
                self.assertFalse(destination.is_symlink())
                self.assertEqual(installer.snapshot_digest(destination), installer.snapshot_digest(backup))
                self.assertFalse(stage.exists())
                self.assertFalse((self.state / "migration-journal.json").exists())
                MANAGER.Installer.remove_snapshot(destination)
                MANAGER.Installer.remove_snapshot(self.state)

    def test_recovery_refuses_modified_stage_or_destination(self):
        installer, destination, stage, _ = self.interrupted_journal("linked")
        (stage / "CLAUDE.md").write_text("changed\n")
        with self.assertRaises(MANAGER.InstallError):
            installer.recover()
        self.assertTrue(destination.is_symlink())

    def test_writer_change_during_snapshot_prevents_detachment(self):
        destination = self.home / ".claude"
        destination.symlink_to(self.root / "dotfiles/shared/claude")
        installer = self.installer()
        original = installer.snapshot_digest

        def changing_copy(source, target=None, active=()):
            result = original(source, target, active)
            if target is not None and target.parent == self.state / "backups":
                (source / "CLAUDE.md").write_text("app wrote during snapshot\n")
            return result

        with installer.lock(), mock.patch.object(installer, "snapshot_digest", side_effect=changing_copy):
            with self.assertRaises(MANAGER.InstallError):
                installer.detach(destination)
        self.assertTrue(destination.is_symlink())


if __name__ == "__main__":
    unittest.main()

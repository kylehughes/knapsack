#!/usr/bin/env python3
"""Tests for the read-only Codex routing status checker."""

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "check-codex-routing.py"
SPEC = importlib.util.spec_from_file_location("codex_routing_status", SCRIPT)
STATUS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STATUS)


class CodexRoutingStatusTests(unittest.TestCase):
    def install_copies(self, home, active_home):
        root = Path(__file__).resolve().parents[2]
        source = root / "dotfiles/shared/codex"
        active_home.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source / "agents", active_home / "agents")
        (active_home / "hooks.json").write_text('{"hooks":{},"description":"app-managed"}')
        (home / ".codex/hooks").mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / "hooks/validate-agent-route.py", home / ".codex/hooks/validate-agent-route.py")
        return root

    def test_explicit_role_references_accept_standard_home_copies(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            standard_home = home / ".codex"
            root = self.install_copies(home, standard_home)
            active_home = home / "runtime"
            active_home.mkdir()
            (active_home / "hooks.json").write_text('{"hooks":{},"description":"app-managed"}')
            agents = {
                Path(profile).stem.replace("-", "_"): {"config_file": str(standard_home / "agents" / profile)}
                for profile in STATUS.PROFILES
            }
            config = {"config": {"agents": agents}}
            with mock.patch.object(Path, "home", return_value=home):
                self.assertEqual(STATUS.file_issues(active_home, root, config), [])
                agents["knapsack_mechanical"]["config_file"] = str(root / "dotfiles/shared/codex/agents/knapsack-mechanical.toml")
                self.assertIn("agent profile is not an isolated matching copy knapsack-mechanical.toml", STATUS.file_issues(active_home, root, config))
                agents["knapsack_mechanical"]["config_file"] = str(home / "missing.toml")
                self.assertIn("missing agent profile knapsack-mechanical.toml", STATUS.file_issues(active_home, root, config))

    def test_active_home_prefers_codex_home_without_changing_it(self):
        self.assertEqual(
            STATUS.active_codex_home({"CODEX_HOME": "/tmp/custom-codex"}, "/tmp/home"),
            Path("/tmp/custom-codex"),
        )
        self.assertEqual(STATUS.active_codex_home({}, "/tmp/home"), Path("/tmp/home/.codex"))

    def test_file_issues_accepts_copies_and_unrelated_profiles(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            active_home = home / ".codex"
            root = self.install_copies(home, active_home)
            (active_home / "agents/local.toml").write_text("local config")
            with mock.patch.object(Path, "home", return_value=home):
                self.assertEqual(STATUS.file_issues(active_home, root), [])

    def test_file_issues_rejects_drift_and_links(self):
        for mutation in ("bytes", "mode", "file-link", "ancestor-link", "hook-bytes", "hook-mode", "hook-link", "hooks-link"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                home = Path(temporary)
                active_home = home / ".codex"
                root = self.install_copies(home, active_home)
                source = root / "dotfiles/shared/codex"
                profile = active_home / "agents" / STATUS.PROFILES[0]
                script = active_home / "hooks/validate-agent-route.py"
                if mutation == "bytes":
                    profile.write_text("altered")
                elif mutation == "mode":
                    profile.chmod(profile.stat().st_mode ^ 0o100)
                elif mutation == "file-link":
                    profile.unlink()
                    profile.symlink_to(source / "agents" / profile.name)
                elif mutation == "ancestor-link":
                    shutil.rmtree(active_home / "agents")
                    (active_home / "agents").symlink_to(source / "agents", target_is_directory=True)
                elif mutation == "hook-bytes":
                    script.write_text("altered")
                elif mutation == "hook-mode":
                    script.chmod(script.stat().st_mode ^ 0o100)
                elif mutation == "hook-link":
                    script.unlink()
                    script.symlink_to(source / "hooks/validate-agent-route.py")
                else:
                    (active_home / "hooks.json").unlink()
                    (active_home / "hooks.json").symlink_to(root / "dotfiles/merge/codex/hooks.json")
                with mock.patch.object(Path, "home", return_value=home):
                    self.assertTrue(STATUS.file_issues(active_home, root))

    def test_runtime_status_is_eligible_when_hook_is_trusted(self):
        active_home = Path("/tmp/codex-home")
        config = {"config": {"features": {"hooks": True}, "agents": {}}}
        hooks = {"data": [{"hooks": [{
            "eventName": "preToolUse",
            "sourcePath": str((active_home / "hooks.json").resolve()),
            "command": STATUS.HOOK_COMMAND,
            "matcher": STATUS.HOOK_MATCHER,
            "handlerType": "command",
            "enabled": True,
            "trustStatus": "trusted",
        }]}]}
        self.assertEqual(STATUS.runtime_issues(config, hooks, active_home), [])
        hook = hooks["data"][0]["hooks"][0]
        hook["sourcePath"] = "/tmp/standard-home/.codex/hooks.json"
        self.assertIn("PreToolUse routing hook is absent from effective hooks",
                      STATUS.runtime_issues(config, hooks, active_home))
        hook["sourcePath"] = str((active_home / "hooks.json").resolve())
        config["config"]["agents"] = None
        self.assertEqual(STATUS.runtime_issues(config, hooks, active_home), [])
        config["config"].pop("agents")
        self.assertEqual(STATUS.runtime_issues(config, hooks, active_home), [])
        for v2 in (True, False, {}, {"tool_namespace": "collaboration"}):
            config["config"]["features"]["multi_agent_v2"] = v2
            self.assertEqual(STATUS.runtime_issues(config, hooks, active_home), [])
        config["config"]["features"]["multi_agent_v2"] = {"tool_namespace": "custom"}
        self.assertIn(
            "custom subagent tool namespaces are unsupported by the routing matcher",
            STATUS.runtime_issues(config, hooks, active_home),
        )
        config["config"]["features"].pop("multi_agent_v2")
        trusted_hook = hooks["data"][0]["hooks"][0]
        hooks["data"][0]["hooks"] = [
            {**trusted_hook, "enabled": False},
            {**trusted_hook, "trustStatus": "untrusted"},
        ]
        self.assertIn(
            "no PreToolUse routing hook is both enabled and trusted",
            STATUS.runtime_issues(config, hooks, active_home),
        )

    def test_runtime_status_reports_disabled_and_untrusted_hook(self):
        active_home = Path("/tmp/codex-home")
        config = {"config": {
            "features": {"hooks": False},
            "agents": {"enabled": False},
        }}
        hooks = {"data": [{"hooks": [{
            "eventName": "preToolUse",
            "sourcePath": str((active_home / "hooks.json").resolve()),
            "command": STATUS.HOOK_COMMAND,
            "matcher": STATUS.HOOK_MATCHER,
            "handlerType": "command",
            "enabled": False,
            "trustStatus": "untrusted",
        }]}]}
        issues = STATUS.runtime_issues(config, hooks, active_home)
        self.assertIn("features.hooks is disabled", issues)
        self.assertIn("agents are disabled", issues)
        self.assertIn("PreToolUse routing hook is disabled", issues)
        self.assertIn("PreToolUse routing hook is untrusted or unknown", issues)

    def test_runtime_status_rejects_missing_or_unknown_hook_data(self):
        issues = STATUS.runtime_issues({"config": {"agents": {}}}, {}, Path("/tmp/codex-home"))
        self.assertEqual(issues, ["Codex returned no hook status"])
        self.assertIn(
            "PreToolUse routing hook is absent from effective hooks",
            STATUS.runtime_issues({"config": {"agents": {}}}, {"data": []}, Path("/tmp/codex-home")),
        )

    def test_request_reads_split_response_after_notification(self):
        child = (
            "import sys,time; sys.stdin.readline(); "
            "sys.stdout.write('{\\\"method\\\":\\\"notice\\\"}\\n'); sys.stdout.flush(); "
            "sys.stdout.write('{\\\"id\\\":1,'); sys.stdout.flush(); time.sleep(.01); "
            "sys.stdout.write('\\\"result\\\":{\\\"ok\\\":true}}\\n'); sys.stdout.flush()"
        )
        process = subprocess.Popen(
            [sys.executable, "-c", child], stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0,
        )
        try:
            result = STATUS.request(process, {"buffer": b""}, 1, "test/read", {}, time.monotonic() + 1)
        finally:
            process.terminate()
            process.wait(timeout=1)
            process.stdin.close()
            process.stdout.close()
        self.assertEqual(result, {"ok": True})

    def test_request_times_out_on_partial_line(self):
        child = "import sys,time; sys.stdin.readline(); sys.stdout.write('{\\\"id\\\":1'); sys.stdout.flush(); time.sleep(2)"
        process = subprocess.Popen(
            [sys.executable, "-c", child], stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0,
        )
        try:
            with self.assertRaises(TimeoutError):
                STATUS.request(process, {"buffer": b""}, 1, "test/read", {}, time.monotonic() + .05)
        finally:
            process.terminate()
            process.wait(timeout=1)
            process.stdin.close()
            process.stdout.close()


if __name__ == "__main__":
    unittest.main()

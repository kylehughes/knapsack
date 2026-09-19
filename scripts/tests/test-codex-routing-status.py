#!/usr/bin/env python3
"""Tests for the read-only Codex routing status checker."""

import importlib.util
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
    def test_explicit_role_references_work_without_mirrored_agents_directory(self):
        root = Path(__file__).resolve().parents[2]
        source = root / "dotfiles/link/codex"
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            active_home = home / "runtime"
            active_home.mkdir()
            (active_home / "hooks.json").write_text('{"hooks":{},"description":"app-managed"}')
            (home / ".codex").mkdir()
            (home / ".codex/hooks").symlink_to(source / "hooks", target_is_directory=True)
            agents = {
                Path(profile).stem.replace("-", "_"): {"config_file": str(source / "agents" / profile)}
                for profile in STATUS.PROFILES
            }
            config = {"config": {"agents": agents}}
            with mock.patch.object(Path, "home", return_value=home):
                self.assertEqual(STATUS.file_issues(active_home, root, config), [])
                agents["knapsack_mechanical"]["config_file"] = str(home / "missing.toml")
                self.assertIn("missing agent profile knapsack-mechanical.toml", STATUS.file_issues(active_home, root, config))

    def test_active_home_prefers_codex_home_without_changing_it(self):
        self.assertEqual(
            STATUS.active_codex_home({"CODEX_HOME": "/tmp/custom-codex"}, "/tmp/home"),
            Path("/tmp/custom-codex"),
        )
        self.assertEqual(STATUS.active_codex_home({}, "/tmp/home"), Path("/tmp/home/.codex"))

    def test_file_issues_accepts_byte_equal_active_home(self):
        root = Path(__file__).resolve().parents[2]
        source = root / "dotfiles/link/codex"
        with tempfile.TemporaryDirectory() as temporary:
            active_home = Path(temporary) / ".codex"
            (active_home / "agents").mkdir(parents=True)
            for profile in STATUS.PROFILES:
                (active_home / "agents" / profile).write_bytes((source / "agents" / profile).read_bytes())
            (active_home / "hooks.json").write_bytes((source / "hooks.json").read_bytes())
            original_home = Path.home
            Path.home = classmethod(lambda cls: source.parent.parent.parent.parent / "missing-home")
            try:
                issues = STATUS.file_issues(active_home, root)
            finally:
                Path.home = original_home
            self.assertIn("$HOME/.codex hook script does not resolve to Knapsack", issues)

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

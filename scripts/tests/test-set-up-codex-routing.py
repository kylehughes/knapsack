#!/usr/bin/env python3
"""Tests for the bounded Codex native routing setup command."""

import importlib.util
import contextlib
import io
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "set-up-codex-routing.py"
SPEC = importlib.util.spec_from_file_location("set_up_codex_routing", SCRIPT)
SETUP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SETUP)


class FakeProcess:
    """Small process double for testing protocol request order without a live server."""

    def __init__(self):
        self.stdin = CaptureStream()
        self.stdout = CaptureStream()

    def poll(self):
        return 0


class CaptureStream:
    """Captures writes while tolerating the setup command's cleanup close."""

    def __init__(self):
        self.contents = b""

    def write(self, value):
        self.contents += value

    def flush(self):
        pass

    def close(self):
        pass


class FakeProtocol:
    """Records requests made through the shared protocol interface."""

    def __init__(self):
        self.requests = []

    def request(self, process, state, request_id, method, params, deadline):
        self.requests.append((request_id, method, params, deadline))
        return {}


class CodexRoutingSetupTests(unittest.TestCase):
    def test_missing_codex_is_skipped_without_writing_configuration(self):
        with mock.patch.object(SETUP.shutil, "which", return_value=None), mock.patch.object(SETUP, "register_native_routes") as register, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(SETUP.main(), 0)
            register.assert_not_called()
    def test_batch_write_has_only_the_owned_role_registrations(self):
        home = Path("/tmp/native-codex")
        params = SETUP.batch_write_params(home)
        self.assertEqual(params["filePath"], "/tmp/native-codex/config.toml")
        self.assertFalse(params["reloadUserConfig"])
        self.assertEqual([edit["keyPath"] for edit in params["edits"]], [
            "agents.knapsack_mechanical",
            "agents.knapsack_ordinary",
            "agents.knapsack_difficult",
            "agents.knapsack_override",
        ])
        for edit in params["edits"]:
            self.assertEqual(edit["mergeStrategy"], "upsert")
            self.assertEqual(set(edit["value"]), {"description", "config_file"})
            self.assertTrue(edit["value"]["config_file"].startswith("/tmp/native-codex/agents/"))
        rendered = repr(params)
        for forbidden in ("features", "hooks", "trust", "approval", "model", "credential", "private"):
            self.assertNotIn(forbidden, rendered)

    def test_missing_native_profiles_blocks_any_server_launch(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / ".codex"
            self.assertEqual(set(SETUP.native_profile_issues(home)), {
                "knapsack-mechanical.toml",
                "knapsack-ordinary.toml",
                "knapsack-difficult.toml",
                "knapsack-override.toml",
            })

    def test_registers_through_initialize_and_one_batch_write(self):
        protocol = FakeProtocol()
        process = FakeProcess()
        original_popen = SETUP.subprocess.Popen
        calls = []
        original_environment = dict(os.environ)
        SETUP.subprocess.Popen = lambda *args, **kwargs: calls.append((args, kwargs)) or process
        try:
            SETUP.register_native_routes(
                Path("/tmp/native-codex"), protocol, time.monotonic() + 1,
            )
        finally:
            SETUP.subprocess.Popen = original_popen
        self.assertEqual([request[1] for request in protocol.requests], ["initialize", "config/batchWrite"])
        self.assertEqual(calls[0][0][0], ["codex", "app-server", "--stdio"])
        self.assertNotIn("CODEX_HOME", calls[0][1]["env"])
        self.assertEqual(dict(os.environ), original_environment)
        self.assertTrue(protocol.requests[0][2]["capabilities"]["experimentalApi"])
        self.assertEqual(protocol.requests[1][2], SETUP.batch_write_params(Path("/tmp/native-codex")))
        self.assertEqual(
            process.stdin.contents,
            b'{"jsonrpc":"2.0","method":"initialized","params":{}}\n',
        )

    def test_main_never_launches_when_native_profiles_are_missing(self):
        original_home = SETUP.Path.home
        original_register = SETUP.register_native_routes
        SETUP.Path.home = classmethod(lambda cls: Path("/tmp/no-codex-routing-home"))
        SETUP.register_native_routes = lambda *args: self.fail("attempted a live configuration write")
        try:
            with mock.patch.object(SETUP.shutil, "which", return_value="/test/codex"), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(SETUP.main(), 1)
        finally:
            SETUP.Path.home = original_home
            SETUP.register_native_routes = original_register


if __name__ == "__main__":
    unittest.main()

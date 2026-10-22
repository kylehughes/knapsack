#!/usr/bin/env python3
"""Exercise IPA serving with isolated Tailscale and Xcode command fixtures."""

import html
import json
import os
import plistlib
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.parse
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "dotfiles/shared/config/zsh/scripts/tailscale-serve-ipa.py"
WRAPPER = ROOT / "dotfiles/shared/config/zsh/functions/tailscale-serve-ipa"

MOCK = r'''import json, os, pathlib, shutil, signal, sys, time
root = pathlib.Path(os.environ["FIXTURE_ROOT"])
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with (root / "processes.jsonl").open("a") as stream:
    stream.write(json.dumps([os.getpid(), os.getpgrp(), name]) + "\n")
with (root / "commands.jsonl").open("a") as stream:
    stream.write(json.dumps([name, *args]) + "\n")
if name == "tailscale":
    if args == ["status", "--json"]:
        print(json.dumps({"BackendState": os.environ.get("BACKEND_STATE", "Running"), "Self": {"DNSName": "fixture.example.ts.net."}}))
        sys.exit(0)
    if args[0] != "serve":
        sys.exit(91)
    import urllib.request
    # Loopback fixture traffic must not consult the machine's network proxy settings.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    target = args[-1]
    (root / "target").write_text(target)
    for path, output in [("/manifest.plist", "manifest.plist"), ("/", "index.html"), ("/app.ipa", "served.ipa")]:
        with (root / "requests.log").open("a") as stream:
            stream.write("fetching " + path + "\n")
        with opener.open(target + path, timeout=3) as response:
            (root / output).write_bytes(response.read())
        with (root / "requests.log").open("a") as stream:
            stream.write("received " + path + "\n")
    (root / "ready").write_text("ready")
    if os.environ.get("SERVE_MODE") == "wait":
        while True:
            time.sleep(0.05)
    sys.exit(int(os.environ.get("SERVE_EXIT", "0")))
if name == "xcodebuild":
    if os.environ.get("BUILD_DESCENDANT") == "1":
        child = os.fork()
        if child == 0:
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            (root / "descendant.pid").write_text(str(os.getpid()))
            (root / "build-ready").write_text("ready")
            while True:
                time.sleep(0.05)
        while True:
            time.sleep(0.05)
    if os.environ.get("BUILD_FAIL") == "1":
        sys.exit(42)
    if "-exportArchive" in args:
        destination = pathlib.Path(args[args.index("-exportPath") + 1])
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / "fixture.ipa", destination / "Fixture.ipa")
    sys.exit(0)
sys.exit(92)
'''


class ServeIPATests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="test-serve-ipa-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.scratch = self.root / "scratch"
        self.scratch.mkdir()
        diagnostics = self.root / "diagnostics"
        diagnostics.mkdir()
        (diagnostics / "sitecustomize.py").write_text(
            "import faulthandler\nfaulthandler.dump_traceback_later(5)\n")
        self.env = dict(os.environ, PATH=str(self.bin), FIXTURE_ROOT=str(self.root),
                        TMPDIR=str(self.scratch), PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(diagnostics))
        (self.bin / "python3").symlink_to(sys.executable)
        for name in ("tailscale", "xcodebuild"):
            path = self.bin / name
            path.write_text(f"#!{sys.executable}\n" + MOCK)
            path.chmod(0o755)
        self.ipa = self.root / "fixture.ipa"
        self.write_ipa()

    def write_ipa(self, metadata=None, binary=False, entries=None):
        if metadata is None:
            metadata = {"CFBundleIdentifier": "com.example.fixture", "CFBundleVersion": "42",
                        "CFBundleShortVersionString": "1.2", "CFBundleDisplayName": "Fixture"}
        with zipfile.ZipFile(self.ipa, "w") as archive:
            archive.writestr("Payload/Fixture.app/Info.plist", plistlib.dumps(
                metadata, fmt=plistlib.FMT_BINARY if binary else plistlib.FMT_XML))
            for name, contents in (entries or {}).items():
                archive.writestr(name, contents)

    def run_helper(self, args=None, env=None, command=None):
        argv = command or [sys.executable, "-B", str(SCRIPT),
                           *(args if args is not None else [str(self.ipa)])]
        process_log = self.root / "processes.jsonl"
        previous_records = len(process_log.read_text().splitlines()) if process_log.exists() else 0
        process = subprocess.Popen(argv, env=dict(self.env, **(env or {})), cwd=self.root,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            stdout, stderr = process.communicate(timeout=8)
        except subprocess.TimeoutExpired as error:
            diagnostics = self.fixture_diagnostics()
            process.send_signal(signal.SIGTERM)
            try:
                stdout, stderr = process.communicate(timeout=8)
            except subprocess.TimeoutExpired:
                # The helper gives commands their own group, so kill recorded mocks too.
                if process_log.exists():
                    for line in process_log.read_text().splitlines()[previous_records:]:
                        pid, group, _ = json.loads(line)
                        try:
                            if os.getpgid(pid) == group:
                                os.killpg(group, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                stdout, stderr = process.communicate(timeout=3)
            self.fail(f"helper timed out after 8 seconds: {argv!r}\n"
                      f"stdout: {(stdout or error.stdout or b'').decode(errors='replace')}\n"
                      f"stderr: {(stderr or error.stderr or b'').decode(errors='replace')}\n{diagnostics}")
        return subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)

    def fixture_diagnostics(self):
        details = []
        for name in ("commands.jsonl", "processes.jsonl", "requests.log", "target", "ready", "build-ready"):
            path = self.root / name
            details.append(f"{name}: {path.read_text() if path.exists() else '<absent>'}")
        details.append(f"temporary files: {[str(path.relative_to(self.scratch)) for path in self.scratch.rglob('*')]}")
        return "\n".join(details)

    def commands(self):
        path = self.root / "commands.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def assert_clean(self):
        self.assertEqual(list(self.scratch.iterdir()), [], "temporary serving files remain")
        target = self.root / "target"
        if target.exists():
            port = urllib.parse.urlsplit(target.read_text()).port
            with socket.socket() as connection:
                connection.settimeout(0.3)
                self.assertNotEqual(connection.connect_ex(("127.0.0.1", port)), 0,
                                    "loopback server still accepts connections")

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stderr.decode() + result.stdout.decode())
        self.assertTrue((self.root / "ready").exists(), "serve never reached the listener")
        self.assert_clean()

    def test_malformed_and_conflicting_inputs_fail_promptly(self):
        cases = [[], [str(self.ipa), str(self.ipa)], ["--port"], ["--scheme"],
                 ["--workspace"], ["--configuration"], ["--unknown"],
                 [str(self.ipa), "--scheme", "Fixture"],
                 ["--scheme", "Fixture", "--workspace", "A", "--project", "B"],
                 [str(self.ipa), "--configuration", "Release"],
                 [str(self.ipa), "--workspace", "A"],
                 [str(self.ipa), "--port", "0"], [str(self.ipa), "--port", "65536"],
                 [str(self.ipa), "--port", "abc"]]
        for args in cases:
            with self.subTest(args=args):
                self.assertNotEqual(self.run_helper(args).returncode, 0)
        self.assertEqual(self.commands(), [])
        self.assert_clean()

    def test_xml_metadata_and_listener_ready_before_serve(self):
        self.assert_success(self.run_helper())
        manifest = plistlib.loads((self.root / "manifest.plist").read_bytes())
        metadata = manifest["items"][0]["metadata"]
        self.assertEqual(metadata["bundle-identifier"], "com.example.fixture")
        self.assertEqual(metadata["bundle-version"], "42")
        self.assertEqual((self.root / "served.ipa").read_bytes(), self.ipa.read_bytes())
        serve = self.commands()[-1]
        self.assertEqual(serve[:3], ["tailscale", "serve", "--https=8443"])
        self.assertRegex(serve[-1], r"^http://127\.0\.0\.1:[1-9][0-9]*$")
        self.assertFalse(any(command[0] == "xcodebuild" for command in self.commands()))

    def test_binary_plist_ignores_nested_watch_app(self):
        self.write_ipa(binary=True, entries={"Payload/Fixture.app/Watch/Watch.app/Info.plist":
            plistlib.dumps({"CFBundleIdentifier": "wrong.watch", "CFBundleVersion": "999"})})
        self.assert_success(self.run_helper())
        metadata = plistlib.loads((self.root / "manifest.plist").read_bytes())["items"][0]["metadata"]
        self.assertEqual(metadata["bundle-identifier"], "com.example.fixture")

    def test_html_escaping_and_encoded_install_url(self):
        title = 'A <script> & "quoted" app'
        self.write_ipa({"CFBundleIdentifier": "com.example.fixture", "CFBundleVersion": "42",
                        "CFBundleDisplayName": title})
        self.assert_success(self.run_helper())
        page = (self.root / "index.html").read_text()
        self.assertNotIn("<script>", page)
        self.assertIn(html.escape(title), page)
        match = re.search(r'href=[\'"](itms-services:[^\'"]+)', page)
        self.assertIsNotNone(match)
        link = html.unescape(match.group(1))
        self.assertIn("url=https%3A%2F%2F", link)
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(link).query)
        self.assertEqual(query["action"], ["download-manifest"])
        self.assertTrue(query["url"][0].startswith("https://fixture.example.ts.net:8443/manifest.plist"))

    def test_missing_required_metadata_is_rejected(self):
        for metadata in ({"CFBundleVersion": "42"}, {"CFBundleIdentifier": "com.example.fixture"}):
            with self.subTest(metadata=metadata):
                self.write_ipa(metadata)
                self.assertNotEqual(self.run_helper().returncode, 0)
                self.assert_clean()
        self.assertFalse(any(command[1] == "serve" for command in self.commands()))

    def test_ambiguous_or_malformed_ipa_is_rejected(self):
        self.write_ipa(entries={"Payload/Other.app/Info.plist": plistlib.dumps({"CFBundleIdentifier": "other", "CFBundleVersion": "1"})})
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.ipa.write_bytes(b"not a zip archive")
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.write_ipa(entries={"Payload/Fixture.app/Info.plist.bad": b"ignored"})
        with zipfile.ZipFile(self.ipa, "w") as archive:
            archive.writestr("Payload/Fixture.app/Info.plist", b"not a plist")
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.assert_clean()

    def test_custom_https_port(self):
        self.assert_success(self.run_helper([str(self.ipa), "--port", "12345"]))
        self.assertIn("--https=12345", self.commands()[-1])

    def test_ipa_does_not_require_xcodebuild_but_requires_tailscale(self):
        (self.bin / "xcodebuild").unlink()
        self.assert_success(self.run_helper())
        (self.bin / "tailscale").unlink()
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.assert_clean()

    def test_workspace_build_preserves_arguments_with_spaces(self):
        workspace = self.root / "My Project.xcworkspace"
        workspace.mkdir()
        self.assert_success(self.run_helper(["--scheme", "App/Debug Scheme", "--workspace", str(workspace),
                                             "--configuration", "Special Debug"]))
        commands = [command for command in self.commands() if command[0] == "xcodebuild"]
        self.assertEqual(len(commands), 2)
        archive = commands[0]
        for flag, value in (("-scheme", "App/Debug Scheme"), ("-workspace", str(workspace)),
                            ("-configuration", "Special Debug"), ("-destination", "generic/platform=iOS")):
            self.assertEqual(archive[archive.index(flag) + 1], value)
        self.assertIn("archive", archive)
        self.assertNotIn("-project", archive)
        self.assertIn("-exportArchive", commands[1])

    def test_existing_archive_exports_without_archiving(self):
        archive = self.root / "My App.xcarchive"
        archive.mkdir()
        self.assert_success(self.run_helper([str(archive)]))
        commands = [command for command in self.commands() if command[0] == "xcodebuild"]
        self.assertEqual(len(commands), 1)
        self.assertIn("-exportArchive", commands[0])
        exported_archive = Path(commands[0][commands[0].index("-archivePath") + 1])
        self.assertEqual(exported_archive.resolve(), archive.resolve())

    def test_failed_build_cleans_temporary_files(self):
        result = self.run_helper(["--scheme", "Fixture"], env={"BUILD_FAIL": "1"})
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(command[1] == "serve" for command in self.commands()))
        self.assert_clean()

    def test_build_cancellation_stops_descendant_after_leader_exits(self):
        process = subprocess.Popen([sys.executable, "-B", str(SCRIPT), "--scheme", "Fixture"],
            env=dict(self.env, BUILD_DESCENDANT="1"), cwd=self.root,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        child_pid = None
        try:
            deadline = time.monotonic() + 6
            while not (self.root / "build-ready").exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            if not (self.root / "build-ready").exists():
                process.send_signal(signal.SIGTERM)
                stdout, stderr = process.communicate(timeout=8)
                self.fail(f"archive did not start its descendant\n{self.fixture_diagnostics()}\n"
                          f"stdout: {stdout.decode(errors='replace')}\nstderr: {stderr.decode(errors='replace')}")
            child_pid = int((self.root / "descendant.pid").read_text())
            process.send_signal(signal.SIGTERM)
            process.communicate(timeout=10)
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                try:
                    os.kill(child_pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.02)
            else:
                self.fail("archive descendant survived cancellation after its leader exited")
            self.assert_clean()
        finally:
            if child_pid is not None:
                try:
                    os.kill(child_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate(timeout=3)

    def test_failed_serve_cleans_temporary_files_and_listener(self):
        self.assertNotEqual(self.run_helper(env={"SERVE_EXIT": "17"}).returncode, 0)
        self.assertTrue((self.root / "ready").exists())
        self.assert_clean()

    def test_stopped_tailscale_is_rejected(self):
        self.assertNotEqual(self.run_helper(env={"BACKEND_STATE": "Stopped"}).returncode, 0)
        self.assertFalse(any(command[1] == "serve" for command in self.commands()))
        self.assert_clean()

    def test_interrupt_and_termination_clean_listener_and_files(self):
        for sig in (signal.SIGINT, signal.SIGTERM):
            with self.subTest(signal=sig):
                (self.root / "ready").unlink(missing_ok=True)
                process = subprocess.Popen([sys.executable, "-B", str(SCRIPT), str(self.ipa)],
                    env=dict(self.env, SERVE_MODE="wait"), cwd=self.root,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
                try:
                    deadline = time.monotonic() + 6
                    while not (self.root / "ready").exists() and process.poll() is None and time.monotonic() < deadline:
                        time.sleep(0.02)
                    if not (self.root / "ready").exists():
                        process.send_signal(signal.SIGTERM)
                        stdout, stderr = process.communicate(timeout=8)
                        self.fail(f"serve did not become ready\n{self.fixture_diagnostics()}\n"
                                  f"stdout: {stdout.decode(errors='replace')}\nstderr: {stderr.decode(errors='replace')}")
                    process.send_signal(sig)
                    process.communicate(timeout=5)
                    self.assert_clean()
                finally:
                    # A broken cleanup must not leave a mock child holding the pipes open.
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.communicate(timeout=3)

    def test_direct_and_autoloaded_wrapper_preserve_shell_state(self):
        zsh = shutil.which("zsh")
        self.assertIsNotNone(zsh)
        self.assert_success(self.run_helper(command=[zsh, str(WRAPPER), str(self.ipa)]))
        command = '''fpath=("$1" $fpath)
autoload -Uz tailscale-serve-ipa
before_options=$(setopt)
trap ':' USR1
before_traps=$(trap)
tailscale-serve-ipa "$2" || exit $?
[[ "$before_options" == "$(setopt)" && "$before_traps" == "$(trap)" ]]'''
        self.assert_success(self.run_helper(command=[zsh, "-f", "-c", command, "fixture", str(WRAPPER.parent), str(self.ipa)]))


if __name__ == "__main__":
    unittest.main()

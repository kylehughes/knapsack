#!/usr/bin/env python3
"""Register Knapsack's native Codex routing profiles.

Usage: scripts/set-up-codex-routing.py
"""

import importlib.util
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


TIMEOUT_SECONDS = 9.0


def load_protocol_helper():
    """Load the checked routing-status protocol helper without copying it."""
    checker = Path(__file__).with_name("check-codex-routing.py")
    spec = importlib.util.spec_from_file_location("knapsack_codex_routing_status", checker)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load the Codex routing protocol helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


STATUS = load_protocol_helper()
# Each tracked route profile registers one role, named for its file.
ROLES = tuple(
    (Path(profile).stem.replace("-", "_"), profile,
     "Knapsack " + Path(profile).stem[:-len("-worker")] + " work route.")
    for profile in STATUS.PROFILES
)


def native_profile_issues(codex_home):
    """Return missing native files before requesting a configuration write."""
    return [
        profile
        for _, profile, _ in ROLES
        if not (codex_home / "agents" / profile).is_file()
    ]


def batch_write_params(codex_home):
    """Build the supported, narrowly-scoped native profile registrations."""
    return {
        "filePath": str(codex_home / "config.toml"),
        "reloadUserConfig": False,
        "edits": [
            {
                "keyPath": "agents." + role,
                "value": {
                    "description": description,
                    "config_file": str(codex_home / "agents" / profile),
                },
                "mergeStrategy": "upsert",
            }
            for role, profile, description in ROLES
        ] + [
            # A null value clears the key. A retired role would otherwise keep
            # pointing at a profile the installer has removed.
            {"keyPath": "agents." + role, "value": None, "mergeStrategy": "replace"}
            for role in STATUS.RETIRED_ROLES
        ],
    }


def close_process(process, deadline):
    """Close the owned app-server and its pipes without extending its request bound."""
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=min(0.5, max(0.0, deadline - time.monotonic())))
        except subprocess.TimeoutExpired:
            process.kill()
            try:
                process.wait(timeout=0.1)
            except subprocess.TimeoutExpired:
                pass
    for stream in (process.stdin, process.stdout):
        if stream is not None:
            stream.close()


def register_native_routes(codex_home, protocol, deadline):
    """Write only Knapsack's native role registrations through Codex app-server."""
    # Setup owns the standard user configuration. Let Codex use its normal home
    # instead of inheriting an app's private runtime home into this child process.
    environment = os.environ.copy()
    environment.pop("CODEX_HOME", None)
    process = subprocess.Popen(
        ["codex", "app-server", "--stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
        env=environment,
    )
    try:
        state = {"buffer": b""}
        protocol.request(
            process,
            state,
            1,
            "initialize",
            {
                "clientInfo": {"name": "knapsack-routing-setup", "version": "1"},
                "capabilities": {"experimentalApi": True},
            },
            deadline,
        )
        process.stdin.write(b'{"jsonrpc":"2.0","method":"initialized","params":{}}\n')
        process.stdin.flush()
        protocol.request(
            process,
            state,
            2,
            "config/batchWrite",
            batch_write_params(codex_home),
            deadline,
        )
    finally:
        close_process(process, deadline)


def main():
    """Register installed Knapsack role files without reading or exposing config data."""
    if shutil.which("codex") is None:
        print("Codex routing setup: Codex is not installed; skipping registration.")
        return 0
    codex_home = Path.home() / ".codex"
    missing = native_profile_issues(codex_home)
    if missing:
        print("Codex routing setup: missing native agent profile " + ", ".join(missing) + ".")
        return 1
    deadline = time.monotonic() + TIMEOUT_SECONDS
    try:
        register_native_routes(codex_home, STATUS, deadline)
    except FileNotFoundError:
        print("Codex routing setup: codex CLI is not installed.")
        return 2
    except (OSError, RuntimeError, TimeoutError):
        print("Codex routing setup: could not register native role routes.")
        return 1
    print(f"Codex routing setup: registered {len(ROLES)} native role routes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Report whether Codex agent-routing files are configured and trusted.

Usage: scripts/check-codex-routing.py
"""

import json
import os
import select
import subprocess
import sys
import time
from pathlib import Path


PROFILES = (
    "knapsack-mechanical.toml",
    "knapsack-ordinary.toml",
    "knapsack-difficult.toml",
    "knapsack-override.toml",
)
HOOK_COMMAND = 'python3 "$HOME/.codex/hooks/validate-agent-route.py"'
HOOK_MATCHER = "^(spawn_agent|Agent|collaborationspawn_agent)$"
TIMEOUT_SECONDS = 9.0
MAX_PROTOCOL_BYTES = 1_048_576


def active_codex_home(environment=None, home=None):
    """Return the Codex home selected by the current environment."""
    environment = os.environ if environment is None else environment
    home = Path.home() if home is None else Path(home)
    configured = environment.get("CODEX_HOME")
    return Path(configured) if configured else home / ".codex"


def repository_root():
    """Return the repository root from this script's known location."""
    return Path(__file__).resolve().parents[1]


def file_issues(active_home, root, config_result=None):
    """Return routing-file differences without changing any installed files."""
    issues = []
    source = root / "dotfiles/link/codex"
    config = (config_result or {}).get("config") or {}
    agents = config.get("agents") if isinstance(config, dict) else None
    for profile in PROFILES:
        expected = source / "agents" / profile
        installed = active_home / "agents" / profile
        role_name = Path(profile).stem.replace("-", "_")
        role = agents.get(role_name) if isinstance(agents, dict) else None
        if isinstance(role, dict) and isinstance(role.get("config_file"), str):
            reference = Path(role["config_file"])
            installed = reference if reference.is_absolute() else active_home / reference
        try:
            if not installed.is_file():
                issues.append("missing agent profile " + profile)
            elif installed.read_bytes() != expected.read_bytes():
                issues.append("agent profile differs " + profile)
        except OSError:
            issues.append("could not read agent profile " + profile)

    installed_hooks = active_home / "hooks.json"
    try:
        if not installed_hooks.is_file():
            issues.append("missing hooks.json")
    except OSError:
        issues.append("could not read hooks.json")

    expected_script = source / "hooks" / "validate-agent-route.py"
    live_script = Path.home() / ".codex/hooks/validate-agent-route.py"
    try:
        script_matches = live_script.exists() and live_script.resolve() == expected_script.resolve()
    except OSError:
        script_matches = False
    if not script_matches:
        issues.append("$HOME/.codex hook script does not resolve to Knapsack")
    return issues


def runtime_issues(config_result, hooks_result, active_home):
    """Classify the effective runtime configuration and its hook trust metadata."""
    issues = []
    config = config_result.get("config") if isinstance(config_result, dict) else None
    if not isinstance(config, dict):
        return ["Codex returned no effective configuration"]

    features = config.get("features")
    if isinstance(features, dict) and features.get("hooks") is False:
        issues.append("features.hooks is disabled")
    if features is not None and not isinstance(features, dict):
        issues.append("Codex returned an unknown features configuration shape")
    v2 = features.get("multi_agent_v2") if isinstance(features, dict) else None
    if isinstance(v2, dict):
        if v2.get("tool_namespace", "collaboration") != "collaboration":
            issues.append("custom subagent tool namespaces are unsupported by the routing matcher")
    elif v2 is not None and not isinstance(v2, bool):
        issues.append("Codex returned an unknown multi_agent_v2 configuration shape")
    agents = config.get("agents")
    if agents is None:
        agents = {}
    if not isinstance(agents, dict):
        return issues + ["Codex returned an unknown agent configuration shape"]
    for key in ("default_subagent_model", "default_subagent_reasoning_effort"):
        if agents.get(key) is not None:
            issues.append(key + " overrides difficult-route inheritance")
    if agents.get("enabled") is False:
        issues.append("agents are disabled")

    expected_source = (active_home / "hooks.json").resolve()
    matching = []
    entries = hooks_result.get("data") if isinstance(hooks_result, dict) else None
    if not isinstance(entries, list):
        return issues + ["Codex returned no hook status"]
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        hooks = entry.get("hooks")
        if not isinstance(hooks, list):
            continue
        for hook in hooks:
            if not isinstance(hook, dict):
                continue
            if hook.get("eventName") != "preToolUse":
                continue
            source_path = hook.get("sourcePath")
            if not isinstance(source_path, str) or Path(source_path).resolve() != expected_source:
                continue
            if hook.get("command") != HOOK_COMMAND:
                continue
            if hook.get("matcher") != HOOK_MATCHER or hook.get("handlerType") != "command":
                continue
            matching.append(hook)
    if not matching:
        issues.append("PreToolUse routing hook is absent from effective hooks")
        return issues
    eligible = [hook for hook in matching if hook.get("enabled") is True and hook.get("trustStatus") in ("trusted", "managed")]
    if eligible:
        return issues
    if not any(hook.get("enabled") is True for hook in matching):
        issues.append("PreToolUse routing hook is disabled")
    if not any(hook.get("trustStatus") in ("trusted", "managed") for hook in matching):
        issues.append("PreToolUse routing hook is untrusted or unknown")
    if not issues or issues[-1] not in ("PreToolUse routing hook is disabled", "PreToolUse routing hook is untrusted or unknown"):
        issues.append("no PreToolUse routing hook is both enabled and trusted")
    return issues


def request(process, state, request_id, method, params, deadline):
    """Send one JSON-RPC request and return its result before the shared deadline."""
    payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
    process.stdin.write((json.dumps(payload) + "\n").encode())
    process.stdin.flush()
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Codex status query timed out")
        ready, _, _ = select.select([process.stdout], [], [], remaining)
        if not ready:
            raise TimeoutError("Codex status query timed out")
        chunk = os.read(process.stdout.fileno(), 4096)
        if not chunk:
            raise RuntimeError("Codex app-server closed before returning status")
        state["buffer"] += chunk
        if len(state["buffer"]) > MAX_PROTOCOL_BYTES:
            raise RuntimeError("Codex status response exceeded its bound")
        lines = state["buffer"].split(b"\n")
        state["buffer"] = lines.pop()
        for line in lines:
            try:
                message = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if not isinstance(message, dict) or message.get("id") != request_id:
                continue
            if "error" in message:
                raise RuntimeError("Codex rejected " + method)
            return message.get("result")


def read_runtime_status(cwd, deadline):
    """Read effective configuration and hook metadata from an owned app-server."""
    try:
        process = subprocess.Popen(
            ["codex", "app-server", "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )
    except FileNotFoundError:
        raise
    try:
        state = {"buffer": b""}
        request(process, state, 1, "initialize", {
            "clientInfo": {"name": "knapsack-routing-status", "version": "1"},
            "capabilities": {"experimentalApi": True},
        }, deadline)
        process.stdin.write(b'{"jsonrpc":"2.0","method":"initialized","params":{}}\n')
        process.stdin.flush()
        config = request(process, state, 2, "config/read", {"cwd": str(cwd)}, deadline)
        hooks = request(process, state, 3, "hooks/list", {"cwds": [str(cwd)]}, deadline)
        return config, hooks
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=min(0.5, max(0.1, deadline - time.monotonic())))
            except subprocess.TimeoutExpired:
                process.kill()
                try:
                    process.wait(timeout=0.1)
                except subprocess.TimeoutExpired:
                    pass
        if process.stdin is not None:
            process.stdin.close()
        if process.stdout is not None:
            process.stdout.close()


def main():
    """Print route-specific eligibility without starting a thread or model call."""
    active_home = active_codex_home()
    config = None
    issues = []
    deadline = time.monotonic() + TIMEOUT_SECONDS
    try:
        config, hooks = read_runtime_status(Path.cwd(), deadline)
    except FileNotFoundError:
        print("Codex routing: codex CLI is not installed.")
        return 2
    except (OSError, RuntimeError, TimeoutError):
        issues.append("could not read effective Codex routing status")
    else:
        issues.extend(runtime_issues(config, hooks, active_home))
    issues = file_issues(active_home, repository_root(), config) + issues

    if issues:
        print("Codex routing [" + str(active_home) + "]: unenforced: " + "; ".join(issues) + ".")
        print("Install with make set-up/dotfiles and make set-up/codex-routing; start a fresh app session to refresh mirrored configuration.")
        print("Review hook trust using /hooks in Codex. Hooks must also be enabled in the source configuration.")
        print("Actual spawn interception needs a runtime smoke test.")
        return 1
    print("Codex routing [" + str(active_home) + "]: configured and trusted eligibility confirmed.")
    print("Actual spawn interception needs a runtime smoke test.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

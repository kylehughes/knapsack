#!/usr/bin/env python3
"""Check tracked repository source, or an isolated snapshot of the Git index."""

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

BASELINE = "scripts/runtime-artifacts-stage-one.json"
ALIASES = {
    "dotfiles/link/codex/AGENTS.md": "../claude/CLAUDE.md",
    "dotfiles/link/gemini/GEMINI.md": "../claude/CLAUDE.md",
    "dotfiles/link/gemini/agents": "../claude/agents",
}
AGENT_RUNTIME = {
    "auth.json", "credentials.json", ".credentials.json", "sessions", "sessions.json",
    "session-env", "projects", "history.jsonl", "history.json", "cache", "logs",
    "debug", "todos", "shell-snapshots", "telemetry", "stats-cache.json", "tmp",
    "settings.local.json", "settings.machine.json", "state", "sqlite", "backups",
    "oauth_creds.json", "google_accounts.json", "trustedFolders.json",
}


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def forbidden(path):
    parts = Path(path).parts
    name = parts[-1]
    if "__pycache__" in parts or name.endswith((".pyc", ".pyo", ".bak", ".orig", ".rej", "~")):
        return True
    if path.startswith("dotfiles/link/config/zsh/functions-local/"):
        return True
    for agent in ("claude", "codex", "gemini"):
        prefix = f"dotfiles/link/{agent}/"
        if path.startswith(prefix):
            relative = path[len(prefix):].split("/")
            if relative[0] in AGENT_RUNTIME or relative[:2] == ["skills", "synced"]:
                return True
    return False


def entries(root):
    result = {}
    for record in git(root, "ls-files", "--stage", "-z").split(b"\0"):
        if not record:
            continue
        metadata, path = record.split(b"\t", 1)
        mode, blob, stage = metadata.decode().split()
        if stage != "0":
            raise ValueError("Resolve index conflicts before checking repository source")
        result[os.fsdecode(path)] = (mode, blob)
    return result


def blob_hash(content, expected):
    algorithm = "sha256" if len(expected) == 64 else "sha1"
    return hashlib.new(algorithm, b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()


def snapshot_index(root, destination, tracked):
    # Read raw object bytes: checkout filters must never execute or change indexed source.
    blobs = [blob for mode, blob in tracked.values()]
    output = subprocess.check_output(
        ["git", "-C", str(root), "cat-file", "--batch"],
        input=("\n".join(blobs) + "\n").encode(),
    )
    offset = 0
    links = []
    for name, (mode, blob) in tracked.items():
        end = output.index(b"\n", offset)
        object_id, kind, length = output[offset:end].split()
        if kind != b"blob":
            raise ValueError(f"{name}: only source blobs are supported")
        offset = end + 1
        content = output[offset:offset + int(length)]
        offset += int(length) + 1
        path = destination / name
        if mode == "120000":
            links.append((path, content))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            path.chmod(0o755 if mode == "100755" else 0o644)
    # Materialize links last so no write follows an index-controlled alias.
    for path, content in links:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(os.fsdecode(content))


def has_orca_command(value):
    if isinstance(value, dict):
        return any(
            (key == "command" and isinstance(child, str) and "ORCA_" in child)
            or has_orca_command(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(has_orca_command(child) for child in value)
    return False


def has_symlink_parent(path, root):
    return any(parent.is_symlink() for parent in path.parents if parent != root and root in parent.parents)


def check(root, tracked):
    errors = []
    baseline_path = root / BASELINE
    if baseline_path.is_symlink() or has_symlink_parent(baseline_path, root):
        raise ValueError(f"{BASELINE}: baseline must be an ordinary source file")
    baseline = json.loads(baseline_path.read_text()) if baseline_path.exists() else {}
    if not isinstance(baseline, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in baseline.items()):
        raise ValueError(f"{BASELINE} must map exact paths to Git blob hashes")
    for name, (mode, _) in tracked.items():
        path = root / name
        if has_symlink_parent(path, root):
            errors.append(f"{name}: source traverses an unexpected directory symlink")
            continue
        if forbidden(name):
            if mode not in ("100644", "100755") or not path.is_file() or path.is_symlink():
                errors.append(f"{name}: runtime artifact is not an unchanged Stage 1 baseline file")
            elif name not in baseline or blob_hash(path.read_bytes(), baseline[name]) != baseline[name]:
                errors.append(f"{name}: runtime artifact must stay local (Stage 1 permits only exact baseline bytes)")
            continue
        if not path.exists() and not path.is_symlink():
            errors.append(f"{name}: tracked source is missing")
            continue
        if path.is_symlink():
            if name.startswith("dotfiles/link/") and name not in ALIASES:
                errors.append(f"{name}: unexpected source alias")
                continue
            target = os.readlink(path)
            if name in ALIASES and target != ALIASES[name]:
                errors.append(f"{name}: expected source alias {ALIASES[name]}")
                continue
            try:
                resolved = path.resolve(strict=True)
                relative = resolved.relative_to(root).as_posix()
            except (OSError, RuntimeError, ValueError):
                errors.append(f"{name}: source symlink is broken, cyclic, or outside the repository")
                continue
            if resolved.is_dir():
                if name != "dotfiles/link/gemini/agents" or not any(p.startswith(relative + "/") for p in tracked):
                    errors.append(f"{name}: unexpected directory alias")
            elif relative not in tracked:
                errors.append(f"{name}: source alias target is not tracked")
            continue
        if mode not in ("100644", "100755") or not path.is_file():
            errors.append(f"{name}: expected an ordinary tracked source file")
            continue
        if name in ALIASES:
            errors.append(f"{name}: expected a source symlink")
            continue
        try:
            if path.suffix == ".py":
                ast.parse(path.read_bytes(), filename=name)
            elif path.suffix == ".json":
                value = json.loads(path.read_bytes())
                if name == "dotfiles/link/codex/hooks.json" and has_orca_command(value):
                    errors.append(f"{name}: Orca runtime hook commands must stay in local configuration")
            else:
                with path.open("rb") as source:
                    first_line = source.readline(256).decode("utf-8", errors="replace").strip()
                shell = "zsh" if first_line in ("#!/usr/bin/env zsh", "#!/bin/zsh") else "bash" if first_line in ("#!/usr/bin/env bash", "#!/bin/bash") else None
                if shell:
                    result = subprocess.run([shell, "-n", str(path)], capture_output=True, text=True)
                    if result.returncode:
                        errors.append(f"{name}: {result.stderr.strip()}")
        except (SyntaxError, ValueError, UnicodeError) as error:
            errors.append(f"{name}: {error}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", help="check only indexed bytes in a temporary snapshot")
    parser.add_argument("--root", type=Path, help="repository to check (default: current Git repository)")
    args = parser.parse_args()
    try:
        root = Path(git(args.root or Path.cwd(), "rev-parse", "--show-toplevel").decode().strip()).resolve()
        tracked = entries(root)
        if args.staged:
            with tempfile.TemporaryDirectory(prefix="knapsack-index-") as temporary:
                snapshot = Path(temporary).resolve()
                snapshot_index(root, snapshot, tracked)
                errors = check(snapshot, tracked)
        else:
            errors = check(root, tracked)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Repository checks failed: {error}", file=sys.stderr)
        return 1
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print("Repository source checks passed" + (" (Git index)." if args.staged else "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())

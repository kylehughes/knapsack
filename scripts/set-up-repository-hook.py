#!/usr/bin/env python3
"""Install the repository source pre-commit hook without replacing custom hooks."""

import argparse
from pathlib import Path
import subprocess
import sys

MARKER = "# Knapsack repository source checks (managed)."
COMMAND = 'python3 -B "$(git rev-parse --show-toplevel)/scripts/check-repository.py" --staged'
HOOK = '#!/bin/sh\n' + MARKER + '\nset -eu\nexec ' + COMMAND + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        root = Path(subprocess.check_output(["git", "-C", str(args.root), "rev-parse", "--show-toplevel"], text=True).strip())
        # Git resolves core.hooksPath itself, including relative paths and worktrees.
        hook_dir = Path(subprocess.check_output(["git", "-C", str(root), "rev-parse", "--git-path", "hooks"], text=True).strip())
        if not hook_dir.is_absolute():
            hook_dir = root / hook_dir
        common_dir = Path(subprocess.check_output(["git", "-C", str(root), "rev-parse", "--git-common-dir"], text=True).strip())
        if not common_dir.is_absolute():
            common_dir = root / common_dir
        hook_dir = hook_dir.resolve()
        if not any(hook_dir == allowed or allowed in hook_dir.parents for allowed in (root.resolve(), common_dir.resolve())):
            print(f"Preserved hooksPath outside this repository: {hook_dir}\nChain this command from its pre-commit hook:\n{COMMAND}", file=sys.stderr)
            return 1
        hook = hook_dir / "pre-commit"
        if hook.is_symlink() or (hook.exists() and hook.read_bytes() != HOOK.encode()):
            print(f"Preserved custom hook: {hook}\nChain this command from that hook:\n{COMMAND}", file=sys.stderr)
            return 1
        hook_dir.mkdir(parents=True, exist_ok=True)
        if not hook.exists():
            hook.write_text(HOOK)
        hook.chmod(hook.stat().st_mode | 0o111)
        print(f"Installed repository source hook: {hook}")
        return 0
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Could not install repository hook: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

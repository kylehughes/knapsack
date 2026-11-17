#!/usr/bin/env python3
"""Install the repository's Git hooks without replacing custom hooks."""

import argparse
from pathlib import Path
import subprocess
import sys

MARKER = "# Knapsack repository source checks (managed)."
COMMAND = 'python3 -B "$(git rev-parse --show-toplevel)/scripts/check-repository.py" --staged'
HOOK = '#!/bin/sh\n' + MARKER + '\nset -eu\nexec ' + COMMAND + '\n'
INSTALL_COMMAND = 'make -C "$(git rev-parse --show-toplevel)" set-up/codex-routing'
# Git runs post-merge after a merge or fast-forward pull and post-rewrite after a
# rebasing pull. Neither can stop the pull, so a failed install only reports itself.
INSTALL_HOOK = (
    '#!/bin/sh\n# Knapsack dotfile install after a pull (managed).\n'
    '[ "${1:-}" = amend ] && exit 0\n'
    + INSTALL_COMMAND + ' || echo "Knapsack: setup needs attention; run make set-up/dotfiles" >&2\n'
    'exit 0\n'
)
HOOKS = (
    ("pre-commit", HOOK, COMMAND),
    ("post-merge", INSTALL_HOOK, INSTALL_COMMAND),
    ("post-rewrite", INSTALL_HOOK, INSTALL_COMMAND),
)


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
        preserved = 0
        for name, contents, command in HOOKS:
            hook = hook_dir / name
            if hook.is_symlink() or (hook.exists() and hook.read_bytes() != contents.encode()):
                print(f"Preserved custom hook: {hook}\nChain this command from that hook:\n{command}", file=sys.stderr)
                preserved = 1
                continue
            hook_dir.mkdir(parents=True, exist_ok=True)
            if not hook.exists():
                hook.write_text(contents)
            hook.chmod(hook.stat().st_mode | 0o111)
            print(f"Installed repository hook: {hook}")
        return preserved
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Could not install repository hook: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

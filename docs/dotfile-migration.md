# Move Dotfiles Out of the Shared Checkout

Stage 1 replaces live links with independent local copies. Stage 2 removes the
old runtime artifacts from Git. Complete Stage 1 on both the personal and work
Mac before publishing Stage 2: a pull that removes tracked files would otherwise
delete files still used through the other Mac's links.

## Stage 1: Run Separately on Each Mac

This is the recovery path for an installation that still depends on legacy
links. The current release has removed the old runtime sources and renamed
`dotfiles/link/` to `dotfiles/shared/` and `dotfiles/copy/` to `dotfiles/seed/`.
Do not pull it into a checkout that still supplies live configuration links.
First use the published Stage 1 revision
`df3759e7df92f947bfe92aa20c7cf1c70554292c` in that checkout. Preserve any existing
work before switching revisions. If cleanup has already removed a live link
target, recover from this Mac's verified backups before proceeding.

Close Claude, Codex, Orca, and other apps that write the affected configuration.
Use a separate Terminal window for the migration. Do not copy configuration,
backups, receipts, or app state from the other Mac.

```sh
cd ~/Knapsack
git fetch origin
git switch --detach df3759e7df92f947bfe92aa20c7cf1c70554292c
make plan/dotfiles
make set-up/dotfiles
make check/dotfiles
make set-up/repository-hook
```

Read the plan before applying it. Setup preserves the complete contents of
recognized legacy linked directories, including hidden files and local
additions, before replacing their links. It materializes known internal aliases
so the resulting files and backups do not depend on the checkout.

Downloaded skills remain local and unmanaged. New installations do not receive
the old tracked skill cache. Existing local functions keep their native
`~/.config/zsh/functions-local/` path. Orca keeps its own projects, accounts, and
hook entries on each Mac.

Setup refuses unexpected links, missing targets, file-type collisions, and
unrecognized local edits. It does not delete a link merely because its target is
missing. Resolve the reported path explicitly; do not force a replacement.

### Resolve Configuration Conflicts

An existing file with no known installed baseline is adopted only when it
matches the desired shared configuration. After that, setup updates it only
while it still matches the recorded version.

For a conflict, inspect the local and shared versions on that Mac. Put an
intended shared edit into the repository. Put a machine-specific edit into the
tool's local override, such as `~/.gitconfig_local` or
`~/.claude/settings.machine.json`. If a local edit should be discarded, preserve
it in a local backup before removing the destination and rerunning setup.

Claude settings preserve the existing merge semantics: objects merge
recursively, and an overlay array replaces the entire base array. Setup reports
differing key names without printing their values. An initial mismatch must be
reconciled before the migration can be considered complete.

Codex reconciliation owns only the routing handler. It preserves unrelated
hooks and metadata, including Orca's integration. A local edit to the owned
handler is a conflict; changes to unrelated handlers are not.

### Verify the Actual Runtimes

After installation, restart the apps and run:

```sh
make check/agents
make check/codex-routing
```

Run the routing check from the runtime environment you use. Orca may select a
different Codex home. Review `/hooks` and trust changed definitions locally;
setup neither enables hooks nor copies trust decisions.

Launch a fresh Codex session through Orca and verify that runtime separately.
The CLI's `agent hooks prepare-codex` command is documented for WSL panes; do not
use it for this macOS migration. If Orca's launcher fails, repair that integration
before recording Orca verification. Do not patch an app-generated Codex home or
substitute an unverified executable.

Confirm each Mac still has its own projects and that normal app use creates no
new tracked or untracked runtime files in Knapsack. Existing ignored migration
leftovers in the source tree can remain until Stage 2. Repeat the routing smoke
test described in the README; eligibility checks alone do not demonstrate that
tool interception works.

## Recovery

Setup keeps its installation ledger, migration journal, content backups, and
Stage 1 receipt under `~/.local/state/knapsack/`. These files belong to that Mac.
Keep them private and retain them through the rollout.

If setup is interrupted, rerun the same command. It uses the journal to finish
a prepared detachment and refuses ambiguous recovery state. A backup is not
considered complete until its content snapshot has been verified. Do not
manually remove the journal or staged files to silence an error.

If recovery reports ambiguity, stop the affected app, inspect the paths in the
local journal, and restore the verified content backup to a real local
destination. Preserve both versions when their contents differ. Do not restore
a live link into a source path scheduled for deletion.

## Stage 2: Repository Cleanup

Record these attestations in the cleanup pull request, without attaching local
reports, paths, project names, or backup contents:

- [ ] Personal Mac: Stage 1 revision identified; setup and isolation checks
      passed with no unresolved conflicts; agent and Orca verification passed.
- [ ] Work Mac: Stage 1 revision identified; setup and isolation checks passed
      with no unresolved conflicts; agent and Orca verification passed.

A receipt from one Mac cannot establish the other Mac's state. A receipt from a
dirty development checkout is not a substitute for checking the published
Stage 1 revision.

The cleanup release removes the tracked synced skill cache, hook backup, and
Python bytecode, along with the exact-byte Stage 1 exceptions. Artifact ignore
and rejection rules remain. Shared sources move from `dotfiles/link/` to
`dotfiles/shared/`; seeds move from `dotfiles/copy/` to `dotfiles/seed/`. The
installation ledger continues to identify ownership by destination.

Publish cleanup only after both attestations, repository checks, and the
two-clone migration fixture pass. Preserve any remaining local source copies
before removing artifacts from a checkout.

Preserve Git history. Do not restore the removed runtime files from history
into a new Mac's app configuration.

## Update After Stage 1

After Stage 1 and runtime verification have passed on both Macs, return to the
normal branch and apply the cleanup release separately on each Mac:

```sh
git switch master
git pull --ff-only
make plan/dotfiles
make set-up/dotfiles
make check/dotfiles
make check/agents
make check/codex-routing
```

Setup writes a current `stage-two.json` receipt without replacing the historical
`stage-one.json`. Keep both receipts, the installation ledger, and all migration
backups local. Local app projects, hooks, downloaded skills, and credentials
remain outside Git. The source rename does not change hook definitions or trust;
repeat the README's runtime smoke test after runtime or routing changes.

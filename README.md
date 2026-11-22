# Knapsack

Kyle Hughes's dotfiles and development environment configuration for macOS.

## Installation

```sh
# Clone repository
cd ~ && git clone git@github.com:kylehughes/knapsack.git Knapsack
cd ~/Knapsack

# Run all setup tasks
make set-up/all
```

Or run individual setup tasks:

```sh
make set-up/homebrew        # Install Homebrew
make set-up/dependencies    # Install dependencies from Brewfile
make set-up/dotfiles        # Install or update local dotfile copies
make set-up/orca            # Patch Orca's live settings from the tracked base and overlay
make set-up/idb             # Install Facebook idb companion and client
make set-up/mcp-servers     # Register shared MCP servers with Claude Code and Codex
make set-up/agent-skills    # Install Knapsack's standalone Codex writing skill
make set-up/local-functions # Create local functions directory
make set-up/repository-hook # Install the staged-source guard and apply-on-pull hooks
make set-up/performance     # Tune macOS for heavy parallel development (opt-in)
```

## Updating Configuration

Pulling applies itself. `make set-up/repository-hook`, which `make set-up/all`
runs, installs Git hooks that run setup after every pull, so another Mac needs
only:

```sh
git pull
```

Setup installs independent local copies, so an edit made in this checkout
changes nothing until setup runs. After editing, apply it by hand:

```sh
make plan/dotfiles
make set-up/dotfiles
make check/dotfiles
```

Restart the relevant app or shell after applying changes.

Setup records the contents and executable bits it last installed. It updates
unchanged managed files, preserves unrelated files, and reports conflicts instead
of replacing local edits. Review each conflict: shared changes belong in the
repository; machine-specific settings belong in a supported local override.
Back up an unwanted local edit before removing that destination and rerunning
setup. There is no automatic import of local settings into Git.

**Installations that still use symlinks need Stage 1 before this release.**
Follow the [migration guide](docs/dotfile-migration.md) at its pinned Stage 1
revision before pulling the cleanup release. Already-migrated machines can use
the update commands above.

## Configuration Ownership

| Owner | Behavior | Examples |
| --- | --- | --- |
| Shared source | Git-tracked files are copied individually; installed directories stay local. | Agent instructions and profiles, shell functions, terminal themes, Vim plugins. |
| Local seed | Create only when absent; never update or retire automatically. | `~/.gitconfig_local`. |
| Composed settings | Combine the shared base with the local overlay; keep app edits in the overlay. | Claude settings and plugin declarations. |
| Live preferences | Patch selected preferences from the base and overlay after the app quits. | Orca settings. |
| Owned hook entry | Reconcile only Knapsack's routing handler, preserving all other local entries. | Codex hooks alongside Orca's integration. |
| Runtime or machine state | Remains outside the checkout and outside installation ownership. | Orca projects, credentials, trust, downloaded skills, caches, and local functions. |

`dotfiles/shared/` contains shared copy sources, `dotfiles/seed/` contains local
seeds, and `dotfiles/merge/` contains composition inputs. Source aliases let
Codex and Antigravity reuse the Claude instructions; their installed files are
independent copies. Ownership is recorded by installed destination, so renaming
a source directory does not re-adopt or retire installed files.

Claude settings use `dotfiles/merge/claude/settings.json` and the untracked
`~/.claude/settings.machine.json`. Objects merge recursively; arrays, including
permission lists and hook event arrays, replace the base array. A setting
changed through the Claude app, such as the model or a plugin, is that Mac's
own: setup writes the difference into the overlay and carries on. Shared
changes still reach every key that Mac has not changed. An array it has
changed, such as the permission list, stops following the base until the entry
is removed from the overlay.

The installation ledger, migration journal, and content backups live in
`~/.local/state/knapsack/`. Keep them on their originating Mac. They are not shared
configuration and must not be committed or copied to the other Mac.

### Orca Preferences

Orca preferences use `dotfiles/merge/orca/settings.json` and the untracked
`~/.orca/settings.machine.json`, created as `{}` if missing. Objects merge
recursively; arrays, such as `terminalQuickCommands`, replace the base array.
`make set-up/orca` patches only `.settings` in the active profile's live data
file, preserving repos, sessions, and worktree metadata. It skips while Orca is
running or before its first launch. Quit Orca before applying settings:

```sh
make set-up/orca
make check/orca
```

To keep preference changes made through Orca's UI, quit Orca, run
`make capture/orca`, and review the base diff before applying settings again.
Capture updates only keys already present in the tracked base; add new shared
preferences there deliberately. Keep machine-specific values in the overlay.
Unlike the dotfile installer, Orca setup reapplies the composed preferences
without reporting local edits as conflicts. It saves the previous live data
file as `orca-data.json.pre-knapsack` beside that file before writing a change.

## Shell Functions

Custom zsh functions for common workflows, autoloaded from `~/.config/zsh/functions/`:

#### Git Workflow Functions

| Function | Description | Usage |
| --- | --- | --- |
| `git-add-amend-force-push` | Stage all changes, amend commit, and force push. | `git-add-amend-force-push` |
| `git-add-commit` | Stage all changes and commit with message. | `git-add-commit "message"` |
| `git-fetch-pull` | Fetch remote changes and pull with rebase. | `git-fetch-pull` |
| `git-log-dag` | Show detailed commit graph with author info. | `git-log-dag [options]` |
| `git-log-graph` | Show commit history as decorated graph. | `git-log-graph [options]` |
| `git-log-pretty` | Show formatted log with details on one line. | `git-log-pretty [options]` |
| `git-push-upstream` | Push current branch and set upstream tracking. | `git-push-upstream` |
| `git-status-diff` | Show status and diff for review. | `git-status-diff` |

#### Graphite Worktree Functions

| Function | Description | Usage |
| --- | --- | --- |
| `gt-worktree-create` | Create a git worktree with full project setup, registered with Graphite. | `gt-worktree-create <branch-name>` |
| `gt-worktree-remove` | Remove a worktree after its PR merges and run `gt sync`. | `gt-worktree-remove [<path>] [options]` |

#### Maintenance and Media Functions

| Function | Description | Usage |
| --- | --- | --- |
| `brew-maintain` | Update, upgrade, autoremove, and clean up Homebrew. | `brew-maintain` |
| `ffmpeg-reduce-size` | Re-encode a video to reduce its file size. | `ffmpeg-reduce-size <video-file>` |
| `xcode-reclaim-space` | Clear DerivedData, prune stale simulators, and delete local Time Machine snapshots. | `xcode-reclaim-space` |

#### Apple Development Functions

| Function | Description | Usage |
| --- | --- | --- |
| `tailscale-serve-ipa` | Serve a signed iOS build for installation from Safari over Tailscale. | `tailscale-serve-ipa <app.ipa \| app.xcarchive>` or `tailscale-serve-ipa --scheme <scheme> [--workspace <path> \| --project <path>]` |

Connect the Mac and iPhone to Tailscale and enable
[HTTPS certificates](https://tailscale.com/docs/how-to/set-up-https-certificates)
for the tailnet. Run the command, open the printed URL in Safari on the iPhone,
and tap **Install**. Keep the command running until installation finishes;
Ctrl-C stops serving and removes temporary files. The URL stays the same for
that Mac and port, including when the iPhone uses cellular.

The IPA must already be signed for the iPhone. Archive and scheme inputs use
Xcode's development export method (`debugging`) and require Xcode 15.3 or later.
With `--scheme`, use `--configuration Release` to change the build configuration.
Use `--port 9443` to choose another HTTPS port (default: 8443). An occupied port fails
without replacing the existing service. The command requires Python 3.9 or later;
the zsh function and its Python companion are installed together by dotfile setup.

#### Claude Code Functions

| Function | Description | Usage |
| --- | --- | --- |
| `claude-fable` | Launch a single Claude Code session on Fable 5.2 without changing the default model. | `claude-fable [claude arguments]` |

Functions follow the `tool-action` naming convention for clarity and tab completion support.

#### Local Functions

Machine-specific functions can be placed in `~/.config/zsh/functions-local/` (not tracked in git):

```sh
# Create local functions directory
make set-up/local-functions

# Add a local function
echo '#!/usr/bin/env zsh
# my-local-function - Description here.
echo "This function only exists on this machine"' > ~/.config/zsh/functions-local/my-local-function
chmod +x ~/.config/zsh/functions-local/my-local-function
```

Local functions are autoloaded just like tracked functions but remain private to each machine.

## Dependencies

Managed via `Brewfile`:

```sh
brew bundle install    # Install all dependencies
brew bundle check      # Check for missing packages
brew bundle cleanup    # Remove unlisted packages
```

`make set-up/idb` finishes the idb setup after Homebrew dependencies are
installed. The idb companion is managed by Homebrew, and the Python client is
managed as a `uv` tool so the `idb` executable is available from `~/.local/bin`.

## Machine Configuration

Knapsack contains configuration shared across machines. Host-specific services,
dependencies, and recovery instructions belong in separate private repositories.
The Mac mini's scan OCR service is managed there and is not installed by
`make set-up/all`.

## AI Agents

The instructions in `dotfiles/shared/claude/CLAUDE.md` are the source of truth
for all three CLI agents on this machine. Codex CLI (`~/.codex/AGENTS.md`) and
Antigravity CLI (`~/.gemini/GEMINI.md`) receive copies of the same instructions, so
`CLAUDE.md` is maintained once. Delegated work runs as Orca workers, using
Orca's `orchestration` skill, and quick read-only lookups use each runtime's
native subagents. Codex's execution profiles choose model and effort while
project instructions supply each worker's task or auditor's mandate. Claude Code's full
settings, including plugin declarations and marketplaces, are generated from
the tracked base and machine overlay. Setup keeps changes made through the
Claude app in that Mac's overlay.
Codex manages plugins locally through its app or CLI.

Run Gemini through Antigravity CLI with `agy`, or use
`agy -p "prompt" --model gemini-4-neon-high` for a headless turn. Check
`agy models` for the current account's model IDs and `agy -p /usage` for quota.
Model access can differ between Macs. Antigravity retains the
[`~/.gemini/GEMINI.md` instruction location](https://antigravity.google/docs/cli/gcli-migration/#context-files-and-workspace-rules);
its settings, account state, and workspace trust remain local.

`make set-up/agent-skills` installs the standalone Codex
`writing-prose-like-a-human` skill from the `repo|skill` declaration in
`scripts/set-up-agent-skills.sh`; its corresponding Claude Code plugin is
declared in the settings base.

Delegation guidance lives in the shared instructions. Orca coordinates the
work: implementation, reviews, long or parallel tasks, and anything for another
model family go to an Orca worker started with the agent, model, and effort its
class gets, while lookups and log digests stay on native subagents. The aim is
the best output for the least usage: the parent keeps orchestration and
judgment, and
each delegated task goes to the cheapest route whose mistakes would be caught.
A task is classified by what it needs, not by how much it matters, and both
runtimes carry a route of the same name for each class:

| Class | The work | Claude Code | Codex CLI |
| --- | --- | --- | --- |
| Mechanical | Exact instructions, nothing to interpret | `mechanical-worker` — `claude-sonnet-5-5`, `medium` | `mechanical_worker` — `gpt-6-luna`, `high` |
| Scout | Find and report facts, changing nothing | `scout-worker` — `claude-sonnet-5-5`, `high` | `scout_worker` — `gpt-6-luna`, `high` |
| Ordinary | Build to a clear contract that a check verifies | `ordinary-worker` — `claude-opus-5-5`, `medium` | `ordinary_worker` — `gpt-6.2-sol`, `medium` |
| Thorough | Bounded work a check would not fully cover | `thorough-worker` — `claude-opus-5-5`, `high` | `thorough_worker` — `gpt-6.2-sol`, `high` |
| Difficult | Judgment with nothing to catch a wrong answer | `difficult-worker` — `claude-opus-5-5`, `high` | `difficult_worker` — `gpt-6.2-astra`, `medium` |

Fable 5.2 and GPT-6.2 Astra are the preferred orchestrators. Fable is a worker
only on an explicit request or after the difficult route has failed a task for
a demonstrated capability reason. Astra is the difficult route on Codex, where
no model sits between Sol and the frontier, and runs above medium effort only
under the same rule. Antigravity has no pinned routes, because its subagents
choose a model tier and cannot set effort; the instructions name a Gemini model
for each class instead.

In Claude Code, the `*-worker` agents in `claude/agents/` pin model and
effort. Any other agent runs on the session's model unless its definition pins
one, so the instructions ask for an explicit `model` and `effort` on each such
call. Opus takes every class in which the worker makes a decision and Sonnet
takes the two in which it makes none, so Haiku holds no route. Per-call effort
requires [Claude Code 2.1.292 or later](https://code.claude.com/docs/en/model-config).
`claude-fable` selects Fable 5.2 by its exact ID, `claude-fable-5-2`, and requires
Claude Code 2.1.321 or later. The session flag leaves the configured default intact.
Report unavailable model support rather than silently choosing an older version.

[`docs/agent-routing.md`](docs/agent-routing.md) records the evidence behind
each pin, the role of every model the three CLIs offer, and the steps for
re-evaluating the roster when a model ships. See the
[Claude Code subagents documentation](https://code.claude.com/docs/en/sub-agents)
and [Codex subagents documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents)
for runtime-specific behavior.

Shared MCP servers are registered separately by `make set-up/mcp-servers`.
Because each agent keeps its MCP configuration in a large, stateful,
secret-bearing local file (`~/.claude.json`, `~/.codex/config.toml`), the setup
script registers servers through each tool's own CLI
instead, and re-running it leaves existing servers untouched. The declared list
lives in `scripts/lib/agent-mcp-servers.sh`; today it registers
[sosumi.ai](https://sosumi.ai/), which renders Apple's JavaScript-only developer
documentation into Markdown.

### Agent Verification

`make check/agents` is read-only. It verifies Knapsack-owned instructions and
agent copies, valid JSON and the expected complete generated Claude settings
(including declared plugins), launcher syntax, and the registered MCP server's
expected URL and transport. It skips optional agent CLIs that are not installed.
It does not require a Codex plugin inventory or perform network health checks.

`make test/agents` runs the fixture-based tests for configuration and routing.

`make check/orca` is read-only. It verifies the tracked Orca settings base
against the public-repository denylist and that the active profile's live
`.settings` contains the composed base and overlay, reported by key name only.
It skips cleanly if Orca has never launched. `make test/orca` runs its
fixture-based tests, kept separate from `make test/agents` because they never
touch the real Orca data.

### Codex Routing

The runtime smoke test below is the release gate. Passing unit tests and an
enabled, trusted hook are insufficient evidence that a spawn is intercepted.

Codex profiles make the model and effort choice explicit at each spawn. No
route inherits the parent, so the session's own model and effort reach a
subagent only through a route that names them. The five class routes are
listed under [AI Agents](#ai-agents). A sixth, `custom_worker`, pins
nothing and takes an explicit `model` and `reasoning_effort`: a user-named
model, a retry that changes one lever, or a task outside the pinned classes.

Mechanical and scout share a model and effort but carry different contracts:
one changes exactly what it is told to, and the other changes nothing. The
difficult route runs GPT-6.2 Astra, which OpenAI's
[current model guidance](https://learn.chatgpt.com/docs/whats-new/gpt-62-astra-sol)
positions for complex reasoning.

The `PreToolUse` hook validates the declared route and rejects model or effort
values that conflict with a pinned route. It reads each pin from the role files
installed beside it in `~/.codex/agents`, so it names no model itself. Every
call must start with fresh context, `fork_turns=none`: Codex 0.169 runs any
other value, including a legacy turn count, as a full-history fork. The hook
does not classify prompts, call a model, log task contents, rewrite arguments,
or grant tool permission. Project auditor instructions remain in their
repositories and are passed in the task contract.

The matcher covers canonical `spawn_agent` / `Agent` and the default V2 hook
identity, `collaborationspawn_agent`. Codex 0.154.0 flattens the namespace and
tool name without a separator; matching only `spawn_agent` misses that path.
See the [runtime normalization](https://github.com/openai/codex/blob/rust-v0.154.0/codex-rs/core/src/tools/registry.rs#L799-L808)
and [reported matcher bug](https://github.com/openai/codex/issues/36519).
Custom V2 tool namespaces are unsupported and the checker reports them;
the hook deliberately avoids matching arbitrary tools by suffix.

Installation and activation are separate:

1. `make set-up/dotfiles` copies the profiles and routing script under
   `~/.codex`, then reconciles the routing handler from
   `dotfiles/merge/codex/hooks.json` into the local hook file. Orca and other
   unrelated handlers remain local. Setup does not change `config.toml` or hook trust.
2. `make set-up/codex-routing` registers every `*-worker` profile in the source
   `~/.codex/config.toml` through Codex's configuration API. Explicit file
   references also support apps that mirror this configuration without copying
   the `agents` directory. The command updates only Knapsack's own roles and
   clears the `knapsack_*` names they had before 2026-11-17;
   it does not enable or trust hooks.
   This step is included in `make set-up/all` and skips machines without Codex.
   File references are generated from that machine's home directory.
3. Check the runtime you actually use with `make check/codex-routing`. An app
   may use a different `CODEX_HOME`; shared instructions appearing in a session
   do not prove that its profiles and hooks were imported. Start a fresh session
   after registration so an app can refresh its mirrored configuration. If the
   references still do not reach the runtime, report that integration as unsupported;
   do not patch its generated home.
4. From a terminal using the shared `~/.codex` configuration, launch
   `codex --enable hooks`. In `/hooks`, select **PreToolUse** and review the hook
   running `python3 "$HOME/.codex/hooks/validate-agent-route.py"`; press **t** to
   trust that hook. New or changed definitions are skipped until trusted.
   Review existing trusted hooks too, since enabling hooks activates them.
   After review, `codex features enable hooks` persists the feature setting;
   `--enable hooks` alone applies only to that launch. Do not use a trust-bypass flag.
5. Start a fresh session and verify actual tool events: an unrouted spawn must
   be denied before a child starts, and each routed child must record the model
   and effort its profile pins.
   A child's assertion about its model is insufficient evidence. Repeat after
   runtime or routing changes.

For Orca, launch a fresh Codex session through the app and repeat the acceptance
checks in that runtime. Orca manages its own copied configuration; do not patch
its generated home. The CLI's `agent hooks prepare-codex` command is documented
for WSL panes and is not part of this macOS setup.

The previous live checks passed on 2026-09-18 with Codex CLI 0.154.0 from a fresh
`codex exec` session: the unrouted V2 spawn was denied before a child started,
and recorded child turns confirmed Luna/high, Terra/medium, Sol/medium, and an
explicit Astra/medium override. The same day a headless Claude Code session
recorded `knapsack-ordinary` on Sonnet at medium and `knapsack-mechanical` on
Haiku with no effort field; Haiku 4.5 did not support effort. Orca
and other wrappers still need the same acceptance checks after this change.

On 2026-09-22, a fresh Codex CLI 0.155.1 session rejected the unrouted spawn;
child turn records confirmed GPT-6 Luna/high for mechanical work and GPT-6
Sol/medium for both ordinary and difficult work. A Claude Code 2.1.280 child
transcript confirmed `knapsack-difficult` ran on `claude-opus-5-5`.

On 2026-10-19, a fresh Codex CLI 0.163.0 session rejected the unrouted spawn;
child turn records confirmed GPT-6 Luna/high for mechanical work and GPT-6.1
Sol/medium for both ordinary and difficult work.

On 2026-11-17, fresh Codex CLI 0.169.0 and Orca-launched sessions rejected the
unrouted spawn. Child turn records in both runtimes confirmed GPT-6 Luna/high,
GPT-6.2 Sol/medium for ordinary and difficult work, and an explicit GPT-6.2
Astra/medium override. The installed `claude-fable` launcher completed a turn on
`claude-fable-5-2` with Claude Code 2.1.326.

Later on 2026-11-17 the routes were renamed from `knapsack-*` to `*-worker`,
scout and thorough routes were added, and the difficult routes moved to Opus
5.5 at high and GPT-6.2 Astra at medium. A fresh Codex CLI 0.169.0 `codex exec`
session then rejected an unrouted spawn, a spawn with a legacy turn count, and
a pinned route given another model. Child turn records confirmed GPT-6 Luna/high
for mechanical and scout, GPT-6.2 Sol/medium for ordinary, GPT-6.2 Sol/high for
thorough, GPT-6.2 Astra/medium for difficult, and an explicit GPT-6.1
Terra/medium through `custom_worker`. A headless Claude Code 2.1.326 session
spawned all five workers without a per-call model or effort; their transcripts
recorded Haiku 5.5/high twice, Sonnet 5.5/medium, Sonnet 5.5/high, and Opus
5.5/high. An Orca-launched Codex session then repeated the Codex checks with the
same rejections and the same recorded models and efforts.

On 2026-11-19 the Claude Code ordinary and thorough routes moved from Sonnet
5.5 to Opus 5.5, and the mechanical and scout routes from Haiku 5.5 to Sonnet
5.5. A headless Claude Code 2.1.326 session spawned all five workers without a
per-call model or effort; their transcripts recorded Sonnet 5.5/medium for
mechanical, Sonnet 5.5/high for scout, Opus 5.5/medium for ordinary, and Opus
5.5/high for thorough and difficult.

On 2026-11-22 delegation moved to Orca workers. From an Orca 1.4.266 Claude Code
session, three parallel `orca orchestration worker-start` calls with the
difficult pairings reported `worker_done`. The Claude transcript recorded Opus
5.5/high, the Codex turn record GPT-6.2 Astra/medium, and the Antigravity
process ran with `--model gemini-4-argon-high`.

On 2026-11-22 Gemini 4 Neon replaced Hydrogen and Argon as the Gemini model for
ordinary, thorough, and difficult work. Antigravity CLI 1.5.14 listed it and
completed a headless turn on `gemini-4-neon-medium`, `-high`, and `-xhigh`.

The status command is read-only and makes no model calls. It checks installation,
effective configuration, and hook trust; passing it establishes eligibility,
not proof that a particular spawn path invokes the hook. Disabled, untrusted,
missing, and unsupported configurations are **unenforced**. Codex documents that
some tool paths bypass hooks, so this is a workflow guard, not a security boundary.
See [Codex hooks](https://learn.chatgpt.com/docs/hooks).

## Development

`make check/repository` checks source policy and runs isolated fixture tests.
`make test/dotfiles` runs migration, composition, and repository-guard tests;
`make test/agents` runs the agent configuration tests; `make test/shell-functions`
checks the IPA helper with disposable IPAs and mocked Tailscale and Xcode commands;
`make test/orca` runs the Orca settings tests. None needs your accounts or launches
an agent. Runtime checks remain separate: `make check/dotfiles`, `make check/agents`,
`make check/codex-routing`, and `make check/orca` inspect this Mac.

`make set-up/repository-hook` installs a pre-commit check for the staged snapshot
and the two hooks that run setup after a pull, `post-merge` and `post-rewrite`.
A setup failure there is reported and never fails the pull. It preserves custom
hooks and reports how to chain each command if one already exists. CI runs the full repository checks. Changes to `master` go through a
pull request with the `Repository checks` job passing against the current base;
no external approving reviewer is required. Administrator bypass, force pushes,
and branch deletion are disabled when the protection is installed.

Repository checks reject runtime artifacts, including synced skill caches,
hook backups, and Python bytecode. The Stage 1 exceptions have been removed.
New shared dotfiles must be explicitly added to Git before setup will install
them. Unsupported source symlinks are rejected.

### Documentation Standards

All scripts and configuration files follow consistent documentation patterns:

- **File headers**: Simple one-line descriptions with usage information for scripts.
- **Section headers**: Title Case sections marked with `--- Section Name ---`.
- **Comments**: Complete sentences with periods, explaining why not what.
- **No decorations**: Clean, readable formatting without excessive separators.

## Performance

`make set-up/performance` applies idempotent, reversible tunings for machines
that run many concurrent simulators and builds: it caps Xcode's compile tasks
per build so parallel builds do not oversubscribe the CPU, disables App Nap and
UI animations, excludes `DerivedData` and `CoreSimulator` from Time Machine, and
turns off Power Nap. It is an opt-in task (it requires `sudo` and changes
interface preferences), so it is not part of `make set-up/all`.

On Apple Silicon there is no software toggle that trades longevity for speed —
the machine already runs at full clocks on AC power. The one lever for sustained
performance under load is thermal headroom, so keep the laptop on a stand or in
clamshell mode with an external display.

Reclaiming disk is a separate, periodic task: run `xcode-reclaim-space` when no
builds are in progress to clear build intermediates, prune stale simulators, and
delete local snapshots.

## Theme

A Gengar-inspired purple theme consistent across all terminal applications:

| Color | Hex | Usage |
| --- | --- | --- |
| Background | `#1c1c1c` | Terminal background. |
| Foreground | `#eeeeee` | Primary text. |
| Purple | `#af5fff` | Status bars, borders. |
| Bright Purple | `#d7afff` | Active elements. |
| Grey | `#444444` | Inactive elements. |

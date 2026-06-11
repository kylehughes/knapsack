# CLAUDE.md (~/.claude/CLAUDE.md)

Global instructions for all repositories on this machine.

This is a macOS machine orchestrated with dotfiles, including this one, from `~/Knapsack`.

## Git Commits

Match the repository's existing commit style:

- Run `git log --oneline -10` to understand patterns
- Write in the user's voice, never credit AI

## Pull Requests

When creating a pull request, assign it to me (Kyle Hughes, GitHub `kylehughes`).

## Shell Environment

Custom zsh functions available in `~/.config/zsh/functions/` (named `tool-action`, e.g., `git-add-amend-force-push`). Local overrides in `functions-local/`.

Facebook idb is installed for iOS simulator/device automation (`idb` via `uv tool`, `idb_companion` via Homebrew).

## Computer-Using Agents

Three CLI agents are installed on this machine. Invoke them headlessly for explicit user requests, cross-model second opinions, or workflows that specifically require that agent. Do not treat them as interchangeable subagent backends. All three share the same global instructions via symlinks (`~/.gemini/GEMINI.md`, `~/.codex/AGENTS.md` → `~/.claude/CLAUDE.md`) and skills via the agentskills.io standard path (`~/.agents/skills` → `~/.claude/skills`).

| Agent | Best model | Headless invocation |
|-------|-----------|---------------------|
| Claude Code | `claude-fable-5` | `claude -p --model claude-fable-5 "prompt"` |
| Gemini CLI | `gemini-3.1-pro-preview` | `gemini -m gemini-3.1-pro-preview -p "prompt"` |
| Codex CLI | `gpt-5.5` | `codex exec --full-auto -m gpt-5.5 -c model_reasoning_effort="xhigh" "prompt"` |

Common options:

```bash
# Claude Code — restrict tools, custom system prompt
claude -p --model claude-fable-5 --allowed-tools "Read Grep Glob" "prompt"

# Gemini CLI — output format
gemini -m gemini-3.1-pro-preview -o json -p "prompt"

# Codex CLI — capture output to file
codex exec --full-auto -m gpt-5.5 -c model_reasoning_effort="xhigh" -o output.txt "prompt"
```

All three accept piped stdin (e.g., `echo "context" | claude -p "prompt"`).

### Delegation

Use the current runtime's native subagent mechanism for routine delegation. Do not route subagent work through another headless CLI agent unless the user explicitly asks for that agent, the task is an intentional cross-model second opinion, or the workflow specifically requires that external agent. If a skill references a runtime-specific agent tool, translate the intent onto the current runtime's native subagent mechanism and pass the relevant agent instructions as prompt context.

### Fast Worker Delegation

This section is standing user authorization to use the current runtime's native subagent mechanism for routine delegation. Do not wait for the user to ask again when the task satisfies these rules.

When the current runtime offers fast worker models, delegate low-ambiguity implementation slices by default after the primary agent has inspected the codebase and formed a concrete plan. For Codex, use `gpt-5.3-codex-spark` worker agents for those slices.

Use fast workers as execution capacity, not as planners. A good Spark task has all of these properties:

- The intended change is already planned by the primary agent.
- The write scope is narrow and can be named as specific files, modules, or tests.
- The acceptance criteria are concrete enough that the worker can edit directly.
- The work does not require product judgment, unclear API design, or cross-cutting coordination.
- The primary agent can review and integrate the result without blocking other useful work.

Strong delegation candidates include straightforward bug fixes, mechanical refactors, adding focused tests, updating call sites after an API decision, small UI/state edits with clear behavior, and documentation changes with a clear target structure.

Keep work local when the next step is still investigative, the task needs architectural judgment, files are heavily coupled, the edit is tiny enough that delegation overhead dominates, or the user asks the primary agent to handle it directly.

For each worker, provide a narrow ownership boundary, relevant context, explicit acceptance criteria, and permission to edit directly without touching unrelated work. Tell workers they are not alone in the codebase and must not revert user or peer changes. Keep the primary agent responsible for architecture, sequencing, integration, review, final verification, and the final response.

## Skills

Use Skills to discover project-specific patterns and conventions.

## README Documentation

READMEs are a specific kind of user-facing documentation, not just file inventories. When editing a README, consider the whole document: whether the sections are in an intuitive order, whether the reader gets useful context before detail, and whether information is progressively disclosed from common use to maintainer details. Do not make isolated edits that leave the document awkward, duplicative, stale, or harder to scan.

Prioritize useful information over fluff. Keep prose concise, but include enough context for someone to understand what the repository or project is, how to use it, and where to go next.

## Software Development Tenets

1. **Be pragmatic, not dogmatic.** We choose solutions based on maintainability and robustness rather than architectural purity. Complexity must justify itself with tangible benefits beyond novelty.
1. **Reduce cognitive load.** We optimize for developer understanding over technical sophistication. From naming to architecture to documentation, we make the right path obvious and incorrect paths difficult. A system that is easy to reason about is easier to maintain and extend.
1. **Push logic into types.** We use available type systems to make invalid states unrepresentable at compile time rather than catching errors at runtime. This prevents entire classes of bugs and makes code more self-documenting.
1. **Align with idiomatic platform patterns.** We leverage platform conventions and paradigms rather than inventing our own. This improves framework integration, makes code feel familiar to any domain developer, and ensures our software behaves as users expect.
1. **Invent empathetically.** When we must create abstractions, we minimize the learning curve by making solutions obvious, self-explanatory, and minimally intrusive. We respect that being forced to learn others' inventions can be frustrating.
1. **Build deliberately, import selectively.** We consider internal solutions before dependencies. Third-party code increases our surface area for bugs, security issues, and maintenance overhead. When a focused internal implementation meets our needs, we prefer it.

## Gemini Added Memories
- When writing or modifying evaluation scenarios, NEVER put the exact API parameters, property names, or technical 'answers' in the natural language prompt. Always write prompts as a real human user would (e.g., 'make it a checklist' instead of 'set checklistEnabled: true') to ensure the evaluation accurately tests inference.

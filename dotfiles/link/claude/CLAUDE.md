# CLAUDE.md (~/.claude/CLAUDE.md)

Global instructions for all repositories on this machine.

This is a macOS machine orchestrated with dotfiles, including this one, from `~/Knapsack`.

## Git Commits

Match the repository's existing commit style:

- Run `git log --oneline -10` to understand patterns
- Write in the user's voice, never credit AI

## Shell Environment

Custom zsh functions available in `~/.config/zsh/functions/` (named `tool-action`, e.g., `git-add-amend-force-push`). Local overrides in `functions-local/`.

## Computer-Using Agents

Three CLI agents are installed on this machine. Each can be invoked headlessly for second opinions or delegation.

| Agent | Best model | Headless invocation |
|-------|-----------|---------------------|
| Claude Code | `claude-opus-4-6` | `claude -p --model opus "prompt"` |
| Gemini CLI | `gemini-3.1-pro-preview` | `gemini -m gemini-3.1-pro-preview -p "prompt"` |
| Codex CLI | `gpt-5.3-codex` | `codex exec --full-auto -m gpt-5.3-codex -c model_reasoning_effort="xhigh" "prompt"` |

Common options:

```bash
# Claude Code — restrict tools, custom system prompt
claude -p --model opus --allowed-tools "Read Grep Glob" "prompt"

# Gemini CLI — output format
gemini -m gemini-3.1-pro-preview -o json -p "prompt"

# Codex CLI — capture output to file
codex exec --full-auto -m gpt-5.3-codex -c model_reasoning_effort="xhigh" -o output.txt "prompt"
```

All three accept piped stdin (e.g., `echo "context" | claude -p "prompt"`).

## Skills

Use Skills to discover project-specific patterns and conventions.

## Software Development Tenets

1. **Be pragmatic, not dogmatic.** We choose solutions based on maintainability and robustness rather than architectural purity. Complexity must justify itself with tangible benefits beyond novelty.
1. **Reduce cognitive load.** We optimize for developer understanding over technical sophistication. From naming to architecture to documentation, we make the right path obvious and incorrect paths difficult. A system that is easy to reason about is easier to maintain and extend.
1. **Push logic into types.** We use available type systems to make invalid states unrepresentable at compile time rather than catching errors at runtime. This prevents entire classes of bugs and makes code more self-documenting.
1. **Align with idiomatic platform patterns.** We leverage platform conventions and paradigms rather than inventing our own. This improves framework integration, makes code feel familiar to any domain developer, and ensures our software behaves as users expect.
1. **Invent empathetically.** When we must create abstractions, we minimize the learning curve by making solutions obvious, self-explanatory, and minimally intrusive. We respect that being forced to learn others' inventions can be frustrating.
1. **Build deliberately, import selectively.** We consider internal solutions before dependencies. Third-party code increases our surface area for bugs, security issues, and maintenance overhead. When a focused internal implementation meets our needs, we prefer it.

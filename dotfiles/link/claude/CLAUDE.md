# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code across all repositories.

## Git Commit Guidelines

When creating git commits:
1. Analyze the repository's git history first to understand the commit style
2. Write commits in the user's voice and style
3. Match the typical commit message density and format used in the repository
4. Never credit yourself, Claude, or AI assistance in commit messages
5. Make commits appear as if written directly by the user

To analyze commit style, run:
```bash
git log --oneline -20  # Recent commit style and density
git log -5             # Detailed recent commits
```

Focus on:
- Message length and detail level
- Capitalization patterns
- Use of imperative mood vs past tense
- Common phrases or conventions
- Punctuation usage
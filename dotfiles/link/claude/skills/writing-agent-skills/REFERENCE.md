# Agent Skills Authoring Reference

## Core Principles

### Conciseness
The context window is a shared resource. Metadata is always loaded, but `SKILL.md` content is loaded only when triggered. Even then, keep it efficient.
- **Assume Competence**: Claude knows general concepts (e.g., what a PDF is). Focus on specific library usage or project conventions.
- **Token Budget**: Aim for < 500 lines for the main `SKILL.md`.

### Degrees of Freedom
Tailor the strictness of instructions to the task:
1.  **High Freedom**: For creative/variable tasks (e.g., "Analyze code structure").
2.  **Medium Freedom**: Pseudocode or flexible templates (e.g., "Generate report with these sections").
3.  **Low Freedom**: Exact scripts or commands for fragile operations (e.g., "Run `migrate.py --verify` exactly").

## Organization Patterns

### Progressive Disclosure
Organize content to minimize token usage until necessary.

1.  **Simple**: Just `SKILL.md`.
2.  **Bundled**: `SKILL.md` + `REFERENCE.md` + `scripts/`.
3.  **Domain-Split**:
    ```
    bigquery-skill/
    ├── SKILL.md
    └── reference/
        ├── finance.md
        ├── sales.md
        └── product.md
    ```
    Claude reads `SKILL.md`, then only reads `reference/sales.md` if the user asks about sales.

### Reference Depth
*   **Rule**: Keep references **one level deep** from `SKILL.md`.
*   *Avoid*: `SKILL.md` -> `advanced.md` -> `details.md`.
*   *Prefer*: `SKILL.md` links to both `advanced.md` and `details.md`.

## Common Patterns

### Workflows
For complex tasks, provide a checklist for Claude to track progress.

**Example (PDF Form Filling)**:
```markdown
## Workflow
Copy this checklist:
- [ ] Step 1: Analyze form (`python scripts/analyze.py`)
- [ ] Step 2: Map fields (`fields.json`)
- [ ] Step 3: Validate (`python scripts/validate.py`)
- [ ] Step 4: Fill form
```

### Templates
Provide strict or flexible templates for output.
- **Strict**: "ALWAYS use this JSON format..."
- **Flexible**: "Here is a sensible default structure..."

### Feedback Loops
Encourage self-correction.
- "Run the validator script. If it fails, fix the issues and run it again. Only proceed when validation passes."

### Source Links
Include links to source material (blogs, docs) in `REFERENCE.md`, not `SKILL.md`.
- **Purpose**: Easy regeneration and maintenance of the skill.
- **Location**: Bottom of `REFERENCE.md` (keeps `SKILL.md` token-efficient and focused on instructions).

## Executable Scripts
Skills can include code (Python/Bash) that Claude executes.
- **Utility Scripts**: deterministic, reliable, save tokens.
- **Error Handling**: Scripts should catch errors and print helpful messages, not crash or punt to Claude.
- **Paths**: Use forward slashes (`/`) exclusively.

## Anti-Patterns
- **Time-Sensitive Info**: Avoid "Use the new API after 2025". Instead, have a "Legacy Patterns" section.
- **Inconsistent Terminology**: Don't mix "URL", "endpoint", and "route". Pick one.
- **Deeply Nested References**: Causes partial reads and context loss.
- **Assumption of Installation**: Explicitly list `pip install` commands or dependencies if they aren't standard.


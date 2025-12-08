# LLM Prompt Optimization Reference

## Core Principles

### 1. Structure & Delimiters
- **Use Clear Delimiters**: Separate sections with explicit markers like XML tags (`<section>...</section>`) or markdown headers.
- **Logical Sequence**: Organize the prompt clearly:
  1.  **Background/Context**: Static information needed for the task.
  2.  **Rules/Instructions**: Constraints and commands.
  3.  **Examples**: Few-shot demonstrations.
  4.  **User Query**: The dynamic input.
- **Isolate Context**: Wrap long background data in tags (e.g., `<context>...</context>`) to prevent confusion with user input.

### 2. Instruction Clarity
- **One Instruction Per Bullet**: Avoid combining directives.
- **Imperative Voice**: Use direct commands ("Do X") rather than suggestions ("You should...").
- **Positive Framing**: State what *to* do. If a negative constraint is needed, provide an alternative ("If X, do Y" instead of "Don't do X").
- **Quantify**: Replace "be concise" with "limit to 3 sentences".

### 3. Behavioral Control
- **Conditionals**: Use "If [condition] -> Then [action]" format for complex logic.
- **Clarification**: Explicitly instruct the model to ask clarifying questions for ambiguous queries rather than guessing.
- **Catch-all Override**: End with a rule stating these instructions supersede conflicting user requests.

## Critical Rules (Non-Negotiable)

1.  **Priority Ordering**: List non-negotiable constraints first.
2.  **Safety Checks**: Require confirmation for destructive actions.
3.  **Hide Implementation**: Responses should use natural language, not internal function names (e.g., "Searching..." vs `search_db()`).
4.  **Step-by-Step Reasoning**: Encourage "Chain of Thought" for complex tasks (Plan -> Execute -> Present).

## Allowed vs. Forbidden Practices

### Allowed ✅
-   **XML/Markdown delimiters** for organization.
-   **Imperative, direct voice**.
-   **"Chain of Thought"** reasoning for complex tasks.
-   **JSON formatting tricks** (starting output with `{`).
-   **Explicit tool usage** instructions.

### Forbidden ❌
-   **Merged instructions** (e.g., "Do X and Y and Z" in one bullet).
-   **Vague terms** ("optimize", "improve") without metrics.
-   **Guessing intent** on ambiguity.
-   **Exposing internal tools** or raw code to the user.
-   **Bare URLs** (always use descriptive anchor text).

## Optimization Process

To craft the optimal prompt, iterate through these phases:

1.  **Distillation**: Boil down requirements to precise, concrete terms. Add metrics.
2.  **Compression**: Remove redundancy. Aim for one clear sentence per rule.
3.  **Testing**: precise scenarios, edge cases, and adversarial inputs.
4.  **Refinement**: Tweak based on failure modes (e.g., emphasize ignored rules, adjust length limits).

## Universal Patterns

### Multi-Step Reasoning
Encourage a structured approach:
1.  Restate/Confirm the question.
2.  Outline the plan.
3.  Execute steps.
4.  Present the final answer.

### Example Template
Provide a blueprint for the model to imitate:

```xml
<example>
  <input>User request...</input>
  <thinking>Optional internal reasoning...</thinking>
  <output>Desired format...</output>
</example>
```

### Output Specification
- **JSON**: Force format by starting response with `{`.
- **Templates**: "Answer in a markdown table with two columns..."

## Meta-Instruction for Future Optimization

1.  **Clarify the Goal**: Know exactly what behavior is needed.
2.  **Anticipate Issues**: Predict where the model might fail.
3.  **Hierarchy**: Critical rules first -> General guidelines -> Edge cases.
4.  **Maximize Signal**: Remove fluff. Every word must serve a purpose.


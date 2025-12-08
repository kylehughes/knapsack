# Claude Context Engineering & Extended Thinking Reference

## Context Engineering Fundamentals

Context engineering is the strategic curation and maintenance of tokens (information) passed to an LLM during inference. This practice is critical for **Anthropic Claude** models to optimize performance within the finite "attention budget".

### Key Concepts
- **Attention Budget**: LLMs have limited capacity to attend to relationships between tokens. As context grows, "context rot" can occur.
- **High-Signal Context**: The goal is to find the smallest set of high-signal tokens that maximize the likelihood of the desired outcome.
- **Context vs. Prompt Engineering**: Prompt engineering is discrete (writing a prompt); context engineering is iterative (managing state over time).

## The Anatomy of Effective Context for Claude

### System Prompts
- **Altitude**: Avoid hardcoding brittle logic or being too vague. Aim for the "Goldilocks zone"—specific enough to guide, flexible enough to allow Claude's heuristics to work.
- **Structure**: Organize into sections (`<instructions>`, `<tools>`, `<examples>`) using **XML tags** or Markdown. Claude is specifically trained to pay attention to XML structure.
- **Iterative Refinement**: Start minimal, then add instructions/examples based on failure modes.

### Tool Design
- **Token Efficiency**: Tools should return only necessary information.
- **Clarity**: Tools must be distinct, self-contained, and robust. Ambiguous toolsets confuse agents.
- **Minimal Viable Set**: Prune unused tools to reduce context pollution.

### Examples (Few-Shot)
- **Canonical Examples**: Use diverse, representative examples rather than exhaustive lists of edge cases.
- **"Pictures"**: Examples act as high-bandwidth signals for desired behavior.

## Dynamic Context Management

### Just-in-Time Retrieval
- **Lightweight Identifiers**: Store paths, IDs, or summaries instead of full content.
- **On-Demand Loading**: Agents use tools to retrieve full content only when needed (e.g., `read_file` after seeing `file_list`).
- **Benefits**: Reduces initial context load, prevents stale data.

### Progressive Disclosure
- **Layered Discovery**: Agents explore hierarchically (e.g., list dirs -> list files -> read file).
- **Signals**: Use metadata (filenames, timestamps) as proxies for relevance before loading content.

## Long-Horizon Strategies

For tasks spanning long durations (minutes to hours), use these techniques to manage context limits and "pollution".

### 1. Compaction (Summarization)
- **Definition**: Summarize conversation history when nearing limits, starting a new context window with the summary.
- **Technique**: Compress history while preserving architectural decisions, unresolved bugs, and key state.
- **Light Touch**: Clear tool outputs after they are used to save space without losing the "action" record.

### 2. Structured Note-Taking (Agentic Memory)
- **External Persistence**: Agents maintain notes in an external file (e.g., `NOTES.md`, `todo_list`).
- **Self-Managed**: Claude reads/writes to these notes to track progress, dependencies, and learnings across context resets.
- **Example**: Tracking game state or research findings across multiple sessions.

### 3. Sub-Agent Architectures
- **Separation of Concerns**: Main agent coordinates; sub-agents execute focused tasks with fresh context windows.
- **Distillation**: Sub-agents explore extensively but return only summarized findings to the main agent.
- **Parallelism**: Allows for complex, multi-track work without clogging the main context.

## Extended Thinking

Extended thinking allows Claude models (like Claude 3.7 Sonnet) to "think" and plan before generating a final response, improving performance on complex tasks.

### When to Use
- **Complex STEM**: Mathematical derivations, code generation with complex constraints.
- **Constraint Optimization**: Planning with multiple competing requirements (e.g., travel itineraries with budget/diet/time limits).
- **Thinking Frameworks**: Applying strategic models (Porter's Five Forces, etc.) sequentially.
- **Content Generation**: Detailed outlines, long-form writing.

### Prompting for Extended Thinking
- **General vs. Prescriptive**: Start with high-level instructions ("Think thoroughly...", "Consider multiple approaches") rather than rigid step-by-step mandates. Claude often finds better paths itself.
- **Multishot with Thinking**: Include `<thinking>` blocks in examples to demonstrate *how* to reason, not just the answer.
- **Instruction Following**: Extended thinking improves adherence to complex instructions.
- **Debugging**: Use the thinking output to diagnose logic errors (though don't feed it back into the prompt).

### Best Practices
- **Budgeting**: Start with a minimum (e.g., 1024 tokens) and scale up. Use batch processing for very large budgets (>32k).
- **Prefill Forbidden**: Do not prefill the assistant response when using extended thinking.
- **Output Control**: If you only want the answer, instruct Claude to output *only* the result after thinking.

## XML Tags for Structure

XML tags help Claude parse prompts accurately, separating context, instructions, and data.

### Benefits
- **Clarity**: Delineates components clearly.
- **Parseability**: Easier to extract specific sections programmatically.
- **Robustness**: Reduces "leaking" between sections (e.g., confusing an example with a real instruction).

### Guidelines
- **Consistency**: Use standard tag names (`<instructions>`, `<example>`, `<context>`) and stick to them.
- **Nesting**: Nest tags logically (e.g., `<examples><example>...</example></examples>`).
- **Referencing**: Refer to tags by name in the instructions ("Use the data in `<context>`...").

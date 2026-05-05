---
name: "handoff-to-expert"
description: "Create a comprehensive no-context escalation brief for a stronger model, senior engineer, or external expert when an agent is stuck on a programming problem. Use when the agent is looping, has tried multiple failed fixes, cannot identify the root cause, needs to hand off debugging context, or the user asks to distill the whole problem space for an expert with no prior project context."
---

# Handoff to Expert

## Overview

Produce a self-contained expert brief, not another speculative fix attempt. The brief must let a capable reader understand the goal, relevant code, failure evidence, prior attempts, constraints, and open hypotheses without access to the previous conversation.

## Operating Mode

When invoked, stop iterating on the implementation unless the user explicitly asks for continued coding. Reconstruct the problem space and prepare a handoff packet that maximizes the expert's chance of solving it.

Prefer concrete evidence over narrative memory. If repository access is available, inspect the relevant files, diffs, commands, test output, logs, and configuration before writing the brief. If evidence is unavailable, say exactly what is missing.

Redact secrets, tokens, private keys, and credentials. Preserve useful structure such as variable names, endpoint shapes, and error classes when redacting.

## Workflow

1. State the user's intended outcome in plain language.
2. Identify the exact current failure mode and how to reproduce it.
3. Gather the smallest complete set of relevant code, configuration, commands, logs, tests, screenshots, or traces.
4. Summarize the architecture and data flow only as far as needed to reason about the issue.
5. Inventory every meaningful attempted fix, including why it seemed plausible and what disproved or weakened it.
6. Separate facts from hypotheses. Label uncertainty directly.
7. Define what would prove the issue is fixed.
8. End with a direct ask to the expert.

## Output Format

Use this structure unless the user requests another format:

### Problem Statement

Explain the desired outcome and why the current behavior is wrong. Include expected vs. actual behavior.

### Project Context

Describe the relevant framework, runtime, architecture, data flow, package boundaries, and conventions. Assume the reader is an excellent engineer but has never seen this project.

### Current Failure

Provide exact symptoms and reproduction steps. Include commands, failing tests, error messages, stack traces, logs, UI behavior, or screenshots when available.

### Relevant Evidence

List the files, functions, types, routes, components, configuration, database tables, external APIs, and line references that matter. Include short code snippets only when they clarify the issue better than a file reference.

### Attempts So Far

For each meaningful attempt, include:

- What changed
- Why it seemed plausible
- What happened
- Why it did not solve the problem

### Constraints and Non-Goals

Capture user requirements, codebase conventions, compatibility constraints, dependency constraints, performance concerns, security considerations, and things that should not be changed.

### Facts vs. Hypotheses

Separate confirmed facts from suspected root causes. Rank hypotheses by plausibility and explain what evidence supports or contradicts each one.

### What Would Prove It Fixed

Name the exact tests, commands, manual checks, or acceptance criteria that would verify a correct solution.

### Expert Ask

End with a direct request for the expert, such as a diagnosis, patch strategy, minimal fix, architectural correction, or test plan.

## Quality Bar

Make the brief dense, concrete, and complete. Avoid vague statements like "it doesn't work" or "the tests fail" without the exact evidence. Do not hide failed attempts; they are useful constraints for the expert. Do not over-compress if details are necessary for diagnosis.

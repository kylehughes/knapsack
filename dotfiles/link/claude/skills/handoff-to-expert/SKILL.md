---
name: "handoff-to-expert"
description: "Create a self-contained escalation brief for a programming/debugging problem when an agent is stuck, repeated fixes have failed, root cause is uncertain, or the user asks to hand off context to a stronger model, senior engineer, teammate, maintainer, or external expert. Produces a no-prior-context packet with goal, failure evidence, relevant code/config, attempted fixes, constraints, hypotheses, and verification criteria."
---

# Handoff to Expert

## Purpose

Create an expert-ready handoff brief, not another speculative fix. The brief must let a capable engineer diagnose the issue without reading the prior conversation. It should preserve the highest-signal facts, evidence, constraints, and failed attempts while avoiding noise, secrets, and unsupported claims.

## When to Use

Use this skill when any of these are true:

- The agent is looping, guessing, or making repeated unsuccessful fixes.
- The root cause remains unclear after reasonable debugging.
- The user asks for a handoff, escalation, expert brief, debugging packet, or summary for another model/person.
- The problem spans multiple files, tools, services, build systems, tests, or runtime environments.
- Continued implementation is likely to waste time without better diagnosis.

Do not use this skill for ordinary first-pass debugging, simple code review, or direct implementation unless the user explicitly asks for an escalation-style brief.

## Core Contract

When invoked, stop trying to solve the bug unless the user explicitly asks for more coding. Gather and compress evidence into a brief that maximizes the expert's chance of solving the problem.

Never imply evidence was inspected, commands were run, or behavior was reproduced unless that actually happened. If information is unavailable, say so precisely and list what would be needed.

## Evidence Priority

Prefer concrete, recent evidence over memory or narrative. If repository or tool access is available, inspect the smallest useful set of artifacts before writing:

1. Current failure output: command, test, stack trace, log, screenshot, or observed UI behavior.
2. Reproduction path: exact steps, inputs, environment, and expected vs. actual behavior.
3. Relevant source: files, functions, types, routes, components, schemas, generated code, or configs.
4. Recent changes: diffs, modified files, dependency updates, migration files, or config edits.
5. System context: language/runtime versions, framework versions, package manager, OS/container details, CI/local differences.
6. Prior attempts: meaningful fixes tried, results, and why each attempt is now weakened or disproven.

If evidence conflicts, preserve the conflict rather than smoothing it over.

## Repository Inspection Guidelines

Use targeted inspection. Do not perform a broad, slow crawl when a few files, tests, logs, or diffs are enough.

High-value checks often include:

- Failing command and exact output.
- Test name, test file, assertion, fixture, and failure location.
- `git diff`, changed files, or relevant uncommitted edits when available.
- Dependency/config files such as package manifests, lockfiles, build settings, env examples, CI config, schema/migration files, and generated-code inputs.
- Entry points and call paths from user action or test setup to failure.

Use `path:line` or `path:start-end` references when possible. Include short snippets only when they clarify better than a file reference. Avoid dumping large files, repeated logs, or full stack traces unless each part matters.

## Security and Privacy

Redact secrets before including evidence. This includes tokens, API keys, passwords, cookies, private keys, credentials, authorization headers, session IDs, personal data, and internal-only URLs when sharing externally.

Preserve debugging value while redacting. Keep field names, shapes, prefixes/suffixes, error classes, status codes, host categories, and variable names when safe. Use placeholders such as `<REDACTED_API_KEY>`, `<USER_ID>`, or `<INTERNAL_HOST>`.

Never recommend sharing proprietary code, customer data, or private logs externally unless the user has authorized it. When external sharing risk exists, include a sanitized version and note what was removed.

## Reasoning Rules

Separate facts, observations, inferences, and hypotheses.

- **Fact:** directly confirmed from code, output, docs, or user-provided evidence.
- **Observation:** behavior seen in a run, test, log, screenshot, or trace.
- **Inference:** a conclusion drawn from facts; explain the bridge.
- **Hypothesis:** a plausible root cause not yet proven; include supporting and contradicting evidence.

Do not invent prior attempts. If the conversation suggests an attempt but details are unclear, write "Reported/unclear attempt" and explain what is known.

Rank hypotheses by plausibility and diagnostic value, not by confidence alone. Prefer hypotheses that explain all observed symptoms and suggest a decisive next check.

## Output Format

Use this structure unless the user requests a different format.

### 1. Executive Summary

One short paragraph with:

- Desired outcome.
- Current blocker.
- Most important evidence.
- Current best hypothesis, if any.

### 2. Problem Statement

Explain the intended behavior and why the current behavior is wrong. Include expected vs. actual behavior.

### 3. Project Context

Describe only the context needed to reason about the issue:

- Language, framework, platform, runtime, package manager, and relevant versions if known.
- Architecture, module boundaries, data flow, lifecycle, external services, database/schema, generated code, or build/test setup.
- Any project conventions that constrain a fix.

### 4. Current Failure

Provide exact symptoms and reproduction information:

- Steps to reproduce.
- Command(s) run, inputs used, or user action taken.
- Failing test(s), assertion(s), stack trace(s), logs, UI state, screenshots, or CI link summaries.
- Whether the failure is deterministic, intermittent, local-only, CI-only, device-specific, environment-specific, or data-dependent.

If reproduction is unknown, give the best-known trigger and label gaps clearly.

### 5. Relevant Evidence

List the relevant artifacts and why each matters. Use file and line references when possible.

Include:

- Source files, functions, types, components, routes, jobs, migrations, schemas, fixtures, generated files, or configs.
- Short code snippets only when necessary.
- Runtime/config/dependency details that materially affect the failure.
- Any contradictory or surprising evidence.

### 6. Attempts So Far

For each meaningful attempt, include:

- What changed or was tested.
- Why it seemed plausible.
- Result observed.
- Why it did not solve the problem or what uncertainty remains.

Separate attempted fixes from passive observations. Do not include trivial or duplicate attempts unless they prevent rework.

### 7. Constraints and Non-Goals

Capture:

- User requirements and acceptance criteria.
- Compatibility requirements, dependency restrictions, API contracts, performance limits, security/privacy requirements, release deadlines, and migration constraints.
- Codebase conventions and architectural boundaries.
- Things the expert should avoid changing.

### 8. Facts vs. Hypotheses

Use two subsections:

**Confirmed facts**

- Bullet only directly supported facts.

**Ranked hypotheses**

For each hypothesis, include:

- Plausibility: high / medium / low.
- Why it fits.
- Evidence against it or missing evidence.
- Fastest decisive test or inspection.

### 9. Missing Information

List missing artifacts that would materially improve diagnosis, such as logs, repro data, failing command output, env vars, dependency versions, screenshots, schema state, CI artifact, or relevant file contents.

Only include items that matter. Do not turn this into a generic questionnaire.

### 10. What Would Prove It Fixed

Name exact verification criteria:

- Test command(s), test names, manual checks, expected logs, screenshots, metrics, or acceptance criteria.
- Regression checks that should stay green.
- Edge cases that should be covered.

### 11. Expert Ask

End with a direct request. Be specific about what help is needed, for example:

- Diagnose the likely root cause.
- Propose the minimal safe patch.
- Identify the missing invariant or architectural mismatch.
- Design a focused test plan.
- Review whether a proposed fix violates project constraints.

## Style and Density

Write for a senior engineer. Be concise, factual, and specific. Use bullets, tables, and short snippets where they improve scanability. Avoid vague phrasing like "it doesn't work," "tests fail," or "probably config" without exact supporting evidence.

Prefer a compact but complete brief over a long transcript summary. Preserve failed attempts and contradictions because they are diagnostic constraints. Avoid conversational filler, apologies, or speculation presented as fact.

## Performance Guardrails

- Gather enough evidence to produce a useful handoff; do not exhaustively inspect the whole project.
- Deduplicate repeated stack traces, logs, and attempts.
- Quote only the relevant lines around failures or invariants.
- Put bulky but necessary details in an appendix.
- If the available context is thin, produce a useful partial brief with a clearly labeled "Missing Information" section rather than blocking on clarification.

## Final Checklist

Before finalizing, verify that the brief answers:

- What is the user trying to accomplish?
- What exactly is failing, and how can it be reproduced?
- What evidence supports the current understanding?
- What code/config/data paths are relevant?
- What has already been tried, and what happened?
- What constraints must a fix respect?
- Which facts are confirmed, and which root causes are still hypotheses?
- What concrete result proves the issue is fixed?
- What should the expert do next?

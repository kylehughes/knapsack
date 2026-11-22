# Agent Routing

How Knapsack decides which model and reasoning effort a delegated task gets in
Claude Code, Codex CLI, and Antigravity CLI, why, and how to keep that decision
current as models change.

The policy that agents read every session is the Delegation section of
`dotfiles/shared/claude/CLAUDE.md`. This document holds what that section is too
short to carry: the reasoning, the evidence, the role of every model each
harness offers, and the upkeep procedure. Read the policy first.

Everything here was last verified on **2026-11-22** against Claude Code 2.1.326,
Codex CLI 0.169.0, Antigravity CLI 1.5.14, and Orca 1.4.266.

## Where Things Live

| What | Where | Notes |
| --- | --- | --- |
| Policy | `dotfiles/shared/claude/CLAUDE.md`, Delegation | Installed for all three CLIs. Names the classes and the roster. |
| Orca workers | Policy, Orca Workers; Orca's `orchestration` skill | The policy names each worker's agent, model, and effort; Orca's skill owns the commands. |
| Claude Code routes | `dotfiles/shared/claude/agents/*-worker.md` | Frontmatter `model` and `effort` are the pins. |
| Codex routes | `dotfiles/shared/codex/agents/*-worker.toml` | `model` and `model_reasoning_effort` are the pins. |
| Codex validator | `dotfiles/shared/codex/hooks/validate-agent-route.py` | Reads the pins from the installed role files. It names no model. |
| Roster check | `scripts/tests/test-agent-roster.py` | Fails when a roster table disagrees with the route files. |
| Codex activation | README, Codex Routing | Registration, hook trust, and the runtime smoke test. |

A route's model and effort are pinned only in its route file. The Codex
validator, setup script, and status check read those files, so none of them
names a model. The roster tables in the policy, this guide, and the README
repeat the pins, and the roster check fails when one disagrees. It also checks
the effort named in each Claude route description and the Orca worker examples
in the policy. It does not check this guide's inventory tables, the Antigravity
model IDs, or prose that counts routes or names a model, so search for the old
model name after a change.

## Orca Workers or Native Subagents

Orca is where delegated work is coordinated, in every model family. A task goes
to an Orca worker when it edits code, reviews, runs long or in parallel, needs
its own worktree, or belongs to another model family. Native subagents keep
only quick read-only work whose sole output is a conclusion: lookups and
digests of verbose test or log output.

The split follows what each one costs and gives. A native subagent shares the
parent's process and returns a summary, so a lookup costs little beyond its own
tokens. An Orca worker is a full session in its own terminal: it can run any
harness, can get its own worktree, and stays visible, so I can watch or talk to
it. That is worth its startup cost for real work and not for a lookup. Orca's
own skill gives the same advice.

An Orca worker is a top-level session, so the native routes do not apply to it.
`worker-start` takes the class's model and effort as `--model` and `--effort`;
Codex takes the model ID, and Antigravity carries effort in the model ID. The
Codex validator sees only native `spawn_agent` calls, so nothing enforces an
Orca worker's pairing; the policy's examples show the difficult pairings, and
the roster check verifies them.

## The Decision Model

The goal is the best output for the least usage. Three facts shape everything
else:

1. **Usage is paid per finished task, not per token.** A stronger model can
   finish with less work, and a failed attempt bills its tokens, then the retry.
2. **A worker's failure is paid for again at the parent's rates.** The parent is
   usually the most expensive model in the session. Reading a bad result,
   noticing it is bad, and re-briefing can cost more than the worker did.
3. **Whether a mistake gets caught matters more than how hard the task is.**
   When a check exists, running cheap and re-running failures higher beats
   running everything high. When no check exists, a miss is silent and the only
   defense is buying quality up front.

So a task's class comes from two questions: how much the worker has to work out
for itself, and whether a wrong or incomplete result would be caught cheaply.

| Class | The worker must work out | A miss is caught by | Tier and effort |
| --- | --- | --- | --- |
| Mechanical | Nothing | The verification command | Small, high |
| Scout | Where to look | The parent, at a glance | Small, high |
| Ordinary | How to build it | The verification command | Workhorse, medium |
| Thorough | What is going on, or what the check misses | Partly, or late | Workhorse, high |
| Difficult | The answer itself | Nothing | Strongest worker |

Claude Code is the exception to the tier column. It runs each class one tier
up: mechanical and scout on Sonnet, ordinary and thorough on Opus. The reasons
are under Claude Code below. Antigravity follows the same idea for ordinary
and thorough work, which run on Neon.

Importance is deliberately not a question. A one-line change to a payment path
is still mechanical if the instructions are exact.

### Effort Bands

Each tier has a range of effort worth paying for. Below it the model
underperforms a cheaper one; above it a stronger model is the better buy.

| Tier | Models today | Band | Why |
| --- | --- | --- | --- |
| Small | GPT-6 Luna, Gemini 3.8 Flash; Haiku 5.5, which holds no route | `high` | Luna costs about a twentieth of the workhorse price per token, so thoroughness is nearly free; Flash costs half of Hydrogen. The tier's failure mode at low effort is stopping early or skipping a check. |
| Workhorse | Sonnet 5.5, GPT-6.2 Sol, Gemini 4 Hydrogen as Neon's fallback | `medium` to `high` | `medium` to `high` buys 7 to 15 points on coding benchmarks for about 1.7 times the cost. Past `high` the curve flattens. |
| Strongest worker | Opus 5.5, GPT-6.2 Astra at `medium`, Gemini 4 Neon | `medium` to `high`, `xhigh` as a retry | At `low` it only matches the workhorse at `high`, and review work collapses. In Anthropic's measurements, Opus at `xhigh` costs about half of Fable at `high` for the same pass rate. |
| Frontier | Fable 5.2, GPT-6.2 Astra above `medium` | By request | Fable is ahead of Opus by a few points for 1.5 to 2.4 times the cost. These are also the orchestrators, whose plan allowance workers would be spending. |

`max` is never pinned: both vendors describe diminishing returns there, and
Anthropic calls it prone to overthinking. Codex's `ultra` is never given to a
worker because it delegates on its own.

"Frontier" means a vendor's most capable model: Fable 5.2 for Anthropic and
GPT-6.2 Astra for OpenAI. Anthropic has a tier between its workhorse and its
frontier model, and Opus fills it. OpenAI has none, so on Codex the strongest
worker is Astra itself, held to `medium`.

## Roster

The roster check parses every cell of this form in the policy, this guide, and
the README. Keep each cell in the form
`` `route` — `model`, `effort` ``.

| Class | Claude Code | Codex CLI |
| --- | --- | --- |
| Mechanical | `mechanical-worker` — `claude-sonnet-5-5`, `medium` | `mechanical_worker` — `gpt-6-luna`, `high` |
| Scout | `scout-worker` — `claude-sonnet-5-5`, `high` | `scout_worker` — `gpt-6-luna`, `high` |
| Ordinary | `ordinary-worker` — `claude-opus-5-5`, `medium` | `ordinary_worker` — `gpt-6.2-sol`, `medium` |
| Thorough | `thorough-worker` — `claude-opus-5-5`, `high` | `thorough_worker` — `gpt-6.2-sol`, `high` |
| Difficult | `difficult-worker` — `claude-opus-5-5`, `high` | `difficult_worker` — `gpt-6.2-astra`, `medium` |

Deviations use the per-call `model` and `effort` parameters in Claude Code and
`custom_worker` in Codex. Antigravity has no routes; see below.

### Claude Code

| Model | ID | Price per MTok, in / out | Claude Code default effort | Role |
| --- | --- | --- | --- | --- |
| Haiku 5.5 | `claude-haiku-5-5` | $0.10 / $0.50, or $0.50 / $2.50 on a request whose prompt exceeds 100,000 tokens | `medium` | Unrouted. Per call, only by request. |
| Sonnet 5.5 | `claude-sonnet-5-5` (`sonnet`) | $2 / $10 | `medium` | Mechanical at `medium`, scout at `high` |
| Opus 5.5 | `claude-opus-5-5` (`opus`) | $4 / $20 | `medium` | Ordinary at `medium`, thorough and difficult at `high` |
| Fable 5.2 | `claude-fable-5-2` (`fable`) | $8 / $40 | `medium` | Orchestrator. A worker only by request or after the difficult route fails. |

All four support `low`, `medium`, `high`, `xhigh`, and `max`.

- **No small model.** Until 2026-11-19 mechanical and scout work ran on Haiku
  5.5 at `high`. They moved to Sonnet on preference, not on a measurement:
  Haiku is about twenty times cheaper per token, and Anthropic places it on
  "high-volume and latency-sensitive work with checkable outputs," which is
  these two classes. The move buys fewer bad lookups and botched edits for the
  parent to notice and re-brief. Haiku remains available per call by request.
- **Sonnet at `medium` for mechanical, `high` for scout.** Sonnet at `medium`
  scored about 7 points below `high` on Anthropic's SWE-bench Pro subset for
  about 59% of the cost. A mechanical task has exact instructions and a
  verification command, so `medium` is enough. A scout's miss is a fact left
  out of a report, which no command catches, and on the Artificial Analysis
  index Sonnet at `medium` only matches Haiku at `high` (31 against 30), so
  scouting at `medium` would have bought nothing.
- **Opus wherever the worker makes a decision.** Until the same date ordinary
  and thorough work ran on Sonnet at `medium` and `high`. They moved to Opus on
  working experience, not on a new benchmark: Opus has been efficient and
  reliable enough per finished task, and light enough on the plan allowance,
  that Sonnet's saving is not worth its misses on anything with a decision in
  it. The measurements agree on quality and price the difference. On
  Anthropic's SWE-bench Pro subset Opus at `medium` solved 92.8% for $0.22 per
  solved task, against 87.6% for $0.11 for Sonnet at `high`, and Sonnet at
  `medium` scored about 7 points lower still. Sonnet costs half as much per
  task and fails more than one task in ten, and each failure is paid for again
  at the parent's rates.
- **What that gives up.** On Anthropic's defect search, Opus with Sonnet
  subagents cost about a third less than Opus alone for about the same score.
  If the allowance ever becomes the constraint, ordinary work is the first
  class to move back, to Sonnet at `high`.
- **Three classes share one model.** Ordinary runs at `medium`; thorough and
  difficult both run at `high`. The classes still differ in each worker's
  instructions and on Codex. A retry on Claude Code is therefore an effort
  step, ending at a per-call `xhigh`, before Fable is considered.
- **Never Opus at `low`.** Opus at `low` and Sonnet at `high` land on the same
  point (87.4% for $0.12 against 87.6% for $0.11 per solved task), so `low`
  gives back what the move to Opus bought.
- **Opus at `high` for thorough and difficult work.** On the SWE-bench Pro subset Opus moves
  from 92.8% at `medium` to 95.3% at `high`, for $0.21 and $0.29 per task. On
  Anthropic's defect-search benchmark it scored 34 points lower at `low` than at
  `medium`, so judgment work is the most effort-sensitive kind there is.
- **Opus before Fable.** On the 463 problems Anthropic used to compare the two,
  Opus at `xhigh` solved 96.5% for $0.75 per solved task, "level with Fable 5.2
  at `high` for a little over half the cost" ($1.39). Fable at `low` solved
  94.6% for $0.39, behind Opus at `high` (95.5% for $0.30). Fable's lead shows
  up on harder reasoning: 1.6 to 5.9 points over Opus at `high` on defect
  search, for 1.5 to 2.4 times the cost.
- **Fable's allowance is the orchestrator's.** On Max, Ultra, and premium Team
  seats, Fable can use up to half of the weekly limit and draws it down "faster
  than other Claude models"; on Pro it bills to usage credits. A Fable worker
  spends the budget the main session runs on.
- **Unrouted agents inherit the parent.** Explore, Plan, general-purpose, and
  plugin agents without a pinned model run on the session's model. On a Fable
  session that is Fable, except that Explore drops to Opus on a subscription.
  A subagent on a different model than the session does not inherit the
  session's effort; it runs at that model's saved or default level unless the
  call or the definition sets one. This is why the policy asks for both `model`
  and `effort` on every such call.

### Codex CLI

| Model | ID | Price per MTok, in / out | Credits per MTok, in / out | Catalog default effort | Role |
| --- | --- | --- | --- | --- | --- |
| GPT-6 Luna | `gpt-6-luna` | $0.10 / $0.50 | 2.5 / 12.5 | `medium` | Mechanical and scout, at `high` |
| GPT-6.1 Terra | `gpt-6.1-terra` | $1 / $5 | 25 / 125 | `low` | Unrouted. Override candidate for screenshot and computer-use subtasks. |
| GPT-6.2 Sol | `gpt-6.2-sol` | $2 / $10 | 50 / 250 | `low` | Ordinary at `medium`, thorough at `high` |
| GPT-6.2 Astra | `gpt-6.2-astra` | $8 / $40 | 200 / 1,000 | `low` | Difficult, at `medium`. Also the orchestrator. |

Luna supports `low` through `max`; the others add `ultra`. The catalog also
lists GPT-6.1 Sol, GPT-6 Astra, GPT-6 Sol, and the GPT-5.6 family. Each is a
superseded version of a model above and has no route.

- **Luna at `high`.** OpenAI's subagent guidance: "If you select GPT-6 Luna
  explicitly, start with `high`," and use it "for fast, narrowly scoped agents
  handling clear, repeatable, or high-volume work." No newer small model exists;
  Luna is still the GPT-6 generation.
- **Sol at `medium` and `high`, never the catalog's `low`.** The catalog
  describes `medium` as balancing "speed and reasoning depth for everyday
  tasks" and `high` as "greater reasoning depth for complex problems." The only
  per-effort coding data available is for GPT-6 Sol, where `low` solved 37.2%
  of DeepSWE, `medium` 56.6%, `high` 65.3%, and `xhigh` 66.6%, at $0.16, $0.38,
  $0.64, and $1.00 per task.
- **Astra at `medium` for difficult work.** Sol and Astra are four times apart
  in price with nothing between them. On the same GPT-6 data, Astra at `low`
  (67.0% for $1.60) barely clears Sol at `high`, and Astra at `medium` (72.8%
  for $3.08) is the first setting Sol cannot reach at any effort; Astra is flat
  above that. Difficult work is where a miss is silent, so it gets the setting
  that is actually stronger and no more.
- **This is the costliest pin in the roster.** A difficult task on Astra costs
  roughly five times one on Sol at `high`. It stays cheap in total only if the
  class stays narrow. Hard work that a check can catch belongs on thorough,
  with escalation on a demonstrated failure.
- **Terra is unproven for coding.** OpenAI positions it for "clear writing,
  visual understanding, and computer use." Independent index scores make it
  look strong for its price, but nothing measures it on agentic coding, so it
  holds no pinned route.
- **Role files lock their settings.** Codex tells the parent a role's model and
  effort "cannot be changed," and a role file beats explicit spawn arguments.
  The validator turns a silent mismatch into a clear rejection.
- **Routed spawns start fresh.** In 0.169 the spawn tool accepts `fork_turns` of
  `none` or `all`, and still parses a legacy turn count as `all`
  (`multi_agents_v2/spawn.rs`: "Accept legacy turn counts without limiting the
  inherited history"). The validator therefore accepts only `fork_turns=none`,
  or `fork_context=false` on runtimes that expose that field.

### Antigravity CLI

`agy` supports subagents, but a custom agent chooses only a tier: `model` takes
`inherit`, `flash`, or `pro`, and there is no effort field. Its definitions live
in `~/.gemini/config/agents/` and use different field and tool names from
Claude Code's. The classes cannot be pinned there, so Knapsack installs no
Antigravity routes and the policy tells the agent which model to run instead.

| Model | ID pattern | API price per MTok, in / out | Role |
| --- | --- | --- | --- |
| Gemini 3.8 Flash | `gemini-3.8-flash-{low,medium,high}` | $0.75 / $3.75, doubling on 2027-01-01 | Mechanical and scout, at `high` |
| Gemini 4 Hydrogen | `gemini-4-hydrogen-{low,medium,high,xhigh}` | $1.50 / $7.50 | Fallback for Neon at the same effort |
| Gemini 4 Neon | `gemini-4-neon-{low,medium,high,xhigh}` | $3 / $15, as reported at launch | Preferred. Ordinary at `medium`; thorough, difficult, and second opinions at `high`; `xhigh` as a retry |
| Gemini 4 Argon | `gemini-4-argon-{low,medium,high}` | $2 / $10, doubling on 2026-12-01 | Unrouted. Superseded by Neon. |
| Orchestrator (Neon) | `gemini-pro-orchestrator-neon` | Not published | An interactive session model, not a worker |
| Orchestrator (Argon) | `gemini-pro-orchestrator-g1-pro` | Not published | Superseded by the Neon orchestrator |
| Claude and GPT models | `claude-*`, `gpt-oss-120b-medium` | Not applicable | Unrouted. Use each model's own harness. |

- **Effort is part of the model ID.** A `-high` suffix and `--effort high` are
  two spellings of the same request. Google does not document which wins when
  they disagree, so pass the suffixed ID alone.
- **Neon is the preferred Gemini model.** Google released it on 2026-11-18 as
  "frontier-level intelligence with fast end-to-end task completion," adapted
  from Carbon and placed between Hydrogen and Carbon. It defaults to `high` and
  supports `low` through `xhigh`. Launch coverage puts it at 59 on the
  Artificial Analysis Coding Agent Index at `xhigh`, level with Opus 5.5 and
  Fable 5.2 at 58, and reports that it replaces Argon in the Gemini app. It is
  the default for every class with a decision in it by preference, as Opus is
  on Claude Code; the scores above come from secondary sources and are not yet
  checked against Google's own pages.
- **Quota is pooled.** Gemini models share a weekly and a five-hour limit. How
  Neon draws on them is not yet documented, so fall back to Hydrogen at the
  same effort when `agy -p /usage` shows the account running short.
- **Flash loses its place in January.** At $1.50 / $7.50 it will cost the same
  as Hydrogen through the API. Move mechanical and scout work to Hydrogen at
  `low` or `medium` then, unless Antigravity's quota still favors Flash.
- **Orchestrator routes on its own.** Google recommends it for most day-to-day
  work: the strong model plans and Hydrogen implements, at a fixed configuration that
  ignores `--effort`. It is a reasonable interactive default and a poor
  headless worker, because the caller cannot choose its depth.
- **Gemini 4 Carbon** is Google's strongest model and does not appear in this
  account's `agy models`. If it does, it is the frontier tier, by request only.
- **Knapsack installs nothing under `~/.gemini/agents/`.** It once copied the
  Claude Code agents there for Gemini CLI. Antigravity does not read that
  directory, so the copy was removed on 2026-11-17 and setup retires any left
  behind.

## Evidence

Vendor measurements are directional and come from each vendor's own harness.
Scores are not comparable across benchmarks, so compare within a row.

### Anthropic, measured by Anthropic

Source: [Optimizing for cost and intelligence](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence).

Anthropic reports the SWE-bench Pro subset three ways, and the figures differ
slightly between them. Each bullet in this guide says which one it quotes.

| Setting | All 478 problems, cost per task | All 478, cost per solved task | 463 problems, cost per solved task |
| --- | --- | --- | --- |
| Sonnet 5.5, `medium` | About 7 points below `high`, at about 59% of its cost | Not reported | Not reported |
| Sonnet 5.5, `high` | Not reported | 87.6% for $0.11 | Not reported |
| Opus 5.5, `low` | 87.4% for $0.11 | 87.4% for $0.12 | Not reported |
| Opus 5.5, `medium` | 92.8% for $0.21 | 92.8% for $0.22 | 93.1% for $0.22 |
| Opus 5.5, `high` | 95.3% for $0.29 | Not reported | 95.5% for $0.30 |
| Opus 5.5, `xhigh` | 96.7% for $0.74, one run | Not reported | 96.5% for $0.75 |
| Fable 5.2, `low` | Not reported | Not reported | 94.6% for $0.39 |
| Fable 5.2, `high` | Not reported | Not reported | 96.3% for $1.39 |

- Checkable work is cheapest run low and re-run on failure: Opus at `low` with
  failures re-run at `high` solved about 97% for about $0.17 a task, against
  95.3% for $0.29 with everything at `high`. The method needs a failure signal;
  "a checker that passes bad work lets those failures through."
- Delegation "came out ahead in only two situations": routine work with a long
  cost tail, and work larger than one context window. For a dependent chain,
  one model at lower effort won every case measured.
- On defect search, Opus with Sonnet subagents cost about a third less than
  Opus alone per part and scored about the same. Swapping Fable in as the
  orchestrator cost 19% more for the same score.
- Haiku subagents under Opus at `medium` cut cost per attempt by 32% and the
  pass rate by about 4 points, "an alternative to lowering effort, not better."
- Haiku 5.5 at `medium` passed 93% of a Managed Agents task set for about
  $0.011 per passed attempt.

### OpenAI

- Subagent guidance, from the [Codex subagents documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents):
  "Use Sol for everyday agents that plan, use tools, and check their work," and
  "raise the effort for a subtask that needs deeper investigation, or lower it
  for a quick scan."
- Prices and credit rates, from the [API pricing](https://developers.openai.com/api/docs/pricing)
  and [Codex pricing](https://learn.chatgpt.com/docs/pricing) pages. Credit
  rates are 25 times the dollar price for every model, so effort changes usage
  only through token count.
- Effort levels and defaults, from `codex debug models` on this Mac.
- Per-effort DeepSWE figures are for **GPT-6, not GPT-6.2**, transcribed by a
  third party from OpenAI's launch charts. OpenAI has published no per-effort
  data for 6.2. Treat the shape of those curves as the evidence, not the
  numbers.

### Independent

[Artificial Analysis](https://artificialanalysis.ai) Intelligence Index v5.0.1,
by effort from `low` to `max`. It measures general capability, not coding.

| Model | Score | Output tokens for the run, millions |
| --- | --- | --- |
| Haiku 5.5 | 19 / 25 / 30 / 35 / 36 | 30 / 53 / 90 / 151 / 298 |
| Sonnet 5.5 | 26 / 31 / 42 / 50 / 55 | 21 / 29 / 55 / 111 / 335 |
| Opus 5.5 | 35 / 48 / 52 / 57 / 59 | 21 / 43 / 56 / 101 / 218 |
| GPT-6.1 Terra | 29 / 38 / 42 / 45 / 51 | 7 / 14 / 21 / 35 / 99 |
| Gemini 4 Hydrogen | 27 / 41 / 51 / 54, no `max` | 20 / 54 / 110 / 304 |

Two patterns here match the vendor data. The largest steps line up with the
pins: Sonnet's is `medium` to `high`, the line a workhorse tier draws between
ordinary and thorough, and Opus's is `low` to `medium`, which is why it never
runs below `medium`.
And every model's last step buys the fewest points per token.

A [practitioner measurement](https://www.latitude.so/blog/reasoning-effort-only-matters-without-tests)
from July 2026 supports the checkable and uncheckable split. On six bug fixes
with tests available, Opus 5 solved 18 of 18 runs at every effort level, and
`low` cost about half of `max` per solve. On one debugging task with the tests
hidden it solved 0 of 13 at `low` and `medium`, 1 at `high`, 3 at `xhigh`, and
8 at `max`. The hidden-test result rests on a single task, the model is one
generation old, and the benchmark is the author's own.

## When a Model Ships

Releases move both the capability gap and the price ratio, so each one is a
reason to re-check a row and rarely a reason to redesign. Work through this for
the new model:

1. **Place it in a tier.** Use the vendor's own positioning and its price
   relative to the model it replaces. A new version of a routed model is a
   candidate for that model's routes and no others.
2. **Collect five facts.** Its ID, its price per million tokens, the effort
   levels it supports, the harness's default effort, and the vendor's stated
   starting effort for agentic work. `codex debug models` and `agy models`
   answer most of this locally; for Claude, read the model configuration and
   effort pages.
3. **Find the knee of its effort curve.** Look for a per-effort table from the
   vendor or from an independent index. The knee is the last step that still
   buys several points for less than twice the cost. With no data, keep the
   effort the route already has.
4. **Check its neighbors.** At the knee, compare cost per solved task with the
   tier below one step higher and the tier above one step lower. If a neighbor
   wins on both score and cost, narrow the band.
5. **Leave the classes alone unless a tier appeared or vanished.** A new tier
   between two routes is a reason to move a class. A vendor dropping a tier,
   as OpenAI has between Sol and Astra, is a reason to pin the next tier up at
   a lower effort.
6. **Record what changed here**: the inventory row, any bullet whose numbers
   moved, and the verification date at the top.

Things that should prompt a look even without a release: a price change, a
harness changing a default effort, or a new knob such as a per-call parameter
or environment variable. One price change that affects a class is already scheduled: Gemini 3.8 Flash
doubles to $1.50 / $7.50 on 2027-01-01, which is Hydrogen's price.

## Changing a Route

1. Edit the route file: `model` and `effort` in
   `dotfiles/shared/claude/agents/`, or `model` and `model_reasoning_effort` in
   `dotfiles/shared/codex/agents/`. A Claude route's description names its
   tier and effort, not its model.
2. Update the roster tables in `dotfiles/shared/claude/CLAUDE.md`, this
   document, and the README, then search all three for the old model name.
3. Run `make check/repository`. The roster check reports any table that still
   disagrees with a route file.
4. Run `make set-up/dotfiles`, then `make check/dotfiles` and
   `make check/agents`.
5. For Codex, run `make set-up/codex-routing` if a route was added, renamed, or
   removed, then `make check/codex-routing` and the runtime smoke test in the
   README. Passing unit tests do not show that a spawn is intercepted.

To add a class, add one `<class>-worker` route file per harness and its row to
the three tables. The validator, the setup script, and the status check pick up
a new Codex profile from the directory. A pinned effort above `high` fails the
tests on purpose.

To rename or remove a Codex route, add its old role name to `RETIRED_ROLES` in
`scripts/check-codex-routing.py`. Setup then clears that registration from
`~/.codex/config.toml`, which would otherwise point at a profile the installer
has removed, and the status check reports it until setup has run.

The validator treats every `*-worker.toml` in `~/.codex/agents` as a route,
including local ones. A local profile it cannot read denies every spawn, and
`make check/codex-routing` reports it.

## Open Questions

- **GPT-6.2 by effort.** The Sol and Astra pins rest on GPT-6 curves and
  OpenAI's descriptions of each level. A 6.2 per-effort table would settle
  whether Sol's `medium` and Astra's `medium` are still the right points.
- **Terra as a scout or ordinary worker.** Its index scores suggest it could
  replace Luna for scouting or undercut Sol on routine work at half the price.
  It needs a coding measurement first.
- **Haiku for mechanical and scout work.** It held both classes until
  2026-11-19 and costs about a twentieth of Sonnet. If the plan allowance
  becomes the constraint, these two classes are the cheapest to move back.
- **Antigravity tiers.** What `flash` and `pro` resolve to on a signed-in
  account, and whether an omitted `tools` list means all tools or none, are
  undocumented. Either answer could make native routes worth installing.
- **A Claude Code default for unrouted agents.** `CLAUDE_CODE_SUBAGENT_MODEL`
  would keep an unrouted subagent off the session's model. Knapsack does not
  set it: the policy asks for an explicit model on every call, and a default
  would hide the calls that forgot.

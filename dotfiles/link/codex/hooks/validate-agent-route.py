#!/usr/bin/env python3
"""Validate declared Codex subagent routes from a PreToolUse JSON event on stdin."""

import json
import sys


MAX_INPUT_BYTES = 1048576
SPAWN_TOOL_NAMES = (
    "spawn_agent",
    "Agent",
    "collaborationspawn_agent",
)
PROFILES = {
    "knapsack_mechanical": ("gpt-6-luna", "high"),
    "knapsack_ordinary": ("gpt-6-sol", "medium"),
    "knapsack_difficult": ("gpt-6-sol", "medium"),
}
ROUTES = (*PROFILES, "knapsack_override")


def validate(event):
    """Return a corrective reason, or None to leave the tool decision untouched."""
    if not isinstance(event, dict):
        return "Agent routing expected a JSON event object."
    if not isinstance(event.get("hook_event_name"), str):
        return "Agent routing expected a hook_event_name string."
    if event.get("hook_event_name") != "PreToolUse":
        return None
    if not isinstance(event.get("tool_name"), str):
        return "Agent routing expected a tool_name string."
    if event.get("tool_name") not in SPAWN_TOOL_NAMES:
        return None
    arguments = event.get("tool_input")
    if not isinstance(arguments, dict):
        return "Agent routing requires an object in tool_input."
    route = arguments.get("agent_type")
    if not isinstance(route, str) or route not in ROUTES:
        return (
            "Select agent_type: knapsack_mechanical (gpt-6-luna high), "
            "knapsack_ordinary (gpt-6-sol medium), knapsack_difficult (gpt-6-sol medium), "
            "or knapsack_override (explicit model and effort). "
            "If the spawn tool has no agent_type field, this runtime is unsupported."
        )
    model = arguments.get("model")
    effort = arguments.get("reasoning_effort")
    if "fork_turns" in arguments and "fork_context" in arguments:
        return "Use only the context selector exposed by this runtime, not both fork_turns and fork_context."
    if route in PROFILES:
        expected_model, expected_effort = PROFILES[route]
        if model not in (None, expected_model) or effort not in (None, expected_effort):
            return "The model or effort conflicts with the selected route; use knapsack_override for an intentional deviation."
    elif not all(isinstance(value, str) and value.strip() for value in (model, effort)):
        return "knapsack_override requires explicit model and reasoning_effort; state the reason in the task contract."

    # Runtime generations expose different context selectors. Never guess which
    # default applies, or silently carry a full conversation into a cheaper task.
    turns = arguments.get("fork_turns")
    partial = isinstance(turns, str) and turns.isascii() and turns.isdigit() and int(turns) > 0
    if turns == "none" or partial or arguments.get("fork_context") is False:
        return None
    return "Choose fresh or bounded context explicitly: fork_turns=none (or a positive turn count), or fork_context=false on runtimes exposing that field."


def main():
    data = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    try:
        if len(data) > MAX_INPUT_BYTES:
            raise ValueError("Input exceeds the bound")
        reason = validate(json.loads(data))
    except (ValueError, UnicodeError, RecursionError):
        reason = "Agent routing could not read a bounded JSON event; no task content was logged."
    output = {} if reason is None else {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Validate declared Codex subagent routes from a PreToolUse JSON event on stdin."""

import json
import re
import sys
from pathlib import Path


MAX_INPUT_BYTES = 1048576
SPAWN_TOOL_NAMES = (
    "spawn_agent",
    "Agent",
    "collaborationspawn_agent",
)
# The role files installed beside this hook are the only place a route's model
# and effort are written down, so changing a model never touches this script.
PROFILE_DIRECTORY = Path(__file__).resolve().parent.parent / "agents"
# Route profiles use quoted scalar assignments; this avoids requiring Python 3.11's tomllib.
PROFILE_ASSIGNMENT = re.compile(r'^([a-z_]+) = "([^"\n]*)"$', re.MULTILINE)
# A routing key written any other way would be skipped and quietly unpin the route.
ROUTING_KEY = re.compile(r"^\s*(name|model|model_reasoning_effort)\b", re.MULTILINE)


def load_routes(directory=PROFILE_DIRECTORY):
    """Return each route's pinned (model, effort), or None for a route that pins neither."""
    routes = {}
    for path in sorted(Path(directory).glob("*-worker.toml")):
        text = path.read_text()
        profile = dict(PROFILE_ASSIGNMENT.findall(text))
        if len(ROUTING_KEY.findall(text)) != sum(key in profile for key in ("name", "model", "model_reasoning_effort")):
            raise ValueError("Unreadable route profile")
        name = profile.get("name")
        model = profile.get("model")
        effort = profile.get("model_reasoning_effort")
        # A half-pinned route would inherit the other setting from the parent.
        if not name or name in routes or (model is None) != (effort is None):
            raise ValueError("Malformed route profile")
        routes[name] = None if model is None else (model, effort)
    if not routes:
        raise ValueError("No route profiles")
    return routes


def describe(routes):
    """List the routes with their pins for a corrective message."""
    return ", ".join(
        f"{name} (explicit model and effort)" if pin is None else f"{name} ({pin[0]} {pin[1]})"
        for name, pin in routes.items()
    )


def validate(event, directory=PROFILE_DIRECTORY):
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
    try:
        routes = load_routes(directory)
    except (OSError, ValueError):
        return "Agent routing could not read its route profiles; run make set-up/dotfiles in Knapsack."
    route = arguments.get("agent_type")
    if not isinstance(route, str) or route not in routes:
        return (
            "Select agent_type: " + describe(routes) + ". "
            "If the spawn tool has no agent_type field, this runtime is unsupported."
        )
    model = arguments.get("model")
    effort = arguments.get("reasoning_effort")
    if "fork_turns" in arguments and "fork_context" in arguments:
        return "Use only the context selector exposed by this runtime, not both fork_turns and fork_context."
    pin = routes[route]
    if pin is not None:
        if model not in (None, pin[0]) or effort not in (None, pin[1]):
            unpinned = " or ".join(name for name, other in routes.items() if other is None)
            return (
                "The model or effort conflicts with the selected route; "
                f"use {unpinned or 'an unpinned route'} for an intentional deviation."
            )
    elif not all(isinstance(value, str) and value.strip() for value in (model, effort)):
        return f"{route} requires explicit model and reasoning_effort; state the reason in the task contract."

    # Codex 0.169 runs any fork_turns value other than none, including a legacy
    # turn count, as a full-history fork. Only an explicit fresh start keeps the
    # parent's whole conversation out of a cheaper task.
    if arguments.get("fork_turns") == "none" or arguments.get("fork_context") is False:
        return None
    return "Start routed agents with fresh context: fork_turns=none, or fork_context=false on runtimes exposing that field."


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

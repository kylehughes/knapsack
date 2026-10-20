"""Pure composition helpers for machine-local agent configuration.

These functions accept decoded JSON objects and never modify their inputs or
perform IO. Callers own parsing, atomic writes, and recording ownership baselines.
"""

from copy import deepcopy


ROUTING_COMMAND = 'python3 "$HOME/.codex/hooks/validate-agent-route.py"'


class CompositionError(ValueError):
    """Configuration is malformed or an owned hook has local modifications."""


def _object(value, label):
    if not isinstance(value, dict):
        raise CompositionError(f"{label} must be an object")


def _validate_claude(value, label):
    _object(value, label)
    for field in ("enabledPlugins", "extraKnownMarketplaces"):
        if field in value:
            _object(value[field], f"{label}.{field}")


def compose_claude_settings(base, overlay):
    """Recursively merge objects, replacing arrays and all other leaf values.

    Both inputs must be objects, with object-valued plugin fields when present.
    Unknown fields are preserved. Use an empty object for an absent overlay.
    """
    _validate_claude(base, "base")
    _validate_claude(overlay, "overlay")

    def merge(left, right):
        result = deepcopy(left)
        for key, value in right.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = merge(result[key], value)
            else:
                result[key] = deepcopy(value)
        return result

    return merge(base, overlay)


def _validate_hooks(value, label):
    _object(value, label)
    if "hooks" not in value:
        return
    _object(value["hooks"], f"{label}.hooks")
    for event, groups in value["hooks"].items():
        if not isinstance(groups, list):
            raise CompositionError(f"{label}.hooks.{event} must be an array")
        for group in groups:
            _validate_group(group, f"{label}.hooks.{event}")


def _validate_group(group, label):
    _object(group, label)
    if "matcher" in group and not isinstance(group["matcher"], str):
        raise CompositionError(f"{label}.matcher must be a string")
    if not isinstance(group.get("hooks"), list):
        raise CompositionError(f"{label}.hooks must be an array")
    for handler in group["hooks"]:
        _object(handler, f"{label} handler")
        if not isinstance(handler.get("type"), str):
            raise CompositionError(f"{label} handler type must be a string")
        if handler["type"] == "command" or "command" in handler:
            if not isinstance(handler.get("command"), str):
                raise CompositionError(f"{label} command must be a string")
        if "timeout" in handler and (
            isinstance(handler["timeout"], bool)
            or not isinstance(handler["timeout"], (int, float))
            or handler["timeout"] <= 0
        ):
            raise CompositionError(f"{label} timeout must be a positive number")


def _owned_definition(group, label):
    _validate_group(group, label)
    if set(group) != {"matcher", "hooks"} or len(group["hooks"]) != 1:
        raise CompositionError(f"{label} must contain one canonical routing handler")
    handler = group["hooks"][0]
    if handler["type"] != "command" or not handler["command"]:
        raise CompositionError(f"{label} must contain a routing command")
    return deepcopy(group)


def reconcile_codex_hooks(existing, desired, previous_owned=None):
    """Return ``(configuration, owned_baseline)`` without changing the inputs.

    ``desired`` is the full tracked hook document, with exactly one PreToolUse
    group containing one command handler. The returned baseline is that group
    (only ``matcher`` and ``hooks``), suitable for ``previous_owned`` next time.
    Existing handlers with the exact routing command, desired command, or prior
    command are ownership candidates. Each must match the desired or previous
    matcher and complete handler; any other candidate is a conflict. Similar
    command strings are unrelated and never adopted by substring matching.

    Canonical duplicates collapse at their first position. Unrelated event and
    handler order, top-level fields, and group metadata survive reconciliation.
    A matcher change splits mixed groups so unrelated handlers retain theirs.
    """
    _validate_hooks(existing, "existing")
    _validate_hooks(desired, "desired")
    desired_events = desired.get("hooks", {})
    if set(desired_events) != {"PreToolUse"} or len(desired_events["PreToolUse"]) != 1:
        raise CompositionError("desired must define exactly one PreToolUse group")
    baseline = _owned_definition(desired_events["PreToolUse"][0], "desired group")
    accepted = [baseline]
    if previous_owned is not None:
        accepted.append(_owned_definition(previous_owned, "previous owned group"))
    commands = {ROUTING_COMMAND}
    commands.update(group["hooks"][0]["command"] for group in accepted)

    # Check every candidate before constructing the result, including candidates
    # moved to another event, which cannot safely be adopted as PreToolUse hooks.
    for event, groups in existing.get("hooks", {}).items():
        for group in groups:
            for handler in group["hooks"]:
                if handler.get("command") not in commands:
                    continue
                if event != "PreToolUse" or not any(
                    group.get("matcher") == known["matcher"]
                    and handler == known["hooks"][0]
                    for known in accepted
                ):
                    raise CompositionError("owned Codex routing hook has local modifications")

    result = deepcopy(existing)
    events = result.setdefault("hooks", {})
    groups = events.setdefault("PreToolUse", [])
    reconciled = []
    inserted = False
    for group in groups:
        candidate_indexes = [
            index for index, handler in enumerate(group["hooks"])
            if handler.get("command") in commands
        ]
        if not candidate_indexes:
            reconciled.append(group)
            continue
        unrelated = [
            handler for handler in group["hooks"]
            if handler.get("command") not in commands
        ]
        if not inserted:
            if group["matcher"] == baseline["matcher"] or not unrelated:
                group["matcher"] = baseline["matcher"]
                group["hooks"] = unrelated
                group["hooks"].insert(candidate_indexes[0], deepcopy(baseline["hooks"][0]))
                reconciled.append(group)
            else:
                reconciled.append(deepcopy(baseline))
                group["hooks"] = unrelated
                reconciled.append(group)
            inserted = True
        else:
            group["hooks"] = unrelated
            if unrelated or set(group) - {"matcher", "hooks"}:
                reconciled.append(group)
    if not inserted:
        reconciled.append(deepcopy(baseline))
    events["PreToolUse"] = reconciled
    return result, baseline

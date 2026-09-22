#!/usr/bin/env python3
"""Tests for the Codex agent routing PreToolUse hook."""

import json
import re
import runpy
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "dotfiles/link/codex/hooks/validate-agent-route.py"
HOOKS_CONFIG = Path(__file__).resolve().parents[2] / "dotfiles/link/codex/hooks.json"
AGENTS_DIRECTORY = Path(__file__).resolve().parents[2] / "dotfiles/link/codex/agents"
MAX_INPUT_BYTES = 1_048_576
KNOWN_TOOL_IDENTITIES = (
    "spawn_agent",
    "Agent",
    "collaborationspawn_agent",
)
UNRELATED_TOOL_IDENTITIES = (
    "unrelated.spawn_agent",
    "foospawn_agent",
    "collaboration.spawn_agents",
)


class CodexRoutingTests(unittest.TestCase):
    def run_hook(self, payload=None, raw=None, cwd=None):
        if raw is None:
            raw = json.dumps(payload, separators=(",", ":"))
        result = subprocess.run(
            ["python3", str(SCRIPT)],
            input=raw.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as error:
            self.fail(f"hook emitted invalid JSON: {result.stdout!r}: {error}")

    @staticmethod
    def event(tool_name="spawn_agent", tool_input=None, **extra):
        event = {
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "tool_input": {} if tool_input is None else tool_input,
        }
        event.update(extra)
        return event

    def assert_allowed(self, payload, tool_name="spawn_agent"):
        self.assertEqual(self.run_hook(self.event(tool_name=tool_name, tool_input=payload)), {})

    def assert_denied(self, payload=None, raw=None, tool_name="spawn_agent"):
        output = self.run_hook(
            self.event(tool_name=tool_name, tool_input=payload) if raw is None else None,
            raw=raw,
        )
        self.assertIsInstance(output, dict)
        specific = output.get("hookSpecificOutput")
        self.assertIsInstance(specific, dict)
        self.assertEqual(specific.get("hookEventName"), "PreToolUse")
        self.assertEqual(specific.get("permissionDecision"), "deny")
        self.assertIsInstance(specific.get("permissionDecisionReason"), str)
        self.assertTrue(specific["permissionDecisionReason"].strip())
        self.assertNotIn("prompt", specific["permissionDecisionReason"].lower())
        self.assertNotIn("contents", specific["permissionDecisionReason"].lower())
        return output

    def test_unrelated_events_and_tools_are_untouched(self):
        self.assertEqual(
            self.run_hook({"hook_event_name": "PostToolUse", "tool_name": "spawn_agent", "tool_input": {}}),
            {},
        )
        for tool_name in (*UNRELATED_TOOL_IDENTITIES, "spawn_agents", "spawn_agent_extra", "Agentic", "agent"):
            self.assertEqual(self.run_hook(self.event(tool_name=tool_name, tool_input={})), {})

    def test_agent_alias_is_handled(self):
        self.assertEqual(self.run_hook(self.event(tool_name="Agent", tool_input={})), self.run_hook(self.event(tool_name="spawn_agent", tool_input={})))

    def test_hook_matcher_matches_only_known_tool_identities(self):
        config = json.loads(HOOKS_CONFIG.read_text())
        matcher = config["hooks"]["PreToolUse"][0]["matcher"]

        for tool_name in KNOWN_TOOL_IDENTITIES:
            with self.subTest(tool_name=tool_name):
                self.assertIsNotNone(re.fullmatch(matcher, tool_name))
        for tool_name in UNRELATED_TOOL_IDENTITIES:
            with self.subTest(tool_name=tool_name):
                self.assertIsNone(re.fullmatch(matcher, tool_name))

    def test_agent_profiles_and_validator_assignments_agree(self):
        profiles = {}
        for profile_path in AGENTS_DIRECTORY.glob("knapsack-*.toml"):
            # These profiles use quoted scalar assignments; avoid requiring Python 3.11's tomllib.
            profile = dict(re.findall(r'^([a-z_]+) = "([^"\n]*)"$', profile_path.read_text(), re.MULTILINE))
            name = profile["name"]
            if name != "knapsack_override":
                profiles[name] = (profile["model"], profile["model_reasoning_effort"])

        validator_profiles = runpy.run_path(str(SCRIPT))["PROFILES"]
        self.assertEqual(profiles, validator_profiles)
        self.assertEqual(
            profiles,
            {
                "knapsack_mechanical": ("gpt-6-luna", "high"),
                "knapsack_ordinary": ("gpt-6-sol", "medium"),
                "knapsack_difficult": ("gpt-6-sol", "medium"),
            },
        )

    def test_known_tool_identities_enforce_routing(self):
        for tool_name in KNOWN_TOOL_IDENTITIES:
            with self.subTest(tool_name=tool_name):
                self.assert_denied({}, tool_name=tool_name)
                self.assert_denied(
                    {
                        "agent_type": "knapsack_mechanical",
                        "fork_context": False,
                        "model": "gpt-5.6-terra",
                        "reasoning_effort": "high",
                    },
                    tool_name=tool_name,
                )
                self.assert_allowed(
                    {
                        "agent_type": "knapsack_mechanical",
                        "fork_context": False,
                        "model": "gpt-6-luna",
                        "reasoning_effort": "high",
                    },
                    tool_name=tool_name,
                )

    def test_unrelated_similar_tool_identities_are_untouched(self):
        for tool_name in UNRELATED_TOOL_IDENTITIES:
            with self.subTest(tool_name=tool_name):
                self.assert_allowed({}, tool_name=tool_name)
                self.assert_allowed(
                    {"agent_type": "knapsack_mechanical", "model": "gpt-5.6-terra"},
                    tool_name=tool_name,
                )

    def test_valid_routes(self):
        self.assert_allowed({"agent_type": "knapsack_mechanical", "fork_turns": "none"})
        self.assert_allowed({"agent_type": "knapsack_mechanical", "fork_context": False, "model": "gpt-6-luna", "reasoning_effort": "high"})
        self.assert_allowed({"agent_type": "knapsack_ordinary", "fork_turns": "2", "model": "gpt-6-sol", "reasoning_effort": "medium"})
        self.assert_allowed({"agent_type": "knapsack_difficult", "fork_turns": "none"})
        self.assert_allowed({"agent_type": "knapsack_difficult", "fork_context": False, "model": "gpt-6-sol", "reasoning_effort": "medium"})
        self.assert_allowed({"agent_type": "knapsack_override", "model": "custom-model", "reasoning_effort": "high", "fork_context": False})
        self.assert_allowed({"agent_type": "knapsack_mechanical", "model": None, "reasoning_effort": None, "fork_context": False})

    def test_pinned_routes_require_fresh_or_partial_context(self):
        for route in ("knapsack_mechanical", "knapsack_ordinary", "knapsack_difficult"):
            for fields in ({}, {"fork_turns": "all"}, {"fork_context": True}, {"fork_turns": "none", "fork_context": False}):
                self.assert_denied({"agent_type": route, **fields})

    def test_previous_pinned_models_are_rejected(self):
        for route, model in (
            ("knapsack_mechanical", "gpt-5.6-luna"),
            ("knapsack_ordinary", "gpt-5.6-terra"),
            ("knapsack_difficult", "gpt-5.6-sol"),
        ):
            self.assert_denied({"agent_type": route, "fork_context": False, "model": model})

    def test_pinned_routes_reject_astra(self):
        for route in ("knapsack_mechanical", "knapsack_ordinary", "knapsack_difficult"):
            self.assert_denied({"agent_type": route, "fork_context": False, "model": "gpt-6-astra"})

    def test_pinned_route_efforts_must_match(self):
        for route, effort in (
            ("knapsack_mechanical", "medium"),
            ("knapsack_ordinary", "high"),
            ("knapsack_difficult", "high"),
        ):
            self.assert_denied({"agent_type": route, "fork_context": False, "reasoning_effort": effort})

    def test_override_requires_explicit_model_and_effort(self):
        self.assert_denied({"agent_type": "knapsack_override", "model": "custom-model", "reasoning_effort": "high"})
        self.assert_denied({"agent_type": "knapsack_override", "fork_context": False})
        self.assert_denied({"agent_type": "knapsack_override", "model": "x", "fork_context": False})
        self.assert_denied({"agent_type": "knapsack_override", "reasoning_effort": "high", "fork_context": False})
        self.assert_denied({"agent_type": "knapsack_override", "model": "", "reasoning_effort": "high", "fork_context": False})

    def test_missing_unknown_and_nonstring_routes_are_denied(self):
        for value in (None, "", "unknown", 1, [], {}):
            payload = {} if value is None else {"agent_type": value}
            self.assert_denied(payload)

    def test_invalid_input_shapes_are_denied(self):
        for raw in ("", "{}", "[]", "null", '"text"', "{malformed"):
            self.assert_denied(raw=raw)
        self.assert_denied(
            raw=json.dumps(
                self.event(tool_input=None), separators=(",", ":")
            )
        )
        for tool_input in ([], "text", 1):
            self.assert_denied(
                raw=json.dumps(
                    self.event(tool_input=tool_input), separators=(",", ":")
                )
            )

    def test_oversized_input_is_denied_without_echoing_contents(self):
        marker = "SECRET_ROUTING_PROMPT"
        raw = "{" + json.dumps(marker + "x" * MAX_INPUT_BYTES) + "}"
        self.assertGreater(len(raw.encode()), MAX_INPUT_BYTES)
        output = self.assert_denied(raw=raw)
        self.assertNotIn(marker, output["hookSpecificOutput"]["permissionDecisionReason"])

        output = self.assert_denied(
            {"agent_type": "unknown", "prompt": marker}
        )
        self.assertNotIn(marker, output["hookSpecificOutput"]["permissionDecisionReason"])

    def test_difficult_never_inherits_the_parent(self):
        self.assert_denied({"agent_type": "knapsack_difficult"})
        self.assert_denied({"agent_type": "knapsack_difficult", "fork_turns": "all"})
        self.assert_allowed(
            {"agent_type": "knapsack_difficult", "fork_turns": "none", "model": None, "reasoning_effort": None}
        )

    def test_script_works_from_cwd_containing_spaces(self):
        payload = {"agent_type": "knapsack_difficult", "fork_turns": "none"}
        with tempfile.TemporaryDirectory(prefix="codex routing cwd ") as cwd:
            self.assert_allowed(payload)
            self.assertEqual(self.run_hook(self.event(tool_input=payload), cwd=cwd), {})


if __name__ == "__main__":
    unittest.main()

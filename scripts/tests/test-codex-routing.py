#!/usr/bin/env python3
"""Tests for the Codex agent routing PreToolUse hook."""

import json
import re
import runpy
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "dotfiles/shared/codex/hooks/validate-agent-route.py"
HOOKS_CONFIG = Path(__file__).resolve().parents[2] / "dotfiles/merge/codex/hooks.json"
AGENTS_DIRECTORY = Path(__file__).resolve().parents[2] / "dotfiles/shared/codex/agents"
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
# The tracked profiles are the roster. Deriving expectations from them keeps
# these tests about the hook's behavior, so a model change never edits a test.
ROUTES = runpy.run_path(str(SCRIPT))["load_routes"]()
PINNED = {name: pin for name, pin in ROUTES.items() if pin is not None}
UNPINNED = [name for name, pin in ROUTES.items() if pin is None]
# A default above high is the costliest lever; it is a retry step, never a pin.
PINNABLE_EFFORTS = ("low", "medium", "high")
FRESH = {"fork_turns": "none"}


class CodexRoutingTests(unittest.TestCase):
    def run_hook(self, payload=None, raw=None, cwd=None, script=SCRIPT):
        if raw is None:
            raw = json.dumps(payload, separators=(",", ":"))
        result = subprocess.run(
            ["python3", "-B", str(script)],
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

    def assert_allowed(self, payload, tool_name="spawn_agent", script=SCRIPT):
        self.assertEqual(
            self.run_hook(self.event(tool_name=tool_name, tool_input=payload), script=script), {},
        )

    def assert_denied(self, payload=None, raw=None, tool_name="spawn_agent", script=SCRIPT):
        output = self.run_hook(
            self.event(tool_name=tool_name, tool_input=payload) if raw is None else None,
            raw=raw,
            script=script,
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

    def install_fixture(self, root, profiles):
        """Install the hook beside fixture profiles, as setup lays it out under ~/.codex."""
        hooks = Path(root) / "hooks"
        hooks.mkdir()
        script = hooks / SCRIPT.name
        shutil.copy2(SCRIPT, script)
        if profiles is not None:
            agents = Path(root) / "agents"
            agents.mkdir()
            for name, body in profiles.items():
                (agents / name).write_text(body)
        return script

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
        entries = [entry for entry in config["hooks"]["PreToolUse"]
                   if any(hook.get("command") == 'python3 "$HOME/.codex/hooks/validate-agent-route.py"'
                          for hook in entry.get("hooks", []))]
        self.assertEqual(len(entries), 1)
        matcher = entries[0]["matcher"]

        for tool_name in KNOWN_TOOL_IDENTITIES:
            with self.subTest(tool_name=tool_name):
                self.assertIsNotNone(re.fullmatch(matcher, tool_name))
        for tool_name in UNRELATED_TOOL_IDENTITIES:
            with self.subTest(tool_name=tool_name):
                self.assertIsNone(re.fullmatch(matcher, tool_name))

    def test_tracked_profiles_form_a_usable_roster(self):
        profiles = sorted(AGENTS_DIRECTORY.glob("*-worker.toml"))
        self.assertEqual(len(profiles), len(ROUTES))
        for profile_path in profiles:
            with self.subTest(profile=profile_path.name):
                profile = dict(re.findall(r'^([a-z_]+) = "([^"\n]*)"$', profile_path.read_text(), re.MULTILINE))
                # Codex resolves a role by name; setup derives the name from the file.
                self.assertEqual(profile.get("name"), profile_path.stem.replace("-", "_"))
                self.assertTrue(profile.get("description"))
                self.assertTrue(profile.get("developer_instructions"))
        self.assertTrue(PINNED)
        self.assertEqual(UNPINNED, ["custom_worker"])
        for route, (model, effort) in PINNED.items():
            with self.subTest(route=route):
                self.assertTrue(model.strip())
                self.assertIn(effort, PINNABLE_EFFORTS)

    def test_known_tool_identities_enforce_routing(self):
        route, (model, effort) = next(iter(PINNED.items()))
        for tool_name in KNOWN_TOOL_IDENTITIES:
            with self.subTest(tool_name=tool_name):
                self.assert_denied({}, tool_name=tool_name)
                self.assert_denied(
                    {"agent_type": route, "fork_context": False, "model": "not-" + model, "reasoning_effort": effort},
                    tool_name=tool_name,
                )
                self.assert_allowed(
                    {"agent_type": route, "fork_context": False, "model": model, "reasoning_effort": effort},
                    tool_name=tool_name,
                )

    def test_unrelated_similar_tool_identities_are_untouched(self):
        route = next(iter(PINNED))
        for tool_name in UNRELATED_TOOL_IDENTITIES:
            with self.subTest(tool_name=tool_name):
                self.assert_allowed({}, tool_name=tool_name)
                self.assert_allowed({"agent_type": route, "model": "another-model"}, tool_name=tool_name)

    def test_pinned_routes_accept_omitted_or_matching_assignments(self):
        for route, (model, effort) in PINNED.items():
            with self.subTest(route=route):
                self.assert_allowed({"agent_type": route, **FRESH})
                self.assert_allowed({"agent_type": route, "fork_context": False})
                self.assert_allowed({"agent_type": route, **FRESH, "model": None, "reasoning_effort": None})
                self.assert_allowed({"agent_type": route, **FRESH, "model": model, "reasoning_effort": effort})
                self.assert_allowed({"agent_type": route, **FRESH, "model": model})
                self.assert_allowed({"agent_type": route, **FRESH, "reasoning_effort": effort})

    def test_pinned_routes_reject_every_other_roster_model(self):
        models = {model for model, _ in PINNED.values()}
        for route, (model, _) in PINNED.items():
            for other in (models - {model}) | {"not-" + model}:
                with self.subTest(route=route, model=other):
                    self.assert_denied({"agent_type": route, **FRESH, "model": other})

    def test_pinned_routes_reject_every_other_effort(self):
        for route, (_, effort) in PINNED.items():
            for other in ("low", "medium", "high", "xhigh", "max", "ultra"):
                if other != effort:
                    with self.subTest(route=route, effort=other):
                        self.assert_denied({"agent_type": route, **FRESH, "reasoning_effort": other})

    def test_every_route_requires_fresh_context(self):
        for route in ROUTES:
            assignment = {} if route in PINNED else {"model": "custom-model", "reasoning_effort": "high"}
            # Codex 0.169 runs a legacy turn count as a full-history fork.
            for fields in ({}, {"fork_turns": "all"}, {"fork_turns": "2"}, {"fork_context": True},
                           {"fork_turns": "none", "fork_context": False}):
                with self.subTest(route=route, fields=fields):
                    self.assert_denied({"agent_type": route, **assignment, **fields})

    def test_override_requires_explicit_model_and_effort(self):
        for route in UNPINNED:
            with self.subTest(route=route):
                self.assert_allowed({"agent_type": route, "model": "custom-model", "reasoning_effort": "high", "fork_context": False})
                self.assert_allowed({"agent_type": route, "model": "custom-model", "reasoning_effort": "high", **FRESH})
                self.assert_denied({"agent_type": route, "model": "custom-model", "reasoning_effort": "high"})
                self.assert_denied({"agent_type": route, "fork_context": False})
                self.assert_denied({"agent_type": route, "model": "x", "fork_context": False})
                self.assert_denied({"agent_type": route, "reasoning_effort": "high", "fork_context": False})
                self.assert_denied({"agent_type": route, "model": "", "reasoning_effort": "high", "fork_context": False})

    def test_missing_unknown_and_nonstring_routes_are_denied(self):
        for value in (None, "", "unknown", 1, [], {}):
            payload = {} if value is None else {"agent_type": value}
            self.assert_denied(payload)

    def test_missing_route_reason_lists_every_route_with_its_pin(self):
        reason = self.assert_denied({})["hookSpecificOutput"]["permissionDecisionReason"]
        for route, (model, effort) in PINNED.items():
            self.assertIn(f"{route} ({model} {effort})", reason)
        for route in UNPINNED:
            self.assertIn(f"{route} (explicit model and effort)", reason)

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

    def test_script_works_from_cwd_containing_spaces(self):
        payload = {"agent_type": next(iter(PINNED)), **FRESH}
        with tempfile.TemporaryDirectory(prefix="codex routing cwd ") as cwd:
            self.assert_allowed(payload)
            self.assertEqual(self.run_hook(self.event(tool_input=payload), cwd=cwd), {})

    def test_installed_hook_reads_the_profiles_beside_it(self):
        profiles = {
            "alpha-worker.toml": 'name = "alpha_worker"\nmodel = "model-a"\nmodel_reasoning_effort = "low"\n',
            "open-worker.toml": 'name = "open_worker"\n',
            "local.toml": 'name = "local_role"\nmodel = "model-z"\nmodel_reasoning_effort = "max"\n',
        }
        with tempfile.TemporaryDirectory() as root:
            script = self.install_fixture(root, profiles)
            self.assert_allowed({"agent_type": "alpha_worker", **FRESH, "model": "model-a", "reasoning_effort": "low"}, script=script)
            self.assert_denied({"agent_type": "alpha_worker", **FRESH, "model": "model-b"}, script=script)
            self.assert_allowed({"agent_type": "open_worker", **FRESH, "model": "model-b", "reasoning_effort": "high"}, script=script)
            # Only Knapsack's own profiles are routes; the tracked roster is not consulted.
            for route in ("local_role", *ROUTES):
                self.assert_denied({"agent_type": route, **FRESH}, script=script)

    def test_unreadable_profiles_deny_spawns_and_leave_other_tools_alone(self):
        fixtures = (
            None,
            {},
            {"half-worker.toml": 'name = "half_worker"\nmodel = "model-a"\n'},
            {"nameless-worker.toml": 'model = "model-a"\nmodel_reasoning_effort = "low"\n'},
            # Codex accepts these spellings, so skipping them would quietly unpin the route.
            {"half-worker.toml": 'name = "half_worker"\nmodel = "model-a"  # note\nmodel_reasoning_effort = "low"  # note\n'},
            {"half-worker.toml": "name = \"half_worker\"\nmodel = 'model-a'\nmodel_reasoning_effort = 'low'\n"},
            {"half-worker.toml": 'name = "half_worker"\nmodel="model-a"\nmodel_reasoning_effort="low"\n'},
            {
                "one-worker.toml": 'name = "same_worker"\n',
                "two-worker.toml": 'name = "same_worker"\n',
            },
        )
        for profiles in fixtures:
            with self.subTest(profiles=profiles), tempfile.TemporaryDirectory() as root:
                script = self.install_fixture(root, profiles)
                output = self.assert_denied({"agent_type": "half_worker", **FRESH}, script=script)
                self.assertIn("route profiles", output["hookSpecificOutput"]["permissionDecisionReason"])
                self.assertEqual(self.run_hook(self.event(tool_name="shell", tool_input={}), script=script), {})


if __name__ == "__main__":
    unittest.main()

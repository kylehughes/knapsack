#!/usr/bin/env python3
"""Tests that every documented roster agrees with the tracked route profiles."""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLAUDE_AGENTS = ROOT / "dotfiles/shared/claude/agents"
CODEX_AGENTS = ROOT / "dotfiles/shared/codex/agents"
POLICY = ROOT / "dotfiles/shared/claude/CLAUDE.md"
ROUTING_GUIDE = ROOT / "docs/agent-routing.md"
README = ROOT / "README.md"
# A roster cell names a route, then its model and effort: `route` — `model`, `effort`.
# The README puts the route in its own column, so a cell border may separate them.
ROSTER_CELL = re.compile(r"`([a-z]+[-_]worker)`\s*(?:—|\|)\s*`([^`]+)`,\s*`([^`]+)`")
# A default above high is the costliest lever; it is a retry step, never a pin.
PINNABLE_EFFORTS = ("low", "medium", "high")


def claude_routes():
    """Return {route: (model, effort)} from the Claude Code agent frontmatter."""
    routes = {}
    for path in sorted(CLAUDE_AGENTS.glob("*-worker.md")):
        frontmatter = path.read_text().split("---\n")[1]
        fields = dict(re.findall(r"^([A-Za-z]+): (.+)$", frontmatter, re.MULTILINE))
        routes[fields["name"]] = (fields.get("model"), fields.get("effort"))
    return routes


def codex_routes():
    """Return {route: (model, effort)} for the Codex roles that pin both."""
    routes = {}
    for path in sorted(CODEX_AGENTS.glob("*-worker.toml")):
        fields = dict(re.findall(r'^([a-z_]+) = "([^"\n]*)"$', path.read_text(), re.MULTILINE))
        if "model" in fields:
            routes[fields["name"]] = (fields["model"], fields["model_reasoning_effort"])
    return routes


def documented(path):
    """Return every (route, model, effort) a document's roster tables state."""
    return ROSTER_CELL.findall(path.read_text())


class AgentRosterTests(unittest.TestCase):
    def setUp(self):
        self.claude = claude_routes()
        self.codex = codex_routes()
        self.pins = {**self.claude, **self.codex}

    def test_claude_agents_pin_a_model_and_a_default_effort(self):
        self.assertTrue(self.claude)
        for path in sorted(CLAUDE_AGENTS.glob("*-worker.md")):
            with self.subTest(agent=path.name):
                self.assertIn(path.stem, self.claude)
                model, effort = self.claude[path.stem]
                self.assertTrue(model)
                self.assertIn(effort, PINNABLE_EFFORTS)

    def test_both_harnesses_route_the_same_classes(self):
        claude = {name[:-len("-worker")] for name in self.claude}
        codex = {name[:-len("_worker")] for name in self.codex}
        self.assertEqual(claude, codex)

    def test_documented_rosters_match_the_profiles(self):
        for document in (POLICY, ROUTING_GUIDE, README):
            cells = documented(document)
            self.assertTrue(cells, f"{document.name} states no roster")
            for route, model, effort in cells:
                with self.subTest(document=document.name, route=route):
                    self.assertIn(route, self.pins)
                    self.assertEqual((model, effort), self.pins[route])

    def test_policy_and_guide_list_every_route(self):
        for document in (POLICY, ROUTING_GUIDE):
            with self.subTest(document=document.name):
                self.assertEqual({route for route, _, _ in documented(document)}, set(self.pins))

    def test_readme_lists_every_route(self):
        listed = {route for route, _, _ in documented(README)}
        self.assertLessEqual(set(self.pins), listed)

    def test_claude_descriptions_name_the_pinned_effort(self):
        for path in sorted(CLAUDE_AGENTS.glob("*-worker.md")):
            with self.subTest(agent=path.name):
                description = re.search(r"^description: (.+)$", path.read_text(), re.MULTILINE).group(1)
                self.assertIn(f"{self.claude[path.stem][1]} effort)", description)

    def test_orca_examples_show_the_difficult_pairing(self):
        policy = POLICY.read_text()
        for agent, route in (("claude", self.claude["difficult-worker"]), ("codex", self.codex["difficult_worker"])):
            with self.subTest(agent=agent):
                model, effort = route
                self.assertIn(f"--agent {agent} --model {model} --effort {effort} ", policy)


if __name__ == "__main__":
    unittest.main()

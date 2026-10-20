#!/usr/bin/env python3
"""Exercise pure configuration composition without touching runtime files."""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "dotfile_composition", ROOT / "scripts/lib/dotfile_composition.py",
)
COMPOSITION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMPOSITION)
DESIRED = json.loads((ROOT / "dotfiles/merge/codex/hooks.json").read_text())
GROUP = DESIRED["hooks"]["PreToolUse"][0]
LOCAL = {"type": "command", "command": "local-tool", "timeout": 12}


class ClaudeCompositionTests(unittest.TestCase):
    def test_recursive_objects_and_replaced_arrays(self):
        base = {
            "permissions": {"allow": ["Read", "Write"], "other": True},
            "enabledPlugins": {"first": True, "second": True},
            "unknown": {"nested": [1, 2]},
        }
        overlay = {
            "permissions": {"allow": ["Agent"]},
            "enabledPlugins": {"first": False},
            "unknown": {"nested": []},
        }
        originals = deepcopy((base, overlay))
        result = COMPOSITION.compose_claude_settings(base, overlay)
        self.assertEqual(result, {
            "permissions": {"allow": ["Agent"], "other": True},
            "enabledPlugins": {"first": False, "second": True},
            "unknown": {"nested": []},
        })
        result["permissions"]["allow"].append("Edit")
        self.assertEqual((base, overlay), originals)

    def test_leaf_types_can_be_replaced(self):
        self.assertEqual(COMPOSITION.compose_claude_settings(
            {"future": {"a": 1}, "other": 1},
            {"future": None, "other": {"b": 2}},
        ), {"future": None, "other": {"b": 2}})

    def test_invalid_object_and_plugin_fields_rejected_in_both_inputs(self):
        for invalid in ([], None, {"enabledPlugins": []}, {"extraKnownMarketplaces": None}):
            for base, overlay in ((invalid, {}), ({}, invalid)):
                with self.subTest(base=base, overlay=overlay):
                    with self.assertRaises(COMPOSITION.CompositionError):
                        COMPOSITION.compose_claude_settings(base, overlay)


class CodexCompositionTests(unittest.TestCase):
    def reconcile(self, existing, desired=None, previous=None):
        originals = deepcopy((existing, DESIRED if desired is None else desired, previous))
        result = COMPOSITION.reconcile_codex_hooks(*originals)
        self.assertEqual((existing, DESIRED if desired is None else desired, previous), originals)
        return result

    def test_empty_configuration_receives_only_owned_group(self):
        result, baseline = self.reconcile({})
        self.assertEqual(result, {"hooks": {"PreToolUse": [GROUP]}})
        self.assertEqual(baseline, GROUP)
        baseline["hooks"][0]["timeout"] = 100
        self.assertEqual(result["hooks"]["PreToolUse"], [GROUP])

    def test_unrelated_events_order_and_metadata_survive(self):
        mixed = deepcopy(GROUP)
        mixed["future"] = {"keep": True}
        mixed["hooks"] = [deepcopy(LOCAL), deepcopy(GROUP["hooks"][0]),
                          {"type": "future-handler", "payload": [1, 2]}]
        existing = {
            "description": "Local description",
            "future": {"mode": True},
            "hooks": {
                "Stop": [{"hooks": [deepcopy(LOCAL)], "future": 1}],
                "PreToolUse": [{"matcher": "other", "hooks": [deepcopy(LOCAL)]}, mixed],
            },
        }
        result, _ = self.reconcile(existing)
        self.assertEqual(result, existing)

    def test_duplicates_collapse_with_local_handlers_in_place(self):
        mixed = deepcopy(GROUP)
        mixed["hooks"] = [deepcopy(LOCAL), deepcopy(GROUP["hooks"][0]),
                          deepcopy(GROUP["hooks"][0]), {"type": "prompt", "prompt": "keep"}]
        metadata_duplicate = deepcopy(GROUP)
        metadata_duplicate["future"] = True
        result, _ = self.reconcile({"hooks": {"PreToolUse": [
            mixed, deepcopy(GROUP), metadata_duplicate,
        ]}})
        self.assertEqual(result["hooks"]["PreToolUse"], [
            {"matcher": GROUP["matcher"], "hooks": [
                LOCAL, GROUP["hooks"][0], {"type": "prompt", "prompt": "keep"},
            ]},
            {"matcher": GROUP["matcher"], "hooks": [], "future": True},
        ])

    def test_changed_owned_handler_or_matcher_conflicts(self):
        changes = [
            {"timeout": 99}, {"type": "prompt"}, {"future": "local edit"},
        ]
        for change in changes:
            group = deepcopy(GROUP)
            group["hooks"][0].update(change)
            with self.subTest(change=change), self.assertRaises(COMPOSITION.CompositionError):
                self.reconcile({"hooks": {"PreToolUse": [group]}})
        group = deepcopy(GROUP)
        group["matcher"] = "local matcher"
        with self.assertRaises(COMPOSITION.CompositionError):
            self.reconcile({"hooks": {"PreToolUse": [group]}})

    def test_owned_command_in_other_event_conflicts(self):
        with self.assertRaises(COMPOSITION.CompositionError):
            self.reconcile({"hooks": {"Stop": [deepcopy(GROUP)]}})

    def test_similar_command_is_unrelated(self):
        group = deepcopy(GROUP)
        group["hooks"][0]["command"] += " --local"
        result, _ = self.reconcile({"hooks": {"PreToolUse": [group]}})
        self.assertEqual(result["hooks"]["PreToolUse"], [group, GROUP])

    def test_previous_baseline_allows_owned_updates(self):
        desired = deepcopy(DESIRED)
        desired["hooks"]["PreToolUse"][0]["hooks"][0]["timeout"] = 4
        with self.assertRaises(COMPOSITION.CompositionError):
            self.reconcile({"hooks": {"PreToolUse": [GROUP]}}, desired)
        result, baseline = self.reconcile(
            {"hooks": {"PreToolUse": [GROUP]}}, desired, GROUP,
        )
        self.assertEqual(result["hooks"]["PreToolUse"], desired["hooks"]["PreToolUse"])
        self.assertEqual(baseline, desired["hooks"]["PreToolUse"][0])
        self.assertEqual(self.reconcile(result, desired, baseline)[0], result)

    def test_previous_command_and_matcher_update_preserves_mixed_group(self):
        old = deepcopy(GROUP)
        old["hooks"][0]["command"] = "old-routing-command"
        old["matcher"] = "old matcher"
        mixed = deepcopy(old)
        mixed["hooks"].append(deepcopy(LOCAL))
        mixed["future"] = True
        result, _ = self.reconcile({"hooks": {"PreToolUse": [mixed]}}, previous=old)
        self.assertEqual(result["hooks"]["PreToolUse"], [GROUP, {
            "matcher": "old matcher", "hooks": [LOCAL], "future": True,
        }])

    def test_invalid_hook_shapes_fail_without_mutation(self):
        malformed = [
            [], {"hooks": []}, {"hooks": {"Stop": {}}},
            {"hooks": {"Stop": [None]}},
            {"hooks": {"Stop": [{"hooks": {}}]}},
            {"hooks": {"Stop": [{"matcher": 1, "hooks": []}]}},
            {"hooks": {"Stop": [{"hooks": [None]}]}},
            {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": []}]}]}},
            {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "x", "timeout": True}]}]}},
        ]
        for value in malformed:
            original = deepcopy(value)
            with self.subTest(value=value), self.assertRaises(COMPOSITION.CompositionError):
                COMPOSITION.reconcile_codex_hooks(value, DESIRED)
            self.assertEqual(value, original)

    def test_invalid_desired_and_previous_definitions_rejected(self):
        for desired in ({}, {"hooks": {"PreToolUse": []}}, {"hooks": {
            "PreToolUse": [GROUP], "Stop": [],
        }}):
            with self.subTest(desired=desired), self.assertRaises(COMPOSITION.CompositionError):
                self.reconcile({}, desired)
        with self.assertRaises(COMPOSITION.CompositionError):
            self.reconcile({}, previous={"matcher": "x", "hooks": []})


if __name__ == "__main__":
    unittest.main()

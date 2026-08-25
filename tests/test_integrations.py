#!/usr/bin/env python3
"""Tests for the multi-agent integrations (Codex hooks + Hermes plugin + core).

Pure stdlib, no pytest. Run:
    python tests/test_integrations.py
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INTEGRATIONS = ROOT / "integrations"
CODEX_HARNESS = INTEGRATIONS / "codex" / "writing-harness-gate.py"
CODEX_TIER = INTEGRATIONS / "codex" / "output-tier-gate.py"
HERMES_PLUGIN = INTEGRATIONS / "hermes" / "writing_harness_plugin.py"
PY = sys.executable
REWRITE_DIFF = ROOT / "scripts" / "rewrite-diff.py"

sys.path.insert(0, str(INTEGRATIONS))
import harness_core as core  # noqa: E402
from itoguchi import packet_contract as contract  # noqa: E402


def itoguchi_packet():
    return {
        "contract": "itoguchi.scene-evidence/v1",
        "story_revision": "sha256:" + "a" * 64,
        "query": {
            "holder": "陳永仁",
            "resolved_holder": "陳永仁",
            "as_of": 18,
            "about": "韓琛",
            "persona": "古惑仔",
        },
        "authored_evidence": [
            {
                "id": "a1",
                "kind": "belief",
                "value": "開始懷疑我的人",
                "availability": "character",
                "source": {
                    "path": "chen_wing_yan.md",
                    "pointer": "/beliefs/1/content",
                },
            },
            {
                "id": "a2",
                "kind": "belief",
                "value": "陳永仁是警方臥底",
                "availability": "writer-only",
                "source": {
                    "path": "hon_sam.md",
                    "pointer": "/beliefs/0/content",
                },
            },
        ],
        "derived_context": [
            {
                "id": "d1",
                "kind": "tension",
                "summary": "正在維持謊言",
                "availability": "writer-only",
                "basis": ["a1"],
            }
        ],
        "voice_constraints": [
            {
                "id": "v1",
                "text": "對韓琛說話時避免完整交代動機",
                "persona": "古惑仔",
                "toward": "韓琛",
                "since": 1,
                "until": None,
                "conflicts_with": [],
                "source": {
                    "path": "chen_wing_yan.md",
                    "pointer": "/voice_constraints/0/text",
                },
            }
        ],
        "warnings": [],
    }


def md_under(dirname, text="這是一段需要過三站的中文長文，先放著。\n"):
    """Create a real .md file under a temp dir whose path contains `dirname`."""
    base = Path(tempfile.mkdtemp()) / dirname
    base.mkdir(parents=True, exist_ok=True)
    f = base / "post.md"
    f.write_text(text, encoding="utf-8")
    return f


class CoreLogic(unittest.TestCase):
    def test_extract_apply_patch_paths(self):
        patch = (
            "*** Begin Patch\n"
            "*** Add File: content/new-post.md\n"
            "+hello\n"
            "*** Update File: articles/old.md\n"
            "*** Move to: posts/moved.md\n"
            "*** End Patch\n"
        )
        paths = core.extract_paths_from_text(patch)
        self.assertEqual(
            paths, ["content/new-post.md", "articles/old.md", "posts/moved.md"]
        )

    def test_collect_from_codex_tool_input(self):
        tool_input = {"input": "*** Update File: content/a.md\n@@\n-x\n+y\n"}
        self.assertIn("content/a.md", core.collect_candidate_paths(tool_input))

    def test_collect_from_direct_path_key(self):
        self.assertIn("content/b.md", core.collect_candidate_paths({"file_path": "content/b.md"}))

    def test_harness_reminder_fires_on_included(self):
        self.assertIsNotNone(core.harness_reminder("content/x.md", "純內文，沒有留證標記"))

    def test_harness_reminder_skips_excluded(self):
        self.assertIsNone(core.harness_reminder("content/drafts/x.md", "內文"))

    def test_harness_reminder_skips_signed_off(self):
        self.assertIsNone(
            core.harness_reminder("content/x.md", "內文\n<!-- writing-harness: S0/S1/S2 ok 2026-06-04 -->\n")
        )

    def test_harness_reminder_skips_skeleton(self):
        self.assertIsNone(core.harness_reminder("content/x.md", "status: draft-skeleton\n內文"))

    def test_harness_reminder_skips_non_md(self):
        self.assertIsNone(core.harness_reminder("content/x.txt", "內文"))

    def test_tier_reminder_fires_on_client_path(self):
        self.assertIsNotNone(core.tier_reminder("clients/acme/proposal.md"))

    def test_tier_reminder_skips_internal_subpath(self):
        self.assertIsNone(core.tier_reminder("clients/acme/intake/notes.md"))


class CodexAdapter(unittest.TestCase):
    def _run(self, script, payload):
        return subprocess.run(
            [PY, str(script)],
            input=json.dumps(payload),
            capture_output=True, text=True, encoding="utf-8",
        )

    def test_codex_harness_emits_system_message(self):
        f = md_under("content")
        payload = {
            "hook_event_name": "PostToolUse",
            "tool_name": "apply_patch",
            "tool_input": {"input": f"*** Update File: {f}\n@@\n+x\n"},
            "tool_response": {},
        }
        r = self._run(CODEX_HARNESS, payload)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertIn("systemMessage", out)
        self.assertIn("寫作 Harness", out["systemMessage"])

    def test_codex_harness_silent_when_signed_off(self):
        f = md_under("content", "內文\n<!-- writing-harness: S0/S1/S2 ok 2026-06-04 -->\n")
        payload = {
            "hook_event_name": "PostToolUse",
            "tool_input": {"input": f"*** Update File: {f}\n"},
        }
        r = self._run(CODEX_HARNESS, payload)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "")

    def test_codex_tier_emits_on_client_path(self):
        f = md_under("clients")
        payload = {
            "hook_event_name": "PostToolUse",
            "tool_input": {"input": f"*** Add File: {f}\n+x\n"},
        }
        r = self._run(CODEX_TIER, payload)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertIn("L3", out["systemMessage"])

    def test_direct_user_facing_clis_are_safe_under_cp932(self):
        env = {**os.environ, "PYTHONIOENCODING": "cp932"}
        harness_file = md_under("content")
        client_file = md_under("clients")
        payloads = (
            (CODEX_HARNESS, {"hook_event_name": "PostToolUse", "tool_input": {"file_path": str(harness_file)}}),
            (CODEX_TIER, {"hook_event_name": "PostToolUse", "tool_input": {"file_path": str(client_file)}}),
        )
        for script, payload in payloads:
            with self.subTest(script=script.name):
                result = subprocess.run(
                    [PY, str(script)], input=json.dumps(payload).encode(),
                    capture_output=True, env=env,
                )
                self.assertEqual(result.returncode, 0, result.stderr.decode("ascii", errors="ignore"))
                self.assertNotIn(b"UnicodeEncodeError", result.stderr)

        draft = md_under("draft", "**小結：** 舊稿。\n")
        final = md_under("final", "新版。\n")
        result = subprocess.run(
            [PY, str(REWRITE_DIFF), str(draft), str(final)], capture_output=True, env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("ascii", errors="ignore"))
        self.assertNotIn(b"UnicodeEncodeError", result.stderr)


class HermesPlugin(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("writing_harness_plugin", HERMES_PLUGIN)
        self.plugin = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.plugin)
        self.plugin._pending.clear()

    def test_register_wires_both_hooks(self):
        registered = {}

        class Ctx:
            def register_hook(self, name, fn):
                registered[name] = fn

        self.plugin.register(Ctx())
        self.assertIn("post_tool_call", registered)
        self.assertIn("pre_llm_call", registered)

    def test_observe_then_inject(self):
        f = md_under("content")
        # post_tool_call observes the write (Hermes calls hooks by keyword)
        self.plugin._on_post_tool(
            tool_name="write_file",
            args={"path": str(f)},
            result=f"wrote {f}",
            task_id="t1",
            duration_ms=3,
        )
        injected = self.plugin._inject_pending(messages=[])
        self.assertIsNotNone(injected)
        self.assertIn("writing-harness", injected["context"])
        # queue drained — next turn injects nothing
        self.assertIsNone(self.plugin._inject_pending())


class ItoguchiPacketContract(unittest.TestCase):
    def test_itoguchi_packet_accepts_v1_and_rejects_unsafe_items(self):
        contract.validate_packet(itoguchi_packet())
        for mutation in (
            lambda p: p.update(contract="itoguchi.scene-evidence/v2"),
            lambda p: p.pop("story_revision"),
            lambda p: p.update(story_revision="sha256:not-a-revision"),
            lambda p: p["authored_evidence"][0].pop("source"),
            lambda p: p["authored_evidence"][0]["source"].update(
                path="C:/stories/chen_wing_yan.md"
            ),
            lambda p: p["authored_evidence"][0]["source"].update(
                path="../chen_wing_yan.md"
            ),
            lambda p: p["authored_evidence"][0]["source"].pop("pointer"),
            lambda p: p["authored_evidence"][0].update(availability="reader"),
            lambda p: p["derived_context"][0].update(id="a1"),
            lambda p: p["derived_context"][0].update(basis=[]),
            lambda p: p["derived_context"][0].update(basis=["missing"]),
            lambda p: p["voice_constraints"][0].update(conflicts_with="v2"),
            lambda p: p.update(warnings="voice_constraints_missing"),
            lambda p: p.update(unexpected=True),
        ):
            with self.subTest(mutation=mutation):
                bad = itoguchi_packet()
                mutation(bad)
                with self.assertRaises(contract.PacketContractError):
                    contract.validate_packet(bad)

    def test_packet_rejects_wrong_structure_types(self):
        for mutation in (
            lambda p: p.update(query=[]),
            lambda p: p["query"].update(as_of=True),
            lambda p: p.update(authored_evidence={}),
            lambda p: p["authored_evidence"][0].update(value=""),
            lambda p: p["derived_context"][0].update(availability="character"),
            lambda p: p["voice_constraints"][0].update(text=""),
            lambda p: p["voice_constraints"][0].update(since="1"),
            lambda p: p.update(warnings=[1]),
        ):
            with self.subTest(mutation=mutation):
                bad = itoguchi_packet()
                mutation(bad)
                with self.assertRaises(contract.PacketContractError):
                    contract.validate_packet(bad)

    def test_expected_revision_must_match(self):
        with self.assertRaises(contract.PacketContractError):
            contract.validate_packet(
                itoguchi_packet(), expected_revision="sha256:" + "b" * 64
            )

    def test_protected_selection_uses_only_present_authored_literals(self):
        selected = contract.select_protected_items(
            itoguchi_packet(), "原稿保留：開始懷疑我的人。開始懷疑我的人。", ["a1"]
        )
        self.assertEqual(selected, [{"value": "開始懷疑我的人", "count": 2}])
        with self.assertRaises(contract.PacketContractError):
            contract.select_protected_items(itoguchi_packet(), "原稿", ["d1"])
        with self.assertRaises(contract.PacketContractError):
            contract.select_protected_items(itoguchi_packet(), "原稿", ["a1"])

    def test_voice_constraint_passes_through_exact_text(self):
        text = "對韓琛說話時避免完整交代動機"
        self.assertEqual(
            contract.select_protected_items(itoguchi_packet(), text, ["v1"]),
            [{"value": text, "count": 1}],
        )

    def test_character_availability_rejects_writer_only_and_derived_ids(self):
        contract.require_character_available(itoguchi_packet(), ["a1"])
        for item_id in ("a2", "d1", "v1"):
            with self.subTest(item_id=item_id):
                with self.assertRaises(contract.PacketContractError):
                    contract.require_character_available(
                        itoguchi_packet(), [item_id]
                    )

    def test_declared_active_voice_conflict_is_rejected(self):
        packet = itoguchi_packet()
        packet["voice_constraints"].append(
            {
                "id": "v2",
                "text": "對韓琛說話時完整交代動機",
                "conflicts_with": [],
                "source": {
                    "path": "chen_wing_yan.md",
                    "pointer": "/voice_constraints/1/text",
                },
            }
        )
        packet["voice_constraints"][0]["conflicts_with"] = ["v2"]
        with self.assertRaises(contract.PacketContractError):
            contract.validate_packet(packet)

    def test_voice_status_requires_constraints_for_new_dialogue(self):
        self.assertEqual(
            contract.voice_status(itoguchi_packet(), writing_new_dialogue=True),
            "voice fidelity: verified against supplied constraints",
        )
        packet = itoguchi_packet()
        packet["voice_constraints"] = []
        with self.assertRaises(contract.PacketContractError):
            contract.voice_status(packet, writing_new_dialogue=True)
        self.assertEqual(
            contract.voice_status(packet, writing_new_dialogue=False),
            "voice fidelity: unverified",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

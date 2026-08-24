#!/usr/bin/env python3
"""Smoke tests for the writing-harness checkers. Pure stdlib, no pytest needed.

Run:
    python tests/test_harness.py
Exit 0 = all pass, 1 = a test failed.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLE = ROOT / "scripts" / "taiwan-style-check.py"
VERBOSITY = ROOT / "scripts" / "verbosity-check.py"
PROTECTED = ROOT / "scripts" / "protected-material-check.py"
BLOATED = ROOT / "examples" / "bloated-sample.md"
CLEAN = ROOT / "examples" / "clean-sample.md"
PY = sys.executable


def run(script, *args):
    return subprocess.run(
        [PY, "-X", "utf8", str(script), *map(str, args)],
        capture_output=True, text=True, encoding="utf-8",
    )


def write_tmp(text):
    fd = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
    fd.write(text)
    fd.close()
    return Path(fd.name)


def write_manifest(items):
    return write_tmp(json.dumps({"items": items}, ensure_ascii=False))


class TaiwanStyleCheck(unittest.TestCase):
    def test_unknown_flag_fails_clearly(self):
        p = write_tmp("這是一段乾淨的繁體中文。\n")
        try:
            r = run(STYLE, p, "--publci")
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("--publci", r.stderr)
        finally:
            p.unlink(missing_ok=True)

    def test_public_mode_allows_ordinary_trust_and_safety_language(self):
        p = write_tmp("這個流程讓家屬比較有安全感，也建立對團隊的信任感。\n")
        try:
            r = run(STYLE, p, "--public")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        finally:
            p.unlink(missing_ok=True)

    def test_public_mode_allows_plain_comparison_idioms(self):
        p = write_tmp("這兩個方案大同小異，成本不外乎人力和時間。\n")
        try:
            r = run(STYLE, p, "--public")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        finally:
            p.unlink(missing_ok=True)

    def test_context_dependent_terms_stay_human_judgment(self):
        cases = (
            ("這個物體的質量是五公斤。\n", ()),
            ("閉環控制會回傳感測值。\n", ()),
            ("日誌保留每筆事件的顆粒度。\n", ()),
            ("樹脂固化後才能脫模。\n", ("--public",)),
        )
        for text, flags in cases:
            with self.subTest(text=text):
                p = write_tmp(text)
                try:
                    self.assertEqual(run(STYLE, p, *flags).returncode, 0)
                finally:
                    p.unlink(missing_ok=True)

    def test_mainland_terms_have_paired_flag_and_allow_cases(self):
        cases = (
            ("視頻", "影片"), ("視頻號", "短影音帳號"), ("公眾號", "粉專"),
            ("在線", "線上"), ("網絡", "網路"), ("互聯網", "網路"),
            ("批量", "批次"), ("軟件", "軟體"), ("信息", "資訊"),
            ("默認", "預設"), ("鏈接", "連結"), ("範式轉換", "典範轉移"),
            ("屏幕", "螢幕"), ("硬盤", "硬碟"), ("硬件", "硬體"),
            ("服務器", "伺服器"), ("登錄", "登入"), ("操作系統", "作業系統"),
            ("數碼", "數位"), ("攝像頭", "視訊鏡頭"), ("賦能", "強化能力"),
            ("復盤", "事後回顧"), ("對標", "對照"), ("抓手", "切入點"),
        )
        for blocked, allowed in cases:
            with self.subTest(term=blocked, direction="flag"):
                p = write_tmp(f"這次使用{blocked}。\n")
                try:
                    self.assertEqual(run(STYLE, p).returncode, 10)
                finally:
                    p.unlink(missing_ok=True)
            with self.subTest(term=blocked, direction="allow"):
                p = write_tmp(f"這次使用{allowed}。\n")
                try:
                    self.assertEqual(run(STYLE, p).returncode, 0)
                finally:
                    p.unlink(missing_ok=True)

    def test_public_jargon_has_paired_flag_and_allow_cases(self):
        cases = (
            ("這條規則機械可檢。\n", "這條規則電腦抓得到。\n"),
            ("這是 false positive。\n", "這是誤報。\n"),
            ("請 verbatim 保留。\n", "請完整保留原話。\n"),
        )
        for blocked, allowed in cases:
            with self.subTest(text=blocked, direction="flag"):
                p = write_tmp(blocked)
                try:
                    self.assertEqual(run(STYLE, p, "--public").returncode, 10)
                finally:
                    p.unlink(missing_ok=True)
            with self.subTest(text=blocked, direction="allow"):
                p = write_tmp(allowed)
                try:
                    self.assertEqual(run(STYLE, p, "--public").returncode, 0)
                finally:
                    p.unlink(missing_ok=True)

    def test_contrast_regex_has_flag_and_allow_boundaries(self):
        flagged = write_tmp("不是甲，是乙。\n不是丙，而是丁。\n不是戊，是己。\n")
        allowed = write_tmp("不是甲，是乙。\n不是丙，而是丁。\n")
        try:
            self.assertEqual(run(STYLE, flagged).returncode, 10)
            self.assertEqual(run(STYLE, allowed).returncode, 0)
        finally:
            flagged.unlink(missing_ok=True)
            allowed.unlink(missing_ok=True)

    def test_client_message_semicolon_is_scoped_by_frontmatter(self):
        flagged = write_tmp("---\naudience: external\ntype: client-message\n---\n先確認需求；再回覆。\n")
        allowed = write_tmp("---\naudience: external\ntype: article\n---\n先確認需求；再回覆。\n")
        try:
            self.assertEqual(run(STYLE, flagged).returncode, 10)
            self.assertEqual(run(STYLE, allowed).returncode, 0)
        finally:
            flagged.unlink(missing_ok=True)
            allowed.unlink(missing_ok=True)

    def test_clean_passes(self):
        p = write_tmp("這是一段乾淨的繁體中文，沒有違規。\n收尾就停。\n")
        try:
            r = run(STYLE, p)
            self.assertEqual(r.returncode, 0, r.stdout)
        finally:
            p.unlink(missing_ok=True)

    def test_em_dash_fails(self):
        p = write_tmp("這裡用了破折號——這就違規了。\n")
        try:
            r = run(STYLE, p)
            self.assertEqual(r.returncode, 10, r.stdout)
        finally:
            p.unlink(missing_ok=True)

    def test_halfwidth_punct_fails(self):
        p = write_tmp("中文句子裡夾了半形逗號,這樣不行。\n")
        try:
            r = run(STYLE, p)
            self.assertEqual(r.returncode, 10, r.stdout)
        finally:
            p.unlink(missing_ok=True)

    def test_mainland_word_fails(self):
        p = write_tmp("我們要處理這些數據和信息。\n")
        try:
            r = run(STYLE, p)
            self.assertEqual(r.returncode, 10, r.stdout)
        finally:
            p.unlink(missing_ok=True)

    def test_noise_frame_fails(self):
        p = write_tmp("其實這件事很簡單。\n")
        try:
            r = run(STYLE, p)
            self.assertEqual(r.returncode, 10, r.stdout)
        finally:
            p.unlink(missing_ok=True)

    def test_ai_residue_has_flag_and_allow_cases(self):
        cases = (
            ("tracking parameter", "來源：https://example.com/post?utm_source=chatgpt.com。\n", "來源：https://example.com/post。\n"),
            ("citation residue", "來源代碼是 turn0search0。\n", "範例程式是 `turn0search0`。\n"),
            ("quoted citation residue", "來源代碼是 turn0search0。\n", "受訪者說：「請保留 turn0search0。」\n"),
        )
        for name, bad, allowed in cases:
            with self.subTest(name=name, direction="flag"):
                p = write_tmp(bad)
                try:
                    self.assertEqual(run(STYLE, p).returncode, 10)
                finally:
                    p.unlink(missing_ok=True)
            with self.subTest(name=name, direction="allow"):
                p = write_tmp(allowed)
                try:
                    self.assertEqual(run(STYLE, p).returncode, 0)
                finally:
                    p.unlink(missing_ok=True)


class ProtectedMaterialCheck(unittest.TestCase):
    def test_exact_protected_material_passes(self):
        before = write_tmp(
            "8/30 的票價是 500 元。詳見 [活動頁](https://example.com/a)。\n"
            "小美說：「我會去。」請執行 `python check.py`。\n"
        )
        after = write_tmp(
            "票價 500 元，活動日期是 8/30。請看 [活動頁](https://example.com/a)。\n"
            "小美說：「我會去。」接著執行 `python check.py`。\n"
        )
        manifest = write_manifest(
            [
                {"value": "8/30", "count": 1},
                {"value": "500", "count": 1},
                {"value": "https://example.com/a", "count": 1},
                {"value": "「我會去。」", "count": 1},
                {"value": "`python check.py`", "count": 1},
            ]
        )
        try:
            self.assertEqual(run(PROTECTED, manifest, before, after).returncode, 0)
        finally:
            manifest.unlink(missing_ok=True)
            before.unlink(missing_ok=True)
            after.unlink(missing_ok=True)

    def test_changed_material_fails(self):
        before = write_tmp("活動是 8/30，票價 500 元。詳見 https://example.com/a。\n")
        after = write_tmp("活動是 8/31，票價 550 元。詳見 https://example.com/b。\n")
        manifest = write_manifest(
            [
                {"value": "8/30", "count": 1},
                {"value": "500", "count": 1},
                {"value": "https://example.com/a", "count": 1},
            ]
        )
        try:
            result = run(PROTECTED, manifest, before, after)
            self.assertEqual(result.returncode, 10, result.stdout)
            self.assertIn("8/30", result.stdout)
            self.assertIn("https://example.com/a", result.stdout)
        finally:
            manifest.unlink(missing_ok=True)
            before.unlink(missing_ok=True)
            after.unlink(missing_ok=True)

    def test_ai_tracking_cleanup_preserves_other_query_bytes(self):
        old_url = (
            "https://example.com/a?label=a%20b&utm_source=chatgpt.com"
            "&tag=one&tag=two&referrer=grok.com&z=%2F#part"
        )
        new_url = "https://example.com/a?label=a%20b&tag=one&tag=two&z=%2F#part"
        before = write_tmp(f"活動頁：{old_url}\n")
        after = write_tmp(f"活動頁：{new_url}\n")
        manifest = write_manifest(
            [{"value": old_url, "count": 1, "allow_ai_tracking_cleanup": True}]
        )
        try:
            self.assertEqual(run(PROTECTED, manifest, before, after).returncode, 0)
        finally:
            manifest.unlink(missing_ok=True)
            before.unlink(missing_ok=True)
            after.unlink(missing_ok=True)


class VerbosityCheck(unittest.TestCase):
    def test_bloated_has_findings(self):
        r = run(VERBOSITY, BLOATED, "--format=json")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)

    def test_clean_has_no_findings(self):
        r = run(VERBOSITY, CLEAN, "--format=json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)

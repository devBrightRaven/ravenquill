#!/usr/bin/env python3
"""Smoke tests for the writing-harness checkers. Pure stdlib, no pytest needed.

Run:
    python tests/test_harness.py
Exit 0 = all pass, 1 = a test failed.
"""
import json
import os
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


def run_native(script, *args, env=None):
    return subprocess.run(
        [PY, str(script), *map(str, args)],
        capture_output=True,
        env={**os.environ, **(env or {})},
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
        terms = (
            "視頻", "視頻號", "公眾號", "在線", "網絡", "互聯網", "批量", "軟件",
            "信息", "默認", "鏈接", "範式轉換", "屏幕", "硬盤", "硬件", "服務器",
            "登錄", "操作系統", "數碼", "攝像頭", "賦能", "復盤", "對標", "抓手",
        )
        for blocked in terms:
            with self.subTest(term=blocked, direction="flag"):
                p = write_tmp(f"這次使用{blocked}。\n")
                try:
                    self.assertEqual(run(STYLE, p).returncode, 10)
                finally:
                    p.unlink(missing_ok=True)
            with self.subTest(term=blocked, direction="allow"):
                p = write_tmp(f"原始欄位值是 `{blocked}`。\n")
                try:
                    self.assertEqual(run(STYLE, p).returncode, 0)
                finally:
                    p.unlink(missing_ok=True)

    def test_public_jargon_has_paired_flag_and_allow_cases(self):
        terms = ("機械可檢", "false positive", "verbatim")
        for term in terms:
            with self.subTest(text=term, direction="flag"):
                p = write_tmp(f"對外文字不要寫 {term}。\n")
                try:
                    self.assertEqual(run(STYLE, p, "--public").returncode, 10)
                finally:
                    p.unlink(missing_ok=True)
            with self.subTest(text=term, direction="allow"):
                p = write_tmp(f"範例欄位是 `{term}`。\n")
                try:
                    self.assertEqual(run(STYLE, p, "--public").returncode, 0)
                finally:
                    p.unlink(missing_ok=True)

    def test_contrast_regex_has_flag_and_allow_boundaries(self):
        flagged = write_tmp("不是甲，是乙。\n不是丙，而是丁。\n不是戊，是己。\n")
        allowed = write_tmp("不是甲，是乙。\n原話是「不是丙，而是丁」。\n`不是戊，是己`。\n")
        try:
            self.assertEqual(run(STYLE, flagged).returncode, 10)
            self.assertEqual(run(STYLE, allowed).returncode, 0)
        finally:
            flagged.unlink(missing_ok=True)
            allowed.unlink(missing_ok=True)

    def test_client_message_semicolon_is_scoped_by_frontmatter(self):
        flagged = write_tmp("---\naudience: external\ntype: client-message\n---\n先確認需求；再回覆。\n")
        allowed = write_tmp("---\naudience: external\ntype: client-message\n---\n指令範例是 `a；b`。\n")
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

    def test_noise_leads_remain_human_judgment(self):
        leads = ("其實", "老實說", "坦白說", "坦白講", "說真的", "講真的", "我記得", "不得不說", "怎麼說呢", "說穿了", "歸根究底", "值得注意的是")
        for lead in leads:
            with self.subTest(lead=lead):
                p = write_tmp(f"{lead}，我們需要重新檢查。\n")
                try:
                    self.assertEqual(run(STYLE, p).returncode, 0)
                finally:
                    p.unlink(missing_ok=True)

    def test_ai_residue_has_flag_and_allow_cases(self):
        cases = (
            ("tracking parameter", "來源：https://example.com/post?utm_source=chatgpt.com。\n", "來源：https://example.com/post。\n"),
            ("citation residue", "來源代碼是 turn0search0。\n", "範例程式是 `turn0search0`。\n"),
            ("quoted citation residue", "來源代碼是 turn0search0。\n", "受訪者說：「請保留 turn0search0。」\n"),
            ("CJK-adjacent residue", "來源turn0search0可查。\n", "來源turn0search0x可查。\n"),
            ("tilde fence", "來源 turn0search0。\n", "~~~text\nturn0search0\n~~~\n"),
            ("indented code", "來源 turn0search0。\n", "    turn0search0\n"),
            ("blockquote", "來源 turn0search0。\n", "> 來源 turn0search0。\n"),
            ("ASCII quote", "來源 turn0search0。\n", '受訪者說「"turn0search0"」。\n'),
            ("curly quote", "來源 turn0search0。\n", "受訪者說：“turn0search0”。\n"),
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

    def test_stateful_markdown_masking_boundaries_and_line_numbers(self):
        allowed = (
            "   ~~~~text\nturn0search0\n~~~~\n",
            "``text ` nested``\n",
            "\n    turn0search0\n",
            '受訪者說 "keep \\"turn0search0\\" here"。\n',
        )
        for text in allowed:
            with self.subTest(text=text):
                p = write_tmp(text)
                try:
                    self.assertEqual(run(STYLE, p).returncode, 0)
                finally:
                    p.unlink(missing_ok=True)

        list_continuation = write_tmp("1. 說明\n    turn0search0\n")
        numbered_line = write_tmp("```\nturn0search0\n```\n乾淨。\nturn9search8\n")
        try:
            self.assertEqual(run(STYLE, list_continuation).returncode, 10)
            result = run(STYLE, numbered_line)
            self.assertEqual(result.returncode, 10)
            self.assertIn("L5", result.stdout)
            self.assertNotIn("L2", result.stdout)
        finally:
            list_continuation.unlink(missing_ok=True)
            numbered_line.unlink(missing_ok=True)

    def test_touched_style_families_have_close_boundaries(self):
        cases = (
            ("ticket", "請處理 ticket。\n", "欄位是 `ticket`。\n", ()),
            ("summary", "**小結：** 內容。\n", "欄位是 `**小結：**`。\n", ()),
            ("numbered", "第一個趨勢是改善。\n", "第一個步驟是確認。\n", ()),
            ("negation", "## 這不是終點\n", "這不是終點。\n", ()),
            ("dash", "甲——乙。\n", "甲—乙，或輸入 --help；欄位是 `甲——乙`。\n", ()),
            ("urgency", "你必須現在處理。\n", "原話是「你必須現在處理」。\n", ()),
            ("api", "我們要做 API call。\n", "欄位是 `API call`。\n", ()),
            ("half punctuation", "中文,中文。\n", "版本 1,000，句尾可用英文句點.\n", ()),
        )
        for name, bad, good, flags in cases:
            with self.subTest(name=name, direction="flag"):
                p = write_tmp(bad)
                try:
                    self.assertEqual(run(STYLE, p, *flags).returncode, 10)
                finally:
                    p.unlink(missing_ok=True)
            with self.subTest(name=name, direction="allow"):
                p = write_tmp(good)
                try:
                    self.assertEqual(run(STYLE, p, *flags).returncode, 0)
                finally:
                    p.unlink(missing_ok=True)

    def test_ambiguous_sentence_leads_are_human_judgment(self):
        for lead in ("其實", "我記得", "老實說"):
            with self.subTest(lead=lead):
                p = write_tmp(f"{lead}，我們需要重新檢查。\n")
                try:
                    self.assertEqual(run(STYLE, p).returncode, 0)
                finally:
                    p.unlink(missing_ok=True)


class ProtectedMaterialCheck(unittest.TestCase):
    def test_any_digit_bearing_value_uses_digit_boundaries(self):
        cases = (("8/30", "18/300"), ("500.00", "1500.00"), ("ID500A", "ID1500A"))
        for value, changed in cases:
            with self.subTest(value=value):
                before = write_tmp(value)
                after = write_tmp(changed)
                manifest = write_manifest([{"value": value, "count": 1}])
                try:
                    self.assertEqual(run(PROTECTED, manifest, before, after).returncode, 10)
                finally:
                    manifest.unlink(missing_ok=True); before.unlink(missing_ok=True); after.unlink(missing_ok=True)

    def test_url_literal_boundaries_support_markdown_balanced_parentheses_and_bang(self):
        for url, text in (
            ("https://example.com/a(b)", "[來源](https://example.com/a(b))"),
            ("HTTPS://example.com/a!", "來源 HTTPS://example.com/a! 結束"),
        ):
            with self.subTest(url=url):
                before = write_tmp(text); after = write_tmp(text)
                manifest = write_manifest([{"value": url, "count": 1}])
                try:
                    self.assertEqual(run(PROTECTED, manifest, before, after).returncode, 0)
                finally:
                    manifest.unlink(missing_ok=True); before.unlink(missing_ok=True); after.unlink(missing_ok=True)

        uppercase = "HTTPS://example.com/Case"
        manifest = write_manifest([{"value": uppercase, "count": 1}])
        before = write_tmp(uppercase); after = write_tmp("https://example.com/Case")
        try:
            self.assertEqual(run(PROTECTED, manifest, before, after).returncode, 10)
        finally:
            manifest.unlink(missing_ok=True); before.unlink(missing_ok=True); after.unlink(missing_ok=True)

    def test_manifest_rejects_empty_and_duplicate_values(self):
        before = write_tmp("x"); after = write_tmp("x")
        manifests = (
            [{"value": "", "count": 1}],
            [{"value": "x", "count": 1}, {"value": "x", "count": 1}],
        )
        try:
            for items in manifests:
                manifest = write_manifest(items)
                try:
                    self.assertEqual(run(PROTECTED, manifest, before, after).returncode, 2)
                finally:
                    manifest.unlink(missing_ok=True)
        finally:
            before.unlink(missing_ok=True); after.unlink(missing_ok=True)

    def test_cleanup_aggregates_colliding_normalized_urls(self):
        one = "https://example.com/a?utm_source=chatgpt.com"
        two = "https://example.com/a?utm_source=openai"
        manifest = write_manifest([
            {"value": one, "count": 1, "allow_ai_tracking_cleanup": True},
            {"value": two, "count": 1, "allow_ai_tracking_cleanup": True},
        ])
        before = write_tmp(f"{one}\n{two}\n"); after = write_tmp("https://example.com/a\n")
        try:
            self.assertEqual(run(PROTECTED, manifest, before, after).returncode, 10)
        finally:
            manifest.unlink(missing_ok=True); before.unlink(missing_ok=True); after.unlink(missing_ok=True)

    def test_cleanup_only_accepts_exact_raw_tracking_segments(self):
        for segment in ("utm_source=ChatGPT.com", "utm_source=chatgpt%2Ecom"):
            url = f"https://example.com/a?x=1&{segment}"
            manifest = write_manifest([{"value": url, "count": 1, "allow_ai_tracking_cleanup": True}])
            before = write_tmp(url); after = write_tmp("https://example.com/a?x=1")
            try:
                self.assertEqual(run(PROTECTED, manifest, before, after).returncode, 10)
            finally:
                manifest.unlink(missing_ok=True); before.unlink(missing_ok=True); after.unlink(missing_ok=True)
    def test_embedded_number_does_not_satisfy_exact_count(self):
        before = write_tmp("票價 500 元。\n")
        after = write_tmp("票價 1500 元。\n")
        manifest = write_manifest([{"value": "500", "count": 1}])
        try:
            self.assertEqual(run(PROTECTED, manifest, before, after).returncode, 10)
        finally:
            manifest.unlink(missing_ok=True)
            before.unlink(missing_ok=True)
            after.unlink(missing_ok=True)

    def test_complete_url_token_rejects_suffix_or_query_addition(self):
        url = "https://example.com/a"
        manifest = write_manifest([{"value": url, "count": 1}])
        before = write_tmp(f"來源：{url}\n")
        try:
            for changed in (f"{url}/extra", f"{url}?added=1", f"x{url}"):
                with self.subTest(changed=changed):
                    after = write_tmp(f"來源：{changed}\n")
                    try:
                        self.assertEqual(run(PROTECTED, manifest, before, after).returncode, 10)
                    finally:
                        after.unlink(missing_ok=True)
        finally:
            manifest.unlink(missing_ok=True)
            before.unlink(missing_ok=True)

    def test_tracking_cleanup_rejects_any_other_url_change(self):
        old_url = "https://example.com/a?x=1&tag=one&tag=two&utm_source=chatgpt.com&label=a%20b#part"
        manifest = write_manifest([{"value": old_url, "count": 1, "allow_ai_tracking_cleanup": True}])
        before = write_tmp(f"來源：{old_url}\n")
        changed_urls = (
            "https://example.com/a?tag=one&tag=two&x=1&label=a%20b#part",
            "https://example.com/a?x=1&tag=one&tag=two&label=a+b#part",
            "https://example.com/a?x=1&tag=one&label=a%20b#part",
            "https://example.com/a?x=1&tag=one&tag=two&label=a%20b#other",
        )
        try:
            for changed in changed_urls:
                with self.subTest(changed=changed):
                    after = write_tmp(f"來源：{changed}\n")
                    try:
                        self.assertEqual(run(PROTECTED, manifest, before, after).returncode, 10)
                    finally:
                        after.unlink(missing_ok=True)
        finally:
            manifest.unlink(missing_ok=True)
            before.unlink(missing_ok=True)

    def test_malformed_manifests_exit_two_without_traceback(self):
        before = write_tmp("原文。\n")
        after = write_tmp("原文。\n")
        manifests = (
            "[]",
            '{"items":[{"value":"x","count":true}]}',
            '{"items":[{"value":"https://example.com","count":1,"allow_ai_tracking_cleanup":"yes"}]}',
            "{not-json",
        )
        try:
            for raw in manifests:
                with self.subTest(raw=raw):
                    manifest = write_tmp(raw)
                    try:
                        result = run(PROTECTED, manifest, before, after)
                        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                        self.assertNotIn("Traceback", result.stderr)
                    finally:
                        manifest.unlink(missing_ok=True)
        finally:
            before.unlink(missing_ok=True)
            after.unlink(missing_ok=True)

    def test_unknown_option_fails_clearly(self):
        result = run(PROTECTED, "manifest.json", "before.md", "after.md", "--manfiest")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("--manfiest", result.stderr)

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


class CliPortability(unittest.TestCase):
    def test_user_facing_clis_do_not_crash_under_cp932_output(self):
        article = write_tmp("這裡用了破折號——這就違規了。\n")
        before = write_tmp("票價 500 元。\n")
        after = write_tmp("票價 550 元。\n")
        manifest = write_manifest([{"value": "500", "count": 1}])
        try:
            commands = (
                (STYLE, (article,)),
                (PROTECTED, (manifest, before, after)),
            )
            for script, args in commands:
                with self.subTest(script=script.name):
                    result = run_native(script, *args, env={"PYTHONIOENCODING": "cp932"})
                    self.assertEqual(result.returncode, 10, result.stderr.decode("ascii", errors="ignore"))
                    self.assertNotIn(b"UnicodeEncodeError", result.stderr)
        finally:
            article.unlink(missing_ok=True)
            manifest.unlink(missing_ok=True)
            before.unlink(missing_ok=True)
            after.unlink(missing_ok=True)

        result = run_native(VERBOSITY, BLOATED, "--format=markdown", env={"PYTHONIOENCODING": "cp932"})
        self.assertEqual(result.returncode, 1, result.stderr.decode("ascii", errors="ignore"))
        self.assertNotIn(b"UnicodeEncodeError", result.stderr)


class VerbosityCheck(unittest.TestCase):
    def test_bloated_has_findings(self):
        r = run(VERBOSITY, BLOATED, "--format=json")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)

    def test_clean_has_no_findings(self):
        r = run(VERBOSITY, CLEAN, "--format=json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)

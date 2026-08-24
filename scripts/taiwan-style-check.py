#!/usr/bin/env python3
"""S1 mechanical gate: Taiwan-style hard rules (grep-level, no LLM).

Scans style hard rules, outputs Markdown report to stdout.
- Exit 0: all pass
- Exit 10: any hit

Usage:
    python taiwan-style-check.py <file.md> [--public]

Rule sync: rules here mirror methodology/taiwan-writing-glossary.md §6 and the
"conclusion-lead / noise-frame" section of methodology/writing-harness.md S1.
When the glossary/harness gains a regex-able rule, add the matching check
function here. Verb audit (glossary §2.2) is context-dependent and intentionally
left to LLM self-comparison against the glossary table, not regex.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ENGLISH_TECH_WORDS = [
    r"\bticket\b",
    r"\bbugs?\b",
    r"\bprompts?\b",
    r"\bcode\b",
    r"\bjuniors?\b",
    r"\btech\s+guys?\b",
    r"\blow\s+context\b",
]

SUMMARY_LABELS = [
    r"\*\*小結[:：]",
    r"\*\*Takeaway[:：]",
    r"\*\*重點[:：]",
    r"\*\*TL;DR",
]

NUMBERED_LEAD = r"第[一二三四五六七八九十]個(趨勢|發現|觀察|重點|反直覺|關鍵)"

CONTRAST_PATTERN = r"不是.{1,15}?，而?是"

NEGATION_H_TITLE = r"^#{2,6}\s+.*不是"

EM_DASH = r"——|──"

URGENCY_WORDS = [
    "該停下來看",
    "值得重視",
    "不可不知",
    "不得不",
    "你必須",
    "建議先收藏",
    "再不學就來不及",
]

# 大陸用語 (glossary §2.1，硬擋)
# 不收：數據／項目／文件／用戶／平臺 = 風格偏好 (glossary §2.1.3)，純子字串 grep 誤報過高
MAINLAND_WORDS = [
    # 媒體 / 社群
    "視頻",
    "視頻號",
    "公眾號",
    # 網路 / 數位
    "在線",
    "網絡",
    "互聯網",
    "批量",
    "軟件",
    "信息",
    "默認",
    "鏈接",
    "範式轉換",
    # 科技詞 (glossary §2.1.1)
    "屏幕",
    "硬盤",
    "硬件",
    "服務器",
    "登錄",
    "操作系統",
    "數碼",
    "攝像頭",
    # 商業黑話 (glossary §2.1.2，只擋重黑話)
    "賦能",
    "復盤",
    "對標",
    "抓手",
]

# API 術語禁令 (glossary §3.1)
API_TERMS = [
    "打 API call",
    "呼叫 API",
    "API 呼叫",
    "打 API",
    "API call",
]

# 對外工程黑話 (glossary §3.3)，僅 --public 模式檢查（對內檔用這些詞合理，不擋）
# 先窄：只收「對外幾乎不可能有合理用法」的純黑話；游走詞（閘／gate／harness／棘輪／sub-agent）
# 留 glossary §3.3 表靠 LLM 自審，不進 regex（避免誤殺工程客戶語境）。(pattern, 建議替換)
PUBLIC_JARGON = [
    (r"機械可檢", "規則明確 / 電腦抓得到"),
    (r"false\s+positives?", "誤報"),
    (r"\bverbatim\b", "原話完整收錄"),
]

# 對外短訊分號（僅 audience: external + type: client-message，glossary §1.1.1）：
# 訊息用句號斷句更像真人，分號＝書面腔。對外長文用分號列舉合理，故以 frontmatter 精準 gate、不擋長文。
MESSAGE_SEMICOLON = "；"

# 句首雜訊詞 (writing-harness S1)
CONCLUSION_LEAD_NOISE = [
    r"(?:^|[。！？；])\s*(其實|老實說|坦白說|坦白講|說真的|講真的|我記得|不得不說|怎麼說呢|說穿了|歸根究[底柢]|值得注意的是)",
]

AI_TOOL_RESIDUE = [
    r"[?&](?:utm_source=(?:chatgpt\.com|openai)|referrer=grok\.com)(?=&|#|\s|[，。；！？)]|$)",
    r"(?<![A-Za-z0-9_])(?:turn\d+(?:search|news|fetch|view)\d+|cite(?:turn\d+\w*\d+))(?![A-Za-z0-9_])",
]

# 半形標點全形化檢查 — 中文上下文不可用半形 , : ? ( ) ; !
URL_RE = re.compile(r"https?://\S+")
CODE_FENCE_RE = re.compile(r"(?ms)^(?P<fence>`{3,}|~{3,})[^\n]*\n.*?^(?P=fence)\s*$")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
INDENTED_CODE_RE = re.compile(r"(?m)^(?: {4}|\t).*$")
BLOCKQUOTE_RE = re.compile(r"(?m)^ {0,3}>.*$")
QUOTED_SPEECH_RE = re.compile(r"「[^」]*」|『[^』]*』|“[^”]*”|\"[^\"\n]*\"", re.DOTALL)
# CJK 統一表意 + 中文標點 + 全形區
CJK_RE = re.compile(r"[一-鿿　-〿＀-￯]")
HALF_PUNCT = set(",:?();!")


def strip_frontmatter(content):
    if content.startswith("---\n"):
        parts = content.split("\n---\n", 1)
        if len(parts) == 2:
            return parts[1]
    return content


def configure_output():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")


def mask_non_prose(body):
    cleaned = body
    for pattern in (CODE_FENCE_RE, INLINE_CODE_RE, INDENTED_CODE_RE, BLOCKQUOTE_RE, QUOTED_SPEECH_RE):
        cleaned = pattern.sub(lambda m: " " * len(m.group(0)), cleaned)
    return cleaned


def parse_frontmatter(content):
    """輕量解析 frontmatter 的 `key: value`（不依賴 yaml）；無 frontmatter 回 {}。
    僅供 gate 判定（audience / type）用，不求完整 yaml 語意。"""
    if not content.startswith("---\n"):
        return {}
    parts = content.split("\n---\n", 1)
    if len(parts) != 2:
        return {}
    fm = {}
    for line in parts[0].splitlines()[1:]:
        m = re.match(r"\s*([A-Za-z_]+)\s*:\s*(.+?)\s*$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return fm


def find_all_with_line(body, pattern, flags=0):
    hits = []
    for i, line in enumerate(body.splitlines(), start=1):
        for m in re.finditer(pattern, line, flags):
            hits.append((i, m.group(0)))
    return hits


def check_english(body):
    hits = []
    for pattern in ENGLISH_TECH_WORDS:
        hits.extend(find_all_with_line(body, pattern, re.IGNORECASE))
    return hits


def check_summary(body):
    hits = []
    for pattern in SUMMARY_LABELS:
        hits.extend(find_all_with_line(body, pattern))
    return hits


def check_numbered(body):
    return find_all_with_line(body, NUMBERED_LEAD)


def check_contrast(body):
    hits = find_all_with_line(body, CONTRAST_PATTERN)
    return len(hits), hits


def check_negation(body):
    return find_all_with_line(body, NEGATION_H_TITLE, re.MULTILINE)


def check_dash(body):
    return find_all_with_line(body, EM_DASH)


def check_urgency(body):
    hits = []
    for word in URGENCY_WORDS:
        hits.extend(find_all_with_line(body, re.escape(word)))
    return hits


def check_mainland_words(body):
    hits = []
    for word in MAINLAND_WORDS:
        hits.extend(find_all_with_line(body, re.escape(word)))
    return hits


def check_api_terms(body):
    hits = []
    for term in API_TERMS:
        hits.extend(find_all_with_line(body, re.escape(term)))
    return hits


def check_public_jargon(body):
    """對外工程黑話（僅 --public）：命中標出 + 建議白話。"""
    hits = []
    for pat, repl in PUBLIC_JARGON:
        for ln, text in find_all_with_line(body, pat, re.IGNORECASE):
            hits.append((ln, f"{text} → 改「{repl}」"))
    return hits


def check_message_semicolon(body):
    """對外短訊分號（僅 external + client-message）：分號改句號斷句。
    清掉 code fence / inline code 後找全形「；」。"""
    cleaned = mask_non_prose(body)
    hits = []
    for ln, text in find_all_with_line(cleaned, MESSAGE_SEMICOLON):
        hits.append((ln, f"{text} → 改句號斷句（訊息少用分號）"))
    return hits


def check_conclusion_lead_noise(body):
    hits = []
    for pattern in CONCLUSION_LEAD_NOISE:
        hits.extend(find_all_with_line(body, pattern))
    return hits


def check_ai_tool_residue(body):
    hits = []
    for pattern in AI_TOOL_RESIDUE:
        hits.extend(find_all_with_line(body, pattern, re.IGNORECASE))
    return hits


def check_halfwidth_punct(body):
    """掃中文上下文中的半形標點（前後 1 字含 CJK 即命中）。
    排除：URL、code fence、inline code、數字夾標點（1,000 / 12:30）。
    """
    cleaned = body
    cleaned = CODE_FENCE_RE.sub(lambda m: " " * len(m.group(0)), cleaned)
    cleaned = INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), cleaned)
    cleaned = URL_RE.sub(lambda m: " " * len(m.group(0)), cleaned)

    hits = []
    for line_no, line in enumerate(cleaned.splitlines(), start=1):
        for i, ch in enumerate(line):
            if ch not in HALF_PUNCT:
                continue
            left = line[i - 1] if i > 0 else ""
            right = line[i + 1] if i < len(line) - 1 else ""
            # 數字夾標點：1,000 / 12:30 / 1;2 視為合法
            if left.isdigit() and right.isdigit():
                continue
            # 前後皆非 CJK → 半形合法（英文上下文）
            if not (CJK_RE.match(left) or CJK_RE.match(right)):
                continue
            start = max(0, i - 6)
            end = min(len(line), i + 7)
            context = line[start:end].replace("\n", " ")
            hits.append((line_no, f"半形 {ch!r} → ...{context}..."))
    return hits


def fmt_hits(hits, limit=10):
    if not hits:
        return "  (none)"
    lines = []
    for ln, text in hits[:limit]:
        lines.append(f"  - L{ln}: `{text}`")
    if len(hits) > limit:
        lines.append(f"  - ... ({len(hits)} total, showing first {limit})")
    return "\n".join(lines)


def main():
    configure_output()
    parser = argparse.ArgumentParser(
        description="Check Taiwan-style hard rules in a Markdown file."
    )
    parser.add_argument("path", type=Path)
    parser.add_argument("--public", action="store_true", help="also check public-facing jargon")
    args = parser.parse_args()

    path = args.path
    public = args.public
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 2

    content = path.read_text(encoding="utf-8")
    body = strip_frontmatter(content)
    scan_body = mask_non_prose(body)
    fm = parse_frontmatter(content)
    is_client_msg = fm.get("audience", "").startswith("external") and "client-message" in fm.get("type", "")

    results = {
        "英文技術詞密度": check_english(body),
        "小結格式標記": check_summary(body),
        "段落引導語贅字（第 N 個 X）": check_numbered(body),
        "否定懸念段落標題": check_negation(body),
        "破折號漏網": check_dash(body),
        "開場推銷詞": check_urgency(scan_body),
        "半形標點漏網（中文上下文）": check_halfwidth_punct(body),
        "大陸用語（glossary §2.1）": check_mainland_words(scan_body),
        "API 術語（glossary §3.1）": check_api_terms(scan_body),
        "結論引導／雜訊框架詞（writing-harness S1）": check_conclusion_lead_noise(scan_body),
        "AI 工具殘留": check_ai_tool_residue(scan_body),
    }
    if public:
        results["對外工程黑話（--public，glossary §3.3）"] = check_public_jargon(scan_body)
    if is_client_msg:
        results["對外短訊分號（；，client-message）"] = check_message_semicolon(body)

    contrast_count, contrast_hits = check_contrast(scan_body)
    any_hit = any(hits for hits in results.values()) or contrast_count > 2

    print(f"# 台灣口語硬規則檢查 — `{path.name}`\n")

    for label, hits in results.items():
        status = f"❌ {len(hits)} 處" if hits else "✅ 0"
        print(f"## {label}: {status}")
        print(fmt_hits(hits))
        print()

    contrast_status = (
        f"❌ {contrast_count} 處（上限 2）"
        if contrast_count > 2
        else f"✅ {contrast_count} / ≤2"
    )
    print(f"## 「不是 X 是 Y」對比密度: {contrast_status}")
    print(fmt_hits(contrast_hits))
    print()

    if any_hit:
        print("---\n**結論：有命中項。請逐條修正後重跑。**")
        return 10
    else:
        print("---\n**結論：全數通過。**")
        return 0


if __name__ == "__main__":
    sys.exit(main())

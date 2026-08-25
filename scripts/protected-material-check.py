#!/usr/bin/env python3
"""Verify an explicit protected-material manifest after a rewrite."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path


AI_TRACKING_SEGMENTS = {
    "utm_source=chatgpt.com",
    "utm_source=openai",
    "referrer=grok.com",
}
URL_SCHEME_RE = re.compile(r"^https?://", re.IGNORECASE)
URL_BOUNDARY = set(" \t\r\n<>\"'「」『』，。；：！？")
URL_LEFT_BOUNDARY = URL_BOUNDARY
DIGIT_JOINERS = set(".,/:+-")


def configure_output():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")


def strip_ai_tracking(url):
    before_fragment, fragment_mark, fragment = url.partition("#")
    base, query_mark, query = before_fragment.partition("?")
    if not query_mark:
        return url

    kept = []
    for segment in query.split("&"):
        if segment not in AI_TRACKING_SEGMENTS:
            kept.append(segment)

    cleaned = base + (f"?{'&'.join(kept)}" if kept else "")
    return cleaned + (f"#{fragment}" if fragment_mark else "")


def load_manifest(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest root must be an object")
    items = data.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("manifest.items must be a non-empty list")
    seen = set()
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("value"), str):
            raise ValueError("each item requires a string value")
        value = item["value"]
        if not value:
            raise ValueError("protected values must not be empty")
        if value in seen:
            raise ValueError("protected values must be unique")
        seen.add(value)
        count = item.get("count")
        if type(count) is not int or count < 1:
            raise ValueError("each item requires a positive integer count")
        cleanup = item.get("allow_ai_tracking_cleanup", False)
        if type(cleanup) is not bool:
            raise ValueError("allow_ai_tracking_cleanup must be a boolean")
        if cleanup and not URL_SCHEME_RE.match(value):
            raise ValueError("allow_ai_tracking_cleanup is valid only for a full URL")
    return items


def count_url_literal(text, value):
    """Count exact URL bytes only when the following character ends the URL token."""
    count = 0
    start = 0
    while True:
        index = text.find(value, start)
        if index < 0:
            return count
        end = index + len(value)
        left_ok = index == 0 or text[index - 1] in URL_LEFT_BOUNDARY
        right_ok = end == len(text) or text[end] in URL_BOUNDARY
        paired_wrapper = any(
            text[max(0, index - len(left)):index] == left and text[end:end + len(right)] == right
            for left, right in (("(", ")"), ("（", "）"), ("**", "**"), ("__", "__"))
        )
        left_ticks = len(text[:index]) - len(text[:index].rstrip("`"))
        right_ticks = len(text[end:]) - len(text[end:].lstrip("`"))
        paired_wrapper = paired_wrapper or (left_ticks > 0 and left_ticks == right_ticks)
        if (left_ok and right_ok) or paired_wrapper:
            count += 1
        start = index + 1


def count_value(text, value):
    if URL_SCHEME_RE.match(value):
        return count_url_literal(text, value)
    if re.search(r"\d", value):
        count = 0
        start = 0
        while True:
            index = text.find(value, start)
            if index < 0:
                return count
            end = index + len(value)
            left = text[index - 1] if index else ""
            right = text[end] if end < len(text) else ""
            left_word = left.isascii() and (left.isalnum() or left == "_")
            right_word = right.isascii() and (right.isalnum() or right == "_")
            left_number = index >= 2 and left in DIGIT_JOINERS and text[index - 2].isdigit()
            right_number = end + 1 < len(text) and right in DIGIT_JOINERS and text[end + 1].isdigit()
            if not (left_word or right_word or left_number or right_number):
                count += 1
            start = index + 1
    return text.count(value)


def verify(items, before, after):
    failures = []
    after_expected = Counter()
    source_for_after = {}
    for item in items:
        value = item["value"]
        expected = item["count"]
        before_count = count_value(before, value)
        after_value = strip_ai_tracking(value) if item.get("allow_ai_tracking_cleanup") else value
        if before_count != expected:
            failures.append((value, expected, before_count, after_value, count_value(after, after_value)))
        if after_value not in after_expected:
            after_expected[after_value] = count_value(before, after_value)
        if after_value != value:
            after_expected[after_value] += expected
        source_for_after.setdefault(after_value, value)
    for after_value, expected in after_expected.items():
        after_count = count_value(after, after_value)
        if after_count != expected:
            value = source_for_after[after_value]
            failures.append((value, expected, count_value(before, value), after_value, after_count))
    return failures


def main():
    configure_output()
    parser = argparse.ArgumentParser(description="Verify protected material after a rewrite.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args()

    manifest_path, before_path, after_path = args.manifest, args.before, args.after
    if not all(path.exists() for path in (manifest_path, before_path, after_path)):
        print("Manifest, before, and after files must exist.", file=sys.stderr)
        return 2

    try:
        items = load_manifest(manifest_path)
    except (json.JSONDecodeError, OSError, UnicodeError, ValueError) as error:
        print(f"Invalid manifest: {error}", file=sys.stderr)
        return 2

    try:
        before = before_path.read_text(encoding="utf-8")
        after = after_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        print(f"Unable to read input: {error}", file=sys.stderr)
        return 2
    failures = verify(items, before, after)
    print("# Protected Material Report\n")
    if not failures:
        print("PASS: every declared literal has the expected count.")
        return 0

    for value, expected, before_count, after_value, after_count in failures:
        print(f"- {value!r}: expected {expected}; before={before_count}; after {after_value!r}={after_count}")
    print("\nFAIL: declared protected material drifted or the manifest does not match the source.")
    return 10


if __name__ == "__main__":
    sys.exit(main())

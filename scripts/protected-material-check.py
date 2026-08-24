#!/usr/bin/env python3
"""Verify an explicit protected-material manifest after a rewrite."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote_plus


AI_TRACKING = {
    ("utm_source", "chatgpt.com"),
    ("utm_source", "openai"),
    ("referrer", "grok.com"),
}

URL_RE = re.compile(r"https?://[^\s<>\"']+")
URL_TRAILING_PUNCTUATION = ".,;:!?，。；：！？)]}」』"


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
        raw_key, separator, raw_value = segment.partition("=")
        key = unquote_plus(raw_key).lower()
        value = unquote_plus(raw_value).lower() if separator else ""
        if (key, value) not in AI_TRACKING:
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
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("value"), str):
            raise ValueError("each item requires a string value")
        count = item.get("count")
        if type(count) is not int or count < 1:
            raise ValueError("each item requires a positive integer count")
        cleanup = item.get("allow_ai_tracking_cleanup", False)
        if type(cleanup) is not bool:
            raise ValueError("allow_ai_tracking_cleanup must be a boolean")
        if cleanup and not item["value"].startswith(("http://", "https://")):
            raise ValueError("allow_ai_tracking_cleanup is valid only for a full URL")
    return items


def extract_urls(text):
    return [match.group(0).rstrip(URL_TRAILING_PUNCTUATION) for match in URL_RE.finditer(text)]


def count_value(text, value):
    if value.startswith(("http://", "https://")):
        return extract_urls(text).count(value)
    if value.isdecimal():
        return len(re.findall(rf"(?<!\d){re.escape(value)}(?!\d)", text))
    return text.count(value)


def verify(items, before, after):
    failures = []
    for item in items:
        value = item["value"]
        expected = item["count"]
        before_count = count_value(before, value)
        after_value = strip_ai_tracking(value) if item.get("allow_ai_tracking_cleanup") else value
        after_count = count_value(after, after_value)
        if before_count != expected or after_count != expected:
            failures.append((value, expected, before_count, after_value, after_count))
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

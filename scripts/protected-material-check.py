#!/usr/bin/env python3
"""Verify an explicit protected-material manifest after a rewrite."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import unquote_plus


AI_TRACKING = {
    ("utm_source", "chatgpt.com"),
    ("utm_source", "openai"),
    ("referrer", "grok.com"),
}


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
    items = data.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("manifest.items must be a non-empty list")
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("value"), str):
            raise ValueError("each item requires a string value")
        if not isinstance(item.get("count"), int) or item["count"] < 1:
            raise ValueError("each item requires a positive integer count")
        if item.get("allow_ai_tracking_cleanup") and not item["value"].startswith(("http://", "https://")):
            raise ValueError("allow_ai_tracking_cleanup is valid only for a full URL")
    return items


def verify(items, before, after):
    failures = []
    for item in items:
        value = item["value"]
        expected = item["count"]
        before_count = before.count(value)
        after_value = strip_ai_tracking(value) if item.get("allow_ai_tracking_cleanup") else value
        after_count = after.count(after_value)
        if before_count != expected or after_count != expected:
            failures.append((value, expected, before_count, after_value, after_count))
    return failures


def main():
    if len(sys.argv) != 4:
        print("Usage: protected-material-check.py <manifest.json> <before.md> <after.md>", file=sys.stderr)
        return 2

    manifest_path, before_path, after_path = map(Path, sys.argv[1:])
    if not all(path.exists() for path in (manifest_path, before_path, after_path)):
        print("Manifest, before, and after files must exist.", file=sys.stderr)
        return 2

    try:
        items = load_manifest(manifest_path)
    except (json.JSONDecodeError, OSError, ValueError) as error:
        print(f"Invalid manifest: {error}", file=sys.stderr)
        return 2

    failures = verify(
        items,
        before_path.read_text(encoding="utf-8"),
        after_path.read_text(encoding="utf-8"),
    )
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

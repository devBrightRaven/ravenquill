---
name: ravenquill
description: Use when drafting, editing, or reviewing reader-facing prose where authorship, source fidelity, or Taiwan Traditional Chinese quality matters.
---

# Ravenquill

Preserve the human author's facts, voice, and decision authority while making writing clearer. Use the repository-relative methodology and Python standard-library checks; optional adapters never change this contract.

## Establish the contract

Before reviewing or editing, record:

```text
scene: fiction | social | newsletter | sales | customer-service | office-report | general
edit_authority: review-only | propose | apply
surface_scope: <files, sections, fields, or output covered by this pass>
source_evidence: <authored story evidence | none>  # optional for fiction
protected_material: <manifest.json | none>
```

- `review-only`: inspect and report; do not write.
- `propose`: provide candidate changes; do not apply them.
- `apply`: write only inside `surface_scope`.
- The human decides what to accept, save, and publish. Hooks and integrations may remind or report, but cannot expand authority or scope.

For `scene: fiction`, use supplied authored story evidence instead of nonfiction real-case or public-claim requirements. Keep packet-external facts, beliefs, character knowledge, canon, and voice constraints unresolved. New character dialogue for a named character requires supplied authored voice constraints and is blocked without them. Existing dialogue may be reviewed or edited with exactly `voice fidelity: unverified` when constraints are absent.

Read [methodology/writing-harness.md](methodology/writing-harness.md) for the S0/S1/S2 gates. For Taiwan-facing Traditional Chinese, also read [methodology/taiwan-writing-glossary.md](methodology/taiwan-writing-glossary.md).

## Protect source material

If protected material exists, save the pre-edit text and create a non-empty JSON manifest before editing. List each exact literal and its expected source count; do not infer or normalize names, dates, numbers, promises, quotations, or URLs. When supplied prose contains a URL and the user asks to preserve facts or source material, the protected literal is the complete supplied URL by default, not selected components.

```json
{"items":[{"value":"8/30","count":1},{"value":"https://example.com/?x=1&utm_source=ChatGPT.com","count":1}]}
```

After editing, run:

```text
python -X utf8 scripts/protected-material-check.py manifest.json before.md after.md
```

Exit `0` passes; any other result remains unresolved. If there is genuinely nothing to protect, record `protected_material: none` and skip this checker. Never invent a placeholder literal or use an empty manifest.

Automatic URL cleanup is limited to removing these exact lowercase raw query segments when the manifest item sets `allow_ai_tracking_cleanup: true`:

```text
utm_source=chatgpt.com
utm_source=openai
referrer=grok.com
```

The required result for a protected URL is one of: the complete URL remains exact; only manifest-authorized exact lowercase raw segments are removed; or the user explicitly authorizes changing or removing that complete URL. A general request to remove AI traces does not select the latter two results. Case or encoded variants such as `utm_source=ChatGPT.com` remain exact and appear in the report as an unresolved human decision unless the user gives that explicit authorization. Context-sensitive wording and high-false-positive style terms remain human judgment.

Report protected-material evidence in this shape:

```text
checker: executed | not executed
artifacts: <actual manifest, before, and after paths | none>
result: <actual exit code | manual exact-literal comparison>
unresolved URL decisions: <variants kept unchanged for human decision | none>
```

An exit code belongs only to a command that actually ran against those artifacts. For chat-only or simulated rewriting, report `checker: not executed` and the manual literal comparison instead.

## Validate the draft

Run the mechanical gate on the edited Markdown:

```text
python -X utf8 scripts/taiwan-style-check.py article.md
python -X utf8 scripts/taiwan-style-check.py article.md --public
```

Use `--public` for general-reader output. Exit `0` passes; exit `10` reports findings to resolve. Then complete S2's human review and report the contract, command results, protected-material result or `none`, and unresolved judgment calls. A mechanical pass never grants permission to apply edits or make the final publishing decision.

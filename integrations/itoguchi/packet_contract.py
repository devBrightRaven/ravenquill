"""Validate optional Itoguchi scene-evidence packets for Ravenquill."""

import importlib.util
from collections import Counter
from pathlib import Path


class PacketContractError(ValueError):
    """The supplied evidence packet is unsupported or unsafe to consume."""


_TOP_LEVEL_KEYS = {
    "contract",
    "story_revision",
    "query",
    "authored_evidence",
    "derived_context",
    "voice_constraints",
    "warnings",
}
_QUERY_KEYS = {"holder", "resolved_holder", "as_of", "about", "persona"}
_KNOWN_WARNINGS = {"voice_constraints_missing", "scene_presence_unverified"}
_WINDOWS_FORBIDDEN_CHARS = '<>:"\\|?*'
_WINDOWS_RESERVED_BASENAMES = {
    "con", "prn", "aux", "nul",
    "com¹", "com²", "com³", "lpt¹", "lpt²", "lpt³",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}
_AUTHORED_POINTERS = {
    "belief": ("beliefs", {"content"}),
    "fact": ("facts", {"content"}),
    "emotion": ("emotional_state", {"state"}),
    "agenda": ("agenda", {"goal"}),
    "relation": ("relations", {"surface", "hidden_tension", "secret_asymmetry"}),
    "nested_belief": ("nested_beliefs", {"believes_content"}),
    "deception": ("deceptions", {"lie"}),
    "persona": ("personas", {"id"}),
}

_checker_path = Path(__file__).resolve().parents[2] / "scripts" / "protected-material-check.py"
_checker_spec = importlib.util.spec_from_file_location(
    "ravenquill_protected_material_check", _checker_path
)
if _checker_spec is None or _checker_spec.loader is None:
    raise ImportError(f"unable to load protected-material checker: {_checker_path}")
_checker = importlib.util.module_from_spec(_checker_spec)
_checker_spec.loader.exec_module(_checker)
_count_value = _checker.count_value


def _require(condition, message):
    if not condition:
        raise PacketContractError(message)


def _nonempty_string(value, label):
    _require(isinstance(value, str) and value.strip(), f"{label} must be a non-empty string")


def _story_time(value, label, *, nullable=False):
    if nullable and value is None:
        return
    _require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        f"{label} must be a number" + (" or null" if nullable else ""),
    )
    _require(value == value and abs(value) != float("inf"), f"{label} must be finite")


def _revision(value, label):
    _require(isinstance(value, str) and value.startswith("sha256:"), f"{label} must use sha256")
    digest = value[7:]
    _require(
        len(digest) == 64 and all(char in "0123456789abcdef" for char in digest),
        f"{label} must contain 64 lowercase hexadecimal characters",
    )


def _source(value, label, collection, fields):
    _require(isinstance(value, dict), f"{label} must be an object")
    _require(set(value) == {"path", "pointer"}, f"{label} must contain only path and pointer")
    path = value.get("path")
    _nonempty_string(path, f"{label}.path")
    parts = path.split("/")
    _require(
        not any(char in _WINDOWS_FORBIDDEN_CHARS for char in path)
        and not any(ord(char) < 32 or ord(char) == 127 for char in path)
        and all(part not in ("", ".", "..") for part in parts),
        f"{label}.path must be a portable relative path",
    )
    _require(
        not any(part.endswith((".", " ")) for part in parts)
        and not any(
            part.split(".", 1)[0].casefold() in _WINDOWS_RESERVED_BASENAMES
            for part in parts
        ),
        f"{label}.path must be a portable relative path",
    )
    _require(parts[-1].endswith(".md"), f"{label}.path must end with .md")
    pointer = value.get("pointer")
    pointer_parts = pointer[1:].split("/") if isinstance(pointer, str) else []
    _require(
        isinstance(pointer, str)
        and pointer.startswith("/")
        and len(pointer_parts) == 3
        and pointer_parts[0] == collection
        and pointer_parts[2] in fields,
        f"{label}.pointer does not match its v1 authority",
    )
    _canonical_decimal(pointer_parts[1], f"{label}.pointer index")
    return path, pointer


def _exact_keys(value, required, label, optional=()):
    _require(isinstance(value, dict), f"{label} must be an object")
    keys = set(value)
    _require(required <= keys and keys <= required | set(optional), f"{label} has missing or unsupported fields")


def _item_ids(item_ids):
    _require(isinstance(item_ids, list), "item_ids must be a list")
    for index, item_id in enumerate(item_ids):
        _nonempty_string(item_id, f"item_ids[{index}]")
    _require(len(item_ids) == len(set(item_ids)), "item_ids must not contain duplicates")


def _canonical_decimal(value, label):
    _require(isinstance(value, str), f"{label} must be a string")
    _require(value == "0" or (value.isascii() and value.isdecimal() and not value.startswith("0")), f"{label} must be a canonical decimal")


def _canonical_id(value, prefix, index, label):
    _nonempty_string(value, label)
    _require(value == f"{prefix}{index}", f"{label} must be {prefix}{index}")


def validate_packet(packet: dict, expected_revision: str | None = None) -> None:
    """Reject packets that do not match the exact safe v1 handoff."""
    _require(isinstance(packet, dict), "packet must be an object")
    _require(set(packet) == _TOP_LEVEL_KEYS, "packet must contain exactly the v1 fields")
    _require(packet["contract"] == "itoguchi.scene-evidence/v1", "unsupported packet contract")
    _revision(packet["story_revision"], "story_revision")
    if expected_revision is not None:
        _revision(expected_revision, "expected_revision")
        _require(packet["story_revision"] == expected_revision, "story revision does not match")

    query = packet["query"]
    _require(isinstance(query, dict) and set(query) == _QUERY_KEYS, "query must contain exactly the v1 fields")
    _nonempty_string(query.get("holder"), "query.holder")
    _nonempty_string(query.get("resolved_holder"), "query.resolved_holder")
    _story_time(query.get("as_of"), "query.as_of")
    for field in ("about", "persona"):
        value = query.get(field)
        _require(value is None or isinstance(value, str), f"query.{field} must be a string or null")
        if isinstance(value, str):
            _nonempty_string(value, f"query.{field}")

    authored = packet["authored_evidence"]
    derived = packet["derived_context"]
    voices = packet["voice_constraints"]
    warnings = packet["warnings"]
    for collection, label in (
        (authored, "authored_evidence"),
        (derived, "derived_context"),
        (voices, "voice_constraints"),
        (warnings, "warnings"),
    ):
        _require(isinstance(collection, list), f"{label} must be a list")

    all_ids = []
    sources = []
    for index, item in enumerate(authored):
        label = f"authored_evidence[{index}]"
        _exact_keys(item, {"id", "kind", "value", "availability", "source"}, label)
        _canonical_id(item["id"], "a", index + 1, f"{label}.id")
        for field in ("kind", "value"):
            _nonempty_string(item[field], f"{label}.{field}")
        _require(item["kind"] in _AUTHORED_POINTERS, f"{label}.kind is unsupported")
        _require(
            isinstance(item["availability"], str)
            and item["availability"] in {"character", "writer-only"},
            f"{label}.availability is unsupported",
        )
        sources.append(
            _source(item["source"], f"{label}.source", *_AUTHORED_POINTERS[item["kind"]])
        )
        all_ids.append(item["id"])

    authored_ids = set(all_ids)
    for index, item in enumerate(derived):
        label = f"derived_context[{index}]"
        _exact_keys(item, {"id", "kind", "summary", "availability", "basis"}, label)
        _canonical_id(item["id"], "d", index + 1, f"{label}.id")
        for field in ("kind", "summary"):
            _nonempty_string(item[field], f"{label}.{field}")
        _require(item["kind"] == "tension", f"{label}.kind must be tension")
        _require(item["availability"] == "writer-only", f"{label}.availability must be writer-only")
        basis = item["basis"]
        _require(isinstance(basis, list) and basis, f"{label}.basis must be a non-empty list")
        for basis_id in basis:
            _nonempty_string(basis_id, f"{label}.basis item")
        _require(len(basis) == len(set(basis)), f"{label}.basis must not contain duplicates")
        _require(set(basis) <= authored_ids, f"{label}.basis must reference authored evidence")
        all_ids.append(item["id"])

    voice_ids = set()
    optional_voice_fields = {"persona", "toward", "since", "until", "conflicts_with"}
    for index, item in enumerate(voices):
        label = f"voice_constraints[{index}]"
        _exact_keys(item, {"id", "text", "source"}, label, optional_voice_fields)
        _nonempty_string(item["id"], f"{label}.id")
        _require(
            not (len(item["id"]) > 1
                 and item["id"][0] in ("a", "d")
                 and item["id"][1:].isdigit()),
            f"{label}.id must not reuse authored or derived namespaces",
        )
        _nonempty_string(item["text"], f"{label}.text")
        sources.append(
            _source(
                item["source"],
                f"{label}.source",
                "voice_constraints",
                {"text"},
            )
        )
        for field in ("persona", "toward"):
            if field in item:
                _nonempty_string(item[field], f"{label}.{field}")
        if "since" in item:
            _story_time(item["since"], f"{label}.since")
        if "until" in item:
            _story_time(item["until"], f"{label}.until", nullable=True)
        _require(
            item.get("persona", query["persona"]) == query["persona"],
            f"{label}.persona is inactive for the packet query",
        )
        _require(
            item.get("toward", query["about"]) == query["about"],
            f"{label}.toward is inactive for the packet query",
        )
        _require(
            item.get("since", 0) <= query["as_of"],
            f"{label}.since is inactive for the packet query",
        )
        _require(
            item.get("until") is None or query["as_of"] < item["until"],
            f"{label}.until is inactive for the packet query",
        )
        conflicts = item.get("conflicts_with", [])
        _require(isinstance(conflicts, list), f"{label}.conflicts_with must be a list")
        for target in conflicts:
            _nonempty_string(target, f"{label}.conflicts_with item")
        _require(len(conflicts) == len(set(conflicts)), f"{label}.conflicts_with must not contain duplicates")
        voice_ids.add(item["id"])
        all_ids.append(item["id"])

    duplicates = [item_id for item_id, count in Counter(all_ids).items() if count > 1]
    _require(not duplicates, f"packet item IDs must be unique: {duplicates}")
    duplicate_sources = [source for source, count in Counter(sources).items() if count > 1]
    _require(not duplicate_sources, f"packet sources must be unique: {duplicate_sources}")
    casefolded_paths = {}
    for path, _ in sources:
        previous = casefolded_paths.get(path.casefold())
        _require(
            previous is None or previous == path,
            f"packet source paths collide case-insensitively: {previous!r}, {path!r}",
        )
        casefolded_paths[path.casefold()] = path
    for item in voices:
        _require(
            not (set(item.get("conflicts_with", [])) & voice_ids),
            f"active voice constraint conflict declared by {item['id']}",
        )
    for index, warning in enumerate(warnings):
        _nonempty_string(warning, f"warnings[{index}]")
        _require(warning in _KNOWN_WARNINGS, f"warnings[{index}] is unsupported")
    _require(len(warnings) == len(set(warnings)), "warnings must not contain duplicates")
    _require(
        (not voices) == ("voice_constraints_missing" in warnings),
        "voice_constraints_missing must match supplied voice constraints",
    )


def select_protected_items(packet: dict, before_text: str, item_ids: list[str]) -> list[dict]:
    """Return existing Ravenquill manifest items for present authored literals."""
    validate_packet(packet)
    _require(isinstance(before_text, str), "before_text must be a string")
    _item_ids(item_ids)
    authored = {item["id"]: item["value"] for item in packet["authored_evidence"]}
    authored.update({item["id"]: item["text"] for item in packet["voice_constraints"]})
    derived_ids = {item["id"] for item in packet["derived_context"]}
    selected_values = {}
    for item_id in item_ids:
        _require(item_id not in derived_ids, f"derived item cannot be protected: {item_id}")
        _require(item_id in authored, f"unknown authored item: {item_id}")
        selected_values.setdefault(authored[item_id], None)
    selected = []
    for value in selected_values:
        count = _count_value(before_text, value)
        _require(count > 0, f"authored literal is absent from before_text: {value!r}")
        selected.append({"value": value, "count": count})
    return selected


def require_character_available(packet: dict, item_ids: list[str]) -> None:
    """Require every requested ID to be character-available authored evidence."""
    validate_packet(packet)
    _item_ids(item_ids)
    authored = {item["id"]: item for item in packet["authored_evidence"]}
    for item_id in item_ids:
        _require(item_id in authored, f"item is not authored evidence: {item_id}")
        _require(authored[item_id]["availability"] == "character", f"item is not character-available: {item_id}")


def voice_status(packet: dict, *, writing_new_dialogue: bool) -> str:
    """Return the approved voice-fidelity status or block unsafe dialogue."""
    validate_packet(packet)
    _require(isinstance(writing_new_dialogue, bool), "writing_new_dialogue must be boolean")
    if "scene_presence_unverified" in packet["warnings"]:
        _require(not writing_new_dialogue, "new dialogue requires verified scene presence")
        return "voice fidelity: unverified"
    if packet["voice_constraints"]:
        return "voice fidelity: verified against supplied constraints"
    _require(not writing_new_dialogue, "new dialogue requires an authored voice constraint")
    return "voice fidelity: unverified"

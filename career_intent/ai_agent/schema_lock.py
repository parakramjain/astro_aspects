from __future__ import annotations

import copy
from typing import Any, Dict, List, Set


MUTABLE_PATH_PATTERNS: List[str] = [
    "opportunity_window.top_drivers[*]",
    "opportunity_window.drivers_detail[*].evidence_snippet",
    "caution_window.top_drivers[*]",
    "caution_window.drivers_detail[*].evidence_snippet",
    "career_intent_scores[*].short_reason",
    "career_intent_scores[*].next_step",
    "recommendation_summary[*]",
    "insight_highlights[*]",
    "window_guidance.opportunity_actions[*]",
    "window_guidance.caution_actions[*]",
    "action_plan.now_to_opportunity_start[*]",
    "action_plan.during_opportunity[*]",
    "action_plan.during_caution[*]",
    "astro_aspects[*].description",
]


def _split(path: str) -> List[str]:
    return [p for p in path.split(".") if p]


def _expand_pattern_paths(data: Any, pattern: str) -> List[str]:
    parts = _split(pattern)
    out: List[str] = []

    def walk(node: Any, idx: int, current: List[str]) -> None:
        if idx >= len(parts):
            out.append(".".join(current))
            return

        part = parts[idx]
        if part.endswith("[*]"):
            key = part[:-3]
            if not isinstance(node, dict):
                return
            arr = node.get(key)
            if not isinstance(arr, list):
                return
            for i, item in enumerate(arr):
                walk(item, idx + 1, current + [f"{key}[{i}]"])
            return

        if isinstance(node, dict) and part in node:
            walk(node[part], idx + 1, current + [part])

    walk(data, 0, [])
    return out


def _get_at_path(data: Any, path: str) -> Any:
    node = data
    for part in _split(path):
        if "[" in part and part.endswith("]"):
            key, idx_text = part[:-1].split("[", 1)
            idx = int(idx_text)
            if not isinstance(node, dict):
                raise KeyError(path)
            node = node[key]
            if not isinstance(node, list):
                raise KeyError(path)
            node = node[idx]
        else:
            if not isinstance(node, dict):
                raise KeyError(path)
            node = node[part]
    return node


def _set_at_path(data: Any, path: str, value: Any) -> None:
    parts = _split(path)
    node = data
    for part in parts[:-1]:
        if "[" in part and part.endswith("]"):
            key, idx_text = part[:-1].split("[", 1)
            idx = int(idx_text)
            node = node[key][idx]
        else:
            node = node[part]

    last = parts[-1]
    if "[" in last and last.endswith("]"):
        key, idx_text = last[:-1].split("[", 1)
        idx = int(idx_text)
        node[key][idx] = value
    else:
        node[last] = value


def _resolved_allowlist(data: Dict[str, Any], allowlist_paths: List[str] | None = None) -> Set[str]:
    patterns = allowlist_paths or MUTABLE_PATH_PATTERNS
    resolved: Set[str] = set()
    for pattern in patterns:
        resolved.update(_expand_pattern_paths(data, pattern))
    return resolved


def extract_text_fields(full_json: Dict[str, Any]) -> Dict[str, str]:
    resolved = _resolved_allowlist(full_json, MUTABLE_PATH_PATTERNS)
    out: Dict[str, str] = {}
    for path in sorted(resolved):
        try:
            value = _get_at_path(full_json, path)
        except KeyError:
            continue
        if isinstance(value, str):
            out[path] = value
    return out


def apply_text_fields(full_json: Dict[str, Any], updated_text_fields: Dict[str, str]) -> Dict[str, Any]:
    patched = copy.deepcopy(full_json)
    resolved = _resolved_allowlist(full_json, MUTABLE_PATH_PATTERNS)
    for path, value in sorted(updated_text_fields.items(), key=lambda item: item[0]):
        if path not in resolved:
            continue
        if isinstance(value, str):
            _set_at_path(patched, path, value)
    return patched


def assert_schema_and_values_unchanged(
    original: Dict[str, Any],
    updated: Dict[str, Any],
    allowlist_paths: List[str],
) -> None:
    allowed = _resolved_allowlist(original, allowlist_paths)
    violations: List[str] = []

    def walk(a: Any, b: Any, path: str) -> None:
        if type(a) is not type(b):
            violations.append(f"{path or '$'}: type changed {type(a).__name__} -> {type(b).__name__}")
            return

        if isinstance(a, dict):
            if set(a.keys()) != set(b.keys()):
                missing = sorted(set(a.keys()) - set(b.keys()))
                extra = sorted(set(b.keys()) - set(a.keys()))
                violations.append(f"{path or '$'}: keys changed missing={missing} extra={extra}")
                return
            for key in a.keys():
                child = f"{path}.{key}" if path else key
                walk(a[key], b[key], child)
            return

        if isinstance(a, list):
            if len(a) != len(b):
                violations.append(f"{path or '$'}: list length changed {len(a)} -> {len(b)}")
                return
            for idx, (av, bv) in enumerate(zip(a, b)):
                child = f"{path}[{idx}]" if path else f"[{idx}]"
                walk(av, bv, child)
            return

        if isinstance(a, str):
            if path in allowed:
                return
            if a != b:
                violations.append(f"{path or '$'}: string changed but path not allowlisted")
            return

        if a != b:
            violations.append(f"{path or '$'}: value changed")

    walk(original, updated, "")
    if violations:
        raise ValueError("Schema/value lock failed: " + " | ".join(violations[:20]))

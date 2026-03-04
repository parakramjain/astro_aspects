from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

from spend_intel_engine.domain.models import RuleMaps, ShoppingCfg, _default_data_dir
from spend_intel_engine.utils.aspect_normalizer import normalize_aspect_code


def _resolve_csv_path(path: str) -> str:
    candidate = Path(path)
    if candidate.exists():
        return str(candidate)

    data_candidate = _default_data_dir() / candidate.name
    if data_candidate.exists():
        return str(data_candidate)

    return str(candidate)


def _read_csv_map(path: str, key_col: str, val_col: str, normalize_aspect: bool) -> Dict[str, str]:
    resolved_path = _resolve_csv_path(path)
    frame = pd.read_csv(resolved_path)
    if key_col not in frame.columns or val_col not in frame.columns:
        raise ValueError(f"CSV at {resolved_path} must include columns {key_col} and {val_col}")

    output: Dict[str, str] = {}
    for _, row in frame.iterrows():
        key_raw = str(row[key_col]).strip()
        value_raw = str(row[val_col]).strip()
        if not key_raw or not value_raw:
            continue

        if normalize_aspect:
            normalized = normalize_aspect_code(key_raw)
            if normalized:
                output[normalized] = value_raw
            else:
                output[key_raw.upper()] = value_raw
        else:
            output[key_raw.upper()] = value_raw
    return output


@lru_cache(maxsize=32)
def _read_csv_map_cached(path: str, key_col: str, val_col: str, normalize_aspect: bool) -> Tuple[Tuple[str, str], ...]:
    mapped = _read_csv_map(path, key_col, val_col, normalize_aspect)
    return tuple(sorted(mapped.items()))


def _ruleset_hash(*paths: str) -> str:
    hasher = hashlib.sha256()
    for path in paths:
        content = Path(path).read_bytes()
        hasher.update(path.encode("utf-8"))
        hasher.update(content)
    return hasher.hexdigest()


@lru_cache(maxsize=16)
def _load_rule_maps_cached(
    natal_spend_aspects_csv: str,
    transit_daily_shopping_aspects_csv: str,
    natal_structure_signals_csv: str,
    moon_spending_aspects_csv: str,
) -> RuleMaps:
    natal_spend = dict(
        _read_csv_map_cached(
            natal_spend_aspects_csv,
            key_col="aspect_code",
            val_col="spend_implication",
            normalize_aspect=True,
        )
    )
    transit_daily = dict(
        _read_csv_map_cached(
            transit_daily_shopping_aspects_csv,
            key_col="aspect_code",
            val_col="day_scoring_implication",
            normalize_aspect=True,
        )
    )
    natal_structure = dict(
        _read_csv_map_cached(
            natal_structure_signals_csv,
            key_col="signal_code",
            val_col="spend_implication",
            normalize_aspect=False,
        )
    )
    moon_spending = dict(
        _read_csv_map_cached(
            moon_spending_aspects_csv,
            key_col="aspect_code",
            val_col="spending_implication",
            normalize_aspect=True,
        )
    )

    resolved_natal = _resolve_csv_path(natal_spend_aspects_csv)
    resolved_transit = _resolve_csv_path(transit_daily_shopping_aspects_csv)
    resolved_structure = _resolve_csv_path(natal_structure_signals_csv)
    resolved_moon = _resolve_csv_path(moon_spending_aspects_csv)

    ruleset_version = _ruleset_hash(
        resolved_natal,
        resolved_transit,
        resolved_structure,
        resolved_moon,
    )

    return RuleMaps(
        natal_spend_implications=natal_spend,
        transit_daily_implications=transit_daily,
        natal_structure_implications=natal_structure,
        moon_spending_implications=moon_spending,
        ruleset_version=ruleset_version,
    )


def load_rule_maps(cfg: ShoppingCfg) -> RuleMaps:
    return _load_rule_maps_cached(
        cfg.natal_spend_aspects_csv,
        cfg.transit_daily_shopping_aspects_csv,
        cfg.natal_structure_signals_csv,
        cfg.moon_spending_aspects_csv,
    )

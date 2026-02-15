from __future__ import annotations

from reporting.normalize import (
    get_lang_text,
    normalize_life_event_description,
    parse_iso_date,
)


def test_life_event_description_dict_passthrough():
    v = {"hi": ["a"], "en": ["b"]}
    assert normalize_life_event_description(v) == v


def test_life_event_description_stringified_dict():
    s = "{'en': ['A'], 'hi': ['B']}"
    out = normalize_life_event_description(s)
    assert isinstance(out, dict)
    assert out["en"] == ["A"]
    assert out["hi"] == ["B"]


def test_life_event_description_plain_string():
    s = "hello"
    assert normalize_life_event_description(s) == "hello"


def test_language_fallback_hi_to_en():
    v = {"en": "EN TEXT"}
    assert get_lang_text(v, preferred="hi", fallback="en") == "EN TEXT"


def test_date_normalization():
    assert str(parse_iso_date("2026-01-16T00:00:00Z")) == "2026-01-16"

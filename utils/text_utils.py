from __future__ import annotations

import re
from html import unescape


_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"[\t\f\r\v]+")


def strip_html(text: str) -> str:
    """Remove HTML tags and decode HTML entities in a string."""
    if not text:
        return ""
    unescaped = unescape(text)
    no_tags = _TAG_RE.sub("", unescaped)
    no_tabs = _WHITESPACE_RE.sub(" ", no_tags)
    return no_tabs

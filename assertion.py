"""
Post-extraction step 1 -- assertion tagging (Sec III-A(d)).

Annotates each span for negation, matching cues within a 50-character
left-context window. Negated spans are retained (not dropped) with their
assertion tag set, so downstream consumers can decide how to use them.
"""
from __future__ import annotations

import re
from typing import List

from models import Assertion, Span

WINDOW_CHARS = 50

_NEGATION_CUES = [
    "no", "not", "denies", "denied", "without", "absent", "absence of",
    "negative for", "no evidence of", "no signs of", "ruled out",
    "unremarkable for", "free of",
]

# sort longest-first so multi-word cues are checked before their substrings
_NEGATION_CUES_SORTED = sorted(_NEGATION_CUES, key=len, reverse=True)
_CUE_PATTERNS = [re.compile(rf"\b{re.escape(c)}\b", re.IGNORECASE) for c in _NEGATION_CUES_SORTED]


_SENTENCE_BOUNDARY_RE = re.compile(r"[.!?\n]")


def _is_negated(text: str, span_start: int) -> bool:
    window_start = max(0, span_start - WINDOW_CHARS)
    window = text[window_start:span_start]
    # don't let the cue window cross a sentence boundary: only consider
    # text after the last sentence-ending punctuation within the window
    boundary_matches = list(_SENTENCE_BOUNDARY_RE.finditer(window))
    if boundary_matches:
        window = window[boundary_matches[-1].end():]
    return any(p.search(window) for p in _CUE_PATTERNS)


def tag_assertions(text: str, spans: List[Span]) -> List[Span]:
    out = []
    for s in spans:
        if s.assertion == Assertion.PRESENT and _is_negated(text, s.start):
            out.append(_with_assertion(s, Assertion.NEGATED))
        else:
            out.append(s)
    return out


def _with_assertion(span: Span, assertion: Assertion) -> Span:
    from dataclasses import replace
    return replace(span, assertion=assertion)

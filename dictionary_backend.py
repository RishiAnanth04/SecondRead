"""
Stage 1 -- HPO dictionary backend (Appendix A.2).

Matching algorithm: tokenize once, enumerate n-grams up to length 10 from
every start position, and look each up in a pre-built inverted index under
two strategies: (1) exact lowercase match, (2) stemmed fallback using a
medical-suffix stemmer. An abbreviation pre-pass captures "(ABBR)" patterns.

Greedy longest-match-first is used so that e.g. "cleft lip and palate"
wins over the shorter "cleft lip" when both are lexicon entries.
"""
from __future__ import annotations

import re
from typing import Dict, List, Set, Tuple

from lexicon_builder import HPOLexicon
from models import Source, Span

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*")
_ABBR_RE = re.compile(r"\(([A-Z]{2,6})\)")
MAX_NGRAM = 10

_MEDICAL_SUFFIXES = [
    "omata", "oma", "itis", "itic", "ology", "ologies", "osis", "oses",
    "pathy", "pathies", "trophy", "plasia", "plasm", "ectomy", "otomy",
    "ostomy", "algia", "emia", "uria", "cyte", "genic", "gram",
]


def _stem(word: str) -> str:
    low = word.lower()
    for suf in sorted(_MEDICAL_SUFFIXES, key=len, reverse=True):
        if low.endswith(suf) and len(low) > len(suf) + 2:
            return low[: -len(suf)]
    return low


class DictionaryMatcher:
    """Builds an inverted n-gram index over the lexicon and matches text."""

    def __init__(self, lexicon: HPOLexicon, max_ngram: int = MAX_NGRAM):
        self.lexicon = lexicon
        self.max_ngram = max_ngram
        # exact index: "token token token" -> set(hp_id)
        self.exact_index: Dict[str, Set[str]] = dict(lexicon.forms)
        # stemmed index: stemmed form -> set(hp_id); built for single- and
        # multi-word forms by stemming only the trailing token, which is
        # where medical suffix variation concentrates.
        self.stemmed_index: Dict[str, Set[str]] = {}
        for form, hp_ids in lexicon.forms.items():
            toks = form.split(" ")
            stemmed_form = " ".join(toks[:-1] + [_stem(toks[-1])])
            self.stemmed_index.setdefault(stemmed_form, set()).update(hp_ids)
        # max n-gram length actually present, capped at max_ngram
        self._form_lengths = {len(f.split(" ")) for f in lexicon.forms}

    def _tokenize(self, text: str) -> List[Tuple[str, int, int]]:
        """Returns list of (token, start_char, end_char)."""
        out = []
        for m in _TOKEN_RE.finditer(text):
            out.append((m.group(0), m.start(), m.end()))
        return out

    def match(self, text: str) -> List[Span]:
        tokens = self._tokenize(text)
        n = len(tokens)
        spans: List[Span] = []
        occupied = [False] * n  # greedy longest-match-first per start index

        # try longest n-grams first so multi-word terms win over substrings
        max_len = min(self.max_ngram, n)
        for length in range(max_len, 0, -1):
            for start in range(0, n - length + 1):
                if any(occupied[start:start + length]):
                    continue
                window = tokens[start:start + length]
                surface = " ".join(t[0] for t in window)
                low = surface.lower()

                hp_ids = self.exact_index.get(low)
                matched_form = low if hp_ids else None

                if not hp_ids and length >= 1:
                    stem_key = " ".join(
                        [w.lower() for w in surface.split(" ")[:-1]]
                        + [_stem(surface.split(" ")[-1])]
                    )
                    hp_ids = self.stemmed_index.get(stem_key)
                    matched_form = stem_key if hp_ids else None

                if hp_ids:
                    char_start = window[0][1]
                    char_end = window[-1][2]
                    spans.append(Span(
                        start=char_start,
                        end=char_end,
                        text=text[char_start:char_end],
                        source=Source.HPO_DICT,
                        matched_form=matched_form,
                        hpo_candidates=tuple(sorted(hp_ids)),
                    ))
                    for i in range(start, start + length):
                        occupied[i] = True

        # abbreviation pre-pass: "(ABBR)" resolved only if ABBR itself
        # (or its expansion) is a lexicon entry
        for m in _ABBR_RE.finditer(text):
            abbr = m.group(1)
            hp_ids = self.exact_index.get(abbr.lower())
            if hp_ids:
                spans.append(Span(
                    start=m.start(1), end=m.end(1), text=abbr,
                    source=Source.HPO_DICT, matched_form=abbr.lower(),
                    hpo_candidates=tuple(sorted(hp_ids)),
                ))

        spans.sort(key=lambda s: (s.start, -(s.end - s.start)))
        return spans

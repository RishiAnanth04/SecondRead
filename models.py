"""
Core data structures for the Stage-1 phenotype span extractor.

Mirrors the paper's design: every extracted mention is a character-anchored
span carrying (a) which backend produced it, (b) an assertion tag, and
(c) optional structured metadata (used by the lab-value backend).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Assertion(str, Enum):
    PRESENT = "present"
    NEGATED = "negated"
    HISTORICAL = "historical"   # reserved for future extension
    FAMILY = "family"           # reserved for future extension
    UNCERTAIN = "uncertain"     # reserved for future extension


class Source(str, Enum):
    HPO_DICT = "hpo_dict"
    NOUN_PHRASE = "noun_phrase"
    LAB_VALUE = "lab_value"


@dataclass(frozen=True)
class Span:
    """A single character-anchored phenotype mention."""
    start: int
    end: int
    text: str          # verbatim surface text, doc[start:end]
    source: Source
    assertion: Assertion = Assertion.PRESENT
    matched_form: Optional[str] = None       # lexicon entry that matched (dict backend)
    hpo_candidates: tuple = field(default_factory=tuple)  # candidate HPO ids (dict backend only)
    lab_name: Optional[str] = None
    lab_value: Optional[str] = None
    lab_unit: Optional[str] = None

    def key(self):
        """De-duplication key: (start, end, source), per paper Sec III-A."""
        return (self.start, self.end, self.source)

    def __repr__(self):
        tag = f"[{self.assertion.value}]" if self.assertion != Assertion.PRESENT else ""
        return f"<{self.source.value}:{self.start}-{self.end} '{self.text}'{tag}>"

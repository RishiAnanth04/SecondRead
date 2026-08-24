"""
Remaining post-extraction global operations (Sec III-A(d)):

  - stoplist filtering: suppresses spans whose surface form is a valid HPO
    entry but appears as a non-phenotype modifier (inheritance terms,
    laterality modifiers, clinical-context phrases)
  - medication filter: discards spans containing medication names/dosing
    tokens
  - de-duplication by (start, end, source)

Subsumed-span removal and a junk filter are implemented but DISABLED by
default, matching the paper's ablation finding that both eliminate valid
single-token phenotypes (e.g. "scoliosis", "brachydactyly").
"""
from __future__ import annotations

from typing import List, Set

from models import Source, Span

# ---------------------------------------------------------------------------
# Stoplist: valid HPO surface forms that are usually non-phenotype modifiers
# ---------------------------------------------------------------------------
DEFAULT_STOPLIST = {
    # inheritance terminology
    "autosomal dominant", "autosomal recessive", "x-linked", "x-linked dominant",
    "x-linked recessive", "mitochondrial", "sporadic", "de novo",
    # laterality modifiers
    "bilateral", "unilateral", "left", "right", "left-sided", "right-sided",
    "symmetric", "asymmetric",
    # generic clinical-context phrases
    "onset", "progressive", "mild", "moderate", "severe", "chronic", "acute",
    "recurrent", "intermittent", "congenital", "acquired", "isolated",
    "generalized", "localized", "variable", "stable", "worsening",
}

# ---------------------------------------------------------------------------
# Medication filter
# ---------------------------------------------------------------------------
_DOSING_TOKENS = {
    "mg", "mcg", "g", "ml", "iu", "units", "tablet", "tablets", "capsule",
    "capsules", "po", "iv", "im", "sc", "bid", "tid", "qid", "qd", "prn",
    "q6h", "q8h", "q12h", "once", "daily", "twice",
}

_COMMON_MEDICATION_NAMES = {
    "acetaminophen", "ibuprofen", "aspirin", "metformin", "lisinopril",
    "atorvastatin", "levothyroxine", "amlodipine", "metoprolol",
    "omeprazole", "albuterol", "gabapentin", "hydrochlorothiazide",
    "sertraline", "losartan", "prednisone", "insulin", "warfarin",
    "furosemide", "amoxicillin", "azithromycin", "ciprofloxacin",
    "vancomycin", "morphine", "fentanyl", "oxycodone", "diazepam",
    "risperidone", "clonazepam", "carbamazepine", "valproate", "phenytoin",
    "levetiracetam", "sildenafil", "methylphenidate",
}


def build_medication_vocab(extra_medications: Set[str] | None = None) -> Set[str]:
    vocab = set(_COMMON_MEDICATION_NAMES)
    if extra_medications:
        vocab |= {m.lower() for m in extra_medications}
    return vocab


def apply_stoplist(spans: List[Span], stoplist: Set[str] | None = None) -> List[Span]:
    stoplist = stoplist or DEFAULT_STOPLIST
    out = []
    for s in spans:
        if s.source == Source.HPO_DICT and s.text.strip().lower() in stoplist:
            continue
        out.append(s)
    return out


def apply_medication_filter(spans: List[Span],
                             medication_vocab: Set[str] | None = None) -> List[Span]:
    medication_vocab = medication_vocab or build_medication_vocab()
    out = []
    for s in spans:
        toks = s.text.lower().split()
        if any(t in _DOSING_TOKENS for t in toks):
            continue
        if any(t in medication_vocab for t in toks):
            continue
        out.append(s)
    return out


def deduplicate(spans: List[Span]) -> List[Span]:
    """De-duplicate by (start, end, source) character-offset triplet,
    per Sec III-A. Keeps first occurrence."""
    seen = set()
    out = []
    for s in spans:
        k = s.key()
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
    return out


def remove_subsumed_spans(spans: List[Span]) -> List[Span]:
    """OPTIONAL / DISABLED BY DEFAULT. Drops a span if it is a strict
    substring range of another span from a different source. Ablation in
    the paper showed this eliminates valid single-token phenotypes, so the
    pipeline does not call this by default -- kept here for completeness."""
    spans_sorted = sorted(spans, key=lambda s: (s.start, -(s.end - s.start)))
    out = []
    for s in spans_sorted:
        subsumed = any(
            other is not s and other.start <= s.start and other.end >= s.end
            and (other.start, other.end) != (s.start, s.end)
            for other in spans_sorted
        )
        if not subsumed:
            out.append(s)
    return out


def junk_filter(spans: List[Span], min_alpha_chars: int = 2) -> List[Span]:
    """OPTIONAL / DISABLED BY DEFAULT. Drops spans with too few alphabetic
    characters. Kept for completeness; disabled per the paper's ablation."""
    out = []
    for s in spans:
        alpha_count = sum(1 for c in s.text if c.isalpha())
        if alpha_count >= min_alpha_chars:
            out.append(s)
    return out

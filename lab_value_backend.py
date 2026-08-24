"""
Stage 1 -- lab-value backend (Sec III-A(c)).

A cascade of compiled regular expressions identifies
lab name + numeric value + unit mentions across colon-delimited,
prose-connector, parenthetical, digit-prefix, and ratio surface forms.
HPO linking of the (lab_name, value, unit) triple is deferred to Stage 2,
so this backend only emits structured, character-anchored spans.
"""
from __future__ import annotations

import re
from typing import List

from models import Source, Span

# shared unit sub-pattern: SI units + scientific-notation prefixes
_UNIT = (
    r"(?:mg/dL|g/dL|mmol/L|µmol/L|umol/L|mEq/L|mIU/mL|mIU/L|µIU/mL|uIU/mL|"
    r"IU/L|IU/mL|U/L|ng/mL|ng/dL|pg/mL|mcg/dL|K/[uµ]L|fL|fl|"
    r"%|mg|g|kg|mL|L|mmHg|bpm|/mm3|x10\^?\d+/[uµ]?L|x10e\d+/[uµ]?L|"
    r"cells/[uµ]?L|copies/mL)"
)
_NUM = r"[-+]?\d+(?:\.\d+)?(?:\s*[eE][-+]?\d+)?"
# NOTE: uses [ \t] rather than \s so a lab-name candidate can never cross a
# line break -- multi-line EHR headers like "Jane Doe\nAGE: 34" previously
# got swallowed into a single (wrong) lab-name match.
_LAB_NAME = r"[A-Za-z][A-Za-z0-9\-\t ]{1,40}?"

_BLOCKLIST = {
    "the", "a", "an", "of", "in", "on", "for", "with", "and", "or", "at",
    "was", "were", "is", "are", "had", "has", "have", "his", "her", "its",
    "patient", "history", "note", "day", "days", "year", "years", "old",
    "chief", "complaint", "found", "showed", "revealed", "noted", "denies",
    "presents", "presented", "admitted", "discharged", "family", "review",
    "systems", "exam", "examination", "assessment", "plan", "impression",
    "normal", "abnormal", "stable", "unremarkable", "significant", "no",
    "not", "without", "vs", "per", "via", "due", "to", "including", "such",
    "as", "post", "pre", "status", "week", "weeks", "month", "months",
}

# EHR section/demographic headers that should never be treated as a lab
# name even though they're followed by "Field: value"-shaped text.
_HEADER_BLOCKLIST = {
    "patient", "age", "date", "sex", "gender", "mrn", "dob",
    "chief complaint", "history of present illness", "past medical history",
    "past surgical history", "family history", "social history",
    "review of systems", "medications", "allergies", "physical exam",
    "laboratory results", "assessment", "plan", "vitals", "vital signs",
    "name", "ssn", "id", "encounter", "provider", "visit type",
}

_PATTERNS = [
    # 1. colon-delimited: "Hemoglobin: 8.2 g/dL"
    re.compile(rf"(?P<lab>{_LAB_NAME}):\s*(?P<val>{_NUM})\s*(?P<unit>{_UNIT})?", re.IGNORECASE),
    # 2. ratio surface forms: "AST/ALT ratio of 2.1", "BUN/Cr 24"
    #    (checked early/specifically so it isn't pre-empted by the more
    #    generic prose-connector pattern below)
    re.compile(rf"(?P<lab>[A-Za-z]{{2,10}}/[A-Za-z]{{2,10}}(?:\s+ratio)?)\s*(?:of|=|:)?\s*(?P<val>{_NUM})\s*(?P<unit>{_UNIT})?", re.IGNORECASE),
    # 3. prose-connector: "hemoglobin of 8.2 g/dL" / "hemoglobin was 8.2 g/dL"
    re.compile(rf"(?P<lab>{_LAB_NAME})\s+(?:of|was|is|at|=)\s+(?P<val>{_NUM})\s*(?P<unit>{_UNIT})?", re.IGNORECASE),
    # 4. parenthetical: "hemoglobin (8.2 g/dL)"
    re.compile(rf"(?P<lab>{_LAB_NAME})\s*\(\s*(?P<val>{_NUM})\s*(?P<unit>{_UNIT})?\s*\)", re.IGNORECASE),
    # 5. digit-prefix: "8.2 g/dL hemoglobin"
    re.compile(rf"(?P<val>{_NUM})\s*(?P<unit>{_UNIT})\s+(?P<lab>{_LAB_NAME})\b", re.IGNORECASE),
    # 6. bare adjacency (no connector): "WBC 14.2 x10^9/L", "Hgb 8.2 g/dL"
    re.compile(rf"\b(?P<lab>[A-Za-z][A-Za-z0-9\-]{{1,20}})\s+(?P<val>{_NUM})\s*(?P<unit>{_UNIT})\b", re.IGNORECASE),
]


def _clean_lab_name(raw: str) -> str:
    return raw.strip(" \t\n-:").strip()


def _is_blocklisted(lab_name: str) -> bool:
    toks = re.findall(r"[a-zA-Z]+", lab_name.lower())
    if not toks:
        return True
    # reject if every content token is a generic prose word
    if all(t in _BLOCKLIST for t in toks):
        return True
    # reject exact EHR section/demographic header matches, e.g. "AGE",
    # "PATIENT", "HISTORY OF PRESENT ILLNESS"
    normalized = " ".join(toks)
    if normalized in _HEADER_BLOCKLIST:
        return True
    return False


def extract_lab_value_spans(text: str) -> List[Span]:
    spans: List[Span] = []
    occupied = [False] * len(text)

    for pattern in _PATTERNS:
        for m in pattern.finditer(text):
            start, end = m.start(), m.end()
            if any(occupied[start:end]):
                continue
            lab_name = _clean_lab_name(m.groupdict().get("lab") or "")
            if not lab_name or _is_blocklisted(lab_name):
                continue
            value = m.groupdict().get("val")
            unit = m.groupdict().get("unit")
            spans.append(Span(
                start=start, end=end, text=text[start:end],
                source=Source.LAB_VALUE,
                lab_name=lab_name, lab_value=value, lab_unit=unit,
            ))
            for i in range(start, end):
                occupied[i] = True

    spans.sort(key=lambda s: s.start)
    return spans

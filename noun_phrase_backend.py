"""
Stage 1 -- noun-phrase backend (Sec III-A(b)).

Dictionary-free recall complement: enumerates spaCy noun chunks, then
applies a two-layer filter (structural, then semantic) that favors
precision so false positives in the union stay contained.
"""
from __future__ import annotations

import re
from typing import List

import spacy

from models import Source, Span

_DIGIT_RE = re.compile(r"\d")
_NON_ALPHA_BOUNDARY_RE = re.compile(r"^[^A-Za-z]+|[^A-Za-z]+$")

# common lab / medication abbreviations that leak into noun chunks
_LAB_MED_ABBR = {
    "cbc", "bmp", "cmp", "ldl", "hdl", "tsh", "alt", "ast", "bun", "inr",
    "esr", "crp", "wbc", "rbc", "hgb", "hct", "mcv", "mchc", "pt", "ptt",
    "mri", "ct", "ekg", "ecg", "iv", "im", "po", "prn", "bid", "tid", "qid",
    "mg", "mcg", "ml", "mmol",
}

_TREATMENT_WORDS = {
    "treatment", "therapy", "medication", "dose", "dosage", "regimen",
    "prescription", "surgery", "procedure", "intervention", "management",
}

_NORMALCY_MARKERS = {
    "normal", "unremarkable", "within normal limits", "wnl", "negative",
    "intact", "grossly normal", "no abnormalities",
}

# anatomy-only nouns that need a pathology modifier to count as a phenotype
_ANATOMY_ONLY = {
    "heart", "lung", "liver", "kidney", "brain", "skin", "eye", "ear",
    "nose", "mouth", "abdomen", "chest", "spine", "joint", "muscle",
    "bone", "face", "hand", "foot", "leg", "arm",
}

_PATHOLOGY_MODIFIERS = {
    "enlarged", "swollen", "abnormal", "deformed", "malformed", "absent",
    "hypoplastic", "hyperplastic", "atrophic", "displaced", "asymmetric",
    "tender", "painful", "inflamed", "irregular", "dysplastic",
}

MIN_LEN_CHARS = 3
MAX_TOKENS = 6

_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm", disable=["ner"])
    return _nlp


def _structural_reject(chunk_text: str, n_tokens: int) -> bool:
    if _DIGIT_RE.search(chunk_text):
        return True
    stripped = _NON_ALPHA_BOUNDARY_RE.sub("", chunk_text)
    if not stripped or len(stripped) < MIN_LEN_CHARS:
        return True
    if n_tokens > MAX_TOKENS:
        return True
    lower_toks = chunk_text.lower().split()
    if any(t in _LAB_MED_ABBR for t in lower_toks):
        return True
    return False


def _semantic_reject(chunk_text: str) -> bool:
    low = chunk_text.lower().strip()
    if low in _NORMALCY_MARKERS:
        return True
    if any(marker in low for marker in _NORMALCY_MARKERS):
        return True
    toks = low.split()
    if any(t in _TREATMENT_WORDS for t in toks):
        return True
    # anatomy-only span without a pathology modifier -> reject
    if len(toks) <= 2:
        head = toks[-1]
        if head in _ANATOMY_ONLY:
            has_modifier = any(t in _PATHOLOGY_MODIFIERS for t in toks[:-1])
            if not has_modifier:
                return True
    return False


def extract_noun_phrase_spans(text: str) -> List[Span]:
    nlp = _get_nlp()
    doc = nlp(text)
    spans: List[Span] = []
    for chunk in doc.noun_chunks:
        chunk_text = chunk.text
        n_tokens = len(chunk)
        if _structural_reject(chunk_text, n_tokens):
            continue
        if _semantic_reject(chunk_text):
            continue
        spans.append(Span(
            start=chunk.start_char,
            end=chunk.end_char,
            text=chunk_text,
            source=Source.NOUN_PHRASE,
        ))
    return spans

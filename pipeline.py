"""
Stage 1 -- Phenotype Span Extraction pipeline (Sec III-A).

Runs the HPO-dictionary, noun-phrase, and lab-value backends independently,
pools their outputs, de-duplicates by (start, end, source), and applies the
shared post-extraction filters (assertion tagging, stoplist, medication
filter). Subsumed-span removal and the junk filter are disabled by default,
matching the paper.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional, Set

from assertion import tag_assertions
from dictionary_backend import DictionaryMatcher
from filters import (apply_medication_filter, apply_stoplist,
                      build_medication_vocab, deduplicate)
from hpo_obo_parser import download_hp_obo, parse_hp_obo
from lab_value_backend import extract_lab_value_spans
from lexicon_builder import DEFAULT_MANUAL_SYNONYMS, build_lexicon, HPOLexicon
from models import Span
from noun_phrase_backend import extract_noun_phrase_spans


@dataclass
class PipelineConfig:
    use_dictionary_backend: bool = True
    use_noun_phrase_backend: bool = True
    use_lab_value_backend: bool = True
    apply_stoplist_filter: bool = True
    apply_medication_filter_step: bool = True
    apply_subsumed_span_removal: bool = False  # disabled by default, per paper
    apply_junk_filter: bool = False            # disabled by default, per paper
    stoplist: Optional[Set[str]] = None
    medication_vocab: Optional[Set[str]] = None
    manual_synonyms: Optional[dict] = None


class PhenotypeExtractor:
    """End-to-end Stage 1 extractor: raw text -> assertion-tagged,
    character-anchored phenotype spans."""

    def __init__(self, lexicon: Optional[HPOLexicon] = None,
                 config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.lexicon = lexicon
        self._matcher: Optional[DictionaryMatcher] = None
        if lexicon is not None and self.config.use_dictionary_backend:
            self._matcher = DictionaryMatcher(lexicon)

    # -- construction helpers -------------------------------------------------
    @classmethod
    def from_obo(cls, obo_path: str, download_if_missing: bool = True,
                 config: Optional[PipelineConfig] = None) -> "PhenotypeExtractor":
        if download_if_missing and not os.path.exists(obo_path):
            download_hp_obo(obo_path)
        terms = parse_hp_obo(obo_path)
        cfg = config or PipelineConfig()
        lexicon = build_lexicon(terms, manual_synonyms=cfg.manual_synonyms)
        return cls(lexicon=lexicon, config=cfg)

    # -- extraction -------------------------------------------------------------
    def extract(self, text: str) -> List[Span]:
        pooled: List[Span] = []

        if self.config.use_dictionary_backend and self._matcher is not None:
            pooled.extend(self._matcher.match(text))

        if self.config.use_noun_phrase_backend:
            pooled.extend(extract_noun_phrase_spans(text))

        if self.config.use_lab_value_backend:
            pooled.extend(extract_lab_value_spans(text))

        pooled = deduplicate(pooled)
        pooled = tag_assertions(text, pooled)

        if self.config.apply_stoplist_filter:
            pooled = apply_stoplist(pooled, self.config.stoplist)

        if self.config.apply_medication_filter_step:
            vocab = self.config.medication_vocab or build_medication_vocab()
            pooled = apply_medication_filter(pooled, vocab)

        if self.config.apply_subsumed_span_removal:
            from filters import remove_subsumed_spans
            pooled = remove_subsumed_spans(pooled)

        if self.config.apply_junk_filter:
            from filters import junk_filter
            pooled = junk_filter(pooled)

        pooled.sort(key=lambda s: (s.start, s.end))
        return pooled

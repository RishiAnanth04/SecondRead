"""
Stage 1 — phenotype span extraction.

Maps raw clinical text to character-anchored, assertion-tagged phenotype
spans. Downstream stages (HPO linking, disease ranking) consume this output.
"""
from .models import Assertion, Source, Span
from .pipeline import PhenotypeExtractor, PipelineConfig

__all__ = [
    "Assertion",
    "Source",
    "Span",
    "PhenotypeExtractor",
    "PipelineConfig",
]

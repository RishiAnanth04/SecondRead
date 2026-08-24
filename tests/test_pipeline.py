from models import Assertion, Source
from pipeline import PhenotypeExtractor, PipelineConfig


def test_pipeline_extracts_and_dedupes(fixture_lexicon):
    extractor = PhenotypeExtractor(lexicon=fixture_lexicon)
    text = "Patient has microcephaly and denies seizures."
    spans = extractor.extract(text)

    # dedup key is (start, end, source), so the dict and noun-phrase
    # backends may both legitimately report the same surface text --
    # check per-source rather than expecting a single global match.
    micro = [s for s in spans if s.text.lower() == "microcephaly"
             and s.source == Source.HPO_DICT]
    assert len(micro) == 1
    assert micro[0].assertion == Assertion.PRESENT

    seiz = [s for s in spans if s.text.lower() == "seizures"
            and s.source == Source.HPO_DICT]
    assert len(seiz) == 1
    assert seiz[0].assertion == Assertion.NEGATED


def test_pipeline_applies_stoplist_end_to_end(fixture_lexicon):
    extractor = PhenotypeExtractor(lexicon=fixture_lexicon)
    # "autosomal dominant" (as a bare modifier) is on the default stoplist;
    # the longer phrase "autosomal dominant inheritance" is a real HPO
    # term name and is intentionally NOT stoplisted.
    spans = extractor.extract("Inheritance pattern was autosomal dominant.")
    dict_hits = [s for s in spans if s.source == Source.HPO_DICT]
    assert dict_hits == []


def test_pipeline_applies_medication_filter_end_to_end(fixture_lexicon):
    extractor = PhenotypeExtractor(lexicon=fixture_lexicon)
    spans = extractor.extract("Started on amoxicillin 500 mg PO TID.")
    assert all("amoxicillin" not in s.text.lower() for s in spans)


def test_pipeline_lab_value_backend_runs(fixture_lexicon):
    extractor = PhenotypeExtractor(lexicon=fixture_lexicon)
    spans = extractor.extract("Hemoglobin: 8.2 g/dL.")
    lab_spans = [s for s in spans if s.source == Source.LAB_VALUE]
    assert len(lab_spans) == 1
    assert lab_spans[0].lab_value == "8.2"


def test_pipeline_subsumed_and_junk_filters_disabled_by_default(fixture_lexicon):
    config = PipelineConfig()
    assert config.apply_subsumed_span_removal is False
    assert config.apply_junk_filter is False
    # single-token phenotypes must survive the default pipeline
    extractor = PhenotypeExtractor(lexicon=fixture_lexicon, config=config)
    spans = extractor.extract("The patient has cyanosis.")
    assert any(s.text.lower() == "cyanosis" for s in spans)


def test_pipeline_can_disable_individual_backends(fixture_lexicon):
    config = PipelineConfig(use_noun_phrase_backend=False, use_lab_value_backend=False)
    extractor = PhenotypeExtractor(lexicon=fixture_lexicon, config=config)
    spans = extractor.extract("Hemoglobin: 8.2 g/dL and joint pain noted.")
    assert all(s.source == Source.HPO_DICT for s in spans)


def test_output_spans_are_sorted_by_offset(fixture_lexicon):
    extractor = PhenotypeExtractor(lexicon=fixture_lexicon)
    spans = extractor.extract("Cyanosis noted. Later, microcephaly confirmed.")
    starts = [s.start for s in spans]
    assert starts == sorted(starts)

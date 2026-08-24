from filters import (apply_medication_filter, apply_stoplist,
                      build_medication_vocab, deduplicate, junk_filter,
                      remove_subsumed_spans)
from models import Source, Span


def _span(text, start, end, source=Source.HPO_DICT):
    return Span(start=start, end=end, text=text, source=source)


def test_stoplist_removes_inheritance_terminology():
    spans = [_span("autosomal dominant", 0, 19)]
    out = apply_stoplist(spans)
    assert out == []


def test_stoplist_keeps_true_phenotypes():
    spans = [_span("microcephaly", 0, 12)]
    out = apply_stoplist(spans)
    assert len(out) == 1


def test_stoplist_only_applies_to_dict_backend_spans():
    # a noun-phrase span with stoplisted text should NOT be removed --
    # the stoplist targets dictionary-backend false positives specifically
    spans = [_span("bilateral", 0, 9, source=Source.NOUN_PHRASE)]
    out = apply_stoplist(spans)
    assert len(out) == 1


def test_medication_filter_removes_dosing_tokens():
    spans = [_span("ibuprofen 200 mg", 0, 16)]
    out = apply_medication_filter(spans)
    assert out == []


def test_medication_filter_removes_known_medication_name():
    spans = [_span("started on amoxicillin", 0, 22)]
    out = apply_medication_filter(spans)
    assert out == []


def test_medication_filter_keeps_non_medication_spans():
    spans = [_span("productive cough", 0, 16)]
    out = apply_medication_filter(spans)
    assert len(out) == 1


def test_deduplicate_by_start_end_source():
    a = _span("cough", 0, 5)
    b = _span("cough", 0, 5)  # identical key
    c = _span("cough", 0, 5, source=Source.NOUN_PHRASE)  # different source, kept
    out = deduplicate([a, b, c])
    assert len(out) == 2


def test_subsumed_span_removal_drops_shorter_overlap():
    outer = _span("shortness of breath", 0, 20)
    inner = _span("breath", 14, 20, source=Source.NOUN_PHRASE)
    out = remove_subsumed_spans([outer, inner])
    assert inner not in out
    assert outer in out


def test_junk_filter_drops_low_alpha_spans():
    junk = _span("--", 0, 2)
    real = _span("pain", 0, 4)
    out = junk_filter([junk, real])
    assert junk not in out
    assert real in out

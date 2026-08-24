from assertion import tag_assertions
from models import Assertion, Source, Span


def _span(text, start, end):
    return Span(start=start, end=end, text=text, source=Source.HPO_DICT)


def test_negation_cue_within_window_tags_negated():
    text = "Patient denies fever on exam."
    fever_start = text.index("fever")
    fever_end = fever_start + len("fever")
    spans = [_span("fever", fever_start, fever_end)]
    out = tag_assertions(text, spans)
    assert out[0].assertion == Assertion.NEGATED


def test_no_cue_leaves_present():
    text = "Patient reports fever on exam."
    fever_start = text.index("fever")
    fever_end = fever_start + len("fever")
    spans = [_span("fever", fever_start, fever_end)]
    out = tag_assertions(text, spans)
    assert out[0].assertion == Assertion.PRESENT


def test_negation_does_not_cross_sentence_boundary():
    text = "No fever. Cough noted on exam."
    cough_start = text.index("Cough")
    cough_end = cough_start + len("Cough")
    spans = [_span("Cough", cough_start, cough_end)]
    out = tag_assertions(text, spans)
    assert out[0].assertion == Assertion.PRESENT


def test_negation_within_same_sentence_after_period():
    text = "Exam notable. No cyanosis observed."
    cyan_start = text.index("cyanosis")
    cyan_end = cyan_start + len("cyanosis")
    spans = [_span("cyanosis", cyan_start, cyan_end)]
    out = tag_assertions(text, spans)
    assert out[0].assertion == Assertion.NEGATED


def test_multiword_cue_without_evidence_of():
    text = "There is no evidence of seizures."
    sz_start = text.index("seizures")
    sz_end = sz_start + len("seizures")
    spans = [_span("seizures", sz_start, sz_end)]
    out = tag_assertions(text, spans)
    assert out[0].assertion == Assertion.NEGATED

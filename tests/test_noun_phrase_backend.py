from noun_phrase_backend import extract_noun_phrase_spans


def test_extracts_a_plausible_phenotype_phrase():
    spans = extract_noun_phrase_spans("The patient has severe joint pain.")
    texts = [s.text.lower() for s in spans]
    assert any("joint pain" in t for t in texts)


def test_rejects_spans_containing_digits():
    spans = extract_noun_phrase_spans("Blood pressure was 120 mmHg today.")
    assert all(not any(c.isdigit() for c in s.text) for s in spans)


def test_rejects_lab_abbreviations():
    spans = extract_noun_phrase_spans("CBC and TSH were within normal limits.")
    texts = [s.text.lower() for s in spans]
    assert not any("cbc" in t or "tsh" in t for t in texts)


def test_rejects_normalcy_markers():
    spans = extract_noun_phrase_spans("Cardiac exam was unremarkable.")
    texts = [s.text.lower() for s in spans]
    assert not any("unremarkable" in t for t in texts)


def test_rejects_treatment_framing():
    spans = extract_noun_phrase_spans("Patient started physical therapy.")
    texts = [s.text.lower() for s in spans]
    assert not any("therapy" in t for t in texts)


def test_rejects_bare_anatomy_without_pathology_modifier():
    spans = extract_noun_phrase_spans("The heart was examined.")
    texts = [s.text.lower() for s in spans]
    assert "the heart" not in texts and "heart" not in texts


def test_keeps_anatomy_with_pathology_modifier():
    spans = extract_noun_phrase_spans("An enlarged heart was noted on exam.")
    texts = [s.text.lower() for s in spans]
    assert any("enlarged heart" in t for t in texts)

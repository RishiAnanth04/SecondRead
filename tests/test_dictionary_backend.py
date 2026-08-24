from models import Source


def test_matches_canonical_term(fixture_matcher):
    spans = fixture_matcher.match("The patient has microcephaly.")
    matched = [s for s in spans if s.text.lower() == "microcephaly"]
    assert len(matched) == 1
    assert "HP:0000252" in matched[0].hpo_candidates
    assert matched[0].source == Source.HPO_DICT


def test_matches_inflected_plural_form(fixture_matcher):
    spans = fixture_matcher.match("Recurrent seizures were reported.")
    matched = [s for s in spans if s.text.lower() == "seizures"]
    assert len(matched) == 1
    assert "HP:0001250" in matched[0].hpo_candidates


def test_greedy_longest_match_wins(fixture_matcher):
    # "Global developmental delay" is a 3-token lexicon entry; the matcher
    # should return the full phrase, not just a substring token.
    spans = fixture_matcher.match("Child has global developmental delay.")
    texts = [s.text.lower() for s in spans]
    assert "global developmental delay" in texts


def test_no_false_match_on_unrelated_text(fixture_matcher):
    spans = fixture_matcher.match("The weather today is sunny and warm.")
    assert spans == []


def test_span_offsets_are_character_accurate(fixture_matcher):
    text = "History: cyanosis noted on exam."
    spans = fixture_matcher.match(text)
    cyanosis_spans = [s for s in spans if s.text.lower() == "cyanosis"]
    assert len(cyanosis_spans) == 1
    s = cyanosis_spans[0]
    assert text[s.start:s.end] == s.text

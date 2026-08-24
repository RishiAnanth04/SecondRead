from lexicon_builder import build_lexicon, _inflect_surface_form, _template_paraphrases


def test_layer1_contains_canonical_name(fixture_terms):
    lex = build_lexicon(fixture_terms)
    assert "HP:0000252" in lex.forms["microcephaly"]


def test_layer1_excludes_broad_synonyms_by_default(fixture_terms):
    lex = build_lexicon(fixture_terms)
    # "Abnormally small head" is BROAD on HP:0000252 in the real ontology;
    # it should NOT be indexed unless include_broad=True
    assert "abnormally small head" not in lex.forms


def test_include_broad_flag_adds_broad_synonyms(fixture_terms):
    lex = build_lexicon(fixture_terms, include_broad=True)
    assert "HP:0000252" in lex.forms.get("abnormally small head", set())


def test_layer2_inflection_adds_plural_form(fixture_terms):
    lex = build_lexicon(fixture_terms)
    # "Seizure" -> "seizures"
    assert "HP:0001250" in lex.forms["seizures"]


def test_layer2_us_uk_spelling_variants():
    variants = _inflect_surface_form("oedema")
    assert "edema" in variants


def test_layer3_abnormality_of_paraphrase():
    paras = _template_paraphrases("Abnormality of the tongue")
    assert "tongue abnormality" in paras
    assert "abnormal tongue" in paras


def test_layer3_paraphrases_indexed_in_lexicon(fixture_terms):
    lex = build_lexicon(fixture_terms)
    assert "HP:0100022" in lex.forms.get("abnormal movement", set())


def test_layer4_manual_synonym_present(fixture_terms):
    lex = build_lexicon(fixture_terms)
    assert "HP:0009902" in lex.forms.get("earpit", set())


def test_layers_are_cumulative(fixture_terms):
    lex = build_lexicon(fixture_terms)
    counts = lex.layer_counts
    assert counts["layer1_canonical"] <= counts["layer2_inflection"]
    assert counts["layer2_inflection"] <= counts["layer3_paraphrases"]
    assert counts["layer3_paraphrases"] <= counts["layer4_manual"]

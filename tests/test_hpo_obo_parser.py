from hpo_obo_parser import parse_hp_obo
from conftest import FIXTURE_OBO


def test_parses_expected_term_count():
    terms = parse_hp_obo(FIXTURE_OBO)
    assert len(terms) == 14


def test_term_has_correct_id_and_name():
    terms = parse_hp_obo(FIXTURE_OBO)
    assert "HP:0000252" in terms
    assert terms["HP:0000252"].name == "Microcephaly"


def test_synonym_scopes_are_captured():
    terms = parse_hp_obo(FIXTURE_OBO)
    hearing = terms["HP:0000365"]
    assert "Hearing loss" in hearing.synonyms["RELATED"]
    assert "Deafness" in hearing.synonyms["EXACT"]
    # BROAD synonyms should be parsed but not merged into EXACT/etc.
    all_exact_narrow_related = (
        hearing.synonyms["EXACT"] + hearing.synonyms["NARROW"]
        + hearing.synonyms["RELATED"]
    )
    assert "Hearing defect" in all_exact_narrow_related


def test_no_obsolete_terms_in_fixture():
    terms = parse_hp_obo(FIXTURE_OBO)
    assert all(not t.is_obsolete for t in terms.values())

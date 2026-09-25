import os

import pytest

FIXTURE_OBO = os.path.join(os.path.dirname(__file__), "fixtures", "mini_hp.obo")


@pytest.fixture(scope="session")
def fixture_terms():
    from stage1.hpo_obo_parser import parse_hp_obo
    return parse_hp_obo(FIXTURE_OBO)


@pytest.fixture(scope="session")
def fixture_lexicon(fixture_terms):
    from stage1.lexicon_builder import build_lexicon
    return build_lexicon(fixture_terms)


@pytest.fixture(scope="session")
def fixture_matcher(fixture_lexicon):
    from stage1.dictionary_backend import DictionaryMatcher
    return DictionaryMatcher(fixture_lexicon)


@pytest.fixture(scope="session")
def fixture_extractor(fixture_lexicon):
    from stage1 import PhenotypeExtractor, PipelineConfig
    return PhenotypeExtractor(lexicon=fixture_lexicon, config=PipelineConfig())

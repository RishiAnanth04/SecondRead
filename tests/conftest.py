import os
import sys

import pytest

# make the project root importable when running `pytest` from the repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FIXTURE_OBO = os.path.join(os.path.dirname(__file__), "fixtures", "mini_hp.obo")


@pytest.fixture(scope="session")
def fixture_terms():
    from hpo_obo_parser import parse_hp_obo
    return parse_hp_obo(FIXTURE_OBO)


@pytest.fixture(scope="session")
def fixture_lexicon(fixture_terms):
    from lexicon_builder import build_lexicon
    return build_lexicon(fixture_terms)


@pytest.fixture(scope="session")
def fixture_matcher(fixture_lexicon):
    from dictionary_backend import DictionaryMatcher
    return DictionaryMatcher(fixture_lexicon)


@pytest.fixture(scope="session")
def fixture_extractor(fixture_lexicon):
    from pipeline import PhenotypeExtractor, PipelineConfig
    return PhenotypeExtractor(lexicon=fixture_lexicon, config=PipelineConfig())

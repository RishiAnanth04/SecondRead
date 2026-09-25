"""Repo-root smoke test — delegates to Stage 1 example."""
from stage1.example import NOTE
from stage1 import PhenotypeExtractor

if __name__ == "__main__":
    extractor = PhenotypeExtractor.from_obo("hp.obo")
    spans = extractor.extract(NOTE)
    for s in spans:
        print(s)

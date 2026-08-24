# Phenotype Span Extractor (Stage 1)

A standalone implementation of **Stage 1** from *"An Auditable, Correctable
Pipeline for Rare-Disease Diagnosis from Clinical Text"* (Kang, Wang, et al.).
It maps raw clinical text to **character-anchored, assertion-tagged
phenotype spans** — the input Stage 2 (HPO linking) and Stage 3 (disease
ranking) would consume in the full pipeline.

## Architecture

Three backends run independently and are pooled, de-duplicated by
`(start, end, source)`, then passed through shared post-extraction filters:

```
                     ┌─────────────────────┐
                     │   raw clinical text  │
                     └──────────┬───────────┘
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
 HPO dictionary        noun-phrase           lab-value
   backend               backend               backend
 (lexicon lookup)     (spaCy chunks +       (regex cascade:
  4-layer surface       structural/          colon, prose,
  form index over        semantic filter)     parenthetical,
  hp.obo)                                     digit-prefix,
        │                     │               ratio, bare)
        └─────────────────────┼─────────────────────┘
                               ▼
                    pool + de-duplicate
                               ▼
                    assertion tagging (negation)
                               ▼
                    stoplist filter (dict backend only)
                               ▼
                    medication filter
                               ▼
                 assertion-tagged, char-anchored spans
```

### 1. HPO dictionary backend (`lexicon_builder.py`, `dictionary_backend.py`)

Builds a 4-layer surface-form lexicon from `hp.obo`:

1. **Canonical names + synonyms** — term names plus EXACT/NARROW/RELATED
   synonyms (BROAD excluded).
2. **Morphological inflection** — pluralization/singularization
   (regular, Latin/Greek `-us/-i`, `-um/-a`, `-is/-es`, `-oma/-omata`) plus
   ~18 US/UK spelling pairs (haem/hem, oedema/edema, ...).
3. **Template paraphrases** — structural rewrites absent from `hp.obo`
   synonyms: `"Abnormality of X"` → `"X abnormality/anomaly/disorder/..."`,
   `"Type N X"` ↔ `"X type N"`, and organ noun→adjective expansion
   (eye→ocular, kidney→renal, ...).
4. **Manual legacy synonyms** — a small hand-curated table for deprecated
   terms (`earpit`, `happy puppet`, ...); extend via `--manual-synonyms
   file.tsv` (`term<TAB>HP:id` per line).

Matching uses a token n-gram hash index (greedy, longest-match-first, up to
10-token windows) with an exact-match pass and a medical-suffix-stemmed
fallback pass, plus a `(ABBR)` pre-pass for parenthetical abbreviations.

### 2. Noun-phrase backend (`noun_phrase_backend.py`)

Dictionary-free recall complement using spaCy's dependency parser
(`en_core_web_sm`, NER disabled) to enumerate noun chunks, then:
- **structural filter**: rejects chunks with digits, non-alphabetic
  boundaries, lab/medication abbreviations, or >6 tokens;
- **semantic filter**: rejects normalcy markers ("unremarkable", "WNL"),
  treatment framings ("medication", "therapy"), and anatomy-only spans
  lacking a pathology modifier ("the heart" vs. "enlarged heart").

### 3. Lab-value backend (`lab_value_backend.py`)

A regex cascade over six surface forms: colon-delimited
(`"Hgb: 8.2 g/dL"`), prose-connector (`"hemoglobin of 8.2 g/dL"`),
parenthetical (`"creatinine (1.4 mg/dL)"`), digit-prefix
(`"8.2 g/dL hemoglobin"`), ratio (`"AST/ALT ratio of 2.1"`), and bare
adjacency (`"WBC 14.2 x10^9/L"`). A ~90-word blocklist suppresses false
fires on ordinary prose. HPO linking of the `(lab_name, value, unit)`
triple is deliberately deferred to Stage 2.

### 4. Post-extraction filters (`assertion.py`, `filters.py`)

- **Assertion tagging**: negation cues (`no`, `not`, `denies`, `without`,
  `absent`, `negative for`, ...) within a 50-character left-context
  window, clipped at the nearest sentence boundary so negation doesn't
  leak across sentences. Negated spans are **kept**, not dropped.
- **Stoplist filtering**: suppresses HPO-valid surface forms that are
  usually non-phenotype modifiers (inheritance terminology, laterality,
  generic severity/onset words).
- **Medication filter**: discards spans containing medication names or
  dosing tokens (`mg`, `PO`, `BID`, ...).
- **Subsumed-span removal / junk filter**: implemented in `filters.py`
  but **disabled by default** — the paper found both eliminate valid
  single-token phenotypes (e.g. "scoliosis").

## Usage

```bash
pip install -r requirements.txt

# hp.obo is downloaded automatically on first run if not present
python cli.py --text "Patient has microcephaly and denies seizures." --json

# or from a file
python cli.py --file note.txt

# reuse an already-downloaded hp.obo
python cli.py --obo hp.obo --no-download --file note.txt
```

Programmatic use:

```python
from pipeline import PhenotypeExtractor

extractor = PhenotypeExtractor.from_obo("hp.obo")  # downloads if missing
spans = extractor.extract("Patient has microcephaly and denies seizures.")

for s in spans:
    print(s.source.value, s.start, s.end, s.text, s.assertion.value, s.hpo_candidates)
```

## Tests

The `tests/` directory has 54 pytest unit + integration tests covering
every module. They run against `tests/fixtures/mini_hp.obo`, a small
14-term excerpt of the real ontology, so the suite is fast (~2s) and needs
**no network access** and **no full hp.obo download**.

```bash
pip install -r requirements.txt   # needed once, for spaCy + pytest
python -m pytest -v               # run everything (uses PYTHONPATH via pytest.ini)
python -m pytest tests/test_lab_value_backend.py -v   # run one module's tests
python -m pytest -k "negation"    # run tests matching a keyword
```

What's covered:

| Test file | Covers |
|---|---|
| `test_hpo_obo_parser.py` | `.obo` parsing: term count, names, synonym scopes, obsolete filtering |
| `test_lexicon_builder.py` | All 4 lexicon layers (canonical/BROAD exclusion, inflection, US/UK spelling, paraphrases, manual synonyms), layer cumulativeness |
| `test_dictionary_backend.py` | Exact match, plural/inflected match, greedy longest-match-first, no false positives, char-offset accuracy |
| `test_noun_phrase_backend.py` | Structural filter (digits, lab abbreviations), semantic filter (normalcy markers, treatment framing, bare anatomy) |
| `test_lab_value_backend.py` | All 6 regex surface forms, blocklist false-positive suppression, no overlapping spans |
| `test_assertion.py` | Negation cue detection, sentence-boundary clipping, multi-word cues |
| `test_filters.py` | Stoplist (dict-backend-only scope), medication filter, dedup key, (disabled-by-default) subsumed-span removal and junk filter |
| `test_pipeline.py` | Full end-to-end extraction, filters applied in sequence, backend toggling, output ordering |

If you want to test against the **real, full-size** `hp.obo` instead of the
fixture (e.g. to sanity-check layer counts match the paper's reported
41,961 → 88,857 → 136,521 → +26), just run `example.py` or the CLI --
they download and use the real file automatically.


## Notes on fidelity to the paper

This reproduces the **architecture and design choices** of Stage 1
(multi-backend union, 4-layer lexicon, assertion window, stoplist/
medication filters, disabled subsumed/junk filters) as described in
Section III-A and Appendix A. It does **not** reproduce the paper's exact
GSC+ stoplist or medication vocabulary (those were derived from a
201-abstract training partition not included in the paper), and the
manual-synonym layer ships only a few illustrative entries — both are
easy to extend by editing `filters.DEFAULT_STOPLIST`,
`filters.build_medication_vocab()`, or passing a TSV via
`lexicon_builder.load_manual_synonyms_tsv()`.

Stage 1 output here is the natural handoff point to a Stage 2 HPO linker
(e.g. a SapBERT bi-encoder, as in the paper) — this repo stops at
character-anchored, assertion-tagged spans plus (for dictionary-backend
hits) candidate HPO IDs.

## Files

| File | Purpose |
|---|---|
| `models.py` | `Span`, `Assertion`, `Source` data structures |
| `hpo_obo_parser.py` | Downloads/parses `hp.obo` |
| `lexicon_builder.py` | 4-layer surface-form lexicon |
| `dictionary_backend.py` | N-gram hash lookup matcher |
| `noun_phrase_backend.py` | spaCy noun-chunk backend |
| `lab_value_backend.py` | Regex-cascade lab-value backend |
| `assertion.py` | Negation/assertion tagging |
| `filters.py` | Stoplist, medication filter, dedup, (disabled) subsumed/junk filters |
| `pipeline.py` | Orchestrates backends + filters into `PhenotypeExtractor` |
| `cli.py` | Command-line entry point |

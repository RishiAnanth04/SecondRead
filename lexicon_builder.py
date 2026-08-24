"""
Builds the multi-layer HPO surface-form lexicon described in the paper
(Sec III-A / Appendix A):

  Layer 1 -- canonical names + EXACT/NARROW/RELATED synonyms
  Layer 2 -- rule-based morphological inflection (plurals, US/UK spelling)
  Layer 3 -- template paraphrases for structural patterns absent from hp.obo
  Layer 4 -- hand-curated legacy synonyms for deprecated terms

Each layer maps surface_form(lowercased) -> set(HP:ids). The layers are
cumulative: later layers add forms without removing earlier ones.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, Set

from hpo_obo_parser import HPOTerm

# ---------------------------------------------------------------------------
# Layer 2: morphological inflection
# ---------------------------------------------------------------------------

_US_UK_PAIRS = [
    ("haem", "hem"), ("oedema", "edema"), ("anaemia", "anemia"),
    ("naevus", "nevus"), ("leukaemia", "leukemia"), ("oesophag", "esophag"),
    ("orthopaedic", "orthopedic"), ("paediatric", "pediatric"),
    ("caecum", "cecum"), ("faeces", "feces"), ("diarrhoea", "diarrhea"),
    ("foetus", "fetus"), ("gynaecolog", "gynecolog"), ("haemat", "hemat"),
    ("hyperaemia", "hyperemia"), ("ischaemia", "ischemia"),
    ("oestrogen", "estrogen"), ("anaesthesia", "anesthesia"),
]


def _us_uk_variants(word: str) -> Set[str]:
    out = {word}
    low = word.lower()
    for uk, us in _US_UK_PAIRS:
        if uk in low:
            out.add(re.sub(uk, us, word, flags=re.IGNORECASE))
        if us in low:
            out.add(re.sub(us, uk, word, flags=re.IGNORECASE))
    return out


def _pluralize_singularize(word: str) -> Set[str]:
    """Rule-based plural/singular inflection for the trailing word only."""
    out = {word}
    w = word

    # Latin / Greek endings
    if w.endswith("us") and len(w) > 3:
        out.add(w[:-2] + "i")                 # radius -> radii
    if w.endswith("i") and len(w) > 2:
        out.add(w[:-1] + "us")
    if w.endswith("um") and len(w) > 3:
        out.add(w[:-2] + "a")                  # ganglion... / datum->data style
    if w.endswith("a") and len(w) > 2:
        out.add(w[:-1] + "um")
    if w.endswith("is") and len(w) > 3:
        out.add(w[:-2] + "es")                 # diagnosis -> diagnoses
    if w.endswith("es") and len(w) > 3 and w[:-2].endswith("i"):
        out.add(w[:-2] + "s")
    if w.endswith("oma"):
        out.add(w + "ta")
        out.add(w + "s")
    if w.endswith("omata"):
        out.add(w[:-2])
    if w.endswith("omas"):
        out.add(w[:-1] + "ta")

    # Regular English pluralization
    if re.search(r"[^aeiou]y$", w):
        out.add(w[:-1] + "ies")                # anomaly -> anomalies
    if w.endswith("ies"):
        out.add(w[:-3] + "y")
    if w.endswith(("s", "x", "z", "ch", "sh")):
        out.add(w + "es")
    else:
        out.add(w + "s")
    if w.endswith("s") and not w.endswith("ss"):
        out.add(w[:-1])

    return out


def _inflect_surface_form(form: str) -> Set[str]:
    """Inflect only the trailing word of a multi-word surface form,
    per the paper's Layer-2 description, and also add US/UK spelling
    variants applied to the whole string."""
    variants = {form}
    tokens = form.split(" ")
    if tokens:
        last = tokens[-1]
        for inflected_last in _pluralize_singularize(last):
            variants.add(" ".join(tokens[:-1] + [inflected_last]).strip())
    spelling_variants = set()
    for v in list(variants):
        spelling_variants |= _us_uk_variants(v)
    variants |= spelling_variants
    return variants


# ---------------------------------------------------------------------------
# Layer 3: template paraphrases
# ---------------------------------------------------------------------------

_ABNORMALITY_OF_RE = re.compile(r"^abnormality of (the )?(.+)$", re.IGNORECASE)
_TYPE_N_PREFIX_RE = re.compile(r"^type (\w+) (.+)$", re.IGNORECASE)
_TYPE_N_SUFFIX_RE = re.compile(r"^(.+) type (\w+)$", re.IGNORECASE)

_ORGAN_ADJECTIVES = {
    "eye": ["ocular", "ophthalmic"], "brain": ["cerebral", "encephalic"],
    "kidney": ["renal"], "heart": ["cardiac"], "liver": ["hepatic"],
    "lung": ["pulmonary"], "skin": ["cutaneous", "dermal"], "bone": ["osseous"],
    "muscle": ["muscular"], "nerve": ["neural", "neuronal"],
    "blood": ["hematologic", "hematological"], "stomach": ["gastric"],
    "tooth": ["dental"], "ear": ["otic", "auricular"], "nose": ["nasal"],
    "mouth": ["oral"], "tongue": ["lingual"], "spine": ["spinal", "vertebral"],
    "joint": ["articular"], "vein": ["venous"],
}


def _abnormality_of_paraphrases(name: str) -> Set[str]:
    out = set()
    m = _ABNORMALITY_OF_RE.match(name)
    if m:
        x = m.group(2).strip()
        out.add(f"{x} abnormality")
        out.add(f"{x} anomaly")
        out.add(f"{x} disorder")
        out.add(f"{x} defect")
        out.add(f"{x} dysfunction")
        out.add(f"abnormal {x}")
        # naive plurals of the paraphrase head noun
        for suffix in ("abnormalities", "anomalies", "disorders", "defects",
                       "dysfunctions"):
            head = suffix.rstrip("s")
            out.add(f"{x} {suffix}")
    return out


def _type_n_paraphrases(name: str) -> Set[str]:
    out = set()
    m = _TYPE_N_PREFIX_RE.match(name)
    if m:
        n, rest = m.group(1), m.group(2).strip()
        out.add(f"{rest} type {n}")
    m = _TYPE_N_SUFFIX_RE.match(name)
    if m:
        rest, n = m.group(1).strip(), m.group(2)
        out.add(f"type {n} {rest}")
    return out


def _organ_adjective_paraphrases(name: str) -> Set[str]:
    out = set()
    low = name.lower()
    for noun, adjs in _ORGAN_ADJECTIVES.items():
        if re.search(rf"\b{noun}\b", low):
            for adj in adjs:
                out.add(re.sub(rf"\b{noun}\b", adj, name, flags=re.IGNORECASE))
    return out


def _template_paraphrases(name: str) -> Set[str]:
    out = set()
    out |= _abnormality_of_paraphrases(name)
    out |= _type_n_paraphrases(name)
    out |= _organ_adjective_paraphrases(name)
    return out


# ---------------------------------------------------------------------------
# Layer 4: manual legacy synonyms
# ---------------------------------------------------------------------------
# A small starter set illustrating the paper's examples (earpit, happy
# puppet, bouts of laughter). Extend via a TSV: term<TAB>HP:id
DEFAULT_MANUAL_SYNONYMS = {
    "earpit": "HP:0009902",            # preauricular pit
    "ear pit": "HP:0009902",
    "happy puppet": "HP:0001262",      # historical name area (Angelman-related sx); placeholder mapping
    "bouts of laughter": "HP:0000749", # inappropriate laughter (approx.)
}


def load_manual_synonyms_tsv(path: str) -> Dict[str, str]:
    mapping = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                mapping[parts[0].strip().lower()] = parts[1].strip()
    return mapping


# ---------------------------------------------------------------------------
# Lexicon assembly
# ---------------------------------------------------------------------------

class HPOLexicon:
    """surface_form(lower) -> set(HP:id), built cumulatively across 4 layers."""

    def __init__(self):
        self.forms: Dict[str, Set[str]] = defaultdict(set)
        self.term_names: Dict[str, str] = {}
        self.layer_counts = {}

    def add(self, form: str, hp_id: str):
        form = form.strip()
        if not form:
            return
        self.forms[form.lower()].add(hp_id)

    def __len__(self):
        return len(self.forms)


def build_lexicon(terms: Dict[str, HPOTerm],
                   manual_synonyms: Dict[str, str] | None = None,
                   include_broad: bool = False) -> HPOLexicon:
    lex = HPOLexicon()

    # ---- Layer 1: canonical names + EXACT/NARROW/RELATED synonyms ----
    before = 0
    for hp_id, term in terms.items():
        if term.is_obsolete or not term.name:
            continue
        lex.term_names[hp_id] = term.name
        lex.add(term.name, hp_id)
        scopes = ["EXACT", "NARROW", "RELATED"] + (["BROAD"] if include_broad else [])
        for scope in scopes:
            for syn in term.synonyms.get(scope, []):
                lex.add(syn, hp_id)
    lex.layer_counts["layer1_canonical"] = len(lex.forms)

    # ---- Layer 2: morphological inflection ----
    layer1_forms = list(lex.forms.items())
    for form, hp_ids in layer1_forms:
        for variant in _inflect_surface_form(form):
            for hp_id in hp_ids:
                lex.add(variant, hp_id)
    lex.layer_counts["layer2_inflection"] = len(lex.forms)

    # ---- Layer 3: template paraphrases (built off canonical names) ----
    for hp_id, term in terms.items():
        if term.is_obsolete or not term.name:
            continue
        for para in _template_paraphrases(term.name):
            lex.add(para, hp_id)
            # also inflect the paraphrase's trailing word
            for variant in _inflect_surface_form(para):
                lex.add(variant, hp_id)
    lex.layer_counts["layer3_paraphrases"] = len(lex.forms)

    # ---- Layer 4: manual legacy synonyms ----
    manual_synonyms = manual_synonyms or DEFAULT_MANUAL_SYNONYMS
    for form, hp_id in manual_synonyms.items():
        lex.add(form, hp_id)
    lex.layer_counts["layer4_manual"] = len(lex.forms)

    return lex

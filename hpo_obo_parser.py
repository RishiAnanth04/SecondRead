"""
A minimal, dependency-free parser for the HPO's .obo file.

We only need [Term] stanzas: id, name, synonym (with scope), is_obsolete.
This avoids pulling in a full OBO/OWL library for what the paper's Stage 1
dictionary backend actually consumes: names + EXACT/NARROW/RELATED synonyms.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List
from urllib.request import Request, urlopen

HPO_OBO_URL = (
    "https://raw.githubusercontent.com/obophenotype/"
    "human-phenotype-ontology/master/hp.obo"
)

_SYNONYM_RE = re.compile(r'^synonym:\s*"((?:[^"\\]|\\.)*)"\s+(EXACT|NARROW|BROAD|RELATED)\b')
_NAME_RE = re.compile(r'^name:\s*(.+)$')
_ID_RE = re.compile(r'^id:\s*(HP:\d{7})$')


@dataclass
class HPOTerm:
    id: str
    name: str
    synonyms: Dict[str, List[str]] = field(default_factory=lambda: {
        "EXACT": [], "NARROW": [], "BROAD": [], "RELATED": []
    })
    is_obsolete: bool = False


def download_hp_obo(dest_path: str, url: str = HPO_OBO_URL, timeout: int = 120) -> str:
    """Download the current hp.obo release to dest_path. Returns dest_path."""
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    with open(dest_path, "wb") as f:
        f.write(data)
    return dest_path


def parse_hp_obo(path: str) -> Dict[str, HPOTerm]:
    """Parse hp.obo into {HP:id -> HPOTerm}. Skips obsolete terms by default
    handling upstream (caller can filter on .is_obsolete)."""
    terms: Dict[str, HPOTerm] = {}
    current: HPOTerm | None = None
    in_term = False

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line == "[Term]":
                in_term = True
                current = None
                continue
            if line.startswith("[") and line.endswith("]"):
                # entering a non-Term stanza (Typedef, etc.)
                in_term = False
                current = None
                continue
            if not in_term or not line.strip():
                continue

            if current is None:
                m = _ID_RE.match(line)
                if m:
                    current = HPOTerm(id=m.group(1), name="")
                    terms[current.id] = current
                continue

            if line.startswith("name:"):
                m = _NAME_RE.match(line)
                if m:
                    current.name = m.group(1).strip()
            elif line.startswith("synonym:"):
                m = _SYNONYM_RE.match(line)
                if m:
                    text = m.group(1).replace('\\"', '"')
                    scope = m.group(2)
                    current.synonyms[scope].append(text)
            elif line.startswith("is_obsolete:") and "true" in line:
                current.is_obsolete = True

    return terms

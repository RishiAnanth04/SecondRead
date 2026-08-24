"""
Command-line interface.

Usage:
    python cli.py --text "Patient presents with productive cough..."
    python cli.py --file note.txt
    echo "some clinical note" | python cli.py
"""
from __future__ import annotations

import argparse
import json
import sys

from pipeline import PhenotypeExtractor, PipelineConfig


def spans_to_dicts(spans):
    out = []
    for s in spans:
        d = {
            "start": s.start, "end": s.end, "text": s.text,
            "source": s.source.value, "assertion": s.assertion.value,
        }
        if s.hpo_candidates:
            d["hpo_candidates"] = list(s.hpo_candidates)
        if s.matched_form:
            d["matched_form"] = s.matched_form
        if s.lab_name:
            d["lab_name"] = s.lab_name
            d["lab_value"] = s.lab_value
            d["lab_unit"] = s.lab_unit
        out.append(d)
    return out


def main():
    ap = argparse.ArgumentParser(description="Stage-1 phenotype span extractor")
    ap.add_argument("--text", type=str, help="Raw clinical text to process")
    ap.add_argument("--file", type=str, help="Path to a text file to process")
    ap.add_argument("--obo", type=str, default="hp.obo",
                     help="Path to hp.obo (downloaded automatically if missing)")
    ap.add_argument("--no-download", action="store_true",
                     help="Do not auto-download hp.obo if missing")
    ap.add_argument("--json", action="store_true", help="Emit JSON")
    args = ap.parse_args()

    if args.text:
        text = args.text
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    extractor = PhenotypeExtractor.from_obo(
        args.obo, download_if_missing=not args.no_download
    )
    spans = extractor.extract(text)

    if args.json:
        print(json.dumps(spans_to_dicts(spans), indent=2))
    else:
        for s in spans:
            tag = f" [{s.assertion.value}]" if s.assertion.value != "present" else ""
            extra = ""
            if s.hpo_candidates:
                extra = f" -> {', '.join(s.hpo_candidates[:3])}"
            elif s.lab_name:
                extra = f" -> {s.lab_name}={s.lab_value}{s.lab_unit or ''}"
            print(f"[{s.source.value:11s}] ({s.start:4d},{s.end:4d}) "
                  f"'{s.text}'{tag}{extra}")


if __name__ == "__main__":
    main()

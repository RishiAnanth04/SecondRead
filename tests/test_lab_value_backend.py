from lab_value_backend import extract_lab_value_spans


def test_colon_delimited_form():
    spans = extract_lab_value_spans("Hemoglobin: 8.2 g/dL.")
    assert len(spans) == 1
    s = spans[0]
    assert s.lab_name.lower() == "hemoglobin"
    assert s.lab_value == "8.2"
    assert s.lab_unit == "g/dL"


def test_prose_connector_form():
    spans = extract_lab_value_spans("Sodium was 128 mmol/L on admission.")
    assert any(s.lab_name.lower() == "sodium" and s.lab_value == "128" for s in spans)


def test_parenthetical_form():
    spans = extract_lab_value_spans("Creatinine (1.4 mg/dL) was elevated.")
    assert any(s.lab_name.lower() == "creatinine" and s.lab_value == "1.4" for s in spans)


def test_digit_prefix_form():
    spans = extract_lab_value_spans("8.2 g/dL hemoglobin was noted.")
    assert any(s.lab_value == "8.2" and s.lab_unit == "g/dL" for s in spans)


def test_ratio_form():
    spans = extract_lab_value_spans("AST/ALT ratio of 2.1 was noted.")
    assert any("ast/alt" in s.lab_name.lower() and s.lab_value == "2.1" for s in spans)


def test_bare_adjacency_form():
    spans = extract_lab_value_spans("WBC 14.2 x10^9/L.")
    assert any(s.lab_name.upper() == "WBC" and s.lab_value == "14.2" for s in spans)


def test_blocklist_suppresses_prose_false_positives():
    # "was 42" alone should not fire without an accompanying unit / lab name
    spans = extract_lab_value_spans("The patient was 42 years old.")
    assert spans == []


def test_no_overlapping_spans():
    spans = extract_lab_value_spans("Hemoglobin: 8.2 g/dL. Sodium was 128 mmol/L.")
    intervals = sorted((s.start, s.end) for s in spans)
    for (s1, e1), (s2, e2) in zip(intervals, intervals[1:]):
        assert e1 <= s2


def test_lab_name_does_not_cross_newline():
    # regression test: multi-line EHR demographic block should not get
    # swallowed into a single false "lab" match spanning the newline
    text = "Jane Doe\nAGE: 34\n"
    spans = extract_lab_value_spans(text)
    assert not any("\n" in s.text for s in spans)


def test_demographic_and_section_headers_are_not_labs():
    text = "PATIENT: Jane Doe\nAGE: 34\nDATE: 08/24/2026\n"
    spans = extract_lab_value_spans(text)
    lab_names_lower = {s.lab_name.lower() for s in spans}
    assert "age" not in lab_names_lower
    assert "date" not in lab_names_lower


def test_adjacent_multiline_labs_do_not_bleed_into_each_other():
    # regression test: "MCV: 72 fL" on one line followed by "WBC: 14.2
    # x10^9/L" on the next must NOT merge into one span ("fL\nWBC=...")
    text = "MCV: 72 fL\nWBC: 14.2 x10^9/L\n"
    spans = extract_lab_value_spans(text)
    lab_names = {s.lab_name for s in spans}
    assert "MCV" in lab_names
    assert "WBC" in lab_names
    mcv = next(s for s in spans if s.lab_name == "MCV")
    assert mcv.lab_unit == "fL"
    wbc = next(s for s in spans if s.lab_name == "WBC")
    assert wbc.lab_value == "14.2"


def test_milli_iu_per_liter_unit_recognized():
    # regression test: mIU/L (distinct from mIU/mL) was previously missing
    # from the unit list, causing TSH results to bleed into the next line
    spans = extract_lab_value_spans("TSH: 8.7 mIU/L\nVitamin B12: 412 pg/mL\n")
    tsh = next(s for s in spans if s.lab_name == "TSH")
    assert tsh.lab_value == "8.7"
    assert tsh.lab_unit == "mIU/L"
    b12 = next(s for s in spans if "vitamin b12" in s.lab_name.lower())
    assert b12.lab_value == "412"

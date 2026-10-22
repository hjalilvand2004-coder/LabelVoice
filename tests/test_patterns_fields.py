# -*- coding: utf-8 -*-
"""آزمون استخراج فیلدها از سطرهای ساختگی — بدون موتور OCR."""
from label_reader.extraction.fields import extract_fields
from label_reader.models import FieldStatus
from tests.conftest import make_line


def _run(lines, product_type="medicine", **kw):
    return extract_fields(lines, product_type, settings(), **kw)


def settings():
    from label_reader.config import Settings
    return Settings(_env_file=None)


def test_paracetamol_sample_fields():
    lines = [
        make_line(1, "Paracetamol", y=30),
        make_line(2, "500 mg", y=100),
        make_line(3, "20 Tablets", y=170),
        make_line(4, "EXP: 2027/06", y=240),
    ]
    fields, warnings = _run(lines)
    assert fields["name"].value == "Paracetamol"
    assert fields["strength"].value == "500"
    assert fields["strength"].unit == "mg"
    assert fields["count"].value == "20"
    assert fields["count"].unit == "tablets"
    assert fields["expiry_date"].value == "2027/06"
    for key in ("name", "strength", "count", "expiry_date"):
        assert fields[key].status == FieldStatus.EXTRACTED
        assert fields[key].source_ids, "هر فیلد باید شاهد داشته باشد"


def test_mcg_vs_mg_distinct():
    lines = [make_line(1, "Vitamin B12", y=30),
             make_line(2, "1000 mcg", y=100)]
    fields, _ = _run(lines)
    assert fields["strength"].unit == "mcg"


def test_combo_strength_250mg_5ml():
    lines = [make_line(1, "Amoxicillin 250 mg/5 mL", y=30)]
    fields, _ = _run(lines)
    assert fields["name"].value == "Amoxicillin"
    assert fields["strength"].value == "250 mg/5 mL"
    assert fields["strength"].unit is None


def test_missing_strength_and_count():
    lines = [make_line(1, "Mystery Syrup", y=30),
             make_line(2, "150 mL", y=100)]
    fields, _ = _run(lines)
    # mL تنها بدون هیچ mg: احتمالاً حجم بسته است → قطعی اعلام نمی‌شود
    assert fields["strength"].status == FieldStatus.UNCERTAIN
    assert "حجم" in (fields["strength"].note_fa or "")
    assert fields["count"].status == FieldStatus.MISSING


def test_zero_value_not_certain():
    # خوانش ناقص ۵۰۰ → ۰ نباید قطعی شود
    lines = [make_line(1, "Drug X", y=30),
             make_line(2, "0 mg", y=100, conf=0.9)]
    fields, _ = _run(lines)
    assert fields["strength"].status == FieldStatus.UNCERTAIN


def test_ambiguous_date_uncertain():
    lines = [make_line(1, "Drug X", y=30),
             make_line(2, "EXP: 2027", y=100)]
    fields, _ = _run(lines)
    f = fields["expiry_date"]
    assert f.value == "2027"
    assert f.status == FieldStatus.UNCERTAIN
    assert f.note_fa  # توضیح ابهام ثبت شود


def test_conflicting_strengths_marked():
    lines = [make_line(1, "500 mg", y=30),
             make_line(2, "250 mg", y=100)]
    fields, _ = _run(lines)
    f = fields["strength"]
    assert f.status == FieldStatus.CONFLICTING
    assert "500" in f.note_fa and "250" in f.note_fa


def test_bottle_volume_not_strength_conflict():
    lines = [make_line(1, "Amoxicillin 250 mg/5 mL", y=30),
             make_line(2, "100 mL bottle", y=100)]
    fields, _ = _run(lines)
    assert fields["strength"].status == FieldStatus.EXTRACTED
    assert fields["strength"].value == "250 mg/5 mL"


def test_general_product_no_strength_from_grams():
    lines = [make_line(1, "Happy Cookie", y=30),
             make_line(2, "Net Wt: 120 g", y=100)]
    fields, _ = _run(lines, product_type="general_product")
    assert "strength" not in fields
    assert fields["net_weight"].value == "120"
    assert fields["net_weight"].unit == "g"


def test_persian_count_and_strength():
    lines = [make_line(1, "\u0627\u0633\u062a\u0627\u0645\u06cc\u0646\u0648\u0641\u0646", y=30),
             make_line(2, "\u06f5\u06f0\u06f0 \u0645\u06cc\u0644\u06cc\u200c\u06af\u0631\u0645", y=100),
             make_line(3, "\u06f2\u06f0 \u0642\u0631\u0635", y=170)]
    fields, _ = _run(lines)
    assert fields["strength"].value == "500"
    assert fields["strength"].unit == "mg"
    assert fields["count"].value == "20"
    assert fields["count"].unit == "قرص"


def test_printed_directive_captured():
    lines = [make_line(1, "Drug X 10 mg", y=30),
             make_line(2, "\u0647\u0631 \u06f8 \u0633\u0627\u0639\u062a \u06cc\u06a9 \u0642\u0631\u0635 \u0645\u0635\u0631\u0641 \u06a9\u0646\u06cc\u062f", y=100)]
    fields, _ = _run(lines)
    d = fields["printed_directives"]
    assert d.status != FieldStatus.MISSING
    assert "مصرف کنید" in (d.value or "")


def test_medicine_classification_keys():
    lines = [make_line(1, "Drug X 500 mg", y=30),
             make_line(2, "20 Tablets", y=100)]
    fields, _ = _run(lines, product_type="medicine")
    assert "active_ingredient" in fields
    assert "net_weight" not in fields


def test_multi_product_warning():
    lines = [make_line(1, "Ibuprofen 400 mg", y=30),
             make_line(2, "24 Tablets", y=100),
             make_line(3, "Aspirin 100 mg", y=800),
             make_line(4, "30 Tablets", y=870)]
    fields, warnings = _run(lines, image_height=1000)
    assert any("یک بسته را برش بزنید" in w for w in warnings)


def test_no_fabrication_when_no_evidence():
    lines = [make_line(1, "Drug X 500 mg", y=30)]
    fields, _ = _run(lines)
    assert fields["count"].value is None
    assert fields["count"].status == FieldStatus.MISSING
    assert fields["manufacturer"].value is None
    assert fields["expiry_date"].value is None

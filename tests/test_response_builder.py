# -*- coding: utf-8 -*-
"""آزمون پاسخ قالبی فارسی و نگهبان قواعد ایمنی."""
from label_reader.config import Settings
from label_reader.extraction.fields import extract_fields
from label_reader.response.builder import (
    build_response, format_strength, NO_TEXT_RESPONSE_FA)
from label_reader.response.guard import validate_llm_output, validate_text
from label_reader.models import FieldRecord, FieldStatus, QualityIssue
from tests.conftest import make_line


def _fields(lines, product_type="medicine"):
    fields, _ = extract_fields(
        lines, product_type, Settings(_env_file=None))
    return fields


def test_exact_sample_sentence():
    """نمونه مشخصات: Paracetamol / 500 mg / 20 Tablets."""
    lines = [make_line(1, "Paracetamol", y=30),
             make_line(2, "500 mg", y=100),
             make_line(3, "20 Tablets", y=170)]
    fields = _fields(lines)
    response = build_response(fields, [], [], 3)
    assert "نام درج‌شده روی بسته: Paracetamol." in response
    assert "قدرت درج‌شده: ۵۰۰ میلی‌گرم." in response
    assert "تعداد درج‌شده: ۲۰ قرص." in response
    assert "توصیه پزشکی" in response and "مقدار مصرف نیستند" in response
    # مرز کلیدی: قدرت درج‌شده هرگز دوز نامیده نمی‌شود
    assert "دوز" not in response

def test_no_medical_use_added():
    lines = [make_line(1, "Paracetamol", y=30),
             make_line(2, "500 mg", y=100),
             make_line(3, "20 Tablets", y=170)]
    response = build_response(_fields(lines), [], [], 3)
    assert "کاهش تب" not in response
    assert "کاهش درد" not in response
    assert "مصرف کنید" not in response


def test_uncertain_strength_not_asserted():
    fields = {"strength": FieldRecord(
        key="strength", label_fa="قدرت درج‌شده", value="500", unit="mg",
        source_ids=["ocr_002"], confidence=0.3, status=FieldStatus.UNCERTAIN)}
    response = build_response(fields, [], [], 5)
    assert "واضح خوانده نشد" in response
    assert "خوانش احتمالی" in response


def test_conflicting_strength_not_asserted():
    fields = {"strength": FieldRecord(
        key="strength", label_fa="قدرت درج‌شده", value="500", unit="mg",
        source_ids=["ocr_002"], confidence=0.9, status=FieldStatus.CONFLICTING,
        note_fa="مقادیر متفاوتی خوانده شد: 500، 250.")}
    response = build_response(fields, [], [], 5)
    assert "قطعی اعلام نمی‌شود" in response


def test_no_text_guidance():
    response = build_response({}, [], [], 0)
    assert response == NO_TEXT_RESPONSE_FA


def test_printed_directive_prefix():
    lines = [make_line(1, "Drug X 10 mg", y=30),
             make_line(2, "\u0647\u0631 \u06f8 \u0633\u0627\u0639\u062a \u06cc\u06a9 \u0642\u0631\u0635 \u0645\u0635\u0631\u0641 \u06a9\u0646\u06cc\u062f", y=100)]
    fields = _fields(lines)
    response = build_response(fields, [], [], 2)
    assert "متن دستور چاپ‌شده روی بسته" in response
    assert "توصیه شخصی به شما نیست" in response


def test_quality_issue_included():
    fields = _fields([make_line(1, "Drug X 500 mg", y=30)])
    issue = QualityIssue(code="blurry", severity="severe",
                         message_fa="متن بسته واضح نیست.")
    response = build_response(fields, [issue], [], 2)
    assert "هشدار کیفیت تصویر" in response


def test_format_strength_combo():
    f = FieldRecord(key="strength", label_fa="قدرت", value="250 mg/5 mL",
                    status=FieldStatus.EXTRACTED)
    assert "میلی‌گرم" in format_strength(f)
    assert "در" in format_strength(f)


# ---------------- نگهبان ----------------

def _evidence(strength_value="500", strength_unit="mg"):
    return {"fields": {"strength": {
        "value": strength_value, "unit": strength_unit,
        "raw_text": f"{strength_value} {strength_unit}", "note_fa": None}}}


def test_guard_rejects_medical_claims():
    report = validate_llm_output(
        "این دارو برای کاهش تب و درد استفاده می‌شود.", _evidence())
    assert not report.ok


def test_guard_rejects_dose_schedule():
    report = validate_llm_output(
        "قدرت 500 mg است. هر ۶ ساعت یک قرص مصرف کنید.", _evidence())
    assert not report.ok


def test_guard_rejects_out_of_evidence_numbers():
    report = validate_llm_output("قدرت درج‌شده: 600 mg.", _evidence("500"))
    assert not report.ok
    report2 = validate_llm_output("قدرت درج‌شده: ۵۰۰ میلی‌گرم.", _evidence("500"))
    assert report2.ok


def test_guard_rejects_dose_naming():
    report = validate_llm_output("دوز مصرف این دارو 500 mg است.", _evidence())
    assert not report.ok


def test_guard_accepts_faithful_rewrite():
    report = validate_llm_output(
        "نام درج‌شده روی بسته: Paracetamol. قدرت درج‌شده: ۵۰۰ میلی‌گرم.",
        _evidence())
    assert report.ok


def test_guard_is_quote_aware_for_printed_directives():
    text = ("متن دستور چاپ‌شده روی بسته: «هر ۸ ساعت یک قرص مصرف کنید». "
            "این صرفاً بازخوانی متن است.")
    report = validate_text(text)
    assert report.ok


def test_template_passes_self_check():
    lines = [make_line(1, "Paracetamol", y=30),
             make_line(2, "500 mg", y=100),
             make_line(3, "20 Tablets", y=170),
             make_line(4, "EXP: 2027/06", y=240)]
    fields = _fields(lines)
    response = build_response(fields, [], [], 4)
    assert validate_text(response).ok

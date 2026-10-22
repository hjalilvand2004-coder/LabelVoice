# -*- coding: utf-8 -*-
"""استخراج فیلدهای ساختاریافته از سطرهای OCR — فقط با شواهد خوانا.

قواعد حیاتی:
- نبود فیلد → null (status=missing)؛ اطلاعات غایب تکمیل نمی‌شود.
- هر فیلد به شناسه قطعه‌های OCR (source_ids) متصل است.
- قدرت دارو از برنامه مصرف جدا نگه داشته می‌شود و «دوز مصرف» نامیده نمی‌شود.
- فیلدهای متناقض علامت‌گذاری می‌شوند، نه اینکه یکی بی‌دلیل انتخاب شود.
"""
from __future__ import annotations

import re

from ..models import FieldRecord, FieldStatus, RawLine
from ..textnorm import cleaned_display_text
from ..config import Settings
from .conflicts import Candidate, resolve_candidates
from .patterns import (
    COUNT_NOUN_CANONICAL, DOSAGE_FORM_FA, RE_BATCH_LABEL, RE_BATCH_VALUE,
    RE_COUNT, RE_COUNT_REV, RE_DATE_VALUE, RE_DIRECTIVE_KEYWORD,
    RE_DOSAGE_FORM, RE_EXPIRY_LABEL, RE_INGREDIENT_KEYWORD,
    RE_MANUFACTURER_KEYWORD, RE_NET_WEIGHT_KEYWORD, RE_PRODUCTION_LABEL,
    RE_STORAGE_KEYWORD, RE_STRENGTH, RE_WARNING_KEYWORD, RE_YEAR_ONLY,
    UNIT_CANONICAL, infer_date_ambiguity,
)

FIELD_LABELS_FA = {
    "name": "نام درج‌شده روی بسته",
    "active_ingredient": "ماده مؤثره درج‌شده",
    "strength": "قدرت درج‌شده",
    "dosage_form": "شکل دارویی درج‌شده",
    "count": "تعداد درج‌شده",
    "net_weight": "وزن یا حجم خالص",
    "ingredients": "ترکیبات درج‌شده",
    "manufacturer": "سازنده درج‌شده",
    "batch": "شماره سری ساخت",
    "production_date": "تاریخ تولید",
    "expiry_date": "تاریخ انقضا",
    "storage": "شرایط نگهداری",
    "warnings": "هشدارهای چاپ‌شده روی بسته",
    "printed_directives": "متن دستور چاپ‌شده روی بسته",
}

_MEDICINE_KEYS = ["name", "active_ingredient", "strength", "dosage_form", "count",
                  "manufacturer", "batch", "production_date", "expiry_date",
                  "storage", "warnings", "printed_directives"]
_GENERAL_KEYS = ["name", "net_weight", "count", "ingredients", "manufacturer",
                 "production_date", "expiry_date", "storage", "warnings",
                 "printed_directives"]

_ALPHA_MIN = 3


def _has_alpha(text: str) -> bool:
    return sum(1 for ch in text if ch.isalpha()) >= _ALPHA_MIN


def _mk_record(key: str, status: FieldStatus, *, value=None, unit=None,
               raw_text=None, source_ids=None, confidence=None,
               note_fa=None) -> FieldRecord:
    return FieldRecord(
        key=key, label_fa=FIELD_LABELS_FA[key], value=value, unit=unit,
        raw_text=raw_text, source_ids=source_ids or [], confidence=confidence,
        status=status, note_fa=note_fa,
    )


def _missing(key: str) -> FieldRecord:
    return _mk_record(key, FieldStatus.MISSING)


def _conf_of(line: RawLine) -> float:
    return line.confidence_mean if line.confidence_mean is not None else 0.5


def _text_candidate_from_strength(match: re.Match, line: RawLine, idx: int) -> Candidate | None:
    unit = UNIT_CANONICAL.get(match.group("unit").lower().strip("."))
    if unit is None:
        return None
    num = match.group("num")
    if match.group("num2"):
        unit2 = UNIT_CANONICAL.get(match.group("unit2").lower().strip("."))
        value = f"{num} {unit}/{match.group('num2')} {unit2}"
        return Candidate(value_norm=value, unit=None, raw_text=match.group(0),
                         source_ids=list(line.source_ids),
                         confidence=_conf_of(line), line_index=idx,
                         x=line.bbox.x, y=line.bbox.y)
    return Candidate(value_norm=num, unit=unit, raw_text=match.group(0),
                     source_ids=list(line.source_ids), confidence=_conf_of(line),
                     line_index=idx, x=line.bbox.x, y=line.bbox.y)


def _count_candidate(match: re.Match, line: RawLine, idx: int) -> Candidate:
    noun = COUNT_NOUN_CANONICAL.get(match.group("noun").lower(), match.group("noun"))
    return Candidate(value_norm=match.group("num"), unit=noun,
                     raw_text=match.group(0), source_ids=list(line.source_ids),
                     confidence=_conf_of(line), line_index=idx,
                     x=line.bbox.x, y=line.bbox.y)


def _find_labeled_date(lines: list[RawLine], label_re) -> list[Candidate]:
    out: list[Candidate] = []
    for idx, line in enumerate(lines):
        m = label_re.search(line.normalized_text)
        if not m:
            continue
        val_match = RE_DATE_VALUE.search(line.normalized_text, m.end())
        if val_match is None and RE_DATE_VALUE.search(line.normalized_text):
            val_match = RE_DATE_VALUE.search(line.normalized_text)
        if val_match is not None:
            value, ambiguous = infer_date_ambiguity(
                val_match.group("d1"), val_match.group("d2"),
                val_match.group("d3"))
            out.append(Candidate(
                value_norm=value + ("?" if ambiguous else ""),
                unit=None, raw_text=val_match.group(0),
                source_ids=list(line.source_ids), confidence=_conf_of(line),
                line_index=idx, x=line.bbox.x, y=line.bbox.y))
            continue
        # سال تنها (مثل EXP: 2027) — مبهم تلقی می‌شود
        remainder = line.normalized_text[m.end():]
        ym = RE_YEAR_ONLY.search(remainder) or RE_YEAR_ONLY.search(line.normalized_text)
        if ym is not None:
            out.append(Candidate(
                value_norm=ym.group(1) + "?",
                unit=None, raw_text=ym.group(1),
                source_ids=list(line.source_ids), confidence=_conf_of(line),
                line_index=idx, x=line.bbox.x, y=line.bbox.y))
            continue
        # برچسب در یک سطر و مقدار در سطر بعدی
        if idx + 1 < len(lines):
            nxt = lines[idx + 1]
            vm = RE_DATE_VALUE.search(nxt.normalized_text)
            if vm is not None and len(vm.group("d1")) >= 2:
                value, ambiguous = infer_date_ambiguity(
                    vm.group("d1"), vm.group("d2"), vm.group("d3"))
                out.append(Candidate(
                    value_norm=value + ("?" if ambiguous else ""),
                    unit=None, raw_text=vm.group(0),
                    source_ids=list(line.source_ids) + list(nxt.source_ids),
                    confidence=min(_conf_of(line), _conf_of(nxt)),
                    line_index=idx, x=line.bbox.x, y=line.bbox.y))
    return out


def _free_text_field(key: str, lines: list[RawLine], keyword_re,
                     settings: Settings) -> tuple[FieldRecord, set[int]]:
    """بازگشت: (رکورد فیلد، شاخص سطرهای مصرف‌شده برای جلوگیری از نام‌کاندید شدن)."""
    hits = [i for i, ln in enumerate(lines)
            if keyword_re.search(ln.normalized_text)]
    if not hits:
        return _missing(key), set()
    seen: set[str] = set()
    values: list[str] = []
    source_ids: list[str] = []
    confs: list[float] = []
    for i in sorted(hits, key=lambda j: (lines[j].bbox.y, lines[j].bbox.x)):
        val = cleaned_display_text(lines[i].text)
        if val and val not in seen:
            seen.add(val)
            values.append(val)
            source_ids.extend(lines[i].source_ids)
            confs.append(_conf_of(lines[i]))
    conf = min(confs)
    status = FieldStatus.EXTRACTED if conf >= settings.low_confidence_threshold \
        else FieldStatus.UNCERTAIN
    note = "این متن عیناً از برچسب بازخوانی شده است." if key == "printed_directives" else None
    return _mk_record(key, status, value="؛ ".join(values), unit=None,
                      raw_text=" / ".join(values), source_ids=source_ids,
                      confidence=round(conf, 2), note_fa=note), set(hits)


def _name_candidates(consumed: set[int], lines: list[RawLine]) -> list[int]:
    out = []
    for idx, line in enumerate(lines):
        if idx in consumed or not _has_alpha(line.normalized_text):
            continue
        if len(line.normalized_text) > 80:
            continue
        out.append(idx)
    out.sort(key=lambda i: (lines[i].bbox.y, lines[i].bbox.x))
    return out


def extract_fields(
    lines: list[RawLine],
    product_type: str,
    settings: Settings,
    image_height: int | None = None,
) -> tuple[dict[str, FieldRecord], list[str]]:
    """استخراج همه فیلدها. بازگشت: (فیلدها، هشدارهای استخراج)."""
    extraction_warnings: list[str] = []
    consumed: set[int] = set()

    strength_cands: list[Candidate] = []
    count_cands: list[Candidate] = []
    for idx, line in enumerate(lines):
        text = line.normalized_text
        st_matches = list(RE_STRENGTH.finditer(text))
        for m in st_matches:
            cand = _text_candidate_from_strength(m, line, idx)
            if cand is not None:
                # «۱۰۰ mL» تنها (حجم بطری) قدرت دارو نیست؛ تنزیل می‌شود تا
                # با قدرت واقعی مثل «250 mg/5 mL» تناقض نسازد.
                if cand.unit == "mL" and " " not in cand.value_norm:
                    cand.confidence = (cand.confidence or 0.5) * 0.35
                strength_cands.append(cand)
                consumed.add(idx)
        for m in RE_COUNT.finditer(text):
            count_cands.append(_count_candidate(m, line, idx))
            consumed.add(idx)
        for m in RE_COUNT_REV.finditer(text):
            count_cands.append(_count_candidate(m, line, idx))
            consumed.add(idx)
    # وقتی کاندید حاوی mg وجود دارد، کاندیدهای mL تنها (حجم بطری) حذف می‌شوند
    has_mg_candidate = any(
        c.unit == "mg" or "mg" in c.value_norm for c in strength_cands)
    if has_mg_candidate:
        strength_cands = [
            c for c in strength_cands
            if not (c.unit == "mL" and " " not in c.value_norm)]
    # محصول عمومی: «گرم/درصد» بدون هیچ mg/mcg، وزن خالص است نه قدرت دارو
    if product_type == "general_product" and not has_mg_candidate:
        strength_cands = []

    expiry_cands = _find_labeled_date(lines, RE_EXPIRY_LABEL)
    prod_cands = _find_labeled_date(lines, RE_PRODUCTION_LABEL)
    for c in expiry_cands + prod_cands:
        consumed.add(c.line_index)

    batch_cands: list[Candidate] = []
    for idx, line in enumerate(lines):
        m = RE_BATCH_LABEL.search(line.normalized_text)
        if not m:
            continue
        vm = RE_BATCH_VALUE.search(line.normalized_text, m.end())
        if vm is None:
            continue
        consumed.add(idx)
        batch_cands.append(Candidate(
            value_norm=vm.group("val"), unit=None, raw_text=vm.group(0),
            source_ids=list(line.source_ids), confidence=_conf_of(line),
            line_index=idx, x=line.bbox.x, y=line.bbox.y))

    def resolve_field(key: str, cands: list[Candidate]) -> FieldRecord:
        best, status, distinct = resolve_candidates(
            cands, settings.low_confidence_threshold)
        if best is None:
            return _missing(key)
        # محافظ خوانش ناقص عدد: «۰» برای قدرت/تعداد معنادار نیست و
        # احتمالاً نتیجه ناخوانایی بخشی از رقم است (مثل ۵۰۰ → ۰).
        if key in ("strength", "count") and best.value_norm:
            try:
                if float(best.value_norm.replace(",", ".")) == 0.0:
                    return _mk_record(
                        key, FieldStatus.UNCERTAIN, value=best.value_norm,
                        unit=best.unit, raw_text=best.raw_text,
                        source_ids=best.source_ids,
                        confidence=min(best.confidence or 0.5, 0.3),
                        note_fa="عدد به‌طور کامل خوانده نشد و ممکن است ناقص "
                                "باشد؛ به‌عنوان مقدار قطعی خوانده نمی‌شود.")
            except ValueError:
                pass
        # «mL تنها» بدون هیچ mg: احتمالاً حجم بسته است، نه قدرت دارو
        if key == "strength" and best.unit == "mL" and \
                not any(c.unit == "mg" or "mg" in c.value_norm for c in cands):
            return _mk_record(
                key, FieldStatus.UNCERTAIN, value=best.value_norm,
                unit=best.unit, raw_text=best.raw_text,
                source_ids=best.source_ids, confidence=best.confidence,
                note_fa="واحد mL به‌تنهایی ممکن است حجم بسته باشد نه قدرت دارو؛ "
                        "به‌عنوان قدرت قطعی خوانده نمی‌شود.")
        if status == "conflicting":
            shown = "، ".join(distinct)
            return _mk_record(
                key, FieldStatus.CONFLICTING, value=best.value_norm,
                unit=best.unit, raw_text=best.raw_text,
                source_ids=best.source_ids, confidence=best.confidence,
                note_fa=f"مقادیر متفاوتی خوانده شد: {shown}. لطفاً ناحیه مربوط را "
                        f"واضح‌تر بگیرید یا مقدار درست را اصلاح کنید.")
        status_enum = FieldStatus.EXTRACTED if status == "extracted" else FieldStatus.UNCERTAIN
        note = ("اطمینان OCR پایین است؛ مقدار ممکن است نادرست خوانده شده باشد."
                if status == "uncertain" else None)
        return _mk_record(key, status_enum, value=best.value_norm, unit=best.unit,
                          raw_text=best.raw_text, source_ids=best.source_ids,
                          confidence=best.confidence, note_fa=note)

    fields: dict[str, FieldRecord] = {}
    fields["strength"] = resolve_field("strength", strength_cands)
    fields["count"] = resolve_field("count", count_cands)

    ref_h = image_height or max((l.bbox.y2 for l in lines), default=1)
    if fields["strength"].status == FieldStatus.CONFLICTING and len(strength_cands) >= 2:
        ys = [c.y for c in strength_cands]
        if max(ys) - min(ys) > 0.5 * ref_h:
            extraction_warnings.append(
                "چند ناحیه متنی مستقل در تصویر دیده می‌شود؛ برای نتیجه دقیق، "
                "لطفاً یک بسته را برش بزنید یا فقط یک بسته را عکس بگیرید. "
                "اطلاعات چند بسته در یک خروجی ادغام نمی‌شود.")

    fields["expiry_date"] = _date_record("expiry_date", expiry_cands, settings)
    fields["production_date"] = _date_record("production_date", prod_cands, settings)
    fields["batch"] = resolve_field("batch", batch_cands)
    fields["storage"], used_idx = _free_text_field(
        "storage", lines, RE_STORAGE_KEYWORD, settings)
    consumed |= used_idx
    fields["warnings"], used_idx = _free_text_field(
        "warnings", lines, RE_WARNING_KEYWORD, settings)
    consumed |= used_idx
    fields["printed_directives"], used_idx = _free_text_field(
        "printed_directives", lines, RE_DIRECTIVE_KEYWORD, settings)
    consumed |= used_idx
    fields["manufacturer"], used_idx = _free_text_field(
        "manufacturer", lines, RE_MANUFACTURER_KEYWORD, settings)
    consumed |= used_idx

    for key, cand in (("expiry_date", expiry_cands), ("production_date", prod_cands),
                      ("batch", batch_cands)):
        if cand:
            consumed.add(cand[0].line_index)

    # ماده مؤثره: فقط اگر صریحاً کنار واژه کلیدی درج شده باشد
    fields["active_ingredient"] = _missing("active_ingredient")
    for idx, line in enumerate(lines):
        m = RE_INGREDIENT_KEYWORD.search(line.normalized_text)
        if not m:
            continue
        after = line.normalized_text[m.end():]
        st = RE_STRENGTH.search(after)
        if st is not None:
            cand = _text_candidate_from_strength(st, line, idx)
            val = cleaned_display_text(
                after[: st.start()].strip(" :=-،,") or st.group(0))
        else:
            val = cleaned_display_text(line.text)
            cand = None
        conf = _conf_of(line)
        fields["active_ingredient"] = _mk_record(
            "active_ingredient",
            FieldStatus.EXTRACTED if conf >= settings.low_confidence_threshold
            else FieldStatus.UNCERTAIN,
            value=val or None, unit=(cand.unit if cand else None),
            raw_text=line.text, source_ids=list(line.source_ids),
            confidence=round(conf, 2))
        consumed.add(idx)
        break

    # شکل دارویی
    fields["dosage_form"] = _missing("dosage_form")
    if fields["count"].unit:
        form = DOSAGE_FORM_FA.get(fields["count"].unit)
        if form:
            fields["dosage_form"] = _mk_record(
                "dosage_form", FieldStatus.EXTRACTED, value=form, unit=None,
                raw_text=fields["count"].raw_text,
                source_ids=list(fields["count"].source_ids),
                confidence=fields["count"].confidence)
    if fields["dosage_form"].status == FieldStatus.MISSING:
        for idx, line in enumerate(lines):
            m = RE_DOSAGE_FORM.search(line.normalized_text)
            if m:
                form = DOSAGE_FORM_FA.get(m.group(0).lower())
                if form:
                    conf = _conf_of(line)
                    fields["dosage_form"] = _mk_record(
                        "dosage_form",
                        FieldStatus.EXTRACTED if conf >= settings.low_confidence_threshold
                        else FieldStatus.UNCERTAIN,
                        value=form, unit=None, raw_text=line.text,
                        source_ids=list(line.source_ids),
                        confidence=round(conf, 2))
                    break

    # فیلدهای عمومی
    fields["net_weight"] = _missing("net_weight")
    for idx, line in enumerate(lines):
        m = RE_NET_WEIGHT_KEYWORD.search(line.normalized_text)
        if not m:
            continue
        st = RE_STRENGTH.search(line.normalized_text, m.end()) or \
            RE_STRENGTH.search(line.normalized_text)
        if st is not None:
            cand = _text_candidate_from_strength(st, line, idx)
            if cand is not None:
                conf = _conf_of(line)
                fields["net_weight"] = _mk_record(
                    "net_weight",
                    FieldStatus.EXTRACTED if conf >= settings.low_confidence_threshold
                    else FieldStatus.UNCERTAIN,
                    value=cand.value_norm, unit=cand.unit, raw_text=st.group(0),
                    source_ids=list(line.source_ids), confidence=round(conf, 2))
                consumed.add(idx)
                break
    fields["ingredients"], used_idx = _free_text_field(
        "ingredients", lines, RE_INGREDIENT_KEYWORD, settings)
    consumed |= used_idx

    # نام: ابتدا سطر بالایی اگر «نام + قدرت» را با هم دارد؛ سپس کاندیدهای آزاد
    fields["name"] = _missing("name")
    name_set = False
    if lines:
        top = min(range(len(lines)), key=lambda i: (lines[i].bbox.y, lines[i].bbox.x))
        top_line = lines[top]
        m = RE_STRENGTH.search(top_line.normalized_text)
        if m is not None:
            remainder = top_line.normalized_text[: m.start()].strip(" :-.،,")
            if sum(1 for ch in remainder if ch.isalpha()) >= _ALPHA_MIN:
                conf = _conf_of(top_line)
                fields["name"] = _mk_record(
                    "name",
                    FieldStatus.EXTRACTED if conf >= settings.low_confidence_threshold
                    else FieldStatus.UNCERTAIN,
                    value=cleaned_display_text(remainder),
                    unit=None, raw_text=top_line.text,
                    source_ids=list(top_line.source_ids),
                    confidence=round(conf, 2))
                consumed.add(top)
                name_set = True
    name_idx_list = [] if name_set else _name_candidates(consumed, lines)
    if name_idx_list:
        idx = name_idx_list[0]
        line = lines[idx]
        conf = _conf_of(line)
        fields["name"] = _mk_record(
            "name", FieldStatus.EXTRACTED if conf >= settings.low_confidence_threshold
            else FieldStatus.UNCERTAIN,
            value=cleaned_display_text(line.text), unit=None, raw_text=line.text,
            source_ids=list(line.source_ids), confidence=round(conf, 2))
        consumed.add(idx)
        # چندمحصولی: نام دوم در بخش پایین «تصویر» → درخواست برش یک بسته
        ref_h = image_height or max((l.bbox.y2 for l in lines), default=1)
        for other in name_idx_list[1:]:
            if lines[other].bbox.y > 0.55 * ref_h:
                extraction_warnings.append(
                    "چند ناحیه متنی مستقل در تصویر دیده می‌شود؛ برای نتیجه دقیق، "
                    "لطفاً یک بسته را برش بزنید یا فقط یک بسته را عکس بگیرید. "
                    "اطلاعات چند بسته در یک خروجی ادغام نمی‌شود.")
                break

    # قالب فیلدها بر اساس نوع بسته (فیلدهای خارج از قالب نمایش داده نمی‌شوند)
    keys = _MEDICINE_KEYS if product_type == "medicine" else _GENERAL_KEYS
    ordered = {k: fields.get(k, _missing(k)) for k in keys}
    return ordered, extraction_warnings


def _date_record(key: str, cands: list[Candidate], settings: Settings) -> FieldRecord:
    best, status, distinct = resolve_candidates(cands, settings.low_confidence_threshold)
    if best is None:
        return _missing(key)
    ambiguous = best.value_norm.endswith("?")
    value = best.value_norm.rstrip("?")
    if status == "conflicting":
        return _mk_record(
            key, FieldStatus.CONFLICTING, value=value, unit=None,
            raw_text=best.raw_text, source_ids=best.source_ids,
            confidence=best.confidence,
            note_fa=f"تاریخ‌های متفاوتی خوانده شد: {'، '.join(distinct)}.")
    if ambiguous:
        return _mk_record(
            key, FieldStatus.UNCERTAIN, value=value, unit=None,
            raw_text=best.raw_text, source_ids=best.source_ids,
            confidence=best.confidence,
            note_fa="تاریخ به‌صورت مبهم درج شده است (سال یا ترتیب روز/ماه قطعی نیست) "
                    "و بدون شواهد به تاریخ قطعی تبدیل نشد.")
    status_enum = FieldStatus.EXTRACTED if status == "extracted" else FieldStatus.UNCERTAIN
    note = "اطمینان OCR پایین است." if status == "uncertain" else None
    return _mk_record(key, status_enum, value=value, unit=None,
                      raw_text=best.raw_text, source_ids=best.source_ids,
                      confidence=best.confidence, note_fa=note)

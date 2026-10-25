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

from ..models import FieldRecord, FieldStatus, OcrPiece, RawLine
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

# نویسه‌هایی که در نام محصول واقعی به‌ندرت ظاهر می‌شوند؛ حضورشان نشانه خوانش
# آشغال OCR است (مثل «RIE [SE ۱ ES {= ray WE» که پیش‌تر به‌عنوان نام چاپ می‌شد)
_NAME_FORBIDDEN_RE = re.compile(r'[\[\]{}<>|=+*#@$%^~\\/_⌐«»"]')


def _has_alpha(text: str) -> bool:
    return sum(1 for ch in text if ch.isalpha()) >= _ALPHA_MIN


# واژه‌های ساختاری که به‌تنهایی «نام محصول» نیستند (v1.8.0): اگر کل سطر
# کاندیدِ نام فقط از این واژه‌ها + ارقام ساخته شده باشد، نام نیست (شکل دارویی
# یا بسته‌بندی است) و اعلامش به‌عنوان نام گمراه‌کننده است.
_STRUCTURAL_ONLY_RE = re.compile(
    r"^(?:[\d\s۰-۹/.,\-–—]|کپسول|انتریک|کوتد|قرص|شربت|آمپول|سوسپانسیون|قطره|"
    r"پماد|ژل|کرم|اسپری|شیاف|دستورالعمل|بسته|عدد|حاوی|میلی|گرم|لیتر|"
    r"تأسیس|تاسیس|شرکت|کارخانه|کد|سری|ساخت|انقضا|تولید|"
    r"mg|ml|g|tablet|capsule|syrup|caps|tab)+$",
    re.IGNORECASE,
)


def _plausible_name(text: str) -> bool:
    """آیا این سطر می‌تواند نام محصول باشد؟ (v1.7.0/1.8.0 — دروازه ضدزباله)

    معیارها:
    - دست‌کم سه نویسه حرفی؛
    - فاقد نویسه‌های ممنوعه (کروشه/آکولاد/نمادهای ریاضی/گیومه و…)؛
    - نسبت نویسه‌های حرف/رقم به کل نویسه‌ها ≥ ۰٫۶ (نام آشغال نماد زیاد دارد)؛
    - ترکیب حرف لاتین + رقم فارسی/عربی در یک سطر رد می‌شود (برچسب واقعی
      در نام فقط از یک خط نوشتار استفاده می‌کند؛ این ترکیب فقط در خوانش خراب
      دیده می‌شود)؛
    - v1.8.0: سطری که فقط از واژه‌های ساختاری (شکل دارویی/واحد) + عدد ساخته
      شده نام نیست — «کپسول انتریک کوتد» شکل دارویی است نه نام محصول.
    """
    if not _has_alpha(text):
        return False
    if _NAME_FORBIDDEN_RE.search(text):
        return False
    total = len(text)
    alnum = sum(1 for ch in text if ch.isalnum())
    if total == 0 or alnum / total < 0.6:
        return False
    latin = sum(1 for ch in text if ch.isalpha() and "\u0000" <= ch <= "\u024f")
    fa_digit = sum(1 for ch in text if ch in "\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9"
                   "\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669")
    if latin > 0 and fa_digit > 0:
        return False
    if _STRUCTURAL_ONLY_RE.match(text.replace("\u200c", " ").strip()):
        return False
    return True


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


def _name_candidates(consumed: set[int], lines: list[RawLine],
                     settings: Settings,
                     pieces_by_id: dict[str, "OcrPiece"] | None = None
                     ) -> list[int]:
    """کاندیدهای نام — فقط سطرهای «باورپذیر» (v1.7.0/1.8.0 دروازه ضدزباله).

    سطرهای آشغال OCR (مثل «RIE [SE ۱ ES {= ray WE») دیگر نام نمی‌شوند؛
    سطرهای با اطمینان زیر name_min_confidence هم کاندید نمی‌شوند تا زبالهٔ
    کم‌اطمینان بالای تصویر، نام واقعیِ پراطمینان (مثل MEDICINE) را نپوشاند.
    در نبود کاندید معتبر، نام صادقانه MISSING اعلام می‌شود.

    v1.8.0: سطر «بریده» هم نام نمی‌شود — اگر محتوای حرفیِ سطر، زیرمجموعهٔ
    محتوای حرفیِ سطر بلندتری باشد (مثل «پرازول» داخل «لانسوپرازول ۳۰
    میلی‌گرم»)، آن سطر قطعه‌ی خوانش جدا شده است، نه نام مستقل.

    v1.8.0-و (قانون اعتبارسنجی چندموتوره): نام فیلدِ حساس است؛ سطر نام باید
    (الف) همه‌ی قطعه‌هایش اطمینان ≥ ۰٫۵ داشته باشند و (ب) دست‌کم یک قطعه با
    رأی تکرارشده (support ≥ ۲ از تسراکت، یا support ≥ ۳ از هر موتوری)
    داشته باشد. به این ترتیب خوانش‌های تک‌منبع (امضای دست‌نویس، خوش‌نویسی
    تزئینی، خوانش اشتباه با اطمینان کاذب) نام نمی‌شوند.
    """
    out = []
    for idx, line in enumerate(lines):
        if idx in consumed or not _plausible_name(line.normalized_text):
            continue
        if (line.confidence_mean if line.confidence_mean is not None else 0.5) \
                < settings.name_min_confidence:
            continue
        if len(line.normalized_text) > 80:
            continue
        if _is_fragment_of_other_line(idx, lines):
            continue
        if _is_repeated_word_line(idx, lines):
            continue
        # v1.8.0: نام تک‌واژه با اطمینان متوسط/پایین قابل اعتماد نیست
        conf = line.confidence_mean if line.confidence_mean is not None else 0.5
        if " " not in line.normalized_text.strip() and conf < 0.75:
            continue
        # v1.8.0-و: قانون چندموتوره/تکرارشده
        if pieces_by_id is not None and not _line_has_corroboration(
                line, pieces_by_id):
            continue
        out.append(idx)
    return out


def _line_has_corroboration(line: RawLine,
                            pieces_by_id: dict[str, "OcrPiece"]) -> bool:
    """آیا سطر نام، شاهد تکرارشده دارد؟ (v1.8.0-و)

    پذیرفته می‌شود اگر:
    - همه‌ی قطعه‌های شاهد اطمینان ≥ ۰٫۵ داشته باشند (None = ۰٫۵)، و
    - دست‌کم یک قطعه با یکی از این شواهد تکرار وجود باشد:
      (الف) support ≥ ۳ (خوانش تکرارشده در چند پیکربندی)؛
      (ب) support ≥ ۲ از موتور تسراکت؛
      (ج) v2.10.0: support ≥ ۲ با رأی از «دو واریانت مستقل» (vote_variants) —
        چون از v2.10.0 شمار واریانت‌های اجراشده با تشخیص مسئله متغیر است
        (۳ تا ۷)، معیار «دو واریانت مستقل هم‌ناحیه را خواندند» پایدارتر از
        شمارش خام رأی است.
    """
    pieces = [pieces_by_id[sid] for sid in line.source_ids
              if sid in pieces_by_id]
    if not pieces:
        # بدون اطلاعات قطعه (مثل آزمون‌های قدیمی) سخت‌گیری اضافه نمی‌شود
        return True
    for p in pieces:
        conf = p.confidence if p.confidence is not None else 0.5
        if conf < 0.5:
            return False
    for p in pieces:
        support = int(getattr(p, "support", 1) or 1)
        if support >= 3:
            return True
        if support >= 2 and str(p.engine).startswith("tesseract"):
            return True
        if support >= 2 and len({v for v in getattr(p, "vote_variants", [])
                                 if v}) >= 2:
            return True
    return False


def _letters_of(text: str) -> str:
    """فقط حروف الفبا (بدون ارقام/فاصله/نماد) برای مقایسه‌ی بریدگی."""
    return "".join(ch for ch in text if ch.isalpha())


def _is_fragment_of_other_line(idx: int, lines: list[RawLine]) -> bool:
    """آیا سطر idx بریده‌ی یک سطر بلندتر است؟ (v1.8.0)

    اگر رشته‌ی حروف سطر، زیررشته‌ی رشته‌ی حروف سطر دیگری با اختلاف طول ≥ ۲
    باشد، سطر یک قطعه‌ی جداشده از همان واژه است (خوانش دو تکه‌ی یک کلمه).
    """
    own = _letters_of(lines[idx].normalized_text)
    if len(own) < 4:
        return False
    for j, other in enumerate(lines):
        if j == idx:
            continue
        other_letters = _letters_of(other.normalized_text)
        if len(other_letters) <= len(own) + 1:
            continue
        if own in other_letters:
            return True
    return False


def _is_repeated_word_line(idx: int, lines: list[RawLine]) -> bool:
    """سطری که همه‌ی واژه‌های حرفی‌اش در سطر دیگری هم هست، نام نیست (v1.8.0).

    ماده‌ی مؤثره معمولاً دو بار روی بسته چاپ می‌شود (زیر برند + در ترکیبات)؛
    برند فقط یک بار. اگر همه‌ی واژه‌های حرفی (طول ≥ ۴) سطر کاندید در سطر
    دیگری هم بیابد، آن سطر «تکرار ماده/متن» است نه نام مستقل.
    """
    import difflib

    own_words = [w for w in lines[idx].normalized_text.split(" ")
                 if len(w) >= 4 and any(ch.isalpha() for ch in w)]
    if not own_words:
        return False
    for j, other in enumerate(lines):
        if j == idx:
            continue
        other_words = other.normalized_text.split(" ")
        hits = 0
        for w in own_words:
            for ow in other_words:
                if w == ow or difflib.SequenceMatcher(None, w, ow).ratio() >= 0.85:
                    hits += 1
                    break
        if own_words and hits == len(own_words):
            return True
    return False


def _clean_ingredient_tokens(val: str) -> str:
    """حذف نخاله‌های پیرامون از مقدار مادهٔ مؤثره (v1.8.0).

    توکن‌های خالصاً عددی، تک‌حرفی/دوحرفی، و ترکیب‌خطی حذف می‌شوند تا از
    سطرهای آلوده (مثل «وی ۹ 6 لانسوپرازول ۳۰ میلی‌گرم») فقط واژه‌های
    معنادار (لانسوپرازول) بیرون بیاید.
    """
    keep: list[str] = []
    for tok in val.split(" "):
        core = tok.strip("،.:؛!؟()«»")
        if not core:
            continue
        alnum = sum(1 for ch in core if ch.isalnum())
        if alnum < 3:
            continue
        if all(ch.isdigit() for ch in core if ch.isalnum()) and \
                any(ch.isdigit() for ch in core):
            continue
        if sum(1 for ch in core if "\u0600" <= ch <= "\u06ff") > 0 and \
                sum(1 for ch in core if ch.isascii() and ch.isalpha()) > 0:
            continue
        keep.append(tok)
    return " ".join(keep)


def _ingredient_from_next_line(idx: int, lines: list[RawLine]) -> tuple[str, RawLine] | None:
    """«حاوی:» در انتهای سطر و مقدار در سطر بعدی (چیدمان دو سطری) — v1.8.0.

    روی جعبه‌های واقعی (مثل لانزول) سطر اول با «حاوی:» تمام می‌شود و سطر
    بعدی «لانسوپرازول ۳۰ میلی‌گرم» است. مقدار فقط وقتی پذیرفته می‌شود که:
    - سطر بعدی بلافاصله زیر سطر فعلی باشد (فاصله ≤ ۲٫۲ برابر ارتفاع)؛
    - بازهٔ x آن‌ها هم‌پوشانی معنادار داشته باشد (ستون واحد)؛
    - شامل الگوی قدرت (عدد + واحد) باشد — سطر ترکیب دارویی تقریباً همیشه
      دوز دارد؛ این شرط جلوی گرفتن سطرهای نامرتبط مثل «موارد مصرف» را می‌گیرد.
    بازگشت: (مقدار بدون الگوی قدرت، سطر شاهد) یا None.
    """
    if idx + 1 >= len(lines):
        return None
    cur, nxt = lines[idx], lines[idx + 1]
    cur_h = max(1, cur.bbox.h)
    if nxt.bbox.y - cur.bbox.y > 2.2 * cur_h:
        return None
    # هم‌پوشانی ستونی
    ix = max(0, min(cur.bbox.x2, nxt.bbox.x2) - max(cur.bbox.x, nxt.bbox.x))
    min_w = max(1, min(cur.bbox.w, nxt.bbox.w))
    if ix / min_w < 0.25:
        return None
    text = nxt.normalized_text
    if not RE_STRENGTH.search(text):
        return None
    val = RE_STRENGTH.sub(" ", text)
    val = cleaned_display_text(val.strip(" :=-،,"))
    val = _clean_ingredient_tokens(val)
    if not val or not _has_alpha(val) or \
            _STRUCTURAL_ONLY_RE.match(val.replace("\u200c", " ").strip()):
        return None
    return val, nxt


def extract_fields(
    lines: list[RawLine],
    product_type: str,
    settings: Settings,
    image_height: int | None = None,
    pieces: list["OcrPiece"] | None = None,
) -> tuple[dict[str, FieldRecord], list[str]]:
    """استخراج همه فیلدها. بازگشت: (فیلدها، هشدارهای استخراج).

    pieces (اختیاری، v1.8.0): قطعه‌های OCR برای اعتبارسنجی چندموتورهٔ نام.
    """
    extraction_warnings: list[str] = []
    consumed: set[int] = set()
    pieces_by_id: dict[str, OcrPiece] = {
        p.id: p for p in (pieces or []) if p.id}

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
        src_line = line
        if st is not None:
            cand = _text_candidate_from_strength(st, line, idx)
            val = cleaned_display_text(
                after[: st.start()].strip(" :=-،,") or st.group(0))
        else:
            # v1.8.0: مقدار = فقط متنِ «بعد از» واژهٔ کلیدی؛ کل سطر (شامل خودِ
            # برچسب مثل «کپسول حاوی:») هرگز مادهٔ مؤثره اعلام نمی‌شود.
            val = _clean_ingredient_tokens(
                cleaned_display_text(after.strip(" :=-،,")))
        if not val or _STRUCTURAL_ONLY_RE.match(
                val.replace("\u200c", " ").strip()) or not _has_alpha(val):
            # v1.8.0: «حاوی:» در انتهای سطر؛ مقدار احتمالاً در سطر بعدی است
            nxt = _ingredient_from_next_line(idx, lines)
            if nxt is None:
                # بعد از واژه کلیدی چیزی خوانا نیست؛ از این سطر ماده مؤثره نمی‌سازیم
                continue
            val, src_line = nxt
            cand = None
        conf = _conf_of(src_line)
        fields["active_ingredient"] = _mk_record(
            "active_ingredient",
            FieldStatus.EXTRACTED if conf >= settings.low_confidence_threshold
            else FieldStatus.UNCERTAIN,
            value=val or None, unit=(cand.unit if cand else None),
            raw_text=src_line.text, source_ids=list(src_line.source_ids),
            confidence=round(conf, 2))
        consumed.add(idx if src_line is line else lines.index(src_line))
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
            if _plausible_name(remainder):
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
    name_idx_list = [] if name_set else _name_candidates(
        consumed, lines, settings, pieces_by_id)
    if name_idx_list:
        # v1.7.0: انتخاب «بالاترین سطرِ باورپذیر» با شرط نزدیکی اطمینان —
        # نام محصول معمولاً بالای بسته است؛ اما اگر سطر بالایی زبالهٔ
        # کم‌اطمینان باشد (فاصلهٔ اطمینان > 0.۱۵ با بهترین کاندید)،
        # اولین کاندیدِ نزدیک به بهترین اطمینان انتخاب می‌شود.
        name_idx_list.sort(key=lambda i: (lines[i].bbox.y, lines[i].bbox.x))
        best_conf = max(
            (lines[i].confidence_mean
             if lines[i].confidence_mean is not None else 0.5)
            for i in name_idx_list)
        threshold = max(best_conf - 0.15, settings.name_min_confidence)
        idx = name_idx_list[0]
        for cand in name_idx_list:
            cand_conf = (lines[cand].confidence_mean
                         if lines[cand].confidence_mean is not None else 0.5)
            if cand_conf >= threshold:
                idx = cand
                break
        line = lines[idx]
        conf = _conf_of(line)
        fields["name"] = _mk_record(
            "name", FieldStatus.EXTRACTED if conf >= settings.low_confidence_threshold
            else FieldStatus.UNCERTAIN,
            value=cleaned_display_text(line.text), unit=None, raw_text=line.text,
            source_ids=list(line.source_ids), confidence=round(conf, 2))
        consumed.add(idx)
        # چندمحصولی: نام دوم معتبر در بخش پایین «تصویر» → درخواست برش یک بسته
        # (v1.7.0) شرط سخت‌گیرانه: نام دوم باید تک‌خطی (فقط فارسی یا فقط لاتین)،
        # نسبت حرف/رقم بالا و طول کافی داشته باشد؛ با OCR آشغال این هشدار کاذب
        # دیگر صادر نمی‌شود.
        ref_h = image_height or max((l.bbox.y2 for l in lines), default=1)
        for other in name_idx_list[1:]:
            other_text = lines[other].normalized_text
            alpha_n = sum(1 for ch in other_text if ch.isalpha())
            latin_n = sum(1 for ch in other_text
                          if ch.isalpha() and "\u0000" <= ch <= "\u024f")
            single_script = latin_n == alpha_n or latin_n == 0
            alnum_ratio = (sum(1 for ch in other_text if ch.isalnum()) /
                           max(1, len(other_text)))
            if lines[other].bbox.y > 0.55 * ref_h and alpha_n >= 4 and \
                    single_script and alnum_ratio >= 0.7 and \
                    _plausible_name(other_text):
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

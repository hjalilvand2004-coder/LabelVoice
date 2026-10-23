# -*- coding: utf-8 -*-
"""خط پردازش اصلی: اعتبارسنجی ← کیفیت ← پیش‌پردازش ← OCR ← استخراج ← پاسخ.

اجزا (پیش‌پردازش، OCR، استخراج، تولید پاسخ، TTS) مستقل و قابل تعویض‌اند.
هیچ متن/تصویری در لاگ‌های پیش‌فرض ثبت نمی‌شود (حریم خصوصی).
"""
from __future__ import annotations

import time

import cv2
import numpy as np

from .config import Settings, load_settings
from .models import (
    AnalysisResult, BoundingBox, FieldRecord, FieldStatus, OcrPiece,
    ProcessingMetadata, ProductType, QualityIssue, RawLine, now_utc_iso,
)
from .ocr import make_provider
from .ocr.base import OcrProvider, OcrUnavailableError
from .ocr.easyocr_provider import EasyOcrProvider
from .ocr.tesseract_provider import TesseractProvider
from .preprocess import auto_deskew, build_variants, crop_fraction
from .preprocess import (
    VARIANT_BINARIZED, VARIANT_GRAY_CLAHE, VARIANT_INK_ISOLATED, VARIANT_ORIGINAL,
)
from .quality import assess_quality
from .stages import image_quality_metrics
from .textnorm import (
    fix_common_label_words,
    normalize_for_matching,
    normalize_digits_ascii,
)
from .validation import validate_and_load, pil_to_bgr
from .extraction import classify_product_type, extract_fields
from .response import build_response, validate_text
from .llm.rewriter import rewrite_with_llm

PRODUCT_TYPE_FA = {
    "medicine": "دارو",
    "general_product": "محصول عمومی",
    "unknown": "نامشخص",
}

MULTI_PRODUCT_NOTE_FA = (
    "در تصاویر چندمحصولی، لطفاً یک بسته را برش بزنید یا انتخاب کنید؛ "
    "اطلاعات چند بسته در یک خروجی ادغام نمی‌شود."
)


class LabelReaderPipeline:
    """هماهنگ‌کننده کل فرایند؛ قابل استفاده از UI و آزمون‌ها."""

    def __init__(self, settings: Settings | None = None,
                 ocr_provider: OcrProvider | None = None):
        self.settings = settings or load_settings()
        self._injected_provider = ocr_provider

    # ---------- ورودی‌ها ----------
    def process_bytes(self, data: bytes, crop: tuple | None = None) -> AnalysisResult:
        img = validate_and_load(
            data,
            max_file_mb=self.settings.max_file_mb,
            max_pixels=self.settings.max_pixels,
        )
        return self.process_pil(img, crop=crop)

    def process_pil(self, pil_image, crop: tuple | None = None,
                    ocr_engine: str | None = None,
                    stage_callback=None) -> AnalysisResult:
        """پردازش کامل؛ اگر stage_callback داده شود، در پایان هر مرحله از
        پنج‌مرحله‌ای ملزومات استاد با payload خروجی/ارزیابی فراخوانی می‌شود."""
        t_total = time.perf_counter()
        durations: dict[str, int] = {}
        warnings_fa: list[str] = []

        def _emit(key: str, payload: dict) -> None:
            if stage_callback is not None:
                try:
                    stage_callback(key, payload)
                except Exception:  # noqa: BLE001 - اعلام هرگز پردازش را نمی‌شکند
                    pass

        bgr = pil_to_bgr(pil_image)
        orig_w, orig_h = bgr.shape[1], bgr.shape[0]

        # ---- مرحله ۱: OpenCV (کیفیت، برش، اصلاح زاویه، بهبود وضوح) ----
        t_stage = time.perf_counter()
        t0 = time.perf_counter()
        metrics, quality_issues = assess_quality(bgr, self.settings)
        durations["quality_ms"] = int((time.perf_counter() - t0) * 1000)
        quality_before = {
            "sharpness": metrics.laplacian_var,
            "contrast": round(float(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).std()), 2),
            "brightness": metrics.mean_brightness,
        }

        # ۲) برش دستی (اختیاری)
        crop_applied = crop is not None
        if crop is not None:
            bgr = crop_fraction(bgr, crop)

        # ۳) صاف‌کردن چرخش کم‌زاویه
        deskew_applied, deskew_angle = False, None
        if self.settings.deskew_max_angle_deg > 0:
            bgr, angle = auto_deskew(bgr, self.settings)
            if angle:
                deskew_applied, deskew_angle = True, round(angle, 2)
                warnings_fa.append(
                    f"چرخش کم‌زاویه تصویر ({deskew_angle} درجه) اصلاح شد.")

        # ۴) نسخه‌های پردازشی
        variants = build_variants(bgr, self.settings)
        durations["opencv_ms"] = int((time.perf_counter() - t_stage) * 1000)
        issues_note = ""
        issue_codes = [i.code for i in quality_issues if i.code != "ok"]
        if issue_codes:
            FA = {"blurry": "تاری", "dark": "نور کم", "bright": "بیش‌نوری",
                  "glare": "انعکاس", "low_resolution": "رزولوشن پایین"}
            issues_note = "ملاحظات کیفیت: " + "، ".join(
                FA.get(c, c) for c in issue_codes)
        _emit("opencv", {
            "quality_before": quality_before,
            "quality_after": image_quality_metrics(variants[VARIANT_ORIGINAL]),
            "crop_applied": crop_applied,
            "deskew_applied": deskew_applied,
            "deskew_angle_deg": deskew_angle,
            "variants": list(variants.keys()),
            "issues_note": issues_note,
            "duration_ms": durations["opencv_ms"],
            "image_bgr": bgr,
        })

        # ۵) OCR روی نسخه‌ها + گیت کیفیت قطعه + امتیازدهی واریانت (v1.7.0)
        t0 = time.perf_counter()
        provider = self._resolve_provider(ocr_engine)
        by_variant: dict[str, list] = {}
        for name, image in variants.items():
            if name == VARIANT_BINARIZED:
                # نسخه دودویی فقط برای مقایسه؛ وقتی خوانش نسخه‌های اصلی ضعیف است
                mean_conf = [p.confidence for vps in by_variant.values()
                             for p in vps if p.confidence is not None]
                if mean_conf and float(np.mean(mean_conf)) >= 0.8:
                    continue
            by_variant[name] = self._filter_pieces(
                provider.run(image, name),
                image_area=int(variants[VARIANT_ORIGINAL].shape[0]) *
                int(variants[VARIANT_ORIGINAL].shape[1]))

        # ۵-ب) موتور دوم مکمل (v1.8.0): EasyOCR فقط نواحی‌ای را پر می‌کند که
        # تسراکت ضعیف خوانده؛ در نبود کتابخانه/مدل، بی‌صدا رد می‌شود.
        engines_used = [provider.name]
        easy_used = False
        if (self._injected_provider is None and
                getattr(self.settings, "dual_engine", False) and
                provider.name.startswith("tesseract")):
            try:
                easy = EasyOcrProvider(self.settings)
                easy_ok, _ = easy.available()
                if easy_ok:
                    easy_names = [
                        n.strip() for n in
                        str(getattr(self.settings, "easyocr_variants",
                                    "original,gray_clahe")).split(",")
                        if n.strip() in variants]
                    for name in easy_names:
                        by_variant.setdefault(f"{name}", []).extend(
                            self._filter_pieces(
                                easy.run(variants[name], name),
                                image_area=int(variants[VARIANT_ORIGINAL].shape[0]) *
                                int(variants[VARIANT_ORIGINAL].shape[1])))
                    engines_used.append("easyocr")
                    easy_used = True
            except Exception:  # noqa: BLE001 — موتور دوم هرگز پردازش را نمی‌شکند
                pass
        durations["ocr_raw_ms"] = int((time.perf_counter() - t0) * 1000)

        variant_results = []
        for name, vps in by_variant.items():
            vconfs = [p.confidence for p in vps if p.confidence is not None]
            variant_results.append({
                "variant": name,
                "pieces": len(vps),
                "chars_total": sum(len(p.text) for p in vps),
                "mean_confidence": (round(sum(vconfs) / len(vconfs), 3)
                                    if vconfs else None),
                "score": round(self._score_variant(vps), 2),
            })

        # ۶) ادغام «بهترین-اول»: مبنا بهترین واریانت؛ بقیه فقط مکمل بدون همپوشانی
        pieces = self._merge_pieces_best_first(by_variant)
        self._assign_ids(pieces)

        # ۷) سطرهای منطقی
        raw_lines = self._build_lines(pieces)

        # ---- مرحله ۲: OCR (اعلام خروجی و ارزیابی) ----
        durations["ocr_ms"] = int((time.perf_counter() - t0) * 1000)
        confs = [p.confidence for p in pieces if p.confidence is not None]
        _emit("ocr", {
            "pieces_count": len(pieces),
            "chars_total": sum(len(p.text) for p in pieces),
            "mean_confidence": (round(sum(confs) / len(confs), 3) if confs
                                else None),
            "lines_count": len(raw_lines),
            "engine": provider.name,
            "lines_preview": [ln.text for ln in raw_lines[:6]],
            "variant_results": variant_results,
            "duration_ms": durations["ocr_ms"],
        })

        # ۸) طبقه‌بندی نوع بسته
        lines_text = [ln.normalized_text for ln in raw_lines]
        product_type, type_note = classify_product_type(lines_text)

        # ۹) استخراج فیلدها
        t0 = time.perf_counter()
        fields, extraction_warnings = extract_fields(
            raw_lines, product_type.value, self.settings,
            image_height=variants[VARIANT_ORIGINAL].shape[0],
            pieces=pieces)
        durations["extraction_ms"] = int((time.perf_counter() - t0) * 1000)

        # ---- مرحله ۳: پردازش متن و کنترل فیلدها (اعلام) ----
        status_counts: dict[str, int] = {}
        for f in fields.values():
            status_counts[f.status.value] = status_counts.get(f.status.value, 0) + 1
        extracted_n = status_counts.get("extracted", 0) + \
            status_counts.get("user_corrected", 0)
        with_evidence = sum(
            1 for f in fields.values()
            if f.status.value in ("extracted", "user_corrected") and f.source_ids)
        coverage = round(100 * with_evidence / extracted_n) if extracted_n else 100
        _emit("fields", {
            "status_counts": status_counts,
            "evidence_coverage": coverage,
            "product_type_fa": PRODUCT_TYPE_FA.get(
                product_type.value, product_type.value),
            "warnings_fa": list(extraction_warnings),
            "duration_ms": durations["extraction_ms"],
        })

        # ۱۰) پاسخ قالبی (و LLM اختیاری)
        t0 = time.perf_counter()
        response_fa = build_response(
            fields, quality_issues, extraction_warnings, len(pieces))
        evidence = self._evidence_for_guard(fields)
        llm_text, llm_reason = rewrite_with_llm(evidence, self.settings)
        if llm_text is not None:
            response_fa = llm_text
        elif self.settings.llm_enabled and llm_reason:
            warnings_fa.append(llm_reason)
        self_check = validate_text(response_fa)
        if not self_check.ok:
            # حکمتی برای خطای سازنده؛ پاسخ امن حداقلی جایگزین می‌شود
            response_fa = (
                "پاسخ تولیدشده از قواعد ایمنی عبور نکرد؛ لطفاً تصویر واضح‌تری "
                "ارائه دهید. " + build_response({}, quality_issues, [], 0))
            self_check = validate_text(response_fa)
        durations["response_ms"] = int((time.perf_counter() - t0) * 1000)

        # ---- مرحله ۴: تولید پاسخ فارسی (اعلام) ----
        _emit("response", {
            "guard_ok": self_check.ok,
            "guard_violations": list(self_check.violations),
            "llm_used": llm_text is not None,
            "length": len(response_fa),
            "preview": response_fa[:200] + ("…" if len(response_fa) > 200 else ""),
            "duration_ms": durations["response_ms"],
        })
        durations["total_ms"] = int((time.perf_counter() - t_total) * 1000)

        notes = [
            "طبقه‌بندی نوع بسته فقط برای انتخاب قالب فیلدهاست و تأیید هویت یا "
            "اصالت محصول محسوب نمی‌شود.",
            type_note,
            "خواندن شماره بارکد به‌تنهایی شناسایی معتبر محصول نیست (بارکدخوان "
            "در این نسخه وجود ندارد).",
        ]

        metadata = ProcessingMetadata(
            engine=" + ".join(engines_used) if easy_used else provider.name,
            languages="+".join(getattr(provider, "last_langs_used", []) or
                               [self.settings.ocr_languages]),
            variants_used=list(variants.keys()),
            image_width=orig_w,
            image_height=orig_h,
            deskew_applied=deskew_applied,
            deskew_angle_deg=deskew_angle,
            durations_ms=durations,
            warnings_fa=warnings_fa,
            notes_fa=notes,
            timestamp_utc=now_utc_iso(),
        )
        return AnalysisResult(
            product_type=product_type,
            product_type_note_fa=type_note,
            ocr_pieces=pieces,
            raw_lines=raw_lines,
            fields=fields,
            quality_issues=quality_issues,
            response_fa=response_fa,
            metadata=metadata,
        )

    # ---------- اصلاح دستی کاربر ----------
    def apply_user_corrections(
        self, result: AnalysisResult, corrections: dict[str, str]
    ) -> AnalysisResult:
        """اصلاح دستی فیلدها با وضعیت user_corrected و حفظ منشأ قبلی."""
        for key, new_value in corrections.items():
            field = result.fields.get(key)
            if field is None:
                continue
            new_value = (new_value or "").strip()
            if not new_value or new_value == field.value:
                continue
            previous = field.value
            field.previous_values = ([previous] if previous else []) + \
                list(field.previous_values)
            field.value = new_value
            field.status = FieldStatus.USER_CORRECTED
            field.confidence = 1.0
            field.note_fa = "مقدار توسط کاربر اصلاح شد؛ مقدار قبلی حفظ شده است."
        # بازتولید پاسخ از فیلدهای اصلاح‌شده
        response = build_response(
            result.fields, result.quality_issues, [], len(result.ocr_pieces))
        check = validate_text(response)
        if not check.ok:
            response = ("پاسخ اصلاح‌شده از قواعد ایمنی عبور نکرد؛ لطفاً مقدار "
                        "واردشده را بررسی کنید.")
        result.response_fa = response
        result.metadata.warnings_fa.append(
            "پاسخ پس از اصلاح دستی بازتولید شد؛ فیلدهای اصلاح‌شده با وضعیت "
            "user_corrected و منشأ قبلی ثبت شدند.")
        return result

    # ---------- ابزارهای داخلی ----------
    _FA_LETTER = "\u0600-\u06ff\u0750-\u077f\ufb50-\ufdff\ufe70-\ufeff"
    _LATIN_LETTER = "a-zA-Z\u00c0-\u024f"
    _FA_DIGIT = "\u06f0-\u06f9\u0660-\u0669"
    _LATIN_DIGIT = "0-9"

    @classmethod
    def _is_mixed_script_garbage(cls, text: str) -> bool:
        """تشخیص زبالهٔ ترکیب‌خطی (v1.8.0) — ریشهٔ خروجی آشغالِ پیشین.

        یک کلمه/قطعهٔ واقعی برچسب از «یک» خط نوشتاری می‌آید. حضور همزمان
        حرف فارسی + حرف لاتین (مثل «کپسولSy») یا رقم فارسی + رقم لاتین
        (مثل «44۵») در «یک قطعه» فقط محصول خوانش خراب است و حذف می‌شود.
        ارقام لاتین با حروف فارسی (مثل «30 میلی‌گرم») مجاز است چون اغلب
        موتورها ارقام را لاتین برمی‌گردانند.
        """
        import re
        has_fa_letter = re.search(f"[{cls._FA_LETTER}]", text) is not None
        has_lat_letter = re.search(f"[{cls._LATIN_LETTER}]", text) is not None
        if has_fa_letter and has_lat_letter:
            return True
        has_fa_digit = re.search(f"[{cls._FA_DIGIT}]", text) is not None
        has_lat_digit = re.search(f"[{cls._LATIN_DIGIT}]", text) is not None
        if has_fa_digit and has_lat_digit:
            return True
        return False

    def _filter_pieces(self, raw: list, image_area: int | None = None) -> list:
        """گیت کیفیت قطعه‌های OCR (v1.7.0 + v1.8.0) — حذف زباله قبل از هر ادغام.

        - نمادهای محض بدون هیچ حرف/رقم (@ ، » ، ° و…) حذف می‌شوند؛
        - کف مطلق اطمینان (settings.piece_conf_floor)؛
        - قطعه‌های خیلی کوتاه باید اطمینان بالاتری داشته باشند؛
        - قطعه‌ی کوتاه با کادر غول‌پیکر (نشان شکست تحلیل چیدمان، مثل یک «3»
          با کادر ۴۳۱×۳۹۴ که کل پایین تصویر را می‌بلعید) حذف می‌شود؛
        - v1.8.0: قطعهٔ ترکیب‌خطی (حرف فارسی + حرف لاتین همزمان) حذف می‌شود.
        این فیلتر جلوی تولید سطرهای فرانکشتاین را می‌گیرد.
        """
        out = []
        for p in raw:
            text = (p.text or "").strip()
            if not text:
                continue
            if self._is_mixed_script_garbage(text):
                continue
            if p.confidence is not None and \
                    p.confidence < self.settings.piece_conf_floor:
                continue
            if not any(ch.isalnum() for ch in text):
                continue
            alnum_n = sum(1 for ch in text if ch.isalnum())
            if len(text) <= self.settings.short_piece_max_len and \
                    (p.confidence is None or
                     p.confidence < self.settings.short_piece_conf_min):
                continue
            if image_area and alnum_n <= 2 and \
                    (p.w * p.h) > 0.15 * image_area:
                continue
            out.append(p)
        return out

    @staticmethod
    def _score_variant(pieces: list) -> float:
        """امتیاز واریانت: مجموع اطمینان × طول مؤثر قطعه‌های معتبر.

        قطعه‌های با کمتر از دو نویسه حرف/رقم سهمی نمی‌گیرند تا واریانت‌هایی که
        فقط نماد و نویز تولید کرده‌اند پایین‌تر از واریانت‌های واقعاً خوانا بمانند.
        """
        score = 0.0
        for p in pieces:
            if p.confidence is None:
                continue
            alnum = sum(1 for ch in (p.text or "") if ch.isalnum())
            if alnum < 2:
                continue
            score += float(p.confidence) * min(alnum, 14)
        return score

    def _merge_pieces_best_first(self, by_variant: dict[str, list]) -> list:
        """ادغام بهترین-اول با رأی‌گیری اجماعی (v1.7.0 + v1.8.0).

        مشکل روش قبلی: ریختن همه قطعه‌های همه واریانت‌ها در یک سبد، سطرهای
        ترکیبی بی‌معنی می‌ساخت (هر واریانت همان کلمه را کمی جابه‌جا/متفاوت
        می‌خواند). اکنون: واریانت با بیشترین امتیاز مبناست؛ سایر واریانت‌ها فقط
        ناحیه‌هایی را پر می‌کنند که هنوز پوشش داده نشده (بدون همپوشانی کادر).

        v1.8.0: هر بار که پیکربندی دیگری همان ناحیه را خواند، «support» قطعهٔ
        نگه‌داشته‌شده یکی بالا می‌رود؛ بعد از ادغام، قطعه‌های «تک‌رأی» با
        اطمینان پایین حذف می‌شوند (نویز تک‌پیکربندی مثل «سس»، «طح»).
        """
        order = sorted(
            by_variant.items(),
            key=lambda kv: self._score_variant(kv[1]), reverse=True)
        # v1.8.0-ز: دو گذرِ ادغام — اول قطعه‌های «سالم» (جعبه‌ی درست)، بعد
        # «فشرده‌ها» فقط برای پر کردن جای خالی. به این ترتیب جعبه‌ی فشرده‌ی
        # EasyOCR نمی‌تواند زودتر از کلمات دقیق تسراکت جای آن‌ها را بگیرد و
        # آن‌ها را بلعیده و واژه‌های تکراری/متناقض بسازد.
        all_items = [(name, p) for name, vps in order for p in vps]
        normal_items = []
        squeezed_items = []
        for name, rp in all_items:
            norm = normalize_for_matching(rp.text)
            n_words = len([w for w in norm.split(" ") if w])
            # جعبهٔ فشرده: عرض به‌ازای هر واژه < ۱٫۶ برابر ارتفاع
            is_squeezed = (n_words >= 2 and rp.h > 0 and
                           rp.w < 1.6 * rp.h * n_words)
            (squeezed_items if is_squeezed else normal_items).append((name, rp))

        kept: list[OcrPiece] = []
        for pass_squeezed, items in ((False, normal_items),
                                     (True, squeezed_items)):
            for _name, rp in items:
                bb = BoundingBox(x=rp.x, y=rp.y, w=rp.w, h=rp.h)
                norm = normalize_for_matching(rp.text)
                duplicated = False
                for ex in kept:
                    # همان ناحیه فیزیکی: IoU بالا یا احتواء با قرینه متنی
                    if not self._same_region(ex.bbox, bb, ex.text, rp.text):
                        continue
                    # قطعهٔ فشرده در گذر دوم فقط رأی می‌دهد؛ ناحیهٔ پوشش‌داده
                    # شده را پر نمی‌کند و جانشین نمی‌شود
                    if not pass_squeezed:
                        ex_norm = normalize_for_matching(ex.text).lower()
                        norm_l = norm.lower()
                        conf_rp = rp.confidence or 0
                        conf_ex = ex.confidence or 0
                        if ex_norm != norm_l:
                            if norm_l in ex_norm or ex_norm in norm_l:
                                # «احتوای متنی»: یکی زیررشتهٔ دیگری است
                                # (خوانش جزئی همان کلمه/عبارت).
                                # v1.8.0-ح: عبارت چندواژه‌ای حق ندارد جای
                                # کلمهٔ دقیق را بگیرد مگر با اطمینان دست‌کم
                                # برابر (جملهٔ شل ۰٫۵۱ نباید کلمهٔ ۰٫۹۰ را
                                # له کند)؛ و برعکس، کلمهٔ دقیقِ بسیار
                                # پراطمینان می‌تواند عبارت کم‌اطمینان را
                                # جایگزین کند.
                                len_gap = abs(len(norm_l) - len(ex_norm))
                                longer_new = len(norm_l) > len(ex_norm)
                                if len_gap >= 2:
                                    multi_in = len(norm_l.split()) >= 2
                                    multi_ex = len(ex_norm.split()) >= 2
                                    if longer_new:
                                        winner_new = (conf_rp >= conf_ex
                                                      if multi_in
                                                      else conf_rp >= 0.5)
                                    else:
                                        winner_new = (conf_rp >= conf_ex + 0.15
                                                      if multi_ex
                                                      else conf_ex < 0.5)
                                elif len_gap == 1:
                                    # خوانش جزئی با یک نویسه کمتر (مثل «۰»
                                    # به‌جای «۳۰» یا BOX به‌جای BOXES):
                                    # کامل‌ترِ هم‌اطمینان (اختلاف ≤ ۰٫۰۵) می‌برد
                                    winner_new = (conf_rp >= conf_ex - 0.05
                                                  if longer_new
                                                  else conf_rp < conf_ex - 0.05)
                                else:
                                    winner_new = conf_rp > conf_ex
                                if winner_new:
                                    ex.text = rp.text
                                    ex.normalized_text = norm
                                    ex.confidence = rp.confidence
                                    ex.variant = rp.variant
                            else:
                                # متفاوت: فقط کامل‌ترِ معتبر جانشین می‌شود
                                # (اطمینان بالا به‌تنهایی کافی نیست؛ خوانش
                                # جزئی آشغال مثل «DA» هم conf بالا می‌گیرد)
                                longer = len(norm_l) > len(ex_norm)
                                same_len_better = (len(norm_l) == len(ex_norm) and
                                                   conf_rp > conf_ex)
                                if (longer or same_len_better) and \
                                        conf_rp >= conf_ex * 0.9:
                                    ex.text = rp.text
                                    ex.normalized_text = norm
                                    ex.confidence = rp.confidence
                                    ex.variant = rp.variant
                    # رأی اجماعی: پیکربندی دیگری هم این ناحیه را خواند
                    ex.support = getattr(ex, "support", 1) + 1
                    duplicated = True
                    break
                if duplicated:
                    continue
                kept.append(OcrPiece(
                    id="", text=rp.text, normalized_text=norm, bbox=bb,
                    confidence=rp.confidence, variant=rp.variant,
                    engine=rp.engine, support=1))
        # --- فیلتر اجماعی (v1.8.0): حذف نویز تک‌رأی کم‌اطمینان ---
        return self._apply_consensus_filter(kept)

    def _apply_consensus_filter(self, pieces: list[OcrPiece]) -> list[OcrPiece]:
        """قطعه‌ای که فقط یک پیکربندی خوانده و اطمینانش پایین است حذف می‌شود.

        کلمات واقعی برچسب معمولاً در چند واریانت/PSM/موتور تکرار خوانده می‌شوند
        (support ≥ 2) یا اطمینان بالایی دارند؛ نویزِ منحصربه‌فردِ کم‌اطمینان
        حذف‌شدنی است. برای تصاویر کم‌متن (زیر آستانهٔ قطعه) فیلتر اعمال
        نمی‌شود تا خروجی خالی نماند.

        v1.8.0-ب: آستانه‌های پله‌ای — قطعه‌های کوتاه (≤۲ نویسه) با تک‌رأی به
        اطمینان بالاتری نیاز دارند، و کادرهای منحط (خیلی نازک/خیلی ریز،
        نشانهٔ خوانش نقطه و خط) همیشه حذف می‌شوند.
        """
        min_n = int(getattr(self.settings, "min_pieces_for_consensus", 6))
        lonely_conf = float(getattr(self.settings, "lonely_piece_conf", 0.55))
        if len(pieces) < min_n:
            kept = [p for p in pieces if not self._is_degenerate_box(p)]
            return kept or pieces
        out = []
        for p in pieces:
            if self._is_degenerate_box(p):
                continue
            support = getattr(p, "support", 1)
            conf = p.confidence
            if support <= 1:
                alnum = sum(1 for ch in p.text if ch.isalnum())
                floor = max(lonely_conf, 0.80) if alnum <= 2 else lonely_conf
                if conf is None or conf < floor:
                    continue
            out.append(p)
        # خروجی خالی نشود: اگر همه رفتند، نسخهٔ کامل برمی‌گردد
        return out if out else pieces

    @staticmethod
    def _is_degenerate_box(p: OcrPiece) -> bool:
        """کادر منحط: خیلی نازک (خط) یا خیلی ریز (نقطه) — همیشه نویز است.

        v1.8.0-ج: نشان‌های گرد/لوگوی درشت با یک رقم/حرف هم فیلتر می‌شوند
        (مثل «۲۸» داخل دایره‌ی بنفش که به‌صورت «۵» با کادر ۱۲۳×۱۳۰ خوانده
        می‌شد و «۵ کپسول» می‌ساخت). متن واقعی تک‌نویسه هرگز این‌قدر درشت و
        مربعی نیست.
        """
        w, h = p.bbox.w, p.bbox.h
        if h < 12 or w < 3:
            return True
        if (w * h) < 60 and len(p.text.strip()) <= 2:
            return True
        alnum = sum(1 for ch in p.text if ch.isalnum())
        if alnum <= 2 and (w * h) >= 8000:
            long_side, short_side = max(w, h), min(w, h)
            if short_side > 0 and long_side / short_side <= 1.6:
                return True
        return False

    @staticmethod
    def _same_region(a: BoundingBox, b: BoundingBox, text_a: str = "",
                     text_b: str = "") -> bool:
        """تشخیص همان ناحیه متن: IoU > 0.4، یا احتواء ≥ 0.55 «با قرینه متنی».

        قرینه متنی = یکی زیررشتهٔ دیگری است (خوانش جزئی) یا شباهت گشتالتی
        ≥ 0.6 (خوانش فازی همان کلمه، مثل MEDIGIN/MEDICINES). بدون قرینه،
        کلمات همسایه با کادرهای همپوشان (چیدمان‌های متراکم) اشتباهاً یکی
        می‌شدند — آزمون امنیتی این خطا را گرفت.
        """
        if a.iou(b) > 0.40:
            return True
        ix = max(0, min(a.x2, b.x2) - max(a.x, b.x))
        iy = max(0, min(a.y2, b.y2) - max(a.y, b.y))
        inter = float(ix * iy)
        if inter <= 0:
            return False
        area_b = float(b.w * b.h)
        area_a = float(a.w * a.h)
        contained = (inter / area_b) >= 0.55 or (inter / area_a) >= 0.55
        if not contained:
            return False
        ta = (text_a or "").strip().lower()
        tb = (text_b or "").strip().lower()
        if not ta or not tb:
            return False
        if ta in tb or tb in ta:
            return True
        import difflib
        return difflib.SequenceMatcher(None, ta, tb).ratio() >= 0.60

    def _resolve_provider(self, ocr_engine: str | None) -> OcrProvider:
        if self._injected_provider is not None:
            return self._injected_provider
        name = ocr_engine or self.settings.ocr_provider
        return make_provider(name, self.settings)

    def _merge_pieces(self, raw: list):
        """حذف قطعه‌های تکراری بین نسخه‌ها (IoU بالا + متن یکسان)."""
        pieces: list[OcrPiece] = []
        for rp in raw:
            bb = BoundingBox(x=rp.x, y=rp.y, w=rp.w, h=rp.h)
            norm = normalize_for_matching(rp.text)
            duplicate = None
            for existing in pieces:
                same_text = existing.normalized_text.lower() == norm.lower()
                if same_text and existing.bbox.iou(bb) > 0.55:
                    if duplicate is None:
                        duplicate = existing
                    elif (existing.confidence or 0) > (duplicate.confidence or 0):
                        duplicate = existing
            if duplicate is not None:
                if (rp.confidence or 0) > (duplicate.confidence or 0):
                    duplicate.confidence = rp.confidence
                    duplicate.variant = rp.variant
                continue
            pieces.append(OcrPiece(
                id="", text=rp.text, normalized_text=norm, bbox=bb,
                confidence=rp.confidence, variant=rp.variant, engine=rp.engine))
        return pieces

    def _assign_ids(self, pieces: list[OcrPiece]) -> None:
        pieces.sort(key=lambda p: (p.bbox.y + p.bbox.h // 2, p.bbox.x))
        for i, p in enumerate(pieces, start=1):
            p.id = f"ocr_{i:03d}"

    def _build_lines(self, pieces: list[OcrPiece]) -> list[RawLine]:
        """ساخت سطرهای منطقی (v1.8.0 — بازنویسی گروه‌بندی).

        سه اصلاح کلیدی نسبت به نسخه قبل:
        ۱. تلورانس Y نسبی: هر قطعه با «میانگین y-مرکز گروه» مقایسه می‌شود
           (نه فقط قطعه قبلی) تا زنجیره‌سو خوردن سطرها در عرض جعبه از بین برود؛
           تلورانس هم نسبت به ارتفاع خود قطعه‌هاست (متن درشت/ریز با هم قاطی نمی‌شود).
        ۲. شکست ستونی: فاصلهٔ افقی بزرگ بین قطعه‌های هم‌سطر (بیش از ۳ برابر
           ارتفاع) یعنی دو بلوک جدا (مثل «کپسول انتریک کوتد» راست و بقیه چپ).
        ۳. حذف خوانش هم‌ستون: دو قطعه در یک سطر که بازهٔ x شان بیش از ۶۰٪ هم‌پوشانی
           دارد، دو خوانش جایگزینِ یک جایگاه‌اند؛ فقط خوانش قوی‌تر می‌ماند.
        """
        import difflib

        if not pieces:
            return []
        ordered = sorted(
            pieces, key=lambda p: (p.bbox.y + p.bbox.h // 2, p.bbox.x))

        # --- ۱) گروه‌بندی سطری با تلورانس نسبی ---
        groups: list[list[OcrPiece]] = []
        cur: list[OcrPiece] = []
        cur_mean_yc: float = 0.0
        for piece in ordered:
            yc = piece.bbox.y + piece.bbox.h // 2
            if not cur:
                cur = [piece]
                cur_mean_yc = float(yc)
                continue
            local_h = float(np.mean([p.bbox.h for p in cur]))
            # v1.8.0-هـ: تلورانس متقارن — ارتفاع «قطعهٔ ورودی» هم لحاظ می‌شود
            # تا قطعه‌های ریز (مثل خوانش‌های ۱۹ پیکسلی) به گروهِ درشت نچسبند.
            tol = max(10.0, 0.55 * (local_h + piece.bbox.h) / 2.0)
            if abs(yc - cur_mean_yc) <= tol:
                cur.append(piece)
                cur_mean_yc = (cur_mean_yc * (len(cur) - 1) + yc) / len(cur)
            else:
                groups.append(cur)
                cur = [piece]
                cur_mean_yc = float(yc)
        if cur:
            groups.append(cur)

        lines: list[RawLine] = []
        from .textnorm import is_mostly_persian
        gi = 0
        for group in groups:
            # --- ۲) شکست ستونی داخل هر گروه ---
            group = sorted(group, key=lambda p: p.bbox.x)
            sub_groups: list[list[OcrPiece]] = [[group[0]]]
            for piece in group[1:]:
                prev = sub_groups[-1][-1]
                gap = piece.bbox.x - prev.bbox.x2
                if gap > 4.5 * max(piece.bbox.h, prev.bbox.h, 14):
                    sub_groups.append([piece])
                else:
                    sub_groups[-1].append(piece)

            for sub in sub_groups:
                gi += 1
                # --- ۳) حذف خوانش هم‌ستون (خوانش جایگزین همان جایگاه) ---
                sub = self._dedupe_column_reads(sub)
                sub = self._dedupe_similar_pieces(sub)
                if not sub:
                    continue
                sub = sorted(sub, key=lambda p: p.bbox.x)
                joined = " ".join(p.text for p in sub)
                if is_mostly_persian(joined):
                    sub = list(reversed(sub))
                text = " ".join(p.text for p in sub).strip()
                # v1.8.0: اصلاح محافظه‌کارانهٔ واژه‌های ساختاری پرتکرار برچسب
                text, _fixes = fix_common_label_words(text)
                norm = normalize_for_matching(text)
                x0 = min(p.bbox.x for p in sub)
                y0 = min(p.bbox.y for p in sub)
                x1 = max(p.bbox.x2 for p in sub)
                y1 = max(p.bbox.y2 for p in sub)
                confs = [p.confidence for p in sub if p.confidence is not None]
                lines.append(RawLine(
                    id=f"line_{gi:03d}",
                    text=text,
                    normalized_text=norm,
                    source_ids=[p.id for p in sub],
                    bbox=BoundingBox(x=x0, y=y0, w=max(1, x1 - x0), h=max(1, y1 - y0)),
                    confidence_mean=(round(sum(confs) / len(confs), 3) if confs else None),
                ))
        return lines

    @staticmethod
    def _dedupe_column_reads(sub: list[OcrPiece]) -> list[OcrPiece]:
        """حذف خوانش‌های جایگزینِ یک جایگاه در یک سطر (v1.8.0).

        وقتی دو قطعه در بازهٔ x بیش از ۶۰٪ هم‌پوشانی دارند (مثل «کپسول» با
        کادر بلند و «سد» خوانش غلطِ داخل همان کادر)، فقط خوانش قوی‌تر
        (اطمینان × وزن پشتیبانی) نگه داشته می‌شود.
        """
        def strength(p: OcrPiece) -> float:
            conf = p.confidence if p.confidence is not None else 0.4
            return conf * (1.0 + 0.25 * (getattr(p, "support", 1) - 1))

        out: list[OcrPiece] = []
        for piece in sorted(sub, key=strength, reverse=True):
            px0, px1 = piece.bbox.x, piece.bbox.x2
            overlaps = False
            for kept in out:
                kx0, kx1 = kept.bbox.x, kept.bbox.x2
                inter = max(0, min(px1, kx1) - max(px0, kx0))
                if inter <= 0:
                    continue
                min_w = max(1, min(px1 - px0, kx1 - kx0))
                if inter / min_w > 0.60:
                    overlaps = True
                    break
            if not overlaps:
                out.append(piece)
        return out

    @staticmethod
    def _dedupe_similar_pieces(group: list[OcrPiece]) -> list[OcrPiece]:
        """حذف خوانش‌های فازی مشابه در یک سطر (مثلاً دو psm)؛ حفظ اطمینان بالاتر.

        فاصله امن: شباهت ≥ 0.8 فقط برای قطعه‌های طول ≥ 3 اعمال می‌شود تا
        ارقام/حروف کوتاه متفاوت (مثل 5 و 6) اشتباهی ادغام نشوند.
        """
        import difflib

        out: list[OcrPiece] = []
        for piece in group:
            replaced = False
            for i, kept in enumerate(out):
                a = kept.normalized_text.strip().lower()
                b = piece.normalized_text.strip().lower()
                if a == b:
                    if (piece.confidence or 0) > (kept.confidence or 0):
                        out[i] = piece
                    replaced = True
                    break
                # قطعه کوتاهِ زیرمجموعه (مثل «2» داخل «B12») حذف می‌شود
                if len(b) <= 3 and len(a) >= 4 and b in a:
                    replaced = True
                    break
                if len(a) <= 3 and len(b) >= 3 and a in b:
                    out[i] = piece
                    replaced = True
                    break
                if len(a) >= 3 and len(b) >= 3 and \
                        difflib.SequenceMatcher(None, a, b).ratio() >= 0.8:
                    if (piece.confidence or 0) > (kept.confidence or 0):
                        out[i] = piece
                    replaced = True
                    break
            if not replaced:
                out.append(piece)
        return out

    def _evidence_for_guard(self, fields: dict[str, FieldRecord]) -> dict:
        return {"fields": {
            key: {
                "value": f.value, "unit": f.unit, "raw_text": f.raw_text,
                "note_fa": f.note_fa,
            } for key, f in fields.items()
        }}

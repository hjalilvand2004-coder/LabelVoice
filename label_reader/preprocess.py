# -*- coding: utf-8 -*-
"""پیش‌پردازش OpenCV — قابل تنظیم و محافظه‌کارانه.

ملاحظه مهم: از پردازش‌هایی که شکل اعداد یا حروف را تغییر دهند پرهیز می‌شود
(بدون threshold سراسری تهاجمی، بدون تغییر شکل نویسه). تصویر اصلی همیشه
حفظ می‌شود و OCR روی چند نسخه اجرا و نتایج مقایسه می‌گردد.
"""
from __future__ import annotations

import cv2
import numpy as np

from .config import Settings

VARIANT_ORIGINAL = "original"
VARIANT_GRAY_CLAHE = "gray_clahe"
# v2.9.0: دو واریانت جدید برای کیفیت بهتر عکس‌های موبایل:
#  - shadow_free: یکنواخت‌سازی نور (حذف سایه/گرادیان روشنایی) با تقسیم بر پس‌زمینه
#  - sharpened: ماسک تیزکننده (Unsharp Mask) — هم‌راستا با نسخهٔ موبایل
VARIANT_SHADOW_FREE = "shadow_free"
VARIANT_SHARPENED = "sharpened"
VARIANT_BINARIZED = "binarized"
VARIANT_WHITE_ON_DARK = "white_on_dark"
VARIANT_INK_ISOLATED = "ink_isolated"


def _odd(n: int) -> int:
    """نزدیک‌ترین عدد فرد بزرگ‌تر یا مساوی (برای اندازهٔ هسته‌های cv2)."""
    return int(n) if int(n) % 2 == 1 else int(n) + 1


def flatten_illumination(gray: np.ndarray) -> np.ndarray:
    """یکنواخت‌سازی نور (v2.9.0) — حذف سایه و گرادیان روشنایی با تقسیم بر پس‌زمینه.

    عکس‌های موبایل از جعبه دارو معمولاً روشنایی نامناسب دارند: یک طرف جعبه
    روشن و طرف دیگر در سایه است. CLAHE در چنین حالتی نویز سایه را هم تقویت
    می‌کند. راه استاندارد (shadow removal کلاسیک):
      ۱) پس‌زمینهٔ روشنایی با morphological close (هستهٔ بیضوی بزرگ ≈ ۱/۸
         کوتاه‌ترین ضلع) برآورد می‌شود — چون متن تیره است، close آن را از
         برآورد پس‌زمینه حذف می‌کند؛
      ۲) تصویر بر پس‌زمینه تقسیم می‌شود: flat = gray / bg × 255؛
      ۳) نتیجه: زمینهٔ هموار روشن و متن تیرهٔ پرکنتراست، مستقل از سایه.
    شکل نویسه‌ها تغییر نمی‌کند (فقط روشنایی مؤثر هر پیکسل عادی‌سازی می‌شود).
    """
    h, w = gray.shape[:2]
    k = _odd(max(31, min(h, w) // 8))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    # هموارسازی ملایم برآورد پس‌زمینه تا پله در نتیجه نیفتد
    bg = cv2.GaussianBlur(bg, (5, 5), 0)
    return cv2.divide(gray, bg, scale=255)


def unsharp_gray(gray: np.ndarray, amount: float = 0.9,
                 ksize: int = 3) -> np.ndarray:
    """ماسک تیزکننده (v2.9.0): gray + amount × (gray − blur(gray)).

    لبه‌های نرم‌شدهٔ عکس دوربین موبایل دوباره برجسته می‌شود؛ تسراکت برای
    رقم‌ها و حروف ریز لبهٔ تیز می‌خواهد. برخلاف فیلترهای مشتق‌گیر تند، شکل
    نویسه تغییر نمی‌کند — فقط لبه‌ها تقویت می‌شوند.
    """
    blur = cv2.GaussianBlur(gray, (_odd(ksize), _odd(ksize)), 0)
    return cv2.addWeighted(gray, 1.0 + amount, blur, -amount, 0)


def upscale_if_needed(bgr: np.ndarray, target_min_side: int) -> np.ndarray:
    """بزرگ‌نمایی کنترل‌شده برای OCR (فقط وقتی تصویر کوچک است).

    v2.9.0: درون‌یابی INTER_LANCZOS4 به‌جای INTER_CUBIC — لانسزوس روی متن
    لبه‌های تمیزتر می‌دهد و وزنی قطعه‌ها در آزمون A/B بهتر شد.
    """
    h, w = bgr.shape[:2]
    min_side = min(h, w)
    if min_side >= target_min_side:
        return bgr
    scale = min(3.0, target_min_side / max(1, min_side))
    new_w, new_h = int(round(w * scale)), int(round(h * scale))
    return cv2.resize(bgr, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)


def to_gray_clahe(bgr: np.ndarray, settings: Settings) -> np.ndarray:
    """خاکستری + نویزگیری دوطرفه + یکنواخت‌سازی نور + CLAHE.

    v2.9.0: یکنواخت‌سازی نور (flatten_illumination) بین نویزگیری و CLAHE
    اضافه شد؛ در عکس‌های با سایه/نور نامناسب، CLAHE دیگر نویز سایه را تقویت
    نمی‌کند و متن در ناحیهٔ سایه هم پرکنتراست می‌شود.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, d=5, sigmaColor=40, sigmaSpace=5)
    gray = flatten_illumination(gray)
    clahe = cv2.createCLAHE(
        clipLimit=settings.clahe_clip_limit,
        tileGridSize=(settings.clahe_tile_size, settings.clahe_tile_size),
    )
    gray = clahe.apply(gray)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def binarize(bgr: np.ndarray) -> np.ndarray:
    """آستانه‌گذاری تطبیقی به‌عنوان نسخه جایگزین برای مقایسه نتایج OCR.

    v2.9.0 — سه بهبود نسبت به نسخهٔ قبل:
    ۱) یکنواخت‌سازی نور قبل از آستانه‌گذاری: در عکس با سایه، آستانهٔ تطبیقی
       روی گرادیان روشنایی خطای دوگانه می‌دهد؛ پس از flatten مسأله حذف می‌شود.
    ۲) اندازهٔ بلوک متناسب با تصویر (≈۱/۲۵ کوتاه‌ترین ضلع، محدود به ۳۱..۹۱):
       پنجرهٔ ثابت ۳۱ برای تصاویر بزرگ نسبت به ارتفاع نویسه کوچک است.
    ۳) medianBlur(3) پایانی: نقطه‌های نمک‌وفلفل حذف می‌شوند بدون آنکه لبهٔ
       نویسه آسیب ببیند.
    نتیجه به BGR سه‌کاناله برگردانده می‌شود تا همه موتورها یک ورودی داشته باشند.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = flatten_illumination(gray)
    h, w = gray.shape[:2]
    block = _odd(max(31, min(91, min(h, w) // 25)))
    bw = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block, 12)
    bw = cv2.medianBlur(bw, 3)
    return cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)


def white_on_dark(bgr: np.ndarray) -> np.ndarray:
    """نسخه ویژه «متن روشن روی پس‌زمینه تیره/میانه» (مثل نام سفید روی جعبه آبی/سبز).

    آستانه‌گذاری تطبیقی معکوس: پیکسل‌های روشن‌تر از همسایگی (متن سفید) به‌عنوان
    پیش‌زمینه علامت می‌خورند و سپس معکوس می‌شوند تا OCR ورودی استاندارد
    (متن تیره روی زمینه روشن) ببیند. اوتسو سراسری در این سناریو شکست می‌خورد
    چون مرز جعبه/میز را جدا می‌کند نه متن/جعبه را (آزمایش v1.7.0 روی نمونه
    جعبه کمک‌دستی: با اوتسو هیچ، با تطبیقی معکوس هر سه واژه خوانده شد).
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    bw = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 51, 12)
    bw = cv2.medianBlur(bw, 3)
    return cv2.cvtColor(cv2.bitwise_not(bw), cv2.COLOR_GRAY2BGR)


def ink_isolated(bgr: np.ndarray) -> np.ndarray:
    """جداسازی جوهر رنگی روی زمینه روشن (v1.8.0).

    متن رنگی (آبی/بنفش/قرمز/سبز) روی جعبه سفید در کانال خاکستری کم‌کنتراست
    می‌شود و تسراکت آن را یا نمی‌بیند یا خراب می‌خواند. با 255 - max(B,G,R)
    هر جوهری (هرچه رنگی‌تر باشد کانالی بالاتر دارد) به جوهر تیره روی زمینه
    روشن تبدیل می‌شود؛ سفیدی زمینه در هر سه کانال بالاست و روشن می‌ماند.
    آزمایش روی جعبه لانزول: «کپسول انتریک کوتد» بنفش فقط با همین واریانت
    + PSM 11 خوانا شد؛ کانال آبی معکوس هم «کیسول انتریک کوند» داد.
    """
    max_ch = cv2.max(cv2.max(bgr[:, :, 0], bgr[:, :, 1]), bgr[:, :, 2])
    ink = 255 - max_ch
    ink = cv2.GaussianBlur(ink, (3, 3), 0)
    return cv2.cvtColor(ink, cv2.COLOR_GRAY2BGR)


def estimate_skew_angle(bgr: np.ndarray) -> float:
    """برآورد زاویه چرخش سطرهای متن (درجه). مثبت = نیاز به چرخش پادساعتگرد.

    v2.9.0 — دو مرحله‌ای شد:
    ۱) کاندید درشت با minAreaRect (مثل قبل)؛
    ۲) پالایش موضعی با «واریانس پروفایل سطرها»: در زاویهٔ درست، سطرهای متن
       تراز می‌شوند و نمودار مجموع پیکسل‌های هر سطر قله‌های تیز دارد؛ پس
       زاویه‌ای که واریانس پروفایل را بیشینه کند برنده است. جست‌وجو در
       بازهٔ ±۲ درجه حول کاندید با گام ۰٫۵ درجه انجام می‌شود (سرعت بالا،
       دقت بهتر؛ minAreaRect به‌تنهایی روی متن پراکنده گاهی چند درجه خطا دارد).
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    if max(h, w) > 700:  # نسخهٔ کوچک برای سرعت — زاویه تغییری نمی‌کند
        s = 700 / max(h, w)
        gray = cv2.resize(gray, (max(1, int(w * s)), max(1, int(h * s))),
                          interpolation=cv2.INTER_AREA)
    h, w = gray.shape[:2]
    bw = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 35, 20)
    # اتصال حروف هر سطر برای پیدا کردن مستطیل سطرها
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 3))
    merged = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel)
    coords = cv2.findNonZero(merged)
    if coords is None or len(coords) < 50:
        return 0.0
    rect = cv2.minAreaRect(coords)
    coarse = rect[2]
    if coarse > 45:
        coarse -= 90
    elif coarse < -45:
        coarse += 90

    def _profile_variance(angle_deg: float) -> float:
        m = cv2.getRotationMatrix2D((w / 2, h / 2), angle_deg, 1.0)
        rot = cv2.warpAffine(bw, m, (w, h), flags=cv2.INTER_NEAREST,
                             borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        rows = rot.astype(np.float32).sum(axis=1)
        return float(rows.var())

    candidates = {0.0, coarse}
    step, d = 0.5, -2.0
    while d <= 2.001:
        candidates.add(round(coarse + d, 2))
        d += step
    best_angle, best_score = coarse, -1.0
    for cand in sorted(candidates):
        if abs(cand) > 45:
            continue
        sc = _profile_variance(cand)
        if sc > best_score:
            best_score, best_angle = sc, cand
    angle = best_angle
    if angle > 45:
        angle -= 90
    elif angle < -45:
        angle += 90
    return float(angle)


def rotate_bgr(bgr: np.ndarray, angle_deg: float) -> np.ndarray:
    h, w = bgr.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    return cv2.warpAffine(
        bgr, matrix, (w, h), flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE)


def auto_deskew(bgr: np.ndarray, settings: Settings) -> tuple[np.ndarray, float]:
    """اصلاح چرخش کم‌زاویه؛ زاویه‌های بزرگ قابل اعتماد نیستند و دست نمی‌خورند."""
    angle = estimate_skew_angle(bgr)
    if 0.5 <= abs(angle) <= settings.deskew_max_angle_deg:
        return rotate_bgr(bgr, angle), angle
    return bgr, 0.0


def crop_fraction(bgr: np.ndarray, box: tuple[float, float, float, float]) -> np.ndarray:
    """برش با کسری از ابعاد تصویر: (x, y, w, h) هرکدام 0..1."""
    h, w = bgr.shape[:2]
    fx, fy, fw, fh = box
    x0 = int(round(max(0.0, fx) * w))
    y0 = int(round(max(0.0, fy) * h))
    x1 = int(round(min(1.0, fx + fw) * w))
    y1 = int(round(min(1.0, fy + fh) * h))
    if x1 - x0 < 10 or y1 - y0 < 10:
        return bgr
    return bgr[y0:y1, x0:x1].copy()


def shadow_free(bgr: np.ndarray) -> np.ndarray:
    """واریانت حذف سایه (v2.9.0): خاکستری + یکنواخت‌سازی نور + نویزگیری ملایم.

    پس از تقسیم بر پس‌زمینه، دانه‌های نویز هم تقویت می‌شوند؛ یک گذر
    bilateralFilter(d=5) آن‌ها را می‌گیرد بدون آنکه لبهٔ متن آسیب ببیند.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    flat = flatten_illumination(gray)
    flat = cv2.bilateralFilter(flat, d=5, sigmaColor=40, sigmaSpace=5)
    return cv2.cvtColor(flat, cv2.COLOR_GRAY2BGR)


def build_variants(bgr: np.ndarray, settings: Settings) -> dict[str, np.ndarray]:
    """ساخت نسخه‌های پردازشی؛ تصویر اصلی حفظ و بازگردانده می‌شود.

    واریانت white_on_dark برای متن روشن روی جعبه‌های تیره (v1.7.0)،
    ink_isolated برای جوهر رنگی روی زمینه روشن (v1.8.0) و
    shadow_free/sharpened برای عکس‌های سایه‌دار/نرم موبایل (v2.9.0)
    اضافه شده‌اند.
    """
    variants, _trace = build_variants_traced(bgr, settings, collect_trace=False)
    return variants


def build_variants_traced(
    bgr: np.ndarray, settings: Settings, collect_trace: bool = True,
) -> tuple[dict[str, np.ndarray], list[dict]]:
    """نسخهٔ ردیابی‌شدهٔ build_variants (v2.6.0) — برای نمایش گام‌به‌گام.

    خروجی دوم، فهرست گام‌های OpenCV است: هر گام شامل کلید، عنوان و توضیح
    فارسیِ عین عملیات انجام‌شده با cv2 و خودِ تصویر حاصل از همان گام، تا
    کاربر «تغییراتی که OpenCV روی تصویر ایجاد می‌کند» را ببیند.
    تصاویر اشاره‌گرِ همان آرایه‌های در حال پردازش‌اند (بدون کپی اضافی)؛
    با collect_trace=False فقط واریانت‌ها ساخته می‌شود.
    """
    trace: list[dict] = []

    def _add(step: str, title_fa: str, desc_fa: str, image: np.ndarray) -> None:
        if collect_trace:
            trace.append({"step": step, "title_fa": title_fa,
                          "desc_fa": desc_fa, "image_bgr": image})

    # ---- گام ۱: بزرگ‌نمایی کنترل‌شده ----
    min_side = min(bgr.shape[:2])
    base = upscale_if_needed(bgr, settings.target_min_side)
    if base.shape[0] != bgr.shape[0] or base.shape[1] != bgr.shape[1]:
        _add(
            VARIANT_ORIGINAL, "بزرگ‌نمایی کنترل‌شده (cv2.resize)",
            f"کوتاه‌ترین ضلع تصویر {min_side} پیکسل بود؛ برای موتورهای OCR "
            f"تا رسیدن به ~{settings.target_min_side} پیکسل با درون‌یابی "
            "لانسزوس (INTER_LANCZOS4، حداکثر ۳ برابر) بزرگ شد — لبه‌های "
            "تمیزتر نسبت به درون‌یابی مکعبی. تصاویر بزرگ‌تر از این آستانه "
            "دست نمی‌خورند.",
            base)
    else:
        _add(
            VARIANT_ORIGINAL, "تصویر اصلی (بدون بزرگ‌نمایی)",
            f"کوتاه‌ترین ضلع تصویر {min_side} پیکسل است و از آستانهٔ "
            f"{settings.target_min_side} بیشتر است؛ بنابراین تغییر مقیاسی "
            "اعمال نشد — نسخهٔ «original» همان تصویر ورودی مرحله OpenCV است.",
            base)

    # ---- گام ۲: خاکستری + نویز‌گیری دوطرفه + یکنواخت‌سازی نور + CLAHE ----
    variants: dict[str, np.ndarray] = {VARIANT_ORIGINAL: base}
    variants[VARIANT_GRAY_CLAHE] = to_gray_clahe(base, settings)
    _add(
        VARIANT_GRAY_CLAHE, "خاکستری + حذف نویز + یکنواخت‌سازی نور + CLAHE",
        "۱) cv2.cvtColor به خاکستری؛ ۲) cv2.bilateralFilter (d=5) برای نرم‌کردن "
        "نویز بدون له‌کردن لبهٔ حروف؛ ۳) یکنواخت‌سازی نور: پس‌زمینهٔ روشنایی با "
        "cv2.morphologyEx CLOSE (هستهٔ بیضوی ≈۱/۸ ضلع) برآورد و تصویر بر آن "
        "تقسیم می‌شود تا سایه و گرادیان نور حذف شود؛ ۴) cv2.createCLAHE + apply "
        f"برای تقویت کنتراست موضعی (clip={settings.clahe_clip_limit}، شبکهٔ "
        f"{settings.clahe_tile_size}×{settings.clahe_tile_size}). متن در سایه "
        "هم اکنون پرکنتراست است.",
        variants[VARIANT_GRAY_CLAHE])

    # ---- گام ۳ (جدید v2.9.0): یکنواخت‌سازی نور خالص (حذف سایه) ----
    variants[VARIANT_SHADOW_FREE] = shadow_free(base)
    _add(
        VARIANT_SHADOW_FREE, "حذف سایه و یکنواخت‌سازی نور (تقسیم بر پس‌زمینه)",
        "cv2.morphologyEx CLOSE با هستهٔ بیضوی بزرگ، پس‌زمینهٔ روشنایی را "
        "برآورد می‌کند (متن تیره از برآورد حذف می‌شود)؛ سپس cv2.divide تصویر "
        "را بر پس‌زمینه تقسیم می‌کند: نتیجه، جعبه‌ای است که انگار با نور یکنواخت "
        "عکس گرفته شده — سایهٔ گوشهٔ تصویر و گرادیان نور حذف و متن تیرهٔ "
        "پرکنتراست می‌شود. این نسخه برای عکس‌های با سایهٔ سنگین نجات‌دهنده است.",
        variants[VARIANT_SHADOW_FREE])

    # ---- گام ۴ (جدید v2.9.0): تیزکردن لبه‌ها (Unsharp Mask) ----
    gc_gray = cv2.cvtColor(
        variants[VARIANT_GRAY_CLAHE], cv2.COLOR_BGR2GRAY)
    variants[VARIANT_SHARPENED] = cv2.cvtColor(
        unsharp_gray(gc_gray, 0.9), cv2.COLOR_GRAY2BGR)
    _add(
        VARIANT_SHARPENED, "تیزکردن لبه‌ها (Unsharp Mask)",
        "مقدار جدید = خاکستری + ۰٫۹ × (خاکستری − GaussianBlur ۳×۳) با "
        "cv2.addWeighted. لبه‌های نرم‌شدهٔ عکس دوربین موبایل دوباره برجسته "
        "می‌شود؛ رقم‌های ریز (تاریخ انقضا، شماره سری) برای OCR خواناتر می‌شوند. "
        "شکل نویسه تغییر نمی‌کند — فقط لبه‌ها تقویت می‌شوند.",
        variants[VARIANT_SHARPENED])

    # ---- گام ۵: آستانه‌گذاری تطبیقی (اختیاری) ----
    if settings.use_binarized_variant:
        variants[VARIANT_BINARIZED] = binarize(base)
        _block_desc = _odd(max(31, min(91, min(base.shape[:2]) // 25)))
        _add(
            VARIANT_BINARIZED, "آستانه‌گذاری تطبیقی (دودویی)",
            "۱) یکنواخت‌سازی نور (حذف سایه)؛ ۲) cv2.adaptiveThreshold گاوسی با "
            f"بلوک {_block_desc} (متناسب با ابعاد تصویر، C=۱۲): هر پیکسل نسبت به "
            "میانگین همسایگی‌اش سیاه/سفید می‌شود؛ ۳) cv2.medianBlur(3) حذف نقاط "
            "نمک‌وفلفل. این نسخه فقط برای «مقایسهٔ خوانش» است — اگر خوانش "
            "نسخه‌های اصلی خوب باشد، به OCR داده نمی‌شود چون آستانهٔ تهاجمی "
            "می‌تواند شکل نویسه را تغییر دهد.",
            variants[VARIANT_BINARIZED])

    # ---- گام ۶: متن روشن روی زمینهٔ تیره ----
    variants[VARIANT_WHITE_ON_DARK] = white_on_dark(base)
    _add(
        VARIANT_WHITE_ON_DARK, "متن روشن روی زمینهٔ تیره (معکوس‌سازی تطبیقی)",
        "GaussianBlur(3×3) + cv2.adaptiveThreshold با THRESH_BINARY_INV "
        "(بلوک ۵۱، C=۱۲) + medianBlur(3) و در پایان bitwise_not. برای نام‌های "
        "سفید روی جعبهٔ آبی/سبز: پیکسل‌های روشن‌تر از همسایگی (متن سفید) "
        "علامت می‌خورند و سپس معکوس می‌شوند تا OCR ورودی استاندارد "
        "(متن تیره روی زمینهٔ روشن) ببیند.",
        variants[VARIANT_WHITE_ON_DARK])

    # ---- گام ۷: جداسازی جوهر رنگی ----
    if getattr(settings, "use_ink_isolated_variant", True):
        variants[VARIANT_INK_ISOLATED] = ink_isolated(base)
        _add(
            VARIANT_INK_ISOLATED, "جداسازی جوهر رنگی (255 − max(B,G,R))",
            "بیشینهٔ سه کانال رنگی گرفته می‌شود و از ۲۵۵ کم می‌شود: هر جوهر "
            "رنگی (آبی/بنفش/قرمز/سبز) که در خاکستری کم‌کنتراست می‌شود، به "
            "جوهر تیره روی زمینهٔ روشن تبدیل می‌شود؛ زمینهٔ سفید در هر سه "
            "کانال بالاست و روشن می‌ماند. سپس GaussianBlur ملایم. کمک‌خوان "
            "متن رنگی روی جعبهٔ سفید.",
            variants[VARIANT_INK_ISOLATED])

    return variants, trace

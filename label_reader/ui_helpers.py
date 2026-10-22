# -*- coding: utf-8 -*-
"""ابزارهای رابط کاربری: استایل راست‌به‌چپ، رسم کادرها، جدول فیلدها."""
from __future__ import annotations

import io

from PIL import Image, ImageDraw

from .models import AnalysisResult, FieldRecord, FieldStatus, OcrPiece

RTL_CSS = """
<style>
@import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css');
html, body, [class*="css"], .stApp, .stMarkdown, .stText, .stDataFrame {
    font-family: 'Vazirmatn', 'Tahoma', sans-serif !important;
}
.stApp { background: #ffffff; direction: rtl; }
.main .block-container { direction: rtl; text-align: right; }
h1, h2, h3, h4, p, li, label, span { text-align: right; }
[data-testid="stSidebar"] { direction: rtl; text-align: right; }
.big-answer {
    direction: rtl; text-align: right; font-size: 1.25rem; line-height: 2.1;
    padding: 1.1rem 1.3rem; border-radius: 12px;
    background: #f8fafc; border: 1px solid #e2e8f0; color: #0f172a;
}
.field-status-extracted { color: #166534; font-weight: 600; }
.field-status-uncertain { color: #92400e; font-weight: 600; }
.field-status-missing { color: #6b7280; font-weight: 600; }
.field-status-conflicting { color: #991b1b; font-weight: 600; }
.field-status-user_corrected { color: #1d4ed8; font-weight: 600; }
.privacy-note {
    direction: rtl; text-align: right; font-size: 0.9rem; color: #475569;
    padding: 0.6rem 0.9rem; background: #fffbeb; border: 1px solid #fde68a;
    border-radius: 10px;
}
</style>
"""

STATUS_FA = {
    FieldStatus.EXTRACTED: "استخراج‌شده",
    FieldStatus.UNCERTAIN: "نامطمئن",
    FieldStatus.MISSING: "غایب",
    FieldStatus.CONFLICTING: "متناقض",
    FieldStatus.USER_CORRECTED: "اصلاح کاربر",
}

PRODUCT_TYPE_FA = {
    "medicine": "دارو",
    "general_product": "محصول عمومی",
    "unknown": "نامشخص",
}


def inject_rtl(st) -> None:
    st.markdown(RTL_CSS, unsafe_allow_html=True)


def draw_ocr_boxes(pil_image: Image.Image, pieces: list[OcrPiece]) -> Image.Image:
    """تصویر با کادر نارنجی روی نواحی OCR و برچسب شناسه قطعه."""
    out = pil_image.copy()
    draw = ImageDraw.Draw(out)
    for p in pieces:
        x0, y0 = p.bbox.x, p.bbox.y
        x1, y1 = p.bbox.x2, p.bbox.y2
        draw.rectangle([x0, y0, x1, y1], outline=(234, 88, 12), width=3)
        label = f"{p.id} ({int((p.confidence or 0) * 100)}%)"
        draw.text((x0 + 2, max(0, y0 - 14)), label, fill=(194, 65, 12))
    return out


def fields_to_rows(fields: dict[str, FieldRecord]) -> list[dict]:
    rows = []
    for f in fields.values():
        rows.append({
            "فیلد": f.label_fa,
            "مقدار": f.value or "—",
            "واحد": f.unit or "—",
            "وضعیت": STATUS_FA.get(f.status, str(f.status)),
            "اطمینان": (f"{round((f.confidence or 0) * 100)}%" if f.confidence is not None else "—"),
            "شواهد": ", ".join(f.source_ids) if f.source_ids else "—",
        })
    return rows


def editable_fields(fields: dict[str, FieldRecord]) -> dict[str, FieldRecord]:
    """فیلدهای قابل اصلاح دستی (حذف موارد غایب بدون شواهد)."""
    return {k: v for k, v in fields.items()
            if k in ("name", "strength", "count", "active_ingredient",
                     "dosage_form", "manufacturer", "batch",
                     "production_date", "expiry_date", "storage")}


def result_to_download(result: AnalysisResult) -> bytes:
    return result.to_json_bytes()


def pil_to_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()

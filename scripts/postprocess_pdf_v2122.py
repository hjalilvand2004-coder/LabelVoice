# -*- coding: utf-8 -*-
"""پست‌پروسس PDF v2.12.2 — شماره صفحه (جلد و صفحهٔ پایانی بدون شماره) + متادیتای فارسی"""
import io
from pathlib import Path

import reportlab
from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

SRC = Path("/home/z/my-project/download/LabelVoice-Documentation-v2.12.2/LabelVoice-Documentation-v2.12.2-raw.pdf")
DST = Path("/home/z/my-project/download/LabelVoice-Documentation-v2.12.2/LabelVoice-Documentation-v2.12.2.pdf")
FONT = Path("/home/z/my-project/download/LabelVoice-Documentation-v2.12.2/fonts/Vazirmatn-Regular.ttf")

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

pdfmetrics.registerFont(TTFont("Vazir", str(FONT)))

reader = PdfReader(str(SRC))
writer = PdfWriter()
n = len(reader.pages)
print("pages:", n)


def footnote_page(num: int, w: float, h: float):
    """اورلی شماره صفحه در پایین وسط"""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))
    c.setFont("Vazir", 8.5)
    c.setFillColor(HexColor("#64748b"))
    c.drawCentredString(w / 2, 16, str(num).translate(FA_DIGITS))
    c.save()
    buf.seek(0)
    return PdfReader(buf).pages[0]


for i, page in enumerate(reader.pages):
    if 0 < i < n - 1:  # جلد (i=0) و صفحهٔ پایانی بدون شماره
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)
        page.merge_page(footnote_page(i + 1, w, h))
    writer.add_page(page)

writer.add_metadata({
    "/Title": "برچسب‌خوان هوشمند دارو و محصولات (LabelVoice) — مستندات فنی نسخهٔ ۲.۱۲.۲",
    "/Author": "حمید جلیلوند و نوید بدری",
    "/Subject": "معماری، مدل صوتی لوکال Piper، WBS و نقشهٔ درختی مخزن",
    "/Creator": "LabelVoice docs pipeline",
})
with open(DST, "wb") as f:
    writer.write(f)
print("OK:", DST, DST.stat().st_size, "bytes")

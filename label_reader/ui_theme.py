# -*- coding: utf-8 -*-
"""تم بصری LabelVoice — CSS حرفه‌ای، رنگ‌های مراحل و اجازهٔ HTML (v1.8.0).

پالت: سرمه‌ای عمیق + فیروزه‌ای دارویی + گرادیان بنفش-آبی؛
هر مرحلهٔ پردازش رنگ اختصاصی دارد تا کاربر همیشه بداند الان
کدام مرحله در حال انجام است.
"""
from __future__ import annotations

# ---------- رنگ اختصاصی هر مرحله ----------
STAGE_COLORS: dict[str, str] = {
    "opencv": "#2563eb",    # آبی — پیش‌پردازش تصویر
    "ocr": "#7c3aed",       # بنفش — موتور خوانش
    "fields": "#ea580c",    # نارنجی — پردازش متن و فیلدها
    "response": "#059669",  # سبز — تولید پاسخ
    "tts": "#db2777",       # صورتی — خوانش صوتی
}
STAGE_ICONS: dict[str, str] = {
    "opencv": "🖼️",
    "ocr": "🔤",
    "fields": "📋",
    "response": "💬",
    "tts": "🔊",
}

THEME_CSS = """
<style>
@import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css');

:root {
  --lv-primary: #0f2b46;
  --lv-accent: #0e7c8f;
  --lv-accent2: #7c3aed;
  --lv-bg: #f4f7fb;
}
html, body, [class*="css"], .stApp, .stMarkdown, button, input, textarea,
.stRadio label, .stSelectbox label, .stCheckbox label, .stSlider label {
  font-family: 'Vazirmatn', 'Tahoma', sans-serif !important;
}
.stApp { background:
  radial-gradient(1200px 400px at 90% -50px, rgba(124,58,237,.08), transparent),
  radial-gradient(1000px 380px at 5% -40px, rgba(14,124,143,.10), transparent),
  var(--lv-bg);
}
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 1.2rem; max-width: 1200px; }

/* ---------- سایدبار ---------- */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0f2b46 0%, #123a5c 55%, #0e7c8f 140%);
}
section[data-testid="stSidebar"] * { color: #eaf2f8 !important; }
section[data-testid="stSidebar"] .stRadio label {
  background: rgba(255,255,255,.07);
  border: 1px solid rgba(255,255,255,.12);
  border-radius: 12px; padding: 8px 12px; margin-bottom: 4px;
  transition: all .2s ease;
}
section[data-testid="stSidebar"] .stRadio label:hover {
  background: rgba(255,255,255,.16); transform: translateX(-3px);
}
.lv-brand {
  text-align: center; padding: 14px 8px 10px;
  border-bottom: 1px solid rgba(255,255,255,.15); margin-bottom: 10px;
}
.lv-brand .logo {
  font-size: 42px; line-height: 1;
  filter: drop-shadow(0 4px 10px rgba(0,0,0,.35));
}
.lv-brand h1 {
  font-size: 19px; margin: 8px 0 2px; font-weight: 800; color: #fff;
}
.lv-brand p { font-size: 11.5px; color: #a8c6d8 !important; margin: 0; }
.lv-version {
  display: inline-block; margin-top: 6px; padding: 2px 10px; font-size: 10.5px;
  background: rgba(14,124,143,.35); border: 1px solid rgba(14,124,143,.6);
  border-radius: 999px; color: #c9f0f7 !important;
}

/* ---------- هیرو ---------- */
.lv-hero {
  background: linear-gradient(135deg, #0f2b46 0%, #14496e 45%, #0e7c8f 100%);
  border-radius: 20px; padding: 26px 28px; color: #fff;
  box-shadow: 0 12px 30px rgba(15,43,70,.25); margin-bottom: 14px;
  position: relative; overflow: hidden;
}
.lv-hero::after {
  content: '💊'; position: absolute; left: 18px; top: 50%;
  transform: translateY(-50%); font-size: 84px; opacity: .16;
}
.lv-hero h1 { font-size: 26px; font-weight: 900; margin: 0 0 6px; }
.lv-hero p { font-size: 14px; margin: 0; color: #d7e9f4; max-width: 88%; }
.lv-hero .authors {
  display: inline-flex; align-items: center; gap: 6px; margin-top: 12px;
  background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.2);
  padding: 5px 14px; border-radius: 999px; font-size: 12.5px;
}

/* ---------- کارت‌ها و چیپ‌ها ---------- */
.lv-card {
  background: #fff; border-radius: 16px; padding: 18px 20px;
  border: 1px solid #e3eaf2; box-shadow: 0 4px 14px rgba(15,43,70,.06);
  margin-bottom: 12px;
}
.lv-scope {
  background: linear-gradient(90deg, #eef7f9, #f6f0fd);
  border: 1px solid #cfe4ea; border-right: 5px solid var(--lv-accent);
  border-radius: 12px; padding: 12px 16px; font-size: 13px; color: #234;
  margin-bottom: 12px;
}
.lv-big-answer {
  background: #fff; border-radius: 16px; padding: 20px 22px; font-size: 16.5px;
  line-height: 2.1; color: #1a2b3c; border: 1px solid #dbe7ef;
  border-right: 6px solid var(--lv-accent);
  box-shadow: 0 4px 16px rgba(15,43,70,.07);
}
.lv-field-chip {
  display: inline-block; padding: 3px 10px; border-radius: 999px;
  font-size: 11.5px; font-weight: 700; margin-inline-start: 6px;
}
.chip-extracted { background: #dcfce7; color: #166534; }
.chip-uncertain { background: #fef9c3; color: #854d0e; }
.chip-missing { background: #f1f5f9; color: #475569; }
.chip-conflicting { background: #fee2e2; color: #991b1b; }
.chip-user_corrected { background: #e0e7ff; color: #3730a3; }

/* ---------- خط‌زمان مراحل رنگی ---------- */
.lv-timeline { direction: rtl; padding: 6px 2px; }
.lv-stage {
  display: flex; align-items: stretch; gap: 0; margin-bottom: 2px;
}
.lv-stage .rail {
  width: 34px; display: flex; flex-direction: column; align-items: center;
}
.lv-stage .dot {
  width: 30px; height: 30px; border-radius: 50%; display: flex;
  align-items: center; justify-content: center; font-size: 14px;
  color: #fff; box-shadow: 0 3px 8px rgba(0,0,0,.18); z-index: 2;
  flex-shrink: 0;
}
.lv-stage .line {
  width: 3px; flex: 1; background: #d7e0ea; margin: 2px 0;
}
.lv-stage.done .line { background: linear-gradient(#c9d6e2, #c9d6e2); }
.lv-stage .body {
  flex: 1; background: #fff; border: 1px solid #e6edf4; border-radius: 12px;
  padding: 10px 14px; margin: 0 10px 12px 0;
  border-right-width: 4px; box-shadow: 0 2px 8px rgba(15,43,70,.05);
}
.lv-stage .body h4 { margin: 0 0 4px; font-size: 14px; font-weight: 800; }
.lv-stage .body .meta {
  font-size: 11.5px; color: #64748b; margin-bottom: 4px;
}
.lv-stage .body .outs { font-size: 12.5px; color: #334155; line-height: 1.9; }
.lv-stage .mrow { font-size: 12px; color: #475569; margin-top: 4px; }
.lv-stage.active .dot { animation: lv-pulse 1.2s infinite; }
@keyframes lv-pulse {
  0% { box-shadow: 0 0 0 0 rgba(124,58,237,.45); }
  70% { box-shadow: 0 0 0 12px rgba(124,58,237,0); }
  100% { box-shadow: 0 0 0 0 rgba(124,58,237,0); }
}
.lv-status-pill {
  display: inline-block; font-size: 10.5px; padding: 1px 9px;
  border-radius: 999px; margin-inline-start: 8px; font-weight: 700;
}
.lv-pill-run { background: #ede9fe; color: #6d28d9; }
.lv-pill-done { background: #dcfce7; color: #15803d; }
.lv-pill-fail { background: #fee2e2; color: #b91c1c; }

/* ---------- کارت طراحان ---------- */
.lv-author {
  background: linear-gradient(135deg, #ffffff, #f4f9fc);
  border: 1px solid #dfe9f2; border-radius: 18px; padding: 24px;
  text-align: center; box-shadow: 0 6px 18px rgba(15,43,70,.07);
}
.lv-author .avatar {
  width: 84px; height: 84px; border-radius: 50%; margin: 0 auto 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 38px; color: #fff;
  background: linear-gradient(135deg, #0e7c8f, #7c3aed);
  box-shadow: 0 6px 16px rgba(14,124,143,.35);
}
.lv-author h3 { margin: 0 0 4px; font-weight: 900; }
.lv-author .role { color: #64748b; font-size: 12.5px; margin-bottom: 10px; }
.lv-metric-tile {
  background: #fff; border-radius: 14px; padding: 14px 16px;
  border: 1px solid #e3eaf2; text-align: center;
}
.lv-metric-tile .v { font-size: 24px; font-weight: 900; color: #0f2b46; }
.lv-metric-tile .k { font-size: 12px; color: #64748b; }
</style>
"""


def stage_timeline_html(records: list[dict], running_key: str | None = None) -> str:
    """ساخت HTML خط‌زمان مراحل با رنگ اختصاصی هر مرحله.

    records: خروجی build_stage_item به ترتیب تکمیل.
    running_key: کلید مرحله‌ای که در حال انجام است (برای انیمیشن نبض).
    """
    from .stages import STAGE_DEFS

    order = [s["key"] for s in STAGE_DEFS]
    by_key = {r["key"]: r for r in records}
    parts = ['<div class="lv-timeline">']
    seen: set[str] = set()
    for key in order:
        item = by_key.get(key)
        if item is None:
            # مرحله‌ای که هنوز نرسیده — خاکستری/در انتظار
            if key == running_key:
                parts.append(
                    f'<div class="lv-stage active"><div class="rail">'
                    f'<div class="dot" style="background:{STAGE_COLORS[key]}">'
                    f'{STAGE_ICONS[key]}</div><div class="line"></div></div>'
                    f'<div class="body" style="border-right-color:{STAGE_COLORS[key]}">'
                    f'<h4>در حال انجام… <span class="lv-status-pill lv-pill-run">'
                    f"در جریان</span></h4></div></div>")
            continue
        seen.add(key)
        color = STAGE_COLORS.get(key, "#64748b")
        status = item.get("status", "done")
        if key == running_key:
            pill = '<span class="lv-status-pill lv-pill-run">در جریان</span>'
            cls = "lv-stage active"
        elif status == "fail":
            pill = '<span class="lv-status-pill lv-pill-fail">ناموفق</span>'
            cls = "lv-stage done"
        else:
            pill = '<span class="lv-status-pill lv-pill-done">انجام شد</span>'
            cls = "lv-stage done"
        dur = item.get("duration_ms")
        dur_html = f" · {dur} میلی‌ثانیه" if dur is not None else ""
        outs = "".join(f"<div>• {o}</div>" for o in item.get("outputs_fa", [])[:3])
        metrics = "".join(
            f'<div class="mrow">{m["name_fa"]}: <b>{m["value"]}</b></div>'
            for m in item.get("metrics", [])[:3])
        parts.append(
            f'<div class="{cls}"><div class="rail">'
            f'<div class="dot" style="background:{color}">{STAGE_ICONS.get(key, "•")}'
            f'</div><div class="line"></div></div>'
            f'<div class="body" style="border-right-color:{color}">'
            f'<h4>مرحله {item.get("num_fa", "")} — {item.get("title_fa", "")}{pill}</h4>'
            f'<div class="meta">{item.get("requirement_fa", "")}{dur_html}</div>'
            f'<div class="outs">{outs}</div>{metrics}</div></div>')
    parts.append("</div>")
    return "".join(parts)

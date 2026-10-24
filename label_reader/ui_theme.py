# -*- coding: utf-8 -*-
"""تم بصری LabelVoice — CSS حرفه‌ای، رنگ‌های مراحل و اجازهٔ HTML (v2.1.0).

پالت داروخانه‌ای (روان‌شناسی رنگ برند دارویی — طرح‌باکس):
  آبی اعتماد #1E88E5 (اعتماد و آرامش) · سبز سلامت #43A047 (سلامت و تعهد)
  سفید بهداشت #FFFFFF (پاکیزگی) · قرمز هشدار #E53935 (هشدار و توجه)
هر مرحلهٔ پردازش رنگ اختصاصی دارد تا کاربر همیشه بداند الان
کدام مرحله در حال انجام است.
"""
from __future__ import annotations

# ---------- رنگ اختصاصی هر مرحله ----------
STAGE_COLORS: dict[str, str] = {
    "opencv": "#1E88E5",    # آبی اعتماد — پیش‌پردازش تصویر
    "ocr": "#00ACC1",       # فیروزه‌ای — موتور خوانش (میان آبی و سبز پالت)
    "fields": "#FB8C00",    # نارنجی — پردازش متن و فیلدها
    "response": "#43A047",  # سبز سلامت — تولید پاسخ
    "tts": "#E53935",       # قرمز هشدار — خوانش صوتی
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
  --lv-primary: #0d47a1;   /* آبی عمیق اعتماد */
  --lv-accent: #1e88e5;    /* آبی دارویی (رنگ اصلی برند) */
  --lv-accent2: #43a047;   /* سبز سلامت */
  --lv-danger: #e53935;    /* قرمز هشدار */
  --lv-bg: #f3f9fe;
}
html, body, [class*="css"], .stApp, .stMarkdown, button, input, textarea,
.stRadio label, .stSelectbox label, .stCheckbox label, .stSlider label {
  font-family: 'Vazirmatn', 'Tahoma', sans-serif !important;
}
.stApp {
  background:
    radial-gradient(1100px 480px at 92% -80px, rgba(30,136,229,.20), transparent 62%),
    radial-gradient(900px 460px at -6% -60px, rgba(67,160,71,.17), transparent 58%),
    radial-gradient(820px 420px at 50% 118%, rgba(229,57,53,.10), transparent 60%),
    radial-gradient(560px 300px at 10% 48%, rgba(30,136,229,.06), transparent 60%),
    linear-gradient(180deg, #e9f3fd 0%, #f8fbff 46%, #edf6ef 100%);
}

/* ریبون چهاررنگ داروخانه‌ای (آبی → سفید → سبز → قرمز) — هویت بصری مشترک وب و موبایل */
.lv-ribbon {
  height: 7px; border-radius: 999px; margin: 0 0 14px;
  background: linear-gradient(90deg,
    #0d47a1 0%, #1e88e5 22%, #e3f2fd 34%, #ffffff 44%,
    #e8f5e9 56%, #43a047 72%, #e53935 100%);
  border: 1px solid rgba(13,71,161,.18);
  box-shadow: 0 2px 8px rgba(13,71,161,.22);
}
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 1.2rem; max-width: 1200px; }

/* ---------- سایدبار ---------- */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0d47a1 0%, #1565c0 55%, #1e88e5 140%);
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
  background: rgba(67,160,71,.35); border: 1px solid rgba(67,160,71,.65);
  border-radius: 999px; color: #d9f5de !important;
}

/* ---------- هیرو ---------- */
.lv-hero {
  background: linear-gradient(135deg, #0d47a1 0%, #1565c0 42%, #1e88e5 68%, #43a047 118%);
  border-radius: 20px; padding: 26px 28px; color: #fff;
  box-shadow: 0 12px 30px rgba(13,71,161,.25); margin-bottom: 14px;
  position: relative; overflow: hidden;
}
/* نوار چهاررنگ بالای هیرو: سبز، سفید، قرمز، آبی */
.lv-hero::before {
  content: ''; position: absolute; top: 0; right: 0; left: 0; height: 5px;
  background: linear-gradient(90deg,
    #43a047 0%, #ffffff 25%, #e53935 50%, #ffffff 75%, #1e88e5 100%);
  opacity: .95;
}
.lv-hero::after {
  content: '💊'; position: absolute; left: 18px; top: 50%;
  transform: translateY(-50%); font-size: 84px; opacity: .16;
}
.lv-hero h1 { font-size: 26px; font-weight: 900; margin: 0 0 6px; }
.lv-hero p { font-size: 14px; margin: 0; color: #dbeafe; max-width: 88%; }
.lv-hero .authors {
  display: inline-flex; align-items: center; gap: 6px; margin-top: 12px;
  background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.2);
  padding: 5px 14px; border-radius: 999px; font-size: 12.5px;
}

/* ---------- کارت‌ها و چیپ‌ها ---------- */
.lv-card {
  background: #fff; border-radius: 16px; padding: 18px 20px;
  border: 1px solid #d8e7f6; box-shadow: 0 4px 14px rgba(13,71,161,.06);
  margin-bottom: 12px;
  position: relative; overflow: hidden;
}
/* خط گرادیانی آبی→سبز بالای هر کارت — حضور پررنگ‌تر پالت در گرافیک صفحه */
.lv-card::before {
  content: ''; position: absolute; top: 0; right: 0; left: 0; height: 3px;
  background: linear-gradient(90deg, #1e88e5 0%, #43a047 60%, #e53935 130%);
  opacity: .85;
}
.lv-scope {
  background: linear-gradient(90deg, #e8f4fd, #eaf6ec);
  border: 1px solid #c4ddf4; border-right: 5px solid var(--lv-accent);
  border-radius: 12px; padding: 12px 16px; font-size: 13px; color: #123;
  margin-bottom: 12px;
}
.lv-big-answer {
  background: #fff; border-radius: 16px; padding: 20px 22px; font-size: 16.5px;
  line-height: 2.1; color: #12283d; border: 1px solid #d4e5f5;
  border-right: 6px solid var(--lv-accent);
  border-top: 3px solid #43a047;
  box-shadow: 0 4px 16px rgba(13,71,161,.07);
}
.lv-field-chip {
  display: inline-block; padding: 3px 10px; border-radius: 999px;
  font-size: 11.5px; font-weight: 700; margin-inline-start: 6px;
}
.chip-extracted { background: #e8f5e9; color: #2e7d32; }
.chip-uncertain { background: #fff8e1; color: #94670a; }
.chip-missing { background: #eceff1; color: #546e7a; }
.chip-conflicting { background: #ffebee; color: #c62828; }
.chip-user_corrected { background: #e3f2fd; color: #1565c0; }

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
  width: 3px; flex: 1; background: #d3e2f1; margin: 2px 0;
}
.lv-stage.done .line { background: linear-gradient(#c3d9ee, #c3d9ee); }
.lv-stage .body {
  flex: 1; background: #fff; border: 1px solid #e1ecf7; border-radius: 12px;
  padding: 10px 14px; margin: 0 10px 12px 0;
  border-right-width: 4px; box-shadow: 0 2px 8px rgba(13,71,161,.05);
}
.lv-stage .body h4 { margin: 0 0 4px; font-size: 14px; font-weight: 800; }
.lv-stage .body .meta {
  font-size: 11.5px; color: #64748b; margin-bottom: 4px;
}
.lv-stage .body .outs { font-size: 12.5px; color: #334155; line-height: 1.9; }
.lv-stage .mrow { font-size: 12px; color: #475569; margin-top: 4px; }
.lv-stage.active .dot { animation: lv-pulse 1.2s infinite; }
@keyframes lv-pulse {
  0% { box-shadow: 0 0 0 0 rgba(30,136,229,.45); }
  70% { box-shadow: 0 0 0 12px rgba(30,136,229,0); }
  100% { box-shadow: 0 0 0 0 rgba(30,136,229,0); }
}
.lv-status-pill {
  display: inline-block; font-size: 10.5px; padding: 1px 9px;
  border-radius: 999px; margin-inline-start: 8px; font-weight: 700;
}
.lv-pill-run { background: #e3f2fd; color: #1565c0; }
.lv-pill-done { background: #e8f5e9; color: #2e7d32; }
.lv-pill-fail { background: #ffebee; color: #c62828; }

/* ---------- کارت طراحان ---------- */
.lv-author {
  background: linear-gradient(135deg, #ffffff, #f2f9fe);
  border: 1px solid #d8e7f6; border-radius: 18px; padding: 24px;
  text-align: center; box-shadow: 0 6px 18px rgba(13,71,161,.07);
}
.lv-author .avatar {
  width: 84px; height: 84px; border-radius: 50%; margin: 0 auto 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 38px; color: #fff;
  background: linear-gradient(135deg, #1e88e5, #43a047);
  box-shadow: 0 6px 16px rgba(30,136,229,.35);
}
.lv-author h3 { margin: 0 0 4px; font-weight: 900; }
.lv-author .role { color: #64748b; font-size: 12.5px; margin-bottom: 10px; }
.lv-metric-tile {
  background: #fff; border-radius: 14px; padding: 14px 16px;
  border: 1px solid #e3eaf2; text-align: center;
}
.lv-metric-tile .v { font-size: 24px; font-weight: 900; color: #0d47a1; }
.lv-metric-tile .k { font-size: 12px; color: #64748b; }

/* ---------- احترام به تنظیمات کاهش حرکت (بند ۶ چارچوب) ---------- */
@media (prefers-reduced-motion: reduce) {
  .lv-stage.active .dot { animation: none !important; }
  .lv-stage .body, .lv-card, section[data-testid="stSidebar"] .stRadio label {
    transition: none !important;
  }
}
</style>
"""

# ---------- حالت تاریک دسکتاپ (بند ۶ چارچوب: حالت روشن و تاریک) ----------
# فقط وقتی کلید «حالت تاریک» سایدبار روشن باشد تزریق می‌شود؛
# همهٔ انتخابگرها بعد از THEME_CSS می‌آیند تا رنگ‌های روشن بازنویسی شوند.
DARK_THEME_CSS = """
<style>
.stApp {
  background:
    radial-gradient(1100px 480px at 92% -80px, rgba(30,136,229,.26), transparent 62%),
    radial-gradient(900px 460px at -6% -60px, rgba(67,160,71,.20), transparent 58%),
    radial-gradient(820px 420px at 50% 118%, rgba(229,57,53,.14), transparent 60%),
    #081426 !important;
}
.stApp p, .stApp li, .stApp td, .stApp th, .stApp dd, .stApp dt,
[data-testid="stMarkdownContainer"] {
  color: #dceaf8 !important;
}
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
  color: #eef6fd !important;
}
.stApp .stCaption, .stApp [data-testid="stCaptionContainer"] { color: #8fabc6 !important; }

/* کارت‌ها و اجزای اختصاصی */
.lv-card, .lv-big-answer, .lv-metric-tile, .lv-author {
  background: #0e2440 !important;
  border-color: #1d3a5f !important;
  box-shadow: 0 4px 14px rgba(0,0,0,.35) !important;
}
.lv-big-answer { color: #e6eff8 !important; border-right-color: var(--lv-accent) !important; }
.lv-scope {
  background: linear-gradient(90deg, #0c2743, #0d2f1e) !important;
  border-color: #24507c !important; color: #cfe3f5 !important;
}
.lv-metric-tile .v { color: #64b5f6 !important; }
.lv-metric-tile .k, .lv-author .role { color: #8fabc6 !important; }
.lv-author { background: linear-gradient(135deg, #0e2440, #0b1c33) !important; }

/* چیپ وضعیت فیلدها — نسخهٔ تاریک */
.chip-extracted { background: #0d2e18 !important; color: #81de9c !important; }
.chip-uncertain { background: #33270a !important; color: #ffd54f !important; }
.chip-missing   { background: #16283b !important; color: #9fb3c8 !important; }
.chip-conflicting { background: #3a1212 !important; color: #ff9e9a !important; }
.chip-user_corrected { background: #0d2a4a !important; color: #90caf9 !important; }

/* خط‌زمان مراحل */
.lv-stage .body {
  background: #0e2440 !important;
  border-color: #1d3a5f !important;
  box-shadow: 0 2px 8px rgba(0,0,0,.35) !important;
}
.lv-stage .line { background: #1d3a5f !important; }
.lv-stage.done .line { background: #1d3a5f !important; }
.lv-stage .body .outs { color: #c8dbee !important; }
.lv-stage .body .meta, .lv-stage .mrow { color: #93aecb !important; }
.lv-status-pill.lv-pill-run  { background: #0d2a4a !important; color: #90caf9 !important; }
.lv-status-pill.lv-pill-done { background: #0d2e18 !important; color: #81de9c !important; }
.lv-status-pill.lv-pill-fail { background: #3a1212 !important; color: #ff9e9a !important; }

/* اجزای بومی Streamlit در بدنهٔ اصلی */
.stApp [data-testid="stExpander"] details,
.stApp [data-testid="stExpander"] summary {
  background: #0e2440 !important; color: #dceaf8 !important;
  border-color: #1d3a5f !important;
}
.stApp [data-testid="stExpander"] summary p { color: #dceaf8 !important; }
.stApp textarea, .stApp input, .stApp [data-baseweb="select"] > div,
.stApp [data-baseweb="input"] {
  background: #0e2440 !important; color: #e6eff8 !important;
}
.stApp [data-testid="stFileUploader"], .stApp [data-testid="stFileUploaderDropzone"] {
  background: #0e2440 !important; border-color: #24507c !important;
}
.stApp [data-testid="stFileUploaderDropzone"] * { color: #c8dbee !important; }
.stApp [data-testid="stRadio"] label, .stApp [data-testid="stCheckbox"] label {
  background: #0c2038 !important; border-color: #1d3a5f !important;
}
.stApp [data-testid="stRadio"] label:hover,
.stApp [data-testid="stCheckbox"] label:hover { background: #143356 !important; }
.stApp .stButton > button {
  background: #103862 !important; color: #eaf4fc !important;
  border: 1px solid #2a5f96 !important;
}
.stApp .stButton > button:hover { background: #17497c !important; }
.stApp hr { border-color: #1d3a5f !important; }
.stApp code, .stApp pre {
  background: #0a1d33 !important; color: #90caf9 !important;
}
.stApp table { border-color: #24507c !important; }
.stApp th { background: #102c4c !important; }
.stApp .stAlert {
  background: #102c4c !important; color: #dceaf8 !important;
  border-color: #24507c !important;
}
.stApp [data-testid="stSlider"] [role="slider"] {
  background-color: #64b5f6 !important;
}
.stApp [data-testid="stSliderTrack"] > div { background: #2a5f96 !important; }
/* سایدبار از قبل تیره است؛ دست‌نخورده */
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

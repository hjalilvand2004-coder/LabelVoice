#!/usr/bin/env python3
"""آزمون دود AppTest برای v2.0.0 — اجرای کامل app.py بدون استثنا + حضور بخش مدل‌ها."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from streamlit.testing.v1 import AppTest  # noqa: E402


def main() -> int:
    at = AppTest.from_file(str(REPO / "app.py"), default_timeout=60)
    at.run()
    assert not at.exception, f"استثنا در اجرای app.py: {at.exception}"
    body = " ".join(str(x) for x in at.main) + " " + \
        " ".join(str(x) for x in at.sidebar)
    # بخش شفافیت مدل‌ها (v2.0.0) — با کلید/برچسب عناصر سایدبار
    sidebar_keys = [str(x.key) for x in at.sidebar if getattr(x, "key", None)]
    assert "help_modelsmd" in sidebar_keys, \
        f"دکمه راهنمای مدل‌ها در سایدبار نیست: {sidebar_keys}"
    assert "vlm_assist" in sidebar_keys, \
        "toggle دستیار Qwen3-VL در سایدبار نیست"
    assert any("جدول مدل" in str(x.label) for x in at.sidebar
               if hasattr(x, "label")), "جدول مدل‌ها (expander) یافت نشد"
    # صفحه خواندن و خط‌زمان
    assert "خواندن دارو" in body
    print("✓ app.py بدون استثنا اجرا شد؛ بخش «مدل‌ها و موتورها» حاضر است.")
    print("✓ toggle دستیار Qwen3-VL:",
          any("vlm_assist" in str(t.key) for t in at.toggle))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

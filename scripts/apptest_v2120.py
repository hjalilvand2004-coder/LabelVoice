# -*- coding: utf-8 -*-
"""AppTest واقعی Streamlit برای v2.12.0 — TTS لوکال در رابط دسکتاپ"""
from pathlib import Path
from streamlit.testing.v1 import AppTest

at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=120)
# noqa
at.run()

assert not at.exception, f"استثنا: {at.exception}"

# سایدبار: صدا حذف شده و توضیح Piper هست
captions = [c.value for c in at.sidebar.caption]
assert any("Piper" in c for c in captions), f"کپشن Piper در سایدبار نیست: {captions}"

# بخش حریم خصوصی: بدون ارسال به سرویس ابری
mds = " ".join(m.value for m in at.sidebar.markdown)
assert "هیچ متنی به سرویس ابری" in mds, "متن حریم خصوصی به‌روز نشده"

# صفحهٔ راهنما هم بدون استثنا رندر شود
at.sidebar.radio[0].set_value(at.sidebar.radio[0].options[2]).run()
assert not at.exception

print("AppTest v2.12.0: بدون استثنا؛ سایدبار/حریم خصوصی/راهنما هم‌راستا با TTS لوکال ✓")

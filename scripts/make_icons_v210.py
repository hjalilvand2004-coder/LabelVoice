#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بازتولید آیکون‌های PWA با پالت داروخانه‌ای v2.1.0
آبی اعتماد #1E88E5 / #0D47A1 + سفید + سبز سلامت #43A047 (خط اسکن).
موتیف: صلیب داروخانه + خط اسکن سبز (خواندن برچسب).
"""
from PIL import Image, ImageDraw

OUT = "/home/z/my-project/labelvoice-clone/mobile-app/icons"

BLUE_TOP = (30, 136, 229)    # 1E88E5
BLUE_BOT = (13, 71, 161)     # 0D47A1
GREEN = (67, 160, 71)        # 43A047
WHITE = (255, 255, 255)


def gradient_bg(size: int) -> Image.Image:
    """پس‌زمینهٔ گرادیان آبی عمودی."""
    img = Image.new("RGBA", (size, size))
    px = img.load()
    for y in range(size):
        t = y / max(size - 1, 1)
        r = int(BLUE_TOP[0] + (BLUE_BOT[0] - BLUE_TOP[0]) * t)
        g = int(BLUE_TOP[1] + (BLUE_BOT[1] - BLUE_TOP[1]) * t)
        b = int(BLUE_TOP[2] + (BLUE_BOT[2] - BLUE_TOP[2]) * t)
        for x in range(size):
            px[x, y] = (r, g, b, 255)
    return img


def rounded(size: int, radius_ratio: float = 0.22) -> Image.Image:
    """آیکون مربع با گوشه‌های گرد (خارج آن شفاف)."""
    img = gradient_bg(size)
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * radius_ratio), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def draw_icon(img: Image.Image, scale: float = 1.0) -> Image.Image:
    """صلیب سفید + خط اسکن سبز، در مقیاس scale (برای ناحیهٔ امن maskable)."""
    size = img.size[0]
    d = ImageDraw.Draw(img)
    s = scale
    # صلیب — مرکز (50%, 47%)
    cx, cy = size * 0.5, size * 0.47
    arm = size * 0.155 * s          # نصف عرض بازو
    length = size * 0.24 * s        # فاصلهٔ مرکز تا نوک بازو
    d.rounded_rectangle([cx - arm, cy - length, cx + arm, cy + length],
                        radius=int(arm * 0.45), fill=WHITE)
    d.rounded_rectangle([cx - length, cy - arm, cx + length, cy + arm],
                        radius=int(arm * 0.45), fill=WHITE)
    # خط اسکن سبز — افقی روی صلیب
    bar_h = size * 0.052 * s
    bar_w = size * 0.33 * s
    d.rounded_rectangle([cx - bar_w, cy - bar_h / 2, cx + bar_w, cy + bar_h / 2],
                        radius=int(bar_h / 2), fill=GREEN)
    # نقطهٔ سبز کوچک پایین (قرص)
    dot_r = size * 0.045 * s
    dot_y = size * 0.78
    d.ellipse([cx - dot_r, dot_y - dot_r, cx + dot_r, dot_y + dot_r], fill=GREEN)
    return img


def main() -> None:
    # آیکون معمولی — گوشه گرد
    for size, name in ((192, "icon-192.png"), (512, "icon-512.png")):
        img = rounded(size)
        img = draw_icon(img)
        img.save(f"{OUT}/{name}")
        print("saved", name)

    # maskable — تمام‌صفحه با ناحیهٔ امن ۸۰٪
    img = gradient_bg(512)
    img = draw_icon(img, scale=0.78)
    img.save(f"{OUT}/maskable-512.png")
    print("saved maskable-512.png")


if __name__ == "__main__":
    main()

"""生成程序图标 .build/app.ico。

素材是 assets/brand_frog.png（水彩青蛙），裁出头部做成圆形徽标，
小尺寸下也能看清眼睛和嘴；同时输出 PNG 供窗口内显示。

用法：
    python make_icon.py
"""
import io
import os
import sys

if sys.stdout and hasattr(sys.stdout, "buffer"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except (ValueError, AttributeError):
        pass

try:
    from PIL import Image, ImageDraw, ImageFilter
except ImportError:
    print("需要 Pillow：python -m pip install pillow")
    sys.exit(1)

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "assets", "brand_frog.png")
OUT_ICO = os.path.join(ROOT, ".build", "app.ico")
OUT_PNG = os.path.join(ROOT, ".build", "app_256.png")

# 裁切区域：紧贴脸部的方框（384x356 原图里量出来的），脸颊左右各留一点，
# 不带腹部——否则头像缩小到 16px 时眼睛会糊成一团。
CROP = (120, 30, 300, 210)

# 徽标底色：比窗口底稍亮一点，让水彩米白有个依托
RING = (78, 161, 247, 255)      # ACCENT，一圈细边
PLATE = (31, 36, 46, 255)       # BG_PANEL


def _head(size: int) -> Image.Image:
    """裁出青蛙头部并缩放到 size。"""
    im = Image.open(SRC).convert("RGB")
    im = im.crop(CROP)
    # 正方形化：居中裁成正方形，避免拉伸变形
    w, h = im.size
    side = min(w, h)
    im = im.crop(((w - side) // 2, (h - side) // 2,
                  (w - side) // 2 + side, (h - side) // 2 + side))
    return im.resize((size, size), Image.LANCZOS)


def make(size: int) -> Image.Image:
    """圆形徽标：细描边 + 圆形裁切的青蛙头。"""
    S = size * 4  # 超采样，边缘更顺滑
    base = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # 圆形蒙版
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, S - 1, S - 1], fill=255)

    # 先铺底色，再贴青蛙头
    plate = Image.new("RGBA", (S, S), PLATE)
    head = _head(S).convert("RGBA")
    base.paste(plate, (0, 0), mask)
    base.paste(head, (0, 0), mask)

    # 细描边
    d = ImageDraw.Draw(base)
    ring = max(2, S // 40)
    d.ellipse([ring // 2, ring // 2, S - 1 - ring // 2, S - 1 - ring // 2],
              outline=RING, width=ring)

    return base.resize((size, size), Image.LANCZOS)


def main() -> None:
    if not os.path.isfile(SRC):
        print("缺少素材：%s" % SRC)
        sys.exit(1)
    os.makedirs(os.path.dirname(OUT_ICO), exist_ok=True)
    sizes = [16, 24, 32, 48, 64, 128, 256]
    imgs = [make(s) for s in sizes]
    imgs[-1].save(OUT_ICO, format="ICO",
                  sizes=[(s, s) for s in sizes], append_images=imgs[:-1])
    imgs[-1].save(OUT_PNG)
    print("图标已生成：%s (%s B)" % (OUT_ICO, format(os.path.getsize(OUT_ICO), ",")))
    print("预览图：%s" % OUT_PNG)


if __name__ == "__main__":
    main()

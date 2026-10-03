#!/usr/bin/env python3
"""Per-card background crops of the painting, softly blurred ("frosted glass"). Needs Pillow; run locally:

    python3 .github/readme/make_backgrounds.py            # uses "background.blur" from readme-config.json
    python3 .github/readme/make_backgrounds.py --blur 8   # override

Each card gets a different region of the painting (moon, nebula, mountains, lake…). The dark overlay and the
text-side gradient are applied in the SVG (readme_cards.py), so only the blur is baked in here.
"""
from __future__ import annotations

import argparse
import json
import pathlib

from PIL import Image, ImageFilter

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = HERE / "hero.jpg"  # 1800×600 painting

# card → (crop box in hero.jpg pixels, stored size). Full-width cards are stored at 800px (they're blurred,
# so the upscale is invisible) to keep every card under 150 KB.
CROPS = {
    "about":        ((330, 0, 1090, 405),   (600, 320)),   # starry nebula sky
    "focus":        ((830, 30, 1590, 435),  (600, 320)),   # the moon, sitting on the right
    "now-building": ((300, 140, 1800, 478), (800, 180)),   # the big mountains
    "tech-stack":   ((270, 0, 1530, 600),   (800, 380)),   # wide mountain range
    "projects":     ((260, 205, 1460, 600), (800, 263)),   # lake reflections
    "status":       ((300, 300, 1800, 600), (800, 158)),   # trees and lake
}


def build(name: str, blur: float, out: pathlib.Path) -> int:
    box, size = CROPS[name]
    img = Image.open(SRC).convert("RGB").crop(box).resize(size, Image.LANCZOS)
    # `blur` is in card pixels (the SVG card's own coordinate space); scale it to the stored image.
    card_w = 600 if size[0] == 600 else 1200
    img = img.filter(ImageFilter.GaussianBlur(blur * size[0] / card_w))
    img.save(out, "JPEG", quality=80, optimize=True, progressive=True)
    return out.stat().st_size


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--blur", type=float)
    ap.add_argument("--only")
    ap.add_argument("--out", default=str(HERE / "bg"))
    a = ap.parse_args()
    cfg = json.loads((ROOT / "readme-config.json").read_text()).get("background", {})
    blur = a.blur if a.blur is not None else cfg.get("blur", 6.5)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name in ([a.only] if a.only else CROPS):
        size = build(name, blur, out / f"{name}.jpg")
        print(f"{name:13s} blur {blur}px  {size/1024:.1f} KB")

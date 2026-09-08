"""Cut the illustrations and handwritten annotations out of the design references.

The seven mockups in design/ are the visual contract for the web panel. The 3D logo, the banner art and
the handwritten notes cannot be rebuilt in CSS, so they are cropped from the references, the dark
background is turned transparent, and the PNGs are saved in app/web/static/img/ (origin documented
here). Demo thumbnails for the seed database are cropped the same way into app/web/static/img/demo/.

Run:  .venv/Scripts/python.exe scripts/extract_design_assets.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "design"
OUT = ROOT / "app" / "web" / "static" / "img"

# name -> (reference file, (left, top, right, bottom), make_dark_transparent)
ASSETS: dict[str, tuple[str, tuple[int, int, int, int], bool]] = {
    "logo-3d.png": ("01-hoje.png", (12, 14, 246, 112), True),
    "hero-art.png": ("01-hoje.png", (905, 101, 1469, 356), True),  # text at (0..66, 148..172) is erased below
    "note-evolucao.png": ("01-hoje.png", (1360, 922, 1462, 1010), True),
    "note-conversa.png": ("03-conversa.png", (862, 108, 1004, 194), True),
    "note-inteligencia.png": ("06-inteligencia.png", (1380, 92, 1491, 198), True),
    "avatar-assistente.png": ("03-conversa.png", (296, 116, 360, 180), False),
}

# Demo thumbnails (vertical 9:16 crops) used only by scripts/seed_demo.py.
DEMO_THUMBS: dict[str, tuple[str, tuple[int, int, int, int]]] = {
    "globe.jpg": ("04-biblioteca.png", (284, 294, 466, 497)),
    "eye.jpg": ("04-biblioteca.png", (479, 294, 661, 497)),
    "coffee.jpg": ("04-biblioteca.png", (674, 294, 856, 497)),
    "headphones.jpg": ("04-biblioteca.png", (869, 294, 1051, 497)),
    "brain.jpg": ("04-biblioteca.png", (284, 665, 466, 868)),
    "city.jpg": ("04-biblioteca.png", (479, 665, 661, 868)),
    "hourglass.jpg": ("04-biblioteca.png", (674, 665, 856, 868)),
    "moon.jpg": ("04-biblioteca.png", (869, 665, 1051, 868)),
    "hourglass-clean.jpg": ("01-hoje.png", (720, 528, 830, 688)),
    "eye-clean.jpg": ("03-conversa.png", (366, 578, 450, 680)),
    "glass.jpg": ("02-estudio.png", (302, 267, 376, 410)),
    "splash.jpg": ("02-estudio.png", (957, 245, 1085, 356)),
    "ice.jpg": ("02-estudio.png", (300, 489, 375, 545)),
    "mountains.jpg": ("02-estudio.png", (300, 557, 375, 613)),
    "coffee-small.jpg": ("02-estudio.png", (300, 625, 375, 681)),
    "logo-thumb.jpg": ("02-estudio.png", (300, 693, 375, 749)),
}


def _transparent(img: Image.Image, threshold: int = 34, soft: int = 26) -> Image.Image:
    """Turn near-black pixels transparent with a soft edge so the crop blends into any dark surface."""
    arr = np.asarray(img.convert("RGBA")).astype(np.float32)
    luma = arr[..., :3].max(axis=2)
    alpha = np.clip((luma - threshold) / soft, 0, 1)
    arr[..., 3] = alpha * 255
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "demo").mkdir(exist_ok=True)
    for name, (ref, box, cut) in ASSETS.items():
        img = Image.open(DESIGN / ref).convert("RGBA").crop(box)
        if cut:
            img = _transparent(img)
        if name == "hero-art.png":  # the banner description overlaps the crop; wipe that strip
            img.paste((0, 0, 0, 0), (0, 140, 70, 180))
        img.save(OUT / name)
        print(f"{name:26} <- {ref} {box}")
    for name, (ref, box) in DEMO_THUMBS.items():
        img = Image.open(DESIGN / ref).convert("RGB").crop(box)
        if ref == "04-biblioteca.png":  # hide the baked-in kebab and duration; the panel draws its own
            w, h = img.size
            img.paste(img.crop((w - 76, 4, w - 44, 44)), (w - 36, 4))
            img.paste(img.crop((w - 136, h - 30, w - 70, h)), (w - 66, h - 30))
        img.save(OUT / "demo" / name, quality=90)
        print(f"demo/{name:21} <- {ref} {box}")


if __name__ == "__main__":
    main()

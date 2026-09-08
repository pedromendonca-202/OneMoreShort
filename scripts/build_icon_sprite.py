"""Build app/web/static/icons.svg: the Lucide symbols the panel uses, plus a few custom brand glyphs.

Source: lucide-static sprite (ISC licence), downloaded once from unpkg. Run with the sprite path:
    .venv/Scripts/python.exe scripts/build_icon_sprite.py path/to/lucide-sprite.svg
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / "web" / "static" / "icons.svg"

NAMES = """house clapperboard message-circle folder chart-column-big chart-column brain settings chevron-right chevron-down
chevron-up chevron-left wallet calendar copy play eye eye-off refresh-cw upload download plus check x info clock file-text
lightbulb sparkles zap search arrow-up-down ellipsis-vertical trash circle-check circle-check-big circle-x triangle-alert
target tv film layout-grid cloud-upload paperclip send user users trophy flask-conical thermometer book-open cpu activity
wifi key palette folder-open rotate-ccw save external-link database server hard-drive arrow-left arrow-right heart
user-plus video layers monitor shield link pencil circle-question-mark image list tag thumbs-up trending-up arrow-up
arrow-down corner-down-right timer mic captions box star hash globe atom camera coffee share-2 badge-check circle
circle-alert pin redo-2 grid-2x2 square-play circle-play bell gauge chart-line chart-no-axes-column-increasing bot
message-square flame rocket compass shuffle sun moon sliders-horizontal circle-dot minus loader circle-dashed check-check
clipboard clipboard-check log-out unplug plug square-check square radio scan-eye test-tube telescope microscope dna leaf
landmark graduation-cap user-round tv-minimal-play wand-sparkles history-alias""".split()

# Custom glyphs (24x24 viewBox, same stroke conventions as Lucide).
CUSTOM = {
    # YouTube-style play badge used for "Últimos publicados" and the YouTube OAuth card.
    "youtube": '<rect x="2.5" y="5" width="19" height="14" rx="4" /><path d="m10 9 5 3-5 3z" fill="currentColor" stroke="none" />',
    # Clock-with-arrow "history" glyph (Lucide renamed it; keep the classic shape).
    "history": '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" /><path d="M3 3v5h5" /><path d="M12 7v5l4 2" />',
    # Retention ring placeholder used before data exists.
    "ring": '<circle cx="12" cy="12" r="9" />',
}


def main(sprite_path: str) -> None:
    sprite = Path(sprite_path).read_text(encoding="utf-8")
    ids = set(re.findall(r'<symbol id="([^"]+)"', sprite))
    out = ['<svg xmlns="http://www.w3.org/2000/svg" style="display:none">',
           '<!-- Lucide icons (ISC licence) trimmed from lucide-static v1.42.0 by scripts/build_icon_sprite.py, plus custom glyphs. -->']
    missing = []
    for name in NAMES:
        if name.endswith("-alias"):
            continue
        if name not in ids:
            missing.append(name)
            continue
        match = re.search(r'<symbol id="%s".*?</symbol>' % re.escape(name), sprite, flags=re.S)
        body = re.sub(r"\s+", " ", match.group(0)).replace(f' class="lucide lucide-{name}"', "")
        out.append(body)
    for name, body in CUSTOM.items():
        out.append(f'<symbol id="{name}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
                   f'stroke-linecap="round" stroke-linejoin="round">{body}</symbol>')
    out.append("</svg>")
    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"{len(out) - 3} symbols -> {OUT}")
    if missing:
        print("missing from sprite:", missing)


if __name__ == "__main__":
    main(sys.argv[1])

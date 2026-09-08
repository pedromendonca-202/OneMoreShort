"""Screenshot one panel route at the reference viewport (1491x1055) with headless Chromium.

    .venv/Scripts/python.exe scripts/capture.py /biblioteca docs/captures/work/biblioteca.png
    .venv/Scripts/python.exe scripts/capture.py "/estudio/OMS-20260908-0001?step=3" out.png --click ".clip-card:nth-child(1)" --wait 800

Requires the panel running on http://127.0.0.1:8787 (scripts/demo.ps1 for the demo database).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("route")
    parser.add_argument("out")
    parser.add_argument("--base", default="http://127.0.0.1:8787")
    parser.add_argument("--wait", type=int, default=1200, help="ms to wait after the screen renders (images, SSE)")
    parser.add_argument("--click", action="append", default=[], help="CSS selector to click before the capture (repeatable)")
    parser.add_argument("--js", default=None, help="JavaScript to evaluate before the capture")
    parser.add_argument("--full", action="store_true", help="full-page capture instead of the viewport")
    parser.add_argument("--width", type=int, default=1491)
    parser.add_argument("--height", type=int, default=1055)
    args = parser.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": args.width, "height": args.height}, device_scale_factor=1)
        page.on("console", lambda msg: errors.append(f"{msg.type}: {msg.text}") if msg.type in ("error", "warning") else None)
        page.on("pageerror", lambda err: errors.append(f"pageerror: {err}"))
        page.goto(args.base + args.route, wait_until="load")
        page.wait_for_function("document.fonts.status === 'loaded' && document.querySelector('#main').children.length > 0", timeout=15000)
        page.wait_for_timeout(args.wait)
        for selector in args.click:
            page.click(selector)
            page.wait_for_timeout(500)
        if args.js:
            page.evaluate(args.js)
            page.wait_for_timeout(400)
        page.screenshot(path=str(out), full_page=args.full)
        browser.close()
    print(f"saved {out}")
    for line in errors:
        print("console:", line)
    return 1 if any(e.startswith(("pageerror", "error")) for e in errors) else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Validate the build against the frozen live snapshot.

Three checks per page:
  1. structural — visible text, image list, link list (archive vs build), exact
  2. closeness  — 2.0 is an intent-level redesign (user decision 2026-10-17),
     not a pixel clone: the old table artifacts (seam line, top-nav band,
     0.5px raster offsets) were dropped, so the new render sits 1-3px off in
     position. A pixel matches if the other render has a near-identical color
     (per-channel <= 32) within ±6px x / ±6px y. Whole-page unmatched budget:
     70k px (~8.7% of 800x1000) — ~2x the worst real page (35.3k); a broken
     photo alone is ~77k.
  3. contract   — design invariants of the new render: the green banner image
     (incl. its cream logo), the black menu panel, the cream 600px column.

Both directories are served by local http.server so absolute URLs work.
Usage: python3 tools/validate.py [ARCHIVE_DIR] [BUILD_DIR]
"""
import html as htmlmod
import http.server
import io
import re
import socketserver
import sys
import threading
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "archive" / "live-2026-10-14"
BUILD = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "build"
VIEWPORT = {"width": 800, "height": 1000}
CLOSER_BUDGET = 70000  # px, see module docstring


def serve(directory: Path, port: int) -> None:
    class Handler(http.server.SimpleHTTPRequestHandler):
        # Extensionless Drupal paths must be served as HTML, or the browser
        # treats them as downloads.
        def guess_type(self, path):  # noqa: A003
            if Path(path).suffix == "" and Path(path).is_file():
                return "text/html"
            return super().guess_type(path)

        def log_message(self, *a):  # silence
            pass

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    httpd = ReusableTCPServer(("127.0.0.1", port), lambda *a, **kw: Handler(*a, directory=directory, **kw))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()


def extract(page_html: str) -> tuple[str, list, list]:
    """Return (visible text, image srcs, link hrefs)."""
    # Sanctioned deviation (user, 2026-10-14, t008): the statcounter footer
    # (a 1x1 tracking pixel on the live site) is dropped from the rebuild —
    # remove it from the reference side so the gate compares like-for-like.
    t = re.sub(r'<div class="statcounter">.*?</div>', "", page_html, flags=re.S)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"<(script|style).*?</\1>", "", t, flags=re.S)
    # Entities are normalized by the DOM; compare unescaped values.
    imgs = sorted(htmlmod.unescape(s) for s in re.findall(r'<img[^>]+src="([^"]*)"', t))
    links = sorted(htmlmod.unescape(s) for s in re.findall(r'<a[^>]+href="([^"]*)"', t))
    t = re.sub(r"<[^>]+>", " ", t)
    text = re.sub(r"\s+", " ", htmlmod.unescape(t)).strip()
    # Sanctioned deviation (2.0, 2026-10-17): the footer credit is real
    # selectable text in the rebuild (it was baked into footer.png in the
    # archive) — drop it so the gate compares like-for-like.
    text = text.replace("ontwerp: Boris Reuderink (b.reuderink@alumni.utwente.nl)", "").strip()
    return text, imgs, links


def close_diff(A: np.ndarray, B: np.ndarray, dx: int = 6, dy: int = 6, tol: int = 32) -> int:
    """Unmatched pixels: old pixels whose neighborhood (±dx/±dy) has no
    near-identical color in the new render. Position-tolerant (the 2.0
    render sits 1-3px off where the old table artifacts were removed),
    color-strict (a wrong color or missing element never matches)."""
    H, W = A.shape[:2]
    match = np.zeros((H, W), bool)
    for oy in range(-dy, dy + 1):
        for ox in range(-dx, dx + 1):
            Bs = np.roll(np.roll(B, oy, axis=0), ox, axis=1)
            match |= (np.abs(Bs - A).max(axis=2) <= tol)
    return int((~match).sum())


def contract(A: np.ndarray) -> list[str]:
    """Design invariants of the new render. Returns failure messages."""
    fails = []
    banner = A[10:90, 100:700]  # 80px logo banner strip
    green = int(((banner[:, :, 1] > banner[:, :, 0] + 20) & (banner[:, :, 1] > 60)).sum())
    if green < 10000:
        fails.append(f"banner not green ({green} px)")
    logo = int((np.abs(banner - np.array([255, 255, 204])).max(axis=2) <= 24).sum())
    if logo < 1000:
        fails.append(f"banner logo missing ({logo} cream px)")
    if int(A[102, 150].sum()) > 120:
        fails.append("panel not dark at (150,102)")
    # y=150 is inside the column on every page: the sidebar panel alone
    # (162px + margins) makes the column at least ~172px tall
    cream = np.array([255, 255, 204])
    for x in (105, 695):  # left/right margin strips of the 600px column
        if int(np.abs(A[150, x] - cream).max()) > 32:
            fails.append(f"column not cream at ({x},150)")
    return fails


def main() -> int:
    serve(ARCHIVE, 8101)
    serve(BUILD, 8102)
    pages = sorted(p.name for p in ARCHIVE.iterdir() if p.is_file() and p.name != "manifest.tsv")
    struct_fail, pixel_fail, contract_fail = [], [], []

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        for name in pages:
            # 1. structural
            a_text, a_imgs, a_links = extract((ARCHIVE / name).read_text(encoding="utf-8"))
            b_text, b_imgs, b_links = extract((BUILD / name).read_text(encoding="utf-8"))
            diffs = [k for k, (a, b) in
                     {"text": (a_text, b_text), "images": (a_imgs, b_imgs), "links": (a_links, b_links)}.items() if a != b]
            if diffs:
                struct_fail.append((name, diffs))
            # 2. closeness — same sanctioned deviation: drop the statcounter
            # element from the reference render before the screenshot
            page.goto(f"http://127.0.0.1:8101/{name}", wait_until="load", timeout=15000)
            page.evaluate("document.querySelector('.statcounter')?.remove()")
            page.wait_for_timeout(300)
            A = np.asarray(Image.open(io.BytesIO(page.screenshot())).convert("RGB"), dtype=np.int16)
            page.goto(f"http://127.0.0.1:8102/{name}", wait_until="load", timeout=15000)
            page.wait_for_timeout(300)
            B = np.asarray(Image.open(io.BytesIO(page.screenshot())).convert("RGB"), dtype=np.int16)
            n = close_diff(A, B)
            if n > CLOSER_BUDGET:
                pixel_fail.append((name, f"{n}/{CLOSER_BUDGET} px"))
            # 3. contract (new render only)
            cf = contract(B)
            if cf:
                contract_fail.append((name, cf))
        browser.close()

    print(f"checked {len(pages)} pages")
    for name, diffs in struct_fail:
        print(f"STRUCTURAL DIFF {name}: {diffs}")
    for name, n in pixel_fail:
        print(f"CLOSENESS OVER BUDGET {name}: {n}")
    for name, cf in contract_fail:
        print(f"CONTRACT FAIL {name}: {cf}")
    ok = not (struct_fail or pixel_fail or contract_fail)
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

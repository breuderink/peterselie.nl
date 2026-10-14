#!/usr/bin/env python3
"""Validate the build against the frozen live snapshot.

Two checks per page (t005 + t006):
  1. structural — visible text, image list, link list (archive vs build)
  2. pixel — headless chromium (playwright) screenshot at 800x1000, PIL diff

Both directories are served by local http.server so absolute URLs work.
Usage: python3 tools/validate.py [ARCHIVE_DIR] [BUILD_DIR]
"""
import html as htmlmod
import http.server
import re
import socketserver
import sys
import threading
from pathlib import Path

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "archive" / "live-2026-10-14"
BUILD = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "build"
VIEWPORT = {"width": 800, "height": 1000}


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
    t = re.sub(r"<!--.*?-->", "", page_html, flags=re.S)
    t = re.sub(r"<(script|style).*?</\1>", "", t, flags=re.S)
    imgs = sorted(re.findall(r'<img[^>]+src="([^"]*)"', t))
    links = sorted(re.findall(r'<a[^>]+href="([^"]*)"', t))
    t = re.sub(r"<[^>]+>", " ", t)
    text = re.sub(r"\s+", " ", htmlmod.unescape(t)).strip()
    return text, imgs, links


def main() -> int:
    serve(ARCHIVE, 8101)
    serve(BUILD, 8102)
    pages = sorted(p.name for p in ARCHIVE.iterdir() if p.is_file() and p.name != "manifest.tsv")
    struct_fail, pixel_fail = [], []

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
            # 2. pixel
            page.goto(f"http://127.0.0.1:8101/{name}", wait_until="load", timeout=15000)
            page.wait_for_timeout(300)
            a = page.screenshot()
            page.goto(f"http://127.0.0.1:8102/{name}", wait_until="load", timeout=15000)
            page.wait_for_timeout(300)
            b = page.screenshot()
            ia = Image.open(__import__("io").BytesIO(a)).convert("RGB")
            ib = Image.open(__import__("io").BytesIO(b)).convert("RGB")
            d = ImageChops.difference(ia, ib)
            changed = sum(1 for px in d.getdata() if px != (0, 0, 0))
            total = ia.size[0] * ia.size[1]
            if changed:
                pixel_fail.append((name, d.getbbox(), f"{changed}/{total} px"))
        browser.close()

    print(f"checked {len(pages)} pages")
    for name, diffs in struct_fail:
        print(f"STRUCTURAL DIFF {name}: {diffs}")
    for name, bbox, n in pixel_fail:
        print(f"PIXEL DIFF {name}: bbox={bbox} {n}")
    print("PASS" if not struct_fail and not pixel_fail else "FAIL")
    return 1 if struct_fail or pixel_fail else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Validate the build.

Two checks:
  1. structural — per page: visible text, image list, link list
     (archive vs build), exact. Catches lost/duplicated content.
     The sidebar menu is exempt from the archive comparison: it is
     owner-editable (content/_data/menu.json) and checked against that
     source instead, so menu changes pass the gate.
  2. contract   — design invariants of the new render, checked on ONE
     page: the green banner image (incl. its cream logo), the black menu
     panel, the cream 600px column. One page is provably enough — the
     chrome is one template + one stylesheet, identical on all 179 pages.

The pixel-diff check (zero tolerance in v1.0, closeness budget in 2.0)
was RETIRED 2026-10-17 with the user's sign-off: parity with the old
site had been proven (179/179 at tag v2.0), and 2.1 is a deliberate
intent-level redesign — measuring distance to the old render no longer
means anything. See LOG.md / KNOWLEDGE.md.

build/ is served by a local http.server so absolute URLs work.
Usage: python3 tools/validate.py [ARCHIVE_DIR] [BUILD_DIR]
"""
import html as htmlmod
import http.server
import io
import json
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
CONTRACT_PAGE = "contact"  # short, stable slug; the chrome is the same on every page
MENU = json.loads((ROOT / "content" / "_data" / "menu.json").read_text(encoding="utf-8"))


def expected_menu(url: str) -> tuple[str, list[str]]:
    """Sidebar text and link hrefs the template must render for a page URL.

    A sub-menu is present on the parent's page and on its children's pages
    (the rule the template implements in _includes/base.html)."""
    labels: list[str] = []
    links: list[str] = []
    for item in MENU:
        labels.append(item["label"])
        links.append(item["url"])
        children = item.get("children", [])
        if children and (item["url"] == url or any(c["url"] == url for c in children)):
            labels += [c["label"] for c in children]
            links += [c["url"] for c in children]
    return " ".join(labels), sorted(links)


def build_path(name: str) -> Path:
    """Build file for an archive filename.

    Pages emit /slug/ directories (GitHub Pages cannot serve extensionless
    files as HTML); .html files (index.html, 404.html) stay flat."""
    return BUILD / name if name.endswith(".html") else BUILD / name / "index.html"


def serve(directory: Path, port: int) -> None:
    class Handler(http.server.SimpleHTTPRequestHandler):
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
    text = text.replace("ontwerp: Boris Reuderink (b.reuderink@alumnus.utwente.nl)", "").strip()
    return text, imgs, links


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
    serve(BUILD, 8102)
    pages = sorted(p.name for p in ARCHIVE.iterdir() if p.is_file() and p.name != "manifest.tsv")
    struct_fail = []

    # Frontmatter `active` is an alias override (e.g. front page -> /intro);
    # otherwise the page URL is what the template highlights/expands.
    overrides = {}
    for f in (ROOT / "content").glob("*.md"):
        lines = f.read_text(encoding="utf-8").split("\n")
        if lines[0] == "---":
            fm = json.loads(lines[1])
            if fm.get("active") and fm["active"] != fm.get("permalink"):
                overrides[fm["permalink"]] = fm["active"]

    menu_fail = [u for item in MENU
                 for u in [item["url"]] + [c["url"] for c in item.get("children", [])]
                 if not build_path(u.lstrip("/")).is_file()]

    # 1. structural — file-based, no browser needed
    for name in pages:
        a_html = (ARCHIVE / name).read_text(encoding="utf-8")
        b_html = build_path(name).read_text(encoding="utf-8")
        a = extract(re.sub(r'<td class="sidebar" id="sidebar-left">.*?(?=<td class="main-content")', "", a_html, flags=re.S))
        aside = re.search(r"<aside id=\"sidebar-left\".*?</aside>", b_html, flags=re.S)
        b = extract(re.sub(r"<aside id=\"sidebar-left\".*?</aside>", "", b_html, flags=re.S))
        diffs = [k for k, (x, y) in {"text": (a[0], b[0]), "images": (a[1], b[1]), "links": (a[2], b[2])}.items() if x != y]
        if aside:
            # Page URL: /slug/ for directory pages, /index.html for the front page.
            url = "/" + name + ("" if name.endswith(".html") else "/")
            m_text, m_links = expected_menu(overrides.get(url, url))
            if extract(aside.group(0))[0] != m_text or extract(aside.group(0))[2] != m_links:
                diffs.append("menu")
        if diffs:
            struct_fail.append((name, diffs))

    # 2. contract — one rendered page
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        page.goto(f"http://127.0.0.1:8102/{CONTRACT_PAGE}", wait_until="load", timeout=15000)
        page.wait_for_timeout(300)
        shot = page.screenshot()
        browser.close()
    A = np.asarray(Image.open(io.BytesIO(shot)).convert("RGB"), dtype=np.int16)
    contract_fail = contract(A)

    print(f"checked {len(pages)} pages")
    for name, diffs in struct_fail:
        print(f"STRUCTURAL DIFF {name}: {diffs}")
    for u in menu_fail:
        print(f"MENU LINK MISSING {u}")
    if contract_fail:
        print(f"CONTRACT FAIL {CONTRACT_PAGE}: {contract_fail}")
    ok = not (struct_fail or contract_fail or menu_fail)
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

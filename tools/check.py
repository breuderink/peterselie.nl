#!/usr/bin/env python3
"""Build gate: structure, not judgment.

Checks the Jekyll build is servable: index.html and 404.html exist and
every internal href/src in every built page resolves THE WAY A BROWSER
WOULD resolve it: the user site serves at the domain root (no baseurl),
root-absolute refs resolve against the domain root and relative refs
against the page's own path. After resolution,
page links are checked under build/ (a file or a directory's index.html,
canonical form /slug/) and /files/ media against the SOURCE tree, not
build/: LFS media is excluded from the build (.jekyll-ignore) and served
from the repo checkout on GitHub Pages.
Stdlib only, so it runs locally with no dependencies.

Usage: python3 tools/check.py [BUILD_DIR]
"""
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent.parent
BUILD = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build"
# Must match baseurl in _config.yml ("" — user site, domain root).
BASEURL = ""
SITE = "https://peterselie.nl"
REF = re.compile(r'(?:href|src)="([^"]+)"')

# Dead on the old site too: the targets never existed (2026-11-13 probe
# against archive/live-2026-10-14b). Fixing or removing them is a content
# call for the owner; they point at the new site, so the site's own 404
# page shows instead of GitHub's. Drop an entry once fixed or pruned.
KNOWN_DEAD = {
    "/heleboelpoppen",
    "/waarismama",
    "/voorstellingtips",
    "/liedjesbladboerderij",
    "/liedjesbruggetje",
    "/liedjevisser",
    "/vertelvoorstellingrattenvangster",
    "/vertelvoorstellingerwt",
    "/knipliedje",
    "/links2",
    "/vogelmarionetten",
    "/leeuwmuis",
    "/files/zeggen15groot.jpg",
    "/files/Lesbrief Klalanaencr.pdf",
    "/files/beweeg_als_een_dier.mp3",
    "/files/Vertellen met extra's_artikel.pdf",
}


def main() -> int:
    fails = []
    pages = [BUILD / "index.html", BUILD / "404.html"] + sorted(
        BUILD.glob("*/index.html"))
    for p in pages:
        if not p.is_file():
            fails.append(f"missing {p.relative_to(BUILD)}")
            continue
        # The page's deployed URL: /slug/index.html -> /slug/.
        rel = p.relative_to(BUILD).as_posix()
        page_url = "/" + (rel[:-len("/index.html")] if rel.endswith("/index.html") else rel)
        for u in REF.findall(p.read_text(encoding="utf-8")):
            if u.startswith(("http", "//", "mailto:", "#", "data:")):
                continue  # external or anchor-only
            absu = u if u.startswith("/") else urljoin(page_url + "/", u)
            path = absu.split("#")[0]
            if path in KNOWN_DEAD:
                continue
            base = ROOT if path.startswith("/files/") else BUILD
            target = base / path.lstrip("/")
            if not (target.is_file() or (target / "index.html").is_file()):
                fails.append(f"{rel}: unresolvable {u!r}")
    for f in fails:
        print("FAIL", f)
    print("PASS" if not fails else f"FAIL ({len(fails)})")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Build gate: structure, not judgment.

Checks the build is servable: index.html and 404.html exist and every
internal href/src in every built page resolves in build/ — a file, or a
directory's index.html (canonical page form is /slug/). Stdlib only, so
it runs locally and in CI with no dependencies.

The oracle gate (tools/validate.py) — exact structural comparison against
the old site's snapshot — is opt-in: run it on re-import days, not on
every build.

Usage: python3 tools/check.py [BUILD_DIR]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build"
REF = re.compile(r'(?:href|src)="([^"]+)"')

# Dead on the old site too (checked against the oracle snapshot): fixing or
# removing them is a content call for the owner (TASKS t027). Drop an entry
# once the reference is fixed or the page pruned.
KNOWN_DEAD = {
    "/heleboelpoppen",
    "/waarismama",
    "/voorstellingtips",
    "/files/zeggen15groot.jpg",
}


def main() -> int:
    fails = []
    pages = [BUILD / "index.html", BUILD / "404.html"] + sorted(
        BUILD.glob("*/index.html"))
    for p in pages:
        if not p.is_file():
            fails.append(f"missing {p.relative_to(BUILD)}")
            continue
        for u in REF.findall(p.read_text(encoding="utf-8")):
            if not u.startswith("/") or u.startswith("//"):
                continue  # external, mailto:, or #anchor-only
            path = u.split("#")[0]
            if path in KNOWN_DEAD:
                continue
            target = BUILD / path.lstrip("/")
            if not (target.is_file() or (target / "index.html").is_file()):
                fails.append(f"{p.relative_to(BUILD)}: unresolvable {u!r}")
    for f in fails:
        print("FAIL", f)
    print("PASS" if not fails else f"FAIL ({len(fails)})")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())

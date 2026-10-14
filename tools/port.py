#!/usr/bin/env python3
"""Port archived Drupal pages to Eleventy content files.

Reads the dated snapshot (archive/live-<date>/) and writes content/<slug>.html:
one JSON frontmatter line (permalink, layout, title, h2, active, expand,
mission) followed by the verbatim node body extracted from the archive.

Usage: python3 tools/port.py ARCHIVE_DIR OUT_DIR
Stdlib only.
"""
import json
import re
import sys
from pathlib import Path

ARCHIVE_RE = re.compile(
    r"<!-- start main content -->\s*(.*?)\s*<!-- end main content -->", re.S
)


def port_page(src: Path, out_dir: Path) -> dict:
    html = src.read_text(encoding="utf-8")
    m_title = re.search(r"<title>(.*?)</title>", html, re.S)
    m_h2 = re.search(r'<h2 class="content-title">(.*?)</h2>', html, re.S)
    m_mission = re.search(r'<div id="mission">(.*?)</div>', html, re.S)
    m_active = re.search(r'<a href="(/[^"]*)"[^>]*class="active"', html)
    m_body = ARCHIVE_RE.search(html)
    missing = [n for n, m in [("title", m_title), ("h2", m_h2), ("body", m_body)] if not m]
    if missing:
        raise ValueError(f"{src.name}: missing {missing}")

    slug = "index" if src.name == "index.html" else src.name
    meta = {
        "permalink": "/index.html" if slug == "index" else f"/{slug}",
        "layout": "base.html",
        "title": m_title.group(1),
        "h2": m_h2.group(1),
        "active": m_active.group(1) if m_active else None,
        "expand": 'class="expanded"' in html,
        "mission": m_mission.group(1) if m_mission else None,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{slug}.html").write_text(
        "---\n" + json.dumps(meta, ensure_ascii=False) + "\n---\n" + m_body.group(1) + "\n",
        encoding="utf-8",
    )
    return meta


def main() -> None:
    arch, out = Path(sys.argv[1]), Path(sys.argv[2])
    pages = sorted(
        p for p in arch.iterdir()
        if p.is_file() and p.name != "manifest.tsv"
    )
    ok, fail = [], []
    for p in pages:
        try:
            port_page(p, out)
            ok.append(p.name)
        except Exception as e:  # noqa: BLE001
            fail.append((p.name, str(e)))
    print(f"ported {len(ok)} pages -> {out}/")
    for name, err in fail:
        print(f"FAILED {name}: {err}", file=sys.stderr)
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()

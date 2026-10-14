#!/usr/bin/env python3
"""Convert eligible content pages from HTML to markdown (t010).

A page is eligible when its body uses only markup markdown can express:
no iframe/object/embed, and no img with width/height/class/title (the
markdown image syntax cannot carry those). <br> is kept as a literal <br>,
because markdown single-newline semantics would change the rendering.

Eligible pages are rewritten as <name>.md (same JSON frontmatter) and the
.html file is deleted. Re-run is a no-op once all eligible pages are .md.
The validator (tools/validate.py) is the gate: run it after converting.

Usage: python3 tools/to_md.py [CONTENT_DIR]
"""
import re
import sys
from pathlib import Path

from markdownify import MarkdownConverter

CONTENT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "content"
BLOCKED = re.compile(r"<(iframe|object|embed)\b")
SIZED_IMG = re.compile(r"<img\b[^>]*\b(width|height|class|title)=")
# Anchors wrapping a break or image (Drupal's "image links") have no
# markdown equivalent.
ANCHOR_MEDIA = re.compile(r"<a\b[^>]*>\s*(?:<br|<img)", re.S)
# markdown-it percent-encodes spaces in link URLs (3 Mythen.pdf -> 3%20Mythen.pdf),
# changing the href.
SPACED_HREF = re.compile(r"<a\b[^>]*href=\"[^\"]+ ")


class BrConverter(MarkdownConverter):
    def convert_br(self, el, text, parent_tags):  # keep line breaks literal
        return "<br>"

    def convert_a(self, el, text, parent_tags):
        # CommonMark link destinations may not contain spaces; wrap in <>
        md = super().convert_a(el, text, parent_tags)
        href = el.get("href", "")
        if " " in href:
            md = md.replace(f"]({href}", f"](<{href}>", 1)
        return md


def convert(src: Path) -> Path:
    raw = src.read_text(encoding="utf-8")
    fm, body = raw.split("---\n", 2)[1], raw.split("---", 2)[2].lstrip("\n")
    out = src.with_suffix(".md")
    out.write_text(f"---\n{fm}---\n{BrConverter().convert(body)}", encoding="utf-8")
    src.unlink()
    return out


def main() -> int:
    converted, kept = [], []
    for src in sorted(CONTENT.glob("*.html")):
        body = src.read_text(encoding="utf-8").split("---", 2)[2]
        if (BLOCKED.search(body) or SIZED_IMG.search(body)
                or ANCHOR_MEDIA.search(body) or SPACED_HREF.search(body)):
            kept.append(src.name)
            stale = src.with_suffix(".md")  # self-heal after a re-port
            if stale.exists():
                stale.unlink()
            continue
        convert(src)
        converted.append(src.name)
    print(f"converted {len(converted)} pages -> .md")
    for name in converted:
        print("  md   ", name.removesuffix(".html"))
    print(f"kept {len(kept)} pages as .html")
    return 0


if __name__ == "__main__":
    sys.exit(main())

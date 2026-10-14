#!/usr/bin/env python3
"""Convert content pages from HTML to markdown (t013: stdlib-only).

The old markdownify-based converter was lost in the container rebuild and
pip has no network (pypi DNS blocked), so this re-implements it with
html.parser. Rules (all verified against the snapshot; the validator is
the gate — LOG 2026-10-14T17:38):

- <p>  -> paragraph; text keeps original whitespace (a single newline
          renders as a space, as on the live site)
- <br> -> literal <br> (markdown single-newline semantics would drift)
- <img> -> ![alt](src "title"?); width/height/class are redundant
          (attrs == natural size, 673/673 — LOG 11:10); a src or href
          containing spaces or parens is wrapped in <> (CommonMark
          forbids them bare — bare spaces make markdown-it drop the
          construct entirely, which is the bug of the t012 tree)
- <a>  -> [text](href "title"?); never the <word> autolink form when
          text == href (a bare <word> is parsed as an HTML tag and the
          link and its text vanish)
- <em>/<strong> -> * / ** emphasis
- <ul>/<li> -> markdown list when well-formed; a malformed list
          (enverder: unclosed <li>, <p> in <li>) together with its stray
          top-level <li> siblings is emitted verbatim — identical bytes,
          and the browser repairs it exactly as on the live site
- <div> aspect-ratio wrappers, top-level <iframe> and <object> ->
          verbatim raw-HTML lines (markdown-it passes block HTML through;
          inside a <p> they stay inline, also verbatim)
- text lines that would start a markdown list (-, *, +, 1.) get a
          backslash-escape so the literal dash text stays literal

Pages are rewritten as <name>.md (same frontmatter) and the .html file is
deleted; .md files left over from pages not in this re-port are removed.

Usage: python3 tools/to_md.py [CONTENT_DIR]
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

CONTENT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "content"

INLINE = {"a", "em", "strong", "img", "br"}
VOID = {"img", "br", "embed", "param"}
RAW_BLOCKS = {"div", "iframe", "object"}
LISTY = re.compile(r"^(\s*)(?:([-*+]) |(\d+)\. )")


class El:
    def __init__(self, tag, attrs, start):
        self.tag, self.attrs, self.children, self.start, self.end = tag, attrs, [], start, start
        self.raw = None  # exact source bytes, set on RAW_BLOCKS
        self.stag = None  # exact start-tag bytes


class Parser(HTMLParser):
    def __init__(self, body):
        super().__init__(convert_charrefs=True)
        self.body = body
        self.line_starts = [0]
        for m in re.finditer("\n", body):
            self.line_starts.append(m.end())
        self.root = El("#root", [], 0)
        self.stack = [self.root]
        self.stray_p = []  # offsets of </p> with no open <p>

    def charpos(self) -> int:
        """Absolute offset at the start of the tag the current handler is for.

        CPython calls handle_*tag before updatepos(i, k), so getpos() points
        at the tag's '<' (verified against the parser source, 3.14).
        """
        line, offset = self.getpos()
        return self.line_starts[line - 1] + offset

    def handle_starttag(self, tag, attrs):
        start = self.charpos()
        el = El(tag, attrs, start)
        el.end = start + len(self.get_starttag_text())
        el.stag = self.get_starttag_text()
        # browser "in body": a new li closes the open li; a block start
        # closes an open <p>. iframe/object do NOT close <p> — they are
        # phrasing content and sit inside <p> on the live site
        if tag == "li":
            # close the innermost open li, but only inside the same list
            lo = 1
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i].tag == "ul":
                    lo = i + 1
                    break
            for i in range(len(self.stack) - 1, lo - 1, -1):
                if self.stack[i].tag == "li":
                    del self.stack[i:]
                    break
        elif tag in ("p", "ul", "li"):
            for i in range(len(self.stack) - 1, 0, -1):
                if self.stack[i].tag == "p":
                    del self.stack[i:]
                    break
        self.stack[-1].children.append(el)
        if tag not in VOID:
            self.stack.append(el)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                self.stack[i].end = self.charpos() + len(f"</{tag}>")
                if tag in RAW_BLOCKS:  # keep the exact source for verbatim emit
                    self.stack[i].raw = self.body[self.stack[i].start:self.stack[i].end]
                del self.stack[i:]
                return
        # stray closing tag: the browser ignores it, but a stray </p>
        # materializes as an empty <p></p> in the DOM (measured: 15px of
        # layout, archiefvoorstelling) — record it so render_body emits
        # the same empty paragraph
        if tag == "p":
            self.stray_p.append(self.charpos())

    def handle_data(self, data):
        if data:
            # U+2028/2029 reach the browser as spaces, but they are
            # whitespace to Python (a .strip() below would eat them) and to
            # markdown-it (normalized away): keep them as entities, which
            # decode to the same DOM char
            self.stack[-1].children.append(data.replace("\u2028", "&#x2028;").replace("\u2029", "&#x2029;"))


def img_md(attrs: dict) -> str:
    src, alt, title = attrs.get("src", ""), attrs.get("alt", ""), attrs.get("title")
    if "]" in alt or '"' in (title or ""):
        raise ValueError(f"unexpressable img alt/title: {alt!r} / {title!r}")
    if re.search(r"[ )]", src):
        src = f"<{src}>"
    s = f"![{alt}]({src}"
    if title is not None:
        s += f' "{title}"'
    return s + ")"


def render_inline(el: El) -> str:
    t, a = el.tag, dict(el.attrs)
    if t in RAW_BLOCKS:  # e.g. an <iframe> inside a <p>: inline raw HTML
        # always the exact source bytes: a malformed tag (a <br /> inside
        # the iframe start tag, one page) must reach the browser unchanged
        # — re-serializing the parsed attrs changes what the browser keeps
        # (on the live page the junk follows the tag as visible text)
        return (el.raw or el.stag).strip()
    if t == "br":
        return "<br>"
    if t == "img":
        return img_md(a)
    if t == "a":
        href, title = a.get("href", ""), a.get("title")
        tags = [c.tag for c in el.children if not isinstance(c, str)]
        post = []
        if "img" in tags and set(tags) <= {"img", "br"}:
            # Drupal "image link": the browser renders <a><br?><img><br?></a>
            # as break(s) around the linked image, so each break keeps its
            # ORIGINAL position and stays inline (a bare <br> line would
            # start a type-7 HTML block and swallow the markdown after it).
            # A break before the image stays inside the label; after it,
            # outside — the anchor boundary is not visible to the renderer.
            img = next(c for c in el.children if not isinstance(c, str) and c.tag == "img")
            pre, seen_img = [], False
            for c in el.children:
                if isinstance(c, str):
                    continue
                if c is img:
                    seen_img = True
                elif c.tag == "br":
                    (pre if not seen_img else post).append("<br>")
            inner = "".join(pre) + img_md(dict(img.attrs))
        else:
            # trim: a leading space defeats the link label, the browser
            # collapses it anyway, so this renders identically
            inner = ("".join(c if isinstance(c, str) else render_inline(c) for c in el.children)).strip()
        if not href and not post:
            # broken <a> without href (the live /historie page): the
            # browser renders it as plain text, but the anchor ELEMENT is
            # still in the live DOM — emit it as raw HTML so the page
            # (and the tag-based text extraction) see the same structure
            return f"<a>{inline_text(el)}</a>"
        if re.search(r"[ )]", href):
            href = f"<{href}>"
        s = f"[{inner}]({href}"
        if title is not None:
            s += f' "{title}"'
        return s + ")" + "".join(post)
    if t in ("em", "strong"):
        # trim: an inner leading space defeats the flanking rules ("* x*" is
        # not emphasis); the browser collapses it anyway
        mark = "*" if t == "em" else "**"
        inner = ("".join(c if isinstance(c, str) else render_inline(c) for c in el.children)).strip()
        return mark + inner + mark
    raise ValueError(f"unexpected inline <{t}>")


def inline_text(el: El) -> str:
    return "".join(c if isinstance(c, str) else render_inline(c) for c in el.children)


def esc_line(ln: str) -> str:
    m = re.match(LISTY, ln)
    if not m:
        return ln
    ws, bullet, num = m.groups()
    rest = ln[m.end():]
    return f"{ws}\\{bullet} {rest}" if bullet else f"{ws}{num}\\. {rest}"


def escape_listy(s: str) -> str:
    return "\n".join(esc_line(ln) for ln in s.split("\n"))


BR_LINE = re.compile(r"^\s*<br\s*/?>\s*$")


def no_br_block_starts(blocks: list) -> list:
    # A line that is only <br> must not start a markdown block: with html
    # enabled markdown-it reads it as a type-7 HTML block that swallows
    # every following markdown line until a blank line (the t012 bug).
    out = []
    for b in blocks:
        lines = b.split("\n")
        while lines and BR_LINE.match(lines[0]):
            br = lines.pop(0)
            if out and out[-1].strip():
                out[-1] += "\n" + br
            else:
                out.append(br)
        if any(x.strip() for x in lines):
            out.append("\n".join(lines))
    return out


def clean_list(ul: El) -> bool:
    for c in ul.children:
        if isinstance(c, str):
            if c.strip():
                return False
        elif c.tag != "li":
            return False
    for li in ul.children:
        if isinstance(li, str):
            continue
        for d in li.children:
            if isinstance(d, str) or d.tag in INLINE:
                continue
            if d.tag == "ul" and clean_list(d):
                continue
            return False
    return True


def render_ul(ul: El, depth: int = 0) -> list:
    pad = "  " * depth
    lines = []
    for li in ul.children:
        if isinstance(li, str):
            continue
        subs = [d for d in li.children if not isinstance(d, str) and d.tag == "ul"]
        head = "".join(
            d if isinstance(d, str) else render_inline(d)
            for d in li.children if not (isinstance(d, El) and d.tag == "ul")
        ).strip()
        if head:
            lines.append(f"{pad}- {head}")
        for s in subs:
            lines.extend(render_ul(s, depth + 1))
    return lines


def has_raw_block(el: El) -> bool:
    for c in el.children:
        if isinstance(c, str):
            continue
        if c.tag in RAW_BLOCKS or has_raw_block(c):
            return True
    return False


def p_verbatim(c: El, kids: list, i: int, body: str) -> bool:
    # Two shapes must keep their original bytes, because markdown cannot
    # express them: a <p> wrapping an <iframe>/<object>/<div> — the
    # browser renders <p><iframe>…</iframe></p> WITH the paragraph box;
    # a bare raw-HTML line in markdown becomes a top-level HTML block and
    # loses it (hond, spookmarionet) — and a <p> whose first content is a
    # <br>: a leading <br> line starts a type-7 HTML block, and moving
    # the break into the previous paragraph shifts it across the p margin
    # (introduction). Both render byte-identical when emitted verbatim.
    if has_raw_block(c):
        return True
    first = next((x for x in c.children if not (isinstance(x, str) and not x.strip())), None)
    return isinstance(first, El) and first.tag == "br"


def render_body(body: str) -> str:
    p = Parser(body)
    p.feed(body)
    kids = p.root.children
    blocks, i, sp = [], 0, 0

    def flush_stray(before: int) -> None:
        nonlocal sp
        while sp < len(p.stray_p) and p.stray_p[sp] < before:
            blocks.append("<p></p>")
            sp += 1

    while i < len(kids):
        c = kids[i]
        if isinstance(c, str):
            if c.strip():
                raise ValueError(f"stray text: {c[:40]!r}")
            i += 1
        elif c.tag == "p":
            flush_stray(c.start)
            if p_verbatim(c, kids, i, body):
                nxt = next((x for x in kids[i + 1:] if isinstance(x, El)), None)
                blocks.append(body[c.start:nxt.start if nxt else len(body)].strip())
            else:
                blocks.append(escape_listy(inline_text(c)))
            i += 1
        elif c.tag in RAW_BLOCKS:
            flush_stray(c.start)
            blocks.append(c.raw.strip())
            i += 1
        elif c.tag in ("ul", "li"):
            # a well-formed lone <ul> becomes a markdown list; anything
            # list-shaped around it (stray <li>, dirty nesting) stays verbatim
            if c.tag == "ul" and clean_list(c):
                nxt = kids[i + 1] if i + 1 < len(kids) else None
                if not (isinstance(nxt, El) and nxt.tag in ("ul", "li")):
                    flush_stray(c.start)
                    blocks.append("\n".join(render_ul(c)))
                    i += 1
                    continue
            # verbatim run: slice by stream position, not element ends —
            # the source leaves <li> unclosed, and the browser does too
            j = i
            while j < len(kids) and isinstance(kids[j], El) and kids[j].tag in ("ul", "li"):
                j += 1
            k = j
            while k < len(kids) and isinstance(kids[k], str):
                k += 1
            end = kids[k].start if k < len(kids) else len(body)
            s = body[c.start:end].strip()
            if not s.startswith(f"<{c.tag}"):
                raise ValueError(f"verbatim run does not start with <{c.tag}>: {s[:60]!r}")
            flush_stray(c.start)
            blocks.append(s)
            i = j
        else:
            raise ValueError(f"unexpected top-level <{c.tag}>")
    flush_stray(len(body))
    return "\n\n".join(no_br_block_starts(blocks)) + "\n"


def convert(raw: str) -> str:
    fm, body = raw.split("---\n", 2)[1], raw.split("---", 2)[2].lstrip("\n")
    # U+2028/2029 that sit in verbatim slices (raw HTML blocks, list runs)
    # also become entities: the browser decodes them to the same DOM char
    md = render_body(body).replace("\u2028", "&#x2028;").replace("\u2029", "&#x2029;")
    return f"---\n{fm}---\n{md}"


def main() -> int:
    results, fails = {}, []
    for src in sorted(CONTENT.glob("*.html")):
        try:
            results[src.stem] = convert(src.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001 — report every page, fail as a batch
            fails.append((src.name, str(e)))
    if fails:
        for name, err in fails:
            print(f"FAILED {name}: {err}", file=sys.stderr)
        return 1
    written = set()
    for stem, md in results.items():
        (CONTENT / f"{stem}.md").write_text(md, encoding="utf-8")
        (CONTENT / f"{stem}.html").unlink()
        written.add(stem)
    for stale in sorted(CONTENT.glob("*.md")):
        if stale.stem not in written:
            stale.unlink()
            print(f"removed stale {stale.name}")
    print(f"converted {len(results)} pages -> .md")
    return 0


if __name__ == "__main__":
    sys.exit(main())

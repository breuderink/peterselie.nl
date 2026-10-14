#!/usr/bin/env python3
"""Snapshot a site: BFS-crawl pages and assets from a base URL into a dir,
preserving paths, with a sha256 manifest.

Usage: python3 tools/snapshot.py BASE_URL ARCHIVE_DIR
Stdlib only. Pages and assets are distinguished by content-type.
Internal links (same host) are followed; external links are ignored.
"""
import hashlib
import re
import sys
import urllib.parse
import urllib.request
from collections import deque

PAGE_TYPES = ("text/html",)


def fetch(url: str) -> tuple[int, bytes, str]:
    p = urllib.parse.urlsplit(url)
    safe = p._replace(
        path=urllib.parse.quote(p.path, safe="/:@!$&'()*+,;=~-"),
        query=urllib.parse.quote(p.query, safe="=&:;+/?"),
    ).geturl()
    req = urllib.request.Request(safe, headers={"User-Agent": "peterselie-snapshot/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read(), r.headers.get("Content-Type", "")


def main() -> None:
    base = sys.argv[1].rstrip("/")
    arch = sys.argv[2]
    host = urllib.parse.urlparse(base).netloc

    queue: deque[str] = deque([base + "/"])
    seen: set[str] = set()
    rows: list[tuple[str, int, int, str, str]] = []  # path, status, bytes, type, sha256

    while queue:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        try:
            status, body, ctype = fetch(url)
        except Exception as e:  # noqa: BLE001 - record and continue
            rows.append((url, 0, 0, f"error: {e}", ""))
            continue
        rel = urllib.parse.urlparse(url).path or "/"
        if rel == "/":
            rel = "/index.html"
        dest = f"{arch}{rel}"
        import pathlib
        pathlib.Path(dest).parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            f.write(body)
        rows.append((url, status, len(body), ctype, hashlib.sha256(body).hexdigest()))
        print(f"{status} {len(body):>7}  {rel}")
        if ctype.split(";")[0] not in PAGE_TYPES:
            continue
        for m in re.findall(r'(?:href|src)="([^"#]+)"', body.decode("utf-8", "replace")):
            full = urllib.parse.urljoin(url, m)
            if urllib.parse.urlparse(full).netloc == host:
                queue.append(full)

    rows.sort()
    with open(f"{arch}/manifest.tsv", "w") as f:
        f.write("url\tstatus\tbytes\tcontent_type\tsha256\n")
        for row in rows:
            f.write("\t".join(str(x) for x in row) + "\n")
    print(f"\n{len(rows)} items -> {arch}/manifest.tsv")


if __name__ == "__main__":
    main()

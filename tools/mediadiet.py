#!/usr/bin/env python3
"""Post-build media diet (t013): shrink the deploy payload, archive untouched.

Runs AFTER `npx @11ty/eleventy`, before the validator. Lossless only:

- orphan files in build/files/ (referenced by no built page) are deleted
  — the 2026-10-14 snapshot has none: all 827 files are referenced, most
  via absolute https://peterselie.nl/files/... URLs (the earlier "78
  orphans / 205 MB" audit missed those — LOG 2026-10-15T21:xx)
- interview.m4a.zip (54 MB) is byte-identical Radiointerview.m4a in a zip
  (verified by sha256, LOG 2026-10-15T08:38) -> replaced by a small
  meta-refresh redirect to the .m4a; the /files/interview.m4a.zip URL keeps working
- PNG: optipng -o2 (lossless, NO --strip: stripping iCCP loses the embedded
  Display P3 profile that browsers color-manage — PIL pixels stay equal but
  the browser renders different colors; caught by the pixel validator,
  2026-10-15), pixel-verified, restored on any drift
- TIF: re-saved with LZW (bouwplaat.tif was stored raw), pixel-verified,
  replaced only if smaller
- JPEG: NOT re-encoded. Decode->encode round-trips are provably lossy
  (same Q tables + 4:4:4, pixels still drift — measured 2026-10-15); a
  DCT-domain tool (jpegtran) is not installable offline. Skipped, not approximated.
- GIF / audio / video: untouched. No lossless GIF tool; lossy = user sign-off.

Idempotent: safe to re-run; a file is only replaced when the result is
pixel-identical AND no larger.

Usage: python3 tools/mediadiet.py [BUILD_DIR]
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

BUILD = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "build"
FILES = BUILD / "files"
REF_RE = re.compile(r'(?:src|href)="([^"]+)"')
ZIP_NAME = "interview.m4a.zip"
ZIP_TARGET = "/files/Radiointerview.m4a"
REDIRECT_HTML = f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta http-equiv="refresh" content="0; url={ZIP_TARGET}"></head>
<body>Deze bestandsnaam is overgedraaid naar
<a href="{ZIP_TARGET}">{ZIP_TARGET.rsplit("/", 1)[-1]}</a>.</body></html>
"""


def referenced() -> set[str]:
    """File names under /files/ referenced by any built page or stylesheet.

    Pages mix relative (/files/x) and absolute (https://peterselie.nl/files/x)
    URLs — match the LAST /files/ segment, so both count. Every /files/ URL in
    the build is a src=/href= (verified 2026-10-15, 832/832).
    """
    refs = set()
    for p in BUILD.rglob("*"):
        if p.is_file() and FILES not in p.parents:
            for m in REF_RE.findall(p.read_text(encoding="utf-8", errors="replace")):
                i = m.rfind("/files/")
                if i >= 0:
                    refs.add(m[i + len("/files/"):])
    return refs


def pixels(path: Path) -> bytes:
    # Normalize: optipng drops a fully-opaque alpha channel (RGBA -> RGB),
    # which is lossless but changes raw tobytes(). Compare in a common
    # colorspace instead (measured on Screenshot.png, alpha 255/255).
    im = Image.open(path)
    return im.convert("RGBA").tobytes()


def mb(n: int) -> str:
    return f"{n / 2**20:.1f} MB"


def main() -> int:
    if not FILES.is_dir():
        sys.exit(f"missing {FILES} — run `npx @11ty/eleventy` first")
    before_files = list(FILES.iterdir())
    before = sum(p.stat().st_size for p in before_files)
    refs = referenced()
    ok = True

    # 1. orphans — referenced set comes from the BUILT pages, so the
    # redirect below does not need to keep the zip "referenced"
    removed, removed_bytes = [], 0
    for p in sorted(FILES.iterdir()):
        if p.is_file() and p.name not in refs:
            removed.append(p)
            removed_bytes += p.stat().st_size
            p.unlink()
    print(f"orphans:   {len(removed):3d} files, {mb(removed_bytes)} removed"
          + (f"  (e.g. {removed[0].name}, {removed[1].name})" if len(removed) > 1 else ""))

    # 2. zip dedupe -> redirect (only if the real m4a is present)
    z, target = FILES / ZIP_NAME, FILES / ZIP_TARGET.rsplit("/", 1)[-1]
    if z.is_file() and target.is_file() and z.stat().st_size > len(REDIRECT_HTML):
        zb = z.stat().st_size
        z.write_text(REDIRECT_HTML, encoding="utf-8")
        print(f"zip:       {ZIP_NAME} {mb(zb)} -> redirect to {ZIP_TARGET}")

    # 3. PNG — optipng in place, pixel-verified, restored on any drift
    for p in sorted(FILES.iterdir()):
        if p.suffix.lower() != ".png":
            continue
        orig = pixels(p)
        bak = p.with_suffix(".png.pre")
        shutil.copy2(p, bak)
        r = subprocess.run(["optipng", "-o2", "-quiet", str(p)],
                           capture_output=True)
        try:
            if r.returncode != 0 or pixels(p) != orig:
                shutil.move(str(bak), p)
                ok = False
                print(f"PNG FAIL  {p.name}: rc={r.returncode} — restored")
        finally:
            bak.unlink(missing_ok=True)
    print(f"png:       optimized (lossless, pixel-verified)")

    # 4. TIF — LZW re-save, pixel-verified, replaced only if smaller
    for p in sorted(FILES.iterdir()):
        if p.suffix.lower() != ".tif":
            continue
        orig_bytes, orig = p.stat().st_size, pixels(p)
        out = p.with_name(p.name + ".lzw.tiff")  # PIL picks the format from the extension
        Image.open(p).save(out, compression="tiff_lzw")
        new_bytes = out.stat().st_size
        if pixels(out) == orig and new_bytes < orig_bytes:
            out.replace(p)
            print(f"tif:       {p.name} {mb(orig_bytes)} -> {mb(new_bytes)} (LZW)")
        else:
            out.unlink(missing_ok=True)
            print(f"tif:       {p.name} kept (LZW {mb(new_bytes)} vs {mb(orig_bytes)})")

    after = sum(p.stat().st_size for p in FILES.iterdir())
    print(f"\nbuild/files: {len(before_files)} -> {len(list(FILES.iterdir()))} files, "
          f"{mb(before)} -> {mb(after)} (-{mb(before - after)})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Media diet (t013): shrink the media payload, archive untouched.

The source media in files/ is committed ALREADY dieted, so this is NOT in
the build chain — run it once after a re-import (port.py) brings back the
undieted originals: `python3 tools/mediadiet.py .` (diets ./files in
place). It can also diet a build dir: `python3 tools/mediadiet.py build`.
Lossless passes,
plus one user-approved lossy audio pass (sign-off 2026-10-16):

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
- JPEG: jpegtran -copy icc -optimize (lossless, DCT-domain). -copy icc keeps
  the ICC profile (552 of 718 JPEGs carry one, mostly Apple Display P3 —
  browsers color-manage it; stripping it changes rendered colors while PIL
  pixels stay equal, zelfpoppenmaken pixel-diff, 2026-10-16) and drops
  EXIF/comment (0 of 718 have an orientation tag). This libjpeg-turbo
  build has no "unsafe" mode — only none|comments|icc|all.
  pixel-verified, kept only if smaller.
- AUDIO (lossy, user-approved): m4a -> AAC 96 kbps, mp3 -> MP3 96 kbps,
  container/extension unchanged; kept only if smaller AND duration within
  2%. The four m4a ZIPs are download files, not inlined — left alone.
- GIF / video: untouched.

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


def jpeg_pass() -> None:
    # jpegtran cannot write in place: read src, write to a sibling temp.
    changed = 0
    for p in sorted(FILES.iterdir()):
        if p.suffix.lower() not in (".jpg", ".jpeg"):
            continue
        before = pixels(p)
        out = p.with_name(p.name + ".jt.jpg")
        r = subprocess.run(["jpegtran", "-copy", "icc", "-optimize",
                            "-outfile", str(out), str(p)], capture_output=True)
        if r.returncode != 0:
            out.unlink(missing_ok=True)
            print(f"jpeg:      {p.name} FAILED rc={r.returncode}: {r.stderr[:120]!r}")
            raise SystemExit(1)
        if out.stat().st_size < p.stat().st_size and pixels(out) == before:
            out.replace(p)
            changed += 1
        else:
            out.unlink(missing_ok=True)
    print(f"jpeg:      {changed} optimized (lossless, pixel-verified)")


AUDIO_CMD = {".m4a": ["aac", "96k"], ".mp3": ["libmp3lame", "96k"]}


def audio_pass() -> None:
    # Lossy (user-approved 2026-10-16): speech/song recordings at 96 kbps,
    # container and extension unchanged. Guard: smaller AND duration intact.
    def dur(f: Path) -> float:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration", "-of", "default=nw=1:nk=1",
                            str(f)], capture_output=True, text=True)
        return float(r.stdout.strip())

    changed = saved = 0
    for p in sorted(FILES.iterdir()):
        if p.suffix.lower() not in AUDIO_CMD:
            continue
        codec, brate = AUDIO_CMD[p.suffix.lower()]
        out = p.with_name(p.name + ".enc" + p.suffix.lower())
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(p),
                            "-vn", "-c:a", codec, "-b:a", brate, str(out)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            out.unlink(missing_ok=True)
            print(f"audio:     {p.name} FAILED: {r.stderr[:120]!r}")
            raise SystemExit(1)
        if out.stat().st_size >= p.stat().st_size:
            out.unlink(missing_ok=True)
            continue
        a, b = dur(p), dur(out)
        if abs(a - b) / a > 0.02:
            out.unlink(missing_ok=True)
            print(f"audio:     {p.name} duration {a:.1f}s -> {b:.1f}s — FAIL")
            raise SystemExit(1)
        saved += p.stat().st_size - out.stat().st_size
        out.replace(p)
        changed += 1
    print(f"audio:     {changed} re-encoded @96k "
          f"({mb(saved)} saved, user-approved lossy)")


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

    # 5. JPEG — jpegtran in DCT domain (lossless), pixel-verified
    jpeg_pass()

    # 6. AUDIO — lossy, user-approved; see module docstring
    audio_pass()

    after = sum(p.stat().st_size for p in FILES.iterdir())
    print(f"\nbuild/files: {len(before_files)} -> {len(list(FILES.iterdir()))} files, "
          f"{mb(before)} -> {mb(after)} (-{mb(before - after)})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

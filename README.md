# peterselie.nl

Source code of the website. Jekyll builds it from the pages; GitHub
Pages deploys it natively on every push to `main` ("Deploy from a
branch", no custom build step).

## Editing pages

Only two files are ever touched:

- `content/*.md` — the pages (markdown)
- `_data/navigation.yml` — the side-bar menu (order, labels, one level
  of sub-menus)

The editing guide with this site's markdown rules is in
[EDITING.md](EDITING.md).

## Media

All media (images, audio, video) lives in `files/` as plain git blobs
(no LFS — GitHub Pages serves the checkout, and it does not smudge
LFS). Put new files in `files/` and link them from a page as
`/files/name.ext`.

## Building locally

```bash
bundle install
bundle exec jekyll build --destination build
python3 tools/check.py   # link/asset check over all pages -> PASS
```

View locally: `python3 -m http.server -d build 8000` →
http://localhost:8000/

## Publishing

Pushing to `main` is enough. The one-time GitHub setup and the
post-deploy checklist are in [DEPLOY.md](DEPLOY.md).

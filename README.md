# peterselie.nl

Source code of the website. Eleventy builds the site from the pages;
every push to `main` builds and publishes it to GitHub Pages
automatically (`.github/workflows/deploy.yml`).

## Editing pages

Only two files are ever touched:

- `content/*.md` — the pages (markdown)
- `content/_data/menu.json` — the side-bar menu (order, labels, one
  level of sub-menus)

The editing guide with this site's markdown rules is in
[EDITING.md](EDITING.md).

## Media

All media (images, audio, video) lives in `files/`, stored via Git LFS —
run `git lfs install` once per machine. Put new files in `files/` and
link them from a page as `/files/name.ext`.

## Building locally

```bash
npm install     # @11ty/eleventy (dev dependency)
npm run build   # cleans build/, builds, runs the link/asset check -> PASS
```

View locally: `python3 -m http.server -d build 8000` →
http://localhost:8000

## Publishing

Pushing to `main` is enough. The one-time GitHub setup and the
post-deploy checklist are in [DEPLOY.md](DEPLOY.md).

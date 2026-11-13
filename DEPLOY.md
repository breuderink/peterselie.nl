# Deploying

GitHub Pages builds this repo with Jekyll on every push to `main` —
"Deploy from a branch", no custom build step. One-time repo setting:
Settings → Pages → Source: **Deploy from a branch**, branch `main`,
directory **/ (root)**. (If Pages was previously set to "GitHub
Actions", switch it back.)

## What the build does

- `content/*.md` → `slug/index.html` — per-page `permalink` front
  matter keeps the legacy Drupal paths (`/slug/` directory form).
- `_data/navigation.yml` → sidebar menu, rendered by `_includes/nav.html`
  (active state and sub-menu expansion derived from the URL).
- `files/resources/*` (stylesheet, banner, favicon) → copied into the
  output; referenced with `relative_url`, so they carry the baseurl.
- `files/*` (LFS media) → **excluded from the build** via
  `.jekyll-ignore`: copying ~332 MB of media would time out GitHub's
  build. Pages serves those files from the repo checkout instead.
- `jekyll-redirect-from` (an allowed GitHub Pages plugin, enabled in
  `_config.yml`) → legacy Drupal URL mapping. The old site's alias
  paths are exactly the new slugs (verified 2026-11-13), so nothing is
  mapped yet; old extensionless URLs (`/visie`) are covered by Pages'
  301 to `/visie/`. If an old node id or other alias ever needs to
  reach a page, add `redirect_from: ["/node/12"]` to that page's front
  matter.

## URLs

Pages are emitted as directories: `/visie/` → `visie/index.html`.
GitHub Pages infers the Content-Type from the file extension and cannot
serve extensionless pages as HTML.

Menu and asset URLs carry the baseurl (`/peterselie.nl/...`), so they
resolve on both the project URL and the custom domain. Body links in
the markdown pages stay root-relative (`/files/...`, `/visie/`) — that
matches the custom domain (the end state), so on the
`breuderink.github.io` project URL the chrome and menu work but body
links 404 until the CNAME is active. The local build is faithful to the
custom domain:

```
python3 -m http.server -d build 8000   # -> http://localhost:8000/peterselie.nl/
```

Old extensionless URLs (`/visie`) keep working only if Pages 301s them
to `/visie/` — probe **after** the DNS switchover (before it, the old
site answers):

```
curl -sI https://peterselie.nl/visie | head -3
```

Expect `301` + `Location: .../visie/`.

## First-deploy checklist

1. Open the project URL — chrome, banner, menu (with sub-menu), one
   page.
2. Open one `/files/...` image and check it is a real image, **not an
   LFS pointer** (a few lines of text starting `version https://...`).
   If it is a pointer, the Pages checkout did not smudge LFS — media
   will need a different route (owner call).
3. Smoke a page + the 404 page.
4. CNAME + DNS switchover, then the 301 probe above.

## Local build + check

```
bundle install
bundle exec jekyll build --destination build
python3 tools/check.py
```

The gate checks `index.html`, `404.html` and every `/slug/` page: all
internal links and file references must resolve (media against the
source `files/` tree). Ends in `PASS` or `FAIL (n)`.

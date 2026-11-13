# Deploying

GitHub Pages builds this repo with Jekyll on every push to `main` —
"Deploy from a branch", no custom build step. The repo is a **user
site**: its name is `breuderink.github.io`, so the site serves at the
domain root on peterselie.nl once the CNAME is active — required, because
the legacy Drupal URLs (`/slug/`, `/files/...`) must resolve at the
root. (A project page keeps its `/project-name` path even under a
CNAME, so it cannot do this.) One-time repo setting: Settings → Pages
→ Source: **Deploy from a branch**, branch `main`, directory **/
(root)**. (If Pages was previously set to "GitHub Actions", switch it
back.)

## What the build does

- `content/*.md` → `slug/index.html` — per-page `permalink` front
  matter keeps the legacy Drupal paths (`/slug/` directory form).
- `_data/navigation.yml` → sidebar menu, rendered by `_includes/nav.html`
  (active state and sub-menu expansion derived from the URL).
- `files/resources/*` (stylesheet, banner, favicon) → copied into the
  output; referenced with `relative_url` (root-absolute, no baseurl).
- `files/*` (media, plain git blobs — no LFS) → **excluded from the
  build** via `.jekyll-ignore`: copying ~334 MB would time out
  GitHub's build. Pages serves those files from the repo checkout
  instead.
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

All URLs are root-absolute: menu and asset links via `relative_url`
(no baseurl), body links as authored in the markdown (`/files/...`,
`/visie/`). They resolve at the domain root — the local build is
faithful to the deployed site:

```
python3 -m http.server -d build 8000   # -> http://localhost:8000/
```

Old extensionless URLs (`/visie`) keep working only if Pages 301s them
to `/visie/` — probe **after** the DNS switchover (before it, the old
site answers):

```
curl -sI https://peterselie.nl/visie | head -3
```

Expect `301` + `Location: .../visie/`.

## First-deploy checklist

1. Open https://breuderink.github.io/ (the user-site URL) — chrome,
   banner, menu (with sub-menu), one page.
2. Open one `/files/...` image and check it renders (media are plain
   git blobs, no LFS — if a few lines of `version https://...` text
   show instead, something smudge-processed the checkout).
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

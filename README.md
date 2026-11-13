# peterselie.nl

Broncode van de website. Eleventy bouwt de site uit de pagina's; elke
push naar `main` bouwt en publiceert automatisch naar GitHub Pages
(`.github/workflows/deploy.yml`).

## Pagina's bewerken

Alleen twee bestanden worden aangepakt:

- `content/*.md` — de pagina's (markdown)
- `content/_data/menu.json` — het zijbalkmenu (volgorde, labels,
  één niveau ondermenu's)

De handleiding met de markdown-regels van deze site staat in
[EDITEREN.md](EDITEREN.md).

## Media

Alle media (afbeeldingen, audio, video) staat in `files/`, opgeslagen
via Git LFS — `git lfs install` een keer per machine. Nieuwe bestanden
naar `files/` zetten en in de pagina linken als `/files/naam.ext`.

## Lokaal bouwen

```bash
npm install     # @11ty/eleventy (dev dependency)
npm run build   # build/ opruimen + bouwen + link/asset-check → PASS
```

Lokaal bekijken: `python3 -m http.server -d build 8000` →
http://localhost:8000

## Publiceren

Pushen naar `main` is genoeg. De eenmalige instelling op GitHub en de
checklist na de eerste deploy staan in [DEPLOY.md](DEPLOY.md).

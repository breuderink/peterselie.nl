# Publiceren (deploy)

Automatisch: elke push naar `main` bouwt `build/` en publiceert het naar
GitHub Pages (`.github/workflows/deploy.yml`). Eénmalig in de repo
instellen: Settings → Pages → Source: **GitHub Actions**. De site staat
dan op `https://breuderink.github.io/peterselie.nl/`.

## Url's

Pagina's worden uitgebracht als mappen: `/visie/` → `visie/index.html`.
GitHub Pages kent de Content-Type af aan de extensie en kan pagina's
zonder extensie niet als html serveren (waarom S3/Plesk dat wél kon, met
trucs). Oude, zonder-extensie url's (`/visie`) blijven werken als Pages
ze met 301 naar `/visie/` omsturt — **na de eerste deploy controleren**:

```
curl -sI https://breuderink.github.io/peterselie.nl/visie | head -3
```

verwacht `301` + `Location: .../visie/`. Zonder die redirect is er op
Pages geen alternatief; dan moeten externe verwijzers gemigreerd worden
(user call).

## Lokale build + controle

`npm run build` = build/ opruimen + eleventy + gate (tools/validate.py);
eindigt in `PASS`. De gate draait lokaal (playwright/chromium); CI bouwt
en publiceert alleen.

Lokaal bekijken: `python3 -m http.server -d build 8000` →
http://localhost:8000. Een map-styled request (`/visie`) stuurt de
server om naar `/visie/`, zoals Pages dat doet.

## Na de eerste deploy controleren

- [ ] Redirect `/visie` → `/visie/` (curl hierboven).
- [ ] Een paar pagina's, de menuknoppen, een video, een audio-download
      (bijv. `/files/...`).
- [ ] Onbekende url toont de 404-pagina (Pages serveert `404.html`
      zelf voor onbekende urls).

## Omschakelen op het domein (pas ná groene controle)

1. `CNAME`-bestand met `peterselie.nl` in de repo (project sites mogen
   een custom domain); DNS van peterselie.nl dan wijzen op GitHub Pages
   (docs.github.com → Configuring a custom domain for a GitHub Pages
   site).
2. E-mail: info@peterselie.nl staat op hetzelfde Plesk-account als de
   huidige website (gecontroleerd, 2026-10-17). MX-records zijn
   onafhankelijk van de website; bij een eventueel later verhuizing van
   het domein (iCloud) wisselen ze apart.
3. De oude site (Drupal) pas uitschakelen ná de nieuwe.
4. Na livegang: een paar pagina's, de menuknoppen, een video en een
   audio-download controleren.

## Alternatieven (niet nodig)

rsync naar Plesk of `aws s3 sync` blijven mogelijk; de mappen-url's
(`index.html` per map) werken daar zonder Content-Type-truc.

# Publiceren (deploy)

De map `build/` na `npm run build` (eindigend in `PASS`) is de complete
website: zelfde urls en bestandsnamen als de huidige site.

## Optie 1: rsync naar de huidige server (Plesk)

```
rsync -avz --delete build/ <gebruiker>@peterselie.nl:/path/naar/webroot/
```

- Upload alles uit `build/` (de map zelf niet), bestaande bestanden
  verwijderen met `--delete`.
- De server mag statisch leveren; PHP is niet nodig.
- Let op: paginabestanden zonder extensie krijgen bij veel statische
  servers (nginx default_type, Apache, S3) `application/octet-stream` —
  zet daar expliciet `text/html` (zie Optie 2), anders downloadt de
  browser de pagina.
- Controleer daarna een paar pagina's én een afbeelding en een
  downloadlink (bijv. /files/bouwplaat.tif).

## Lokaal testen

`python3 -m http.server` levert paginabestanden zonder extensie op als
`application/octet-stream` — de browser downloadt dan i.p.v. tonen.
Gebruik daarom:

```
python3 tools/serve_local.py 8000
```

en ga naar http://localhost:8000.

## Optie 2: S3 (statische hosting)

```
aws s3 sync build/ s3:<bucket>/ --delete
```

Let op: onze paginabestanden hebben **geen extensie** (zoals de oude
site: `/visie`, niet `/visie.html`). S3 kent de Content-Type af aan de
extensie en zou dan `application/octet-stream` geven — de browser
downloadt i.p.v. tonen. Los op door voor de pagina's expliciet
`Content-Type: text/html` te zetten, bijv.:

```
# pagina's = bestanden zonder extensie, behalve index.html en /files/*
cd build && find . -maxdepth 1 -type f ! -name "*.html" ! -name "*.txt" -print0 |
  xargs -0 -n1 -I{} aws s3 cp "{}" "s3:<bucket>/{}" --content-type "text/html; charset=utf-8"
```

(De bestanden in `files/`, `themes/`, `misc/`, `modules/` laten S3
normaliter op de juiste Content-Type zetten.)

## Vóór het omschakelen

- [ ] DNS: laat de domeinwijziging pas toe na een groene controle.
- [ ] E-mail: info@peterselie.nl staat op hetzelfde Plesk-account als de
      website (gecontroleerd, 2026-10-17). Gaat de mail later naar iCloud
      op een domein, dan wisselen de MX-records — onafhankelijk van de
      website zelf; de mail blijft dan werken zolang het domein er is.
- [ ] De oude site (Drupal) pas uitschakelen ná de nieuwe site.
- [ ] Na livegang: een paar pagina's, de menuknoppen, een video en een
      audio-download controleren.

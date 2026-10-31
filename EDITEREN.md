# Peterselie: website bewerken

De website bestaat uit gewone tekstbestanden. Elke pagina is één bestand
in de map `content/`, met de naam van de pagina:

- `content/visie.md` → https://peterselie.nl/visie
- `content/contact.md` → https://peterselie.nl/contact

## Zo bewerkt u een pagina

1. Open het bestand in een teksteditor (bijv. Kladblok/TextEdit).
2. Pas de tekst aan.
3. Sla op, bouw de site opnieuw (zie onder), en controleer het groene
   licht.

### Regels en tekst

- **Een regel in het bestand = een regel op de website.**
  Nieuwe regel in het bestand, nieuwe regel op de site. Geen extra
  tekenen nodig.
- Een lege regel maakt een nieuwe alinea.
- Let op onzichtbare markeringen: `*woord*` of `_woord_` wordt cursief,
  `#` aan het begin van een regel wordt een kop, en `[` ... `](` wordt
  een link. Type er niet toevallig tussenin.
- Bestaande markeringen in het bestand (bijv. `<a>`, `<img>`, `&nbsp;`)
  mag u niet verwijderen.
- Afbeeldingen en links staan in het bestand als hele regels met
  `<img ...>` of `<a ...>`. Laat die ongewijzigd.

### Wat mag u NIET aanraken

- De regels bovenin het bestand, tussen de `---` (permalink, title,
  h2, ...): die bepalen de url en de opmaak.
- De bestanden `_includes/`, `themes/`, `files/`, `tools/` en de
  bestanden `STATE.md`, `LOG.md`, `KNOWLEDGE.md`, `TASKS.md`.

## Het menu

Het menu staat in één bestand: `content/_data/menu.json`. Elke item heeft:

- `"label"` — de tekst zoals die in het menu staat
- `"url"` — de link (bijv. `/contact` = https://peterselie.nl/contact)
- `"children"` — optioneel: submenu-items, zelf weer label + url

De volgorde in het bestand is de volgorde in het menu. Een item met
children staat open op zijn eigen pagina en op de pagina's van zijn
children. De controle checkt het menu tegen dit bestand, dus aanpassingen
in het menu mogen gewoon — de pagina's zelf blijven vast aan het origineel.

## Nieuwe afbeelding of bestand

Zet het bestand in de map `files/` en verwijst ernaar in de pagina met
de url `https://peterselie.nl/files/naam-van-het-bestand`.

## Na het bewerken: bouwen en controleren

```
npm run build
```

Dit bouwt de site, maakt de media kleiner waar veilig kan, en controleert
alle 179 pagina's tegen het origineel.

- Eindigt het met `PASS`? Dan is de site klaar om te publiceren
  (zie `DEPLOY.md`).
- Eindigt het met `FAIL`? Dan is er iets mis met de aanpassing. Zet het
  bestand terug (`git checkout content/naam.md`) en bouw opnieuw.

## Terug naar de oude versie

Elke bewaarde versie zit in git. `git log -- content/visie.md` toont de
geschiedenis van een pagina; `git checkout <versie> -- content/visie.md`
zet hem terug.

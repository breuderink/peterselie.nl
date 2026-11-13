# Peterselie: editing the website

The website is plain text files. Each page is one file in the `content/`
directory, named after the page:

- `content/visie.md` → https://peterselie.nl/visie
- `content/contact.md` → https://peterselie.nl/contact

## How to edit a page

1. Open the file in a text editor (e.g. Notepad/TextEdit).
2. Change the text.
3. Save, rebuild the site (see below), and check for the green light.

### Lines and text

- **One line in the file = one line on the website.**
  New line in the file, new line on the site. No extra characters needed.
- A blank line starts a new paragraph.
- Watch out for invisible markers: `*word*` or `_word_` becomes
  italic, a `#` at the start of a line becomes a heading, and
  `[` ... `](` becomes a link. Do not type these by accident.
- Existing markers in the file (e.g. `<a>`, `<img>`, `&nbsp;`) must not
  be removed.
- Images and links appear in the file as whole lines with `<img ...>` or
  `<a ...>`. Leave them unchanged.

### What you must NOT touch

- The lines at the top of the file, between the `---` (permalink, title,
  h2, ...): they determine the URL and the layout.
- The files in `_layouts/`, `_includes/`, `_data/`, `files/resources/`,
  `tools/` and the files `_config.yml`, `Gemfile`, `README.md`,
  `DEPLOY.md`.

## The menu

The menu lives in one file: `_data/navigation.yml`. Each item has:

- `label:` — the text as shown in the menu
- `url:` — the link, with a trailing slash (e.g. `/contact/` =
  https://peterselie.nl/contact)
- `children:` — optional: sub-menu items, each again a label + url

The order in the file is the order in the menu. An item with children
stays open on its own page and on the pages of its children. The build
check verifies the menu against this file and that every link resolves,
so changing the menu is fine.

## Adding an image or file

Put the file in the `files/` directory and refer to it from the page
with the root-absolute path `/peterselie.nl/files/name-of-the-file`
(the baseurl prefix is what makes it resolve on the project page; it
also works once the CNAME is active).

## After editing: build and check

```
bundle exec jekyll build --destination build && python3 tools/check.py
```

This cleans `build/`, builds the site, and runs the check that every
link and file reference in all 180 pages resolves.

- Does it end with `PASS`? Then the site is ready to publish
  (see `DEPLOY.md`).
- Does it end with `FAIL`? Something is wrong with the change. Revert
  the file (`git checkout content/name.md`) and build again.

## Going back to an older version

Every saved version is in git. `git log -- content/visie.md` shows a
page's history; `git checkout <version> -- content/visie.md` restores it.

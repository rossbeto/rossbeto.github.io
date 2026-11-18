# A Coder's CV

Source of **https://rossbeto.github.io**: my CV, project write-ups and technical posts.
Built with [MkDocs](https://www.mkdocs.org) and [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/),
deployed to GitHub Pages by GitHub Actions on every push to `main`.

## Run it locally

```bash
make sync       # install from uv.lock (needs uv)
make serve      # http://127.0.0.1:8001, reloads on save
make check      # lint, import contracts, tests, strict build, link check, forbidden terms (what CI runs)
```
No Python on the machine? `make docker-serve` runs the same preview in a container.

The CV PDF needs WeasyPrint's system libraries (Pango; `apt install libpango-1.0-0
libpangoft2-1.0-0 libharfbuzz-subset0`). Without them `make generate` skips the PDF with a
warning and the site simply has no "Download PDF" link; `make docker-pdf` makes it in a container
instead. CI sets `PORTFOLIO_PDF=required`, so a deploy always has it.

## Layout

| Path | What |
|---|---|
| `data/cv.yml` | **the CV**: one source for the CV page, the PDF, the profile column and the home header (JSON Resume shape) |
| `docs/` | the pages (Markdown) and assets; `docs/cv/index.md` and `docs/cv/*.pdf` are generated |
| `docs/projects/` | one page per project (front matter feeds the generated index and home cards); hand-written, or synced from the project's repo |
| `data/projects.yml` | projects synced from their own repos' portfolio cards, pinned to a commit |
| `docs/blog/posts/` | blog posts (Material blog plugin); how to write one: `docs/blog/README.md` |
| `src/portfolio/` | `portfolio generate`: validates `data/cv.yml` and post front matter, writes the generated files and the CV PDF (gitignored); print layout in `templates/cv_print.*` |
| `generated/` | generated Markdown pulled into pages with `pymdownx.snippets` (home: latest posts) |
| `overrides/` | Material theme overrides: the profile column on the left of every page |
| `mkdocs.yml` | site configuration, navigation, the profile values |
| `tests/` | the site builds in strict mode; the profile is on every page; no email or placeholder is published |
| `scripts/` | offline link check, forbidden-terms check (hashed list) |

## Edit the CV

Edit `data/cv.yml`, then `make generate` (or `make serve`, which runs it once at start; re-run
`make generate` while it is running). Validation names the field: `work[0].highlights[1]:
placeholder '[X]'`. Capabilities shown only in a personal lab carry `proof: projects/<page>.md`
and get a **lab** badge. No email or phone: the site never publishes them.

The same run writes `docs/cv/NguyenHienLam-CV.pdf` (A4). Over 3 pages fails the build. To keep
the PDF short, `x_print: false` on an entry keeps it on the web page only.

## Add a project

1. Copy `docs/projects/_template.md.example` to `docs/projects/<slug>.md` and fill in the front
   matter (`stage`, not `status`: Material reserves that key). Keep `repo_public: false` until
   the repository is public; the site then never links to it (a test checks).
2. Put media under `docs/assets/projects/<slug>/` (GIFs ≤ 1 MB, other images ≤ 300 KB; a test
   checks) and use a small poster image for the card.
3. Add one line under `Projects` in the `nav` of `mkdocs.yml` (the strict build fails if you
   forget), then `make check`.

`featured: true` puts the card on the home page (up to 3).

## Sync a project from its repo

A **public** project can keep its write-up next to its code, in `docs/portfolio-card.md`
(template: `docs/projects/_card_template.md.example`). The card has exactly these `##`
sections: **Title, Pitch, Media, Highlights, Tech stack, Links**; a missing, empty, repeated or
unknown section stops the sync and names it.

1. Add the repo to `data/projects.yml` with `ref` (a full commit SHA), the `media` files to copy
   and the site-only `meta` (summary, stage, kind, tags, poster image).
2. `make projects-sync` writes `docs/projects/<slug>.md` and `docs/assets/projects/<slug>/…`:
   links into the repo point at the file on GitHub **at that commit**; images must be listed in
   `media` (no hotlinking). Add the nav line, `make check`, commit.
3. Later updates: the `sync-projects` workflow (manual or weekly) bumps the refs and opens a pull
   request. CI runs `make projects-check`, which fails if a synced page was edited by hand.

Private repos are never synced (no token); their pages stay hand-written with `repo_public: false`.

## Add a post

1. Copy `docs/blog/posts/_template.md.example` to `docs/blog/posts/<slug>.md` (it starts as `draft: true`).
2. Write; `make serve` shows drafts, the build never publishes them.
3. Go through the checklist in `docs/blog/README.md`, remove `draft: true`, run `make check`, push.

`portfolio generate` (run by `make build`, `make serve` and the tests) checks the front matter: a
title over 60 characters, a description over 155, 2–5 tags, unknown keys, or a `[X]` gap stop the
build and name the file.

## Contact

[Open an issue](https://github.com/rossbeto/rossbeto.github.io/issues/new?template=contact.yml)
(issues are public) or message me on [LinkedIn](https://www.linkedin.com/in/lam-nguyen-723b279/).

## Licence

Code and content: [MIT](LICENSE).

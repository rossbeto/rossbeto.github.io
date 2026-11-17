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

## Layout

| Path | What |
|---|---|
| `data/cv.yml` | **the CV**: one source for the CV page, the profile column and the home header (JSON Resume shape) |
| `docs/` | the pages (Markdown) and assets; `docs/cv/index.md` is generated |
| `docs/blog/posts/` | blog posts (Material blog plugin); how to write one: `docs/blog/README.md` |
| `src/portfolio/` | `portfolio generate`: validates `data/cv.yml` and post front matter, writes the generated files (gitignored) |
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

# A Coder's CV

Source of **https://rossbeto.github.io**: my CV, project write-ups and technical posts.
Built with [MkDocs](https://www.mkdocs.org) and [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/),
deployed to GitHub Pages by GitHub Actions on every push to `main`.

## Run it locally

```bash
make sync       # install from uv.lock (needs uv)
make serve      # http://127.0.0.1:8001, reloads on save
make check      # lint, tests, strict build, link check, forbidden-terms check (what CI runs)
```
No Python on the machine? `make docker-serve` runs the same preview in a container.

## Layout

| Path | What |
|---|---|
| `docs/` | the pages (Markdown) and assets |
| `overrides/` | Material theme overrides: the profile column on the left of every page |
| `mkdocs.yml` | site configuration, navigation, the profile values |
| `tests/` | the site builds in strict mode; the profile is on every page; no email or placeholder is published |
| `scripts/` | offline link check, forbidden-terms check (hashed list) |

## Contact

[Open an issue](https://github.com/rossbeto/rossbeto.github.io/issues/new?template=contact.yml)
(issues are public) or message me on [LinkedIn](https://www.linkedin.com/in/lam-nguyen-723b279/).

## Licence

Code and content: [MIT](LICENSE).

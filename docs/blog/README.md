# Writing a post (not built: `exclude_docs` in mkdocs.yml)

1. Copy `posts/_template.md.example` to `posts/<slug>.md`, keep `draft: true` while writing.
2. `make serve` shows drafts; `make build` never publishes them.
3. Before removing `draft: true`, go through the checklist below, then `make check`.

Front matter is validated by `portfolio generate` (`src/portfolio/blog/model.py`): unknown keys,
a title over 60 characters, a description over 155, fewer than 2 or more than 5 tags, or a `[X]`
gap stop the build with the file name.

## Review checklist (every post)
- [ ] No employer-internal names, code, URLs or figures; examples come from my public labs only.
- [ ] Every claim checked against the lab code and tests; snippets are real (shortened, not invented).
- [ ] A plain-language intro a recruiter can follow; the details below the `<!-- more -->` line.
- [ ] Title ≤ 60 characters, description ≤ 155, 2–5 tags, 1–2 categories.
- [ ] Images have alt text; no image over 1 MB.
- [ ] `make check` green (spelling, links, forbidden terms).

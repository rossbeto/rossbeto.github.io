"""A Coder's CV: the site's Python package.

`portfolio generate` writes plain files from the content before `mkdocs build` (today: the
"latest posts" list on the home page; from Phase 003: the CV page and profile from data/cv.yml).
Plain files, not an MkDocs hook, so the site also builds with Zensical, which does not run hooks
(plan: decisions D-05).
"""

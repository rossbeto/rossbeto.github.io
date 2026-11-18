# A Coder's CV. `make help` lists targets.
.DEFAULT_GOAL := help
UV := uv
export NO_MKDOCS_2_WARNING := 1
PORT ?= 8001
MATERIAL_IMAGE := squidfunk/mkdocs-material:9.8.1
PYTHON_IMAGE := python:3.13-slim-trixie
PLAYWRIGHT_IMAGE := mcr.microsoft.com/playwright/python:v1.64.1-noble
PDF_LIBS := libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0

.PHONY: help sync generate pdf docker-pdf projects-sync projects-check social-images a11y zensical serve build test lint links terms check docker-serve clean

help:            ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/ —/'

sync:            ## install from uv.lock
	$(UV) sync --frozen

generate:        ## write the generated pages, snippets and the CV PDF (skipped with a warning without Pango)
	$(UV) run portfolio generate

pdf:             ## like generate, but a missing CV PDF is an error (as in CI)
	PORTFOLIO_PDF=required $(UV) run portfolio generate

docker-pdf:      ## `make pdf` in a container, for a host without Pango (installs nothing on the host)
	docker run --rm -v $(CURDIR):/src -w /src -e PORTFOLIO_PDF=required \
	  -e UV_PROJECT_ENVIRONMENT=/tmp/venv $(PYTHON_IMAGE) sh -ec '\
	    apt-get update -q && apt-get install -y -q --no-install-recommends $(PDF_LIBS) >/dev/null; \
	    pip install -q uv==0.11.3; uv sync --frozen -q; uv run portfolio generate; \
	    chown -R $(shell id -u):$(shell id -g) docs/cv docs/projects generated overrides/partials'

projects-sync:   ## project pages from their repos' portfolio cards, at the refs in data/projects.yml (network)
	$(UV) run portfolio sync-projects

projects-check:  ## fail if synced project pages differ from their pinned cards (network; CI runs it)
	$(UV) run portfolio sync-projects --check

social-images:   ## re-render the share-preview card and touch icon from data/cv.yml (Docker), then commit them
	$(UV) run python scripts/social_images.py html
	docker run --rm --user $(shell id -u):$(shell id -g) -e HOME=/tmp -v $(CURDIR):/src -w /src \
	  $(PLAYWRIGHT_IMAGE) sh -ec 'pip install -q --user --break-system-packages playwright==1.64.1 \
	    && python3 scripts/social_images.py shoot'

a11y: build      ## axe-core accessibility check of the built site, light and dark (Docker)
	@mkdir -p .cache
	@test -s .cache/axe.min.js || curl -fsSL -o .cache/axe.min.js https://cdn.jsdelivr.net/npm/axe-core@4.10.3/axe.min.js
	docker run --rm --user $(shell id -u):$(shell id -g) -e HOME=/tmp -v $(CURDIR):/src -w /src \
	  $(PLAYWRIGHT_IMAGE) sh -ec 'pip install -q --user --break-system-packages playwright==1.64.1; \
	    python3 -m http.server 8002 --bind 127.0.0.1 -d site >/dev/null 2>&1 & sleep 1; \
	    python3 scripts/a11y_check.py'

zensical: generate  ## trial build with Zensical, Material's successor (pinned; not part of check)
	uvx --from zensical==0.0.74 zensical build --clean

serve: generate  ## live preview on http://127.0.0.1:$(PORT) (re-run `make generate` after editing post front matter)
	$(UV) run mkdocs serve -a 127.0.0.1:$(PORT)

build: generate  ## strict build into site/
	$(UV) run mkdocs build --strict

test:            ## unit + build tests; coverage gate on the generator package
	$(UV) run pytest --cov=portfolio --cov-report=term-missing:skip-covered --cov-fail-under=95

lint:            ## ruff, format, mypy, codespell
	$(UV) run ruff check .
	$(UV) run ruff format --check .
	$(UV) run mypy
	$(UV) run lint-imports
	$(UV) run codespell

links: build     ## relative links in the Markdown sources resolve (offline)
	$(UV) run python scripts/check_links.py README.md docs/

terms:           ## no forbidden (internal) names in files and commit messages
	python3 scripts/forbidden_terms.py check --history

check: lint test links terms  ## everything CI runs

docker-serve:    ## the same preview in a container (needs generated/ from a previous `make generate`)
	docker run --rm -it -p 127.0.0.1:$(PORT):8000 -v $(CURDIR):/docs $(MATERIAL_IMAGE)

clean:           ## remove build output
	rm -rf site .cache generated

# A Coder's CV. `make help` lists targets.
.DEFAULT_GOAL := help
UV := uv
export NO_MKDOCS_2_WARNING := 1
PORT ?= 8001
MATERIAL_IMAGE := squidfunk/mkdocs-material:9.8.1

.PHONY: help sync serve build test lint links terms check docker-serve clean

help:            ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/ —/'

sync:            ## install from uv.lock
	$(UV) sync --frozen

serve:           ## live preview on http://127.0.0.1:$(PORT)
	$(UV) run mkdocs serve -a 127.0.0.1:$(PORT)

build:           ## strict build into site/
	$(UV) run mkdocs build --strict

test:            ## unit + build tests
	$(UV) run pytest

lint:            ## ruff, format, mypy, codespell
	$(UV) run ruff check .
	$(UV) run ruff format --check .
	$(UV) run mypy
	$(UV) run codespell

links: build     ## relative links in the Markdown sources resolve (offline)
	$(UV) run python scripts/check_links.py README.md docs/

terms:           ## no forbidden (internal) names in files and commit messages
	python3 scripts/forbidden_terms.py check --history

check: lint test links terms  ## everything CI runs

docker-serve:    ## the same preview in a container (no host Python needed)
	docker run --rm -it -p 127.0.0.1:$(PORT):8000 -v $(CURDIR):/docs $(MATERIAL_IMAGE)

clean:           ## remove build output
	rm -rf site .cache

PYTHON ?= python
PIP ?= $(PYTHON) -m pip

.PHONY: install test conformance lint build clean types-python types-typescript openapi-validate

install:
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

test: conformance

conformance:
	$(PYTHON) -m pytest conformance/python/ -v

lint:
	$(PYTHON) -m ruff check python/ conformance/python/
	$(PYTHON) -m ruff format --check python/ conformance/python/

build:
	$(PYTHON) -m build --sdist --wheel --outdir dist/

types-typescript:
	cd typescript && bun install && bun run typecheck

openapi-validate:
	$(PYTHON) -c "import yaml; yaml.safe_load(open('openapi/components.yaml'))" && echo "OpenAPI YAML syntax OK"

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache .mypy_cache
	find python conformance -type d -name '__pycache__' -prune -exec rm -rf {} +

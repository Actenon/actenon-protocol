PYTHON ?= python
PIP ?= $(PYTHON) -m pip

.PHONY: install test conformance lint build clean types-python types-typescript openapi-validate ecosystem verify-claims compile-yaml

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

ecosystem:
        python -m actenon_protocol.ecosystem --write README.md --repo actenon-protocol

# Regenerate the pre-compiled JSON catalogue from the YAML source.
# Run this whenever refusals/catalogue.v1.yaml changes; commit the JSON.
compile-yaml:
        $(PYTHON) scripts/compile_yaml_to_json.py

# Machine-verify every claim the README makes about the package itself:
# zero runtime deps, vector counts, version coherence, badge accuracy,
# YAML<->JSON catalogue sync. This is the gate that protects credibility
# for a trust product. Fails CI on any drift.
verify-claims: compile-yaml-check
        @echo "==> Verifying zero runtime dependencies"
        @$(PYTHON) -c "import tomllib,sys; \
                d=tomllib.load(open('pyproject.toml','rb')); \
                deps=d['project'].get('dependencies',[]); \
                sys.exit(1) if deps else print('OK: zero runtime deps')"
        @echo "==> Verifying YAML<->JSON catalogue sync"
        @$(PYTHON) scripts/compile_yaml_to_json.py --check
        @echo "==> Verifying Python badge in sync"
        @$(PYTHON) scripts/sync_badges.py --check
        @echo "==> Verifying README install instructions"
        @$(PYTHON) scripts/check_readme_installs.py
        @echo "==> Verifying ecosystem table"
        @$(PYTHON) -m actenon_protocol.ecosystem --check README.md --repo actenon-protocol
        @echo "==> All claims verified."

compile-yaml-check:
        @$(PYTHON) scripts/compile_yaml_to_json.py --check

clean:
        rm -rf build dist *.egg-info .pytest_cache .ruff_cache .mypy_cache
        find python conformance -type d -name '__pycache__' -prune -exec rm -rf {} +

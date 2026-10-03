"""Every canonical JSON Schema ships in the wheel, byte-identical.

The package carries hand-made copies of schemas/*.v1.json under
python/actenon_protocol/data/. Nothing checked them: execution_result.v1.json
(the 1.1.0 ExecutionResult union) and boundary_manifest.v1.json were never
copied, so the published package could not validate execution results, and the
standalone conformance runner failed outside a checkout.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = sorted((ROOT / "schemas").glob("*.v1.json"))
DATA = ROOT / "python" / "actenon_protocol" / "data"


@pytest.mark.parametrize("schema", SCHEMAS, ids=lambda p: p.name)
def test_schema_is_shipped_identically(schema: Path) -> None:
    shipped = DATA / schema.name
    assert shipped.exists(), f"{schema.name} is not shipped as package data"
    assert shipped.read_bytes() == schema.read_bytes(), (
        f"{schema.name} package copy differs from schemas/"
    )


def test_runner_finds_schemas_outside_a_checkout(tmp_path, monkeypatch) -> None:
    import importlib.util
    import shutil

    # The runner copied out of the repository (as external implementations do)
    # must still find the schemas, through the installed package.
    shutil.copytree(ROOT / "conformance", tmp_path / "conformance")
    spec = importlib.util.spec_from_file_location(
        "runner_copy", tmp_path / "conformance" / "runner.py"
    )
    runner = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(
        __import__("sys").modules, "runner_copy", runner
    )  # dataclasses need it registered
    spec.loader.exec_module(runner)
    names = {p.name for p in runner.schema_files()}
    assert "execution_result.v1.json" in names

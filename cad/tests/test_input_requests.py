"""Input requests mirror pending register rows without supplying measurements."""
import csv
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("input_requests", ROOT / "cad/input_requests.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_all_pending_rows_preserved():
    rows = list(csv.DictReader(module.REGISTER.open()))
    pending = [r for r in rows if r["evidence_state"] == "pending"]
    requests = module.requests(rows)
    assert {r["parameter"] for r in requests} == {r["parameter"] for r in pending}
    assert len(requests) == len(pending)
    assert all(r["value"] == "" and r["status"] == "pending" for r in requests)
    assert all(r["acquisition"] != "unclassified" for r in requests)


def test_new_pending_row_cannot_disappear():
    rows = list(csv.DictReader(module.REGISTER.open()))
    rows.append(dict(parameter="new_interface", value="", unit="mm",
                     evidence_state="pending", source="new source", release_requirement="Inspect"))
    added = next(r for r in module.requests(rows) if r["parameter"] == "new_interface")
    assert added["acquisition"] == "unclassified"


@pytest.mark.parametrize("mutation", ["unit", "value", "duplicate"])
def test_invalid_pending_row_rejected(mutation):
    row = dict(parameter="new_interface", value="", unit="mm", evidence_state="pending",
               source="source", release_requirement="Inspect")
    if mutation == "unit":
        row["unit"] = "guessed_unit"
    if mutation == "value":
        row["value"] = "42"
    with pytest.raises(ValueError):
        module.requests([row, row] if mutation == "duplicate" else [row])


def test_committed_sheet_matches_register():
    assert module.DEFAULT_OUTPUT.read_text() == module.render(module.requests(
        list(csv.DictReader(module.REGISTER.open()))))
